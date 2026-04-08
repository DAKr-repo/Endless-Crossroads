"""LiteRT-LM Gemma 4 inference engine for C.O.D.E.X.

Wraps Google's LiteRT-LM runtime to provide async generation
compatible with the Architect router. Replaces Ollama for the
"codex" (Academy) model slot.

Singleton pattern — one engine shared across Architect + Autopilot.
Only one conversation can exist at a time (LiteRT-LM limitation).
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

# Default model path (HuggingFace cache location after litert-lm download)
_DEFAULT_MODEL_PATH = (
    "/home/pi/.cache/huggingface/hub/"
    "models--litert-community--gemma-4-E2B-it-litert-lm/"
    "snapshots/616f4124e6ff216292f16e7f73ff33b5ba9a4dd4/"
    "gemma-4-E2B-it.litertlm"
)

# Context window — benchmarked stable up to 6K on CM5
_DEFAULT_MAX_TOKENS = 4096

# Singleton instance
_instance: Optional[LiteRTEngine] = None
_instance_lock = threading.Lock()


def get_litert_engine(
    model_path: str = _DEFAULT_MODEL_PATH,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> LiteRTEngine:
    """Get or create the singleton LiteRTEngine."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = LiteRTEngine(model_path, max_tokens)
        return _instance


class LiteRTEngine:
    """Async wrapper around LiteRT-LM for Gemma 4 E2B inference.

    Key constraints:
    - Only one conversation at a time (enforced by LiteRT-LM)
    - Lazy loading — engine loads on first generate() call
    - System prompt injected as first user message (Gemma chat format)
    - Thread-safe via asyncio.run_in_executor for blocking calls
    """

    def __init__(
        self,
        model_path: str = _DEFAULT_MODEL_PATH,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ):
        self._model_path = model_path
        self._max_tokens = max_tokens
        self._engine = None
        self._lock = threading.Lock()

    def _ensure_loaded(self):
        """Lazy-load the LiteRT-LM engine on first use."""
        if self._engine is not None:
            return

        import litert_lm
        litert_lm.set_min_log_severity(litert_lm.LogSeverity.WARNING)

        logger.info("Loading LiteRT-LM Gemma 4 E2B (%s)", self._model_path)
        self._engine = litert_lm.Engine(
            model_path=self._model_path,
            max_num_tokens=self._max_tokens,
        )
        logger.info("LiteRT-LM engine ready (max_tokens=%d)", self._max_tokens)

    def _build_messages(
        self, prompt: str, system: str = ""
    ) -> list[dict[str, str]]:
        """Build message list with optional system prompt injection."""
        messages = []
        if system:
            # Gemma 4 uses role-based chat — inject system as first user msg
            messages.append({
                "role": "user",
                "content": f"[System Instructions]\n{system}\n[End Instructions]\n\nAcknowledge briefly.",
            })
            messages.append({
                "role": "assistant",
                "content": "Understood.",
            })
        messages.append({"role": "user", "content": prompt})
        return messages

    def _generate_sync(
        self, prompt: str, system: str = "", max_tokens: int = 400
    ) -> tuple[str, int]:
        """Blocking generation. Run via executor for async."""
        with self._lock:
            self._ensure_loaded()
            conv = self._engine.create_conversation(
                messages=self._build_messages(prompt, system)
            )
            try:
                # Send empty message to trigger generation from pre-loaded messages
                # Actually, create_conversation with messages doesn't auto-generate.
                # We need to send the last user message separately.
                pass
            finally:
                pass

            # Recreate: conversation API expects send_message for generation
            del conv
            conv = self._engine.create_conversation()
            try:
                if system:
                    # Inject system prompt as first exchange
                    conv.send_message(
                        f"[System Instructions]\n{system}\n[End Instructions]\n\nAcknowledge briefly."
                    )

                resp = conv.send_message(prompt)
                text = self._extract_text(resp)
                # Rough token estimate: ~1.3 tokens per word
                token_est = max(1, int(len(text.split()) * 1.3))
                return text, token_est
            finally:
                del conv

    def _generate_stream_sync(
        self, prompt: str, system: str = ""
    ):
        """Blocking streaming generation. Yields text chunks."""
        with self._lock:
            self._ensure_loaded()
            conv = self._engine.create_conversation()
            try:
                if system:
                    conv.send_message(
                        f"[System Instructions]\n{system}\n[End Instructions]\n\nAcknowledge briefly."
                    )

                for chunk_dict in conv.send_message_async(prompt):
                    text = self._extract_text(chunk_dict)
                    if text:
                        yield text
            finally:
                del conv

    @staticmethod
    def _extract_text(resp: dict) -> str:
        """Extract text from LiteRT-LM response dict."""
        if not isinstance(resp, dict):
            return str(resp)
        content = resp.get("content", [])
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "".join(parts)

    def generate_sync(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 400,
    ) -> tuple[str, int]:
        """Blocking generation — for sync callers (dm_tools, discord_bot)."""
        return self._generate_sync(prompt, system, max_tokens)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 400,
    ) -> tuple[str, int]:
        """Async generation — returns (text, token_count)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._generate_sync, prompt, system, max_tokens
        )

    async def generate_stream(
        self,
        prompt: str,
        system: str = "",
    ) -> AsyncIterator[str]:
        """Async streaming — yields text chunks.

        Because LiteRT-LM's streaming is blocking, we collect chunks
        in a background thread and feed them through an async queue.
        """
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _producer():
            try:
                for chunk in self._generate_stream_sync(prompt, system):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:
                logger.error("LiteRT-LM stream error: %s", e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, _producer)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    def unload(self):
        """Release the engine from memory (thermal flush)."""
        with self._lock:
            if self._engine is not None:
                logger.info("Unloading LiteRT-LM engine")
                # Force cleanup without triggering segfault
                self._engine = None
                global _instance
                _instance = None

    @property
    def is_loaded(self) -> bool:
        return self._engine is not None

    @property
    def model_path(self) -> str:
        return self._model_path

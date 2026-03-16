"""
voice_bridge.py - Unified Voice Synthesis Bridge
=================================================
Provides emotional modulation, NPC speaker identity, and queued
playback for both terminal (aplay) and Discord (FFmpegPCMAudio)
interfaces via the Mouth TTS service (Piper).

WO-V13.1 | Sensory Integration: Piper TTS Voice Bridge
"""

import asyncio
import io
import os
import re
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiohttp

# Norwegian narrator voice model path (configurable via env)
_PIPER_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "piper"
NARRATOR_VOICE_MODEL = os.getenv(
    "PIPER_NARRATOR_MODEL",
    str(_PIPER_MODEL_DIR / "no_NO-talesyntese-medium.onnx")
)


# ============================================================================
# Voice Cue — Emotional Modulation
# ============================================================================

@dataclass
class VoiceCue:
    """Piper TTS modulation parameters tied to an emotional tag."""
    tag: str
    speaker_id: Optional[int] = None
    length_scale: float = 1.0
    noise_scale: float = 0.333
    noise_w_scale: float = 0.333


VOICE_CUE_TABLE: dict[str, VoiceCue] = {
    "hushed":   VoiceCue(tag="Hushed",   length_scale=1.3, noise_scale=0.15, noise_w_scale=0.2),
    "urgent":   VoiceCue(tag="Urgent",   length_scale=0.8, noise_scale=0.5,  noise_w_scale=0.5),
    "gravelly": VoiceCue(tag="Gravelly", length_scale=1.1, noise_scale=0.6,  noise_w_scale=0.6),
    "solemn":   VoiceCue(tag="Solemn",   length_scale=1.4, noise_scale=0.2,  noise_w_scale=0.15),
    "cheerful": VoiceCue(tag="Cheerful", length_scale=0.9, noise_scale=0.45, noise_w_scale=0.4),
    "menacing": VoiceCue(tag="Menacing", length_scale=1.2, noise_scale=0.55, noise_w_scale=0.5),
    "narrator": VoiceCue(tag="Narrator", length_scale=1.05, noise_scale=0.3, noise_w_scale=0.3),
}

# Regex: leading [Tag] bracket, e.g. "[Gravelly] Welcome to my forge."
_CUE_PATTERN = re.compile(r"^\[(\w+)\]\s*")


# ============================================================================
# NPC Speaker Pools — role -> speaker_id buckets
# ============================================================================

NPC_VOICE_POOLS: dict[str, list[int]] = {
    "merchant":    [5, 12, 42, 73, 88],
    "leader":      [0, 26, 54, 30, 98],
    "informant":   [11, 17, 46, 77, 84],
    "quest_giver": [3, 28, 60, 85, 93],
    "default":     [1, 8, 33, 50, 70],
    "narrator":    [24],
}


def get_npc_speaker_id(name: str, role: str = "default") -> int:
    """Deterministic speaker_id from NPC name and role.

    Uses hash(name) % pool_size so the same NPC always gets the same voice.
    """
    pool = NPC_VOICE_POOLS.get(role, NPC_VOICE_POOLS["default"])
    return pool[hash(name) % len(pool)]


# ============================================================================
# Voice Cue Parser
# ============================================================================

def parse_voice_cue(text: str) -> tuple[str, Optional[VoiceCue]]:
    """Extract a leading [Tag] voice cue from text.

    Returns:
        (cleaned_text, VoiceCue or None)
    """
    if not text:
        return (text, None)

    match = _CUE_PATTERN.match(text)
    if not match:
        return (text, None)

    tag = match.group(1).lower()
    cue = VOICE_CUE_TABLE.get(tag)
    if cue is None:
        return (text, None)

    cleaned = text[match.end():]
    return (cleaned, cue)


# ============================================================================
# VoiceBridge — Unified TTS Interface
# ============================================================================

class VoiceBridge:
    """Unified voice synthesis bridge for terminal and Discord playback.

    Replaces VoiceUplink.  Supports emotional modulation via VoiceCue,
    per-NPC speaker identity, and queued sequential playback.
    """

    MOUTH_URL = "http://127.0.0.1:5001/speak"
    MAX_TEXT_LEN = 500

    def __init__(self):
        self.enabled: bool = True
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=16)
        self._drain_task: Optional[asyncio.Task] = None

    # ── Text chunking ────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, max_len: int = 500) -> list[str]:
        """Split text on sentence boundaries for TTS chunking.

        Prevents long narrations from being truncated by the TTS engine.
        Splits on '. ', '! ', '? ' boundaries, keeping chunks under max_len.
        """
        if len(text) <= max_len:
            return [text]

        chunks: list[str] = []
        current = ""
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_len:
                current = f"{current} {sentence}".strip() if current else sentence
            else:
                if current:
                    chunks.append(current)
                # If a single sentence is longer than max_len, force-split it
                if len(sentence) > max_len:
                    for i in range(0, len(sentence), max_len):
                        chunks.append(sentence[i:i + max_len])
                    current = ""
                else:
                    current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text[:max_len]]

    # ── Core synthesis ──────────────────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w_scale: Optional[float] = None,
        model_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """POST to Mouth service with modulation params, return WAV bytes.

        Args:
            model_path: Optional override model path for narrator voice.
        """
        text = re.sub(r"```[\s\S]*?```", " code block ", text)
        text = text[:self.MAX_TEXT_LEN]
        if not text.strip():
            return None

        payload: dict = {"text": text}
        if speaker_id is not None:
            payload["speaker_id"] = speaker_id
        if length_scale is not None:
            payload["length_scale"] = length_scale
        if noise_scale is not None:
            payload["noise_scale"] = noise_scale
        if noise_w_scale is not None:
            payload["noise_w_scale"] = noise_w_scale
        if model_path is not None:
            payload["model_path"] = model_path

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.MOUTH_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.read()
        except Exception:
            return None

    # ── Discord playback ────────────────────────────────────────────────

    async def speak_discord(
        self,
        text: str,
        voice_client,
        voice_cue: Optional[VoiceCue] = None,
        speaker_id: Optional[int] = None,
    ):
        """Queue text for sequential playback in a Discord voice channel.

        Long text is automatically chunked on sentence boundaries so the
        full narration plays instead of being truncated.
        """
        if not self.enabled:
            return
        if not voice_client or not voice_client.is_connected():
            return

        # Chunk long text for complete playback
        chunks = self._chunk_text(text, self.MAX_TEXT_LEN)
        for chunk in chunks:
            try:
                self._queue.put_nowait(
                    (chunk, voice_client, voice_cue, speaker_id)
                )
            except asyncio.QueueFull:
                break

        if self._drain_task is None or self._drain_task.done():
            self._drain_task = asyncio.create_task(self._drain_queue())

    async def _drain_queue(self):
        """Sequential playback processor — one utterance at a time."""
        try:
            import discord
        except ImportError:
            return

        while not self._queue.empty():
            try:
                text, vc, cue, sid = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            # Resolve modulation from cue
            ls = cue.length_scale if cue else None
            ns = cue.noise_scale if cue else None
            nw = cue.noise_w_scale if cue else None
            final_sid = sid if sid is not None else (cue.speaker_id if cue else None)

            # Use Norwegian narrator model for narrator-tagged speech
            narrator_model = None
            if cue and cue.tag.lower() == "narrator":
                narrator_path = Path(NARRATOR_VOICE_MODEL)
                if narrator_path.exists():
                    narrator_model = str(narrator_path)

            wav_bytes = await self.synthesize(
                text,
                speaker_id=final_sid,
                length_scale=ls,
                noise_scale=ns,
                noise_w_scale=nw,
                model_path=narrator_model,
            )
            if not wav_bytes or not vc.is_connected():
                continue

            # Play via FFmpegPCMAudio with pipe input (no tempfile)
            done_event = asyncio.Event()

            def _after(error):
                done_event.set()

            source = discord.FFmpegPCMAudio(
                io.BytesIO(wav_bytes), pipe=True,
                before_options="-analyzeduration 100000",
            )

            while vc.is_playing():
                await asyncio.sleep(0.1)

            vc.play(source, after=_after)

            try:
                await asyncio.wait_for(done_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass

    # ── Terminal playback ───────────────────────────────────────────────

    @staticmethod
    def speak_terminal(wav_bytes: bytes) -> None:
        """Fire-and-forget playback via aplay subprocess."""
        if not wav_bytes:
            return
        if not shutil.which("aplay"):
            return
        proc = subprocess.Popen(
            ["aplay", "-q", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.stdin.write(wav_bytes)
        proc.stdin.close()
        # Fire-and-forget: do NOT call proc.wait()

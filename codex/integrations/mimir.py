#!/usr/bin/env python3
"""
MIMIR BRIDGE: Local AI Task Handler
====================================

Provides both an importable library function ``query_mimir()`` and a
CLI entry point.

Library usage::

    from codex.integrations.mimir import query_mimir
    result = query_mimir("Summarize the dungeon layout", context_text)

CLI usage::

    python3 -m codex.integrations.mimir "Instruction" --file context.py
"""

import importlib.util
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import requests

# Context optimization — load via spec_from_file_location to avoid sys.path mutation
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_OPTIMIZE_CONTEXT_PATH = _PROJECT_ROOT / "scripts" / "optimize_context.py"
CONTEXT_OPTIMIZER_AVAILABLE = False
create_mimir_context = None
ContextWindow = None
if _OPTIMIZE_CONTEXT_PATH.exists():
    try:
        _spec = importlib.util.spec_from_file_location(
            "optimize_context", str(_OPTIMIZE_CONTEXT_PATH),
        )
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        create_mimir_context = _mod.create_mimir_context
        ContextWindow = _mod.ContextWindow
        CONTEXT_OPTIMIZER_AVAILABLE = True
    except Exception:
        pass

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mimir"  # Custom Ollama model with Norse Skald persona


def query_mimir(
    prompt: str,
    context: str = "",
    namespace: Optional[str] = None,
    model: Optional[str] = None,
    priority_filter: Optional[int] = None,
    template_key: Optional[str] = None,
) -> str:
    """Query the local Mimir AI model.

    Args:
        prompt: The question or instruction.
        context: Optional context text (e.g. document content).
        namespace: Optional namespace tag for scoped queries (e.g. book name).
        model: Override default model name.
        priority_filter: If set, hint to the caller that results should be
                         sorted by priority (1=SOURCE, 2=SUPPLEMENTS, 3=MODULES).
        template_key: Optional key into NARRATIVE_TEMPLATES for few-shot examples.
                      WO-V47.0: Injects system prompt and examples from narrative_frame.

    Returns:
        AI response string, or an error message.
    """
    parts = []

    # WO-V47.0: Inject template system prompt and examples
    if template_key:
        try:
            from codex.core.services.narrative_frame import NARRATIVE_TEMPLATES
            template = NARRATIVE_TEMPLATES.get(template_key, {})
            if template.get("system"):
                parts.append(f"SYSTEM: {template['system']}")
            for ex in template.get("examples", []):
                parts.append(f"Example input: {ex.get('input', '')}")
                parts.append(f"Example output: {ex.get('output', '')}")
        except Exception:
            pass

    if namespace:
        parts.append(f"NAMESPACE: {namespace}")
    if context:
        parts.append(f"CONTEXT:\n{context}")
    # WO-V63.0: Cap prompt length to prevent abuse / accidental context blowout
    if len(prompt) > 2000:
        prompt = prompt[:2000]
    parts.append(f"TASK:\n{prompt}")
    parts.append("RESPONSE (Concise):")
    full_prompt = "\n\n".join(parts)

    payload = {
        "model": model or MODEL,
        "prompt": full_prompt,
        "stream": True,
        "options": {
            "temperature": 0.2,
            "num_ctx": 2048,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=90)
        response.raise_for_status()
        result = []
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                result.append(chunk.get("response", ""))
                if chunk.get("done", False):
                    break
        return "".join(result)
    except Exception as e:
        return f"Error connecting to Local AI: {e}"


class MimirAdapter:
    """Adapter bridging query_mimir() to the async .generate() interface.

    NarrativeEngine._consult_mimir() expects ``await self.mimir.generate(prompt)``.
    This adapter wraps the synchronous query_mimir() call in a coroutine so
    the existing async machinery works transparently.
    """

    async def generate(self, prompt: str) -> str:
        return query_mimir(prompt)


# Backward-compatible alias
query_local_ai = query_mimir

# Named namespace constants for structured queries
RULES_LORE_SEARCH = "rules_lore"


def search_rules_lore(prompt: str, context: str = "", system_id: str = "dnd5e", **kwargs) -> str:
    """Query Mimir scoped to rules/lore namespace with FAISS retrieval.

    WO-V33.0: Enriches context with FAISS chunks before calling Mimir.

    Args:
        prompt: The question or instruction.
        context: Optional existing context text.
        system_id: FAISS index to search (default "dnd5e").
    """
    rag_context = ""
    try:
        from codex.core.services.rag_service import get_rag_service
        rag = get_rag_service()
        result = rag.search(prompt, system_id, k=3, token_budget=600)
        # WO-V56.0: Thermal-gated summarization for 3+ chunks
        if result and len(result.chunks) >= 3 and rag._should_summarize():
            result = rag.summarize(result, prompt)
        if result:
            rag_context = rag.format_context(result, header="SOURCE:")
    except Exception:
        pass

    full_context = context
    if rag_context:
        full_context = f"{rag_context}\n\n{context}" if context else rag_context

    return query_mimir(prompt, full_context, namespace=RULES_LORE_SEARCH, **kwargs)


def build_grapes_context(grapes_dict: dict) -> str:
    """Format G.R.A.P.E.S. data as concise world context (~200 tokens).

    Handles both old flat format and new structured format.
    """
    if not grapes_dict:
        return ""

    # Detect format: flat strings vs nested lists
    sample = next(iter(grapes_dict.values()), None)
    is_flat = isinstance(sample, str)

    if is_flat:
        lines = []
        for key in ("geography", "religion", "achievements", "politics", "economics", "social", "language", "culture", "architecture"):
            val = grapes_dict.get(key)
            if val:
                lines.append(f"{key.upper()}: {val}")
        return "WORLD CONTEXT:\n" + "\n".join(lines) if lines else ""

    # Rich structured format -- try GrapesProfile
    try:
        from codex.core.world.grapes_engine import GrapesProfile
        profile = GrapesProfile.from_dict(grapes_dict)
        return "WORLD CONTEXT:\n" + profile.to_narrative_summary()
    except Exception:
        pass

    # Fallback: flatten nested structure manually
    parts = []
    for key in ("geography", "religion", "arts", "politics", "economics", "social", "architecture"):
        entries = grapes_dict.get(key, [])
        if isinstance(entries, list) and entries:
            first = entries[0]
            if isinstance(first, dict):
                summary = ", ".join(str(v) for v in first.values())
                parts.append(f"{key.upper()}: {summary}")
    return "WORLD CONTEXT:\n" + "\n".join(parts) if parts else ""


def build_zone_context(engine) -> str:
    """Build zone/module context from an engine's ZoneManager (~100 tokens).

    If the engine has a zone_manager attribute with an active module,
    returns structured context about the current module, chapter, zone,
    and progression state.

    Args:
        engine: Any game engine that may have a zone_manager attribute.

    Returns:
        Formatted context string, or empty string if no module is active.
    """
    zm = getattr(engine, "zone_manager", None)
    if zm is None or zm.module_complete:
        return ""

    lines = ["MODULE CONTEXT:"]
    lines.append(f"  Module: {zm.module_name}")
    if zm.chapter_name:
        lines.append(f"  Chapter: {zm.chapter_name}")
    if zm.zone_name:
        lines.append(f"  Zone: {zm.zone_name}")
    lines.append(f"  Progress: {zm.zone_progress}")

    entry = zm.current_zone_entry
    if entry:
        lines.append(f"  Topology: {entry.topology}")
        if entry.location_id:
            lines.append(f"  Location: {entry.location_id}")
        lines.append(f"  Exit condition: {entry.exit_trigger}")

    return "\n".join(lines)


def build_chronology_context(chronology: list, limit: int = 10) -> str:
    """Format recent historical events as concise world history context (~150 tokens).

    Accepts a list of HistoricalEvent dicts or HistoricalEvent objects.
    """
    if not chronology:
        return ""

    lines = ["WORLD HISTORY (recent events):"]
    for entry in chronology[:limit]:
        if hasattr(entry, "timestamp"):
            # HistoricalEvent object
            ts = entry.timestamp[:10] if len(entry.timestamp) >= 10 else entry.timestamp
            etype = entry.event_type.value if hasattr(entry.event_type, "value") else str(entry.event_type)
            summary = entry.summary
            auth = entry.authority_level
            reliability = auth.name if hasattr(auth, "name") else str(auth)
        else:
            # Dict format
            ts = str(entry.get("timestamp", ""))[:10]
            etype = str(entry.get("event_type", "?"))
            summary = entry.get("summary", "?")
            auth_val = entry.get("authority_level", 2)
            reliability_map = {1: "EYEWITNESS", 2: "CHRONICLE", 3: "LEGEND"}
            reliability = reliability_map.get(auth_val, str(auth_val))

        lines.append(f"- [{ts}] ({etype}, {reliability}) {summary}")

    return "\n".join(lines)


def query_mimir_with_context(
    prompt: str,
    system_prompt: str = "",
    world_state: Optional[dict] = None,
    chat_history: Optional[list] = None,
    model: Optional[str] = None,
    max_tokens: int = 8192,
) -> str:
    """Query Mimir with token-budget-aware context management.

    Uses ContextWindow from optimize_context.py to manage sliding
    window context within Ollama's token limit.

    Falls back to basic query_mimir() if optimizer unavailable.
    """
    if not CONTEXT_OPTIMIZER_AVAILABLE or not chat_history:
        context = ""
        if world_state:
            # WO-V8.0: inject G.R.A.P.E.S. context if available
            grapes = world_state.get("grapes") if isinstance(world_state, dict) else None
            if grapes:
                context = build_grapes_context(grapes)
            if not context:
                context = json.dumps(world_state, default=str)[:500]
            # WO-V11.2: inject chronology context if available
            chronology = world_state.get("chronology") if isinstance(world_state, dict) else None
            if chronology:
                chrono_ctx = build_chronology_context(chronology)
                if chrono_ctx:
                    context = (context + "\n\n" + chrono_ctx) if context else chrono_ctx
        return query_mimir(prompt, context=context, model=model)

    messages = create_mimir_context(
        system_prompt=system_prompt or "You are Mimir, a concise narrative AI.",
        world_state=world_state or {},
        chat_history=chat_history,
        max_tokens=max_tokens,
    )

    # Add the current prompt as the latest user message
    messages.append({"role": "user", "content": prompt})

    # Use Ollama chat API instead of generate
    payload = {
        "model": model or MODEL,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.2,
            "num_ctx": min(max_tokens, 4096),
        },
    }

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=payload, stream=True, timeout=90
        )
        response.raise_for_status()
        result = []
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                result.append(msg.get("content", ""))
                if chunk.get("done", False):
                    break
        return "".join(result)
    except Exception as e:
        return f"Error connecting to Local AI: {e}"


def main():
    parser = argparse.ArgumentParser(description="Ask Mimir a question.")
    parser.add_argument("instruction", type=str, help="What do you want Mimir to do?")
    parser.add_argument("--file", type=str, help="File to read as context", required=False)
    parser.add_argument("--namespace", type=str, help="Restrict to a book/vault namespace", required=False)

    args = parser.parse_args()

    file_content = ""
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_content = f.read()
        except FileNotFoundError:
            print(f"Error: File {args.file} not found.")
            sys.exit(1)

    if not sys.stdin.isatty():
        file_content += "\n" + sys.stdin.read()

    result = query_mimir(args.instruction, file_content, namespace=args.namespace)
    print(result)


if __name__ == "__main__":
    main()

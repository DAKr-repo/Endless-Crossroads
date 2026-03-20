#!/usr/bin/env python3
"""
scripts/enrich_module.py — Module Enrichment Pipeline (Tier 2 & 3)
===================================================================
Enriches generated module blueprints with Codex model output (Tier 2)
and optional RAG-sourced PDF context (Tier 3).

Usage:
    python scripts/enrich_module.py vault_maps/modules/bitd_heist_42/
    python scripts/enrich_module.py vault_maps/modules/bitd_heist_42/ --rag
    python scripts/enrich_module.py vault_maps/modules/bitd_heist_42/ --dry-run
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from codex.core.enrichment_prompts import (
    NPC_ENRICHMENT_SYSTEM,
    NPC_ENRICHMENT_TEMPLATE,
    MIMIR_NPC_SYSTEM,
    MIMIR_NPC_TEMPLATE,
    MIMIR_NPC_VALIDATE_PATTERN,
    ROOM_ENRICHMENT_SYSTEM,
    ROOM_ENRICHMENT_TEMPLATE,
    MIMIR_ROOM_SYSTEM,
    MIMIR_ROOM_TEMPLATE,
    EVENT_ENRICHMENT_SYSTEM,
    EVENT_ENRICHMENT_TEMPLATE,
    MIMIR_EVENT_SYSTEM,
    MIMIR_EVENT_TEMPLATE,
    QUEST_ARC_SYSTEM,
    QUEST_ARC_TEMPLATE,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LLM_COOLDOWN = 3.0  # seconds between model calls (Pi 5 thermal safety)
THERMAL_MAX_TEMP = 70.0  # Celsius — pause enrichment above this
THERMAL_WAIT_INTERVAL = 5.0  # seconds between thermal re-checks
THERMAL_MAX_WAIT = 120.0  # max seconds to wait for cooldown before skipping
ACADEMY_TIMEOUT_MS = 300_000  # 5 minutes — qwen3 needs time to think on Pi 5


# ---------------------------------------------------------------------------
# Module brief builder
# ---------------------------------------------------------------------------

def build_module_brief(manifest: dict, blueprints: dict) -> str:
    """Summarise a module into a compact ~200-token brief for prompt injection.

    Args:
        manifest: Parsed module_manifest.json dict.
        blueprints: Dict of scene_id -> blueprint dict.

    Returns:
        A compact text summary of the module structure.
    """
    lines = [f"{manifest.get('display_name', 'Unknown Module')} ({manifest.get('system_id', '?')})"]

    for chapter in manifest.get("chapters", []):
        lines.append(f"  Chapter: {chapter.get('display_name', chapter.get('chapter_id', '?'))}")
        for zone in chapter.get("zones", []):
            zid = zone.get("zone_id", "?")
            bp = blueprints.get(zid, {})
            room_count = len(bp.get("rooms", {}))
            npcs = []
            enemies = []
            for room in bp.get("rooms", {}).values():
                hints = room.get("content_hints", {})
                for npc in hints.get("npcs", []):
                    npcs.append(npc.get("name", "?"))
                for enemy in hints.get("enemies", []):
                    enemies.append(enemy.get("name", "?"))
            topo = bp.get("metadata", {}).get("topology", zone.get("topology", "?"))
            scene_line = f"    - {zid} ({topo}, {room_count} rooms)"
            if npcs:
                scene_line += f", NPCs: {', '.join(npcs[:3])}"
            if enemies:
                scene_line += f", Enemies: {', '.join(enemies[:3])}"
            lines.append(scene_line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Thermal gate
# ---------------------------------------------------------------------------

def _get_cpu_temp() -> float:
    """Read CPU temperature in Celsius. Returns 0.0 if unavailable."""
    try:
        from codex.core.cortex import get_cortex
        cortex = get_cortex()
        state = cortex.read_metabolic_state()
        return state.cpu_temp_celsius
    except Exception:
        return 0.0  # If cortex unavailable, assume cool


async def _wait_for_thermal() -> bool:
    """Wait until CPU is cool enough for model calls.

    Returns True if temperature is acceptable, False only after
    THERMAL_MAX_WAIT seconds of continuous overheating.
    """
    waited = 0.0
    while True:
        temp = _get_cpu_temp()
        if temp == 0.0 or temp < THERMAL_MAX_TEMP:
            return True
        if waited >= THERMAL_MAX_WAIT:
            return False
        await asyncio.sleep(THERMAL_WAIT_INTERVAL)
        waited += THERMAL_WAIT_INTERVAL


# ---------------------------------------------------------------------------
# RAG helper
# ---------------------------------------------------------------------------

def _query_rag(query: str, system_id: str) -> str:
    """Query RAGService for PDF context. Returns empty string if unavailable."""
    try:
        from codex.core.services.rag_service import get_rag_service
        rag = get_rag_service()
        result = rag.search(query, system_id, k=3)
        if result:
            return f"SOURCE MATERIAL:\n{result.context_str}\n\n"
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Codex invocation
# ---------------------------------------------------------------------------

_last_llm_call = 0.0
_architect = None


async def _get_architect():
    """Lazy-init a shared Architect with extended timeout for enrichment."""
    global _architect
    if _architect is None:
        from codex.core.architect import Architect, ArchitectConfig
        config = ArchitectConfig()
        config.ACADEMY_TIMEOUT_MS = ACADEMY_TIMEOUT_MS
        _architect = Architect(config)
    return _architect


async def _invoke_model(
    prompt: str,
    system_prompt: str,
    model: str = "codex",
    mode: str = "ACADEMY",
    retries: int = 1,
) -> Optional[str]:
    """Call a model via Architect with thermal check, cooldown, and retry.

    Args:
        prompt: User prompt text.
        system_prompt: System prompt text.
        model: Ollama model name ("codex" or "mimir").
        mode: ThinkingMode name — "ACADEMY" for Codex, "REFLEX" for Mimir.
        retries: Number of retry attempts on failure (default 1).

    Returns enriched text, or None if all attempts were skipped/failed.
    """
    global _last_llm_call

    for attempt in range(1 + retries):
        # Wait for CPU to cool if needed (up to THERMAL_MAX_WAIT seconds)
        if not await _wait_for_thermal():
            return None

        # Minimum cooldown between calls (extra cooldown on retry)
        cooldown = LLM_COOLDOWN * (2 if attempt > 0 else 1)
        elapsed = time.time() - _last_llm_call
        if elapsed < cooldown:
            await asyncio.sleep(cooldown - elapsed)

        try:
            from codex.core.architect import (
                RoutingDecision, ThinkingMode, Complexity,
            )
            from codex.core.cortex import ThermalStatus

            architect = await _get_architect()
            thinking_mode = getattr(ThinkingMode, mode, ThinkingMode.ACADEMY)
            decision = RoutingDecision(
                mode=thinking_mode,
                model=model,
                complexity=Complexity.HIGH if model == "codex" else Complexity.LOW,
                thermal_status=ThermalStatus.OPTIMAL,
                clearance_granted=True,
                reasoning="Module enrichment",
            )
            response = await architect.invoke_model(prompt, system_prompt, decision)
            _last_llm_call = time.time()

            content = response.content.strip()
            if content:
                return content
            # Empty response — retry if attempts remain
        except Exception:
            _last_llm_call = time.time()
            # Retry if attempts remain

    return None


async def _invoke_codex(prompt: str, system_prompt: str) -> Optional[str]:
    """Call Codex model (Academy mode). Backward-compatible wrapper."""
    return await _invoke_model(prompt, system_prompt, model="codex", mode="ACADEMY")


async def _invoke_mimir(prompt: str, system_prompt: str) -> Optional[str]:
    """Call Mimir model (Reflex mode) — fast, for dialogue."""
    return await _invoke_model(prompt, system_prompt, model="mimir", mode="REFLEX")


# ---------------------------------------------------------------------------
# Per-element enrichment
# ---------------------------------------------------------------------------

def _validate_npc_dialogue(text: str) -> bool:
    """Check if dialogue matches [Tone] sentence format."""
    import re
    return bool(re.match(MIMIR_NPC_VALIDATE_PATTERN, text))


async def _enrich_npc(
    npc: dict,
    module_name: str,
    system_id: str,
    module_brief: str,
    rag_context: str,
    scene_name: str = "",
) -> bool:
    """Enrich a single NPC's dialogue. Tries Mimir first, Codex fallback.

    Returns True if modified.
    """
    # --- Mimir path: few-shot, fast ---
    mimir_prompt = MIMIR_NPC_TEMPLATE.format(
        npc_role=npc.get("role", "unknown"),
        scene_name=scene_name or module_name,
        current_dialogue=npc.get("dialogue", ""),
    )
    result = await _invoke_mimir(mimir_prompt, MIMIR_NPC_SYSTEM)

    # Strip leading "-> " if model echoes the arrow
    if result and result.startswith("->"):
        result = result[2:].strip()

    # Validate format — if Mimir output is malformed, fall back to Codex
    if result and _validate_npc_dialogue(result):
        npc["dialogue"] = result
        return True

    # --- Codex fallback: full context, slower ---
    codex_prompt = NPC_ENRICHMENT_TEMPLATE.format(
        module_name=module_name,
        system_id=system_id,
        source_material=rag_context,
        module_brief=module_brief,
        npc_name=npc.get("name", "Unknown"),
        npc_role=npc.get("role", "unknown"),
        current_dialogue=npc.get("dialogue", ""),
    )
    result = await _invoke_codex(codex_prompt, NPC_ENRICHMENT_SYSTEM)
    if result:
        npc["dialogue"] = result
        return True
    return False


async def _enrich_room(
    hints: dict,
    module_name: str,
    system_id: str,
    scene_name: str,
    topology: str,
    tier: int,
    module_brief: str,
    rag_context: str,
) -> bool:
    """Enrich a room's description. Returns True if modified."""
    current = hints.get("description", "")
    if not current:
        return False
    prompt = ROOM_ENRICHMENT_TEMPLATE.format(
        module_name=module_name,
        system_id=system_id,
        source_material=rag_context,
        scene_name=scene_name,
        topology=topology,
        tier=tier,
        current_description=current,
    )
    result = await _invoke_codex(prompt, ROOM_ENRICHMENT_SYSTEM)
    if result:
        hints["description"] = result
        if hints.get("read_aloud"):
            hints["read_aloud"] = result[:200]
        return True

    # --- Mimir fallback: few-shot, fast ---
    room_type = hints.get("room_type", "room")
    mimir_prompt = MIMIR_ROOM_TEMPLATE.format(
        room_type=room_type,
        topology=topology,
        current_description=current,
    )
    result = await _invoke_mimir(mimir_prompt, MIMIR_ROOM_SYSTEM)
    if result:
        if result.startswith("->"):
            result = result[2:].strip()
        hints["description"] = result
        if hints.get("read_aloud"):
            hints["read_aloud"] = result[:200]
        return True
    return False


async def _enrich_events(
    hints: dict,
    module_name: str,
    system_id: str,
    scene_name: str,
    module_brief: str,
) -> bool:
    """Enrich event triggers for a room. Returns True if modified."""
    triggers = hints.get("event_triggers", [])
    if not triggers:
        return False
    trigger_text = "\n".join(f"- {t}" for t in triggers)
    prompt = EVENT_ENRICHMENT_TEMPLATE.format(
        module_name=module_name,
        system_id=system_id,
        module_brief=module_brief,
        scene_name=scene_name,
        current_triggers=trigger_text,
    )
    result = await _invoke_codex(prompt, EVENT_ENRICHMENT_SYSTEM)
    if result:
        new_triggers = [
            line.lstrip("- ").strip()
            for line in result.strip().splitlines()
            if line.strip()
        ]
        if new_triggers:
            hints["event_triggers"] = new_triggers
            return True

    # --- Mimir fallback: enrich triggers one at a time ---
    enriched = []
    any_changed = False
    for trigger in triggers:
        mimir_prompt = MIMIR_EVENT_TEMPLATE.format(current_trigger=trigger)
        mimir_result = await _invoke_mimir(mimir_prompt, MIMIR_EVENT_SYSTEM)
        if mimir_result:
            if mimir_result.startswith("->"):
                mimir_result = mimir_result[2:].strip()
            enriched.append(mimir_result)
            any_changed = True
        else:
            enriched.append(trigger)  # keep original on failure
    if any_changed:
        hints["event_triggers"] = enriched
        return True
    return False


async def _weave_quest_arc(
    manifest: dict,
    blueprints: dict,
    module_brief: str,
    rag_context: str,
) -> Optional[str]:
    """Generate a narrative hook connecting all scenes. Returns hook text."""
    scene_lines = []
    for chapter in manifest.get("chapters", []):
        for zone in chapter.get("zones", []):
            zid = zone.get("zone_id", "?")
            bp = blueprints.get(zid, {})
            display = bp.get("metadata", {}).get("display_name", zid)
            npcs = []
            for room in bp.get("rooms", {}).values():
                for npc in room.get("content_hints", {}).get("npcs", []):
                    npcs.append(npc.get("name", "?"))
            desc = bp.get("metadata", {}).get("topology", "")
            line = f"- {display}: {desc}"
            if npcs:
                line += f", NPCs: {', '.join(npcs[:3])}"
            scene_lines.append(line)

    prompt = QUEST_ARC_TEMPLATE.format(
        module_name=manifest.get("display_name", "Unknown"),
        system_id=manifest.get("system_id", "?"),
        source_material=rag_context,
        scene_list="\n".join(scene_lines),
    )
    result = await _invoke_codex(prompt, QUEST_ARC_SYSTEM)
    if result:
        return result

    # --- Mimir fallback: shorter prompt ---
    mimir_prompt = (
        f"Write a 2-sentence adventure hook for \"{manifest.get('display_name', '?')}\" "
        f"({manifest.get('system_id', '?')}). "
        f"Scenes: {', '.join(s.split(':')[0].lstrip('- ') for s in scene_lines[:4])}. "
        f"What brought the crew here and what threat awaits?"
    )
    return await _invoke_mimir(mimir_prompt, QUEST_ARC_SYSTEM)


# ---------------------------------------------------------------------------
# Main enrichment pipeline
# ---------------------------------------------------------------------------

async def enrich_module(
    module_dir: str,
    use_rag: bool = False,
    dry_run: bool = False,
) -> dict:
    """Enrich a generated module with Codex model output.

    Args:
        module_dir: Path to the module directory.
        use_rag:    Enable RAG-sourced PDF context (Tier 3).
        dry_run:    Print enrichment plan without modifying files.

    Returns:
        Dict with enrichment statistics.
    """
    module_path = Path(module_dir)
    manifest_path = module_path / "module_manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"No module_manifest.json in {module_path}")

    manifest = json.loads(manifest_path.read_text())
    system_id = manifest.get("system_id", "")
    module_name = manifest.get("display_name", "Unknown Module")

    # Load all blueprint JSONs
    blueprints: dict = {}
    for chapter in manifest.get("chapters", []):
        for zone in chapter.get("zones", []):
            bp_file = zone.get("blueprint")
            if bp_file:
                bp_path = module_path / bp_file
                if bp_path.exists():
                    blueprints[zone["zone_id"]] = json.loads(bp_path.read_text())

    # Build compact module brief
    module_brief = build_module_brief(manifest, blueprints)

    # Build enrichment work list
    work_items: list[tuple[str, str, dict]] = []  # (type, label, context)
    for scene_id, bp in blueprints.items():
        scene_name = bp.get("metadata", {}).get("display_name", scene_id)
        for room_id, room in bp.get("rooms", {}).items():
            hints = room.get("content_hints", {})
            for npc in hints.get("npcs", []):
                work_items.append(("npc", f"{npc.get('name', '?')} ({scene_name})",
                                   {"npc": npc, "scene_id": scene_id, "bp": bp}))
            if room_id == "0" and hints.get("description"):
                work_items.append(("room", scene_name,
                                   {"hints": hints, "scene_id": scene_id, "bp": bp}))
            if room_id == "0" and hints.get("event_triggers"):
                work_items.append(("event", f"Events: {scene_name}",
                                   {"hints": hints, "scene_id": scene_id, "bp": bp}))
    work_items.append(("quest_arc", "Quest Arc Weave", {}))

    # Count by type
    stats = {
        "npcs": sum(1 for t, _, _ in work_items if t == "npc"),
        "npcs_enriched": 0,
        "rooms": sum(1 for t, _, _ in work_items if t == "room"),
        "rooms_enriched": 0,
        "events": sum(1 for t, _, _ in work_items if t == "event"),
        "events_enriched": 0,
        "quest_arc": False,
        "codex_calls": 0,
        "mimir_calls": 0,
        "skipped_thermal": 0,
    }

    if dry_run:
        _codex_items = sum(1 for t, _, _ in work_items if t != "npc")
        _mimir_items = stats["npcs"]
        print(f"DRY RUN — Enrichment plan for: {module_name}")
        print(f"  System:        {system_id}")
        print(f"  Scenes:        {len(blueprints)}")
        print(f"  NPCs to enrich:  {stats['npcs']} (Mimir, ~25s each)")
        print(f"  Rooms to enrich: {stats['rooms']} (Codex, ~60s each)")
        print(f"  Events to enrich: {stats['events']} (Codex, ~60s each)")
        print(f"  Quest arc:       yes (Codex)")
        print(f"  RAG enabled:     {use_rag}")
        print(f"  Strategy:        Mimir first (fast), then Codex (creative)")
        print(f"  Thermal:         waits up to {int(THERMAL_MAX_WAIT)}s per "
              f"call if CPU > {THERMAL_MAX_TEMP}C")
        return stats

    # --- Rich progress display ---
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.panel import Panel

    console = Console()

    # Partition: Mimir runs first (fast, cools CPU), then Codex
    mimir_queue = [(t, l, c) for t, l, c in work_items if t == "npc"]
    codex_queue = [(t, l, c) for t, l, c in work_items if t != "npc"]

    console.print(Panel(
        f"[bold]{module_name}[/bold]  ({system_id})\n"
        f"Scenes: {len(blueprints)}  |  NPCs: {stats['npcs']}  |  "
        f"Rooms: {stats['rooms']}  |  Events: {stats['events']}\n"
        f"RAG: {'enabled' if use_rag else 'disabled'}  |  "
        f"Mimir: {len(mimir_queue)} NPCs  |  Codex: {len(codex_queue)} items\n"
        f"[dim]Mimir first (fast), then Codex. "
        f"Thermal patience: waits up to {int(THERMAL_MAX_WAIT)}s if hot.[/dim]",
        title="Module Enrichment",
        border_style="cyan",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        total = len(mimir_queue) + len(codex_queue)
        task = progress.add_task("[cyan]Preparing...", total=total)

        # --- Phase 1: Mimir handles all NPC dialogue (fast) ---
        for _, label, ctx in mimir_queue:
            progress.update(task, description=f"[magenta]Mimir: {label}")
            npc = ctx["npc"]
            bp = ctx["bp"]
            rag_ctx = ""
            if use_rag:
                rag_ctx = _query_rag(
                    f"What factions and notable figures exist as "
                    f"{npc.get('role', '')} in {system_id}?",
                    system_id,
                )
            _npc_scene = bp.get("metadata", {}).get(
                "display_name", ctx["scene_id"])
            ok = await _enrich_npc(
                npc, module_name, system_id, module_brief, rag_ctx,
                scene_name=_npc_scene)
            stats["mimir_calls"] += 1
            if ok:
                stats["npcs_enriched"] += 1
            else:
                stats["skipped_thermal"] += 1
            progress.advance(task)

        # --- Phase 2: Codex handles rooms, events, quest arc ---
        for item_type, label, ctx in codex_queue:
            progress.update(task, description=f"[cyan]Codex: {label}")

            if item_type == "room":
                hints = ctx["hints"]
                bp = ctx["bp"]
                scene_name = bp.get("metadata", {}).get(
                    "display_name", ctx["scene_id"])
                topology = bp.get("metadata", {}).get(
                    "topology", "dungeon")
                room_0 = bp.get("rooms", {}).get("0", {})
                tier = room_0.get("tier", 1)
                rag_ctx = ""
                if use_rag:
                    rag_ctx = _query_rag(
                        f"Describe the atmosphere and architecture "
                        f"of {topology} in {system_id}",
                        system_id,
                    )
                ok = await _enrich_room(
                    hints, module_name, system_id, scene_name,
                    topology, tier, module_brief, rag_ctx,
                )
                stats["codex_calls"] += 1
                if ok:
                    stats["rooms_enriched"] += 1
                else:
                    stats["skipped_thermal"] += 1

            elif item_type == "event":
                hints = ctx["hints"]
                bp = ctx["bp"]
                scene_name = bp.get("metadata", {}).get(
                    "display_name", ctx["scene_id"])
                ok = await _enrich_events(
                    hints, module_name, system_id,
                    scene_name, module_brief,
                )
                stats["codex_calls"] += 1
                if ok:
                    stats["events_enriched"] += 1
                else:
                    stats["skipped_thermal"] += 1

            elif item_type == "quest_arc":
                rag_ctx = ""
                if use_rag:
                    rag_ctx = _query_rag(
                        f"What conflicts and threats exist "
                        f"in {system_id}?",
                        system_id,
                    )
                hook = await _weave_quest_arc(
                    manifest, blueprints, module_brief, rag_ctx)
                stats["codex_calls"] += 1
                if hook:
                    stats["quest_arc"] = True
                    first_scene_id = None
                    for chapter in manifest.get("chapters", []):
                        for zone in chapter.get("zones", []):
                            first_scene_id = zone.get("zone_id")
                            break
                        if first_scene_id:
                            break
                    if first_scene_id and first_scene_id in blueprints:
                        bp = blueprints[first_scene_id]
                        room_0 = bp.get("rooms", {}).get("0", {})
                        h = room_0.get("content_hints", {})
                        h["read_aloud"] = hook
                else:
                    stats["skipped_thermal"] += 1

            progress.advance(task)

        progress.update(task, description="[green]Writing enriched blueprints...")

    # Write enriched blueprints back to disk
    for scene_id, bp in blueprints.items():
        bp_path = module_path / f"{scene_id}.json"
        bp_path.write_text(json.dumps(bp, indent=2))

    # Summary panel
    console.print(Panel(
        f"NPCs:      {stats['npcs_enriched']}/{stats['npcs']}  "
        f"(mimir: {stats['mimir_calls']}, codex fallback: {stats['codex_calls']})\n"
        f"Rooms:     {stats['rooms_enriched']}/{stats['rooms']}\n"
        f"Events:    {stats['events_enriched']}/{stats['events']}\n"
        f"Quest Arc: {'yes' if stats['quest_arc'] else 'no'}\n"
        f"Skipped:   {stats['skipped_thermal']}",
        title="Enrichment Complete",
        border_style="green" if stats["skipped_thermal"] == 0 else "yellow",
    ))

    # Cleanup shared architect session
    global _architect
    if _architect is not None:
        await _architect.close()
        _architect = None

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Enrich a generated module with Codex model output."
    )
    parser.add_argument("module_dir", help="Path to the module directory")
    parser.add_argument("--rag", action="store_true",
                        help="Enable RAG-sourced PDF context (Tier 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show enrichment plan without modifying files")

    args = parser.parse_args()
    asyncio.run(enrich_module(args.module_dir, use_rag=args.rag, dry_run=args.dry_run))


if __name__ == "__main__":
    main()

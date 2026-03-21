"""
codex.bots.fitd_dispatch
========================
Shared FITD command dispatcher for Discord and Telegram bots.

Provides scene navigation, FITD dice (action roll + resist), job tracking,
NPC conversations, recap, and trace — without requiring Rich Console or
LoopContext.

Returns plain text strings suitable for bot message replies, or None if
the command is unhandled (caller should fall through to bridge.step()).
"""

from __future__ import annotations

import random
from typing import Any, Optional


# ── Always-available commands (no module/scene needed) ────────────────────


def _cmd_roll(engine: Any, args: str) -> str:
    """FITD action roll."""
    if not args:
        return "Usage: roll <action>\nExample: roll prowl"
    action = args.split()[0].lower()
    try:
        result = engine.handle_command("roll_action", action=action)
        return f"--- Roll: {action} ---\n{result}"
    except Exception as e:
        return f"Roll failed: {e}"


def _cmd_resist(engine: Any, args: str) -> str:
    """FITD resistance roll — 2d6, deduct stress."""
    action = args.split()[0].lower() if args else "resist"
    stress_clock = getattr(engine, 'stress_clock', None)
    if stress_clock is None and hasattr(engine, 'party') and engine.party:
        stress_clock = getattr(engine.party[0], 'stress_clock', None)
    if stress_clock is None:
        return "No stress clock available for this engine."

    dice = [random.randint(1, 6) for _ in range(2)]
    sixes = dice.count(6)
    stress_cost = max(0, 6 - sixes)
    result = stress_clock.resist(stress_cost)
    dice_str = ", ".join(str(d) for d in dice)
    lines = [
        f"--- Resist: {action} ---",
        f"Dice: [{dice_str}]  Sixes: {sixes}  Stress cost: {stress_cost}",
        f"Stress: {result['new_stress']}/{stress_clock.max_stress}",
    ]
    if result.get("trauma_triggered"):
        lines.append(
            f"TRAUMA: {result['new_trauma']} — stress cleared, trauma gained."
        )
    if result.get("broken"):
        lines.append("You are BROKEN (4 traumas).")
    return "\n".join(lines)


def _cmd_fitd_status(engine: Any, args: str) -> str:
    """FITD party status — stress, harm, playbook, crew info."""
    lines = [f"--- {getattr(engine, 'display_name', 'FITD')} Status ---"]
    party = getattr(engine, 'party', [])
    if not party:
        lines.append("No characters in party.")
    for char in party:
        name = getattr(char, 'name', '?')
        playbook = getattr(char, 'playbook', '')
        stress = getattr(char, 'stress', 0)
        stress_max = 9
        sc = getattr(char, 'stress_clock', None)
        if sc:
            stress = sc.current
            stress_max = sc.max_stress
        trauma = getattr(char, 'trauma', 0)
        harm = getattr(char, 'harm', [])
        armor = getattr(char, 'armor', 0)
        lines.append(f"  {name} ({playbook})")
        lines.append(f"    Stress: {stress}/{stress_max}  Trauma: {trauma}  Armor: {armor}")
        if harm:
            lines.append(f"    Harm: {harm}")

    # Crew info
    crew_name = getattr(engine, 'crew_name', '')
    if crew_name:
        lines.append(f"\n  Crew: {crew_name}")
        for attr in ('heat', 'wanted_level', 'rep', 'coin', 'turf'):
            val = getattr(engine, attr, None)
            if val is not None:
                lines.append(f"    {attr.replace('_', ' ').title()}: {val}")
    return "\n".join(lines)


def _cmd_recap(engine: Any, args: str) -> str:
    """Session recap from memory shards."""
    shards = getattr(engine, "_memory_shards", None)
    if not shards:
        return "No narrative shards recorded yet."
    try:
        from codex.core.services.narrative_loom import synthesize_narrative
        return f"--- Session Recap ---\n{synthesize_narrative('Session recap', shards)}"
    except Exception as e:
        # Fallback: show last 5 shards raw
        recent = shards[-5:]
        lines = ["--- Recent Events ---"]
        for s in recent:
            lines.append(f"  * {s}" if isinstance(s, str) else f"  * {s}")
        return "\n".join(lines)


def _cmd_trace(engine: Any, args: str) -> str:
    """Trace a narrative fact through memory shard layers."""
    if not args:
        return "Usage: trace <fact>"
    try:
        result = engine.trace_fact(args)
        return str(result)
    except AttributeError:
        return "This engine does not support fact tracing."
    except Exception as e:
        return f"Trace failed: {e}"


# ── Scene-dependent commands (require scene_state) ───────────────────────


def _cmd_scene_look(scene_state: Any, args: str) -> str:
    """Show current scene."""
    scene = scene_state.current_scene()
    if not scene:
        return "No scene loaded."
    idx = scene_state.scene_idx + 1
    count = scene_state.scene_count()
    text = scene_state.format_scene(scene)
    return f"--- Scene {idx}/{count} ---\n{text}"


def _cmd_scene_next(scene_state: Any, args: str) -> str:
    """Advance to next scene."""
    if scene_state.talking_to:
        scene_state.exit_conversation()
    scene = scene_state.advance_scene()
    if scene is None:
        count = scene_state.scene_count()
        lines = [f"--- Zone Complete! ---", f"All {count} scenes visited."]
        if not scene_state.zm.module_complete:
            if scene_state.advance_zone():
                scene = scene_state.current_scene()
                if scene:
                    chapter = getattr(scene_state.zm, 'chapter_name', 'Next Chapter')
                    lines.append(f"\n--- {chapter} — Scene 1 ---")
                    lines.append(scene_state.format_scene(scene))
            else:
                module_name = getattr(scene_state.zm, 'module_name', 'Module')
                lines.append(f"\nMODULE COMPLETE! {module_name} finished!")
        return "\n".join(lines)
    else:
        idx = scene_state.scene_idx + 1
        count = scene_state.scene_count()
        text = scene_state.format_scene(scene)
        return f"--- Scene {idx}/{count} ---\n{text}"


def _cmd_scenes(scene_state: Any, args: str) -> str:
    """List all scenes with visited markers."""
    lines = [f"--- Scenes: {getattr(scene_state.zm, 'zone_name', 'Zone')} ---"]
    for i, (rid, rnode) in enumerate(scene_state.scene_list):
        marker = ">" if i == scene_state.scene_idx else " "
        visited = " [VISITED]" if rid in scene_state.visited else ""
        rtype = getattr(rnode, 'room_type', '')
        rtype_str = f" ({rtype.name})" if hasattr(rtype, 'name') else ""
        lines.append(f" {marker} Scene {i + 1}{rtype_str}{visited}")
    return "\n".join(lines)


def _cmd_talk(scene_state: Any, engine: Any, args: str) -> str:
    """Talk to an NPC or list NPCs in current scene."""
    scene = scene_state.current_scene()
    if not scene:
        return "No scene loaded."
    npcs = scene.npcs if hasattr(scene, 'npcs') else scene.get("npcs", [])
    if not npcs:
        return "No NPCs in this scene."

    if not args:
        lines = ["NPCs in this scene:"]
        for npc in npcs:
            name = npc.name if hasattr(npc, 'name') else npc.get("name", "Unknown")
            role = npc.role if hasattr(npc, 'role') else npc.get("role", "")
            role_str = f" ({role})" if role else ""
            lines.append(f"  * {name}{role_str}")
        return "\n".join(lines)

    target = args.lower()
    for npc in npcs:
        name = npc.name if hasattr(npc, 'name') else npc.get("name", "Unknown")
        if target in name.lower():
            dialogue = npc.dialogue if hasattr(npc, 'dialogue') else npc.get("dialogue", "")
            role = npc.role if hasattr(npc, 'role') else npc.get("role", "")
            npc_dict = npc if isinstance(npc, dict) else {
                "name": name, "role": role,
                "dialogue": dialogue,
                "notes": getattr(npc, 'notes', '') or '',
            }
            lines = [f"--- {name} ---"]
            if role:
                lines.append(f"Role: {role}")
            if dialogue:
                lines.append(f'"{dialogue}"')
            else:
                lines.append(f"{name} has nothing to say.")
            scene_state.enter_conversation(name, npc_dict)
            lines.append("\nChat freely or type 'bye' to end.")
            if "quest" in role.lower() or "fixer" in role.lower():
                scene_state.pending_offer = {
                    "title": dialogue[:60] if dialogue else f"Job from {name}",
                    "npc": name,
                    "scene_idx": scene_state.scene_idx,
                }
                lines.append("Type 'accept' to take this job.")
            return "\n".join(lines)
    return f"No NPC named '{args}' in this scene."


def _cmd_accept(scene_state: Any, args: str) -> str:
    """Accept a pending job offer."""
    if scene_state.pending_offer:
        job = scene_state.pending_offer
        scene_state.accepted_jobs.append(job)
        scene_state.pending_offer = None
        return f"Job Accepted: {job['title']}"
    return "No pending job offer."


def _cmd_jobs(scene_state: Any, args: str) -> str:
    """List accepted jobs."""
    if not scene_state.accepted_jobs:
        return "No jobs accepted yet."
    lines = ["--- Accepted Jobs ---"]
    for i, job in enumerate(scene_state.accepted_jobs, 1):
        lines.append(f"  {i}. {job['title']} (from {job.get('npc', '?')})")
    return "\n".join(lines)


def _cmd_services(scene_state: Any, args: str) -> str:
    """List services in current scene."""
    scene = scene_state.current_scene()
    if not scene:
        return "No scene loaded."
    services = scene.services if hasattr(scene, 'services') else scene.get("services", [])
    if not services:
        return "No services available in this scene."
    lines = ["--- Available Services ---"]
    for svc in services:
        lines.append(f"  * {svc}")
    return "\n".join(lines)


def _cmd_investigate(engine: Any, scene_state: Any, args: str) -> str:
    """Roll a study action to investigate the scene."""
    try:
        result = engine.handle_command("roll_action", action="study")
        return f"--- Investigation ---\n{result}"
    except Exception as e:
        return f"Investigation failed: {e}"


# ── Conversation mode ────────────────────────────────────────────────────


def _conversation_intercept(
    scene_state: Any,
    engine: Any,
    verb: str,
    full_text: str,
) -> str:
    """Handle input while in NPC conversation mode."""
    if verb in ("bye", "leave", "goodbye"):
        name = scene_state.exit_conversation()
        return f"You end your conversation with {name}."

    if verb == "accept" and scene_state.pending_offer:
        return _cmd_accept(scene_state, "")

    # Free-form NPC dialogue — try Mimir if available, else generic
    npc_name = scene_state.talking_to
    npc_data = scene_state._talking_to_npc or {}
    try:
        from codex.integrations.mimir import query_npc_dialogue
        result = query_npc_dialogue(
            npc_name, full_text, npc_data,
            system_id=getattr(engine, 'system_id', 'fitd'),
        )
        return f'{npc_name}: "{result}"'
    except Exception:
        role = npc_data.get("role", "")
        return f'{npc_name} considers your words. ({role or "NPC"})'


# ── Main dispatcher ──────────────────────────────────────────────────────


def dispatch_fitd_command(
    verb: str,
    args: str,
    engine: Any,
    bridge: Any = None,
    scene_state: Any = None,
) -> Optional[str]:
    """Process FITD-specific commands, return text or None.

    Args:
        verb: First word of command (lowercased).
        args: Remaining text after verb.
        engine: Active FITD engine (NarrativeEngineBase subclass).
        bridge: UniversalGameBridge instance (for fallback).
        scene_state: _FITDSceneState or None.

    Returns:
        Formatted text response, or None if command is unhandled
        (caller should fall through to bridge.step()).
    """
    if not engine:
        return None

    # Conversation mode intercept — must check first
    if scene_state and scene_state.talking_to:
        return _conversation_intercept(
            scene_state, engine, verb, f"{verb} {args}".strip(),
        )

    # Always-available FITD commands
    _ALWAYS = {
        "roll": _cmd_roll,
        "resist": _cmd_resist,
        "fitd_status": _cmd_fitd_status,
        "recap": _cmd_recap,
        "trace": _cmd_trace,
    }
    handler = _ALWAYS.get(verb)
    if handler:
        return handler(engine, args)

    # Scene-dependent commands
    if scene_state:
        _SCENE = {
            "scene": _cmd_scene_look,
            "next": _cmd_scene_next,
            "scenes": _cmd_scenes,
            "accept": _cmd_accept,
            "jobs": _cmd_jobs,
            "journal": _cmd_jobs,
            "services": _cmd_services,
        }
        scene_handler = _SCENE.get(verb)
        if scene_handler:
            return scene_handler(scene_state, args)

        if verb == "talk" or verb == "npc":
            return _cmd_talk(scene_state, engine, args)

        if verb == "investigate":
            return _cmd_investigate(engine, scene_state, args)

    return None

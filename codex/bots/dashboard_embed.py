"""
codex.bots.dashboard_embed
============================
Text-formatted DM Dashboard renderer for Discord and Telegram bots.

Converts VitalsSchema + DMDashboard state into plain text blocks
suitable for bot messages. No Rich dependency.
"""

from __future__ import annotations

from typing import Any, Optional


def format_dashboard_text(vitals, dashboard=None, engine=None) -> str:
    """Render a full dashboard view as plain text.

    Args:
        vitals: VitalsSchema from get_vitals()
        dashboard: Optional DMDashboard instance (for conditions, initiative, etc.)
        engine: Optional engine for enemy data

    Returns:
        Multi-line plain text string (under 4000 chars for Telegram safety).
    """
    sections = []
    sections.append(_format_world(vitals, engine))
    sections.append(_format_table(vitals, dashboard))
    sections.append(_format_intel(dashboard))
    return "\n".join(sections)


def _format_resource_bar(name: str, current: int, max_val: int, width: int = 15) -> str:
    """Simple text resource bar."""
    if max_val <= 0:
        return f"{name}: {current}"
    filled = int((current / max_val) * width)
    bar = "#" * filled + "." * (width - filled)
    return f"{name}: [{bar}] {current}/{max_val}"


def _format_world(vitals, engine=None) -> str:
    """World panel: system, location, enemies, exits."""
    lines = [f"=== {vitals.system_name} ==="]

    if vitals.zone_name:
        lines.append(f"Zone: {vitals.zone_name}")
    if vitals.chapter_name:
        lines.append(f"Chapter: {vitals.chapter_name}")
    if vitals.module_name:
        lines.append(f"Module: {vitals.module_name}")

    extra = vitals.extra
    room_id = extra.get("room_id")
    if room_id is not None:
        lines.append(f"Room: {room_id}")

    # Exits
    exits = extra.get("exits", [])
    if exits:
        exit_strs = []
        for e in exits:
            if isinstance(e, dict):
                exit_strs.append(f"{e.get('direction', '?')}")
            else:
                exit_strs.append(str(e))
        lines.append(f"Exits: {', '.join(exit_strs)}")

    # Enemies
    if engine and room_id is not None:
        pop = getattr(engine, 'populated_rooms', {}).get(room_id)
        if pop:
            content = pop.content if hasattr(pop, 'content') else pop
            enemies = content.get("enemies", []) if isinstance(content, dict) else []
            if enemies:
                lines.append("")
                lines.append("Enemies:")
                for e in enemies:
                    name = e.get("name", "?")
                    hp = e.get("hp", "?")
                    max_hp = e.get("max_hp", hp)
                    defense = e.get("defense", e.get("ac", "?"))
                    alive = e.get("alive", True)
                    marker = "" if alive else " [DEAD]"
                    lines.append(f"  {name} HP:{hp}/{max_hp} DEF:{defense}{marker}")

    # System-specific
    if vitals.system_tag == "CROWN":
        lines.append(f"Patron: {extra.get('patron', '?')}")
        lines.append(f"Leader: {extra.get('leader', '?')}")
    elif vitals.system_tag == "BITD":
        lines.append(f"Crew: {extra.get('crew_name', '?')}")

    return "\n".join(lines)


def _format_table(vitals, dashboard=None) -> str:
    """Table panel: resources, party, conditions, initiative."""
    lines = [""]

    # Resource bars
    lines.append(_format_resource_bar(
        vitals.primary_resource, vitals.primary_current, vitals.primary_max))
    if vitals.secondary_resource:
        lines.append(_format_resource_bar(
            vitals.secondary_resource, vitals.secondary_current, vitals.secondary_max))

    # Party
    if vitals.party:
        lines.append("")
        lines.append("Party:")
        for m in vitals.party:
            alive = "+" if m.get("alive", True) else "x"
            name = m.get("name", "?")
            hp = m.get("hp", 0)
            max_hp = m.get("max_hp", 0)
            extra_info = ""
            if "class" in m:
                extra_info = f" L{m.get('level', 1)} {m['class']}"
            elif "playbook" in m:
                extra_info = f" {m['playbook']} S:{m.get('stress', 0)}"
            elif "order" in m:
                extra_info = f" {m['order']}"
            lines.append(f"  [{alive}] {name}{extra_info} HP:{hp}/{max_hp}")

    if not dashboard:
        return "\n".join(lines)

    # Conditions
    entities = dashboard.conditions.get_all_entities()
    if entities:
        lines.append("")
        lines.append("Conditions:")
        for entity in entities:
            conds = dashboard.conditions.get_conditions(entity)
            cond_strs = [f"{c.condition_type.value}({c.duration})" for c in conds]
            lines.append(f"  {entity}: {', '.join(cond_strs)}")

    # Initiative
    order = dashboard.initiative.get_order()
    if order:
        current = dashboard.initiative.current()
        lines.append("")
        lines.append(f"Initiative (R{dashboard.initiative.round_number}):")
        for name in order:
            marker = ">" if current and name == current.name else " "
            lines.append(f"  {marker} {name}")

    # D&D 5e: Concentration
    if vitals.system_tag == "DND5E":
        conc = dashboard.concentration.get_concentrating()
        if conc:
            lines.append("")
            lines.append("Concentration:")
            for caster, spell in conc.items():
                lines.append(f"  {caster}: {spell}")
        dying = dashboard.death_saves.list_dying()
        if dying != "No characters making death saves.":
            lines.append("")
            lines.append(dying)

    # BITD crew
    extra = vitals.extra
    if vitals.system_tag == "BITD":
        lines.append("")
        lines.append(
            f"Wanted: {extra.get('wanted_level', 0)} | "
            f"Rep: {extra.get('rep', 0)} | "
            f"Coin: {extra.get('coin', 0)}")

    return "\n".join(lines)


def _format_intel(dashboard=None) -> str:
    """Intel panel: notes, quests, timer."""
    if not dashboard:
        return ""
    lines = [""]

    # Timer
    if dashboard.timer.running:
        lines.append(f"Session: {dashboard.timer.elapsed_str()}")

    # Notes (last 3)
    if dashboard._notes:
        lines.append("")
        lines.append("Notes:")
        for note in dashboard._notes[-3:]:
            lines.append(f"  * {note}")

    # Quests
    quest_summary = dashboard.quests.active_summary(3)
    if quest_summary != "No active quests.":
        lines.append("")
        lines.append("Quests:")
        lines.append(quest_summary)

    return "\n".join(lines)

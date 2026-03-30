"""
codex.core.dm_dashboard — DM Live Dashboard
=============================================

3-panel Rich terminal UI for DM monitoring across all engine families.

Architecture:
  - VitalsSchema: Universal adapter normalizing engine state
  - 5 adapter functions (one per engine family)
  - DMDashboard: 3-panel Layout (World | Table | Intelligence)
  - Command dispatch to DM tools + mechanics modules
  - Broadcast event subscription for Intelligence panel

Renders using clear-and-reprint (same pattern as play_burnwillow.py
and play_player_view.py — no Live/async).

WO-V34.0: The Sovereign Dashboard — Gaps #3, #4, #10
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


# =========================================================================
# VITALS SCHEMA — Universal Engine Adapter
# =========================================================================

@dataclass
class VitalsSchema:
    """Normalizes vitals from ANY engine into a common rendering schema."""
    system_name: str            # "Burnwillow", "Crown & Crew", etc.
    system_tag: str             # "BURNWILLOW", "CROWN", "BITD", "DND5E", "STC"
    primary_resource: str       # "HP", "Stress", "Focus", "Sway"
    primary_current: int = 0
    primary_max: int = 0
    secondary_resource: str = ""  # "Doom", "Heat", "Day", ""
    secondary_current: int = 0
    secondary_max: int = 0
    party: List[dict] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    # WO-V40.0: Module/zone context for spatial wiring
    module_name: str = ""
    chapter_name: str = ""
    zone_name: str = ""
    zone_progress: str = ""


# =========================================================================
# ADAPTER FUNCTIONS — One per engine family
# =========================================================================

def vitals_from_burnwillow(engine) -> VitalsSchema:
    """Adapt BurnwillowEngine to VitalsSchema."""
    char = engine.character
    party = []
    for c in getattr(engine, 'party', []):
        party.append({
            "name": c.name,
            "hp": c.current_hp,
            "max_hp": c.max_hp,
            "alive": c.is_alive(),
        })

    doom_current = 0
    if hasattr(engine, 'doom_clock'):
        doom_current = engine.doom_clock.current

    extra = {
        "room_id": getattr(engine, 'current_room_id', None),
        "doom_thresholds": [5, 10, 15, 20],
    }
    if char and hasattr(char, 'gear'):
        gear = char.gear
        if gear:
            equipped = []
            for slot, item in gear.slots.items():
                if item:
                    equipped.append(f"{slot.value}: {item.name}")
            extra["gear"] = equipped

    exits = engine.get_cardinal_exits() if hasattr(engine, 'get_cardinal_exits') else []
    extra["exits"] = exits

    return VitalsSchema(
        system_name="Burnwillow",
        system_tag="BURNWILLOW",
        primary_resource="HP",
        primary_current=char.current_hp if char else 0,
        primary_max=char.max_hp if char else 0,
        secondary_resource="Doom",
        secondary_current=doom_current,
        secondary_max=20,
        party=party,
        extra=extra,
    )


def vitals_from_crown(engine) -> VitalsSchema:
    """Adapt CrownAndCrewEngine to VitalsSchema."""
    alignment = "NEUTRAL"
    if hasattr(engine, 'get_alignment'):
        alignment = engine.get_alignment()

    extra = {
        "alignment": alignment,
        "patron": getattr(engine, 'patron', ''),
        "leader": getattr(engine, 'leader', ''),
        "arc_length": getattr(engine, 'arc_length', 5),
    }
    if hasattr(engine, 'dna'):
        extra["dna"] = dict(engine.dna)

    return VitalsSchema(
        system_name="Crown & Crew",
        system_tag="CROWN",
        primary_resource="Sway",
        primary_current=getattr(engine, 'sway', 0),
        primary_max=3,
        secondary_resource="Day",
        secondary_current=getattr(engine, 'day', 1),
        secondary_max=getattr(engine, 'arc_length', 5),
        party=[],
        extra=extra,
    )


def vitals_from_bitd(engine) -> VitalsSchema:
    """Adapt BitDEngine to VitalsSchema."""
    party = []
    for char in getattr(engine, 'party', []):
        clock = engine.stress_clocks.get(char.name)
        stress = clock.current_stress if clock else 0
        max_stress = clock.max_stress if clock else 9
        party.append({
            "name": char.name,
            "hp": max_stress - stress,  # "health" = remaining stress capacity
            "max_hp": max_stress,
            "alive": True,
            "stress": stress,
            "playbook": char.playbook,
        })

    extra = {
        "crew_name": getattr(engine, 'crew_name', ''),
        "crew_type": getattr(engine, 'crew_type', ''),
        "wanted_level": getattr(engine, 'wanted_level', 0),
        "rep": getattr(engine, 'rep', 0),
        "coin": getattr(engine, 'coin', 0),
        "turf": getattr(engine, 'turf', 0),
    }

    return VitalsSchema(
        system_name="Blades in the Dark",
        system_tag="BITD",
        primary_resource="Stress",
        primary_current=engine.stress_clocks[engine.party[0].name].current_stress
        if engine.party and engine.party[0].name in engine.stress_clocks else 0,
        primary_max=9,
        secondary_resource="Heat",
        secondary_current=getattr(engine, 'heat', 0),
        secondary_max=9,
        party=party,
        extra=extra,
    )


def vitals_from_dnd5e(engine) -> VitalsSchema:
    """Adapt DnD5eEngine to VitalsSchema."""
    char = engine.character
    party = []
    for c in getattr(engine, 'party', []):
        party.append({
            "name": c.name,
            "hp": c.current_hp,
            "max_hp": c.max_hp,
            "alive": c.is_alive(),
            "level": c.level,
            "class": c.character_class,
            "ac": c.armor_class,
            "xp": getattr(c, 'xp', 0),
        })

    extra = {
        "room_id": getattr(engine, 'current_room_id', None),
        "exits": engine.get_cardinal_exits() if hasattr(engine, 'get_cardinal_exits') else [],
    }
    if char:
        extra["ability_scores"] = {
            "STR": char.strength, "DEX": char.dexterity,
            "CON": char.constitution, "INT": char.intelligence,
            "WIS": char.wisdom, "CHA": char.charisma,
        }
        extra["proficiency"] = char.proficiency_bonus

    return VitalsSchema(
        system_name="D&D 5th Edition",
        system_tag="DND5E",
        primary_resource="HP",
        primary_current=char.current_hp if char else 0,
        primary_max=char.max_hp if char else 0,
        secondary_resource="AC",
        secondary_current=char.armor_class if char else 10,
        secondary_max=25,
        party=party,
        extra=extra,
    )


def vitals_from_cosmere(engine) -> VitalsSchema:
    """Adapt CosmereEngine to VitalsSchema."""
    char = engine.character
    party = []
    for c in getattr(engine, 'party', []):
        party.append({
            "name": c.name,
            "hp": c.current_hp,
            "max_hp": c.max_hp,
            "alive": c.is_alive(),
            "order": c.order,
            "focus": c.focus,
            "ideal_level": getattr(c, 'ideal_level', 1),
        })

    extra = {
        "room_id": getattr(engine, 'current_room_id', None),
        "exits": engine.get_cardinal_exits() if hasattr(engine, 'get_cardinal_exits') else [],
    }
    if char:
        extra["order"] = char.order
        extra["surges"] = char.get_surges()
        extra["defense"] = char.defense

    return VitalsSchema(
        system_name="Cosmere RPG",
        system_tag="STC",
        primary_resource="HP",
        primary_current=char.current_hp if char else 0,
        primary_max=char.max_hp if char else 0,
        secondary_resource="Focus",
        secondary_current=char.focus if char else 0,
        secondary_max=10,
        party=party,
        extra=extra,
    )


def get_vitals(engine, system_tag: str) -> VitalsSchema:
    """Dispatch to the correct adapter function."""
    adapters = {
        "BURNWILLOW": vitals_from_burnwillow,
        "CROWN": vitals_from_crown,
        "BITD": vitals_from_bitd,
        "SAV": vitals_from_bitd,
        "BOB": vitals_from_bitd,
        "CANDELA": vitals_from_bitd,
        "CBRPNK": vitals_from_bitd,
        "DND5E": vitals_from_dnd5e,
        "STC": vitals_from_cosmere,
    }
    adapter = adapters.get(system_tag.upper())
    if adapter:
        vitals = adapter(engine)
    else:
        # Fallback
        vitals = VitalsSchema(
            system_name=system_tag,
            system_tag=system_tag.upper(),
            primary_resource="HP",
        )
    # WO-V40.0: Inject zone context from engine's ZoneManager (if present)
    zm = getattr(engine, "zone_manager", None)
    if zm is not None and not zm.module_complete:
        vitals.module_name = zm.module_name
        vitals.chapter_name = zm.chapter_name
        vitals.zone_name = zm.zone_name
        vitals.zone_progress = zm.zone_progress
    return vitals


# =========================================================================
# DM DASHBOARD — 3-Panel Layout
# =========================================================================

class DMDashboard:
    """3-panel Rich terminal dashboard for DM monitoring.

    Layout:
    ┌──────────────┬──────────────┬──────────────┐
    │  THE WORLD   │  THE TABLE   │ INTELLIGENCE │
    ├──────────────┴──────────────┴──────────────┤
    │  DM> [command input]                       │
    └────────────────────────────────────────────┘
    """

    def __init__(self, console: Console, system_tag: str, core=None):
        self.console = console
        self.system_tag = system_tag.upper()
        self._notes: List[str] = []
        self._event_log: List[str] = []
        self._last_query: str = ""
        self._broadcast = None
        self.core = core  # Optional reference to the running Codex core/app object

        # Subscribe to broadcast events
        try:
            from codex.core.services.broadcast import GlobalBroadcastManager
            self._broadcast = GlobalBroadcastManager(system_theme=system_tag.lower())
            for event_type in [
                "MAP_UPDATE", "HIGH_IMPACT_DECISION", "TRAIT_ACTIVATED",
                "FACTION_CLOCK_TICK", "CIVIC_EVENT", "RAG_INDEX_INVALIDATED",
            ]:
                self._broadcast.subscribe(event_type, self._on_broadcast)
        except ImportError:
            pass

        # Mechanics modules
        from codex.core.mechanics.conditions import ConditionTracker
        from codex.core.mechanics.initiative import InitiativeTracker
        from codex.core.mechanics.rest import RestManager
        from codex.core.mechanics.progression import ProgressionTracker

        self.conditions = ConditionTracker()
        self.initiative = InitiativeTracker()
        self.rest_mgr = RestManager()
        self.progression: Optional[ProgressionTracker] = None

        # Quest tracker
        from codex.core.mechanics.quest import QuestTracker
        self.quests = QuestTracker()

        # NPC tracker
        from codex.core.mechanics.npc_tracker import NPCTracker
        self.npc_tracker = NPCTracker()

        # Session timer
        from codex.core.mechanics.session_timer import SessionTimer
        self.timer = SessionTimer()
        self.timer.start()

        # Session log
        from codex.core.mechanics.session_log import SessionLog
        self.session_log = SessionLog()

        # D&D 5e specific
        from codex.core.mechanics.concentration import ConcentrationTracker
        from codex.core.mechanics.death_saves import DeathSaveTracker
        self.concentration = ConcentrationTracker()
        self.death_saves = DeathSaveTracker()

        # Rules quick-reference
        self._rules_data = self._load_rules_reference()

        # Companion
        self.companion = None

    def _on_broadcast(self, payload: dict) -> None:
        """Push broadcast events to the event log."""
        source = payload.get("_source_module", "system")
        event = payload.get("event_type", payload.get("type", "event"))
        msg = f"[{source}] {event}"
        self._event_log.append(msg)
        if len(self._event_log) > 20:
            self._event_log = self._event_log[-20:]

    def _load_rules_reference(self) -> dict:
        """Load rules reference from config/rules/."""
        import json
        from pathlib import Path
        rules_dir = Path(__file__).resolve().parent.parent.parent / "config" / "rules"
        data = {}
        # Load universal rules
        universal = rules_dir / "universal.json"
        if universal.exists():
            try:
                data.update(json.loads(universal.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        # Load system-specific overlay
        family = "fitd" if self.system_tag in (
            "BITD", "SAV", "BOB", "CBRPNK", "CANDELA"
        ) else self.system_tag.lower()
        system_file = rules_dir / f"{family}.json"
        if system_file.exists():
            try:
                data.update(json.loads(system_file.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return data

    def _format_rules_lookup(self, topic: str = "") -> str:
        """Format rules reference for display."""
        if not self._rules_data:
            return "No rules reference data loaded."
        topic = topic.strip().lower()
        if not topic:
            sections = list(self._rules_data.keys())
            return "Rules topics: " + ", ".join(sections) + "\nUsage: rules <topic>"
        # Find matching section
        for key, value in self._rules_data.items():
            if topic in key.lower():
                if isinstance(value, dict):
                    lines = [f"--- {key} ---"]
                    for k, v in value.items():
                        lines.append(f"  {k}: {v}")
                    return "\n".join(lines)
                return f"--- {key} ---\n{value}"
        return f"No rules found for '{topic}'. Topics: {', '.join(self._rules_data.keys())}"

    def _get_room_enemies(self, engine, room_id) -> list:
        """Extract enemy data from current room for stat display."""
        pop = getattr(engine, 'populated_rooms', {}).get(room_id)
        if not pop:
            return []
        content = pop.content if hasattr(pop, 'content') else pop
        if isinstance(content, dict):
            return content.get("enemies", [])
        return []

    def _format_enemy_stat_line(self, enemy: dict) -> str:
        """Compact 1-liner for enemy in combat panel."""
        name = enemy.get("name", "Unknown")
        hp = enemy.get("hp", "?")
        max_hp = enemy.get("max_hp", hp)
        defense = enemy.get("defense", enemy.get("ac", "?"))
        damage = enemy.get("damage", enemy.get("attack", "?"))
        special = enemy.get("special", "")
        alive = enemy.get("alive", True)
        marker = "" if alive else " [DEAD]"
        line = f"{name} HP:{hp}/{max_hp} DEF:{defense} DMG:{damage}"
        if special:
            line += f" ({special})"
        return line + marker

    # ─── Panel Builders ────────────────────────────────────────────────

    def _build_world_panel(self, vitals: VitalsSchema, engine=None) -> Panel:
        """Left panel: system, location, enemies, exits."""
        text = Text()
        text.append(f"{vitals.system_name}\n", style="bold cyan")
        text.append(f"[{vitals.system_tag}]\n\n", style="dim")

        # Room / Location
        room_id = vitals.extra.get("room_id")
        if room_id is not None:
            text.append(f"Room: {room_id}\n", style="white")

            # Room description
            if engine and hasattr(engine, 'populated_rooms'):
                pop_room = engine.populated_rooms.get(room_id)
                if pop_room and hasattr(pop_room, 'content'):
                    desc = pop_room.content.get("description", "")
                    if desc:
                        text.append(f"{desc[:80]}...\n" if len(desc) > 80 else f"{desc}\n",
                                    style="dim white")

                    # Enemies
                    enemies = pop_room.content.get("enemies", [])
                    if enemies:
                        text.append("\nEnemies:\n", style="bold red")
                        for e in enemies:
                            hp = e.get("hp", "?")
                            text.append(f"  {e.get('name', '?')} (HP: {hp})\n",
                                        style="red")

                    # Loot
                    loot = pop_room.content.get("loot", [])
                    if loot:
                        text.append("\nLoot:\n", style="bold yellow")
                        for l in loot:
                            text.append(f"  {l.get('name', '?')}\n", style="yellow")

                    # Hazards
                    hazards = pop_room.content.get("hazards", [])
                    if hazards:
                        text.append("\nHazards:\n", style="bold magenta")
                        for h in hazards:
                            text.append(f"  {h.get('name', '?')}\n", style="magenta")

        # Crown-specific
        if vitals.system_tag == "CROWN":
            text.append(f"\nPatron: {vitals.extra.get('patron', '?')}\n", style="white")
            text.append(f"Leader: {vitals.extra.get('leader', '?')}\n", style="white")
            text.append(f"Alignment: {vitals.extra.get('alignment', '?')}\n", style="bold")

        # Exits
        exits = vitals.extra.get("exits", [])
        if exits:
            text.append("\nExits: ", style="green")
            exit_strs = [f"{e.get('direction', '?')}→R{e.get('id', '?')}" for e in exits]
            text.append(", ".join(exit_strs) + "\n", style="green")

        return Panel(text, title="[bold]THE WORLD[/bold]", box=box.ROUNDED,
                     border_style="cyan", height=20)

    def _build_table_panel(self, vitals: VitalsSchema, engine=None) -> Panel:
        """Center panel: party vitals, resources, conditions, initiative, enemies."""
        text = Text()

        # Primary resource bar
        text.append(f"{vitals.primary_resource}: ", style="bold")
        bar_len = 20
        if vitals.primary_max > 0:
            filled = int((vitals.primary_current / vitals.primary_max) * bar_len)
        else:
            filled = 0
        text.append("█" * filled, style="green")
        text.append("░" * (bar_len - filled), style="dim")
        text.append(f" {vitals.primary_current}/{vitals.primary_max}\n", style="white")

        # Secondary resource
        if vitals.secondary_resource:
            text.append(f"{vitals.secondary_resource}: ", style="bold")
            if vitals.secondary_max > 0:
                filled = int((vitals.secondary_current / vitals.secondary_max) * bar_len)
            else:
                filled = 0
            color = "red" if vitals.secondary_resource == "Doom" else "blue"
            text.append("█" * filled, style=color)
            text.append("░" * (bar_len - filled), style="dim")
            text.append(f" {vitals.secondary_current}/{vitals.secondary_max}\n", style="white")

        # Party
        if vitals.party:
            text.append("\nParty:\n", style="bold")
            for member in vitals.party:
                alive = "●" if member.get("alive", True) else "✕"
                name = member.get("name", "?")
                hp = member.get("hp", 0)
                max_hp = member.get("max_hp", 0)
                style = "white" if member.get("alive", True) else "dim red"
                extra = ""
                if "class" in member:
                    extra = f" L{member.get('level', 1)} {member['class']}"
                elif "playbook" in member:
                    extra = f" {member['playbook']}"
                    hp_label = f"S:{member.get('stress', 0)}"
                elif "order" in member:
                    extra = f" {member['order']} I{member.get('ideal_level', 1)}"
                text.append(f"  {alive} {name}{extra} HP:{hp}/{max_hp}\n", style=style)

        # Conditions
        entities_with_conditions = self.conditions.get_all_entities()
        if entities_with_conditions:
            text.append("\nConditions:\n", style="bold magenta")
            for entity in entities_with_conditions:
                conds = self.conditions.get_conditions(entity)
                cond_strs = [f"{c.condition_type.value}({c.duration})" for c in conds]
                text.append(f"  {entity}: {', '.join(cond_strs)}\n", style="magenta")

        # Initiative
        order = self.initiative.get_order()
        if order:
            text.append(f"\nInitiative (R{self.initiative.round_number}):\n", style="bold yellow")
            current = self.initiative.current()
            for i, name in enumerate(order):
                marker = "►" if current and name == current.name else " "
                text.append(f"  {marker} {name}\n", style="yellow")

        # System-specific extras
        extra = vitals.extra
        if vitals.system_tag == "BITD":
            text.append(f"\nCrew: {extra.get('crew_name', '?')}\n", style="white")
            text.append(f"Wanted: {extra.get('wanted_level', 0)} | "
                        f"Rep: {extra.get('rep', 0)} | "
                        f"Coin: {extra.get('coin', 0)}\n", style="white")

        # D&D 5e: Concentration tracking
        if vitals.system_tag == "DND5E":
            conc = self.concentration.get_concentrating()
            if conc:
                text.append("\nConcentration:\n", style="bold blue")
                for caster, spell in conc.items():
                    text.append(f"  {caster}: {spell}\n", style="blue")

            # Death saves
            dying_text = self.death_saves.list_dying()
            if dying_text != "No characters making death saves.":
                text.append(f"\n{dying_text}\n", style="bold red")

        # Enemies in combat
        room_id = vitals.extra.get("room_id")
        if engine and room_id is not None:
            enemies = self._get_room_enemies(engine, room_id)
            if enemies:
                text.append("\nEnemies:\n", style="bold red")
                for enemy in enemies:
                    text.append(f"  {self._format_enemy_stat_line(enemy)}\n", style="red")

        return Panel(text, title="[bold]THE TABLE[/bold]", box=box.ROUNDED,
                     border_style="green", height=20)

    def _build_intel_panel(self) -> Panel:
        """Right panel: notes, events, thermal, last query."""
        text = Text()

        # Session notes (last 5)
        text.append("Notes:\n", style="bold")
        if self._notes:
            for note in self._notes[-5:]:
                text.append(f"  • {note}\n", style="dim white")
        else:
            text.append("  (none)\n", style="dim")

        # Broadcast events (last 5)
        text.append("\nEvents:\n", style="bold")
        if self._event_log:
            for event in self._event_log[-5:]:
                text.append(f"  ▸ {event}\n", style="dim cyan")
        else:
            text.append("  (none)\n", style="dim")

        # Thermal status
        text.append("\nThermal: ", style="bold")
        try:
            from codex.core.cortex import Cortex
            cortex = Cortex()
            state = cortex.read_metabolic_state()
            text.append(f"{state.thermal_status.value}\n",
                        style="green" if state.metabolic_clearance else "red")
        except Exception:
            text.append("N/A\n", style="dim")

        # Last query result
        if self._last_query:
            text.append(f"\nLast Query:\n", style="bold")
            # Truncate to fit panel
            truncated = self._last_query[:200]
            if len(self._last_query) > 200:
                truncated += "..."
            text.append(f"  {truncated}\n", style="dim white")

        # Session timer
        if self.timer.running:
            elapsed = self.timer.elapsed_str()
            text.append(f"\nSession: {elapsed}", style="bold")
            pacing = self.timer.pacing_check()
            if pacing:
                text.append(f" ({pacing})", style="yellow")
            text.append("\n")

        # Active quests (last 5)
        quest_summary = self.quests.active_summary(5)
        if quest_summary != "No active quests.":
            text.append("\nQuests:\n", style="bold green")
            text.append(f"{quest_summary}\n", style="green")

        return Panel(text, title="[bold]INTELLIGENCE[/bold]", box=box.ROUNDED,
                     border_style="yellow", height=20)

    def _build_llm_stats_panel(self) -> Panel:
        """Right-most panel: live LLM session stats from Architect."""
        text = Text()

        # Resolve architect from core reference
        architect = None
        if self.core is not None:
            architect = getattr(self.core, "architect", None)

        if architect is None or not hasattr(architect, "session_stats"):
            text.append("[dim]No LLM data[/dim]")
            return Panel(text, title="[bold]LLM STATS[/bold]", box=box.ROUNDED,
                         border_style="cyan", height=20)

        s = architect.session_stats

        text.append("Session Totals:\n", style="bold")
        text.append(f"  Calls:    {s.total_calls}\n", style="white")
        text.append(f"  Tokens:   {s.total_tokens}\n", style="white")
        text.append(f"  Avg lat:  {s.avg_latency_ms:.0f} ms\n", style="white")
        text.append(f"  Errors:   {s.errors}\n",
                    style="red" if s.errors > 0 else "dim")

        text.append("\nLast Call:\n", style="bold")
        if s.total_calls > 0:
            text.append(f"  Model:    {s.last_model}\n", style="cyan")
            text.append(f"  Mode:     {s.last_mode}\n", style="cyan")
            text.append(f"  Latency:  {s.last_latency_ms:.0f} ms\n", style="cyan")
        else:
            text.append("  (none yet)\n", style="dim")

        # Config snapshot
        cfg = getattr(architect, "config", None)
        if cfg is not None:
            text.append("\nConfig:\n", style="bold")
            text.append(f"  Reflex:  {getattr(cfg, 'MODEL_REFLEX', '?')}\n", style="dim white")
            text.append(f"  Academy: {getattr(cfg, 'MODEL_ACADEMY', '?')}\n", style="dim white")

        return Panel(text, title="[bold]LLM STATS[/bold]", box=box.ROUNDED,
                     border_style="cyan", height=20)

    # ─── Rendering ─────────────────────────────────────────────────────

    def render(self, vitals: VitalsSchema, engine=None) -> Layout:
        """Build the full 3-panel layout."""
        layout = Layout()
        layout.split_column(
            Layout(name="main", ratio=4),
            Layout(name="footer", size=3),
        )
        layout["main"].split_row(
            Layout(self._build_world_panel(vitals, engine), name="world"),
            Layout(self._build_table_panel(vitals, engine), name="table"),
            Layout(self._build_intel_panel(), name="intel"),
            Layout(self._build_llm_stats_panel(), name="llm_stats"),
        )
        layout["footer"].update(
            Panel(
                Text.from_markup(f"[bold cyan]DM>[/bold cyan] Type a command (type 'help' for list)"),
                box=box.HORIZONTALS,
                border_style="dim",
            )
        )
        return layout

    # ─── Command Dispatch ──────────────────────────────────────────────

    def dispatch_command(self, cmd_str: str, engine=None) -> str:
        """Route a DM command to the appropriate handler."""
        parts = cmd_str.strip().split(maxsplit=1)
        if not parts:
            return ""

        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # DM Tools
        if cmd == "roll":
            from codex.core.dm_tools import roll_dice
            _, msg = roll_dice(args or "1d20")
            self._notes.append(f"Roll: {msg}")
            return msg

        elif cmd == "npc":
            from codex.core.dm_tools import generate_npc
            result = generate_npc(args)
            self._notes.append(f"NPC: {args or 'random'}")
            return result

        elif cmd == "trap":
            from codex.core.dm_tools import generate_trap
            return generate_trap(args or "medium")

        elif cmd == "loot":
            from codex.core.dm_tools import calculate_loot
            return calculate_loot(args or "medium")

        elif cmd == "encounter":
            from codex.core.dm_tools import generate_encounter
            tier = 1
            try:
                tier = int(args)
            except (ValueError, TypeError):
                pass
            return generate_encounter(self.system_tag, tier)

        elif cmd == "bestiary":
            from codex.core.dm_tools import lookup_creature
            result = lookup_creature(args, self.system_tag)
            self._last_query = result
            return result

        elif cmd == "ask":
            from codex.core.dm_tools import query_codex
            result = query_codex(args, self.system_tag.lower())
            self._last_query = result
            return result

        elif cmd == "note":
            self._notes.append(args)
            return f"Note added: {args}"

        elif cmd == "summary":
            from codex.core.dm_tools import summarize_context
            notes_text = "\n".join(self._notes)
            return summarize_context(notes_text)

        elif cmd == "scan":
            from codex.core.dm_tools import scan_vault
            return scan_vault()

        # Mechanics
        elif cmd == "init":
            return self._handle_initiative(args, engine)

        elif cmd == "condition":
            return self._handle_condition_apply(args)

        elif cmd == "uncondition":
            return self._handle_condition_remove(args)

        elif cmd == "rest":
            return self._handle_rest(args, engine)

        elif cmd == "xp":
            return self._handle_xp(args, engine)

        elif cmd == "levelup":
            return self._handle_levelup(args, engine)

        elif cmd == "companion":
            return self._handle_companion(args, engine)

        # System
        elif cmd == "status":
            try:
                from codex.core.cortex import Cortex
                cortex = Cortex()
                state = cortex.read_metabolic_state()
                return (
                    f"Thermal: {state.thermal_status.value}\n"
                    f"Clearance: {'YES' if state.metabolic_clearance else 'NO'}"
                )
            except Exception:
                return "Thermal status unavailable"

        elif cmd == "refresh":
            return "Vitals refreshed."

        elif cmd == "rules":
            return self._format_rules_lookup(args)

        elif cmd == "quest":
            return self._dispatch_quest(args)

        elif cmd == "npcs":
            return self._dispatch_npc(args)

        elif cmd == "timer":
            return self._dispatch_timer(args)

        elif cmd == "log":
            return self._dispatch_log(args)

        elif cmd == "concentrate":
            return self._dispatch_concentration(args)

        elif cmd == "death":
            return self._dispatch_death_save(args)

        elif cmd == "budget":
            if self.system_tag == "BURNWILLOW":
                return "Encounter budgets are not used in Burnwillow."
            return self._dispatch_encounter_budget(args)

        # ─── Burnwillow-Specific Commands ───────────────────────────
        elif cmd == "doom":
            return self._bw_doom(args, engine)

        elif cmd == "faction":
            return self._bw_faction(args, engine)

        elif cmd == "spawn":
            return self._bw_spawn(args, engine)

        elif cmd == "give":
            return self._bw_give(args, engine)

        elif cmd == "teach":
            return self._bw_teach(args, engine)

        elif cmd == "inflict":
            return self._bw_inflict(args, engine)

        elif cmd == "cure":
            return self._bw_cure(args, engine)

        elif cmd == "zone":
            return self._bw_zone(args, engine)

        elif cmd == "rot":
            return self._bw_rot(args, engine)

        elif cmd == "voice":
            return self._bw_voice(args)

        elif cmd == "cascade":
            return self._bw_cascade(engine)

        elif cmd == "inspect":
            return self._bw_inspect(args, engine)

        elif cmd == "help":
            return self._help_text()

        return f"Unknown command: {cmd}. Type 'help' for commands."

    def _dispatch_quest(self, args: str) -> str:
        """Handle quest subcommands: add, list, complete, abandon, remove."""
        parts = args.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else "list"
        sub_args = parts[1].strip() if len(parts) > 1 else ""

        if sub == "add":
            if not sub_args:
                return "Usage: quest add <title>"
            return self.quests.add(sub_args)
        elif sub in ("list", "all"):
            return self.quests.list_quests(status=sub_args or "")
        elif sub in ("complete", "done"):
            if not sub_args:
                return "Usage: quest complete <id>"
            return self.quests.complete(sub_args)
        elif sub == "abandon":
            if not sub_args:
                return "Usage: quest abandon <id>"
            return self.quests.abandon(sub_args)
        elif sub == "remove":
            if not sub_args:
                return "Usage: quest remove <id>"
            return self.quests.remove(sub_args)
        else:
            # Treat as "add" if no recognized subcommand
            return self.quests.add(args.strip())

    def _dispatch_npc(self, args: str) -> str:
        """Handle npc subcommands: log, list, attitude, info, remove."""
        parts = args.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else "list"
        sub_args = parts[1].strip() if len(parts) > 1 else ""
        if sub == "log":
            # npc log Name note text
            npc_parts = sub_args.split(maxsplit=1)
            name = npc_parts[0] if npc_parts else ""
            note = npc_parts[1] if len(npc_parts) > 1 else ""
            if not name:
                return "Usage: npc log <name> [note]"
            return self.npc_tracker.log(name, note=note)
        elif sub in ("list", "all"):
            return self.npc_tracker.list_npcs(attitude=sub_args)
        elif sub == "attitude":
            att_parts = sub_args.split(maxsplit=1)
            if len(att_parts) < 2:
                return "Usage: npc attitude <name> <friendly|neutral|hostile>"
            return self.npc_tracker.set_attitude(att_parts[0], att_parts[1])
        elif sub == "info":
            return self.npc_tracker.get_info(sub_args)
        elif sub == "remove":
            return self.npc_tracker.remove(sub_args)
        else:
            # Treat as info lookup
            return self.npc_tracker.get_info(args.strip())

    def _dispatch_timer(self, args: str) -> str:
        """Handle timer subcommands: start, stop, pause, resume, check."""
        sub = args.strip().lower() or "check"
        if sub == "start":
            return self.timer.start()
        elif sub == "stop":
            return self.timer.stop()
        elif sub == "pause":
            return self.timer.pause()
        elif sub == "resume":
            return self.timer.resume()
        else:
            elapsed = self.timer.elapsed_str()
            pacing = self.timer.pacing_check()
            return f"Session time: {elapsed}" + (f" — {pacing}" if pacing else "")

    def _dispatch_log(self, args: str) -> str:
        """Handle log subcommands: add, save, recap."""
        parts = args.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else "recap"
        sub_args = parts[1].strip() if len(parts) > 1 else ""
        if sub == "add":
            if not sub_args:
                return "Usage: log add <note text>"
            return self.session_log.add_note(sub_args)
        elif sub == "save":
            return self.session_log.save()
        elif sub == "recap":
            return self.session_log.load_last_recap()
        else:
            # Treat as note addition
            return self.session_log.add_note(args.strip())

    def _dispatch_concentration(self, args: str) -> str:
        """Handle concentrate subcommands: <caster> <spell>, drop, check, list."""
        if self.system_tag != "DND5E":
            return "Concentration tracking is D&D 5e only."
        parts = args.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else "list"
        sub_args = parts[1].strip() if len(parts) > 1 else ""
        if sub == "drop":
            return self.concentration.drop(sub_args) if sub_args else "Usage: concentrate drop <caster>"
        elif sub == "check":
            # concentrate check <caster> <damage>
            check_parts = sub_args.split()
            if len(check_parts) < 2:
                return "Usage: concentrate check <caster> <damage>"
            result = self.concentration.damage_check(check_parts[0], int(check_parts[1]))
            return result or f"{check_parts[0]} is not concentrating."
        elif sub == "pass":
            return self.concentration.pass_save(sub_args)
        elif sub == "fail":
            return self.concentration.fail_save(sub_args)
        elif sub == "list":
            return self.concentration.list_active()
        else:
            # concentrate <caster> <spell>
            if sub_args:
                return self.concentration.concentrate(sub, sub_args)
            return "Usage: concentrate <caster> <spell>"

    def _dispatch_death_save(self, args: str) -> str:
        """Handle death subcommands: start, success, fail, nat20, stabilize, list."""
        if self.system_tag != "DND5E":
            return "Death saves are D&D 5e only."
        parts = args.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else "list"
        name = parts[1].strip() if len(parts) > 1 else ""
        if sub == "start":
            return self.death_saves.start_dying(name) if name else "Usage: death start <name>"
        elif sub == "success":
            return self.death_saves.save_success(name) if name else "Usage: death success <name>"
        elif sub == "fail":
            return self.death_saves.save_failure(name) if name else "Usage: death fail <name>"
        elif sub == "nat20":
            return self.death_saves.nat20(name) if name else "Usage: death nat20 <name>"
        elif sub == "crit":
            return self.death_saves.crit_fail(name) if name else "Usage: death crit <name>"
        elif sub == "stabilize":
            return self.death_saves.stabilize(name) if name else "Usage: death stabilize <name>"
        else:
            return self.death_saves.list_dying()

    def _dispatch_encounter_budget(self, args: str) -> str:
        """Handle budget command: budget <party_levels> vs <monster_crs>."""
        from codex.core.mechanics.encounter_budget import calculate_encounter
        if self.system_tag == "DND5E":
            # Parse: budget 5,5,4,4 vs 3,1,1
            if "vs" not in args:
                return "Usage: budget <levels> vs <CRs>\nExample: budget 5,5,4,4 vs 3,1,1"
            left, right = args.split("vs", 1)
            try:
                levels = [int(x.strip()) for x in left.strip().split(",") if x.strip()]
                crs = [x.strip() for x in right.strip().split(",") if x.strip()]
            except ValueError:
                return "Usage: budget <levels> vs <CRs>"
            return calculate_encounter("DND5E", party_levels=levels, monster_crs=crs)
        elif self.system_tag in ("BITD", "SAV", "BOB", "CBRPNK", "CANDELA"):
            # Parse: budget <tier> <num_enemies>
            budget_parts = args.strip().split()
            tier = int(budget_parts[0]) if budget_parts else 1
            num = int(budget_parts[1]) if len(budget_parts) > 1 else 1
            return calculate_encounter(self.system_tag, tier=tier, num_enemies=num)
        return calculate_encounter(self.system_tag)

    # ─── Mechanics Handlers ────────────────────────────────────────────

    def _handle_initiative(self, args: str, engine) -> str:
        """Handle initiative sub-commands: roll, show, next, reset."""
        sub = args.split()[0] if args else "show"

        if sub == "roll":
            self.initiative.reset()
            from codex.core.mechanics.initiative import INITIATIVE_CONFIG
            config = INITIATIVE_CONFIG.get(self.system_tag, {"die": 20, "stat": "dexterity"})
            die = config["die"]

            # Roll for party
            if engine and hasattr(engine, 'party'):
                for char in engine.party:
                    stat_attr = config["stat"]
                    mod = 0
                    if hasattr(char, 'modifier') and hasattr(char, stat_attr):
                        score = getattr(char, stat_attr, 10)
                        mod = (score - 10) // 2
                    elif hasattr(char, stat_attr):
                        mod = getattr(char, stat_attr, 0)
                    self.initiative.roll_initiative(char.name, mod, True, die)

            self.initiative.sort()
            order = self.initiative.get_order()
            return f"Initiative rolled! Order: {', '.join(order)}"

        elif sub == "next":
            entry = self.initiative.next_turn()
            if entry:
                # WO-V35.0: Broadcast initiative advance for bot sync
                if self._broadcast:
                    self._broadcast.broadcast("INITIATIVE_ADVANCE", {
                        "name": entry.name,
                        "round": self.initiative.round_number,
                        "order": self.initiative.get_order(),
                        "is_player": entry.is_player,
                    })
                return f"Turn: {entry.name} (Round {self.initiative.round_number})"
            return "No combatants in initiative."

        elif sub == "reset":
            self.initiative.reset()
            return "Initiative cleared."

        else:  # show
            order = self.initiative.get_order()
            if not order:
                return "No initiative order. Use 'init roll' to start."
            current = self.initiative.current()
            lines = [f"Round {self.initiative.round_number}:"]
            for name in order:
                marker = "►" if current and name == current.name else " "
                lines.append(f"  {marker} {name}")
            return "\n".join(lines)

    def _handle_condition_apply(self, args: str) -> str:
        """Apply a condition: condition <name> <type> [duration]"""
        parts = args.split()
        if len(parts) < 2:
            return "Usage: condition <name> <type> [duration]"

        name = parts[0]
        try:
            from codex.core.mechanics.conditions import ConditionType, Condition, CONDITION_DEFAULTS
            ctype = ConditionType(parts[1].capitalize())
        except (ValueError, KeyError):
            valid = ", ".join(ct.value for ct in ConditionType)
            return f"Unknown condition: {parts[1]}. Valid: {valid}"

        duration = 3
        if len(parts) > 2:
            try:
                duration = int(parts[2])
            except ValueError:
                pass

        condition = Condition(
            condition_type=ctype,
            duration=duration,
            modifier=CONDITION_DEFAULTS.get(ctype, 0),
        )
        msg = self.conditions.apply(name, condition)
        # WO-V35.0: Broadcast condition change for bot sync
        if self._broadcast:
            self._broadcast.broadcast("CONDITION_CHANGE", {
                "entity": name,
                "action": "apply",
                "condition_type": ctype.value,
                "conditions": self.conditions.to_dict().get(name, []),
            })
        return msg

    def _handle_condition_remove(self, args: str) -> str:
        """Remove a condition: uncondition <name> <type>"""
        parts = args.split()
        if len(parts) < 2:
            return "Usage: uncondition <name> <type>"

        name = parts[0]
        try:
            from codex.core.mechanics.conditions import ConditionType
            ctype = ConditionType(parts[1].capitalize())
        except (ValueError, KeyError):
            return f"Unknown condition: {parts[1]}"

        msg = self.conditions.remove(name, ctype)
        # WO-V35.0: Broadcast condition change for bot sync
        if self._broadcast:
            self._broadcast.broadcast("CONDITION_CHANGE", {
                "entity": name,
                "action": "remove",
                "condition_type": ctype.value,
                "conditions": self.conditions.to_dict().get(name, []),
            })
        return msg

    def _handle_rest(self, args: str, engine) -> str:
        """Handle rest command."""
        rest_type = args.strip().lower() if args else "short"
        if rest_type not in ("short", "long"):
            rest_type = "short"
        result = self.rest_mgr.rest(engine, self.system_tag, rest_type)
        self._notes.append(f"{rest_type.title()} rest taken")
        # WO-V35.0: Broadcast rest complete for bot sync
        if self._broadcast:
            self._broadcast.broadcast("REST_COMPLETE", {
                "rest_type": rest_type,
                "system_tag": self.system_tag,
                "hp_recovered": result.hp_recovered,
                "summary": result.summary(),
            })
        return result.summary()

    def _handle_xp(self, args: str, engine) -> str:
        """Award XP: xp <amount> [source]"""
        parts = args.split(maxsplit=1)
        if not parts:
            return "Usage: xp <amount> [source]"
        try:
            amount = int(parts[0])
        except ValueError:
            return f"Invalid XP amount: {parts[0]}"
        source = parts[1] if len(parts) > 1 else ""

        if self.system_tag == "DND5E" and engine and hasattr(engine, 'gain_xp'):
            return engine.gain_xp(amount, source)
        elif self.system_tag in ("BITD", "SAV", "BOB"):
            if self.progression:
                return self.progression.mark_xp(source)
            return "No progression tracker active."
        elif self.progression:
            return self.progression.award_xp(amount, source)
        return "XP system not configured for this engine."

    def _handle_levelup(self, args: str, engine) -> str:
        """Level up a character."""
        name = args.strip()
        if self.system_tag == "DND5E" and engine and hasattr(engine, 'level_up'):
            return engine.level_up(name)
        elif self.system_tag == "STC" and engine and hasattr(engine, 'swear_ideal'):
            return engine.swear_ideal(name)
        return f"Level-up not supported for {self.system_tag}"

    def _handle_companion(self, args: str, engine) -> str:
        """Toggle AI companion on/off."""
        if self.companion is None:
            from codex.core.autopilot import GenericAutopilotAgent
            from codex.games.burnwillow.autopilot import PERSONALITY_POOL
            import random
            personality = random.choice(PERSONALITY_POOL)
            self.companion = GenericAutopilotAgent(personality, self.system_tag)

        sub = args.strip().lower() if args else ""
        if sub == "on":
            return self.companion.toggle(True)
        elif sub == "off":
            return self.companion.toggle(False)
        return self.companion.toggle()

    # ─────────────────────────────────────────────────────────────────
    # BURNWILLOW-SPECIFIC DM COMMANDS
    # ─────────────────────────────────────────────────────────────────

    def _bw_engine(self, engine):
        """Get the BurnwillowEngine from whatever is passed."""
        if engine and hasattr(engine, 'doom_clock'):
            return engine
        if self.core and hasattr(self.core, 'engine'):
            return self.core.engine
        return None

    def _bw_doom(self, args: str, engine) -> str:
        """View, advance, reduce, or set the Doom Clock."""
        eng = self._bw_engine(engine)
        if not eng:
            return "No Burnwillow engine available."
        if not args.strip():
            current = eng.doom_clock.current
            return f"Doom Clock: {current}\nThresholds: {eng.doom_clock.thresholds}"
        arg = args.strip()
        if arg.startswith("+"):
            n = int(arg[1:])
            events = eng.advance_doom(n)
            return f"Doom advanced by {n}. Now: {eng.doom_clock.current}\n" + "\n".join(events)
        elif arg.startswith("-"):
            n = int(arg[1:])
            eng.doom_clock.current = max(0, eng.doom_clock.current - n)
            return f"Doom reduced by {n}. Now: {eng.doom_clock.current}"
        elif arg.startswith("set "):
            n = int(arg[4:])
            eng.doom_clock.current = max(0, n)
            return f"Doom set to {n}."
        return f"Usage: doom [+N/-N/set N]  Current: {eng.doom_clock.current}"

    def _bw_faction(self, args: str, engine) -> str:
        """View or adjust faction reputation."""
        eng = self._bw_engine(engine)
        if not eng or not hasattr(eng, 'faction_rep'):
            return "No faction system available."
        if not args.strip():
            return "\n".join(eng.faction_rep.get_summary())
        parts = args.strip().split()
        faction = parts[0].lower()
        if len(parts) < 2:
            tier = eng.faction_rep.get_tier_name(faction)
            val = eng.faction_rep.get_tier(faction)
            return f"{faction}: {tier} ({val:+d})"
        try:
            amount = int(parts[1])
        except ValueError:
            return f"Usage: faction <name> [+N/-N]"
        msgs = eng.faction_rep.change_rep(faction, amount)
        return "\n".join(msgs)

    def _bw_spawn(self, args: str, engine) -> str:
        """Spawn an enemy or NPC into the current room."""
        eng = self._bw_engine(engine)
        if not eng:
            return "No engine available."
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: spawn enemy <name/tier> | spawn npc <name>"
        spawn_type = parts[0].lower()
        name = parts[1]

        if spawn_type == "enemy":
            # Try to parse as tier number
            try:
                tier = int(name)
                import random as _rng
                from codex.games.burnwillow.content import get_random_enemy
                enemy = get_random_enemy(tier, _rng.Random())
                if eng.current_room_id and eng.populated_rooms:
                    pop = eng.populated_rooms.get(eng.current_room_id)
                    if pop and isinstance(pop.content, dict):
                        pop.content.setdefault("enemies", []).append(enemy)
                return f"Spawned Tier {tier} enemy: {enemy.get('name', '?')}"
            except (ValueError, ImportError):
                # Spawn by name
                enemy = {"name": name, "hp": 15, "defense": 12, "damage": "2d6", "tier": 2}
                if eng.current_room_id and eng.populated_rooms:
                    pop = eng.populated_rooms.get(eng.current_room_id)
                    if pop and isinstance(pop.content, dict):
                        pop.content.setdefault("enemies", []).append(enemy)
                return f"Spawned enemy: {name}"

        elif spawn_type == "npc":
            npc = {"name": name, "npc_type": "quest_giver", "dialogue": f"{name} has appeared."}
            if eng.current_room_id and eng.populated_rooms:
                pop = eng.populated_rooms.get(eng.current_room_id)
                if pop and isinstance(pop.content, dict):
                    pop.content.setdefault("npcs", []).append(npc)
            return f"NPC spawned: {name}"

        return "Usage: spawn enemy <name/tier> | spawn npc <name>"

    def _bw_give(self, args: str, engine) -> str:
        """Give items, ingredients, amber, or scrap to a character."""
        eng = self._bw_engine(engine)
        if not eng or not eng.character:
            return "No active character."
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: give <type> <details>\n  give ingredient <name> [count]\n  give amber <amount>\n  give scrap <amount>\n  give recipe <name>"
        give_type = parts[0].lower()
        detail = parts[1]
        char = eng.character

        if give_type == "ingredient":
            ing_parts = detail.rsplit(maxsplit=1)
            name = ing_parts[0]
            count = 1
            if len(ing_parts) > 1:
                try:
                    count = int(ing_parts[1])
                    name = ing_parts[0]
                except ValueError:
                    name = detail
            char.ingredients[name] = char.ingredients.get(name, 0) + count
            return f"Gave {count}x {name}. Total: {char.ingredients[name]}"

        elif give_type == "amber":
            try:
                amount = int(detail)
            except ValueError:
                return "Usage: give amber <amount>"
            char.scrap += amount  # Amber and scrap are the same economy
            return f"Gave {amount} amber/scrap. Total: {char.scrap}"

        elif give_type == "scrap":
            try:
                amount = int(detail)
            except ValueError:
                return "Usage: give scrap <amount>"
            char.scrap += amount
            return f"Gave {amount} scrap. Total: {char.scrap}"

        elif give_type == "recipe":
            if detail not in char.known_recipes:
                char.known_recipes.append(detail)
            return f"Recipe unlocked: {detail}"

        return "Usage: give ingredient/amber/scrap/recipe <details>"

    def _bw_teach(self, args: str, engine) -> str:
        """Teach a recipe to the party."""
        eng = self._bw_engine(engine)
        if not eng or not eng.character:
            return "No active character."
        recipe_name = args.strip()
        if not recipe_name:
            return "Usage: teach <recipe name>"
        char = eng.character
        if recipe_name not in char.known_recipes:
            char.known_recipes.append(recipe_name)
        return f"Recipe taught: {recipe_name}"

    def _bw_inflict(self, args: str, engine) -> str:
        """Inflict a condition on a character."""
        eng = self._bw_engine(engine)
        if not eng:
            return "No engine available."
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: inflict <character> <condition>"
        char_name = parts[0]
        cond_name = parts[1]
        target = None
        for c in eng.party:
            if char_name.lower() in c.name.lower():
                target = c
                break
        if not target:
            target = eng.character
        from codex.games.burnwillow.engine import Condition
        for cond in Condition:
            if cond_name.lower().replace("-", "").replace("_", "") in cond.value.lower().replace("-", ""):
                msg = target.add_condition(cond)
                return msg
        return f"Unknown condition: {cond_name}. Available: {', '.join(c.value for c in Condition)}"

    def _bw_cure(self, args: str, engine) -> str:
        """Remove a condition from a character."""
        eng = self._bw_engine(engine)
        if not eng:
            return "No engine available."
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: cure <character> <condition>"
        char_name = parts[0]
        cond_name = parts[1]
        target = None
        for c in eng.party:
            if char_name.lower() in c.name.lower():
                target = c
                break
        if not target:
            target = eng.character
        from codex.games.burnwillow.engine import Condition
        for cond in Condition:
            if cond_name.lower().replace("-", "").replace("_", "") in cond.value.lower().replace("-", ""):
                msg = target.remove_condition(cond)
                return msg or f"{target.name} doesn't have {cond.value}."
        return f"Unknown condition: {cond_name}"

    def _bw_zone(self, args: str, engine) -> str:
        """View or switch the current dungeon zone."""
        eng = self._bw_engine(engine)
        if not eng:
            return "No engine available."
        if not args.strip():
            zone = getattr(eng, '_zone', 'unknown')
            zone_names = {1: "The Tangle", 2: "The Stone-Grip", 3: "The Aether-Flow",
                         4: "The Rot-Heart", 5: "The Crown", 6: "The Heartwood", 7: "The Undergrove"}
            return f"Current zone: {zone} ({zone_names.get(zone, '?')})"
        try:
            new_zone = int(args.strip())
        except ValueError:
            return "Usage: zone [1-7]"
        import random as _rng
        eng.generate_dungeon(depth=4, seed=_rng.randint(0, 999999), zone=new_zone)
        zone_names = {1: "The Tangle", 2: "The Stone-Grip", 3: "The Aether-Flow",
                     4: "The Rot-Heart", 5: "The Crown", 6: "The Heartwood", 7: "The Undergrove"}
        return f"Zone switched to {new_zone} ({zone_names.get(new_zone, '?')}). Dungeon regenerated."

    def _bw_rot(self, args: str, engine) -> str:
        """Trigger or clear vault breach echo (Rot intensity)."""
        eng = self._bw_engine(engine)
        if not eng:
            return "No engine available."
        if not args.strip():
            echo = eng.vault_echo_remaining
            return f"Vault echo remaining: {echo} rooms"
        if args.strip() == "+":
            msg = eng.trigger_vault_breach()
            return msg
        elif args.strip() == "-":
            eng.vault_echo_remaining = 0
            return "Vault echo cleared."
        return "Usage: rot [+/-]  (+ triggers breach, - clears echo)"

    def _bw_voice(self, args: str) -> str:
        """Show NPC voice prompt for roleplay reference."""
        if not args.strip():
            return "Usage: voice <npc name>"
        import json
        from pathlib import Path
        npc_path = Path(__file__).resolve().parent.parent.parent / "config" / "npcs" / "burnwillow.json"
        if not npc_path.exists():
            return "NPC config not found."
        data = json.loads(npc_path.read_text())
        target = args.strip().lower()
        for npc in data.get("named_npcs", []):
            if target in npc.get("name", "").lower():
                lines = [f"=== {npc['name']} ==="]
                lines.append(f"Voice: {npc.get('voice', 'No voice note.')}")
                lines.append(f"Quirk: {npc.get('quirk', '')}")
                lines.append(f"Want: {npc.get('want', '')}")
                lines.append(f"Need: {npc.get('need', '')}")
                faction = npc.get('faction', '')
                if faction:
                    lines.append(f"Faction: {faction}")
                return "\n".join(lines)
        return f"No NPC named '{args.strip()}' found."

    def _bw_cascade(self, engine) -> str:
        """Trigger a Leech Cascade event in the current room."""
        eng = self._bw_engine(engine)
        if not eng or not eng.current_room_id:
            return "No active room."
        pop = eng.populated_rooms.get(eng.current_room_id)
        if not pop or not isinstance(pop.content, dict):
            return "Room has no content to modify."
        # Add cascade enemies
        pop.content.setdefault("enemies", []).extend([
            {"name": "Sap Leech", "hp": 6, "defense": 9, "damage": "1d4",
             "special": "Life Drain: heals 1 HP per hit. Inflicts Sap-Drained.", "tier": 1},
            {"name": "Sap Leech", "hp": 6, "defense": 9, "damage": "1d4",
             "special": "Life Drain: heals 1 HP per hit. Inflicts Sap-Drained.", "tier": 1},
        ])
        pop.content.setdefault("hazards", []).append(
            {"name": "Leech Cascade", "damage": 0, "description": "Sap Leeches cluster on the walls. The Root-Song thins."}
        )
        return "Leech Cascade triggered! 2 Sap Leeches spawned. Room conditions: Sap-Drained."

    def _bw_inspect(self, args: str, engine) -> str:
        """Full character inspection — gear, sets, affixes, conditions, stats."""
        eng = self._bw_engine(engine)
        if not eng:
            return "No engine available."
        target = eng.character
        if args.strip():
            for c in eng.party:
                if args.strip().lower() in c.name.lower():
                    target = c
                    break
        if not target:
            return "No character found."
        from codex.games.burnwillow.engine import StatType, GEAR_SETS
        lines = [f"=== {target.name} ({target.heritage}) ==="]
        lines.append(f"HP: {target.current_hp}/{target.max_hp}  Defense: {target.get_defense()}")
        for stat in StatType:
            eff = target.get_effective_score(stat)
            mod = target.get_stat_mod(stat)
            dice = target.gear.get_total_dice_bonus(stat)
            lines.append(f"  {stat.value}: {eff} ({mod:+d}) [{dice}d6 pool]")
        # Gear
        lines.append("\nGear:")
        for slot, item in target.gear.slots.items():
            if item:
                display = item.get_display_name()
                extra = f" [SET:{item.set_id}]" if item.set_id else ""
                lines.append(f"  {slot.value}: {display} (T{item.tier.value}){extra}")
        # Set bonuses
        sets = target.gear.get_set_progress()
        if sets:
            lines.append("\nSets:")
            for sid, (count, name) in sets.items():
                lines.append(f"  {name}: {count}/4")
        # Active bonuses
        bonuses = target.gear.get_active_set_bonuses()
        if bonuses:
            lines.append("Active Set Bonuses:")
            for key, bonus in bonuses.items():
                lines.append(f"  {key}: {bonus.get('description', str(bonus))}")
        # Conditions
        conds = target.get_active_conditions()
        if conds:
            lines.append(f"\nConditions: {', '.join(conds)}")
        # Ingredients
        if target.ingredients:
            lines.append(f"\nIngredients: {len(target.ingredients)} types")
        if target.known_recipes:
            lines.append(f"Known Recipes: {len(target.known_recipes)}")
        return "\n".join(lines)

    def _bw_help_text(self) -> str:
        """Burnwillow-specific DM Dashboard help."""
        return (
            "DM Dashboard — BURNWILLOW\n"
            "═══════════════════════════\n"
            "\n"
            "--- World Control ---\n"
            "  doom [+N/-N/set N]       - View/adjust Doom Clock\n"
            "  faction [name] [+N/-N]   - View/adjust faction reputation\n"
            "  zone [1-7]               - View or switch dungeon zone\n"
            "  rot [+/-]                - Trigger/clear vault breach echo\n"
            "  cascade                  - Trigger Leech Cascade in current room\n"
            "\n"
            "--- Encounter Management ---\n"
            "  spawn enemy <name/tier>  - Add enemy to current room\n"
            "  spawn npc <name>         - Add NPC to current scene\n"
            "  encounter [tier]         - Generate full encounter\n"
            "  bestiary <name>          - Lookup creature stats\n"
            "  inflict <char> <cond>    - Apply condition to character\n"
            "  cure <char> <cond>       - Remove condition from character\n"
            "  init [roll|show|next]    - Initiative tracker\n"
            "\n"
            "--- Loot & Economy ---\n"
            "  give ingredient <name> [N]  - Give ingredients\n"
            "  give amber/scrap <N>        - Give currency\n"
            "  give recipe <name>          - Unlock a recipe\n"
            "  teach <recipe>              - Teach recipe to party\n"
            "  loot [difficulty]           - Generate random loot\n"
            "\n"
            "--- Information ---\n"
            "  inspect [character]      - Full character sheet (gear, sets, conditions)\n"
            "  voice <npc name>         - NPC voice/quirk/want/need for roleplay\n"
            "  ask <question>           - Query Codex model w/ RAG\n"
            "  rules [topic]            - Rules quick-reference\n"
            "\n"
            "--- Session Management ---\n"
            "  roll <dice>              - Roll dice (e.g. 3d6+2)\n"
            "  condition <name> <type>  - Apply condition (generic)\n"
            "  rest [short|long]        - Trigger rest\n"
            "  quest add/list/complete  - Quest tracker\n"
            "  npcs log/list/info       - NPC tracker\n"
            "  note <text>              - Session note\n"
            "  timer [start|stop]       - Session timer\n"
            "  log add/save/recap       - Session log\n"
            "  status                   - Thermal/RAM vitals\n"
            "  quit                     - Exit dashboard\n"
        )

    def _help_text(self) -> str:
        """Return help text for all commands."""
        if self.system_tag == "BURNWILLOW":
            return self._bw_help_text()
        return (
            "DM Dashboard Commands:\n"
            "  roll <dice>         - Roll dice (e.g. 2d6+3)\n"
            "  npc [archetype]     - Generate random NPC\n"
            "  trap [difficulty]   - Generate trap\n"
            "  loot [difficulty]   - Generate loot\n"
            "  encounter [tier]    - Generate encounter\n"
            "  bestiary <name>     - Lookup creature stats\n"
            "  ask <question>      - Query Codex model w/ RAG\n"
            "  note <text>         - Add session note\n"
            "  summary             - Summarize session notes\n"
            "  scan                - Scan vault for content\n"
            "  init [roll|show|next|reset] - Initiative tracker\n"
            "  condition <name> <type> [dur] - Apply condition\n"
            "  uncondition <name> <type>     - Remove condition\n"
            "  rest [short|long]   - Trigger rest\n"
            "  xp <amount> [src]   - Award XP/mark\n"
            "  levelup <name>      - Level up character\n"
            "  companion [on|off]  - Toggle AI companion\n"
            "  rules [topic]       - Rules quick-reference\n"
            "  quest add <title>   - Track a quest/plot thread\n"
            "  quest list [status] - List quests (active/completed/all)\n"
            "  quest complete <id> - Mark quest complete\n"
            "  quest abandon <id>  - Abandon quest\n"
            "  quest remove <id>   - Delete quest\n"
            "  npcs log <name> [note] - Track NPC interaction\n"
            "  npcs list [attitude] - List tracked NPCs\n"
            "  npcs attitude <name> <type> - Set NPC attitude\n"
            "  npcs info <name>    - Show NPC details\n"
            "  timer [start|stop|pause|resume] - Session timer\n"
            "  log add <note>      - Add persistent session note\n"
            "  log save            - Save session log to file\n"
            "  log recap           - Show last session recap\n"
            "  concentrate <who> <spell> - Track concentration (5e)\n"
            "  concentrate drop <who>    - Drop concentration\n"
            "  concentrate check <who> <dmg> - Conc. save check\n"
            "  death start <name>  - Begin death saves (5e)\n"
            "  death success/fail <name> - Record save result\n"
            "  death nat20/stabilize <name> - Special outcomes\n"
            "  budget <levels> vs <CRs>  - Encounter budget (5e)\n"
            "  status              - Thermal/RAM vitals\n"
            "  refresh             - Re-read engine state\n"
            "  quit                - Exit dashboard\n"
        )

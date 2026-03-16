"""
codex.core.autopilot — Generic AI Companion (System-Agnostic)
===============================================================

Wraps the Burnwillow AutopilotAgent heuristics with per-engine
snapshot builders and command executors for all 5 engine families.

Each engine gets:
  - A snapshot builder that normalizes engine state to plain dicts
  - A command executor that translates agent output to engine calls

Reuses CompanionPersonality and PERSONALITY_POOL from burnwillow/autopilot.py.

WO-V34.0: The Sovereign Dashboard — Gap #1
"""

from typing import Optional

from codex.games.burnwillow.autopilot import (
    AutopilotAgent, CompanionPersonality, PERSONALITY_POOL,
)
from codex.core.trait_evolution import TraitEvolution, apply_nudge_trigger


class GenericAutopilotAgent:
    """System-agnostic AI companion that wraps AutopilotAgent's heuristics."""

    def __init__(self, personality: CompanionPersonality, system_tag: str):
        self.system_tag = system_tag.upper()
        self.agent = AutopilotAgent(personality=personality)
        self.personality = personality
        self.enabled = False
        self.evolution: Optional[TraitEvolution] = None

    def init_evolution(self) -> None:
        """Initialize trait evolution tracking from current personality."""
        if self.personality and not self.evolution:
            traits = {
                "aggression": self.personality.aggression,
                "curiosity": self.personality.curiosity,
                "caution": self.personality.caution,
            }
            self.evolution = TraitEvolution(traits)

    def nudge(self, trigger: str, turn: int = 0) -> list:
        """Apply a nudge trigger to trait evolution. Returns change descriptions."""
        if not self.evolution:
            self.init_evolution()
        return apply_nudge_trigger(self.evolution, trigger, turn)

    def get_effective_personality(self) -> CompanionPersonality:
        """Return personality with evolution applied."""
        if not self.evolution:
            return self.personality
        current = self.evolution.get_current_traits()
        import copy
        p = copy.copy(self.personality)
        p.aggression = current.get("aggression", p.aggression)
        p.curiosity = current.get("curiosity", p.curiosity)
        p.caution = current.get("caution", p.caution)
        return p

    # ─── Snapshot Builders ─────────────────────────────────────────────

    def build_snapshot(self, engine, phase: str = "exploration") -> dict:
        """Build a normalized snapshot dict for the decision engine."""
        builder = {
            "BURNWILLOW": self._snapshot_burnwillow,
            "DND5E": self._snapshot_dnd5e,
            "STC": self._snapshot_cosmere,
            "BITD": self._snapshot_bitd,
            "CROWN": self._snapshot_crown,
        }.get(self.system_tag, self._snapshot_generic)
        return builder(engine, phase)

    def _snapshot_burnwillow(self, engine, phase: str) -> dict:
        """Burnwillow snapshots use the existing engine API directly."""
        char = engine.character
        hp_pct = char.current_hp / max(1, char.max_hp) if char else 1.0
        room_id = getattr(engine, 'current_room_id', None)

        return {
            "hp_pct": hp_pct,
            "enemies": [],
            "loot": [],
            "searched": False,
            "exits": engine.get_cardinal_exits() if hasattr(engine, 'get_cardinal_exits') else [],
            "has_interactive": False,
            "current_room_id": room_id,
        }

    def _snapshot_dnd5e(self, engine, phase: str) -> dict:
        """Map DnD5e state to snapshot keys."""
        char = engine.character
        hp_pct = char.current_hp / max(1, char.max_hp) if char else 1.0
        exits = engine.get_cardinal_exits() if hasattr(engine, 'get_cardinal_exits') else []
        room = engine.populated_rooms.get(engine.current_room_id) if engine.current_room_id else None
        enemies = room.content.get("enemies", []) if room else []

        return {
            "hp_pct": hp_pct,
            "enemies": enemies,
            "loot": room.content.get("loot", []) if room else [],
            "searched": False,
            "exits": exits,
            "has_interactive": False,
            "current_room_id": engine.current_room_id,
        }

    def _snapshot_cosmere(self, engine, phase: str) -> dict:
        """Map Cosmere state to snapshot keys."""
        char = engine.character
        hp_pct = char.current_hp / max(1, char.max_hp) if char else 1.0
        exits = engine.get_cardinal_exits() if hasattr(engine, 'get_cardinal_exits') else []

        return {
            "hp_pct": hp_pct,
            "enemies": [],
            "loot": [],
            "searched": False,
            "exits": exits,
            "has_interactive": False,
            "current_room_id": engine.current_room_id,
        }

    def _snapshot_bitd(self, engine, phase: str) -> dict:
        """Map BitD state — stress/heat as health proxy."""
        char = engine.character
        clock = engine.stress_clocks.get(char.name) if char else None
        stress_pct = clock.current_stress / max(1, clock.max_stress) if clock else 0
        hp_pct = 1.0 - stress_pct  # Invert: high stress = low "hp"

        return {
            "hp_pct": hp_pct,
            "enemies": [],
            "loot": [],
            "searched": False,
            "exits": [],
            "has_interactive": False,
            "room_type": "",
        }

    def _snapshot_crown(self, engine, phase: str) -> dict:
        """Map Crown state — sway as exploration context."""
        return {
            "hp_pct": 1.0,
            "enemies": [],
            "loot": [],
            "searched": False,
            "exits": [],
            "has_interactive": False,
            "room_type": "",
        }

    def _snapshot_generic(self, engine, phase: str) -> dict:
        """Fallback for unknown systems."""
        return {
            "hp_pct": 1.0,
            "enemies": [],
            "loot": [],
            "searched": False,
            "exits": [],
            "has_interactive": False,
        }

    # ─── Command Executors ─────────────────────────────────────────────

    def execute(self, action: str, engine) -> str:
        """Translate agent output to engine calls."""
        executor = {
            "BURNWILLOW": self._execute_burnwillow,
            "DND5E": self._execute_dnd5e,
            "STC": self._execute_cosmere,
            "BITD": self._execute_bitd,
            "CROWN": self._execute_crown,
        }.get(self.system_tag, self._execute_generic)
        return executor(action, engine)

    def _execute_burnwillow(self, action: str, engine) -> str:
        """Burnwillow commands route through engine directly."""
        if action == "bind":
            return "Companion suggests binding wounds."
        elif action.startswith("move "):
            room_id = action.split()[-1]
            try:
                rid = int(room_id)
                if engine.move_to_room(rid):
                    return f"Companion moves to room {rid}."
                return "Companion: can't move there."
            except (ValueError, AttributeError):
                return f"Companion: invalid room '{room_id}'."
        elif action == "search":
            return "Companion searches the room."
        elif action == "attack":
            return "Companion engages the enemy!"
        return f"Companion: {action}"

    def _execute_dnd5e(self, action: str, engine) -> str:
        """DnD5e: roll_check, move_to_room."""
        if action.startswith("move "):
            try:
                rid = int(action.split()[-1])
                if engine.move_to_room(rid):
                    return f"Companion moves to room {rid}."
            except (ValueError, AttributeError):
                pass
            return "Companion: can't move there."
        elif action == "attack":
            return "Companion attacks!"
        return f"Companion: {action}"

    def _execute_cosmere(self, action: str, engine) -> str:
        """Cosmere: roll_check + focus_spend."""
        if action.startswith("move "):
            try:
                rid = int(action.split()[-1])
                if engine.move_to_room(rid):
                    return f"Companion moves to room {rid}."
            except (ValueError, AttributeError):
                pass
            return "Companion: can't move there."
        return f"Companion: {action}"

    def _execute_bitd(self, action: str, engine) -> str:
        """BitD: route through handle_command."""
        if action in ("end", "guard"):
            return f"Companion: {action}"
        return engine.handle_command(action) if hasattr(engine, 'handle_command') else f"Companion: {action}"

    def _execute_crown(self, action: str, engine) -> str:
        """Crown: narrative actions."""
        return f"Companion considers: {action}"

    def _execute_generic(self, action: str, engine) -> str:
        return f"Companion: {action}"

    # ─── Core Decision ─────────────────────────────────────────────────

    def decide(self, engine, phase: str = "exploration") -> str:
        """Build snapshot, decide, return action string."""
        snapshot = self.build_snapshot(engine, phase)
        if phase == "combat":
            return self.agent.decide_combat(snapshot)
        elif phase == "hub":
            return self.agent.decide_hub(snapshot)
        return self.agent.decide_exploration(snapshot)

    def toggle(self, on: Optional[bool] = None) -> str:
        """Toggle companion on/off."""
        if on is not None:
            self.enabled = on
        else:
            self.enabled = not self.enabled
        return f"AI Companion {'ENABLED' if self.enabled else 'DISABLED'}"

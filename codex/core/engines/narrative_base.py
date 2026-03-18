"""
codex/core/engines/narrative_base.py — Narrative/FITD Engine Base Class
========================================================================
Extracts the common scene-based navigation and FITD roll patterns shared
by BitDEngine, SaVEngine, and related narrative engines.

Subclasses provide system-specific hooks:

    _get_command_registry()   — dict mapping cmd name -> handler callable
    _format_status()          — return human-readable status string
    _create_character(name, **kwargs)  — factory for character dataclass

Usage:
    class MyEngine(NarrativeEngineBase):
        system_id = "myid"
        system_family = "MYID"
        display_name = "My System"

        def _create_character(self, name, **kwargs):
            return MyCharacter(name=name, **kwargs)

        def _get_command_registry(self):
            return {
                "do_thing": self._cmd_do_thing,
            }

        def _format_status(self):
            return f"Party: {len(self.party)} | Heat: {self.heat}"
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from codex.core.services.narrative_loom import NarrativeLoomMixin


class NarrativeEngineBase(NarrativeLoomMixin):
    """Base class for narrative / FITD / PbtA scene-based engines.

    Provides: roll_action(), push_stress(), handle_command(), get_status(),
    stress_clock and faction_clocks management, save_state(), load_state().

    Subclasses must override: _create_character(), _get_command_registry().
    Subclasses may override: _format_status(), get_status(), get_mood_context().
    """

    # --- Subclasses must set these class attributes -----------------------
    system_id: str = "base_narrative"
    system_family: str = "BASE"
    display_name: str = "Narrative Engine"

    def __init__(self) -> None:
        self.character: Optional[Any] = None
        self.party: List[Any] = []
        self.setting_id: str = ""
        self.stress_clocks: Dict[str, Any] = {}
        self.faction_clocks: List[Any] = []
        self._init_loom()

    # =====================================================================
    # Abstract hooks — subclasses must implement
    # =====================================================================

    def _create_character(self, name: str, **kwargs) -> Any:
        """Factory for the system's character dataclass.

        Args:
            name: Character's name.
            **kwargs: System-specific keyword arguments.

        Returns:
            A new character instance.

        Raises:
            NotImplementedError: Subclasses must implement this.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _create_character()"
        )

    def _get_command_registry(self) -> Dict[str, Callable]:
        """Return a mapping of command name -> handler callable.

        Each handler should accept **kwargs and return a str result.

        Returns:
            Dict mapping command strings to bound methods.
        """
        return {}

    # =====================================================================
    # Optional hooks — subclasses may override
    # =====================================================================

    def _format_status(self) -> str:
        """Return a human-readable status string for this engine.

        Default implementation returns a basic party summary.

        Returns:
            Status string for display.
        """
        lead = self.party[0] if self.party else None
        name = lead.name if lead else "None"
        return f"{self.display_name} | Lead: {name} | Party: {len(self.party)}"

    # =====================================================================
    # Character management
    # =====================================================================

    def create_character(self, name: str, **kwargs) -> Any:
        """Create a character and set as party lead.

        Pops 'setting_id' before delegating to _create_character().
        Creates a StressClock for the new character.

        Args:
            name: Character's name.
            **kwargs: System-specific keyword arguments.

        Returns:
            Newly created character instance.
        """
        setting_id = kwargs.pop("setting_id", self.setting_id)
        if setting_id:
            self.setting_id = setting_id
        char = self._create_character(name, setting_id=setting_id, **kwargs)
        self.character = char
        if not self.party:
            self.party = [char]
        else:
            self.party.append(char)
        from codex.core.services.fitd_engine import StressClock
        self.stress_clocks[name] = StressClock()
        self._add_shard(
            f"{self.display_name} crew founded. Lead: {name}.", "MASTER"
        )
        return char

    def add_to_party(self, char: Any) -> None:
        """Add an existing character to the party.

        Args:
            char: Character instance to add.
        """
        self.party.append(char)
        from codex.core.services.fitd_engine import StressClock
        self.stress_clocks[char.name] = StressClock()

    def remove_from_party(self, char: Any) -> None:
        """Remove a character from the party.

        Args:
            char: Character instance to remove.
        """
        if char in self.party:
            self.party.remove(char)
            self.stress_clocks.pop(char.name, None)

    def get_active_party(self) -> List[Any]:
        """Return all current party members.

        Returns:
            List of all party members (FITD chars don't have HP death).
        """
        return list(self.party)

    # =====================================================================
    # Action rolls (FITD core mechanic)
    # =====================================================================

    def roll_action(
        self,
        character: Optional[Any] = None,
        action: str = "",
        bonus_dice: int = 0,
        **kwargs,
    ) -> Any:
        """Roll a FITD action using the character's action dots.

        Looks up the action attribute on the character and builds an
        FITDActionRoll with that many dice plus any bonus dice.

        Args:
            character: The acting character (defaults to lead).
            action: Action attribute name (e.g. 'hunt', 'helm', 'scrap').
            bonus_dice: Extra dice from teamwork / assist.
            **kwargs: 'position' (Position) and 'effect' (Effect) accepted.

        Returns:
            FITDResult with outcome, dice, and position/effect context.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect
        char = character or self.character
        dots = getattr(char, action, 0) if char else 0
        position = kwargs.get("position", Position.RISKY)
        effect = kwargs.get("effect", Effect.STANDARD)
        roll = FITDActionRoll(
            dice_count=dots + bonus_dice,
            position=position,
            effect=effect,
        )
        return roll.roll()

    def push_stress(self, char_name: str, amount: int = 1) -> dict:
        """Push stress for a character with trauma shard emission.

        Args:
            char_name: Name of the character whose stress clock to push.
            amount: Stress points to add.

        Returns:
            StressClock.push() result dict, or empty dict if not found.
        """
        clock = self.stress_clocks.get(char_name)
        if not clock:
            return {}
        result = clock.push(amount)
        if result.get("trauma_triggered"):
            self._add_shard(
                f"{char_name} suffered trauma: {result['new_trauma']}. "
                f"Total traumas: {result['total_traumas']}/4.",
                "ANCHOR",
                source="session",
            )
        return result

    def add_faction_clock(self, name: str, segments: int = 4) -> Any:
        """Add a faction progress clock.

        Args:
            name: Clock name.
            segments: Number of segments (4, 6, or 8).

        Returns:
            The newly created FactionClock.
        """
        from codex.core.services.fitd_engine import FactionClock
        clock = FactionClock(name=name, segments=segments)
        self.faction_clocks.append(clock)
        return clock

    # =====================================================================
    # Status
    # =====================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dict suitable for Butler/UI display.

        Returns:
            Dict with system, party_size, lead, stress summary.
        """
        lead = self.party[0] if self.party else None
        lead_stress = None
        if lead:
            clock = self.stress_clocks.get(lead.name)
            if clock:
                lead_stress = f"{clock.current_stress}/{clock.max_stress}"
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "lead_stress": lead_stress,
            "faction_clocks": len(self.faction_clocks),
        }

    def get_mood_context(self) -> Dict[str, Any]:
        """Return current mechanical state as narrative mood modifiers.

        Returns:
            Dict with tension, tone_words, party_condition, system_specific.
        """
        lead = self.character
        clock = self.stress_clocks.get(lead.name) if lead else None
        stress = clock.current_stress if clock else 0
        max_stress = clock.max_stress if clock else 9
        trauma_count = len(clock.traumas) if clock else 0
        stress_pct = stress / max(1, max_stress)
        tension = min(1.0, stress_pct + (trauma_count * 0.15))

        words: List[str] = []
        if trauma_count >= 2:
            words.extend(["haunted", "fractured", "unreliable"])
        if stress_pct > 0.7:
            words.extend(["fraying", "manic", "reckless"])

        if stress_pct > 0.8 or trauma_count >= 3:
            condition = "critical"
        elif stress_pct > 0.5 or trauma_count >= 1:
            condition = "battered"
        else:
            condition = "healthy"

        return {
            "tension": round(tension, 2),
            "tone_words": words,
            "party_condition": condition,
            "system_specific": {"stress": stress, "trauma_count": trauma_count},
        }

    # =====================================================================
    # Command dispatch
    # =====================================================================

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Dispatch a command string to the appropriate handler.

        Checks for 'trace_fact' (loom built-in) first, then consults
        _get_command_registry(), then falls through to _cmd_{cmd} methods.

        Args:
            cmd: Command identifier string.
            **kwargs: Command-specific keyword arguments.

        Returns:
            Human-readable result string.
        """
        if cmd == "trace_fact":
            return self.trace_fact(kwargs.get("fact", ""))
        # Check subclass registry first
        registry = self._get_command_registry()
        handler = registry.get(cmd)
        if handler:
            return handler(**kwargs)
        # Fall back to _cmd_* convention
        method = getattr(self, f"_cmd_{cmd}", None)
        if method:
            return method(**kwargs)
        return f"Unknown command: {cmd}"

    def _cmd_status(self, **kwargs) -> str:
        """Display engine status."""
        return self._format_status()

    def _cmd_roll_action(self, **kwargs) -> str:
        """Roll a FITD action check."""
        from codex.core.services.fitd_engine import format_roll_result
        result = self.roll_action(**kwargs)
        return format_roll_result(result)

    def _cmd_crew_stress(self, **kwargs) -> str:
        """Show crew stress and trauma."""
        lines = ["Crew Stress/Trauma:"]
        for name, clock in self.stress_clocks.items():
            traumas = ", ".join(clock.traumas) if clock.traumas else "none"
            lines.append(
                f"  {name}: stress {clock.current_stress}/{clock.max_stress}"
                f" | traumas: {traumas}"
            )
        if not self.stress_clocks:
            lines.append("  No crew members registered.")
        return "\n".join(lines)

    def _cmd_clocks(self, **kwargs) -> str:
        """Show all faction clocks."""
        if not self.faction_clocks:
            return "No faction clocks active."
        lines = ["Faction Clocks:"]
        for clock in self.faction_clocks:
            filled = clock.filled
            segments = clock.max_segments or "?"
            bar = "#" * filled + "-" * (
                (segments - filled) if isinstance(segments, int) else 0
            )
            lines.append(f"  {clock.name}: [{bar}] {filled}/{segments}")
        return "\n".join(lines)

    # =====================================================================
    # Save / Load
    # =====================================================================

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state to JSON-safe dict.

        Returns:
            Dict with system_id, setting_id, party, stress, faction_clocks.
        """
        return {
            "system_id": self.system_id,
            "setting_id": self.setting_id,
            "party": [c.to_dict() for c in self.party],
            "stress": {k: v.to_dict() for k, v in self.stress_clocks.items()},
            "faction_clocks": [c.to_dict() for c in self.faction_clocks],
        }

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict.

        Subclasses that add extra state should call super().load_state(data)
        then restore their own fields.

        Note: character deserialization requires subclasses to implement
        a classmethod or call _create_character with dict unpacking.
        The base implementation stores raw dicts when _create_character
        raises NotImplementedError, to avoid crashing on load.

        Args:
            data: Dict from a previous save_state() call.
        """
        from codex.core.services.fitd_engine import StressClock, UniversalClock
        self.setting_id = data.get("setting_id", "")

        rebuilt: List[Any] = []
        for d in data.get("party", []):
            try:
                char = self._create_character(**d)
                rebuilt.append(char)
            except (NotImplementedError, TypeError, Exception):
                pass
        self.party = rebuilt
        self.character = self.party[0] if self.party else None

        self.stress_clocks = {
            k: StressClock.from_dict(v)
            for k, v in data.get("stress", {}).items()
        }
        self.faction_clocks = [
            UniversalClock.from_dict(c)
            for c in data.get("faction_clocks", [])
        ]

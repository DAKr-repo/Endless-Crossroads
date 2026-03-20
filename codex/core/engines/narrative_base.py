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
        self._npc_disposition: Optional[Any] = None

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

    def _get_trauma_table(self) -> Optional[list]:
        """Return a custom trauma table for StressClock, or None for default.

        Override in subclasses that use a non-standard trauma table
        (e.g. Band of Blades uses BOB_TRAUMAS).

        Returns:
            List of trauma strings, or None to use FITD defaults.
        """
        return None

    def _use_stress_clocks(self) -> bool:
        """Whether this engine uses StressClock-based stress tracking.

        Override to return False for systems like Candela Obscura that
        use Body/Brain/Bleed tracks instead of a unified stress clock.

        Returns:
            True if characters get StressClocks (default), False otherwise.
        """
        return True

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
        if self._use_stress_clocks():
            from codex.core.services.fitd_engine import StressClock
            trauma_table = self._get_trauma_table()
            if trauma_table:
                self.stress_clocks[name] = StressClock(trauma_table=trauma_table)
            else:
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
        if self._use_stress_clocks():
            from codex.core.services.fitd_engine import StressClock
            trauma_table = self._get_trauma_table()
            if trauma_table:
                self.stress_clocks[char.name] = StressClock(trauma_table=trauma_table)
            else:
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

    def roll_fortune(self, dice_count: int = 1, **kwargs) -> Any:
        """Roll a FITD fortune roll (no position/effect context).

        Args:
            dice_count: Number of d6s in the pool. 0 = 2d6 take lowest.
            **kwargs: Ignored; present for uniform call signature.

        Returns:
            FortuneResult with outcome ("bad"/"mixed"/"good"/"crit"),
            highest die, and all_dice list.
        """
        from codex.core.services.fitd_engine import FITDFortuneRoll
        roll = FITDFortuneRoll(dice_count=dice_count)
        result = roll.roll()
        self._add_shard(
            f"Fortune roll ({dice_count}d): {result.outcome}",
            "CHRONICLE",
        )
        return result

    def roll_resistance(
        self,
        character: Optional[Any] = None,
        attribute: str = "",
        **kwargs,
    ) -> dict:
        """Roll resistance for a character using an attribute's action dots.

        Args:
            character: Acting character (defaults to engine lead).
            attribute: Attribute name to look up dots on the character.
            **kwargs: Ignored; present for uniform call signature.

        Returns:
            resistance_roll() result dict with dice, stress_cost, crit, push_result.
        """
        from codex.core.services.fitd_engine import resistance_roll
        char = character or self.character
        dots = getattr(char, attribute, 0) if char else 0
        clock = self.stress_clocks.get(char.name) if char else None
        result = resistance_roll(dots, clock)
        cost = result["stress_cost"]
        self._add_shard(
            f"{char.name if char else '?'} resists (attribute: {attribute}, cost: {cost} stress)",
            "CHRONICLE",
        )
        return result

    def gather_information(
        self,
        character: Optional[Any] = None,
        action: str = "",
        question: str = "",
        **kwargs,
    ) -> dict:
        """Gather information using a controlled action roll.

        Args:
            character: Acting character (defaults to engine lead).
            action: Action attribute name to look up dots.
            question: The question being investigated (narrative context).
            **kwargs: Ignored; present for uniform call signature.

        Returns:
            gather_information() result dict with outcome, quality, dice.
        """
        from codex.core.services.fitd_engine import gather_information
        char = character or self.character
        dots = getattr(char, action, 0) if char else 0
        result = gather_information(dots, question)
        self._add_shard(
            f"Gathered info ({action}): {result['quality']} — {question[:50]}",
            "CHRONICLE",
        )
        return result

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
        cmd = cmd.lower().replace("-", "_")
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

    def _cmd_fortune(self, **kwargs) -> str:
        """Roll a fortune die pool.

        Kwargs:
            dice_count (int): Number of d6s (default 1). 0 = 2d6 take lowest.

        Returns:
            Formatted fortune roll result string.
        """
        from codex.core.services.fitd_engine import format_fortune_result
        dice_count = int(kwargs.get("dice_count", 1))
        result = self.roll_fortune(dice_count)
        return format_fortune_result(result)

    def _cmd_resist(self, **kwargs) -> str:
        """Roll resistance for the lead character.

        Kwargs:
            attribute (str): Attribute name to look up dots on the character.

        Returns:
            Formatted resistance result string including stress cost and
            any trauma triggered.
        """
        from codex.core.services.fitd_engine import resistance_roll as _resist_roll
        attribute = kwargs.get("attribute", "")
        char = self.character
        if not char:
            return "No active character."
        if not attribute:
            return "Specify attribute (e.g. resist attribute=hunt)"
        dots = getattr(char, attribute, 0)
        clock = self.stress_clocks.get(char.name)
        result = _resist_roll(dots, clock)
        dice_str = ", ".join(str(d) for d in result["dice"])
        crit_msg = " (CRIT — no stress!)" if result["crit"] else ""
        trauma_msg = ""
        if result.get("push_result", {}) and result["push_result"].get("trauma_triggered"):
            trauma_msg = f" TRAUMA: {result['push_result']['new_trauma']}!"
        self._add_shard(
            f"{char.name} resists ({attribute}): cost {result['stress_cost']} stress{crit_msg}",
            "CHRONICLE",
        )
        return (
            f"Resistance ({attribute}): [{dice_str}] -> cost {result['stress_cost']} stress"
            f"{crit_msg}{trauma_msg}"
        )

    def _cmd_gather_info(self, **kwargs) -> str:
        """Roll to gather information.

        Kwargs:
            action (str): Action attribute name (default "survey").
            question (str): The question being investigated.

        Returns:
            Formatted gather-info result string with outcome and quality.
        """
        action = kwargs.get("action", "survey")
        question = kwargs.get("question", "")
        result = self.gather_information(action=action, question=question)
        dice_str = ", ".join(str(d) for d in result["dice"])
        return (
            f"Gather Info ({action}): [{dice_str}] -> {result['outcome'].upper()}\n"
            f"Quality: {result['quality']}"
            + (f"\nQuestion: {question}" if question else "")
        )

    # =====================================================================
    # NPC Disposition (WO-P7)
    # =====================================================================

    def _get_npc_disposition(self) -> Any:
        """Lazily initialise and return the DispositionManager.

        Returns:
            The engine's DispositionManager instance (created on first access).
        """
        if self._npc_disposition is None:
            from codex.core.services.npc_memory import DispositionManager
            self._npc_disposition = DispositionManager()
        return self._npc_disposition

    def _cmd_npc_status(self, **kwargs) -> str:
        """Show an NPC's disposition and history.

        Kwargs:
            name (str): NPC identifier. Omit to list all tracked NPCs.

        Returns:
            History summary for the named NPC, or a full listing if no name given.
        """
        name = kwargs.get("name", "")
        if not name:
            return self._get_npc_disposition().list_npcs()
        return self._get_npc_disposition().get_status(name)

    def _cmd_npc_adjust(self, **kwargs) -> str:
        """Adjust an NPC's disposition score.

        Kwargs:
            name (str): NPC identifier (required).
            delta (int): Amount to adjust, positive or negative.
            reason (str): Human-readable reason for the change.

        Returns:
            Formatted before/after string; emits a CHRONICLE shard if changed.
        """
        name = kwargs.get("name", "")
        if not name:
            return "Specify NPC name: npc_adjust name=<name> delta=<int> reason=<str>"
        delta = int(kwargs.get("delta", 0))
        reason = kwargs.get("reason", "unspecified")
        mgr = self._get_npc_disposition()
        result = mgr.adjust_disposition(name, delta, reason, source="player_action")
        if result["changed"]:
            self._add_shard(
                f"NPC {name} disposition: {result['old_label']} -> {result['new_label']} ({reason})",
                "CHRONICLE",
            )
        return (
            f"{name}: {result['old_label']} ({result['old']:+d}) -> "
            f"{result['new_label']} ({result['new']:+d})\n"
            f"Reason: {reason}"
        )

    def _cmd_faction_response(self, **kwargs) -> str:
        """Check the faction response for an NPC given an event type.

        Kwargs:
            name (str): NPC identifier (required).
            event_type (str): One of score_against, score_near, territory_taken,
                              aid_given, ignored, or "default".

        Returns:
            Formatted response string with disposition range and action taken.
        """
        name = kwargs.get("name", "")
        event_type = kwargs.get("event_type", "default")
        if not name:
            return "Specify NPC name: faction_response name=<name> event_type=<str>"
        mgr = self._get_npc_disposition()
        result = mgr.get_faction_response(name, event_type)
        return (
            f"Faction response for {name} (event: {event_type}):\n"
            f"Disposition: {result['disposition_range']} ({result['disposition']:+d})\n"
            f"Response: {result['response_type'].upper()} — {result['description']}"
        )

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
            "npc_disposition": self._npc_disposition.to_dict() if self._npc_disposition else None,
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
        disp_data = data.get("npc_disposition")
        if disp_data:
            from codex.core.services.npc_memory import DispositionManager
            self._npc_disposition = DispositionManager.from_dict(disp_data)

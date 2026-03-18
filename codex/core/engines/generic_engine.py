"""
codex/core/engines/generic_engine.py — Generic Fallback Engine
==============================================================
Fallback engine for game systems that have a manifest but no custom
implementation.  Reads resolution_mechanic and character_stats from the
manifest to provide a playable (if minimal) experience.

Dispatch routing based on manifest.resolution_mechanic:
  - "fitd" / "forged_in_the_dark"  -> FITDActionRoll (d6-pool)
  - "pbta" / "powered_by_apocalypse" -> PbtAActionRoll (2d6+stat)
  - anything else                  -> d20 roll via codex.core.dice

Registration:
    register_engine("generic", GenericEngine)
    # Systems without a concrete engine fall back to GenericEngine.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from codex.core.engines.narrative_base import NarrativeEngineBase


# =====================================================================
# Minimal Character dataclass for GenericEngine
# =====================================================================

class GenericCharacter:
    """A bare-bones character for use with GenericEngine.

    Stats are stored in a free-form dict driven by the manifest's
    character_stats field.
    """

    def __init__(self, name: str, setting_id: str = "", **kwargs: Any) -> None:
        self.name = name
        self.setting_id = setting_id
        # Store any extra kwargs as stats
        self.stats: Dict[str, Any] = kwargs

    def is_alive(self) -> bool:
        """Generic characters are always considered active."""
        return True

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        return {"name": self.name, "setting_id": self.setting_id, **self.stats}

    @classmethod
    def from_dict(cls, data: dict) -> "GenericCharacter":
        """Deserialize from a plain dict."""
        name = data.pop("name", "Unknown")
        setting_id = data.pop("setting_id", "")
        return cls(name=name, setting_id=setting_id, **data)


# =====================================================================
# Generic Engine
# =====================================================================

class GenericEngine(NarrativeEngineBase):
    """Generic fallback engine for systems without custom code.

    Uses manifest metadata for character stats and resolution mechanic.
    Dispatches dice to PbtA, FITD, or d20 based on manifest.
    Unknown commands are described as narrative actions.

    Attributes:
        system_id: From manifest or "generic".
        display_name: From manifest or "Generic System".
        resolution_mechanic: The dice mechanic string from manifest.
        manifest: The full manifest dict (may be None).
    """

    system_id = "generic"
    system_family = "GENERIC"
    display_name = "Generic System"

    def __init__(
        self,
        system_id: str = "generic",
        manifest: Optional[dict] = None,
    ) -> None:
        """Initialize from manifest metadata.

        Args:
            system_id: The system identifier string.
            manifest: Parsed system_manifest.json dict (optional).
        """
        super().__init__()
        self.manifest: Optional[dict] = manifest or {}
        # Override class attributes from manifest
        if system_id:
            self.system_id = system_id
        mf = self.manifest
        self.display_name = mf.get("display_name", self.display_name)
        self.system_family = mf.get("system_family", system_id.upper())
        self.resolution_mechanic: str = mf.get("resolution_mechanic", "d20")
        self._char_stat_keys: List[str] = mf.get("character_stats", [])

        # Lazy roller references
        self._pbta_roller: Optional[Any] = None
        self._fitd_roller_class: Optional[Any] = None

    # =====================================================================
    # Abstract hook implementations
    # =====================================================================

    def _create_character(self, name: str, **kwargs) -> GenericCharacter:
        """Create a GenericCharacter seeded with manifest stat keys.

        Args:
            name: Character's name.
            **kwargs: Additional stat overrides.

        Returns:
            A GenericCharacter with default stats from manifest.
        """
        # Seed default stats from manifest character_stats
        defaults = {stat: 0 for stat in self._char_stat_keys}
        defaults.update(kwargs)
        return GenericCharacter(name=name, **defaults)

    def _get_command_registry(self) -> Dict[str, Callable]:
        """Return command registry with roll, status, stats.

        Returns:
            Dict mapping command name -> handler method.
        """
        return {
            "roll": self._cmd_roll,
            "status": self._cmd_status,
            "stats": self._cmd_stats,
        }

    def _format_status(self) -> str:
        """Return status string with manifest metadata.

        Returns:
            Human-readable status string.
        """
        lead = self.party[0] if self.party else None
        mechanic = self.resolution_mechanic
        return (
            f"{self.display_name} | "
            f"Resolution: {mechanic} | "
            f"Party: {len(self.party)} | "
            f"Lead: {lead.name if lead else 'None'}"
        )

    # =====================================================================
    # Resolution dispatch
    # =====================================================================

    def _cmd_roll(self, **kwargs) -> str:
        """Route a roll to the correct resolution mechanic.

        Kwargs:
            action: Action name or stat key (str).
            bonus: Integer bonus to add (default 0).

        Returns:
            Human-readable roll result string.
        """
        mech = self.resolution_mechanic.lower()
        action = kwargs.get("action", "")
        bonus = int(kwargs.get("bonus", 0))

        if mech in ("fitd", "forged_in_the_dark", "action_roll"):
            return self._roll_fitd(action, bonus)
        elif mech in ("pbta", "powered_by_apocalypse", "2d6"):
            return self._roll_pbta(bonus)
        else:
            return self._roll_d20(bonus)

    def _roll_fitd(self, action: str, bonus_dice: int) -> str:
        """Roll FITD d6-pool resolution.

        Args:
            action: Action attribute name on current character.
            bonus_dice: Extra dice from teamwork.

        Returns:
            Formatted roll result string.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, format_roll_result
        char = self.character
        dots = getattr(char, action, 0) if char else 0
        roll = FITDActionRoll(dice_count=max(1, dots + bonus_dice))
        result = roll.roll()
        return format_roll_result(result)

    def _roll_pbta(self, stat_bonus: int) -> str:
        """Roll PbtA 2d6+stat resolution.

        Args:
            stat_bonus: Stat modifier to add.

        Returns:
            Formatted roll result string.
        """
        from codex.core.services.pbta_engine import PbtAActionRoll
        if self._pbta_roller is None:
            self._pbta_roller = PbtAActionRoll()
        result = self._pbta_roller.roll_move(stat_bonus=stat_bonus)
        return self._pbta_roller.format_result(result)

    def _roll_d20(self, bonus: int) -> str:
        """Roll d20+bonus resolution.

        Args:
            bonus: Integer bonus to add.

        Returns:
            Formatted roll result string.
        """
        from codex.core.dice import roll_dice
        _, rolls, _ = roll_dice("1d20")
        raw = rolls[0]
        total = raw + bonus
        crit = " [CRITICAL HIT]" if raw == 20 else ""
        fumble = " [FUMBLE]" if raw == 1 else ""
        return f"d20: {raw} + {bonus} = {total}{crit}{fumble}"

    # =====================================================================
    # Stat display
    # =====================================================================

    def _cmd_stats(self, **kwargs) -> str:
        """Show character stats based on manifest character_stats field.

        Returns:
            Formatted character sheet string.
        """
        char = self.character
        if not char:
            return "No character created. Use create_character() first."
        lines = [f"Character: {char.name}"]
        if self._char_stat_keys:
            lines.append("Stats:")
            for stat in self._char_stat_keys:
                val = getattr(char, stat, char.stats.get(stat, 0))
                lines.append(f"  {stat.title()}: {val}")
        else:
            if char.stats:
                lines.append("Stats:")
                for k, v in char.stats.items():
                    lines.append(f"  {k.title()}: {v}")
            else:
                lines.append("  No stats defined in manifest.")
        return "\n".join(lines)

    # =====================================================================
    # Status override
    # =====================================================================

    def _cmd_status(self, **kwargs) -> str:
        """Show engine status from manifest metadata."""
        return self._format_status()

    # =====================================================================
    # Save / Load (extends NarrativeEngineBase)
    # =====================================================================

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state including manifest metadata.

        Returns:
            Base state dict plus resolution_mechanic and manifest snapshot.
        """
        state = super().save_state()
        state["resolution_mechanic"] = self.resolution_mechanic
        state["char_stat_keys"] = self._char_stat_keys
        return state

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict.

        Args:
            data: Dict from a previous save_state() call.
        """
        self.resolution_mechanic = data.get(
            "resolution_mechanic", self.resolution_mechanic
        )
        self._char_stat_keys = data.get("char_stat_keys", self._char_stat_keys)
        # Party restore — GenericCharacter supports from_dict
        from codex.core.services.fitd_engine import StressClock, UniversalClock
        self.setting_id = data.get("setting_id", "")
        self.party = [
            GenericCharacter.from_dict(dict(d))
            for d in data.get("party", [])
        ]
        self.character = self.party[0] if self.party else None
        self.stress_clocks = {
            k: StressClock.from_dict(v)
            for k, v in data.get("stress", {}).items()
        }
        self.faction_clocks = [
            UniversalClock.from_dict(c)
            for c in data.get("faction_clocks", [])
        ]


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("generic", GenericEngine)
except ImportError:
    pass

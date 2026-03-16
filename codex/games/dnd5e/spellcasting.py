"""
codex.games.dnd5e.spellcasting
================================
Spell slot tracking, concentration management, and spell preparation
for D&D 5e characters.

Supports:
  - Full casters (bard, cleric, druid, sorcerer, wizard): full slot table L1-L20
  - Half casters (paladin, ranger, artificer): slots up to L5 only
  - Warlock pact magic: all slots same level, regain on short rest
  - Non-casters (fighter, barbarian, rogue, monk): no slots
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random


# =========================================================================
# SPELL SLOT TABLES
# =========================================================================

# Full caster spell slot table: character level 1-20, slots per spell level 1-9
SPELL_SLOT_TABLE: Dict[int, Dict[int, int]] = {
    1:  {1: 2},
    2:  {1: 3},
    3:  {1: 4, 2: 2},
    4:  {1: 4, 2: 3},
    5:  {1: 4, 2: 3, 3: 2},
    6:  {1: 4, 2: 3, 3: 3},
    7:  {1: 4, 2: 3, 3: 3, 4: 1},
    8:  {1: 4, 2: 3, 3: 3, 4: 2},
    9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}

# Half-caster slot table: effective caster level = class level // 2, capped at L5
HALF_CASTER_SLOT_TABLE: Dict[int, Dict[int, int]] = {}
for _lvl in range(1, 21):
    _effective = max(1, _lvl // 2)
    _raw = SPELL_SLOT_TABLE.get(_effective, {})
    HALF_CASTER_SLOT_TABLE[_lvl] = {k: v for k, v in _raw.items() if k <= 5}

# Warlock pact magic: all slots at the same spell level, regain on short rest
WARLOCK_SLOT_TABLE: Dict[int, Dict[str, int]] = {
    1:  {"slots": 1, "slot_level": 1},
    2:  {"slots": 2, "slot_level": 1},
    3:  {"slots": 2, "slot_level": 2},
    4:  {"slots": 2, "slot_level": 2},
    5:  {"slots": 2, "slot_level": 3},
    6:  {"slots": 2, "slot_level": 3},
    7:  {"slots": 2, "slot_level": 4},
    8:  {"slots": 2, "slot_level": 4},
    9:  {"slots": 2, "slot_level": 5},
    10: {"slots": 2, "slot_level": 5},
    11: {"slots": 3, "slot_level": 5},
    12: {"slots": 3, "slot_level": 5},
    13: {"slots": 3, "slot_level": 5},
    14: {"slots": 3, "slot_level": 5},
    15: {"slots": 3, "slot_level": 5},
    16: {"slots": 3, "slot_level": 5},
    17: {"slots": 4, "slot_level": 5},
    18: {"slots": 4, "slot_level": 5},
    19: {"slots": 4, "slot_level": 5},
    20: {"slots": 4, "slot_level": 5},
}

FULL_CASTER_CLASSES = {"bard", "cleric", "druid", "sorcerer", "wizard"}
HALF_CASTER_CLASSES = {"paladin", "ranger", "artificer"}


# =========================================================================
# SPELL SLOT TRACKER
# =========================================================================

class SpellSlotTracker:
    """
    Tracks spell slot usage and recovery for a single character.

    Handles full casters, half casters, warlocks, and non-casters.
    Warlock pact magic slots all exist at `pact_slot_level` and recover
    on a short rest (or long rest).
    """

    def __init__(self, character_class: str, level: int) -> None:
        """
        Initialise tracker for a character.

        Args:
            character_class: D&D 5e class name (case-insensitive).
            level: Character level (1–20).
        """
        self.character_class = character_class.lower()
        self.level = level
        self.is_warlock = self.character_class == "warlock"
        self.pact_slot_level: int = 1  # Only meaningful for warlocks
        self.max_slots: Dict[int, int] = {}
        self.current_slots: Dict[int, int] = {}
        self._init_slots()

    def _init_slots(self) -> None:
        """Populate max_slots and current_slots based on class and level."""
        if self.is_warlock:
            info = WARLOCK_SLOT_TABLE.get(self.level, {"slots": 1, "slot_level": 1})
            self.pact_slot_level = info["slot_level"]
            self.max_slots = {self.pact_slot_level: info["slots"]}
        elif self.character_class in FULL_CASTER_CLASSES:
            self.max_slots = dict(SPELL_SLOT_TABLE.get(self.level, {}))
        elif self.character_class in HALF_CASTER_CLASSES:
            self.max_slots = dict(HALF_CASTER_SLOT_TABLE.get(self.level, {}))
        else:
            # Non-casters have no spell slots
            self.max_slots = {}
        self.current_slots = dict(self.max_slots)

    # ─── Slot queries ──────────────────────────────────────────────────

    def can_cast(self, spell_level: int) -> bool:
        """
        Check whether at least one slot is available at the given spell level.

        Cantrips (spell_level == 0) are always castable.
        Warlock slots all sit at pact_slot_level; any level <= that is valid.

        Args:
            spell_level: Spell level 0–9.

        Returns:
            True if casting is possible.
        """
        if spell_level == 0:
            return True
        if self.is_warlock:
            return (
                self.current_slots.get(self.pact_slot_level, 0) > 0
                and spell_level <= self.pact_slot_level
            )
        return self.current_slots.get(spell_level, 0) > 0

    def expend_slot(self, spell_level: int) -> bool:
        """
        Consume one slot at the given level.

        Args:
            spell_level: Slot level to expend (0 for cantrip — no-op).

        Returns:
            True if a slot was successfully expended, False if none available.
        """
        if spell_level == 0:
            return True
        if self.is_warlock:
            key = self.pact_slot_level
            if self.current_slots.get(key, 0) > 0:
                self.current_slots[key] -= 1
                return True
            return False
        if self.current_slots.get(spell_level, 0) > 0:
            self.current_slots[spell_level] -= 1
            return True
        return False

    def recover_slots(self, rest_type: str = "long") -> None:
        """
        Recover spell slots after a rest.

        Full casters and half casters only recover on a long rest.
        Warlocks recover all pact slots on a short or long rest.

        Args:
            rest_type: "short" or "long".
        """
        if rest_type == "long" or self.is_warlock:
            self.current_slots = dict(self.max_slots)
        # Short rest: non-warlocks gain nothing (Arcane Recovery handled externally)

    def get_available_levels(self) -> List[int]:
        """Return list of spell levels with at least one slot remaining."""
        return [lvl for lvl, count in self.current_slots.items() if count > 0]

    # ─── Serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise tracker state for save/load."""
        return {
            "character_class": self.character_class,
            "level": self.level,
            "max_slots": {str(k): v for k, v in self.max_slots.items()},
            "current_slots": {str(k): v for k, v in self.current_slots.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpellSlotTracker":
        """Restore a SpellSlotTracker from a saved dict."""
        tracker = cls(data["character_class"], data["level"])
        tracker.max_slots = {int(k): v for k, v in data.get("max_slots", {}).items()}
        tracker.current_slots = {int(k): v for k, v in data.get("current_slots", {}).items()}
        return tracker

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SpellSlotTracker({self.character_class!r}, L{self.level}, "
            f"slots={self.current_slots})"
        )


# =========================================================================
# CONCENTRATION TRACKER
# =========================================================================

class ConcentrationTracker:
    """
    Tracks whether a character is concentrating on a spell.

    D&D 5e rule: a character may concentrate on at most one spell at a time.
    Starting a new concentration spell breaks the old one. Taking damage
    requires a Constitution saving throw (DC = max(10, damage // 2)).
    """

    def __init__(self) -> None:
        self.active_spell: Optional[str] = None

    def start(self, spell_name: str) -> str:
        """
        Begin concentrating on a new spell, breaking any current concentration.

        Args:
            spell_name: Name of the spell to concentrate on.

        Returns:
            A human-readable description of what happened.
        """
        old = self.active_spell
        self.active_spell = spell_name
        if old:
            return f"Concentration on {old} broken. Now concentrating on {spell_name}."
        return f"Concentrating on {spell_name}."

    def check(
        self,
        damage: int,
        constitution_mod: int = 0,
        proficiency: int = 0,
    ) -> dict:
        """
        Roll a Constitution saving throw to maintain concentration.

        DC = max(10, damage // 2). Natural 20 always succeeds.
        If the save fails, concentration is broken.

        Args:
            damage: Amount of damage taken that triggered the check.
            constitution_mod: Character's Constitution modifier.
            proficiency: Proficiency bonus if the character has War Caster or Resilient (Con).

        Returns:
            Dict with keys: required, spell, dc, roll, total, success, and optionally lost.
        """
        if not self.active_spell:
            return {"required": False}

        dc = max(10, damage // 2)
        roll = random.randint(1, 20)
        total = roll + constitution_mod + proficiency
        success = (roll == 20) or (total >= dc)

        result: dict = {
            "required": True,
            "spell": self.active_spell,
            "dc": dc,
            "roll": roll,
            "total": total,
            "success": success,
        }
        if not success:
            result["lost"] = self.active_spell
            self.active_spell = None
        return result

    def break_concentration(self) -> Optional[str]:
        """
        Forcibly end concentration (e.g. incapacitated, unconscious, dead).

        Returns:
            Name of the spell that was broken, or None if not concentrating.
        """
        old = self.active_spell
        self.active_spell = None
        return old

    # ─── Serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise tracker state for save/load."""
        return {"active_spell": self.active_spell}

    @classmethod
    def from_dict(cls, data: dict) -> "ConcentrationTracker":
        """Restore a ConcentrationTracker from a saved dict."""
        t = cls()
        t.active_spell = data.get("active_spell")
        return t

    def __repr__(self) -> str:  # pragma: no cover
        return f"ConcentrationTracker(active={self.active_spell!r})"


# =========================================================================
# SPELL MANAGER
# =========================================================================

class SpellManager:
    """
    Manages known/prepared spells for a character.

    "Known" casters (bard, sorcerer, warlock, ranger, artificer) learn a fixed
    list of spells that are always available.
    "Prepared" casters (cleric, druid, paladin, wizard) choose a daily subset
    from their full list; max prepared = ability_mod + level.
    """

    def __init__(
        self, character_class: str, level: int, ability_mod: int = 0
    ) -> None:
        """
        Initialise spell manager.

        Args:
            character_class: D&D 5e class name (case-insensitive).
            level: Character level (1–20).
            ability_mod: Spellcasting ability modifier (used for max prepared).
        """
        self.character_class = character_class.lower()
        self.level = level
        self.ability_mod = ability_mod
        self.known_spells: List[str] = []
        self.prepared_spells: List[str] = []
        self.cantrips: List[str] = []
        self._load_casting_rules()

    def _load_casting_rules(self) -> None:
        """Determine casting type and ability for this class."""
        # Prepared casters choose their spells daily
        _PREPARED = {"cleric", "druid", "paladin", "wizard"}
        # Known casters have a fixed learned list
        _KNOWN = {"bard", "ranger", "sorcerer", "warlock", "artificer"}
        _ABILITY_MAP = {
            "bard": "charisma", "cleric": "wisdom", "druid": "wisdom",
            "paladin": "charisma", "ranger": "wisdom", "sorcerer": "charisma",
            "warlock": "charisma", "wizard": "intelligence", "artificer": "intelligence",
        }
        if self.character_class in _PREPARED:
            self.casting_type = "prepared"
        elif self.character_class in _KNOWN:
            self.casting_type = "known"
        else:
            self.casting_type = "none"
        self.casting_ability = _ABILITY_MAP.get(self.character_class, "intelligence")

    # ─── Preparation ───────────────────────────────────────────────────

    def get_max_prepared(self) -> int:
        """
        Return maximum number of spells that can be prepared.

        Only meaningful for "prepared" casters.

        Returns:
            Max prepared count (always at least 1 for prepared casters).
        """
        if self.casting_type == "prepared":
            return max(1, self.ability_mod + self.level)
        return 0

    def prepare(self, spell_name: str) -> str:
        """
        Prepare a spell for a "prepared" caster.

        Args:
            spell_name: Name of the spell to prepare.

        Returns:
            Result message.
        """
        if not spell_name:
            return "No spell name provided."
        if spell_name in self.prepared_spells:
            return f"{spell_name} is already prepared."
        if (
            self.casting_type == "prepared"
            and len(self.prepared_spells) >= self.get_max_prepared()
        ):
            return f"Cannot prepare more spells (max {self.get_max_prepared()})."
        self.prepared_spells.append(spell_name)
        return f"Prepared {spell_name}."

    def unprepare(self, spell_name: str) -> str:
        """
        Remove a spell from the prepared list.

        Args:
            spell_name: Name of the spell to unprepare.

        Returns:
            Result message.
        """
        if spell_name in self.prepared_spells:
            self.prepared_spells.remove(spell_name)
            return f"Unprepared {spell_name}."
        return f"{spell_name} is not prepared."

    # ─── Casting checks ────────────────────────────────────────────────

    def can_cast_spell(self, spell_name: str) -> bool:
        """
        Check whether a spell name is available to cast (ignoring slots).

        Cantrips are always available regardless of preparation rules.

        Args:
            spell_name: Name of the spell.

        Returns:
            True if the spell can be cast (still requires an available slot).
        """
        if spell_name in self.cantrips:
            return True
        if self.casting_type == "known":
            return spell_name in self.known_spells
        if self.casting_type == "prepared":
            return spell_name in self.prepared_spells
        return False

    def cast_spell(
        self, spell_name: str, slot_tracker: SpellSlotTracker, spell_level: int = 0
    ) -> str:
        """
        Attempt to cast a spell, expending a slot if needed.

        Args:
            spell_name: Name of the spell to cast.
            slot_tracker: The character's SpellSlotTracker.
            spell_level: Slot level to use (0 for cantrips).

        Returns:
            Human-readable result string.
        """
        if not self.can_cast_spell(spell_name):
            return f"You don't have {spell_name} prepared or known."
        if spell_level > 0 and not slot_tracker.can_cast(spell_level):
            return f"No available level {spell_level} spell slots."
        if spell_level > 0:
            slot_tracker.expend_slot(spell_level)
        level_str = f" at level {spell_level}" if spell_level > 0 else " (cantrip)"
        return f"Cast {spell_name}{level_str}."

    # ─── Serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise manager state for save/load."""
        return {
            "character_class": self.character_class,
            "level": self.level,
            "ability_mod": self.ability_mod,
            "known_spells": list(self.known_spells),
            "prepared_spells": list(self.prepared_spells),
            "cantrips": list(self.cantrips),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpellManager":
        """Restore a SpellManager from a saved dict."""
        m = cls(
            data["character_class"],
            data["level"],
            data.get("ability_mod", 0),
        )
        m.known_spells = data.get("known_spells", [])
        m.prepared_spells = data.get("prepared_spells", [])
        m.cantrips = data.get("cantrips", [])
        return m

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SpellManager({self.character_class!r}, L{self.level}, "
            f"type={self.casting_type!r})"
        )

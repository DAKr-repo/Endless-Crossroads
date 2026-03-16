"""
codex.core.mechanics.conditions — Persistent Status Effect Tracker
===================================================================

Tracks conditions (buffs/debuffs) on named entities across combat rounds.
System-agnostic — used by all engine families.

Design:
  - ConditionType enum covers standard + Burnwillow-specific conditions
  - Condition dataclass tracks duration, saves, and modifiers
  - ConditionTracker manages per-entity condition lists with tick/apply/remove

WO-V34.0: The Sovereign Dashboard — Gap #7
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING


# =========================================================================
# CONDITION TYPES
# =========================================================================

class ConditionType(Enum):
    """Standard condition types across all engine families."""
    POISONED = "Poisoned"
    STUNNED = "Stunned"
    BLINDED = "Blinded"
    FRIGHTENED = "Frightened"
    GRAPPLED = "Grappled"
    BLIGHTED = "Blighted"       # Burnwillow: DR penalty
    ROTTED = "Rotted"           # Burnwillow: HP drain per round
    BURNING = "Burning"         # Damage per round
    BLESSED = "Blessed"         # +2 to saves
    HASTED = "Hasted"           # Extra action (DnD5e/Cosmere)


# =========================================================================
# CONDITION DATACLASS
# =========================================================================

@dataclass
class Condition:
    """A single active condition on an entity."""
    condition_type: ConditionType
    duration: int               # Rounds remaining, -1 = until save, -2 = permanent
    source: str = ""            # "Spore-Crawler attack", "Mage spell"
    save_dc: int = 0            # DC to save against each round (0 = no save)
    save_stat: str = ""         # "CON", "WIS", "GRIT"
    modifier: int = 0           # Generic modifier (-2 for poison, +2 for blessed)

    def to_dict(self) -> dict:
        return {
            "type": self.condition_type.value,
            "duration": self.duration,
            "source": self.source,
            "save_dc": self.save_dc,
            "save_stat": self.save_stat,
            "modifier": self.modifier,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Condition":
        return cls(
            condition_type=ConditionType(data["type"]),
            duration=data.get("duration", 1),
            source=data.get("source", ""),
            save_dc=data.get("save_dc", 0),
            save_stat=data.get("save_stat", ""),
            modifier=data.get("modifier", 0),
        )


# Default modifiers for standard conditions
CONDITION_DEFAULTS: Dict[ConditionType, int] = {
    ConditionType.POISONED: -2,
    ConditionType.STUNNED: 0,
    ConditionType.BLINDED: -2,
    ConditionType.FRIGHTENED: -1,
    ConditionType.GRAPPLED: 0,
    ConditionType.BLIGHTED: -1,
    ConditionType.ROTTED: -1,
    ConditionType.BURNING: 0,
    ConditionType.BLESSED: 2,
    ConditionType.HASTED: 0,
}

# Icon mapping for bot/embed rendering (WO-V35.0)
CONDITION_ICONS: Dict[ConditionType, str] = {
    ConditionType.POISONED: "\U0001f9ea",
    ConditionType.STUNNED: "\U0001f4ab",
    ConditionType.BLINDED: "\U0001f648",
    ConditionType.FRIGHTENED: "\U0001f631",
    ConditionType.GRAPPLED: "\U0001faa2",
    ConditionType.BLIGHTED: "\U0001f342",
    ConditionType.ROTTED: "\U0001f480",
    ConditionType.BURNING: "\U0001f525",
    ConditionType.BLESSED: "\u2728",
    ConditionType.HASTED: "\u26a1",
}


def format_condition_icons(conditions: list) -> str:
    """Format Condition objects as icon string for bot/embed rendering.

    Returns '' if empty.
    """
    if not conditions:
        return ""
    parts = []
    for c in conditions:
        if isinstance(c, Condition):
            icon = CONDITION_ICONS.get(c.condition_type, "\u2753")
            parts.append(f"{icon}{c.condition_type.value}")
        elif isinstance(c, dict):
            try:
                ctype = ConditionType(c.get("type", ""))
                icon = CONDITION_ICONS.get(ctype, "\u2753")
                parts.append(f"{icon}{ctype.value}")
            except (ValueError, KeyError):
                parts.append(f"\u2753{c.get('type', '?')}")
    return " ".join(parts)


# =========================================================================
# CONDITION TRACKER
# =========================================================================

@dataclass
class ConditionTracker:
    """Manages active conditions for all entities."""
    _conditions: Dict[str, List[Condition]] = field(default_factory=dict)

    def apply(self, name: str, condition: Condition) -> str:
        """Apply a condition to an entity. Returns status message."""
        if name not in self._conditions:
            self._conditions[name] = []

        # Replace existing condition of same type (refresh duration)
        self._conditions[name] = [
            c for c in self._conditions[name]
            if c.condition_type != condition.condition_type
        ]
        self._conditions[name].append(condition)

        dur = condition.duration
        dur_str = (
            "permanent" if dur == -2
            else "until save" if dur == -1
            else f"{dur} rounds"
        )
        return f"{name} is now {condition.condition_type.value} ({dur_str})"

    def remove(self, name: str, ctype: ConditionType) -> str:
        """Remove a condition from an entity. Returns status message."""
        if name not in self._conditions:
            return f"{name} has no conditions"

        before = len(self._conditions[name])
        self._conditions[name] = [
            c for c in self._conditions[name]
            if c.condition_type != ctype
        ]
        if len(self._conditions[name]) < before:
            return f"{ctype.value} removed from {name}"
        return f"{name} is not {ctype.value}"

    def tick_round(self, name: str) -> List[str]:
        """Decrement durations for an entity. Returns expired messages."""
        if name not in self._conditions:
            return []

        messages = []
        remaining = []
        for c in self._conditions[name]:
            if c.duration == -2:  # Permanent
                remaining.append(c)
                continue
            if c.duration == -1:  # Until save — stays
                remaining.append(c)
                continue
            c.duration -= 1
            if c.duration <= 0:
                messages.append(f"{c.condition_type.value} expired on {name}")
            else:
                remaining.append(c)

        self._conditions[name] = remaining
        return messages

    def has(self, name: str, ctype: ConditionType) -> bool:
        """Check if an entity has a specific condition."""
        return any(
            c.condition_type == ctype
            for c in self._conditions.get(name, [])
        )

    def get_conditions(self, name: str) -> List[Condition]:
        """Get all active conditions for an entity."""
        return list(self._conditions.get(name, []))

    def get_attack_mod(self, name: str) -> int:
        """Net attack modifier from all conditions."""
        total = 0
        for c in self._conditions.get(name, []):
            if c.condition_type in (
                ConditionType.POISONED, ConditionType.BLINDED,
                ConditionType.BLIGHTED,
            ):
                total += c.modifier or CONDITION_DEFAULTS.get(c.condition_type, 0)
            elif c.condition_type == ConditionType.BLESSED:
                total += c.modifier or CONDITION_DEFAULTS.get(c.condition_type, 0)
        return total

    def get_defense_mod(self, name: str) -> int:
        """Net defense modifier from all conditions."""
        total = 0
        for c in self._conditions.get(name, []):
            if c.condition_type == ConditionType.BLIGHTED:
                total += c.modifier or CONDITION_DEFAULTS.get(c.condition_type, 0)
            elif c.condition_type == ConditionType.HASTED:
                total += 2
        return total

    def should_skip_turn(self, name: str) -> bool:
        """True if entity should skip their turn (Stunned)."""
        return self.has(name, ConditionType.STUNNED)

    def clear_all(self, name: str) -> None:
        """Remove all conditions from an entity."""
        self._conditions.pop(name, None)

    def get_all_entities(self) -> List[str]:
        """Return all entity names with conditions."""
        return [n for n, conds in self._conditions.items() if conds]

    def to_dict(self) -> dict:
        return {
            name: [c.to_dict() for c in conds]
            for name, conds in self._conditions.items()
            if conds
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConditionTracker":
        tracker = cls()
        for name, cond_list in data.items():
            tracker._conditions[name] = [
                Condition.from_dict(c) for c in cond_list
            ]
        return tracker

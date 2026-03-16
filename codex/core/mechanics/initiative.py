"""
codex.core.mechanics.initiative — Turn Order Management
=========================================================

Tracks initiative order for tactical combat across all engine families.
Each engine uses its own die + modifier mapping.

Per-engine initiative stats:
  - Burnwillow: 1d6 + wits_modifier
  - DnD5e: 1d20 + dex_modifier
  - Cosmere: 1d20 + speed_modifier
  - BitD/Crown: not applicable (narrative, no tactical initiative)

WO-V34.0: The Sovereign Dashboard — Gap #6
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# =========================================================================
# INITIATIVE ENTRY
# =========================================================================

@dataclass
class InitiativeEntry:
    """A single combatant in the initiative order."""
    name: str
    roll: int               # Total (die + modifier)
    modifier: int           # DEX mod, Wits mod, etc.
    is_player: bool
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "roll": self.roll,
            "modifier": self.modifier,
            "is_player": self.is_player,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InitiativeEntry":
        return cls(**data)


# =========================================================================
# PER-ENGINE INITIATIVE CONFIG
# =========================================================================

INITIATIVE_CONFIG: Dict[str, Dict[str, int]] = {
    "BURNWILLOW": {"die": 6, "stat": "wits"},
    "DND5E": {"die": 20, "stat": "dexterity"},
    "STC": {"die": 20, "stat": "speed"},
    "BITD": {"die": 6, "stat": "survey"},       # Narrative, rarely used
    "CROWN": {"die": 6, "stat": "sway"},         # Narrative, rarely used
}


# =========================================================================
# INITIATIVE TRACKER
# =========================================================================

@dataclass
class InitiativeTracker:
    """Manages turn order for tactical combat."""
    entries: List[InitiativeEntry] = field(default_factory=list)
    current_index: int = 0
    round_number: int = 1

    def roll_initiative(
        self,
        name: str,
        modifier: int = 0,
        is_player: bool = True,
        die: int = 20,
        rng: Optional[random.Random] = None,
    ) -> InitiativeEntry:
        """Roll initiative for a combatant and add to tracker."""
        _rng = rng or random
        roll = _rng.randint(1, die) + modifier
        entry = InitiativeEntry(
            name=name, roll=roll, modifier=modifier, is_player=is_player,
        )
        self.entries.append(entry)
        return entry

    def sort(self) -> None:
        """Sort entries descending by roll, ties broken by modifier."""
        self.entries.sort(key=lambda e: (e.roll, e.modifier), reverse=True)

    def next_turn(self) -> Optional[InitiativeEntry]:
        """Advance to next active combatant. Wraps to new round."""
        if not self.entries:
            return None

        active = [e for e in self.entries if e.is_active]
        if not active:
            return None

        # Find next active entry
        attempts = 0
        while attempts < len(self.entries):
            self.current_index = (self.current_index + 1) % len(self.entries)
            if self.current_index == 0:
                self.round_number += 1
            if self.entries[self.current_index].is_active:
                return self.entries[self.current_index]
            attempts += 1

        return None

    def current(self) -> Optional[InitiativeEntry]:
        """Return the current combatant."""
        if not self.entries:
            return None
        if self.current_index >= len(self.entries):
            self.current_index = 0
        return self.entries[self.current_index]

    def remove(self, name: str) -> None:
        """Mark a combatant as inactive (dead/fled)."""
        for entry in self.entries:
            if entry.name == name:
                entry.is_active = False
                break

    def reset(self) -> None:
        """Clear all entries for new combat."""
        self.entries.clear()
        self.current_index = 0
        self.round_number = 1

    def get_order(self) -> List[str]:
        """Display-friendly ordered list of active combatant names."""
        return [e.name for e in self.entries if e.is_active]

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "current_index": self.current_index,
            "round_number": self.round_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InitiativeTracker":
        return cls(
            entries=[InitiativeEntry.from_dict(e) for e in data.get("entries", [])],
            current_index=data.get("current_index", 0),
            round_number=data.get("round_number", 1),
        )

"""
codex.core.mechanics.concentration — D&D 5e Concentration Tracking
===================================================================
Tracks which characters are concentrating on spells and prompts for
concentration saves when they take damage.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ConcentrationEntry:
    """A single concentration spell being maintained."""
    spell_name: str
    caster: str
    dc: int = 10  # Base DC for concentration check

    def damage_dc(self, damage: int) -> int:
        """Calculate concentration DC from damage taken."""
        return max(10, damage // 2)


@dataclass
class ConcentrationTracker:
    """Manages concentration spells for D&D 5e."""
    _active: Dict[str, ConcentrationEntry] = field(default_factory=dict)

    def concentrate(self, caster: str, spell_name: str) -> str:
        """Start concentrating on a spell. Drops any existing concentration."""
        old = self._active.get(caster)
        msg = ""
        if old:
            msg = f"{caster} drops concentration on {old.spell_name}. "
        self._active[caster] = ConcentrationEntry(
            spell_name=spell_name, caster=caster,
        )
        return msg + f"{caster} concentrating on {spell_name}."

    def drop(self, caster: str) -> str:
        """Voluntarily drop concentration."""
        entry = self._active.pop(caster, None)
        if not entry:
            return f"{caster} is not concentrating on anything."
        return f"{caster} drops concentration on {entry.spell_name}."

    def damage_check(self, caster: str, damage: int) -> Optional[str]:
        """When a concentrating caster takes damage, return the save prompt."""
        entry = self._active.get(caster)
        if not entry:
            return None
        dc = entry.damage_dc(damage)
        return (
            f"CONCENTRATION CHECK: {caster} took {damage} damage while "
            f"concentrating on {entry.spell_name}. "
            f"DC {dc} Constitution save required!"
        )

    def fail_save(self, caster: str) -> str:
        """Called when concentration save fails."""
        entry = self._active.pop(caster, None)
        if not entry:
            return f"{caster} was not concentrating."
        return f"{caster} loses concentration on {entry.spell_name}!"

    def pass_save(self, caster: str) -> str:
        """Called when concentration save succeeds."""
        entry = self._active.get(caster)
        if not entry:
            return f"{caster} was not concentrating."
        return f"{caster} maintains concentration on {entry.spell_name}."

    def list_active(self) -> str:
        if not self._active:
            return "No active concentration spells."
        lines = ["Active Concentration:"]
        for name, entry in self._active.items():
            lines.append(f"  {name}: {entry.spell_name}")
        return "\n".join(lines)

    def get_concentrating(self) -> Dict[str, str]:
        """Return {caster: spell_name} for all active."""
        return {k: v.spell_name for k, v in self._active.items()}

    def to_dict(self) -> dict:
        return {k: {"spell_name": v.spell_name, "caster": v.caster}
                for k, v in self._active.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "ConcentrationTracker":
        tracker = cls()
        for name, entry in data.items():
            tracker._active[name] = ConcentrationEntry(**entry)
        return tracker

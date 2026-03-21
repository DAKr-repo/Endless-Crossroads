"""
codex.core.mechanics.death_saves — D&D 5e Death Save Tracking
===============================================================
Tracks death saving throws (successes/failures) for downed characters.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DeathSaveState:
    """Death save progress for a single character."""
    successes: int = 0
    failures: int = 0

    @property
    def stabilized(self) -> bool:
        return self.successes >= 3

    @property
    def dead(self) -> bool:
        return self.failures >= 3

    def reset(self):
        self.successes = 0
        self.failures = 0


@dataclass
class DeathSaveTracker:
    """Manages death saves for downed D&D 5e characters."""
    _saves: Dict[str, DeathSaveState] = field(default_factory=dict)

    def start_dying(self, name: str) -> str:
        """Mark a character as downed and begin tracking."""
        self._saves[name] = DeathSaveState()
        return f"{name} is dying! Death saves begin."

    def save_success(self, name: str) -> str:
        """Record a death save success."""
        state = self._saves.get(name)
        if not state:
            return f"{name} is not making death saves."
        state.successes += 1
        if state.stabilized:
            self._saves.pop(name)
            return f"{name} rolls a success ({state.successes}/3). STABILIZED!"
        return f"{name} rolls a success ({state.successes}/3 successes, {state.failures}/3 failures)."

    def save_failure(self, name: str) -> str:
        """Record a death save failure."""
        state = self._saves.get(name)
        if not state:
            return f"{name} is not making death saves."
        state.failures += 1
        if state.dead:
            self._saves.pop(name)
            return f"{name} rolls a failure ({state.failures}/3). {name} is DEAD."
        return f"{name} rolls a failure ({state.successes}/3 successes, {state.failures}/3 failures)."

    def nat20(self, name: str) -> str:
        """Natural 20 — regain 1 HP, stop dying."""
        state = self._saves.pop(name, None)
        if not state:
            return f"{name} is not making death saves."
        return f"{name} rolls a natural 20! Regains 1 HP and is conscious."

    def crit_fail(self, name: str) -> str:
        """Critical damage while dying — counts as 2 failures."""
        state = self._saves.get(name)
        if not state:
            return f"{name} is not making death saves."
        state.failures += 2
        if state.dead:
            self._saves.pop(name)
            return f"{name} takes a critical hit while dying. {name} is DEAD."
        return f"{name} takes a critical hit — 2 failures ({state.failures}/3)."

    def stabilize(self, name: str) -> str:
        """Manually stabilize (e.g. Spare the Dying)."""
        state = self._saves.pop(name, None)
        if not state:
            return f"{name} is not making death saves."
        return f"{name} is stabilized."

    def list_dying(self) -> str:
        if not self._saves:
            return "No characters making death saves."
        lines = ["Death Saves:"]
        for name, state in self._saves.items():
            s = "O" * state.successes + "." * (3 - state.successes)
            f = "X" * state.failures + "." * (3 - state.failures)
            lines.append(f"  {name}: Successes [{s}] Failures [{f}]")
        return "\n".join(lines)

    def is_dying(self, name: str) -> bool:
        return name in self._saves

    def to_dict(self) -> dict:
        return {k: {"successes": v.successes, "failures": v.failures}
                for k, v in self._saves.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "DeathSaveTracker":
        tracker = cls()
        for name, vals in data.items():
            tracker._saves[name] = DeathSaveState(**vals)
        return tracker

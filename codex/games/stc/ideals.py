"""
codex.games.stc.ideals
========================
Radiant Ideal progression system for the Cosmere RPG.

Each Radiant order has five ideals that must be sworn in sequence.
Unlike D&D level-ups, ideal progression requires both narrative readiness
and a dice check representing spiritual resonance with the spren.

Classes:
  - IdealProgression: Tracks a single character's ideal journey
"""

import random
from typing import Any, Dict, List, Optional


# =========================================================================
# IDEAL DIFFICULTY BY LEVEL
# =========================================================================

# DC for the oath_check at each ideal level (1 = automatic on swear, 5 = hardest)
IDEAL_DC: Dict[int, int] = {
    1: 0,   # First Ideal is universal — no check required
    2: 10,
    3: 13,
    4: 16,
    5: 19,
}

# Minimum narrative progress required before the check can be attempted
IDEAL_PROGRESS_THRESHOLD: float = 0.5


# =========================================================================
# IDEAL PROGRESSION
# =========================================================================

class IdealProgression:
    """
    Tracks a Radiant character's journey through the five Ideals.

    Ideal progression requires two conditions:
    1. Sufficient narrative progress (accumulated via add_progress()).
    2. A successful oath_check() dice roll against the ideal's DC.

    Attributes:
        character_name: Name of the character.
        order: Radiant order (lowercase).
        current_ideal: Current ideal level sworn (1-5).
        ideal_progress: Per-ideal narrative progress (0.0-1.0).
        unlocked_abilities: List of ability names unlocked via unlock_ability().
        _rng: Random instance for deterministic testing.
    """

    def __init__(
        self,
        character_name: str,
        order: str = "",
        current_ideal: int = 1,
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        Initialise ideal progression for a character.

        Args:
            character_name: Name of the character.
            order: Radiant order name (lowercase).
            current_ideal: Starting ideal level (1-5). Default 1.
            rng: Optional seeded Random for deterministic tests.
        """
        self.character_name = character_name
        self.order = order.lower()
        self.current_ideal: int = max(1, min(5, current_ideal))
        self.ideal_progress: Dict[int, float] = {i: 0.0 for i in range(1, 6)}
        # Mark all already-sworn ideals as complete
        for i in range(1, self.current_ideal + 1):
            self.ideal_progress[i] = 1.0
        self.unlocked_abilities: List[str] = []
        self._rng = rng or random.Random()

    def get_oath_text(self, ideal_number: int) -> str:
        """
        Return the oath text for a given ideal number.

        Args:
            ideal_number: Ideal level (1-5).

        Returns:
            The oath text string, or a default if order data is unavailable.
        """
        try:
            from codex.forge.reference_data.stc_orders import ORDERS
            order_data = ORDERS.get(self.order, {})
            ideals = order_data.get("ideals", {})
            return ideals.get(ideal_number, "Life before death, strength before weakness.")
        except ImportError:
            return "Life before death, strength before weakness, journey before destination."

    def add_progress(self, amount: float = 0.1, reason: str = "") -> dict:
        """
        Increment narrative progress toward the next ideal.

        Progress accumulates on the *next* ideal to be sworn (current_ideal + 1).
        If already at Ideal 5, progress is tracked but has no further mechanical effect.

        Args:
            amount: Progress amount (0.0-1.0). Default 0.1.
            reason: Description of what caused the progress.

        Returns:
            Dict with keys: next_ideal (int), progress (float), reason (str),
            ready_to_swear (bool), message (str).
        """
        next_ideal = min(5, self.current_ideal + 1)
        if self.current_ideal >= 5:
            return {
                "next_ideal": 5,
                "progress": 1.0,
                "reason": reason,
                "ready_to_swear": False,
                "message": f"{self.character_name} has sworn all 5 Ideals.",
            }

        before = self.ideal_progress[next_ideal]
        self.ideal_progress[next_ideal] = min(1.0, before + max(0.0, amount))
        progress = self.ideal_progress[next_ideal]
        ready = progress >= IDEAL_PROGRESS_THRESHOLD

        reason_str = f" ({reason})" if reason else ""
        return {
            "next_ideal": next_ideal,
            "progress": progress,
            "reason": reason,
            "ready_to_swear": ready,
            "message": (
                f"{self.character_name} progresses toward Ideal {next_ideal}: "
                f"{progress:.0%}{reason_str}. "
                + ("Ready to attempt oath!" if ready else f"Need {IDEAL_PROGRESS_THRESHOLD:.0%} to attempt.")
            ),
        }

    def oath_check(
        self,
        ideal_number: int,
        context: str = "",
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        Attempt to swear the specified ideal.

        Requires:
        - ideal_number == current_ideal + 1 (must swear in sequence)
        - Narrative progress >= IDEAL_PROGRESS_THRESHOLD
        - Successful dice roll against IDEAL_DC[ideal_number]

        On success, current_ideal is incremented and powers unlocked.
        The First Ideal (1) is automatically granted if character has none.

        Args:
            ideal_number: Ideal number to attempt swearing (must be next).
            context: Narrative context description (flavor only).
            rng: Optional Random override.

        Returns:
            Dict with keys: success (bool), ideal_sworn (int or None),
            roll (int), dc (int), oath_text (str), message (str),
            new_powers (list).
        """
        r = rng or self._rng

        # Validate sequence
        if ideal_number != self.current_ideal + 1:
            if ideal_number <= self.current_ideal:
                return {
                    "success": False,
                    "ideal_sworn": None,
                    "roll": 0,
                    "dc": 0,
                    "oath_text": "",
                    "message": f"{self.character_name} has already sworn Ideal {ideal_number}.",
                    "new_powers": [],
                }
            return {
                "success": False,
                "ideal_sworn": None,
                "roll": 0,
                "dc": 0,
                "oath_text": "",
                "message": (
                    f"Must swear Ideal {self.current_ideal + 1} next, "
                    f"not Ideal {ideal_number}."
                ),
                "new_powers": [],
            }

        if self.current_ideal >= 5:
            return {
                "success": False,
                "ideal_sworn": None,
                "roll": 0,
                "dc": 0,
                "oath_text": "",
                "message": f"{self.character_name} has sworn all 5 Ideals.",
                "new_powers": [],
            }

        dc = IDEAL_DC.get(ideal_number, 10)
        oath_text = self.get_oath_text(ideal_number)

        # Check narrative progress requirement
        progress = self.ideal_progress.get(ideal_number, 0.0)
        if progress < IDEAL_PROGRESS_THRESHOLD and dc > 0:
            return {
                "success": False,
                "ideal_sworn": None,
                "roll": 0,
                "dc": dc,
                "oath_text": oath_text,
                "message": (
                    f"{self.character_name} is not yet ready to swear Ideal {ideal_number}. "
                    f"Narrative progress: {progress:.0%} (need {IDEAL_PROGRESS_THRESHOLD:.0%})."
                ),
                "new_powers": [],
            }

        # First Ideal is automatic
        if dc == 0:
            roll = 20
            success = True
        else:
            roll = r.randint(1, 20)
            success = roll >= dc or roll == 20

        new_powers: List[str] = []
        if success:
            self.current_ideal = ideal_number
            self.ideal_progress[ideal_number] = 1.0
            # Gather newly unlocked powers
            try:
                from codex.forge.reference_data.stc_orders import ORDERS
                order_data = ORDERS.get(self.order, {})
                per_level = order_data.get("per_ideal_powers", {})
                for power in per_level.get(ideal_number, []):
                    new_powers.append(power["name"])
                    self.unlocked_abilities.append(power["name"])
            except ImportError:
                pass

            context_str = f' "{context}"' if context else ""
            msg = (
                f'{self.character_name} swears the {_ordinal(ideal_number)} Ideal'
                f"{context_str}: "
                f'"{oath_text}" '
                f"(Roll: {roll} vs DC {dc}). "
                + (f"Powers unlocked: {', '.join(new_powers)}." if new_powers else "")
            )
        else:
            msg = (
                f"{self.character_name} attempts to swear Ideal {ideal_number} "
                f"but falters. (Roll: {roll} vs DC {dc}). The words won't come."
            )

        return {
            "success": success,
            "ideal_sworn": ideal_number if success else None,
            "roll": roll,
            "dc": dc,
            "oath_text": oath_text,
            "message": msg,
            "new_powers": new_powers,
        }

    def unlock_ability(self, ability_name: str) -> dict:
        """
        Directly grant access to a named ability (used by the engine on ideal swearing).

        Args:
            ability_name: Name of the ability to unlock.

        Returns:
            Dict with keys: unlocked (bool), ability_name (str), message (str).
        """
        if ability_name in self.unlocked_abilities:
            return {
                "unlocked": False,
                "ability_name": ability_name,
                "message": f"{ability_name} is already unlocked.",
            }
        self.unlocked_abilities.append(ability_name)
        return {
            "unlocked": True,
            "ability_name": ability_name,
            "message": f"{self.character_name} unlocked: {ability_name}.",
        }

    def get_available_ideals(self) -> List[dict]:
        """
        Return information about all five ideals and their status.

        Returns:
            List of dicts with keys: ideal_number, text, sworn, progress,
            dc, ready_to_attempt.
        """
        result: List[dict] = []
        for i in range(1, 6):
            sworn = i <= self.current_ideal
            progress = self.ideal_progress.get(i, 0.0)
            dc = IDEAL_DC.get(i, 10)
            is_next = i == self.current_ideal + 1
            ready = is_next and progress >= IDEAL_PROGRESS_THRESHOLD
            result.append({
                "ideal_number": i,
                "text": self.get_oath_text(i),
                "sworn": sworn,
                "progress": progress,
                "dc": dc,
                "ready_to_attempt": ready,
            })
        return result

    def to_dict(self) -> dict:
        """Serialise to a plain dict for save/load."""
        return {
            "character_name": self.character_name,
            "order": self.order,
            "current_ideal": self.current_ideal,
            "ideal_progress": {str(k): v for k, v in self.ideal_progress.items()},
            "unlocked_abilities": list(self.unlocked_abilities),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IdealProgression":
        """Deserialise from a saved dict."""
        ip = cls(
            character_name=data["character_name"],
            order=data.get("order", ""),
            current_ideal=data.get("current_ideal", 1),
        )
        raw_progress = data.get("ideal_progress", {})
        ip.ideal_progress = {int(k): float(v) for k, v in raw_progress.items()}
        # Ensure all 5 levels exist
        for i in range(1, 6):
            if i not in ip.ideal_progress:
                ip.ideal_progress[i] = 1.0 if i <= ip.current_ideal else 0.0
        ip.unlocked_abilities = list(data.get("unlocked_abilities", []))
        return ip


# =========================================================================
# HELPERS
# =========================================================================

def _ordinal(n: int) -> str:
    """Return ordinal string for 1-5."""
    return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}.get(n, f"{n}th")


__all__ = ["IdealProgression", "IDEAL_DC", "IDEAL_PROGRESS_THRESHOLD"]

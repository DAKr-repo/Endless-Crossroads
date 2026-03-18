"""
PbtA Engine — Powered by the Apocalypse resolution system.
===========================================================

Provides the shared mechanical core for all PbtA-family games:
  - PbtAResult dataclass (2d6 + stat outcome)
  - PbtAActionRoll class with roll_move()

Outcome thresholds (standard PbtA):
  - 1+1 (snake eyes): critical_miss
  - 6+6 (boxcars): critical_hit
  - <= 6: miss  (GM makes a hard move)
  - 7-9: weak_hit (success with complication)
  - 10+: strong_hit (full success)

Each sub-system (Apocalypse World, Dungeon World, Monster of the Week)
extends these primitives with its own move list and playbook abilities.
"""

import random
from dataclasses import dataclass
from typing import List, Optional


# =========================================================================
# RESULT DATACLASS
# =========================================================================

@dataclass
class PbtAResult:
    """Outcome of a Powered by the Apocalypse 2d6+stat roll.

    Attributes:
        total: Sum of both dice plus stat_bonus.
        dice: The two individual d6 values rolled.
        stat_bonus: The stat modifier added to the roll.
        outcome: One of 'miss', 'weak_hit', 'strong_hit',
                 'critical_miss', or 'critical_hit'.
    """
    total: int
    dice: List[int]
    stat_bonus: int
    outcome: str


# =========================================================================
# ACTION ROLL
# =========================================================================

class PbtAActionRoll:
    """Powered by the Apocalypse resolution: 2d6 + stat.

    Outcomes:
        - Both dice show 1 (1+1)  : critical_miss (GM's hard move, aggravated)
        - Both dice show 6 (6+6)  : critical_hit  (full success + bonus)
        - Total <= 6              : miss           (GM makes a hard move)
        - Total 7-9               : weak_hit       (success with cost)
        - Total 10+               : strong_hit     (full success)

    The critical_miss/critical_hit checks take precedence over the
    numeric threshold checks so snake eyes always reads as critical_miss
    even though 1+1+stat could technically land in weak_hit range.

    Usage::

        roller = PbtAActionRoll()
        result = roller.roll_move(stat_bonus=2)
        print(result.outcome, result.total)
    """

    def roll_move(
        self,
        stat_bonus: int = 0,
        rng: Optional[random.Random] = None,
    ) -> PbtAResult:
        """Execute a standard PbtA move roll (2d6 + stat).

        Args:
            stat_bonus: The acting stat's modifier (typically -2 to +3).
            rng: Optional seeded Random instance for deterministic tests.
                 If None, uses the module-level random functions.

        Returns:
            PbtAResult with total, dice list, stat_bonus, and outcome.
        """
        r = rng or random
        d1 = r.randint(1, 6)
        d2 = r.randint(1, 6)
        total = d1 + d2 + stat_bonus

        # Special cases take precedence over numeric thresholds
        if d1 == 1 and d2 == 1:
            outcome = "critical_miss"
        elif d1 == 6 and d2 == 6:
            outcome = "critical_hit"
        elif total <= 6:
            outcome = "miss"
        elif total <= 9:
            outcome = "weak_hit"
        else:
            outcome = "strong_hit"

        return PbtAResult(
            total=total,
            dice=[d1, d2],
            stat_bonus=stat_bonus,
            outcome=outcome,
        )

    def format_result(self, result: PbtAResult) -> str:
        """Format a PbtAResult into a human-readable string.

        Args:
            result: A PbtAResult from roll_move().

        Returns:
            Multi-line string describing the roll and outcome.
        """
        dice_str = ", ".join(str(d) for d in result.dice)
        outcome_label = result.outcome.replace("_", " ").upper()
        bonus_str = f"+{result.stat_bonus}" if result.stat_bonus >= 0 else str(result.stat_bonus)
        return (
            f"Dice: [{dice_str}] {bonus_str} -> {result.total} | {outcome_label}"
        )

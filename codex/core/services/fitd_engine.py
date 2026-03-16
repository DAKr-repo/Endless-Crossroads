"""
FITD Engine — Universal Forged in the Dark resolution system.
===============================================================

Provides the shared mechanical core for all FITD-family games:
  - Position / Effect enums
  - d6-pool action rolls (FITDActionRoll / FITDResult)
  - StressClock with configurable trauma tables (AMD-02)
  - FactionClock (4/6/8 segment progress clocks)
  - LegionState (Band of Blades military resources, AMD-02)

Each sub-system (BitD, S&V, BoB, CBR+PNK) extends these primitives
with its own action list, playbook abilities, and consequence tables.

Design note: Burnwillow's DoomClock is NOT stress (it's a dungeon
timer).  Crown & Crew uses Sway (not FITD stress).  This module is
entirely new code with no existing overlap.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# =========================================================================
# POSITION / EFFECT
# =========================================================================

class Position(Enum):
    """The GM-set danger level of an action."""
    CONTROLLED = "controlled"
    RISKY = "risky"
    DESPERATE = "desperate"


class Effect(Enum):
    """The expected impact magnitude of an action."""
    ZERO = "zero"
    LIMITED = "limited"
    STANDARD = "standard"
    GREAT = "great"
    EXTREME = "extreme"


# =========================================================================
# ACTION ROLL
# =========================================================================

@dataclass
class FITDResult:
    """Outcome of a Forged in the Dark d6-pool roll."""
    outcome: str              # "failure", "mixed", "success", "critical"
    highest: int
    all_dice: list[int]
    position: Position
    effect: Effect
    consequences: list[str] = field(default_factory=list)


@dataclass
class FITDActionRoll:
    """Shared d6-pool resolution for all FITD systems.

    Roll *dice_count* d6s.  Highest die determines outcome:
      - 1-3: failure
      - 4-5: mixed success
      - 6:   full success
      - Two or more 6s: critical
    If dice_count is 0, roll 2d6 and take the *lowest* (disadvantage).
    """
    dice_count: int
    position: Position = Position.RISKY
    effect: Effect = Effect.STANDARD

    def roll(self, rng: Optional[random.Random] = None) -> FITDResult:
        """Execute the roll and return a :class:`FITDResult`."""
        _rng = rng or random.Random()

        if self.dice_count <= 0:
            # Zero-dice roll: roll 2d6 take lowest
            dice = sorted([_rng.randint(1, 6) for _ in range(2)])
            highest = dice[0]
        else:
            dice = [_rng.randint(1, 6) for _ in range(self.dice_count)]
            highest = max(dice)

        sixes = dice.count(6)

        if sixes >= 2:
            outcome = "critical"
        elif highest == 6:
            outcome = "success"
        elif highest >= 4:
            outcome = "mixed"
        else:
            outcome = "failure"

        return FITDResult(
            outcome=outcome,
            highest=highest,
            all_dice=dice,
            position=self.position,
            effect=self.effect,
        )


# =========================================================================
# STRESS / TRAUMA
# =========================================================================

FITD_DEFAULT_TRAUMAS: list[str] = [
    "Cold", "Haunted", "Obsessed", "Reckless",
    "Soft", "Unstable", "Vicious", "Paranoid",
]

BOB_TRAUMAS: list[str] = [
    "Shell-Shocked", "Bloodthirsty", "Deserter", "Hollow",
    "Scarred", "Feral", "Broken",
]


@dataclass
class StressClock:
    """Universal Stress / Trauma tracker for FITD games.

    AMD-02: ``trauma_table`` is configurable per-system (BoB uses grittier
    traumas than generic FITD).
    """
    current_stress: int = 0
    max_stress: int = 9
    traumas: list[str] = field(default_factory=list)
    max_traumas: int = 4
    trauma_table: list[str] = field(default_factory=lambda: list(FITD_DEFAULT_TRAUMAS))

    def push(self, amount: int = 1, rng: Optional[random.Random] = None) -> dict:
        """Add stress.  Returns dict with new state and whether trauma triggered."""
        _rng = rng or random.Random()
        self.current_stress += amount
        trauma_triggered = False
        broken = False

        if self.current_stress > self.max_stress:
            # Trauma!
            self.current_stress = 0
            if self.trauma_table:
                available = [t for t in self.trauma_table if t not in self.traumas]
                if available:
                    new_trauma = _rng.choice(available)
                    self.traumas.append(new_trauma)
                    trauma_triggered = True

            if len(self.traumas) >= self.max_traumas:
                broken = True

        return {
            "new_stress": self.current_stress,
            "trauma_triggered": trauma_triggered,
            "new_trauma": self.traumas[-1] if trauma_triggered else None,
            "broken": broken,
            "total_traumas": len(self.traumas),
        }

    def resist(self, stress_cost: int = 0) -> dict:
        """Spend stress to resist a consequence.

        The caller (game engine) determines the cost via a resistance roll.
        """
        actual_cost = min(stress_cost, self.max_stress)
        result = self.push(actual_cost)
        result["action"] = "resist"
        return result

    def recover(self, amount: int = 0) -> dict:
        """Vice scene stress recovery."""
        old = self.current_stress
        self.current_stress = max(0, self.current_stress - amount)
        return {
            "recovered": old - self.current_stress,
            "new_stress": self.current_stress,
            "overindulged": amount > old,
        }

    def to_dict(self) -> dict:
        return {
            "current_stress": self.current_stress,
            "max_stress": self.max_stress,
            "traumas": self.traumas,
            "max_traumas": self.max_traumas,
            "trauma_table": self.trauma_table,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StressClock":
        return cls(
            current_stress=data.get("current_stress", 0),
            max_stress=data.get("max_stress", 9),
            traumas=data.get("traumas", []),
            max_traumas=data.get("max_traumas", 4),
            trauma_table=data.get("trauma_table", list(FITD_DEFAULT_TRAUMAS)),
        )


# =========================================================================
# FACTION / PROGRESS CLOCKS (re-exported from codex.core.mechanics.clock)
# =========================================================================

from codex.core.mechanics.clock import UniversalClock, FactionClock  # noqa: F401


# =========================================================================
# LEGION STATE (Band of Blades — AMD-02)
# =========================================================================

@dataclass
class LegionState:
    """Band of Blades military resources (extends base FITD)."""
    supply: int = 5       # 0-10, logistics resource
    intel: int = 3        # 0-10, reconnaissance resource
    morale: int = 5       # 0-10, troop spirit
    pressure: int = 0     # Undead army advance (0-6 clock)

    def adjust(self, resource: str, amount: int) -> dict:
        """Adjust a named resource, clamping to valid range."""
        if resource == "pressure":
            lo, hi = 0, 6
        else:
            lo, hi = 0, 10

        old = getattr(self, resource, None)
        if old is None:
            return {"error": f"Unknown resource: {resource}"}

        new = max(lo, min(hi, old + amount))
        setattr(self, resource, new)
        return {"resource": resource, "old": old, "new": new, "delta": new - old}

    def to_dict(self) -> dict:
        return {
            "supply": self.supply,
            "intel": self.intel,
            "morale": self.morale,
            "pressure": self.pressure,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LegionState":
        return cls(
            supply=data.get("supply", 5),
            intel=data.get("intel", 3),
            morale=data.get("morale", 5),
            pressure=data.get("pressure", 0),
        )


# =========================================================================
# SHARED ROLL FORMATTER (WO-V10.0)
# =========================================================================

def format_roll_result(result: FITDResult) -> str:
    """Format an FITDResult into a human-readable string.

    All 5 FITD engines reuse this for consistent output.
    """
    dice_str = ", ".join(str(d) for d in result.all_dice)
    outcome_label = result.outcome.upper()
    return (
        f"Dice: [{dice_str}] -> {outcome_label}\n"
        f"Position: {result.position.value} | Effect: {result.effect.value}"
    )


# Engine registration
try:
    from codex.core.engine_protocol import register_engine
    register_engine("fitd", FITDActionRoll)
except ImportError:
    pass

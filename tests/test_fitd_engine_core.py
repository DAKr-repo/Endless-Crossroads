"""
Tests for codex/core/services/fitd_engine.py

Coverage targets:
  - FITDActionRoll: zero-dice, 1/2/4 dice, critical, mixed, success, failure,
    position/effect pass-through
  - StressClock: push, recover, trauma trigger, broken state, serialization
  - LegionState: adjust (clamp), unknown resource, serialization round-trip
  - format_roll_result: string shape

All tests are fully self-contained.  No external services, no I/O.
A seeded random.Random is used wherever dice matter to make outcomes
deterministic without patching the module.
"""

import random

import pytest

from codex.core.services.fitd_engine import (
    Effect,
    FITDActionRoll,
    FITDResult,
    LegionState,
    Position,
    StressClock,
    format_roll_result,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rng(*seq: int) -> random.Random:
    """Return a Random whose randint() calls return *seq* in order.

    This avoids patching the module: FITDActionRoll.roll() accepts an
    optional *rng* kwarg, so we can inject a seeded instance.
    The standard library Random is good enough — we seed it to a value
    whose first N d6 rolls match what we need, or we use a fake subclass.
    """
    return random.Random()  # unused overrides below use subclass approach


class _FakeRNG(random.Random):
    """Fake RNG that returns values from a fixed queue.

    Usage::

        rng = _FakeRNG(3, 5, 6, 6)
        # first randint() call → 3, second → 5, …
    """

    def __init__(self, *values: int) -> None:
        super().__init__()
        self._queue = list(values)

    def randint(self, a: int, b: int) -> int:  # type: ignore[override]
        if not self._queue:
            raise RuntimeError("_FakeRNG ran out of values")
        return self._queue.pop(0)

    def choice(self, seq):  # type: ignore[override]
        return seq[0]  # deterministic: always pick first available item


# ---------------------------------------------------------------------------
# FITDActionRoll — zero-dice (disadvantage) mechanics
# ---------------------------------------------------------------------------

class TestFITDActionRollZeroDice:

    def test_zero_dice_takes_lowest_of_two(self):
        """Roll two dice and take the lowest when dice_count=0."""
        rng = _FakeRNG(5, 2)          # sorted → [2, 5] → highest = dice[0] = 2
        roll = FITDActionRoll(dice_count=0)
        result = roll.roll(rng=rng)
        assert result.highest == 2
        assert result.outcome == "failure"

    def test_zero_dice_all_dice_contains_two_values(self):
        rng = _FakeRNG(4, 3)          # sorted → [3, 4] → highest = 3 (mixed)
        result = FITDActionRoll(dice_count=0).roll(rng=rng)
        assert len(result.all_dice) == 2

    def test_negative_dice_treated_as_zero(self):
        """Negative dice_count should also use the zero-dice path."""
        rng = _FakeRNG(6, 1)          # sorted → [1, 6] → highest = 1 (failure)
        result = FITDActionRoll(dice_count=-3).roll(rng=rng)
        assert result.highest == 1
        assert result.outcome == "failure"


# ---------------------------------------------------------------------------
# FITDActionRoll — standard pool sizes
# ---------------------------------------------------------------------------

class TestFITDActionRollPoolSizes:

    def test_one_die_success(self):
        rng = _FakeRNG(6)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        assert result.outcome == "success"
        assert result.highest == 6
        assert len(result.all_dice) == 1

    def test_two_dice_mixed(self):
        rng = _FakeRNG(4, 3)
        result = FITDActionRoll(dice_count=2).roll(rng=rng)
        assert result.outcome == "mixed"
        assert result.highest == 4

    def test_four_dice_failure(self):
        rng = _FakeRNG(1, 2, 3, 1)
        result = FITDActionRoll(dice_count=4).roll(rng=rng)
        assert result.outcome == "failure"
        assert result.highest == 3
        assert len(result.all_dice) == 4


# ---------------------------------------------------------------------------
# FITDActionRoll — outcome boundary detection
# ---------------------------------------------------------------------------

class TestFITDActionRollOutcomes:

    def test_critical_two_sixes(self):
        """Two sixes in any pool size → critical."""
        rng = _FakeRNG(6, 6)
        result = FITDActionRoll(dice_count=2).roll(rng=rng)
        assert result.outcome == "critical"

    def test_critical_three_sixes(self):
        """Three sixes also → critical (>=2 sixes)."""
        rng = _FakeRNG(6, 6, 6)
        result = FITDActionRoll(dice_count=3).roll(rng=rng)
        assert result.outcome == "critical"

    def test_success_single_six(self):
        """Exactly one six among multiple dice → success (not critical)."""
        rng = _FakeRNG(6, 3, 2)
        result = FITDActionRoll(dice_count=3).roll(rng=rng)
        assert result.outcome == "success"

    def test_mixed_boundary_low(self):
        """Highest die = 4 → mixed."""
        rng = _FakeRNG(4)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        assert result.outcome == "mixed"

    def test_mixed_boundary_high(self):
        """Highest die = 5 → mixed."""
        rng = _FakeRNG(5)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        assert result.outcome == "mixed"

    def test_failure_boundary(self):
        """Highest die = 3 → failure."""
        rng = _FakeRNG(3)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        assert result.outcome == "failure"

    def test_failure_all_ones(self):
        rng = _FakeRNG(1, 1, 1, 1)
        result = FITDActionRoll(dice_count=4).roll(rng=rng)
        assert result.outcome == "failure"
        assert result.highest == 1


# ---------------------------------------------------------------------------
# FITDActionRoll — position and effect pass-through
# ---------------------------------------------------------------------------

class TestFITDActionRollPositionEffect:

    def test_position_and_effect_on_result(self):
        rng = _FakeRNG(3)
        result = FITDActionRoll(
            dice_count=1,
            position=Position.DESPERATE,
            effect=Effect.GREAT,
        ).roll(rng=rng)
        assert result.position == Position.DESPERATE
        assert result.effect == Effect.GREAT

    def test_default_position_risky_effect_standard(self):
        rng = _FakeRNG(2)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        assert result.position == Position.RISKY
        assert result.effect == Effect.STANDARD

    def test_consequences_empty_by_default(self):
        rng = _FakeRNG(1)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        assert result.consequences == []


# ---------------------------------------------------------------------------
# StressClock
# ---------------------------------------------------------------------------

class TestStressClockPushRecover:

    def test_push_adds_stress(self):
        sc = StressClock()
        sc.push(3)
        assert sc.current_stress == 3

    def test_recover_removes_stress(self):
        sc = StressClock(current_stress=5)
        result = sc.recover(2)
        assert sc.current_stress == 3
        assert result["recovered"] == 2
        assert result["new_stress"] == 3

    def test_recover_clamps_at_zero(self):
        sc = StressClock(current_stress=2)
        result = sc.recover(10)
        assert sc.current_stress == 0
        assert result["overindulged"] is True

    def test_push_no_trauma_below_max(self):
        sc = StressClock()           # max_stress=9
        result = sc.push(9)          # exactly at max, not *over*
        assert result["trauma_triggered"] is False
        assert sc.current_stress == 9

    def test_push_trauma_triggers_over_max(self):
        sc = StressClock()
        rng = _FakeRNG()             # choice() returns seq[0]
        result = sc.push(10, rng=rng)   # 10 > 9 → trauma
        assert result["trauma_triggered"] is True
        assert sc.current_stress == 0   # resets after trauma
        assert len(sc.traumas) == 1

    def test_trauma_name_from_table(self):
        sc = StressClock()
        rng = _FakeRNG()
        sc.push(10, rng=rng)
        # _FakeRNG.choice picks seq[0] = first available trauma
        assert sc.traumas[0] == "Cold"

    def test_broken_at_four_traumas(self):
        """Reaching max_traumas (4) sets broken=True in the return dict."""
        sc = StressClock(traumas=["Cold", "Haunted", "Obsessed"])
        rng = _FakeRNG()
        result = sc.push(10, rng=rng)   # adds 4th trauma
        assert result["broken"] is True

    def test_not_broken_before_four_traumas(self):
        sc = StressClock(traumas=["Cold"])
        rng = _FakeRNG()
        result = sc.push(10, rng=rng)
        assert result["broken"] is False


# ---------------------------------------------------------------------------
# StressClock — serialization
# ---------------------------------------------------------------------------

class TestStressClockSerialization:

    def test_round_trip_empty(self):
        sc = StressClock()
        restored = StressClock.from_dict(sc.to_dict())
        assert restored.current_stress == sc.current_stress
        assert restored.max_stress == sc.max_stress
        assert restored.traumas == sc.traumas
        assert restored.trauma_table == sc.trauma_table

    def test_round_trip_with_state(self):
        sc = StressClock(current_stress=7, traumas=["Reckless", "Soft"])
        restored = StressClock.from_dict(sc.to_dict())
        assert restored.current_stress == 7
        assert restored.traumas == ["Reckless", "Soft"]

    def test_from_dict_missing_keys_uses_defaults(self):
        sc = StressClock.from_dict({})
        assert sc.current_stress == 0
        assert sc.max_stress == 9
        assert sc.traumas == []


# ---------------------------------------------------------------------------
# LegionState
# ---------------------------------------------------------------------------

class TestLegionState:

    def test_adjust_supply(self):
        ls = LegionState()
        result = ls.adjust("supply", -3)
        assert ls.supply == 2
        assert result["new"] == 2
        assert result["old"] == 5

    def test_adjust_clamps_at_zero(self):
        ls = LegionState(supply=2)
        ls.adjust("supply", -10)
        assert ls.supply == 0

    def test_adjust_clamps_at_ten(self):
        ls = LegionState(morale=8)
        ls.adjust("morale", 5)
        assert ls.morale == 10

    def test_adjust_pressure_clamps_at_six(self):
        ls = LegionState(pressure=5)
        ls.adjust("pressure", 4)
        assert ls.pressure == 6

    def test_adjust_unknown_resource_returns_error(self):
        ls = LegionState()
        result = ls.adjust("gold", 3)
        assert "error" in result

    def test_round_trip(self):
        ls = LegionState(supply=1, intel=9, morale=3, pressure=6)
        restored = LegionState.from_dict(ls.to_dict())
        assert restored.supply == 1
        assert restored.intel == 9
        assert restored.morale == 3
        assert restored.pressure == 6

    def test_from_dict_defaults(self):
        ls = LegionState.from_dict({})
        assert ls.supply == 5
        assert ls.intel == 3
        assert ls.morale == 5
        assert ls.pressure == 0


# ---------------------------------------------------------------------------
# format_roll_result
# ---------------------------------------------------------------------------

class TestFormatRollResult:

    def test_contains_dice_values(self):
        rng = _FakeRNG(4, 5)
        result = FITDActionRoll(dice_count=2).roll(rng=rng)
        formatted = format_roll_result(result)
        assert "4" in formatted
        assert "5" in formatted

    def test_contains_outcome_label(self):
        rng = _FakeRNG(6)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        formatted = format_roll_result(result)
        assert "SUCCESS" in formatted

    def test_contains_position_and_effect(self):
        rng = _FakeRNG(3)
        result = FITDActionRoll(
            dice_count=1,
            position=Position.CONTROLLED,
            effect=Effect.LIMITED,
        ).roll(rng=rng)
        formatted = format_roll_result(result)
        assert "controlled" in formatted
        assert "limited" in formatted

    def test_returns_string(self):
        rng = _FakeRNG(2)
        result = FITDActionRoll(dice_count=1).roll(rng=rng)
        assert isinstance(format_roll_result(result), str)

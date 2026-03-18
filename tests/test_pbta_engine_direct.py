"""
Direct unit tests for codex/core/services/pbta_engine.py.

Tests are fully self-contained: no external services, no LLM calls,
no filesystem I/O.  Determinism is achieved with seeded random.Random
instances so every outcome is predictable.
"""

import random
import pytest

from codex.core.services.pbta_engine import PbtAActionRoll, PbtAResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rng_constant(d1: int, d2: int) -> random.Random:
    """Return a seeded RNG whose first two randint(1,6) calls return d1, d2."""
    # Brute-force seed search: deterministic given small search space.
    for seed in range(10_000):
        r = random.Random(seed)
        a = r.randint(1, 6)
        b = r.randint(1, 6)
        if a == d1 and b == d2:
            return random.Random(seed)  # fresh instance at the same seed
    raise RuntimeError(f"Could not find a seed that produces ({d1}, {d2})")


# ---------------------------------------------------------------------------
# Test 1: strong hit — dice total 10+
# ---------------------------------------------------------------------------

class TestStrongHit:
    def test_outcome_is_strong_hit(self):
        # 5+5=10 with stat_bonus=0 -> strong_hit
        roller = PbtAActionRoll()
        rng = _rng_constant(5, 5)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "strong_hit"

    def test_total_matches_dice_plus_bonus(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(5, 5)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.total == sum(result.dice) + result.stat_bonus

    def test_stat_bonus_pushes_into_strong_hit(self):
        # 4+4=8, +2 stat -> 10, still strong_hit
        roller = PbtAActionRoll()
        rng = _rng_constant(4, 4)
        result = roller.roll_move(stat_bonus=2, rng=rng)
        assert result.outcome == "strong_hit"
        assert result.total == 10


# ---------------------------------------------------------------------------
# Test 2: weak hit — dice total 7-9
# ---------------------------------------------------------------------------

class TestWeakHit:
    def test_outcome_is_weak_hit_on_8(self):
        # 4+4=8 with stat_bonus=0 -> weak_hit
        roller = PbtAActionRoll()
        rng = _rng_constant(4, 4)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "weak_hit"

    def test_total_is_8(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(4, 4)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.total == 8

    def test_boundary_7_is_weak_hit(self):
        # 3+4=7, stat 0 -> weak_hit (lower boundary)
        roller = PbtAActionRoll()
        rng = _rng_constant(3, 4)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "weak_hit"
        assert result.total == 7

    def test_boundary_9_is_weak_hit(self):
        # 5+4=9, stat 0 -> weak_hit (upper boundary)
        roller = PbtAActionRoll()
        rng = _rng_constant(5, 4)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "weak_hit"
        assert result.total == 9


# ---------------------------------------------------------------------------
# Test 3: miss — dice total <= 6 (not 1+1)
# ---------------------------------------------------------------------------

class TestMiss:
    def test_outcome_is_miss_on_6(self):
        # 2+4=6, stat 0 -> miss (upper miss boundary)
        roller = PbtAActionRoll()
        rng = _rng_constant(2, 4)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "miss"

    def test_total_is_6(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(2, 4)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.total == 6

    def test_negative_bonus_pushes_into_miss(self):
        # 4+4=8, -3 stat -> 5 -> miss
        roller = PbtAActionRoll()
        rng = _rng_constant(4, 4)
        result = roller.roll_move(stat_bonus=-3, rng=rng)
        assert result.outcome == "miss"
        assert result.total == 5


# ---------------------------------------------------------------------------
# Test 4: snake eyes (1+1) => critical_miss overrides numeric threshold
# ---------------------------------------------------------------------------

class TestSnakeEyes:
    def test_critical_miss_outcome(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(1, 1)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "critical_miss"

    def test_dice_are_both_ones(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(1, 1)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.dice == [1, 1]

    def test_high_stat_does_not_save_snake_eyes(self):
        # 1+1+3=5 would be a miss numerically, but critical_miss takes precedence.
        roller = PbtAActionRoll()
        rng = _rng_constant(1, 1)
        result = roller.roll_move(stat_bonus=3, rng=rng)
        assert result.outcome == "critical_miss"


# ---------------------------------------------------------------------------
# Test 5: boxcars (6+6) => critical_hit overrides numeric threshold
# ---------------------------------------------------------------------------

class TestBoxcars:
    def test_critical_hit_outcome(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(6, 6)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "critical_hit"

    def test_dice_are_both_sixes(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(6, 6)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.dice == [6, 6]

    def test_negative_stat_does_not_override_boxcars(self):
        # 6+6-5=7 would be weak_hit numerically, but critical_hit takes precedence.
        roller = PbtAActionRoll()
        rng = _rng_constant(6, 6)
        result = roller.roll_move(stat_bonus=-5, rng=rng)
        assert result.outcome == "critical_hit"


# ---------------------------------------------------------------------------
# Test 6: stat bonus is stored on the result
# ---------------------------------------------------------------------------

class TestStatBonus:
    def test_bonus_stored_positive(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(3, 3)
        result = roller.roll_move(stat_bonus=2, rng=rng)
        assert result.stat_bonus == 2

    def test_bonus_stored_negative(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(5, 5)
        result = roller.roll_move(stat_bonus=-1, rng=rng)
        assert result.stat_bonus == -1

    def test_zero_bonus_stored(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(4, 3)
        result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.stat_bonus == 0

    def test_total_accounts_for_bonus(self):
        roller = PbtAActionRoll()
        rng = _rng_constant(3, 3)
        result = roller.roll_move(stat_bonus=2, rng=rng)
        assert result.total == 3 + 3 + 2


# ---------------------------------------------------------------------------
# Test 7: format_result returns a human-readable string
# ---------------------------------------------------------------------------

class TestFormatResult:
    def _make_result(self, d1, d2, bonus, outcome):
        return PbtAResult(
            total=d1 + d2 + bonus,
            dice=[d1, d2],
            stat_bonus=bonus,
            outcome=outcome,
        )

    def test_contains_dice_values(self):
        roller = PbtAActionRoll()
        result = self._make_result(4, 4, 0, "weak_hit")
        text = roller.format_result(result)
        assert "4" in text

    def test_contains_total(self):
        roller = PbtAActionRoll()
        result = self._make_result(5, 5, 0, "strong_hit")
        text = roller.format_result(result)
        assert "10" in text

    def test_outcome_uppercased_in_output(self):
        roller = PbtAActionRoll()
        result = self._make_result(1, 1, 0, "critical_miss")
        text = roller.format_result(result)
        assert "CRITICAL MISS" in text

    def test_positive_bonus_shows_plus_sign(self):
        roller = PbtAActionRoll()
        result = self._make_result(3, 3, 2, "strong_hit")
        text = roller.format_result(result)
        assert "+2" in text

    def test_negative_bonus_shows_minus_sign(self):
        roller = PbtAActionRoll()
        result = self._make_result(5, 5, -1, "strong_hit")
        text = roller.format_result(result)
        assert "-1" in text

    def test_returns_string(self):
        roller = PbtAActionRoll()
        result = self._make_result(4, 4, 1, "weak_hit")
        assert isinstance(roller.format_result(result), str)

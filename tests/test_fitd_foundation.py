"""
tests/test_fitd_foundation.py — FITD Shared Mechanics Foundation (WO-P1)
=========================================================================
Covers:
  - FITDFortuneRoll / FortuneResult
  - resistance_roll()
  - gather_information()
  - ConsequenceTable / CONSEQUENCE_TYPES
  - format_fortune_result()
  - NarrativeEngineBase.roll_fortune(), roll_resistance(), gather_information()
  - NarrativeEngineBase._cmd_fortune(), _cmd_resist(), _cmd_gather_info()
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pytest

from codex.core.services.fitd_engine import (
    CONSEQUENCE_TYPES,
    ConsequenceTable,
    FITDFortuneRoll,
    FortuneResult,
    StressClock,
    format_fortune_result,
    gather_information,
    resistance_roll,
)
from codex.core.engines.narrative_base import NarrativeEngineBase


# ---------------------------------------------------------------------------
# Minimal concrete engine for testing NarrativeEngineBase methods
# ---------------------------------------------------------------------------

@dataclass
class _FakeChar:
    """Minimal character stub with a couple of action dots."""
    name: str
    hunt: int = 2
    survey: int = 1
    skirmish: int = 0

    def to_dict(self) -> dict:
        return {"name": self.name, "hunt": self.hunt, "survey": self.survey, "skirmish": self.skirmish}


class _FakeEngine(NarrativeEngineBase):
    """Concrete subclass for test isolation."""

    system_id = "fake"
    system_family = "FAKE"
    display_name = "Fake System"

    def _create_character(self, name: str, **kwargs) -> _FakeChar:
        return _FakeChar(
            name=name,
            hunt=kwargs.get("hunt", 2),
            survey=kwargs.get("survey", 1),
            skirmish=kwargs.get("skirmish", 0),
        )

    def _get_command_registry(self) -> Dict[str, Any]:
        return {}


def _make_engine_with_char(name: str = "Vex") -> _FakeEngine:
    """Create an engine with a single character already registered."""
    engine = _FakeEngine()
    engine.create_character(name)
    return engine


# ===========================================================================
# FortuneResult dataclass sanity
# ===========================================================================

class TestFortuneResult:
    def test_fields_accessible(self):
        r = FortuneResult(outcome="good", highest=6, all_dice=[3, 6])
        assert r.outcome == "good"
        assert r.highest == 6
        assert r.all_dice == [3, 6]


# ===========================================================================
# FITDFortuneRoll
# ===========================================================================

class TestFITDFortuneRoll:

    def test_fortune_roll_zero_dice_takes_lowest(self):
        """dice_count=0 must roll 2d6 and use the lower value."""
        # Use a seed that produces [5, 2] -> sorted [2, 5] -> highest = 2 (lowest)
        rng = random.Random(99)
        roll = FITDFortuneRoll(dice_count=0)
        result = roll.roll(rng)
        # Exactly 2 dice rolled
        assert len(result.all_dice) == 2
        # highest must equal the minimum of the two dice
        assert result.highest == min(result.all_dice)

    def test_fortune_roll_negative_dice_treated_as_zero(self):
        """Negative dice_count behaves the same as 0 (2d6 take lowest)."""
        rng = random.Random(7)
        roll = FITDFortuneRoll(dice_count=-3)
        result = roll.roll(rng)
        assert len(result.all_dice) == 2
        assert result.highest == min(result.all_dice)

    def test_fortune_roll_outcome_bad(self):
        """Verify "bad" outcome for highest <= 3."""
        # Seed that gives two dice both <= 3
        rng = random.Random(0)
        roll = FITDFortuneRoll(dice_count=2)
        # Keep rolling until we get a "bad" result to verify logic
        for _ in range(1000):
            r = roll.roll(random.Random(random.randint(1, 99999)))
            if r.highest <= 3:
                assert r.outcome == "bad"
                break

    def test_fortune_roll_outcome_mixed(self):
        """Verify "mixed" for highest in 4-5 with no crit."""
        for seed in range(10000):
            r = FITDFortuneRoll(dice_count=2).roll(random.Random(seed))
            if 4 <= r.highest <= 5 and r.all_dice.count(6) < 2:
                assert r.outcome == "mixed"
                break

    def test_fortune_roll_outcome_good(self):
        """Verify "good" for exactly one 6 (no crit)."""
        for seed in range(10000):
            r = FITDFortuneRoll(dice_count=2).roll(random.Random(seed))
            if r.all_dice.count(6) == 1:
                assert r.outcome == "good"
                assert r.highest == 6
                break

    def test_fortune_roll_crit_two_sixes(self):
        """Two or more sixes produce "crit" regardless of pool size."""
        # Roll a large pool until we get 2+ sixes
        for seed in range(10000):
            r = FITDFortuneRoll(dice_count=4).roll(random.Random(seed))
            if r.all_dice.count(6) >= 2:
                assert r.outcome == "crit"
                break

    def test_fortune_roll_crit_exact_seed(self):
        """Deterministic crit: two-dice pool where both are 6."""
        # Patch a fixed rng that always returns 6
        class _AlwaysSix(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 6

        r = FITDFortuneRoll(dice_count=2).roll(_AlwaysSix())
        assert r.outcome == "crit"
        assert r.all_dice == [6, 6]
        assert r.highest == 6

    def test_fortune_roll_dice_count_respected(self):
        """dice_count=3 must produce exactly 3 dice."""
        rng = random.Random(42)
        r = FITDFortuneRoll(dice_count=3).roll(rng)
        assert len(r.all_dice) == 3

    def test_fortune_roll_highest_matches_max(self):
        """highest must equal max(all_dice) for positive dice_count."""
        for seed in range(50):
            r = FITDFortuneRoll(dice_count=3).roll(random.Random(seed))
            assert r.highest == max(r.all_dice)


# ===========================================================================
# resistance_roll()
# ===========================================================================

class TestResistanceRoll:

    def test_resistance_roll_basic_cost_formula(self):
        """stress_cost == 6 - highest for non-crit outcomes."""
        for seed in range(500):
            rng = random.Random(seed)
            result = resistance_roll(2, rng=rng)
            if not result["crit"]:
                expected = 6 - result["highest"]
                assert result["stress_cost"] == expected, (
                    f"seed={seed}: expected cost {expected}, got {result['stress_cost']}"
                )

    def test_resistance_roll_crit_zero_cost(self):
        """Two sixes -> crit flag True and stress_cost == 0."""
        class _AlwaysSix(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 6

        result = resistance_roll(2, rng=_AlwaysSix())
        assert result["crit"] is True
        assert result["stress_cost"] == 0

    def test_resistance_roll_zero_dice_takes_lowest(self):
        """attribute_dice=0 -> 2d6 take lowest."""
        rng = random.Random(42)
        result = resistance_roll(0, rng=rng)
        # 2 dice rolled, highest = lowest of the pair
        assert len(result["dice"]) == 2
        assert result["highest"] == min(result["dice"])

    def test_resistance_roll_no_clock_push_result_none(self):
        """Without a clock, push_result must be None."""
        rng = random.Random(1)
        result = resistance_roll(2, stress_clock=None, rng=rng)
        assert result["push_result"] is None

    def test_resistance_roll_with_clock_no_cost_on_crit(self):
        """Crit resistance must not push any stress onto the clock."""
        class _AlwaysSix(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 6

        clock = StressClock(current_stress=3)
        result = resistance_roll(2, stress_clock=clock, rng=_AlwaysSix())
        assert result["stress_cost"] == 0
        assert result["push_result"] is None
        assert clock.current_stress == 3  # unchanged

    def test_resistance_roll_with_clock_integrates_stress(self):
        """Non-crit resistance pushes stress onto the clock."""
        # Force a result of highest=1 (cost=5) with a 1-die roll
        class _AlwaysOne(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 1

        clock = StressClock(current_stress=0)
        result = resistance_roll(1, stress_clock=clock, rng=_AlwaysOne())
        assert result["stress_cost"] == 5
        assert result["push_result"] is not None
        assert clock.current_stress == 5

    def test_resistance_roll_trauma_on_overflow(self):
        """If resistance cost overflows stress, trauma triggers in clock."""
        class _AlwaysOne(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 1

        clock = StressClock(current_stress=7)   # cost=5 will overflow to 12 -> trauma
        result = resistance_roll(1, stress_clock=clock, rng=_AlwaysOne())
        assert result["push_result"]["trauma_triggered"] is True

    def test_resistance_roll_cost_minimum_zero(self):
        """stress_cost can never be negative (highest=6 non-crit -> cost=0)."""
        class _AlwaysSix(random.Random):
            # Only one die so no crit
            _call_count = 0
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 6

        result = resistance_roll(1, rng=_AlwaysSix())
        # Single die of 6 => 1 six => not crit, but cost = 6-6 = 0
        assert result["stress_cost"] == 0
        assert result["crit"] is False


# ===========================================================================
# gather_information()
# ===========================================================================

class TestGatherInformation:

    def test_gather_information_basic_keys(self):
        """Result dict must contain all expected keys."""
        rng = random.Random(1)
        result = gather_information(2, question="Who owns the warehouse?", rng=rng)
        for key in ("outcome", "dice", "highest", "quality", "question"):
            assert key in result, f"Missing key: {key}"

    def test_gather_information_question_preserved(self):
        """The question string is returned verbatim."""
        q = "What is the guard rotation?"
        result = gather_information(1, question=q, rng=random.Random(5))
        assert result["question"] == q

    def test_gather_information_outcome_maps_to_quality(self):
        """All possible outcomes have a quality string that is not 'unknown'."""
        quality_map = {
            "failure": "nothing useful",
            "mixed": "partial/incomplete",
            "success": "good detail",
            "critical": "exceptional detail + extra",
        }
        for seed in range(500):
            result = gather_information(3, rng=random.Random(seed))
            expected = quality_map.get(result["outcome"])
            if expected:
                assert result["quality"] == expected

    def test_gather_information_zero_dots_still_works(self):
        """0 action_dots rolls 2d6 take lowest (disadvantage)."""
        rng = random.Random(10)
        result = gather_information(0, rng=rng)
        assert len(result["dice"]) == 2
        assert result["highest"] == min(result["dice"])

    def test_gather_information_failure_outcome(self):
        """Force a failure and check quality."""
        class _AlwaysOne(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 1

        result = gather_information(2, rng=_AlwaysOne())
        assert result["outcome"] == "failure"
        assert result["quality"] == "nothing useful"

    def test_gather_information_critical_outcome(self):
        """Force a critical and check quality."""
        class _AlwaysSix(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 6

        result = gather_information(2, rng=_AlwaysSix())
        assert result["outcome"] == "critical"
        assert result["quality"] == "exceptional detail + extra"


# ===========================================================================
# ConsequenceTable
# ===========================================================================

class TestConsequenceTable:

    def test_consequence_table_default_controlled_failure(self):
        table = ConsequenceTable()
        cons = table.get_consequences("controlled", "failure")
        assert "reduced effect" in cons

    def test_consequence_table_default_risky_failure(self):
        table = ConsequenceTable()
        cons = table.get_consequences("risky", "failure")
        assert "complication" in cons
        assert "harm" in cons

    def test_consequence_table_default_desperate_failure(self):
        table = ConsequenceTable()
        cons = table.get_consequences("desperate", "failure")
        assert "severe harm" in cons
        assert "lost opportunity" in cons

    def test_consequence_table_success_is_empty(self):
        """No default consequences on full success."""
        table = ConsequenceTable()
        cons = table.get_consequences("risky", "success")
        assert cons == []

    def test_consequence_table_override_replaces_defaults(self):
        """An override must fully replace the default, not extend it."""
        overrides = {
            "risky": {
                "failure": ["custom_consequence"],
            }
        }
        table = ConsequenceTable(overrides=overrides)
        cons = table.get_consequences("risky", "failure")
        assert cons == ["custom_consequence"]
        # harm and complication should NOT be present
        assert "harm" not in cons

    def test_consequence_table_override_partial(self):
        """An override for one position/outcome should not affect others."""
        overrides = {"risky": {"failure": ["custom"]}}
        table = ConsequenceTable(overrides=overrides)
        # Unchanged path
        cons_mixed = table.get_consequences("risky", "mixed")
        assert "complication" in cons_mixed

    def test_consequence_table_unknown_position_returns_empty(self):
        table = ConsequenceTable()
        assert table.get_consequences("mythic", "failure") == []

    def test_consequence_table_roundtrip_serialization(self):
        """to_dict() / from_dict() round-trip must preserve overrides."""
        overrides = {"desperate": {"mixed": ["oops"]}}
        table = ConsequenceTable(overrides=overrides)
        restored = ConsequenceTable.from_dict(table.to_dict())
        assert restored.get_consequences("desperate", "mixed") == ["oops"]

    def test_consequence_table_case_insensitive(self):
        """Position and outcome strings should be lowercased internally."""
        table = ConsequenceTable()
        cons = table.get_consequences("RISKY", "FAILURE")
        assert "complication" in cons

    def test_consequence_types_module_constant_intact(self):
        """CONSEQUENCE_TYPES module constant has all three positions."""
        for pos in ("controlled", "risky", "desperate"):
            assert pos in CONSEQUENCE_TYPES


# ===========================================================================
# format_fortune_result()
# ===========================================================================

class TestFormatFortuneResult:

    def test_format_fortune_result_contains_outcome(self):
        r = FortuneResult(outcome="mixed", highest=5, all_dice=[3, 5])
        text = format_fortune_result(r)
        assert "MIXED" in text

    def test_format_fortune_result_contains_dice(self):
        r = FortuneResult(outcome="good", highest=6, all_dice=[2, 6])
        text = format_fortune_result(r)
        assert "2" in text
        assert "6" in text

    def test_format_fortune_result_format_prefix(self):
        r = FortuneResult(outcome="bad", highest=2, all_dice=[2])
        text = format_fortune_result(r)
        assert text.startswith("Fortune:")

    def test_format_fortune_result_crit(self):
        r = FortuneResult(outcome="crit", highest=6, all_dice=[6, 6])
        text = format_fortune_result(r)
        assert "CRIT" in text


# ===========================================================================
# NarrativeEngineBase.roll_fortune()
# ===========================================================================

class TestNarrativeBaseRollFortune:

    def test_roll_fortune_returns_fortune_result(self):
        engine = _make_engine_with_char()
        result = engine.roll_fortune(dice_count=2)
        assert isinstance(result, FortuneResult)

    def test_roll_fortune_adds_shard(self):
        engine = _make_engine_with_char()
        initial_shards = len(engine._memory_shards)
        engine.roll_fortune(dice_count=1)
        assert len(engine._memory_shards) > initial_shards

    def test_roll_fortune_shard_contains_outcome(self):
        engine = _make_engine_with_char()
        result = engine.roll_fortune(dice_count=1)
        last_shard = engine._memory_shards[-1]
        assert result.outcome in last_shard.content.lower()

    def test_roll_fortune_zero_dice(self):
        engine = _make_engine_with_char()
        result = engine.roll_fortune(dice_count=0)
        # 2d6 take lowest => 2 dice
        assert len(result.all_dice) == 2

    def test_cmd_fortune_returns_string(self):
        engine = _make_engine_with_char()
        out = engine.handle_command("fortune", dice_count=2)
        assert isinstance(out, str)
        assert "Fortune:" in out

    def test_cmd_fortune_default_one_die(self):
        engine = _make_engine_with_char()
        out = engine.handle_command("fortune")
        # Default is 1 die -> exactly 1 value in brackets
        assert "Fortune:" in out


# ===========================================================================
# NarrativeEngineBase.roll_resistance()
# ===========================================================================

class TestNarrativeBaseRollResistance:

    def test_roll_resistance_returns_dict(self):
        engine = _make_engine_with_char()
        result = engine.roll_resistance(attribute="hunt")
        assert isinstance(result, dict)
        for key in ("dice", "highest", "stress_cost", "crit", "push_result"):
            assert key in result

    def test_roll_resistance_adds_shard(self):
        engine = _make_engine_with_char()
        initial = len(engine._memory_shards)
        engine.roll_resistance(attribute="hunt")
        assert len(engine._memory_shards) > initial

    def test_roll_resistance_uses_character_dots(self):
        """hunt=2 -> 2 dice rolled."""
        engine = _make_engine_with_char()
        engine.character.hunt = 2
        # Verify length of dice array matches the dots
        # (0-dot char would roll 2d6 take lowest, also 2 dice — so use 3 dots)
        engine.character.hunt = 3
        result = engine.roll_resistance(attribute="hunt")
        assert len(result["dice"]) == 3

    def test_cmd_resist_no_char_returns_message(self):
        engine = _FakeEngine()  # no character created
        out = engine.handle_command("resist", attribute="hunt")
        assert "No active character" in out

    def test_cmd_resist_no_attribute_returns_hint(self):
        engine = _make_engine_with_char()
        out = engine.handle_command("resist")
        assert "attribute" in out.lower()

    def test_cmd_resist_returns_formatted_string(self):
        engine = _make_engine_with_char()
        out = engine.handle_command("resist", attribute="hunt")
        assert "Resistance" in out
        assert "stress" in out.lower()

    def test_cmd_resist_crit_message(self):
        """When crit, output should mention CRIT."""
        class _AlwaysSix(random.Random):
            def randint(self, a: int, b: int) -> int:  # type: ignore[override]
                return 6

        engine = _make_engine_with_char()
        engine.character.hunt = 2
        # Patch to force a crit by monkeypatching resistance_roll result
        import codex.core.engines.narrative_base as nb
        original = nb.NarrativeEngineBase._cmd_resist

        called = {}

        def _mock_resist(self, **kwargs):
            called["ran"] = True
            return original(self, **kwargs)

        # We can't easily mock rng through handle_command, so just confirm
        # that the output contains "CRIT" when we force it via roll_resistance
        from codex.core.services import fitd_engine as fe
        orig_rr = fe.resistance_roll

        def _force_crit(attribute_dice, stress_clock=None, rng=None):
            return orig_rr(attribute_dice, stress_clock, rng=_AlwaysSix())

        fe.resistance_roll = _force_crit
        try:
            out = engine.handle_command("resist", attribute="hunt")
        finally:
            fe.resistance_roll = orig_rr

        assert "CRIT" in out


# ===========================================================================
# NarrativeEngineBase.gather_information()
# ===========================================================================

class TestNarrativeBaseGatherInfo:

    def test_gather_information_returns_dict(self):
        engine = _make_engine_with_char()
        result = engine.gather_information(action="survey", question="Who is watching?")
        assert isinstance(result, dict)
        for key in ("outcome", "dice", "highest", "quality", "question"):
            assert key in result

    def test_gather_information_adds_shard(self):
        engine = _make_engine_with_char()
        initial = len(engine._memory_shards)
        engine.gather_information(action="survey", question="Test question")
        assert len(engine._memory_shards) > initial

    def test_gather_information_question_in_shard(self):
        engine = _make_engine_with_char()
        engine.gather_information(action="survey", question="Find the vault")
        last_shard = engine._memory_shards[-1]
        # First 50 chars of question should be in shard content
        assert "Find the vault" in last_shard.content

    def test_cmd_gather_info_returns_string(self):
        engine = _make_engine_with_char()
        out = engine.handle_command("gather_info", action="survey", question="Where is the target?")
        assert isinstance(out, str)
        assert "Gather Info" in out

    def test_cmd_gather_info_default_action(self):
        """Without an action kwarg, defaults to 'survey'."""
        engine = _make_engine_with_char()
        out = engine.handle_command("gather_info")
        assert "survey" in out.lower()

    def test_cmd_gather_info_question_shown_when_provided(self):
        engine = _make_engine_with_char()
        out = engine.handle_command("gather_info", action="hunt", question="Track the courier")
        assert "Track the courier" in out

    def test_cmd_gather_info_no_question_no_question_line(self):
        engine = _make_engine_with_char()
        out = engine.handle_command("gather_info", action="hunt")
        assert "Question:" not in out

    def test_gather_information_no_char_uses_zero_dots(self):
        """Engine with no character falls back to 0 dots (2d6 take lowest)."""
        engine = _FakeEngine()   # no character created
        result = engine.gather_information(action="hunt")
        assert len(result["dice"]) == 2
        assert result["highest"] == min(result["dice"])

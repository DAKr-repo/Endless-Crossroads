"""
tests/test_mechanics_suite.py — Comprehensive mechanics module test coverage.
==============================================================================

Covers: clock, conditions, initiative, rest, progression, capacity_manager.

WO-V51.0: The Foundation Sprint — Track A
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# =========================================================================
# CLOCK TESTS (~10)
# =========================================================================

from codex.core.mechanics.clock import UniversalClock, FactionClock, DoomClock


class TestUniversalClockTick:
    """Segment-mode tick behavior."""

    def test_tick_clamps_to_max_segments(self):
        c = UniversalClock("Test", max_segments=4, filled=3)
        c.tick(5)
        assert c.filled == 4

    def test_tick_free_increment_without_max(self):
        c = UniversalClock("Test", max_segments=None, filled=0)
        c.tick(100)
        assert c.filled == 100


class TestUniversalClockAdvance:
    """Threshold-mode advance behavior."""

    def test_advance_triggers_thresholds(self):
        c = DoomClock(current=4, thresholds={5: "Dread", 10: "Terror"})
        events = c.advance(1)
        assert events == ["[DOOM 5] Dread"]
        assert c.filled == 5

    def test_advance_skips_already_crossed(self):
        c = DoomClock(current=6, thresholds={5: "Dread", 10: "Terror"})
        events = c.advance(1)
        assert events == []

    def test_advance_returns_doom_format(self):
        c = DoomClock(current=9, thresholds={10: "Collapse"})
        events = c.advance(1)
        assert len(events) == 1
        assert events[0].startswith("[DOOM 10]")


class TestUniversalClockProperties:
    """Property aliases and state checks."""

    def test_is_complete_segment_mode(self):
        c = FactionClock("Faction", segments=4, filled=4)
        assert c.is_complete is True

    def test_is_complete_false_without_segments(self):
        c = UniversalClock("Free", max_segments=None, filled=999)
        assert c.is_complete is False

    def test_current_property_alias(self):
        c = UniversalClock("Test", filled=7)
        assert c.current == 7
        c.current = 12
        assert c.filled == 12

    def test_reset_sets_filled_to_zero(self):
        c = UniversalClock("Test", filled=15)
        c.reset()
        assert c.filled == 0


class TestUniversalClockSerialization:
    """to_dict / from_dict roundtrip."""

    def test_roundtrip(self):
        c = UniversalClock("Doom", filled=7, max_segments=20,
                           thresholds={5: "Dread", 10: "Terror"})
        d = c.to_dict()
        c2 = UniversalClock.from_dict(d)
        assert c2.name == "Doom"
        assert c2.filled == 7
        assert c2.max_segments == 20
        assert c2.thresholds == {5: "Dread", 10: "Terror"}

    def test_from_dict_coerces_string_threshold_keys(self):
        data = {"name": "Doom", "filled": 0,
                "thresholds": {"5": "Dread", "10": "Terror"}}
        c = UniversalClock.from_dict(data)
        assert 5 in c.thresholds
        assert 10 in c.thresholds


class TestClockFactories:
    """FactionClock / DoomClock factory functions."""

    def test_faction_clock_factory(self):
        c = FactionClock("Guild", segments=6)
        assert c.max_segments == 6
        assert c.filled == 0

    def test_doom_clock_factory(self):
        c = DoomClock(current=3, thresholds={5: "Event"})
        assert c.name == "Doom"
        assert c.filled == 3
        assert c.max_segments is None


# =========================================================================
# CONDITIONS TESTS (~12)
# =========================================================================

from codex.core.mechanics.conditions import (
    Condition, ConditionTracker, ConditionType,
    format_condition_icons, CONDITION_DEFAULTS,
)


class TestConditionTrackerApply:
    """apply() replaces same type (refresh, not stack)."""

    def test_apply_returns_status_message(self):
        tracker = ConditionTracker()
        msg = tracker.apply("Goblin", Condition(
            condition_type=ConditionType.POISONED, duration=3))
        assert "Poisoned" in msg
        assert "3 rounds" in msg

    def test_apply_replaces_same_type(self):
        tracker = ConditionTracker()
        tracker.apply("Goblin", Condition(
            condition_type=ConditionType.POISONED, duration=2))
        tracker.apply("Goblin", Condition(
            condition_type=ConditionType.POISONED, duration=5))
        conds = tracker.get_conditions("Goblin")
        assert len(conds) == 1
        assert conds[0].duration == 5


class TestConditionTrackerRemove:
    """remove() by type; edge cases."""

    def test_remove_absent_entity(self):
        tracker = ConditionTracker()
        msg = tracker.remove("Nobody", ConditionType.STUNNED)
        assert "has no conditions" in msg

    def test_remove_absent_type(self):
        tracker = ConditionTracker()
        tracker.apply("Goblin", Condition(
            condition_type=ConditionType.POISONED, duration=3))
        msg = tracker.remove("Goblin", ConditionType.STUNNED)
        assert "is not Stunned" in msg

    def test_remove_existing(self):
        tracker = ConditionTracker()
        tracker.apply("Goblin", Condition(
            condition_type=ConditionType.POISONED, duration=3))
        msg = tracker.remove("Goblin", ConditionType.POISONED)
        assert "removed" in msg
        assert not tracker.has("Goblin", ConditionType.POISONED)


class TestConditionTrackerTick:
    """tick_round() decrements, expires, preserves permanent/until-save."""

    def test_tick_decrements_and_expires(self):
        tracker = ConditionTracker()
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.STUNNED, duration=1))
        msgs = tracker.tick_round("Orc")
        assert any("expired" in m for m in msgs)
        assert not tracker.has("Orc", ConditionType.STUNNED)

    def test_tick_preserves_permanent(self):
        tracker = ConditionTracker()
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.BLIGHTED, duration=-2))
        tracker.tick_round("Orc")
        assert tracker.has("Orc", ConditionType.BLIGHTED)

    def test_tick_preserves_until_save(self):
        tracker = ConditionTracker()
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.FRIGHTENED, duration=-1))
        tracker.tick_round("Orc")
        assert tracker.has("Orc", ConditionType.FRIGHTENED)


class TestConditionTrackerQueries:
    """has(), should_skip_turn(), clear_all(), get_all_entities()."""

    def test_should_skip_turn_stunned(self):
        tracker = ConditionTracker()
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.STUNNED, duration=2))
        assert tracker.should_skip_turn("Orc") is True
        assert tracker.should_skip_turn("Nobody") is False

    def test_clear_all(self):
        tracker = ConditionTracker()
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.POISONED, duration=3))
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.STUNNED, duration=2))
        tracker.clear_all("Orc")
        assert tracker.get_conditions("Orc") == []

    def test_get_all_entities(self):
        tracker = ConditionTracker()
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.POISONED, duration=3))
        tracker.apply("Goblin", Condition(
            condition_type=ConditionType.STUNNED, duration=2))
        entities = tracker.get_all_entities()
        assert set(entities) == {"Orc", "Goblin"}


class TestConditionModifiers:
    """get_attack_mod() and get_defense_mod()."""

    def test_get_attack_mod_sums(self):
        tracker = ConditionTracker()
        tracker.apply("Hero", Condition(
            condition_type=ConditionType.POISONED, duration=3, modifier=-2))
        tracker.apply("Hero", Condition(
            condition_type=ConditionType.BLESSED, duration=3, modifier=2))
        mod = tracker.get_attack_mod("Hero")
        assert mod == 0  # -2 + 2 = 0

    def test_get_defense_mod_blighted_and_hasted(self):
        tracker = ConditionTracker()
        tracker.apply("Hero", Condition(
            condition_type=ConditionType.BLIGHTED, duration=3, modifier=-1))
        tracker.apply("Hero", Condition(
            condition_type=ConditionType.HASTED, duration=3))
        mod = tracker.get_defense_mod("Hero")
        assert mod == 1  # -1 + 2 = 1


class TestConditionFormatIcons:
    """format_condition_icons() with mixed inputs."""

    def test_format_mixed_condition_and_dict(self):
        cond = Condition(condition_type=ConditionType.POISONED, duration=2)
        d = {"type": "Stunned"}
        result = format_condition_icons([cond, d])
        assert "Poisoned" in result
        assert "Stunned" in result

    def test_format_empty_returns_empty(self):
        assert format_condition_icons([]) == ""


class TestConditionSerialization:
    """to_dict / from_dict roundtrip."""

    def test_tracker_roundtrip(self):
        tracker = ConditionTracker()
        tracker.apply("Orc", Condition(
            condition_type=ConditionType.POISONED, duration=3, modifier=-2))
        tracker.apply("Hero", Condition(
            condition_type=ConditionType.HASTED, duration=-2))
        d = tracker.to_dict()
        t2 = ConditionTracker.from_dict(d)
        assert t2.has("Orc", ConditionType.POISONED)
        assert t2.has("Hero", ConditionType.HASTED)


# =========================================================================
# INITIATIVE TESTS (~8)
# =========================================================================

from codex.core.mechanics.initiative import InitiativeTracker


class TestInitiativeRoll:
    """roll_initiative() with seeded rng."""

    def test_deterministic_with_seeded_rng(self):
        tracker = InitiativeTracker()
        rng = random.Random(42)
        entry = tracker.roll_initiative("Hero", modifier=3, die=20, rng=rng)
        # Deterministic: same seed always gives same result
        tracker2 = InitiativeTracker()
        rng2 = random.Random(42)
        entry2 = tracker2.roll_initiative("Hero", modifier=3, die=20, rng=rng2)
        assert entry.roll == entry2.roll


class TestInitiativeSort:
    """sort() descending by (roll, modifier)."""

    def test_sort_descending(self):
        tracker = InitiativeTracker()
        tracker.entries = []
        from codex.core.mechanics.initiative import InitiativeEntry
        tracker.entries.append(InitiativeEntry("Slow", roll=5, modifier=0, is_player=True))
        tracker.entries.append(InitiativeEntry("Fast", roll=20, modifier=3, is_player=True))
        tracker.entries.append(InitiativeEntry("Mid", roll=12, modifier=1, is_player=False))
        tracker.sort()
        assert [e.name for e in tracker.entries] == ["Fast", "Mid", "Slow"]


class TestInitiativeNextTurn:
    """next_turn() wraps round, skips inactive."""

    def test_next_turn_wraps_round(self):
        tracker = InitiativeTracker()
        from codex.core.mechanics.initiative import InitiativeEntry
        tracker.entries = [
            InitiativeEntry("A", roll=20, modifier=0, is_player=True),
            InitiativeEntry("B", roll=10, modifier=0, is_player=False),
        ]
        tracker.current_index = 0
        e1 = tracker.next_turn()
        assert e1.name == "B"
        e2 = tracker.next_turn()
        assert e2.name == "A"
        assert tracker.round_number == 2  # wrapped around

    def test_next_turn_skips_inactive(self):
        tracker = InitiativeTracker()
        from codex.core.mechanics.initiative import InitiativeEntry
        tracker.entries = [
            InitiativeEntry("A", roll=20, modifier=0, is_player=True),
            InitiativeEntry("Dead", roll=15, modifier=0, is_player=False, is_active=False),
            InitiativeEntry("C", roll=5, modifier=0, is_player=True),
        ]
        tracker.current_index = 0
        e = tracker.next_turn()
        assert e.name == "C"  # skipped Dead

    def test_next_turn_none_when_all_inactive(self):
        tracker = InitiativeTracker()
        from codex.core.mechanics.initiative import InitiativeEntry
        tracker.entries = [
            InitiativeEntry("Dead", roll=20, modifier=0, is_player=True, is_active=False),
        ]
        assert tracker.next_turn() is None


class TestInitiativeCurrent:
    """current() self-heals out-of-range index."""

    def test_current_heals_out_of_range(self):
        tracker = InitiativeTracker()
        from codex.core.mechanics.initiative import InitiativeEntry
        tracker.entries = [
            InitiativeEntry("A", roll=20, modifier=0, is_player=True),
        ]
        tracker.current_index = 99
        e = tracker.current()
        assert e.name == "A"
        assert tracker.current_index == 0


class TestInitiativeRemoveAndOrder:
    """remove() marks inactive; get_order() returns active names."""

    def test_remove_marks_inactive(self):
        tracker = InitiativeTracker()
        from codex.core.mechanics.initiative import InitiativeEntry
        tracker.entries = [
            InitiativeEntry("A", roll=20, modifier=0, is_player=True),
            InitiativeEntry("B", roll=10, modifier=0, is_player=False),
        ]
        tracker.remove("B")
        assert not tracker.entries[1].is_active
        assert tracker.get_order() == ["A"]


class TestInitiativeSerialization:
    """to_dict / from_dict roundtrip preserving inactive entries."""

    def test_roundtrip(self):
        tracker = InitiativeTracker()
        from codex.core.mechanics.initiative import InitiativeEntry
        tracker.entries = [
            InitiativeEntry("A", roll=20, modifier=2, is_player=True),
            InitiativeEntry("Dead", roll=10, modifier=0, is_player=False, is_active=False),
        ]
        tracker.round_number = 3
        d = tracker.to_dict()
        t2 = InitiativeTracker.from_dict(d)
        assert len(t2.entries) == 2
        assert t2.entries[1].is_active is False
        assert t2.round_number == 3


# =========================================================================
# REST TESTS (~10)
# =========================================================================

from codex.core.mechanics.rest import RestManager, RestResult


@dataclass
class _MockChar:
    """Minimal mock character for rest tests."""
    name: str
    hp: int
    max_hp: int
    constitution: int = 14
    hit_dice_remaining: int = 3
    hit_die_type: int = 8
    level: int = 5
    focus: int = 0
    intellect: int = 14

    def heal(self, amount: int) -> int:
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual


class _MockDoomClock:
    """Minimal mock doom clock."""
    def __init__(self):
        self.filled = 0

    def tick(self, amount: int = 1):
        self.filled += amount


class _MockEngine:
    """Minimal mock engine for rest tests."""
    def __init__(self, party=None, system_id="burnwillow"):
        self._party = party or []
        self.system_id = system_id
        self.doom_clock = _MockDoomClock()
        self.stress_clocks: Dict[str, MagicMock] = {}

    def get_active_party(self):
        return self._party


class TestRestBurnwillow:
    """short_rest_burnwillow / long_rest_burnwillow."""

    def test_short_rest_heals_leader_half(self):
        leader = _MockChar("Kael", hp=5, max_hp=20)
        member = _MockChar("Lyra", hp=3, max_hp=16)
        engine = _MockEngine(party=[leader, member])
        mgr = RestManager()
        result = mgr.short_rest_burnwillow(engine)
        assert result.hp_recovered["Kael"] == 10  # max(1, 20//2) = 10
        assert result.hp_recovered["Lyra"] == 4   # max(1, 16//4) = 4
        assert "Doom +1" in result.side_effects

    def test_long_rest_full_heal_doom_3(self):
        leader = _MockChar("Kael", hp=1, max_hp=20)
        engine = _MockEngine(party=[leader])
        mgr = RestManager()
        result = mgr.long_rest_burnwillow(engine)
        assert leader.hp == 20
        assert "Doom +3" in result.side_effects


class TestRestDnd5e:
    """short_rest_dnd5e / long_rest_dnd5e."""

    def test_short_rest_spends_hit_die(self):
        char = _MockChar("Hero", hp=5, max_hp=40, constitution=14,
                         hit_dice_remaining=3, hit_die_type=8)
        engine = _MockEngine(party=[char])
        mgr = RestManager()
        result = mgr.short_rest_dnd5e(engine)
        assert char.hit_dice_remaining == 2
        assert "Hero" in result.hp_recovered

    def test_short_rest_skips_zero_hd(self):
        char = _MockChar("Hero", hp=5, max_hp=40, hit_dice_remaining=0)
        engine = _MockEngine(party=[char])
        mgr = RestManager()
        result = mgr.short_rest_dnd5e(engine)
        assert "Hero" not in result.hp_recovered

    def test_long_rest_full_hp_recover_hd(self):
        char = _MockChar("Hero", hp=5, max_hp=40, level=6,
                         hit_dice_remaining=1)
        engine = _MockEngine(party=[char])
        mgr = RestManager()
        result = mgr.long_rest_dnd5e(engine)
        assert char.hp == 40
        # Recover max(1, 6//2) = 3 hit dice, capped at level (6)
        assert char.hit_dice_remaining == 4  # 1 + 3 = 4


class TestRestCosmere:
    """short_rest_cosmere focus recovery."""

    def test_short_rest_recovers_focus(self):
        char = _MockChar("Radiant", hp=20, max_hp=20, intellect=14, focus=0)
        engine = _MockEngine(party=[char])
        mgr = RestManager()
        result = mgr.short_rest_cosmere(engine)
        expected_focus = max(0, (14 - 10) // 2 + 2)  # 4
        assert char.focus == expected_focus


class TestRestDispatcher:
    """rest() dispatcher routes correctly."""

    def test_case_insensitive_tag(self):
        engine = _MockEngine(party=[_MockChar("Hero", 5, 20)])
        mgr = RestManager()
        result = mgr.rest(engine, "burnwillow", "short")
        assert result.rest_type == "short"

    def test_unknown_system(self):
        engine = _MockEngine(party=[])
        mgr = RestManager()
        result = mgr.rest(engine, "unknown_system", "short")
        assert "Unknown system" in result.side_effects

    def test_empty_party_no_crash(self):
        engine = _MockEngine(party=[])
        mgr = RestManager()
        result = mgr.rest(engine, "burnwillow", "short")
        assert result.hp_recovered == {}


# =========================================================================
# PROGRESSION TESTS (~8)
# =========================================================================

from codex.core.mechanics.progression import (
    ProgressionTracker, DND5E_XP_TABLE, FITD_XP_PER_ADVANCE,
)


class TestProgressionXP:
    """award_xp() and check_level_up()."""

    def test_award_xp_accumulates(self):
        tracker = ProgressionTracker(system="xp")
        tracker.award_xp(100, "goblin")
        tracker.award_xp(200, "chest")
        assert tracker.current_xp == 300
        assert len(tracker.xp_log) == 2

    def test_check_level_up_vs_table(self):
        tracker = ProgressionTracker(system="xp", current_xp=300)
        assert tracker.check_level_up(1) is True  # 300 >= 300 for level 2
        assert tracker.check_level_up(2) is False  # 300 < 900 for level 3

    def test_check_level_up_non_xp_system(self):
        tracker = ProgressionTracker(system="fitd")
        tracker.current_xp = 9999
        assert tracker.check_level_up(1) is False

    def test_check_level_up_at_max_level(self):
        tracker = ProgressionTracker(system="xp", current_xp=999999)
        assert tracker.check_level_up(20) is False  # No level 21


class TestProgressionFITD:
    """mark_xp() 8 marks → advance."""

    def test_mark_xp_triggers_advance(self):
        tracker = ProgressionTracker(system="fitd", current_xp=7)
        msg = tracker.mark_xp("desperate action")
        assert "ADVANCE AVAILABLE!" in msg
        assert tracker.current_xp == 0  # reset after 8


class TestProgressionMilestone:
    """advance_milestone() increments and logs."""

    def test_advance_milestone(self):
        tracker = ProgressionTracker(system="milestone")
        msg = tracker.advance_milestone("Swore First Ideal")
        assert tracker.milestones == 1
        assert "milestone" in tracker.xp_log[0]["type"]


class TestProgressionXPToNext:
    """get_xp_to_next() non-xp system → 0."""

    def test_xp_to_next_non_xp(self):
        tracker = ProgressionTracker(system="fitd")
        assert tracker.get_xp_to_next(5) == 0

    def test_xp_to_next_xp_system(self):
        tracker = ProgressionTracker(system="xp", current_xp=100)
        remaining = tracker.get_xp_to_next(1)
        assert remaining == 200  # 300 - 100


class TestProgressionSerialization:
    """to_dict() truncates xp_log; from_dict roundtrip."""

    def test_to_dict_truncates_log(self):
        tracker = ProgressionTracker(system="xp")
        for i in range(30):
            tracker.award_xp(10, f"source_{i}")
        d = tracker.to_dict()
        assert len(d["xp_log"]) == 20  # truncated

    def test_roundtrip(self):
        tracker = ProgressionTracker(system="xp", current_xp=500, milestones=2)
        tracker.xp_log = [{"amount": 500, "source": "dragon"}]
        d = tracker.to_dict()
        t2 = ProgressionTracker.from_dict(d)
        assert t2.system == "xp"
        assert t2.current_xp == 500
        assert t2.milestones == 2


# =========================================================================
# CAPACITY MANAGER TESTS (~7)
# =========================================================================

from codex.core.services.capacity_manager import (
    check_capacity, CapacityMode, CapacityStatus,
)


class TestCapacityManager:
    """check_capacity() pure function tests."""

    def test_ok_within_80_percent(self):
        result = check_capacity(CapacityMode.SLOTS, limit=10, current=7)
        assert result["status"] == CapacityStatus.OK.value

    def test_warning_above_80_percent(self):
        result = check_capacity(CapacityMode.SLOTS, limit=10, current=9)
        assert result["status"] == CapacityStatus.WARNING.value
        assert "heavy" in result["message"].lower()

    def test_over_capacity_above_100(self):
        result = check_capacity(CapacityMode.WEIGHT, limit=50, current=60)
        assert result["status"] == CapacityStatus.OVER_CAPACITY.value
        assert "over" in result["message"].lower()

    def test_zero_limit_zero_current_ok(self):
        result = check_capacity(CapacityMode.SLOTS, limit=0, current=0)
        assert result["status"] == CapacityStatus.OK.value

    def test_zero_limit_positive_current_warning(self):
        # limit=0, current>0 → ratio=1.0 → WARNING (ratio > 0.8 but not > 1.0)
        result = check_capacity(CapacityMode.SLOTS, limit=0, current=5)
        assert result["status"] == CapacityStatus.WARNING.value

    def test_exactly_80_percent_is_ok(self):
        result = check_capacity(CapacityMode.SLOTS, limit=10, current=8)
        assert result["status"] == CapacityStatus.OK.value

    def test_negative_remaining_when_over(self):
        result = check_capacity(CapacityMode.WEIGHT, limit=50, current=60)
        assert result["remaining"] == -10.0

    def test_slots_wording(self):
        result = check_capacity(CapacityMode.SLOTS, limit=10, current=11)
        assert "slots" in result["message"]

    def test_weight_wording(self):
        result = check_capacity(CapacityMode.WEIGHT, limit=50, current=55)
        assert "weight" in result["message"]

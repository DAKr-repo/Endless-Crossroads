"""Tests for WO-V61.0 Track C — Momentum Ledger."""
import pytest
from codex.core.services.momentum import (
    MomentumLedger, MomentumBin, MomentumEntry,
    ACTION_CATEGORY_MAP, CASCADE_MAP,
)


class TestMomentumLedgerBasics:
    def test_empty_ledger(self):
        ledger = MomentumLedger()
        assert ledger.get_all_trends() == []

    def test_record_creates_bin(self):
        ledger = MomentumLedger()
        ledger.record("security", "dock_ward", "kill", weight=1.0)
        b = ledger.get_bin("security", "dock_ward")
        assert b is not None
        assert b.total_weight == 1.0
        assert b.entry_count == 1

    def test_record_accumulates(self):
        ledger = MomentumLedger()
        ledger.record("security", "dock_ward", "kill", 1.0)
        ledger.record("security", "dock_ward", "kill", 1.0)
        ledger.record("security", "dock_ward", "room_cleared", 0.5)
        b = ledger.get_bin("security", "dock_ward")
        assert b.total_weight == 2.5
        assert b.entry_count == 3

    def test_different_locations_separate(self):
        ledger = MomentumLedger()
        ledger.record("security", "dock_ward", "kill", 1.0)
        ledger.record("security", "north_ward", "kill", 1.0)
        assert ledger.get_bin("security", "dock_ward").total_weight == 1.0
        assert ledger.get_bin("security", "north_ward").total_weight == 1.0


class TestThresholds:
    def test_minor_shift_at_3(self):
        ledger = MomentumLedger()
        events = []
        for _ in range(3):
            events.extend(ledger.record("security", "ward", "kill", 1.0))
        assert any(e["name"] == "minor_shift" for e in events)

    def test_notable_trend_at_7(self):
        ledger = MomentumLedger()
        events = []
        for _ in range(7):
            events.extend(ledger.record("security", "ward", "kill", 1.0))
        assert any(e["name"] == "notable_trend" for e in events)

    def test_major_shift_at_12(self):
        ledger = MomentumLedger()
        events = []
        for _ in range(12):
            events.extend(ledger.record("security", "ward", "kill", 1.0))
        assert any(e["name"] == "major_shift" for e in events)

    def test_tipping_point_at_20(self):
        ledger = MomentumLedger()
        events = []
        for _ in range(20):
            events.extend(ledger.record("security", "ward", "kill", 1.0))
        assert any(e["name"] == "tipping_point" for e in events)

    def test_threshold_fires_once(self):
        """Same threshold doesn't fire twice."""
        ledger = MomentumLedger()
        events = []
        for _ in range(5):
            events.extend(ledger.record("security", "ward", "kill", 1.0))
        minor_shifts = [e for e in events if e["name"] == "minor_shift"]
        assert len(minor_shifts) == 1

    def test_threshold_event_has_fields(self):
        ledger = MomentumLedger()
        events = ledger.record("security", "ward", "kill", 5.0)
        assert len(events) >= 1
        e = events[0]
        assert "level" in e
        assert "name" in e
        assert "category" in e
        assert "location" in e
        assert "total_weight" in e


class TestCascade:
    def test_cascade_at_tipping_point(self):
        ledger = MomentumLedger()
        # Push security to 20
        events = ledger.record("security", "ward", "kill", 20.0)
        tipping = [e for e in events if e["name"] == "tipping_point"]
        assert len(tipping) == 1
        assert tipping[0].get("cascade") is not None
        # Cascade should go to economics (per CASCADE_MAP)
        assert tipping[0]["cascade"]["category"] == "economics"
        # Verify the cascaded bin exists
        econ_bin = ledger.get_bin("economics", "ward")
        assert econ_bin is not None
        assert econ_bin.total_weight >= 3.0


class TestRecordFromEvent:
    def test_kill_maps_to_security(self):
        ledger = MomentumLedger()
        ledger.record_from_event("kill", "depths", turn=1, tier=1)
        b = ledger.get_bin("security", "depths")
        assert b is not None
        assert b.total_weight > 0

    def test_loot_maps_to_economics(self):
        ledger = MomentumLedger()
        ledger.record_from_event("loot", "depths", turn=1)
        b = ledger.get_bin("economics", "depths")
        assert b is not None

    def test_unknown_event_no_op(self):
        ledger = MomentumLedger()
        result = ledger.record_from_event("unknown_event", "depths")
        assert result == []

    def test_tier_scaling(self):
        ledger = MomentumLedger()
        ledger.record_from_event("kill", "depths", tier=3)
        b = ledger.get_bin("security", "depths")
        # tier 3: base 1.0 + (3-1)*0.5 = 2.0
        assert b.total_weight == 2.0

    def test_all_mapped_events(self):
        """Every event in ACTION_CATEGORY_MAP can be recorded."""
        ledger = MomentumLedger()
        for event_type in ACTION_CATEGORY_MAP:
            ledger.record_from_event(event_type, "test_loc", turn=1)
        trends = ledger.get_all_trends(min_weight=0.1)
        assert len(trends) > 0


class TestDominantTrend:
    def test_dominant_trend(self):
        ledger = MomentumLedger()
        ledger.record("security", "ward", "kill", 5.0)
        ledger.record("economics", "ward", "loot", 2.0)
        trend = ledger.get_dominant_trend("ward")
        assert trend is not None
        assert trend[0] == "security"
        assert trend[1] == 5.0

    def test_no_trend_for_empty_location(self):
        ledger = MomentumLedger()
        assert ledger.get_dominant_trend("nowhere") is None


class TestDecay:
    def test_decay_stale_bins(self):
        ledger = MomentumLedger()
        ledger.record("security", "ward", "kill", 2.0, turn=1)
        # Decay with current_turn far ahead
        ledger.decay(current_turn=100, stale_turns=30, decay_amount=0.5)
        b = ledger.get_bin("security", "ward")
        # 2.0 - 0.5 = 1.5, still above prune_below=1.0 default
        if b:
            assert b.total_weight < 2.0

    def test_decay_prunes_below_threshold(self):
        ledger = MomentumLedger()
        ledger.record("security", "ward", "kill", 1.0, turn=1)
        pruned = ledger.decay(current_turn=100, stale_turns=30, decay_amount=0.5)
        # 1.0 - 0.5 = 0.5, below prune_below=1.0
        assert pruned == 1
        assert ledger.get_bin("security", "ward") is None

    def test_active_bins_not_decayed(self):
        ledger = MomentumLedger()
        ledger.record("security", "ward", "kill", 5.0, turn=95)
        pruned = ledger.decay(current_turn=100, stale_turns=30)
        assert pruned == 0
        assert ledger.get_bin("security", "ward").total_weight == 5.0


class TestSerialization:
    def test_roundtrip(self):
        ledger = MomentumLedger(universe_id="test")
        ledger.record("security", "ward", "kill", 3.0, turn=1)
        ledger.record("economics", "ward", "loot", 1.5, turn=2)
        data = ledger.to_dict()
        restored = MomentumLedger.from_dict(data)
        assert restored.universe_id == "test"
        assert restored.get_bin("security", "ward").total_weight == 3.0
        assert restored.get_bin("economics", "ward").total_weight == 1.5

    def test_empty_ledger_roundtrip(self):
        ledger = MomentumLedger()
        data = ledger.to_dict()
        restored = MomentumLedger.from_dict(data)
        assert restored.get_all_trends() == []

    def test_backward_compat_no_momentum(self):
        """Loading save data without momentum_ledger doesn't crash."""
        data = {}
        ledger = MomentumLedger.from_dict(data)
        assert ledger.get_all_trends() == []


class TestGetAllTrends:
    def test_filters_by_min_weight(self):
        ledger = MomentumLedger()
        ledger.record("security", "ward", "kill", 5.0)
        ledger.record("economics", "ward", "loot", 1.0)
        trends = ledger.get_all_trends(min_weight=3.0)
        assert len(trends) == 1
        assert trends[0].category == "security"

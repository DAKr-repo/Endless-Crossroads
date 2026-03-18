"""Direct tests for codex/core/services/momentum.py.

Focuses on: threshold-crossing fires the event list (callback contract),
cascade detection and field inspection, negative thresholds, no double-fire
on the same threshold, serialization round-trip, and empty state defaults.

Complements test_momentum_ledger.py without duplicating its cases.
"""
import pytest
from codex.core.services.momentum import (
    MomentumLedger,
    MomentumBin,
    MomentumEntry,
    ACTION_CATEGORY_MAP,
    CASCADE_MAP,
)


# ---------------------------------------------------------------------------
# 1. Threshold crossing fires the returned event list (callback contract)
# ---------------------------------------------------------------------------

class TestThresholdCallbackContract:
    """record() returns a list of threshold events — callers use this as the
    callback mechanism.  Verify the list is populated at the right moments."""

    def test_no_events_returned_below_first_threshold(self):
        ledger = MomentumLedger()
        events = ledger.record("economics", "market", "trade", weight=2.9)
        assert events == [], "Should return empty list when weight < 3.0"

    def test_single_event_returned_exactly_at_first_threshold(self):
        ledger = MomentumLedger()
        events = ledger.record("economics", "market", "trade", weight=3.0)
        assert len(events) == 1
        assert events[0]["level"] == 3.0
        assert events[0]["name"] == "minor_shift"

    def test_multiple_thresholds_crossed_in_one_call(self):
        """Jumping from 0 to 8.0 should cross both 3.0 and 7.0."""
        ledger = MomentumLedger()
        events = ledger.record("economics", "market", "windfall", weight=8.0)
        levels = {e["level"] for e in events}
        assert 3.0 in levels
        assert 7.0 in levels

    def test_event_dict_contains_required_fields(self):
        ledger = MomentumLedger()
        events = ledger.record("politics", "hall", "vote", weight=3.5)
        assert len(events) >= 1
        ev = events[0]
        for field in ("level", "name", "category", "location", "total_weight", "entry_count"):
            assert field in ev, f"Event dict missing field: {field}"

    def test_category_and_location_match_record_call(self):
        ledger = MomentumLedger()
        events = ledger.record("religion", "shrine", "ritual", weight=3.1)
        assert len(events) == 1
        assert events[0]["category"] == "religion"
        assert events[0]["location"] == "shrine"

    def test_total_weight_in_event_reflects_actual_bin_weight(self):
        ledger = MomentumLedger()
        ledger.record("geography", "hills", "explore", weight=1.0)
        events = ledger.record("geography", "hills", "explore", weight=2.5)
        assert len(events) == 1
        assert events[0]["total_weight"] == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# 2. Cascade detection and field inspection
# ---------------------------------------------------------------------------

class TestCascadeDetection:
    def test_tipping_point_event_has_cascade_key(self):
        ledger = MomentumLedger()
        events = ledger.record("security", "ward", "patrol", weight=20.0)
        tipping = [e for e in events if e["level"] == 20.0]
        assert len(tipping) == 1
        assert "cascade" in tipping[0], "Tipping point event must have 'cascade' key"

    def test_cascade_key_contains_expected_fields(self):
        ledger = MomentumLedger()
        events = ledger.record("security", "ward", "patrol", weight=20.0)
        tipping = next(e for e in events if e["level"] == 20.0)
        cascade = tipping["cascade"]
        assert "category" in cascade
        assert "weight" in cascade

    def test_cascade_targets_correct_secondary_category(self):
        """Every category in CASCADE_MAP should cascade to the right secondary."""
        for primary, secondary in CASCADE_MAP.items():
            ledger = MomentumLedger()
            events = ledger.record(primary, "loc", "action", weight=20.0)
            tipping = next((e for e in events if e["level"] == 20.0), None)
            if tipping is None:
                pytest.fail(f"No tipping_point event for category {primary}")
            assert tipping["cascade"]["category"] == secondary, (
                f"Cascade from {primary} should target {secondary}"
            )

    def test_cascade_creates_secondary_bin(self):
        ledger = MomentumLedger()
        ledger.record("economics", "port", "boom", weight=20.0)
        # economics cascades to politics
        politics_bin = ledger.get_bin("politics", "port")
        assert politics_bin is not None
        assert politics_bin.total_weight >= 3.0

    def test_cascade_weight_is_positive_three(self):
        ledger = MomentumLedger()
        events = ledger.record("politics", "capital", "coup", weight=20.0)
        tipping = next(e for e in events if e["level"] == 20.0)
        assert tipping["cascade"]["weight"] == pytest.approx(3.0)

    def test_below_tipping_point_has_no_cascade(self):
        ledger = MomentumLedger()
        events = ledger.record("security", "ward", "patrol", weight=12.0)
        for ev in events:
            assert "cascade" not in ev, (
                f"Events below tipping_point must not have 'cascade' key: {ev}"
            )


# ---------------------------------------------------------------------------
# 3. Negative thresholds
# ---------------------------------------------------------------------------

class TestNegativeThresholds:
    def test_negative_weight_crosses_negative_threshold(self):
        ledger = MomentumLedger()
        events = ledger.record("security", "slums", "death", weight=-3.0)
        assert len(events) == 1
        assert events[0]["level"] == 3.0
        assert events[0]["total_weight"] == pytest.approx(-3.0)

    def test_negative_event_carries_negative_total_weight(self):
        """Threshold events triggered by negative accumulation must report
        a negative total_weight so callers can distinguish polarity."""
        ledger = MomentumLedger()
        events = ledger.record("economics", "market", "crash", weight=-5.0)
        neg_events = [e for e in events if e["total_weight"] < 0]
        assert len(neg_events) >= 1

    def test_positive_threshold_not_crossed_by_negative_weight(self):
        """Negative accumulation must not trigger positive threshold history."""
        ledger = MomentumLedger()
        ledger.record("security", "ward", "disaster", weight=-10.0)
        b = ledger.get_bin("security", "ward")
        assert b.last_threshold_fired == 0.0

    def test_negative_tipping_point_cascades_with_negative_weight(self):
        ledger = MomentumLedger()
        ledger.record("security", "ward", "collapse", weight=-20.0)
        # economics is the cascade target for security
        econ_bin = ledger.get_bin("economics", "ward")
        assert econ_bin is not None
        assert econ_bin.total_weight < 0, "Negative cascade must inject negative weight"

    def test_both_positive_and_negative_weights_tracked(self):
        """A bin that goes positive then negative tracks the net total.

        Starting weight 0, record +4 => total = +4.0.
        Then record -10 => total = -6.0.
        """
        ledger = MomentumLedger()
        ledger.record("social", "district", "rally", weight=4.0)
        b = ledger.get_bin("social", "district")
        assert b.total_weight == pytest.approx(4.0)

        ledger.record("social", "district", "riot", weight=-10.0)
        assert b.total_weight == pytest.approx(-6.0)
        assert b.entry_count == 2
        # Positive threshold history must remain unchanged
        assert b.last_threshold_fired >= 3.0


# ---------------------------------------------------------------------------
# 4. No double-fire on same threshold
# ---------------------------------------------------------------------------

class TestNoDoubleFire:
    def test_same_positive_threshold_fires_only_once(self):
        ledger = MomentumLedger()
        events = []
        for _ in range(6):
            events.extend(ledger.record("geography", "frontier", "scout", weight=1.0))
        minor_events = [e for e in events if e["level"] == 3.0]
        assert len(minor_events) == 1, (
            f"minor_shift threshold should fire exactly once, got {len(minor_events)}"
        )

    def test_same_negative_threshold_fires_only_once(self):
        ledger = MomentumLedger()
        events = []
        for _ in range(6):
            events.extend(ledger.record("security", "slums", "funeral", weight=-1.0))
        minor_neg = [e for e in events if e["level"] == 3.0 and e["total_weight"] < 0]
        assert len(minor_neg) == 1, (
            f"Negative minor_shift should fire exactly once, got {len(minor_neg)}"
        )

    def test_each_threshold_level_fires_at_most_once(self):
        ledger = MomentumLedger()
        events = []
        for _ in range(25):
            events.extend(ledger.record("economics", "port", "trade", weight=1.0))
        for level in (3.0, 7.0, 12.0, 20.0):
            matching = [e for e in events if e["level"] == level and e["total_weight"] > 0]
            assert len(matching) <= 1, (
                f"Threshold {level} fired {len(matching)} times; expected at most 1"
            )

    def test_last_threshold_fired_advances_monotonically(self):
        """last_threshold_fired should never decrease."""
        ledger = MomentumLedger()
        b = None
        for i in range(15):
            ledger.record("religion", "temple", "prayer", weight=1.0)
            b = ledger.get_bin("religion", "temple")
            # last_threshold_fired only ever increases
        assert b is not None
        assert b.last_threshold_fired >= 12.0


# ---------------------------------------------------------------------------
# 5. Serialization round-trip
# ---------------------------------------------------------------------------

class TestSerializationRoundTrip:
    def test_empty_ledger_round_trips(self):
        ledger = MomentumLedger(universe_id="")
        data = ledger.to_dict()
        restored = MomentumLedger.from_dict(data)
        assert restored.universe_id == ""
        assert restored.get_all_trends() == []

    def test_universe_id_survives_round_trip(self):
        ledger = MomentumLedger(universe_id="realm_of_ash")
        data = ledger.to_dict()
        restored = MomentumLedger.from_dict(data)
        assert restored.universe_id == "realm_of_ash"

    def test_bin_weight_and_count_survive_round_trip(self):
        ledger = MomentumLedger()
        ledger.record("politics", "senate", "election", weight=2.5)
        ledger.record("politics", "senate", "lobbying", weight=1.0)
        data = ledger.to_dict()
        restored = MomentumLedger.from_dict(data)
        b = restored.get_bin("politics", "senate")
        assert b is not None
        assert b.total_weight == pytest.approx(3.5)
        assert b.entry_count == 2

    def test_threshold_history_survives_round_trip(self):
        """last_threshold_fired must be preserved so thresholds don't re-fire
        after a load."""
        ledger = MomentumLedger()
        ledger.record("security", "walls", "defend", weight=5.0)
        data = ledger.to_dict()
        restored = MomentumLedger.from_dict(data)
        b = restored.get_bin("security", "walls")
        assert b.last_threshold_fired >= 3.0

        # Incrementing should NOT re-fire the already-passed threshold
        events = restored.record("security", "walls", "defend", weight=0.5)
        minor = [e for e in events if e["level"] == 3.0]
        assert minor == [], "minor_shift must not re-fire after load"

    def test_negative_threshold_history_survives_round_trip(self):
        ledger = MomentumLedger()
        ledger.record("economics", "docks", "embargo", weight=-5.0)
        data = ledger.to_dict()
        restored = MomentumLedger.from_dict(data)
        b = restored.get_bin("economics", "docks")
        assert b.last_neg_threshold_fired >= 3.0

    def test_entries_cap_at_twenty_in_serialized_form(self):
        """MomentumBin.to_dict() caps stored entries at 20."""
        ledger = MomentumLedger()
        for i in range(30):
            ledger.record("geography", "wilds", "scout", weight=0.1, turn=i)
        data = ledger.to_dict()
        bin_key = "geography|wilds"
        assert bin_key in data["bins"]
        assert len(data["bins"][bin_key]["entries"]) <= 20


# ---------------------------------------------------------------------------
# 6. Empty state defaults
# ---------------------------------------------------------------------------

class TestEmptyStateDefaults:
    def test_new_ledger_has_no_bins(self):
        ledger = MomentumLedger()
        assert ledger.get_all_trends() == []

    def test_get_bin_returns_none_for_unknown_key(self):
        ledger = MomentumLedger()
        assert ledger.get_bin("security", "nowhere") is None

    def test_get_dominant_trend_returns_none_for_empty_ledger(self):
        ledger = MomentumLedger()
        assert ledger.get_dominant_trend("anywhere") is None

    def test_decay_on_empty_ledger_returns_zero(self):
        ledger = MomentumLedger()
        assert ledger.decay(current_turn=999) == 0

    def test_from_dict_with_empty_dict_produces_defaults(self):
        ledger = MomentumLedger.from_dict({})
        assert ledger.universe_id == ""
        assert ledger.get_all_trends() == []

    def test_new_bin_starts_at_zero_weight(self):
        ledger = MomentumLedger()
        ledger.record("social", "plaza", "gather", weight=0.0)
        b = ledger.get_bin("social", "plaza")
        assert b is not None
        assert b.total_weight == pytest.approx(0.0)
        assert b.last_threshold_fired == 0.0
        assert b.last_neg_threshold_fired == 0.0

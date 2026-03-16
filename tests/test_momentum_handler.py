"""Tests for WO-V62.0 Track C — Momentum Threshold Handler."""
import pytest
from codex.core.services.momentum_handler import (
    MomentumThresholdHandler,
    TREND_MUTATIONS,
    NEGATIVE_EVENTS,
    _trend_to_grapes_modifier,
)
from codex.core.services.momentum import (
    MomentumLedger,
    MomentumBin,
    ACTION_CATEGORY_MAP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(level: float, category: str = "security", location: str = "docks",
                total_weight: float = None, entry_count: int = 5,
                cascade: dict = None) -> dict:
    """Build a synthetic threshold event for handler tests."""
    if total_weight is None:
        total_weight = level + 1.0  # Just above the threshold
    from codex.core.services.momentum import MomentumLedger
    name = MomentumLedger.THRESHOLD_NAMES.get(level, "unknown")
    event = {
        "level": level,
        "name": name,
        "category": category,
        "location": location,
        "total_weight": total_weight,
        "entry_count": entry_count,
    }
    if cascade is not None:
        event["cascade"] = cascade
    return event


# ---------------------------------------------------------------------------
# _trend_to_grapes_modifier
# ---------------------------------------------------------------------------

class TestTrendToGrapesModifier:
    def test_positive_security(self):
        result = _trend_to_grapes_modifier("security", 5.0)
        assert result is not None
        assert result["grapes_category"] == "social"
        # Narrative should reference safety / guards
        assert "safer" in result["narrative"].lower() or "walk" in result["narrative"].lower()

    def test_negative_security(self):
        result = _trend_to_grapes_modifier("security", -5.0)
        assert result is not None
        # Narrative should reference fear / danger
        assert "fear" in result["narrative"].lower() or "sundown" in result["narrative"].lower()

    def test_all_categories_have_positive_result(self):
        for cat in ("security", "economics", "politics", "religion", "geography", "social"):
            result = _trend_to_grapes_modifier(cat, 1.0)
            assert result is not None, f"Missing positive modifier for {cat}"
            assert "grapes_category" in result
            assert "field" in result
            assert "value" in result
            assert "narrative" in result

    def test_all_categories_have_negative_result(self):
        for cat in ("security", "economics", "politics", "religion", "geography", "social"):
            result = _trend_to_grapes_modifier(cat, -1.0)
            assert result is not None, f"Missing negative modifier for {cat}"
            assert "grapes_category" in result
            assert "field" in result
            assert "value" in result
            assert "narrative" in result

    def test_positive_and_negative_differ(self):
        for cat in TREND_MUTATIONS:
            pos = _trend_to_grapes_modifier(cat, 1.0)
            neg = _trend_to_grapes_modifier(cat, -1.0)
            # At minimum the narratives should differ
            assert pos["narrative"] != neg["narrative"], (
                f"Positive and negative narratives for {cat} must differ"
            )

    def test_unknown_category_returns_none(self):
        assert _trend_to_grapes_modifier("nonexistent", 1.0) is None

    def test_zero_weight_treated_as_negative(self):
        # weight == 0 is not positive, so should return negative variant
        result = _trend_to_grapes_modifier("security", 0.0)
        assert result is not None
        neg = _trend_to_grapes_modifier("security", -1.0)
        assert result["narrative"] == neg["narrative"]


# ---------------------------------------------------------------------------
# MomentumThresholdHandler — basic handle() contract
# ---------------------------------------------------------------------------

class TestHandleBasics:
    def test_empty_list_returns_empty(self):
        handler = MomentumThresholdHandler()
        assert handler.handle([]) == []

    def test_returns_list_of_strings(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(3.0)]
        result = handler.handle(events)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_handler_graceful_with_all_none_deps(self):
        """Handler must not raise when all optional deps are None."""
        handler = MomentumThresholdHandler()
        events = [
            _make_event(3.0),
            _make_event(7.0),
            _make_event(12.0),
            _make_event(20.0, cascade={"category": "economics", "weight": -3.0}),
        ]
        result = handler.handle(events)  # Must not raise
        assert isinstance(result, list)

    def test_unknown_category_does_not_raise(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(7.0, category="unknown_cat")]
        result = handler.handle(events)  # Should not raise
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Minor shift (3.0)
# ---------------------------------------------------------------------------

class TestMinorShift:
    def test_generates_rumor_message(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(3.0, total_weight=3.5)]
        messages = handler.handle(events)
        assert len(messages) >= 1
        assert "Rumor" in messages[0]

    def test_negative_weight_produces_negative_narrative(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(3.0, total_weight=-4.0)]
        messages = handler.handle(events)
        assert len(messages) >= 1
        # Security negative narrative references fear or sundown
        combined = " ".join(messages).lower()
        assert "fear" in combined or "sundown" in combined or "forbidden" in combined

    def test_positive_weight_produces_positive_narrative(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(3.0, category="security", total_weight=3.5)]
        messages = handler.handle(events)
        combined = " ".join(messages).lower()
        assert "safer" in combined or "walk" in combined or "streets" in combined

    def test_crier_narrate_called_if_present(self):
        class MockCrier:
            called = False
            def narrate_trend_event(self, event):
                MockCrier.called = True
                return "A crier speaks of change."

        handler = MomentumThresholdHandler(crier=MockCrier())
        events = [_make_event(3.0)]
        messages = handler.handle(events)
        assert MockCrier.called
        assert any("A crier speaks of change." in m for m in messages)

    def test_crier_returning_none_falls_back(self):
        class SilentCrier:
            def narrate_trend_event(self, event):
                return None  # Signal: nothing to say

        handler = MomentumThresholdHandler(crier=SilentCrier())
        events = [_make_event(3.0)]
        messages = handler.handle(events)
        # Fallback to TREND_MUTATIONS narrative
        assert len(messages) >= 1


# ---------------------------------------------------------------------------
# Notable trend (7.0)
# ---------------------------------------------------------------------------

class TestNotableTrend:
    def _make_ledger_mock(self):
        class MockLedger:
            def __init__(self):
                self.mutated = False
                self.recorded = False
                self.last_mutate_args = {}
                self._grapes = {
                    "social": [{"prohibition": "old", "punishment": "old", "origin": "old"}],
                    "economics": [{"abundance": "old"}],
                    "politics": [{"agenda": "old"}],
                    "religion": [{"ritual": "old", "heresy": "old"}],
                    "geography": [{"feature": "old"}],
                }

            def mutate(self, category, index, field, value):
                self.mutated = True
                self.last_mutate_args = {
                    "category": category, "index": index,
                    "field": field, "value": value,
                }
                if category in self._grapes and index < len(self._grapes[category]):
                    self._grapes[category][index][field] = value

            def record_historical_event(self, **kwargs):
                self.recorded = True

        return MockLedger()

    def test_mutate_called_on_ledger(self):
        ledger = self._make_ledger_mock()
        handler = MomentumThresholdHandler(world_ledger=ledger)
        events = [_make_event(7.0, category="security", total_weight=8.0)]
        handler.handle(events)
        assert ledger.mutated

    def test_world_shifts_message_present(self):
        ledger = self._make_ledger_mock()
        handler = MomentumThresholdHandler(world_ledger=ledger)
        events = [_make_event(7.0, category="security", total_weight=8.0)]
        messages = handler.handle(events)
        assert any("world shifts" in m.lower() for m in messages)

    def test_crier_broadcast_at_7(self):
        class MockCrier:
            def narrate_trend_event(self, event):
                return "The town buzzes."

        handler = MomentumThresholdHandler(crier=MockCrier())
        events = [_make_event(7.0, total_weight=8.0)]
        messages = handler.handle(events)
        assert any("Town Crier" in m for m in messages)
        assert any("The town buzzes." in m for m in messages)

    def test_economics_category_mutation(self):
        ledger = self._make_ledger_mock()
        handler = MomentumThresholdHandler(world_ledger=ledger)
        events = [_make_event(7.0, category="economics", total_weight=8.0)]
        handler.handle(events)
        assert ledger.mutated
        assert ledger.last_mutate_args["category"] == "economics"

    def test_negative_weight_uses_negative_mutation(self):
        ledger = self._make_ledger_mock()
        handler = MomentumThresholdHandler(world_ledger=ledger)
        events = [_make_event(7.0, category="security", total_weight=-8.0)]
        handler.handle(events)
        assert ledger.mutated
        # Negative security -> prohibition about lost patrols
        assert "forbidden" in ledger.last_mutate_args.get("value", "").lower() or \
               "patrols" in ledger.last_mutate_args.get("value", "").lower()

    def test_ledger_key_error_does_not_raise(self):
        """mutate() raising KeyError must be swallowed gracefully."""
        class BrokenLedger:
            def mutate(self, **kwargs):
                raise KeyError("grapes_category not found")
            def record_historical_event(self, **kwargs):
                pass

        handler = MomentumThresholdHandler(world_ledger=BrokenLedger())
        events = [_make_event(7.0)]
        handler.handle(events)  # Must not propagate


# ---------------------------------------------------------------------------
# Major shift (12.0)
# ---------------------------------------------------------------------------

class TestMajorShift:
    def _make_engine_mock(self):
        class MockEngine:
            def __init__(self):
                self.shards = []

            def _add_shard(self, content: str, stype: str, source: str = ""):
                self.shards.append({"content": content, "type": stype, "source": source})

        return MockEngine()

    def _make_broadcast_mock(self):
        class MockBroadcast:
            def __init__(self):
                self.events = []

            def broadcast(self, event_type: str, data: dict):
                self.events.append({"event_type": event_type, "data": data})

        return MockBroadcast()

    def test_anchor_shard_emitted(self):
        engine = self._make_engine_mock()
        handler = MomentumThresholdHandler(engine=engine)
        events = [_make_event(12.0, category="security", location="docks",
                               total_weight=13.0, entry_count=15)]
        handler.handle(events)
        assert len(engine.shards) >= 1
        shard = engine.shards[0]
        assert shard["type"] == "ANCHOR"
        assert shard["source"] == "momentum"
        assert "security" in shard["content"]
        assert "docks" in shard["content"]

    def test_broadcast_fired(self):
        bm = self._make_broadcast_mock()
        handler = MomentumThresholdHandler(broadcast_manager=bm)
        events = [_make_event(12.0, category="economics", location="market",
                               total_weight=14.0, entry_count=20)]
        handler.handle(events)
        assert len(bm.events) >= 1
        ev = bm.events[0]
        assert ev["event_type"] == "HIGH_IMPACT_DECISION"
        assert ev["data"]["category"] == "economics"
        assert "momentum_economics_major" in ev["data"]["event_tag"]

    def test_anchor_shard_not_emitted_without_engine(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(12.0)]
        # Must not raise; no shard anywhere to check, just verify no exception
        handler.handle(events)

    def test_broadcast_not_emitted_without_broadcast_manager(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(12.0)]
        handler.handle(events)  # No exception

    def test_all_major_messages_present(self):
        """At 12.0, minor + notable + major effects should all fire."""
        engine = self._make_engine_mock()
        bm = self._make_broadcast_mock()

        class MockLedger:
            def mutate(self, **kwargs): pass
            def record_historical_event(self, **kwargs): pass

        handler = MomentumThresholdHandler(
            world_ledger=MockLedger(), engine=engine, broadcast_manager=bm
        )
        events = [_make_event(12.0, category="security", total_weight=13.0)]
        messages = handler.handle(events)
        # Rumor from 3.0 path, world shifts from 7.0 path, anchor shard
        assert any("Rumor" in m for m in messages)
        assert any("world shifts" in m.lower() for m in messages)
        assert len(engine.shards) >= 1
        assert len(bm.events) >= 1


# ---------------------------------------------------------------------------
# Tipping point (20.0)
# ---------------------------------------------------------------------------

class TestTippingPoint:
    def test_cascade_message_present(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(20.0, category="security", total_weight=21.0,
                               cascade={"category": "economics", "weight": -3.0})]
        messages = handler.handle(events)
        assert any("Cascade" in m for m in messages)
        assert any("economics" in m.lower() for m in messages)

    def test_no_cascade_key_does_not_raise(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(20.0, cascade=None)]
        messages = handler.handle(events)  # Must not raise
        assert isinstance(messages, list)

    def test_cascade_message_contains_secondary_category(self):
        handler = MomentumThresholdHandler()
        events = [_make_event(20.0, category="politics", total_weight=21.0,
                               cascade={"category": "social", "weight": 3.0})]
        messages = handler.handle(events)
        combined = " ".join(messages)
        assert "social" in combined.lower()

    def test_all_tiers_fire_at_20(self):
        """Tipping point should produce messages from all four tiers."""
        class MockLedger:
            def mutate(self, **kwargs): pass
            def record_historical_event(self, **kwargs): pass

        class MockEngine:
            def __init__(self): self.shards = []
            def _add_shard(self, c, t, source=""): self.shards.append(t)

        class MockBroadcast:
            def __init__(self): self.events = []
            def broadcast(self, et, data): self.events.append(et)

        handler = MomentumThresholdHandler(
            world_ledger=MockLedger(),
            engine=MockEngine(),
            broadcast_manager=MockBroadcast(),
        )
        events = [_make_event(20.0, category="security", total_weight=21.0,
                               cascade={"category": "economics", "weight": 3.0})]
        messages = handler.handle(events)
        assert any("Rumor" in m for m in messages)
        assert any("world shifts" in m.lower() for m in messages)
        assert any("Cascade" in m for m in messages)


# ---------------------------------------------------------------------------
# Negative threshold integration (MomentumLedger changes)
# ---------------------------------------------------------------------------

class TestNegativeThresholds:
    def test_negative_events_set_is_non_empty(self):
        """NEGATIVE_EVENTS frozenset should contain known negative-polarity events."""
        assert "party_death" in NEGATIVE_EVENTS
        assert "companion_fell" in NEGATIVE_EVENTS
        assert "near_death" in NEGATIVE_EVENTS

    def test_core_negative_events_have_negative_weights_in_map(self):
        """The events that are both negative-narrative AND carry negative ledger weight
        must be negative in ACTION_CATEGORY_MAP (subset of NEGATIVE_EVENTS)."""
        # doom_threshold maps to religion +1.5 (crossing a doom threshold strengthens
        # religious dread — positive religion weight by design). Only pure-negative
        # events that subtract from security are checked here.
        must_be_negative = {"party_death", "companion_fell", "near_death"}
        for event_type in must_be_negative:
            if event_type in ACTION_CATEGORY_MAP:
                _, weight = ACTION_CATEGORY_MAP[event_type]
                assert weight < 0, (
                    f"{event_type} should have a negative base weight in "
                    f"ACTION_CATEGORY_MAP, got {weight}"
                )

    def test_ledger_fires_negative_threshold_after_deaths(self):
        """Repeated party deaths must push the bin below -3.0 and fire a threshold."""
        ledger = MomentumLedger(universe_id="test_neg")
        # party_death has weight -1.0; need ≥ 4 to get abs value past 3.0
        all_events = []
        for i in range(5):
            result = ledger.record_from_event("party_death", "docks", turn=i)
            all_events.extend(result)
        assert len(all_events) >= 1, "Expected at least one negative threshold to fire"
        b = ledger.get_bin("security", "docks")
        assert b is not None
        assert b.total_weight < 0
        assert b.last_neg_threshold_fired >= 3.0

    def test_negative_threshold_event_has_negative_total_weight(self):
        """Threshold events fired by negative accumulation should carry negative total_weight."""
        ledger = MomentumLedger(universe_id="test_neg2")
        all_events = []
        for i in range(5):
            result = ledger.record_from_event("party_death", "docks", turn=i)
            all_events.extend(result)
        for event in all_events:
            assert event["total_weight"] < 0, (
                f"Threshold event from party_death accumulation should have "
                f"negative total_weight, got {event['total_weight']}"
            )

    def test_positive_events_produce_positive_weight(self):
        ledger = MomentumLedger(universe_id="test_pos")
        all_events = []
        for i in range(5):
            result = ledger.record_from_event("kill", "docks", turn=i)
            all_events.extend(result)
        b = ledger.get_bin("security", "docks")
        assert b is not None
        assert b.total_weight > 0

    def test_positive_threshold_not_fired_by_negative_accumulation(self):
        """Negative events should not cross positive thresholds."""
        ledger = MomentumLedger(universe_id="test_pn")
        all_events = []
        for i in range(10):
            result = ledger.record_from_event("party_death", "docks", turn=i)
            all_events.extend(result)
        b = ledger.get_bin("security", "docks")
        assert b.last_threshold_fired == 0.0, (
            "Positive threshold should not have fired from negative accumulation"
        )

    def test_negative_and_positive_thresholds_independent(self):
        """A bin can accumulate both positive and negative thresholds independently."""
        ledger = MomentumLedger(universe_id="test_both")
        # Push positive past 3.0
        for i in range(4):
            ledger.record("security", "ward", "kill", weight=1.0, turn=i)
        b = ledger.get_bin("security", "ward")
        assert b.last_threshold_fired >= 3.0

        # Now drive it negative
        for i in range(10):
            ledger.record("security", "ward", "party_death", weight=-1.0, turn=10 + i)
        b = ledger.get_bin("security", "ward")
        # total_weight is now 4 - 10 = -6
        assert b.total_weight < 0
        assert b.last_neg_threshold_fired >= 3.0

    def test_negative_threshold_does_not_re_fire(self):
        """Passing the same negative threshold multiple times fires it only once."""
        ledger = MomentumLedger(universe_id="test_refire")
        all_events = []
        for i in range(8):
            result = ledger.record("security", "ward", "companion_fell",
                                   weight=-1.0, turn=i)
            all_events.extend(result)
        # Only one minor_shift threshold event
        minor_events = [e for e in all_events if e["level"] == 3.0]
        assert len(minor_events) == 1, (
            f"Negative minor_shift should fire exactly once, got {len(minor_events)}"
        )

    def test_companion_fell_triggers_negative_threshold(self):
        """companion_fell has weight -1.5 per event; 3 events = -4.5, crosses -3.0."""
        ledger = MomentumLedger(universe_id="test_cf")
        all_events = []
        for i in range(3):
            result = ledger.record_from_event("companion_fell", "outskirts", turn=i)
            all_events.extend(result)
        assert len(all_events) >= 1
        b = ledger.get_bin("security", "outskirts")
        assert b.total_weight == pytest.approx(-4.5)
        assert b.last_neg_threshold_fired >= 3.0

    def test_negative_tipping_point_cascade_has_negative_weight(self):
        """Negative tipping point cascade event should carry negative weight."""
        ledger = MomentumLedger(universe_id="test_neg_tip")
        # Accumulate enough negatives to exceed -20.0
        for i in range(15):
            ledger.record("security", "ward", "companion_fell",
                          weight=-1.5, turn=i)
        b = ledger.get_bin("security", "ward")
        # -1.5 * 15 = -22.5; should have crossed -20.0
        assert b.last_neg_threshold_fired == 20.0
        # Check cascade bin exists for economics with negative weight
        econ_bin = ledger.get_bin("economics", "ward")
        assert econ_bin is not None
        assert econ_bin.total_weight < 0


# ---------------------------------------------------------------------------
# MomentumBin serialisation round-trip (regression for new field)
# ---------------------------------------------------------------------------

class TestMomentumBinSerialisation:
    def test_last_neg_threshold_fired_round_trips(self):
        b = MomentumBin(category="security", location="docks")
        b.last_neg_threshold_fired = 7.0
        d = b.to_dict()
        assert d["last_neg_threshold_fired"] == 7.0
        b2 = MomentumBin.from_dict(d)
        assert b2.last_neg_threshold_fired == 7.0

    def test_missing_field_defaults_to_zero(self):
        """Backwards compat: old saves without last_neg_threshold_fired should load fine."""
        data = {
            "category": "security",
            "location": "docks",
            "total_weight": -5.0,
            "entry_count": 5,
            "last_threshold_fired": 0.0,
            # last_neg_threshold_fired deliberately absent
            "last_entry_turn": 3,
            "entries": [],
        }
        b = MomentumBin.from_dict(data)
        assert b.last_neg_threshold_fired == 0.0

    def test_ledger_round_trip_preserves_neg_threshold(self):
        ledger = MomentumLedger(universe_id="serial_test")
        for i in range(5):
            ledger.record("security", "docks", "party_death", weight=-1.0, turn=i)
        d = ledger.to_dict()
        ledger2 = MomentumLedger.from_dict(d)
        b = ledger2.get_bin("security", "docks")
        assert b is not None
        assert b.last_neg_threshold_fired >= 3.0


# ---------------------------------------------------------------------------
# TREND_MUTATIONS coverage
# ---------------------------------------------------------------------------

class TestTrendMutationsCoverage:
    def test_all_action_map_categories_have_mutations(self):
        """Every GRAPES category that appears in ACTION_CATEGORY_MAP must
        have a corresponding entry in TREND_MUTATIONS."""
        categories = {cat for _, (cat, _) in ACTION_CATEGORY_MAP.items()}
        for cat in categories:
            assert cat in TREND_MUTATIONS, (
                f"Category '{cat}' appears in ACTION_CATEGORY_MAP but is "
                f"missing from TREND_MUTATIONS"
            )

    def test_each_mutation_has_required_keys(self):
        required_keys = {
            "grapes_category",
            "field_positive", "field_negative",
            "narrative_positive", "narrative_negative",
        }
        for cat, mapping in TREND_MUTATIONS.items():
            missing = required_keys - mapping.keys()
            assert not missing, f"TREND_MUTATIONS[{cat!r}] missing keys: {missing}"

    def test_field_entries_are_two_tuples(self):
        for cat, mapping in TREND_MUTATIONS.items():
            for key in ("field_positive", "field_negative"):
                entry = mapping[key]
                assert isinstance(entry, tuple) and len(entry) == 2, (
                    f"TREND_MUTATIONS[{cat!r}][{key!r}] must be a 2-tuple"
                )

    def test_narratives_are_non_empty_strings(self):
        for cat, mapping in TREND_MUTATIONS.items():
            for key in ("narrative_positive", "narrative_negative"):
                narr = mapping[key]
                assert isinstance(narr, str) and len(narr) > 0, (
                    f"TREND_MUTATIONS[{cat!r}][{key!r}] must be a non-empty string"
                )

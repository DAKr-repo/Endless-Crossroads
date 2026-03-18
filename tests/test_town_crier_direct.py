"""Direct tests for codex/core/services/town_crier.py.

Covers: CivicPulse advance triggers, repeatable events, category filtering,
cross-module events, serialization round-trip, empty state defaults, and
CrierVoice narration fallback path.  No external services required.
"""
import pytest
from codex.core.services.town_crier import (
    CivicCategory,
    CivicEvent,
    CivicPulse,
    CrierVoice,
    BURNWILLOW_CIVIC_EVENTS,
    BURNWILLOW_CRIER_TEMPLATES,
    EVENT_FACTION_CLOCK_TICK,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pulse_with_events(*events: CivicEvent, tick: int = 0) -> CivicPulse:
    """Return a fresh CivicPulse pre-loaded with the given events."""
    p = CivicPulse(current_tick=tick, events=list(events))
    return p


def _event(threshold: int, category: CivicCategory = CivicCategory.SECURITY,
           tag: str = "TEST_EVENT", repeatable: bool = False,
           repeat_interval: int = 0) -> CivicEvent:
    return CivicEvent(threshold, category, tag, repeatable, repeat_interval)


# ---------------------------------------------------------------------------
# 1. advance() fires at threshold
# ---------------------------------------------------------------------------

class TestAdvanceTriggerAtThreshold:
    def test_event_fires_exactly_at_threshold(self):
        pulse = _pulse_with_events(_event(3, tag="FIRE_AT_3"))
        triggered = pulse.advance(3)
        assert len(triggered) == 1
        assert triggered[0].event_tag == "FIRE_AT_3"

    def test_event_fires_when_advance_overshoots_threshold(self):
        """Advancing by more ticks than the threshold gap still triggers."""
        pulse = _pulse_with_events(_event(3, tag="FIRE_AT_3"))
        triggered = pulse.advance(10)
        assert any(e.event_tag == "FIRE_AT_3" for e in triggered)

    def test_event_does_not_fire_below_threshold(self):
        pulse = _pulse_with_events(_event(5, tag="NOT_YET"))
        triggered = pulse.advance(4)
        assert triggered == []

    def test_multiple_events_fire_in_same_advance(self):
        pulse = _pulse_with_events(
            _event(2, tag="A"),
            _event(3, tag="B"),
        )
        triggered = pulse.advance(3)
        tags = {e.event_tag for e in triggered}
        assert "A" in tags and "B" in tags

    def test_tick_accumulates_across_advances(self):
        pulse = _pulse_with_events(_event(5, tag="LATER"))
        pulse.advance(3)
        triggered = pulse.advance(2)
        assert any(e.event_tag == "LATER" for e in triggered)

    def test_event_does_not_refire_after_threshold_passed(self):
        pulse = _pulse_with_events(_event(2, tag="ONCE"))
        pulse.advance(2)
        triggered_again = pulse.advance(1)
        assert not any(e.event_tag == "ONCE" for e in triggered_again)


# ---------------------------------------------------------------------------
# 2. Repeatable events
# ---------------------------------------------------------------------------

class TestRepeatableEvents:
    def test_repeatable_event_fires_at_initial_threshold(self):
        pulse = _pulse_with_events(_event(5, tag="REP", repeatable=True, repeat_interval=3))
        triggered = pulse.advance(5)
        assert any(e.event_tag == "REP" for e in triggered)

    def test_repeatable_event_fires_again_after_interval(self):
        pulse = _pulse_with_events(_event(5, tag="REP", repeatable=True, repeat_interval=3))
        pulse.advance(5)            # fires initial threshold
        triggered = pulse.advance(3)  # fires repeat at tick 8
        assert any(e.event_tag == "REP" for e in triggered)

    def test_repeatable_event_does_not_fire_before_interval(self):
        pulse = _pulse_with_events(_event(5, tag="REP", repeatable=True, repeat_interval=5))
        pulse.advance(5)            # initial fire
        triggered = pulse.advance(3)  # only 3 ticks into the 5-tick interval
        assert not any(e.event_tag == "REP" for e in triggered)

    def test_non_repeatable_event_fires_once(self):
        pulse = _pulse_with_events(_event(2, tag="ONCE", repeatable=False))
        pulse.advance(2)
        triggered = pulse.advance(10)
        assert not any(e.event_tag == "ONCE" for e in triggered)


# ---------------------------------------------------------------------------
# 3. Category filtering
# ---------------------------------------------------------------------------

class TestCategoryFiltering:
    def test_get_active_by_category_returns_only_matching(self):
        pulse = _pulse_with_events(
            _event(1, CivicCategory.TRADE, "TRADE_EVT"),
            _event(2, CivicCategory.SECURITY, "SEC_EVT"),
        )
        pulse.advance(3)
        trade = pulse.get_active_by_category(CivicCategory.TRADE)
        assert len(trade) == 1
        assert trade[0]["event_tag"] == "TRADE_EVT"

    def test_get_active_by_category_empty_when_none_triggered(self):
        pulse = _pulse_with_events(_event(10, CivicCategory.MORALE, "FAR_MORALE"))
        pulse.advance(3)
        result = pulse.get_active_by_category(CivicCategory.MORALE)
        assert result == []

    def test_triggered_history_records_category_value(self):
        pulse = _pulse_with_events(_event(1, CivicCategory.INFRASTRUCTURE, "INFRA"))
        pulse.advance(1)
        assert pulse.triggered_history[0]["category"] == "infrastructure"


# ---------------------------------------------------------------------------
# 4. Cross-module events
# ---------------------------------------------------------------------------

class TestCrossModuleEvents:
    def test_boss_slain_advances_tick(self):
        pulse = _pulse_with_events(_event(1, tag="TICK_EVENT"))
        before = pulse.current_tick
        pulse.handle_cross_module({"event_type": "BOSS_SLAIN"})
        assert pulse.current_tick == before + 1

    def test_boss_slain_can_trigger_threshold_event(self):
        pulse = _pulse_with_events(_event(1, CivicCategory.SECURITY, "SECURITY_BOOST"))
        triggered = []
        # patch advance so we capture return value
        original_advance = pulse.advance
        result = []

        # Drive tick to 0, then BOSS_SLAIN should push to 1 and fire the event
        pulse.handle_cross_module({"event_type": "BOSS_SLAIN"})
        assert "SECURITY_BOOST" in [e["event_tag"] for e in pulse.triggered_history]

    def test_faction_clock_tick_records_bulletin(self):
        pulse = CivicPulse()
        pulse.handle_cross_module({
            "event_type": EVENT_FACTION_CLOCK_TICK,
            "faction_name": "The Iron Guild",
            "agenda": "Control the docks",
            "filled": 3,
            "segments": 6,
        })
        assert len(pulse.triggered_history) == 1
        entry = pulse.triggered_history[0]
        assert entry["event_tag"] == "FACTION_BULLETIN"
        assert entry["faction_name"] == "The Iron Guild"
        assert entry["agenda"] == "Control the docks"
        assert entry["filled"] == 3
        assert entry["segments"] == 6

    def test_unknown_cross_module_event_is_no_op(self):
        pulse = CivicPulse()
        before_tick = pulse.current_tick
        before_history = len(pulse.triggered_history)
        pulse.handle_cross_module({"event_type": "TOTALLY_UNKNOWN"})
        assert pulse.current_tick == before_tick
        assert len(pulse.triggered_history) == before_history


# ---------------------------------------------------------------------------
# 5. Serialization round-trip
# ---------------------------------------------------------------------------

class TestSerializationRoundTrip:
    def test_empty_pulse_round_trips(self):
        pulse = CivicPulse()
        data = pulse.to_dict()
        restored = CivicPulse.from_dict(data)
        assert restored.current_tick == 0
        assert restored.events == []
        assert restored.triggered_history == []

    def test_tick_and_history_survive_round_trip(self):
        pulse = _pulse_with_events(_event(2, CivicCategory.TRADE, "ROUND_TRIP"))
        pulse.advance(3)
        data = pulse.to_dict()
        restored = CivicPulse.from_dict(data)
        assert restored.current_tick == 3
        assert len(restored.triggered_history) == 1
        assert restored.triggered_history[0]["event_tag"] == "ROUND_TRIP"

    def test_events_survive_round_trip_with_all_fields(self):
        ev = CivicEvent(10, CivicCategory.RUMOR, "MY_TAG", repeatable=True, repeat_interval=5)
        pulse = CivicPulse(events=[ev])
        restored = CivicPulse.from_dict(pulse.to_dict())
        assert len(restored.events) == 1
        r = restored.events[0]
        assert r.threshold == 10
        assert r.category == CivicCategory.RUMOR
        assert r.event_tag == "MY_TAG"
        assert r.repeatable is True
        assert r.repeat_interval == 5

    def test_sub_location_and_universe_id_survive_round_trip(self):
        pulse = CivicPulse(sub_location="dock_ward", universe_id="universe_alpha")
        restored = CivicPulse.from_dict(pulse.to_dict())
        assert restored.sub_location == "dock_ward"
        assert restored.universe_id == "universe_alpha"

    def test_restored_pulse_continues_advancing(self):
        """A restored pulse should track further advances correctly."""
        pulse = _pulse_with_events(_event(5, tag="LATER"))
        pulse.advance(3)
        restored = CivicPulse.from_dict(pulse.to_dict())
        triggered = restored.advance(2)
        assert any(e.event_tag == "LATER" for e in triggered)


# ---------------------------------------------------------------------------
# 6. Empty state defaults
# ---------------------------------------------------------------------------

class TestEmptyStateDefaults:
    def test_default_civic_pulse_fields(self):
        pulse = CivicPulse()
        assert pulse.current_tick == 0
        assert pulse.events == []
        assert pulse.triggered_history == []
        assert pulse.sub_location == ""
        assert pulse.universe_id == ""

    def test_advance_with_no_events_returns_empty(self):
        pulse = CivicPulse()
        assert pulse.advance(100) == []

    def test_get_active_by_category_on_empty_pulse(self):
        pulse = CivicPulse()
        assert pulse.get_active_by_category(CivicCategory.TRADE) == []

    def test_from_dict_empty_dict_produces_defaults(self):
        pulse = CivicPulse.from_dict({})
        assert pulse.current_tick == 0
        assert pulse.events == []
        assert pulse.triggered_history == []


# ---------------------------------------------------------------------------
# 7. CrierVoice narration — fallback path (no Mimir)
# ---------------------------------------------------------------------------

class TestCrierVoiceNarration:
    def test_narrate_uses_registered_template(self):
        voice = CrierVoice()
        voice.register_templates("burnwillow", BURNWILLOW_CRIER_TEMPLATES)
        ev = CivicEvent(2, CivicCategory.TRADE, "SCRAP_MERCHANT")
        result = voice.narrate(ev, {})
        assert result in BURNWILLOW_CRIER_TEMPLATES["SCRAP_MERCHANT"]

    def test_narrate_falls_back_to_tag_label_when_no_template(self):
        voice = CrierVoice()
        ev = CivicEvent(1, CivicCategory.RUMOR, "UNKNOWN_TAG")
        result = voice.narrate(ev, {})
        # Should produce the generic "[CATEGORY] Tag Name" fallback
        assert "RUMOR" in result.upper()
        assert "Unknown Tag" in result

    def test_mimir_result_takes_priority_over_template(self):
        def fake_mimir(prompt, _):
            return "Mimir speaks of ancient things."

        voice = CrierVoice(mimir_fn=fake_mimir)
        voice.register_templates("test", {"MY_EVENT": ["Static fallback."]})
        ev = CivicEvent(1, CivicCategory.RUMOR, "MY_EVENT")
        result = voice.narrate(ev, {})
        assert result == "Mimir speaks of ancient things."

    def test_mimir_exception_falls_back_to_template(self):
        def broken_mimir(prompt, _):
            raise RuntimeError("Mimir is offline")

        voice = CrierVoice(mimir_fn=broken_mimir)
        voice.register_templates("test", {"MY_EVENT": ["Fallback text."]})
        ev = CivicEvent(1, CivicCategory.RUMOR, "MY_EVENT")
        result = voice.narrate(ev, {})
        assert result == "Fallback text."

    def test_burnwillow_events_have_templates_for_all_tags(self):
        """Every tag in BURNWILLOW_CIVIC_EVENTS has a matching template entry."""
        for ev in BURNWILLOW_CIVIC_EVENTS:
            assert ev.event_tag in BURNWILLOW_CRIER_TEMPLATES, (
                f"Missing template for civic event tag: {ev.event_tag}"
            )

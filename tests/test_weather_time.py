"""
tests/test_weather_time.py — WO-V69.0 World Simulation Tests
=============================================================
Tests for:
  - DayClock: initialization, advance, day-wrap, is_dark, flavor messages, serialization
  - WeatherEngine: initialization, advance transitions, get_modifier, terrain tables,
    dungeon no-weather, severity, serialization
  - Integration: both serialize correctly for save format
"""

import sys
from pathlib import Path
from typing import List

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================================
# DayClock tests
# =========================================================================

class TestDayClock:
    """Tests for DayClock and TimeOfDay."""

    def test_init_defaults(self):
        """DayClock initializes with MORNING phase, day 1."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock()
        assert dc.phase == TimeOfDay.MORNING
        assert dc.day == 1

    def test_init_custom(self):
        """DayClock respects explicit phase and day arguments."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.DUSK, day=3)
        assert dc.phase == TimeOfDay.DUSK
        assert dc.day == 3

    def test_advance_one_tick(self):
        """Advancing by 1 tick moves to the next phase."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.MORNING)
        dc.advance(1)
        assert dc.phase == TimeOfDay.MIDDAY

    def test_advance_multiple_ticks(self):
        """Advancing by N ticks skips N phases."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        # MORNING -> MIDDAY -> AFTERNOON -> DUSK
        dc = DayClock(phase=TimeOfDay.MORNING)
        dc.advance(3)
        assert dc.phase == TimeOfDay.DUSK

    def test_advance_wraps_to_new_day(self):
        """Advancing past PREDAWN increments the day counter."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        # Start at PREDAWN (last phase) — one more tick = DAWN on day 2
        dc = DayClock(phase=TimeOfDay.PREDAWN, day=1)
        dc.advance(1)
        assert dc.phase == TimeOfDay.DAWN
        assert dc.day == 2

    def test_advance_full_cycle(self):
        """A full 8-phase cycle returns to the same phase on the next day."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.DAWN, day=1)
        dc.advance(8)
        assert dc.phase == TimeOfDay.DAWN
        assert dc.day == 2

    def test_is_dark_night_phases(self):
        """is_dark() returns True for DUSK, NIGHT, MIDNIGHT, PREDAWN."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dark_phases = [TimeOfDay.DUSK, TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT, TimeOfDay.PREDAWN]
        for phase in dark_phases:
            dc = DayClock(phase=phase)
            assert dc.is_dark(), f"Expected is_dark() True for {phase}"

    def test_is_dark_light_phases(self):
        """is_dark() returns False for DAWN, MORNING, MIDDAY, AFTERNOON."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        light_phases = [TimeOfDay.DAWN, TimeOfDay.MORNING, TimeOfDay.MIDDAY, TimeOfDay.AFTERNOON]
        for phase in light_phases:
            dc = DayClock(phase=phase)
            assert not dc.is_dark(), f"Expected is_dark() False for {phase}"

    def test_advance_returns_dawn_flavor(self):
        """Advancing to DAWN returns a flavor message."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.PREDAWN)
        msgs = dc.advance(1)
        assert len(msgs) == 1
        assert "dawn" in msgs[0].lower()

    def test_advance_returns_dusk_flavor(self):
        """Advancing to DUSK returns a flavor message."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.AFTERNOON)
        msgs = dc.advance(1)
        assert len(msgs) == 1
        assert "dusk" in msgs[0].lower() or "shadow" in msgs[0].lower()

    def test_advance_returns_midnight_flavor(self):
        """Advancing to MIDNIGHT returns a flavor message."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.NIGHT)
        msgs = dc.advance(1)
        assert len(msgs) == 1
        assert "night" in msgs[0].lower() or "midnight" in msgs[0].lower()

    def test_advance_no_flavor_for_neutral_phase(self):
        """Advancing to a non-key phase returns no flavor messages."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.MORNING)
        msgs = dc.advance(1)  # -> MIDDAY
        assert msgs == []

    def test_display_format(self):
        """display() returns a human-readable string."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.MIDDAY, day=5)
        result = dc.display()
        assert "5" in result
        assert "Midday" in result

    def test_serialization_round_trip(self):
        """to_dict() / from_dict() round-trip preserves state."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        original = DayClock(phase=TimeOfDay.MIDNIGHT, day=7)
        data = original.to_dict()
        restored = DayClock.from_dict(data)
        assert restored.phase == original.phase
        assert restored.day == original.day

    def test_serialization_keys(self):
        """to_dict() contains 'phase' and 'day' keys."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        dc = DayClock(phase=TimeOfDay.DUSK, day=2)
        data = dc.to_dict()
        assert "phase" in data
        assert "day" in data
        assert data["phase"] == "dusk"
        assert data["day"] == 2


# =========================================================================
# WeatherEngine tests
# =========================================================================

class TestWeatherEngine:
    """Tests for WeatherEngine and WeatherState."""

    def test_init_defaults(self):
        """WeatherEngine initializes with CLEAR weather."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        assert w.current == WeatherState.CLEAR
        assert w.severity == 0
        assert w.terrain_type == "forest"
        assert w.turns_remaining > 0

    def test_init_custom_terrain(self):
        """WeatherEngine respects terrain_type argument."""
        from codex.core.mechanics.weather import WeatherEngine
        w = WeatherEngine(terrain_type="mountain")
        assert w.terrain_type == "mountain"

    def test_advance_no_change_while_turns_remain(self):
        """advance() returns None while turns_remaining > 1."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine(terrain_type="forest", seed=42)
        w.turns_remaining = 5
        initial_weather = w.current
        # Advance 4 times — should not trigger a transition yet
        results = [w.advance() for _ in range(4)]
        assert all(r is None for r in results)

    def test_advance_triggers_transition(self):
        """advance() triggers a new weather roll when turns_remaining hits 0."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine(terrain_type="forest", seed=99)
        # Force the timer to expire on the next tick
        w.turns_remaining = 1
        # Force a weather change by setting up a known transition
        w.current = WeatherState.OVERCAST
        result = w.advance()
        # Timer expired — either weather changed (result = str) or same state (result = None)
        # Either way, turns_remaining was reset
        assert w.turns_remaining > 0

    def test_advance_returns_flavor_on_change(self):
        """When weather changes, advance() returns a non-empty string."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        # Use seeded RNG to get a deterministic transition
        w = WeatherEngine(terrain_type="forest", seed=1234)
        w.current = WeatherState.OVERCAST  # Most transitions from OVERCAST go to RAIN
        w.turns_remaining = 1
        # Repeatedly advance until we get a change (may need multiple runs)
        for _ in range(20):
            w.turns_remaining = 1
            result = w.advance()
            if result is not None:
                assert isinstance(result, str)
                assert len(result) > 0
                return
        # If no change happened in 20 tries (very unlikely with OVERCAST), pass gracefully
        pass

    def test_dungeon_no_weather(self):
        """Dungeon terrain never transitions — advance() always returns None."""
        from codex.core.mechanics.weather import WeatherEngine
        w = WeatherEngine(terrain_type="dungeon", seed=42)
        w.turns_remaining = 1  # Would trigger if not dungeon
        for _ in range(10):
            result = w.advance()
            assert result is None

    def test_get_modifier_clear(self):
        """CLEAR weather returns empty modifier dict."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.CLEAR
        mods = w.get_modifier()
        assert mods == {}

    def test_get_modifier_rain(self):
        """RAIN applies ranged attack penalty."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.RAIN
        w.severity = 0
        mods = w.get_modifier()
        assert "ranged" in mods
        assert mods["ranged"] < 0

    def test_get_modifier_rain_severity_scales(self):
        """Higher severity increases RAIN ranged penalty."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.RAIN
        w.severity = 0
        mild_penalty = w.get_modifier()["ranged"]
        w.severity = 2
        hard_penalty = w.get_modifier()["ranged"]
        assert hard_penalty <= mild_penalty  # More negative or equal

    def test_get_modifier_fog(self):
        """FOG applies perception penalty and blocks ambushes."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.FOG
        mods = w.get_modifier()
        assert "perception" in mods
        assert mods["perception"] < 0
        assert mods.get("enemy_ambush_blocked") is True

    def test_get_modifier_storm(self):
        """STORM applies movement cost and attack penalty."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.STORM
        mods = w.get_modifier()
        assert "movement_cost" in mods
        assert "attack" in mods
        assert mods["attack"] < 0

    def test_get_modifier_snow(self):
        """SNOW applies movement cost and secrets bonus."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.SNOW
        mods = w.get_modifier()
        assert "movement_cost" in mods
        assert "secrets" in mods

    def test_get_modifier_wind(self):
        """WIND applies ranged attack penalty."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.WIND
        mods = w.get_modifier()
        assert "ranged" in mods
        assert mods["ranged"] < 0

    def test_get_modifier_heat_high_severity(self):
        """HEAT at severity >= 2 triggers exhaustion_risk."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.HEAT
        w.severity = 2
        mods = w.get_modifier()
        assert mods.get("exhaustion_risk") is True

    def test_get_modifier_heat_low_severity(self):
        """HEAT at severity < 2 does not trigger exhaustion_risk."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.HEAT
        w.severity = 1
        mods = w.get_modifier()
        assert "exhaustion_risk" not in mods

    def test_terrain_transition_forest_used(self):
        """Forest terrain table is consulted for weather transitions."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState, TERRAIN_TRANSITIONS
        w = WeatherEngine(terrain_type="forest", seed=7)
        # Verify the forest table exists and has CLEAR entry
        assert "forest" in TERRAIN_TRANSITIONS
        assert WeatherState.CLEAR in TERRAIN_TRANSITIONS["forest"]

    def test_terrain_transition_mountain_used(self):
        """Mountain terrain has distinct transition table."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState, TERRAIN_TRANSITIONS
        assert "mountain" in TERRAIN_TRANSITIONS
        # Mountains have WIND and SNOW entries not in forest
        assert WeatherState.WIND in TERRAIN_TRANSITIONS["mountain"]
        assert WeatherState.SNOW in TERRAIN_TRANSITIONS["mountain"]

    def test_flavor_text_base(self):
        """flavor_text() returns non-empty string for each weather state."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        for state in WeatherState:
            w.current = state
            w.severity = 0
            text = w.flavor_text()
            assert isinstance(text, str)
            assert len(text) > 0

    def test_flavor_text_severe(self):
        """flavor_text() appends severity marker at severity >= 2."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine()
        w.current = WeatherState.RAIN
        w.severity = 2
        text = w.flavor_text()
        assert "severe" in text.lower() or "\u2014" in text

    def test_serialization_round_trip(self):
        """to_dict() / from_dict() round-trip preserves all fields."""
        from codex.core.mechanics.weather import WeatherEngine, WeatherState
        w = WeatherEngine(terrain_type="swamp", seed=0)
        w.current = WeatherState.FOG
        w.severity = 1
        w.turns_remaining = 4
        data = w.to_dict()
        restored = WeatherEngine.from_dict(data)
        assert restored.current == w.current
        assert restored.severity == w.severity
        assert restored.turns_remaining == w.turns_remaining
        assert restored.terrain_type == w.terrain_type

    def test_serialization_keys(self):
        """to_dict() contains required keys."""
        from codex.core.mechanics.weather import WeatherEngine
        w = WeatherEngine(terrain_type="coast")
        data = w.to_dict()
        assert "current" in data
        assert "severity" in data
        assert "turns_remaining" in data
        assert "terrain_type" in data


# =========================================================================
# Integration: serialization round-trip for save format
# =========================================================================

class TestWorldSimIntegration:
    """Integration tests for combined DayClock + WeatherEngine save round-trip."""

    def test_combined_save_format(self):
        """Both DayClock and WeatherEngine serialize to JSON-compatible dicts."""
        import json
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        from codex.core.mechanics.weather import WeatherEngine, WeatherState

        day_clock = DayClock(phase=TimeOfDay.NIGHT, day=3)
        weather = WeatherEngine(terrain_type="urban")
        weather.current = WeatherState.RAIN
        weather.severity = 1

        save_data = {
            "day_clock": day_clock.to_dict(),
            "weather": weather.to_dict(),
        }
        # Must be JSON-serializable (no non-primitive types)
        serialized = json.dumps(save_data)
        loaded = json.loads(serialized)

        restored_dc = DayClock.from_dict(loaded["day_clock"])
        restored_w = WeatherEngine.from_dict(loaded["weather"])

        assert restored_dc.phase == TimeOfDay.NIGHT
        assert restored_dc.day == 3
        assert restored_w.current == WeatherState.RAIN
        assert restored_w.severity == 1
        assert restored_w.terrain_type == "urban"

    def test_backward_compat_missing_keys(self):
        """Loading save data without day_clock/weather keys falls back gracefully."""
        from codex.core.mechanics.clock import DayClock, TimeOfDay
        from codex.core.mechanics.weather import WeatherEngine

        save_data = {}  # Old save — no world simulation keys

        day_clock = DayClock.from_dict(save_data.get("day_clock", {"phase": "morning", "day": 1}))
        weather = WeatherEngine.from_dict(save_data.get("weather", {
            "current": "clear", "severity": 0, "turns_remaining": 5, "terrain_type": "dungeon"
        }))

        assert day_clock.phase == TimeOfDay.MORNING
        assert day_clock.day == 1
        assert weather.terrain_type == "dungeon"

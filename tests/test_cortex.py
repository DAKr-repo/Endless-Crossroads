"""
Cortex Thermal State Machine Tests
====================================

Covers:
  - TestStateTransitionsUp: OPTIMAL->FATIGUED (>65°C), FATIGUED->CRITICAL (>75°C)
  - TestHysteresisDown: CRITICAL->RECOVERY (<70°C), FATIGUED->OPTIMAL (<60°C),
                        RECOVERY->FATIGUED re-entry
  - TestRecoveryCooldown: 30s gate enforced; early promotion blocked; expiry works
  - TestClearanceEvaluation: Full clearance matrix (status x RAM conditions)
  - TestPainSignal: Message format at CRITICAL; absent below threshold
  - TestEdgeCases: Exact threshold boundary, temp bounce, RECOVERY re-entry to FATIGUED
  - TestSystemPromptModifier: Returns "" for OPTIMAL, advisory for FATIGUED,
                              critical string for CRITICAL and RECOVERY

All hardware I/O is mocked via unittest.mock.patch.object.
No real CPU temperature or psutil calls are made.
"""

import time
import sys
from pathlib import Path
from unittest.mock import patch, patch as _patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codex.core.cortex import Cortex, CortexConfig, ThermalStatus, MetabolicState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cortex(initial_status: ThermalStatus = ThermalStatus.OPTIMAL) -> Cortex:
    """Return a fresh Cortex whose internal status is pre-set."""
    c = Cortex()
    c._current_status = initial_status
    return c


def _thermal_status(cortex: Cortex, temp: float) -> ThermalStatus:
    """Drive the state machine with a single temperature reading and return the result."""
    status = cortex._calculate_thermal_status(temp)
    cortex._current_status = status
    return status


# ---------------------------------------------------------------------------
# 1. State Transitions — climbing up the severity ladder
# ---------------------------------------------------------------------------

class TestStateTransitionsUp:
    """Rising temperature drives OPTIMAL -> FATIGUED -> CRITICAL."""

    def test_optimal_to_fatigued_above_65(self):
        """Temp just above 65°C moves state from OPTIMAL to FATIGUED."""
        cortex = _make_cortex(ThermalStatus.OPTIMAL)
        result = _thermal_status(cortex, 65.1)
        assert result == ThermalStatus.FATIGUED

    def test_optimal_transitions_fatigued_at_exact_65(self):
        """Temp exactly 65°C meets the >= threshold — transitions to FATIGUED."""
        cortex = _make_cortex(ThermalStatus.OPTIMAL)
        result = _thermal_status(cortex, 65.0)
        assert result == ThermalStatus.FATIGUED

    def test_fatigued_to_critical_above_75(self):
        """Temp above 75°C immediately moves state to CRITICAL regardless of prior state."""
        cortex = _make_cortex(ThermalStatus.FATIGUED)
        result = _thermal_status(cortex, 75.1)
        assert result == ThermalStatus.CRITICAL

    def test_optimal_to_critical_directly(self):
        """A sudden spike from OPTIMAL straight past 75°C lands in CRITICAL."""
        cortex = _make_cortex(ThermalStatus.OPTIMAL)
        result = _thermal_status(cortex, 80.0)
        assert result == ThermalStatus.CRITICAL


# ---------------------------------------------------------------------------
# 2. Hysteresis — temperature must fall far enough to recover
# ---------------------------------------------------------------------------

class TestHysteresisDown:
    """Hysteresis prevents oscillation at threshold boundaries."""

    def test_critical_stays_critical_above_hysteresis(self):
        """CRITICAL does NOT exit until temp < 70°C (75 - 5 hysteresis)."""
        cortex = _make_cortex(ThermalStatus.CRITICAL)
        # 70.0°C is the exact boundary: must be strictly less than 70 to exit
        result = _thermal_status(cortex, 71.0)
        assert result == ThermalStatus.CRITICAL

    def test_critical_to_recovery_below_70(self):
        """CRITICAL exits to RECOVERY once temp drops below 70°C."""
        cortex = _make_cortex(ThermalStatus.CRITICAL)
        result = _thermal_status(cortex, 69.9)
        assert result == ThermalStatus.RECOVERY

    def test_fatigued_stays_fatigued_between_60_and_65(self):
        """FATIGUED does NOT return to OPTIMAL in the 60-65°C hysteresis band."""
        cortex = _make_cortex(ThermalStatus.FATIGUED)
        result = _thermal_status(cortex, 62.0)
        assert result == ThermalStatus.FATIGUED

    def test_fatigued_to_optimal_below_60(self):
        """FATIGUED exits to OPTIMAL only when temp drops below 60°C."""
        cortex = _make_cortex(ThermalStatus.FATIGUED)
        result = _thermal_status(cortex, 59.9)
        assert result == ThermalStatus.OPTIMAL

    def test_recovery_re_enters_fatigued_above_65(self):
        """While in RECOVERY, a spike above 65°C sends the state to FATIGUED."""
        cortex = _make_cortex(ThermalStatus.RECOVERY)
        cortex._recovery_start_time = time.time() - 10  # only 10s in recovery
        result = _thermal_status(cortex, 66.0)
        assert result == ThermalStatus.FATIGUED


# ---------------------------------------------------------------------------
# 3. Recovery Cooldown — 30-second gate
# ---------------------------------------------------------------------------

class TestRecoveryCooldown:
    """RECOVERY -> OPTIMAL requires both low temp AND 30s elapsed."""

    def test_recovery_blocked_before_30s(self):
        """Even with low temp, RECOVERY stays put if only 15s have elapsed."""
        cortex = _make_cortex(ThermalStatus.RECOVERY)
        cortex._recovery_start_time = time.time() - 15  # 15s elapsed
        result = _thermal_status(cortex, 55.0)
        assert result == ThermalStatus.RECOVERY

    def test_recovery_promoted_after_30s_at_low_temp(self):
        """RECOVERY -> OPTIMAL after 30s elapsed AND temp is below 60°C."""
        cortex = _make_cortex(ThermalStatus.RECOVERY)
        cortex._recovery_start_time = time.time() - 31  # 31s elapsed
        result = _thermal_status(cortex, 55.0)
        assert result == ThermalStatus.OPTIMAL

    def test_recovery_blocked_at_30s_but_temp_too_high(self):
        """30s have elapsed but temp is 62°C (above 60 hysteresis floor): stays RECOVERY."""
        cortex = _make_cortex(ThermalStatus.RECOVERY)
        cortex._recovery_start_time = time.time() - 31
        result = _thermal_status(cortex, 62.0)
        # 62°C is between 60 and 65: hysteresis band — stays RECOVERY
        assert result == ThermalStatus.RECOVERY

    def test_recovery_clears_start_time_on_promotion(self):
        """After RECOVERY -> OPTIMAL, _recovery_start_time is cleared to None."""
        cortex = _make_cortex(ThermalStatus.RECOVERY)
        cortex._recovery_start_time = time.time() - 31
        _thermal_status(cortex, 55.0)
        assert cortex._recovery_start_time is None


# ---------------------------------------------------------------------------
# 4. Clearance Evaluation
# ---------------------------------------------------------------------------

class TestClearanceEvaluation:
    """_evaluate_clearance gates Academy model access."""

    def test_optimal_good_ram_grants_clearance(self):
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.OPTIMAL, 50.0, 6.0) is True

    def test_fatigued_denies_clearance(self):
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.FATIGUED, 50.0, 6.0) is False

    def test_critical_denies_clearance(self):
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.CRITICAL, 50.0, 6.0) is False

    def test_recovery_denies_clearance(self):
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.RECOVERY, 50.0, 6.0) is False

    def test_optimal_but_ram_percent_too_high_denies(self):
        """90% RAM usage or above denies clearance even when thermally OPTIMAL."""
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.OPTIMAL, 90.0, 6.0) is False

    def test_optimal_but_ram_available_too_low_denies(self):
        """Less than 2 GB available RAM denies clearance even when thermally OPTIMAL."""
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.OPTIMAL, 50.0, 1.9) is False

    def test_optimal_ram_at_exact_boundary_denies(self):
        """Exactly 90% RAM usage is at the critical threshold — clearance denied."""
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.OPTIMAL, 90.0, 4.0) is False

    def test_optimal_available_ram_at_exact_minimum_grants(self):
        """Exactly 2.0 GB available at OPTIMAL with healthy percent grants clearance."""
        cortex = _make_cortex()
        assert cortex._evaluate_clearance(ThermalStatus.OPTIMAL, 50.0, 2.0) is True


# ---------------------------------------------------------------------------
# 5. Pain Signal Generation
# ---------------------------------------------------------------------------

class TestPainSignal:
    """_generate_pain_signal produces the correct formatted message."""

    def test_pain_signal_contains_temperature(self):
        """Pain signal embeds the formatted temperature in the message."""
        cortex = _make_cortex()
        msg = cortex._generate_pain_signal(78.4)
        assert "78.4" in msg

    def test_pain_signal_contains_critical_prefix(self):
        """Pain signal starts with the THERMAL CRITICAL header."""
        cortex = _make_cortex()
        msg = cortex._generate_pain_signal(80.0)
        assert msg.startswith("[THERMAL CRITICAL:")

    def test_pain_signal_not_present_in_optimal_state(self):
        """MetabolicState.pain_signal_active is False when thermally OPTIMAL."""
        cortex = _make_cortex()
        with patch.object(cortex, "_read_cpu_temperature", return_value=55.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
            state = cortex.read_metabolic_state()
        assert state.pain_signal_active is False
        assert state.pain_message is None

    def test_pain_signal_active_in_critical_state(self):
        """MetabolicState.pain_signal_active is True and message is set at CRITICAL."""
        cortex = _make_cortex()
        with patch.object(cortex, "_read_cpu_temperature", return_value=80.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
            state = cortex.read_metabolic_state()
        assert state.pain_signal_active is True
        assert state.pain_message is not None
        assert "80.0" in state.pain_message


# ---------------------------------------------------------------------------
# 6. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary conditions and non-linear temperature scenarios."""

    def test_exact_65_triggers_fatigued(self):
        """65.0°C meets the >= threshold for TEMP_OPTIMAL_MAX — transitions to FATIGUED."""
        cortex = _make_cortex(ThermalStatus.OPTIMAL)
        result = _thermal_status(cortex, 65.0)
        assert result == ThermalStatus.FATIGUED

    def test_exact_75_triggers_critical(self):
        """75.0°C meets TEMP_CRITICAL (>=) — state becomes CRITICAL."""
        cortex = _make_cortex(ThermalStatus.OPTIMAL)
        result = _thermal_status(cortex, 75.0)
        assert result == ThermalStatus.CRITICAL

    def test_temperature_bounce_stays_fatigued_in_band(self):
        """Rapid oscillation between 62°C and 64°C keeps the state FATIGUED (hysteresis band)."""
        cortex = _make_cortex(ThermalStatus.FATIGUED)
        result: ThermalStatus = ThermalStatus.FATIGUED
        for temp in [64.0, 62.0, 63.5, 61.0, 64.5]:
            result = _thermal_status(cortex, temp)
        # All readings are above 60°C hysteresis floor — should remain FATIGUED
        assert result == ThermalStatus.FATIGUED

    def test_read_metabolic_state_mocks_hardware(self):
        """read_metabolic_state() with mocked sensors returns a well-formed MetabolicState."""
        cortex = _make_cortex()
        with patch.object(cortex, "_read_cpu_temperature", return_value=55.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(60.0, 4.0)):
            state = cortex.read_metabolic_state()
        assert isinstance(state, MetabolicState)
        assert state.cpu_temp_celsius == 55.0
        assert state.ram_usage_percent == 60.0
        assert state.ram_available_gb == 4.0
        assert state.thermal_status == ThermalStatus.OPTIMAL
        assert state.metabolic_clearance is True


# ---------------------------------------------------------------------------
# 7. get_system_prompt_modifier
# ---------------------------------------------------------------------------

class TestSystemPromptModifier:
    """get_system_prompt_modifier returns context-appropriate instructions."""

    def test_optimal_returns_empty_string(self):
        """No modifier is injected when the system is OPTIMAL."""
        cortex = _make_cortex()
        with patch.object(cortex, "_read_cpu_temperature", return_value=55.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
            modifier = cortex.get_system_prompt_modifier()
        assert modifier == ""

    def test_fatigued_returns_advisory(self):
        """FATIGUED state injects a thermal advisory with conciseness instructions."""
        cortex = _make_cortex()
        with patch.object(cortex, "_read_cpu_temperature", return_value=68.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
            modifier = cortex.get_system_prompt_modifier()
        assert "THERMAL ADVISORY" in modifier
        assert len(modifier) > 0

    def test_critical_returns_critical_modifier(self):
        """CRITICAL state injects a maximum-brevity warning."""
        cortex = _make_cortex()
        with patch.object(cortex, "_read_cpu_temperature", return_value=80.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
            modifier = cortex.get_system_prompt_modifier()
        assert "THERMAL CRITICAL" in modifier
        assert "BREVITY" in modifier

    def test_recovery_returns_critical_modifier(self):
        """RECOVERY state also injects the critical-brevity modifier (same as CRITICAL)."""
        cortex = _make_cortex(ThermalStatus.RECOVERY)
        # Set recovery_start_time so state doesn't immediately promote back to OPTIMAL
        cortex._recovery_start_time = time.time() - 5
        with patch.object(cortex, "_read_cpu_temperature", return_value=64.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
            modifier = cortex.get_system_prompt_modifier()
        assert "THERMAL CRITICAL" in modifier

    def test_modifier_ends_with_double_newline_when_active(self):
        """Non-empty modifiers are terminated with double newline for prompt injection."""
        cortex = _make_cortex()
        with patch.object(cortex, "_read_cpu_temperature", return_value=68.0), \
             patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
            modifier = cortex.get_system_prompt_modifier()
        assert modifier.endswith("\n\n")

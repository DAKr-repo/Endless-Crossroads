"""
codex_cortex.py - The Body (Homeostasis Layer)

The Cortex monitors hardware vitals and enforces thermal safety.
It acts as the metabolic regulator, gating access to compute-intensive
models (Academy / Coder) based on current thermal state.

This module implements the "Digital Ectotherm" principle:
The organism must regulate its own heat to survive.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import psutil


# Persona JSON lives alongside the core services
_PERSONA_FILE = Path(__file__).resolve().parent / "services" / "mimir_persona.json"
_GM_PROFILES_FILE = Path(__file__).resolve().parent / "services" / "system_gm_profiles.json"


class ThermalStatus(Enum):
    """Thermal state of the organism."""
    OPTIMAL = "GREEN"      # Full capability - Academy model allowed
    FATIGUED = "YELLOW"    # Throttled - Qwen only
    CRITICAL = "RED"       # Emergency - Minimal output, pain signal
    RECOVERY = "COOLDOWN"  # Hysteresis state - waiting to return to GREEN


@dataclass
class MetabolicState:
    """Current metabolic readings of the organism."""
    cpu_temp_celsius: float
    ram_usage_percent: float
    ram_available_gb: float
    thermal_status: ThermalStatus
    metabolic_clearance: bool  # Can we use Academy model?
    timestamp: float = field(default_factory=time.time)

    # Pain signal - set when CRITICAL threshold crossed
    pain_signal_active: bool = False
    pain_message: Optional[str] = None


class CortexConfig:
    """Thermal thresholds and hysteresis parameters."""

    # Temperature thresholds (Celsius)
    TEMP_OPTIMAL_MAX = 65.0      # Above this: FATIGUED
    TEMP_CRITICAL = 75.0         # Above this: CRITICAL

    # Hysteresis - must drop this far below threshold to recover
    HYSTERESIS_DROP = 5.0        # Must be 5°C below threshold
    RECOVERY_COOLDOWN_SEC = 30   # Minimum seconds in RECOVERY before GREEN

    # RAM thresholds
    RAM_MIN_AVAILABLE_GB = 2.0   # Minimum free RAM for Academy model
    RAM_CRITICAL_PERCENT = 90.0  # Above this: deny heavy models

    # RAM pressure thresholds (WO-V31.0: Homeostatic Guard)
    RAM_DANGER_GB = 12           # GB used — DANGER: flush non-essential models
    RAM_WARNING_GB = 10          # GB used — WARNING: advisory

    # Polling interval
    POLL_INTERVAL_SEC = 2.0


class Cortex:
    """
    The Body - Thermal Homeostasis Controller.

    Monitors CPU temperature and RAM, enforces thermal safety limits,
    and provides metabolic clearance decisions for the Architect.
    """

    def __init__(self, config: Optional[CortexConfig] = None):
        self.config = config or CortexConfig()
        self._current_status = ThermalStatus.OPTIMAL
        self._recovery_start_time: Optional[float] = None
        self._last_critical_time: Optional[float] = None
        self._pain_signal_acknowledged = False
        # Active session state for GM profile injection
        self.active_system_id: Optional[str] = None
        self.active_dm_influence: Optional[dict] = None

    def _read_cpu_temperature(self) -> float:
        """
        Read CPU temperature from system sensors.

        Returns temperature in Celsius.
        Falls back to 50.0°C if sensors unavailable.
        """
        try:
            temps = psutil.sensors_temperatures()

            # Raspberry Pi reports under 'cpu_thermal'
            if 'cpu_thermal' in temps:
                return temps['cpu_thermal'][0].current

            # Fallback: check common sensor names
            for name in ['coretemp', 'k10temp', 'acpitz']:
                if name in temps and temps[name]:
                    return temps[name][0].current

            # No sensors found - return safe default
            return 50.0

        except Exception:
            # Sensor read failed - assume moderate temp
            return 50.0

    def _read_ram_stats(self) -> tuple[float, float]:
        """
        Read RAM usage statistics.

        Returns:
            (usage_percent, available_gb)
        """
        mem = psutil.virtual_memory()
        usage_percent = mem.percent
        available_gb = mem.available / (1024 ** 3)
        return usage_percent, available_gb

    def _calculate_thermal_status(self, temp: float) -> ThermalStatus:
        """
        Determine thermal status with hysteresis.

        State transitions:
        - OPTIMAL -> FATIGUED: temp > 65°C
        - FATIGUED -> CRITICAL: temp > 75°C
        - CRITICAL -> RECOVERY: temp < 70°C (75 - 5 hysteresis)
        - RECOVERY -> OPTIMAL: temp < 60°C AND 30s elapsed
        - FATIGUED -> OPTIMAL: temp < 60°C (65 - 5 hysteresis)
        """
        current = self._current_status
        now = time.time()

        # CRITICAL check - highest priority
        if temp >= self.config.TEMP_CRITICAL:
            self._recovery_start_time = None
            self._last_critical_time = now
            return ThermalStatus.CRITICAL

        # Coming down from CRITICAL
        if current == ThermalStatus.CRITICAL:
            if temp < (self.config.TEMP_CRITICAL - self.config.HYSTERESIS_DROP):
                self._recovery_start_time = now
                return ThermalStatus.RECOVERY
            return ThermalStatus.CRITICAL

        # In RECOVERY - waiting for cooldown period
        if current == ThermalStatus.RECOVERY:
            recovery_elapsed = now - (self._recovery_start_time or now)
            temp_threshold = self.config.TEMP_OPTIMAL_MAX - self.config.HYSTERESIS_DROP

            if temp < temp_threshold and recovery_elapsed >= self.config.RECOVERY_COOLDOWN_SEC:
                self._recovery_start_time = None
                return ThermalStatus.OPTIMAL
            elif temp >= self.config.TEMP_OPTIMAL_MAX:
                return ThermalStatus.FATIGUED
            return ThermalStatus.RECOVERY

        # FATIGUED check
        if temp >= self.config.TEMP_OPTIMAL_MAX:
            return ThermalStatus.FATIGUED

        # Coming down from FATIGUED
        if current == ThermalStatus.FATIGUED:
            if temp < (self.config.TEMP_OPTIMAL_MAX - self.config.HYSTERESIS_DROP):
                return ThermalStatus.OPTIMAL
            return ThermalStatus.FATIGUED

        return ThermalStatus.OPTIMAL

    def read_metabolic_state(self) -> MetabolicState:
        """
        Take a complete metabolic reading.

        This is the primary interface for other modules to query
        the organism's physical state.
        """
        temp = self._read_cpu_temperature()
        ram_percent, ram_available = self._read_ram_stats()

        # Calculate new thermal status with hysteresis
        new_status = self._calculate_thermal_status(temp)
        self._current_status = new_status

        # Determine metabolic clearance (can we use Academy model?)
        clearance = self._evaluate_clearance(new_status, ram_percent, ram_available)

        # Check for pain signal
        pain_active = False
        pain_msg = None
        if new_status == ThermalStatus.CRITICAL:
            pain_active = True
            pain_msg = self._generate_pain_signal(temp)

        return MetabolicState(
            cpu_temp_celsius=temp,
            ram_usage_percent=ram_percent,
            ram_available_gb=ram_available,
            thermal_status=new_status,
            metabolic_clearance=clearance,
            pain_signal_active=pain_active,
            pain_message=pain_msg
        )

    def _evaluate_clearance(
        self,
        status: ThermalStatus,
        ram_percent: float,
        ram_available: float
    ) -> bool:
        """
        Evaluate whether Academy model-R1 may be invoked.

        Clearance requires:
        1. Thermal status is OPTIMAL (GREEN)
        2. RAM usage below critical threshold
        3. Sufficient free RAM available
        """
        if status != ThermalStatus.OPTIMAL:
            return False

        if ram_percent >= self.config.RAM_CRITICAL_PERCENT:
            return False

        if ram_available < self.config.RAM_MIN_AVAILABLE_GB:
            return False

        return True

    def _generate_pain_signal(self, temp: float) -> str:
        """
        Generate the Pain Signal message for CRITICAL state.

        This message is injected into responses when the organism
        is in thermal distress.
        """
        return (
            f"[THERMAL CRITICAL: {temp:.1f}°C] "
            "System entering protective shutdown. "
            "Deep reasoning suspended. "
            "Responses will be minimal until temperature normalizes."
        )

    def check_metabolic_clearance(self) -> bool:
        """
        Quick check: Is Academy model-R1 authorized?

        This is the primary gate function called by the Architect
        before routing to Academy mode.

        Returns:
            True if Academy model may be invoked, False otherwise.
        """
        state = self.read_metabolic_state()
        return state.metabolic_clearance

    def check_ram_pressure(self) -> str:
        """Check RAM pressure level.

        Returns 'OK', 'WARNING', or 'DANGER' based on total RAM used.

        WO-V31.0: Homeostatic Guard — RAM pressure monitoring.
        """
        used_gb = psutil.virtual_memory().used / (1024 ** 3)
        if used_gb >= self.config.RAM_DANGER_GB:
            return "DANGER"
        elif used_gb >= self.config.RAM_WARNING_GB:
            return "WARNING"
        return "OK"

    def _flush_vram(self):
        """Force-unload non-essential models from memory.

        Unloads LiteRT-LM Gemma 4 engine. Mimir (Ollama) is retained.

        WO-V31.0: Homeostatic Guard — VRAM flush on RAM DANGER.
        """
        # Unload LiteRT-LM engine (frees ~350MB hard + ~1.2GB page cache)
        try:
            from codex.core.services.litert_engine import get_litert_engine
            engine = get_litert_engine()
            if engine.is_loaded:
                engine.unload()
        except Exception:
            pass  # Best-effort flush

    def get_system_prompt_modifier(self) -> str:
        """
        Get prompt modifier based on current thermal state.

        Returns instructions to prepend to system prompts that
        enforce appropriate verbosity for current conditions.
        """
        state = self.read_metabolic_state()

        if state.thermal_status == ThermalStatus.OPTIMAL:
            return ""  # No modification needed

        if state.thermal_status == ThermalStatus.FATIGUED:
            return (
                "[THERMAL ADVISORY: System running warm. "
                "Keep responses concise. Avoid lengthy explanations. "
                "Prioritize direct answers over elaboration.]\n\n"
            )

        if state.thermal_status in (ThermalStatus.CRITICAL, ThermalStatus.RECOVERY):
            return (
                "[THERMAL CRITICAL: System overheated. "
                "MAXIMUM BREVITY REQUIRED. "
                "One sentence responses only. "
                "No explanations. No elaboration. Direct answers only.]\n\n"
            )

        return ""

    def get_status_report(self) -> str:
        """
        Generate a human-readable status report.

        Useful for diagnostics and Discord status commands.
        """
        state = self.read_metabolic_state()

        status_emoji = {
            ThermalStatus.OPTIMAL: "🟢",
            ThermalStatus.FATIGUED: "🟡",
            ThermalStatus.CRITICAL: "🔴",
            ThermalStatus.RECOVERY: "🔵"
        }

        emoji = status_emoji.get(state.thermal_status, "⚪")

        report = [
            f"{emoji} Thermal Status: {state.thermal_status.value}",
            f"   CPU Temperature: {state.cpu_temp_celsius:.1f}°C",
            f"   RAM Usage: {state.ram_usage_percent:.1f}%",
            f"   RAM Available: {state.ram_available_gb:.2f} GB",
            f"   Model Clearance: {'GRANTED' if state.metabolic_clearance else 'DENIED'}"
        ]

        if state.pain_signal_active:
            report.append(f"   ⚠️ PAIN SIGNAL: {state.pain_message}")

        return "\n".join(report)

    def get_base_persona_prompt(self) -> str:
        """
        Returns Mimir's origin prompt from mimir_persona.json.
        Falls back to a minimal prompt if the file is unavailable.
        """
        try:
            if _PERSONA_FILE.exists():
                data = json.loads(_PERSONA_FILE.read_text())
                return data.get("origin_prompt", "")
        except Exception:
            pass

        # Fallback — keeps the system functional without the JSON
        return (
            "You are Mimir, Guardian of the Endless Crossroads. "
            "Your responses must always be accurate, brief, and non-redundant. "
            "Never misspell your name. Your name is Mimir."
        )

    def get_gm_profile_prompt(self, system_id: str) -> str:
        """Build a system-specific GM identity prompt from system_gm_profiles.json.

        Layers the GM title, narrative identity, principles, and key mechanics
        onto the base Mimir persona to create a grounded, system-aware narrator.

        Args:
            system_id: Engine system identifier (e.g. "candela", "bitd", "dnd5e").

        Returns:
            GM profile prompt string, or empty string if no profile found.
        """
        try:
            if not _GM_PROFILES_FILE.exists():
                return ""
            profiles = json.loads(_GM_PROFILES_FILE.read_text())
            profile = profiles.get(system_id, {})
            if not profile:
                return ""

            # Universal narration rules (spoiler filter, etc.)
            universal = profiles.get("_universal", {})
            narration_rules = universal.get("narration_rules", [])
            spoiler_filter = universal.get("spoiler_filter", "")

            gm_title = profile.get("gm_title", "Game Master")
            identity = profile.get("narrative_identity", "")
            principles = profile.get("gm_principles", [])
            moves = profile.get("making_moves", [])
            mechanics = profile.get("key_mechanics_to_narrate", [])
            combat = profile.get("combat_guidance", "")

            parts = []

            # Universal rules come first — they override everything
            if narration_rules:
                parts.append("[NARRATION RULES] " + " | ".join(narration_rules))
            if spoiler_filter:
                parts.append(f"[SPOILER FILTER] {spoiler_filter}")

            parts.append(f"\n[GM IDENTITY: {gm_title}] {identity}")

            if principles:
                parts.append("PRINCIPLES: " + " | ".join(principles[:5]))

            if moves:
                parts.append("MOVES: " + " | ".join(moves[:4]))

            if mechanics:
                parts.append("NARRATE: " + " | ".join(mechanics[:4]))

            if combat:
                parts.append(f"COMBAT: {combat}")

            return " ".join(parts)
        except Exception:
            return ""

    def get_dm_influence_prompt(self, dm_influence: Optional[dict] = None) -> str:
        """Build a DM influence prompt from session dials.

        Args:
            dm_influence: Dict with tone (0-1), ruthlessness (0-1),
                          narration_style, and custom_directives.

        Returns:
            DM influence prompt string, or empty string if no influence set.
        """
        if not dm_influence:
            return ""

        parts = []
        tone = dm_influence.get("tone", 0.5)
        ruth = dm_influence.get("ruthlessness", 0.5)
        style = dm_influence.get("narration_style", "balanced")
        directives = dm_influence.get("custom_directives", [])

        # Map tone to descriptive guidance
        if tone < 0.25:
            parts.append("[TONE: Grimdark — emphasize despair, corruption, and moral decay.]")
        elif tone < 0.45:
            parts.append("[TONE: Grim — the world is dangerous and hope is scarce.]")
        elif tone < 0.55:
            parts.append("[TONE: Balanced — mix danger with moments of warmth and humor.]")
        elif tone < 0.75:
            parts.append("[TONE: Heroic — the protagonists can make a real difference.]")
        else:
            parts.append("[TONE: Whimsical — lighter, more adventurous, wonder over dread.]")

        # Map ruthlessness
        if ruth < 0.3:
            parts.append("[CONSEQUENCES: Lenient — soften failures, give second chances.]")
        elif ruth < 0.6:
            parts.append("[CONSEQUENCES: Fair — consequences match the risk taken.]")
        elif ruth < 0.8:
            parts.append("[CONSEQUENCES: Harsh — failures hurt. Resources are scarce.]")
        else:
            parts.append("[CONSEQUENCES: Merciless — every mistake has lasting cost.]")

        # Narration style
        if style == "terse":
            parts.append("[STYLE: Terse — short, punchy sentences. Minimal description.]")
        elif style == "descriptive":
            parts.append("[STYLE: Descriptive — rich sensory detail, atmospheric prose.]")

        # Custom directives
        if directives:
            parts.append("[DM DIRECTIVES: " + "; ".join(directives) + "]")

        return " ".join(parts)


# Singleton instance for cross-module access
_cortex_instance: Optional[Cortex] = None


def get_cortex() -> Cortex:
    """Get or create the singleton Cortex instance."""
    global _cortex_instance
    if _cortex_instance is None:
        _cortex_instance = Cortex()
    return _cortex_instance


async def cortex_monitor_loop(callback=None, interval: float = 2.0):
    """
    Async monitoring loop for continuous thermal observation.

    Includes RAM pressure check (WO-V31.0): flushes non-essential
    models from Ollama VRAM when RAM usage reaches DANGER threshold.

    Args:
        callback: Optional async function called with MetabolicState on each reading
        interval: Seconds between readings
    """
    cortex = get_cortex()

    while True:
        state = cortex.read_metabolic_state()

        # WO-V31.0: Homeostatic Guard — RAM pressure check
        ram_pressure = cortex.check_ram_pressure()
        if ram_pressure == "DANGER":
            cortex._flush_vram()

        if callback:
            await callback(state)

        await asyncio.sleep(interval)


# Direct access function for Architect
def check_metabolic_clearance() -> bool:
    """
    Module-level convenience function.

    Returns True if Academy model-R1 may be invoked.
    """
    return get_cortex().check_metabolic_clearance()


if __name__ == "__main__":
    # Self-test: Print current status
    cortex = Cortex()
    print("C.O.D.E.X. Cortex - Metabolic Status Check")
    print("=" * 45)
    print(cortex.get_status_report())
    print()

    state = cortex.read_metabolic_state()
    print(f"Metabolic Clearance for Academy model: {state.metabolic_clearance}")

    if modifier := cortex.get_system_prompt_modifier():
        print(f"\nSystem Prompt Modifier Active:\n{modifier}")

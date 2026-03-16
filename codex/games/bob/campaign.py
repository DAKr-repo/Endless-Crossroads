"""
codex.games.bob.campaign
==========================
Campaign phase subsystem for Band of Blades.

Manages the march / camp / mission cycle, Legion morale and supply,
Pressure Clock advancement, and the narrative shape of the retreat.

Classes:
    PressureClock       — Tracks the Cinder King's advance (0-5 levels).
    CampaignPhaseManager — Manages the march / camp / mission cycle.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================================
# PRESSURE CLOCK
# =========================================================================

# Description text for each pressure level
_PRESSURE_LABELS = {
    0: "Quiet",
    1: "Distant Thunder",
    2: "Closing In",
    3: "Under Siege",
    4: "Desperate Hours",
    5: "Last Stand",
}

# Maximum ticks at each level before advancing to the next
_TICKS_PER_LEVEL = 3


class PressureClock:
    """Tracks the Cinder King's advance toward the Legion.

    Pressure is represented as a level (0-5) with ticks within each level.
    Accumulating ``_TICKS_PER_LEVEL`` ticks advances to the next level.
    Reaching level 5 triggers the campaign's final phase.
    """

    def __init__(self, level: int = 0, ticks: int = 0):
        """Initialise the Pressure Clock.

        Args:
            level: Starting pressure level (0-5, default 0).
            ticks: Starting ticks within the current level (default 0).
        """
        self.level: int = max(0, min(5, level))
        self.ticks: int = max(0, ticks)

    @property
    def label(self) -> str:
        """Human-readable name for the current pressure level."""
        return _PRESSURE_LABELS.get(self.level, "Unknown")

    @property
    def is_final(self) -> bool:
        """Return True when pressure has reached the campaign's last stand."""
        return self.level >= 5

    def tick(self, amount: int = 1) -> Dict[str, Any]:
        """Advance the Pressure Clock by *amount* ticks.

        When ticks fill a level, pressure advances. Returns a result dict
        describing what happened.

        Args:
            amount: Number of ticks to add (default 1).

        Returns:
            Dict with keys: old_level, new_level, old_ticks, new_ticks,
            level_advanced (bool), is_final (bool), label.
        """
        old_level = self.level
        old_ticks = self.ticks

        self.ticks += amount

        levels_advanced = 0
        while self.ticks >= _TICKS_PER_LEVEL and self.level < 5:
            self.ticks -= _TICKS_PER_LEVEL
            self.level += 1
            levels_advanced += 1

        # Cap at max level
        if self.level >= 5:
            self.level = 5
            self.ticks = 0

        return {
            "old_level": old_level,
            "new_level": self.level,
            "old_ticks": old_ticks,
            "new_ticks": self.ticks,
            "level_advanced": levels_advanced > 0,
            "levels_advanced": levels_advanced,
            "is_final": self.is_final,
            "label": self.label,
        }

    def reduce(self, amount: int = 1) -> Dict[str, Any]:
        """Reduce pressure by *amount* ticks (Legion victory).

        Args:
            amount: Number of ticks to remove (default 1).

        Returns:
            Dict describing the change.
        """
        old_level = self.level
        old_ticks = self.ticks

        self.ticks -= amount
        while self.ticks < 0 and self.level > 0:
            self.level -= 1
            self.ticks += _TICKS_PER_LEVEL
        self.ticks = max(0, self.ticks)

        return {
            "old_level": old_level,
            "new_level": self.level,
            "old_ticks": old_ticks,
            "new_ticks": self.ticks,
            "label": self.label,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for save/load."""
        return {"level": self.level, "ticks": self.ticks}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PressureClock":
        """Deserialize from a plain dict."""
        return cls(level=data.get("level", 0), ticks=data.get("ticks", 0))

    def __repr__(self) -> str:
        return (
            f"PressureClock(level={self.level}/{5}, "
            f"ticks={self.ticks}/{_TICKS_PER_LEVEL}, label='{self.label}')"
        )


# =========================================================================
# CAMP ACTIVITIES
# =========================================================================

CAMP_ACTIVITIES = {
    "rest": {
        "description": "Troops rest and recover. Morale improves.",
        "morale_delta": +1,
        "supply_cost": 0,
    },
    "resupply": {
        "description": "Scavenge or trade for supplies.",
        "morale_delta": 0,
        "supply_cost": 0,  # Resupply adds supply, handled separately
    },
    "recruit": {
        "description": "Recruit new soldiers to replace losses.",
        "morale_delta": 0,
        "supply_cost": 2,
    },
    "ceremony": {
        "description": "Hold a religious ceremony. Morale improves significantly.",
        "morale_delta": +2,
        "supply_cost": 1,
    },
    "train": {
        "description": "Run drills and training exercises.",
        "morale_delta": 0,
        "supply_cost": 0,
    },
    "intel_review": {
        "description": "Review gathered intelligence and plan ahead.",
        "morale_delta": 0,
        "supply_cost": 0,
    },
}

# Morale descriptions per level (1-5 scale)
MORALE_DESCRIPTIONS = {
    1: "Broken — the Legion is close to dissolution.",
    2: "Low — soldiers are demoralized and questioning.",
    3: "Steady — holding together under difficult circumstances.",
    4: "Good — soldiers are committed and confident.",
    5: "Excellent — the Legion fights with purpose and fire.",
}

# Encounter chance during a march (0.0-1.0)
MARCH_ENCOUNTER_CHANCE = 0.30


# =========================================================================
# CAMPAIGN PHASE MANAGER
# =========================================================================

class CampaignPhaseManager:
    """Manages the Legion's march / camp / mission cycle.

    Tracks resource levels (morale, supply), the campaign timeline,
    holy relics acquired, and the route taken during the retreat.

    The phase cycle is:  march -> camp -> mission -> march -> ...

    Args:
        current_phase: Starting phase (default "march").
        time_passed: Days elapsed since Ettenmark Fields (default 0).
        morale: Legion morale on a 1-5 scale (default 3).
        supply: Legion supply on a 0-10 scale (default 5).
        pressure: Starting pressure level (default 0).
    """

    PHASE_CYCLE: List[str] = ["march", "camp", "mission"]

    def __init__(
        self,
        current_phase: str = "march",
        time_passed: int = 0,
        morale: int = 3,
        supply: int = 5,
        pressure: int = 0,
        holy_relics: Optional[List[str]] = None,
        route: Optional[List[str]] = None,
    ):
        self.current_phase: str = current_phase
        self.time_passed: int = time_passed
        self.morale: int = max(1, min(5, morale))
        self.supply: int = max(0, min(10, supply))
        self.pressure_clock: PressureClock = PressureClock(level=pressure)
        self.holy_relics: List[str] = holy_relics or []
        self.route: List[str] = route or []

    @property
    def pressure(self) -> int:
        """Current pressure level (0-5)."""
        return self.pressure_clock.level

    def advance_phase(self) -> str:
        """Cycle to the next campaign phase.

        Cycles march -> camp -> mission -> march.

        Returns:
            The new phase name.
        """
        idx = self.PHASE_CYCLE.index(self.current_phase) if self.current_phase in self.PHASE_CYCLE else 0
        self.current_phase = self.PHASE_CYCLE[(idx + 1) % len(self.PHASE_CYCLE)]
        return self.current_phase

    def march(
        self,
        destination: str,
        supply_cost: int = 1,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Move the Legion to a new destination.

        Consumes supply, advances the campaign day counter, appends the
        destination to the route, and rolls for random encounters.

        Args:
            destination: The name of the location being marched to.
            supply_cost: Supply consumed by the march (default 1).
            rng: Optional seeded Random for deterministic results.

        Returns:
            Dict with keys: destination, supply_before, supply_after,
            supply_cost, encounter (bool), encounter_type (str or None),
            day, phase.
        """
        _rng = rng or random.Random()
        supply_before = self.supply
        actual_cost = min(supply_cost, self.supply)
        self.supply = max(0, self.supply - actual_cost)
        self.time_passed += 1
        self.route.append(destination)

        # Supply shortfall hits morale
        if actual_cost < supply_cost:
            self.morale = max(1, self.morale - 1)

        # Random encounter check
        encounter = _rng.random() < MARCH_ENCOUNTER_CHANCE
        encounter_types = [
            "undead patrol",
            "Broken scouts",
            "civilian refugees",
            "abandoned supply cache",
            "ambush",
        ]
        encounter_type = _rng.choice(encounter_types) if encounter else None

        return {
            "destination": destination,
            "supply_before": supply_before,
            "supply_after": self.supply,
            "supply_cost": actual_cost,
            "encounter": encounter,
            "encounter_type": encounter_type,
            "day": self.time_passed,
            "phase": self.current_phase,
        }

    def camp(
        self,
        activity: str = "rest",
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Perform a camp phase activity.

        Supported activities: rest, resupply, recruit, ceremony, train,
        intel_review.

        Args:
            activity: The camp activity to perform (default "rest").
            rng: Optional seeded Random for deterministic results.

        Returns:
            Dict with keys: activity, morale_before, morale_after,
            supply_before, supply_after, supply_gained (resupply only),
            description, result.
        """
        _rng = rng or random.Random()
        config = CAMP_ACTIVITIES.get(activity, CAMP_ACTIVITIES["rest"])

        morale_before = self.morale
        supply_before = self.supply

        morale_delta = config["morale_delta"]
        supply_cost = config["supply_cost"]

        supply_gained = 0
        result = ""

        # Apply supply cost (if any)
        self.supply = max(0, self.supply - supply_cost)

        # Activity-specific logic
        if activity == "rest":
            self.morale = min(5, self.morale + morale_delta)
            result = "Troops rest. Morale improves."

        elif activity == "resupply":
            # Roll-based resupply: d3+1 supply
            supply_gained = _rng.randint(1, 3) + 1
            self.supply = min(10, self.supply + supply_gained)
            result = f"Scavenging yields {supply_gained} supply."

        elif activity == "recruit":
            if self.supply >= supply_cost:
                result = "Recruitment successful. New soldiers join the Legion."
            else:
                result = "Insufficient supply for recruitment."

        elif activity == "ceremony":
            self.morale = min(5, self.morale + morale_delta)
            result = "The ceremony strengthens resolve. Morale improves significantly."

        elif activity == "train":
            result = "Drills complete. Soldiers are sharper for it."

        elif activity == "intel_review":
            result = "Intelligence reviewed. The Legion has a clearer picture of the enemy."

        else:
            result = f"Activity '{activity}' completed."

        return {
            "activity": activity,
            "morale_before": morale_before,
            "morale_after": self.morale,
            "supply_before": supply_before,
            "supply_after": self.supply,
            "supply_gained": supply_gained,
            "description": config["description"],
            "result": result,
        }

    def pressure_check(self, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        """Roll to see if Pressure increases.

        The base chance of pressure increase depends on the current pressure
        level (higher pressure = higher chance of further escalation).
        A natural roll result is also returned for transparency.

        Args:
            rng: Optional seeded Random for deterministic results.

        Returns:
            Dict with keys: roll, threshold, pressure_increased (bool),
            old_level, new_level, label, tick_result.
        """
        _rng = rng or random.Random()

        # Higher pressure = lower threshold to pass (more likely to worsen)
        # Level 0-1: 30%, Level 2: 40%, Level 3: 50%, Level 4: 60%, Level 5: 0% (already max)
        thresholds = {0: 30, 1: 30, 2: 40, 3: 50, 4: 60, 5: 0}
        threshold = thresholds.get(self.pressure_clock.level, 30)

        roll = _rng.randint(1, 100)
        pressure_increased = roll <= threshold and not self.pressure_clock.is_final

        tick_result = None
        if pressure_increased:
            tick_result = self.pressure_clock.tick(1)

        return {
            "roll": roll,
            "threshold": threshold,
            "pressure_increased": pressure_increased,
            "old_level": tick_result["old_level"] if tick_result else self.pressure_clock.level,
            "new_level": self.pressure_clock.level,
            "label": self.pressure_clock.label,
            "tick_result": tick_result,
        }

    def time_passes(self, days: int = 1) -> str:
        """Advance the campaign clock by *days* days.

        Args:
            days: Number of days to advance (default 1).

        Returns:
            Human-readable status string.
        """
        self.time_passed += days
        return (
            f"Day {self.time_passed}: {days} day(s) pass. "
            f"Morale: {self.morale}/5 | Supply: {self.supply}/10 | "
            f"Pressure: {self.pressure_clock.label} (level {self.pressure})"
        )

    def add_relic(self, relic_name: str) -> str:
        """Add a holy relic to the Legion's inventory.

        Args:
            relic_name: Name of the acquired relic.

        Returns:
            Confirmation string.
        """
        self.holy_relics.append(relic_name)
        return f"Relic acquired: {relic_name}. Legion now holds {len(self.holy_relics)} relic(s)."

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dict of current campaign state."""
        return {
            "phase": self.current_phase,
            "day": self.time_passed,
            "morale": self.morale,
            "morale_label": MORALE_DESCRIPTIONS.get(self.morale, "Unknown"),
            "supply": self.supply,
            "pressure": self.pressure,
            "pressure_label": self.pressure_clock.label,
            "relics": len(self.holy_relics),
            "relic_names": list(self.holy_relics),
            "route": list(self.route),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for save/load."""
        return {
            "current_phase": self.current_phase,
            "time_passed": self.time_passed,
            "morale": self.morale,
            "supply": self.supply,
            "pressure_clock": self.pressure_clock.to_dict(),
            "holy_relics": list(self.holy_relics),
            "route": list(self.route),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignPhaseManager":
        """Deserialize from a plain dict."""
        mgr = cls(
            current_phase=data.get("current_phase", "march"),
            time_passed=data.get("time_passed", 0),
            morale=data.get("morale", 3),
            supply=data.get("supply", 5),
            holy_relics=data.get("holy_relics", []),
            route=data.get("route", []),
        )
        clock_data = data.get("pressure_clock", {})
        mgr.pressure_clock = PressureClock.from_dict(clock_data)
        return mgr

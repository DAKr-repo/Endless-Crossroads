"""
UniversalClock - Unified progress / threshold clock system.
===========================================================

Supports two modes:
  - Segment mode (FactionClock-style): finite segments, tick() returns True
    when filled.
  - Threshold mode (DoomClock-style): open-ended counter, advance() returns
    triggered event strings.

Both modes can be combined (e.g., a 20-segment clock with narrative thresholds).

Also provides DayClock and TimeOfDay for world-simulation time tracking.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


@dataclass
class UniversalClock:
    """A progress clock that supports both segment-capped and threshold modes.

    Segment mode:   Set *max_segments* to a positive int (4, 6, 8, 20 …).
                    tick() returns True when filled >= max_segments.

    Threshold mode: Populate the *thresholds* dict ({int: str}).
                    advance() returns a list of triggered event strings.

    Both modes compose freely on the same instance.
    """

    name: str
    filled: int = 0
    max_segments: Optional[int] = None          # None = unlimited
    thresholds: Dict[int, str] = field(default_factory=dict)

    # --- Aliases for backward compatibility -----------------------------------

    @property
    def current(self) -> int:
        """Alias for *filled* (DoomClock compat)."""
        return self.filled

    @current.setter
    def current(self, value: int) -> None:
        self.filled = value

    @property
    def segments(self) -> Optional[int]:
        """Alias for *max_segments* (FactionClock compat)."""
        return self.max_segments

    # --- Core API -------------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """True when the clock has reached its cap (segment mode only)."""
        if self.max_segments is None:
            return False
        return self.filled >= self.max_segments

    def tick(self, amount: int = 1) -> bool:
        """Advance the clock (segment-style).

        Returns True when the clock completes.  Clamps to *max_segments*
        if set; otherwise increments freely.
        """
        if self.max_segments is not None:
            self.filled = min(self.filled + amount, self.max_segments)
        else:
            self.filled += amount
        return self.is_complete

    def advance(self, turns: int = 1) -> List[str]:
        """Advance the clock (threshold-style).

        Returns a list of event strings for every threshold crossed.
        """
        old = self.filled
        self.tick(turns)

        triggered: List[str] = []
        for threshold, event in sorted(self.thresholds.items()):
            if old < threshold <= self.filled:
                triggered.append(f"[DOOM {threshold}] {event}")
        return triggered

    def reset(self) -> None:
        """Reset clock to 0."""
        self.filled = 0

    # --- Serialisation --------------------------------------------------------

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "filled": self.filled}
        if self.max_segments is not None:
            d["max_segments"] = self.max_segments
            d["segments"] = self.max_segments       # FactionClock compat key
        if self.thresholds:
            d["thresholds"] = self.thresholds
        # DoomClock compat key
        d["current"] = self.filled
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "UniversalClock":
        raw_thresholds = data.get("thresholds", {})
        thresholds = {int(k): v for k, v in raw_thresholds.items()}
        return cls(
            name=data.get("name", "Clock"),
            filled=data.get("filled", data.get("current", 0)),
            max_segments=data.get("max_segments", data.get("segments")),
            thresholds=thresholds,
        )


# ── Backward-Compatible Factory Functions ────────────────────────────────

def FactionClock(name: str, segments: int = 4, filled: int = 0) -> UniversalClock:
    """Create a segment-mode UniversalClock (FactionClock compat)."""
    return UniversalClock(name=name, max_segments=segments, filled=filled)


def DoomClock(current: int = 0, thresholds: Optional[Dict[int, str]] = None) -> UniversalClock:
    """Create a threshold-mode UniversalClock (DoomClock compat)."""
    return UniversalClock(
        name="Doom",
        filled=current,
        max_segments=None,
        thresholds=thresholds or {},
    )


# ── Day/Night Cycle ───────────────────────────────────────────────────────────

class TimeOfDay(Enum):
    """Eight phases of the day, advancing in order."""
    DAWN = "dawn"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"
    PREDAWN = "predawn"


class DayClock:
    """Tracks time of day and day count across 8 phases per day.

    Each call to advance() moves forward one or more phases.  Wrapping
    past PREDAWN increments the day counter.  Key transitions emit
    atmospheric flavor messages.
    """

    _PHASES: List[TimeOfDay] = list(TimeOfDay)

    def __init__(
        self,
        phase: TimeOfDay = TimeOfDay.MORNING,
        day: int = 1,
    ) -> None:
        self.phase: TimeOfDay = phase
        self.day: int = day

    def advance(self, ticks: int = 1) -> List[str]:
        """Advance time by *ticks* phases.

        Returns a list of atmospheric flavor strings for notable transitions
        (dawn, dusk, midnight).  Empty list if no key transitions occurred.
        """
        messages: List[str] = []
        for _ in range(ticks):
            idx = self._PHASES.index(self.phase)
            new_idx = (idx + 1) % len(self._PHASES)
            if new_idx == 0:  # Wrapped past PREDAWN → new day
                self.day += 1
            self.phase = self._PHASES[new_idx]
            if self.phase == TimeOfDay.DAWN:
                messages.append("The first light of dawn creeps across the horizon.")
            elif self.phase == TimeOfDay.DUSK:
                messages.append("Shadows lengthen as dusk settles over the land.")
            elif self.phase == TimeOfDay.MIDNIGHT:
                messages.append("The deepest hour of night arrives.")
        return messages

    def is_dark(self) -> bool:
        """Return True for phases from DUSK through PREDAWN (inclusive)."""
        return self.phase in (
            TimeOfDay.DUSK,
            TimeOfDay.NIGHT,
            TimeOfDay.MIDNIGHT,
            TimeOfDay.PREDAWN,
        )

    def display(self) -> str:
        """Human-readable summary, e.g. 'Day 3 — Dusk'."""
        return f"Day {self.day} \u2014 {self.phase.value.title()}"

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        return {"phase": self.phase.value, "day": self.day}

    @classmethod
    def from_dict(cls, data: dict) -> "DayClock":
        """Restore from a serialized dict."""
        return cls(
            phase=TimeOfDay(data["phase"]),
            day=data.get("day", 1),
        )

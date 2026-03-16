"""
UniversalClock - Unified progress / threshold clock system.
===========================================================

Supports two modes:
  - Segment mode (FactionClock-style): finite segments, tick() returns True
    when filled.
  - Threshold mode (DoomClock-style): open-ended counter, advance() returns
    triggered event strings.

Both modes can be combined (e.g., a 20-segment clock with narrative thresholds).
"""

from dataclasses import dataclass, field
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

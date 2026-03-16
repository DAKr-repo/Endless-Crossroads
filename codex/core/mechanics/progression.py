"""
codex.core.mechanics.progression — XP / Milestone / FITD Advancement
======================================================================

Supports 4 progression systems:
  - "xp": D&D 5e SRD XP thresholds
  - "milestone": Cosmere Radiant Ideal milestones
  - "fitd": Forged in the Dark 8-mark advancement
  - "gear": Burnwillow gear-as-progression (MetaUnlocks)

WO-V34.0: The Sovereign Dashboard — Gap #9
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# =========================================================================
# D&D 5e SRD XP TABLE
# =========================================================================

DND5E_XP_TABLE: Dict[int, int] = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
    6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
    11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
    16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000,
}

# FITD: 8 XP marks per advance
FITD_XP_PER_ADVANCE = 8


# =========================================================================
# PROGRESSION TRACKER
# =========================================================================

@dataclass
class ProgressionTracker:
    """Tracks character advancement across all engine families."""
    system: str             # "xp" | "milestone" | "fitd" | "gear"
    current_xp: int = 0
    milestones: int = 0
    xp_log: List[dict] = field(default_factory=list)

    def award_xp(self, amount: int, source: str = "") -> str:
        """Award XP (for 'xp' system). Returns status message."""
        self.current_xp += amount
        self.xp_log.append({"amount": amount, "source": source})
        return f"+{amount} XP from {source or 'unknown'} (total: {self.current_xp})"

    def check_level_up(self, current_level: int) -> bool:
        """Check if enough XP for next level (for 'xp' system)."""
        if self.system != "xp":
            return False
        next_level = current_level + 1
        threshold = DND5E_XP_TABLE.get(next_level)
        if threshold is None:
            return False
        return self.current_xp >= threshold

    def mark_xp(self, trigger: str = "") -> str:
        """Mark XP (for 'fitd' system). Returns status message."""
        self.current_xp += 1
        self.xp_log.append({"amount": 1, "source": trigger})
        if self.current_xp >= FITD_XP_PER_ADVANCE:
            self.current_xp -= FITD_XP_PER_ADVANCE
            return f"XP marked ({trigger}). ADVANCE AVAILABLE!"
        return f"XP marked ({trigger}). {self.current_xp}/{FITD_XP_PER_ADVANCE}"

    def advance_milestone(self, desc: str = "") -> str:
        """Record a milestone (for 'milestone' system). Returns status message."""
        self.milestones += 1
        self.xp_log.append({"amount": 1, "source": desc, "type": "milestone"})
        return f"Milestone #{self.milestones}: {desc or 'Achievement'}"

    def get_xp_to_next(self, current_level: int) -> int:
        """XP remaining until next level (for 'xp' system)."""
        if self.system != "xp":
            return 0
        next_level = current_level + 1
        threshold = DND5E_XP_TABLE.get(next_level, 0)
        return max(0, threshold - self.current_xp)

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "current_xp": self.current_xp,
            "milestones": self.milestones,
            "xp_log": self.xp_log[-20:],  # Keep last 20 entries
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProgressionTracker":
        return cls(
            system=data.get("system", "xp"),
            current_xp=data.get("current_xp", 0),
            milestones=data.get("milestones", 0),
            xp_log=data.get("xp_log", []),
        )

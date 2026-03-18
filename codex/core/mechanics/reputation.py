"""
codex/core/mechanics/reputation.py — Faction Reputation System
===============================================================

Tracks player standing with named factions on a -3..+3 scale.
Provides disposition modifiers for NPC interaction and persistence
via to_dict/from_dict.

Standing titles map cleanly to NPC attitude: Honored allies help
the party without question; Outcasts face hostility or refusal.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


# Standing titles keyed by integer level
STANDING_TITLES: Dict[int, str] = {
    -3: "Outcast",
    -2: "Suspect",
    -1: "Stranger",
    0: "Neutral",
    1: "Known",
    2: "Trusted",
    3: "Honored",
}

# NPC disposition shift per standing level (added to base DC or dialogue roll)
_DISPOSITION_MAP: Dict[int, int] = {
    -3: -6,  # Hostile — attacks or refuses outright
    -2: -4,  # Suspicious — prices raised, info withheld
    -1: -2,  # Cold — minimal help
    0:   0,  # Neutral — standard interaction
    1:   2,  # Friendly — slight discount, more info
    2:   4,  # Warm — will go out of their way
    3:   6,  # Allied — will risk themselves for the party
}


@dataclass
class FactionStanding:
    """Standing between the party and one named faction.

    Args:
        faction_id: Machine-readable faction key (e.g. "city_watch").
        standing:   Current level, clamped to -3..+3.
    """

    faction_id: str
    standing: int = 0

    @property
    def title(self) -> str:
        """Human-readable tier label for the current standing."""
        return STANDING_TITLES.get(self.standing, "Unknown")

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        return {
            "faction_id": self.faction_id,
            "standing": self.standing,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FactionStanding":
        """Restore from a serialized dict."""
        return cls(
            faction_id=data["faction_id"],
            standing=int(data.get("standing", 0)),
        )


class ReputationTracker:
    """Manages standing across all factions the party has interacted with.

    Factions are created on first contact and persist until cleared.
    Standing is always clamped to the -3..+3 range.
    """

    def __init__(self) -> None:
        self.standings: Dict[str, FactionStanding] = {}

    # ─── Core API ────────────────────────────────────────────────────────

    def adjust(self, faction_id: str, delta: int, reason: str = "") -> str:
        """Adjust standing for a faction and return a tier-change message.

        Creates the faction entry at neutral if it doesn't exist.
        Clamps the result to -3..+3.

        Args:
            faction_id: The faction to adjust.
            delta:      Positive = better standing, negative = worse.
            reason:     Optional flavour string for the log message.

        Returns:
            A human-readable message describing the change.
        """
        fs = self._get_or_create(faction_id)
        old_standing = fs.standing
        old_title = fs.title

        new_raw = old_standing + delta
        fs.standing = max(-3, min(3, new_raw))
        new_title = fs.title

        reason_str = f" ({reason})" if reason else ""
        if fs.standing == old_standing:
            return f"{faction_id}: standing unchanged at {old_title}{reason_str}."

        direction = "improved" if delta > 0 else "worsened"
        tier_changed = new_title != old_title
        if tier_changed:
            return (
                f"{faction_id}: standing {direction} from {old_title} "
                f"to {new_title} ({fs.standing:+d}){reason_str}."
            )
        return (
            f"{faction_id}: standing {direction} "
            f"({old_standing:+d} -> {fs.standing:+d}, {new_title}){reason_str}."
        )

    def get_standing(self, faction_id: str) -> FactionStanding:
        """Return the current FactionStanding, creating neutral if absent."""
        return self._get_or_create(faction_id)

    def get_disposition_modifier(self, faction_id: str) -> int:
        """Return an integer modifier for NPC interactions with this faction.

        Positive values make checks easier; negative values harder.
        """
        fs = self._get_or_create(faction_id)
        return _DISPOSITION_MAP.get(fs.standing, 0)

    def all_standings(self) -> list:
        """Return a sorted list of (faction_id, FactionStanding) tuples."""
        return sorted(self.standings.items(), key=lambda x: x[0])

    # ─── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize the full tracker to a JSON-safe dict."""
        return {
            "standings": {
                fid: fs.to_dict()
                for fid, fs in self.standings.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReputationTracker":
        """Restore a ReputationTracker from a serialized dict."""
        tracker = cls()
        for fid, fs_data in data.get("standings", {}).items():
            tracker.standings[fid] = FactionStanding.from_dict(fs_data)
        return tracker

    # ─── Internal ────────────────────────────────────────────────────────

    def _get_or_create(self, faction_id: str) -> FactionStanding:
        if faction_id not in self.standings:
            self.standings[faction_id] = FactionStanding(faction_id=faction_id)
        return self.standings[faction_id]

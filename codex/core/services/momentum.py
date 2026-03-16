"""
Momentum Ledger — Cumulative trend tracking for TownCryer.
==========================================================

WO-V61.0 Track C: Bins player actions by GRAPES category + location.
When a category accumulates enough weight in a location, fires a compound
event that synthesizes the trend into a narrative broadcast.

Thresholds:
    3.0  — Minor shift (single TownCryer rumor)
    7.0  — Notable trend (TownCryer broadcast + GRAPES modifier)
    12.0 — Major shift (broadcast + GRAPES mutation + ANCHOR shard)
    20.0 — Tipping point (cascade — secondary bin gets +3.0 free weight)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class MomentumEntry:
    """A single binned action."""
    category: str       # GRAPES key: "geography", "religion", etc.
    location: str       # Ward/zone/region identifier
    weight: float       # Impact weight (default 1.0, scaled by action type)
    action_tag: str     # What happened: "aided_poor", "killed_boss", "stole_goods"
    turn: int = 0       # Game turn for ordering
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MomentumBin:
    """Accumulated momentum in one category+location pair."""
    category: str
    location: str
    total_weight: float = 0.0
    entry_count: int = 0
    entries: List[MomentumEntry] = field(default_factory=list)
    last_threshold_fired: float = 0.0      # Prevents re-firing same positive threshold
    last_neg_threshold_fired: float = 0.0  # Prevents re-firing same negative threshold
    last_entry_turn: int = 0               # For decay staleness check

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "location": self.location,
            "total_weight": self.total_weight,
            "entry_count": self.entry_count,
            "last_threshold_fired": self.last_threshold_fired,
            "last_neg_threshold_fired": self.last_neg_threshold_fired,
            "last_entry_turn": self.last_entry_turn,
            "entries": [
                {"category": e.category, "location": e.location,
                 "weight": e.weight, "action_tag": e.action_tag,
                 "turn": e.turn, "timestamp": e.timestamp}
                for e in self.entries[-20:]  # Cap stored entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MomentumBin":
        b = cls(
            category=data["category"],
            location=data["location"],
            total_weight=data.get("total_weight", 0.0),
            entry_count=data.get("entry_count", 0),
            last_threshold_fired=data.get("last_threshold_fired", 0.0),
            last_neg_threshold_fired=data.get("last_neg_threshold_fired", 0.0),
            last_entry_turn=data.get("last_entry_turn", 0),
        )
        for e in data.get("entries", []):
            b.entries.append(MomentumEntry(
                category=e["category"], location=e["location"],
                weight=e["weight"], action_tag=e["action_tag"],
                turn=e.get("turn", 0), timestamp=e.get("timestamp", ""),
            ))
        return b


# Maps session log event types to GRAPES categories + base weight
ACTION_CATEGORY_MAP: Dict[str, Tuple[str, float]] = {
    "kill":             ("security", 1.0),
    "room_cleared":     ("security", 0.5),
    "quest_complete":   ("politics", 2.0),
    "loot":             ("economics", 0.5),
    "faction_shift":    ("politics", 2.0),
    "doom_threshold":   ("religion", 1.5),
    "zone_breakthrough": ("geography", 2.0),
    "room_entered":     ("geography", 0.3),
    "party_death":      ("security", -1.0),  # Negative: area feels dangerous
    "near_death":       ("security", -0.5),
    "companion_fell":   ("security", -1.5),
    "ally_saved":       ("social", 1.0),
    "rare_item_used":   ("economics", 1.0),
}

# Cascade connections: when a category tips, which secondary bin gets free weight
CASCADE_MAP: Dict[str, str] = {
    "security": "economics",     # Safe streets -> merchant traffic
    "economics": "politics",     # Wealth -> political influence
    "politics": "social",        # Political power -> social change
    "social": "religion",        # Social upheaval -> spiritual seeking
    "religion": "geography",     # Religious expansion -> territory
    "geography": "security",     # New territory -> defense needs
}


class MomentumLedger:
    """Tracks cumulative player action trends by GRAPES category + location.

    Thresholds:
        3.0  — Minor shift (single TownCryer rumor)
        7.0  — Notable trend (TownCryer broadcast + GRAPES modifier)
        12.0 — Major shift (broadcast + GRAPES mutation + ANCHOR shard)
        20.0 — Tipping point (cascade event — secondary bin gets +3.0)
    """

    THRESHOLDS = [3.0, 7.0, 12.0, 20.0]
    THRESHOLD_NAMES = {
        3.0: "minor_shift",
        7.0: "notable_trend",
        12.0: "major_shift",
        20.0: "tipping_point",
    }

    def __init__(self, universe_id: str = ""):
        self.universe_id = universe_id
        self._bins: Dict[Tuple[str, str], MomentumBin] = {}

    def record(self, category: str, location: str, action_tag: str,
               weight: float = 1.0, turn: int = 0) -> List[dict]:
        """Record an action. Returns list of newly crossed thresholds.

        Each threshold dict contains:
            level: float (3.0, 7.0, 12.0, or 20.0)
            name: str (minor_shift, notable_trend, major_shift, tipping_point)
            category: str
            location: str
            total_weight: float
            entry_count: int
            cascade: Optional[dict] (only for tipping_point)
        """
        key = (category, location)
        if key not in self._bins:
            self._bins[key] = MomentumBin(category=category, location=location)

        b = self._bins[key]
        entry = MomentumEntry(
            category=category, location=location,
            weight=weight, action_tag=action_tag, turn=turn,
        )
        b.entries.append(entry)
        b.total_weight += weight
        b.entry_count += 1
        b.last_entry_turn = turn

        # Check positive thresholds
        crossed = []
        for threshold in self.THRESHOLDS:
            if b.total_weight >= threshold > b.last_threshold_fired:
                event = {
                    "level": threshold,
                    "name": self.THRESHOLD_NAMES[threshold],
                    "category": category,
                    "location": location,
                    "total_weight": b.total_weight,
                    "entry_count": b.entry_count,
                }
                b.last_threshold_fired = threshold

                # Handle cascade at tipping point
                if threshold == 20.0:
                    cascade_cat = CASCADE_MAP.get(category)
                    if cascade_cat:
                        cascade_events = self.record(
                            cascade_cat, location, f"cascade_from_{category}",
                            weight=3.0, turn=turn,
                        )
                        event["cascade"] = {
                            "category": cascade_cat,
                            "weight": 3.0,
                            "events": cascade_events,
                        }

                crossed.append(event)

        # Check negative thresholds (absolute value of total_weight vs threshold)
        # Fires when the bin has gone sufficiently negative, independently of
        # positive threshold history. Uses last_neg_threshold_fired to prevent
        # re-firing the same negative level.
        if b.total_weight < 0:
            abs_weight = abs(b.total_weight)
            for threshold in self.THRESHOLDS:
                if abs_weight >= threshold > b.last_neg_threshold_fired:
                    event = {
                        "level": threshold,
                        "name": self.THRESHOLD_NAMES[threshold],
                        "category": category,
                        "location": location,
                        "total_weight": b.total_weight,  # Negative; handler reads sign
                        "entry_count": b.entry_count,
                    }
                    b.last_neg_threshold_fired = threshold

                    # Negative tipping point cascades with negative free weight
                    if threshold == 20.0:
                        cascade_cat = CASCADE_MAP.get(category)
                        if cascade_cat:
                            cascade_events = self.record(
                                cascade_cat, location, f"cascade_from_{category}",
                                weight=-3.0, turn=turn,
                            )
                            event["cascade"] = {
                                "category": cascade_cat,
                                "weight": -3.0,
                                "events": cascade_events,
                            }

                    crossed.append(event)

        return crossed

    def record_from_event(self, event_type: str, location: str,
                          turn: int = 0, tier: int = 1) -> List[dict]:
        """Record from a session log event type using ACTION_CATEGORY_MAP.

        Args:
            event_type: Session log event type (e.g. "kill", "loot")
            location: Current location identifier
            turn: Current game turn
            tier: Enemy/area tier for weight scaling

        Returns:
            List of crossed threshold events (same as record()).
        """
        mapping = ACTION_CATEGORY_MAP.get(event_type)
        if not mapping:
            return []
        category, base_weight = mapping
        # Scale weight by tier for combat events
        if event_type in ("kill", "room_cleared"):
            weight = base_weight + (tier - 1) * 0.5
        else:
            weight = base_weight
        return self.record(category, location, event_type, weight, turn)

    def get_bin(self, category: str, location: str) -> Optional[MomentumBin]:
        """Get accumulated momentum for a category+location pair."""
        return self._bins.get((category, location))

    def get_dominant_trend(self, location: str) -> Optional[Tuple[str, float]]:
        """Return the highest-weight category for a given location."""
        best = None
        best_weight = 0.0
        for (cat, loc), b in self._bins.items():
            if loc == location and b.total_weight > best_weight:
                best = cat
                best_weight = b.total_weight
        return (best, best_weight) if best else None

    def get_all_trends(self, min_weight: float = 3.0) -> List[MomentumBin]:
        """Return all bins above a minimum weight threshold."""
        return [b for b in self._bins.values() if b.total_weight >= min_weight]

    def decay(self, current_turn: int, stale_turns: int = 30,
              decay_amount: float = 0.5, prune_below: float = 1.0) -> int:
        """Apply decay to stale bins.

        Args:
            current_turn: Current game turn
            stale_turns: Number of turns without activity before decay applies
            decay_amount: Weight removed per decay call
            prune_below: Bins below this weight are removed

        Returns:
            Number of bins pruned.
        """
        pruned = 0
        keys_to_remove = []
        for key, b in self._bins.items():
            if current_turn - b.last_entry_turn >= stale_turns:
                b.total_weight -= decay_amount
                if b.total_weight < prune_below:
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._bins[key]
            pruned += 1
        return pruned

    def to_dict(self) -> dict:
        return {
            "universe_id": self.universe_id,
            "bins": {
                f"{cat}|{loc}": b.to_dict()
                for (cat, loc), b in self._bins.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MomentumLedger":
        ledger = cls(universe_id=data.get("universe_id", ""))
        for key_str, bin_data in data.get("bins", {}).items():
            b = MomentumBin.from_dict(bin_data)
            ledger._bins[(b.category, b.location)] = b
        return ledger

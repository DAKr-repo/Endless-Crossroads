"""
codex.core.world.world_ledger -- Player-Driven World Mutation System
=====================================================================

Tracks and persists player-driven mutations to a G.R.A.P.E.S. profile,
enabling write-back of in-game world changes (cleared landmarks, depleted
resources, etc.) to the world JSON file.

WO-V8.1: The Crier's Pulse
WO-V11.2: The Chronologer — HistoricalEvent timeline + persistence
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EventType(Enum):
    """Classification of historical events."""
    WAR = "war"
    DISCOVERY = "discovery"
    CHRONICLE_ENDING = "chronicle_ending"
    MUTATION = "mutation"
    POLITICAL = "political"
    ECONOMIC = "economic"
    SOCIAL = "social"
    CIVIC = "civic"
    FACTION = "faction"


class AuthorityLevel(Enum):
    """How reliable is the source of this event?"""
    EYEWITNESS = 1
    CHRONICLE = 2
    LEGEND = 3


# ---------------------------------------------------------------------------
# HistoricalEvent dataclass
# ---------------------------------------------------------------------------

@dataclass
class HistoricalEvent:
    """A single recorded event in the world's chronology."""
    timestamp: str
    event_type: EventType
    summary: str
    authority_level: AuthorityLevel = AuthorityLevel.CHRONICLE
    category: str = ""
    universe_id: str = ""
    source: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "summary": self.summary,
            "authority_level": self.authority_level.value,
            "category": self.category,
            "universe_id": self.universe_id,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoricalEvent":
        return cls(
            timestamp=data.get("timestamp", ""),
            event_type=EventType(data["event_type"]),
            summary=data.get("summary", ""),
            authority_level=AuthorityLevel(data.get("authority_level", 2)),
            category=data.get("category", ""),
            universe_id=data.get("universe_id", ""),
            source=data.get("source", ""),
        )


# ---------------------------------------------------------------------------
# CivicCategory → EventType mapping for ingest_civic_event()
# ---------------------------------------------------------------------------

_CIVIC_TO_EVENT: dict = {
    "trade": EventType.ECONOMIC,
    "security": EventType.FACTION,
    "rumor": EventType.SOCIAL,
    "morale": EventType.SOCIAL,
    "infrastructure": EventType.CIVIC,
}


class WorldLedger:
    """Tracks and persists player-driven mutations to a G.R.A.P.E.S. profile."""

    def __init__(self, world_path: Path, grapes_dict: dict):
        self._path = world_path
        self._grapes = grapes_dict
        self._changelog: List[dict] = []
        self._chronology: List[HistoricalEvent] = []
        self._load_chronology()

    # ------------------------------------------------------------------
    # Chronology hydration
    # ------------------------------------------------------------------

    def _load_chronology(self) -> None:
        """Hydrate chronology from the world JSON file on init."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                world_data = json.load(f)
            for entry in world_data.get("chronology", []):
                try:
                    self._chronology.append(HistoricalEvent.from_dict(entry))
                except (KeyError, ValueError):
                    pass
        except (json.JSONDecodeError, IOError):
            pass

    # ------------------------------------------------------------------
    # Internal: append a chronology entry
    # ------------------------------------------------------------------

    def _record(
        self,
        event_type: EventType,
        summary: str,
        authority_level: AuthorityLevel = AuthorityLevel.EYEWITNESS,
        category: str = "",
        source: str = "auto",
    ) -> None:
        self._chronology.append(HistoricalEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            summary=summary,
            authority_level=authority_level,
            category=category,
            source=source,
        ))

    # ------------------------------------------------------------------
    # Mutation methods (original API — now auto-record chronology)
    # ------------------------------------------------------------------

    def mutate(self, category: str, index: int, field: str, value: str) -> None:
        """Change a specific field on a G.R.A.P.E.S. entry.

        Args:
            category: G.R.A.P.E.S. category key (e.g. "geography", "economics").
            index: Index of the entry within the category list.
            field: Field name on the entry dict to modify.
            value: New value for the field.

        Raises:
            KeyError: If category doesn't exist in grapes data.
            IndexError: If index is out of range.
        """
        entries = self._grapes.get(category)
        if entries is None:
            raise KeyError(f"Unknown G.R.A.P.E.S. category: {category}")
        if not isinstance(entries, list) or index < 0 or index >= len(entries):
            raise IndexError(
                f"Index {index} out of range for '{category}' "
                f"(has {len(entries) if isinstance(entries, list) else 0} entries)"
            )
        entry = entries[index]
        if not isinstance(entry, dict) or field not in entry:
            raise KeyError(f"Field '{field}' not found on {category}[{index}]")

        old_value = entry[field]
        entry[field] = value
        detail = f"{category}[{index}].{field}: '{old_value}' -> '{value}'"
        self._changelog.append({
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "action": "mutate",
            "detail": detail,
        })
        self._record(EventType.MUTATION, detail, category=category)

    def clear_landmark(self, landmark_name: str, cleared_by: str = "unknown") -> bool:
        """Mark a geography landmark as cleared.

        Args:
            landmark_name: Name of the landmark to clear.
            cleared_by: Who/what cleared the landmark.

        Returns:
            True if the landmark was found and cleared, False otherwise.
        """
        geo = self._grapes.get("geography", [])
        if not isinstance(geo, list):
            return False
        for entry in geo:
            if isinstance(entry, dict) and entry.get("name") == landmark_name:
                old_feature = entry.get("feature", "")
                entry["feature"] = f"Cleared by {cleared_by}"
                self._changelog.append({
                    "timestamp": datetime.now().isoformat(),
                    "category": "geography",
                    "action": "clear_landmark",
                    "detail": f"'{landmark_name}': '{old_feature}' -> 'Cleared by {cleared_by}'",
                })
                self._record(
                    EventType.DISCOVERY,
                    f"Landmark '{landmark_name}' cleared by {cleared_by}",
                    category="geography",
                )
                return True
        return False

    def deplete_resource(self, resource_name: str) -> bool:
        """Shift a ScarcityEntry's abundance to 'depleted'.

        Args:
            resource_name: Name of the resource to deplete.

        Returns:
            True if the resource was found and depleted, False otherwise.
        """
        econ = self._grapes.get("economics", [])
        if not isinstance(econ, list):
            return False
        for entry in econ:
            if isinstance(entry, dict) and entry.get("resource") == resource_name:
                old_abundance = entry.get("abundance", "")
                entry["abundance"] = "depleted"
                self._changelog.append({
                    "timestamp": datetime.now().isoformat(),
                    "category": "economics",
                    "action": "deplete_resource",
                    "detail": f"'{resource_name}': '{old_abundance}' -> 'depleted'",
                })
                self._record(
                    EventType.ECONOMIC,
                    f"Resource '{resource_name}' depleted (was {old_abundance})",
                    category="economics",
                )
                return True
        return False

    # ------------------------------------------------------------------
    # Public chronology API
    # ------------------------------------------------------------------

    def record_historical_event(
        self,
        event_type: EventType,
        summary: str,
        authority_level: AuthorityLevel = AuthorityLevel.CHRONICLE,
        category: str = "",
        universe_id: str = "",
        source: str = "manual",
    ) -> None:
        """Manually record a historical event in the chronology."""
        self._chronology.append(HistoricalEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            summary=summary,
            authority_level=authority_level,
            category=category,
            universe_id=universe_id,
            source=source,
        ))

    def get_chronology(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50,
    ) -> List[HistoricalEvent]:
        """Return chronology entries, most-recent-first.

        Args:
            event_type: If set, filter to only this type.
            limit: Maximum number of entries to return.
        """
        events = self._chronology
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return list(reversed(events))[:limit]

    def ingest_civic_event(self, event_dict: dict) -> None:
        """Bridge a CivicPulse/WorldHistory event into the chronology.

        Maps CivicCategory string values to EventType via _CIVIC_TO_EVENT.
        """
        cat_str = event_dict.get("category", "").lower()
        event_type = _CIVIC_TO_EVENT.get(cat_str, EventType.CIVIC)
        summary = event_dict.get("event_tag", event_dict.get("detail", "Civic event"))
        self._chronology.append(HistoricalEvent(
            timestamp=event_dict.get("timestamp", datetime.now().isoformat()),
            event_type=event_type,
            summary=summary,
            authority_level=AuthorityLevel.CHRONICLE,
            category=cat_str,
            source="civic_pulse",
        ))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Write mutated grapes + chronology back to the world JSON file."""
        from codex.paths import safe_save_json

        if not self._path.exists():
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                world_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        world_data["grapes"] = self._grapes
        world_data["chronology"] = [e.to_dict() for e in self._chronology]
        safe_save_json(self._path, world_data)

    def get_changelog(self) -> List[dict]:
        """Return the list of mutations for display/logging."""
        return list(self._changelog)

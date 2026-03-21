"""
codex.core.mechanics.npc_tracker — NPC Relationship Tracker
=============================================================
Tracks NPC names, attitudes, last interaction, and location.
Persists via to_dict/from_dict.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


@dataclass
class NPCRecord:
    """A single tracked NPC."""
    name: str
    attitude: str = "neutral"   # friendly / neutral / hostile / unknown
    location: str = ""
    notes: List[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)

    def add_note(self, note: str):
        self.notes.append(note)
        self.last_seen = time.time()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "attitude": self.attitude,
            "location": self.location,
            "notes": self.notes[-10:],  # Keep last 10
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NPCRecord":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class NPCTracker:
    """Manages a collection of NPC records."""
    npcs: Dict[str, NPCRecord] = field(default_factory=dict)

    def log(self, name: str, note: str = "", location: str = "",
            attitude: str = "") -> str:
        """Log an NPC interaction. Creates record if new."""
        key = name.lower()
        if key not in self.npcs:
            self.npcs[key] = NPCRecord(name=name)
        npc = self.npcs[key]
        if note:
            npc.add_note(note)
        if location:
            npc.location = location
        if attitude:
            npc.attitude = attitude
        npc.last_seen = time.time()
        return f"NPC logged: {name} ({npc.attitude}) at {npc.location or '?'}"

    def set_attitude(self, name: str, attitude: str) -> str:
        key = name.lower()
        npc = self.npcs.get(key)
        if not npc:
            return f"NPC '{name}' not tracked. Use 'npc log {name}' first."
        npc.attitude = attitude
        return f"{npc.name} attitude set to {attitude}."

    def remove(self, name: str) -> str:
        key = name.lower()
        npc = self.npcs.pop(key, None)
        if not npc:
            return f"NPC '{name}' not found."
        return f"NPC removed: {npc.name}"

    def list_npcs(self, attitude: str = "", limit: int = 10) -> str:
        if not self.npcs:
            return "No NPCs tracked."
        filtered = sorted(self.npcs.values(),
                          key=lambda n: n.last_seen, reverse=True)
        if attitude:
            filtered = [n for n in filtered if n.attitude == attitude]
        if not filtered:
            return f"No {attitude} NPCs." if attitude else "No NPCs tracked."
        lines = ["Tracked NPCs:"]
        markers = {"friendly": "+", "hostile": "!", "neutral": "~", "unknown": "?"}
        for npc in filtered[:limit]:
            m = markers.get(npc.attitude, "?")
            loc = f" @ {npc.location}" if npc.location else ""
            lines.append(f"  [{m}] {npc.name}{loc}")
            if npc.notes:
                lines.append(f"      Last: {npc.notes[-1]}")
        remaining = len(filtered) - limit
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")
        return "\n".join(lines)

    def get_info(self, name: str) -> str:
        key = name.lower()
        npc = self.npcs.get(key)
        if not npc:
            return f"NPC '{name}' not tracked."
        lines = [
            f"--- {npc.name} ---",
            f"Attitude: {npc.attitude}",
            f"Location: {npc.location or 'Unknown'}",
        ]
        if npc.notes:
            lines.append("Notes:")
            for note in npc.notes[-5:]:
                lines.append(f"  - {note}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.npcs.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "NPCTracker":
        tracker = cls()
        for key, npc_data in data.items():
            tracker.npcs[key] = NPCRecord.from_dict(npc_data)
        return tracker

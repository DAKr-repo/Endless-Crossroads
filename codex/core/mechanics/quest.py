"""
codex.core.mechanics.quest — Quest / Plot Thread Tracker
=========================================================

Persistent quest tracker for the DM Dashboard. Tracks active quests,
completed threads, and abandoned leads across sessions.

Follows the same to_dict/from_dict pattern as ConditionTracker and
ProgressionTracker for JSON persistence.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import hashlib


@dataclass
class Quest:
    """A single quest or plot thread."""
    id: str
    title: str
    status: str = "active"      # "active" | "completed" | "abandoned"
    notes: str = ""
    source: str = ""            # NPC or location that gave the quest
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "notes": self.notes,
            "source": self.source,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Quest":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class QuestTracker:
    """Manages a collection of quests with add/complete/list/remove."""
    quests: Dict[str, Quest] = field(default_factory=dict)

    def _make_id(self, title: str) -> str:
        """Generate a short 6-char hex ID from title + timestamp."""
        raw = f"{title}{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:6]

    def add(self, title: str, notes: str = "", source: str = "") -> str:
        """Create a new quest. Returns status message."""
        qid = self._make_id(title)
        self.quests[qid] = Quest(
            id=qid, title=title, notes=notes, source=source,
        )
        return f"Quest added [{qid}]: {title}"

    def complete(self, quest_id: str) -> str:
        """Mark a quest as completed."""
        q = self.quests.get(quest_id)
        if not q:
            return f"Quest '{quest_id}' not found."
        q.status = "completed"
        q.updated_at = time.time()
        return f"Quest completed: {q.title}"

    def abandon(self, quest_id: str) -> str:
        """Mark a quest as abandoned."""
        q = self.quests.get(quest_id)
        if not q:
            return f"Quest '{quest_id}' not found."
        q.status = "abandoned"
        q.updated_at = time.time()
        return f"Quest abandoned: {q.title}"

    def remove(self, quest_id: str) -> str:
        """Delete a quest entirely."""
        q = self.quests.pop(quest_id, None)
        if not q:
            return f"Quest '{quest_id}' not found."
        return f"Quest removed: {q.title}"

    def list_quests(self, status: str = "", limit: int = 10) -> str:
        """Return formatted quest list. Filter by status if provided."""
        filtered = [
            q for q in sorted(self.quests.values(),
                               key=lambda x: x.updated_at, reverse=True)
            if not status or q.status == status
        ]
        if not filtered:
            return "No quests tracked." if not status else f"No {status} quests."
        lines = []
        for q in filtered[:limit]:
            marker = {"active": "+", "completed": "x", "abandoned": "-"}.get(q.status, "?")
            source_str = f" (from {q.source})" if q.source else ""
            lines.append(f"  [{marker}] {q.id}: {q.title}{source_str}")
            if q.notes:
                lines.append(f"       {q.notes}")
        return "\n".join(lines)

    def active_summary(self, limit: int = 5) -> str:
        """Short summary of active quests for dashboard panel."""
        active = [q for q in self.quests.values() if q.status == "active"]
        if not active:
            return "No active quests."
        active.sort(key=lambda x: x.updated_at, reverse=True)
        lines = []
        for q in active[:limit]:
            lines.append(f"  + {q.title}")
        remaining = len(active) - limit
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            qid: q.to_dict() for qid, q in self.quests.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestTracker":
        tracker = cls()
        for qid, qdata in data.items():
            tracker.quests[qid] = Quest.from_dict(qdata)
        return tracker

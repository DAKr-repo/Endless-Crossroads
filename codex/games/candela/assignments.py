"""
codex/games/candela/assignments.py — Assignment Phase Tracker
==============================================================
Tracks the 3-act structure of Candela Obscura assignments:
Hook -> Exploration -> Climax, with phase transitions.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AssignmentTracker:
    """Tracks the 3-act structure of a Candela Obscura assignment.

    Assignments follow a fixed 3-act structure: Hook -> Exploration -> Climax.
    Each phase accumulates notes and transitions are one-way until the
    assignment is completed at the Climax phase.
    """

    PHASES = ["hook", "exploration", "climax"]

    current_phase: str = "hook"
    phase_notes: Dict[str, List[str]] = field(default_factory=lambda: {
        "hook": [], "exploration": [], "climax": []
    })
    assignment_name: str = ""
    completed: bool = False

    def advance_phase(self) -> dict:
        """Advance to the next phase in the 3-act structure.

        Returns:
            Dict with 'success' bool, 'old_phase', 'new_phase' on success,
            or 'error' string on failure.
        """
        idx = self.PHASES.index(self.current_phase)
        if idx >= len(self.PHASES) - 1:
            return {
                "success": False,
                "error": "Already in climax phase. Use 'complete_assignment' to finish.",
            }
        old = self.current_phase
        self.current_phase = self.PHASES[idx + 1]
        return {"success": True, "old_phase": old, "new_phase": self.current_phase}

    def add_note(self, note: str) -> None:
        """Add a note to the current phase.

        Args:
            note: Freeform text to record under the current phase.
        """
        self.phase_notes[self.current_phase].append(note)

    def complete(self) -> dict:
        """Mark the assignment as completed.

        Only valid when current_phase is 'climax'.

        Returns:
            Dict with 'success' bool and 'assignment' name on success,
            or 'error' string on failure.
        """
        if self.current_phase != "climax":
            return {
                "success": False,
                "error": (
                    f"Cannot complete from {self.current_phase} phase. "
                    "Must be in climax."
                ),
            }
        self.completed = True
        return {"success": True, "assignment": self.assignment_name}

    def get_summary(self) -> str:
        """Return a human-readable summary of assignment progress.

        Returns:
            Multi-line string showing phase, status, and recent notes.
        """
        lines = [f"Assignment: {self.assignment_name or 'Unnamed'}"]
        lines.append(f"Phase: {self.current_phase.upper()}")
        lines.append(f"Status: {'COMPLETED' if self.completed else 'Active'}")
        for phase in self.PHASES:
            marker = ">>>" if phase == self.current_phase and not self.completed else "   "
            notes = self.phase_notes.get(phase, [])
            lines.append(f"  {marker} {phase.title()} ({len(notes)} notes)")
            for note in notes[-3:]:  # Show last 3 notes per phase
                lines.append(f"        - {note[:60]}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for save/load."""
        return {
            "current_phase": self.current_phase,
            "phase_notes": {k: list(v) for k, v in self.phase_notes.items()},
            "assignment_name": self.assignment_name,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AssignmentTracker":
        """Deserialize from a plain dict.

        Args:
            data: Dict previously produced by to_dict().

        Returns:
            Reconstructed AssignmentTracker instance.
        """
        tracker = cls()
        tracker.current_phase = data.get("current_phase", "hook")
        tracker.phase_notes = data.get(
            "phase_notes", {"hook": [], "exploration": [], "climax": []}
        )
        tracker.assignment_name = data.get("assignment_name", "")
        tracker.completed = data.get("completed", False)
        return tracker


__all__ = ["AssignmentTracker"]

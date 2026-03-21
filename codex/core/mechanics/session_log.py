"""
codex.core.mechanics.session_log — Persistent Session Log
==========================================================
Auto-saves session notes to a markdown file on session end.
Provides last-session recap on session start.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class SessionLog:
    """Manages persistent session notes across sessions."""
    campaign_dir: Optional[Path] = None
    notes: List[str] = field(default_factory=list)
    session_number: int = 1

    def add_note(self, note: str) -> str:
        self.notes.append(note)
        return f"Note #{len(self.notes)}: {note}"

    def save(self) -> str:
        """Write all notes to campaign session log file."""
        if not self.campaign_dir:
            return "No campaign directory set — notes not persisted."
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.campaign_dir / "session_log.md"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"\n## Session {self.session_number} — {timestamp}\n"]
        for note in self.notes:
            lines.append(f"- {note}")
        lines.append("")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))

        count = len(self.notes)
        self.notes.clear()
        self.session_number += 1
        return f"Saved {count} notes to {log_path.name}."

    def load_last_recap(self) -> str:
        """Read the last session's notes from the log file."""
        if not self.campaign_dir:
            return "No campaign directory set."
        log_path = self.campaign_dir / "session_log.md"
        if not log_path.exists():
            return "No previous session log found."
        text = log_path.read_text(encoding="utf-8")
        # Find last session block
        sections = text.split("\n## Session ")
        if len(sections) < 2:
            return "No previous session entries."
        last = sections[-1]
        lines = last.strip().split("\n")
        header = lines[0] if lines else "Unknown"
        notes = [l for l in lines[1:] if l.strip().startswith("- ")]
        if not notes:
            return f"Last session ({header}): no notes recorded."
        recap = f"Last session ({header}):\n" + "\n".join(notes[:10])
        if len(notes) > 10:
            recap += f"\n  ... and {len(notes) - 10} more"
        return recap

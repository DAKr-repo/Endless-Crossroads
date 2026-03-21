"""
codex.core.mechanics.session_timer — Real-World Session Timer
==============================================================
Tracks elapsed session time and provides pacing reminders.
"""

import time
from dataclasses import dataclass


@dataclass
class SessionTimer:
    """Tracks real-world elapsed session time."""
    start_time: float = 0.0
    _paused_at: float = 0.0
    _pause_total: float = 0.0
    running: bool = False

    def start(self) -> str:
        if self.running:
            return f"Timer already running ({self.elapsed_str()})."
        self.start_time = time.time()
        self._pause_total = 0.0
        self._paused_at = 0.0
        self.running = True
        return "Session timer started."

    def stop(self) -> str:
        if not self.running:
            return "Timer not running."
        elapsed = self.elapsed_str()
        self.running = False
        return f"Session ended. Duration: {elapsed}."

    def pause(self) -> str:
        if not self.running:
            return "Timer not running."
        if self._paused_at:
            return "Already paused."
        self._paused_at = time.time()
        return f"Timer paused at {self.elapsed_str()}."

    def resume(self) -> str:
        if not self._paused_at:
            return "Timer not paused."
        self._pause_total += time.time() - self._paused_at
        self._paused_at = 0.0
        return f"Timer resumed. Elapsed: {self.elapsed_str()}."

    def elapsed_seconds(self) -> float:
        if not self.running:
            return 0.0
        now = self._paused_at if self._paused_at else time.time()
        return now - self.start_time - self._pause_total

    def elapsed_str(self) -> str:
        secs = int(self.elapsed_seconds())
        hours = secs // 3600
        mins = (secs % 3600) // 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    def pacing_check(self) -> str:
        """Return pacing reminder if thresholds are hit."""
        mins = int(self.elapsed_seconds()) // 60
        if mins >= 240:
            return "4+ hours — consider wrapping up!"
        elif mins >= 180:
            return "3 hours in — start heading toward a stopping point."
        elif mins >= 120:
            return "2 hours — good time for a break."
        elif mins >= 60:
            return "1 hour elapsed."
        return ""

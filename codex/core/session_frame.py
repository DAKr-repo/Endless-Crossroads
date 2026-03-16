"""
codex.core.session_frame — Session Architecture (WO-V62.0 Track A)
===================================================================

Wraps each play session with identity, type, and lifecycle hooks.
Supports one-shot, expedition, campaign, and freeform session types.

Session types:
  one_shot   — Single run, no world persistence, character export offered at close
  expedition — 1-2 hrs, character + quests + momentum persist, turn budget
  campaign   — Multi-session, full state persistence
  freeform   — Open-ended, full state + GRAPES mutations
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from codex.core.services.narrative_loom import ANCHOR_EVENT_TYPES


SESSION_TYPES = ("one_shot", "expedition", "campaign", "freeform")


@dataclass
class SessionFrame:
    """Wraps a play session with identity, type, and lifecycle hooks."""
    session_id: str = ""
    session_number: int = 1
    session_type: str = "campaign"
    campaign_id: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    opening_hook: str = ""
    turn_count: int = 0
    anchor_count: int = 0
    summary: str = ""

    def close(self, session_log: List[dict] = None,
              mimir_fn: Optional[Callable] = None) -> None:
        """End the session: set end time, generate summary.

        Args:
            session_log: List of event dicts recorded during the session.
            mimir_fn: Optional AI generation function(prompt, context) -> str.
        """
        self.ended_at = datetime.now().isoformat()
        if session_log:
            self.anchor_count = sum(
                1 for e in session_log if e.get("type") in ANCHOR_EVENT_TYPES
            )
            self.summary = _generate_session_summary(session_log, mimir_fn)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "session_id": self.session_id,
            "session_number": self.session_number,
            "session_type": self.session_type,
            "campaign_id": self.campaign_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "opening_hook": self.opening_hook,
            "turn_count": self.turn_count,
            "anchor_count": self.anchor_count,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionFrame":
        """Deserialize from a dict (as produced by to_dict)."""
        return cls(
            session_id=data.get("session_id", ""),
            session_number=data.get("session_number", 1),
            session_type=data.get("session_type", "campaign"),
            campaign_id=data.get("campaign_id"),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at"),
            opening_hook=data.get("opening_hook", ""),
            turn_count=data.get("turn_count", 0),
            anchor_count=data.get("anchor_count", 0),
            summary=data.get("summary", ""),
        )


def _generate_session_summary(session_log: List[dict],
                               mimir_fn: Optional[Callable] = None) -> str:
    """Generate a 1-sentence summary of the session from its log.

    Attempts Mimir generation first; falls back to a deterministic
    summary built from event counts.

    Args:
        session_log: Structured event dicts from the session chronicle.
        mimir_fn: Optional AI generation function(prompt, context) -> str.

    Returns:
        A single-sentence summary string.
    """
    if not session_log:
        return "An uneventful session."

    # Count key events
    kills = sum(1 for e in session_log if e.get("type") == "kill")
    deaths = [e.get("name", "?") for e in session_log if e.get("type") == "party_death"]
    rooms = sum(1 for e in session_log if e.get("type") == "room_entered")
    anchors = [e for e in session_log if e.get("type") in ANCHOR_EVENT_TYPES]

    if mimir_fn:
        anchor_summary = ", ".join(a.get("type", "?") for a in anchors[:5])
        prompt = (
            f"Write exactly one sentence summarizing this game session: "
            f"{kills} enemies slain, {rooms} rooms explored, "
            f"{len(deaths)} fallen allies{', key moments: ' + anchor_summary if anchor_summary else ''}. "
            f"Be dramatic and specific."
        )
        try:
            import concurrent.futures
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = pool.submit(mimir_fn, prompt, "")
            try:
                result = future.result(timeout=10)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            if result and len(result) > 10:
                return result.strip().split("\n")[0]  # First line only
        except Exception:
            pass

    # Fallback: deterministic summary
    parts = []
    if kills > 0:
        parts.append(f"{kills} enemies slain")
    if rooms > 0:
        parts.append(f"{rooms} rooms explored")
    if deaths:
        parts.append(f"{', '.join(deaths)} fell")
    if not parts:
        parts.append("an uneventful delve")
    return "The party " + ", ".join(parts) + "."


# =========================================================================
# Opening Hooks
# =========================================================================

ONE_SHOT_HOOKS = [
    "The posting board at the crossroads has one last notice, pinned with a rusted nail.",
    "A stranger presses a map into your hands and vanishes into the crowd.",
    "The tavern keeper slides a key across the bar. 'Someone left this for you.'",
    "Rain hammers the cobblestones. A door you've never noticed stands ajar.",
]

EXPEDITION_HOOKS = [
    "Dawn breaks cold. Your supplies are packed. The wild awaits.",
    "The scout's report is grim: the path ahead is clear, but not for long.",
    "You check your gear one last time. The descent begins.",
]

CAMPAIGN_HOOKS = [
    "Another day in the depths. The darkness remembers your name.",
    "The world has not forgotten what you did. Neither have its enemies.",
]

FREEFORM_HOOKS = [
    "The world turns. What will you make of it?",
    "No map. No mission. Just the road and whatever lies beyond.",
]

_HOOK_POOLS: Dict[str, List[str]] = {
    "one_shot": ONE_SHOT_HOOKS,
    "expedition": EXPEDITION_HOOKS,
    "campaign": CAMPAIGN_HOOKS,
    "freeform": FREEFORM_HOOKS,
}


def generate_opening_hook(
    session_type: str = "campaign",
    prior_sessions: Optional[List[dict]] = None,
    momentum_ledger=None,
    location: str = "unknown",
    mimir_fn: Optional[Callable] = None,
) -> str:
    """Generate a session-opening narrative hook.

    Priority order:
      1. Mimir generation seeded from prior session summaries.
      2. Momentum-based hook from dominant trend.
      3. Random fallback from the session-type hook pool.

    Args:
        session_type: One of SESSION_TYPES.
        prior_sessions: List of prior SessionFrame.to_dict() dicts.
        momentum_ledger: Optional MomentumLedger with get_dominant_trend().
        location: Current location name for momentum lookup.
        mimir_fn: Optional AI generation function(prompt, context) -> str.

    Returns:
        A narrative hook string.
    """
    import random

    # Try Mimir generation from prior session context
    if mimir_fn and prior_sessions:
        context_lines = []
        for s in prior_sessions[-3:]:
            summary = s.get("summary", "")
            num = s.get("session_number", "?")
            if summary:
                context_lines.append(f"Session {num}: {summary}")
        if context_lines:
            prompt = (
                "Write a 1-2 sentence opening hook for a new game session. "
                "Reference what happened before:\n" + "\n".join(context_lines)
            )
            try:
                import concurrent.futures
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = pool.submit(mimir_fn, prompt, "")
                try:
                    result = future.result(timeout=10)
                finally:
                    pool.shutdown(wait=False, cancel_futures=True)
                if result and len(result) > 10:
                    return result.strip()
            except Exception:
                pass

    # Try momentum-based hook
    if momentum_ledger:
        try:
            dominant = momentum_ledger.get_dominant_trend(location)
            if dominant and dominant[1] >= 7.0:
                cat, weight = dominant
                from codex.core.services.momentum_handler import TREND_MUTATIONS
                mapping = TREND_MUTATIONS.get(cat, {})
                narr_key = "narrative_positive" if weight > 0 else "narrative_negative"
                narr = mapping.get(narr_key, "")
                if narr:
                    return f"{narr} But something stirs beneath the surface."
        except Exception:
            pass

    # Fallback: random hook from pool
    pool = _HOOK_POOLS.get(session_type, CAMPAIGN_HOOKS)
    return random.choice(pool)


# =========================================================================
# Session Epilogue
# =========================================================================

_FALLBACK_EPILOGUES: Dict[str, str] = {
    "party_death": "Word of the fallen spreads quietly through town. A candle is lit at the shrine.",
    "doom_threshold": "The ground trembles faintly. Something stirs in the deep places.",
    "companion_fell": "A companion's empty bedroll is folded and placed by the fire. No one speaks of it.",
    "zone_breakthrough": "Beyond the threshold, the air changes. Something ancient exhales.",
}


def generate_epilogue(
    session_log: List[dict],
    session_type: str = "campaign",
    momentum_ledger=None,
    mimir_fn: Optional[Callable] = None,
) -> Optional[str]:
    """Generate a 'what happens after you leave' vignette.

    Returns None for one-shot sessions or when no anchor events occurred.

    Args:
        session_log: Structured event dicts from the session chronicle.
        session_type: One of SESSION_TYPES.
        momentum_ledger: Optional MomentumLedger with get_dominant_trend().
        mimir_fn: Optional AI generation function(prompt, context) -> str.

    Returns:
        An epilogue string, or None if not applicable.
    """
    if session_type == "one_shot":
        return None

    anchors = [e for e in session_log if e.get("type") in ANCHOR_EVENT_TYPES]
    if not anchors:
        return None

    if mimir_fn:
        context_parts = []
        context_parts.append(f"Key events: {', '.join(a['type'] for a in anchors[-5:])}")
        if momentum_ledger:
            try:
                dominant = momentum_ledger.get_dominant_trend("all")
                if dominant:
                    context_parts.append(f"Dominant trend: {dominant[0]} ({dominant[1]:.1f})")
            except Exception:
                pass

        prompt = (
            "Write a 2-3 sentence epilogue for a game session. Describe what happens "
            "in the world after the player leaves — NPCs reacting, consequences unfolding, "
            "hints of what's to come. Do NOT address the player directly.\n\n"
            + "\n".join(context_parts)
        )
        try:
            import concurrent.futures
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = pool.submit(mimir_fn, prompt, "")
            try:
                result = future.result(timeout=10)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            if result and len(result) > 20:
                return result.strip()
        except Exception:
            pass

    # Fallback: static epilogues based on most dramatic anchor
    for anchor_type, epilogue in _FALLBACK_EPILOGUES.items():
        if any(a.get("type") == anchor_type for a in anchors):
            return epilogue

    return None


# =========================================================================
# Expedition Timer
# =========================================================================

EXPEDITION_SUPPLY_STAGES = [
    (0.5, "[dim]Your pack feels lighter than it should.[/]"),
    (0.7, "[yellow]Your water skin is nearly empty. The jerky is gone.[/]"),
    (0.8, "[bold yellow]Supplies run low. You should consider returning.[/]"),
    (0.9, "[bold red]Your torch gutters. Your stomach cramps. Time is running out.[/]"),
    (1.0, "[bold red]Your rations are exhausted. You must return or face consequences.[/]"),
]


class ExpeditionTimer:
    """Turn-budget tracker for expedition sessions.

    Tracks elapsed turns against a fixed budget and emits supply-pressure
    narration messages at configurable thresholds.
    """

    def __init__(self, turn_budget: int = 50):
        """Initialise the timer.

        Args:
            turn_budget: Maximum turns before supplies are exhausted.
                         Pass 0 to disable the timer (unlimited turns).
        """
        self.budget = turn_budget
        self.elapsed = 0
        self._last_stage: float = 0.0

    def tick(self) -> Optional[str]:
        """Advance one turn.

        Returns:
            A Rich-formatted supply narration string when a new stage
            threshold is crossed, otherwise None.
        """
        self.elapsed += 1
        if self.budget <= 0:
            return None
        ratio = self.elapsed / self.budget
        for threshold, message in reversed(EXPEDITION_SUPPLY_STAGES):
            if ratio >= threshold and threshold > self._last_stage:
                self._last_stage = threshold
                return message
        return None

    @property
    def exhausted(self) -> bool:
        """True when elapsed turns meet or exceed the budget."""
        return self.budget > 0 and self.elapsed >= self.budget

    @property
    def ratio(self) -> float:
        """Elapsed turns as a fraction of the budget (0.0–1.0+)."""
        if self.budget <= 0:
            return 0.0
        return self.elapsed / self.budget

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for save persistence."""
        return {
            "budget": self.budget,
            "elapsed": self.elapsed,
            "last_stage": self._last_stage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExpeditionTimer":
        """Deserialize from a dict (as produced by to_dict)."""
        t = cls(turn_budget=data.get("budget", 50))
        t.elapsed = data.get("elapsed", 0)
        t._last_stage = data.get("last_stage", 0.0)
        return t


# =========================================================================
# Session Counter Persistence
# =========================================================================

def get_next_session_number(campaign_id: str, saves_dir: Path = None) -> int:
    """Get the next session number for a campaign.

    Reads the persisted counter and returns counter + 1.
    Returns 1 for unknown campaigns or empty campaign_id.

    Args:
        campaign_id: Unique campaign identifier string.
        saves_dir: Directory containing session_counters.json.
                   Defaults to Path("saves").

    Returns:
        The next session number (1-indexed).
    """
    if not campaign_id:
        return 1
    if saves_dir is None:
        saves_dir = Path("saves")
    counter_file = saves_dir / "session_counters.json"
    counters: dict = {}
    if counter_file.exists():
        try:
            counters = json.loads(counter_file.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return counters.get(campaign_id, 0) + 1


def save_session_counter(campaign_id: str, session_number: int,
                         saves_dir: Path = None) -> None:
    """Persist session counter for a campaign.

    Writes the current session number so future calls to
    get_next_session_number() return session_number + 1.

    Args:
        campaign_id: Unique campaign identifier string.
        session_number: The session number just completed.
        saves_dir: Directory to write session_counters.json.
                   Defaults to Path("saves").
    """
    if not campaign_id:
        return
    if saves_dir is None:
        saves_dir = Path("saves")
    saves_dir.mkdir(parents=True, exist_ok=True)
    counter_file = saves_dir / "session_counters.json"
    counters: dict = {}
    if counter_file.exists():
        try:
            counters = json.loads(counter_file.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    counters[campaign_id] = session_number
    counter_file.write_text(json.dumps(counters, indent=2))

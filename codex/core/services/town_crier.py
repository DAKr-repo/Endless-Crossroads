"""
Town Crier — Civic Pulse & Narrative Rumor System.
=====================================================

Follows the DoomClock threshold pattern: civic events trigger when the
tick counter reaches defined thresholds.  Ticks advance after each
dungeon run (death or extraction).

Components:
  - CivicPulse: tick-driven event engine stored in meta_state
  - CrierVoice: narrative generator that converts CivicEvents into
    in-world rumors (via Mimir or fallback templates)
  - WorldHistory: universe-gated persistent event ledger (WO-V5.1)
  - AMD-05: sub_location support for ward-aware rumors
"""

import json
import random as _rng_module
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional


# =========================================================================
# ENUMS & DATA
# =========================================================================

class CivicCategory(Enum):
    TRADE = "trade"
    SECURITY = "security"
    RUMOR = "rumor"
    INFRASTRUCTURE = "infrastructure"
    MORALE = "morale"


@dataclass
class CivicEvent:
    """A civic milestone that fires when the tick counter reaches threshold."""
    threshold: int
    category: CivicCategory
    event_tag: str              # System-agnostic: "MERCHANT_ARRIVAL"
    repeatable: bool = False
    repeat_interval: int = 0    # Ticks between repeats (0 = no repeat)


# =========================================================================
# CIVIC PULSE ENGINE
# =========================================================================

@dataclass
class CivicPulse:
    """Tick-driven civic event tracker.

    Ticks advance after each dungeon run (death or extraction).
    Stored in meta_state so it survives the death loop.
    """
    current_tick: int = 0
    events: List[CivicEvent] = field(default_factory=list)
    triggered_history: List[dict] = field(default_factory=list)
    sub_location: str = ""  # AMD-05: ward-level location scope
    universe_id: str = ""   # WO-V5.1: universe scope for event isolation
    _world_history: Optional["WorldHistory"] = field(default=None, repr=False)

    def attach_history(self, history: "WorldHistory") -> None:
        """Attach a WorldHistory ledger for persistent event recording."""
        self._world_history = history

    def advance(self, ticks: int = 1) -> List[CivicEvent]:
        """Advance the tick counter and return newly triggered events."""
        newly_triggered: List[CivicEvent] = []
        old_tick = self.current_tick
        self.current_tick += ticks

        for event in self.events:
            if event.threshold > old_tick and event.threshold <= self.current_tick:
                newly_triggered.append(event)
                entry = {
                    "tick": self.current_tick,
                    "event_tag": event.event_tag,
                    "category": event.category.value,
                }
                self.triggered_history.append(entry)
                # Persist to universe-gated ledger (WO-V5.1)
                if self._world_history and self.universe_id:
                    self._world_history.record_event(self.universe_id, entry)
            elif event.repeatable and event.repeat_interval > 0:
                # Check if a repeat interval was crossed
                if old_tick >= event.threshold:
                    last_fire = event.threshold
                    while last_fire + event.repeat_interval <= self.current_tick:
                        last_fire += event.repeat_interval
                    prev_last = event.threshold
                    while prev_last + event.repeat_interval <= old_tick:
                        prev_last += event.repeat_interval
                    if last_fire > prev_last:
                        newly_triggered.append(event)
                        entry = {
                            "tick": self.current_tick,
                            "event_tag": event.event_tag,
                            "category": event.category.value,
                            "repeat": True,
                        }
                        self.triggered_history.append(entry)
                        if self._world_history and self.universe_id:
                            self._world_history.record_event(self.universe_id, entry)

        return newly_triggered

    def get_active_by_category(self, cat: CivicCategory) -> List[dict]:
        """Return triggered events filtered by category."""
        return [h for h in self.triggered_history
                if h.get("category") == cat.value]

    def handle_cross_module(self, event: dict):
        """React to events from other game modules (AMD-02 / WO-V8.1)."""
        event_type = event.get("event_type", "")
        if event_type == "BOSS_SLAIN":
            self.advance(1)  # Security improves
        elif event_type == EVENT_FACTION_CLOCK_TICK:
            # Record faction clock tick as a synthetic civic event (WO-V8.1)
            entry = {
                "tick": self.current_tick,
                "event_tag": "FACTION_BULLETIN",
                "category": CivicCategory.SECURITY.value,
                "faction_name": event.get("faction_name", "Unknown"),
                "agenda": event.get("agenda", ""),
                "filled": event.get("filled", 0),
                "segments": event.get("segments", 0),
            }
            self.triggered_history.append(entry)
            if self._world_history and self.universe_id:
                self._world_history.record_event(self.universe_id, entry)

    # ─────────────────────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "current_tick": self.current_tick,
            "triggered_history": self.triggered_history,
            "sub_location": self.sub_location,
            "universe_id": self.universe_id,
            "events": [
                {
                    "threshold": e.threshold,
                    "category": e.category.value,
                    "event_tag": e.event_tag,
                    "repeatable": e.repeatable,
                    "repeat_interval": e.repeat_interval,
                }
                for e in self.events
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CivicPulse":
        events = []
        for ed in data.get("events", []):
            events.append(CivicEvent(
                threshold=ed["threshold"],
                category=CivicCategory(ed["category"]),
                event_tag=ed["event_tag"],
                repeatable=ed.get("repeatable", False),
                repeat_interval=ed.get("repeat_interval", 0),
            ))
        return cls(
            current_tick=data.get("current_tick", 0),
            events=events,
            triggered_history=data.get("triggered_history", []),
            sub_location=data.get("sub_location", ""),
            universe_id=data.get("universe_id", ""),
        )


# =========================================================================
# BURNWILLOW CIVIC EVENTS (default table)
# =========================================================================

BURNWILLOW_CIVIC_EVENTS: List[CivicEvent] = [
    CivicEvent(2, CivicCategory.TRADE, "SCRAP_MERCHANT"),
    CivicEvent(3, CivicCategory.RUMOR, "DEEP_FLOOR_RUMOR"),
    CivicEvent(5, CivicCategory.SECURITY, "PATROL_REINFORCED"),
    CivicEvent(7, CivicCategory.MORALE, "SURVIVOR_STORIES"),
    CivicEvent(10, CivicCategory.INFRASTRUCTURE, "FORGE_UNLOCKED"),
    CivicEvent(15, CivicCategory.TRADE, "RARE_MERCHANT", repeatable=True, repeat_interval=10),
    CivicEvent(20, CivicCategory.INFRASTRUCTURE, "TEMPLE_RESTORED"),
]


# =========================================================================
# CRIER VOICE — NARRATIVE GENERATOR (AMD-02)
# =========================================================================

BURNWILLOW_CRIER_TEMPLATES: Dict[str, List[str]] = {
    "SCRAP_MERCHANT": [
        "A hooded trader has set up shop near the threshold. Rare scraps, they say.",
        "Word is, a salvager crawled out of the deep with a cart full of iron.",
    ],
    "DEEP_FLOOR_RUMOR": [
        "Whispers in the tavern: something stirs below the third floor.",
        "An old delver swears he heard singing from the depths.",
    ],
    "PATROL_REINFORCED": [
        "The militia doubled the watch last night. Something stirred below.",
        "Guards pace the threshold with fresh torches. They seem on edge.",
    ],
    "SURVIVOR_STORIES": [
        "A grizzled survivor shares tales by the fire. Morale lifts.",
        "Children gather to hear stories of the brave delvers who returned.",
    ],
    "FORGE_UNLOCKED": [
        "The old forge breathes again. Emberhome can now refit heavy arms.",
        "Sparks fly from the reopened smithy. The sound of hammers echoes.",
    ],
    "RARE_MERCHANT": [
        "A mysterious merchant arrives with wares from the far reaches.",
        "Strange goods from unknown lands appear at the market stalls.",
    ],
    "TEMPLE_RESTORED": [
        "The temple bells ring for the first time in years. Hope renews.",
        "Priests light the altar fires. Healing services resume.",
    ],
}


# =========================================================================
# G.R.A.P.E.S. RUMOR TEMPLATES (WO-V8.1)
# =========================================================================

GRAPES_RUMOR_TEMPLATES: Dict[str, List[str]] = {
    "scarcity": [
        "Traders whisper that {resource} is {abundance}. {trade_note}.",
        "The market stalls are thin on {resource} — {trade_note}.",
    ],
    "taboo": [
        "Beware: {prohibition}. Those caught face {punishment}.",
        "The elders forbid {prohibition}. Its origin: {origin}.",
    ],
    "landmark": [
        "Scouts report movement near {name}. The {terrain} there is treacherous.",
        "A survivor from {name} describes {feature}.",
    ],
    "heresy": [
        "Hushed talk of {heresy} spreads through the back alleys.",
        "A zealot was seen preaching {heresy} near the gate.",
    ],
}


# =========================================================================
# FACTION BULLETIN TEMPLATES (WO-V8.1)
# =========================================================================

FACTION_BULLETIN_TEMPLATES: List[str] = [
    "URGENT: {faction_name} advances their agenda — {agenda}. Clock: {filled}/{segments}.",
    "Breaking: The {faction_name} make their move. {agenda}. [{filled}/{segments}]",
]


class CrierVoice:
    """Convert system state changes into in-world narrative.

    If Mimir is available, generates dynamic prose.
    If not, uses fallback templates with random selection.
    """

    def __init__(
        self,
        mimir_fn: Optional[Callable] = None,
        system_theme: str = "default",
        universe_manager=None,
        grapes_profile: Optional[dict] = None,
    ):
        self._mimir = mimir_fn
        self._system_theme = system_theme
        self._universe_mgr = universe_manager
        self._grapes: Optional[dict] = grapes_profile
        self._fallback_templates: Dict[str, List[str]] = {}

    def set_grapes_profile(self, profile_dict: dict) -> None:
        """Hot-swap the active G.R.A.P.E.S. profile for world-aware rumors."""
        self._grapes = profile_dict

    def register_templates(self, system_id: str, templates: Dict[str, List[str]]):
        """Register system-specific fallback templates."""
        self._fallback_templates.update(templates)

    def narrate(self, event: CivicEvent, context: dict) -> str:
        """Convert a CivicEvent into a narrative rumor string."""
        # Try Mimir first
        if self._mimir:
            try:
                prompt = (
                    f"Write a short in-world rumor (1-2 sentences) for a "
                    f"{self._system_theme} setting. Event: {event.event_tag}, "
                    f"Category: {event.category.value}. Context: {context}"
                )
                # Append G.R.A.P.E.S. world context when available (WO-V8.1)
                if self._grapes:
                    snippet = _build_grapes_snippet(self._grapes)
                    if snippet:
                        prompt += f" World context: {snippet}"
                result = self._mimir(prompt, "")
                if result and len(result) > 10:
                    return result.strip()
            except Exception:
                pass

        # Try G.R.A.P.E.S. procedural rumor before static templates (WO-V8.1)
        grapes_rumor = self._grapes_rumor(event)
        if grapes_rumor:
            return grapes_rumor

        # Fallback to static templates
        templates = self._fallback_templates.get(event.event_tag, [])
        if templates:
            return _rng_module.choice(templates)

        return f"[{event.category.value.upper()}] {event.event_tag.replace('_', ' ').title()}"

    # ─────────────────────────────────────────────────────────────
    # G.R.A.P.E.S. procedural rumors (WO-V8.1)
    # ─────────────────────────────────────────────────────────────

    def _grapes_rumor(self, event: CivicEvent) -> Optional[str]:
        """Generate a rumor from G.R.A.P.E.S. data matching the event category.

        Returns None if no grapes data or no matching entries.
        """
        if not self._grapes:
            return None

        # Map CivicCategory → G.R.A.P.E.S. pool + template key
        category_map: Dict[CivicCategory, List[tuple]] = {
            CivicCategory.TRADE: [("economics", "scarcity")],
            CivicCategory.MORALE: [("economics", "scarcity")],
            CivicCategory.SECURITY: [("social", "taboo"), ("geography", "landmark")],
            CivicCategory.RUMOR: [("religion", "heresy"), ("social", "taboo")],
            CivicCategory.INFRASTRUCTURE: [("geography", "landmark")],
        }

        pools = category_map.get(event.category, [])
        for grapes_key, template_key in pools:
            entries = self._grapes.get(grapes_key, [])
            if not entries or not isinstance(entries, list):
                continue
            templates = GRAPES_RUMOR_TEMPLATES.get(template_key, [])
            if not templates:
                continue
            entry = _rng_module.choice(entries)
            if not isinstance(entry, dict):
                continue
            try:
                return _rng_module.choice(templates).format_map(entry)
            except KeyError:
                continue
        return None

    def generate_grapes_rumors(self, limit: int = 3) -> List[str]:
        """Produce standalone rumors purely from G.R.A.P.E.S. data.

        Cycles through scarcity, taboo, landmark, heresy pools.
        Returns an empty list if no grapes data is set.
        """
        if not self._grapes:
            return []

        rumors: List[str] = []
        pools = [
            ("economics", "scarcity"),
            ("social", "taboo"),
            ("geography", "landmark"),
            ("religion", "heresy"),
        ]

        for grapes_key, template_key in pools:
            if len(rumors) >= limit:
                break
            entries = self._grapes.get(grapes_key, [])
            if not entries or not isinstance(entries, list):
                continue
            templates = GRAPES_RUMOR_TEMPLATES.get(template_key, [])
            if not templates:
                continue
            for entry in entries:
                if len(rumors) >= limit:
                    break
                if not isinstance(entry, dict):
                    continue
                try:
                    rumors.append(_rng_module.choice(templates).format_map(entry))
                except KeyError:
                    continue
        return rumors

    def narrate_bulletin(self, payload: dict) -> str:
        """Format a faction clock tick into a narrative bulletin (WO-V8.1).

        Args:
            payload: Dict with faction_name, agenda, filled, segments.

        Returns:
            Formatted bulletin string.
        """
        try:
            return _rng_module.choice(FACTION_BULLETIN_TEMPLATES).format_map(payload)
        except (KeyError, IndexError):
            faction = payload.get("faction_name", "Unknown")
            agenda = payload.get("agenda", "")
            filled = payload.get("filled", "?")
            segments = payload.get("segments", "?")
            return f"[BULLETIN] {faction}: {agenda} [{filled}/{segments}]"

    def get_rumors(self, universe_id: str, history: "WorldHistory",
                   limit: int = 5) -> List[str]:
        """Retrieve narrated rumors from the active universe's history only.

        Implements the WO-V5.1 isolation gate: events from other universes
        are silently discarded.

        Args:
            universe_id: The active universe to retrieve rumors for.
            history: The WorldHistory persistent ledger.
            limit: Maximum number of recent rumors to return.

        Returns:
            List of narrated rumor strings (most recent first).
        """
        import random as _rng
        events = history.get_events(universe_id, limit=limit)
        rumors: List[str] = []
        for entry in events:
            tag = entry.get("event_tag", "")
            cat = entry.get("category", "rumor")
            # Build a lightweight CivicEvent for narration
            try:
                civic = CivicEvent(
                    threshold=0,
                    category=CivicCategory(cat),
                    event_tag=tag,
                )
            except ValueError:
                civic = CivicEvent(0, CivicCategory.RUMOR, tag)
            rumors.append(self.narrate(civic, {"universe_id": universe_id}))
        return rumors

    def should_relay(self, event: dict, target_module: str) -> bool:
        """The Tuner: check if source and target share a universe (AMD-03)."""
        if not self._universe_mgr:
            return False
        source = event.get("_source_module", "unknown")
        return self._universe_mgr.are_linked(source, target_module)


# =========================================================================
# MODULE-LEVEL HELPERS (WO-V8.1)
# =========================================================================

def _build_grapes_snippet(grapes: dict) -> str:
    """Build a concise world-context snippet from G.R.A.P.E.S. data."""
    parts: List[str] = []
    econ = grapes.get("economics", [])
    if econ and isinstance(econ, list):
        for e in econ[:2]:
            if isinstance(e, dict):
                parts.append(f"{e.get('resource', '?')} is {e.get('abundance', '?')}")
    social = grapes.get("social", [])
    if social and isinstance(social, list):
        for s in social[:1]:
            if isinstance(s, dict):
                parts.append(f"Taboo: {s.get('prohibition', '?')}")
    geo = grapes.get("geography", [])
    if geo and isinstance(geo, list):
        for g in geo[:1]:
            if isinstance(g, dict):
                parts.append(f"Landmark: {g.get('name', '?')}")
    return "; ".join(parts)


def broadcast_clock_tick(broadcaster, clock, faction: dict) -> None:
    """Helper for game loops to broadcast a faction clock tick event.

    Call after clock.tick() or clock.advance() triggers an event.

    Args:
        broadcaster: A GlobalBroadcastManager instance.
        clock: The UniversalClock that was ticked.
        faction: Dict with faction_name, agenda keys.
    """
    from codex.core.services.broadcast import GlobalBroadcastManager

    if not isinstance(broadcaster, GlobalBroadcastManager):
        return

    payload = {
        "faction_name": faction.get("faction_name", faction.get("name", "Unknown")),
        "agenda": faction.get("agenda", ""),
        "filled": getattr(clock, "filled", 0),
        "segments": getattr(clock, "segments", 0),
        "clock_name": getattr(clock, "name", ""),
    }
    broadcaster.broadcast_cross_module(
        "grapes", EVENT_FACTION_CLOCK_TICK, payload,
        universe_id=faction.get("universe_id", ""),
    )


# Well-known event type for faction clock ticks (WO-V8.1)
EVENT_FACTION_CLOCK_TICK = "FACTION_CLOCK_TICK"


# =========================================================================
# WORLD HISTORY — PERSISTENT EVENT LEDGER (WO-V5.1)
# =========================================================================

class WorldHistory:
    """Universe-gated persistent event ledger (WO-V5.1).

    Events are organized by universe_id in state/world_history.json.
    The Town Crier only retrieves rumors from the active universe.
    """

    def __init__(self, path: Optional[Path] = None):
        from codex.paths import WORLD_HISTORY_FILE, safe_save_json as _ssj
        self._path: Path = path or WORLD_HISTORY_FILE
        self._safe_save = _ssj
        self._data: dict = self.load()

    # ── persistence ──────────────────────────────────────────────────

    def load(self) -> dict:
        """Load the history ledger from disk."""
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"universes": {}}
        return {"universes": {}}

    def save(self) -> None:
        """Persist the ledger to disk via safe_save_json."""
        self._safe_save(self._path, self._data)

    # ── public API ───────────────────────────────────────────────────

    def record_event(self, universe_id: str, event_data: dict) -> None:
        """Append an event with timestamp to a universe's event list."""
        universes = self._data.setdefault("universes", {})
        events = universes.setdefault(universe_id, [])
        entry = dict(event_data)
        entry.setdefault("timestamp", datetime.now().isoformat())
        events.append(entry)
        self.save()

    def get_events(self, universe_id: str, limit: int = 10) -> List[dict]:
        """Return the last *limit* events for this universe only."""
        events = self._data.get("universes", {}).get(universe_id, [])
        return events[-limit:]

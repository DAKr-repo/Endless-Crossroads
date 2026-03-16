"""
GlobalBroadcastManager — Observer-pattern event bus for C.O.D.E.X.
===================================================================

Thread-safe broadcast system with optional async support.
Follows the DoomClock.advance() return-style pattern.

Features:
  - Subscribe/broadcast with string event types
  - system_theme tag for listener-side skinning
  - Thread-safe sync listeners (threading.Lock)
  - Optional asyncio.Queue for async listeners
  - Cross-module broadcast with universe_id isolation (AMD-02/03)
  - Crossroad Transmission logging for cross-module events (WO 8.2)
"""

import asyncio
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# ── Event type constants ──────────────────────────────────────────────
EVENT_ZONE_COMPLETE = "ZONE_COMPLETE"
EVENT_ZONE_TRANSITION = "ZONE_TRANSITION"
EVENT_WORLD_MAP_TRAVEL = "WORLD_MAP_TRAVEL"


# Log cross-module events to codex_builder.log
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CROSSROAD_LOG = _PROJECT_ROOT / "codex_builder.log"


def _log_crossroad_transmission(source: str, event_type: str,
                                universe_id: str, listener_count: int) -> None:
    """Append a Crossroad Transmission entry to the build log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(_CROSSROAD_LOG, "a") as f:
            f.write(
                f"[{timestamp}] CROSSROAD TRANSMISSION: "
                f"{source} -> {event_type} "
                f"(universe={universe_id or 'global'}, "
                f"listeners={listener_count})\n"
            )
    except Exception:
        pass  # Logging must never break the bus


class GlobalBroadcastManager:
    """Central event bus for the C.O.D.E.X. platform.

    Attributes:
        system_theme: Metadata tag indicating the active system
                      ("burnwillow", "dnd5e", "crown", etc.).
                      Listeners use this to decide how to skin events.
    """

    def __init__(self, system_theme: str = "default"):
        self.system_theme: str = system_theme
        self._listeners: dict[str, list[Callable]] = {}
        self._async_queues: dict[str, list[asyncio.Queue]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Sync subscribe / broadcast
    # ------------------------------------------------------------------

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Register a synchronous callback for *event_type*."""
        with self._lock:
            self._listeners.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """Remove a previously registered callback. Returns True if found."""
        with self._lock:
            cbs = self._listeners.get(event_type, [])
            if callback in cbs:
                cbs.remove(callback)
                return True
        return False

    def broadcast(self, event_type: str, payload: dict) -> list[dict]:
        """Fire *event_type* to all sync listeners.

        Returns a list of results from listeners that returned non-None.
        """
        results: list[dict] = []
        with self._lock:
            callbacks = list(self._listeners.get(event_type, []))

        for cb in callbacks:
            try:
                result = cb(payload)
                if result is not None:
                    results.append(result)
            except Exception:
                pass  # Listeners must not break the bus
        return results

    # ------------------------------------------------------------------
    # Async support
    # ------------------------------------------------------------------

    def subscribe_async(self, event_type: str) -> asyncio.Queue:
        """Return an asyncio.Queue that receives payloads for *event_type*."""
        q: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._async_queues.setdefault(event_type, []).append(q)
        return q

    def broadcast_async(self, event_type: str, payload: dict) -> None:
        """Enqueue *payload* to all async subscribers of *event_type*."""
        with self._lock:
            queues = list(self._async_queues.get(event_type, []))

        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # Drop if consumer is behind

    # ------------------------------------------------------------------
    # Cross-module broadcast (AMD-02 / AMD-03)
    # ------------------------------------------------------------------

    def broadcast_cross_module(
        self,
        source_module: str,
        event_type: str,
        payload: dict,
        universe_id: str = "",
    ) -> list[dict]:
        """Broadcast from one module for other modules to react to.

        Enriches the payload with ``_source_module`` and ``_universe_id``
        so that listeners can filter by universe scope.

        Args:
            source_module: Originating module id (e.g. "burnwillow").
            event_type: Semantic event name (e.g. "BOSS_SLAIN").
            payload: Arbitrary event data.
            universe_id: Scope identifier — listeners from a different
                         universe should silently discard the event.

        Returns:
            Aggregated listener results (same as :meth:`broadcast`).
        """
        enriched = {
            **payload,
            "_source_module": source_module,
            "_universe_id": universe_id,
        }
        results = self.broadcast(event_type, enriched)

        # Log every cross-module event as a Crossroad Transmission
        with self._lock:
            listener_count = len(self._listeners.get(event_type, []))
        _log_crossroad_transmission(source_module, event_type,
                                    universe_id, listener_count)

        return results

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Well-known event types
    # ------------------------------------------------------------------

    # Navigation: emitted when the map display should update on remote clients.
    EVENT_MAP_UPDATE = "MAP_UPDATE"
    # Memory: emitted for high-impact shard creation.
    EVENT_HIGH_IMPACT = "HIGH_IMPACT_DECISION"
    # Trait: emitted when a trait is activated.
    EVENT_TRAIT_ACTIVATED = "TRAIT_ACTIVATED"
    # Faction Clock: emitted when a G.R.A.P.E.S. faction clock ticks (WO-V8.1).
    EVENT_FACTION_CLOCK_TICK = "FACTION_CLOCK_TICK"
    # Civic Event: emitted for settlement-level civic happenings (WO-V12.1).
    EVENT_CIVIC_EVENT = "CIVIC_EVENT"
    # NPC Witness: emitted when an NPC records a memory (WO-V12.1).
    EVENT_NPC_WITNESS = "NPC_WITNESS"
    # RAG Invalidation: emitted when FAISS indices are rebuilt (WO-V33.0).
    EVENT_RAG_INVALIDATE = "RAG_INDEX_INVALIDATED"
    # Initiative Advance: emitted when DM advances turn order (WO-V35.0).
    EVENT_INITIATIVE_ADVANCE = "INITIATIVE_ADVANCE"
    # Condition Change: emitted when a condition is applied/removed (WO-V35.0).
    EVENT_CONDITION_CHANGE = "CONDITION_CHANGE"
    # Rest Complete: emitted when a rest finishes via bridge or dashboard (WO-V35.0).
    EVENT_REST_COMPLETE = "REST_COMPLETE"
    # Session Recap: emitted when a session recap is generated (WO-V37.0).
    EVENT_SESSION_RECAP = "SESSION_RECAP"
    # Zone Complete: emitted when all exit conditions for a zone are met.
    EVENT_ZONE_COMPLETE = "ZONE_COMPLETE"
    # Zone Transition: emitted when the party moves from one zone to the next.
    EVENT_ZONE_TRANSITION = "ZONE_TRANSITION"
    # World Map Travel: emitted when the party travels between world map locations.
    EVENT_WORLD_MAP_TRAVEL = "WORLD_MAP_TRAVEL"

    def clear(self) -> None:
        """Remove all listeners and queues (e.g. on shutdown)."""
        with self._lock:
            self._listeners.clear()
            self._async_queues.clear()

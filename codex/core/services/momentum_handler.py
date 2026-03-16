"""
Momentum Threshold Handler — Closes the feedback loop.
======================================================

When MomentumLedger.record() returns crossed thresholds, this handler
converts them into concrete world effects: rumors, GRAPES mutations,
ANCHOR shards, and cascade broadcasts.

WO-V62.0 Track C
"""
from typing import Dict, List, Optional, Tuple


# Negative events carry negative polarity for GRAPES direction
NEGATIVE_EVENTS = frozenset({
    "party_death", "companion_fell", "doom_threshold",
    "near_death",
})

# Maps momentum categories to concrete GRAPES mutations
TREND_MUTATIONS: Dict[str, dict] = {
    "security": {
        "grapes_category": "social",
        "field_positive": ("prohibition", "Vigilante justice is tolerated"),
        "field_negative": ("prohibition", "Speaking of the lost patrols is forbidden"),
        "narrative_positive": "The streets feel safer. Guards walk taller.",
        "narrative_negative": "Fear grips the ward. Doors bolt at sundown.",
    },
    "economics": {
        "grapes_category": "economics",
        "field_positive": ("abundance", "rising"),
        "field_negative": ("abundance", "scarce"),
        "narrative_positive": "New merchants arrive. The market swells.",
        "narrative_negative": "Shops shutter. Coin grows scarce.",
    },
    "politics": {
        "grapes_category": "politics",
        "field_positive": ("agenda", "Reform movement gains traction"),
        "field_negative": ("agenda", "Power consolidates in fewer hands"),
        "narrative_positive": "The council listens to new voices.",
        "narrative_negative": "Edicts come down without debate.",
    },
    "religion": {
        "grapes_category": "religion",
        "field_positive": ("ritual", "Public ceremonies resume"),
        "field_negative": ("heresy", "Whispered prayers to forgotten gods"),
        "narrative_positive": "Temple bells ring for the first time in months.",
        "narrative_negative": "The faithful grow restless. Strange symbols appear.",
    },
    "geography": {
        "grapes_category": "geography",
        "field_positive": ("feature", "New paths cleared through the wilds"),
        "field_negative": ("feature", "Roads crumble, the wilds reclaim"),
        "narrative_positive": "Scouts report safe passage to the north.",
        "narrative_negative": "The frontier contracts. The wild is winning.",
    },
    "social": {
        "grapes_category": "social",
        "field_positive": ("punishment", "Community mediation replaces harsh law"),
        "field_negative": ("punishment", "Public shaming escalates"),
        "narrative_positive": "Neighbors speak again. Trust rebuilds.",
        "narrative_negative": "Suspicion poisons every conversation.",
    },
}


def _trend_to_grapes_modifier(category: str, weight: float) -> Optional[dict]:
    """Convert a momentum category + weight into a GRAPES mutation dict.

    Args:
        category: GRAPES momentum category (e.g. "security", "economics").
        weight: Total accumulated weight; sign determines polarity.

    Returns:
        Dict with grapes_category, field, value, and narrative keys,
        or None if the category has no mapping.
    """
    mapping = TREND_MUTATIONS.get(category)
    if not mapping:
        return None
    positive = weight > 0
    field_key = "field_positive" if positive else "field_negative"
    narr_key = "narrative_positive" if positive else "narrative_negative"
    field, value = mapping[field_key]
    return {
        "grapes_category": mapping["grapes_category"],
        "field": field,
        "value": value,
        "narrative": mapping[narr_key],
    }


class MomentumThresholdHandler:
    """Processes momentum threshold crossings into concrete world effects.

    Each threshold level triggers a different tier of world response:
        3.0  — Minor shift: generate a trend-aware rumor.
        7.0  — Notable trend: town crier broadcast + GRAPES modifier.
        12.0 — Major shift: permanent GRAPES mutation + ANCHOR shard + broadcast.
        20.0 — Tipping point: all of the above + cascade notification.

    All dependencies are optional — pass None for any you do not have.
    The handler degrades gracefully if a dependency is absent.
    """

    def __init__(
        self,
        world_ledger=None,
        crier=None,
        grapes_profile=None,
        broadcast_manager=None,
        engine=None,
    ):
        """Initialise the handler.

        Args:
            world_ledger: WorldLedger instance with mutate() and
                record_historical_event() methods.
            crier: TownCrier-like object with narrate_trend_event().
            grapes_profile: Raw GRAPES dict (unused directly; mutations
                go through world_ledger.mutate()).
            broadcast_manager: Object with broadcast(event_type, data).
            engine: Game engine instance with _add_shard().
        """
        self._ledger = world_ledger
        self._crier = crier
        self._grapes = grapes_profile
        self._broadcast = broadcast_manager
        self._engine = engine

    def handle(self, threshold_events: List[dict]) -> List[str]:
        """Process a list of threshold-crossing events.

        Each event dict must contain at minimum: level, name, category,
        location, total_weight, entry_count. An optional 'cascade' key
        is expected for tipping_point (20.0) events.

        Args:
            threshold_events: List of threshold dicts from
                MomentumLedger.record().

        Returns:
            List of Rich-formatted narrative message strings.
        """
        messages: List[str] = []
        for event in threshold_events:
            level = event["level"]
            if level >= 3.0:
                messages.extend(self._handle_minor_shift(event))
            if level >= 7.0:
                messages.extend(self._handle_notable_trend(event))
            if level >= 12.0:
                messages.extend(self._handle_major_shift(event))
            if level >= 20.0:
                messages.extend(self._handle_tipping_point(event))
        return messages

    # ------------------------------------------------------------------
    # Internal threshold handlers
    # ------------------------------------------------------------------

    def _handle_minor_shift(self, event: dict) -> List[str]:
        """3.0 threshold: generate a trend-aware rumor.

        Delegates to crier.narrate_trend_event() if available, otherwise
        falls back to TREND_MUTATIONS narrative strings.
        """
        # Try crier first
        if self._crier and hasattr(self._crier, "narrate_trend_event"):
            rumor = self._crier.narrate_trend_event(event)
            if rumor:
                return [f"[dim italic]Rumor: {rumor}[/]"]

        # Fallback: derive rumor from TREND_MUTATIONS
        mapping = TREND_MUTATIONS.get(event.get("category", ""))
        if mapping:
            positive = event.get("total_weight", 0) > 0
            narr_key = "narrative_positive" if positive else "narrative_negative"
            narr = mapping.get(narr_key, "")
            if narr:
                return [f"[dim italic]Rumor: {narr}[/]"]
        return []

    def _handle_notable_trend(self, event: dict) -> List[str]:
        """7.0 threshold: town crier broadcast + GRAPES modifier.

        Applies a GRAPES mutation via world_ledger.mutate() and records
        a historical event. Emits a bolded town crier message if a crier
        is present.
        """
        messages: List[str] = []

        # Town crier broadcast
        if self._crier and hasattr(self._crier, "narrate_trend_event"):
            broadcast = self._crier.narrate_trend_event(event)
            if broadcast:
                messages.append(f"[bold]Town Crier: {broadcast}[/]")

        # Apply GRAPES modifier via ledger
        if self._ledger:
            category = event.get("category", "")
            modifier = _trend_to_grapes_modifier(category, event.get("total_weight", 0))
            if modifier:
                try:
                    self._ledger.mutate(
                        category=modifier["grapes_category"],
                        index=0,
                        field=modifier["field"],
                        value=modifier["value"],
                    )
                except (KeyError, IndexError, AttributeError):
                    pass  # GRAPES category not present in this world

                try:
                    from codex.core.world.world_ledger import EventType  # type: ignore
                    self._ledger.record_historical_event(
                        event_type=EventType.MUTATION,
                        summary=modifier["narrative"],
                        category=category,
                    )
                except (ImportError, Exception):
                    pass

                messages.append(f"[cyan]The world shifts: {modifier['narrative']}[/]")

        return messages

    def _handle_major_shift(self, event: dict) -> List[str]:
        """12.0 threshold: permanent mutation + ANCHOR shard + NPC broadcast.

        Builds on _handle_notable_trend() and additionally emits an ANCHOR
        shard into the engine's memory and broadcasts a HIGH_IMPACT_DECISION
        event for NPC memory routing.
        """
        messages = self._handle_notable_trend(event)

        # Emit ANCHOR shard into engine memory
        if self._engine and hasattr(self._engine, "_add_shard"):
            self._engine._add_shard(
                f"Major shift in {event.get('category', '?')} at "
                f"{event.get('location', '?')}: "
                f"{event.get('entry_count', 0)} actions accumulated.",
                "ANCHOR",
                source="momentum",
            )

        # Broadcast for NPC memory routing
        if self._broadcast and hasattr(self._broadcast, "broadcast"):
            self._broadcast.broadcast(
                "HIGH_IMPACT_DECISION",
                {
                    "_event_type": "HIGH_IMPACT_DECISION",
                    "event_tag": f"momentum_{event.get('category', '?')}_major",
                    "category": event.get("category", ""),
                    "summary": (
                        f"Major {event.get('category', '')} shift "
                        f"at {event.get('location', '')}"
                    ),
                },
            )

        return messages

    def _handle_tipping_point(self, event: dict) -> List[str]:
        """20.0 threshold: all major-shift effects + cascade notification.

        If the event dict contains a 'cascade' key (populated by
        MomentumLedger at the tipping point), appends a cascade message
        naming the secondary category that received free weight.
        """
        messages = self._handle_major_shift(event)
        cascade = event.get("cascade")
        if cascade:
            messages.append(
                f"[bold yellow]Cascade: {event.get('category', '?')} momentum "
                f"spills into {cascade.get('category', '?')}![/]"
            )
        return messages

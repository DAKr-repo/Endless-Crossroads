"""
Narrative Loom — Cross-shard synthesis & contradiction diagnostics.
====================================================================

AMD-07: This service does NOT just concatenate retrieved shards.
It reasons across layered context (world primers, session facts,
civic events, player actions) to produce a single non-contradictory
narrative block.

Components:
  - synthesize_narrative(): multi-shard reasoning via Mimir
  - SessionManifest: per-session compiled narrative cache
  - diagnostic_trace(): trace a fact back through its source shards
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

try:
    from codex.core.memory import MemoryShard, ShardType
    _MEMORY_AVAILABLE = True
except ImportError:
    MemoryShard = None  # type: ignore[assignment,misc]
    ShardType = None    # type: ignore[assignment,misc]
    _MEMORY_AVAILABLE = False


ANCHOR_EVENT_TYPES = frozenset({
    "near_death", "ally_saved", "rare_item_used", "critical_roll",
    "companion_fell", "faction_shift", "doom_threshold", "zone_breakthrough",
    "party_death",
})


# =========================================================================
# NARRATIVE LOOM MIXIN — Shared integration for all game engines
# =========================================================================

class NarrativeLoomMixin:
    """Mixin that gives any game engine Narrative Loom integration.

    Provides:
      - ``_init_loom()``: call in ``__init__`` to set up shard storage.
      - ``_add_shard(content, shard_type, source)``: record a narrative event.
      - ``trace_fact(fact)``: trace a stated fact through shard layers.

    Shard types (by authority):
      - MASTER: campaign-level context (created once at engine init).
      - ANCHOR: milestone events (level-up, ideal, advancement).
      - CHRONICLE: session events (kills, room transitions, rolls).
      - ECHO: AI-generated narrative fragments.
    """

    def _init_loom(self) -> None:
        """Initialize Narrative Loom fields. Call from engine __init__."""
        self._memory_shards: list = []
        self._manifest = None

    def _add_shard(self, content: str, shard_type: str,
                   source: str = "") -> None:
        """Create a MemoryShard and append to the engine's shard list."""
        if not _MEMORY_AVAILABLE:
            return
        src = source or getattr(self, "system_id", "unknown")
        shard = MemoryShard(
            shard_type=ShardType(shard_type),
            content=content,
            source=src,
        )
        self._memory_shards.append(shard)

    def trace_fact(self, fact: str) -> str:
        """Trace a stated fact back through narrative shard layers.

        Returns a formatted string showing which shards support or
        contradict the claim, ordered by authority.
        """
        if not _MEMORY_AVAILABLE:
            return "Narrative Loom not available."
        if not self._memory_shards:
            return "No memory shards loaded — trace unavailable."

        results = diagnostic_trace(fact, self._memory_shards)
        if not results:
            return f"No shards mention '{fact}'."

        lines = [f'Trace: "{fact}"', ""]
        for r in results:
            lines.append(
                f"  [{r['type']}] ({r['source']}) "
                f"relevance={r['relevance']}"
            )
            if r.get("excerpt"):
                lines.append(f"    {r['excerpt']}")
        return "\n".join(lines)


# =========================================================================
# SESSION MANIFEST
# =========================================================================

@dataclass
class SessionManifest:
    """Anchors a campaign session to a compiled narrative snapshot.

    Once synthesized, the compiled narrative is cached so Mimir uses the
    resolved version of facts rather than re-layering shards each query.
    """
    session_id: str
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    anchored_shards: List[str] = field(default_factory=list)  # shard IDs
    compiled_narrative: str = ""
    content_hash: str = ""  # Hash of input shards for cache invalidation

    def is_stale(self, current_shards: List[MemoryShard]) -> bool:
        """Check if the compiled narrative is outdated."""
        new_hash = _hash_shards(current_shards)
        return new_hash != self.content_hash

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created": self.created,
            "anchored_shards": self.anchored_shards,
            "compiled_narrative": self.compiled_narrative,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionManifest":
        return cls(
            session_id=data["session_id"],
            created=data.get("created", ""),
            anchored_shards=data.get("anchored_shards", []),
            compiled_narrative=data.get("compiled_narrative", ""),
            content_hash=data.get("content_hash", ""),
        )


# =========================================================================
# HELPERS
# =========================================================================

def _hash_shards(shards: List[MemoryShard]) -> str:
    """Compute a content hash over a list of shards for cache invalidation."""
    h = hashlib.sha256()
    for s in sorted(shards, key=lambda s: s.id):
        h.update(s.id.encode())
        h.update(s.content.encode())
    return h.hexdigest()[:16]


def _prioritize_shards(shards: List[MemoryShard]) -> List[MemoryShard]:
    """Order shards by type priority: MASTER > ANCHOR > CHRONICLE > ECHO."""
    order = {ShardType.MASTER: 0, ShardType.ANCHOR: 1,
             ShardType.CHRONICLE: 2, ShardType.ECHO: 3}
    return sorted(shards, key=lambda s: (order.get(s.shard_type, 9), s.timestamp))


# =========================================================================
# SYNTHESIS ENGINE
# =========================================================================

def synthesize_narrative(
    query: str,
    context_shards: List[MemoryShard],
    mimir_fn: Optional[Callable] = None,
    manifest: Optional[SessionManifest] = None,
) -> str:
    """Synthesize a non-contradictory narrative from layered shards.

    If a valid cached manifest exists and is not stale, returns the cached
    compilation.  Otherwise, reasons across shards via Mimir (or falls
    back to priority-ordered concatenation).

    Args:
        query: The player's question or the narrative prompt.
        context_shards: Relevant memory shards to synthesize.
        mimir_fn: Optional AI generation function(prompt, context) -> str.
        manifest: Optional session manifest for caching.

    Returns:
        Synthesized narrative string.
    """
    # Check cache
    if manifest and not manifest.is_stale(context_shards):
        if manifest.compiled_narrative:
            return manifest.compiled_narrative

    ordered = _prioritize_shards(context_shards)

    # Build layered context
    layers = []
    for shard in ordered:
        label = shard.shard_type.value
        source = shard.source or "unknown"
        layers.append(f"[{label}/{source}] {shard.content}")

    layered_context = "\n---\n".join(layers)

    if mimir_fn:
        synthesis_prompt = (
            "You are a narrative synthesizer. Given the following layered context "
            "(ordered by authority: MASTER > ANCHOR > CHRONICLE > ECHO), produce "
            "a single coherent narrative block that resolves any contradictions by "
            "preferring higher-authority layers. Do NOT list sources; write prose.\n\n"
            f"QUERY: {query}\n\n"
            f"LAYERS:\n{layered_context}"
        )
        try:
            result = mimir_fn(synthesis_prompt, "")
            if result and len(result) > 20:
                # Cache the result
                if manifest:
                    manifest.compiled_narrative = result
                    manifest.content_hash = _hash_shards(context_shards)
                    manifest.anchored_shards = [s.id for s in ordered]
                return result
        except Exception:
            pass

    # Fallback: priority-ordered concatenation
    fallback = "\n\n".join(s.content for s in ordered)
    if manifest:
        manifest.compiled_narrative = fallback
        manifest.content_hash = _hash_shards(context_shards)
        manifest.anchored_shards = [s.id for s in ordered]
    return fallback


# =========================================================================
# DIAGNOSTIC TRACE
# =========================================================================

def diagnostic_trace(
    fact: str,
    shards: List[MemoryShard],
) -> List[dict]:
    """Trace a stated fact back through the shard layers.

    Performs keyword matching to find which shards contain the fact,
    ordered by authority level.  This lets a player ask "Wait, I thought
    the King was dead?" and get a layered explanation of where that
    belief came from.

    Args:
        fact: The fact or claim to trace (e.g. "the king is dead").

    Returns:
        List of dicts with keys: shard_id, type, source, excerpt, relevance.
    """
    fact_lower = fact.lower()
    words = set(fact_lower.split())
    results = []

    for shard in _prioritize_shards(shards):
        content_lower = shard.content.lower()

        # Score by keyword overlap
        matching_words = sum(1 for w in words if w in content_lower)
        if matching_words == 0:
            continue

        relevance = matching_words / max(len(words), 1)

        # Extract a short excerpt around the first match
        excerpt = ""
        for word in words:
            idx = content_lower.find(word)
            if idx >= 0:
                start = max(0, idx - 40)
                end = min(len(shard.content), idx + len(word) + 60)
                excerpt = "..." + shard.content[start:end] + "..."
                break

        results.append({
            "shard_id": shard.id,
            "type": shard.shard_type.value,
            "source": shard.source,
            "excerpt": excerpt,
            "relevance": round(relevance, 2),
        })

    # Sort by relevance descending, then by authority
    results.sort(key=lambda r: -r["relevance"])
    return results


def _format_anchor(event: dict) -> str:
    """Format a single anchor event into a human-readable line."""
    etype = event.get("type", "")
    if etype == "near_death":
        return f"  {event.get('name', '?')} nearly fell ({event.get('hp', '?')}/{event.get('max_hp', '?')} HP) from {event.get('attacker', 'unknown')}"
    elif etype == "ally_saved":
        return f"  {event.get('savior', '?')} saved {event.get('saved', '?')} via {event.get('method', '?')}"
    elif etype == "critical_roll":
        return f"  {event.get('roller', '?')} rolled a {event.get('result', '?')} {event.get('context', '')}"
    elif etype == "companion_fell":
        return f"  Companion {event.get('name', '?')} ({event.get('archetype', '?')}) fell to {event.get('cause', 'unknown')}"
    elif etype == "doom_threshold":
        return f"  Doom {event.get('doom_value', '?')}: {event.get('event_text', '')}"
    elif etype == "zone_breakthrough":
        return f"  Broke through to Tier {event.get('tier', '?')}"
    elif etype == "faction_shift":
        return f"  {event.get('npc_name', '?')} disposition: {event.get('old_tier', '?')} -> {event.get('new_tier', '?')}"
    elif etype == "rare_item_used":
        return f"  {event.get('user', '?')} used {event.get('item_name', '?')} ({event.get('trait', '')})"
    elif etype == "party_death":
        return f"  {event.get('name', '?')} has fallen"
    return f"  {etype}: {event}"


# =========================================================================
# SESSION CHRONICLE — RECAP SUMMARIZATION (WO-V37.0)
# =========================================================================

def format_session_stats(
    session_log: List[dict],
    engine_snapshot: dict,
) -> dict:
    """Build a structured stats dict from a session chronicle log.

    Args:
        session_log: List of event dicts with ``type`` keys.
        engine_snapshot: Dict with ``party``, ``doom``, ``turns``,
            ``chapter``, ``completed_quests`` keys.

    Returns:
        Dict with kills, loot, rooms_explored, rooms_cleared, etc.
    """
    kills_total = 0
    kills_by_tier: Dict[int, int] = {}
    loot_items: List[str] = []
    rooms_explored = 0
    rooms_cleared = 0
    quests_completed: List[str] = []
    aoe_used = 0
    deaths: List[str] = []
    companions_summoned: List[str] = []

    for event in session_log:
        etype = event.get("type", "")
        if etype == "kill":
            kills_total += 1
            tier = event.get("tier", 1)
            kills_by_tier[tier] = kills_by_tier.get(tier, 0) + 1
        elif etype == "loot":
            name = event.get("item_name", "Unknown")
            loot_items.append(name)
        elif etype == "room_cleared":
            rooms_cleared += 1
        elif etype == "room_entered":
            rooms_explored += 1
        elif etype == "aoe_used":
            aoe_used += 1
        elif etype == "quest_complete":
            title = event.get("title", "Unknown")
            quests_completed.append(title)
        elif etype == "party_death":
            deaths.append(event.get("name", "Unknown"))
        elif etype == "companion_summoned":
            companions_summoned.append(event.get("name", "Unknown"))

    # Also pull quest completions from engine snapshot if not in log
    snap_quests = engine_snapshot.get("completed_quests", [])
    for q in snap_quests:
        if q not in quests_completed:
            quests_completed.append(q)

    party_info = engine_snapshot.get("party", [])

    anchor_moments = []
    for event in session_log:
        if event.get("type") in ANCHOR_EVENT_TYPES:
            anchor_moments.append(event)

    return {
        "kills": {"total": kills_total, "by_tier": kills_by_tier},
        "loot": loot_items,
        "rooms_explored": rooms_explored,
        "rooms_cleared": rooms_cleared,
        "quests_completed": quests_completed,
        "aoe_used": aoe_used,
        "deaths": deaths,
        "companions_summoned": companions_summoned,
        "party": party_info,
        "doom": engine_snapshot.get("doom", 0),
        "turns": engine_snapshot.get("turns", 0),
        "chapter": engine_snapshot.get("chapter", 1),
        "anchor_moments": anchor_moments,
    }


def summarize_session(
    session_log: List[dict],
    engine_snapshot: dict,
    mimir_fn: Optional[Callable] = None,
) -> str:
    """Produce a human-readable session recap.

    Always includes a structured stats block.  If *mimir_fn* is provided,
    attempts to generate a short narrative flavour paragraph (with a 10-second
    timeout and graceful fallback to stats-only).

    Args:
        session_log: Structured chronicle events from GameState.session_log.
        engine_snapshot: Dict with party, doom, turns, chapter, completed_quests.
        mimir_fn: Optional ``(prompt, context) -> str`` AI generation function.

    Returns:
        Formatted recap string.
    """
    stats = format_session_stats(session_log, engine_snapshot)

    lines: List[str] = []
    lines.append("=== SESSION RECAP ===")
    lines.append("")

    # Rooms
    lines.append(f"Rooms explored: {stats['rooms_explored']}")
    lines.append(f"Rooms cleared:  {stats['rooms_cleared']}")

    # Kills
    kill_info = stats["kills"]
    if kill_info["total"] > 0:
        tier_parts = ", ".join(
            f"T{t}: {c}" for t, c in sorted(kill_info["by_tier"].items())
        )
        lines.append(f"Enemies slain:  {kill_info['total']} ({tier_parts})")
    else:
        lines.append("Enemies slain:  0")

    # Loot
    if stats["loot"]:
        lines.append(f"Loot gained:    {', '.join(stats['loot'])}")
    else:
        lines.append("Loot gained:    none")

    # AoE
    if stats["aoe_used"]:
        lines.append(f"AoE activations: {stats['aoe_used']}")

    # Quests
    if stats["quests_completed"]:
        lines.append(f"Quests done:    {', '.join(stats['quests_completed'])}")

    # Deaths
    if stats["deaths"]:
        lines.append(f"Fallen allies:  {', '.join(stats['deaths'])}")

    # Companions
    if stats["companions_summoned"]:
        lines.append(f"Companions:     {', '.join(stats['companions_summoned'])}")

    # Party status
    lines.append("")
    lines.append("--- Party Status ---")
    for member in stats["party"]:
        lines.append(f"  {member['name']}: {member['hp']}/{member['max_hp']} HP")

    # Doom & turns
    lines.append("")
    lines.append(f"Doom Clock: {stats['doom']}/20")
    lines.append(f"Turns taken: {stats['turns']}")

    stats_block = "\n".join(lines)

    # WO-V61.0: Append anchor moments to stats block
    anchors = stats.get("anchor_moments", [])
    if anchors:
        anchor_lines = ["", "--- Key Moments ---"]
        for a in anchors:
            anchor_lines.append(_format_anchor(a))
        stats_block += "\n".join(anchor_lines)

    # Optional Mimir narrative flavour
    if mimir_fn:
        import concurrent.futures
        prompt = (
            "Write a brief (2-3 sentence) dramatic narrative recap of this "
            "dungeon session. Focus on the most dramatic moments, not just statistics.\n\n"
            + stats_block
        )
        try:
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = pool.submit(mimir_fn, prompt, "")
            try:
                narrative = future.result(timeout=10)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            if narrative and len(narrative) > 20:
                return stats_block + "\n\n--- Mimir's Chronicle ---\n" + narrative
        except Exception:
            pass  # Timeout or error — fall back to stats only

    return stats_block

#!/usr/bin/env python3
"""
codex_memory_engine.py — Memory Shard Neural Link System
==========================================================

The Memory Engine is the structured context management layer for C.O.D.E.X.
It bridges game state, conversation history, and LLM invocation with:

1. Categorized memory shards (MASTER, ANCHOR, ECHO, CHRONICLE)
2. Priority-based context weaving within token budgets
3. Persistent save/load for session continuity
4. Tag-based retrieval and search

Memory Shards are the atoms of context. They are timestamped, weighted,
and organized by importance to ensure critical context (world primers,
faction data) is never evicted, while ephemeral turns are managed via
a sliding window.

Version: 1.0 (Neural Link)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import logging
import uuid

log = logging.getLogger(__name__)


# =============================================================================
# SHARD TYPE TAXONOMY
# =============================================================================

class ShardType(Enum):
    """Memory shard classification by persistence priority."""
    MASTER = "MASTER"       # World info, primers, faction data — NEVER evicted
    ECHO = "ECHO"           # Recent chat turns — sliding window, evictable
    CHRONICLE = "CHRONICLE" # Summaries of past sessions — low priority but persistent
    ANCHOR = "ANCHOR"       # Key plot points, NPC introductions — semi-permanent


# =============================================================================
# MEMORY SHARD — THE DATA ATOM
# =============================================================================

@dataclass
class MemoryShard:
    """A single unit of memory in the C.O.D.E.X. system.

    Memory Shards are the atoms of context. They are categorized by type,
    tagged for retrieval, timestamped for ordering, and weighted for eviction.

    Attributes:
        id: Unique 8-character identifier
        shard_type: MASTER, ECHO, CHRONICLE, or ANCHOR
        content: The text content of the shard
        timestamp: ISO 8601 timestamp of creation
        tags: List of tags for retrieval (e.g., ["combat", "npc:julian"])
        pinned: If True, never evicted (typically MASTER shards)
        token_estimate: Estimated token count (~4 chars per token)
        source: Origin identifier ("user", "mimir", "system", "genesis")
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    shard_type: ShardType = ShardType.ECHO
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)
    pinned: bool = False
    token_estimate: int = 0
    source: str = ""

    def __post_init__(self):
        """Calculate token estimate on creation."""
        if self.token_estimate == 0:
            self.token_estimate = max(1, len(self.content) // 4)

    def to_dict(self) -> dict:
        """Serialize for JSON save."""
        return {
            "id": self.id,
            "type": self.shard_type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "pinned": self.pinned,
            "token_estimate": self.token_estimate,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryShard":
        """Deserialize from JSON."""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            shard_type=ShardType(data.get("type", "ECHO")),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            tags=data.get("tags", []),
            pinned=data.get("pinned", False),
            token_estimate=data.get("token_estimate", 0),
            source=data.get("source", ""),
        )


# =============================================================================
# CODEX MEMORY ENGINE — THE NEURAL LINK
# =============================================================================

class CodexMemoryEngine:
    """The Memory Engine — manages all context shards for LLM interactions.

    Responsibilities:
    1. Store and categorize memory shards
    2. Pin critical context (world primers, faction data)
    3. Weave optimal context strings within token budgets
    4. Persist to disk for save/load
    5. Integrate with the ContextWindow from scripts/optimize_context.py

    The Memory Engine maintains four categories of shards:
    - MASTER: Pinned world state (never evicted)
    - ANCHOR: Key plot points (rarely evicted)
    - ECHO: Recent turns (frequently evicted)
    - CHRONICLE: Session summaries (persistent but low priority)
    """

    def __init__(self, max_tokens: int = 8192, generation_reserve: int = 2048,
                 broadcast_manager=None):
        """Initialize the Memory Engine.

        Args:
            max_tokens: Maximum context window size (default 8192)
            generation_reserve: Tokens reserved for model output (default 2048)
            broadcast_manager: Optional GlobalBroadcastManager for high-impact
                               shard notifications.
        """
        self.max_tokens = max_tokens
        self.generation_reserve = generation_reserve
        self.budget = max_tokens - generation_reserve

        self.shards: list[MemoryShard] = []

        self.save_path: Optional[Path] = None

        self.broadcast_manager = broadcast_manager

    # ─────────────────────────────────────────────────────────────────────
    # SHARD MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────

    def create_shard(
        self,
        content: str,
        shard_type: str | ShardType = "ECHO",
        tags: Optional[list[str]] = None,
        source: str = "",
        pinned: bool = False
    ) -> MemoryShard:
        """Create and store a new memory shard.

        Args:
            content: The text content of the shard
            shard_type: "MASTER", "ECHO", "CHRONICLE", or "ANCHOR"
            tags: Optional tags for retrieval (e.g., ["combat", "npc:julian"])
            source: Origin identifier ("user", "mimir", "system", "genesis")
            pinned: If True, never evicted

        Returns:
            The created MemoryShard
        """
        if isinstance(shard_type, str):
            shard_type = ShardType(shard_type)

        shard = MemoryShard(
            shard_type=shard_type,
            content=content,
            tags=tags or [],
            source=source,
            pinned=pinned,
        )

        self.shards.append(shard)

        # Broadcast high-impact shards for cross-system listeners
        if self.broadcast_manager and shard.shard_type in (ShardType.ANCHOR, ShardType.MASTER):
            try:
                self.broadcast_manager.broadcast(
                    "HIGH_IMPACT_DECISION",
                    {"shard_id": shard.id, "type": shard.shard_type.value,
                     "summary": shard.content[:200], "tags": shard.tags},
                )
            except Exception:
                pass  # Broadcast failure must not break shard creation

        return shard

    def pin_shard(self, shard_id: str) -> bool:
        """Pin a shard so it's never evicted from context.

        Typically used for MASTER shards (world primer, faction data).
        Pinned shards are always included at the top of weave_context().

        Args:
            shard_id: ID of the shard to pin

        Returns:
            True if shard was found and pinned, False otherwise
        """
        for shard in self.shards:
            if shard.id == shard_id:
                shard.pinned = True
                return True
        return False

    def unpin_shard(self, shard_id: str) -> bool:
        """Unpin a previously pinned shard.

        Args:
            shard_id: ID of the shard to unpin

        Returns:
            True if shard was found and unpinned, False otherwise
        """
        for shard in self.shards:
            if shard.id == shard_id:
                shard.pinned = False
                return True
        return False

    # ─────────────────────────────────────────────────────────────────────
    # CONTEXT ASSEMBLY
    # ─────────────────────────────────────────────────────────────────────

    def weave_context(self, include_system_prompt: bool = True) -> str:
        """Assemble the optimal context string for the LLM within token budget.

        Priority order:
        1. MASTER shards (pinned — world primer, faction data)
        2. ANCHOR shards (key plot points, ordered by recency)
        3. Recent ECHO shards (last N that fit in remaining budget)
        4. CHRONICLE shards (session summaries, only if room)

        Args:
            include_system_prompt: If True, prepend a generic system header

        Returns:
            A single string ready to pass as context to the LLM.
            Stays within self.budget tokens.
        """
        sections = []
        used_tokens = 0

        # System prompt (optional)
        system_header = ""
        if include_system_prompt:
            system_header = "=== C.O.D.E.X. MEMORY CONTEXT ===\n\n"
            used_tokens += len(system_header) // 4

        # Priority 1: MASTER shards (pinned)
        master_shards = [s for s in self.shards if s.shard_type == ShardType.MASTER or s.pinned]
        master_content = []
        for shard in master_shards:
            if used_tokens + shard.token_estimate <= self.budget:
                master_content.append(shard.content)
                used_tokens += shard.token_estimate

        if master_content:
            sections.append("--- WORLD STATE ---\n" + "\n\n".join(master_content))

        # Priority 2: ANCHOR shards (ordered by recency)
        anchor_shards = [s for s in self.shards if s.shard_type == ShardType.ANCHOR and not s.pinned]
        anchor_shards.sort(key=lambda s: s.timestamp, reverse=True)
        anchor_content = []
        for shard in anchor_shards:
            if used_tokens + shard.token_estimate <= self.budget:
                anchor_content.append(shard.content)
                used_tokens += shard.token_estimate

        if anchor_content:
            sections.append("--- KEY EVENTS ---\n" + "\n\n".join(anchor_content))

        # Priority 3: ECHO shards (recent turns, last N that fit)
        echo_shards = [s for s in self.shards if s.shard_type == ShardType.ECHO]
        echo_shards.sort(key=lambda s: s.timestamp, reverse=True)
        echo_content = []
        for shard in echo_shards:
            if used_tokens + shard.token_estimate <= self.budget:
                echo_content.append(shard.content)
                used_tokens += shard.token_estimate

        # Reverse to chronological order
        echo_content.reverse()
        if echo_content:
            sections.append("--- RECENT CONVERSATION ---\n" + "\n\n".join(echo_content))

        # Priority 4: CHRONICLE shards (only if room)
        chronicle_shards = [s for s in self.shards if s.shard_type == ShardType.CHRONICLE]
        chronicle_shards.sort(key=lambda s: s.timestamp, reverse=True)
        chronicle_content = []
        for shard in chronicle_shards:
            if used_tokens + shard.token_estimate <= self.budget:
                chronicle_content.append(shard.content)
                used_tokens += shard.token_estimate

        if chronicle_content:
            sections.append("--- SESSION HISTORY ---\n" + "\n\n".join(chronicle_content))

        return system_header + "\n\n".join(sections)

    def weave_messages(self, system_prompt: str = "") -> list[dict]:
        """Assemble context as a list of message dicts for chat API.

        Args:
            system_prompt: Optional system prompt to prepend

        Returns:
            List of {"role": "system"/"user"/"assistant", "content": "..."} dicts
            compatible with Ollama's chat API.
        """
        messages = []
        used_tokens = 0

        # System message (pinned context)
        system_content_parts = []
        if system_prompt:
            system_content_parts.append(system_prompt)

        # Add MASTER shards to system message
        master_shards = [s for s in self.shards if s.shard_type == ShardType.MASTER or s.pinned]
        for shard in master_shards:
            if used_tokens + shard.token_estimate <= self.budget:
                system_content_parts.append(shard.content)
                used_tokens += shard.token_estimate

        if system_content_parts:
            messages.append({
                "role": "system",
                "content": "\n\n".join(system_content_parts)
            })

        # Add ANCHOR shards as system messages
        anchor_shards = [s for s in self.shards if s.shard_type == ShardType.ANCHOR and not s.pinned]
        anchor_shards.sort(key=lambda s: s.timestamp)
        for shard in anchor_shards:
            if used_tokens + shard.token_estimate <= self.budget:
                messages.append({
                    "role": "system",
                    "content": f"[KEY EVENT] {shard.content}"
                })
                used_tokens += shard.token_estimate

        # Add ECHO shards as user/assistant messages
        echo_shards = [s for s in self.shards if s.shard_type == ShardType.ECHO]
        echo_shards.sort(key=lambda s: s.timestamp)
        for shard in echo_shards:
            if used_tokens + shard.token_estimate <= self.budget:
                role = "user" if shard.source == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": shard.content
                })
                used_tokens += shard.token_estimate

        return messages

    def _calculate_used_tokens(self) -> int:
        """Calculate total tokens used by all shards."""
        return sum(s.token_estimate for s in self.shards)

    def _evict_oldest_echoes(self, tokens_to_free: int) -> int:
        """Remove oldest ECHO shards until enough tokens are freed.

        Args:
            tokens_to_free: Number of tokens to free

        Returns:
            Number of tokens actually freed
        """
        # Get evictable ECHO shards (not pinned), sorted by timestamp
        evictable = [s for s in self.shards if s.shard_type == ShardType.ECHO and not s.pinned]
        evictable.sort(key=lambda s: s.timestamp)

        freed = 0
        for shard in evictable:
            if freed >= tokens_to_free:
                break
            self.shards.remove(shard)
            freed += shard.token_estimate

        return freed

    # ─────────────────────────────────────────────────────────────────────
    # WORLD STATE INTEGRATION
    # ─────────────────────────────────────────────────────────────────────

    def ingest_world_state(self, world_state: dict) -> MemoryShard:
        """Create a MASTER shard from a WorldState dict.

        Compresses the world state into a concise context block:
        - World name, genre, tone
        - Faction terms (Crown/Crew names and descriptions)
        - G.R.A.P.E.S. summary (1 line per category)
        - World primer text

        Automatically pins the resulting shard.

        Args:
            world_state: Dict from WorldState.to_dict() or GenesisEngine.roll_unified_world()

        Returns:
            The pinned MASTER shard
        """
        lines = []

        # World identity
        name = world_state.get("name", "Unknown World")
        genre = world_state.get("genre", "Fantasy")
        tone = world_state.get("tone", "neutral")
        lines.append(f"WORLD: {name}")
        lines.append(f"GENRE: {genre} | TONE: {tone.upper()}")
        lines.append("")

        # Faction terms
        terms = world_state.get("terms", {})
        crown = terms.get("crown", "The Crown")
        crew = terms.get("crew", "The Crew")
        lines.append(f"CROWN FACTION: {crown}")
        lines.append(f"CREW FACTION: {crew}")
        lines.append("")

        # G.R.A.P.E.S. summary -- detect rich vs flat format
        grapes = world_state.get("grapes", {})
        if grapes:
            # WO-V8.0: Try rich format via GrapesProfile
            _used_rich = False
            try:
                from codex.core.world.grapes_engine import GrapesProfile
                sample = next(iter(grapes.values()), None)
                if isinstance(sample, list):
                    profile = GrapesProfile.from_dict(grapes)
                    lines.append("WORLD STRUCTURE (G.R.A.P.E.S.):")
                    lines.append(profile.to_narrative_summary())
                    lines.append("")
                    _used_rich = True
            except Exception:
                pass

            if not _used_rich:
                # Flat format fallback
                lines.append("WORLD STRUCTURE (G.R.A.P.E.S.):")
                for key in ["geography", "religion", "achievements", "politics", "economics", "social"]:
                    value = grapes.get(key, "Unknown")
                    if isinstance(value, str):
                        lines.append(f"  {key.upper()}: {value}")
                    else:
                        lines.append(f"  {key.upper()}: {value}")
                lines.append("")

        # World primer
        primer = world_state.get("primer", "")
        if primer:
            lines.append("WORLD PRIMER:")
            lines.append(primer)

        content = "\n".join(lines)

        shard = self.create_shard(
            content=content,
            shard_type=ShardType.MASTER,
            tags=["world", "genesis"],
            source="genesis",
            pinned=True
        )

        return shard

    def ingest_game_state(self, engine_state: dict) -> MemoryShard:
        """Create/update an ANCHOR shard from current game engine state.

        Captures: current day, location, sway, corruption, allegiance, active events.
        Called at the start of each turn to keep context current.

        Args:
            engine_state: Dict from game engine (day, location, sway, etc.)

        Returns:
            The created ANCHOR shard
        """
        lines = []

        day = engine_state.get("current_day", 1)
        max_days = engine_state.get("max_days", 5)
        location = engine_state.get("current_location", "Unknown")
        sway = engine_state.get("sway", 0)

        lines.append(f"DAY {day}/{max_days} — LOCATION: {location}")
        lines.append(f"PLAYER SWAY: {sway:+d}")

        # Allegiance
        if sway < -1:
            allegiance = "Crown Loyal"
        elif sway > 1:
            allegiance = "Crew Loyal"
        else:
            allegiance = "Neutral"
        lines.append(f"ALLEGIANCE: {allegiance}")

        # Active events
        events = engine_state.get("active_events", [])
        if events:
            lines.append(f"ACTIVE EVENTS: {', '.join(events)}")

        content = "\n".join(lines)

        shard = self.create_shard(
            content=content,
            shard_type=ShardType.ANCHOR,
            tags=["game_state", f"day_{day}"],
            source="system"
        )

        return shard

    # ─────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────

    def save_to_disk(self, path: Optional[Path] = None) -> Path:
        """Save all shards to a JSON file.

        Schema (compatible with legacy codex_save.json):
        {
            "version": "2.0",
            "engine": "codex_memory",
            "timestamp": "...",
            "shards": [...],
            "metadata": {
                "total_shards": N,
                "pinned_count": N,
                "token_budget": 8192
            }
        }

        Args:
            path: Optional path to save to. If None, uses self.save_path or defaults to "memory_save.json"

        Returns:
            Path where the file was saved
        """
        if path is None:
            if self.save_path:
                path = self.save_path
            else:
                from codex.paths import SAVES_DIR
                SAVES_DIR.mkdir(parents=True, exist_ok=True)
                path = SAVES_DIR / "memory_save.json"

        self.save_path = path

        data = {
            "version": "2.0",
            "engine": "codex_memory",
            "timestamp": datetime.now().isoformat(),
            "shards": [s.to_dict() for s in self.shards],
            "metadata": {
                "total_shards": len(self.shards),
                "pinned_count": sum(1 for s in self.shards if s.pinned),
                "token_budget": self.budget,
                "max_tokens": self.max_tokens,
                "generation_reserve": self.generation_reserve,
            }
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return path

    def load_from_disk(self, path: Path) -> None:
        """Load shards from a JSON file.

        Handles both legacy (codex_save.json) and new formats.
        For legacy files: converts old structure to MemoryShard format.

        Args:
            path: Path to the JSON file

        Raises:
            FileNotFoundError: If path does not exist
            json.JSONDecodeError: If file is not valid JSON
        """
        with open(path) as f:
            data = json.load(f)

        self.save_path = path

        # Check version
        version = data.get("version", "1.0")

        if version == "2.0":
            # New format — load shards directly
            self.shards = [MemoryShard.from_dict(s) for s in data.get("shards", [])]

            # Restore metadata
            metadata = data.get("metadata", {})
            self.budget = metadata.get("token_budget", self.budget)
            self.max_tokens = metadata.get("max_tokens", self.max_tokens)
            self.generation_reserve = metadata.get("generation_reserve", self.generation_reserve)

        else:
            # Legacy format — attempt shard recovery (WO-V10.0)
            log.warning(
                "Legacy memory format (version=%s) loaded from %s",
                version, path,
            )
            recovered = []
            raw_shards = data.get("shards", [])
            for raw in raw_shards:
                try:
                    recovered.append(MemoryShard.from_dict(raw))
                except Exception as exc:
                    log.warning("Skipped malformed shard during recovery: %s", exc)
            self.shards = recovered
            log.info(
                "Legacy recovery: %d/%d shards recovered from %s",
                len(recovered), len(raw_shards), path,
            )

    # ─────────────────────────────────────────────────────────────────────
    # UTILITY
    # ─────────────────────────────────────────────────────────────────────

    def get_usage_report(self) -> dict:
        """Return current memory usage breakdown.

        Returns:
            {
                "total_shards": int,
                "master_count": int,
                "anchor_count": int,
                "echo_count": int,
                "chronicle_count": int,
                "pinned_count": int,
                "total_tokens": int,
                "budget": int,
                "headroom": int,
            }
        """
        master_count = sum(1 for s in self.shards if s.shard_type == ShardType.MASTER)
        anchor_count = sum(1 for s in self.shards if s.shard_type == ShardType.ANCHOR)
        echo_count = sum(1 for s in self.shards if s.shard_type == ShardType.ECHO)
        chronicle_count = sum(1 for s in self.shards if s.shard_type == ShardType.CHRONICLE)
        pinned_count = sum(1 for s in self.shards if s.pinned)
        total_tokens = self._calculate_used_tokens()

        return {
            "total_shards": len(self.shards),
            "master_count": master_count,
            "anchor_count": anchor_count,
            "echo_count": echo_count,
            "chronicle_count": chronicle_count,
            "pinned_count": pinned_count,
            "total_tokens": total_tokens,
            "budget": self.budget,
            "headroom": self.budget - total_tokens,
        }

    def summarize_echoes(self, max_echoes: int = 10) -> Optional[str]:
        """Summarize older ECHO shards into a single CHRONICLE shard.

        This compresses conversation history to free token budget
        while preserving important context.
        Called when echo count exceeds threshold.

        Args:
            max_echoes: Keep this many recent echoes, summarize the rest

        Returns:
            Summary text, or None if no echoes to summarize
        """
        echo_shards = [s for s in self.shards if s.shard_type == ShardType.ECHO]
        echo_shards.sort(key=lambda s: s.timestamp)

        if len(echo_shards) <= max_echoes:
            return None

        # Take oldest echoes for summarization
        to_summarize = echo_shards[:-max_echoes]

        # Simple summarization: concatenate with timestamps
        lines = [f"[{s.timestamp[:10]}] {s.content[:100]}..." for s in to_summarize]
        summary = "SUMMARIZED CONVERSATION:\n" + "\n".join(lines)

        # Create CHRONICLE shard
        self.create_shard(
            content=summary,
            shard_type=ShardType.CHRONICLE,
            tags=["summary"],
            source="system"
        )

        # Remove summarized echoes
        for shard in to_summarize:
            self.shards.remove(shard)

        return summary

    def search_shards(
        self,
        query: str,
        shard_type: Optional[ShardType] = None,
        semantic: bool = False,
    ) -> list[MemoryShard]:
        """Search shards by content or tags.

        Args:
            query: Search query (keyword or semantic)
            shard_type: Optional filter by shard type
            semantic: If True, use embedding-based cosine similarity
                      ranking via nomic-embed-text. Falls back to keyword
                      on any failure. Expensive on Pi 5 — use deliberately.

        Returns:
            List of matching shards
        """
        if semantic:
            try:
                return self._semantic_search(query, shard_type)
            except Exception:
                pass  # Fall back to keyword

        query_lower = query.lower()
        results = []

        for shard in self.shards:
            if shard_type and shard.shard_type != shard_type:
                continue

            # Search in content
            if query_lower in shard.content.lower():
                results.append(shard)
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in shard.tags):
                results.append(shard)

        return results

    def _semantic_search(
        self,
        query: str,
        shard_type: Optional[ShardType] = None,
        top_k: int = 5,
    ) -> list[MemoryShard]:
        """Embedding-based semantic search over memory shards.

        Uses nomic-embed-text via Ollama to embed both the query and
        candidate shard contents, then ranks by cosine similarity.

        Expensive (~2-5s for typical shard counts of 10-50).
        """
        import numpy as np
        import requests

        candidates = self.shards
        if shard_type:
            candidates = [s for s in candidates if s.shard_type == shard_type]
        if not candidates:
            return []

        # Embed query + all candidate contents in one batch
        texts = [query] + [s.content[:500] for s in candidates]
        resp = requests.post(
            "http://localhost:11434/api/embed",
            json={"model": "nomic-embed-text", "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        embeddings = np.array(resp.json()["embeddings"], dtype="float32")

        # Cosine similarity: query vs each shard
        query_vec = embeddings[0]
        shard_vecs = embeddings[1:]
        norms_q = np.linalg.norm(query_vec)
        norms_s = np.linalg.norm(shard_vecs, axis=1)
        # Avoid division by zero
        norms_s[norms_s == 0] = 1.0
        similarities = shard_vecs @ query_vec / (norms_s * norms_q)

        # Sort by descending similarity
        ranked_indices = np.argsort(-similarities)[:top_k]
        return [candidates[i] for i in ranked_indices if similarities[i] > 0.3]

    def search_by_tags(
        self,
        prompt_keywords: set,
        budget: int = 400,
    ) -> list[MemoryShard]:
        """Return ANCHOR shards whose tags overlap with prompt keywords.

        Scored by overlap count, filled to budget. Used by the Narrative
        Intelligence Layer (WO-V47.0) for Story Card pattern retrieval.

        Args:
            prompt_keywords: Set of lowercased keyword strings.
            budget: Maximum token budget for returned shards.

        Returns:
            List of MemoryShard objects fitting within budget.
        """
        if not prompt_keywords:
            return []

        candidates = []
        for shard in self.shards:
            if shard.shard_type != ShardType.ANCHOR:
                continue
            tag_set = {t.lower() for t in shard.tags}
            overlap = len(prompt_keywords & tag_set)
            if overlap > 0:
                candidates.append((overlap, shard))

        # Sort by overlap count descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Fill to budget
        result = []
        used = 0
        for _score, shard in candidates:
            if used + shard.token_estimate > budget:
                break
            result.append(shard)
            used += shard.token_estimate
        return result

    def clear_echoes(self) -> int:
        """Remove all ECHO shards (for session reset).

        Returns:
            Count of removed shards
        """
        echo_shards = [s for s in self.shards if s.shard_type == ShardType.ECHO]
        count = len(echo_shards)

        for shard in echo_shards:
            self.shards.remove(shard)

        return count


# =============================================================================
# STANDALONE DEMO
# =============================================================================

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()

    console.print(Panel(
        "[bold cyan]CODEX MEMORY ENGINE — STANDALONE DEMO[/bold cyan]\n\n"
        "[dim]Testing Memory Shard creation, context weaving, and persistence[/dim]",
        box=box.DOUBLE,
        border_style="cyan"
    ))
    console.print()

    # Create engine
    memory = CodexMemoryEngine(max_tokens=8192)

    # Ingest a world
    console.print("[bold]1. Ingesting world state...[/bold]")
    world_data = {
        "name": "The Iron Reach",
        "genre": "Dark Fantasy",
        "tone": "grim",
        "terms": {"crown": "The General", "crew": "The Resistance"},
        "grapes": {
            "geography": "Frozen tundra wasteland",
            "religion": "Ancestor spirit worship",
            "politics": "Military junta (war council)",
            "economics": "Rationed supplies, black market thrives",
            "social": "Rigid hierarchy, deserters hunted",
            "achievements": "Gunpowder firearms, fortified bunkers",
        },
        "primer": "The Iron Reach is a frozen wasteland ruled by the General's iron fist. Survival is brutal. Loyalty is everything.",
    }
    master = memory.ingest_world_state(world_data)
    console.print(f"[green]✓ MASTER shard created: {master.id} ({master.token_estimate} tokens)[/green]")
    console.print()

    # Simulate conversation
    console.print("[bold]2. Simulating conversation turns...[/bold]")
    for i in range(8):
        memory.create_shard(
            f"I approach the gate and demand entry. My breath frosts in the cold air.",
            shard_type="ECHO",
            source="user"
        )
        memory.create_shard(
            f"The guard eyes you with suspicion. 'State your business,' he growls, hand on his sword hilt. The wind carries ash from the burning fields beyond.",
            shard_type="ECHO",
            source="mimir"
        )
    console.print(f"[green]✓ Created {8*2} ECHO shards[/green]")
    console.print()

    # Add a key event (ANCHOR)
    console.print("[bold]3. Recording a key event...[/bold]")
    anchor = memory.create_shard(
        "You witnessed the General execute a deserter in the town square. The crowd watched in silence. The Resistance recruiter approached you afterward.",
        shard_type="ANCHOR",
        tags=["npc:recruiter", "event:execution"],
        source="system"
    )
    console.print(f"[green]✓ ANCHOR shard created: {anchor.id}[/green]")
    console.print()

    # Weave context
    console.print("[bold]4. Weaving context within token budget...[/bold]")
    context = memory.weave_context()
    console.print(f"[dim]Context length: {len(context)} characters (~{len(context)//4} tokens)[/dim]")
    console.print()

    # Display usage report
    console.print("[bold]5. Memory usage report:[/bold]")
    report = memory.get_usage_report()

    table = Table(box=box.ROUNDED, border_style="gold1")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Shards", str(report["total_shards"]))
    table.add_row("MASTER Shards", str(report["master_count"]))
    table.add_row("ANCHOR Shards", str(report["anchor_count"]))
    table.add_row("ECHO Shards", str(report["echo_count"]))
    table.add_row("CHRONICLE Shards", str(report["chronicle_count"]))
    table.add_row("Pinned Shards", str(report["pinned_count"]))
    table.add_row("Total Tokens", str(report["total_tokens"]))
    table.add_row("Budget", str(report["budget"]))
    table.add_row("Headroom", f"{report['headroom']} tokens", style="green" if report["headroom"] > 0 else "red")

    console.print(table)
    console.print()

    # Test save/load
    console.print("[bold]6. Testing persistence...[/bold]")
    import tempfile
    _, tmp_save = tempfile.mkstemp(suffix="_test_memory.json")
    save_path = Path(tmp_save)
    memory.save_to_disk(save_path)
    console.print(f"[green]✓ Saved to {save_path}[/green]")

    # Load into new engine
    memory2 = CodexMemoryEngine()
    memory2.load_from_disk(save_path)
    console.print(f"[green]✓ Loaded {len(memory2.shards)} shards from disk[/green]")
    console.print()

    # Test search
    console.print("[bold]7. Testing shard search...[/bold]")
    results = memory.search_shards("recruiter")
    console.print(f"[green]✓ Found {len(results)} shard(s) matching 'recruiter'[/green]")
    if results:
        console.print(f"[dim]  First match: {results[0].content[:60]}...[/dim]")
    console.print()

    # Test message weaving
    console.print("[bold]8. Testing message weaving for chat API...[/bold]")
    messages = memory.weave_messages(system_prompt="You are Mimir, the C.O.D.E.X. Dungeon Master.")
    console.print(f"[green]✓ Wove {len(messages)} messages[/green]")
    console.print(f"[dim]  Message structure:[/dim]")
    for i, msg in enumerate(messages[:3]):
        role = msg["role"]
        preview = msg["content"][:50].replace("\n", " ")
        console.print(f"    {i+1}. [{role}] {preview}...")
    console.print()

    console.print(Panel(
        "[bold green]✓ ALL TESTS PASSED[/bold green]\n\n"
        "[dim]Memory Engine is operational.[/dim]",
        box=box.HEAVY,
        border_style="green"
    ))

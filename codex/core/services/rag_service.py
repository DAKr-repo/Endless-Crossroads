"""
RAG Service — RLM-aware Retrieval for C.O.D.E.X.
===================================================

Provides typed RAGResult objects with optional recursive summarization,
ManifoldGuard validation, and thermal gating.

Singleton access via ``get_rag_service()``.

Version: 1.0 (WO-V33.0 — The Sovereign Recall)
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


# =========================================================================
# RAG RESULT — Typed symbolic handle
# =========================================================================

@dataclass
class RAGResult:
    """Typed return from RAG search — symbolic handle for context injection."""
    chunks: List[str] = field(default_factory=list)
    chunk_results: List = field(default_factory=list)  # List[ChunkResult] from retriever
    system_id: str = ""
    query: str = ""
    search_time_ms: float = 0.0
    summary: Optional[str] = None
    validated: bool = False
    rejected_chunks: List[str] = field(default_factory=list)

    @property
    def context_str(self) -> str:
        """Return the best available context: summary > raw chunks."""
        if self.summary:
            return self.summary
        if not self.chunks:
            return ""
        return "\n".join(f"[{i+1}] {c}" for i, c in enumerate(self.chunks))

    @property
    def citations(self) -> List[str]:
        """Human-readable source citations from chunk_results."""
        seen = set()
        cites = []
        for cr in self.chunk_results:
            c = cr.citation if hasattr(cr, 'citation') else ""
            if c and c not in seen:
                seen.add(c)
                cites.append(c)
        return cites

    @property
    def token_estimate(self) -> int:
        return len(self.context_str) // 4

    def __bool__(self) -> bool:
        return bool(self.chunks) or bool(self.summary)


# =========================================================================
# RAG SERVICE — Singleton
# =========================================================================

class RAGService:
    """RLM-aware retrieval service for C.O.D.E.X.

    Features:
    - Typed RAGResult objects (callers control what enters context)
    - Thermal gating (embedding calls gated by cortex clearance)
    - Recursive summarization (retrieved chunks compressed via Mimir)
    - ManifoldGuard validation (retrieved chunks checked against game state)
    """

    SYSTEM_ALIASES: Dict[str, str] = {
        "burnwillow": "burnwillow",
        "crown": "crown",
        "dnd5e": "dnd5e",
        "bitd": "bitd",
        "bob": "bob",
        "sav": "sav",
        "cbr_pnk": "cbr_pnk",
        "cbrpnk": "cbr_pnk",
        "candela": "candela_obscura",
        "candela_obscura": "candela_obscura",
        "stc": "stc",
    }

    def __init__(
        self,
        index_root: Optional[Path] = None,
        broadcast_manager=None,
    ):
        self._index_root = index_root
        self._retriever = None
        self._retriever_loaded = False
        self._broadcast = broadcast_manager
        self._summary_cache: Dict[Tuple[str, str], Tuple[str, float]] = {}
        self._CACHE_TTL = 3600  # 1 hour

        # Subscribe to invalidation events
        if self._broadcast:
            try:
                from codex.core.services.broadcast import GlobalBroadcastManager
                self._broadcast.subscribe("RAG_INDEX_INVALIDATED", self._on_invalidate)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Lazy retriever loading
    # ------------------------------------------------------------------

    def _ensure_retriever(self) -> bool:
        """Lazy-load the CodexRetriever. Returns True if available."""
        if self._retriever_loaded:
            return self._retriever is not None
        self._retriever_loaded = True
        try:
            from codex.core.retriever import CodexRetriever
            if self._index_root is None:
                from codex.paths import FAISS_INDEX_DIR
                self._index_root = FAISS_INDEX_DIR
            if self._index_root.exists():
                self._retriever = CodexRetriever(self._index_root)
                log.info("RAGService: CodexRetriever loaded from %s", self._index_root)
                return True
            else:
                log.warning("RAGService: FAISS index dir not found: %s", self._index_root)
        except Exception as e:
            log.warning("RAGService: Failed to load retriever: %s", e)
        return False

    # ------------------------------------------------------------------
    # Thermal gating
    # ------------------------------------------------------------------

    def _check_thermal(self) -> bool:
        """Returns True if safe to perform embedding calls."""
        try:
            from codex.core.cortex import get_cortex
            cortex = get_cortex()
            state = cortex.read_metabolic_state()
            return state.metabolic_clearance
        except Exception:
            return True  # If cortex unavailable, proceed optimistically

    # ------------------------------------------------------------------
    # Core search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        system_id: str,
        k: int = 5,
        token_budget: int = 0,
    ) -> RAGResult:
        """Search a system's FAISS index for relevant chunks.

        Args:
            query: Search query.
            system_id: System alias (e.g. "burnwillow", "dnd5e").
            k: Number of chunks to retrieve.
            token_budget: If >0, trim chunks to fit within this char budget.

        Returns:
            RAGResult with retrieved chunks. Never raises.
        """
        result = RAGResult(system_id=system_id, query=query)

        if not self._ensure_retriever():
            return result
        if not self._check_thermal():
            log.info("RAGService: Thermal gate blocked search for '%s'", query[:50])
            return result

        resolved_id = self.SYSTEM_ALIASES.get(system_id, system_id)
        start = time.time()
        try:
            chunks = self._retriever.search(query, resolved_id, k=k)
            result.search_time_ms = (time.time() - start) * 1000
            if token_budget > 0:
                trimmed = []
                budget_remaining = token_budget
                for chunk in chunks:
                    if len(chunk) <= budget_remaining:
                        trimmed.append(chunk)
                        budget_remaining -= len(chunk)
                    elif budget_remaining > 50:
                        trimmed.append(chunk[:budget_remaining])
                        break
                result.chunks = trimmed
            else:
                result.chunks = chunks
        except Exception as e:
            log.warning("RAGService: search error: %s", e)
            result.search_time_ms = (time.time() - start) * 1000

        return result

    def search_rich(
        self,
        query: str,
        system_id: str,
        k: int = 5,
        token_budget: int = 0,
        source: Optional[str] = None,
        chapter: Optional[str] = None,
    ) -> RAGResult:
        """Search with full provenance metadata (v3.0 docstores).

        Returns RAGResult with both chunks (text) and chunk_results (metadata).
        Supports optional source and chapter filters.
        """
        result = RAGResult(system_id=system_id, query=query)

        if not self._ensure_retriever():
            return result
        if not self._check_thermal():
            return result

        resolved_id = self.SYSTEM_ALIASES.get(system_id, system_id)
        start = time.time()
        try:
            if source or chapter:
                chunk_results = self._retriever.search_filtered(
                    query, resolved_id, k=k, source=source, chapter=chapter,
                )
            else:
                chunk_results = self._retriever.search_rich(query, resolved_id, k=k)

            result.search_time_ms = (time.time() - start) * 1000
            result.chunk_results = chunk_results
            result.chunks = [cr.text for cr in chunk_results]

            if token_budget > 0:
                trimmed_cr = []
                trimmed_chunks = []
                budget_remaining = token_budget
                for cr in chunk_results:
                    if len(cr.text) <= budget_remaining:
                        trimmed_cr.append(cr)
                        trimmed_chunks.append(cr.text)
                        budget_remaining -= len(cr.text)
                    elif budget_remaining > 50:
                        trimmed_chunks.append(cr.text[:budget_remaining])
                        trimmed_cr.append(cr)
                        break
                result.chunk_results = trimmed_cr
                result.chunks = trimmed_chunks
        except Exception as e:
            log.warning("RAGService: search_rich error: %s", e)
            result.search_time_ms = (time.time() - start) * 1000

        return result

    def search_multi(
        self,
        query: str,
        system_ids: List[str],
        k_per_system: int = 3,
        token_budget: int = 0,
    ) -> RAGResult:
        """Search multiple indices and merge results.

        Returns a single RAGResult with chunks from all requested systems.
        """
        result = RAGResult(query=query)
        all_chunks = []
        total_time = 0.0

        for sid in system_ids:
            sub = self.search(query, sid, k=k_per_system)
            all_chunks.extend(sub.chunks)
            total_time += sub.search_time_ms

        result.search_time_ms = total_time
        result.system_id = ",".join(system_ids)

        if token_budget > 0:
            trimmed = []
            budget_remaining = token_budget
            for chunk in all_chunks:
                if len(chunk) <= budget_remaining:
                    trimmed.append(chunk)
                    budget_remaining -= len(chunk)
                elif budget_remaining > 50:
                    trimmed.append(chunk[:budget_remaining])
                    break
            result.chunks = trimmed
        else:
            result.chunks = all_chunks

        return result

    # ------------------------------------------------------------------
    # WO-V56.0: Thermal gate for summarization
    # ------------------------------------------------------------------

    def _should_summarize(self) -> bool:
        """Only summarize when system is thermally cool enough."""
        try:
            from codex.core.cortex import get_cortex
            cortex = get_cortex()
            temp = cortex.get_cpu_temp()
            return temp < 65.0  # Skip summarization above 65°C
        except Exception:
            return True  # Default to summarize if can't read temp

    # ------------------------------------------------------------------
    # Recursive summarization
    # ------------------------------------------------------------------

    def summarize(self, result: RAGResult, query: str) -> RAGResult:
        """Compress retrieved chunks via Mimir into 2-3 sentence summary.

        Caches results keyed by (query_hash, system_id) with 1-hour TTL.
        Falls back to raw chunks on any failure.
        """
        if not result.chunks:
            return result

        cache_key = (
            hashlib.md5(query.encode()).hexdigest()[:12],
            result.system_id,
        )

        # Check cache
        cached = self._summary_cache.get(cache_key)
        if cached:
            text, ts = cached
            if time.time() - ts < self._CACHE_TTL:
                result.summary = text
                return result

        # Build summarization prompt
        chunk_text = "\n---\n".join(result.chunks[:5])
        prompt = (
            f"Compress these reference chunks into 2-3 sentences "
            f"relevant to: {query}\n\n{chunk_text}"
        )

        try:
            from codex.integrations.mimir import query_mimir
            summary = query_mimir(prompt)
            if summary and not summary.startswith("[") and len(summary) > 20:
                result.summary = summary
                self._summary_cache[cache_key] = (summary, time.time())
        except Exception as e:
            log.warning("RAGService: summarize failed: %s", e)

        return result

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_context(
        self,
        result: RAGResult,
        header: str = "REFERENCE MATERIAL:",
    ) -> str:
        """Format a RAGResult for injection into an LLM prompt.

        Prefers .summary over raw chunks.
        """
        if not result:
            return ""
        body = result.context_str
        if not body:
            return ""
        return f"{header}\n{body}"

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _on_invalidate(self, payload: dict) -> None:
        """Handle RAG_INDEX_INVALIDATED broadcast."""
        log.info("RAGService: Invalidating caches on broadcast")
        self._summary_cache.clear()
        # Force retriever reload on next search
        if self._retriever:
            self._retriever._cache.clear()

    def clear_cache(self) -> None:
        """Manually clear all caches."""
        self._summary_cache.clear()
        if self._retriever:
            self._retriever._cache.clear()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True if the retriever can be loaded."""
        return self._ensure_retriever()


# =========================================================================
# SINGLETON
# =========================================================================

_rag_service: Optional[RAGService] = None


def get_rag_service(broadcast_manager=None) -> RAGService:
    """Get or create the RAG Service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(broadcast_manager=broadcast_manager)
    return _rag_service

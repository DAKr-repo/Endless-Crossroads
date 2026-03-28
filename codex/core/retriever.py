"""
codex_retriever.py - FAISS-backed RAG Retrieval (LangChain-Free)
================================================================
Uses native faiss-cpu and numpy for vector search.
Embeddings via direct Ollama API calls to nomic-embed-text.

Version: 3.0 (WO-V139 — Page Index)
"""

import json
import pickle
import requests
import numpy as np
import faiss
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ChunkResult:
    """A retrieved chunk with full provenance metadata."""
    text: str = ""
    source: str = ""
    source_file: str = ""
    page_start: int = 0
    page_end: int = 0
    system_id: str = ""
    priority: int = 2
    chapter: Optional[str] = None
    score: float = 0.0  # L2 distance from FAISS (lower = closer)

    @property
    def citation(self) -> str:
        """Human-readable source citation."""
        if not self.source:
            return ""
        if self.page_start and self.page_end and self.page_start != self.page_end:
            return f"{self.source}, pp. {self.page_start}-{self.page_end}"
        elif self.page_start:
            return f"{self.source}, p. {self.page_start}"
        return self.source


OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"


class CodexRetriever:
    """Retrieves lore chunks from FAISS indices using semantic search."""

    SYSTEM_MAP = {
        "cbr_pnk": "cbr_pnk",
        "dnd5e": "dnd5e",
        "bitd": "bitd",
        "candela_obscura": "candela_obscura",
        "bob": "bob",
        "sav": "sav",
        "stc": "stc",
        "burnwillow": "burnwillow",
        "crown": "crown",
    }

    def __init__(self, index_root: Path):
        self._index_root = Path(index_root)
        self._cache: dict = {}

    def _embed(self, text: str) -> Optional[np.ndarray]:
        """Get embedding vector from Ollama."""
        try:
            resp = requests.post(
                OLLAMA_EMBED_URL,
                json={"model": EMBED_MODEL, "input": text},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings") or data.get("embedding")
            if embeddings:
                vec = embeddings[0] if isinstance(embeddings[0], list) else embeddings
                return np.array(vec, dtype="float32").reshape(1, -1)
        except Exception:
            pass
        return None

    def search(self, query: str, system_id: str, k: int = 5) -> List[str]:
        """Search a system's FAISS index for relevant chunks."""
        loaded = self._load_store(system_id)
        if loaded is None:
            return []

        index, docstore, id_map = loaded
        query_vec = self._embed(query)
        if query_vec is None:
            return []

        try:
            D, I = index.search(query_vec, k)
            results = []
            for idx in I[0]:
                if idx == -1:
                    continue
                doc_id = id_map.get(int(idx))
                if doc_id and doc_id in docstore:
                    entry = docstore[doc_id]
                    # v3.0: entry is a dict with "text" + "meta"
                    # v2.0: entry is a plain string
                    if isinstance(entry, dict):
                        results.append(entry.get("text", ""))
                    else:
                        results.append(entry)
            return results
        except Exception:
            return []

    def search_rich(self, query: str, system_id: str, k: int = 5) -> List[ChunkResult]:
        """Search with full metadata provenance (v3.0 docstores).

        Returns ChunkResult objects with page numbers, source, chapter, etc.
        Falls back gracefully for v2.0 docstores (no page info).
        """
        loaded = self._load_store(system_id)
        if loaded is None:
            return []

        index, docstore, id_map = loaded
        query_vec = self._embed(query)
        if query_vec is None:
            return []

        try:
            D, I = index.search(query_vec, k)
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx == -1:
                    continue
                doc_id = id_map.get(int(idx))
                if not doc_id or doc_id not in docstore:
                    continue

                entry = docstore[doc_id]
                if isinstance(entry, dict):
                    meta = entry.get("meta", {})
                    results.append(ChunkResult(
                        text=entry.get("text", ""),
                        source=meta.get("source", ""),
                        source_file=meta.get("source_file", ""),
                        page_start=meta.get("page_start", 0),
                        page_end=meta.get("page_end", 0),
                        system_id=meta.get("system_id", system_id),
                        priority=meta.get("priority", 2),
                        chapter=meta.get("chapter"),
                        score=float(dist),
                    ))
                else:
                    # v2.0 fallback — plain string, no metadata
                    results.append(ChunkResult(
                        text=entry,
                        system_id=system_id,
                        score=float(dist),
                    ))
            return results
        except Exception:
            return []

    def search_filtered(
        self,
        query: str,
        system_id: str,
        k: int = 5,
        source: Optional[str] = None,
        chapter: Optional[str] = None,
        page_range: Optional[Tuple[int, int]] = None,
    ) -> List[ChunkResult]:
        """Search with metadata filters. Over-fetches then post-filters.

        Args:
            query: Search query.
            system_id: System to search.
            k: Number of results to return after filtering.
            source: Filter to chunks from this source PDF (e.g. "Dragon Heist").
            chapter: Filter to chunks with this chapter tag.
            page_range: Filter to chunks within (start_page, end_page) range.
        """
        # Over-fetch to ensure we get enough after filtering
        raw = self.search_rich(query, system_id, k=k * 4)
        filtered = []
        for cr in raw:
            if source and cr.source.lower() != source.lower():
                continue
            if chapter and (not cr.chapter or chapter.lower() not in cr.chapter.lower()):
                continue
            if page_range:
                p_start, p_end = page_range
                if cr.page_start and (cr.page_end < p_start or cr.page_start > p_end):
                    continue
            filtered.append(cr)
            if len(filtered) >= k:
                break
        return filtered

    def get_toc(self, system_id: str, source_file: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get the TOC index for a system (or a specific source file).

        Returns {source_filename: [{"title": ..., "page": ..., "level": ...}]}
        """
        loaded = self._load_store(system_id)
        if loaded is None:
            return {}

        folder = self.SYSTEM_MAP.get(system_id, system_id)
        json_file = self._index_root / folder / "docstore.json"
        if not json_file.exists():
            return {}

        try:
            data = json.loads(json_file.read_text())
            toc_index = data.get("toc_index", {})
            if source_file:
                entry = toc_index.get(source_file, [])
                return {source_file: entry} if entry else {}
            return toc_index
        except Exception:
            return {}

    def _load_store(self, system_id: str):
        """Lazy-load FAISS index + docstore.
        Returns (index, docstore, id_map) or None."""
        folder = self.SYSTEM_MAP.get(system_id)
        if not folder:
            return None
        if folder in self._cache:
            return self._cache[folder]

        idx_path = self._index_root / folder
        faiss_file = idx_path / "index.faiss"
        if not faiss_file.exists():
            return None

        try:
            index = faiss.read_index(str(faiss_file))

            # Try JSON docstore first, fall back to pickle
            docstore, id_map = {}, {}
            json_file = idx_path / "docstore.json"
            pkl_file = idx_path / "index.pkl"

            if json_file.exists():
                data = json.loads(json_file.read_text())
                docstore = data.get("docstore", {})
                id_map = {int(k): v for k, v in data.get("id_map", {}).items()}
            elif pkl_file.exists():
                docstore, id_map = self._load_langchain_pkl(pkl_file)

            self._cache[folder] = (index, docstore, id_map)
            return self._cache[folder]
        except Exception:
            return None

    @staticmethod
    def _load_langchain_pkl(pkl_file: Path) -> tuple[dict, dict]:
        """Load legacy LangChain-format pickle and extract docstore + id_map."""
        try:
            with open(pkl_file, "rb") as f:
                data = pickle.load(f)
            # LangChain FAISS stores (InMemoryDocstore, {idx: doc_id})
            lc_docstore, lc_id_map = data
            docstore = {}
            for doc_id, doc in lc_docstore._dict.items():
                docstore[doc_id] = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            return docstore, lc_id_map
        except Exception:
            return {}, {}

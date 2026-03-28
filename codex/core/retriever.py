"""
codex_retriever.py - FAISS-backed RAG Retrieval (LangChain-Free)
================================================================
Uses native faiss-cpu and numpy for vector search.
Embeddings via direct Ollama API calls to nomic-embed-text.

Version: 2.0 (WO V27.0 — LangChain excision)
"""

import json
import pickle
import requests
import numpy as np
import faiss
from pathlib import Path
from typing import List, Optional


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

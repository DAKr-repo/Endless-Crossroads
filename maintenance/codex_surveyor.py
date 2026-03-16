#!/usr/bin/env python3
"""
codex_surveyor.py -- FAISS Room Description Miner (LangChain-Free)
==================================================================

Scans FAISS vector indices for location/room descriptions and
synthesizes map-generation prompts.  Outputs are saved to
``vault_maps/{system_id}/`` for the Librarian's map view.

Uses native faiss-cpu + numpy + direct Ollama embedding API.

Version: 2.0 (WO V27.0 — LangChain excision)

Usage:
    python maintenance/codex_surveyor.py                  # survey all
    python maintenance/codex_surveyor.py --system dnd5e   # one system
    python maintenance/codex_surveyor.py --dry-run         # preview only
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import faiss
import requests

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from codex.paths import VAULT_MAPS_DIR

FAISS_DIR = _ROOT / "faiss_index"
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"

# Queries to mine location descriptions from FAISS
_LOCATION_QUERIES = [
    "room description dungeon chamber",
    "location tavern inn shop building",
    "cave temple ruins fortress",
    "city town village settlement",
    "wilderness forest mountain river",
]


def _embed(text: str):
    """Get embedding vector from Ollama."""
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBEDDING_MODEL, "input": text},
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


def _load_faiss_index(system_id: str):
    """Load a FAISS index + docstore for the given system.

    Returns (index, docstore, id_map) or None.
    """
    index_path = FAISS_DIR / system_id
    faiss_file = index_path / "index.faiss"
    if not faiss_file.exists():
        return None

    try:
        index = faiss.read_index(str(faiss_file))

        docstore, id_map = {}, {}
        json_file = index_path / "docstore.json"
        pkl_file = index_path / "index.pkl"

        if json_file.exists():
            data = json.loads(json_file.read_text())
            docstore = data.get("docstore", {})
            id_map = {int(k): v for k, v in data.get("id_map", {}).items()}
        elif pkl_file.exists():
            # Legacy LangChain pickle fallback
            import pickle
            try:
                with open(pkl_file, "rb") as f:
                    lc_data = pickle.load(f)
                lc_docstore, lc_id_map = lc_data
                for doc_id, doc in lc_docstore._dict.items():
                    docstore[doc_id] = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                id_map = lc_id_map
            except Exception:
                pass

        return (index, docstore, id_map)
    except Exception as e:
        print(f"[WARN] Could not load FAISS for {system_id}: {e}")
        return None


def _search(store_tuple, query: str, k: int = 20) -> list:
    """Search a FAISS index for relevant chunks."""
    index, docstore, id_map = store_tuple
    query_vec = _embed(query)
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
                results.append({"content": docstore[doc_id], "source": "faiss"})
        return results
    except Exception:
        return []


def _extract_locations(store_tuple, system_id: str, limit: int = 20) -> list:
    """Query the FAISS store for location-like passages."""
    results = []
    seen_content = set()

    for query in _LOCATION_QUERIES:
        docs = _search(store_tuple, query, k=limit)

        for doc in docs:
            content = doc["content"].strip()
            key = content[:100]
            if key in seen_content:
                continue
            seen_content.add(key)

            results.append({
                "system_id": system_id,
                "query": query,
                "content": content[:500],
                "source": doc.get("source", "unknown"),
            })

    return results


def _save_survey_results(system_id: str, locations: list, dry_run: bool):
    """Write extracted location data to vault_maps/{system_id}/survey.json."""
    output_dir = VAULT_MAPS_DIR / system_id
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "system_id": system_id,
        "surveyed_at": datetime.now().isoformat(timespec="seconds"),
        "location_count": len(locations),
        "locations": locations,
    }

    if dry_run:
        print(f"  [DRY RUN] Would write {len(locations)} locations to "
              f"vault_maps/{system_id}/survey.json")
        return

    output_path = output_dir / "survey.json"
    output_path.write_text(json.dumps(output, indent=2))
    print(f"  Wrote {len(locations)} locations to {output_path}")


def survey_system(system_id: str, dry_run: bool = False) -> int:
    """Mine location descriptions from a single system's FAISS index."""
    print(f"[Surveyor] Scanning {system_id}...")
    store_tuple = _load_faiss_index(system_id)
    if store_tuple is None:
        print(f"  No FAISS index found for {system_id}, skipping.")
        return 0

    locations = _extract_locations(store_tuple, system_id)
    if locations:
        _save_survey_results(system_id, locations, dry_run)
    else:
        print(f"  No location passages found for {system_id}.")

    return len(locations)


def survey_all(dry_run: bool = False) -> dict:
    """Survey all available FAISS indices."""
    results = {}
    if not FAISS_DIR.exists():
        print(f"[WARN] FAISS directory not found: {FAISS_DIR}")
        return results

    for child in sorted(FAISS_DIR.iterdir()):
        if child.is_dir() and (child / "index.faiss").exists():
            count = survey_system(child.name, dry_run=dry_run)
            results[child.name] = count

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Mine FAISS indices for location descriptions"
    )
    parser.add_argument(
        "--system", type=str, default=None,
        help="Survey a specific system (e.g. dnd5e)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without writing files"
    )
    args = parser.parse_args()

    if args.system:
        count = survey_system(args.system, dry_run=args.dry_run)
        print(f"\n[Surveyor] Found {count} locations for {args.system}.")
    else:
        results = survey_all(dry_run=args.dry_run)
        total = sum(results.values())
        print(f"\n[Surveyor] Total: {total} locations across "
              f"{len(results)} systems.")


if __name__ == "__main__":
    main()

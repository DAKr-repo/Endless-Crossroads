#!/usr/bin/env python3
"""
scripts/verify_content.py — Source Verification Audit Tool
============================================================
Compares authored game content (zone files, bestiary, NPCs) against
the FAISS-indexed source PDFs to flag potential hallucinations.

For each authored item, queries the RAG index for matching source
content and produces a verification report.

Usage:
    python scripts/verify_content.py --zone vault_maps/modules/dragon_heist/
    python scripts/verify_content.py --bestiary config/bestiary/dnd5e.json
    python scripts/verify_content.py --npcs config/npcs/dnd5e.json
    python scripts/verify_content.py --all --system dnd5e
    python scripts/verify_content.py --zone vault_maps/modules/dragon_heist/ --report reports/

WO-V158-163: Source verification audit.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_ROOT = PROJECT_ROOT / "faiss_index"

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"
EMBED_TIMEOUT = 30

# Similarity thresholds
VERIFIED_THRESHOLD = 0.75    # High similarity = likely accurate
SUSPECT_THRESHOLD = 0.55     # Medium = close but may differ
# Below SUSPECT = no source found or very different


def embed_query(text: str) -> Optional[np.ndarray]:
    """Embed a query string via Ollama."""
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBED_MODEL, "input": text[:500]},
            timeout=EMBED_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings") or data.get("embedding")
        if embeddings:
            vec = embeddings[0] if isinstance(embeddings[0], list) else embeddings
            return np.array(vec, dtype="float32")
    except Exception as e:
        print(f"  [WARN] Embed failed: {e}")
    return None


def load_faiss_index(system_id: str):
    """Load a FAISS index and docstore for a system."""
    import faiss

    index_dir = INDEX_ROOT / system_id
    faiss_path = index_dir / "index.faiss"
    docstore_path = index_dir / "docstore.json"

    if not faiss_path.exists():
        print(f"[ERROR] No FAISS index for {system_id} at {faiss_path}")
        return None, None

    index = faiss.read_index(str(faiss_path))

    docstore = {}
    if docstore_path.exists():
        data = json.loads(docstore_path.read_text())
        docstore = data.get("docstore", {})

    return index, docstore


def search_index(index, docstore: dict, query_vec: np.ndarray, k: int = 3):
    """Search FAISS index and return top-k results with similarity scores."""
    if index is None or query_vec is None:
        return []

    query_vec_2d = query_vec.reshape(1, -1)
    distances, indices = index.search(query_vec_2d, k)

    results = []
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx < 0:
            continue
        doc_key = f"doc_{idx}"
        text = docstore.get(doc_key, "")
        # Convert L2 distance to similarity (approximate)
        similarity = 1.0 / (1.0 + dist)
        results.append({
            "rank": i + 1,
            "similarity": round(similarity, 4),
            "distance": round(float(dist), 4),
            "doc_key": doc_key,
            "text": text[:300],
        })

    return results


def verify_item(
    index, docstore: dict, item_name: str, item_text: str,
    cooldown: float = 0.5,
) -> dict:
    """Verify a single authored item against the FAISS index.

    Returns a verification dict with: name, status, similarity, source_excerpt.
    """
    # Build query from the item
    query = f"{item_name}: {item_text[:300]}"
    vec = embed_query(query)
    if vec is None:
        return {
            "name": item_name,
            "status": "error",
            "similarity": 0.0,
            "source_excerpt": "",
            "authored_excerpt": item_text[:200],
        }

    time.sleep(cooldown)  # Thermal safety

    results = search_index(index, docstore, vec, k=3)
    if not results:
        return {
            "name": item_name,
            "status": "no_source_found",
            "similarity": 0.0,
            "source_excerpt": "",
            "authored_excerpt": item_text[:200],
        }

    best = results[0]
    sim = best["similarity"]

    if sim >= VERIFIED_THRESHOLD:
        status = "verified"
    elif sim >= SUSPECT_THRESHOLD:
        status = "suspect"
    else:
        status = "unverified"

    return {
        "name": item_name,
        "status": status,
        "similarity": sim,
        "source_excerpt": best["text"][:200],
        "authored_excerpt": item_text[:200],
        "top_results": results,
    }


# =============================================================================
# Zone file verification
# =============================================================================

def verify_zone_files(zone_dir: str, system_id: str = "dnd5e") -> List[dict]:
    """Verify all rooms in a zone directory against source PDFs."""
    zone_path = Path(zone_dir)
    if not zone_path.is_dir():
        print(f"[ERROR] Not a directory: {zone_dir}")
        return []

    index, docstore = load_faiss_index(system_id)
    if index is None:
        return []

    results = []
    json_files = sorted(zone_path.glob("*.json"))

    for json_file in json_files:
        if json_file.name == "module_manifest.json":
            continue

        try:
            data = json.loads(json_file.read_text())
        except json.JSONDecodeError:
            continue

        rooms = data.get("rooms", data.get("locations", {}))
        module_name = zone_path.name

        for room_id, room in rooms.items():
            ch = room.get("content_hints", {})
            desc = ch.get("description", "")
            if not desc:
                continue

            # Verify room description
            item_name = f"{module_name}/{json_file.stem}/room_{room_id}"
            print(f"  Verifying: {item_name}...")
            result = verify_item(index, docstore, item_name, desc)
            result["file"] = json_file.name
            result["room_id"] = room_id
            result["type"] = "room_description"
            results.append(result)

            # Verify NPCs
            for npc in ch.get("npcs", []):
                if isinstance(npc, dict):
                    npc_name = npc.get("name", "Unknown")
                    npc_text = f"{npc_name} ({npc.get('role', '')}): {npc.get('dialogue', '')}"
                    npc_result = verify_item(index, docstore, f"{item_name}/NPC:{npc_name}", npc_text)
                    npc_result["file"] = json_file.name
                    npc_result["room_id"] = room_id
                    npc_result["type"] = "npc"
                    results.append(npc_result)

            # Verify read_aloud
            read_aloud = ch.get("read_aloud", "")
            if read_aloud:
                ra_result = verify_item(index, docstore, f"{item_name}/read_aloud", read_aloud)
                ra_result["file"] = json_file.name
                ra_result["room_id"] = room_id
                ra_result["type"] = "read_aloud"
                results.append(ra_result)

    return results


# =============================================================================
# Bestiary verification
# =============================================================================

def verify_bestiary(bestiary_path: str, system_id: str = "dnd5e") -> List[dict]:
    """Verify bestiary descriptions against source PDFs."""
    path = Path(bestiary_path)
    if not path.exists():
        print(f"[ERROR] File not found: {bestiary_path}")
        return []

    index, docstore = load_faiss_index(system_id)
    if index is None:
        return []

    data = json.loads(path.read_text())
    tiers = data.get("tiers", data)
    results = []

    for tier_key, entries in tiers.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "")
            desc = entry.get("description", "")
            if not name:
                continue

            query_text = f"{name}: {desc}" if desc else name
            print(f"  Verifying bestiary: {name}...")
            result = verify_item(index, docstore, f"bestiary/{name}", query_text)
            result["tier"] = tier_key
            result["type"] = "bestiary"
            result["has_description"] = bool(desc)
            results.append(result)

    return results


# =============================================================================
# NPC verification
# =============================================================================

def verify_npcs(npc_path: str, system_id: str = "dnd5e") -> List[dict]:
    """Verify NPC data against source PDFs."""
    path = Path(npc_path)
    if not path.exists():
        print(f"[ERROR] File not found: {npc_path}")
        return []

    index, docstore = load_faiss_index(system_id)
    if index is None:
        return []

    data = json.loads(path.read_text())
    results = []

    for section in ("named_npcs", "generic_templates"):
        for npc in data.get(section, []):
            if not isinstance(npc, dict):
                continue
            name = npc.get("name", "")
            desc = npc.get("description", "")
            source = npc.get("source", "")
            if not name:
                continue

            query_text = f"{name}: {desc}"
            if source:
                query_text += f" (Source: {source})"

            print(f"  Verifying NPC: {name}...")
            result = verify_item(index, docstore, f"npc/{name}", query_text)
            result["type"] = "npc"
            result["section"] = section
            result["claimed_source"] = source
            results.append(result)

    return results


# =============================================================================
# Report generation
# =============================================================================

def generate_report(results: List[dict], output_path: Optional[str] = None) -> str:
    """Generate a verification report from results."""
    verified = [r for r in results if r["status"] == "verified"]
    suspect = [r for r in results if r["status"] == "suspect"]
    unverified = [r for r in results if r["status"] == "unverified"]
    errors = [r for r in results if r["status"] in ("error", "no_source_found")]

    lines = [
        "=" * 70,
        "  SOURCE VERIFICATION AUDIT REPORT",
        "=" * 70,
        "",
        f"Total items checked: {len(results)}",
        f"  Verified (>={VERIFIED_THRESHOLD:.0%} match):  {len(verified)}",
        f"  Suspect ({SUSPECT_THRESHOLD:.0%}-{VERIFIED_THRESHOLD:.0%} match):  {len(suspect)}",
        f"  Unverified (<{SUSPECT_THRESHOLD:.0%} match):   {len(unverified)}",
        f"  Errors/No source:          {len(errors)}",
        "",
    ]

    if suspect:
        lines.append("-" * 70)
        lines.append("SUSPECT ITEMS (close but may differ from source):")
        lines.append("-" * 70)
        for r in suspect:
            lines.append(f"\n  [{r['similarity']:.2%}] {r['name']}")
            lines.append(f"    Authored: {r.get('authored_excerpt', '')[:100]}...")
            lines.append(f"    Source:   {r.get('source_excerpt', '')[:100]}...")

    if unverified:
        lines.append("")
        lines.append("-" * 70)
        lines.append("UNVERIFIED ITEMS (low match — likely hallucinated or no source):")
        lines.append("-" * 70)
        for r in unverified:
            lines.append(f"\n  [{r['similarity']:.2%}] {r['name']}")
            lines.append(f"    Authored: {r.get('authored_excerpt', '')[:100]}...")
            if r.get("source_excerpt"):
                lines.append(f"    Best match: {r['source_excerpt'][:100]}...")
            if r.get("claimed_source"):
                lines.append(f"    Claimed source: {r['claimed_source']}")

    report = "\n".join(lines)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        print(f"\nReport saved to: {out}")

    return report


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Verify authored game content against source PDFs via FAISS index."
    )
    parser.add_argument("--system", default="dnd5e", help="System ID for FAISS index (default: dnd5e)")
    parser.add_argument("--zone", metavar="DIR", help="Verify zone files in a directory")
    parser.add_argument("--bestiary", metavar="FILE", help="Verify bestiary JSON file")
    parser.add_argument("--npcs", metavar="FILE", help="Verify NPC JSON file")
    parser.add_argument("--report", metavar="FILE", help="Save report to file")
    parser.add_argument("--all", action="store_true", help="Run all verifications for the system")

    args = parser.parse_args()
    all_results: List[dict] = []

    if args.zone:
        print(f"\n=== Verifying zone files: {args.zone} ===")
        all_results.extend(verify_zone_files(args.zone, args.system))

    if args.bestiary:
        print(f"\n=== Verifying bestiary: {args.bestiary} ===")
        all_results.extend(verify_bestiary(args.bestiary, args.system))

    if args.npcs:
        print(f"\n=== Verifying NPCs: {args.npcs} ===")
        all_results.extend(verify_npcs(args.npcs, args.system))

    if args.all:
        print(f"\n=== Full verification for system: {args.system} ===")

        # Zone files
        zones_root = PROJECT_ROOT / "vault_maps" / "modules"
        system_prefix = args.system.replace("5e", "")  # dnd5e -> dnd
        for zone_dir in sorted(zones_root.iterdir()):
            if zone_dir.is_dir() and not zone_dir.name.startswith(("crown_", "bob_", "bitd_", "sav_", "cbrpnk_", "candela_", "stc_", "sample_", "burnwillow")):
                print(f"\n--- Zone: {zone_dir.name} ---")
                all_results.extend(verify_zone_files(str(zone_dir), args.system))

        # Bestiary
        bestiary = PROJECT_ROOT / "config" / "bestiary" / f"{args.system}.json"
        if bestiary.exists():
            print(f"\n--- Bestiary ---")
            all_results.extend(verify_bestiary(str(bestiary), args.system))

        # NPCs
        npcs = PROJECT_ROOT / "config" / "npcs" / f"{args.system}.json"
        if npcs.exists():
            print(f"\n--- NPCs ---")
            all_results.extend(verify_npcs(str(npcs), args.system))

    if all_results:
        report = generate_report(all_results, args.report)
        print(f"\n{report}")

        # Save raw results as JSON
        if args.report:
            json_path = Path(args.report).with_suffix(".json")
            json_path.write_text(json.dumps(all_results, indent=2, default=str))
            print(f"Raw results saved to: {json_path}")
    else:
        print("\nNo items to verify. Use --zone, --bestiary, --npcs, or --all.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
scripts/reextract_zones.py — Re-extract zone files from FAISS-indexed source PDFs.

Replaces hallucinated content_hints (description, read_aloud, NPCs) with
text sourced from the actual indexed PDF chunks.

For each room in a zone file:
1. Builds a search query from zone name + draft description + NPC names
2. Queries FAISS index with embedding for room-specific chunk retrieval
3. Gemma 4 polishes source chunks into clean GM text
4. Writes updated zone file with source-grounded content

Usage:
    python scripts/reextract_zones.py --module dragon_heist --system dnd5e
    python scripts/reextract_zones.py --module dragon_heist --system dnd5e --dry-run
    python scripts/reextract_zones.py --module dragon_heist --system dnd5e --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_ROOT = PROJECT_ROOT / "faiss_index"
MODULES_ROOT = PROJECT_ROOT / "vault_maps" / "modules"

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"
EMBED_TIMEOUT = 30
COOLDOWN = 0.3  # seconds between embed calls

# Gemma context budget (improvement D: increased from 5x400)
CONTEXT_CHUNKS = 8
CONTEXT_CHARS_PER_CHUNK = 600


def embed_query(text: str) -> Optional[np.ndarray]:
    """Embed a query string via Ollama nomic-embed-text.

    Returns a flat 1-D float32 vector, or None on failure.
    """
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


# ---------------------------------------------------------------------------
# FAISS index loading (improvement A)
# ---------------------------------------------------------------------------

def load_faiss_index(system_id: str, source_tag: str):
    """Load FAISS index + source-filtered docstore for a system.

    Returns (faiss_index, source_chunks, all_chunks, page_index) where:
    - source_chunks: {faiss_idx: text} for chunks matching source_tag
    - all_chunks: {faiss_idx: text} for all chunks
    - page_index: {page_num: [faiss_idx, ...]} for source chunks (page proximity)
    """
    import faiss

    index_dir = INDEX_ROOT / system_id
    faiss_path = index_dir / "index.faiss"
    docstore_path = index_dir / "docstore.json"

    if not faiss_path.exists():
        print(f"[ERROR] No FAISS index at {faiss_path}")
        return None, {}, {}, {}

    index = faiss.read_index(str(faiss_path))

    docstore = {}
    id_map = {}
    if docstore_path.exists():
        data = json.loads(docstore_path.read_text())
        docstore = data.get("docstore", {})
        id_map = {int(k): v for k, v in data.get("id_map", {}).items()}

    # Build source-filtered lookup: FAISS idx → (text, page_num)
    # Also build page index for page-proximity retrieval
    source_chunks = {}  # faiss_idx → (text, page_num)
    page_index = {}     # page_num → [faiss_idx, ...]
    tag_prefix = f"[{source_tag}]"
    for faiss_idx, doc_key in id_map.items():
        entry = docstore.get(doc_key, "")
        if isinstance(entry, dict):
            text = entry.get("text", "")
            meta = entry.get("meta", {})
        else:
            text = str(entry)
            meta = {}
        if text.startswith(tag_prefix):
            clean = text[len(tag_prefix):].strip()
            if "........" not in clean and len(clean) >= 80:
                page_start = meta.get("page_start", 0)
                source_chunks[faiss_idx] = (clean, page_start)
                # Index by page for proximity lookups
                if page_start:
                    page_index.setdefault(page_start, []).append(faiss_idx)

    # Also build full lookup (all sources) for broader search
    all_chunks = {}
    for faiss_idx, doc_key in id_map.items():
        entry = docstore.get(doc_key, "")
        text = entry.get("text", "") if isinstance(entry, dict) else str(entry)
        if len(text) >= 80:
            all_chunks[faiss_idx] = text

    return index, source_chunks, all_chunks, page_index


def search_faiss(
    index, source_chunks: dict, all_chunks: dict,
    page_index: dict,
    query: str, top_k: int = CONTEXT_CHUNKS,
) -> list[tuple[str, int]]:
    """Search FAISS index with embedding + page proximity expansion.

    1. Embed the query and search FAISS for nearest neighbours
    2. Prefer source-tagged chunks
    3. For top hits, pull page-adjacent chunks (N-1, N+1) from same source
    4. Return up to top_k chunks, deduped

    The page proximity step ensures that when FAISS finds page 42 of a
    module, we also include pages 41 and 43 which likely contain the
    rest of that room's description.
    """
    query_vec = embed_query(query)
    if query_vec is None:
        return []
    time.sleep(COOLDOWN)

    query_vec_2d = query_vec.reshape(1, -1)
    # Search broadly so we can filter to source
    D, I = index.search(query_vec_2d, top_k * 4)

    # Collect source-matched FAISS hits
    source_hits = []  # (faiss_idx, rank)
    for rank, idx in enumerate(I[0]):
        if idx == -1:
            continue
        idx_int = int(idx)
        if idx_int in source_chunks:
            source_hits.append((idx_int, rank))

    # Identify pages of top hits for proximity expansion
    hit_pages = set()
    for faiss_idx, _rank in source_hits[:3]:  # top 3 hits
        _text, page = source_chunks[faiss_idx]
        if page:
            hit_pages.add(page)

    # Expand to adjacent pages
    adjacent_pages = set()
    for p in hit_pages:
        adjacent_pages.update([p - 1, p, p + 1])

    # Gather results: direct hits first, then page-adjacent, then fallback
    results = []  # list of (text, page_num)
    seen = set()

    # Pass 1: Direct FAISS source hits (ranked by embedding similarity)
    for faiss_idx, _rank in source_hits:
        if faiss_idx not in seen:
            results.append(source_chunks[faiss_idx])
            seen.add(faiss_idx)
            if len(results) >= top_k:
                break

    # Pass 2: Page-adjacent source chunks (not already in results)
    if len(results) < top_k and adjacent_pages:
        for page_num in sorted(adjacent_pages):
            for faiss_idx in page_index.get(page_num, []):
                if faiss_idx not in seen and faiss_idx in source_chunks:
                    results.append(source_chunks[faiss_idx])
                    seen.add(faiss_idx)
                    if len(results) >= top_k:
                        break
            if len(results) >= top_k:
                break

    # Pass 3: Fill remaining from any chunks in FAISS results (no page info)
    if len(results) < top_k:
        for idx in I[0]:
            if idx == -1:
                continue
            idx_int = int(idx)
            if idx_int not in seen and idx_int in all_chunks:
                results.append((all_chunks[idx_int], 0))
                seen.add(idx_int)
                if len(results) >= top_k:
                    break

    return results


def search_chunks_keyword(
    chunks: list[str], keywords: list[str], top_k: int = 10
) -> list[str]:
    """Fast keyword-based search — no embedding calls needed.

    Kept as fallback if FAISS index isn't available.
    """
    scored = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(
            chunk_lower.count(kw.lower()) for kw in keywords if len(kw) > 2
        )
        if score > 0:
            scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:top_k]]


# ---------------------------------------------------------------------------
# Search query builder (improvement C: NPC names + draft description)
# ---------------------------------------------------------------------------

def build_search_query(
    zone_name: str, room_type: str, draft_desc: str,
    npc_names: list[str],
) -> str:
    """Build a rich search query combining zone, description, and NPC names.

    The query is what gets embedded and sent to FAISS. Richer queries
    produce better semantic matches than bare zone names.
    """
    parts = [zone_name]
    if room_type and room_type not in ("normal", "start"):
        parts.append(room_type)
    # Use first ~150 chars of draft description as search context
    if draft_desc:
        parts.append(draft_desc[:150])
    # Add NPC names for targeted retrieval (improvement C)
    for name in npc_names[:3]:
        parts.append(name)
    return " ".join(parts)


def extract_npc_names(content_hints: dict) -> list[str]:
    """Pull existing NPC names from content_hints for search enrichment."""
    names = []
    for npc in content_hints.get("npcs", []):
        name = npc.get("name", "")
        if name and len(name) > 2:
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# Gemma Polish
# ---------------------------------------------------------------------------

def gemma_polish(
    ocr_chunks: list[tuple[str, int]],
    draft_description: str,
    draft_read_aloud: str,
    location_name: str,
    source_tag: str,
) -> dict:
    """Use Gemma 4 E2B to restore canonical content from source chunks + draft.

    ocr_chunks: list of (chunk_text, page_number) tuples.
    Returns dict with polished description, read_aloud, and npcs.
    """
    sys.path.insert(0, str(PROJECT_ROOT))

    from codex.core.services.litert_engine import get_litert_engine
    engine = get_litert_engine()

    # Filter heavily garbled chunks (alpha ratio < 0.6 = OCR noise)
    clean_chunks = []
    for text, page in ocr_chunks:
        alpha_ratio = len(re.findall(r'[a-zA-Z]', text)) / max(1, len(text))
        if alpha_ratio > 0.6:
            clean_chunks.append((text, page))
    if not clean_chunks:
        clean_chunks = ocr_chunks[:3]  # fallback to best available

    # Combine source chunks with page citations
    # (improvement D: 8 x 600 instead of 5 x 400)
    context_parts = []
    for text, page in clean_chunks[:CONTEXT_CHUNKS]:
        page_label = f"[p.{page}] " if page else ""
        context_parts.append(f"{page_label}{text[:CONTEXT_CHARS_PER_CHUNK]}")
    source_context = "\n---\n".join(context_parts)

    # --- Polish description ---
    desc_prompt = (
        f"SOURCE TEXT (from {source_tag} PDF, may contain OCR errors):\n"
        f"{source_context}\n\n"
        f"DRAFT DESCRIPTION (atmospheric but may not be canon):\n"
        f"{draft_description}\n\n"
        f"TASK: Write a 2-3 sentence GM description for '{location_name}'. "
        f"Use ONLY facts from the SOURCE TEXT. Fix any OCR garble. "
        f"Keep the atmospheric tone of the DRAFT where it aligns with source. "
        f"If the source contradicts the draft, the source wins. "
        f"Output ONLY the description, nothing else."
    )
    desc_system = (
        "You are a D&D librarian restoring canonical text from OCR scans. "
        "Be faithful to the source. Never invent details not in the source."
    )

    desc, _ = engine.generate_sync(prompt=desc_prompt, system=desc_system, max_tokens=200)

    # --- Polish read_aloud ---
    ra_prompt = (
        f"SOURCE TEXT (from {source_tag} PDF):\n"
        f"{source_context}\n\n"
        f"DRAFT READ-ALOUD (atmospheric but may not be canon):\n"
        f"{draft_read_aloud}\n\n"
        f"TASK: Write 2-3 sentences of boxed read-aloud text for '{location_name}'. "
        f"This is text the DM reads to players when they enter the area. "
        f"Use sensory details from the SOURCE TEXT. Fix OCR garble. "
        f"Second-person perspective ('you see...'). "
        f"Output ONLY the read-aloud text."
    )

    read_aloud, _ = engine.generate_sync(prompt=ra_prompt, system=desc_system, max_tokens=200)

    # --- Extract NPCs ---
    npc_prompt = (
        f"SOURCE TEXT (from {source_tag} PDF):\n"
        f"{source_context}\n\n"
        f"TASK: List ONLY named NPCs who are physically present at or "
        f"directly associated with '{location_name}'. Do NOT include "
        f"NPCs merely mentioned in passing or from other locations.\n"
        f"For each, provide:\n"
        f"- name\n- role (1 sentence from source)\n"
        f"If no named NPCs are specifically at this location, respond with NONE.\n"
        f"Format: NAME | ROLE (one per line)"
    )

    npc_text, _ = engine.generate_sync(prompt=npc_prompt, system=desc_system, max_tokens=150)

    # Parse NPC output
    npcs = []
    if npc_text and "NONE" not in npc_text.upper():
        for line in npc_text.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 1)
                name = parts[0].strip().strip("-* ")
                role = parts[1].strip() if len(parts) > 1 else ""
                if name and len(name) > 2 and name[0].isupper():
                    npcs.append({
                        "name": name,
                        "role": role,
                        "dialogue": "",
                        "notes": f"[Source: {source_tag} PDF]",
                    })

    return {
        "description": desc.strip() if desc else draft_description,
        "read_aloud": read_aloud.strip() if read_aloud else draft_read_aloud,
        "npcs": npcs[:4],
    }


# ---------------------------------------------------------------------------
# Room extraction (refactored for FAISS)
# ---------------------------------------------------------------------------

def extract_room_content(
    index, source_chunks: dict, all_chunks: dict, page_index: dict,
    zone_name: str, room_type: str,
    draft_desc: str = "", draft_read_aloud: str = "",
    npc_names: list[str] = None,
    source_tag: str = "", use_gemma: bool = True,
) -> dict:
    """Extract source-grounded content for a room via FAISS search + Gemma.

    Uses the room's draft description + NPC names to build a rich
    embedding query for room-specific chunk retrieval.
    """
    npc_names = npc_names or []

    # Build rich search query (improvements A + C)
    query = build_search_query(zone_name, room_type, draft_desc, npc_names)
    matches = search_faiss(index, source_chunks, all_chunks, page_index, query)

    if not matches:
        return {
            "description": draft_desc or f"[NO SOURCE FOUND for {zone_name}]",
            "read_aloud": draft_read_aloud,
            "npcs": [],
            "_source_status": "no_source",
            "_source_chunks": 0,
        }

    if use_gemma:
        polished = gemma_polish(
            ocr_chunks=matches,
            draft_description=draft_desc,
            draft_read_aloud=draft_read_aloud,
            location_name=zone_name,
            source_tag=source_tag,
        )
        polished["_source_status"] = "polished"
        polished["_source_chunks"] = len(matches)
        return polished

    # Fallback: raw chunk extraction (no Gemma)
    return {
        "description": matches[0][0][:500],
        "read_aloud": matches[1][0][:500] if len(matches) > 1 else "",
        "npcs": [],
        "_source_status": "extracted_raw",
        "_source_chunks": len(matches),
    }


# ---------------------------------------------------------------------------
# Module-level extraction
# ---------------------------------------------------------------------------

def reextract_module(
    module_name: str, system_id: str, source_tag: str,
    dry_run: bool = False, force: bool = False,
) -> dict:
    """Re-extract all zone files in a module from source PDF chunks.

    Args:
        force: If True, re-process rooms that were already polished.
    """
    module_dir = MODULES_ROOT / module_name
    if not module_dir.is_dir():
        print(f"[ERROR] Module not found: {module_dir}")
        return {"error": "not found"}

    print(f"Loading FAISS index for {system_id} (source: [{source_tag}])...")
    index, source_chunks, all_chunks, page_index = load_faiss_index(
        system_id, source_tag
    )
    if index is None:
        return {"error": "no index"}

    print(f"  {len(source_chunks)} source-tagged chunks, "
          f"{len(all_chunks)} total in index, "
          f"{len(page_index)} pages indexed")

    summary = {
        "module": module_name,
        "source_tag": source_tag,
        "files_processed": 0,
        "rooms_total": 0,
        "rooms_extracted": 0,
        "rooms_no_source": 0,
        "rooms_skipped": 0,
    }

    for json_file in sorted(module_dir.glob("*.json")):
        if json_file.name == "module_manifest.json":
            continue

        data = json.loads(json_file.read_text())
        rooms = data.get("rooms", {})
        if not rooms:
            continue

        print(f"\n--- {json_file.name} ({len(rooms)} rooms) ---")
        summary["files_processed"] += 1

        zone_name = json_file.stem.replace("_", " ").title()
        modified = False

        for room_id, room in rooms.items():
            summary["rooms_total"] += 1
            ch = room.get("content_hints", {})

            # Skip already-polished rooms unless --force
            if not force and ch.get("_extraction_date") and ch.get("_method") == "polished":
                summary["rooms_skipped"] += 1
                print(f"  Room {room_id}: SKIPPED (already polished)")
                continue

            draft_desc = ch.get("description", "")
            draft_ra = ch.get("read_aloud", "")
            room_type = room.get("room_type", "")
            npc_names = extract_npc_names(ch)

            # Extract from source with FAISS + page proximity + Gemma Polish
            content = extract_room_content(
                index, source_chunks, all_chunks, page_index,
                zone_name, room_type,
                draft_desc=draft_desc,
                draft_read_aloud=draft_ra,
                npc_names=npc_names,
                source_tag=source_tag,
            )

            status = content["_source_status"]
            n_chunks = content["_source_chunks"]

            if status in ("polished", "extracted_raw"):
                summary["rooms_extracted"] += 1
                tag = "POLISHED" if status == "polished" else "RAW"
                print(f"  Room {room_id}: {tag} ({n_chunks} chunks)")

                if not dry_run:
                    ch["description"] = content["description"]
                    ch["_source"] = source_tag
                    ch["_extraction_date"] = "2026-04-08"
                    ch["_method"] = status
                    if content["read_aloud"]:
                        ch["read_aloud"] = content["read_aloud"]
                    if content["npcs"]:
                        ch["npcs"] = content["npcs"]
                    modified = True
            else:
                summary["rooms_no_source"] += 1
                print(f"  Room {room_id}: NO SOURCE (kept draft)")

        if modified and not dry_run:
            json_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"  -> Updated {json_file.name}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Re-extract zone files from FAISS-indexed source PDFs"
    )
    parser.add_argument("--module", required=True, help="Module directory name")
    parser.add_argument("--system", default="dnd5e", help="System ID for FAISS index")
    parser.add_argument("--source-tag", default=None,
                        help="Source tag in docstore (default: derived from module name)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without modifying files")
    parser.add_argument("--force", action="store_true",
                        help="Re-extract rooms that were already polished")

    args = parser.parse_args()

    # Derive source tag from module name
    source_tag = args.source_tag
    if not source_tag:
        tag_map = {
            "dragon_heist": "Waterdeep_ Dragon Heist",
            "mad_mage": "Dungeon of the Mad Mage",
            "out_of_abyss": "Out of the Abyss",
            "rime_frostmaiden": "Rime of the Frostmaiden",
            "tyranny_dragons": "Tyranny of Dragons",
        }
        source_tag = tag_map.get(args.module, args.module.replace("_", " ").title())

    print(f"Re-extracting {args.module} from [{source_tag}] ({args.system})")
    if args.dry_run:
        print("[DRY RUN — no files will be modified]")
    if args.force:
        print("[FORCE — re-extracting already-polished rooms]")

    summary = reextract_module(
        args.module, args.system, source_tag,
        dry_run=args.dry_run, force=args.force,
    )

    print(f"\n{'='*50}")
    print(f"SUMMARY: {summary.get('module', '?')}")
    print(f"  Files processed:  {summary.get('files_processed', 0)}")
    print(f"  Rooms total:      {summary.get('rooms_total', 0)}")
    print(f"  Rooms extracted:  {summary.get('rooms_extracted', 0)}")
    print(f"  Rooms skipped:    {summary.get('rooms_skipped', 0)}")
    print(f"  Rooms no source:  {summary.get('rooms_no_source', 0)}")


if __name__ == "__main__":
    main()

"""
codex_index_builder.py - Knowledge Forge (LangChain-Free)
=========================================================
Uses native faiss-cpu, numpy, and direct Ollama embedding API.
Outputs index.faiss + docstore.json per vault (no more .pkl).

Version: 9.0 (WO V27.0 — LangChain excision)
"""

import os
import re
import glob
import sys
import time
import json
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

# Ensure project root is on sys.path (needed when run as subprocess)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import numpy as np
import faiss
import requests
from pypdf import PdfReader

# --- CONFIGURATION ---
BASE_DIR = _PROJECT_ROOT  # Project root
VAULT_DIR = os.path.join(BASE_DIR, "vault")
DB_DIR = os.path.join(BASE_DIR, "faiss_index")
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MANIFEST_FILE = os.path.join(VAULT_DIR, "vault_manifest.json")

# Subfolder -> RAG priority mapping
SUBFOLDER_PRIORITY = {
    "SOURCE": 1,
    "SUPPLEMENTS": 2,
    "MODULES": 3,
    "MODULE": 3,
    "AUDIO": 99,
}
DEFAULT_PRIORITY = 2

# Directories that contain non-indexable content (audio, images, etc.)
# Files inside these dirs are excluded from vault scanning and indexing.
SKIP_DIRS = {"AUDIO", "audio", "IMAGES", "images", "MAPS", "maps"}


def _is_in_skip_dir(filepath: str) -> bool:
    """Return True if filepath is inside a non-indexable directory."""
    parts = Path(filepath).parts
    return bool(SKIP_DIRS.intersection(parts))

# Family parent directories
FAMILY_PARENTS = {"FITD", "ILLUMINATED_WORLDS"}

# Setup logging
from maintenance.codex_utils import setup_logging
_logger = setup_logging("INDEX_BUILDER")


# =========================================================================
# DOCUMENT DATACLASS (replaces LangChain Document)
# =========================================================================

@dataclass
class DocChunk:
    """A text chunk with metadata."""
    page_content: str
    metadata: Dict = field(default_factory=dict)


# =========================================================================
# VAULT MANIFEST — SHA-256 Delta Sync
# =========================================================================

def _compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file for change detection."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


class VaultManifest:
    """Tracks SHA-256 hashes of indexed PDFs for incremental sync."""

    def __init__(self, path: str = MANIFEST_FILE):
        self._path = path
        self._hashes: Dict[str, str] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                self._hashes = data.get("file_hashes", {})
            except Exception:
                self._hashes = {}

    def save(self):
        data = {
            "version": "2.0",
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "file_count": len(self._hashes),
            "file_hashes": self._hashes,
        }
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)

    def is_changed(self, rel_path: str, current_hash: str) -> bool:
        return self._hashes.get(rel_path) != current_hash

    def update(self, rel_path: str, file_hash: str):
        self._hashes[rel_path] = file_hash

    def remove(self, rel_path: str):
        self._hashes.pop(rel_path, None)

    @property
    def tracked_count(self) -> int:
        return len(self._hashes)

    @property
    def all_tracked(self) -> Dict[str, str]:
        """Return a copy of all tracked file hashes."""
        return dict(self._hashes)


def check_vault_changes() -> dict:
    """Lightweight scan: compare vault PDFs/TXTs against manifest.

    Returns {"new": [...], "changed": [...], "total_vault": N, "total_tracked": N}
    No side effects — does not modify manifest or build indices.
    """
    result = {"new": [], "changed": [], "total_vault": 0, "total_tracked": 0}

    manifest = VaultManifest(path=MANIFEST_FILE)
    result["total_tracked"] = manifest.tracked_count

    vaults = get_vaults()
    if not vaults:
        return result

    for vault_info in vaults:
        vault_path = vault_info["path"]
        pdf_files = glob.glob(os.path.join(vault_path, "**", "*.pdf"), recursive=True)
        txt_files = glob.glob(os.path.join(vault_path, "**", "*.txt"), recursive=True)

        for doc_file in pdf_files + txt_files:
            if _is_in_skip_dir(doc_file):
                continue
            result["total_vault"] += 1
            manifest_key = os.path.relpath(doc_file, VAULT_DIR)

            try:
                current_hash = _compute_file_hash(doc_file)
            except OSError:
                continue

            stored = manifest.all_tracked.get(manifest_key)
            if stored is None:
                # File not in manifest at all — new
                result["new"].append(manifest_key)
            elif manifest.is_changed(manifest_key, current_hash):
                # File in manifest but hash differs — changed
                result["changed"].append(manifest_key)

    return result


# Colors for Terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    print(Colors.HEADER + "+" + "=" * 46 + "+" + Colors.ENDC)
    print(Colors.HEADER + "|    C.O.D.E.X. KNOWLEDGE FORGE V9.0          |" + Colors.ENDC)
    print(Colors.HEADER + "|    Native FAISS — Resume-Safe Delta Sync     |" + Colors.ENDC)
    print(Colors.HEADER + "+" + "=" * 46 + "+" + Colors.ENDC)


# =========================================================================
# TEXT SPLITTER (replaces LangChain RecursiveCharacterTextSplitter)
# =========================================================================

def _split_text(text: str, chunk_size: int = CHUNK_SIZE,
                chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks using recursive separators."""
    separators = ["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    chunks = []

    def _split_recursive(text: str, seps: list) -> List[str]:
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        sep = seps[0] if seps else ""
        remaining_seps = seps[1:] if len(seps) > 1 else [""]

        if sep:
            parts = text.split(sep)
        else:
            # Character-level split
            result = []
            for i in range(0, len(text), chunk_size - chunk_overlap):
                result.append(text[i:i + chunk_size])
            return result

        current = ""
        result = []
        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    result.append(current)
                if len(part) > chunk_size:
                    result.extend(_split_recursive(part, remaining_seps))
                    current = ""
                else:
                    current = part

        if current:
            result.append(current)

        return result

    raw_chunks = _split_recursive(text, separators)

    # Apply overlap
    for i, chunk in enumerate(raw_chunks):
        if i > 0 and chunk_overlap > 0 and len(raw_chunks[i-1]) > chunk_overlap:
            overlap_text = raw_chunks[i-1][-chunk_overlap:]
            chunk = overlap_text + chunk
        if chunk.strip():
            chunks.append(chunk.strip())

    return chunks


# =========================================================================
# EMBEDDING
# =========================================================================

def _embed_texts(texts: List[str]) -> Optional[np.ndarray]:
    """Get embedding vectors from Ollama for a batch of texts."""
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBEDDING_MODEL, "input": texts},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings")
        if embeddings:
            return np.array(embeddings, dtype="float32")
    except Exception as e:
        _logger.error(f"Embedding error: {e}")
    return None


# =========================================================================
# RECURSIVE VAULT DISCOVERY
# =========================================================================

def get_vaults() -> List[Dict]:
    """Recursively scan VAULT_DIR for leaf vaults."""
    if not os.path.exists(VAULT_DIR):
        os.makedirs(VAULT_DIR)
        print(f"{Colors.WARNING}Created missing vault directory: {VAULT_DIR}{Colors.ENDC}")

    vaults: List[Dict] = []

    for entry in sorted(os.listdir(VAULT_DIR)):
        full_path = os.path.join(VAULT_DIR, entry)
        if not os.path.isdir(full_path):
            continue

        if entry in FAMILY_PARENTS:
            for child in sorted(os.listdir(full_path)):
                child_path = os.path.join(full_path, child)
                if os.path.isdir(child_path):
                    vaults.append({
                        "name": child,
                        "path": child_path,
                        "system_id": child.lower().replace(" ", "_"),
                        "system_family": entry,
                    })
        else:
            vaults.append({
                "name": entry,
                "path": full_path,
                "system_id": entry.lower().replace(" ", "_"),
                "system_family": entry.lower().replace(" ", "_"),
            })

    return vaults


def _infer_priority(rel_path: str) -> int:
    """Derive RAG priority from a file's relative path within its vault."""
    parts = Path(rel_path).parts
    if len(parts) > 1:
        subfolder = parts[0].upper()
        return SUBFOLDER_PRIORITY.get(subfolder, DEFAULT_PRIORITY)
    return DEFAULT_PRIORITY


# =========================================================================
# CHAPTER-LEVEL METADATA DETECTION
# =========================================================================

_CHAPTER_PATTERNS = [
    re.compile(r'^(?:Chapter|CHAPTER)\s+(\d+)', re.MULTILINE),
    re.compile(r'^(?:Level|LEVEL)\s+(\d+)', re.MULTILINE),
    re.compile(r'^(?:Part|PART)\s+(\w+)', re.MULTILINE),
    re.compile(r'^(?:Appendix|APPENDIX)\s+(\w+)', re.MULTILINE),
]

_SUBDOC_PATTERNS = {
    "gazetteer": re.compile(
        r"(?:Volo['\u2019]?s?\s+Guide\s+to\s+Waterdeep|Gazetteer)", re.IGNORECASE
    ),
    "code_legal": re.compile(r"Code\s+Legal", re.IGNORECASE),
}

_WATERDEEP_WARDS = [
    "Castle Ward", "Dock Ward", "Field Ward", "North Ward",
    "Sea Ward", "Southern Ward", "Trades Ward", "City of the Dead",
]


def _detect_chapter(text_block: str) -> Optional[str]:
    for pattern in _CHAPTER_PATTERNS:
        m = pattern.search(text_block[:500])
        if m:
            return m.group(0).strip()
    return None


def _detect_subdoc_tags(text_block: str) -> Dict[str, str]:
    tags: Dict[str, str] = {}
    for label, pattern in _SUBDOC_PATTERNS.items():
        if pattern.search(text_block):
            tags["sub_document"] = label
            if label == "gazetteer":
                tags["location_context"] = "Waterdeep"
            break

    for ward in _WATERDEEP_WARDS:
        if ward.lower() in text_block.lower():
            tags["sub_location"] = ward
            break

    return tags


# =========================================================================
# PDF LOADING
# =========================================================================

def load_documents(vault_info: Dict, manifest: Optional[VaultManifest] = None) -> List[DocChunk]:
    """Load PDFs and text files recursively from a vault, enriching metadata.

    WO-V33.0: Renamed from load_pdfs, adds .txt support for BurnwillowSRD etc.
    """
    vault_path = vault_info["path"]
    system_id = vault_info["system_id"]
    system_family = vault_info["system_family"]

    # Discover both PDFs and text files, excluding non-indexable dirs
    pdf_files = glob.glob(os.path.join(vault_path, "**", "*.pdf"), recursive=True)
    txt_files = glob.glob(os.path.join(vault_path, "**", "*.txt"), recursive=True)
    all_files = [f for f in pdf_files + txt_files if not _is_in_skip_dir(f)]

    documents: List[DocChunk] = []

    if not all_files:
        print(f"    {Colors.WARNING}No documents found in {vault_path} or its subfolders.{Colors.ENDC}")
        return []

    print(f"    Found {len(all_files)} source files ({len(pdf_files)} PDF, {len(txt_files)} TXT).")

    skipped = 0
    for doc_file in all_files:
        try:
            rel_path = os.path.relpath(doc_file, vault_path)
            manifest_key = os.path.relpath(doc_file, VAULT_DIR)

            if manifest:
                current_hash = _compute_file_hash(doc_file)
                if not manifest.is_changed(manifest_key, current_hash):
                    print(f"    = Unchanged: {rel_path} {Colors.GREEN}(skipped){Colors.ENDC}")
                    skipped += 1
                    continue

            print(f"    + Parsing: {rel_path}...", end=" ", flush=True)

            priority = _infer_priority(rel_path)

            if priority == 99:
                print(f"{Colors.WARNING}SKIP (audio){Colors.ENDC}")
                continue

            text_content = ""
            is_txt = doc_file.lower().endswith(".txt")

            if is_txt:
                # Plain text file — read directly
                with open(doc_file, "r", errors="replace") as f:
                    text_content = f.read()
                page_count = len(text_content) // 3000 or 1  # Approximate
            else:
                # PDF file — extract via pypdf
                reader = PdfReader(doc_file)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_content += text + "\n"
                page_count = len(reader.pages)

            metadata = {
                "source": os.path.basename(doc_file),
                "vault": vault_info["name"],
                "path": rel_path,
                "system_id": system_id,
                "system_family": system_family,
                "priority": priority,
            }

            chapter = _detect_chapter(text_content)
            if chapter:
                metadata["chapter"] = chapter

            subdoc_tags = _detect_subdoc_tags(text_content)
            metadata.update(subdoc_tags)

            documents.append(DocChunk(page_content=text_content, metadata=metadata))
            fmt = "TXT" if is_txt else "PDF"
            print(f"{Colors.GREEN}OK ({page_count} {'chars' if is_txt else 'pages'}, P{priority}, {fmt}){Colors.ENDC}")

            if manifest:
                manifest.update(manifest_key, current_hash)
                manifest.save()

        except Exception as e:
            print(f"{Colors.FAIL}ERROR{Colors.ENDC}")
            _logger.error(f"Error parsing {doc_file}: {e}")

    if skipped:
        print(f"    {Colors.GREEN}Delta sync: {skipped} unchanged file(s) skipped.{Colors.ENDC}")

    return documents


# Backward-compatible alias
load_pdfs = load_documents


def _enhance_chunk_metadata(chunks: List[DocChunk]) -> List[DocChunk]:
    """Post-process chunks to propagate chapter/level tags."""
    for chunk in chunks:
        if "chapter" not in chunk.metadata:
            detected = _detect_chapter(chunk.page_content)
            if detected:
                chunk.metadata["chapter"] = detected

        subdoc_tags = _detect_subdoc_tags(chunk.page_content)
        for key, val in subdoc_tags.items():
            if key not in chunk.metadata:
                chunk.metadata[key] = val

    return chunks


# =========================================================================
# INDEX BUILDING (native FAISS + Ollama embed)
# =========================================================================

def build_index(vault_name: str, documents: List[DocChunk]):
    """Chunk text, embed, and build/save the FAISS index with docstore.json."""
    if not documents:
        return

    # Split documents into chunks
    print(f"    > Sharding {len(documents)} source docs...", end=" ", flush=True)
    all_chunks: List[DocChunk] = []
    for doc in documents:
        texts = _split_text(doc.page_content)
        for text in texts:
            all_chunks.append(DocChunk(page_content=text, metadata=dict(doc.metadata)))
    print(f"Created {len(all_chunks)} shards.")

    # Enhance metadata
    all_chunks = _enhance_chunk_metadata(all_chunks)

    print(f"    > Vectorizing (native FAISS + {EMBEDDING_MODEL})...")

    save_path = os.path.join(DB_DIR, vault_name.lower())
    faiss_file = os.path.join(save_path, "index.faiss")

    # Load existing index for delta merge
    existing_index = None
    existing_docstore = {}
    existing_id_map = {}
    next_id = 0

    if os.path.exists(faiss_file):
        try:
            existing_index = faiss.read_index(faiss_file)
            json_file = os.path.join(save_path, "docstore.json")
            if os.path.exists(json_file):
                data = json.loads(Path(json_file).read_text())
                existing_docstore = data.get("docstore", {})
                existing_id_map = {int(k): v for k, v in data.get("id_map", {}).items()}
                next_id = max(existing_id_map.keys(), default=-1) + 1
            print(f"    > Loaded existing index for delta merge "
                  f"({existing_index.ntotal} vectors).")
        except Exception as e:
            print(f"    {Colors.WARNING}Could not load existing index, "
                  f"rebuilding: {e}{Colors.ENDC}")
            existing_index = None

    # Batch embed and build
    batch_size = 50
    total_chunks = len(all_chunks)
    total_batches = (total_chunks + batch_size - 1) // batch_size
    failed_batches = 0

    new_vectors = []
    new_docstore = dict(existing_docstore)
    new_id_map = dict(existing_id_map)
    current_id = next_id

    for batch_num, i in enumerate(range(0, total_chunks, batch_size), 1):
        batch = all_chunks[i:i + batch_size]
        texts = [c.page_content for c in batch]

        heartbeat_msg = (
            f"[HEARTBEAT] Still Vectorizing... "
            f"Batch {batch_num}/{total_batches} "
            f"({i}/{total_chunks} shards)"
        )
        print(f"    {heartbeat_msg}", flush=True)
        _logger.info(heartbeat_msg)

        try:
            embeddings = _embed_texts(texts)
            if embeddings is None:
                raise RuntimeError("Embedding returned None")

            for j, chunk in enumerate(batch):
                doc_id = f"doc_{current_id}"
                new_docstore[doc_id] = chunk.page_content
                new_id_map[current_id] = doc_id
                current_id += 1

            new_vectors.append(embeddings)

        except Exception as e:
            failed_batches += 1
            err_msg = f"Batch {batch_num}/{total_batches} failed: {e}"
            print(f"    {Colors.FAIL}{err_msg}{Colors.ENDC}")
            _logger.error(err_msg)
            if failed_batches >= 3:
                print(f"\n{Colors.FAIL}Too many batch failures ({failed_batches}). "
                      f"Aborting vectorization.{Colors.ENDC}")
                print(f"{Colors.WARNING}Ensure 'ollama serve' is running and "
                      f"you have pulled '{EMBEDDING_MODEL}'{Colors.ENDC}")
                return

    if failed_batches:
        print(f"    {Colors.WARNING}{failed_batches} batch(es) failed during "
              f"vectorization.{Colors.ENDC}")

    if not new_vectors:
        print(f"    {Colors.WARNING}No vectors produced.{Colors.ENDC}")
        return

    # Build final FAISS index
    all_vectors = np.vstack(new_vectors)

    if existing_index is not None:
        existing_index.add(all_vectors)
        final_index = existing_index
        print(f"    > Merged {all_vectors.shape[0]} new vectors into existing index "
              f"(total: {final_index.ntotal}).")
    else:
        dim = all_vectors.shape[1]
        final_index = faiss.IndexFlatL2(dim)
        final_index.add(all_vectors)

    # Save
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    try:
        faiss.write_index(final_index, faiss_file)

        # Write docstore.json (replaces .pkl)
        docstore_data = {
            "version": "2.0",
            "docstore": new_docstore,
            "id_map": {str(k): v for k, v in new_id_map.items()},
        }
        docstore_path = os.path.join(save_path, "docstore.json")
        with open(docstore_path, "w") as f:
            json.dump(docstore_data, f)

        print(f"    {Colors.GREEN}Indexing Complete.{Colors.ENDC}")
        print(f"    Saved index & docstore to: {save_path} "
              f"({final_index.ntotal} vectors)")
    except Exception as e:
        print(f"    {Colors.FAIL}Failed to save index: {e}{Colors.ENDC}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    os.system('clear')
    print_banner()

    vault_list = get_vaults()

    if not vault_list:
        print(f"{Colors.FAIL}No vaults found in {VAULT_DIR}. Please create directories there.{Colors.ENDC}")
        return

    manifest = VaultManifest()
    print(f"Delta sync manifest: {manifest.tracked_count} file(s) tracked.\n")

    print("Found Vaults:")
    for i, v in enumerate(vault_list):
        family_tag = f" [{v['system_family']}]" if v["system_family"] != v["system_id"] else ""
        print(f" [{i+1}] {v['name'].upper()}{family_tag}")
    print(f" [A] Build All")
    print(f" [F] Full Rebuild (ignore manifest)")

    choice = input(f"\n{Colors.BLUE}Select System > {Colors.ENDC}").strip().upper()

    full_rebuild = False
    selected: List[Dict] = []

    if choice == 'F':
        selected = vault_list
        full_rebuild = True
        print(f"{Colors.WARNING}Full rebuild mode — ignoring manifest.{Colors.ENDC}")
    elif choice == 'A':
        selected = vault_list
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(vault_list):
            selected = [vault_list[idx]]
        else:
            print(f"{Colors.FAIL}Invalid selection.{Colors.ENDC}")
            return
    else:
        print(f"{Colors.FAIL}Invalid selection.{Colors.ENDC}")
        return

    active_manifest = None if full_rebuild else manifest

    try:
        for vault_info in selected:
            print(f"\n{Colors.BLUE}>>> BUILDING INDEX FOR: {vault_info['name'].upper()} "
                  f"(family={vault_info['system_family']}){Colors.ENDC}")
            docs = load_documents(vault_info, manifest=active_manifest)
            build_index(vault_info["name"], docs)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrupted by user.{Colors.ENDC}")
    finally:
        manifest.save()
        print(f"\n{Colors.GREEN}Manifest saved "
              f"({manifest.tracked_count} files tracked).{Colors.ENDC}")

    # WO-V33.0: Broadcast RAG invalidation (best-effort)
    try:
        from codex.core.services.broadcast import GlobalBroadcastManager
        bus = GlobalBroadcastManager()
        bus.broadcast("RAG_INDEX_INVALIDATED", {"source": "index_builder"})
        print(f"{Colors.GREEN}RAG invalidation broadcast sent.{Colors.ENDC}")
    except Exception:
        pass


if __name__ == "__main__":
    main()

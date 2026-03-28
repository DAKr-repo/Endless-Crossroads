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
from typing import List, Dict, Optional, Tuple

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

# WO-V156: Noise patterns to strip from extracted PDF text
_NOISE_PATTERNS = [
    re.compile(r'Property of \w+\..*?Order #\d+'),           # DRM watermark
    re.compile(r'^\d{1,3}\s*$', re.MULTILINE),               # Standalone page numbers
    re.compile(r'©\s*\d{4}.*?(?:Wizards|Hasbro|Elderbrain).*?$',
               re.MULTILINE | re.IGNORECASE),                  # Copyright lines
]


def _clean_text(text: str) -> str:
    """Strip common noise from PDF-extracted text (DRM, page numbers, copyright)."""
    for pattern in _NOISE_PATTERNS:
        text = pattern.sub('', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


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
class PageSpan:
    """Tracks which PDF pages a chunk spans."""
    start_page: int = 0
    end_page: int = 0


@dataclass
class AnnotatedChunk:
    """A text chunk with page provenance."""
    text: str
    page_span: PageSpan = field(default_factory=PageSpan)


@dataclass
class DocChunk:
    """A text chunk with metadata."""
    page_content: str
    metadata: Dict = field(default_factory=dict)
    page_texts: List[Tuple[int, str]] = field(default_factory=list)


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


# =========================================================================
# INDEX HEALTH AUDIT — detect gaps, missing tags, incomplete coverage
# =========================================================================

def audit_index_health(manifest: 'VaultManifest') -> Dict[str, List[str]]:
    """Scan all indices for gaps and return files that need re-indexing.

    Checks:
    1. Files in manifest but with zero tagged shards in docstore
       (indexed by old builder without source tagging)
    2. Vault files not in manifest at all (never indexed)
    3. Files whose hash changed since last index

    Returns dict mapping system_id -> list of vault-relative file paths
    that need re-indexing. Also removes stale manifest entries so delta
    sync will pick them up.
    """
    needs_reindex: Dict[str, List[str]] = {}
    vaults = get_vaults()

    for vault_info in vaults:
        vault_path = vault_info["path"]
        vault_name = vault_info["name"].lower()
        system_id = vault_info["system_id"]

        # Find all indexable files in this vault
        pdf_files = glob.glob(os.path.join(vault_path, "**", "*.pdf"), recursive=True)
        txt_files = glob.glob(os.path.join(vault_path, "**", "*.txt"), recursive=True)
        all_files = [f for f in pdf_files + txt_files if not _is_in_skip_dir(f)]

        if not all_files:
            continue

        # Load existing docstore to check for source tags and v3.0 metadata
        docstore_path = os.path.join(DB_DIR, vault_name, "docstore.json")
        tagged_sources = set()
        has_page_data = False
        if os.path.exists(docstore_path):
            try:
                data = json.loads(Path(docstore_path).read_text())
                ds_version = data.get("version", "2.0")
                docstore = data.get("docstore", {})
                for entry in docstore.values():
                    # v3.0: entry is {"text": ..., "meta": {...}}
                    if isinstance(entry, dict):
                        text = entry.get("text", "")
                        meta = entry.get("meta", {})
                        if meta.get("source"):
                            tagged_sources.add(meta["source"])
                        if meta.get("page_start", 0) > 0:
                            has_page_data = True
                    else:
                        # v2.0: entry is a plain string with [Source] prefix
                        text = entry
                        if text.startswith("[") and "]" in text[:80]:
                            source = text[1:text.index("]")]
                            tagged_sources.add(source)
            except Exception:
                pass

        files_to_reindex = []
        for doc_file in all_files:
            manifest_key = os.path.relpath(doc_file, VAULT_DIR)
            filename_stem = Path(doc_file).stem  # e.g. "Dragon Heist"

            # Check 1: file hash changed
            try:
                current_hash = _compute_file_hash(doc_file)
            except OSError:
                continue

            if manifest.is_changed(manifest_key, current_hash):
                files_to_reindex.append(manifest_key)
                continue

            # Check 2: file is in manifest but has no tagged shards
            stored = manifest.all_tracked.get(manifest_key)
            if stored is not None and filename_stem not in tagged_sources:
                files_to_reindex.append(manifest_key)
                continue

        if files_to_reindex:
            needs_reindex[system_id] = files_to_reindex

            # Remove stale manifest entries so delta sync picks them up
            for f in files_to_reindex:
                manifest.remove(f)

            print(f"  {Colors.WARNING}[AUDIT] {vault_info['name']}: "
                  f"{len(files_to_reindex)} file(s) need re-indexing:{Colors.ENDC}")
            for f in files_to_reindex:
                reason = "no source tags" if manifest.all_tracked.get(f) else "new/changed"
                print(f"    - {Path(f).name} ({reason})")

    if not needs_reindex:
        print(f"  {Colors.GREEN}[AUDIT] All indices healthy — "
              f"no gaps detected.{Colors.ENDC}")

    return needs_reindex


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


# Page boundary marker (null byte — never appears in PDF text)
_PAGE_MARKER = "\x00PAGE:{}\x00"
_PAGE_MARKER_RE = re.compile(r'\x00PAGE:(\d+)\x00')


def _split_text_paged(
    page_texts: List[Tuple[int, str]],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[AnnotatedChunk]:
    """Split page-annotated text into chunks that track page provenance.

    Inserts invisible page markers, splits with the recursive splitter,
    then scans each chunk for markers to determine its PageSpan.
    """
    if not page_texts:
        return []

    # Build marked text: insert page markers at each page boundary
    marked_parts = []
    for page_num, text in page_texts:
        marked_parts.append(_PAGE_MARKER.format(page_num))
        marked_parts.append(text)
    marked_text = "".join(marked_parts)

    # Split using existing recursive splitter
    raw_chunks = _split_text(marked_text, chunk_size, chunk_overlap)

    # For each chunk, find page markers to determine span, then strip them
    annotated: List[AnnotatedChunk] = []
    for chunk in raw_chunks:
        markers = _PAGE_MARKER_RE.findall(chunk)
        clean_text = _PAGE_MARKER_RE.sub('', chunk).strip()
        if not clean_text:
            continue

        if markers:
            pages = [int(m) for m in markers]
            span = PageSpan(start_page=min(pages), end_page=max(pages))
        else:
            # No marker in this chunk — it's entirely within a single page.
            # Find the nearest preceding marker from the full text.
            span = PageSpan(start_page=0, end_page=0)

        annotated.append(AnnotatedChunk(text=clean_text, page_span=span))

    # Fix chunks with no markers: propagate from previous chunk
    for i, ac in enumerate(annotated):
        if ac.page_span.start_page == 0 and i > 0:
            prev = annotated[i - 1].page_span
            ac.page_span = PageSpan(start_page=prev.end_page, end_page=prev.end_page)

    return annotated


def _extract_toc(reader: PdfReader) -> List[Dict]:
    """Extract table of contents from PDF outline/bookmarks.

    Returns list of {"title": str, "page": int, "level": int}.
    Returns empty list if PDF has no outline.
    """
    toc: List[Dict] = []

    def _walk_outline(items, level: int = 1):
        for item in items:
            if isinstance(item, list):
                _walk_outline(item, level + 1)
            else:
                try:
                    title = item.get('/Title', str(item))
                    page_num = reader.get_destination_page_number(item) + 1  # 1-based
                    toc.append({"title": title, "page": page_num, "level": level})
                except Exception:
                    pass

    try:
        if reader.outline:
            _walk_outline(reader.outline)
    except Exception:
        pass

    return toc


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
            page_texts: List[Tuple[int, str]] = []
            toc: List[Dict] = []
            is_txt = doc_file.lower().endswith(".txt")

            if is_txt:
                # Plain text file — read directly
                with open(doc_file, "r", errors="replace") as f:
                    text_content = f.read()
                page_count = len(text_content) // 3000 or 1  # Approximate
                page_texts = [(1, _clean_text(text_content))]
            else:
                # PDF file — extract via pypdf with per-page tracking
                reader = PdfReader(doc_file)
                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    if text:
                        cleaned = _clean_text(text)
                        if cleaned:
                            page_texts.append((page_num, cleaned))
                            text_content += cleaned + "\n"
                page_count = len(reader.pages)
                # Extract TOC from PDF bookmarks
                toc = _extract_toc(reader)

            metadata = {
                "source": os.path.basename(doc_file),
                "vault": vault_info["name"],
                "path": rel_path,
                "system_id": system_id,
                "system_family": system_family,
                "priority": priority,
                "page_count": page_count,
            }

            if toc:
                metadata["toc"] = toc

            chapter = _detect_chapter(text_content)
            if chapter:
                metadata["chapter"] = chapter

            subdoc_tags = _detect_subdoc_tags(text_content)
            metadata.update(subdoc_tags)

            documents.append(DocChunk(
                page_content=text_content,
                metadata=metadata,
                page_texts=page_texts,
            ))
            toc_note = f", {len(toc)} TOC entries" if toc else ""
            fmt = "TXT" if is_txt else "PDF"
            print(f"{Colors.GREEN}OK ({page_count} {'chars' if is_txt else 'pages'}, P{priority}, {fmt}{toc_note}){Colors.ENDC}")

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

    # Split documents into page-aware chunks
    print(f"    > Sharding {len(documents)} source docs...", end=" ", flush=True)
    all_chunks: List[DocChunk] = []
    # Collect TOC per source file for the toc_index
    toc_index: Dict[str, List[Dict]] = {}
    for doc in documents:
        source_name = doc.metadata.get("source", "").replace(".pdf", "").replace(".PDF", "")

        # Store TOC for this source
        if doc.metadata.get("toc"):
            toc_index[doc.metadata["source"]] = doc.metadata["toc"]

        # Use page-aware splitter if page_texts available, else fallback
        if doc.page_texts:
            annotated = _split_text_paged(doc.page_texts)
            for ac in annotated:
                tagged_text = f"[{source_name}] {ac.text}" if source_name else ac.text
                meta = dict(doc.metadata)
                meta["page_start"] = ac.page_span.start_page
                meta["page_end"] = ac.page_span.end_page
                all_chunks.append(DocChunk(page_content=tagged_text, metadata=meta))
        else:
            # Fallback for docs with no page_texts (shouldn't happen, but safe)
            texts = _split_text(doc.page_content)
            for text in texts:
                tagged_text = f"[{source_name}] {text}" if source_name else text
                all_chunks.append(DocChunk(page_content=tagged_text, metadata=dict(doc.metadata)))
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
    checkpoint_interval = 10  # Save every 10 batches (500 shards)
    total_chunks = len(all_chunks)
    total_batches = (total_chunks + batch_size - 1) // batch_size
    failed_batches = 0

    new_vectors = []
    new_docstore = dict(existing_docstore)
    new_id_map = dict(existing_id_map)
    current_id = next_id

    # Ensure save directory exists for checkpoints
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Initialize or reuse the running FAISS index for incremental saves
    dim = 768  # nomic-embed-text dimension
    if existing_index is not None:
        running_index = existing_index
    else:
        running_index = faiss.IndexFlatL2(dim)

    def _save_checkpoint(reason: str = "checkpoint"):
        """Flush pending vectors to index and save to disk."""
        nonlocal new_vectors
        if not new_vectors:
            return
        batch_vectors = np.vstack(new_vectors)
        running_index.add(batch_vectors)
        new_vectors = []  # Clear pending

        try:
            faiss.write_index(running_index, faiss_file)
            docstore_data = {
                "version": "3.0",
                "docstore": new_docstore,
                "id_map": {str(k): v for k, v in new_id_map.items()},
                "toc_index": toc_index,
            }
            docstore_path = os.path.join(save_path, "docstore.json")
            with open(docstore_path, "w") as f:
                json.dump(docstore_data, f)
            print(f"    {Colors.GREEN}[CHECKPOINT] Saved {reason}: "
                  f"{running_index.ntotal} vectors on disk.{Colors.ENDC}")
            _logger.info(f"[CHECKPOINT] {reason}: {running_index.ntotal} vectors saved.")
        except Exception as e:
            print(f"    {Colors.WARNING}[CHECKPOINT] Save failed: {e}{Colors.ENDC}")
            _logger.error(f"[CHECKPOINT] Save failed: {e}")

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
                # Docstore v3.0: structured entry with metadata
                new_docstore[doc_id] = {
                    "text": chunk.page_content,
                    "meta": {
                        "source": chunk.metadata.get("source", "").replace(".pdf", "").replace(".PDF", ""),
                        "source_file": chunk.metadata.get("source", ""),
                        "page_start": chunk.metadata.get("page_start", 0),
                        "page_end": chunk.metadata.get("page_end", 0),
                        "system_id": chunk.metadata.get("system_id", ""),
                        "priority": chunk.metadata.get("priority", 2),
                        "chapter": chunk.metadata.get("chapter"),
                    },
                }
                new_id_map[current_id] = doc_id
                current_id += 1

            new_vectors.append(embeddings)

        except Exception as e:
            failed_batches += 1
            err_msg = f"Batch {batch_num}/{total_batches} failed: {e}"
            print(f"    {Colors.FAIL}{err_msg}{Colors.ENDC}")
            _logger.error(err_msg)
            if failed_batches >= 3:
                # Save what we have before aborting
                _save_checkpoint(f"emergency save before abort ({failed_batches} failures)")
                print(f"\n{Colors.FAIL}Too many batch failures ({failed_batches}). "
                      f"Aborting vectorization.{Colors.ENDC}")
                print(f"{Colors.WARNING}Ensure 'ollama serve' is running and "
                      f"you have pulled '{EMBEDDING_MODEL}'{Colors.ENDC}")
                return

        # Periodic checkpoint — save progress every N batches
        if batch_num % checkpoint_interval == 0:
            _save_checkpoint(f"batch {batch_num}/{total_batches}")

    if failed_batches:
        print(f"    {Colors.WARNING}{failed_batches} batch(es) failed during "
              f"vectorization.{Colors.ENDC}")

    # Final save — flush any remaining vectors
    if new_vectors:
        batch_vectors = np.vstack(new_vectors)
        running_index.add(batch_vectors)
        new_vectors = []

    if running_index.ntotal == 0:
        print(f"    {Colors.WARNING}No vectors produced.{Colors.ENDC}")
        return

    print(f"    > Final index: {running_index.ntotal} vectors.")

    try:
        faiss.write_index(running_index, faiss_file)

        # Write docstore.json v3.0 with structured metadata
        docstore_data = {
            "version": "3.0",
            "docstore": new_docstore,
            "id_map": {str(k): v for k, v in new_id_map.items()},
            "toc_index": toc_index,
        }
        docstore_path = os.path.join(save_path, "docstore.json")
        with open(docstore_path, "w") as f:
            json.dump(docstore_data, f)

        print(f"    {Colors.GREEN}Indexing Complete.{Colors.ENDC}")
        print(f"    Saved index & docstore to: {save_path} "
              f"({running_index.ntotal} vectors)")
    except Exception as e:
        print(f"    {Colors.FAIL}Failed to save index: {e}{Colors.ENDC}")


# =========================================================================
# AUTO-RUN (called by Maestro — no interactive menu)
# =========================================================================

def auto_build(mode: str = "smart") -> int:
    """Non-interactive index build for Maestro integration.

    Args:
        mode: "smart" (audit & fix gaps), "all" (delta sync all),
              "force" (full rebuild ignoring manifest).

    Returns:
        Number of systems processed.
    """
    vault_list = get_vaults()
    if not vault_list:
        print(f"{Colors.WARNING}No vaults found.{Colors.ENDC}")
        return 0

    manifest = VaultManifest()

    if mode == "smart":
        print(f"\n{Colors.BLUE}Running index health audit...{Colors.ENDC}")
        gaps = audit_index_health(manifest)
        if not gaps:
            print(f"{Colors.GREEN}All indices healthy — nothing to rebuild.{Colors.ENDC}")
            return 0
        manifest.save()
        selected = [v for v in vault_list if v["system_id"] in gaps]
        total_files = sum(len(f) for f in gaps.values())
        print(f"{Colors.BLUE}Smart rebuild: {total_files} file(s) across "
              f"{len(selected)} system(s).{Colors.ENDC}")
        active_manifest = manifest
    elif mode == "force":
        selected = vault_list
        active_manifest = None
    else:  # "all"
        selected = vault_list
        active_manifest = manifest

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

    return len(selected)


# =========================================================================
# MAIN (interactive — standalone use)
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
    print(f" [S] Smart Rebuild (audit & fix gaps)")
    print(f" [F] Full Rebuild (ignore manifest)")

    choice = input(f"\n{Colors.BLUE}Select System > {Colors.ENDC}").strip().upper()

    full_rebuild = False
    smart_rebuild = False
    selected: List[Dict] = []

    if choice == 'F':
        selected = vault_list
        full_rebuild = True
        print(f"{Colors.WARNING}Full rebuild mode — ignoring manifest.{Colors.ENDC}")
    elif choice == 'S':
        print(f"\n{Colors.BLUE}Running index health audit...{Colors.ENDC}\n")
        gaps = audit_index_health(manifest)
        if not gaps:
            print(f"\n{Colors.GREEN}Nothing to rebuild — all indices are healthy.{Colors.ENDC}")
            return
        # Save manifest with stale entries removed (audit already called manifest.remove)
        manifest.save()
        smart_rebuild = True
        # Select only vaults that have gaps
        gap_systems = set(gaps.keys())
        selected = [v for v in vault_list if v["system_id"] in gap_systems]
        total_files = sum(len(f) for f in gaps.values())
        print(f"\n{Colors.BLUE}Smart rebuild: {total_files} file(s) across "
              f"{len(selected)} system(s) queued for re-indexing.{Colors.ENDC}")
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

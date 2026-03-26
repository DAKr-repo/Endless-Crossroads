"""
scripts/build_indices.py — FAISS Index Builder
===============================================
Scans vault/*/SOURCE/ for PDFs, extracts text, chunks it, embeds each
chunk via Ollama nomic-embed-text, and writes FAISS indices to
faiss_index/{system_id}/.

Docstore format mirrors codex/core/retriever.py:
    {
        "version": 1,
        "docstore": {"doc_0": "text...", ...},
        "id_map":   {"0": "doc_0", ...}
    }

Usage:
    python scripts/build_indices.py --all
    python scripts/build_indices.py --system dnd5e
    python scripts/build_indices.py --all --chunk-size 600 --force
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Generator

import numpy as np
import requests
import faiss
from pypdf import PdfReader
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = PROJECT_ROOT / "vault"
INDEX_ROOT = PROJECT_ROOT / "faiss_index"

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768          # nomic-embed-text output dimension
EMBED_TIMEOUT = 30       # seconds per request
EMBED_RETRY_LIMIT = 3    # retries on transient errors

DEFAULT_CHUNK_SIZE = 800  # characters (increased from 500 for better context)
DEFAULT_OVERLAP = 100     # characters (increased from 50 to reduce boundary splits)

console = Console()


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: Path) -> list[str]:
    """Return list of page text strings from a PDF file.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        List of non-empty page text strings. Empty pages are skipped.

    Raises:
        Exception: Propagates pypdf errors to the caller for logging.
    """
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(text)
    return pages


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _clean_page_text(text: str) -> str:
    """Remove common noise from PDF-extracted text.

    Strips DRM watermarks, repeated headers/footers, and page numbers.
    """
    import re
    # Common DRM watermark pattern
    text = re.sub(r'Property of \w+\..*?Order #\d+', '', text)
    # Standalone page numbers (just a number on a line)
    text = re.sub(r'^\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    # Repeated copyright lines
    text = re.sub(r'©\s*\d{4}.*?(?:Wizards|Hasbro|Elderbrain).*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Collapse excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> Generator[str, None, None]:
    """Yield overlapping chunks from text, preferring paragraph boundaries.

    Tries to break at paragraph boundaries (double newlines) within the
    chunk_size window. Falls back to sentence boundaries, then hard splits.

    Args:
        text: Raw text to split.
        chunk_size: Maximum characters per chunk.
        overlap: Characters shared between consecutive chunks.

    Yields:
        Non-empty stripped chunks.
    """
    if not text:
        return

    step = max(1, chunk_size - overlap)
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # If we're not at the end, try to break at a natural boundary
        if end < text_len:
            # Try paragraph break first (double newline)
            para_break = text.rfind('\n\n', start + step // 2, end)
            if para_break > start:
                end = para_break

            # Try sentence break (period + space/newline)
            elif text[end - 1] not in '.!?\n':
                sent_break = max(
                    text.rfind('. ', start + step // 2, end),
                    text.rfind('.\n', start + step // 2, end),
                )
                if sent_break > start:
                    end = sent_break + 1  # Include the period

        chunk = text[start:end].strip()
        if chunk and len(chunk) > 20:  # Skip tiny fragments
            yield chunk

        # Advance by step, but don't go past where we actually ended
        start = max(start + step, end - overlap)


def chunks_from_pages(
    pages: list[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    source_name: str = "",
) -> list[str]:
    """Convert a list of page strings into a flat list of text chunks.

    Cleans noise (watermarks, page numbers) before chunking.
    Optionally prefixes chunks with source name for provenance.

    Args:
        pages: Page-level text extracted from a PDF.
        chunk_size: Characters per chunk.
        overlap: Overlap between consecutive chunks.
        source_name: Optional PDF filename to prefix chunks with.

    Returns:
        Ordered list of text chunks across all pages.
    """
    all_chunks: list[str] = []
    prefix = f"[{source_name}] " if source_name else ""

    for page_idx, page_text in enumerate(pages):
        cleaned = _clean_page_text(page_text)
        if not cleaned:
            continue
        for chunk in chunk_text(cleaned, chunk_size, overlap):
            all_chunks.append(f"{prefix}{chunk}" if prefix else chunk)

    return all_chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_text(text: str) -> np.ndarray | None:
    """Get a float32 embedding vector from Ollama nomic-embed-text.

    Mirrors the logic in codex/core/retriever.py CodexRetriever._embed().

    Args:
        text: Text to embed.

    Returns:
        1-D float32 numpy array of shape (EMBED_DIM,), or None on failure.
    """
    for attempt in range(1, EMBED_RETRY_LIMIT + 1):
        try:
            resp = requests.post(
                OLLAMA_EMBED_URL,
                json={"model": EMBED_MODEL, "input": text},
                timeout=EMBED_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings") or data.get("embedding")
            if embeddings:
                vec = embeddings[0] if isinstance(embeddings[0], list) else embeddings
                return np.array(vec, dtype="float32")
        except requests.exceptions.ConnectionError:
            # Ollama not running — surface immediately, no point retrying.
            raise
        except Exception as exc:
            if attempt == EMBED_RETRY_LIMIT:
                console.print(
                    f"[yellow]  Warning: embed failed after {EMBED_RETRY_LIMIT} "
                    f"attempts — {exc}[/yellow]"
                )
            else:
                time.sleep(0.5 * attempt)
    return None


def check_ollama() -> bool:
    """Verify Ollama is reachable and nomic-embed-text is available.

    Returns:
        True if a test embed succeeds, False otherwise.
    """
    try:
        vec = embed_text("ping")
        return vec is not None
    except requests.exceptions.ConnectionError:
        return False


# ---------------------------------------------------------------------------
# FAISS index building
# ---------------------------------------------------------------------------

def build_index_for_system(
    system_id: str,
    pdf_paths: list[Path],
    chunk_size: int,
    overlap: int,
    force: bool,
    progress: Progress,
) -> dict:
    """Build and write a FAISS index for one system.

    Args:
        system_id: System identifier (e.g. "dnd5e"). Used as output dir name.
        pdf_paths: List of PDF files to index.
        chunk_size: Characters per chunk.
        overlap: Overlap characters between chunks.
        force: If False, skip systems whose index.faiss already exists.
        progress: Shared Rich Progress instance for nested task display.

    Returns:
        Summary dict with keys: system_id, pdfs, chunks, skipped, error.
    """
    out_dir = INDEX_ROOT / system_id
    faiss_file = out_dir / "index.faiss"

    # Skip check
    if faiss_file.exists() and not force:
        return {
            "system_id": system_id,
            "pdfs": len(pdf_paths),
            "chunks": 0,
            "skipped": True,
            "error": None,
        }

    # Collect all chunks across all PDFs
    all_chunks: list[str] = []
    pdf_task = progress.add_task(
        f"  [cyan]{system_id}[/cyan] — reading PDFs",
        total=len(pdf_paths),
    )

    for pdf_path in pdf_paths:
        progress.update(
            pdf_task,
            description=f"  [cyan]{system_id}[/cyan] — [dim]{pdf_path.name}[/dim]",
        )
        try:
            pages = extract_pdf_text(pdf_path)
            source = pdf_path.stem  # Filename without extension
            chunks = chunks_from_pages(pages, chunk_size, overlap, source_name=source)
            all_chunks.extend(chunks)
        except Exception as exc:
            console.print(
                f"[yellow]  Warning: could not read {pdf_path.name} — {exc}[/yellow]"
            )
        progress.advance(pdf_task)

    progress.remove_task(pdf_task)

    if not all_chunks:
        return {
            "system_id": system_id,
            "pdfs": len(pdf_paths),
            "chunks": 0,
            "skipped": False,
            "error": "No text extracted from PDFs",
        }

    # Embed all chunks
    vectors: list[np.ndarray] = []
    docstore: dict[str, str] = {}
    id_map: dict[str, str] = {}

    embed_task = progress.add_task(
        f"  [cyan]{system_id}[/cyan] — embedding chunks",
        total=len(all_chunks),
    )

    for i, chunk in enumerate(all_chunks):
        progress.update(
            embed_task,
            description=(
                f"  [cyan]{system_id}[/cyan] — embedding "
                f"[dim]{i + 1}/{len(all_chunks)}[/dim]"
            ),
        )
        vec = embed_text(chunk)
        if vec is not None:
            doc_id = f"doc_{len(vectors)}"
            docstore[doc_id] = chunk
            id_map[str(len(vectors))] = doc_id
            vectors.append(vec)
        progress.advance(embed_task)

    progress.remove_task(embed_task)

    if not vectors:
        return {
            "system_id": system_id,
            "pdfs": len(pdf_paths),
            "chunks": len(all_chunks),
            "skipped": False,
            "error": "All embeddings failed — is Ollama running?",
        }

    # Build FAISS index
    matrix = np.vstack(vectors).astype("float32")
    dim = matrix.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(matrix)

    # Write outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(faiss_file))

    docstore_data = {
        "version": 1,
        "docstore": docstore,
        "id_map": id_map,
    }
    (out_dir / "docstore.json").write_text(
        json.dumps(docstore_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "system_id": system_id,
        "pdfs": len(pdf_paths),
        "chunks": len(vectors),
        "skipped": False,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_systems(vault_root: Path) -> dict[str, list[Path]]:
    """Scan vault directories for PDF files under SOURCE/ subdirectories.

    Handles two layouts:
      - Flat:  vault/<system>/SOURCE/*.pdf         (e.g. dnd5e, stc, burnwillow)
      - Group: vault/<group>/<system>/SOURCE/*.pdf  (e.g. FITD/bitd, ILLUMINATED_WORLDS/Candela_Obscura)

    Group directories are detected as top-level vault entries that contain no
    SOURCE/ dir themselves but whose children do (e.g. ``vault/FITD/``).

    Vault directory names that differ from canonical Codex system IDs are
    normalised via VAULT_DIR_TO_SYSTEM_ID before being added to the result.

    Args:
        vault_root: Root of the vault directory.

    Returns:
        Dict mapping system_id -> sorted list of PDF Paths.
        Systems with no PDFs are excluded.
    """
    # Map vault directory names → canonical Codex system IDs where they differ.
    VAULT_DIR_TO_SYSTEM_ID: dict[str, str] = {
        "Candela_Obscura": "candela",
        "CBR_PNK": "cbrpnk",
    }

    systems: dict[str, list[Path]] = {}
    if not vault_root.exists():
        return systems

    def _collect(system_dir: Path) -> None:
        """Collect ALL PDFs from a system directory, scanning all subdirectories.

        WO-V156: Scans the entire system directory tree for PDFs — SOURCE/,
        MODULES/, MODULE/, SETTINGS/, SUPPLEMENTS/, and any other subfolders.
        The vault folder structure is for human organization; the indexer
        should find every PDF regardless of which subfolder it's in.
        """
        raw_pdfs = sorted(system_dir.rglob("*.pdf")) + sorted(system_dir.rglob("*.PDF"))
        unique_pdfs = list(dict.fromkeys(raw_pdfs))
        if unique_pdfs:
            system_id = VAULT_DIR_TO_SYSTEM_ID.get(system_dir.name, system_dir.name)
            systems[system_id] = unique_pdfs

    for top_dir in sorted(vault_root.iterdir()):
        if not top_dir.is_dir():
            continue
        # A system directory has its own SOURCE/, MODULES/, etc.
        # A group directory (like FITD/) contains child system directories.
        is_system = any(
            (top_dir / name).is_dir()
            for name in ("SOURCE", "MODULES", "MODULE", "SETTINGS", "SUPPLEMENTS")
        )
        if is_system:
            _collect(top_dir)
        else:
            # Group directory — recurse into children
            for child_dir in sorted(top_dir.iterdir()):
                if child_dir.is_dir():
                    child_is_system = any(
                        (child_dir / name).is_dir()
                        for name in ("SOURCE", "MODULES", "MODULE", "SETTINGS", "SUPPLEMENTS")
                    ) or any(child_dir.rglob("*.pdf")) or any(child_dir.rglob("*.PDF"))
                    if child_is_system:
                        _collect(child_dir)

    return systems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed Namespace with attributes: system, all, chunk_size, overlap, force.
    """
    parser = argparse.ArgumentParser(
        prog="build_indices",
        description=(
            "Build FAISS semantic search indices from PDFs in vault/*/SOURCE/. "
            "Requires Ollama running with nomic-embed-text loaded."
        ),
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--system",
        metavar="SYSTEM_ID",
        help="Build index for a single system (e.g. dnd5e).",
    )
    target.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Build indices for all systems with PDFs (default).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        metavar="N",
        help=f"Characters per text chunk (default: {DEFAULT_CHUNK_SIZE}).",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        metavar="N",
        help=f"Overlap characters between chunks (default: {DEFAULT_OVERLAP}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild indices even if index.faiss already exists.",
    )
    parser.add_argument(
        "--pdf",
        metavar="PATH",
        nargs="+",
        help=(
            "Index specific PDF file(s) into the given system's index. "
            "Requires --system. Does a delta merge (adds to existing index). "
            "Example: --system dnd5e --pdf 'vault/dnd5e/MODULES/Curse of Strahd.pdf'"
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Main entry point.

    Returns:
        Exit code: 0 on success, 1 on fatal error.
    """
    args = parse_args()

    console.print(
        Panel.fit(
            "[bold cyan]Codex FAISS Index Builder[/bold cyan]\n"
            f"Vault: [dim]{VAULT_ROOT}[/dim]\n"
            f"Output: [dim]{INDEX_ROOT}[/dim]",
            border_style="cyan",
        )
    )

    # Discover available systems
    all_systems = discover_systems(VAULT_ROOT)

    if not all_systems:
        console.print(
            "[yellow]No PDFs found under vault/*/SOURCE/. "
            "Place PDF files in vault/<system_id>/SOURCE/ and re-run.[/yellow]"
        )
        return 0

    # Handle --pdf: index specific files into a system
    if args.pdf:
        if not args.system:
            console.print("[red]--pdf requires --system to know which index to add to.[/red]")
            return 1
        pdf_paths = []
        for p in args.pdf:
            path = Path(p)
            if not path.exists():
                console.print(f"[red]PDF not found: {p}[/red]")
                return 1
            pdf_paths.append(path)
        target_systems = {args.system: pdf_paths}
        # Force merge since we're adding specific files
        args.force = True
        console.print(f"\n[bold]Indexing {len(pdf_paths)} specific PDF(s) into [cyan]{args.system}[/cyan]:[/bold]")
        for p in pdf_paths:
            console.print(f"  {p.name}")
        console.print()
    # Apply --system filter
    elif args.system:
        if args.system not in all_systems:
            console.print(
                f"[red]System '[bold]{args.system}[/bold]' has no PDFs in "
                f"vault/{args.system}/ (or directory does not exist).[/red]"
            )
            console.print(
                f"Available systems: {', '.join(sorted(all_systems.keys()))}"
            )
            return 1
        target_systems = {args.system: all_systems[args.system]}
    else:
        target_systems = all_systems

    # Show discovery summary
    console.print(f"\nFound [bold]{len(target_systems)}[/bold] system(s) with PDFs:\n")
    for sid, pdfs in sorted(target_systems.items()):
        console.print(f"  [cyan]{sid}[/cyan] — {len(pdfs)} PDF(s)")
    console.print()

    # Check Ollama connectivity before starting
    console.print("[dim]Checking Ollama connectivity...[/dim]")
    if not check_ollama():
        console.print(
            "[red]Cannot reach Ollama at localhost:11434 or "
            f"'{EMBED_MODEL}' not loaded.\n"
            "Start Ollama with: ollama serve\n"
            f"Pull model with:   ollama pull {EMBED_MODEL}[/red]"
        )
        return 1
    console.print(f"[green]Ollama OK — using {EMBED_MODEL}[/green]\n")

    # Build indices with progress display
    results: list[dict] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        system_task = progress.add_task(
            "[bold]Systems[/bold]", total=len(target_systems)
        )

        for system_id, pdf_paths in sorted(target_systems.items()):
            progress.update(
                system_task,
                description=f"[bold]Processing[/bold] [cyan]{system_id}[/cyan]",
            )
            result = build_index_for_system(
                system_id=system_id,
                pdf_paths=pdf_paths,
                chunk_size=args.chunk_size,
                overlap=args.overlap,
                force=args.force,
                progress=progress,
            )
            results.append(result)
            progress.advance(system_task)

        progress.update(system_task, description="[bold]Done[/bold]")

    # Results table
    console.print()
    table = Table(title="Build Results", border_style="cyan", show_lines=True)
    table.add_column("System", style="cyan", no_wrap=True)
    table.add_column("PDFs", justify="right")
    table.add_column("Chunks", justify="right")
    table.add_column("Status", justify="center")

    success_count = 0
    for r in results:
        if r["skipped"]:
            status = "[yellow]Skipped[/yellow]"
        elif r["error"]:
            status = f"[red]Error[/red]\n[dim]{r['error']}[/dim]"
        else:
            status = "[green]OK[/green]"
            success_count += 1

        table.add_row(
            r["system_id"],
            str(r["pdfs"]),
            str(r["chunks"]),
            status,
        )

    console.print(table)
    console.print(
        f"\n[bold]{success_count}/{len(results)}[/bold] system(s) indexed successfully."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
LibrarianTUI -- Three-panel knowledge browser for Mimir's Vault.
================================================================

Uses Rich Layout to present:
  - [Tome Index]   2-column width: tree-grouped book list + special vaults
  - [Open Page]    5-column width: chapters / maps / graveyard / seeds
  - [Consult Mimir] 3-column width: Mimir Q&A restricted to current book

Populates its index from vault directories.  Supports two modes:

  - **Full access** (system_id=None): scan every leaf vault, descending
    into family parents like FITD/ and ILLUMINATED_WORLDS/.
  - **Restricted folio** (system_id set): show only the books belonging
    to the requested chronicle, resolved via VAULT_SYSTEM_MAP with a
    case-insensitive fallback.

Two-level numeric navigation:
  - Main index: typing a number opens the corresponding tome.
  - Inside a tome: typing a number selects the corresponding chapter.

Special sections:
  - **Seed Vault**: Procedural dungeon seeds archived by game sessions.
  - **Hall of Heroes**: Memorial graveyard for fallen characters.
  - **[M] Maps**: Toggle to show generated maps for the active tome.

AMD-05: includes Quick Reference: Laws command for Code Legal shards.
"""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from rich.console import Console
from rich.layout import Layout
from rich.markup import escape
from rich.panel import Panel
from rich.tree import Tree
from rich import box

try:
    from codex.forge.source_scanner import scan_vault_structure
    _VAULT_SCANNER_AVAILABLE = True
except ImportError:
    _VAULT_SCANNER_AVAILABLE = False

try:
    from codex.core.services.cartography import list_maps
    _CARTOGRAPHY_AVAILABLE = True
except ImportError:
    _CARTOGRAPHY_AVAILABLE = False

try:
    from codex.core.world.world_ledger import HistoricalEvent, EventType, AuthorityLevel
    _CHRONOLOGY_AVAILABLE = True
except ImportError:
    _CHRONOLOGY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Vault-path resolution helpers
# ---------------------------------------------------------------------------

# Family directories whose children are individual systems
_FAMILY_PARENTS = {"FITD", "ILLUMINATED_WORLDS"}

# Human-friendly labels for family groups and system directories
_FAMILY_LABELS: Dict[str, str] = {
    "FITD": "Forged in the Dark",
    "ILLUMINATED_WORLDS": "Illuminated Worlds",
}

_DISPLAY_NAMES: Dict[str, str] = {
    "dnd5e": "D&D 5e",
    "bitd": "Blades in the Dark",
    "bob": "Band of Blades",
    "sav": "Scum and Villainy",
    "CBR_PNK": "CBR+PNK",
    "Candela_Obscura": "Candela Obscura",
    "stc": "Stormlight",
    "burnwillow": "Burnwillow",
}


def _friendly_name(book_key: str) -> str:
    """Return a display-friendly name for a vault directory."""
    return _DISPLAY_NAMES.get(book_key, book_key.replace("_", " ").title())


def _load_persona_data() -> dict:
    """Load the full mimir_persona.json data."""
    persona_path = Path(__file__).with_name("mimir_persona.json")
    if persona_path.exists():
        try:
            return json.loads(persona_path.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def _resolve_vault_paths(
    vault_root: Path, system_id: Optional[str] = None,
) -> Dict[Optional[str], List[Path]]:
    """Return a nested mapping ``{family_name_or_None: [leaf_paths]}``.

    Family parents (FITD, ILLUMINATED_WORLDS) become dict keys whose
    values list their child system directories.  Top-level vaults that
    are not inside a family appear under the ``None`` key.

    When *system_id* is set, only the matching leaf is returned (under
    its family key, or ``None`` for a top-level vault).
    """
    if not vault_root.exists():
        return {}

    if system_id is not None:
        sid = system_id.lower()
        # 1. Direct child
        for child in vault_root.iterdir():
            if child.is_dir() and child.name.lower() == sid:
                return {None: [child]}
        # 2. Inside a family parent
        for child in vault_root.iterdir():
            if child.is_dir() and child.name in _FAMILY_PARENTS:
                for sub in child.iterdir():
                    if sub.is_dir() and sub.name.lower() == sid:
                        return {child.name: [sub]}
        # 3. Check VAULT_SYSTEM_MAP reverse mapping
        try:
            from codex.integrations.vault_processor import VAULT_SYSTEM_MAP
            for folder_name, mapped_id in VAULT_SYSTEM_MAP.items():
                if mapped_id.lower() == sid or folder_name.lower() == sid:
                    candidate = vault_root / folder_name
                    if candidate.is_dir():
                        return {None: [candidate]}
                    for parent in vault_root.iterdir():
                        if parent.is_dir() and parent.name in _FAMILY_PARENTS:
                            candidate = parent / folder_name
                            if candidate.is_dir():
                                return {parent.name: [candidate]}
        except ImportError:
            pass
        return {}

    # Full scan -- families first, then standalone
    result: Dict[Optional[str], List[Path]] = {}
    standalone: List[Path] = []
    for child in sorted(vault_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in _FAMILY_PARENTS:
            subs = sorted(sub for sub in child.iterdir() if sub.is_dir())
            if subs:
                result[child.name] = subs
        else:
            standalone.append(child)
    if standalone:
        result[None] = standalone
    return result


# ---------------------------------------------------------------------------
# LibrarianTUI
# ---------------------------------------------------------------------------

class LibrarianTUI:
    """Three-panel knowledge browser for Mimir's Vault."""

    def __init__(
        self,
        vault_path: Optional[Path] = None,
        mimir_fn: Optional[Callable] = None,
        system_id: Optional[str] = None,
        butler=None,
        cache=None,
    ):
        from codex.paths import VAULT_DIR
        self._vault_root = vault_path or VAULT_DIR
        self._mimir = mimir_fn
        self._system_id = system_id
        self._butler = butler
        self._cache = cache  # LoreCache instance or None (WO V20.5.4)
        self._index: Dict[str, List[str]] = {}      # book key -> chapter names
        self._book_paths: Dict[str, Path] = {}       # book key -> filesystem Path
        self._vault_map: Dict[int, str] = {}          # tome number -> book key
        self._chapter_map: Dict[int, str] = {}        # chapter number -> chapter name
        # (family_label or None, [(num, book_key), ...])
        self._groups: List[Tuple[Optional[str], List[Tuple[int, str]]]] = []
        self._current_book: Optional[str] = None
        self._current_chapter: Optional[str] = None
        self._current_text: str = ""
        self._query_history: List[str] = []

        # V10.0: Map view toggle
        self._map_view: bool = False

        # V10.0-B / V11.0: Special view modes
        self._grave_view: bool = False
        self._seed_view: bool = False
        # WO-V8.0: World Atlas view
        self._atlas_view: bool = False
        self._atlas_worlds: Dict[int, dict] = {}
        self._atlas_profile: Optional[dict] = None
        self._grave_entries: Dict[str, List[dict]] = {}
        self._grave_map: Dict[int, dict] = {}
        self._seed_entries: List[dict] = []
        self._seed_map: Dict[int, dict] = {}
        self._selected_grave: Optional[dict] = None
        self._selected_seed: Optional[dict] = None
        self._file_map: Dict[int, Path] = {}  # files within a chapter dir
        self._pdf_mode: bool = False       # True when reading a PDF
        self._pdf_reader = None            # pypdf PdfReader instance
        self._pdf_path: Optional[Path] = None  # Path to active PDF
        self._pdf_page: int = 0            # Current page index (0-based)
        self._pdf_total_pages: int = 0     # Total pages in active PDF

        # D1 (WO-V9.5): Content-type tags from scan_vault_structure
        self._content_tags: Dict[str, List[str]] = {}  # book_key -> ["rules","settings",...]

        # WO-V11.2: Chronology view state
        self._chrono_view: bool = False
        self._chrono_filter: Optional[str] = None  # EventType value string or None
        self._chrono_events: list = []

        # Resolve chronicle name and quotes for display
        persona = _load_persona_data()
        self._system_mappings = persona.get("system_mappings", {})
        self._system_quotes = persona.get("system_quotes", {})
        self._chronicle_name = self._resolve_chronicle_name()

        # WO-V9.0: World Ledger for mutation tracking
        self._world_ledger = None

        self._build_index()

    def set_world_ledger(self, ledger) -> None:
        """Attach a WorldLedger for mutation highlighting in Atlas view."""
        self._world_ledger = ledger

    def _resolve_chronicle_name(self) -> str:
        """Friendly display name for the active chronicle."""
        if self._system_id is None:
            return ""
        sid = self._system_id.lower()
        if sid in self._system_mappings:
            return self._system_mappings[sid]
        return f"The {self._system_id.upper()} chronicle"

    def _build_index(self):
        """Scan vault hierarchy and build index, vault map, and groups."""
        hierarchy = _resolve_vault_paths(self._vault_root, self._system_id)

        for _family, paths in hierarchy.items():
            for book_dir in paths:
                chapters: List[str] = []
                for sub in sorted(book_dir.iterdir()):
                    if sub.is_dir():
                        chapters.append(sub.name)
                    elif sub.suffix == ".pdf":
                        chapters.append(sub.stem)
                if chapters:
                    self._index[book_dir.name] = chapters
                    self._book_paths[book_dir.name] = book_dir

        # WO-V9.5 D1: Annotate tomes with content-type tags from vault scanner
        if _VAULT_SCANNER_AVAILABLE:
            for book_key, book_path in self._book_paths.items():
                try:
                    structure = scan_vault_structure(str(book_path))
                    tags = []
                    for cat in ("rules", "settings", "modules"):
                        if structure.get(cat):
                            tags.append(cat)
                    if tags:
                        self._content_tags[book_key] = tags
                except Exception:
                    pass

        # Build vault_map (numeric tome selection) and display groups
        self._vault_map = {}
        self._groups = []
        counter = 1

        for family, paths in hierarchy.items():
            group_entries: List[Tuple[int, str]] = []
            for book_dir in paths:
                if book_dir.name in self._index:
                    self._vault_map[counter] = book_dir.name
                    group_entries.append((counter, book_dir.name))
                    counter += 1
            if group_entries:
                label = _FAMILY_LABELS.get(family, family) if family else None
                self._groups.append((label, group_entries))

    def _build_chapter_map(self):
        """Rebuild chapter map for the currently open book."""
        self._chapter_map = {}
        if self._current_book and self._current_book in self._index:
            for i, chapter in enumerate(self._index[self._current_book], 1):
                self._chapter_map[i] = chapter

    # ------------------------------------------------------------------
    # PDF reader helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_pdf_text(text: str) -> str:
        """Clean pypdf output: fix ligatures, collapse whitespace."""
        # Common ligature replacements
        text = text.replace('\ufb01', 'fi')
        text = text.replace('\ufb02', 'fl')
        text = text.replace('\ufb00', 'ff')
        text = text.replace('\ufb03', 'ffi')
        text = text.replace('\ufb04', 'ffl')
        # Collapse 3+ blank lines into 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Collapse multiple spaces (but not newlines)
        text = re.sub(r'[^\S\n]{2,}', ' ', text)
        # Strip trailing whitespace per line
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        text = text.strip()
        # Escape Rich markup characters to prevent [bracketed] text crashing panels
        text = escape(text)
        return text

    def _open_pdf(self, pdf_path: Path) -> bool:
        """Enter PDF reader mode with lazy loading.

        Returns True on success, False on error.
        """
        try:
            from pypdf import PdfReader
            self._pdf_reader = PdfReader(str(pdf_path))
            self._pdf_path = pdf_path
            self._pdf_total_pages = len(self._pdf_reader.pages)
            self._pdf_page = 0
            self._pdf_mode = True

            # Check if the PDF has any readable text (sample first 5 pages)
            sample_count = min(5, self._pdf_total_pages)
            has_text = any(
                (p.extract_text() or "").strip()
                for p in self._pdf_reader.pages[:sample_count]
            )
            if not has_text and self._pdf_total_pages <= 5:
                # Small PDF with no extractable text at all (image-only)
                self._current_text = (
                    "[yellow]This PDF has no readable text (image-only).[/yellow]"
                )
                return True  # Still open it — user may want to navigate

            self._load_pdf_page(0)
            return True
        except Exception as e:
            self._current_text = f"[red]Could not open PDF: {e}[/red]"
            self._pdf_reader = None
            self._pdf_mode = False
            return False

    def _load_pdf_page(self, page_idx: int):
        """Extract and sanitize a single page for display, auto-skipping empty pages."""
        if not self._pdf_reader:
            return
        if page_idx < 0 or page_idx >= self._pdf_total_pages:
            return

        # Try to find a non-empty page starting from page_idx
        original_idx = page_idx
        skipped = 0
        raw = ""
        while page_idx < self._pdf_total_pages:
            raw = self._pdf_reader.pages[page_idx].extract_text() or ""
            if raw.strip():
                break
            skipped += 1
            page_idx += 1

        if not raw.strip():
            # All remaining pages are empty — stay on original
            self._pdf_page = original_idx
            self._current_text = "(No extractable text on this or following pages)"
            return

        self._pdf_page = page_idx
        page_indicator = f"Page {page_idx + 1}/{self._pdf_total_pages}"
        if skipped > 0:
            page_indicator += f" ({skipped} empty skipped)"

        sanitized = self._sanitize_pdf_text(raw)
        self._current_text = f"[dim]{page_indicator}[/dim]\n{sanitized}"

    def _close_pdf(self):
        """Exit PDF reader mode and release resources."""
        self._pdf_reader = None
        self._pdf_path = None
        self._pdf_total_pages = 0
        self._pdf_page = 0
        self._pdf_mode = False

    def _load_seed_data(self) -> List[dict]:
        """Load seeds from the seed ledger."""
        from codex.paths import VAULT_MAPS_DIR
        ledger = VAULT_MAPS_DIR / "seed_ledger.json"
        if ledger.exists():
            try:
                data = json.loads(ledger.read_text())
                return data.get("seeds", [])
            except (json.JSONDecodeError, KeyError):
                pass
        return []

    def _load_graveyard_data(self) -> Dict[str, List[dict]]:
        """Load graveyard entries grouped by system."""
        try:
            from codex.core.services.graveyard import list_fallen
            return list_fallen(
                system_id=self._system_id
            )
        except ImportError:
            return {}

    def _count_graveyard(self) -> int:
        """Total number of fallen heroes across all systems."""
        return sum(len(v) for v in self._grave_entries.values())

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def open_book(self, name: str) -> bool:
        """Select a book by exact name or case-insensitive fallback."""
        key = None
        if name in self._index:
            key = name
        else:
            for book in self._index:
                if book.lower() == name.lower():
                    key = book
                    break
        if key is None:
            return False
        self._current_book = key
        self._current_chapter = None
        self._map_view = False
        self._grave_view = False
        self._seed_view = False
        self._selected_grave = None
        self._selected_seed = None
        self._build_chapter_map()
        count = len(self._index[key])
        self._current_text = (
            f"Tome: {_friendly_name(key)}  --  {count} chapter(s)"
        )
        return True

    def select_chapter(self, chapter_name: str) -> bool:
        """Select a chapter within the current book."""
        if not self._current_book:
            return False
        if chapter_name not in self._index.get(self._current_book, []):
            return False
        self._current_chapter = chapter_name
        self._file_map = {}
        book_path = self._book_paths.get(self._current_book)
        if not book_path:
            self._current_text = f"Chapter: {chapter_name}"
            return True
        chapter_path = book_path / chapter_name
        if chapter_path.is_dir():
            files = sorted(
                f for f in chapter_path.iterdir() if f.is_file()
            )
            lines = [f"[bold]{chapter_name}/[/bold]", ""]
            for i, f in enumerate(files, 1):
                self._file_map[i] = f
                if f.suffix.lower() == ".pdf":
                    lines.append(
                        f"  [bold white]\\[{i}][/bold white] "
                        f"[bold cyan]{f.name}[/bold cyan]"
                    )
                else:
                    lines.append(
                        f"  [bold white]\\[{i}][/bold white] {f.name}"
                    )
            self._current_text = "\n".join(lines) if files else (
                f"{chapter_name}/ [dim](empty)[/dim]"
            )
        elif chapter_path.with_suffix(".pdf").exists():
            pdf_path = chapter_path.with_suffix(".pdf")
            self._open_pdf(pdf_path)
        else:
            self._current_text = f"[bold]{chapter_name}[/bold]"
        return True

    def close_book(self):
        """Return to the top-level tome index."""
        self._current_book = None
        self._current_chapter = None
        self._current_text = ""
        self._chapter_map = {}
        self._file_map = {}
        self._close_pdf()
        self._map_view = False

    def enter_graveyard(self):
        """Switch to the Memorial Hall view."""
        self.close_book()
        self._grave_view = True
        self._seed_view = False
        self._grave_entries = self._load_graveyard_data()
        # Build numbered selection map across all systems
        self._grave_map = {}
        counter = 1
        for _sid, fallen in self._grave_entries.items():
            for entry in fallen:
                self._grave_map[counter] = entry
                counter += 1

    def enter_seed_vault(self):
        """Switch to the Seed Vault view."""
        self.close_book()
        self._seed_view = True
        self._grave_view = False
        self._seed_entries = self._load_seed_data()
        self._seed_map = {}
        for i, seed in enumerate(self._seed_entries, 1):
            self._seed_map[i] = seed

    def enter_atlas(self):
        """Switch to the World Atlas view -- scans worlds/*.json."""
        self.close_book()
        self._atlas_view = True
        self._grave_view = False
        self._seed_view = False
        self._atlas_profile = None
        self._atlas_worlds = {}

        worlds_dir = self._vault_root.parent.parent / "worlds"
        if not worlds_dir.exists():
            return

        counter = 1
        for path in sorted(worlds_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                self._atlas_worlds[counter] = {
                    "name": data.get("name", path.stem),
                    "genre": data.get("genre", "Unknown"),
                    "tone": data.get("tone", "Unknown"),
                    "grapes": data.get("grapes", {}),
                }
                counter += 1
            except (json.JSONDecodeError, KeyError):
                pass

    def enter_chronology(self):
        """Switch to the Chronology timeline view."""
        self.close_book()
        self._chrono_view = True
        self._grave_view = False
        self._seed_view = False
        self._atlas_view = False
        self._chrono_filter = None
        self._chrono_events = []

        if self._world_ledger and hasattr(self._world_ledger, 'get_chronology'):
            self._chrono_events = self._world_ledger.get_chronology(limit=50)
        elif _CHRONOLOGY_AVAILABLE:
            # Try loading from most recent world JSON directly
            worlds_dir = self._vault_root.parent.parent / "worlds"
            if worlds_dir.exists():
                files = sorted(worlds_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                if files:
                    try:
                        data = json.loads(files[0].read_text())
                        self._chrono_events = [
                            HistoricalEvent.from_dict(e)
                            for e in data.get("chronology", [])
                        ]
                        self._chrono_events.reverse()  # most-recent-first
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass

    def _render_chronology(self) -> Panel:
        """Center panel: vertical timeline with authority-level color coding."""
        events = self._chrono_events
        if self._chrono_filter and self._chrono_filter != "all":
            events = [
                e for e in events
                if (isinstance(e, HistoricalEvent) and e.event_type.value == self._chrono_filter)
                or (isinstance(e, dict) and e.get("event_type") == self._chrono_filter)
            ]

        if not events:
            if self._chrono_filter and self._chrono_filter != "all":
                content = f"[dim]No events matching filter '{self._chrono_filter}'.\nType 'all' to clear filter.[/dim]"
            else:
                content = "[dim]No historical events recorded yet.\nWorld mutations and civic events will appear here.[/dim]"
        else:
            lines = []
            for e in events:
                if isinstance(e, HistoricalEvent):
                    ts = e.timestamp[:16].replace("T", " ") if len(e.timestamp) >= 16 else e.timestamp
                    etype = e.event_type.value.upper()
                    summary = e.summary
                    auth = e.authority_level
                    source = e.source or ""
                else:
                    ts = str(e.get("timestamp", ""))[:16].replace("T", " ")
                    etype = str(e.get("event_type", "?")).upper()
                    summary = e.get("summary", "?")
                    auth_val = e.get("authority_level", 2)
                    auth = AuthorityLevel(auth_val) if _CHRONOLOGY_AVAILABLE else None
                    source = e.get("source", "")

                # Authority-level color coding
                if _CHRONOLOGY_AVAILABLE and isinstance(auth, AuthorityLevel):
                    if auth == AuthorityLevel.EYEWITNESS:
                        style_open, style_close = "[bold white]", "[/bold white]"
                    elif auth == AuthorityLevel.LEGEND:
                        style_open, style_close = "[dim italic]", "[/dim italic]"
                    else:
                        style_open, style_close = "[yellow]", "[/yellow]"
                else:
                    style_open, style_close = "", ""

                auth_label = auth.name if isinstance(auth, AuthorityLevel) else "?"
                lines.append(
                    f"{style_open}{ts}  [{etype}]  {summary}{style_close}"
                )
                lines.append(
                    f"  [dim]{auth_label} | {source}[/dim]"
                )
                lines.append("")

            content = "\n".join(lines)

        filter_hint = "[dim]Filter: war | discovery | mutation | political | economic | social | civic | faction | all[/dim]"
        subtitle = f"[dim]{self._chrono_filter or 'all'}[/dim]" if self._chrono_filter else filter_hint
        return Panel(
            content,
            title="[bold]World Chronology[/bold]",
            subtitle=subtitle,
            border_style="dark_goldenrod",
        )

    def _render_atlas_index(self) -> Panel:
        """Render the World Atlas index listing."""
        if not self._atlas_worlds:
            content = "[dim]No saved worlds found.\nUse the Genesis Wizard to create one.[/dim]"
        else:
            lines = []
            for num, world in self._atlas_worlds.items():
                lines.append(
                    f"  [bold white]\\[{num}][/bold white] "
                    f"[bold]{world['name']}[/bold] "
                    f"[dim]{world['genre']} | {world['tone']}[/dim]"
                )
            content = "\n".join(lines)
        return Panel(content, title="[bold]World Atlas[/bold]", border_style="gold1")

    def _is_mutated_entry(self, category: str, entry) -> bool:
        """Detect if a GRAPES entry has been mutated by world events."""
        if isinstance(entry, dict):
            # Geography: cleared locations
            feature = entry.get("feature", "")
            if isinstance(feature, str) and feature.startswith("Cleared by"):
                return True
            # Economics: depleted resources
            if entry.get("abundance") == "depleted":
                return True
        return False

    def _render_atlas_detail(self, grapes_dict: dict) -> Panel:
        """Render a 6-section G.R.A.P.E.S. breakdown for a selected world.

        WO-V9.0: Mutated entries are highlighted with [MUTATED] prefix.
        """
        lines = []
        section_labels = {
            "geography": "Geography",
            "religion": "Religion",
            "arts": "Arts",
            "politics": "Politics",
            "economics": "Economics",
            "social": "Social",
            "language": "Language",
            "culture": "Culture",
            "architecture": "Architecture & Fashion",
        }

        for key, label in section_labels.items():
            entries = grapes_dict.get(key, [])
            lines.append(f"[bold cyan]{label}[/bold cyan]")
            if isinstance(entries, str):
                lines.append(f"  {entries}")
            elif isinstance(entries, list):
                for entry in entries:
                    mutated = self._is_mutated_entry(key, entry)
                    prefix = "[bold green][MUTATED][/] " if mutated else ""
                    if isinstance(entry, dict):
                        summary = " | ".join(f"{v}" for v in entry.values())
                        lines.append(f"  - {prefix}{summary}")
                    else:
                        lines.append(f"  - {prefix}{entry}")
            else:
                lines.append("  [dim]No data[/dim]")
            lines.append("")

        # WO-V9.0: Recent Changes footer from WorldLedger
        if self._world_ledger:
            try:
                changelog = self._world_ledger.get_changelog()
                if changelog:
                    lines.append("[bold yellow]Recent Changes[/bold yellow]")
                    for entry in changelog[-5:]:
                        action = entry.get("action", "?")
                        detail = entry.get("detail", "?")
                        lines.append(f"  [{action}] {detail}")
                    lines.append("")
            except Exception:
                pass

        return Panel("\n".join(lines), title="[bold]G.R.A.P.E.S. Profile[/bold]", border_style="gold1")

    def _exit_special_view(self):
        """Return from graveyard, seed vault, atlas, chronology, or PDF to normal index."""
        self._grave_view = False
        self._seed_view = False
        self._atlas_view = False
        self._chrono_view = False
        self._chrono_filter = None
        self._chrono_events = []
        self._selected_grave = None
        self._selected_seed = None
        self._atlas_profile = None
        self._atlas_worlds = {}
        self._grave_map = {}
        self._seed_map = {}
        self._close_pdf()

    def _resolve_system_id(self, book_key: Optional[str]) -> Optional[str]:
        """Map a vault book key to a RAG Service system ID."""
        if not book_key:
            return None
        from codex.core.services.rag_service import RAGService
        key = book_key.lower().replace(" ", "_")
        if key in RAGService.SYSTEM_ALIASES:
            return key
        # Try without family prefix (e.g. "FITD/bitd" -> "bitd")
        if "/" in key:
            key = key.rsplit("/", 1)[-1]
            if key in RAGService.SYSTEM_ALIASES:
                return key
        return None

    def query_mimir(self, question: str) -> str:
        """Query Mimir restricted to the current book namespace.

        WO V20.5.4: cache-first — checks LoreCache before calling Ollama.
        WO-V33.0: RAG-enriched — FAISS chunks injected as context.
        Results are grit-scrubbed before caching.
        """
        namespace = self._current_book or "general"
        cache_key = question.strip().lower()

        # Cache check (instant)
        if self._cache:
            cached = self._cache.get(namespace, cache_key)
            if cached:
                self._query_history.append(
                    f"Q: {question}\nA: {cached}\n[cached]"
                )
                return cached

        # WO-V33.0 + V139: RAG enrichment with citations
        rag_context = ""
        try:
            from codex.core.services.rag_service import get_rag_service
            rag = get_rag_service()
            system_id = self._resolve_system_id(namespace)
            if system_id:
                result = rag.search_rich(question, system_id, k=3, token_budget=800)
                if result:
                    rag_context = rag.format_context(result, header="SOURCE MATERIAL:")
        except Exception:
            pass

        # Mimir query (slow — Ollama inference)
        if not self._mimir:
            return "[Mimir offline - no AI model available]"
        try:
            context = f"Namespace: {namespace}."
            if rag_context:
                context = f"{rag_context}\n\n{context}"
            result = self._mimir(question, context)

            # Grit scrub before caching
            from codex.core.cache import grit_scrub
            result = grit_scrub(result)

            # Store in cache
            if self._cache:
                self._cache.put(namespace, cache_key, result)

            self._query_history.append(f"Q: {question}\nA: {result}")
            return result
        except Exception as e:
            return f"[Mimir error: {e}]"

    def query_laws(self) -> str:
        """AMD-05: Quick Reference: Laws for Code Legal shards."""
        return self.query_mimir(
            "Summarize the Code Legal of Waterdeep. "
            "List the key laws and punishments concisely."
        )

    # ------------------------------------------------------------------
    # Seed archiving (static -- callable without a TUI instance)
    # ------------------------------------------------------------------

    @staticmethod
    def archive_seed(seed_data: dict):
        """Archive a dungeon seed to the seed ledger.

        Args:
            seed_data: Dict with ``seed_value``, ``dungeon_type``,
                ``level_number``.  Timestamp is added automatically.
        """
        from codex.paths import VAULT_MAPS_DIR
        VAULT_MAPS_DIR.mkdir(parents=True, exist_ok=True)
        ledger_path = VAULT_MAPS_DIR / "seed_ledger.json"

        if ledger_path.exists():
            try:
                ledger = json.loads(ledger_path.read_text())
            except (json.JSONDecodeError, KeyError):
                ledger = {"version": "1.0", "seeds": []}
        else:
            ledger = {"version": "1.0", "seeds": []}

        if "timestamp" not in seed_data:
            seed_data["timestamp"] = datetime.now().isoformat(
                timespec="seconds"
            )
        seed_data.setdefault(
            "id", f"seed_{seed_data.get('seed_value', 0)}"
        )

        ledger["seeds"].append(seed_data)

        # Atomic write
        fd, tmp = tempfile.mkstemp(
            dir=str(VAULT_MAPS_DIR), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(ledger, f, indent=2)
            os.replace(tmp, str(ledger_path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> Layout:
        """Render the three-panel layout."""
        layout = Layout()
        layout.split_row(
            Layout(self._render_index(), name="index", ratio=2),
            Layout(self._render_text(), name="text", ratio=5),
            Layout(self._render_query(), name="query", ratio=3),
        )
        return layout

    def _render_index(self) -> Panel:
        """Left panel: tree-grouped tome index + special vaults."""
        tree = Tree("", guide_style="dim cyan")

        for family_label, entries in self._groups:
            if family_label:
                branch = tree.add(
                    f"[bold yellow]{family_label}[/bold yellow]"
                )
            else:
                branch = tree
            for num, book_key in entries:
                if book_key == self._current_book:
                    marker = "[bold green]>[/bold green]"
                else:
                    marker = " "
                name = _friendly_name(book_key)
                count = len(self._index.get(book_key, []))
                # WO-V9.5: Content-type tag annotation
                tags = self._content_tags.get(book_key, [])
                tag_str = f" [dim]{','.join(tags)}[/dim]" if tags else ""
                branch.add(
                    f"{marker} [bold white]\\[{num}][/bold white] "
                    f"{name} ({count}){tag_str}"
                )

        # Seed Vault node
        seed_count = len(self._load_seed_data())
        seed_marker = (
            "[bold green]>[/bold green]" if self._seed_view else " "
        )
        tree.add(
            f"{seed_marker} [bold #d4a574]Seed Vault[/bold #d4a574]"
            f" [dim]({seed_count})[/dim]"
        )

        # Hall of Heroes node
        grave_data = self._load_graveyard_data()
        grave_count = sum(len(v) for v in grave_data.values())
        grave_marker = (
            "[bold green]>[/bold green]" if self._grave_view else " "
        )
        tree.add(
            f"{grave_marker} [bold #8b0000]Hall of Heroes[/bold #8b0000]"
            f" [dim]({grave_count} fallen)[/dim]"
        )

        # WO-V11.2: Chronology node
        chrono_marker = (
            "[bold green]>[/bold green]" if self._chrono_view else " "
        )
        tree.add(
            f"{chrono_marker} [bold dark_goldenrod]Chronology[/bold dark_goldenrod]"
        )

        return Panel(tree, title="[bold]Tome Index[/bold]", border_style="cyan")

    def _render_pdf(self) -> Panel:
        """Center panel: dedicated PDF reader with page footer."""
        content = self._current_text or "(No text)"
        chapter = self._current_chapter or "PDF"
        title = f"[bold]{chapter}[/bold]"
        footer = (
            f"[dim]Page {self._pdf_page + 1} of {self._pdf_total_pages} "
            f"| 'n' next | 'p' prev | 'b' back to Vault[/dim]"
        )
        return Panel(
            content, title=title, subtitle=footer, border_style="white",
        )

    def _render_text(self) -> Panel:
        """Center panel: context-sensitive content display."""
        # --- PDF reader mode ---
        if self._pdf_mode:
            return self._render_pdf()
        # --- Chronology view ---
        if self._chrono_view:
            return self._render_chronology()
        # --- Atlas view ---
        if self._atlas_view:
            if self._atlas_profile:
                return self._render_atlas_detail(self._atlas_profile)
            return self._render_atlas_index()
        # --- Graveyard view ---
        if self._grave_view:
            return self._render_graveyard()
        # --- Seed Vault view ---
        if self._seed_view:
            return self._render_seeds()
        # --- Map toggle view ---
        if self._map_view and self._current_book:
            return self._render_maps()
        # --- Normal tome/chapter view ---
        if not self._current_book:
            content = "[dim]Select a tome from the index...[/dim]"
            title = "[bold]The Open Page[/bold]"
        elif self._current_chapter:
            content = self._current_text
            title = (
                f"[bold]{_friendly_name(self._current_book)} "
                f"/ {self._current_chapter}[/bold]"
            )
        else:
            lines: List[str] = []
            for num, chapter in self._chapter_map.items():
                lines.append(
                    f"  [bold white]\\[{num}][/bold white] {chapter}"
                )
            content = "\n".join(lines) if lines else "[dim]Empty tome.[/dim]"
            map_hint = "  [M] Maps" if self._current_book else ""
            title = (
                f"[bold]{_friendly_name(self._current_book)}[/bold]"
                f"{map_hint}"
            )

        subtitle = None
        if self._butler and getattr(self._butler, '_narrating', False):
            subtitle = "[dim italic]Mimir is Narrating...[/]"
        return Panel(content, title=title, subtitle=subtitle, border_style="white")

    def _render_graveyard(self) -> Panel:
        """Center panel: Memorial Hall with graveyard theme."""
        if self._selected_grave:
            # Detail view for a single tombstone
            e = self._selected_grave
            lines = [
                f"[bold]{e.get('name', 'Unknown')}[/bold]",
                "",
                f'[italic]"{e.get("elegy", "Rest now.")}"[/italic]',
                "",
            ]
            if e.get("cause"):
                lines.append(f"Cause: {e['cause']}")
            stats = []
            for k in ("hp_max", "might", "wits", "grit", "aether"):
                if e.get(k) is not None:
                    stats.append(f"{k.upper()}: {e[k]}")
            if stats:
                lines.append("  ".join(stats))
            if e.get("doom") is not None:
                lines.append(f"Doom: {e['doom']}  Turns: {e.get('turns', '?')}")
            if e.get("seed") is not None:
                lines.append(f"Seed: {e['seed']}  (replayable)")
            if e.get("timestamp"):
                lines.append(f"[dim]{e['timestamp']}[/dim]")
            content = "\n".join(lines)
            title = f"[bold]Tombstone: {e.get('name', '?')}[/bold]"
        elif self._grave_map:
            # List all fallen, numbered
            lines = []
            current_sys = None
            for num, entry in self._grave_map.items():
                sid = entry.get("system_id", "unknown")
                if sid != current_sys:
                    current_sys = sid
                    lines.append(
                        f"\n[bold #8b0000]{_friendly_name(sid)}[/bold #8b0000]"
                    )
                cause = entry.get("cause", "")
                cause_short = (cause[:40] + "...") if len(cause) > 40 else cause
                lines.append(
                    f"  [bold white]\\[{num}][/bold white] "
                    f"{entry.get('name', '?')} "
                    f"[dim]-- {cause_short}[/dim]"
                )
            content = "\n".join(lines) if lines else (
                "[dim]No fallen heroes yet. "
                "The chronicles are young.[/dim]"
            )
            title = "[bold]Hall of Heroes[/bold]"
        else:
            content = (
                "[dim]No fallen heroes yet. "
                "The chronicles are young.[/dim]"
            )
            title = "[bold]Hall of Heroes[/bold]"

        subtitle = None
        if self._butler and getattr(self._butler, '_narrating', False):
            subtitle = "[dim italic]Mimir is Narrating...[/]"
        return Panel(content, title=title, subtitle=subtitle, border_style="#8b0000")

    def _render_seeds(self) -> Panel:
        """Center panel: Seed Vault display."""
        if self._selected_seed:
            s = self._selected_seed
            lines = [
                f"[bold]Seed: {s.get('seed_value', '?')}[/bold]",
                "",
                f"Type: {s.get('dungeon_type', 'standard')}",
                f"Depth: {s.get('level_number', '?')}",
            ]
            if s.get("total_rooms"):
                lines.append(f"Rooms: {s['total_rooms']}")
            if s.get("start_room") is not None:
                lines.append(f"Start: Room {s['start_room']}")
            if s.get("system_id"):
                lines.append(f"System: {_friendly_name(s['system_id'])}")
            if s.get("timestamp"):
                lines.append(f"[dim]{s['timestamp']}[/dim]")
            lines.append("")
            lines.append("[dim]Use this seed value to replay the dungeon.[/dim]")
            content = "\n".join(lines)
            title = f"[bold]Seed {s.get('seed_value', '?')}[/bold]"
        elif self._seed_map:
            lines = []
            for num, seed in self._seed_map.items():
                sid = seed.get("system_id", "")
                sys_tag = f" ({_friendly_name(sid)})" if sid else ""
                lines.append(
                    f"  [bold white]\\[{num}][/bold white] "
                    f"Seed {seed.get('seed_value', '?')}"
                    f"{sys_tag} "
                    f"[dim]{seed.get('timestamp', '')}[/dim]"
                )
            content = "\n".join(lines)
            title = "[bold]Seed Vault[/bold]"
        else:
            content = "[dim]No seeds archived yet.[/dim]"
            title = "[bold]Seed Vault[/bold]"

        return Panel(content, title=title, border_style="#d4a574")

    def _render_maps(self) -> Panel:
        """Center panel: Map files for the active tome."""
        from codex.paths import VAULT_MAPS_DIR
        book_key = self._current_book
        map_dir = VAULT_MAPS_DIR / book_key if book_key else None

        lines: List[str] = []
        if map_dir and map_dir.is_dir():
            image_suffixes = {".png", ".jpg", ".jpeg", ".svg", ".txt"}
            for f in sorted(map_dir.rglob("*")):
                if f.is_file() and f.suffix.lower() in image_suffixes:
                    rel = f.relative_to(map_dir)
                    lines.append(f"  {rel}")
            # Also check for survey data
            survey = map_dir / "survey.json"
            if survey.exists():
                try:
                    data = json.loads(survey.read_text())
                    loc_count = data.get("location_count", 0)
                    lines.append(
                        f"\n[dim]Survey: {loc_count} locations mined[/dim]"
                    )
                except (json.JSONDecodeError, KeyError):
                    pass

        if lines:
            content = "\n".join(lines)
        else:
            content = (
                "[dim]No maps available for this tome.\n"
                "Run the Surveyor to generate map data.[/dim]"
            )

        title = (
            f"[bold]{_friendly_name(book_key or '')} "
            f"-- Maps[/bold]"
        )
        return Panel(content, title=title, border_style="green")

    def _render_query(self) -> Panel:
        """Right panel: Mimir Q&A."""
        if self._query_history:
            display = "\n---\n".join(self._query_history[-3:])
        else:
            display = "[dim]Ask Mimir a question about the current tome.[/dim]"

        return Panel(display, title="[bold]Consult Mimir[/bold]", border_style="yellow")

    # ------------------------------------------------------------------
    # Interactive loop
    # ------------------------------------------------------------------

    def _splash_text(self) -> str:
        """Return branded splash text for the session header."""
        default_quote = "I am the memory that outlasts any single chronicle."
        if self._system_id is None:
            quote = default_quote
            return (
                "[bold cyan]MIMIR'S VAULT[/bold cyan]\n"
                "[dim]The Collected Lore of Every Chronicle[/dim]\n\n"
                f'[italic]"{quote}"[/italic]'
            )
        sid = self._system_id.lower()
        quote = self._system_quotes.get(sid, default_quote)
        return (
            "[bold cyan]MIMIR'S VAULT[/bold cyan]\n"
            f"[dim]Restricted Folio -- {self._chronicle_name}[/dim]\n\n"
            f'[italic]"{quote}"[/italic]'
        )

    def _help_text(self) -> str:
        """Return the command reference string."""
        return (
            "[dim]Commands: <number> | open <tome> | ask <question> "
            "| list | back | [M] maps | grave | seeds | atlas | chrono | laws | carto | tutorial | quit\n"
            "PDF: n (next) | p (prev) | page <N> | b (back to vault)[/dim]"
        )

    def run_loop(self, console: Optional[Console] = None):
        """Interactive loop for terminal use."""
        con = console or Console()

        con.print()
        con.print(Panel(self._splash_text(), border_style="cyan", box=box.DOUBLE))
        con.print(self._help_text())
        con.print()

        while True:
            con.print(self.render())

            # Dynamic prompt
            if self._pdf_mode:
                prompt = (
                    f"[bold]vault [Page {self._pdf_page + 1}"
                    f"/{self._pdf_total_pages}]> [/bold]"
                )
            elif self._chrono_view:
                prompt = "[bold dark_goldenrod]vault [Chronology]> [/bold dark_goldenrod]"
            elif self._atlas_view:
                prompt = "[bold gold1]vault [Atlas]> [/bold gold1]"
            elif self._grave_view:
                prompt = "[bold #8b0000]vault [Memorial]> [/bold #8b0000]"
            elif self._seed_view:
                prompt = "[bold #d4a574]vault [Seeds]> [/bold #d4a574]"
            elif self._current_book:
                prompt = (
                    f"[bold]vault "
                    f"[{_friendly_name(self._current_book)}]> [/bold]"
                )
            else:
                prompt = "[bold]vault> [/bold]"

            try:
                raw = con.input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not raw:
                continue
            if raw.lower() in ("quit", "exit", "q"):
                break

            # --- Numeric selection (context-sensitive) ---
            if raw.isdigit():
                num = int(raw)
                if self._pdf_mode:
                    # Jump to page N (1-based)
                    if 1 <= num <= self._pdf_total_pages:
                        self._load_pdf_page(num - 1)
                    else:
                        con.print(f"[red]Page {num} out of range (1-{self._pdf_total_pages})[/red]")
                elif self._atlas_view:
                    if self._atlas_profile:
                        con.print("[dim]Type 'back' to return to the atlas index.[/dim]")
                    elif num in self._atlas_worlds:
                        self._atlas_profile = self._atlas_worlds[num].get("grapes", {})
                    else:
                        con.print(f"[red]No world at index {num}[/red]")
                elif self._grave_view:
                    if self._selected_grave:
                        # Already viewing a tombstone -- number is no-op
                        con.print("[dim]Type 'back' to return to the list.[/dim]")
                    elif num in self._grave_map:
                        self._selected_grave = self._grave_map[num]
                    else:
                        con.print(f"[red]No entry at index {num}[/red]")
                elif self._seed_view:
                    if self._selected_seed:
                        con.print("[dim]Type 'back' to return to the list.[/dim]")
                    elif num in self._seed_map:
                        self._selected_seed = self._seed_map[num]
                    else:
                        con.print(f"[red]No seed at index {num}[/red]")
                elif self._current_book:
                    if self._current_chapter and self._file_map:
                        # Inside a chapter directory — select a file
                        if num in self._file_map:
                            fp = self._file_map[num]
                            if fp.suffix.lower() == ".pdf":
                                self._open_pdf(fp)
                            else:
                                con.print(
                                    f"[dim]{fp.name} — not a readable format[/dim]"
                                )
                        else:
                            con.print(f"[red]No file at index {num}[/red]")
                    elif num in self._chapter_map:
                        self.select_chapter(self._chapter_map[num])
                    else:
                        con.print(f"[red]No chapter at index {num}[/red]")
                else:
                    if num in self._vault_map:
                        self.open_book(self._vault_map[num])
                    else:
                        con.print(f"[red]No tome at index {num}[/red]")
                continue

            parts = raw.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "open" and arg:
                self._exit_special_view()
                if arg.lower().startswith("seed"):
                    # "open seed <id>" -- enter seed vault
                    seed_arg = arg.split(None, 1)
                    if len(seed_arg) > 1:
                        self.enter_seed_vault()
                        # Try to select by seed value
                        try:
                            sv = int(seed_arg[1])
                            for entry in self._seed_entries:
                                if entry.get("seed_value") == sv:
                                    self._selected_seed = entry
                                    break
                        except ValueError:
                            pass
                    else:
                        self.enter_seed_vault()
                elif arg.isdigit():
                    num = int(arg)
                    if num in self._vault_map:
                        self.open_book(self._vault_map[num])
                    else:
                        con.print(f"[red]No tome at index {num}[/red]")
                elif not self.open_book(arg):
                    con.print(f"[red]Tome not found: {arg}[/red]")

            elif cmd in ("back", "b"):
                if self._pdf_mode:
                    # PDF reader -> back one level
                    self._close_pdf()
                    if self._file_map and self._current_chapter:
                        # Opened from within a directory — re-render it
                        self.select_chapter(self._current_chapter)
                    else:
                        # Opened as a direct chapter — return to chapter list
                        self._current_chapter = None
                        self._current_text = ""
                elif self._chrono_view:
                    self._exit_special_view()
                elif self._atlas_view and self._atlas_profile:
                    self._atlas_profile = None
                elif self._atlas_view:
                    self._exit_special_view()
                elif self._selected_grave:
                    self._selected_grave = None
                elif self._selected_seed:
                    self._selected_seed = None
                elif self._grave_view or self._seed_view:
                    self._exit_special_view()
                elif self._map_view:
                    self._map_view = False
                elif self._current_chapter:
                    self._current_chapter = None
                    self._current_text = ""
                    self._file_map = {}
                elif self._current_book:
                    self.close_book()

            elif cmd in ("m", "maps"):
                if self._current_book:
                    self._map_view = not self._map_view
                else:
                    con.print("[dim]Open a tome first to view its maps.[/dim]")

            elif cmd in ("grave", "memorial", "graveyard"):
                self.enter_graveyard()

            elif cmd in ("atlas", "world", "worlds"):
                self.enter_atlas()

            elif cmd in ("chrono", "chronology", "timeline"):
                self.enter_chronology()

            elif self._chrono_view and cmd in (
                "war", "discovery", "mutation", "political",
                "economic", "social", "civic", "faction", "all",
            ):
                self._chrono_filter = None if cmd == "all" else cmd
                # Re-filter is handled at render time

            elif cmd in ("seeds", "seed"):
                if arg:
                    # "seed <value>" -- try to open specific seed
                    self.enter_seed_vault()
                    try:
                        sv = int(arg)
                        for entry in self._seed_entries:
                            if entry.get("seed_value") == sv:
                                self._selected_seed = entry
                                break
                    except ValueError:
                        pass
                else:
                    self.enter_seed_vault()

            elif cmd == "n" and self._pdf_mode:
                # Next page
                if self._pdf_page + 1 < self._pdf_total_pages:
                    self._load_pdf_page(self._pdf_page + 1)
                else:
                    con.print("[dim]Already on the last page.[/dim]")

            elif cmd == "p" and self._pdf_mode:
                # Previous page
                if self._pdf_page > 0:
                    self._load_pdf_page(self._pdf_page - 1)
                else:
                    con.print("[dim]Already on the first page.[/dim]")

            elif cmd == "page" and arg:
                if self._pdf_mode:
                    try:
                        page_num = int(arg) - 1  # User uses 1-based
                        if 0 <= page_num < self._pdf_total_pages:
                            self._load_pdf_page(page_num)
                        else:
                            con.print(f"[red]Page {arg} out of range (1-{self._pdf_total_pages})[/red]")
                    except ValueError:
                        con.print("[red]Usage: page <number>[/red]")
                else:
                    con.print("[dim]No PDF currently open. Select a PDF chapter first.[/dim]")

            elif cmd == "ask" and arg:
                self.query_mimir(arg)

            elif cmd == "laws":
                self.query_laws()

            elif cmd in ("cartography", "carto"):
                if _CARTOGRAPHY_AVAILABLE:
                    maps_data = list_maps()
                    if maps_data:
                        lines = ["[bold]Available Maps[/bold]", ""]
                        for system, files in maps_data.items():
                            lines.append(
                                f"[bold cyan]{_friendly_name(system)}[/bold cyan]"
                            )
                            for f in files[:10]:
                                lines.append(f"  {f}")
                            if len(files) > 10:
                                lines.append(
                                    f"  [dim]...and {len(files) - 10} more[/dim]"
                                )
                            lines.append("")
                        con.print(
                            Panel(
                                "\n".join(lines),
                                title="[bold]Cartography[/bold]",
                                border_style="green",
                            )
                        )
                    else:
                        con.print("[dim]No maps available. Run a dungeon to generate some.[/dim]")
                else:
                    con.print("[dim]Cartography service not available.[/dim]")

            elif cmd in ("tutorial", "tut"):
                try:
                    from codex.core.services.tutorial import TutorialBrowser, PlatformTutorial
                    import codex.core.services.tutorial_content  # noqa: F401
                    browser = TutorialBrowser(
                        tutorial=PlatformTutorial(),
                        system_filter=self._system_id,
                    )
                    browser.run_loop(con)
                except Exception as e:
                    con.print(f"[yellow]Tutorial unavailable: {e}[/yellow]")

            elif cmd == "list":
                for family_label, entries in self._groups:
                    if family_label:
                        con.print(
                            f"  [bold yellow]{family_label}[/bold yellow]"
                        )
                    for num, book_key in entries:
                        con.print(
                            f"    [{num}] {_friendly_name(book_key)}"
                        )

            else:
                con.print(self._help_text())

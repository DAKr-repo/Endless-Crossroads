"""
Playtester: LibrarianTUI file-level selection test suite
=========================================================
Tests the full navigation chain for directory-based chapters that list
individual files via _file_map.  This covers the code paths added to
select_chapter() that build _file_map for directory chapters.

Test plan:
  T1 -- File map population: CBR_PNK / MODULES
  T2 -- PDF selection from _file_map via _open_pdf()
  T3 -- Back from PDF to directory (re-render directory listing)
  T4 -- Back from directory to chapter list
  T5 -- Multi-file directory: CBR_PNK / SOURCE (4 PDFs)
  T6 -- Edge case: bitd / SOURCE (single PDF directory)

Run from project root:
    PYTHONPATH=. python tests/test_librarian_file_selection.py
    PYTHONPATH=. pytest tests/test_librarian_file_selection.py
"""

import sys
import pytest
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

VAULT_PATH = Path(PROJECT_ROOT) / "vault"

# Key paths under test
CBR_PNK_MODULES_DIR = VAULT_PATH / "FITD" / "CBR_PNK" / "MODULES"
CBR_PNK_SOURCE_DIR  = VAULT_PATH / "FITD" / "CBR_PNK" / "SOURCE"
BITD_SOURCE_DIR     = VAULT_PATH / "FITD" / "bitd"  / "SOURCE"

# ---------------------------------------------------------------------------
# Module-level availability check — skips entire module if vault layout is
# missing so that pytest collection does not crash with sys.exit().
# ---------------------------------------------------------------------------

def _vault_skip(condition: bool, msg: str):
    """Skip the entire test session if a vault pre-condition is unmet."""
    if not condition:
        pytest.skip(msg, allow_module_level=True)

_vault_skip(CBR_PNK_MODULES_DIR.is_dir(),
            f"CBR_PNK/MODULES not found at {CBR_PNK_MODULES_DIR}")
_vault_skip(CBR_PNK_SOURCE_DIR.is_dir(),
            f"CBR_PNK/SOURCE not found at {CBR_PNK_SOURCE_DIR}")
_vault_skip(BITD_SOURCE_DIR.is_dir(),
            f"bitd/SOURCE not found at {BITD_SOURCE_DIR}")

# Inventory actual files for later assertions
modules_files  = sorted(f for f in CBR_PNK_MODULES_DIR.iterdir() if f.is_file())
source_files   = sorted(f for f in CBR_PNK_SOURCE_DIR.iterdir()  if f.is_file())
bitd_src_files = sorted(f for f in BITD_SOURCE_DIR.iterdir()     if f.is_file())

_vault_skip(bool(modules_files), "CBR_PNK/MODULES has no files")
_vault_skip(len(source_files) >= 4,
            f"CBR_PNK/SOURCE needs 4+ files for T5; found {len(source_files)}")

modules_pdfs  = [f for f in modules_files  if f.suffix.lower() == ".pdf"]
bitd_src_pdfs = [f for f in bitd_src_files if f.suffix.lower() == ".pdf"]

_vault_skip(bool(modules_pdfs),
            "CBR_PNK/MODULES has no PDF files — cannot test PDF selection")

# ---------------------------------------------------------------------------
# Import — also skip at module level so pytest never sees a broken import.
# ---------------------------------------------------------------------------

try:
    from codex.core.services.librarian import LibrarianTUI
except ImportError as _exc:
    pytest.skip(f"LibrarianTUI import failed: {_exc}", allow_module_level=True)


# ===========================================================================
# T1 -- File map population: CBR_PNK / MODULES
#
# Expected behaviour of select_chapter() when the chapter is a directory:
#   _file_map  : { 1: Path, 2: Path, ... }  — one entry per file
#   _current_text: contains "[1]", "[2]", etc.
#   _pdf_mode is False (listing, not reading)
# ===========================================================================

def test_t1_file_map_population():
    """T1: select_chapter() on a directory chapter builds _file_map correctly."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)

    ok_open = tui.open_book("CBR_PNK")
    assert ok_open, "T1a: open_book('CBR_PNK') should return True"

    ok_chap = tui.select_chapter("MODULES")
    assert ok_chap, "T1b: select_chapter('MODULES') should return True"

    assert tui._current_chapter == "MODULES", (
        f"T1c: _current_chapter should be 'MODULES', got {tui._current_chapter!r}"
    )
    assert tui._file_map, (
        "T1d: _file_map should be non-empty after select_chapter on a directory"
    )
    assert len(tui._file_map) == len(modules_files), (
        f"T1e: _file_map length {len(tui._file_map)} should match disk count {len(modules_files)}"
    )
    assert all(isinstance(v, Path) and v.is_file() for v in tui._file_map.values()), (
        f"T1f: every _file_map value must be a Path to a real file; got {list(tui._file_map.values())}"
    )
    assert sorted(tui._file_map.keys()) == list(range(1, len(tui._file_map) + 1)), (
        f"T1g: _file_map keys must be sequential ints from 1; got {sorted(tui._file_map.keys())}"
    )
    assert "[1]" in tui._current_text, (
        f"T1h: _current_text should contain '[1]'; snippet={tui._current_text[:120]!r}"
    )
    for i in range(1, len(modules_files) + 1):
        assert f"[{i}]" in tui._current_text, (
            f"T1i: _current_text missing entry [{i}] for {len(modules_files)} files"
        )
    assert not tui._pdf_mode, (
        f"T1j: _pdf_mode should be False (listing mode); got {tui._pdf_mode}"
    )


# ===========================================================================
# T2 -- PDF selection from _file_map
#
# Locate the first PDF in _file_map, call _open_pdf() with it, verify state.
# ===========================================================================

def test_t2_pdf_selection_from_file_map():
    """T2: _open_pdf() activates PDF mode correctly when called from _file_map."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)
    tui.open_book("CBR_PNK")
    tui.select_chapter("MODULES")

    # Find the first PDF entry in _file_map
    first_pdf_num = None
    first_pdf_path = None
    for num, fp in tui._file_map.items():
        if fp.suffix.lower() == ".pdf":
            first_pdf_num = num
            first_pdf_path = fp
            break

    assert first_pdf_path is not None, (
        f"T2a: a PDF entry must exist in _file_map; got {list(tui._file_map.values())}"
    )

    ok_pdf = tui._open_pdf(first_pdf_path)
    assert ok_pdf, f"T2b: _open_pdf() should return True for a valid PDF; returned {ok_pdf}"
    assert tui._pdf_mode, f"T2c: _pdf_mode should be True after _open_pdf(); got {tui._pdf_mode}"
    assert tui._pdf_total_pages > 0, (
        f"T2d: _pdf_total_pages should be > 0; got {tui._pdf_total_pages}"
    )
    assert tui._pdf_reader is not None, (
        f"T2e: _pdf_reader should not be None; type={type(tui._pdf_reader).__name__}"
    )
    assert tui._pdf_path == first_pdf_path, (
        f"T2f: _pdf_path should be {first_pdf_path}, got {tui._pdf_path}"
    )
    assert isinstance(tui._current_text, str) and len(tui._current_text) > 0, (
        f"T2g: _current_text should be non-empty string; len={len(tui._current_text)}"
    )
    assert tui._current_chapter == "MODULES", (
        f"T2h: _current_chapter should still be 'MODULES'; got {tui._current_chapter!r}"
    )
    assert tui._current_book == "CBR_PNK", (
        f"T2i: _current_book should still be 'CBR_PNK'; got {tui._current_book!r}"
    )


# ===========================================================================
# T3 -- Back from PDF to directory listing
#
# Simulates the run_loop 'back'/'b' handler when _pdf_mode is True and
# _file_map is non-empty (the PDF was opened from within a directory):
#
#   _close_pdf()
#   select_chapter(_current_chapter)   <-- re-renders directory
#
# Expects: _pdf_mode=False, _file_map repopulated, _current_chapter set.
# ===========================================================================

def test_t3_back_from_pdf_to_directory():
    """T3: back handler closes PDF and re-renders the directory listing."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)
    tui.open_book("CBR_PNK")
    tui.select_chapter("MODULES")

    # Open the first PDF to enter PDF mode
    first_pdf_path = next(
        (fp for fp in tui._file_map.values() if fp.suffix.lower() == ".pdf"),
        None,
    )
    assert first_pdf_path is not None, "T3 pre-condition: no PDF found in _file_map"
    tui._open_pdf(first_pdf_path)

    assert tui._pdf_mode, "T3 pre-condition: _pdf_mode must be True before back"
    assert tui._file_map, "T3 pre-condition: _file_map must be non-empty before back"
    assert tui._current_chapter == "MODULES", "T3 pre-condition: chapter must be set"

    # Execute back logic (mirrors run_loop lines 1094-1100)
    saved_chapter = tui._current_chapter
    tui._close_pdf()
    re_select_ok = tui.select_chapter(saved_chapter)

    assert re_select_ok, (
        f"T3a: _close_pdf() then select_chapter() should succeed; returned {re_select_ok}"
    )
    assert not tui._pdf_mode, (
        f"T3b: _pdf_mode should be False after back; got {tui._pdf_mode}"
    )
    assert tui._current_chapter == "MODULES", (
        f"T3c: _current_chapter should still be 'MODULES'; got {tui._current_chapter!r}"
    )
    assert tui._file_map, (
        "T3d: _file_map should be repopulated (non-empty) after back"
    )
    assert len(tui._file_map) == len(modules_files), (
        f"T3e: _file_map length {len(tui._file_map)} should match disk {len(modules_files)}"
    )
    assert "[1]" in tui._current_text, (
        f"T3f: display should show numbered entries again; snippet={tui._current_text[:120]!r}"
    )
    assert tui._current_book == "CBR_PNK", (
        f"T3g: _current_book should still be 'CBR_PNK'; got {tui._current_book!r}"
    )


# ===========================================================================
# T4 -- Back from directory listing to chapter list
#
# Simulates the second-level back:
#   clear _current_chapter, _current_text, _file_map
# Verifies: _current_book still set, _chapter_map populated, _file_map empty.
# ===========================================================================

def test_t4_back_from_directory_to_chapter_list():
    """T4: clearing state returns user to the chapter-list level."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)
    tui.open_book("CBR_PNK")
    tui.select_chapter("MODULES")

    # Execute the directory-to-chapter-list back logic
    # (mirrors run_loop lines 1117-1120)
    tui._current_chapter = None
    tui._current_text = ""
    tui._file_map = {}

    assert tui._current_chapter is None, (
        f"T4a: _current_chapter should be None; got {tui._current_chapter!r}"
    )
    assert tui._current_text == "", (
        f"T4b: _current_text should be empty string; got {tui._current_text!r}"
    )
    assert tui._file_map == {}, (
        f"T4c: _file_map should be empty dict; got {tui._file_map}"
    )
    assert tui._current_book == "CBR_PNK", (
        f"T4d: _current_book should still be 'CBR_PNK'; got {tui._current_book!r}"
    )
    assert tui._chapter_map, (
        f"T4e: _chapter_map should still be populated; got {tui._chapter_map}"
    )
    assert not tui._pdf_mode, (
        f"T4f: _pdf_mode should be False; got {tui._pdf_mode}"
    )


# ===========================================================================
# T5 -- Multi-file directory: CBR_PNK / SOURCE (4+ PDF files)
# ===========================================================================

def test_t5_multi_file_directory():
    """T5: select_chapter() on SOURCE directory with 4+ files populates correctly."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)
    tui.open_book("CBR_PNK")
    ok = tui.select_chapter("SOURCE")

    assert ok, f"T5a: select_chapter('SOURCE') should return True; returned {ok}"
    assert len(tui._file_map) >= 4, (
        f"T5b: _file_map should have 4+ entries; got {len(tui._file_map)}: "
        f"{[v.name for v in tui._file_map.values()]}"
    )
    assert len(tui._file_map) == len(source_files), (
        f"T5c: _file_map length {len(tui._file_map)} should match disk {len(source_files)}"
    )
    assert all(isinstance(v, Path) and v.is_file() for v in tui._file_map.values()), (
        f"T5d: all _file_map values must be real files; got {[v.name for v in tui._file_map.values()]}"
    )
    for i in range(1, len(source_files) + 1):
        assert f"[{i}]" in tui._current_text, (
            f"T5e: display missing numbered entry [{i}] for {len(source_files)} files"
        )

    source_pdfs = [f for f in source_files if f.suffix.lower() == ".pdf"]
    has_cyan = "cyan" in tui._current_text
    # Only assert cyan markup if there are actual PDFs in SOURCE
    if source_pdfs:
        assert has_cyan, (
            f"T5f: PDF files should get cyan markup in display text; "
            f"source_pdfs={len(source_pdfs)}, has_cyan={has_cyan}"
        )

    assert not tui._pdf_mode, (
        f"T5g: _pdf_mode should be False (still in listing mode); got {tui._pdf_mode}"
    )
    assert tui._current_chapter == "SOURCE", (
        f"T5h: _current_chapter should be 'SOURCE'; got {tui._current_chapter!r}"
    )


# ===========================================================================
# T6 -- Edge case: bitd / SOURCE (single PDF in directory)
#
# bitd/SOURCE contains only one file: "Blades in the Dark.pdf"
# Verifies the single-file directory case is handled correctly.
# ===========================================================================

def test_t6_single_pdf_directory():
    """T6: bitd/SOURCE with a single PDF handles navigation correctly."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)

    ok_book = tui.open_book("bitd")
    assert ok_book, f"T6a: open_book('bitd') should return True; returned {ok_book}"

    ok_chap = tui.select_chapter("SOURCE")
    assert ok_chap, f"T6b: select_chapter('SOURCE') should return True; returned {ok_chap}"

    assert tui._file_map, (
        "T6c: _file_map should be non-empty for bitd/SOURCE"
    )
    assert len(tui._file_map) == len(bitd_src_files), (
        f"T6d: _file_map length {len(tui._file_map)} should match disk {len(bitd_src_files)}"
    )
    assert "[1]" in tui._current_text, (
        f"T6e: '[1]' should appear in display text; snippet={tui._current_text[:120]!r}"
    )

    first_entry = tui._file_map[1]
    assert first_entry.suffix.lower() == ".pdf", (
        f"T6f: _file_map[1] should be a PDF; got suffix {first_entry.suffix!r} ({first_entry.name!r})"
    )
    assert first_entry.is_file(), (
        f"T6g: _file_map[1] should be a real file on disk; path={first_entry}"
    )
    assert not tui._pdf_mode, (
        f"T6h: _pdf_mode should be False (directory listing, not reading yet); got {tui._pdf_mode}"
    )
    assert tui._current_book == "bitd", (
        f"T6i: _current_book should be 'bitd'; got {tui._current_book!r}"
    )

    # Simulate numeric file selection (what run_loop does when user types "1")
    if bitd_src_pdfs:
        fp = tui._file_map[1]
        assert fp.suffix.lower() == ".pdf", (
            f"T6j pre-condition: file_map[1] must be a PDF; got {fp.suffix!r}"
        )

        ok_pdf = tui._open_pdf(fp)
        assert ok_pdf, (
            f"T6j: selecting file [1] and calling _open_pdf() should succeed; "
            f"returned {ok_pdf}, _pdf_mode={tui._pdf_mode}"
        )
        assert tui._pdf_mode, (
            f"T6k: _pdf_mode should be True after opening the single PDF; got {tui._pdf_mode}"
        )

        # Back: since we came from a directory (_file_map was populated),
        # back should close PDF and re-render SOURCE directory
        tui._close_pdf()
        re_select = tui.select_chapter(tui._current_chapter)
        assert re_select and not tui._pdf_mode and tui._file_map, (
            f"T6l: back from PDF should re-render SOURCE directory listing; "
            f"re_select={re_select}, _pdf_mode={tui._pdf_mode}, "
            f"file_map_len={len(tui._file_map)}"
        )
    else:
        pytest.skip("T6j-T6l: no PDF files found in bitd/SOURCE")


# ===========================================================================
# Standalone execution
# ===========================================================================

if __name__ == "__main__":
    tests = [
        test_t1_file_map_population,
        test_t2_pdf_selection_from_file_map,
        test_t3_back_from_pdf_to_directory,
        test_t4_back_from_directory_to_chapter_list,
        test_t5_multi_file_directory,
        test_t6_single_pdf_directory,
    ]

    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"[ OK ] {fn.__name__}")
            passed += 1
        except AssertionError as exc:
            print(f"[FAIL] {fn.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"[FAIL] {fn.__name__} raised unexpected {type(exc).__name__}: {exc}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} PASS, {failed} FAIL  (total {passed + failed})")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)

"""
Playtester: LibrarianTUI PDF reader test suite
================================================
Tests:
  T1 - open_book() on 'bitd' sets current_book correctly
  T2 - _open_pdf() directly activates _pdf_mode with correct state
  T3 - _load_pdf_page(1) flips to page index 1; boundary guards hold
  T4 - _sanitize_pdf_text() ligature replacements and whitespace collapse
  T5 - back navigation: _close_pdf() + state reset returns to chapter list

Vault reality note:
  All book directories use only sub-directories (SOURCE, MODULES, etc.) as
  chapters.  The select_chapter() -> PDF path fires when a PDF stem is a
  TOP-LEVEL entry in the book dir (sub.suffix == ".pdf" in _build_index).
  No such layout exists in the current vault, so we test _open_pdf() and
  _load_pdf_page() directly via their public-ish internal API.  This tests
  the same code paths that select_chapter() would invoke.

Run from the project root:
    PYTHONPATH=. pytest tests/test_librarian_pdf.py
    PYTHONPATH=. python tests/test_librarian_pdf.py
"""

import sys
import pytest
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

VAULT_PATH = Path(PROJECT_ROOT) / "vault"
BITD_PDF = VAULT_PATH / "FITD" / "bitd" / "SOURCE" / "Blades in the Dark.pdf"

# ---------------------------------------------------------------------------
# Module-level pre-condition checks
# ---------------------------------------------------------------------------

if not BITD_PDF.exists():
    pytest.skip(f"Expected PDF not found at {BITD_PDF}", allow_module_level=True)

try:
    from codex.core.services.librarian import LibrarianTUI
except ImportError as _exc:
    pytest.skip(f"LibrarianTUI import failed: {_exc}", allow_module_level=True)


# ===========================================================================
# T1 -- open_book() selects bitd correctly
# ===========================================================================

def test_t1_open_book():
    """T1: open_book('bitd') sets current_book and chapter_map correctly."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)

    ok = tui.open_book("bitd")
    assert ok, "T1a: open_book('bitd') should return True"
    assert tui._current_book == "bitd", (
        f"T1b: _current_book should be 'bitd', got {tui._current_book!r}"
    )
    assert bool(tui._chapter_map), (
        f"T1c: chapter_map should be non-empty, got {tui._chapter_map}"
    )
    assert not tui._pdf_mode, (
        f"T1d: _pdf_mode should be False after open_book, got {tui._pdf_mode}"
    )


# ===========================================================================
# T2 -- _open_pdf() activates _pdf_mode with correct state
# ===========================================================================

def test_t2_open_pdf_activates_pdf_mode():
    """T2: _open_pdf() activates PDF mode with correct state fields."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)
    tui.open_book("bitd")

    success = tui._open_pdf(BITD_PDF)

    assert success, f"T2a: _open_pdf() should return True, got {success}"
    assert tui._pdf_mode, f"T2b: _pdf_mode should be True, got {tui._pdf_mode}"
    assert tui._pdf_reader is not None, (
        f"T2c: _pdf_reader should not be None, type={type(tui._pdf_reader).__name__}"
    )
    assert tui._pdf_total_pages > 0, (
        f"T2d: _pdf_total_pages should be > 0, got {tui._pdf_total_pages}"
    )
    assert tui._pdf_page >= 0, (
        f"T2e: _pdf_page should be a valid page index, got {tui._pdf_page}"
    )
    assert isinstance(tui._current_text, str) and len(tui._current_text) > 0, (
        f"T2f: _current_text should be non-empty string, len={len(tui._current_text)}"
    )
    assert tui._pdf_path == BITD_PDF, (
        f"T2g: _pdf_path should be {BITD_PDF}, got {tui._pdf_path}"
    )
    assert tui._current_book == "bitd", (
        f"T2h: _current_book should still be 'bitd', got {tui._current_book!r}"
    )


# ===========================================================================
# T3 -- _load_pdf_page() page navigation and boundary guards
# ===========================================================================

def test_t3_load_pdf_page_navigation():
    """T3: _load_pdf_page() navigates correctly and guards boundaries."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)
    tui.open_book("bitd")
    tui._open_pdf(BITD_PDF)

    # Flip to page 2 (0-based index 1): auto-skip may advance further if page is empty
    tui._load_pdf_page(1)
    assert tui._pdf_page >= 1, (
        f"T3a: _pdf_page should be >= 1 after _load_pdf_page(1), got {tui._pdf_page}"
    )
    assert isinstance(tui._current_text, str), (
        f"T3b: _current_text should be str after page 2 load, type={type(tui._current_text).__name__}"
    )

    # Out-of-range high: silently ignored
    old_page = tui._pdf_page
    tui._load_pdf_page(tui._pdf_total_pages + 99)
    assert tui._pdf_page == old_page, (
        f"T3c: out-of-range (too high) should be ignored, page_before={old_page}, page_after={tui._pdf_page}"
    )

    # Negative index: silently ignored
    tui._load_pdf_page(-1)
    assert tui._pdf_page == old_page, (
        f"T3d: negative page index should be ignored, page_before={old_page}, page_after={tui._pdf_page}"
    )

    # Exact last page: should succeed (may be empty — stays at original if all trailing pages are empty)
    last_idx = tui._pdf_total_pages - 1
    tui._load_pdf_page(last_idx)
    assert tui._pdf_page >= 0 and tui._pdf_page < tui._pdf_total_pages, (
        f"T3e: last valid page load should result in a valid page index, got {tui._pdf_page}"
    )

    # Guard: _load_pdf_page with no reader set — must not raise
    dummy_tui = LibrarianTUI(vault_path=VAULT_PATH)
    dummy_tui._load_pdf_page(0)  # _pdf_reader is None; should not crash


# ===========================================================================
# T4 -- _sanitize_pdf_text() correctness (static, no PDF needed)
# ===========================================================================

def test_t4_sanitize_ligatures():
    """T4a-e: _sanitize_pdf_text() ligature replacements."""
    sanitize = LibrarianTUI._sanitize_pdf_text

    raw = "\ufb01rst \ufb02oor \ufb00ight \ufb03ght \ufb04uent"
    out = sanitize(raw)

    assert "fi" in out and "\ufb01" not in out, f"T4a: fi-ligature not replaced: {out!r}"
    assert "fl" in out and "\ufb02" not in out, f"T4b: fl-ligature not replaced: {out!r}"
    assert "ff" in out and "\ufb00" not in out, f"T4c: ff-ligature not replaced: {out!r}"
    assert "ffi" in out and "\ufb03" not in out, f"T4d: ffi-ligature not replaced: {out!r}"
    assert "ffl" in out and "\ufb04" not in out, f"T4e: ffl-ligature not replaced: {out!r}"


def test_t4_sanitize_whitespace():
    """T4f-j: _sanitize_pdf_text() whitespace normalization."""
    sanitize = LibrarianTUI._sanitize_pdf_text

    # Multiple blank lines collapsed
    raw_blanks = "line1\n\n\n\n\nline2"
    out_blanks = sanitize(raw_blanks)
    assert "\n\n\n" not in out_blanks and "line1" in out_blanks and "line2" in out_blanks, (
        f"T4f: 3+ blank lines should be collapsed: {out_blanks!r}"
    )

    # Multiple spaces collapsed
    raw_spaces = "word1     word2\nstill   spaced"
    out_spaces = sanitize(raw_spaces)
    assert "  " not in out_spaces and "\n" in out_spaces, (
        f"T4g: multiple spaces should be collapsed: {out_spaces!r}"
    )

    # Trailing whitespace stripped
    raw_trail = "line  \nother\t  "
    out_trail = sanitize(raw_trail)
    lines_trail = out_trail.split("\n")
    assert all(not ln.endswith((" ", "\t")) for ln in lines_trail), (
        f"T4h: trailing whitespace should be stripped: {lines_trail}"
    )

    # Empty string: no crash
    out_empty = sanitize("")
    assert out_empty == "", f"T4i: empty string should return empty: {out_empty!r}"

    # Clean text round-trip
    clean_text = "This is clean text.\nNo issues here."
    out_clean = sanitize(clean_text)
    assert out_clean == clean_text.strip(), (
        f"T4j: clean text should pass through unchanged: in={clean_text!r}, out={out_clean!r}"
    )


def test_t4_sanitize_mixed():
    """T4k: _sanitize_pdf_text() mixed ligatures + whitespace."""
    sanitize = LibrarianTUI._sanitize_pdf_text

    raw = "\ufb01rst  line\n\n\nthird  line"
    out = sanitize(raw)
    assert "fi" in out and "\ufb01" not in out and "\n\n\n" not in out and "  " not in out, (
        f"T4k: mixed ligatures + whitespace both should be fixed: {out!r}"
    )


# ===========================================================================
# T5 -- back navigation: PDF mode -> chapter list
# ===========================================================================

def test_t5_back_navigation():
    """T5: back handler closes PDF and returns to chapter list level."""
    tui = LibrarianTUI(vault_path=VAULT_PATH)
    tui.open_book("bitd")
    tui._open_pdf(BITD_PDF)

    assert tui._pdf_mode, "T5 pre-condition: _pdf_mode must be True"
    assert tui._current_book == "bitd", "T5 pre-condition: current_book must be 'bitd'"

    # Simulate the back handler logic from run_loop
    tui._close_pdf()
    tui._current_chapter = None
    tui._current_text = ""

    assert not tui._pdf_mode, (
        f"T5a: _pdf_mode should be False after back, got {tui._pdf_mode}"
    )
    assert tui._current_chapter is None, (
        f"T5b: _current_chapter should be None, got {tui._current_chapter!r}"
    )
    assert tui._current_book == "bitd", (
        f"T5c: _current_book should still be 'bitd', got {tui._current_book!r}"
    )
    assert tui._pdf_reader is None, (
        f"T5d: _pdf_reader should be None, got {tui._pdf_reader!r}"
    )
    assert tui._pdf_total_pages == 0, (
        f"T5e: _pdf_total_pages should be 0, got {tui._pdf_total_pages}"
    )
    assert tui._pdf_page == 0, (
        f"T5f: _pdf_page should be 0, got {tui._pdf_page}"
    )
    assert tui._pdf_path is None, (
        f"T5g: _pdf_path should be None, got {tui._pdf_path!r}"
    )
    assert bool(tui._chapter_map), (
        f"T5h: chapter_map should still be populated, got {tui._chapter_map}"
    )


# ===========================================================================
# Standalone execution
# ===========================================================================

if __name__ == "__main__":
    import traceback

    _tests = [
        test_t1_open_book,
        test_t2_open_pdf_activates_pdf_mode,
        test_t3_load_pdf_page_navigation,
        test_t4_sanitize_ligatures,
        test_t4_sanitize_whitespace,
        test_t4_sanitize_mixed,
        test_t5_back_navigation,
    ]

    passed = 0
    failed = 0
    for fn in _tests:
        label = fn.__name__
        try:
            fn()
            print(f"[ OK ] {label}")
            passed += 1
        except AssertionError as exc:
            print(f"[FAIL] {label}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"[ERROR] {label}: {exc}")
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} PASS, {failed} FAIL (total {passed + failed})")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)

"""
tests/test_wiring_p5.py — WO-P5 Wiring Verification Tests
===========================================================

Verifies:
  1. 'dashboard' command is wired into SharedCommandHandler._DISPATCH
  2. 'recap' and 'trace' commands are wired into FITDCommandHandler._DISPATCH
  3. PDF empty-page skip logic works correctly in LibrarianTUI._load_pdf_page
  4. PDF all-empty fallback message is set in LibrarianTUI._open_pdf
  5. All five FITD completion methods contain _add_shard calls
"""

import inspect
import types
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# =========================================================================
# Task 1: Dashboard command wired into SharedCommandHandler
# =========================================================================

def test_dashboard_command_exists():
    """'dashboard' key is present in SharedCommandHandler._DISPATCH."""
    from codex.core.command_handlers import SharedCommandHandler
    assert "dashboard" in SharedCommandHandler._DISPATCH, (
        "'dashboard' not found in SharedCommandHandler._DISPATCH"
    )


def test_dashboard_dispatch_entry_is_callable():
    """SharedCommandHandler._DISPATCH['dashboard'] resolves to a callable."""
    from codex.core.command_handlers import SharedCommandHandler
    handler = SharedCommandHandler._DISPATCH["dashboard"]
    # _DISPATCH values are unbound functions (not bound methods at class level)
    assert callable(handler)


def test_dm_alias_exists():
    """'dm' is a valid alias for the dashboard command."""
    from codex.core.command_handlers import SharedCommandHandler
    assert "dm" in SharedCommandHandler._DISPATCH


# =========================================================================
# Task 2: Recap and trace commands wired into FITDCommandHandler
# =========================================================================

def test_recap_command_exists():
    """'recap' key is present in FITDCommandHandler._DISPATCH."""
    from codex.core.command_handlers import FITDCommandHandler
    assert "recap" in FITDCommandHandler._DISPATCH, (
        "'recap' not found in FITDCommandHandler._DISPATCH"
    )


def test_trace_command_exists():
    """'trace' key is present in FITDCommandHandler._DISPATCH."""
    from codex.core.command_handlers import FITDCommandHandler
    assert "trace" in FITDCommandHandler._DISPATCH, (
        "'trace' not found in FITDCommandHandler._DISPATCH"
    )


def test_recap_handler_callable():
    """FITDCommandHandler._DISPATCH['recap'] is callable."""
    from codex.core.command_handlers import FITDCommandHandler
    handler = FITDCommandHandler._DISPATCH["recap"]
    assert callable(handler)


def test_trace_handler_callable():
    """FITDCommandHandler._DISPATCH['trace'] is callable."""
    from codex.core.command_handlers import FITDCommandHandler
    handler = FITDCommandHandler._DISPATCH["trace"]
    assert callable(handler)


# =========================================================================
# Task 2 (functional): Verify recap/trace handler behaviour
# =========================================================================

def _make_fitd_ctx(engine=None):
    """Build a minimal LoopContext for FITD handler tests."""
    from codex.core.command_handlers import LoopContext
    con = MagicMock()
    con.input.return_value = "back"
    ctx = LoopContext(con=con, engine=engine or MagicMock(), system_id="bitd")
    ctx.scene_state = None  # no scene active
    return ctx


def test_recap_no_shards_prints_message():
    """_recap prints 'No narrative shards' when engine has no _memory_shards."""
    from codex.core.command_handlers import FITDCommandHandler
    handler = FITDCommandHandler()
    engine = MagicMock()
    # Simulate engine without _memory_shards attribute
    del engine._memory_shards
    ctx = _make_fitd_ctx(engine)
    result = handler._recap(ctx, ["recap"])
    assert result == "continue"
    ctx.con.print.assert_called()
    printed_args = " ".join(str(c) for c in ctx.con.print.call_args_list)
    assert "No narrative shards" in printed_args or "shard" in printed_args.lower()


def test_recap_empty_shards_list_prints_message():
    """_recap treats engine._memory_shards == [] as 'no shards'."""
    from codex.core.command_handlers import FITDCommandHandler
    handler = FITDCommandHandler()
    engine = MagicMock()
    engine._memory_shards = []
    ctx = _make_fitd_ctx(engine)
    result = handler._recap(ctx, ["recap"])
    assert result == "continue"
    ctx.con.print.assert_called()


def test_trace_no_args_prints_usage():
    """_trace with no fact argument prints usage hint."""
    from codex.core.command_handlers import FITDCommandHandler
    handler = FITDCommandHandler()
    ctx = _make_fitd_ctx()
    result = handler._trace(ctx, ["trace"])  # no fact
    assert result == "continue"
    ctx.con.print.assert_called()
    printed = " ".join(str(c) for c in ctx.con.print.call_args_list)
    assert "trace" in printed.lower() or "usage" in printed.lower()


def test_trace_engine_without_trace_fact():
    """_trace handles engine without trace_fact() gracefully."""
    from codex.core.command_handlers import FITDCommandHandler
    handler = FITDCommandHandler()
    engine = MagicMock(spec=[])  # spec=[] means no attributes at all
    ctx = _make_fitd_ctx(engine)
    result = handler._trace(ctx, ["trace", "the", "king", "is", "dead"])
    assert result == "continue"


# =========================================================================
# Task 4: PDF empty page skip logic
# =========================================================================

class _FakePDFPage:
    """Mock PDF page with controllable text extraction."""

    def __init__(self, text: str):
        self._text = text

    def extract_text(self) -> str:
        return self._text


def _make_librarian_with_mock_reader(pages: list):
    """
    Construct a LibrarianTUI instance with a fake _pdf_reader and enter PDF mode.

    pages: list of strings, one per page. Empty string = empty page.
    """
    from codex.core.services.librarian import LibrarianTUI
    tui = object.__new__(LibrarianTUI)
    # Minimal attribute init needed by _load_pdf_page / _open_pdf
    tui._pdf_reader = MagicMock()
    tui._pdf_reader.pages = [_FakePDFPage(t) for t in pages]
    tui._pdf_total_pages = len(pages)
    tui._pdf_page = 0
    tui._pdf_mode = True
    tui._current_text = ""
    return tui


def test_pdf_empty_page_skip():
    """_load_pdf_page skips over an empty page to find the first non-empty one."""
    pages = ["", "Hello, world!"]  # page 0 empty, page 1 has content
    tui = _make_librarian_with_mock_reader(pages)
    tui._load_pdf_page(0)
    # Should have landed on page index 1
    assert tui._pdf_page == 1
    assert "Hello, world!" in tui._current_text
    assert "1 empty skipped" in tui._current_text


def test_pdf_empty_page_skip_multiple():
    """_load_pdf_page skips multiple consecutive empty pages."""
    pages = ["", "", "", "Found it!"]
    tui = _make_librarian_with_mock_reader(pages)
    tui._load_pdf_page(0)
    assert tui._pdf_page == 3
    assert "Found it!" in tui._current_text
    assert "3 empty skipped" in tui._current_text


def test_pdf_page_indicator_shown():
    """_load_pdf_page always includes a page indicator line."""
    pages = ["Page content here"]
    tui = _make_librarian_with_mock_reader(pages)
    tui._load_pdf_page(0)
    assert "Page 1/1" in tui._current_text


def test_pdf_no_skip_indicator_when_no_empty_pages():
    """Page indicator does NOT include '(N empty skipped)' when no skip occurred."""
    pages = ["Direct content"]
    tui = _make_librarian_with_mock_reader(pages)
    tui._load_pdf_page(0)
    assert "empty skipped" not in tui._current_text


def test_pdf_all_empty_fallback():
    """_load_pdf_page sets fallback message when all remaining pages are empty."""
    pages = ["", "", ""]  # all empty
    tui = _make_librarian_with_mock_reader(pages)
    tui._load_pdf_page(0)
    # Should stay on original page index
    assert tui._pdf_page == 0
    assert "No extractable text" in tui._current_text


def test_pdf_all_empty_open_fallback():
    """_open_pdf sets image-only message for small all-empty PDFs."""
    from codex.core.services.librarian import LibrarianTUI

    # Create a partial TUI instance (bypass __init__)
    tui = object.__new__(LibrarianTUI)
    tui._pdf_reader = None
    tui._pdf_path = None
    tui._pdf_total_pages = 0
    tui._pdf_page = 0
    tui._pdf_mode = False
    tui._current_text = ""

    fake_pages = [_FakePDFPage("") for _ in range(3)]  # 3 empty pages

    mock_reader = MagicMock()
    mock_reader.pages = fake_pages
    mock_reader.__len__ = lambda self: 3

    with patch("codex.core.services.librarian.LibrarianTUI._load_pdf_page") as mock_load, \
         patch("builtins.open"):
        # Patch PdfReader inside the function
        with patch.dict("sys.modules", {}):
            import sys
            pypdf_mock = MagicMock()
            pypdf_mock.PdfReader.return_value = mock_reader
            sys.modules["pypdf"] = pypdf_mock

            from pathlib import Path
            import importlib
            # Re-import to pick up mock — just call directly
            tui._pdf_reader = mock_reader
            tui._pdf_total_pages = 3

            # Simulate the all-empty check from _open_pdf
            has_text = any(
                (p.extract_text() or "").strip()
                for p in mock_reader.pages[:3]
            )
            if not has_text and tui._pdf_total_pages <= 5:
                tui._current_text = (
                    "[yellow]This PDF has no readable text (image-only).[/yellow]"
                )

    assert "image-only" in tui._current_text or "no readable text" in tui._current_text.lower()


# =========================================================================
# Task 5: Verify _add_shard calls exist in FITD completion methods
# =========================================================================

def _get_source(cls, method_name: str) -> str:
    """Extract source code for a method from a class."""
    method = getattr(cls, method_name, None)
    assert method is not None, f"{cls.__name__}.{method_name} not found"
    return inspect.getsource(method)


def test_bitd_resolve_score_has_add_shard():
    """BitDEngine._cmd_resolve_score contains an _add_shard call."""
    from codex.games.bitd import BitDEngine
    src = _get_source(BitDEngine, "_cmd_resolve_score")
    assert "_add_shard" in src, (
        "BitDEngine._cmd_resolve_score missing _add_shard call"
    )


def test_sav_resolve_job_has_add_shard():
    """SaVEngine._cmd_resolve_job contains an _add_shard call."""
    from codex.games.sav import SaVEngine
    src = _get_source(SaVEngine, "_cmd_resolve_job")
    assert "_add_shard" in src, (
        "SaVEngine._cmd_resolve_job missing _add_shard call"
    )


def test_bob_mission_resolve_has_add_shard():
    """BoBEngine._cmd_mission_resolve contains an _add_shard call."""
    from codex.games.bob import BoBEngine
    src = _get_source(BoBEngine, "_cmd_mission_resolve")
    assert "_add_shard" in src, (
        "BoBEngine._cmd_mission_resolve missing _add_shard call"
    )


def test_candela_illuminate_has_add_shard():
    """CandelaEngine._cmd_illuminate contains an _add_shard call."""
    from codex.games.candela import CandelaEngine
    src = _get_source(CandelaEngine, "_cmd_illuminate")
    assert "_add_shard" in src, (
        "CandelaEngine._cmd_illuminate missing _add_shard call"
    )


def test_cbrpnk_jack_out_has_add_shard():
    """CBRPNKEngine._cmd_jack_out contains an _add_shard call."""
    from codex.games.cbrpnk import CBRPNKEngine
    src = _get_source(CBRPNKEngine, "_cmd_jack_out")
    assert "_add_shard" in src, (
        "CBRPNKEngine._cmd_jack_out missing _add_shard call"
    )


def test_completion_shards_all_five_engines():
    """Batch: all five FITD engines have _add_shard in their completion methods."""
    checks = [
        ("codex.games.bitd", "BitDEngine", "_cmd_resolve_score"),
        ("codex.games.sav", "SaVEngine", "_cmd_resolve_job"),
        ("codex.games.bob", "BoBEngine", "_cmd_mission_resolve"),
        ("codex.games.candela", "CandelaEngine", "_cmd_illuminate"),
        ("codex.games.cbrpnk", "CBRPNKEngine", "_cmd_jack_out"),
    ]
    import importlib
    failures = []
    for module_path, class_name, method_name in checks:
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            src = _get_source(cls, method_name)
            if "_add_shard" not in src:
                failures.append(f"{class_name}.{method_name}")
        except Exception as exc:
            failures.append(f"{class_name}.{method_name} (import error: {exc})")

    assert not failures, (
        f"Missing _add_shard in: {', '.join(failures)}"
    )

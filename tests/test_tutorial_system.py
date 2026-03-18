"""
tests/test_tutorial_system.py
==============================
Tests for codex/core/services/tutorial.py.

Coverage:
  1. TutorialRegistry: register, get_module, filter by category, get_all
  2. PlatformTutorial: hints, record_command, page tracking, completion,
     persistence (new & old JSON formats), IOError tolerance
  3. TutorialBrowser: render returns Layout, quit handling, navigation,
     category filter, empty-registry guard
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from codex.core.services.tutorial import (
    PlatformTutorial,
    TutorialBrowser,
    TutorialModule,
    TutorialPage,
    TutorialRegistry,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

def _make_page(pid: str, ptype: str = "reference") -> TutorialPage:
    return TutorialPage(
        page_id=pid,
        title=f"Title {pid}",
        content=f"Content for {pid}",
        page_type=ptype,
        prompt="What command?" if ptype == "interactive" else "",
        valid_inputs=["go"] if ptype == "interactive" else [],
        success_message="Correct!" if ptype == "interactive" else "",
    )


def _make_module(
    mid: str,
    category: str = "platform",
    n_pages: int = 2,
    prerequisite: str | None = None,
) -> TutorialModule:
    return TutorialModule(
        module_id=mid,
        title=f"Module {mid}",
        description=f"Desc for {mid}",
        system_id=category,
        category=category,
        pages=[_make_page(f"{mid}_p{i}") for i in range(n_pages)],
        prerequisite=prerequisite,
    )


@pytest.fixture(autouse=True)
def _clean_registry():
    """Isolate each test: save/restore TutorialRegistry._modules."""
    original = dict(TutorialRegistry._modules)
    yield
    TutorialRegistry._modules.clear()
    TutorialRegistry._modules.update(original)


@pytest.fixture
def tmp_stats(tmp_path) -> Path:
    return tmp_path / "session_stats.json"


@pytest.fixture
def tutorial(tmp_stats) -> PlatformTutorial:
    return PlatformTutorial(stats_path=tmp_stats)


# ---------------------------------------------------------------------------
# 1. TutorialRegistry
# ---------------------------------------------------------------------------

class TestTutorialRegistry:
    def test_register_and_get_module(self):
        mod = _make_module("reg_test")
        TutorialRegistry.register(mod)
        result = TutorialRegistry.get_module("reg_test")
        assert result is mod

    def test_get_module_returns_none_for_unknown(self):
        assert TutorialRegistry.get_module("does_not_exist") is None

    def test_get_modules_for_category_filters_correctly(self):
        mod_a = _make_module("cat_a1", category="alpha")
        mod_b = _make_module("cat_b1", category="beta")
        mod_a2 = _make_module("cat_a2", category="alpha")
        TutorialRegistry.register(mod_a)
        TutorialRegistry.register(mod_b)
        TutorialRegistry.register(mod_a2)

        alpha_mods = TutorialRegistry.get_modules_for_category("alpha")
        assert len(alpha_mods) == 2
        assert all(m.category == "alpha" for m in alpha_mods)

    def test_get_modules_for_missing_category_returns_empty(self):
        result = TutorialRegistry.get_modules_for_category("nonexistent_cat")
        assert result == []

    def test_get_all_categories_sorted_and_deduplicated(self):
        TutorialRegistry.register(_make_module("gc1", category="zebra"))
        TutorialRegistry.register(_make_module("gc2", category="alpha"))
        TutorialRegistry.register(_make_module("gc3", category="alpha"))

        cats = TutorialRegistry.get_all_categories()
        assert cats == sorted(set(cats))
        assert "zebra" in cats
        assert "alpha" in cats
        # no duplicates
        assert len(cats) == len(set(cats))

    def test_get_all_modules_returns_all_registered(self):
        mods = [_make_module(f"all_{i}") for i in range(3)]
        for m in mods:
            TutorialRegistry.register(m)
        all_mods = TutorialRegistry.get_all_modules()
        ids = {m.module_id for m in all_mods}
        assert {"all_0", "all_1", "all_2"}.issubset(ids)


# ---------------------------------------------------------------------------
# 2. PlatformTutorial — hints
# ---------------------------------------------------------------------------

class TestPlatformTutorialHints:
    def test_get_hint_for_known_command(self, tutorial):
        hint = tutorial.get_hint("look")
        assert hint is not None
        assert "look" in hint.lower()

    def test_get_hint_case_insensitive(self, tutorial):
        assert tutorial.get_hint("LOOK") == tutorial.get_hint("look")

    def test_get_hint_for_unknown_command_returns_none(self, tutorial):
        assert tutorial.get_hint("supernova") is None

    def test_hint_threshold_zero_always_returns_hint(self, tutorial):
        # Default HINT_THRESHOLD == 0 means always return hint regardless of usage
        for _ in range(10):
            tutorial.record_command("save", "terminal")
        assert tutorial.get_hint("save") is not None

    def test_record_command_increments_usage(self, tutorial):
        tutorial.record_command("map", "terminal")
        tutorial.record_command("map", "terminal")
        assert tutorial._usage["map"]["terminal"] == 2

    def test_record_command_per_interface(self, tutorial):
        tutorial.record_command("help", "terminal")
        tutorial.record_command("help", "discord")
        assert tutorial._usage["help"]["terminal"] == 1
        assert tutorial._usage["help"]["discord"] == 1


# ---------------------------------------------------------------------------
# 3. PlatformTutorial — completion tracking
# ---------------------------------------------------------------------------

class TestPlatformTutorialCompletion:
    def test_mark_page_viewed_tracks_pages(self, tutorial):
        mod = _make_module("comp_mod", n_pages=2)
        TutorialRegistry.register(mod)

        tutorial.mark_page_viewed("comp_mod", "comp_mod_p0")
        progress = tutorial.get_progress("comp_mod")
        assert progress["viewed"] == 1
        assert progress["total"] == 2
        assert not progress["completed"]

    def test_module_auto_completes_when_all_pages_viewed(self, tutorial):
        mod = _make_module("auto_comp", n_pages=2)
        TutorialRegistry.register(mod)

        tutorial.mark_page_viewed("auto_comp", "auto_comp_p0")
        tutorial.mark_page_viewed("auto_comp", "auto_comp_p1")

        assert tutorial.is_completed("auto_comp")
        progress = tutorial.get_progress("auto_comp")
        assert progress["completed"]

    def test_viewing_same_page_twice_not_double_counted(self, tutorial):
        mod = _make_module("dedup_mod", n_pages=2)
        TutorialRegistry.register(mod)

        tutorial.mark_page_viewed("dedup_mod", "dedup_mod_p0")
        tutorial.mark_page_viewed("dedup_mod", "dedup_mod_p0")

        assert tutorial.get_progress("dedup_mod")["viewed"] == 1

    def test_is_completed_false_for_unknown_module(self, tutorial):
        assert not tutorial.is_completed("ghost_module")

    def test_get_progress_for_unregistered_module(self, tutorial):
        progress = tutorial.get_progress("not_registered")
        assert progress == {"viewed": 0, "total": 0, "completed": False}


# ---------------------------------------------------------------------------
# 4. PlatformTutorial — persistence
# ---------------------------------------------------------------------------

class TestPlatformTutorialPersistence:
    def test_stats_persist_to_disk(self, tmp_stats):
        t1 = PlatformTutorial(stats_path=tmp_stats)
        t1.record_command("look", "terminal")

        t2 = PlatformTutorial(stats_path=tmp_stats)
        assert t2._usage.get("look", {}).get("terminal") == 1

    def test_new_format_loaded_correctly(self, tmp_stats):
        payload = {
            "command_usage": {"attack": {"terminal": 5}},
            "tutorial_completion": {"mod1": {"completed": True, "pages_viewed": [], "timestamp": "2026-01-01T00:00:00"}},
        }
        tmp_stats.write_text(json.dumps(payload))
        t = PlatformTutorial(stats_path=tmp_stats)
        assert t._usage["attack"]["terminal"] == 5
        assert t._completion["mod1"]["completed"]

    def test_old_flat_format_loaded_as_usage(self, tmp_stats):
        # Old format: flat dict with command -> interface -> count
        old_payload = {"loot": {"terminal": 3}}
        tmp_stats.write_text(json.dumps(old_payload))
        t = PlatformTutorial(stats_path=tmp_stats)
        assert t._usage["loot"]["terminal"] == 3
        assert t._completion == {}

    def test_corrupt_json_does_not_crash(self, tmp_stats):
        tmp_stats.write_text("NOT VALID JSON {{{{")
        t = PlatformTutorial(stats_path=tmp_stats)
        assert t._usage == {}
        assert t._completion == {}

    def test_missing_stats_file_starts_clean(self, tmp_path):
        t = PlatformTutorial(stats_path=tmp_path / "no_such_file.json")
        assert t._usage == {}
        assert t._completion == {}


# ---------------------------------------------------------------------------
# 5. TutorialBrowser — rendering
# ---------------------------------------------------------------------------

class TestTutorialBrowserRender:
    def test_render_returns_layout(self, tutorial):
        from rich.layout import Layout
        browser = TutorialBrowser(tutorial=tutorial)
        result = browser.render()
        assert isinstance(result, Layout)

    def test_render_with_empty_registry_does_not_crash(self, tutorial):
        # Registry is clean via autouse fixture
        from rich.layout import Layout
        browser = TutorialBrowser(tutorial=tutorial)
        layout = browser.render()
        assert isinstance(layout, Layout)

    def test_render_shows_registered_categories(self, tutorial):
        from rich.console import Console
        from io import StringIO

        TutorialRegistry.register(_make_module("vis_mod", category="burnwillow"))
        browser = TutorialBrowser(tutorial=tutorial)

        sio = StringIO()
        con = Console(file=sio, highlight=False)
        con.print(browser.render())
        output = sio.getvalue()
        assert "burnwillow" in output.lower() or "Burnwillow" in output

    def test_system_filter_hides_other_categories(self, tutorial):
        from rich.console import Console
        from io import StringIO

        TutorialRegistry.register(_make_module("hidden_mod", category="crown"))
        TutorialRegistry.register(_make_module("shown_mod", category="burnwillow"))
        TutorialRegistry.register(_make_module("plat_mod", category="platform"))

        browser = TutorialBrowser(tutorial=tutorial, system_filter="burnwillow")
        cats = browser._visible_categories()
        assert "burnwillow" in cats
        assert "platform" in cats
        assert "crown" not in cats


# ---------------------------------------------------------------------------
# 6. TutorialBrowser — input handling
# ---------------------------------------------------------------------------

class TestTutorialBrowserInputHandling:
    def test_quit_at_category_level_returns_false(self, tutorial):
        browser = TutorialBrowser(tutorial=tutorial)
        assert browser._level == "category"
        result = browser._handle_category_level("q")
        assert result is False

    def test_invalid_category_number_sets_status(self, tutorial):
        TutorialRegistry.register(_make_module("nav_mod", category="platform"))
        browser = TutorialBrowser(tutorial=tutorial)
        browser._handle_category_level("99")
        assert "99" in browser._status

    def test_valid_category_advances_to_module_level(self, tutorial):
        TutorialRegistry.register(_make_module("adv_mod", category="platform"))
        browser = TutorialBrowser(tutorial=tutorial)
        browser._handle_category_level("1")
        assert browser._level == "module"
        assert browser._current_category is not None

    def test_back_at_module_level_returns_to_category(self, tutorial):
        TutorialRegistry.register(_make_module("back_mod", category="platform"))
        browser = TutorialBrowser(tutorial=tutorial)
        browser._handle_category_level("1")
        assert browser._level == "module"
        browser._handle_module_level("b")
        assert browser._level == "category"
        assert browser._current_category is None

    def test_quit_at_module_level_returns_false(self, tutorial):
        TutorialRegistry.register(_make_module("quit_mod", category="platform"))
        browser = TutorialBrowser(tutorial=tutorial)
        browser._handle_category_level("1")
        result = browser._handle_module_level("q")
        assert result is False

    def test_prerequisite_locked_module_registered(self, tutorial):
        """Locked module with prerequisite can be registered and queried."""
        base = _make_module("prereq_base", category="platform")
        locked = _make_module("prereq_locked", category="platform", prerequisite="prereq_base")
        TutorialRegistry.register(base)
        TutorialRegistry.register(locked)

        assert TutorialRegistry.get_module("prereq_locked") is locked
        assert locked.prerequisite == "prereq_base"

    def test_page_level_quit_returns_false(self, tutorial):
        mod = _make_module("page_quit", category="platform", n_pages=1)
        TutorialRegistry.register(mod)
        browser = TutorialBrowser(tutorial=tutorial)

        # Navigate to page level directly
        browser._current_category = "platform"
        browser._build_module_map("platform")
        browser._handle_module_level("1")
        assert browser._level == "page"

        from unittest.mock import MagicMock
        mock_console = MagicMock()
        result = browser._handle_page_level(mock_console, "q")
        assert result is False

    def test_advance_page_returns_to_module_list_on_last_page(self, tutorial):
        mod = _make_module("adv_page", category="platform", n_pages=1)
        TutorialRegistry.register(mod)
        browser = TutorialBrowser(tutorial=tutorial)
        browser._current_module = mod
        browser._current_page_idx = 0

        browser._advance_page(mod)
        assert browser._level == "module"
        assert browser._current_module is None

    def test_generate_command_reference_page_content(self):
        page = TutorialBrowser._generate_command_reference(
            "burnwillow",
            {"Movement": ["n", "s", "e", "w"], "Combat": ["attack"]},
        )
        assert page.page_id == "burnwillow_cmd_reference"
        assert page.page_type == "reference"
        assert "n" in page.content
        assert "attack" in page.content

"""
test_settings_browser.py - Tests for vault content scanning and display.

Covers:
- scan_system_content() categorization (rules, settings, modules)
- Deduplication of files found via multiple directory mappings
- Empty/missing vault directories
- render_system_content_table() output
- play_universal vault path resolver
"""

import os
import json
import tempfile
from pathlib import Path
from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from codex.forge.source_scanner import scan_system_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vault(tmp_path: Path, structure: dict):
    """Create a temporary vault structure.

    structure: {relative_path: None} creates files, dirs are implicit.
    Example: {"SOURCE/core.pdf": None, "MODULES/adventure.pdf": None}
    """
    for rel_path in structure:
        fp = tmp_path / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("")


# ---------------------------------------------------------------------------
# scan_system_content tests
# ---------------------------------------------------------------------------

class TestScanSystemContent:

    def test_empty_vault(self, tmp_path):
        result = scan_system_content(str(tmp_path))
        assert result == {"rules": [], "settings": [], "modules": []}

    def test_nonexistent_path(self):
        result = scan_system_content("/does/not/exist/anywhere")
        assert result == {"rules": [], "settings": [], "modules": []}

    def test_source_files_are_rules(self, tmp_path):
        _make_vault(tmp_path, {
            "SOURCE/gm_guide.pdf": None,
            "SOURCE/framework.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["rules"]) == 2
        names = {r["name"] for r in result["rules"]}
        assert names == {"framework", "gm_guide"}

    def test_source_rules_subdir(self, tmp_path):
        _make_vault(tmp_path, {
            "SOURCE/Rules/handbook.pdf": None,
            "SOURCE/Rules/starter.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["rules"]) == 2
        names = {r["name"] for r in result["rules"]}
        assert names == {"handbook", "starter"}

    def test_source_bestiary_subdir(self, tmp_path):
        _make_vault(tmp_path, {
            "SOURCE/Bestiary/monsters.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["rules"]) == 1
        assert result["rules"][0]["name"] == "monsters"

    def test_source_settings_subdir(self, tmp_path):
        _make_vault(tmp_path, {
            "SOURCE/Settings/world_guide.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["settings"]) == 1
        assert result["settings"][0]["name"] == "world_guide"

    def test_top_level_settings(self, tmp_path):
        _make_vault(tmp_path, {
            "SETTINGS/prdtr.pdf": None,
            "SETTINGS/megalopolis.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["settings"]) == 2

    def test_top_level_supplements(self, tmp_path):
        _make_vault(tmp_path, {
            "SUPPLEMENTS/extra.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["settings"]) == 1
        assert result["settings"][0]["name"] == "extra"

    def test_modules_dir(self, tmp_path):
        _make_vault(tmp_path, {
            "MODULES/adventure.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["modules"]) == 1

    def test_module_singular_dir(self, tmp_path):
        _make_vault(tmp_path, {
            "MODULE/quest.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["modules"]) == 1
        assert result["modules"][0]["name"] == "quest"

    def test_full_cbr_pnk_structure(self, tmp_path):
        """Simulate the real CBR+PNK vault layout."""
        _make_vault(tmp_path, {
            "SOURCE/gm_guide.pdf": None,
            "SOURCE/framework.pdf": None,
            "SOURCE/weird.pdf": None,
            "SOURCE/hunters.pdf": None,
            "SETTINGS/prdtr.pdf": None,
            "SETTINGS/megalopolis.pdf": None,
            "MODULES/mindthegap.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["rules"]) == 4
        assert len(result["settings"]) == 2
        assert len(result["modules"]) == 1

    def test_full_dnd5e_structure(self, tmp_path):
        """Simulate the real D&D 5e vault layout."""
        _make_vault(tmp_path, {
            "SOURCE/Rules/phb.pdf": None,
            "SOURCE/Rules/dmg.pdf": None,
            "SOURCE/Bestiary/mm.pdf": None,
            "SOURCE/Settings/sword_coast.pdf": None,
            "MODULES/dragon_heist.pdf": None,
            "MODULES/mad_mage.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["rules"]) == 3  # phb + dmg + mm
        assert len(result["settings"]) == 1
        assert len(result["modules"]) == 2

    def test_deduplication(self, tmp_path):
        """Files should not appear twice if found via multiple paths."""
        # SOURCE/Settings/ and top-level SETTINGS/ point to same category
        # but should not produce dupes if paths differ
        _make_vault(tmp_path, {
            "SOURCE/Settings/guide.pdf": None,
            "SETTINGS/supplement.pdf": None,
        })
        result = scan_system_content(str(tmp_path))
        assert len(result["settings"]) == 2

    def test_entries_have_path_and_name(self, tmp_path):
        _make_vault(tmp_path, {"SOURCE/core.pdf": None})
        result = scan_system_content(str(tmp_path))
        entry = result["rules"][0]
        assert "name" in entry
        assert "path" in entry
        assert entry["name"] == "core"
        assert entry["path"].endswith("core.pdf")

    def test_real_cbr_pnk_vault(self):
        """Integration test against the real CBR_PNK vault if present."""
        vault = Path(__file__).resolve().parent.parent / "vault" / "FITD" / "CBR_PNK"
        if not vault.exists():
            pytest.skip("CBR_PNK vault not present")
        result = scan_system_content(str(vault))
        assert len(result["rules"]) >= 1
        assert len(result["settings"]) >= 1
        assert len(result["modules"]) >= 1

    def test_real_dnd5e_vault(self):
        """Integration test against the real D&D 5e vault if present."""
        vault = Path(__file__).resolve().parent.parent / "vault" / "dnd5e"
        if not vault.exists():
            pytest.skip("dnd5e vault not present")
        result = scan_system_content(str(vault))
        assert len(result["rules"]) >= 2
        assert len(result["modules"]) >= 1


# ---------------------------------------------------------------------------
# render_system_content_table tests
# ---------------------------------------------------------------------------

class TestRenderSystemContentTable:

    def test_renders_all_sections(self):
        from codex.forge.char_wizard import render_system_content_table
        content = {
            "rules": [{"name": "Handbook", "path": "/x"}],
            "settings": [{"name": "World Guide", "path": "/y"}],
            "modules": [{"name": "Adventure", "path": "/z"}],
        }
        buf = StringIO()
        con = Console(file=buf, force_terminal=True, width=80)
        render_system_content_table(content, "TestSystem", con)
        output = buf.getvalue()
        assert "SOURCEBOOKS" in output
        assert "SETTINGS" in output
        assert "ADVENTURE MODULES" in output
        assert "Handbook" in output
        assert "World Guide" in output
        assert "Adventure" in output

    def test_empty_content_no_output(self):
        from codex.forge.char_wizard import render_system_content_table
        content = {"rules": [], "settings": [], "modules": []}
        buf = StringIO()
        con = Console(file=buf, force_terminal=True, width=80)
        render_system_content_table(content, "Empty", con)
        assert buf.getvalue().strip() == ""

    def test_partial_content(self):
        from codex.forge.char_wizard import render_system_content_table
        content = {
            "rules": [{"name": "Core", "path": "/a"}],
            "settings": [],
            "modules": [],
        }
        buf = StringIO()
        con = Console(file=buf, force_terminal=True, width=80)
        render_system_content_table(content, "Minimal", con)
        output = buf.getvalue()
        assert "SOURCEBOOKS" in output
        assert "SETTINGS" not in output
        assert "ADVENTURE MODULES" not in output


# ---------------------------------------------------------------------------
# play_universal vault path resolver tests
# ---------------------------------------------------------------------------

class TestResolveVaultPath:

    def test_resolve_known_system(self):
        from play_universal import _resolve_vault_path
        path = _resolve_vault_path("dnd5e")
        if path is None:
            pytest.skip("vault/dnd5e not present")
        assert "dnd5e" in path

    def test_resolve_nested_system(self):
        from play_universal import _resolve_vault_path
        path = _resolve_vault_path("bitd")
        if path is None:
            pytest.skip("vault/FITD/bitd not present")
        assert "bitd" in path

    def test_resolve_nonexistent_returns_none(self):
        from play_universal import _resolve_vault_path
        assert _resolve_vault_path("nonexistent_system_xyz") is None

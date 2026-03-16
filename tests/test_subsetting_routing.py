"""
tests/test_subsetting_routing.py — WO-V49.0
=============================================
Tests for:
1. Sub-setting resolution (stc_roshar -> stc + roshar)
2. Module inheritance in source_scanner
3. Setting skip logic in campaign wizard
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================
# Sub-setting Resolution
# =========================================================================

class TestSubsettingResolution:
    """Test _resolve_subsetting() in play_universal.py."""

    def test_stc_roshar_resolves_to_stc(self):
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("stc_roshar")
        assert resolved == "stc"
        assert setting == "roshar"

    def test_dnd5e_unchanged(self):
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("dnd5e")
        assert resolved == "dnd5e"
        assert setting == ""

    def test_bitd_unchanged(self):
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("bitd")
        assert resolved == "bitd"
        assert setting == ""

    def test_stc_base_unchanged(self):
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("stc")
        assert resolved == "stc"
        assert setting == ""

    def test_sav_unchanged(self):
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("sav")
        assert resolved == "sav"
        assert setting == ""

    def test_unknown_system_with_underscore_unchanged(self):
        """If the parent portion isn't a known system, don't split."""
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("custom_world")
        assert resolved == "custom_world"
        assert setting == ""

    def test_stc_multiple_underscores(self):
        """Only split on first underscore: stc_deep_roshar -> stc, deep_roshar."""
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("stc_deep_roshar")
        assert resolved == "stc"
        assert setting == "deep_roshar"

    def test_candela_unchanged(self):
        from play_universal import _resolve_subsetting
        resolved, setting = _resolve_subsetting("candela")
        assert resolved == "candela"
        assert setting == ""


# =========================================================================
# Module Inheritance in source_scanner
# =========================================================================

class TestModuleInheritance:
    """Test scan_system_content with parent_path merging."""

    def _setup_vault(self, tmp_path):
        """Create a parent + child vault structure for testing."""
        parent = tmp_path / "stc"
        parent.mkdir()
        parent_mod = parent / "MODULE"
        parent_mod.mkdir()
        (parent_mod / "adventure_alpha.pdf").write_text("parent mod A")
        (parent_mod / "adventure_beta.pdf").write_text("parent mod B")

        parent_settings = parent / "SETTINGS"
        parent_settings.mkdir()
        (parent_settings / "forgotten_realms.pdf").write_text("parent setting")

        child = parent / "roshar"
        child.mkdir()
        # Child has its own module overlapping one parent name
        child_mod = child / "MODULE"
        child_mod.mkdir()
        (child_mod / "adventure_beta.pdf").write_text("child mod B override")

        return str(child), str(parent)

    def test_child_only_returns_child_content(self):
        from codex.forge.source_scanner import scan_system_content
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            child_path, parent_path = self._setup_vault(tmp_path)
            result = scan_system_content(child_path)
            mod_names = [m["name"] for m in result["modules"]]
            assert "adventure_beta" in mod_names
            assert "adventure_alpha" not in mod_names

    def test_parent_merge_adds_missing_modules(self):
        from codex.forge.source_scanner import scan_system_content
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            child_path, parent_path = self._setup_vault(tmp_path)
            result = scan_system_content(child_path, parent_path=parent_path)
            mod_names = [m["name"] for m in result["modules"]]
            assert "adventure_alpha" in mod_names  # from parent
            assert "adventure_beta" in mod_names    # from child (not duplicated)
            # Should not duplicate adventure_beta
            assert mod_names.count("adventure_beta") == 1

    def test_parent_merge_adds_settings(self):
        from codex.forge.source_scanner import scan_system_content
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            child_path, parent_path = self._setup_vault(tmp_path)
            result = scan_system_content(child_path, parent_path=parent_path)
            setting_names = [s["name"] for s in result["settings"]]
            assert "forgotten_realms" in setting_names

    def test_no_parent_path_no_merge(self):
        from codex.forge.source_scanner import scan_system_content
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            child_path, parent_path = self._setup_vault(tmp_path)
            result = scan_system_content(child_path, parent_path=None)
            mod_names = [m["name"] for m in result["modules"]]
            assert "adventure_alpha" not in mod_names

    def test_nonexistent_parent_path_no_crash(self):
        from codex.forge.source_scanner import scan_system_content
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            child_path, _ = self._setup_vault(tmp_path)
            result = scan_system_content(child_path, parent_path="/nonexistent/path")
            # Should still return child content without crashing
            mod_names = [m["name"] for m in result["modules"]]
            assert "adventure_beta" in mod_names


# =========================================================================
# Ears Model Routing
# =========================================================================

class TestEarsModelRouting:
    """Verify ears.py uses the correct Ollama model."""

    def test_ollama_model_is_mimir(self):
        pytest.importorskip("fastapi", reason="fastapi not installed (optional, in requirements_ears.txt)")
        from codex.services.ears import OLLAMA_MODEL
        assert OLLAMA_MODEL == "mimir"

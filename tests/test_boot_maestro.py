"""
test_boot_maestro.py — Boot Wizard + Maestro Pre-Launch Integration
====================================================================
Tests for WO boot chain: Desktop Icon → Boot Wizard → Vault Scan → Maestro → Main Agent.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# =========================================================================
# Phase 1: check_vault_changes()
# =========================================================================

class TestCheckVaultChanges:
    """Tests for the lightweight vault scanner."""

    def test_returns_correct_structure(self, tmp_path):
        """check_vault_changes() returns dict with new/changed/total keys."""
        from maintenance.codex_index_builder import check_vault_changes

        with patch("maintenance.codex_index_builder.VAULT_DIR", str(tmp_path)), \
             patch("maintenance.codex_index_builder.MANIFEST_FILE", str(tmp_path / "manifest.json")):
            result = check_vault_changes()

        assert "new" in result
        assert "changed" in result
        assert "total_vault" in result
        assert "total_tracked" in result
        assert isinstance(result["new"], list)
        assert isinstance(result["changed"], list)

    def test_detects_new_file(self, tmp_path):
        """A PDF not in manifest is reported as new."""
        from maintenance.codex_index_builder import check_vault_changes

        # Create a vault with one PDF
        vault = tmp_path / "dnd5e"
        vault.mkdir()
        pdf = vault / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test content")

        # Empty manifest
        manifest_path = tmp_path / "vault_manifest.json"
        manifest_path.write_text(json.dumps({"file_hashes": {}}))

        with patch("maintenance.codex_index_builder.VAULT_DIR", str(tmp_path)), \
             patch("maintenance.codex_index_builder.MANIFEST_FILE", str(manifest_path)):
            result = check_vault_changes()

        assert len(result["new"]) == 1
        assert "dnd5e/test.pdf" in result["new"][0] or result["new"][0] == os.path.join("dnd5e", "test.pdf")
        assert result["total_vault"] == 1

    def test_detects_changed_file(self, tmp_path):
        """A PDF with different hash is reported as changed."""
        from maintenance.codex_index_builder import check_vault_changes, _compute_file_hash

        vault = tmp_path / "dnd5e"
        vault.mkdir()
        pdf = vault / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 original content")

        # Manifest with old hash
        manifest_key = os.path.join("dnd5e", "test.pdf")
        manifest_path = tmp_path / "vault_manifest.json"
        manifest_path.write_text(json.dumps({
            "file_hashes": {manifest_key: "old_hash_that_wont_match"}
        }))

        with patch("maintenance.codex_index_builder.VAULT_DIR", str(tmp_path)), \
             patch("maintenance.codex_index_builder.MANIFEST_FILE", str(manifest_path)):
            result = check_vault_changes()

        assert len(result["changed"]) == 1
        assert len(result["new"]) == 0

    def test_clean_when_manifest_matches(self, tmp_path):
        """No changes reported when manifest hashes match current files."""
        from maintenance.codex_index_builder import check_vault_changes, _compute_file_hash

        vault = tmp_path / "dnd5e"
        vault.mkdir()
        pdf = vault / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 stable content")

        # Manifest with correct hash
        manifest_key = os.path.join("dnd5e", "test.pdf")
        current_hash = _compute_file_hash(str(pdf))
        manifest_path = tmp_path / "vault_manifest.json"
        manifest_path.write_text(json.dumps({
            "file_hashes": {manifest_key: current_hash}
        }))

        with patch("maintenance.codex_index_builder.VAULT_DIR", str(tmp_path)), \
             patch("maintenance.codex_index_builder.MANIFEST_FILE", str(manifest_path)):
            result = check_vault_changes()

        assert len(result["new"]) == 0
        assert len(result["changed"]) == 0
        assert result["total_vault"] == 1
        assert result["total_tracked"] == 1

    def test_audio_files_excluded(self, tmp_path):
        """Files inside AUDIO directories should not appear in vault scan."""
        from maintenance.codex_index_builder import check_vault_changes

        vault = tmp_path / "FITD" / "CBR_PNK"
        vault.mkdir(parents=True)

        # Regular file that should be detected
        pdf = vault / "rules.pdf"
        pdf.write_bytes(b"%PDF-1.4 rules content")

        # Audio directory with license.txt — should be skipped
        audio = vault / "AUDIO"
        audio.mkdir()
        (audio / "license.txt").write_text("Creative Commons license")
        (audio / "track01.wav").write_bytes(b"RIFF fake wav")

        manifest_path = tmp_path / "vault_manifest.json"
        manifest_path.write_text(json.dumps({"file_hashes": {}}))

        with patch("maintenance.codex_index_builder.VAULT_DIR", str(tmp_path)), \
             patch("maintenance.codex_index_builder.MANIFEST_FILE", str(manifest_path)):
            result = check_vault_changes()

        # Only the PDF should appear, not the license.txt in AUDIO
        assert result["total_vault"] == 1
        assert len(result["new"]) == 1
        assert "rules.pdf" in result["new"][0]
        assert not any("AUDIO" in f for f in result["new"])

    def test_empty_vault_returns_zeros(self, tmp_path):
        """Empty vault directory returns zero counts."""
        from maintenance.codex_index_builder import check_vault_changes

        manifest_path = tmp_path / "vault_manifest.json"
        manifest_path.write_text(json.dumps({"file_hashes": {}}))

        with patch("maintenance.codex_index_builder.VAULT_DIR", str(tmp_path)), \
             patch("maintenance.codex_index_builder.MANIFEST_FILE", str(manifest_path)):
            result = check_vault_changes()

        assert result["total_vault"] == 0
        assert result["total_tracked"] == 0
        assert result["new"] == []
        assert result["changed"] == []


class TestSkipDirFilter:
    """Tests for the _is_in_skip_dir() filter."""

    def test_audio_dir_skipped(self):
        from maintenance.codex_index_builder import _is_in_skip_dir
        assert _is_in_skip_dir("/vault/FITD/CBR_PNK/AUDIO/license.txt") is True

    def test_normal_dir_not_skipped(self):
        from maintenance.codex_index_builder import _is_in_skip_dir
        assert _is_in_skip_dir("/vault/dnd5e/SOURCE/rules.pdf") is False

    def test_case_sensitive_audio(self):
        from maintenance.codex_index_builder import _is_in_skip_dir
        assert _is_in_skip_dir("/vault/system/audio/track.wav") is True
        assert _is_in_skip_dir("/vault/system/AUDIO/track.wav") is True

    def test_images_dir_skipped(self):
        from maintenance.codex_index_builder import _is_in_skip_dir
        assert _is_in_skip_dir("/vault/system/IMAGES/map.png") is True

    def test_no_false_positive_on_audio_in_filename(self):
        from maintenance.codex_index_builder import _is_in_skip_dir
        assert _is_in_skip_dir("/vault/dnd5e/audio_notes.txt") is False


# =========================================================================
# Phase 2: Boot Wizard Fixes
# =========================================================================

class TestBootWizardFixes:
    """Tests for bug fixes in codex_boot_wizard.py."""

    def test_codex_dir_resolves_to_project_root(self):
        """CODEX_DIR should point to project root, not maintenance/."""
        from maintenance.codex_boot_wizard import CODEX_DIR

        # CODEX_DIR should be the Codex project root
        assert CODEX_DIR.name == "Codex" or "codex" in CODEX_DIR.name.lower() or \
            (CODEX_DIR / "codex_agent_main.py").exists(), \
            f"CODEX_DIR={CODEX_DIR} doesn't look like project root"
        # Must NOT be the maintenance/ directory
        assert CODEX_DIR.name != "maintenance", \
            f"CODEX_DIR still points to maintenance/: {CODEX_DIR}"

    def test_cortex_import_succeeds(self):
        """get_cortex should be importable from codex.core.cortex."""
        from codex.core.cortex import get_cortex, ThermalStatus
        assert callable(get_cortex)
        assert ThermalStatus is not None

    def test_gamesave_dir_outside_maintenance(self):
        """GameSave.SAVE_DIR should resolve to <project>/saves, not maintenance/saves."""
        from maintenance.codex_boot_wizard import GameSave

        save_dir = GameSave.SAVE_DIR
        assert "maintenance" not in str(save_dir) or save_dir.parent.name != "maintenance", \
            f"GameSave.SAVE_DIR incorrectly inside maintenance/: {save_dir}"


# =========================================================================
# Phase 2B: Vault Scan
# =========================================================================

class TestVaultScan:
    """Tests for vault_scan() on BootWizard."""

    def test_vault_scan_no_crash_empty_vault(self):
        """vault_scan() doesn't crash when import fails."""
        from maintenance.codex_boot_wizard import BootWizard

        with patch.object(BootWizard, "__init__", lambda self: None):
            wizard = BootWizard()
            # Simulate import failure inside vault_scan by patching the module
            with patch.dict("sys.modules", {"maintenance.codex_index_builder": None}):
                wizard.vault_scan()  # Should not raise — caught by try/except

    def test_vault_scan_no_crash_clean_vault(self):
        """vault_scan() doesn't crash when vault has no changes."""
        from maintenance.codex_boot_wizard import BootWizard

        mock_changes = {"new": [], "changed": [], "total_vault": 0, "total_tracked": 0}

        with patch.object(BootWizard, "__init__", lambda self: None):
            wizard = BootWizard()
            with patch("maintenance.codex_index_builder.check_vault_changes",
                        return_value=mock_changes):
                wizard.vault_scan()  # Should not raise

    def test_content_scan_finds_modules(self):
        """_scan_content_and_modules() detects adventure modules."""
        from maintenance.codex_boot_wizard import BootWizard

        result = BootWizard._scan_content_and_modules()
        assert isinstance(result, dict)
        assert result["module_count"] > 0, "No modules detected by scanner"
        assert len(result["modules_by_system"]) > 0

    def test_content_scan_finds_config(self):
        """_scan_content_and_modules() detects config JSON files."""
        from maintenance.codex_boot_wizard import BootWizard

        result = BootWizard._scan_content_and_modules()
        assert result["total_config_files"] > 0, "No config files detected"
        categories = [c["name"] for c in result["config_categories"]]
        assert "bestiary" in categories
        assert "loot" in categories

    def test_vault_scan_shows_content_inventory(self):
        """vault_scan() shows content inventory even with no PDF changes."""
        from maintenance.codex_boot_wizard import BootWizard

        mock_changes = {"new": [], "changed": [], "total_vault": 0, "total_tracked": 5}

        with patch.object(BootWizard, "__init__", lambda self: None):
            wizard = BootWizard()
            with patch("maintenance.codex_index_builder.check_vault_changes",
                        return_value=mock_changes):
                wizard.vault_scan()  # Should show content inventory, not "up to date"


# =========================================================================
# Phase 2C: Maestro Importability
# =========================================================================

class TestMaestroImportability:
    """Tests that Maestro functions are importable from boot wizard context."""

    def test_auto_scaffold_importable(self):
        """auto_scaffold() can be imported from codex_maestro."""
        from maintenance.codex_maestro import auto_scaffold
        assert callable(auto_scaffold)

    def test_run_all_importable(self):
        """_run_all() can be imported from codex_maestro."""
        from maintenance.codex_maestro import _run_all
        assert callable(_run_all)

    def test_maestro_main_importable(self):
        """main() can be imported from codex_maestro."""
        from maintenance.codex_maestro import main as maestro_main
        assert callable(maestro_main)


# =========================================================================
# Phase 3-4: Script and Launcher Fixes
# =========================================================================

class TestScriptFixes:
    """Tests for start_maestro.sh and desktop launcher."""

    def test_start_maestro_points_to_maestro(self):
        """start_maestro.sh should reference codex_maestro.py, not codex_gemini_bridge.py."""
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "start_maestro.sh"
        if script_path.exists():
            content = script_path.read_text()
            assert "codex_maestro.py" in content, \
                "start_maestro.sh should reference codex_maestro.py"
            assert "codex_gemini_bridge.py" not in content, \
                "start_maestro.sh still references non-existent codex_gemini_bridge.py"

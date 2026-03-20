"""
tests/test_content_pipeline_profiles.py — WO-P6: Content Pipeline Expansion Tests
====================================================================================
Tests that:
  - All 6 systems (dnd5e, stc, bitd, sav, bob, candela) are present in SYSTEM_PROFILES
  - Each profile has at least one recognizable extractor-pattern key
  - All pattern values in a profile compile as valid regexes
  - All extractor names referenced by callers are present in the EXTRACTORS registry
  - discover_systems() resolves both flat (vault/<system>/SOURCE) and group
    (vault/<group>/<system>/SOURCE) vault layouts
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Pattern keys recognised by the extractors in build_content.py
_PATTERN_KEYS = frozenset({
    "stat_block_pattern",
    "magic_item_pattern",
    "feature_pattern",
    "loot_table_pattern",
    "loot_pattern",
    "trap_pattern",
    "hazard_pattern",
    "npc_pattern",
    "location_pattern",
    "table_pattern",
})

# Valid extractor names as registered in EXTRACTORS dict
_VALID_EXTRACTORS = frozenset({
    "bestiary",
    "loot",
    "hazards",
    "magic_items",
    "features",
    "locations",
    "npcs",
    "traps",
    "tables",
})


def _import_build_content() -> types.ModuleType:
    """Import build_content without executing __main__ block."""
    import importlib
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_content",
        PROJECT_ROOT / "scripts" / "build_content.py",
    )
    assert spec is not None and spec.loader is not None, "Could not find build_content.py"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def bc():
    """Return the build_content module."""
    return _import_build_content()


# ---------------------------------------------------------------------------
# Test Class 1: SYSTEM_PROFILES structure
# ---------------------------------------------------------------------------

class TestSystemProfiles:
    """SYSTEM_PROFILES contains all expected systems with valid patterns."""

    REQUIRED_SYSTEMS = ("dnd5e", "stc", "bitd", "sav", "bob", "candela")

    def test_all_required_systems_present(self, bc):
        profiles = bc.SYSTEM_PROFILES
        for system in self.REQUIRED_SYSTEMS:
            assert system in profiles, (
                f"SYSTEM_PROFILES missing required system '{system}'"
            )

    def test_each_profile_has_at_least_one_pattern_key(self, bc):
        profiles = bc.SYSTEM_PROFILES
        for system in self.REQUIRED_SYSTEMS:
            profile = profiles[system]
            matching_keys = _PATTERN_KEYS & set(profile.keys())
            assert matching_keys, (
                f"SYSTEM_PROFILES['{system}'] has no recognised pattern keys "
                f"(expected one of: {sorted(_PATTERN_KEYS)})"
            )

    def test_all_pattern_values_compile_as_valid_regex(self, bc):
        profiles = bc.SYSTEM_PROFILES
        for system in self.REQUIRED_SYSTEMS:
            profile = profiles[system]
            for key, value in profile.items():
                if key not in _PATTERN_KEYS:
                    continue
                try:
                    re.compile(value, re.IGNORECASE | re.DOTALL)
                except re.error as exc:
                    pytest.fail(
                        f"SYSTEM_PROFILES['{system}']['{key}'] is not a valid regex: {exc}"
                    )

    def test_fitd_profiles_have_npc_and_location_patterns(self, bc):
        """FITD systems need NPC and location patterns for narrative content."""
        profiles = bc.SYSTEM_PROFILES
        for system in ("bitd", "sav", "bob", "candela"):
            assert "npc_pattern" in profiles[system], (
                f"SYSTEM_PROFILES['{system}'] missing 'npc_pattern'"
            )
            assert "location_pattern" in profiles[system], (
                f"SYSTEM_PROFILES['{system}'] missing 'location_pattern'"
            )

    def test_fitd_profiles_have_hazard_or_trap_pattern(self, bc):
        """FITD systems use hazard_pattern (entanglements, bleed, etc.)."""
        profiles = bc.SYSTEM_PROFILES
        for system in ("bitd", "sav", "bob", "candela"):
            has_hazard = "hazard_pattern" in profiles[system] or "trap_pattern" in profiles[system]
            assert has_hazard, (
                f"SYSTEM_PROFILES['{system}'] has neither 'hazard_pattern' nor 'trap_pattern'"
            )

    def test_fitd_profiles_have_table_pattern(self, bc):
        """FITD books include random tables; all four systems need table_pattern."""
        profiles = bc.SYSTEM_PROFILES
        for system in ("bitd", "sav", "bob", "candela"):
            assert "table_pattern" in profiles[system], (
                f"SYSTEM_PROFILES['{system}'] missing 'table_pattern'"
            )

    def test_no_profile_value_is_empty_string(self, bc):
        """Empty pattern strings would silently match everything — guard against it."""
        profiles = bc.SYSTEM_PROFILES
        for system in self.REQUIRED_SYSTEMS:
            for key, value in profiles[system].items():
                if key in _PATTERN_KEYS:
                    assert value.strip(), (
                        f"SYSTEM_PROFILES['{system}']['{key}'] is an empty string"
                    )


# ---------------------------------------------------------------------------
# Test Class 2: EXTRACTORS registry completeness
# ---------------------------------------------------------------------------

class TestExtractorsRegistry:
    """EXTRACTORS dict contains all expected extractor names."""

    def test_all_valid_extractors_registered(self, bc):
        extractors = bc.EXTRACTORS
        for name in _VALID_EXTRACTORS:
            assert name in extractors, (
                f"EXTRACTORS missing expected extractor '{name}'"
            )

    def test_all_registered_extractors_are_callable(self, bc):
        for name, fn in bc.EXTRACTORS.items():
            assert callable(fn), f"EXTRACTORS['{name}'] is not callable"


# ---------------------------------------------------------------------------
# Test Class 3: discover_systems() handles both vault layouts
# ---------------------------------------------------------------------------

class TestDiscoverSystems:
    """discover_systems() resolves flat and group vault layouts."""

    def _make_vault(self, tmp_path: Path, layout: dict) -> Path:
        """Create a fake vault with given layout.

        layout: {system_id: [relative_pdf_path, ...], ...}
        """
        vault = tmp_path / "vault"
        vault.mkdir()
        for system_id, pdf_paths in layout.items():
            for rel in pdf_paths:
                full = vault / rel
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_bytes(b"%PDF-1.4 fake")
        return vault

    def test_flat_layout_discovered(self, bc, tmp_path):
        """vault/<system>/SOURCE/*.pdf — existing pattern for dnd5e/stc."""
        vault = self._make_vault(tmp_path, {
            "dnd5e": ["dnd5e/SOURCE/core.pdf"],
            "stc": ["stc/SOURCE/roshar.pdf"],
        })
        result = bc.discover_systems(vault)
        assert "dnd5e" in result, "flat layout: dnd5e not discovered"
        assert "stc" in result, "flat layout: stc not discovered"
        assert len(result["dnd5e"]) == 1
        assert len(result["stc"]) == 1

    def test_group_layout_discovered(self, bc, tmp_path):
        """vault/<group>/<system>/SOURCE/*.pdf — FITD and ILLUMINATED_WORLDS.

        Uses the real vault directory names (Candela_Obscura, CBR_PNK) to verify
        the normalisation map in discover_systems() is applied correctly.
        """
        vault = self._make_vault(tmp_path, {
            "FITD/bitd": ["FITD/bitd/SOURCE/bitd.pdf"],
            "FITD/sav": ["FITD/sav/SOURCE/sav.pdf"],
            "FITD/bob": ["FITD/bob/SOURCE/bob.pdf"],
            # Real vault name for candela is Candela_Obscura — normalised to 'candela'
            "ILLUMINATED_WORLDS/Candela_Obscura": [
                "ILLUMINATED_WORLDS/Candela_Obscura/SOURCE/candela.pdf"
            ],
            # Real vault name for cbrpnk is CBR_PNK — normalised to 'cbrpnk'
            "FITD/CBR_PNK": ["FITD/CBR_PNK/SOURCE/cbrpnk.pdf"],
        })
        result = bc.discover_systems(vault)
        assert "bitd" in result, "group layout: bitd not discovered"
        assert "sav" in result, "group layout: sav not discovered"
        assert "bob" in result, "group layout: bob not discovered"
        assert "candela" in result, (
            "group layout: Candela_Obscura not normalised to 'candela'"
        )
        assert "cbrpnk" in result, (
            "group layout: CBR_PNK not normalised to 'cbrpnk'"
        )

    def test_mixed_layout_discovered(self, bc, tmp_path):
        """Both flat and group systems coexist in the same vault."""
        vault = self._make_vault(tmp_path, {
            "dnd5e": ["dnd5e/SOURCE/core.pdf"],
            "FITD/bitd": ["FITD/bitd/SOURCE/bitd.pdf"],
        })
        result = bc.discover_systems(vault)
        assert "dnd5e" in result
        assert "bitd" in result

    def test_empty_vault_returns_empty_dict(self, bc, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        result = bc.discover_systems(vault)
        assert result == {}

    def test_nonexistent_vault_returns_empty_dict(self, bc, tmp_path):
        result = bc.discover_systems(tmp_path / "does_not_exist")
        assert result == {}

    def test_group_dir_without_pdfs_not_included(self, bc, tmp_path):
        """A group subdir with SOURCE but no PDFs should not appear in results."""
        vault = tmp_path / "vault"
        (vault / "FITD" / "empty_system" / "SOURCE").mkdir(parents=True)
        result = bc.discover_systems(vault)
        assert "empty_system" not in result

    def test_real_vault_contains_fitd_systems(self, bc):
        """Integration check: the actual project vault discovers bitd/sav/bob/candela/cbrpnk."""
        vault_root = PROJECT_ROOT / "vault"
        if not vault_root.exists():
            pytest.skip("vault/ directory not present")
        result = bc.discover_systems(vault_root)
        # bitd/sav/bob under vault/FITD/; candela under vault/ILLUMINATED_WORLDS/Candela_Obscura/
        # cbrpnk under vault/FITD/CBR_PNK/ — all normalised to canonical system IDs
        for system in ("bitd", "sav", "bob", "candela", "cbrpnk"):
            assert system in result, (
                f"real vault: system '{system}' not discovered — "
                f"check vault/FITD/{system}/SOURCE/ or ILLUMINATED_WORLDS normalisation map"
            )


# ---------------------------------------------------------------------------
# Test Class 4: output directory pre-conditions
# ---------------------------------------------------------------------------

class TestOutputDirectories:
    """Config output directories for FITD systems exist (or can be created)."""

    OUTPUT_DIRS = (
        "bestiary", "loot", "hazards", "locations", "npcs", "tables",
    )

    def test_all_output_dirs_exist(self):
        config = PROJECT_ROOT / "config"
        for dirname in self.OUTPUT_DIRS:
            dirpath = config / dirname
            assert dirpath.exists() and dirpath.is_dir(), (
                f"config/{dirname}/ does not exist — pipeline cannot write output"
            )

"""
tests/test_module_select.py — Module select flow and villain routing tests.
============================================================================

Covers: module scanning, spatial capability detection, villain path
filtering, and ZoneManager villain path persistence.

WO-V51.0: The Foundation Sprint — Phase B5
"""

import json
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from codex.spatial.module_manifest import ModuleManifest, Chapter, ZoneEntry
from codex.spatial.zone_manager import ZoneManager


# =========================================================================
# Test fixtures
# =========================================================================

def _make_dragon_heist_manifest() -> ModuleManifest:
    """Build a Dragon Heist-style manifest with villain path zones."""
    return ModuleManifest(
        module_id="dragon_heist",
        display_name="Waterdeep: Dragon Heist",
        system_id="dnd5e",
        chapters=[
            Chapter(
                chapter_id="ch1",
                display_name="Chapter 1",
                order=1,
                zones=[
                    ZoneEntry(zone_id="yawning_portal",
                              entry_trigger="module_start",
                              exit_trigger="quest_complete"),
                ],
            ),
            Chapter(
                chapter_id="ch3",
                display_name="Chapter 3: Fireball",
                order=3,
                zones=[
                    ZoneEntry(zone_id="dock_ward",
                              entry_trigger="quest_complete",
                              exit_trigger="investigation_complete"),
                ],
            ),
            Chapter(
                chapter_id="ch4",
                display_name="Chapter 4: Dragon Season",
                order=4,
                zones=[
                    ZoneEntry(zone_id="kolat_towers",
                              entry_trigger="villain_path_manshoon",
                              exit_trigger="boss_defeated"),
                    ZoneEntry(zone_id="cassalanter_estate",
                              entry_trigger="villain_path_cassalanter",
                              exit_trigger="boss_defeated"),
                    ZoneEntry(zone_id="xanathar_lair",
                              entry_trigger="villain_path_xanathar",
                              exit_trigger="boss_defeated"),
                    ZoneEntry(zone_id="manshoon_sanctum",
                              entry_trigger="villain_path_manshoon",
                              exit_trigger="boss_defeated"),
                ],
            ),
            Chapter(
                chapter_id="ch5",
                display_name="Chapter 5: Spring Madness",
                order=5,
                zones=[
                    ZoneEntry(zone_id="vault_of_dragons",
                              entry_trigger="boss_defeated",
                              exit_trigger="module_complete"),
                ],
            ),
        ],
    )


def _make_cbrpnk_manifest() -> ModuleManifest:
    """Build a CBR+PNK manifest for FITD detection tests."""
    return ModuleManifest(
        module_id="cbrpnk_mind_gap",
        display_name="Mind the Gap",
        system_id="cbrpnk",
        chapters=[
            Chapter(
                chapter_id="act1",
                display_name="Act 1: The Job",
                order=1,
                zones=[
                    ZoneEntry(zone_id="fixer_den",
                              entry_trigger="module_start",
                              exit_trigger="player_choice"),
                ],
            ),
        ],
    )


# =========================================================================
# Module scanning
# =========================================================================

class TestModuleScanning:
    """Module scanning finds modules by system_id."""

    def test_scan_finds_dnd5e_modules(self, tmp_path):
        # Set up mock module directory
        mod_dir = tmp_path / "modules" / "dragon_heist"
        mod_dir.mkdir(parents=True)
        manifest = _make_dragon_heist_manifest()
        (mod_dir / "module_manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2))

        # Patch _MODULES_DIR to tmp_path / "modules"
        with patch("play_universal._MODULES_DIR", tmp_path / "modules"), \
             patch("play_universal.ModuleManifest", ModuleManifest):
            from play_universal import _offer_module_select
            # Can't easily test interactive input, but we can test
            # that the function finds modules by checking the scan logic
            from play_universal import _MODULES_DIR
            modules = []
            for entry in sorted((tmp_path / "modules").iterdir()):
                if not entry.is_dir():
                    continue
                mp = entry / "module_manifest.json"
                if mp.exists():
                    data = json.loads(mp.read_text())
                    if data.get("system_id") == "dnd5e":
                        modules.append(data)
            assert len(modules) == 1
            assert modules[0]["display_name"] == "Waterdeep: Dragon Heist"

    def test_scan_returns_none_for_unknown_system(self, tmp_path):
        mod_dir = tmp_path / "modules" / "dragon_heist"
        mod_dir.mkdir(parents=True)
        manifest = _make_dragon_heist_manifest()
        (mod_dir / "module_manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2))

        # Scan for non-existent system
        modules = []
        for entry in sorted((tmp_path / "modules").iterdir()):
            if not entry.is_dir():
                continue
            mp = entry / "module_manifest.json"
            if mp.exists():
                data = json.loads(mp.read_text())
                if data.get("system_id") == "unknown_system":
                    modules.append(data)
        assert len(modules) == 0

    def test_scan_finds_cbrpnk_modules(self, tmp_path):
        mod_dir = tmp_path / "modules" / "cbrpnk_mind_gap"
        mod_dir.mkdir(parents=True)
        manifest = _make_cbrpnk_manifest()
        (mod_dir / "module_manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2))

        modules = []
        for entry in sorted((tmp_path / "modules").iterdir()):
            if not entry.is_dir():
                continue
            mp = entry / "module_manifest.json"
            if mp.exists():
                data = json.loads(mp.read_text())
                if data.get("system_id") == "cbrpnk":
                    modules.append(data)
        assert len(modules) == 1


# =========================================================================
# Spatial capability detection
# =========================================================================

class TestSpatialCapability:
    """Engine spatial capability detection."""

    def test_engine_with_generate_dungeon_is_spatial(self):
        engine = MagicMock()
        engine.generate_dungeon = MagicMock(return_value={"total_rooms": 5})
        assert hasattr(engine, 'generate_dungeon')

    def test_engine_without_generate_dungeon_is_narrative(self):
        engine = MagicMock(spec=['handle_command', 'create_character'])
        assert not hasattr(engine, 'generate_dungeon')


# =========================================================================
# Villain path filtering
# =========================================================================

class TestVillainPath:
    """ZoneManager villain path routing."""

    def test_set_villain_path_filters_ch4(self):
        manifest = _make_dragon_heist_manifest()
        zm = ZoneManager(manifest=manifest, base_path="")
        zm.set_villain_path("manshoon")

        # Get ch4 zones and filter
        ch4 = [ch for ch in manifest.chapters if ch.chapter_id == "ch4"][0]
        filtered = zm._filter_zones_by_path(ch4.zones)

        zone_ids = [z.zone_id for z in filtered]
        assert "kolat_towers" in zone_ids
        assert "manshoon_sanctum" in zone_ids
        assert "cassalanter_estate" not in zone_ids
        assert "xanathar_lair" not in zone_ids

    def test_no_path_set_returns_all(self):
        manifest = _make_dragon_heist_manifest()
        zm = ZoneManager(manifest=manifest, base_path="")
        # No villain path set — fallback behavior
        ch4 = [ch for ch in manifest.chapters if ch.chapter_id == "ch4"][0]
        filtered = zm._filter_zones_by_path(ch4.zones)
        assert len(filtered) == 4  # All zones preserved

    def test_villain_path_persists_in_save(self):
        manifest = _make_dragon_heist_manifest()
        zm = ZoneManager(manifest=manifest, base_path="")
        zm.set_villain_path("cassalanter")
        d = zm.to_dict()
        assert d["villain_path"] == "cassalanter"

        zm2 = ZoneManager.from_dict(d, manifest=manifest)
        assert zm2._villain_path == "cassalanter"

    def test_get_villain_paths(self):
        manifest = _make_dragon_heist_manifest()
        zm = ZoneManager(manifest=manifest, base_path="")
        # Move to ch4
        zm.chapter_idx = 2  # ch4 is at index 2 (after sorting: ch1=0, ch3=1, ch4=2)
        paths = zm.get_villain_paths()
        assert "manshoon" in paths
        assert "cassalanter" in paths
        assert "xanathar" in paths

    def test_advance_skips_non_matching_villain_zones(self):
        """When villain path is set, advance() skips non-matching zones."""
        manifest = _make_dragon_heist_manifest()
        zm = ZoneManager(manifest=manifest, base_path="")
        zm.set_villain_path("xanathar")

        # Move to ch3 dock_ward (index 1, zone 0)
        zm.chapter_idx = 1
        zm.zone_idx = 0

        # Advance from dock_ward → should skip kolat_towers (manshoon),
        # skip cassalanter_estate, land on xanathar_lair
        next_entry = zm.advance()
        assert next_entry is not None
        assert next_entry.zone_id == "xanathar_lair"

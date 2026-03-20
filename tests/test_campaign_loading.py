"""
tests/test_campaign_loading.py — Campaign Loading Screen Tests
================================================================
Tests that _campaign_loading_sequence creates memory shards,
triggers dungeon generation for spatial systems, and skips it
for FITD systems.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from play_universal import _campaign_loading_sequence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(system="dnd5e", party=None, dungeon_result=None):
    """Create a minimal mock engine."""
    engine = MagicMock()
    engine.party = party or []
    engine.current_location = None
    if dungeon_result is not None:
        engine.generate_dungeon.return_value = dungeon_result
    return engine


def _quiet_console():
    """Console that doesn't print to terminal."""
    from rich.console import Console
    return Console(quiet=True)


# ---------------------------------------------------------------------------
# Tests: Memory shard creation
# ---------------------------------------------------------------------------

class TestMemoryShards:
    def test_creates_master_shard_with_system_id(self):
        engine = _make_engine(dungeon_result={"total_rooms": 5})
        mem, _ = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", None, None)
        master = [s for s in mem.shards if s.shard_type.value == "MASTER"]
        assert len(master) == 1
        assert "dnd5e" in master[0].content
        assert master[0].pinned is True

    def test_master_shard_includes_campaign_name(self):
        engine = _make_engine(dungeon_result={"total_rooms": 5})
        manifest = {"campaign_name": "Dragon Heist"}
        mem, _ = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", manifest, None)
        master = [s for s in mem.shards if s.shard_type.value == "MASTER"]
        assert "Dragon Heist" in master[0].content

    def test_creates_anchor_shard_with_session_start(self):
        engine = _make_engine(dungeon_result={"total_rooms": 5})
        mem, _ = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", None, None)
        anchors = [s for s in mem.shards if s.shard_type.value == "ANCHOR"]
        assert len(anchors) == 1
        assert "Day 1" in anchors[0].content

    def test_anchor_shard_includes_party_names(self):
        hero = SimpleNamespace(name="Aldric")
        engine = _make_engine(party=[hero], dungeon_result={"total_rooms": 5})
        mem, _ = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", None, None)
        anchors = [s for s in mem.shards if s.shard_type.value == "ANCHOR"]
        assert "Aldric" in anchors[0].content

    def test_always_creates_two_shards(self):
        engine = _make_engine(dungeon_result={"total_rooms": 5})
        mem, _ = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", None, None)
        assert len(mem.shards) == 2


# ---------------------------------------------------------------------------
# Tests: Dungeon generation routing
# ---------------------------------------------------------------------------

class TestDungeonGeneration:
    @patch("play_universal.DUNGEON_SYSTEMS", {"dnd5e", "stc"})
    def test_spatial_system_generates_dungeon(self):
        engine = _make_engine(dungeon_result={"total_rooms": 8})
        _, result = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", None, None)
        engine.generate_dungeon.assert_called_once()
        assert result["total_rooms"] == 8

    @patch("play_universal.DUNGEON_SYSTEMS", {"dnd5e", "stc"})
    def test_module_zone_skips_dungeon_generation(self):
        engine = _make_engine()
        zm = MagicMock()
        zm.current_graph = MagicMock()  # non-None = zone already loaded
        zm.zone_name = "The Yawning Portal"
        zm.manifest = SimpleNamespace(display_name="Dragon Heist")
        _, result = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", None, zm)
        engine.generate_dungeon.assert_not_called()
        assert result is None

    @patch("play_universal.DUNGEON_SYSTEMS", {"dnd5e", "stc"})
    @patch("play_universal.FITD_SYSTEMS", {"bitd", "sav", "bob"})
    def test_fitd_system_skips_dungeon_generation(self):
        engine = _make_engine()
        _, result = _campaign_loading_sequence(
            _quiet_console(), engine, "bitd", None, None)
        engine.generate_dungeon.assert_not_called()
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Module info in shards
# ---------------------------------------------------------------------------

class TestModuleInfo:
    @patch("play_universal.DUNGEON_SYSTEMS", {"dnd5e"})
    def test_module_name_in_master_shard(self):
        engine = _make_engine(dungeon_result={"total_rooms": 5})
        zm = MagicMock()
        zm.current_graph = MagicMock()
        zm.zone_name = "Chapter 1"
        zm.manifest = SimpleNamespace(display_name="Waterdeep: Dragon Heist")
        mem, _ = _campaign_loading_sequence(
            _quiet_console(), engine, "dnd5e", None, zm)
        master = [s for s in mem.shards if s.shard_type.value == "MASTER"]
        assert "Waterdeep: Dragon Heist" in master[0].content

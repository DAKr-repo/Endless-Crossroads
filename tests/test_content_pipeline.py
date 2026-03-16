"""
tests/test_content_pipeline.py — WO-V58.0 Content Extraction Pipeline Tests
=============================================================================
Tests for:
  - config_loader utility
  - D&D 5e loot/hazard/magic_items config loading
  - STC bestiary/loot/hazard config loading
  - CosmereAdapter._make_enemy() bestiary integration
  - build_content.py extractor registry and helpers
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================================
# Track D — config_loader.py
# =========================================================================

class TestConfigLoader:
    """Tests for codex.core.config_loader."""

    def setup_method(self):
        from codex.core.config_loader import clear_cache
        clear_cache()

    def test_load_config_bestiary_dnd5e(self):
        """Load existing bestiary config."""
        from codex.core.config_loader import load_config
        data = load_config("bestiary", "dnd5e")
        assert data is not None
        assert data["version"] == 1
        assert "tiers" in data
        assert "1" in data["tiers"]
        assert len(data["tiers"]["1"]) > 0

    def test_load_config_missing_returns_fallback(self):
        """Missing config returns fallback."""
        from codex.core.config_loader import load_config
        result = load_config("nonexistent", "nosystem", fallback={"default": True})
        assert result == {"default": True}

    def test_load_config_caching(self):
        """Second load returns cached data."""
        from codex.core.config_loader import load_config
        data1 = load_config("bestiary", "dnd5e")
        data2 = load_config("bestiary", "dnd5e")
        assert data1 is data2  # Same object (cached)

    def test_load_config_force_bypass_cache(self):
        """force=True reloads from disk."""
        from codex.core.config_loader import load_config
        data1 = load_config("bestiary", "dnd5e")
        data2 = load_config("bestiary", "dnd5e", force=True)
        assert data1 is not data2
        assert data1 == data2

    def test_config_exists_true(self):
        """config_exists returns True for existing file."""
        from codex.core.config_loader import config_exists
        assert config_exists("bestiary", "dnd5e") is True

    def test_config_exists_false(self):
        """config_exists returns False for missing file."""
        from codex.core.config_loader import config_exists
        assert config_exists("nonexistent", "nosystem") is False

    def test_config_path_construction(self):
        """config_path returns proper path."""
        from codex.core.config_loader import config_path
        p = config_path("bestiary", "dnd5e")
        assert p.endswith(os.path.join("config", "bestiary", "dnd5e.json"))

    def test_clear_cache(self):
        """clear_cache empties the cache."""
        from codex.core.config_loader import load_config, clear_cache, _CACHE
        load_config("bestiary", "dnd5e")
        assert len(_CACHE) > 0
        clear_cache()
        assert len(_CACHE) == 0

    def test_load_config_loot_dnd5e(self):
        """Load loot config for D&D 5e."""
        from codex.core.config_loader import load_config
        data = load_config("loot", "dnd5e")
        assert data is not None
        assert "tiers" in data
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            for item in data["tiers"][tier]:
                assert "name" in item
                assert "rarity" in item

    def test_load_config_hazards_dnd5e(self):
        """Load hazards config for D&D 5e."""
        from codex.core.config_loader import load_config
        data = load_config("hazards", "dnd5e")
        assert data is not None
        assert "tiers" in data
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            for hazard in data["tiers"][tier]:
                assert "name" in hazard
                assert "dc" in hazard

    def test_load_config_magic_items_dnd5e(self):
        """Load magic items config for D&D 5e."""
        from codex.core.config_loader import load_config
        data = load_config("magic_items", "dnd5e")
        assert data is not None
        assert "items" in data
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert "name" in item
            assert "rarity" in item

    def test_load_config_features_dnd5e(self):
        """Load features config for D&D 5e."""
        from codex.core.config_loader import load_config
        data = load_config("features", "dnd5e")
        assert data is not None
        assert "invocations" in data
        assert "maneuvers" in data
        assert "metamagic" in data
        assert "fighting_styles" in data
        assert len(data["invocations"]) >= 10
        assert len(data["maneuvers"]) >= 10

    def test_load_config_bestiary_stc(self):
        """Load STC bestiary config."""
        from codex.core.config_loader import load_config
        data = load_config("bestiary", "stc")
        assert data is not None
        assert data.get("format") == "cosmere"
        assert "tiers" in data
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            for monster in data["tiers"][tier]:
                assert "name" in monster
                assert "role" in monster

    def test_load_config_loot_stc(self):
        """Load STC loot config."""
        from codex.core.config_loader import load_config
        data = load_config("loot", "stc")
        assert data is not None
        assert data.get("format") == "cosmere"
        assert "tiers" in data

    def test_load_config_hazards_stc(self):
        """Load STC hazards config."""
        from codex.core.config_loader import load_config
        data = load_config("hazards", "stc")
        assert data is not None
        assert "tiers" in data


# =========================================================================
# Track B — D&D 5e Engine Loader Integration
# =========================================================================

class TestDnD5eLoaders:
    """Tests for D&D 5e engine config-driven pools."""

    def test_load_loot_pool_from_config(self):
        """_load_loot_pool returns names from config."""
        # Reset cache
        import codex.games.dnd5e as dnd5e_mod
        dnd5e_mod._LOOT_CACHE = None
        pool = dnd5e_mod._load_loot_pool()
        assert isinstance(pool, dict)
        assert 1 in pool
        assert 4 in pool
        assert "Potion of Healing" in pool[1]
        assert "Vorpal Sword" in pool[4]

    def test_load_hazard_pool_from_config(self):
        """_load_hazard_pool returns names with DC from config."""
        import codex.games.dnd5e as dnd5e_mod
        dnd5e_mod._HAZARD_CACHE = None
        pool = dnd5e_mod._load_hazard_pool()
        assert isinstance(pool, dict)
        assert 1 in pool
        # Should include DC notation
        assert any("DC" in h for h in pool[1])

    def test_load_magic_items(self):
        """_load_magic_items returns list of item dicts."""
        import codex.games.dnd5e as dnd5e_mod
        dnd5e_mod._MAGIC_ITEMS_CACHE = None
        items = dnd5e_mod._load_magic_items()
        assert isinstance(items, list)
        assert len(items) > 0
        assert all("name" in i for i in items)
        assert all("rarity" in i for i in items)

    def test_loot_pool_backward_compatible(self):
        """_LOOT_POOL module-level dict still works."""
        from codex.games.dnd5e import _LOOT_POOL
        assert isinstance(_LOOT_POOL, dict)
        assert 1 in _LOOT_POOL
        assert isinstance(_LOOT_POOL[1], list)
        assert len(_LOOT_POOL[1]) > 0

    def test_hazard_pool_backward_compatible(self):
        """_HAZARD_POOL module-level dict still works."""
        from codex.games.dnd5e import _HAZARD_POOL
        assert isinstance(_HAZARD_POOL, dict)
        assert 1 in _HAZARD_POOL

    def test_adapter_uses_loaded_pools(self):
        """DnD5eAdapter.populate_room uses config-loaded pools."""
        from codex.games.dnd5e import DnD5eAdapter
        adapter = DnD5eAdapter(seed=42)
        loot = adapter.get_loot_pool(1)
        assert isinstance(loot, list)
        assert len(loot) > 0


# =========================================================================
# Track C — STC Engine Loader Integration
# =========================================================================

class TestSTCLoaders:
    """Tests for STC/Cosmere engine config-driven pools."""

    def test_load_bestiary_from_config(self):
        """STC _load_bestiary returns structured entries."""
        import codex.games.stc as stc_mod
        stc_mod._STC_BESTIARY_CACHE = None
        bestiary = stc_mod._load_bestiary()
        assert isinstance(bestiary, dict)
        assert 1 in bestiary
        assert 4 in bestiary
        for entry in bestiary[1]:
            assert "name" in entry

    def test_load_bestiary_has_cosmere_stats(self):
        """STC bestiary entries include Cosmere stat format."""
        import codex.games.stc as stc_mod
        stc_mod._STC_BESTIARY_CACHE = None
        bestiary = stc_mod._load_bestiary()
        entry = bestiary[1][0]
        assert "role" in entry
        assert "base_hp" in entry
        assert entry["role"] in ("minion", "rival", "boss")

    def test_load_loot_pool_stc(self):
        """STC _load_loot_pool returns names from config."""
        import codex.games.stc as stc_mod
        stc_mod._STC_LOOT_CACHE = None
        pool = stc_mod._load_loot_pool()
        assert isinstance(pool, dict)
        assert 1 in pool
        assert "Stormlight Sphere (Chip)" in pool[1]

    def test_load_hazard_pool_stc(self):
        """STC _load_hazard_pool returns names from config."""
        import codex.games.stc as stc_mod
        stc_mod._STC_HAZARD_CACHE = None
        pool = stc_mod._load_hazard_pool()
        assert isinstance(pool, dict)
        assert 1 in pool
        assert "Highstorm Winds" in pool[1]

    def test_enemy_pool_from_bestiary(self):
        """_ENEMY_POOL populated from bestiary names."""
        from codex.games.stc import _ENEMY_POOL
        assert isinstance(_ENEMY_POOL, dict)
        assert 1 in _ENEMY_POOL
        assert "Cremling Swarm" in _ENEMY_POOL[1]

    def test_cosmere_adapter_make_enemy(self):
        """CosmereAdapter._make_enemy uses bestiary stats."""
        from codex.games.stc import CosmereAdapter
        adapter = CosmereAdapter(seed=42)
        enemy = adapter._make_enemy(1)
        assert "name" in enemy
        assert "hp" in enemy
        assert "attack" in enemy
        assert "defense" in enemy
        assert enemy["tier"] == 1
        assert enemy["hp"] > 0

    def test_cosmere_adapter_make_enemy_tier4(self):
        """CosmereAdapter._make_enemy works for tier 4."""
        from codex.games.stc import CosmereAdapter
        adapter = CosmereAdapter(seed=42)
        enemy = adapter._make_enemy(4)
        assert enemy["tier"] == 4
        assert enemy["hp"] > 0

    def test_adapter_populate_room_uses_make_enemy(self):
        """CosmereAdapter.populate_room creates enemies via _make_enemy."""
        from codex.games.stc import CosmereAdapter
        adapter = CosmereAdapter(seed=100)
        # Create a mock room
        room = MagicMock()
        room.tier = 2
        from codex.spatial.map_engine import RoomType
        room.room_type = RoomType.BOSS
        pop = adapter.populate_room(room)
        # Boss rooms always have 1-2 enemies
        assert len(pop.content["enemies"]) >= 1
        for e in pop.content["enemies"]:
            assert "name" in e
            assert e["hp"] > 0


# =========================================================================
# Track A — build_content.py helpers
# =========================================================================

class TestBuildContentHelpers:
    """Tests for build_content.py utility functions."""

    def test_extractor_registry_complete(self):
        """All 5 extractors registered."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from build_content import EXTRACTORS
        assert "bestiary" in EXTRACTORS
        assert "loot" in EXTRACTORS
        assert "hazards" in EXTRACTORS
        assert "magic_items" in EXTRACTORS
        assert "features" in EXTRACTORS

    def test_system_profiles_dnd5e(self):
        """D&D 5e system profile has expected patterns."""
        from build_content import SYSTEM_PROFILES
        profile = SYSTEM_PROFILES["dnd5e"]
        assert "stat_block_pattern" in profile
        assert "magic_item_pattern" in profile
        assert "trap_pattern" in profile

    def test_system_profiles_stc(self):
        """STC system profile has expected patterns."""
        from build_content import SYSTEM_PROFILES
        profile = SYSTEM_PROFILES["stc"]
        assert "stat_block_pattern" in profile

    def test_tier_from_cr(self):
        """CR-to-tier mapping works correctly."""
        from build_content import _tier_from_cr
        assert _tier_from_cr("1/4") == 1
        assert _tier_from_cr("1") == 1
        assert _tier_from_cr("4") == 1
        assert _tier_from_cr("5") == 2
        assert _tier_from_cr("10") == 2
        assert _tier_from_cr("11") == 3
        assert _tier_from_cr("17") == 3
        assert _tier_from_cr("18") == 4
        assert _tier_from_cr("30") == 4
        assert _tier_from_cr("bad") == 1

    def test_regex_extract_stat_block_dnd5e(self):
        """Regex stat block extraction for D&D 5e."""
        from build_content import _regex_extract_stat_block
        chunk = (
            "Goblin\n"
            "Small humanoid\n"
            "Armor Class 15 (leather armor)\n"
            "Hit Points 7 (2d6)\n"
            "Challenge 1/4\n"
        )
        result = _regex_extract_stat_block(chunk, "dnd5e")
        assert result is not None
        assert result["name"] == "Goblin"
        assert result["base_hp"] == 7
        assert result["base_ac"] == 15
        assert result["cr"] == "1/4"

    def test_regex_extract_stat_block_stc(self):
        """Regex stat block extraction for STC."""
        from build_content import _regex_extract_stat_block
        chunk = (
            "Parshendi Scout\n"
            "Tier 1 Minion\n"
            "Health: 11\n"
        )
        result = _regex_extract_stat_block(chunk, "stc")
        assert result is not None
        assert result["name"] == "Parshendi Scout"
        assert result["role"] == "minion"
        assert result["base_hp"] == 11

    def test_regex_extract_magic_item(self):
        """Regex magic item extraction."""
        from build_content import _regex_extract_magic_item
        chunk = (
            "Cloak of Protection\n"
            "Wondrous item, uncommon (requires attunement)\n"
            "You gain a +1 bonus to AC and saving throws.\n"
        )
        result = _regex_extract_magic_item(chunk)
        assert result is not None
        assert result["name"] == "Cloak of Protection"
        assert result["rarity"] == "uncommon"
        assert result["attunement"] is True

    def test_extract_bestiary_skips_existing(self):
        """Bestiary extractor skips when config exists and force=False."""
        from build_content import extract_bestiary
        result = extract_bestiary("dnd5e", [], no_llm=True, force=False)
        assert result["status"] == "skipped (exists)"

    def test_extract_loot_skips_existing(self):
        """Loot extractor skips when config exists and force=False."""
        from build_content import extract_loot
        result = extract_loot("dnd5e", [], no_llm=True, force=False)
        assert result["status"] == "skipped (exists)"

    def test_extract_hazards_skips_existing(self):
        """Hazards extractor skips when config exists and force=False."""
        from build_content import extract_hazards
        result = extract_hazards("dnd5e", [], no_llm=True, force=False)
        assert result["status"] == "skipped (exists)"


# =========================================================================
# Integration — Config data validation
# =========================================================================

class TestConfigDataIntegrity:
    """Validate the content of config JSON files."""

    def test_dnd5e_loot_tier_coverage(self):
        """D&D 5e loot has all 4 tiers."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("loot", "dnd5e")
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            assert len(data["tiers"][tier]) >= 3

    def test_dnd5e_hazard_tier_coverage(self):
        """D&D 5e hazards has all 4 tiers."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("hazards", "dnd5e")
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            assert len(data["tiers"][tier]) >= 3

    def test_stc_bestiary_tier_coverage(self):
        """STC bestiary has all 4 tiers with required fields."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("bestiary", "stc")
        assert data["format"] == "cosmere"
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            for monster in data["tiers"][tier]:
                assert "name" in monster
                assert "role" in monster
                assert "base_hp" in monster
                assert monster["role"] in ("minion", "rival", "boss")

    def test_stc_bestiary_has_stat_attributes(self):
        """STC bestiary entries include physical/cognitive/spiritual stats."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("bestiary", "stc")
        entry = data["tiers"]["1"][0]
        assert "physical" in entry
        assert "cognitive" in entry
        assert "spiritual" in entry
        assert "str" in entry["physical"]

    def test_stc_loot_tier_coverage(self):
        """STC loot has all 4 tiers."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("loot", "stc")
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            assert len(data["tiers"][tier]) >= 3

    def test_stc_hazard_tier_coverage(self):
        """STC hazards has all 4 tiers."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("hazards", "stc")
        for tier in ["1", "2", "3", "4"]:
            assert tier in data["tiers"]
            assert len(data["tiers"][tier]) >= 3

    def test_dnd5e_magic_items_rarity_distribution(self):
        """Magic items span multiple rarities."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("magic_items", "dnd5e")
        rarities = {item["rarity"] for item in data["items"]}
        assert "common" in rarities
        assert "uncommon" in rarities
        assert "rare" in rarities
        assert "legendary" in rarities

    def test_dnd5e_features_invocations(self):
        """Invocations have name and effect."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("features", "dnd5e")
        for inv in data["invocations"]:
            assert "name" in inv
            assert "effect" in inv

    def test_dnd5e_features_maneuvers(self):
        """Maneuvers have name and effect."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("features", "dnd5e")
        for man in data["maneuvers"]:
            assert "name" in man
            assert "effect" in man

    def test_dnd5e_features_metamagic(self):
        """Metamagic options have name, cost, and effect."""
        from codex.core.config_loader import load_config, clear_cache
        clear_cache()
        data = load_config("features", "dnd5e")
        for mm in data["metamagic"]:
            assert "name" in mm
            assert "cost" in mm
            assert "effect" in mm

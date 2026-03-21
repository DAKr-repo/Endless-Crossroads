"""
tests/test_content_sprint.py — Validation for Content Sprint (Backlog #11-15)
==============================================================================
Verifies that FITD systems have populated config files for NPCs, locations,
hazards, tables, bestiary, loot, and magic items, and that ContentPool
correctly loads and serves them.
"""

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CONFIG = Path(__file__).resolve().parent.parent / "config"

FITD_SYSTEMS = ["bitd", "sav", "bob", "candela", "cbrpnk"]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _load(subdir: str, system: str) -> dict:
    fp = CONFIG / subdir / f"{system}.json"
    assert fp.exists(), f"Missing {fp.relative_to(CONFIG.parent)}"
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


# ---------------------------------------------------------------------------
# Phase 2: SaV Full Population (#11)
# ---------------------------------------------------------------------------

class TestSaVContentPool:
    """SaV should have non-empty content for all pool types."""

    def test_sav_npcs_exist(self):
        data = _load("npcs", "sav")
        assert len(data.get("named_npcs", [])) >= 5

    def test_sav_locations_exist(self):
        data = _load("locations", "sav")
        locs = data.get("locations", [])
        assert len(locs) >= 3

    def test_sav_bestiary_exist(self):
        data = _load("bestiary", "sav")
        assert "tiers" in data
        for tier in ("1", "2", "3", "4"):
            assert len(data["tiers"].get(tier, [])) >= 1

    def test_sav_loot_exist(self):
        data = _load("loot", "sav")
        assert "tiers" in data
        for tier in ("1", "2", "3", "4"):
            assert len(data["tiers"].get(tier, [])) >= 1

    def test_sav_content_pool_loads(self):
        from codex.forge.content_pool import ContentPool

        pool = ContentPool("sav", seed=42)
        npcs = pool.get_npcs(1, "", 3)
        assert len(npcs) == 3
        assert all(n.name != "Unknown" for n in npcs)

    def test_sav_content_pool_enemies(self):
        from codex.forge.content_pool import ContentPool

        pool = ContentPool("sav", seed=42)
        enemies = pool.get_enemies(tier=2, count=2)
        assert len(enemies) == 2
        assert all(e.name != "Tier 2 Adversary" for e in enemies)

    def test_sav_content_pool_loot(self):
        from codex.forge.content_pool import ContentPool

        pool = ContentPool("sav", seed=42)
        loot = pool.get_loot(tier=1, count=2)
        assert len(loot) == 2
        assert all(l.name != "Tier 1 Trinket" for l in loot)


# ---------------------------------------------------------------------------
# Phase 3: FITD Hazards (#12)
# ---------------------------------------------------------------------------

class TestFITDHazards:
    """All 5 FITD systems should have hazard config files."""

    @pytest.mark.parametrize("system", FITD_SYSTEMS)
    def test_hazards_file_exists(self, system: str):
        data = _load("hazards", system)
        assert "tiers" in data

    @pytest.mark.parametrize("system", FITD_SYSTEMS)
    def test_hazards_four_tiers(self, system: str):
        data = _load("hazards", system)
        for tier in ("1", "2", "3", "4"):
            entries = data["tiers"].get(tier, [])
            assert len(entries) >= 2, f"{system} hazards tier {tier} has {len(entries)} entries"

    @pytest.mark.parametrize("system", FITD_SYSTEMS)
    def test_hazard_schema(self, system: str):
        data = _load("hazards", system)
        for tier, entries in data["tiers"].items():
            for entry in entries:
                assert "name" in entry
                assert "dc" in entry
                assert "damage" in entry
                assert "damage_type" in entry


# ---------------------------------------------------------------------------
# Phase 4: FITD Locations + NPCs (#13)
# ---------------------------------------------------------------------------

class TestFITDLocationsNPCs:
    """All 5 FITD systems should have NPC and location configs."""

    @pytest.mark.parametrize("system", FITD_SYSTEMS)
    def test_npcs_file_exists(self, system: str):
        data = _load("npcs", system)
        npcs = data.get("named_npcs", [])
        assert len(npcs) >= 5, f"{system} has only {len(npcs)} NPCs"

    @pytest.mark.parametrize("system", ["bitd", "sav", "bob", "cbrpnk"])
    def test_locations_file_exists(self, system: str):
        data = _load("locations", system)
        # Locations may be under various keys
        total = sum(
            len(v) for v in data.values()
            if isinstance(v, list) and v and isinstance(v[0], dict)
        )
        assert total >= 3, f"{system} has only {total} locations"

    def test_candela_locations_exist(self):
        """Candela should retain its existing rich location file."""
        data = _load("locations", "candela")
        total = sum(
            len(v) for v in data.values()
            if isinstance(v, list) and v and isinstance(v[0], dict)
        )
        assert total >= 6

    @pytest.mark.parametrize("system", FITD_SYSTEMS)
    def test_npc_schema(self, system: str):
        data = _load("npcs", system)
        for npc in data.get("named_npcs", []):
            assert "name" in npc
            assert "role" in npc


# ---------------------------------------------------------------------------
# Phase 5: STC Magic Items (#14)
# ---------------------------------------------------------------------------

class TestSTCMagicItems:
    """STC should have a magic items config with shardblades + fabrials."""

    def test_stc_magic_items_exist(self):
        data = _load("magic_items", "stc")
        items = data.get("items", [])
        assert len(items) >= 10

    def test_stc_has_shardblades(self):
        data = _load("magic_items", "stc")
        names = {i["name"] for i in data["items"]}
        assert "Sylblade" in names
        assert "Oathbringer" in names

    def test_stc_has_fabrials(self):
        data = _load("magic_items", "stc")
        names = {i["name"] for i in data["items"]}
        assert "Spanreed" in names
        assert "Soulcaster" in names

    def test_stc_magic_item_schema(self):
        data = _load("magic_items", "stc")
        for item in data["items"]:
            assert "name" in item
            assert "rarity" in item
            assert "type" in item
            assert "description" in item

    def test_content_pool_get_magic_items(self):
        from codex.forge.content_pool import ContentPool

        pool = ContentPool("stc", seed=42)
        items = pool.get_magic_items("legendary", 2)
        assert len(items) == 2
        assert all(i.rarity == "legendary" for i in items)

    def test_dnd5e_magic_items_still_work(self):
        from codex.forge.content_pool import ContentPool

        pool = ContentPool("dnd5e", seed=42)
        items = pool.get_magic_items(count=3)
        assert len(items) == 3


# ---------------------------------------------------------------------------
# Phase 6: Tables for Non-D&D Systems (#15)
# ---------------------------------------------------------------------------

class TestFITDTables:
    """Each FITD system should have at least one generation table."""

    @pytest.mark.parametrize("system", FITD_SYSTEMS)
    def test_table_file_exists(self, system: str):
        pattern = f"{system}_*.json"
        tables_dir = CONFIG / "tables"
        matches = list(tables_dir.glob(pattern))
        assert len(matches) >= 1, f"No table files for {system}"

    @pytest.mark.parametrize("system", FITD_SYSTEMS)
    def test_content_pool_loads_tables(self, system: str):
        from codex.forge.content_pool import ContentPool

        pool = ContentPool(system, seed=42)
        tables = pool.get_all_tables()
        assert len(tables) >= 1, f"ContentPool({system}) loaded 0 tables"


# ---------------------------------------------------------------------------
# Cross-system diversity
# ---------------------------------------------------------------------------

class TestModuleDiversity:
    """Verify that different systems produce different content."""

    def test_bitd_vs_sav_npcs_differ(self):
        from codex.forge.content_pool import ContentPool

        pool_bitd = ContentPool("bitd", seed=42)
        pool_sav = ContentPool("sav", seed=42)
        bitd_names = {n.name for n in pool_bitd.get_npcs(1, "", 5)}
        sav_names = {n.name for n in pool_sav.get_npcs(1, "", 5)}
        assert bitd_names != sav_names, "BitD and SaV NPCs should be different"

    def test_bitd_vs_sav_enemies_differ(self):
        from codex.forge.content_pool import ContentPool

        pool_bitd = ContentPool("bitd", seed=42)
        pool_sav = ContentPool("sav", seed=42)
        bitd_names = {e.name for e in pool_bitd.get_enemies(1, 4)}
        sav_names = {e.name for e in pool_sav.get_enemies(1, 4)}
        assert bitd_names != sav_names, "BitD and SaV enemies should be different"

    def test_stc_vs_dnd5e_magic_items_differ(self):
        from codex.forge.content_pool import ContentPool

        pool_stc = ContentPool("stc", seed=42)
        pool_dnd = ContentPool("dnd5e", seed=42)
        stc_names = {i.name for i in pool_stc.get_magic_items(count=5)}
        dnd_names = {i.name for i in pool_dnd.get_magic_items(count=5)}
        assert stc_names != dnd_names


# ---------------------------------------------------------------------------
# Backlog #62: STC Traps + Generation Tables
# ---------------------------------------------------------------------------

class TestSTCTraps:
    """STC should have Rosharan traps with 4 tiers."""

    def test_stc_traps_file_exists(self):
        data = _load("traps", "stc")
        assert "traps" in data

    def test_stc_traps_count(self):
        data = _load("traps", "stc")
        assert len(data["traps"]) >= 20

    def test_stc_traps_four_tiers(self):
        data = _load("traps", "stc")
        tiers_found = {t["tier"] for t in data["traps"]}
        assert {1, 2, 3, 4} == tiers_found

    def test_stc_traps_five_per_tier(self):
        data = _load("traps", "stc")
        from collections import Counter
        tier_counts = Counter(t["tier"] for t in data["traps"])
        for tier in (1, 2, 3, 4):
            assert tier_counts[tier] >= 5, f"Tier {tier} has {tier_counts[tier]} traps, expected >= 5"

    def test_stc_trap_schema(self):
        data = _load("traps", "stc")
        required_fields = {"name", "tier", "trigger", "dc_detect", "dc_disarm", "damage", "damage_type", "description"}
        for trap in data["traps"]:
            missing = required_fields - set(trap.keys())
            assert not missing, f"Trap '{trap.get('name', '?')}' missing fields: {missing}"

    def test_stc_trap_dc_scaling(self):
        """Higher tiers should have higher DCs."""
        data = _load("traps", "stc")
        for trap in data["traps"]:
            tier = trap["tier"]
            if tier == 1:
                assert trap["dc_detect"] <= 12
            elif tier == 4:
                assert trap["dc_detect"] >= 18

    def test_content_pool_traps(self):
        from codex.forge.content_pool import ContentPool
        pool = ContentPool("stc", seed=42)
        traps = pool.get_traps(tier=2, count=2)
        assert len(traps) == 2
        assert all(isinstance(t, dict) for t in traps)
        assert all("name" in t for t in traps)

    def test_content_pool_traps_tier4(self):
        from codex.forge.content_pool import ContentPool
        pool = ContentPool("stc", seed=42)
        traps = pool.get_traps(tier=4, count=3)
        assert len(traps) == 3


class TestSTCGenerationTables:
    """STC should have NPC, dungeon dressing, and heritage generation tables."""

    def test_stc_npc_generation_exists(self):
        fp = CONFIG / "tables" / "stc_npc_generation.json"
        assert fp.exists(), "Missing stc_npc_generation.json"
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert "heritages" in data
        assert "radiant_orders" in data
        assert len(data["heritages"]) >= 10
        assert len(data["radiant_orders"]) == 10

    def test_stc_dungeon_dressing_exists(self):
        fp = CONFIG / "tables" / "stc_dungeon_dressing.json"
        assert fp.exists(), "Missing stc_dungeon_dressing.json"
        data = json.loads(fp.read_text(encoding="utf-8"))
        expected_keys = {"room_furnishings", "wall_decorations", "floor_details", "sounds", "smells", "lighting"}
        assert expected_keys.issubset(set(data.keys()))
        for key in expected_keys:
            assert len(data[key]) >= 6, f"{key} has too few entries"

    def test_stc_heritage_generation_exists(self):
        fp = CONFIG / "tables" / "stc_heritage_generation.json"
        assert fp.exists(), "Missing stc_heritage_generation.json"
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert "cultural_greetings" in data
        assert "heritage_foods" in data
        assert "cultural_values" in data
        assert len(data["cultural_values"]) >= 10

    def test_content_pool_loads_stc_tables(self):
        from codex.forge.content_pool import ContentPool
        pool = ContentPool("stc", seed=42)
        tables = pool.get_all_tables()
        # Should have at least: roshar_generation, quest_hooks, npc_generation, dungeon_dressing, heritage_generation
        assert len(tables) >= 5, f"STC has {len(tables)} tables, expected >= 5"

    def test_stc_npc_table_has_personality_traits(self):
        fp = CONFIG / "tables" / "stc_npc_generation.json"
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert "personality_traits" in data
        assert len(data["personality_traits"]) >= 10
        assert "quirks" in data
        assert "motivations" in data

    def test_stc_heritage_table_has_superstitions(self):
        fp = CONFIG / "tables" / "stc_heritage_generation.json"
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert "cultural_superstitions" in data
        assert len(data["cultural_superstitions"]) >= 8


class TestSTCTrapsRefData:
    """Validate STC traps reference_data module."""

    def test_import_from_module(self):
        from codex.forge.reference_data.stc_traps import STC_TRAPS
        assert isinstance(STC_TRAPS, dict)
        assert "traps" in STC_TRAPS

    def test_import_from_aggregator(self):
        from codex.forge.reference_data.stc import STC_TRAPS
        assert isinstance(STC_TRAPS, dict)
        assert "traps" in STC_TRAPS

    def test_trap_count(self):
        from codex.forge.reference_data.stc_traps import STC_TRAPS
        assert len(STC_TRAPS["traps"]) == 20

    def test_all_four_tiers_present(self):
        from codex.forge.reference_data.stc_traps import STC_TRAPS
        tiers = {t["tier"] for t in STC_TRAPS["traps"]}
        assert tiers == {1, 2, 3, 4}

    def test_trap_schema_fields(self):
        from codex.forge.reference_data.stc_traps import STC_TRAPS
        required = {"name", "tier", "trigger", "dc_detect", "dc_disarm",
                     "damage", "damage_type", "description", "source"}
        for trap in STC_TRAPS["traps"]:
            missing = required - set(trap.keys())
            assert not missing, f"Trap {trap.get('name', '?')} missing: {missing}"

    def test_five_traps_per_tier(self):
        from codex.forge.reference_data.stc_traps import STC_TRAPS
        from collections import Counter
        tier_counts = Counter(t["tier"] for t in STC_TRAPS["traps"])
        for tier in (1, 2, 3, 4):
            assert tier_counts[tier] == 5, f"Tier {tier} has {tier_counts[tier]} traps"

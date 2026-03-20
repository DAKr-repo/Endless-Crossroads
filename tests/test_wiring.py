"""
tests/test_wiring.py — Content Wiring Integration Tests
=========================================================

Verifies that content data flows from config JSONs into the game engines
and module generator. Catches "dead data" — config files that exist on
disk but are never consumed.
"""

import json
import pathlib
import random

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_ROOT = PROJECT_ROOT / "config"
MODULES_ROOT = PROJECT_ROOT / "vault_maps" / "modules"


# -----------------------------------------------------------------------
# Fix 1: generate_module.py wires traps + tables + location dressing
# -----------------------------------------------------------------------


def test_generate_module_includes_traps():
    """Module generator places traps in rooms (dnd5e has trap config).

    Traps only appear in rooms without enemies, so try multiple seeds.
    """
    from scripts.generate_module import generate_module
    import tempfile
    import shutil

    found_traps = False
    for seed in [42, 100, 200, 300, 400]:
        out_dir = tempfile.mkdtemp()
        try:
            generate_module(
                template_id="investigation",
                system_id="dnd5e",
                tier=1,
                seed=seed,
                output_dir=out_dir,
            )
            for fp in pathlib.Path(out_dir).rglob("*.json"):
                if fp.name == "module_manifest.json":
                    continue
                data = json.loads(fp.read_text())
                for room in data.get("rooms", {}).values():
                    hints = room.get("content_hints", {})
                    if hints.get("traps"):
                        found_traps = True
                        break
                if found_traps:
                    break
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)
        if found_traps:
            break
    assert found_traps, "No traps found across multiple seeds/templates"


def test_generate_module_location_dressing():
    """Module generator enriches room descriptions from location pool."""
    from scripts.generate_module import generate_module
    import tempfile
    import shutil

    out_dir = tempfile.mkdtemp()
    try:
        generate_module(
            template_id="dungeon_crawl",
            system_id="dnd5e",
            tier=1,
            seed=123,
            output_dir=out_dir,
        )
        found_desc = False
        for fp in pathlib.Path(out_dir).rglob("*.json"):
            if fp.name == "module_manifest.json":
                continue
            data = json.loads(fp.read_text())
            for room in data.get("rooms", {}).values():
                hints = room.get("content_hints", {})
                desc = hints.get("description", "")
                if desc and desc != "You arrive at a new location.":
                    found_desc = True
                    break
            if found_desc:
                break
        assert found_desc, "No enriched descriptions found"
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


# -----------------------------------------------------------------------
# Fix 2: Burnwillow engine config loading
# -----------------------------------------------------------------------


def test_burnwillow_engine_config_loaders_exist():
    """Burnwillow engine exposes config loading functions."""
    from codex.games.burnwillow import engine as bw

    assert callable(getattr(bw, "_load_bw_bestiary", None))
    assert callable(getattr(bw, "_load_bw_loot", None))
    assert callable(getattr(bw, "_load_bw_hazards", None))


def test_burnwillow_config_bestiary_loads():
    """Config bestiary for burnwillow loads and has tiers."""
    from codex.games.burnwillow.engine import _load_bw_bestiary

    bestiary = _load_bw_bestiary()
    assert isinstance(bestiary, dict)
    if bestiary:  # Non-empty when config file exists
        assert any(isinstance(k, int) for k in bestiary.keys())


def test_burnwillow_config_hazards_loads():
    """Config hazards for burnwillow loads."""
    from codex.games.burnwillow.engine import _load_bw_hazards

    hazards = _load_bw_hazards()
    assert isinstance(hazards, dict)


# -----------------------------------------------------------------------
# Fix 3: DnD5e/STC engines load traps
# -----------------------------------------------------------------------


def test_dnd5e_trap_pool_loads():
    """DnD5e engine loads trap pool from config."""
    from codex.games.dnd5e import _load_trap_pool

    pool = _load_trap_pool()
    assert isinstance(pool, dict)
    # Should have entries if config/traps/dnd5e.json exists
    if (CONFIG_ROOT / "traps" / "dnd5e.json").exists():
        total = sum(len(v) for v in pool.values())
        assert total > 0, "Trap pool empty despite config file existing"


def test_dnd5e_adapter_populates_traps():
    """DnD5eAdapter.populate_room() includes traps key in content."""
    from codex.games.dnd5e import DnD5eAdapter
    from codex.spatial.map_engine import RoomNode, RoomType

    adapter = DnD5eAdapter(seed=42)
    # Create a normal room — traps can appear with or without enemies
    room = RoomNode(
        id=5, x=10, y=10, width=6, height=6,
        room_type=RoomType.NORMAL, tier=1, connections=[4, 6],
    )
    pop = adapter.populate_room(room)
    assert "traps" in pop.content  # Key always present (may be empty list)


def test_stc_trap_pool_loads():
    """STC engine loads trap pool from config (may be empty)."""
    from codex.games.stc import _load_trap_pool

    pool = _load_trap_pool()
    assert isinstance(pool, dict)


# -----------------------------------------------------------------------
# Fix 4+5: Module discovery — burnwillow + crown
# -----------------------------------------------------------------------


def test_burnwillow_modules_discoverable():
    """At least one burnwillow module exists in vault_maps/modules/."""
    found = []
    if MODULES_ROOT.is_dir():
        for entry in MODULES_ROOT.iterdir():
            if not entry.is_dir():
                continue
            mf = entry / "module_manifest.json"
            if mf.exists():
                data = json.loads(mf.read_text())
                if data.get("system_id") == "burnwillow":
                    found.append(entry.name)
    assert len(found) >= 3, f"Expected 3+ burnwillow modules, found: {found}"


def test_crown_modules_discoverable():
    """Crown campaign modules have campaign.json with required fields."""
    found = []
    if MODULES_ROOT.is_dir():
        for entry in MODULES_ROOT.iterdir():
            if not entry.is_dir():
                continue
            mf = entry / "module_manifest.json"
            campaign = entry / "campaign.json"
            if mf.exists() and campaign.exists():
                data = json.loads(mf.read_text())
                if data.get("system_id") == "crown":
                    found.append(entry.name)
    assert len(found) >= 3, f"Expected 3+ crown modules, found: {found}"


def test_play_crown_has_discover_function():
    """play_crown.py exposes _discover_crown_modules()."""
    import play_crown
    assert callable(getattr(play_crown, "_discover_crown_modules", None))


def test_crown_discover_finds_modules():
    """_discover_crown_modules() returns at least one crown module."""
    from play_crown import _discover_crown_modules

    mods = _discover_crown_modules()
    assert len(mods) >= 1, f"No crown modules discovered"
    assert all("path" in m and "name" in m for m in mods)


# -----------------------------------------------------------------------
# Fix 6: build_content.py extractors are not stubs
# -----------------------------------------------------------------------


def test_extract_loot_is_not_stub():
    """extract_loot() does real work, not just returns a skip message."""
    from scripts.build_content import extract_loot

    # Call with no PDFs — should return "no entries found", not the old stub message
    result = extract_loot("dnd5e", [], no_llm=True, force=True)
    # The key test: it should NOT return the old stub status messages
    assert "skipped (no PDF loot tables detected)" not in result.get("status", "")


def test_extract_hazards_is_not_stub():
    """extract_hazards() does real work, not just returns a skip message."""
    from scripts.build_content import extract_hazards

    result = extract_hazards("dnd5e", [], no_llm=True, force=True)
    assert "skipped (no PDF hazard tables detected)" not in result.get("status", "")


def test_extract_features_is_not_stub():
    """extract_features() does real work for dnd5e."""
    from scripts.build_content import extract_features

    result = extract_features("dnd5e", [], no_llm=True, force=True)
    assert "skipped (no PDF feature blocks detected)" not in result.get("status", "")


def test_regex_extract_loot_helper():
    """_regex_extract_loot parses gold values from text."""
    from scripts.build_content import _regex_extract_loot

    text = "Longsword of Flames\nValue: 500 gp\nRequires attunement"
    result = _regex_extract_loot(text, "dnd5e")
    assert result is not None
    assert result["name"] == "Longsword of Flames"
    assert result["value_gp"] == 500


def test_regex_extract_hazard_helper():
    """_regex_extract_hazard parses DC and damage from text."""
    from scripts.build_content import _regex_extract_hazard

    text = "Pit Trap\nDC 12 Dexterity saving throw, 2d6 piercing damage"
    result = _regex_extract_hazard(text, "dnd5e")
    assert result is not None
    assert result["name"] == "Pit Trap"
    assert result["dc"] == 12
    assert "2d6" in result["damage"]


def test_regex_extract_feature_helper():
    """_regex_extract_feature parses feature name and prerequisite."""
    from scripts.build_content import _regex_extract_feature

    text = "Agonizing Blast\nPrerequisite: eldritch blast cantrip\nWhen you cast eldritch blast..."
    result = _regex_extract_feature(text)
    assert result is not None
    assert result["name"] == "Agonizing Blast"
    assert "eldritch blast" in result["prerequisite"]


# -----------------------------------------------------------------------
# Cross-system: ContentPool tables flow into generate_module
# -----------------------------------------------------------------------


def test_content_pool_tables_accessible():
    """ContentPool loads tables for dnd5e."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("dnd5e", seed=42)
    tables = pool.get_all_tables()
    assert len(tables) >= 5
    # dungeon_dressing should exist for dnd5e
    dressing = pool.get_table("dungeon_dressing")
    assert dressing is not None


def test_content_pool_traps_accessible():
    """ContentPool loads traps for dnd5e."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("dnd5e", seed=42)
    traps = pool.get_traps(tier=1, count=2)
    assert len(traps) == 2
    assert all(isinstance(t, dict) for t in traps)


# -----------------------------------------------------------------------
# Wiring: generate_module + enrich_module importable from main
# -----------------------------------------------------------------------


def test_generate_module_importable_from_scripts():
    """scripts.generate_module is importable as a package."""
    from scripts.generate_module import generate_module, list_templates
    assert callable(generate_module)
    templates = list_templates()
    assert len(templates) >= 5


def test_enrich_module_importable_from_scripts():
    """scripts.enrich_module is importable as a package."""
    from scripts.enrich_module import enrich_module
    assert callable(enrich_module)


def test_generate_module_all_systems():
    """generate_module produces valid output for every system with content data."""
    from scripts.generate_module import generate_module
    import tempfile
    import shutil

    systems = ["bitd", "sav", "bob", "candela", "dnd5e", "stc", "burnwillow"]
    for system_id in systems:
        out_dir = tempfile.mkdtemp()
        try:
            result = generate_module(
                template_id="heist",
                system_id=system_id,
                tier=1,
                seed=777,
                output_dir=out_dir,
            )
            manifest = pathlib.Path(result) / "module_manifest.json"
            assert manifest.exists(), f"{system_id}: no manifest generated"
            data = json.loads(manifest.read_text())
            assert data["system_id"] == system_id
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


def test_dm_tools_menu_has_generate_enrich():
    """codex_agent_main.py has run_module_generator and run_module_enrichment."""
    import codex_agent_main as cam
    assert callable(getattr(cam, "run_module_generator", None))
    assert callable(getattr(cam, "run_module_enrichment", None))

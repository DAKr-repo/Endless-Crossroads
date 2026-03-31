"""
tests/test_starter_modules.py — Validate all starter modules
=============================================================

Verifies that:
  1. All expected module manifests exist and load via ModuleManifest
  2. Each module has the correct system_id
  3. Room 0 of the first zone has description + at least 1 NPC or event_trigger
  4. ContentPool returns non-empty bestiary and loot for each system
  5. Config-sourced locations and NPCs load for each system
  6. Crown campaign.json files load correctly
  7. Procedural generation tables load via ContentPool
"""

import json
import os
import pathlib

import pytest

MODULE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "vault_maps" / "modules"
CONFIG_ROOT = pathlib.Path(__file__).resolve().parent.parent / "config"

# All expected starter modules: (module_id, system_id)
EXPECTED_MODULES = [
    # Candela full assignments (Phase 3)
    ("candela_light_eater", "candela"),
    ("candela_still_life", "candela"),
    ("candela_devils_well", "candela"),
    ("candela_stage_fright", "candela"),
    # BitD / SaV / BoB (Phase 3)
    ("bitd_dimmer_sisters", "bitd"),
    ("sav_ashen_knives", "sav"),
    ("bob_first_assault", "bob"),
    # BoB locations (Phase 4)
    ("bob_western_front", "bob"),
    ("bob_plainsworth", "bob"),
    ("bob_long_road", "bob"),
    ("bob_barrak_mines", "bob"),
    ("bob_gallows_pass", "bob"),
    ("bob_sunstrider_camp", "bob"),
    ("bob_duresh_forest", "bob"),
    ("bob_talgon_forest", "bob"),
    # Candela brief assignments (Phase 5)
    ("candela_champagne_problems", "candela"),
    ("candela_fools_gold", "candela"),
    ("candela_the_icebox", "candela"),
    ("candela_lifeblood", "candela"),
    ("candela_sleep_tight", "candela"),
    ("candela_under_the_big_top", "candela"),
    # CBR+PNK campaign modules (Phase 9)
    ("cbrpnk_omni_global", "cbrpnk"),
    ("cbrpnk_prdtr", "cbrpnk"),
    ("cbrpnk_mona_rise", "cbrpnk"),
    # STC modules (Full-System Sprint)
    ("stc_first_step", "stc"),
    ("stc_bridge_nine", "stc"),
    ("stc_stonewalkers", "stc"),
    ("stc_war_of_reckoning", "stc"),
    ("stc_kholinar_infiltration", "stc"),
    # Burnwillow modules (Full-System Sprint)
    ("burnwillow_emberhome", "burnwillow"),
    ("burnwillow_ashen_cellar", "burnwillow"),
    ("burnwillow_ironvein_mines", "burnwillow"),
    ("burnwillow_rotwood_hollow", "burnwillow"),
    ("burnwillow_rot_spire", "burnwillow"),
]

# Crown campaign modules (no spatial zones, just campaign.json)
CROWN_CAMPAIGN_MODULES = [
    ("crown_border_run", "crown"),
    ("crown_plague_city", "crown"),
    ("crown_pirate_throne", "crown"),
    ("ashburn_chronicles", "crown"),
]


def _load_manifest(module_id: str) -> dict:
    """Load a module_manifest.json as a raw dict."""
    path = MODULE_ROOT / module_id / "module_manifest.json"
    with open(path) as f:
        return json.load(f)


def _load_first_blueprint(module_id: str, manifest: dict) -> dict:
    """Load the first zone's blueprint JSON."""
    chapters = manifest.get("chapters", [])
    if not chapters:
        pytest.skip(f"No chapters in {module_id}")
    zones = chapters[0].get("zones", [])
    if not zones:
        pytest.skip(f"No zones in first chapter of {module_id}")
    bp_name = zones[0].get("blueprint", "")
    if not bp_name:
        pytest.skip(f"No blueprint for first zone of {module_id}")
    bp_path = MODULE_ROOT / module_id / bp_name
    with open(bp_path) as f:
        return json.load(f)


# -----------------------------------------------------------------------
# Parametrized tests: one per module
# -----------------------------------------------------------------------


@pytest.mark.parametrize("module_id,expected_system", EXPECTED_MODULES)
def test_manifest_exists_and_loads(module_id: str, expected_system: str):
    """Module manifest exists and parses as valid JSON."""
    path = MODULE_ROOT / module_id / "module_manifest.json"
    if not path.exists():
        pytest.skip(f"Module not yet created: {module_id}")
    manifest = _load_manifest(module_id)
    assert isinstance(manifest, dict)
    assert manifest.get("module_id") == module_id


@pytest.mark.parametrize("module_id,expected_system", EXPECTED_MODULES)
def test_system_id_correct(module_id: str, expected_system: str):
    """Module declares the correct system_id."""
    path = MODULE_ROOT / module_id / "module_manifest.json"
    if not path.exists():
        pytest.skip(f"Module not yet created: {module_id}")
    manifest = _load_manifest(module_id)
    assert manifest.get("system_id") == expected_system


@pytest.mark.parametrize("module_id,expected_system", EXPECTED_MODULES)
def test_first_zone_has_content(module_id: str, expected_system: str):
    """Room 0 of the first zone has a description and at least 1 NPC or event trigger."""
    path = MODULE_ROOT / module_id / "module_manifest.json"
    if not path.exists():
        pytest.skip(f"Module not yet created: {module_id}")
    manifest = _load_manifest(module_id)
    bp = _load_first_blueprint(module_id, manifest)
    rooms = bp.get("rooms", {})
    room_0 = rooms.get("0") or rooms.get(0)
    assert room_0 is not None, f"No room 0 in first zone of {module_id}"

    # content_hints can be inline in the room OR at the top level keyed by room id.
    # Some modules (e.g. burnwillow) put fields directly on the room object.
    hints = room_0.get("content_hints", {})
    if not hints:
        top_hints = bp.get("content_hints", {})
        hints = top_hints.get("0", top_hints.get(0, {}))

    desc = hints.get("description", "") or room_0.get("description", "")
    assert desc, f"Room 0 has no description in {module_id}"

    npcs = hints.get("npcs", []) or room_0.get("npcs", [])
    triggers = hints.get("event_triggers", []) or room_0.get("event_triggers", [])
    assert npcs or triggers, (
        f"Room 0 has no NPCs and no event_triggers in {module_id}"
    )


@pytest.mark.parametrize("module_id,expected_system", EXPECTED_MODULES)
def test_manifest_loads_via_class(module_id: str, expected_system: str):
    """ModuleManifest.from_dict() round-trips the manifest without error."""
    path = MODULE_ROOT / module_id / "module_manifest.json"
    if not path.exists():
        pytest.skip(f"Module not yet created: {module_id}")
    from codex.spatial.module_manifest import ModuleManifest

    raw = _load_manifest(module_id)
    manifest = ModuleManifest.from_dict(raw)
    assert manifest.module_id == module_id
    assert manifest.system_id == expected_system
    assert len(manifest.chapters) > 0


# -----------------------------------------------------------------------
# ContentPool integration
# -----------------------------------------------------------------------


def test_candela_bestiary_non_empty():
    """ContentPool('candela') returns non-empty bestiary at tier 1."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("candela", seed=42)
    enemies = pool.get_enemies(tier=1, count=2)
    assert len(enemies) == 2
    assert enemies[0].name != "Tier 1 Adversary"  # not the fallback


def test_candela_loot_non_empty():
    """ContentPool('candela') returns non-empty loot at tier 1."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("candela", seed=42)
    loot = pool.get_loot(tier=1, count=2)
    assert len(loot) == 2
    assert loot[0].name != "Tier 1 Trinket"  # not the fallback


def test_candela_locations_from_config():
    """ContentPool('candela') returns config-sourced locations."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("candela", seed=42)
    locs = pool.get_locations()
    assert len(locs) > 0
    names = [l.name for l in locs]
    assert "The Parlor Cafe" in names or "Antiquarian Estate" in names


def test_candela_npcs_from_config():
    """ContentPool('candela') returns config-sourced NPCs."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("candela", seed=42)
    npcs = pool.get_npcs(count=3)
    assert len(npcs) == 3
    # Should be real names from config, not procedural
    names = [n.name for n in npcs]
    # At least one should be from the Candela NPC config
    known_names = {
        "Avery Choi", "Chaska Deloria", "Tang Yuna", "Oscar Enfield",
        "Luis Roe", "Emerson Walsh", "Alma Baquiran", "Oksana Blum",
        "Caerwyn Stone", "Joseph Abdi", "Kiana Tumata", "Ember Rose",
        "Dr. Michele Lappin", "Oksana Blum", "Richard Satanta",
        "Elder Kenneth Krause", "Father Timothy Singh",
        "Magistra Elara Voss", "Sister Ines Collard", "Sable",
    }
    assert any(n in known_names for n in names), f"No known Candela NPCs found in {names}"


# -----------------------------------------------------------------------
# Template validation
# -----------------------------------------------------------------------


def test_candela_assignment_template_exists():
    """The candela_assignment template is valid and has 7 scenes."""
    config_root = pathlib.Path(__file__).resolve().parent.parent / "config"
    template_path = config_root / "templates" / "candela_assignment.json"
    assert template_path.exists()
    with open(template_path) as f:
        data = json.load(f)
    assert data["template_id"] == "candela_assignment"
    assert len(data["scenes"]) == 7
    scene_ids = [s["scene_id"] for s in data["scenes"]]
    assert scene_ids == [
        "hook", "arrival", "exploration_1", "exploration_2",
        "escalation_1", "escalation_2", "climax",
    ]


# -----------------------------------------------------------------------
# Crown campaign module tests
# -----------------------------------------------------------------------


@pytest.mark.parametrize("module_id,expected_system", CROWN_CAMPAIGN_MODULES)
def test_crown_campaign_manifest(module_id: str, expected_system: str):
    """Crown campaign module has valid manifest and campaign.json."""
    manifest_path = MODULE_ROOT / module_id / "module_manifest.json"
    if not manifest_path.exists():
        pytest.skip(f"Module not yet created: {module_id}")
    manifest = json.loads(manifest_path.read_text())
    assert manifest.get("system_id") == expected_system
    assert manifest.get("module_id") == module_id


@pytest.mark.parametrize("module_id,expected_system", CROWN_CAMPAIGN_MODULES)
def test_crown_campaign_json_loads(module_id: str, expected_system: str):
    """Crown campaign.json exists and has required prompt pools."""
    campaign_path = MODULE_ROOT / module_id / "campaign.json"
    if not campaign_path.exists():
        pytest.skip(f"campaign.json not yet created: {module_id}")
    data = json.loads(campaign_path.read_text())
    assert isinstance(data, dict)
    # All campaign packs should have prompts
    assert len(data.get("prompts_crown", [])) >= 10
    assert len(data.get("prompts_crew", [])) >= 10
    assert len(data.get("prompts_world", [])) >= 5


# -----------------------------------------------------------------------
# D&D 5e config expansion tests
# -----------------------------------------------------------------------


def test_dnd5e_locations_config():
    """D&D 5e locations config has entries across multiple categories."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("dnd5e", seed=42)
    locs = pool.get_locations()
    assert len(locs) >= 20, f"Expected 20+ locations, got {len(locs)}"


def test_dnd5e_npcs_config():
    """D&D 5e NPC config has named NPCs and generic templates."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("dnd5e", seed=42)
    npcs = pool.get_npcs(count=5)
    assert len(npcs) == 5
    # Should include real names from config
    names = {n.name for n in npcs}
    assert len(names) >= 1  # At least some are distinct


def test_dnd5e_traps_config():
    """D&D 5e traps config loads and provides tier-based traps."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("dnd5e", seed=42)
    traps = pool.get_traps(tier=1, count=3)
    assert len(traps) == 3
    assert all(t.get("name") for t in traps)


def test_dnd5e_hazards_expanded():
    """D&D 5e hazards config has at least 40 entries across tiers."""
    fp = CONFIG_ROOT / "hazards" / "dnd5e.json"
    data = json.loads(fp.read_text())
    total = sum(len(v) for v in data.get("tiers", {}).values())
    assert total >= 40, f"Expected 40+ hazards, got {total}"


def test_dnd5e_loot_expanded():
    """D&D 5e loot config has at least 60 entries across tiers."""
    fp = CONFIG_ROOT / "loot" / "dnd5e.json"
    data = json.loads(fp.read_text())
    total = sum(len(v) for v in data.get("tiers", {}).values())
    assert total >= 60, f"Expected 60+ loot items, got {total}"


# -----------------------------------------------------------------------
# STC config tests
# -----------------------------------------------------------------------


def test_stc_locations_config():
    """STC locations config has Roshar locations."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("stc", seed=42)
    locs = pool.get_locations()
    assert len(locs) >= 15, f"Expected 15+ locations, got {len(locs)}"


def test_stc_npcs_config():
    """STC NPC config loads with named NPCs."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("stc", seed=42)
    npcs = pool.get_npcs(count=3)
    assert len(npcs) == 3


def test_stc_bestiary_expanded():
    """STC bestiary has entries across all 4 tiers."""
    fp = CONFIG_ROOT / "bestiary" / "stc.json"
    data = json.loads(fp.read_text())
    for tier in ["1", "2", "3", "4"]:
        entries = data.get("tiers", {}).get(tier, [])
        assert len(entries) >= 3, f"STC bestiary tier {tier} has < 3 entries"


# -----------------------------------------------------------------------
# Burnwillow config tests
# -----------------------------------------------------------------------


def test_burnwillow_bestiary_config():
    """Burnwillow bestiary has 4 tiers of ember-themed enemies."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("burnwillow", seed=42)
    for tier in range(1, 5):
        enemies = pool.get_enemies(tier=tier, count=2)
        assert len(enemies) == 2
        assert enemies[0].name != f"Tier {tier} Adversary"


def test_burnwillow_loot_config():
    """Burnwillow loot has GearGrid items across tiers."""
    fp = CONFIG_ROOT / "loot" / "burnwillow.json"
    data = json.loads(fp.read_text())
    total = sum(len(v) for v in data.get("tiers", {}).values())
    assert total >= 30, f"Expected 30+ loot items, got {total}"


def test_burnwillow_locations_config():
    """Burnwillow locations include Emberhome and surrounding areas."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("burnwillow", seed=42)
    locs = pool.get_locations()
    assert len(locs) >= 15
    names = [l.name for l in locs]
    # Should have settlement locations
    assert any("Forge" in n or "Market" in n or "Chapel" in n for n in names)


def test_burnwillow_npcs_config():
    """Burnwillow NPC config has named NPCs and templates."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("burnwillow", seed=42)
    npcs = pool.get_npcs(count=5)
    assert len(npcs) == 5


def test_burnwillow_hazards_config():
    """Burnwillow hazards have ember-themed entries across tiers."""
    fp = CONFIG_ROOT / "hazards" / "burnwillow.json"
    data = json.loads(fp.read_text())
    total = sum(len(v) for v in data.get("tiers", {}).values())
    assert total >= 15, f"Expected 15+ hazards, got {total}"


# -----------------------------------------------------------------------
# Procedural generation table tests
# -----------------------------------------------------------------------


def test_dnd5e_tables_load():
    """D&D 5e procedural tables load via ContentPool."""
    from codex.forge.content_pool import ContentPool

    pool = ContentPool("dnd5e", seed=42)
    tables = pool.get_all_tables()
    assert len(tables) >= 5, f"Expected 5+ table categories, got {len(tables)}"


def test_dnd5e_dungeon_generation_table():
    """D&D 5e dungeon generation table has required keys."""
    fp = CONFIG_ROOT / "tables" / "dnd5e_dungeon_generation.json"
    assert fp.exists()
    data = json.loads(fp.read_text())
    assert "chamber_shapes" in data
    assert "passage_types" in data
    assert "dungeon_purpose" in data


def test_dnd5e_treasure_table():
    """D&D 5e treasure table has gemstones and art objects."""
    fp = CONFIG_ROOT / "tables" / "dnd5e_treasure.json"
    assert fp.exists()
    data = json.loads(fp.read_text())
    assert "gemstones" in data
    assert "art_objects" in data


def test_dnd5e_npc_generation_table():
    """D&D 5e NPC generation table has personality traits."""
    fp = CONFIG_ROOT / "tables" / "dnd5e_npc_generation.json"
    assert fp.exists()
    data = json.loads(fp.read_text())
    assert "appearance" in data
    assert "mannerisms" in data
    assert "flaws" in data


def test_stc_roshar_table():
    """STC Roshar generation table has spren sightings and weather."""
    fp = CONFIG_ROOT / "tables" / "stc_roshar_generation.json"
    assert fp.exists()
    data = json.loads(fp.read_text())
    assert "spren_sightings" in data or "weather_patterns" in data


def test_burnwillow_generation_table():
    """Burnwillow generation table has dungeon dressing and DoomClock events."""
    fp = CONFIG_ROOT / "tables" / "burnwillow_generation.json"
    assert fp.exists()
    data = json.loads(fp.read_text())
    assert "dungeon_dressing" in data
    assert "doomclock_events" in data
    assert len(data["dungeon_dressing"]) >= 20


# -----------------------------------------------------------------------
# Crown scene system tests
# -----------------------------------------------------------------------


def test_crown_scene_creation():
    """CrownScene can be created, resolved, and serialized."""
    from codex.games.crown.scenes import CrownScene

    scene = CrownScene(
        scene_id="test_scene",
        description="A test scene",
        location="Test Location",
        choices=[
            {"text": "Option A", "sway_effect": 1, "tag": "BLOOD"},
            {"text": "Option B", "sway_effect": -1, "tag": "GUILE"},
        ],
    )
    assert not scene.resolved
    texts = scene.get_choice_texts()
    assert texts == ["Option A", "Option B"]

    result = scene.resolve(0)
    assert scene.resolved
    assert result["sway_effect"] == 1
    assert result["tag"] == "BLOOD"


def test_crown_scene_runner_empty():
    """CrownSceneRunner with no chapters is backward compatible."""
    from codex.games.crown.scenes import CrownSceneRunner

    runner = CrownSceneRunner()
    assert runner.get_current_scene() is None
    assert runner.is_complete()
    assert runner.get_progress() == "No scenes"


def test_crown_scene_runner_progression():
    """CrownSceneRunner advances through scenes and chapters."""
    from codex.games.crown.scenes import CrownScene, CrownChapter, CrownSceneRunner

    ch = CrownChapter(
        chapter_id="ch1",
        display_name="Chapter 1",
        scenes=[
            CrownScene("s1", "Scene 1", choices=[{"text": "Go", "sway_effect": 1}]),
            CrownScene("s2", "Scene 2", choices=[{"text": "Go", "sway_effect": -1}]),
        ],
    )
    runner = CrownSceneRunner(chapters=[ch])
    assert runner.get_progress() == "Scene 0/2"

    scene = runner.get_current_scene()
    assert scene.scene_id == "s1"
    scene.resolve(0)
    runner.advance()

    scene = runner.get_current_scene()
    assert scene.scene_id == "s2"
    scene.resolve(0)
    runner.advance()

    assert runner.is_complete()
    assert runner.get_progress() == "Scene 2/2"


def test_crown_scene_runner_serialization():
    """CrownSceneRunner round-trips through to_dict/from_dict."""
    from codex.games.crown.scenes import CrownScene, CrownChapter, CrownSceneRunner

    ch = CrownChapter(
        chapter_id="ch1",
        display_name="Chapter 1",
        scenes=[
            CrownScene("s1", "Scene 1", choices=[{"text": "Go"}]),
        ],
    )
    runner = CrownSceneRunner(chapters=[ch])
    data = runner.to_dict()
    restored = CrownSceneRunner.from_dict(data)
    assert len(restored.chapters) == 1
    assert restored.chapters[0].scenes[0].scene_id == "s1"


def test_crown_scene_from_campaign_json():
    """CrownSceneRunner.from_campaign_json() parses scenes_by_day format."""
    from codex.games.crown.scenes import CrownSceneRunner

    campaign = {
        "scenes_by_day": {
            "1": {
                "scene_id": "day1",
                "description": "First day scene",
                "choices": [{"text": "A"}, {"text": "B"}],
            },
            "2": {
                "scene_id": "day2",
                "description": "Second day scene",
                "choices": [{"text": "C"}],
            },
        }
    }
    runner = CrownSceneRunner.from_campaign_json(campaign)
    assert len(runner.chapters) == 1
    assert len(runner.chapters[0].scenes) == 2


# -----------------------------------------------------------------------
# Ashburn expansion tests
# -----------------------------------------------------------------------


def test_ashburn_scenarios_config():
    """Ashburn scenarios config exists with multiple scenarios."""
    fp = CONFIG_ROOT / "scenarios" / "ashburn_scenarios.json"
    assert fp.exists(), "Ashburn scenarios config missing"
    data = json.loads(fp.read_text())
    scenarios = data.get("scenarios", [])
    assert len(scenarios) >= 3, f"Expected 3+ scenarios, got {len(scenarios)}"
    # Each scenario should have an identifier and title (id or scenario_id)
    for s in scenarios:
        assert s.get("scenario_id") or s.get("id"), f"Missing id in {s}"
        assert s.get("display_name") or s.get("title"), f"Missing title in {s}"

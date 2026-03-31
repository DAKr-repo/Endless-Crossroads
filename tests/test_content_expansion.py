"""
tests/test_content_expansion.py — WO-V70.0 Content Expansion Tests
====================================================================
Tests for:
  - Travel terrain JSON schema validation (new + expanded files)
  - FITD bestiary config schema (bitd, bob, cbrpnk, crown)
  - FITD loot config schema (bitd, bob, cbrpnk, crown)
  - Graveyard schema fields
  - ModuleManifest source_type field round-trip
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_DIR = PROJECT_ROOT / "config"
TRAVEL_DIR = CONFIG_DIR / "travel"
BESTIARY_DIR = CONFIG_DIR / "bestiary"
LOOT_DIR = CONFIG_DIR / "loot"


# =============================================================================
# Helpers
# =============================================================================

def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _assert_terrain_schema(data: dict, terrain_name: str) -> None:
    """Assert that a terrain dict has the required structural keys."""
    assert "terrain_type" in data, f"{terrain_name}: missing terrain_type"
    assert "events" in data, f"{terrain_name}: missing events"
    events = data["events"]
    assert isinstance(events, dict), f"{terrain_name}: events must be a dict"
    assert len(events) >= 1, f"{terrain_name}: must have at least 1 tier"
    for tier_key, tier_events in events.items():
        assert isinstance(tier_events, list), f"{terrain_name}[{tier_key}]: tier must be a list"
        for ev in tier_events:
            assert "id" in ev, f"{terrain_name}[{tier_key}]: event missing 'id'"
            assert "type" in ev, f"{terrain_name}[{tier_key}]: event missing 'type'"
            assert "title" in ev, f"{terrain_name}[{tier_key}]: event missing 'title'"
            assert "dc" in ev, f"{terrain_name}[{tier_key}]: event missing 'dc'"


def _assert_has_4_tiers(data: dict, label: str) -> None:
    events = data.get("events", data.get("tiers", {}))
    tier_keys = set(str(k) for k in events.keys())
    for expected in ("tier_1", "tier_2", "tier_3", "tier_4"):
        assert expected in tier_keys, f"{label}: missing {expected} (found {tier_keys})"


def _assert_fitd_bestiary_schema(data: dict, system: str) -> None:
    assert "version" in data, f"{system} bestiary: missing version"
    assert "tiers" in data, f"{system} bestiary: missing tiers"
    tiers = data["tiers"]
    for tier_key, entries in tiers.items():
        assert isinstance(entries, list), f"{system} bestiary[{tier_key}]: must be list"
        assert len(entries) >= 1, f"{system} bestiary[{tier_key}]: must have at least 1 entry"
        for e in entries:
            assert "name" in e, f"{system} bestiary[{tier_key}]: entry missing 'name'"
            assert "threat_level" in e, f"{system} bestiary[{tier_key}]: entry '{e.get('name')}' missing 'threat_level'"
            assert "capabilities" in e, f"{system} bestiary[{tier_key}]: entry '{e.get('name')}' missing 'capabilities'"


def _assert_fitd_loot_schema(data: dict, system: str) -> None:
    assert "version" in data, f"{system} loot: missing version"
    assert "tiers" in data, f"{system} loot: missing tiers"
    tiers = data["tiers"]
    for tier_key, entries in tiers.items():
        assert isinstance(entries, list), f"{system} loot[{tier_key}]: must be list"
        assert len(entries) >= 1, f"{system} loot[{tier_key}]: must have at least 1 entry"
        for e in entries:
            assert "name" in e, f"{system} loot[{tier_key}]: entry missing 'name'"
            assert "rarity" in e, f"{system} loot[{tier_key}]: entry '{e.get('name')}' missing 'rarity'"


# =============================================================================
# Part 1: Travel Terrain Schema
# =============================================================================

class TestTerrainSchema:
    """Validate JSON schema for all travel terrain files."""

    def test_swamp_has_4_tiers(self):
        data = _load_json(TRAVEL_DIR / "swamp.json")
        _assert_terrain_schema(data, "swamp")
        _assert_has_4_tiers(data, "swamp")

    def test_urban_has_4_tiers(self):
        data = _load_json(TRAVEL_DIR / "urban.json")
        _assert_terrain_schema(data, "urban")
        _assert_has_4_tiers(data, "urban")

    def test_desert_exists_and_has_4_tiers(self):
        data = _load_json(TRAVEL_DIR / "desert.json")
        assert data["terrain_type"] == "desert"
        _assert_terrain_schema(data, "desert")
        _assert_has_4_tiers(data, "desert")

    def test_arctic_exists_and_has_4_tiers(self):
        data = _load_json(TRAVEL_DIR / "arctic.json")
        assert data["terrain_type"] == "arctic"
        _assert_terrain_schema(data, "arctic")
        _assert_has_4_tiers(data, "arctic")

    def test_jungle_exists_and_has_4_tiers(self):
        data = _load_json(TRAVEL_DIR / "jungle.json")
        assert data["terrain_type"] == "jungle"
        _assert_terrain_schema(data, "jungle")
        _assert_has_4_tiers(data, "jungle")

    def test_plains_exists_and_has_4_tiers(self):
        data = _load_json(TRAVEL_DIR / "plains.json")
        assert data["terrain_type"] == "plains"
        _assert_terrain_schema(data, "plains")
        _assert_has_4_tiers(data, "plains")

    def test_desert_tier1_has_sandstorm(self):
        """Verify the T1 sandstorm event exists with a seek-shelter mechanic."""
        data = _load_json(TRAVEL_DIR / "desert.json")
        tier1 = data["events"]["tier_1"]
        ids = [e["id"] for e in tier1]
        assert "sandstorm" in ids

    def test_arctic_tier2_has_ice_bridge(self):
        data = _load_json(TRAVEL_DIR / "arctic.json")
        tier2 = data["events"]["tier_2"]
        ids = [e["id"] for e in tier2]
        assert "ice_bridge" in ids

    def test_jungle_tier4_is_multiphase(self):
        """T4 yuan-ti entry should have notes about multi-phase."""
        data = _load_json(TRAVEL_DIR / "jungle.json")
        tier4 = data["events"]["tier_4"]
        assert len(tier4) >= 1
        entry = tier4[0]
        assert "notes" in entry
        assert "multi-phase" in entry["notes"].lower() or "phase" in entry["notes"].lower()

    def test_all_new_terrain_valid_event_types(self):
        """All events must use one of the three valid type values."""
        valid_types = {"skill_challenge", "combat", "discovery"}
        for fname in ("desert.json", "arctic.json", "jungle.json", "plains.json"):
            data = _load_json(TRAVEL_DIR / fname)
            for tier_key, events in data["events"].items():
                for ev in events:
                    assert ev["type"] in valid_types, (
                        f"{fname}[{tier_key}] event '{ev['id']}' has invalid type '{ev['type']}'"
                    )

    def test_existing_terrain_files_still_valid(self):
        """Sanity: original terrain files haven't been accidentally broken."""
        for fname in ("forest.json", "mountain.json", "road.json", "coast.json", "underdark.json"):
            path = TRAVEL_DIR / fname
            if path.exists():
                data = _load_json(path)
                _assert_terrain_schema(data, fname)


# =============================================================================
# Part 2: FITD Bestiary Configs
# =============================================================================

class TestFITDBestiaryConfigs:
    """Validate schema for FITD-format bestiary configs."""

    def test_bitd_bestiary_loads(self):
        data = _load_json(BESTIARY_DIR / "bitd.json")
        _assert_fitd_bestiary_schema(data, "bitd")

    def test_bob_bestiary_loads(self):
        data = _load_json(BESTIARY_DIR / "bob.json")
        _assert_fitd_bestiary_schema(data, "bob")

    def test_cbrpnk_bestiary_loads(self):
        data = _load_json(BESTIARY_DIR / "cbrpnk.json")
        _assert_fitd_bestiary_schema(data, "cbrpnk")

    def test_crown_bestiary_loads(self):
        data = _load_json(BESTIARY_DIR / "crown.json")
        _assert_fitd_bestiary_schema(data, "crown")

    def test_bitd_bestiary_has_4_tiers(self):
        data = _load_json(BESTIARY_DIR / "bitd.json")
        tiers = data["tiers"]
        for t in ("1", "2", "3", "4"):
            assert t in tiers, f"bitd bestiary missing tier {t}"

    def test_bob_bestiary_has_campaign_phase(self):
        """BoB entries should include campaign_phase field."""
        data = _load_json(BESTIARY_DIR / "bob.json")
        tier1 = data["tiers"]["1"]
        for entry in tier1:
            assert "campaign_phase" in entry, f"BoB entry '{entry.get('name')}' missing campaign_phase"

    def test_cbrpnk_bestiary_has_heat_threshold(self):
        """CBR+PNK entries should include heat_threshold field."""
        data = _load_json(BESTIARY_DIR / "cbrpnk.json")
        tier1 = data["tiers"]["1"]
        for entry in tier1:
            assert "heat_threshold" in entry, f"cbrpnk entry '{entry.get('name')}' missing heat_threshold"

    def test_crown_bestiary_has_sway(self):
        """Crown entries should include sway field."""
        data = _load_json(BESTIARY_DIR / "crown.json")
        tier1 = data["tiers"]["1"]
        for entry in tier1:
            assert "sway" in entry, f"Crown entry '{entry.get('name')}' missing sway"

    def test_fitd_bestiary_min_5_entries_per_tier_1_2(self):
        """Each FITD bestiary should have 5+ entries in tiers 1 and 2."""
        for system in ("bitd", "bob", "cbrpnk", "crown"):
            data = _load_json(BESTIARY_DIR / f"{system}.json")
            for t in ("1", "2"):
                count = len(data["tiers"].get(t, []))
                assert count >= 5, f"{system} bestiary tier {t} has only {count} entries (need 5+)"

    def test_fitd_no_dnd_ac_hp_fields(self):
        """FITD bestiaries must NOT have D&D-style base_ac/base_hp/base_atk fields."""
        for system in ("bitd", "bob", "cbrpnk", "crown"):
            data = _load_json(BESTIARY_DIR / f"{system}.json")
            for tier_key, entries in data["tiers"].items():
                for e in entries:
                    for forbidden in ("base_ac", "base_hp", "base_atk", "base_dmg", "cr"):
                        assert forbidden not in e, (
                            f"{system} bestiary[{tier_key}] '{e.get('name')}' has forbidden D&D field '{forbidden}'"
                        )


# =============================================================================
# Part 3: FITD Loot Configs
# =============================================================================

class TestFITDLootConfigs:
    """Validate schema for FITD-format loot configs."""

    def test_bitd_loot_loads(self):
        data = _load_json(LOOT_DIR / "bitd.json")
        _assert_fitd_loot_schema(data, "bitd")

    def test_bob_loot_loads(self):
        data = _load_json(LOOT_DIR / "bob.json")
        _assert_fitd_loot_schema(data, "bob")

    def test_cbrpnk_loot_loads(self):
        data = _load_json(LOOT_DIR / "cbrpnk.json")
        _assert_fitd_loot_schema(data, "cbrpnk")

    def test_crown_loot_loads(self):
        data = _load_json(LOOT_DIR / "crown.json")
        _assert_fitd_loot_schema(data, "crown")

    def test_bitd_loot_has_quality_field(self):
        data = _load_json(LOOT_DIR / "bitd.json")
        tier1 = data["tiers"]["1"]
        for entry in tier1:
            assert "quality" in entry, f"bitd loot '{entry.get('name')}' missing quality"

    def test_bob_loot_has_supply_value(self):
        data = _load_json(LOOT_DIR / "bob.json")
        tier1 = data["tiers"]["1"]
        for entry in tier1:
            assert "supply_value" in entry, f"bob loot '{entry.get('name')}' missing supply_value"

    def test_cbrpnk_loot_has_cred_value(self):
        data = _load_json(LOOT_DIR / "cbrpnk.json")
        tier1 = data["tiers"]["1"]
        for entry in tier1:
            assert "value_cred" in entry, f"cbrpnk loot '{entry.get('name')}' missing value_cred"

    def test_crown_loot_has_sway_value(self):
        data = _load_json(LOOT_DIR / "crown.json")
        tier1 = data["tiers"]["1"]
        for entry in tier1:
            assert "sway_value" in entry, f"crown loot '{entry.get('name')}' missing sway_value"

    def test_all_fitd_loot_have_4_tiers(self):
        for system in ("bitd", "bob", "cbrpnk", "crown"):
            data = _load_json(LOOT_DIR / f"{system}.json")
            tiers = data["tiers"]
            for t in ("1", "2", "3", "4"):
                assert t in tiers, f"{system} loot missing tier {t}"


# =============================================================================
# Part 4: Graveyard Schema
# =============================================================================

class TestGraveyardSchema:
    """Validate the rewritten graveyard schema."""

    def setup_method(self):
        self.data = _load_json(
            PROJECT_ROOT / "config" / "systems" / "rules_GRAVEYARD.json"
        )

    def test_graveyard_has_storage_format(self):
        assert "storage_format" in self.data

    def test_graveyard_has_supported_systems(self):
        assert "supported_systems" in self.data
        systems = self.data["supported_systems"]
        assert isinstance(systems, list)
        assert len(systems) >= 1

    def test_graveyard_supported_systems_includes_core(self):
        systems = self.data["supported_systems"]
        for expected in ("burnwillow", "dnd5e", "stc", "bitd"):
            assert expected in systems, f"graveyard missing supported system '{expected}'"

    def test_graveyard_has_fields_section(self):
        assert "fields" in self.data
        fields = self.data["fields"]
        assert isinstance(fields, dict)

    def test_graveyard_required_fields_present(self):
        fields = self.data["fields"]
        for required in ("name", "system", "cause_of_death", "date", "achievements"):
            assert required in fields, f"graveyard fields missing '{required}'"

    def test_graveyard_no_placeholder_class_names(self):
        raw = json.dumps(self.data)
        assert "Character Class A" not in raw
        assert "Character Class B" not in raw
        assert "Playbook X" not in raw

    def test_graveyard_fields_cover_tombstone_data(self):
        """Fields schema must define the core tombstone attributes."""
        assert "fields" in self.data
        fields = self.data["fields"]
        assert "name" in fields
        assert "system" in fields
        assert "cause_of_death" in fields


# =============================================================================
# Part 5: ModuleManifest source_type
# =============================================================================

class TestModuleManifestSourceType:
    """Validate the source_type field addition to ModuleManifest."""

    def test_source_type_defaults_to_empty_string(self):
        from codex.spatial.module_manifest import ModuleManifest
        m = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="dnd5e",
        )
        assert m.source_type == ""

    def test_source_type_round_trips_via_to_dict(self):
        from codex.spatial.module_manifest import ModuleManifest
        m = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="dnd5e",
            source_type="community_authored",
        )
        d = m.to_dict()
        assert d["source_type"] == "community_authored"

    def test_source_type_round_trips_via_from_dict(self):
        from codex.spatial.module_manifest import ModuleManifest
        raw = {
            "module_id": "test",
            "display_name": "Test",
            "system_id": "cbrpnk",
            "source_type": "community_authored",
            "chapters": [],
            "freeform_zones": [],
        }
        m = ModuleManifest.from_dict(raw)
        assert m.source_type == "community_authored"

    def test_source_type_absent_in_legacy_dict_defaults_to_empty(self):
        from codex.spatial.module_manifest import ModuleManifest
        raw = {
            "module_id": "legacy",
            "display_name": "Legacy Module",
            "system_id": "bitd",
            "chapters": [],
            "freeform_zones": [],
        }
        m = ModuleManifest.from_dict(raw)
        assert m.source_type == ""

    def test_source_type_empty_not_serialized(self):
        """Empty source_type should not appear in to_dict output (omit-if-empty pattern)."""
        from codex.spatial.module_manifest import ModuleManifest
        m = ModuleManifest(
            module_id="test",
            display_name="Test",
            system_id="dnd5e",
            source_type="",
        )
        d = m.to_dict()
        assert "source_type" not in d

    def test_source_type_round_trips_via_tempfile(self):
        """Full save/load cycle through a temp file."""
        import json
        import tempfile
        import os
        from codex.spatial.module_manifest import ModuleManifest
        m = ModuleManifest(
            module_id="temp_test",
            display_name="Temp Test",
            system_id="sav",
            source_type="community_authored",
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            tmp_path = fh.name
        try:
            m.save(tmp_path)
            loaded = ModuleManifest.load(tmp_path)
            assert loaded.source_type == "community_authored"
        finally:
            os.unlink(tmp_path)

    def test_community_authored_modules_have_source_type(self):
        """All module manifests with source_pdf null should have source_type set."""
        import os
        _VALID_SOURCE_TYPES = {
            "community_authored", "publisher_licensed", "homebrew_original", "generated",
        }
        modules_dir = PROJECT_ROOT / "vault_maps" / "modules"
        for module_dir in modules_dir.iterdir():
            manifest_path = module_dir / "module_manifest.json"
            if not manifest_path.exists():
                continue
            with open(manifest_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("source_pdf") is None:
                assert "source_type" in data, (
                    f"{module_dir.name}/module_manifest.json has null source_pdf but no source_type"
                )
                assert data["source_type"] in _VALID_SOURCE_TYPES, (
                    f"{module_dir.name}: unexpected source_type='{data['source_type']}'"
                )

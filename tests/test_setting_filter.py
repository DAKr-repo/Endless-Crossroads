"""
tests/test_setting_filter.py
==============================
WO-V43.0: Hierarchical Sub-Setting System tests.

Tests the setting filter utility, reference data tagging, engine
setting propagation, adapter pool swapping, and vault discovery.
"""

import pytest
from typing import Dict, Any

from codex.forge.reference_data.setting_filter import (
    filter_by_setting,
    filter_pool_by_setting,
)


# =========================================================================
# 1. FILTER UTILITY — filter_by_setting
# =========================================================================


class TestFilterBySetting:
    """Tests for the filter_by_setting() pure function."""

    SAMPLE_DATA: Dict[str, Dict[str, Any]] = {
        "alethi": {"setting": "roshar", "name": "Alethi"},
        "skaa": {"setting": "scadrial", "name": "Skaa"},
        "spear": {"setting": "cosmere", "name": "Spear"},
        "generic": {"setting": "", "name": "Generic"},
        "no_tag": {"name": "NoTag"},
    }

    def test_none_returns_all(self):
        result = filter_by_setting(self.SAMPLE_DATA, None)
        assert len(result) == 5

    def test_empty_returns_all(self):
        result = filter_by_setting(self.SAMPLE_DATA, "")
        assert len(result) == 5

    def test_setting_match(self):
        result = filter_by_setting(self.SAMPLE_DATA, "roshar")
        assert "alethi" in result
        assert "spear" in result       # cosmere = universal
        assert "generic" in result     # "" = universal
        assert "no_tag" in result      # missing = universal
        assert "skaa" not in result    # scadrial != roshar

    def test_unknown_setting(self):
        result = filter_by_setting(self.SAMPLE_DATA, "nalthis")
        # Only universal entries pass
        assert "spear" in result
        assert "generic" in result
        assert "no_tag" in result
        assert "alethi" not in result
        assert "skaa" not in result

    def test_cosmere_is_universal(self):
        result = filter_by_setting(self.SAMPLE_DATA, "scadrial")
        assert "spear" in result       # cosmere passes all filters
        assert "skaa" in result        # scadrial match
        assert "alethi" not in result  # roshar != scadrial

    def test_no_mutation(self):
        original_len = len(self.SAMPLE_DATA)
        filter_by_setting(self.SAMPLE_DATA, "roshar")
        assert len(self.SAMPLE_DATA) == original_len


# =========================================================================
# 2. FILTER UTILITY — filter_pool_by_setting
# =========================================================================


class TestFilterPoolBySetting:
    """Tests for the filter_pool_by_setting() pure function."""

    DEFAULT_POOL = {1: ["a", "b"], 2: ["c", "d"]}
    ROSHAR_POOL = {1: ["x", "y"], 2: ["z", "w"]}
    REGISTRY = {"roshar": ROSHAR_POOL}

    def test_none_returns_default(self):
        result = filter_pool_by_setting(self.DEFAULT_POOL, None, self.REGISTRY)
        assert result is self.DEFAULT_POOL

    def test_match_returns_registered(self):
        result = filter_pool_by_setting(self.DEFAULT_POOL, "roshar", self.REGISTRY)
        assert result is self.ROSHAR_POOL

    def test_unknown_returns_default(self):
        result = filter_pool_by_setting(self.DEFAULT_POOL, "scadrial", self.REGISTRY)
        assert result is self.DEFAULT_POOL

    def test_no_registry_returns_default(self):
        result = filter_pool_by_setting(self.DEFAULT_POOL, "roshar", None)
        assert result is self.DEFAULT_POOL


# =========================================================================
# 3. REFERENCE DATA TAGGING
# =========================================================================


class TestReferenceDataTagging:
    """Verify that all STC reference data entries have setting tags."""

    def test_all_heritages_tagged(self):
        from codex.forge.reference_data.stc_heritages import HERITAGES
        for name, data in HERITAGES.items():
            assert "setting" in data, f"Heritage '{name}' missing 'setting' key"

    def test_all_orders_tagged(self):
        from codex.forge.reference_data.stc_orders import ORDERS
        for name, data in ORDERS.items():
            assert "setting" in data, f"Order '{name}' missing 'setting' key"

    def test_all_surge_types_tagged(self):
        from codex.forge.reference_data.stc_orders import SURGE_TYPES
        for name, data in SURGE_TYPES.items():
            assert "setting" in data, f"Surge '{name}' missing 'setting' key"

    def test_roshar_heritages_count(self):
        from codex.forge.reference_data.stc_heritages import HERITAGES
        result = filter_by_setting(HERITAGES, "roshar")
        assert len(result) == 10

    def test_roshar_orders_count(self):
        from codex.forge.reference_data.stc_orders import ORDERS
        result = filter_by_setting(ORDERS, "roshar")
        assert len(result) == 10

    def test_weapon_properties_tagged_cosmere(self):
        from codex.forge.reference_data.stc_equipment import WEAPON_PROPERTIES
        for name, data in WEAPON_PROPERTIES.items():
            assert data.get("setting") == "cosmere", (
                f"Weapon '{name}' should have setting='cosmere'"
            )

    def test_weapons_pass_roshar_filter(self):
        """Cosmere-tagged weapons should pass through any sub-setting filter."""
        from codex.forge.reference_data.stc_equipment import WEAPON_PROPERTIES
        result = filter_by_setting(WEAPON_PROPERTIES, "roshar")
        assert len(result) == len(WEAPON_PROPERTIES)

    def test_shardblades_tagged_roshar(self):
        from codex.forge.reference_data.stc_equipment import SHARDBLADES
        for name, data in SHARDBLADES.items():
            assert data.get("setting") == "roshar", (
                f"Shardblade '{name}' should have setting='roshar'"
            )


# =========================================================================
# 4. ENGINE SETTING PROPAGATION
# =========================================================================


class TestEngineSettingPropagation:
    """Verify setting_id flows through CosmereEngine correctly."""

    def test_default_no_setting(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        assert e.setting_id == ""

    def test_create_character_with_setting(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        char = e.create_character("Kaladin", order="windrunner", setting_id="roshar")
        assert char.setting_id == "roshar"
        assert e.setting_id == "roshar"

    def test_save_load_preserves_setting(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        e.create_character("Shallan", order="lightweaver", setting_id="roshar")
        state = e.save_state()
        assert state["setting_id"] == "roshar"
        assert state["party"][0]["setting_id"] == "roshar"

        e2 = CosmereEngine()
        e2.load_state(state)
        assert e2.setting_id == "roshar"
        assert e2.character.setting_id == "roshar"

    def test_adapter_uses_setting(self):
        from codex.games.stc import CosmereAdapter, _ENEMY_POOL
        adapter = CosmereAdapter(setting_id="roshar")
        # Roshar pool is the same as default (only pool registered)
        assert adapter._enemies is _ENEMY_POOL

    def test_adapter_default_no_setting(self):
        from codex.games.stc import CosmereAdapter, _ENEMY_POOL
        adapter = CosmereAdapter()
        assert adapter._enemies is _ENEMY_POOL

    def test_engine_heritages_accessor(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        e.setting_id = "roshar"
        heritages = e.get_heritages()
        assert len(heritages) == 10
        assert "Alethi" in heritages

    def test_engine_orders_accessor(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        e.setting_id = "roshar"
        orders = e.get_orders()
        assert len(orders) == 10
        assert "windrunner" in orders

    def test_engine_equipment_accessor(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        e.setting_id = "roshar"
        weapons = e.get_equipment("weapons")
        assert len(weapons) == 12  # all cosmere weapons pass roshar filter
        blades = e.get_equipment("shardblades")
        assert len(blades) == 5


# =========================================================================
# 5. DISCOVERY — Vault Structure
# =========================================================================


class TestDiscoveryFindsRoshar:
    """Verify that CharacterBuilderEngine discovers the Roshar sub-setting."""

    def test_schema_has_setting_id(self):
        from codex.forge.char_wizard import CreationSchema
        import dataclasses
        field_names = [f.name for f in dataclasses.fields(CreationSchema)]
        assert "setting_id" in field_names

    def test_roshar_discovered(self):
        from codex.forge.char_wizard import CharacterBuilderEngine
        engine = CharacterBuilderEngine()
        schema = engine.get_system("stc_roshar")
        assert schema is not None, "stc_roshar not discovered in vault"
        assert schema.display_name == "Roshar"

    def test_roshar_parent_is_stc(self):
        from codex.forge.char_wizard import CharacterBuilderEngine
        engine = CharacterBuilderEngine()
        schema = engine.get_system("stc_roshar")
        assert schema is not None
        assert schema.parent_engine == "stc"

    def test_roshar_setting_id(self):
        from codex.forge.char_wizard import CharacterBuilderEngine
        engine = CharacterBuilderEngine()
        schema = engine.get_system("stc_roshar")
        assert schema is not None
        assert schema.setting_id == "roshar"

    def test_parent_stc_still_exists(self):
        from codex.forge.char_wizard import CharacterBuilderEngine
        engine = CharacterBuilderEngine()
        stc = engine.get_system("stc")
        assert stc is not None
        assert stc.display_name == "Cosmere Roleplaying Game"

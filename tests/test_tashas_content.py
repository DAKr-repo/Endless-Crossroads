"""
tests/test_tashas_content.py
=============================
Validates Tasha's Cauldron of Everything reference data and its integration
with the loader and dnd5e aggregator module.

Test categories
---------------
1. LIFE_PATH_TABLES integrity      (3 tests)
2. DARK_SECRETS integrity          (3 tests)
3. GROUP_PATRONS integrity         (4 tests)
4. OPTIONAL_CLASS_FEATURES         (2 tests)
5. CUSTOM_LINEAGE                  (2 tests)
6. Loader integration              (3 tests)
"""

import pytest

# ---------------------------------------------------------------------------
# Module-level imports — fail fast on missing modules
# ---------------------------------------------------------------------------
from codex.forge.reference_data.dnd5e_tashas import (
    LIFE_PATH_TABLES,
    DARK_SECRETS,
    GROUP_PATRONS,
    OPTIONAL_CLASS_FEATURES,
    CUSTOM_LINEAGE,
)
from codex.forge.reference_data.dnd5e import (
    LIFE_PATH_TABLES as AGG_LIFE_PATH,
    DARK_SECRETS as AGG_DARK_SECRETS,
    GROUP_PATRONS as AGG_GROUP_PATRONS,
    OPTIONAL_CLASS_FEATURES as AGG_OPTIONAL_FEATURES,
    CUSTOM_LINEAGE as AGG_CUSTOM_LINEAGE,
)
from codex.forge.reference_data.loader import load_reference


# ===========================================================================
# 1. LIFE_PATH_TABLES INTEGRITY
# ===========================================================================

class TestLifePathTables:
    """LIFE_PATH_TABLES must have 5 categories each with at least one entry."""

    REQUIRED_CATEGORIES = {
        "parents", "birthplace", "siblings",
        "childhood_memories", "life_events",
    }

    def test_all_required_categories_present(self):
        """All 5 TCE life path categories must exist in LIFE_PATH_TABLES."""
        assert self.REQUIRED_CATEGORIES.issubset(set(LIFE_PATH_TABLES.keys())), (
            f"Missing categories: {self.REQUIRED_CATEGORIES - set(LIFE_PATH_TABLES.keys())}"
        )

    def test_every_category_is_nonempty_list(self):
        """Every category must be a non-empty list of strings."""
        for category, entries in LIFE_PATH_TABLES.items():
            assert isinstance(entries, list), (
                f"Category '{category}' is not a list"
            )
            assert len(entries) > 0, (
                f"Category '{category}' has no entries"
            )
            for entry in entries:
                assert isinstance(entry, str) and entry.strip(), (
                    f"Category '{category}' contains an invalid entry: {entry!r}"
                )

    def test_life_events_has_at_least_eight_entries(self):
        """Life events table should be rich — at least 8 entries."""
        assert len(LIFE_PATH_TABLES["life_events"]) >= 8


# ===========================================================================
# 2. DARK_SECRETS INTEGRITY
# ===========================================================================

class TestDarkSecrets:
    """DARK_SECRETS must have exactly 12 entries, each with id/name/description."""

    REQUIRED_KEYS = {"id", "name", "description"}

    def test_exactly_twelve_secrets(self):
        """DARK_SECRETS must contain exactly 12 entries."""
        assert len(DARK_SECRETS) == 12, (
            f"Expected 12 dark secrets, got {len(DARK_SECRETS)}"
        )

    def test_all_secrets_have_required_keys(self):
        """Every secret must have id, name, and description."""
        for secret in DARK_SECRETS:
            missing = self.REQUIRED_KEYS - set(secret.keys())
            assert not missing, (
                f"Secret {secret.get('id', '?')} is missing keys: {missing}"
            )

    def test_all_secret_ids_are_unique(self):
        """Secret IDs must be unique across the list."""
        ids = [s["id"] for s in DARK_SECRETS]
        assert len(ids) == len(set(ids)), "Duplicate secret IDs found"


# ===========================================================================
# 3. GROUP_PATRONS INTEGRITY
# ===========================================================================

class TestGroupPatrons:
    """GROUP_PATRONS must have exactly 8 entries with full structure."""

    REQUIRED_KEYS = {"id", "name", "description", "perks", "quest_hooks"}

    def test_exactly_eight_patrons(self):
        """GROUP_PATRONS must contain exactly 8 entries."""
        assert len(GROUP_PATRONS) == 8, (
            f"Expected 8 group patrons, got {len(GROUP_PATRONS)}"
        )

    def test_all_patrons_have_required_keys(self):
        """Every patron must have id, name, description, perks, quest_hooks."""
        for patron in GROUP_PATRONS:
            missing = self.REQUIRED_KEYS - set(patron.keys())
            assert not missing, (
                f"Patron {patron.get('id', '?')} is missing keys: {missing}"
            )

    def test_all_patrons_have_nonempty_perks(self):
        """Every patron must have at least one perk."""
        for patron in GROUP_PATRONS:
            assert isinstance(patron["perks"], list) and len(patron["perks"]) >= 1, (
                f"Patron '{patron['id']}' has no perks"
            )

    def test_all_patrons_have_nonempty_quest_hooks(self):
        """Every patron must have at least one quest hook."""
        for patron in GROUP_PATRONS:
            assert isinstance(patron["quest_hooks"], list) and len(patron["quest_hooks"]) >= 1, (
                f"Patron '{patron['id']}' has no quest hooks"
            )


# ===========================================================================
# 4. OPTIONAL_CLASS_FEATURES
# ===========================================================================

class TestOptionalClassFeatures:
    """OPTIONAL_CLASS_FEATURES must cover at least 10 classes."""

    REQUIRED_CLASSES = {
        "barbarian", "bard", "cleric", "druid", "fighter",
        "monk", "paladin", "ranger", "rogue", "sorcerer",
        "warlock", "wizard",
    }

    def test_covers_at_least_ten_classes(self):
        """Optional features must be defined for at least 10 PHB classes."""
        assert len(OPTIONAL_CLASS_FEATURES) >= 10, (
            f"Expected features for at least 10 classes, "
            f"got {len(OPTIONAL_CLASS_FEATURES)}"
        )

    def test_each_class_entry_has_required_feature_keys(self):
        """Every feature entry must have name, replaces, level, description."""
        required = {"name", "replaces", "level", "description"}
        for cls_name, features in OPTIONAL_CLASS_FEATURES.items():
            assert isinstance(features, list), (
                f"Class '{cls_name}' features is not a list"
            )
            for feat in features:
                missing = required - set(feat.keys())
                assert not missing, (
                    f"Class '{cls_name}' feature {feat.get('name', '?')} "
                    f"is missing keys: {missing}"
                )


# ===========================================================================
# 5. CUSTOM_LINEAGE
# ===========================================================================

class TestCustomLineage:
    """CUSTOM_LINEAGE must have all mandatory keys with correct types."""

    REQUIRED_KEYS = {
        "description", "ability_bonus", "size", "speed",
        "feat", "darkvision_or_skill", "languages",
    }

    def test_all_required_keys_present(self):
        """CUSTOM_LINEAGE must contain all 7 required keys."""
        missing = self.REQUIRED_KEYS - set(CUSTOM_LINEAGE.keys())
        assert not missing, f"CUSTOM_LINEAGE is missing keys: {missing}"

    def test_speed_is_integer_thirty(self):
        """Base speed for Custom Lineage is always 30 ft."""
        assert CUSTOM_LINEAGE["speed"] == 30

    def test_languages_is_nonempty_list(self):
        """Languages must be a non-empty list including Common."""
        langs = CUSTOM_LINEAGE["languages"]
        assert isinstance(langs, list) and len(langs) >= 1
        assert "Common" in langs


# ===========================================================================
# 6. LOADER INTEGRATION
# ===========================================================================

class TestLoaderIntegration:
    """load_reference() must resolve all 5 new Tasha's categories correctly."""

    def test_load_reference_life_path_returns_table(self):
        """load_reference('life_path') must return LIFE_PATH_TABLES."""
        result = load_reference("life_path")
        assert isinstance(result, dict)
        assert "life_events" in result
        assert result == LIFE_PATH_TABLES

    def test_load_reference_dark_secrets_returns_list(self):
        """load_reference('dark_secrets') must return DARK_SECRETS."""
        result = load_reference("dark_secrets")
        assert isinstance(result, list)
        assert len(result) == 12
        assert result == DARK_SECRETS

    def test_load_reference_group_patrons_returns_list(self):
        """load_reference('group_patrons') must return GROUP_PATRONS."""
        result = load_reference("group_patrons")
        assert isinstance(result, list)
        assert len(result) == 8
        assert result == GROUP_PATRONS

    def test_load_reference_optional_features_returns_dict(self):
        """load_reference('optional_features') must return OPTIONAL_CLASS_FEATURES."""
        result = load_reference("optional_features")
        assert isinstance(result, dict)
        assert "wizard" in result
        assert result == OPTIONAL_CLASS_FEATURES

    def test_load_reference_custom_lineage_returns_dict(self):
        """load_reference('custom_lineage') must return CUSTOM_LINEAGE."""
        result = load_reference("custom_lineage")
        assert isinstance(result, dict)
        assert "speed" in result
        assert result == CUSTOM_LINEAGE

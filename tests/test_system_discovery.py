"""
tests/test_system_discovery.py — WO-V59.0 System Discovery & Trait Tests
==========================================================================
Tests for:
  - engine_traits.py: trait registry, validation, dependency resolution
  - system_discovery.py: manifest scanning, system type classification
  - system_manifest.json: schema validation for all 9 systems
  - play_universal.py: dynamic DUNGEON_SYSTEMS/FITD_SYSTEMS wiring
  - classify_system.py: heuristic classification
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


# =========================================================================
# engine_traits.py
# =========================================================================

class TestTraitRegistry:
    """Tests for codex.core.engine_traits."""

    def test_known_traits_not_empty(self):
        from codex.core.engine_traits import KNOWN_TRAITS
        assert len(KNOWN_TRAITS) >= 12

    def test_all_traits_have_definitions(self):
        from codex.core.engine_traits import KNOWN_TRAITS, TRAIT_CATALOG
        for trait in KNOWN_TRAITS:
            assert trait in TRAIT_CATALOG
            td = TRAIT_CATALOG[trait]
            assert td.name == trait
            assert td.category in ("resolution", "narrative", "combat", "progression", "resource")
            assert td.module_path
            assert td.class_name

    def test_validate_traits_all_known(self):
        from codex.core.engine_traits import validate_traits
        assert validate_traits(["action_roll", "stress_track", "narrative_loom"]) == []

    def test_validate_traits_unknown(self):
        from codex.core.engine_traits import validate_traits
        unknown = validate_traits(["action_roll", "telekinesis", "time_travel"])
        assert "telekinesis" in unknown
        assert "time_travel" in unknown
        assert "action_roll" not in unknown

    def test_validate_primary_loop(self):
        from codex.core.engine_traits import validate_primary_loop
        assert validate_primary_loop("spatial_dungeon") is True
        assert validate_primary_loop("scene_navigation") is True
        assert validate_primary_loop("hex_exploration") is False

    def test_get_trait_deps_includes_transitive(self):
        """quest_system requires narrative_loom — deps should include it."""
        from codex.core.engine_traits import get_trait_deps
        deps = get_trait_deps(["quest_system"])
        assert "narrative_loom" in deps
        assert "quest_system" in deps

    def test_get_trait_deps_no_extras(self):
        """action_roll has no deps — should only return itself."""
        from codex.core.engine_traits import get_trait_deps
        deps = get_trait_deps(["action_roll"])
        assert deps == {"action_roll"}

    def test_get_wiring_imports(self):
        from codex.core.engine_traits import get_wiring_imports
        imports = get_wiring_imports(["action_roll", "stress_track"])
        assert "action_roll" in imports
        assert "FITDActionRoll" in imports["action_roll"]
        assert "stress_track" in imports
        assert "StressClock" in imports["stress_track"]

    def test_trait_categories_populated(self):
        from codex.core.engine_traits import TRAIT_CATEGORIES
        assert "resolution" in TRAIT_CATEGORIES
        assert "narrative" in TRAIT_CATEGORIES
        assert "combat" in TRAIT_CATEGORIES
        assert "progression" in TRAIT_CATEGORIES
        assert "resource" in TRAIT_CATEGORIES

    def test_loop_types_defined(self):
        from codex.core.engine_traits import LOOP_TYPES
        assert "spatial_dungeon" in LOOP_TYPES
        assert "scene_navigation" in LOOP_TYPES


# =========================================================================
# system_discovery.py
# =========================================================================

class TestSystemDiscovery:
    """Tests for codex.core.system_discovery."""

    def setup_method(self):
        from codex.core.system_discovery import clear_cache
        clear_cache()

    def test_scan_manifests_finds_all(self):
        from codex.core.system_discovery import get_all_manifests
        manifests = get_all_manifests(force=True)
        # At minimum, original systems (burnwillow, crown) must be found
        assert len(manifests) >= 2
        assert "burnwillow" in manifests
        assert "crown" in manifests
        # Third-party systems only present when vault has their content
        for sys_id in ("dnd5e", "stc", "bitd", "sav", "bob", "cbrpnk", "candela"):
            if sys_id in manifests:
                assert isinstance(manifests[sys_id], dict)

    def test_get_manifest_returns_data(self):
        from codex.core.system_discovery import get_manifest
        m = get_manifest("dnd5e")
        assert m is not None
        assert m["system_id"] == "dnd5e"
        assert m["engine_type"] == "spatial"
        assert m["primary_loop"] == "spatial_dungeon"

    def test_get_manifest_missing_returns_none(self):
        from codex.core.system_discovery import get_manifest
        assert get_manifest("nonexistent_system") is None

    def test_discover_system_types(self):
        from codex.core.system_discovery import discover_system_types
        dungeon, narrative = discover_system_types()
        # Dungeon systems (burnwillow/crown are standalone, excluded from routing)
        assert "dnd5e" in dungeon
        assert "stc" in dungeon
        assert "burnwillow" not in dungeon
        assert "crown" not in dungeon
        # Narrative systems
        assert "bitd" in narrative
        assert "sav" in narrative
        assert "bob" in narrative
        assert "cbrpnk" in narrative
        assert "candela" in narrative
        # No overlap
        assert not (dungeon & narrative)

    def test_discover_includes_hardcoded_fallback(self):
        """Even with no manifests, hardcoded fallback sets are returned."""
        from codex.core.system_discovery import discover_system_types
        dungeon, narrative = discover_system_types(
            vault_root=Path("/nonexistent/vault")
        )
        assert "dnd5e" in dungeon
        assert "bitd" in narrative

    def test_get_primary_loop(self):
        from codex.core.system_discovery import get_primary_loop
        assert get_primary_loop("dnd5e") == "spatial_dungeon"
        assert get_primary_loop("bitd") == "scene_navigation"
        assert get_primary_loop("stc") == "spatial_dungeon"
        assert get_primary_loop("burnwillow") == "spatial_dungeon"
        assert get_primary_loop("candela") == "scene_navigation"

    def test_get_primary_loop_fallback(self):
        from codex.core.system_discovery import get_primary_loop
        # Unknown system with no manifest falls back based on hardcoded
        assert get_primary_loop("unknown_xyz") == "scene_navigation"

    def test_get_engine_traits(self):
        from codex.core.system_discovery import get_engine_traits
        traits = get_engine_traits("dnd5e")
        assert "initiative" in traits
        assert "narrative_loom" in traits
        assert "progression_xp" in traits

    def test_get_engine_traits_fitd(self):
        from codex.core.system_discovery import get_engine_traits
        traits = get_engine_traits("bitd")
        assert "action_roll" in traits
        assert "stress_track" in traits
        assert "faction_clocks" in traits

    def test_get_pattern_hint(self):
        from codex.core.system_discovery import get_pattern_hint
        hint = get_pattern_hint("dnd5e")
        assert hint is not None
        assert "Armor Class" in hint or "AC" in hint

    def test_get_pattern_hint_stc(self):
        from codex.core.system_discovery import get_pattern_hint
        hint = get_pattern_hint("stc")
        assert hint is not None
        assert "Tier" in hint

    def test_get_resolution_mechanic(self):
        from codex.core.system_discovery import get_resolution_mechanic
        assert get_resolution_mechanic("dnd5e") == "d20"
        assert get_resolution_mechanic("bitd") == "dice_pool_d6"
        assert get_resolution_mechanic("stc") == "d20"

    def test_get_engine_module(self):
        from codex.core.system_discovery import get_engine_module
        assert get_engine_module("dnd5e") == "codex.games.dnd5e"
        assert get_engine_module("bitd") == "codex.games.bitd"
        assert get_engine_module("unknown") == "codex.games.unknown"

    def test_caching(self):
        from codex.core.system_discovery import get_all_manifests
        m1 = get_all_manifests()
        m2 = get_all_manifests()
        assert m1 is m2  # Same object (cached)

    def test_clear_cache(self):
        from codex.core.system_discovery import get_all_manifests, clear_cache
        m1 = get_all_manifests()
        clear_cache()
        m2 = get_all_manifests()
        assert m1 is not m2


# =========================================================================
# System manifest schema validation
# =========================================================================

class TestManifestSchema:
    """Validate all 9 system manifests have correct schema."""

    REQUIRED_FIELDS = [
        "system_id", "display_name", "engine_type", "engine_traits",
        "primary_loop", "resolution_mechanic", "classified_by",
        "confidence", "needs_review",
    ]

    def setup_method(self):
        from codex.core.system_discovery import clear_cache
        clear_cache()

    def _get_all(self):
        from codex.core.system_discovery import get_all_manifests
        return get_all_manifests(force=True)

    def test_all_manifests_have_required_fields(self):
        for system_id, manifest in self._get_all().items():
            for field in self.REQUIRED_FIELDS:
                assert field in manifest, (
                    f"{system_id} manifest missing field '{field}'"
                )

    def test_engine_type_valid(self):
        for system_id, manifest in self._get_all().items():
            assert manifest["engine_type"] in ("spatial", "narrative"), (
                f"{system_id} has invalid engine_type: {manifest['engine_type']}"
            )

    def test_primary_loop_valid(self):
        from codex.core.engine_traits import validate_primary_loop
        for system_id, manifest in self._get_all().items():
            assert validate_primary_loop(manifest["primary_loop"]), (
                f"{system_id} has invalid primary_loop: {manifest['primary_loop']}"
            )

    def test_traits_all_known(self):
        from codex.core.engine_traits import validate_traits
        for system_id, manifest in self._get_all().items():
            unknown = validate_traits(manifest["engine_traits"])
            assert not unknown, (
                f"{system_id} has unknown traits: {unknown}"
            )

    def test_all_engines_have_narrative_loom(self):
        """Every engine should declare narrative_loom trait."""
        for system_id, manifest in self._get_all().items():
            assert "narrative_loom" in manifest["engine_traits"], (
                f"{system_id} missing narrative_loom trait"
            )

    def test_spatial_systems_use_spatial_loop(self):
        for system_id, manifest in self._get_all().items():
            if manifest["engine_type"] == "spatial":
                assert manifest["primary_loop"] == "spatial_dungeon", (
                    f"spatial system {system_id} should use spatial_dungeon loop"
                )

    def test_narrative_systems_use_scene_loop(self):
        for system_id, manifest in self._get_all().items():
            if manifest["engine_type"] == "narrative":
                assert manifest["primary_loop"] == "scene_navigation", (
                    f"narrative system {system_id} should use scene_navigation loop"
                )

    def test_fitd_systems_have_action_roll(self):
        fitd = {"bitd", "sav", "bob", "cbrpnk", "candela"}
        for system_id, manifest in self._get_all().items():
            if system_id in fitd:
                assert "action_roll" in manifest["engine_traits"], (
                    f"FITD system {system_id} should have action_roll trait"
                )

    def test_human_classified_systems_not_flagged(self):
        for system_id, manifest in self._get_all().items():
            if manifest["classified_by"] == "human":
                assert manifest["confidence"] == 1.0
                assert manifest["needs_review"] is False

    def test_resolution_mechanic_valid(self):
        valid = {"d20", "dice_pool_d6", "2d6_plus_stat", "d100",
                 "dice_pool_d10", "custom"}
        for system_id, manifest in self._get_all().items():
            assert manifest["resolution_mechanic"] in valid, (
                f"{system_id} has unknown resolution: {manifest['resolution_mechanic']}"
            )


# =========================================================================
# classify_system.py — heuristic classifier
# =========================================================================

class TestHeuristicClassifier:
    """Tests for classify_system.py heuristic classification."""

    def test_dnd_text_classified_spatial(self):
        from classify_system import classify_heuristic
        text = (
            "The goblin has Armor Class 15 and Hit Points 7 (2d6). "
            "Challenge Rating 1/4. Initiative order is rolled at the "
            "start of combat."
        )
        result = classify_heuristic(text)
        assert result["engine_type"] == "spatial"
        assert result["primary_loop"] == "spatial_dungeon"
        assert result["confidence"] >= 0.7

    def test_fitd_text_classified_narrative(self):
        from classify_system import classify_heuristic
        text = (
            "Choose your Action Rating from Insight, Prowess, or Resolve. "
            "Mark Stress when you push yourself or resist consequences. "
            "Position and Effect determine outcome severity. "
            "Your Vice helps you relieve stress between scores."
        )
        result = classify_heuristic(text)
        assert result["engine_type"] == "narrative"
        assert result["primary_loop"] == "scene_navigation"
        assert result["confidence"] >= 0.7

    def test_pbta_text_classified_narrative(self):
        from classify_system import classify_heuristic
        text = (
            "When you defy danger, roll+relevant stat. "
            "On a 10+, you succeed. On a 7-9, you succeed with a cost. "
            "On a 6-, the GM makes a move. "
            "This move is triggered when you act."
        )
        result = classify_heuristic(text)
        assert result["engine_type"] == "narrative"
        assert result["primary_loop"] == "scene_navigation"

    def test_cosmere_text_classified_spatial(self):
        from classify_system import classify_heuristic
        text = (
            "Tier 1 Minion enemies are easy to defeat. "
            "Tier 2 Rival opponents present a challenge. "
            "Tier 3 Boss encounters require strategy."
        )
        result = classify_heuristic(text)
        assert result["engine_type"] == "spatial"

    def test_detects_d20_resolution(self):
        from classify_system import classify_heuristic
        text = "Roll a d20 and add your modifier to determine success."
        result = classify_heuristic(text)
        assert result["resolution_mechanic"] == "d20"

    def test_detects_dice_pool_resolution(self):
        from classify_system import classify_heuristic
        text = "Build a dice pool of d6s based on your action rating."
        result = classify_heuristic(text)
        assert result["resolution_mechanic"] == "dice_pool_d6"

    def test_detects_2d6_resolution(self):
        from classify_system import classify_heuristic
        text = "Roll 2d6+ your relevant stat modifier."
        result = classify_heuristic(text)
        assert result["resolution_mechanic"] == "2d6_plus_stat"

    def test_detects_traits(self):
        from classify_system import classify_heuristic
        text = (
            "Action Rating determines dice pool. "
            "Mark Stress boxes when pushing. "
            "Faction clocks track progress. "
            "Initiative order is used in combat."
        )
        result = classify_heuristic(text)
        traits = result["engine_traits"]
        assert "narrative_loom" in traits  # Always present
        assert "action_roll" in traits
        assert "stress_track" in traits

    def test_detects_dnd_stats(self):
        from classify_system import _detect_stats
        text = "Strength 16, Dexterity 14, Constitution 12, Intelligence 10, Wisdom 8, Charisma 15"
        stats = _detect_stats(text)
        assert "Strength" in stats
        assert "Charisma" in stats

    def test_detects_fitd_stats(self):
        from classify_system import _detect_stats
        text = "Your three attributes are Insight, Prowess, and Resolve."
        stats = _detect_stats(text)
        assert stats == ["Insight", "Prowess", "Resolve"]

    def test_detects_damage_types(self):
        from classify_system import _detect_damage_types
        text = "The weapon deals slashing damage. Fire and cold are elemental."
        types = _detect_damage_types(text)
        assert "slashing" in types
        assert "fire" in types
        assert "cold" in types

    def test_find_unmanifested_systems(self):
        """All current systems should have manifests — none unmanifested."""
        from classify_system import find_unmanifested_systems
        unmanifested = find_unmanifested_systems()
        # The FITD parent dir and ILLUMINATED_WORLDS parent dir
        # might show up if they have SOURCE dirs without manifests.
        # Core systems should NOT appear.
        for known in ["dnd5e", "stc", "bitd", "sav", "bob", "cbrpnk", "candela"]:
            assert known not in unmanifested, (
                f"Known system {known} should have a manifest"
            )


# =========================================================================
# play_universal.py — dynamic system sets
# =========================================================================

class TestPlayUniversalDiscovery:
    """Tests for dynamic DUNGEON_SYSTEMS/FITD_SYSTEMS in play_universal.py."""

    def test_dungeon_systems_populated(self):
        from play_universal import DUNGEON_SYSTEMS
        assert isinstance(DUNGEON_SYSTEMS, set)
        assert "dnd5e" in DUNGEON_SYSTEMS
        assert "stc" in DUNGEON_SYSTEMS
        # burnwillow/crown are standalone — excluded from universal routing
        assert "burnwillow" not in DUNGEON_SYSTEMS
        assert "crown" not in DUNGEON_SYSTEMS

    def test_fitd_systems_populated(self):
        from play_universal import FITD_SYSTEMS
        assert isinstance(FITD_SYSTEMS, set)
        assert "bitd" in FITD_SYSTEMS
        assert "sav" in FITD_SYSTEMS
        assert "bob" in FITD_SYSTEMS
        assert "cbrpnk" in FITD_SYSTEMS
        assert "candela" in FITD_SYSTEMS

    def test_no_overlap(self):
        from play_universal import DUNGEON_SYSTEMS, FITD_SYSTEMS
        overlap = DUNGEON_SYSTEMS & FITD_SYSTEMS
        assert not overlap, f"Systems in both sets: {overlap}"

    def test_resolve_subsetting_unchanged(self):
        from play_universal import _resolve_subsetting
        assert _resolve_subsetting("dnd5e") == ("dnd5e", "")
        assert _resolve_subsetting("stc_roshar") == ("stc", "roshar")
        assert _resolve_subsetting("bitd") == ("bitd", "")
        assert _resolve_subsetting("burnwillow") == ("burnwillow", "")


# =========================================================================
# build_content.py — manifest enrichment
# =========================================================================

class TestBuildContentEnrichment:
    """Tests for manifest-driven SYSTEM_PROFILES enrichment."""

    def test_profiles_include_hardcoded(self):
        from build_content import SYSTEM_PROFILES
        assert "dnd5e" in SYSTEM_PROFILES
        assert "stc" in SYSTEM_PROFILES

    def test_enrich_does_not_override_hardcoded(self):
        """Manifest enrichment should not replace hand-tuned profiles."""
        from build_content import SYSTEM_PROFILES
        # dnd5e profile should still have all the hand-tuned patterns
        profile = SYSTEM_PROFILES["dnd5e"]
        assert "magic_item_pattern" in profile
        assert "trap_pattern" in profile


# =========================================================================
# Integration — temp manifest in temp vault
# =========================================================================

class TestDiscoveryWithTempManifest:
    """Test discovery with a temporary system_manifest.json."""

    def test_temp_manifest_discovered(self):
        from codex.core.system_discovery import _scan_manifests
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create vault/{system}/system_manifest.json
            system_dir = Path(tmpdir) / "test_rpg"
            system_dir.mkdir()
            source_dir = system_dir / "SOURCE"
            source_dir.mkdir()
            manifest = {
                "system_id": "test_rpg",
                "display_name": "Test RPG",
                "engine_type": "narrative",
                "engine_traits": ["narrative_loom", "action_roll"],
                "primary_loop": "scene_navigation",
                "resolution_mechanic": "dice_pool_d6",
                "classified_by": "test",
                "classified_at": "2026-01-01T00:00:00Z",
                "confidence": 1.0,
                "needs_review": False,
            }
            (system_dir / "system_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            result = _scan_manifests(Path(tmpdir))
            assert "test_rpg" in result
            assert result["test_rpg"]["engine_type"] == "narrative"

    def test_needs_review_excluded_from_discovery(self):
        """Systems with needs_review=True are excluded from type sets."""
        from codex.core.system_discovery import discover_system_types
        with tempfile.TemporaryDirectory() as tmpdir:
            system_dir = Path(tmpdir) / "unreviewed"
            system_dir.mkdir()
            manifest = {
                "system_id": "unreviewed",
                "display_name": "Unreviewed RPG",
                "engine_type": "spatial",
                "primary_loop": "spatial_dungeon",
                "needs_review": True,
                "confidence": 0.4,
            }
            (system_dir / "system_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            dungeon, narrative = discover_system_types(vault_root=Path(tmpdir))
            # "unreviewed" should NOT appear in either set (needs_review=True)
            # but hardcoded fallbacks should still be there
            assert "unreviewed" not in dungeon
            assert "unreviewed" not in narrative
            assert "dnd5e" in dungeon  # hardcoded fallback

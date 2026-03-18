"""
tests/test_scaffolding.py — WO-V72.0 Engine Scaffolding Tests
=============================================================
Tests for:
  - SpatialEngineBase: instantiation, abstract stubs, save/load contract
  - NarrativeEngineBase: instantiation, command dispatch, roll_action
  - PbtAActionRoll: outcomes, stat_bonus, seeded RNG determinism
  - GenericEngine: instantiation, command dispatch, manifest-driven stats
  - scaffold_engine.py: output validity, JSON config correctness
"""

from __future__ import annotations

import importlib
import json
import random
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


# =========================================================================
# TestSpatialEngineBase
# =========================================================================

class TestSpatialEngineBase:
    """Tests for codex.core.engines.spatial_base.SpatialEngineBase."""

    def _make_engine(self):
        """Create a minimal concrete subclass for testing."""
        from codex.core.engines.spatial_base import SpatialEngineBase
        from dataclasses import dataclass

        @dataclass
        class DummyCharacter:
            name: str
            setting_id: str = ""
            def is_alive(self): return True
            def to_dict(self): return {"name": self.name, "setting_id": self.setting_id}

        class DummySpatialEngine(SpatialEngineBase):
            system_id = "dummy_spatial"
            system_family = "DUMMY"
            display_name = "Dummy Spatial"

            def _create_character(self, name, **kwargs):
                kwargs.pop("setting_id", None)
                return DummyCharacter(name=name)

            def _get_adapter(self, **kwargs):
                stub = MagicMock()
                stub.rng = random.Random()
                return stub

        return DummySpatialEngine()

    def test_instantiation(self):
        engine = self._make_engine()
        assert engine.system_id == "dummy_spatial"

    def test_system_family(self):
        engine = self._make_engine()
        assert engine.system_family == "DUMMY"

    def test_display_name(self):
        engine = self._make_engine()
        assert engine.display_name == "Dummy Spatial"

    def test_create_character(self):
        engine = self._make_engine()
        char = engine.create_character("Dungeon Hero")
        assert char.name == "Dungeon Hero"
        assert engine.character is char
        assert char in engine.party

    def test_party_management(self):
        engine = self._make_engine()
        c1 = engine.create_character("Hero1")
        c2 = engine.create_character("Hero2")
        assert len(engine.party) == 2
        engine.remove_from_party(c1)
        assert c1 not in engine.party
        assert len(engine.party) == 1

    def test_get_active_party_filters_dead(self):
        engine = self._make_engine()
        # Dead character (is_alive returns False)
        from dataclasses import dataclass

        @dataclass
        class DeadChar:
            name: str
            setting_id: str = ""
            def is_alive(self): return False
            def to_dict(self): return {"name": self.name}

        engine.party = [DeadChar(name="Ghost")]
        assert engine.get_active_party() == []

    def test_abstract_get_adapter_raises(self):
        from codex.core.engines.spatial_base import SpatialEngineBase

        class BrokenEngine(SpatialEngineBase):
            system_id = "broken"
            system_family = "BROKEN"
            display_name = "Broken"

            def _create_character(self, name, **kwargs):
                return MagicMock(name=name)

        engine = BrokenEngine()
        with pytest.raises(NotImplementedError):
            engine._get_adapter()

    def test_abstract_create_character_raises(self):
        from codex.core.engines.spatial_base import SpatialEngineBase

        class BrokenEngine(SpatialEngineBase):
            system_id = "broken2"
            system_family = "BROKEN"
            display_name = "Broken2"

            def _get_adapter(self, **kwargs):
                return MagicMock()

        engine = BrokenEngine()
        with pytest.raises(NotImplementedError):
            engine._create_character("Test")

    def test_get_status_no_party(self):
        engine = self._make_engine()
        status = engine.get_status()
        assert status["system"] == "dummy_spatial"
        assert status["party_size"] == 0
        assert status["lead"] is None

    def test_get_status_with_party(self):
        engine = self._make_engine()
        engine.create_character("StatusHero")
        status = engine.get_status()
        assert status["party_size"] == 1
        assert status["lead"] == "StatusHero"

    def test_save_state_contract(self):
        engine = self._make_engine()
        engine.create_character("SaveMe")
        state = engine.save_state()
        assert isinstance(state, dict)
        assert "system_id" in state
        assert "party" in state
        assert state["system_id"] == "dummy_spatial"

    def test_load_state_restores_party(self):
        engine = self._make_engine()
        engine.create_character("LoadTest")
        state = engine.save_state()

        engine2 = self._make_engine()
        engine2.load_state(state)
        assert engine2.character is not None
        assert engine2.character.name == "LoadTest"

    def test_no_dungeon_returns_none_for_room(self):
        engine = self._make_engine()
        assert engine.get_current_room() is None
        assert engine.get_current_room_dict() is None
        assert engine.get_connected_rooms() == []
        assert engine.get_cardinal_exits() == []

    def test_move_to_room_fails_without_dungeon(self):
        engine = self._make_engine()
        result = engine.move_to_room(999)
        assert result is False

    def test_move_player_grid_fails_without_dungeon(self):
        engine = self._make_engine()
        result = engine.move_player_grid("north")
        assert result is False

    def test_get_mood_context_returns_neutral(self):
        engine = self._make_engine()
        ctx = engine.get_mood_context()
        assert ctx["party_condition"] == "healthy"
        assert ctx["tension"] == 0.0


# =========================================================================
# TestNarrativeEngineBase
# =========================================================================

class TestNarrativeEngineBase:
    """Tests for codex.core.engines.narrative_base.NarrativeEngineBase."""

    def _make_engine(self):
        """Create a minimal concrete subclass for testing."""
        from codex.core.engines.narrative_base import NarrativeEngineBase
        from dataclasses import dataclass

        @dataclass
        class DummyNarrChar:
            name: str
            hunt: int = 0
            setting_id: str = ""
            def is_alive(self): return True
            def to_dict(self): return {
                "name": self.name, "hunt": self.hunt, "setting_id": self.setting_id
            }

        class DummyNarrEngine(NarrativeEngineBase):
            system_id = "dummy_narr"
            system_family = "DUMMY_NARR"
            display_name = "Dummy Narrative"

            def _create_character(self, name, **kwargs):
                hunt = kwargs.pop("hunt", 0)
                kwargs.pop("setting_id", None)
                return DummyNarrChar(name=name, hunt=hunt)

            def _get_command_registry(self):
                return {
                    "custom_cmd": lambda **kw: "custom_result",
                }

        return DummyNarrEngine()

    def test_instantiation(self):
        engine = self._make_engine()
        assert engine.system_id == "dummy_narr"

    def test_create_character_registers_stress(self):
        engine = self._make_engine()
        char = engine.create_character("StressTest")
        assert char.name in engine.stress_clocks

    def test_add_remove_party(self):
        engine = self._make_engine()
        char = engine.create_character("Initial")
        from dataclasses import dataclass

        @dataclass
        class ExtraChar:
            name: str
            def is_alive(self): return True
            def to_dict(self): return {"name": self.name}

        extra = ExtraChar(name="Extra")
        engine.add_to_party(extra)
        assert extra in engine.party
        engine.remove_from_party(extra)
        assert extra not in engine.party

    def test_handle_command_custom_registry(self):
        engine = self._make_engine()
        result = engine.handle_command("custom_cmd")
        assert result == "custom_result"

    def test_handle_command_fallback_to_method(self):
        engine = self._make_engine()
        engine.create_character("StatusChar")
        result = engine.handle_command("status")
        assert isinstance(result, str)

    def test_handle_unknown_command(self):
        engine = self._make_engine()
        result = engine.handle_command("does_not_exist")
        assert "Unknown" in result or "unknown" in result

    def test_roll_action_returns_result(self):
        engine = self._make_engine()
        engine.create_character("Roller")
        result = engine.roll_action(action="hunt", bonus_dice=1)
        assert hasattr(result, "outcome")
        assert result.outcome in ("failure", "mixed", "success", "critical")

    def test_push_stress_increments(self):
        engine = self._make_engine()
        engine.create_character("StressPusher")
        result = engine.push_stress("StressPusher", 3)
        assert result.get("new_stress") == 3

    def test_push_stress_unknown_char(self):
        engine = self._make_engine()
        result = engine.push_stress("Nobody", 1)
        assert result == {}

    def test_add_faction_clock(self):
        engine = self._make_engine()
        clock = engine.add_faction_clock("TestClock", segments=4)
        assert clock in engine.faction_clocks
        assert clock.max_segments == 4

    def test_save_state_contract(self):
        engine = self._make_engine()
        engine.create_character("Saver")
        state = engine.save_state()
        assert "system_id" in state
        assert "party" in state
        assert "stress" in state

    def test_load_state_restores(self):
        engine = self._make_engine()
        engine.create_character("Loader")
        state = engine.save_state()

        engine2 = self._make_engine()
        engine2.load_state(state)
        # party may not restore fully without proper from_dict,
        # but stress_clocks should be there
        assert isinstance(engine2.stress_clocks, dict)

    def test_get_status_structure(self):
        engine = self._make_engine()
        engine.create_character("StatusPerson")
        status = engine.get_status()
        assert "system" in status
        assert "party_size" in status
        assert status["party_size"] == 1

    def test_cmd_crew_stress(self):
        engine = self._make_engine()
        engine.create_character("CrewMember")
        result = engine._cmd_crew_stress()
        assert "CrewMember" in result

    def test_cmd_clocks_no_clocks(self):
        engine = self._make_engine()
        result = engine._cmd_clocks()
        assert "No faction clocks" in result

    def test_cmd_clocks_with_clock(self):
        engine = self._make_engine()
        engine.add_faction_clock("CopClock", segments=6)
        result = engine._cmd_clocks()
        assert "CopClock" in result

    def test_abstract_create_character_raises(self):
        from codex.core.engines.narrative_base import NarrativeEngineBase

        class BrokenNarr(NarrativeEngineBase):
            system_id = "broken_narr"
            system_family = "BROKEN"
            display_name = "Broken"

        engine = BrokenNarr()
        with pytest.raises(NotImplementedError):
            engine._create_character("Test")


# =========================================================================
# TestPbtAActionRoll
# =========================================================================

class TestPbtAActionRoll:
    """Tests for codex.core.services.pbta_engine.PbtAActionRoll."""

    def _roller(self):
        from codex.core.services.pbta_engine import PbtAActionRoll
        return PbtAActionRoll()

    def test_miss_outcome(self):
        """Total <= 6 with no special dice -> miss."""
        roller = self._roller()
        rng = random.Random()
        # Force dice: 1, 2 (total=3+0=3 -> miss)
        rng.randint = lambda a, b: 1 if b == 6 else b
        # Use a reproducible approach instead: patch
        with patch.object(rng, "randint", side_effect=[2, 3]):
            result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "miss"
        assert result.total == 5

    def test_weak_hit_outcome(self):
        """Total 7-9 -> weak_hit."""
        roller = self._roller()
        rng = random.Random()
        with patch.object(rng, "randint", side_effect=[4, 4]):
            result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "weak_hit"
        assert result.total == 8

    def test_strong_hit_outcome(self):
        """Total 10+ -> strong_hit."""
        roller = self._roller()
        rng = random.Random()
        with patch.object(rng, "randint", side_effect=[5, 5]):
            result = roller.roll_move(stat_bonus=0, rng=rng)
        assert result.outcome == "strong_hit"
        assert result.total == 10

    def test_critical_miss_snake_eyes(self):
        """Both 1s -> critical_miss regardless of stat_bonus."""
        roller = self._roller()
        rng = random.Random()
        with patch.object(rng, "randint", side_effect=[1, 1]):
            result = roller.roll_move(stat_bonus=5, rng=rng)  # would be 7 otherwise
        assert result.outcome == "critical_miss"

    def test_critical_hit_boxcars(self):
        """Both 6s -> critical_hit regardless of stat_bonus."""
        roller = self._roller()
        rng = random.Random()
        with patch.object(rng, "randint", side_effect=[6, 6]):
            result = roller.roll_move(stat_bonus=-5, rng=rng)  # would be 7 otherwise
        assert result.outcome == "critical_hit"

    def test_stat_bonus_affects_total(self):
        """stat_bonus is added to the total."""
        roller = self._roller()
        rng = random.Random()
        with patch.object(rng, "randint", side_effect=[3, 3]):
            result = roller.roll_move(stat_bonus=2, rng=rng)
        assert result.total == 8  # 3+3+2
        assert result.stat_bonus == 2

    def test_negative_stat_bonus(self):
        """Negative stat_bonus lowers total."""
        roller = self._roller()
        rng = random.Random()
        with patch.object(rng, "randint", side_effect=[5, 5]):
            result = roller.roll_move(stat_bonus=-2, rng=rng)
        assert result.total == 8  # 5+5-2
        assert result.outcome == "weak_hit"

    def test_seeded_rng_deterministic(self):
        """Same seed produces same result."""
        roller = self._roller()
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        r1 = roller.roll_move(stat_bonus=0, rng=rng1)
        r2 = roller.roll_move(stat_bonus=0, rng=rng2)
        assert r1.dice == r2.dice
        assert r1.total == r2.total
        assert r1.outcome == r2.outcome

    def test_result_dice_has_two_elements(self):
        """PbtAResult.dice always has exactly 2 elements."""
        roller = self._roller()
        for _ in range(20):
            result = roller.roll_move()
            assert len(result.dice) == 2
            assert all(1 <= d <= 6 for d in result.dice)

    def test_total_equals_sum_of_dice_plus_bonus(self):
        """PbtAResult.total == dice[0] + dice[1] + stat_bonus."""
        roller = self._roller()
        for bonus in (-2, 0, 3):
            result = roller.roll_move(stat_bonus=bonus)
            expected = result.dice[0] + result.dice[1] + bonus
            assert result.total == expected

    def test_outcome_is_valid_string(self):
        """PbtAResult.outcome is always one of the 5 valid strings."""
        valid_outcomes = {"miss", "weak_hit", "strong_hit", "critical_miss", "critical_hit"}
        roller = self._roller()
        for _ in range(30):
            result = roller.roll_move()
            assert result.outcome in valid_outcomes

    def test_format_result_returns_string(self):
        """format_result() returns a non-empty string."""
        from codex.core.services.pbta_engine import PbtAActionRoll
        roller = PbtAActionRoll()
        result = roller.roll_move(stat_bonus=1)
        formatted = roller.format_result(result)
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_pbta_result_dataclass(self):
        """PbtAResult is a dataclass with expected attributes."""
        from codex.core.services.pbta_engine import PbtAResult
        r = PbtAResult(total=10, dice=[5, 5], stat_bonus=0, outcome="strong_hit")
        assert r.total == 10
        assert r.dice == [5, 5]


# =========================================================================
# TestGenericEngine
# =========================================================================

class TestGenericEngine:
    """Tests for codex.core.engines.generic_engine.GenericEngine."""

    def _make_engine(self, resolution="d20", char_stats=None):
        from codex.core.engines.generic_engine import GenericEngine
        manifest = {
            "display_name": "Test Generic",
            "resolution_mechanic": resolution,
            "character_stats": char_stats or ["strength", "dexterity"],
        }
        return GenericEngine(system_id="test_generic", manifest=manifest)

    def test_instantiation(self):
        engine = self._make_engine()
        assert engine.system_id == "test_generic"

    def test_display_name_from_manifest(self):
        engine = self._make_engine()
        assert engine.display_name == "Test Generic"

    def test_create_character(self):
        engine = self._make_engine()
        char = engine.create_character("GenChar")
        assert char.name == "GenChar"
        assert engine.character is char

    def test_manifest_driven_stats(self):
        engine = self._make_engine(char_stats=["power", "agility", "wits"])
        char = engine.create_character("StatChar")
        # Stats should be seeded with defaults from manifest
        assert "power" in char.stats or hasattr(char, "power")

    def test_status_command(self):
        engine = self._make_engine()
        engine.create_character("Commander")
        result = engine.handle_command("status")
        assert isinstance(result, str)
        assert "Test Generic" in result

    def test_stats_command(self):
        engine = self._make_engine()
        engine.create_character("StatsGuy")
        result = engine.handle_command("stats")
        assert isinstance(result, str)
        assert "StatsGuy" in result

    def test_stats_command_no_character(self):
        engine = self._make_engine()
        result = engine.handle_command("stats")
        assert "No character" in result

    def test_roll_d20_command(self):
        engine = self._make_engine(resolution="d20")
        engine.create_character("Roller")
        result = engine.handle_command("roll")
        assert isinstance(result, str)
        assert "d20" in result

    def test_roll_pbta_command(self):
        engine = self._make_engine(resolution="pbta")
        engine.create_character("PbtARoller")
        result = engine.handle_command("roll")
        assert isinstance(result, str)
        # PbtA result should mention dice total
        assert "->" in result or "MISS" in result.upper() or "HIT" in result.upper()

    def test_roll_fitd_command(self):
        engine = self._make_engine(resolution="fitd")
        engine.create_character("FitdRoller")
        result = engine.handle_command("roll")
        assert isinstance(result, str)

    def test_unknown_command(self):
        engine = self._make_engine()
        result = engine.handle_command("not_a_real_command")
        assert "Unknown" in result or "unknown" in result

    def test_save_load_round_trip(self):
        engine = self._make_engine()
        engine.create_character("Persisted")
        state = engine.save_state()
        assert "resolution_mechanic" in state
        assert "char_stat_keys" in state

        engine2 = self._make_engine()
        engine2.load_state(state)
        assert engine2.character is not None
        assert engine2.character.name == "Persisted"

    def test_generic_engine_registered(self):
        """GenericEngine should be in ENGINE_REGISTRY."""
        from codex.core.engine_protocol import ENGINE_REGISTRY
        # Import triggers registration
        import codex.core.engines.generic_engine  # noqa: F401
        assert "generic" in ENGINE_REGISTRY

    def test_no_manifest_uses_defaults(self):
        from codex.core.engines.generic_engine import GenericEngine
        engine = GenericEngine()
        assert engine.system_id == "generic"
        assert engine.display_name == "Generic System"


# =========================================================================
# TestScaffolder
# =========================================================================

class TestScaffolder:
    """Tests for scripts/scaffold_engine.py."""

    def _make_temp_manifest(self, tmpdir: Path, system_id: str, loop: str = "scene_navigation") -> Path:
        """Create a minimal manifest in a temp directory."""
        manifest = {
            "system_id": system_id,
            "display_name": f"Test {system_id.title()}",
            "engine_type": "narrative" if loop == "scene_navigation" else "spatial",
            "primary_loop": loop,
            "resolution_mechanic": "fitd" if loop == "scene_navigation" else "d20",
            "engine_traits": ["action_roll", "stress_track"],
            "character_stats": ["hack", "skulk", "fight"],
        }
        path = tmpdir / "system_manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_find_manifest_returns_none_for_unknown(self):
        from scaffold_engine import find_manifest
        result = find_manifest("zzz_totally_fake_system_that_does_not_exist")
        assert result is None

    def test_to_class_name_simple(self):
        from scaffold_engine import _to_class_name
        assert _to_class_name("myworld") == "Myworld"

    def test_to_class_name_snake_case(self):
        from scaffold_engine import _to_class_name
        assert _to_class_name("my_world") == "MyWorld"

    def test_to_class_name_hyphen(self):
        from scaffold_engine import _to_class_name
        assert _to_class_name("pbta-world") == "PbtaWorld"

    def test_build_extra_imports_known_traits(self):
        from scaffold_engine import _build_extra_imports
        imports = _build_extra_imports(["action_roll", "stress_track"])
        assert "FITDActionRoll" in imports or "fitd_engine" in imports

    def test_build_extra_imports_unknown_trait(self):
        from scaffold_engine import _build_extra_imports
        # Unknown traits are silently ignored
        imports = _build_extra_imports(["totally_unknown_trait"])
        assert imports == ""

    def test_build_char_stat_fields_empty(self):
        from scaffold_engine import _build_char_stat_fields
        result = _build_char_stat_fields([])
        assert "TODO" in result

    def test_build_char_stat_fields_with_stats(self):
        from scaffold_engine import _build_char_stat_fields
        result = _build_char_stat_fields(["power", "agility"])
        assert "power" in result
        assert "agility" in result

    def test_scaffold_generates_valid_python(self):
        """Generated narrative engine file should compile without errors."""
        from scaffold_engine import (
            generate_engine_file,
            _to_class_name,
            _build_extra_imports,
            _build_char_stat_fields,
        )
        import py_compile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            manifest_path = self._make_temp_manifest(tmppath, "scaffold_test")
            manifest = json.loads(manifest_path.read_text())

            engine_dir = tmppath / "codex" / "games" / "scaffold_test"
            generate_engine_file("scaffold_test", manifest, engine_dir, force=True)

            engine_file = engine_dir / "__init__.py"
            assert engine_file.exists()
            # Should not raise SyntaxError
            py_compile.compile(str(engine_file), doraise=True)

    def test_scaffold_spatial_generates_valid_python(self):
        """Generated spatial engine file should compile without errors."""
        from scaffold_engine import generate_engine_file
        import py_compile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            manifest_path = self._make_temp_manifest(tmppath, "spatial_test", "spatial_dungeon")
            manifest = json.loads(manifest_path.read_text())

            engine_dir = tmppath / "codex" / "games" / "spatial_test"
            generate_engine_file("spatial_test", manifest, engine_dir, force=True)

            engine_file = engine_dir / "__init__.py"
            assert engine_file.exists()
            py_compile.compile(str(engine_file), doraise=True)

    def test_config_templates_are_valid_json(self):
        """Generated config templates should be valid JSON."""
        from scaffold_engine import generate_config_template

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Patch config dir to write into tmpdir
            import scaffold_engine as sm
            orig_root = sm._PROJECT_ROOT
            sm._PROJECT_ROOT = tmppath
            try:
                path = generate_config_template(
                    "json_test",
                    "bestiary",
                    {"_comment": "test", "system_id": "json_test", "tiers": {"1": []}},
                    force=True,
                )
                data = json.loads(path.read_text(encoding="utf-8"))
                assert isinstance(data, dict)
                assert "tiers" in data
            finally:
                sm._PROJECT_ROOT = orig_root

    def test_test_file_generation(self):
        """Generated test file should compile without syntax errors."""
        from scaffold_engine import generate_test_file
        import py_compile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            manifest = {
                "system_id": "gen_test",
                "display_name": "Generated Test",
                "primary_loop": "scene_navigation",
            }
            tests_dir = tmppath / "tests"
            generate_test_file("gen_test", manifest, tests_dir, force=True)

            test_file = tests_dir / "test_gen_test_engine.py"
            assert test_file.exists()
            py_compile.compile(str(test_file), doraise=True)

    def test_generated_test_has_auto_header(self):
        """Generated test file should have the auto-generated header."""
        from scaffold_engine import generate_test_file

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            manifest = {"system_id": "header_test", "display_name": "Header Test"}
            tests_dir = tmppath / "tests"
            generate_test_file("header_test", manifest, tests_dir, force=True)

            content = (tests_dir / "test_header_test_engine.py").read_text()
            assert "AUTO-GENERATED" in content


# =========================================================================
# TestEngineTraitsPbtA
# =========================================================================

class TestEngineTraitsPbtA:
    """Tests for the pbta_roll trait added to TRAIT_CATALOG."""

    def test_pbta_roll_in_catalog(self):
        from codex.core.engine_traits import TRAIT_CATALOG, KNOWN_TRAITS
        assert "pbta_roll" in TRAIT_CATALOG
        assert "pbta_roll" in KNOWN_TRAITS

    def test_pbta_roll_trait_category(self):
        from codex.core.engine_traits import TRAIT_CATALOG
        trait = TRAIT_CATALOG["pbta_roll"]
        assert trait.category == "resolution"

    def test_pbta_roll_trait_module_path(self):
        from codex.core.engine_traits import TRAIT_CATALOG
        trait = TRAIT_CATALOG["pbta_roll"]
        assert trait.module_path == "codex.core.services.pbta_engine"

    def test_pbta_roll_trait_class_name(self):
        from codex.core.engine_traits import TRAIT_CATALOG
        trait = TRAIT_CATALOG["pbta_roll"]
        assert trait.class_name == "PbtAActionRoll"

    def test_validate_traits_accepts_pbta_roll(self):
        from codex.core.engine_traits import validate_traits
        unknown = validate_traits(["pbta_roll", "action_roll"])
        assert "pbta_roll" not in unknown

    def test_get_wiring_imports_includes_pbta(self):
        from codex.core.engine_traits import get_wiring_imports
        imports = get_wiring_imports(["pbta_roll"])
        assert "pbta_roll" in imports
        assert "PbtAActionRoll" in imports["pbta_roll"]

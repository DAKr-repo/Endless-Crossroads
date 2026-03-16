"""
tests/test_universal_game_loop.py - Universal Engine Routing Tests
===================================================================

Tests for:
  1. System set membership (FITD vs Dungeon)
  2. Engine factory from registry
  3. Character conversion from wizard manifest
  4. FITD loop command dispatch
  5. Dungeon loop engine integration
  6. Routing in codex_agent_main.py (NEW + LOAD paths)

Version: 1.0 (WO-V40.0)
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import game modules to trigger ENGINE_REGISTRY population
import codex.games.bitd      # noqa: F401
import codex.games.sav       # noqa: F401
import codex.games.bob       # noqa: F401
import codex.games.cbrpnk    # noqa: F401
import codex.games.candela   # noqa: F401
import codex.games.dnd5e     # noqa: F401
import codex.games.stc       # noqa: F401


# =========================================================================
# 1. ROUTING TESTS — System set membership & registry
# =========================================================================

class TestSystemSets:
    """Verify FITD and Dungeon system sets are correct."""

    def test_fitd_systems(self):
        from play_universal import FITD_SYSTEMS
        assert FITD_SYSTEMS == {"bitd", "sav", "bob", "cbrpnk", "candela"}

    def test_dungeon_systems(self):
        from play_universal import DUNGEON_SYSTEMS
        assert "dnd5e" in DUNGEON_SYSTEMS
        assert "stc" in DUNGEON_SYSTEMS

    def test_no_overlap(self):
        from play_universal import FITD_SYSTEMS, DUNGEON_SYSTEMS
        assert FITD_SYSTEMS.isdisjoint(DUNGEON_SYSTEMS)

    def test_all_systems_in_registry(self):
        from play_universal import FITD_SYSTEMS, DUNGEON_SYSTEMS
        from codex.core.engine_protocol import ENGINE_REGISTRY
        for sid in FITD_SYSTEMS | DUNGEON_SYSTEMS:
            assert sid in ENGINE_REGISTRY, f"{sid} missing from ENGINE_REGISTRY"

    def test_engine_factory_bitd(self):
        from codex.core.engine_protocol import ENGINE_REGISTRY
        engine = ENGINE_REGISTRY["bitd"]()
        assert engine.system_id == "bitd"
        assert engine.system_family == "FITD"

    def test_engine_factory_dnd5e(self):
        from codex.core.engine_protocol import ENGINE_REGISTRY
        engine = ENGINE_REGISTRY["dnd5e"]()
        assert engine.system_id == "dnd5e"

    def test_engine_factory_stc(self):
        from codex.core.engine_protocol import ENGINE_REGISTRY
        engine = ENGINE_REGISTRY["stc"]()
        assert engine.system_id == "stc"

    def test_engine_factory_sav(self):
        from codex.core.engine_protocol import ENGINE_REGISTRY
        engine = ENGINE_REGISTRY["sav"]()
        assert engine.system_id == "sav"

    def test_engine_factory_bob(self):
        from codex.core.engine_protocol import ENGINE_REGISTRY
        engine = ENGINE_REGISTRY["bob"]()
        assert engine.system_id == "bob"

    def test_engine_factory_cbrpnk(self):
        from codex.core.engine_protocol import ENGINE_REGISTRY
        engine = ENGINE_REGISTRY["cbrpnk"]()
        assert engine.system_id == "cbrpnk"

    def test_engine_factory_candela(self):
        from codex.core.engine_protocol import ENGINE_REGISTRY
        engine = ENGINE_REGISTRY["candela"]()
        assert engine.system_id == "candela"


# =========================================================================
# 2. CHARACTER CONVERSION — Wizard manifest -> engine kwargs
# =========================================================================

class TestCharacterConversion:
    """Test convert_wizard_character for each system."""

    def test_bitd_conversion(self):
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("bitd", "Dusk", {
            "playbook": "Cutter",
            "heritage": {"id": "Akoros"},
        }, {
            "hunt": 1, "study": 2, "skirmish": 3,
        })
        assert kwargs["playbook"] == "Cutter"
        assert kwargs["heritage"] == "Akoros"
        assert kwargs["hunt"] == 1
        assert kwargs["study"] == 2
        assert kwargs["skirmish"] == 3
        assert kwargs["sway"] == 0  # default

    def test_sav_conversion(self):
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("sav", "Nova", {
            "playbook": "Pilot",
            "heritage": "Spacer",
        }, {
            "helm": 2, "hack": 1,
        })
        assert kwargs["playbook"] == "Pilot"
        assert kwargs["heritage"] == "Spacer"
        assert kwargs["helm"] == 2
        assert kwargs["hack"] == 1

    def test_bob_conversion(self):
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("bob", "Griff", {
            "playbook": "Scout",
            "heritage": "Panyar",
        }, {
            "scout_action": 2, "skirmish": 1,
        })
        assert kwargs["playbook"] == "Scout"
        assert kwargs["heritage"] == "Panyar"
        assert kwargs["scout_action"] == 2

    def test_cbrpnk_conversion(self):
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("cbrpnk", "Neon", {
            "archetype": "Hacker",
            "background": "Corporate Exile",
            "chrome": ["Cybereyes", "Reflex Booster"],
        }, {
            "hack": 3, "shoot": 1,
        })
        assert kwargs["archetype"] == "Hacker"
        assert kwargs["background"] == "Corporate Exile"
        assert kwargs["chrome"] == ["Cybereyes", "Reflex Booster"]
        assert kwargs["hack"] == 3

    def test_candela_conversion(self):
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("candela", "Ada", {
            "role": "Scholar",
            "specialization": "Doctor",
        }, {
            "survey": 2, "focus": 1, "strike": 1,
        })
        assert kwargs["role"] == "Scholar"
        assert kwargs["specialization"] == "Doctor"
        assert kwargs["survey"] == 2
        assert kwargs["focus"] == 1

    def test_dnd5e_conversion(self):
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("dnd5e", "Thorin", {
            "character_class": "fighter",
            "race": "dwarf",
        }, {
            "strength": 16, "dexterity": 12, "constitution": 14,
            "intelligence": 10, "wisdom": 10, "charisma": 8,
        })
        assert kwargs["character_class"] == "fighter"
        assert kwargs["race"] == "dwarf"
        assert kwargs["strength"] == 16
        assert kwargs["charisma"] == 8

    def test_dnd5e_class_key_fallback(self):
        """Test that 'class' key works as fallback for 'character_class'."""
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("dnd5e", "Elara", {
            "class": "wizard",
            "race": "elf",
        }, {})
        assert kwargs["character_class"] == "wizard"

    def test_stc_conversion(self):
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("stc", "Kaladin", {
            "order": "windrunner",
            "heritage": "Alethi",
        }, {
            "strength": 14, "speed": 12, "intellect": 10,
        })
        assert kwargs["order"] == "windrunner"
        assert kwargs["heritage"] == "Alethi"
        assert kwargs["strength"] == 14

    def test_missing_stats_defaults(self):
        """Missing stats should default to 0 (FITD) or 10 (d20)."""
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("bitd", "Ghost", {}, {})
        assert kwargs["hunt"] == 0
        assert kwargs["skirmish"] == 0

        kwargs = convert_wizard_character("dnd5e", "Hero", {}, {})
        assert kwargs["strength"] == 10
        assert kwargs["charisma"] == 10

    def test_dict_choice_extraction(self):
        """Choices as {'id': 'value'} dicts should be extracted."""
        from play_universal import convert_wizard_character
        kwargs = convert_wizard_character("sav", "Jet", {
            "playbook": {"id": "Mechanic", "name": "Mechanic"},
            "heritage": {"id": "Imperial"},
        }, {})
        assert kwargs["playbook"] == "Mechanic"
        assert kwargs["heritage"] == "Imperial"


# =========================================================================
# 3. FITD LOOP — Engine command dispatch
# =========================================================================

class TestFITDLoop:
    """Test FITD engine creation and command dispatch."""

    def test_bitd_create_and_status(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Dusk", playbook="Cutter", heritage="Akoros")
        status = engine.get_status()
        assert status["lead"] == "Dusk"
        assert status["playbook"] == "Cutter"

    def test_bitd_handle_command_roll(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Dusk", skirmish=2)
        result = engine.handle_command("roll_action", action="skirmish")
        assert "Dice:" in result

    def test_bitd_handle_command_crew_status(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Dusk")
        result = engine.handle_command("crew_status")
        assert "Heat:" in result or "Crew:" in result

    def test_bitd_handle_command_entanglement(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Dusk")
        result = engine.handle_command("entanglement")
        assert "Entanglement Roll:" in result

    def test_sav_handle_command_ship_status(self):
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Nova", playbook="Pilot")
        engine.ship_name = "The Raven"
        result = engine.handle_command("ship_status")
        assert "The Raven" in result

    def test_bob_handle_command_legion_status(self):
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Griff")
        result = engine.handle_command("legion_status")
        assert "Supply:" in result

    def test_cbrpnk_handle_command_glitch(self):
        from codex.games.cbrpnk import CBRPNKEngine
        engine = CBRPNKEngine()
        engine.create_character("Neon", archetype="Hacker")
        result = engine.handle_command("glitch_status")
        assert "Glitch Die:" in result

    def test_candela_handle_command_circle(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Ada", role="Scholar")
        engine.circle_name = "The Seekers"
        result = engine.handle_command("circle_status")
        assert "The Seekers" in result

    def test_unknown_command(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Dusk")
        result = engine.handle_command("nonexistent_command")
        assert "Unknown command" in result

    def test_save_load_roundtrip(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Dusk", playbook="Cutter", skirmish=2)
        engine.heat = 3
        engine.coin = 5
        saved = engine.save_state()
        engine2 = BitDEngine()
        engine2.load_state(saved)
        assert engine2.character.name == "Dusk"
        assert engine2.character.playbook == "Cutter"
        assert engine2.character.skirmish == 2
        assert engine2.heat == 3
        assert engine2.coin == 5


# =========================================================================
# 4. DUNGEON LOOP — DnD5e / Cosmere engine commands
# =========================================================================

class TestDungeonLoop:
    """Test dungeon-mode engines with navigation and combat."""

    def test_dnd5e_create_and_generate(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Thorin", character_class="fighter",
                                strength=16, constitution=14)
        result = engine.generate_dungeon(seed=42)
        assert result["total_rooms"] > 0
        assert engine.current_room_id is not None

    def test_dnd5e_navigation(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Thorin", character_class="fighter")
        engine.generate_dungeon(seed=42)
        exits = engine.get_cardinal_exits()
        assert isinstance(exits, list)
        if exits:
            target = exits[0]["id"]
            assert engine.move_to_room(target)
            assert target in engine.visited_rooms

    def test_dnd5e_bridge_look(self):
        from codex.games.dnd5e import DnD5eEngine
        from play_universal import _EngineWrappedBridge
        engine = DnD5eEngine()
        engine.create_character("Thorin", character_class="fighter")
        engine.generate_dungeon(seed=42)
        bridge = _EngineWrappedBridge(engine)
        result = bridge.step("look")
        assert "Room" in result
        assert "EXITS:" in result or "EXIT" in result.upper()

    def test_dnd5e_bridge_map(self):
        from codex.games.dnd5e import DnD5eEngine
        from play_universal import _EngineWrappedBridge
        engine = DnD5eEngine()
        engine.create_character("Thorin", character_class="fighter")
        engine.generate_dungeon(seed=42)
        bridge = _EngineWrappedBridge(engine)
        result = bridge.step("map")
        assert len(result) > 0

    def test_dnd5e_bridge_help(self):
        from codex.games.dnd5e import DnD5eEngine
        from play_universal import _EngineWrappedBridge
        engine = DnD5eEngine()
        engine.create_character("Thorin", character_class="fighter")
        engine.generate_dungeon(seed=42)
        bridge = _EngineWrappedBridge(engine)
        result = bridge.step("help")
        assert "attack" in result.lower()

    def test_stc_create_and_generate(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner",
                                heritage="Alethi", strength=14)
        result = engine.generate_dungeon(seed=42)
        assert result["total_rooms"] > 0

    def test_stc_bridge_look(self):
        from codex.games.stc import CosmereEngine
        from play_universal import _EngineWrappedBridge
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        engine.generate_dungeon(seed=42)
        bridge = _EngineWrappedBridge(engine)
        result = bridge.step("look")
        assert "Room" in result

    def test_dnd5e_bridge_status(self):
        from codex.games.dnd5e import DnD5eEngine
        from play_universal import _EngineWrappedBridge
        engine = DnD5eEngine()
        engine.create_character("Thorin", character_class="fighter")
        engine.generate_dungeon(seed=42)
        bridge = _EngineWrappedBridge(engine)
        result = bridge.step("stats")
        assert "Thorin" in result

    def test_dnd5e_save_load(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Thorin", character_class="fighter",
                                strength=16)
        engine.generate_dungeon(seed=42)
        saved = engine.save_state()
        engine2 = DnD5eEngine()
        engine2.load_state(saved)
        assert engine2.character.name == "Thorin"
        assert engine2.character.strength == 16


# =========================================================================
# 5. INTEGRATION — Routing in codex_agent_main.py
# =========================================================================

class TestRouting:
    """Test that the import and routing logic works correctly."""

    def test_universal_import_available(self):
        """play_universal should be importable."""
        from play_universal import main as run_universal_game
        assert callable(run_universal_game)

    def test_engine_registry_import(self):
        """ENGINE_REGISTRY should have all 7 systems + fitd primitive."""
        from codex.core.engine_protocol import ENGINE_REGISTRY
        for sid in ("bitd", "sav", "bob", "cbrpnk", "candela", "dnd5e", "stc"):
            assert sid in ENGINE_REGISTRY

    def test_crown_not_in_universal(self):
        """Crown/Ashburn should not be routed through universal."""
        from play_universal import FITD_SYSTEMS, DUNGEON_SYSTEMS
        assert "crown" not in FITD_SYSTEMS
        assert "crown" not in DUNGEON_SYSTEMS
        assert "ashburn" not in FITD_SYSTEMS
        assert "ashburn" not in DUNGEON_SYSTEMS

    def test_burnwillow_not_in_universal(self):
        """Burnwillow has its own loop and should not be in universal."""
        from play_universal import FITD_SYSTEMS, DUNGEON_SYSTEMS
        assert "burnwillow" not in FITD_SYSTEMS
        assert "burnwillow" not in DUNGEON_SYSTEMS

    def test_main_unknown_system(self):
        """main() with unknown system_id should not crash."""
        from play_universal import main
        from io import StringIO
        from rich.console import Console
        # Patch Console to suppress output
        with patch("play_universal.Console") as mock_con_cls:
            mock_con = MagicMock()
            mock_con_cls.return_value = mock_con
            main("nonexistent_system_xyz")
            # Should have printed an error message
            mock_con.print.assert_called()
            args_str = str(mock_con.print.call_args_list[0])
            assert "Unknown game system" in args_str or "nonexistent" in args_str

    def test_convert_wizard_character_all_systems(self):
        """Smoke test: conversion should not crash for any supported system."""
        from play_universal import convert_wizard_character
        systems = ["bitd", "sav", "bob", "cbrpnk", "candela", "dnd5e", "stc"]
        for sid in systems:
            kwargs = convert_wizard_character(sid, "TestHero", {}, {})
            assert isinstance(kwargs, dict), f"Failed for {sid}"


class TestMultiCharacterParty:
    """Test multi-character party creation through wizard manifest."""

    def test_bitd_multi_character(self):
        from codex.games.bitd import BitDEngine
        from play_universal import convert_wizard_character
        engine = BitDEngine()
        chars_data = [
            {"name": "Dusk", "choices": {"playbook": "Cutter"}, "stats": {"skirmish": 2}},
            {"name": "Silk", "choices": {"playbook": "Slide"}, "stats": {"sway": 3}},
        ]
        for i, cd in enumerate(chars_data):
            kwargs = convert_wizard_character("bitd", cd["name"],
                                              cd["choices"], cd["stats"])
            if i == 0:
                engine.create_character(cd["name"], **kwargs)
            else:
                char = engine.create_character(cd["name"], **kwargs)
        # Last create_character call sets the party to just that character
        # for FITD engines, but both exist as StressClock entries
        assert engine.character.name == "Silk"

    def test_dnd5e_multi_character(self):
        from codex.games.dnd5e import DnD5eEngine
        from play_universal import convert_wizard_character
        engine = DnD5eEngine()
        chars_data = [
            {"name": "Thorin", "choices": {"character_class": "fighter"}, "stats": {"strength": 16}},
            {"name": "Elara", "choices": {"character_class": "wizard"}, "stats": {"intelligence": 18}},
        ]
        for i, cd in enumerate(chars_data):
            kwargs = convert_wizard_character("dnd5e", cd["name"],
                                              cd["choices"], cd["stats"])
            if i == 0:
                engine.create_character(cd["name"], **kwargs)
            else:
                from codex.games.dnd5e import DnD5eCharacter
                char = DnD5eCharacter(name=cd["name"], **kwargs)
                engine.add_to_party(char)
        assert len(engine.party) == 2
        assert engine.party[0].name == "Thorin"
        assert engine.party[1].name == "Elara"


class TestEngineWrappedBridge:
    """Test the _EngineWrappedBridge adapter."""

    def test_bridge_wraps_existing_engine(self):
        from codex.games.dnd5e import DnD5eEngine
        from play_universal import _EngineWrappedBridge
        engine = DnD5eEngine()
        engine.create_character("Hero", character_class="fighter")
        engine.generate_dungeon(seed=1)
        bridge = _EngineWrappedBridge(engine)
        # Bridge should use the same engine instance
        assert bridge._bridge.engine is engine
        assert not bridge.dead

    def test_bridge_unknown_command(self):
        from codex.games.dnd5e import DnD5eEngine
        from play_universal import _EngineWrappedBridge
        engine = DnD5eEngine()
        engine.create_character("Hero", character_class="fighter")
        engine.generate_dungeon(seed=1)
        bridge = _EngineWrappedBridge(engine)
        result = bridge.step("xyzzy")
        assert "Unknown command" in result or "unknown" in result.lower()


class TestCommandTableRendering:
    """Test that command tables load properly for all systems."""

    def test_load_bitd_commands(self):
        from play_universal import _load_system_commands, _SYSTEM_COMMANDS
        _load_system_commands("bitd")
        assert "roll_action" in _SYSTEM_COMMANDS.get("bitd", {})

    def test_load_sav_commands(self):
        from play_universal import _load_system_commands, _SYSTEM_COMMANDS
        _load_system_commands("sav")
        assert "ship_status" in _SYSTEM_COMMANDS.get("sav", {})

    def test_load_bob_commands(self):
        from play_universal import _load_system_commands, _SYSTEM_COMMANDS
        _load_system_commands("bob")
        assert "legion_status" in _SYSTEM_COMMANDS.get("bob", {})

    def test_load_cbrpnk_commands(self):
        from play_universal import _load_system_commands, _SYSTEM_COMMANDS
        _load_system_commands("cbrpnk")
        assert "glitch_status" in _SYSTEM_COMMANDS.get("cbrpnk", {})

    def test_load_candela_commands(self):
        from play_universal import _load_system_commands, _SYSTEM_COMMANDS
        _load_system_commands("candela")
        assert "circle_status" in _SYSTEM_COMMANDS.get("candela", {})

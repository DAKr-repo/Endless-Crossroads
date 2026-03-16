"""
tests/test_engine_stack.py - Tests for WO-V60.0 Engine Stacking
=================================================================

Tests MechanicLayer, StackedCharacter, StackedCommandDispatcher,
ACTION_EQUIVALENCE_MAP, snapshot/seed helpers, and stacked save/load.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from codex.core.engine_stack import (
    ACTION_EQUIVALENCE_MAP,
    IncompatibleStackError,
    MechanicLayer,
    STACKABLE_FAMILIES,
    StackedCharacter,
    StackedCommandDispatcher,
    _SYSTEM_ACTIONS,
    can_stack,
    extract_action_map,
    seed_actions,
    snapshot_engine,
)
from codex.core.mechanics.clock import UniversalClock


# =========================================================================
# FIXTURES
# =========================================================================

def _make_mock_engine(system_id="cbrpnk", actions=None, display_name=None):
    """Create a mock engine with character and action dots."""
    engine = MagicMock()
    engine.system_id = system_id
    engine.system_family = "FITD"
    engine.display_name = display_name or system_id.upper()
    engine.save_state.return_value = {
        "system_id": system_id,
        "character": {"name": "TestRunner"},
    }

    char = MagicMock()
    char.name = "TestRunner"
    if actions:
        for k, v in actions.items():
            setattr(char, k, v)
    else:
        # Default CBR+PNK actions
        char.hack = 2
        char.override = 1
        char.scan = 1
        char.study = 0
        char.scramble = 1
        char.scrap = 2
        char.skulk = 0
        char.shoot = 2
        char.attune = 0
        char.command = 1
        char.consort = 0
        char.sway = 1

    engine.character = char
    engine.party = [char]
    return engine


def _make_sav_engine(actions=None):
    """Create a mock SaV engine."""
    engine = MagicMock()
    engine.system_id = "sav"
    engine.system_family = "FITD"
    engine.display_name = "Scum and Villainy"
    engine.save_state.return_value = {
        "system_id": "sav",
        "character": {"name": "TestPilot"},
    }

    char = MagicMock()
    char.name = "TestPilot"
    defaults = {
        "doctor": 0, "hack": 1, "rig": 0, "study": 1,
        "helm": 0, "scramble": 0, "scrap": 0, "skulk": 0,
        "attune": 0, "command": 0, "consort": 0, "sway": 0,
    }
    if actions:
        defaults.update(actions)
    for k, v in defaults.items():
        setattr(char, k, v)

    engine.character = char
    engine.party = [char]
    return engine


# =========================================================================
# MECHANIC LAYER TESTS
# =========================================================================

class TestMechanicLayer:
    def test_create_layer(self):
        layer = MechanicLayer(
            system_id="cbrpnk",
            engine_state={"test": True},
            action_snapshot={"hack": 2, "shoot": 1},
        )
        assert layer.system_id == "cbrpnk"
        assert layer.dormant is False
        assert layer.action_snapshot["hack"] == 2

    def test_serialize_roundtrip(self):
        layer = MechanicLayer(
            system_id="sav",
            engine_state={"crew": "smugglers"},
            action_snapshot={"helm": 2, "doctor": 1},
            dormant=True,
            timestamp="2026-03-09T12:00:00+00:00",
        )
        data = layer.to_dict()
        restored = MechanicLayer.from_dict(data)
        assert restored.system_id == "sav"
        assert restored.dormant is True
        assert restored.action_snapshot == {"helm": 2, "doctor": 1}
        assert restored.timestamp == "2026-03-09T12:00:00+00:00"

    def test_from_dict_defaults(self):
        layer = MechanicLayer.from_dict({"system_id": "bitd"})
        assert layer.engine_state == {}
        assert layer.action_snapshot == {}
        assert layer.dormant is False
        assert layer.timestamp == ""


# =========================================================================
# STACKED CHARACTER TESTS
# =========================================================================

class TestStackedCharacter:
    def test_empty_stack(self):
        sc = StackedCharacter(name="TestHero")
        assert sc.layers == []
        assert sc.merged_actions() == {}
        assert sc.get_active_layer() is None

    def test_add_layer(self):
        sc = StackedCharacter(name="Kira")
        sc.add_layer("cbrpnk", {"state": 1}, {"hack": 2, "shoot": 1})
        assert len(sc.layers) == 1
        assert sc.active_system_id == "cbrpnk"
        assert sc.layers[0].dormant is False

    def test_add_second_layer_marks_first_dormant(self):
        sc = StackedCharacter(name="Kira")
        sc.add_layer("cbrpnk", {}, {"hack": 2})
        sc.add_layer("sav", {}, {"helm": 1})
        assert len(sc.layers) == 2
        assert sc.layers[0].dormant is True
        assert sc.layers[1].dormant is False
        assert sc.active_system_id == "sav"

    def test_get_layer(self):
        sc = StackedCharacter(name="Kira")
        sc.add_layer("cbrpnk", {}, {"hack": 2})
        sc.add_layer("sav", {}, {"helm": 1})
        assert sc.get_layer("cbrpnk").system_id == "cbrpnk"
        assert sc.get_layer("sav").system_id == "sav"
        assert sc.get_layer("bitd") is None

    def test_get_active_layer(self):
        sc = StackedCharacter(name="Kira")
        sc.add_layer("cbrpnk", {}, {"hack": 2})
        sc.add_layer("sav", {}, {"helm": 1})
        active = sc.get_active_layer()
        assert active.system_id == "sav"
        assert active.dormant is False

    def test_merged_actions_union_max(self):
        sc = StackedCharacter(name="Kira")
        sc.add_layer("cbrpnk", {}, {"hack": 2, "shoot": 3, "sway": 1})
        sc.add_layer("sav", {}, {"hack": 1, "helm": 2, "sway": 2})
        merged = sc.merged_actions()
        assert merged["hack"] == 2     # max(2, 1)
        assert merged["shoot"] == 3    # only in cbrpnk
        assert merged["helm"] == 2     # only in sav
        assert merged["sway"] == 2     # max(1, 2)

    def test_serialize_roundtrip(self):
        sc = StackedCharacter(name="Kira")
        sc.add_layer("cbrpnk", {"heat": 3}, {"hack": 2, "shoot": 1})
        sc.add_layer("sav", {"crew": "smugglers"}, {"helm": 2})

        data = sc.to_dict()
        assert data["name"] == "Kira"
        assert data["active_system_id"] == "sav"
        assert len(data["layers"]) == 2

        restored = StackedCharacter.from_dict(data)
        assert restored.name == "Kira"
        assert restored.active_system_id == "sav"
        assert len(restored.layers) == 2
        assert restored.layers[0].dormant is True
        assert restored.layers[1].dormant is False

    def test_json_serializable(self):
        sc = StackedCharacter(name="Test")
        sc.add_layer("cbrpnk", {"x": 1}, {"hack": 2})
        json_str = json.dumps(sc.to_dict())
        data = json.loads(json_str)
        restored = StackedCharacter.from_dict(data)
        assert restored.name == "Test"


# =========================================================================
# STACKED COMMAND DISPATCHER TESTS
# =========================================================================

class TestStackedCommandDispatcher:
    def test_dispatch_active_engine_first(self):
        active = MagicMock()
        active.handle_command.return_value = "Active result"
        active.display_name = "SaV"
        active.system_id = "sav"

        dormant = MagicMock()
        dormant.handle_command.return_value = "Dormant result"
        dormant.display_name = "CBR+PNK"
        dormant.system_id = "cbrpnk"

        d = StackedCommandDispatcher(active, [dormant])
        result = d.dispatch("crew_status")
        assert result == "Active result"
        active.handle_command.assert_called_once_with("crew_status")
        dormant.handle_command.assert_not_called()

    def test_dispatch_falls_through_to_dormant(self):
        active = MagicMock()
        active.handle_command.return_value = "Unknown command: chrome_status"
        active.display_name = "SaV"
        active.system_id = "sav"

        dormant = MagicMock()
        dormant.handle_command.return_value = "Chrome: 3 installed"
        dormant.display_name = "CBR+PNK"
        dormant.system_id = "cbrpnk"

        d = StackedCommandDispatcher(active, [dormant])
        result = d.dispatch("chrome_status")
        assert "[CBR+PNK]" in result
        assert "Chrome: 3 installed" in result

    def test_dispatch_unknown_both(self):
        active = MagicMock()
        active.handle_command.return_value = "Unknown command: foo"
        active.system_id = "sav"

        dormant = MagicMock()
        dormant.handle_command.return_value = "Unknown command: foo"
        dormant.system_id = "cbrpnk"

        d = StackedCommandDispatcher(active, [dormant])
        result = d.dispatch("foo")
        assert "Unknown command: foo" in result

    def test_dispatch_no_dormant(self):
        active = MagicMock()
        active.handle_command.return_value = "OK"
        active.system_id = "sav"

        d = StackedCommandDispatcher(active, [])
        assert d.dispatch("status") == "OK"

    def test_dispatch_active_exception_falls_through(self):
        active = MagicMock()
        active.handle_command.side_effect = RuntimeError("boom")
        active.system_id = "sav"

        dormant = MagicMock()
        dormant.handle_command.return_value = "Dormant OK"
        dormant.display_name = "CBR+PNK"
        dormant.system_id = "cbrpnk"

        d = StackedCommandDispatcher(active, [dormant])
        result = d.dispatch("test_cmd")
        assert "[CBR+PNK]" in result

    def test_get_all_commands(self):
        class FakeActive:
            display_name = "SaV"
            system_id = "sav"
            def _cmd_crew_status(self): pass
            def _cmd_ship_status(self): pass

        class FakeDormant:
            display_name = "CBR+PNK"
            system_id = "cbrpnk"
            def _cmd_chrome_status(self): pass
            def _cmd_hack(self): pass

        d = StackedCommandDispatcher(FakeActive(), [FakeDormant()])
        all_cmds = d.get_all_commands()
        assert "SaV (active)" in all_cmds
        assert "CBR+PNK (dormant)" in all_cmds
        assert "crew_status" in all_cmds["SaV (active)"]
        assert "chrome_status" in all_cmds["CBR+PNK (dormant)"]

    def test_is_unknown_detection(self):
        assert StackedCommandDispatcher._is_unknown("Unknown command: foo")
        assert StackedCommandDispatcher._is_unknown("Unrecognized input")
        assert StackedCommandDispatcher._is_unknown("")
        assert not StackedCommandDispatcher._is_unknown("Crew status: OK")

    def test_dispatch_empty_result_is_unknown(self):
        active = MagicMock()
        active.handle_command.return_value = ""
        active.system_id = "sav"

        dormant = MagicMock()
        dormant.handle_command.return_value = "Got it"
        dormant.display_name = "BitD"
        dormant.system_id = "bitd"

        d = StackedCommandDispatcher(active, [dormant])
        result = d.dispatch("test")
        assert "[BitD]" in result


# =========================================================================
# EXTRACT ACTION MAP TESTS
# =========================================================================

class TestExtractActionMap:
    def test_extract_cbrpnk(self):
        engine = _make_mock_engine("cbrpnk")
        actions = extract_action_map(engine)
        assert actions["hack"] == 2
        assert actions["shoot"] == 2
        assert actions["study"] == 0
        assert len(actions) == len(_SYSTEM_ACTIONS["cbrpnk"])

    def test_extract_sav(self):
        engine = _make_sav_engine({"helm": 3, "hack": 2})
        actions = extract_action_map(engine)
        assert actions["helm"] == 3
        assert actions["hack"] == 2

    def test_extract_no_character(self):
        engine = MagicMock()
        engine.system_id = "cbrpnk"
        engine.character = None
        engine.party = []
        assert extract_action_map(engine) == {}

    def test_extract_unknown_system_fallback(self):
        """Unknown system falls back to heuristic scanning."""
        engine = MagicMock()
        engine.system_id = "custom_rpg"
        char = MagicMock()
        char.name = "Hero"
        char.fight = 3
        char.talk = 2
        char.xp = 100  # Should be excluded
        char.stress = 4  # Should be excluded (but 4 is in range...)
        # Mock dir() to return our attributes
        char.__dir__ = lambda self: ['fight', 'talk', 'xp', 'stress']
        engine.character = char
        engine.party = [char]
        actions = extract_action_map(engine)
        assert actions["fight"] == 3
        assert actions["talk"] == 2
        assert "xp" not in actions
        assert "stress" not in actions


# =========================================================================
# SNAPSHOT ENGINE TESTS
# =========================================================================

class TestSnapshotEngine:
    def test_snapshot_basic(self):
        engine = _make_mock_engine("cbrpnk")
        layer = snapshot_engine(engine)
        assert layer.system_id == "cbrpnk"
        assert layer.dormant is False
        assert layer.action_snapshot["hack"] == 2
        assert layer.engine_state["system_id"] == "cbrpnk"
        assert layer.timestamp != ""

    def test_snapshot_preserves_all_actions(self):
        engine = _make_mock_engine("cbrpnk")
        layer = snapshot_engine(engine)
        assert len(layer.action_snapshot) == len(_SYSTEM_ACTIONS["cbrpnk"])

    def test_snapshot_no_save_state(self):
        engine = MagicMock(spec=[])
        engine.system_id = "test"
        engine.character = None
        engine.party = []
        layer = snapshot_engine(engine)
        assert layer.engine_state == {}


# =========================================================================
# SEED ACTIONS TESTS
# =========================================================================

class TestSeedActions:
    def test_seed_cbrpnk_to_sav(self):
        """CBR+PNK actions seed SaV via equivalence map and name match."""
        source_layer = MechanicLayer(
            system_id="cbrpnk",
            action_snapshot={
                "hack": 2, "override": 1, "scan": 1, "study": 0,
                "scramble": 1, "scrap": 2, "skulk": 0, "shoot": 2,
                "attune": 0, "command": 1, "consort": 0, "sway": 1,
            },
        )
        seeds = seed_actions([source_layer], "sav")

        # Direct name matches
        assert seeds["hack"] == 2       # hack -> hack
        assert seeds["scramble"] == 1   # scramble -> scramble
        assert seeds["scrap"] == 2      # scrap -> scrap (direct), shoot->scrap (equiv, max)
        assert seeds["command"] == 1    # command -> command
        assert seeds["sway"] == 1       # sway -> sway

        # Equivalence map
        assert seeds["rig"] == 1        # override -> rig
        assert seeds["study"] == 1      # scan -> study (equiv), study -> study (direct=0)

        # No source
        assert seeds["doctor"] == 0
        assert seeds["helm"] == 0

    def test_seed_bitd_to_sav(self):
        """BitD actions seed SaV correctly."""
        source_layer = MechanicLayer(
            system_id="bitd",
            action_snapshot={
                "hunt": 2, "study": 1, "survey": 2, "tinker": 1,
                "finesse": 3, "prowl": 2, "skirmish": 1, "wreck": 2,
                "attune": 1, "command": 2, "consort": 1, "sway": 2,
            },
        )
        seeds = seed_actions([source_layer], "sav")

        assert seeds["doctor"] == 2      # hunt -> doctor
        assert seeds["study"] == 2       # study direct=1, survey->study=2
        assert seeds["rig"] == 1         # tinker -> rig
        assert seeds["helm"] == 3        # finesse -> helm
        assert seeds["skulk"] == 2       # prowl -> skulk
        assert seeds["scrap"] == 2       # skirmish->scrap=1, wreck->scrap=2
        assert seeds["attune"] == 1      # direct match
        assert seeds["command"] == 2     # direct match
        assert seeds["sway"] == 2        # direct match

    def test_seed_empty_layers(self):
        seeds = seed_actions([], "sav")
        assert all(v == 0 for v in seeds.values())
        assert len(seeds) == len(_SYSTEM_ACTIONS["sav"])

    def test_seed_unknown_target(self):
        source = MechanicLayer(system_id="cbrpnk", action_snapshot={"hack": 2})
        seeds = seed_actions([source], "unknown_system")
        assert seeds == {}

    def test_seed_multiple_layers_max(self):
        """Multiple source layers use max() for each action."""
        layer1 = MechanicLayer(
            system_id="cbrpnk",
            action_snapshot={"hack": 2, "sway": 1},
        )
        layer2 = MechanicLayer(
            system_id="bitd",
            action_snapshot={"sway": 3, "prowl": 2},
        )
        seeds = seed_actions([layer1, layer2], "sav")
        assert seeds["hack"] == 2   # from layer1
        assert seeds["sway"] == 3   # max(1, 3)
        assert seeds["skulk"] == 2  # prowl -> skulk


# =========================================================================
# ACTION EQUIVALENCE MAP TESTS
# =========================================================================

class TestEquivalenceMap:
    def test_all_sources_are_known_actions(self):
        """Every source action in the map should exist in some system."""
        all_actions = set()
        for actions in _SYSTEM_ACTIONS.values():
            all_actions.update(actions)
        for source in ACTION_EQUIVALENCE_MAP:
            assert source in all_actions, f"Unknown source action: {source}"

    def test_all_targets_are_known_actions(self):
        """Every target action in the map should exist in some system."""
        all_actions = set()
        for actions in _SYSTEM_ACTIONS.values():
            all_actions.update(actions)
        for target in ACTION_EQUIVALENCE_MAP.values():
            assert target in all_actions, f"Unknown target action: {target}"


# =========================================================================
# SYSTEM ACTIONS REGISTRY TESTS
# =========================================================================

class TestSystemActions:
    def test_all_fitd_systems_have_entries(self):
        for sid in ("cbrpnk", "sav", "bitd", "bob", "candela"):
            assert sid in _SYSTEM_ACTIONS, f"Missing {sid} in _SYSTEM_ACTIONS"
            assert len(_SYSTEM_ACTIONS[sid]) > 0

    def test_no_duplicate_actions_per_system(self):
        for sid, actions in _SYSTEM_ACTIONS.items():
            assert len(actions) == len(set(actions)), \
                f"Duplicate actions in {sid}: {actions}"


# =========================================================================
# STACKED SAVE/LOAD FORMAT TESTS
# =========================================================================

class TestStackedSaveFormat:
    def test_stacked_save_format(self):
        sc = StackedCharacter(name="Kira")
        sc.add_layer("cbrpnk", {"heat": 3}, {"hack": 2, "shoot": 1})
        sc.add_layer("sav", {"crew": "smugglers"}, {"helm": 2, "hack": 2})

        # Simulate save format
        save_data = {
            "format_version": 2,
            "stacked": True,
            "active_system_id": sc.active_system_id,
            "character_name": sc.name,
            "layers": [l.to_dict() for l in sc.layers],
        }

        # Verify structure
        assert save_data["format_version"] == 2
        assert save_data["stacked"] is True
        assert save_data["active_system_id"] == "sav"
        assert len(save_data["layers"]) == 2
        assert save_data["layers"][0]["dormant"] is True
        assert save_data["layers"][1]["dormant"] is False

    def test_backward_compat_legacy_save(self):
        """Legacy (non-stacked) saves don't have 'stacked' key."""
        legacy_save = {
            "system_id": "bitd",
            "character": {"name": "Test"},
        }
        assert not legacy_save.get("stacked")

    def test_load_stacked_save(self):
        """Verify stacked save can be reconstructed."""
        save_data = {
            "format_version": 2,
            "stacked": True,
            "active_system_id": "sav",
            "character_name": "Kira",
            "layers": [
                {
                    "system_id": "cbrpnk",
                    "dormant": True,
                    "timestamp": "2026-03-09T12:00:00",
                    "engine_state": {"heat": 3},
                    "action_snapshot": {"hack": 2, "override": 1},
                },
                {
                    "system_id": "sav",
                    "dormant": False,
                    "timestamp": "2026-03-09T14:00:00",
                    "engine_state": {"crew": "smugglers"},
                    "action_snapshot": {"hack": 2, "rig": 1},
                },
            ],
        }

        sc = StackedCharacter(
            name=save_data["character_name"],
            active_system_id=save_data["active_system_id"],
        )
        sc.layers = [MechanicLayer.from_dict(l) for l in save_data["layers"]]

        assert sc.name == "Kira"
        assert sc.active_system_id == "sav"
        assert len(sc.layers) == 2
        assert sc.get_active_layer().system_id == "sav"
        assert sc.get_layer("cbrpnk").dormant is True
        assert sc.merged_actions()["hack"] == 2
        assert sc.merged_actions()["override"] == 1
        assert sc.merged_actions()["rig"] == 1


# =========================================================================
# MODULE MANIFEST SYSTEM TRANSITIONS TESTS
# =========================================================================

class TestModuleManifestTransitions:
    def test_manifest_transitions_field(self):
        from codex.spatial.module_manifest import ModuleManifest
        mm = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="cbrpnk",
            system_transitions=[
                {"target_system": "sav", "trigger": "zone_complete", "zone_id": "escape_pod"},
            ],
        )
        assert len(mm.system_transitions) == 1
        assert mm.system_transitions[0]["target_system"] == "sav"

    def test_manifest_transitions_serialization(self):
        from codex.spatial.module_manifest import ModuleManifest
        mm = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="cbrpnk",
            system_transitions=[
                {"target_system": "sav", "trigger": "zone_complete", "zone_id": "escape_pod"},
            ],
        )
        data = mm.to_dict()
        assert "system_transitions" in data
        assert len(data["system_transitions"]) == 1

        restored = ModuleManifest.from_dict(data)
        assert len(restored.system_transitions) == 1
        assert restored.system_transitions[0]["target_system"] == "sav"

    def test_manifest_transitions_default_empty(self):
        from codex.spatial.module_manifest import ModuleManifest
        mm = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="dnd5e",
        )
        assert mm.system_transitions == []
        data = mm.to_dict()
        assert "system_transitions" not in data  # Omitted when empty

    def test_manifest_transitions_backward_compat(self):
        """Old manifests without system_transitions load cleanly."""
        from codex.spatial.module_manifest import ModuleManifest
        data = {
            "module_id": "old_mod",
            "display_name": "Old Module",
            "system_id": "bitd",
            "chapters": [],
        }
        mm = ModuleManifest.from_dict(data)
        assert mm.system_transitions == []


# =========================================================================
# ENGINE PROTOCOL STACKABLE TESTS
# =========================================================================

class TestStackableProtocol:
    def test_stackable_protocol_exists(self):
        from codex.core.engine_protocol import StackableEngine
        assert hasattr(StackableEngine, 'get_action_map')

    def test_runtime_checkable(self):
        from codex.core.engine_protocol import StackableEngine

        class GoodEngine:
            def get_action_map(self) -> dict:
                return {"hack": 2}

        assert isinstance(GoodEngine(), StackableEngine)


# =========================================================================
# INTEGRATION TESTS
# =========================================================================

class TestIntegration:
    def test_full_transition_flow(self):
        """Simulate: CBR+PNK -> snapshot -> seed SaV -> stacked char."""
        # Start with CBR+PNK
        cbrpnk_engine = _make_mock_engine("cbrpnk", {
            "hack": 2, "override": 1, "scan": 1, "study": 0,
            "scramble": 1, "scrap": 2, "skulk": 0, "shoot": 2,
            "attune": 0, "command": 1, "consort": 0, "sway": 1,
        })

        # Snapshot
        layer = snapshot_engine(cbrpnk_engine)
        assert layer.system_id == "cbrpnk"
        assert layer.action_snapshot["hack"] == 2

        # Create stacked char
        sc = StackedCharacter(name="Kira")
        layer.dormant = True
        sc.layers.append(layer)

        # Seed SaV
        seeds = seed_actions(sc.layers, "sav")
        assert seeds["hack"] == 2   # direct
        assert seeds["rig"] == 1    # override -> rig
        assert seeds["scrap"] == 2  # max(scrap=2, shoot->scrap=2)

        # Add SaV layer
        sc.add_layer("sav", {"crew": "test"}, seeds)

        # Verify merged
        merged = sc.merged_actions()
        assert merged["hack"] == 2
        assert merged["override"] == 1    # CBR+PNK only
        assert merged["rig"] == 1          # SaV only (seeded)
        assert merged["shoot"] == 2        # CBR+PNK only

        # Verify serialization
        data = sc.to_dict()
        restored = StackedCharacter.from_dict(data)
        assert len(restored.layers) == 2
        assert restored.merged_actions() == merged

    def test_dispatcher_with_real_command_patterns(self):
        """Test dispatcher with engine-like command patterns."""
        active = MagicMock()
        active.system_id = "sav"
        active.display_name = "Scum and Villainy"

        dormant = MagicMock()
        dormant.system_id = "cbrpnk"
        dormant.display_name = "CBR+PNK"

        # SaV handles ship_status, CBR+PNK handles chrome_status
        def active_handler(cmd, **kw):
            if cmd == "ship_status":
                return "Ship: Crimson Wake, Hull: 8/10"
            return f"Unknown command: {cmd}"

        def dormant_handler(cmd, **kw):
            if cmd == "chrome_status":
                return "Chrome installed: Reflex Booster, Cyberdeck"
            return f"Unknown command: {cmd}"

        active.handle_command = active_handler
        dormant.handle_command = dormant_handler

        d = StackedCommandDispatcher(active, [dormant])

        # Active command
        assert "Crimson Wake" in d.dispatch("ship_status")

        # Dormant fallthrough
        result = d.dispatch("chrome_status")
        assert "[CBR+PNK]" in result
        assert "Reflex Booster" in result

        # Unknown in both
        assert "Unknown command" in d.dispatch("nonexistent")

    def test_three_layer_stack(self):
        """CBR+PNK -> SaV -> BitD triple stack."""
        sc = StackedCharacter(name="Traveler")

        # Layer 1: CBR+PNK
        sc.add_layer("cbrpnk", {}, {"hack": 3, "shoot": 2, "sway": 1})
        assert sc.active_system_id == "cbrpnk"

        # Layer 2: SaV (seeded)
        seeds_sav = seed_actions(sc.layers, "sav")
        sc.add_layer("sav", {}, seeds_sav)
        assert sc.layers[0].dormant is True
        assert sc.active_system_id == "sav"

        # Layer 3: BitD (seeded from both prior)
        seeds_bitd = seed_actions(sc.layers, "bitd")
        sc.add_layer("bitd", {}, seeds_bitd)
        assert len(sc.layers) == 3
        assert sc.layers[0].dormant is True
        assert sc.layers[1].dormant is True
        assert sc.layers[2].dormant is False

        merged = sc.merged_actions()
        assert merged["hack"] == 3  # From CBR+PNK layer
        assert merged["shoot"] == 2  # From CBR+PNK layer


# =========================================================================
# COMPATIBILITY GATE TESTS
# =========================================================================

class TestCompatibilityGate:
    def test_can_stack_fitd_family(self):
        """BitD + SaV are both FITD — should stack."""
        assert can_stack("bitd", "sav") is True

    def test_can_stack_cbrpnk_candela(self):
        """CBR+PNK + Candela are both FITD — should stack."""
        assert can_stack("cbrpnk", "candela") is True

    def test_cannot_stack_dnd5e_fitd(self):
        """D&D 5e + BitD are different families — cannot stack."""
        assert can_stack("dnd5e", "bitd") is False

    def test_cannot_stack_dnd5e_stc(self):
        """D&D 5e + STC are different families — cannot stack."""
        assert can_stack("dnd5e", "stc") is False

    def test_cannot_stack_burnwillow_fitd(self):
        """Burnwillow + BitD are different families — cannot stack."""
        assert can_stack("burnwillow", "bitd") is False

    def test_can_stack_symmetric(self):
        """can_stack is symmetric: A->B == B->A."""
        assert can_stack("sav", "bob") is True
        assert can_stack("bob", "sav") is True

    def test_stackable_families_contains_fitd(self):
        """STACKABLE_FAMILIES has the fitd group with all 5 systems."""
        assert "fitd" in STACKABLE_FAMILIES
        assert STACKABLE_FAMILIES["fitd"] == frozenset(
            {"bitd", "sav", "bob", "cbrpnk", "candela"}
        )

    def test_add_layer_rejects_incompatible(self):
        """IncompatibleStackError raised when stacking D&D 5e onto FITD."""
        sc = StackedCharacter(name="Test")
        sc.add_layer("bitd", {}, {"hunt": 2})
        with pytest.raises(IncompatibleStackError) as exc_info:
            sc.add_layer("dnd5e", {}, {"strength": 14})
        assert "dnd5e" in str(exc_info.value)
        assert "bitd" in str(exc_info.value)

    def test_seed_actions_returns_empty_for_incompatible(self):
        """seed_actions() returns {} when source→target is incompatible."""
        source = MechanicLayer(system_id="dnd5e", action_snapshot={"strength": 14})
        result = seed_actions([source], "bitd")
        assert result == {}


# =========================================================================
# SHARED CLOCK TESTS
# =========================================================================

class TestSharedClocks:
    def test_shared_clock_add_get(self):
        """Add a clock and retrieve it by name."""
        sc = StackedCharacter(name="Hero")
        clock = UniversalClock(name="Faction War", max_segments=8, filled=3)
        sc.add_clock(clock)
        retrieved = sc.get_clock("Faction War")
        assert retrieved is clock
        assert retrieved.filled == 3
        assert retrieved.max_segments == 8

    def test_shared_clock_remove(self):
        """Remove a clock by name."""
        sc = StackedCharacter(name="Hero")
        sc.add_clock(UniversalClock(name="Doom", filled=5))
        assert sc.get_clock("Doom") is not None
        sc.remove_clock("Doom")
        assert sc.get_clock("Doom") is None
        # Removing again is a no-op
        sc.remove_clock("Doom")

    def test_shared_clock_serialization(self):
        """Clocks survive to_dict/from_dict roundtrip."""
        sc = StackedCharacter(name="Hero")
        sc.add_layer("bitd", {}, {"hunt": 2})
        sc.add_clock(UniversalClock(name="Heat", max_segments=6, filled=4))
        sc.add_clock(UniversalClock(name="Campaign", filled=12,
                                     thresholds={5: "Act 1", 10: "Act 2"}))

        data = sc.to_dict()
        assert "shared_clocks" in data
        assert "Heat" in data["shared_clocks"]
        assert "Campaign" in data["shared_clocks"]

        restored = StackedCharacter.from_dict(data)
        heat = restored.get_clock("Heat")
        assert heat is not None
        assert heat.filled == 4
        assert heat.max_segments == 6

        campaign = restored.get_clock("Campaign")
        assert campaign is not None
        assert campaign.filled == 12
        assert 5 in campaign.thresholds

    def test_shared_clock_persists_across_transitions(self):
        """Clocks survive adding new layers."""
        sc = StackedCharacter(name="Hero")
        sc.add_layer("bitd", {}, {"hunt": 2})
        clock = UniversalClock(name="Faction War", max_segments=8, filled=3)
        sc.add_clock(clock)

        # Transition to SaV
        sc.add_layer("sav", {}, {"helm": 1})

        # Clock persists
        assert sc.get_clock("Faction War") is clock
        assert sc.get_clock("Faction War").filled == 3

        # Advance it
        sc.get_clock("Faction War").tick(2)
        assert sc.get_clock("Faction War").filled == 5

"""
tests/test_scene_interaction.py — Scene interaction, save fix, and FITD scene state tests.
============================================================================================

Covers:
  - Bridge scene commands: talk, investigate, perceive, unlock, services, event
  - Enhanced look (NPCs, services, DC hints)
  - Enhanced move (event triggers on entry)
  - Save fix: save_state instead of save_game
  - FITD scene state: navigation, zone advancement

WO-V52.0: Scene Interaction + FITD Narrative Runner + Save Fix
"""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================
# Mock engine factory
# =========================================================================

def _make_room_node(room_type="NORMAL", x=0, y=0, width=10, height=10,
                     connections=None):
    """Create a mock room node with spatial data for minimap rendering."""
    node = SimpleNamespace(
        room_type=SimpleNamespace(name=room_type),
        x=x, y=y, width=width, height=height,
        connections=connections or set(),
        content_hints=None,
    )
    return node


def _make_mock_engine(room_content=None, system_id="dnd5e"):
    """Build a mock engine with a single room containing given content."""
    engine = MagicMock()
    engine.system_id = system_id
    engine.display_name = "Test Engine"
    engine.current_room_id = 1

    # Character
    char = MagicMock()
    char.name = "TestHero"
    char.current_hp = 20
    char.max_hp = 20
    char.is_alive.return_value = True
    engine.character = char

    # Room nodes with spatial data
    room_node_1 = _make_room_node(x=0, y=0, connections={2})
    room_node_2 = _make_room_node(x=20, y=0, connections={1})
    engine.get_current_room.return_value = room_node_1

    # Exits
    engine.get_cardinal_exits.return_value = [
        {"direction": "N", "id": 2, "type": "NORMAL"},
    ]

    # Dungeon graph
    graph = MagicMock()
    graph.rooms = {1: room_node_1, 2: room_node_2}
    engine.dungeon_graph = graph

    # Visited rooms
    engine.visited_rooms = {1}

    # Populated rooms
    content = room_content or {}
    pop = SimpleNamespace(content=content)
    engine.populated_rooms = {1: pop}

    # roll_check
    engine.roll_check.return_value = {"success": True, "total": 18, "modifier": 2}

    # save_state
    engine.save_state.return_value = {"system_id": system_id, "test": True}

    return engine


def _make_bridge(engine):
    """Create a UniversalGameBridge wrapping a pre-initialized engine."""
    from codex.games.bridge import UniversalGameBridge
    from codex.core.mechanics.rest import RestManager

    bridge = object.__new__(UniversalGameBridge)
    bridge.engine = engine
    bridge.dead = False
    bridge.last_frame = None
    bridge._broadcast = None
    bridge._system_tag = engine.system_id.upper()
    bridge._rest_mgr = RestManager()
    bridge._butler = None
    bridge.show_dm_notes = False  # WO-V54.0
    bridge._talking_to = None    # WO-V54.0
    bridge._session_log = []     # WO-V61.0
    return bridge


# =========================================================================
# Bridge scene commands
# =========================================================================

class TestTalkCommand:
    """talk / npc command tests."""

    def test_talk_no_arg_lists_npcs(self):
        engine = _make_mock_engine(room_content={
            "npcs": [
                {"name": "Durnan", "role": "innkeeper", "dialogue": "Welcome!"},
                {"name": "Volo", "role": "author"},
            ],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("talk")
        assert "Durnan" in result
        assert "Volo" in result
        assert "innkeeper" in result

    def test_talk_with_name_shows_dialogue(self):
        engine = _make_mock_engine(room_content={
            "npcs": [
                {"name": "Durnan", "role": "innkeeper", "dialogue": "Welcome to the Yawning Portal!"},
            ],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("talk durnan")
        assert "Welcome to the Yawning Portal!" in result
        assert "Durnan" in result

    def test_talk_case_insensitive_substring(self):
        engine = _make_mock_engine(room_content={
            "npcs": [
                {"name": "Fixer Mara Chen", "role": "quest_giver", "dialogue": "Got a job for you."},
            ],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("talk mara")
        assert "Got a job for you." in result

    def test_talk_unknown_npc(self):
        engine = _make_mock_engine(room_content={
            "npcs": [
                {"name": "Durnan", "role": "innkeeper"},
            ],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("talk gandalf")
        assert "No NPC named" in result

    def test_talk_no_npcs_in_room(self):
        engine = _make_mock_engine(room_content={})
        bridge = _make_bridge(engine)
        result = bridge.step("talk")
        assert "no npcs" in result.lower()

    def test_npc_alias_works(self):
        engine = _make_mock_engine(room_content={
            "npcs": [
                {"name": "Bartender", "dialogue": "What'll it be?"},
            ],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("npc bartender")
        assert "What'll it be?" in result


class TestInvestigateCommand:
    """investigate command tests."""

    def test_investigate_success(self):
        engine = _make_mock_engine(room_content={
            "investigation_dc": 15,
            "investigation_success": "You find a hidden compartment!",
        })
        engine.roll_check.return_value = {"success": True, "total": 18}
        bridge = _make_bridge(engine)
        result = bridge.step("investigate")
        assert "hidden compartment" in result
        assert "successful" in result.lower()

    def test_investigate_clears_dc(self):
        content = {
            "investigation_dc": 15,
            "investigation_success": "Found it!",
        }
        engine = _make_mock_engine(room_content=content)
        engine.roll_check.return_value = {"success": True, "total": 18}
        bridge = _make_bridge(engine)
        bridge.step("investigate")
        # DC should be cleared
        assert content["investigation_dc"] == 0
        # Second attempt should say nothing to investigate
        result = bridge.step("investigate")
        assert "Nothing to investigate" in result

    def test_investigate_failure(self):
        engine = _make_mock_engine(room_content={
            "investigation_dc": 20,
            "investigation_success": "Secret found!",
        })
        engine.roll_check.return_value = {"success": False, "total": 8}
        bridge = _make_bridge(engine)
        result = bridge.step("investigate")
        assert "nothing" in result.lower()
        assert "Secret found" not in result

    def test_investigate_no_dc(self):
        engine = _make_mock_engine(room_content={})
        bridge = _make_bridge(engine)
        result = bridge.step("investigate")
        assert "Nothing to investigate" in result


class TestPerceiveCommand:
    """perceive / perception command tests."""

    def test_perceive_success(self):
        engine = _make_mock_engine(room_content={
            "perception_dc": 12,
            "perception_success": "You notice a tripwire!",
        })
        engine.roll_check.return_value = {"success": True, "total": 15}
        bridge = _make_bridge(engine)
        result = bridge.step("perceive")
        assert "tripwire" in result

    def test_perceive_failure(self):
        engine = _make_mock_engine(room_content={
            "perception_dc": 18,
            "perception_success": "Trap detected!",
        })
        engine.roll_check.return_value = {"success": False, "total": 10}
        bridge = _make_bridge(engine)
        result = bridge.step("perceive")
        assert "unusual" in result.lower()
        assert "Trap detected" not in result

    def test_perception_alias(self):
        engine = _make_mock_engine(room_content={
            "perception_dc": 10,
            "perception_success": "Found!",
        })
        engine.roll_check.return_value = {"success": True, "total": 15}
        bridge = _make_bridge(engine)
        result = bridge.step("perception")
        assert "Found!" in result


class TestUnlockCommand:
    """unlock / lockpick command tests."""

    def test_unlock_success(self):
        content = {"lock_dc": 15}
        engine = _make_mock_engine(room_content=content)
        engine.roll_check.return_value = {"success": True, "total": 17}
        bridge = _make_bridge(engine)
        result = bridge.step("unlock")
        assert "opened" in result.lower()
        assert content["lock_dc"] == 0

    def test_unlock_failure(self):
        engine = _make_mock_engine(room_content={"lock_dc": 20})
        engine.roll_check.return_value = {"success": False, "total": 8}
        bridge = _make_bridge(engine)
        result = bridge.step("unlock")
        assert "holds firm" in result.lower()

    def test_unlock_no_lock(self):
        engine = _make_mock_engine(room_content={})
        bridge = _make_bridge(engine)
        result = bridge.step("unlock")
        assert "nothing locked" in result.lower()

    def test_lockpick_alias(self):
        engine = _make_mock_engine(room_content={"lock_dc": 12})
        engine.roll_check.return_value = {"success": True, "total": 15}
        bridge = _make_bridge(engine)
        result = bridge.step("lockpick")
        assert "opened" in result.lower()


class TestServicesCommand:
    """services command tests."""

    def test_services_lists_room_services(self):
        engine = _make_mock_engine(room_content={
            "services": ["drinks", "job_briefing", "intel_purchase"],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("services")
        assert "drinks" in result
        assert "job_briefing" in result
        assert "intel_purchase" in result

    def test_services_empty(self):
        engine = _make_mock_engine(room_content={})
        bridge = _make_bridge(engine)
        result = bridge.step("services")
        assert "No services" in result


class TestEventCommand:
    """event command tests."""

    def test_event_shows_triggers(self):
        engine = _make_mock_engine(room_content={
            "event_triggers": ["A shadowy figure approaches.", "The door slams shut."],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("event")
        assert "shadowy figure" in result
        assert "door slams" in result

    def test_event_empty(self):
        engine = _make_mock_engine(room_content={})
        bridge = _make_bridge(engine)
        result = bridge.step("event")
        assert "No events" in result


# =========================================================================
# Enhanced look
# =========================================================================

class TestEnhancedLook:
    """_handle_look() shows NPCs, services, and DC hints."""

    def test_look_shows_npcs(self):
        engine = _make_mock_engine(room_content={
            "description": "A tavern.",
            "npcs": [
                {"name": "Durnan", "role": "innkeeper"},
            ],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("look")
        assert "Durnan" in result
        assert "innkeeper" in result
        assert "NPCS" in result

    def test_look_shows_services(self):
        engine = _make_mock_engine(room_content={
            "description": "A market.",
            "services": ["weapons", "potions"],
        })
        bridge = _make_bridge(engine)
        result = bridge.step("look")
        assert "SERVICES" in result
        assert "weapons" in result

    def test_look_shows_investigation_hint(self):
        engine = _make_mock_engine(room_content={
            "investigation_dc": 15,
        })
        bridge = _make_bridge(engine)
        result = bridge.step("look")
        assert "investigated" in result

    def test_look_shows_perception_hint(self):
        engine = _make_mock_engine(room_content={
            "perception_dc": 12,
        })
        bridge = _make_bridge(engine)
        result = bridge.step("look")
        assert "hidden" in result

    def test_look_shows_lock_hint(self):
        engine = _make_mock_engine(room_content={
            "lock_dc": 15,
        })
        bridge = _make_bridge(engine)
        result = bridge.step("look")
        assert "lock" in result.lower()


# =========================================================================
# Enhanced move
# =========================================================================

class TestEnhancedMove:
    """_handle_move() shows event triggers on room entry."""

    def test_move_shows_event_trigger(self):
        # Set up room 2 content with event triggers
        engine = _make_mock_engine(room_content={})
        room2_content = {"event_triggers": ["A trap springs!"], "description": "Dark hall."}
        pop2 = SimpleNamespace(content=room2_content)
        engine.populated_rooms[2] = pop2

        bridge = _make_bridge(engine)

        # Override get_current_room for the move destination
        def side_effect():
            return engine.dungeon_graph.rooms.get(engine.current_room_id)
        engine.get_current_room.side_effect = side_effect

        # Move will update current_room_id via move_to_room mock
        def move_side_effect(rid):
            engine.current_room_id = rid
        engine.move_to_room.side_effect = move_side_effect

        result = bridge.step("n")
        assert "trap springs" in result.lower()


# =========================================================================
# Save fix
# =========================================================================

class TestSaveFix:
    """_handle_save() uses save_state (not save_game)."""

    def test_save_calls_save_state(self, tmp_path):
        engine = _make_mock_engine()
        engine.save_state.return_value = {"test": True}
        bridge = _make_bridge(engine)

        with patch("codex.games.bridge._SAVES_DIR", tmp_path):
            result = bridge.step("save")
        assert "saved" in result.lower()
        engine.save_state.assert_called_once()

    def test_save_writes_json(self, tmp_path):
        engine = _make_mock_engine()
        engine.save_state.return_value = {"system_id": "dnd5e", "hp": 20}
        bridge = _make_bridge(engine)

        with patch("codex.games.bridge._SAVES_DIR", tmp_path):
            bridge.step("save")

        save_file = tmp_path / "dnd5e_save.json"
        assert save_file.exists()
        data = json.loads(save_file.read_text())
        assert data["system_id"] == "dnd5e"
        assert data["hp"] == 20

    def test_save_no_save_state(self):
        engine = _make_mock_engine()
        del engine.save_state
        bridge = _make_bridge(engine)
        result = bridge.step("save")
        assert "not supported" in result.lower()


# =========================================================================
# FITD Scene State
# =========================================================================

def _make_mock_graph(num_rooms=3, with_hints=True):
    """Build a mock DungeonGraph with content_hints on rooms."""
    rooms = {}
    for i in range(num_rooms):
        room = MagicMock()
        room.room_type = SimpleNamespace(name="NORMAL")
        if with_hints:
            room.content_hints = {
                "description": f"Scene {i} description.",
                "npcs": [{"name": f"NPC_{i}", "role": "test", "dialogue": f"Hello from scene {i}"}],
                "services": [f"service_{i}"],
                "event_triggers": [f"Event {i} occurs."],
                "investigation_dc": 10 + i,
            }
        else:
            room.content_hints = None
        rooms[i] = room

    graph = MagicMock()
    graph.rooms = rooms
    return graph


def _make_mock_zone_manager(graphs=None, module_name="Test Module",
                             chapter_name="Chapter 1"):
    """Build a mock ZoneManager that returns predefined graphs."""
    zm = MagicMock()
    zm.module_name = module_name
    zm.chapter_name = chapter_name
    zm.zone_name = "test_zone"
    zm.module_complete = False
    zm.zone_progress = "Chapter 1/1, Zone 1/1"

    _graphs = list(graphs) if graphs else [_make_mock_graph()]
    _graph_idx = [0]

    def load_zone():
        if _graph_idx[0] < len(_graphs):
            g = _graphs[_graph_idx[0]]
            return g
        return None

    def advance():
        _graph_idx[0] += 1
        if _graph_idx[0] >= len(_graphs):
            zm.module_complete = True
            return None
        zm.chapter_name = f"Chapter {_graph_idx[0] + 1}"
        return MagicMock()  # ZoneEntry

    zm.load_current_zone.side_effect = load_zone
    zm.advance.side_effect = advance

    return zm


class TestFITDSceneState:
    """_FITDSceneState navigation and zone progression."""

    def test_loads_scenes_from_graph(self):
        from play_universal import _FITDSceneState
        zm = _make_mock_zone_manager()
        ss = _FITDSceneState(zm, "/tmp/test")
        assert ss.scene_count() == 3

    def test_current_scene_returns_scene_data(self):
        from play_universal import _FITDSceneState
        zm = _make_mock_zone_manager()
        ss = _FITDSceneState(zm, "/tmp/test")
        scene = ss.current_scene()
        assert scene is not None
        assert scene.description == "Scene 0 description."

    def test_advance_scene_progresses(self):
        from play_universal import _FITDSceneState
        zm = _make_mock_zone_manager()
        ss = _FITDSceneState(zm, "/tmp/test")
        ss.current_scene()  # Visit scene 0
        scene = ss.advance_scene()
        assert scene is not None
        assert ss.scene_idx == 1
        assert scene.description == "Scene 1 description."

    def test_advance_scene_returns_none_at_zone_end(self):
        from play_universal import _FITDSceneState
        graph = _make_mock_graph(num_rooms=2)
        zm = _make_mock_zone_manager(graphs=[graph])
        ss = _FITDSceneState(zm, "/tmp/test")
        ss.advance_scene()  # Go to scene 1
        result = ss.advance_scene()  # Past end
        assert result is None

    def test_visited_tracking(self):
        from play_universal import _FITDSceneState
        zm = _make_mock_zone_manager()
        ss = _FITDSceneState(zm, "/tmp/test")
        assert ss.visited_count() == 0
        ss.current_scene()
        assert ss.visited_count() == 1
        ss.advance_scene()
        assert ss.visited_count() == 2

    def test_advance_zone_loads_next(self):
        from play_universal import _FITDSceneState
        graph1 = _make_mock_graph(num_rooms=2)
        graph2 = _make_mock_graph(num_rooms=4)
        zm = _make_mock_zone_manager(graphs=[graph1, graph2])
        ss = _FITDSceneState(zm, "/tmp/test")
        assert ss.scene_count() == 2  # First graph
        result = ss.advance_zone()
        assert result is True
        assert ss.scene_count() == 4  # Second graph
        assert ss.scene_idx == 0  # Reset

    def test_advance_zone_returns_false_at_module_end(self):
        from play_universal import _FITDSceneState
        zm = _make_mock_zone_manager(graphs=[_make_mock_graph(num_rooms=1)])
        ss = _FITDSceneState(zm, "/tmp/test")
        result = ss.advance_zone()
        assert result is False

    def test_format_scene_displays_content(self):
        from play_universal import _FITDSceneState
        zm = _make_mock_zone_manager()
        ss = _FITDSceneState(zm, "/tmp/test")
        scene = ss.current_scene()
        text = ss.format_scene(scene)
        assert "Scene 0 description" in text
        assert "NPC_0" in text
        assert "service_0" in text
        assert "Event 0 occurs" in text

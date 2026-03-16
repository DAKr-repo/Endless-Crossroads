"""
tests/test_bridge_movement.py — WO-V49.0
=========================================
Tests for:
1. Movement direction normalization (short-form and long-form exits)
2. System-aware help text
"""
from unittest.mock import MagicMock, patch, PropertyMock
import pytest


# ---------------------------------------------------------------------------
# Helpers — build a minimal mock engine
# ---------------------------------------------------------------------------

class _FakeRoom:
    """Minimal room node for minimap rendering."""
    def __init__(self, rid, x=0, y=0, connections=None):
        self.id = rid
        self.x = x
        self.y = y
        self.width = 3
        self.height = 3
        self.connections = connections or set()
        self.room_type = MagicMock()
        self.room_type.name = "NORMAL"
        self.is_locked = False
        self.tier = 1


def _make_mock_engine(system_id="dnd5e", exits=None, room_type="NORMAL"):
    """Create a mock engine with configurable cardinal exits."""
    engine = MagicMock()
    engine.system_id = system_id
    engine.display_name = system_id.upper()
    engine.current_room_id = 1
    engine.visited_rooms = {1}
    engine.character = MagicMock()
    engine.character.current_hp = 20
    engine.character.max_hp = 20
    engine.character.name = "Tester"
    engine.character.is_alive.return_value = True

    # Dungeon graph with real room coordinates for minimap
    r1 = _FakeRoom(1, x=0, y=0, connections={2, 3})
    r2 = _FakeRoom(2, x=0, y=-1, connections={1})
    r3 = _FakeRoom(3, x=1, y=0, connections={1})
    engine.dungeon_graph = MagicMock()
    engine.dungeon_graph.rooms = {1: r1, 2: r2, 3: r3}

    # Room node for look/status
    room_node = MagicMock()
    room_node.room_type.name = room_type
    engine.get_current_room.return_value = room_node

    # Populated rooms
    pop = MagicMock()
    pop.content = {"description": "A test room.", "enemies": [], "loot": []}
    engine.populated_rooms = {1: pop, 2: pop, 3: pop}

    # Exits — default to long-form (D&D 5e / STC style)
    if exits is None:
        exits = [
            {"direction": "north", "id": 2, "type": "NORMAL", "tier": 1},
            {"direction": "east", "id": 3, "type": "NORMAL", "tier": 1},
        ]
    engine.get_cardinal_exits.return_value = exits

    # move_to_room changes current_room_id
    def _move(room_id):
        engine.current_room_id = room_id
        engine.visited_rooms.add(room_id)
        return True
    engine.move_to_room.side_effect = _move

    return engine


def _make_bridge(engine):
    """Create a UniversalGameBridge wrapping a mock engine (bypass __init__)."""
    from codex.games.bridge import UniversalGameBridge
    from codex.core.mechanics.rest import RestManager

    bridge = object.__new__(UniversalGameBridge)
    bridge.engine = engine
    bridge.dead = False
    bridge.last_frame = None
    bridge._broadcast = None
    bridge._system_tag = engine.system_id.upper()
    bridge._rest_mgr = RestManager()
    bridge._butler = None  # WO-V50.0
    bridge.show_dm_notes = False  # WO-V54.0
    bridge._talking_to = None    # WO-V54.0
    bridge._session_log = []     # WO-V61.0
    return bridge


# =========================================================================
# Movement — long-form exits (D&D 5e / STC)
# =========================================================================

class TestMovementLongFormExits:
    """Engine returns lowercase long-form directions like 'north', 'east'."""

    def test_move_north_with_n(self):
        engine = _make_mock_engine(exits=[
            {"direction": "north", "id": 2, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        result = bridge.step("n")
        engine.move_to_room.assert_called_once_with(2)

    def test_move_north_with_full_word(self):
        engine = _make_mock_engine(exits=[
            {"direction": "north", "id": 2, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        result = bridge.step("north")
        engine.move_to_room.assert_called_once_with(2)

    def test_move_south(self):
        engine = _make_mock_engine(exits=[
            {"direction": "south", "id": 3, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("s")
        engine.move_to_room.assert_called_once_with(3)

    def test_move_east(self):
        engine = _make_mock_engine(exits=[
            {"direction": "east", "id": 4, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("e")
        engine.move_to_room.assert_called_once_with(4)

    def test_move_west(self):
        engine = _make_mock_engine(exits=[
            {"direction": "west", "id": 5, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("w")
        engine.move_to_room.assert_called_once_with(5)

    def test_move_to_nonexistent_direction(self):
        engine = _make_mock_engine(exits=[
            {"direction": "north", "id": 2, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        result = bridge.step("s")
        engine.move_to_room.assert_not_called()
        assert "can't go" in result.lower()

    def test_multiple_exits_selects_correct(self):
        engine = _make_mock_engine(exits=[
            {"direction": "north", "id": 2, "type": "NORMAL", "tier": 1},
            {"direction": "south", "id": 3, "type": "NORMAL", "tier": 1},
            {"direction": "east", "id": 4, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("e")
        engine.move_to_room.assert_called_once_with(4)


# =========================================================================
# Movement — short-form exits (Burnwillow)
# =========================================================================

class TestMovementShortFormExits:
    """Engine returns uppercase short-form directions like 'N', 'E'."""

    def test_move_north_short_form_exit(self):
        engine = _make_mock_engine(system_id="burnwillow", exits=[
            {"direction": "N", "id": 2, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("n")
        engine.move_to_room.assert_called_once_with(2)

    def test_move_south_short_form_exit(self):
        engine = _make_mock_engine(system_id="burnwillow", exits=[
            {"direction": "S", "id": 3, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("s")
        engine.move_to_room.assert_called_once_with(3)

    def test_move_east_short_form_exit(self):
        engine = _make_mock_engine(system_id="burnwillow", exits=[
            {"direction": "E", "id": 4, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("e")
        engine.move_to_room.assert_called_once_with(4)

    def test_move_west_short_form_exit(self):
        engine = _make_mock_engine(system_id="burnwillow", exits=[
            {"direction": "W", "id": 5, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("w")
        engine.move_to_room.assert_called_once_with(5)

    def test_move_northeast_short_form(self):
        engine = _make_mock_engine(system_id="burnwillow", exits=[
            {"direction": "NE", "id": 6, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("ne")
        engine.move_to_room.assert_called_once_with(6)

    def test_nonexistent_direction_short_form(self):
        engine = _make_mock_engine(system_id="burnwillow", exits=[
            {"direction": "N", "id": 2, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        result = bridge.step("w")
        engine.move_to_room.assert_not_called()
        assert "can't go" in result.lower()


# =========================================================================
# Movement — mixed / diagonal long-form
# =========================================================================

class TestMovementDiagonal:
    """Diagonal movement in both exit formats."""

    def test_northeast_long_form(self):
        engine = _make_mock_engine(exits=[
            {"direction": "northeast", "id": 7, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("ne")
        engine.move_to_room.assert_called_once_with(7)

    def test_southwest_long_form(self):
        engine = _make_mock_engine(exits=[
            {"direction": "southwest", "id": 8, "type": "NORMAL", "tier": 1},
        ])
        bridge = _make_bridge(engine)
        bridge.step("sw")
        engine.move_to_room.assert_called_once_with(8)


# =========================================================================
# Help Text — system-aware
# =========================================================================

class TestHelpText:
    """Help text varies by system."""

    def test_burnwillow_help_includes_push(self):
        engine = _make_mock_engine(system_id="burnwillow")
        bridge = _make_bridge(engine)
        result = bridge.step("help")
        assert "push" in result.lower()

    def test_burnwillow_help_includes_use(self):
        engine = _make_mock_engine(system_id="burnwillow")
        bridge = _make_bridge(engine)
        result = bridge.step("help")
        assert "use" in result.lower()

    def test_burnwillow_help_includes_search(self):
        engine = _make_mock_engine(system_id="burnwillow")
        bridge = _make_bridge(engine)
        result = bridge.step("help")
        assert "search" in result.lower()

    def test_dnd5e_help_includes_hitdice(self):
        engine = _make_mock_engine(system_id="dnd5e")
        bridge = _make_bridge(engine)
        result = bridge.step("help")
        assert "hitdice" in result.lower()

    def test_dnd5e_help_excludes_push(self):
        engine = _make_mock_engine(system_id="dnd5e")
        bridge = _make_bridge(engine)
        result = bridge.step("help")
        assert "push" not in result.lower()

    def test_stc_help_excludes_push(self):
        engine = _make_mock_engine(system_id="stc")
        bridge = _make_bridge(engine)
        result = bridge.step("help")
        assert "push" not in result.lower()

    def test_stc_help_excludes_hitdice(self):
        engine = _make_mock_engine(system_id="stc")
        bridge = _make_bridge(engine)
        result = bridge.step("help")
        assert "hitdice" not in result.lower()

    def test_all_systems_have_movement_commands(self):
        for sid in ("burnwillow", "dnd5e", "stc"):
            engine = _make_mock_engine(system_id=sid)
            bridge = _make_bridge(engine)
            result = bridge.step("help")
            assert "n/s/e/w" in result.lower()
            assert "attack" in result.lower()
            assert "rest" in result.lower()

    def test_all_systems_have_save(self):
        for sid in ("burnwillow", "dnd5e", "stc"):
            engine = _make_mock_engine(system_id=sid)
            bridge = _make_bridge(engine)
            result = bridge.step("help")
            assert "save" in result.lower()

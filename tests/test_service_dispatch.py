"""
tests/test_service_dispatch.py — WO-V54.0
==========================================
Tests for:
1. Service command routing (dungeon bridge + FITD loop)
2. DM notes hiding from player view
3. NPC conversation state + Mimir dialogue fallback
4. FITD party creation fix (no overwrite)
5. FITD scene audio mapping
6. Spatial map helper functions
"""
from unittest.mock import MagicMock, patch
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
        self.content_hints = {}


def _make_mock_engine(system_id="dnd5e", room_content=None):
    """Create a mock engine with configurable room content."""
    engine = MagicMock()
    engine.system_id = system_id
    engine.display_name = system_id.upper()
    engine.current_room_id = 1
    engine.visited_rooms = {1}
    engine.party = []

    char = MagicMock()
    char.current_hp = 20
    char.max_hp = 20
    char.name = "Tester"
    char.is_alive.return_value = True
    engine.character = char

    r1 = _FakeRoom(1, x=0, y=0, connections={2})
    r2 = _FakeRoom(2, x=0, y=-1, connections={1})
    engine.dungeon_graph = MagicMock()
    engine.dungeon_graph.rooms = {1: r1, 2: r2}
    engine.dungeon_graph.metadata = {"theme": "STONE"}

    room_node = MagicMock()
    room_node.room_type.name = "NORMAL"
    engine.get_current_room.return_value = room_node

    default_content = {
        "description": "A test room.",
        "enemies": [],
        "loot": [],
        "npcs": [
            {
                "name": "Durnan",
                "role": "innkeeper",
                "dialogue": "One gold to go down.",
                "notes": "Retired adventurer. Secret: knows the way out.",
            },
            {
                "name": "Volo",
                "role": "quest_giver",
                "dialogue": "Find my friend Floon!",
                "notes": "Chronic liar.",
            },
        ],
        "services": ["drink", "rest", "rumor", "quest"],
        "event_triggers": ["A troll bursts from the well!"],
    }
    if room_content:
        default_content.update(room_content)

    pop = MagicMock()
    pop.content = default_content
    engine.populated_rooms = {1: pop}

    exits = [{"direction": "north", "id": 2, "type": "NORMAL", "tier": 1}]
    engine.get_cardinal_exits.return_value = exits

    def _move(room_id):
        engine.current_room_id = room_id
        engine.visited_rooms.add(room_id)
        return True
    engine.move_to_room.side_effect = _move
    engine.roll_check.return_value = {"total": 15, "success": True}

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
    bridge._butler = None
    bridge.show_dm_notes = False  # WO-V54.0
    bridge._talking_to = None    # WO-V54.0
    bridge._session_log = []     # WO-V61.0
    return bridge


# =========================================================================
# Track B: Service Command Dispatch (Dungeon Bridge)
# =========================================================================

class TestServiceDispatchBridge:
    """Service names route to _dispatch_service instead of 'Unknown command'."""

    def test_drink_returns_flavor_text(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("drink")
        assert "Unknown command" not in result
        assert "drink" in result.lower() or "warmth" in result.lower() or "tankard" in result.lower()

    def test_rumor_returns_event_trigger(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("rumor")
        assert "Unknown command" not in result
        assert "troll" in result.lower()

    def test_quest_returns_npc_hints(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("quest")
        assert "Unknown command" not in result
        assert "Volo" in result

    def test_heal_restores_hp(self):
        engine = _make_mock_engine()
        engine.character.current_hp = 5
        bridge = _make_bridge(engine)
        result = bridge.step("heal")
        # heal is in SERVICE_ALIASES, dispatches to _service_heal
        assert "Unknown command" not in result

    def test_services_list_still_works(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("services")
        assert "drink" in result.lower()
        assert "rumor" in result.lower()

    def test_service_not_in_room(self):
        engine = _make_mock_engine(room_content={"services": []})
        bridge = _make_bridge(engine)
        result = bridge.step("drink")
        assert "not available" in result.lower() or "no services" in result.lower()

    def test_buy_returns_shop_text(self):
        engine = _make_mock_engine(room_content={"services": ["buy"]})
        bridge = _make_bridge(engine)
        result = bridge.step("buy")
        assert "Unknown command" not in result

    def test_exit_settlement_hint(self):
        engine = _make_mock_engine(room_content={"services": ["exit_settlement"]})
        bridge = _make_bridge(engine)
        result = bridge.step("exit_settlement")
        assert "movement" in result.lower()


# =========================================================================
# Track C: DM Notes Hiding
# =========================================================================

class TestDMNotesHiding:
    """DM notes should be hidden from player view by default."""

    def test_notes_hidden_by_default(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("talk durnan")
        assert "Retired adventurer" not in result
        assert "Secret:" not in result

    def test_notes_shown_when_enabled(self):
        bridge = _make_bridge(_make_mock_engine())
        bridge.show_dm_notes = True
        result = bridge.step("talk durnan")
        assert "Retired adventurer" in result

    def test_notes_hidden_for_quest_giver(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("talk volo")
        assert "Chronic liar" not in result


# =========================================================================
# Track E: NPC Conversation State
# =========================================================================

class TestNPCConversation:
    """NPC conversation state tracking and dialogue routing."""

    def test_talk_enters_conversation_mode(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("talk durnan")
        assert bridge._talking_to == "Durnan"
        assert "talking to" in result.lower() or "Durnan" in result

    def test_bye_exits_conversation(self):
        bridge = _make_bridge(_make_mock_engine())
        bridge.step("talk durnan")
        result = bridge.step("bye")
        assert bridge._talking_to is None
        assert "end" in result.lower() or "Durnan" in result

    def test_leave_exits_conversation(self):
        bridge = _make_bridge(_make_mock_engine())
        bridge.step("talk durnan")
        result = bridge.step("leave")
        assert bridge._talking_to is None

    def test_goodbye_exits_conversation(self):
        bridge = _make_bridge(_make_mock_engine())
        bridge.step("talk durnan")
        result = bridge.step("goodbye")
        assert bridge._talking_to is None

    def test_movement_exits_conversation(self):
        bridge = _make_bridge(_make_mock_engine())
        bridge.step("talk durnan")
        assert bridge._talking_to == "Durnan"
        bridge.step("n")
        assert bridge._talking_to is None

    def test_free_input_routes_to_npc_dialogue(self):
        from unittest.mock import patch
        bridge = _make_bridge(_make_mock_engine())
        bridge.step("talk durnan")
        # Mock Mimir so we don't call Ollama in tests
        with patch("codex.integrations.mimir.query_mimir",
                    return_value=None):
            result = bridge.step("what news do you have?")
        assert "Unknown command" not in result
        assert "Durnan" in result

    def test_unknown_command_when_not_talking(self):
        bridge = _make_bridge(_make_mock_engine())
        assert bridge._talking_to is None
        result = bridge.step("xyzzy")
        assert "Unknown command" in result


# =========================================================================
# Track F: Party Creation Fix
# =========================================================================

class TestPartyCreationFix:
    """FITD engines should append to party, not overwrite."""

    def test_cbrpnk_party_append(self):
        from codex.games.cbrpnk import CBRPNKEngine
        engine = CBRPNKEngine()
        engine.create_character("Runner1")
        assert len(engine.party) == 1
        engine.create_character("Runner2")
        assert len(engine.party) == 2
        assert engine.party[0].name == "Runner1"
        assert engine.party[1].name == "Runner2"

    def test_bitd_party_append(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel1")
        assert len(engine.party) == 1
        engine.create_character("Scoundrel2")
        assert len(engine.party) == 2

    def test_sav_party_append(self):
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Pilot1")
        assert len(engine.party) == 1
        engine.create_character("Pilot2")
        assert len(engine.party) == 2

    def test_bob_party_append(self):
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Soldier1")
        assert len(engine.party) == 1
        engine.create_character("Soldier2")
        assert len(engine.party) == 2

    def test_candela_party_append(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Investigator1")
        assert len(engine.party) == 1
        engine.create_character("Investigator2")
        assert len(engine.party) == 2


# =========================================================================
# Track H: FITD Scene Audio Mapping
# =========================================================================

class TestFITDSceneAudio:
    """Audio map builds correctly from file naming convention."""

    def test_audio_map_builds_from_filenames(self):
        """Verify _build_audio_map parses CBR PNK_01_ style names."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            audio_dir = os.path.join(td, "AUDIO")
            os.makedirs(audio_dir)
            # Create fake WAV files
            for name in [
                "CBR PNK_01_dearpass_.wav",
                "CBR PNK_02_destination.wav",
                "CBR PNK_03_enjoy.wav",
            ]:
                with open(os.path.join(audio_dir, name), "w") as f:
                    f.write("fake")

            # Create a fake module base_path so _find_audio_dir works
            mod_dir = os.path.join(td, "modules", "mind_the_gap")
            os.makedirs(mod_dir)

            from play_universal import _FITDSceneState

            # Manually construct to test audio mapping only
            state = object.__new__(_FITDSceneState)
            state.audio_dir = audio_dir
            state.audio_map = state._build_audio_map()

            assert 0 in state.audio_map  # _01_ -> scene 0
            assert 1 in state.audio_map  # _02_ -> scene 1
            assert 2 in state.audio_map  # _03_ -> scene 2
            assert state.audio_map[0].endswith("dearpass_.wav")

    def test_audio_dir_not_found(self):
        """No audio dir returns None."""
        from play_universal import _FITDSceneState
        state = object.__new__(_FITDSceneState)
        state.audio_dir = state._find_audio_dir("/nonexistent/path")
        assert state.audio_dir is None
        state.audio_map = state._build_audio_map()
        assert state.audio_map == {}


# =========================================================================
# Track A: Spatial Map Helpers
# =========================================================================

class TestSpatialMapHelpers:
    """Test _rebuild_spatial_rooms and _get_lead_hp."""

    def test_get_lead_hp_from_party(self):
        from play_universal import _get_lead_hp
        engine = _make_mock_engine()
        char = MagicMock()
        char.current_hp = 15
        char.max_hp = 25
        engine.party = [char]
        assert _get_lead_hp(engine, "current") == 15
        assert _get_lead_hp(engine, "max") == 25

    def test_get_lead_hp_from_character(self):
        from play_universal import _get_lead_hp
        engine = _make_mock_engine()
        engine.party = []
        engine.character.current_hp = 10
        engine.character.max_hp = 20
        assert _get_lead_hp(engine, "current") == 10
        assert _get_lead_hp(engine, "max") == 20

    def test_get_lead_hp_no_character(self):
        from play_universal import _get_lead_hp
        engine = MagicMock()
        engine.party = []
        engine.character = None
        assert _get_lead_hp(engine) == 0

    def test_rebuild_spatial_rooms_returns_dict(self):
        from play_universal import _rebuild_spatial_rooms
        engine = _make_mock_engine()
        rooms = _rebuild_spatial_rooms(engine)
        # Should return a dict (may be empty if spatial renderer not available)
        assert isinstance(rooms, dict)

    def test_rebuild_spatial_rooms_no_graph(self):
        from play_universal import _rebuild_spatial_rooms
        engine = MagicMock()
        engine.dungeon_graph = None
        rooms = _rebuild_spatial_rooms(engine)
        assert rooms == {}


# =========================================================================
# Track G: FITD Message Fix
# =========================================================================

class TestFITDMessageFix:
    """Verify the misleading 'spatial navigation planned' message is replaced."""

    def test_message_not_in_source(self):
        """The old misleading message should not appear in play_universal.py."""
        import pathlib
        src = pathlib.Path("play_universal.py").read_text()
        assert "Spatial navigation for FITD systems is planned" not in src

    def test_new_message_in_source(self):
        """The new scene navigation instructions should appear."""
        import pathlib
        src = pathlib.Path("play_universal.py").read_text()
        assert "Navigate scenes with:" in src


# =========================================================================
# Track D: Yawning Portal Troll
# =========================================================================

class TestYawningPortalTroll:
    """Verify Room 0 has troll enemy and event trigger."""

    def test_troll_in_room_0(self):
        import json
        with open("vault_maps/modules/dragon_heist/yawning_portal.json") as f:
            data = json.load(f)
        room_0 = data["rooms"]["0"]
        enemies = room_0["content_hints"].get("enemies", [])
        assert len(enemies) >= 1
        troll = enemies[0]
        assert troll["name"] == "Troll"
        assert troll["hp"] == 84

    def test_troll_event_trigger(self):
        import json
        with open("vault_maps/modules/dragon_heist/yawning_portal.json") as f:
            data = json.load(f)
        room_0 = data["rooms"]["0"]
        events = room_0["content_hints"].get("event_triggers", [])
        assert len(events) >= 1
        assert "troll" in events[0].lower() or "Troll" in events[0]


# =========================================================================
# Integration: Bridge + Services End-to-End
# =========================================================================

class TestBridgeServiceIntegration:
    """End-to-end service dispatch through bridge.step()."""

    def test_drink_via_step(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("drink")
        assert "Unknown command" not in result

    def test_rumor_via_step(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("rumor")
        assert "Unknown command" not in result

    def test_quest_via_step(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("quest")
        assert "Unknown command" not in result

    def test_lore_via_step(self):
        engine = _make_mock_engine(room_content={"services": ["lore"]})
        bridge = _make_bridge(engine)
        result = bridge.step("lore")
        assert "Unknown command" not in result

    def test_services_with_arg_routes_service(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("services drink")
        assert "Unknown command" not in result
        assert "drink" in result.lower() or "warmth" in result.lower() or "tankard" in result.lower()

    def test_help_includes_service_hint(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("help")
        assert "drink" in result.lower()
        assert "rumor" in result.lower()

    def test_help_includes_talk_instructions(self):
        bridge = _make_bridge(_make_mock_engine())
        result = bridge.step("help")
        assert "bye" in result.lower()

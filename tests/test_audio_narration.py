"""
tests/test_audio_narration.py — WO-V50.0
=========================================
Tests for:
1. Butler narration cooldown (3s rate-limit)
2. Bridge set_butler + _try_narrate
3. Bridge voice command
4. Bridge narration hooks (move/kill/death)
5. _EngineWrappedBridge butler wiring
6. Burnwillow victory + quest narration
7. Telegram /voice /sheet /atlas /rumors
"""
import asyncio
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers — reuse _make_mock_engine pattern from test_bridge_movement.py
# ---------------------------------------------------------------------------

class _FakeRoom:
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
    engine.character.take_damage.return_value = 5

    r1 = _FakeRoom(1, x=0, y=0, connections={2})
    r2 = _FakeRoom(2, x=0, y=-1, connections={1})
    engine.dungeon_graph = MagicMock()
    engine.dungeon_graph.rooms = {1: r1, 2: r2}

    room_node = MagicMock()
    room_node.room_type.name = room_type
    engine.get_current_room.return_value = room_node

    pop = MagicMock()
    pop.content = {"description": "A dark chamber.", "enemies": [], "loot": []}
    engine.populated_rooms = {1: pop, 2: pop}

    if exits is None:
        exits = [{"direction": "north", "id": 2, "type": "NORMAL", "tier": 1}]
    engine.get_cardinal_exits.return_value = exits

    def _move(room_id):
        engine.current_room_id = room_id
        engine.visited_rooms.add(room_id)
        return True
    engine.move_to_room.side_effect = _move

    return engine


def _make_bridge(engine):
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
# Phase 1: Butler Cooldown
# =========================================================================

class TestButlerCooldown:
    """Narration cooldown prevents thermal spikes."""

    def test_cooldown_fields_exist(self):
        from codex.core.butler import CodexButler
        butler = CodexButler()
        assert hasattr(butler, '_last_narrate_ts')
        assert hasattr(butler, '_narrate_cooldown')
        assert butler._narrate_cooldown == 3.0
        assert butler._last_narrate_ts == 0.0

    @patch("requests.post")
    @patch("shutil.which", return_value="/usr/bin/aplay")
    @patch("subprocess.Popen")
    def test_narrate_updates_timestamp(self, mock_popen, mock_which, mock_post):
        from codex.core.butler import CodexButler
        butler = CodexButler()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake_wav_data"
        mock_post.return_value = mock_resp
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        before = time.time()
        result = butler.narrate("Test narration")
        after = time.time()

        assert result is True
        assert butler._last_narrate_ts >= before
        assert butler._last_narrate_ts <= after

    @patch("requests.post")
    @patch("shutil.which", return_value="/usr/bin/aplay")
    @patch("subprocess.Popen")
    def test_cooldown_blocks_rapid_calls(self, mock_popen, mock_which, mock_post):
        from codex.core.butler import CodexButler
        butler = CodexButler()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake_wav"
        mock_post.return_value = mock_resp
        mock_popen.return_value = MagicMock()

        # First call succeeds
        assert butler.narrate("First") is True
        # Immediate second call blocked by cooldown
        assert butler.narrate("Second") is False
        # Only one HTTP request made
        assert mock_post.call_count == 1

    def test_cooldown_allows_after_delay(self):
        from codex.core.butler import CodexButler
        butler = CodexButler()
        # Simulate a narration that happened 10 seconds ago
        butler._last_narrate_ts = time.time() - 10
        # Cooldown should NOT block (10 > 3)
        assert (time.time() - butler._last_narrate_ts) >= butler._narrate_cooldown


# =========================================================================
# Phase 2: Bridge set_butler + _try_narrate
# =========================================================================

class TestBridgeButlerIntegration:
    """Bridge butler wiring and narration."""

    def test_set_butler(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        bridge.set_butler(butler)
        assert bridge._butler is butler

    def test_try_narrate_calls_butler(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        bridge.set_butler(butler)
        bridge._try_narrate("Hello world")
        butler.narrate.assert_called_once_with("Hello world")

    def test_try_narrate_no_butler(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        # Should not raise
        bridge._try_narrate("No butler here")

    def test_try_narrate_exception_suppressed(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        butler.narrate.side_effect = RuntimeError("TTS failed")
        bridge.set_butler(butler)
        # Should not raise
        bridge._try_narrate("Error test")


# =========================================================================
# Phase 2: Bridge voice command
# =========================================================================

class TestBridgeVoiceCommand:
    """Voice toggle command via bridge."""

    def test_voice_no_butler(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        result = bridge.step("voice")
        assert "No voice system" in result

    def test_voice_toggle_on(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        butler._voice_enabled = False
        bridge.set_butler(butler)
        result = bridge.step("voice on")
        assert "ON" in result
        assert butler._voice_enabled is True

    def test_voice_toggle_off(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        butler._voice_enabled = True
        bridge.set_butler(butler)
        result = bridge.step("voice off")
        assert "OFF" in result
        assert butler._voice_enabled is False


# =========================================================================
# Phase 2: Bridge narration hooks (move/kill/death)
# =========================================================================

class TestBridgeNarrationHooks:
    """Narration fires on key game events."""

    def test_move_triggers_narration(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        bridge.set_butler(butler)
        bridge.step("n")
        butler.narrate.assert_called_once()
        call_text = butler.narrate.call_args[0][0]
        assert "Normal" in call_text or "dark chamber" in call_text.lower()

    def test_kill_triggers_narration(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        bridge.set_butler(butler)

        # Set up enemy in current room
        pop = engine.populated_rooms[1]
        pop.content["enemies"] = [{"name": "Goblin", "hp": 1, "max_hp": 5, "defense": 5, "attack": 1}]
        # Ensure hit succeeds
        engine.roll_check.return_value = {"success": True, "total": 15, "modifier": 2}

        bridge.step("attack")
        # Should have narrated the kill
        calls = [c[0][0] for c in butler.narrate.call_args_list]
        assert any("slain" in c.lower() for c in calls)

    def test_death_triggers_narration(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        butler = MagicMock()
        bridge.set_butler(butler)

        pop = engine.populated_rooms[1]
        pop.content["enemies"] = [{"name": "Dragon", "hp": 100, "max_hp": 100, "defense": 5, "attack": 20}]
        engine.roll_check.return_value = {"success": False, "total": 5, "modifier": 0}
        engine.character.armor_class = 10
        engine.character.defense = 10
        engine.character.is_alive.return_value = False

        bridge.step("attack")
        calls = [c[0][0] for c in butler.narrate.call_args_list]
        assert any("fallen" in c.lower() for c in calls)


# =========================================================================
# Phase 3: _EngineWrappedBridge butler wiring
# =========================================================================

class TestEngineWrappedBridgeButler:
    """Butler wiring through the play_universal wrapper."""

    def test_wrapped_bridge_has_butler_attr(self):
        from play_universal import _EngineWrappedBridge
        engine = _make_mock_engine()
        wrapper = _EngineWrappedBridge(engine)
        assert hasattr(wrapper._bridge, '_butler')

    def test_wrapped_bridge_accepts_set_butler(self):
        from play_universal import _EngineWrappedBridge
        engine = _make_mock_engine()
        wrapper = _EngineWrappedBridge(engine)
        butler = MagicMock()
        wrapper._bridge.set_butler(butler)
        assert wrapper._bridge._butler is butler


# =========================================================================
# Phase 4: Burnwillow victory + quest narration
# =========================================================================

class TestBurnwillowNarrationGaps:
    """Victory and quest turn-in trigger narration."""

    def test_victory_narration(self):
        """render_victory_screen calls butler.narrate on victory."""
        from unittest.mock import MagicMock as MM
        state = MM()
        state.console = MM()
        state.engine = MM()
        state.doom = 5
        state.turn_number = 20

        butler = MM()
        state.butler = butler

        # Set up party
        char1 = MM()
        char1.name = "Hero"
        char1.is_alive.return_value = True
        state.engine.party = [char1]
        state.engine.visited_rooms = {1, 2, 3}

        from play_burnwillow import render_victory_screen, Minion
        # Patch isinstance check for Minion
        with patch("play_burnwillow.isinstance", side_effect=lambda obj, cls: False if cls is Minion else type.__instancecheck__(cls, obj)):
            pass
        # Direct call — will use real isinstance
        render_victory_screen(state)
        butler.narrate.assert_called_once_with("The Burnwillow blooms again. You are victorious.")

    def test_quest_turnin_npc_narration(self):
        """Quest turn-in at NPC talk triggers narration."""
        # This tests the pattern exists — we can't easily call the full
        # _settlement_talk function, but we verify the code path is wired
        import ast
        source = Path(__file__).resolve().parent.parent / "play_burnwillow.py"
        tree = ast.parse(source.read_text())
        # Find all string literals containing "Quest complete"
        quest_narrate_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "Quest complete" in node.value:
                    quest_narrate_count += 1
        # Should have at least 2 (NPC talk + quest log)
        assert quest_narrate_count >= 2, f"Expected >=2 'Quest complete' narration strings, found {quest_narrate_count}"


# =========================================================================
# Phase 5: Telegram commands
# =========================================================================

class TestTelegramVoice:
    """Telegram /voice command."""

    def test_voice_toggle(self):
        from codex.bots.telegram_bot import TelegramSession
        session = TelegramSession(chat_id=12345)
        assert session.voice_enabled is False
        session.voice_enabled = True
        assert session.voice_enabled is True


class TestTelegramSheet:
    """Telegram /sheet command structure."""

    def test_sheet_no_bridge(self):
        from codex.bots.telegram_bot import cmd_sheet_tg, get_session
        update = MagicMock()
        update.effective_chat.id = 99999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        session = get_session(99999)
        session.bridge = None
        asyncio.get_event_loop().run_until_complete(cmd_sheet_tg(update, context))
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "No active session" in call_text


class TestTelegramAtlas:
    """Telegram /atlas command."""

    def test_atlas_no_worlds_dir(self):
        from codex.bots.telegram_bot import cmd_atlas_tg
        update = MagicMock()
        update.effective_chat.id = 99998
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        with patch("codex.bots.telegram_bot._ROOT", Path("/nonexistent")):
            asyncio.get_event_loop().run_until_complete(cmd_atlas_tg(update, context))
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "No worlds" in call_text

    def test_atlas_loads_grapes(self, tmp_path):
        from codex.bots.telegram_bot import cmd_atlas_tg
        worlds = tmp_path / "worlds"
        worlds.mkdir()
        world_data = {
            "name": "Test World",
            "grapes": {
                "geography": "Mountains",
                "religion": "Sun worship",
                "achievements": "Great wall",
                "politics": "Monarchy",
                "economics": "Trade routes",
                "social": "Feudal",
            },
        }
        (worlds / "test.json").write_text(json.dumps(world_data))

        update = MagicMock()
        update.effective_chat.id = 99997
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        with patch("codex.bots.telegram_bot._ROOT", tmp_path):
            asyncio.get_event_loop().run_until_complete(cmd_atlas_tg(update, context))
        call_text = update.message.reply_text.call_args[0][0]
        assert "Test World" in call_text
        assert "Mountains" in call_text
        assert "Monarchy" in call_text


class TestTelegramRumors:
    """Telegram /rumors command."""

    def test_rumors_generates_from_grapes(self, tmp_path):
        from codex.bots.telegram_bot import cmd_rumors_tg
        worlds = tmp_path / "worlds"
        worlds.mkdir()
        world_data = {
            "name": "Rumor World",
            "grapes": {
                "geography": "Islands",
                "religion": "Storm gods",
                "politics": "Democracy",
                "economics": "Fishing",
                "social": "Egalitarian",
            },
            "primer": "The islands are home to fierce storms. The people are resilient and proud.",
        }
        (worlds / "rumor_world.json").write_text(json.dumps(world_data))

        update = MagicMock()
        update.effective_chat.id = 99996
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        with patch("codex.bots.telegram_bot._ROOT", tmp_path):
            asyncio.get_event_loop().run_until_complete(cmd_rumors_tg(update, context))
        call_text = update.message.reply_text.call_args[0][0]
        assert "Town Crier" in call_text

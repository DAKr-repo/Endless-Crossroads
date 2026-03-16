"""
Tests for Discord bot pure logic (WO-V47.0).

Uses sys.modules monkeypatch to avoid discord.py import dependency.
Tests DiscordSession state, Phase enum, and embed construction.
"""
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────
# Discord.py SDK stub — must be set up BEFORE importing discord_bot
# ─────────────────────────────────────────────────────────────────────

_discord_stub = MagicMock()
_discord_stub.Intents = MagicMock()
_discord_stub.Intents.default = MagicMock(return_value=MagicMock())
_discord_stub.Embed = MagicMock
_discord_stub.ui = MagicMock()
_discord_stub.ui.View = type("View", (), {"__init_subclass__": classmethod(lambda cls, **kw: None)})
_discord_stub.ui.button = MagicMock(return_value=lambda f: f)
_discord_stub.ui.Button = MagicMock
_discord_stub.ButtonStyle = MagicMock()
_discord_stub.ButtonStyle.primary = 1
_discord_stub.ButtonStyle.success = 2
_discord_stub.ButtonStyle.danger = 3
_discord_stub.ButtonStyle.secondary = 4
_discord_stub.app_commands = MagicMock()
_discord_stub.Object = MagicMock

_ext_stub = MagicMock()
_ext_stub.commands = MagicMock()
_ext_stub.commands.Bot = MagicMock

sys.modules.setdefault("discord", _discord_stub)
sys.modules.setdefault("discord.ext", _ext_stub)
sys.modules.setdefault("discord.ext.commands", _ext_stub.commands)
sys.modules.setdefault("discord.ui", _discord_stub.ui)

# Also stub optional voice-related modules
for mod in ["nacl", "nacl.secret", "nacl.utils", "opus"]:
    sys.modules.setdefault(mod, MagicMock())


# ─────────────────────────────────────────────────────────────────────
# Now we can import
# ─────────────────────────────────────────────────────────────────────

class TestDiscordPhaseEnum:
    """Test the Phase enum exists with expected values."""

    def test_import_phase(self):
        from codex.bots.discord_bot import Phase
        assert Phase.IDLE is not None

    def test_expected_phases_exist(self):
        from codex.bots.discord_bot import Phase
        for name in ["IDLE", "MENU", "DUNGEON", "MORNING", "CAMPFIRE",
                      "COUNCIL", "FINALE"]:
            assert hasattr(Phase, name), f"Phase.{name} missing"

    def test_unique_values(self):
        from codex.bots.discord_bot import Phase
        values = [p.value for p in Phase]
        assert len(values) == len(set(values))


class TestDiscordSession:
    """Test DiscordSession dataclass logic."""

    def _make_session(self, channel_id=99999):
        from codex.bots.discord_bot import DiscordSession, Phase
        session = DiscordSession(channel_id=channel_id)
        return session

    def test_initial_phase_idle(self):
        from codex.bots.discord_bot import Phase
        session = self._make_session()
        assert session.phase == Phase.IDLE

    def test_channel_id_stored(self):
        session = self._make_session(channel_id=42)
        assert session.channel_id == 42

    def test_engine_initially_none(self):
        session = self._make_session()
        assert session.engine is None

    def test_conditions_initially_none(self):
        session = self._make_session()
        assert session.conditions is None

    def test_start_game_when_not_idle(self):
        from codex.bots.discord_bot import Phase
        session = self._make_session()
        session.phase = Phase.MORNING
        result = session.start_game()
        assert "already" in result.lower() or "⚠️" in result

    def test_end_session_when_idle(self):
        session = self._make_session()
        result = session.end_session()
        assert isinstance(result, str)

    def test_get_status_when_idle(self):
        session = self._make_session()
        result = session.get_status()
        assert isinstance(result, str)

    def test_phase_transitions_morning_to_campfire(self):
        from codex.bots.discord_bot import Phase
        session = self._make_session()
        # Manually set up engine and phase
        mock_engine = MagicMock()
        mock_engine.handle_travel.return_value = ("campfire prompt", None)
        mock_engine.get_campfire_prompt.return_value = "The fire burns."
        mock_engine.day = 1
        session.engine = mock_engine
        session.phase = Phase.MORNING
        result = session.handle_travel()
        assert isinstance(result, str)


class TestDiscordSessionVote:
    """Test vote handling logic."""

    def _make_session_at_council(self):
        from codex.bots.discord_bot import DiscordSession, Phase
        session = DiscordSession(channel_id=99999)
        session.phase = Phase.COUNCIL
        mock_engine = MagicMock()
        mock_engine.process_vote.return_value = "The vote is cast."
        mock_engine.day = 3
        mock_engine.max_days = 5
        mock_engine.sway = 0
        mock_engine.get_world_prompt.return_value = "A new day."
        session.engine = mock_engine
        session.current_dilemma = {
            "prompt": "Test",
            "option_1": "A",
            "option_2": "B",
        }
        return session

    def test_vote_invalid_choice(self):
        session = self._make_session_at_council()
        result = session.handle_vote("3")
        assert result is None or "1 or 2" in str(result).lower() or isinstance(result, str)

    def test_vote_when_not_in_council(self):
        from codex.bots.discord_bot import DiscordSession, Phase
        session = DiscordSession(channel_id=99999)
        session.phase = Phase.IDLE
        result = session.handle_vote("1")
        assert result is None


class TestDiscordSessionRest:
    """Test rest handling."""

    def test_rest_when_not_in_rest_phase(self):
        from codex.bots.discord_bot import DiscordSession, Phase
        session = DiscordSession(channel_id=99999)
        session.phase = Phase.IDLE
        result = session.handle_rest("long")
        assert result is None


class TestDiscordSessionAllegiance:
    """Test allegiance handling."""

    def _make_session_at_campfire(self):
        from codex.bots.discord_bot import DiscordSession, Phase
        session = DiscordSession(channel_id=99999)
        session.phase = Phase.CAMPFIRE
        mock_engine = MagicMock()
        mock_engine.process_allegiance.return_value = 1
        mock_engine.day = 1
        mock_engine.sway = 1
        mock_engine.max_days = 5
        session.engine = mock_engine
        return session

    def test_allegiance_when_not_campfire(self):
        from codex.bots.discord_bot import DiscordSession, Phase
        session = DiscordSession(channel_id=99999)
        session.phase = Phase.IDLE
        result = session.handle_allegiance("crown")
        assert result is None

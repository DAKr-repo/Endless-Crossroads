#!/usr/bin/env python3
"""
WO-V37.0 — The Chronicle Recap: Session Summarization Tests
=============================================================

~25 tests across 7 classes covering:
  - Session log field + log_event helper
  - format_session_stats grouping logic
  - summarize_session output (stats-only, Mimir, timeout fallback)
  - action_recap terminal command
  - BurnwillowBridge get_session_stats / recap
  - Bot recap formatting
  - Event capture wiring in _perform_attack, action_loot, etc.
"""

import sys
import json
import copy
import random
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codex.games.burnwillow.engine import (
    BurnwillowEngine, Character, GearGrid, GearItem, GearSlot, GearTier,
    StatType, create_starter_gear,
)
from codex.games.burnwillow.bridge import BurnwillowBridge
from codex.core.services.narrative_loom import (
    format_session_stats, summarize_session,
)
from codex.core.services.broadcast import GlobalBroadcastManager


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_log():
    """A representative session log with diverse events."""
    return [
        {"type": "room_entered", "turn": 1, "room_id": 0},
        {"type": "room_entered", "turn": 2, "room_id": 1},
        {"type": "kill", "turn": 2, "target": "Ash Hound", "tier": 1, "room_id": 1},
        {"type": "kill", "turn": 2, "target": "Rot Fiend", "tier": 2, "room_id": 1},
        {"type": "room_cleared", "turn": 2, "room_id": 1, "room_type": "corridor"},
        {"type": "loot", "turn": 3, "item_name": "Rusted Blade", "tier": 1, "room_id": 1},
        {"type": "room_entered", "turn": 4, "room_id": 2},
        {"type": "kill", "turn": 4, "target": "Blightborn", "tier": 3, "room_id": 2},
        {"type": "aoe_used", "turn": 4, "trait": "[Shockwave]", "by": "Hero", "targets_hit": 2},
        {"type": "room_cleared", "turn": 4, "room_id": 2, "room_type": "hall"},
        {"type": "loot", "turn": 5, "item_name": "Shockwave Maul", "tier": 2, "room_id": 2},
        {"type": "companion_summoned", "turn": 6, "name": "Ashara"},
        {"type": "party_death", "turn": 7, "name": "Ashara"},
    ]


@pytest.fixture
def sample_snapshot():
    """Engine state snapshot for recap."""
    return {
        "party": [
            {"name": "Hero", "hp": 15, "max_hp": 20},
            {"name": "Ashara", "hp": 0, "max_hp": 12},
        ],
        "doom": 8,
        "turns": 7,
        "chapter": 1,
        "completed_quests": ["Find the Lost Blade"],
    }


@pytest.fixture
def game_state():
    """Minimal GameState for testing (patched to avoid Rich console)."""
    # Import GameState from play_burnwillow
    from play_burnwillow import GameState
    state = GameState()
    # Don't need a full engine for most tests
    state.engine = BurnwillowEngine()
    state.engine.create_party(["TestHero"])
    state.engine.generate_dungeon(depth=2, seed=42)
    return state


@pytest.fixture
def bridge():
    """Create a BurnwillowBridge for testing."""
    return BurnwillowBridge("TestHero", seed=42)


# =============================================================================
# CLASS 1: TestSessionLog (4 tests)
# =============================================================================

class TestSessionLog:
    """Test session_log field and log_event helper on GameState."""

    def test_session_log_initialized_empty(self, game_state):
        """session_log starts as an empty list."""
        assert game_state.session_log == []
        assert isinstance(game_state.session_log, list)

    def test_log_event_appends(self, game_state):
        """log_event appends structured dict with type and turn."""
        game_state.log_event("kill", target="Goblin", tier=1)
        assert len(game_state.session_log) == 1
        event = game_state.session_log[0]
        assert event["type"] == "kill"
        assert event["target"] == "Goblin"
        assert event["tier"] == 1
        assert "turn" in event

    def test_log_event_tracks_turn(self, game_state):
        """log_event includes current turn_number."""
        game_state.turn_number = 5
        game_state.log_event("loot", item_name="Sword")
        assert game_state.session_log[0]["turn"] == 5

    def test_save_load_persistence(self, game_state, tmp_path):
        """session_log persists through save/load cycle."""
        game_state.log_event("kill", target="TestEnemy", tier=1)
        game_state.log_event("loot", item_name="TestItem", tier=2, room_id=0)

        # Simulate save
        save_data = game_state.engine.save_game()
        save_data["session_log"] = game_state.session_log
        save_data["turn_number"] = game_state.turn_number
        save_data["cleared_rooms"] = []
        save_data["searched_rooms"] = []
        save_data["scouted_rooms"] = []

        save_file = tmp_path / "test_save.json"
        save_file.write_text(json.dumps(save_data, default=str))

        # Simulate load
        loaded = json.loads(save_file.read_text())
        restored_log = loaded.get("session_log", [])
        assert len(restored_log) == 2
        assert restored_log[0]["type"] == "kill"
        assert restored_log[1]["type"] == "loot"


# =============================================================================
# CLASS 2: TestFormatSessionStats (4 tests)
# =============================================================================

class TestFormatSessionStats:
    """Test format_session_stats grouping and counting logic."""

    def test_kill_grouping_by_tier(self, sample_log, sample_snapshot):
        """Kills are correctly grouped by tier."""
        stats = format_session_stats(sample_log, sample_snapshot)
        assert stats["kills"]["total"] == 3
        assert stats["kills"]["by_tier"][1] == 1  # Ash Hound
        assert stats["kills"]["by_tier"][2] == 1  # Rot Fiend
        assert stats["kills"]["by_tier"][3] == 1  # Blightborn

    def test_loot_list(self, sample_log, sample_snapshot):
        """Loot items are collected by name."""
        stats = format_session_stats(sample_log, sample_snapshot)
        assert "Rusted Blade" in stats["loot"]
        assert "Shockwave Maul" in stats["loot"]
        assert len(stats["loot"]) == 2

    def test_rooms_counted(self, sample_log, sample_snapshot):
        """Rooms explored and cleared are counted correctly."""
        stats = format_session_stats(sample_log, sample_snapshot)
        assert stats["rooms_explored"] == 3  # 3 room_entered events
        assert stats["rooms_cleared"] == 2   # 2 room_cleared events

    def test_empty_log_graceful(self, sample_snapshot):
        """Empty session log returns zeroed stats."""
        stats = format_session_stats([], sample_snapshot)
        assert stats["kills"]["total"] == 0
        assert stats["loot"] == []
        assert stats["rooms_explored"] == 0
        assert stats["rooms_cleared"] == 0
        assert stats["party"] == sample_snapshot["party"]

    def test_quests_from_snapshot(self, sample_log, sample_snapshot):
        """Completed quests from engine snapshot are included."""
        stats = format_session_stats(sample_log, sample_snapshot)
        assert "Find the Lost Blade" in stats["quests_completed"]

    def test_companion_and_death_tracking(self, sample_log, sample_snapshot):
        """Companions summoned and party deaths are tracked."""
        stats = format_session_stats(sample_log, sample_snapshot)
        assert "Ashara" in stats["companions_summoned"]
        assert "Ashara" in stats["deaths"]


# =============================================================================
# CLASS 3: TestSummarizeSession (3 tests)
# =============================================================================

class TestSummarizeSession:
    """Test summarize_session text output."""

    def test_stats_only_output(self, sample_log, sample_snapshot):
        """Without Mimir, returns stats block only."""
        result = summarize_session(sample_log, sample_snapshot)
        assert "=== SESSION RECAP ===" in result
        assert "Enemies slain:  3" in result
        assert "Rusted Blade" in result
        assert "Doom Clock: 8/20" in result
        assert "Hero: 15/20 HP" in result

    def test_mimir_narrative_included(self, sample_log, sample_snapshot):
        """When Mimir succeeds, narrative paragraph is appended."""
        def fake_mimir(prompt, ctx):
            return "The heroes fought bravely through the dark corridors of Burnwillow."

        result = summarize_session(sample_log, sample_snapshot, mimir_fn=fake_mimir)
        assert "Mimir's Chronicle" in result
        assert "heroes fought bravely" in result

    def test_mimir_timeout_fallback(self, sample_log, sample_snapshot):
        """When Mimir times out, falls back to stats only."""
        def slow_mimir(prompt, ctx):
            import time
            time.sleep(15)  # Exceeds 10s timeout
            return "This should not appear."

        result = summarize_session(sample_log, sample_snapshot, mimir_fn=slow_mimir)
        assert "=== SESSION RECAP ===" in result
        assert "Mimir's Chronicle" not in result


# =============================================================================
# CLASS 4: TestActionRecap (3 tests)
# =============================================================================

class TestActionRecap:
    """Test action_recap terminal command."""

    def test_returns_formatted_text(self, game_state):
        """action_recap returns a list with formatted recap string."""
        from play_burnwillow import action_recap
        game_state.log_event("kill", target="TestEnemy", tier=1, room_id=0)
        result = action_recap(game_state)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "SESSION RECAP" in result[0]
        assert "Enemies slain:  1" in result[0]

    def test_works_with_empty_log(self, game_state):
        """action_recap handles empty session log gracefully."""
        from play_burnwillow import action_recap
        result = action_recap(game_state)
        assert isinstance(result, list)
        assert "SESSION RECAP" in result[0]
        assert "Enemies slain:  0" in result[0]

    def test_party_status_shown(self, game_state):
        """action_recap shows party HP status."""
        from play_burnwillow import action_recap
        result = action_recap(game_state)
        assert "TestHero" in result[0]


# =============================================================================
# CLASS 5: TestBridgeStats (3 tests)
# =============================================================================

class TestBridgeStats:
    """Test BurnwillowBridge.get_session_stats and recap."""

    def test_get_session_stats_returns_dict(self, bridge):
        """get_session_stats returns a well-formed dict."""
        stats = bridge.get_session_stats()
        assert isinstance(stats, dict)
        assert "kills" in stats
        assert "loot" in stats
        assert "party" in stats
        assert stats["kills"]["total"] == 0  # No combat yet

    def test_empty_session(self, bridge):
        """Empty session has zero counts."""
        stats = bridge.get_session_stats()
        assert stats["rooms_explored"] == 0
        assert stats["rooms_cleared"] == 0
        assert stats["loot"] == []

    def test_combat_events_tracked(self, bridge):
        """Kill events logged via bridge attack are tracked."""
        # Manually log an event to simulate combat
        bridge._log_event("kill", target="TestEnemy", tier=1,
                          room_id=bridge.engine.current_room_id)
        bridge._log_event("loot", item_name="TestItem", tier=1,
                          room_id=bridge.engine.current_room_id)
        stats = bridge.get_session_stats()
        assert stats["kills"]["total"] == 1
        assert "TestItem" in stats["loot"]

    def test_recap_command(self, bridge):
        """Bridge step('recap') returns recap text."""
        result = bridge.step("recap")
        assert "SESSION RECAP" in result


# =============================================================================
# CLASS 6: TestBotRecap (4 tests)
# =============================================================================

class TestBotRecap:
    """Test bot recap formatting and broadcast event."""

    def test_discord_embed_format(self, bridge):
        """get_session_stats returns data suitable for Discord embed."""
        bridge._log_event("kill", target="Goblin", tier=1, room_id=0)
        stats = bridge.get_session_stats()
        # Verify structure is embed-compatible
        assert "kills" in stats
        assert "by_tier" in stats["kills"]
        assert "party" in stats
        assert all("name" in m and "hp" in m for m in stats["party"])

    def test_telegram_text_format(self, bridge):
        """Recap stats can be formatted as plain text for Telegram."""
        bridge._log_event("kill", target="Goblin", tier=1, room_id=0)
        stats = bridge.get_session_stats()
        # Build telegram-style text
        lines = [
            f"Enemies slain: {stats['kills']['total']}",
            f"Rooms explored: {stats['rooms_explored']}",
        ]
        text = "\n".join(lines)
        assert "Enemies slain: 1" in text

    def test_event_session_recap_fired(self):
        """EVENT_SESSION_RECAP can be broadcast."""
        bm = GlobalBroadcastManager(system_theme="burnwillow")
        received = []
        bm.subscribe("SESSION_RECAP", lambda p: received.append(p))

        bm.broadcast("SESSION_RECAP", {
            "system_id": "burnwillow",
            "stats": {"kills": {"total": 5}},
            "narrative": "A brave session.",
        })
        assert len(received) == 1
        assert received[0]["stats"]["kills"]["total"] == 5
        assert received[0]["narrative"] == "A brave session."

    def test_subscription_receives_payload(self):
        """Subscribed listener receives full recap payload."""
        bm = GlobalBroadcastManager()
        payloads = []
        bm.subscribe(GlobalBroadcastManager.EVENT_SESSION_RECAP,
                      lambda p: payloads.append(p))

        recap_data = {
            "system_id": "burnwillow",
            "stats": {"kills": {"total": 3}, "loot": ["Sword"]},
            "narrative": "The darkness receded.",
        }
        bm.broadcast(GlobalBroadcastManager.EVENT_SESSION_RECAP, recap_data)
        assert len(payloads) == 1
        assert payloads[0]["stats"]["loot"] == ["Sword"]


# =============================================================================
# CLASS 7: TestEventCapture (4 tests)
# =============================================================================

class TestEventCapture:
    """Test that game actions properly log events to session_log."""

    def test_kill_events_logged_in_perform_attack(self, game_state):
        """_perform_attack logs kill events when enemy dies."""
        from play_burnwillow import _perform_attack
        room_id = game_state.current_room_id
        game_state.room_enemies[room_id] = [
            {"name": "Weak Goblin", "hp": 1, "defense": 1, "tier": 1, "dr": 0},
        ]
        # Force a guaranteed hit by giving the character high might
        char = game_state.engine.party[0]
        char.might = 20

        _perform_attack(game_state, char, 0)

        kill_events = [e for e in game_state.session_log if e["type"] == "kill"]
        assert len(kill_events) >= 1
        assert kill_events[0]["target"] == "Weak Goblin"

    def test_loot_events_logged(self, game_state):
        """action_loot logs loot pickup events."""
        from play_burnwillow import action_loot
        room_id = game_state.current_room_id
        game_state.room_loot[room_id] = [
            {"name": "Test Sword", "slot": "R.Hand", "tier": 1},
        ]
        game_state.room_enemies[room_id] = []  # No enemies (can loot)

        action_loot(game_state)

        loot_events = [e for e in game_state.session_log if e["type"] == "loot"]
        assert len(loot_events) == 1
        assert loot_events[0]["item_name"] == "Test Sword"

    def test_room_entered_logged(self, game_state):
        """action_move logs room_entered events."""
        from play_burnwillow import action_move
        # Get connected rooms to find a valid target
        connected = game_state.engine.get_connected_rooms()
        if connected:
            target_id = connected[0]["id"]
            # Populate room content to prevent KeyErrors
            game_state.room_enemies.setdefault(target_id, [])
            game_state.room_loot.setdefault(target_id, [])
            game_state.room_furniture.setdefault(target_id, [])

            action_move(game_state, target_id)

            entered_events = [e for e in game_state.session_log if e["type"] == "room_entered"]
            assert len(entered_events) >= 1
            assert entered_events[0]["room_id"] == target_id

    def test_companion_summoned_logged(self, game_state):
        """action_companion logs companion_summoned events (at hub)."""
        from play_burnwillow import action_companion
        game_state.in_settlement = True  # Must be at hub

        action_companion(game_state)

        companion_events = [e for e in game_state.session_log
                           if e["type"] == "companion_summoned"]
        assert len(companion_events) == 1
        assert "name" in companion_events[0]

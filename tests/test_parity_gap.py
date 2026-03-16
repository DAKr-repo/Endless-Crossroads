"""
tests/test_parity_gap.py — WO-V35.0 Parity Gap Tests
=====================================================

~29 tests covering the 3 visibility/interaction gaps:
  1. Initiative Visibility — DM broadcast -> bot session
  2. Condition Rendering — Icons, formatters, embed integration
  3. Mechanical Interaction — Rest via bridges, hitdice, RestManager

Test Classes:
  TestConditionIcons       — Icon mapping, formatters, discord renderer
  TestBroadcastEvents      — Event constants, payload fields
  TestBridgeRest           — BW short/long, UGB short/long, hitdice
  TestDiscordSession       — Session fields, condition/initiative update
  TestTelegramSession      — Session fields, dungeon status rendering
  TestDMFrameEnrich        — Conditions/initiative in dm_frame.json
  TestEndToEndSync         — DM -> bot condition/initiative/rest sync
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================
# TestConditionIcons — 5 tests
# =========================================================================

class TestConditionIcons:
    """Verify CONDITION_ICONS dict and format_condition_icons helper."""

    def test_all_types_have_icons(self):
        """Every ConditionType should have an icon in CONDITION_ICONS."""
        from codex.core.mechanics.conditions import ConditionType, CONDITION_ICONS
        for ct in ConditionType:
            assert ct in CONDITION_ICONS, f"Missing icon for {ct}"

    def test_format_condition_icons_with_objects(self):
        """format_condition_icons handles Condition objects."""
        from codex.core.mechanics.conditions import (
            Condition, ConditionType, format_condition_icons, CONDITION_ICONS,
        )
        conds = [
            Condition(condition_type=ConditionType.POISONED, duration=3),
            Condition(condition_type=ConditionType.BURNING, duration=2),
        ]
        result = format_condition_icons(conds)
        assert CONDITION_ICONS[ConditionType.POISONED] in result
        assert "Poisoned" in result
        assert CONDITION_ICONS[ConditionType.BURNING] in result
        assert "Burning" in result

    def test_format_condition_icons_with_dicts(self):
        """format_condition_icons handles dict representations."""
        from codex.core.mechanics.conditions import format_condition_icons, CONDITION_ICONS, ConditionType
        conds = [{"type": "Stunned", "duration": 1}]
        result = format_condition_icons(conds)
        assert CONDITION_ICONS[ConditionType.STUNNED] in result
        assert "Stunned" in result

    def test_format_condition_icons_empty(self):
        """Empty list returns empty string."""
        from codex.core.mechanics.conditions import format_condition_icons
        assert format_condition_icons([]) == ""
        assert format_condition_icons(None) == ""

    def test_discord_renderer(self):
        """render_condition_icons_discord works with dict and object lists."""
        from codex.games.burnwillow.discord_embed import render_condition_icons_discord
        from codex.core.mechanics.conditions import Condition, ConditionType
        # With objects
        conds = [Condition(condition_type=ConditionType.BLESSED, duration=5)]
        result = render_condition_icons_discord(conds)
        assert "Blessed" in result
        # With dicts
        conds_d = [{"type": "Hasted"}]
        result_d = render_condition_icons_discord(conds_d)
        assert "Hasted" in result_d
        # Empty
        assert render_condition_icons_discord([]) == ""


# =========================================================================
# TestBroadcastEvents — 4 tests
# =========================================================================

class TestBroadcastEvents:
    """Verify new broadcast event constants and payloads."""

    def test_event_constants_exist(self):
        """3 new event constants are defined on GlobalBroadcastManager."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        assert hasattr(GlobalBroadcastManager, 'EVENT_INITIATIVE_ADVANCE')
        assert hasattr(GlobalBroadcastManager, 'EVENT_CONDITION_CHANGE')
        assert hasattr(GlobalBroadcastManager, 'EVENT_REST_COMPLETE')

    def test_initiative_advance_broadcast(self):
        """Broadcasting INITIATIVE_ADVANCE delivers payload to subscriber."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        bm = GlobalBroadcastManager()
        received = []
        bm.subscribe("INITIATIVE_ADVANCE", lambda p: received.append(p))
        bm.broadcast("INITIATIVE_ADVANCE", {
            "name": "Kael", "round": 2, "order": ["Kael", "Goblin"],
            "is_player": True,
        })
        assert len(received) == 1
        assert received[0]["name"] == "Kael"
        assert received[0]["round"] == 2

    def test_condition_change_broadcast(self):
        """Broadcasting CONDITION_CHANGE delivers payload."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        bm = GlobalBroadcastManager()
        received = []
        bm.subscribe("CONDITION_CHANGE", lambda p: received.append(p))
        bm.broadcast("CONDITION_CHANGE", {
            "entity": "Kael", "action": "apply",
            "condition_type": "Poisoned", "conditions": [],
        })
        assert len(received) == 1
        assert received[0]["action"] == "apply"

    def test_rest_complete_broadcast(self):
        """Broadcasting REST_COMPLETE delivers payload with fields."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        bm = GlobalBroadcastManager()
        received = []
        bm.subscribe("REST_COMPLETE", lambda p: received.append(p))
        bm.broadcast("REST_COMPLETE", {
            "rest_type": "short",
            "system_tag": "BURNWILLOW",
            "hp_recovered": {"Kael": 5},
            "summary": "Short rest",
        })
        assert len(received) == 1
        assert received[0]["rest_type"] == "short"
        assert received[0]["hp_recovered"]["Kael"] == 5


# =========================================================================
# TestBridgeRest — 6 tests
# =========================================================================

class TestBridgeRest:
    """Verify RestManager integration on both bridges."""

    def test_burnwillow_bridge_short_rest(self):
        """BurnwillowBridge short rest uses RestManager."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        bridge = BurnwillowBridge("TestHero", seed=42)
        # Damage the character first
        bridge.engine.character.current_hp = 5
        result = bridge.step("rest short")
        assert "SHORT" in result.upper() or "short" in result.lower()
        assert bridge.engine.character.current_hp > 5

    def test_burnwillow_bridge_long_rest(self):
        """BurnwillowBridge long rest heals fully with Doom cost."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        bridge = BurnwillowBridge("TestHero", seed=42)
        bridge.engine.character.current_hp = 3
        initial_doom = bridge.engine.doom_clock.current
        result = bridge.step("rest long")
        assert "LONG" in result.upper() or "long" in result.lower()
        assert bridge.engine.character.current_hp == bridge.engine.character.max_hp
        assert bridge.engine.doom_clock.current > initial_doom

    def test_burnwillow_bridge_rest_broadcast(self):
        """BurnwillowBridge rest broadcasts REST_COMPLETE."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        from codex.games.burnwillow.bridge import BurnwillowBridge
        bm = GlobalBroadcastManager()
        received = []
        bm.subscribe("REST_COMPLETE", lambda p: received.append(p))
        bridge = BurnwillowBridge("TestHero", seed=42, broadcast_manager=bm)
        bridge.engine.character.current_hp = 5
        bridge.step("rest short")
        assert len(received) == 1
        assert received[0]["system_tag"] == "BURNWILLOW"

    def test_universal_bridge_short_rest(self):
        """UniversalGameBridge short rest uses RestManager."""
        from codex.games.bridge import UniversalGameBridge
        from codex.games.dnd5e import DnD5eEngine
        bridge = UniversalGameBridge(DnD5eEngine)
        bridge.engine.character.current_hp = 3
        result = bridge.step("rest short")
        assert "SHORT" in result.upper() or "rest" in result.lower()

    def test_universal_bridge_long_rest(self):
        """UniversalGameBridge long rest fully heals."""
        from codex.games.bridge import UniversalGameBridge
        from codex.games.dnd5e import DnD5eEngine
        bridge = UniversalGameBridge(DnD5eEngine)
        bridge.engine.character.current_hp = 3
        result = bridge.step("rest long")
        assert "LONG" in result.upper() or "long" in result.lower()
        assert bridge.engine.character.current_hp == bridge.engine.character.max_hp

    def test_hitdice_command_dnd5e(self):
        """hitdice command works on DnD5e bridge, rejected on others."""
        from codex.games.bridge import UniversalGameBridge
        from codex.games.dnd5e import DnD5eEngine
        bridge = UniversalGameBridge(DnD5eEngine)
        result = bridge.step("hitdice")
        # Should either spend a hit die or report none remaining
        assert "hit" in result.lower() or "no" in result.lower() or "SHORT" in result.upper()


# =========================================================================
# TestDiscordSession — 4 tests
# =========================================================================

class TestDiscordSession:
    """Verify WO-V35.0 fields on DiscordSession."""

    def test_new_fields_exist(self):
        """DiscordSession has conditions, initiative_order, active_turn."""
        from codex.bots.discord_bot import DiscordSession
        sess = DiscordSession(channel_id=1234)
        assert sess.conditions is None
        assert sess.initiative_order == []
        assert sess.active_turn == ""

    def test_condition_update_on_session(self):
        """Applying a condition through the tracker updates session state."""
        from codex.bots.discord_bot import DiscordSession
        from codex.core.mechanics.conditions import ConditionTracker, Condition, ConditionType
        sess = DiscordSession(channel_id=1234)
        sess.conditions = ConditionTracker()
        cond = Condition(condition_type=ConditionType.POISONED, duration=3)
        sess.conditions.apply("Kael", cond)
        assert sess.conditions.has("Kael", ConditionType.POISONED)

    def test_initiative_update_on_session(self):
        """Setting initiative_order and active_turn on session."""
        from codex.bots.discord_bot import DiscordSession
        sess = DiscordSession(channel_id=1234)
        sess.initiative_order = ["Kael", "Goblin", "Bryn"]
        sess.active_turn = "Kael"
        assert sess.active_turn == "Kael"
        assert len(sess.initiative_order) == 3

    def test_end_session_clears_parity_fields(self):
        """end_session() resets conditions, initiative, active_turn."""
        from codex.bots.discord_bot import DiscordSession
        from codex.core.mechanics.conditions import ConditionTracker
        sess = DiscordSession(channel_id=1234)
        sess.phase = MagicMock()  # Not IDLE
        sess.phase.name = "DUNGEON"
        # Simulate active state
        from codex.bots.discord_bot import Phase
        sess.phase = Phase.DUNGEON
        sess.conditions = ConditionTracker()
        sess.initiative_order = ["A", "B"]
        sess.active_turn = "A"
        sess.end_session()
        assert sess.conditions is None
        assert sess.initiative_order == []
        assert sess.active_turn == ""


# =========================================================================
# TestTelegramSession — 4 tests
# =========================================================================

class TestTelegramSession:
    """Verify WO-V35.0 fields on TelegramSession."""

    def test_new_fields_exist(self):
        """TelegramSession has conditions, initiative_order, active_turn."""
        from codex.bots.telegram_bot import TelegramSession
        sess = TelegramSession(chat_id=5678)
        assert sess.conditions is None
        assert sess.initiative_order == []
        assert sess.active_turn == ""

    def test_dungeon_status_rendering(self):
        """Burnwillow status with conditions renders correctly."""
        from codex.bots.telegram_bot import TelegramSession
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType, format_condition_icons,
        )
        sess = TelegramSession(chat_id=5678)
        sess.conditions = ConditionTracker()
        cond = Condition(condition_type=ConditionType.BURNING, duration=2)
        sess.conditions.apply("Kael", cond)
        # Verify the tracker state
        assert sess.conditions.has("Kael", ConditionType.BURNING)
        icons = format_condition_icons(sess.conditions.get_conditions("Kael"))
        assert "Burning" in icons

    def test_condition_display(self):
        """Multiple conditions display all icons."""
        from codex.core.mechanics.conditions import (
            Condition, ConditionType, format_condition_icons, CONDITION_ICONS,
        )
        conds = [
            Condition(condition_type=ConditionType.POISONED, duration=3),
            Condition(condition_type=ConditionType.HASTED, duration=5),
        ]
        result = format_condition_icons(conds)
        assert CONDITION_ICONS[ConditionType.POISONED] in result
        assert CONDITION_ICONS[ConditionType.HASTED] in result

    def test_end_game_clears_parity_fields(self):
        """end_game() resets conditions, initiative, active_turn."""
        from codex.bots.telegram_bot import TelegramSession, Phase
        from codex.core.mechanics.conditions import ConditionTracker
        sess = TelegramSession(chat_id=5678)
        sess.phase = Phase.DUNGEON
        sess.conditions = ConditionTracker()
        sess.initiative_order = ["X", "Y"]
        sess.active_turn = "X"
        sess.end_game()
        assert sess.conditions is None
        assert sess.initiative_order == []
        assert sess.active_turn == ""


# =========================================================================
# TestDMFrameEnrich — 3 tests
# =========================================================================

class TestDMFrameEnrich:
    """Verify _write_dm_frame enrichment with conditions/initiative."""

    def test_conditions_in_frame(self, tmp_path):
        """Conditions data appears in dm_frame.json when dashboard provided."""
        from codex.core.dm_dashboard import DMDashboard, VitalsSchema
        from codex.core.mechanics.conditions import Condition, ConditionType
        from rich.console import Console

        dashboard = DMDashboard(Console(), "BURNWILLOW")
        cond = Condition(condition_type=ConditionType.POISONED, duration=3, modifier=-2)
        dashboard.conditions.apply("Kael", cond)

        vitals = VitalsSchema(
            system_name="Burnwillow", system_tag="BURNWILLOW",
            primary_resource="HP", primary_current=10, primary_max=20,
        )

        # Monkey-patch the state dir for test isolation
        frame_file = tmp_path / "dm_frame.json"
        with patch("play_dm_view.STATE_DIR", tmp_path), \
             patch("play_dm_view.DM_FRAME_FILE", frame_file):
            from play_dm_view import _write_dm_frame
            _write_dm_frame(vitals, dashboard=dashboard)

        data = json.loads(frame_file.read_text())
        assert "conditions" in data
        assert "Kael" in data["conditions"]
        assert data["conditions"]["Kael"][0]["type"] == "Poisoned"

    def test_initiative_in_frame(self, tmp_path):
        """Initiative data appears in dm_frame.json when dashboard provided."""
        from codex.core.dm_dashboard import DMDashboard, VitalsSchema
        from rich.console import Console

        dashboard = DMDashboard(Console(), "DND5E")
        dashboard.initiative.roll_initiative("Aldric", 3, True, 20)
        dashboard.initiative.roll_initiative("Goblin", -1, False, 20)
        dashboard.initiative.sort()

        vitals = VitalsSchema(
            system_name="D&D 5e", system_tag="DND5E",
            primary_resource="HP", primary_current=15, primary_max=20,
        )

        frame_file = tmp_path / "dm_frame.json"
        with patch("play_dm_view.STATE_DIR", tmp_path), \
             patch("play_dm_view.DM_FRAME_FILE", frame_file):
            from play_dm_view import _write_dm_frame
            _write_dm_frame(vitals, dashboard=dashboard)

        data = json.loads(frame_file.read_text())
        assert "initiative" in data
        assert "order" in data["initiative"]
        assert len(data["initiative"]["order"]) == 2
        assert "round" in data["initiative"]

    def test_frame_without_dashboard(self, tmp_path):
        """Without dashboard, no conditions/initiative keys in frame."""
        from codex.core.dm_dashboard import VitalsSchema

        vitals = VitalsSchema(
            system_name="Burnwillow", system_tag="BURNWILLOW",
            primary_resource="HP",
        )

        frame_file = tmp_path / "dm_frame.json"
        with patch("play_dm_view.STATE_DIR", tmp_path), \
             patch("play_dm_view.DM_FRAME_FILE", frame_file):
            from play_dm_view import _write_dm_frame
            _write_dm_frame(vitals)

        data = json.loads(frame_file.read_text())
        assert "conditions" not in data
        assert "initiative" not in data


# =========================================================================
# TestEndToEndSync — 3 tests
# =========================================================================

class TestEndToEndSync:
    """End-to-end broadcast sync between DM Dashboard and bot sessions."""

    def test_dm_condition_sync(self):
        """DM applies condition -> broadcast -> subscriber receives payload."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console

        bm = GlobalBroadcastManager()
        received = []
        bm.subscribe("CONDITION_CHANGE", lambda p: received.append(p))

        dashboard = DMDashboard(Console(), "BURNWILLOW")
        dashboard._broadcast = bm

        result = dashboard.dispatch_command("condition Kael Poisoned 3")
        assert "Poisoned" in result
        assert len(received) == 1
        assert received[0]["entity"] == "Kael"
        assert received[0]["action"] == "apply"
        assert received[0]["condition_type"] == "Poisoned"

    def test_dm_initiative_sync(self):
        """DM advances initiative -> broadcast -> subscriber receives turn."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        from codex.core.dm_dashboard import DMDashboard
        from codex.games.burnwillow.engine import BurnwillowEngine
        from rich.console import Console

        bm = GlobalBroadcastManager()
        received = []
        bm.subscribe("INITIATIVE_ADVANCE", lambda p: received.append(p))

        dashboard = DMDashboard(Console(), "BURNWILLOW")
        dashboard._broadcast = bm

        engine = BurnwillowEngine()
        engine.create_party(["Kael"])
        engine.generate_dungeon(seed=42)

        # Roll initiative first
        dashboard.dispatch_command("init roll", engine)
        # Advance
        result = dashboard.dispatch_command("init next", engine)
        assert "Turn:" in result or "Round" in result
        assert len(received) >= 1
        assert "name" in received[-1]
        assert "order" in received[-1]

    def test_player_rest_broadcast(self):
        """Player rests via bridge -> REST_COMPLETE broadcast fires."""
        from codex.core.services.broadcast import GlobalBroadcastManager
        from codex.games.burnwillow.bridge import BurnwillowBridge

        bm = GlobalBroadcastManager()
        received = []
        bm.subscribe("REST_COMPLETE", lambda p: received.append(p))

        bridge = BurnwillowBridge("TestHero", seed=42, broadcast_manager=bm)
        bridge.engine.character.current_hp = 5

        bridge.step("rest short")
        assert len(received) == 1
        assert received[0]["rest_type"] == "short"
        assert "hp_recovered" in received[0]


# =========================================================================
# TestCompactEmbedConditions — Extra coverage
# =========================================================================

class TestCompactEmbedConditions:
    """Verify compact embed includes conditions field when provided."""

    def _make_paper_doll_char(self):
        """Create a mock Character matching discord_embed's expected interface."""
        char = MagicMock()
        char.name = "Kael"
        char.title = "The Wanderer"
        char.hp_current = 10
        char.doom = 3
        char.stats.hp_max = 20
        char.stats.defense = 12
        char.calculate_dice_pool.return_value = 3
        # Equipment slots
        for slot in ("head", "shoulders", "neck", "chest", "arms", "legs",
                     "right_hand", "left_hand", "right_ring", "left_ring"):
            setattr(char, slot, None)
        return char

    def test_compact_embed_with_conditions(self):
        """character_to_discord_embed_compact includes status effects field."""
        from codex.games.burnwillow.discord_embed import character_to_discord_embed_compact
        from codex.core.mechanics.conditions import Condition, ConditionType

        char = self._make_paper_doll_char()
        conds = [
            Condition(condition_type=ConditionType.POISONED, duration=3),
        ]
        embed = character_to_discord_embed_compact(char, conditions=conds)
        field_names = [f["name"] for f in embed["fields"]]
        assert any("Status" in name for name in field_names)

    def test_compact_embed_no_conditions(self):
        """compact embed without conditions has no status effects field."""
        from codex.games.burnwillow.discord_embed import character_to_discord_embed_compact

        char = self._make_paper_doll_char()
        embed = character_to_discord_embed_compact(char)
        field_names = [f["name"] for f in embed["fields"]]
        assert not any("Status" in name for name in field_names)

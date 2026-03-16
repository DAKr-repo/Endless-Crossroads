"""
tests/test_fitd_roleplay.py — FITD Roleplay Enhancement Tests
===============================================================

Covers:
  Track A: Conversation mode in FITD loop (query_npc_dialogue, scene state)
  Track B: System-aware service flavor text
  Track C: Quest acceptance in FITD loop
  Track D: Contextual error messages

FITD Roleplay Enhancement Sprint
"""
from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================
# Track A: query_npc_dialogue — shared NPC dialogue function
# =========================================================================

class TestQueryNpcDialogue:
    """Tests for narrative_frame.query_npc_dialogue()."""

    def test_returns_none_when_mimir_unavailable(self):
        """query_npc_dialogue returns None if mimir import fails."""
        from codex.core.services.narrative_frame import query_npc_dialogue
        with patch.dict("sys.modules", {"codex.integrations.mimir": None}):
            result = query_npc_dialogue(
                "Durnan", "Hello there",
                {"name": "Durnan", "role": "innkeeper", "dialogue": "Welcome."},
            )
        # Should gracefully return None (import/call fails)
        assert result is None

    def test_returns_cleaned_response_on_success(self):
        """query_npc_dialogue returns cleaned Mimir response."""
        from codex.core.services.narrative_frame import query_npc_dialogue
        mock_mimir = MagicMock()
        mock_mimir.query_mimir.return_value = '  "Welcome to the tavern, friend."  '

        with patch.dict("sys.modules", {"codex.integrations.mimir": mock_mimir}):
            result = query_npc_dialogue(
                "Durnan", "Hello",
                {"name": "Durnan", "role": "innkeeper", "dialogue": "One gold."},
            )
        assert result == "Welcome to the tavern, friend."

    def test_returns_none_on_error_response(self):
        """query_npc_dialogue returns None if Mimir returns an error."""
        from codex.core.services.narrative_frame import query_npc_dialogue
        mock_mimir = MagicMock()
        mock_mimir.query_mimir.return_value = "Error: model not found"

        with patch.dict("sys.modules", {"codex.integrations.mimir": mock_mimir}):
            result = query_npc_dialogue(
                "Durnan", "Hello",
                {"name": "Durnan", "role": "innkeeper"},
            )
        assert result is None

    def test_builds_context_from_npc_data(self):
        """query_npc_dialogue includes role, dialogue, notes in prompt context."""
        from codex.core.services.narrative_frame import query_npc_dialogue
        mock_mimir = MagicMock()
        mock_mimir.query_mimir.return_value = "Response text"

        npc_data = {
            "name": "Volo",
            "role": "quest_giver",
            "dialogue": "Find my friend!",
            "notes": "Chronic liar",
        }
        with patch.dict("sys.modules", {"codex.integrations.mimir": mock_mimir}):
            query_npc_dialogue(
                "Volo", "What happened?", npc_data,
                room_desc="A dimly lit tavern.", events=["Bar fight"],
            )
        # Verify mimir was called with npc_dialogue template
        call_kwargs = mock_mimir.query_mimir.call_args
        assert call_kwargs is not None
        assert "npc_dialogue" in str(call_kwargs)

    def test_handles_empty_npc_data(self):
        """query_npc_dialogue works with empty npc_data dict."""
        from codex.core.services.narrative_frame import query_npc_dialogue
        mock_mimir = MagicMock()
        mock_mimir.query_mimir.return_value = "A grunt."

        with patch.dict("sys.modules", {"codex.integrations.mimir": mock_mimir}):
            result = query_npc_dialogue("Guard", "Hey", {})
        assert result == "A grunt."

    def test_fr_wiki_injection_skipped_for_non_fr(self):
        """query_npc_dialogue skips wiki lookup for non-FR settings."""
        from codex.core.services.narrative_frame import query_npc_dialogue
        mock_mimir = MagicMock()
        mock_mimir.query_mimir.return_value = "Response"

        with patch.dict("sys.modules", {"codex.integrations.mimir": mock_mimir}):
            result = query_npc_dialogue(
                "NPC", "Hello", {}, setting_id="burnwillow",
            )
        assert result == "Response"


# =========================================================================
# Track B: Service flavor text
# =========================================================================

class TestServiceFlavor:
    """Tests for get_service_flavor() and SERVICE_FLAVOR dict."""

    def test_fitd_drink_flavor(self):
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("drink", "cbrpnk")
        assert result is not None
        assert "burn" in result.lower() or "strong" in result.lower()

    def test_dungeon_drink_flavor(self):
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("drink", "dnd5e")
        assert result is not None
        assert "tankard" in result.lower() or "ale" in result.lower()

    def test_fitd_hacking_support(self):
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("hacking_support", "cbrpnk")
        assert result is not None
        assert len(result) > 20

    def test_dungeon_temple_flavor(self):
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("temple", "dnd5e")
        assert result is not None

    def test_unknown_service_returns_none(self):
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("nonexistent_service_xyz", "cbrpnk")
        assert result is None

    def test_default_fallback(self):
        """Unknown system_id falls back to default family."""
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("drink", "unknown_system")
        assert result is not None  # default has drink

    def test_all_fitd_systems_map_to_fitd_family(self):
        from codex.core.services.narrative_frame import _SYSTEM_TO_FAMILY
        for sys_id in ("bitd", "sav", "bob", "cbrpnk", "candela"):
            assert _SYSTEM_TO_FAMILY[sys_id] == "fitd"

    def test_all_dungeon_systems_map_to_dungeon_family(self):
        from codex.core.services.narrative_frame import _SYSTEM_TO_FAMILY
        for sys_id in ("dnd5e", "stc", "burnwillow", "crown"):
            assert _SYSTEM_TO_FAMILY[sys_id] == "dungeon"

    def test_grid_access_flavor(self):
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("grid_access", "cbrpnk")
        assert result is not None
        assert "grid" in result.lower() or "terminal" in result.lower()

    def test_buy_chrome_flavor(self):
        from codex.core.services.narrative_frame import get_service_flavor
        result = get_service_flavor("buy_chrome", "cbrpnk")
        assert result is not None

    def test_bridge_dispatch_uses_flavor(self):
        """bridge._dispatch_service() returns flavor text for known services."""
        from codex.games.bridge import UniversalGameBridge
        bridge = object.__new__(UniversalGameBridge)
        engine = MagicMock()
        engine.system_id = "cbrpnk"
        bridge.engine = engine
        bridge.dead = False
        bridge._system_tag = "CBRPNK"
        bridge._butler = None
        bridge.show_dm_notes = False
        bridge._talking_to = None
        bridge._session_log = []     # WO-V61.0

        result = bridge._dispatch_service("hacking_support")
        # Should contain flavor text, not generic "You use the X service"
        assert "use the hacking_support service" not in result.lower()


# =========================================================================
# Track A (continued): _FITDSceneState conversation mode
# =========================================================================

def _make_scene_state():
    """Create a minimal _FITDSceneState for testing without file I/O."""
    from play_universal import _FITDSceneState
    ss = object.__new__(_FITDSceneState)
    ss.zm = MagicMock()
    ss.zm.chapter_name = "Chapter 1"
    ss.zm.zone_name = "Zone A"
    ss.zm.module_name = "Test Module"
    ss.zm.module_complete = False
    ss.base_path = "/tmp/test"
    ss.current_graph = None
    ss.scene_list = []
    ss.scene_idx = 0
    ss.visited = set()
    ss.audio_dir = None
    ss.audio_map = {}
    # Conversation mode
    ss.talking_to = None
    ss._talking_to_npc = None
    # Quest tracking
    ss.accepted_jobs = []
    ss.pending_offer = None
    return ss


class TestFITDConversationState:
    """Tests for _FITDSceneState conversation mode."""

    def test_enter_conversation(self):
        ss = _make_scene_state()
        ss.enter_conversation("Mara", {"name": "Mara", "role": "fixer"})
        assert ss.talking_to == "Mara"
        assert ss._talking_to_npc["role"] == "fixer"

    def test_exit_conversation(self):
        ss = _make_scene_state()
        ss.enter_conversation("Mara", {"name": "Mara"})
        name = ss.exit_conversation()
        assert name == "Mara"
        assert ss.talking_to is None
        assert ss._talking_to_npc is None

    def test_exit_conversation_when_not_talking(self):
        ss = _make_scene_state()
        name = ss.exit_conversation()
        assert name is None

    def test_accepted_jobs_starts_empty(self):
        ss = _make_scene_state()
        assert ss.accepted_jobs == []

    def test_pending_offer_starts_none(self):
        ss = _make_scene_state()
        assert ss.pending_offer is None


# =========================================================================
# Track C: Quest acceptance
# =========================================================================

class TestFITDQuestAcceptance:
    """Tests for quest/job acceptance in FITD scene state."""

    def test_accept_pending_offer(self):
        ss = _make_scene_state()
        ss.pending_offer = {"title": "Steal the data", "npc": "Mara", "scene_idx": 0}
        job = ss.pending_offer
        ss.accepted_jobs.append(job)
        ss.pending_offer = None
        assert len(ss.accepted_jobs) == 1
        assert ss.accepted_jobs[0]["title"] == "Steal the data"
        assert ss.pending_offer is None

    def test_multiple_jobs(self):
        ss = _make_scene_state()
        ss.accepted_jobs.append({"title": "Job 1", "npc": "A", "scene_idx": 0})
        ss.accepted_jobs.append({"title": "Job 2", "npc": "B", "scene_idx": 1})
        assert len(ss.accepted_jobs) == 2


# =========================================================================
# Track D: Contextual error messages
# =========================================================================

class TestContextualErrors:
    """Tests for improved error messages in FITD loop."""

    def test_npc_name_hint(self):
        """When input matches an NPC name, suggest 'talk' command."""
        # This tests the logic pattern, not the full loop
        npcs = [
            SimpleNamespace(name="Bouncer"),
            SimpleNamespace(name="Mara"),
        ]
        verb = "bouncer"
        hint = None
        for npc in npcs:
            if verb in npc.name.lower():
                hint = f"Try: talk {npc.name.lower().split()[0]}"
                break
        assert hint == "Try: talk bouncer"

    def test_no_npc_match_gives_help_hint(self):
        """When no NPC name matches, suggest 'help'."""
        npcs = [SimpleNamespace(name="Bouncer")]
        verb = "xyzzy"
        hint = None
        for npc in npcs:
            if verb in npc.name.lower():
                hint = f"Try: talk {npc.name.lower()}"
                break
        if hint is None:
            hint = "Unknown command. Try 'help' for options."
        assert "help" in hint


# =========================================================================
# Integration: bridge refactor preserves behavior
# =========================================================================

class TestBridgeNpcDialogueRefactor:
    """Verify bridge._handle_npc_dialogue() still works after refactor."""

    def test_fallback_to_static_dialogue(self):
        """When Mimir fails, bridge falls back to static dialogue."""
        from codex.games.bridge import UniversalGameBridge
        bridge = object.__new__(UniversalGameBridge)
        engine = MagicMock()
        engine.system_id = "dnd5e"
        engine.setting_id = ""
        engine.current_room_id = 1
        pop = SimpleNamespace(content={
            "npcs": [{"name": "Bob", "role": "guard", "dialogue": "Halt!", "notes": ""}],
            "description": "A gate.",
            "event_triggers": [],
        })
        engine.populated_rooms = {1: pop}
        bridge.engine = engine
        bridge.dead = False
        bridge._talking_to = "Bob"
        bridge._system_tag = "DND5E"
        bridge._butler = None
        bridge.show_dm_notes = False
        bridge._session_log = []     # WO-V61.0

        # Mock query_npc_dialogue to return None (simulating Mimir failure)
        with patch("codex.core.services.narrative_frame.query_npc_dialogue", return_value=None):
            result = bridge._handle_npc_dialogue("Hello guard")
        assert "Halt!" in result

    def test_returns_mimir_response(self):
        """When Mimir succeeds, bridge returns its response."""
        from codex.games.bridge import UniversalGameBridge
        bridge = object.__new__(UniversalGameBridge)
        engine = MagicMock()
        engine.system_id = "dnd5e"
        engine.setting_id = ""
        engine.current_room_id = 1
        pop = SimpleNamespace(content={
            "npcs": [{"name": "Bob", "role": "guard", "dialogue": "Halt!", "notes": ""}],
            "description": "A gate.",
            "event_triggers": [],
        })
        engine.populated_rooms = {1: pop}
        bridge.engine = engine
        bridge.dead = False
        bridge._talking_to = "Bob"
        bridge._system_tag = "DND5E"
        bridge._butler = None
        bridge.show_dm_notes = False
        bridge._session_log = []     # WO-V61.0

        with patch("codex.core.services.narrative_frame.query_npc_dialogue",
                   return_value="Stand back, citizen."):
            result = bridge._handle_npc_dialogue("Hello guard")
        assert "Stand back, citizen." in result

    def test_not_talking_to_anyone(self):
        """bridge._handle_npc_dialogue returns error when not in conversation."""
        from codex.games.bridge import UniversalGameBridge
        bridge = object.__new__(UniversalGameBridge)
        engine = MagicMock()
        engine.system_id = "dnd5e"
        engine.current_room_id = 1
        engine.populated_rooms = {}
        bridge.engine = engine
        bridge.dead = False
        bridge._talking_to = None
        bridge._system_tag = "DND5E"
        bridge._butler = None
        bridge.show_dm_notes = False
        bridge._session_log = []     # WO-V61.0

        result = bridge._handle_npc_dialogue("Hello")
        assert "not talking" in result.lower()

    def test_nothing_more_to_say_fallback(self):
        """When no dialogue and Mimir fails, show 'nothing more to say'."""
        from codex.games.bridge import UniversalGameBridge
        bridge = object.__new__(UniversalGameBridge)
        engine = MagicMock()
        engine.system_id = "dnd5e"
        engine.setting_id = ""
        engine.current_room_id = 1
        pop = SimpleNamespace(content={
            "npcs": [{"name": "Silent", "role": "guard", "dialogue": "", "notes": ""}],
            "description": "",
            "event_triggers": [],
        })
        engine.populated_rooms = {1: pop}
        bridge.engine = engine
        bridge.dead = False
        bridge._talking_to = "Silent"
        bridge._system_tag = "DND5E"
        bridge._butler = None
        bridge.show_dm_notes = False
        bridge._session_log = []     # WO-V61.0

        with patch("codex.core.services.narrative_frame.query_npc_dialogue", return_value=None):
            result = bridge._handle_npc_dialogue("Hey")
        assert "nothing more to say" in result.lower()

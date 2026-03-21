"""Tests for codex.bots.fitd_dispatch — shared FITD command dispatcher."""

import pytest
from unittest.mock import MagicMock, patch
from codex.bots.fitd_dispatch import dispatch_fitd_command


# ── Mock Helpers ──────────────────────────────────────────────────────────


def _make_mock_engine(system_id="bitd"):
    engine = MagicMock()
    engine.system_id = system_id
    engine.display_name = "Blades in the Dark"

    char = MagicMock()
    char.name = "Aldo"
    char.playbook = "Cutter"
    char.stress = 3
    char.trauma = 0
    char.harm = []
    char.armor = 1
    sc = MagicMock()
    sc.current = 3
    sc.max_stress = 9
    sc.resist.return_value = {"new_stress": 5, "new_trauma": 0}
    char.stress_clock = sc
    engine.party = [char]
    engine.crew_name = "The Crows"
    engine.heat = 2
    engine.wanted_level = 1
    engine.rep = 4
    engine.coin = 6
    engine.turf = 3
    engine._memory_shards = ["Entered Crow's Foot", "Met Bazso", "Took the score"]
    engine.handle_command.return_value = "Dice: [4, 6]  Result: Partial Success"
    engine.trace_fact.return_value = "Bazso Baz is leader of the Lampblacks."
    return engine


def _make_mock_scene_state():
    ss = MagicMock()
    ss.talking_to = None
    ss._talking_to_npc = None
    ss.pending_offer = None
    ss.accepted_jobs = []
    ss.scene_idx = 0
    ss.visited = set()

    scene = MagicMock()
    scene.npcs = [MagicMock(name="Bazso", role="gang leader", dialogue="What do you want?", notes="")]
    scene.services = ["Drinks", "Rumors"]
    ss.current_scene.return_value = scene
    ss.scene_count.return_value = 5
    ss.format_scene.return_value = "A dimly lit tavern in Crow's Foot."
    ss.scene_list = [(f"room_{i}", MagicMock()) for i in range(5)]
    ss.zm = MagicMock()
    ss.zm.zone_name = "Crow's Foot"
    ss.zm.module_complete = False
    ss.zm.chapter_name = "Act 1"
    ss.zm.module_name = "The Doskvol Job"
    return ss


# ── Always-Available Command Tests ────────────────────────────────────


class TestAlwaysAvailable:
    def test_roll_action(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("roll", "prowl", engine)
        assert result is not None
        assert "Roll: prowl" in result
        engine.handle_command.assert_called_once_with("roll_action", action="prowl")

    def test_roll_no_args(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("roll", "", engine)
        assert "Usage" in result

    def test_resist(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("resist", "", engine)
        assert result is not None
        assert "Resist" in result
        assert "Stress:" in result

    def test_fitd_status(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("fitd_status", "", engine)
        assert "Aldo" in result
        assert "Cutter" in result
        assert "The Crows" in result

    def test_recap(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("recap", "", engine)
        assert result is not None
        # Falls back to raw shards since narrative_loom may not be available
        assert "Recap" in result or "Events" in result

    def test_trace(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("trace", "Bazso", engine)
        assert "Lampblacks" in result

    def test_trace_no_args(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("trace", "", engine)
        assert "Usage" in result


# ── Scene-Dependent Command Tests ─────────────────────────────────────


class TestSceneCommands:
    def test_scene_look(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        result = dispatch_fitd_command("scene", "", engine, scene_state=ss)
        assert "Scene 1/5" in result
        assert "dimly lit tavern" in result

    def test_scene_next(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        new_scene = MagicMock()
        ss.advance_scene.return_value = new_scene
        ss.scene_idx = 1
        ss.format_scene.return_value = "The docks at midnight."
        result = dispatch_fitd_command("next", "", engine, scene_state=ss)
        assert "Scene 2/5" in result

    def test_scene_next_zone_complete(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        ss.advance_scene.return_value = None
        ss.advance_zone.return_value = False
        result = dispatch_fitd_command("next", "", engine, scene_state=ss)
        assert "Zone Complete" in result

    def test_scenes_list(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        result = dispatch_fitd_command("scenes", "", engine, scene_state=ss)
        assert "Scene 1" in result
        assert "Scene 5" in result

    def test_jobs_empty(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        result = dispatch_fitd_command("jobs", "", engine, scene_state=ss)
        assert "No jobs" in result

    def test_accept_pending(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        ss.pending_offer = {"title": "Steal the gem", "npc": "Bazso", "scene_idx": 0}
        result = dispatch_fitd_command("accept", "", engine, scene_state=ss)
        assert "Job Accepted" in result
        assert len(ss.accepted_jobs) == 1

    def test_services(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        result = dispatch_fitd_command("services", "", engine, scene_state=ss)
        assert "Drinks" in result
        assert "Rumors" in result

    def test_investigate(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        result = dispatch_fitd_command("investigate", "", engine, scene_state=ss)
        assert "Investigation" in result


# ── No Scene State Tests ──────────────────────────────────────────────


class TestNoSceneState:
    def test_scene_without_state_returns_none(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("scene", "", engine, scene_state=None)
        assert result is None

    def test_next_without_state_returns_none(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("next", "", engine, scene_state=None)
        assert result is None


# ── Conversation Mode Tests ───────────────────────────────────────────


class TestConversationMode:
    def test_bye_exits_conversation(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        ss.talking_to = "Bazso"
        ss.exit_conversation.return_value = "Bazso"
        result = dispatch_fitd_command("bye", "", engine, scene_state=ss)
        assert "end your conversation" in result
        ss.exit_conversation.assert_called_once()

    def test_accept_in_conversation(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        ss.talking_to = "Bazso"
        ss.pending_offer = {"title": "The Score", "npc": "Bazso", "scene_idx": 0}
        result = dispatch_fitd_command("accept", "", engine, scene_state=ss)
        assert "Job Accepted" in result

    def test_freeform_dialogue(self):
        engine = _make_mock_engine()
        ss = _make_mock_scene_state()
        ss.talking_to = "Bazso"
        ss._talking_to_npc = {"name": "Bazso", "role": "gang leader"}
        result = dispatch_fitd_command("hello", "there", engine, scene_state=ss)
        assert "Bazso" in result


# ── Fall-Through Tests ────────────────────────────────────────────────


class TestFallThrough:
    def test_unknown_command_returns_none(self):
        engine = _make_mock_engine()
        result = dispatch_fitd_command("dance", "", engine)
        assert result is None

    def test_none_engine_returns_none(self):
        result = dispatch_fitd_command("roll", "prowl", None)
        assert result is None

    def test_look_without_scene_falls_through(self):
        """look without scene_state should fall through to bridge."""
        engine = _make_mock_engine()
        result = dispatch_fitd_command("look", "", engine, scene_state=None)
        assert result is None

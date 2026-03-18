"""
tests/test_fitd_scene_persist.py — Gap Fix: FITD Scene State Persistence
=========================================================================
Tests for _FITDSceneState.to_dict()/restore_from_dict() round-trip.
"""
import pytest


class TestFITDSceneStateSerialization:
    """to_dict/restore_from_dict on _FITDSceneState."""

    def _make_scene_state(self):
        """Create a minimal _FITDSceneState with mocked zone manager."""
        from unittest.mock import MagicMock
        from play_universal import _FITDSceneState

        zm = MagicMock()
        zm.load_current_zone.return_value = None
        # Bypass __init__'s _load_current_zone and audio dir probing
        ss = object.__new__(_FITDSceneState)
        ss.zm = zm
        ss.base_path = "/tmp/fake"
        ss.current_graph = None
        ss.scene_list = []
        ss.scene_idx = 0
        ss.visited = set()
        ss.audio_dir = None
        ss.audio_map = {}
        ss.talking_to = None
        ss._talking_to_npc = None
        ss.accepted_jobs = []
        ss.pending_offer = None
        return ss

    def test_round_trip(self):
        """to_dict -> restore_from_dict preserves all persisted fields."""
        ss = self._make_scene_state()
        ss.scene_idx = 3
        ss.visited = {0, 1, 2, 3}
        ss.accepted_jobs = [{"title": "Heist", "reward": 4}]
        ss.pending_offer = {"title": "Smuggle", "reward": 2}

        data = ss.to_dict()

        ss2 = self._make_scene_state()
        ss2.restore_from_dict(data)

        assert ss2.scene_idx == 3
        assert ss2.visited == {0, 1, 2, 3}
        assert len(ss2.accepted_jobs) == 1
        assert ss2.accepted_jobs[0]["title"] == "Heist"
        assert ss2.pending_offer["title"] == "Smuggle"

    def test_empty_defaults(self):
        """to_dict on fresh state returns sane defaults."""
        ss = self._make_scene_state()
        data = ss.to_dict()

        assert data["scene_idx"] == 0
        assert data["visited"] == []
        assert data["accepted_jobs"] == []
        assert data["pending_offer"] is None

    def test_transient_fields_excluded(self):
        """Transient fields (talking_to, audio, graph) must not appear in dict."""
        ss = self._make_scene_state()
        ss.talking_to = "NPC Bob"
        ss.audio_dir = "/tmp/audio"
        ss.current_graph = object()

        data = ss.to_dict()

        assert "talking_to" not in data
        assert "audio_dir" not in data
        assert "audio_map" not in data
        assert "current_graph" not in data
        assert "scene_list" not in data

    def test_restore_with_missing_keys(self):
        """restore_from_dict should handle partial data gracefully."""
        ss = self._make_scene_state()
        ss.scene_idx = 5
        ss.accepted_jobs = [{"title": "Old Job"}]

        # Restore from empty dict — should reset to defaults
        ss.restore_from_dict({})

        assert ss.scene_idx == 0
        assert ss.visited == set()
        assert ss.accepted_jobs == []
        assert ss.pending_offer is None

    def test_visited_set_conversion(self):
        """visited should be serialized as sorted list and restored as set."""
        ss = self._make_scene_state()
        ss.visited = {5, 2, 8, 1}

        data = ss.to_dict()
        assert data["visited"] == [1, 2, 5, 8]  # sorted

        ss2 = self._make_scene_state()
        ss2.restore_from_dict(data)
        assert ss2.visited == {1, 2, 5, 8}

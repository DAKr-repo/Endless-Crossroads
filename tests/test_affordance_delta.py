"""Tests for Affordance-Aware Narrative + Delta-Based Storytelling.

WO-V48.0: Validates _build_affordance_context(), RoomStateSnapshot,
DeltaTracker, and their integration into build_narrative_frame().
"""

import pytest
from unittest.mock import MagicMock

from codex.core.services.narrative_frame import (
    DeltaTracker,
    RoomStateSnapshot,
    _build_affordance_context,
    build_narrative_frame,
)


# =========================================================================
# FIXTURES — Mock engines
# =========================================================================

def _make_mock_engine(
    room_data=None,
    connected_rooms=None,
    tier=1,
    setting="burnwillow",
    has_get_current_room=True,
    has_get_connected_rooms=True,
):
    """Build a mock engine with configurable room state."""
    engine = MagicMock()
    engine.system_id = setting
    engine.current_tier = tier

    if has_get_current_room:
        engine.get_current_room = MagicMock(return_value=room_data)
        # WO-V57.0: Also set get_current_room_dict for callers that prefer dict
        engine.get_current_room_dict = MagicMock(return_value=room_data)
    else:
        # Remove the attribute entirely
        del engine.get_current_room
        del engine.get_current_room_dict

    if has_get_connected_rooms:
        engine.get_connected_rooms = MagicMock(return_value=connected_rooms or [])
    else:
        del engine.get_connected_rooms

    # Remove dungeon/room attributes so _extract_tier falls back to current_tier
    del engine.current_room_id
    del engine.dungeon

    # Remove get_cardinal_exits so _build_affordance_context falls through
    # to get_connected_rooms (which these tests configure explicitly)
    del engine.get_cardinal_exits

    # WO-V61.0: Pin get_mood_context to return a plain dict so narrative_frame
    # comparisons against float values (tension > 0.7) don't hit MagicMock.
    engine.get_mood_context = MagicMock(return_value={
        "tension": 0.0, "tone_words": [], "party_condition": "healthy",
        "system_specific": {},
    })

    return engine


def _room_with_enemies(count=3, names=None):
    """Build a room dict with enemies."""
    if names is None:
        names = ["Rust Rat"] * count
    enemies = [{"name": n, "hp": 5} for n in names]
    return {
        "id": 1,
        "type": "forge",
        "tier": 2,
        "visited": False,
        "enemies": enemies,
        "loot": [{"name": "Rusted Blade"}],
        "hazards": [{"name": "Steam Vent"}],
        "furniture": [],
        "connections": [2, 3],
    }


def _room_cleared():
    """Build a cleared room dict."""
    return {
        "id": 1,
        "type": "corridor",
        "tier": 1,
        "visited": True,
        "enemies": [],
        "loot": [],
        "hazards": [],
        "furniture": [],
        "connections": [2],
    }


def _connected_rooms():
    """Build a set of connected rooms."""
    return [
        {"id": 2, "type": "corridor", "tier": 1, "is_locked": False, "visited": True},
        {"id": 3, "type": "treasure", "tier": 2, "is_locked": True, "visited": False},
        {"id": 4, "type": "forge", "tier": 2, "is_locked": False, "visited": False},
    ]


# =========================================================================
# AFFORDANCE TESTS
# =========================================================================

class TestBuildAffordanceContext:
    """Tests for _build_affordance_context()."""

    def test_enemies_present_shows_names_and_count(self):
        room = _room_with_enemies(3, ["Clockwork Spider", "Rust Golem", "Rust Golem"])
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "3 enemies" in result
        assert "Clockwork Spider" in result
        assert "Rust Golem x2" in result

    def test_no_enemies_shows_cleared(self):
        room = _room_cleared()
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "cleared" in result

    def test_loot_present_shows_item_count(self):
        room = _room_with_enemies(1, ["Rat"])
        room["loot"] = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "3 items" in result

    def test_no_loot_omits_items(self):
        room = _room_cleared()
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "items" not in result

    def test_hazards_present_shows_hazard_count(self):
        room = _room_with_enemies(1, ["Rat"])
        room["hazards"] = [{"name": "Trap"}, {"name": "Pit"}]
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "2 hazards" in result

    def test_no_hazards_omits_hazards(self):
        room = _room_cleared()
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "hazard" not in result

    def test_locked_exit_mentions_locked(self):
        room = _room_with_enemies(1, ["Rat"])
        connected = [{"id": 2, "type": "vault", "tier": 3, "is_locked": True, "visited": False}]
        engine = _make_mock_engine(room_data=room, connected_rooms=connected)
        result = _build_affordance_context(engine)
        assert "locked" in result

    def test_visited_exit_mentions_visited(self):
        room = _room_with_enemies(1, ["Rat"])
        connected = [{"id": 2, "type": "corridor", "tier": 1, "is_locked": False, "visited": True}]
        engine = _make_mock_engine(room_data=room, connected_rooms=connected)
        result = _build_affordance_context(engine)
        assert "visited" in result

    def test_unexplored_exit_mentions_unexplored(self):
        room = _room_with_enemies(1, ["Rat"])
        connected = [{"id": 2, "type": "library", "tier": 2, "is_locked": False, "visited": False}]
        engine = _make_mock_engine(room_data=room, connected_rooms=connected)
        result = _build_affordance_context(engine)
        assert "unexplored" in result

    def test_engine_without_get_current_room_returns_empty(self):
        engine = _make_mock_engine(
            room_data=None, has_get_current_room=False,
        )
        result = _build_affordance_context(engine)
        assert result == ""

    def test_engine_with_no_room_returns_empty(self):
        engine = _make_mock_engine(room_data=None, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert result == ""

    def test_first_visit_label(self):
        room = _room_with_enemies(1, ["Rat"])
        room["visited"] = False
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "first visit" in result

    def test_revisit_label(self):
        room = _room_with_enemies(1, ["Rat"])
        room["visited"] = True
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "revisit" in result

    def test_starts_with_room_state_prefix(self):
        room = _room_with_enemies(1, ["Rat"])
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert result.startswith("ROOM STATE:")

    def test_duplicate_enemies_grouped(self):
        room = _room_with_enemies(4, ["Spider", "Spider", "Golem", "Spider"])
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        result = _build_affordance_context(engine)
        assert "Spider x3" in result
        assert "Golem" in result
        # Golem appears once, should NOT have x1
        assert "Golem x" not in result


class TestAffordanceInFrame:
    """Tests for affordance context integration into build_narrative_frame()."""

    def test_frame_includes_affordance_text(self):
        room = _room_with_enemies(2, ["Shadow Beast", "Shadow Beast"])
        engine = _make_mock_engine(room_data=room, connected_rooms=[])
        frame = build_narrative_frame(engine, "Describe the room")
        assert "ROOM STATE:" in frame["context"]
        assert "Shadow Beast x2" in frame["context"]

    def test_affordance_doesnt_starve_shards(self):
        """Affordance should leave room for memory shards (budget > 0 after)."""
        room = _room_with_enemies(1, ["Rat"])
        engine = _make_mock_engine(room_data=room, connected_rooms=_connected_rooms())
        frame = build_narrative_frame(engine, "Describe the room", budget=800)
        # Context should exist but not consume entire budget
        context_tokens = len(frame["context"]) // 4
        assert context_tokens < 700  # leaves room for shards


# =========================================================================
# DELTA TRACKER TESTS
# =========================================================================

class TestDeltaTracker:
    """Tests for DeltaTracker and RoomStateSnapshot."""

    def test_empty_tracker_has_no_snapshots(self):
        tracker = DeltaTracker()
        assert tracker.to_dict() == {}

    def test_record_visit_creates_snapshot(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(3, ["Rat", "Rat", "Spider"])
        tracker.record_visit(1, room)
        data = tracker.to_dict()
        assert "1" in data
        assert data["1"]["enemy_count"] == 3
        assert data["1"]["visit_count"] == 1

    def test_record_visit_increments_visit_count(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(2, ["Rat", "Rat"])
        tracker.record_visit(1, room)
        tracker.record_visit(1, room)
        data = tracker.to_dict()
        assert data["1"]["visit_count"] == 2

    def test_compute_delta_empty_on_first_visit(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(2, ["Rat", "Rat"])
        delta = tracker.compute_delta(1, room)
        assert delta == ""

    def test_compute_delta_detects_enemies_killed(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(3, ["Rat", "Rat", "Spider"])
        tracker.record_visit(1, room)
        # Revisit with all enemies gone
        cleared = dict(room)
        cleared["enemies"] = []
        delta = tracker.compute_delta(1, cleared)
        assert "enemies are gone" in delta.lower()
        assert "quiet" in delta.lower()

    def test_compute_delta_detects_partial_kill(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(3, ["Rat", "Rat", "Spider"])
        tracker.record_visit(1, room)
        partial = dict(room)
        partial["enemies"] = [{"name": "Spider"}]
        delta = tracker.compute_delta(1, partial)
        assert "2 enemies have fallen" in delta
        assert "1 remain" in delta

    def test_compute_delta_detects_loot_taken(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(1, ["Rat"])
        room["loot"] = [{"name": "Blade"}, {"name": "Shield"}]
        tracker.record_visit(1, room)
        looted = dict(room)
        looted["loot"] = []
        delta = tracker.compute_delta(1, looted)
        assert "taken" in delta.lower()

    def test_compute_delta_detects_partial_loot(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(1, ["Rat"])
        room["loot"] = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        tracker.record_visit(1, room)
        partial = dict(room)
        partial["loot"] = [{"name": "C"}]
        delta = tracker.compute_delta(1, partial)
        assert "2 items have been claimed" in delta

    def test_compute_delta_detects_new_enemies(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(1, ["Rat"])
        tracker.record_visit(1, room)
        more = dict(room)
        more["enemies"] = [{"name": "Rat"}, {"name": "Spider"}, {"name": "Golem"}]
        delta = tracker.compute_delta(1, more)
        assert "2 new enemies" in delta

    def test_compute_delta_empty_when_nothing_changed(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(2, ["Rat", "Spider"])
        tracker.record_visit(1, room)
        delta = tracker.compute_delta(1, room)
        assert delta == ""

    def test_to_dict_from_dict_roundtrip(self):
        tracker = DeltaTracker()
        room1 = _room_with_enemies(3, ["Rat", "Rat", "Spider"])
        room2 = _room_cleared()
        room2["id"] = 2
        tracker.record_visit(1, room1)
        tracker.record_visit(2, room2)
        tracker.record_visit(1, room1)  # second visit

        data = tracker.to_dict()
        restored = DeltaTracker.from_dict(data)
        restored_data = restored.to_dict()

        assert data == restored_data

    def test_from_dict_handles_invalid_keys(self):
        """Non-integer room_id keys should be skipped."""
        data = {"bad_key": {"enemy_count": 1}, "5": {"enemy_count": 2}}
        tracker = DeltaTracker.from_dict(data)
        result = tracker.to_dict()
        assert "5" in result
        assert "bad_key" not in result

    def test_snapshot_preserves_enemy_names(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(2, ["Clockwork Spider", "Rust Golem"])
        tracker.record_visit(1, room)
        data = tracker.to_dict()
        assert "Clockwork Spider" in data["1"]["enemy_names"]
        assert "Rust Golem" in data["1"]["enemy_names"]


class TestDeltaInFrame:
    """Tests for delta tracking integration into build_narrative_frame()."""

    def test_frame_includes_delta_text(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(3, ["Rat", "Rat", "Spider"])
        tracker.record_visit(1, room)

        # Now the room is cleared on revisit
        cleared_room = dict(room)
        cleared_room["enemies"] = []
        cleared_room["visited"] = True
        engine = _make_mock_engine(room_data=cleared_room, connected_rooms=[])

        frame = build_narrative_frame(
            engine, "Describe the room", delta_tracker=tracker,
        )
        assert "CHANGES:" in frame["context"]
        assert "enemies are gone" in frame["context"].lower()

    def test_frame_no_delta_on_first_visit(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(2, ["Rat", "Rat"])
        engine = _make_mock_engine(room_data=room, connected_rooms=[])

        frame = build_narrative_frame(
            engine, "Describe the room", delta_tracker=tracker,
        )
        assert "CHANGES:" not in frame["context"]

    def test_frame_no_delta_without_tracker(self):
        room = _room_with_enemies(2, ["Rat", "Rat"])
        engine = _make_mock_engine(room_data=room, connected_rooms=[])

        frame = build_narrative_frame(
            engine, "Describe the room", delta_tracker=None,
        )
        assert "CHANGES:" not in frame["context"]

    def test_frame_delta_and_affordance_coexist(self):
        tracker = DeltaTracker()
        room = _room_with_enemies(3, ["Rat", "Rat", "Spider"])
        tracker.record_visit(1, room)

        # Revisit with partial clear
        revisited = dict(room)
        revisited["enemies"] = [{"name": "Spider"}]
        revisited["visited"] = True
        engine = _make_mock_engine(
            room_data=revisited, connected_rooms=_connected_rooms(),
        )

        frame = build_narrative_frame(
            engine, "Describe the room", delta_tracker=tracker,
        )
        context = frame["context"]
        assert "ROOM STATE:" in context
        assert "CHANGES:" in context


class TestRoomStateSnapshot:
    """Tests for RoomStateSnapshot dataclass."""

    def test_default_values(self):
        snap = RoomStateSnapshot(enemy_count=5)
        assert snap.enemy_count == 5
        assert snap.enemy_names == []
        assert snap.loot_count == 0
        assert snap.hazard_count == 0
        assert snap.visit_count == 1

    def test_custom_values(self):
        snap = RoomStateSnapshot(
            enemy_count=2,
            enemy_names=["Rat", "Spider"],
            loot_count=3,
            hazard_count=1,
            visit_count=4,
        )
        assert snap.enemy_count == 2
        assert snap.enemy_names == ["Rat", "Spider"]
        assert snap.loot_count == 3
        assert snap.hazard_count == 1
        assert snap.visit_count == 4

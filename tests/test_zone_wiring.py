"""
tests/test_zone_wiring.py
==========================
Tests for ZoneManager, the stateful zone-progression bridge between a
ModuleManifest and the ZoneLoader.

Imports verified against:
    codex/spatial/zone_manager.py      - ZoneManager, event constants
    codex/spatial/module_manifest.py   - ModuleManifest, Chapter, ZoneEntry

Test categories
---------------
1. ZoneManager construction from a ModuleManifest
2. load_current_zone() returns a DungeonGraph (ZoneLoader mocked)
3. advance() moves through zones in order
4. advance() returns None when module is complete
5. check_exit_condition() for each trigger type
6. to_dict() / from_dict() round trip
7. zone_progress property format
8. module_complete flag lifecycle
9. fire_zone_complete() broadcasts (GlobalBroadcastManager mocked)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from codex.spatial.module_manifest import ModuleManifest, Chapter, ZoneEntry
from codex.spatial.zone_manager import (
    ZoneManager,
    EVENT_ZONE_COMPLETE,
    EVENT_ZONE_TRANSITION,
)


# ===========================================================================
# Fixtures / helpers
# ===========================================================================

def _make_zone(zone_id: str, exit_trigger: str = "boss_defeated",
               blueprint: str | None = None) -> ZoneEntry:
    """Build a minimal ZoneEntry."""
    return ZoneEntry(
        zone_id=zone_id,
        exit_trigger=exit_trigger,
        blueprint=blueprint,
    )


def _make_chapter(chapter_id: str, order: int, zones: list[ZoneEntry]) -> Chapter:
    """Build a Chapter with specified zones."""
    return Chapter(
        chapter_id=chapter_id,
        display_name=f"Chapter {order}",
        order=order,
        zones=zones,
    )


def _two_chapter_manifest() -> ModuleManifest:
    """
    2 chapters × 2 zones each  ->  4 total zones.
    Ch1: [zone_a, zone_b],  Ch2: [zone_c, zone_d]
    """
    ch1 = _make_chapter("ch1", 1, [
        _make_zone("zone_a", "quest_complete"),
        _make_zone("zone_b", "boss_defeated"),
    ])
    ch2 = _make_chapter("ch2", 2, [
        _make_zone("zone_c", "player_choice"),
        _make_zone("zone_d", "timer"),
    ])
    return ModuleManifest(
        module_id="test_module",
        display_name="Test Module",
        system_id="dnd5e",
        chapters=[ch1, ch2],
    )


def _single_zone_manifest() -> ModuleManifest:
    """1 chapter, 1 zone — advancing immediately completes the module."""
    ch = _make_chapter("ch1", 1, [_make_zone("only_zone", "boss_defeated")])
    return ModuleManifest(
        module_id="tiny_module",
        display_name="Tiny Module",
        system_id="burnwillow",
        chapters=[ch],
    )


def _make_manager(manifest: ModuleManifest) -> ZoneManager:
    """Return a ZoneManager whose ZoneLoader is bypassed."""
    mgr = ZoneManager(manifest=manifest, base_path="")
    return mgr


# ===========================================================================
# 1. Construction
# ===========================================================================

class TestZoneManagerConstruction:
    """ZoneManager initialises with correct default state."""

    def test_initial_chapter_idx_is_zero(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.chapter_idx == 0

    def test_initial_zone_idx_is_zero(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.zone_idx == 0

    def test_module_complete_starts_false(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.module_complete is False

    def test_current_graph_starts_none(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.current_graph is None

    def test_manifest_reference_preserved(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.manifest is manifest

    def test_sorted_chapters_returns_chapters_by_order(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        chapters = mgr.sorted_chapters
        orders = [c.order for c in chapters]
        assert orders == sorted(orders)

    def test_current_chapter_returns_first_chapter(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.current_chapter is not None
        assert mgr.current_chapter.chapter_id == "ch1"

    def test_current_zone_entry_returns_first_zone(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        ze = mgr.current_zone_entry
        assert ze is not None
        assert ze.zone_id == "zone_a"

    def test_module_name_returns_display_name(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.module_name == "Test Module"

    def test_chapter_name_returns_current_chapter_display(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.chapter_name == "Chapter 1"

    def test_zone_name_returns_current_zone_id(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.zone_name == "zone_a"


# ===========================================================================
# 2. load_current_zone() — ZoneLoader mocked
# ===========================================================================

class TestLoadCurrentZone:
    """load_current_zone() delegates to ZoneLoader.load_zone() and returns the graph."""

    def test_returns_dungeon_graph_from_loader(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        fake_graph = MagicMock(name="DungeonGraph")
        mgr.loader = MagicMock()
        mgr.loader.load_zone.return_value = fake_graph

        result = mgr.load_current_zone()

        assert result is fake_graph

    def test_loader_load_zone_called_with_current_entry(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        fake_graph = MagicMock(name="DungeonGraph")
        mgr.loader = MagicMock()
        mgr.loader.load_zone.return_value = fake_graph

        entry_before = mgr.current_zone_entry
        mgr.load_current_zone()

        mgr.loader.load_zone.assert_called_once_with(entry_before)

    def test_graph_cached_in_current_graph(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        fake_graph = MagicMock(name="DungeonGraph")
        mgr.loader = MagicMock()
        mgr.loader.load_zone.return_value = fake_graph

        mgr.load_current_zone()

        assert mgr.current_graph is fake_graph

    def test_load_zone_returns_none_when_module_complete(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        mgr.module_complete = True
        mgr.chapter_idx = 99  # Force current_zone_entry to None

        result = mgr.load_current_zone()
        assert result is None

    def test_module_complete_set_when_no_entry(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        mgr.chapter_idx = 99  # Out of range

        mgr.load_current_zone()
        assert mgr.module_complete is True


# ===========================================================================
# 3. advance() — moves through zones in order
# ===========================================================================

class TestAdvance:
    """advance() steps through zone chain, updating chapter_idx and zone_idx."""

    def test_advance_from_zone_a_returns_zone_b(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        # Start: ch1 zone_a -> advance to ch1 zone_b
        result = mgr.advance()
        assert result is not None
        assert result.zone_id == "zone_b"

    def test_advance_updates_zone_idx(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()
        assert mgr.zone_idx == 1

    def test_advance_chapter_boundary_increments_chapter_idx(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        # advance past ch1 zone_b -> should cross into ch2
        mgr.advance()  # zone_a -> zone_b (ch1 idx=1)
        mgr.advance()  # zone_b -> zone_c (ch2 idx=0)
        assert mgr.chapter_idx == 1
        assert mgr.zone_idx == 0

    def test_advance_invalidates_cached_graph(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        mgr._current_graph = MagicMock(name="OldGraph")

        mgr.advance()

        assert mgr.current_graph is None

    def test_advance_full_chain_visits_all_zones(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        visited = ["zone_a"]  # Starting zone

        for _ in range(3):
            result = mgr.advance()
            if result:
                visited.append(result.zone_id)

        assert visited == ["zone_a", "zone_b", "zone_c", "zone_d"]

    def test_advance_returns_zone_entry_with_correct_id(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        result = mgr.advance()
        assert isinstance(result, ZoneEntry)
        assert result.zone_id == "zone_b"


# ===========================================================================
# 4. advance() returns None when module is complete
# ===========================================================================

class TestAdvanceModuleComplete:
    """advance() returns None and sets module_complete=True at end of chain."""

    def test_advance_past_last_zone_returns_none(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        # Start at only_zone; advance -> None (no next)
        result = mgr.advance()
        assert result is None

    def test_advance_sets_module_complete_true(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()
        assert mgr.module_complete is True

    def test_advance_after_completion_still_returns_none(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()  # Complete the module
        result = mgr.advance()  # Advance again
        assert result is None

    def test_advance_four_zones_to_completion(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        results = []
        for _ in range(5):  # One extra attempt past end
            results.append(mgr.advance())
        # First 3 advances return entries; 4th returns None
        assert all(r is not None for r in results[:3])
        assert results[3] is None
        assert mgr.module_complete is True


# ===========================================================================
# 5. check_exit_condition() for each trigger type
# ===========================================================================

class TestCheckExitCondition:
    """check_exit_condition() evaluates the current zone's exit_trigger."""

    def _manager_with_trigger(self, trigger: str) -> ZoneManager:
        ch = _make_chapter("ch1", 1, [_make_zone("test_zone", trigger)])
        manifest = ModuleManifest(
            module_id="trigger_test", display_name="Trigger Test",
            system_id="dnd5e", chapters=[ch],
        )
        return _make_manager(manifest)

    # boss_defeated
    def test_boss_defeated_true_when_flag_set(self):
        mgr = self._manager_with_trigger("boss_defeated")
        assert mgr.check_exit_condition({"boss_defeated": True}) is True

    def test_boss_defeated_false_when_flag_absent(self):
        mgr = self._manager_with_trigger("boss_defeated")
        assert mgr.check_exit_condition({}) is False

    def test_boss_defeated_false_when_flag_false(self):
        mgr = self._manager_with_trigger("boss_defeated")
        assert mgr.check_exit_condition({"boss_defeated": False}) is False

    # quest_complete
    def test_quest_complete_true_when_flag_set(self):
        mgr = self._manager_with_trigger("quest_complete")
        assert mgr.check_exit_condition({"quest_complete": True}) is True

    def test_quest_complete_false_when_absent(self):
        mgr = self._manager_with_trigger("quest_complete")
        assert mgr.check_exit_condition({}) is False

    # player_choice
    def test_player_choice_always_true(self):
        mgr = self._manager_with_trigger("player_choice")
        assert mgr.check_exit_condition({}) is True

    def test_player_choice_true_regardless_of_state(self):
        mgr = self._manager_with_trigger("player_choice")
        assert mgr.check_exit_condition({"boss_defeated": False}) is True

    # timer
    def test_timer_true_when_expired(self):
        mgr = self._manager_with_trigger("timer")
        assert mgr.check_exit_condition({"timer_expired": True}) is True

    def test_timer_false_when_not_expired(self):
        mgr = self._manager_with_trigger("timer")
        assert mgr.check_exit_condition({"timer_expired": False}) is False

    def test_timer_false_when_absent(self):
        mgr = self._manager_with_trigger("timer")
        assert mgr.check_exit_condition({}) is False

    # all_rooms
    def test_all_rooms_true_when_rooms_cleared_equals_total(self):
        mgr = self._manager_with_trigger("all_rooms")
        fake_graph = MagicMock()
        fake_graph.rooms = {1: MagicMock(), 2: MagicMock(), 3: MagicMock()}
        mgr._current_graph = fake_graph
        assert mgr.check_exit_condition({"rooms_cleared": 3}) is True

    def test_all_rooms_false_when_not_enough_cleared(self):
        mgr = self._manager_with_trigger("all_rooms")
        fake_graph = MagicMock()
        fake_graph.rooms = {1: MagicMock(), 2: MagicMock(), 3: MagicMock()}
        mgr._current_graph = fake_graph
        assert mgr.check_exit_condition({"rooms_cleared": 2}) is False

    def test_all_rooms_false_when_no_graph_loaded(self):
        mgr = self._manager_with_trigger("all_rooms")
        # No graph loaded -> False
        assert mgr.check_exit_condition({"rooms_cleared": 999}) is False

    # module complete -> no entry
    def test_check_returns_false_when_no_current_entry(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        mgr.chapter_idx = 99  # Out of range
        assert mgr.check_exit_condition({"boss_defeated": True}) is False


# ===========================================================================
# 6. to_dict() / from_dict() round trip
# ===========================================================================

class TestSerialisation:
    """ZoneManager serialises and deserialises its progression state correctly."""

    def test_to_dict_contains_module_id(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        d = mgr.to_dict()
        assert d["module_id"] == "test_module"

    def test_to_dict_contains_chapter_and_zone_idx(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()  # Move to zone_b
        d = mgr.to_dict()
        assert d["chapter_idx"] == 0
        assert d["zone_idx"] == 1

    def test_to_dict_contains_module_complete(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()  # Complete the module
        d = mgr.to_dict()
        assert d["module_complete"] is True

    def test_from_dict_restores_chapter_idx(self):
        manifest = _two_chapter_manifest()
        original = _make_manager(manifest)
        original.advance()  # zone_b
        original.advance()  # zone_c (chapter 2)

        saved = original.to_dict()
        restored = ZoneManager.from_dict(saved, manifest=manifest)

        assert restored.chapter_idx == original.chapter_idx

    def test_from_dict_restores_zone_idx(self):
        manifest = _two_chapter_manifest()
        original = _make_manager(manifest)
        original.advance()

        saved = original.to_dict()
        restored = ZoneManager.from_dict(saved, manifest=manifest)

        assert restored.zone_idx == original.zone_idx

    def test_from_dict_restores_module_complete(self):
        manifest = _single_zone_manifest()
        original = _make_manager(manifest)
        original.advance()

        saved = original.to_dict()
        restored = ZoneManager.from_dict(saved, manifest=manifest)

        assert restored.module_complete is True

    def test_from_dict_with_defaults(self):
        """from_dict with empty dict initialises to defaults."""
        manifest = _two_chapter_manifest()
        mgr = ZoneManager.from_dict({}, manifest=manifest)
        assert mgr.chapter_idx == 0
        assert mgr.zone_idx == 0
        assert mgr.module_complete is False

    def test_round_trip_current_zone_entry_matches(self):
        """After deserialising, current_zone_entry should be the same zone."""
        manifest = _two_chapter_manifest()
        original = _make_manager(manifest)
        original.advance()  # zone_b

        saved = original.to_dict()
        restored = ZoneManager.from_dict(saved, manifest=manifest)

        assert restored.current_zone_entry.zone_id == "zone_b"


# ===========================================================================
# 7. zone_progress property format
# ===========================================================================

class TestZoneProgress:
    """zone_progress returns a human-readable string with chapter/zone fractions."""

    def test_initial_progress_string(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        progress = mgr.zone_progress
        assert "Chapter 1/2" in progress
        assert "Zone 1/2" in progress

    def test_progress_after_advance(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()  # Move to zone_b
        progress = mgr.zone_progress
        assert "Zone 2/2" in progress

    def test_progress_after_chapter_change(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()  # zone_b
        mgr.advance()  # zone_c (ch2)
        progress = mgr.zone_progress
        assert "Chapter 2/2" in progress
        assert "Zone 1/2" in progress


# ===========================================================================
# 8. module_complete flag lifecycle
# ===========================================================================

class TestModuleCompleteFlag:
    """module_complete is set to True exactly when the chain is exhausted."""

    def test_starts_as_false(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        assert mgr.module_complete is False

    def test_not_set_until_advance_past_last_zone(self):
        manifest = _two_chapter_manifest()
        mgr = _make_manager(manifest)
        mgr.advance()  # zone_b
        mgr.advance()  # zone_c
        assert mgr.module_complete is False
        mgr.advance()  # zone_d
        assert mgr.module_complete is False
        mgr.advance()  # past end -> complete
        assert mgr.module_complete is True

    def test_set_by_load_current_zone_when_out_of_range(self):
        manifest = _single_zone_manifest()
        mgr = _make_manager(manifest)
        mgr.chapter_idx = 99
        mgr.load_current_zone()
        assert mgr.module_complete is True


# ===========================================================================
# 9. fire_zone_complete broadcasts (GlobalBroadcastManager mocked)
# ===========================================================================

class TestFireZoneComplete:
    """fire_zone_complete() invokes GlobalBroadcastManager.publish with ZONE_COMPLETE.

    zone_manager.py imports GlobalBroadcastManager inside the try block at
    call time (deferred import).  We patch it on the broadcast module so the
    local `from codex.core.services.broadcast import GlobalBroadcastManager`
    picks up our mock.  We also inject a .publish classmethod attribute so the
    mock_gbm.publish(…) call resolves correctly.
    """

    def _patched_gbm(self):
        """Return a MagicMock configured as a class with a .publish classmethod."""
        mock_cls = MagicMock(name="GlobalBroadcastManager")
        # publish is called as a classmethod: GlobalBroadcastManager.publish(...)
        return mock_cls

    def test_fire_zone_complete_calls_broadcast(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        mgr.fire_zone_complete()
        bm.broadcast.assert_called_once()

    def test_fire_zone_complete_passes_event_zone_complete(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        mgr.fire_zone_complete()
        event_name = bm.broadcast.call_args[0][0]
        assert event_name == EVENT_ZONE_COMPLETE

    def test_fire_zone_complete_payload_contains_module_id(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        mgr.fire_zone_complete()
        payload = bm.broadcast.call_args[0][1]
        assert payload["module"] == "test_module"

    def test_fire_zone_complete_payload_contains_zone_id(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        mgr.fire_zone_complete()
        payload = bm.broadcast.call_args[0][1]
        assert payload["zone"] == "zone_a"

    def test_advance_calls_broadcast_with_zone_transition(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        mgr.advance()
        bm.broadcast.assert_called_once()
        event_name = bm.broadcast.call_args[0][0]
        assert event_name == EVENT_ZONE_TRANSITION

    def test_advance_broadcast_payload_has_next_zone(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        mgr.advance()
        payload = bm.broadcast.call_args[0][1]
        assert payload["zone"] == "zone_b"

    def test_fire_zone_complete_survives_broadcast_exception(self):
        """fire_zone_complete must not raise even if broadcast raises."""
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        bm.broadcast.side_effect = RuntimeError("bus error")
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        # Should not raise — the except clause in zone_manager swallows it
        mgr.fire_zone_complete()

    def test_advance_broadcast_survives_exception(self):
        """advance() must not raise even if broadcast raises."""
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        bm.broadcast.side_effect = RuntimeError("bus error")
        mgr = ZoneManager(manifest=manifest, base_path="", broadcast_manager=bm)
        result = mgr.advance()

        # The advance itself must still succeed
        assert result is not None
        assert result.zone_id == "zone_b"

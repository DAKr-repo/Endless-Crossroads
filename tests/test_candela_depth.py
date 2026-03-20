"""
tests/test_candela_depth.py — WO-P4: Candela Depth
=====================================================
Tests for:
  - AssignmentTracker (assignments.py)
  - PhenomenaTracker (investigations.py)
  - CandelaEngine integration (games/candela/__init__.py)
"""

import pytest
from codex.games.candela.assignments import AssignmentTracker
from codex.games.candela.investigations import PhenomenaTracker
from codex.games.candela import CandelaEngine, CandelaCharacter


# =============================================================================
# AssignmentTracker
# =============================================================================

class TestAssignmentTracker:
    """Tests for AssignmentTracker phase lifecycle."""

    def test_starts_at_hook(self):
        tracker = AssignmentTracker()
        assert tracker.current_phase == "hook"

    def test_advance_phase_hook_to_exploration(self):
        tracker = AssignmentTracker()
        result = tracker.advance_phase()
        assert result["success"] is True
        assert result["old_phase"] == "hook"
        assert result["new_phase"] == "exploration"
        assert tracker.current_phase == "exploration"

    def test_advance_phase_exploration_to_climax(self):
        tracker = AssignmentTracker()
        tracker.advance_phase()  # hook -> exploration
        result = tracker.advance_phase()  # exploration -> climax
        assert result["success"] is True
        assert result["old_phase"] == "exploration"
        assert result["new_phase"] == "climax"
        assert tracker.current_phase == "climax"

    def test_cannot_advance_past_climax(self):
        tracker = AssignmentTracker()
        tracker.advance_phase()
        tracker.advance_phase()  # now at climax
        result = tracker.advance_phase()
        assert result["success"] is False
        assert "climax" in result["error"].lower()
        assert tracker.current_phase == "climax"

    def test_complete_only_works_from_climax(self):
        tracker = AssignmentTracker(assignment_name="The Pale Door")
        # From hook — should fail
        result = tracker.complete()
        assert result["success"] is False
        assert "climax" in result["error"].lower()

        tracker.advance_phase()  # -> exploration
        result = tracker.complete()
        assert result["success"] is False

        tracker.advance_phase()  # -> climax
        result = tracker.complete()
        assert result["success"] is True
        assert result["assignment"] == "The Pale Door"
        assert tracker.completed is True

    def test_add_note_stores_to_current_phase(self):
        tracker = AssignmentTracker()
        tracker.add_note("Witness saw lights in the attic.")
        assert "Witness saw lights in the attic." in tracker.phase_notes["hook"]
        assert tracker.phase_notes["exploration"] == []

        tracker.advance_phase()
        tracker.add_note("Blood on the floor.")
        assert "Blood on the floor." in tracker.phase_notes["exploration"]
        assert len(tracker.phase_notes["hook"]) == 1  # unchanged

    def test_get_summary_includes_phase_info(self):
        tracker = AssignmentTracker(assignment_name="Hollow Choir")
        tracker.add_note("A clock running backward.")
        summary = tracker.get_summary()
        assert "Hollow Choir" in summary
        assert "HOOK" in summary
        assert "Active" in summary
        assert "A clock running backward." in summary

    def test_get_summary_shows_completed_when_done(self):
        tracker = AssignmentTracker(assignment_name="End Case")
        tracker.advance_phase()
        tracker.advance_phase()
        tracker.complete()
        summary = tracker.get_summary()
        assert "COMPLETED" in summary

    def test_to_dict_from_dict_round_trip(self):
        tracker = AssignmentTracker(assignment_name="Crimson Weave")
        tracker.add_note("First clue found.")
        tracker.advance_phase()
        tracker.add_note("Exploration note.")
        data = tracker.to_dict()

        restored = AssignmentTracker.from_dict(data)
        assert restored.assignment_name == "Crimson Weave"
        assert restored.current_phase == "exploration"
        assert "First clue found." in restored.phase_notes["hook"]
        assert "Exploration note." in restored.phase_notes["exploration"]
        assert restored.completed is False

    def test_round_trip_preserves_completed_flag(self):
        tracker = AssignmentTracker(assignment_name="Done")
        tracker.advance_phase()
        tracker.advance_phase()
        tracker.complete()
        data = tracker.to_dict()
        restored = AssignmentTracker.from_dict(data)
        assert restored.completed is True
        assert restored.current_phase == "climax"

    def test_from_dict_defaults_on_missing_keys(self):
        restored = AssignmentTracker.from_dict({})
        assert restored.current_phase == "hook"
        assert restored.assignment_name == ""
        assert restored.completed is False
        assert restored.phase_notes == {"hook": [], "exploration": [], "climax": []}


# =============================================================================
# PhenomenaTracker
# =============================================================================

class TestPhenomenaTracker:
    """Tests for PhenomenaTracker escalation clock."""

    def test_starts_at_dormant(self):
        tracker = PhenomenaTracker()
        assert tracker.stage == "dormant"
        assert tracker.escalation_ticks == 0

    def test_tick_advances_through_stages(self):
        tracker = PhenomenaTracker(escalation_threshold=2)
        # 2 ticks -> stirring
        result = tracker.tick(2)
        assert result["advanced"] is True
        assert result["old_stage"] == "dormant"
        assert result["new_stage"] == "stirring"
        assert tracker.stage == "stirring"

    def test_tick_does_not_advance_before_threshold(self):
        tracker = PhenomenaTracker(escalation_threshold=4)
        result = tracker.tick(1)
        assert result["advanced"] is False
        assert result["new_stage"] == "dormant"
        assert tracker.escalation_ticks == 1

    def test_tick_can_skip_multiple_stages(self):
        tracker = PhenomenaTracker(escalation_threshold=2)
        # 6 ticks should advance 3 stages: dormant->stirring->active->consuming
        result = tracker.tick(6)
        assert tracker.stage == "consuming"

    def test_cannot_advance_past_consuming(self):
        tracker = PhenomenaTracker(escalation_threshold=2)
        tracker.tick(8)  # More than enough to hit consuming
        assert tracker.stage == "consuming"
        # Ticks should be capped at threshold, not grow unbounded
        assert tracker.escalation_ticks == tracker.escalation_threshold

    def test_reduce_decreases_ticks(self):
        tracker = PhenomenaTracker()
        tracker.tick(2)
        result = tracker.reduce(1)
        assert result["old_ticks"] == 2
        assert result["new_ticks"] == 1
        assert result["stage"] == "dormant"

    def test_reduce_floors_at_zero(self):
        tracker = PhenomenaTracker()
        tracker.tick(1)
        result = tracker.reduce(10)
        assert result["new_ticks"] == 0
        assert tracker.escalation_ticks == 0

    def test_reduce_does_not_change_stage(self):
        """Reducing ticks does not reverse the stage."""
        tracker = PhenomenaTracker(escalation_threshold=2)
        tracker.tick(2)  # -> stirring, 0 ticks
        tracker.tick(1)  # 1 tick at stirring
        result = tracker.reduce(1)
        assert tracker.stage == "stirring"  # Stage unchanged
        assert result["new_ticks"] == 0

    def test_to_dict_from_dict_round_trip(self):
        tracker = PhenomenaTracker(
            phenomena_name="The Hollow Choir",
            escalation_threshold=3,
        )
        tracker.tick(2)
        data = tracker.to_dict()

        restored = PhenomenaTracker.from_dict(data)
        assert restored.phenomena_name == "The Hollow Choir"
        assert restored.escalation_threshold == 3
        assert restored.escalation_ticks == 2
        assert restored.stage == "dormant"

    def test_from_dict_defaults_on_missing_keys(self):
        restored = PhenomenaTracker.from_dict({})
        assert restored.stage == "dormant"
        assert restored.escalation_ticks == 0
        assert restored.escalation_threshold == 4
        assert restored.phenomena_name == ""

    def test_get_status_includes_stage_name(self):
        tracker = PhenomenaTracker(phenomena_name="Pale Door", escalation_threshold=4)
        tracker.tick(1)
        status = tracker.get_status()
        assert "Pale Door" in status
        assert "DORMANT" in status
        assert "1/4" in status
        # Stage ladder should appear
        assert "stirring" in status
        assert "active" in status
        assert "consuming" in status

    def test_get_status_highlights_current_stage(self):
        tracker = PhenomenaTracker(escalation_threshold=2)
        tracker.tick(2)  # advance to stirring
        status = tracker.get_status()
        assert "STIRRING" in status


# =============================================================================
# CandelaEngine Integration
# =============================================================================

class TestCandelaEngineIntegration:
    """Integration tests: engine commands wire through to tracker logic."""

    def _make_engine(self) -> CandelaEngine:
        engine = CandelaEngine()
        char = CandelaCharacter(name="Ada Voss", role="Weird")
        engine.party.append(char)
        engine.character = char
        return engine

    # ── Assignment commands ────────────────────────────────────────────

    def test_start_assignment_sets_name_and_phase(self):
        engine = self._make_engine()
        result = engine.handle_command("start_assignment", name="The Pale Door")
        assert "The Pale Door" in result
        assert "HOOK" in result
        tracker = engine._assignment_tracker
        assert tracker is not None
        assert tracker.assignment_name == "The Pale Door"
        assert tracker.current_phase == "hook"

    def test_start_assignment_requires_name(self):
        engine = self._make_engine()
        result = engine.handle_command("start_assignment")
        assert "name" in result.lower() or "specify" in result.lower()

    def test_advance_phase_transitions_correctly(self):
        engine = self._make_engine()
        engine.handle_command("start_assignment", name="Crimson Weave")
        result = engine.handle_command("advance_phase")
        assert "HOOK" in result
        assert "EXPLORATION" in result
        assert engine._assignment_tracker.current_phase == "exploration"

    def test_advance_phase_at_climax_returns_error(self):
        engine = self._make_engine()
        engine.handle_command("start_assignment", name="X")
        engine.handle_command("advance_phase")  # -> exploration
        engine.handle_command("advance_phase")  # -> climax
        result = engine.handle_command("advance_phase")  # should error
        assert "climax" in result.lower()

    def test_complete_assignment_increments_assignments_completed(self):
        engine = self._make_engine()
        assert engine.assignments_completed == 0
        engine.handle_command("start_assignment", name="Test Mission")
        engine.handle_command("advance_phase")
        engine.handle_command("advance_phase")  # -> climax
        result = engine.handle_command("complete_assignment")
        assert "Test Mission" in result
        assert engine.assignments_completed == 1

    def test_complete_assignment_from_hook_returns_error(self):
        engine = self._make_engine()
        engine.handle_command("start_assignment", name="Y")
        result = engine.handle_command("complete_assignment")
        assert "climax" in result.lower() or "cannot" in result.lower()

    def test_assignment_status_shows_summary(self):
        engine = self._make_engine()
        engine.handle_command("start_assignment", name="Flickering Man")
        result = engine.handle_command("assignment_status")
        assert "Flickering Man" in result
        assert "HOOK" in result

    # ── Bleed escalation ──────────────────────────────────────────────

    def test_bleed_escalation_triggers_at_threshold(self):
        engine = self._make_engine()
        # One investigator, threshold = 1 * 2 = 2
        engine.character.bleed = 2
        result = engine.handle_command("bleed_escalation")
        assert "ESCALATION" in result
        assert "brain mark" in result.lower()

    def test_bleed_escalation_does_not_trigger_below_threshold(self):
        engine = self._make_engine()
        engine.character.bleed = 1  # threshold = 2
        result = engine.handle_command("bleed_escalation")
        assert "ESCALATION" not in result
        assert "holds" in result.lower() or "1/2" in result

    def test_bleed_escalation_multi_party(self):
        engine = self._make_engine()
        char2 = CandelaCharacter(name="Bram Gault", role="Muscle")
        engine.party.append(char2)
        # 2 investigators -> threshold = 4
        engine.character.bleed = 1
        char2.bleed = 1  # total = 2, below threshold
        result = engine.handle_command("bleed_escalation")
        assert "2/4" in result

    # ── Phenomena commands ────────────────────────────────────────────

    def test_phenomena_tick_command_advances_phenomena(self):
        engine = self._make_engine()
        # Default threshold = 4; tick 4 times
        result = engine.handle_command("phenomena_tick", amount=4)
        tracker = engine._phenomena_tracker
        assert tracker is not None
        assert tracker.stage == "stirring"
        assert "STIRRING" in result

    def test_phenomena_tick_without_advance(self):
        engine = self._make_engine()
        result = engine.handle_command("phenomena_tick", amount=1)
        assert "dormant" in result.lower()
        assert "1/4" in result

    def test_phenomena_reduce_command(self):
        engine = self._make_engine()
        engine.handle_command("phenomena_tick", amount=2)
        result = engine.handle_command("phenomena_reduce", amount=1)
        assert "1" in result  # new ticks = 1
        assert "dormant" in result.lower()

    def test_phenomena_status_command(self):
        engine = self._make_engine()
        result = engine.handle_command("phenomena_status")
        assert "dormant" in result.lower() or "DORMANT" in result

    # ── Fortune (inherited from NarrativeEngineBase) ──────────────────

    def test_fortune_command_works(self):
        engine = self._make_engine()
        result = engine.handle_command("fortune", dice_count=2)
        # Should produce some output containing dice or outcome
        assert result  # non-empty
        assert isinstance(result, str)

    # ── Save / Load ───────────────────────────────────────────────────

    def test_save_load_preserves_assignment_state(self):
        engine = self._make_engine()
        engine.handle_command("start_assignment", name="Restored Mission")
        engine.handle_command("advance_phase")  # -> exploration
        state = engine.save_state()

        engine2 = CandelaEngine()
        engine2.load_state(state)
        assert engine2._assignment_tracker is not None
        assert engine2._assignment_tracker.assignment_name == "Restored Mission"
        assert engine2._assignment_tracker.current_phase == "exploration"

    def test_save_load_preserves_phenomena_state(self):
        engine = self._make_engine()
        engine.handle_command("phenomena_tick", amount=5)  # crosses into stirring
        state = engine.save_state()

        engine2 = CandelaEngine()
        engine2.load_state(state)
        assert engine2._phenomena_tracker is not None
        assert engine2._phenomena_tracker.stage == "stirring"

    def test_save_with_no_trackers_initialised(self):
        """Engines with no tracker use should save None and load cleanly."""
        engine = self._make_engine()
        state = engine.save_state()
        assert state.get("assignment_tracker") is None
        assert state.get("phenomena_tracker") is None

        engine2 = CandelaEngine()
        engine2.load_state(state)
        # Trackers should not be initialised until first use
        assert engine2._assignment_tracker is None
        assert engine2._phenomena_tracker is None

    def test_save_load_preserves_assignments_completed(self):
        engine = self._make_engine()
        engine.handle_command("start_assignment", name="M")
        engine.handle_command("advance_phase")
        engine.handle_command("advance_phase")
        engine.handle_command("complete_assignment")
        assert engine.assignments_completed == 1

        state = engine.save_state()
        engine2 = CandelaEngine()
        engine2.load_state(state)
        assert engine2.assignments_completed == 1

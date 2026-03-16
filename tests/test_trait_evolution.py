"""Tests for WO-V61.0 Track D — Trait Evolution system."""
import pytest
from codex.core.trait_evolution import (
    TraitEvolution, TraitDelta, NUDGE_TRIGGERS, apply_nudge_trigger,
)


class TestTraitEvolution:
    def _make_evo(self):
        return TraitEvolution({"aggression": 0.9, "curiosity": 0.3, "caution": 0.1})

    def test_initial_traits_unchanged(self):
        evo = self._make_evo()
        assert evo.get_current_value("aggression") == 0.9
        assert evo.get_current_value("curiosity") == 0.3
        assert evo.get_current_value("caution") == 0.1

    def test_nudge_changes_value(self):
        evo = self._make_evo()
        evo.nudge("caution", 0.1, "test")
        assert evo.get_current_value("caution") == pytest.approx(0.2, abs=0.01)

    def test_nudge_accumulates(self):
        evo = self._make_evo()
        evo.nudge("aggression", -0.05, "r1")
        evo.nudge("aggression", -0.05, "r2")
        assert evo.get_current_value("aggression") == pytest.approx(0.8, abs=0.01)

    def test_max_drift_cap(self):
        """Can't drift more than MAX_DRIFT from original."""
        evo = self._make_evo()
        # Try to push aggression down by 0.6 (exceeds MAX_DRIFT=0.4)
        for _ in range(20):
            evo.nudge("aggression", -0.05, "test")
        # Should cap at original - 0.4 = 0.5
        assert evo.get_current_value("aggression") == pytest.approx(0.5, abs=0.01)

    def test_max_drift_cap_upward(self):
        evo = self._make_evo()
        for _ in range(20):
            evo.nudge("caution", 0.05, "test")
        # 0.1 + 0.4 = 0.5
        assert evo.get_current_value("caution") == pytest.approx(0.5, abs=0.01)

    def test_value_clamped_0_to_1(self):
        """Values never go below 0 or above 1."""
        evo = TraitEvolution({"caution": 0.05})
        evo.nudge("caution", -0.1, "test")
        assert evo.get_current_value("caution") >= 0.0

        evo2 = TraitEvolution({"aggression": 0.95})
        evo2.nudge("aggression", 0.3, "test")
        assert evo2.get_current_value("aggression") <= 1.0

    def test_unknown_trait_ignored(self):
        evo = self._make_evo()
        evo.nudge("unknown_trait", 0.5, "test")
        assert evo.get_current_value("unknown_trait") == 0.0

    def test_get_current_traits(self):
        evo = self._make_evo()
        evo.nudge("caution", 0.1, "test")
        traits = evo.get_current_traits()
        assert "aggression" in traits
        assert "curiosity" in traits
        assert "caution" in traits
        assert traits["caution"] == pytest.approx(0.2, abs=0.01)

    def test_get_drift(self):
        evo = self._make_evo()
        evo.nudge("aggression", -0.1, "r1")
        evo.nudge("aggression", -0.05, "r2")
        assert evo.get_drift("aggression") == pytest.approx(-0.15, abs=0.01)

    def test_evolution_summary_empty(self):
        evo = self._make_evo()
        assert "No personality evolution" in evo.get_evolution_summary()

    def test_evolution_summary_with_changes(self):
        evo = self._make_evo()
        evo.nudge("caution", 0.1, "nearly_died")
        summary = evo.get_evolution_summary()
        assert "caution" in summary

    def test_serialization_roundtrip(self):
        evo = self._make_evo()
        evo.nudge("caution", 0.05, "nearly_died", turn=10)
        evo.nudge("aggression", -0.03, "saved_ally", turn=15)
        data = evo.to_dict()
        restored = TraitEvolution.from_dict(data)
        assert restored.get_current_value("caution") == pytest.approx(
            evo.get_current_value("caution"), abs=0.001)
        assert restored.get_current_value("aggression") == pytest.approx(
            evo.get_current_value("aggression"), abs=0.001)
        assert len(restored.deltas) == 2


class TestNudgeTriggers:
    def test_nearly_died_increases_caution(self):
        evo = TraitEvolution({"aggression": 0.5, "curiosity": 0.5, "caution": 0.5})
        msgs = apply_nudge_trigger(evo, "nearly_died")
        assert len(msgs) > 0
        assert evo.get_current_value("caution") > 0.5

    def test_killed_boss_increases_aggression(self):
        evo = TraitEvolution({"aggression": 0.5, "curiosity": 0.5, "caution": 0.5})
        apply_nudge_trigger(evo, "killed_boss")
        assert evo.get_current_value("aggression") > 0.5

    def test_saved_ally_decreases_aggression(self):
        evo = TraitEvolution({"aggression": 0.5, "curiosity": 0.5, "caution": 0.5})
        apply_nudge_trigger(evo, "saved_ally")
        assert evo.get_current_value("aggression") < 0.5
        assert evo.get_current_value("caution") < 0.5

    def test_unknown_trigger_no_op(self):
        evo = TraitEvolution({"aggression": 0.5, "curiosity": 0.5, "caution": 0.5})
        msgs = apply_nudge_trigger(evo, "nonexistent_trigger")
        assert msgs == []

    def test_all_defined_triggers_have_entries(self):
        for trigger in NUDGE_TRIGGERS:
            assert isinstance(NUDGE_TRIGGERS[trigger], list)

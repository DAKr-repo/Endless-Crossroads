"""Tests for WO-V61.0 Track D — Cross-System Companion Maps."""
import pytest
from codex.core.companion_maps import (
    COMPANION_CLASS_MAP, DECISION_NARRATION,
    get_companion_class, narrate_decision,
)


class TestCompanionClassMap:
    def test_all_systems_covered(self):
        expected_systems = {
            "dnd5e", "stc", "bitd", "sav", "bob", "cbrpnk",
            "candela", "burnwillow", "crown",
        }
        assert expected_systems.issubset(set(COMPANION_CLASS_MAP.keys()))

    def test_all_archetypes_per_system(self):
        archetypes = {"vanguard", "scholar", "scavenger", "healer"}
        for system_id, mapping in COMPANION_CLASS_MAP.items():
            for arch in archetypes:
                assert arch in mapping, f"{system_id} missing {arch}"

    def test_get_companion_class_dnd5e(self):
        result = get_companion_class("dnd5e", "vanguard")
        assert result is not None
        assert result["class"] == "Fighter"

    def test_get_companion_class_bitd(self):
        result = get_companion_class("bitd", "scholar")
        assert result == "Whisper"

    def test_get_companion_class_unknown_system(self):
        result = get_companion_class("unknown_system", "vanguard")
        assert result is None

    def test_get_companion_class_unknown_archetype(self):
        result = get_companion_class("dnd5e", "berserker")
        assert result is None


class TestDecisionNarration:
    def test_narrate_returns_string(self):
        result = narrate_decision("attack", "vanguard", "Bryn", "Ghoul")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_narrate_includes_name(self):
        result = narrate_decision("attack", "vanguard", "Bryn", "Ghoul")
        assert "Bryn" in result

    def test_narrate_fallback_for_unknown(self):
        """Unknown action+archetype combos should return empty or generic."""
        result = narrate_decision("dance", "vanguard", "Test")
        # Either empty or a generic fallback is fine
        assert isinstance(result, str)

    def test_narrate_evolved_caution(self):
        """High caution drift changes attack narration."""
        drift = {"caution": 0.2, "aggression": 0.0}
        result = narrate_decision("attack", "vanguard", "Bryn", "Ghoul", evolution_drift=drift)
        assert "hesitate" in result.lower() or "cover" in result.lower()

    def test_narrate_evolved_aggression_loss(self):
        """Low aggression drift changes attack narration."""
        drift = {"caution": 0.0, "aggression": -0.15}
        result = narrate_decision("attack", "vanguard", "Bryn", "Ghoul", evolution_drift=drift)
        assert "learned" in result.lower() or "line" in result.lower()

    def test_narrate_no_evolution_normal(self):
        """Without evolution drift, normal template is used."""
        result = narrate_decision("attack", "vanguard", "Bryn", "Ghoul", evolution_drift=None)
        assert "Bryn" in result

    def test_decision_narration_keys_are_tuples(self):
        for key in DECISION_NARRATION:
            assert isinstance(key, tuple)
            assert len(key) == 2


class TestGenericAutopilotEvolution:
    """Tests for GenericAutopilotAgent trait evolution integration."""

    def _make_vanguard(self):
        """Create a standard vanguard CompanionPersonality."""
        from codex.games.burnwillow.autopilot import CompanionPersonality
        return CompanionPersonality(
            archetype="vanguard",
            description="A battle-hardened warrior.",
            quirk="Always charges first.",
            aggression=0.9,
            curiosity=0.2,
            caution=0.1,
        )

    def test_init_evolution(self):
        from codex.core.autopilot import GenericAutopilotAgent
        p = self._make_vanguard()
        agent = GenericAutopilotAgent(p, "burnwillow")
        agent.init_evolution()
        assert agent.evolution is not None
        assert agent.evolution.original["aggression"] == 0.9

    def test_nudge_passthrough(self):
        from codex.core.autopilot import GenericAutopilotAgent
        p = self._make_vanguard()
        agent = GenericAutopilotAgent(p, "burnwillow")
        msgs = agent.nudge("nearly_died", turn=5)
        assert len(msgs) > 0
        assert agent.evolution is not None

    def test_get_effective_personality(self):
        from codex.core.autopilot import GenericAutopilotAgent
        p = self._make_vanguard()
        agent = GenericAutopilotAgent(p, "burnwillow")
        agent.nudge("nearly_died")  # +0.03 caution
        effective = agent.get_effective_personality()
        assert effective.caution > p.caution
        # Original personality object is unchanged
        assert p.caution == 0.1

    def test_init_evolution_idempotent(self):
        """Calling init_evolution twice does not reset accumulated drift."""
        from codex.core.autopilot import GenericAutopilotAgent
        p = self._make_vanguard()
        agent = GenericAutopilotAgent(p, "burnwillow")
        agent.init_evolution()
        agent.nudge("nearly_died")
        first_caution = agent.evolution.get_current_value("caution")
        agent.init_evolution()  # Should be a no-op since evolution already exists
        assert agent.evolution.get_current_value("caution") == first_caution

    def test_evolution_original_preserved(self):
        """Original trait values are stored correctly in the evolution tracker."""
        from codex.core.autopilot import GenericAutopilotAgent
        p = self._make_vanguard()
        agent = GenericAutopilotAgent(p, "burnwillow")
        agent.init_evolution()
        assert agent.evolution.original["aggression"] == pytest.approx(0.9)
        assert agent.evolution.original["curiosity"] == pytest.approx(0.2)
        assert agent.evolution.original["caution"] == pytest.approx(0.1)

    def test_multiple_nudges_accumulate(self):
        """Multiple nudge triggers stack on the same trait."""
        from codex.core.autopilot import GenericAutopilotAgent
        p = self._make_vanguard()
        agent = GenericAutopilotAgent(p, "burnwillow")
        agent.nudge("nearly_died")   # +0.03 caution
        agent.nudge("nearly_died")   # +0.03 caution again
        caution = agent.evolution.get_current_value("caution")
        assert caution == pytest.approx(0.16, abs=0.01)  # 0.1 + 0.06

    def test_effective_personality_aggression_decays(self):
        """saved_ally trigger reduces aggression in effective personality."""
        from codex.core.autopilot import GenericAutopilotAgent
        p = self._make_vanguard()
        agent = GenericAutopilotAgent(p, "burnwillow")
        agent.nudge("saved_ally")   # -0.01 aggression
        effective = agent.get_effective_personality()
        assert effective.aggression < 0.9

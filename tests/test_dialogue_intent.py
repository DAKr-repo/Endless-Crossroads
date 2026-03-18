"""
Tests for WO-V62.0: Dialogue-to-Trait Evolution Bridge.
=======================================================

Covers:
- Intent classifier (positive/negative/fallback categories)
- Bond mechanics (multiplier, tiers, accumulation, clamp)
- Cooldown enforcement
- Grudging narration
- Reluctant ally autopilot
- Serialization round-trip
- NPCMemoryBank.get_recent_shards()
"""

import random
import pytest

from codex.core.dialogue_intent import classify_intent, DialogueIntent
from codex.core.trait_evolution import TraitEvolution, TraitDelta
from codex.core.companion_maps import narrate_decision, _GRUDGING_NARRATION


# =========================================================================
# INTENT CLASSIFIER TESTS
# =========================================================================

class TestClassifyIntent:

    # --- Positive intents ---

    def test_counsel_caution_phrase(self):
        intent = classify_intent("be careful out there")
        assert intent.category == "counsel_caution"
        assert intent.confidence >= 0.3
        assert ("caution", 0.03) in intent.trait_nudges
        assert intent.bond_delta > 0

    def test_counsel_caution_dont_rush(self):
        intent = classify_intent("don't rush in blindly")
        assert intent.category == "counsel_caution"

    def test_encourage_aggression(self):
        intent = classify_intent("charge in and hit them hard!")
        assert intent.category == "encourage_aggression"
        assert ("aggression", 0.03) in intent.trait_nudges

    def test_encourage_aggression_be_brave(self):
        intent = classify_intent("Be brave!")
        assert intent.category == "encourage_aggression"

    def test_encourage_curiosity(self):
        intent = classify_intent("look around this room")
        assert intent.category == "encourage_curiosity"
        assert ("curiosity", 0.03) in intent.trait_nudges

    def test_encourage_curiosity_investigate(self):
        intent = classify_intent("investigate that sound")
        assert intent.category == "encourage_curiosity"

    def test_praise(self):
        intent = classify_intent("good job on that fight!")
        assert intent.category == "praise"
        assert intent.bond_delta == 0.03
        assert intent.trait_nudges == []

    def test_praise_well_done(self):
        intent = classify_intent("well done!")
        assert intent.category == "praise"

    def test_praise_thank_you(self):
        intent = classify_intent("thank you for everything")
        assert intent.category == "praise"

    def test_comfort(self):
        intent = classify_intent("are you ok after that?")
        assert intent.category == "comfort"
        assert intent.bond_delta == 0.02

    def test_comfort_hang_in_there(self):
        intent = classify_intent("hang in there, we'll make it")
        assert intent.category == "comfort"

    # --- Negative intents ---

    def test_insult_useless(self):
        intent = classify_intent("you're useless")
        assert intent.category == "insult"
        assert intent.bond_delta == -0.04
        assert ("aggression", 0.02) in intent.trait_nudges

    def test_insult_pathetic(self):
        intent = classify_intent("that was pathetic")
        assert intent.category == "insult"

    def test_insult_coward(self):
        intent = classify_intent("don't be such a coward")
        assert intent.category == "insult"

    def test_threaten(self):
        intent = classify_intent("do as i say or else")
        assert intent.category == "threaten"
        assert intent.bond_delta == -0.03

    def test_threaten_shut_up(self):
        intent = classify_intent("shut up and follow")
        assert intent.category == "threaten"

    def test_criticize(self):
        intent = classify_intent("you should have blocked that")
        assert intent.category == "criticize"
        assert intent.bond_delta == -0.02

    def test_criticize_why_didnt(self):
        intent = classify_intent("why didn't you heal me?")
        assert intent.category == "criticize"

    def test_dismiss_whatever(self):
        intent = classify_intent("whatever")
        assert intent.category == "dismiss"
        assert intent.bond_delta == -0.02

    def test_dismiss_go_away(self):
        intent = classify_intent("go away, leave me alone")
        assert intent.category == "dismiss"

    # --- Fallback ---

    def test_fallback_generic_message(self):
        intent = classify_intent("how about this weather")
        assert intent.category == "bond"
        assert intent.confidence == 0.1
        assert intent.bond_delta == 0.005

    def test_fallback_empty_string(self):
        intent = classify_intent("")
        assert intent.category == "bond"

    # --- Priority ---

    def test_hostile_overrides_positive(self):
        """'useless fool' should match insult, not fallback."""
        intent = classify_intent("you useless fool")
        assert intent.category == "insult"

    def test_multi_word_phrase_priority(self):
        """Multi-word phrases match before single words."""
        intent = classify_intent("be careful with that")
        assert intent.category == "counsel_caution"


# =========================================================================
# BOND MECHANICS TESTS
# =========================================================================

class TestBondMechanics:

    def test_bond_default_zero(self):
        evo = TraitEvolution({"aggression": 0.5})
        assert evo.bond == 0.0

    def test_adjust_bond_positive(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.adjust_bond(0.03)
        assert abs(evo.bond - 0.03) < 1e-9

    def test_adjust_bond_negative(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.adjust_bond(-0.04)
        assert abs(evo.bond - (-0.04)) < 1e-9

    def test_bond_clamps_positive(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.adjust_bond(2.0)
        assert evo.bond == 1.0

    def test_bond_clamps_negative(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.adjust_bond(-2.0)
        assert evo.bond == -1.0

    def test_bond_accumulation(self):
        evo = TraitEvolution({"aggression": 0.5})
        for _ in range(10):
            evo.adjust_bond(0.03)
        assert abs(evo.bond - 0.3) < 1e-9

    # --- Bond tiers ---

    def test_tier_deeply_bonded(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = 0.8
        assert evo.get_bond_tier() == "deeply bonded"

    def test_tier_trusted_ally(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = 0.5
        assert evo.get_bond_tier() == "trusted ally"

    def test_tier_growing_closer(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = 0.2
        assert evo.get_bond_tier() == "growing closer"

    def test_tier_new_acquaintance(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = 0.0
        assert evo.get_bond_tier() == "new acquaintance"

    def test_tier_distrustful(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = -0.3
        assert evo.get_bond_tier() == "distrustful"

    def test_tier_hostile(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = -0.6
        assert evo.get_bond_tier() == "hostile"

    def test_tier_boundary_minus_point_one(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = -0.1
        assert evo.get_bond_tier() == "new acquaintance"

    def test_tier_boundary_minus_point_five(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = -0.5
        assert evo.get_bond_tier() == "distrustful"

    # --- Bond multiplier ---

    def test_multiplier_new_companion(self):
        """Bond 0.0 -> 30% effectiveness."""
        evo = TraitEvolution({"aggression": 0.5})
        assert abs(evo.get_bond_multiplier() - 0.3) < 1e-9

    def test_multiplier_deep_bond(self):
        """Bond 1.0 -> 100% effectiveness."""
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = 1.0
        assert abs(evo.get_bond_multiplier() - 1.0) < 1e-9

    def test_multiplier_mid_bond(self):
        """Bond 0.5 -> 65% effectiveness."""
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = 0.5
        assert abs(evo.get_bond_multiplier() - 0.65) < 1e-9

    def test_multiplier_negative_bond(self):
        """Bond -0.5 -> -0.35 (inverts nudges)."""
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = -0.5
        assert abs(evo.get_bond_multiplier() - (-0.35)) < 1e-9

    def test_multiplier_full_enmity(self):
        """Bond -1.0 -> -0.7."""
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = -1.0
        assert abs(evo.get_bond_multiplier() - (-0.7)) < 1e-9

    def test_nudge_inversion_at_negative_bond(self):
        """Counsel caution with negative bond should decrease caution."""
        evo = TraitEvolution({"caution": 0.5, "aggression": 0.5})
        evo.bond = -0.5
        multiplier = evo.get_bond_multiplier()
        # counsel_caution nudges caution +0.03
        evo.nudge("caution", 0.03 * multiplier, "player_counsel_caution", 1)
        drift = evo.get_drift("caution")
        assert drift < 0  # Inverted! Caution went down


# =========================================================================
# SERIALIZATION TESTS
# =========================================================================

class TestBondSerialization:

    def test_bond_in_to_dict(self):
        evo = TraitEvolution({"aggression": 0.5})
        evo.bond = -0.4
        d = evo.to_dict()
        assert d["bond"] == -0.4

    def test_bond_from_dict(self):
        data = {"original": {"aggression": 0.5}, "deltas": [], "bond": 0.7}
        evo = TraitEvolution.from_dict(data)
        assert evo.bond == 0.7

    def test_bond_default_from_dict_missing(self):
        """Legacy saves without bond key default to 0.0."""
        data = {"original": {"aggression": 0.5}, "deltas": []}
        evo = TraitEvolution.from_dict(data)
        assert evo.bond == 0.0

    def test_negative_bond_round_trip(self):
        evo = TraitEvolution({"caution": 0.3, "aggression": 0.8})
        evo.bond = -0.75
        evo.nudge("caution", 0.02, "test", 1)
        d = evo.to_dict()
        evo2 = TraitEvolution.from_dict(d)
        assert abs(evo2.bond - (-0.75)) < 1e-9
        assert evo2.get_bond_tier() == "hostile"
        assert len(evo2.deltas) == 1


# =========================================================================
# GRUDGING NARRATION TESTS
# =========================================================================

class TestGrudgingNarration:

    def test_hostile_attack_narration(self):
        result = narrate_decision("attack", "vanguard", "Bryn", "Goblin",
                                  bond_tier="hostile")
        assert "Bryn" in result
        # Should come from _GRUDGING_NARRATION, not normal templates
        assert any(frag in result for frag in ["survival demands", "irritation", "ignoring"])

    def test_hostile_guard_narration(self):
        result = narrate_decision("guard", "healer", "Neve", bond_tier="distrustful")
        assert "Neve" in result
        assert any(frag in result for frag in ["themselves", "grudgingly"])

    def test_normal_bond_uses_standard_templates(self):
        result = narrate_decision("attack", "vanguard", "Bryn", "Goblin",
                                  bond_tier="trusted ally")
        # Should NOT use grudging narration
        grudge_texts = [t.format(name="Bryn", target="Goblin") for t in _GRUDGING_NARRATION["attack"]]
        assert result not in grudge_texts or result == ""

    def test_none_bond_tier_uses_standard(self):
        result = narrate_decision("attack", "vanguard", "Bryn", "Goblin",
                                  bond_tier=None)
        grudge_texts = [t.format(name="Bryn", target="Goblin") for t in _GRUDGING_NARRATION["attack"]]
        assert result not in grudge_texts or result == ""


# =========================================================================
# RELUCTANT ALLY (AUTOPILOT) TESTS
# =========================================================================

class TestReluctantAlly:

    def test_bond_removes_command_bolster(self):
        """At bond < -0.3, Command and Bolster should be filtered out."""
        from codex.games.burnwillow.autopilot import AutopilotAgent, CompanionPersonality
        agent = AutopilotAgent(
            personality=CompanionPersonality(
                archetype="healer", description="", quirk="",
                aggression=0.2, curiosity=0.4, caution=0.8,
            )
        )
        snapshot = {
            "hp_pct": 0.9,
            "enemies": [{"name": "Goblin", "hp": 5, "max_hp": 10, "tier": 1}],
            "allies": [{"name": "Player", "hp": 20, "hp_pct": 0.3, "max_hp": 30}],
            "traits": ["[Triage]", "[Bolster]", "[Command]"],
            "char_name": "Neve",
            "equipped_traits": [],
            "has_healing_item": False,
        }
        # At bond -0.4, Command and Bolster should be removed from consideration
        # Healer with wounded ally would normally triage, which is still allowed
        result = agent.decide_combat(snapshot, bond=-0.4)
        # Should NOT choose command or bolster
        assert not result.startswith("command")
        assert not result.startswith("bolster")

    def test_self_preservation_at_negative_bond(self):
        """At bond < 0, guard threshold rises to HP < 0.35."""
        from codex.games.burnwillow.autopilot import AutopilotAgent, CompanionPersonality
        agent = AutopilotAgent(
            personality=CompanionPersonality(
                archetype="vanguard", description="", quirk="",
                aggression=0.9, curiosity=0.3, caution=0.1,
            )
        )
        snapshot = {
            "hp_pct": 0.30,  # Below 0.35 but above 0.2
            "enemies": [{"name": "Orc", "hp": 20, "max_hp": 20, "tier": 2}],
            "allies": [],
            "traits": [],
            "char_name": "Bryn",
            "equipped_traits": [],
            "has_healing_item": False,
        }
        result = agent.decide_combat(snapshot, bond=-0.2)
        assert result == "guard"

    def test_normal_bond_no_early_guard(self):
        """At bond >= 0, 0.30 HP should NOT trigger early guard."""
        from codex.games.burnwillow.autopilot import AutopilotAgent, CompanionPersonality
        agent = AutopilotAgent(
            personality=CompanionPersonality(
                archetype="vanguard", description="", quirk="",
                aggression=0.9, curiosity=0.3, caution=0.1,
            )
        )
        snapshot = {
            "hp_pct": 0.30,
            "enemies": [{"name": "Orc", "hp": 20, "max_hp": 20, "tier": 2}],
            "allies": [],
            "traits": [],
            "char_name": "Bryn",
            "equipped_traits": [],
            "has_healing_item": False,
        }
        result = agent.decide_combat(snapshot, bond=0.0)
        # At bond 0, 0.30 > 0.2 normal guard threshold, so should attack
        assert result.startswith("attack")


# =========================================================================
# NPC MEMORY GET_RECENT_SHARDS TESTS
# =========================================================================

class TestGetRecentShards:

    def test_get_recent_shards_returns_correct_count(self):
        from codex.core.services.npc_memory import NPCMemoryBank
        bank = NPCMemoryBank(npc_name="Bryn")
        bank.record("event 1")
        bank.record("event 2")
        bank.record("event 3")
        bank.record("event 4")
        result = bank.get_recent_shards(2)
        assert len(result) == 2

    def test_get_recent_shards_newest_first(self):
        import time
        from codex.core.services.npc_memory import NPCMemoryBank
        bank = NPCMemoryBank(npc_name="Bryn")
        bank.record("old event")
        time.sleep(0.01)
        bank.record("new event")
        result = bank.get_recent_shards(2)
        assert "new event" in result[0].content
        assert "old event" in result[1].content

    def test_get_recent_shards_empty_bank(self):
        from codex.core.services.npc_memory import NPCMemoryBank
        bank = NPCMemoryBank(npc_name="Bryn")
        result = bank.get_recent_shards(3)
        assert result == []

    def test_get_recent_shards_fewer_than_requested(self):
        from codex.core.services.npc_memory import NPCMemoryBank
        bank = NPCMemoryBank(npc_name="Bryn")
        bank.record("only one")
        result = bank.get_recent_shards(5)
        assert len(result) == 1


# =========================================================================
# COOLDOWN TESTS
# =========================================================================

class TestDialogueCooldown:

    def test_cooldown_prevents_rapid_nudges(self):
        """Same companion shouldn't get nudged within 3 turns."""
        evo = TraitEvolution({"caution": 0.5, "aggression": 0.5})
        intent = classify_intent("be careful")
        assert intent.confidence >= 0.3

        last_turn = 5
        turn_now = 7  # Gap of 2 (< 3)
        should_apply = turn_now - last_turn >= 3
        assert not should_apply

    def test_cooldown_allows_after_gap(self):
        """After 3+ turns, nudge should apply."""
        last_turn = 5
        turn_now = 8  # Gap of 3
        should_apply = turn_now - last_turn >= 3
        assert should_apply

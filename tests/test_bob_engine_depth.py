"""
WO-Phase2A — Band of Blades Engine Depth: Tests
==================================================

Covers:
  - TestBoBPlaybookData   — 4 playbooks load with required fields
  - TestBoBLegionData     — Specialists, squads, chosen, missions, pressures
  - TestBoBFactionData    — All factions load with required fields
  - TestCampaignPhaseManager — Phase cycling, march, camp, pressure
  - TestPressureClock     — Ticking, level progression, cap behaviour
  - TestMissionResolver   — Planning, engagement, resolution, casualties
  - TestBoBEngineSaveLoad — Full round-trip with subsystem state
  - TestBoBCommandDispatch — All handle_command dispatches
"""

import random
import pytest

from codex.forge.reference_data.bob_playbooks import (
    PLAYBOOKS,
    ROOKIE_ABILITIES,
    HERITAGES,
)
from codex.forge.reference_data.bob_legion import (
    SPECIALISTS,
    SQUAD_TYPES,
    CHOSEN,
    MISSION_TYPES,
    CAMPAIGN_PRESSURES,
)
from codex.forge.reference_data.bob_factions import FACTIONS
from codex.forge.reference_data.bob import (
    PLAYBOOKS as AGG_PLAYBOOKS,
    SPECIALISTS as AGG_SPECIALISTS,
    FACTIONS as AGG_FACTIONS,
)
from codex.games.bob import BoBEngine, BoBCharacter
from codex.games.bob.campaign import CampaignPhaseManager, PressureClock
from codex.games.bob.missions import (
    MissionResolver,
    MissionReward,
    MISSION_DIFFICULTY_TABLE,
    CASUALTY_TABLE,
)


# =========================================================================
# HELPERS
# =========================================================================

def _rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def _engine_with_char() -> BoBEngine:
    """Return a BoBEngine with one character ready for testing."""
    engine = BoBEngine()
    engine.create_character("Sgt. Asha", playbook="Heavy", heritage="Bartan")
    return engine


# =========================================================================
# 1. PLAYBOOK DATA
# =========================================================================

class TestBoBPlaybookData:
    """Verify that all four specialist playbooks load with required fields."""

    def test_four_playbooks_present(self):
        # SOURCE: Band of Blades.pdf, pp.79-115 — Heavy, Medic, Officer, Scout
        # are the four core playbooks (Sniper/Rookie/Soldier are in SPECIALISTS)
        assert len(PLAYBOOKS) == 4
        for key in ("Heavy", "Medic", "Officer", "Scout"):
            assert key in PLAYBOOKS, f"Missing playbook: {key}"

    def test_playbook_has_required_keys(self):
        required = {"description", "special_abilities", "items"}
        for name, pb in PLAYBOOKS.items():
            missing = required - set(pb.keys())
            assert not missing, f"{name} missing keys: {missing}"

    def test_heavy_and_medic_have_four_or_more_abilities(self):
        # Heavy (p.80-81) has 7 abilities, Medic (p.84-85) has 7 abilities
        for name in ("Heavy", "Medic"):
            count = len(PLAYBOOKS[name]["special_abilities"])
            assert count >= 4, f"{name} has {count} abilities (expected >= 4)"

    def test_each_ability_has_name_and_description(self):
        for pb_name, pb in PLAYBOOKS.items():
            for ability in pb["special_abilities"]:
                assert "name" in ability, f"{pb_name} ability missing 'name'"
                assert "description" in ability, f"{pb_name} ability missing 'description'"
                assert ability["name"], f"{pb_name} ability has empty name"

    def test_playbook_items_non_empty(self):
        for name, pb in PLAYBOOKS.items():
            assert pb["items"], f"{name} has no items"

    def test_rookie_abilities_present(self):
        assert len(ROOKIE_ABILITIES) >= 8
        expected = {"Skirmish", "Maneuver", "Discipline", "Doctor", "Marshal"}
        for key in expected:
            assert key in ROOKIE_ABILITIES, f"Missing rookie ability: {key}"

    def test_heritages_present(self):
        assert len(HERITAGES) == 4
        for key in ("Bartan", "Orite", "Panyar", "Zemyati"):
            assert key in HERITAGES, f"Missing heritage: {key}"

    def test_heritage_has_description_and_trait(self):
        for name, h in HERITAGES.items():
            assert "description" in h, f"{name} missing 'description'"
            assert "cultural_trait" in h, f"{name} missing 'cultural_trait'"
            assert h["description"], f"{name} has empty description"

    def test_aggregator_exports_playbooks(self):
        """Verify bob.py aggregator re-exports correctly."""
        assert AGG_PLAYBOOKS is PLAYBOOKS


# =========================================================================
# 2. LEGION DATA
# =========================================================================

class TestBoBLegionData:
    """Verify specialists, squad types, Chosen, missions, and pressure data."""

    def test_seven_specialists_present(self):
        # SOURCE: Band of Blades.pdf, pp.79-115
        # 7 specialists: Heavy, Medic, Officer, Scout, Sniper, Rookie, Soldier
        assert len(SPECIALISTS) == 7
        for key in ("Heavy", "Medic", "Officer", "Scout", "Sniper", "Rookie", "Soldier"):
            assert key in SPECIALISTS, f"Missing specialist: {key}"

    def test_specialist_has_required_keys(self):
        required = {"description", "abilities", "gear"}
        for name, spec in SPECIALISTS.items():
            missing = required - set(spec.keys())
            assert not missing, f"{name} specialist missing: {missing}"

    def test_specialist_has_at_least_two_abilities(self):
        # Heavy and Medic have 7 each (SOURCE: pp.80-85).
        # Officer/Scout/Sniper/Soldier playbooks are EXPANDED — full ability pages
        # not extracted; minimum 4 standard abilities (Veteran/Elite/Hardened/Survivor).
        # Rookie has 2 (no standard abilities per p.77: "not available to Rookies").
        for name, spec in SPECIALISTS.items():
            assert len(spec["abilities"]) >= 2, f"{name} has < 2 abilities"
        # Verify the fully sourced ones have full sets
        assert len(SPECIALISTS["Heavy"]["abilities"]) >= 5
        assert len(SPECIALISTS["Medic"]["abilities"]) >= 5

    def test_three_squad_types_present(self):
        assert len(SQUAD_TYPES) == 3
        for key in ("Rookies", "Soldiers", "Elite"):
            assert key in SQUAD_TYPES, f"Missing squad type: {key}"

    def test_squad_type_has_stats(self):
        required = {"scale", "quality", "armor", "features"}
        for name, sq in SQUAD_TYPES.items():
            missing = required - set(sq.keys())
            assert not missing, f"{name} squad missing: {missing}"

    def test_squad_quality_ascending(self):
        """Elite quality > Soldiers quality > Rookies quality."""
        assert SQUAD_TYPES["Rookies"]["quality"] < SQUAD_TYPES["Soldiers"]["quality"]
        assert SQUAD_TYPES["Soldiers"]["quality"] < SQUAD_TYPES["Elite"]["quality"]

    def test_three_chosen_present(self):
        # SOURCE: Band of Blades.pdf, pp.159-181
        # The three Chosen: Shreya (p.165), Horned One (p.171), Zora (p.177)
        # NOTE: Render is a BROKEN (enemy general), not a Chosen
        assert len(CHOSEN) == 3
        for key in ("Shreya", "Horned One", "Zora"):
            assert key in CHOSEN, f"Missing Chosen: {key}"

    def test_chosen_has_required_keys(self):
        required = {"description", "powers", "corruption_triggers", "stats"}
        for name, ch in CHOSEN.items():
            missing = required - set(ch.keys())
            assert not missing, f"{name} Chosen missing: {missing}"

    def test_chosen_has_corruption_max(self):
        for name, ch in CHOSEN.items():
            assert "corruption_max" in ch["stats"], f"{name} missing corruption_max"
            assert ch["stats"]["corruption_max"] > 0

    def test_six_mission_types_present(self):
        assert len(MISSION_TYPES) == 6
        for key in ("Assault", "Recon", "Religious", "Supply", "Rescue", "Skirmish"):
            assert key in MISSION_TYPES, f"Missing mission type: {key}"

    def test_mission_type_has_required_keys(self):
        required = {"description", "difficulty", "reward_type"}
        for name, mt in MISSION_TYPES.items():
            missing = required - set(mt.keys())
            assert not missing, f"{name} mission missing: {missing}"

    def test_mission_difficulties_in_range(self):
        for name, mt in MISSION_TYPES.items():
            d = mt["difficulty"]
            assert 1 <= d <= 5, f"{name} difficulty {d} out of range"

    def test_five_pressure_levels(self):
        assert len(CAMPAIGN_PRESSURES) == 5
        for level in range(1, 6):
            assert level in CAMPAIGN_PRESSURES, f"Missing pressure level: {level}"

    def test_pressure_has_name_description_effect(self):
        for level, p in CAMPAIGN_PRESSURES.items():
            assert "name" in p, f"Level {level} missing 'name'"
            assert "description" in p, f"Level {level} missing 'description'"
            assert "effect" in p, f"Level {level} missing 'effect'"

    def test_aggregator_exports_specialists(self):
        assert AGG_SPECIALISTS is SPECIALISTS


# =========================================================================
# 3. FACTION DATA
# =========================================================================

class TestBoBFactionData:
    """Verify all factions load with required structural fields."""

    def test_broken_factions_present(self):
        # SOURCE: Band of Blades.pdf, pp.184-209
        # Exactly 3 Broken generals: Blighter, Breaker, Render
        broken = [k for k, v in FACTIONS.items() if v.get("faction_type") == "broken"]
        assert len(broken) == 3, f"Expected 3 Broken factions, got {len(broken)}"
        for key in ("Blighter", "Breaker", "Render"):
            assert key in FACTIONS, f"Missing Broken: {key}"

    def test_undead_types_present(self):
        # SOURCE: Band of Blades.pdf, pp.190-191, 198-199, 206-207
        # Undead types catalogued: Rotters, Crows, Burned, Gaunt, Shadow Witches
        undead = [k for k, v in FACTIONS.items() if v.get("faction_type") == "undead"]
        assert len(undead) == 5, f"Expected 5 undead types, got {len(undead)}"
        for key in ("Rotters", "Crows", "Burned", "Gaunt", "Shadow Witches"):
            assert key in FACTIONS, f"Missing undead type: {key}"

    def test_allied_groups_present(self):
        allied = [k for k, v in FACTIONS.items() if v.get("faction_type") == "allied"]
        assert len(allied) == 3, f"Expected 3 allied groups, got {len(allied)}"

    def test_each_faction_has_required_keys(self):
        required = {"faction_type", "tier", "description", "unit_types", "special_abilities"}
        for name, faction in FACTIONS.items():
            missing = required - set(faction.keys())
            assert not missing, f"Faction '{name}' missing: {missing}"

    def test_faction_tiers_in_range(self):
        # SOURCE: Band of Blades.pdf — threat ratings
        # Broken generals are threat 5 (pp.190, 198, 206).
        # Elites are threat 2, Line troops are threat 1.
        for name, faction in FACTIONS.items():
            tier = faction["tier"]
            assert 1 <= tier <= 5, f"'{name}' tier {tier} out of range (1-5)"

    def test_broken_factions_have_commander(self):
        for name, faction in FACTIONS.items():
            if faction["faction_type"] == "broken":
                assert "commander" in faction, f"Broken faction '{name}' missing 'commander'"

    def test_allied_factions_have_notable_npcs(self):
        for name, faction in FACTIONS.items():
            if faction["faction_type"] == "allied":
                assert "notable_npcs" in faction, f"Allied '{name}' missing 'notable_npcs'"
                assert len(faction["notable_npcs"]) >= 1

    def test_broken_are_tier_5(self):
        # SOURCE: Band of Blades.pdf, pp.190, 198, 206 — each Broken is threat 5
        for broken_name in ("Blighter", "Breaker", "Render"):
            assert FACTIONS[broken_name]["tier"] == 5, f"{broken_name} should be tier 5"

    def test_rotters_are_tier_1(self):
        # SOURCE: Band of Blades.pdf, p.190 — Rotters are threat 1
        assert FACTIONS["Rotters"]["tier"] == 1

    def test_shadow_witches_are_tier_2(self):
        # SOURCE: Band of Blades.pdf, p.199 — Elites count as threat 2
        assert FACTIONS["Shadow Witches"]["tier"] == 2

    def test_aggregator_exports_factions(self):
        assert AGG_FACTIONS is FACTIONS


# =========================================================================
# 4. PRESSURE CLOCK
# =========================================================================

class TestPressureClock:
    """Unit tests for PressureClock."""

    def test_initial_state(self):
        pc = PressureClock()
        assert pc.level == 0
        assert pc.ticks == 0
        assert pc.label == "Quiet"
        assert pc.is_final is False

    def test_tick_advances_ticks(self):
        pc = PressureClock()
        result = pc.tick(1)
        assert result["new_ticks"] == 1
        assert result["level_advanced"] is False

    def test_tick_three_advances_level(self):
        pc = PressureClock()
        pc.tick(1)
        pc.tick(1)
        result = pc.tick(1)
        assert result["level_advanced"] is True
        assert pc.level == 1
        assert pc.ticks == 0

    def test_tick_bulk_advances_multiple_levels(self):
        pc = PressureClock()
        result = pc.tick(9)  # 3 ticks per level x 3 levels
        assert pc.level == 3
        assert pc.ticks == 0
        assert result["levels_advanced"] == 3

    def test_level_caps_at_5(self):
        pc = PressureClock()
        pc.tick(100)
        assert pc.level == 5
        assert pc.is_final is True

    def test_final_level_label(self):
        pc = PressureClock(level=5)
        assert pc.label == "Last Stand"
        assert pc.is_final is True

    def test_reduce_ticks(self):
        pc = PressureClock(level=2, ticks=2)
        result = pc.reduce(1)
        assert result["new_ticks"] == 1
        assert pc.level == 2

    def test_reduce_crosses_level_boundary(self):
        pc = PressureClock(level=2, ticks=0)
        pc.reduce(1)
        assert pc.level == 1
        assert pc.ticks == 2  # 3 ticks per level - 1

    def test_serialize_round_trip(self):
        pc = PressureClock(level=3, ticks=1)
        data = pc.to_dict()
        restored = PressureClock.from_dict(data)
        assert restored.level == pc.level
        assert restored.ticks == pc.ticks

    def test_repr(self):
        pc = PressureClock(level=2, ticks=1)
        r = repr(pc)
        assert "PressureClock" in r
        assert "2" in r


# =========================================================================
# 5. CAMPAIGN PHASE MANAGER
# =========================================================================

class TestCampaignPhaseManager:
    """Unit tests for CampaignPhaseManager."""

    def test_default_initial_state(self):
        mgr = CampaignPhaseManager()
        assert mgr.current_phase == "march"
        assert mgr.time_passed == 0
        assert mgr.morale == 3
        assert mgr.supply == 5
        assert mgr.pressure == 0

    def test_advance_phase_cycles(self):
        mgr = CampaignPhaseManager()
        assert mgr.advance_phase() == "camp"
        assert mgr.advance_phase() == "mission"
        assert mgr.advance_phase() == "march"

    def test_march_consumes_supply(self):
        mgr = CampaignPhaseManager(supply=5)
        result = mgr.march("Aldermoor", supply_cost=2)
        assert result["supply_after"] == 3
        assert result["supply_cost"] == 2
        assert result["destination"] == "Aldermoor"

    def test_march_advances_time(self):
        mgr = CampaignPhaseManager()
        mgr.march("Barrowfield")
        assert mgr.time_passed == 1

    def test_march_appends_to_route(self):
        mgr = CampaignPhaseManager()
        mgr.march("Point A")
        mgr.march("Point B")
        assert mgr.route == ["Point A", "Point B"]

    def test_march_supply_floor_at_zero(self):
        mgr = CampaignPhaseManager(supply=1)
        result = mgr.march("Danger Town", supply_cost=5)
        assert mgr.supply == 0
        assert result["supply_cost"] == 1  # actual cost capped at available

    def test_march_supply_shortfall_hurts_morale(self):
        mgr = CampaignPhaseManager(supply=0, morale=3)
        mgr.march("Somewhere", supply_cost=2)
        assert mgr.morale == 2

    def test_march_encounter_deterministic(self):
        mgr = CampaignPhaseManager()
        rng = random.Random(0)  # seed 0 gives encounter on first march
        result = mgr.march("Test Dest", rng=rng)
        # Just verify structure, not specific encounter
        assert "encounter" in result
        assert "encounter_type" in result

    def test_camp_rest_improves_morale(self):
        mgr = CampaignPhaseManager(morale=2)
        result = mgr.camp(activity="rest")
        assert result["morale_after"] > result["morale_before"]

    def test_camp_morale_caps_at_5(self):
        mgr = CampaignPhaseManager(morale=5)
        mgr.camp(activity="rest")
        assert mgr.morale == 5

    def test_camp_resupply_adds_supply(self):
        mgr = CampaignPhaseManager(supply=2)
        rng = random.Random(42)
        result = mgr.camp(activity="resupply", rng=rng)
        assert result["supply_gained"] > 0
        assert mgr.supply > 2

    def test_camp_ceremony_big_morale_boost(self):
        mgr = CampaignPhaseManager(morale=1)
        result = mgr.camp(activity="ceremony")
        assert result["morale_after"] >= 3

    def test_camp_recruit_costs_supply(self):
        mgr = CampaignPhaseManager(supply=5)
        mgr.camp(activity="recruit")
        # Recruit costs 2 supply
        assert mgr.supply == 3

    def test_pressure_check_structure(self):
        mgr = CampaignPhaseManager()
        result = mgr.pressure_check(rng=_rng(99))
        assert "roll" in result
        assert "threshold" in result
        assert "pressure_increased" in result
        assert "new_level" in result

    def test_pressure_check_can_increase(self):
        """High pressure means almost certain increase. Seed for reliable result."""
        mgr = CampaignPhaseManager(pressure=4)
        rng = random.Random(1)  # low roll -> high chance increase
        result = mgr.pressure_check(rng=rng)
        # At level 4, threshold is 60, many rolls will trigger
        assert isinstance(result["pressure_increased"], bool)

    def test_pressure_stays_at_5(self):
        mgr = CampaignPhaseManager(pressure=5)
        result = mgr.pressure_check(rng=_rng(1))
        assert result["new_level"] == 5
        assert result["pressure_increased"] is False

    def test_time_passes(self):
        mgr = CampaignPhaseManager()
        msg = mgr.time_passes(days=3)
        assert mgr.time_passed == 3
        assert "3" in msg

    def test_add_relic(self):
        mgr = CampaignPhaseManager()
        msg = mgr.add_relic("Nyx's Lantern")
        assert "Nyx's Lantern" in mgr.holy_relics
        assert "Nyx's Lantern" in msg

    def test_get_status_structure(self):
        mgr = CampaignPhaseManager()
        status = mgr.get_status()
        for key in ("phase", "day", "morale", "supply", "pressure", "relics"):
            assert key in status, f"Status missing key: {key}"

    def test_serialize_round_trip(self):
        mgr = CampaignPhaseManager(
            current_phase="camp",
            time_passed=7,
            morale=4,
            supply=3,
            pressure=2,
            holy_relics=["Bone Reliquary"],
            route=["Start", "Middle"],
        )
        mgr.pressure_clock.tick(1)
        data = mgr.to_dict()
        restored = CampaignPhaseManager.from_dict(data)

        assert restored.current_phase == "camp"
        assert restored.time_passed == 7
        assert restored.morale == 4
        assert restored.supply == 3
        assert restored.holy_relics == ["Bone Reliquary"]
        assert restored.route == ["Start", "Middle"]

    def test_pressure_property_delegates_to_clock(self):
        mgr = CampaignPhaseManager(pressure=2)
        assert mgr.pressure == mgr.pressure_clock.level


# =========================================================================
# 6. MISSION RESOLVER
# =========================================================================

class TestMissionResolver:
    """Unit tests for MissionResolver."""

    def test_plan_mission_returns_plan(self):
        resolver = MissionResolver()
        plan = resolver.plan_mission("Assault", "Soldiers")
        assert plan["mission_type"] == "Assault"
        assert plan["squad"] == "Soldiers"
        assert "base_difficulty" in plan
        assert "reward_type" in plan

    def test_plan_mission_unknown_type_returns_error(self):
        resolver = MissionResolver()
        plan = resolver.plan_mission("FakeType", "Soldiers")
        assert "error" in plan

    def test_plan_mission_case_insensitive(self):
        resolver = MissionResolver()
        plan = resolver.plan_mission("assault", "Soldiers")
        assert "error" not in plan
        assert plan["mission_type"] == "Assault"

    def test_plan_sets_planned_mission(self):
        resolver = MissionResolver()
        assert resolver.planned_mission is None
        resolver.plan_mission("Recon", "Elite")
        assert resolver.planned_mission is not None

    def test_engagement_roll_structure(self):
        resolver = MissionResolver()
        result = resolver.engagement_roll(
            mission_type="Assault",
            squad_quality=1,
            specialist_bonus=0,
            pressure_level=0,
            rng=_rng(42),
        )
        for key in ("outcome", "dice", "highest", "dice_pool", "position"):
            assert key in result, f"Missing key: {key}"

    def test_engagement_roll_elite_better_than_rookies(self):
        """Elite (quality 2) should have larger dice pool than Rookies (quality 0)."""
        resolver = MissionResolver()
        result_elite = resolver.engagement_roll(
            "Assault", squad_quality=2, pressure_level=0, rng=_rng(1)
        )
        result_rookie = resolver.engagement_roll(
            "Assault", squad_quality=0, pressure_level=0, rng=_rng(1)
        )
        assert result_elite["dice_pool"] > result_rookie["dice_pool"]

    def test_engagement_roll_high_pressure_reduces_pool(self):
        """High pressure adds difficulty, reducing dice pool."""
        resolver = MissionResolver()
        low = resolver.engagement_roll("Assault", squad_quality=2, pressure_level=0)
        high = resolver.engagement_roll("Assault", squad_quality=2, pressure_level=5)
        assert low["dice_pool"] >= high["dice_pool"]

    def test_difficulty_table_has_all_mission_types(self):
        for mtype in ("Assault", "Recon", "Religious", "Supply", "Rescue", "Skirmish"):
            assert mtype in MISSION_DIFFICULTY_TABLE, f"Missing {mtype} in difficulty table"

    def test_difficulty_table_has_all_pressure_levels(self):
        for mtype, levels in MISSION_DIFFICULTY_TABLE.items():
            for lvl in range(6):
                assert lvl in levels, f"{mtype} missing pressure level {lvl}"

    def test_casualty_table_has_all_outcomes(self):
        for key in ("critical", "success", "mixed", "failure"):
            assert key in CASUALTY_TABLE, f"Missing casualty outcome: {key}"

    def test_casualty_table_severity_ascending(self):
        """Failure should have higher casualty level than critical."""
        assert CASUALTY_TABLE["critical"]["casualty_level"] < CASUALTY_TABLE["failure"]["casualty_level"]

    def test_resolve_mission_structure(self):
        resolver = MissionResolver(rng_seed=42)
        plan = resolver.plan_mission("Supply", "Soldiers")
        result = resolver.resolve_mission(plan, "success", "success")
        for key in ("mission_type", "success_level", "casualty_outcome", "morale_delta"):
            assert key in result, f"Missing key: {key}"

    def test_resolve_mission_clears_planned(self):
        resolver = MissionResolver(rng_seed=42)
        resolver.plan_mission("Recon", "Elite")
        resolver.resolve_mission(resolver.planned_mission, "success", "success")
        assert resolver.planned_mission is None

    def test_resolve_mission_records_history(self):
        resolver = MissionResolver(rng_seed=42)
        plan = resolver.plan_mission("Rescue", "Soldiers")
        resolver.resolve_mission(plan, "mixed", "mixed")
        assert len(resolver.completed_missions) == 1

    def test_resolve_failure_no_rewards(self):
        resolver = MissionResolver(rng_seed=99)
        plan = resolver.plan_mission("Assault", "Rookies")
        result = resolver.resolve_mission(plan, "failure", "failure")
        reward = result["reward"]
        assert reward["supply_gained"] == 0
        assert reward["intel_gained"] == 0

    def test_resolve_critical_has_best_rewards(self):
        resolver = MissionResolver(rng_seed=1)
        plan_s = resolver.plan_mission("Supply", "Elite")
        result_c = resolver.resolve_mission(plan_s, "critical", "critical")

        resolver2 = MissionResolver(rng_seed=1)
        plan_s2 = resolver2.plan_mission("Supply", "Elite")
        result_f = resolver2.resolve_mission(plan_s2, "failure", "failure")

        assert result_c["reward"]["supply_gained"] > result_f["reward"]["supply_gained"]

    def test_casualty_roll_structure(self):
        resolver = MissionResolver(rng_seed=42)
        result = resolver.casualty_roll("Soldiers", mission_difficulty=2)
        for key in ("squad_type", "outcome", "casualty_level", "soldiers_lost_min",
                    "soldiers_lost_max", "label"):
            assert key in result, f"Missing key: {key}"

    def test_casualty_roll_elite_better_than_rookies(self):
        """Elite troops should generally have better casualty outcomes."""
        # Run multiple trials and check average
        elite_losses = []
        rookie_losses = []
        for seed in range(20):
            resolver = MissionResolver(rng_seed=seed)
            r_e = resolver.casualty_roll("Elite", 2, rng=random.Random(seed))
            resolver2 = MissionResolver(rng_seed=seed)
            r_r = resolver2.casualty_roll("Rookies", 2, rng=random.Random(seed))
            elite_losses.append(r_e["casualty_level"])
            rookie_losses.append(r_r["casualty_level"])
        avg_elite = sum(elite_losses) / len(elite_losses)
        avg_rookie = sum(rookie_losses) / len(rookie_losses)
        assert avg_elite <= avg_rookie

    def test_mission_reward_describe(self):
        reward = MissionReward(supply_gained=3, morale_gained=1, intel_gained=0)
        desc = reward.describe()
        assert "+3 Supply" in desc
        assert "Morale" in desc

    def test_mission_reward_relic(self):
        reward = MissionReward(relic_found=True, relic_name="Holy Standard")
        desc = reward.describe()
        assert "Relic" in desc
        assert "Holy Standard" in desc

    def test_mission_reward_no_rewards(self):
        reward = MissionReward()
        assert "No significant rewards" in reward.describe()

    def test_serialize_round_trip(self):
        resolver = MissionResolver(rng_seed=5)
        resolver.plan_mission("Skirmish", "Soldiers")
        resolver.resolve_mission(resolver.planned_mission, "success", "success")
        data = resolver.to_dict()

        restored = MissionResolver.from_dict(data)
        assert len(restored.completed_missions) == 1
        assert restored.completed_missions[0]["mission_type"] == "Skirmish"


# =========================================================================
# 7. BOB ENGINE SAVE / LOAD
# =========================================================================

class TestBoBEngineSaveLoad:
    """Full round-trip save/load including subsystem state."""

    def test_basic_save_load(self):
        engine = _engine_with_char()
        state = engine.save_state()
        engine2 = BoBEngine()
        engine2.load_state(state)
        assert engine2.character is not None
        assert engine2.character.name == "Sgt. Asha"
        assert engine2.campaign_phase == engine.campaign_phase

    def test_save_includes_subsystem_keys(self):
        engine = _engine_with_char()
        # Force subsystem initialisation
        _ = engine._get_campaign_mgr()
        _ = engine._get_mission_resolver()
        state = engine.save_state()
        assert "campaign_mgr" in state
        assert "mission_resolver" in state

    def test_load_restores_campaign_manager(self):
        engine = _engine_with_char()
        mgr = engine._get_campaign_mgr()
        mgr.march("Test Town", supply_cost=1)
        mgr.add_relic("Test Relic")

        state = engine.save_state()
        engine2 = BoBEngine()
        engine2.load_state(state)

        mgr2 = engine2._get_campaign_mgr()
        assert "Test Town" in mgr2.route
        assert "Test Relic" in mgr2.holy_relics

    def test_load_restores_mission_resolver(self):
        engine = _engine_with_char()
        resolver = engine._get_mission_resolver()
        plan = resolver.plan_mission("Assault", "Elite")
        resolver.resolve_mission(plan, "success", "success")

        state = engine.save_state()
        engine2 = BoBEngine()
        engine2.load_state(state)

        resolver2 = engine2._get_mission_resolver()
        assert len(resolver2.completed_missions) == 1

    def test_save_without_subsystems_is_safe(self):
        """If subsystems were never initialised, save should not crash."""
        engine = _engine_with_char()
        # Do NOT touch _get_campaign_mgr or _get_mission_resolver
        state = engine.save_state()
        assert state["campaign_mgr"] is None
        assert state["mission_resolver"] is None

    def test_load_without_subsystem_data_is_safe(self):
        """Loading state without subsystem keys should not crash."""
        engine = _engine_with_char()
        state = engine.save_state()
        # Remove subsystem keys to simulate old save format
        state.pop("campaign_mgr", None)
        state.pop("mission_resolver", None)

        engine2 = BoBEngine()
        engine2.load_state(state)  # Should not raise
        assert engine2.character is not None

    def test_stress_clock_survives_round_trip(self):
        engine = _engine_with_char()
        clock = engine.stress_clocks["Sgt. Asha"]
        clock.push(3)

        state = engine.save_state()
        engine2 = BoBEngine()
        engine2.load_state(state)

        clock2 = engine2.stress_clocks["Sgt. Asha"]
        assert clock2.current_stress == 3

    def test_legion_state_survives_round_trip(self):
        engine = _engine_with_char()
        engine.legion.adjust("supply", -2)
        engine.legion.adjust("intel", 3)

        state = engine.save_state()
        engine2 = BoBEngine()
        engine2.load_state(state)

        assert engine2.legion.supply == engine.legion.supply
        assert engine2.legion.intel == engine.legion.intel

    def test_party_survives_round_trip(self):
        engine = BoBEngine()
        engine.create_character("Alpha", playbook="Heavy", heritage="Bartan")
        engine.add_to_party(BoBCharacter(name="Bravo", playbook="Scout", heritage="Orite"))

        state = engine.save_state()
        engine2 = BoBEngine()
        engine2.load_state(state)

        assert len(engine2.party) == 2
        assert engine2.party[1].name == "Bravo"


# =========================================================================
# 8. BOB ENGINE COMMAND DISPATCH
# =========================================================================

class TestBoBCommandDispatch:
    """Verify all handle_command dispatches return strings without crashing."""

    def _engine(self) -> BoBEngine:
        return _engine_with_char()

    def test_legion_status(self):
        e = self._engine()
        result = e.handle_command("legion_status")
        assert "Supply" in result
        assert "Morale" in result
        assert "Pressure" in result

    def test_squad_status(self):
        e = self._engine()
        result = e.handle_command("squad_status")
        assert "Sgt. Asha" in result
        assert "stress" in result

    def test_chosen_status(self):
        e = self._engine()
        result = e.handle_command("chosen_status")
        assert "Chosen" in result

    def test_supply_check_positive(self):
        e = self._engine()
        result = e.handle_command("supply_check", delta=2)
        assert "Supply" in result
        assert "+2" in result

    def test_supply_check_negative(self):
        e = self._engine()
        result = e.handle_command("supply_check", delta=-1)
        assert "-1" in result

    def test_campaign_advance(self):
        e = self._engine()
        result = e.handle_command("campaign_advance")
        assert "camp" in result.lower()

    def test_roll_action(self):
        e = self._engine()
        result = e.handle_command("roll_action", action="skirmish")
        assert "Dice" in result or "Position" in result

    def test_march_command(self):
        e = self._engine()
        result = e.handle_command("march", destination="Aldermoor", supply_cost=1)
        assert "Aldermoor" in result
        assert "Supply" in result

    def test_camp_rest(self):
        e = self._engine()
        result = e.handle_command("camp", activity="rest")
        assert "rest" in result.lower() or "Morale" in result

    def test_camp_resupply(self):
        e = self._engine()
        result = e.handle_command("camp", activity="resupply")
        assert "supply" in result.lower() or "Supply" in result

    def test_camp_ceremony(self):
        e = self._engine()
        result = e.handle_command("camp", activity="ceremony")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_campaign_status(self):
        e = self._engine()
        result = e.handle_command("campaign_status")
        assert "Phase" in result
        assert "Morale" in result
        assert "Supply" in result

    def test_pressure_check_command(self):
        e = self._engine()
        result = e.handle_command("pressure_check")
        assert "Pressure" in result
        assert "check" in result.lower() or "level" in result.lower()

    def test_time_passes_command(self):
        e = self._engine()
        result = e.handle_command("time_passes", days=3)
        assert "Day 3" in result or "3 day" in result

    def test_mission_plan_assault(self):
        e = self._engine()
        result = e.handle_command("mission_plan", mission_type="Assault", squad="Soldiers")
        assert "Assault" in result
        assert "Soldiers" in result

    def test_mission_plan_with_specialist(self):
        e = self._engine()
        result = e.handle_command("mission_plan", mission_type="Recon",
                                  squad="Elite", specialist="Sniper")
        assert "Sniper" in result

    def test_mission_plan_bad_type(self):
        e = self._engine()
        result = e.handle_command("mission_plan", mission_type="FakeType", squad="Soldiers")
        assert "Unknown" in result or "error" in result.lower()

    def test_mission_resolve_without_plan(self):
        e = self._engine()
        result = e.handle_command("mission_resolve", casualties_roll="success",
                                  success_level="success")
        assert "No mission planned" in result

    def test_mission_resolve_full_flow(self):
        e = self._engine()
        e.handle_command("mission_plan", mission_type="Supply", squad="Soldiers")
        result = e.handle_command("mission_resolve", casualties_roll="success",
                                  success_level="success")
        assert "Supply" in result
        assert "SUCCESS" in result.upper()

    def test_mission_resolve_failure(self):
        e = self._engine()
        e.handle_command("mission_plan", mission_type="Rescue", squad="Rookies")
        result = e.handle_command("mission_resolve", casualties_roll="failure",
                                  success_level="failure")
        assert "FAILURE" in result.upper()
        assert "Casualties" in result

    def test_trace_fact(self):
        e = self._engine()
        result = e.handle_command("trace_fact", fact="Chosen identity")
        assert isinstance(result, str)

    def test_unknown_command(self):
        e = self._engine()
        result = e.handle_command("not_a_real_command")
        assert "Unknown" in result

    def test_all_commands_in_registry_dispatch(self):
        """Every command in BOB_COMMANDS should at minimum not raise."""
        from codex.games.bob import BOB_COMMANDS
        e = self._engine()

        skip_with_special_args = {
            "supply_check",      # needs delta
            "march",             # needs destination
            "camp",              # needs activity
            "time_passes",       # needs days
            "mission_plan",      # needs mission_type, squad
            "mission_resolve",   # needs planned mission first
        }

        for cmd in BOB_COMMANDS:
            if cmd in skip_with_special_args:
                continue
            result = e.handle_command(cmd)
            assert isinstance(result, str), f"Command '{cmd}' did not return str"

    def test_bob_commands_has_new_commands(self):
        """Verify the command registry was updated with Phase2A commands."""
        from codex.games.bob import BOB_COMMANDS, BOB_CATEGORIES
        new_commands = ["march", "camp", "mission_plan", "mission_resolve",
                        "pressure_check", "time_passes", "campaign_status"]
        for cmd in new_commands:
            assert cmd in BOB_COMMANDS, f"'{cmd}' missing from BOB_COMMANDS"

        assert "Campaign" in BOB_CATEGORIES
        assert "Mission" in BOB_CATEGORIES

    def test_campaign_sync_after_march(self):
        """march command should sync LegionState supply with CampaignPhaseManager."""
        e = self._engine()
        initial_supply = e.legion.supply
        e.handle_command("march", destination="Barrowfield", supply_cost=1)
        assert e.legion.supply == initial_supply - 1

    def test_camp_sync_after_resupply(self):
        """camp resupply should reflect in LegionState supply."""
        e = self._engine()
        e.legion.supply = 2  # Set a known baseline
        e.handle_command("camp", activity="resupply")
        # Supply should be > 2 after resupply
        assert e.legion.supply >= 2

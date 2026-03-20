"""
tests/test_sav_bob_depth.py — WO-P3: SaV + BoB Depth Tests
============================================================
Tests for:
  - PlanningPhase (jobs.py)
  - SaVDowntimeManager (downtime.py)
  - SaVEngine: new commands, inherited fortune/resist/gather_info, save/load
  - BoBEngine: extended camp commands, inherited mechanics, save/load
"""

import random
import pytest


# =========================================================================
# HELPERS
# =========================================================================

def _seeded(seed: int) -> random.Random:
    """Return a seeded Random for deterministic tests."""
    return random.Random(seed)


def _make_sav_engine():
    """Create a SaVEngine with a single character registered."""
    from codex.games.sav import SaVEngine
    engine = SaVEngine()
    engine.create_character("Kira", playbook="Pilot", heritage="Spacer")
    engine.ship_name = "Nightfall"
    engine.ship_class = "Stardancer"
    return engine


def _make_bob_engine():
    """Create a BoBEngine with a single legionnaire registered."""
    from codex.games.bob import BoBEngine
    engine = BoBEngine()
    engine.create_character("Cade", playbook="Scout", heritage="Bartan")
    engine.chosen = "Dariusz"
    return engine


# =========================================================================
# PLANNING PHASE TESTS
# =========================================================================

class TestPlanningPhase:
    """Tests for codex/games/sav/jobs.py PlanningPhase."""

    def test_valid_plan_type_accepted(self):
        from codex.games.sav.jobs import PlanningPhase
        phase = PlanningPhase()
        result = phase.set_plan("assault", "via the loading dock")
        assert result["success"] is True
        assert result["plan_type"] == "assault"
        assert result["detail"] == "via the loading dock"
        assert phase.completed is True

    def test_all_valid_plan_types_accepted(self):
        from codex.games.sav.jobs import PlanningPhase
        for plan_type in ["assault", "deception", "infiltration", "mystic", "social", "transport"]:
            phase = PlanningPhase()
            result = phase.set_plan(plan_type)
            assert result["success"] is True, f"Expected {plan_type!r} to be valid"

    def test_invalid_plan_type_rejected(self):
        from codex.games.sav.jobs import PlanningPhase
        phase = PlanningPhase()
        result = phase.set_plan("stealth")
        assert result["success"] is False
        assert "error" in result
        assert phase.completed is False

    def test_case_insensitive_plan_type(self):
        from codex.games.sav.jobs import PlanningPhase
        phase = PlanningPhase()
        result = phase.set_plan("ASSAULT")
        assert result["success"] is True
        assert phase.plan_type == "assault"

    def test_empty_detail_allowed(self):
        from codex.games.sav.jobs import PlanningPhase
        phase = PlanningPhase()
        result = phase.set_plan("social")
        assert result["success"] is True
        assert phase.detail == ""

    def test_to_dict_round_trip(self):
        from codex.games.sav.jobs import PlanningPhase
        phase = PlanningPhase()
        phase.set_plan("infiltration", "through the maintenance shaft")
        phase.loadout = "light"
        d = phase.to_dict()
        assert d["plan_type"] == "infiltration"
        assert d["detail"] == "through the maintenance shaft"
        assert d["loadout"] == "light"
        assert d["completed"] is True

    def test_from_dict_restores_state(self):
        from codex.games.sav.jobs import PlanningPhase
        original = PlanningPhase()
        original.set_plan("transport", "using the decoy freighter")
        original.loadout = "heavy"
        restored = PlanningPhase.from_dict(original.to_dict())
        assert restored.plan_type == "transport"
        assert restored.detail == "using the decoy freighter"
        assert restored.loadout == "heavy"
        assert restored.completed is True

    def test_from_dict_with_partial_data(self):
        from codex.games.sav.jobs import PlanningPhase
        phase = PlanningPhase.from_dict({})
        assert phase.plan_type == ""
        assert phase.loadout == "normal"
        assert phase.completed is False

    def test_overwrite_existing_plan(self):
        from codex.games.sav.jobs import PlanningPhase
        phase = PlanningPhase()
        phase.set_plan("assault")
        result = phase.set_plan("deception", "posing as Hegemony inspectors")
        assert result["success"] is True
        assert phase.plan_type == "deception"


# =========================================================================
# SaV DOWNTIME MANAGER TESTS
# =========================================================================

class TestSaVDowntimeManager:
    """Tests for codex/games/sav/downtime.py SaVDowntimeManager."""

    def test_acquire_asset_success(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        # Force a high roll via seed
        rng = _seeded(999)  # will likely produce high values
        result = mgr.acquire_asset(crew_tier=3, quality_desired=2, rng=rng)
        assert "success" in result
        assert "quality" in result
        assert "dice" in result
        assert len(result["dice"]) == 3
        assert isinstance(result["description"], str)

    def test_acquire_asset_failure_on_low_roll(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        # Seed that produces 1,1,1
        class ForcedLowRng:
            def randint(self, a, b):
                return 1
        result = mgr.acquire_asset(crew_tier=2, quality_desired=2, rng=ForcedLowRng())
        assert result["success"] is False
        assert "Failed" in result["description"]

    def test_acquire_asset_minimum_one_die(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        result = mgr.acquire_asset(crew_tier=0)
        # Should roll 1 die minimum, not 0
        assert len(result["dice"]) == 1

    def test_recover_high_roll_heals_two_levels(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedSixRng:
            def randint(self, a, b):
                return 6
        result = mgr.recover(healer_dots=2, rng=ForcedSixRng())
        assert result["levels_healed"] == 2
        assert "2 harm level" in result["description"]

    def test_recover_mid_roll_heals_one_level(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedFourRng:
            def randint(self, a, b):
                return 4
        result = mgr.recover(healer_dots=1, rng=ForcedFourRng())
        assert result["levels_healed"] == 1

    def test_recover_low_roll_heals_nothing(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedLowRng:
            def randint(self, a, b):
                return 2
        result = mgr.recover(healer_dots=1, rng=ForcedLowRng())
        assert result["levels_healed"] == 0
        assert "unsuccessful" in result["description"]

    def test_vice_indulgence_normal(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedThreeRng:
            def randint(self, a, b):
                return 3
        result = mgr.vice_indulgence(rng=ForcedThreeRng())
        assert result["stress_recovered"] == 3
        assert result["overindulged"] is False
        assert "OVERINDULGENCE" not in result["description"]

    def test_vice_indulgence_overindulgence_on_six(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedSixRng:
            def randint(self, a, b):
                return 6
        result = mgr.vice_indulgence(rng=ForcedSixRng())
        assert result["stress_recovered"] == 6
        assert result["overindulged"] is True
        assert "OVERINDULGENCE" in result["description"]

    def test_long_term_project_creates_new_project(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedFiveRng:
            def randint(self, a, b):
                return 5
        result = mgr.long_term_project("Forge documents", action_dots=2, clock_size=6, rng=ForcedFiveRng())
        assert result["project"] == "Forge documents"
        assert result["ticks"] == 2
        assert result["progress"] == 2
        assert result["size"] == 6
        assert result["completed"] is False

    def test_long_term_project_accumulates_progress(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedFourRng:
            def randint(self, a, b):
                return 4
        mgr.long_term_project("Build smuggler hold", action_dots=1, clock_size=4, rng=ForcedFourRng())
        mgr.long_term_project("Build smuggler hold", action_dots=1, clock_size=4, rng=ForcedFourRng())
        result = mgr.long_term_project("Build smuggler hold", action_dots=1, clock_size=4, rng=ForcedFourRng())
        assert result["completed"] is True
        assert "COMPLETED" in result["description"]

    def test_long_term_project_six_gives_three_ticks(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedSixRng:
            def randint(self, a, b):
                return 6
        result = mgr.long_term_project("Upgrade engines", action_dots=1, clock_size=8, rng=ForcedSixRng())
        assert result["ticks"] == 3

    def test_long_term_project_low_roll_gives_one_tick(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedOneRng:
            def randint(self, a, b):
                return 1
        result = mgr.long_term_project("Bribe official", action_dots=1, clock_size=8, rng=ForcedOneRng())
        assert result["ticks"] == 1

    def test_train_returns_xp(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        result = mgr.train("insight")
        assert result["xp_gained"] == 1
        assert result["attribute"] == "insight"
        assert "XP" in result["description"]

    def test_to_dict_from_dict_round_trip(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager()
        class ForcedFourRng:
            def randint(self, a, b):
                return 4
        mgr.long_term_project("Test project", action_dots=1, clock_size=6, rng=ForcedFourRng())
        d = mgr.to_dict()
        restored = SaVDowntimeManager.from_dict(d)
        assert "Test project" in restored.projects
        assert restored.projects["Test project"]["progress"] == 2

    def test_from_dict_empty_data(self):
        from codex.games.sav.downtime import SaVDowntimeManager
        mgr = SaVDowntimeManager.from_dict({})
        assert mgr.projects == {}


# =========================================================================
# SaV ENGINE INTEGRATION TESTS
# =========================================================================

class TestSaVEngineDepth:
    """Integration tests for SaVEngine P3 commands."""

    def test_plan_job_valid(self):
        engine = _make_sav_engine()
        result = engine.handle_command("plan_job", plan_type="infiltration", detail="through the vent shaft")
        assert "infiltration" in result
        assert "vent shaft" in result

    def test_plan_job_invalid_type(self):
        engine = _make_sav_engine()
        result = engine.handle_command("plan_job", plan_type="sneaky")
        assert "Invalid" in result or "invalid" in result.lower()

    def test_plan_job_persists_in_planning_phase(self):
        engine = _make_sav_engine()
        engine.handle_command("plan_job", plan_type="social", detail="posing as buyers")
        phase = engine._get_planning_phase()
        assert phase.plan_type == "social"
        assert phase.completed is True

    def test_downtime_acquire_returns_description(self):
        engine = _make_sav_engine()
        result = engine.handle_command("downtime_acquire", crew_tier=2, quality=1)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_downtime_recover_returns_description(self):
        engine = _make_sav_engine()
        result = engine.handle_command("downtime_recover", healer_dots=2)
        assert isinstance(result, str)

    def test_downtime_vice_reduces_stress(self):
        engine = _make_sav_engine()
        char = engine.character
        # Push some stress first
        engine.push_stress(char.name, 5)
        stress_before = engine.stress_clocks[char.name].current_stress
        engine.handle_command("downtime_vice")
        stress_after = engine.stress_clocks[char.name].current_stress
        # Stress should have been reduced (or at least not increased)
        assert stress_after <= stress_before

    def test_downtime_project_requires_name(self):
        engine = _make_sav_engine()
        result = engine.handle_command("downtime_project")
        assert "project_name" in result.lower() or "Specify" in result

    def test_downtime_project_progresses(self):
        engine = _make_sav_engine()
        result = engine.handle_command("downtime_project", project_name="Hidden cache", clock_size=8)
        assert "Hidden cache" in result
        assert "/" in result  # progress/size format

    def test_downtime_train_returns_xp(self):
        engine = _make_sav_engine()
        result = engine.handle_command("downtime_train", attribute="prowess")
        assert "prowess" in result
        assert "XP" in result or "xp" in result.lower()

    def test_faction_response_scales_with_heat(self):
        engine = _make_sav_engine()
        engine.heat = 0
        result_low = engine.handle_command("faction_response")
        assert "haven't noticed" in result_low

        engine.heat = 3
        result_high = engine.handle_command("faction_response")
        assert "retaliation" in result_high or "strike" in result_high or "war" in result_high or "Faction" in result_high

    def test_faction_response_capped_at_4(self):
        engine = _make_sav_engine()
        engine.heat = 99  # way above max
        result = engine.handle_command("faction_response")
        # Should not crash; heat_tier capped at 4
        assert isinstance(result, str)

    def test_fortune_inherited(self):
        engine = _make_sav_engine()
        result = engine.handle_command("fortune", dice_count=2)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resist_inherited_requires_attribute(self):
        engine = _make_sav_engine()
        result = engine.handle_command("resist")
        assert "attribute" in result.lower() or "Specify" in result

    def test_resist_inherited_with_attribute(self):
        engine = _make_sav_engine()
        result = engine.handle_command("resist", attribute="attune")
        assert isinstance(result, str)
        # Should mention stress cost
        assert "stress" in result.lower()

    def test_gather_info_inherited(self):
        engine = _make_sav_engine()
        result = engine.handle_command("gather_info", action="study", question="Where is the vault?")
        assert isinstance(result, str)
        assert "Where is the vault" in result or "quality" in result.lower()

    def test_save_load_preserves_downtime_state(self):
        engine = _make_sav_engine()
        # Trigger downtime manager via a project
        engine.handle_command("downtime_project", project_name="Establish safe house", clock_size=6)
        state = engine.save_state()
        assert state["downtime_mgr"] is not None
        assert "Establish safe house" in state["downtime_mgr"]["projects"]

        # Restore into fresh engine
        from codex.games.sav import SaVEngine
        engine2 = SaVEngine()
        engine2.load_state(state)
        assert engine2._downtime_mgr is not None
        assert "Establish safe house" in engine2._downtime_mgr.projects

    def test_save_load_preserves_planning_phase(self):
        engine = _make_sav_engine()
        engine.handle_command("plan_job", plan_type="mystic", detail="through the void")
        state = engine.save_state()
        assert state["planning_phase"] is not None
        assert state["planning_phase"]["plan_type"] == "mystic"

        from codex.games.sav import SaVEngine
        engine2 = SaVEngine()
        engine2.load_state(state)
        assert engine2._planning_phase is not None
        assert engine2._planning_phase.plan_type == "mystic"

    def test_save_load_none_when_uninitialized(self):
        engine = _make_sav_engine()
        state = engine.save_state()
        # Subsystems never accessed — should serialize as None
        assert state["downtime_mgr"] is None
        assert state["planning_phase"] is None

    def test_command_registry_includes_new_commands(self):
        engine = _make_sav_engine()
        registry = engine._get_command_registry()
        for cmd in ["plan_job", "downtime_acquire", "downtime_recover",
                    "downtime_vice", "downtime_project", "downtime_train",
                    "faction_response", "fortune", "resist", "gather_info"]:
            assert cmd in registry, f"Expected {cmd!r} in command registry"


# =========================================================================
# BoB ENGINE INTEGRATION TESTS
# =========================================================================

class TestBoBEngineDepth:
    """Integration tests for BoBEngine P3 commands."""

    def test_religious_services_adjusts_morale(self):
        engine = _make_bob_engine()
        morale_before = engine.legion.morale
        engine.handle_command("religious_services")
        morale_after = engine.legion.morale
        # Morale should stay same or increase
        assert morale_after >= morale_before

    def test_religious_services_high_roll_adds_two(self):
        engine = _make_bob_engine()
        engine.legion.morale = 5
        # Patch by directly calling with forced rng
        import random as rng_module
        original_randint = rng_module.randint
        rng_module.randint = lambda a, b: 6
        try:
            result = engine.handle_command("religious_services")
        finally:
            rng_module.randint = original_randint
        assert "2" in result or engine.legion.morale == 7

    def test_liberty_stress_relief_in_result(self):
        engine = _make_bob_engine()
        result = engine.handle_command("liberty")
        assert isinstance(result, str)
        assert "Stress relief" in result or "stress" in result.lower()

    def test_liberty_overindulgence_reduces_morale(self):
        engine = _make_bob_engine()
        engine.legion.morale = 8
        import random as rng_module
        original_randint = rng_module.randint
        rng_module.randint = lambda a, b: 6
        try:
            result = engine.handle_command("liberty")
        finally:
            rng_module.randint = original_randint
        assert "OVERINDULGENCE" in result
        assert engine.legion.morale == 7

    def test_scrounge_high_roll_gains_supply(self):
        engine = _make_bob_engine()
        engine.legion.supply = 3
        import random as rng_module
        original_randint = rng_module.randint
        rng_module.randint = lambda a, b: 6
        try:
            engine.handle_command("scrounge")
        finally:
            rng_module.randint = original_randint
        assert engine.legion.supply == 5

    def test_scrounge_low_roll_gains_nothing(self):
        engine = _make_bob_engine()
        engine.legion.supply = 4
        import random as rng_module
        original_randint = rng_module.randint
        rng_module.randint = lambda a, b: 2
        try:
            result = engine.handle_command("scrounge")
        finally:
            rng_module.randint = original_randint
        assert engine.legion.supply == 4
        assert "Nothing useful" in result

    def test_record_casualty_adds_to_list(self):
        engine = _make_bob_engine()
        engine.handle_command("record_casualty", name="Sergeant Varis")
        assert "Sergeant Varis" in engine._fallen_legionnaires

    def test_record_casualty_decrements_morale(self):
        engine = _make_bob_engine()
        engine.legion.morale = 7
        engine.handle_command("record_casualty", name="Luca")
        assert engine.legion.morale == 6

    def test_record_casualty_requires_name(self):
        engine = _make_bob_engine()
        result = engine.handle_command("record_casualty")
        assert "Specify" in result or "name" in result.lower()

    def test_memorial_shows_fallen(self):
        engine = _make_bob_engine()
        engine.handle_command("record_casualty", name="Elise")
        engine.handle_command("record_casualty", name="Brand")
        result = engine.handle_command("memorial")
        assert "Elise" in result
        assert "Brand" in result
        assert "Total fallen: 2" in result

    def test_memorial_no_fallen(self):
        engine = _make_bob_engine()
        result = engine.handle_command("memorial")
        assert "No fallen" in result or "endures" in result

    def test_multiple_casualties_tracked(self):
        engine = _make_bob_engine()
        names = ["Varis", "Elise", "Brand", "Oryn"]
        for name in names:
            engine.handle_command("record_casualty", name=name)
        assert len(engine._fallen_legionnaires) == 4
        for name in names:
            assert name in engine._fallen_legionnaires

    def test_legion_advance_thresholds_locked_at_zero(self):
        engine = _make_bob_engine()
        engine._missions_completed = 0
        result = engine.handle_command("legion_advance")
        assert "0" in result
        assert "more needed" in result

    def test_legion_advance_first_threshold_unlocked(self):
        engine = _make_bob_engine()
        engine._missions_completed = 3
        result = engine.handle_command("legion_advance")
        assert "UNLOCKED" in result

    def test_legion_advance_all_unlocked_at_10(self):
        engine = _make_bob_engine()
        engine._missions_completed = 10
        result = engine.handle_command("legion_advance")
        assert result.count("UNLOCKED") == 3

    def test_legion_advance_partial_unlocks(self):
        engine = _make_bob_engine()
        engine._missions_completed = 6
        result = engine.handle_command("legion_advance")
        assert result.count("UNLOCKED") == 2
        assert "more needed" in result

    def test_fortune_inherited(self):
        engine = _make_bob_engine()
        result = engine.handle_command("fortune", dice_count=2)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resist_inherited_requires_attribute(self):
        engine = _make_bob_engine()
        result = engine.handle_command("resist")
        assert "attribute" in result.lower() or "Specify" in result

    def test_resist_inherited_with_attribute(self):
        engine = _make_bob_engine()
        result = engine.handle_command("resist", attribute="discipline")
        assert isinstance(result, str)
        assert "stress" in result.lower()

    def test_gather_info_inherited(self):
        engine = _make_bob_engine()
        result = engine.handle_command("gather_info", action="scout_action", question="Enemy positions?")
        assert isinstance(result, str)
        assert "Enemy positions" in result or "quality" in result.lower()

    def test_save_load_preserves_fallen_legionnaires(self):
        engine = _make_bob_engine()
        engine.handle_command("record_casualty", name="Varis")
        engine.handle_command("record_casualty", name="Elise")
        state = engine.save_state()
        assert "Varis" in state["fallen_legionnaires"]
        assert "Elise" in state["fallen_legionnaires"]

        from codex.games.bob import BoBEngine
        engine2 = BoBEngine()
        engine2.load_state(state)
        assert "Varis" in engine2._fallen_legionnaires
        assert "Elise" in engine2._fallen_legionnaires

    def test_save_load_preserves_missions_completed(self):
        engine = _make_bob_engine()
        engine._missions_completed = 7
        state = engine.save_state()
        assert state["missions_completed"] == 7

        from codex.games.bob import BoBEngine
        engine2 = BoBEngine()
        engine2.load_state(state)
        assert engine2._missions_completed == 7

    def test_save_load_fallen_empty_by_default(self):
        engine = _make_bob_engine()
        state = engine.save_state()
        assert state["fallen_legionnaires"] == []
        assert state["missions_completed"] == 0

    def test_command_registry_includes_new_commands(self):
        engine = _make_bob_engine()
        registry = engine._get_command_registry()
        for cmd in ["religious_services", "liberty", "scrounge", "memorial",
                    "record_casualty", "legion_advance", "fortune", "resist", "gather_info"]:
            assert cmd in registry, f"Expected {cmd!r} in command registry"

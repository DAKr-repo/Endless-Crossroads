"""
WO Phase 1B — Scum & Villainy Engine Depth: Tests
===================================================

Covers:
  - TestSaVPlaybookData     — 7 playbooks load with required fields
  - TestSaVShipData         — 3 ship classes, 15 modules load
  - TestSaVFactionData      — 20+ factions load
  - TestShipState           — Ship damage, repair, operational checks
  - TestShipCombat          — Ship combat rolls, damage system
  - TestJobPhaseManager     — Job lifecycle: engage, complications, resolve
  - TestJumpPlanning        — Jump roll outcomes
  - TestSaVEngineSaveLoad   — Full round-trip with subsystem state
  - TestSaVCommandDispatch  — All handle_command dispatches
"""

import random
import pytest

from codex.forge.reference_data.sav_playbooks import PLAYBOOKS, HERITAGES, VICE_TYPES
from codex.forge.reference_data.sav_ships import (
    SHIP_CLASSES,
    SHIP_MODULES,
    SYSTEM_QUALITY_TRACKS,
)
from codex.forge.reference_data.sav_factions import FACTIONS, FACTION_STATUS
from codex.forge.reference_data.sav import (
    PLAYBOOKS as AGG_PLAYBOOKS,
    SHIP_CLASSES as AGG_SHIP_CLASSES,
    FACTIONS as AGG_FACTIONS,
)
from codex.games.sav.ships import (
    ShipState,
    ship_combat_roll,
    damage_system,
    repair_system,
    install_module,
    use_gambit,
)
from codex.games.sav.jobs import (
    JobState,
    JobPhaseManager,
    jump_planning,
    PLAN_TYPES,
    ENGAGEMENT_OUTCOMES,
)
from codex.games.sav import SaVEngine, SaVCharacter


# =========================================================================
# HELPERS
# =========================================================================

def _rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def _make_ship(ship_class: str = "Cerberus") -> ShipState:
    """Create a ShipState from a known ship class."""
    return ShipState(name="Test Ship", ship_class=ship_class)


def _make_engine() -> SaVEngine:
    """Create a SaVEngine with one character."""
    engine = SaVEngine()
    engine.create_character("Vex", playbook="Pilot", heritage="Spacer")
    engine.ship_name = "Stardancer"
    engine.ship_class = "Stardancer"
    return engine


# =========================================================================
# PLAYBOOK DATA
# =========================================================================

class TestSaVPlaybookData:
    """Verify all 7 playbooks load with the required field structure."""

    EXPECTED_PLAYBOOKS = [
        "Mechanic", "Muscle", "Mystic", "Pilot",
        "Scoundrel", "Speaker", "Stitch",
    ]

    def test_all_playbooks_present(self):
        for pb in self.EXPECTED_PLAYBOOKS:
            assert pb in PLAYBOOKS, f"Missing playbook: {pb}"

    def test_playbook_count(self):
        assert len(PLAYBOOKS) == 7

    def test_each_playbook_has_description(self):
        for name, data in PLAYBOOKS.items():
            assert "description" in data, f"{name} missing description"
            assert len(data["description"]) > 20, f"{name} description too short"

    def test_each_playbook_has_six_or_more_abilities(self):
        for name, data in PLAYBOOKS.items():
            abilities = data.get("special_abilities", [])
            assert len(abilities) >= 6, f"{name} has only {len(abilities)} abilities"

    def test_each_ability_has_name_and_description(self):
        for pb_name, data in PLAYBOOKS.items():
            for ability in data.get("special_abilities", []):
                assert "name" in ability, f"{pb_name} ability missing name"
                assert "description" in ability, f"{pb_name}/{ability.get('name')} missing description"

    def test_each_playbook_has_friends(self):
        for name, data in PLAYBOOKS.items():
            friends = data.get("friends", [])
            assert len(friends) > 0, f"{name} has no friends"

    def test_each_playbook_has_rivals(self):
        for name, data in PLAYBOOKS.items():
            rivals = data.get("rivals", [])
            assert len(rivals) > 0, f"{name} has no rivals"

    def test_each_playbook_has_items(self):
        for name, data in PLAYBOOKS.items():
            items = data.get("items", [])
            assert len(items) > 0, f"{name} has no items"

    def test_each_playbook_has_xp_trigger(self):
        for name, data in PLAYBOOKS.items():
            assert "xp_trigger" in data, f"{name} missing xp_trigger"
            assert len(data["xp_trigger"]) > 10

    def test_heritages_present(self):
        # SOURCE: Scum and Villainy.pdf, p.58 — exactly 4 heritages confirmed
        # "Wanderer" was a fabricated entry, removed
        expected = ["Colonist", "Imperial", "Spacer", "Syndicate"]
        for h in expected:
            assert h in HERITAGES, f"Missing heritage: {h}"

    def test_heritages_have_descriptions(self):
        for name, data in HERITAGES.items():
            assert "description" in data
            assert len(data["description"]) > 20

    def test_vice_types_present(self):
        assert len(VICE_TYPES) >= 6

    def test_aggregator_re_exports_playbooks(self):
        assert AGG_PLAYBOOKS is PLAYBOOKS


# =========================================================================
# SHIP DATA
# =========================================================================

class TestSaVShipData:
    """Verify all 3 ship classes and 15 modules load correctly."""

    EXPECTED_SHIPS = ["Stardancer", "Cerberus", "Firedrake"]
    # SOURCE: Scum and Villainy.pdf, p.117-120
    # Auxiliary modules confirmed p.118: AI Module, Armory, Brig, Galley, Medical Bay, Science Bay, Shields
    # Ship upgrades confirmed p.117: Holo-Emitters, Intruder Alarm, Land Rover, Power Reserves,
    #   Shuttle, Stasis Pods, Vault
    # Engine/Comms/Weapon modules from p.119-120 (EXPANDED names where text unextractable)
    # Old fabricated names removed: Cloaking Device, Cargo Bay Expansion, Crew Quarters,
    #   Engine Boost, Salvage Rig
    EXPECTED_MODULES = [
        # Auxiliary — SOURCE: p.118
        "AI Module", "Armory", "Brig", "Galley", "Medical Bay", "Science Bay", "Shields",
        # Hull upgrades — SOURCE: p.117
        "Holo-Emitters", "Intruder Alarm", "Shuttle", "Vault",
        # Comms — EXPANDED
        "Fake Transponder", "ECM Suite", "Long-Range Sensors", "Void Compass",
    ]

    def test_all_ship_classes_present(self):
        for ship in self.EXPECTED_SHIPS:
            assert ship in SHIP_CLASSES, f"Missing ship class: {ship}"

    def test_ship_class_count(self):
        assert len(SHIP_CLASSES) == 3

    def test_each_ship_has_description(self):
        for name, data in SHIP_CLASSES.items():
            assert "description" in data, f"{name} missing description"

    def test_each_ship_has_four_systems(self):
        systems = {"engines", "hull", "comms", "weapons"}
        for name, data in SHIP_CLASSES.items():
            assert "systems" in data, f"{name} missing systems"
            assert set(data["systems"].keys()) == systems, f"{name} wrong systems"

    def test_system_quality_values_in_range(self):
        for name, data in SHIP_CLASSES.items():
            for sys_name, quality in data["systems"].items():
                assert 0 <= quality <= 3, f"{name}.{sys_name} quality {quality} out of range"

    def test_each_ship_has_crew_min(self):
        for name, data in SHIP_CLASSES.items():
            assert "crew_min" in data, f"{name} missing crew_min"
            assert data["crew_min"] >= 1

    def test_each_ship_has_speed(self):
        for name, data in SHIP_CLASSES.items():
            assert "speed" in data, f"{name} missing speed"
            assert 1 <= data["speed"] <= 4

    def test_stardancer_is_fastest(self):
        assert SHIP_CLASSES["Stardancer"]["speed"] > SHIP_CLASSES["Cerberus"]["speed"]
        assert SHIP_CLASSES["Stardancer"]["speed"] > SHIP_CLASSES["Firedrake"]["speed"]

    def test_firedrake_has_highest_weapons(self):
        assert SHIP_CLASSES["Firedrake"]["systems"]["weapons"] == 3

    def test_all_modules_present(self):
        for module in self.EXPECTED_MODULES:
            assert module in SHIP_MODULES, f"Missing module: {module}"

    def test_module_count_at_least_15(self):
        assert len(SHIP_MODULES) >= 15

    def test_each_module_has_description(self):
        for name, data in SHIP_MODULES.items():
            assert "description" in data, f"{name} missing description"

    def test_each_module_has_category(self):
        # SOURCE: Scum and Villainy.pdf, p.118-120 — modules organized by category
        # Field is "category" (auxiliary/hull/engines/comms/weapons)
        valid_categories = {"auxiliary", "engines", "hull", "comms", "weapons"}
        for name, data in SHIP_MODULES.items():
            assert "category" in data, f"{name} missing category"
            assert data["category"] in valid_categories, f"{name} has invalid category: {data['category']}"

    def test_each_module_has_effect(self):
        for name, data in SHIP_MODULES.items():
            assert "effect" in data, f"{name} missing effect"

    def test_system_quality_tracks_for_all_systems(self):
        for sys_name in ["engines", "hull", "comms", "weapons"]:
            assert sys_name in SYSTEM_QUALITY_TRACKS
            track = SYSTEM_QUALITY_TRACKS[sys_name]
            for level in [0, 1, 2, 3]:
                assert level in track, f"{sys_name} missing quality level {level}"

    def test_aggregator_re_exports_ship_classes(self):
        assert AGG_SHIP_CLASSES is SHIP_CLASSES


# =========================================================================
# FACTION DATA
# =========================================================================

class TestSaVFactionData:
    """Verify 20+ factions load with required fields."""

    def test_faction_count_at_least_20(self):
        assert len(FACTIONS) >= 20

    def test_each_faction_has_required_fields(self):
        # SOURCE: Scum and Villainy.pdf, p.316-326
        # Added "category" (Hegemony/Weirdness/Criminal) and "goal" to required fields
        required = {"tier", "category", "description", "notable_npcs", "sector", "quirk", "goal"}
        for name, data in FACTIONS.items():
            missing = required - set(data.keys())
            assert not missing, f"{name} missing fields: {missing}"

    def test_tiers_are_in_valid_range(self):
        for name, data in FACTIONS.items():
            assert 1 <= data["tier"] <= 5, f"{name} tier {data['tier']} out of range"

    def test_guild_of_engineers_is_tier_5(self):
        # SOURCE: Scum and Villainy.pdf, p.316 — Guild of Engineers is Tier V (highest)
        # "The Hegemony" is not a faction entry; Guild of Engineers represents Hegemony power
        assert FACTIONS["Guild of Engineers"]["tier"] == 5

    def test_church_of_stellar_flame_is_tier_4(self):
        # SOURCE: Scum and Villainy.pdf, p.316
        assert FACTIONS["Church of Stellar Flame"]["tier"] == 4

    def test_all_factions_have_npcs_list(self):
        # Not all factions have named NPCs in the PDF (some pages unextractable)
        # All factions must have the notable_npcs KEY (list may be empty for unextracted pages)
        for name, data in FACTIONS.items():
            assert "notable_npcs" in data, f"{name} missing notable_npcs key"

    def test_all_factions_have_quirk(self):
        for name, data in FACTIONS.items():
            assert len(data.get("quirk", "")) > 10, f"{name} quirk too short"

    def test_faction_status_scale_has_7_entries(self):
        # -3 to +3
        assert len(FACTION_STATUS) == 7

    def test_faction_status_range(self):
        for level in range(-3, 4):
            assert level in FACTION_STATUS, f"FACTION_STATUS missing level {level}"

    def test_specific_factions_present(self):
        # SOURCE: Scum and Villainy.pdf, p.316-319
        # Corrected from fabricated names:
        #   "The Hegemony" -> not a faction (Guild of Engineers is Tier V Hegemony anchor)
        #   "Cobalt Wolves" -> "Scarlet Wolves" (SOURCE: p.316, p.319)
        #   "The Wreckers" -> "Wreckers" (SOURCE: p.316)
        expected = [
            "Guild of Engineers", "Scarlet Wolves",
            "Nightspeakers", "Wreckers", "Vignerons",
            "The Agony", "Ashen Knives", "Dyrinek Gang",
        ]
        for f in expected:
            assert f in FACTIONS, f"Missing faction: {f}"

    def test_aggregator_re_exports_factions(self):
        assert AGG_FACTIONS is FACTIONS


# =========================================================================
# SHIP STATE
# =========================================================================

class TestShipState:
    """Test ShipState construction, damage, repair, and serialisation."""

    def test_default_construction(self):
        ship = ShipState()
        assert ship.name == "Unnamed"
        assert ship.hull_integrity == 6
        assert ship.gambits == 2

    def test_cerberus_sets_correct_systems(self):
        ship = _make_ship("Cerberus")
        assert ship.systems["hull"] == 3
        assert ship.systems["weapons"] == 2
        assert ship.systems["engines"] == 2

    def test_stardancer_has_best_engines(self):
        ship = _make_ship("Stardancer")
        assert ship.systems["engines"] == 3

    def test_firedrake_has_best_weapons(self):
        ship = _make_ship("Firedrake")
        assert ship.systems["weapons"] == 3

    def test_take_damage_reduces_system(self):
        ship = _make_ship("Cerberus")
        before = ship.systems["engines"]
        ship.take_damage("engines", 1)
        assert ship.systems["engines"] == before - 1

    def test_take_damage_clamps_at_zero(self):
        ship = _make_ship("Cerberus")
        ship.take_damage("engines", 99)
        assert ship.systems["engines"] == 0

    def test_hull_damage_reduces_integrity(self):
        ship = _make_ship("Cerberus")
        ship.take_damage("hull", 2)
        assert ship.hull_integrity == 4

    def test_repair_system_increases_quality(self):
        ship = _make_ship("Cerberus")
        ship.systems["engines"] = 1
        ship.repair_system("engines", 1)
        assert ship.systems["engines"] == 2

    def test_repair_system_clamps_at_3(self):
        ship = _make_ship("Cerberus")
        ship.systems["engines"] = 3
        ship.repair_system("engines", 5)
        assert ship.systems["engines"] == 3

    def test_is_operational_when_systems_intact(self):
        ship = _make_ship("Cerberus")
        assert ship.is_operational() is True

    def test_not_operational_when_all_systems_zero(self):
        ship = _make_ship("Cerberus")
        for sys_name in ship.systems:
            ship.systems[sys_name] = 0
        ship.hull_integrity = 0
        assert ship.is_operational() is False

    def test_not_operational_when_hull_integrity_zero(self):
        ship = _make_ship("Cerberus")
        ship.hull_integrity = 0
        assert ship.is_operational() is False

    def test_to_dict_round_trip(self):
        ship = _make_ship("Cerberus")
        ship.gambits = 3
        ship.installed_modules = ["Medical Bay"]
        data = ship.to_dict()
        ship2 = ShipState.from_dict(data)
        assert ship2.name == ship.name
        assert ship2.ship_class == ship.ship_class
        assert ship2.systems == ship.systems
        assert ship2.gambits == 3
        assert "Medical Bay" in ship2.installed_modules

    def test_from_dict_restores_systems_exactly(self):
        """from_dict must not overwrite systems via __post_init__."""
        data = {
            "name": "Battle Scarred",
            "ship_class": "Cerberus",
            "hull_integrity": 3,
            "systems": {"engines": 1, "hull": 0, "comms": 2, "weapons": 1},
            "installed_modules": [],
            "crew_quality": 2,
            "gambits": 1,
        }
        ship = ShipState.from_dict(data)
        assert ship.systems["hull"] == 0
        assert ship.systems["engines"] == 1


# =========================================================================
# SHIP COMBAT
# =========================================================================

class TestShipCombat:
    """Test ship_combat_roll and damage_system functions."""

    def test_combat_roll_returns_dict_with_required_keys(self):
        ship = _make_ship("Cerberus")
        result = ship_combat_roll(ship, "weapons", rng=_rng(42))
        assert "dice" in result
        assert "highest" in result
        assert "critical" in result
        assert "outcome" in result
        assert "description" in result

    def test_combat_roll_uses_system_quality_as_dice_count(self):
        ship = _make_ship("Cerberus")
        # weapons quality = 2, so 2 dice
        result = ship_combat_roll(ship, "weapons", bonus_dice=0, rng=_rng(1))
        assert len(result["dice"]) == 2

    def test_combat_roll_zero_dice_uses_two_dice_take_lowest(self):
        ship = _make_ship("Cerberus")
        ship.systems["engines"] = 0
        result = ship_combat_roll(ship, "engines", rng=_rng(7))
        assert len(result["dice"]) == 2

    def test_combat_roll_bonus_dice_added(self):
        ship = _make_ship("Cerberus")
        ship.systems["comms"] = 1
        result = ship_combat_roll(ship, "comms", bonus_dice=2, rng=_rng(1))
        assert len(result["dice"]) == 3

    def test_critical_outcome_when_two_sixes(self):
        # Find a seed that produces two sixes with 3 dice
        ship = _make_ship("Cerberus")
        ship.systems["weapons"] = 3
        found_critical = False
        for seed in range(500):
            result = ship_combat_roll(ship, "weapons", rng=random.Random(seed))
            if result["critical"]:
                assert result["outcome"] == "critical"
                found_critical = True
                break
        assert found_critical, "Could not find a critical in 500 seeds"

    def test_failure_outcome_when_all_dice_low(self):
        ship = _make_ship("Cerberus")
        ship.systems["weapons"] = 1
        found_failure = False
        for seed in range(500):
            result = ship_combat_roll(ship, "weapons", rng=random.Random(seed))
            if result["outcome"] == "failure":
                found_failure = True
                break
        assert found_failure, "Could not find a failure in 500 seeds"

    def test_damage_system_reduces_quality(self):
        ship = _make_ship("Cerberus")
        before = ship.systems["engines"]
        result = damage_system(ship, "engines", 1)
        assert result["damage_dealt"] == 1
        assert result["system_after"] == before - 1

    def test_damage_system_crippled_when_quality_zero(self):
        ship = _make_ship("Cerberus")
        ship.systems["engines"] = 1
        result = damage_system(ship, "engines", 1)
        assert result["crippled"] is True
        assert ship.systems["engines"] == 0

    def test_damage_system_includes_status_description(self):
        ship = _make_ship("Cerberus")
        result = damage_system(ship, "engines", 1)
        assert "status_description" in result
        assert len(result["status_description"]) > 5

    def test_damage_system_unknown_system_returns_error(self):
        ship = _make_ship("Cerberus")
        result = damage_system(ship, "photon_torpedoes", 1)
        assert "error" in result
        assert result["damage_dealt"] == 0

    def test_install_module_succeeds(self):
        ship = _make_ship("Cerberus")
        result = install_module(ship, "Medical Bay")
        assert result["success"] is True
        assert "Medical Bay" in ship.installed_modules

    def test_install_module_duplicate_fails(self):
        ship = _make_ship("Cerberus")
        install_module(ship, "Medical Bay")
        result = install_module(ship, "Medical Bay")
        assert result["success"] is False
        assert "already" in result["message"].lower()

    def test_install_unknown_module_fails(self):
        ship = _make_ship("Cerberus")
        result = install_module(ship, "Phase Cannon")
        assert result["success"] is False

    def test_use_gambit_decrements(self):
        ship = _make_ship("Cerberus")
        ship.gambits = 3
        result = use_gambit(ship)
        assert result["success"] is True
        assert result["gambits_remaining"] == 2
        assert ship.gambits == 2

    def test_use_gambit_fails_when_none(self):
        ship = _make_ship("Cerberus")
        ship.gambits = 0
        result = use_gambit(ship)
        assert result["success"] is False

    def test_repair_system_success(self):
        ship = _make_ship("Cerberus")
        ship.systems["engines"] = 1
        # Use enough mechanic dots to ensure a success
        found_success = False
        for seed in range(500):
            ship.systems["engines"] = 1
            result = repair_system(ship, "engines", mechanic_dots=3, rng=random.Random(seed))
            if result["outcome"] in ("success", "critical"):
                found_success = True
                assert result["system_after"] > 1
                break
        assert found_success

    def test_repair_system_failure_no_change(self):
        ship = _make_ship("Cerberus")
        ship.systems["comms"] = 1
        found_failure = False
        for seed in range(500):
            ship.systems["comms"] = 1
            result = repair_system(ship, "comms", mechanic_dots=1, rng=random.Random(seed))
            if result["outcome"] == "failure":
                found_failure = True
                assert result["restored"] == 0
                assert result["system_after"] == 1
                break
        assert found_failure


# =========================================================================
# JOB PHASE MANAGER
# =========================================================================

class TestJobPhaseManager:
    """Test the full job lifecycle."""

    def test_start_job_creates_job_state(self):
        manager = JobPhaseManager()
        job = manager.start_job("The Hegemony", "deception")
        assert isinstance(job, JobState)
        assert job.target == "The Hegemony"
        assert job.plan_type == "deception"
        assert job.active is True

    def test_start_job_sets_current_job(self):
        manager = JobPhaseManager()
        job = manager.start_job("Guild of Engineers", "infiltration")
        assert manager.current_job is job

    def test_add_complication_adds_to_list(self):
        manager = JobPhaseManager()
        manager.start_job("Target", "assault")
        manager.add_complication("Alarm triggered")
        manager.add_complication("Guard patrol spotted us")
        assert len(manager.current_job.complications) == 2

    def test_add_complication_with_no_job_doesnt_crash(self):
        manager = JobPhaseManager()
        manager.add_complication("This should not crash")  # No active job

    def test_engagement_roll_returns_required_keys(self):
        manager = JobPhaseManager()
        result = manager.job_engagement_roll(crew_tier=2, plan_type="assault", rng=_rng(42))
        assert "outcome" in result
        assert "dice" in result
        assert "highest" in result
        assert "starting_position" in result

    def test_engagement_controlled_on_success(self):
        manager = JobPhaseManager()
        found_controlled = False
        for seed in range(500):
            result = manager.job_engagement_roll(
                crew_tier=3, plan_type="deception", rng=random.Random(seed)
            )
            if result["outcome"] in ("success", "critical"):
                assert result["starting_position"] == "controlled"
                found_controlled = True
                break
        assert found_controlled

    def test_engagement_desperate_on_failure(self):
        manager = JobPhaseManager()
        found_desperate = False
        for seed in range(500):
            result = manager.job_engagement_roll(
                crew_tier=1, plan_type="assault", rng=random.Random(seed)
            )
            if result["outcome"] == "failure":
                assert result["starting_position"] == "desperate"
                found_desperate = True
                break
        assert found_desperate

    def test_plan_types_dict_has_all_types(self):
        expected = {"assault", "deception", "infiltration", "mystic", "social", "transport"}
        assert set(PLAN_TYPES.keys()) == expected

    def test_resolve_job_no_complications(self):
        manager = JobPhaseManager()
        manager.start_job("Small Merchant", "transport")
        result = manager.resolve_job(crew_tier=1, target_tier=1)
        assert "error" not in result
        assert result["cred"] >= 1
        assert result["rep"] >= 0
        assert result["heat"] >= 1

    def test_resolve_job_complications_increase_heat(self):
        manager = JobPhaseManager()
        manager.start_job("Hegemony Convoy", "assault")
        manager.add_complication("Witnesses")
        manager.add_complication("Navy patrol responded")
        result_complicated = manager.resolve_job(crew_tier=2, target_tier=3)

        # Start a clean job at same tier
        manager.start_job("Hegemony Convoy", "assault")
        result_clean = manager.resolve_job(crew_tier=2, target_tier=3)

        assert result_complicated["heat"] > result_clean["heat"]

    def test_resolve_job_clears_current_job(self):
        manager = JobPhaseManager()
        manager.start_job("Target", "assault")
        manager.resolve_job(crew_tier=1, target_tier=2)
        assert manager.current_job is None

    def test_resolve_job_with_no_active_job_returns_error(self):
        manager = JobPhaseManager()
        result = manager.resolve_job()
        assert "error" in result

    def test_job_state_to_dict_round_trip(self):
        job = JobState(
            target="The Agony",
            plan_type="social",
            detail="Pose as merchants",
            complications=["Cover blown"],
            cred_earned=3,
        )
        data = job.to_dict()
        job2 = JobState.from_dict(data)
        assert job2.target == "The Agony"
        assert job2.plan_type == "social"
        assert "Cover blown" in job2.complications
        assert job2.cred_earned == 3

    def test_manager_to_dict_round_trip_with_active_job(self):
        manager = JobPhaseManager()
        manager.start_job("Cobalt Wolves", "assault")
        manager.add_complication("They had backup")
        data = manager.to_dict()
        manager2 = JobPhaseManager.from_dict(data)
        assert manager2.current_job is not None
        assert manager2.current_job.target == "Cobalt Wolves"
        assert "They had backup" in manager2.current_job.complications

    def test_manager_to_dict_round_trip_no_job(self):
        manager = JobPhaseManager()
        data = manager.to_dict()
        manager2 = JobPhaseManager.from_dict(data)
        assert manager2.current_job is None


# =========================================================================
# JUMP PLANNING
# =========================================================================

class TestJumpPlanning:
    """Test jump_planning roll outcomes."""

    def test_returns_required_keys(self):
        result = jump_planning("Aleph System", nav_dots=2, rng=_rng(42))
        assert "outcome" in result
        assert "dice" in result
        assert "destination" in result
        assert "description" in result
        assert "mishap" in result

    def test_destination_preserved(self):
        result = jump_planning("Rin's World", nav_dots=1, rng=_rng(1))
        assert result["destination"] == "Rin's World"

    def test_mishap_on_low_roll(self):
        found_mishap = False
        for seed in range(500):
            result = jump_planning("Brekk", nav_dots=0, rng=random.Random(seed))
            if result["mishap"] is True:
                assert result["outcome"] == "mishap"
                found_mishap = True
                break
        assert found_mishap

    def test_excellent_on_high_roll(self):
        found_excellent = False
        for seed in range(500):
            result = jump_planning("Deep Space", nav_dots=4, rng=random.Random(seed))
            if result["outcome"] == "excellent":
                assert result["mishap"] is False
                found_excellent = True
                break
        assert found_excellent

    def test_clean_jump_is_not_mishap(self):
        found_clean = False
        for seed in range(500):
            result = jump_planning("Procyon", nav_dots=2, rng=random.Random(seed))
            if result["outcome"] == "clean":
                assert result["mishap"] is False
                found_clean = True
                break
        assert found_clean

    def test_zero_nav_dots_uses_two_dice(self):
        result = jump_planning("Unknown", nav_dots=0, rng=_rng(7))
        assert len(result["dice"]) == 2

    def test_high_nav_dots_uses_correct_dice(self):
        result = jump_planning("Aleph", nav_dots=3, rng=_rng(1))
        assert len(result["dice"]) == 3


# =========================================================================
# SAV ENGINE SAVE/LOAD
# =========================================================================

class TestSaVEngineSaveLoad:
    """Full round-trip save/load with subsystem state."""

    def test_save_state_includes_subsystem_keys(self):
        engine = _make_engine()
        engine._get_ship_state()  # Force init
        engine._get_job_manager()  # Force init
        data = engine.save_state()
        assert "ship_state" in data
        assert "job_manager" in data

    def test_save_state_includes_party(self):
        engine = _make_engine()
        data = engine.save_state()
        assert len(data["party"]) == 1
        assert data["party"][0]["name"] == "Vex"

    def test_load_state_restores_party(self):
        engine = _make_engine()
        data = engine.save_state()
        engine2 = SaVEngine()
        engine2.load_state(data)
        assert len(engine2.party) == 1
        assert engine2.party[0].name == "Vex"
        assert engine2.character.name == "Vex"

    def test_load_state_restores_ship_state(self):
        engine = _make_engine()
        ship = engine._get_ship_state()
        ship.gambits = 3
        ship.systems["weapons"] = 1
        ship.installed_modules.append("Medical Bay")
        data = engine.save_state()

        engine2 = SaVEngine()
        engine2.load_state(data)
        ship2 = engine2._get_ship_state()
        assert ship2.gambits == 3
        assert ship2.systems["weapons"] == 1
        assert "Medical Bay" in ship2.installed_modules

    def test_load_state_restores_active_job(self):
        engine = _make_engine()
        manager = engine._get_job_manager()
        manager.start_job("Nightspeakers", "mystic")
        manager.add_complication("Void resonance detected")
        data = engine.save_state()

        engine2 = SaVEngine()
        engine2.load_state(data)
        manager2 = engine2._get_job_manager()
        assert manager2.current_job is not None
        assert manager2.current_job.target == "Nightspeakers"
        assert "Void resonance detected" in manager2.current_job.complications

    def test_load_state_without_subsystems_doesnt_crash(self):
        """Old save files without ship_state/job_manager keys must still load."""
        engine = _make_engine()
        data = engine.save_state()
        data.pop("ship_state", None)
        data.pop("job_manager", None)

        engine2 = SaVEngine()
        engine2.load_state(data)
        assert engine2._ship_state is None
        assert engine2._job_manager is None

    def test_heat_rep_coin_round_trip(self):
        engine = _make_engine()
        engine.heat = 3
        engine.rep = 5
        engine.coin = 7
        data = engine.save_state()
        engine2 = SaVEngine()
        engine2.load_state(data)
        assert engine2.heat == 3
        assert engine2.rep == 5
        assert engine2.coin == 7

    def test_stress_clock_round_trip(self):
        engine = _make_engine()
        engine.stress_clocks["Vex"].push(4)
        data = engine.save_state()
        engine2 = SaVEngine()
        engine2.load_state(data)
        assert engine2.stress_clocks["Vex"].current_stress == 4

    def test_character_to_dict_from_dict(self):
        char = SaVCharacter(name="Mira", playbook="Speaker", heritage="Syndicate",
                             helm=2, scrap=1, sway=3)
        data = char.to_dict()
        char2 = SaVCharacter.from_dict(data)
        assert char2.name == "Mira"
        assert char2.playbook == "Speaker"
        assert char2.helm == 2
        assert char2.sway == 3


# =========================================================================
# COMMAND DISPATCH
# =========================================================================

class TestSaVCommandDispatch:
    """Verify all handle_command entries return strings."""

    def test_trace_fact_returns_string(self):
        engine = _make_engine()
        result = engine.handle_command("trace_fact", fact="ship systems")
        assert isinstance(result, str)

    def test_ship_status_returns_ship_info(self):
        engine = _make_engine()
        result = engine.handle_command("ship_status")
        assert isinstance(result, str)
        assert "Ship" in result

    def test_crew_status_returns_crew_info(self):
        engine = _make_engine()
        result = engine.handle_command("crew_status")
        assert isinstance(result, str)
        assert "Stress" in result or "Vex" in result

    def test_roll_action_returns_dice_result(self):
        engine = _make_engine()
        result = engine.handle_command("roll_action", action="helm")
        assert isinstance(result, str)
        assert "Dice" in result or "dice" in result.lower()

    def test_ship_upgrade_requires_module_arg(self):
        engine = _make_engine()
        result = engine.handle_command("ship_upgrade")
        assert "module" in result.lower() or "Specify" in result

    def test_ship_upgrade_with_valid_module(self):
        engine = _make_engine()
        result = engine.handle_command("ship_upgrade", module="Medical Bay")
        assert isinstance(result, str)
        assert "installed" in result.lower() or "Medical Bay" in result

    def test_ship_combat_returns_outcome(self):
        engine = _make_engine()
        result = engine.handle_command("ship_combat", system="weapons")
        assert isinstance(result, str)
        assert "Outcome" in result or "outcome" in result.lower()

    def test_ship_repair_returns_result(self):
        engine = _make_engine()
        ship = engine._get_ship_state()
        ship.systems["hull"] = 1
        result = engine.handle_command("ship_repair", system="hull", mechanic_dots=2)
        assert isinstance(result, str)

    def test_install_module_command(self):
        engine = _make_engine()
        result = engine.handle_command("install_module", module="Fake Transponder")
        assert isinstance(result, str)
        assert "Fake Transponder" in result or "installed" in result.lower()

    def test_use_gambit_command(self):
        engine = _make_engine()
        ship = engine._get_ship_state()
        ship.gambits = 2
        result = engine.handle_command("use_gambit")
        assert isinstance(result, str)
        assert "gambit" in result.lower()

    def test_set_course_command(self):
        engine = _make_engine()
        result = engine.handle_command("set_course", destination="Rin's World", nav_dots=2)
        assert isinstance(result, str)
        assert "Rin's World" in result

    def test_jump_command_alias(self):
        engine = _make_engine()
        result = engine.handle_command("jump", destination="Aleph System", nav_dots=1)
        assert isinstance(result, str)
        assert "Aleph System" in result

    def test_engagement_command_starts_job(self):
        engine = _make_engine()
        result = engine.handle_command(
            "engagement", target="The Agony", plan_type="assault"
        )
        assert isinstance(result, str)
        assert "The Agony" in result

    def test_resolve_job_after_engagement(self):
        engine = _make_engine()
        engine.handle_command("engagement", target="Cobalt Wolves", plan_type="assault")
        result = engine.handle_command("resolve_job", target_tier=2)
        assert isinstance(result, str)
        # Should show cred/rep/heat
        assert "cred" in result.lower() or "heat" in result.lower() or "rep" in result.lower()

    def test_resolve_job_without_active_job(self):
        engine = _make_engine()
        result = engine.handle_command("resolve_job", target_tier=2)
        assert isinstance(result, str)
        assert "No active job" in result or "error" in result.lower()

    def test_unknown_command_returns_error(self):
        engine = _make_engine()
        result = engine.handle_command("fire_photon_torpedoes")
        assert "Unknown" in result

    def test_sav_commands_dict_has_all_dispatched_commands(self):
        from codex.games.sav import SAV_COMMANDS, SAV_CATEGORIES
        # All category entries must be in SAV_COMMANDS
        for category, cmds in SAV_CATEGORIES.items():
            for cmd in cmds:
                assert cmd in SAV_COMMANDS, f"Category '{category}' cmd '{cmd}' not in SAV_COMMANDS"

    def test_sav_categories_cover_ship_and_jobs_and_crew(self):
        from codex.games.sav import SAV_CATEGORIES
        assert "Ship" in SAV_CATEGORIES
        assert "Jobs" in SAV_CATEGORIES
        assert "Crew" in SAV_CATEGORIES

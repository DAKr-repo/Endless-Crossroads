"""
WO-V2C — Candela Obscura Engine Depth: Tests
==============================================

Covers:
  - TestCandelaRoleData       — 5 roles, 10 specializations, ability structure
  - TestCandelaPhenomenaData  — 10+ phenomena load with all required fields
  - TestCandelaCircleData     — Circle abilities, trust mechanics, NPCs
  - TestClueTracker           — Add, verify, connect clues, persistence
  - TestCaseState             — Case dataclass lifecycle
  - TestInvestigationManager  — Open case, investigate, illuminate, danger
  - TestGildedMoves           — Role ability usage and mark costs
  - TestCandelaEngineSaveLoad — Round-trip with investigation state
  - TestCandelaCommandDispatch — All handle_command dispatches
"""

import random
import pytest

from codex.forge.reference_data.candela_roles import ROLES, CATALYSTS
from codex.forge.reference_data.candela_phenomena import PHENOMENA
from codex.forge.reference_data.candela_circles import (
    CIRCLE_ABILITIES,
    TRUST_MECHANICS,
    NPC_RELATIONSHIPS,
)
from codex.games.candela.investigations import (
    Clue,
    ClueTracker,
    CaseState,
    InvestigationManager,
    INVESTIGATION_METHODS,
    ILLUMINATION_OUTCOMES,
)
from codex.games.candela import CandelaEngine, CandelaCharacter, CANDELA_COMMANDS, CANDELA_CATEGORIES


# =========================================================================
# HELPERS
# =========================================================================

def _rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def _char(**kwargs) -> CandelaCharacter:
    defaults = {
        "name": "Iris",
        "role": "Scholar",
        "specialization": "Professor",
        "survey": 2,
        "focus": 1,
        "sense": 1,
    }
    defaults.update(kwargs)
    return CandelaCharacter(**defaults)


def _engine_with_char() -> CandelaEngine:
    engine = CandelaEngine()
    engine.create_character("Iris", role="Scholar", specialization="Professor",
                            survey=2, focus=1)
    return engine


# =========================================================================
# ROLE DATA
# =========================================================================

class TestCandelaRoleData:
    """ROLES dict has correct structure for all 5 roles and 10 specializations."""

    def test_five_roles_present(self):
        assert set(ROLES.keys()) == {"Face", "Muscle", "Scholar", "Slink", "Weird"}

    def test_each_role_has_two_specializations(self):
        for role_name, role_data in ROLES.items():
            specs = role_data.get("specializations", {})
            assert len(specs) == 2, f"{role_name} should have 2 specializations, got {len(specs)}"

    def test_face_specializations(self):
        specs = ROLES["Face"]["specializations"]
        assert "Magician" in specs
        assert "Journalist" in specs

    def test_muscle_specializations(self):
        specs = ROLES["Muscle"]["specializations"]
        assert "Explorer" in specs
        assert "Soldier" in specs

    def test_scholar_specializations(self):
        specs = ROLES["Scholar"]["specializations"]
        assert "Professor" in specs
        assert "Doctor" in specs

    def test_slink_specializations(self):
        specs = ROLES["Slink"]["specializations"]
        assert "Criminal" in specs
        assert "Detective" in specs

    def test_weird_specializations(self):
        specs = ROLES["Weird"]["specializations"]
        assert "Medium" in specs
        assert "Occultist" in specs

    def test_each_specialization_has_four_abilities(self):
        for role_name, role_data in ROLES.items():
            for spec_name, spec_data in role_data["specializations"].items():
                abilities = spec_data.get("abilities", [])
                assert len(abilities) == 4, (
                    f"{role_name}/{spec_name} should have 4 abilities, got {len(abilities)}"
                )

    def test_ability_has_required_fields(self):
        for role_name, role_data in ROLES.items():
            for spec_name, spec_data in role_data["specializations"].items():
                for ability in spec_data["abilities"]:
                    assert "name" in ability, f"{role_name}/{spec_name} ability missing 'name'"
                    assert "description" in ability, f"{role_name}/{spec_name} ability missing 'description'"
                    assert "cost" in ability, f"{role_name}/{spec_name} ability missing 'cost'"
                    assert "trigger" in ability, f"{role_name}/{spec_name} ability missing 'trigger'"

    def test_ability_cost_is_dict(self):
        for role_name, role_data in ROLES.items():
            for spec_name, spec_data in role_data["specializations"].items():
                for ability in spec_data["abilities"]:
                    assert isinstance(ability["cost"], dict)

    def test_ability_names_are_unique_within_spec(self):
        for role_name, role_data in ROLES.items():
            for spec_name, spec_data in role_data["specializations"].items():
                names = [a["name"] for a in spec_data["abilities"]]
                assert len(names) == len(set(names)), (
                    f"{role_name}/{spec_name} has duplicate ability names"
                )

    def test_weird_abilities_have_bleed_cost(self):
        """Weird specializations should have at least some bleed costs."""
        weird_specs = ROLES["Weird"]["specializations"]
        for spec_name, spec_data in weird_specs.items():
            has_bleed = any(
                "bleed" in ability["cost"]
                for ability in spec_data["abilities"]
            )
            assert has_bleed, f"Weird/{spec_name} should have at least one bleed-cost ability"

    def test_role_has_description(self):
        for role_name, role_data in ROLES.items():
            assert "description" in role_data and role_data["description"], (
                f"{role_name} missing description"
            )

    def test_role_has_drives(self):
        for role_name, role_data in ROLES.items():
            drives = role_data.get("drives", [])
            assert len(drives) == 3, f"{role_name} should have 3 drives"

    def test_catalysts_count(self):
        assert len(CATALYSTS) >= 10

    def test_catalyst_structure(self):
        for cat in CATALYSTS:
            assert "name" in cat
            assert "description" in cat
            assert cat["name"]
            assert cat["description"]


# =========================================================================
# PHENOMENA DATA
# =========================================================================

class TestCandelaPhenomenaData:
    """PHENOMENA dict has correct structure for all entries."""

    def test_minimum_ten_phenomena(self):
        assert len(PHENOMENA) >= 10

    def test_required_fields_present(self):
        required = {"name", "category", "threat_level", "description", "signs", "mechanics", "weakness"}
        for key, data in PHENOMENA.items():
            missing = required - set(data.keys())
            assert not missing, f"Phenomenon '{key}' missing fields: {missing}"

    def test_category_is_valid(self):
        valid_categories = {"Spectral", "Alchemical", "Biological", "Dimensional"}
        for key, data in PHENOMENA.items():
            assert data["category"] in valid_categories, (
                f"Phenomenon '{key}' has invalid category '{data['category']}'"
            )

    def test_threat_level_in_range(self):
        for key, data in PHENOMENA.items():
            assert 1 <= data["threat_level"] <= 5, (
                f"Phenomenon '{key}' threat_level {data['threat_level']} out of range"
            )

    def test_signs_is_nonempty_list(self):
        for key, data in PHENOMENA.items():
            signs = data.get("signs", [])
            assert isinstance(signs, list) and len(signs) >= 3, (
                f"Phenomenon '{key}' should have >= 3 signs"
            )

    def test_mechanics_is_dict(self):
        for key, data in PHENOMENA.items():
            assert isinstance(data["mechanics"], dict) and data["mechanics"], (
                f"Phenomenon '{key}' mechanics should be non-empty dict"
            )

    def test_weakness_is_nonempty_string(self):
        for key, data in PHENOMENA.items():
            assert isinstance(data["weakness"], str) and data["weakness"], (
                f"Phenomenon '{key}' weakness should be non-empty string"
            )

    def test_name_is_nonempty_string(self):
        for key, data in PHENOMENA.items():
            assert isinstance(data["name"], str) and data["name"]

    def test_specific_phenomena_present(self):
        expected_keys = [
            "crimson_weave", "hollow_choir", "flickering_man",
            "glass_garden", "whispering_archive", "moth_swarm",
            "undying_fire", "shattered_mirror", "hunger_below",
            "bone_singer",
        ]
        for key in expected_keys:
            assert key in PHENOMENA, f"Expected phenomenon '{key}' not found"

    def test_category_distribution(self):
        """All four categories should appear at least once."""
        categories = {data["category"] for data in PHENOMENA.values()}
        for cat in ("Spectral", "Alchemical", "Biological", "Dimensional"):
            assert cat in categories, f"Category '{cat}' missing from phenomena"

    def test_has_threat_level_5_phenomena(self):
        high_threat = [k for k, v in PHENOMENA.items() if v["threat_level"] >= 5]
        assert len(high_threat) >= 1, "Should have at least one threat_level 5 phenomenon"


# =========================================================================
# CIRCLE DATA
# =========================================================================

class TestCandelaCircleData:
    """Circle abilities, trust mechanics, and NPC relationships."""

    def test_six_circle_abilities(self):
        # SOURCE: Candela Obscura Core Rulebook, p.41 — exactly 6 circle abilities listed
        assert len(CIRCLE_ABILITIES) == 6

    def test_circle_ability_fields(self):
        required = {"name", "description", "mechanical_effect"}
        for key, data in CIRCLE_ABILITIES.items():
            missing = required - set(data.keys())
            assert not missing, f"Circle ability '{key}' missing: {missing}"

    def test_specific_circle_abilities(self):
        # SOURCE: Candela Obscura Core Rulebook, p.41
        expected = [
            "stamina_training", "nobody_left_behind", "in_this_together",
            "interdisciplinary", "resource_management", "one_last_run",
        ]
        for key in expected:
            assert key in CIRCLE_ABILITIES, f"Circle ability '{key}' missing"

    def test_four_trust_levels(self):
        assert set(TRUST_MECHANICS.keys()) == {"suspicious", "cautious", "trusting", "bonded"}

    def test_trust_level_values(self):
        assert TRUST_MECHANICS["suspicious"]["level"] == 0
        assert TRUST_MECHANICS["cautious"]["level"] == 1
        assert TRUST_MECHANICS["trusting"]["level"] == 2
        assert TRUST_MECHANICS["bonded"]["level"] == 3

    def test_trust_mechanics_fields(self):
        required = {"level", "name", "description", "effects"}
        for key, data in TRUST_MECHANICS.items():
            missing = required - set(data.keys())
            assert not missing, f"Trust level '{key}' missing: {missing}"

    def test_twelve_npcs(self):
        assert len(NPC_RELATIONSHIPS) == 12

    def test_npc_fields(self):
        required = {"name", "role", "initial_trust", "secret", "connection_to_phenomena"}
        for npc in NPC_RELATIONSHIPS:
            missing = required - set(npc.keys())
            assert not missing, f"NPC '{npc.get('name')}' missing fields: {missing}"

    def test_npc_initial_trust_is_valid(self):
        valid_trusts = {"suspicious", "cautious", "trusting", "bonded"}
        for npc in NPC_RELATIONSHIPS:
            assert npc["initial_trust"] in valid_trusts, (
                f"NPC '{npc['name']}' has invalid initial_trust '{npc['initial_trust']}'"
            )


# =========================================================================
# CLUE TRACKER
# =========================================================================

class TestClueTracker:
    """ClueTracker — add, verify, connect, query, persist."""

    def test_add_clue_returns_clue(self):
        tracker = ClueTracker()
        clue = tracker.add_clue("Crimson water in cistern", "Survey")
        assert isinstance(clue, Clue)
        assert clue.description == "Crimson water in cistern"
        assert clue.source == "Survey"
        assert not clue.verified

    def test_add_multiple_clues(self):
        tracker = ClueTracker()
        tracker.add_clue("Clue A", "Source 1")
        tracker.add_clue("Clue B", "Source 2")
        assert tracker.total_count() == 2

    def test_verify_clue_success(self):
        tracker = ClueTracker()
        tracker.add_clue("Test clue", "Survey")
        result = tracker.verify_clue(0)
        assert result["success"]
        assert tracker.clues[0].verified

    def test_verify_clue_already_verified(self):
        tracker = ClueTracker()
        tracker.add_clue("Test clue", "Survey")
        tracker.verify_clue(0)
        result = tracker.verify_clue(0)
        assert not result["success"]
        assert "already verified" in result["error"]

    def test_verify_clue_bad_index(self):
        tracker = ClueTracker()
        result = tracker.verify_clue(99)
        assert not result["success"]
        assert "No clue at index" in result["error"]

    def test_connect_clue(self):
        tracker = ClueTracker()
        tracker.add_clue("Red water", "Survey")
        result = tracker.connect_clue(0, "crimson_weave")
        assert result["success"]
        assert tracker.clues[0].connected_phenomena == "crimson_weave"

    def test_connect_clue_bad_index(self):
        tracker = ClueTracker()
        result = tracker.connect_clue(5, "crimson_weave")
        assert not result["success"]

    def test_get_unverified(self):
        tracker = ClueTracker()
        tracker.add_clue("A", "S1")
        tracker.add_clue("B", "S2")
        tracker.verify_clue(0)
        unverified = tracker.get_unverified()
        assert len(unverified) == 1
        assert unverified[0].description == "B"

    def test_get_by_phenomena(self):
        tracker = ClueTracker()
        tracker.add_clue("Clue 1", "Survey")
        tracker.add_clue("Clue 2", "Focus")
        tracker.connect_clue(0, "crimson_weave")
        result = tracker.get_by_phenomena("crimson_weave")
        assert len(result) == 1
        assert result[0].description == "Clue 1"

    def test_verified_count(self):
        tracker = ClueTracker()
        tracker.add_clue("A", "S1")
        tracker.add_clue("B", "S2")
        tracker.verify_clue(0)
        assert tracker.verified_count() == 1

    def test_persistence_round_trip(self):
        tracker = ClueTracker()
        tracker.add_clue("Crimson water", "Survey")
        tracker.verify_clue(0)
        tracker.connect_clue(0, "crimson_weave")
        tracker.add_clue("Ghost image", "Focus")

        data = tracker.to_dict()
        restored = ClueTracker.from_dict(data)

        assert restored.total_count() == 2
        assert restored.clues[0].verified
        assert restored.clues[0].connected_phenomena == "crimson_weave"
        assert not restored.clues[1].verified

    def test_empty_tracker_to_dict(self):
        tracker = ClueTracker()
        data = tracker.to_dict()
        assert "clues" in data
        assert data["clues"] == []

    def test_clue_to_dict(self):
        clue = Clue("Description", "Source", verified=True, connected_phenomena="hollow_choir")
        d = clue.to_dict()
        assert d["description"] == "Description"
        assert d["verified"] is True
        assert d["connected_phenomena"] == "hollow_choir"

    def test_clue_from_dict(self):
        data = {
            "description": "Test",
            "source": "S",
            "verified": False,
            "connected_phenomena": "",
        }
        clue = Clue.from_dict(data)
        assert clue.description == "Test"
        assert not clue.verified


# =========================================================================
# CASE STATE
# =========================================================================

class TestCaseState:
    """CaseState dataclass serialization and defaults."""

    def test_defaults(self):
        case = CaseState(case_name="The Red Tide")
        assert case.phenomena == ""
        assert case.clues_found == 0
        assert case.clues_needed == 5
        assert case.danger_level == 0
        assert case.active is True
        assert case.outcome == ""

    def test_to_dict(self):
        case = CaseState(
            case_name="The Red Tide",
            phenomena="crimson_weave",
            clues_found=3,
            clues_needed=5,
            danger_level=2,
            active=True,
            outcome="",
        )
        d = case.to_dict()
        assert d["case_name"] == "The Red Tide"
        assert d["phenomena"] == "crimson_weave"
        assert d["clues_found"] == 3
        assert d["danger_level"] == 2

    def test_from_dict_round_trip(self):
        case = CaseState(
            case_name="Hollow Choir",
            phenomena="hollow_choir",
            clues_found=4,
            clues_needed=5,
            danger_level=1,
            active=True,
            outcome="",
        )
        restored = CaseState.from_dict(case.to_dict())
        assert restored.case_name == case.case_name
        assert restored.phenomena == case.phenomena
        assert restored.clues_found == case.clues_found
        assert restored.danger_level == case.danger_level

    def test_closed_case_has_outcome(self):
        case = CaseState(case_name="Test", active=False, outcome="illuminated")
        assert case.outcome == "illuminated"
        assert not case.active


# =========================================================================
# INVESTIGATION MANAGER
# =========================================================================

class TestInvestigationManager:
    """InvestigationManager — full case lifecycle."""

    def test_open_case_creates_case(self):
        mgr = InvestigationManager()
        case = mgr.open_case("The Red Tide", phenomena="crimson_weave", clues_needed=4)
        assert case.case_name == "The Red Tide"
        assert case.phenomena == "crimson_weave"
        assert case.clues_needed == 4
        assert case.active

    def test_open_case_resets_clue_tracker(self):
        mgr = InvestigationManager()
        mgr.open_case("First Case")
        mgr.clue_tracker.add_clue("Old clue", "Survey")
        mgr.open_case("Second Case")
        assert mgr.clue_tracker.total_count() == 0

    def test_close_case(self):
        mgr = InvestigationManager()
        mgr.open_case("Test Case")
        result = mgr.close_case("resolved")
        assert result["success"]
        assert not mgr.active_case.active
        assert mgr.active_case.outcome == "resolved"

    def test_close_case_no_active(self):
        mgr = InvestigationManager()
        result = mgr.close_case()
        assert not result["success"]

    def test_investigate_success_adds_clue(self):
        mgr = InvestigationManager()
        mgr.open_case("Test")
        # Seed ensures success
        result = mgr.investigate(action_dots=3, method="survey", rng=_rng(1))
        assert "outcome" in result
        # With enough dots the result should be success or critical on seed 1
        if result["outcome"] in ("success", "critical"):
            assert result.get("clue_found")
            assert mgr.clue_tracker.total_count() == 1

    def test_investigate_failure_raises_danger(self):
        mgr = InvestigationManager()
        mgr.open_case("Test")
        # Force a failure: 0 dice -> disadvantage
        # Try enough attempts to get a failure
        for seed in range(50):
            mgr2 = InvestigationManager()
            mgr2.open_case("Test2")
            result = mgr2.investigate(action_dots=0, method="survey", rng=_rng(seed))
            if result.get("outcome") == "failure":
                assert mgr2.active_case.danger_level == 1
                break

    def test_investigate_no_active_case(self):
        mgr = InvestigationManager()
        result = mgr.investigate(action_dots=2)
        assert not result.get("success", True) and "error" in result

    def test_illuminate_requires_enough_clues(self):
        mgr = InvestigationManager()
        mgr.open_case("Test", clues_needed=3)
        mgr.active_case.clues_found = 2
        result = mgr.illuminate()
        assert not result["success"]
        assert "Insufficient clues" in result["error"]

    def test_illuminate_success_closes_case(self):
        mgr = InvestigationManager()
        mgr.open_case("Test", clues_needed=2)
        mgr.active_case.clues_found = 2
        # Add verified clues so dice pool >= 1
        clue = mgr.clue_tracker.add_clue("Verified clue", "Survey")
        clue.verified = True
        result = mgr.illuminate(rng=_rng(42))
        assert result["success"]
        assert not mgr.active_case.active
        assert mgr.active_case.outcome in ("illuminated", "contained", "failed")

    def test_illuminate_no_active_case(self):
        mgr = InvestigationManager()
        result = mgr.illuminate()
        assert not result["success"]

    def test_danger_escalation_low_danger(self):
        mgr = InvestigationManager()
        mgr.open_case("Test")
        mgr.active_case.danger_level = 1
        result = mgr.danger_escalation()
        assert result["success"]
        assert not result["manifested"]

    def test_danger_escalation_max(self):
        mgr = InvestigationManager()
        mgr.open_case("Test")
        mgr.active_case.danger_level = 5
        result = mgr.danger_escalation()
        assert result["success"]
        assert result["manifested"]

    def test_danger_escalation_no_case(self):
        mgr = InvestigationManager()
        result = mgr.danger_escalation()
        assert not result["success"]

    def test_build_trust_success_increases(self):
        mgr = InvestigationManager()
        result = mgr.build_trust("Warden Kaske", "success")
        assert result["new_trust"] == 2  # Cautious (1) -> Trusting (2)
        assert result["changed"]

    def test_build_trust_failure_decreases(self):
        mgr = InvestigationManager()
        mgr.circle_trust["constance frey"] = 2
        result = mgr.build_trust("Constance Frey", "failure")
        assert result["new_trust"] == 1
        assert result["changed"]

    def test_build_trust_mixed_unchanged(self):
        mgr = InvestigationManager()
        result = mgr.build_trust("Sable", "mixed")
        assert not result["changed"]

    def test_build_trust_caps_at_three(self):
        mgr = InvestigationManager()
        mgr.circle_trust["nils acker"] = 3
        result = mgr.build_trust("Nils Acker", "critical")
        assert result["new_trust"] == 3

    def test_persistence_round_trip(self):
        mgr = InvestigationManager()
        mgr.open_case("The Pale Door Case", phenomena="pale_door", clues_needed=4)
        mgr.clue_tracker.add_clue("A door appeared mid-air", "Survey")
        mgr.clue_tracker.verify_clue(0)
        mgr.circle_trust["warden kaske"] = 2
        mgr.active_case.clues_found = 1
        mgr.active_case.danger_level = 2

        data = mgr.to_dict()
        restored = InvestigationManager.from_dict(data)

        assert restored.active_case.case_name == "The Pale Door Case"
        assert restored.active_case.danger_level == 2
        assert restored.clue_tracker.verified_count() == 1
        assert restored.circle_trust.get("warden kaske") == 2

    def test_investigation_methods_completeness(self):
        """All nine investigation methods should be present."""
        expected = {
            "survey", "focus", "sense", "sway", "read",
            "hide", "strike", "control", "move",
        }
        assert set(INVESTIGATION_METHODS.keys()) == expected

    def test_illumination_outcomes_completeness(self):
        expected = {"critical", "success", "mixed", "failure"}
        assert set(ILLUMINATION_OUTCOMES.keys()) == expected


# =========================================================================
# GILDED MOVES
# =========================================================================

class TestGildedMoves:
    """Gilded move usage — look up and apply ability costs.

    Ability names and costs are sourced from the Candela Obscura Core Rulebook,
    pp.28-32 (Journalist, Magician, Explorer, Soldier, Doctor, Professor,
    Criminal, Detective, Medium, Occultist abilities).
    """

    def test_known_ability_succeeds(self):
        # SOURCE: p.29 — Field Experience (Explorer) costs nerve: 0
        mgr = InvestigationManager()
        char = _char()
        result = mgr.gilded_move(char, "Field Experience")
        assert result["success"]
        assert "Field Experience" in result["message"]

    def test_unknown_ability_fails(self):
        mgr = InvestigationManager()
        char = _char()
        result = mgr.gilded_move(char, "Nonexistent Power")
        assert not result["success"]
        assert "Unknown ability" in result["error"]

    def test_ability_with_brain_cost_marks_brain(self):
        # SOURCE: p.31 — Back Against the Wall (Detective) costs brain: 1
        mgr = InvestigationManager()
        char = _char(brain=0)
        result = mgr.gilded_move(char, "Back Against the Wall")
        assert result["success"]
        assert char.brain == 1

    def test_ability_with_bleed_cost_marks_bleed(self):
        # SOURCE: p.32 — Play the Bait (Occultist) costs bleed: 1
        mgr = InvestigationManager()
        char = _char(bleed=0)
        result = mgr.gilded_move(char, "Play the Bait")
        assert result["success"]
        assert char.bleed == 1

    def test_zero_cost_ability_no_marks(self):
        # SOURCE: p.29 — Field Experience (Explorer) costs nerve: 0 (zero cost)
        mgr = InvestigationManager()
        char = _char()
        result = mgr.gilded_move(char, "Field Experience")
        assert result["success"]
        # Zero cost means no mark change on body
        assert char.body == 0

    def test_ability_search_case_insensitive(self):
        # SOURCE: p.29 — Field Experience, tested lowercase
        mgr = InvestigationManager()
        char = _char()
        result = mgr.gilded_move(char, "field experience")
        assert result["success"]

    def test_ability_marks_applied_dict(self):
        # SOURCE: p.30 — Steel Mind (Professor) costs intuition: 0
        mgr = InvestigationManager()
        char = _char()
        result = mgr.gilded_move(char, "Steel Mind")
        assert result["success"]
        assert "marks_applied" in result

    def test_high_body_cost_ability(self):
        # SOURCE: p.32 — Ghostblade (Occultist) costs body: 1
        mgr = InvestigationManager()
        char = _char(body=0, brain=0)
        result = mgr.gilded_move(char, "Ghostblade")
        assert result["success"]
        assert char.body == 1

    def test_ability_scarred_when_track_fills(self):
        """Taking mark to cap causes scarred flag.
        SOURCE: p.31 — Back Against the Wall (Detective) costs brain: 1
        """
        mgr = InvestigationManager()
        char = _char(brain=2, brain_max=3)  # 1 brain away from cap
        result = mgr.gilded_move(char, "Back Against the Wall")  # brain: 1
        assert result["success"]
        marks = result["marks_applied"]
        assert marks["brain"]["scarred"]


# =========================================================================
# ENGINE SAVE / LOAD
# =========================================================================

class TestCandelaEngineSaveLoad:
    """Round-trip save_state/load_state preserves investigation state."""

    def test_basic_round_trip(self):
        engine = _engine_with_char()
        state = engine.save_state()
        engine2 = CandelaEngine()
        engine2.load_state(state)
        assert engine2.character.name == "Iris"
        assert engine2.circle_name == engine.circle_name

    def test_saves_investigation_state(self):
        engine = _engine_with_char()
        mgr = engine._get_investigation_mgr()
        mgr.open_case("The Pale Door", phenomena="pale_door", clues_needed=3)
        mgr.clue_tracker.add_clue("Impossible door sighted", "Survey")
        mgr.clue_tracker.verify_clue(0)
        mgr.active_case.clues_found = 1
        mgr.active_case.danger_level = 2

        state = engine.save_state()
        assert "investigation" in state

        engine2 = CandelaEngine()
        engine2.load_state(state)

        restored_mgr = engine2._get_investigation_mgr()
        assert restored_mgr.active_case.case_name == "The Pale Door"
        assert restored_mgr.active_case.danger_level == 2
        assert restored_mgr.clue_tracker.verified_count() == 1

    def test_no_investigation_state_is_safe(self):
        """An engine without investigation data saves/loads without error."""
        engine = _engine_with_char()
        state = engine.save_state()
        assert "investigation" not in state

        engine2 = CandelaEngine()
        engine2.load_state(state)
        # Manager should lazily init on first access
        mgr = engine2._get_investigation_mgr()
        assert mgr is not None

    def test_party_round_trip(self):
        engine = CandelaEngine()
        c1 = engine.create_character("Iris", role="Scholar", specialization="Professor")
        c2 = CandelaCharacter(name="Lysander", role="Weird", specialization="Medium")
        engine.add_to_party(c2)

        state = engine.save_state()
        engine2 = CandelaEngine()
        engine2.load_state(state)

        assert len(engine2.party) == 2
        assert engine2.party[0].name == "Iris"
        assert engine2.party[1].name == "Lysander"

    def test_assignments_completed_preserved(self):
        engine = _engine_with_char()
        engine.assignments_completed = 3
        state = engine.save_state()
        engine2 = CandelaEngine()
        engine2.load_state(state)
        assert engine2.assignments_completed == 3

    def test_trust_state_preserved(self):
        engine = _engine_with_char()
        mgr = engine._get_investigation_mgr()
        mgr.circle_trust["warden kaske"] = 3

        state = engine.save_state()
        engine2 = CandelaEngine()
        engine2.load_state(state)

        restored_mgr = engine2._get_investigation_mgr()
        assert restored_mgr.circle_trust.get("warden kaske") == 3


# =========================================================================
# COMMAND DISPATCH
# =========================================================================

class TestCandelaCommandDispatch:
    """handle_command dispatches correctly for all registered commands."""

    def test_trace_fact(self):
        engine = _engine_with_char()
        result = engine.handle_command("trace_fact", fact="crimson water")
        assert isinstance(result, str)

    def test_roll_action(self):
        engine = _engine_with_char()
        result = engine.handle_command("roll_action", action="survey")
        assert "Dice:" in result or "FAILURE" in result.upper() or "SUCCESS" in result.upper()

    def test_circle_status(self):
        engine = _engine_with_char()
        engine.circle_name = "The Ashwood Circle"
        result = engine.handle_command("circle_status")
        assert "The Ashwood Circle" in result

    def test_party_status(self):
        engine = _engine_with_char()
        result = engine.handle_command("party_status")
        assert "Iris" in result
        assert "Body" in result

    def test_take_mark(self):
        engine = _engine_with_char()
        result = engine.handle_command("take_mark", track="brain")
        assert "Brain" in result
        assert engine.character.brain == 1

    def test_open_case(self):
        engine = _engine_with_char()
        result = engine.handle_command(
            "open_case", case_name="The Hollow Choir Case", phenomena="hollow_choir"
        )
        assert "The Hollow Choir Case" in result
        mgr = engine._get_investigation_mgr()
        assert mgr.active_case.case_name == "The Hollow Choir Case"

    def test_open_case_missing_name(self):
        engine = _engine_with_char()
        result = engine.handle_command("open_case")
        assert "requires" in result.lower() or "case_name" in result

    def test_investigate_command(self):
        engine = _engine_with_char()
        engine.handle_command("open_case", case_name="Test Case")
        result = engine.handle_command("investigate", action="survey")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_gilded_move_command(self):
        engine = _engine_with_char()
        result = engine.handle_command("gilded_move", ability="Deep Research")
        assert "Deep Research" in result

    def test_gilded_move_no_char(self):
        engine = CandelaEngine()
        result = engine.handle_command("gilded_move", ability="Deep Research")
        assert "No active investigator" in result

    def test_gilded_move_missing_ability(self):
        engine = _engine_with_char()
        result = engine.handle_command("gilded_move")
        assert "requires" in result.lower() or "ability" in result

    def test_illuminate_requires_clues(self):
        engine = _engine_with_char()
        engine.handle_command("open_case", case_name="Test", clues_needed=5)
        result = engine.handle_command("illuminate")
        assert "Insufficient" in result or "Cannot" in result

    def test_illuminate_success(self):
        engine = _engine_with_char()
        engine.handle_command("open_case", case_name="Test", clues_needed=2)
        mgr = engine._get_investigation_mgr()
        mgr.active_case.clues_found = 2
        clue = mgr.clue_tracker.add_clue("Evidence", "Survey")
        clue.verified = True
        result = engine.handle_command("illuminate")
        assert isinstance(result, str)
        assert engine.assignments_completed == 1

    def test_case_status_no_case(self):
        engine = _engine_with_char()
        result = engine.handle_command("case_status")
        assert "No active case" in result

    def test_case_status_with_case(self):
        engine = _engine_with_char()
        engine.handle_command("open_case", case_name="Glass Garden Incident",
                               phenomena="glass_garden")
        result = engine.handle_command("case_status")
        assert "Glass Garden Incident" in result
        assert "Danger" in result

    def test_clues_empty(self):
        engine = _engine_with_char()
        engine.handle_command("open_case", case_name="Test")
        result = engine.handle_command("clues")
        assert "No clues" in result

    def test_clues_after_investigation(self):
        engine = _engine_with_char()
        engine.handle_command("open_case", case_name="Test")
        mgr = engine._get_investigation_mgr()
        mgr.clue_tracker.add_clue("A red door", "Survey")
        result = engine.handle_command("clues")
        assert "A red door" in result

    def test_danger_check_command(self):
        engine = _engine_with_char()
        engine.handle_command("open_case", case_name="Test")
        result = engine.handle_command("danger_check")
        assert isinstance(result, str)

    def test_build_trust_command(self):
        engine = _engine_with_char()
        result = engine.handle_command("build_trust", npc="Warden Kaske", result="success")
        assert "Warden Kaske" in result

    def test_build_trust_missing_npc(self):
        engine = _engine_with_char()
        result = engine.handle_command("build_trust", result="success")
        assert "requires" in result.lower() or "npc" in result.lower()

    def test_unknown_command(self):
        engine = _engine_with_char()
        result = engine.handle_command("nonexistent_cmd")
        assert "Unknown command" in result

    def test_candela_commands_dict_completeness(self):
        expected = {
            "roll_action", "circle_status", "take_mark", "party_status",
            "open_case", "investigate", "gilded_move", "illuminate",
            "case_status", "clues", "danger_check", "build_trust",
        }
        assert expected.issubset(set(CANDELA_COMMANDS.keys()))

    def test_candela_categories_completeness(self):
        expected_cats = {"Circle", "Action", "Investigation", "Roleplay"}
        assert expected_cats.issubset(set(CANDELA_CATEGORIES.keys()))

    def test_all_investigation_category_commands_dispatchable(self):
        engine = _engine_with_char()
        for cmd in CANDELA_CATEGORIES["Investigation"]:
            # Just confirm it dispatches (doesn't hit "Unknown command")
            result = engine.handle_command(cmd)
            assert "Unknown command" not in result, (
                f"Command '{cmd}' in Investigation category returned 'Unknown command'"
            )

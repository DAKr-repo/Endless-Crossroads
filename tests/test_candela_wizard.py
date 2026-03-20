#!/usr/bin/env python3
"""Tests for the Character Creation Wizard Overhaul — New Step Types + Candela Flow.

Covers: dependent_choice, point_allocate, auto_derive, ability_select step types,
full Candela schema loading, CharacterSheet FITD fields, circle creation,
and FITD stat block rendering.
"""

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codex.forge.char_wizard import (
    CharacterSheet,
    CreationSchema,
    SystemBuilder,
    CharacterBuilderEngine,
    render_stat_block_view,
)
from rich.console import Console


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_console():
    return Console(file=open(os.devnull, "w"), force_terminal=True)


def _make_schema(steps, **overrides):
    defaults = dict(
        system_id="test",
        display_name="Test System",
        genre="Test",
        stats_method="action_dots",
        stats=["Nerve", "Cunning", "Intuition"],
        view_type="stat_block",
        derived={},
        vault_path="/tmp/test_vault",
    )
    defaults.update(overrides)
    defaults["steps"] = steps
    return CreationSchema(**defaults)


def _run_builder(schema, inputs):
    con = _make_console()
    builder = SystemBuilder(schema, con)
    with patch("codex.forge.char_wizard.Prompt.ask", side_effect=inputs):
        with patch("codex.forge.char_wizard.scan_content_availability", return_value={"Core"}):
            sheet = builder.run()
    return sheet, builder


# ---------------------------------------------------------------------------
# CharacterSheet — New Fields
# ---------------------------------------------------------------------------

class TestCharacterSheetFITDFields:
    def test_fitd_fields_default_empty(self):
        sheet = CharacterSheet(system_id="candela")
        assert sheet.action_ratings == {}
        assert sheet.gilded_actions == []
        assert sheet.drives == {}
        assert sheet.resistances == {}
        assert sheet.abilities == []
        assert sheet.catalyst == ""
        assert sheet.question == ""
        assert sheet.style == ""
        assert sheet.pronouns == ""
        assert sheet.relationships == []

    def test_circle_fields_default_empty(self):
        sheet = CharacterSheet(system_id="candela")
        assert sheet.circle_name == ""
        assert sheet.circle_chapter_house == ""
        assert sheet.circle_abilities == []
        assert sheet.circle_resources == {}

    def test_summary_lines_includes_fitd_data(self):
        sheet = CharacterSheet(system_id="candela", name="Ada")
        sheet.action_ratings = {"Move": 1, "Strike": 2, "Survey": 1}
        sheet.gilded_actions = ["Survey"]
        sheet.drives = {"Nerve": 4, "Cunning": 2, "Intuition": 3}
        sheet.resistances = {"Nerve": 1, "Cunning": 0, "Intuition": 1}
        sheet.abilities = ["I Know a Guy", "Insider Access"]
        sheet.catalyst = "Lost a friend to the shadows"
        sheet.pronouns = "she/her"

        lines = sheet.summary_lines()
        text = "\n".join(lines)
        assert "Actions:" in text
        assert "Gilded:" in text
        assert "Drives:" in text
        assert "Resistances:" in text
        assert "Abilities:" in text
        assert "Catalyst:" in text
        assert "Pronouns:" in text


# ---------------------------------------------------------------------------
# dependent_choice Step Type
# ---------------------------------------------------------------------------

class TestDependentChoice:
    def test_basic_dependent_choice(self):
        steps = [
            {"id": "role", "type": "choice", "label": "Role", "prompt": "Pick",
             "options": [{"value": "Face", "label": "Face"}]},
            {"id": "specialty", "type": "dependent_choice", "label": "Specialty",
             "prompt": "Pick specialty", "depends_on": "role",
             "option_groups": {
                 "Face": [
                     {"value": "Journalist", "description": "Bold"},
                     {"value": "Magician", "description": "Entertainer"},
                 ]
             }},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "1"])
        assert sheet.choices["specialty"] == "Journalist"

    def test_dependent_choice_second_option(self):
        steps = [
            {"id": "role", "type": "choice", "label": "Role", "prompt": "Pick",
             "options": [{"value": "Muscle", "label": "Muscle"}]},
            {"id": "specialty", "type": "dependent_choice", "label": "Specialty",
             "prompt": "Pick specialty", "depends_on": "role",
             "option_groups": {
                 "Muscle": [
                     {"value": "Explorer", "description": "Daredevil"},
                     {"value": "Soldier", "description": "Warrior"},
                 ]
             }},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "2"])
        assert sheet.choices["specialty"] == "Soldier"

    def test_gilded_mode_preset_plus_choose(self):
        steps = [
            {"id": "specialty", "type": "text_input", "label": "Specialty",
             "prompt": "Specialty?"},
            {"id": "gilded_actions", "type": "dependent_choice",
             "label": "Gild Actions", "description": "Choose 1 additional",
             "depends_on": "specialty",
             "preset_gilded": {"Journalist": "Survey"},
             "choose_count": 1,
             "from": ["Move", "Strike", "Control", "Sway", "Read", "Hide", "Survey", "Focus", "Sense"]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Journalist", "1"])
        assert "Survey" in sheet.gilded_actions
        assert len(sheet.gilded_actions) == 2
        assert sheet.gilded_actions[1] == "Move"

    def test_empty_option_groups(self):
        steps = [
            {"id": "role", "type": "text_input", "label": "Role", "prompt": "?"},
            {"id": "specialty", "type": "dependent_choice", "label": "Specialty",
             "prompt": "Pick", "depends_on": "role",
             "option_groups": {"Face": [{"value": "A"}]}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Unknown"])
        # No options for "Unknown" — should silently skip
        assert "specialty" not in sheet.choices or sheet.choices.get("specialty") is None


# ---------------------------------------------------------------------------
# point_allocate Step Type
# ---------------------------------------------------------------------------

class TestPointAllocate:
    def test_basic_allocation(self):
        steps = [
            {"id": "drives", "type": "point_allocate", "label": "Drives",
             "description": "Distribute 3 points", "points": 3,
             "max_per_category": 6,
             "categories": ["Nerve", "Cunning", "Intuition"]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "1", "1"])
        assert sheet.drives["Nerve"] == 3
        assert sheet.drives["Cunning"] == 0

    def test_allocation_with_presets(self):
        steps = [
            {"id": "specialty", "type": "text_input", "label": "Spec", "prompt": "?"},
            {"id": "drives", "type": "point_allocate", "label": "Drives",
             "points": 2, "max_per_category": 6,
             "categories": ["Nerve", "Cunning", "Intuition"],
             "preset_key": "specialty",
             "presets": {"Doctor": {"Intuition": 3}}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Doctor", "1", "1"])
        assert sheet.drives["Intuition"] == 3
        assert sheet.drives["Nerve"] == 2

    def test_max_per_category(self):
        steps = [
            {"id": "action_ratings", "type": "point_allocate",
             "label": "Actions", "points": 3, "max_per_category": 2,
             "categories": ["A", "B", "C"]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "1", "1"])
        assert sheet.choices["action_ratings"]["A"] == 2
        assert sheet.choices["action_ratings"]["B"] == 1

    def test_zero_raise(self):
        steps = [
            {"id": "specialty", "type": "text_input", "label": "Spec", "prompt": "?"},
            {"id": "action_ratings", "type": "point_allocate",
             "label": "Actions", "points": 1, "max_per_category": 2,
             "zero_raise": True,
             "categories": ["Move", "Strike", "Control"],
             "preset_key": "specialty",
             "presets": {"Explorer": {"Move": 1, "Strike": 2}}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Explorer", "1", "1"])
        assert sheet.action_ratings["Control"] == 1
        assert sheet.action_ratings["Move"] == 2

    def test_stores_on_action_ratings_field(self):
        steps = [
            {"id": "action_ratings", "type": "point_allocate",
             "label": "Actions", "points": 2, "max_per_category": 2,
             "categories": ["Move", "Strike"]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "2"])
        assert sheet.action_ratings == {"Move": 1, "Strike": 1}

    def test_stores_on_drives_field(self):
        steps = [
            {"id": "drives", "type": "point_allocate",
             "label": "Drives", "points": 2, "max_per_category": 6,
             "categories": ["Nerve", "Cunning"]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "2"])
        assert sheet.drives == {"Nerve": 1, "Cunning": 1}


# ---------------------------------------------------------------------------
# auto_derive Step Type
# ---------------------------------------------------------------------------

class TestAutoDerive:
    def test_resistance_derivation(self):
        steps = [
            {"id": "drives", "type": "point_allocate", "label": "Drives",
             "points": 3, "max_per_category": 9,
             "categories": ["Nerve", "Cunning", "Intuition"]},
            {"id": "resistances", "type": "auto_derive", "label": "Resistances",
             "source": "drives", "formula": "floor(value / 3)"},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "1", "1"])
        assert sheet.resistances["Nerve"] == 1
        assert sheet.resistances["Cunning"] == 0
        assert sheet.resistances["Intuition"] == 0

    def test_resistance_higher_values(self):
        steps = [
            {"id": "drives", "type": "point_allocate", "label": "Drives",
             "points": 6, "max_per_category": 9,
             "categories": ["Nerve", "Cunning"]},
            {"id": "resistances", "type": "auto_derive", "label": "Resistances",
             "source": "drives", "formula": "floor(value / 3)"},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "1", "1", "1", "2", "2"])
        assert sheet.resistances["Nerve"] == 1
        assert sheet.resistances["Cunning"] == 0

    def test_auto_derive_stored_in_choices(self):
        steps = [
            {"id": "drives", "type": "point_allocate", "label": "Drives",
             "points": 6, "max_per_category": 9,
             "categories": ["A", "B"]},
            {"id": "resistances", "type": "auto_derive", "label": "Resistances",
             "source": "drives", "formula": "floor(value / 3)"},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "1", "1", "2", "2", "2"])
        assert sheet.choices["resistances"] == {"A": 1, "B": 1}


# ---------------------------------------------------------------------------
# ability_select Step Type
# ---------------------------------------------------------------------------

class TestAbilitySelect:
    def test_basic_ability_select(self):
        steps = [
            {"id": "role", "type": "text_input", "label": "Role", "prompt": "?"},
            {"id": "role_ability", "type": "ability_select",
             "label": "Role Ability", "count": 1, "depends_on": "role",
             "pools": {"Face": ["I Know a Guy", "Sweet Talk", "Cool Under Pressure"]}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Face", "2"])
        assert "Sweet Talk" in sheet.abilities
        assert sheet.choices["role_ability"] == ["Sweet Talk"]

    def test_no_duplicates_across_steps(self):
        steps = [
            {"id": "role", "type": "text_input", "label": "Role", "prompt": "?"},
            {"id": "role_ability", "type": "ability_select",
             "label": "Role Ability", "count": 1, "depends_on": "role",
             "pools": {"Face": ["A", "B", "C"]}},
            {"id": "spec_ability", "type": "ability_select",
             "label": "Spec Ability", "count": 1, "depends_on": "role",
             "pools": {"Face": ["A", "B", "C", "D"]}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Face", "1", "1"])
        assert sheet.abilities == ["A", "B"]

    def test_missing_pool(self):
        steps = [
            {"id": "role", "type": "text_input", "label": "Role", "prompt": "?"},
            {"id": "role_ability", "type": "ability_select",
             "label": "Role Ability", "count": 1, "depends_on": "role",
             "pools": {"Face": ["A"]}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Unknown"])
        assert sheet.abilities == []


# ---------------------------------------------------------------------------
# Candela Schema Loading
# ---------------------------------------------------------------------------

_CANDELA_RULES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vault", "ILLUMINATED_WORLDS", "Candela_Obscura", "creation_rules.json"
)

_skip_no_candela = pytest.mark.skipif(
    not os.path.exists(_CANDELA_RULES), reason="Candela creation_rules.json not found"
)


class TestCandelaSchema:
    @_skip_no_candela
    def test_schema_loads(self):
        with open(_CANDELA_RULES) as f:
            data = json.load(f)
        assert data["system_id"] == "candela"
        assert len(data["steps"]) == 14

    @_skip_no_candela
    def test_step_types_present(self):
        with open(_CANDELA_RULES) as f:
            data = json.load(f)
        types = {s["type"] for s in data["steps"]}
        assert {"text_input", "choice", "dependent_choice",
                "point_allocate", "auto_derive", "ability_select"} <= types

    @_skip_no_candela
    def test_step_ids(self):
        with open(_CANDELA_RULES) as f:
            data = json.load(f)
        expected = [
            "name", "role", "specialty", "action_ratings", "drives",
            "resistances", "gilded_actions", "role_ability", "specialty_ability",
            "catalyst", "question", "style", "pronouns", "relationship",
        ]
        assert [s["id"] for s in data["steps"]] == expected

    @_skip_no_candela
    def test_circle_creation_structure(self):
        with open(_CANDELA_RULES) as f:
            data = json.load(f)
        circle = data["derived"]["circle_creation"]
        assert len(circle["steps"]) == 5
        ids = [s["id"] for s in circle["steps"]]
        assert "circle_question" in ids
        assert "circle_name" in ids
        assert "chapter_house" in ids
        assert "circle_abilities" in ids
        assert "circle_resources" in ids
        # Circle question is a choice with 6 options (d6 table)
        cq = next(s for s in circle["steps"] if s["id"] == "circle_question")
        assert cq["type"] == "choice"
        assert len(cq["options"]) == 6
        # Circle abilities: 6 from PDF, choose 1
        ca = next(s for s in circle["steps"] if s["id"] == "circle_abilities")
        assert len(ca["pool"]) == 6
        assert ca["count"] == 1
        # Chapter house: 13 Newfaire districts
        ch = next(s for s in circle["steps"] if s["id"] == "chapter_house")
        assert len(ch["options"]) == 13

    @_skip_no_candela
    def test_all_specialties_covered(self):
        with open(_CANDELA_RULES) as f:
            data = json.load(f)
        spec_step = next(s for s in data["steps"] if s["id"] == "specialty")
        specs = set()
        for group in spec_step["option_groups"].values():
            for opt in group:
                specs.add(opt["value"])

        for step in data["steps"]:
            if step.get("preset_key") == "specialty":
                assert specs == set(step["presets"].keys()), \
                    f"Step {step['id']} presets don't match specialties"
            if step.get("preset_gilded"):
                assert specs == set(step["preset_gilded"].keys())


# ---------------------------------------------------------------------------
# Full Candela Flow (Simulated)
# ---------------------------------------------------------------------------

class TestCandelaFullFlow:
    @_skip_no_candela
    def test_full_wizard(self):
        schema = CreationSchema.from_file(_CANDELA_RULES,
            os.path.dirname(_CANDELA_RULES))

        inputs = [
            "Ada Lovelace",  # name
            "1",  # role: Face
            "1",  # specialty: Journalist
            "1",  # zero_raise: first zero-rated action
            "1", "1", "1",  # 3 action rating points
            "1", "1", "1", "1", "1", "1",  # 6 drive points
            # resistances: auto, no input
            "1",  # gilded: choose 1 additional
            "1",  # role ability
            "1",  # specialty ability
            "Lost my partner to a shadow creature",  # catalyst
            "What lies beneath Newfaire?",  # question
            "Trenchcoat and typewriter",  # style
            "she/her",  # pronouns
            "3",  # relationship: Confidant
        ]

        con = _make_console()
        builder = SystemBuilder(schema, con)
        with patch("codex.forge.char_wizard.Prompt.ask", side_effect=inputs):
            with patch("codex.forge.char_wizard.scan_content_availability",
                       return_value={"Core"}):
                sheet = builder.run()

        assert sheet.name == "Ada Lovelace"
        assert sheet.choices["role"]["value"] == "Face"
        assert sheet.choices["specialty"] == "Journalist"
        assert len(sheet.action_ratings) >= 3  # at least preset + allocated
        assert len(sheet.drives) == 3
        assert len(sheet.resistances) == 3
        assert len(sheet.gilded_actions) >= 1
        assert len(sheet.abilities) == 2
        assert sheet.catalyst == "Lost my partner to a shadow creature"
        assert sheet.pronouns == "she/her"
        assert len(sheet.relationships) == 1


# ---------------------------------------------------------------------------
# Circle Creation
# ---------------------------------------------------------------------------

class TestCircleCreation:
    @_skip_no_candela
    def test_circle_flow(self):
        schema = CreationSchema.from_file(_CANDELA_RULES,
            os.path.dirname(_CANDELA_RULES))

        con = _make_console()
        builder = SystemBuilder(schema, con)
        builder.sheet.name = "Test"

        circle_inputs = [
            "1",  # circle_question: choice from 6 options
            "The Nightwatch",  # circle_name
            "2",  # chapter_house: The Eaves
            "1",  # 1 circle ability
            # circle_resources: 4 points (default)
            "1", "1", "2", "2",
        ]

        with patch("codex.forge.char_wizard.Prompt.ask", side_effect=circle_inputs):
            circle_data = builder.run_circle_creation()

        assert circle_data["circle_name"] == "The Nightwatch"
        assert circle_data["chapter_house"] == "The Eaves"
        assert len(circle_data["circle_abilities"]) == 1
        assert sum(circle_data["circle_resources"].values()) == 4
        assert builder.sheet.circle_name == "The Nightwatch"

    def test_no_circle_without_schema(self):
        schema = _make_schema([], derived={})
        con = _make_console()
        builder = SystemBuilder(schema, con)
        assert builder.run_circle_creation() == {}


# ---------------------------------------------------------------------------
# FITD Stat Block Rendering
# ---------------------------------------------------------------------------

class TestFITDRendering:
    @_skip_no_candela
    def test_fitd_stat_block(self):
        schema = CreationSchema.from_file(_CANDELA_RULES,
            os.path.dirname(_CANDELA_RULES))

        sheet = CharacterSheet(system_id="candela", name="Ada")
        sheet.action_ratings = {"Move": 1, "Strike": 0, "Control": 0,
                                "Sway": 1, "Read": 2, "Hide": 0,
                                "Survey": 2, "Focus": 1, "Sense": 1}
        sheet.gilded_actions = ["Survey", "Read"]
        sheet.drives = {"Nerve": 2, "Cunning": 4, "Intuition": 3}
        sheet.resistances = {"Nerve": 0, "Cunning": 1, "Intuition": 1}
        sheet.abilities = ["I Know a Guy", "Insider Access"]
        sheet.choices["role"] = {"value": "Face"}
        sheet.choices["specialty"] = "Journalist"

        panel = render_stat_block_view(sheet, schema)
        assert panel is not None
        assert "Candela Obscura" in str(panel.title)

    def test_non_fitd_still_works(self):
        schema = _make_schema([], derived={"hp_max": 10})
        sheet = CharacterSheet(system_id="dnd5e", name="Gandalf")
        sheet.stats = {"Strength": 10, "Wisdom": 18}
        panel = render_stat_block_view(sheet, schema)
        assert panel is not None


# ---------------------------------------------------------------------------
# Resolve Dependency Helper
# ---------------------------------------------------------------------------

class TestResolveDependency:
    def test_string_value(self):
        schema = _make_schema([])
        con = _make_console()
        builder = SystemBuilder(schema, con)
        builder.sheet.choices["role"] = "Face"
        assert builder._resolve_dependency("role") == "Face"

    def test_dict_value(self):
        schema = _make_schema([])
        con = _make_console()
        builder = SystemBuilder(schema, con)
        builder.sheet.choices["role"] = {"value": "Muscle", "label": "Muscle"}
        assert builder._resolve_dependency("role") == "Muscle"

    def test_missing_value(self):
        schema = _make_schema([])
        con = _make_console()
        builder = SystemBuilder(schema, con)
        assert builder._resolve_dependency("nonexistent") == ""


# ---------------------------------------------------------------------------
# Text Input — FITD Field Storage
# ---------------------------------------------------------------------------

class TestTextInputFITDFields:
    def test_catalyst_stored(self):
        steps = [{"id": "catalyst", "type": "text_input",
                  "label": "Catalyst", "prompt": "Why?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Shadow took my family"])
        assert sheet.catalyst == "Shadow took my family"

    def test_question_stored(self):
        steps = [{"id": "question", "type": "text_input",
                  "label": "Question", "prompt": "What?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["What is the truth?"])
        assert sheet.question == "What is the truth?"

    def test_pronouns_stored(self):
        steps = [{"id": "pronouns", "type": "text_input",
                  "label": "Pronouns", "prompt": "Pronouns?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["they/them"])
        assert sheet.pronouns == "they/them"

    def test_style_stored(self):
        steps = [{"id": "style", "type": "text_input",
                  "label": "Style", "prompt": "Style?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Victorian goth"])
        assert sheet.style == "Victorian goth"


# ---------------------------------------------------------------------------
# Choice — Relationship Storage
# ---------------------------------------------------------------------------

class TestRelationshipChoice:
    def test_relationship_stored(self):
        steps = [
            {"id": "relationship", "type": "choice",
             "label": "Relationship", "prompt": "Choose",
             "options": [
                 {"value": "Mentor", "label": "Mentor", "description": "Guide"},
                 {"value": "Rival", "label": "Rival", "description": "Compete"},
             ]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["2"])
        assert len(sheet.relationships) == 1
        assert sheet.relationships[0]["type"] == "Rival"

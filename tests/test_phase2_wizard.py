#!/usr/bin/env python3
"""Tests for Phase 2 Character Creation Wizard — BitD, SaV, BoB, STC.

Covers: new CharacterSheet fields, group creation generalization,
STC point-buy + auto_derive, FITD action_ratings with playbook presets,
dependent_choice for friends/rivals, and full flow simulations.
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
        stats=["Insight", "Prowess", "Resolve"],
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


_VAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vault")


def _rules_path(rel):
    return os.path.join(_VAULT, rel, "creation_rules.json")


def _skip_if_missing(path):
    return pytest.mark.skipif(
        not os.path.exists(path), reason=f"{path} not found"
    )


# ---------------------------------------------------------------------------
# CharacterSheet — New Fields (Phase 2)
# ---------------------------------------------------------------------------

class TestCharacterSheetPhase2Fields:
    def test_fitd_extended_fields_default_empty(self):
        sheet = CharacterSheet(system_id="bitd")
        assert sheet.background == ""
        assert sheet.alias == ""
        assert sheet.look == ""
        assert sheet.friend == ""
        assert sheet.rival == ""
        assert sheet.vice_purveyor == ""
        assert sheet.heritage_detail == ""

    def test_stc_fields_default_empty(self):
        sheet = CharacterSheet(system_id="stc")
        assert sheet.skills == {}
        assert sheet.expertises == []
        assert sheet.talents == []
        assert sheet.purpose == ""
        assert sheet.obstacle == ""

    def test_group_fields_default_empty(self):
        sheet = CharacterSheet(system_id="bitd")
        assert sheet.group_name == ""
        assert sheet.group_type == ""
        assert sheet.group_abilities == []
        assert sheet.group_resources == {}

    def test_summary_lines_includes_new_fields(self):
        sheet = CharacterSheet(system_id="bitd", name="Cutter")
        sheet.background = "Military"
        sheet.alias = "The Blade"
        sheet.friend = "Marlane"
        sheet.rival = "Chael"
        sheet.purpose = "Power"
        sheet.obstacle = "Debt"
        sheet.skills = {"Athletics": 2, "Stealth": 1}
        sheet.talents = ["Opportunist"]
        sheet.group_name = "The Crows"

        lines = sheet.summary_lines()
        text = "\n".join(lines)
        assert "Background: Military" in text
        assert "Alias: The Blade" in text
        assert "Friend: Marlane" in text
        assert "Rival: Chael" in text
        assert "Purpose: Power" in text
        assert "Obstacle: Debt" in text
        assert "Skills:" in text
        assert "Talents: Opportunist" in text
        assert "Group: The Crows" in text


# ---------------------------------------------------------------------------
# Text Input — New Field Storage
# ---------------------------------------------------------------------------

class TestTextInputNewFields:
    def test_background_stored(self):
        steps = [{"id": "background", "type": "text_input",
                  "label": "Background", "prompt": "Background?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Military"])
        assert sheet.background == "Military"

    def test_alias_stored(self):
        steps = [{"id": "alias", "type": "text_input",
                  "label": "Alias", "prompt": "Alias?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["The Blade"])
        assert sheet.alias == "The Blade"

    def test_look_stored(self):
        steps = [{"id": "look", "type": "text_input",
                  "label": "Look", "prompt": "Appearance?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Scarred and wiry"])
        assert sheet.look == "Scarred and wiry"

    def test_vice_purveyor_stored(self):
        steps = [{"id": "vice_purveyor", "type": "text_input",
                  "label": "Vice Purveyor", "prompt": "Who?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Old Greta"])
        assert sheet.vice_purveyor == "Old Greta"

    def test_heritage_detail_stored(self):
        steps = [{"id": "heritage_detail", "type": "text_input",
                  "label": "Heritage Detail", "prompt": "Describe?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Born in the harbor district"])
        assert sheet.heritage_detail == "Born in the harbor district"

    def test_purpose_stored(self):
        steps = [{"id": "purpose", "type": "text_input",
                  "label": "Purpose", "prompt": "Purpose?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Protect the innocent"])
        assert sheet.purpose == "Protect the innocent"

    def test_obstacle_stored(self):
        steps = [{"id": "obstacle", "type": "text_input",
                  "label": "Obstacle", "prompt": "Obstacle?"}]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["A dark past"])
        assert sheet.obstacle == "A dark past"


# ---------------------------------------------------------------------------
# Point Allocate — Skills and Attributes
# ---------------------------------------------------------------------------

class TestPointAllocateExtended:
    def test_skills_stored_on_sheet(self):
        steps = [
            {"id": "skills", "type": "point_allocate",
             "label": "Skills", "points": 2, "max_per_category": 2,
             "categories": ["Athletics", "Stealth", "Lore"]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["1", "2"])
        assert sheet.skills["Athletics"] == 1
        assert sheet.skills["Stealth"] == 1
        assert sheet.skills["Lore"] == 0

    def test_attributes_stored_on_sheet_stats(self):
        steps = [
            {"id": "attributes", "type": "point_allocate",
             "label": "Attributes", "points": 4, "max_per_category": 3,
             "categories": ["Strength", "Speed", "Intellect"]},
        ]
        schema = _make_schema(steps)
        # Input: 1,1 -> STR+2; 2,3 -> SPD+1, INT+1
        sheet, _ = _run_builder(schema, ["1", "1", "2", "3"])
        assert sheet.stats["Strength"] == 2
        assert sheet.stats["Speed"] == 1
        assert sheet.stats["Intellect"] == 1

    def test_skills_with_path_preset(self):
        steps = [
            {"id": "path", "type": "text_input", "label": "Path", "prompt": "?"},
            {"id": "skills", "type": "point_allocate",
             "label": "Skills", "points": 2, "max_per_category": 2,
             "categories": ["Athletics", "Stealth", "Lore"],
             "preset_key": "path",
             "presets": {"Warrior": {"Athletics": 1}}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Warrior", "2", "2"])
        assert sheet.skills["Athletics"] == 1  # preset
        assert sheet.skills["Stealth"] == 2  # 2 points allocated


# ---------------------------------------------------------------------------
# Auto Derive — Multi-field Derivations (STC)
# ---------------------------------------------------------------------------

class TestAutoDeriveSTC:
    def test_multi_field_derivation(self):
        steps = [
            {"id": "attributes", "type": "point_allocate",
             "label": "Attributes", "points": 6, "max_per_category": 3,
             "categories": ["Strength", "Speed", "Willpower"]},
            {"id": "final_stats", "type": "auto_derive",
             "label": "Final Calculations",
             "derivations": [
                 {"name": "Health", "formula": "10 + Strength"},
                 {"name": "Focus", "formula": "2 + Willpower"},
                 {"name": "Physical Defense", "formula": "10 + Strength + Speed"},
             ]},
        ]
        schema = _make_schema(steps)
        # Allocate: STR=2, SPD=2, WIL=2
        sheet, _ = _run_builder(schema, ["1", "1", "2", "2", "3", "3"])
        final = sheet.choices["final_stats"]
        assert final["Health"] == 12  # 10 + 2
        assert final["Focus"] == 4   # 2 + 2
        assert final["Physical Defense"] == 14  # 10 + 2 + 2

    def test_derivation_with_zero_attrs(self):
        steps = [
            {"id": "attributes", "type": "point_allocate",
             "label": "Attributes", "points": 2, "max_per_category": 3,
             "categories": ["Strength", "Speed"]},
            {"id": "final_stats", "type": "auto_derive",
             "label": "Final",
             "derivations": [
                 {"name": "Health", "formula": "10 + Strength"},
             ]},
        ]
        schema = _make_schema(steps)
        # Allocate: STR=0, SPD=2
        sheet, _ = _run_builder(schema, ["2", "2"])
        assert sheet.choices["final_stats"]["Health"] == 10


# ---------------------------------------------------------------------------
# Ability Select — Talents (STC) + Flat Pool
# ---------------------------------------------------------------------------

class TestAbilitySelectTalents:
    def test_talents_stored_on_sheet(self):
        steps = [
            {"id": "path", "type": "text_input", "label": "Path", "prompt": "?"},
            {"id": "talents", "type": "ability_select",
             "label": "Talents", "count": 1, "depends_on": "path",
             "pools": {"Warrior": ["Vigilant Stance", "Counterattack", "Shield Wall"]}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Warrior", "1"])
        assert "Vigilant Stance" in sheet.talents
        assert sheet.choices["talents"] == ["Vigilant Stance"]
        # Should NOT be in abilities (that's for Candela/FITD)
        assert sheet.abilities == []

    def test_flat_pool_ability_select(self):
        steps = [
            {"id": "talents", "type": "ability_select",
             "label": "Talents", "count": 1,
             "pool": ["Alpha", "Beta", "Gamma"]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["2"])
        assert "Beta" in sheet.talents

    def test_abilities_still_work(self):
        steps = [
            {"id": "role", "type": "text_input", "label": "Role", "prompt": "?"},
            {"id": "role_ability", "type": "ability_select",
             "label": "Ability", "count": 1, "depends_on": "role",
             "pools": {"Face": ["I Know a Guy", "Sweet Talk"]}},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Face", "1"])
        assert "I Know a Guy" in sheet.abilities
        assert sheet.talents == []


# ---------------------------------------------------------------------------
# Dependent Choice — Friend/Rival Storage
# ---------------------------------------------------------------------------

class TestDependentChoiceFriendRival:
    def test_friend_stored_on_sheet(self):
        steps = [
            {"id": "playbook", "type": "text_input", "label": "PB", "prompt": "?"},
            {"id": "friend", "type": "dependent_choice",
             "label": "Friend", "prompt": "Choose your closest friend.",
             "depends_on": "playbook",
             "option_groups": {
                 "Cutter": [
                     {"value": "Marlane", "description": "A pugilist"},
                     {"value": "Chael", "description": "A vicious thug"},
                 ]
             }},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Cutter", "1"])
        assert sheet.friend == "Marlane"
        assert sheet.choices["friend"] == "Marlane"

    def test_rival_stored_on_sheet(self):
        steps = [
            {"id": "playbook", "type": "text_input", "label": "PB", "prompt": "?"},
            {"id": "rival", "type": "dependent_choice",
             "label": "Rival", "prompt": "Choose your rival.",
             "depends_on": "playbook",
             "option_groups": {
                 "Cutter": [
                     {"value": "Mercy", "description": "A cold killer"},
                     {"value": "Grace", "description": "An extortionist"},
                 ]
             }},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["Cutter", "2"])
        assert sheet.rival == "Grace"


# ---------------------------------------------------------------------------
# Choice — Background Storage
# ---------------------------------------------------------------------------

class TestChoiceBackground:
    def test_background_stored_from_choice(self):
        steps = [
            {"id": "background", "type": "choice",
             "label": "Background", "prompt": "Choose background.",
             "options": [
                 {"value": "Academic", "label": "Academic", "description": "Scholar"},
                 {"value": "Military", "label": "Military", "description": "Soldier"},
             ]},
        ]
        schema = _make_schema(steps)
        sheet, _ = _run_builder(schema, ["2"])
        assert sheet.background == "Military"


# ---------------------------------------------------------------------------
# Group Creation (Generalized from Circle)
# ---------------------------------------------------------------------------

class TestGroupCreation:
    def test_circle_creation_still_works(self):
        """run_circle_creation is now an alias for run_group_creation."""
        schema = _make_schema([], derived={
            "circle_creation": {
                "steps": [
                    {"id": "circle_name", "type": "text_input",
                     "label": "Name", "prompt": "Circle name?"},
                ]
            }
        })
        con = _make_console()
        builder = SystemBuilder(schema, con)
        builder.sheet.name = "Test"
        with patch("codex.forge.char_wizard.Prompt.ask", side_effect=["The Watch"]):
            result = builder.run_circle_creation()
        assert result["circle_name"] == "The Watch"
        assert builder.sheet.circle_name == "The Watch"

    def test_crew_creation(self):
        schema = _make_schema([], derived={
            "crew_creation": {
                "steps": [
                    {"id": "crew_type", "type": "choice",
                     "label": "Crew Type", "prompt": "Pick type",
                     "options": [
                         {"value": "Shadows", "label": "Shadows"},
                         {"value": "Bravos", "label": "Bravos"},
                     ]},
                    {"id": "crew_name", "type": "text_input",
                     "label": "Crew Name", "prompt": "Name your crew."},
                ]
            }
        })
        con = _make_console()
        builder = SystemBuilder(schema, con)
        builder.sheet.name = "Test"
        with patch("codex.forge.char_wizard.Prompt.ask", side_effect=["1", "The Wraiths"]):
            result = builder.run_group_creation()
        assert result["crew_type"] == "Shadows"
        assert result["crew_name"] == "The Wraiths"
        assert builder.sheet.group_type == "Shadows"
        assert builder.sheet.group_name == "The Wraiths"

    def test_no_creation_returns_empty(self):
        schema = _make_schema([], derived={"stress_max": 9})
        con = _make_console()
        builder = SystemBuilder(schema, con)
        assert builder.run_group_creation() == {}


# ---------------------------------------------------------------------------
# STC Schema Loading
# ---------------------------------------------------------------------------

_STC_RULES = _rules_path("stc")
_skip_no_stc = _skip_if_missing(_STC_RULES)


class TestSTCSchema:
    @_skip_no_stc
    def test_schema_loads(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        assert data["system_id"] == "stc"
        assert len(data["steps"]) == 12

    @_skip_no_stc
    def test_step_types_present(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        types = {s["type"] for s in data["steps"]}
        assert {"text_input", "choice", "dependent_choice",
                "point_allocate", "auto_derive", "ability_select"} <= types

    @_skip_no_stc
    def test_step_ids(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        expected = [
            "name", "ancestry", "culture", "path", "path_specialty",
            "attributes", "skills", "talents",
            "purpose", "obstacle", "look", "final_stats",
        ]
        assert [s["id"] for s in data["steps"]] == expected

    @_skip_no_stc
    def test_six_attributes(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        attr_step = next(s for s in data["steps"] if s["id"] == "attributes")
        assert len(attr_step["categories"]) == 6
        assert attr_step["points"] == 12
        assert attr_step["max_per_category"] == 3

    @_skip_no_stc
    def test_eighteen_skills(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        skill_step = next(s for s in data["steps"] if s["id"] == "skills")
        assert len(skill_step["categories"]) == 18
        assert skill_step["points"] == 4
        assert skill_step["max_per_category"] == 2

    @_skip_no_stc
    def test_six_paths_with_specialties(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        path_step = next(s for s in data["steps"] if s["id"] == "path")
        assert len(path_step["options"]) == 6
        spec_step = next(s for s in data["steps"] if s["id"] == "path_specialty")
        assert len(spec_step["option_groups"]) == 6
        for path, specs in spec_step["option_groups"].items():
            assert len(specs) == 3, f"{path} should have 3 specialties"

    @_skip_no_stc
    def test_derivations_present(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        final = next(s for s in data["steps"] if s["id"] == "final_stats")
        assert len(final["derivations"]) == 5
        names = [d["name"] for d in final["derivations"]]
        assert "Health" in names
        assert "Focus" in names
        assert "Physical Defense" in names

    @_skip_no_stc
    def test_all_path_presets_in_skills(self):
        with open(_STC_RULES) as f:
            data = json.load(f)
        skill_step = next(s for s in data["steps"] if s["id"] == "skills")
        path_step = next(s for s in data["steps"] if s["id"] == "path")
        path_vals = {o["value"] for o in path_step["options"]}
        preset_keys = set(skill_step["presets"].keys())
        assert path_vals == preset_keys


# ---------------------------------------------------------------------------
# STC Full Flow (Simulated)
# ---------------------------------------------------------------------------

class TestSTCFullFlow:
    @_skip_no_stc
    def test_full_wizard(self):
        schema = CreationSchema.from_file(_STC_RULES, os.path.dirname(_STC_RULES))

        inputs = [
            "Kaladin Stormblessed",  # name
            "1",   # ancestry: Human
            "1",   # culture: Alethi
            "6",   # path: Warrior
            "1",   # specialty: Duelist
            # attributes: 12 points across 6 attrs
            "1", "1",  # STR +2
            "2", "2",  # SPD +2
            "3", "3",  # INT +2
            "4", "4",  # WIL +2
            "5", "5",  # AWA +2
            "6", "6",  # PRE +2
            # skills: 4 points (Warrior preset: Athletics=1)
            "1", "1",  # Athletics +2 (now 2, but Athletics is already 1... wait, preset makes it 1, then +1 = 2, max is 2, so second point goes elsewhere)
            "2", "3",  # Agility +1, Heavy Weaponry +1
            # talents: pick 1 from Warrior pool
            "1",       # Vigilant Stance
            "To protect",        # purpose
            "Surviving the storms",  # obstacle
            "Tall, dark-skinned, slave brands",  # look
            # final_stats: auto, no input
        ]

        con = _make_console()
        builder = SystemBuilder(schema, con)
        with patch("codex.forge.char_wizard.Prompt.ask", side_effect=inputs):
            with patch("codex.forge.char_wizard.scan_content_availability",
                       return_value={"Core"}):
                sheet = builder.run()

        assert sheet.name == "Kaladin Stormblessed"
        assert sheet.choices["ancestry"]["value"] == "Human"
        assert sheet.choices["path"]["value"] == "Warrior"
        assert sheet.choices["path_specialty"] == "Duelist"
        assert len(sheet.stats) == 6  # 6 attributes
        assert len(sheet.skills) == 18  # all 18 skills tracked
        assert "Vigilant Stance" in sheet.talents
        assert sheet.purpose == "To protect"
        assert sheet.obstacle == "Surviving the storms"
        assert "final_stats" in sheet.choices
        # Health should be 10 + Strength
        assert sheet.choices["final_stats"]["Health"] == 10 + sheet.stats["Strength"]


# ---------------------------------------------------------------------------
# STC Sub-Setting Loading
# ---------------------------------------------------------------------------

_STC_ROSHAR = _rules_path("stc/roshar")
_skip_no_roshar = _skip_if_missing(_STC_ROSHAR)


class TestSTCRoshar:
    @_skip_no_roshar
    def test_roshar_loads(self):
        with open(_STC_ROSHAR) as f:
            data = json.load(f)
        assert data["system_id"] == "stc_roshar"
        assert data["parent_engine"] == "stc"
        assert data["setting_id"] == "roshar"

    @_skip_no_roshar
    def test_roshar_has_same_steps(self):
        with open(_STC_RULES) as f:
            parent = json.load(f)
        with open(_STC_ROSHAR) as f:
            child = json.load(f)
        assert len(child["steps"]) == len(parent["steps"])
        parent_ids = [s["id"] for s in parent["steps"]]
        child_ids = [s["id"] for s in child["steps"]]
        assert parent_ids == child_ids


# ---------------------------------------------------------------------------
# BitD Schema Loading
# ---------------------------------------------------------------------------

_BITD_RULES = _rules_path("FITD/bitd")
_skip_no_bitd = _skip_if_missing(_BITD_RULES)


class TestBitDSchema:
    @_skip_no_bitd
    def test_schema_loads(self):
        with open(_BITD_RULES) as f:
            data = json.load(f)
        assert data["system_id"] == "bitd"
        assert len(data["steps"]) >= 10

    @_skip_no_bitd
    def test_seven_playbooks(self):
        with open(_BITD_RULES) as f:
            data = json.load(f)
        pb_step = next(s for s in data["steps"] if s["id"] == "playbook")
        assert len(pb_step["options"]) == 7

    @_skip_no_bitd
    def test_twelve_actions(self):
        with open(_BITD_RULES) as f:
            data = json.load(f)
        ar_step = next(s for s in data["steps"] if s["id"] == "action_ratings")
        assert len(ar_step["categories"]) == 12

    @_skip_no_bitd
    def test_has_crew_creation(self):
        with open(_BITD_RULES) as f:
            data = json.load(f)
        assert "crew_creation" in data.get("derived", {})


# ---------------------------------------------------------------------------
# SaV Schema Loading
# ---------------------------------------------------------------------------

_SAV_RULES = _rules_path("FITD/sav")
_skip_no_sav = _skip_if_missing(_SAV_RULES)


class TestSaVSchema:
    @_skip_no_sav
    def test_schema_loads(self):
        with open(_SAV_RULES) as f:
            data = json.load(f)
        assert data["system_id"] == "sav"
        assert len(data["steps"]) >= 10

    @_skip_no_sav
    def test_seven_playbooks(self):
        with open(_SAV_RULES) as f:
            data = json.load(f)
        pb_step = next(s for s in data["steps"] if s["id"] == "playbook")
        assert len(pb_step["options"]) == 7

    @_skip_no_sav
    def test_twelve_actions(self):
        with open(_SAV_RULES) as f:
            data = json.load(f)
        ar_step = next(s for s in data["steps"] if s["id"] == "action_ratings")
        assert len(ar_step["categories"]) == 12

    @_skip_no_sav
    def test_has_ship_creation(self):
        with open(_SAV_RULES) as f:
            data = json.load(f)
        assert "ship_creation" in data.get("derived", {})


# ---------------------------------------------------------------------------
# BoB Schema Loading
# ---------------------------------------------------------------------------

_BOB_RULES = _rules_path("FITD/bob")
_skip_no_bob = _skip_if_missing(_BOB_RULES)


class TestBoBSchema:
    @_skip_no_bob
    def test_schema_loads(self):
        with open(_BOB_RULES) as f:
            data = json.load(f)
        assert data["system_id"] == "bob"
        assert len(data["steps"]) >= 7

    @_skip_no_bob
    def test_specialist_playbooks(self):
        with open(_BOB_RULES) as f:
            data = json.load(f)
        pb_step = next(s for s in data["steps"] if s["id"] == "playbook")
        vals = {o.get("value", o.get("id", "")) for o in pb_step["options"]}
        assert {"Heavy", "Medic", "Officer", "Scout", "Sniper"} <= vals

    @_skip_no_bob
    def test_four_heritages(self):
        with open(_BOB_RULES) as f:
            data = json.load(f)
        h_step = next(s for s in data["steps"] if s["id"] == "heritage")
        assert len(h_step["options"]) == 4

    @_skip_no_bob
    def test_has_legion_creation(self):
        with open(_BOB_RULES) as f:
            data = json.load(f)
        assert "legion_creation" in data.get("derived", {})


# ---------------------------------------------------------------------------
# Engine Discovery — Finds New Systems
# ---------------------------------------------------------------------------

class TestEngineDiscovery:
    def test_discovers_stc(self):
        engine = CharacterBuilderEngine()
        stc = engine.get_system("stc")
        assert stc is not None
        assert stc.display_name == "Cosmere Roleplaying Game"

    def test_discovers_stc_roshar(self):
        engine = CharacterBuilderEngine()
        roshar = engine.get_system("stc_roshar")
        assert roshar is not None
        assert roshar.parent_engine == "stc"


# ---------------------------------------------------------------------------
# FITD Stat Block Rendering — Extended Fields
# ---------------------------------------------------------------------------

class TestStatBlockExtended:
    def test_bitd_style_stat_block(self):
        schema = _make_schema([], stats=["Insight", "Prowess", "Resolve"])
        sheet = CharacterSheet(system_id="bitd", name="Cutter")
        sheet.action_ratings = {
            "Hunt": 0, "Study": 0, "Survey": 1, "Tinker": 0,
            "Finesse": 0, "Prowl": 0, "Skirmish": 2, "Wreck": 1,
            "Attune": 0, "Command": 1, "Consort": 0, "Sway": 0,
        }
        sheet.background = "Military"
        sheet.friend = "Marlane"
        sheet.rival = "Chael"

        panel = render_stat_block_view(sheet, schema)
        assert panel is not None

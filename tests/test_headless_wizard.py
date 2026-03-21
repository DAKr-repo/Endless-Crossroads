"""Tests for codex.forge.char_wizard_headless — UI-agnostic character creation."""

import pytest
from codex.forge.char_wizard_headless import HeadlessWizard
from codex.forge.char_wizard import CharacterBuilderEngine, CreationSchema


# ── Helpers ───────────────────────────────────────────────────────────


def _get_schema(system_id: str) -> CreationSchema:
    """Load a schema from vault via CharacterBuilderEngine."""
    engine = CharacterBuilderEngine()
    schema = engine.get_system(system_id)
    if not schema:
        pytest.skip(f"No creation_rules.json for {system_id}")
    return schema


def _make_simple_schema() -> CreationSchema:
    """Create a minimal test schema without vault dependency."""
    return CreationSchema(
        system_id="test",
        display_name="Test System",
        genre="Test",
        stats_method="manual",
        stats=["STR", "DEX", "CON"],
        steps=[
            {"id": "name", "type": "text_input", "label": "Name", "prompt": "Enter name:"},
            {"id": "class", "type": "choice", "label": "Class", "prompt": "Choose class:",
             "options": [
                 {"value": "Fighter", "label": "Fighter", "description": "A warrior"},
                 {"value": "Wizard", "label": "Wizard", "description": "A mage"},
                 {"value": "Rogue", "label": "Rogue", "description": "A sneak"},
             ]},
            {"id": "stats", "type": "stat_roll", "label": "Roll Stats",
             "method": "roll_4d6_drop_lowest", "assign_to": ["STR", "DEX", "CON"]},
        ],
        view_type="stat_block",
        derived={},
        vault_path="/tmp/test_vault",
    )


# ── Core Lifecycle Tests ──────────────────────────────────────────────


class TestHeadlessWizardLifecycle:
    def test_init(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        assert wizard.step_idx == 0
        assert not wizard.complete

    def test_first_prompt_is_text_input(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt["type"] == "text_input"
        assert prompt["id"] == "name"
        assert prompt["step_index"] == 0
        assert prompt["total_steps"] == 3

    def test_submit_text(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        result = wizard.submit_answer("Aldo")
        assert result["ok"]
        assert wizard.sheet.name == "Aldo"
        assert wizard.step_idx == 1

    def test_submit_choice(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        wizard.submit_answer("Aldo")  # text step
        prompt = wizard.current_step_prompt()
        assert prompt["type"] == "choice"
        assert len(prompt["options"]) == 3
        result = wizard.submit_answer(2)  # Wizard
        assert result["ok"]
        assert wizard.sheet.choices["class"]["value"] == "Wizard"

    def test_stat_roll_auto_applies(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        wizard.submit_answer("Aldo")
        wizard.current_step_prompt()
        wizard.submit_answer(1)
        prompt = wizard.current_step_prompt()
        assert prompt["type"] == "stat_roll"
        assert prompt["auto_applied"]
        assert len(prompt["rolled_values"]) == 3
        # Stats should be assigned
        assert "STR" in wizard.sheet.stats
        assert "DEX" in wizard.sheet.stats
        assert "CON" in wizard.sheet.stats

    def test_complete_after_all_steps(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        wizard.submit_answer("Aldo")
        wizard.current_step_prompt()
        wizard.submit_answer(1)
        wizard.current_step_prompt()  # stat_roll auto-advances step_idx past end
        # One more call to confirm completion
        final = wizard.current_step_prompt()
        assert final is None
        assert wizard.complete


class TestValidation:
    def test_empty_text_rejected(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        result = wizard.submit_answer("")
        assert not result["ok"]
        assert "error" in result

    def test_choice_out_of_range(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        wizard.submit_answer("Aldo")
        wizard.current_step_prompt()
        result = wizard.submit_answer(99)
        assert not result["ok"]

    def test_choice_zero_rejected(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        wizard.submit_answer("Aldo")
        wizard.current_step_prompt()
        result = wizard.submit_answer(0)
        assert not result["ok"]


class TestBackNavigation:
    def test_back_from_choice(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        wizard.submit_answer("Aldo")
        assert wizard.step_idx == 1
        prompt = wizard.back()
        assert prompt is not None
        assert prompt["type"] == "text_input"
        assert wizard.step_idx == 0

    def test_back_from_start_returns_none(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        assert wizard.back() is None


class TestSerialization:
    def test_to_dict_from_dict(self):
        schema = _make_simple_schema()
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        wizard.submit_answer("Aldo")
        data = wizard.to_dict()
        assert data["system_id"] == "test"
        assert data["step_idx"] == 1
        assert data["name"] == "Aldo"


# ── Real Schema Tests (require vault) ─────────────────────────────────


class TestBitDSchema:
    def test_bitd_first_step(self):
        schema = _get_schema("bitd")
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt is not None
        assert prompt["type"] in ("text_input", "choice")
        assert prompt["total_steps"] > 5  # BitD has 13 steps

    def test_bitd_walk_name_step(self):
        schema = _get_schema("bitd")
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        if prompt["type"] == "text_input":
            result = wizard.submit_answer("Aldo")
            assert result["ok"]


class TestSaVSchema:
    def test_sav_loads(self):
        schema = _get_schema("sav")
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt is not None


class TestCandelaSchema:
    def test_candela_loads(self):
        schema = _get_schema("candela")
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt is not None


class TestDnD5eSchema:
    def test_dnd5e_loads(self):
        schema = _get_schema("dnd5e")
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt is not None


class TestSTCSchema:
    def test_stc_loads(self):
        schema = _get_schema("stc")
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt is not None


# ── Point Allocate Tests ──────────────────────────────────────────────


class TestPointAllocate:
    def test_point_allocate_step(self):
        schema = CreationSchema(
            system_id="test_pa", display_name="Test PA", genre="Test",
            stats_method="action_dots", stats=[],
            steps=[
                {"id": "action_ratings", "type": "point_allocate",
                 "label": "Actions", "points": 3, "max_per_category": 2,
                 "categories": ["Hunt", "Study", "Survey"]},
            ],
            view_type="stat_block", derived={}, vault_path="/tmp",
        )
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt["type"] == "point_allocate"
        assert prompt["points"] == 3
        assert "Hunt" in prompt["categories"]
        result = wizard.submit_answer({"Hunt": 2, "Study": 1, "Survey": 0})
        assert result["ok"]
        assert wizard.sheet.action_ratings["Hunt"] == 2
        assert wizard.sheet.action_ratings["Study"] == 1


# ── Ability Select Tests ──────────────────────────────────────────────


class TestAbilitySelect:
    def test_ability_select_step(self):
        schema = CreationSchema(
            system_id="test_as", display_name="Test AS", genre="Test",
            stats_method="manual", stats=[],
            steps=[
                {"id": "talents", "type": "ability_select",
                 "label": "Talents", "count": 2,
                 "pool": ["Stealth", "Athletics", "Arcana", "Deception"]},
            ],
            view_type="stat_block", derived={}, vault_path="/tmp",
        )
        wizard = HeadlessWizard(schema)
        prompt = wizard.current_step_prompt()
        assert prompt["type"] == "ability_select"
        assert prompt["count"] == 2
        result = wizard.submit_answer(["Stealth", "Arcana"])
        assert result["ok"]
        assert wizard.sheet.choices["talents"] == ["Stealth", "Arcana"]

    def test_wrong_count_rejected(self):
        schema = CreationSchema(
            system_id="test_as2", display_name="Test", genre="Test",
            stats_method="manual", stats=[],
            steps=[
                {"id": "talents", "type": "ability_select", "label": "Talents",
                 "count": 2, "pool": ["A", "B", "C"]},
            ],
            view_type="stat_block", derived={}, vault_path="/tmp",
        )
        wizard = HeadlessWizard(schema)
        wizard.current_step_prompt()
        result = wizard.submit_answer(["A"])
        assert not result["ok"]

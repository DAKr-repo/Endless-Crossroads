"""Tests for expanded spell data: completeness + structure validation."""
import pytest


class TestSpellListStructure:
    """Validate SPELL_LISTS structure and completeness."""

    def test_all_nine_classes_present(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        expected = {"bard", "cleric", "druid", "paladin", "ranger",
                    "sorcerer", "warlock", "wizard", "artificer"}
        assert set(SPELL_LISTS.keys()) == expected

    def test_full_casters_have_levels_0_through_9(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        for cls in ("bard", "cleric", "druid", "sorcerer", "wizard"):
            for lvl in range(0, 10):
                assert lvl in SPELL_LISTS[cls], f"{cls} missing level {lvl}"
                assert len(SPELL_LISTS[cls][lvl]) > 0, f"{cls} level {lvl} is empty"

    def test_warlock_has_levels_0_through_9(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        for lvl in range(0, 10):
            assert lvl in SPELL_LISTS["warlock"], f"warlock missing level {lvl}"

    def test_half_casters_have_correct_level_range(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        for cls in ("paladin", "ranger"):
            # Half-casters have an explicit empty cantrip list (key 0 present, empty)
            assert 0 in SPELL_LISTS[cls], f"{cls} missing cantrip key (should be empty list)"
            assert SPELL_LISTS[cls][0] == [], f"{cls} cantrip list should be empty"
            for lvl in range(1, 6):
                assert lvl in SPELL_LISTS[cls], f"{cls} missing level {lvl}"
            for lvl in range(6, 10):
                assert lvl not in SPELL_LISTS[cls], f"{cls} should not have level {lvl}"

    def test_artificer_has_cantrips_through_5(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        for lvl in range(0, 6):
            assert lvl in SPELL_LISTS["artificer"], f"artificer missing level {lvl}"

    def test_all_entries_are_strings(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        for cls, levels in SPELL_LISTS.items():
            for lvl, spells in levels.items():
                assert isinstance(spells, list), f"{cls}[{lvl}] not a list"
                for spell in spells:
                    assert isinstance(spell, str), f"{cls}[{lvl}] has non-string: {spell}"

    def test_no_duplicate_spells_within_class(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        for cls, levels in SPELL_LISTS.items():
            all_spells = []
            for spells in levels.values():
                all_spells.extend(spells)
            assert len(all_spells) == len(set(all_spells)), f"{cls} has duplicate spells"

    def test_minimum_spell_counts(self):
        """Each class should have a reasonable number of total spells."""
        from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
        minimums = {
            "bard": 80, "cleric": 80, "druid": 80, "sorcerer": 80,
            "warlock": 70, "wizard": 200, "paladin": 30, "ranger": 30,
            "artificer": 50,
        }
        for cls, min_count in minimums.items():
            total = sum(len(spells) for spells in SPELL_LISTS[cls].values())
            assert total >= min_count, f"{cls} has {total} spells, expected >= {min_count}"


class TestSlotTables:
    """Validate spell slot progression tables."""

    def test_full_caster_table_has_20_levels(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_SLOT_TABLE
        assert len(SPELL_SLOT_TABLE) == 20
        for lvl in range(1, 21):
            assert lvl in SPELL_SLOT_TABLE

    def test_full_caster_level_1_has_2_first_level_slots(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_SLOT_TABLE
        assert SPELL_SLOT_TABLE[1] == {1: 2}

    def test_full_caster_level_20_has_9th_level_slot(self):
        from codex.forge.reference_data.dnd5e_spells import SPELL_SLOT_TABLE
        assert 9 in SPELL_SLOT_TABLE[20]
        assert SPELL_SLOT_TABLE[20][9] >= 1

    def test_half_caster_table_caps_at_5th_level(self):
        from codex.forge.reference_data.dnd5e_spells import HALF_CASTER_SLOT_TABLE
        for lvl, slots in HALF_CASTER_SLOT_TABLE.items():
            for spell_lvl in slots:
                assert spell_lvl <= 5, f"Half-caster level {lvl} has spell level {spell_lvl}"

    def test_warlock_table_has_20_levels(self):
        from codex.forge.reference_data.dnd5e_spells import WARLOCK_SLOT_TABLE
        assert len(WARLOCK_SLOT_TABLE) == 20

    def test_warlock_slot_level_caps_at_5(self):
        from codex.forge.reference_data.dnd5e_spells import WARLOCK_SLOT_TABLE
        for info in WARLOCK_SLOT_TABLE.values():
            assert info["slot_level"] <= 5

    def test_warlock_level_17_has_4_slots(self):
        from codex.forge.reference_data.dnd5e_spells import WARLOCK_SLOT_TABLE
        assert WARLOCK_SLOT_TABLE[17]["slots"] == 4


class TestBackwardCompatibility:
    """Ensure existing consumers still work."""

    def test_spellcasting_dict_still_exists(self):
        from codex.forge.reference_data.dnd5e_spells import SPELLCASTING
        assert isinstance(SPELLCASTING, dict)
        assert "bard" in SPELLCASTING

    def test_starting_equipment_still_exists(self):
        from codex.forge.reference_data.dnd5e_spells import STARTING_EQUIPMENT
        assert isinstance(STARTING_EQUIPMENT, dict)

    def test_equipment_catalog_still_exists(self):
        from codex.forge.reference_data.dnd5e_spells import EQUIPMENT_CATALOG
        assert isinstance(EQUIPMENT_CATALOG, dict)

    def test_aggregator_module_exports(self):
        from codex.forge.reference_data.dnd5e import SPELL_LISTS, SPELLCASTING
        assert "wizard" in SPELL_LISTS
        assert "bard" in SPELLCASTING

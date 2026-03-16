"""
tests/test_char_wizard_full.py
================================
Validates the character creation wizard data completeness: DnD5eCharacter
fields, Tasha's optional content, spell slot tables, and feat prerequisites.

Test categories
---------------
1.  DnD5eCharacter creation with proficiencies and features fields
2.  Custom lineage (CUSTOM_LINEAGE from dnd5e_tashas)
3.  Life path tables have rollable entries
4.  Group patron data has description and perks for every entry
5.  Optional class features exist for at least 3 classes
6.  Higher-level spells exist (wizard has level 9 spells)
7.  Spell slot table has 20 levels
8.  Warlock slot table has 20 levels and slots cap at level 5
9.  Half-caster slot table caps at level 5 spells
10. Feat prerequisite blocking (STR 13 req fails for STR 10 character)
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from codex.games.dnd5e import DnD5eCharacter
from codex.games.dnd5e.feats import FeatManager, FEAT_PREREQUISITES
from codex.games.dnd5e.spellcasting import (
    SpellSlotTracker,
    SPELL_SLOT_TABLE,
    WARLOCK_SLOT_TABLE,
    HALF_CASTER_SLOT_TABLE,
)
from codex.forge.reference_data.dnd5e_spells import SPELL_LISTS
from codex.forge.reference_data.dnd5e_tashas import (
    CUSTOM_LINEAGE,
    LIFE_PATH_TABLES,
    GROUP_PATRONS,
    OPTIONAL_CLASS_FEATURES,
)


# ===========================================================================
# 1. DnD5eCharacter creation with proficiencies and features
# ===========================================================================

class TestDnD5eCharacterFields:
    """DnD5eCharacter supports proficiencies and features as list fields."""

    def test_create_with_proficiencies(self):
        char = DnD5eCharacter(
            name="Aldric",
            character_class="fighter",
            proficiencies=["heavy_armor", "martial_weapons", "shields"],
        )
        assert char.proficiencies == ["heavy_armor", "martial_weapons", "shields"]

    def test_create_with_features(self):
        char = DnD5eCharacter(
            name="Aldric",
            character_class="fighter",
            features=["extra_attack", "action_surge"],
        )
        assert char.features == ["extra_attack", "action_surge"]

    def test_proficiencies_default_is_empty_list(self):
        char = DnD5eCharacter(name="Blank", character_class="rogue")
        assert char.proficiencies == []

    def test_features_default_is_empty_list(self):
        char = DnD5eCharacter(name="Blank", character_class="rogue")
        assert char.features == []

    def test_round_trip_proficiencies(self):
        char = DnD5eCharacter(
            name="Finn",
            character_class="paladin",
            proficiencies=["heavy_armor", "divine_smite"],
            features=["lay_on_hands"],
        )
        data = char.to_dict()
        char2 = DnD5eCharacter.from_dict(data)
        assert char2.proficiencies == ["heavy_armor", "divine_smite"]
        assert char2.features == ["lay_on_hands"]

    def test_round_trip_preserves_ability_scores(self):
        char = DnD5eCharacter(
            name="Bryn",
            character_class="barbarian",
            strength=18, dexterity=14, constitution=16,
            intelligence=8, wisdom=12, charisma=10,
        )
        data = char.to_dict()
        char2 = DnD5eCharacter.from_dict(data)
        assert char2.strength == 18
        assert char2.constitution == 16

    def test_round_trip_preserves_level(self):
        char = DnD5eCharacter(name="Lvl10", character_class="wizard", level=10)
        data = char.to_dict()
        char2 = DnD5eCharacter.from_dict(data)
        assert char2.level == 10

    def test_character_name_preserved(self):
        char = DnD5eCharacter(name="Volo Inkbottom", character_class="bard")
        assert char.name == "Volo Inkbottom"

    def test_character_class_preserved(self):
        char = DnD5eCharacter(name="Test", character_class="druid")
        assert char.character_class == "druid"

    def test_multiple_proficiency_types(self):
        char = DnD5eCharacter(
            name="Versatile",
            character_class="fighter",
            proficiencies=["heavy_armor", "Perception", "Athletics"],
        )
        assert "heavy_armor" in char.proficiencies
        assert "Perception" in char.proficiencies
        assert "Athletics" in char.proficiencies


# ===========================================================================
# 2. Custom lineage
# ===========================================================================

class TestCustomLineage:
    """CUSTOM_LINEAGE must be fully populated with all required TCE keys."""

    REQUIRED_KEYS = {
        "description", "ability_bonus", "size", "speed",
        "feat", "darkvision_or_skill", "languages",
    }

    def test_all_required_keys_present(self):
        missing = self.REQUIRED_KEYS - set(CUSTOM_LINEAGE.keys())
        assert not missing, f"CUSTOM_LINEAGE missing keys: {missing}"

    def test_speed_is_thirty(self):
        """Base speed for Custom Lineage is always 30 ft."""
        assert CUSTOM_LINEAGE["speed"] == 30

    def test_languages_includes_common(self):
        langs = CUSTOM_LINEAGE["languages"]
        assert isinstance(langs, list) and len(langs) >= 1
        assert "Common" in langs

    def test_description_is_nonempty_string(self):
        desc = CUSTOM_LINEAGE["description"]
        assert isinstance(desc, str) and desc.strip()

    def test_feat_field_is_nonempty_string(self):
        feat = CUSTOM_LINEAGE["feat"]
        assert isinstance(feat, str) and feat.strip()

    def test_ability_bonus_describes_choice(self):
        """ability_bonus should describe a +2/+1 allocation or similar."""
        ab = CUSTOM_LINEAGE["ability_bonus"]
        assert isinstance(ab, str) and len(ab) > 0

    def test_darkvision_or_skill_is_nonempty(self):
        dvs = CUSTOM_LINEAGE["darkvision_or_skill"]
        assert isinstance(dvs, str) and len(dvs) > 0


# ===========================================================================
# 3. Life path tables have rollable entries
# ===========================================================================

class TestLifePathRollable:
    """Every LIFE_PATH_TABLES category must contain at least one string entry."""

    REQUIRED_CATEGORIES = {
        "parents", "birthplace", "siblings",
        "childhood_memories", "life_events",
    }

    def test_all_required_categories_present(self):
        missing = self.REQUIRED_CATEGORIES - set(LIFE_PATH_TABLES.keys())
        assert not missing, f"LIFE_PATH_TABLES missing categories: {missing}"

    @pytest.mark.parametrize("category", [
        "parents", "birthplace", "siblings",
        "childhood_memories", "life_events",
    ])
    def test_category_is_nonempty_list(self, category):
        entries = LIFE_PATH_TABLES[category]
        assert isinstance(entries, list) and len(entries) >= 1, (
            f"LIFE_PATH_TABLES['{category}'] is not a non-empty list"
        )

    @pytest.mark.parametrize("category", [
        "parents", "birthplace", "siblings",
        "childhood_memories", "life_events",
    ])
    def test_category_entries_are_strings(self, category):
        for i, entry in enumerate(LIFE_PATH_TABLES[category]):
            assert isinstance(entry, str) and entry.strip(), (
                f"LIFE_PATH_TABLES['{category}'][{i}] is not a valid string"
            )

    def test_life_events_has_enough_variety(self):
        """life_events should have at least 8 entries for a meaningful roll."""
        assert len(LIFE_PATH_TABLES["life_events"]) >= 8

    def test_parents_table_is_rollable(self):
        """parents table must have entries so a random.choice() is possible."""
        import random
        entry = random.choice(LIFE_PATH_TABLES["parents"])
        assert isinstance(entry, str) and entry.strip()


# ===========================================================================
# 4. Group patron data has description and perks for every entry
# ===========================================================================

class TestGroupPatronData:
    """GROUP_PATRONS must have 8 patrons, each with description and perks."""

    def test_exactly_eight_patrons(self):
        assert len(GROUP_PATRONS) == 8, (
            f"Expected 8 patrons, got {len(GROUP_PATRONS)}"
        )

    @pytest.mark.parametrize("patron_idx", range(8))
    def test_patron_has_description(self, patron_idx):
        patron = GROUP_PATRONS[patron_idx]
        assert "description" in patron, (
            f"Patron {patron.get('id', patron_idx)} has no description"
        )
        assert isinstance(patron["description"], str) and patron["description"].strip()

    @pytest.mark.parametrize("patron_idx", range(8))
    def test_patron_has_perks(self, patron_idx):
        patron = GROUP_PATRONS[patron_idx]
        assert "perks" in patron, (
            f"Patron {patron.get('id', patron_idx)} has no perks"
        )
        perks = patron["perks"]
        assert isinstance(perks, list) and len(perks) >= 1, (
            f"Patron {patron.get('id', patron_idx)} has empty perks"
        )

    def test_all_patrons_have_name(self):
        for patron in GROUP_PATRONS:
            assert "name" in patron and patron["name"].strip()

    def test_all_patron_ids_unique(self):
        ids = [p["id"] for p in GROUP_PATRONS if "id" in p]
        assert len(ids) == len(set(ids)), "Duplicate patron IDs found"

    def test_each_patron_has_quest_hooks(self):
        for patron in GROUP_PATRONS:
            hooks = patron.get("quest_hooks", [])
            assert isinstance(hooks, list) and len(hooks) >= 1, (
                f"Patron {patron.get('id', '?')} has no quest hooks"
            )


# ===========================================================================
# 5. Optional class features exist for at least 3 classes
# ===========================================================================

class TestOptionalClassFeatures:
    """OPTIONAL_CLASS_FEATURES must cover at least 3 PHB classes with full structure."""

    _THREE_KEY_CLASSES = ["barbarian", "bard", "wizard"]

    def test_covers_at_least_three_classes(self):
        assert len(OPTIONAL_CLASS_FEATURES) >= 3, (
            f"Expected features for at least 3 classes, "
            f"got {len(OPTIONAL_CLASS_FEATURES)}"
        )

    @pytest.mark.parametrize("cls", _THREE_KEY_CLASSES)
    def test_class_features_present(self, cls):
        assert cls in OPTIONAL_CLASS_FEATURES, (
            f"OPTIONAL_CLASS_FEATURES missing entry for '{cls}'"
        )

    @pytest.mark.parametrize("cls", _THREE_KEY_CLASSES)
    def test_class_features_is_nonempty_list(self, cls):
        features = OPTIONAL_CLASS_FEATURES[cls]
        assert isinstance(features, list) and len(features) >= 1, (
            f"OPTIONAL_CLASS_FEATURES['{cls}'] is empty"
        )

    @pytest.mark.parametrize("cls", _THREE_KEY_CLASSES)
    def test_class_feature_entries_have_required_keys(self, cls):
        required = {"name", "replaces", "level", "description"}
        for feat in OPTIONAL_CLASS_FEATURES[cls]:
            missing = required - set(feat.keys())
            assert not missing, (
                f"OPTIONAL_CLASS_FEATURES['{cls}'] entry {feat.get('name', '?')} "
                f"missing keys: {missing}"
            )

    def test_feature_level_is_integer(self):
        for cls, features in OPTIONAL_CLASS_FEATURES.items():
            for feat in features:
                lvl = feat.get("level")
                assert isinstance(lvl, int), (
                    f"OPTIONAL_CLASS_FEATURES['{cls}']['{feat.get('name')}'].level "
                    f"is {lvl!r}, expected int"
                )

    def test_feature_names_are_nonempty_strings(self):
        for cls, features in OPTIONAL_CLASS_FEATURES.items():
            for feat in features:
                name = feat.get("name", "")
                assert isinstance(name, str) and name.strip(), (
                    f"OPTIONAL_CLASS_FEATURES['{cls}'] has a feature with "
                    f"invalid name: {name!r}"
                )


# ===========================================================================
# 6. Higher-level spells exist
# ===========================================================================

class TestHigherLevelSpells:
    """Spell lists include higher-level spells (level 7-9) for full casters."""

    def test_wizard_has_level_9_spells(self):
        assert 9 in SPELL_LISTS["wizard"], "Wizard spell list has no level 9 spells"
        assert len(SPELL_LISTS["wizard"][9]) >= 1

    def test_wizard_level_9_has_named_spells(self):
        """Verify we get real spell names, not empty strings."""
        for spell in SPELL_LISTS["wizard"][9]:
            assert isinstance(spell, str) and spell.strip(), (
                f"Wizard level 9 spell list contains invalid entry: {spell!r}"
            )

    def test_cleric_has_level_9_spells(self):
        assert 9 in SPELL_LISTS["cleric"]
        assert len(SPELL_LISTS["cleric"][9]) >= 1

    def test_druid_has_level_9_spells(self):
        assert 9 in SPELL_LISTS["druid"]
        assert len(SPELL_LISTS["druid"][9]) >= 1

    def test_sorcerer_has_level_9_spells(self):
        assert 9 in SPELL_LISTS["sorcerer"]
        assert len(SPELL_LISTS["sorcerer"][9]) >= 1

    def test_bard_has_level_9_spells(self):
        assert 9 in SPELL_LISTS["bard"]
        assert len(SPELL_LISTS["bard"][9]) >= 1

    def test_warlock_has_level_9_spells(self):
        assert 9 in SPELL_LISTS["warlock"]
        assert len(SPELL_LISTS["warlock"][9]) >= 1

    def test_paladin_does_not_have_level_6_spells(self):
        """Half-casters must not have spell level 6+."""
        assert 6 not in SPELL_LISTS["paladin"], (
            "Paladin should not have level 6 spells"
        )

    def test_ranger_does_not_have_level_6_spells(self):
        assert 6 not in SPELL_LISTS["ranger"], (
            "Ranger should not have level 6 spells"
        )


# ===========================================================================
# 7. Spell slot table has 20 levels
# ===========================================================================

class TestSpellSlotTable:
    """SPELL_SLOT_TABLE covers all 20 character levels with correct structure."""

    def test_has_exactly_20_levels(self):
        assert len(SPELL_SLOT_TABLE) == 20

    def test_all_levels_1_through_20_present(self):
        for lvl in range(1, 21):
            assert lvl in SPELL_SLOT_TABLE, (
                f"SPELL_SLOT_TABLE missing level {lvl}"
            )

    def test_level_1_has_two_first_level_slots(self):
        assert SPELL_SLOT_TABLE[1] == {1: 2}

    def test_level_20_has_ninth_level_slot(self):
        slots = SPELL_SLOT_TABLE[20]
        assert 9 in slots and slots[9] >= 1

    def test_level_5_has_third_level_slots(self):
        assert 3 in SPELL_SLOT_TABLE[5]

    def test_slot_counts_are_positive_integers(self):
        for lvl, slots in SPELL_SLOT_TABLE.items():
            for spell_lvl, count in slots.items():
                assert isinstance(count, int) and count > 0, (
                    f"SPELL_SLOT_TABLE[{lvl}][{spell_lvl}] = {count} is invalid"
                )

    def test_higher_levels_have_more_or_equal_slots(self):
        """Level 9 slots at level 20 must be >= at level 17."""
        lvl17 = SPELL_SLOT_TABLE[17].get(9, 0)
        lvl20 = SPELL_SLOT_TABLE[20].get(9, 0)
        assert lvl20 >= lvl17

    def test_spell_slot_tracker_wizard_uses_table(self):
        tracker = SpellSlotTracker("wizard", 3)
        assert tracker.max_slots == SPELL_SLOT_TABLE[3]


# ===========================================================================
# 8. Warlock slot table has 20 levels and caps at spell level 5
# ===========================================================================

class TestWarlockSlotTable:
    """WARLOCK_SLOT_TABLE covers all 20 levels; pact slot level never exceeds 5."""

    def test_has_exactly_20_levels(self):
        assert len(WARLOCK_SLOT_TABLE) == 20

    def test_all_levels_1_through_20_present(self):
        for lvl in range(1, 21):
            assert lvl in WARLOCK_SLOT_TABLE, (
                f"WARLOCK_SLOT_TABLE missing level {lvl}"
            )

    def test_slot_level_never_exceeds_5(self):
        for lvl, info in WARLOCK_SLOT_TABLE.items():
            assert info["slot_level"] <= 5, (
                f"WARLOCK_SLOT_TABLE[{lvl}].slot_level = {info['slot_level']} > 5"
            )

    def test_level_1_has_one_slot(self):
        assert WARLOCK_SLOT_TABLE[1]["slots"] == 1

    def test_level_17_has_four_slots(self):
        assert WARLOCK_SLOT_TABLE[17]["slots"] == 4

    def test_level_5_slot_level_is_three(self):
        assert WARLOCK_SLOT_TABLE[5]["slot_level"] == 3

    def test_slot_counts_are_positive(self):
        for lvl, info in WARLOCK_SLOT_TABLE.items():
            assert info["slots"] >= 1, (
                f"WARLOCK_SLOT_TABLE[{lvl}].slots = {info['slots']} is invalid"
            )

    def test_tracker_warlock_recovers_on_short_rest(self):
        tracker = SpellSlotTracker("warlock", 5)
        tracker.expend_slot(tracker.pact_slot_level)
        tracker.recover_slots("short")
        assert tracker.current_slots[tracker.pact_slot_level] == tracker.max_slots[tracker.pact_slot_level]


# ===========================================================================
# 9. Half-caster slot table caps at level 5 spells
# ===========================================================================

class TestHalfCasterSlotTable:
    """HALF_CASTER_SLOT_TABLE must not contain spell slots above level 5."""

    def test_all_spell_levels_are_at_most_5(self):
        for char_lvl, slots in HALF_CASTER_SLOT_TABLE.items():
            for spell_lvl in slots:
                assert spell_lvl <= 5, (
                    f"HALF_CASTER_SLOT_TABLE[{char_lvl}] contains spell level "
                    f"{spell_lvl} > 5"
                )

    def test_table_is_nonempty(self):
        assert len(HALF_CASTER_SLOT_TABLE) > 0

    def test_slot_counts_are_positive(self):
        for char_lvl, slots in HALF_CASTER_SLOT_TABLE.items():
            for spell_lvl, count in slots.items():
                assert count >= 1, (
                    f"HALF_CASTER_SLOT_TABLE[{char_lvl}][{spell_lvl}] = {count}"
                )

    def test_tracker_paladin_level_10_has_no_level_6_slot(self):
        tracker = SpellSlotTracker("paladin", 10)
        for lvl in range(6, 10):
            assert tracker.max_slots.get(lvl, 0) == 0, (
                f"Paladin (level 10) should not have level {lvl} slots"
            )

    def test_tracker_ranger_level_20_caps_at_level_5(self):
        tracker = SpellSlotTracker("ranger", 20)
        for lvl in range(6, 10):
            assert tracker.max_slots.get(lvl, 0) == 0, (
                f"Ranger (level 20) should not have level {lvl} slots"
            )


# ===========================================================================
# 10. Feat prerequisite blocking
# ===========================================================================

class TestFeatPrerequisiteBlocking:
    """Feat prerequisites correctly block ineligible characters."""

    def test_grappler_blocks_str_10_character(self):
        """Grappler requires STR 13; a STR 10 character must be blocked."""
        fm = FeatManager()
        char = DnD5eCharacter(name="WeakWiz", character_class="wizard", strength=10)
        result = fm.validate_prerequisite("Grappler", char)
        assert result is False

    def test_grappler_allows_str_13_character(self):
        """Grappler requires exactly STR 13; a STR 13 character must pass."""
        fm = FeatManager()
        char = DnD5eCharacter(name="MinStr", character_class="fighter", strength=13)
        result = fm.validate_prerequisite("Grappler", char)
        assert result is True

    def test_grappler_allows_str_16_character(self):
        """Grappler requires STR 13; a STR 16 fighter must pass."""
        fm = FeatManager()
        char = DnD5eCharacter(name="StrongFighter", character_class="fighter", strength=16)
        result = fm.validate_prerequisite("Grappler", char)
        assert result is True

    def test_defensive_duelist_blocks_dex_12(self):
        """Defensive Duelist requires DEX 13; DEX 12 must be blocked."""
        fm = FeatManager()
        char = DnD5eCharacter(name="ClumFighter", character_class="fighter", dexterity=12)
        result = fm.validate_prerequisite("Defensive Duelist", char)
        assert result is False

    def test_defensive_duelist_allows_dex_13(self):
        fm = FeatManager()
        char = DnD5eCharacter(name="DexFighter", character_class="fighter", dexterity=13)
        result = fm.validate_prerequisite("Defensive Duelist", char)
        assert result is True

    def test_war_caster_blocks_non_caster(self):
        """War Caster requires the ability to cast spells; fighters cannot take it."""
        fm = FeatManager()
        char = DnD5eCharacter(name="Brick", character_class="fighter")
        result = fm.validate_prerequisite("War Caster", char)
        assert result is False

    def test_war_caster_allows_wizard(self):
        """War Caster requires spellcasting; wizards qualify."""
        fm = FeatManager()
        char = DnD5eCharacter(name="Mage", character_class="wizard")
        result = fm.validate_prerequisite("War Caster", char)
        assert result is True

    def test_inspiring_leader_blocks_low_charisma(self):
        """Inspiring Leader requires CHA 13; CHA 10 must be blocked."""
        fm = FeatManager()
        char = DnD5eCharacter(name="Mute", character_class="fighter", charisma=10)
        result = fm.validate_prerequisite("Inspiring Leader", char)
        assert result is False

    def test_inspiring_leader_allows_high_charisma(self):
        fm = FeatManager()
        char = DnD5eCharacter(name="Talker", character_class="bard", charisma=14)
        result = fm.validate_prerequisite("Inspiring Leader", char)
        assert result is True

    def test_apply_feat_with_unmet_prereq_does_not_grant(self):
        """apply_feat() must not add to granted_feats when prereq is unmet."""
        fm = FeatManager()
        char = DnD5eCharacter(name="Weakling", character_class="wizard", strength=10)
        fm.apply_feat("Grappler", char)
        assert "Grappler" not in fm.granted_feats

    def test_apply_feat_with_met_prereq_does_grant(self):
        """apply_feat() must add to granted_feats when prereq is met."""
        fm = FeatManager()
        char = DnD5eCharacter(name="Brute", character_class="fighter", strength=16)
        fm.apply_feat("Grappler", char)
        assert "Grappler" in fm.granted_feats

    def test_unknown_feat_returns_false_for_validate(self):
        fm = FeatManager()
        char = DnD5eCharacter(name="Test", character_class="fighter")
        assert fm.validate_prerequisite("NotARealFeat", char) is False

    def test_no_prereq_feat_always_passes(self):
        """Feats with no prerequisites must validate True for any character."""
        fm = FeatManager()
        char = DnD5eCharacter(name="Anyone", character_class="rogue", strength=8)
        # Tough has no ability score requirements
        assert fm.validate_prerequisite("Tough", char) is True

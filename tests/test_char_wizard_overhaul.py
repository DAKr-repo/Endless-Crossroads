"""
tests/test_char_wizard_overhaul.py
===================================
Comprehensive tests for the D&D 5e character wizard overhaul and reference
data systems. Covers data completeness, structural integrity, loader behaviour,
source filtering, CharacterSheet field defaults, and cross-reference integrity.

Test categories
---------------
1. Reference Data Completeness   (10 tests)
2. Reference Data Structure      ( 5 tests)
3. Loader Tests                  ( 5 tests)
4. Source Filtering              ( 3 tests)
5. CharacterSheet New Fields     ( 5 tests)
6. Cross-Reference Integrity     ( 5 tests)
"""

import pytest

# ---------------------------------------------------------------------------
# Module-level imports of reference data — fail fast if modules are missing
# ---------------------------------------------------------------------------
from codex.forge.reference_data.dnd5e import (
    SUBRACES,
    SUBCLASSES,
    SKILLS,
    CLASS_SKILL_CHOICES,
    BACKGROUND_SKILLS,
    SAVING_THROW_PROFICIENCIES,
    ALIGNMENTS,
    FEATS,
    PERSONALITY,
    SPELL_LISTS,
    SPELLCASTING,
    STARTING_EQUIPMENT,
    EQUIPMENT_CATALOG,
)
from codex.forge.reference_data.loader import (
    load_reference,
    filter_by_source,
)
from codex.forge.char_wizard import CharacterSheet


# ===========================================================================
# 1.  REFERENCE DATA COMPLETENESS
# ===========================================================================

# The 13 classes defined in the PHB (including Artificer from TCE, but
# universally treated as part of the standard class roster in this project).
PHB_CLASSES = {
    "barbarian", "bard", "cleric", "druid", "fighter",
    "monk", "paladin", "ranger", "rogue", "sorcerer",
    "warlock", "wizard", "artificer",
}

# PHB races that must have at least one subrace entry.
PHB_RACES = {
    "dwarf", "elf", "halfling", "human", "gnome",
    "half_elf", "half_orc", "tiefling", "dragonborn",
}

# All 18 core skills from the PHB.
PHB_SKILLS = {
    "acrobatics", "animal_handling", "arcana", "athletics",
    "deception", "history", "insight", "intimidation",
    "investigation", "medicine", "nature", "perception",
    "performance", "persuasion", "religion", "sleight_of_hand",
    "stealth", "survival",
}

# The 9 canonical alignment identifiers.
NINE_ALIGNMENTS = {
    "lawful_good", "neutral_good", "chaotic_good",
    "lawful_neutral", "true_neutral", "chaotic_neutral",
    "lawful_evil", "neutral_evil", "chaotic_evil",
}


class TestReferenceDataCompleteness:

    def test_all_phb_classes_have_subclasses(self):
        """Every PHB class must have at least one subclass entry."""
        missing = [cls for cls in PHB_CLASSES if not SUBCLASSES.get(cls)]
        assert missing == [], (
            f"Classes with no subclass data: {missing}"
        )

    def test_all_phb_races_have_subraces(self):
        """Every PHB race must have at least one subrace entry."""
        missing = [race for race in PHB_RACES if not SUBRACES.get(race)]
        assert missing == [], (
            f"Races with no subrace data: {missing}"
        )

    def test_all_18_phb_skills_present(self):
        """All 18 core skills must be present in SKILLS."""
        missing = PHB_SKILLS - set(SKILLS.keys())
        assert missing == set(), f"Missing skills: {missing}"

    def test_all_13_classes_have_skill_choices(self):
        """All 13 classes must have a CLASS_SKILL_CHOICES entry."""
        missing = PHB_CLASSES - set(CLASS_SKILL_CHOICES.keys())
        assert missing == set(), (
            f"Classes missing skill-choice entries: {missing}"
        )

    def test_all_13_classes_have_saving_throw_proficiencies(self):
        """All 13 classes must have SAVING_THROW_PROFICIENCIES entries."""
        missing = PHB_CLASSES - set(SAVING_THROW_PROFICIENCIES.keys())
        assert missing == set(), (
            f"Classes missing saving-throw entries: {missing}"
        )

    def test_all_9_alignments_present(self):
        """All 9 canonical alignments must be present in ALIGNMENTS."""
        missing = NINE_ALIGNMENTS - set(ALIGNMENTS.keys())
        assert missing == set(), f"Missing alignments: {missing}"

    def test_feats_minimum_40(self):
        """FEATS must contain at least 40 entries (PHB alone provides ~42)."""
        assert len(FEATS) >= 40, (
            f"Expected >= 40 feats, got {len(FEATS)}"
        )

    def test_all_personality_backgrounds_have_correct_entry_counts(self):
        """Each background in PERSONALITY must have 8 traits, 6 ideals, 6 bonds, 6 flaws."""
        errors = []
        expected = {"traits": 8, "ideals": 6, "bonds": 6, "flaws": 6}
        for bg, data in PERSONALITY.items():
            for category, count in expected.items():
                actual = len(data.get(category, []))
                if actual != count:
                    errors.append(
                        f"{bg}.{category}: expected {count}, got {actual}"
                    )
        assert errors == [], "Personality entry count mismatches:\n" + "\n".join(errors)

    def test_spell_lists_have_cantrips_and_level1_per_spellcasting_class(self):
        """Every spellcasting class in SPELL_LISTS must have cantrips (level 0) and level-1 entries."""
        errors = []
        for cls, levels in SPELL_LISTS.items():
            # Level 0 key must exist (cantrips list; may be empty for half-casters)
            if 0 not in levels:
                errors.append(f"{cls}: missing cantrip list (key 0)")
            # Level 1 key must exist and contain at least one spell
            if 1 not in levels or not levels[1]:
                errors.append(f"{cls}: missing or empty level-1 spell list (key 1)")
        assert errors == [], "Spell list gaps:\n" + "\n".join(errors)

    def test_spellcasting_has_entries_for_all_9_spellcasting_classes(self):
        """SPELLCASTING must have entries for all 9 spellcasting classes."""
        spellcasting_classes = {
            "bard", "cleric", "druid", "paladin", "ranger",
            "sorcerer", "warlock", "wizard", "artificer",
        }
        missing = spellcasting_classes - set(SPELLCASTING.keys())
        assert missing == set(), (
            f"Missing SPELLCASTING entries for: {missing}"
        )


# ===========================================================================
# 2.  REFERENCE DATA STRUCTURE
# ===========================================================================

class TestReferenceDataStructure:

    def test_subrace_entries_have_required_keys(self):
        """Each subrace dict must have id, name, source, bonuses, traits."""
        required = {"id", "name", "source", "bonuses", "traits"}
        errors = []
        for race, entries in SUBRACES.items():
            for entry in entries:
                missing = required - set(entry.keys())
                if missing:
                    errors.append(
                        f"SUBRACES[{race!r}] entry {entry.get('id', '?')!r} missing keys: {missing}"
                    )
        assert errors == [], "\n".join(errors)

    def test_subclass_entries_have_required_keys(self):
        """Each subclass dict must have id, name, source, level."""
        required = {"id", "name", "source", "level"}
        errors = []
        for cls, entries in SUBCLASSES.items():
            for entry in entries:
                missing = required - set(entry.keys())
                if missing:
                    errors.append(
                        f"SUBCLASSES[{cls!r}] entry {entry.get('id', '?')!r} missing keys: {missing}"
                    )
        assert errors == [], "\n".join(errors)

    def test_feat_entries_have_required_keys(self):
        """Each feat dict must have name, source, prereq, description."""
        required = {"name", "source", "prereq", "description"}
        errors = []
        for feat_id, feat in FEATS.items():
            missing = required - set(feat.keys())
            if missing:
                errors.append(
                    f"FEATS[{feat_id!r}] missing keys: {missing}"
                )
        assert errors == [], "\n".join(errors)

    def test_skill_entries_have_required_keys(self):
        """Each skill dict must have ability and source."""
        required = {"ability", "source"}
        errors = []
        for skill_id, skill in SKILLS.items():
            missing = required - set(skill.keys())
            if missing:
                errors.append(
                    f"SKILLS[{skill_id!r}] missing keys: {missing}"
                )
        assert errors == [], "\n".join(errors)

    def test_equipment_catalog_categories_have_expected_structure(self):
        """EQUIPMENT_CATALOG must have known categories; each item must have a name and cost_gp."""
        # Weapons and armor categories
        expected_categories = {
            "simple_melee", "simple_ranged",
            "martial_melee", "martial_ranged",
            "armor", "packs",
        }
        present = set(EQUIPMENT_CATALOG.keys())
        missing_cats = expected_categories - present
        assert missing_cats == set(), (
            f"EQUIPMENT_CATALOG missing categories: {missing_cats}"
        )

        errors = []
        for category, items in EQUIPMENT_CATALOG.items():
            for item in items:
                for key in ("name", "cost_gp"):
                    if key not in item:
                        errors.append(
                            f"EQUIPMENT_CATALOG[{category!r}] item {item.get('name', '?')!r} "
                            f"missing key: {key!r}"
                        )
        assert errors == [], "\n".join(errors)


# ===========================================================================
# 3.  LOADER TESTS
# ===========================================================================

class TestLoader:

    def test_load_reference_subraces_returns_subraces_dict(self):
        """load_reference('subraces') must return the SUBRACES dict."""
        result = load_reference("subraces")
        assert isinstance(result, dict)
        # Must contain the canonical dwarf entry
        assert "dwarf" in result

    def test_load_reference_subclasses_returns_subclasses_dict(self):
        """load_reference('subclasses') must return the SUBCLASSES dict."""
        result = load_reference("subclasses")
        assert isinstance(result, dict)
        assert "fighter" in result

    def test_load_reference_feats_returns_feats_dict(self):
        """load_reference('feats') must return the FEATS dict."""
        result = load_reference("feats")
        assert isinstance(result, dict)
        assert len(result) >= 40

    def test_load_reference_nonexistent_category_returns_empty_dict(self):
        """load_reference with an unknown category must return an empty dict without raising."""
        result = load_reference("nonexistent_category_xyz")
        assert result == {}

    def test_filter_by_source_returns_only_matching_source(self):
        """filter_by_source with {'Core'} must pass PHB items and block XGE items."""
        items = [
            {"name": "PHB Item",  "source": "PHB"},
            {"name": "XGE Item",  "source": "XGE"},
            {"name": "TCE Item",  "source": "TCE"},
        ]
        result = filter_by_source(items, {"Core"})
        names = [i["name"] for i in result]
        assert "PHB Item" in names, "PHB item should pass when 'Core' is available"
        assert "XGE Item" not in names, "XGE item should be filtered out with only 'Core'"
        assert "TCE Item" not in names, "TCE item should be filtered out with only 'Core'"


# ===========================================================================
# 4.  SOURCE FILTERING
# ===========================================================================

class TestSourceFiltering:

    def test_phb_sourced_items_pass_with_core(self):
        """PHB-sourced items pass filter when available_sources contains 'Core'."""
        items = [{"name": "PHB Entry", "source": "PHB"}]
        result = filter_by_source(items, {"Core"})
        assert len(result) == 1
        assert result[0]["name"] == "PHB Entry"

    def test_xge_sourced_items_pass_with_xanathar(self):
        """XGE-sourced items pass filter when 'Xanathar' is in available_sources."""
        items = [{"name": "XGE Entry", "source": "XGE"}]
        result = filter_by_source(items, {"Core", "Xanathar"})
        assert len(result) == 1
        assert result[0]["name"] == "XGE Entry"

    def test_xge_sourced_items_filtered_out_when_only_core(self):
        """XGE-sourced items are excluded when available_sources is only {'Core'}."""
        items = [
            {"name": "PHB Entry", "source": "PHB"},
            {"name": "XGE Entry", "source": "XGE"},
        ]
        result = filter_by_source(items, {"Core"})
        names = [i["name"] for i in result]
        assert "PHB Entry" in names
        assert "XGE Entry" not in names


# ===========================================================================
# 5.  CHARACTERSHEET NEW FIELDS
# ===========================================================================

class TestCharacterSheetNewFields:

    def _make_sheet(self) -> CharacterSheet:
        """Minimal CharacterSheet with only system_id set."""
        return CharacterSheet(system_id="dnd5e")

    def test_all_new_fields_exist_with_correct_defaults(self):
        """CharacterSheet must have all new extended fields with expected defaults."""
        sheet = self._make_sheet()
        assert sheet.skill_proficiencies == [], "skill_proficiencies default should be []"
        assert sheet.saving_throw_proficiencies == [], "saving_throw_proficiencies default should be []"
        assert sheet.cantrips_known == [], "cantrips_known default should be []"
        assert sheet.spells_known == [], "spells_known default should be []"
        assert sheet.alignment == "", "alignment default should be empty string"
        assert sheet.personality_traits == [], "personality_traits default should be []"
        assert sheet.ideals == [], "ideals default should be []"
        assert sheet.bonds == [], "bonds default should be []"
        assert sheet.flaws == [], "flaws default should be []"
        assert sheet.gold == 0, "gold default should be 0"
        assert sheet.equipment_mode == "package", "equipment_mode default should be 'package'"

    def test_skill_proficiencies_starts_as_empty_list(self):
        """skill_proficiencies specifically must start as an empty list."""
        sheet = self._make_sheet()
        assert isinstance(sheet.skill_proficiencies, list)
        assert len(sheet.skill_proficiencies) == 0

    def test_alignment_starts_as_empty_string(self):
        """alignment must default to an empty string, not None."""
        sheet = self._make_sheet()
        assert sheet.alignment == ""
        assert isinstance(sheet.alignment, str)

    def test_equipment_mode_defaults_to_package(self):
        """equipment_mode must default to 'package'."""
        sheet = self._make_sheet()
        assert sheet.equipment_mode == "package"

    def test_sheet_fields_are_mutable_independently(self):
        """Mutable list fields must be independent across different CharacterSheet instances."""
        sheet_a = self._make_sheet()
        sheet_b = self._make_sheet()
        sheet_a.skill_proficiencies.append("athletics")
        assert sheet_b.skill_proficiencies == [], (
            "Mutating sheet_a.skill_proficiencies must not affect sheet_b "
            "(dataclass mutable default_factory isolation check)"
        )


# ===========================================================================
# 6.  CROSS-REFERENCE INTEGRITY
# ===========================================================================

VALID_ABILITIES = {
    "strength", "dexterity", "constitution",
    "intelligence", "wisdom", "charisma",
}


class TestCrossReferenceIntegrity:

    def test_class_skill_choices_skills_exist_in_skills_dict(self):
        """All skills listed in CLASS_SKILL_CHOICES[class]['from'] must exist in SKILLS
        (for classes where 'from' is a list, not 'any')."""
        errors = []
        for cls, info in CLASS_SKILL_CHOICES.items():
            pool = info.get("from", [])
            if pool == "any":
                continue  # Bard picks from all skills — validated separately
            for skill in pool:
                if skill not in SKILLS:
                    errors.append(
                        f"CLASS_SKILL_CHOICES[{cls!r}]['from'] contains unknown skill: {skill!r}"
                    )
        assert errors == [], "\n".join(errors)

    def test_background_skills_exist_in_skills_dict(self):
        """All skills granted by BACKGROUND_SKILLS must exist in SKILLS."""
        errors = []
        for bg, skills in BACKGROUND_SKILLS.items():
            for skill in skills:
                if skill not in SKILLS:
                    errors.append(
                        f"BACKGROUND_SKILLS[{bg!r}] contains unknown skill: {skill!r}"
                    )
        assert errors == [], "\n".join(errors)

    def test_all_saving_throw_abilities_are_valid(self):
        """Every ability listed in SAVING_THROW_PROFICIENCIES must be a valid ability score."""
        errors = []
        for cls, abilities in SAVING_THROW_PROFICIENCIES.items():
            for ability in abilities:
                if ability not in VALID_ABILITIES:
                    errors.append(
                        f"SAVING_THROW_PROFICIENCIES[{cls!r}] contains invalid ability: {ability!r}"
                    )
        assert errors == [], "\n".join(errors)

    def test_subclass_levels_match_expected_patterns(self):
        """Subclass unlock levels must match the known PHB progression patterns.

        Expected unlock levels (all subclasses in the data must use one of these):
          - level 1: cleric, sorcerer, warlock
          - level 2: druid, wizard, artificer
          - level 3: all others (barbarian, bard, fighter, monk, paladin, ranger, rogue)
        """
        level1_classes = {"cleric", "sorcerer", "warlock"}
        level2_classes = {"druid", "wizard"}
        # level3_classes is everything else

        errors = []
        for cls, entries in SUBCLASSES.items():
            for entry in entries:
                lvl = entry.get("level")
                if cls in level1_classes:
                    if lvl != 1:
                        errors.append(
                            f"SUBCLASSES[{cls!r}] {entry.get('id')!r}: "
                            f"expected level 1, got {lvl}"
                        )
                elif cls in level2_classes:
                    if lvl != 2:
                        errors.append(
                            f"SUBCLASSES[{cls!r}] {entry.get('id')!r}: "
                            f"expected level 2, got {lvl}"
                        )
                else:
                    # Everything else unlocks at level 3
                    if lvl != 3:
                        errors.append(
                            f"SUBCLASSES[{cls!r}] {entry.get('id')!r}: "
                            f"expected level 3, got {lvl}"
                        )
        assert errors == [], "\n".join(errors)

    def test_spellcasting_abilities_match_expected_classes(self):
        """Spellcasting abilities in SPELLCASTING must match the PHB table."""
        expected = {
            "bard":      "charisma",
            "cleric":    "wisdom",
            "druid":     "wisdom",
            "paladin":   "charisma",
            "ranger":    "wisdom",
            "sorcerer":  "charisma",
            "warlock":   "charisma",
            "wizard":    "intelligence",
            "artificer": "intelligence",
        }
        errors = []
        for cls, ability in expected.items():
            entry = SPELLCASTING.get(cls)
            if entry is None:
                errors.append(f"SPELLCASTING[{cls!r}] not found")
                continue
            actual = entry.get("ability")
            if actual != ability:
                errors.append(
                    f"SPELLCASTING[{cls!r}].ability: expected {ability!r}, got {actual!r}"
                )
        assert errors == [], "\n".join(errors)

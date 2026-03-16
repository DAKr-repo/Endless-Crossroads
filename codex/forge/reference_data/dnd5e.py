"""
codex.forge.reference_data.dnd5e
=================================
Aggregator module that re-exports all D&D 5e reference data from sub-modules.

Sub-modules:
    dnd5e_races       — SUBRACES, SUBCLASSES
    dnd5e_skills      — SKILLS, CLASS_SKILL_CHOICES, BACKGROUND_SKILLS,
                        SAVING_THROW_PROFICIENCIES, ALIGNMENTS
    dnd5e_feats       — FEATS
    dnd5e_personality — PERSONALITY
    dnd5e_spells      — SPELL_LISTS, SPELLCASTING, STARTING_EQUIPMENT,
                        EQUIPMENT_CATALOG
    dnd5e_tashas      — LIFE_PATH_TABLES, DARK_SECRETS, GROUP_PATRONS,
                        OPTIONAL_CLASS_FEATURES, CUSTOM_LINEAGE
"""

from codex.forge.reference_data.dnd5e_races import SUBRACES, SUBCLASSES
from codex.forge.reference_data.dnd5e_skills import (
    SKILLS,
    CLASS_SKILL_CHOICES,
    BACKGROUND_SKILLS,
    SAVING_THROW_PROFICIENCIES,
    ALIGNMENTS,
)
from codex.forge.reference_data.dnd5e_feats import FEATS
from codex.forge.reference_data.dnd5e_personality import PERSONALITY
from codex.forge.reference_data.dnd5e_spells import (
    SPELL_LISTS,
    SPELLCASTING,
    STARTING_EQUIPMENT,
    EQUIPMENT_CATALOG,
)
from codex.forge.reference_data.dnd5e_tashas import (
    LIFE_PATH_TABLES,
    DARK_SECRETS,
    GROUP_PATRONS,
    OPTIONAL_CLASS_FEATURES,
    CUSTOM_LINEAGE,
)

__all__ = [
    "SUBRACES",
    "SUBCLASSES",
    "SKILLS",
    "CLASS_SKILL_CHOICES",
    "BACKGROUND_SKILLS",
    "SAVING_THROW_PROFICIENCIES",
    "ALIGNMENTS",
    "FEATS",
    "PERSONALITY",
    "SPELL_LISTS",
    "SPELLCASTING",
    "STARTING_EQUIPMENT",
    "EQUIPMENT_CATALOG",
    "LIFE_PATH_TABLES",
    "DARK_SECRETS",
    "GROUP_PATRONS",
    "OPTIONAL_CLASS_FEATURES",
    "CUSTOM_LINEAGE",
]

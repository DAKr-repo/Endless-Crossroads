"""
codex.forge.reference_data
===========================
Hardcoded PHB / Xanathar's / Tasha's reference tables for D&D 5e character
creation.  These replace the AI-generated lists previously used by char_wizard
so that data is deterministic, offline, and filterable by source book.
"""

try:
    from codex.forge.reference_data.dnd5e import (
        SUBRACES,
        SUBCLASSES,
        SKILLS,
        CLASS_SKILL_CHOICES,
        BACKGROUND_SKILLS,
        FEATS,
        STARTING_EQUIPMENT,
        EQUIPMENT_CATALOG,
        SPELL_LISTS,
        SPELLCASTING,
        PERSONALITY,
        ALIGNMENTS,
        SAVING_THROW_PROFICIENCIES,
    )
except ImportError:
    # dnd5e.py has not been created yet; symbols will be populated when available.
    SUBRACES: dict = {}
    SUBCLASSES: dict = {}
    SKILLS: dict = {}
    CLASS_SKILL_CHOICES: dict = {}
    BACKGROUND_SKILLS: dict = {}
    FEATS: dict = {}
    STARTING_EQUIPMENT: dict = {}
    EQUIPMENT_CATALOG: dict = {}
    SPELL_LISTS: dict = {}
    SPELLCASTING: dict = {}
    PERSONALITY: dict = {}
    ALIGNMENTS: dict = {}
    SAVING_THROW_PROFICIENCIES: dict = {}

__all__ = [
    "SUBRACES",
    "SUBCLASSES",
    "SKILLS",
    "CLASS_SKILL_CHOICES",
    "BACKGROUND_SKILLS",
    "FEATS",
    "STARTING_EQUIPMENT",
    "EQUIPMENT_CATALOG",
    "SPELL_LISTS",
    "SPELLCASTING",
    "PERSONALITY",
    "ALIGNMENTS",
    "SAVING_THROW_PROFICIENCIES",
]

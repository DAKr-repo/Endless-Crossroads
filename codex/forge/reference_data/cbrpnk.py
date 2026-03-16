"""
codex.forge.reference_data.cbrpnk
===================================
Aggregator module that re-exports all CBR+PNK reference data from sub-modules.

Sub-modules:
    cbrpnk_archetypes  — ARCHETYPES, BACKGROUNDS, VICES, ATTRIBUTES, ACTIONS, ENGAGEMENT_PLANS
    cbrpnk_chrome      — CHROME, CHROME_SLOTS, GLITCH_EFFECTS, CYBERWARE_TABLE
    cbrpnk_corps       — FACTIONS, CORPORATIONS (alias)
    cbrpnk_mechanics   — ACTION_RESULTS, THREAT_LEVELS, EFFECT_LEVELS, CONSEQUENCE_TYPES,
                          HARM_LEVELS, ADVERSARY_SKILLS, RUN_STRUCTURE, GLITCH_DICE_RULES,
                          ANGLE_ROLL_RESULTS, PROGRESS_TRACK_SIZES, PROGRESS_TRACK_GUIDANCE,
                          LONG_SHOT_RULES, DOWNTIME_ACTIVITIES, SETTING_TERMS
    cbrpnk_threats     — SAMPLE_THREATS, ICE_TYPES_PDF, MONA_RISE_THREATS, MONA_RISE_AIS
    cbrpnk_weird       — META_HERITAGES, META_TALENTS, WEIRD_THREATS, WEIRD_FACTIONS,
                          WEIRD_STUFF_SUPPLIERS, WEIRD_DRAWBACKS, WEIRD_CONSEQUENCES
    cbrpnk_hunters     — PREMADE_HUNTERS, HUNTER_ACTIVATION_RULES, HUNTER_BUILDING_RULES
"""

from codex.forge.reference_data.cbrpnk_archetypes import (
    ARCHETYPES,
    BACKGROUNDS,
    VICES,
    ATTRIBUTES,
    ACTIONS,
    ENGAGEMENT_PLANS,
)
from codex.forge.reference_data.cbrpnk_chrome import (
    CHROME,
    CHROME_SLOTS,
    GLITCH_EFFECTS,
    CYBERWARE_TABLE,
)
from codex.forge.reference_data.cbrpnk_corps import FACTIONS, CORPORATIONS
from codex.forge.reference_data.cbrpnk_mechanics import (
    ACTION_RESULTS,
    THREAT_LEVELS,
    EFFECT_LEVELS,
    CONSEQUENCE_TYPES,
    HARM_LEVELS,
    ADVERSARY_SKILLS,
    RUN_STRUCTURE,
    GLITCH_DICE_RULES,
    ANGLE_ROLL_RESULTS,
    PROGRESS_TRACK_SIZES,
    PROGRESS_TRACK_GUIDANCE,
    LONG_SHOT_RULES,
    DOWNTIME_ACTIVITIES,
    SETTING_TERMS,
)
from codex.forge.reference_data.cbrpnk_threats import (
    SAMPLE_THREATS,
    ICE_TYPES_PDF,
    MONA_RISE_THREATS,
    MONA_RISE_AIS,
)
from codex.forge.reference_data.cbrpnk_weird import (
    META_HERITAGES,
    META_TALENTS,
    WEIRD_THREATS,
    WEIRD_FACTIONS,
    WEIRD_STUFF_SUPPLIERS,
    WEIRD_DRAWBACKS,
    WEIRD_CONSEQUENCES,
)
from codex.forge.reference_data.cbrpnk_hunters import (
    PREMADE_HUNTERS,
    HUNTER_ACTIVATION_RULES,
    HUNTER_BUILDING_RULES,
)

__all__ = [
    # archetypes
    "ARCHETYPES",
    "BACKGROUNDS",
    "VICES",
    "ATTRIBUTES",
    "ACTIONS",
    "ENGAGEMENT_PLANS",
    # chrome
    "CHROME",
    "CHROME_SLOTS",
    "GLITCH_EFFECTS",
    "CYBERWARE_TABLE",
    # corps / factions
    "FACTIONS",
    "CORPORATIONS",
    # mechanics
    "ACTION_RESULTS",
    "THREAT_LEVELS",
    "EFFECT_LEVELS",
    "CONSEQUENCE_TYPES",
    "HARM_LEVELS",
    "ADVERSARY_SKILLS",
    "RUN_STRUCTURE",
    "GLITCH_DICE_RULES",
    "ANGLE_ROLL_RESULTS",
    "PROGRESS_TRACK_SIZES",
    "PROGRESS_TRACK_GUIDANCE",
    "LONG_SHOT_RULES",
    "DOWNTIME_ACTIVITIES",
    "SETTING_TERMS",
    # threats
    "SAMPLE_THREATS",
    "ICE_TYPES_PDF",
    "MONA_RISE_THREATS",
    "MONA_RISE_AIS",
    # weird
    "META_HERITAGES",
    "META_TALENTS",
    "WEIRD_THREATS",
    "WEIRD_FACTIONS",
    "WEIRD_STUFF_SUPPLIERS",
    "WEIRD_DRAWBACKS",
    "WEIRD_CONSEQUENCES",
    # hunters
    "PREMADE_HUNTERS",
    "HUNTER_ACTIVATION_RULES",
    "HUNTER_BUILDING_RULES",
]

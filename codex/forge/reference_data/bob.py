"""
codex.forge.reference_data.bob
================================
Aggregator module that re-exports all Band of Blades reference data
from the three sub-modules.

Sub-modules:
    bob_playbooks — PLAYBOOKS, ROOKIE_ABILITIES, HERITAGES
    bob_legion    — SPECIALISTS, SQUAD_TYPES, CHOSEN,
                    MISSION_TYPES, CAMPAIGN_PRESSURES
    bob_factions  — FACTIONS
"""

from codex.forge.reference_data.bob_playbooks import (
    PLAYBOOKS,
    ROOKIE_ABILITIES,
    HERITAGES,
)
from codex.forge.reference_data.bob_legion import (
    SPECIALISTS,
    SQUAD_TYPES,
    CHOSEN,
    MISSION_TYPES,
    CAMPAIGN_PRESSURES,
)
from codex.forge.reference_data.bob_factions import FACTIONS

__all__ = [
    # Playbooks
    "PLAYBOOKS",
    "ROOKIE_ABILITIES",
    "HERITAGES",
    # Legion
    "SPECIALISTS",
    "SQUAD_TYPES",
    "CHOSEN",
    "MISSION_TYPES",
    "CAMPAIGN_PRESSURES",
    # Factions
    "FACTIONS",
]

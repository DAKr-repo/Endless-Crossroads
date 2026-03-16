"""
codex.forge.reference_data.bitd
================================
Aggregator for all Blades in the Dark reference data.
"""

from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS, HERITAGES, VICE_TYPES
from codex.forge.reference_data.bitd_factions import FACTIONS, FACTION_STATUS
from codex.forge.reference_data.bitd_crew import CREW_TYPES, GENERAL_CREW_UPGRADES, LAIR_FEATURES

__all__ = [
    "PLAYBOOKS", "HERITAGES", "VICE_TYPES",
    "FACTIONS", "FACTION_STATUS",
    "CREW_TYPES", "GENERAL_CREW_UPGRADES", "LAIR_FEATURES",
]

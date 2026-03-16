"""
codex.forge.reference_data.crown
==================================
Aggregator module — re-exports all Crown & Crew reference data.

Sub-modules:
    crown_leaders  — LEADERS, PATRONS, LEADER_EVENTS
    crown_factions — FACTIONS, FACTION_RELATIONSHIPS, FACTION_NAMES
"""

from codex.forge.reference_data.crown_leaders import (
    LEADERS,
    PATRONS,
    LEADER_EVENTS,
)
from codex.forge.reference_data.crown_factions import (
    FACTIONS,
    FACTION_RELATIONSHIPS,
    FACTION_NAMES,
)

__all__ = [
    # Leaders
    "LEADERS",
    "PATRONS",
    "LEADER_EVENTS",
    # Factions
    "FACTIONS",
    "FACTION_RELATIONSHIPS",
    "FACTION_NAMES",
]

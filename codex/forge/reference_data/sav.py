"""
codex.forge.reference_data.sav
================================
Aggregator module that re-exports all Scum & Villainy reference data.

Sub-modules:
    sav_playbooks — PLAYBOOKS, HERITAGES, VICE_TYPES
    sav_ships     — SHIP_CLASSES, SHIP_MODULES, SYSTEM_QUALITY_TRACKS
    sav_factions  — FACTIONS, FACTION_STATUS
"""

from codex.forge.reference_data.sav_playbooks import PLAYBOOKS, HERITAGES, VICE_TYPES
from codex.forge.reference_data.sav_ships import (
    SHIP_CLASSES,
    SHIP_MODULES,
    SYSTEM_QUALITY_TRACKS,
)
from codex.forge.reference_data.sav_factions import FACTIONS, FACTION_STATUS

__all__ = [
    "PLAYBOOKS",
    "HERITAGES",
    "VICE_TYPES",
    "SHIP_CLASSES",
    "SHIP_MODULES",
    "SYSTEM_QUALITY_TRACKS",
    "FACTIONS",
    "FACTION_STATUS",
]

"""
codex.games.crown
==================
Crown & Crew narrative engine package.

Exports:
    CrownAndCrewEngine  — Main engine class
    CROWN_COMMANDS      — Command registry for dashboard integration
    CROWN_CATEGORIES    — Categorized command map
"""

from codex.games.crown.engine import (
    CrownAndCrewEngine,
    CROWN_COMMANDS,
    CROWN_CATEGORIES,
    COUNCIL_DILEMMAS,
    MORNING_EVENTS,
    PATRONS,
    LEADERS,
    TAGS,
    SWAY_TIERS,
    LEGACY_TITLES,
)

__all__ = [
    "CrownAndCrewEngine",
    "CROWN_COMMANDS",
    "CROWN_CATEGORIES",
    "COUNCIL_DILEMMAS",
    "MORNING_EVENTS",
    "PATRONS",
    "LEADERS",
    "TAGS",
    "SWAY_TIERS",
    "LEGACY_TITLES",
]

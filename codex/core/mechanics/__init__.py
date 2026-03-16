"""codex.core.mechanics - Shared mechanical primitives.

Exports:
  - UniversalClock, FactionClock, DoomClock (clock.py)
  - ConditionType, Condition, ConditionTracker (conditions.py)
  - InitiativeEntry, InitiativeTracker (initiative.py)
  - RestManager, RestResult (rest.py)
  - ProgressionTracker, DND5E_XP_TABLE, FITD_XP_PER_ADVANCE (progression.py)
"""

from codex.core.mechanics.clock import UniversalClock, FactionClock, DoomClock
from codex.core.mechanics.conditions import (
    ConditionType, Condition, ConditionTracker, CONDITION_DEFAULTS,
    CONDITION_ICONS, format_condition_icons,
)
from codex.core.mechanics.initiative import (
    InitiativeEntry, InitiativeTracker, INITIATIVE_CONFIG,
)
from codex.core.mechanics.rest import RestManager, RestResult
from codex.core.mechanics.progression import (
    ProgressionTracker, DND5E_XP_TABLE, FITD_XP_PER_ADVANCE,
)

__all__ = [
    "UniversalClock", "FactionClock", "DoomClock",
    "ConditionType", "Condition", "ConditionTracker", "CONDITION_DEFAULTS",
    "CONDITION_ICONS", "format_condition_icons",
    "InitiativeEntry", "InitiativeTracker", "INITIATIVE_CONFIG",
    "RestManager", "RestResult",
    "ProgressionTracker", "DND5E_XP_TABLE", "FITD_XP_PER_ADVANCE",
]

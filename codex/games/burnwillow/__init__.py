# codex/games/burnwillow/__init__.py
# Burnwillow game module exports

from codex.games.burnwillow.autopilot import (
    AutopilotAgent,
    CompanionPersonality,
    create_ai_character,
    create_backfill_companions,
    select_ai_target,
    register_companion_as_npc,
    build_exploration_snapshot,
    build_combat_snapshot,
    build_hub_snapshot,
    DECISION_MODEL,
    NARRATION_MODEL,
    PERSONALITY_POOL,
)

__all__ = [
    "AutopilotAgent",
    "CompanionPersonality",
    "create_ai_character",
    "create_backfill_companions",
    "select_ai_target",
    "register_companion_as_npc",
    "build_exploration_snapshot",
    "build_combat_snapshot",
    "build_hub_snapshot",
    "DECISION_MODEL",
    "NARRATION_MODEL",
    "PERSONALITY_POOL",
]

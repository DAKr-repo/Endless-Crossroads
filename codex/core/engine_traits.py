"""
codex/core/engine_traits.py — Engine Trait Registry
=====================================================
Maps declared engine traits to existing shared modules.
Traits are a wiring manifest — they tell the scaffolder (V60.0)
which existing modules to import and initialize for a new engine.

This module does NOT create new mixins. It catalogs what already exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Set


# ---------------------------------------------------------------------------
# Trait definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TraitDef:
    """Definition of a single engine trait."""
    name: str
    category: str           # resolution, narrative, combat, progression, resource
    description: str
    module_path: str         # dotted import path to the providing module
    class_name: str          # primary class or function name in that module
    requires: frozenset      # other traits this depends on


# ---------------------------------------------------------------------------
# Trait catalog — maps to EXISTING shared code
# ---------------------------------------------------------------------------

TRAIT_CATALOG: Dict[str, TraitDef] = {
    # RESOLUTION traits
    "action_roll": TraitDef(
        name="action_roll",
        category="resolution",
        description="FITD d6-pool action resolution (1-3 fail, 4-5 mixed, 6 success, 66 critical)",
        module_path="codex.core.services.fitd_engine",
        class_name="FITDActionRoll",
        requires=frozenset(),
    ),
    "pbta_roll": TraitDef(
        name="pbta_roll",
        category="resolution",
        description="Powered by the Apocalypse 2d6+stat resolution (miss/weak/strong/critical)",
        module_path="codex.core.services.pbta_engine",
        class_name="PbtAActionRoll",
        requires=frozenset(),
    ),
    "stress_track": TraitDef(
        name="stress_track",
        category="resolution",
        description="Stress accumulation with trauma trigger threshold",
        module_path="codex.core.services.fitd_engine",
        class_name="StressClock",
        requires=frozenset(),
    ),

    # CLOCK traits
    "faction_clocks": TraitDef(
        name="faction_clocks",
        category="resolution",
        description="Segment-based faction progress clocks",
        module_path="codex.core.mechanics.clock",
        class_name="FactionClock",
        requires=frozenset(),
    ),
    "doom_clock": TraitDef(
        name="doom_clock",
        category="resolution",
        description="Threshold-based escalation timer (Burnwillow pattern)",
        module_path="codex.core.mechanics.clock",
        class_name="DoomClock",
        requires=frozenset(),
    ),

    # NARRATIVE traits
    "quest_system": TraitDef(
        name="quest_system",
        category="narrative",
        description="Quest acceptance, objective tracking, turn-in with rewards",
        module_path="codex.core.narrative_engine",
        class_name="NarrativeEngine",
        requires=frozenset({"narrative_loom"}),
    ),
    "npc_dialogue": TraitDef(
        name="npc_dialogue",
        category="narrative",
        description="Mimir-powered NPC conversation with disposition tracking",
        module_path="codex.core.narrative_engine",
        class_name="NarrativeEngine",
        requires=frozenset({"narrative_loom"}),
    ),
    "narrative_loom": TraitDef(
        name="narrative_loom",
        category="narrative",
        description="Session memory shards, narrative synthesis, session chronicle",
        module_path="codex.core.services.narrative_loom",
        class_name="NarrativeLoomMixin",
        requires=frozenset(),
    ),

    # COMBAT traits
    "conditions": TraitDef(
        name="conditions",
        category="combat",
        description="Status condition tracking with duration, save DC, modifier stacking",
        module_path="codex.core.mechanics.conditions",
        class_name="ConditionTracker",
        requires=frozenset(),
    ),
    "initiative": TraitDef(
        name="initiative",
        category="combat",
        description="Turn order tracking with config-driven die + stat formula",
        module_path="codex.core.mechanics.initiative",
        class_name="InitiativeTracker",
        requires=frozenset(),
    ),

    # PROGRESSION traits
    "progression_xp": TraitDef(
        name="progression_xp",
        category="progression",
        description="XP/milestone/FITD-mark progression with level-up detection",
        module_path="codex.core.mechanics.progression",
        class_name="ProgressionTracker",
        requires=frozenset(),
    ),
    "rest": TraitDef(
        name="rest",
        category="progression",
        description="Short/long rest or downtime dispatcher with per-engine methods",
        module_path="codex.core.mechanics.rest",
        class_name="RestManager",
        requires=frozenset(),
    ),

    # RESOURCE traits
    "capacity": TraitDef(
        name="capacity",
        category="resource",
        description="Slot or weight-based encumbrance checking",
        module_path="codex.core.services.capacity_manager",
        class_name="check_capacity",
        requires=frozenset(),
    ),
}

# All known trait names
KNOWN_TRAITS: FrozenSet[str] = frozenset(TRAIT_CATALOG.keys())

# Category groupings
TRAIT_CATEGORIES: Dict[str, List[str]] = {}
for _trait in TRAIT_CATALOG.values():
    TRAIT_CATEGORIES.setdefault(_trait.category, []).append(_trait.name)


# ---------------------------------------------------------------------------
# Primary loop types
# ---------------------------------------------------------------------------

LOOP_TYPES = {
    "spatial_dungeon": "BSP dungeon generation, room navigation, fog of war",
    "scene_navigation": "Linear/branching scene progression (FITD, PbtA, Illuminated)",
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_traits(traits: List[str]) -> List[str]:
    """Return list of unknown trait names (empty = all valid)."""
    return [t for t in traits if t not in KNOWN_TRAITS]


def validate_primary_loop(loop: str) -> bool:
    """Check if primary_loop value is known."""
    return loop in LOOP_TYPES


def get_trait_deps(traits: List[str]) -> Set[str]:
    """Return the full set of traits including transitive dependencies."""
    result = set(traits)
    added = True
    while added:
        added = False
        for t in list(result):
            td = TRAIT_CATALOG.get(t)
            if td:
                for dep in td.requires:
                    if dep not in result:
                        result.add(dep)
                        added = True
    return result


def get_wiring_imports(traits: List[str]) -> Dict[str, str]:
    """Return {trait_name: "module.path.ClassName"} for scaffold generation."""
    result = {}
    for t in get_trait_deps(traits):
        td = TRAIT_CATALOG.get(t)
        if td:
            result[t] = f"{td.module_path}.{td.class_name}"
    return result

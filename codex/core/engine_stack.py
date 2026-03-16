"""
codex.core.engine_stack - Engine Stacking for Cross-System Campaigns
=====================================================================

Enables additive mechanic layering: characters accumulate mechanics from
multiple game systems without losing prior abilities. The active engine
drives the game loop while dormant subsystems remain accessible.

Architecture:
    MechanicLayer           -- one system's contribution to a character
    StackedCharacter        -- multi-system character wrapper
    StackedCommandDispatcher-- routes commands across active + dormant engines
    ACTION_EQUIVALENCE_MAP  -- cross-system action translation table
    STACKABLE_FAMILIES      -- compatibility gate for stacking
    snapshot_engine()       -- extract MechanicLayer from a live engine
    seed_actions()          -- compute seed action dots for a new system
    can_stack()             -- check if two systems are compatible

Version: 1.1 (WO-V60.0 + Orchestrator Retirement)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# =========================================================================
# ACTION EQUIVALENCE MAP
# =========================================================================

# Cross-system action translation — used during layer creation to seed
# new action dots. Only maps actions that DON'T share a name across systems.
# Shared names (hack, study, scramble, scrap, skulk, attune, command,
# consort, sway) transfer automatically by name match.

ACTION_EQUIVALENCE_MAP: Dict[str, str] = {
    # CBR+PNK -> SaV
    "override": "rig",
    "scan": "study",
    "shoot": "scrap",
    # BitD -> SaV
    "hunt": "doctor",
    "survey": "study",
    "tinker": "rig",
    "finesse": "helm",
    "prowl": "skulk",
    "skirmish": "scrap",
    "wreck": "scrap",
    # BoB -> SaV
    "marshal": "command",
    "research": "study",
    "scout_action": "skulk",
    "maneuver": "helm",
    "discipline": "command",
}

# Known action field names per system (for extraction from character objects)
_SYSTEM_ACTIONS: Dict[str, List[str]] = {
    "cbrpnk": [
        "hack", "override", "scan", "study", "scramble", "scrap",
        "skulk", "shoot", "attune", "command", "consort", "sway",
    ],
    "sav": [
        "doctor", "hack", "rig", "study",
        "helm", "scramble", "scrap", "skulk",
        "attune", "command", "consort", "sway",
    ],
    "bitd": [
        "hunt", "study", "survey", "tinker",
        "finesse", "prowl", "skirmish", "wreck",
        "attune", "command", "consort", "sway",
    ],
    "bob": [
        "doctor", "marshal", "research", "scout_action",
        "maneuver", "skirmish", "wreck",
        "consort", "discipline", "sway",
    ],
    "candela": [
        "move", "strike", "control",
        "sway", "read", "hide",
        "survey", "focus", "sense",
    ],
}


# =========================================================================
# STACKING COMPATIBILITY GATE
# =========================================================================

# Systems that can stack with each other (share mechanical DNA).
# All 5 FITD+Candela systems share the d6-pool core rule set.
# D&D 5e, STC, Burnwillow, and Crown are each isolated families.
STACKABLE_FAMILIES: Dict[str, frozenset] = {
    "fitd": frozenset({"bitd", "sav", "bob", "cbrpnk", "candela"}),
}


class IncompatibleStackError(ValueError):
    """Raised when attempting to stack incompatible game systems."""

    def __init__(self, source: str, target: str):
        families_desc = ", ".join(
            f"{name}: {{{', '.join(sorted(members))}}}"
            for name, members in STACKABLE_FAMILIES.items()
        )
        super().__init__(
            f"Cannot stack '{target}' onto '{source}' — different mechanical families. "
            f"Stacking is only supported within: {families_desc}"
        )
        self.source = source
        self.target = target


def can_stack(source_system_id: str, target_system_id: str) -> bool:
    """Check if two systems are compatible for stacking.

    Returns True if both systems belong to the same stackable family.
    Systems not in any family cannot stack with anything.
    """
    for family in STACKABLE_FAMILIES.values():
        if source_system_id in family and target_system_id in family:
            return True
    return False


# =========================================================================
# MECHANIC LAYER
# =========================================================================

@dataclass
class MechanicLayer:
    """One system's contribution to a stacked character.

    Captures the full engine state snapshot and action dot values at
    the time the layer was created or last updated.
    """

    system_id: str
    engine_state: dict = field(default_factory=dict)
    action_snapshot: dict = field(default_factory=dict)
    dormant: bool = False
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "engine_state": dict(self.engine_state),
            "action_snapshot": dict(self.action_snapshot),
            "dormant": self.dormant,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MechanicLayer":
        return cls(
            system_id=data["system_id"],
            engine_state=data.get("engine_state", {}),
            action_snapshot=data.get("action_snapshot", {}),
            dormant=data.get("dormant", False),
            timestamp=data.get("timestamp", ""),
        )


# =========================================================================
# STACKED CHARACTER
# =========================================================================

@dataclass
class StackedCharacter:
    """Multi-system character wrapper.

    Layers are ordered by acquisition time; the last non-dormant layer
    is the active system. Shared clocks persist across layer transitions.
    """

    name: str
    layers: List[MechanicLayer] = field(default_factory=list)
    active_system_id: str = ""
    shared_clocks: Dict[str, Any] = field(default_factory=dict)

    def add_layer(
        self,
        system_id: str,
        engine_state: dict,
        action_snapshot: dict,
    ) -> None:
        """Add a new mechanic layer (becomes the active system).

        All existing layers are marked dormant. The new layer is active.

        Raises:
            IncompatibleStackError: If the new system can't stack with
                existing layers.
        """
        # Gate: check compatibility with all existing layers
        for layer in self.layers:
            if not can_stack(layer.system_id, system_id):
                raise IncompatibleStackError(layer.system_id, system_id)

        for layer in self.layers:
            layer.dormant = True

        self.layers.append(MechanicLayer(
            system_id=system_id,
            engine_state=engine_state,
            action_snapshot=action_snapshot,
            dormant=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        self.active_system_id = system_id

    def get_layer(self, system_id: str) -> Optional[MechanicLayer]:
        """Return the layer for a given system, or None."""
        for layer in self.layers:
            if layer.system_id == system_id:
                return layer
        return None

    def get_active_layer(self) -> Optional[MechanicLayer]:
        """Return the currently active (non-dormant) layer."""
        for layer in reversed(self.layers):
            if not layer.dormant:
                return layer
        return None

    def merged_actions(self) -> Dict[str, int]:
        """Union of all action dots across layers, max() on collision."""
        merged: Dict[str, int] = {}
        for layer in self.layers:
            for action, value in layer.action_snapshot.items():
                if isinstance(value, int):
                    merged[action] = max(merged.get(action, 0), value)
        return merged

    # --- Shared clock management ---------------------------------------------

    def add_clock(self, clock: Any) -> None:
        """Register a shared clock by its ``name`` attribute."""
        self.shared_clocks[clock.name] = clock

    def get_clock(self, name: str) -> Optional[Any]:
        """Return the shared clock with *name*, or None."""
        return self.shared_clocks.get(name)

    def remove_clock(self, name: str) -> None:
        """Remove a shared clock. Does nothing if not found."""
        self.shared_clocks.pop(name, None)

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "active_system_id": self.active_system_id,
            "layers": [l.to_dict() for l in self.layers],
        }
        if self.shared_clocks:
            d["shared_clocks"] = {
                name: clock.to_dict() for name, clock in self.shared_clocks.items()
            }
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "StackedCharacter":
        from codex.core.mechanics.clock import UniversalClock
        layers = [MechanicLayer.from_dict(l) for l in data.get("layers", [])]
        shared_clocks: Dict[str, Any] = {}
        for name, clock_data in data.get("shared_clocks", {}).items():
            shared_clocks[name] = UniversalClock.from_dict(clock_data)
        return cls(
            name=data["name"],
            layers=layers,
            active_system_id=data.get("active_system_id", ""),
            shared_clocks=shared_clocks,
        )


# =========================================================================
# STACKED COMMAND DISPATCHER
# =========================================================================

class StackedCommandDispatcher:
    """Routes commands across active + dormant engine layers.

    The active engine gets first shot at every command. If it returns an
    "unknown command" style response, the dispatcher falls through to
    dormant engines in reverse chronological order.
    """

    _UNKNOWN_MARKERS = ("unknown command", "unrecognized", "no such command")

    def __init__(
        self,
        active_engine: Any,
        dormant_engines: Optional[List[Any]] = None,
    ) -> None:
        self.active_engine = active_engine
        self.dormant_engines: List[Any] = dormant_engines or []

    def dispatch(self, cmd: str, **kwargs) -> str:
        """Dispatch a command, falling through to dormant engines."""
        # Try active engine first
        if hasattr(self.active_engine, 'handle_command'):
            try:
                result = self.active_engine.handle_command(cmd, **kwargs)
                if not self._is_unknown(result):
                    return result
            except Exception:
                pass

        # Fall through to dormant engines (reverse chronological)
        for engine in reversed(self.dormant_engines):
            if not hasattr(engine, 'handle_command'):
                continue
            try:
                result = engine.handle_command(cmd, **kwargs)
                if not self._is_unknown(result):
                    tag = getattr(engine, 'display_name', engine.system_id)
                    return f"[{tag}] {result}"
            except Exception:
                continue

        return f"Unknown command: {cmd}"

    def get_all_commands(self) -> Dict[str, List[str]]:
        """Merge command lists from all layers for help display.

        Returns:
            Dict mapping system display_name -> list of command names.
        """
        result: Dict[str, List[str]] = {}

        # Active engine
        active_name = getattr(
            self.active_engine, 'display_name',
            getattr(self.active_engine, 'system_id', 'Active'),
        )
        active_cmds = self._extract_commands(self.active_engine)
        if active_cmds:
            result[f"{active_name} (active)"] = active_cmds

        # Dormant engines
        for engine in self.dormant_engines:
            name = getattr(engine, 'display_name', getattr(engine, 'system_id', '?'))
            cmds = self._extract_commands(engine)
            if cmds:
                result[f"{name} (dormant)"] = cmds

        return result

    @staticmethod
    def _extract_commands(engine) -> List[str]:
        """Extract _cmd_* method names from an engine."""
        cmds = []
        for attr in dir(engine):
            if attr.startswith("_cmd_"):
                cmds.append(attr[5:])  # Strip _cmd_ prefix
        return sorted(cmds)

    @classmethod
    def _is_unknown(cls, result: str) -> bool:
        """Check if a result indicates an unknown command."""
        if not result:
            return True
        lower = result.lower()
        return any(marker in lower for marker in cls._UNKNOWN_MARKERS)


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def extract_action_map(engine) -> Dict[str, int]:
    """Extract action dot values from a live engine's character.

    Looks up the character object, then reads known action fields
    based on the engine's system_id. Falls back to scanning for
    int attributes in the 0-4 range.
    """
    char = _get_lead_character(engine)
    if char is None:
        return {}

    system_id = getattr(engine, 'system_id', '')
    known_actions = _SYSTEM_ACTIONS.get(system_id, [])

    actions: Dict[str, int] = {}
    if known_actions:
        for action in known_actions:
            val = getattr(char, action, 0)
            if isinstance(val, int):
                actions[action] = val
    else:
        # Fallback: scan for int fields in 0-4 range (heuristic)
        for attr in dir(char):
            if attr.startswith('_'):
                continue
            val = getattr(char, attr, None)
            if isinstance(val, int) and 0 <= val <= 4:
                # Exclude common non-action int fields
                if attr not in ('xp', 'stress', 'trauma', 'level', 'tier',
                                'heat', 'rep', 'coin', 'humanity'):
                    actions[attr] = val

    return actions


def snapshot_engine(engine) -> MechanicLayer:
    """Create a MechanicLayer from a live engine's current state."""
    system_id = getattr(engine, 'system_id', 'unknown')
    engine_state = {}
    if hasattr(engine, 'save_state'):
        engine_state = engine.save_state()

    action_snapshot = extract_action_map(engine)

    return MechanicLayer(
        system_id=system_id,
        engine_state=engine_state,
        action_snapshot=action_snapshot,
        dormant=False,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def seed_actions(
    source_layers: List[MechanicLayer],
    target_system_id: str,
) -> Dict[str, int]:
    """Compute seed action dots for a new system using equivalence map.

    For each action in the target system:
    1. If the action name exists in a prior layer, seed = max(prior_value, 0)
    2. If an equivalent exists via ACTION_EQUIVALENCE_MAP, seed = max(equiv, 0)
    3. Otherwise, seed = 0

    Returns empty dict if any source layer is incompatible with the target.

    Returns:
        Dict of action_name -> seed_value for the target system.
    """
    # Gate: check compatibility
    for layer in source_layers:
        if not can_stack(layer.system_id, target_system_id):
            log.warning(
                "seed_actions: incompatible stack %s -> %s, returning empty",
                layer.system_id, target_system_id,
            )
            return {}

    target_actions = _SYSTEM_ACTIONS.get(target_system_id, [])
    if not target_actions:
        return {}

    # Build merged action pool from all source layers
    pool: Dict[str, int] = {}
    for layer in source_layers:
        for action, value in layer.action_snapshot.items():
            if isinstance(value, int):
                pool[action] = max(pool.get(action, 0), value)

    # Build reverse equivalence map: for the target system, what source
    # actions map to each target action?
    reverse_map: Dict[str, List[str]] = {}
    for source_action, target_action in ACTION_EQUIVALENCE_MAP.items():
        reverse_map.setdefault(target_action, []).append(source_action)

    seeds: Dict[str, int] = {}
    for action in target_actions:
        # Direct name match from pool
        val = pool.get(action, 0)

        # Check equivalence map (source actions that map to this target action)
        for source_action in reverse_map.get(action, []):
            source_val = pool.get(source_action, 0)
            val = max(val, source_val)

        seeds[action] = val

    return seeds


def _get_lead_character(engine) -> Any:
    """Get the lead character from an engine."""
    party = getattr(engine, 'party', [])
    if party:
        return party[0]
    return getattr(engine, 'character', None)

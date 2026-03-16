"""
codex.core.engine_protocol - Universal Game Engine Interface
=============================================================

Defines the Protocol that all game system engines should implement.
Used by the future Game System Wizard to discover and compose mechanics.

Existing engines (BurnwillowEngine, CrownAndCrewEngine) already satisfy
this protocol implicitly -- no changes needed to them.
"""

from typing import Protocol, runtime_checkable, Any, Dict, List, Optional


@runtime_checkable
class GameEngine(Protocol):
    """Universal interface for all Codex game engines."""

    system_id: str          # e.g. "burnwillow", "bitd", "crown"
    system_family: str      # e.g. "BURNWILLOW", "FITD", "STC"
    display_name: str       # Human-readable name

    def get_status(self) -> Dict[str, Any]:
        """Return current game state summary for Butler/UI."""
        ...

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state to JSON-safe dict."""
        ...

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from saved dict."""
        ...


@runtime_checkable
class DiceEngine(Protocol):
    """Engines that have a core dice resolution mechanic."""

    def roll_check(self, **kwargs) -> Dict[str, Any]:
        """Execute the system's core dice mechanic."""
        ...


@runtime_checkable
class PartyEngine(Protocol):
    """Engines that manage a party of characters."""

    party: list

    def add_to_party(self, char: Any) -> None: ...
    def remove_from_party(self, char: Any) -> None: ...
    def get_active_party(self) -> list: ...


@runtime_checkable
class StackableEngine(Protocol):
    """Engines that support cross-system stacking (WO-V60.0).

    Optional protocol — engines that implement get_action_map() enable
    cleaner action extraction for engine stacking. Engines without this
    method still work via the fallback in engine_stack.extract_action_map().
    """

    def get_action_map(self) -> Dict[str, int]:
        """Return current action dot values as {action_name: int}."""
        ...


# Engine registry (populated at import time by game packages)
ENGINE_REGISTRY: Dict[str, type] = {}


def register_engine(system_id: str, engine_class: type) -> None:
    """Register a game engine class for discovery by the Game System Wizard."""
    ENGINE_REGISTRY[system_id] = engine_class

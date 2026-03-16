"""
TraitHandler — System-agnostic trait resolution dispatcher.
=============================================================

Each game system implements :class:`TraitResolver` to resolve trait effects
using its own dice/DC mechanics.  The :class:`TraitHandler` dispatches
``activate_trait`` calls to the correct resolver based on ``system_id``.

Follows the :class:`RulesetAdapter` ABC pattern from
:mod:`codex.spatial.map_engine`.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger("CODEX.TraitHandler")


class MissingEngineError(Exception):
    """Raised when a trait is activated for an unregistered system."""


class TraitResolver(ABC):
    """Abstract base for game-system-specific trait resolution.

    Each game system (Burnwillow, D&D 5e, etc.) implements this interface.
    """

    @abstractmethod
    def resolve_trait(self, trait_id: str, context: dict) -> dict:
        """Resolve *trait_id* using system-specific mechanics.

        Args:
            trait_id: Canonical trait name (e.g. ``"SET_TRAP"``).
            context: Arbitrary context dict (character, room, etc.).

        Returns:
            Result dict describing the outcome.
        """
        ...


class TraitHandler:
    """Core dispatcher that routes trait activations to system resolvers.

    Attributes:
        _resolvers: Mapping of system_id -> TraitResolver.
        _broadcast: Optional GlobalBroadcastManager reference.
    """

    def __init__(self, broadcast_manager=None):
        self._resolvers: dict[str, TraitResolver] = {}
        self._broadcast = broadcast_manager

    def register_resolver(self, system_id: str, resolver: TraitResolver) -> None:
        """Register a resolver for *system_id*."""
        self._resolvers[system_id] = resolver

    def activate_trait(self, trait_id: str, system_id: str, context: dict) -> dict:
        """Activate a trait using the resolver for *system_id*.

        Args:
            trait_id: Canonical trait name.
            system_id: Which game system should resolve (e.g. ``"burnwillow"``).
            context: Arbitrary context for the resolver.

        Returns:
            Result dict from the resolver.

        Raises:
            MissingEngineError: If no resolver is registered for *system_id*.
        """
        resolver = self._resolvers.get(system_id)
        if resolver is None:
            raise MissingEngineError(
                f"No TraitResolver registered for system '{system_id}'. "
                f"Available: {list(self._resolvers.keys())}"
            )

        result = resolver.resolve_trait(trait_id, context)

        # Optionally broadcast significant trait activations
        if self._broadcast and result.get("broadcast"):
            self._broadcast.broadcast(
                "TRAIT_ACTIVATED",
                {"trait_id": trait_id, "system_id": system_id, "result": result},
            )

        return result

    def has_resolver(self, system_id: str) -> bool:
        """Check whether a resolver is registered for *system_id*."""
        return system_id in self._resolvers


# ─── Entity Schema ───────────────────────────────────────────────────────

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "entity_schema.json"

_entity_cache: Optional[dict] = None


def load_entity_schema(path: Path | None = None) -> dict:
    """Load and cache the entity schema from ``config/entity_schema.json``.

    Returns:
        Dict mapping entity_id -> entity definition (with traits, overrides).
    """
    global _entity_cache
    if _entity_cache is not None:
        return _entity_cache

    schema_path = path or _SCHEMA_PATH
    if not schema_path.exists():
        logger.warning("Entity schema not found: %s", schema_path)
        _entity_cache = {}
        return _entity_cache

    try:
        data = json.loads(schema_path.read_text())
        _entity_cache = data.get("entities", {})
        logger.info("Entity schema loaded: %d entities", len(_entity_cache))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load entity schema: %s", e)
        _entity_cache = {}

    return _entity_cache


def get_entity_traits(entity_id: str) -> list[str]:
    """Return the ``special_traits`` list for *entity_id*, or empty list."""
    schema = load_entity_schema()
    entity = schema.get(entity_id, {})
    return entity.get("special_traits", [])


def get_entity_override(entity_id: str, system_id: str) -> dict:
    """Return the system_override for *entity_id* + *system_id*, or empty dict."""
    schema = load_entity_schema()
    entity = schema.get(entity_id, {})
    return entity.get("system_overrides", {}).get(system_id, {})

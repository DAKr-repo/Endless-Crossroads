"""
codex/core/config_loader.py — Shared JSON Config Loader
========================================================
Loads config/[category]/[system_id].json with fallback support.
Used by engine loaders (bestiary, loot, hazards, magic_items, features).
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional


# Project root — three levels up from this file (codex/core/config_loader.py)
_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
_CONFIG_ROOT = os.path.join(_PROJECT_ROOT, "config")

# Module-level cache: (category, system_id) -> parsed data
_CACHE: dict[tuple[str, str], Any] = {}


def load_config(
    category: str,
    system_id: str,
    fallback: Any = None,
    *,
    force: bool = False,
) -> Any:
    """Load config/[category]/[system_id].json with fallback.

    Args:
        category: Config subdirectory (bestiary, loot, hazards, magic_items, features).
        system_id: System identifier (dnd5e, stc).
        fallback: Value to return if file missing or corrupt.
        force: If True, bypass cache and re-read from disk.

    Returns:
        Parsed JSON data or fallback value.
    """
    cache_key = (category, system_id)
    if not force and cache_key in _CACHE:
        return _CACHE[cache_key]

    config_path = os.path.join(_CONFIG_ROOT, category, f"{system_id}.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        _CACHE[cache_key] = data
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback


def config_exists(category: str, system_id: str) -> bool:
    """Check if a config file exists without loading it."""
    config_path = os.path.join(_CONFIG_ROOT, category, f"{system_id}.json")
    return os.path.isfile(config_path)


def config_path(category: str, system_id: str) -> str:
    """Return the absolute path for a config file (may not exist yet)."""
    return os.path.join(_CONFIG_ROOT, category, f"{system_id}.json")


def clear_cache() -> None:
    """Clear the config cache (useful for testing)."""
    _CACHE.clear()

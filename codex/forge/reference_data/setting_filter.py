"""
codex.forge.reference_data.setting_filter
==========================================
Generic filter utility for hierarchical sub-setting content gating.

Two pure functions that filter reference data dicts and content pools
by setting_id (e.g. "roshar", "forgotten_realms"). Used by engines
to gate heritages, orders, equipment, and encounter pools to the
active sub-setting while preserving universal content.

Convention:
  - setting_id is None or "": return ALL entries (no filtering)
  - "cosmere" or "": universal content, passes all filters
  - "roshar", "scadrial", etc.: sub-setting-specific content

WO-V43.0: Initial implementation.
"""

from typing import Any, Dict, List, Optional, Sequence

# Default universal tags that pass all filters regardless of setting_id.
_DEFAULT_UNIVERSAL_TAGS: frozenset = frozenset({"", "cosmere"})


def filter_by_setting(
    data: Dict[str, Dict[str, Any]],
    setting_id: Optional[str] = None,
    universal_tags: Optional[Sequence[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Filter a reference data dict by setting tag.

    Rules:
    - setting_id is None or "": return ALL entries (no filtering)
    - Otherwise: include entries where entry["setting"] == setting_id,
      or entry["setting"] is in the universal tags set (default: "", "cosmere")

    Args:
        data: Dict of {name: {setting: ..., ...}} reference entries.
        setting_id: The active sub-setting to filter for, or None/"" for all.
        universal_tags: Optional sequence of tag values that should always pass
            the filter (e.g. parent system tags). Defaults to ("", "cosmere").

    Returns:
        Filtered copy of data (original dict is never mutated).
    """
    if not setting_id:
        return dict(data)

    pass_tags = (
        frozenset(universal_tags) if universal_tags is not None
        else _DEFAULT_UNIVERSAL_TAGS
    )

    result = {}
    for key, entry in data.items():
        entry_setting = entry.get("setting", "")
        if entry_setting == setting_id or entry_setting in pass_tags:
            result[key] = entry
    return result


def filter_pool_by_setting(
    pool: Dict[int, List[str]],
    setting_id: Optional[str],
    pool_registry: Optional[Dict[str, Dict[int, List[str]]]] = None,
) -> Dict[int, List[str]]:
    """Swap entire content pools by setting.

    Returns registry[setting_id] if found, else the default pool.

    Args:
        pool: Default content pool (tier -> items).
        setting_id: The active sub-setting, or None/"" for default.
        pool_registry: Optional mapping of setting_id -> pool.

    Returns:
        The matching pool from the registry, or the default pool.
    """
    if not setting_id or not pool_registry:
        return pool
    return pool_registry.get(setting_id, pool)


__all__ = ["filter_by_setting", "filter_pool_by_setting"]

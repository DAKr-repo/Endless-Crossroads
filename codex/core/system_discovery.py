"""
codex/core/system_discovery.py — Dynamic System Discovery
===========================================================
Scans vault/*/system_manifest.json (recursively) to discover game systems
and classify them by engine type, replacing hardcoded DUNGEON_SYSTEMS
and FITD_SYSTEMS sets.

Provides backward-compatible fallback — hardcoded sets are merged with
discovered systems so existing code never breaks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_ROOT = _PROJECT_ROOT / "vault"

# ---------------------------------------------------------------------------
# Hardcoded fallbacks (backward compat — never removed)
# ---------------------------------------------------------------------------

_HARDCODED_DUNGEON = {"dnd5e", "stc"}
_HARDCODED_NARRATIVE = {"bitd", "sav", "bob", "cbrpnk", "candela"}

# Systems that have their own game loops (not routed through play_universal.py).
# Their manifests exist for classification/discovery but they're excluded from
# the DUNGEON_SYSTEMS/FITD_SYSTEMS sets used for routing.
_STANDALONE_SYSTEMS = {"burnwillow", "crown"}

# ---------------------------------------------------------------------------
# Manifest cache
# ---------------------------------------------------------------------------

_manifest_cache: Optional[Dict[str, dict]] = None


def _scan_manifests(vault_root: Optional[Path] = None) -> Dict[str, dict]:
    """Scan vault for all system_manifest.json files.

    Returns dict mapping system_id -> parsed manifest data.
    """
    root = vault_root or VAULT_ROOT
    manifests: Dict[str, dict] = {}

    if not root.exists():
        return manifests

    for manifest_path in sorted(root.rglob("system_manifest.json")):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
            system_id = data.get("system_id")
            if system_id:
                data["_manifest_path"] = str(manifest_path)
                manifests[system_id] = data
        except (json.JSONDecodeError, OSError, KeyError):
            continue

    return manifests


def get_all_manifests(*, force: bool = False) -> Dict[str, dict]:
    """Return cached dict of all discovered system manifests.

    Args:
        force: If True, re-scan vault instead of using cache.

    Returns:
        Dict mapping system_id -> manifest data.
    """
    global _manifest_cache
    if _manifest_cache is None or force:
        _manifest_cache = _scan_manifests()
    return _manifest_cache


def get_manifest(system_id: str) -> Optional[dict]:
    """Return the manifest for a single system, or None."""
    return get_all_manifests().get(system_id)


# ---------------------------------------------------------------------------
# System classification
# ---------------------------------------------------------------------------

def discover_system_types(
    *, vault_root: Optional[Path] = None
) -> Tuple[Set[str], Set[str]]:
    """Discover spatial (dungeon) and narrative (FITD/PbtA) system sets.

    Scans vault/*/system_manifest.json and merges with hardcoded
    fallback sets for backward compatibility.

    Returns:
        (dungeon_systems, narrative_systems) — two sets of system_id strings.
    """
    manifests = _scan_manifests(vault_root) if vault_root else get_all_manifests()

    dungeon: Set[str] = set()
    narrative: Set[str] = set()

    for system_id, manifest in manifests.items():
        if manifest.get("needs_review"):
            continue  # Skip unreviewed auto-classified systems

        # Skip standalone systems (they have their own game loops)
        if system_id in _STANDALONE_SYSTEMS:
            continue

        engine_type = manifest.get("engine_type", "")
        primary_loop = manifest.get("primary_loop", "")

        if engine_type == "spatial" or primary_loop == "spatial_dungeon":
            dungeon.add(system_id)
        elif engine_type == "narrative" or primary_loop == "scene_navigation":
            narrative.add(system_id)

    # Merge hardcoded fallback
    dungeon |= _HARDCODED_DUNGEON
    narrative |= _HARDCODED_NARRATIVE

    return dungeon, narrative


def get_primary_loop(system_id: str) -> str:
    """Return the primary_loop for a system.

    Falls back to heuristic if no manifest exists.
    """
    manifest = get_manifest(system_id)
    if manifest:
        return manifest.get("primary_loop", "scene_navigation")

    # Heuristic fallback
    if system_id in _HARDCODED_DUNGEON:
        return "spatial_dungeon"
    return "scene_navigation"


def get_engine_traits(system_id: str) -> List[str]:
    """Return the declared engine_traits for a system."""
    manifest = get_manifest(system_id)
    if manifest:
        return manifest.get("engine_traits", [])
    return []


def get_pattern_hint(system_id: str) -> Optional[str]:
    """Return the stat_block_format.pattern_hint from the manifest."""
    manifest = get_manifest(system_id)
    if manifest:
        fmt = manifest.get("stat_block_format", {})
        return fmt.get("pattern_hint")
    return None


def get_resolution_mechanic(system_id: str) -> str:
    """Return the resolution_mechanic for a system."""
    manifest = get_manifest(system_id)
    if manifest:
        return manifest.get("resolution_mechanic", "custom")
    return "custom"


# ---------------------------------------------------------------------------
# Engine module discovery
# ---------------------------------------------------------------------------

# Maps system_id to the Python module path for import.
# Handles non-standard vault layouts (FITD/*, ILLUMINATED_WORLDS/*).
_MODULE_MAP: Dict[str, str] = {
    "bitd": "codex.games.bitd",
    "sav": "codex.games.sav",
    "bob": "codex.games.bob",
    "cbrpnk": "codex.games.cbrpnk",
    "candela": "codex.games.candela",
    "dnd5e": "codex.games.dnd5e",
    "stc": "codex.games.stc",
    "burnwillow": "codex.games.burnwillow",
    "crown": "codex.games.crown",
}


def get_engine_module(system_id: str) -> Optional[str]:
    """Return the Python module path for an engine, or None if unknown."""
    if system_id in _MODULE_MAP:
        return _MODULE_MAP[system_id]
    # Convention: codex.games.{system_id}
    return f"codex.games.{system_id}"


def get_importable_systems() -> List[str]:
    """Return system_ids that have both a manifest and a Python engine module."""
    import importlib
    result = []
    for system_id in get_all_manifests():
        module_path = get_engine_module(system_id)
        if module_path:
            try:
                importlib.import_module(module_path)
                result.append(system_id)
            except ImportError:
                pass
    return result


def clear_cache() -> None:
    """Clear the manifest cache (useful for testing)."""
    global _manifest_cache
    _manifest_cache = None

"""
codex_registry_builder.py — Universal Registry Builder (v2.0)
=============================================================

Scans config/systems/ for rules JSONs, builds deep-indexed registries
into deterministic_core/ for the C.O.D.E.X. agent to load at runtime.

v2.0 Changes:
  - Auto-detects new/modified configs via file mtime comparison
  - Importable `build_all()` for programmatic use (Maestro zero-touch)
  - FITD/Illuminated-aware index flattening (action maps, stress, etc.)
  - `--auto` CLI flag for non-interactive build-all
"""

import json
import logging
import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, Optional

# Ensure project root is on sys.path (needed when run as subprocess)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from maintenance.codex_utils import setup_logging
_logger = setup_logging("REGISTRY_BUILDER")

# CONFIGURATION
BASE_DIR = Path(__file__).resolve().parent.parent  # Project root, not maintenance/
CONFIG_DIR = str(BASE_DIR / "config" / "systems")
OUTPUT_DIR = str(BASE_DIR / "deterministic_core")


def load_system_configs() -> Dict[str, dict]:
    """Scans the config directory for available TTRPG systems."""
    systems = {}
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        return systems

    for filename in sorted(os.listdir(CONFIG_DIR)):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(CONFIG_DIR, filename), 'r') as f:
                    data = json.load(f)
                    # Use system_id from JSON, fallback to filename
                    sid = data.get('system_id', filename.replace('.json', '')).upper()
                    systems[sid] = data
            except Exception as e:
                print(f"  Warning: Error loading {filename}: {e}")
    return systems


def _needs_rebuild(system_id: str, config_path: str) -> bool:
    """Check if a system's registry is outdated or missing.

    Compares the config JSON's mtime against the existing registry output.
    Returns True if the registry needs to be (re)built.
    """
    output_path = os.path.join(OUTPUT_DIR, f"rules_{system_id}.json")
    if not os.path.exists(output_path):
        return True

    config_mtime = os.path.getmtime(config_path)
    output_mtime = os.path.getmtime(output_path)
    return config_mtime > output_mtime


def _flatten_actions(core_stats: dict) -> dict:
    """Flatten action maps from core_stats for quick lookup.

    Works for both FITD (attributes -> actions) and Illuminated
    (resistances -> actions) structures.
    """
    flat = {}
    actions = core_stats.get("actions", {})
    if isinstance(actions, dict):
        for group, action_list in actions.items():
            if isinstance(action_list, list):
                for action in action_list:
                    flat[action.lower()] = {
                        "name": action,
                        "group": group,
                    }
    return flat


# Default templates for RECOVERY fallback
_RECOVERY_DEFAULTS = {
    "display_name": lambda sid: sid,
    "engine": "custom",
    "dice_system": "custom",
    "system_family": "",
    "races": [],
    "deep_classes": {},
    "feats": [],
    "archetype_categories": {},
    "core_stats": {},
    "resources": [],
    "mechanics": {},
}


def _validate_system_data(system_id: str, system_data: dict) -> dict:
    """Check for empty or missing keys.  Apply defaults with RECOVERY log.

    Returns the (possibly patched) system_data dict.
    """
    patched = dict(system_data)

    for key, default in _RECOVERY_DEFAULTS.items():
        value = patched.get(key)
        is_missing = value is None
        is_empty = (isinstance(value, (list, dict, str)) and not value)

        if is_missing or is_empty:
            fallback = default(system_id) if callable(default) else default
            patched[key] = fallback
            tag = "missing" if is_missing else "empty"
            msg = f"[RECOVERY] Using default template for {key} in {system_id} ({tag})."
            _logger.info(msg)
            print(f"    {msg}")

    # Also check inside mechanics dict
    mechanics = patched.get("mechanics", {})
    if isinstance(mechanics, dict):
        for mkey in ("stats", "resources", "classes", "subclasses", "races"):
            if mkey in mechanics and not mechanics[mkey]:
                msg = f"[RECOVERY] Using default template for mechanics.{mkey} in {system_id} (empty)."
                _logger.info(msg)
                print(f"    {msg}")
                # Leave empty list in place -- it's valid, just noted

    return patched


def _get_mechanic(data: dict, key: str, default=None):
    """Read a key from top-level OR nested mechanics dict.

    Checks data[key] first, then data['mechanics'][key].
    Merges both if both exist and are lists.
    """
    top = data.get(key)
    nested = data.get("mechanics", {}).get(key) if isinstance(data.get("mechanics"), dict) else None

    if top is not None and nested is not None:
        # Both exist -- merge if both are lists
        if isinstance(top, list) and isinstance(nested, list):
            seen = set()
            merged = []
            for item in top + nested:
                norm = item.lower() if isinstance(item, str) else item
                if norm not in seen:
                    merged.append(item)
                    seen.add(norm)
            return merged
        # Top-level takes precedence for non-list types
        return top
    if top is not None:
        return top
    if nested is not None:
        return nested
    return default


def build_registry(system_id: str, system_data: dict) -> str:
    """Builds a deep-indexed rules file based on the system schema.

    Returns the output file path.
    """
    system_data = _validate_system_data(system_id, system_data)
    display_name = system_data.get('display_name', system_id)
    print(f"\n>>> Building C.O.D.E.X. Registry for {display_name}...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Build the lookup index
    lookup = {}

    # Flatten races (D&D-style)
    races = _get_mechanic(system_data, 'races', [])
    if races:
        print(f"    -> Mapping {len(races)} Races...")
        for race in races:
            if isinstance(race, str):
                lookup[race.lower()] = {"type": "race", "name": race}

    # Flatten classes & subclasses (D&D-style)
    deep_classes = _get_mechanic(system_data, 'deep_classes', {})
    if deep_classes:
        print(f"    -> Mapping {len(deep_classes)} Core Classes & Subclasses...")
        for main_cls, subs in deep_classes.items():
            lookup[main_cls.lower()] = {"type": "class", "name": main_cls}
            print(f"        * {main_cls} ({len(subs)} subclasses)")
            for sub in subs:
                if isinstance(sub, str):
                    lookup[sub.lower()] = {"type": "subclass", "name": sub, "parent": main_cls}

    # Flatten feats (D&D-style)
    feats = _get_mechanic(system_data, 'feats', [])
    if feats:
        print(f"    -> Mapping {len(feats)} Feats...")
        for feat in feats:
            if isinstance(feat, str):
                lookup[feat.lower()] = {"type": "feat", "name": feat}

    # Flatten archetype categories (FITD/Illuminated)
    archetypes = _get_mechanic(system_data, 'archetype_categories', {})
    if archetypes:
        total = sum(len(v) for v in archetypes.values() if isinstance(v, list))
        if total:
            print(f"    -> Mapping {total} Archetypes...")
        for category, entries in archetypes.items():
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, str):
                        lookup[entry.lower()] = {
                            "type": "archetype",
                            "name": entry,
                            "category": category,
                        }

    # Flatten action maps (FITD/Illuminated)
    core_stats = _get_mechanic(system_data, 'core_stats', {})
    if isinstance(core_stats, dict) and core_stats.get('actions'):
        action_index = _flatten_actions(core_stats)
        if action_index:
            print(f"    -> Mapping {len(action_index)} Actions...")
            lookup.update(action_index)

    # Flatten resources
    resources = _get_mechanic(system_data, 'resources', [])
    if resources:
        print(f"    -> Mapping {len(resources)} Resources...")
        for res in resources:
            if isinstance(res, str):
                lookup[res.lower()] = {"type": "resource", "name": res}

    # Engine metadata tag
    engine = system_data.get('engine', 'custom')
    dice = system_data.get('dice_system', 'custom')

    # Build final registry
    registry_output = {
        "meta": {
            "system_id": system_id,
            "display_name": display_name,
            "engine": engine,
            "dice_system": dice,
            "system_family": system_data.get("system_family", ""),
            "version": "C.O.D.E.X. 2.0",
        },
        "lookup": lookup,
        "structure": system_data,
    }

    # Save the finalized registry
    output_path = os.path.join(OUTPUT_DIR, f"rules_{system_id}.json")
    with open(output_path, 'w') as f:
        json.dump(registry_output, f, indent=4)

    print(f"    SUCCESS: {output_path} ({len(lookup)} indexed entries)")
    return output_path


def build_all(delta_only: bool = True, silent: bool = False) -> int:
    """Build registries for all system configs.  Importable entry point.

    Args:
        delta_only: If True, skip systems whose config hasn't changed
                    since the last build.
        silent: Suppress per-system output (used by Maestro zero-touch).

    Returns:
        Number of registries built.
    """
    available = load_system_configs()
    if not available:
        if not silent:
            print(f"  No system configurations found in {CONFIG_DIR}")
        return 0

    built = 0
    skipped = 0

    for sid in sorted(available.keys()):
        config_path = None
        for fn in os.listdir(CONFIG_DIR):
            if fn.endswith(".json"):
                fp = os.path.join(CONFIG_DIR, fn)
                try:
                    with open(fp, 'r') as f:
                        d = json.load(f)
                    if d.get('system_id', '').upper() == sid:
                        config_path = fp
                        break
                except Exception:
                    pass

        if delta_only and config_path and not _needs_rebuild(sid, config_path):
            skipped += 1
            continue

        build_registry(sid, available[sid])
        built += 1

    if not silent and skipped:
        print(f"\n  Delta check: {skipped} registry(ies) already up-to-date.")

    return built


def main():
    print("--- C.O.D.E.X.: UNIVERSAL REGISTRY BUILDER v2.0 ---")
    available_systems = load_system_configs()

    if not available_systems:
        print(f"  Error: No system configurations found in {CONFIG_DIR}")
        print(f"  TIP: Ensure your rules_*.json files are in: {CONFIG_DIR}")
        return

    # Non-interactive mode for Maestro / CI
    if "--auto" in sys.argv:
        count = build_all(delta_only=("--full" not in sys.argv))
        print(f"\nAuto build complete: {count} registry(ies) built.")
        return

    sids = sorted(list(available_systems.keys()))
    for i, sid in enumerate(sids, 1):
        name = available_systems[sid].get('display_name', sid)
        engine = available_systems[sid].get('engine', '?')
        print(f" [{i}] {name} ({sid}) [{engine}]")

    print(f" [A] Build All")
    print(f" [D] Delta Build (skip unchanged)")

    try:
        choice = input("\nSelect System to Build > ").strip().upper()
        if choice == 'A':
            build_all(delta_only=False)
        elif choice == 'D':
            count = build_all(delta_only=True)
            print(f"\nDelta build complete: {count} built.")
        elif choice.isdigit() and 1 <= int(choice) <= len(sids):
            sid = sids[int(choice)-1]
            build_registry(sid, available_systems[sid])
        else:
            print("Invalid selection.")
    except KeyboardInterrupt:
        print("\nCancelled.")


if __name__ == "__main__":
    main()

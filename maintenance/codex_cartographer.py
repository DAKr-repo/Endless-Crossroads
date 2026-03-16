#!/usr/bin/env python3
"""
codex_cartographer.py -- Vault Map Directory Mirroring
======================================================

Replicates the ``vault/`` directory hierarchy into ``vault_maps/`` so
that each system has a matching folder structure ready for map images.

Family parents (FITD, ILLUMINATED_WORLDS) are descended into just like
the Librarian does, creating per-system map folders.

Usage:
    python maintenance/codex_cartographer.py          # mirror all
    python maintenance/codex_cartographer.py --dry-run # preview only
"""

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from codex.paths import VAULT_DIR, VAULT_MAPS_DIR

_FAMILY_PARENTS = {"FITD", "ILLUMINATED_WORLDS"}


def mirror_vault_hierarchy(dry_run: bool = False) -> list[str]:
    """Create matching directories in vault_maps/ for every leaf vault.

    Returns a list of created (or would-be-created) directory paths.
    """
    created: list[str] = []

    if not VAULT_DIR.exists():
        print(f"[WARN] Vault root not found: {VAULT_DIR}")
        return created

    VAULT_MAPS_DIR.mkdir(parents=True, exist_ok=True)

    for child in sorted(VAULT_DIR.iterdir()):
        if not child.is_dir():
            continue

        if child.name in _FAMILY_PARENTS:
            # Mirror each child system under the family parent
            family_map_dir = VAULT_MAPS_DIR / child.name
            for sub in sorted(child.iterdir()):
                if not sub.is_dir():
                    continue
                target = family_map_dir / sub.name
                if not target.exists():
                    if not dry_run:
                        target.mkdir(parents=True, exist_ok=True)
                    created.append(str(target.relative_to(_ROOT)))
        else:
            # Mirror top-level vault as-is
            target = VAULT_MAPS_DIR / child.name
            if not target.exists():
                if not dry_run:
                    target.mkdir(parents=True, exist_ok=True)
                created.append(str(target.relative_to(_ROOT)))

    # Ensure seeds directory exists
    seeds_dir = VAULT_MAPS_DIR / "seeds"
    if not seeds_dir.exists():
        if not dry_run:
            seeds_dir.mkdir(parents=True, exist_ok=True)
        created.append(str(seeds_dir.relative_to(_ROOT)))

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Mirror vault/ hierarchy into vault_maps/"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview directories that would be created"
    )
    args = parser.parse_args()

    label = "Would create" if args.dry_run else "Created"
    created = mirror_vault_hierarchy(dry_run=args.dry_run)

    if created:
        print(f"[Cartographer] {label} {len(created)} directories:")
        for path in created:
            print(f"  {path}")
    else:
        print("[Cartographer] vault_maps/ hierarchy is already up to date.")


if __name__ == "__main__":
    main()

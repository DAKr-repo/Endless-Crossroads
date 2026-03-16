"""
Graveyard Service -- Universal memorial for fallen heroes.
==========================================================

Records deaths across all chronicles (Burnwillow, Crown, FITD, etc.)
into per-system JSON files under ``vault/graveyard/``.

Each entry contains the character's name, stats snapshot, cause of death,
the dungeon seed (when applicable), and a generated "elegy" line.

Usage:
    from codex.core.services.graveyard import log_death, list_fallen, get_elegy

    log_death({
        "name": "Kael",
        "hp_max": 12,
        "might": 14,
        "wits": 10,
        "cause": "Slain by Root Warden in Room 5",
        "doom": 17,
        "turns": 42,
    }, system_id="burnwillow", seed=314159)
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from codex.paths import VAULT_DIR

_GRAVEYARD_DIR = VAULT_DIR / "graveyard"

# Elegy templates -- rotated by character name hash
_ELEGIES = [
    "The flame endures in memory, long after the ash has cooled.",
    "They walked where shadows dared not tread. Now the shadows carry their name.",
    "No song is sung for those who fall in silence. Let this record be the verse.",
    "The dungeon remembers every footstep. These were the last.",
    "Some fires burn so bright they consume themselves. This was one.",
    "Where the roots grow deepest, the bravest bones lie still.",
    "The Doom Clock stopped, but the echo never fades.",
    "They carried the light as far as they could. Someone else must carry it now.",
]


def _graveyard_path(system_id: str) -> Path:
    """Return the graveyard JSON path for a given system."""
    return _GRAVEYARD_DIR / f"{system_id.lower()}.json"


def _load_graveyard(system_id: str) -> dict:
    """Load or initialize a system graveyard file."""
    path = _graveyard_path(system_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {"system_id": system_id, "fallen": []}


def _save_graveyard(system_id: str, data: dict):
    """Atomically write graveyard data to disk."""
    _GRAVEYARD_DIR.mkdir(parents=True, exist_ok=True)
    path = _graveyard_path(system_id)
    fd, tmp = tempfile.mkstemp(
        dir=str(_GRAVEYARD_DIR), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _generate_elegy(name: str) -> str:
    """Pick an elegy based on character name hash for deterministic variety."""
    idx = sum(ord(c) for c in name) % len(_ELEGIES)
    return _ELEGIES[idx]


def log_death(
    character_data: dict,
    system_id: str,
    seed: Optional[int] = None,
) -> dict:
    """Record a character death in the system graveyard.

    Args:
        character_data: Dict with at minimum ``name``.  May also include
            ``hp_max``, ``might``, ``wits``, ``grit``, ``aether``,
            ``cause``, ``doom``, ``turns``, ``room_id``.
        system_id: Chronicle identifier (e.g. ``burnwillow``, ``bitd``).
        seed: Optional dungeon/session seed for replay reference.

    Returns:
        The tombstone entry that was written.
    """
    name = character_data.get("name", "Unknown")
    entry = {
        "name": name,
        "system_id": system_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "seed": seed,
        "elegy": _generate_elegy(name),
        "hp_max": character_data.get("hp_max"),
        "might": character_data.get("might"),
        "wits": character_data.get("wits"),
        "grit": character_data.get("grit"),
        "aether": character_data.get("aether"),
        "cause": character_data.get("cause", "Fell in the darkness"),
        "doom": character_data.get("doom"),
        "turns": character_data.get("turns"),
        "room_id": character_data.get("room_id"),
    }

    graveyard = _load_graveyard(system_id)
    graveyard["fallen"].append(entry)
    _save_graveyard(system_id, graveyard)
    return entry


def list_fallen(system_id: Optional[str] = None) -> Dict[str, List[dict]]:
    """Return fallen heroes grouped by system.

    If *system_id* is provided, returns only that system's fallen.
    Otherwise scans all graveyard files.
    """
    _GRAVEYARD_DIR.mkdir(parents=True, exist_ok=True)
    result: Dict[str, List[dict]] = {}

    if system_id:
        data = _load_graveyard(system_id)
        if data["fallen"]:
            result[system_id] = data["fallen"]
        return result

    for path in sorted(_GRAVEYARD_DIR.iterdir()):
        if path.suffix == ".json":
            sid = path.stem
            try:
                data = json.loads(path.read_text())
                fallen = data.get("fallen", [])
                if fallen:
                    result[sid] = fallen
            except (json.JSONDecodeError, KeyError):
                continue

    return result


def get_elegy(system_id: str, name: str) -> Optional[dict]:
    """Retrieve a specific tombstone entry by name (most recent match)."""
    graveyard = _load_graveyard(system_id)
    name_lower = name.lower()
    for entry in reversed(graveyard["fallen"]):
        if entry.get("name", "").lower() == name_lower:
            return entry
    return None


def get_graveyard_systems() -> List[str]:
    """Return list of system IDs that have graveyard data."""
    _GRAVEYARD_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        p.stem for p in _GRAVEYARD_DIR.iterdir()
        if p.suffix == ".json"
    )

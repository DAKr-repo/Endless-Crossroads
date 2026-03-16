"""
codex.core.character_export — Character Portability (WO-V62.0 Track A)
======================================================================

Export characters from one session to import into another.
Supports same-system import (exact transfer) and cross-system import
(lossy conversion via portable stats).

Export format:
  - All original character fields are preserved verbatim.
  - ``_export_meta`` dict records provenance (system_id, exported_at, etc.).
  - ``_portable_stats`` dict carries system-agnostic fields for cross-system
    import (name, level, hp_ratio, combat_style, notable_items).

Cross-system import maps combat_style to a system-specific class/playbook
via _PORTABLE_CLASS_MAP.  Unknown target systems return None.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_CHARACTERS_DIR = Path("saves/characters")

# Maps combat_style to system-specific class/playbook.
# Follows the COMPANION_CLASS_MAP pattern from WO-V61.0.
# All systems must provide exactly four combat styles:
#   melee, ranged, magic, support
_PORTABLE_CLASS_MAP: Dict[str, Dict[str, str]] = {
    "burnwillow": {
        "melee": "Warrior",
        "ranged": "Ranger",
        "magic": "Arcanist",
        "support": "Healer",
    },
    "dnd5e": {
        "melee": "Fighter",
        "ranged": "Ranger",
        "magic": "Wizard",
        "support": "Cleric",
    },
    "stc": {
        "melee": "Windrunner",
        "ranged": "Edgedancer",
        "magic": "Lightweaver",
        "support": "Truthwatcher",
    },
    "bitd": {
        "melee": "Cutter",
        "ranged": "Lurk",
        "magic": "Whisper",
        "support": "Leech",
    },
    "sav": {
        "melee": "Muscle",
        "ranged": "Pilot",
        "magic": "Mystic",
        "support": "Mechanic",
    },
    "bob": {
        "melee": "Heavy",
        "ranged": "Scout",
        "magic": "Medic",
        "support": "Officer",
    },
    "cbrpnk": {
        "melee": "Punk",
        "ranged": "Hacker",
        "magic": "Decker",
        "support": "Medtech",
    },
    "candela": {
        "melee": "Face",
        "ranged": "Slink",
        "magic": "Weird",
        "support": "Scholar",
    },
    "crown": {
        "melee": "Knight",
        "ranged": "Spy",
        "magic": "Advisor",
        "support": "Diplomat",
    },
}


def _infer_combat_style(char_data: dict) -> str:
    """Infer combat style from character data heuristics.

    Priority order:
      1. ``playbook`` field (FITD systems).
      2. ``class`` field (D&D-style systems).
      3. Stat block — highest stat wins.
      4. Default: "melee".

    Args:
        char_data: Raw character dict from any game engine.

    Returns:
        One of: "melee", "ranged", "magic", "support".
    """
    # Check for explicit class/playbook
    playbook = char_data.get("playbook", "").lower()
    char_class = char_data.get("class", "").lower()
    role = playbook or char_class

    if any(w in role for w in ("fighter", "cutter", "warrior", "heavy", "muscle", "knight", "punk")):
        return "melee"
    if any(w in role for w in ("ranger", "lurk", "scout", "pilot", "hacker", "slink", "spy")):
        return "ranged"
    if any(w in role for w in ("wizard", "whisper", "mystic", "decker", "weird", "arcanist", "advisor",
                                "lightweaver", "windrunner")):
        return "magic"
    if any(w in role for w in ("cleric", "leech", "mechanic", "medic", "medtech", "scholar", "healer",
                                "diplomat", "edgedancer", "truthwatcher")):
        return "support"

    # Fallback: check stats
    stats = char_data.get("stats", {})
    if isinstance(stats, dict):
        str_val = stats.get("strength", stats.get("str", 0))
        int_val = stats.get("intelligence", stats.get("int", 0))
        wis_val = stats.get("wisdom", stats.get("wis", 0))
        dex_val = stats.get("dexterity", stats.get("dex", 0))
        if str_val >= max(int_val, wis_val, dex_val):
            return "melee"
        if dex_val >= max(str_val, int_val, wis_val):
            return "ranged"
        if int_val >= max(str_val, wis_val, dex_val):
            return "magic"
        return "support"

    return "melee"  # Default


def export_character(char_data: dict, system_id: str,
                     campaign_id: Optional[str] = None) -> dict:
    """Export a character as a portable dict.

    The returned dict is a shallow copy of char_data with two extra keys:
      - ``_export_meta``: provenance information.
      - ``_portable_stats``: system-agnostic stats for cross-system import.

    Args:
        char_data: Raw character dict from any game engine.
        system_id: The engine that owns this character (e.g. "burnwillow").
        campaign_id: Optional campaign identifier for provenance tracking.

    Returns:
        Export dict suitable for JSON serialization and later import.
    """
    max_hp = char_data.get("max_hp", char_data.get("hp", 10))
    current_hp = char_data.get("current_hp", max_hp)
    hp_ratio = current_hp / max(1, max_hp)

    portable: Dict[str, object] = {
        "name": char_data.get("name", "Unknown"),
        "level": char_data.get("level", 1),
        "hp_ratio": round(hp_ratio, 2),
        "combat_style": _infer_combat_style(char_data),
        "notable_items": [],
    }

    # Extract up to five notable items from gear/inventory
    gear = char_data.get("gear", char_data.get("inventory", []))
    if isinstance(gear, list):
        for item in gear[:5]:
            if isinstance(item, dict):
                portable["notable_items"].append(item.get("name", str(item)))  # type: ignore[union-attr]
            elif isinstance(item, str):
                portable["notable_items"].append(item)  # type: ignore[union-attr]

    export = dict(char_data)  # Preserve all original character fields
    export["_export_meta"] = {
        "system_id": system_id,
        "exported_at": datetime.now().isoformat(),
        "source_campaign": campaign_id,
        "level": portable["level"],
    }
    export["_portable_stats"] = portable

    return export


def save_exported_character(export_data: dict) -> Path:
    """Save an exported character to disk.

    File is written to ``saves/characters/<name>_<system_id>.json``.
    The directory is created if it does not exist.

    Args:
        export_data: Dict as returned by export_character().

    Returns:
        Path to the written file.
    """
    _CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    name = export_data.get("name", "unknown").replace(" ", "_").lower()
    system_id = export_data.get("_export_meta", {}).get("system_id", "unknown")
    filename = f"{name}_{system_id}.json"
    path = _CHARACTERS_DIR / filename
    path.write_text(json.dumps(export_data, indent=2, default=str))
    return path


def import_character(export_data: dict, target_system_id: str) -> Optional[dict]:
    """Import a character into a target system.

    Same-system import: returns a clean copy of the character with export
    metadata stripped — a full-fidelity transfer.

    Cross-system import: builds a minimal character dict from ``_portable_stats``
    and maps combat_style to the target system's class/playbook via
    ``_PORTABLE_CLASS_MAP``.  Returns None if the target system is unknown
    or if ``_portable_stats`` is missing.

    Args:
        export_data: Dict as returned by export_character().
        target_system_id: The engine that will receive this character.

    Returns:
        Character dict ready for the target engine, or None on failure.
    """
    meta = export_data.get("_export_meta", {})
    source_system = meta.get("system_id", "")

    if source_system == target_system_id:
        # Same system: direct import — strip export metadata
        char = dict(export_data)
        char.pop("_export_meta", None)
        char.pop("_portable_stats", None)
        return char

    # Cross-system: use portable stats
    portable = export_data.get("_portable_stats")
    if not portable:
        return None

    target_map = _PORTABLE_CLASS_MAP.get(target_system_id)
    if not target_map:
        return None

    combat_style = portable.get("combat_style", "melee")
    target_class = target_map.get(combat_style, "Fighter")

    return {
        "name": portable["name"],
        "level": portable.get("level", 1),
        "class": target_class,
        "combat_style": combat_style,
        "hp_ratio": portable.get("hp_ratio", 1.0),
        "notable_items": portable.get("notable_items", []),
        "_imported_from": source_system,
        "_cross_system": True,
    }


def list_exported_characters(system_id: Optional[str] = None) -> List[dict]:
    """List all exported character files, optionally filtered by system.

    Each entry in the returned list contains the file metadata (name, path,
    export_meta fields) but not the full character data — call
    ``json.loads(Path(entry["path"]).read_text())`` to get the full export.

    Args:
        system_id: If provided, only return characters exported from this system.

    Returns:
        List of metadata dicts, sorted alphabetically by filename.
    """
    if not _CHARACTERS_DIR.exists():
        return []
    chars = []
    for f in sorted(_CHARACTERS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, IOError):
            continue
        meta = data.get("_export_meta", {})
        if system_id is not None and meta.get("system_id") != system_id:
            continue
        chars.append({
            "file": f.name,
            "path": str(f),
            "name": data.get("name", "Unknown"),
            **meta,
        })
    return chars

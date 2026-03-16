"""
codex.forge.reference_data.loader -- Reference Data Loader with JSON Overrides
===============================================================================

Loads reference data from hardcoded Python dicts with optional JSON override
support. JSON files in vault/{system}/reference/{category}.json take priority
over hardcoded data, allowing future PDFs to auto-generate overrides via the
extractor without modifying code.

Priority: JSON override > hardcoded Python dict
Merge strategy: JSON entries win on key conflicts; hardcoded entries preserved otherwise.
"""

import json
import os
from typing import Any, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def load_reference(category: str, system_id: str = "dnd5e") -> dict:
    """Load reference data with JSON override support.

    Args:
        category: Data category name (e.g., "subraces", "subclasses", "feats",
                  "skills", "equipment", "spells", "backgrounds", "personality")
        system_id: Game system identifier (default "dnd5e")

    Returns:
        Merged dict with JSON overrides taking priority over hardcoded data.

    Lookup order:
        1. vault/{system_id}/reference/{category}.json (if exists)
        2. codex.forge.reference_data.{system_id}.{CATEGORY_MAPPING[category]}

    If both exist, deep-merge with JSON winning on conflicts.
    """
    # Load hardcoded base data
    base = _load_hardcoded(category, system_id)

    # Check for JSON override
    override_path = os.path.join(_ROOT, "vault", system_id, "reference", f"{category}.json")
    if os.path.isfile(override_path):
        try:
            with open(override_path, "r", encoding="utf-8") as f:
                override = json.load(f)
            return _deep_merge(base, override)
        except (json.JSONDecodeError, IOError):
            pass

    return base


def _load_hardcoded(category: str, system_id: str) -> dict:
    """Load hardcoded reference data from Python modules."""
    # Map category names to module attribute names
    CATEGORY_MAP = {
        "subraces": "SUBRACES",
        "subclasses": "SUBCLASSES",
        "feats": "FEATS",
        "skills": "SKILLS",
        "class_skills": "CLASS_SKILL_CHOICES",
        "backgrounds": "BACKGROUND_SKILLS",
        "equipment": "EQUIPMENT_CATALOG",
        "starting_equipment": "STARTING_EQUIPMENT",
        "spells": "SPELL_LISTS",
        "spellcasting": "SPELLCASTING",
        "personality": "PERSONALITY",
        "alignments": "ALIGNMENTS",
        "saving_throws": "SAVING_THROW_PROFICIENCIES",
        # Tasha's Cauldron of Everything
        "life_path": "LIFE_PATH_TABLES",
        "dark_secrets": "DARK_SECRETS",
        "group_patrons": "GROUP_PATRONS",
        "optional_features": "OPTIONAL_CLASS_FEATURES",
        "custom_lineage": "CUSTOM_LINEAGE",
    }

    attr_name = CATEGORY_MAP.get(category, category.upper())

    try:
        if system_id == "dnd5e":
            from codex.forge.reference_data import dnd5e
            return getattr(dnd5e, attr_name, {})
        elif system_id == "bitd":
            from codex.forge.reference_data import bitd
            return getattr(bitd, attr_name, {})
        elif system_id == "sav":
            from codex.forge.reference_data import sav
            return getattr(sav, attr_name, {})
        elif system_id == "bob":
            from codex.forge.reference_data import bob
            return getattr(bob, attr_name, {})
        elif system_id == "cbrpnk":
            from codex.forge.reference_data import cbrpnk
            return getattr(cbrpnk, attr_name, {})
        elif system_id == "candela":
            from codex.forge.reference_data import candela
            return getattr(candela, attr_name, {})
        elif system_id == "stc":
            from codex.forge.reference_data import stc
            return getattr(stc, attr_name, {})
        elif system_id == "crown":
            from codex.forge.reference_data import crown
            return getattr(crown, attr_name, {})
    except ImportError:
        pass

    return {}


def _deep_merge(base: Any, override: Any) -> Any:
    """Deep merge two dicts. Override values take priority.

    - Dict + Dict: merge keys recursively
    - List + List: override replaces entirely
    - Any + Any: override wins
    """
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for key, value in override.items():
            if key in result:
                result[key] = _deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    return override


def get_available_sources(vault_path: Optional[str] = None) -> set:
    """Get set of available source books from vault.

    Delegates to source_scanner but provides a stable API for reference data.
    """
    try:
        from codex.forge.source_scanner import scan_content_availability
        return scan_content_availability(vault_path)
    except ImportError:
        return {"Core"}


def filter_by_source(items: list, available_sources: set) -> list:
    """Filter reference data items by available sources.

    Args:
        items: List of dicts with "source" keys
        available_sources: Set of available source keywords

    Source mapping:
        "PHB" -> "Core"
        "XGE" -> "Xanathar"
        "TCE" -> "Tasha"
        "SCAG" -> "Sword Coast"
        "VGM" -> "Core" (treat as core for availability)
        "ERLW" -> "Eberron"
    """
    SOURCE_MAP = {
        "PHB": "Core",
        "XGE": "Xanathar",
        "TCE": "Tasha",
        "SCAG": "Sword Coast",
        "VGM": "Core",
        "ERLW": "Eberron",
        "DMG": "Core",
    }

    return [
        item for item in items
        if SOURCE_MAP.get(item.get("source", "PHB"), "Core") in available_sources
    ]

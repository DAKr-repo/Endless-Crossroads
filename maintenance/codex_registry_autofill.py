"""
codex_registry_autofill.py -- Unified Registry Autofill (V3.0)
==============================================================

Sole automation agent for populating config/systems/ rules JSONs.
Combines three data sources in priority order:

  1. **MASTER_REGISTRY** — hardcoded official taxonomy (stats, classes,
     subclasses, races) that serves as the static ground truth.
  2. **Filesystem Crawler** — scans vault subdirectories for file-based
     homebrew content (PDFs in CLASSES/, SUBCLASSES/, RACES/ folders).
  3. **AI Extraction** (optional) — queries the FAISS index via
     ``codex.integrations.mimir.query_mimir`` to discover content not
     captured by the first two sources.  Gracefully degrades if Ollama
     or the mimir module is unavailable.

Merge logic is non-destructive: existing user edits in rules JSONs are
preserved.  New entries are appended without duplicates.

Replaces the deprecated codex_registry_autopilot.py and the old
codex_tools-dependent autofill.

Usage:
    python maintenance/codex_registry_autofill.py          # interactive
    python maintenance/codex_registry_autofill.py --auto   # zero-touch

Importable:
    from maintenance.codex_registry_autofill import autofill_all
    count = autofill_all(silent=True)
"""

import json
import glob
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Ensure project root is on sys.path (needed when run as subprocess)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# --- CONFIGURATION ---
BASE_DIR = Path(_PROJECT_ROOT)   # Project root
CONFIG_DIR = BASE_DIR / "config" / "systems"
VAULT_DIR = BASE_DIR / "vault"

from maintenance.codex_utils import log_event

# Family parent directories (contain child vaults, not PDFs directly)
FAMILY_PARENTS = {"FITD", "ILLUMINATED_WORLDS"}

# --- COLORS ---
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"


# =========================================================================
# SOURCE 1: MASTER REGISTRY — Official Static Taxonomy
# =========================================================================

MASTER_REGISTRY: Dict[str, dict] = {
    "DND5E": {
        "name": "Dungeons & Dragons 5th Edition",
        "mechanics": {
            "stats": ["STR", "DEX", "CON", "INT", "WIS", "CHA"],
            "resources": [
                "HP", "Hit Dice", "Spell Slots", "Ki",
                "Sorcery Points", "Rage", "Superiority Dice",
            ],
            "classes": [
                "Artificer", "Barbarian", "Bard", "Cleric", "Druid",
                "Fighter", "Monk", "Paladin", "Ranger", "Rogue",
                "Sorcerer", "Warlock", "Wizard",
            ],
            "subclasses": [
                "Berserker", "Totem Warrior", "Ancestral Guardian", "Zealot",
                "Lore", "Valor", "Glamour", "Swords", "Whispers",
                "Life", "Light", "Nature", "Tempest", "Trickery", "War",
                "Grave", "Forge",
                "Land", "Moon", "Dreams", "Shepherd", "Spores",
                "Champion", "Battle Master", "Eldritch Knight",
                "Arcane Archer", "Cavalier", "Samurai", "Echo Knight",
                "Open Hand", "Shadow", "Four Elements", "Drunken Master",
                "Kensei",
                "Devotion", "Ancients", "Vengeance", "Conquest", "Redemption",
                "Hunter", "Beast Master", "Gloom Stalker", "Horizon Walker",
                "Monster Slayer",
                "Thief", "Assassin", "Arcane Trickster", "Inquisitive",
                "Mastermind", "Scout", "Swashbuckler",
                "Draconic", "Wild Magic", "Divine Soul", "Storm",
                "Archfey", "Fiend", "Great Old One", "Celestial", "Hexblade",
                "Abjuration", "Conjuration", "Divination", "Enchantment",
                "Evocation", "Illusion", "Necromancy", "Transmutation",
                "Bladesinging",
            ],
            "races": [
                "Human", "Elf", "Dwarf", "Halfling", "Dragonborn", "Gnome",
                "Half-Elf", "Half-Orc", "Tiefling", "Aasimar", "Firbolg",
                "Goliath", "Kenku", "Lizardfolk", "Tabaxi", "Triton",
                "Genasi", "Warforged", "Changeling",
            ],
        },
    },
    "BITD": {
        "name": "Blades in the Dark",
        "mechanics": {
            "stats": ["Insight", "Prowess", "Resolve"],
            "resources": ["Stress", "Trauma", "Coin", "Heat", "Rep",
                          "Wanted Level"],
            "classes": ["Cutter", "Hound", "Leech", "Lurk", "Slide",
                        "Spider", "Whisper"],
            "subclasses": ["Assassin", "Brave", "Bruiser", "Hunter",
                           "Ghost", "Skulk"],
        },
    },
    "STC": {
        "name": "Stormlight / Cosmere RPG",
        "mechanics": {
            "stats": ["Strength", "Speed", "Intellect", "Will",
                      "Awareness", "Presence"],
            "resources": ["Investiture", "Stormlight", "Focus"],
            "classes": [
                "Windrunner", "Skybreaker", "Dustbringer", "Edgedancer",
                "Truthwatcher", "Lightweaver", "Elsecaller", "Willshaper",
                "Stoneward", "Bondsmith",
            ],
            "subclasses": ["Squire", "Radiant", "Living Shard"],
        },
    },
    "BOB": {
        "name": "Band of Blades",
        "mechanics": {
            "stats": ["Insight", "Prowess", "Resolve"],
            "resources": ["Stress", "Trauma", "Morale", "Supply"],
            "classes": ["Rookie", "Soldier", "Medic", "Sniper", "Heavy",
                        "Officer", "Specialist"],
            "subclasses": [],
        },
    },
    "SAV": {
        "name": "Scum and Villainy",
        "mechanics": {
            "stats": ["Insight", "Prowess", "Resolve"],
            "resources": ["Stress", "Cred", "Heat", "Gambits"],
            "classes": ["Mechanic", "Muscle", "Mystic", "Pilot",
                        "Scoundrel", "Speaker", "Stitch"],
            "subclasses": [],
        },
    },
    "CBR_PNK": {
        "name": "CBR+PNK",
        "mechanics": {
            "stats": ["Insight", "Prowess", "Resolve"],
            "resources": ["Stress"],
            "classes": [],
            "subclasses": [],
            "actions": ["Hack", "Prowl", "Skirmish", "Study",
                        "Survey", "Tinker", "Consort", "Sway"],
        },
    },
    "CANDELA_OBSCURA": {
        "name": "Candela Obscura",
        "mechanics": {
            "stats": ["Nerve", "Cunning", "Intuition"],
            "resources": ["Marks", "Scars"],
            "classes": [],
            "subclasses": [],
            "actions": ["Strike", "Control", "Move", "Hide",
                        "Sneak", "Sense", "Conduct", "Survey", "Read"],
        },
    },
    "BURNWILLOW": {
        "name": "Burnwillow",
        "mechanics": {
            "stats": ["Vigor", "Flow", "Focus"],
            "resources": ["Health", "Energy", "Will"],
            "classes": [],
            "subclasses": [],
        },
    },
}


# =========================================================================
# DELTA SYNC — Skip systems that are already up-to-date
# =========================================================================

AUTOFILL_MANIFEST = VAULT_DIR / "vault_manifest.json"


def _needs_autofill(system_id: str) -> bool:
    """Check if a system needs autofill by comparing timestamps.

    Returns True if autofill should run for this system:
    - Rules JSON doesn't exist yet
    - Vault manifest is newer than the rules JSON (new PDFs indexed)
    - Rules JSON has zero mechanics entries (empty config)

    Returns False if the rules JSON is up-to-date.
    """
    rules_path = CONFIG_DIR / f"rules_{system_id}.json"

    # No rules file at all -- needs autofill
    if not rules_path.exists():
        return True

    # Check if vault manifest is newer than the rules JSON
    if AUTOFILL_MANIFEST.exists():
        try:
            manifest_mtime = AUTOFILL_MANIFEST.stat().st_mtime
            rules_mtime = rules_path.stat().st_mtime
            if manifest_mtime > rules_mtime:
                return True
        except OSError:
            pass

    # Check if the rules JSON has zero mechanics entries
    try:
        data = json.loads(rules_path.read_text())
        mechanics = data.get("mechanics", {})
        total = sum(len(v) for v in mechanics.values() if isinstance(v, list))
        if total == 0:
            return True
    except (json.JSONDecodeError, OSError):
        return True

    return False


# =========================================================================
# SOURCE 2: FILESYSTEM CRAWLER — Homebrew Discovery
# =========================================================================

# Subfolder names that map to mechanic keys
_FOLDER_KEY_MAP = {
    "CLASSES": "classes",
    "SUBCLASSES": "subclasses",
    "ARCHETYPES": "subclasses",
    "RACES": "races",
    "SPECIES": "races",
}


def _clean_filename(filename: str) -> str:
    """Strip extension and leading 'The ' from a filename."""
    name = os.path.splitext(filename)[0]
    return name.replace("The ", "").strip()


def crawl_for_homebrew(system_path: str) -> Dict[str, List[str]]:
    """Scan a vault directory for file-based homebrew content."""
    discovered: Dict[str, List[str]] = {}
    if not os.path.exists(system_path):
        return discovered

    for folder in os.listdir(system_path):
        folder_path = os.path.join(system_path, folder)
        if not os.path.isdir(folder_path):
            continue
        key = _FOLDER_KEY_MAP.get(folder.upper())
        if not key:
            continue

        files = glob.glob(os.path.join(folder_path, "*"))
        names = [
            _clean_filename(os.path.basename(f))
            for f in files
            if f.lower().endswith((".pdf", ".txt", ".md"))
        ]
        if names:
            discovered[key] = names
            print(f"      + Crawler found {key}: {names}")

    return discovered


# =========================================================================
# SOURCE 3: AI EXTRACTION (optional, graceful degradation)
# =========================================================================

def _try_ai_extract(system_id: str, system_name: str,
                    key: str, query: str) -> List[str]:
    """Attempt to extract a list from the FAISS index via Mimir.

    Returns an empty list if Mimir, Ollama, or the index is unavailable.
    """
    try:
        from codex.integrations.mimir import query_mimir
    except ImportError:
        return []

    prompt = (
        f"Extract a JSON list of distinct {query} from {system_name}. "
        f"Return ONLY a valid JSON list of strings. "
        f'Example: ["Item 1", "Item 2"]'
    )
    context = f"system_id={system_id}"

    try:
        raw = query_mimir(prompt, context, namespace=system_id)
        # Try to parse JSON from the response
        import re
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return []


# =========================================================================
# MERGE LOGIC — Non-destructive deduplication
# =========================================================================

def merge_mechanics(base: dict, new_data: dict) -> dict:
    """Merge new lists into base lists without duplicates."""
    for key, items in new_data.items():
        if key not in base:
            base[key] = []

        current_set = {v.lower() if isinstance(v, str) else v
                       for v in base[key]}
        for item in items:
            if isinstance(item, str) and item.lower() not in current_set:
                base[key].append(item)
                current_set.add(item.lower())

        if all(isinstance(v, str) for v in base[key]):
            base[key].sort()

    return base


# =========================================================================
# AUTOFILL PIPELINE
# =========================================================================

def autofill_system(system_id: str, master_data: Optional[dict] = None,
                    use_ai: bool = True, silent: bool = False) -> bool:
    """Autofill a single system's rules JSON.

    Layers data from MASTER_REGISTRY -> filesystem crawler -> AI extraction.
    Returns True if the file was modified.
    """
    log_event("AUTOFILL", f"Processing system: {system_id}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    filepath = CONFIG_DIR / f"rules_{system_id}.json"

    # Load existing config or start from master template
    existing: dict = {}
    if filepath.exists():
        try:
            existing = json.loads(filepath.read_text())
            if not silent:
                print(f"      Loaded existing {filepath.name}")
        except Exception:
            existing = {}

    current_mechanics = existing.get("mechanics", {})

    # Complete opt-out: if config has _no_registry_merge, skip ALL layers and write nothing
    if existing.get("_no_registry_merge"):
        if not silent:
            print(f"      All layers: Skipped (_no_registry_merge flag set)")
            total = sum(len(v) for v in current_mechanics.values() if isinstance(v, list))
            print(f"      Synced: {filepath.name} ({total} total entries)")
        return False  # No modification

    # Layer 1: MASTER_REGISTRY static data
    # Skip merge if config explicitly opts out (prevents garbage data injection)
    if existing.get("_no_ai_extract") and not master_data:
        pass  # No master data to merge anyway
    elif master_data:
        master_mechanics = master_data.get("mechanics", {})
        current_mechanics = merge_mechanics(current_mechanics, master_mechanics)
        if not silent:
            print(f"      Layer 1: Master Registry applied")

    # Layer 2: Filesystem crawler
    # Try direct vault path, then inside family parents
    system_path = str(VAULT_DIR / system_id.lower())
    if not os.path.exists(system_path):
        for family in FAMILY_PARENTS:
            candidate = str(VAULT_DIR / family / system_id.lower())
            if os.path.exists(candidate):
                system_path = candidate
                break

    homebrew = crawl_for_homebrew(system_path)
    if homebrew:
        current_mechanics = merge_mechanics(current_mechanics, homebrew)
        if not silent:
            print(f"      Layer 2: Filesystem crawler found {len(homebrew)} categories")
    elif not silent:
        print(f"      Layer 2: No homebrew files found")

    # Layer 3: AI extraction (optional)
    # Skip AI extraction if the config explicitly opts out (prevents garbage data injection)
    if existing.get("_no_ai_extract") or existing.get("mechanics", {}).get("_no_ai_extract"):
        use_ai = False
        if not silent:
            print(f"      Layer 3: Skipped (config has _no_ai_extract flag)")
    if use_ai:
        ai_found = 0
        display_name = (master_data or {}).get("name", system_id)
        for key, query in [
            ("races", f"playable races or species in {display_name}"),
            ("classes", f"character classes or playbooks in {display_name}"),
            ("subclasses", f"subclasses or specializations in {display_name}"),
        ]:
            # Skip if already well-populated
            if len(current_mechanics.get(key, [])) > 5:
                continue
            items = _try_ai_extract(system_id, display_name, key, query)
            if items:
                current_mechanics = merge_mechanics(
                    current_mechanics, {key: items}
                )
                ai_found += len(items)
        if not silent:
            if ai_found:
                print(f"      Layer 3: AI extracted {ai_found} entries")
            else:
                print(f"      Layer 3: AI extraction unavailable or no new data")

    # Assemble the output (preserve all existing keys)
    output = dict(existing)
    output["system_id"] = output.get("system_id", system_id)
    output["display_name"] = output.get(
        "display_name",
        (master_data or {}).get("name", system_id)
    )
    output["mechanics"] = current_mechanics

    # Write
    filepath.write_text(json.dumps(output, indent=4))
    if not silent:
        total = sum(len(v) for v in current_mechanics.values()
                    if isinstance(v, list))
        print(f"      Synced: {filepath.name} ({total} total entries)")

    return True


def autofill_all(use_ai: bool = True, silent: bool = False) -> int:
    """Autofill all known systems.  Importable entry point for Maestro.

    Processes every system in MASTER_REGISTRY, plus any vault directories
    that aren't covered by the master list.

    Returns number of systems processed.
    """
    log_event("AUTOFILL", "=== AUTOFILL RUN START ===")
    processed = 0
    skipped = 0

    # Process systems in MASTER_REGISTRY
    for sid, data in sorted(MASTER_REGISTRY.items()):
        if not _needs_autofill(sid):
            skipped += 1
            if not silent:
                print(f"\n   Delta: {sid} up-to-date")
            continue
        if not silent:
            print(f"\n   [{sid}] {data['name']}")
        autofill_system(sid, master_data=data, use_ai=use_ai, silent=silent)
        processed += 1

    # Also process vault systems not in MASTER_REGISTRY
    if VAULT_DIR.exists():
        known_sids = {s.upper() for s in MASTER_REGISTRY}
        for entry in sorted(VAULT_DIR.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name in FAMILY_PARENTS:
                for child in sorted(entry.iterdir()):
                    if child.is_dir():
                        sid = child.name.upper().replace(" ", "_")
                        if sid not in known_sids:
                            if not _needs_autofill(sid):
                                skipped += 1
                                if not silent:
                                    print(f"\n   Delta: {sid} up-to-date")
                                continue
                            if not silent:
                                print(f"\n   [{sid}] (vault-discovered, family={entry.name})")
                            autofill_system(sid, use_ai=use_ai, silent=silent)
                            processed += 1
            else:
                sid = entry.name.upper().replace(" ", "_")
                if sid not in known_sids:
                    if not _needs_autofill(sid):
                        skipped += 1
                        if not silent:
                            print(f"\n   Delta: {sid} up-to-date")
                        continue
                    if not silent:
                        print(f"\n   [{sid}] (vault-discovered)")
                    autofill_system(sid, use_ai=use_ai, silent=silent)
                    processed += 1

    if skipped and not silent:
        print(f"\n   Delta sync: {skipped} system(s) already up-to-date.")

    log_event("AUTOFILL", f"=== AUTOFILL RUN COMPLETE: {processed} processed, {skipped} skipped ===")
    return processed


# =========================================================================
# CLI ENTRY POINT
# =========================================================================

def main():
    print(f"{CYAN}--- C.O.D.E.X. REGISTRY AUTOFILL V3.0 ---{RESET}")
    print(f"Config dir: {CONFIG_DIR}")
    print(f"Vault dir:  {VAULT_DIR}")

    use_ai = "--no-ai" not in sys.argv

    if "--auto" in sys.argv:
        count = autofill_all(use_ai=use_ai)
        print(f"\n{GREEN}Autofill complete: {count} system(s) processed.{RESET}")
        return

    # Interactive mode
    sids = sorted(MASTER_REGISTRY.keys())
    for i, sid in enumerate(sids, 1):
        print(f" [{i}] {MASTER_REGISTRY[sid]['name']} ({sid})")
    print(f" [A] Autofill All")

    choice = input(f"\n{CYAN}Select > {RESET}").strip().upper()

    if choice == "A":
        count = autofill_all(use_ai=use_ai)
        print(f"\n{GREEN}Done: {count} system(s) processed.{RESET}")
    elif choice.isdigit() and 1 <= int(choice) <= len(sids):
        sid = sids[int(choice) - 1]
        autofill_system(sid, master_data=MASTER_REGISTRY[sid], use_ai=use_ai)
    else:
        print(f"{RED}Invalid selection.{RESET}")

    print(f"\n{CYAN}Next: run codex_registry_builder.py to compile.{RESET}")


if __name__ == "__main__":
    main()

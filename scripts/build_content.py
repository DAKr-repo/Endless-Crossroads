"""
scripts/build_content.py — Unified Content Extraction Pipeline
===============================================================
Orchestrates extraction of structured game content from vault PDFs
into config JSON files.  Pluggable extractors per content type,
with optional LLM classification via qwen3.5:2b for ambiguous chunks.

Usage:
    python scripts/build_content.py --all                    # All extractors, all systems
    python scripts/build_content.py --system dnd5e           # All extractors, one system
    python scripts/build_content.py --extract bestiary        # One extractor, all systems
    python scripts/build_content.py --extract bestiary,loot   # Multiple extractors
    python scripts/build_content.py --no-llm                  # Regex only, skip LLM
    python scripts/build_content.py --force                   # Rebuild existing configs
    python scripts/build_content.py --dry-run                 # Show what would be extracted
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = PROJECT_ROOT / "vault"
CONFIG_ROOT = PROJECT_ROOT / "config"

# Reuse discovery from build_indices
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
try:
    from build_indices import discover_systems, extract_pdf_text, chunk_text
except ImportError:
    # Fallback stubs if build_indices unavailable
    def discover_systems(vault_root: Path) -> dict:
        """Fallback discover_systems — handles flat and group vault layouts.

        Flat:  vault/<system>/SOURCE/*.pdf + vault/<system>/MODULES/*.pdf
        Group: vault/<group>/<system>/SOURCE/*.pdf  (e.g. FITD/bitd)

        WO-V157: Now scans both SOURCE/ and MODULES/ (and MODULE/).
        Module PDFs contain bestiary entries, NPCs, locations, and
        read_aloud text needed by the extraction pipeline.
        """
        _DIR_TO_ID = {"Candela_Obscura": "candela", "CBR_PNK": "cbrpnk"}
        systems = {}
        if not vault_root.exists():
            return systems

        def _collect(system_dir: Path) -> None:
            """Collect ALL PDFs from a system directory tree.

            WO-V157: Scans all subdirectories — SOURCE/, MODULES/, MODULE/,
            SETTINGS/, SUPPLEMENTS/, and any other subfolders.
            """
            pdfs = sorted(system_dir.rglob("*.pdf")) + sorted(system_dir.rglob("*.PDF"))
            unique = list(dict.fromkeys(pdfs))
            if unique:
                system_id = _DIR_TO_ID.get(system_dir.name, system_dir.name)
                systems[system_id] = unique

        for d in sorted(vault_root.iterdir()):
            if not d.is_dir():
                continue
            has_pdfs = any(d.rglob("*.pdf")) or any(d.rglob("*.PDF"))
            if has_pdfs:
                _collect(d)
            else:
                for child in sorted(d.iterdir()):
                    if child.is_dir():
                        if any(child.rglob("*.pdf")) or any(child.rglob("*.PDF")):
                            _collect(child)
        return systems

    def extract_pdf_text(pdf_path: Path) -> list:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return [p.extract_text().strip() for p in reader.pages
                if (p.extract_text() or "").strip()]

    def chunk_text(text, chunk_size=500, overlap=50):
        if not text:
            return
        step = max(1, chunk_size - overlap)
        start = 0
        while start < len(text):
            chunk = text[start:start + chunk_size].strip()
            if chunk:
                yield chunk
            start += step


console = Console()

# ---------------------------------------------------------------------------
# LLM Classification (Tier 2)
# ---------------------------------------------------------------------------

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
CLASSIFY_MODEL = "qwen3.5:2b"
LLM_COOLDOWN = 2.0  # seconds between requests (Pi 5 thermal safety)

_last_llm_call = 0.0


def classify_chunk(
    chunk: str,
    content_type: str,
    *,
    no_llm: bool = False,
) -> Optional[dict]:
    """Send ambiguous text to qwen3.5:2b for structured extraction.

    Returns parsed JSON dict or None on failure.
    """
    global _last_llm_call
    if no_llm:
        return None

    prompts = {
        "bestiary": (
            "Extract the monster/creature stat block from this text as JSON. "
            "Return ONLY a JSON object with keys: name, cr, base_hp, base_ac, "
            "base_atk, base_dmg. If no stat block found, return null.\n\n"
            "Text:\n{text}"
        ),
        "loot": (
            "Extract the treasure/loot item from this text as JSON. "
            "Return ONLY a JSON object with keys: name, rarity, value_gp. "
            "If no loot item found, return null.\n\n"
            "Text:\n{text}"
        ),
        "hazards": (
            "Extract the trap/hazard from this text as JSON. "
            "Return ONLY a JSON object with keys: name, dc, damage, damage_type. "
            "If no trap/hazard found, return null.\n\n"
            "Text:\n{text}"
        ),
        "magic_items": (
            "Extract the magic item from this text as JSON. "
            "Return ONLY a JSON object with keys: name, rarity, type, attunement, "
            "description. If no magic item found, return null.\n\n"
            "Text:\n{text}"
        ),
        "features": (
            "Extract the class feature from this text as JSON. "
            "Return ONLY a JSON object with keys: name, prerequisite, effect. "
            "If no class feature found, return null.\n\n"
            "Text:\n{text}"
        ),
        "locations": (
            "Extract the location/place from this text as JSON. "
            "Return ONLY a JSON object with keys: name, description, topology "
            "(one of: settlement, dungeon, wilderness). "
            "If no location found, return null.\n\n"
            "Text:\n{text}"
        ),
        "npcs": (
            "Extract the NPC/character from this text as JSON. "
            "Return ONLY a JSON object with keys: name, role, description. "
            "If no NPC found, return null.\n\n"
            "Text:\n{text}"
        ),
        "traps": (
            "Extract the trap/hazard mechanism from this text as JSON. "
            "Return ONLY a JSON object with keys: name, trigger, dc_detect, "
            "dc_disarm, damage, damage_type, description. "
            "If no trap found, return null.\n\n"
            "Text:\n{text}"
        ),
    }

    prompt_template = prompts.get(content_type)
    if not prompt_template:
        return None

    # Thermal cooldown
    elapsed = time.time() - _last_llm_call
    if elapsed < LLM_COOLDOWN:
        time.sleep(LLM_COOLDOWN - elapsed)

    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": CLASSIFY_MODEL,
                "prompt": prompt_template.format(text=chunk[:1000]),
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500},
            },
            timeout=30,
        )
        _last_llm_call = time.time()
        resp.raise_for_status()
        response_text = resp.json().get("response", "")

        # Extract JSON from response
        json_match = re.search(r'\{[^{}]+\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if data and isinstance(data, dict) and data.get("name"):
                return data
    except Exception:
        pass
    return None


def check_llm_available() -> bool:
    """Check if the classification LLM is available."""
    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": CLASSIFY_MODEL,
                "prompt": "Say OK",
                "stream": False,
                "options": {"num_predict": 5},
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# System-specific regex profiles
# ---------------------------------------------------------------------------

SYSTEM_PROFILES: Dict[str, dict] = {
    "dnd5e": {
        "stat_block_pattern": r"(?:Armor Class|AC)\s+\d+.*?(?:Hit Points|HP)\s+\d+",
        "magic_item_pattern": (
            r"(?:Wondrous item|Weapon|Armor|Ring|Rod|Staff|Wand|Scroll|Potion)"
            r".*?(?:common|uncommon|rare|very rare|legendary)"
        ),
        "feature_pattern": r"(?:Invocation|Infusion|Maneuver|Metamagic).*?(?:Prerequisite:|effect)",
        "loot_table_pattern": r"(?:Treasure|Hoard|Individual).*?(?:cp|sp|gp|pp)",
        "trap_pattern": r"(?:Trap|Hazard).*?(?:DC\s+\d+|damage)",
        "npc_pattern": r"(?:NPC|Character|Personality).*?(?:role|occupation|description)",
        "location_pattern": r"(?:Location|Area|Room|Ward|District).*?(?:description|features)",
        "table_pattern": r"(?:d\d+|Table|Random|Roll).*?(?:\d+\.\s|\d+\s{2,})",
    },
    "stc": {
        "stat_block_pattern": r"Tier\s+\d+\s+(?:Minion|Rival|Boss).*?Health",
        "loot_pattern": r"(?:Sphere|Fabrial|Shardblade|Equipment)",
        "hazard_pattern": r"(?:Highstorm|Everstorm|Void|Chasm).*?(?:damage|DC)",
        "npc_pattern": r"(?:NPC|Character|Bridgeman|Knight|Scholar)",
        "location_pattern": r"(?:Location|City|Warcamp|Chasm|Plateau)",
        "table_pattern": r"(?:d\d+|Table|Random|Roll).*?(?:\d+\.\s|\d+\s{2,})",
    },
    # ---- FITD systems -------------------------------------------------------
    # Patterns are designed to find FITD-style narrative content: gangs/factions
    # as stat-block equivalents, coin/items as loot, devil's bargains/entanglements
    # as hazards, named contacts as NPCs, and district/terrain descriptions as locations.
    "bitd": {
        # FITD uses Tier + scale for adversaries; no HP/AC
        "stat_block_pattern": r"(?:Tier\s+[IVX\d]+|Gang|Faction|Crew).*?(?:scale|strength|hold)",
        "loot_pattern": r"(?:Coin|Stash|Score|Rep|Vault|Payoff|Fence)",
        "hazard_pattern": r"(?:Entanglement|Heat|Wanted Level|Devil's Bargain|Consequence)",
        "npc_pattern": r"(?:Contact|Ally|Rival|Friend|Enemy|NPC|Faction Leader)",
        "location_pattern": r"(?:District|Ward|Den|Lair|The\s+[A-Z][a-z]+|Doskvol|Duskwall)",
        "table_pattern": r"(?:d\d+|Table|Random|Roll|Downtime|Entanglement).*?(?:\d+\.\s|\d+\s{2,})",
    },
    "sav": {
        # Scum and Villainy: ships/crews as adversaries, credits as loot
        "stat_block_pattern": r"(?:Tier\s+[IVX\d]+|Ship|Crew|Gang|Squadron).*?(?:scale|power|hold)",
        "loot_pattern": r"(?:Credit|Cred|Stash|Score|Cargo|Contraband|Haul)",
        "hazard_pattern": r"(?:Wanted Level|Heat|Faction Trouble|Complication|Consequence|Patrol)",
        "npc_pattern": r"(?:Contact|Ally|Rival|NPC|Faction\s+\w+|Captain|Commander|Agent)",
        "location_pattern": r"(?:Planet|Station|System|Sector|Port|The\s+[A-Z][a-z]+|Procyon)",
        "table_pattern": r"(?:d\d+|Table|Random|Roll|Downtime|Entanglement).*?(?:\d+\.\s|\d+\s{2,})",
    },
    "bob": {
        # Band of Blades: military campaign, soldiers and commanders
        "stat_block_pattern": r"(?:Broken|Chosen|Legion|Undead|Enemy\s+\w+).*?(?:Threat|Tier|Scale)",
        "loot_pattern": r"(?:Supply|Morale|Loot|Equipment|Spoils|Resources|Food)",
        "hazard_pattern": r"(?:Mission|Assault|Skirmish|Bleed|Pressure|Danger|Hazard)",
        "npc_pattern": r"(?:Soldier|Commander|Specialist|Officer|NPC|Named\s+\w+)",
        "location_pattern": r"(?:Camp|Fort|Road|Village|Retreat|Territory|Eastern\s+Kingdoms)",
        "table_pattern": r"(?:d\d+|Table|Random|Roll|Assignment|Mission).*?(?:\d+\.\s|\d+\s{2,})",
    },
    "candela": {
        # Candela Obscura: investigators vs. bleed/gilded/horrors
        "stat_block_pattern": r"(?:Monster|Horror|Threat|Adversary|Creature|Specter|Gilded)",
        "loot_pattern": r"(?:Candle|Wick|Token|Evidence|Artifact|Relic|Device)",
        "hazard_pattern": r"(?:Bleed|Scar|Mark|Condition|Gilded\s+Effect|Haunt|Anomaly)",
        "npc_pattern": r"(?:Circle\s+Member|Contact|Witness|NPC|Inspector|Archivist|Patron)",
        "location_pattern": r"(?:District|Quarter|Salon|Manor|Library|Newfaire|The\s+[A-Z][a-z]+)",
        "table_pattern": r"(?:d\d+|Table|Random|Roll|Investigation).*?(?:\d+\.\s|\d+\s{2,})",
    },
    "cbrpnk": {
        # CBR+PNK: corpo-dystopia, runners vs. megacorp security
        "stat_block_pattern": r"(?:Threat|Corp\s+Security|Agent|Hunter|Drone|Construct).*?(?:Tier|Scale|Harm)",
        "loot_pattern": r"(?:Credit|Cred|Gear|Cyberware|Weapon|Implant|Data\s+Core)",
        "hazard_pattern": r"(?:Heat|Exposure|Pursuit|Corporate\s+Response|Consequence|Feedback)",
        "npc_pattern": r"(?:Contact|Fixer|Corpo|NPC|Runner|Hacker|Dealer)",
        "location_pattern": r"(?:District|Sector|Zone|Hub|Megaplex|The\s+[A-Z][a-z]+|Corp\s+Tower)",
        "table_pattern": r"(?:d\d+|Table|Random|Roll|Contract|Run).*?(?:\d+\.\s|\d+\s{2,})",
    },
}


def _enrich_profiles_from_manifests() -> None:
    """Enrich SYSTEM_PROFILES with pattern_hint from system_manifest.json files.

    If a manifest declares stat_block_format.pattern_hint and the system
    has no existing profile, creates a minimal profile with that pattern.
    """
    try:
        from codex.core.system_discovery import get_all_manifests
        for system_id, manifest in get_all_manifests().items():
            if system_id in SYSTEM_PROFILES:
                continue  # Don't override hand-tuned profiles
            fmt = manifest.get("stat_block_format", {})
            hint = fmt.get("pattern_hint")
            if hint:
                SYSTEM_PROFILES[system_id] = {"stat_block_pattern": hint}
    except ImportError:
        pass


_enrich_profiles_from_manifests()


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

def _tier_from_cr(cr_str: str) -> int:
    """Map D&D CR string to tier 1-4."""
    try:
        if "/" in cr_str:
            num, den = cr_str.split("/")
            cr = float(num) / float(den)
        else:
            cr = float(cr_str)
    except (ValueError, ZeroDivisionError):
        return 1
    if cr <= 4:
        return 1
    if cr <= 10:
        return 2
    if cr <= 17:
        return 3
    return 4


def extract_bestiary(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract bestiary entries from PDFs.

    Returns summary dict with keys: system_id, content_type, entries, status.
    """
    out_path = CONFIG_ROOT / "bestiary" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "bestiary",
            "entries": 0,
            "status": "skipped (exists)",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    stat_pattern = profile.get("stat_block_pattern")
    if not stat_pattern:
        return {
            "system_id": system_id,
            "content_type": "bestiary",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(stat_pattern, re.IGNORECASE | re.DOTALL)
    entries_by_tier: Dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    seen_names: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue

        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=800, overlap=100):
                if regex.search(chunk):
                    # Try regex extraction first
                    entry = _regex_extract_stat_block(chunk, system_id)
                    if not entry and not no_llm:
                        entry = classify_chunk(chunk, "bestiary", no_llm=no_llm)

                    if entry and entry.get("name") and entry["name"] not in seen_names:
                        seen_names.add(entry["name"])
                        cr = entry.get("cr", "1")
                        tier = _tier_from_cr(str(cr)) if system_id == "dnd5e" else entry.get("tier", 1)
                        tier = max(1, min(4, tier))
                        entries_by_tier[tier].append(entry)

    total = sum(len(v) for v in entries_by_tier.values())
    if total > 0:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "tiers": {str(k): v for k, v in entries_by_tier.items()},
        }
        if system_id == "stc":
            data["format"] = "cosmere"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "bestiary",
        "entries": total,
        "status": "ok" if total > 0 else "no entries found",
    }


def _regex_extract_stat_block(chunk: str, system_id: str) -> Optional[dict]:
    """Try to regex-extract a stat block from a text chunk."""
    if system_id == "dnd5e":
        name_match = re.search(r'^([A-Z][a-zA-Z\'-]+(?:[ ][A-Za-z\'-]+)*)', chunk)
        hp_match = re.search(r'(?:Hit Points|HP)\s+(\d+)', chunk, re.IGNORECASE)
        ac_match = re.search(r'(?:Armor Class|AC)\s+(\d+)', chunk, re.IGNORECASE)
        cr_match = re.search(r'Challenge\s+(\d+(?:/\d+)?)', chunk, re.IGNORECASE)
        if name_match and hp_match:
            return {
                "name": name_match.group(1).strip(),
                "cr": cr_match.group(1) if cr_match else "1",
                "base_hp": int(hp_match.group(1)),
                "base_ac": int(ac_match.group(1)) if ac_match else 10,
                "base_atk": 3,
                "base_dmg": "1d6+1",
            }
    elif system_id == "stc":
        name_match = re.search(r'^([A-Z][a-zA-Z\'-]+(?:[ ][A-Za-z\'-]+)*)', chunk)
        tier_match = re.search(r'Tier\s+(\d+)', chunk, re.IGNORECASE)
        role_match = re.search(r'(Minion|Rival|Boss)', chunk, re.IGNORECASE)
        hp_match = re.search(r'Health[:\s]+(\d+)', chunk, re.IGNORECASE)
        if name_match and (tier_match or role_match):
            return {
                "name": name_match.group(1).strip(),
                "role": role_match.group(1).lower() if role_match else "minion",
                "tier": int(tier_match.group(1)) if tier_match else 1,
                "base_hp": int(hp_match.group(1)) if hp_match else 10,
            }
    return None


def extract_loot(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract loot/treasure entries from PDFs."""
    out_path = CONFIG_ROOT / "loot" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "loot",
            "entries": 0,
            "status": "skipped (exists)",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("loot_table_pattern") or profile.get("loot_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "loot",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    entries_by_tier: Dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    seen_names: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue
        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=600, overlap=80):
                if not regex.search(chunk):
                    continue
                entry = _regex_extract_loot(chunk, system_id)
                if not entry and not no_llm:
                    entry = classify_chunk(chunk, "loot", no_llm=no_llm)
                if entry and entry.get("name") and entry["name"] not in seen_names:
                    seen_names.add(entry["name"])
                    gp = entry.get("value_gp", entry.get("value", 0))
                    try:
                        gp = int(gp)
                    except (TypeError, ValueError):
                        gp = 0
                    tier = 1 if gp <= 50 else 2 if gp <= 500 else 3 if gp <= 5000 else 4
                    entry["tier"] = tier
                    entries_by_tier[tier].append(entry)

    total = sum(len(v) for v in entries_by_tier.values())
    if total > 0:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "tiers": {str(k): v for k, v in entries_by_tier.items()},
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "loot",
        "entries": total,
        "status": "ok" if total > 0 else "no entries found",
    }


def _regex_extract_loot(chunk: str, system_id: str) -> Optional[dict]:
    """Try regex extraction of a loot item from text."""
    name_match = re.search(r'^([A-Z][a-zA-Z\'-]+(?:[ ][A-Za-z\'-]+)*)', chunk)
    gp_match = re.search(r'(\d[\d,]*)\s*gp', chunk, re.IGNORECASE)
    if name_match and gp_match:
        return {
            "name": name_match.group(1).strip(),
            "value_gp": int(gp_match.group(1).replace(",", "")),
        }
    return None


def extract_hazards(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract trap/hazard entries from PDFs."""
    out_path = CONFIG_ROOT / "hazards" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "hazards",
            "entries": 0,
            "status": "skipped (exists)",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("trap_pattern") or profile.get("hazard_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "hazards",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    entries_by_tier: Dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    seen_names: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue
        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=600, overlap=80):
                if not regex.search(chunk):
                    continue
                entry = _regex_extract_hazard(chunk, system_id)
                if not entry and not no_llm:
                    entry = classify_chunk(chunk, "hazards", no_llm=no_llm)
                if entry and entry.get("name") and entry["name"] not in seen_names:
                    seen_names.add(entry["name"])
                    dc = entry.get("dc", 0)
                    try:
                        dc = int(dc)
                    except (TypeError, ValueError):
                        dc = 0
                    tier = 1 if dc <= 12 else 2 if dc <= 15 else 3 if dc <= 18 else 4
                    entry["tier"] = tier
                    entries_by_tier[tier].append(entry)

    total = sum(len(v) for v in entries_by_tier.values())
    if total > 0:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "tiers": {str(k): v for k, v in entries_by_tier.items()},
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "hazards",
        "entries": total,
        "status": "ok" if total > 0 else "no entries found",
    }


def _regex_extract_hazard(chunk: str, system_id: str) -> Optional[dict]:
    """Try regex extraction of a hazard/trap from text."""
    name_match = re.search(r'^([A-Z][a-zA-Z\'-]+(?:[ ][A-Za-z\'-]+)*)', chunk)
    dc_match = re.search(r'DC\s+(\d+)', chunk, re.IGNORECASE)
    dmg_match = re.search(r'(\d+d\d+(?:\s*\+\s*\d+)?)', chunk)
    if name_match and (dc_match or dmg_match):
        return {
            "name": name_match.group(1).strip(),
            "dc": int(dc_match.group(1)) if dc_match else 10,
            "damage": dmg_match.group(1) if dmg_match else "",
            "damage_type": "",
        }
    return None


def extract_magic_items(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract magic items from PDFs."""
    out_path = CONFIG_ROOT / "magic_items" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "magic_items",
            "entries": 0,
            "status": "skipped (exists)",
        }

    if system_id != "dnd5e":
        return {
            "system_id": system_id,
            "content_type": "magic_items",
            "entries": 0,
            "status": "not applicable",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("magic_item_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "magic_items",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    items: list = []
    seen: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue

        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=600, overlap=80):
                if regex.search(chunk):
                    entry = _regex_extract_magic_item(chunk)
                    if not entry and not no_llm:
                        entry = classify_chunk(chunk, "magic_items", no_llm=no_llm)
                    if entry and entry.get("name") and entry["name"] not in seen:
                        seen.add(entry["name"])
                        items.append(entry)

    if items:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "items": items,
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "magic_items",
        "entries": len(items),
        "status": "ok" if items else "no entries found",
    }


def _regex_extract_magic_item(chunk: str) -> Optional[dict]:
    """Try regex extraction of a magic item from text."""
    rarity_match = re.search(
        r'(common|uncommon|rare|very rare|legendary)',
        chunk, re.IGNORECASE,
    )
    type_match = re.search(
        r'(Wondrous item|Weapon|Armor|Ring|Rod|Staff|Wand|Scroll|Potion)',
        chunk, re.IGNORECASE,
    )
    attune_match = re.search(r'requires attunement', chunk, re.IGNORECASE)
    name_match = re.search(r'^([A-Z][a-zA-Z\'-]+(?:[ ][A-Za-z\'-]+)*)', chunk)

    if name_match and rarity_match:
        return {
            "name": name_match.group(1).strip(),
            "rarity": rarity_match.group(1).lower(),
            "type": type_match.group(1).lower() if type_match else "wondrous",
            "attunement": bool(attune_match),
            "description": chunk[:200].strip(),
        }
    return None


def extract_features(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract class features from PDFs."""
    out_path = CONFIG_ROOT / "features" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "features",
            "entries": 0,
            "status": "skipped (exists)",
        }

    if system_id != "dnd5e":
        return {
            "system_id": system_id,
            "content_type": "features",
            "entries": 0,
            "status": "not applicable",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("feature_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "features",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    features: list = []
    seen: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue
        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=600, overlap=80):
                if not regex.search(chunk):
                    continue
                entry = _regex_extract_feature(chunk)
                if not entry and not no_llm:
                    entry = classify_chunk(chunk, "features", no_llm=no_llm)
                if entry and entry.get("name") and entry["name"] not in seen:
                    seen.add(entry["name"])
                    features.append(entry)

    if features:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "features": features,
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "features",
        "entries": len(features),
        "status": "ok" if features else "no entries found",
    }


def _regex_extract_feature(chunk: str) -> Optional[dict]:
    """Try regex extraction of a class feature from text."""
    name_match = re.search(r'^([A-Z][a-zA-Z\'-]+(?:[ ][A-Za-z\'-]+)*)', chunk)
    prereq_match = re.search(r'[Pp]rerequisite:\s*(.+?)(?:\n|$)', chunk)
    if name_match:
        return {
            "name": name_match.group(1).strip(),
            "prerequisite": prereq_match.group(1).strip() if prereq_match else "",
            "effect": chunk[:300].strip(),
        }
    return None


def extract_locations(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract location/place entries from PDFs."""
    out_path = CONFIG_ROOT / "locations" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "locations",
            "entries": 0,
            "status": "skipped (exists)",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("location_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "locations",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    locations: list = []
    seen: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue
        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=600, overlap=80):
                if regex.search(chunk):
                    entry = classify_chunk(chunk, "locations", no_llm=no_llm)
                    if entry and entry.get("name") and entry["name"] not in seen:
                        seen.add(entry["name"])
                        locations.append(entry)

    if locations:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "locations": locations,
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "locations",
        "entries": len(locations),
        "status": "ok" if locations else "no entries found",
    }


def extract_npcs(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract NPC entries from PDFs."""
    out_path = CONFIG_ROOT / "npcs" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "npcs",
            "entries": 0,
            "status": "skipped (exists)",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("npc_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "npcs",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    npcs: list = []
    seen: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue
        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=600, overlap=80):
                if regex.search(chunk):
                    entry = classify_chunk(chunk, "npcs", no_llm=no_llm)
                    if entry and entry.get("name") and entry["name"] not in seen:
                        seen.add(entry["name"])
                        npcs.append(entry)

    if npcs:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "named_npcs": npcs,
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "npcs",
        "entries": len(npcs),
        "status": "ok" if npcs else "no entries found",
    }


def extract_traps(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract trap entries from PDFs."""
    out_path = CONFIG_ROOT / "traps" / f"{system_id}.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "traps",
            "entries": 0,
            "status": "skipped (exists)",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("trap_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "traps",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    traps: list = []
    seen: set = set()

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue
        for page_text in pages:
            for chunk in chunk_text(page_text, chunk_size=600, overlap=80):
                if regex.search(chunk):
                    entry = classify_chunk(chunk, "traps", no_llm=no_llm)
                    if entry and entry.get("name") and entry["name"] not in seen:
                        seen.add(entry["name"])
                        traps.append(entry)

    if traps:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Extracted from vault PDFs ({len(pdf_paths)} files)",
            "traps": traps,
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "traps",
        "entries": len(traps),
        "status": "ok" if traps else "no entries found",
    }


def extract_tables(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
    force: bool = False,
) -> dict:
    """Extract random/generation tables from PDFs.

    Searches for d100/d20/d12/d8/d6 roll tables and structured generation
    tables.  Results are written to config/tables/{system_id}_extracted.json.
    """
    out_path = CONFIG_ROOT / "tables" / f"{system_id}_extracted.json"
    if out_path.exists() and not force:
        return {
            "system_id": system_id,
            "content_type": "tables",
            "entries": 0,
            "status": "skipped (exists)",
        }

    profile = SYSTEM_PROFILES.get(system_id, {})
    pattern = profile.get("table_pattern")
    if not pattern:
        return {
            "system_id": system_id,
            "content_type": "tables",
            "entries": 0,
            "status": "no profile",
        }

    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    # Detect d-roll tables: "d100", "d20", "d12", "d8", "d6"
    dice_regex = re.compile(r'\b[dD](\d+)\b')
    row_regex = re.compile(r'^\s*(\d+(?:\s*[-–]\s*\d+)?)\s+(.+)$', re.MULTILINE)

    tables: Dict[str, list] = {}
    table_count = 0

    for pdf_path in pdf_paths:
        try:
            pages = extract_pdf_text(pdf_path)
        except Exception:
            continue

        for page_idx, page_text in enumerate(pages):
            for chunk in chunk_text(page_text, chunk_size=1200, overlap=150):
                if not regex.search(chunk) and not dice_regex.search(chunk):
                    continue
                # Extract table rows
                rows = row_regex.findall(chunk)
                if len(rows) >= 3:  # At least 3 rows to qualify as a table
                    # Try to find table title
                    title_match = re.search(
                        r'(?:Table[:\s]+)?([A-Z][A-Za-z\s]+?)(?:\n|d\d)',
                        chunk,
                    )
                    title = title_match.group(1).strip() if title_match else f"table_p{page_idx}_{table_count}"
                    table_key = re.sub(r'\s+', '_', title.lower())[:40]

                    entries = []
                    for roll, desc in rows:
                        entries.append({"roll": roll.strip(), "result": desc.strip()})

                    if table_key not in tables:
                        tables[table_key] = entries
                        table_count += 1

    if tables:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "source": f"Auto-extracted from vault PDFs ({len(pdf_paths)} files)",
            "tables": tables,
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "system_id": system_id,
        "content_type": "tables",
        "entries": table_count,
        "status": "ok" if table_count > 0 else "no tables found",
    }


# ---------------------------------------------------------------------------
# Extractor registry
# ---------------------------------------------------------------------------

EXTRACTORS: Dict[str, Callable] = {
    "bestiary": extract_bestiary,
    "loot": extract_loot,
    "hazards": extract_hazards,
    "magic_items": extract_magic_items,
    "features": extract_features,
    "locations": extract_locations,
    "npcs": extract_npcs,
    "traps": extract_traps,
    "tables": extract_tables,
}


# ---------------------------------------------------------------------------
# Dry-run reporter
# ---------------------------------------------------------------------------

def dry_run_report(target_systems: Dict[str, List[Path]], extractors: List[str]) -> None:
    """Print what would be extracted without actually extracting."""
    console.print(Panel.fit(
        "[bold yellow]DRY RUN[/bold yellow] — no files will be written",
        border_style="yellow",
    ))

    for system_id, pdfs in sorted(target_systems.items()):
        console.print(f"\n[bold cyan]{system_id}[/bold cyan] ({len(pdfs)} PDFs)")
        for ext_name in extractors:
            out_path = CONFIG_ROOT / ext_name / f"{system_id}.json"
            exists = out_path.exists()
            status = "[yellow]exists[/yellow]" if exists else "[green]would create[/green]"
            console.print(f"  {ext_name:15s} → {out_path.relative_to(PROJECT_ROOT)}  {status}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build_content",
        description="Unified content extraction pipeline for Codex vault PDFs.",
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--system", metavar="ID", help="Process one system only.")
    target.add_argument("--all", action="store_true", default=True, help="Process all systems (default).")
    parser.add_argument(
        "--extract", metavar="TYPES",
        help="Comma-separated extractor names (default: all). Options: " + ", ".join(EXTRACTORS),
    )
    parser.add_argument("--no-llm", action="store_true", help="Regex only, skip LLM classification.")
    parser.add_argument("--force", action="store_true", help="Rebuild existing config files.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be extracted.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    console.print(Panel.fit(
        "[bold cyan]Codex Content Extraction Pipeline[/bold cyan]\n"
        f"Vault: [dim]{VAULT_ROOT}[/dim]\n"
        f"Config: [dim]{CONFIG_ROOT}[/dim]",
        border_style="cyan",
    ))

    # Discover systems
    all_systems = discover_systems(VAULT_ROOT)
    if not all_systems:
        console.print("[yellow]No PDFs found under vault/*/SOURCE/.[/yellow]")
        return 0

    # Apply system filter
    if args.system:
        if args.system not in all_systems:
            console.print(f"[red]System '{args.system}' not found.[/red]")
            console.print(f"Available: {', '.join(sorted(all_systems))}")
            return 1
        target_systems = {args.system: all_systems[args.system]}
    else:
        target_systems = all_systems

    # Apply extractor filter
    if args.extract:
        extractor_names = [e.strip() for e in args.extract.split(",")]
        for name in extractor_names:
            if name not in EXTRACTORS:
                console.print(f"[red]Unknown extractor: '{name}'[/red]")
                console.print(f"Available: {', '.join(EXTRACTORS)}")
                return 1
    else:
        extractor_names = list(EXTRACTORS.keys())

    # Discovery summary
    console.print(f"\nSystems: [bold]{len(target_systems)}[/bold]  "
                  f"Extractors: [bold]{', '.join(extractor_names)}[/bold]\n")

    # Dry run
    if args.dry_run:
        dry_run_report(target_systems, extractor_names)
        return 0

    # LLM availability check (if needed)
    using_llm = not args.no_llm
    if using_llm:
        console.print("[dim]Checking LLM availability...[/dim]")
        if check_llm_available():
            console.print(f"[green]LLM OK — using {CLASSIFY_MODEL}[/green]")
        else:
            console.print(f"[yellow]LLM not available — falling back to regex only[/yellow]")
            using_llm = False
    else:
        console.print("[dim]LLM disabled (--no-llm)[/dim]")

    # Run extractors
    results: list = []

    for system_id, pdf_paths in sorted(target_systems.items()):
        console.print(f"\n[bold cyan]{system_id}[/bold cyan]")
        for ext_name in extractor_names:
            extractor = EXTRACTORS[ext_name]
            console.print(f"  [dim]{ext_name}...[/dim]", end=" ")
            result = extractor(
                system_id,
                pdf_paths,
                no_llm=not using_llm,
                force=args.force,
            )
            results.append(result)
            status = result["status"]
            entries = result["entries"]
            if status.startswith("ok"):
                console.print(f"[green]{entries} entries[/green]")
            elif status.startswith("skipped"):
                console.print(f"[yellow]{status}[/yellow]")
            else:
                console.print(f"[dim]{status}[/dim]")

    # Summary table
    console.print()
    table = Table(title="Extraction Results", border_style="cyan", show_lines=True)
    table.add_column("System", style="cyan")
    table.add_column("Type")
    table.add_column("Entries", justify="right")
    table.add_column("Status")

    for r in results:
        status_style = (
            "[green]OK[/green]" if r["status"] == "ok"
            else "[yellow]" + r["status"] + "[/yellow]"
        )
        table.add_row(r["system_id"], r["content_type"], str(r["entries"]), status_style)

    console.print(table)

    extracted = sum(1 for r in results if r["status"] == "ok")
    console.print(f"\n[bold]{extracted}[/bold] content type(s) extracted successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

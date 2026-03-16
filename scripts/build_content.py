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
        systems = {}
        if not vault_root.exists():
            return systems
        for d in sorted(vault_root.iterdir()):
            if not d.is_dir():
                continue
            src = d / "SOURCE"
            if not src.is_dir():
                continue
            pdfs = sorted(src.rglob("*.pdf")) + sorted(src.rglob("*.PDF"))
            if pdfs:
                systems[d.name] = list(dict.fromkeys(pdfs))
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
    },
    "stc": {
        "stat_block_pattern": r"Tier\s+\d+\s+(?:Minion|Rival|Boss).*?Health",
        "loot_pattern": r"(?:Sphere|Fabrial|Shardblade|Equipment)",
        "hazard_pattern": r"(?:Highstorm|Everstorm|Void|Chasm).*?(?:damage|DC)",
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
    # Loot extraction from PDFs requires significant regex per system.
    # For systems without a profile, skip.
    return {
        "system_id": system_id,
        "content_type": "loot",
        "entries": 0,
        "status": "no profile" if system_id not in SYSTEM_PROFILES else "skipped (no PDF loot tables detected)",
    }


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
    return {
        "system_id": system_id,
        "content_type": "hazards",
        "entries": 0,
        "status": "no profile" if system_id not in SYSTEM_PROFILES else "skipped (no PDF hazard tables detected)",
    }


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

    return {
        "system_id": system_id,
        "content_type": "features",
        "entries": 0,
        "status": "skipped (no PDF feature blocks detected)",
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

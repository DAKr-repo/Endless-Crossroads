"""
scripts/classify_system.py — System Classifier
=================================================
Analyzes vault PDFs to auto-generate system_manifest.json for new
game systems. Uses heuristic pre-filter (resolves ~80% of cases)
with LLM fallback via qwen3.5:2b for ambiguous systems.

Usage:
    python scripts/classify_system.py --system new_system
    python scripts/classify_system.py --all          # Classify all unmanifested systems
    python scripts/classify_system.py --no-llm       # Heuristics only
    python scripts/classify_system.py --dry-run       # Show classification without writing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = PROJECT_ROOT / "vault"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
try:
    from build_indices import extract_pdf_text
except ImportError:
    def extract_pdf_text(pdf_path: Path) -> list:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return [p.extract_text().strip() for p in reader.pages
                if (p.extract_text() or "").strip()]

console = Console()

# ---------------------------------------------------------------------------
# Heuristic patterns
# ---------------------------------------------------------------------------

# (pattern, engine_type, primary_loop, confidence)
HEURISTIC_RULES: List[Tuple[str, str, str, float]] = [
    # Spatial (D&D-like)
    (r"(?:Armor Class|AC)\s+\d+.*(?:Hit Points|HP)\s+\d+", "spatial", "spatial_dungeon", 0.9),
    (r"Challenge\s+Rating\s+\d+", "spatial", "spatial_dungeon", 0.85),
    (r"(?:dungeon|room|corridor)\s+(?:map|exploration|crawl)", "spatial", "spatial_dungeon", 0.7),

    # Spatial (Cosmere-like)
    (r"Tier\s+\d+\s+(?:Minion|Rival|Boss)", "spatial", "spatial_dungeon", 0.9),

    # FITD
    (r"(?:Action Rating|action rating).*(?:Stress|stress)", "narrative", "scene_navigation", 0.9),
    (r"(?:Position|position)\s+(?:and|&)\s+(?:Effect|effect)", "narrative", "scene_navigation", 0.85),
    (r"(?:entanglement|vice|trauma)\s+(?:roll|table)", "narrative", "scene_navigation", 0.8),
    (r"(?:Crew|crew)\s+(?:type|sheet|playbook)", "narrative", "scene_navigation", 0.75),

    # PbtA
    (r"(?:When you|when you).*(?:roll\s*\+|on a 10\+|on a 7)", "narrative", "scene_navigation", 0.85),
    (r"(?:On a 10\+|On a 7-9|On a 6-)", "narrative", "scene_navigation", 0.9),
    (r"(?:move|Move)\s+(?:trigger|triggered)", "narrative", "scene_navigation", 0.8),

    # Illuminated Worlds
    (r"(?:Illumination|illumination|Circle|Phenomena)", "narrative", "scene_navigation", 0.7),

    # Hex/overworld (still spatial)
    (r"hex\s+(?:grid|map|crawl|exploration)", "spatial", "spatial_dungeon", 0.7),
]

# Trait detection patterns
TRAIT_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    "action_roll": [
        (r"(?:Action Rating|action rating)", 0.9),
        (r"(?:d6 pool|dice pool)", 0.7),
        (r"(?:Position|position)\s+(?:and|&)\s+(?:Effect|effect)", 0.85),
    ],
    "stress_track": [
        (r"(?:Stress|stress)\s+(?:box|track|level|point)", 0.9),
        (r"(?:Trauma|trauma)\s+(?:trigger|table|list)", 0.8),
    ],
    "faction_clocks": [
        (r"(?:Faction|faction)\s+(?:clock|tier|status)", 0.85),
        (r"(?:Clock|clock)\s+(?:segment|progress|tick)", 0.7),
    ],
    "conditions": [
        (r"(?:Condition|condition|Status Effect).*(?:Poisoned|Stunned|Blinded)", 0.8),
        (r"(?:saving throw|save DC)", 0.6),
    ],
    "initiative": [
        (r"(?:Initiative|initiative)\s+(?:order|roll|bonus)", 0.85),
        (r"(?:Turn Order|turn order)", 0.7),
    ],
    "quest_system": [
        (r"(?:Quest|quest|Mission|mission)\s+(?:board|log|objective|reward)", 0.7),
    ],
    "progression_xp": [
        (r"(?:Experience Points|XP|experience)\s+(?:table|award|gain|level)", 0.8),
        (r"(?:Level Up|level up|advancement)", 0.6),
    ],
    "narrative_loom": [],  # Always included — universal trait
    "npc_dialogue": [
        (r"(?:NPC|npc|Non-Player Character)", 0.5),
    ],
    "rest": [
        (r"(?:Short Rest|Long Rest|Downtime)", 0.8),
    ],
    "doom_clock": [
        (r"(?:Doom|doom|Doomsday)\s+(?:clock|track|timer)", 0.8),
    ],
    "capacity": [
        (r"(?:Encumbrance|encumbrance|Carrying Capacity|Inventory Slot)", 0.7),
    ],
}

# Resolution mechanic detection
RESOLUTION_PATTERNS: List[Tuple[str, str, float]] = [
    (r"(?:d20|1d20|twenty-sided)", "d20", 0.95),
    (r"(?:dice pool|d6 pool|pool of d6)", "dice_pool_d6", 0.9),
    (r"(?:2d6\s*\+|roll\+|roll \+)", "2d6_plus_stat", 0.85),
    (r"(?:d100|percentile)", "d100", 0.8),
    (r"(?:d10 pool|d10s)", "dice_pool_d10", 0.8),
]


# ---------------------------------------------------------------------------
# Heuristic classifier
# ---------------------------------------------------------------------------

def classify_heuristic(text: str) -> dict:
    """Classify a system using regex heuristics on extracted text.

    Returns partial manifest dict with confidence scores.
    """
    # Engine type detection
    best_type = ("narrative", "scene_navigation", 0.3)  # default
    for pattern, etype, loop, conf in HEURISTIC_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            if conf > best_type[2]:
                best_type = (etype, loop, conf)

    # Resolution mechanic
    resolution = "custom"
    res_conf = 0.0
    for pattern, mechanic, conf in RESOLUTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE) and conf > res_conf:
            resolution = mechanic
            res_conf = conf

    # Trait detection
    traits = ["narrative_loom"]  # Always present
    for trait_name, patterns in TRAIT_PATTERNS.items():
        if trait_name == "narrative_loom":
            continue
        for pattern, threshold in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if trait_name not in traits:
                    traits.append(trait_name)
                break

    # Character stats extraction
    stats = _detect_stats(text)

    # Damage types
    damage_types = _detect_damage_types(text)

    return {
        "engine_type": best_type[0],
        "primary_loop": best_type[1],
        "resolution_mechanic": resolution,
        "engine_traits": traits,
        "character_stats": stats,
        "damage_types": damage_types,
        "confidence": best_type[2],
    }


def _detect_stats(text: str) -> List[str]:
    """Detect character stat names from text."""
    # D&D-style six stats
    dnd_stats = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
    if all(re.search(rf"\b{s}\b", text, re.IGNORECASE) for s in dnd_stats[:4]):
        return dnd_stats

    # FITD-style three categories
    fitd_stats = ["Insight", "Prowess", "Resolve"]
    if all(re.search(rf"\b{s}\b", text, re.IGNORECASE) for s in fitd_stats):
        return fitd_stats

    # Cosmere-style
    cosmere_stats = ["Strength", "Speed", "Intellect"]
    if all(re.search(rf"\b{s}\b", text, re.IGNORECASE) for s in cosmere_stats):
        return cosmere_stats

    return []


def _detect_damage_types(text: str) -> List[str]:
    """Detect damage type keywords from text."""
    known = [
        "slashing", "piercing", "bludgeoning", "fire", "cold",
        "lightning", "thunder", "poison", "acid", "necrotic",
        "radiant", "force", "psychic", "keen", "impact", "spirit",
    ]
    found = []
    for dt in known:
        if re.search(rf"\b{dt}\b", text, re.IGNORECASE):
            found.append(dt)
    return found


# ---------------------------------------------------------------------------
# LLM classifier (Tier 2 fallback)
# ---------------------------------------------------------------------------

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
CLASSIFY_MODEL = "qwen3.5:2b"

CLASSIFY_PROMPT = """You are analyzing a tabletop RPG rulebook. Based on the text below, classify this game system.

Output ONLY valid JSON with these keys:
- engine_type: "spatial" (dungeon crawling, grid maps, room exploration) or "narrative" (mission-based, scene-based, story-first)
- resolution_mechanic: "d20" / "dice_pool_d6" / "2d6_plus_stat" / "d100" / "dice_pool_d10" / "custom"
- character_stats: list of primary character attribute names
- damage_types: list of damage type categories (empty list if none)
- currency: string name of in-game currency
- progression: "xp_levels" / "milestone" / "advance_marks" / "custom"
- stat_block_pattern: regex pattern to match enemy stat blocks (or null)

TEXT:
{text}"""


def classify_llm(text: str) -> Optional[dict]:
    """Classify using qwen3.5:2b via Ollama. Returns partial manifest or None."""
    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": CLASSIFY_MODEL,
                "prompt": CLASSIFY_PROMPT.format(text=text[:4000]),
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 800},
            },
            timeout=60,
        )
        resp.raise_for_status()
        response_text = resp.json().get("response", "")
        json_match = re.search(r'\{[^{}]+\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return None


def check_llm_available() -> bool:
    """Check if classification LLM is reachable."""
    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={"model": CLASSIFY_MODEL, "prompt": "OK", "stream": False,
                  "options": {"num_predict": 3}},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

def classify_system(
    system_id: str,
    pdf_paths: List[Path],
    *,
    no_llm: bool = False,
) -> dict:
    """Classify a game system from its PDF rulebooks.

    Args:
        system_id: System identifier.
        pdf_paths: PDF files to analyze.
        no_llm: If True, skip LLM and use heuristics only.

    Returns:
        Complete system_manifest dict ready to write.
    """
    # Extract text from first 20 pages of each PDF
    all_text = []
    for pdf_path in pdf_paths[:3]:  # Cap at 3 PDFs for performance
        try:
            pages = extract_pdf_text(pdf_path)
            all_text.extend(pages[:20])  # First 20 pages per PDF
        except Exception:
            continue

    combined_text = "\n".join(all_text)

    if not combined_text.strip():
        return _empty_manifest(system_id)

    # Phase 1: Heuristic classification
    result = classify_heuristic(combined_text)

    # Phase 2: LLM enrichment (if heuristic confidence < 0.7)
    if not no_llm and result["confidence"] < 0.7:
        llm_result = classify_llm(combined_text)
        if llm_result:
            result = _merge_classifications(result, llm_result)

    # Build manifest
    manifest = {
        "system_id": system_id,
        "display_name": _infer_display_name(system_id, combined_text),
        "engine_type": result["engine_type"],
        "engine_traits": result["engine_traits"],
        "primary_loop": result["primary_loop"],
        "resolution_mechanic": result["resolution_mechanic"],
        "stat_block_format": {
            "fields": _infer_stat_fields(result["engine_type"]),
            "pattern_hint": None,
        },
        "character_stats": result.get("character_stats", []),
        "damage_types": result.get("damage_types", []),
        "currency": result.get("currency", ""),
        "progression": result.get("progression", "custom"),
        "classified_by": "heuristic" if result["confidence"] >= 0.7 else CLASSIFY_MODEL,
        "classified_at": datetime.now(timezone.utc).isoformat(),
        "confidence": result["confidence"],
        "needs_review": result["confidence"] < 0.8,
    }

    return manifest


def _empty_manifest(system_id: str) -> dict:
    """Return a minimal manifest for systems with no extractable text."""
    return {
        "system_id": system_id,
        "display_name": system_id.replace("_", " ").title(),
        "engine_type": "narrative",
        "engine_traits": ["narrative_loom"],
        "primary_loop": "scene_navigation",
        "resolution_mechanic": "custom",
        "stat_block_format": {"fields": [], "pattern_hint": None},
        "character_stats": [],
        "damage_types": [],
        "currency": "",
        "progression": "custom",
        "classified_by": "fallback",
        "classified_at": datetime.now(timezone.utc).isoformat(),
        "confidence": 0.1,
        "needs_review": True,
    }


def _merge_classifications(heuristic: dict, llm: dict) -> dict:
    """Merge heuristic and LLM results, preferring higher-confidence data."""
    result = dict(heuristic)

    # LLM can enrich but not override high-confidence heuristic fields
    if heuristic["confidence"] < 0.5:
        result["engine_type"] = llm.get("engine_type", result["engine_type"])
        result["resolution_mechanic"] = llm.get("resolution_mechanic", result["resolution_mechanic"])

    # Always take LLM-enriched data for fields heuristics are weak at
    if llm.get("character_stats"):
        result["character_stats"] = llm["character_stats"]
    if llm.get("currency"):
        result["currency"] = llm["currency"]
    if llm.get("progression"):
        result["progression"] = llm["progression"]
    if llm.get("stat_block_pattern"):
        result["stat_block_pattern"] = llm["stat_block_pattern"]

    # Bump confidence slightly if LLM agrees with heuristic
    if llm.get("engine_type") == heuristic["engine_type"]:
        result["confidence"] = min(0.95, result["confidence"] + 0.1)

    return result


def _infer_display_name(system_id: str, text: str) -> str:
    """Try to extract the game name from the first page of text."""
    first_lines = text[:500].split("\n")
    for line in first_lines:
        line = line.strip()
        if len(line) > 5 and len(line) < 80 and not line.startswith(("©", "http", "www")):
            return line
    return system_id.replace("_", " ").title()


def _infer_stat_fields(engine_type: str) -> List[str]:
    """Return default stat block fields based on engine type."""
    if engine_type == "spatial":
        return ["name", "hp", "ac", "attack", "damage"]
    return ["name", "type", "tier"]


# ---------------------------------------------------------------------------
# Vault discovery (for unmanifested systems)
# ---------------------------------------------------------------------------

def find_unmanifested_systems() -> Dict[str, List[Path]]:
    """Find vault directories with PDFs but no system_manifest.json.

    Returns dict mapping potential system_id -> list of PDF paths.
    """
    result: Dict[str, List[Path]] = {}

    if not VAULT_ROOT.exists():
        return result

    # Find all directories containing a SOURCE subfolder with PDFs
    for source_dir in VAULT_ROOT.rglob("SOURCE"):
        if not source_dir.is_dir():
            continue

        parent = source_dir.parent
        manifest = parent / "system_manifest.json"
        if manifest.exists():
            continue  # Already has a manifest

        pdfs = sorted(source_dir.rglob("*.pdf")) + sorted(source_dir.rglob("*.PDF"))
        if pdfs:
            # Derive system_id from directory name
            system_id = parent.name.lower().replace(" ", "_").replace("-", "_")
            result[system_id] = list(dict.fromkeys(pdfs))

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="classify_system",
        description="Classify game systems from vault PDFs and generate system_manifest.json.",
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--system", metavar="ID", help="Classify a specific vault directory.")
    target.add_argument("--all", action="store_true", default=True,
                       help="Classify all unmanifested systems (default).")
    parser.add_argument("--no-llm", action="store_true", help="Heuristics only, skip LLM.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing manifests.")
    parser.add_argument("--dry-run", action="store_true", help="Show results without writing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    console.print(Panel.fit(
        "[bold cyan]Codex System Classifier[/bold cyan]\n"
        f"Vault: [dim]{VAULT_ROOT}[/dim]",
        border_style="cyan",
    ))

    # Find systems to classify
    if args.system:
        # Find PDFs for a specific system
        candidates: Dict[str, List[Path]] = {}
        for source_dir in VAULT_ROOT.rglob("SOURCE"):
            parent = source_dir.parent
            system_id = parent.name.lower().replace(" ", "_").replace("-", "_")
            if system_id == args.system or parent.name == args.system:
                pdfs = sorted(source_dir.rglob("*.pdf")) + sorted(source_dir.rglob("*.PDF"))
                if pdfs:
                    candidates[args.system] = list(dict.fromkeys(pdfs))
                    break
        if not candidates:
            console.print(f"[red]No PDFs found for system '{args.system}'.[/red]")
            return 1
    else:
        if args.force:
            # Re-classify all systems with PDFs
            from build_indices import discover_systems
            candidates = discover_systems(VAULT_ROOT)
        else:
            candidates = find_unmanifested_systems()

    if not candidates:
        console.print("[green]All systems already have manifests. Use --force to reclassify.[/green]")
        return 0

    console.print(f"\nFound [bold]{len(candidates)}[/bold] system(s) to classify:\n")
    for sid, pdfs in sorted(candidates.items()):
        console.print(f"  [cyan]{sid}[/cyan] — {len(pdfs)} PDF(s)")

    # LLM check
    using_llm = not args.no_llm
    if using_llm:
        console.print("\n[dim]Checking LLM availability...[/dim]")
        if check_llm_available():
            console.print(f"[green]LLM OK — {CLASSIFY_MODEL}[/green]")
        else:
            console.print("[yellow]LLM not available — using heuristics only[/yellow]")
            using_llm = False

    # Classify each system
    results = []
    for system_id, pdf_paths in sorted(candidates.items()):
        console.print(f"\n[bold cyan]{system_id}[/bold cyan]")
        manifest = classify_system(system_id, pdf_paths, no_llm=not using_llm)
        results.append(manifest)

        # Display result
        console.print(f"  Type: [bold]{manifest['engine_type']}[/bold]")
        console.print(f"  Loop: {manifest['primary_loop']}")
        console.print(f"  Resolution: {manifest['resolution_mechanic']}")
        console.print(f"  Traits: {', '.join(manifest['engine_traits'])}")
        console.print(f"  Confidence: {manifest['confidence']:.0%}")
        if manifest["needs_review"]:
            console.print("  [yellow]⚠ Needs human review[/yellow]")

        # Write manifest
        if not args.dry_run:
            # Find the right directory for this system
            out_dir = None
            for source_dir in VAULT_ROOT.rglob("SOURCE"):
                parent = source_dir.parent
                sid = parent.name.lower().replace(" ", "_").replace("-", "_")
                if sid == system_id or parent.name == system_id:
                    out_dir = parent
                    break
            if out_dir:
                out_path = out_dir / "system_manifest.json"
                out_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                console.print(f"  [green]Written: {out_path.relative_to(PROJECT_ROOT)}[/green]")

    # Summary
    console.print()
    table = Table(title="Classification Results", border_style="cyan")
    table.add_column("System", style="cyan")
    table.add_column("Type")
    table.add_column("Loop")
    table.add_column("Confidence", justify="right")
    table.add_column("Review?")

    for m in results:
        conf_style = "[green]" if m["confidence"] >= 0.8 else "[yellow]"
        table.add_row(
            m["system_id"],
            m["engine_type"],
            m["primary_loop"],
            f"{conf_style}{m['confidence']:.0%}[/]",
            "[yellow]Yes[/yellow]" if m["needs_review"] else "[green]No[/green]",
        )

    console.print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())

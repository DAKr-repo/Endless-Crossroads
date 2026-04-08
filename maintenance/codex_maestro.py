#!/usr/bin/env python3
"""
codex_maestro.py - Mimir and the C.O.D.E.X. of Chronicles
==========================================================

Unified Maintenance Wizard.  A Rich TUI that orchestrates the four
C.O.D.E.X. maintenance operations in The True Sequence:

  1. System Scaffold   (TemplateRegistry-based, zero-touch)
  2. Index Builder     (codex_index_builder.py, delta-sync aware)
  3. Registry Autofill (codex_registry_autofill.py, 3-layer merge)
  4. Registry Builder  (codex_registry_builder.py, compiles lookup)

The sequence matters: the Index Builder vectorizes PDFs first so that
Autofill's AI extraction layer (Layer 3) has FAISS data to query.
Autofill then populates the rules JSONs, and the Registry Builder
compiles them into fast lookup indices.

v3.0 Changes (Amendment 09):
  - Reordered to The True Sequence (Index -> Autofill -> Builder)
  - codex_registry_autopilot.py deprecated; autofill is sole agent
  - Autofill runs as importable function (not subprocess)
  - 4-step menu with individual and Run-All modes

Aesthetic: Gold/Crimson/Emerald palette matching codex_boot_wizard.py.
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Ensure project root is on sys.path (needed when run as subprocess or standalone)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text
from rich import box

from maintenance.codex_utils import log_event, LOG_FILE

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAINTENANCE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config" / "systems"
VAULT_DIR = PROJECT_ROOT / "vault"

# Color scheme (matches boot wizard)
GOLD = "bold yellow"
CRIMSON = "bold red"
EMERALD = "bold green"
SILVER = "dim white"

console = Console()


# =========================================================================
# TEMPLATE REGISTRY — Replaces interactive scaffolding prompts
# =========================================================================

# Family parent directories that contain child system vaults
FAMILY_PARENTS = {"FITD", "ILLUMINATED_WORLDS"}

# Base templates keyed by engine family.  When a vault is detected under
# vault/FITD/<system>, the FITD template is applied automatically.
TEMPLATE_REGISTRY: Dict[str, dict] = {
    "FITD": {
        "engine": "FITD",
        "system_family": "FITD",
        "archetype_categories": {
            "Playbooks": []
        },
        "core_stats": {
            "attributes": ["Insight", "Prowess", "Resolve"],
            "actions": {}
        },
        "resources": ["Stress", "Trauma"],
        "dice_system": "d6_pool",
        "position_effect": True,
        "stress_max": 9,
        "trauma_max": 4,
    },
    "ILLUMINATED_WORLDS": {
        "engine": "Illuminated",
        "system_family": "ILLUMINATED_WORLDS",
        "archetype_categories": {
            "Roles": []
        },
        "core_stats": {
            "resistances": ["Nerve", "Cunning", "Intuition"],
            "actions": {}
        },
        "resources": ["Marks", "Scars"],
        "dice_system": "gilded_dice",
    },
    "GENERIC": {
        "engine": "custom",
        "system_family": "",
        "archetype_categories": {},
        "core_stats": [],
        "resources": [],
        "dice_system": "custom",
    },
}


def _discover_unscaffolded_vaults() -> List[dict]:
    """Scan the vault for systems that don't have a rules JSON yet.

    Returns list of dicts: {system_id, display_name, family, vault_path}.
    """
    if not VAULT_DIR.exists():
        return []

    existing_configs = set()
    if CONFIG_DIR.exists():
        for f in CONFIG_DIR.iterdir():
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    existing_configs.add(data.get("system_id", "").upper())
                except Exception:
                    pass

    missing: List[dict] = []

    for entry in sorted(VAULT_DIR.iterdir()):
        if not entry.is_dir():
            continue

        if entry.name in FAMILY_PARENTS:
            # Descend into family children
            for child in sorted(entry.iterdir()):
                if child.is_dir():
                    sid = child.name.upper().replace(" ", "_").replace("+", "_")
                    if sid not in existing_configs:
                        missing.append({
                            "system_id": sid,
                            "display_name": child.name,
                            "family": entry.name,
                            "vault_path": str(child),
                        })
        else:
            sid = entry.name.upper().replace(" ", "_")
            if sid not in existing_configs:
                missing.append({
                    "system_id": sid,
                    "display_name": entry.name,
                    "family": sid,
                    "vault_path": str(entry),
                })

    return missing


def _scaffold_from_template(system_info: dict) -> Path:
    """Generate a rules JSON for a system using the TemplateRegistry.

    Picks the template matching the vault family, fills in the system_id,
    and writes to config/systems/.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    family = system_info["family"]
    template = TEMPLATE_REGISTRY.get(family, TEMPLATE_REGISTRY["GENERIC"]).copy()

    config = {
        "system_id": system_info["system_id"],
        "display_name": system_info["display_name"],
        **template,
    }
    if not config.get("system_family"):
        config["system_family"] = family

    out_path = CONFIG_DIR / f"rules_{system_info['system_id']}.json"
    with open(out_path, "w") as f:
        json.dump(config, f, indent=4)

    return out_path


def auto_scaffold(silent: bool = False) -> int:
    """Scaffold all unregistered vault systems.  Returns count of new configs."""
    missing = _discover_unscaffolded_vaults()
    if not missing:
        if not silent:
            console.print(f"  [{EMERALD}]All vault systems already scaffolded.[/]")
        return 0

    count = 0
    for info in missing:
        path = _scaffold_from_template(info)
        count += 1
        if not silent:
            console.print(
                f"  [{EMERALD}]Scaffolded:[/] {info['system_id']} "
                f"(family={info['family']}) -> {path.name}"
            )
        _log(f"SCAFFOLD: {info['system_id']} -> {path}")

    return count


# =========================================================================
# SCRIPTS TO ORCHESTRATE
# =========================================================================

def _auto_autofill(silent: bool = False) -> int:
    """Run the unified registry autofill (3-layer merge)."""
    from maintenance.codex_registry_autofill import autofill_all
    return autofill_all(use_ai=True, silent=silent)


def _auto_registry_build(silent: bool = False) -> int:
    """Build registries for all system configs (zero-touch via build_all)."""
    from maintenance.codex_registry_builder import build_all
    return build_all(delta_only=True, silent=silent)


def _auto_index_build(silent: bool = False) -> int:
    """Smart-rebuild: audit indices and re-index only files with gaps."""
    from maintenance.codex_index_builder import auto_build
    return auto_build(mode="smart")


SCRIPTS = [
    {
        "name": "System Scaffold",
        "file": None,
        "description": "Auto-scaffold via TemplateRegistry (zero-touch).",
        "auto_fn": auto_scaffold,
    },
    {
        "name": "Index Builder",
        "file": "codex_index_builder.py",
        "description": "Vectorizes vault PDFs into FAISS indices (delta-sync). Requires Ollama.",
        "auto_fn": _auto_index_build,
    },
    {
        "name": "Registry Autofill",
        "file": None,
        "description": "Populates rules JSONs (Master + Crawler + AI extraction).",
        "auto_fn": _auto_autofill,
    },
    {
        "name": "Registry Builder",
        "file": None,
        "description": "Compiles rules JSONs into fast lookup indices.",
        "auto_fn": _auto_registry_build,
    },
]


# =========================================================================
# CORE FUNCTIONS
# =========================================================================

def _log(message: str):
    """Append a timestamped message to the build log."""
    log_event("MAESTRO", message)


def _render_banner():
    """Display the Maestro title banner."""
    banner = Text()
    banner.append("\n  MIMIR AND THE C.O.D.E.X. OF CHRONICLES\n", style=GOLD)
    banner.append("  Chronicles Of Destiny: Endless Crossroads\n", style=SILVER)
    banner.append("  Where all fates meet at the X.\n", style="dim yellow")
    console.print(Panel(banner, border_style="yellow", box=box.DOUBLE))


def _render_menu():
    """Display the main menu and return user choice."""
    table = Table(box=box.SIMPLE, border_style="yellow", show_header=False, pad_edge=False)
    table.add_column("Key", style=GOLD, width=6)
    table.add_column("Action", style="white")

    for i, script in enumerate(SCRIPTS, 1):
        table.add_row(f"  [{i}]", f"{script['name']} - {script['description']}")

    table.add_row("", "")
    table.add_row("  [P]", "Index Single PDF (pick a system and PDF to index)")
    table.add_row("  [A]", "Run All (zero-touch sequential)")
    table.add_row("  [L]", "View Build Log")
    table.add_row("  [Q]", "Exit")

    console.print(table)
    console.print()

    choice = Prompt.ask(
        f"[{GOLD}]Select>[/]",
        choices=["1", "2", "3", "4", "p", "a", "l", "q"],
        default="q",
        console=console,
        show_choices=False,
    )
    return choice.lower()


def _run_script(script_info: dict) -> bool:
    """Run a maintenance script.  Returns True on success."""
    name = script_info["name"]

    # Check if this step has a built-in auto function
    auto_fn = script_info.get("auto_fn")
    if auto_fn:
        console.print(f"\n  [{GOLD}]Running {name} (auto)...[/]")
        _log(f"START: {name} (auto)")
        try:
            count = auto_fn()
            console.print(f"  [{EMERALD}]SUCCESS:[/] {name} ({count} systems processed).")
            _log(f"SUCCESS: {name} ({count} scaffolded)")
            return True
        except Exception as e:
            console.print(f"  [{CRIMSON}]ERROR:[/] {e}")
            _log(f"ERROR: {name} - {e}")
            return False

    # Otherwise, run as subprocess
    script_path = MAINTENANCE_DIR / script_info["file"]

    if not script_path.exists():
        console.print(f"  [{CRIMSON}]ERROR:[/] {script_path} not found.")
        _log(f"FAIL: {name} - script not found at {script_path}")
        return False

    console.print(f"\n  [{GOLD}]Running {name}...[/]")
    _log(f"START: {name} ({script_path})")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
            timeout=None,
        )

        if result.returncode == 0:
            console.print(f"  [{EMERALD}]SUCCESS:[/] {name} completed.")
            _log(f"SUCCESS: {name} (exit code 0)")
            return True
        else:
            console.print(f"  [{CRIMSON}]FAILED:[/] {name} exited with code {result.returncode}.")
            _log(f"FAIL: {name} (exit code {result.returncode})")
            return False
    except KeyboardInterrupt:
        console.print(f"\n  [{SILVER}]{name} interrupted by user.[/]")
        _log(f"INTERRUPTED: {name}")
        return False
    except Exception as e:
        console.print(f"  [{CRIMSON}]ERROR:[/] {e}")
        _log(f"ERROR: {name} - {e}")
        return False


def _run_all():
    """Run all four maintenance steps in The True Sequence (zero-touch)."""
    _log("=== MAESTRO: ZERO-TOUCH RUN ALL START ===")
    results = []
    for script in SCRIPTS:
        success = _run_script(script)
        results.append((script["name"], success))

    # Summary
    console.print()
    summary = Table(title="Build Summary", box=box.SIMPLE, border_style="yellow")
    summary.add_column("Script", style="white")
    summary.add_column("Status", justify="center")

    for name, success in results:
        status = f"[{EMERALD}]OK[/]" if success else f"[{CRIMSON}]FAIL[/]"
        summary.add_row(name, status)

    console.print(summary)
    _log("=== MAESTRO: ZERO-TOUCH RUN ALL COMPLETE ===")


def _index_single_pdf():
    """Interactive menu to index a single PDF into a system's FAISS index."""
    from rich.prompt import Confirm

    # Discover available systems
    systems_dir = VAULT_DIR
    available = []
    for d in sorted(systems_dir.iterdir()):
        if d.is_dir() and any(d.rglob("*.pdf")):
            available.append(d.name)
        elif d.is_dir():
            # Check group dirs (FITD/, ILLUMINATED_WORLDS/)
            for child in sorted(d.iterdir()):
                if child.is_dir() and any(child.rglob("*.pdf")):
                    available.append(child.name)

    if not available:
        console.print(f"  [{CRIMSON}]No systems with PDFs found in vault/[/]")
        return

    # Show available systems
    console.print(f"\n  [{GOLD}]Available systems:[/]")
    for i, sys_id in enumerate(available, 1):
        console.print(f"    [{GOLD}]{i}[/] {sys_id}")

    sys_choice = Prompt.ask(
        f"\n  [{GOLD}]System number or ID[/]",
        console=console,
    )

    # Resolve system ID
    try:
        idx = int(sys_choice) - 1
        system_id = available[idx]
    except (ValueError, IndexError):
        system_id = sys_choice.strip()

    # Map vault dir names to canonical IDs
    _VAULT_TO_ID = {"Candela_Obscura": "candela", "CBR_PNK": "cbrpnk"}
    canonical_id = _VAULT_TO_ID.get(system_id, system_id)

    # Find all PDFs in that system's vault
    # Check both flat and grouped layouts
    system_vault = VAULT_DIR / system_id
    if not system_vault.is_dir():
        # Try group dirs
        for group in ("FITD", "ILLUMINATED_WORLDS"):
            candidate = VAULT_DIR / group / system_id
            if candidate.is_dir():
                system_vault = candidate
                break

    if not system_vault.is_dir():
        console.print(f"  [{CRIMSON}]Vault directory not found for '{system_id}'[/]")
        return

    pdfs = sorted(system_vault.rglob("*.pdf")) + sorted(system_vault.rglob("*.PDF"))
    pdfs = list(dict.fromkeys(pdfs))  # deduplicate

    if not pdfs:
        console.print(f"  [{CRIMSON}]No PDFs found in {system_vault}[/]")
        return

    # Show available PDFs
    console.print(f"\n  [{GOLD}]PDFs in {system_id}:[/]")
    for i, pdf in enumerate(pdfs, 1):
        rel = pdf.relative_to(system_vault)
        console.print(f"    [{GOLD}]{i:2d}[/] {rel}")

    pdf_choice = Prompt.ask(
        f"\n  [{GOLD}]PDF number to index[/]",
        console=console,
    )

    try:
        pdf_idx = int(pdf_choice) - 1
        selected_pdf = pdfs[pdf_idx]
    except (ValueError, IndexError):
        console.print(f"  [{CRIMSON}]Invalid selection.[/]")
        return

    console.print(f"\n  Indexing [{EMERALD}]{selected_pdf.name}[/] into [{GOLD}]{canonical_id}[/]...")
    if not Confirm.ask(f"  [{SILVER}]Proceed?[/]", console=console, default=True):
        return

    # Run build_indices.py with --pdf flag
    _log(f"INDEX PDF: {selected_pdf.name} -> {canonical_id}")
    script_path = PROJECT_ROOT / "scripts" / "build_indices.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path),
             "--system", canonical_id,
             "--pdf", str(selected_pdf),
             "--force"],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
            timeout=7200,  # 2 hour timeout for large PDFs
        )
        if result.returncode == 0:
            console.print(f"  [{EMERALD}]SUCCESS:[/] {selected_pdf.name} indexed into {canonical_id}.")
            _log(f"SUCCESS: {selected_pdf.name} -> {canonical_id}")
        else:
            console.print(f"  [{CRIMSON}]FAILED:[/] Exit code {result.returncode}")
            _log(f"FAIL: {selected_pdf.name} -> {canonical_id} (exit {result.returncode})")
    except subprocess.TimeoutExpired:
        console.print(f"  [{CRIMSON}]TIMEOUT:[/] Indexing took too long (>2h).")
        _log(f"TIMEOUT: {selected_pdf.name}")
    except Exception as e:
        console.print(f"  [{CRIMSON}]ERROR:[/] {e}")
        _log(f"ERROR: {selected_pdf.name} - {e}")


def _view_log():
    """Display the build log contents."""
    if not LOG_FILE.exists():
        console.print(f"  [{SILVER}]No build log found at {LOG_FILE}[/]")
        return

    content = LOG_FILE.read_text()
    if not content.strip():
        console.print(f"  [{SILVER}]Build log is empty.[/]")
        return

    # Show last 40 lines max
    lines = content.strip().split("\n")
    if len(lines) > 40:
        display = "\n".join(lines[-40:])
        header = f"Build Log (last 40 of {len(lines)} lines)"
    else:
        display = "\n".join(lines)
        header = "Build Log"

    console.print(Panel(display, title=header, border_style="yellow", box=box.SIMPLE))


def main():
    """Main menu loop."""
    console.clear()
    _render_banner()
    _log("=== MAESTRO SESSION START ===")

    while True:
        choice = _render_menu()

        if choice == "q":
            console.print(f"\n  [{SILVER}]Maestro signing off.[/]\n")
            break
        elif choice == "p":
            _index_single_pdf()
        elif choice == "a":
            _run_all()
        elif choice == "l":
            _view_log()
        elif choice in ("1", "2", "3", "4"):
            idx = int(choice) - 1
            _run_script(SCRIPTS[idx])

        console.print()
        try:
            Prompt.ask(f"[{SILVER}]Press Enter to continue[/]", console=console, default="")
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""DM View — Live Diagnostic Dashboard Service

Run in a terminal (or second screen) to monitor game state in real-time.
Works as a service: watches state/dm_frame.json for updates from the
game loop, renders a 3-panel dashboard, and accepts DM commands.

Similar architecture to play_player_view.py but with interactive input.

Two modes:
  1. SERVICE MODE (default): Watch state file for engine updates from
     play_burnwillow.py or any game loop. DM can issue tool commands
     (roll, npc, bestiary, etc.) without a running engine.
  2. STANDALONE MODE (--standalone): Spin up an engine internally for
     testing. Full dashboard with all mechanics.

Usage:
    python play_dm_view.py                          # Service mode
    python play_dm_view.py --system burnwillow      # Service mode, system hint
    python play_dm_view.py --standalone --system dnd5e --seed 42  # Standalone

Version: 1.0 (WO-V34.0)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex.paths import STATE_DIR
from codex.core.dm_dashboard import (
    DMDashboard, VitalsSchema, get_vitals,
)

DM_FRAME_FILE = STATE_DIR / "dm_frame.json"
POLL_INTERVAL = 0.5  # seconds


# =========================================================================
# ENGINE FACTORY — Standalone mode only
# =========================================================================

def create_engine(system_tag: str, seed=None, party_names=None):
    """Instantiate the correct engine for standalone mode."""
    tag = system_tag.upper()

    if tag == "BURNWILLOW":
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        names = party_names or ["Kael"]
        if len(names) > 1:
            engine.create_party(names)
        else:
            engine.create_character(names[0])
        engine.generate_dungeon(seed=seed)
        return engine

    elif tag == "DND5E":
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        name = party_names[0] if party_names else "Aldric"
        engine.create_character(name, character_class="fighter", race="human")
        for extra_name in (party_names or [])[1:]:
            from codex.games.dnd5e import DnD5eCharacter
            engine.add_to_party(DnD5eCharacter(name=extra_name, character_class="wizard"))
        engine.generate_dungeon(seed=seed)
        return engine

    elif tag == "STC":
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        name = party_names[0] if party_names else "Kaladin"
        engine.create_character(name, order="windrunner", heritage="alethi")
        for extra_name in (party_names or [])[1:]:
            from codex.games.stc import CosmereCharacter
            engine.add_to_party(CosmereCharacter(name=extra_name, order="edgedancer"))
        engine.generate_dungeon(seed=seed)
        return engine

    elif tag == "BITD":
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        name = party_names[0] if party_names else "Vex"
        engine.create_character(name, playbook="Cutter", vice="gambling")
        engine.crew_name = "The Red Sashes"
        engine.crew_type = "Bravos"
        return engine

    elif tag == "CROWN":
        from codex.games.crown.engine import CrownAndCrewEngine
        engine = CrownAndCrewEngine()
        engine.setup()
        return engine

    else:
        raise ValueError(f"Unknown system: {system_tag}")


# =========================================================================
# SERVICE MODE — Watch state file + interactive commands
# =========================================================================

def run_service_mode(console: Console, system_tag: str):
    """Service mode: watch dm_frame.json for state, accept DM commands."""
    dashboard = DMDashboard(console, system_tag)
    last_mtime = 0.0

    console.clear()
    _print_banner(console, system_tag, "SERVICE")

    # Initial render with empty vitals
    vitals = VitalsSchema(
        system_name=system_tag.title(),
        system_tag=system_tag.upper(),
        primary_resource="HP",
    )

    try:
        while True:
            # Check for state file updates
            try:
                if DM_FRAME_FILE.exists():
                    mtime = DM_FRAME_FILE.stat().st_mtime
                    if mtime > last_mtime:
                        last_mtime = mtime
                        data = json.loads(DM_FRAME_FILE.read_text())
                        vitals = _vitals_from_frame(data, system_tag)
            except (json.JSONDecodeError, OSError):
                pass

            # Render dashboard
            console.clear()
            layout = dashboard.render(vitals)
            console.print(layout)

            # Command input (non-blocking feel with timeout prompt)
            try:
                cmd = console.input("[bold cyan]DM>[/bold cyan] ")
            except EOFError:
                break

            cmd = cmd.strip()
            if not cmd:
                continue
            if cmd.lower() == "quit":
                console.print("[bold]Dashboard closed.[/bold]")
                break

            # Dispatch command (no engine in service mode)
            result = dashboard.dispatch_command(cmd, engine=None)
            if result:
                console.print(Panel(result, title="Result", border_style="green",
                                    box=box.ROUNDED))
                time.sleep(1.5)  # Let user read result before refresh

    except KeyboardInterrupt:
        console.print("\n[bold]Dashboard closed.[/bold]")


def _vitals_from_frame(data: dict, system_tag: str) -> VitalsSchema:
    """Build VitalsSchema from a dm_frame.json dict."""
    party = []
    for p in data.get("party", []):
        party.append({
            "name": p.get("name", "?"),
            "hp": p.get("hp", 0),
            "max_hp": p.get("max_hp", 0),
            "alive": p.get("alive", True),
        })

    return VitalsSchema(
        system_name=data.get("system_name", system_tag.title()),
        system_tag=data.get("system_tag", system_tag.upper()),
        primary_resource=data.get("primary_resource", "HP"),
        primary_current=data.get("primary_current", 0),
        primary_max=data.get("primary_max", 0),
        secondary_resource=data.get("secondary_resource", ""),
        secondary_current=data.get("secondary_current", 0),
        secondary_max=data.get("secondary_max", 0),
        party=party,
        extra=data.get("extra", {}),
    )


# =========================================================================
# STANDALONE MODE — Internal engine + full dashboard
# =========================================================================

def run_standalone_mode(console: Console, system_tag: str, seed=None,
                        party_names=None, companion=False):
    """Standalone mode: create engine internally, full dashboard."""
    engine = create_engine(system_tag, seed=seed, party_names=party_names)
    dashboard = DMDashboard(console, system_tag)

    # Set up progression tracker
    from codex.core.mechanics.progression import ProgressionTracker
    prog_system = {
        "DND5E": "xp", "BITD": "fitd", "SAV": "fitd",
        "STC": "milestone", "BURNWILLOW": "gear", "CROWN": "milestone",
    }.get(system_tag.upper(), "xp")
    dashboard.progression = ProgressionTracker(system=prog_system)

    # Enable companion if requested
    if companion:
        dashboard.dispatch_command("companion on", engine)

    console.clear()
    _print_banner(console, system_tag, "STANDALONE")
    time.sleep(1)

    try:
        while True:
            # Get vitals from live engine
            vitals = get_vitals(engine, system_tag)

            # Render
            console.clear()
            layout = dashboard.render(vitals, engine)
            console.print(layout)

            # Companion auto-action
            if dashboard.companion and dashboard.companion.enabled:
                action = dashboard.companion.decide(engine)
                result = dashboard.companion.execute(action, engine)
                if result:
                    dashboard._notes.append(f"[AI] {result}")

            # Command input
            try:
                cmd = console.input("[bold cyan]DM>[/bold cyan] ")
            except EOFError:
                break

            cmd = cmd.strip()
            if not cmd:
                continue
            if cmd.lower() == "quit":
                console.print("[bold]Dashboard closed.[/bold]")
                break

            # Dispatch with engine
            result = dashboard.dispatch_command(cmd, engine)
            if result:
                console.print(Panel(result, title="Result", border_style="green",
                                    box=box.ROUNDED))
                time.sleep(1.5)

            # Write state frame for Player View consumption
            _write_dm_frame(vitals, dashboard=dashboard)

    except KeyboardInterrupt:
        console.print("\n[bold]Dashboard closed.[/bold]")


def _write_dm_frame(vitals: VitalsSchema, dashboard=None) -> None:
    """Write vitals to dm_frame.json for external consumers.

    If *dashboard* is provided, enriches the frame with conditions and
    initiative data (WO-V35.0).
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "system_name": vitals.system_name,
        "system_tag": vitals.system_tag,
        "primary_resource": vitals.primary_resource,
        "primary_current": vitals.primary_current,
        "primary_max": vitals.primary_max,
        "secondary_resource": vitals.secondary_resource,
        "secondary_current": vitals.secondary_current,
        "secondary_max": vitals.secondary_max,
        "party": vitals.party,
        "extra": vitals.extra,
        "timestamp": time.time(),
    }
    # WO-V35.0: Enrich with conditions and initiative from dashboard
    if dashboard:
        data["conditions"] = dashboard.conditions.to_dict()
        current = dashboard.initiative.current()
        data["initiative"] = {
            "order": dashboard.initiative.get_order(),
            "round": dashboard.initiative.round_number,
            "current": current.name if current else "",
        }
    try:
        DM_FRAME_FILE.write_text(json.dumps(data, default=str))
    except OSError:
        pass


# =========================================================================
# UI HELPERS
# =========================================================================

def _print_banner(console: Console, system_tag: str, mode: str):
    """Print startup banner."""
    banner = Text()
    banner.append("DM DASHBOARD", style="bold cyan")
    banner.append(f"  [{system_tag.upper()}]", style="dim")
    banner.append(f"  {mode} MODE\n", style="bold yellow")
    banner.append("Type 'help' for commands, 'quit' to exit.\n", style="dim white")
    console.print(Panel(banner, box=box.DOUBLE, border_style="cyan"))


# =========================================================================
# MAIN
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="DM Dashboard — Live Diagnostic View",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python play_dm_view.py                              # Service mode\n"
            "  python play_dm_view.py --system dnd5e               # Service, DnD5e hint\n"
            "  python play_dm_view.py --standalone --system burnwillow --seed 42\n"
            "  python play_dm_view.py --standalone --system bitd\n"
            "  python play_dm_view.py --standalone --party Kael,Bryn,Neve\n"
        ),
    )
    parser.add_argument("--system", default="burnwillow",
                        choices=["burnwillow", "crown", "bitd", "dnd5e", "stc"],
                        help="Game system (default: burnwillow)")
    parser.add_argument("--standalone", action="store_true",
                        help="Run with internal engine (not watching state file)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for dungeon generation")
    parser.add_argument("--party", type=str, default=None,
                        help="Comma-separated party names (e.g. Kael,Bryn,Neve)")
    parser.add_argument("--companion", action="store_true",
                        help="Enable AI companion on startup")

    args = parser.parse_args()
    console = Console()
    system_tag = args.system.upper()
    party_names = args.party.split(",") if args.party else None

    if args.standalone:
        run_standalone_mode(console, system_tag, args.seed, party_names, args.companion)
    else:
        run_service_mode(console, system_tag)


if __name__ == "__main__":
    main()

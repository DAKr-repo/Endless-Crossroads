#!/usr/bin/env python3
"""
CROWN & CREW — Terminal Interface
----------------------------------
Interactive terminal loop for the Crown & Crew narrative engine.
Supports variable-length arcs, quest archetypes, rest mechanics,
tarot card rendering, and Mimir's Vault access.

Version: 2.0 (Rest + Quests + Tarot)
"""

import json
import time
import sys
import os
from pathlib import Path
from codex.games.crown.engine import CrownAndCrewEngine

# Scene progression system (optional — backward compatible)
try:
    from codex.games.crown.scenes import CrownSceneRunner
    SCENES_AVAILABLE = True
except ImportError:
    SCENES_AVAILABLE = False

# Optional Rich + Tarot imports with fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from codex.integrations.tarot import render_tarot_card, get_card_for_context
    TAROT_AVAILABLE = True
except ImportError:
    TAROT_AVAILABLE = False

# Quest archetype system
try:
    from codex.games.crown.quests import list_quests, get_quest
    QUESTS_AVAILABLE = True
except ImportError:
    QUESTS_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def type_writer(text, speed=0.01):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()


def _render_plain(title: str | None, body: str):
    """Plain-text fallback renderer for terminals without Rich."""
    lines = []
    if title:
        lines.append(f"\n--- {title} ---")
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


def display_card(context: str, text: str, title: str | None = None):
    """Render text as a tarot card if available, else plain panel or print."""
    if TAROT_AVAILABLE and RICH_AVAILABLE:
        card_key = get_card_for_context(context)
        card = render_tarot_card(card_key, text, custom_title=title, width=60)
        console.print(card)
    elif RICH_AVAILABLE:
        console.print(Panel(text, title=title, width=60, box=box.HEAVY))
    else:
        console.print(_render_plain(title, text))


def offer_vault():
    """Between-day prompt that optionally opens Mimir's Vault."""
    print("\n  [Enter] Continue    [L] Consult Mimir's Vault    [T] Tutorial")
    choice = input("\n> ").strip().lower()
    if choice == "t":
        try:
            from rich.console import Console as RichConsole
            from codex.core.services.tutorial import TutorialBrowser, PlatformTutorial
            import codex.core.services.tutorial_content  # noqa: F401
            con = RichConsole()
            browser = TutorialBrowser(tutorial=PlatformTutorial(), system_filter="crown")
            browser.run_loop(con)
        except Exception:
            print("  [Tutorial unavailable]")
        return
    if choice == "l":
        try:
            from rich.console import Console as RichConsole
            from codex.core.services.librarian import LibrarianTUI
        except ImportError:
            print("  [Mimir's Vault unavailable]")
            return

        mimir_fn = None
        try:
            from codex.integrations.mimir import query_mimir
            mimir_fn = query_mimir
        except ImportError:
            pass

        con = RichConsole()
        lib = LibrarianTUI(mimir_fn=mimir_fn, system_id=None)
        lib.run_loop(con)


def select_quest() -> dict | None:
    """Show quest selection menu. Returns world_state dict or None for default."""
    if not QUESTS_AVAILABLE:
        return None

    quests = list_quests()
    if not quests:
        return None

    print("\n  [0] Prologue March (classic 5-day campaign)")
    for i, q in enumerate(quests, 1):
        print(f"  [{i}] {q.name} ({q.arc_length} days) — {q.description[:50]}")

    choice = input("\n> Select campaign type: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(quests):
        quest = quests[int(choice) - 1]
        return quest
    return None


def rest_choice(engine: CrownAndCrewEngine) -> str:
    """Prompt for rest type between days."""
    print("\n  [L] Long Rest (advance day)  [S] Short Rest (minor event)  [N] No Rest")
    choice = input("\n> Rest choice: ").strip().lower()
    if choice in ('s', 'short'):
        return engine.trigger_short_rest()
    elif choice in ('n', 'none'):
        return engine.skip_rest()
    else:
        return engine.trigger_long_rest()


def _parse_module_arg() -> str:
    """Return the value of --module <path> from sys.argv, or empty string."""
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--module" and i < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith("--module="):
            return arg.split("=", 1)[1]
    return ""


def _load_campaign_json(module_dir: str) -> dict:
    """Load campaign.json from a module directory.

    Args:
        module_dir: Path to the module directory.

    Returns:
        Parsed campaign.json dict, or empty dict on failure.
    """
    campaign_path = Path(module_dir) / "campaign.json"
    if not campaign_path.exists():
        return {}
    try:
        with open(campaign_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [Warning: could not load campaign.json — {e}]")
        return {}


def _discover_crown_modules() -> list:
    """Scan vault_maps/modules/ for crown module directories.

    Returns list of dicts with 'path' (module dir) and 'name' (display name).
    """
    modules_dir = Path(__file__).resolve().parent / "vault_maps" / "modules"
    if not modules_dir.is_dir():
        return []
    results = []
    for entry in sorted(modules_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Check for campaign.json (crown modules) or module_manifest.json with system_id=crown
        campaign = entry / "campaign.json"
        manifest = entry / "module_manifest.json"
        if campaign.exists():
            try:
                data = json.loads(campaign.read_text())
                results.append({
                    "path": str(entry),
                    "name": data.get("campaign_title", entry.name),
                })
                continue
            except Exception:
                pass
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text())
                if data.get("system_id") == "crown":
                    results.append({
                        "path": str(entry),
                        "name": data.get("display_name", entry.name),
                    })
            except Exception:
                continue
    return results


def main():
    clear_screen()

    # --- Module argument (--module <path>) ---
    module_dir = _parse_module_arg()
    campaign_data: dict = {}
    if module_dir:
        campaign_data = _load_campaign_json(module_dir)
        if campaign_data:
            print(f"  [Module loaded: {Path(module_dir).name}]")

    # --- Module discovery (interactive) ---
    if not module_dir:
        crown_mods = _discover_crown_modules()
        if crown_mods:
            print("\n  Adventure Modules:")
            print("  [0] Original Campaign")
            for i, m in enumerate(crown_mods, 1):
                print(f"  [{i}] {m['name']}")
            try:
                choice = input("  Select module [0]: ").strip() or "0"
                idx = int(choice)
                if 0 < idx <= len(crown_mods):
                    module_dir = crown_mods[idx - 1]["path"]
                    campaign_data = _load_campaign_json(module_dir)
                    if campaign_data:
                        print(f"  [Module loaded: {Path(module_dir).name}]")
            except (ValueError, EOFError, KeyboardInterrupt):
                pass

    # --- Quest Selection ---
    print("=" * 58)
    print("        CROWN & CREW: NARRATIVE CAMPAIGN ENGINE")
    print("=" * 58)

    quest = select_quest()
    if quest is not None:
        world_state = quest.to_world_state()
        # Merge module world_state fields if present (module takes lower priority)
        if campaign_data.get("world_state"):
            merged = dict(campaign_data["world_state"])
            merged.update(world_state)
            world_state = merged
        engine = CrownAndCrewEngine(
            world_state=world_state,
            arc_length=quest.arc_length,
            rest_config=quest.rest_config,
        )
        campaign_title = quest.name
    elif campaign_data.get("world_state"):
        engine = CrownAndCrewEngine(world_state=campaign_data["world_state"])
        campaign_title = campaign_data.get("campaign_title", "The Prologue March")
    else:
        engine = CrownAndCrewEngine()
        campaign_title = campaign_data.get("campaign_title", "The Prologue March")

    # --- Attach scene runner if campaign data contains scene definitions ---
    if SCENES_AVAILABLE and campaign_data:
        runner = CrownSceneRunner.from_campaign_json(campaign_data)
        if not runner.is_complete() or runner.chapters:
            engine.set_scene_runner(runner)

    clear_screen()

    # --- Campaign Banner ---
    crown_term = engine.terms.get("crown", "The Crown")
    crew_term = engine.terms.get("crew", "The Crew")

    if RICH_AVAILABLE:
        banner = Panel(
            f"[bold]{crown_term}[/bold] vs [bold]{crew_term}[/bold]\n\n"
            f"Patron: [cyan]{engine.patron}[/cyan]\n"
            f"Leader: [magenta]{engine.leader}[/magenta]\n"
            f"Arc: {engine.arc_length} days",
            title=f"[bold gold1]{campaign_title}[/bold gold1]",
            border_style="gold1",
            box=box.DOUBLE,
            width=58,
        )
        console.print(banner)
    else:
        print(f"\n  {campaign_title}")
        print(f"  {crown_term} vs {crew_term}")
        print(f"  Patron: {engine.patron}")
        print(f"  Leader: {engine.leader}")
        print(f"  Arc: {engine.arc_length} days")

    print("\nThe journey begins now...")
    time.sleep(2)

    # --- Main Day Loop ---
    while engine.day <= engine.arc_length:
        clear_screen()

        # --- MORNING EVENT ---
        morning = engine.get_morning_event()
        if RICH_AVAILABLE:
            console.print(
                Panel(
                    f"[dim italic]{morning['text']}[/dim italic]",
                    title=f"[bold]Dawn — Day {engine.day}/{engine.arc_length}[/bold]",
                    border_style="yellow",
                    width=60,
                )
            )
        else:
            print(f"\n--- Dawn — Day {engine.day}/{engine.arc_length} ---")
            print(f"  {morning['text']}")

        time.sleep(1)

        # --- THE WORLD ---
        world_prompt = engine.get_world_prompt()
        display_card("world", world_prompt, f"[dim]Day {engine.day} — The Hostile Grounds[/dim]")
        print("[The party travels through the day...]")
        time.sleep(1)

        # --- NIGHT: THE CAMPFIRE ---
        print()
        if RICH_AVAILABLE:
            console.print(f"[bold red]NIGHT FALLS.[/bold red] [dim]{engine.get_status()}[/dim]")
        else:
            print(f"NIGHT FALLS. {engine.get_status()}")

        # Breach Day Special
        if engine.is_breach_day():
            witness = engine.get_secret_witness()
            display_card("legacy", witness, "[bold red]THE BREACH — Secret Witness[/bold red]")
            print("[You must decide how to react to what you saw...]")

        # --- SCENE PHASE (optional, from campaign.json) ---
        scene = engine.get_scene_for_today()
        if scene:
            print()
            if RICH_AVAILABLE:
                scene_title = scene.location if scene.location else f"Day {engine.day} — Scene"
                console.print(Panel(
                    scene.description,
                    title=f"[bold]{scene_title}[/bold]",
                    border_style="cyan",
                    width=60,
                ))
            else:
                loc = scene.location or f"Day {engine.day}"
                print(f"\n--- {loc} ---")
                print(f"  {scene.description}")

            for i, text in enumerate(scene.get_choice_texts()):
                print(f"  [{i + 1}] {text}")

            scene_input = ""
            while not scene_input.isdigit() or not (1 <= int(scene_input) <= len(scene.choices)):
                scene_input = input("\n> Your choice: ").strip()
                if not scene_input:
                    scene_input = "1"

            result = engine.resolve_scene_choice(int(scene_input) - 1)
            if result.get("narrative"):
                print(f"\n  {result['narrative']}")
            sway_delta = result.get("sway_effect", 0)
            if sway_delta != 0:
                direction = "toward the Crown" if sway_delta > 0 else "toward the Crew"
                print(f"  [Sway shifts {direction}. Now: {engine.sway:+d}]")
            print()
            input("[Press Enter to continue...]")

        # --- Allegiance Choice ---
        print(f"\nWho do you serve tonight?")
        print(f"  [C] {crown_term} (Order, Law, Safety)")
        print(f"  [R] {crew_term} (Freedom, Bonds, Chaos)")

        choice = ""
        while choice not in ['c', 'r']:
            choice = input("\n> Your Choice (C/R): ").lower().strip()

        side = "crown" if choice == 'c' else "crew"
        result_text = engine.declare_allegiance(side)

        if RICH_AVAILABLE:
            console.print(f"\n[bold]{result_text}[/bold]")
        else:
            print(f"\n--> {result_text}")

        # --- Allegiance Prompt Reveal ---
        prompt = engine.get_prompt()
        card_context = "crown" if side == "crown" else "crew"
        display_card(card_context, prompt, f"[dim]The Dilemma[/dim]")

        # --- Campfire (not on Breach day) ---
        if not engine.is_breach_day():
            campfire = engine.get_campfire_prompt()
            display_card("campfire", campfire, f"[dim]The {engine.terms.get('campfire', 'Campfire')}[/dim]")

        input("\n[PRESS ENTER TO PROCEED TO MIDNIGHT COUNCIL]")

        # --- MIDNIGHT COUNCIL ---
        clear_screen()
        dilemma = engine.get_council_dilemma()

        if RICH_AVAILABLE:
            dilemma_text = (
                f"[italic]{dilemma['prompt']}[/italic]\n\n"
                f"[cyan][1] {crown_term}: {dilemma['crown']}[/cyan]\n"
                f"[magenta][2] {crew_term}: {dilemma['crew']}[/magenta]"
            )
            console.print(Panel(
                dilemma_text,
                title=f"[bold]Day {engine.day} — Midnight Council[/bold]",
                border_style="bright_white",
                box=box.DOUBLE,
                width=60,
            ))
        else:
            print(f"\n--- Day {engine.day}: Midnight Council ---")
            print(f"  {dilemma['prompt']}")
            print(f"\n  [1] {crown_term}: {dilemma['crown']}")
            print(f"  [2] {crew_term}: {dilemma['crew']}")

        vote = ""
        while vote not in ['1', '2']:
            vote = input("\n> Your Vote (1/2): ").strip()

        vote_side = "crown" if vote == '2' else "crew"
        result = engine.resolve_vote({vote_side: 1})

        if RICH_AVAILABLE:
            console.print(f"\n[bold]{result['flavor']}[/bold]")
        else:
            print(f"\n--> {result['flavor']}")

        # --- Rest Choice ---
        rest_msg = rest_choice(engine)
        print(f"\n  {rest_msg}")

        offer_vault()

    # --- END GAME ---
    clear_screen()
    report = engine.generate_legacy_report()

    display_card("legacy", report, "[bold gold1]Legacy Report[/bold gold1]")

    # Save the receipt
    from pathlib import Path
    saves_dir = Path(__file__).resolve().parent / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    filename = saves_dir / f"character_receipt_{int(time.time())}.txt"
    with open(filename, "w") as f:
        f.write(report)
    print(f"\nCharacter saved to {filename}")


if __name__ == "__main__":
    main()

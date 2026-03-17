#!/usr/bin/env python3
"""
CROWN & CREW — Terminal Interface
----------------------------------
Interactive terminal loop for the Crown & Crew narrative engine.
Supports variable-length arcs, quest archetypes, rest mechanics,
tarot card rendering, and Mimir's Vault access.

Version: 2.0 (Rest + Quests + Tarot)
"""

import time
import sys
import os
from codex.games.crown.engine import CrownAndCrewEngine

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


def display_card(context: str, text: str, title: str | None = None):
    """Render text as a tarot card if available, else plain panel or print."""
    if TAROT_AVAILABLE and RICH_AVAILABLE:
        card_key = get_card_for_context(context)
        card = render_tarot_card(card_key, text, custom_title=title, width=60)
        console.print(card)
    elif RICH_AVAILABLE:
        console.print(Panel(text, title=title, width=60, box=box.HEAVY))
    else:
        if title:
            print(f"\n--- {title} ---")  # noqa: CodeQL — game narrative, not credentials
        print(text)  # noqa: CodeQL — game narrative text, not sensitive data
        print()


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


def main():
    clear_screen()

    # --- Quest Selection ---
    print("=" * 58)
    print("        CROWN & CREW: NARRATIVE CAMPAIGN ENGINE")
    print("=" * 58)

    quest = select_quest()
    if quest is not None:
        world_state = quest.to_world_state()
        engine = CrownAndCrewEngine(
            world_state=world_state,
            arc_length=quest.arc_length,
            rest_config=quest.rest_config,
        )
        campaign_title = quest.name
    else:
        engine = CrownAndCrewEngine()
        campaign_title = "The Prologue March"

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

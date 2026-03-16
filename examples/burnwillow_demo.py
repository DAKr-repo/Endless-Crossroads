#!/usr/bin/env python3
"""
Burnwillow UI Demo
==================
Demonstrates both terminal (Rich) and Discord embed outputs
for the Paper Doll character sheet system.

Author: Codex Designer
Usage: python burnwillow_demo.py
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

from codex.games.burnwillow.paper_doll import (
    Character,
    CharacterStats,
    GearItem,
    render_paper_doll
)
from codex.games.burnwillow.discord_embed import (
    character_to_discord_embed,
    character_to_discord_embed_compact
)


def create_test_characters() -> list[Character]:
    """Create sample characters for testing different builds."""

    # Character 1: Lightly equipped starter
    char1_stats = CharacterStats(might=12, wits=14, grit=10, aether=8)
    char1 = Character(
        name="Fern",
        title="The Scavenger",
        hp_current=8,
        stats=char1_stats,
        doom=1,
        right_hand=GearItem(name="Rusty Shiv", tier=1, dice_contribution=1),
        chest=GearItem(name="Tattered Cloak", tier=1, dice_contribution=1)
    )

    # Character 2: Mid-game balanced build
    char2_stats = CharacterStats(might=14, wits=12, grit=16, aether=10)
    char2 = Character(
        name="Moss",
        title="The Wanderer",
        hp_current=12,
        stats=char2_stats,
        doom=3,
        head=GearItem(name="Bark Helm", tier=2, dice_contribution=2),
        chest=GearItem(name="Ironbark Plate", tier=2, dice_contribution=2),
        legs=GearItem(name="Thornwalker", tier=2, dice_contribution=2),
        right_hand=GearItem(name="Sap Cudgel", tier=2, dice_contribution=2),
        left_hand=GearItem(name="Scrap Shield", tier=1, dice_contribution=1)
    )

    # Character 3: Max dice pool end-game
    char3_stats = CharacterStats(might=16, wits=10, grit=18, aether=14)
    char3 = Character(
        name="Willow",
        title="The Lightbearer",
        hp_current=18,
        stats=char3_stats,
        doom=7,
        head=GearItem(name="Crown of Embers", tier=3, dice_contribution=3),
        shoulders=GearItem(name="Mantle of Ash", tier=2, dice_contribution=2),
        neck=GearItem(name="Sunresin Charm", tier=4, dice_contribution=4),
        chest=GearItem(name="Burnwillow Core", tier=5, dice_contribution=5),
        arms=GearItem(name="Petrified Vambraces", tier=3, dice_contribution=3),
        legs=GearItem(name="Heartwood Greaves", tier=3, dice_contribution=3),
        right_hand=GearItem(name="Light's Edge", tier=5, dice_contribution=5),
        left_hand=GearItem(name="Moonstone Focus", tier=3, dice_contribution=3),
        right_ring=GearItem(name="Ring of Cinders", tier=2, dice_contribution=2),
        left_ring=GearItem(name="Fungal Band", tier=1, dice_contribution=1)
    )

    return [char1, char2, char3]


def demo_terminal_output(console: Console):
    """Show terminal Rich output for all test characters."""
    characters = create_test_characters()

    console.rule("[bold #FFD700]BURNWILLOW PAPER DOLL SYSTEM[/bold #FFD700]", style="#2D5016")
    console.print()

    for char in characters:
        console.print(render_paper_doll(char, console_width=80))
        console.print()


def demo_discord_output(console: Console):
    """Show Discord embed JSON for comparison."""
    characters = create_test_characters()

    console.rule("[bold #FFD700]DISCORD EMBED TRANSLATION[/bold #FFD700]", style="#2D5016")
    console.print()

    for i, char in enumerate(characters, 1):
        console.print(f"[bold #FFD700]Character {i}: {char.name}[/bold #FFD700]")
        console.print()

        # Full embed
        full_embed = character_to_discord_embed(char)
        console.print(Panel(
            json.dumps(full_embed, indent=2),
            title="Full Embed JSON",
            border_style="#00FFCC",
            box=box.ROUNDED
        ))
        console.print()

        # Compact embed
        compact_embed = character_to_discord_embed_compact(char)
        console.print(Panel(
            json.dumps(compact_embed, indent=2),
            title="Compact Embed JSON",
            border_style="#CC5500",
            box=box.ROUNDED
        ))
        console.print()
        console.print("[dim]" + "─" * 80 + "[/dim]")
        console.print()


def demo_comparison(console: Console):
    """Side-by-side comparison of terminal vs Discord."""
    char = create_test_characters()[1]  # Use middle character

    console.rule("[bold #FFD700]TERMINAL vs DISCORD COMPARISON[/bold #FFD700]", style="#2D5016")
    console.print()

    console.print("[bold #00FFCC]TERMINAL OUTPUT:[/bold #00FFCC]")
    console.print(render_paper_doll(char, console_width=80))
    console.print()

    console.print("[bold #00FFCC]DISCORD EMBED (Compact):[/bold #00FFCC]")
    compact = character_to_discord_embed_compact(char)
    console.print(Panel(
        json.dumps(compact, indent=2),
        border_style="#2D5016",
        box=box.DOUBLE
    ))


def demo_dice_pool_progression(console: Console):
    """Show how dice pool visualization scales from 1d6 to 5d6."""
    from codex.games.burnwillow.paper_doll import render_dice_pips

    console.rule("[bold #FFD700]DICE POOL PROGRESSION[/bold #FFD700]", style="#2D5016")
    console.print()

    tiers = [
        ("Tier I - Scrap/Wood", 1),
        ("Tier II - Ironbark/Hide", 2),
        ("Tier III - Heartwood/Moonstone", 3),
        ("Tier IV - Ambercore/Sunresin", 4),
        ("Tier V - Burnwillow/Light", 5)
    ]

    for tier_name, dice in tiers:
        pips = render_dice_pips(dice, max_pips=5)
        text = Text()
        text.append(f"{tier_name:<35}", style="#F5F5DC")
        text.append(pips)
        text.append(f"  {dice}d6", style="#00FFCC bold")
        console.print(text)

    console.print()
    console.print("[dim]Note: Base dice pool is 1d6 + gear contributions, capped at 5d6 total.[/dim]")


def demo_hp_thresholds(console: Console):
    """Show HP bar color thresholds."""
    from codex.games.burnwillow.paper_doll import render_hp_bar

    console.rule("[bold #FFD700]HP BAR COLOR THRESHOLDS[/bold #FFD700]", style="#2D5016")
    console.print()

    thresholds = [
        ("Healthy (>60%)", 15, 15),
        ("Wounded (60%)", 9, 15),
        ("Bloodied (30%)", 5, 15),
        ("Critical (<30%)", 2, 15),
        ("Near Death", 1, 15),
    ]

    for label, current, maximum in thresholds:
        text = Text()
        text.append(f"{label:<20}", style="#F5F5DC")
        text.append(render_hp_bar(current, maximum, width=15))
        text.append(f"  {current}/{maximum}", style="#F5F5DC")
        console.print(text)


def main():
    """Run all demos."""
    console = Console()
    console.clear()

    # Title banner
    title = Text()
    title.append("\n")
    title.append("╔═══════════════════════════════════════════════════════════════╗\n", style="#2D5016")
    title.append("║  ", style="#2D5016")
    title.append("BURNWILLOW PAPER DOLL SYSTEM", style="#FFD700 bold")
    title.append("                             ║\n", style="#2D5016")
    title.append("║  ", style="#2D5016")
    title.append("Bioluminescent Decay UI Framework", style="#00FFCC")
    title.append("                          ║\n", style="#2D5016")
    title.append("╚═══════════════════════════════════════════════════════════════╝\n", style="#2D5016")
    console.print(title)

    # Menu
    console.print("[bold #FFD700]Available Demos:[/bold #FFD700]")
    console.print("  1. Terminal Output (Rich Library)")
    console.print("  2. Discord Embed JSON")
    console.print("  3. Side-by-Side Comparison")
    console.print("  4. Dice Pool Progression")
    console.print("  5. HP Bar Thresholds")
    console.print("  6. Run All Demos")
    console.print()

    choice = console.input("[bold #00FFCC]Select demo (1-6):[/bold #00FFCC] ")

    console.print()

    if choice == "1":
        demo_terminal_output(console)
    elif choice == "2":
        demo_discord_output(console)
    elif choice == "3":
        demo_comparison(console)
    elif choice == "4":
        demo_dice_pool_progression(console)
    elif choice == "5":
        demo_hp_thresholds(console)
    elif choice == "6":
        demo_terminal_output(console)
        console.input("\n[dim]Press Enter to continue...[/dim]")
        console.clear()
        demo_discord_output(console)
        console.input("\n[dim]Press Enter to continue...[/dim]")
        console.clear()
        demo_comparison(console)
        console.input("\n[dim]Press Enter to continue...[/dim]")
        console.clear()
        demo_dice_pool_progression(console)
        console.print()
        demo_hp_thresholds(console)
    else:
        console.print("[bold #CC5500]Invalid choice. Running default demo.[/bold #CC5500]")
        demo_terminal_output(console)

    console.print()
    console.print("[dim]Demo complete.[/dim]")


if __name__ == "__main__":
    main()

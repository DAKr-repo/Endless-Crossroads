#!/usr/bin/env python3
"""
test_burnwillow_ui.py - Visual test suite for Burnwillow Rich UI

Run this to see all UI components in action.
Tests both standalone UI and integration with game engine.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

# Import UI components
from codex.games.burnwillow.ui import (
    render_gear_grid,
    render_roll_result,
    render_status,
    render_death_screen,
    RunStatistics,
    MetaUnlocks,
    WILLOW,
    FUNGAL_CYAN,
    GLOW
)

# Try to import game engine
try:
    from codex.games.burnwillow.engine import (
        BurnwillowEngine,
        Character,
        GearSlot,
        StatType,
        DC,
        create_starter_gear
    )
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False
    print("[WARNING] burnwillow_module.py not found. Using stub data only.")


def test_full_integration():
    """Test UI with full game engine integration."""
    console = Console()

    console.print("\n")
    console.print(Panel(
        Text("BURNWILLOW INTEGRATION TEST", justify="center", style=WILLOW),
        border_style=FUNGAL_CYAN,
        box=box.DOUBLE
    ))
    console.print("\n")

    # Initialize engine
    engine = BurnwillowEngine()

    # Create character
    console.print(Text("Creating Character...", style=WILLOW))
    hero = engine.create_character("Kael the Wanderer")

    # Equip starter gear
    console.print(Text("Equipping Starter Gear...", style=WILLOW))
    starter = create_starter_gear()
    hero.gear.equip(starter[0])  # Sword
    hero.gear.equip(starter[1])  # Jerkin
    hero.gear.equip(starter[3])  # Gloves
    hero.gear.equip(starter[4])  # Shield

    console.print("\n")

    # Test 1: Equipment Display
    console.print(Panel(
        Text("TEST 1: EQUIPMENT DISPLAY", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))
    console.print(render_gear_grid(hero.gear.slots, console))
    console.print("\n")

    # Test 2: Character Status
    console.print(Panel(
        Text("TEST 2: CHARACTER STATUS", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    character_data = {
        'hp_current': hero.current_hp,
        'hp_max': hero.max_hp,
        'dungeon_depth': 1,
        'doom_clock': 0,
        'doom_max': 10,
        'stats': {
            'might': (hero.might, hero.get_stat_mod(StatType.MIGHT)),
            'wits': (hero.wits, hero.get_stat_mod(StatType.WITS)),
            'grit': (hero.grit, hero.get_stat_mod(StatType.GRIT)),
            'aether': (hero.aether, hero.get_stat_mod(StatType.AETHER))
        }
    }

    console.print(render_status(character_data, console))
    console.print("\n")

    # Test 3: Dice Rolling
    console.print(Panel(
        Text("TEST 3: DICE ROLLING", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    # Lockpicking check (success likely)
    result = hero.make_check(StatType.WITS, DC.HARD.value)
    console.print(render_roll_result(
        result.rolls,
        result.modifier,
        result.total,
        result.dc,
        "Lockpicking Check"
    ))
    console.print("\n")

    # Attack check
    result = hero.make_check(StatType.MIGHT, DC.HARD.value)
    console.print(render_roll_result(
        result.rolls,
        result.modifier,
        result.total,
        result.dc,
        "Melee Attack"
    ))
    console.print("\n")

    # Test 4: Combat Simulation
    console.print(Panel(
        Text("TEST 4: COMBAT SIMULATION", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    console.print(Text(f"Hero HP: {hero.current_hp}/{hero.max_hp}", style=GLOW))

    # Take damage
    damage = hero.take_damage(5)
    console.print(Text(f"→ Took 5 damage (DR absorbed {5-damage})", style="yellow"))
    console.print(Text(f"→ Actual damage: {damage}", style="red"))

    # Show updated status
    character_data['hp_current'] = hero.current_hp
    console.print(render_status(character_data, console))
    console.print("\n")

    # Test 5: Death Screen
    console.print(Panel(
        Text("TEST 5: DEATH SCREEN", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    run_stats = RunStatistics(
        floors_cleared=3,
        enemies_slain=22,
        turns_taken=145,
        chests_opened=7,
        gold_collected=380,
        highest_depth=4,
        cause_of_death="Blight Warden"
    )

    meta_unlocks = MetaUnlocks(
        total_runs=9,
        deepest_depth=3,
        total_kills=156,
        unlocked_starts=["Wanderer", "Thief"],
        unlocked_blessings=["Fortune"]
    )

    console.print(render_death_screen(run_stats, meta_unlocks, 4, console))
    console.print("\n")

    console.print(Panel(
        Text("ALL INTEGRATION TESTS COMPLETE", justify="center", style=GLOW),
        border_style=FUNGAL_CYAN
    ))
    console.print("\n")


def test_standalone():
    """Test UI components with stub data (no engine)."""
    console = Console()

    console.print("\n")
    console.print(Panel(
        Text("BURNWILLOW STANDALONE UI TEST", justify="center", style=WILLOW),
        border_style=FUNGAL_CYAN,
        box=box.DOUBLE
    ))
    console.print("\n")

    # Import GearSlot from UI module
    from codex.games.burnwillow.ui import GearSlot

    # Test 1: Empty Equipment Grid
    console.print(Panel(
        Text("TEST 1: EMPTY EQUIPMENT GRID", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    empty_gear = {slot: None for slot in GearSlot}
    console.print(render_gear_grid(empty_gear, console))
    console.print("\n")

    # Test 2: Character Status (Low HP)
    console.print(Panel(
        Text("TEST 2: LOW HP STATUS", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    low_hp_data = {
        'hp_current': 3,
        'hp_max': 15,
        'dungeon_depth': 5,
        'doom_clock': 8,
        'doom_max': 10,
        'stats': {
            'might': (14, 2),
            'wits': (12, 1),
            'grit': (16, 3),
            'aether': (10, 0)
        }
    }

    console.print(render_status(low_hp_data, console))
    console.print("\n")

    # Test 3: Failed Roll
    console.print(Panel(
        Text("TEST 3: FAILED ROLL", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    failed_rolls = [1, 1, 2]
    console.print(render_roll_result(
        failed_rolls,
        0,
        sum(failed_rolls),
        12,
        "Critical Failure"
    ))
    console.print("\n")

    # Test 4: Perfect Roll
    console.print(Panel(
        Text("TEST 4: PERFECT ROLL", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    perfect_rolls = [6, 6, 6, 6, 6]
    console.print(render_roll_result(
        perfect_rolls,
        4,
        sum(perfect_rolls) + 4,
        20,
        "Legendary Success"
    ))
    console.print("\n")

    # Test 5: First Death
    console.print(Panel(
        Text("TEST 5: FIRST DEATH", style=f"bold {WILLOW}"),
        border_style=FUNGAL_CYAN
    ))

    first_run_stats = RunStatistics(
        floors_cleared=0,
        enemies_slain=1,
        turns_taken=12,
        chests_opened=0,
        gold_collected=0,
        highest_depth=1,
        cause_of_death="Starving Rat"
    )

    first_unlocks = MetaUnlocks(
        total_runs=0,
        deepest_depth=0,
        total_kills=0,
        unlocked_starts=["Wanderer"],
        unlocked_blessings=[]
    )

    console.print(render_death_screen(first_run_stats, first_unlocks, 1, console))
    console.print("\n")

    console.print(Panel(
        Text("ALL STANDALONE TESTS COMPLETE", justify="center", style=GLOW),
        border_style=FUNGAL_CYAN
    ))
    console.print("\n")


if __name__ == "__main__":
    console = Console()

    # Check if engine is available
    if ENGINE_AVAILABLE:
        console.print(Text("✓ Game engine detected", style="green"))
        console.print(Text("Running FULL INTEGRATION TEST\n", style="bold yellow"))
        test_full_integration()
    else:
        console.print(Text("✗ Game engine not found", style="red"))
        console.print(Text("Running STANDALONE UI TEST\n", style="bold yellow"))
        test_standalone()

    console.print(Text("\n[Press any key to exit]", style="dim"))

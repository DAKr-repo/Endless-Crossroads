"""
Burnwillow Integration Example
================================

Demonstrates how to combine:
- burnwillow_module.py (game mechanics engine)
- burnwillow_persistence.py (death loop save/load)

This shows the proper separation of concerns:
- Game Engine: Handles dice rolls, combat, gear, checks
- Persistence Layer: Handles save/load, death loop, validation
"""

from codex.games.burnwillow import persistence
from codex.games.burnwillow.engine import BurnwillowEngine, Character, GearItem, GearSlot, GearTier, StatType, DC


def example_new_game():
    """Example: Starting a new game from scratch."""
    print("=" * 70)
    print("EXAMPLE 1: New Game")
    print("=" * 70)

    # Create fresh save data (persistence layer)
    save_data = persistence.initialize_new_save()

    # Extract run_state to initialize game engine
    run_state = save_data["run_state"]

    # Create game engine
    engine = BurnwillowEngine()

    # Load character from persistence into engine
    hero = Character(
        name=run_state["character_name"],
        might=run_state["stats"]["might"]["score"],
        wits=run_state["stats"]["wits"]["score"],
        grit=run_state["stats"]["grit"]["score"],
        aether=run_state["stats"]["aether"]["score"]
    )
    hero.current_hp = run_state["hp"]
    engine.character = hero

    print(f"Character: {hero.name}")
    print(f"HP: {hero.current_hp}/{hero.max_hp}")
    print(f"Might: {hero.might} ({hero.get_stat_mod(StatType.MIGHT):+d})")
    print(f"Legacy Deaths: {save_data['meta_state']['total_deaths']}")

    # Save the initial state
    save_path = "saves/burnwillow_game.json"
    success, error = persistence.save_game(
        run_state=save_data["run_state"],
        meta_state=save_data["meta_state"],
        filepath=save_path
    )

    if success:
        print(f"\n✓ Game saved to: {save_path}")
    else:
        print(f"\n✗ Save failed: {error}")


def example_load_and_play():
    """Example: Load existing save and play a turn."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Load Game and Play")
    print("=" * 70)

    save_path = "saves/burnwillow_game.json"

    # Load from persistence
    save_data, error = persistence.load_game(save_path)
    if not save_data:
        print(f"✗ Load failed: {error}")
        return

    print(f"✓ Loaded: {save_data['run_state']['character_name']}")

    # Initialize game engine with loaded data
    engine = BurnwillowEngine()
    run_state = save_data["run_state"]

    hero = Character(
        name=run_state["character_name"],
        might=run_state["stats"]["might"]["score"],
        wits=run_state["stats"]["wits"]["score"],
        grit=run_state["stats"]["grit"]["score"],
        aether=run_state["stats"]["aether"]["score"]
    )
    hero.current_hp = run_state["hp"]
    engine.character = hero

    # Play: Attack a goblin
    print(f"\n{hero.name} attacks a Goblin!")
    result = hero.make_check(StatType.MIGHT, DC.HARD.value)
    print(result)

    # Update run statistics
    if result.success:
        run_state["run_statistics"]["enemies_slain"] += 1
        print("Goblin defeated!")

    # Save updated state
    success, error = persistence.save_game(
        run_state=run_state,
        meta_state=save_data["meta_state"],
        filepath=save_path
    )

    if success:
        print(f"✓ Progress saved")


def example_character_death():
    """Example: Handle character death (Death Loop)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Character Death (Death Loop)")
    print("=" * 70)

    save_path = "saves/burnwillow_game.json"

    # Load current game
    save_data, error = persistence.load_game(save_path)
    if not save_data:
        print(f"✗ Load failed: {error}")
        return

    old_name = save_data["run_state"]["character_name"]
    old_deaths = save_data["meta_state"]["total_deaths"]

    print(f"Character: {old_name}")
    print(f"Total deaths (before): {old_deaths}")
    print(f"\n{old_name} has fallen!")

    # Execute death loop (wipe run_state, preserve meta_state)
    save_data = persistence.wipe_run_state(save_data)

    new_name = save_data["run_state"]["character_name"]
    new_deaths = save_data["meta_state"]["total_deaths"]

    print(f"\nNew character: {new_name}")
    print(f"Total deaths (after): {new_deaths}")
    print(f"Graveyard size: {len(save_data['meta_state']['graveyard'])}")

    # Show the epitaph
    last_grave = save_data["meta_state"]["graveyard"][-1]
    print(f"\nRest in peace, {last_grave['name']}")
    print(f"  {last_grave['epitaph']}")

    # Save the new state
    success, error = persistence.save_game(
        run_state=save_data["run_state"],
        meta_state=save_data["meta_state"],
        filepath=save_path
    )

    if success:
        print(f"\n✓ Death Loop complete. New hero ready.")


def example_meta_progression():
    """Example: Update meta_state (town upgrades, currency)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Meta Progression (Persistent)")
    print("=" * 70)

    save_path = "saves/burnwillow_game.json"

    # Load game
    save_data, error = persistence.load_game(save_path)
    if not save_data:
        print(f"✗ Load failed: {error}")
        return

    meta = save_data["meta_state"]

    print(f"Legacy Currency: {meta['legacy_currency']}")
    print(f"Town Status: {meta['town_status']}")

    # Simulate earning currency and upgrading town
    print("\nCharacter collects 50 Burnwillow Sap...")
    meta["legacy_currency"] += 50

    print("Upgrading Blacksmith (25 Sap)...")
    if meta["legacy_currency"] >= 25:
        meta["legacy_currency"] -= 25
        meta["town_status"]["blacksmith"] += 1
        print(f"  Blacksmith upgraded to level {meta['town_status']['blacksmith']}")

    # Unlock a blueprint
    print("Discovering Steel Longsword blueprint...")
    if "Steel Longsword" not in meta["unlocked_blueprints"]:
        meta["unlocked_blueprints"].append("Steel Longsword")

    print(f"\nNew Currency: {meta['legacy_currency']}")
    print(f"Blueprints Unlocked: {len(meta['unlocked_blueprints'])}")

    # Save updated meta_state
    success, error = persistence.save_game(
        run_state=save_data["run_state"],
        meta_state=meta,
        filepath=save_path
    )

    if success:
        print(f"✓ Meta progression saved (survives death)")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("BURNWILLOW INTEGRATION DEMONSTRATION")
    print("Combining Game Engine + Death Loop Persistence")
    print("=" * 70)

    example_new_game()
    example_load_and_play()
    example_character_death()
    example_meta_progression()

    print("\n" + "=" * 70)
    print("INTEGRATION EXAMPLES COMPLETE")
    print("=" * 70)

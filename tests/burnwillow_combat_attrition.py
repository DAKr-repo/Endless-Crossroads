#!/usr/bin/env python3
"""
BURNWILLOW COMBAT SIMULATOR: ATTRITION TEST
============================================
Testing resource attrition over consecutive encounters without rest.

CRITICAL QUESTION: Can a Tier 0 player survive 3-5 Rot-Beetles in a row?

This simulates dungeon crawling where the player cannot rest between fights,
testing the "Death Spiral by 1000 Cuts" hypothesis.

Author: Codex Playtester
Version: 1.0.0
Date: 2026-02-06
"""

import random
import statistics
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum


class GauntletResult(Enum):
    """Result of a gauntlet run."""
    SURVIVED = "SURVIVED"
    DEFEATED = "DEFEATED"


@dataclass
class Combatant:
    name: str
    max_hp: int
    hp: int
    damage: int
    dr: int = 0
    defense_dc: int = 10

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: int) -> int:
        actual_damage = max(0, damage - self.dr)
        self.hp -= actual_damage
        return actual_damage

    def reset(self):
        self.hp = self.max_hp


@dataclass
class Player(Combatant):
    dice_count: int = 2
    dice_sides: int = 6
    stat_modifier: int = 1

    def attack_roll(self) -> Tuple[int, List[int]]:
        dice_results = [random.randint(1, self.dice_sides) for _ in range(self.dice_count)]
        total = sum(dice_results) + self.stat_modifier
        return total, dice_results


@dataclass
class Enemy(Combatant):
    pass


def simulate_single_encounter(player: Player, enemy_config: dict) -> dict:
    """
    Simulate a single encounter. Player HP persists, enemy respawns.

    Returns:
        dict with result, rounds, damage_taken, player_hp_after
    """
    enemy = Enemy(
        name=enemy_config['name'],
        max_hp=enemy_config['hp'],
        hp=enemy_config['hp'],
        damage=enemy_config['damage'],
        dr=enemy_config.get('dr', 0),
        defense_dc=enemy_config['dc']
    )

    rounds = 0
    damage_taken_this_fight = 0

    while player.is_alive() and enemy.is_alive():
        rounds += 1

        # Player turn
        attack_total, dice = player.attack_roll()
        if attack_total >= enemy.defense_dc:
            enemy.take_damage(player.damage)

        if not enemy.is_alive():
            break

        # Enemy turn
        damage = player.take_damage(enemy.damage)
        damage_taken_this_fight += damage

        if not player.is_alive():
            break

    return {
        'player_survived': player.is_alive(),
        'rounds': rounds,
        'damage_taken': damage_taken_this_fight,
        'player_hp_after': max(0, player.hp)
    }


def run_gauntlet(player: Player, enemy_config: dict, num_encounters: int, verbose: bool = False) -> dict:
    """
    Run consecutive encounters until player dies or survives all.

    Returns:
        dict with gauntlet_result, encounters_survived, hp_history, total_damage
    """
    player.reset()

    encounters_survived = 0
    hp_history = [player.hp]
    total_damage = 0
    encounter_details = []

    if verbose:
        print(f"\n{'='*70}")
        print(f"GAUNTLET START: {num_encounters}x {enemy_config['name']}")
        print(f"Player HP: {player.hp}/{player.max_hp}, DR: {player.dr}")
        print(f"{'='*70}")

    for i in range(num_encounters):
        if verbose:
            print(f"\n[Encounter {i+1}/{num_encounters}] Player HP: {player.hp}/{player.max_hp}")

        result = simulate_single_encounter(player, enemy_config)

        total_damage += result['damage_taken']
        hp_history.append(result['player_hp_after'])
        encounter_details.append(result)

        if verbose:
            if result['player_survived']:
                print(f"  → Victory in {result['rounds']} rounds. Took {result['damage_taken']} damage. HP: {result['player_hp_after']}/{player.max_hp}")
            else:
                print(f"  → DEFEATED in {result['rounds']} rounds. HP: 0/{player.max_hp}")

        if not result['player_survived']:
            break

        encounters_survived += 1

    gauntlet_result = GauntletResult.SURVIVED if encounters_survived == num_encounters else GauntletResult.DEFEATED

    if verbose:
        print(f"\n{'='*70}")
        if gauntlet_result == GauntletResult.SURVIVED:
            print(f"GAUNTLET COMPLETE: Survived all {num_encounters} encounters!")
            print(f"Final HP: {player.hp}/{player.max_hp} (took {total_damage} total damage)")
        else:
            print(f"GAUNTLET FAILED: Defeated after {encounters_survived}/{num_encounters} encounters")
            print(f"Total damage taken: {total_damage}")
        print(f"{'='*70}\n")

    return {
        'gauntlet_result': gauntlet_result,
        'encounters_survived': encounters_survived,
        'hp_history': hp_history,
        'total_damage': total_damage,
        'encounter_details': encounter_details
    }


def run_batch_gauntlets(enemy_config: dict, num_encounters: int, iterations: int = 100) -> List[dict]:
    """Run multiple gauntlet simulations and collect results."""
    results = []

    for i in range(iterations):
        player = Player(
            name="Tier 0 Adventurer",
            max_hp=10,
            hp=10,
            damage=3,
            dr=1,
            defense_dc=10,
            dice_count=2,
            dice_sides=6,
            stat_modifier=1
        )

        result = run_gauntlet(player, enemy_config, num_encounters, verbose=False)
        results.append(result)

    return results


def analyze_gauntlet_results(results: List[dict], num_encounters: int, enemy_name: str):
    """Print analysis of gauntlet results."""
    total = len(results)
    survived = [r for r in results if r['gauntlet_result'] == GauntletResult.SURVIVED]
    defeated = [r for r in results if r['gauntlet_result'] == GauntletResult.DEFEATED]

    survival_rate = (len(survived) / total) * 100

    avg_encounters_survived = statistics.mean([r['encounters_survived'] for r in results])
    avg_total_damage = statistics.mean([r['total_damage'] for r in results])

    # HP progression analysis (survivors only)
    if survived:
        avg_final_hp = statistics.mean([r['hp_history'][-1] for r in survived])
        min_final_hp = min([r['hp_history'][-1] for r in survived])

        # Average HP after each encounter (survivors only)
        hp_after_each = []
        for encounter_idx in range(num_encounters):
            hp_values = [r['hp_history'][encounter_idx + 1] for r in survived if len(r['hp_history']) > encounter_idx + 1]
            if hp_values:
                hp_after_each.append(statistics.mean(hp_values))
    else:
        avg_final_hp = 0
        min_final_hp = 0
        hp_after_each = []

    # Defeat distribution
    defeat_distribution = {}
    for i in range(num_encounters + 1):
        defeat_distribution[i] = len([r for r in results if r['encounters_survived'] == i and r['gauntlet_result'] == GauntletResult.DEFEATED])

    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║            ATTRITION TEST: CONSECUTIVE ENCOUNTERS                    ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Enemy: {enemy_name:<59} ║")
    print(f"║  Encounters per Gauntlet: {num_encounters:<47} ║")
    print(f"║  Iterations: {total:<56} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Survival Rate:           {survival_rate:>5.1f}% ({len(survived)}/{total})                       ║")
    print(f"║  Defeat Rate:             {100-survival_rate:>5.1f}% ({len(defeated)}/{total})                        ║")
    print(f"║  Avg Encounters Survived: {avg_encounters_survived:>5.2f} / {num_encounters}                            ║")
    print(f"║  Avg Total Damage Taken:  {avg_total_damage:>5.2f}                                       ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  SURVIVOR METRICS (when gauntlet completed)                          ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Avg Final HP:            {avg_final_hp:>5.2f} / 10                                   ║")
    print(f"║  Min Final HP:            {min_final_hp:>5} / 10                                      ║")

    if hp_after_each:
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  HP PROGRESSION (avg HP remaining after each encounter)             ║")
        print("╠══════════════════════════════════════════════════════════════════════╣")
        for idx, avg_hp in enumerate(hp_after_each):
            encounter_num = idx + 1
            print(f"║    After Encounter {encounter_num}:      {avg_hp:>5.2f} / 10                                   ║")

    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  DEFEAT DISTRIBUTION (when players were defeated)                   ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    for encounter_num in range(1, num_encounters + 1):
        count = defeat_distribution.get(encounter_num, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"║    Defeated at Encounter {encounter_num}: {count:>3} ({percentage:>5.1f}%)                             ║")

    # Risk assessment
    if survival_rate >= 80:
        risk = "🟢 LOW - Gauntlet manageable"
    elif survival_rate >= 60:
        risk = "🟡 MEDIUM - Challenging but fair"
    elif survival_rate >= 40:
        risk = "🟠 HIGH - Punishing attrition"
    else:
        risk = "🔴 CRITICAL - Unsustainable attrition"

    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  ATTRITION RISK:          {risk:<48} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()


def main():
    print("\n" + "="*70)
    print("BURNWILLOW ATTRITION TEST: DEATH BY 1000 CUTS")
    print("="*70)

    # Test configurations
    baseline_config = {
        'name': 'Rot-Beetle (BASELINE: DC 8, 4 HP, 2 dmg)',
        'dc': 8,
        'hp': 4,
        'damage': 2
    }

    optionA_config = {
        'name': 'Rot-Beetle (OPTION A: DC 9, 6 HP, 3 dmg)',
        'dc': 9,
        'hp': 6,
        'damage': 3
    }

    # Test 1: 3-encounter gauntlet (common dungeon room)
    print("\n[TEST 1] 3-Encounter Gauntlet (100 iterations)...")
    print("Scenario: Player clears a small dungeon room with 3 beetles")

    baseline_3 = run_batch_gauntlets(baseline_config, num_encounters=3, iterations=100)
    analyze_gauntlet_results(baseline_3, num_encounters=3, enemy_name="Rot-Beetle (BASELINE)")

    optionA_3 = run_batch_gauntlets(optionA_config, num_encounters=3, iterations=100)
    analyze_gauntlet_results(optionA_3, num_encounters=3, enemy_name="Rot-Beetle (OPTION A)")

    # Test 2: 5-encounter gauntlet (full dungeon wing)
    print("\n[TEST 2] 5-Encounter Gauntlet (100 iterations)...")
    print("Scenario: Player clears a full dungeon wing without rest")

    baseline_5 = run_batch_gauntlets(baseline_config, num_encounters=5, iterations=100)
    analyze_gauntlet_results(baseline_5, num_encounters=5, enemy_name="Rot-Beetle (BASELINE)")

    optionA_5 = run_batch_gauntlets(optionA_config, num_encounters=5, iterations=100)
    analyze_gauntlet_results(optionA_5, num_encounters=5, enemy_name="Rot-Beetle (OPTION A)")

    # Verbose sample run
    print("\n[SAMPLE GAUNTLET] Running single verbose 3-encounter gauntlet (OPTION A)...")
    player = Player(
        name="Tier 0 Adventurer",
        max_hp=10,
        hp=10,
        damage=3,
        dr=1,
        defense_dc=10,
        dice_count=2,
        dice_sides=6,
        stat_modifier=1
    )
    run_gauntlet(player, optionA_config, num_encounters=3, verbose=True)

    print("\n[RECOMMENDATIONS]")
    print("=" * 70)
    print("Attrition testing reveals:")
    print("- 3-encounter gauntlets test 'dungeon room' sustainability")
    print("- 5-encounter gauntlets test 'full expedition' endurance")
    print("- If 3-encounter survival < 60%, player NEEDS healing/rest after each room")
    print("- If 5-encounter survival < 30%, healing consumables become mandatory")
    print("\nDesign implications:")
    print("- Add healing potions (restore 1d6 HP, 1-2 per dungeon)")
    print("- Add 'campfire' rest points every 3-5 encounters")
    print("- Consider 'Wounded' condition at 50% HP (mechanical penalty)")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()

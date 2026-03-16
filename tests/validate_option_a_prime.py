#!/usr/bin/env python3
"""
OPTION A-PRIME VALIDATION
=========================
Testing the "Goldilocks" balance for Rot-Beetle.

Target: 75-85% win rate, ~6 HP remaining, ~10% ambush advantage

Configuration: DC 9, 5 HP, 2 damage

Author: Codex Playtester
Version: 1.0.0
Date: 2026-02-06
"""

import random
import statistics
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum


class CombatResult(Enum):
    PLAYER_WIN = "PLAYER_WIN"
    PLAYER_LOSS = "PLAYER_LOSS"


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


def simulate_combat(player: Player, enemy: Combatant, ambush: bool = False) -> dict:
    player.reset()
    enemy.reset()

    rounds = 0
    hits = 0
    misses = 0
    damage_dealt = 0
    damage_taken = 0

    # Ambush
    if ambush:
        attack_total, dice = player.attack_roll()
        if attack_total >= enemy.defense_dc:
            dmg = enemy.take_damage(player.damage)
            damage_dealt += dmg
            hits += 1
        else:
            misses += 1

    # Combat loop
    while player.is_alive() and enemy.is_alive():
        rounds += 1

        # Player turn
        attack_total, dice = player.attack_roll()
        if attack_total >= enemy.defense_dc:
            dmg = enemy.take_damage(player.damage)
            damage_dealt += dmg
            hits += 1
        else:
            misses += 1

        if not enemy.is_alive():
            break

        # Enemy turn
        dmg = player.take_damage(enemy.damage)
        damage_taken += dmg

    result = CombatResult.PLAYER_WIN if player.is_alive() else CombatResult.PLAYER_LOSS

    return {
        'result': result,
        'rounds': rounds,
        'player_hp': max(0, player.hp),
        'damage_dealt': damage_dealt,
        'damage_taken': damage_taken,
        'hits': hits,
        'misses': misses
    }


def run_simulations(config: dict, iterations: int = 100, ambush: bool = False) -> List[dict]:
    results = []

    for _ in range(iterations):
        player = Player(
            name="Tier 0 Adventurer",
            max_hp=10,
            hp=10,
            damage=3,
            dr=1,
            dice_count=2,
            dice_sides=6,
            stat_modifier=1
        )

        enemy = Combatant(
            name=config['name'],
            max_hp=config['hp'],
            hp=config['hp'],
            damage=config['damage'],
            dr=0,
            defense_dc=config['dc']
        )

        result = simulate_combat(player, enemy, ambush=ambush)
        results.append(result)

    return results


def print_analysis(results: List[dict], config: dict, ambush: bool = False):
    total = len(results)
    wins = [r for r in results if r['result'] == CombatResult.PLAYER_WIN]
    losses = [r for r in results if r['result'] == CombatResult.PLAYER_LOSS]

    win_rate = (len(wins) / total) * 100

    if wins:
        avg_hp = statistics.mean([r['player_hp'] for r in wins])
        min_hp = min([r['player_hp'] for r in wins])
        max_hp = max([r['player_hp'] for r in wins])
    else:
        avg_hp = min_hp = max_hp = 0

    avg_rounds = statistics.mean([r['rounds'] for r in results])
    avg_damage_taken = statistics.mean([r['damage_taken'] for r in results])
    avg_hits = statistics.mean([r['hits'] for r in results])
    avg_misses = statistics.mean([r['misses'] for r in results])
    hit_rate = (avg_hits / (avg_hits + avg_misses)) * 100 if (avg_hits + avg_misses) > 0 else 0

    # Risk assessment
    if win_rate >= 85:
        risk = "🟢 LOW (Too easy)"
        verdict = "❌ Still too easy"
    elif 75 <= win_rate < 85:
        risk = "🟡 MEDIUM (TARGET RANGE)"
        verdict = "✅ BALANCED - Ship it"
    elif 60 <= win_rate < 75:
        risk = "🟠 HIGH (Too hard)"
        verdict = "❌ Too difficult"
    else:
        risk = "🔴 CRITICAL (Brutal)"
        verdict = "❌ Unplayable"

    combat_type = "AMBUSH" if ambush else "STANDARD"

    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print(f"║  OPTION A-PRIME VALIDATION ({combat_type} COMBAT)                       ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Configuration: {config['name']:<53} ║")
    print(f"║  Stats: DC {config['dc']}, {config['hp']} HP, {config['damage']} damage                                          ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Iterations:              {total:>5}                                       ║")
    print(f"║  Win Rate:                {win_rate:>5.1f}% ({len(wins)}/{total})                       ║")
    print(f"║  Loss Rate:               {100-win_rate:>5.1f}% ({len(losses)}/{total})                        ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  VICTORY METRICS                                                     ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Avg HP Remaining:        {avg_hp:>5.2f} / 10                                   ║")
    print(f"║  Min HP Remaining:        {min_hp:>5} / 10                                      ║")
    print(f"║  Max HP Remaining:        {max_hp:>5} / 10                                      ║")
    print(f"║  Avg Rounds:              {avg_rounds:>5.2f}                                       ║")
    print(f"║  Avg Damage Taken:        {avg_damage_taken:>5.2f}                                       ║")
    print(f"║  Hit Rate:                {hit_rate:>5.1f}%                                       ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Death Spiral Risk:       {risk:<48} ║")
    print(f"║  Verdict:                 {verdict:<48} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    return win_rate


def main():
    print("\n" + "="*70)
    print("OPTION A-PRIME VALIDATION TEST")
    print("Testing Goldilocks balance: DC 9, 5 HP, 2 damage")
    print("="*70)

    config = {
        'name': 'Rot-Beetle (OPTION A-PRIME)',
        'dc': 9,
        'hp': 5,
        'damage': 2
    }

    print("\n[TEST 1] Running 100 iterations: Standard Combat...")
    standard_results = run_simulations(config, iterations=100, ambush=False)
    standard_win_rate = print_analysis(standard_results, config, ambush=False)

    print("\n[TEST 2] Running 100 iterations: Ambush Combat...")
    ambush_results = run_simulations(config, iterations=100, ambush=True)
    ambush_win_rate = print_analysis(ambush_results, config, ambush=True)

    # Ambush advantage analysis
    ambush_delta = ambush_win_rate - standard_win_rate

    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                     AMBUSH ADVANTAGE ANALYSIS                        ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Standard Win Rate:       {standard_win_rate:>5.1f}%                                     ║")
    print(f"║  Ambush Win Rate:         {ambush_win_rate:>5.1f}%                                     ║")
    print(f"║  Ambush Advantage:        +{ambush_delta:>4.1f}%                                     ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")

    if ambush_delta >= 10:
        ambush_verdict = "✅ GOOD - Meaningful tactical advantage"
    elif ambush_delta >= 5:
        ambush_verdict = "🟡 ACCEPTABLE - Minor advantage"
    else:
        ambush_verdict = "❌ WEAK - Needs ambush redesign"

    print(f"║  Verdict:                 {ambush_verdict:<48} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    print("\n" + "="*70)
    print("FINAL RECOMMENDATION")
    print("="*70)

    if 75 <= standard_win_rate < 85:
        print("✅ OPTION A-PRIME is BALANCED for single encounters")
        print(f"   Win rate: {standard_win_rate:.1f}% (target: 75-85%)")
        print()
        print("NEXT STEPS:")
        print("1. Implement OPTION A-PRIME stats in Rot-Beetle bestiary")
        print("2. Add healing potion system (1d6 HP restore)")
        print("3. Re-test 3-encounter gauntlet with healing")
        print("4. Fix ambush mechanics if advantage < 10%")
    elif standard_win_rate >= 85:
        print("❌ OPTION A-PRIME is still TOO EASY")
        print(f"   Win rate: {standard_win_rate:.1f}% (target: 75-85%)")
        print()
        print("RECOMMENDED ADJUSTMENTS:")
        print("- Increase DC to 10 OR increase HP to 6 OR increase damage to 3")
        print("- Re-run simulation after adjustment")
    else:
        print("❌ OPTION A-PRIME is TOO DIFFICULT")
        print(f"   Win rate: {standard_win_rate:.1f}% (target: 75-85%)")
        print()
        print("RECOMMENDED ADJUSTMENTS:")
        print("- Decrease DC to 8 OR decrease HP to 4 OR keep damage at 2")
        print("- Consider adding +1 to player stat modifier")

    print("="*70)
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
BURNWILLOW COMBAT SIMULATOR: THE GRINDER
=========================================
Stress-testing combat balance for Project Volo (Burnwillow expansion).

Test Scenario: Tier 0 Player vs Rot-Beetle (baseline difficulty)

Author: Codex Playtester
Version: 1.0.0
Date: 2026-02-06
"""

import random
import statistics
from dataclasses import dataclass, field
from typing import List, Tuple
from enum import Enum


class CombatResult(Enum):
    PLAYER_WIN = "PLAYER_WIN"
    PLAYER_LOSS = "PLAYER_LOSS"


@dataclass
class CombatStats:
    """Metrics tracked per combat iteration."""
    result: CombatResult
    rounds: int
    player_hp_remaining: int
    total_damage_dealt: int
    total_damage_taken: int
    hits: int
    misses: int


@dataclass
class Combatant:
    """Base combatant with HP, damage, and defense."""
    name: str
    max_hp: int
    hp: int
    damage: int
    dr: int = 0
    defense_dc: int = 10

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: int) -> int:
        """Apply damage after DR. Returns actual damage taken."""
        actual_damage = max(0, damage - self.dr)
        self.hp -= actual_damage
        return actual_damage

    def reset(self):
        """Reset HP to max for new simulation."""
        self.hp = self.max_hp


@dataclass
class Player(Combatant):
    """Player with dice pool and stat modifier."""
    dice_count: int = 2
    dice_sides: int = 6
    stat_modifier: int = 1

    def attack_roll(self) -> Tuple[int, List[int]]:
        """Roll attack dice + modifier. Returns (total, individual_dice)."""
        dice_results = [random.randint(1, self.dice_sides) for _ in range(self.dice_count)]
        total = sum(dice_results) + self.stat_modifier
        return total, dice_results


@dataclass
class Enemy(Combatant):
    """Enemy with fixed or dice-based damage."""
    pass


def simulate_combat(player: Player, enemy: Enemy, ambush: bool = False, verbose: bool = False) -> CombatStats:
    """
    Simulate a single combat encounter.

    Args:
        player: Player combatant
        enemy: Enemy combatant
        ambush: If True, player gets a free attack before combat starts
        verbose: If True, print round-by-round details

    Returns:
        CombatStats object with metrics
    """
    # Reset combatants
    player.reset()
    enemy.reset()

    rounds = 0
    hits = 0
    misses = 0
    total_damage_dealt = 0
    total_damage_taken = 0

    # Ambush round (free attack)
    if ambush:
        attack_total, dice = player.attack_roll()
        if attack_total >= enemy.defense_dc:
            damage = enemy.take_damage(player.damage)
            total_damage_dealt += damage
            hits += 1
            if verbose:
                print(f"  [AMBUSH] Player rolls {dice} + {player.stat_modifier} = {attack_total} vs DC {enemy.defense_dc} → HIT! {damage} damage dealt.")
        else:
            misses += 1
            if verbose:
                print(f"  [AMBUSH] Player rolls {dice} + {player.stat_modifier} = {attack_total} vs DC {enemy.defense_dc} → MISS!")

    # Main combat loop
    while player.is_alive() and enemy.is_alive():
        rounds += 1

        if verbose:
            print(f"\n  Round {rounds}:")

        # Player turn
        attack_total, dice = player.attack_roll()
        if attack_total >= enemy.defense_dc:
            damage = enemy.take_damage(player.damage)
            total_damage_dealt += damage
            hits += 1
            if verbose:
                print(f"    Player rolls {dice} + {player.stat_modifier} = {attack_total} vs DC {enemy.defense_dc} → HIT! {damage} damage dealt. Enemy HP: {enemy.hp}/{enemy.max_hp}")
        else:
            misses += 1
            if verbose:
                print(f"    Player rolls {dice} + {player.stat_modifier} = {attack_total} vs DC {enemy.defense_dc} → MISS!")

        # Check if enemy died
        if not enemy.is_alive():
            if verbose:
                print(f"    Enemy defeated!")
            break

        # Enemy turn (auto-hit simplified model, or could add player defense DC)
        damage_taken = player.take_damage(enemy.damage)
        total_damage_taken += damage_taken
        if verbose:
            print(f"    Enemy attacks → {damage_taken} damage dealt (after DR). Player HP: {player.hp}/{player.max_hp}")

        # Check if player died
        if not player.is_alive():
            if verbose:
                print(f"    Player defeated!")
            break

    # Determine result
    if player.is_alive():
        result = CombatResult.PLAYER_WIN
    else:
        result = CombatResult.PLAYER_LOSS

    return CombatStats(
        result=result,
        rounds=rounds,
        player_hp_remaining=max(0, player.hp),
        total_damage_dealt=total_damage_dealt,
        total_damage_taken=total_damage_taken,
        hits=hits,
        misses=misses
    )


def run_simulation(iterations: int = 100, ambush: bool = False, verbose: bool = False) -> List[CombatStats]:
    """
    Run multiple combat simulations and collect stats.

    Args:
        iterations: Number of combats to simulate
        ambush: If True, all combats start with player ambush
        verbose: If True, print each combat in detail

    Returns:
        List of CombatStats for analysis
    """
    # Define combatants per GDD v1.0
    player = Player(
        name="Tier 0 Adventurer",
        max_hp=10,
        hp=10,
        damage=3,  # Simple weapon
        dr=1,      # Padded Jerkin
        defense_dc=10,  # Placeholder (not used in this sim, enemy auto-hits)
        dice_count=2,
        dice_sides=6,
        stat_modifier=1
    )

    enemy = Enemy(
        name="Rot-Beetle",
        max_hp=4,
        hp=4,
        damage=2,  # Fixed damage
        dr=0,
        defense_dc=8
    )

    results = []

    for i in range(iterations):
        if verbose:
            print(f"\n{'='*60}")
            print(f"Combat #{i+1}")
            print(f"{'='*60}")

        stats = simulate_combat(player, enemy, ambush=ambush, verbose=verbose)
        results.append(stats)

        if verbose:
            print(f"\nResult: {stats.result.value} in {stats.rounds} rounds")
            print(f"Player HP remaining: {stats.player_hp_remaining}")

    return results


def analyze_results(results: List[CombatStats], ambush: bool = False) -> None:
    """
    Analyze simulation results and print formatted report.

    Args:
        results: List of CombatStats from simulation
        ambush: Whether this was an ambush simulation
    """
    total = len(results)
    wins = [r for r in results if r.result == CombatResult.PLAYER_WIN]
    losses = [r for r in results if r.result == CombatResult.PLAYER_LOSS]

    win_rate = (len(wins) / total) * 100
    loss_rate = (len(losses) / total) * 100

    # Win metrics
    if wins:
        avg_rounds_to_kill = statistics.mean([r.rounds for r in wins])
        avg_hp_remaining = statistics.mean([r.player_hp_remaining for r in wins])
        min_hp_remaining = min([r.player_hp_remaining for r in wins])
        max_hp_remaining = max([r.player_hp_remaining for r in wins])
    else:
        avg_rounds_to_kill = 0
        avg_hp_remaining = 0
        min_hp_remaining = 0
        max_hp_remaining = 0

    # Loss metrics
    if losses:
        avg_rounds_survived = statistics.mean([r.rounds for r in losses])
    else:
        avg_rounds_survived = 0

    # Death Spiral Risk Assessment
    if win_rate < 60:
        risk = "HIGH"
        risk_color = "🔴"
    elif win_rate < 80:
        risk = "MEDIUM"
        risk_color = "🟡"
    else:
        risk = "LOW"
        risk_color = "🟢"

    # All combats metrics
    avg_rounds_all = statistics.mean([r.rounds for r in results])
    avg_damage_dealt = statistics.mean([r.total_damage_dealt for r in results])
    avg_damage_taken = statistics.mean([r.total_damage_taken for r in results])
    avg_hits = statistics.mean([r.hits for r in results])
    avg_misses = statistics.mean([r.misses for r in results])
    hit_rate = (avg_hits / (avg_hits + avg_misses)) * 100 if (avg_hits + avg_misses) > 0 else 0

    # Print report
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║              COMBAT SIMULATION: THE GRINDER                          ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")

    if ambush:
        print("║  Scenario: Tier 0 (2d6+1, 3 dmg) vs Rot-Beetle (DC 8, 4 HP) + AMBUSH║")
    else:
        print("║  Scenario: Tier 0 (2d6+1, 3 dmg) vs Rot-Beetle (DC 8, 4 HP)          ║")

    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Iterations:              {total:>5}                                       ║")
    print(f"║  Win Rate:                {win_rate:>5.1f}%  ({len(wins)}/{total})                       ║")
    print(f"║  Loss Rate:               {loss_rate:>5.1f}%  ({len(losses)}/{total})                        ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  VICTORY METRICS (when player wins)                                 ║")
    print(f"║    Avg Rounds to Kill:    {avg_rounds_to_kill:>5.2f}                                       ║")
    print(f"║    Avg HP Remaining:      {avg_hp_remaining:>5.2f} / 10                                   ║")
    print(f"║    Min HP Remaining:      {min_hp_remaining:>5} / 10                                      ║")
    print(f"║    Max HP Remaining:      {max_hp_remaining:>5} / 10                                      ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  DEFEAT METRICS (when player loses)                                 ║")
    print(f"║    Avg Rounds Survived:   {avg_rounds_survived:>5.2f}                                       ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  COMBAT EFFICIENCY (all battles)                                    ║")
    print(f"║    Avg Rounds per Combat: {avg_rounds_all:>5.2f}                                       ║")
    print(f"║    Avg Damage Dealt:      {avg_damage_dealt:>5.2f}                                       ║")
    print(f"║    Avg Damage Taken:      {avg_damage_taken:>5.2f}                                       ║")
    print(f"║    Hit Rate:              {hit_rate:>5.1f}%                                       ║")
    print(f"║    Avg Hits:              {avg_hits:>5.2f}                                       ║")
    print(f"║    Avg Misses:            {avg_misses:>5.2f}                                       ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  DEATH SPIRAL RISK:       {risk_color} {risk:<48} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  RISK CRITERIA:                                                      ║")
    print("║    HIGH   (Win Rate < 60%):  Player loses HP faster than kill rate   ║")
    print("║    MEDIUM (Win Rate 60-80%): Balanced but risky                      ║")
    print("║    LOW    (Win Rate > 80%):  Player dominates baseline encounter     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()


def main():
    """Run all simulations and generate reports."""
    print("\n" + "="*70)
    print("PROJECT VOLO: BURNWILLOW COMBAT SIMULATOR")
    print("The Grinder - Death Spiral Stress Test")
    print("="*70)

    # Simulation 1: Standard Combat (no ambush)
    print("\n[TEST 1] Running 100 iterations: Standard Combat...")
    results_standard = run_simulation(iterations=100, ambush=False, verbose=False)
    analyze_results(results_standard, ambush=False)

    # Simulation 2: Ambush Advantage
    print("\n[TEST 2] Running 100 iterations: Ambush Advantage...")
    results_ambush = run_simulation(iterations=100, ambush=True, verbose=False)
    analyze_results(results_ambush, ambush=True)

    # Comparison
    win_rate_standard = (len([r for r in results_standard if r.result == CombatResult.PLAYER_WIN]) / len(results_standard)) * 100
    win_rate_ambush = (len([r for r in results_ambush if r.result == CombatResult.PLAYER_WIN]) / len(results_ambush)) * 100
    ambush_delta = win_rate_ambush - win_rate_standard

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║                     AMBUSH ADVANTAGE ANALYSIS                        ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Standard Combat Win Rate:    {win_rate_standard:>5.1f}%                               ║")
    print(f"║  Ambush Combat Win Rate:      {win_rate_ambush:>5.1f}%                               ║")
    print(f"║  Ambush Advantage:            +{ambush_delta:>4.1f}%                               ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")

    if ambush_delta >= 15:
        verdict = "CRITICAL - Ambush is game-changing"
        verdict_color = "🔴"
    elif ambush_delta >= 10:
        verdict = "SIGNIFICANT - Ambush provides major advantage"
        verdict_color = "🟡"
    elif ambush_delta >= 5:
        verdict = "MODERATE - Ambush helps but not dominant"
        verdict_color = "🟢"
    else:
        verdict = "MINIMAL - Ambush has little impact"
        verdict_color = "⚪"

    print(f"║  Verdict: {verdict_color} {verdict:<50} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    # Sample verbose combat
    print("\n[SAMPLE COMBAT] Running single verbose combat for inspection...")
    print("="*70)
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
    enemy = Enemy(
        name="Rot-Beetle",
        max_hp=4,
        hp=4,
        damage=2,
        dr=0,
        defense_dc=8
    )
    simulate_combat(player, enemy, ambush=False, verbose=True)
    print("="*70)
    print("\n[SIMULATION COMPLETE]")
    print("\nRecommendations:")
    print("- Review win rates against Death Spiral thresholds")
    print("- If HIGH risk: Consider reducing enemy damage or increasing player DR")
    print("- If LOW risk: Consider adding enemy special abilities or increasing DC")
    print("- Ambush advantage should be 10-15% to reward scouting/stealth")
    print("\nNext Steps:")
    print("- Test against Tier 1 enemies (Rust-Maw, Feral Hound)")
    print("- Test edge cases: Player at 1 HP, enemy at 1 HP")
    print("- Test consecutive combats (resource attrition simulation)")
    print()


if __name__ == "__main__":
    main()

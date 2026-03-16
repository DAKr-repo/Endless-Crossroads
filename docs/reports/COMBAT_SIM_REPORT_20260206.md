# Combat Simulation Report: The Grinder
**Date:** 2026-02-06
**Tester:** Codex Playtester
**System:** Burnwillow Combat (GDD v1.0)
**Test Build:** `/home/pi/Projects/claude_sandbox/Codex/burnwillow_combat_sim.py`

---

## Executive Summary

**VERDICT: 🔴 CRITICAL BALANCE ISSUE - Rot-Beetle is trivially easy**

The Tier 0 baseline enemy (Rot-Beetle) was defeated in **100% of simulations** with an average of **7.5 HP remaining** (out of 10). This indicates the "Death Spiral" risk is inverted—the **player dominates too easily**, removing challenge and tension from early-game encounters.

---

## Test Scenario

**Player Stats (Tier 0 Starter):**
- Dice Pool: 2d6 + 1 (Might modifier)
- HP: 10
- DR: 1 (Padded Jerkin)
- Damage: 3 (Simple weapon)

**Enemy Stats (Rot-Beetle):**
- Defense DC: 8
- HP: 4
- Damage: 2 (reduced to 1 after player DR)
- Special: Skitter (not applicable in melee)

---

## Results: Standard Combat (100 iterations)

| Metric | Value |
|--------|-------|
| **Win Rate** | 100.0% (100/100) |
| **Loss Rate** | 0.0% (0/100) |
| **Avg Rounds to Kill** | 3.45 |
| **Avg HP Remaining** | 7.55 / 10 |
| **Min HP Remaining** | 3 / 10 |
| **Max HP Remaining** | 9 / 10 |
| **Hit Rate** | 58.0% |
| **Avg Damage Dealt** | 6.0 |
| **Avg Damage Taken** | 2.45 |
| **Death Spiral Risk** | 🟢 LOW (but inverted—too safe) |

---

## Results: Ambush Combat (100 iterations)

| Metric | Value |
|--------|-------|
| **Win Rate** | 100.0% (100/100) |
| **Avg Rounds to Kill** | 2.30 |
| **Avg HP Remaining** | 8.70 / 10 |
| **Avg Damage Taken** | 1.30 |
| **Ambush Advantage** | +0.0% win rate (already 100%) |
| **Verdict** | ⚪ MINIMAL - Ambush has little impact |

**Analysis:** Since the player already wins 100% of the time, ambush only reduces the time to kill by ~1 round and saves ~1 HP. This makes ambush/stealth mechanics feel unrewarding.

---

## Critical Issues Identified

### 1. Rot-Beetle Cannot Kill the Player
- **Player effective HP:** 10 HP with 1 DR = survives 10 hits
- **Beetle kills in:** 2 hits (6 damage total)
- **Player kills in:** 2 hits on average (4 HP / 3 damage = 1.33 hits)
- **Problem:** Player has a 58% hit rate but only needs to land 2 hits. Beetle cannot land 10 hits before dying.

### 2. Defense DC 8 is Too Low
- **Player roll:** 2d6 + 1 = 3 to 13 range
- **Average roll:** 8 (7 from dice + 1 modifier)
- **Hit probability vs DC 8:** ~58% (16 ways to roll 7+ on 2d6 out of 36)
- **Recommendation:** Increase DC to 9 or 10 to reduce hit rate to 40-50%

### 3. Beetle HP is Too Low
- **Current HP:** 4
- **Overkill factor:** Player deals 3 damage per hit, killing in 2 hits (6 damage total)
- **Recommendation:** Increase HP to 6 to require 2 hits without overkill, or add 1 DR to absorb some damage

### 4. Beetle Damage is Too Low
- **Current damage:** 2 raw → 1 after player DR
- **Required hits to kill player:** 10 hits
- **Actual hits landed:** ~3.45 (combat ends before 10 hits possible)
- **Recommendation:** Increase damage to 3 (2 after DR) or add special ability (poison, armor shred)

### 5. Ambush Advantage is Meaningless
- **Expected behavior:** Ambush should increase win rate by 10-15%
- **Actual behavior:** Win rate already 100%, ambush only saves 1 round
- **Root cause:** Baseline combat is too easy, removing tactical value of scouting/stealth
- **Recommendation:** Increase enemy difficulty so ambush becomes a meaningful tactical choice

---

## Sample Combat Log (Verbose)

```
Round 1:
  Player rolls [2, 4] + 1 = 7 vs DC 8 → MISS!
  Enemy attacks → 1 damage dealt (after DR). Player HP: 9/10

Round 2:
  Player rolls [4, 2] + 1 = 7 vs DC 8 → MISS!
  Enemy attacks → 1 damage dealt (after DR). Player HP: 8/10

Round 3:
  Player rolls [3, 5] + 1 = 9 vs DC 8 → HIT! 3 damage dealt. Enemy HP: 1/4
  Enemy attacks → 1 damage dealt (after DR). Player HP: 7/10

Round 4:
  Player rolls [1, 1] + 1 = 3 vs DC 8 → MISS!
  Enemy attacks → 1 damage dealt (after DR). Player HP: 6/10

Round 5:
  Player rolls [6, 6] + 1 = 13 vs DC 8 → HIT! 3 damage dealt. Enemy HP: -2/4
  Enemy defeated!
```

**Observation:** Even with unlucky rolls (two misses, double 1s), the player still wins comfortably with 6/10 HP remaining.

---

## Recommendations

### Immediate Fixes (Tier 0 Balance)

**Option A: Buff Rot-Beetle (Conservative)**
- Increase DC from 8 → 9 (reduces player hit rate to ~50%)
- Increase HP from 4 → 6 (requires consistent 2 hits)
- Increase damage from 2 → 3 (2 after DR, kills player in 5 hits)
- **Expected Win Rate:** 75-85% (medium risk)

**Option B: Buff Rot-Beetle (Aggressive)**
- Increase DC from 8 → 10 (reduces player hit rate to ~40%)
- Increase HP from 4 → 6
- Increase damage from 2 → 3
- Add special: "Acid Spray" (on hit, apply -1 DR for 2 rounds)
- **Expected Win Rate:** 60-70% (medium-high risk, rewards tactical play)

**Option C: Nerf Player (Alternative)**
- Reduce starting DR from 1 → 0 (make armor a meaningful upgrade)
- Reduce starting HP from 10 → 8
- Keep weapon damage at 3
- **Expected Win Rate:** 70-80% (keeps challenge without changing enemy design)

### Long-Term Design Changes

1. **Add Tier 0.5 "Tutorial" Enemy**
   - DC 7, 3 HP, 1 damage
   - Guaranteed win (95%+) for player confidence
   - Rot-Beetle becomes "first real fight"

2. **Implement Wound System**
   - At 50% HP (5/10), apply -1 to attack rolls (Death Spiral mechanic)
   - At 25% HP (2-3/10), apply -2 to attack rolls
   - Makes late-fight recovery harder, increases tension

3. **Add Consumable Healing**
   - Healing Salve (restore 1d6 HP, 1 per encounter)
   - Adds tactical depth (heal now vs save for later)
   - Increases survivability without trivializing combat

4. **Rebalance Ambush**
   - Ambush = free attack + advantage on first round (+1d6 to dice pool)
   - Makes scouting/stealth mechanically valuable
   - Target: 10-15% win rate increase vs standard combat

---

## Next Steps

1. **Immediate:** Run simulation with Option A (conservative buff) and verify win rate drops to 75-85%
2. **Short-term:** Test Tier 1 enemies (Rust-Maw, Feral Hound) to ensure difficulty curve
3. **Long-term:** Implement consecutive combat simulation (resource attrition over 3-5 fights)
4. **Edge cases:** Test player at 1 HP, enemy at 1 HP, multiple enemies vs single player

---

## Files Created

- `/home/pi/Projects/claude_sandbox/Codex/burnwillow_combat_sim.py` (Grinder test harness)
- `/home/pi/Projects/claude_sandbox/Codex/COMBAT_SIM_REPORT_20260206.md` (This document)

---

**Approval Required:**
- @Designer: Confirm enemy buff direction (Option A vs B vs C)
- @Mechanic: Implement chosen balance changes in `codex_combat_engine.py`
- @Architect: Review Death Spiral mechanics and wound system design

**Status:** 🔴 BLOCKING - Cannot ship Tier 0 combat with 100% player win rate

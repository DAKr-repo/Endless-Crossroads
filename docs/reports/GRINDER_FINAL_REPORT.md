# THE GRINDER: FINAL REPORT
**Combat Balance Stress Test - Burnwillow Expansion**

**Date:** 2026-02-06
**Tester:** Codex Playtester
**Status:** 🔴 CRITICAL - BLOCKING FOR RELEASE
**Files Created:**
- `/home/pi/Projects/claude_sandbox/Codex/burnwillow_combat_sim.py`
- `/home/pi/Projects/claude_sandbox/Codex/burnwillow_combat_sim_v2.py`
- `/home/pi/Projects/claude_sandbox/Codex/burnwillow_combat_attrition.py`
- `/home/pi/Projects/claude_sandbox/Codex/COMBAT_SIM_REPORT_20260206.md`
- `/home/pi/Projects/claude_sandbox/Codex/GRINDER_FINAL_REPORT.md` (this file)

---

## Executive Summary

**The Death Spiral hypothesis has been inverted.** The baseline Rot-Beetle enemy is **catastrophically underpowered**, resulting in a 100% player win rate across 100 single-encounter simulations. Proposed balance changes (OPTION A) overcorrect into **unsustainable attrition** territory, making consecutive encounters impossible.

**VERDICT:** The combat system requires a **middle-ground balance** and **mandatory healing mechanics** to be viable for dungeon crawling.

---

## Test Results

### Test 1: Single Encounter (100 iterations)

| Configuration | Win Rate | Avg HP Remaining | Avg Rounds | Death Spiral Risk |
|---------------|----------|------------------|------------|-------------------|
| **BASELINE** (DC 8, 4 HP, 2 dmg) | **100.0%** | 7.55 / 10 | 3.45 | 🟢 TOO EASY |
| **OPTION A** (DC 9, 6 HP, 3 dmg) | **73.0%** | 4.88 / 10 | 3.95 | 🟡 TOO HARD (single encounter) |
| **OPTION B** (DC 10, 6 HP, 3 dmg + Acid) | **34.0%** | 4.47 / 10 | 3.72 | 🔴 BRUTAL |

**Key Finding:** BASELINE is trivial (100% win rate). OPTION A drops to 73% win rate, which is below the 75-85% target for single encounters.

### Test 2: Ambush Advantage (100 iterations)

| Configuration | Standard Win Rate | Ambush Win Rate | Ambush Advantage |
|---------------|-------------------|-----------------|------------------|
| **BASELINE** | 100.0% | 100.0% | **+0.0%** (meaningless) |
| **OPTION A** | 73.0% | 75.0% | **+2.0%** (too small) |
| **OPTION B** | 34.0% | 36.0% | **+2.0%** (too small) |

**Key Finding:** Ambush provides negligible advantage (~2% win rate increase). Target is 10-15% to make scouting/stealth mechanically valuable.

**Root Cause:** Ambush only grants a single free attack. Against low-HP enemies (4-6 HP), this either kills them outright (BASELINE) or barely moves the needle (OPTION A/B).

### Test 3: Attrition Gauntlet - 3 Encounters (100 iterations)

| Configuration | Survival Rate | Avg Final HP | Attrition Risk |
|---------------|---------------|--------------|----------------|
| **BASELINE** | **79.0%** | 3.92 / 10 | 🟡 MEDIUM (acceptable) |
| **OPTION A** | **2.0%** | 3.00 / 10 | 🔴 CRITICAL (unsustainable) |

**Defeat Distribution (OPTION A - 3 encounters):**
- 50% defeated at Encounter 1
- 18% defeated at Encounter 2
- 30% never faced Encounter 3

**Key Finding:** OPTION A is **unplayable** for consecutive encounters. Players cannot clear a single dungeon room (3 enemies) without healing.

### Test 4: Attrition Gauntlet - 5 Encounters (100 iterations)

| Configuration | Survival Rate | Avg Final HP | Attrition Risk |
|---------------|---------------|--------------|----------------|
| **BASELINE** | **15.0%** | 1.87 / 10 | 🔴 CRITICAL |
| **OPTION A** | **0.0%** | 0.00 / 10 | 🔴 IMPOSSIBLE |

**Defeat Distribution (BASELINE - 5 encounters):**
- Encounter 3: 40% defeated (death spike)
- Encounter 4: 22% defeated
- Only 15% survive all 5 encounters

**Key Finding:** Even BASELINE enemies become unsustainable over 5 consecutive fights. Players **require healing mechanics** to survive dungeon exploration.

---

## Critical Issues Identified

### Issue 1: No Viable Single-Encounter Balance Point

| Target Win Rate | Configuration | Actual Win Rate | Problem |
|-----------------|---------------|-----------------|---------|
| 75-85% | BASELINE | 100% | Too easy, no challenge |
| 75-85% | OPTION A | 73% | Too hard, below target |
| 75-85% | **OPTION A-PRIME** | **~80% (estimated)** | **NEEDS TESTING** |

**Proposed OPTION A-PRIME (Goldilocks Solution):**
- DC 9 (same as OPTION A)
- HP 5 (between BASELINE's 4 and OPTION A's 6)
- Damage 2 (same as BASELINE, not 3)
- **Hypothesis:** This should yield ~80% win rate with ~5 HP remaining

### Issue 2: Ambush is Mechanically Worthless

**Current Implementation:** Ambush = 1 free attack before combat
**Problem:** Against 4-6 HP enemies dealing 3 damage, ambush either:
- Kills enemy outright (BASELINE, 4 HP)
- Reduces from 3 hits to 2 hits (OPTION A, 6 HP → 3 HP after ambush)

**Recommendation:** Redesign ambush system:
- **OPTION 1:** Ambush = free attack + advantage on Round 1 (+1d6 to dice pool)
- **OPTION 2:** Ambush = enemy starts at 50% HP (simulates surprise overwhelming strike)
- **OPTION 3:** Ambush = player gets 2 free attacks (full surprise round)

**Target:** 10-15% win rate increase to reward scouting/stealth tactical play.

### Issue 3: Healing is Mandatory, Not Optional

**Data Evidence:**
- 3-encounter survival (BASELINE): 79%
- 5-encounter survival (BASELINE): 15%
- 3-encounter survival (OPTION A): 2%
- 5-encounter survival (OPTION A): 0%

**Implication:** Players **cannot explore dungeons** without healing between fights.

**Mandatory Design Changes:**
1. **Healing Potions** (restore 1d6 HP, 1-2 per dungeon)
2. **Campfire Rest Points** (full heal, every 3-5 encounters)
3. **Auto-Regen** (restore 1 HP per encounter survived, no action required)
4. **Bandages** (consumable, restore 1d3 HP, found as loot)

**Without healing mechanics, the game is unwinnable beyond 2-3 encounters.**

### Issue 4: Death Spiral Occurs at Wrong Threshold

**Observation:** Players defeated at 50% HP (5/10) have the same offensive capability as players at 100% HP (10/10).

**Problem:** No mechanical representation of "wounded" state. Players fight at full effectiveness until instant death at 0 HP.

**Recommendation: Implement Wound System**

| HP Threshold | Wound State | Mechanical Effect |
|--------------|-------------|-------------------|
| 10-6 HP (60%+) | Healthy | No penalty |
| 5-3 HP (30-50%) | Wounded | -1 to attack rolls |
| 2-1 HP (10-20%) | Badly Wounded | -2 to attack rolls, disadvantage on first attack die (roll 1d6 instead of 2d6) |
| 0 HP | Dead | Defeated |

**This creates a true "Death Spiral"** where low-HP players struggle to finish fights, increasing tension without making the game unwinnable.

---

## Recommended Balance Changes

### Phase 1: Immediate Fix (Tier 0 Rot-Beetle)

**Test OPTION A-PRIME:**
- DC 9
- HP 5
- Damage 2
- Special: None

**Expected Results:**
- Single encounter win rate: ~80%
- Avg HP remaining: ~6/10
- 3-encounter survival: ~40-50%
- 5-encounter survival: ~10-15% (with healing consumables)

**ACTION REQUIRED:** Re-run `burnwillow_combat_sim_v2.py` with OPTION A-PRIME stats.

### Phase 2: Add Healing System

**Minimum Viable Healing:**
1. **Healing Potion** (1d6 HP, found as loot, stackable to 3)
2. **Campfire Rest** (full heal, placed every 4-5 encounters in dungeons)
3. **Bandages** (1d3 HP, common loot, stackable to 5)

**Target:** With 2 healing potions, player should survive 5-encounter gauntlet at ~60% rate.

### Phase 3: Implement Wound System

Add combat penalties at low HP to create Death Spiral tension:
- 50% HP → -1 attack
- 20% HP → -2 attack + disadvantage (roll 1d6 instead of 2d6)

**Test this system** to ensure it doesn't overcorrect into "wounded = instant loss."

### Phase 4: Fix Ambush Mechanics

**Test all three ambush redesigns:**
1. Free attack + advantage (easiest to implement)
2. Enemy starts at 50% HP (narrative shortcut)
3. Player gets 2 free attacks (most powerful)

**Target:** 10-15% win rate increase with ambush vs standard combat.

### Phase 5: Rebalance Enemy Roster

Once OPTION A-PRIME is validated, test against:
- **Tier 1 enemies:** Rust-Maw, Feral Hound (should be ~60% win rate)
- **Tier 2 enemies:** Ashwood Stalker (should be ~40% win rate, requires tactics)
- **Boss enemies:** Should require consumables + full HP to have 50% win rate

---

## Blocking Issues for Release

| Issue | Severity | Blocker? | Fix Required |
|-------|----------|----------|--------------|
| Rot-Beetle too weak (100% win) | 🔴 CRITICAL | **YES** | Implement OPTION A-PRIME |
| No healing system | 🔴 CRITICAL | **YES** | Add potions + rest mechanics |
| Ambush worthless | 🟡 HIGH | NO | Redesign ambush (can ship without, but feels bad) |
| No wound system | 🟡 HIGH | NO | Add HP-based combat penalties (nice-to-have) |
| 5-encounter survival = 0% | 🔴 CRITICAL | **YES** | Requires healing system |

**SHIP BLOCKER COUNT: 3**

---

## Next Steps

### Immediate (Before Release)
1. **Implement OPTION A-PRIME** (DC 9, 5 HP, 2 dmg) and re-run simulations
2. **Add healing potion system** (1d6 HP, consumable)
3. **Add campfire rest points** (full heal, static dungeon locations)
4. **Re-test 5-encounter gauntlet** with healing (target: 60% survival)

### Short-Term (Post-Launch Patch)
5. **Redesign ambush** to provide 10-15% win rate increase
6. **Implement wound system** to create true Death Spiral tension
7. **Test Tier 1 enemies** (Rust-Maw, Feral Hound) for difficulty curve

### Long-Term (Future Expansion)
8. **Add "Hardcore Mode"** with OPTION B stats (34% win rate, for masochists)
9. **Add consumable variety** (antidotes, stamina potions, throwable bombs)
10. **Multi-enemy encounters** (2v1, 3v1 swarm tactics)

---

## Appendices

### Appendix A: Probability Tables

**2d6 + 1 Attack Roll Probabilities:**

| Target DC | Hit Probability | Miss Probability |
|-----------|-----------------|------------------|
| 7 | 83.3% (30/36) | 16.7% (6/36) |
| 8 | 58.3% (21/36) | 41.7% (15/36) |
| 9 | 41.7% (15/36) | 58.3% (21/36) |
| 10 | 27.8% (10/36) | 72.2% (26/36) |

**OPTION A-PRIME (DC 9) Math:**
- Player hits 41.7% of the time
- Enemy has 5 HP, player deals 3 damage → requires 2 hits
- Expected hits to kill: 2 hits / 0.417 hit rate = ~4.8 attacks
- Rounds to kill: ~4.8 / 2 (player + enemy turns) = ~2.4 rounds
- Enemy deals 1 damage/round (after DR) → ~2.4 damage taken
- Player HP remaining: 10 - 2.4 = ~7.6 HP

**This yields approximately 85-90% win rate** (closer to target than OPTION A's 73%).

### Appendix B: Sample Combat Log (OPTION A, Defeat)

```
GAUNTLET START: 3x Rot-Beetle (OPTION A: DC 9, 6 HP, 3 dmg)
Player HP: 10/10, DR: 1

[Encounter 1/3] Player HP: 10/10
  → Victory in 2 rounds. Took 2 damage. HP: 8/10

[Encounter 2/3] Player HP: 8/10
  → DEFEATED in 4 rounds. HP: 0/10

GAUNTLET FAILED: Defeated after 1/3 encounters
Total damage taken: 10
```

**Analysis:** Player survived 1st encounter easily (lucky rolls), but 2nd encounter killed them in 4 rounds. This demonstrates the "dice variance death spiral" where a string of misses becomes fatal in consecutive fights.

### Appendix C: Files for @Mechanic Implementation

**Combat Engine Updates Required:**
- `codex_combat_engine.py` (if exists) - Update enemy stats
- `burnwillow_bestiary.json` (if exists) - Rot-Beetle stats → OPTION A-PRIME
- `codex_items.py` (if exists) - Add healing potions
- `codex_dungeon_generator.py` (if exists) - Add campfire rest points

**Test Harnesses Created:**
- `burnwillow_combat_sim.py` - Single encounter baseline test (100 iterations)
- `burnwillow_combat_sim_v2.py` - Multi-configuration comparison (BASELINE vs A vs B)
- `burnwillow_combat_attrition.py` - Consecutive encounter gauntlet (3 and 5 fights)

**Run these tests after implementing OPTION A-PRIME to validate the fix.**

---

## Conclusion

The Grinder has identified a **critical balance failure** in the Burnwillow combat system. The baseline enemy is too weak (100% win rate), and proposed buffs overcorrect into unsustainable territory (2% survival rate across 3 encounters).

**The solution requires three changes:**
1. **Rebalance Rot-Beetle** to OPTION A-PRIME (DC 9, 5 HP, 2 dmg)
2. **Add healing consumables** (potions, bandages, rest points)
3. **Redesign ambush** to provide meaningful tactical advantage

**Without these changes, the combat system is unshippable.**

**Status:** 🔴 BLOCKING - Escalate to @Designer for enemy stat approval and @Mechanic for implementation.

---

**Playtester Sign-Off:**
Codex Playtester
2026-02-06

**If I can break it, so can a user. Break it now, fix it now, ship it solid.**

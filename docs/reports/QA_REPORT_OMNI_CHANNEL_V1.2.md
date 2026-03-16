# QA REPORT: OMNI-CHANNEL PARITY — VERIFICATION AUDIT V1.2
## SCENARIO-V1.2 — The Nomad Seeker (Fix Verification)

**Date:** 2026-02-21
**Auditor:** @codex-playtester
**Scope:** Verify eradication of 7 Critical Blockers (WO-086) + 3 High Severity (WO-V24.1)
**Baseline:** QA_REPORT_OMNI_CHANNEL_PARITY.md (V1.0, 2026-02-20)
**Regression:** 196/196 tests pass (full suite)

---

## EXECUTIVE VERDICT

**ALL 10 FIXES VERIFIED. ERADICATION CONFIRMED.**

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| CB-01 | CRITICAL | Telegram format_legacy phantom import | FIXED |
| CB-02 | CRITICAL | Discord QUEST_SELECT start_game() guard | FIXED |
| CB-03 | CRITICAL | Ashburn loop `range(1, 6)` hardcoded | FIXED |
| CB-04 | CRITICAL | Ashburn display `DAY {day} of 5` | FIXED |
| CB-05 | CRITICAL | Ashburn breach `day == 3` hardcoded | FIXED |
| CB-06 | CRITICAL | Ashburn death screen `{day}/5` | FIXED |
| CB-07 | CRITICAL | Ashburn transition `day < 5` | FIXED |
| HIGH-01 | HIGH | Telegram `end_session()` AttributeError | FIXED |
| HIGH-02 | HIGH | Telegram `/crown` fails from MENU phase | FIXED |
| HIGH-03 | HIGH | ASHBURN_HEIR/LEGACY phases unrouted | FIXED |

---

## CRITICAL BLOCKER VERIFICATION

### TEST 1: CB-01 — Telegram Legacy Report Import

**Before:** `from codex_crown_module import LEGACY_TITLES` (phantom module, instant crash)
**After:** `from codex.games.crown.engine import LEGACY_TITLES`

```
Verification: python3 -c "from codex.games.crown.engine import LEGACY_TITLES; print(len(LEGACY_TITLES))"
Result: 15 entries — PASS
```

`LEGACY_TITLES` is a module-level dict in `codex/games/crown/engine.py` with 15 `(alignment, dominant_tag)` -> `{title, desc}` mappings. The import now resolves correctly. `format_legacy()` at `telegram_bot.py:175` can render campaign finales without crashing.

### TEST 2: CB-02 — Discord Quest Selection Guard Bypass

**Before:** `session.phase = Phase.MORNING` then `session.start_game()` which guards `phase != IDLE` -> instant error message
**After:** Inline response building that bypasses `start_game()` entirely

```
File: codex/bots/discord_bot.py (QUEST_SELECT handler)
Pattern: get_world_prompt() + get_morning_event() + quest metadata inline
CB-02 fix comment present: "# Bypass start_game() — it guards phase != IDLE (CB-02 fix)"
```

Verified with Siege (7-day) and Heist (3-day) archetypes: engine constructs correctly from `quest.to_world_state()`, response includes arc_length-aware text. **PASS.**

### TEST 3: CB-03 — Ashburn Loop Dynamism

**Before:** `for day in range(1, 6):`
**After:** `for day in range(1, engine.arc_length + 1):`

```
Verification: grep -n "range(1, 6)" codex_agent_main.py
Result: 0 matches — PASS
```

The Ashburn campaign loop now respects `engine.arc_length`. A Heist quest (3 days) will iterate 1-3; a Siege quest (7 days) will iterate 1-7.

### TEST 4: CB-04 — Ashburn Display String

**Before:** `f"DAY {day} of 5 - {region}"`
**After:** `f"DAY {day} of {engine.arc_length} - {region}"`

```
Verification: No "of 5" strings found in Ashburn display lines — PASS
```

### TEST 5: CB-05 — Dynamic Breach Day

**Before:** `elif day == 3: region = "THE BREACH"` and `if day == 3:` (Secret Witness)
**After:** `breach_day = max(1, round(engine.arc_length * engine.rest_config.get("breach_day_fraction", 0.6)))` then `day == breach_day`

```
Verification: breach_day calculation present, uses engine.rest_config — PASS
Heist (3-day): breach = max(1, round(3 * 0.6)) = 2
Siege (7-day): breach = max(1, round(7 * 0.6)) = 4
Standard (5-day): breach = max(1, round(5 * 0.6)) = 3 (backward compatible)
```

### TEST 6: CB-06 — Dynamic Death Screen

**Before:** `f"Days Survived: {day}/5"` and `f"5/5"`
**After:** `f"Days Survived: {day}/{engine.arc_length}"` and `f"{engine.arc_length}/{engine.arc_length}"`

```
Verification: No "/5" death screen references found — PASS
```

### TEST 7: CB-07 — Dynamic Transition Gate

**Before:** `if day < 5:`
**After:** `if day < engine.arc_length:`

```
Verification: No "day < 5" hardcoded references found — PASS
```

---

## HIGH SEVERITY VERIFICATION

### TEST 8: HIGH-01 — Telegram end_session() -> end_game()

**Before:** `session.end_session()` at telegram_bot.py:988 (method doesn't exist)
**After:** `session.end_game()` (correct method name)

```
Verification: 0 occurrences of "end_session()" in telegram_bot.py (excluding comments) — PASS
```

### TEST 9: HIGH-02 — Telegram /crown MENU Guard

**Before:** `if session.phase not in (Phase.IDLE, Phase.MENU):` on `/crown` and `/ashburn` commands — MENU phase skipped `end_game()`, then `start_game()` failed because `phase != IDLE`
**After:** `if session.phase != Phase.IDLE:` — MENU phase now correctly triggers `end_game()` reset

```
File: codex/bots/telegram_bot.py
  Line 734: if session.phase != Phase.IDLE:  (cmd_crown) — PASS
  Line 743: if session.phase != Phase.IDLE:  (cmd_ashburn) — PASS
  Line 863: if session.phase != Phase.IDLE:  (MENU play_crown handler) — PASS
  Line 888: if session.phase != Phase.IDLE:  (MENU play_ashburn handler) — PASS
```

Note: 6 other `not in (Phase.IDLE, Phase.MENU)` guards remain on `/prologue`, `/burnwillow`, `/dnd5e`, `/cosmere`, `/quest`, and `_on_map_update`. These are **correct** — they properly reset active sessions when launching non-Crown games. The bug was specific to Crown/Ashburn commands that called `start_game()` afterward.

### TEST 10: HIGH-03 — ASHBURN_HEIR/LEGACY Phase Routing

**Before:** Both Phase enums declared `ASHBURN_HEIR` and `ASHBURN_LEGACY` but neither bot routed messages to handlers. Sessions reaching these phases fell through to Mimir chat.

**After:** Full heir selection and legacy resolution flows wired in both bots.

#### Discord (`discord_bot.py`):

| Component | Location | Status |
|-----------|----------|--------|
| `cmd_ashburn()` shows Julian/Rowan selection | Lines 1699-1721 | WIRED |
| MENU `play_ashburn` handler | Lines 2464-2481 | WIRED |
| ASHBURN_HEIR handler in `on_message()` | Lines ~2581-2606 | WIRED |
| ASHBURN_LEGACY handler in `on_message()` | Lines ~2609-2640 | WIRED |
| `handle_allegiance()` duck-type legacy check | `hasattr(self.engine, 'generate_legacy_check')` | WIRED |

#### Telegram (`telegram_bot.py`):

| Component | Location | Status |
|-----------|----------|--------|
| `cmd_ashburn()` shows Julian/Rowan selection | Lines 740-755 | WIRED |
| MENU `play_ashburn` handler | Lines 884-905 | WIRED |
| ASHBURN_HEIR handler in `handle_message()` | Phase.ASHBURN_HEIR block | WIRED |
| ASHBURN_LEGACY handler in `handle_message()` | Phase.ASHBURN_LEGACY block | WIRED |
| `handle_allegiance()` duck-type legacy check | `hasattr(self.engine, 'generate_legacy_check')` | WIRED |

```
Verification: All 5 components confirmed present in both bots — PASS (10/10 sub-checks)
```

#### Ashburn Flow (both platforms):
1. `/ashburn` or MENU select -> Shows Julian/Rowan choice -> Phase.ASHBURN_HEIR
2. User picks "1" (Julian) or "2" (Rowan) -> `AshburnHeirEngine(heir_name=...)` created -> Phase.MORNING
3. Normal Crown loop with `handle_allegiance()` -> duck-type detects Ashburn engine
4. `generate_legacy_check()` fires (33% chance on rolls 5-6) -> Phase.ASHBURN_LEGACY
5. "1" (Obey) or "2" (Lie) -> `resolve_legacy_choice()` -> corruption tracked
6. `check_betrayal()` at corruption >= 5 -> game over or continue

---

## REGRESSION STATUS

```
PYTHONPATH=. pytest tests/ -v
196 passed in 3.00s

PYTHONPATH=. pytest tests/test_omni_parity.py -v
20 passed in 0.06s
```

---

## REMAINING ISSUES (from V1.0 report, NOT in scope for this verification)

### Still Open — High Severity:
- **HIGH-04**: Telegram Omni-Forge stub ("Coming Soon")
- **HIGH-05**: Engine `_council_dilemmas` not serialized in `to_dict()`

### Still Open — Medium Severity:
- **MED-01**: Quest morning events never wired into engine instance
- **MED-02**: Telegram welcome "Five days to the border" hardcoded
- **MED-03**: Tutorial content "5-day" references
- **MED-04**: Tarot cards absent from both bots
- **MED-05**: Telegram `main()` missing 3 commands
- **MED-06**: Infinite Short Rest exploit (no per-day counter)

### Still Open — Minor/Cosmetic:
- **MIN-01** through **MIN-05**: Comment/label "5-day" references

---

## NOMAD SEEKER SCENARIO — UPDATED STATUS

| Platform | Can Start Heist? | Can Short Rest? | Can View Legacy? | Day/Arc Correct? |
|----------|-----------------|-----------------|------------------|------------------|
| Terminal | YES | YES | YES | YES (Crown + Ashburn) |
| Discord  | **YES** (CB-02 fixed) | YES | YES | YES |
| Telegram | YES | YES | **YES** (CB-01 fixed) | YES |

**Cross-platform save/load remains structurally impossible** (documented in V1.0, out of scope for this sprint). The Nomad Seeker can now complete a full campaign on any single platform. Platform switching requires starting fresh.

---

*Report generated by @codex-playtester. 10/10 targeted fixes verified. 196/196 regression tests pass.*
*V1.0 residual: 2 High, 6 Medium, 5 Minor remain open for future sprints.*

# QA REPORT: OMNI-CHANNEL PARITY AUDIT
## SCENARIO-V1.1 — The Nomad Seeker (Behavioral Audit)

**Date:** 2026-02-20
**Auditor:** @codex-playtester
**Scope:** Cross-platform Crown & Crew campaign (Terminal → Discord → Telegram)
**Quest:** "The Grand Heist" (arc_length=3, slug=heist)
**Methodology:** Blind behavioral code trace — codebase treated as black box

---

## EXECUTIVE VERDICT

**SCENARIO STATUS: FAIL — NOT COMPLETABLE**

The Nomad Seeker cannot complete. Three crash-level bugs prevent the Telegram Legacy Report from rendering, the Discord quest selection from displaying a welcome message, and the cross-platform save/load mechanism does not exist. Additionally, 5 critical "Day X/5" hallucinations survive in the Ashburn campaign loop.

| Platform | Can Start Heist? | Can Short Rest? | Can View Legacy? | Day/Arc Correct? |
|----------|-----------------|-----------------|------------------|------------------|
| Terminal | YES | YES | YES | YES (Crown) / **NO (Ashburn)** |
| Discord  | **BROKEN** (error msg) | YES (if started via !crown) | YES | YES |
| Telegram | YES (via /quest) | YES | **CRASH** | YES (display) / **NO (welcome)** |

---

## CRITICAL BLOCKERS (7)

### CB-01 | Telegram Legacy Report Crash — `ModuleNotFoundError`
- **File:** `codex/bots/telegram_bot.py:175`
- **Code:** `from codex_crown_module import LEGACY_TITLES`
- **Impact:** `codex_crown_module` does not exist. Every campaign finale crashes with an unhandled exception. The game runs perfectly through Days 1-3 and dies the instant `format_legacy()` is called. No player has ever seen a Telegram Legacy Report.
- **Fix:** `from codex.games.crown.engine import LEGACY_TITLES`

### CB-02 | Discord QUEST_SELECT → start_game() Guard Mismatch
- **File:** `codex/bots/discord_bot.py:2567-2569`
- **Code:** Sets `session.phase = Phase.MORNING` then calls `session.start_game()` which guards `phase != IDLE`
- **Impact:** Selecting any quest archetype on Discord returns `"A game is already in progress."` instead of the world prompt. The engine IS correctly constructed — the player just can't see the welcome banner or morning event. The game is technically playable if you know to type `!travel`, but the UX is broken.
- **Fix:** Replace `start_game()` call with direct `format_morning()` output (matching Telegram's working pattern at line 918).

### CB-03 | Ashburn Loop: `range(1, 6)` Hardcoded
- **File:** `codex_agent_main.py:1167`
- **Code:** `for day in range(1, 6):`
- **Impact:** The Ashburn campaign ignores `engine.arc_length` entirely. It always plays exactly 5 days regardless of engine configuration. The Crown campaign at line 682 was correctly updated to `while engine.day <= engine.arc_length` — Ashburn was missed.

### CB-04 | Ashburn Display: `"DAY {day} of 5"` Hardcoded
- **File:** `codex_agent_main.py:1180`
- **Code:** `f"═══ DAY {day} of 5 — {region} ═══"`
- **Impact:** Player always sees "of 5" even if `arc_length != 5`. **Day X/5 hallucination.**

### CB-05 | Ashburn Breach: `day == 3` Hardcoded
- **File:** `codex_agent_main.py:1173, 1196`
- **Code:** `elif day == 3: region = "THE BREACH"` and `if day == 3:` (Secret Witness trigger)
- **Impact:** Breach always fires Day 3 instead of using `engine.is_breach_day()`. On a 7-day arc, breach would be Day 4 (60% mark) but fires Day 3 instead.

### CB-06 | Ashburn Death Screen: `{day}/5` Hardcoded
- **File:** `codex_agent_main.py:1419`
- **Code:** `f"Days Survived: {day}/5"`
- **Impact:** Death screen shows "/5" regardless of `arc_length`. **Day X/5 hallucination.**

### CB-07 | Ashburn Transition: `day < 5` Hardcoded
- **File:** `codex_agent_main.py:1430`
- **Code:** `if day < 5:`
- **Impact:** "Face your fate" prompt fires on Day 5 instead of the final day. On a 7-day arc, the wrong prompt shows on Days 5 and 6.

---

## HIGH SEVERITY (5)

### HIGH-01 | Telegram `end_session()` AttributeError
- **File:** `codex/bots/telegram_bot.py:988`
- **Code:** `session.end_session()` — method doesn't exist. Should be `session.end_game()`
- **Impact:** Every dungeon death via inline keyboard button crashes. Session becomes permanently stuck.

### HIGH-02 | Telegram `/crown` Fails from MENU Phase
- **File:** `codex/bots/telegram_bot.py:721-725, 841-845`
- **Code:** Guard `if session.phase not in (Phase.IDLE, Phase.MENU)` skips `end_game()` when in MENU, then `start_game()` returns error because `phase != IDLE`
- **Impact:** Selecting Crown & Crew from the main menu returns "A game is already in progress." Player cannot start a Crown game via the menu flow.
- **Fix:** Change guard to `if session.phase != Phase.IDLE:` so MENU triggers `end_game()` reset.

### HIGH-03 | ASHBURN_HEIR/ASHBURN_LEGACY Phases — No Handlers
- **File:** `codex/bots/discord_bot.py:281-282`, `codex/bots/telegram_bot.py:230-231`
- **Impact:** Both Phase enums declare these values but neither bot's message handler routes them. An Ashburn session reaching heir/legacy selection falls through to Mimir chat. Player is stuck.

### HIGH-04 | Telegram Omni-Forge: Stub Only
- **File:** `codex/bots/telegram_bot.py:835-838`
- **Code:** Returns `"Coming Soon."` with no phase transition
- **Impact:** Menu option #6 advertised but non-functional. Player input after selection falls to Mimir.

### HIGH-05 | Engine `_council_dilemmas` Not Serialized
- **File:** `codex/games/crown/engine.py` — `to_dict()` (line ~1155)
- **Impact:** `_council_dilemmas`, `quest_slug`, `quest_name`, `special_mechanics` are never written to the serialized dict. A cold load (without `world_state` kwarg) replaces Heist's 5 thematic dilemmas with 8 generic Crown & Crew dilemmas. Cross-platform save/load would lose quest identity.

---

## MEDIUM SEVERITY (6)

### MED-01 | Quest Morning Events Never Wired
- **File:** `codex/games/crown/engine.py` — `__post_init__()` and `get_morning_event()`
- **Impact:** All 7 quest archetypes define thematic morning events (Heist: safehouse patrol, Dwarvish locks, broadsheet, gold coin, Inside Man absence). `to_world_state()` emits them under `"morning_events"` key. `__post_init__()` never reads this key. `get_morning_event()` hardcodes the module-level `MORNING_EVENTS` list. Result: Heist players encounter wilderness road events instead of city heist events. Silent data loss across all quest archetypes.

### MED-02 | Telegram Welcome: "Five days to the border"
- **File:** `codex/bots/telegram_bot.py:464`
- **Code:** `"Five days to the border. Every choice shapes your soul."`
- **Impact:** Hardcoded flavor text. A Heist player (3-day arc) or Siege player (7-day arc) sees "Five days" regardless. **Day hallucination (cosmetic but misleading).**

### MED-03 | Tutorial Content: Multiple "5-day" References
- **File:** `codex/core/services/tutorial_content.py:66, 91, 1111, 1117, 1120-1132`
- **Impact:** Tutorial describes Crown & Crew as "A 5-day narrative card game" and "played over five in-game days." Wrong for quests with arc_length 3 or 7.

### MED-04 | Tarot Cards Absent from Both Bots
- **Files:** `codex/bots/discord_bot.py`, `codex/bots/telegram_bot.py`
- **Impact:** Terminal has 8 tarot injection points (Wolf at world prompt, Dead Tree at campfire, Moon at legacy, Sun Ring/Registry Key at dilemma). Both bots have zero. The campfire scene, allegiance dilemma, and finale lack their atmospheric framing on Discord/Telegram. Largest aesthetic discontinuity between platforms.

### MED-05 | Telegram `main()` Missing 3 Commands
- **File:** `codex/bots/telegram_bot.py:1105-1122`
- **Impact:** Standalone `python telegram_bot.py` testing path doesn't register `/crown`, `/ashburn`, `/quest` commands. Production path (`run_telegram_bot()`) is unaffected.

### MED-06 | Infinite Short Rest Exploit
- **File:** `codex/bots/discord_bot.py:1006-1038`
- **Impact:** `handle_rest("short")` returns to Phase.MORNING with no loop counter. Player can cycle COUNCIL → REST → MORNING → ... indefinitely, farming favorable sway bias events. While sway caps at ±3, it undermines narrative pacing.

---

## MINOR/COSMETIC (5)

### MIN-01 | `codex_agent_main.py:1440` — Comment "Survived all 5 days"
### MIN-02 | `codex/games/crown/engine.py:1293-1304` — `__main__` test uses `range(1, 6)`
### MIN-03 | `play_crown.py:113` — "classic 5-day campaign" menu label (correct for Prologue March)
### MIN-04 | `codex/games/crown/quests.py:492, 1094, 1296` — "Five days" in quest flavor text (matches those quests' arc_length=5, but fragile)
### MIN-05 | `codex_agent_main.py:636` — Docstring "5-Day Narrative Campaign" (stale after arc_length became dynamic)

---

## EVALUATION CRITERIA RESULTS

### 1. The Telegram Trap: Empty Shell?
**VERDICT: NOT an empty shell, but NOT production-ready.**

Telegram has a fully implemented 13-state state machine with real handlers for all Crown & Crew phases. Messages reach users via `reply_text()`. REST, QUEST_SELECT, and COUNCIL phases all function correctly. However, three crash bugs (CB-01 format_legacy import, HIGH-01 end_session typo, HIGH-02 /crown guard) prevent any campaign from completing. The bot is 90% functional — the last 10% is the part the player actually cares about (seeing the ending).

### 2. The Sub-Menu Gap: Did Options Disappear?
**VERDICT: PARTIAL PASS.**

| Option | Terminal | Discord | Telegram |
|--------|----------|---------|----------|
| Quest Archetype | YES | YES (but CB-02 breaks UX) | YES |
| REST (long/short/skip) | YES | YES | YES |
| Ashburn Heir/Legacy | YES | **NO** (HIGH-03: no handler) | **NO** (HIGH-03: no handler) |
| Omni-Forge | YES | YES | **NO** (HIGH-04: stub) |

REST options survive platform switching. Quest Archetype exists everywhere but is broken on Discord (CB-02). Ashburn sub-phases are declared but unrouted on both bots.

### 3. Visual Continuity: Tarot Carry-Over?
**VERDICT: FAIL.**

Zero tarot injections on Discord or Telegram (MED-04). Terminal has 8. The Wolf card (world prompt), Dead Tree (campfire), Moon (legacy), and Sun Ring/Registry Key (allegiance dilemma) are terminal-exclusive atmospheric elements. Both bots show bare text where Terminal shows framed tarot panels.

### 4. Day X/5 Hallucinations?
**VERDICT: 5 CRITICAL BLOCKERS in Ashburn (CB-03 through CB-07), 1 MEDIUM in Telegram welcome (MED-02), 1 MEDIUM in tutorials (MED-03).**

The Crown & Crew campaign on all three platforms correctly uses dynamic `arc_length`. The Ashburn campaign is entirely hardcoded to 5 days with `range(1, 6)`, `"DAY {day} of 5"`, `day == 3`, `{day}/5`, and `day < 5`.

---

## NOMAD SEEKER SCENARIO TRACE

### Step 1: Start Heist in Terminal, Play Day 1, Save and Exit
- **Quest selection:** `run_crown_crew_menu()` shows "Quest Archetype" option. Select Heist → `quest.to_world_state()` → engine constructed with `arc_length=3`. WORKS.
- **Day 1:** Loop enters `while engine.day <= 3`. Region = "THE WILDS" (day 1 < breach day 2). Morning event shown (generic, not Heist-themed — MED-01). Allegiance declared. Campfire. Council dilemma (Heist-themed, 5 pool). WORKS.
- **Save and Exit:** **BLOCKS.** There is no mid-campaign save mechanism in `run_crown_campaign()`. The butler `sync_session_to_file()` syncs session metadata only, not engine state. The only save path is the legacy report written at campaign end. **The Nomad Seeker cannot save mid-campaign.**

### Step 2: Load Save in Discord, Trigger Short Rest
- **Load:** **IMPOSSIBLE.** Discord has no `!load` command. No call to `CrownAndCrewEngine.from_dict()` exists anywhere in `discord_bot.py`. The only entry points are `!crown` (fresh), `!quest` (fresh from archetype), and `!prologue` (fresh from campaign context). Cross-platform terminal→Discord Crown handoff is structurally impossible.
- **Short Rest (if started fresh via !quest):** `handle_rest("short")` calls `engine.trigger_short_rest()` which does NOT advance the day. Phase returns to MORNING. Day stays the same. WORKS correctly in isolation.

### Step 3: Switch to Telegram, Verify Day Count, View Legacy at Day 3
- **Session transfer:** **IMPOSSIBLE.** Same as Discord — no load/resume mechanism. Sessions are in-memory only.
- **Day count (if started fresh via /quest):** All display sites use `engine.arc_length`. For Heist: "Day 1/3", "Day 2/3", "Day 3/3". CORRECT.
- **Legacy Report:** **CRASH.** `format_legacy()` imports from `codex_crown_module` which doesn't exist (CB-01). The player never sees the Legacy Report.

---

## CROSS-PLATFORM SAVE/LOAD — THE MISSING BRIDGE

The fundamental blocker for the Nomad Seeker scenario is that **no platform serializes Crown & Crew engine state to a shareable format during gameplay:**

| Platform | Mid-Campaign Save? | Load from File? | `to_dict()` Used? | `from_dict()` Used? |
|----------|--------------------|-----------------|--------------------|---------------------|
| Terminal | NO | NO (Prologue only) | NO | NO |
| Discord  | NO | NO | NO | NO |
| Telegram | NO | NO | NO | NO |

The engine's `to_dict()`/`from_dict()` round-trip is fully functional (20/20 tests pass in `test_omni_parity.py`) but is never called by any UI layer during gameplay. It exists as a capability without consumers.

---

## RECOMMENDED FIX PRIORITY

### Immediate (blocks any campaign completion):
1. **CB-01:** Fix `telegram_bot.py:175` import → `from codex.games.crown.engine import LEGACY_TITLES`
2. **CB-02:** Fix `discord_bot.py:2567-2569` → bypass `start_game()`, build response inline
3. **HIGH-01:** Fix `telegram_bot.py:988` → `session.end_game()`
4. **HIGH-02:** Fix `telegram_bot.py:721, 841` guard → `if session.phase != Phase.IDLE:`

### Next Sprint (Ashburn Day/5 hallucination sweep):
5. **CB-03 through CB-07:** Refactor `run_ashburn_campaign()` in `codex_agent_main.py` to use `engine.arc_length`, `engine.is_breach_day()`, and dynamic display strings.

### Platform Parity Sprint:
6. **MED-01:** Wire quest `morning_events` into engine instance field
7. **HIGH-05:** Serialize `_council_dilemmas` in `to_dict()`
8. **HIGH-03:** Implement ASHBURN_HEIR/LEGACY handlers in both bots
9. **MED-04:** Port tarot card rendering to Discord (embed) and Telegram (code block)
10. **MED-06:** Add short rest counter (max 1 per day cycle)

### Long-term (Nomad Seeker enablement):
11. Implement mid-campaign `!save`/`/save` for Crown & Crew across all platforms
12. Implement `!load`/`/load` consuming `engine.to_dict()` output
13. Shared save format (JSON) with platform-agnostic engine state

---

*Report generated by @codex-playtester. 7 Critical Blockers, 5 High, 6 Medium, 5 Minor.*
*Full scenario: FAIL. The Nomad Seeker cannot cross platforms.*

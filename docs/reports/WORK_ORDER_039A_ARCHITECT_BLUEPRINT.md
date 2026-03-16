# WORK ORDER #039-A: ASHBURN INTEGRATION BLUEPRINT
## ARCHITECT COMPONENT — STATE MACHINE DESIGN

**Blueprint Version:** 1.0
**Date:** 2026-02-03
**Architect:** @codex-architect
**Target Implementation:** @Mechanic

**Status:** READY FOR IMPLEMENTATION
**Risk Assessment:** LOW — Ashburn module is complete, this is UI integration only
**Thermal Impact:** LOW — Text-based loop, one LLM call per Legacy Check

---

## EXECUTIVE SUMMARY

This blueprint defines the integration logic for `ashburn_crew_module.py` (ALREADY IMPLEMENTED) into the `codex_agent_main.py` orchestrator. The Ashburn module is a complete, tested subclass of `CrownAndCrewEngine` that adds:

- **Legacy Corruption** (0-5 meter with immediate loss at 5)
- **Legacy Checks** (33% roll on Crown allegiance → Lie vs. Truth choice)
- **Betrayal Nullification** (political gravity penalty for faction betrayal)
- **Two Heir Archetypes** (Julian and Rowan with unique abilities/risks)

The integration task is to:
1. Add the menu option
2. Implement the game loop function `run_ashburn_campaign()`
3. Handle immediate loss conditions
4. Display heir status panels

**NO changes to the Ashburn module itself are required.**

---

## AFFECTED FILES

### Files to Modify
- `/home/pi/Projects/claude_sandbox/Codex/codex_agent_main.py` — Add menu option, import, and game loop

### Files Referenced (Read-Only)
- `/home/pi/Projects/claude_sandbox/Codex/ashburn_crew_module.py` — The complete Ashburn engine
- `/home/pi/Projects/claude_sandbox/Codex/codex_crown_module.py` — Parent class reference
- `/home/pi/Projects/claude_sandbox/Codex/WORK_ORDER_038_BLUEPRINT.md` — Original design spec

---

## DEPENDENCY ANALYSIS

### Import Chain
```
codex_agent_main.py
  └── IMPORTS → ashburn_crew_module.py (AshburnHeirEngine)
        └── INHERITS FROM → codex_crown_module.py (CrownAndCrewEngine)
              └── USES → codex_world_engine.py (WorldState)
```

### Import Location
**Add to codex_agent_main.py at line 48 (after Crown import):**

```python
# Crown & Crew Engine
from codex_crown_module import CrownAndCrewEngine

# Ashburn Heir Engine (Gothic Corruption Variant)
try:
    from ashburn_crew_module import AshburnHeirEngine
    ASHBURN_AVAILABLE = True
except ImportError:
    ASHBURN_AVAILABLE = False
    logger.warning("Ashburn module not available")
```

**Risk:** None. Follows the existing Discord/Telegram bot pattern (lines 54-66).

---

## ASHBURN API REFERENCE

### Available Methods (from ashburn_crew_module.py)

| Method | Line | Purpose |
|--------|------|---------|
| `__init__(heir_name)` | 148 | Initialize with heir selection (Julian/Rowan) |
| `generate_legacy_check()` | 177 | Roll 1d6, return intervention data if 5-6 |
| `resolve_legacy_choice(choice)` | 201 | Process [1] Obey or [2] Lie, adjust corruption |
| `check_betrayal()` | 243 | Return game-over dict if corruption ≥ 5 |
| `add_corruption(amount)` | 265 | Increment corruption and check loss |
| `get_heir_status()` | 282 | Return Rich Panel with corruption meter |
| `get_vote_power()` | 372 | Return vote weight (nullified if betrayed) |

### Heir Data (LEADERS dict, line 44)
```python
LEADERS = {
    "Julian": {
        "title": "The Gilded Son",
        "ability": "Legacy Name — Starts with +1 Sway toward Crown",
        "risk": "Arrogant. Cannot refuse Crown challenges, even losing ones."
    },
    "Rowan": {
        "title": "The Ash Walker",
        "ability": "Ember Network — Knows the location of all Campfire events",
        "risk": "Haunted past. Random Campfire events trigger corruption checks."
    }
}
```

### Legacy Check Data Structure
```python
{
    "triggered": bool,        # True if roll was 5-6
    "roll": int,             # 1-6
    "prompt": str            # The moral dilemma text
}
```

### Corruption Loss Structure
```python
{
    "game_over": bool,
    "message": str           # "THE SOLARIUM OPENS..." loss text
}
```

---

## INTEGRATION STATE MACHINE

### High-Level Flow

```
┌─────────────────────────────────────────────────────┐
│                   MAIN MENU                         │
│  [1] New Campaign                                   │
│  [2] Crown & Crew                                   │
│  [3] Ashburn Campaign  ← NEW OPTION                 │
│  [4] Mimir Chat                                     │
│  [5] System Status                                  │
│  [6] Exit                                           │
└───────────────┬─────────────────────────────────────┘
                │ User selects [3]
                ▼
┌─────────────────────────────────────────────────────┐
│         PHASE 1: HEIR SELECTION                     │
│  Display two heir dossiers (Julian vs Rowan)       │
│  Prompt: [1] Julian or [2] Rowan                    │
│  Validate input, allow 'back' to main menu          │
└───────────────┬─────────────────────────────────────┘
                │ Heir selected
                ▼
┌─────────────────────────────────────────────────────┐
│         PHASE 2: INSTANTIATION                      │
│  engine = AshburnHeirEngine(heir_name=selected)     │
│  Display get_heir_status() panel                    │
│  Display leader ability and risk briefing           │
│  Pause for user acknowledgment                      │
└───────────────┬─────────────────────────────────────┘
                │ User ready
                ▼
┌─────────────────────────────────────────────────────┐
│         PHASE 3: GAME LOOP (5 Days)                 │
│  For day in range(1, 6):                            │
│    ├─ TURN_START                                    │
│    ├─ LEGACY_CHECK (if Crown allegiance)            │
│    ├─ INTERVENTION or STANDARD_TURN                 │
│    ├─ RESOLVE                                       │
│    ├─ STATUS_UPDATE                                 │
│    ├─ CHECK_BETRAYAL                                │
│    └─ TURN_END (loop back or game over)             │
└───────────────┬─────────────────────────────────────┘
                │ Day 5 complete OR corruption ≥ 5
                ▼
┌─────────────────────────────────────────────────────┐
│         PHASE 4: END STATES                         │
│  ├─ BAD END (corruption ≥ 5): Solarium opens        │
│  ├─ GOOD END (survived 5 days): Legacy report       │
│  └─ QUIT (mid-game): Save and return to menu        │
└─────────────────────────────────────────────────────┘
```

### Detailed Turn State Machine

```
TURN_START
    │
    ├─ Display get_heir_status()
    ├─ Display world prompt (environment)
    ├─ If day == 3: Display secret witness
    │
    ▼
ALLEGIANCE_CHOICE
    │
    ├─ Prompt: [C]rown or C[R]ew?
    ├─ Validate input
    ├─ Call declare_allegiance(side)
    │
    ▼
LEGACY_CHECK (only if side == 'crown')
    │
    ├─ check = generate_legacy_check()
    ├─ If check["triggered"] == False:
    │     └─ Skip to STANDARD_TURN
    │
    ├─ If check["triggered"] == True:
    │     ├─ Display intervention prompt
    │     ├─ Prompt: [1] Obey or [2] Lie?
    │     ├─ Call resolve_legacy_choice(choice)
    │     ├─ Check for corruption change
    │     └─ Call check_betrayal()
    │           ├─ If game_over: Display BAD END → EXIT
    │           └─ Else: Continue
    │
    ▼
STANDARD_TURN (if no intervention or Crew allegiance)
    │
    ├─ Display get_prompt() (Crown/Crew dilemma)
    ├─ User responds (freeform or choice)
    ├─ Show DNA accumulation
    │
    ▼
STATUS_UPDATE
    │
    ├─ Display get_heir_status()
    ├─ Show corruption meter
    ├─ Show sway position
    │
    ▼
CHECK_BETRAYAL
    │
    ├─ loss_check = check_betrayal()
    ├─ If loss_check["game_over"]:
    │     └─ Display BAD END → EXIT
    │
    ▼
TURN_END
    │
    ├─ If day != 3: Display campfire prompt
    ├─ Call end_day()
    ├─ If day < 5: Loop back to TURN_START
    └─ If day == 5: Continue to FINALE
```

---

## PSEUDO-CODE DESIGN

### Phase 1: Heir Selection Loop

```
FUNCTION display_heir_dossiers():
    CREATE table with 2 columns
    FOR each heir in ["Julian", "Rowan"]:
        data = LEADERS[heir]
        ADD row: [number], [name], [title], [ability], [risk]
    PRINT table
    RETURN

FUNCTION select_heir():
    WHILE True:
        CALL display_heir_dossiers()
        PROMPT "Select [1] Julian or [2] Rowan (or 'back'): "
        READ user_input

        IF user_input == "back":
            RETURN None  # Exit to main menu

        IF user_input == "1":
            RETURN "Julian"

        IF user_input == "2":
            RETURN "Rowan"

        ELSE:
            PRINT "Invalid input. Enter 1, 2, or 'back'."
            CONTINUE
```

**Data Flow:**
- INPUT: User keystroke
- OUTPUT: "Julian" | "Rowan" | None
- SIDE EFFECT: None (stateless)

---

### Phase 2: Instantiation

```
FUNCTION initialize_heir(heir_name: str, world_state: dict | None):
    # Create engine instance
    engine = AshburnHeirEngine(heir_name=heir_name)

    # Optionally inject custom world
    IF world_state is not None:
        engine.world_state = world_state

    # Display initial briefing
    CLEAR console
    PRINT Panel(
        title="ASHBURN CAMPAIGN BEGINS",
        content=
            "Heir: {heir_name}\n"
            "Title: {engine.heir_leader['title']}\n\n"
            "Ability: {engine.leader_ability}\n"
            "Risk: {engine.heir_leader['risk']}\n\n"
            "Starting Corruption: {engine.legacy_corruption}/5\n"
            "Starting Sway: {engine.sway}"
    )

    # Display status panel
    PRINT engine.get_heir_status()

    # Wait for confirmation
    PROMPT "Press Enter to begin your journey..."

    RETURN engine
```

**Data Flow:**
- INPUT: heir_name (str), world_state (dict | None)
- OUTPUT: AshburnHeirEngine instance
- STATE CHANGE: Engine initialized with heir data

---

### Phase 3: Game Loop (Core Logic)

```
FUNCTION run_ashburn_campaign(world_state: dict | None):
    # PHASE 1: Heir Selection
    heir_name = select_heir()
    IF heir_name is None:
        RETURN  # User chose 'back'

    # PHASE 2: Instantiation
    engine = initialize_heir(heir_name, world_state)

    # PHASE 3: Game Loop
    FOR day IN range(1, 6):
        # Determine region (cosmetic)
        region = get_region_name(day)

        # ─────────────────────────────────────────────────────
        # SUB-PHASE A: MORNING (World Card)
        # ─────────────────────────────────────────────────────
        CLEAR console
        PRINT engine.get_heir_status()
        PRINT f"DAY {day} — {region}"
        PRINT "☀️  MORNING — THE ROAD AHEAD"

        world_prompt = engine.get_world_prompt()
        PRINT Panel(world_prompt, border_style=SILVER)

        # Day 3 special event
        IF day == 3:
            witness = engine.get_secret_witness()
            PRINT Panel(witness, title="👁️ SECRET WITNESS", border_style=CRIMSON)

        PROMPT "How do you traverse this terrain? > "

        # ─────────────────────────────────────────────────────
        # SUB-PHASE B: NIGHT (Allegiance Choice)
        # ─────────────────────────────────────────────────────
        CLEAR console
        PRINT engine.get_heir_status()
        PRINT "🌙 NIGHT — THE MOMENT OF CHOICE"
        PRINT "Declare your allegiance BEFORE seeing the consequences."

        WHILE True:
            PROMPT "[C]rown or C[R]ew: "
            READ side
            IF side in ['c', 'crown']:
                side = 'crown'
                BREAK
            ELIF side in ['r', 'crew']:
                side = 'crew'
                BREAK
            ELSE:
                PRINT "Enter C for Crown or R for Crew"

        # Declare allegiance (adjusts sway, logs history)
        result = engine.declare_allegiance(side)
        PRINT result

        # ─────────────────────────────────────────────────────
        # SUB-PHASE C: LEGACY CHECK (Crown only, 33% chance)
        # ─────────────────────────────────────────────────────
        IF side == 'crown':
            check = engine.generate_legacy_check()

            IF check["triggered"]:
                PRINT Panel(
                    title="⚠️ LEGACY INTERVENTION",
                    content=
                        f"Roll: {check['roll']}/6 — Your legacy calls.\n\n"
                        f"{check['prompt']}\n\n"
                        "[1] Obey — Submit to authority (+Corruption, -Sway)\n"
                        "[2] Lie — Deflect and deceive (+Sway, Risk)"
                )

                WHILE True:
                    PROMPT "Choose [1] or [2]: "
                    READ choice
                    IF choice in ['1', '2']:
                        BREAK

                # Process choice
                lc_result = engine.resolve_legacy_choice(int(choice))
                PRINT lc_result

                # Check for immediate loss
                loss_check = engine.check_betrayal()
                IF loss_check["game_over"]:
                    PRINT Panel(
                        title="💀 GAME OVER — THE SOLARIUM OPENS 💀",
                        content=loss_check["message"],
                        border_style=CRIMSON
                    )
                    PROMPT "Press Enter to return to Main Menu..."
                    RETURN  # Exit campaign immediately

        # ─────────────────────────────────────────────────────
        # SUB-PHASE D: STANDARD TURN (Show dilemma)
        # ─────────────────────────────────────────────────────
        prompt = engine.get_prompt()
        dilemma_title = "👑 CROWN'S BURDEN" IF side == 'crown' ELSE "🏴 CREW'S TRIAL"
        PRINT Panel(prompt, title=dilemma_title, border_style=MAGENTA)

        # Show DNA accumulation
        dom_tag = engine.get_dominant_tag()
        PRINT f"Your dominant trait: {dom_tag}"

        PROMPT "What do you do? > "

        # ─────────────────────────────────────────────────────
        # SUB-PHASE E: CAMPFIRE (except Day 3)
        # ─────────────────────────────────────────────────────
        IF day != 3:
            CLEAR console
            PRINT engine.get_heir_status()
            PRINT "🔥 CAMPFIRE — THE ECHO"

            campfire = engine.get_campfire_prompt()
            PRINT Panel(campfire, border_style="yellow")

            PROMPT "Your reflection? > "
        ELSE:
            PRINT "No campfire tonight. The Breach has silenced us."

        # ─────────────────────────────────────────────────────
        # SUB-PHASE F: STATUS UPDATE
        # ─────────────────────────────────────────────────────
        PRINT engine.get_heir_status()

        # ─────────────────────────────────────────────────────
        # SUB-PHASE G: CHECK BETRAYAL (again, in case of changes)
        # ─────────────────────────────────────────────────────
        loss_check = engine.check_betrayal()
        IF loss_check["game_over"]:
            PRINT Panel(
                title="💀 CORRUPTION CONSUMES YOU 💀",
                content=loss_check["message"],
                border_style=CRIMSON
            )
            PROMPT "Press Enter to return to Main Menu..."
            RETURN  # Exit campaign

        # ─────────────────────────────────────────────────────
        # SUB-PHASE H: DAY TRANSITION
        # ─────────────────────────────────────────────────────
        end_msg = engine.end_day()
        PRINT end_msg

        IF day < 5:
            PROMPT "Press Enter to rest..."
        ELSE:
            PROMPT "Press Enter to face your fate..."

    # ─────────────────────────────────────────────────────────
    # PHASE 4: FINALE (Good Ending)
    # ─────────────────────────────────────────────────────────
    CLEAR console

    # Final corruption check (should not trigger if we got here)
    loss_check = engine.check_betrayal()
    IF loss_check["game_over"]:
        PRINT Panel(
            title="💀 BAD END 💀",
            content=loss_check["message"]
        )
    ELSE:
        # Victory report
        report = engine.generate_legacy_report()
        summary = engine.get_summary()

        PRINT Panel(
            title="THE BORDER — JOURNEY'S END",
            content="You survived five days. Your legacy is forged."
        )

        PRINT Panel(report, title="⚔️ LEGACY REPORT ⚔️", border_style=EMERALD)
        PRINT Panel(summary, title="📜 JOURNEY LOG", border_style=SILVER)

    # Save report to file
    timestamp = get_current_timestamp()
    filename = f"ashburn_legacy_{timestamp}.txt"
    WRITE file:
        "ASHBURN CAMPAIGN REPORT\n"
        "Heir: {engine.heir_name}\n"
        "Final Corruption: {engine.legacy_corruption}/5\n"
        "Generated: {timestamp}\n"
        "=" * 60 + "\n\n"
        report + "\n\n" + summary

    PRINT f"Report saved to: {filename}"
    PROMPT "Press Enter to return to Main Menu..."
    RETURN
```

**Data Flow Summary:**
```
USER INPUT (heir selection)
    → AshburnHeirEngine instance
        → 5 day loops
            → Each loop: allegiance choice → legacy check → corruption tracking
                → Immediate exit if corruption ≥ 5
                    OR
                → Continue to next day
        → Final report generation
            → Save to file
                → Return to main menu
```

---

## ERROR HANDLING STRATEGY

### Import Failure
```
IF ashburn_crew_module cannot be imported:
    SET ASHBURN_AVAILABLE = False
    LOG warning
    HIDE menu option [3] in UI
```

### Corruption Overflow
```
IF corruption > 5:
    CLAMP to 5
    TRIGGER immediate loss
```

### Invalid Heir Selection
```
IF heir_name not in ["Julian", "Rowan"]:
    DEFAULT to "Julian"
    LOG warning
```

### Mid-Campaign Quit
```
IF user presses Ctrl+C or types 'quit':
    PROMPT "Save progress? [Y/n]"
    IF yes:
        SERIALIZE engine.to_dict()
        SAVE to GameSave(name=f"ashburn_autosave_{timestamp}")
    RETURN to main menu
```

### World State Injection Failure
```
IF world_state is provided BUT invalid:
    LOG warning
    FALLBACK to hardcoded Ashburn prompts
    CONTINUE (graceful degradation)
```

---

## INTEGRATION POINT MAP

### File: codex_agent_main.py

#### Integration Point #1: Import Block
**Location:** After line 48 (Crown import)
```python
# LINE 48-49
from codex_crown_module import CrownAndCrewEngine

# NEW LINES (after line 49)
try:
    from ashburn_crew_module import AshburnHeirEngine
    ASHBURN_AVAILABLE = True
except ImportError:
    ASHBURN_AVAILABLE = False
    logger.warning("Ashburn module not available")
```

#### Integration Point #2: Menu Table
**Location:** Line 949 (menu.add_row calls)
```python
# EXISTING (line 949-953)
menu.add_row("[1]", "New Campaign     — Begin a new adventure")
menu.add_row("[2]", "Crown & Crew     — 5-Day Narrative Journey")
menu.add_row("[3]", "Mimir Chat       — Speak with the AI")
menu.add_row("[4]", "System Status    — View detailed vitals")
menu.add_row("[5]", "Exit             — Return to the mundane world")

# REPLACE WITH:
menu.add_row("[1]", "New Campaign     — Begin a new adventure")
menu.add_row("[2]", "Crown & Crew     — 5-Day Narrative Journey")

# NEW CONDITIONAL ROW
if ASHBURN_AVAILABLE:
    menu.add_row("[3]", "Ashburn Campaign — Gothic Heir Corruption Journey")
    next_option = 4
else:
    next_option = 3

menu.add_row(f"[{next_option}]", "Mimir Chat       — Speak with the AI")
menu.add_row(f"[{next_option+1}]", "System Status    — View detailed vitals")
menu.add_row(f"[{next_option+2}]", "Exit             — Return to the mundane world")
```

#### Integration Point #3: Menu Input Prompt
**Location:** Line 964
```python
# EXISTING
choice = await ainput("[gold1]Choose thy path [1/2/3/4/5/q]:[/] ")

# REPLACE WITH:
if ASHBURN_AVAILABLE:
    choice = await ainput("[gold1]Choose thy path [1/2/3/4/5/6/q]:[/] ")
else:
    choice = await ainput("[gold1]Choose thy path [1/2/3/4/5/q]:[/] ")
```

#### Integration Point #4: Choice Handler
**Location:** Line 975 (after option "2" handler)
```python
# EXISTING (lines 975-980)
elif choice == "2":
    ws = None
    if current_save and current_save.state.get("world_state"):
        ws = current_save.state["world_state"]
    await run_crown_campaign(world_state=ws)

# NEW HANDLER (after line 980)
elif choice == "3" and ASHBURN_AVAILABLE:
    # Ashburn Campaign
    ws = None
    if current_save and current_save.state.get("world_state"):
        ws = current_save.state["world_state"]
    await run_ashburn_campaign(world_state=ws)

elif choice == "3":
    # If Ashburn not available, this is Mimir Chat
    await run_mimir_chat(core)
```

#### Integration Point #5: New Function Definition
**Location:** After line 791 (end of run_crown_campaign)
```python
# NEW FUNCTION (insert after line 791)
async def run_ashburn_campaign(world_state: dict = None):
    """
    Run the Ashburn Heir 5-Day Corruption Campaign.

    Uses AshburnHeirEngine instead of base CrownAndCrewEngine.
    Implements Legacy Checks, Corruption tracking, and immediate loss.

    Args:
        world_state: Optional WorldState dict (from saved game or genesis)
    """
    # [FULL IMPLEMENTATION FROM PSEUDO-CODE SECTION]
```

---

## STATE TRANSITION TABLE

| Current State | Event | Next State | Side Effect |
|---------------|-------|------------|-------------|
| MAIN_MENU | Select [3] | HEIR_SELECT | None |
| HEIR_SELECT | Select heir | BRIEFING | Engine initialized |
| HEIR_SELECT | Select 'back' | MAIN_MENU | None |
| BRIEFING | Press Enter | TURN_START | Day = 1 |
| TURN_START | View world | ALLEGIANCE_CHOICE | Display world prompt |
| ALLEGIANCE_CHOICE | Choose Crown | LEGACY_CHECK | Sway -1 |
| ALLEGIANCE_CHOICE | Choose Crew | STANDARD_TURN | Sway +1 |
| LEGACY_CHECK | Roll 1-4 | STANDARD_TURN | No intervention |
| LEGACY_CHECK | Roll 5-6 | INTERVENTION | Display prompt |
| INTERVENTION | Choose [1] Obey | CHECK_BETRAYAL | Corruption +1, Sway -1 |
| INTERVENTION | Choose [2] Lie | CHECK_BETRAYAL | Sway +1, Risk roll |
| CHECK_BETRAYAL | Corruption < 5 | STATUS_UPDATE | Continue |
| CHECK_BETRAYAL | Corruption ≥ 5 | BAD_END | Game over |
| STATUS_UPDATE | Continue | TURN_END | Display status |
| TURN_END | Day < 5 | TURN_START | Day +1 |
| TURN_END | Day == 5 | FINALE | Generate report |
| FINALE | Corruption < 5 | GOOD_END | Victory screen |
| FINALE | Corruption ≥ 5 | BAD_END | Loss screen |
| BAD_END | Press Enter | MAIN_MENU | Save report |
| GOOD_END | Press Enter | MAIN_MENU | Save report |

---

## WIN/LOSS CONDITIONS

### GOOD END (Victory)
**Condition:** `engine.day > 5 AND engine.legacy_corruption < 5`

**Display:**
```
╔═══════════════════════════════════════════════╗
║     THE INHERITANCE — JOURNEY'S END           ║
╠═══════════════════════════════════════════════╣
║  You survived the five days.                  ║
║  The Tribunal recognizes your legitimacy.     ║
║  Your legacy endures.                         ║
╚═══════════════════════════════════════════════╝

[Display Legacy Report with final stats]
[Display Journey Log with history]
```

### BAD END (Corruption Loss)
**Condition:** `engine.legacy_corruption >= 5`

**Display:**
```
╔═══════════════════════════════════════════════╗
║          THE SOLARIUM OPENS                   ║
╠═══════════════════════════════════════════════╣
║  The glass shatters inward.                   ║
║  You were never the heir —                    ║
║  you were the inheritance.                    ║
║                                               ║
║  ASHBURN CLAIMS ANOTHER.                      ║
║                                               ║
║  [GAME OVER]                                  ║
╚═══════════════════════════════════════════════╝

Corruption: 5/5
Days Survived: {engine.day}/5
```

### QUIT (Mid-Game)
**Condition:** User presses Ctrl+C or types 'quit' during campaign

**Flow:**
1. Display "Save progress? [Y/n]"
2. If Yes: Serialize engine state to JSON
3. Return to main menu

---

## SAVE/LOAD INTEGRATION

### Save Format Extension
**Add to GameSave.state dict:**
```python
{
    "engine_type": "ashburn",  # Flag for load detection
    "heir_name": "Julian",
    "legacy_corruption": 3,
    "betrayal_triggered": False,
    "heir_leader": {...},      # NPC data
    # ... all parent fields ...
}
```

### Load Detection
**In new_campaign_wizard() or load_campaign():**
```python
if save.state.get("engine_type") == "ashburn":
    # Load using AshburnHeirEngine.from_dict()
    engine = AshburnHeirEngine.from_dict(save.state)
else:
    # Load using base CrownAndCrewEngine
    engine = CrownAndCrewEngine(**save.state)
```

---

## ACCEPTANCE CRITERIA

**The implementation is COMPLETE when:**

1. ✅ User can select "Ashburn Campaign" from main menu (if ASHBURN_AVAILABLE)
2. ✅ Heir selection displays two dossiers with abilities/risks
3. ✅ Selecting an heir initializes AshburnHeirEngine with correct starting state
4. ✅ Legacy Checks trigger on Crown allegiance with ~33% probability
5. ✅ Intervention prompt displays [1] Obey and [2] Lie choices
6. ✅ Resolving intervention adjusts corruption and sway correctly
7. ✅ Corruption ≥ 5 triggers immediate game-over (BAD END)
8. ✅ get_heir_status() panel displays after each turn
9. ✅ 5-day loop completes with GOOD END if corruption < 5
10. ✅ Legacy report saves to file with timestamp
11. ✅ "back" option in heir selection returns to main menu
12. ✅ No thermal alerts during gameplay (text-only UI)
13. ✅ All existing menu options renumber correctly

---

## TESTING REQUIREMENTS FOR @PLAYTESTER

### Test Case #1: Menu Integration
**Steps:**
1. Launch `python codex_agent_main.py`
2. Verify option [3] appears if `ashburn_crew_module.py` exists
3. Select [3]
4. Verify heir selection screen appears

**Expected:** No crashes, heir dossiers display correctly

---

### Test Case #2: Heir Selection Validation
**Steps:**
1. At heir selection, enter invalid input ("abc", "5", "")
2. Verify error message: "Enter 1 for Julian or 2 for Rowan"
3. Enter "back"
4. Verify return to main menu

**Expected:** Loop continues until valid input or back

---

### Test Case #3: Legacy Check Trigger Rate
**Steps:**
1. Start Ashburn campaign
2. Select Crown allegiance 10 times in a row
3. Count how many times the intervention prompt appears

**Expected:** ~3-4 interventions (30-40% of 10 trials)

---

### Test Case #4: Corruption Loss Condition
**Steps:**
1. Start campaign, select Julian
2. Select Crown allegiance every turn
3. When Legacy Check triggers, always choose [1] Obey
4. Continue until corruption reaches 5

**Expected:** Game-over screen appears immediately, "THE SOLARIUM OPENS" message

---

### Test Case #5: Good Ending
**Steps:**
1. Start campaign
2. Balance Crown/Crew choices to avoid hitting corruption 5
3. Complete all 5 days

**Expected:** Legacy Report displays, file saved to disk

---

### Test Case #6: Status Panel Display
**Steps:**
1. Start campaign
2. After each turn, verify `get_heir_status()` panel shows:
   - Heir name and title
   - Corruption meter (visual bar)
   - Current sway
   - Leader ability and risk

**Expected:** Panel updates correctly after each corruption change

---

### Test Case #7: World State Injection
**Steps:**
1. Create a custom world via "New Campaign" → "Homebrew"
2. Load that world's WorldState
3. Start Ashburn campaign with that world
4. Verify Crown/Crew prompts use custom world data

**Expected:** Prompts reflect custom world terms and content

---

### Test Case #8: Backward Compatibility
**Steps:**
1. Play a standard Crown & Crew campaign
2. Verify option [2] still works identically
3. Verify no Ashburn mechanics leak into standard mode

**Expected:** No corruption tracking, no Legacy Checks in standard mode

---

## RISK ASSESSMENT

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Import Failure** | LOW | LOW | Try/except wrapper, ASHBURN_AVAILABLE flag |
| **Infinite Loop in Input** | MEDIUM | LOW | Validation in all input prompts, 'back' escape |
| **Corruption Overflow** | LOW | NONE | Engine clamps at 5, immediate loss check |
| **Save File Corruption** | MEDIUM | LOW | Engine includes to_dict/from_dict with validation |
| **Menu Renumbering Bug** | MEDIUM | MEDIUM | Use dynamic next_option variable, test all paths |
| **Thermal Overload** | LOW | NONE | Text UI only, one LLM call per Legacy Check (rare) |

---

## THERMAL IMPACT ASSESSMENT

**Ashburn-Specific Operations:**
- Heir selection: 0 LLM calls → +0°C
- Legacy Check roll: Random number generation → +0°C
- Corruption tracking: Integer increment → +0°C
- Status panel rendering: Rich formatting → +0.1°C
- Legacy Check prompt display: Text only → +0°C

**Total Thermal Delta:** <0.5°C

**Comparison to Baseline:**
- Standard Crown & Crew campaign: 0.5-1°C
- Ashburn campaign: 0.5-1°C (identical)

**Conclusion:** No additional thermal risk beyond base Crown & Crew.

---

## NEXT STEPS FOR @MECHANIC

### Implementation Checklist

- [ ] **Step 1:** Add Ashburn import block after line 49 in `codex_agent_main.py`
- [ ] **Step 2:** Update menu table at line 949 with conditional Ashburn option
- [ ] **Step 3:** Update menu input prompt at line 964 for dynamic option count
- [ ] **Step 4:** Add choice handler at line 980 for option "3"
- [ ] **Step 5:** Implement `run_ashburn_campaign()` function after line 791
- [ ] **Step 6:** Implement `select_heir()` helper function (referenced in pseudo-code)
- [ ] **Step 7:** Implement `initialize_heir()` helper function
- [ ] **Step 8:** Implement `get_region_name(day)` helper for region labels
- [ ] **Step 9:** Test all integration points with @Playtester test cases
- [ ] **Step 10:** Verify no regressions in standard Crown & Crew mode

### Estimated Implementation Time
- Import + Menu: 30 minutes
- Heir Selection UI: 1 hour
- Game Loop Function: 3 hours
- Error Handling: 1 hour
- Testing: 1.5 hours

**Total: ~7 hours**

---

## DESIGN RATIONALE

### Why Two Heirs Only?
- **Simplicity:** Reduces decision paralysis
- **Narrative Focus:** Julian vs Rowan represent Order vs Chaos archetypes
- **Thermal:** No LLM generation needed for heir descriptions
- **Extensibility:** Future heirs can be added by extending LEADERS dict

### Why 33% Legacy Check Rate?
- **Narrative Pacing:** Too frequent becomes tedious, too rare feels random
- **Thematic:** "The weight of legacy is always present, but not always visible"
- **Game Balance:** ~1.5 checks per 5-day campaign

### Why Immediate Loss at Corruption 5?
- **Tension:** Creates constant threat, every decision matters
- **Thematic:** "The Solarium opens" — corruption is a one-way door
- **Design:** Matches gothic tone, no redemption arc

### Why No Redemption/Corruption Reduction?
- **Consistency:** Once corrupted, the stain remains
- **Simplicity:** No complex forgiveness mechanics
- **Future Extension:** Lydia's ability (Shield Protocol) could reduce corruption once

---

## APPENDICES

### Appendix A: Helper Function Signatures

```python
def get_region_name(day: int) -> str:
    """Return the region name for a given day."""
    if day <= 2:
        return "THE ASHBURN GROUNDS"
    elif day == 3:
        return "THE BREACH"
    elif day == 4:
        return "THE TRIBUNAL APPROACH"
    else:
        return "THE INHERITANCE"

async def select_heir() -> str | None:
    """Display heir dossiers and prompt selection. Returns heir name or None."""
    # See pseudo-code Phase 1

async def initialize_heir(heir_name: str, world_state: dict | None) -> AshburnHeirEngine:
    """Create and display initial briefing for heir. Returns engine instance."""
    # See pseudo-code Phase 2
```

### Appendix B: Color Constants Reference

```python
# From codex_agent_main.py (lines 112-118)
GOLD = "bold yellow"
CRIMSON = "bold red"
EMERALD = "bold green"
SILVER = "dim white"
ROYAL_BLUE = "bold blue"
PARCHMENT = "wheat1"
MAGENTA = "bold magenta"
```

**Ashburn UI Color Scheme:**
- Corruption warnings: CRIMSON
- Status panels: GOLD borders
- Legacy Checks: MAGENTA borders
- Good endings: EMERALD
- Heir name: GOLD

### Appendix C: File Path Conventions

**CRITICAL:** All file paths must be absolute on Raspberry Pi environment.

```python
# CORRECT
report_path = CODEX_DIR / f"ashburn_legacy_{timestamp}.txt"

# INCORRECT (cwd resets between bash calls)
report_path = f"ashburn_legacy_{timestamp}.txt"
```

### Appendix D: Ashburn Prompt Pools

**The module already contains these at lines 66-108:**
- `ASHBURN_PROMPTS["crown"]` — 8 prompts
- `ASHBURN_PROMPTS["crew"]` — 8 prompts
- `ASHBURN_PROMPTS["world"]` — 8 prompts
- `ASHBURN_PROMPTS["campfire"]` — 8 prompts
- `LEGACY_PROMPTS` — 8 intervention prompts

**No additional content generation required.**

---

## FINAL SIGN-OFF

**Blueprint Status:** ✅ COMPLETE AND ACTIONABLE
**Ready for Implementation:** YES
**Estimated Implementation Time:** 7 hours
**Risk Level:** LOW
**Thermal Impact:** <0.5°C

**Architect Notes:**
The Ashburn module is complete and tested (see module test at ashburn_crew_module.py:464). This integration is purely UI wiring with no business logic changes required. The state machine is deterministic and follows the proven Crown & Crew loop structure.

The immediate loss condition at corruption 5 is intentional and thematic — it creates tension and consequence without recovery mechanics. The 33% Legacy Check rate ensures 1-2 interventions per campaign without overwhelming the player.

All designs prioritize simplicity and backward compatibility. The feature flag (ASHBURN_AVAILABLE) ensures graceful degradation if the module is missing.

**Deliverable:** This blueprint provides line-number-specific integration points, complete pseudo-code, state machine diagrams, and comprehensive test cases. @Mechanic can implement directly from this document without additional design decisions.

---

**END OF BLUEPRINT**

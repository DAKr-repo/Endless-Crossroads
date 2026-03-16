@codex-mechanic @codex-designer @codex-architect

**MISSION:** BATCH 003/004 (ENGINE RECOVERY & SIDEBAR UPGRADE)

**STEP 1: SYSTEM FIREWALL & TRANSMUTER**
1. **Architect:** Identify and DELETE any rogue "D&D-to-Burnwillow" conversion logic in `engine.py` or `campaign_manager.py`.
2. **Mechanic:** Move conversion logic to a standalone utility: `codex/forge/codex_transmuter.py`.
3. **Policy:** If a system engine is missing, fail with `MissingEngineError`; do not fallback to Burnwillow.

**STEP 2: SIDEBAR HIERARCHY & UX**
1. **Designer:** Modify `play_burnwillow.py` to use a Sidebar-first info flow.
2. **Mechanic:** - Redirect long text (Room descriptions, `inspect <id>`, `gear`) to the Sidebar Panel.
    - Reserve Adventure Log for 1-line tactical feedback (Combat, Loot, DC checks).
    - Fix the Log Overflow/Clipping issue.

**STEP 3: STABLE INVENTORY & EQUIPMENT**
1. **Mechanic:** Use permanent indices in the `backpack` (Item [2] stays at index [2] even if [0] is removed).
2. **Mechanic:** Implement 1H/2H logic. Allow 1H weapons in `L_HAND` or `R_HAND`. 2H weapons block both.

**STEP 4: TACTICAL OBJECTS & THE HUB**
1. **Mechanic:** Add `(x, y)` coords to Enemies and Loot. Implement movable `WorldObjects` (Pillars/Furniture).
2. **Designer:** Map cardinal directions to Exits in the Survey panel: `[N] Room 4 | [E] Room 5`.
3. **Author/Mechanic:** Restore **Emberhome** as the starting hub before dungeon generation.

**STEP 5: PERSISTENCE**
1. **Mechanic:** Bind the `save` command to `engine.save_game()` and add a save prompt to the `quit` command.

**VERIFICATION:**
- Run syntax check: `python3 -m py_compile play_burnwillow.py`.
- Verify `inspect` output appears in the Sidebar.
- Verify inventory indices no longer shift after equipping items.
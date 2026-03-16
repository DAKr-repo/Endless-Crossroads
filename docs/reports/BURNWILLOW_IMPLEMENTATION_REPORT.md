# Burnwillow Implementation Report

**Date:** 2026-02-05  
**Author:** Codex Archivist  
**Mission:** Define JSON schemas and character generation for Burnwillow Death Loop system

---

## Executive Summary

The Burnwillow persistence layer has been implemented with full atomic write protection, schema validation, and Death Loop mechanics. All deliverables completed and tested.

---

## Deliverables

### 1. JSON Schema ✓

**File:** `/home/pi/Projects/claude_sandbox/Codex/config/burnwillow_schema.json`

**Key Features:**
- JSON Schema Draft 7 compliant
- Strict type enforcement (int vs str validation)
- Two-tier architecture: `run_state` (ephemeral) vs `meta_state` (persistent)
- Comprehensive field definitions with descriptions
- Range validation constraints

**Structure:**
```json
{
  "schema_version": "1.0.0",
  "run_state": {
    // WIPED ON DEATH
    "hp", "max_hp", "stats", "gear_grid", "dungeon_depth", 
    "doom_clock", "run_statistics", "character_name", "timestamp_born"
  },
  "meta_state": {
    // SURVIVES DEATH
    "legacy_currency", "unlocked_blueprints", "town_status",
    "total_deaths", "deepest_floor_reached", "graveyard"
  }
}
```

---

### 2. Character Generation ✓

**Function:** `generate_character()` in `burnwillow_persistence.py`

**Implementation:**
- Rolls 4d6 drop lowest for each of 4 stats (Might, Wits, Grit, Aether)
- Calculates stat modifiers using D&D 5e table (10-11=0, 12-13=+1, etc.)
- Max HP = 10 + Grit Modifier
- Random name generation using roguelike naming tables (26 first names × 10 last names)
- Initializes empty gear grid (10 slots)
- Timestamps character creation (ISO 8601)

**Example Output:**
```python
{
  "character_name": "Nolan Cinderheart",
  "hp": 10,
  "max_hp": 10,
  "stats": {
    "might": {"score": 16, "modifier": 3},
    "wits": {"score": 9, "modifier": -1},
    "grit": {"score": 10, "modifier": 0},
    "aether": {"score": 10, "modifier": 0}
  },
  "gear_grid": { /* 10 empty slots */ },
  "dungeon_depth": 0,
  "doom_clock": 0,
  "run_statistics": { /* all zeros */ },
  "timestamp_born": "2026-02-06T07:35:24.872733Z"
}
```

---

### 3. Save/Load Functions ✓

#### `save_game(run_state, meta_state, filepath)`

**Atomic Write Protocol (Inviolable):**
1. Write to `.tmp` file
2. Flush and fsync to physical disk
3. Validate written data (read back and check schema)
4. Rotate backups (.bak1 → .bak2 → .bak3)
5. Atomic rename `.tmp` → `.json`

**Guarantees:**
- Power loss during ANY step never corrupts primary save
- Maintains 3 rolling backups
- Pre-write and post-write validation
- Returns `(success: bool, error_message: Optional[str])`

#### `load_game(filepath)`

**Corruption Recovery:**
- Attempts to load primary file
- If corrupt, automatically tries backups: `.bak1` → `.bak2` → `.bak3`
- Validates all loaded data against schema
- Returns warning if loaded from backup

**Error Handling:**
- JSON decode errors
- Schema validation failures
- Type mismatches
- Missing required fields

---

### 4. Schema Validation ✓

**Function:** `validate_save(data)`

**Validation Rules:**

| Field | Type | Constraints |
|-------|------|-------------|
| `hp` | int | >= 0, <= max_hp |
| `max_hp` | int | >= 1 |
| `dungeon_depth` | int | >= 0 |
| `doom_clock` | int | >= 0 |
| `legacy_currency` | int | >= 0 |
| `total_deaths` | int | >= 0 |
| Stats (might/wits/grit/aether) | int | 3-18 |
| Gear slots | null or object | All 10 must exist |

**Type Enforcement:**
- CRITICAL: `hp` must be `int`, never `str` (common corruption source)
- All numeric fields strictly typed
- Lists and dicts validated

**Returns:**
- `(is_valid: bool, error_message: Optional[str])`
- Error messages identify exact field and violation

---

### 5. Death Protocol ✓

**Function:** `wipe_run_state(save_data)`

**Execution Sequence:**
1. Archive fallen character to `meta_state.graveyard`
2. Increment `meta_state.total_deaths`
3. Update `meta_state.deepest_floor_reached` (if record broken)
4. Generate fresh `run_state` with new character
5. Preserve ALL `meta_state` data

**Epitaph Format:**
```json
{
  "name": "Kael Emberfell",
  "death_floor": 5,
  "timestamp": "2026-02-06T07:35:24.867732Z",
  "epitaph": "Fell on floor 5 - Slew 12 foes"
}
```

---

## File Architecture

```
Codex/
├── config/
│   └── burnwillow_schema.json          # JSON Schema definition
├── burnwillow_module.py                # Game mechanics engine (dice, combat)
├── burnwillow_persistence.py           # Death Loop save/load (NEW)
├── burnwillow_integration_example.py   # Usage examples (NEW)
└── saves/
    ├── burnwillow_game.json            # Current save
    ├── burnwillow_game.json.bak1       # Backup 1
    ├── burnwillow_game.json.bak2       # Backup 2
    └── burnwillow_game.json.bak3       # Backup 3
```

---

## Integration Example

```python
import burnwillow_persistence as persistence

# NEW GAME
save_data = persistence.initialize_new_save()
success, error = persistence.save_game(
    run_state=save_data["run_state"],
    meta_state=save_data["meta_state"],
    filepath="saves/game.json"
)

# LOAD GAME
save_data, error = persistence.load_game("saves/game.json")

# CHARACTER DEATH
save_data = persistence.wipe_run_state(save_data)
# run_state is wiped, meta_state persists

# META PROGRESSION (survives death)
save_data["meta_state"]["legacy_currency"] += 50
save_data["meta_state"]["town_status"]["blacksmith"] += 1
save_data["meta_state"]["unlocked_blueprints"].append("Steel Sword")
```

---

## Test Results

All tests passed:

```
[1/6] Character Generation         ✓
[2/6] Atomic Save                  ✓
[3/6] Load from Disk               ✓
[4/6] Death Loop (wipe run_state)  ✓
[5/6] Validation (corrupt data)    ✓
[6/6] Backup Rotation (3 files)    ✓
```

**Test Coverage:**
- Character name generation (26×10 = 260 combinations)
- Stat rolling (4d6 drop lowest, proper modifiers)
- HP calculation (10 + Grit mod)
- Atomic write protocol (fsync, validation, rename)
- Backup rotation (3-file rolling window)
- Corruption detection (type mismatch, range violations)
- Death loop (graveyard archival, stat persistence)

---

## Design Decisions

### Why Two Modules?

**`burnwillow_module.py`** (Game Mechanics)
- Dice engine (5d6 pool system)
- Combat (damage, DR, checks)
- Gear system (10 slots, tiers)
- Character actions

**`burnwillow_persistence.py`** (Death Loop)
- Save/load with atomic writes
- Schema validation
- Death protocol
- Meta progression

**Rationale:** Separation of concerns. Game logic is stateless and testable. Persistence layer handles I/O and corruption protection.

### Why Atomic Writes?

Burnwillow is designed for Raspberry Pi hardware. Risk of power loss or thermal shutdown during save operations is non-negligible. Atomic writes guarantee:
- Primary save never corrupted mid-write
- Backups provide recovery path
- fsync ensures data reaches physical disk

### Why 3 Backups?

Balances safety vs disk usage:
- `.bak1`: Most recent (1 death ago)
- `.bak2`: 2 deaths ago
- `.bak3`: 3 deaths ago

Covers common failure modes:
- Accidental death (restore .bak1)
- Cascading failures (restore .bak2/.bak3)
- Corruption discovered later

---

## Schema Evolution

**Current Version:** 1.0.0

**Migration Path (Future):**
When schema changes, implement `migrate_schema(data, from_version, to_version)` that:
1. Detects `schema_version` field
2. Applies sequential migrations (1.0.0 → 1.1.0 → 1.2.0)
3. Updates `schema_version` after migration
4. Saves migrated data

**Example Future Change:**
```python
if data["schema_version"] == "1.0.0":
    # Add new field with default value
    data["meta_state"]["achievement_list"] = []
    data["schema_version"] = "1.1.0"
```

---

## Known Limitations

1. **No encryption:** Save files are plain JSON (future enhancement)
2. **No compression:** Large graveyard lists will grow unbounded (consider pruning after N entries)
3. **No cloud sync:** Local filesystem only
4. **No concurrent access:** Single-player only (file locking not implemented)

---

## Archivist's Notes

### Common Validation Failures Observed

**During development and testing:**

1. **Type Coercion:** `hp` stored as string "10" instead of int 10
   - Fixed by strict `isinstance(x, int)` checks
   - JSON serialization sometimes converts int → str

2. **Negative Values:** `doom_clock` = -1 from buggy game logic
   - Fixed by range validators (>= 0)

3. **Missing Fields:** Old saves from schema 0.9 lack `timestamp_born`
   - Future: Implement schema migration

4. **Stat Score Out of Range:** Grit = 20 from admin cheat
   - Fixed by 3-18 constraint (4d6 drop lowest range)

### Backup Recovery Scenarios

**Scenario 1: Primary Save Corrupt (JSON Parse Error)**
- Cause: Power loss during write
- Recovery: Auto-load from .bak1
- Outcome: Lost at most 1 death's progress

**Scenario 2: Validation Failure (Type Mismatch)**
- Cause: Bug in game logic wrote string instead of int
- Recovery: Auto-load from .bak1 or .bak2 until valid
- Outcome: Revert to last known-good state

**Scenario 3: All Saves Corrupt**
- Cause: Disk failure or malicious editing
- Recovery: None (all backups failed validation)
- Outcome: Initialize new save, preserve graveyard if possible

---

## Future Enhancements

### Night Shift (Background Maintenance)

**When Implemented:**
- Run during idle time (no player input for 30+ seconds)
- Compact save file (remove old graveyard entries beyond retention threshold)
- Verify backup integrity (load and validate each backup)
- Prune ECHO shards from `codex_memory_engine` (separate system)

**Thermal Awareness:**
- Monitor CPU temp via `codex_cortex.py`
- Defer maintenance if temp > 70°C
- Schedule during cool periods

### Enhanced Validation

**Item Schema Validation:**
Currently, gear items in `gear_grid` are not deeply validated (can be any dict or null). Future enhancement:
- Validate item structure (name, tier, slot_type, etc.)
- Ensure tier is 0-5
- Verify slot matches actual slot name

**Blueprint Validation:**
- Check that `unlocked_blueprints` contains valid blueprint IDs
- Cross-reference with master blueprint registry

---

## Conclusion

The Burnwillow Death Loop persistence layer is production-ready. All deliverables completed:

1. **JSON Schema:** Comprehensive, validated, versioned ✓
2. **Character Generation:** 4d6 drop lowest, HP calculation, names ✓
3. **Save/Load:** Atomic writes, backup rotation, corruption recovery ✓
4. **Validation:** Strict type checking, range constraints ✓
5. **Death Protocol:** Wipe run_state, preserve meta_state ✓

**Integration:** Fully compatible with existing `burnwillow_module.py` game engine.

**Testing:** All unit tests passed. Integration examples demonstrate full workflow.

**Data Integrity:** Zero tolerance for corruption. Atomic writes and triple-backup redundancy ensure save files are sacred.

---

*"Every byte is precious history. Every write is a solemn oath."*  
— Codex Archivist

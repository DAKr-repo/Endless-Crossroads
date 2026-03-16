# WO-STUBS: The Loose Threads
## Work Order — Stub Completion & System Flesh-Out

All stubs, placeholders, and incomplete implementations across the Codex project,
organized by the system they were meant to serve. Each entry describes current state,
intended purpose, what's missing, and dependencies.

---

## SYSTEM 1: PDF-to-Map Pipeline

### Stub 1A: `codex/core/services/cartography.py` — `generate_map_from_context()`
**Current state:** Pure placeholder — creates output directory, returns `{"status": "pending"}`
**Intended purpose:** Bridge between FAISS-indexed PDF location descriptions (Librarian/Vault Processor) and the BSP spatial map engine. A player or GM describes a location, cartography generates a dungeon layout.
**What's missing:**
- Actual generation logic. Two paths:
  - **Path A (BSP procedural):** Instantiate `CodexMapEngine`, call `generate()` with seed derived from location context, run `ContentInjector` with appropriate `RulesetAdapter`, serialize `DungeonGraph` to `vault_maps/`
  - **Path B (External image):** Call image generation API with description, save to `vault_maps/`
- A `GenericAdapter(RulesetAdapter)` for non-Burnwillow systems — only `BurnwillowAdapter` and `TangleAdapter` exist
- `save_map()` helper to write graph/image to disk
- Return dict should flip `status` from `"pending"` to `"complete"`
**Dependencies that exist:** `VAULT_MAPS_DIR`, `CodexMapEngine`, `ContentInjector`, `BurnwillowAdapter`
**Dependencies that DON'T exist:** `GenericAdapter` for DnD5e/Cosmere/etc., no callers anywhere in codebase

### Stub 1B: `codex/core/services/cartography.py` — `list_maps()`
**Current state:** Fully implemented, zero callers
**Intended purpose:** Scan `vault_maps/` for available map files (png, jpg, svg, txt) grouped by system
**What's missing:** Just needs to be called from librarian TUI or butler command

---

## SYSTEM 2: FITD Command Dispatchers

All 5 FITD engines define command registries but have NO `handle_command()` dispatcher.

### Stub 2A: `codex/games/sav/__init__.py` — SaV Command Handlers
**Current state:** SAV_COMMANDS declares 5 commands; engine has `roll_action()` and `get_status()` but no dispatcher
**Command readiness:**

| Command | Engine method exists? | What's needed |
|---|---|---|
| `roll_action` | YES — `SaVEngine.roll_action()` | Format output as text |
| `ship_status` | PARTIAL — `get_status()` has ship/heat/coin | Named method + formatted output |
| `crew_status` | PARTIAL — `stress_clocks` dict accessible | Named method + formatted output |
| `ship_upgrade` | NO | Ship module data model + upgrade logic |
| `set_course` | NO | Sector/navigation model |

**What's missing:** `handle_command(cmd, **kwargs) -> str` dispatcher, individual handler methods, ship module data model, sector nav model

### Stub 2B: `codex/games/bob/__init__.py` — BoB Command Handlers
**Current state:** BOB_COMMANDS declares 6 commands; similar gap to SaV
**Command readiness:**

| Command | Engine method exists? | What's needed |
|---|---|---|
| `roll_action` | YES — `BoBEngine.roll_action()` | Format output |
| `legion_status` | PARTIAL — `LegionState` has supply/morale/pressure | Named method + formatted output |
| `squad_status` | PARTIAL — `stress_clocks` accessible | Named method + formatted output |
| `supply_check` | PARTIAL — `self.legion.supply` readable | `modify_supply(delta)` with bounds check |
| `campaign_advance` | NO — `self.campaign_phase` is bare string | Phase cycle logic + validation |
| `chosen_status` | NO — `self.chosen` is just a name string | Chosen NPC model with condition/clock |

**What's missing:** `handle_command()` dispatcher, Chosen NPC data model, campaign phase validation, supply mutation method

### Stub 2C: `codex/games/bitd/__init__.py` — BitD Command Handlers
**Current state:** Engine registered, no command registry or dispatcher
**What's missing:** Command definitions for crew management, score cycle, heat/rep tracking, entanglement roll + `handle_command()` dispatcher

### Stub 2D: `codex/games/candela/__init__.py` — Candela Command Handlers
**Current state:** Engine registered, no command registry or dispatcher
**What's missing:** Command definitions for Body/Brain/Bleed tracks, `take_mark`, assignment cycle + `handle_command()` dispatcher

### Stub 2E: `codex/games/cbrpnk/__init__.py` — CBR+PNK Command Handlers
**Current state:** Engine registered, no command registry or dispatcher
**What's missing:** Command definitions for glitch die, grid intrusion, corp response scaling + `handle_command()` dispatcher

---

## SYSTEM 3: Multi-Engine Session Management

### Stub 3A: `codex/core/mechanics/orchestrator.py` — `HybridGameOrchestrator`
**Current state:** Fully implemented class, zero instantiations anywhere
**Intended purpose:** Manage multiple co-active game engines in a single session (e.g., Ashburn = Crown + Burnwillow). Provides CRS gating, shared clock management, aggregated status, and merged command registries.
**What the class provides (all working):**
- `add_engine()` / `remove_engine()` / `get_engine()` with CRS validation
- `get_status()` — aggregates all engines' status
- `save_state()` / `load_state()` — serialization
- `add_clock()` / `get_clock()` — shared `UniversalClock` management
- `register_commands()` / `get_categorized_commands()` — command merge
- `get_battlefield_status()` — SaV+BoB crossover view
**What's missing:**
- No entry point in `codex_agent_main.py`, `discord_bot.py`, or `telegram_bot.py`
- Butler doesn't route through orchestrator for multi-engine status
- No session-creation flow that instantiates it, adds engines, registers commands
- `load_state()` requires callers to reconstruct engines before calling `add_engine()` — no automated round-trip
- Ashburn session flow doesn't exist as a playable mode

---

## SYSTEM 4: Narrative Intelligence

### Stub 4A: Crown Engine — `_memory_shards` Never Populated
**Current state:** `CrownAndCrewEngine` references `self._memory_shards` via `hasattr()` guard (line 330) but the attribute is never defined or populated
**Intended purpose:** Feed the Narrative Loom with session memory shards for cross-shard synthesis
**What's missing:**
- `self._memory_shards: List[MemoryShard] = []` initialization in `__init__`
- Shard population: create shards from session events (NPC interactions, player decisions, world changes) and append to `_memory_shards`
- Integration with `CodexMemoryEngine` or direct `MemoryShard` construction

### Stub 4B: `synthesize_narrative()` — Mimir Callable Signature Mismatch
**Current state:** Called with `mimir_fn=self.mimir` but the Mimir callable signature may not match `(prompt: str, context: str) -> str`. The `try/except` silently swallows mismatches, always falling through to concatenation.
**What's missing:**
- Verify/adapt `CrownAndCrewEngine.mimir` to match `synthesize_narrative()`'s expected `mimir_fn(prompt, context) -> str` signature
- Or wrap the mimir object in a lambda adapter: `mimir_fn=lambda p, c: self.mimir.invoke_model(p, system_prompt=c)`
- Remove the overly broad `except Exception: pass` and use specific exception handling

### Stub 4C: `diagnostic_trace()` — Zero Callers
**Current state:** Fully implemented keyword-matching trace that walks shard layers
**Intended purpose:** Player asks "Wait, I thought the king was dead?" and gets a layered explanation showing which shards contain that claim, with authority level and excerpt
**What's missing:** A command entry point — either a `trace <fact>` butler reflex, a librarian command, or a Discord `!trace` command

### Stub 4D: `SessionManifest` — Never Instantiated
**Current state:** Complete dataclass with caching, staleness detection, serialization
**Intended purpose:** Cache compiled narratives per session so Mimir doesn't re-synthesize on every query
**What's missing:**
- Instantiation in Crown engine or any session manager
- Pass to `synthesize_narrative()` calls for caching
- Save/load integration with session persistence

---

## SYSTEM 5: Encounter Generation

### Stub 5A: `codex/core/encounters.py` — CBR+PNK Encounter Router
**Current state:** `EncounterRouter.generate()` routes `tag == "CBR_PNK"` to `_route_stub()` which returns empty `EncounterResult` with "not yet implemented" message
**What's missing:**
- `_route_cbrpnk(ctx)` method analogous to `_route_burnwillow()` and `_route_dnd5e()`
- Grid/corp-response encounter tables (heat-scaled)
- Cyberpunk NPC templates (like existing `DND5E_NPC_TEMPLATES`, `COSMERE_NPC_TEMPLATES`)
- Grid intrusion hazard tables
**Dependencies that exist:** `CBRPNKEngine` has `heat` and `glitch_die` fields for encounter scaling

---

## SYSTEM 6: Data Integrity

### Stub 6A: `codex/core/memory.py` — Legacy Format Handler
**Current state:** `CodexMemoryEngine.load_from_disk()` has an `else` branch at line 611 that sets `self.shards = []` with comment "Currently no legacy format defined, so this is a placeholder"
**Risk:** An old save file would silently load as empty with no warning
**What's missing:** Either a format version header check with migration logic, or at minimum a warning log when encountering unknown format

---

## SYSTEM 7: Zone Generation

### Stub 7A: `codex/games/burnwillow/zone1.py` — `TangleGenerator` Top-Level Usage
**Current state:** `TangleGenerator.__init__` is `pass`. The class `generate_zone()` method works, but the class is never referenced at the top level — `play_burnwillow.py` calls `engine.generate_dungeon()` directly.
**Intended purpose:** High-level convenience class for zone generation that could be used as an entry point or factory
**What's missing:** Either wire `TangleGenerator` as the top-level API for zone generation, or remove the class and keep just `TangleAdapter`

---

## Priority Matrix

| Priority | Stub | Effort | Impact |
|---|---|---|---|
| HIGH | 2A-2E: FITD handle_command() | Medium | Enables all FITD Discord dropdowns |
| HIGH | 3A: HybridGameOrchestrator | Medium | Unlocks multi-engine sessions |
| HIGH | 4A-4D: Narrative Loom wiring | Low-Medium | Enables AI narrative synthesis |
| MEDIUM | 1A: Cartography generation | Medium | PDF-to-map pipeline |
| MEDIUM | 5A: CBR+PNK encounters | Medium | Complete encounter system |
| LOW | 6A: Legacy format handler | Low | Data safety |
| LOW | 7A: TangleGenerator usage | Low | API cleanliness |

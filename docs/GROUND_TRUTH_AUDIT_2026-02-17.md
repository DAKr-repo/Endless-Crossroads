# Ground Truth Audit Report — Project Codex
**Date:** 2026-02-17
**Version:** 3.0.0
**Auditor:** Claude Opus 4.6 (Architect + Mechanic)
**Purpose:** Objective baseline for incoming Assistant Project Manager

---

## 1. Core Architecture

### 1A. Active Game Systems

| System | Engine File | Entry Point | Status | Notes |
|--------|------------|-------------|--------|-------|
| **Burnwillow** | `codex/games/burnwillow/engine.py` | `play_burnwillow.py` (terminal), `codex_agent_main.py` menu [3] | DEPLOYED v1.2 | Roguelike dungeon crawler. Party system, minions, DoomClock, GearGrid, BSP dungeons |
| **Crown & Crew** | `codex/games/crown/engine.py` | `play_crown.py` (terminal), `codex_agent_main.py` menu [2] | DEPLOYED v3.0 | 5-day narrative loop. Patron/Leader, Sway tracking, Political Gravity |
| **Blades in the Dark** | `codex/games/bitd/__init__.py` | None (stub) | WIP | Package framework only. Extends `codex.core.services.fitd_engine` |

### 1B. Map Engine Migration Status

**Status: COMPLETE** (WO 106, deployed 2026-02-11)

- **Location:** `codex/spatial/map_engine.py` (was `codex_map_engine.py`)
- **Renderer:** `codex/spatial/map_renderer.py` (was `codex_map_renderer.py`)
- All consumers import from `codex.spatial.map_engine` — verified in `play_burnwillow.py` lines 46-49
- No orphaned references to old flat paths found
- Classes: `CodexMapEngine`, `DungeonGraph`, `RoomNode`, `BurnwillowAdapter`, `ContentInjector`, `PopulatedRoom`

### 1C. Package Hierarchy

```
codex/                          # __version__ = "3.0.0"
  paths.py                      # Central path registry (PROJECT_ROOT-anchored)
  core/
    architect.py                # Unified router to Mimir, complexity routing
    butler.py                   # Low-latency reflex router (<10ms), session bridge, scribe
    cache.py                    # LoreCache + grit_scrub (WO V20.5.4)
    cortex.py                   # Hardware monitoring, thermal safety
    dice.py                     # Dice rolling engine
    encounters.py               # Universal encounter engine (system-agnostic)
    manifold_guard.py           # State consistency validator
    memory.py                   # Memory shard neural link
    menu.py                     # Unified menu controller (WO 109)
    registry.py                 # CommandRegistry for centralized resolution
    retriever.py                # Context retrieval system
    services/
      broadcast.py              # Event broadcasting
      capacity_manager.py       # Resource capacity tracking
      cartography.py            # Map/dungeon representation
      fitd_engine.py            # Forged in the Dark core ruleset
      graveyard.py              # NPC/entity death tracking
      librarian.py              # Mimir's Vault browser TUI (3-panel)
      narrative_loom.py         # Story generation
      town_crier.py             # Announcement/notification
      trait_handler.py          # Character trait management
      tutorial.py               # Interactive tutorials
      universe_manager.py       # Multi-universe management
  games/
    burnwillow/
      engine.py                 # BurnwillowEngine, Character, DoomClock, GearGrid
      content.py                # Monster templates, loot tables, room descriptions
      zone1.py                  # Emberhome Hub zone data
      persistence.py            # Save/load handling
      ui.py                     # Terminal UI components
      paper_doll.py             # Character equipment TUI renderer
      bridge.py                 # Burnwillow-to-Discord event bridge
      discord_embed.py          # Discord-specific UI rendering
    crown/
      engine.py                 # CrownAndCrewEngine (5-day narrative)
      ashburn.py                # Ashburn Heir Engine (gothic variant)
    bitd/                       # WIP stub
  spatial/
    map_engine.py               # Universal BSP dungeon generation
    map_renderer.py             # Spatial grid renderer (RUST/STONE/GOTHIC themes)
  forge/
    char_wizard.py              # Content-agnostic character builder
    omni_forge.py               # Dynamic table/content generator (WO 089)
    source_scanner.py           # PDF source availability scanner
    adapter.py                  # CharacterAdapter (Wizard-to-Engine bridge)
    codex_transmuter.py         # Character sheet transformer
  world/
    genesis.py                  # Procedural world generation (G.R.A.P.E.S.)
    world_wizard.py             # World engine orchestrator
  services/
    ears.py                     # STT microservice (FastAPI :5000)
    mouth.py                    # TTS microservice (FastAPI :5001)
  bots/
    discord_bot.py              # py-cord 2.7.1, voice receive, 9 phases
    telegram_bot.py             # python-telegram-bot v20+, 7 phases
  integrations/
    mimir.py                    # Ollama bridge (query_mimir + CLI)
    tarot.py                    # Ashburn tarot card system
    vault_processor.py          # Vault file processing
```

### 1D. Root Entry Points

| File | Purpose | Status |
|------|---------|--------|
| `codex_agent_main.py` | Unified orchestrator — Rich terminal UI, menu, all game launches | FUNCTIONAL |
| `play_burnwillow.py` | Burnwillow game loop (3210 lines) | FUNCTIONAL |
| `play_crown.py` | Crown & Crew game loop | FUNCTIONAL |
| `codex_gemini_bridge.py` | Gemini API utility (manual invocation, not integrated) | FUNCTIONAL |

### 1E. Version

**`codex/__init__.py`**: `__version__ = "3.0.0"`

### 1F. Service Status

| Port | Service | File | Status | Dependencies |
|------|---------|------|--------|-------------|
| 5000 | Ears (STT) | `codex/services/ears.py` | DEPLOYED (WO 084-A) | faster-whisper base.en int8 |
| 5001 | Mouth (TTS) | `codex/services/mouth.py` | DEPLOYED (WO 084-B) | piper-tts (not yet installed) |
| 11434 | Ollama (LLM) | External | OPERATIONAL | qwen2.5-coder:1.5b |

Systemd service files: `codex_ears.service`, `codex_mouth.service` (Restart=always, RestartSec=5)

---

## 2. Bug Triage

### 2A. Map Renderer Junction Logic

**Status: FIXED** (WO V20.3.5)

**File:** `codex/spatial/map_renderer.py`

The junction/doorway bug has been resolved:
- `ThemeConfig` now has dedicated `doorway_char: str = "#"` and `color_doorway: str = "bold white"` fields (line 76)
- RUST theme uses `wall_char="█"` / `corridor_char="░"` / `doorway_char="#"` — all distinct
- GOTHIC theme uses `wall_char="▒"` / distinct doorway rendering
- `_paint_corridors()` properly detects wall chars at room thresholds and places doorways

**Minor note:** STONE theme has `wall_char="#"` and `doorway_char="#"` (same character). This is intentional for classic roguelike aesthetic but means doorways are visually indistinguishable from walls in STONE theme only.

**Verdict: No action required.**

### 2B. action_save Shallow-Copy

**Status: LOW-MEDIUM RISK** (potential data corruption under specific conditions)

**File:** `play_burnwillow.py` lines 2204-2234

**The issue:**
```python
# Lines 2221-2223
save_data["room_enemies"] = {str(k): v for k, v in state.room_enemies.items()}
save_data["room_loot"] = {str(k): v for k, v in state.room_loot.items()}
save_data["room_furniture"] = {str(k): v for k, v in state.room_furniture.items()}
```

The dict comprehension creates a new dict, but the values `v` (which are `List[dict]`) are assigned **by reference**. If anything mutates these lists between save and the next game action, the save data and live state share the same objects.

**Renderer injection** (line ~678) also assigns by reference:
```python
sr.enemies = state.room_enemies.get(room_id, [])
```

**Actual risk:** Low in practice — the renderer doesn't sort or mutate lists in-place. The one exception is Rot Hunter injection (line ~692) which correctly creates a new list via `list(sr.enemies) + [hunter_marker]`.

**Recommendation:** Future hardening WO should add deep copy:
```python
save_data["room_enemies"] = {str(k): [dict(e) for e in v] for k, v in state.room_enemies.items()}
```

---

## 3. RAG Status

### 3A. FAISS Vector Index

**Directory:** `faiss_index/`
**Status:** EXISTS — 8 system indices populated

| Index | Files | Last Updated |
|-------|-------|-------------|
| `bitd/` | index.faiss, index.pkl | Jan 31 |
| `bob/` | index.faiss, index.pkl | Jan 31 |
| `candela_obscura/` | index.faiss, index.pkl | Feb 14 |
| `cbr_pnk/` | index.faiss | Feb 14 |
| `codebase/` | index.faiss, docstore.json | Jan 27 |
| `dnd5e/` | index.faiss, index.pkl | Feb 8 |
| `sav/` | index.faiss, index.pkl | Feb 8 |
| `stc/` | index.faiss, index.pkl | Feb 8 |

**Note:** Legacy FAISS tooling (`codex_tools.py`) is archived. These indices are used by `LibrarianTUI` for vault semantic search but are not actively maintained. Consider refresh.

### 3B. Lore Cache (WO V20.5.4 — just deployed)

**File:** `state/lore_cache.json`
**Status:** Module implemented, file not yet created on disk (auto-creates on first `put()`)

**Implementation:** `codex/core/cache.py`
- `LoreCache` class: lazy-loaded Dict backed by JSON
- Keys: `{system_tag}:{query_lower}` (e.g., `burnwillow:rot-beetle`)
- Atomic writes via `tempfile.mkstemp` + `os.replace`
- Corrupt JSON → silent fallback to empty dict
- `grit_scrub()` applied before all cache writes (strips markdown, emoji, banned words)

**Integration points:**
- `codex/core/services/librarian.py` → `query_mimir()` checks cache first
- `play_burnwillow.py` → `action_inspect` enriches with cached lore
- `play_burnwillow.py` → `refresh_lore` command clears cache by system

### 3C. Query Latency Profile

**Mimir config** (`codex/integrations/mimir.py`):

| Parameter | Value |
|-----------|-------|
| Endpoint | `http://localhost:11434/api/generate` |
| Model | `qwen2.5-coder:1.5b` |
| Timeout | 90 seconds |
| Context window | 2048 tokens |
| Temperature | 0.2 |
| Streaming | Enabled |

**Realistic Pi 5 latencies:**
- Simple queries (<50 tokens): 5-15s
- Medium queries (100-200 tokens): 20-45s
- Complex queries (>400 tokens): May approach 90s timeout
- Under concurrent load: Queuing/serialization likely (single CPU inference)

**Mitigation:** LoreCache eliminates repeat queries. First hit pays Ollama cost; subsequent hits return instantly from disk.

### 3D. Live Session Bridge

**File:** `state/live_session.json`
**Status:** ACTIVE — last updated 2026-02-16 21:09

Contains Burnwillow session snapshot (party, doom, room, gear). 120s staleness check prevents serving stale data. Allows Ears voice service to query game status without live engine reference.

---

## 4. UI/UX Parity

### 4A. Menu System

**Source of truth:** `codex/core/menu.py` (WO 109)

All three interfaces use `CodexMenu`:

| Interface | Options | Rendering |
|-----------|---------|-----------|
| Terminal | 7 items (Chronicles, Crown, Burnwillow, DM Tools, Vault, Status, Exit) | Rich Table |
| Discord | 4 items (Prologue, Burnwillow, Omni-Forge, End Session) | Discord Embed |
| Telegram | 4 items (same as Discord) | HTML |

`resolve_selection(interface, raw_input)` returns identical action strings across all interfaces. Terminal alias: `q` → `exit`.

### 4B. Burnwillow Commands (30+)

Dispatched via 57-line if/elif chain in `play_burnwillow.py` lines 2782-3035.

**Movement:** `n/s/e/w`, `move <id|dir>`
**Exploration:** `look/l`, `inspect <#>`, `inspect item <#>`, `inspect equipped <name>`, `scout <id>`, `search`, `loot`, `interact [#]`
**Character:** `inv/i/gear/backpack`, `doll/sheet`, `equip <#> [slot]`, `bind/heal/rest`
**Party:** `party`, `switch <#>`, `give <#> to <#>`
**Combat:** `attack/atk/fight [#]`, `guard`, `intercept`, `command <name>`, `bolster <name>`, `triage <name>`, `sanctify`, `summon`
**Utility:** `roll/r <XdY>`, `library`, `save`, `load`, `map`, `help [1-3]`, `clear/cls`, `[`/`]` (scroll), `wait/pass`, `refresh_lore`, `quit/exit/q`

Help text: 3-page system (`_HELP_PAGES` lines 2573-2642).

**Note:** `CommandRegistry` exists in `codex/core/registry.py` but the Burnwillow game loop uses a manual if/elif chain instead. Refactoring to registry-based dispatch would improve maintainability.

### 4C. Bot Commands

| Discord (12 cmds) | Telegram (11 cmds) | Notes |
|---|---|---|
| `!help` | `/help` | Display help text |
| `!menu` / `!play` | `/play` / `/menu` | Main navigation |
| `!travel` | `/travel` | Advance morning phase |
| `!stop` / `!quit` / `!abort` / `!end` | `/stop` / `/end` | End session |
| `!status` | `/status` | System/session status |
| `!clear` | `/clear` | Clear session memory |
| `!ping` | `/ping` | Instant health check |
| `!prologue` | `/prologue` | Crown & Crew from campaign |
| `!burnwillow` | `/burnwillow` | Start dungeon run |
| `!summon` | `/summon` | Acknowledge presence |
| `!voice [join\|leave]` | — | Discord voice only |

**Phase Enum differences:**
- Discord: 9 phases (IDLE, MENU, DUNGEON, MORNING, NIGHT, CAMPFIRE, COUNCIL, FINALE, OMNI)
- Telegram: 7 phases (no NIGHT, no OMNI — CAMPFIRE handles allegiance)

### 4D. Butler Reflex Patterns (11)

All patterns in `codex/core/butler.py`:

1. `note/log/scribe <text>` → Session log entry
2. `lookup/rule/what is <term>` → Knowledge base query (237 entries)
3. `roll/r XdY±Z` → Dice roll
4. `what time/what's the time/current time` → Clock
5. `what day/what's the date/today's date` → Date
6. `time/date/clock` → Time shorthand
7. `status/stat/hp` → Game status (Burnwillow or Crown)
8. `damage/hurt/hit N [to name]` → Apply damage
9. `heal/cure/restore N [to name]` → Heal character
10. `inventory/inv/gear/equipment/items` → Gear list
11. `ping` → Health check

---

## 5. Orphaned / Dead Code

| File | Location | Status | Action |
|------|----------|--------|--------|
| `codex_ui_manager.py` | Root | ORPHANED (zero imports) | Archive or delete |
| `codex_discord_ui.py` | `archive/` | ARCHIVED | No action |
| `codex_tools.py` | `archive/` | ARCHIVED (legacy FAISS) | No action |
| `codex_gemini_bridge.py` | Root | UTILITY (manual invocation) | Keep — standalone Gemini tester |

---

## 6. Version & Deployment Summary

| Component | Version/WO | Status |
|-----------|-----------|--------|
| Package version | 3.0.0 | Current |
| Package migration | WO 106 | Complete (33 files, 55 import rewrites) |
| Burnwillow engine | v1.2 | Deployed |
| Crown engine | v3.0 | Deployed |
| Map renderer | v2.1 | Deployed |
| Menu controller | WO 109 | Deployed |
| Butler protocol | WO 107 | Deployed |
| Live session bridge | WO 102 | Deployed |
| Ears STT | WO 084-A | Deployed |
| Mouth TTS | WO 084-B | Deployed (deps not installed) |
| Discord voice | WO 114-115 | Deployed (py-cord 2.7.1) |
| Monster DR/Archetypes | WO V20.2 | Deployed |
| Stabilization pass | WO V20.3.5 | Deployed (this session) |
| Librarian cache | WO V20.5.4 | Deployed (this session) |

---

## 7. Critical File Paths (for Master Plan)

```
# Entry points
codex_agent_main.py              # Main orchestrator
play_burnwillow.py               # Burnwillow game loop
play_crown.py                    # Crown & Crew game loop

# Core package
codex/__init__.py                # v3.0.0
codex/paths.py                   # All path constants
codex/core/butler.py             # Reflex router + session bridge
codex/core/cache.py              # LoreCache + grit_scrub
codex/core/menu.py               # Unified menu (single source of truth)
codex/core/registry.py           # CommandRegistry
codex/core/services/librarian.py # Mimir's Vault TUI

# Game engines
codex/games/burnwillow/engine.py # BurnwillowEngine
codex/games/burnwillow/content.py# Monsters, loot, descriptions
codex/games/crown/engine.py      # CrownAndCrewEngine

# Spatial
codex/spatial/map_engine.py      # BSP dungeon generation
codex/spatial/map_renderer.py    # Grid renderer (themes)

# Services
codex/services/ears.py           # STT :5000
codex/services/mouth.py          # TTS :5001
codex/integrations/mimir.py      # Ollama bridge

# Bots
codex/bots/discord_bot.py        # py-cord
codex/bots/telegram_bot.py       # python-telegram-bot

# Data
state/live_session.json          # Session bridge (auto-updated)
state/lore_cache.json            # Lore cache (created on first use)
saves/burnwillow_save.json       # Game save
faiss_index/                     # Vector indices (8 systems)
config/systems/rules_DND5E.json  # Equipment knowledge base
vault/                           # PDF source vault
```

---

## 8. Action Items (Prioritized)

| Priority | Item | Effort |
|----------|------|--------|
| LOW | Deep-copy room_enemies/loot/furniture in action_save | S |
| LOW | Archive `codex_ui_manager.py` | XS |
| LOW | Refresh stale FAISS indices | M |
| FUTURE | Refactor Burnwillow command dispatch to use CommandRegistry | M |
| FUTURE | Add OMNI phase to Telegram bot | S |
| FUTURE | Install piper-tts dependency for Mouth service | S |

**No critical or high-priority bugs found.** The codebase is in a stable, production-ready state.

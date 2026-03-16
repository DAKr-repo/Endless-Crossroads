# SYSTEM MANIFEST — TOTAL V1.0

> **Project:** C.O.D.E.X. (Codex of Chronicles)
> **Date:** 2026-02-21
> **Scope:** 100% recursive audit of all `.py`, `.json`, and config files
> **Method:** Independent source-level extraction — no assumptions from prior documentation
> **Version:** `codex.__version__ = "3.0.0"`

---

## Table of Contents

1. [Directory Map & File Inventory](#1-directory-map--file-inventory)
2. [Package Architecture & Dependency Hub](#2-package-architecture--dependency-hub)
3. [Engine Logic — All Systems](#3-engine-logic--all-systems)
4. [State Serialization Schemas](#4-state-serialization-schemas)
5. [Cross-Platform Handoff Map](#5-cross-platform-handoff-map)
6. [Module Catalog](#6-module-catalog)
7. [Ghost Audit — Orphans, Stubs, Dead Code](#7-ghost-audit--orphans-stubs-dead-code)
8. [Volo Legacy Check](#8-volo-legacy-check)
9. [Test Coverage Map](#9-test-coverage-map)

---

## 1. Directory Map & File Inventory

### 1.1 Package Tree

```
codex/                          # Root package (__version__ = "3.0.0")
├── __init__.py                 # 12 lines — version + docstring
├── paths.py                    # 67 lines — central path registry (THE dependency hub)
│
├── bots/                       # Platform interface layer
│   ├── __init__.py             # empty
│   ├── discord_bot.py          # 2,793 lines — Discord interface v3.1
│   ├── telegram_bot.py         # 1,290 lines — Telegram interface (python-telegram-bot v20+)
│   └── scryer.py               # 242 lines — Rich→PNG screenshot engine (pyte + Pillow)
│
├── core/                       # Brain + shared services
│   ├── __init__.py             # empty
│   ├── architect.py            # ~180 lines — LLM router with thermal gating
│   ├── butler.py               # ~375 lines — reflex handler chain (13+ reflexes)
│   ├── cache.py                # ~90 lines — session cache (JSON, TTL)
│   ├── cortex.py               # ~286 lines — thermal monitor + persona loader
│   ├── dice.py                 # ~115 lines — universal dice roller
│   ├── dm_tools.py             # ~160 lines — encounter generator + DM utilities
│   ├── encounters.py           # ~269 lines — EncounterEngine + EncounterContext
│   ├── engine_protocol.py      # ~120 lines — GameEngine/DiceEngine/PartyEngine protocols
│   ├── manifold_guard.py       # ~90 lines — state consistency verifier
│   ├── memory.py               # ~324 lines — shard-based memory engine
│   ├── menu.py                 # ~76 lines — terminal menu dispatcher
│   ├── narrative_content.py    # ~1,129 lines — static NPC/quest/haven templates
│   ├── narrative_engine.py     # ~625 lines — quest tracker + NPC dialogue
│   ├── registry.py             # ~272 lines — command definition + alias resolution
│   ├── retriever.py            # ~90 lines — FAISS-backed RAG retriever
│   ├── state_frame.py          # ~326 lines — frozen game snapshot dataclass
│   │
│   ├── mechanics/
│   │   ├── __init__.py         # 1 line
│   │   ├── clock.py            # ~131 lines — UniversalClock (DoomClock + FactionClock)
│   │   └── orchestrator.py     # ~433 lines — multi-engine session manager + CRS gating
│   │
│   ├── services/
│   │   ├── __init__.py         # 1 line
│   │   ├── broadcast.py        # ~186 lines — thread-safe observer event bus
│   │   ├── capacity_manager.py # ~64 lines — weight/slot encumbrance check
│   │   ├── cartography.py      # ~266 lines — BSP map generation bridge
│   │   ├── fitd_engine.py      # ~279 lines — shared FITD d6-pool core
│   │   ├── graveyard.py        # ~177 lines — persistent character memorial
│   │   ├── librarian.py        # ~400+ lines — three-panel knowledge browser TUI
│   │   ├── narrative_loom.py   # ~215 lines — cross-shard narrative synthesis
│   │   ├── npc_memory.py       # ~481 lines — NPC persistent memory + BiasLens
│   │   ├── town_crier.py       # ~563 lines — civic event engine + rumor generator
│   │   ├── trait_handler.py    # ~145 lines — ABC trait resolver dispatcher
│   │   ├── tutorial.py         # ~200+ lines — contextual hint + tutorial browser
│   │   ├── tutorial_content.py # ~500+ lines — 21 tutorial modules across 5 categories
│   │   ├── universe_manager.py # ~164 lines — universe namespace isolation
│   │   ├── mimir_persona.json  # 38 lines — Mimir persona config (Norse Skald)
│   │   └── spatial/
│   │       └── __init__.py     # ~26 lines — re-exports from codex.spatial.*
│   │
│   └── world/
│       ├── __init__.py         # 43 lines — re-exports all world types
│       ├── grapes_engine.py    # ~566 lines — G.R.A.P.E.S. world generator
│       ├── grapes_templates.json # ~500+ lines — 15 entries × 9 categories
│       └── world_ledger.py     # ~329 lines — world mutation tracker + chronology
│
├── forge/                      # Content generation + character building
│   ├── __init__.py             # empty
│   ├── adapter.py              # 9 lines — backward-compat re-export shim
│   ├── char_wizard.py          # 945 lines — content-agnostic character builder
│   ├── codex_transmuter.py     # 288 lines — cross-system character translation
│   ├── loot_tables.py          # 388 lines — deterministic SRD loot tables
│   ├── omni_forge.py           # 98 lines — table roller (deterministic first, AI fallback)
│   └── source_scanner.py       # 100 lines — vault PDF/source scanner
│
├── games/                      # Game-specific engines
│   ├── __init__.py             # empty
│   ├── bridge.py               # 640 lines — UniversalGameBridge (protocol-generic)
│   │
│   ├── burnwillow/
│   │   ├── __init__.py         # empty
│   │   ├── engine.py           # 2,182 lines — BurnwillowEngine + Character + GearGrid
│   │   ├── bridge.py           # 968 lines — BurnwillowBridge (Burnwillow-specific)
│   │   ├── content.py          # 892 lines — enemy/loot/hazard/room tables
│   │   ├── zone1.py            # 712 lines — The Tangle biome adapter
│   │   ├── ui.py               # 829 lines — Rich UI components (legacy)
│   │   ├── paper_doll.py       # 257 lines — Rich character sheet renderer
│   │   ├── discord_embed.py    # 265 lines — Discord embed converters
│   │   └── atmosphere.py       # 271 lines — thermal narrative modifier
│   │
│   ├── crown/
│   │   ├── __init__.py         # empty
│   │   ├── engine.py           # 1,420 lines — CrownAndCrewEngine (narrative campaign)
│   │   ├── ashburn.py          # 844 lines — AshburnHeirEngine (corruption variant)
│   │   └── quests.py           # 1,537 lines — 7 quest archetypes
│   │
│   ├── bitd/__init__.py        # BitDEngine (FITD family)
│   ├── sav/__init__.py         # SaVEngine (FITD family)
│   ├── bob/__init__.py         # BoBEngine (FITD family)
│   ├── cbrpnk/__init__.py      # CBRPNKEngine (FITD family)
│   ├── candela/__init__.py     # CandelaEngine (ILLUMINATED_WORLDS family)
│   ├── dnd5e/__init__.py       # DnD5eEngine (DND5E family)
│   └── stc/__init__.py         # CosmereEngine (STC family)
│
├── integrations/               # External service adapters
│   ├── __init__.py             # empty
│   ├── mimir.py                # 301 lines — Ollama REST wrapper + context builder
│   ├── tarot.py                # 267 lines — 5 symbolic tarot cards (Rich + text)
│   └── vault_processor.py      # 667 lines — PDF equipment extractor
│
├── services/                   # Hardware microservices
│   ├── __init__.py             # empty
│   ├── ears.py                 # 274 lines — FastAPI STT on port 5000 (faster-whisper)
│   ├── mouth.py                # 275 lines — FastAPI TTS on port 5001 (Piper)
│   └── voice_bridge.py         # 316 lines — unified voice synthesis bridge
│
├── spatial/                    # Procedural map generation + rendering
│   ├── __init__.py             # empty
│   ├── map_engine.py           # 1,373 lines — BSP dungeon generator (geometry only)
│   ├── map_renderer.py         # 818 lines — Rich 2D map renderer (5 themes)
│   ├── player_renderer.py      # 345 lines — player-safe Rich Layout
│   └── blueprints/
│       └── emberhome.json      # 32 lines — static 8-room settlement blueprint
│
├── stubs/                      # Offline SDK stubs
│   ├── __init__.py             # 7 lines — re-exports install_discord_stubs
│   └── discord_stub.py         # ~300 lines — comprehensive discord.py stub
│
└── world/                      # World creation tools
    ├── __init__.py             # empty
    ├── genesis.py              # 495 lines — procedural world generator
    └── world_wizard.py         # 1,424 lines — terminal world creation wizard
```

### 1.2 Root-Level Python Files

| File | Lines | Status | Purpose |
|------|-------|--------|---------|
| `codex_agent_main.py` | ~3,514 | **ACTIVE** | Primary entry point — terminal UI + embedded Discord fallback |
| `play_burnwillow.py` | ~4,030 | **ACTIVE** | Terminal roguelike game loop |
| `play_crown.py` | 313 | **ACTIVE** | Terminal Crown & Crew campaign loop |
| `play_player_view.py` | 94 | **ACTIVE** | External HDMI monitor display |
| `codex_gemini_bridge.py` | 89 | **ORPHANED** | Standalone Gemini API client (predates `gemini` CLI) |
| `codex_ui_manager.py` | ~780 | **ORPHANED** | Rendering abstraction layer (never wired) |
| `optimize_context.py` | ~300 | **ORPHANED** | Token budget manager (never integrated into Mimir) |

### 1.3 Config Files

| File | Purpose | Runtime Consumer |
|------|---------|-----------------|
| `config/entity_schema.json` | Cross-system item definitions (5 entities) | `trait_handler.py` via `load_entity_schema()` |
| `config/burnwillow_schema.json` | JSON Schema for run/meta state | **STALE STUB** — uses `Flow/Focus/Vigor` stats, not `Might/Wits/Grit/Aether` |
| `config/skald_lexicon.json` | Mimir quips (10 categories, 5-10 each) | Likely `burnwillow/` game events |
| `config/models/Modelfile.codex` | Ollama model: `qwen3:1.7b`, 8192 ctx | Build-time only (`ollama create`) |
| `config/models/ModelfileMimir` | Legacy Ollama model: `qwen2.5:0.5b`, 2048 ctx | Deprecated — backup only |
| `config/systems/rules_BITD.json` | Blades in the Dark system rules | `fitd_engine.py` / maintenance |
| `config/systems/rules_DND5E.json` | D&D 5e rules + SRD items | `loot_tables.py` via `refresh_from_vault()` |
| `config/systems/rules_BURNWILLOW.json` | **STALE STUB** — placeholder stats | Not consumed at runtime |
| `config/systems/rules_BOB.json` | Band of Blades rules | Maintenance scripts |
| `config/systems/rules_SAV.json` | Scum and Villainy rules | Maintenance scripts |
| `config/systems/rules_CANDELA*.json` | Candela Obscura rules (2 files) | Maintenance scripts |
| `config/systems/rules_CBR*.json` | CBR+PNK rules (2 files, naming collision) | Maintenance scripts |
| `config/systems/rules_STC.json` | Cosmere rules | Maintenance scripts |
| `config/systems/rules_GRAVEYARD.json` | Retired system definitions | Not consumed |
| `config/systems/dnd5e_encounters.json` | XP thresholds + CR tables (levels 1-20) | Likely `dm_tools.py` |

---

## 2. Package Architecture & Dependency Hub

### 2.1 The Dependency Hub: `codex/paths.py`

Every persistence-capable module imports from this file. It is the single source of truth for all filesystem paths.

```python
PROJECT_ROOT       = Path(__file__).resolve().parent.parent    # Codex/
STATE_DIR          = PROJECT_ROOT / "state"
SAVES_DIR          = PROJECT_ROOT / "saves"
VAULT_DIR          = PROJECT_ROOT / "vault"
VAULT_MAPS_DIR     = PROJECT_ROOT / "vault_maps"
CONFIG_DIR         = PROJECT_ROOT / "config"
WORLDS_DIR         = PROJECT_ROOT / "worlds"
MODELS_DIR         = PROJECT_ROOT / "models"
TEMPLATES_DIR      = PROJECT_ROOT / "templates"
LOGS_DIR           = PROJECT_ROOT / "gemini_sandbox" / "session_logs"

SESSION_STATE_FILE = STATE_DIR / "session_state.json"
SESSION_STATS_FILE = STATE_DIR / "session_stats.json"
BRIDGE_FILE        = STATE_DIR / "live_session.json"
LORE_CACHE_FILE    = STATE_DIR / "lore_cache.json"
WORLD_HISTORY_FILE = STATE_DIR / "world_history.json"
NPC_MEMORY_FILE    = STATE_DIR / "npc_memory.json"

DND5E_SOURCE_DIR   = VAULT_DIR / "dnd5e" / "SOURCE"
PIPER_MODEL_DIR    = MODELS_DIR / "piper"

def safe_save_json(filepath: Path, data: dict) -> None:
    # Atomic write with .bak rotation for crash safety
```

### 2.2 The Event Backbone: `GlobalBroadcastManager`

Thread-safe observer bus connecting Memory, NPC Memory, Town Crier, Cartography, and Bridge layers.

**Well-known event constants:**

| Constant | Value | Publishers | Subscribers |
|----------|-------|-----------|-------------|
| `EVENT_MAP_UPDATE` | `"MAP_UPDATE"` | Bridges (via `_emit_frame()`) | Discord bot, Telegram bot |
| `EVENT_HIGH_IMPACT` | `"HIGH_IMPACT_DECISION"` | Crown engine | Memory, NPC Memory (all NPCs) |
| `EVENT_TRAIT_ACTIVATED` | `"TRAIT_ACTIVATED"` | TraitHandler | NPC Memory (all NPCs) |
| `EVENT_FACTION_CLOCK_TICK` | `"FACTION_CLOCK_TICK"` | Town Crier | NPC Memory (informant/leader) |
| `EVENT_CIVIC_EVENT` | `"CIVIC_EVENT"` | Town Crier | NPC Memory (role-mapped) |
| `EVENT_NPC_WITNESS` | `"NPC_WITNESS"` | NPC Memory | (internal routing) |

### 2.3 The Lazy Import Pattern

Universal throughout the codebase for Pi 5 constraints. Heavy dependencies are imported inside method bodies or `try/except ImportError` blocks. This prevents startup failures when optional deps (FAISS, langchain, discord.py, faster-whisper) are not installed.

```python
# Canonical pattern (seen in 30+ files):
def some_method(self):
    try:
        from codex.integrations.mimir import query_mimir
    except ImportError:
        return fallback_value
```

### 2.4 Internal Dependency Graph

```
codex.paths ←── (nearly everything that persists data)
    ↑
codex.core.services.broadcast ←── (event producers + consumers)
    ↑
codex.core.memory ←── narrative_engine, npc_memory
    ↑
codex.core.world.grapes_engine ←── memory, genesis, encounters, npc_memory
    ↑
codex.core.world.world_ledger ←── librarian, chronology consumers
    ↑
codex.core.mechanics.clock ←── fitd_engine, grapes_engine, orchestrator, burnwillow
    ↑
codex.core.engine_protocol ←── fitd_engine, all 7 registered engines
    ↑
codex.core.services.fitd_engine ←── bitd, sav, bob, cbrpnk, candela (composition, not inheritance)
```

### 2.5 The Two Thermal Tiers

| Layer | Module | Role |
|-------|--------|------|
| **IF** gate | `codex.core.cortex` | ThermalStatus (GREEN/YELLOW/RED/CRITICAL), CPU/GPU temp monitoring via psutil/vcgencmd |
| **HOW** route | `codex.core.architect` | Complexity analysis → model selection → Ollama HTTP call with thermal clearance check |

---

## 3. Engine Logic — All Systems

### 3.1 Burnwillow (Roguelike Dungeon Crawler)

**Engine:** `codex/games/burnwillow/engine.py` (2,182 lines)
**Bridge:** `codex/games/burnwillow/bridge.py` (968 lines)
**Terminal:** `play_burnwillow.py` (4,030 lines)

#### Turn Sequence
1. Room entry → `_check_room_encounter()` (ambush check: Wits vs enemy passive DC)
2. Combat or explore
3. Player action (move/search/attack/use/etc.)
4. Doom tick → wave check → roamer advancement

#### Stats & Character Model

| Stat | Type | HP Formula |
|------|------|-----------|
| Might | Primary | `max_hp = 10 + grit_mod` |
| Wits | Primary | |
| Grit | Primary | |
| Aether | Primary | |

**Gear Slots (10):** HEAD, SHOULDERS, CHEST, ARMS, LEGS, R_HAND, L_HAND, R_RING, L_RING, NECK
**Wildcard Slots:** SHOULDERS, NECK, R_RING, L_RING (accept any stat)
**Gear Tiers:** 0-4 (TIER_0 through TIER_IV)
**Difficulty Classes:** ROUTINE=8, HARD=12, HEROIC=16, LEGENDARY=20

#### Doom Clock
- Thresholds: `{5, 10, 13, 15, 17, 20, 22}`
- Wave 1 (Doom 10): 2-3 stationary ambush enemies in unvisited rooms
- Wave 2 (Doom 15): 1-2 BFS roamers (every 2 doom ticks)
- Wave 3 (Doom 20): Rot Hunter — BFS pursuit every 1 doom tick

#### Pity Loot System
- Counter: `_turns_since_unique_loot` (increments per turn, resets on unique find)
- Trigger: After 12 dry turns → forces tier 2+ unique drop
- Formula: `min(4, max(2, player_tier + 1))`
- Seeded: `equip_loadout()` pre-seeds `_found_item_names` with 3 starter gear names

#### Loadouts

| ID | Gear Indices | Starter Items |
|----|-------------|---------------|
| sellsword | [0,1,3] | Rusted Shortsword, Padded Jerkin, Burglar's Gloves |
| occultist | [2,5,1] | — |
| sentinel | [0,4,1] | — |
| archer | [7,1] | — |
| vanguard | [8,1] | — |
| scholar | [9,10,3] | — |

#### Content Tables (`content.py`)

| Table | Tiers | Entries Per Tier |
|-------|-------|-----------------|
| ENEMY_TABLES | 4 | 5-6 enemies each |
| LOOT_TABLES | 4 | 14-18 items each |
| HAZARD_TABLES | 4 | 5 hazards each |
| ROOM_DESCRIPTIONS | 4 | 8 descriptions each |
| BOSS_TEMPLATES | 1 | 5 bosses |
| WAVE_ENEMIES | 2 | Wave 1: 2 types, Wave 2: 2 types |
| CONTENT_ARCHETYPES | — | beast/scavenger/aetherial/construct per enemy |
| CONTENT_DR_BY_TIER | 4 | {1:0, 2:1, 3:2, 4:3} |

**Bosses:** Hollowed Bear (25HP), The Rust King (50HP), The Blight Mother (60HP), The Clockwork Archon (45HP), The Void Herald (40HP)

#### BurnwillowTraitResolver (9 traits)

| Trait | Mechanic |
|-------|----------|
| SET_TRAP | Place trap in room |
| CHARGE | Rush attack bonus |
| SANCTIFY | Bless area (anti-blight) |
| RESIST_BLIGHT | Passive blight resistance |
| FAR_SIGHT | Extended vision |
| INTERCEPT | +DR until next hit (scales T1:+2 → T4:+5+reflect) |
| COMMAND | Wits DC 12, grant bonus damage |
| BOLSTER | Aether DC 10, +Nd6 on next roll (N = item tier, cap 3) |
| TRIAGE | Wits DC 12, heal Nd6 (N = item tier) |

---

### 3.2 Crown & Crew (Narrative Campaign)

**Engine:** `codex/games/crown/engine.py` (1,420 lines)
**Terminal:** `play_crown.py` (313 lines) + `codex_agent_main.py` async variant

#### Turn Sequence (per day)
1. `get_morning_event()` → sway-biased road encounter
2. `get_world_prompt()` → environment description
3. `declare_allegiance(side, tag)` → sway ±1
4. `get_prompt()` → crown/crew dilemma
5. `get_campfire_prompt()` → reflection (non-breach days only)
6. `get_council_dilemma()` → group vote
7. `resolve_vote(votes)` → weighted outcome
8. Rest choice → `trigger_long_rest()` / `trigger_short_rest()` / `skip_rest()`
9. `end_day()` → advance day counter

#### Sway Mechanics
- Range: -3 (full Crown) to +3 (full Crew)
- `declare_allegiance("crown")` → sway -= 1
- `declare_allegiance("crew")` → sway += 1
- `VOTE_POWER: {0: 1, 1: 2, 2: 4, 3: 8}` — exponential weight by |sway|
- `SWAY_TIERS: {-3..+3}` → alignment label + narrative tone

#### DNA Tags
5 tags: `BLOOD, GUILE, HEARTH, SILENCE, DEFIANCE`
- Auto-assigned via `AUTO_TAGS: {"crew": [...], "crown": [...]}`
- Tracked in `dna: Dict[str, int]`
- Dominant tag determines legacy title

#### Breach Day
- Formula: `max(1, round(arc_length * breach_day_fraction))`
- Default `breach_day_fraction = 0.6`
- Verified for arcs 3-10 (see QA Report)

#### Rest System
- **Long rest**: Advance day
- **Short rest**: Sway shift from morning event bias (1/day cap via `_short_rests_today`)
- **Skip rest**: Sway decays 1 toward 0

#### Content Pools
- `PATRONS`: 8 patron names
- `LEADERS`: 8 leader names
- `PROMPTS_CROWN/CREW/WORLD/CAMPFIRE`: 10 each
- `MORNING_EVENTS`: 10 sway-biased encounters (text/bias/tag)
- `COUNCIL_DILEMMAS`: 8 group vote scenarios (prompt/crown/crew)
- `LEGACY_TITLES`: keyed by (alignment, tag) pairs

---

### 3.3 Ashburn Heir (Crown Variant)

**Engine:** `codex/games/crown/ashburn.py` (844 lines)
**Extends:** `CrownAndCrewEngine` (dataclass inheritance)

#### 4 Heirs

| Key | Title | Mechanical Effect |
|-----|-------|-------------------|
| Lydia | — | Starts sway = 0 |
| Jax | — | Starts sway = 0 |
| Julian | The Gilded Son | Starts sway = -1 (Crown bias via `__post_init__`) |
| Rowan | — | Starts sway = 0 |

#### Corruption System
- `legacy_corruption: int` (0-5, 5 = game over)
- +1 on `resolve_legacy_choice(choice=1)` (Obey path)
- +2 on Lie detection
- `check_betrayal()` → 20% chance per opposite-side vote
- Betrayal Nullification: modifies `get_vote_power()`

#### Overridden Methods
- `__post_init__()` — sets heir-specific state, overrides prompt pools
- `get_prompt(side)` — uses Ashburn-specific pools (8 per side)
- `get_vote_power()` — applies Betrayal Nullification
- `to_dict()` — includes `legacy_corruption`, `heir_name`, `heir_leader`, `betrayal_triggered`

#### Known Gap
`generate_legacy_report()` is **inherited unchanged** from parent. Heir choice has mechanical consequences during play (sway offset, corruption) but NOT in the final report structure.

---

### 3.4 Quest Archetypes

**Module:** `codex/games/crown/quests.py` (1,537 lines)

7 self-contained narrative templates that reshape `CrownAndCrewEngine` via `world_state` injection.

| Slug | Name | Arc Length | Special Mechanics Keys |
|------|------|-----------|----------------------|
| `siege` | Siege Defense | 7 | `supply_track`, `wall_integrity`, `breach_day_override` |
| `summit` | Diplomatic Summit | 4 | `influence_track`, `leverage_tokens`, `private_meetings` |
| `trial` | Trial of the Accused | 5 | `evidence_track`, `testimony_slots`, `jury_opinion` |
| `caravan` | Caravan Expedition | 6 | `supply_track`, `water_per_day`, `terrain_hazard_chance` |
| `heist` | The Grand Heist | 3 | `heat_track`, `heat_max`, `crew_trust`, `noise_threshold` |
| `succession` | Succession Crisis | 5 | `faction_influence`, `noble_houses_declared`, `coronation_countdown` |
| `outbreak` | Outbreak Response | 5 | `infection_track`, `infection_max`, `cure_progress`, `cure_threshold`, `daily_spread` |

Each `QuestArchetype.to_world_state()` injects: `terms`, `prompts` (crown/crew/world/campfire), `council_dilemmas`, `morning_events`, `special_mechanics`.

---

### 3.5 FITD Shared Core

**Module:** `codex/core/services/fitd_engine.py` (279 lines)

Shared d6-pool resolution used by BitD, SaV, BoB, CBR+PNK, and Candela via **composition** (not inheritance).

#### FITDActionRoll
- Input: `dice_count`, `position` (CONTROLLED/RISKY/DESPERATE), `effect` (LIMITED/STANDARD/GREAT)
- Resolution: roll Nd6 → highest die determines outcome
  - 0 dice: roll 2d6, take lowest (disadvantage)
  - 1-3: failure, 4-5: mixed, 6: success, two+ 6s: critical
- Output: `FITDResult(outcome, highest, all_dice, position, effect, consequences)`

#### StressClock
- Fields: `current_stress` (0-9), `traumas` list, `max_traumas` (4)
- `push(amount)` → add stress, triggers trauma at overflow
- `resist(cost)` → spend stress to resist consequence
- `recover(amount)` → vice scene recovery
- Trauma tables: `FITD_DEFAULT_TRAUMAS` (8), `BOB_TRAUMAS` (7)

#### LegionState (Band of Blades only)
- Fields: `supply`, `intel`, `morale`, `pressure`
- `adjust(resource, amount)` → clamped mutation

---

### 3.6 ENGINE_REGISTRY — All 9 Registered Systems

| `system_id` | Engine Class | `system_family` | File | Uses StressClock | Uses LegionState | Has TraitResolver |
|-------------|-------------|-----------------|------|-----------------|-----------------|-------------------|
| `"fitd"` | `FITDActionRoll` | N/A (primitive) | `fitd_engine.py` | — | — | — |
| `"bitd"` | `BitDEngine` | `"FITD"` | `games/bitd/__init__.py` | Yes | No | No |
| `"sav"` | `SaVEngine` | `"FITD"` | `games/sav/__init__.py` | Yes | No | No |
| `"bob"` | `BoBEngine` | `"FITD"` | `games/bob/__init__.py` | Yes (BOB_TRAUMAS) | Yes | No |
| `"cbrpnk"` | `CBRPNKEngine` | `"FITD"` | `games/cbrpnk/__init__.py` | Yes | No | No |
| `"candela"` | `CandelaEngine` | `"ILLUMINATED_WORLDS"` | `games/candela/__init__.py` | No (Body/Brain/Bleed) | No | No |
| `"dnd5e"` | `DnD5eEngine` | `"DND5E"` | `games/dnd5e/__init__.py` | No | No | `DnD5eTraitResolver` |
| `"stc"` | `CosmereEngine` | `"STC"` | `games/stc/__init__.py` | No | No | `CosmereTraitResolver` |

**Note:** Burnwillow, Crown, and Ashburn use their own engines **outside** the registry.

#### Per-Engine Command Surface

| Engine | COMMANDS dict | CATEGORIES dict |
|--------|--------------|-----------------|
| BitD | `roll_action, crew_status, score_status, entanglement, party_status` | `Crew, Action` |
| SaV | `ship_status, ship_upgrade, set_course, roll_action, crew_status` | `Ship, Crew` |
| BoB | `legion_status, campaign_advance, supply_check, chosen_status, roll_action, squad_status` | `Legion, Squad` |
| CBR+PNK | `roll_action, crew_status, glitch_status, jack_in, party_status` | `Grid, Action` |
| Candela | `roll_action, circle_status, take_mark, party_status` | `Circle, Action` |
| DnD5e | **None defined** | **None defined** |
| Cosmere | **None defined** | **None defined** |

**CBR+PNK unique behavior:** `_cmd_roll_action` increments `glitch_die` on failure (only engine that mutates state in roll command).

---

### 3.7 Spatial Map System

**Engine:** `codex/spatial/map_engine.py` (1,373 lines) — BSP dungeon generator (geometry only)
**Renderer:** `codex/spatial/map_renderer.py` (818 lines) — Rich 2D map with 5 themes

#### Room Types (18)
`START, NORMAL, TREASURE, BOSS, CORRIDOR, SECRET, RETURN_GATE, HIDDEN_PORTAL, BORDER_CROSSING, TAVERN, FORGE, MARKET, TEMPLE, BARRACKS, TOWN_GATE, TOWN_SQUARE, LIBRARY, RESIDENCE`

#### Generation Modes
`DUNGEON, WILDERNESS, VERTICAL, SETTLEMENT`

#### System-Dispatched Room Types
- **Burnwillow:** RETURN_GATE at 25-50% BFS distance
- **DnD5e:** HIDDEN_PORTAL at 10% chance in deep rooms (≥50%)
- **Crown:** BORDER_CROSSING at ≥75% distance

#### Map Themes (5)
`RUST, STONE, GOTHIC, VILLAGE, CANOPY`

#### Static Blueprint
`codex/spatial/blueprints/emberhome.json` — Fixed 8-room settlement: town_square (hub), tavern, forge, barracks, market, town_gate, temple, library.

---

## 4. State Serialization Schemas

### 4.1 CrownAndCrewEngine.to_dict() — 28 keys

```
day, sway, patron, leader, history, dna, vote_log, arc_length,
rest_type, rest_config, terms, entities, threat, region, goal,
_used_crown, _used_crew, _used_world, _used_campfire, _used_morning, _used_dilemmas,
_council_dilemmas, quest_slug, quest_name, special_mechanics,
_morning_events, _short_rests_today
```

### 4.2 AshburnHeirEngine.to_dict() — 28 + 4 keys

Inherits all Crown keys plus: `legacy_corruption`, `heir_name`, `heir_leader`, `betrayal_triggered`

### 4.3 BurnwillowEngine.save_game() — nested dict

```
character:
  name, might, wits, grit, aether, current_hp, gear (GearGrid.to_dict()),
  inventory (dict of GearItem.to_dict()), keys

party: List[Character.to_dict()]

doom_clock:
  name, filled, max_segments, thresholds, mode

dungeon:
  graph (DungeonGraph.to_dict()), current_room_id, player_pos,
  visited_rooms, zone

civic_pulse: CivicPulse state
pity_counter: _turns_since_unique_loot
found_items: _found_item_names
first_strike_used: bool

wave state (in play_burnwillow.py GameState):
  wave_spawns, wave_dormancy, _wave_roam_counter
```

### 4.4 FITD Engine save_state() Pattern

All 5 FITD engines + DnD5e + Cosmere follow the same pattern:
```python
def save_state(self) -> Dict:
    return {
        "system_id": self.system_id,
        "characters": [c.to_dict() for c in self.party],
        "faction_clocks": [c.to_dict() for c in self._faction_clocks],
        # engine-specific fields...
    }
```

FITD-specific fields by engine:

| Engine | Extra Save Fields |
|--------|------------------|
| BitD | `heat`, `wanted_level`, `rep`, `coin`, `turf`, `crew_name`, `crew_type` |
| SaV | `heat`, `rep`, `coin`, `ship_name`, `ship_class` |
| BoB | `legion` (LegionState), `chosen`, `campaign_phase` |
| CBR+PNK | `heat`, `glitch_die` |
| Candela | `circle_name`, `assignments_completed` |
| DnD5e | `dungeon_graph`, `populated_rooms`, `player_pos`, `visited_rooms` |
| Cosmere | `dungeon_graph`, `populated_rooms`, `player_pos`, `visited_rooms` |

### 4.5 Backward Compatibility

Both Crown and Burnwillow engines use `setattr()` loops for tracked-set fields with `.get()` fallbacks:
```python
# Crown pattern:
for key in ("_used_crown", "_used_crew", ...):
    setattr(self, key, set(data.get(key, [])))

# Burnwillow pattern:
self._turns_since_unique_loot = data.get("pity_counter", 0)
self._found_item_names = set(data.get("found_items", []))
```

GearGrid has `_SLOT_MIGRATION` dict for corrupted save slot name aliases.

---

## 5. Cross-Platform Handoff Map

### 5.1 Crown & Crew

| Phase | Terminal (`play_crown.py`) | Discord (`discord_bot.py`) | Telegram (`telegram_bot.py`) |
|-------|---------------------------|---------------------------|------------------------------|
| Init | `CrownAndCrewEngine()` direct | `DiscordSession.start_game()` | `TelegramSession.start_game()` |
| Morning | `engine.get_morning_event()` → Rich Panel | Injected in world prompt | Injected in world prompt |
| World | `engine.get_world_prompt()` → tarot card | `handle_travel()` sends embed | `handle_travel()` sends text |
| Allegiance | `input()` → `declare_allegiance()` | `handle_allegiance()` via reactions | `handle_allegiance()` via text |
| Campfire | `engine.get_campfire_prompt()` → tarot | `handle_travel()` campfire path | `handle_travel()` campfire path |
| Council | `engine.get_council_dilemma()` → panel | `_format_council()` embed | `format_council()` text |
| Vote | `input()` → `resolve_vote()` | `handle_vote()` | `handle_vote()` |
| Rest | `input()` → long/short/skip | `handle_rest()` via buttons | `handle_message()` via text |
| Legacy | `generate_legacy_report()` → tarot card | `handle_vote()` finale path | `handle_vote()` finale path |
| Tarot | `render_tarot_card()` (Rich Panel) | `format_tarot_text()` (code block) | `format_tarot_text()` (code block) |

### 5.2 Burnwillow

| Phase | Terminal (`play_burnwillow.py`) | Discord (`discord_bot.py`) | Telegram |
|-------|-------------------------------|---------------------------|----------|
| Init | `BurnwillowEngine()` + `GameState` | `BurnwillowBridge.step()` | N/A |
| Commands | `input()` → dispatch dict | `GameCommandView` buttons + `on_message` | N/A |
| Movement | `action_move()` → map render | `bridge.step("move n")` → text | N/A |
| Combat | `run_combat_round()` loop | `bridge.step("attack")` → text | N/A |
| Map | `screen_refresh()` Rich Layout | `scryer.capture_rich()` → PNG | N/A |

### 5.3 Phase Enums

**Discord Phase (15 values):**
`IDLE, MENU, DUNGEON, MORNING, NIGHT, CAMPFIRE, COUNCIL, FINALE, OMNI, DND5E, COSMERE, REST, ASHBURN_HEIR, ASHBURN_LEGACY, QUEST_SELECT`

**Telegram Phase (14 values):**
`IDLE, MENU, DUNGEON, MORNING, CAMPFIRE, COUNCIL, FINALE, DND5E, COSMERE, REST, ASHBURN_HEIR, ASHBURN_LEGACY, QUEST_SELECT, OMNI`

**Divergence:** Discord has `NIGHT` phase (between MORNING and COUNCIL). Telegram goes directly `MORNING → CAMPFIRE → COUNCIL`.

### 5.4 Bridge Pattern

Two bridge types exist with no shared inheritance:

| Bridge | File | Engine | Command Surface |
|--------|------|--------|----------------|
| `UniversalGameBridge` | `games/bridge.py` | Any `GameEngine` protocol | 18 generic commands |
| `BurnwillowBridge` | `games/burnwillow/bridge.py` | `BurnwillowEngine` only | 18 Burnwillow-specific commands |

Both use `step(command: str) -> str` as the single dispatch entry point.
Both define `COMMAND_CATEGORIES` (class attr) for UI grouping.
Both use `_emit_frame()` to broadcast state via `GlobalBroadcastManager`.

### 5.5 Voice Pipeline

```
Discord voice → _UtteranceSink (PCM buffer)
    → VoiceListener._poll_loop()
    → WAV
    → EARS_URL /transcribe (port 5000, faster-whisper)
    → wake word check ("mimir", "volo", "codex", "computer")
    → Butler reflex or core.process_input()
    → response text
    → VoiceBridge.speak_discord()
    → queue (maxsize=16)
    → _drain_queue()
    → MOUTH_URL /speak (port 5001, Piper TTS)
    → WAV bytes → FFmpegPCMAudio
```

---

## 6. Module Catalog

### 6.1 Protocols & ABCs

| Protocol/ABC | Module | Attributes | Methods |
|-------------|--------|-----------|---------|
| `GameEngine` | `engine_protocol.py` | `system_id`, `system_family`, `display_name` | `get_status()`, `save_state()`, `load_state()` |
| `DiceEngine` | `engine_protocol.py` | — | `roll_check(**kwargs)` |
| `PartyEngine` | `engine_protocol.py` | `party: list` | `add_to_party()`, `remove_from_party()`, `get_active_party()` |
| `TraitResolver` | `trait_handler.py` | — | `resolve(trait_name, user, target, engine)` (abstract) |
| `RulesetAdapter` | `map_engine.py` | — | `populate_room(room)` |

### 6.2 All Enums

| Enum | Module | Values |
|------|--------|--------|
| `StatType` | `burnwillow/engine.py` | MIGHT, WITS, GRIT, AETHER |
| `GearSlot` | `burnwillow/engine.py` | HEAD, SHOULDERS, CHEST, ARMS, LEGS, R_HAND, L_HAND, R_RING, L_RING, NECK |
| `GearTier` | `burnwillow/engine.py` | TIER_0 through TIER_IV (0-4) |
| `DC` | `burnwillow/engine.py` | ROUTINE=8, HARD=12, HEROIC=16, LEGENDARY=20 |
| `ThermalTone` | `atmosphere.py` | 11 values: HOMECOMING through CANOPY_CROWN |
| `BiomeTag` | `zone1.py` | 10 values: ROOT_WALL through ROTWOOD_COLUMN |
| `RoomType` | `map_engine.py` | 18 room types |
| `Direction` | `map_engine.py` | N, S, E, W, NE, NW, SE, SW |
| `GenerationMode` | `map_engine.py` | DUNGEON, WILDERNESS, VERTICAL, SETTLEMENT |
| `MapTheme` | `map_renderer.py` | RUST, STONE, GOTHIC, VILLAGE, CANOPY |
| `RoomVisibility` | `map_renderer.py` | HIDDEN=0, UNEXPLORED=1, VISITED=2, CURRENT=3 |
| `ThermalStatus` | `cortex.py` | GREEN, YELLOW, RED, CRITICAL |
| `Complexity` | `architect.py` | LOW, MEDIUM, HIGH |
| `ThinkingMode` | `architect.py` | QUICK, DEEP |
| `ShardType` | `memory.py` | ECHO, ANCHOR |
| `CampaignPhase` | `narrative_engine.py` | HAVEN, JOURNEY, DELVE, AFTERMATH |
| `GuardVerdict` | `manifold_guard.py` | PASS, WARN, FAIL |
| `Position` | `fitd_engine.py` | CONTROLLED, RISKY, DESPERATE |
| `Effect` | `fitd_engine.py` | ZERO, LIMITED, STANDARD, GREAT, EXTREME |
| `CapacityMode` | `capacity_manager.py` | SLOTS, WEIGHT |
| `CapacityStatus` | `capacity_manager.py` | OK, WARNING, OVER_CAPACITY |
| `CivicCategory` | `town_crier.py` | TRADE, SECURITY, RUMOR, INFRASTRUCTURE, MORALE |
| `EventType` | `world_ledger.py` | WAR, DISCOVERY, CHRONICLE_ENDING, MUTATION, POLITICAL, ECONOMIC, SOCIAL, CIVIC, FACTION |
| `AuthorityLevel` | `world_ledger.py` | EYEWITNESS=1, CHRONICLE=2, LEGEND=3 |
| `Phase` (Discord) | `discord_bot.py` | 15 values |
| `Phase` (Telegram) | `telegram_bot.py` | 14 values |

### 6.3 All Dataclasses

| Dataclass | Module | Key Fields |
|-----------|--------|-----------|
| `CheckResult` | `burnwillow/engine.py` | success, total, rolls, modifier, dc |
| `GearItem` | `burnwillow/engine.py` | name, slot, tier, stat_bonuses, damage_reduction, special_traits, two_handed, weight |
| `GearGrid` | `burnwillow/engine.py` | slots: Dict[GearSlot, Optional[GearItem]] |
| `Character` | `burnwillow/engine.py` | name, might, wits, grit, aether, gear, inventory, keys |
| `Minion(Character)` | `burnwillow/engine.py` | is_minion=True, summon_duration=3 |
| `CrownAndCrewEngine` | `crown/engine.py` | day, sway, patron, leader, history, dna, arc_length, terms, ... (28+ fields) |
| `AshburnHeirEngine` | `crown/ashburn.py` | (extends Crown) + legacy_corruption, heir_name, betrayal_triggered |
| `QuestArchetype` | `crown/quests.py` | name, slug, arc_length, terms, prompts, council_dilemmas, special_mechanics |
| `FITDResult` | `fitd_engine.py` | outcome, highest, all_dice, position, effect, consequences |
| `FITDActionRoll` | `fitd_engine.py` | dice_count, position, effect |
| `StressClock` | `fitd_engine.py` | current_stress, max_stress, traumas, max_traumas |
| `LegionState` | `fitd_engine.py` | supply, intel, morale, pressure |
| `UniversalClock` | `clock.py` | name, filled, max_segments, thresholds, mode |
| `StateFrame` | `state_frame.py` | system_id, turn_number, hp, doom, location, inventory, party, rooms (frozen) |
| `MemoryShard` | `memory.py` | content, shard_type, source, timestamp |
| `SessionManifest` | `narrative_loom.py` | shard_hash, synthesis, timestamp |
| `Quest` | `narrative_engine.py` | id, title, description, phase, objectives, reward |
| `NPC` | `narrative_engine.py` | id, name, role, location, relationship, memory |
| `DungeonNPC` | `narrative_engine.py` | id, name, role, tier, location, alive |
| `NarrativeEngine` | `narrative_engine.py` | quest_log, npc_roster, current_phase, chapter, npc_memory |
| `MetabolicState` | `cortex.py` | thermal_status, cpu_temp, gpu_temp, cpu_percent |
| `CivicEvent` | `town_crier.py` | category, event_tag, detail, timestamp, severity |
| `CivicPulse` | `town_crier.py` | active_events, tick_counter, thresholds |
| `BiasLens` | `npc_memory.py` | cultural_values, bias_table |
| `NPCMemoryBank` | `npc_memory.py` | npc_id, shards, lens (MAX_SHARDS=8) |
| `HistoricalEvent` | `world_ledger.py` | timestamp, event_type, summary, authority_level, category, universe_id, source |
| `UniverseLink` | `universe_manager.py` | universe_id, module_a, module_b, link_type, created_at |
| `RoomNode` | `map_engine.py` | id, x, y, width, height, room_type, connections, tier, is_locked, is_secret |
| `DungeonGraph` | `map_engine.py` | seed, width, height, rooms, start_room_id |
| `BSPNode` | `map_engine.py` | x, y, width, height, left, right |
| `SpatialRoom` | `map_renderer.py` | id, x, y, width, height, visibility, connections, enemies, loot, furniture |
| `ThemeConfig` | `map_renderer.py` | wall_char, floor_char, door_char, colors... |
| `CommandDef` | `registry.py` | name, aliases, description, category, is_narrative |
| `VoiceCue` | `voice_bridge.py` | tag, speaker_id, length_scale, noise_scale, noise_w_scale |
| `SessionState` | `codex_agent_main.py` | conversation_history, game_state, last_interaction |
| `DiscordSession` | `discord_bot.py` | channel_id, phase, engine, current_dilemma, game_type, bridge, mimir |
| `TelegramSession` | `telegram_bot.py` | chat_id, phase, engine, current_dilemma, game_type, bridge, mimir |
| `TutorialPage` | `tutorial.py` | title, body, example, tip |
| `TutorialModule` | `tutorial.py` | module_id, category, title, pages |
| `Landmark` | `grapes_engine.py` | name, terrain, feature |
| `Tenet` | `grapes_engine.py` | doctrine, ritual, heresy |
| `Aesthetic` | `grapes_engine.py` | style, art_form, cultural_mark |
| `PoliticalFaction` | `grapes_engine.py` | name, agenda, clock_name, clock_segments |
| `ScarcityEntry` | `grapes_engine.py` | resource, abundance, trade_note |
| `Taboo` | `grapes_engine.py` | prohibition, punishment, origin |
| `LanguageProfile` | `grapes_engine.py` | name, phoneme_type, vowels, consonants, syllable_patterns, suffixes, titles |
| `CulturalValue` | `grapes_engine.py` | tenet, expression, consequence |
| `AestheticProfile` | `grapes_engine.py` | building_style, material, motif, clothing_style, textile, accessory |
| `GrapesProfile` | `grapes_engine.py` | geography, religion, arts, politics, economics, social, language, culture, architecture |
| `RunStatistics` | `burnwillow/ui.py` | floors_cleared, enemies_slain, turns_taken, chests_opened, gold_collected |
| `MetaUnlocks` | `burnwillow/ui.py` | total_runs, deepest_depth, total_kills, unlocked_starts, unlocked_blessings |

### 6.4 Inheritance Chains

```
Exception
  ├── CoreRuleSetMismatch          (orchestrator.py)
  └── MissingEngineError           (trait_handler.py, codex_transmuter.py)

ABC
  └── TraitResolver                (trait_handler.py)
      ├── BurnwillowTraitResolver  (burnwillow/engine.py)
      ├── DnD5eTraitResolver       (games/dnd5e/__init__.py)
      └── CosmereTraitResolver     (games/stc/__init__.py)

CrownAndCrewEngine
  └── AshburnHeirEngine            (crown/ashburn.py)

RulesetAdapter                     (map_engine.py)
  ├── GenericAdapter               (cartography.py)
  ├── BurnwillowAdapter            (map_engine.py)
  └── TangleAdapter                (zone1.py)

commands.Bot
  ├── CodexDiscordBot              (discord_bot.py)
  └── CodexBot                     (codex_agent_main.py — fallback)

discord.ui.View
  ├── NavigationButtons            (discord_bot.py)
  ├── ActionButtons                (discord_bot.py)
  ├── GameCommandView              (discord_bot.py)
  ├── CharacterCreationView        (discord_bot.py)
  ├── CharacterArchetypeView       (discord_bot.py)
  ├── BurnwillowStatAllocView      (discord_bot.py)
  ├── BurnwillowLoadoutView        (discord_bot.py)
  ├── CharacterConfirmView         (discord_bot.py)
  ├── NavigationView               (codex_ui_manager.py — orphaned)
  └── DiceRollView                 (dice.py — conditional)
```

**Critical: No FITD engine extends anything from `fitd_engine.py`.** All 7 registered engines are standalone classes using `FITDActionRoll` via deferred local imports (composition pattern).

---

## 7. Ghost Audit — Orphans, Stubs, Dead Code

### 7.1 Confirmed Wired (Active)

| Module | Consumer(s) | Verification |
|--------|------------|-------------|
| `broadcast.py` | 10+ files import GlobalBroadcastManager | grep confirmed |
| `tarot.py` | play_crown.py, discord_bot.py, telegram_bot.py, codex_agent_main.py | grep confirmed |
| `trait_handler.py` | BurnwillowBridge.__init__ registers BurnwillowTraitResolver | grep confirmed |
| `narrative_loom.py` | CrownAndCrewEngine._consult_mimir() | import verified |
| `town_crier.py` | BurnwillowEngine.__init__() creates CivicPulse | import verified |
| `npc_memory.py` | play_burnwillow.py _init_npc_memory() | import verified |
| `graveyard.py` | log_death() called from Burnwillow bridge | import verified |
| `cartography.py` | Librarian `carto` command | import verified |
| `fitd_engine.py` | All 5 FITD engines + BoB | deferred imports confirmed |

### 7.2 Partially Wired (Functional but Limited Reach)

| Module | Status | Detail |
|--------|--------|--------|
| `capacity_manager.py` | Imported in BurnwillowBridge | `check_encumbrance()` never called from play loops |
| `retriever.py` | `CodexRetriever` defined | No confirmed caller — FAISS + langchain required |
| `manifold_guard.py` | `ManifoldGuard` defined | `verify_conservation_of_identity()` has no confirmed caller |
| `universe_manager.py` | Used in codex_agent_main.py | `are_linked()` gating not wired into any engine dispatch |
| `dm_tools.py` | DM Tools menu in codex_agent_main.py | `summarize_context()` Mimir path may not exist |

### 7.3 Root-Level Orphans

| File | Lines | Status | Evidence |
|------|-------|--------|---------|
| `codex_gemini_bridge.py` | 89 | **ORPHANED** | Zero imports found across entire codebase; predates `gemini` CLI |
| `codex_ui_manager.py` | ~780 | **ORPHANED** | Zero imports; `GameState` enum conflicts with play_burnwillow.py class name |
| `optimize_context.py` | ~300 | **ORPHANED** | Zero imports; `ContextWindow` never wired into Mimir path |

### 7.4 Stale Config

| File | Issue |
|------|-------|
| `config/burnwillow_schema.json` | Uses `Flow/Focus/Vigor` stats — engine uses `Might/Wits/Grit/Aether` |
| `config/models/ModelfileMimir` | Legacy `qwen2.5:0.5b` — current is `qwen3:1.7b` (`Modelfile.codex`) |
| `config/systems/rules_BURNWILLOW.json` | Placeholder data ("Character Class 1") — engine is source of truth |
| `config/systems/rules_GRAVEYARD.json` | Retired system definitions |
| `config/systems/rules_CBR*.json` | Naming collision (two files for same system) |

### 7.5 Dead Code Within Active Files

| Location | Code | Status |
|----------|------|--------|
| `codex_agent_main.py` | Embedded `CodexBot` + `VoiceUplink` classes | Fallback — shadowed by `CodexDiscordBot` |
| `burnwillow/ui.py` | `RunStatistics`, `MetaUnlocks`, `render_death_screen()` | Partially used (ui.py predates paper_doll.py refactor) |
| `engine_protocol.py` | `ENGINE_REGISTRY` dict | Write-only from codex/core/ perspective — consumers in bridges |
| `graveyard.py` | `get_graveyard_systems()`, `get_elegy()` | No confirmed callers |

### 7.6 Duplicate Rendering

`paper_doll.py` and `ui.py` both render equipment grids and HP bars with the same color palette. `paper_doll.py` (newer) imports from engine types. `ui.py` (older) uses dict-based interface. `discord_embed.py` imports from `paper_doll.py`.

---

## 8. Volo Legacy Check

### 8.1 Shadow Map

| Artifact | Location | Status |
|----------|----------|--------|
| "Project Volo" docstring references | `codex_agent_main.py` file header | Cosmetic — no string "volo" in code body |
| "Dual-Interface Concurrent Orchestrator" name | `codex_agent_main.py` docstring | Cosmetic — architecture has evolved |
| `@Architect/@Mechanic/@Designer/@Playtester` roles | `CLAUDE.md` Team Manifest | Active — still used as agent persona triggers |
| `WAKE_WORDS` includes "volo" | `discord_bot.py` | Active — voice wake word |
| Embedded `CodexBot` fallback | `codex_agent_main.py` | Active fallback — functionally behind `CodexDiscordBot` |
| Gemini bridge standalone | `codex_gemini_bridge.py` | Orphaned — `gemini` CLI is current tool |
| UI Manager framework | `codex_ui_manager.py` | Orphaned — rendering abstraction never wired |
| Context Window manager | `optimize_context.py` | Orphaned — Mimir uses own context handling |
| Pre-current lore snippets | `codex_ui_manager.py` ("Qwen whispers...") | Stale flavor text |

### 8.2 Name Collision Hazard

Both `codex_ui_manager.py` (`Enum`) and `play_burnwillow.py` (`class`) define a type named `GameState`. They are completely unrelated. Current isolation prevents this from being a bug, but it is a latent hazard if the orphaned file is ever re-imported.

---

## 9. Test Coverage Map

### 9.1 Test Files (22 files in `tests/`)

| File | Type | Focus |
|------|------|-------|
| `test_aesthetic_profile.py` | pytest | AestheticProfile + GrapesProfile architecture |
| `test_burnwillow_integration.py` | pytest | BurnwillowEngine integration |
| `test_burnwillow_ui.py` | pytest | Rich UI rendering |
| `test_chronologer.py` | pytest | WorldLedger chronology + EventType |
| `test_crown_expansion.py` | pytest | Crown engine + quests |
| `test_grapes_cultural_dna.py` | pytest | LanguageProfile + CulturalValue |
| `test_librarian_file_selection.py` | pytest | LibrarianTUI file handling |
| `test_librarian_pdf.py` | pytest | PDF reader mode |
| `test_map_renderer.py` | pytest | SpatialGridRenderer + themes |
| `test_npc_memory.py` | pytest | BiasLens + NPCMemoryBank + NPCMemoryManager |
| `test_omni_parity.py` | pytest | Cross-platform parity |
| `test_paper_doll.py` | pytest | Rich character sheet |
| `test_universal_command_menu.py` | pytest | COMMAND_CATEGORIES + bridge dispatch |
| `test_voice_bridge.py` | pytest | VoiceBridge + VoiceCue |
| `test_wo_v9_4.py` | pytest | Bridge hardening (WO-V9.4) |
| `verify_wo038.py` | verification | WO-038 deployment verification |
| `verify_wo042_full.py` | verification | WO-042 deployment verification |
| `burnwillow_combat_sim.py` | simulation | Combat balance testing |
| `burnwillow_combat_sim_v2.py` | simulation | Combat balance v2 |
| `burnwillow_combat_attrition.py` | simulation | Attrition curve analysis |
| `burnwillow_stress_test.py` | simulation | Engine stress test |
| `validate_option_a_prime.py` | validation | Architecture option validation |

### 9.2 Coverage Gaps

| Area | Test Status |
|------|------------|
| Burnwillow engine core | Covered (integration + combat sims) |
| Crown & Crew engine | Covered (expansion tests) |
| Ashburn Heir engine | Partially covered (via QA scenarios, no dedicated test file) |
| FITD engines (7) | **No dedicated tests** |
| Map generation (BSP) | Covered (map_renderer tests) |
| NPC Memory | Covered (20 tests) |
| World generation (GRAPES) | Covered (cultural DNA + aesthetic profile) |
| Discord bot | No unit tests (Views require real discord.py) |
| Telegram bot | No unit tests |
| Voice pipeline | Covered (voice_bridge tests) |
| Mimir integration | No dedicated tests |
| OmniForge | No dedicated tests |

---

## Appendix A: Port Registry

| Port | Service | Module |
|------|---------|--------|
| 5000 | Ears (STT) | `codex/services/ears.py` |
| 5001 | Mouth (TTS) | `codex/services/mouth.py` |
| 11434 | Ollama (LLM) | External |

## Appendix B: World Data Pipeline

```
GrapesGenerator.generate(seed)
    → GrapesProfile (9 categories, 2-4 entries each)
    → WorldLedger (mutation tracking + chronology)
    → CodexMemoryEngine.ingest_world_state(profile.to_narrative_summary())
    → MemoryShard (ANCHOR type)
    → mimir.build_grapes_context(grapes_dict)
    → Injected into LLM context (~150-200 tokens)
```

## Appendix C: Tarot Cards

| Key | Context | Border Color | Used For |
|-----|---------|-------------|----------|
| `sun_ring` | crown | #DAA520 (gold) | Crown allegiance prompts |
| `registry_key` | crew | grey50 | Crew allegiance prompts |
| `dead_tree` | campfire | #556B2F (olive) | Campfire reflections |
| `wolf` | world | #4B0082 (indigo) | World/environment prompts |
| `moon` | legacy | #191970 (midnight) | Legacy reports, breach events |

---

*Generated by recursive source-level extraction. No assumptions from prior documentation.*
*Cross-referenced against 3 QA behavioral scenarios (see QA_REPORT_SYSTEM_INTEGRITY.md).*
*Audit date: 2026-02-21*

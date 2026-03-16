# SYSTEM MANIFEST — TOTAL V2.0

> **Project:** C.O.D.E.X. (Codex of Chronicles)
> **Date:** 2026-03-09
> **Scope:** 100% recursive audit of all `.py`, `.json`, and config files
> **Method:** Independent source-level extraction — no assumptions from prior documentation
> **Supersedes:** SYSTEM_MANIFEST_TOTAL_V1.0 (2026-02-21)
> **Work Orders Since V1.0:** WO-V42.0 through WO-V60.0 (19 Work Orders)

---

## Table of Contents

1. [Directory Map & File Inventory](#1-directory-map--file-inventory)
2. [Package Architecture & Dependency Hub](#2-package-architecture--dependency-hub)
3. [Engine Logic — All Systems](#3-engine-logic--all-systems)
4. [State Serialization Schemas](#4-state-serialization-schemas)
5. [Cross-Platform Handoff Map](#5-cross-platform-handoff-map)
6. [Module Catalog & Content Pipeline](#6-module-catalog--content-pipeline)
7. [System Discovery & Trait Registry](#7-system-discovery--trait-registry)
8. [Engine Stacking — Cross-System Campaigns](#8-engine-stacking--cross-system-campaigns)
9. [Integrations & External Services](#9-integrations--external-services)
10. [Test Coverage Map](#10-test-coverage-map)
11. [Ghost Audit — Dead Code Status](#11-ghost-audit--dead-code-status)

---

## 1. Directory Map & File Inventory

### 1.1 Summary

| Category | Files | Lines |
|----------|-------|-------|
| `codex/` (core package) | 180 | 84,568 |
| `tests/` | 78 | 38,547 |
| `scripts/` | 7 | 3,399 |
| Top-level play files | 4 | 11,739 |
| `maintenance/` | 8 | 3,247 |
| **Total Python** | **~277** | **~141,500** |
| Config JSON files | 24 | — |
| System manifests | 9 | — |
| Adventure modules | 10 | — |

### 1.2 Package Tree

```
codex/                          # Root package (__version__ = "3.0.0")
├── __init__.py                 # Version + docstring
├── paths.py                    # Central path registry (THE dependency hub)
│
├── bots/                       # Platform interface layer
│   ├── discord_bot.py          # 3,019 lines — Discord interface v3.1
│   ├── telegram_bot.py         # 1,709 lines — Telegram interface (python-telegram-bot v20+)
│   └── scryer.py               # Rich→PNG screenshot engine (pyte + Pillow)
│
├── core/                       # Brain + shared services
│   ├── architect.py            # LLM router with thermal gating
│   ├── butler.py               # Reflex handler chain (13+ reflexes), narration cooldown (3s)
│   ├── cache.py                # Session cache (JSON, TTL)
│   ├── cortex.py               # Thermal monitor + persona loader
│   ├── dice.py                 # Universal dice roller
│   ├── dm_tools.py             # Encounter generator + DM utilities
│   ├── encounters.py           # EncounterEngine + EncounterContext
│   ├── engine_protocol.py      # GameEngine/DiceEngine/PartyEngine protocols + ENGINE_REGISTRY
│   ├── engine_stack.py          # Engine stacking: MechanicLayer, StackedCharacter, dispatcher [WO-V60.0]
│   ├── engine_traits.py        # TRAIT_CATALOG (12 traits), TraitDef, validation [WO-V59.0]
│   ├── config_loader.py        # Shared JSON config loader with caching [WO-V58.0]
│   ├── manifold_guard.py       # State consistency verifier
│   ├── memory.py               # CodexMemoryEngine — shard-based memory
│   ├── menu.py                 # Terminal menu dispatcher
│   ├── narrative_content.py    # Static NPC/quest/haven/room templates
│   ├── narrative_engine.py     # NarrativeEngine — quest tracker + NPC dialogue + Mimir calls
│   ├── quest_rewards.py        # Materialize quest rewards, setting palettes [WO-V44.0]
│   ├── registry.py             # Command definition + alias resolution
│   ├── retriever.py            # FAISS-backed RAG retriever
│   ├── state_frame.py          # Frozen game snapshot dataclass
│   ├── system_discovery.py     # Dynamic system discovery from manifests [WO-V59.0]
│   │
│   ├── mechanics/
│   │   ├── clock.py            # UniversalClock (DoomClock + FactionClock factory)
│   │   ├── conditions.py       # ConditionTracker — 10 condition types, per-entity
│   │   ├── initiative.py       # InitiativeTracker — per-engine die formula
│   │   ├── orchestrator.py     # HybridGameOrchestrator — multi-engine CRS gating (stub)
│   │   ├── progression.py      # ProgressionTracker — XP/milestone/FITD advancement
│   │   └── rest.py             # RestManager — short/long rest per engine type
│   │
│   └── services/
│       ├── broadcast.py        # GlobalBroadcastManager — thread-safe event bus
│       ├── capacity_manager.py # Weight/slot encumbrance check
│       ├── cartography.py      # BSP map generation bridge
│       ├── fitd_engine.py      # Shared FITD core: FITDActionRoll, StressClock, FactionClock
│       ├── graveyard.py        # Persistent character memorial
│       ├── librarian.py        # Three-panel knowledge browser TUI
│       ├── narrative_frame.py  # DeltaTracker + build_narrative_frame() — 7-strategy enrichment
│       ├── narrative_loom.py   # NarrativeLoomMixin — cross-shard synthesis + session recap
│       ├── npc_memory.py       # NPCMemoryManager + BiasLens + disposition tracking
│       ├── rag_service.py      # RAGService — FAISS retrieval + thermal-gated summarization
│       ├── town_crier.py       # Civic event engine + rumor generator
│       ├── trait_handler.py    # TraitHandler — system-agnostic trait resolution dispatcher
│       ├── tutorial.py         # Contextual hint + tutorial browser
│       ├── tutorial_content.py # 21 tutorial modules across 5 categories
│       └── universe_manager.py # Universe namespace isolation
│
├── forge/                      # Character creation
│   ├── char_wizard.py          # Interactive character builder
│   ├── omni_forge.py           # System-agnostic forge dispatcher
│   ├── source_scanner.py       # Vault content scanner + parent merge [WO-V49.0]
│   ├── adapter.py              # CreationSchema adapter
│   ├── codex_transmuter.py     # Character transmutation tools
│   ├── loot_tables.py          # System-agnostic loot generation
│   └── reference_data/         # Per-system creation data (PDF-sourced)
│       ├── setting_filter.py   # filter_by_setting() + filter_pool_by_setting() [WO-V43.0]
│       ├── burnwillow_data.py  # Heritages, loadouts, gear tiers
│       ├── dnd5e_data.py       # Races, classes, backgrounds, equipment
│       ├── stc_data.py         # Heritages, orders, surges (tagged "roshar")
│       ├── bitd_data.py        # Playbooks, heritages, crew types
│       ├── sav_data.py         # Playbooks, heritages, ship classes
│       ├── bob_data.py         # Playbooks, heritages, legion resources
│       ├── cbrpnk_data.py      # Archetypes, backgrounds, chrome
│       └── candela_data.py     # Roles, specializations, catalysts
│
├── games/                      # Engine implementations
│   ├── bridge.py               # UniversalGameBridge — 1,246 lines, 32 commands
│   ├── burnwillow/
│   │   └── engine.py           # BurnwillowEngine — 2,400 lines
│   ├── crown/
│   │   └── engine.py           # CrownAndCrewEngine — 1,689 lines
│   ├── dnd5e/
│   │   └── __init__.py         # DnD5eEngine — 1,235 lines
│   ├── stc/
│   │   └── __init__.py         # CosmereEngine — 1,250 lines
│   ├── bitd/
│   │   └── __init__.py         # BitDEngine — 624 lines
│   ├── sav/
│   │   └── __init__.py         # SaVEngine — 643 lines
│   ├── bob/
│   │   └── __init__.py         # BoBEngine — 629 lines
│   ├── cbrpnk/
│   │   └── __init__.py         # CBRPNKEngine — 638 lines
│   └── candela/
│       └── __init__.py         # CandelaEngine — 589 lines
│
├── spatial/                    # Map generation & rendering
│   ├── map_engine.py           # CodexMapEngine — BSP dungeon generator
│   ├── map_renderer.py         # SpatialGridRenderer — 2D character matrix + fog of war
│   ├── module_manifest.py      # ModuleManifest, Chapter, ZoneEntry — module metadata + system_transitions [WO-V60.0]
│   ├── zone_manager.py         # ZoneManager — stateful zone progression
│   ├── zone_loader.py          # Zone loader — blueprint JSON or procedural
│   ├── scene_data.py           # SceneData typed models (NPCs, enemies, loot, DCs) [WO-V51.0]
│   ├── settlement_adapter.py   # Settlement room adapter for Rich rendering
│   ├── world_map.py            # Procedural world map generation
│   ├── world_map_renderer.py   # Rich world map rendering + travel UI
│   └── player_renderer.py      # Player character status display
│
├── integrations/               # External service clients
│   ├── mimir.py                # Ollama (Mimir model) task handler + RAG search
│   ├── fr_wiki.py              # Forgotten Realms Wiki via Kiwix ZIM [WO-V55.0]
│   ├── tarot.py                # Tarot card rendering for narrative prompts
│   └── vault_processor.py      # PDF → module blueprint extraction + vault indexing
│
├── services/                   # System services
│   ├── ears.py                 # Speech-to-text (Whisper)
│   └── mouth.py                # Text-to-speech (Piper)
│
├── stubs/
│   └── discord_stub.py         # Offline discord.py SDK stub
│
└── world/                      # World generation
    ├── genesis.py              # GenesisEngine — procedural world creation
    └── world_wizard.py         # Interactive world builder
```

### 1.3 Top-Level Files

```
play_burnwillow.py    # 6,410 lines — Burnwillow interactive game loop (v2.0)
play_universal.py     # 1,403 lines — Universal engine router (dungeon/FITD dispatch)
play_crown.py         #   312 lines — Crown & Crew launcher
codex_agent_main.py   # 3,614 lines — Unified orchestrator (Rich UI + Discord + Telegram)
```

### 1.4 Scripts

```
scripts/
├── build_content.py   # 711 lines — Unified extraction: PDF → config JSON [WO-V58.0]
├── build_indices.py   # 561 lines — FAISS index builder from vault PDFs [WO-V57.0]
├── classify_system.py # 576 lines — Heuristic + LLM system classifier [WO-V59.0]
├── scrape_fr_wiki.py  # 534 lines — FR wiki scraper: Fandom API → ZIM [WO-V55.0]
├── start_maestro.sh   # Boot script → codex_maestro.py
├── fr_wiki_articles.txt # 34,627 article titles for FR wiki scrape
└── Codex.desktop      # Desktop launcher
```

### 1.5 Config Files

```
config/
├── bestiary/
│   ├── dnd5e.json     # 185 PDF-sourced monsters, 4 tiers (61/58/43/23)
│   └── stc.json       # 16 Cosmere adversaries, 4 tiers
├── features/
│   └── dnd5e.json     # Invocations, maneuvers, metamagic, fighting styles
├── hazards/
│   ├── dnd5e.json     # 4-tier environmental hazards
│   └── stc.json       # Cosmere hazards
├── loot/
│   ├── dnd5e.json     # 4-tier loot tables
│   └── stc.json       # Cosmere loot
├── magic_items/
│   └── dnd5e.json     # 28 magic items
├── burnwillow_schema.json
├── entity_schema.json
├── skald_lexicon.json
└── systems/           # System-specific config
```

### 1.6 Vault & Adventure Modules

**System Manifests (9):**
```
vault/burnwillow/system_manifest.json
vault/crown/system_manifest.json
vault/dnd5e/system_manifest.json
vault/stc/system_manifest.json
vault/FITD/bitd/system_manifest.json
vault/FITD/sav/system_manifest.json
vault/FITD/bob/system_manifest.json
vault/FITD/CBR_PNK/system_manifest.json
vault/ILLUMINATED_WORLDS/Candela_Obscura/system_manifest.json
```

**Adventure Modules (10):**
```
vault_maps/modules/
├── dragon_heist/        # D&D 5e — Waterdeep: Dragon Heist (4 villain paths)
├── mad_mage/            # D&D 5e — Dungeon of the Mad Mage
├── out_of_abyss/        # D&D 5e — Out of the Abyss
├── rime_frostmaiden/    # D&D 5e — Rime of the Frostmaiden
├── tyranny_dragons/     # D&D 5e — Tyranny of Dragons
├── stc_bridge_nine/     # STC — Bridge Nine
├── stc_first_step/      # STC — First Step
├── stc_stonewalkers/    # STC — Stonewalkers
├── cbrpnk_mind_gap/     # CBR+PNK — Mind the Gap
└── sample_module/       # Reference template
```

---

## 2. Package Architecture & Dependency Hub

### 2.1 Dependency Flow

```
                         codex/paths.py (central path registry)
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
           codex/core/     codex/games/     codex/spatial/
           (brain)         (engines)        (maps)
                │               │               │
                ▼               ▼               ▼
         codex/services/   codex/forge/    codex/integrations/
         (ears, mouth)     (char creation)  (mimir, wiki, RAG)
                │               │               │
                └───────┬───────┘               │
                        ▼                       │
                   codex/bots/                  │
                   (discord, telegram)──────────┘
```

**Key Dependency Rules:**
- `codex/core/` imports NOTHING from `codex/games/` (one-way dependency)
- `codex/games/` engines import from `codex/core/` (protocols, services, mechanics)
- `codex/spatial/` is independent of game engines (content injection via adapters)
- `codex/integrations/` is a leaf — no upstream imports
- `codex/bots/` consumes everything; nothing imports from bots

### 2.2 Path Registry (`codex/paths.py`)

All filesystem paths centralized here. Every module that needs a path imports from `paths.py`:
- `CODEX_ROOT` — project root
- `VAULT_DIR` — vault/ (PDF library)
- `SAVES_DIR` — saves/
- `CONFIG_DIR` — config/
- `FAISS_DIR` — faiss_index/
- `WORLDS_DIR` — worlds/ (GRAPES data)
- `VAULT_MAPS_DIR` — vault_maps/modules/

### 2.3 Protocol Hub (`codex/core/engine_protocol.py`)

```python
@runtime_checkable
class GameEngine(Protocol):
    system_id: str        # "burnwillow", "bitd", "crown", "dnd5e", "stc", etc.
    system_family: str    # "BURNWILLOW", "FITD", "CROWN", "DND5E", "STC"
    display_name: str

    def get_status() → Dict[str, Any]: ...
    def save_state() → Dict[str, Any]: ...
    def load_state(data: Dict[str, Any]) → None: ...

@runtime_checkable
class DiceEngine(Protocol):
    def roll_check(**kwargs) → Dict[str, Any]: ...

@runtime_checkable
class PartyEngine(Protocol):
    party: List
    def add_to_party(char) → None: ...
    def remove_from_party(char) → None: ...
    def get_active_party() → List: ...

@runtime_checkable
class StackableEngine(Protocol):                    # [WO-V60.0]
    def get_action_map() -> Dict[str, int]: ...

ENGINE_REGISTRY: Dict[str, type] = {}
# Registered: bitd, sav, bob, cbrpnk, candela, dnd5e, stc
# Standalone (not in registry): burnwillow, crown
```

---

## 3. Engine Logic — All Systems

### 3.1 Engine Summary Table

| System | Engine Class | Character Class | Family | Lines | Resolution | Party | Modules | Traits |
|--------|-------------|-----------------|--------|-------|------------|-------|---------|--------|
| **Burnwillow** | `BurnwillowEngine` | `Character` | BURNWILLOW | 2,400 | 5d6 pool + stat mod vs DC | Yes | No | 21 (TraitHandler) |
| **Crown & Crew** | `CrownAndCrewEngine` | — (Sway-based) | CROWN | 1,689 | Narrative Sway (-3 to +3) | No | No | — |
| **D&D 5e** | `DnD5eEngine` | `DnD5eCharacter` | DND5E | 1,235 | d20 + ability mod + proficiency vs DC | Yes | Yes | DnD5eTraitResolver |
| **Cosmere (STC)** | `CosmereEngine` | `CosmereCharacter` | STC | 1,250 | d6 pool + surge mod vs DC | Yes | Yes | CosmereTraitResolver |
| **Blades in the Dark** | `BitDEngine` | `BitDCharacter` | FITD | 624 | d6 pool highest-die | Yes | Yes | — |
| **Scum & Villainy** | `SaVEngine` | `SaVCharacter` | FITD | 643 | d6 pool highest-die | Yes | Yes | — |
| **Band of Blades** | `BoBEngine` | `BoBCharacter` | FITD | 629 | d6 pool highest-die | Yes | Yes | — |
| **CBR+PNK** | `CBRPNKEngine` | `CBRPNKCharacter` | FITD | 638 | d6 pool highest-die | Yes | Yes | — |
| **Candela Obscura** | `CandelaEngine` | `CandelaCharacter` | ILLUMINATED | 589 | d6 pool highest-die | Yes | Yes | — |

### 3.2 Burnwillow Engine

**File:** `codex/games/burnwillow/engine.py` (2,400 lines)

**Character Model:**
- 4 core stats: `might`, `wits`, `grit`, `aether` (4d6 drop lowest)
- Derived: `max_hp`, `current_hp`, `base_defense`
- Equipment: `GearGrid` (10 slots: HEAD, SHOULDERS, CHEST, ARMS, LEGS, R.HAND, L.HAND, R.RING, L.RING, NECK)
- Gear: Tier-based (TIER_0 to TIER_IV), dice bonuses, 21 special traits

**Unique Mechanics:**
- **DoomClock:** 7 thresholds (5, 10, 13, 15, 17, 20, 22) — escalating dungeon danger
- **GearGrid:** 10-slot equipment with trait activations (Lockpick, Intercept, Summon, Cleave, etc.)
- **Damage Reduction (DR):** Armor provides DR, actual damage = max(1, damage - DR)
- **Ambush System:** 1d6 + Wits mod vs Passive DC on room entry
- **Minion System:** `Minion(Character)` subclass, HP=3+mod, 3-round duration
- **Pity Timer:** Tracks turns since unique loot drop
- **CivicPulse:** Civic event tracking with WorldHistory integration

**Quest System (WO-V44.0+):**
- `offer_dungeon_quest()`, `check_objective()`, `turn_in_quest()`
- Objectives: kill_count, search_count, loot_count, reach
- Mimir-first quest generation with static fallback (WO-V45.0)
- NPC disposition tracking: turn-in increments; disposition ≥ 2 reveals bonus rumor

**Party System:**
- `create_party(names)`, `add_to_party()`, `remove_from_party()`, `get_active_party()`
- Enemy HP/ATK scaling by party size
- 6 starter loadout templates: sellsword, occultist, sentinel, archer, vanguard, scholar

**Subsystems:**
- `DeltaTracker` — narrative frame enrichment (WO-V48.0)
- `TraitHandler` + `BurnwillowTraitResolver` — 21 gear traits (WO-V56.0)
- `NarrativeLoomMixin` — memory shards
- `NPCMemoryManager` — NPC disposition + broadcast events

### 3.3 Crown & Crew Engine

**File:** `codex/games/crown/engine.py` (1,689 lines)

**Unique Mechanics:**
- **Sway System:** Integer -3 to +3 tracking crew allegiance
  - -3: Crown Agent → 0: Drifter → +3: Crew Loyal
- **Narrative DNA:** 5 tags (BLOOD, GUILE, HEARTH, SILENCE, DEFIANCE) via voting
- **Blind Allegiance Loop:** Players commit (crown/crew/drifter) before seeing prompts
- **Political Gravity:** Weighted council voting with faction influence
- **Arc System:** Variable 5-day arcs with rest progression
- **20 prompt pools** per category (Crown, Crew, World, Campfire, Morning, Council)

**Subsystems:**
- Politics engine (lazy-initialized)
- Event generator (lazy-initialized)
- NarrativeLoomMixin
- Entity GPS tracking (update_entity, get_entity_state, trace_fact)
- Mimir integration for AI-driven prompt generation

### 3.4 D&D 5th Edition Engine

**File:** `codex/games/dnd5e/__init__.py` (1,235 lines)

**Character Model:**
- 6 ability scores: STR, DEX, CON, INT, WIS, CHA (standard array or random)
- Derived: `max_hp` (hit die + CON mod), `armor_class` (10 + DEX mod), `proficiency_bonus`
- Class hit dice: Barbarian d12, Fighter/Paladin/Ranger d10, most d8, Sorc/Wiz d6
- `setting_id` for campaign setting gating (WO-V55.0)

**Module Pipeline (WO-V51.0 + V53.0 + V57.0):**
- `load_module(manifest_path)` → ZoneManager init, first zone load
- `load_dungeon_graph(graph)` → DnD5eAdapter + ContentInjector population
- `_apply_content_hints(PopulatedRoom)` → hand-authored content override
- `advance_zone()` → next zone with villain path filtering
- `_module_manifest_path` persisted in save/load (WO-V57.0)

**Content Loading (WO-V58.0):**
- `_load_bestiary()` → 185 PDF-sourced monsters from `config/bestiary/dnd5e.json`
- `_load_loot_pool()`, `_load_hazard_pool()`, `_load_magic_items()` → config-driven with fallback

**Party Scaling:**
- 1 player: 1.0x HP/ATK → 6 players: 2.6x HP, 1.5x ATK

**Lazy Subsystems:**
- Spell slots, concentration trackers (per-character)
- Spell managers, feat managers (class abilities)
- Combat resolver, zone manager, delta tracker

### 3.5 Cosmere (STC) Engine

**File:** `codex/games/stc/__init__.py` (1,250 lines)

**Character Model:**
- 3 core attributes: `strength`, `speed`, `intellect`
- Derived: `max_hp` (10 + STR mod), `defense` (10 + SPD mod), `focus`/`max_focus` (Stormlight pool)
- Order (10 Radiant Orders), heritage, surge_type, ideal_level (1-5)
- `setting_id` for sub-setting filtering (e.g., "roshar") (WO-V43.0)

**Unique Mechanics:**
- **10 Radiant Orders:** Windrunner, Skybreaker, Dustbringer, Edgedancer, Truthwatcher, Lightweaver, Elsecaller, Willshaper, Stoneward, Bondsmith
- **Surges:** Two per order; tied to attributes
- **Focus/Stormlight:** Resource pool for surge invocations
- **Ideal Progression:** 5 levels of Radiant advancement
- **Setting Filtering:** Heritages, orders, equipment filtered by `setting_id` via `filter_by_setting()`

**Module Pipeline:** Mirrors D&D 5e (`load_module`, `load_dungeon_graph`, `_apply_content_hints`, `advance_zone`)

**Convenience Accessors:** `get_heritages()`, `get_orders()`, `get_equipment(category)` — all setting-filtered

### 3.6 FITD Engine Family (5 Systems)

**Shared Core** (`codex/core/services/fitd_engine.py`):
- `FITDActionRoll` — d6-pool resolution: 1-3 fail, 4-5 mixed, 6 success, 6+6 critical
- `StressClock` — 9-stress max → trauma (random from table), 4 trauma max → broken
- `FactionClock` — 4/6/8-segment progress clocks
- `Position` enum: CONTROLLED, RISKY, DESPERATE
- `Effect` enum: ZERO, LIMITED, STANDARD, GREAT, EXTREME

**Per-Engine Unique Mechanics:**

| Engine | Unique Feature | Character Model |
|--------|---------------|-----------------|
| **BitD** | Score cycle (flashback, planning, execution, downtime), crew resources (heat/wanted/rep/coin/turf) | 12 action dots (Insight/Prowess/Resolve × 4) |
| **SaV** | Ship management (ShipState: hull, crew, supply, engines, systems), job cycle | 12 action dots (doctor/hack/rig/study, helm/scramble/scrap/skulk, attune/command/consort/sway) |
| **BoB** | LegionState (supply/intel/morale/pressure), march/camp/mission cycle, custom BOB_TRAUMAS | 10 action dots + marshal/discipline |
| **CBR+PNK** | Grid hacking (GridState: ICE, nodes, programs), Glitch Die accumulation, Chrome augmentations | hack/override/scan/study, scramble/scrap/skulk/shoot |
| **Candela** | Body/Brain/Bleed tracks (max 3 each, not stress), investigation management | 9 action dots (Nerve/Cunning/Intuition × 3), role + specialization |

**Shared Changes Since V1.0:**
- Party creation fix: `if not self.party: ... else: append` (WO-V54.0)
- `setting_id` field on all 5 engines (WO-V46.0)
- Setting-filtered accessors: `get_playbooks()`, `get_heritages()`, `get_factions()`

---

## 4. State Serialization Schemas

All engines implement `save_state() → Dict[str, Any]` and `load_state(data) → None`.

### 4.1 Burnwillow

```python
{
    "system_id": "burnwillow",
    "character": Character.to_dict(),
    "party": [c.to_dict() for c in party if not isinstance(c, Minion)],
    "doom_clock": DoomClock.to_dict(),
    "dungeon": {
        "graph": DungeonGraph.to_dict(),
        "current_room_id": int,
        "player_pos": (int, int),
        "visited_rooms": [int, ...],
        "zone": str
    },
    "civic_pulse": CivicPulse.to_dict() | None,
    "pity_counter": int,
    "found_items": [str, ...],
    "delta_tracker": DeltaTracker.to_dict() | None   # [WO-V48.0]
}
```

### 4.2 Crown & Crew

```python
{
    "day": int, "sway": int, "patron": str, "leader": str,
    "history": [Dict], "dna": {"BLOOD": int, "GUILE": int, ...},
    "vote_log": [Dict], "arc_length": int, "rest_type": str,
    "rest_config": Dict, "terms": Dict, "entities": Dict,
    "quest_slug": str, "quest_name": str,
    "special_mechanics": Dict, "campaign_context": Dict,
    "_used_crown": [int], "_used_crew": [int], "_used_world": [int],
    "_used_campfire": [int], "_used_morning": [int], "_used_dilemmas": [int],
    "_politics_engine": Dict | None,
    "_event_generator": Dict | None
}
```

### 4.3 D&D 5e

```python
{
    "system_id": "dnd5e",
    "setting_id": str,                                # [WO-V55.0]
    "party": [DnD5eCharacter.to_dict()],
    "current_room_id": int, "player_pos": (int, int),
    "visited_rooms": [int, ...],
    "spell_slots": {name: SpellSlotTracker.to_dict()},
    "concentration": {name: ConcentrationTracker.to_dict()},
    "spell_managers": {name: SpellManager.to_dict()},
    "feat_managers": {name: FeatManager.to_dict()},
    "zone_manager": ZoneManager.to_dict() | None,     # [WO-V51.0]
    "module_manifest_path": str | None,                # [WO-V57.0]
    "delta_tracker": DeltaTracker.to_dict() | None     # [WO-V56.0]
}
```

### 4.4 Cosmere (STC)

```python
{
    "system_id": "stc",
    "setting_id": str,                                # [WO-V43.0]
    "party": [CosmereCharacter.to_dict()],
    "current_room_id": int, "player_pos": (int, int),
    "visited_rooms": [int, ...],
    "surge_managers": {name: SurgeManager.to_dict()},
    "ideal_trackers": {name: IdealProgression.to_dict()},
    "storm_tracker": StormTracker.to_dict() | None,
    "zone_manager": ZoneManager.to_dict() | None,     # [WO-V51.0]
    "module_manifest_path": str | None,                # [WO-V57.0]
    "delta_tracker": DeltaTracker.to_dict() | None     # [WO-V56.0]
}
```

### 4.5 FITD Engines

**BitD:**
```python
{
    "system_id": "bitd", "setting_id": str,
    "party": [BitDCharacter.to_dict()],
    "stress": {name: StressClock.to_dict()},
    "faction_clocks": [UniversalClock.to_dict()],
    "crew_name": str, "crew_type": str,
    "heat": int, "wanted_level": int, "rep": int, "coin": int, "turf": int,
    "score_state": ScoreState.to_dict(),
    "flashback_mgr": FlashbackManager.to_dict(),
    "bargain_tracker": BargainTracker.to_dict(),
    "downtime_mgr": DowntimeManager.to_dict()
}
```

**SaV:** Same pattern + `ship_state: ShipState.to_dict()`, `job_manager: JobPhaseManager.to_dict()`

**BoB:** Same pattern + `legion: LegionState.to_dict()`, `chosen: str`, `campaign_phase: str`, `campaign_mgr`, `mission_resolver`

**CBR+PNK:** Same pattern + `glitch_die: int`, `grid_state: GridState.to_dict()`, `chrome_mgr: ChromeManager.to_dict()`

**Candela:** Same pattern (no stress — uses body/brain/bleed tracks) + `circle_name: str`, `assignments_completed: int`, `investigation: InvestigationManager.to_dict()`

---

## 5. Cross-Platform Handoff Map

### 5.1 UniversalGameBridge

**File:** `codex/games/bridge.py` (1,246 lines)

The bridge adapts any `GameEngine`-protocol engine to text commands. Used by D&D 5e, STC, and all FITD engines. Burnwillow uses its own bridge embedded in `play_burnwillow.py`.

**Command Categories (32 commands):**

| Category | Commands |
|----------|----------|
| Movement | n, s, e, w, ne, nw, se, sw |
| Combat | attack, rest (short/long), hitdice (D&D 5e only) |
| Interaction | talk, investigate, perceive, unlock, services, event |
| Exploration | look, search, loot, drop, use, push, map, inventory, stats, travel, voice, save, help |
| Lore | lore (FR wiki lookup, setting-gated) |
| Stacking | transition, layers (cross-system campaign management) [WO-V60.0] |

**Service Dispatch (WO-V54.0):**
- 14 service aliases → 9 service handlers
- drink → flavor text, heal/cure/bless → party healing, rumors/lore → Mimir, quest/job → quest dispatch, buy/sell → shopkeeper, chrome → ripperdoc

**NPC Dialogue (WO-V54.0):**
- `talk <npc>` enters conversation mode → free-form input routes to Mimir
- Context: NPC role, personality, setting, hidden notes, situation
- FR wiki lore injection for Forgotten Realms settings (WO-V55.0)
- `bye`/`leave`/`goodbye` exits conversation

**Audio Narration (WO-V50.0):**
- `set_butler(butler)` attaches CodexButler for TTS
- `_try_narrate(text)` fires on room entry, kills, death, quest completion
- Butler cooldown: 3 seconds between narrations

### 5.2 Play Universal — Game Loop Routing

**File:** `play_universal.py` (1,403 lines)

```python
def main(system_id: str, manifest=None, butler=None):
    """Universal engine router — dungeon vs FITD dispatch."""
```

| System Type | Loop | Module Support | Renderer |
|-------------|------|----------------|----------|
| Spatial (dnd5e, stc) | `_run_dungeon_loop()` | ZoneManager + ZoneLoader | SpatialGridRenderer |
| Narrative (bitd, sav, bob, cbrpnk, candela) | `_run_fitd_loop()` | `_FITDSceneState` | Text panels |

**Module Selection (WO-V51.0):**
- `_offer_module_select()` scans `vault_maps/modules/*/module_manifest.json`
- System-agnostic: works for both dungeon and FITD systems
- Villain path selection for multi-path modules (Dragon Heist)

**FITD Scene State (WO-V52.0):**
- `_FITDSceneState`: Linear narrative progression through blueprint rooms
- Audio playback from `AUDIO/` directory on scene entry (WO-V54.0)
- Commands: scene, next, scenes, talk, services, investigate, perceive

**Zone Event Subscription (WO-V56.0):**
- Bridge subscribes to `EVENT_ZONE_COMPLETE` for UI feedback
- Zone/chapter advance fires broadcast events

### 5.3 Bot Interfaces

**Discord** (`codex/bots/discord_bot.py` — 3,019 lines):
- 20+ async command handlers
- Voice channel support with Opus watchdog (WO-V9.4)
- Scrying: StateFrame → PNG rendering with thermal guard (> 75°C)
- Full game session support: Burnwillow, D&D 5e, Cosmere, Crown, FITD

**Telegram** (`codex/bots/telegram_bot.py` — 1,709 lines):
- Mirror protocol: ASCII terminal aesthetics
- 25+ async command handlers
- Full feature parity with Discord (voice, sheet, atlas, rumors)
- Sway bar rendering for Crown & Crew

**Parity Status:** Full feature parity across Terminal, Discord, and Telegram.

### 5.4 Play Burnwillow — Standalone Loop

**File:** `play_burnwillow.py` (6,410 lines)

Burnwillow has its own game loop due to unique mechanics:
- Emberhome hub with settlement services (forge, healer, rumor board)
- Structured combat with party cycling + ambush detection
- Spatial map rendering via SpatialGridRenderer
- Quest log with turn-in UI
- NPC memory + broadcast event integration
- Memory Engine wiring: `_engine_ref` set on NarrativeEngine (WO-V56.0)

---

## 6. Module Catalog & Content Pipeline

### 6.1 Module Manifest Schema

```python
ModuleManifest:
    module_id: str              # "dragon_heist"
    display_name: str           # "Waterdeep: Dragon Heist"
    system_id: str              # "dnd5e"
    source_pdf: str             # Reference PDF name
    world_map: Optional[Dict]   # World map data
    starting_location: str      # Entry zone
    recommended_levels: str     # "1-5"
    chapters: [Chapter]         # Ordered chapter list
    freeform_zones: [ZoneEntry] # Unordered zones
    campaign_setting: str       # "forgotten_realms" [WO-V55.0]
```

### 6.2 Content Extraction Pipeline (WO-V58.0)

**Script:** `scripts/build_content.py`

5 extractors: bestiary, loot, hazards, magic_items, features
Two-tier extraction: regex first → LLM (qwen3.5:2b) fallback with 2s thermal cooldown

**Config Loader** (`codex/core/config_loader.py`):
- `load_config(category, system_id)` → loads `config/{category}/{system_id}.json`
- Module-level cache with `clear_cache()` and `force=True` bypass
- Used by all game engines for content loading

**D&D 5e Bestiary (185 monsters, 4 tiers):**
- Sources: Monster Manual, Mordenkainen's Monsters, Out of the Abyss, Tyranny of Dragons, Dragon Heist, Dungeon of the Mad Mage, Rime of the Frostmaiden
- Tier 1: 61 monsters | Tier 2: 58 | Tier 3: 43 | Tier 4: 23 (includes Baphomet, Demogorgon, Orcus, Tiamat)

**STC Bestiary (16 Cosmere adversaries, 4 tiers):**
- Cosmere stat blocks: physical/cognitive/spiritual attributes, role (minion/rival/boss)

### 6.3 FAISS Index Builder (WO-V57.0)

**Script:** `scripts/build_indices.py`
- Scans `vault/*/SOURCE/` for PDFs
- Chunks text with configurable size/overlap
- Embeds via Ollama `nomic-embed-text`
- Writes to `faiss_index/{system_id}/`
- CLI: `--all`, `--system`, `--chunk-size`, `--overlap`, `--force`

---

## 7. System Discovery & Trait Registry

### 7.1 System Discovery (WO-V59.0)

**File:** `codex/core/system_discovery.py`

Replaces hardcoded `DUNGEON_SYSTEMS`/`FITD_SYSTEMS` with manifest-driven discovery:

```python
discover_system_types(vault_root=None) → (dungeon_systems: Set[str], narrative_systems: Set[str])
get_all_manifests() → Dict[str, dict]         # Cached manifest scan
get_manifest(system_id) → Optional[dict]
get_primary_loop(system_id) → str             # "spatial_dungeon" | "scene_navigation"
get_engine_traits(system_id) → List[str]
get_resolution_mechanic(system_id) → str
get_importable_systems() → List[str]          # Systems with Python engine module
```

**Routing Logic:**
- `primary_loop: "spatial_dungeon"` → `_run_dungeon_loop()` (D&D 5e, STC)
- `primary_loop: "scene_navigation"` → `_run_fitd_loop()` (BitD, SaV, BoB, CBR+PNK, Candela)
- Standalone: Burnwillow, Crown excluded from routing (own game loops)

**Hardcoded Fallback:** Dungeon: {dnd5e, stc}, Narrative: {bitd, sav, bob, cbrpnk, candela}

### 7.2 Engine Trait Registry (WO-V59.0)

**File:** `codex/core/engine_traits.py`

12 traits mapped to existing shared modules:

| Category | Trait | Module |
|----------|-------|--------|
| Resolution | `action_roll` | `fitd_engine.FITDActionRoll` |
| Resolution | `stress_track` | `fitd_engine.StressClock` |
| Resolution | `faction_clocks` | `clock.FactionClock` |
| Resolution | `doom_clock` | `clock.DoomClock` |
| Narrative | `quest_system` | `narrative_engine.NarrativeEngine` |
| Narrative | `npc_dialogue` | `narrative_engine.NarrativeEngine` |
| Narrative | `narrative_loom` | `narrative_loom.NarrativeLoomMixin` |
| Combat | `conditions` | `conditions.ConditionTracker` |
| Combat | `initiative` | `initiative.InitiativeTracker` |
| Progression | `progression_xp` | `progression.ProgressionTracker` |
| Progression | `rest` | `rest.RestManager` |
| Resource | `capacity` | `capacity_manager.check_capacity` |

**System Manifest Schema:**
```json
{
    "system_id": "dnd5e",
    "display_name": "Dungeons & Dragons 5th Edition",
    "engine_type": "spatial_dungeon",
    "engine_traits": ["conditions", "initiative", "rest", "progression_xp", "quest_system", "npc_dialogue", "narrative_loom"],
    "primary_loop": "spatial_dungeon",
    "resolution_mechanic": "d20_check",
    "stat_block_format": {"pattern_hint": "..."},
    "character_stats": ["str", "dex", "con", "int", "wis", "cha"],
    "damage_types": ["slashing", "piercing", ...],
    "currency": "gp",
    "progression": "xp_milestone",
    "classified_by": "manual",
    "confidence": 1.0
}
```

### 7.3 System Classifier (WO-V59.0)

**Script:** `scripts/classify_system.py`
- 13 heuristic rules + per-trait detection patterns
- LLM fallback (qwen3.5:2b) for confidence < 0.7
- `find_unmanifested_systems()` discovers vault dirs without manifests
- Generates `system_manifest.json` for new systems

---

## 8. Engine Stacking — Cross-System Campaigns

### 8.1 Overview (WO-V60.0)

**File:** `codex/core/engine_stack.py` (402 lines)

Engine stacking enables additive mechanic layering: characters accumulate mechanics from multiple game systems without losing prior abilities. When a campaign transitions from CBR+PNK to Scum & Villainy, the character's cyberpunk abilities become a dormant layer while the new spacefaring system drives the active game loop. Dormant commands remain accessible via fallthrough dispatch.

### 8.2 Core Classes

**MechanicLayer** — One system's contribution to a stacked character:
```python
@dataclass
class MechanicLayer:
    system_id: str              # "cbrpnk", "sav", "bitd", etc.
    engine_state: dict          # Full save_state() snapshot
    action_snapshot: dict       # {action_name: dot_value} at snapshot time
    dormant: bool = False       # True when not the active system
    timestamp: str = ""         # ISO-8601 creation time
```

**StackedCharacter** — Multi-system character wrapper:
```python
@dataclass
class StackedCharacter:
    name: str
    layers: List[MechanicLayer]
    active_system_id: str

    add_layer(system_id, engine_state, action_snapshot)  # Marks prior layers dormant
    get_layer(system_id) -> Optional[MechanicLayer]
    get_active_layer() -> Optional[MechanicLayer]
    merged_actions() -> Dict[str, int]                   # Union of all dots, max() on collision
```

**StackedCommandDispatcher** — Routes commands across active + dormant engines:
- Active engine gets first shot at every command
- If result contains "unknown command" / "unrecognized", falls through to dormant engines (reverse chronological)
- Dormant responses prefixed with `[SystemName]`
- `get_all_commands()` merges command lists from all layers for help display

### 8.3 Action Equivalence Map

13 cross-system action translations for seeding new-system action dots from prior layers:

| Source Action | Target Action | Route |
|---------------|---------------|-------|
| override | rig | CBR+PNK → SaV |
| scan | study | CBR+PNK → SaV |
| shoot | scrap | CBR+PNK → SaV |
| hunt | doctor | BitD → SaV |
| survey | study | BitD → SaV |
| tinker | rig | BitD → SaV |
| finesse | helm | BitD → SaV |
| prowl | skulk | BitD → SaV |
| skirmish | scrap | BitD → SaV |
| wreck | scrap | BitD → SaV |
| marshal | command | BoB → SaV |
| research | study | BoB → SaV |
| scout_action | skulk | BoB → SaV |
| maneuver | helm | BoB → SaV |
| discipline | command | BoB → SaV |

Shared action names (hack, study, scramble, scrap, skulk, attune, command, consort, sway) transfer automatically by name match — no equivalence entry needed.

### 8.4 Helper Functions

- `extract_action_map(engine)` — Read action dot values from a live engine's lead character. Uses `_SYSTEM_ACTIONS` registry for known systems; falls back to heuristic scanning (int fields in 0-4 range) for unknown systems
- `snapshot_engine(engine)` — Create a `MechanicLayer` from a live engine via `save_state()` + `extract_action_map()`
- `seed_actions(source_layers, target_system_id)` — Compute seed action dots for a new system using the equivalence map + direct name matching, taking max() across all source layers

### 8.5 System Actions Registry

Known action field names per FITD system (5 entries):

| System | Actions |
|--------|---------|
| cbrpnk | hack, override, scan, study, scramble, scrap, skulk, shoot, attune, command, consort, sway |
| sav | doctor, hack, rig, study, helm, scramble, scrap, skulk, attune, command, consort, sway |
| bitd | hunt, study, survey, tinker, finesse, prowl, skirmish, wreck, attune, command, consort, sway |
| bob | doctor, marshal, research, scout_action, maneuver, skirmish, wreck, consort, discipline, sway |
| candela | move, strike, control, sway, read, hide, survey, focus, sense |

### 8.6 Stacked Save Format (v2)

```python
{
    "format_version": 2,
    "stacked": True,
    "active_system_id": "sav",
    "character_name": "Kira",
    "layers": [
        {
            "system_id": "cbrpnk",
            "dormant": True,
            "timestamp": "2026-03-09T12:00:00+00:00",
            "engine_state": { ... full save_state() ... },
            "action_snapshot": {"hack": 2, "override": 1, ...}
        },
        {
            "system_id": "sav",
            "dormant": False,
            "timestamp": "2026-03-09T14:00:00+00:00",
            "engine_state": { ... full save_state() ... },
            "action_snapshot": {"hack": 2, "rig": 1, "helm": 2, ...}
        }
    ]
}
```

Backward compatible: legacy saves without `"stacked"` key load normally.

### 8.7 Wiring Chain

| Step | Trigger | Handler | What Happens |
|------|---------|---------|--------------|
| Save | `save` command | `_save_stacked()` | Detects stacked_char → writes format v2 JSON |
| Load | `codex_agent_main.py` | `_load_stacked_save()` | Detects `manifest.get("stacked")` → `main_stacked()` → reconstructs engines + dispatcher |
| Transition | `transition` command | `_transition_system()` | Snapshots current engine → seeds actions → creates new engine → builds StackedCommandDispatcher → hot-swaps |
| Dispatch | Every command | `dispatcher.dispatch()` | If stacked: active engine first, dormant fallthrough. Dormant responses prefixed with `[SystemName]` |
| Layers | `layers` command | `_show_layers()` | Displays all mechanic layers with active/dormant status |

### 8.8 Modified Files

| File | Changes |
|------|---------|
| `codex/core/engine_protocol.py` | Added `StackableEngine` protocol with `get_action_map()` |
| `codex/spatial/module_manifest.py` | Added `system_transitions` field + serialization |
| `play_universal.py` | `_show_layers()`, `_transition_system()`, `_save_stacked()`, `_load_stacked_save()`, `main_stacked()` entry point; `transition`/`layers` commands in both FITD and dungeon loops; dispatcher integration; stacked save detection |
| `codex_agent_main.py` | Load path detects stacked saves and routes to `run_universal_game()` |

### 8.9 Module Manifest: system_transitions

New field on `ModuleManifest` for declaring cross-system transition points:

```python
system_transitions: List[Dict] = []
# Example:
[{"target_system": "sav", "trigger": "zone_complete", "zone_id": "escape_pod"}]
```

Serialization: omitted from `to_dict()` when empty (backward compatible with old manifests).

---

## 9. Integrations & External Services

### 9.1 Mimir (Local LLM)

**File:** `codex/integrations/mimir.py`

- **Model:** "mimir" (custom Ollama Modelfile — Norse Skald persona, 0.5-1.7B parameter)
- **Endpoint:** `http://localhost:11434/api/generate`
- **Functions:**
  - `query_mimir(prompt, context, namespace, template_key)` → AI response
  - `search_rules_lore(prompt, context, system_id)` → FAISS retrieval + Mimir synthesis
  - `build_grapes_context(grapes_dict)` → world context formatting (~200 tokens)

**Narrative Frame (7-strategy enrichment):**
- `build_narrative_frame()` assembles: system context, sensory palette, affordance hints, delta-based room changes, memory shards, few-shot examples, room fragments

**Thermal-Gated Summarization (WO-V56.0):**
- RAG `summarize()` called in `search_rules_lore()` for 3+ chunks
- Skipped above 65°C CPU temperature

### 9.2 Forgotten Realms Wiki (Kiwix)

**File:** `codex/integrations/fr_wiki.py`

- **Source:** Custom ZIM file (67.3 MB, 34,625 articles) built via `scripts/scrape_fr_wiki.py`
- **Server:** kiwix-serve on port 8080
- **Multi-Source Fallback:** FR wiki ZIM (priority 1) → Wikipedia ZIM (priority 2)
- **Auto-Detection:** `_probe_sources()` extracts `book_id` from OPDS catalog
- **Setting Gate:** `FR_SETTINGS` frozenset (12 tags: forgotten_realms, sword_coast, waterdeep, barovia, etc.)
- **Usage:** `lore <topic>` command, NPC dialogue enrichment, module-load lore blurbs

### 9.3 RAG Service

**File:** `codex/core/services/rag_service.py`

- `RAGResult` typed handle: chunks, system_id, query, search_time_ms, summary
- `RAGService` singleton: FAISS search, multi-system search, Mimir summarization
- Thermal gating: Summarization skipped above 65°C
- Cache: 1-hour TTL for summarized results

### 9.4 Broadcast Event Bus

**File:** `codex/core/services/broadcast.py`

Thread-safe observer pattern with well-known events:

| Category | Events |
|----------|--------|
| Zones | EVENT_ZONE_COMPLETE, EVENT_ZONE_TRANSITION, EVENT_WORLD_MAP_TRAVEL |
| Memory | EVENT_HIGH_IMPACT, EVENT_CIVIC_EVENT, EVENT_NPC_WITNESS |
| Mechanics | EVENT_TRAIT_ACTIVATED, EVENT_FACTION_CLOCK_TICK |
| Combat | EVENT_INITIATIVE_ADVANCE, EVENT_CONDITION_CHANGE, EVENT_REST_COMPLETE |
| Session | EVENT_SESSION_RECAP |

### 9.5 Voice Services

- **Ears** (`codex/services/ears.py`): Speech-to-text via Whisper
- **Mouth** (`codex/services/mouth.py`): Text-to-speech via Piper
- **Butler Cooldown:** 3-second rate limit for narration (WO-V50.0)
- **Model:** "mimir" for fast voice responses

### 9.6 Port Registry

| Port | Service |
|------|---------|
| 8080 | kiwix-serve (FR wiki + Wikipedia ZIMs) |
| 11434 | Ollama (Mimir LLM) |

---

## 10. Test Coverage Map

### 10.1 Summary

- **Total Test Files:** 77
- **Total Tests:** 3,375 passing (0 failures)
- **Total Test Lines:** 37,765

### 10.2 Test Suite by Category

**Engine Tests:**

| File | Tests | Coverage |
|------|-------|----------|
| test_stc_engine_depth.py | 152 | STC/Cosmere engine depth |
| test_sav_engine_depth.py | 120 | Scum & Villainy depth |
| test_universal_game_loop.py | 55 | Universal routing & loops |
| test_quality_audit.py | 43 | Engine protocol compliance |
| test_bridge_movement.py | 38 | Bridge direction handling |
| test_subsetting_routing.py | 14 | Sub-setting resolution |

**Service Tests:**

| File | Tests | Coverage |
|------|-------|----------|
| test_service_dispatch.py | 41 | Service alias routing |
| test_rag_service.py | 27 | RAG retrieval + summarization |
| test_mechanics_suite.py | 62 | Clock, conditions, initiative, rest, progression |
| test_services_suite.py | 29 | Capacity, broadcast, narrative_loom, orchestrator |
| test_voice_bridge.py | 21 | Butler narration |
| test_npc_memory.py | 20 | NPC broadcast integration |

**Spatial & Module Tests:**

| File | Tests | Coverage |
|------|-------|----------|
| test_zone_wiring.py | 62 | Module zone pipeline |
| test_zone_pipeline.py | 15 | Zone load/advance |
| test_world_map.py | 41 | World generation |
| test_scene_interaction.py | 38 | Talk/investigate/unlock |
| test_scene_data.py | 12 | SceneData parsing |

**Discovery & Content Tests:**

| File | Tests | Coverage |
|------|-------|----------|
| test_system_discovery.py | 55 | Manifest auto-discovery [WO-V59.0] |
| test_content_pipeline.py | 49 | Content extraction [WO-V58.0] |
| test_setting_filter.py | 31 | Hierarchical sub-settings |

**Integration Tests:**

| File | Tests | Coverage |
|------|-------|----------|
| test_fr_wiki.py | 53 | FR wiki client + search |
| test_narrative_frame.py | 42 | Narrative frame enrichment |
| test_quest_system.py | 42 | Quest mechanics |
| test_quest_map_mimir.py | 31 | Quest markers + Mimir generation |

**Cross-Platform Tests:**

| File | Tests | Coverage |
|------|-------|----------|
| test_omni_parity.py | 36 | Discord/Telegram parity |
| test_parity_gap.py | 31 | Interface alignment |
| test_telegram_bot.py | 32 | Telegram async protocol |
| test_audio_narration.py | 23 | Audio narration wiring |

**Infrastructure Tests:**

| File | Tests | Coverage |
|------|-------|----------|
| test_boot_maestro.py | 20 | Boot chain + vault scanner |
| test_wo_v57_bugfixes.py | 22 | Bug fix validation |
| test_spell_data.py | 19 | Spell parsing |
| test_engine_stack.py | 47 | Engine stacking, cross-system campaigns [WO-V60.0] |
| test_dead_code_activation.py | — | Dead code resurrection [WO-V56.0] |

---

## 11. Ghost Audit — Dead Code Status

### 11.1 Activated Systems (WO-V56.0)

| System | Before | After |
|--------|--------|-------|
| DeltaTracker (BW) | Records visits but never reaches prompts | Delta narration in Mimir prompts via `_engine_ref` |
| DeltaTracker (D&D/STC) | Not instantiated | Instantiated, recording visits, saved/loaded |
| Memory Engine shards | Never injected | ANCHOR shards injected into Mimir prompts |
| `_engine_ref` | Never set | Set on NarrativeEngine → unlocks narrative frame |
| `build_narrative_frame()` | Called but delta/shard paths unreachable | Full enrichment pipeline active |
| `RAG.summarize()` | Never called | Called in `search_rules_lore()` (thermal-gated) |
| Zone broadcast events | Fire but no subscribers | Subscribers in dungeon loop for UI feedback |
| TraitHandler | No resolvers registered | Burnwillow resolver (21 traits) registered + wired |
| `synthesize_narrative()` | Crown only | Session recap on all engine exits |

### 11.2 Intentionally Inactive

| System | Reason |
|--------|--------|
| `RAG.validate()` + ManifoldGuard | Regex-based claim extraction is fragile; adds latency on Pi 5 |
| `broadcast_cross_module()` | No cross-module scenarios exist yet |
| `HybridGameOrchestrator` | Partially superseded by Engine Stacking (WO-V60.0); CRS gating still useful for validation |
| `legacy_import/` + `archive/` | Historical files, not dead code |

---

## Appendix A: Work Order History (V42.0 — V60.0)

| WO | Title | Deployed | Key Changes |
|----|-------|----------|-------------|
| V42.0 | PDF Extraction | 2026-02-27 | Replaced 21 fabricated data files with PDF-sourced content |
| V43.0 | Hierarchical Sub-Settings | 2026-02-28 | setting_filter.py, STC Roshar sub-setting, parent vault merge |
| V44.0 | Narrative Overhaul | 2026-03-01 | Quest triggers, turn-in UI, dungeon NPC quests, haven events |
| V45.0 | Quest Map Markers | 2026-03-01 | Map quest markers, broadcast wiring, Mimir quest generation, rumor board |
| V46.0–V48.0 | (Various) | 2026-03 | Setting IDs on FITD engines, DeltaTracker wiring |
| V49.0 | Parity & Polish | 2026-03-06 | Movement normalization, sub-setting resolution, system-aware help |
| V50.0 | Audio Narration | 2026-03-06 | Butler cooldown, bridge narration, Telegram parity |
| V51.0 | Foundation Sprint | 2026-03-06 | 91 new tests, adventure module wiring, SceneData, villain paths |
| V52.0 | Scene Interaction | 2026-03-06 | 6 new bridge commands, FITD narrative runner, save fix |
| V53.0 | Module Zone Pipeline | 2026-03-06 | load_dungeon_graph(), _apply_content_hints() for D&D 5e + STC |
| V54.0 | Playability Sprint | 2026-03-07 | Spatial map rendering, service dispatch, NPC dialogue, audio triggers |
| V55.0 | FR Wiki Integration | 2026-03-07 | FRWikiClient, Kiwix multi-source, NPC lore enrichment |
| V56.0 | Dead Code Resurrection | 2026-03-08 | _engine_ref wiring, DeltaTracker activation, TraitHandler, session recap |
| V57.0 | Bug Fixes + Infrastructure | 2026-03-08 | Room interface fix, module manifest persistence, 185 D&D 5e monsters |
| V58.0 | Content Extraction | 2026-03-08 | build_content.py, config_loader.py, 5 extractors, config JSON |
| V59.0 | System Discovery | 2026-03-08 | engine_traits.py, system_discovery.py, classify_system.py, 9 manifests |
| V60.0 | Engine Stacking | 2026-03-09 | engine_stack.py (MechanicLayer, StackedCharacter, StackedCommandDispatcher), StackableEngine protocol, system_transitions on ModuleManifest, stacked save/load/transition in play_universal.py |

---

## Appendix B: Reference Data Policy

**WO-V41.0 Incident:** 21 fabricated reference data files created without PDF source.
**WO-V42.0 Resolution:** All replaced with PDF-sourced extraction.

**Policy:**
1. **Source-First:** ALWAYS read PDFs from vault BEFORE writing reference data
2. **Two-Pass:** Pass 1 extracts raw data. Pass 2 structures into Python dicts
3. **Validation:** Tests assert against independent ground truth, not fabricated data

---

*Generated 2026-03-09 by Claude Opus 4.6 — independent source-level extraction*

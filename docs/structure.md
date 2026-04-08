# C.O.D.E.X. System Architecture (2026-04-08)

## Repository Layout

```
Codex/
├── CLAUDE.md                       # Claude Code guidance (project instructions)
├── requirements.txt                # Python dependencies
│
├── codex/                          # Main package
│   ├── core/                       # Core intelligence layer
│   │   ├── architect.py            # Sovereign Duo Router (mimir + LiteRT-LM)
│   │   ├── butler.py               # Reflex handler chain
│   │   ├── cortex.py               # Thermal/RAM homeostasis
│   │   ├── autopilot.py            # Companion AI + scene narration
│   │   ├── dm_tools.py             # GM queries, loot, NPC, summarization
│   │   ├── dm_dashboard.py         # In-session GM dashboard
│   │   ├── command_handlers.py     # Shared commands (!help, !status, etc.)
│   │   ├── config_loader.py        # YAML/JSON config loading
│   │   ├── companion_maps.py       # get_native_role() — system-native class names
│   │   ├── dice.py                 # Visual dice (unwired)
│   │   ├── engine_protocol.py      # GameEngine/DiceEngine/PartyEngine protocols
│   │   ├── engine_stack.py         # Stackable engine composition
│   │   ├── engine_traits.py        # Shared engine trait mixins
│   │   ├── system_discovery.py     # Auto-discovers installed game systems
│   │   ├── mechanics/              # Shared game mechanics
│   │   │   ├── clock.py            # Progress clocks (FITD)
│   │   │   ├── conditions.py       # Status conditions
│   │   │   ├── initiative.py       # Turn order
│   │   │   ├── rest.py             # Short/long rest
│   │   │   ├── progression.py      # XP + level-up
│   │   │   └── journey.py          # Travel events
│   │   └── services/               # Shared services
│   │       ├── litert_engine.py    # LiteRT-LM singleton (Gemma 4 E2B)
│   │       ├── fitd_engine.py      # FITD shared core (FITDActionRoll, clocks)
│   │       ├── rag_service.py      # RAG retrieval wrapper
│   │       ├── librarian.py        # FAISS query interface
│   │       ├── broadcast.py        # Multi-channel output
│   │       ├── narrative_loom.py   # Cross-shard narrative synthesis (unwired)
│   │       └── system_gm_profiles.json  # 10 GM persona profiles
│   │
│   ├── games/                      # Game system engines
│   │   ├── burnwillow/             # Custom aether/rot magic system
│   │   ├── crown/                  # Crown & Crew (in design)
│   │   ├── bitd/                   # Blades in the Dark
│   │   ├── sav/                    # Scum and Villainy
│   │   ├── bob/                    # Band of Blades
│   │   ├── cbrpnk/                 # Cyberpunk FITD
│   │   ├── candela/                # Candela Obscura
│   │   ├── dnd5e/                  # D&D 5th Edition
│   │   ├── stc/                    # Starforged/STC
│   │   └── ashburn/                # Ashburn (tarot-based)
│   │
│   ├── spatial/                    # Map + zone system
│   │   ├── map_engine.py           # BSP dungeon generation
│   │   ├── map_renderer.py         # Rich terminal renderer
│   │   ├── module_manifest.py      # Module metadata registry
│   │   ├── zone_manager.py         # Zone JSON loader + navigation
│   │   └── scene_data.py           # Scene state container
│   │
│   ├── forge/                      # Character + content creation
│   │   ├── char_wizard.py          # State-driven character creation
│   │   ├── source_scanner.py       # PDF source extraction
│   │   ├── content_pool.py         # Loot/encounter tables
│   │   ├── adapter.py              # System-specific data adapters
│   │   ├── codex_transmuter.py     # Cross-system conversion (unwired)
│   │   └── loot_tables.py          # Loot generation
│   │
│   ├── world/                      # World generation
│   │   ├── genesis.py              # Procedural world gen (unwired)
│   │   └── world_wizard.py         # Interactive world builder (unwired)
│   │
│   ├── services/                   # External service wrappers
│   │   ├── ears.py                 # STT service (port 5000)
│   │   └── mouth.py                # TTS service (port 5001)
│   │
│   ├── bots/                       # Chat interfaces
│   │   ├── discord_bot.py          # Discord interface
│   │   └── telegram_bot.py         # Telegram interface
│   │
│   └── integrations/               # External knowledge
│       ├── mimir.py                # Ollama mimir query wrapper
│       ├── tarot.py                # Ashburn tarot (TAROT_AVAILABLE, unwired)
│       ├── fr_wiki.py              # FR Wiki via Kiwix
│       └── vault_processor.py      # PDF ingestion
│
├── config/                         # System configuration
│   ├── systems/                    # Per-system YAML configs
│   ├── tables/                     # Quest hooks, loot tables
│   └── magic_items/                # Magic item config by system
│
├── vault_maps/                     # Zone definition files (JSON)
│   └── modules/
│       └── dragon_heist/           # 7 zone files (Gemma Polish in progress)
│
├── faiss_index/                    # FAISS knowledge bases (v3 format)
│   ├── dnd5e/                      # docstore.json + index.faiss
│   ├── burnwillow/
│   ├── bitd/                       # 743 chunks
│   ├── sav/                        # 695 chunks
│   ├── bob/                        # 826 chunks
│   ├── stc/                        # 3289 chunks
│   ├── cbrpnk/
│   ├── candela/
│   └── codebase/
│
├── scripts/                        # Offline pipeline tools
│   ├── build_indices.py            # FAISS v3 builder (merge mode, OCR quality)
│   ├── build_content.py            # 9 extractors, 6 system profiles
│   ├── verify_content.py           # Source-match audit (v3 aware)
│   ├── reextract_zones.py          # Gemma Polish zone extraction
│   ├── enrich_module.py            # Mimir-enhanced room enrichment
│   ├── generate_module.py          # Zone JSON from content pool
│   └── refdata_to_config.py        # reference_data → config JSON
│
├── maintenance/
│   ├── codex_maestro.py            # Maintenance menu (incl. [P] single PDF index)
│   └── codex_boot_wizard.py        # Boot wizard (shows gemma4:e2b LiteRT-LM)
│
├── tests/                          # Test suite (6,672 passing)
│
└── docs/
    ├── SYSTEM_CAPABILITIES.md      # This system's capabilities (updated)
    └── structure.md                # This file
```

---

## Sovereign Duo Router Flow

```
                      ┌─────────────────────────────────────┐
                      │           USER INPUT                 │
                      │   (Discord / Terminal / Voice)       │
                      └──────────────┬──────────────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────────────┐
                      │      codex/core/butler.py            │
                      │      Reflex Handler Chain            │
                      │                                     │
                      │  check_reflex(input) → response?    │
                      │  YES → instant reply (no model)     │
                      │  NO  → pass to Architect            │
                      └──────────────┬──────────────────────┘
                                     │ (no reflex match)
                                     ▼
                      ┌─────────────────────────────────────┐
                      │      codex/core/architect.py         │
                      │      Sovereign Duo Router            │
                      │                                     │
                      │  analyze_complexity(query)          │
                      │  → REFLEX or ACADEMY                │
                      └──────────────┬──────────────────────┘
                                     │
               ┌─────────────────────┴─────────────────────┐
               │                                           │
               ▼                                           ▼
   ┌───────────────────────┐                 ┌─────────────────────────┐
   │  REFLEX MODE          │                 │  ACADEMY MODE           │
   │  (always available)   │                 │  (thermal-gated)        │
   └───────────┬───────────┘                 └────────────┬────────────┘
               │                                          │
               │                                          ▼
               │                          ┌─────────────────────────────┐
               │                          │   codex/core/cortex.py      │
               │                          │   Thermal Gate              │
               │                          │                             │
               │                          │  OPTIMAL → LiteRT-LM ✅     │
               │                          │  FATIGUED → Ollama mimir    │
               │                          │  CRITICAL → mimir only      │
               │                          └────────────┬────────────────┘
               │                                       │
               │               ┌───────────────────────┤
               │               │                       │
               ▼               ▼                       ▼
   ┌───────────────────┐  ┌────────────────┐  ┌────────────────────────┐
   │   Ollama          │  │  LiteRT-LM     │  │  Ollama (degraded)     │
   │   qwen2.5:0.5b    │  │  gemma4:e2b    │  │  qwen2.5:0.5b          │
   │   (Mimir)         │  │  (CoD:EX)      │  │  (Mimir, FATIGUED)     │
   │   ~400 MB RAM     │  │  ~1.5 GB RAM   │  │  ~400 MB RAM           │
   │   <2s latency     │  │  7.6 tok/s     │  │  <2s latency           │
   └─────────┬─────────┘  └───────┬────────┘  └──────────┬─────────────┘
             │                    │                       │
             └────────────────────┴───────────────────────┘
                                  │
                                  ▼
                      ┌─────────────────────────────────────┐
                      │   FAISS Retrieval (optional)         │
                      │   codex/core/services/librarian.py   │
                      │   9 docstores, v3 format             │
                      │   nomic-embed-text embeddings        │
                      └──────────────┬──────────────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────────────┐
                      │   Output                             │
                      │   Discord / Terminal / TTS           │
                      └─────────────────────────────────────┘
```

---

## Thermal State Machine

```
     ┌─────────────────┐      >65°C      ┌─────────────────┐
     │    OPTIMAL      │ ──────────────► │    FATIGUED     │
     │    (GREEN)      │                 │    (YELLOW)     │
     │                 │ ◄────────────── │                 │
     │  LiteRT-LM: YES │  <60°C + 30s   │  LiteRT-LM: NO  │
     │  Mimir: YES     │                 │  Mimir: YES     │
     │  Companion: YES │                 │  Companion: NO  │
     └─────────────────┘                 └────────┬────────┘
                                                  │ >75°C
                                                  ▼
                                         ┌─────────────────┐
                                         │    CRITICAL     │
                                         │    (RED)        │
                                         │                 │
                                         │  LiteRT-LM: KILL│
                                         │  Mimir: MINIMAL │
                                         │  flush_vram()   │
                                         └────────┬────────┘
                                                  │ <70°C
                                                  ▼
                                         ┌─────────────────┐
                                         │   RECOVERY      │
                                         │   (COOLDOWN)    │
                                         │   30s minimum   │
                                         └─────────────────┘
```

---

## Model Routing Matrix

| Scenario | Thermal | Model | Latency |
|----------|---------|-------|---------|
| `!roll 1d20` | Any | Butler reflex (no model) | <100ms |
| Simple question | Any | qwen2.5:0.5b (mimir) | <2s |
| GM narration | OPTIMAL | gemma4:e2b (LiteRT-LM) | 5-15s |
| GM narration | FATIGUED | qwen2.5:0.5b (mimir) | <2s |
| Companion dialogue | OPTIMAL | gemma4:e2b (max 80 tok) | ~5s |
| Companion dialogue | FATIGUED | mimir narration | <2s |
| Companion dialogue | CRITICAL | Static template | <100ms |
| Session summary | OPTIMAL | gemma4:e2b | 10-20s |
| RAG knowledge query | Any | nomic-embed → mimir | <5s |

---

## FAISS Docstore v3 Format

```json
{
  "version": 3,
  "docstore": {
    "chunk_id": {
      "text": "[Source Tag] page content...",
      "meta": {
        "source": "Waterdeep_ Dragon Heist",
        "system_id": "dnd5e",
        "page_start": 42,
        "page_end": 43,
        "quality": 0.79
      }
    }
  }
}
```

**Quality score**: `len(alpha chars) / len(total chars)` — OCR garble detector (NOT reading accuracy). Thresholds: page < 0.40 skipped, chunk < 0.45 skipped.

---

## Companion AI: Native Role System

```python
# codex/core/companion_maps.py
get_native_role(system_id, archetype) -> str

# archetype "vanguard" resolves to:
# bitd    → "Cutter"
# sav     → "Muscle"
# bob     → "Heavy"
# cbrpnk  → "Punk"
# candela → "Face"
# dnd5e   → "Fighter"
# stc     → "Windrunner"
# crown   → "Soldier"
```

Companion dialogue system prompt: `{personality} You are playing the role of {native_role} in this {system} adventure.`

---

## Coder Sandbox (Extracted 2026-04-07)

The qwen2.5-coder:1.5b sandbox was extracted from Codex to its own project:

```
~/Projects/claude_sandbox/Architect_Sandbox/
├── coder_engine.py     # CoderEngine: async Ollama client + _DESTRUCTIVE_PATTERNS validation
├── sandbox.py          # CLI: one_shot() and repl()
└── test_coder_engine.py  # 8 tests (sandbox validation)
```

**Why extracted:** Reduces Codex complexity; coder sandbox has no gameplay role. Architect no longer routes to `qwen2.5-coder:1.5b` for any game-loop path.

---

## Critical Invariants

1. **Thermal Interlock**: LiteRT-LM (Gemma 4) never runs outside OPTIMAL thermal state.
2. **Companion Thermal Gate**: Companion dialogue is OPTIMAL-only; degrades to mimir then static.
3. **LiteRT-LM Singleton**: One `LiteRTEngine` instance shared across Architect, dm_tools, autopilot. One conversation at a time — `del conv` before `create_conversation()`.
4. **VRAM Flush on CRITICAL**: `cortex._flush_vram()` stops Ollama models AND calls `litert_engine.unload()`.
5. **Source-First Policy**: ALL zone file content must originate from source PDFs via FAISS. Training data is a hallucination risk. See `memory/reference_data_policy.md`.
6. **Graceful Degradation**: Every LLM call has a fallback. Gemma → mimir → static. Never a hard failure.
7. **Save Format v2**: `{"format_version": 2, "stacked": true, "layers": [...]}`.

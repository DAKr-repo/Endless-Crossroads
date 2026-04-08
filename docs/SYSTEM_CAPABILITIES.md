# SYSTEM_CAPABILITIES.md

A brutally honest summary of what C.O.D.E.X. can and cannot do as of the current codebase (2026-04-08).

---

## System Overview: The "Sovereign Duo" Architecture

C.O.D.E.X. is a multi-interface TTRPG GM assistant running on a Raspberry Pi CM5 (16 GB).

| Layer | Module | Role | Status |
|-------|--------|------|--------|
| **Body** | `codex/core/cortex.py` | Thermal homeostasis + RAM guard | ✅ Fully functional |
| **Mind** | `codex/core/architect.py` | Sovereign Duo Router + model orchestration | ✅ Functional |
| **Butler** | `codex/core/butler.py` | Reflex handler chain (instant commands) | ✅ Functional |
| **DM Tools** | `codex/core/dm_tools.py` | GM queries, loot, NPC, summarization | ✅ Functional |
| **Autopilot** | `codex/core/autopilot.py` | Companion AI + scene narration | ✅ Functional |
| **Games** | `codex/games/*/` | 10 game system engines | ✅ All functional |
| **Spatial** | `codex/spatial/` | BSP dungeon maps + zone manager | ✅ Functional |
| **Forge** | `codex/forge/` | Character creation + content pipeline | ✅ Functional |
| **Voice** | `codex/services/ears.py`, `mouth.py` | STT (port 5000) + TTS (port 5001) | ✅ Ready (separate processes) |
| **Discord** | `codex/bots/discord_bot.py` | Discord interface | ✅ Functional |
| **FAISS** | `faiss_index/` | 9 knowledge bases (v3 format) | ✅ Functional |

---

## Model Stack

### Live Models

| Role | Model | Runtime | RAM | Thermal Gate |
|------|-------|---------|-----|-------------|
| **Mimir** (Reflex/Voice) | qwen2.5:0.5b | Ollama | ~400 MB | None (always available) |
| **CoD:EX** (Academy/Companion) | gemma4:e2b | LiteRT-LM | ~1.5 GB | OPTIMAL only |
| **nomic-embed-text** | Embeddings | Ollama | ~274 MB | None |

**Retired**: qwen3:1.7b, deepseek-r1:1.5b, qwen2.5-coder:1.5b, llama3.2:1b
**Extracted**: qwen2.5-coder:1.5b coder sandbox → `~/Projects/claude_sandbox/Architect_Sandbox/`

### RAM Budget

| Component | RAM |
|-----------|-----|
| OS + services | ~2.5 GB |
| Ollama (mimir + nomic) | ~800 MB |
| LiteRT-LM (gemma4:e2b) | ~1.5 GB |
| **Total inference** | **~4.8 GB** |
| **Free (typical)** | **~11.2 GB** |

---

## Module Analysis

### `codex/core/cortex.py` — The Body ✅ FULLY IMPLEMENTED

**What it does:**
- Reads CPU temperature via `psutil.sensors_temperatures()` (`cpu_thermal` sensor)
- Reads RAM via `psutil.virtual_memory()`
- 4-state machine: OPTIMAL → FATIGUED → CRITICAL → RECOVERY
- Hysteresis: must drop 5°C below threshold AND wait 30s to return to OPTIMAL
- `_flush_vram()` on RAM DANGER: stops Ollama models + calls `LiteRTEngine.unload()`
- Generates "Pain Signal" messages at CRITICAL; enforces brevity via system prompt modifiers

**Thresholds (hardcoded in CortexConfig):**
- OPTIMAL: < 65°C
- FATIGUED: 65-75°C (mimir only)
- CRITICAL: > 75°C (minimal responses, flush VRAM)

**Limitations:**
- No GPU monitoring
- Thresholds not configurable at runtime (file-backed config not wired)

---

### `codex/core/architect.py` — The Mind ✅ SOVEREIGN DUO ROUTER

**What it does:**
- Routes queries between two model paths: **mimir** (Ollama) and **codex** (LiteRT-LM)
- `_LITERT_MODELS: set[str] = {"codex"}` — any model in this set bypasses Ollama
- `_call_litert()` / `_stream_litert()` — async wrappers around LiteRTEngine
- `_call_ollama()` — HTTP POST to `localhost:11434/api/generate`
- Thermal gate: LiteRT-LM only runs at OPTIMAL; degrades to mimir at FATIGUED/CRITICAL
- Streaming (`invoke_stream()`) supported for both paths

**Routing logic:**
```
query → complexity heuristic → REFLEX or ACADEMY
ACADEMY + OPTIMAL thermal → gemma4:e2b via LiteRT-LM
ACADEMY + FATIGUED/CRITICAL → qwen2.5:0.5b via Ollama
REFLEX → qwen2.5:0.5b via Ollama (always)
```

**Removed (dead code cleanup 2026-04-07):**
- `SANDBOX_DIR`, `MODEL_NARRATIVE`, `MODEL_EXPERIMENTAL`
- `ThinkingMode.EXPERIMENTAL`, `_validate_coder_sandbox()`, `_detect_code_request()`
- `COMPLEXITY_CODE_KEYWORDS`, `EXPERIMENTAL_TIMEOUT_MS`

---

### `codex/core/services/litert_engine.py` — LiteRT-LM Singleton ✅ NEW (2026-04-07)

**What it does:**
- Wraps Google's `litert_lm` Python SDK for Gemma 4 E2B inference
- Singleton (`get_litert_engine()`) — shared by Architect, dm_tools, autopilot
- Lazy loading — model loads on first call, not at startup
- `generate_sync(prompt, system, max_tokens)` → `(str, int)` — used in dm_tools
- `generate(prompt, system, max_tokens)` → async wrapper via `run_in_executor`
- `generate_stream(prompt, system)` → `AsyncIterator[str]`
- `unload()` — releases 1.5 GB on thermal flush
- System prompt injected as first user turn (Gemma chat format)
- One-conversation-at-a-time limitation enforced: `del conv` before new `create_conversation()`

**LiteRT-LM API pattern:**
```python
engine = litert_lm.LiteRtLmEngine(model_path=...)
conv = engine.create_conversation()
result = conv.send_message(messages)
# result = {'content': [{'text': '...'}], 'role': 'assistant'}
```

**Known limitation:** One active conversation at a time; concurrent calls are serialized via asyncio lock.

---

### `codex/core/dm_tools.py` — GM Query Tools ✅ FUNCTIONAL

**Key functions:**
- `query_codex(prompt, system)` → calls `LiteRTEngine.generate_sync()` (Gemma 4)
- `summarize_context(history)` → calls `LiteRTEngine.generate_sync()` (Gemma 4)
- `query_mimir(prompt, system)` → Ollama HTTP call (qwen2.5:0.5b)
- `search_knowledge(query, system_id)` → FAISS retrieval + mimir synthesis
- `generate_loot(cr, theme)`, `generate_npc(role)`, `generate_encounter(biome, cr)`

---

### `codex/core/autopilot.py` — Companion AI ✅ WIRED (2026-04-07)

**What it does:**
- `companion_dialogue(context, event)` — Gemma 4 generates in-character companion speech
  - System prompt: companion personality + native role name for the current game system
  - Max 80 tokens; thermal-gated (OPTIMAL only)
  - 3-tier fallback: Gemma 4 → mimir narration → static templates
- `_native_role(system_id, archetype)` → calls `get_native_role()` from `companion_maps.py`
- `narrate_action(action, result, context)` — wraps companion dialogue into scene narration

**Native role examples (via `companion_maps.py`):**
| Archetype | BitD | STC | D&D 5e | Crown | BoB |
|-----------|------|-----|--------|-------|-----|
| vanguard | Cutter | Windrunner | Fighter | Soldier | Heavy |
| trickster | Slide | Infiltrator | Rogue | Scout | Skirmisher |
| support | Whisper | Mystic | Cleric | Medic | Pilot |

---

### Game Engines — 10 Systems ✅ ALL FUNCTIONAL

| System | Engine | Notes |
|--------|--------|-------|
| Burnwillow | `games/burnwillow/engine.py` | Custom aether/rot magic system |
| Crown | `games/crown/engine.py` | In design (campaigns dir exists) |
| BitD / SaV / BoB / CbRPNK / Candela | `games/*/engine.py` via FITD shared core | fitd_engine.py FITDActionRoll |
| D&D 5e | `games/dnd5e/engine.py` | Full 5e rules; FAISS knowledge base |
| STC | `games/stc/engine.py` | 3289-chunk FAISS index |

**ENGINE_REGISTRY** (8 entries in `engine_protocol.py`): fitd, bitd, sav, bob, cbrpnk, candela, dnd5e, stc

---

### FAISS Knowledge Bases — v3 Format ✅ (2026-04-07)

**9 docstores**: dnd5e, burnwillow, bitd (743 chunks), sav (695), bob (826), stc (3289), cbrpnk, candela, codebase

**Docstore v3 chunk format:**
```json
{
  "text": "[Source Tag] chunk content...",
  "meta": {
    "source": "Source Tag",
    "system_id": "dnd5e",
    "page_start": 42,
    "page_end": 43,
    "quality": 0.79
  }
}
```

**Quality score**: Alpha ratio (`len(a-zA-Z chars) / total chars`). OCR garble detector, NOT accuracy. Expected: 75-87% for clean digital PDFs; D&D stat blocks legitimately lower it.

**Chunk filtering thresholds:**
- Pages with quality < 0.40 skipped entirely (heavily garbled)
- Chunks with quality < 0.45 skipped
- TOC pages, pronunciation guides, fragments < 80 chars excluded

**`--pdf` merge mode** (build_indices.py): strips old same-source chunks, appends new — preserves all other system chunks. Does NOT rebuild entire index.

---

### `scripts/reextract_zones.py` — Gemma Polish Pipeline ✅ NEW (2026-04-07)

Replaces hallucinated/OCR-garbled zone file content with source-grounded text.

**Pipeline:**
1. Load all chunks from docstore filtered by source tag
2. Keyword search to find relevant chunks per room
3. Filter chunks: alpha ratio > 0.6 (removes heavy garble)
4. **Gemma Polish** (3 LiteRT-LM calls per room):
   - Description: OCR chunks + draft → 2-3 sentence GM description
   - Read-aloud: OCR chunks + draft → boxed read-aloud text (second person)
   - NPCs: only named NPCs physically at the location
5. Write updated zone JSON (backup in `.bak_20260407/`)

**Usage:**
```bash
python scripts/reextract_zones.py --module dragon_heist --system dnd5e
python scripts/reextract_zones.py --module dragon_heist --system dnd5e --dry-run
```

---

### Content Pipeline ✅ FUNCTIONAL

- `scripts/build_content.py`: 9 extractors, 6 system profiles
- `scripts/build_indices.py`: FAISS v3 builder with merge mode, OCR quality scoring
- `scripts/verify_content.py`: source-match audit (handles v3 dict entries)
- `scripts/enrich_module.py`: Mimir-enhanced room content
- `scripts/generate_module.py`: generates zone JSON from content pool

---

### Spatial System ✅ FUNCTIONAL

- `codex/spatial/map_engine.py`: BSP dungeon generation → DungeonGraph → RoomNode → PopulatedRoom
- `codex/spatial/zone_manager.py`: loads zone JSON, tracks player position, room connections
- `codex/spatial/module_manifest.py`: module metadata and zone registry

**Dragon Heist modules** (7 zone files): Trollskull Alley, Kolat Towers, Cassalanter Estate, Gralhund Villa, Dock Ward, Sea Maidens Faire, Manshoon Sanctum

---

### Maintenance Tools ✅ UPDATED

- `maintenance/codex_maestro.py`: Full maintenance menu
  - `[P]` — **Index Single PDF** (new 2026-04-07): pick system → pick PDF → `build_indices.py --pdf`
  - Other options: full rebuild, verify, audit, zone enrichment
- `maintenance/codex_boot_wizard.py`: Boot wizard — model display shows `gemma4:e2b (LiteRT-LM)`

---

## External Dependencies

| Dependency | Required | Port/Path | Used For |
|------------|----------|-----------|----------|
| **Ollama** | ✅ Critical | localhost:11434 | mimir + nomic embeddings |
| `qwen2.5:0.5b` | ✅ Critical | Ollama | Mimir reflex + voice |
| `nomic-embed-text` | ✅ Critical | Ollama | FAISS query embeddings |
| **LiteRT-LM** | ✅ Critical | Python SDK | Gemma 4 E2B inference |
| `gemma-4-E2B-it.litertlm` | ✅ Critical | `~/.cache/litert-lm/` | Academy + Companion AI |
| **Ears (STT)** | ⚠️ Optional | Port 5000 | Speech-to-text |
| **Mouth (TTS)** | ⚠️ Optional | Port 5001 | Text-to-speech (Piper) |
| **Kiwix** | ⚠️ Optional | Port 8080 | FR Wiki (34,625 articles) |
| **FFmpeg** | ⚠️ For voice | PATH | Discord voice audio |
| `DISCORD_TOKEN` | ✅ For Discord | `.env` | Bot authentication |

---

## Test Suite

- **6,672 tests passing, 0 failures** (as of 2026-04-07)
- `pytest tests/` — full suite
- `pytest tests/test_architect.py` — routing tests (coder sandbox tests removed)
- `pytest tests/test_dm_dashboard.py` — dm_tools tests (patched for LiteRT-LM)
- `pytest tests/test_quality_audit.py` — Burnwillow combo validation

---

## Summary: What Works

### Fully Operational
- ✅ Thermal monitoring + 4-state machine with hysteresis
- ✅ Sovereign Duo routing (mimir + Gemma 4 via LiteRT-LM)
- ✅ 10 TTRPG game system engines
- ✅ FAISS retrieval across 9 knowledge bases
- ✅ Character creation wizards (all 6 FITD systems + D&D 5e)
- ✅ BSP dungeon generation + zone navigation
- ✅ Companion AI with system-native role names
- ✅ Gemma Polish source extraction pipeline
- ✅ Discord bot + Discord dashboard (DM screen)
- ✅ Voice STT/TTS (Ears + Mouth services)
- ✅ Session summarization via Gemma 4

### Known Incomplete Features (built, never wired)
- `codex/core/dice.py` — Rich dice animation (imported but handler missing)
- `codex/world/genesis.py` — Procedural world generator (imported, handler missing)
- `codex/integrations/tarot.py` — Ashburn tarot (TAROT_AVAILABLE=True, never rendered)
- `codex/core/services/narrative_loom.py` — Cross-shard synthesis (tested, not in engines)
- `codex/forge/codex_transmuter.py` — Cross-system character conversion (no imports)

### Pending Work
- Dragon Heist zone re-extraction (Gemma Polish in progress)
- Other D&D module re-extraction: Mad Mage, Rime of Frostmaiden, Tyranny of Dragons
- Rebuild other system indices to v3: bitd, bob, sav, cbrpnk, candela
- Web UI (#232, #233, #235)
- Coppermind/Cosmere Wiki to Kiwix
- STC + non-D&D zone file audits (#160, #162)

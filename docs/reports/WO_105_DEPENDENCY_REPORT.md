# WO-105: Dependency Mapping & Package Structure Report

**Status:** DEPLOYED
**Date:** 2026-02-11
**Scope:** Forensic inventory, path hardening, graveyard cleanup, package skeleton

---

## Executive Summary

Project Codex has grown to **55 Python files** in a flat root directory. This work order performs a complete dependency audit, eliminates dead code, hardens all relative path references, and lays the `codex/` package foundation for the future migration (separate WO).

### Actions Taken

| Action | Count | Details |
|--------|-------|---------|
| Files deleted | 3 | `codex_journal_ui.py`, `state_manager.py`, `codex_dynamic_power.py` |
| Files archived | 2 | `codex_tools.py`, `codex_discord_ui.py` -> `archive/` |
| Files moved | 1 | `debug_token.py` -> `scripts/` |
| Hardcoded paths fixed | 10 | Across 7 files (Priority 1 + 2) |
| Package created | 1 | `codex/` with `__init__.py` + `paths.py` |

---

## Phase 1: Module Inventory

### Entry Points (11 files with `__main__`)

| File | Role | Description |
|------|------|-------------|
| `codex_agent_main.py` | Hub Orchestrator | Main entry. Terminal UI + Discord + Telegram + all engines |
| `play_burnwillow.py` | Game Entry | Interactive roguelike dungeon crawler |
| `play_crown.py` | Game Entry | Crown & Crew terminal launcher |
| `codex_ears.py` | Service | FastAPI STT on :5000 |
| `codex_mouth.py` | Service | FastAPI TTS on :5001 |
| `codex_discord_bot.py` | Bot | Discord interface |
| `codex_telegram_bot.py` | Bot | Telegram mirror protocol |
| `codex_world_engine.py` | Tool | World creation wizard |
| `codex_char_wizard.py` | Tool | Character builder |
| `vault_processor.py` | Tool | Equipment extractor from PDFs |
| `ask_mimir.py` | Tool | Ollama CLI bridge |

### Core Libraries (24 files)

| File | Tier | Imported By |
|------|------|-------------|
| `burnwillow_module.py` | 0 | play_burnwillow, codex_adapter, codex_burnwillow_bridge, tests |
| `codex_crown_module.py` | 0 | codex_agent_main, discord_bot, telegram_bot, play_crown, ashburn |
| `codex_cortex.py` | 0 | codex_agent_main, codex_architect |
| `codex_butler.py` | 0 | codex_agent_main, codex_ears |
| `codex_map_engine.py` | 0 | play_burnwillow, codex_burnwillow_bridge, examples |
| `codex_map_renderer.py` | 0 | play_burnwillow, examples |
| `codex_source_scanner.py` | 0 | codex_char_wizard, codex_omni_forge |
| `codex_architect.py` | 1 | codex_agent_main |
| `codex_adapter.py` | 1 | codex_agent_main |
| `codex_omni_forge.py` | 1 | codex_discord_bot |
| `codex_burnwillow_bridge.py` | 2 | codex_discord_bot, codex_telegram_bot |
| `volo_manifold_guard.py` | 0 | codex_agent_main |
| `codex_dice_engine.py` | 0 | codex_agent_main |
| `codex_memory_engine.py` | 0 | standalone |
| `codex_genesis_engine.py` | 0 | codex_agent_main |
| `ashburn_crew_module.py` | 1 | codex_agent_main |
| `ashburn_tarot.py` | 0 | codex_agent_main |
| `burnwillow_content.py` | 0 | standalone |
| `burnwillow_zone1.py` | 0 | standalone |
| `burnwillow_persistence.py` | 0 | burnwillow_integration_example |
| `burnwillow_ui.py` | 0 | test_burnwillow_ui |
| `burnwillow_paper_doll.py` | 0 | burnwillow_demo, burnwillow_discord_embed, test_paper_doll |
| `burnwillow_discord_embed.py` | 1 | burnwillow_demo |
| `codex_ui_manager.py` | 0 | standalone |

### Circular Dependencies

**None detected.** The import graph is a clean DAG.

### sys.path Manipulation

Only `test_map_renderer.py` (`sys.path.insert(0, ...)`). Test harness, acceptable.

---

## Phase 2: Graveyard Cleanup

### Deleted (confirmed orphans, zero active imports)

| File | Lines | Reason |
|------|-------|--------|
| `codex_journal_ui.py` | 15 | Basic logger. Only in `legacy_import/` |
| `state_manager.py` | 25 | 3-field Mimir state. Only in `legacy_import/` |
| `codex_dynamic_power.py` | 13 | Two stub functions. Only in `legacy_import/` |

### Archived to `archive/`

| File | Lines | Reason |
|------|-------|--------|
| `codex_tools.py` | 251 | Legacy FAISS Xenolore V15.3. Guarded try/except in agent_main (graceful fallback) |
| `codex_discord_ui.py` | 600+ | Complete DM Screen UI, but never wired into active bot |

### Moved to `scripts/`

| File | Reason |
|------|--------|
| `debug_token.py` | One-off Discord token validator |

---

## Phase 3: Hardcoded Path Fixes

### Priority 1 (CRITICAL -- would break on CWD change)

| File | Line | Before | After |
|------|------|--------|-------|
| `codex_agent_main.py` | 264 | `Path("state/session_state.json")` | `CODEX_DIR / "state" / "session_state.json"` |
| `codex_agent_main.py` | 382 | `SAVE_DIR = Path("saves")` | `SAVE_DIR = CODEX_DIR / "saves"` |
| `codex_agent_main.py` | 2308 | `Path("saves") / campaign_name` | `CODEX_DIR / "saves" / campaign_name` |
| `codex_discord_bot.py` | 112 | `Path("saves")` | `_ROOT / "saves"` |
| `codex_telegram_bot.py` | 223 | `Path("saves")` | `_ROOT / "saves"` |
| `codex_world_engine.py` | 324 | `WORLDS_DIR = Path("worlds")` | `WORLDS_DIR = _ROOT / "worlds"` |

### Priority 2 (HIGH -- production risk)

| File | Line | Before | After |
|------|------|--------|-------|
| `codex_mouth.py` | 54 | `"models/piper/..."` relative string | `str(_ROOT / "models" / "piper" / "...")` |
| `codex_source_scanner.py` | 27 | Default `"vault/dnd5e/SOURCE"` | Default `None`, resolve via `_ROOT` internally |
| `codex_char_wizard.py` | 222 | `os.path.join(os.getcwd(), "vault")` | `os.path.join(_ROOT, "vault")` |
| `codex_char_wizard.py` | 779 | `os.path.join(os.getcwd(), "saves")` | `os.path.join(_ROOT, "saves")` |

### Already Safe (use `Path(__file__)` pattern)

`codex_butler.py`, `codex_ears.py`, `codex_genesis_engine.py`, `ashburn_crew_module.py`, `vault_processor.py`

---

## Phase 4: Package Skeleton

### Created: `codex/` package

```
codex/
  __init__.py    # v3.0.0, package docstring
  paths.py       # Central path registry (11 constants)
```

### `codex/paths.py` Constants

| Constant | Resolves To |
|----------|-------------|
| `PROJECT_ROOT` | `Codex/` (parent of codex package) |
| `STATE_DIR` | `Codex/state/` |
| `SAVES_DIR` | `Codex/saves/` |
| `VAULT_DIR` | `Codex/vault/` |
| `CONFIG_DIR` | `Codex/config/` |
| `WORLDS_DIR` | `Codex/worlds/` |
| `MODELS_DIR` | `Codex/models/` |
| `TEMPLATES_DIR` | `Codex/templates/` |
| `LOGS_DIR` | `Codex/gemini_sandbox/session_logs/` |
| `SESSION_STATE_FILE` | `Codex/state/session_state.json` |
| `BRIDGE_FILE` | `Codex/state/live_session.json` |
| `DND5E_SOURCE_DIR` | `Codex/vault/dnd5e/SOURCE/` |
| `PIPER_MODEL_DIR` | `Codex/models/piper/` |

### Verification

```
$ python3 -c "from codex.paths import SAVES_DIR; print(SAVES_DIR.exists())"
True
$ python3 -c "import codex; print(codex.__version__)"
3.0.0
```

---

## Phase 5: Proposed Migration Structure (Future WO)

```
Codex/
  codex_agent_main.py          # STAYS AT ROOT
  play_burnwillow.py           # STAYS AT ROOT
  play_crown.py                # STAYS AT ROOT
  codex_gemini_bridge.py       # STAYS AT ROOT
  codex/
    __init__.py                # CREATED (WO-105)
    paths.py                   # CREATED (WO-105)
    core/                      # architect, butler, cortex, memory, dice, manifold_guard
    games/
      burnwillow/              # engine, content, zone1, persistence, ui, paper_doll, discord_embed, bridge
      crown/                   # engine, ashburn
    spatial/                   # map_engine, map_renderer
    forge/                     # char_wizard, omni_forge, source_scanner, adapter
    world/                     # genesis, world_wizard
    services/                  # ears, mouth
    bots/                      # discord_bot, telegram_bot
    integrations/              # mimir, tarot, vault_processor
  tests/                       # All test/sim files
  examples/                    # Demo/integration examples
  archive/                     # CREATED (WO-105) -- preserved orphans
  scripts/                     # CREATED (WO-105) -- one-off utilities
```

### Migration Order (for future WO)

1. Move Tier 0 modules first (no local imports = safest)
2. Update imports bottom-up (Tier 0 -> 1 -> 2 -> 3 -> hub)
3. Switch hardcoded `_ROOT` patterns to `codex.paths` imports
4. Move tests/examples/archive last (lowest risk)
5. Update systemd units (`codex_ears.service`, `codex_mouth.service`)
6. Verify all entry points still work from root

### Estimated Import Rewrites

| File | Import Lines to Change |
|------|----------------------|
| `codex_agent_main.py` | ~16 |
| `codex_discord_bot.py` | ~4 |
| `codex_telegram_bot.py` | ~3 |
| `play_burnwillow.py` | ~3 |
| `codex_burnwillow_bridge.py` | ~2 |
| `codex_ears.py` | ~1 |
| All other moved files | ~1-2 each |
| **Total** | ~45-55 import rewrites |

---

## Verification Checklist

- [x] `py_compile` passes on all 10 modified files
- [x] `codex.paths` resolves correctly
- [x] `codex.__version__` == 3.0.0
- [x] No circular dependencies
- [x] Graveyard files removed/archived
- [x] All `Path("saves")` references anchored to `__file__`
- [x] `codex_agent_main.py` uses `CODEX_DIR` (existing constant)
- [ ] Full smoke test pending (manual: `python3 codex_agent_main.py`)

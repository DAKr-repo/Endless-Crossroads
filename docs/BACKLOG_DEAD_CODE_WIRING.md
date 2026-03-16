# Backlog: Dead Code Wiring Opportunities

Items identified during the pre-commit audit (2026-03-15) that were removed
from imports but represent unfinished features worth revisiting.

---

## 1. MetabolicState — Structured Thermal Display

**What it is:** `codex.core.cortex.MetabolicState` is a dataclass with CPU temp,
RAM usage, thermal status, pain signals, and metabolic clearance (whether the
system can safely invoke large LLM models).

**Where it's already used:** `architect.py` (gates model selection), `dm_dashboard.py`
(thermal panel), `discord_bot.py` (status command), `rag_service.py` (thermal gate).

**What's missing:** `codex_agent_main.py` calls `core.get_status_report()` which
returns a formatted string. It could instead use `cortex.read_metabolic_state()`
to get structured data and render a richer Rich panel with color-coded thermal
bars, RAM gauges, and model availability indicators.

**Effort:** Small — the data is already there, just needs a renderer.

**Wiring point:** The `system_status` action in `main_menu()` (~line 3375).

---

## 2. ModelResponse / ArchitectConfig — LLM Observability

**What they are:**
- `ModelResponse`: Structured LLM output with content, model name, token count,
  latency, and whether it was cached.
- `ArchitectConfig`: Settings object for the Architect (model preferences,
  temperature, max tokens, timeout).

**Where they're already used:** Inside `architect.py` — every `think()` call
returns a `ModelResponse`, and the Architect is initialized with an
`ArchitectConfig`.

**What's missing:** The main agent could:
- Show per-query token usage and latency in a debug/DM panel
- Let the user tune LLM settings via a runtime settings menu
- Track cumulative token spend per session

**Effort:** Medium — needs a settings UI and a stats aggregator.

**Wiring point:** A new "LLM Stats" panel in the DM Dashboard, or a
`/settings` command in the main menu.

---

## 3. run_discord_bot() — Simplified Bot Startup

**What it is:** `codex.bots.discord_bot.run_discord_bot(core)` is a clean
3-line async helper that creates the bot, reads the token from env, and starts.

**Why it wasn't used:** The main agent's Discord startup block (~line 3684)
needs to wire `_monitor._discord_bot` for the voice watchdog health check.
`run_discord_bot()` doesn't expose the bot instance for this.

**What's needed:** Either:
- Add a `bot_ref` output parameter to `run_discord_bot()`, or
- Have it return the bot instance, or
- Move the health monitor wiring into `CodexDiscordBot.__init__()`

**Effort:** Small — any of the three approaches is ~5 lines.

---

## 4. get_card_for_context() — Tarot in Main Menu

**What it is:** Maps game contexts (crown, crew, campfire, world, legacy)
to tarot card keys for thematic UI rendering.

**Where it's already used:** `play_crown.py`, `discord_bot.py`,
`telegram_bot.py`, `crown/ashburn.py` — all render tarot cards contextually.

**What's missing from codex_agent_main.py:** The main menu and game launcher
screens could show a tarot card matching the current game system or menu
section. E.g., entering the Crown module shows the Sun Ring card, entering
world creation shows the Wolf card.

**Effort:** Small — import it back and add `render_tarot_card(get_card_for_context("crown"), "...")` calls at menu transitions.

---

## 5. WorldEngine / WorldState — Direct Access

**What they are:** `WorldEngine` manages world generation and persistence.
`WorldState` is the full world data structure (regions, factions, NPCs, history).

**Current status:** The main agent uses `get_world_engine()` singleton which
returns a `WorldEngine` internally. The classes were imported for type hints.

**What could be added:** Type-annotated function signatures in the main agent,
or direct `WorldState` manipulation for save/load of world data outside the
singleton pattern.

**Effort:** Low priority — the singleton pattern works fine.

---

## 6. Docstrings — Public API Documentation

**What's missing:** Most public classes and functions lack docstrings. Someone
reading the code for the first time has to reverse-engineer intent from
implementation.

**Scope:** Focus on public API surfaces first:
- `codex/core/engine_protocol.py` — GameEngine, DiceEngine, PartyEngine protocols
- `codex/games/bridge.py` — UniversalGameBridge, step(), command handlers
- `codex/core/mechanics/` — journey, clock, conditions, initiative, rest
- `codex/spatial/` — map_engine, map_renderer, zone_manager
- `codex/forge/` — char_wizard, omni_forge, source_scanner

**Approach:** Module-level docstring + class docstring + one-liner on each
public method. Skip private methods and obvious getters/setters.

**Effort:** Medium — spread across many files but each change is small.

---

## Priority Order

1. **MetabolicState** — easy win, high visual impact
2. **run_discord_bot()** — small cleanup, reduces code complexity
3. **get_card_for_context()** — flavor enhancement, low effort
4. **ModelResponse/ArchitectConfig** — medium effort, useful for DM tools
5. **WorldEngine/WorldState** — low priority, current pattern works
6. **Docstrings** — public API documentation pass

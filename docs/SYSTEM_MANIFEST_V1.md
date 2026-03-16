# SYSTEM MANIFEST V1.0

> **Generated**: 2026-02-21
> **Scope**: Engine logic, serialization schemas, cross-platform handoffs, orphan audit
> **Authority**: Reverse-engineered from source code, verified against runtime behavior

---

## Section 1: Engine Logic — Turn Order & Mechanics

### 1.1 Crown & Crew (`codex/games/crown/engine.py`)

**Turn Sequence (per day)**:

```
1. get_morning_event()      → Road encounter with sway bias
2. declare_allegiance(side, tag) → Sway shift, DNA accumulation
3. get_prompt(side)          → Moral dilemma prompt (Crown or Crew pool)
4. get_world_prompt()        → Terrain/environment prompt
5. get_council_dilemma()     → Council vote + resolve_vote()
6. get_campfire_prompt()     → Reflection prompt (skipped on breach day)
   OR get_secret_witness()   → Breach day special event
7. end_day()                 → Advance day, reset daily state
8. Rest choice               → long_rest / short_rest / skip_rest
```

**Sway Mechanics**:
- Scale: -3 (Crown Agent) to +3 (Crew Loyal), clamped
- `declare_allegiance(side, tag)`: shifts sway +1 (crew) or -1 (crown)
- DNA tracking: `dna[tag] += 1` on each allegiance (tags: BLOOD, GUILE, HEARTH, SILENCE, DEFIANCE)
- Auto-tag assignment: crew → HEARTH/DEFIANCE/BLOOD, crown → GUILE/SILENCE/BLOOD

**Vote Power (Political Gravity)**:

| abs(sway) | Power | Tier Name |
|-----------|-------|-----------|
| 0 | 1x | Drifter |
| 1 | 2x | Leaning |
| 2 | 4x | Trusted |
| 3 | 8x | Loyal |

`resolve_vote({"crown": N, "crew": M})` applies player's weighted multiplier to their aligned side. Ties broken by current sway direction.

**Breach Day Formula**:
```python
breach_day = round(arc_length * breach_day_fraction)
# Default: breach_day_fraction = 0.6
# Arc 5 → Day 3, Arc 7 → Day 4, Arc 10 → Day 6
```

**Rest System**:
- Long rest: advances day via `end_day()`, full day cycle
- Short rest: does NOT advance day. Limited to `max_short_rests_per_day` (default 1). Applies morning event sway cap
- Skip rest: does NOT advance day. Decays sway ±1 toward 0 (`sway_decay_on_skip` = 1)

**Arc Termination**: `end_day()` when `day > arc_length` returns "The journey ends" message.

**Drifter Tax**: If `sway == 0 AND day < 3`, triggers Double Draw penalty.

**Core Constants**:
- `PATRONS`: 8 Crown-side NPCs (High Inquisitor, Governor, Spymaster, etc.)
- `LEADERS`: 8 Crew-side NPCs (Captain Vane, The Defector, The Mercenary, etc.)
- `TAGS`: 5 values (BLOOD, GUILE, HEARTH, SILENCE, DEFIANCE)
- `SWAY_TIERS`: -3 to +3, each with name/power/desc
- `MORNING_EVENTS`: 10 entries, each with text/bias/tag
- `COUNCIL_DILEMMAS`: 8 entries, each with prompt/crown/crew
- Prompt pools: 10 each for crown/crew/world/campfire

---

### 1.2 Ashburn Heir (`codex/games/crown/ashburn.py`)

Extends `CrownAndCrewEngine`. Adds Legacy Corruption system.

**LEADERS Dict** (4 heirs):

| Heir | Title | Ability | Risk |
|------|-------|---------|------|
| Lydia | The Velvet Chancellor | Diplomatic Immunity — nullify one Crown vote/round | Double-agent exposure → +2 corruption |
| Jax | The Signal Ghost | Dead Drop — secretly pass intel to Crew | Paranoid. 1-in-6 betrayal/round |
| Julian | The Gilded Son | Legacy Name — starts with +1 Sway toward Crown | Cannot refuse Crown challenges |
| Rowan | The Ash Walker | Ember Network — knows all Campfire event locations | Random corruption checks on Campfire |

**Heir-Specific Mechanics**:
- Julian: `sway -= 1` at init (Crown-leaning start)
- Legacy Checks: `generate_legacy_check()` rolls 1d6, triggers on 5-6 (33%)
- Legacy Choice: Obey (corruption +1, sway -1) or Lie (sway +1, 33% detection → corruption +2)
- Corruption threshold: `legacy_corruption >= 5` → immediate game over via `check_betrayal()`
- Vote power override: if `betrayal_triggered`, returns 1 (nullifies gravity)

**Ashburn Prompts**: 8 each for crown/crew/world/campfire (override parent pools).
**Legacy Prompts**: 8 narrative call entries with binary choices.

**`generate_legacy_report()`**: INHERITED unchanged from parent `CrownAndCrewEngine`. Heir choice affects sway and corruption during play but NOT the final report structure. **Known gap**: heir-specific outcomes are not reflected in the legacy report format.

---

### 1.3 Quest Archetypes (`codex/games/crown/quests.py`)

**QuestArchetype Dataclass Fields**:
```
name, slug, arc_length, terms{crown,crew,neutral,campfire,world},
morning_events[], council_dilemmas[], prompts_crown[], prompts_crew[],
prompts_world[], prompts_campfire[], secret_witness,
special_mechanics{}, rest_config{}, patrons[], leaders[], description
```

**7 Quest Archetypes**:

| Slug | Name | Arc | Special Mechanics |
|------|------|-----|-------------------|
| `siege` | Siege Defense | 7 | supply_track, wall_integrity, breach_day=4 |
| `summit` | Diplomatic Summit | 4 | influence_track, leverage_tokens, private_meetings |
| `trial` | Trial of the Accused | 5 | evidence_track, testimony_slots, jury_opinion |
| `caravan` | Caravan Expedition | 6 | supply_track, water_per_day=2, terrain_hazard=0.3 |
| `heist` | The Grand Heist | 3 | heat_track (0-10), crew_trust=3, noise_threshold=5 |
| `succession` | Succession Crisis | 5 | faction_influence, noble_houses_declared, coronation_countdown=5 |
| `outbreak` | Outbreak Response | 5 | infection_track (0-20), cure_progress, daily_spread=3 |

**`to_world_state()`** returns dict consumed by `CrownAndCrewEngine(world_state=ws)` in `__post_init__()`. Keys: terms, prompts_*, secret_witness, patrons, leaders, morning_events, council_dilemmas, arc_length, quest_name, quest_slug, special_mechanics, rest_config.

---

### 1.4 Burnwillow (`codex/games/burnwillow/engine.py`)

**Turn Sequence (exploration)**:
```
1. Room entry → _check_room_encounter() (ambush check)
2. If enemies present → combat mode (run_combat_round loop)
3. Player action (move/search/loot/use/push/rest/look)
4. Doom tick → advance_doom(turns)
5. Wave check → _process_wave_spawns()
6. Repeat until TPK or boss kill
```

**Doom Clock**:
- Thresholds: `{5, 10, 13, 15, 17, 20, 22}` with event strings
- Advances on: movement (+1), search (+1), rest (+1)
- Wave triggers at threshold values (see Wave System)

**Wave System (WO-V17.0)**:

| Wave | Doom Trigger | Behavior | Enemies |
|------|-------------|----------|---------|
| 1 | 10 | 2-3 stationary ambush in unvisited rooms | Blight-Hawk, Hollowed Scavenger |
| 2 | 15 | 1-2 BFS roamers from entrance, advance every 2 doom ticks | Blighted Sentinel, Spore-Crawler |
| 3 | 20 | Rot Hunter — BFS pursuit every 1 doom tick, forced combat | Rot Hunter (boss-tier) |

**Pity Loot System**:
- `_turns_since_unique_loot`: int counter, increments on search
- `_found_item_names`: set, seeded with starter gear names in `equip_loadout()`
- `check_pity_loot()`: after 12+ dry turns, forces tier 2+ unique drop via `get_random_loot()`
- `register_loot_find(name)`: resets counter if name not in `_found_item_names`

**Character Model**:
```
name, might, wits, grit, aether (core stats)
max_hp = 10 + grit_mod
current_hp = max_hp (init)
base_defense = 10 + wits_mod
gear: GearGrid (10 slots)
inventory: Dict[int, GearItem] (stable-index backpack)
keys: int (consumable lock openers)
```

**Stat Modifier Formula**: `(score - 10) // 2`

**Dice System**:
- `roll_dice_pool(dice_count, modifier, dc)`: Nd6 + modifier vs DC
- Hard cap: max 5d6
- Crit: all 6s. Fumble: all 1s
- Pool contribution: base 1d6 + gear tier bonuses from matching stat slots

**GearGrid** (10 slots):
- Slots: HEAD, SHOULDERS, CHEST, ARMS, LEGS, R_HAND, L_HAND, R_RING, L_RING, NECK
- `SLOT_STAT_MAP`: R_HAND/L_HAND → MIGHT, HEAD/ARMS → WITS, CHEST/LEGS → GRIT
- Wildcard slots (SHOULDERS, NECK, R_RING, L_RING): require `primary_stat` override
- Two-handed weapons occupy R_HAND, displace L_HAND

**GearTier**: TIER_0 (0) through TIER_IV (4). Dice bonus = tier value.

**Damage Reduction**: `DR_BY_TIER = {1:0, 2:1, 3:2, 4:3}`, bosses = tier + 1.

**Archetypes**: beast, scavenger, aetherial, construct. Mapped via `CONTENT_ARCHETYPES`.

**Loadout Map** (6 class presets):
```
sellsword: Shortsword + Jerkin + Gloves[Lockpick]
occultist:  Wand + Bell[Summon] + Jerkin
sentinel:   Shortsword + Shield[Intercept] + Jerkin
archer:     Shortbow[Ranged] + Jerkin
vanguard:   Greatsword[Cleave] + Jerkin
scholar:    Grimoire + Robes + Gloves[Lockpick]
```

**Starter Gear Pool** (11 items, indices 0-10):
0. Rusted Shortsword (R.Hand, T1)
1. Padded Jerkin (Chest, T1, DR 1)
2. Old Oak Wand (R.Hand, T1, +1 Aether)
3. Burglar's Gloves (Arms, T1, +1 Wits, [Lockpick])
4. Pot Lid Shield (L.Hand, T1, DR 1, [Intercept])
5. Beckoning Bell (L.Hand, T1, +1 Aether, [Summon])
6. Lantern of the Lost (L.Hand, T2, +2 Aether, [Summon][Light])
7. Shortbow (R.Hand, T1, +1 Wits, [Ranged])
8. Greatsword (R.Hand, T1, +2 Might, [Cleave], two-handed)
9. Grimoire (R.Hand, T1, +1 Wits, [Spellslot])
10. Threadbare Robes (Chest, T1, +1 Aether)

**Combat Actions** (party system):
- attack: Might check vs enemy defense, damage on success
- guard: Passive, reduces incoming damage
- intercept: +DR bonus (T1:+2, T2:+3, T3:+4, T4:+5+reflect 1d6)
- command: Wits DC 12, grants bonus damage (solo: self, party: ally)
- bolster: Aether DC 10, grants +Nd6 on next roll (N = item tier, cap 3)
- triage: Wits DC 12, heals Nd6 HP (N = item tier), success = no charge consumed
- sanctify: Area effect, enemies take 1d6 at enemy phase
- summon: Creates Minion (HP: 3 + aether_mod, 3-round duration)
- retreat: Escape combat (may fail)

**In-Combat Movement**: 30ft budget, n/s/e/w as free action, no room transitions.

**Minion System**: `Minion(Character)` subclass. `create_minion(summoner_name, summoner_aether_mod)` → HP: 3 + aether_mod, might: 8 + aether_mod, 3-round duration. `tick_duration()` decrements, returns alive status.

**Enemy Targeting**: `select_target_weighted(party)` — weighted by inverse HP ratio (wounded prioritized). Weight = `max(0.1, 1.0 - hp_ratio + 0.3)`.

**Content Tables**:
- `ENEMY_TABLES[tier]`: T1 (5), T2 (6), T3 (6), T4 (5) enemies
- `LOOT_TABLES[tier]`: T1 (15), T2 (19), T3 (18), T4 (18) items
- `HAZARD_TABLES[tier]`: T1-T4, 5 each
- `BOSS_TEMPLATES`: 5 unique bosses (Hollowed Bear through Void Herald)
- `ROOM_DESCRIPTIONS[tier]`: 8 per tier + special types
- `WAVE_ENEMIES[1]`: Blight-Hawk, Hollowed Scavenger
- `WAVE_ENEMIES[2]`: Blighted Sentinel, Spore-Crawler
- `ARCHETYPE_LOOT`: 4x4 pool (per archetype per tier)

**Difficulty Classes**: ROUTINE (8), HARD (12), HEROIC (16), LEGENDARY (20).

**Trait Resolution** (`BurnwillowTraitResolver._TRAIT_MAP`):
```
SET_TRAP, CHARGE, SANCTIFY, RESIST_BLIGHT, FAR_SIGHT,
INTERCEPT, COMMAND, BOLSTER, TRIAGE
```

---

## Section 2: State Serialization Schema

### 2.1 CrownAndCrewEngine.to_dict()

**28 keys**:

| Category | Keys |
|----------|------|
| Core state | `day`, `sway`, `patron`, `leader`, `history`, `dna`, `vote_log` |
| Arc/rest | `arc_length`, `rest_type`, `rest_config` |
| World | `terms`, `entities`, `threat`, `region`, `goal` |
| Tracking sets | `_used_crown`, `_used_crew`, `_used_world`, `_used_campfire`, `_used_morning`, `_used_dilemmas` |
| Quest | `quest_slug`, `quest_name`, `special_mechanics`, `_council_dilemmas`, `_morning_events`, `_short_rests_today` |

**from_dict() pattern**: `cls()` construction with init keys, then `setattr()` loop for tracked-set fields. `.get()` fallbacks for backward compat.

### 2.2 AshburnHeirEngine.to_dict()

**Extends parent with 6 keys**:
```
legacy_corruption, heir_name, heir_leader, leader_ability,
betrayal_triggered, engine_type="ashburn"
```

**from_dict()**: Validates `engine_type`, handles corrupted saves with warning + reset.

### 2.3 BurnwillowEngine.save_game()

**Top-level keys**:

| Category | Keys |
|----------|------|
| Character | `character` (Character.to_dict() or None) |
| Party | `party` (list of Character.to_dict(), excludes Minions) |
| Doom | `doom_clock` (DoomClock.to_dict()) |
| Dungeon | `dungeon.graph`, `dungeon.current_room_id`, `dungeon.player_pos`, `dungeon.visited_rooms`, `dungeon.zone` |
| Civic | `civic_pulse` (CivicPulse.to_dict() or None) |
| Pity loot | `pity_counter`, `found_items` |

**Character.to_dict() schema**:
```
name, might, wits, grit, aether, max_hp, current_hp,
base_defense, gear (GearGrid.to_dict()), inventory,
_next_inv_id, keys
```

**GearGrid.to_dict()**: Dict of slot_name → GearItem.to_dict() or None.

**GearItem.to_dict()**:
```
name, slot (str), tier (int), stat_bonuses, damage_reduction,
special_traits, description, two_handed, weight, primary_stat
```

### 2.4 play_burnwillow.py GameState Save Augmentation

`action_save()` augments engine save with GameState fields:
```
turn_number, cleared_rooms[], searched_rooms[], scouted_rooms[],
dungeon_seed, room_enemies{str→list}, room_loot{str→list},
room_furniture{str→list}, doom_clock_state{current_turn, doom_level},
rot_hunter, first_strike_used, dungeon_path, narrative
```

NPC memory saved separately to `state/npc_memory.json` via `NPCMemoryManager.save()`.

**load_game() restores**: Engine state → GameState fields → spatial rooms → NPC memory → volatile state cleared.

---

## Section 3: Cross-Platform Handoff Map

### 3.1 Crown & Crew

| Step | Terminal (`play_crown.py`) | Discord (`discord_bot.py`) | Telegram (`telegram_bot.py`) |
|------|---------------------------|---------------------------|------------------------------|
| Session init | `CrownAndCrewEngine()` direct | `DiscordSession.start_game()` → engine init | `TelegramSession.start_game()` → engine init |
| Morning event | `engine.get_morning_event()` → Rich panel | `start_game()` injects in world prompt | `start_game()` injects in world prompt |
| Allegiance | `input()` → `declare_allegiance()` | `handle_allegiance()` via reactions/buttons | `handle_allegiance()` via text input |
| Prompt | `get_prompt(side)` → `display_card()` tarot | `handle_allegiance()` sends embed | `handle_allegiance()` sends text |
| World prompt | `get_world_prompt()` → `display_card()` tarot | `handle_vote()` sends embed | `handle_vote()` sends text |
| Council vote | `get_council_dilemma()` → `resolve_vote()` | `handle_vote()` via buttons | `handle_vote()` via text |
| Campfire | `get_campfire_prompt()` → `display_card()` tarot | `handle_travel()` campfire path | `handle_travel()` campfire path |
| Rest | `rest_choice()` → long/short/skip | `handle_rest()` via buttons | `handle_message()` via text |
| Legacy | `generate_legacy_report()` → console panel | `handle_vote()` finale path | `handle_vote()` finale path |
| Tarot | `render_tarot_card()` (Rich Panel, 5 contexts) | `format_tarot_text()` in code block | `format_tarot_text()` in code block |
| Save/Load | None (single-session) | None | None |

**Tarot Contexts**: "crown", "crew", "campfire", "world", "legacy" → mapped to cards via `get_card_for_context()`.

**Phase Enums** (Discord/Telegram):
```
IDLE, CHOOSE_GAME, CROWN_SETUP, CROWN_ALLEGIANCE, CROWN_VOTE,
CROWN_REST, CROWN_CAMPFIRE, ASHBURN_PROLOGUE, ASHBURN_LEGACY,
BURNWILLOW, DUNGEON, OMNI, MIMIR, SETUP
```

### 3.2 Burnwillow

| Step | Terminal (`play_burnwillow.py`) | Discord (`discord_bot.py`) |
|------|-------------------------------|---------------------------|
| Session init | `BurnwillowEngine()` + `GameState` + emberhome | `BurnwillowBridge(player_name)` |
| Commands | `input()` → `CommandRegistry.resolve()` → dispatch | `GameCommandView` buttons + `on_message` → `bridge.step()` |
| Movement | `engine.move_player_grid()` + `_end_exploration_turn()` | `bridge.step("move n")` → text response |
| Combat | `run_combat_round()` structured loop | `bridge.step("attack")` → text response |
| Search | `action_search()` → doom tick → pity check | `bridge.step("search")` → text response |
| Wave spawns | `_process_wave_spawns()` in game loop | Via bridge (no separate wave handler) |
| Save/Load | `action_save/load()` → `saves/burnwillow_save.json` | Not implemented |
| NPC Memory | `_init_npc_memory()` → `NPCMemoryManager` | Via narrative engine |
| Emberhome | `_run_emberhome_hub()` → settlement loop | Not implemented |
| Telegram | N/A | N/A (not implemented) |

**Bridge Pattern**: `BurnwillowBridge` wraps `BurnwillowEngine`. `step(command: str) -> str` is the single entry point. Parses command → dispatches to `_cmd_*` handlers → returns formatted text. `COMMAND_CATEGORIES` (class attribute) defines 3 groups:
- **navigation**: move, n/s/e/w, look, map
- **combat**: attack, intercept, command, bolster, triage, rest
- **exploration**: search, loot, drop, use, push, inventory, stats, save, help, tutorial

**`UniversalGameBridge`** (`codex/games/bridge.py`): Generic adapter for any `GameEngine` protocol. Same `step()` pattern. Used as fallback for FITD/D&D5e systems, not for Burnwillow or Crown.

---

## Section 4: Ghost Audit — Stubs, Orphans & Wiring Status

### Fully Wired (confirmed with grep)

| Module | Evidence |
|--------|----------|
| `narrative_loom.py` | Called in `CrownAndCrewEngine._consult_mimir()` |
| `town_crier.CivicPulse` | Instantiated by `BurnwillowEngine.__init__()` |
| `universe_manager.py` | Used in `codex_agent_main.py` and `world_wizard.py` |
| `broadcast.GlobalBroadcastManager` | Accepted by `BurnwillowBridge.__init__(broadcast_manager=)`, emits MAP_UPDATE via `_emit_frame()`. Consumed by `npc_memory.py`, `trait_handler.py`, `discord_bot.py`, `telegram_bot.py` |
| `tarot.py` | Terminal: `render_tarot_card()` in `play_crown.py` `display_card()`. Discord: imported with `format_tarot_text()`. Telegram: imported with `format_tarot_text()` |
| `trait_handler.py` | Registered by `BurnwillowBridge.__init__()`: `register_resolver("burnwillow", BurnwillowTraitResolver())`. `activate_trait()` called in `_cmd_use()` |
| `npc_memory.py` | Wired in `play_burnwillow.py` `_init_npc_memory()`. Load/save hooks active. Attached to `NarrativeEngine` |
| `fitd_engine.py` | Shared FITD core used by SaV, BoB, BitD, Candela, CBRPNK engines |
| `graveyard.py` | Called by `BurnwillowEngine.log_character_death()` |

### Partially Wired (functional but limited reach)

| Module | Status | Detail |
|--------|--------|--------|
| `capacity_manager.py` | Importable, not called | `check_capacity()` defined but never invoked from game loops. Burnwillow uses inline encumbrance checks on Character |
| `optimize_context.py` | Standalone, not imported | Token-budgeting utility written for Mimir. Never imported by any module. Mimir uses inline context management |
| `cartography.py` | list_maps() wired | `list_maps()` used by Librarian `carto` command. `generate_map_from_context()` available but not called in game loops |
| `bridge.py` (Universal) | Imported, rarely instantiated | Discord/Telegram import it. Burnwillow uses `BurnwillowBridge` (dedicated). Universal used for FITD systems |

### Config Files

| Path | Runtime Status |
|------|---------------|
| `config/entity_schema.json` | Loaded by `trait_handler.load_entity_schema()` at runtime (confirmed) |
| `config/codex_voice.json` | Loaded by Discord voice system |
| `config/systems/*.json` (12 files) | Rules definitions. Loaded by maintenance/admin scripts, not runtime game loops |

### No "Coming Soon" Stubs Remain

All previously identified stubs have been resolved across WO-V9.5 through WO-V17.0 deployments.

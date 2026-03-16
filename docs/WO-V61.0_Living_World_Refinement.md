# WORK ORDER: WO-V61.0 — The Living World Refinement

**Priority:** HIGH
**Assignee:** @Mechanic, @Designer
**Dependencies:** WO-V31.0 (Autopilot), WO-V34.0 (GenericAutopilot), WO-V37.0 (Chronicle Recap), WO-V50.0 (Audio Narration), WO-V54.0 (Playability Sprint)
**Origin:** NotebookLM critique analysis — 4 architectural suggestions verified against codebase

---

## Overview

External critique identified four gaps between C.O.D.E.X.'s mechanical depth and its narrative output. Code verification confirms all four are genuine. This WO addresses them in priority order:

1. **Track A — Emotional Anchor Shards** (quick win, surgical)
2. **Track B — Narrative Mood Injection** (connects existing infrastructure)
3. **Track C — Momentum Ledger for TownCryer** (new subsystem, highest impact)
4. **Track D — Cross-System Companions + Trait Evolution** (completes existing system)

Each track is independently deployable. No track depends on another.

---

## Track A: Emotional Anchor Shards

### Problem

Session recaps are stat sheets. `format_session_stats()` counts kills, loot, and rooms. `summarize_session()` feeds these counts to Mimir with a generic prompt. Mimir has no access to emotional context, so recaps read like audit trails.

The session log tracks only 8 event types, all mechanical:
- `room_entered`, `kill`, `room_cleared`, `aoe_used`, `loot`, `companion_summoned`, `party_death`, `quest_complete`

No events capture near-death, rare resource expenditure, faction shifts, critical rolls, or companion sacrifice.

### What Exists

- `MemoryShard` with `ShardType.ANCHOR` (semi-permanent, high priority) — exists but underused
- `NarrativeLoomMixin._add_shard()` — ready to emit anchors from any engine
- `synthesize_narrative()` already prioritizes ANCHOR shards over CHRONICLE/ECHO
- `GlobalBroadcastManager` with `HIGH_IMPACT_DECISION` event type — wired to NPC memory

### Implementation

#### A1: New session log event types

Add these event types to the session log at their respective trigger points:

| Event Type | Trigger | Fields | File |
|---|---|---|---|
| `near_death` | Character drops below 20% HP during combat | `turn`, `name`, `hp`, `max_hp`, `attacker` | `play_burnwillow.py` damage resolution |
| `ally_saved` | Triage/heal brings character from <20% to >20% | `turn`, `savior`, `saved`, `method` | `play_burnwillow.py` triage/bolster |
| `rare_item_used` | Item with tier >= 3 or `[Summon]`/`[Phoenix]` trait consumed | `turn`, `item_name`, `tier`, `user`, `trait` | `play_burnwillow.py` item use |
| `critical_roll` | Natural max on all dice (e.g., all 6s on damage) or natural 1 on all dice | `turn`, `roller`, `roll_type`, `result`, `context` | `engine.py` roll_check/roll_dice_pool |
| `companion_fell` | AI companion drops to 0 HP | `turn`, `name`, `archetype`, `cause` | `play_burnwillow.py` combat resolution |
| `faction_shift` | NPC disposition crosses a tier boundary (e.g., neutral→friendly) | `turn`, `npc_name`, `old_tier`, `new_tier` | `narrative_engine.py` turn_in_quest |
| `doom_threshold` | DoomClock crosses a named threshold (13, 17, 20, 22) | `turn`, `doom_value`, `event_text` | `engine.py` doom clock advance |
| `zone_breakthrough` | Party enters a new zone/tier for the first time | `turn`, `zone_id`, `tier` | `play_burnwillow.py` descent |

#### A2: Emit ANCHOR shards at friction points

At each trigger site above, also call:
```python
if hasattr(engine, '_add_shard'):
    engine._add_shard(
        f"{savior} sacrificed {item_name} to pull {saved} back from death",
        "ANCHOR",
        source="session"
    )
```

The content string should be narrative, not mechanical — "Bryn charged the Blight Crawler at 3 HP and fell" not "companion_fell: Bryn, hp=0".

#### A3: Enrich summarize_session() with anchor context

Modify `narrative_loom.py:summarize_session()`:

1. After building `stats_block`, scan `session_log` for anchor event types (`near_death`, `ally_saved`, `rare_item_used`, `critical_roll`, `companion_fell`, `faction_shift`, `doom_threshold`, `zone_breakthrough`)
2. Build an `anchors_block` string: one sentence per anchor event, ordered chronologically
3. Append `anchors_block` to the Mimir prompt after the stats block:
   ```python
   prompt = (
       "Write a brief (2-3 sentence) dramatic narrative recap of this "
       "dungeon session. Focus on the most dramatic moments.\n\n"
       + stats_block
       + "\n\n--- Key Moments ---\n"
       + anchors_block
   )
   ```
4. Also include anchors in the text-only fallback (when Mimir is unavailable), under a "Key Moments" heading

#### A4: Broadcast anchors to NPC memory

When an ANCHOR shard is created via `_add_shard()`, it should also broadcast via `GlobalBroadcastManager` as `HIGH_IMPACT_DECISION` so NPCs hear about it:
- This is already wired in `memory.py` lines 188-196 for `CodexMemoryEngine`
- Ensure `NarrativeLoomMixin._add_shard()` also broadcasts when a `broadcast_manager` is available on the engine

#### A5: Universal bridge anchor emissions

For engines routed through `play_universal.py` (DnD5e, STC, FITD systems), add equivalent anchor emissions in the universal bridge:
- `bridge.py:_handle_combat()` — emit `near_death` when character HP drops below 20%
- `bridge.py:_handle_move()` — emit `zone_breakthrough` on first entry to new zone
- FITD loop — emit `doom_threshold` equivalent when stress maxes out / trauma taken

### Files Modified

| File | Changes |
|---|---|
| `play_burnwillow.py` | 8 new `log_event()` calls at trigger sites |
| `codex/games/burnwillow/engine.py` | `_add_shard()` calls at doom threshold, critical roll |
| `codex/core/services/narrative_loom.py` | `format_session_stats()` gains anchor extraction; `summarize_session()` prompt enriched |
| `codex/core/services/narrative_loom.py` | `NarrativeLoomMixin._add_shard()` gains optional broadcast |
| `play_universal.py` | Anchor emissions in dungeon/FITD loops |
| `codex/games/bridge.py` | Anchor emissions in combat/move handlers |

### Tests

- `test_anchor_shards.py`: Verify each of the 8 event types is logged at correct trigger
- Verify `summarize_session()` includes anchor block when anchor events present
- Verify `summarize_session()` output unchanged when no anchor events (backward compat)
- Verify ANCHOR shards broadcast to NPC memory
- Verify Mimir prompt contains "Key Moments" section

---

## Track B: Narrative Mood Injection

### Problem

Room descriptions and NPC dialogue don't reflect character mechanical state. A character at 2 HP gets the same tavern description as one at full health. Candela trauma doesn't make rooms feel paranoid. FITD stress at 8/9 doesn't inject urgency. Doom clock at 20 doesn't darken prose.

### What Exists

The infrastructure is 80% built — it just isn't connected:

- **`atmosphere.py`** — Proven pattern: `ThermalTone` maps tier depth to sensory leads + lexicon substitutions. Applied at dungeon generation time.
- **`narrative_frame.py`** — `DeltaTracker` + tier-specific sensory palettes injected into Mimir prompts. Operates at perception time.
- **Crown engine** — `_consult_mimir()` injects sway value into prompt ("sway is +3"). Mechanical state directly modulates narrative.
- **`world_wizard.py`** — `TONE_PRESETS` (gritty/heroic/comedic/gothic) as string modifiers.
- **`query_mimir()`** — Accepts `prompt` and `context` strings. No structured mood parameter, but context is freeform.

### Implementation

#### B1: Engine protocol — `get_mood_context()`

Add optional method to engine protocol pattern (not a formal Protocol — just implement on engines that support it):

```python
def get_mood_context(self) -> dict:
    """Return current mechanical state as narrative mood modifiers.

    Returns dict with optional keys:
        tension: float 0.0-1.0 (overall danger/urgency)
        tone_words: List[str] (adjectives to inject)
        party_condition: str ("healthy", "battered", "desperate", "critical")
        system_specific: dict (engine-unique mood data)
    """
```

#### B2: Per-engine implementations

**Burnwillow:**
```python
def get_mood_context(self) -> dict:
    party_hp_pct = sum(c.current_hp for c in self.party) / max(1, sum(c.max_hp for c in self.party))
    doom_pct = self.doom_clock.current / 20
    tension = max(doom_pct, 1.0 - party_hp_pct)

    if party_hp_pct < 0.25:
        condition = "critical"
        words = ["desperate", "ragged", "blood-slicked"]
    elif party_hp_pct < 0.5:
        condition = "battered"
        words = ["weary", "strained", "bruised"]
    elif doom_pct > 0.75:
        condition = "desperate"
        words = ["oppressive", "suffocating", "relentless"]
    else:
        condition = "healthy"
        words = []

    return {
        "tension": round(tension, 2),
        "tone_words": words,
        "party_condition": condition,
        "system_specific": {
            "doom": self.doom_clock.current,
            "doom_pct": round(doom_pct, 2),
            "tier": getattr(self, '_current_tier', 1),
        },
    }
```

**DnD5e:**
```python
def get_mood_context(self) -> dict:
    char = self.character
    hp_pct = char.current_hp / max(1, char.max_hp) if char else 1.0
    # Factor in death saves, spell slots remaining, etc.
    tension = 1.0 - hp_pct
    if hp_pct < 0.25:
        condition, words = "critical", ["bleeding", "frantic", "dim"]
    elif hp_pct < 0.5:
        condition, words = "battered", ["worn", "cautious", "tense"]
    else:
        condition, words = "healthy", []
    return {"tension": round(tension, 2), "tone_words": words, "party_condition": condition, "system_specific": {}}
```

**STC (Cosmere):**
```python
def get_mood_context(self) -> dict:
    char = self.character
    hp_pct = char.current_hp / max(1, char.max_hp) if char else 1.0
    # Stormlight as resource depletion indicator
    stormlight = getattr(char, 'stormlight', 0)
    max_stormlight = getattr(char, 'max_stormlight', 1) or 1
    sl_pct = stormlight / max_stormlight
    tension = max(1.0 - hp_pct, 1.0 - sl_pct)
    words = []
    if sl_pct < 0.2:
        words.extend(["dimming", "fading", "drained"])  # Stormlight running low
    if hp_pct < 0.25:
        condition = "critical"
    elif hp_pct < 0.5:
        condition = "battered"
    else:
        condition = "healthy"
    return {
        "tension": round(tension, 2), "tone_words": words,
        "party_condition": condition,
        "system_specific": {"stormlight_pct": round(sl_pct, 2)},
    }
```

**FITD engines (BitD/SaV/BoB/CBR+PNK/Candela):**
```python
def get_mood_context(self) -> dict:
    char = self.character
    stress = getattr(char, 'stress', 0)
    max_stress = getattr(char, 'max_stress', 9) or 9
    trauma_count = len(getattr(char, 'traumas', []))
    stress_pct = stress / max_stress
    tension = min(1.0, stress_pct + (trauma_count * 0.15))

    words = []
    if trauma_count >= 2:
        words.extend(["haunted", "fractured", "unreliable"])
    if stress_pct > 0.7:
        words.extend(["fraying", "manic", "reckless"])

    if stress_pct > 0.8 or trauma_count >= 3:
        condition = "critical"
    elif stress_pct > 0.5 or trauma_count >= 1:
        condition = "battered"
    else:
        condition = "healthy"

    return {
        "tension": round(tension, 2), "tone_words": words,
        "party_condition": condition,
        "system_specific": {"stress": stress, "trauma_count": trauma_count},
    }
```

**Crown & Crew:**
```python
def get_mood_context(self) -> dict:
    sway = getattr(self, 'sway', 0)
    day = getattr(self, 'day', 1)
    if abs(sway) >= 3:
        condition = "committed"
        words = ["fervent", "decisive", "zealous"]
    elif sway == 0 and day > 3:
        condition = "adrift"
        words = ["uncertain", "wary", "uncommitted"]
    else:
        condition = "healthy"
        words = []
    tension = min(1.0, day / 7)  # Tension rises as endgame approaches
    return {
        "tension": round(tension, 2), "tone_words": words,
        "party_condition": condition,
        "system_specific": {"sway": sway, "day": day},
    }
```

#### B3: Inject mood into Mimir prompts

**`narrative_frame.py`** — Modify `_build_affordance_context()` to call `engine.get_mood_context()` when available and append mood context:

```python
mood = engine.get_mood_context() if hasattr(engine, 'get_mood_context') else {}
if mood.get("tone_words"):
    context += f"\nMood: {', '.join(mood['tone_words'])}. Party condition: {mood['party_condition']}."
if mood.get("tension", 0) > 0.7:
    context += " Descriptions should feel urgent and dangerous."
```

**`bridge.py`** — Modify `_handle_npc_dialogue()` to inject mood into NPC conversation prompt:
```python
mood = engine.get_mood_context() if hasattr(engine, 'get_mood_context') else {}
if mood.get("party_condition") in ("critical", "battered"):
    npc_context += f" The visitor looks {mood['party_condition']}."
```

**`butler.py`** — Modify `narrate()` to accept optional mood context for tone-aware narration.

#### B4: Perception-time atmosphere (Burnwillow enhancement)

Currently `thermal_narrative_modifier()` runs at dungeon generation time. Add a lighter-weight perception-time overlay:

In `play_burnwillow.py`, when displaying room descriptions on entry, if doom > 15 or party HP < 30%, apply a `mood_overlay()` function that:
1. Prepends a short mood sentence (from a pool keyed by `party_condition`)
2. Does NOT rewrite the base description — just layers a sentence on top

Example mood overlays:
- `critical`: "Every shadow feels like a threat. Your hands won't stop shaking."
- `battered`: "You're running on borrowed time. The wounds are adding up."
- `desperate` (high doom): "The Burnwillow groans around you. The rot is close."

### Files Modified

| File | Changes |
|---|---|
| `codex/games/burnwillow/engine.py` | `get_mood_context()` method |
| `codex/games/dnd5e/__init__.py` | `get_mood_context()` method |
| `codex/games/stc/__init__.py` | `get_mood_context()` method |
| `codex/games/bitd/__init__.py` | `get_mood_context()` method (shared FITD pattern) |
| `codex/games/sav/__init__.py` | `get_mood_context()` method |
| `codex/games/bob/__init__.py` | `get_mood_context()` method |
| `codex/games/cbrpnk/__init__.py` | `get_mood_context()` method |
| `codex/games/candela/__init__.py` | `get_mood_context()` method |
| `codex/games/crown/engine.py` | `get_mood_context()` method |
| `codex/core/services/narrative_frame.py` | Mood injection in `_build_affordance_context()` |
| `codex/games/bridge.py` | Mood injection in `_handle_npc_dialogue()` |
| `codex/core/butler.py` | Optional mood context in `narrate()` |
| `play_burnwillow.py` | Perception-time `mood_overlay()` on room entry |

### Tests

- `test_mood_injection.py`: Verify each engine returns valid `get_mood_context()` dict
- Verify tension values scale correctly (low HP = high tension, full HP = low tension)
- Verify mood context appears in Mimir prompt when tension > threshold
- Verify room descriptions unchanged when mood is neutral (backward compat)
- Verify FITD stress/trauma maps to correct tone words

---

## Track C: Momentum Ledger for TownCryer

### Problem

TownCryer broadcasts discrete, isolated events. No trend detection, no pattern aggregation, no compounding consequences. GRAPES world profile is static after generation — player actions never modify world state. The system tells players "what happened" but never "what it means for the world."

Current architecture:
- `CivicPulse`: threshold-based tick counter, events are independent
- `GlobalBroadcastManager`: fire-and-forget event bus, stateless
- `WorldHistory`: append-only log, no analysis methods
- `CrierVoice`: template + Mimir narration, no trend awareness
- GRAPES profile: read-only after `roll_unified_world()`

### What Exists to Build On

- `WorldHistory.record_event()` already logs events with timestamps and universe isolation
- `CivicCategory` enum (TRADE, SECURITY, RUMOR, INFRASTRUCTURE, MORALE) maps cleanly to GRAPES categories
- `CrierVoice` already has GRAPES-aware rumor generation (`_grapes_rumor()`)
- Broadcast system has 14 event types for trigger detection
- `NarrativeLoomMixin._add_shard()` can persist momentum milestones as ANCHOR shards

### Implementation

#### C1: New file — `codex/core/services/momentum.py`

```python
"""
Momentum Ledger — Cumulative trend tracking for TownCryer.

Bins player actions by GRAPES category + location. When a category
accumulates enough weight in a location, fires a compound event
that synthesizes the trend into a narrative broadcast.
"""

@dataclass
class MomentumEntry:
    """A single binned action."""
    category: str          # GRAPES key: "geography", "religion", etc.
    location: str          # Ward/zone/region identifier
    weight: float          # Impact weight (default 1.0, scaled by action type)
    action_tag: str        # What happened: "aided_poor", "killed_boss", "stole_goods"
    turn: int              # Game turn for ordering
    timestamp: str         # ISO timestamp

@dataclass
class MomentumBin:
    """Accumulated momentum in one category+location pair."""
    category: str
    location: str
    total_weight: float = 0.0
    entry_count: int = 0
    entries: List[MomentumEntry] = field(default_factory=list)
    last_threshold_fired: float = 0.0  # Prevents re-firing same threshold

class MomentumLedger:
    """Tracks cumulative player action trends by GRAPES category + location.

    Thresholds:
        3.0  — Minor shift (single TownCryer rumor)
        7.0  — Notable trend (TownCryer broadcast + GRAPES modifier)
        12.0 — Major shift (TownCryer broadcast + GRAPES mutation + ANCHOR shard)
        20.0 — Tipping point (cascade event — secondary bin gets +3.0 free weight)
    """

    THRESHOLDS = [3.0, 7.0, 12.0, 20.0]

    def __init__(self, universe_id: str = ""):
        self.universe_id = universe_id
        self._bins: Dict[Tuple[str, str], MomentumBin] = {}

    def record(self, category: str, location: str, action_tag: str,
               weight: float = 1.0, turn: int = 0) -> List[dict]:
        """Record an action. Returns list of newly crossed thresholds."""
        ...

    def get_bin(self, category: str, location: str) -> Optional[MomentumBin]:
        """Get accumulated momentum for a category+location pair."""
        ...

    def get_dominant_trend(self, location: str) -> Optional[Tuple[str, float]]:
        """Return the highest-weight category for a given location."""
        ...

    def get_all_trends(self, min_weight: float = 3.0) -> List[MomentumBin]:
        """Return all bins above a minimum weight threshold."""
        ...

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "MomentumLedger": ...
```

#### C2: Action-to-GRAPES category mapping

```python
# Maps session log event types + context to GRAPES categories
ACTION_CATEGORY_MAP = {
    # Direct mappings
    "kill":           ("security", 1.0),     # Clearing threats
    "room_cleared":   ("security", 0.5),     # Area secured
    "quest_complete": ("politics", 2.0),     # Political/social impact
    "loot":           ("economics", 0.5),    # Resource extraction
    "faction_shift":  ("politics", 2.0),     # Political shift
    "doom_threshold": ("religion", 1.5),     # Cosmic/doom significance
    "zone_breakthrough": ("geography", 2.0), # Territory explored

    # Context-dependent (secondary categorization in record() logic)
    # "aided_npc" → "social" if NPC is commoner, "politics" if NPC is noble
    # "stole_goods" → "economics" negative weight
    # "restored_temple" → "religion" 3.0
}
```

#### C3: Wire momentum recording into game loops

**`play_burnwillow.py`** — After each `log_event()` call, also call `momentum_ledger.record()`:
```python
state.session_log.append({"type": "kill", ...})
if state.momentum_ledger:
    state.momentum_ledger.record(
        category="security",
        location=state.current_location or "burnwillow_depths",
        action_tag="kill",
        weight=1.0 + (tier - 1) * 0.5,  # Higher tier = more impact
        turn=state.turn_count,
    )
```

**`play_universal.py`** — Same pattern for DnD5e/STC/FITD game loops.

#### C4: Momentum threshold handlers

When `MomentumLedger.record()` returns crossed thresholds:

| Threshold | Effect |
|---|---|
| **3.0 (Minor shift)** | Generate a trend-aware TownCryer rumor via `CrierVoice`. Rumor references the pattern, not the individual action. E.g., "The lower wards feel safer of late. Fewer screams at night." |
| **7.0 (Notable trend)** | Generate a stronger broadcast + apply a temporary GRAPES modifier. E.g., `grapes_profile["economics"]["abundance"] = "rising"`. Modifier persists until counter-momentum or decay. |
| **12.0 (Major shift)** | Generate a dramatic broadcast + mutate GRAPES profile permanently + emit ANCHOR shard. E.g., "The Dock Ward economy has transformed. New merchants arrive daily." |
| **20.0 (Tipping point)** | All of the above + cascade: inject +3.0 weight into a related bin. E.g., security momentum cascades into economics (safe streets → merchant traffic). |

#### C5: GRAPES mutation

Add `mutate()` method to GRAPES profile:
```python
def mutate(self, category: str, key: str, new_value: str, reason: str) -> None:
    """Modify a GRAPES field based on player momentum.

    Records the mutation with reason for chronicle purposes.
    """
```

Mutations are persisted in save data and reflected in subsequent world generation, rumor templates, and NPC dialogue context.

#### C6: Trend-aware CrierVoice

Extend `CrierVoice` to accept `MomentumLedger` and generate trend-aware broadcasts:

```python
def narrate_trend(self, bin: MomentumBin) -> str:
    """Generate a narrative rumor about an accumulated trend."""
    if self._mimir:
        prompt = (
            f"Write a 1-2 sentence in-world rumor about a {bin.category} "
            f"trend in {bin.location}. The players have performed "
            f"{bin.entry_count} related actions (examples: "
            f"{', '.join(e.action_tag for e in bin.entries[-3:])}). "
            f"Total momentum: {bin.total_weight:.1f}. "
            f"Describe the societal shift, not individual actions."
        )
        if self._grapes:
            prompt += f" World context: {_build_grapes_snippet(self._grapes)}"
        result = self._mimir(prompt, "")
        if result and len(result) > 10:
            return result.strip()
    # Fallback: generic trend templates
    return self._fallback_trend(bin)
```

#### C7: Momentum decay

Implement slow decay to prevent runaway accumulation:
- Bins decay by 0.5 weight per dungeon run (Burnwillow) or per session (FITD)
- Decay only applies to bins that haven't received new entries in 3+ runs
- Bins below 1.0 weight are pruned
- Decay runs in `CivicPulse.advance()` as a post-tick hook

#### C8: Persistence

Save `MomentumLedger` alongside `CivicPulse` in meta_state:
```json
{
  "civic_pulse": { ... },
  "momentum_ledger": {
    "universe_id": "...",
    "bins": {
      "security|burnwillow_depths": {
        "total_weight": 8.5,
        "entry_count": 6,
        "last_threshold_fired": 7.0,
        "entries": [...]
      }
    }
  }
}
```

### New File

| File | Purpose |
|---|---|
| `codex/core/services/momentum.py` | MomentumEntry, MomentumBin, MomentumLedger, ACTION_CATEGORY_MAP, cascade logic |

### Modified Files

| File | Changes |
|---|---|
| `codex/core/services/town_crier.py` | `CrierVoice.narrate_trend()`, momentum decay in `CivicPulse.advance()` |
| `codex/world/genesis.py` | `GrapesProfile.mutate()` method + mutation persistence |
| `play_burnwillow.py` | `GameState.momentum_ledger`, recording after `log_event()`, threshold handling |
| `play_universal.py` | Momentum ledger creation + recording in dungeon/FITD loops |
| Save handlers | Serialize/deserialize momentum ledger in meta_state |

### Tests

- `test_momentum_ledger.py`:
  - Verify binning by category + location
  - Verify threshold crossing returns correct events
  - Verify cascade at 20.0 (secondary bin receives weight)
  - Verify decay removes stale bins
  - Verify GRAPES mutation at 12.0 threshold
  - Verify serialization round-trip
  - Verify trend-aware CrierVoice output differs from event-only output
  - Verify backward compat — saves without momentum_ledger load cleanly

---

## Track D: Cross-System Companions + Trait Evolution

### Problem

1. **Companions only available in Burnwillow.** `GenericAutopilotAgent` wraps all 5 engine families but there's no recruitment UI in `play_universal.py`. DnD5e, STC, and FITD players cannot summon companions.
2. **Personality traits are frozen at creation.** A vanguard (aggression=0.9, caution=0.1) who nearly dies every fight never adapts. No learning, no growth.
3. **Combat decisions lack narrative explanation.** When a companion charges recklessly, the player sees the action but not the motivation.

### What Exists

- **`codex/games/burnwillow/autopilot.py`** (647 lines): `AutopilotAgent`, `CompanionPersonality`, `PERSONALITY_POOL`, `create_ai_character()`, `decide_exploration()`, `decide_combat()`, `decide_hub()`, `select_ai_target()`, `register_companion_as_npc()`
- **`codex/core/autopilot.py`** (225 lines): `GenericAutopilotAgent` with snapshot builders for Burnwillow/DnD5e/STC/BitD/Crown
- **`play_burnwillow.py`**: Full companion command, persistence, combat execution
- **`play_universal.py`**: Zero companion integration

### Implementation

#### D1: Companion command in play_universal.py

Add `companion` command to both `_run_dungeon_loop()` and `_run_fitd_loop()`:

```python
elif verb == "companion":
    await _handle_companion_command(con, engine, state, args)
```

**`_handle_companion_command()`** flow:
1. If no companion exists: show personality selection menu (4 archetypes)
2. Player picks archetype (or "random")
3. Call `create_ai_character(archetype=choice)` — reuse existing factory
4. Create engine-appropriate character:
   - **DnD5e**: Use engine's `create_character()` with mapped class (vanguard→Fighter, scholar→Wizard, scavenger→Rogue, healer→Cleric)
   - **STC**: Map to Cosmere orders
   - **FITD**: Map to playbooks (vanguard→Cutter/Muscle, scholar→Whisper/Mystic, etc.)
5. Add to `engine.party`
6. Create `GenericAutopilotAgent(personality, system_tag)` and store in state
7. Register as NPC for dialogue via `register_companion_as_npc()`
8. If companion exists: show status (name, archetype, personality floats, biography)

**Companion in dungeon combat:**
In `_run_dungeon_loop()` combat resolution, check for active `GenericAutopilotAgent`:
```python
if companion_agent and companion_agent.enabled:
    snapshot = companion_agent.build_snapshot(engine, "combat")
    action = companion_agent.agent.decide_combat(snapshot)
    # Execute action on engine
    companion_agent.execute(action, engine)
```

**Companion in FITD scenes:**
In `_run_fitd_loop()`, companions contribute to group actions:
- On `action` command, if companion exists and action matches archetype strength, companion assists (+1d)
- On `engagement` roll, companion's personality influences approach suggestion

**Companion in exploration:**
In dungeon loop idle phase, companion auto-acts based on `decide_exploration()`:
- Scholar: "Theron examines the runes on the north wall." (auto-investigate)
- Scavenger: "Isolde pockets a handful of loose coins." (auto-loot minor items)
- Display as `[dim][Companion] action description[/dim]` so player sees it but isn't interrupted

#### D2: Archetype-to-system mapping

```python
# Maps personality archetypes to system-specific character classes/playbooks
COMPANION_CLASS_MAP = {
    "dnd5e": {
        "vanguard": {"class": "Fighter", "background": "Soldier"},
        "scholar": {"class": "Wizard", "background": "Sage"},
        "scavenger": {"class": "Rogue", "background": "Criminal"},
        "healer": {"class": "Cleric", "background": "Acolyte"},
    },
    "stc": {
        "vanguard": {"order": "Windrunner", "role": "front-line"},
        "scholar": {"order": "Truthwatcher", "role": "support"},
        "scavenger": {"order": "Lightweaver", "role": "utility"},
        "healer": {"order": "Edgedancer", "role": "healer"},
    },
    "bitd": {
        "vanguard": "Cutter",
        "scholar": "Whisper",
        "scavenger": "Lurk",
        "healer": "Leech",
    },
    "sav": {
        "vanguard": "Muscle",
        "scholar": "Mystic",
        "scavenger": "Scoundrel",
        "healer": "Mechanic",
    },
    "bob": {
        "vanguard": "Heavy",
        "scholar": "Medic",
        "scavenger": "Scout",
        "healer": "Officer",
    },
    "cbrpnk": {
        "vanguard": "Punk",
        "scholar": "Hacker",
        "scavenger": "Runner",
        "healer": "Fixer",
    },
    "candela": {
        "vanguard": "Face",
        "scholar": "Weird",
        "scavenger": "Slink",
        "healer": "Muscle",
    },
}
```

#### D3: Trait evolution system

Add `TraitEvolution` tracker to `CompanionPersonality`:

```python
@dataclass
class TraitDelta:
    """A recorded event that nudges personality floats."""
    trait: str              # "aggression", "curiosity", "caution"
    delta: float            # +/- change (small: 0.02-0.05)
    reason: str             # "nearly_died", "saved_ally", "explored_secret"
    turn: int

class TraitEvolution:
    """Tracks cumulative nudges to personality floats over time."""

    # Maximum drift from original values (prevents complete personality inversion)
    MAX_DRIFT = 0.4

    def __init__(self, original: CompanionPersonality):
        self.original = original
        self.deltas: List[TraitDelta] = []

    def nudge(self, trait: str, delta: float, reason: str, turn: int = 0) -> None:
        """Apply a small personality nudge. Clamps to MAX_DRIFT from original."""
        ...

    def get_current(self) -> CompanionPersonality:
        """Return personality with accumulated nudges applied."""
        ...

    def get_evolution_summary(self) -> str:
        """Return narrative summary of how companion has changed."""
        ...

    def to_dict(self) / from_dict(): ...
```

**Nudge triggers (in combat/exploration resolution):**

| Event | Trait | Delta | Reason |
|---|---|---|---|
| Companion drops below 20% HP | caution | +0.03 | "nearly_died" |
| Companion kills a boss | aggression | +0.02 | "killed_boss" |
| Companion saves an ally (intercept/triage) | caution | -0.02, aggression | -0.01 | "saved_ally" |
| Companion explores a secret room | curiosity | +0.02 | "found_secret" |
| Player verbally praises companion (via talk) | — | context-dependent | "player_feedback" |
| Companion is healed by player 3+ times in one run | caution | +0.04 | "learned_caution" |
| Companion survives a full dungeon run at <30% HP | aggression | -0.02, caution | +0.03 | "survivor_growth" |

**Drift cap:** No float can drift more than 0.4 from its original value. A vanguard (aggression=0.9) can drop to 0.5 but never to 0.1 — they remain fundamentally aggressive but learn some restraint.

#### D4: Narrated companion decisions

When a companion acts, prepend a short motivation line based on personality:

```python
DECISION_NARRATION = {
    ("attack", "vanguard"): [
        "{name} snarls and charges forward.",
        "{name} doesn't hesitate — blade first.",
    ],
    ("attack", "scholar"): [
        "{name} strikes reluctantly, eyes still scanning the room.",
        "{name} lands a precise, calculated blow.",
    ],
    ("guard", "healer"): [
        "{name} raises a ward and braces.",
        "{name} whispers a prayer and holds position.",
    ],
    ("triage", "healer"): [
        "{name} rushes to {target}'s side, hands already working.",
        "\"Hold still,\" {name} mutters, pressing cloth to the wound.",
    ],
    ("attack_reckless", "vanguard"): [  # When attacking at <20% HP
        "{name} ignores the blood streaming down their arm and charges.",
        "\"Not yet,\" {name} growls, throwing themselves at {target}.",
    ],
}
```

Display as: `[italic dim]{narration}[/italic dim]` before the mechanical action output.

For evolved companions, reference the evolution:
- If `caution` has drifted +0.15 from original: "{name} hesitates — then charges anyway, but angles for cover."
- If `aggression` has drifted -0.1 from original: "{name} holds the line instead of charging. They've learned."

#### D5: Persistence for universal companions

Save companion state in campaign manifest alongside engine state:
```json
{
  "companion": {
    "name": "Theron",
    "system_tag": "dnd5e",
    "personality": { "archetype": "scholar", ... },
    "evolution": {
      "original": { "aggression": 0.2, "curiosity": 0.9, "caution": 0.6 },
      "deltas": [
        {"trait": "caution", "delta": 0.03, "reason": "nearly_died", "turn": 47},
        ...
      ]
    },
    "character_state": { /* engine-specific character save data */ }
  }
}
```

### New Files

| File | Purpose |
|---|---|
| `codex/core/trait_evolution.py` | `TraitDelta`, `TraitEvolution`, nudge triggers, drift capping, evolution summaries |
| `codex/core/companion_maps.py` | `COMPANION_CLASS_MAP`, `DECISION_NARRATION`, cross-system archetype-to-class mapping |

### Modified Files

| File | Changes |
|---|---|
| `codex/games/burnwillow/autopilot.py` | Import `TraitEvolution`, wire nudge calls in `decide_combat()` outcomes |
| `codex/core/autopilot.py` | `GenericAutopilotAgent` gains `evolution: TraitEvolution` field, `nudge()` passthrough, `get_effective_personality()` |
| `play_universal.py` | `_handle_companion_command()`, companion combat/exploration in dungeon loop, companion assist in FITD loop, companion save/load, `companion` in COMMAND_CATEGORIES |
| `play_burnwillow.py` | Wire `TraitEvolution` into existing companion system, nudge calls at combat resolution |

### Tests

- `test_companion_universal.py`:
  - Verify companion creation for each system tag (9 engines)
  - Verify `COMPANION_CLASS_MAP` covers all systems
  - Verify companion combat integration in dungeon loop mock
  - Verify companion save/load round-trip in universal format
- `test_trait_evolution.py`:
  - Verify nudge accumulation
  - Verify MAX_DRIFT cap prevents inversion
  - Verify `get_current()` returns modified personality
  - Verify evolution summary narrative
  - Verify serialization round-trip
  - Verify nudge triggers fire at correct combat events
- `test_companion_narration.py`:
  - Verify decision narration varies by archetype
  - Verify evolved companions get modified narration
  - Verify narration fallback when archetype/action combo not in map

---

## Execution Order

1. **Track A** — Emotional Anchor Shards (smallest scope, immediate recap improvement)
2. **Track B** — Narrative Mood Injection (connects existing patterns, moderate scope)
3. **Track D** — Cross-System Companions (completes existing feature, high player impact)
4. **Track C** — Momentum Ledger (new subsystem, largest scope, highest long-term impact)

Tests throughout. Each track must pass full suite (`python -m pytest tests/ -x`) before moving to next.

---

## Verification

1. **Track A**: Run a Burnwillow session where a character nearly dies, use a rare item, and complete a quest. Verify recap includes "Key Moments" section referencing these events, not just kill/loot counts.
2. **Track B**: Start a DnD5e session. Take heavy damage. Verify room descriptions on next `look` command include mood-aware language. Verify NPC dialogue acknowledges party condition.
3. **Track C**: Over 5+ Burnwillow runs, repeatedly clear security threats in one area. Verify TownCryer broadcasts shift from "guards are nervous" to "the ward flourishes under unnamed heroes." Verify GRAPES profile reflects the shift.
4. **Track D**: In `play_universal.py`, start a DnD5e session. Type `companion`. Select "vanguard." Verify Fighter companion joins party. Enter combat. Verify companion acts with personality-driven narration. After 3 near-death events, verify `caution` float has drifted upward.
5. **Full regression**: `python -m pytest tests/ -x` — all tests pass, zero regressions.

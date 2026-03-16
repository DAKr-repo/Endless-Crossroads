# WORK ORDER: WO-V62.0 — Session Architecture, Willow Wood & GRAPES Mutation

**Priority:** HIGH
**Assignee:** @Mechanic, @Designer, @Architect
**Dependencies:** WO-V61.0 (Momentum Ledger, Anchor Shards), WO-V54.0 (Playability Sprint), WO-V45.0 (NPC Memory)
**Origin:** Design review — session framing gaps, missing overworld layer, unwired mutation system

---

## Overview

Four interconnected gaps prevent Burnwillow (and all game systems) from supporting both quick one-shots and long-form freeform campaigns:

1. **No session framing** — games start and stop but nothing marks a "session" as a unit. No session numbering, no opening hooks, no structured wrap-up. One-shots and campaigns use the same undifferentiated flow.
2. **No overworld** — Emberhome connects directly to dungeon. There's no transition space, no exploration outside dungeons, no place for the world to *feel* alive between delves.
3. **GRAPES mutation unwired** — `WorldLedger.mutate()` exists but nothing calls it. Player actions accumulate momentum (WO-V61.0) but never change the world. The feedback loop is open.
4. **No character portability** — Characters are locked to their save file. No way to keep a one-shot character, import a character into a new campaign, or carry a veteran into a different session type.

This WO closes all four gaps across all game systems.

---

## Track A: Session Architecture — Universal Session Frame

### Problem

There's no concept of a "session" as a discrete unit. A player can't do a quick 15-minute one-shot with a clean ending, nor can they track "session 4 of my campaign" across saves. The game loop is: start → play until quit → maybe save. No opening, no structured close. No epilogue showing the world reacting to what just happened. No way to carry a character from one session type to another.

### What Exists

- `_session_log` on both bridges (WO-V61.0) — event list per play session
- `summarize_session()` in narrative_loom.py — recap generation
- `SessionManifest` in narrative_loom.py — session anchoring (unused beyond init)
- `CivicPulse.advance()` — tick-driven events (currently only advances on doom ticks)
- `MomentumLedger` (WO-V61.0) — trend tracking, threshold crossing
- Save system — full state persistence

### Implementation

#### A1: SessionFrame dataclass

**New file:** `codex/core/session_frame.py`

```python
@dataclass
class SessionFrame:
    """Wraps a play session with identity, type, and lifecycle hooks."""
    session_id: str              # UUID or sequential "campaign_name_003"
    session_number: int          # Sequential within campaign (1, 2, 3...)
    session_type: str            # "one_shot", "expedition", "campaign", "freeform"
    campaign_id: Optional[str]   # None for one-shots
    started_at: str              # ISO timestamp
    ended_at: Optional[str]      # Set on close
    opening_hook: str            # Narrative hook shown at session start
    turn_count: int = 0          # Turns elapsed this session
    anchor_count: int = 0        # Dramatic moments logged
    summary: str = ""            # 1-sentence summary generated at close (used by future opening hooks)

    # Lifecycle
    def close(self, session_log, engine_snapshot, mimir_fn=None):
        """End the session: generate recap + epilogue, advance civic pulse, decay momentum."""
        self.ended_at = datetime.now().isoformat()
        self.summary = _generate_session_summary(session_log, mimir_fn)
        ...

    def to_dict(self) / from_dict(cls, data): ...
```

#### A2: Session types and their behaviors

| Type | Duration Target | Persistence | Momentum Decay | Civic Advance | World Mutation | Character Keep |
|---|---|---|---|---|---|---|
| `one_shot` | 15-30 min | Character only (player choice) | None | None | None | Offered at close |
| `expedition` | 1-2 hrs | Character + quests + momentum | Per-expedition | +2 ticks | At thresholds only | Auto |
| `campaign` | Multi-session | Full state | Per-session close | +1 tick/session | At thresholds | Auto |
| `freeform` | Open-ended | Full state + GRAPES | Per-session close | +1 tick/session | At thresholds + rumor-driven | Auto |

**One-shot character persistence (player choice):**

At one-shot close, the player is offered:
```
Your delve is complete.
  1. Walk away     — This character's story ends here.
  2. Keep walking  — Export this character for future adventures.
```

Option 2 exports the character to `saves/characters/{name}_{system_id}.json` — a standalone character file stripped of world state, quest progress, and session context. This file can be imported into any future session of the same system (see A8).

#### A3: Session start flow

In all play loops (`play_burnwillow.py`, `play_universal.py`), wrap the game loop:

```python
# At game start, after character creation / save load
session = SessionFrame(
    session_id=f"{campaign_id}_{session_number:03d}",
    session_number=_get_next_session_number(campaign_id),
    session_type=selected_type,  # From menu or CLI arg
    campaign_id=campaign_id,
    started_at=datetime.now().isoformat(),
    opening_hook=_generate_opening_hook(state, prior_sessions),
)
# Display hook
con.print(Panel(session.opening_hook, title=f"Session {session.session_number}", border_style="cyan"))
```

#### A4: Opening hook generation (session-history-aware)

```python
def _generate_opening_hook(state, prior_sessions: List[dict] = None, mimir_fn=None) -> str:
    """Generate a session-opening narrative hook from current world state and prior sessions."""
    momentum = getattr(state, 'momentum_ledger', None)

    # Reference prior session summaries for continuity
    if prior_sessions:
        last = prior_sessions[-1]
        last_summary = last.get("summary", "")
        sessions_count = len(prior_sessions)
        # "It has been three expeditions since you first entered the depths."

    if momentum:
        dominant = momentum.get_dominant_trend(location or "unknown")
        if dominant and dominant[1] >= 7.0:
            # Trend-based hook: "The docks are thriving. But something stirs beneath..."
            ...

    # Mimir generation: feed prior session summaries + momentum + anchor events
    if mimir_fn and prior_sessions:
        context_lines = [f"Session {s['session_number']}: {s['summary']}" for s in prior_sessions[-3:]]
        prompt = (
            "Write a 1-2 sentence opening hook for a new game session. "
            "Reference what happened before:\n" + "\n".join(context_lines)
        )
        try:
            result = mimir_fn(prompt, "")
            if result and len(result) > 10:
                return result.strip()
        except Exception:
            pass

    # Fallback: generic hooks by session type
    ONE_SHOT_HOOKS = [
        "The posting board at the crossroads has one last notice, pinned with a rusted nail.",
        "A stranger presses a map into your hands and vanishes into the crowd.",
    ]
    ...
```

#### A5: Session close flow with epilogue

At every exit point (quit command, victory, death, save-and-quit):

```python
session.close(
    session_log=state.session_log,  # or bridge._session_log
    engine_snapshot=_build_snapshot(state),
    mimir_fn=mimir_fn,
)

# Advance CivicPulse by session type
if session.session_type in ("campaign", "freeform", "expedition"):
    ticks = 2 if session.session_type == "expedition" else 1
    if hasattr(state.engine, 'civic_pulse') and state.engine.civic_pulse:
        fired = state.engine.civic_pulse.advance(ticks)
        for event in fired:
            con.print(f"[dim italic]Town Crier: {crier.narrate(event, {})}[/]")

# Momentum decay for stale bins
if momentum_ledger:
    pruned = momentum_ledger.decay(current_turn=state.turn_number)

# Generate recap
recap = summarize_session(state.session_log, snapshot, mimir_fn)
con.print(Panel(recap, title="Session Recap", border_style="yellow"))

# Generate epilogue — "what happens after you leave" vignette
epilogue = _generate_epilogue(state, session, mimir_fn)
if epilogue:
    con.print(Panel(epilogue, title="Meanwhile...", border_style="dim cyan"))

# One-shot: offer character export
if session.session_type == "one_shot":
    _offer_character_export(state, con)

# Persist session number + summary
_save_session_counter(campaign_id, session.session_number)
```

#### A5a: Epilogue generation

```python
def _generate_epilogue(state, session: SessionFrame, mimir_fn=None) -> Optional[str]:
    """Generate a brief 'what happens after you leave' vignette."""
    if session.session_type == "one_shot":
        return None  # One-shots are self-contained

    # Build context from anchor events, GRAPES state, momentum trends
    anchors = [e for e in state.session_log if e.get("type") in ANCHOR_EVENT_TYPES]
    momentum = getattr(state, 'momentum_ledger', None)
    grapes = getattr(state, '_grapes_profile', None)

    if mimir_fn:
        context_parts = []
        if anchors:
            context_parts.append(f"Key events: {', '.join(a['type'] for a in anchors[-5:])}")
        if momentum:
            dominant = momentum.get_dominant_trend("all")
            if dominant:
                context_parts.append(f"Dominant trend: {dominant[0]} ({dominant[1]:.1f})")

        prompt = (
            "Write a 2-3 sentence epilogue for a game session. Describe what happens "
            "in the world after the player leaves — NPCs reacting, consequences unfolding, "
            "hints of what's to come. Do NOT address the player directly.\n\n"
            + "\n".join(context_parts)
        )
        try:
            result = mimir_fn(prompt, "")
            if result and len(result) > 20:
                return result.strip()
        except Exception:
            pass

    # Fallback: static epilogues based on session events
    if any(a["type"] == "party_death" for a in anchors):
        return "Word of the fallen spreads quietly through town. A candle is lit at the shrine."
    if any(a["type"] == "doom_threshold" for a in anchors):
        return "The ground trembles faintly. Something stirs in the deep places."
    return None
```

#### A6: Session type selection UI

At game start (new game flow), after character creation:

```
How would you like to play?
  1. Quick Delve  — A single dungeon run. No strings attached.
  2. Expedition   — Explore, fight, return. Your progress matters.
  3. Campaign     — A continuing story across multiple sessions.
  4. Freeform     — The world responds to you. No fixed ending.
```

For returning players (loading a save), the session type is stored in the save.

#### A7: Persistence

Add to save format:
```json
{
    "session_type": "freeform",
    "session_number": 4,
    "campaign_id": "burnwillow_kael_2026",
    "sessions_played": [
        {"session_id": "..._001", "turns": 45, "anchors": 3, "summary": "Kael cleared the root cellar and befriended the wounded scout."},
        {"session_id": "..._002", "turns": 62, "anchors": 7, "summary": "The party barely survived the Spore Chamber. The doom clock crossed its second threshold."},
    ]
}
```

Each session stores a 1-sentence `summary` generated at close. These summaries are fed to opening hook generation for narrative continuity across sessions.

#### A8: Character import system

**New file:** `codex/core/character_export.py`

```python
def export_character(engine, char_index: int = 0) -> dict:
    """Export a character as a portable dict, stripped of world/session state."""
    state = engine.save_state()
    # Extract character data only — no room, quest, doom, world state
    char_data = _extract_character_only(state, engine.__class__.__name__, char_index)
    char_data["_export_meta"] = {
        "system_id": engine.system_id,
        "exported_at": datetime.now().isoformat(),
        "source_campaign": getattr(engine, 'campaign_id', None),
        "level": char_data.get("level", 1),
    }
    return char_data

def import_character(engine, char_data: dict) -> bool:
    """Import a previously exported character into an engine.
    Returns True if successful, False if system mismatch."""
    meta = char_data.get("_export_meta", {})
    if meta.get("system_id") != engine.system_id:
        return False  # System mismatch — can't import a BitD character into Burnwillow
    _inject_character(engine, char_data)
    return True

def list_exported_characters(system_id: str = None) -> List[dict]:
    """List all exported character files, optionally filtered by system."""
    saves_dir = Path("saves/characters")
    if not saves_dir.exists():
        return []
    chars = []
    for f in saves_dir.glob("*.json"):
        data = json.loads(f.read_text())
        meta = data.get("_export_meta", {})
        if system_id is None or meta.get("system_id") == system_id:
            chars.append({"file": f.name, "name": data.get("name", "Unknown"), **meta})
    return chars
```

Character import is offered at session start:
```
Create your character:
  1. New character
  2. Import existing character
```

Option 2 lists exported characters for the current system_id. The imported character enters the new session with their stats/gear intact but no quest progress, no world state, and session_number reset to 1.

### Files Modified

| File | Changes |
|---|---|
| `codex/core/session_frame.py` | **NEW** — SessionFrame, opening hooks, epilogue, close logic |
| `codex/core/character_export.py` | **NEW** — export_character(), import_character(), list_exported_characters() |
| `play_burnwillow.py` | Session type menu, frame wrapping, close on exit, character export/import |
| `play_universal.py` | Same session framing for all universal systems |
| Save format | `session_type`, `session_number`, `campaign_id`, `sessions_played` with summaries |

### Tests

- `test_session_frame.py`: SessionFrame lifecycle, serialization, session numbering, summary storage
- Verify one_shot sessions don't persist world state
- Verify one_shot close offers character export
- Verify campaign sessions increment session_number
- Verify opening hooks reference prior session summaries
- Verify epilogue generates for campaign/freeform, not for one_shot
- `test_character_export.py`: Export roundtrip, system_id mismatch rejection, import into fresh engine, list filtering

---

## Track B: The Willow Wood — Burnwillow Overworld

### Problem

Emberhome → Dungeon is a hard cut. There's no transition, no sense of journey, no place for non-combat exploration. The world feels like two disconnected rooms: safe hub and deadly dungeon.

### Lore Foundation

The Willow Wood surrounds Emberhome — a small forest of willow trees, each sprouted from a seed of the great Burnwillow that fell from the canopy above. The willows thin and wither as the forest approaches the Grove's edge. This is the living boundary between civilization and rot.

### Design Principles

1. **Multi-pillar encounters**: Every encounter offers multiple resolution paths — RP/narrative, social, exploration, and combat. The player chooses the approach. A territorial beast can be fought, calmed, lured away, or studied. A collapsed bridge can be repaired, circumvented, or the river forded.
2. **Secrets and discovery**: Hidden rooms, lore objects, and environmental puzzles reward exploration — similar to dungeon vaults and secrets but themed around the wilderness.
3. **Procedural paths**: Fixed landmark rooms form the skeleton; procedural corridor rooms flesh out each path to a destination, making every session's journey feel different.
4. **Living barometer**: Specific rooms reflect GRAPES world state, making the Wood a visible indicator of how the world is changing.

### Implementation

#### B1: Willow Wood zone architecture

The Wood has two layers:

1. **Landmark rooms** (8-10 fixed): Named locations that persist and serve as feature entry points. These are always present and always in the same relative positions.
2. **Path rooms** (3-5 procedural per path): Generated between landmarks and destination gates. Seeded from `session_number` so each visit is different, but the same session always generates the same path.

```
                         ┌──[proc]──[proc]──[proc]── DESCENT GATE (Root Stair)
                         │
GROVE HEART ── SHRINE ── CROSSING ──[proc]──[proc]── CAVE MOUTH
    │              │         │
    └── HOLLOW ────┴── THICKET ──[proc]──[proc]──[proc]── ASCENT GATE (Canopy Ladder)
         │                │
         └── CLEARING ────┘
              (GRAPES barometer)
```

Each path between a landmark and a destination gate has 3-5 procedural rooms drawn from a room pool.

#### B2: Landmark rooms (fixed)

**New file:** `codex/spatial/blueprints/willow_wood.json`

```json
{
    "zone_id": "willow_wood",
    "display_name": "The Willow Wood",
    "topology": "wilderness",
    "theme": "RUST",
    "landmark_rooms": [
        {"id": 0, "type": "grove_heart", "name": "Heart of the Wood", "tier": 0,
         "description": "Ancient willows crowd together here, their roots intertwined. Emberhome's lanterns glow faintly through the canopy behind you.",
         "connections": [1, 2],
         "grapes_binding": null},
        {"id": 1, "type": "shrine", "name": "The Wayward Shrine", "tier": 0,
         "description": "A moss-covered shrine carved into a hollow trunk. Someone has left fresh wildflowers.",
         "connections": [0, 3], "services": ["save", "rest"],
         "grapes_binding": "religion"},
        {"id": 2, "type": "hollow", "name": "The Whisper Hollow", "tier": 0,
         "description": "The ground dips into a natural bowl. Voices carry strangely here — you hear fragments of conversation from nowhere.",
         "connections": [0, 4], "services": ["npc_encounter"],
         "grapes_binding": "social"},
        {"id": 3, "type": "crossing", "name": "Merchant's Crossing", "tier": 1,
         "description": "A well-worn path crosses a shallow stream. Cart tracks mark the mud on both sides.",
         "connections": [1, 5, 6], "services": ["trade"],
         "grapes_binding": "economics"},
        {"id": 4, "type": "thicket", "name": "The Withering Thicket", "tier": 1,
         "description": "The willows here are skeletal — bark peeling, branches bare. Something has drained the life from them.",
         "connections": [2, 5, 7],
         "grapes_binding": "geography"},
        {"id": 5, "type": "clearing", "name": "Ashen Clearing", "tier": 1,
         "description": "A circle of scorched earth where nothing grows. The stumps of burned willows ring the clearing like teeth.",
         "connections": [3, 4, 7],
         "grapes_binding": "security"},
        {"id": 6, "type": "pool", "name": "The Still Pool", "tier": 0,
         "description": "A dark pond fed by no visible stream. The water is perfectly still — not even leaves disturb the surface.",
         "connections": [0, 5],
         "grapes_binding": null},
        {"id": 7, "type": "rootbridge", "name": "The Rootbridge", "tier": 1,
         "description": "Living roots form a natural bridge over a deep ravine. The wood groans and shifts underfoot.",
         "connections": [4, 3],
         "grapes_binding": null}
    ],
    "destination_gates": [
        {"gate_id": "descent", "name": "The Root Stair", "tier": 1,
         "exit_type": "descend",
         "description": "Massive roots spiral downward into darkness. The air rising from below smells of damp earth and iron.",
         "path_from": 3, "path_rooms": "3-5"},
        {"gate_id": "ascent", "name": "The Canopy Ladder", "tier": 1,
         "exit_type": "ascend",
         "description": "Woven rope ladders ascend through thinning branches toward the distant crown of the Burnwillow.",
         "path_from": 4, "path_rooms": "3-5"},
        {"gate_id": "cave", "name": "The Maw", "tier": 2,
         "exit_type": "descend",
         "description": "A jagged crack in the hillside exhales a cold breath. Claw marks line the stone around the entrance.",
         "path_from": 3, "path_rooms": "4-5"}
    ],
    "start_room": 0,
    "npc_pool": ["wandering_herbalist", "lost_traveler", "wounded_scout", "mushroom_forager",
                 "fleeing_merchant", "willow_tender", "ghost_lantern_keeper"],
    "encounter_table": {
        "tier_0": ["will_o_wisp", "twig_blight", "root_crawler", "lost_fawn"],
        "tier_1": ["blighted_wolf", "spore_shambler", "rot_sprite", "territorial_boar"],
        "tier_2": ["hollow_knight", "canopy_stalker", "rot_elemental"]
    }
}
```

#### B3: Procedural path rooms

**New section in blueprint:** `path_room_pool`

Each path between a landmark and a gate draws 3-5 rooms from a themed pool. The pool is shuffled using `session_seed = hash(session_number + gate_id)`.

```json
{
    "path_room_pool": [
        {"type": "trail", "name_pool": ["Winding Trail", "Overgrown Path", "Deer Track", "Mud Lane"],
         "tier": 0, "encounter_chance": 0.1,
         "description_pool": [
             "The path narrows between leaning willows. Footprints in the mud suggest recent passage.",
             "Fallen branches block the trail. Someone has been cutting them — recently.",
             "A game trail winds through tall grass. Something rustles just out of sight."
         ]},
        {"type": "stream", "name_pool": ["Shallow Ford", "The Trickle", "Moss Creek", "Iron Brook"],
         "tier": 0, "encounter_chance": 0.2,
         "description_pool": [
             "A shallow stream cuts across the path. The water runs dark with tannin.",
             "Stepping stones cross a bubbling brook. One stone has a carved rune on its face."
         ]},
        {"type": "grove", "name_pool": ["Silent Grove", "Twisted Copse", "The Weeping Stand"],
         "tier": 1, "encounter_chance": 0.3,
         "description_pool": [
             "A ring of willows leans inward, branches touching like clasped hands.",
             "The trees here grow in a spiral pattern. The air smells of sap and decay."
         ]},
        {"type": "ruin", "name_pool": ["Broken Waypost", "Collapsed Lean-To", "Foundation Stones"],
         "tier": 1, "encounter_chance": 0.4,
         "description_pool": [
             "Stone foundations peek through moss. Someone lived here once.",
             "A crumbled waypost lists directions to places you've never heard of."
         ]},
        {"type": "den", "name_pool": ["Hollow Log", "Beast's Den", "Bramble Nest"],
         "tier": 1, "encounter_chance": 0.5,
         "description_pool": [
             "Claw marks score the earth around a massive hollow log. Something lives here.",
             "Bones and fur litter the ground. The den's occupant is elsewhere — for now."
         ]},
        {"type": "overlook", "name_pool": ["Ridge View", "The Lookout", "Canopy Gap"],
         "tier": 0, "encounter_chance": 0.0,
         "description_pool": [
             "A break in the canopy reveals the landscape below. You can see far from here.",
             "The ridge offers a clear view. Smoke rises from Emberhome in the distance."
         ]}
    ]
}
```

**Path generation algorithm:**

```python
def _generate_path_rooms(gate: dict, session_seed: int, room_pool: list) -> list:
    """Generate 3-5 procedural rooms between a landmark and a gate."""
    rng = random.Random(session_seed ^ hash(gate["gate_id"]))
    count = rng.randint(gate.get("path_rooms_min", 3), gate.get("path_rooms_max", 5))
    available = [r for r in room_pool if r["tier"] <= gate["tier"]]
    selected = rng.sample(available, min(count, len(available)))
    rooms = []
    for i, template in enumerate(selected):
        room = {
            "id": f"path_{gate['gate_id']}_{i}",
            "name": rng.choice(template["name_pool"]),
            "type": template["type"],
            "tier": template["tier"],
            "description": rng.choice(template["description_pool"]),
            "encounter_chance": template["encounter_chance"],
        }
        rooms.append(room)
    return rooms
```

#### B4: Multi-pillar encounters

Encounters in the Willow Wood are NOT combat-first. Each encounter offers multiple resolution approaches:

```python
WOOD_ENCOUNTERS = {
    "territorial_boar": {
        "name": "Territorial Boar",
        "description": "A massive boar blocks the trail, tusks lowered, eyes red.",
        "approaches": {
            "combat": {"dc": 12, "reward": "boar_hide", "description": "Fight the beast head-on."},
            "social": {"dc": 10, "skill": "command", "reward": "boar_ally_1_room",
                       "description": "Calm the beast with steady voice and posture."},
            "exploration": {"dc": 8, "skill": "perception", "reward": "bypass",
                           "description": "Spot a side trail that avoids the boar entirely."},
            "narrative": {"dc": 0, "reward": "lore_fragment",
                         "description": "Observe quietly. The boar guards a shallow grave — someone buried here."},
        }
    },
    "will_o_wisp": {
        "name": "Will-o'-Wisp",
        "description": "A pale light drifts between the trees, always just ahead.",
        "approaches": {
            "combat": {"dc": 14, "reward": "wisp_essence", "description": "Attack the light. It fights back."},
            "social": {"dc": 12, "skill": "mending", "reward": "guided_to_secret",
                       "description": "Offer a prayer. The wisp brightens and waits."},
            "exploration": {"dc": 10, "skill": "perception", "reward": "shortcut",
                           "description": "Follow at a distance. It leads you somewhere unexpected."},
            "narrative": {"dc": 0, "reward": "lore_fragment",
                         "description": "Watch it fade. You notice it hovers where a name is carved into bark."},
        }
    },
    "collapsed_bridge": {
        "name": "Collapsed Bridge",
        "description": "The old bridge has given way. The ravine is too wide to jump.",
        "approaches": {
            "combat": {"dc": 0, "reward": "none", "description": "Nothing to fight here."},
            "social": {"dc": 10, "skill": "command", "reward": "npc_help",
                       "description": "Call out. A voice answers from the other side."},
            "exploration": {"dc": 12, "skill": "perception", "reward": "hidden_crossing",
                           "description": "Search downstream. Find a fallen tree spanning the gap."},
            "narrative": {"dc": 0, "reward": "lore_fragment",
                         "description": "The bridge was cut deliberately. Tool marks on the supports."},
        }
    },
    "lost_fawn": {
        "name": "Lost Fawn",
        "description": "A young deer stands trembling in the underbrush, leg caught in old wire.",
        "approaches": {
            "combat": {"dc": 0, "reward": "none", "description": "There's nothing to fight here."},
            "social": {"dc": 8, "skill": "triage", "reward": "fawn_freed",
                       "description": "Approach slowly and free the trapped leg."},
            "exploration": {"dc": 10, "skill": "perception", "reward": "snare_network",
                           "description": "Follow the wire. Find a network of old traps — and who set them."},
            "narrative": {"dc": 0, "reward": "lore_fragment",
                         "description": "The wire is dwarven make, corroded green. This trap is very old."},
        }
    },
}
```

**Encounter resolution in the game loop:**

```python
def _resolve_wood_encounter(state, encounter: dict, con) -> str:
    """Present a multi-pillar encounter. Returns outcome key."""
    con.print(Panel(encounter["description"], title=encounter["name"], border_style="yellow"))
    con.print("[bold]How do you approach?[/]")
    approaches = encounter["approaches"]
    for i, (key, approach) in enumerate(approaches.items(), 1):
        if approach.get("dc", 0) > 0:
            con.print(f"  {i}. [{key.upper()}] {approach['description']}")
        else:
            con.print(f"  {i}. [{key.upper()}] {approach['description']}")

    choice = _get_choice(con, len(approaches))
    chosen_key = list(approaches.keys())[choice]
    approach = approaches[chosen_key]

    if approach["dc"] > 0:
        # Roll against DC using relevant skill
        result = roll_dice_pool(dice_count, mod, approach["dc"])
        if result["success"]:
            con.print(f"[green]Success![/] {_narrate_success(encounter, chosen_key)}")
            return approach["reward"]
        else:
            con.print(f"[red]Failed.[/] {_narrate_failure(encounter, chosen_key)}")
            return "fail"
    else:
        # Narrative approaches always succeed
        con.print(f"[cyan italic]{_narrate_observation(encounter, chosen_key)}[/]")
        return approach["reward"]
```

#### B5: Secrets and discovery

The Willow Wood contains hidden content that rewards thorough exploration:

**Secret types:**

| Secret Type | Discovery Method | Reward |
|---|---|---|
| `hidden_cache` | Perception check (DC 12) in specific rooms | Tier 1 loot or consumable |
| `lore_inscription` | Investigate action at ruin/shrine rooms | Lore fragment → enriches NPC dialogue + recap |
| `hidden_path` | Found via will-o'-wisp "guided_to_secret" or high perception | Connects to otherwise unreachable room with unique NPC or mini-event |
| `buried_offering` | Interact with shrine after observing lore inscription | Unique trait item or blessing (1-session buff) |
| `willow_seed` | Rare drop from narrative encounters in tier 0 rooms | Consumable: plant in dungeon room to create 1-turn safe rest point |
| `echo_memory` | Listen at The Whisper Hollow after 3+ sessions | Mimir-generated flashback from a prior session's anchor event |

**Secret distribution:**

```python
WOOD_SECRETS = {
    "hidden_cache": {
        "rooms": ["ruin", "den", "overlook"],  # Can appear in these procedural room types
        "dc": 12, "skill": "perception",
        "one_per_session": True,  # Only one hidden cache per Wood visit
        "loot_tier": 1,
    },
    "lore_inscription": {
        "rooms": ["ruin", "shrine", "grove"],
        "dc": 10, "skill": "investigation",
        "one_per_session": False,  # Multiple inscriptions possible
        "reward": "lore_fragment",  # Stored in session_log for recap enrichment
    },
    "hidden_path": {
        "trigger": "guided_to_secret",  # From will-o'-wisp encounter
        "creates_room": True,  # Adds a bonus room to the current path
    },
    "buried_offering": {
        "rooms": ["shrine"],
        "prerequisite": "has_lore_inscription",  # Must have found an inscription first
        "reward": "session_blessing",  # +1 to all DCs for rest of session
    },
    "willow_seed": {
        "rooms": ["grove_heart", "grove", "pool"],
        "drop_chance": 0.15,  # 15% chance from narrative encounters in these rooms
        "reward_item": {"name": "Willow Seed", "tier": 2, "trait": "Sanctuary",
                        "description": "Plant in any dungeon room to create a 1-turn safe rest point."},
    },
    "echo_memory": {
        "rooms": ["hollow"],
        "prerequisite": "session_number >= 3",
        "reward": "flashback",  # Mimir generates a scene from a prior session's anchor event
    },
}
```

**Secret implementation:**

Secrets are checked on room entry (`investigate`/`perceive` commands) or triggered by encounter outcomes. The `echo_memory` secret is special — it feeds prior session summaries to Mimir and asks for a vivid flashback scene, tying the Willow Wood's "whisper" lore to actual gameplay history.

#### B6: GRAPES-reactive landmark rooms

Specific landmark rooms visually and mechanically change based on GRAPES world state:

```python
GRAPES_ROOM_BINDINGS = {
    "economics": {
        "room_id": 3,  # Merchant's Crossing
        "positive": {
            "description_suffix": " A caravan has set up camp here. Lanterns swing from posts.",
            "services": ["trade", "quest_board"],
            "npc_override": "prosperous_merchant",
        },
        "negative": {
            "description_suffix": " The crossing is empty. Rotting crates line the bank.",
            "services": ["trade_limited"],
            "npc_override": "desperate_peddler",
        },
    },
    "security": {
        "room_id": 5,  # Ashen Clearing
        "positive": {
            "description_suffix": " A patrol camp has been established. Soldiers tend a cookfire.",
            "services": ["rest", "quest_board"],
            "npc_override": "patrol_captain",
        },
        "negative": {
            "description_suffix": " Squatters huddle around a dying fire. They watch you with hollow eyes.",
            "encounter_override": "desperate_squatters",
        },
    },
    "religion": {
        "room_id": 1,  # Wayward Shrine
        "positive": {
            "description_suffix": " The shrine gleams. Fresh flowers and candles crowd the alcove.",
            "services": ["save", "rest", "blessing"],
        },
        "negative": {
            "description_suffix": " The shrine has been defaced. Strange symbols are scratched into the bark.",
            "services": ["save"],
            "encounter_override": "shrine_defiler",
        },
    },
    "social": {
        "room_id": 2,  # The Whisper Hollow
        "positive": {
            "description_suffix": " The whispers are warm — laughter, singing, fragments of celebration.",
            "npc_override": "joyful_spirit",
        },
        "negative": {
            "description_suffix": " The whispers are sharp — accusations, weeping, the sound of doors slamming.",
            "npc_override": "grieving_spirit",
        },
    },
    "geography": {
        "room_id": 4,  # The Withering Thicket
        "positive": {
            "description_suffix": " New growth pushes through the dead bark. Green shoots, fragile but alive.",
        },
        "negative": {
            "description_suffix": " The withering has spread further since your last visit. Even the ground is grey.",
            "encounter_chance_bonus": 0.2,  # More hostile encounters
        },
    },
}
```

**Binding evaluation:** On Wood entry, each bound room checks the corresponding GRAPES category's current state. The `WorldLedger.get_category_health(category)` method returns a -1.0 to +1.0 score. Positive (> 0.3) and negative (< -0.3) states modify the room. Neutral stays as the default description.

#### B7: Willow Wood as overworld layer

The Willow Wood sits between Emberhome and all dungeon/cave entries. The flow becomes:

```
EMBERHOME (hub) → [gate] → WILLOW WOOD (overworld)
                                  │
                                  ├── [proc path 3-5 rooms] → ROOT STAIR (underground dungeon)
                                  ├── [proc path 4-5 rooms] → THE MAW (cave system)
                                  └── [proc path 3-5 rooms] → CANOPY LADDER (canopy dungeon)
                                  │
                                  ↑ Can return to Emberhome from grove_heart
                                  ↑ Can explore landmarks freely
                                  ↑ Encounters offer choice, not mandatory combat
                                  ↑ Secrets reward thorough exploration
```

#### B8: Integration into play_burnwillow.py

Replace the current direct Emberhome → dungeon transition:

```python
def _run_willow_wood(state: GameState):
    """Run the Willow Wood overworld exploration phase."""
    con = state.console

    # Load Willow Wood blueprint + generate procedural paths
    wood = WillowWoodZone(
        session_seed=hash(state.session_number or 1),
        grapes_profile=getattr(state, '_grapes_profile', None),
        world_ledger=getattr(state, 'world_ledger', None),
    )
    wood.generate()  # Builds landmarks + procedural paths + applies GRAPES bindings

    # Build spatial rooms for rendering
    wood_rooms = {}
    for rid, node in wood.all_rooms().items():
        wood_rooms[rid] = SpatialRoom.from_map_engine_room(node, ...)

    state.in_willow_wood = True
    state.wood_zone = wood
    state.wood_rooms = wood_rooms
    current_room = 0  # Heart of the Wood (start)

    while state.running and state.in_willow_wood:
        room = wood.get_room(current_room)

        # Render wood map + room description (with GRAPES suffix if bound)
        _render_wood_room(state, room, wood_rooms)

        # Check for secrets in current room
        secrets = wood.check_secrets(current_room, state)
        if secrets:
            _hint_secret(con, secrets)  # "You notice something unusual..."

        # Check for encounter on room entry (procedural rooms only)
        encounter = wood.roll_encounter(current_room, state)
        if encounter:
            outcome = _resolve_wood_encounter(state, encounter, con)
            _apply_encounter_reward(state, outcome, encounter)

        # Standard command loop: move, look, investigate, perceive, talk, rest, etc.
        cmd = _get_wood_command(con)
        if cmd.startswith("move"):
            target = _parse_move(cmd, room)
            if target == "emberhome":
                state.in_willow_wood = False
                break
            current_room = target
        elif cmd == "investigate":
            _investigate_room(state, room, wood)
        elif cmd == "perceive":
            _perceive_room(state, room, wood)
        elif cmd in ("descend", "ascend", "enter"):
            gate = wood.get_gate(current_room)
            if gate:
                state.dungeon_path = gate["exit_type"]
                state.in_willow_wood = False
                break
        ...
```

#### B9: Danger gradient

Encounters scale by distance from Emberhome, but are primarily avoidable:

- **Landmark rooms (tier 0)**: No hostile encounters. NPC interactions, lore, services.
- **Path rooms (tier 0)**: 10-20% encounter chance. Encounters default to non-combat (observation, social, exploration). Combat only if the player escalates or fails a social check.
- **Path rooms (tier 1)**: 30-50% encounter chance. Mix of approaches available. Some encounters have combat as the *easiest* option but not the only one.
- **Path rooms (tier 2, cave path only)**: 50%+ encounter chance. More dangerous, combat is a valid primary approach. Secrets here are rarer but more valuable.

This gives new players a safe space to learn commands in landmarks before venturing down procedural paths.

#### B10: Wood state persistence

The Willow Wood procedural rooms regenerate each session (seeded by session_number), but:
- **Landmark rooms are persistent** — their GRAPES bindings track world state
- **NPC encounters are seeded** from session_number (different NPCs each session)
- **Merchant inventory rotates** based on momentum state and economics GRAPES
- **Discovered secrets are tracked** per save — once you find the buried offering at the shrine, it stays found
- **Collected lore inscriptions** persist in the session log and enrich future opening hooks and NPC dialogue

```python
# In save format:
"willow_wood": {
    "discovered_secrets": ["buried_offering_shrine", "lore_inscription_ruin_3"],
    "collected_seeds": 2,
    "echo_memories_seen": [1, 3],  # Session numbers whose anchors were replayed
}
```

### Files Created

| File | Purpose |
|---|---|
| `codex/spatial/blueprints/willow_wood.json` | Willow Wood zone blueprint (landmarks + path pool + secrets + encounters) |
| `codex/spatial/willow_wood.py` | **NEW** — WillowWoodZone class, path generation, GRAPES binding evaluation, secret/encounter resolution |

### Files Modified

| File | Changes |
|---|---|
| `play_burnwillow.py` | `_run_willow_wood()`, `_resolve_wood_encounter()`, `_investigate_room()`, `_perceive_room()`, transition wiring, GameState fields |
| `codex/games/burnwillow/engine.py` | Willow Wood encounter table (multi-approach), tier 0/1/2 creatures |

### Tests

- `test_willow_wood.py`:
  - Blueprint loads with all landmark rooms
  - Path generation produces 3-5 rooms per gate
  - Path generation is deterministic for same session_seed
  - Different session_seeds produce different paths
  - GRAPES bindings modify room descriptions correctly
  - Multi-pillar encounters offer all approach types
  - Secrets are gated by prerequisites
  - Secret discovery persists across sessions
  - Danger gradient scales with tier
  - Grove heart connects back to Emberhome flow
  - Descent/ascent/cave gates set correct dungeon_path
  - echo_memory requires session_number >= 3

---

## Track C: GRAPES Mutation Wiring

### Problem

`WorldLedger.mutate()` exists with full functionality — category mutation, landmark clearing, resource depletion, historical event recording, chronology — but nothing in the game loop calls it. The Momentum Ledger (WO-V61.0) tracks player action trends and crosses thresholds, but those thresholds don't trigger mutations. The feedback loop is open: players act → momentum accumulates → ...nothing changes.

### What Exists

- `WorldLedger.mutate(category, index, field, value)` — changes a GRAPES field
- `WorldLedger.clear_landmark(name, cleared_by)` — marks geography as cleared
- `WorldLedger.deplete_resource(name)` — shifts abundance to "depleted"
- `WorldLedger.record_historical_event()` — records to chronology
- `WorldLedger.ingest_civic_event()` — bridges CivicPulse events
- `MomentumLedger.record()` — returns threshold crossings (3.0, 7.0, 12.0, 20.0)
- `CrierVoice.narrate()` — generates narrative from events
- `GrapesProfile.to_dict()` / `from_dict()` — serialization ready
- `CrierVoice._grapes_rumor()` — already generates rumors from GRAPES data

### Implementation

#### C1: MomentumThresholdHandler

**New file:** `codex/core/services/momentum_handler.py`

Bridges momentum threshold crossings to world mutations:

```python
"""
Momentum Threshold Handler — Closes the feedback loop.
======================================================

When MomentumLedger.record() returns crossed thresholds, this handler
converts them into concrete world effects: rumors, GRAPES mutations,
ANCHOR shards, and cascade broadcasts.
"""

class MomentumThresholdHandler:
    """Processes momentum threshold crossings into world effects."""

    def __init__(self, world_ledger=None, crier=None, grapes_profile=None,
                 broadcast_manager=None, engine=None):
        self._ledger = world_ledger
        self._crier = crier
        self._grapes = grapes_profile
        self._broadcast = broadcast_manager
        self._engine = engine

    def handle(self, threshold_events: List[dict]) -> List[str]:
        """Process threshold crossings. Returns list of narrative messages."""
        messages = []
        for event in threshold_events:
            level = event["level"]
            if level >= 3.0:
                messages.extend(self._handle_minor_shift(event))
            if level >= 7.0:
                messages.extend(self._handle_notable_trend(event))
            if level >= 12.0:
                messages.extend(self._handle_major_shift(event))
            if level >= 20.0:
                messages.extend(self._handle_tipping_point(event))
        return messages

    def _handle_minor_shift(self, event) -> List[str]:
        """3.0: Generate a trend-aware TownCryer rumor."""
        if self._crier:
            # Build a synthetic CivicEvent for the crier
            rumor = self._crier.narrate_trend_event(event)
            if rumor:
                return [f"[dim italic]Rumor: {rumor}[/]"]
        return []

    def _handle_notable_trend(self, event) -> List[str]:
        """7.0: Stronger broadcast + temporary GRAPES modifier."""
        messages = []
        if self._crier:
            broadcast = self._crier.narrate_trend_event(event)
            if broadcast:
                messages.append(f"[bold]Town Crier: {broadcast}[/]")

        # Apply temporary GRAPES modifier
        if self._grapes and self._ledger:
            category = event["category"]
            modifier = _trend_to_grapes_modifier(category, event["total_weight"])
            if modifier:
                self._ledger.mutate(
                    category=modifier["grapes_category"],
                    index=0,
                    field=modifier["field"],
                    value=modifier["value"],
                )
                self._ledger.record_historical_event(
                    event_type="MUTATION",
                    summary=modifier["narrative"],
                    category=category,
                )
                messages.append(f"[cyan]The world shifts: {modifier['narrative']}[/]")
        return messages

    def _handle_major_shift(self, event) -> List[str]:
        """12.0: Permanent GRAPES mutation + ANCHOR shard."""
        messages = self._handle_notable_trend(event)  # Includes mutation

        # Emit ANCHOR shard
        if self._engine and hasattr(self._engine, '_add_shard'):
            self._engine._add_shard(
                f"Major shift in {event['category']} at {event['location']}: "
                f"{event['entry_count']} actions accumulated.",
                "ANCHOR", source="momentum"
            )

        # Broadcast for NPC memory
        if self._broadcast:
            self._broadcast.broadcast("HIGH_IMPACT_DECISION", {
                "_event_type": "HIGH_IMPACT_DECISION",
                "event_tag": f"momentum_{event['category']}_major",
                "category": event["category"],
                "summary": f"Major {event['category']} shift at {event['location']}",
            })
        return messages

    def _handle_tipping_point(self, event) -> List[str]:
        """20.0: All of the above + cascade notification."""
        messages = self._handle_major_shift(event)
        cascade = event.get("cascade")
        if cascade:
            messages.append(
                f"[bold yellow]Cascade: {event['category']} momentum spills into "
                f"{cascade['category']}![/]"
            )
        return messages
```

#### C2: Momentum polarity — positive and negative weight

The momentum ledger currently records all events with positive weight (action counts). To support both positive and negative world trends, events carry a **polarity** that determines mutation direction.

**Positive-polarity events** (constructive actions):
- `kill` (enemy cleared), `room_cleared`, `ally_saved`, `zone_breakthrough`, `loot` (treasure found)
- Player buying from merchants, completing quests, healing allies

**Negative-polarity events** (destructive or loss events):
- `party_death`, `companion_fell`, `doom_threshold`, `near_death` (repeated)
- Player fleeing, buildings burning, quest failure, NPC death

**Decay-to-negative:** When a category has had no activity for a sustained period while other categories accumulate, the stale category decays below zero. This represents neglect — the security of an area erodes when no one patrols it, the economy withers when no one trades.

```python
# In MomentumLedger, event recording now carries polarity:
NEGATIVE_EVENTS = frozenset({
    "party_death", "companion_fell", "doom_threshold",
    "near_death",  # Negative only when repeated (3+ in one session)
})

def record_from_event(self, event_type, location, turn, tier=1):
    """Record with automatic polarity detection."""
    polarity = -1.0 if event_type in NEGATIVE_EVENTS else 1.0
    weight = self._weight_for_event(event_type, tier) * polarity
    return self.record(category, location, weight, turn)
```

The `total_weight` in each MomentumBin can now be negative. `_trend_to_grapes_modifier()` uses the sign to determine which mutation to apply.

#### C2a: GRAPES mutation mapping

```python
# Maps momentum categories to concrete GRAPES mutations
TREND_MUTATIONS = {
    "security": {
        "grapes_category": "social",
        "field_positive": ("prohibition", "Vigilante justice is tolerated"),
        "field_negative": ("prohibition", "Speaking of the lost patrols is forbidden"),
        "narrative_positive": "The streets feel safer. Guards walk taller.",
        "narrative_negative": "Fear grips the ward. Doors bolt at sundown.",
    },
    "economics": {
        "grapes_category": "economics",
        "field_positive": ("abundance", "rising"),
        "field_negative": ("abundance", "scarce"),
        "narrative_positive": "New merchants arrive. The market swells.",
        "narrative_negative": "Shops shutter. Coin grows scarce.",
    },
    "politics": {
        "grapes_category": "politics",
        "field_positive": ("agenda", "Reform movement gains traction"),
        "field_negative": ("agenda", "Power consolidates in fewer hands"),
        "narrative_positive": "The council listens to new voices.",
        "narrative_negative": "Edicts come down without debate.",
    },
    "religion": {
        "grapes_category": "religion",
        "field_positive": ("ritual", "Public ceremonies resume"),
        "field_negative": ("heresy", "Whispered prayers to forgotten gods"),
        "narrative_positive": "Temple bells ring for the first time in months.",
        "narrative_negative": "The faithful grow restless. Strange symbols appear.",
    },
    "geography": {
        "grapes_category": "geography",
        "field_positive": ("feature", "New paths cleared through the wilds"),
        "field_negative": ("feature", "Roads crumble, the wilds reclaim"),
        "narrative_positive": "Scouts report safe passage to the north.",
        "narrative_negative": "The frontier contracts. The wild is winning.",
    },
    "social": {
        "grapes_category": "social",
        "field_positive": ("punishment", "Community mediation replaces harsh law"),
        "field_negative": ("punishment", "Public shaming escalates"),
        "narrative_positive": "Neighbors speak again. Trust rebuilds.",
        "narrative_negative": "Suspicion poisons every conversation.",
    },
}

def _trend_to_grapes_modifier(category: str, weight: float) -> Optional[dict]:
    """Convert a momentum category + weight into a GRAPES mutation."""
    mapping = TREND_MUTATIONS.get(category)
    if not mapping:
        return None
    positive = weight > 0
    field_key = "field_positive" if positive else "field_negative"
    narr_key = "narrative_positive" if positive else "narrative_negative"
    field, value = mapping[field_key]
    return {
        "grapes_category": mapping["grapes_category"],
        "field": field,
        "value": value,
        "narrative": mapping[narr_key],
    }
```

#### C3: CrierVoice trend narration

Add `narrate_trend_event()` to existing `CrierVoice` class:

```python
def narrate_trend_event(self, momentum_event: dict) -> str:
    """Generate a narrative rumor about an accumulated trend (WO-V62.0)."""
    category = momentum_event.get("category", "")
    location = momentum_event.get("location", "unknown")
    weight = momentum_event.get("total_weight", 0)
    count = momentum_event.get("entry_count", 0)
    level = momentum_event.get("name", "minor_shift")

    if self._mimir:
        prompt = (
            f"Write a 1-2 sentence in-world rumor about a {category} "
            f"trend in {location}. Players performed {count} related actions. "
            f"This is a {level.replace('_', ' ')} — "
            f"{'a whisper' if level == 'minor_shift' else 'common knowledge' if level == 'notable_trend' else 'undeniable truth'}. "
            f"Describe the societal shift, not individual actions."
        )
        if self._grapes_profile:
            # Inject relevant GRAPES context
            grapes_cat = TREND_MUTATIONS.get(category, {}).get("grapes_category", category)
            grapes_data = self._grapes_profile.get(grapes_cat, [])
            if grapes_data:
                prompt += f" World context: {str(grapes_data)[:200]}"
        try:
            result = self._mimir(prompt, "")
            if result and len(result) > 10:
                return result.strip()
        except Exception:
            pass

    # Fallback: use TREND_MUTATIONS narrative
    mapping = TREND_MUTATIONS.get(category, {})
    positive = weight > 0
    narr_key = "narrative_positive" if positive else "narrative_negative"
    return mapping.get(narr_key, f"Something shifts in the {category} of {location}.")
```

#### C4: Wire into game loops

**play_burnwillow.py** — In `GameState.log_event()`, after momentum recording:

```python
def log_event(self, event_type: str, **kwargs):
    self.session_log.append({"type": event_type, "turn": self.turn_number, **kwargs})
    if self.momentum_ledger:
        location = self.current_location_id or "burnwillow_depths"
        tier = kwargs.get("tier", 1)
        threshold_events = self.momentum_ledger.record_from_event(
            event_type, location, turn=self.turn_number, tier=tier,
        )
        # WO-V62.0: Handle threshold crossings
        if threshold_events and self._momentum_handler:
            messages = self._momentum_handler.handle(threshold_events)
            for msg in messages:
                self.add_log(msg)
```

Add `_momentum_handler` to GameState.__init__ and wire in `init_game()`:

```python
from codex.core.services.momentum_handler import MomentumThresholdHandler

# In init_game(), after momentum_ledger creation:
state._momentum_handler = MomentumThresholdHandler(
    world_ledger=world_ledger,       # From WorldLedger if available
    crier=crier_voice,               # CrierVoice instance
    grapes_profile=grapes_dict,      # From world config if available
    broadcast_manager=state.broadcast_manager,
    engine=state.engine,
)
```

**play_universal.py** — Same pattern in `_run_dungeon_loop()`.

**bridge.py** — In `_log_event()`, threshold events are already recorded in the ledger. The handler needs to be attached:

```python
def set_momentum_handler(self, handler):
    self._momentum_handler = handler
```

#### C5: WorldLedger initialization and persistence

**play_burnwillow.py** — Create WorldLedger at game init:

```python
from codex.core.world.world_ledger import WorldLedger

# In init_game():
state.world_ledger = WorldLedger(universe_id="burnwillow")
# If loading from save, restore from save data
if save_data and save_data.get("world_ledger"):
    state.world_ledger = WorldLedger.from_dict(save_data["world_ledger"])
```

Add to save format:
```python
save_data["world_ledger"] = state.world_ledger.to_dict()
```

#### C6: GRAPES profile persistence in saves

Currently GRAPES is only in WorldState config, not in save files. Add:

```python
# In save:
if hasattr(state, '_grapes_profile') and state._grapes_profile:
    save_data["grapes_profile"] = state._grapes_profile.to_dict()

# In load:
grapes_data = save_data.get("grapes_profile")
if grapes_data:
    state._grapes_profile = GrapesProfile.from_dict(grapes_data)
```

This means GRAPES mutations persist across sessions — the world remembers.

### Files Created

| File | Purpose |
|---|---|
| `codex/core/services/momentum_handler.py` | MomentumThresholdHandler, TREND_MUTATIONS, mutation mapping |

### Files Modified

| File | Changes |
|---|---|
| `codex/core/services/town_crier.py` | `CrierVoice.narrate_trend_event()` method |
| `play_burnwillow.py` | WorldLedger init, momentum handler wiring, GRAPES in save/load |
| `play_universal.py` | Same momentum handler wiring |
| `codex/games/bridge.py` | `set_momentum_handler()`, handler invocation in `_log_event()` |
| Save format | `world_ledger`, `grapes_profile` keys |

### Tests

- `test_momentum_handler.py`:
  - Verify minor_shift generates rumor text
  - Verify notable_trend calls WorldLedger.mutate()
  - Verify major_shift emits ANCHOR shard
  - Verify tipping_point includes cascade message
  - Verify handler works with None dependencies (graceful degradation)
  - Verify GRAPES mutation persists in save/load roundtrip
  - Verify CrierVoice.narrate_trend_event() produces non-empty string
  - Verify TREND_MUTATIONS covers all momentum categories
  - Verify negative events (party_death, companion_fell) produce negative weight
  - Verify positive events (kill, ally_saved) produce positive weight
  - Verify negative momentum triggers negative GRAPES mutations ("Fear grips the ward...")
  - Verify decay-to-negative fires for neglected categories
  - Verify Willow Wood GRAPES bindings read category health correctly

---

## Track D: Universal Session Framing for All Game Systems

### Problem

Session architecture (Track A) is designed for Burnwillow but every game system needs the same one-shot / expedition / campaign / freeform structure. DnD5e, STC, FITD, Crown — all should support session types with system-appropriate behavior. FITD one-shots need a defined model. Crown shouldn't be dismissed as "N/A" for extended play.

### Implementation

#### D1: Session type in play_universal.py

The session type selection from Track A applies to all systems routed through `play_universal.py`:

```python
# In main() or _run_dungeon_loop()/_run_fitd_loop():
session_type = _prompt_session_type(con, system_id)
session = SessionFrame(
    session_type=session_type,
    session_number=_get_next_session_number(campaign_id),
    ...
)
```

The session type menu adapts its labels per system (see D2).

#### D2: Per-system session behaviors

| System | One-Shot | Expedition | Campaign | Freeform |
|---|---|---|---|---|
| **Burnwillow** | Quick Delve (1 dungeon, no world state) | Willow Wood → dungeon → return (turn budget) | Module zones, full persistence | Rumor board + momentum + GRAPES |
| **DnD5e** | Module one-shot | Module chapter (turn budget) | Module chapters, FR wiki lore | Rumor board + momentum + FR wiki |
| **STC** | Module one-shot | Module chapter (turn budget) | Module chapters, Cosmere lore | Rumor board + momentum |
| **BitD/SaV/BoB** | CBR+PNK-style single score (see D3) | Score + full downtime | Score chain + faction clocks | Player-directed scores from faction state |
| **CBR+PNK** | Single run (the default — CBR+PNK IS the one-shot) | Extended run + secondary objectives | Grid chain, ICE escalation | ICE sandbox |
| **Candela** | Single assignment | Assignment + investigation phase | Assignment chain + bleed | Open investigation |
| **Crown** | Full 7-day arc (self-contained) | N/A | Multi-arc (persistent NPC relationships carry over between arcs) | Extended court (7-day timer removed, open-ended court exploration) |

#### D3: FITD one-shot — the CBR+PNK model

CBR+PNK is the definitive FITD one-shot format. All FITD one-shots should follow its structure:

**CBR+PNK one-shot structure:**
1. **Character generation** — fast, template-driven. No backstory needed.
2. **Briefing** — the score is presented. One objective, clear stakes.
3. **The Run** — linear scene progression toward the objective. No downtime. No free play. Tension ramps.
4. **Resolution** — success or failure. The story ends.

**Adapted for other FITD systems:**

| System | One-Shot Template |
|---|---|
| **BitD** | A single score. Pre-generated crew sheet. Skip engagement roll (start in media res). No downtime — the score IS the session. Entanglements happen in narration, not mechanically. |
| **SaV** | A single job. Ship is pre-configured. One planetary scene. Skip the planning phase — the job goes wrong immediately. |
| **BoB** | A single mission. Pre-built squad. No campaign map advancement. The mission outcome is the ending. |
| **Candela** | A single assignment. Pre-generated circle. One illumination key. No between-assignment phase. |

**Implementation:**

```python
# In _run_fitd_loop(), when session_type == "one_shot":
if session.session_type == "one_shot":
    # Skip downtime entirely
    # Skip free play
    # Skip engagement roll — start in media res
    # Generate a score/mission/assignment based on system
    score = _generate_one_shot_score(engine, system_id)
    con.print(Panel(score["briefing"], title="The Job", border_style="red"))
    # Run scenes linearly until resolution
    # At resolution: offer character export (Track A8)
```

#### D4: Crown extended play modes

Crown is not just a 7-day one-shot. Extended modes:

**Crown Campaign (multi-arc):**
- Each arc is a standard 7-day Crown game
- Between arcs: NPC relationship scores persist. Sway resets to starting position. Day resets to 1.
- NPCs remember prior arcs — `_add_shard("ANCHOR", ...)` events from prior arcs are accessible to Mimir for NPC dialogue
- New arc introduces new political crisis but the court remembers you
- Session close saves `arc_number`, `persistent_npcs: dict[str, float]` (name → relationship score)

**Crown Freeform (extended court):**
- The 7-day timer is removed. Days advance only when the player chooses to "retire for the evening"
- The court operates as a sandbox — talk to NPCs, attend events, build alliances, uncover secrets
- Sway still matters but there's no deadline pressure
- CivicPulse fires political events on each "day advance" — the court is alive
- Momentum tracks the player's political lean (reformist vs traditionalist vs isolationist)

```python
# In Crown engine, session type modifies behavior:
if session_type == "freeform":
    self.max_days = None  # No day limit
    self.day_advance_mode = "manual"  # Player-triggered
elif session_type == "campaign":
    self.arc_number = save_data.get("arc_number", 1)
    self._restore_persistent_npcs(save_data.get("persistent_npcs", {}))
```

#### D5: FITD campaign session framing

FITD games have a natural session structure: **Score → Downtime → Free Play → Score**. Map this to session types:

- **One-shot**: Score only (CBR+PNK model, see D3)
- **Expedition**: Score + full downtime (healing, crafting, heat reduction, long-term projects)
- **Campaign**: Score → downtime → free play cycle. Between sessions: faction clocks advance, GRAPES politics mutate
- **Freeform**: Player chooses next score from faction clock state. Free play is the primary mode.

The `CivicPulse` system already has FITD-relevant events. Wire faction clocks from GRAPES politics:

```python
# In FITD session close (campaign/freeform):
if session.session_type in ("campaign", "freeform"):
    # Advance faction clocks
    if hasattr(engine, 'faction_clocks'):
        for clock in engine.faction_clocks.values():
            clock.tick(1)
            if clock.is_full():
                # Faction event fires — major world change
                event = _resolve_faction_event(clock)
                con.print(f"[bold red]{event['narrative']}[/]")
                if momentum_handler:
                    momentum_handler._handle_tipping_point({
                        "category": "politics",
                        "location": clock.faction_name,
                        "level": 20.0,
                    })
```

#### D6: Expedition timer for spatial systems

For DnD5e, STC, and Burnwillow (spatial dungeon systems), expeditions have a soft time limit expressed through narrative pressure, not a visible counter:

**Narrative supply system:**

```python
EXPEDITION_SUPPLY_STAGES = [
    (0.0, None),                          # 0-50%: no pressure
    (0.5, "[dim]Your pack feels lighter than it should.[/]"),
    (0.7, "[yellow]Your water skin is nearly empty. The jerky is gone.[/]"),
    (0.8, "[bold yellow]Supplies run low. You should consider returning.[/]"),
    (0.9, "[bold red]Your torch gutters. Your stomach cramps. Time is running out.[/]"),
    (1.0, "[bold red]Your rations are exhausted. You must return or face consequences.[/]"),
]

class ExpeditionTimer:
    def __init__(self, turn_budget: int = 50):
        self.budget = turn_budget
        self.elapsed = 0
        self._last_stage = 0

    def tick(self) -> Optional[str]:
        """Advance one turn. Returns supply narration if a new stage is reached."""
        self.elapsed += 1
        ratio = self.elapsed / self.budget
        for threshold, message in reversed(EXPEDITION_SUPPLY_STAGES):
            if ratio >= threshold and threshold > self._last_stage:
                self._last_stage = threshold
                return message
        return None

    @property
    def exhausted(self) -> bool:
        return self.elapsed >= self.budget
```

- **One-shots**: No timer (play until done or dead)
- **Expeditions**: Timer is enforced. At 100%, the party takes increasing damage per turn (starvation/exposure) — not an instant game-over, but escalating pressure.
- **Campaign/Freeform**: Timer is advisory only. Messages fire but no mechanical penalty.

#### D7: Character import across systems

Track A8 defines character export/import within the same system. For cross-system play (e.g., a Burnwillow character entering a D&D 5e module), the character export includes a `_portable_stats` block:

```python
"_portable_stats": {
    "name": "Kael",
    "level": 3,
    "hp_ratio": 0.85,       # Percentage, not absolute
    "combat_style": "melee",  # melee/ranged/magic/support
    "notable_items": ["Rusted Shortsword", "Padded Jerkin"],
}
```

The importing engine uses `_portable_stats` to create a **system-native equivalent** character. A level 3 melee Burnwillow character becomes a level 3 Fighter in D&D 5e, or a level 3 Cutter in BitD. This is lossy by design — the feel transfers, not the exact mechanics.

Cross-system import is offered only for systems that share a `combat_style` mapping. The `COMPANION_CLASS_MAP` from WO-V61.0 already provides this mapping for 9 systems × 4 archetypes.

### Files Modified

| File | Changes |
|---|---|
| `play_universal.py` | Session type menu (system-aware labels), per-system framing, FITD one-shot flow, expedition timer, faction clock wiring |
| `play_burnwillow.py` | Expedition timer integration in dungeon loop |
| `codex/core/session_frame.py` | System-specific session behaviors, ExpeditionTimer, one-shot score generation |
| `codex/core/character_export.py` | `_portable_stats` generation, cross-system import mapping |
| `codex/games/crown/engine.py` | `max_days`, `day_advance_mode`, `arc_number`, persistent NPC wiring |

### Tests

- `test_universal_session.py`:
  - Verify session type selection works for all system_ids
  - Verify FITD one-shot skips downtime/free play
  - Verify FITD campaign advances faction clocks on session close
  - Verify expedition timer fires warnings at correct thresholds
  - Verify expedition timer enforces at 100% for expedition type only
  - Verify Crown campaign persists NPC relationships between arcs
  - Verify Crown freeform removes day limit
  - Verify character export includes _portable_stats
  - Verify cross-system import creates system-native character
  - Verify system mismatch without mapping is rejected

---

## Execution Order

1. **Track C** — GRAPES Mutation Wiring (closes the feedback loop, highest architectural impact)
2. **Track A** — Session Architecture + Character Export (frames all play, enables one-shot vs campaign, character portability)
3. **Track B** — Willow Wood (Burnwillow-specific, depends on session framing + GRAPES bindings from Track C)
4. **Track D** — Universal Session Framing (extends Track A to all systems, FITD one-shot model, Crown extended modes, expedition timer)

Tests throughout. Each track must pass full suite before moving to next.

---

## Verification

### Track C — GRAPES Mutation
1. Start a Burnwillow freeform session. Kill 12 enemies in one area. Verify TownCryer announces a security trend. Verify GRAPES social category reflects the shift.
2. Lose 3 party members in one session. Verify negative momentum accumulates in security. Verify GRAPES mutation is negative ("Fear grips the ward...").
3. Save and reload — verify mutation persists. Start new session — verify opening hook references the shift.
4. Leave an area alone for many turns while acting elsewhere. Verify decay takes the neglected category below zero.

### Track A — Session Architecture
1. Start a new game. Select "Quick Delve." Complete dungeon. Verify no world state saved. Verify character export is offered.
2. Export character. Start new game. Select "Import existing character." Verify character loads with stats/gear, no quest progress.
3. Start "Campaign." Complete session 1. Verify epilogue shows ("Meanwhile..."). Verify session summary stored.
4. Load campaign. Verify session_number is 2. Verify opening hook references session 1 summary.

### Track B — Willow Wood
1. Start Burnwillow. Leave Emberhome. Arrive in Willow Wood. Verify landmark rooms present.
2. Move toward Root Stair. Verify 3-5 procedural rooms on the path.
3. Encounter a territorial boar. Verify 4 approach options (combat/social/exploration/narrative).
4. Choose narrative approach. Verify lore fragment is logged.
5. Investigate a ruin room. Verify secret discovery (lore inscription).
6. Return to Emberhome. Re-enter Willow Wood in same session. Verify same procedural layout.
7. Start new session. Verify different procedural rooms but same landmarks.
8. Accumulate negative economics momentum. Visit Merchant's Crossing. Verify "Shops shutter" description variant.
9. Visit The Whisper Hollow after 3+ sessions. Verify echo_memory flashback triggers.

### Track D — Universal Session Framing
1. Start BitD one-shot. Verify score is presented immediately (no engagement roll, no downtime). Complete score. Verify character export offered.
2. Start BitD campaign. Complete score + downtime. Close session. Verify faction clocks advance.
3. Start DnD5e expedition. Verify supply narration fires at 50%, 70%, 80%. At 100%, verify starvation pressure.
4. Start Crown campaign. Complete first arc. Start second arc. Verify NPC relationships carry over.
5. Start Crown freeform. Verify no 7-day limit. Advance day manually. Verify CivicPulse fires events.
6. Export a Burnwillow character. Import into DnD5e. Verify system-native equivalent created.

### Full Regression
- `python -m pytest tests/ -x` — all tests pass, zero regressions.

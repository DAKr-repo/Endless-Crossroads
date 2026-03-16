# WORK ORDER #038: ASHBURN MODULE & DEEP WORLD BUILDER
## COMPREHENSIVE SYSTEM BLUEPRINT

**Blueprint Version:** 1.0
**Date:** 2026-02-03
**Architect:** @codex-architect
**Target Implementation:** @Mechanic

**Status:** READY FOR IMPLEMENTATION
**Risk Assessment:** MEDIUM — New subclass with state extensions and menu integration
**Thermal Impact:** LOW — Text-based UI, minimal LLM calls

---

## EXECUTIVE SUMMARY

This blueprint defines two major feature additions to the C.O.D.E.X. narrative engine:

1. **AshburnHeirEngine** — A subclass of `CrownAndCrewEngine` that adds a corruption/legacy system with NPC relationships and betrayal mechanics
2. **DeepWorldEngine** — Upgrades to `WorldEngine` that add structured world-building flows (G.R.A.P.E.S.) and text import

Both features integrate into the existing `codex_agent_main.py` orchestrator via menu additions.

---

## AFFECTED FILES

### Files to Create
- `/home/pi/Projects/claude_sandbox/Codex/ashburn_crew_module.py` — New module containing `AshburnHeirEngine` class

### Files to Modify
- `/home/pi/Projects/claude_sandbox/Codex/codex_world_engine.py` — Add G.R.A.P.E.S. wizard and text import flow
- `/home/pi/Projects/claude_sandbox/Codex/codex_agent_main.py` — Add Ashburn menu option and integration logic

### Files Referenced (Read-Only)
- `/home/pi/Projects/claude_sandbox/Codex/codex_crown_module.py` — Base class for Ashburn
- `/home/pi/Projects/claude_sandbox/Codex/codex_cortex.py` — Thermal monitoring (no changes)
- `/home/pi/Projects/claude_sandbox/Codex/volo_manifold_guard.py` — State consistency (no changes)

---

## DEPENDENCY GRAPH

```
ashburn_crew_module.py
  └── INHERITS FROM → codex_crown_module.py (CrownAndCrewEngine)
        └── USES → codex_world_engine.py (WorldState, WorldEngine)
              └── USES → codex_architect.py (LLM generation)

codex_agent_main.py
  └── IMPORTS → ashburn_crew_module.py (AshburnHeirEngine)
  └── IMPORTS → codex_world_engine.py (WorldEngine)
  └── IMPORTS → codex_crown_module.py (CrownAndCrewEngine)
```

**Import Order:**
```python
# In ashburn_crew_module.py
from codex_crown_module import CrownAndCrewEngine, SWAY_TIERS, TAGS

# In codex_agent_main.py (add to existing imports)
from ashburn_crew_module import AshburnHeirEngine
```

---

# SECTION A: ASHBURN HEIR ENGINE BLUEPRINT

## A.1 Overview

**File:** `ashburn_crew_module.py`
**Class:** `AshburnHeirEngine`
**Inherits From:** `CrownAndCrewEngine` (codex_crown_module.py:196)

**Purpose:**
A narrative extension of Crown & Crew that adds:
- **Legacy Corruption** — A 0-5 meter that tracks moral decay
- **NPC Leader System** — 4 archetypes with abilities and risks
- **Legacy Checks** — Roll-based events that offer moral choices (Lie vs. Truth)
- **Betrayal Nullification** — Players who betray their faction lose political gravity weight AND gain corruption
- **Immediate Loss Condition** — Corruption ≥ 5 triggers game-over

**Setting Context:**
"Ashburn High" — A gothic boarding school where the player is the heir to a disgraced noble family. The "Crown" represents institutional authority (faculty, donors). The "Crew" represents student resistance factions. The player navigates social politics while managing their family's legacy corruption.

---

## A.2 Inheritance Architecture

### A.2.1 Methods Inherited As-Is

The following parent methods are used without override:

| Method | Source Line | Purpose |
|--------|-------------|---------|
| `get_status()` | codex_crown_module.py:301 | Returns formatted status string |
| `get_tier()` | codex_crown_module.py:309 | Returns current Sway Tier data |
| `get_alignment()` | codex_crown_module.py:313 | Determines CROWN/CREW/DRIFTER |
| `get_alignment_display()` | codex_crown_module.py:322 | Returns display name with world terms |
| `get_sway_color()` | codex_crown_module.py:332 | Discord embed color (hex) |
| `get_sway_visual()` | codex_crown_module.py:344 | ASCII sway bar (👑═══◆═══🏴) |
| `get_dominant_tag()` | codex_crown_module.py:357 | Returns tag with highest DNA |
| `get_prompt()` | codex_crown_module.py:410 | Gets unique Crown/Crew prompt |
| `get_world_prompt()` | codex_crown_module.py:425 | Gets unique World prompt |
| `get_campfire_prompt()` | codex_crown_module.py:429 | Gets unique Campfire prompt |
| `get_secret_witness()` | codex_crown_module.py:436 | Day 3 special event |
| `get_summary()` | codex_crown_module.py:582 | Journey log text |
| `check_drifter_tax()` | codex_crown_module.py:549 | Double Draw penalty |
| `is_breach_day()` | codex_crown_module.py:553 | Day 3 check |
| `_get_unique_prompt()` | codex_crown_module.py:285 | Prompt pool rotation logic |

### A.2.2 Methods Overridden

| Method | Reason for Override |
|--------|---------------------|
| `declare_allegiance()` | Add Legacy Check trigger logic |
| `get_vote_power()` | Implement Betrayal Nullification |
| `end_day()` | Add corruption check, trigger immediate loss |
| `generate_legacy_report()` | Include corruption meter and NPC relationships |

### A.2.3 New Methods

| Method | Purpose |
|--------|---------|
| `generate_legacy_check()` | Roll d6 on Crown cards, trigger Lie vs. Truth choice |
| `check_betrayal()` | Detect if corruption ≥ 5, trigger immediate loss |
| `process_legacy_choice()` | Handle player's Lie/Truth decision, adjust corruption |
| `get_heir_status()` | Return Rich-formatted panel with heir name, corruption, NPCs |
| `add_corruption()` | Increment corruption and check for loss condition |
| `get_npc_ability()` | Return ability text for a given NPC |
| `get_npc_risk()` | Return risk text for a given NPC |

---

## A.3 New State Variables

**Data Model Extension:**

```python
@dataclass
class AshburnHeirEngine(CrownAndCrewEngine):
    """
    Ashburn High narrative variant with corruption and NPC systems.
    """

    # New Ashburn-specific state
    legacy_corruption: int = 0  # Range: 0-5 (5 = immediate loss)
    heir_name: str = "The Heir"  # Player's character name
    npcs: dict[str, dict] = field(default_factory=dict)  # Leader archetypes
    betrayal_triggered: bool = False  # Track if betrayal nullification is active

    # All parent fields inherited:
    # day, sway, patron, leader, history, dna, world_state, terms, etc.
```

**Field Specifications:**

| Field | Type | Default | Range/Constraints | Purpose |
|-------|------|---------|-------------------|---------|
| `legacy_corruption` | int | 0 | 0-5 (≥5 = loss) | Moral decay meter |
| `heir_name` | str | "The Heir" | Any non-empty string | Player character name |
| `npcs` | dict | {} | See NPC schema below | Leader relationship data |
| `betrayal_triggered` | bool | False | True/False | Tracks political gravity nullification state |

---

## A.4 NPC Leader System

### A.4.1 NPC Data Schema

```python
# In AshburnHeirEngine.__post_init__()
self.npcs = {
    "Lydia": {
        "name": "Lydia Ashburn",
        "archetype": "The Loyalist",
        "ability": "Shield Protocol — Lydia can absorb one corruption point for you once per campaign.",
        "risk": "If betrayed, Lydia turns to the Crown and becomes a recurring antagonist.",
        "status": "neutral",  # neutral | allied | betrayed
        "ability_used": False
    },
    "Jax": {
        "name": "Jax Thorne",
        "archetype": "The Rebel",
        "ability": "Wildcard Draw — Once per campaign, Jax can force a re-roll on a Legacy Check.",
        "risk": "If betrayed, Jax leaks your secrets to the student body (gain +1 corruption).",
        "status": "neutral",
        "ability_used": False
    },
    "Julian": {
        "name": "Julian Graves",
        "archetype": "The Scholar",
        "ability": "Arcane Insight — Julian can reveal the outcome of a choice before you commit.",
        "risk": "If betrayed, Julian publishes your family history in the school journal.",
        "status": "neutral",
        "ability_used": False
    },
    "Rowan": {
        "name": "Rowan Vex",
        "archetype": "The Enforcer",
        "ability": "Intimidation — Rowan can suppress one Crown dilemma entirely.",
        "risk": "If betrayed, Rowan physically confronts you (automatic corruption +2).",
        "status": "neutral",
        "ability_used": False
    }
}
```

### A.4.2 NPC Interaction Flow

**When to Use:**
- NPCs are introduced during the narrative (not mechanically enforced in base game loop)
- The @Designer will write prompts that reference NPCs
- The Ashburn variant supports Discord/Terminal prompts like:
  - "Do you ask Lydia for help?" → Trigger Shield Protocol
  - "Do you trust Jax with this information?" → Ally or betray

**Implementation Hooks:**
```python
def get_npc_ability(self, npc_name: str) -> str:
    """Return the ability description for display."""
    return self.npcs.get(npc_name, {}).get("ability", "Unknown NPC")

def get_npc_risk(self, npc_name: str) -> str:
    """Return the risk description for display."""
    return self.npcs.get(npc_name, {}).get("risk", "Unknown NPC")

def use_npc_ability(self, npc_name: str) -> dict:
    """
    Trigger an NPC's ability.

    Returns:
        {
            "success": bool,
            "message": str,
            "effect": str  # e.g., "corruption_reduced"
        }
    """
    # Implementation details left to @Mechanic
    pass
```

---

## A.5 Legacy Check System

### A.5.1 Trigger Condition

**When:**
- After `declare_allegiance("crown", ...)` is called
- Roll 1d6
- On 5-6: Trigger Legacy Check

**Frequency:**
- Only on Crown allegiance declarations
- Not every Crown choice, but probabilistic (33% chance)

### A.5.2 Legacy Check Flow

```
┌─────────────────────────────────────┐
│ Player declares allegiance: CROWN   │
└──────────┬──────────────────────────┘
           │
           ▼
      Roll 1d6
           │
     ┌─────┴─────┐
     │   1-4     │   5-6
     ▼           ▼
  Continue    Legacy Check
  Normal      Triggered
  Flow            │
                  ▼
         ┌────────────────┐
         │ Present Choice │
         │  LIE vs TRUTH  │
         └────┬───────┬───┘
              │       │
         [LIE]│       │[TRUTH]
              │       │
              ▼       ▼
         Sway +1   No Sway
         Corruption +1  Corruption +0
              │       │
              └───┬───┘
                  ▼
           Continue Game
```

### A.5.3 Method Signature

```python
def generate_legacy_check(self) -> dict:
    """
    Roll for Legacy Check. On 5-6, return choice data.

    Returns:
        {
            "triggered": bool,
            "roll": int,  # 1-6
            "prompt": str,  # The moral dilemma text
            "lie_option": str,
            "truth_option": str
        }
    """
    roll = random.randint(1, 6)
    if roll <= 4:
        return {"triggered": False, "roll": roll}

    # Select a legacy prompt (new pool to be defined)
    prompt = self._get_legacy_prompt()

    return {
        "triggered": True,
        "roll": roll,
        "prompt": prompt,
        "lie_option": "Lie — Protect your legacy (Sway +1, Corruption +1)",
        "truth_option": "Truth — Face the consequences (No Sway, No Corruption)"
    }

def process_legacy_choice(self, choice: str) -> str:
    """
    Process the player's Lie/Truth choice.

    Args:
        choice: "lie" | "truth"

    Returns:
        Narrative feedback string
    """
    if choice.lower() == "lie":
        self.sway += 1  # Additional Crown sway
        self.add_corruption(1)
        return "You buried the truth. Your legacy darkens. (Corruption +1, Sway +1)"
    else:
        return "You spoke the truth. The weight remains, but your conscience is clear."
```

---

## A.6 Betrayal Nullification Mechanic

**CRITICAL DESIGN NOTE: This is INTENTIONAL, not a bug.**

### A.6.1 Definition

**Betrayal Nullification** is a cross-cutting mechanic that affects Political Gravity:

- **Condition:** Player has high sway (|sway| ≥ 2) in one faction, then votes for the OPPOSITE faction in a council vote
- **Effect:** Player's political gravity weight is nullified (reverts to 1x instead of 4x or 8x)
- **Thematic Justification:** "Betrayal costs political capital. Your faction no longer trusts your voice."

### A.6.2 Implementation

**Override in `AshburnHeirEngine.get_vote_power()`:**

```python
def get_vote_power(self) -> int:
    """
    Get vote weight with Betrayal Nullification.

    Overrides parent to implement betrayal detection.

    Political Gravity:
        |sway| 0 → 1 vote power  (Drifter)
        |sway| 1 → 2 vote power  (Leaning)
        |sway| 2 → 4 vote power  (Trusted)
        |sway| 3 → 8 vote power  (Loyal)

    Betrayal Nullification:
        If self.betrayal_triggered == True:
            Weight reverts to 1 regardless of sway.

    Returns:
        int: Vote power multiplier
    """
    if self.betrayal_triggered:
        return 1  # Nullified — betrayal costs political capital

    # Normal gravity
    abs_sway = abs(self.sway)
    return VOTE_POWER.get(abs_sway, 1)
```

**Betrayal Detection Logic:**

```python
def resolve_vote(self, votes: dict[str, int], player_vote: str) -> dict:
    """
    Extended vote resolution with betrayal detection.

    Args:
        votes: {"crown": count, "crew": count}
        player_vote: "crown" | "crew" — the side the player voted for

    Returns:
        Same structure as parent resolve_vote, plus "betrayal_detected" flag
    """
    # Detect betrayal BEFORE applying gravity
    player_alignment = self.get_alignment()  # CROWN/CREW/DRIFTER
    abs_sway = abs(self.sway)

    betrayal_detected = False
    if abs_sway >= 2:  # Trusted or Loyal tier
        if player_alignment == "CROWN" and player_vote == "crew":
            betrayal_detected = True
        elif player_alignment == "CREW" and player_vote == "crown":
            betrayal_detected = True

    if betrayal_detected:
        self.betrayal_triggered = True
        self.add_corruption(1)  # Betrayal also corrupts

    # Call parent's resolve_vote (which will use our overridden get_vote_power)
    result = super().resolve_vote(votes)
    result["betrayal_detected"] = betrayal_detected

    return result
```

### A.6.3 Betrayal Recovery

**When does betrayal_triggered reset?**
- Option 1: Permanent for the campaign (harsh)
- Option 2: Resets after 2 consecutive votes in the same faction (redemption arc)
- **RECOMMENDED:** Option 1 for Ashburn's gothic tone

**Design Rationale:**
- Betrayal is a one-way door
- Reflects the "legacy corruption" theme
- Creates meaningful consequence for fence-sitting

---

## A.7 Immediate Loss Condition

### A.7.1 Corruption Threshold

**Rule:** If `legacy_corruption >= 5`, the player immediately loses.

### A.7.2 Implementation

**In `AshburnHeirEngine.check_betrayal()`:**

```python
def check_betrayal(self) -> dict:
    """
    Check if corruption has reached the loss threshold.

    Returns:
        {
            "game_over": bool,
            "corruption": int,
            "message": str
        }
    """
    if self.legacy_corruption >= 5:
        return {
            "game_over": True,
            "corruption": self.legacy_corruption,
            "message": (
                "YOUR LEGACY IS CONSUMED.\n\n"
                f"Corruption: {self.legacy_corruption}/5\n"
                "The weight of your choices has crushed you. "
                "Your family name dies with you. The Ashburn line ends tonight."
            )
        }
    return {
        "game_over": False,
        "corruption": self.legacy_corruption,
        "message": f"Corruption: {self.legacy_corruption}/5 — The darkness grows."
    }

def add_corruption(self, amount: int = 1) -> dict:
    """
    Add corruption and check for immediate loss.

    Args:
        amount: Corruption points to add (default: 1)

    Returns:
        Same structure as check_betrayal()
    """
    self.legacy_corruption += amount
    return self.check_betrayal()
```

### A.7.3 Integration with Game Loop

**When to call:**
- After every corruption-triggering event:
  - Legacy Check (Lie choice)
  - Betrayal detection
  - NPC risk triggers

**Flow:**
```python
# In the game loop (codex_agent_main.py or Discord bot):
if engine.is_ashburn_variant:
    loss_check = engine.check_betrayal()
    if loss_check["game_over"]:
        console.print(Panel(loss_check["message"], border_style="red", title="GAME OVER"))
        return  # Exit game loop
```

---

## A.8 Rich Status Panel

### A.8.1 Method Signature

```python
def get_heir_status(self) -> Panel:
    """
    Generate a Rich Panel showing Ashburn-specific status.

    Returns:
        rich.panel.Panel with:
            - Heir name
            - Corruption meter (visual bar)
            - NPC relationship summary
            - Current sway and alignment
            - Betrayal status
    """
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    # Corruption bar
    corruption_bar = "█" * self.legacy_corruption + "░" * (5 - self.legacy_corruption)
    corruption_color = "green" if self.legacy_corruption < 2 else ("yellow" if self.legacy_corruption < 4 else "red")

    # NPC summary
    npc_lines = []
    for name, data in self.npcs.items():
        status_icon = {
            "neutral": "○",
            "allied": "●",
            "betrayed": "✗"
        }.get(data["status"], "?")
        ability_status = "USED" if data["ability_used"] else "READY"
        npc_lines.append(f"{status_icon} {name} — {data['archetype']} ({ability_status})")

    npc_block = "\n".join(npc_lines) if npc_lines else "[dim]No NPCs active[/dim]"

    # Betrayal warning
    betrayal_warning = ""
    if self.betrayal_triggered:
        betrayal_warning = "\n[bold red]⚠️  POLITICAL CAPITAL NULLIFIED (Betrayal)[/bold red]"

    # Assemble panel
    content = (
        f"[bold gold1]{self.heir_name}[/bold gold1]\n"
        f"[dim]Heir of the Ashburn Line[/dim]\n\n"
        f"[bold]CORRUPTION[/bold]\n"
        f"[{corruption_color}]{corruption_bar}[/] {self.legacy_corruption}/5\n\n"
        f"[bold]SWAY & ALIGNMENT[/bold]\n"
        f"{self.get_sway_visual()}\n"
        f"{self.get_status()}\n"
        f"{betrayal_warning}\n\n"
        f"[bold]NPC RELATIONSHIPS[/bold]\n"
        f"{npc_block}"
    )

    return Panel(
        content,
        title="[bold]⚔️  HEIR STATUS  ⚔️[/bold]",
        border_style="gold1",
        box=box.DOUBLE
    )
```

### A.8.2 Usage in Game Loop

```python
# In codex_agent_main.py or Discord bot:
if isinstance(engine, AshburnHeirEngine):
    console.print(engine.get_heir_status())
else:
    render_vitals(core.cortex)  # Standard vitals
```

---

## A.9 Save/Load Extensions

### A.9.1 Serialization

**Extend parent's save logic:**

```python
def to_dict(self) -> dict:
    """Serialize Ashburn state to dict."""
    parent_data = super().to_dict() if hasattr(super(), 'to_dict') else {}

    ashburn_data = {
        "legacy_corruption": self.legacy_corruption,
        "heir_name": self.heir_name,
        "npcs": self.npcs,
        "betrayal_triggered": self.betrayal_triggered,
        "engine_type": "ashburn"  # Flag for load detection
    }

    return {**parent_data, **ashburn_data}

@classmethod
def from_dict(cls, data: dict) -> "AshburnHeirEngine":
    """Deserialize Ashburn state from dict."""
    # Extract Ashburn fields
    corruption = data.pop("legacy_corruption", 0)
    heir = data.pop("heir_name", "The Heir")
    npcs = data.pop("npcs", {})
    betrayal = data.pop("betrayal_triggered", False)

    # Create instance with parent data
    instance = cls(**data)

    # Restore Ashburn state
    instance.legacy_corruption = corruption
    instance.heir_name = heir
    instance.npcs = npcs
    instance.betrayal_triggered = betrayal

    return instance
```

### A.9.2 Save File Format

**Example JSON:**
```json
{
  "engine_type": "ashburn",
  "day": 3,
  "sway": -1,
  "patron": "The High Inquisitor",
  "leader": "Captain Vane",
  "legacy_corruption": 2,
  "heir_name": "Elara Ashburn",
  "betrayal_triggered": false,
  "npcs": {
    "Lydia": {
      "name": "Lydia Ashburn",
      "archetype": "The Loyalist",
      "status": "allied",
      "ability_used": false
    }
  },
  "history": [...]
}
```

---

## A.10 Legacy Prompt Pool

**New hardcoded pool for Legacy Checks:**

```python
ASHBURN_LEGACY_PROMPTS: list[str] = [
    "A professor asks about your father's research. The truth would ruin him—but also clear your name.",
    "The headmaster offers to expunge your disciplinary record in exchange for informing on the Crew.",
    "Your family's crest is found carved into a crime scene. You know who did it. Do you protect them?",
    "A letter from your imprisoned mother arrives. She asks you to lie under oath to secure her release.",
    "The school board debates expelling you. One board member is blackmailable. Do you use the leverage?",
    "Your younger sibling is caught breaking curfew. Taking the blame would protect them but add to your record.",
    "A scholarship student accuses you of bribery. It's true—but denying it would preserve your standing.",
    "The Crown offers amnesty to your family if you testify against the Crew leader. Do you take the deal?",
]
```

---

## A.11 Testing Requirements for @Playtester

**Test Cases:**

1. **Legacy Check Trigger Rate**
   - Declare Crown allegiance 30 times
   - Verify ~33% trigger rate (10 ± 3 triggers)

2. **Corruption Loss Condition**
   - Manually set `legacy_corruption = 4`
   - Trigger one more corruption event
   - Verify immediate game-over

3. **Betrayal Nullification**
   - Build sway to +2 (Crew Trusted)
   - Vote Crown in a council decision
   - Verify `betrayal_triggered = True`
   - Verify `get_vote_power() == 1`

4. **NPC Ability Usage**
   - Trigger Lydia's Shield Protocol
   - Verify corruption reduced by 1
   - Verify `ability_used = True`
   - Verify cannot use again

5. **Save/Load Integrity**
   - Create Ashburn game at Day 3, Corruption 3
   - Save to JSON
   - Load from JSON
   - Verify all state restored

---

# SECTION B: DEEP WORLD ENGINE BLUEPRINT

## B.1 Overview

**File:** `codex_world_engine.py` (MODIFY EXISTING)
**Target Function:** `run_genesis_wizard()` (line 452)

**Purpose:**
Extend the existing World Genesis Wizard with two new creation modes:
1. **G.R.A.P.E.S. Flow** — Structured 6-question world-building interview
2. **Text Import** — Paste-and-parse for existing setting bibles

---

## B.2 Menu Update

### B.2.1 Current Menu (Reference)

**Location:** `run_genesis_wizard()` — currently shows:
1. Select Base Simulation (D&D 5e, Blades, etc.)
2. Select Tone (Gritty, Heroic, etc.)
3. Name the World
4. LLM Primer Generation

### B.2.2 New Menu Flow

**Insert NEW STEP after "Select Base Simulation" (before Tone selection):**

```
┌──────────────────────────────────────────┐
│  WORLD CREATION METHOD                   │
├──────────────────────────────────────────┤
│  [1] Quick Genesis  (Current flow)       │
│  [2] Detailed Genesis (G.R.A.P.E.S.)     │
│  [3] Import Setting Bible (Text Paste)   │
└──────────────────────────────────────────┘
```

**Implementation Point:**

```python
# In run_genesis_wizard(), after system selection (line 530):

# NEW STEP: Creation Method Selector
console.print()
console.print(Panel(
    "[bold]SELECT WORLD CREATION METHOD[/bold]\n\n"
    "[1] Quick Genesis — Fast, AI-generated\n"
    "[2] Detailed Genesis (G.R.A.P.E.S.) — Structured interview\n"
    "[3] Import Setting Bible — Paste existing lore",
    border_style=SILVER,
    box=box.ROUNDED,
))
console.print()

while True:
    method_choice = await _ainput("[gold1]Select method [1/2/3]:[/] ")
    if method_choice in ("1", "2", "3"):
        break
    console.print("[dim]Enter 1, 2, or 3[/dim]")

# Branch logic:
if method_choice == "1":
    # Continue current flow (Tone → Name → LLM)
    pass
elif method_choice == "2":
    # Run G.R.A.P.E.S. wizard → Skip LLM generation
    grapes_data = await self._run_grapes_wizard()
    # Populate WorldState from grapes_data
    pass
elif method_choice == "3":
    # Run Text Import wizard → Skip LLM generation
    import_data = await self._run_text_import()
    # Parse and populate WorldState
    pass
```

---

## B.3 G.R.A.P.E.S. Detailed Genesis

### B.3.1 Acronym Definition

**G.R.A.P.E.S.** is a historical analysis framework adapted for world-building:

- **G**eography — Terrain, climate, landmarks
- **R**eligion — Faiths, deities, spiritual practices
- **A**chievements — Technology level, inventions, cultural milestones
- **P**olitics — Government type, power structures, factions
- **E**conomics — Trade, currency, resources
- **S**ocial — Class structure, customs, daily life

### B.3.2 Flow Design

**New Method:** `WorldEngine._run_grapes_wizard()`

```python
async def _run_grapes_wizard(self) -> dict:
    """
    Run the G.R.A.P.E.S. structured world-building interview.

    Returns:
        dict with keys: geography, religion, achievements, politics, economics, social
    """
    console.clear()
    console.print(Panel(
        "[bold cyan]G.R.A.P.E.S. DETAILED GENESIS[/bold cyan]\n\n"
        "[dim]A structured interview to build your world systematically.\n"
        "Answer each category in 1-3 sentences.[/dim]",
        box=box.DOUBLE,
        border_style=CYAN
    ))
    console.print()

    grapes_data = {}

    # Define questions
    questions = [
        ("geography", "🌍 GEOGRAPHY", "Describe the terrain, climate, and major landmarks of this world."),
        ("religion", "⛪ RELIGION", "What faiths, deities, or spiritual practices exist? Who worships what?"),
        ("achievements", "🔬 ACHIEVEMENTS", "What is the technology level? Notable inventions? Cultural milestones?"),
        ("politics", "⚖️ POLITICS", "What government type exists? Who holds power? What factions compete?"),
        ("economics", "💰 ECONOMICS", "How does trade work? What is the currency? What resources are valuable?"),
        ("social", "👥 SOCIAL", "Describe class structure, customs, and daily life for common people."),
    ]

    for key, title, prompt_text in questions:
        console.print(f"[bold gold1]{title}[/bold gold1]")
        console.print(f"[dim]{prompt_text}[/dim]")
        console.print()

        response = await _ainput("[green]Your answer:[/green] ")
        grapes_data[key] = response.strip() or "No details provided."
        console.print()

    # Confirmation
    console.print(Panel(
        "\n".join([f"[bold]{k.upper()}:[/bold] {v}" for k, v in grapes_data.items()]),
        title="[bold]G.R.A.P.E.S. SUMMARY[/bold]",
        border_style=EMERALD
    ))
    console.print()

    confirm = await _ainput("[gold1]Accept this world data? [Y/n]:[/] ")
    if confirm.lower() in ("n", "no"):
        return await self._run_grapes_wizard()  # Restart

    return grapes_data
```

### B.3.3 Data Mapping

**How G.R.A.P.E.S. data maps to WorldState:**

| G.R.A.P.E.S. Field | WorldState Field | Notes |
|--------------------|------------------|-------|
| `geography` | `grapes_geography` | NEW field (see B.4.1) |
| `religion` | `grapes_religion` | NEW field |
| `achievements` | `grapes_achievements` | NEW field |
| `politics` | `grapes_politics` | NEW field |
| `economics` | `grapes_economics` | NEW field |
| `social` | `grapes_social` | NEW field |
| ALL (synthesized) | `primer` | Concatenate all 6 into a world primer |

**Synthesis Logic:**

```python
# After collecting grapes_data:
world.primer = (
    f"GEOGRAPHY: {grapes_data['geography']} "
    f"RELIGION: {grapes_data['religion']} "
    f"POLITICS: {grapes_data['politics']} "
    f"ECONOMICS: {grapes_data['economics']} "
    f"SOCIAL: {grapes_data['social']} "
    f"ACHIEVEMENTS: {grapes_data['achievements']}"
)

# Store raw G.R.A.P.E.S. data for later reference
world.grapes_geography = grapes_data['geography']
world.grapes_religion = grapes_data['religion']
# ... etc
```

---

## B.4 WorldState Data Model Extensions

### B.4.1 New Fields

**Add to `WorldState` dataclass (line 216):**

```python
@dataclass
class WorldState:
    """A generated or loaded world configuration."""
    # Existing fields...
    name: str
    system_id: str
    system_display: str
    tone: str
    genre: str
    terms: dict[str, str] = field(default_factory=dict)
    primer: str = ""
    prompts_crown: list[str] = field(default_factory=list)
    prompts_crew: list[str] = field(default_factory=list)
    prompts_world: list[str] = field(default_factory=list)
    prompts_campfire: list[str] = field(default_factory=list)
    secret_witness: str = ""
    patrons: list[str] = field(default_factory=list)
    leaders: list[str] = field(default_factory=list)
    created_timestamp: float = field(default_factory=time.time)

    # NEW FIELDS for G.R.A.P.E.S.
    grapes_geography: str = ""
    grapes_religion: str = ""
    grapes_achievements: str = ""
    grapes_politics: str = ""
    grapes_economics: str = ""
    grapes_social: str = ""

    # NEW FIELD for Text Import
    import_source_text: str = ""  # Original pasted text
```

### B.4.2 Serialization Update

**Update `to_dict()` and `from_dict()` methods (lines 244, 264):**

```python
def to_dict(self) -> dict:
    """Serialize to JSON-compatible dict."""
    return {
        # ... existing fields ...
        "grapes_geography": self.grapes_geography,
        "grapes_religion": self.grapes_religion,
        "grapes_achievements": self.grapes_achievements,
        "grapes_politics": self.grapes_politics,
        "grapes_economics": self.grapes_economics,
        "grapes_social": self.grapes_social,
        "import_source_text": self.import_source_text,
    }

@classmethod
def from_dict(cls, data: dict) -> "WorldState":
    """Deserialize from dict."""
    return cls(
        # ... existing fields ...
        grapes_geography=data.get("grapes_geography", ""),
        grapes_religion=data.get("grapes_religion", ""),
        grapes_achievements=data.get("grapes_achievements", ""),
        grapes_politics=data.get("grapes_politics", ""),
        grapes_economics=data.get("grapes_economics", ""),
        grapes_social=data.get("grapes_social", ""),
        import_source_text=data.get("import_source_text", ""),
    )
```

---

## B.5 Text Import Flow

### B.5.1 Purpose

Allow users to paste existing setting documents (e.g., from a Google Doc, wiki, or .txt file) and auto-parse them into WorldState fields.

### B.5.2 Implementation

**New Method:** `WorldEngine._run_text_import()`

```python
async def _run_text_import(self) -> dict:
    """
    Run the Text Import wizard.

    User pastes freeform text, which is parsed (or sent to LLM) to extract
    world parameters.

    Returns:
        dict with extracted world data
    """
    console.clear()
    console.print(Panel(
        "[bold cyan]TEXT IMPORT WIZARD[/bold cyan]\n\n"
        "[dim]Paste your existing setting bible, wiki text, or notes.\n"
        "Press Enter twice when done (blank line to finish).[/dim]",
        box=box.DOUBLE,
        border_style=CYAN
    ))
    console.print()

    console.print("[green]Paste your setting text:[/green]")
    console.print("[dim](Enter a blank line to finish)[/dim]")
    console.print()

    lines = []
    while True:
        line = await _ainput("")
        if not line.strip():
            break
        lines.append(line)

    source_text = "\n".join(lines)

    if not source_text.strip():
        console.print("[yellow]No text provided. Returning to menu...[/yellow]")
        return {}

    console.print()
    console.print(f"[cyan]Received {len(source_text)} characters. Parsing...[/cyan]")

    # Parse strategy: LLM or keyword extraction?
    # OPTION 1: LLM-based extraction (if architect available)
    # OPTION 2: Keyword search (fallback)

    # For blueprint purposes, document BOTH strategies

    # Strategy A: LLM Extraction
    if self.architect:
        extracted = await self._llm_parse_setting_text(source_text)
    else:
        # Strategy B: Keyword Fallback
        extracted = self._keyword_parse_setting_text(source_text)

    console.print()
    console.print(Panel(
        f"[bold]Extracted Data:[/bold]\n\n"
        f"World Name: {extracted.get('name', 'Unknown')}\n"
        f"Genre: {extracted.get('genre', 'Unknown')}\n"
        f"Factions Detected: {len(extracted.get('factions', []))}\n"
        f"Primer Length: {len(extracted.get('primer', ''))} chars",
        border_style=EMERALD
    ))

    confirm = await _ainput("\n[gold1]Use this data? [Y/n]:[/] ")
    if confirm.lower() in ("n", "no"):
        return await self._run_text_import()  # Restart

    return extracted
```

### B.5.3 Parsing Strategies

#### Strategy A: LLM-Based Extraction

```python
async def _llm_parse_setting_text(self, source_text: str) -> dict:
    """
    Use the Architect to parse freeform setting text into structured data.

    Args:
        source_text: User-pasted setting bible

    Returns:
        dict with: name, genre, primer, factions, patrons, leaders, etc.
    """
    from codex_architect import RoutingDecision, ThinkingMode, Complexity, ThermalStatus

    prompt = f"""You are a world-building extraction engine.

Parse the following setting text and extract:
1. World name (if mentioned)
2. Genre (Fantasy, Sci-Fi, Horror, etc.)
3. Two opposing factions (names and brief descriptions)
4. A 2-3 sentence world primer
5. 3 authority figure names (patrons)
6. 3 rebel leader names

Setting text:
\"\"\"
{source_text[:3000]}  # Truncate to avoid token limits
\"\"\"

Output ONLY in this exact format:
===NAME===
[world name or "Unknown"]
===GENRE===
[genre]
===FACTION_AUTHORITY===
[name]
===FACTION_REBEL===
[name]
===PRIMER===
[2-3 sentences]
===PATRONS===
[patron 1]
[patron 2]
[patron 3]
===LEADERS===
[leader 1]
[leader 2]
[leader 3]
"""

    decision = RoutingDecision(
        mode=ThinkingMode.REFLEX,
        model="mimir",
        complexity=Complexity.MEDIUM,
        thermal_status=ThermalStatus.OPTIMAL,
        clearance_granted=True,
        reasoning="Text import parsing"
    )

    try:
        response = await self.architect.invoke_model(
            query=prompt,
            system_prompt="You are a data extraction tool. Output only the requested format.",
            decision=decision,
        )

        raw = response.content
        return self._parse_extraction_output(raw, source_text)

    except Exception as e:
        console.print(f"[yellow]LLM parsing failed: {e}. Using keyword fallback.[/yellow]")
        return self._keyword_parse_setting_text(source_text)
```

#### Strategy B: Keyword Fallback

```python
def _keyword_parse_setting_text(self, source_text: str) -> dict:
    """
    Fallback parser using keyword extraction.

    Args:
        source_text: User-pasted setting bible

    Returns:
        dict with basic extracted data
    """
    import re

    # Extract world name (look for "World of X", "The X Realm", etc.)
    name_patterns = [
        r"[Ww]orld of ([\w\s]+)",
        r"The ([\w\s]+) Realm",
        r"Setting: ([\w\s]+)",
    ]
    name = "Imported World"
    for pattern in name_patterns:
        match = re.search(pattern, source_text)
        if match:
            name = match.group(1).strip()
            break

    # Extract genre (look for keywords)
    genre = "Fantasy"  # Default
    if any(kw in source_text.lower() for kw in ["space", "starship", "laser", "cyberpunk"]):
        genre = "Sci-Fi"
    elif any(kw in source_text.lower() for kw in ["vampire", "horror", "gothic", "ghost"]):
        genre = "Horror"

    # Extract factions (crude: look for "vs", "against", "opposed to")
    factions = []
    faction_pattern = r"([\w\s]+) (?:vs|versus|against|opposed to) ([\w\s]+)"
    match = re.search(faction_pattern, source_text, re.IGNORECASE)
    if match:
        factions = [match.group(1).strip(), match.group(2).strip()]
    else:
        factions = ["The Authority", "The Resistance"]  # Defaults

    # Primer: First 2-3 sentences
    sentences = re.split(r'[.!?]\s+', source_text)
    primer = ". ".join(sentences[:3]) + "."

    return {
        "name": name,
        "genre": genre,
        "faction_authority": factions[0],
        "faction_rebel": factions[1],
        "primer": primer,
        "patrons": ["Patron 1", "Patron 2", "Patron 3"],  # Placeholder
        "leaders": ["Leader 1", "Leader 2", "Leader 3"],  # Placeholder
        "import_source_text": source_text,
    }

def _parse_extraction_output(self, raw: str, original_text: str) -> dict:
    """Parse the LLM's structured output into a dict."""
    def _extract(marker: str) -> str:
        start = raw.find(f"==={marker}===")
        if start == -1:
            return ""
        start = raw.index("===", start) + len(f"==={marker}===")
        end = raw.find("===", start)
        if end == -1:
            end = len(raw)
        return raw[start:end].strip()

    def _lines(section: str) -> list[str]:
        return [ln.strip() for ln in section.splitlines() if ln.strip()]

    return {
        "name": _extract("NAME") or "Imported World",
        "genre": _extract("GENRE") or "Fantasy",
        "faction_authority": _extract("FACTION_AUTHORITY") or "The Authority",
        "faction_rebel": _extract("FACTION_REBEL") or "The Resistance",
        "primer": _extract("PRIMER") or "A world of conflict.",
        "patrons": _lines(_extract("PATRONS")) or ["Patron 1", "Patron 2", "Patron 3"],
        "leaders": _lines(_extract("LEADERS")) or ["Leader 1", "Leader 2", "Leader 3"],
        "import_source_text": original_text,
    }
```

---

## B.6 Testing Requirements for @Playtester

**Test Cases:**

1. **G.R.A.P.E.S. Full Flow**
   - Select method [2]
   - Answer all 6 questions
   - Verify data appears in World Receipt
   - Verify saved JSON contains `grapes_*` fields

2. **G.R.A.P.E.S. Cancellation**
   - Start G.R.A.P.E.S. wizard
   - Answer "no" at confirmation
   - Verify restart or return to menu

3. **Text Import with LLM**
   - Paste a 500-word setting description
   - Verify LLM extracts factions, primer, names
   - Verify `import_source_text` field populated

4. **Text Import Keyword Fallback**
   - Disable Architect (set to None)
   - Paste text
   - Verify keyword parser extracts basic data
   - Verify no crashes

5. **Quick Genesis Backward Compatibility**
   - Select method [1]
   - Verify old flow works unchanged
   - Verify no `grapes_*` fields in output

---

# SECTION C: INTEGRATION BLUEPRINT

## C.1 Main Menu Integration

### C.1.1 Current Menu (codex_agent_main.py:949)

**Existing Options:**
```
[1] New Campaign     — Begin a new adventure
[2] Crown & Crew     — 5-Day Narrative Journey
[3] Mimir Chat       — Speak with the AI
[4] System Status    — View detailed vitals
[5] Exit             — Return to the mundane world
```

### C.1.2 Proposed Menu Update

**Add new option [6]:**

```
[1] New Campaign     — Begin a new adventure
[2] Crown & Crew     — 5-Day Narrative Journey
[3] Ashburn High     — Gothic Heir Corruption Campaign  ← NEW
[4] Mimir Chat       — Speak with the AI
[5] System Status    — View detailed vitals
[6] Exit             — Return to the mundane world
```

**Implementation:**

```python
# In codex_agent_main.py, main_menu() function (line 927)

menu.add_row("[1]", "New Campaign     — Begin a new adventure")
menu.add_row("[2]", "Crown & Crew     — 5-Day Narrative Journey")
menu.add_row("[3]", "Ashburn High     — Gothic Heir Corruption Campaign")  # NEW
menu.add_row("[4]", "Mimir Chat       — Speak with the AI")
menu.add_row("[5]", "System Status    — View detailed vitals")
menu.add_row("[6]", "Exit             — Return to the mundane world")

# ... later in the choice handler ...

choice = await ainput("[gold1]Choose thy path [1/2/3/4/5/6/q]:[/] ")

# ... existing cases ...

elif choice == "3":
    # NEW: Ashburn High campaign
    ws = None
    if current_save and current_save.state.get("world_state"):
        ws = current_save.state["world_state"]
    await run_ashburn_campaign(world_state=ws)
```

---

## C.2 Ashburn Campaign Runner

### C.2.1 New Function

**Add to codex_agent_main.py:**

```python
async def run_ashburn_campaign(world_state: dict = None):
    """
    Run the Ashburn High 5-Day Corruption Campaign.

    Uses AshburnHeirEngine instead of base CrownAndCrewEngine.

    Args:
        world_state: Optional WorldState dict (from saved game or genesis)
    """
    console.clear()

    # Import at runtime to avoid circular dependency
    from ashburn_crew_module import AshburnHeirEngine

    # Get heir name from player
    console.print(Panel(
        "[bold gold1]ASHBURN HIGH[/bold gold1]\n\n"
        "[dim]You are the heir to a disgraced noble family.\n"
        "Five days remain before the Inheritance Tribunal.\n"
        "Manage your corruption. Guard your legacy.[/dim]",
        box=box.DOUBLE,
        border_style=CRIMSON,
        title="[bold]⚔️  The Heir Rises ⚔️[/bold]"
    ))
    console.print()

    heir_name = await ainput("[gold1]What is your name, heir?[/] [The Heir]: ")
    if not heir_name.strip():
        heir_name = "The Heir"

    # Initialize engine
    engine = AshburnHeirEngine(
        world_state=world_state,
        heir_name=heir_name
    )

    # Title screen with NPC intro
    console.clear()
    console.print(engine.get_heir_status())
    console.print()
    console.print(Panel(
        "[bold]THE FOUR LEADERS[/bold]\n\n"
        + "\n\n".join([
            f"[bold]{npc['name']}[/bold] — {npc['archetype']}\n"
            f"  Ability: {npc['ability']}\n"
            f"  Risk: {npc['risk']}"
            for npc in engine.npcs.values()
        ]),
        border_style=SILVER,
        box=box.ROUNDED
    ))
    await ainput("\n[dim]Press Enter to begin your journey...[/dim]")

    # Main game loop (same structure as run_crown_campaign, but with Ashburn checks)
    for day in range(1, 6):
        # Determine region
        if day <= 2:
            region = "THE GROUNDS"
        elif day == 3:
            region = "THE BREACH"
        elif day == 4:
            region = "THE TRIBUNAL HALL"
        else:
            region = "THE INHERITANCE"

        # PHASE 1: MORNING
        console.clear()
        console.print(engine.get_heir_status())
        console.print()
        console.print(f"[bold gold1]DAY {day} — {region}[/bold gold1]")
        console.print()
        console.print("[bold cyan]☀️  MORNING — THE PATH AHEAD[/bold cyan]")
        console.print()

        world = engine.get_world_prompt()
        console.print(Panel(world, border_style=SILVER, padding=(1, 2)))

        if day == 3:
            console.print()
            console.print(Panel(
                engine.get_secret_witness(),
                title="[bold red]👁️  A WITNESS EMERGES[/bold red]",
                border_style=CRIMSON,
                padding=(1, 2)
            ))

        console.print()
        await ainput("[dim]How do you proceed? > [/dim]")

        # PHASE 2: NIGHT — Allegiance + Legacy Check
        console.clear()
        console.print(engine.get_heir_status())
        console.print()
        console.print("[bold magenta]🌙 NIGHT — THE CHOICE[/bold magenta]")
        console.print()

        # Allegiance choice
        while True:
            choice = (await ainput(
                "[gold1]Declare allegiance — [C]rown or C[R]ew: [/]"
            )).lower().strip()

            if choice in ('c', 'crown'):
                side = 'crown'
                break
            elif choice in ('r', 'crew'):
                side = 'crew'
                break
            else:
                console.print("[dim]Enter C for Crown or R for Crew[/dim]")

        # Declare + Legacy Check
        result = engine.declare_allegiance(side)
        console.print(f"\n[bold cyan]>> {result}[/bold cyan]")

        # Check for Legacy Check trigger (only on Crown)
        if side == 'crown':
            legacy_check = engine.generate_legacy_check()
            if legacy_check["triggered"]:
                console.print()
                console.print(Panel(
                    f"[bold red]⚠️  LEGACY CHECK TRIGGERED (Roll: {legacy_check['roll']})[/bold red]\n\n"
                    f"{legacy_check['prompt']}\n\n"
                    f"[cyan][L] LIE[/cyan] — {legacy_check['lie_option']}\n"
                    f"[green][T] TRUTH[/green] — {legacy_check['truth_option']}",
                    title="[bold]THE WEIGHT OF LEGACY[/bold]",
                    border_style=CRIMSON,
                    padding=(1, 2)
                ))

                while True:
                    lc_choice = (await ainput("[bold gold1][L]ie or [T]ruth: [/]")).lower().strip()
                    if lc_choice in ('l', 'lie', 't', 'truth'):
                        break

                lc_result = engine.process_legacy_choice(lc_choice)
                console.print(f"\n[bold yellow]>> {lc_result}[/bold yellow]")

                # Check for immediate loss
                loss_check = engine.check_betrayal()
                if loss_check["game_over"]:
                    console.print()
                    console.print(Panel(
                        loss_check["message"],
                        title="[bold red]💀 GAME OVER 💀[/bold red]",
                        border_style=CRIMSON,
                        box=box.DOUBLE
                    ))
                    await ainput("\n[dim]Press Enter to return to Main Menu...[/dim]")
                    return  # Exit campaign

        # Show dilemma
        prompt = engine.get_prompt()
        console.print()
        console.print(Panel(
            f"[italic]{prompt}[/italic]",
            border_style=MAGENTA,
            padding=(1, 2)
        ))

        console.print()
        await ainput("[bold green]What do you do? > [/bold green]")

        # PHASE 3: CAMPFIRE (except Day 3)
        if day != 3:
            console.clear()
            console.print(engine.get_heir_status())
            console.print()
            console.print("[bold yellow]🔥 CAMPFIRE — THE ECHO[/bold yellow]")
            console.print()

            campfire = engine.get_campfire_prompt()
            console.print(Panel(campfire, border_style="yellow", padding=(1, 2)))

            console.print()
            await ainput("[bold green]Your reflection? > [/bold green]")

        # PHASE 4: END DAY
        console.print()
        end_msg = engine.end_day()
        for line in end_msg.split('\n'):
            console.print(f"[cyan]{line}[/cyan]")

        console.print()
        if day < 5:
            await ainput("[dim]Press Enter to rest...[/dim]")
        else:
            await ainput("[dim]Press Enter to face your fate...[/dim]")

    # FINALE
    console.clear()

    # Final corruption check
    loss_check = engine.check_betrayal()
    if loss_check["game_over"]:
        console.print(Panel(
            loss_check["message"],
            title="[bold red]💀 YOUR LEGACY IS CONSUMED 💀[/bold red]",
            border_style=CRIMSON,
            box=box.DOUBLE
        ))
    else:
        # Victory report
        report = engine.generate_legacy_report()
        summary = engine.get_summary()

        console.print(Panel(
            "[bold gold1]THE INHERITANCE — JOURNEY'S END[/bold gold1]\n\n"
            "[dim]You have survived the five days.\n"
            "The Tribunal awaits your testimony.[/dim]",
            box=box.DOUBLE,
            border_style=GOLD
        ))

        console.print()
        console.print(Panel(
            report,
            title="[bold]⚔️  LEGACY REPORT ⚔️[/bold]",
            border_style=EMERALD,
            padding=(1, 2)
        ))

        console.print()
        console.print(Panel(
            summary,
            title="[bold]📜 JOURNEY LOG[/bold]",
            border_style=SILVER,
            padding=(1, 2)
        ))

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ashburn_legacy_{timestamp}.txt"
    with open(filename, 'w') as f:
        f.write("ASHBURN HIGH - LEGACY REPORT\n")
        f.write(f"Heir: {engine.heir_name}\n")
        f.write(f"Final Corruption: {engine.legacy_corruption}/5\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(engine.generate_legacy_report() + "\n\n" + engine.get_summary())

    console.print(f"\n[dim]Report saved to: {filename}[/dim]")
    await ainput("\n[dim]Press Enter to return to Main Menu...[/dim]")
```

---

## C.3 Betrayal Nullification Cross-Cutting Logic

### C.3.1 Scope

**Betrayal Nullification** affects BOTH:
1. Base `CrownAndCrewEngine` (optional: can be added in a future update)
2. `AshburnHeirEngine` (mandatory: integrated now)

### C.3.2 Decision Point

**Should Betrayal Nullification be in the parent class or only in Ashburn?**

**RECOMMENDATION: Ashburn-only for now.**

**Rationale:**
- The base Crown & Crew system is stable and in production
- Adding betrayal detection to the parent changes core mechanics
- Ashburn is a variant that EXPECTS harsher consequences
- Future work order can promote it to parent if desired

**Alternative (Future Enhancement):**
If promoting to parent, add a flag:

```python
# In CrownAndCrewEngine.__init__():
betrayal_detection_enabled: bool = False

# In CrownAndCrewEngine.resolve_vote():
if self.betrayal_detection_enabled:
    # Run betrayal detection logic
    pass
```

Then Ashburn sets `betrayal_detection_enabled = True` in `__post_init__()`.

### C.3.3 Corruption as Cross-Cutting Concern

**Corruption triggers in Ashburn:**
1. Legacy Check (Lie choice) → +1 corruption
2. Betrayal Nullification → +1 corruption
3. NPC betrayal (Rowan risk) → +2 corruption

**Integration Point:**
Every corruption-triggering event calls `add_corruption(amount)`, which internally calls `check_betrayal()` to enforce immediate loss.

---

## C.4 Module Loading Strategy

### C.4.1 Import Structure

**In codex_agent_main.py (top-level imports):**

```python
# Existing imports...
from codex_crown_module import CrownAndCrewEngine
from codex_world_engine import WorldEngine, WorldState, get_world_engine

# NEW IMPORT
try:
    from ashburn_crew_module import AshburnHeirEngine
    ASHBURN_AVAILABLE = True
except ImportError:
    ASHBURN_AVAILABLE = False
    logger.warning("Ashburn module not available")
```

**Lazy Loading (Alternative):**

If we want to avoid loading Ashburn unless needed:

```python
# In run_ashburn_campaign():
from ashburn_crew_module import AshburnHeirEngine  # Import only when called
```

**RECOMMENDATION: Top-level import with try/except.**

**Rationale:**
- Fails gracefully if ashburn_crew_module.py doesn't exist
- Allows menu option to be hidden if unavailable
- Matches existing Discord/Telegram bot pattern (lines 54-66)

### C.4.2 Feature Flag

**Menu visibility:**

```python
# In main_menu():
menu.add_row("[1]", "New Campaign     — Begin a new adventure")
menu.add_row("[2]", "Crown & Crew     — 5-Day Narrative Journey")

if ASHBURN_AVAILABLE:
    menu.add_row("[3]", "Ashburn High     — Gothic Heir Corruption Campaign")
    next_option = "4"
else:
    next_option = "3"

menu.add_row(f"[{next_option}]", "Mimir Chat       — Speak with the AI")
# ... etc
```

---

## C.5 Backward Compatibility

### C.5.1 Existing Save Files

**Issue:** Existing Crown & Crew save files don't have Ashburn fields.

**Solution:** Type detection in load logic.

```python
# In GameSave.from_dict():
@classmethod
def from_dict(cls, data: dict) -> "GameSave":
    save = cls(
        name=data["name"],
        world=data["world"],
        level=data["level"],
        created=datetime.fromisoformat(data["created"])
    )
    save.playtime_hours = data.get("playtime_hours", 0)
    save.state = data.get("state", {})

    # Check if this is an Ashburn save
    if save.state.get("engine_type") == "ashburn":
        save.is_ashburn = True  # NEW field

    return save
```

**Menu integration:**

```python
# In main_menu():
if current_save:
    if hasattr(current_save, 'is_ashburn') and current_save.is_ashburn:
        console.print(f"[dim]Active Campaign: [bold]{current_save.name}[/bold] (Ashburn High)[/dim]")
    else:
        console.print(f"[dim]Active Campaign: [bold]{current_save.name}[/bold] ({current_save.world})[/dim]")
```

### C.5.2 WorldState Compatibility

**Issue:** Existing worlds don't have `grapes_*` fields.

**Solution:** Default empty strings in `from_dict()` (already implemented in B.4.2).

**Verification:**
- Load a world created before this update
- All `grapes_*` fields default to `""`
- World is usable in both Classic and Ashburn modes

---

## C.6 Discord Integration (Future)

**Out of scope for this work order, but documented for future reference:**

When Ashburn is eventually exposed via Discord:

```python
# In codex_discord_bot.py (new command):

@commands.command(name="ashburn")
async def cmd_ashburn(self, ctx):
    """Start an Ashburn High campaign in this channel."""
    from ashburn_crew_module import AshburnHeirEngine

    # Initialize engine with Discord session state
    user_id = str(ctx.author.id)
    engine = AshburnHeirEngine()

    # Store in session
    self.core.get_session(user_id).game_state["ashburn_engine"] = engine

    # Send heir status embed
    embed = discord.Embed(
        title="⚔️  ASHBURN HIGH  ⚔️",
        description=f"Welcome, {engine.heir_name}.",
        color=engine.get_sway_color()
    )
    embed.add_field(name="Corruption", value=f"{engine.legacy_corruption}/5")
    await ctx.send(embed=embed)
```

---

## C.7 Testing Requirements for @Playtester

**Integration Test Cases:**

1. **Menu Navigation**
   - Launch codex_agent_main.py
   - Verify option [3] appears (if ASHBURN_AVAILABLE)
   - Select [3]
   - Verify Ashburn campaign starts

2. **Ashburn Full Playthrough**
   - Play full 5-day Ashburn campaign
   - Trigger at least one Legacy Check
   - Trigger Betrayal Nullification
   - Verify corruption increments correctly
   - Verify immediate loss at corruption ≥ 5

3. **Ashburn + Custom World**
   - Create a G.R.A.P.E.S. world
   - Start Ashburn campaign with that world
   - Verify terms, prompts, and NPCs use world data

4. **Save/Load Ashburn Campaign**
   - Start Ashburn, play to Day 3
   - Save via GameSave system
   - Load save
   - Verify corruption, NPCs, betrayal state restored

5. **Backward Compatibility**
   - Load an old Crown & Crew save
   - Play normally
   - Verify no crashes, no Ashburn features leak in

---

# SECTION D: RISK ASSESSMENT & MITIGATION

## D.1 Identified Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Circular Import** (ashburn → crown → world → architect) | HIGH | MEDIUM | Use lazy imports, careful module structure |
| **State Corruption** (corrupted save files) | HIGH | LOW | Add save file versioning, validation on load |
| **LLM Timeout** (G.R.A.P.E.S. parsing hangs) | MEDIUM | MEDIUM | 30-second timeout, fallback to keyword parser |
| **Thermal Overload** (sustained LLM calls) | LOW | LOW | G.R.A.P.E.S. is one-time generation, not looped |
| **Breaking Existing Games** (parent class changes) | CRITICAL | LOW | Ashburn is a subclass, parent unchanged |
| **Discord Concurrency** (Ashburn state shared across channels) | MEDIUM | MEDIUM | Use session isolation (user_id keying) |

## D.2 Mitigation Strategies

### Circular Import Prevention

```
SAFE IMPORT ORDER:
1. codex_cortex (no dependencies)
2. codex_architect (depends on cortex)
3. codex_world_engine (depends on architect)
4. codex_crown_module (depends on world_engine)
5. ashburn_crew_module (depends on crown_module)
6. codex_agent_main (imports all)
```

**Rule:** Never import codex_agent_main from any module.

### Save File Versioning

**Add to all save files:**

```python
{
    "save_version": "1.0",  # Increment on breaking changes
    "engine_type": "ashburn",
    ...
}
```

**Load validation:**

```python
if data.get("save_version") != "1.0":
    raise ValueError("Incompatible save file version")
```

### Thermal Safety

**G.R.A.P.E.S. wizard does NOT call LLM.**
- User provides text manually
- No AI generation during interview

**Text Import calls LLM once:**
- 30-second timeout
- Fallback to keyword parser on failure

---

# SECTION E: WORK ORDER SUMMARY

## E.1 Deliverables Checklist for @Mechanic

- [ ] **Create:** `ashburn_crew_module.py`
  - [ ] `AshburnHeirEngine` class with all specified methods
  - [ ] NPC dictionary initialization
  - [ ] Legacy Check system
  - [ ] Betrayal Nullification logic
  - [ ] Corruption tracking and immediate loss
  - [ ] Rich status panel
  - [ ] Save/load extensions

- [ ] **Modify:** `codex_world_engine.py`
  - [ ] Add `grapes_*` fields to `WorldState` dataclass
  - [ ] Add `import_source_text` field
  - [ ] Update `to_dict()` and `from_dict()` serialization
  - [ ] Add creation method selector to `run_genesis_wizard()`
  - [ ] Implement `_run_grapes_wizard()` method
  - [ ] Implement `_run_text_import()` method
  - [ ] Implement `_llm_parse_setting_text()` method
  - [ ] Implement `_keyword_parse_setting_text()` method
  - [ ] Implement `_parse_extraction_output()` method

- [ ] **Modify:** `codex_agent_main.py`
  - [ ] Add Ashburn import with try/except
  - [ ] Add `ASHBURN_AVAILABLE` flag
  - [ ] Update main menu to include option [3]
  - [ ] Implement `run_ashburn_campaign()` function
  - [ ] Add Ashburn detection in save file display
  - [ ] Update menu numbering logic for dynamic options

- [ ] **Testing** (for @Playtester)
  - [ ] All test cases from Sections A.11, B.6, C.7
  - [ ] Thermal monitoring during extended play
  - [ ] Save/load integrity across all modes

## E.2 Implementation Priority

**PHASE 1: Foundation (Est. 4 hours)**
1. WorldState data model extensions (B.4)
2. AshburnHeirEngine skeleton class (A.2, A.3)
3. Basic import structure in main (C.4)

**PHASE 2: World Builder (Est. 3 hours)**
4. G.R.A.P.E.S. wizard (B.3)
5. Text Import wizard (B.5)
6. LLM + keyword parsers (B.5.3)

**PHASE 3: Ashburn Mechanics (Est. 5 hours)**
7. Legacy Check system (A.5)
8. Betrayal Nullification (A.6)
9. Corruption + immediate loss (A.7)
10. NPC system (A.4)
11. Rich status panel (A.8)

**PHASE 4: Integration (Est. 3 hours)**
12. Ashburn campaign runner (C.2)
13. Menu integration (C.1)
14. Save/load (A.9, C.5)

**PHASE 5: Testing (Est. 2 hours)**
15. Unit tests for all new methods
16. Integration tests
17. Playthrough verification

**TOTAL ESTIMATED TIME: 17 hours**

## E.3 Acceptance Criteria

**The implementation is COMPLETE when:**

1. A player can select "Ashburn High" from the main menu
2. The Ashburn campaign runs for 5 days with corruption tracking
3. Legacy Checks trigger on Crown allegiance with 33% probability
4. Corruption ≥ 5 triggers immediate game-over
5. Betrayal Nullification correctly reduces vote power to 1x
6. G.R.A.P.E.S. wizard collects 6 answers and populates WorldState
7. Text Import accepts pasted text and extracts world data (LLM or keyword)
8. All save files serialize/deserialize correctly
9. Backward compatibility: old Crown & Crew saves still load
10. No thermal alerts during normal gameplay
11. All @Playtester test cases pass

---

# SECTION F: APPENDICES

## F.1 Color Palette Reference

```python
# From codex_agent_main.py (lines 112-118)
GOLD = "bold yellow"
CRIMSON = "bold red"
EMERALD = "bold green"
SILVER = "dim white"
ROYAL_BLUE = "bold blue"
PARCHMENT = "wheat1"
MAGENTA = "bold magenta"
CYAN = "bold cyan"
```

**Usage in Ashburn:**
- Corruption warnings: `CRIMSON`
- Status panels: `GOLD` borders
- NPCs: `SILVER` text
- Legacy Checks: `MAGENTA` borders

## F.2 Rich Formatting Patterns

**Panel with Double Border:**
```python
Panel(content, box=box.DOUBLE, border_style=GOLD, title="Title")
```

**Table with Heavy Edge:**
```python
Table(box=box.HEAVY_EDGE, border_style=SILVER, title="Title")
```

**Inline Color Markup:**
```python
console.print("[bold red]Warning[/bold red]")
```

## F.3 File Path Conventions

**All paths MUST be absolute (Raspberry Pi environment):**

```python
# CORRECT:
save_path = Path("/home/pi/Projects/claude_sandbox/Codex/saves/game.json")

# INCORRECT (cwd resets between bash calls):
save_path = Path("saves/game.json")
```

**Use CODEX_DIR constant:**
```python
CODEX_DIR = Path(__file__).resolve().parent
save_path = CODEX_DIR / "saves" / "game.json"
```

## F.4 Async Pattern Reference

**Terminal Input (Non-Blocking):**
```python
user_input = await ainput("[gold1]Prompt:[/] ")
```

**Confirmation:**
```python
confirmed = await aconfirm("Proceed?", default=True)
```

**Status Spinner:**
```python
with console.status("[cyan]Processing...[/cyan]", spinner="dots"):
    await asyncio.sleep(2)
```

## F.5 Type Hints Standard

**Use Python 3.10+ syntax:**
```python
def method(self, param: str | None = None) -> dict[str, int]:
    pass
```

**DataClass Fields:**
```python
from typing import Literal

side: Literal["crown", "crew"]
npcs: dict[str, dict] = field(default_factory=dict)
```

---

# SECTION G: THERMAL CONSIDERATIONS

## G.1 CPU Impact Analysis

**Ashburn Module:**
- NEW: Legacy Check roll (1d6) → Negligible
- NEW: Corruption tracking (int increment) → Negligible
- NEW: NPC dictionary lookups → Negligible
- EXISTING: All parent methods (already profiled)

**Estimated Thermal Delta:** +0.5°C (stateless computation)

**G.R.A.P.E.S. Wizard:**
- User input (blocking I/O) → No CPU
- String concatenation → Negligible

**Estimated Thermal Delta:** +0°C

**Text Import (LLM Parsing):**
- Single LLM call (~3000 tokens)
- Duration: 10-30 seconds
- Thermal impact: Same as existing Mimir chat

**Estimated Thermal Delta:** +2-5°C during parse, returns to baseline after

**Mitigation:**
- LLM parsing is one-time (world creation only)
- Not repeated during gameplay
- Timeout at 30 seconds
- Fallback to zero-CPU keyword parser

## G.2 Memory Impact

**Ashburn State:**
- 4 NPCs × ~200 bytes = 800 bytes
- Corruption int: 8 bytes
- Betrayal flag: 1 byte

**Total Ashburn Overhead:** ~1 KB per session

**G.R.A.P.E.S. Data:**
- 6 text fields × ~500 chars = 3000 bytes

**Total G.R.A.P.E.S. Overhead:** ~3 KB per world

**Assessment:** NEGLIGIBLE (Raspberry Pi has 4-8 GB RAM)

---

# SECTION H: OPEN QUESTIONS FOR USER

**None.** Blueprint is complete and ready for implementation.

If during implementation @Mechanic encounters ambiguities, refer to this document first. If unresolved, escalate to @Architect for clarification.

---

# FINAL SIGN-OFF

**Blueprint Status:** ✅ COMPLETE
**Ready for Handoff:** YES
**Estimated Implementation Time:** 17 hours
**Risk Level:** MEDIUM
**Thermal Impact:** LOW

**@Architect Notes:**
This blueprint defines two tightly integrated features with clear boundaries. The Ashburn module is a clean subclass extension. The World Builder is a UI enhancement with no breaking changes. Both features support the core philosophy: emergent narrative through structured choice.

The Betrayal Nullification mechanic is intentionally harsh — it reflects the gothic tone of Ashburn High where political capital is fragile and corruption is a one-way door.

All designs prioritize backward compatibility and thermal safety.

**Next Step:** @Mechanic implements. @Playtester verifies. @Designer populates ASHBURN_LEGACY_PROMPTS pool with gothic flavor text.

---

**END OF BLUEPRINT**

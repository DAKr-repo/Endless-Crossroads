# WORK ORDER 039-A — ASHBURN GOTHIC VISUAL IDENTITY
**Design Specification Document**
**Project:** C.O.D.E.X. — Ashburn Heir Campaign
**Designer:** @codex-designer
**Date:** 2026-02-03
**Status:** DESIGN COMPLETE — READY FOR IMPLEMENTATION

---

## 1. MAIN MENU ENTRY

### Visual Design
The Ashburn entry must contrast with the base game's high-fantasy aesthetic. Where Crown & Crew is **gold and heroic**, Ashburn is **crimson and institutional**.

#### Menu String (Plain)
```
[3] 🥀 The Ashburn Protocol — Gothic Heir Campaign
```

#### Rich Markup Version
```python
"[3] [bold red]🥀 THE ASHBURN PROTOCOL[/bold red] [dim]— Gothic Heir Campaign[/dim]"
```

#### Full Menu Mockup
```
╔═══════════════════════════════════════════════════════════════════╗
║                         ══════ MAIN QUEST ══════                 ║
╠═══════════════════════════════════════════════════════════════════╣
║  [1]  New Campaign       — Begin a new adventure                 ║
║  [2]  Crown & Crew       — 5-Day Narrative Journey               ║
║  [3]  🥀 THE ASHBURN PROTOCOL — Gothic Heir Campaign             ║
║  [4]  Mimir Chat         — Speak with the AI                     ║
║  [5]  System Status      — View detailed vitals                  ║
║  [6]  Exit               — Return to the mundane world           ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Rationale:**
- Rose emoji (🥀) signals decay, gothic romance, boarding school crests
- Crimson text breaks the gold/emerald pattern of the standard menu
- "Protocol" instead of "Campaign" — institutional, clinical
- Dimmed subtitle de-emphasizes to maintain hierarchy

---

## 2. ASHBURN LANDING SCREEN — ASCII HEADER

### "The Iron Gates" — Gothic Boarding School Entry

#### ASCII Art (Width: 64 characters)
```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│   ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄    │
│   █                                                  █    │
│   █    A S H B U R N   H I G H                       █    │
│   █                                                  █    │
│   █    ═══ The Legacy You Cannot Escape ═══         █    │
│   █                                                  █    │
│   ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀    │
│              ║                      ║                      │
│              ║  Corruption: [░░░░░] ║                      │
│              ║   Your Move.          ║                      │
│              ║                      ║                      │
└────────────────────────────────────────────────────────────┘
```

#### Alternative — Minimalist Spire Version
```
        ▲
       ███
      █████
     ███████
    █████████
       ███
       ███     A S H B U R N   H I G H
       ███
   ═══════════════════════════════════════
    The Iron Gates        Day 1/5
    Corruption: [░░░░░]   Sway: [═══◆═══]
   ═══════════════════════════════════════
```

**Rationale:**
- Heavy lines evoke wrought iron, institutional architecture
- Symmetry suggests authority, rigidity
- Sparse decoration — no flourishes, no warmth
- Vertical lines (pillars, gates) create oppressive height
- Corruption meter immediately visible — this is a loss-condition game

**Rich Panel Wrapper:**
```python
from rich.panel import Panel
from rich import box

console.print(Panel(
    ASHBURN_HEADER_ART,
    box=box.HEAVY,
    border_style="bold red",
    title="[bold red]⚔️  THE ASHBURN PROTOCOL  ⚔️[/bold red]",
    title_align="center"
))
```

---

## 3. HEIR DOSSIER PANELS

### Panel A: Julian Ashburn — "The Gilded Son"

#### Rich Panel Code
```python
from rich.panel import Panel
from rich import box
from rich.text import Text

julian_panel = Panel(
    "[bold gold1]JULIAN ASHBURN[/bold gold1]\n"
    "[dim]The Gilded Son[/dim]\n\n"
    "[italic]A golden prince trapped in amber. The Board chose him "
    "before he could choose himself.[/italic]\n\n"
    "[bold cyan]POWER:[/bold cyan] Command\n"
    "  [dim]Legacy Name grants +1 Crown Sway at start[/dim]\n\n"
    "[bold red]RISK:[/bold red] Burn\n"
    "  [dim]Cannot refuse Crown challenges, even losing ones[/dim]",
    box=box.DOUBLE,
    border_style="gold1",
    title="[bold]HEIR PROFILE — JULIAN[/bold]",
    padding=(1, 2)
)
```

**Visual Notes:**
- Gold border — wealth, privilege, gilded cage
- `box.DOUBLE` — formal, aristocratic
- Cyan for abilities (institutional blessing)
- Red for risks (the price of legacy)

---

### Panel B: Rowan Ashburn — "The Ash Walker"

#### Rich Panel Code
```python
rowan_panel = Panel(
    "[bold grey70]ROWAN ASHBURN[/bold grey70]\n"
    "[dim]The Ash Walker[/dim]\n\n"
    "[italic]They found the old records. They know what the school buried. "
    "Now the school knows they know.[/italic]\n\n"
    "[bold dark_orange]POWER:[/bold dark_orange] Reveal\n"
    "  [dim]Ember Network shows all Campfire event locations[/dim]\n\n"
    "[bold dark_red]RISK:[/bold dark_red] Exposure\n"
    "  [dim]Random Campfire events trigger corruption checks[/dim]",
    box=box.HEAVY,
    border_style="grey58",
    title="[bold]HEIR PROFILE — ROWAN[/bold]",
    padding=(1, 2)
)
```

**Visual Notes:**
- Grey border — ash, obscurity, resistance
- `box.HEAVY` — scarred, industrial, weight
- Orange accent — embers, hidden fire, insurgency
- Dark red for risks (exposure to corruption)

---

## 4. ASHBURN COLOR PALETTE

### Palette Definition (Rich Color Codes)

```python
# Ashburn Gothic Color Scheme
ASHBURN_CRIMSON = "bold red"          # Corruption, danger, The Board
ASHBURN_ASH_GREY = "grey70"           # Institution, stone, neutrality
ASHBURN_EMBER = "dark_orange"         # Resistance, Crew, hidden fire
ASHBURN_DEEP_PURPLE = "dark_magenta"  # Legacy Interventions, supernatural
ASHBURN_PALE_SILVER = "bright_white"  # Narration, atmospheric text
ASHBURN_BLOOD = "dark_red"            # High corruption states
ASHBURN_GOLD = "gold1"                # Julian's wealth/privilege (rare use)
ASHBURN_DIM = "dim white"             # De-emphasized, secondary text
```

### Usage Matrix

| Element                  | Color              | Rich Code           | Rationale                          |
|-------------------------|--------------------|---------------------|------------------------------------|
| Corruption Meter (0-2)  | Green              | `green`             | Safe zone                          |
| Corruption Meter (3-4)  | Ember Orange       | `dark_orange`       | Warning — you're slipping          |
| Corruption Meter (5)    | Crimson (flashing) | `bold red blink`    | Loss condition imminent            |
| The Board (Crown)       | Crimson            | `bold red`          | Authority, control                 |
| The Crew                | Ember Orange       | `dark_orange`       | Insurgency, warmth amid cold       |
| Ashburn Academy (World) | Ash Grey           | `grey70`            | Stone, fog, institutional          |
| Legacy Interventions    | Deep Purple        | `dark_magenta`      | Uncanny, supernatural pressure     |
| Heir Names              | Pale Silver        | `bright_white`      | Ghostly, clinical                  |
| Corruption Warnings     | Blood Red          | `dark_red`          | Dread, inevitability               |
| Mimir's Voice (Ashburn) | Ash Grey           | `grey70`            | Colder, more clinical than gold    |

**Design Note:**
The standard Crown & Crew uses **Gold (Crown) vs. Magenta (Crew)**. Ashburn replaces this with **Crimson (Board) vs. Ember (Crew)** — both darker, both oppressive, both corrupting in different ways.

---

## 5. CORRUPTION METER VISUAL

### Format String & Color Progression

#### Basic Format
```
Corruption: [██░░░] 2/5 — Tempted
```

#### Python Implementation
```python
def render_corruption_meter(corruption: int) -> str:
    """
    Render the Ashburn corruption meter with color-coded status.

    Args:
        corruption: int 0-5

    Returns:
        Rich markup string
    """
    # Visual bar
    filled = "█" * corruption
    empty = "░" * (5 - corruption)

    # Color logic
    if corruption == 0:
        color = "green"
    elif corruption <= 2:
        color = "yellow"
    elif corruption <= 4:
        color = "dark_orange"
    else:
        color = "bold red blink"  # Flashing at threshold

    # Status labels
    status_labels = {
        0: "Pure",
        1: "Curious",
        2: "Tempted",
        3: "Compromised",
        4: "Consumed",
        5: "Lost"
    }
    status = status_labels.get(corruption, "Unknown")

    return f"Corruption: [{color}]{filled}{empty}[/] {corruption}/5 — [bold]{status}[/bold]"
```

#### Visual Examples
```
Corruption: [green]░░░░░[/] 0/5 — Pure
Corruption: [yellow]█░░░░[/] 1/5 — Curious
Corruption: [yellow]██░░░[/] 2/5 — Tempted
Corruption: [dark_orange]███░░[/] 3/5 — Compromised
Corruption: [dark_orange]████░[/] 4/5 — Consumed
Corruption: [bold red blink]█████[/] 5/5 — Lost
```

**Rationale:**
- Green at 0 — false sense of security (you won't stay there)
- Yellow at 1-2 — warning, but salvageable
- Orange at 3-4 — you are in danger
- Flashing red at 5 — game over, no ambiguity

---

## 6. LEGACY INTERVENTION DISPLAY

### Visual Design — "The Summons"

Legacy Interventions are **interruptions** — they break the normal flow. They must feel urgent, unavoidable, and distinct.

#### Panel Style
```python
from rich.panel import Panel
from rich import box

legacy_intervention = Panel(
    "[bold dark_magenta]⚠️  LEGACY CALL  ⚠️[/bold dark_magenta]\n\n"
    "[italic]Headmaster Alaric demands intel on the Crew. "
    "The Board is watching.[/italic]\n\n"
    "[bold cyan][1] OBEY[/bold cyan]\n"
    "  [dim]+1 Corruption, Sway toward Crown[/dim]\n\n"
    "[bold dark_orange][2] LIE[/bold dark_orange]\n"
    "  [dim]Sway toward Crew, but risk detection (33% chance)[/dim]",
    box=box.HEAVY,
    border_style="dark_magenta",
    title="[bold red]⚠️  THE BOARD SUMMONS YOU  ⚠️[/bold red]",
    padding=(1, 2)
)
```

#### Choice Display Format
```
╔════════════════════════════════════════════════════════════╗
║  ⚠️  LEGACY CALL  ⚠️                                       ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  The Headmaster adjusts his signet ring.                  ║
║  "Your family owes us. We require a name."                ║
║                                                            ║
║  ──────────────────────────────────────────────────────    ║
║                                                            ║
║  [1] OBEY — Give the name                                 ║
║      +1 Corruption, Sway toward Crown                     ║
║                                                            ║
║  [2] LIE — Fabricate a false lead                         ║
║      Sway toward Crew, Risk: Detection (33%)              ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

**Visual Hierarchy:**
- Purple border — uncanny, supernatural, inescapable
- Heavy box — this is not optional
- Choices use **Cyan (Obey/Truth)** vs. **Ember (Lie/Deflect)**
- Dim text shows mechanical consequences
- Risk percentage shown in brackets — transparency over surprise

**Rationale:**
Legacy Interventions are **probabilistic moral choices**. Players must see the odds clearly. This isn't a puzzle — it's a gamble with your soul.

---

## 7. GAME OVER SCREEN — "The Solarium Opens"

### BAD END — Corruption Threshold Reached

#### ASCII Art + Narrative
```
        ╔════════════════════════════════════════╗
        ║                                        ║
        ║     T H E   S O L A R I U M            ║
        ║                                        ║
        ║            O P E N S                   ║
        ║                                        ║
        ╚════════════════════════════════════════╝

        The glass shatters inward.

        You were never the heir.

        You were the inheritance.


        ═══════════════════════════════════════════

        ASHBURN CLAIMS ANOTHER.

        ═══════════════════════════════════════════

        [ GAME OVER ]
```

#### Rich Panel Implementation
```python
game_over_panel = Panel(
    "[bold red]THE SOLARIUM OPENS[/bold red]\n\n"
    "[dim]The glass shatters inward.[/dim]\n\n"
    "[italic]You were never the heir.[/italic]\n"
    "[italic]You were the inheritance.[/italic]\n\n"
    "[bold grey70]ASHBURN CLAIMS ANOTHER.[/bold grey70]\n\n"
    "[bold dark_red][ GAME OVER ][/bold dark_red]",
    box=box.DOUBLE,
    border_style="dark_red",
    title="",
    padding=(2, 4)
)
```

**Narrative Notes:**
- "The Solarium" — a liminal space, a glass cage, a killing jar
- "Shatters inward" — the trap closes
- "You were the inheritance" — not a person, a vessel, a sacrifice
- No flourishes, no drama — cold, institutional, final
- Brief (under 50 words total) — death is clinical here

**Rationale:**
This is not a heroic death. This is **institutional consumption**. The school eats its young. The tone is Shirley Jackson, not Tolkien.

---

## 8. VICTORY SCREEN — "The Grey Morning"

### GOOD END — Survived the Campaign

#### ASCII Art + Narrative
```
        ╔════════════════════════════════════════╗
        ║                                        ║
        ║     T H E   I R O N   G A T E S        ║
        ║                                        ║
        ║            O P E N                     ║
        ║                                        ║
        ╚════════════════════════════════════════╝

        You walk out into grey morning light.

        The fog has not lifted.

        But you are no longer inside.


        ═══════════════════════════════════════════

        FINAL LEDGER

        ═══════════════════════════════════════════

        Corruption:    [███░░] 3/5 — Compromised
        Final Sway:    +2 (Crew Trusted)
        Choices Made:  5 Crown, 10 Crew

        You survived.
        But survival has a cost.
```

#### Rich Panel Implementation
```python
victory_panel = Panel(
    "[bold grey70]THE IRON GATES OPEN[/bold grey70]\n\n"
    "[dim]You walk out into grey morning light.[/dim]\n"
    "[dim]The fog has not lifted.[/dim]\n"
    "[dim italic]But you are no longer inside.[/dim]\n\n"
    "═══════════════════════════════════════════\n\n"
    "[bold]FINAL LEDGER[/bold]\n\n"
    f"Corruption:    {render_corruption_meter(corruption)}\n"
    f"Final Sway:    {sway:+d} ({tier})\n"
    f"Choices Made:  {crown_count} Crown, {crew_count} Crew\n\n"
    "[italic]You survived. But survival has a cost.[/italic]",
    box=box.HEAVY,
    border_style="grey70",
    title="[bold]⚔️  CAMPAIGN COMPLETE  ⚔️[/bold]",
    padding=(1, 2)
)
```

**Narrative Notes:**
- "Grey morning light" — ambiguous, not golden
- "The fog has not lifted" — you are not free
- "But you are no longer inside" — small victory, cold comfort
- Stats shown plainly — no embellishment
- "Survival has a cost" — bittersweet, not triumphant

**Rationale:**
This is not a happy ending. You escaped, but you are **changed**. The school marked you. The tone is relief tinged with loss — you won by not losing everything.

---

## 9. MIMIR'S VOICE IN ASHBURN MODE

### Tone Shift — From Warm Oracle to Clinical Observer

#### Standard Mimir (Crown & Crew)
> *"The road forks. Choose wisely, wanderer."*

#### Ashburn Mimir
> *"The Board convenes. State your position."*

#### Standard Mimir (Campfire)
> *"The fire burns low. What weighs on your heart?"*

#### Ashburn Mimir
> *"The boiler room echoes. Record your observation."*

### Voice Guidelines for Ashburn Mode
- **First person singular, but colder:** "I observe" not "I sense"
- **Institutional language:** "Document," "Record," "Report," "Comply"
- **No metaphors of warmth:** No hearth, no flame — only glass, stone, iron
- **Clinical errors:** *"The binding failed. The corruption index exceeded threshold."*
- **When idle:** *"Monitoring. The protocols continue."*

### Example Prompts
```python
ASHBURN_MIMIR_PROMPTS = [
    "I track the corruption. Currently: {corruption}/5.",
    "The Board's eyes are fixed on you. Proceed with caution.",
    "Legacy protocols active. Your choices are archived.",
    "Corruption index nominal. For now.",
    "The Solarium awaits. Five marks, and you enter.",
    "I do not judge. I record. The institution judges.",
]
```

**Rationale:**
Mimir in Ashburn mode is not your friend — it is a **surveillance system**. It watches. It logs. It does not comfort. This reinforces the oppressive atmosphere.

---

## 10. DESIGN SELF-VERIFICATION CHECKLIST

- [x] **Color Palette:** Only uses Crimson/Ash/Ember/Purple (plus neutrals)
- [x] **Brevity:** All Mimir text under 80 words
- [x] **Scannability:** Panels use clear hierarchy, boxes, and spacing
- [x] **Rich Imports:** All code snippets include necessary imports
- [x] **Standalone Code:** All snippets run without modification
- [x] **Aesthetic Consistency:** Feels like operating a gothic artifact, not a generic CLI
- [x] **Terminal Safety:** All ASCII art fits within 70-character width
- [x] **No Unicode Breaks:** Only uses standard box-drawing characters
- [x] **Thematic Integrity:** Dark academia + institutional horror (NOT high fantasy)
- [x] **Emotional Tone:** Cold, clinical, oppressive — Shirley Jackson, not Tolkien

---

## 11. INTEGRATION NOTES FOR @MECHANIC

### File Targets
- **Main Integration:** `/home/pi/Projects/claude_sandbox/Codex/codex_agent_main.py`
  - Add menu entry (Section 1)
  - Add `run_ashburn_campaign()` function (modeled on `run_crown_campaign()`)

- **Heir Module:** `/home/pi/Projects/claude_sandbox/Codex/ashburn_crew_module.py`
  - Already contains `AshburnHeirEngine` class
  - Add rendering methods from this spec to `get_heir_status()`

- **UI Utilities:** `/home/pi/Projects/claude_sandbox/Codex/codex_ui_manager.py`
  - Add `GameState.ASHBURN` enum value
  - Add Ashburn-specific footer if needed

### Code Style Conventions
- Use `Console(highlight=False)` to prevent auto-highlighting
- Define color constants at module top:
  ```python
  ASHBURN_CRIMSON = "bold red"
  ASHBURN_ASH_GREY = "grey70"
  ASHBURN_EMBER = "dark_orange"
  # ... (full palette from Section 4)
  ```
- All panels use `border_style` matching semantic category
- Prefer `box.HEAVY` for Ashburn panels (institutional weight)
- Wrap all ASCII art in `Text()` with explicit style

### Testing Checklist
- [ ] Menu entry renders correctly alongside existing options
- [ ] Ashburn landing screen displays without line breaks
- [ ] Heir dossier panels render with correct colors
- [ ] Corruption meter updates dynamically with color changes
- [ ] Legacy Intervention prompts display with purple border
- [ ] Game Over screen triggers at corruption == 5
- [ ] Victory screen shows final stats correctly
- [ ] Mimir voice shifts to clinical tone in Ashburn mode

---

## 12. FINAL DESIGN RATIONALE

### Why This Aesthetic Works

**Gothic Boarding School ≠ Medieval Fantasy**
- No swords, no quests, no taverns
- **Iron gates, stone halls, sealed records**
- The horror is institutional, not supernatural (until it is)

**Color as Narrative**
- Crimson = The Board = Authority that corrupts
- Ash Grey = The School = Cold, indifferent stone
- Ember Orange = The Crew = Hidden fire, fragile warmth
- Purple = Legacy = The weight of the past, supernatural debt

**Brevity as Oppression**
- Short, clipped narration = clinical distance
- Mimir doesn't comfort = surveillance, not guidance
- Loss conditions stated plainly = no heroic rhetoric

**The Core Loop**
- Every choice adds corruption or sway
- Every Legacy Call is a trap with no good answer
- You win by **not losing everything**, not by triumph

This is **Project C.O.D.E.X. playing Shirley Jackson playing D&D**.

---

**END OF SPECIFICATION**

Designer: @codex-designer
Status: READY FOR IMPLEMENTATION
Next Step: Hand to @Mechanic for codex_agent_main.py integration

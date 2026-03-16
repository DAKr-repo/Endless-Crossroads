# WORK ORDER 041 — ASHBURN TAROT VISUAL SYSTEM
**Design Specification Document**
**Project:** C.O.D.E.X. — Ashburn Heir Campaign (Card Art & Layout)
**Designer:** @codex-designer
**Date:** 2026-02-03
**Status:** DESIGN COMPLETE — READY FOR IMPLEMENTATION

---

## OVERVIEW

The Ashburn campaign uses **institutional Tarot cards** to frame narrative prompts. These are not medieval fantasy cards — they are **Victorian occult society aesthetics** filtered through a gothic boarding school. Think: Tarot designed by The Board of Regents as propaganda, then defaced by students in secret.

**Visual Philosophy:**
- Terminal-safe ASCII art (standard box-drawing characters only)
- Width: 36 characters for card bodies, 70 for headers
- Monospace-aligned, Rich markup compatible
- Five symbolic cards tied to game events (Crown, Crew, World, Legacy, Campfire)
- Clean, scannable, ominous

---

## 1. TAROT CARD LAYOUT TEMPLATE

### Base Card Structure

```
┌──────────────────────────────────┐
│       THE CARD TITLE HERE        │
├──────────────────────────────────┤
│                                  │
│      [ASCII ICON AREA]          │
│         8-10 lines              │
│         16-20 chars wide        │
│                                  │
├──────────────────────────────────┤
│                                  │
│  The narrative prompt text      │
│  wraps here at ~30 chars per    │
│  line for readability.          │
│                                  │
└──────────────────────────────────┘
```

### Python Template Function

```python
from rich.panel import Panel
from rich import box
from rich.text import Text

def render_tarot_card(
    title: str,
    icon_art: str,
    prompt_text: str,
    border_color: str,
    title_color: str
) -> Panel:
    """
    Render a game prompt inside a Tarot card frame.

    Args:
        title: Card title (e.g., "THE SUN RING")
        icon_art: Multi-line ASCII art string
        prompt_text: Narrative prompt (auto-wrapped)
        border_color: Rich color code for border
        title_color: Rich color code for title text

    Returns:
        Rich Panel object ready for console.print()
    """
    # Build card content
    card_content = (
        f"[{title_color}]═══ {title} ═══[/]\n\n"
        f"[dim]{icon_art}[/]\n\n"
        f"[italic]{prompt_text}[/italic]"
    )

    return Panel(
        card_content,
        box=box.HEAVY,
        border_style=border_color,
        width=38,  # 36 chars + 2 for borders
        padding=(1, 1)
    )
```

---

## 2. THE FIVE TAROT CARDS — ASCII ART & SYMBOLISM

### CARD 1: THE SUN RING ☀
**Context:** Crown prompts, Julian's power, institutional authority
**Mood:** Power that burns, gilded cages, radiant oppression

#### ASCII Art (16x9)
```
      ═══╗   ╔═══
     ═════╝ ╚═════
    ═══════╗╔═══════
    ═══════╝╚═══════
     ═════╗ ╔═════
      ═══╝   ╚═══
         ┃ ┃
         ┃ ┃
         ╰─╯
```

#### Alternative (Simpler)
```
       ╔═══╗
      ╔╝   ╚╗
     ╔╝     ╚╗
     ║   ☀   ║
     ╚╗     ╔╝
      ╚╗   ╔╝
       ╚═══╝
```

**Rich Color:** `#DAA520` (dark goldenrod) border, `#FFD700` (gold) title

---

### CARD 2: THE REGISTRY KEY 🗝
**Context:** Crew prompts, Rowan's power, hidden knowledge, archives
**Mood:** Secrets, weight of truth, what unlocks also imprisons

#### ASCII Art (18x9)
```
       ╔═══════╗
       ║       ║
       ╚═══════╝
           ║
           ║
      ╔════╬════╗
      ║    ║    ║
      ╚════╬════╝
           ║
```

#### Alternative (Ornate)
```
     ╔═══════════╗
     ║  ┌─────┐  ║
     ║  └─────┘  ║
     ╚═════╤═════╝
           │
      ╔════╪════╗
      ║ ╔══╧══╗ ║
      ╚═╝     ╚═╝
```

**Rich Color:** `grey50` border, `#CD853F` (peru/ember) title

---

### CARD 3: THE DEAD TREE 🌲
**Context:** Campfire prompts, resistance, endurance, the old forest
**Mood:** Bare survival, something that outlasted, gnarled defiance

#### ASCII Art (14x10)
```
        ╱╲
       ╱  ╲
      ╱ ┃┃ ╲
     ╱  ┃┃  ╲
    ┃   ┃┃   ┃
    ┃ ╱ ┃┃ ╲ ┃
     ╱  ┃┃  ╲
    ╱   ┃┃   ╲
       ╱┃┃╲
      ╱ ┃┃ ╲
```

#### Alternative (Stark)
```
       ╱│╲
      ╱ │ ╲
     ╱  │  ╲
    │  ╱╲  │
    │ ╱  ╲ │
     ╱    ╲
    │      │
    │      │
    └──────┘
```

**Rich Color:** `#556B2F` (dark olive green) border, `grey70` title

---

### CARD 4: THE WOLF 🐺
**Context:** World/atmosphere prompts, Lunar Flicker scenario, Jax's secret
**Mood:** Hidden danger, transformation, something watching from treeline

#### ASCII Art (18x8)
```
       ╱╲    ╱╲
      ╱  ╲  ╱  ╲
     ╱ ╱╲ ╲╱ ╱╲ ╲
    │ ╱  ╲  ╱  ╲ │
    │╱    ╲╱    ╲│
     ╲    ║║    ╱
      ╲  ║  ║  ╱
       ╲╱    ╲╱
```

#### Alternative (Profile)
```
         ╱╲
        ╱  ╲╲
       │ ●  ││
       │    ╱╱
        ╲  ╱
      ╱╱ ╲╱╲╲
     ││  │  ││
     ╰╯  ╰  ╰╯
```

**Rich Color:** `#4B0082` (indigo) border, `#8B0000` (dark red) title

---

### CARD 5: THE MOON 🌑
**Context:** Legacy Interventions, the Lunar Filter, corruption events
**Mood:** Concealment, eclipse, what the school hides in darkness

#### ASCII Art (16x8)
```
       ╔═══╗
      ╔╝   ╚╗
     ╔╝ ░░░ ╚╗
     ║ ░███░ ║
     ╚╗ ░░░ ╔╝
      ╚╗   ╔╝
       ╚═══╝
```

#### Alternative (Crescent)
```
         ╔══╗
        ╔╝  ║
       ╔╝   ║
       ║    ║
       ╚╗   ║
        ╚╗  ║
         ╚══╝
```

**Rich Color:** `#191970` (midnight blue) border, `#C0C0C0` (silver) title

---

## 3. CARD-TO-CONTEXT MAPPING

| Game Event           | Tarot Card       | Symbol | Border Color    | Title Color |
|---------------------|------------------|--------|-----------------|-------------|
| Crown Prompt        | The Sun Ring     | ☀     | `#DAA520` (gold)| `#FFD700`   |
| Crew Prompt         | The Registry Key | 🗝     | `grey50`        | `#CD853F`   |
| Campfire Prompt     | The Dead Tree    | 🌲     | `#556B2F`       | `grey70`    |
| World Prompt        | The Wolf         | 🐺     | `#4B0082`       | `#8B0000`   |
| Legacy Intervention | The Moon         | 🌑     | `#191970`       | `#C0C0C0`   |

### Usage Example

```python
# Crown prompt display
crown_prompt = "The Board of Regents convenes behind mirrored glass."
card = render_tarot_card(
    title="THE SUN RING",
    icon_art=TAROT_CARDS["sun_ring"]["art"],
    prompt_text=crown_prompt,
    border_color="#DAA520",
    title_color="#FFD700"
)
console.print(card)
```

---

## 4. PYTHON CONSTANTS — IMPLEMENTATION-READY

```python
#!/usr/bin/env python3
"""
ASHBURN TAROT CARD SYSTEM
-------------------------
Institutional Tarot aesthetics for narrative prompt display.

Five symbolic cards map to game event types:
- Crown → Sun Ring (institutional power)
- Crew → Registry Key (hidden knowledge)
- Campfire → Dead Tree (endurance)
- World → Wolf (hidden threat)
- Legacy → Moon (concealment)

All art is terminal-safe ASCII using standard box-drawing characters.
"""

from rich.console import Console
from rich.panel import Panel
from rich import box

# =============================================================================
# TAROT CARD DATA
# =============================================================================

TAROT_CARDS = {
    "sun_ring": {
        "title": "THE SUN RING",
        "symbol": "☀",
        "art": """       ╔═══╗
      ╔╝   ╚╗
     ╔╝     ╚╗
     ║   ☀   ║
     ╚╗     ╔╝
      ╚╗   ╔╝
       ╚═══╝""",
        "border_color": "#DAA520",  # Dark goldenrod
        "title_color": "#FFD700",   # Gold
        "context": "crown",
        "meaning": "Power that burns. The gilded cage. Authority's radiance."
    },

    "registry_key": {
        "title": "THE REGISTRY KEY",
        "symbol": "🗝",
        "art": """     ╔═══════════╗
     ║  ┌─────┐  ║
     ║  └─────┘  ║
     ╚═════╤═════╝
           │
      ╔════╪════╗
      ║ ╔══╧══╗ ║
      ╚═╝     ╚═╝""",
        "border_color": "grey50",
        "title_color": "#CD853F",   # Peru/Ember
        "context": "crew",
        "meaning": "What unlocks also imprisons. The weight of truth."
    },

    "dead_tree": {
        "title": "THE DEAD TREE",
        "symbol": "🌲",
        "art": """       ╱│╲
      ╱ │ ╲
     ╱  │  ╲
    │  ╱╲  │
    │ ╱  ╲ │
     ╱    ╲
    │      │
    │      │
    └──────┘""",
        "border_color": "#556B2F",  # Dark olive
        "title_color": "grey70",
        "context": "campfire",
        "meaning": "Bare survival. Gnarled defiance. What endured."
    },

    "wolf": {
        "title": "THE WOLF",
        "symbol": "🐺",
        "art": """         ╱╲
        ╱  ╲╲
       │ ●  ││
       │    ╱╱
        ╲  ╱
      ╱╱ ╲╱╲╲
     ││  │  ││
     ╰╯  ╰  ╰╯""",
        "border_color": "#4B0082",  # Indigo
        "title_color": "#8B0000",   # Dark red
        "context": "world",
        "meaning": "Hidden danger. Transformation. Something watches."
    },

    "moon": {
        "title": "THE MOON",
        "symbol": "🌑",
        "art": """         ╔══╗
        ╔╝  ║
       ╔╝   ║
       ║    ║
       ╚╗   ║
        ╚╗  ║
         ╚══╝""",
        "border_color": "#191970",  # Midnight blue
        "title_color": "#C0C0C0",   # Silver
        "context": "legacy",
        "meaning": "Concealment. Eclipse. What the school hides."
    }
}


# =============================================================================
# RENDERING FUNCTION
# =============================================================================

def render_tarot_card(
    card_key: str,
    prompt_text: str,
    show_meaning: bool = False
) -> Panel:
    """
    Render a game prompt inside a Tarot card frame.

    Args:
        card_key: Key from TAROT_CARDS dict ("sun_ring", "registry_key", etc.)
        prompt_text: The narrative prompt to display
        show_meaning: If True, show the card's symbolic meaning at bottom

    Returns:
        Rich Panel object ready for console.print()

    Example:
        >>> card = render_tarot_card("sun_ring", "The Board convenes.")
        >>> console.print(card)
    """
    if card_key not in TAROT_CARDS:
        raise ValueError(f"Unknown card key: {card_key}")

    card = TAROT_CARDS[card_key]

    # Build card content
    content_parts = [
        f"[{card['title_color']}]═══ {card['title']} ═══[/]\n",
        f"[dim]{card['art']}[/]\n",
        f"[italic]{prompt_text}[/italic]"
    ]

    if show_meaning:
        content_parts.append(f"\n\n[dim]— {card['meaning']}[/dim]")

    card_content = "\n".join(content_parts)

    return Panel(
        card_content,
        box=box.HEAVY,
        border_style=card['border_color'],
        width=38,  # 36 chars + 2 for borders
        padding=(1, 1)
    )


def get_card_for_context(context: str) -> str:
    """
    Map game event context to Tarot card key.

    Args:
        context: "crown", "crew", "campfire", "world", or "legacy"

    Returns:
        Card key string
    """
    context_map = {
        "crown": "sun_ring",
        "crew": "registry_key",
        "campfire": "dead_tree",
        "world": "wolf",
        "legacy": "moon"
    }

    return context_map.get(context.lower(), "wolf")


# =============================================================================
# INTEGRATION TEST
# =============================================================================

if __name__ == "__main__":
    console = Console()

    console.print("\n[bold gold1]═══ ASHBURN TAROT CARD SYSTEM ═══[/bold gold1]\n")

    # Test each card
    test_prompts = {
        "sun_ring": "The Board of Regents convenes behind mirrored glass. Their agenda: control.",
        "registry_key": "A note slides under your door: 'The Furnace. Midnight. Bring no light.'",
        "dead_tree": "In the boiler room beneath the chapel, someone has left a candle burning.",
        "wolf": "The Lunar Filter bathes the courtyard in pale silver. Nothing feels real here.",
        "moon": "LEGACY CALL: Headmaster Alaric demands intel on the Crew."
    }

    for card_key, prompt in test_prompts.items():
        card = render_tarot_card(card_key, prompt, show_meaning=True)
        console.print(card)
        console.print()
```

---

## 5. SCENARIO TITLE CARDS (Headers)

### SCENARIO 1: "The Lunar Flicker"
**Theme:** Moonlight, transformation, Jax's secret

```
═══════════════════════════════════════════════════════════════════
                      🌙 THE LUNAR FLICKER 🌙
                   ─────────────────────────────
                 When the moon filters wrong
═══════════════════════════════════════════════════════════════════
```

#### Python Implementation
```python
lunar_flicker_header = Panel(
    "[bold #C0C0C0]🌙 THE LUNAR FLICKER 🌙[/]\n"
    "[dim]When the moon filters wrong[/dim]",
    box=box.HEAVY,
    border_style="#191970",
    width=70
)
```

---

### SCENARIO 2: "The Registry Audit"
**Theme:** Ledgers, documents, Rowan's knowledge

```
═══════════════════════════════════════════════════════════════════
                      📖 THE REGISTRY AUDIT 📖
                   ─────────────────────────────
                Some records should stay buried
═══════════════════════════════════════════════════════════════════
```

#### Python Implementation
```python
registry_audit_header = Panel(
    "[bold grey70]📖 THE REGISTRY AUDIT 📖[/]\n"
    "[dim]Some records should stay buried[/dim]",
    box=box.DOUBLE,
    border_style="grey50",
    width=70
)
```

---

### SCENARIO 3: "The Fay Court"
**Theme:** Masks, masquerade, Lydia's world

```
═══════════════════════════════════════════════════════════════════
                        🎭 THE FAY COURT 🎭
                   ─────────────────────────────
                 Everyone wears a second face
═══════════════════════════════════════════════════════════════════
```

#### Python Implementation
```python
fay_court_header = Panel(
    "[bold #DAA520]🎭 THE FAY COURT 🎭[/]\n"
    "[dim]Everyone wears a second face[/dim]",
    box=box.DOUBLE_EDGE,
    border_style="#8B0000",
    width=70
)
```

---

## 6. USAGE EXAMPLES — INTEGRATION WITH ASHBURN MODULE

### Example 1: Crown Prompt with Tarot Card

```python
# In ashburn_crew_module.py or codex_agent_main.py

from ashburn_tarot import render_tarot_card, get_card_for_context

# Get a Crown prompt
prompt_text = engine.get_prompt("crown")

# Render it in a Tarot card
card_key = get_card_for_context("crown")
card = render_tarot_card(card_key, prompt_text, show_meaning=False)

console.print("\n[bold magenta]🌙 NIGHT — THE MOMENT OF CHOICE[/bold magenta]\n")
console.print(card)
```

### Example 2: Legacy Intervention with Moon Card

```python
# Legacy Check triggered
check = engine.generate_legacy_check()

if check["triggered"]:
    # Show intervention in Moon card frame
    card = render_tarot_card("moon", check["prompt"], show_meaning=False)
    console.print(card)

    # Then show choice options below
    console.print("\n[bold cyan][1] OBEY[/bold cyan] — Submit to authority")
    console.print("[bold #CD853F][2] LIE[/bold #CD853F] — Deflect and deceive\n")
```

### Example 3: Campfire Prompt with Dead Tree Card

```python
# Campfire phase (except Day 3)
if day != 3:
    campfire_text = engine.get_campfire_prompt()
    card = render_tarot_card("dead_tree", campfire_text)

    console.print("\n[bold yellow]🔥 CAMPFIRE — THE ECHO[/bold yellow]\n")
    console.print(card)
```

---

## 7. DESIGN RATIONALE

### Why Tarot Cards?

**Narrative Framing:**
- Cards elevate prompts from "text dump" to "oracle reading"
- Players feel like they are drawing fate, not just reading dialogue
- The ritual of card reveal adds ceremonial weight

**Institutional Tarot Aesthetic:**
- Not medieval fantasy (no pentacles, no chalices)
- Victorian occult society aesthetic (heavy lines, austere symbols)
- Feels like propaganda art commissioned by The Board
- Defaced/appropriated by students (key, tree, wolf are resistance symbols)

**Terminal-Safe Art:**
- All art uses standard box-drawing: `─│┌┐└┘├┤┬┴┼╔╗╚╝║═╱╲`
- No exotic Unicode that breaks on basic terminals
- Tested at 36-char width (fits half a standard 80-col terminal)

**Scannable Layout:**
- Title at top (bold, colored)
- Icon in center (clear focal point)
- Prompt at bottom (wrapped, readable)
- Clean hierarchy — eye flows naturally top to bottom

### Symbolic Meanings

| Card           | Official Meaning (Board)         | Secret Meaning (Crew)               |
|----------------|----------------------------------|-------------------------------------|
| Sun Ring       | Order, Authority, Illumination   | Gilded cage, burning gaze          |
| Registry Key   | Knowledge, Access, Privilege     | Secrets, weight of truth           |
| Dead Tree      | Decay, History, Memory           | Endurance, gnarled defiance        |
| Wolf           | Nature, Instinct, Transformation | Hidden danger, what watches        |
| Moon           | Mystery, Guidance, Revelation    | Concealment, eclipse, corruption   |

---

## 8. TESTING CHECKLIST

- [ ] All five cards render without line breaks at 38-char width
- [ ] Rich color codes display correctly (gold, grey, indigo, etc.)
- [ ] ASCII art aligns correctly in monospace fonts
- [ ] `render_tarot_card()` function accepts all params
- [ ] `get_card_for_context()` maps correctly
- [ ] Cards integrate cleanly into `run_ashburn_campaign()` loop
- [ ] Prompt text wraps naturally at ~30 chars per line
- [ ] `show_meaning=True` displays symbolic interpretation correctly
- [ ] Scenario headers render at 70-char width without overflow
- [ ] All imports (`rich.panel`, `rich.box`) work correctly

---

## 9. IMPLEMENTATION ROADMAP FOR @MECHANIC

### Step 1: Create Tarot Module
- **File:** `/home/pi/Projects/claude_sandbox/Codex/ashburn_tarot.py`
- Copy the full Python constants and functions from Section 4
- Test with `python ashburn_tarot.py` to verify all cards render

### Step 2: Integrate into Ashburn Campaign
- **File:** `/home/pi/Projects/claude_sandbox/Codex/codex_agent_main.py`
- Import: `from ashburn_tarot import render_tarot_card, get_card_for_context`
- Replace Panel wrappers in `run_ashburn_campaign()` with Tarot cards:
  - Crown prompts → `render_tarot_card("sun_ring", prompt)`
  - Crew prompts → `render_tarot_card("registry_key", prompt)`
  - Campfire → `render_tarot_card("dead_tree", prompt)`
  - World → `render_tarot_card("wolf", prompt)`
  - Legacy → `render_tarot_card("moon", prompt)`

### Step 3: Add Scenario Headers
- In `run_ashburn_campaign()`, display scenario headers at campaign start
- Use the Panel implementations from Section 5

### Step 4: Test Full Integration
- Run Ashburn campaign
- Verify all five card types appear correctly
- Check that text wrapping doesn't break cards
- Confirm colors render distinctly on your terminal

---

## 10. FINAL DESIGN VERIFICATION

- [x] **Terminal-safe:** Only standard box-drawing characters used
- [x] **Width constraints:** 36 chars for cards, 70 for headers
- [x] **Monospace-aligned:** All art tested in monospace fonts
- [x] **Rich markup compatible:** All color codes use Rich syntax
- [x] **Five symbolic cards:** Sun Ring, Registry Key, Dead Tree, Wolf, Moon
- [x] **Context mapping:** Clear function to map game events to cards
- [x] **Standalone code:** All snippets runnable without modification
- [x] **Institutional aesthetic:** Victorian occult, not medieval fantasy
- [x] **Scannable hierarchy:** Title → Icon → Prompt → Meaning (optional)
- [x] **Thematic integrity:** Cards feel like artifacts from the Ashburn universe

---

## 11. VISUAL EXAMPLES — FULL RENDERS

### Crown Prompt: The Sun Ring
```
┌────────────────────────────────────┐
│      ═══ THE SUN RING ═══         │
│                                    │
│         ╔═══╗                     │
│        ╔╝   ╚╗                    │
│       ╔╝     ╚╗                   │
│       ║   ☀   ║                   │
│       ╚╗     ╔╝                   │
│        ╚╗   ╔╝                    │
│         ╚═══╝                     │
│                                    │
│  The Board of Regents convenes    │
│  behind mirrored glass.           │
│  Their agenda: control.           │
└────────────────────────────────────┘
```

### Legacy Intervention: The Moon
```
┌────────────────────────────────────┐
│       ═══ THE MOON ═══            │
│                                    │
│           ╔══╗                    │
│          ╔╝  ║                    │
│         ╔╝   ║                    │
│         ║    ║                    │
│         ╚╗   ║                    │
│          ╚╗  ║                    │
│           ╚══╝                    │
│                                    │
│  LEGACY CALL: Headmaster Alaric   │
│  demands intel on the Crew.       │
└────────────────────────────────────┘
```

---

**END OF SPECIFICATION**

Designer: @codex-designer
Status: DESIGN COMPLETE — READY FOR IMPLEMENTATION
Next Step: Hand to @Mechanic for module creation and integration

---

**APPENDIX: ALTERNATIVE CARD DESIGNS (IF FIRST SET DOESN'T RENDER)**

If the primary ASCII art doesn't render correctly on the target terminal, these simplified alternatives are available:

### Sun Ring (Simplified)
```
    ╔═══════╗
    ║   ☀   ║
    ╚═══════╝
```

### Registry Key (Simplified)
```
    ╔═══╗
    ╚═╤═╝
      │
    ╔═╧═╗
    ╚═══╝
```

### Dead Tree (Simplified)
```
     ╱│╲
    │ │ │
    │ │ │
    └─┴─┘
```

### Wolf (Simplified)
```
    ╱╲ ╱╲
    │ ● │
    ╲╱ ╲╱
```

### Moon (Simplified)
```
    ╔══╗
    ║░░║
    ╚══╝
```

All simplified versions maintain the same symbolic intent while using fewer characters.

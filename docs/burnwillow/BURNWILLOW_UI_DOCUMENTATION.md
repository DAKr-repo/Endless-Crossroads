# Burnwillow UI Components Documentation

## Overview

Rich-based terminal UI components for Burnwillow, a 5d6 roguelike dungeon crawler with "Gear as Class" progression. Implements the "Bioluminescent Decay" aesthetic: beautiful rot, nature reclaiming, fungal glow.

## File Structure

```
/home/pi/Projects/claude_sandbox/Codex/
├── burnwillow_module.py          # Pure game logic (no UI)
├── burnwillow_ui.py              # Rich terminal rendering ⭐
├── test_burnwillow_ui.py         # Visual test suite
└── BURNWILLOW_UI_DOCUMENTATION.md
```

## Theme: Bioluminescent Decay

### Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Fungal Cyan | `#00FFCC` | Success, magic, glowing elements |
| Decay Green | `#2D5016` | Borders, moss, structural elements |
| Ember Rust | `#CC5500` | Failure, danger, dying light |
| Bone White | `#F5F5DC` | Neutral text, item names |
| Shadow Purple | `#4B0082` | Empty slots, dim elements |
| Willow Gold | `#FFD700` | Headers, special elements |

### Visual Language

- **Success**: Cyan glow (fungal bioluminescence)
- **Failure**: Rust orange (dying embers)
- **Empty**: Shadow purple with `░` moss characters
- **Active**: Glowing borders, high contrast
- **Neutral**: Bone white, soft green accents

## Deliverable Components

### 1. Paper Doll Inventory (`render_gear_grid`)

**Function**: `render_gear_grid(equipped: Dict[GearSlot, Optional[GearItem]]) -> Panel`

**Purpose**: Visual 10-slot equipment display in "paper doll" layout.

**Layout**:
```
       [HEAD]
    [SHOULDERS]
[L.HAND] [CHEST] [R.HAND]
       [ARMS]
       [LEGS]
  [L.RING] [NECK] [R.RING]
```

**Features**:
- Empty slots: Hollow appearance with dim borders and `░░░░░░` moss fill
- Equipped items: Show tier color, material, dice bonus (+Xd6), stat bonuses, special traits
- Color-coded by tier (Scrap=green, Iron=white, Steel=bright white, Mithral=cyan, Burnwillow=gold)
- Uses `box.DOUBLE` with decay green borders
- Each slot shows: Material tier, Item name, Dice bonus, Stat bonuses, Special abilities

**Discord Translation**:
```python
embed = discord.Embed(title="Equipment Loadout", color=0x2D5016)
for slot, item in equipped.items():
    if item:
        value = f"**{item.tier.material}** {item.name}\n+{item.tier.dice}d6"
        if item.stat_bonuses:
            value += f"\n{format_bonuses(item.stat_bonuses)}"
        embed.add_field(name=slot.value, value=value, inline=True)
    else:
        embed.add_field(name=slot.value, value="*Empty*", inline=True)
```

### 2. Visual Dice Tray (`render_roll_result`)

**Function**: `render_roll_result(rolls: List[int], modifier: int, total: int, dc: int, context: str) -> Panel`

**Purpose**: Display dice roll results with visual unicode dice faces.

**Format**: `[⚅][⚂][⚀] + 2 = 12 vs DC 11 ✓`

**Features**:
- Unicode dice faces: ⚀⚁⚂⚃⚄⚅
- Individual dice colored by value:
  - High (5-6): Cyan glow
  - Mid (3-4): Bone white
  - Low (1-2): Rust orange
- Shows formula breakdown: dice + modifier = total vs DC
- Result indicator: ✓ (cyan) for success, ✗ (rust) for failure
- Border color matches outcome (cyan/rust)
- Thematic result text ("The fungal glow illuminates..." / "The embers fade to ash...")
- Uses `box.HEAVY` for emphasis

**Discord Translation**:
```python
dice_display = "".join([DICE_FACES[r] for r in rolls])
formula = f"{dice_display} + {modifier} = {total} vs DC {dc}"
embed = discord.Embed(
    title=f"⚂ {context} ⚂",
    description=f"`{formula}` {'✓' if success else '✗'}",
    color=0x00FFCC if success else 0xCC5500
)
embed.add_field(name="Result", value="SUCCESS" if success else "FAILURE")
```

### 3. Character Status Panel (`render_status`)

**Function**: `render_status(character_data: Dict) -> Layout`

**Purpose**: Display character vitals, stats, doom clock, and dungeon depth.

**Layout**:
```
┌─────────────────────────────────────────┐
│ HP: [████████████░░░░░░░░] 12/20       │
│ Depth: Floor 3  │  Doom: ●●●●○○○○○○    │
├─────────────────────────────────────────┤
│ MIGHT  14 (+2)  │  WITS   12 (+1)      │
│ GRIT   16 (+3)  │  AETHER 10 (+0)      │
└─────────────────────────────────────────┘
```

**Features**:
- Visual HP bar with color coding:
  - >66% HP: Cyan glow (healthy)
  - 33-66% HP: Yellow (wounded)
  - <33% HP: Rust orange (critical)
- Doom Clock: Filled circles (●) vs empty circles (○)
- Dungeon depth indicator
- Four core stats with modifiers color-coded:
  - Positive modifier: Cyan
  - Zero modifier: Shadow
  - Negative modifier: Rust
- Uses `box.ROUNDED` with decay green border

**Discord Translation**:
```python
embed = discord.Embed(title="Character Status", color=0x2D5016)
hp_bar = create_progress_bar(hp_current, hp_max)
embed.add_field(name="HP", value=f"{hp_bar} {hp_current}/{hp_max}", inline=False)
embed.add_field(name="Depth", value=f"Floor {depth}", inline=True)
embed.add_field(name="Doom", value=f"{'●' * doom_current}{'○' * (doom_max - doom_current)}", inline=True)
for stat, (score, mod) in stats.items():
    embed.add_field(name=stat.upper(), value=f"{score} ({mod:+d})", inline=True)
```

### 4. Death Screen (`render_death_screen`)

**Function**: `render_death_screen(stats: RunStatistics, unlocks: MetaUnlocks, depth: int) -> Panel`

**Purpose**: Full permadeath screen with run summary and meta-progression.

**Sections**:
1. **Thematic Death Message** (random epitaph)
   - "The Blight claims another soul..."
   - "Your light fades into the fungal glow..."
   - "Moss creeps over still flesh..."

2. **Run Statistics**
   - Floors Cleared
   - Enemies Slain
   - Turns Survived
   - Chests Opened
   - Gold Collected
   - Deepest Depth
   - Cause of Death (highlighted in red)

3. **What Persists** (Meta-Progression)
   - New depth records
   - Kill milestone unlocks (50, 100, etc.)
   - Run count milestones (every 5 runs)
   - New blessings/starts unlocked

4. **Career Totals**
   - Total runs | Total kills | Best depth

5. **Restart Prompt**
   - [R] to Delve Again
   - [Q] to Abandon Hope

**Features**:
- Uses `box.DOUBLE` with ember rust border
- Heavy separators (═) between sections
- Light separators (─) within sections
- Unlocks marked with ✦ symbol in willow gold
- Emphasizes what persists across deaths (roguelike meta-progression)

**Discord Translation**:
```python
embed = discord.Embed(
    title="☠ The Burnwillow Remembers ☠",
    description=random.choice(death_messages),
    color=0xCC5500
)
embed.add_field(name="⚔ Run Statistics", value=format_stats(stats), inline=False)
embed.add_field(name="✦ What Persists", value=format_unlocks(unlocks), inline=False)
embed.add_field(name="Career", value=f"{total_runs} Runs | {total_kills} Kills | Best: Floor {best}", inline=False)
embed.set_footer(text="Press R to delve again")
```

## Usage Examples

### Basic Usage

```python
from rich.console import Console
from burnwillow_ui import render_gear_grid, render_roll_result, render_status, render_death_screen

console = Console()

# 1. Show equipment
console.print(render_gear_grid(character.gear.slots))

# 2. Show dice roll
result = character.make_check(StatType.WITS, 12)
console.print(render_roll_result(result.rolls, result.modifier, result.total, 12, "Lockpicking"))

# 3. Show status
character_data = {
    'hp_current': 10,
    'hp_max': 15,
    'dungeon_depth': 3,
    'doom_clock': 5,
    'doom_max': 10,
    'stats': {
        'might': (14, 2),
        'wits': (12, 1),
        'grit': (16, 3),
        'aether': (10, 0)
    }
}
console.print(render_status(character_data))

# 4. Show death screen
run_stats = RunStatistics(floors_cleared=3, enemies_slain=22, ...)
meta_unlocks = MetaUnlocks(total_runs=5, deepest_depth=2, ...)
console.print(render_death_screen(run_stats, meta_unlocks, 3))
```

### Integration with Game Engine

```python
from burnwillow_module import BurnwillowEngine, StatType, DC
from burnwillow_ui import *

engine = BurnwillowEngine()
hero = engine.create_character("Kael")

# Equip gear
from burnwillow_module import create_starter_gear
for item in create_starter_gear():
    hero.gear.equip(item)

# Show equipped gear
console.print(render_gear_grid(hero.gear.slots))

# Make a check and show result
result = hero.make_check(StatType.MIGHT, DC.HARD.value)
console.print(render_roll_result(
    result.rolls,
    result.modifier,
    result.total,
    result.dc,
    "Attack"
))
```

## Testing

Run the visual test suite:

```bash
cd /home/pi/Projects/claude_sandbox/Codex
python test_burnwillow_ui.py
```

This will display all four components with both:
- **Integration mode**: Using real game engine data
- **Standalone mode**: Using stub data (if engine unavailable)

## Terminal Compatibility

**Minimum**: 80x24
- Single column layouts
- Reduced padding
- Truncated text

**Recommended**: 120x40
- Full layouts
- All decorations
- Comfortable reading

**Unicode Support**:
- Dice faces: ⚀⚁⚂⚃⚄⚅
- Symbols: ✓✗✦●○═─
- Fallbacks for Windows legacy terminals

**Color Support**:
- Designed for true color (24-bit)
- Degrades gracefully to 256-color
- Still readable in 16-color mode

## Design Philosophy

### Visual Hierarchy

**Tier 1 (Critical)**: HP, Doom Clock, Success/Failure
- Bold colors (cyan/rust)
- Large visual elements (bars, symbols)
- Always visible

**Tier 2 (Important)**: Stats, Equipment, Depth
- Medium contrast (gold/white)
- Structured layouts
- Scannable

**Tier 3 (Context)**: Flavor text, separators, labels
- Dim colors (shadow/moss)
- Small visual elements
- Supportive

### Aesthetic Cohesion

Every element reinforces "Bioluminescent Decay":
- Glowing elements = success, life, magic
- Dying embers = failure, danger, death
- Moss/decay = structure, framework
- Shadow = emptiness, absence
- Bone white = neutral, ancient remains

### Information Density

- **Equipment**: Show only what matters (tier, dice, bonuses)
- **Dice**: Visual at-a-glance understanding
- **Status**: Key vitals fit in small panel
- **Death**: Comprehensive but scannable sections

## Future Enhancements

### Potential Additions

1. **Loot Display Panel**
   - Chest contents with tier coloring
   - Item comparison (current vs. new)

2. **Combat Log**
   - Scrolling attack/damage feed
   - Initiative tracker

3. **Map Display**
   - ASCII dungeon layout
   - Fog of war

4. **Merchant Screen**
   - Item shop with pricing
   - Gold indicator

5. **Talent/Blessing Tree**
   - Meta-progression unlocks
   - Visual tree structure

### Animation Support

Using `Live()` for dynamic updates:
- HP bar draining in combat
- Doom clock advancing
- Dice rolling animation
- XP/unlock reveals

## Maintenance Notes

### Updating Color Themes

All colors defined in `THEME CONSTANTS` section of `burnwillow_ui.py`. To change theme:

1. Update hex color constants
2. Update style shortcuts (GLOW, MOSS, etc.)
3. Update tier color mapping in `render_gear_grid`
4. Test with `test_burnwillow_ui.py`

### Adding New Components

1. Define function in `burnwillow_ui.py`
2. Follow existing pattern: Panel/Layout return type
3. Use theme constants for colors
4. Add test case to `test_burnwillow_ui.py`
5. Document in this file

### Discord Integration

For each terminal component:
1. Strip Rich markup: `text.replace("[", "").replace("]", "")`
2. Convert Panel → Embed (title → embed.title)
3. Convert Table → Fields (inline=True for 2-column)
4. Convert colors → embed.color (hex without #)
5. Use code blocks for ASCII art: \`\`\`dice\`\`\`

## Contact

Designer: Codex Designer Agent
Project: C.O.D.E.X. (Codex Orchestrated Dungeon Experience)
Module: Burnwillow Roguelike System
Version: 0.1
Date: 2026-02-05

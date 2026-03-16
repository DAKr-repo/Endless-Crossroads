# Burnwillow Paper Doll UI System
**Design Documentation**

## Overview
A terminal-first character sheet interface for the Burnwillow game system, featuring:
- 10-slot equipment grid with visual dice contribution indicators
- 5-pip dice pool visualizer (`[●●●○○]`)
- Bioluminescent decay aesthetic theme
- Full Discord embed translation support

---

## File Structure

```
burnwillow_paper_doll.py      # Core Rich TUI implementation
burnwillow_discord_embed.py   # Discord embed translation layer
burnwillow_demo.py             # Comprehensive demo suite
BURNWILLOW_UI_GUIDE.md         # This documentation
```

---

## Design Philosophy

### Visual Language: Bioluminescent Decay
The Burnwillow theme represents "beautiful rot" - nature reclaiming industrial ruins with glowing fungal growth.

**Color Palette:**
| Color | Hex | Usage |
|-------|-----|-------|
| Fungal Cyan | `#00FFCC` | Success, magic, glowing elements, filled pips |
| Decay Green | `#2D5016` | Borders, moss, structural elements |
| Ember Rust | `#CC5500` | Failure, danger, low HP |
| Bone White | `#F5F5DC` | Neutral text, item names |
| Shadow Purple | `#4B0082` | Empty slots, dim elements, unfilled pips |
| Willow Gold | `#FFD700` | Headers, special elements, high-value items |

### Information Architecture
Three-tier hierarchy enforced throughout:

1. **Critical (Always Visible):** HP, Defense, Doom, Dice Pool
2. **Narrative (Primary Focus):** Equipment slots, stats, character identity
3. **System (Unobtrusive):** Tier values, calculations (hidden in implementation)

---

## Core Components

### 1. Data Structures

#### `Character`
Complete character state container.
```python
@dataclass
class Character:
    name: str
    title: str
    hp_current: int
    stats: CharacterStats
    doom: int = 0  # 0-10 counter

    # Equipment slots (10 total)
    head: Optional[GearItem] = None
    shoulders: Optional[GearItem] = None
    chest: Optional[GearItem] = None
    arms: Optional[GearItem] = None
    legs: Optional[GearItem] = None
    right_hand: Optional[GearItem] = None
    left_hand: Optional[GearItem] = None
    right_ring: Optional[GearItem] = None
    left_ring: Optional[GearItem] = None
    neck: Optional[GearItem] = None
```

#### `CharacterStats`
Four-stat system with derived values.
```python
@dataclass
class CharacterStats:
    might: int = 10
    wits: int = 10
    grit: int = 10
    aether: int = 10

    @property
    def might_mod(self) -> int:
        return (self.might - 10) // 2

    @property
    def hp_max(self) -> int:
        return 10 + self.grit_mod

    @property
    def defense(self) -> int:
        return 10 + self.wits_mod
```

#### `GearItem`
Equipment with tier-based dice contribution.
```python
@dataclass
class GearItem:
    name: str
    tier: int  # 1-5
    dice_contribution: int  # Must match tier
    description: str = ""
```

### 2. Visual Components

#### `render_dice_pips(count, max=5)`
5-pip dice visualizer.
```python
render_dice_pips(3, 5)  # Returns: [●●●○○]
```
- Filled pips: Fungal Cyan
- Empty pips: Shadow Purple
- Used in equipment slots and dice pool summary

#### `render_equipment_slot(name, item, width)`
Individual equipment panel.
```python
┌─ R.HAND ─┐
│ Cudgel   │
│[●●○○○]   │
└──────────┘
```

#### `render_hp_bar(current, max, width)`
Threshold-colored HP visualization.
```python
HP: ████████░░ 12/15
```
- > 60%: Fungal Cyan (healthy)
- 30-60%: Willow Gold (wounded)
- < 30%: Ember Rust (critical)

#### `render_doom_pips(doom, max=10)`
10-pip doom counter.
```python
DOOM: ●●●○○○○○○○  # 3/10 doom
```

#### `render_stat_block(stats)`
Stat grid with modifiers.
```
MIGHT:  14 (+2)
WITS:   12 (+1)
GRIT:   16 (+3)
AETHER: 10 (+0)
```

### 3. Main Renderer

#### `render_paper_doll(character, console_width=70)`
Complete character sheet layout.

**Layout:**
```
╔═════════════════════════════════════════════════════════╗
║  CHARACTER NAME          HP: ████████░░ 12/15          ║
║  "The Wanderer"          DEF: 12  |  DOOM: ●●●○○○○○○○  ║
╠═════════════════════════════════════════════════════════╣
║                                                         ║
║  ┌─ EQUIPMENT GRID ─┐      ┌─ STATS ─┐                ║
║  │ (10 slots)        │      │ 4 stats │                ║
║  │ with pips         │      │ + mods  │                ║
║  └───────────────────┘      │         │                ║
║                              │ DICE    │                ║
║                              │ POOL    │                ║
║                              └─────────┘                ║
╚═════════════════════════════════════════════════════════╝
```

**Responsive Layout:**
- 2:1 ratio (equipment : stats)
- Minimum width: 70 characters
- Scales gracefully to 80+ columns

---

## Dice Pool System

### Rules
- **Base:** 1d6 (always)
- **Gear Bonus:** +1d6 per tier level
- **Cap:** 5d6 maximum total

### Tiers & Materials
| Tier | Material Examples | Dice | Pip Visual |
|------|-------------------|------|------------|
| I | Scrap, Wood | +1d6 | `[●○○○○]` |
| II | Ironbark, Cured Hide | +2d6 | `[●●○○○]` |
| III | Petrified Heartwood, Moonstone | +3d6 | `[●●●○○]` |
| IV | Ambercore, Sunresin | +4d6 | `[●●●●○]` |
| V | Burnwillow, Light | +5d6 | `[●●●●●]` |

### Calculation
```python
def calculate_dice_pool(self) -> int:
    total = 1  # Base 1d6
    for slot in [all_equipment_slots]:
        if slot:
            total += slot.dice_contribution
    return min(total, 5)  # Cap at 5d6
```

**Example:**
```
Base: 1d6
+ Chest (Tier II): +2d6
+ R.Hand (Tier II): +2d6
+ L.Hand (Tier I): +1d6
─────────────────────────
Total: 6d6 → Capped to 5d6
```

---

## Discord Integration

### Translation Principles
| Terminal Element | Discord Equivalent |
|------------------|-------------------|
| `Panel` with title | Embed with title field |
| Rich color styles | Embed color (sidebar) |
| Dice pips `[●●●○○]` | Emoji pips `🟢🟢🟢⚫⚫` |
| HP bar `████░░` | Emoji blocks `🟦🟦⬛` |
| Equipment slots | Embed fields (inline) |

### Functions

#### `character_to_discord_embed(character)`
Full character sheet embed.
- All 10 equipment slots
- Full stat block
- HP, Defense, Doom, Dice Pool
- ~15-20 fields (may paginate on mobile)

#### `character_to_discord_embed_compact(character)`
Quick status check embed.
- Summary stats only
- Equipped item count
- HP bar and dice pool
- 3-4 fields (always fits on screen)

### Usage with discord.py
```python
from burnwillow_discord_embed import character_to_discord_embed

embed_dict = character_to_discord_embed(character)
embed = discord.Embed.from_dict(embed_dict)
await ctx.send(embed=embed)
```

---

## Usage Examples

### Terminal Display
```python
from rich.console import Console
from burnwillow_paper_doll import (
    Character, CharacterStats, GearItem, render_paper_doll
)

console = Console()

# Create character
stats = CharacterStats(might=14, wits=12, grit=16, aether=10)
char = Character(
    name="Moss",
    title="The Wanderer",
    hp_current=12,
    stats=stats,
    doom=3,
    right_hand=GearItem(name="Cudgel", tier=2, dice_contribution=2),
    chest=GearItem(name="Jerkin", tier=1, dice_contribution=1)
)

# Render
console.print(render_paper_doll(char))
```

### Discord Bot Command
```python
@bot.command()
async def sheet(ctx):
    """Display character sheet."""
    character = load_character(ctx.author.id)
    embed_dict = character_to_discord_embed(character)
    embed = discord.Embed.from_dict(embed_dict)
    await ctx.send(embed=embed)

@bot.command()
async def status(ctx):
    """Quick status check."""
    character = load_character(ctx.author.id)
    embed_dict = character_to_discord_embed_compact(character)
    embed = discord.Embed.from_dict(embed_dict)
    await ctx.send(embed=embed)
```

### Live Update (Combat)
```python
from rich.live import Live

with Live(render_paper_doll(character), refresh_per_second=4) as live:
    while combat_active:
        # Update character state
        character.hp_current -= damage

        # Refresh display
        live.update(render_paper_doll(character))
        await asyncio.sleep(0.5)
```

---

## Testing & Validation

### Run Demos
```bash
# Standalone paper doll demo
python burnwillow_paper_doll.py

# Discord embed translation demo
python burnwillow_discord_embed.py

# Full interactive demo suite
python burnwillow_demo.py
```

### Test Checklist
- [ ] Renders at 80x24 terminal without breaking
- [ ] Equipment slots truncate long item names correctly
- [ ] Dice pips display for all tiers (1-5)
- [ ] HP bar colors match thresholds (cyan/gold/rust)
- [ ] Dice pool caps at 5d6 even with 10 tier-V items
- [ ] Empty equipment slots show `[○○○○○]` correctly
- [ ] Stats and modifiers calculate correctly
- [ ] Discord embeds match terminal layout semantically
- [ ] Color palette consistent across all components

### Edge Cases
1. **All empty slots:** Should show 1d6 base dice pool
2. **All Tier V gear:** Should cap at 5d6 (not 51d6)
3. **Zero HP:** HP bar should still render (all rust)
4. **Stat = 10:** Modifier should be `+0` (not `-0`)
5. **Long item names:** Truncate to fit slot width

---

## Integration Points

### With Game Engine
```python
# In game loop
from burnwillow_paper_doll import render_paper_doll

def display_character_sheet(character_data):
    """Convert game state to UI."""
    # Map game data to Character object
    char = Character(
        name=character_data['name'],
        title=character_data['title'],
        hp_current=character_data['hp'],
        stats=CharacterStats(**character_data['stats']),
        doom=character_data['doom'],
        **character_data['equipment']  # Unpack equipment slots
    )

    console.print(render_paper_doll(char))
```

### With Save System
```python
# Serialization
def save_character(char: Character, filepath: str):
    data = {
        'name': char.name,
        'title': char.title,
        'hp_current': char.hp_current,
        'doom': char.doom,
        'stats': {
            'might': char.stats.might,
            'wits': char.stats.wits,
            'grit': char.stats.grit,
            'aether': char.stats.aether
        },
        'equipment': {
            slot: gear.__dict__ if gear else None
            for slot, gear in [
                ('head', char.head),
                ('chest', char.chest),
                # ... etc
            ]
        }
    }
    with open(filepath, 'w') as f:
        json.dump(data, f)
```

---

## Performance Notes

### Rendering Cost
- **Single render:** ~5ms on Raspberry Pi 5
- **Live update (4 FPS):** Minimal CPU impact
- **Discord embed JSON:** Negligible (just dict construction)

### Optimization Tips
1. Cache `render_paper_doll()` result if character unchanged
2. Use `Live()` context for combat scenes (auto-refresh)
3. Pre-calculate dice pool in Character object if checked frequently
4. Truncate item descriptions in GearItem to 50 chars max

---

## Future Enhancements

### Planned Features
- [ ] Animated dice rolls with pip fills
- [ ] Equipment slot hover tooltips (for terminal with mouse support)
- [ ] Color-coded tier indicators on item names
- [ ] ASCII art gear icons per slot type
- [ ] Doom counter pulse effect when approaching 10
- [ ] Stat modifier delta display (e.g., `+2 → +3` on equipment change)

### Extension Points
```python
# Custom renderers for different themes
def render_paper_doll_gothic(character):
    """Victorian horror aesthetic variant."""
    # Use Gothic color palette from MEMORY.md
    pass

# Animated components
def render_dice_roll_animation(roll_result, duration=2.0):
    """Show dice rolling before revealing result."""
    pass
```

---

## Troubleshooting

### Issue: Text overflows panel borders
**Solution:** Set `overflow="fold"` on Panel or pre-truncate strings.

### Issue: Colors not showing in terminal
**Solution:** Ensure terminal supports 24-bit color. Use `console = Console(force_terminal=True)`.

### Issue: Dice pool exceeds 5d6
**Solution:** Verify `calculate_dice_pool()` uses `min(total, 5)`.

### Issue: HP bar broken at 0 HP
**Solution:** Use `max(0, min(1, current / maximum))` to clamp percent.

---

## Credits & License

**Author:** Codex Designer
**System:** Burnwillow (Bioluminescent Decay)
**Framework:** Rich (Python terminal UI library)
**Aesthetic:** Industrial decay, fungal glow, beautiful rot

*Part of Project Volo: The Codex System*

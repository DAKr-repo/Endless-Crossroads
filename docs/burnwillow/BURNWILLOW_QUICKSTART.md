# Burnwillow Paper Doll - Quick Start Guide

## Installation
```bash
# Already included in requirements.txt
pip install rich>=14.0.0
```

## Minimal Working Example
```python
from rich.console import Console
from burnwillow_paper_doll import Character, CharacterStats, GearItem, render_paper_doll

console = Console()

# Create character
stats = CharacterStats(might=14, wits=12, grit=16, aether=10)
character = Character(
    name="Moss",
    title="The Wanderer",
    hp_current=12,
    stats=stats,
    doom=3,
    right_hand=GearItem(name="Cudgel", tier=2, dice_contribution=2)
)

# Display
console.print(render_paper_doll(character))
```

## 5-Minute Integration Checklist

### 1. Import Components
```python
from burnwillow_paper_doll import (
    Character,
    CharacterStats,
    GearItem,
    render_paper_doll
)
```

### 2. Create Character Data
```python
# Stats (base 10, modifiers auto-calculated)
stats = CharacterStats(
    might=14,   # +2 mod
    wits=12,    # +1 mod
    grit=16,    # +3 mod (HP = 13)
    aether=10   # +0 mod
)

# Equipment (tier = dice contribution)
weapon = GearItem(
    name="Sap Cudgel",
    tier=2,
    dice_contribution=2
)
```

### 3. Build Character
```python
character = Character(
    name="Moss",
    title="The Wanderer",
    hp_current=12,
    stats=stats,
    doom=3,
    right_hand=weapon
    # Other slots optional
)
```

### 4. Render
```python
from rich.console import Console
console = Console()
console.print(render_paper_doll(character))
```

## Discord Integration (3 Steps)

### 1. Import Discord Module
```python
from burnwillow_discord_embed import character_to_discord_embed
```

### 2. Generate Embed
```python
embed_dict = character_to_discord_embed(character)
```

### 3. Send to Discord
```python
embed = discord.Embed.from_dict(embed_dict)
await ctx.send(embed=embed)
```

## Key Rules

### Dice Pool System
- **Base:** 1d6 (always)
- **Gear:** +1d6 per tier (1-5)
- **Cap:** 5d6 maximum
- **Visual:** `[●●●○○]` = 3d6

### Equipment Slots (10 Total)
```
Head, Shoulders, Neck
Chest, Arms, Legs
Right Hand, Left Hand
Right Ring, Left Ring
```

### Gear Tiers
| Tier | Material | Dice |
|------|----------|------|
| I | Scrap/Wood | +1d6 |
| II | Ironbark/Hide | +2d6 |
| III | Heartwood/Moonstone | +3d6 |
| IV | Ambercore/Sunresin | +4d6 |
| V | Burnwillow/Light | +5d6 |

### Stats & Formulas
```python
modifier = (stat - 10) // 2
hp_max = 10 + grit_mod
defense = 10 + wits_mod
```

## Testing Commands
```bash
# Visual test (no interaction)
python test_paper_doll.py

# Full demo suite (interactive)
python burnwillow_demo.py

# Discord embed JSON output
python burnwillow_discord_embed.py
```

## Common Patterns

### Load from Save File
```python
import json

with open("character.json") as f:
    data = json.load(f)

stats = CharacterStats(**data['stats'])
equipment = {
    slot: GearItem(**item_data) if item_data else None
    for slot, item_data in data['equipment'].items()
}

character = Character(
    name=data['name'],
    title=data['title'],
    hp_current=data['hp'],
    stats=stats,
    doom=data['doom'],
    **equipment
)
```

### Update HP During Combat
```python
from rich.live import Live

with Live(render_paper_doll(character), refresh_per_second=2) as live:
    while combat_active:
        # Take damage
        character.hp_current -= damage

        # Auto-refresh display
        live.update(render_paper_doll(character))
        await asyncio.sleep(0.5)
```

### Equip Item
```python
# Create item
new_weapon = GearItem(name="Light's Edge", tier=5, dice_contribution=5)

# Equip to slot
character.right_hand = new_weapon

# Dice pool auto-updates on next render
```

## Color Palette Reference

```python
FUNGAL_CYAN = "#00FFCC"      # Success, filled pips
DECAY_GREEN = "#2D5016"      # Borders, structure
EMBER_RUST = "#CC5500"       # Danger, low HP
BONE_WHITE = "#F5F5DC"       # Item names, text
SHADOW_PURPLE = "#4B0082"    # Empty slots
WILLOW_GOLD = "#FFD700"      # Headers, titles
```

## Troubleshooting

**Q: Dice pool shows 7d6 instead of capping at 5d6**
A: Bug in calculation. Should use `min(total, 5)`.

**Q: Item names overflow panel**
A: Names truncated to slot width automatically. Verify `width` parameter.

**Q: HP bar all gray**
A: Check HP > 0. Use `max(0, current)` to clamp.

**Q: Colors not showing**
A: Terminal must support 24-bit color. Try `Console(force_terminal=True)`.

## Full Documentation
- `BURNWILLOW_UI_GUIDE.md` - Complete design doc
- `.claude/agent-memory/codex-designer/MEMORY.md` - Theme patterns
- `burnwillow_paper_doll.py` - Source code (heavily commented)

## Support
Built by Codex Designer for Project Volo.
See TEAM_MANIFEST.md for team contacts.

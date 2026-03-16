# Spatial Map Renderer — Quick Start Guide

Get the new spatial map renderer running in 5 minutes.

---

## 1. Run the Standalone Demo

```bash
cd /home/pi/Projects/claude_sandbox/Codex
python codex_map_renderer.py
```

This will display all three themes (RUST, STONE, GOTHIC) with a sample dungeon. No dependencies beyond Rich.

**Expected Output:**
- Three full dungeon maps
- Each with different tileset and colors
- Fog of war demonstration
- Stats sidebar with HP, enemies, loot

---

## 2. Run the Integration Example

```bash
python example_spatial_map_integration.py
```

This demonstrates the complete workflow:
1. Generate dungeon with `codex_map_engine`
2. Populate with Burnwillow content
3. Convert to spatial format
4. Render with all three themes

---

## 3. Basic Usage in Your Code

```python
from codex_map_renderer import (
    render_spatial_map,
    MapTheme,
    SpatialRoom,
    RoomVisibility
)
from rich.console import Console

# Create a simple dungeon
rooms = {
    0: SpatialRoom(
        id=0, x=0, y=0, width=8, height=6,
        room_type="start",
        connections=[1],
        visibility=RoomVisibility.CURRENT,
        enemies=[{"name": "Rat", "hp": 3}],
        loot=[{"name": "Coin"}]
    ),
    1: SpatialRoom(
        id=1, x=10, y=0, width=8, height=6,
        room_type="normal",
        connections=[0],
        visibility=RoomVisibility.VISITED,
        enemies=[],
        loot=[]
    )
}

# Render
console = Console()
panel = render_spatial_map(
    rooms=rooms,
    player_room_id=0,
    theme=MapTheme.RUST
)
console.print(panel)
```

---

## 4. Integration with codex_map_engine

```python
from codex_map_engine import CodexMapEngine
from codex_map_renderer import SpatialRoom, RoomVisibility, render_spatial_map

# Generate dungeon
engine = CodexMapEngine(seed=12345)
dungeon = engine.generate()

# Convert to spatial (tracking visited rooms)
visited = {0}  # Start room
current = 0    # Player location

spatial_rooms = {}
for room_id, room_node in dungeon.rooms.items():
    visibility = (
        RoomVisibility.CURRENT if room_id == current else
        RoomVisibility.VISITED if room_id in visited else
        RoomVisibility.UNEXPLORED
    )
    spatial_rooms[room_id] = SpatialRoom.from_map_engine_room(room_node, visibility)

# Render
panel = render_spatial_map(rooms=spatial_rooms, player_room_id=current)
console.print(panel)
```

---

## 5. Switch Themes

```python
from codex_map_renderer import MapTheme

# Burnwillow (Industrial Decay)
panel = render_spatial_map(rooms=rooms, player_room_id=0, theme=MapTheme.RUST)

# D&D (Classic Dungeon)
panel = render_spatial_map(rooms=rooms, player_room_id=0, theme=MapTheme.STONE)

# Ashburn High (Victorian Horror)
panel = render_spatial_map(rooms=rooms, player_room_id=0, theme=MapTheme.GOTHIC)
```

---

## 6. Add Stats Sidebar

```python
stats = {
    "room_name": "The Entrance Hall",
    "room_description": "Dust motes dance in dim light.",
    "hp_current": 10,
    "hp_max": 15,
    "depth": 1,
    "enemies": [{"name": "Rat", "hp": 3}],
    "loot": [{"name": "Rusty Key"}],
    "exits": ["N", "E"]
}

panel = render_spatial_map(
    rooms=rooms,
    player_room_id=0,
    theme=MapTheme.RUST,
    stats=stats  # <-- Add this
)
```

---

## 7. Update as Player Moves

```python
def move_player(from_room: int, to_room: int, spatial_rooms: dict):
    # Mark old room as visited
    spatial_rooms[from_room].visibility = RoomVisibility.VISITED
    spatial_rooms[from_room].enemies = []  # Clear entities
    spatial_rooms[from_room].loot = []

    # Mark new room as current
    spatial_rooms[to_room].visibility = RoomVisibility.CURRENT
    # Populate entities from game state
    spatial_rooms[to_room].enemies = get_enemies_in_room(to_room)
    spatial_rooms[to_room].loot = get_loot_in_room(to_room)

    # Re-render
    panel = render_spatial_map(rooms=spatial_rooms, player_room_id=to_room)
    console.print(panel)
```

---

## 8. Customize Viewport

```python
# Smaller viewport for 80x24 terminals
panel = render_spatial_map(
    rooms=rooms,
    player_room_id=0,
    viewport_width=40,
    viewport_height=20
)

# Larger viewport for wide terminals
panel = render_spatial_map(
    rooms=rooms,
    player_room_id=0,
    viewport_width=80,
    viewport_height=30
)
```

---

## 9. Debugging (Show All Rooms)

```python
# For testing: Show all rooms regardless of fog of war
renderer = SpatialGridRenderer(MapTheme.RUST)
map_lines = renderer.render_dungeon(
    rooms=spatial_rooms,
    player_room_id=0,
    show_all_rooms=True  # <-- Debug mode
)
```

---

## 10. Export to Discord/Telegram

### Discord Embed
```python
# Get plain text version (no Rich formatting)
from rich.console import Console

console = Console(record=True)
console.print(panel)
text_output = console.export_text()

# Send as code block
embed = discord.Embed(
    title="Dungeon Map",
    description=f"```\n{text_output}\n```",
    color=0x00FFCC
)
await ctx.send(embed=embed)
```

### Telegram
```python
# Monospace formatting
message = f"```\n{text_output}\n```"
await bot.send_message(chat_id, message, parse_mode="Markdown")
```

---

## Common Issues

### Issue: Rooms not showing up
**Fix:** Check that `room.visibility != RoomVisibility.UNEXPLORED` or set `show_all_rooms=True`

### Issue: Entities missing
**Fix:** Ensure `room.visibility == RoomVisibility.CURRENT` and `room.enemies`/`room.loot` are populated

### Issue: Corridors not connecting
**Fix:** Both connected rooms must be VISITED or CURRENT

### Issue: Colors not displaying
**Fix:** Use a terminal with 24-bit color support (GNOME Terminal, Kitty, iTerm2)

---

## Next Steps

- Read full docs: `docs/SPATIAL_MAP_GUIDE.md`
- See visual examples: `docs/VISUAL_EXAMPLES.md`
- Review integration: `example_spatial_map_integration.py`
- Update agent memory: `.claude/agent-memory/codex-designer/MEMORY.md`

---

**You're ready to integrate spatial maps into your game!**

The renderer is modular, performant, and theme-aware. It works seamlessly with `codex_map_engine.py` and can be adapted to any ruleset.

Happy dungeon crawling! 🗺️

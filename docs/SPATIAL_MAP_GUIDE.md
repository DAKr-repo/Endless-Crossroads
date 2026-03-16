# Spatial Map Renderer v2.0 — Integration Guide

## Overview

The `codex_map_renderer.py` module has been completely overhauled to provide **high-fidelity 2D spatial rendering** of procedurally generated dungeons. This replaces the previous abstract symbol-based visualization with true spatial representation where rooms have interiors, walls, floors, and corridors.

---

## Key Features

### 1. True Spatial Representation
- **Rooms occupy actual grid space** based on their `x`, `y`, `width`, `height` coordinates
- **Wall characters** vary by position (corners vs edges)
- **Floor tiles** fill room interiors (not just borders)
- **Entities** (player, enemies, loot) are positioned within rooms

### 2. Three-Tier Fog of War
- **CURRENT**: Player's room — bright borders, full visibility, entities shown
- **VISITED**: Previously explored — dimmed, no entities
- **UNEXPLORED**: Never visited — fog character fill OR completely hidden

### 3. Thematic Tilesets
Three complete ASCII tilesets with distinct aesthetics:
- **RUST** (Burnwillow): Industrial decay, heavy metal blocks
- **STONE** (D&D): Classic dungeon, stone walls and flagstone floors
- **GOTHIC** (Ashburn High): Victorian box-drawing characters

### 4. Viewport System
- Player-centered scrolling for large dungeons
- Configurable viewport size (default 50x22 chars)
- Automatic clipping and centering

---

## Architecture

### Core Classes

```python
class SpatialGridRenderer:
    """Main 2D character matrix builder."""

class GridCell:
    """Single grid cell with char, style, metadata."""
    char: str
    style: str
    is_wall: bool
    is_floor: bool
    is_entity: bool
    room_id: Optional[int]

class SpatialRoom:
    """Adapter for codex_map_engine.RoomNode."""
    id: int
    x: int
    y: int
    width: int
    height: int
    room_type: str  # "start", "normal", "boss", "treasure"
    visibility: RoomVisibility
    enemies: List[Dict]
    loot: List[Dict]

class RoomVisibility(Enum):
    CURRENT = "current"
    VISITED = "visited"
    UNEXPLORED = "unexplored"
```

### Rendering Pipeline

```
1. Calculate dungeon bounds (min/max x/y)
   ↓
2. Initialize 2D GridCell matrix
   ↓
3. Render each room to grid:
   - Walls (edge detection for corners)
   - Floor (interior tiles)
   - Entities (only if CURRENT)
   ↓
4. Render corridors (L-shaped paths)
   ↓
5. Convert grid to Rich Text objects
   ↓
6. Apply viewport clipping
   ↓
7. Build stats sidebar (optional)
   ↓
8. Return Rich Panel
```

---

## Integration with codex_map_engine

### Step 1: Generate Dungeon Geometry

```python
from codex_map_engine import CodexMapEngine, RoomType

# Generate procedural dungeon
engine = CodexMapEngine(seed=12345)
dungeon_graph = engine.generate(width=50, height=50, max_depth=4)

# dungeon_graph.rooms is Dict[int, RoomNode]
# RoomNode has: id, x, y, width, height, room_type, connections, tier
```

### Step 2: Convert to SpatialRooms

```python
from codex_map_renderer import SpatialRoom, RoomVisibility

# Track which rooms player has visited
visited_room_ids = {0, 1, 2}  # Example: start + 2 visited
current_room_id = 2

# Convert RoomNode to SpatialRoom
spatial_rooms = {}
for room_id, room_node in dungeon_graph.rooms.items():
    # Determine visibility
    if room_id == current_room_id:
        visibility = RoomVisibility.CURRENT
    elif room_id in visited_room_ids:
        visibility = RoomVisibility.VISITED
    else:
        visibility = RoomVisibility.UNEXPLORED

    # Convert
    spatial_rooms[room_id] = SpatialRoom.from_map_engine_room(
        room=room_node,
        visibility=visibility
    )

    # Add entities (only needed for CURRENT room)
    if room_id == current_room_id:
        spatial_rooms[room_id].enemies = [
            {"name": "Rust Rat", "hp": 5},
            {"name": "Oil Slick", "hp": 3}
        ]
        spatial_rooms[room_id].loot = [
            {"name": "Rusted Shortsword"}
        ]
```

### Step 3: Render the Map

```python
from codex_map_renderer import render_spatial_map, MapTheme
from rich.console import Console

console = Console()

# Optional: Build stats dict
stats = {
    "room_name": "Storage Bay #3",
    "room_description": "Rusted pipes drip oily water. Something skitters in the shadows.",
    "hp_current": 8,
    "hp_max": 15,
    "depth": 3,
    "enemies": spatial_rooms[current_room_id].enemies,
    "loot": spatial_rooms[current_room_id].loot,
    "exits": ["N", "S"]  # Cardinal directions
}

# Render
map_panel = render_spatial_map(
    rooms=spatial_rooms,
    player_room_id=current_room_id,
    theme=MapTheme.RUST,  # or STONE, GOTHIC
    stats=stats,  # Optional
    viewport_width=50,
    viewport_height=22,
    console=console
)

console.print(map_panel)
```

---

## Theme Configuration

### RUST (Burnwillow)

```python
MapTheme.RUST
```

**Tileset:**
- Walls: `█` (heavy industrial blocks)
- Floor: `·` (metal grating)
- Fog: `░` (bioluminescent spores)
- Player: `@` (cyan glow)
- Enemy: `E` (rust orange)
- Loot: `$` (willow gold)

**Color Palette:**
- Wall: `#0f380f` (deep green)
- Floor: `#2D5016` (decay green)
- Current: `#00FFCC` (fungal cyan)
- Visited: `#2D5016` (dimmed)
- Fog: `#4B0082` (shadow purple)

**Aesthetic:** Industrial decay, bioluminescent rot, heavy metal

---

### STONE (D&D Classic)

```python
MapTheme.STONE
```

**Tileset:**
- Walls: `#` (stone blocks)
- Floor: `.` (flagstone)
- Fog: `~` (shadow)
- Player: `@` (gold)
- Enemy: `M` (monster)
- Loot: `*` (treasure)

**Color Palette:**
- Wall: `#808080` (stone grey)
- Floor: `#5f5f5f` (darker grey)
- Current: `#FFD700` (gold)
- Visited: `#808080` (dimmed)
- Fog: `#404040` (deep shadow)

**Aesthetic:** Torchlit dungeon crawl, underground caverns

---

### GOTHIC (Ashburn High)

```python
MapTheme.GOTHIC
```

**Tileset:**
- Walls: `═` (horizontal), `║` (vertical)
- Corners: `╔` (NW), `╗` (NE), `╚` (SW), `╝` (SE)
- Floor: `░` (carpet/marble)
- Fog: `▒` (darkness)
- Player: `☥` (ankh, bone white)
- Enemy: `Σ` (blood red)
- Loot: `✦` (gold)

**Color Palette:**
- Wall: `#4B0082` (deep purple)
- Floor: `#2B0042` (deeper purple)
- Current: `#F5F5DC` (bone white)
- Visited: `#5f5f87` (slate)
- Fog: `#2B0042` (deeper purple)

**Aesthetic:** Victorian horror, cursed halls, eldritch atmosphere

---

## Advanced Usage

### Custom Entity Positioning

By default, entities are scattered using `_scatter_positions()` (corners and edges). To customize:

```python
# Manually place enemies at specific positions
spatial_room = spatial_rooms[current_room_id]
spatial_room.enemies = [
    {"name": "Boss Rat", "hp": 20, "position": (4, 3)}  # Custom position
]
```

### Visibility Management

Update room visibility as player explores:

```python
def enter_room(room_id: int, spatial_rooms: Dict[int, SpatialRoom]):
    # Mark previous room as VISITED
    for room in spatial_rooms.values():
        if room.visibility == RoomVisibility.CURRENT:
            room.visibility = RoomVisibility.VISITED

    # Mark new room as CURRENT
    spatial_rooms[room_id].visibility = RoomVisibility.CURRENT
```

### Dynamic Stats Sidebar

```python
# Update stats as game state changes
stats["hp_current"] = player.hp
stats["enemies"] = spatial_rooms[current_room_id].enemies
stats["exits"] = get_available_exits(current_room_id, dungeon_graph)

# Re-render
map_panel = render_spatial_map(rooms=spatial_rooms, ...)
```

---

## Performance Considerations

### Memory Usage
- Small dungeon (10 rooms, 50x50 grid): ~2-5 MB
- Large dungeon (30 rooms, 100x100 grid): ~10-20 MB

### CPU Usage
- Initial render: ~10-50ms on Pi 5
- Re-render (same dungeon): ~5-20ms (caching possible)

### Optimization Tips
1. **Limit viewport size** for smaller terminals (40x20 vs 50x22)
2. **Cache GridCell matrix** if dungeon doesn't change between renders
3. **Lazy entity rendering**: Only compute positions for CURRENT room
4. **Sparse grid**: Use dict instead of 2D list for very large dungeons

---

## Testing

### Run Standalone Demo

```bash
cd /home/pi/Projects/claude_sandbox/Codex
python codex_map_renderer.py
```

This will display all three themes with a sample dungeon.

### Manual Testing Checklist

- [ ] Renders at 80x24 without breaking
- [ ] Spatial grid handles room boundaries correctly
- [ ] Fog of war shows 3 visibility states
- [ ] Entities only appear in CURRENT room
- [ ] Corridors connect properly between visited rooms
- [ ] Wall corners render correctly (NW, NE, SW, SE)
- [ ] Player always at room center
- [ ] Theme colors consistent across all elements

---

## Discord/Telegram Translation

The spatial map can be converted to Discord embeds or Telegram messages:

### Discord Embed
```python
# Convert map to code block (monospace preservation)
map_text = "\n".join([line.plain for line in map_lines])

embed = discord.Embed(
    title="The Minimap",
    description=f"```\n{map_text}\n```",
    color=0x00FFCC  # Fungal cyan
)

# Add stats as fields
embed.add_field(name="HP", value="8/15", inline=True)
embed.add_field(name="Depth", value="Floor 3", inline=True)
embed.add_field(name="Enemies", value="2x Rust Rat", inline=False)
```

### Telegram
```python
# Use monospace formatting
message = f"```\n{map_text}\n```\n\nHP: 8/15\nDepth: Floor 3"
await bot.send_message(chat_id, message, parse_mode="Markdown")
```

---

## Troubleshooting

### Issue: Rooms overlap or render incorrectly
**Solution:** Verify `codex_map_engine` generated valid coordinates. Check that `room.x + room.width` doesn't exceed dungeon bounds.

### Issue: Entities not showing up
**Solution:** Ensure room visibility is set to `RoomVisibility.CURRENT` and entities list is populated.

### Issue: Corridors don't connect
**Solution:** Check that both connected rooms have `visibility != UNEXPLORED`. Corridors only render between visible rooms.

### Issue: Theme colors not displaying
**Solution:** Verify terminal supports 24-bit color. Use `Console(force_terminal=True)` for consistency.

---

## Future Enhancements

- **Dynamic lighting**: Torchlight radius, darkness gradient
- **Animated entities**: Enemies pulse/flicker in CURRENT room
- **Room descriptions**: Hover tooltips or overlay text
- **Minimap zoom**: Dynamic viewport scaling
- **Path highlighting**: Show route from start to current room

---

## API Reference

### Main Functions

```python
render_spatial_map(
    rooms: Dict[int, SpatialRoom],
    player_room_id: int,
    theme: MapTheme = MapTheme.RUST,
    stats: Optional[Dict[str, Any]] = None,
    viewport_width: int = 50,
    viewport_height: int = 22,
    console: Optional[Console] = None
) -> Panel
```

### Helper Functions

```python
build_stats_sidebar(
    stats: Dict[str, Any],
    theme: ThemeConfig
) -> Panel
```

### Classes

See "Core Classes" section above for full API.

---

## Credits

- **Architecture**: Codex Designer Agent
- **Tilesets**: Inspired by traditional roguelikes (NetHack, Brogue, Dungeon Crawl Stone Soup)
- **Rich Library**: Will McGugan (https://github.com/Textualize/rich)

---

**Version:** 2.0 (Spatial Mode)
**Last Updated:** 2026-02-06
**File:** `/home/pi/Projects/claude_sandbox/Codex/codex_map_renderer.py`

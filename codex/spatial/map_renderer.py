#!/usr/bin/env python3
"""
codex_map_renderer.py - High-Fidelity Spatial Grid Renderer
=============================================================

A complete 2D dungeon map renderer with true spatial representation.
Each room occupies actual grid space, with walls, floors, doors, and corridors.

Key Features:
- TRUE spatial rendering: Rooms have interiors with floor tiles
- Viewport system: Player-centered scrolling for large dungeons
- Fog of war: Current room (bright), visited (dimmed), unexplored (hidden)
- Thematic tilesets: Different ASCII art for RUST, STONE, GOTHIC
- Entity rendering: Only show enemies/loot in CURRENT room
- Corridor visualization: Actual passages connecting rooms

Architecture:
  1. SpatialGridRenderer: Main 2D character matrix builder
  2. ThemeConfig: Defines wall/floor/door characters per theme
  3. VisibilitySystem: Manages fog of war (current, visited, unexplored)
  4. ViewportController: Handles player-centered scrolling

Version: 2.1 (High Contrast Update)
"""

from typing import Dict, List, Set, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich import box


# =============================================================================
# THEME SYSTEM — THREE AESTHETIC TILESETS
# =============================================================================

class MapTheme(Enum):
    RUST = "RUST"       # Burnwillow (Sci-Fi/Industrial)
    STONE = "STONE"     # D&D (Classic Dungeon)
    GOTHIC = "GOTHIC"   # Blades/Vampire (Victorian/Dark)
    VILLAGE = "VILLAGE"  # Settlements (warm wood)
    CANOPY = "CANOPY"    # Burnwillow canopy (ascending)


@dataclass
class ThemeConfig:
    """All tile characters and Rich style strings for a single map aesthetic.

    Instances are registered in THEME_REGISTRY by name (e.g. "RUST", "STONE").
    Renderers read from ThemeConfig directly rather than switching on MapTheme
    values, so new themes require only a new ThemeConfig registration.
    """
    wall_char: str
    floor_char: str
    corridor_char: str
    door_closed: str
    door_open: str
    wall_style: str     # Rich style string (e.g. "bold white")
    floor_style: str
    color_current: str  # Color for "Current Room" highlight
    color_visited: str  # Color for "Visited" dimming
    color_enemy: str
    color_loot: str
    color_player: str
    # Extended symbols (WO V20.1)
    symbol_boss: str = "B"
    symbol_loot: str = "!"
    symbol_furniture: str = "?"
    color_furniture: str = "bold white"
    color_scouted: str = "dim yellow"
    symbol_hunter: str = "H"
    color_hunter: str = "bold magenta"
    # Container symbols (WO V20.3)
    symbol_chest: str = "["
    symbol_rack: str = "="
    color_chest: str = "bold yellow"
    color_rack: str = "bold cyan"
    # Doorway symbols (WO V20.3.5)
    doorway_char: str = "#"
    color_doorway: str = "bold white"
    # Quest markers (WO V45.0)
    symbol_quest: str = "?"
    color_quest: str = "bold magenta"


# THEME DEFINITIONS

class ThemeRegistry:
    """Registry of named ThemeConfig instances.

    Pre-registers RUST, STONE, and GOTHIC.  New themes can be added via
    ``register(name, config)``.  Accepts both :class:`MapTheme` enum
    members and plain strings as keys for backward compatibility.
    """

    def __init__(self):
        self._themes: dict[str, ThemeConfig] = {}

    def register(self, name: str, config: ThemeConfig) -> None:
        """Register (or overwrite) a theme by string name."""
        self._themes[name] = config

    def get(self, name) -> ThemeConfig:
        """Retrieve a theme by name or MapTheme enum.

        Raises ``KeyError`` if not found.
        """
        key = name.value if isinstance(name, MapTheme) else str(name)
        return self._themes[key]

    def __getitem__(self, key) -> ThemeConfig:
        return self.get(key)

    def __contains__(self, key) -> bool:
        k = key.value if isinstance(key, MapTheme) else str(key)
        return k in self._themes

    def names(self) -> list[str]:
        """Return all registered theme names."""
        return list(self._themes.keys())


# Singleton theme registry pre-populated with the three core tilesets
THEME_REGISTRY = ThemeRegistry()

THEME_REGISTRY.register("RUST", ThemeConfig(
    wall_char="█",
    floor_char="·",
    corridor_char="░",
    door_closed="║",
    door_open="│",
    wall_style="grey74",       # High contrast concrete
    floor_style="dim cyan",
    color_current="bold cyan",
    color_visited="dim cyan",
    color_enemy="bold red",
    color_loot="bold yellow",
    color_player="bold white on cyan"
))
THEME_REGISTRY.register("STONE", ThemeConfig(
    wall_char="#",
    floor_char=".",
    corridor_char=":",
    door_closed="+",
    door_open="'",
    wall_style="bold white",   # Classic roguelike bright walls
    floor_style="dim white",
    color_current="bold green",
    color_visited="dim green",
    color_enemy="bold red",
    color_loot="bold gold1",
    color_player="bold white on green"
))
THEME_REGISTRY.register("GOTHIC", ThemeConfig(
    wall_char="▒",
    floor_char="¸",
    corridor_char="≈",
    door_closed="¶",
    door_open=" ",
    wall_style="bold purple",  # Eldritch/Void
    floor_style="dim magenta",
    color_current="bold magenta",
    color_visited="dim magenta",
    color_enemy="bold red",
    color_loot="bold yellow",
    color_player="bold white on magenta"
))
THEME_REGISTRY.register("VILLAGE", ThemeConfig(
    wall_char="▓",            # Thick timber walls
    floor_char="·",           # Cobblestone
    corridor_char="─",        # Streets/paths
    door_closed="▪",          # Building entrance
    door_open="▫",            # Open door
    wall_style="dark_goldenrod",
    floor_style="dim white",
    color_current="bold yellow",
    color_visited="dim yellow",
    color_enemy="bold red",
    color_loot="bold green",
    color_player="bold white on dark_goldenrod",
    symbol_boss="★",          # Quest giver
    symbol_loot="$",          # Merchant goods
    symbol_furniture="♦",     # Interactive objects
))
THEME_REGISTRY.register("CANOPY", ThemeConfig(
    wall_char="║",            # Vertical bark walls
    floor_char="≈",           # Woven branch floor
    corridor_char="│",        # Vertical connections (climbing)
    door_closed="◊",          # Bark hatch
    door_open="○",            # Open passage
    wall_style="dark_goldenrod",
    floor_style="yellow",
    color_current="bold yellow",
    color_visited="dim yellow",
    color_enemy="bold red",
    color_loot="bold green",
    color_player="bold white on dark_goldenrod",
    symbol_boss="✦",          # Crown guardian
    symbol_loot="❋",          # Sap/amber loot
    symbol_furniture="♠",     # Living wood features
))

# Backward-compatible dict-style access: THEMES[MapTheme.RUST] still works
THEMES = THEME_REGISTRY


# =============================================================================
# DATA STRUCTURES FOR SPATIAL MAP
# =============================================================================

class RoomVisibility(Enum):
    """Fog-of-war state for a single room in the spatial renderer.

    Controls which tiles are drawn and what style is applied: HIDDEN rooms are
    skipped entirely, UNEXPLORED show outlines only, VISITED render dimmed, and
    CURRENT renders at full brightness with entity symbols.
    """
    HIDDEN = 0
    UNEXPLORED = 1  # Outline known but content hidden (e.g. from map item)
    VISITED = 2     # Fully explored, shown dim
    CURRENT = 3     # Where the player is, shown bright


@dataclass
class SpatialRoom:
    """
    Represents a room for the renderer.
    Coordinates (x, y) are abstract 'grid units', not screen pixels.
    width/height are in grid units (e.g. 5x3 tiles).
    """
    id: int
    x: int
    y: int
    width: int
    height: int
    visibility: RoomVisibility = RoomVisibility.HIDDEN
    connections: List[int] = field(default_factory=list)  # List of room IDs connected to
    enemies: List[dict] = field(default_factory=list)     # Only populated for CURRENT room
    loot: List[dict] = field(default_factory=list)        # Only populated for CURRENT room
    furniture: List[dict] = field(default_factory=list)   # Interactive objects
    quest_markers: List[str] = field(default_factory=list)  # WO-V45.0: quest objective types in room
    room_type: Any = None  # RoomType enum value (for settlement labels)

    @staticmethod
    def from_map_engine_room(room_node: Any, visibility: RoomVisibility = RoomVisibility.HIDDEN):
        """Convert a RoomNode from codex_map_engine to a SpatialRoom."""
        return SpatialRoom(
            id=room_node.id,
            x=room_node.x,
            y=room_node.y,
            width=room_node.width,
            height=room_node.height,
            visibility=visibility,
            connections=room_node.connections,
            room_type=getattr(room_node, "room_type", None),
        )


# =============================================================================
# SETTLEMENT ROOM SYMBOLS
# =============================================================================

# Imported lazily to avoid circular imports with map_engine
_SETTLEMENT_SYMBOLS: dict[str, tuple[str, str]] = {
    "tavern": ("T", "bold yellow"),
    "forge": ("F", "bold red"),
    "market": ("M", "bold green"),
    "temple": ("+", "bold cyan"),
    "barracks": ("B", "bold white"),
    "town_gate": ("G", "bold magenta"),
    "town_square": ("◆", "bold yellow"),
    "library": ("L", "bold blue"),
    "residence": ("R", "dim white"),
}


# =============================================================================
# SPATIAL GRID RENDERER
# =============================================================================

class SpatialGridRenderer:
    """
    Builds a 2D character grid of the dungeon based on spatial coordinates.
    Handles coordinate normalization (shifting negative coords to 0,0) and tile plotting.
    """

    def __init__(self, rooms: Dict[int, SpatialRoom], theme: MapTheme = MapTheme.RUST):
        self.rooms = rooms
        self.theme = THEMES[theme]
        self.grid: Dict[Tuple[int, int], Tuple[str, str]] = {}  # (x,y) -> (char, style)
        self.min_x = 0
        self.min_y = 0
        self.max_x = 0
        self.max_y = 0
        self._build_grid()

    def _build_grid(self):
        """Construct the character matrix."""
        if not self.rooms:
            return

        # 1. Determine bounds
        # Convert engine coords (large spread) to tighter visual grid
        # NOTE: Assuming map_engine coords are already reasonable (e.g. 0-100 range)
        # We multiply by a scale factor to give rooms interior space if needed, 
        # but map_engine likely already provides distinct non-overlapping coords.
        
        all_x = [r.x for r in self.rooms.values()] + [r.x + r.width for r in self.rooms.values()]
        all_y = [r.y for r in self.rooms.values()] + [r.y + r.height for r in self.rooms.values()]
        
        self.min_x = min(all_x) - 2 # Padding
        self.min_y = min(all_y) - 2
        self.max_x = max(all_x) + 2
        self.max_y = max(all_y) + 2

        # 2. Paint Rooms
        for r in self.rooms.values():
            if r.visibility == RoomVisibility.HIDDEN:
                continue
            
            self._paint_room(r)
            self._paint_corridors(r)

    def _paint_room(self, r: SpatialRoom):
        """Draw walls, floor, and content for a single room."""
        # Determine style based on visibility
        if r.visibility == RoomVisibility.CURRENT:
            wall_style = self.theme.color_current
            floor_style = self.theme.color_current
        elif r.visibility == RoomVisibility.VISITED:
            wall_style = self.theme.wall_style  # Use theme default for visited walls
            floor_style = self.theme.color_visited
        else: # UNEXPLORED
            wall_style = "dim grey30"
            floor_style = "dim grey10"

        # Draw box
        for y in range(r.y, r.y + r.height):
            for x in range(r.x, r.x + r.width):
                char = self.theme.floor_char
                style = floor_style

                # Walls
                is_wall = (x == r.x or x == r.x + r.width - 1 or 
                           y == r.y or y == r.y + r.height - 1)
                
                if is_wall:
                    char = self.theme.wall_char
                    style = wall_style

                self.grid[(x, y)] = (char, style)

        # Place entities at spread positions inside the room (after floor is drawn)
        if r.visibility == RoomVisibility.CURRENT:
            cx = r.x + r.width // 2
            cy = r.y + r.height // 2
            inner_x0, inner_y0 = r.x + 1, r.y + 1
            inner_x1, inner_y1 = r.x + r.width - 2, r.y + r.height - 2

            _ARCHETYPE_SYM = {"beast": "b", "scavenger": "s", "construct": "c", "aetherial": "a"}
            for i, _e in enumerate(r.enemies):
                ex = cx + 1 + i
                ey = cy
                if inner_x0 <= ex <= inner_x1 and inner_y0 <= ey <= inner_y1:
                    if _e.get("is_rot_hunter"):
                        sym, style = self.theme.symbol_hunter, self.theme.color_hunter
                    elif _e.get("is_boss"):
                        sym, style = self.theme.symbol_boss, self.theme.color_enemy
                    else:
                        sym = _ARCHETYPE_SYM.get(_e.get("archetype", ""), "E")
                        style = self.theme.color_enemy
                    self.grid[(ex, ey)] = (sym, style)

            for i, _item in enumerate(r.loot):
                lx = cx - 1 - i
                ly = cy
                if inner_x0 <= lx <= inner_x1 and inner_y0 <= ly <= inner_y1:
                    self.grid[(lx, ly)] = (self.theme.symbol_loot, self.theme.color_loot)

            for i, obj in enumerate(r.furniture):
                fx = cx - 1 + i
                fy = cy + 1
                if inner_x0 <= fx <= inner_x1 and inner_y0 <= fy <= inner_y1:
                    # WO V20.3: Container-specific symbols
                    ctype = obj.get("container_type", "furniture") if isinstance(obj, dict) else "furniture"
                    if ctype == "chest":
                        sym, col = self.theme.symbol_chest, self.theme.color_chest
                    elif ctype == "rack":
                        sym, col = self.theme.symbol_rack, self.theme.color_rack
                    else:
                        sym, col = self.theme.symbol_furniture, self.theme.color_furniture
                    self.grid[(fx, fy)] = (sym, col)

            # WO-V45.0: Quest objective marker at bottom-left interior
            if r.quest_markers:
                qx = r.x + 1
                qy = r.y + r.height - 2
                if r.x + 1 <= qx <= r.x + r.width - 2 and r.y + 1 <= qy <= r.y + r.height - 2:
                    self.grid[(qx, qy)] = (self.theme.symbol_quest, self.theme.color_quest)

        elif r.visibility == RoomVisibility.VISITED and (r.enemies or r.loot or r.quest_markers):
            # Scouted rooms show entity positions in dimmed color
            cx = r.x + r.width // 2
            cy = r.y + r.height // 2
            inner_x0, inner_y0 = r.x + 1, r.y + 1
            inner_x1, inner_y1 = r.x + r.width - 2, r.y + r.height - 2

            _ARCHETYPE_SYM_V = {"beast": "b", "scavenger": "s", "construct": "c", "aetherial": "a"}
            for i, _e in enumerate(r.enemies):
                ex = cx + 1 + i
                ey = cy
                if inner_x0 <= ex <= inner_x1 and inner_y0 <= ey <= inner_y1:
                    if _e.get("is_rot_hunter"):
                        sym, style = self.theme.symbol_hunter, self.theme.color_hunter
                    elif _e.get("is_boss"):
                        sym, style = self.theme.symbol_boss, self.theme.color_scouted
                    else:
                        sym = _ARCHETYPE_SYM_V.get(_e.get("archetype", ""), "E")
                        style = self.theme.color_scouted
                    self.grid[(ex, ey)] = (sym, style)

            for i, _item in enumerate(r.loot):
                lx = cx - 1 - i
                ly = cy
                if inner_x0 <= lx <= inner_x1 and inner_y0 <= ly <= inner_y1:
                    self.grid[(lx, ly)] = (self.theme.symbol_loot, self.theme.color_scouted)

            # WO-V45.0: Dimmed quest marker for visited rooms
            if r.quest_markers:
                qx = r.x + 1
                qy = r.y + r.height - 2
                if inner_x0 <= qx <= inner_x1 and inner_y0 <= qy <= inner_y1:
                    self.grid[(qx, qy)] = (self.theme.symbol_quest, self.theme.color_scouted)

        # Settlement building labels (drawn for any visible room)
        if r.visibility != RoomVisibility.HIDDEN:
            rtype = getattr(r, "room_type", None)
            if rtype:
                rtype_str = rtype.value if hasattr(rtype, "value") else str(rtype)
                sym_info = _SETTLEMENT_SYMBOLS.get(rtype_str)
                if sym_info:
                    sym, sym_style = sym_info
                    cx = r.x + r.width // 2
                    cy = r.y + r.height // 2
                    # Only draw label if player marker isn't already there
                    if (cx, cy) not in self.grid or self.grid[(cx, cy)][0] != "@":
                        self.grid[(cx, cy)] = (sym, sym_style)

    def _paint_corridors(self, r: SpatialRoom):
        """Draw corridors to connected rooms (Manhattan routing)."""
        # Only draw if visible
        if r.visibility == RoomVisibility.HIDDEN:
            return

        cx, cy = r.x + r.width // 2, r.y + r.height // 2
        
        for target_id in r.connections:
            if target_id not in self.rooms: continue
            target = self.rooms[target_id]
            if target.visibility == RoomVisibility.HIDDEN: continue

            tx, ty = target.x + target.width // 2, target.y + target.height // 2

            # Draw L-shaped corridor
            # Horizontal first, then Vertical
            
            # Determines color
            style = self.theme.floor_style
            if r.visibility == RoomVisibility.CURRENT or target.visibility == RoomVisibility.CURRENT:
                style = self.theme.color_current # Lit corridor
            
            # Horizontal leg
            x_step = 1 if tx > cx else -1
            for x in range(cx, tx + x_step, x_step):
                if (x, cy) not in self.grid:
                    self.grid[(x, cy)] = (self.theme.corridor_char, style)
                else:
                    existing_char, _ = self.grid[(x, cy)]
                    if existing_char == self.theme.wall_char:
                        self.grid[(x, cy)] = (self.theme.doorway_char, self.theme.color_doorway)

            # Vertical leg
            y_step = 1 if ty > cy else -1
            for y in range(cy, ty + y_step, y_step):
                if (tx, y) not in self.grid:
                    self.grid[(tx, y)] = (self.theme.corridor_char, style)
                else:
                    existing_char, _ = self.grid[(tx, y)]
                    if existing_char == self.theme.wall_char:
                        self.grid[(tx, y)] = (self.theme.doorway_char, self.theme.color_doorway)


# =============================================================================
# MINI-MAP RENDERER (Canonical — replaces per-bridge duplicates)
# =============================================================================

# Mini-map symbols
_MM_PLAYER = "@"
_MM_VISITED = "#"
_MM_UNEXPLORED = "?"
_MM_TREASURE = "$"
_MM_BOSS = "B"
_MM_LOCKED = "!"
_MM_GATE = "G"     # Return Gate (Burnwillow)
_MM_PORTAL = "P"   # Hidden Portal (D&D)
_MM_BORDER = "X"   # Border Crossing (Crown)
_MM_QUEST = "Q"     # WO-V45.0: Quest objective marker
_MM_EMPTY = "."
_MM_H_CONN = "-"
_MM_V_CONN = "|"


def _draw_minimap_connection(grid: list, ax: int, ay: int, bx: int, by: int):
    """Draw connection lines between two mini-map grid positions."""
    if ax == bx:
        for y in range(min(ay, by) + 1, max(ay, by)):
            if grid[y][ax] == _MM_EMPTY:
                grid[y][ax] = _MM_V_CONN
    elif ay == by:
        for x in range(min(ax, bx) + 1, max(ax, bx)):
            if grid[ay][x] == _MM_EMPTY:
                grid[ay][x] = _MM_H_CONN


def render_mini_map(
    dungeon_rooms: Dict[int, dict],
    current_room_id: int,
    visited_rooms: Set[int],
    grid_size: int = 7,
    scale: int = 8,
    rich_mode: bool = False,
    theme: Optional[MapTheme] = None,
    doom: Optional[int] = None,
) -> Union[str, Text]:
    """Render a graph-topology mini-map.

    Args:
        dungeon_rooms: room_id -> {x, y, width, height, connections, room_type, is_locked}
        current_room_id: ID of the player's current room.
        visited_rooms: Set of visited room IDs.
        grid_size: Grid dimension (default 7x7).
        scale: Coordinate scaling factor.
        rich_mode: True returns Rich Text with colors, False returns plain string.
        theme: MapTheme for color selection (used when rich_mode=True).
        doom: If provided, shown in footer.

    Returns:
        Plain string (rich_mode=False) or Rich Text (rich_mode=True).
    """
    current_room = dungeon_rooms.get(current_room_id)
    if not current_room:
        return Text("(no map)") if rich_mode else "(no map)"

    cx = current_room["x"] + current_room["width"] // 2
    cy = current_room["y"] + current_room["height"] // 2

    # Determine visible rooms: visited + connected to current
    connected_ids = set(current_room.get("connections", []))
    visible_ids = set(visited_rooms) | connected_ids
    visible_ids.add(current_room_id)

    mid = grid_size // 2
    grid = [[_MM_EMPTY] * grid_size for _ in range(grid_size)]
    room_positions = {}

    for room_id in visible_ids:
        room = dungeon_rooms.get(room_id)
        if not room:
            continue

        rx = room["x"] + room["width"] // 2
        ry = room["y"] + room["height"] // 2
        dx = rx - cx
        dy = ry - cy
        gx = max(0, min(grid_size - 1, mid + round(dx / scale)))
        gy = max(0, min(grid_size - 1, mid + round(dy / scale)))
        room_positions[room_id] = (gx, gy)

        # Determine symbol
        if room_id == current_room_id:
            sym = _MM_PLAYER
        elif room.get("quest_markers") and room_id in visited_rooms:
            sym = _MM_QUEST  # WO-V45.0: quest objective in visited room
        elif room_id in visited_rooms:
            sym = _MM_VISITED
        elif room.get("is_locked"):
            sym = _MM_LOCKED
        elif room.get("room_type") == "TREASURE":
            sym = _MM_TREASURE
        elif room.get("room_type") == "BOSS":
            sym = _MM_BOSS
        elif room.get("room_type") == "RETURN_GATE":
            sym = _MM_GATE
        elif room.get("room_type") == "HIDDEN_PORTAL":
            sym = _MM_PORTAL
        elif room.get("room_type") == "BORDER_CROSSING":
            sym = _MM_BORDER
        else:
            sym = _MM_UNEXPLORED

        grid[gy][gx] = sym

    # Draw connections
    for room_id in visible_ids:
        if room_id not in room_positions:
            continue
        room = dungeon_rooms.get(room_id)
        if not room:
            continue
        ax, ay = room_positions[room_id]
        for conn_id in room.get("connections", []):
            if conn_id in room_positions:
                bx, by = room_positions[conn_id]
                _draw_minimap_connection(grid, ax, ay, bx, by)

    # Footer
    total = len(dungeon_rooms)
    visited_count = len(visited_rooms)
    footer_parts = []
    if doom is not None:
        footer_parts.append(f"Doom:{doom}/20")
    footer_parts.append(f"Rm {visited_count}/{total}")
    footer = "  ".join(footer_parts)

    if not rich_mode:
        lines = [" ".join(row) for row in grid]
        lines.append(f"  {footer}")
        return "\n".join(lines)

    # Rich mode: colored symbols
    theme_cfg = THEMES[theme] if theme else THEMES[MapTheme.RUST]
    result = Text()
    _SYM_STYLES = {
        _MM_PLAYER: theme_cfg.color_player,
        _MM_QUEST: theme_cfg.color_quest,
        _MM_VISITED: theme_cfg.color_visited,
        _MM_UNEXPLORED: "dim white",
        _MM_TREASURE: theme_cfg.color_loot,
        _MM_BOSS: theme_cfg.color_enemy,
        _MM_LOCKED: "bold yellow",
        _MM_GATE: "bold green",
        _MM_PORTAL: "bold magenta",
        _MM_BORDER: "bold blue",
        _MM_H_CONN: "dim white",
        _MM_V_CONN: "dim white",
        _MM_EMPTY: "dim grey30",
    }
    for y, row in enumerate(grid):
        for x, sym in enumerate(row):
            style = _SYM_STYLES.get(sym, "dim white")
            result.append(sym, style=style)
            if x < grid_size - 1:
                result.append(" ", style="dim grey30")
        result.append("\n")
    result.append(f"  {footer}", style="dim white")
    return result


def rooms_to_minimap_dict(graph) -> Dict[int, dict]:
    """Convert a DungeonGraph to the dict format expected by render_mini_map().

    Helper to avoid repeating the dict comprehension in callers.
    """
    if not graph or not hasattr(graph, 'rooms'):
        return {}
    return {
        rid: {
            "x": r.x,
            "y": r.y,
            "width": r.width,
            "height": r.height,
            "connections": list(r.connections),
            "room_type": r.room_type.name if hasattr(r, 'room_type') else "NORMAL",
            "is_locked": getattr(r, 'is_locked', False),
        }
        for rid, r in graph.rooms.items()
    }


# =============================================================================
# VIEWPORT CONTROLLER
# =============================================================================

def render_spatial_map(rooms: Dict[int, SpatialRoom],
                      player_room_id: int,
                      theme: MapTheme,
                      stats: Dict = None,
                      viewport_width: int = 60,
                      viewport_height: int = 25,
                      console: Console = None,
                      player_pos: Optional[Tuple[int, int]] = None,
                      map_title: Optional[str] = None,
                      max_width: Optional[int] = None,
                      max_height: Optional[int] = None) -> Layout:
    """
    Main entry point. Returns a Rich Layout with Map (Left) and Sidebar (Right).
    Handles viewport centering on player.

    Args:
        player_pos: Exact (x, y) grid position for the @ marker. If None,
                    defaults to center of player_room_id.
        map_title: Custom panel title. If None, defaults per theme:
                   VILLAGE → "EMBERHOME", CANOPY → "THE CANOPY",
                   everything else → "THE DEPTHS".
        max_width: If provided, cap ``viewport_width`` to this value.
                   Useful for narrow-terminal layouts.
        max_height: If provided, cap ``viewport_height`` to this value.
                    Useful for narrow-terminal layouts.
    """
    if max_width is not None:
        viewport_width = min(viewport_width, max_width)
    if max_height is not None:
        viewport_height = min(viewport_height, max_height)
    renderer = SpatialGridRenderer(rooms, theme)

    # Inject player marker at exact grid position
    if player_pos:
        renderer.grid[player_pos] = ("@", THEMES[theme].color_player)

    # 1. Determine center point (follow the player marker)
    if player_pos:
        center_x, center_y = player_pos
    elif player_room_id in rooms:
        pr = rooms[player_room_id]
        center_x = pr.x + pr.width // 2
        center_y = pr.y + pr.height // 2
    else:
        center_x, center_y = 0, 0

    # 2. Calculate Viewport Bounds
    # Ensure even number of chars around center
    half_w = viewport_width // 2
    half_h = viewport_height // 2
    
    start_x = center_x - half_w
    start_y = center_y - half_h
    end_x = center_x + half_w
    end_y = center_y + half_h

    # 3. Build Text Object
    map_text = Text()
    
    for y in range(start_y, end_y):
        line = Text()
        for x in range(start_x, end_x):
            if (x, y) in renderer.grid:
                char, style = renderer.grid[(x, y)]
                line.append(char, style=style)
            else:
                # Void space
                line.append(" ", style="black")
        map_text.append(line)
        map_text.append("\n")

    # 4. Construct Layout
    main_layout = Layout()
    main_layout.split_row(
        Layout(name="map", ratio=7),
        Layout(name="sidebar", ratio=3)
    )

    # Map Panel
    if map_title is None:
        _THEME_TITLES = {
            MapTheme.VILLAGE: "EMBERHOME",
            MapTheme.CANOPY: "THE CANOPY",
        }
        map_title = _THEME_TITLES.get(theme, "THE DEPTHS")
    map_title = f"[bold {THEMES[theme].color_current}]{map_title}[/]"
    main_layout["map"].update(
        Panel(map_text, title=map_title, border_style=THEMES[theme].color_visited, box=box.ROUNDED)
    )

    # Sidebar Panel
    if stats:
        mini_map = stats.get("mini_map")
        sidebar_content = build_stats_sidebar(stats, THEMES[theme], mini_map=mini_map)
        main_layout["sidebar"].update(
            Panel(sidebar_content, title="[bold white]SURVEY[/]", border_style="white", box=box.ROUNDED)
        )
    else:
        main_layout["sidebar"].update(Panel("", title="Survey"))

    return main_layout


def build_stats_sidebar(stats: Dict, theme_cfg: ThemeConfig,
                        mini_map: Optional[Text] = None) -> Table:
    """Helper to build the stats table.

    stats keys:
        room_name, room_description, exits, enemies, loot, detail (optional).
        If 'detail' is set, it replaces the default room description block
        (used by look/inspect/gear commands to push info to the sidebar).
    """
    table = Table.grid(padding=0, expand=True)
    table.add_column(justify="left")

    # Room Name
    table.add_row(Text(stats.get("room_name", "Unknown"), style=f"bold underline {theme_cfg.color_current}"))
    table.add_row("")

    # Detail override OR room description
    detail = stats.get("detail")
    if detail:
        table.add_row(Text(detail, style="white"))
        table.add_row("")
    else:
        desc = stats.get("room_description", "...")
        table.add_row(Text(desc, style="dim white"))
        table.add_row("")

    # Exits
    exits = stats.get("exits", [])
    if exits:
        table.add_row(Text(f"Exits: {', '.join(exits)}", style="white"))
    else:
        table.add_row(Text("Exits: None", style="dim red"))
    table.add_row("")

    # Entities
    enemies = stats.get("enemies", [])
    if enemies:
        table.add_row(Text("HOSTILES:", style=f"bold {theme_cfg.color_enemy}"))
        for e in enemies:
            dr_tag = f" [DR {e['dr']}]" if e.get("dr", 0) > 0 else ""
            boss_tag = " [BOSS]" if e.get("is_boss") else ""
            table.add_row(Text(f" {e['name']}{boss_tag}{dr_tag}", style=theme_cfg.color_enemy))
    else:
        table.add_row(Text("No Hostiles", style="dim green"))

    loot = stats.get("loot", [])
    if loot:
        table.add_row(Text("LOOT:", style=f"bold {theme_cfg.color_loot}"))
        for item in loot:
            table.add_row(Text(f" {item['name']}", style=theme_cfg.color_loot))

    furniture = stats.get("furniture", [])
    if furniture:
        table.add_row(Text("OBJECTS:", style=f"bold {theme_cfg.color_furniture}"))
        for obj in furniture:
            ctype = obj.get("container_type", "furniture") if isinstance(obj, dict) else "furniture"
            if ctype == "chest":
                sym, col = theme_cfg.symbol_chest, theme_cfg.color_chest
            elif ctype == "rack":
                sym, col = theme_cfg.symbol_rack, theme_cfg.color_rack
            else:
                sym, col = theme_cfg.symbol_furniture, theme_cfg.color_furniture
            table.add_row(Text(f" {sym} {obj.get('name', '???')}", style=col))

    # Mini-map (appended at bottom of sidebar)
    if mini_map:
        table.add_row("")
        table.add_row(Text("MAP:", style=f"bold {theme_cfg.color_current}"))
        table.add_row(mini_map if isinstance(mini_map, Text) else Text(str(mini_map)))

    return table

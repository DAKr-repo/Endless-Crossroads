#!/usr/bin/env python3
"""
codex.spatial.world_map_renderer -- Point-Crawl World Map Renderer
===================================================================

Renders world-level location graphs as point-crawl maps with:
- Single-character location icons on a grid
- Route lines between connected locations (Manhattan routing)
- Fog of war: current=bright, visited=normal, known=dim, unknown=hidden
- Terrain-based coloring
- Viewport centering on current location

NOT the same as SpatialGridRenderer (room-interior dungeon maps).
This renders high-level overworld navigation.

Data structures (WorldLocation, WorldRoute, WorldMap) are defined here
because no separate world-map engine exists yet.  Callers that build
their own engine should produce objects that satisfy the same duck-typed
interface.

Version: 1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from rich import box
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# =============================================================================
# LOCATION TYPE ICONS
# =============================================================================

# Location type -> display icon (single ASCII character)
LOCATION_ICONS: Dict[str, str] = {
    "city": "C",
    "town": "T",
    "village": "v",
    "ruins": "R",
    "dungeon_entrance": "D",
    "wilderness_poi": "*",
    "camp": "c",
}

# Human-readable labels for the sidebar
LOCATION_TYPE_LABELS: Dict[str, str] = {
    "city": "City",
    "town": "Town",
    "village": "Village",
    "ruins": "Ruins",
    "dungeon_entrance": "Dungeon",
    "wilderness_poi": "Point of Interest",
    "camp": "Camp",
}


# =============================================================================
# TERRAIN COLORS
# =============================================================================

# Terrain -> Rich style (applied to location icon and route lines that cross it)
TERRAIN_COLORS: Dict[str, str] = {
    "coastal": "bold cyan",
    "forest": "bold green",
    "mountain": "bold white",
    "plains": "bold yellow",
    "desert": "bold dark_goldenrod",
    "swamp": "bold dark_green",
    "urban": "bold grey74",
    "underground": "bold magenta",
    "tundra": "bold blue",
}

# Fallback when terrain is unknown
_DEFAULT_TERRAIN_STYLE = "bold white"


# =============================================================================
# VISIBILITY CONSTANTS
# =============================================================================

class LocationVisibility:
    """Integer constants for location fog-of-war visibility levels."""

    HIDDEN = 0    # Unknown — not rendered at all
    KNOWN = 1     # Name visible, rendered dim (adjacent to visited)
    VISITED = 2   # Fully explored, normal colour
    CURRENT = 3   # Player is here — bright + reversed


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class WorldLocation:
    """A single named place on the world map.

    Attributes:
        id: Unique string identifier (e.g. ``"emberhome"``).
        display_name: Human-readable name shown in the sidebar.
        x: Horizontal world coordinate.
        y: Vertical world coordinate (increases downward, like screen coords).
        location_type: One of the keys in ``LOCATION_ICONS``.
        terrain: One of the keys in ``TERRAIN_COLORS``.
        connections: List of location IDs reachable from this node.
        services: Optional list of service strings (e.g. ``["inn", "forge"]``).
        icon: Override the auto-computed icon.  If ``None``, type-based icon is used.
        description: Short flavour text shown in the sidebar when this is current.
    """

    id: str
    display_name: str
    x: int
    y: int
    location_type: str = "wilderness_poi"
    terrain: str = "plains"
    connections: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    icon: Optional[str] = None
    description: str = ""


@dataclass
class WorldRoute:
    """A navigable route between two WorldLocations.

    Routes are bidirectional by convention; callers should add both
    directions to ``WorldLocation.connections`` when building the graph.

    Attributes:
        from_id: Source location ID.
        to_id: Destination location ID.
        travel_days: Estimated days of travel (integer or float).
        terrain: Predominant terrain along the route.
        danger_level: 0=Safe … 4=Deadly.
    """

    from_id: str
    to_id: str
    travel_days: float = 1.0
    terrain: str = "plains"
    danger_level: int = 1


@dataclass
class WorldMap:
    """Container for all world map data.

    Attributes:
        locations: Mapping of location ID → WorldLocation.
        routes: List of WorldRoute objects.
        bounds: ``(width, height)`` of the coordinate space.  Used to
                scale world coords onto the viewport grid.
        title: Display name for the world (shown in the map panel title).
    """

    locations: Dict[str, WorldLocation] = field(default_factory=dict)
    routes: List[WorldRoute] = field(default_factory=list)
    bounds: Tuple[int, int] = (100, 100)
    title: str = "THE WORLD"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def add_location(self, loc: WorldLocation) -> None:
        """Register a location and update connections symmetrically."""
        self.locations[loc.id] = loc

    def add_route(self, route: WorldRoute) -> None:
        """Add a route and ensure both endpoints know about each other."""
        self.routes.append(route)
        from_loc = self.locations.get(route.from_id)
        to_loc = self.locations.get(route.to_id)
        if from_loc and route.to_id not in from_loc.connections:
            from_loc.connections.append(route.to_id)
        if to_loc and route.from_id not in to_loc.connections:
            to_loc.connections.append(route.from_id)

    def get_route(self, from_id: str, to_id: str) -> Optional[WorldRoute]:
        """Return the route object between two locations, or ``None``."""
        for r in self.routes:
            if (r.from_id == from_id and r.to_id == to_id) or \
               (r.from_id == to_id and r.to_id == from_id):
                return r
        return None


# =============================================================================
# WORLD MAP RENDERER
# =============================================================================

class WorldMapRenderer:
    """Renders a WorldMap as a point-crawl grid with route connections.

    Grid cells hold a single character: either a location icon, a route
    line character (``-`` horizontal, ``|`` vertical), or a blank space.
    The grid is viewport-clipped and centred on the current location.
    """

    # Characters used for route lines
    _ROUTE_H = "-"
    _ROUTE_V = "|"
    _ROUTE_CROSS = "+"
    _ROUTE_STYLE = "dim white"

    def __init__(
        self,
        world_map: WorldMap,
        current_location_id: str,
        visited: Set[str],
        known: Set[str],
    ) -> None:
        """
        Args:
            world_map: WorldMap instance with locations and routes.
            current_location_id: ID of the player's current location.
            visited: Set of location IDs the player has been to.
            known: Set of location IDs the player knows about (not yet visited).
        """
        self.world_map = world_map
        self.current_id = current_location_id
        self.visited = visited
        self.known = known

    # ------------------------------------------------------------------
    # Visibility & style helpers
    # ------------------------------------------------------------------

    def _get_visibility(self, location_id: str) -> int:
        """Return the LocationVisibility level for a location ID."""
        if location_id == self.current_id:
            return LocationVisibility.CURRENT
        if location_id in self.visited:
            return LocationVisibility.VISITED
        if location_id in self.known:
            return LocationVisibility.KNOWN
        return LocationVisibility.HIDDEN

    def _get_icon(self, loc: WorldLocation) -> str:
        """Return the single-character display icon for a location."""
        if loc.icon:
            return loc.icon
        return LOCATION_ICONS.get(loc.location_type, "?")

    def _get_style(self, loc: WorldLocation, visibility: int) -> str:
        """Return a Rich style string based on terrain and visibility level."""
        base = TERRAIN_COLORS.get(loc.terrain, _DEFAULT_TERRAIN_STYLE)
        # Strip leading "bold " so we can apply dim variant cleanly
        bare = base.replace("bold ", "")
        if visibility == LocationVisibility.CURRENT:
            # Bright reverse (standout) to make the player marker pop
            return f"bold reverse {bare}"
        elif visibility == LocationVisibility.VISITED:
            return base
        elif visibility == LocationVisibility.KNOWN:
            return f"dim {bare}"
        # HIDDEN — caller should not reach here, but handle gracefully
        return "dim grey30"

    # ------------------------------------------------------------------
    # Internal grid builder
    # ------------------------------------------------------------------

    def _build_full_grid(
        self, viewport_width: int, viewport_height: int
    ) -> Tuple[Dict[Tuple[int, int], Tuple[str, str]], int, int]:
        """Build a (char, style) dict keyed by (screen_x, screen_y).

        The grid is in *screen space* — coordinates are relative to the
        top-left corner of the viewport, not world space.  The current
        location is always placed at the viewport centre.

        Returns:
            Tuple of:
              - grid: dict mapping (sx, sy) → (char, style)
              - center_sx: screen X of the current location
              - center_sy: screen Y of the current location
        """
        grid: Dict[Tuple[int, int], Tuple[str, str]] = {}

        current_loc = self.world_map.locations.get(self.current_id)
        if not current_loc:
            return grid, viewport_width // 2, viewport_height // 2

        # World-coordinate origin = current location
        cx_world, cy_world = current_loc.x, current_loc.y

        # Scale: map world-coord range onto the viewport
        # We want the full world to fit in (viewport - 4) cells with some margin.
        bw, bh = self.world_map.bounds
        # Avoid division by zero; default to 1 if bounds are degenerate
        scale_x = max(1.0, bw / max(1, viewport_width - 4))
        scale_y = max(1.0, bh / max(1, viewport_height - 4))

        center_sx = viewport_width // 2
        center_sy = viewport_height // 2

        # --- Pass 1: compute screen positions for visible locations ---
        loc_screen_pos: Dict[str, Tuple[int, int]] = {}
        for loc_id, loc in self.world_map.locations.items():
            vis = self._get_visibility(loc_id)
            if vis == LocationVisibility.HIDDEN:
                continue
            sx = center_sx + round((loc.x - cx_world) / scale_x)
            sy = center_sy + round((loc.y - cy_world) / scale_y)
            # Clamp to viewport (leave 1-cell border)
            sx = max(1, min(viewport_width - 2, sx))
            sy = max(1, min(viewport_height - 2, sy))
            loc_screen_pos[loc_id] = (sx, sy)

        # --- Pass 2: draw route lines (Manhattan L-routing) ---
        for route in self.world_map.routes:
            from_pos = loc_screen_pos.get(route.from_id)
            to_pos = loc_screen_pos.get(route.to_id)
            if not from_pos or not to_pos:
                continue
            ax, ay = from_pos
            bx, by = to_pos
            route_style = self._ROUTE_STYLE

            # Horizontal leg: travel from ax to bx along row ay
            x_step = 1 if bx > ax else -1
            for x in range(ax + x_step, bx, x_step):
                coord = (x, ay)
                existing = grid.get(coord)
                if existing is None:
                    grid[coord] = (self._ROUTE_H, route_style)
                elif existing[0] == self._ROUTE_V:
                    # Crossing point
                    grid[coord] = (self._ROUTE_CROSS, route_style)

            # Vertical leg: travel from ay to by along column bx
            y_step = 1 if by > ay else -1
            for y in range(ay + y_step, by, y_step):
                coord = (bx, y)
                existing = grid.get(coord)
                if existing is None:
                    grid[coord] = (self._ROUTE_V, route_style)
                elif existing[0] == self._ROUTE_H:
                    grid[coord] = (self._ROUTE_CROSS, route_style)

            # Draw the corner connector at (bx, ay) if it's empty space
            corner = (bx, ay)
            if grid.get(corner) is None:
                grid[corner] = ("+", route_style)

        # --- Pass 3: paint location icons (over routes, so icons win) ---
        for loc_id, (sx, sy) in loc_screen_pos.items():
            loc = self.world_map.locations[loc_id]
            vis = self._get_visibility(loc_id)
            icon = self._get_icon(loc)
            style = self._get_style(loc, vis)
            grid[(sx, sy)] = (icon, style)

        return grid, center_sx, center_sy

    # ------------------------------------------------------------------
    # Public render methods
    # ------------------------------------------------------------------

    def render(self, viewport_width: int = 60, viewport_height: int = 25) -> Layout:
        """Render the full world map with a sidebar legend.

        Returns a Rich Layout split into:
          - Left (ratio=7): Map panel with the point-crawl grid.
          - Right (ratio=3): Sidebar listing visible locations and a legend.

        Args:
            viewport_width: Character width of the map content area.
            viewport_height: Character height of the map content area.
        """
        grid, _, _ = self._build_full_grid(viewport_width, viewport_height)

        # --- Assemble map Text ---
        map_text = Text()
        for sy in range(viewport_height):
            for sx in range(viewport_width):
                cell = grid.get((sx, sy))
                if cell:
                    char, style = cell
                    map_text.append(char, style=style)
                else:
                    map_text.append(" ", style="black")
            map_text.append("\n")

        # --- Map panel title ---
        map_title = f"[bold cyan]{self.world_map.title}[/]"

        # --- Build Layout ---
        main_layout = Layout()
        main_layout.split_row(
            Layout(name="map", ratio=7),
            Layout(name="sidebar", ratio=3),
        )

        main_layout["map"].update(
            Panel(
                map_text,
                title=map_title,
                border_style="dim cyan",
                box=box.ROUNDED,
            )
        )
        main_layout["sidebar"].update(
            Panel(
                self._build_sidebar(),
                title="[bold white]LOCATIONS[/]",
                border_style="white",
                box=box.ROUNDED,
            )
        )

        return main_layout

    def render_mini_world_map(self, grid_size: int = 9) -> Text:
        """Render a compact mini world map for sidebar embedding.

        Shows locations as single chars in a small grid, centred on the
        current location.  Similar to ``render_mini_map()`` in
        ``map_renderer.py`` but for world-level point-crawl navigation.

        Args:
            grid_size: Dimension of the square character grid (default 9×9).

        Returns:
            Rich Text object ready to embed in any sidebar or panel.
        """
        current_loc = self.world_map.locations.get(self.current_id)
        if not current_loc:
            return Text("(no world map)")

        cx, cy = current_loc.x, current_loc.y
        mid = grid_size // 2

        # Build 2D character + style grids
        grid = [[" "] * grid_size for _ in range(grid_size)]
        grid_styles = [["dim grey30"] * grid_size for _ in range(grid_size)]
        loc_positions: Dict[str, Tuple[int, int]] = {}

        bw, bh = self.world_map.bounds
        # Scale factors: how many world units per grid cell
        scale_x = max(1, bw // max(1, grid_size * 2))
        scale_y = max(1, bh // max(1, grid_size * 2))

        for loc_id, loc in self.world_map.locations.items():
            vis = self._get_visibility(loc_id)
            if vis == LocationVisibility.HIDDEN:
                continue

            gx = mid + (loc.x - cx) // scale_x
            gy = mid + (loc.y - cy) // scale_y
            gx = max(0, min(grid_size - 1, gx))
            gy = max(0, min(grid_size - 1, gy))

            loc_positions[loc_id] = (gx, gy)
            grid[gy][gx] = self._get_icon(loc)
            grid_styles[gy][gx] = self._get_style(loc, vis)

        # Draw Manhattan route connections between visible locations
        for route in self.world_map.routes:
            from_pos = loc_positions.get(route.from_id)
            to_pos = loc_positions.get(route.to_id)
            if not from_pos or not to_pos:
                continue
            ax, ay = from_pos
            bx, by = to_pos

            # Horizontal leg along row ay
            for x in range(min(ax, bx) + 1, max(ax, bx)):
                if grid[ay][x] == " ":
                    grid[ay][x] = "-"
                    grid_styles[ay][x] = "dim white"

            # Vertical leg along column bx
            for y in range(min(ay, by) + 1, max(ay, by)):
                if grid[y][bx] == " ":
                    grid[y][bx] = "|"
                    grid_styles[y][bx] = "dim white"

        # Assemble Rich Text
        result = Text()
        for y in range(grid_size):
            for x in range(grid_size):
                result.append(grid[y][x], style=grid_styles[y][x])
                if x < grid_size - 1:
                    result.append(" ", style="dim grey30")
            result.append("\n")

        # Footer: discovery progress
        visited_count = sum(
            1 for lid in self.world_map.locations if lid in self.visited
        )
        total = len(self.world_map.locations)
        result.append(f"  {visited_count}/{total} discovered", style="dim white")

        return result

    # ------------------------------------------------------------------
    # Sidebar builder
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> Table:
        """Build the sidebar table listing visible locations and a legend.

        Layout (top to bottom):
          1. Current location name + description
          2. Visited locations list
          3. Known (fog) locations list
          4. Icon / terrain legend
        """
        table = Table.grid(padding=0, expand=True)
        table.add_column(justify="left")

        current_loc = self.world_map.locations.get(self.current_id)

        # --- Current location header ---
        if current_loc:
            table.add_row(
                Text(current_loc.display_name, style="bold reverse cyan")
            )
            loc_type_label = LOCATION_TYPE_LABELS.get(
                current_loc.location_type, current_loc.location_type.title()
            )
            table.add_row(Text(f"  {loc_type_label}", style="dim cyan"))
            if current_loc.description:
                table.add_row(Text(current_loc.description, style="dim white"))
            if current_loc.services:
                services_str = ", ".join(current_loc.services)
                table.add_row(Text(f"  Services: {services_str}", style="dim green"))
        else:
            table.add_row(Text("Unknown Location", style="bold red"))
        table.add_row("")

        # --- Visited locations ---
        visited_locs = [
            loc for lid, loc in self.world_map.locations.items()
            if lid in self.visited and lid != self.current_id
        ]
        if visited_locs:
            table.add_row(Text("VISITED:", style="bold white"))
            for loc in visited_locs:
                icon = self._get_icon(loc)
                terrain_style = TERRAIN_COLORS.get(loc.terrain, _DEFAULT_TERRAIN_STYLE)
                table.add_row(
                    Text(f"  {icon} {loc.display_name}", style=terrain_style)
                )
            table.add_row("")

        # --- Known (fog) locations ---
        known_locs = [
            loc for lid, loc in self.world_map.locations.items()
            if lid in self.known and lid not in self.visited and lid != self.current_id
        ]
        if known_locs:
            table.add_row(Text("KNOWN:", style="bold dim white"))
            for loc in known_locs:
                icon = self._get_icon(loc)
                bare_terrain = TERRAIN_COLORS.get(
                    loc.terrain, _DEFAULT_TERRAIN_STYLE
                ).replace("bold ", "")
                table.add_row(
                    Text(f"  {icon} {loc.display_name}", style=f"dim {bare_terrain}")
                )
            table.add_row("")

        # --- Route legend (terrain types present in routes) ---
        terrain_set: Set[str] = set()
        for loc in self.world_map.locations.values():
            if self._get_visibility(loc.id) != LocationVisibility.HIDDEN:
                terrain_set.add(loc.terrain)
        if terrain_set:
            table.add_row(Text("TERRAIN:", style="bold dim white"))
            for terrain in sorted(terrain_set):
                style = TERRAIN_COLORS.get(terrain, _DEFAULT_TERRAIN_STYLE)
                label = terrain.replace("_", " ").title()
                table.add_row(Text(f"  {label}", style=style))
            table.add_row("")

        # --- Icon legend ---
        table.add_row(Text("ICONS:", style="bold dim white"))
        for loc_type, icon in LOCATION_ICONS.items():
            label = LOCATION_TYPE_LABELS.get(loc_type, loc_type)
            table.add_row(Text(f"  {icon} {label}", style="dim white"))

        return table


# =============================================================================
# PUBLIC ENTRY POINTS
# =============================================================================

def render_world_map(
    world_map: WorldMap,
    current_location_id: str,
    visited: Set[str],
    known: Set[str],
    viewport_width: int = 60,
    viewport_height: int = 25,
) -> Layout:
    """Main entry point for world map rendering.

    Args:
        world_map: Populated WorldMap instance.
        current_location_id: ID of the player's current location.
        visited: Set of location IDs the player has visited.
        known: Set of location IDs the player knows about but hasn't visited.
        viewport_width: Character width of the map content area.
        viewport_height: Character height of the map content area.

    Returns:
        A Rich Layout with a map panel (left, ratio=7) and sidebar (right, ratio=3).
    """
    renderer = WorldMapRenderer(world_map, current_location_id, visited, known)
    return renderer.render(viewport_width, viewport_height)


def render_travel_options(
    world_map: WorldMap,
    current_location_id: str,
    visited: Set[str],
) -> Panel:
    """Render available travel destinations from the current location.

    Produces a Rich Panel containing a table of connected locations with
    travel time, predominant terrain, and danger level.

    Args:
        world_map: Populated WorldMap instance.
        current_location_id: ID of the player's current location.
        visited: Set of visited location IDs (marks already-seen destinations).

    Returns:
        A Rich Panel ready to print or embed in a Layout.
    """
    current_loc = world_map.locations.get(current_location_id)
    if not current_loc:
        return Panel("No location data.", title="Travel")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("#", style="bold cyan", width=3)
    table.add_column("Destination", style="bold white")
    table.add_column("Days", style="yellow", width=5)
    table.add_column("Terrain", style="dim white")
    table.add_column("Danger", style="red", width=8)

    _DANGER_LABELS: Dict[int, str] = {
        0: "Safe",
        1: "Low",
        2: "Moderate",
        3: "High",
        4: "Deadly",
    }

    for i, conn_id in enumerate(current_loc.connections, 1):
        dest = world_map.locations.get(conn_id)
        if not dest:
            continue

        route = world_map.get_route(current_location_id, conn_id)
        days = str(route.travel_days) if route else "?"
        terrain = route.terrain.replace("_", " ").title() if route else "Unknown"
        danger = _DANGER_LABELS.get(route.danger_level, "?") if route else "?"

        visited_mark = " *" if conn_id in visited else ""
        table.add_row(
            str(i),
            f"{dest.display_name}{visited_mark}",
            days,
            terrain,
            danger,
        )

    if not current_loc.connections:
        table.add_row("-", "[dim]No routes known[/]", "-", "-", "-")

    return Panel(
        table,
        title=f"[bold]Travel from {current_loc.display_name}[/]",
        border_style="cyan",
    )

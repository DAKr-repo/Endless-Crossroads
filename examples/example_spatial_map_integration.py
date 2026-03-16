#!/usr/bin/env python3
"""
example_spatial_map_integration.py
===================================

Demonstrates how to integrate the spatial map renderer with codex_map_engine.
Shows the complete workflow from procedural generation to visual rendering.

Usage:
    python example_spatial_map_integration.py
"""

from codex.spatial.map_engine import CodexMapEngine, BurnwillowAdapter, ContentInjector
from codex.spatial.map_renderer import (
    render_spatial_map,
    MapTheme,
    SpatialRoom,
    RoomVisibility
)
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box


def main():
    console = Console()

    console.print("\n")
    console.print(Panel(
        Text("CODEX SPATIAL MAP — FULL INTEGRATION EXAMPLE", justify="center", style="bold cyan"),
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print("\n")

    # =========================================================================
    # STEP 1: Generate Procedural Dungeon (Geometry Only)
    # =========================================================================
    console.print(Text("STEP 1: Generating Dungeon Geometry", style="bold yellow"))
    console.print()

    engine = CodexMapEngine(seed=42)
    dungeon_graph = engine.generate(
        width=50,
        height=50,
        max_depth=4,
        min_room_size=5
    )

    console.print(f"  Seed: {dungeon_graph.seed}")
    console.print(f"  Dungeon Size: {dungeon_graph.width}x{dungeon_graph.height}")
    console.print(f"  Total Rooms: {len(dungeon_graph.rooms)}")
    console.print(f"  Start Room: {dungeon_graph.start_room_id}")
    console.print("\n")

    # =========================================================================
    # STEP 2: Populate with Burnwillow Content (Enemies, Loot, Hazards)
    # =========================================================================
    console.print(Text("STEP 2: Populating with Burnwillow Content", style="bold yellow"))
    console.print()

    adapter = BurnwillowAdapter(seed=42)
    injector = ContentInjector(adapter)
    populated_rooms = injector.populate_all(dungeon_graph)

    console.print(f"  Populated {len(populated_rooms)} rooms with content")
    console.print("\n")

    # =========================================================================
    # STEP 3: Simulate Player Exploration
    # =========================================================================
    console.print(Text("STEP 3: Simulating Player Exploration", style="bold yellow"))
    console.print()

    # Start at the start room
    current_room_id = dungeon_graph.start_room_id
    visited_room_ids = {current_room_id}

    # Simulate exploring a few rooms
    # (In real game, this would be driven by player input)
    exploration_path = [current_room_id]
    for _ in range(3):  # Explore 3 more rooms
        current_room = dungeon_graph.get_room(current_room_id)
        if current_room and current_room.connections:
            # Move to first connected room
            next_room_id = current_room.connections[0]
            if next_room_id not in visited_room_ids:
                visited_room_ids.add(next_room_id)
                current_room_id = next_room_id
                exploration_path.append(current_room_id)

    console.print(f"  Exploration Path: {' → '.join(map(str, exploration_path))}")
    console.print(f"  Visited Rooms: {len(visited_room_ids)}")
    console.print(f"  Current Room: {current_room_id}")
    console.print("\n")

    # =========================================================================
    # STEP 4: Convert to SpatialRooms for Rendering
    # =========================================================================
    console.print(Text("STEP 4: Converting to Spatial Representation", style="bold yellow"))
    console.print()

    spatial_rooms = {}

    for room_id, populated_room in populated_rooms.items():
        geometry = populated_room.geometry
        content = populated_room.content

        # Determine visibility
        if room_id == current_room_id:
            visibility = RoomVisibility.CURRENT
        elif room_id in visited_room_ids:
            visibility = RoomVisibility.VISITED
        else:
            visibility = RoomVisibility.UNEXPLORED

        # Create SpatialRoom
        spatial_room = SpatialRoom.from_map_engine_room(
            room=geometry,
            visibility=visibility
        )

        # Add content (enemies, loot) for rendering
        if visibility == RoomVisibility.CURRENT:
            spatial_room.enemies = content.get("enemies", [])
            spatial_room.loot = content.get("loot", [])

        spatial_rooms[room_id] = spatial_room

    console.print(f"  Converted {len(spatial_rooms)} rooms to SpatialRoom format")
    console.print("\n")

    # =========================================================================
    # STEP 5: Build Stats Sidebar Data
    # =========================================================================
    current_pop_room = populated_rooms[current_room_id]
    current_content = current_pop_room.content
    current_geom = current_pop_room.geometry

    # Get available exits (connected rooms)
    exits = []
    for conn_id in current_geom.connections:
        conn_room = dungeon_graph.get_room(conn_id)
        if conn_room:
            # Determine direction (simplified)
            if conn_room.y < current_geom.y:
                exits.append("N")
            elif conn_room.y > current_geom.y:
                exits.append("S")
            if conn_room.x < current_geom.x:
                exits.append("W")
            elif conn_room.x > current_geom.x:
                exits.append("E")

    stats = {
        "room_name": f"Room {current_room_id} ({current_geom.room_type.value.capitalize()})",
        "room_description": current_content.get("description", "An empty chamber."),
        "hp_current": 12,  # Example player stats
        "hp_max": 15,
        "depth": current_geom.tier,
        "enemies": current_content.get("enemies", []),
        "loot": current_content.get("loot", []),
        "exits": exits
    }

    # =========================================================================
    # STEP 6: Render All Three Themes
    # =========================================================================
    console.print(Text("STEP 5: Rendering Spatial Maps", style="bold yellow"))
    console.print("\n")

    themes = [
        (MapTheme.RUST, "BURNWILLOW (Industrial Decay)"),
        (MapTheme.STONE, "D&D (Classic Fantasy)"),
        (MapTheme.GOTHIC, "ASHBURN HIGH (Victorian Horror)")
    ]

    for theme_enum, theme_name in themes:
        console.print(Text(f"═══ {theme_name} ═══", style="bold cyan"))
        console.print()

        map_panel = render_spatial_map(
            rooms=spatial_rooms,
            player_room_id=current_room_id,
            theme=theme_enum,
            stats=stats,
            viewport_width=50,
            viewport_height=22,
            console=console
        )

        console.print(map_panel)
        console.print("\n")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    console.print(Panel(
        Text("Integration example complete!\n\nWorkflow:\n"
             "1. Generate dungeon geometry (codex_map_engine)\n"
             "2. Populate with content (BurnwillowAdapter)\n"
             "3. Track player exploration (visited_room_ids)\n"
             "4. Convert to SpatialRoom format\n"
             "5. Render with theme-specific tilesets\n\n"
             "Next: Integrate into game loop with player input!",
             justify="left", style="green"),
        title="[bold green]SUCCESS[/]",
        border_style="green"
    ))
    console.print("\n")


if __name__ == "__main__":
    main()

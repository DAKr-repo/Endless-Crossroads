#!/usr/bin/env python3
"""
Tests for codex.spatial.map_renderer — Theme showcase + API verification.
"""
import pytest
from codex.spatial.map_renderer import (
    Console, Panel, Text, box,
    MapTheme, SpatialRoom, RoomVisibility, THEMES,
    render_spatial_map, render_mini_map, build_stats_sidebar,
)


def _create_sample_rooms():
    """Build a small dungeon of 4 SpatialRoom objects for render_spatial_map."""
    return {
        0: SpatialRoom(id=0, x=0, y=0, width=5, height=3,
                        visibility=RoomVisibility.CURRENT, connections=[1, 2]),
        1: SpatialRoom(id=1, x=8, y=0, width=5, height=3,
                        visibility=RoomVisibility.VISITED, connections=[0, 3]),
        2: SpatialRoom(id=2, x=0, y=6, width=5, height=3,
                        visibility=RoomVisibility.VISITED, connections=[0]),
        3: SpatialRoom(id=3, x=8, y=6, width=5, height=3,
                        visibility=RoomVisibility.HIDDEN, connections=[1]),
    }


def _create_minimap_rooms():
    """Build dict-format rooms for render_mini_map (expects Dict[int, dict])."""
    return {
        0: {"x": 0, "y": 0, "width": 5, "height": 3, "connections": [1, 2]},
        1: {"x": 8, "y": 0, "width": 5, "height": 3, "connections": [0, 3]},
        2: {"x": 0, "y": 6, "width": 5, "height": 3, "connections": [0]},
        3: {"x": 8, "y": 6, "width": 5, "height": 3, "connections": [1]},
    }


class TestMapRendererImports:
    def test_map_theme_enum(self):
        assert MapTheme.RUST.value == "RUST"
        assert MapTheme.STONE.value == "STONE"
        assert MapTheme.GOTHIC.value == "GOTHIC"

    def test_spatial_room_construction(self):
        room = SpatialRoom(id=0, x=0, y=0, width=5, height=3)
        assert room.id == 0
        assert room.visibility == RoomVisibility.HIDDEN

    def test_room_visibility_enum(self):
        assert RoomVisibility.CURRENT is not None
        assert RoomVisibility.VISITED is not None
        assert RoomVisibility.HIDDEN is not None


class TestRenderSpatialMap:
    def test_returns_layout(self):
        rooms = _create_sample_rooms()
        stats = {"hp_current": 8, "hp_max": 15, "doom_clock": 4, "doom_max": 10, "depth": 3}
        result = render_spatial_map(
            rooms=rooms,
            player_room_id=0,
            theme=MapTheme.RUST,
            stats=stats,
        )
        from rich.layout import Layout
        assert isinstance(result, Layout)

    def test_all_themes_render(self):
        rooms = _create_sample_rooms()
        stats = {"hp_current": 10, "hp_max": 10, "doom_clock": 0, "doom_max": 10, "depth": 1}
        for theme in [MapTheme.RUST, MapTheme.STONE, MapTheme.GOTHIC]:
            result = render_spatial_map(
                rooms=rooms,
                player_room_id=0,
                theme=theme,
                stats=stats,
            )
            assert result is not None, f"Theme {theme.value} returned None"


class TestMiniMap:
    def test_mini_map_returns_str(self):
        rooms = _create_minimap_rooms()
        result = render_mini_map(rooms, current_room_id=0, visited_rooms={0, 1})
        assert isinstance(result, str)
        assert "@" in result  # Player marker

    def test_mini_map_rich_mode(self):
        rooms = _create_minimap_rooms()
        result = render_mini_map(rooms, current_room_id=0, visited_rooms={0, 1},
                                  rich_mode=True, theme=MapTheme.RUST)
        from rich.text import Text
        assert isinstance(result, Text)


class TestStatsSidebar:
    def test_sidebar_returns_table(self):
        from rich.table import Table
        stats = {"hp_current": 8, "hp_max": 15, "doom_clock": 4, "doom_max": 10, "depth": 3}
        theme_cfg = THEMES[MapTheme.RUST]
        result = build_stats_sidebar(stats, theme_cfg)
        assert isinstance(result, Table)


# Visual showcase (run with: python tests/test_map_renderer.py)
def main():
    console = Console()
    console.print("\n")
    console.print(Panel(
        Text("CODEX MAP RENDERER — THEME SHOWCASE", justify="center", style="bold cyan"),
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print("\n")

    rooms = _create_sample_rooms()
    sample_stats = {
        "hp_current": 8, "hp_max": 15,
        "doom_clock": 4, "doom_max": 10, "depth": 3
    }

    themes_to_demo = [
        (MapTheme.RUST, "BURNWILLOW (Bioluminescent Decay)"),
        (MapTheme.STONE, "D&D (Classic Fantasy)"),
        (MapTheme.GOTHIC, "ASHBURN HIGH (Victorian Horror)"),
    ]

    for theme_enum, theme_name in themes_to_demo:
        console.print(Text(f"═══ {theme_name} ═══", style="bold yellow"))
        console.print()
        map_panel = render_spatial_map(
            rooms=rooms,
            theme=theme_enum,
            player_room_id=0,
            stats=sample_stats,
            console=console
        )
        console.print(map_panel)
        console.print("\n")

    console.print(Panel(
        Text("Map renderer showcase complete!", justify="center", style="bold green"),
        border_style="green"
    ))
    console.print("\n")


if __name__ == "__main__":
    main()

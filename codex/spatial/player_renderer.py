"""
codex/spatial/player_renderer.py - Player View Renderer
========================================================

Takes a StateFrame and produces a capture-optimized Rich Layout
with DM-only metadata stripped.

Designed for:
  - Standalone terminal viewer on external monitor (play_player_view.py)
  - PNG screenshot capture via ScryingEngine (Discord/Telegram)

Strips: trap_details, invisible_enemies, DM sidebar notes
Keeps: tactical map with FoW, visible enemies, loot, party vitals, mini-map

Version: 1.0 (WO V4.2)
"""

from typing import Dict, Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from codex.core.state_frame import StateFrame
from codex.spatial.map_renderer import (
    SpatialRoom, SpatialGridRenderer, RoomVisibility,
    MapTheme, THEMES, ThemeConfig,
    render_mini_map,
)


class PlayerRenderer:
    """Renders a player-safe Rich Layout from a StateFrame."""

    def __init__(self, theme: MapTheme = MapTheme.RUST,
                 viewport_width: int = 50, viewport_height: int = 20):
        self.theme = theme
        self.theme_cfg = THEMES[theme]
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

    def render(self, frame: StateFrame) -> Layout:
        """Build a player-safe Rich Layout from a StateFrame.

        Strips DM-only data (traps, invisible enemies) and builds
        a clean view suitable for external monitors or screenshots.

        WO-V9.0: Inserts battlefield panel between party and narrative
        when frame.battlefield is present.
        """
        root = Layout()

        sections = [
            Layout(name="title", size=3),
            Layout(name="main", ratio=6),
            Layout(name="party", size=3),
        ]
        if frame.battlefield:
            sections.append(Layout(name="battlefield", size=8))
        sections.append(Layout(name="narrative", size=6))

        root.split_column(*sections)

        # Title bar
        root["title"].update(self._build_title(frame))

        # Main: Map + Sidebar
        main = Layout()
        main.split_row(
            Layout(name="map", ratio=7),
            Layout(name="sidebar", ratio=3),
        )
        main["map"].update(self._build_map(frame))
        main["sidebar"].update(self._build_sidebar(frame))
        root["main"].update(main)

        # Party vitals bar
        root["party"].update(self._build_party_bar(frame))

        # WO-V9.0: Battlefield HUD (SaV+BoB crossover)
        if frame.battlefield:
            root["battlefield"].update(self._build_battlefield(frame.battlefield))

        # Narrative panel
        root["narrative"].update(self._build_narrative(frame))

        return root

    def _build_title(self, frame: StateFrame) -> Panel:
        """Title bar: system name + room name."""
        title = Text()
        system_name = frame.system_id.upper()
        title.append(f" {system_name} ", style=f"bold {self.theme_cfg.color_current} on #1a1a2e")
        title.append(f" :: {frame.room_name} ", style=f"dim {self.theme_cfg.color_visited}")
        if frame.doom is not None:
            title.append(f"  Doom: {frame.doom}", style=f"bold {self.theme_cfg.color_enemy}")
        title.append(f"  Turn: {frame.turn_number}", style="dim white")
        if frame.combat_mode:
            title.append(f"  ** COMBAT R{frame.combat_round} **",
                         style=f"bold {self.theme_cfg.color_enemy}")
        return Panel(title, box=box.HEAVY, border_style=self.theme_cfg.color_current)

    def _build_map(self, frame: StateFrame) -> Panel:
        """Tactical map with FoW from visited_rooms."""
        rooms = self._rebuild_spatial_rooms(frame)
        if not rooms:
            return Panel("No map data", title="MAP", border_style="dim")

        renderer = SpatialGridRenderer(rooms, self.theme)

        # Inject player marker
        if frame.player_pos:
            renderer.grid[frame.player_pos] = ("@", self.theme_cfg.color_player)

        # Center on player
        if frame.player_pos:
            center_x, center_y = frame.player_pos
        elif frame.current_room_id in rooms:
            pr = rooms[frame.current_room_id]
            center_x = pr.x + pr.width // 2
            center_y = pr.y + pr.height // 2
        else:
            center_x, center_y = 0, 0

        half_w = self.viewport_width // 2
        half_h = self.viewport_height // 2
        start_x = center_x - half_w
        start_y = center_y - half_h
        end_x = center_x + half_w
        end_y = center_y + half_h

        map_text = Text()
        for y in range(start_y, end_y):
            line = Text()
            for x in range(start_x, end_x):
                if (x, y) in renderer.grid:
                    char, style = renderer.grid[(x, y)]
                    line.append(char, style=style)
                else:
                    line.append(" ", style="black")
            map_text.append(line)
            map_text.append("\n")

        map_title = f"[bold {self.theme_cfg.color_current}]THE DEPTHS[/]"
        return Panel(map_text, title=map_title,
                     border_style=self.theme_cfg.color_visited, box=box.ROUNDED)

    def _build_sidebar(self, frame: StateFrame) -> Panel:
        """Stats sidebar — strips DM-only details, includes mini-map."""
        table = Table.grid(padding=0, expand=True)
        table.add_column(justify="left")

        # Room name
        table.add_row(Text(frame.room_name,
                           style=f"bold underline {self.theme_cfg.color_current}"))
        table.add_row("")

        # Room description (player-safe)
        table.add_row(Text(frame.room_description[:200] if frame.room_description else "...",
                           style="dim white"))
        table.add_row("")

        # Exits
        if frame.exits:
            exit_labels = []
            for ex in frame.exits:
                label = ex.get("direction", "?").upper()
                if ex.get("visited"):
                    label += "*"
                if ex.get("is_locked"):
                    label += " [LOCKED]"
                exit_labels.append(label)
            table.add_row(Text(f"Exits: {', '.join(exit_labels)}", style="white"))
        else:
            table.add_row(Text("Exits: None", style="dim red"))
        table.add_row("")

        # Visible enemies only (invisible_enemies stripped)
        if frame.enemies:
            table.add_row(Text("HOSTILES:", style=f"bold {self.theme_cfg.color_enemy}"))
            for e in frame.enemies:
                name = e.get("name", "Unknown")
                boss = " [BOSS]" if e.get("is_boss") else ""
                table.add_row(Text(f" {name}{boss}", style=self.theme_cfg.color_enemy))
        else:
            table.add_row(Text("No Hostiles", style="dim green"))

        # Loot
        if frame.loot:
            table.add_row(Text("LOOT:", style=f"bold {self.theme_cfg.color_loot}"))
            for item in frame.loot:
                name = item.get("name", "???") if isinstance(item, dict) else str(item)
                table.add_row(Text(f" {name}", style=self.theme_cfg.color_loot))

        # Furniture
        if frame.furniture:
            table.add_row(Text("OBJECTS:", style="bold white"))
            for obj in frame.furniture:
                name = obj.get("name", "???") if isinstance(obj, dict) else str(obj)
                table.add_row(Text(f" {name}", style="white"))

        # Trap hint (vague, not detailed)
        if frame.trap_details:
            table.add_row("")
            table.add_row(Text("The air feels charged...", style="dim yellow"))

        # Mini-map
        dungeon_dict = {rid: rdata for rid, rdata in frame.dungeon_rooms}
        if dungeon_dict:
            mini = render_mini_map(
                dungeon_dict, frame.current_room_id, set(frame.visited_rooms),
                rich_mode=True, theme=self.theme, doom=frame.doom,
            )
            table.add_row("")
            table.add_row(Text("MAP:", style=f"bold {self.theme_cfg.color_current}"))
            table.add_row(mini)

        return Panel(table, title="[bold white]SURVEY[/]",
                     border_style="white", box=box.ROUNDED)

    def _build_party_bar(self, frame: StateFrame) -> Panel:
        """Horizontal party vitals bar."""
        party_text = Text()
        for i, member in enumerate(frame.party):
            if i > 0:
                party_text.append("  |  ", style="dim")

            name = member.get("name", "?")
            hp = member.get("hp", 0)
            max_hp = member.get("max_hp", 1)
            alive = member.get("alive", True)
            is_minion = member.get("is_minion", False)

            minion_tag = "[S] " if is_minion else ""
            active_tag = "[>] " if name == frame.active_character else ""

            if not alive:
                party_text.append(f" {active_tag}{minion_tag}{name} ", style="dim strike")
                party_text.append(f"DEAD", style="dim strike")
            else:
                party_text.append(f" {active_tag}{minion_tag}{name} ",
                                  style=f"bold {self.theme_cfg.color_player}")
                hp_style = "bold red" if hp <= max_hp // 3 else "bold white"
                party_text.append(f"HP:{hp}/{max_hp}", style=hp_style)

        return Panel(party_text, box=box.SIMPLE, border_style="dim")

    def _build_narrative(self, frame: StateFrame) -> Panel:
        """Narrative scroll: last action + room description."""
        parts = Text()

        if frame.last_action:
            parts.append(frame.last_action, style="bold yellow")
            parts.append("\n\n")

        if frame.room_description:
            parts.append(frame.room_description, style="dim white")

        # Recent message log
        if frame.message_log:
            parts.append("\n")
            for msg in frame.message_log[-5:]:
                parts.append(f"\n{msg}", style="grey70")

        return Panel(parts, title="[bold white]CHRONICLE[/]",
                     border_style="grey50", box=box.SIMPLE)

    def _build_battlefield(self, bf: dict) -> Panel:
        """WO-V9.0: Battlefield HUD for SaV+BoB crossover status."""
        table = Table(box=box.SIMPLE_HEAVY, expand=True, show_header=True,
                      border_style="bold #4488ff")
        table.add_column("SHIP", style="cyan", ratio=1)
        table.add_column("LEGION", style="yellow", ratio=1)

        # Ship column data
        ship = bf.get("ship", {})
        ship_lines = []
        for key, val in ship.items():
            ship_lines.append(f"{key.title()}: {val}")

        # Legion column data
        legion = bf.get("legion", {})
        legion_lines = []
        for key, val in legion.items():
            legion_lines.append(f"{key.title()}: {val}")

        # Pad to equal length
        max_rows = max(len(ship_lines), len(legion_lines), 1)
        ship_lines.extend([""] * (max_rows - len(ship_lines)))
        legion_lines.extend([""] * (max_rows - len(legion_lines)))

        for s, l in zip(ship_lines, legion_lines):
            table.add_row(s, l)

        # Clocks row
        clocks = bf.get("clocks", {})
        if clocks:
            clock_parts = []
            for name, val in clocks.items():
                filled = val if isinstance(val, int) else 0
                bar = "=" * filled + "-" * max(0, 8 - filled)
                clock_parts.append(f"{name}: [{bar}] {filled}/8")
            table.add_row("[dim]Clocks:[/dim]", " | ".join(clock_parts))

        return Panel(table, title="[bold #4488ff]BATTLEFIELD[/]",
                     border_style="bold #4488ff", box=box.ROUNDED)

    def _rebuild_spatial_rooms(self, frame: StateFrame) -> Dict[int, SpatialRoom]:
        """Build SpatialRoom objects from StateFrame dungeon_rooms + visited_rooms."""
        rooms = {}
        dungeon_dict = {rid: rdata for rid, rdata in frame.dungeon_rooms}

        for room_id, rdata in dungeon_dict.items():
            # Determine visibility
            if room_id == frame.current_room_id:
                vis = RoomVisibility.CURRENT
            elif room_id in frame.visited_rooms:
                vis = RoomVisibility.VISITED
            elif room_id in frame.scouted_rooms:
                vis = RoomVisibility.VISITED
            else:
                vis = RoomVisibility.HIDDEN

            sr = SpatialRoom(
                id=room_id,
                x=rdata["x"],
                y=rdata["y"],
                width=rdata["width"],
                height=rdata["height"],
                visibility=vis,
                connections=rdata.get("connections", []),
            )

            # Inject entities for current room (visible only)
            if room_id == frame.current_room_id:
                sr.enemies = list(frame.enemies)
                sr.loot = list(frame.loot)
                sr.furniture = list(frame.furniture)

            rooms[room_id] = sr

        return rooms

#!/usr/bin/env python3
"""Player View - External Monitor Display

Run in a second terminal on an external monitor:
    DISPLAY=:0 python play_player_view.py

Watches state/player_frame.json for StateFrame updates and renders
a player-safe Rich view. Pairs with play_burnwillow.py on the DM screen.

The DM plays on the handheld Pi 5 screen (terminal 1).
Players watch on the external monitor (terminal 2).

Usage:
    python play_player_view.py              # Default (RUST theme)
    python play_player_view.py --theme STONE
    python play_player_view.py --width 60 --height 25

Version: 1.0 (WO V4.2)
"""

import argparse
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from codex.paths import STATE_DIR
from codex.core.state_frame import frame_from_json, GameState, STATE_BUTTONS, GOLD, SILVER
from codex.spatial.player_renderer import PlayerRenderer
from codex.spatial.map_renderer import MapTheme

from rich.layout import Layout

FRAME_FILE = STATE_DIR / "player_frame.json"
POLL_INTERVAL = 0.3  # seconds


def _state_footer(frame) -> Panel:
    """Render a state-aware footer from the frame's game_state."""
    try:
        gs = GameState[frame.game_state]
    except (KeyError, AttributeError):
        gs = GameState.GAMEPLAY

    buttons = STATE_BUTTONS.get(gs, [])
    parts = []
    for label, _ in buttons:
        if label.startswith("["):
            key_end = label.index("]") + 1
            key = label[:key_end]
            desc = label[key_end:].strip()
            parts.append(f"[{GOLD}]{key}[/] {desc}")
        else:
            parts.append(label)

    hint_line = "  ".join(parts) if parts else "Awaiting input..."
    combat_tag = "  [bold red]COMBAT[/]" if frame.combat_mode else ""

    return Panel(
        Text.from_markup(hint_line + combat_tag),
        box=box.HORIZONTALS,
        border_style=SILVER,
        title=f"[{SILVER}]{gs.name}[/]",
        title_align="left",
        padding=(0, 2),
    )


def _waiting_screen() -> Panel:
    """Render a waiting screen while no game is active."""
    text = Text()
    text.append("PLAYER VIEW\n\n", style="bold cyan")
    text.append("Waiting for game session...\n", style="dim white")
    text.append("Start a game from the C.O.D.E.X. main menu.\n", style="dim grey70")
    return Panel(text, box=box.DOUBLE, border_style="cyan")


def main():
    parser = argparse.ArgumentParser(description="Player View - External Monitor Display")
    parser.add_argument("--theme", choices=["RUST", "STONE", "GOTHIC"], default="RUST",
                        help="Map theme (default: RUST)")
    parser.add_argument("--width", type=int, default=50, help="Viewport width")
    parser.add_argument("--height", type=int, default=20, help="Viewport height")
    args = parser.parse_args()

    theme = MapTheme[args.theme]
    console = Console()
    renderer = PlayerRenderer(theme=theme, viewport_width=args.width, viewport_height=args.height)
    last_mtime = 0.0

    console.clear()
    console.print(_waiting_screen())

    try:
        while True:
            try:
                if FRAME_FILE.exists():
                    mtime = FRAME_FILE.stat().st_mtime
                    if mtime > last_mtime:
                        last_mtime = mtime
                        data = FRAME_FILE.read_text()
                        if data.strip():
                            frame = frame_from_json(data)
                            main_layout = renderer.render(frame)
                            footer = _state_footer(frame)
                            console.clear()
                            console.print(main_layout)
                            console.print(footer)
                elif last_mtime > 0:
                    # Frame file was deleted (game ended)
                    last_mtime = 0.0
                    console.clear()
                    console.print(_waiting_screen())

                time.sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                raise
            except Exception:
                time.sleep(1.0)  # Retry on transient read errors
    except KeyboardInterrupt:
        console.print("\n[dim]Player View closed.[/dim]")


if __name__ == "__main__":
    main()

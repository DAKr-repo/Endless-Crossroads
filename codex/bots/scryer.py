"""
codex/bots/scryer.py - The Scrying Engine (V4.1)
=================================================

Captures Rich terminal output as PNG screenshots for Discord/Telegram.
Uses pyte (virtual terminal emulator) + Pillow for rendering.

Optionally uses FFmpeg + Xvfb for video streaming (stretch goal).

Architecture:
  - ScryingEngine: Rich renderable -> PNG via pyte + Pillow
  - ScryingEmbed: Auto-updating Discord embed for screenshot channel
  - Dynamic thermal scaling: drops FPS when CPU > 75C

Requires: pip install pyte Pillow
System deps (optional for video): sudo apt-get install xvfb ffmpeg

Version: 1.0 (WO V4.1)
"""

import asyncio
import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("CODEX.Scryer")

_ROOT = Path(__file__).resolve().parent.parent.parent  # -> Codex/


class ScryingEngine:
    """Captures Rich terminal output as PNG screenshots."""

    # ANSI color palette (standard 8 colors + bright variants)
    _ANSI_COLORS = {
        "default": (200, 200, 200),
        "black": (0, 0, 0),
        "red": (205, 49, 49),
        "green": (13, 188, 121),
        "yellow": (229, 229, 16),
        "blue": (36, 114, 200),
        "magenta": (188, 63, 188),
        "cyan": (17, 168, 205),
        "white": (229, 229, 229),
    }

    _BG_COLOR = (30, 30, 30)  # Dark terminal background

    def __init__(self, width: int = 1280, height: int = 720,
                 cols: int = 160, rows: int = 45):
        self.width = width
        self.height = height
        self.cols = cols
        self.rows = rows
        self._output_dir = _ROOT / "state"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._output_path = self._output_dir / "current_view.png"

    async def capture_rich(self, renderable) -> Optional[Path]:
        """Render a Rich object to PNG via pyte terminal emulation + Pillow.

        Args:
            renderable: Any Rich renderable (Panel, Table, Layout, etc.)

        Returns:
            Path to the generated PNG, or None on failure.
        """
        try:
            import pyte
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as e:
            logger.warning(f"Scrying Engine dependencies missing: {e}")
            return None

        try:
            # Render Rich object to ANSI text
            from rich.console import Console
            buf = io.StringIO()
            console = Console(file=buf, width=self.cols, force_terminal=True,
                              color_system="standard")
            console.print(renderable)
            ansi_text = buf.getvalue()

            # Feed ANSI text into pyte virtual terminal
            screen = pyte.Screen(self.cols, self.rows)
            stream = pyte.Stream(screen)
            stream.feed(ansi_text)

            # Render pyte screen to PIL Image
            img = self._render_screen_to_image(screen)
            img.save(str(self._output_path))
            return self._output_path

        except Exception as e:
            logger.error(f"Scrying capture failed: {e}")
            return None

    def _render_screen_to_image(self, screen) -> "Image":
        """Convert pyte screen buffer to PIL Image with ANSI colors."""
        from PIL import Image, ImageDraw

        # Larger character cells for sharper output
        char_w, char_h = 10, 20
        img_w = self.cols * char_w
        img_h = self.rows * char_h
        img = Image.new("RGB", (img_w, img_h), self._BG_COLOR)
        draw = ImageDraw.Draw(img)

        try:
            from PIL import ImageFont
            font = ImageFont.load_default()
        except Exception:
            font = None

        for y in range(self.rows):
            line = screen.buffer.get(y, {})
            for x in range(self.cols):
                char_data = line.get(x)
                if not char_data:
                    continue
                char = char_data.data
                if char == " ":
                    continue

                # Resolve foreground color
                fg = char_data.fg if hasattr(char_data, 'fg') else "default"
                color = self._ANSI_COLORS.get(fg, self._ANSI_COLORS["default"])

                # Resolve background color
                bg = char_data.bg if hasattr(char_data, 'bg') else "default"
                if bg != "default" and bg in self._ANSI_COLORS:
                    bg_color = self._ANSI_COLORS[bg]
                    draw.rectangle(
                        [x * char_w, y * char_h,
                         (x + 1) * char_w, (y + 1) * char_h],
                        fill=bg_color
                    )

                draw.text((x * char_w, y * char_h), char, fill=color, font=font)

        return img

    def get_target_fps(self) -> int:
        """Dynamic FPS based on CPU temperature. Drops to 5fps above 75C."""
        try:
            from codex.core.cortex import CodexCortex
            cortex = CodexCortex()
            state = cortex.read_metabolic_state()
            return 5 if state.cpu_temp_celsius > 75 else 10
        except Exception:
            return 10

    async def start_video_stream(self) -> Optional[asyncio.subprocess.Process]:
        """Capture Xvfb display and output raw video for Discord (stretch goal).

        Requires Xvfb running on :99 (scripts/start_xvfb.sh).
        Returns the FFmpeg subprocess or None if unavailable.
        """
        fps = self.get_target_fps()
        cmd = [
            "ffmpeg", "-f", "x11grab",
            "-video_size", f"{self.width}x{self.height}",
            "-framerate", str(fps),
            "-i", ":99",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-tune", "zerolatency", "-pix_fmt", "yuv420p",
            "-f", "rawvideo", "pipe:1"
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            logger.info(f"Video stream started at {fps}fps")
            return proc
        except FileNotFoundError:
            logger.warning("FFmpeg not found — video streaming unavailable")
            return None
        except Exception as e:
            logger.error(f"Video stream failed: {e}")
            return None


async def scry_frame(frame, engine: ScryingEngine, renderer) -> Optional[Path]:
    """Convenience: render a StateFrame through PlayerRenderer, capture to PNG.

    Args:
        frame: StateFrame instance.
        engine: ScryingEngine for PNG capture.
        renderer: PlayerRenderer instance.

    Returns:
        Path to PNG or None on failure.
    """
    try:
        layout = renderer.render(frame)
        return await engine.capture_rich(layout)
    except Exception as e:
        logger.error(f"scry_frame failed: {e}")
        return None


class ScryingEmbed:
    """Auto-updating screenshot embed in a dedicated Discord channel.

    Maintains a single message in a #player-view channel, editing it
    with the latest screenshot after each game action.
    """

    def __init__(self, channel):
        self._channel = channel
        self._message = None

    async def update(self, image_path: Path, caption: str = ""):
        """Update the scrying embed with a new screenshot.

        Args:
            image_path: Path to the PNG screenshot.
            caption: Optional description text.
        """
        try:
            import discord
        except ImportError:
            return

        try:
            file = discord.File(str(image_path), filename="view.png")
            embed = discord.Embed(title="Player View", description=caption)
            embed.set_image(url="attachment://view.png")

            if self._message:
                try:
                    await self._message.edit(embed=embed, attachments=[file])
                except Exception:
                    # Message may have been deleted; create a new one
                    self._message = await self._channel.send(embed=embed, file=file)
            else:
                self._message = await self._channel.send(embed=embed, file=file)
        except Exception as e:
            logger.error(f"Scrying embed update failed: {e}")

"""
codex_dice_engine.py - The Bones of Fate

Dice rolling mechanics with immersive visual feedback for Terminal (rich) and Discord.
Supports standard RPG notation: NdX+/-M (e.g., 2d20+5, 4d6-2, 1d6)

Architecture:
- Pure function for dice parsing and rolling
- Async animators for Terminal (rich.Live) and Discord (Embeds)
- Critical hit/fail detection for d20 rolls
- Re-roll button support via discord.ui.View
"""

from __future__ import annotations

import asyncio
import random
import re
from typing import Optional, Tuple

# --- Terminal Rendering (rich) ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    from rich.live import Live
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Panel = None
    Text = None
    Align = None
    Live = None
    box = None

# --- Discord Rendering ---
try:
    import discord
    from discord import ui
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None
    ui = None


# =============================================================================
# 1. CORE DICE LOGIC
# =============================================================================

def roll_dice(expression: str) -> Tuple[int, list, int]:
    """
    Parse and execute a dice roll expression.

    Args:
        expression: Dice notation string (e.g., "2d20+5", "1d6", "4d6-2")

    Returns:
        Tuple of (total, individual_rolls, modifier)
        - total: Final sum including modifier
        - individual_rolls: List of raw die results
        - modifier: The +/- value applied

    Raises:
        ValueError: If expression is invalid or malformed

    Examples:
        >>> roll_dice("2d20+5")
        (27, [12, 10], 5)
        >>> roll_dice("1d6")
        (4, [4], 0)
    """
    # Clean whitespace
    expr = expression.strip().lower()

    # Pattern: NdX+/-M or just NdX
    pattern = r'^(\d+)d(\d+)(([+-])(\d+))?$'
    match = re.match(pattern, expr)

    if not match:
        raise ValueError(
            f"Invalid dice expression: '{expression}'. "
            "Expected format: NdX+/-M (e.g., 2d20+5, 1d6, 4d6-2)"
        )

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier_sign = match.group(4)  # '+' or '-' or None
    modifier_value = int(match.group(5)) if match.group(5) else 0

    # Apply sign to modifier
    if modifier_sign == '-':
        modifier = -modifier_value
    else:
        modifier = modifier_value

    # Validate dice parameters
    if num_dice < 1:
        raise ValueError("Number of dice must be at least 1")
    if die_size < 2:
        raise ValueError("Die size must be at least 2 (d2 minimum)")
    if num_dice > 100:
        raise ValueError("Maximum 100 dice per roll (to prevent abuse)")

    # Roll the bones
    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier

    return (total, rolls, modifier)


# =============================================================================
# 2. TERMINAL ANIMATOR (rich)
# =============================================================================

async def animate_terminal_roll(
    expression: str,
    console: Optional[Console] = None
) -> Tuple[int, list, int]:
    """
    Animate a dice roll in the terminal with rich.Live.

    Shows cycling random numbers for ~1.5 seconds before revealing
    the actual result. Applies special styling for critical hits/fails.

    Args:
        expression: Dice notation string
        console: Optional rich.Console instance (creates default if None)

    Returns:
        Tuple of (total, rolls, modifier) from roll_dice()

    Raises:
        ValueError: If expression is invalid
        RuntimeError: If rich is not available
    """
    if not RICH_AVAILABLE:
        raise RuntimeError(
            "rich library not available. Install with: pip install rich"
        )

    if console is None:
        console = Console()

    # Parse expression first to validate
    total, rolls, modifier = roll_dice(expression)

    # Detect critical outcomes (only for d20 rolls)
    is_d20 = "d20" in expression.lower()
    is_crit_success = is_d20 and 20 in rolls
    is_crit_fail = is_d20 and 1 in rolls

    # Animation config
    animation_frames = 25
    frame_delay = 0.06  # 1.5 seconds total

    def make_rolling_panel(frame_idx: int, final: bool = False) -> Panel:
        """Generate a panel for the current animation frame."""
        if final:
            # Final result display
            rolls_text = " + ".join([str(r) for r in rolls])
            if modifier != 0:
                mod_str = f"{modifier:+d}"
                display_text = f"{rolls_text} {mod_str} = {total}"
            else:
                display_text = f"{rolls_text} = {total}"

            # Style based on critical outcome
            if is_crit_success:
                text_style = "bold green"
                title = "CRITICAL SUCCESS!"
                border_style = "green"
            elif is_crit_fail:
                text_style = "bold red"
                title = "CRITICAL FAIL!"
                border_style = "red"
            else:
                text_style = "bold yellow"
                title = "The Fates Decree"
                border_style = "yellow"

            content = Text(display_text, style=text_style, justify="center")
        else:
            # Rolling animation - show random cycling numbers
            num_dice = len(rolls)
            die_size = int(expression.split('d')[1].split('+')[0].split('-')[0])
            fake_rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            rolls_text = "  ".join([f"[{r}]" for r in fake_rolls])

            content = Text(rolls_text, style="dim cyan", justify="center")
            title = "Rolling..."
            border_style = "cyan"

        return Panel(
            Align.center(content),
            title=f"[bold]{title}[/]",
            border_style=border_style,
            box=box.DOUBLE if final else box.ROUNDED,
            padding=(1, 2),
        )

    # Animate
    with Live(make_rolling_panel(0), console=console, refresh_per_second=20) as live:
        # Rolling phase
        for i in range(animation_frames):
            live.update(make_rolling_panel(i))
            await asyncio.sleep(frame_delay)

        # Final reveal
        live.update(make_rolling_panel(0, final=True))
        await asyncio.sleep(0.5)  # Hold final result briefly

    return (total, rolls, modifier)


# =============================================================================
# 3. DISCORD EMBED RENDERER
# =============================================================================

async def get_discord_roll_embed(expression: str) -> Tuple[discord.Embed, int, list]:
    """
    Generate a Discord Embed for a dice roll result.

    Args:
        expression: Dice notation string

    Returns:
        Tuple of (embed, total, rolls)
        - embed: Formatted discord.Embed
        - total: Final roll result
        - rolls: List of individual die results

    Raises:
        ValueError: If expression is invalid
        RuntimeError: If discord.py is not available
    """
    if not DISCORD_AVAILABLE:
        raise RuntimeError(
            "discord.py not available. Install with: pip install discord.py"
        )

    # Roll the dice
    total, rolls, modifier = roll_dice(expression)

    # Detect critical outcomes
    is_d20 = "d20" in expression.lower()
    is_crit_success = is_d20 and 20 in rolls
    is_crit_fail = is_d20 and 1 in rolls

    # Color code
    if is_crit_success:
        color = discord.Color.green()
        title = "🎲 CRITICAL SUCCESS!"
    elif is_crit_fail:
        color = discord.Color.red()
        title = "🎲 CRITICAL FAIL!"
    else:
        color = discord.Color.blue()
        title = "🎲 The Fates Decree"

    # Build embed
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    # Fields
    embed.add_field(
        name="Expression",
        value=f"`{expression}`",
        inline=False
    )

    # Individual rolls
    rolls_display = "  ".join([f"**[{r}]**" for r in rolls])
    embed.add_field(
        name="Rolls",
        value=rolls_display,
        inline=False
    )

    # Total calculation
    if modifier != 0:
        mod_str = f"{modifier:+d}"
        calc = f"{sum(rolls)} {mod_str} = **{total}**"
    else:
        calc = f"**{total}**"

    embed.add_field(
        name="Total",
        value=calc,
        inline=False
    )

    embed.set_footer(text="The Bones of Fate")

    return (embed, total, rolls)


# =============================================================================
# 4. DISCORD RE-ROLL VIEW
# =============================================================================

if DISCORD_AVAILABLE:
    class DiceRollView(ui.View):
        """
        Interactive Discord View with a re-roll button.

        Allows users to re-roll the same dice expression without
        typing the command again.
        """

        def __init__(self, expression: str, timeout: float = 180.0):
            super().__init__(timeout=timeout)
            self.expression = expression

        @ui.button(label="Re-roll", emoji="🎲", style=discord.ButtonStyle.primary)
        async def reroll_button(
            self,
            interaction: discord.Interaction,
            button: ui.Button
        ):
            """Handle re-roll button press."""
            try:
                # Generate new roll
                embed, total, rolls = await get_discord_roll_embed(self.expression)

                # Update message with new result
                await interaction.response.edit_message(
                    embed=embed,
                    view=self  # Keep the re-roll button
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Re-roll failed: {e}",
                    ephemeral=True
                )

        async def on_timeout(self):
            """Disable button when view times out."""
            self.reroll_button.disabled = True
            self.stop()

else:
    # Stub when Discord unavailable
    class DiceRollView:
        """Stub for DiceRollView when discord.py is not installed."""
        def __init__(self, expression: str, timeout: float = 180.0):
            raise RuntimeError("discord.py not available")


# =============================================================================
# 5. CONVENIENCE FUNCTIONS
# =============================================================================

def is_critical_success(rolls: list, expression: str) -> bool:
    """Check if roll contains a natural 20 (d20 only)."""
    return "d20" in expression.lower() and 20 in rolls


def is_critical_fail(rolls: list, expression: str) -> bool:
    """Check if roll contains a natural 1 (d20 only)."""
    return "d20" in expression.lower() and 1 in rolls


def format_roll_text(total: int, rolls: list, modifier: int) -> str:
    """
    Format roll results as plain text.

    Returns:
        Human-readable string like "Rolled: [12] [8] +5 = 25"
    """
    rolls_str = " ".join([f"[{r}]" for r in rolls])
    if modifier != 0:
        mod_str = f"{modifier:+d}"
        return f"Rolled: {rolls_str} {mod_str} = {total}"
    else:
        return f"Rolled: {rolls_str} = {total}"


# =============================================================================
# 6. MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("   C.O.D.E.X. DICE ENGINE TEST")
    print("="*50)

    # Test basic rolling
    print("\n[1] Basic Roll Tests:")
    test_expressions = ["2d20+5", "1d6", "4d6-2", "3d8", "1d20"]
    for expr in test_expressions:
        try:
            total, rolls, mod = roll_dice(expr)
            print(f"  {expr:12} -> {format_roll_text(total, rolls, mod)}")
        except ValueError as e:
            print(f"  {expr:12} -> ERROR: {e}")

    # Test invalid expressions
    print("\n[2] Invalid Expression Tests:")
    invalid = ["2d", "d20", "2d20+", "0d6", "2d1", "abc"]
    for expr in invalid:
        try:
            roll_dice(expr)
            print(f"  {expr:12} -> SHOULD HAVE FAILED")
        except ValueError as e:
            print(f"  {expr:12} -> Correctly rejected")

    # Test terminal animation (if rich available)
    if RICH_AVAILABLE:
        print("\n[3] Terminal Animation Test:")
        print("  Running animated roll...")
        total, rolls, mod = asyncio.run(animate_terminal_roll("2d20+5"))
        print(f"  Result: {format_roll_text(total, rolls, mod)}")
    else:
        print("\n[3] Terminal Animation: SKIPPED (rich not installed)")

    # Test Discord embed (if discord.py available)
    if DISCORD_AVAILABLE:
        print("\n[4] Discord Embed Test:")
        print("  Generating embed...")
        embed, total, rolls = asyncio.run(get_discord_roll_embed("1d20"))
        print(f"  Embed Title: {embed.title}")
        print(f"  Result: {format_roll_text(total, rolls, 0)}")
    else:
        print("\n[4] Discord Embed: SKIPPED (discord.py not installed)")

    print("\n" + "="*50)
    print("[COMPLETE] The Bones of Fate are ready.")
    print("="*50 + "\n")

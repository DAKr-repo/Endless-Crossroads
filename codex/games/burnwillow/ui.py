"""
burnwillow_ui.py - Rich Library UI Components for Burnwillow

Bioluminescent Decay aesthetic for terminal rendering.
Designed to work with burnwillow_module.py game engine.

Theme: Beautiful Rot - Nature Reclaiming
- Deep Greens: Forest decay, moss
- Rust Oranges: Dying light, embers
- Glowing Cyans: Fungal bioluminescence
- Bone Whites: Ancient remains
- Shadow Purples: Deep darkness

Deliverables:
1. Paper Doll Inventory (render_gear_grid)
2. Visual Dice Tray (render_roll_result)
3. Character Status Panel (render_status)
4. Death Screen (render_death_screen)
"""

import random
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.progress import BarColumn
from rich.align import Align
from rich import box

# Import game structures
try:
    from codex.games.burnwillow.engine import (
        Character, GearItem, GearSlot, GearTier, StatType, CheckResult
    )
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False
    # Create stub classes for standalone testing
    from enum import Enum

    class GearSlot(Enum):
        HEAD = "Head"
        SHOULDERS = "Shoulders"
        CHEST = "Chest"
        ARMS = "Arms"
        LEGS = "Legs"
        R_HAND = "R.Hand"
        L_HAND = "L.Hand"
        R_RING = "R.Ring"
        L_RING = "L.Ring"
        NECK = "Neck"

    class GearTier(Enum):
        TIER_0 = 0
        TIER_I = 1
        TIER_II = 2
        TIER_III = 3
        TIER_IV = 4


# =============================================================================
# THEME CONSTANTS - BIOLUMINESCENT DECAY
# =============================================================================

# Hex colors for Rich (supports true color terminals)
FUNGAL_CYAN = "#00FFCC"      # Glowing bioluminescence (success, magic)
DECAY_GREEN = "#2D5016"      # Forest moss, decay
EMBER_RUST = "#CC5500"       # Dying embers, failure, danger
BONE_WHITE = "#F5F5DC"       # Ancient remains, neutral
SHADOW_PURPLE = "#4B0082"    # Deep darkness, mystery
WILLOW_GOLD = "#FFD700"      # The Burnwillow tree itself
DEEP_BLACK = "#1a1a1a"       # Background darkness

# Rich style shortcuts
GLOW = f"bold {FUNGAL_CYAN}"
MOSS = f"{DECAY_GREEN}"
EMBER = f"bold {EMBER_RUST}"
BONE = BONE_WHITE
SHADOW = f"dim {SHADOW_PURPLE}"
WILLOW = f"bold {WILLOW_GOLD}"


# =============================================================================
# DICE DISPLAY
# =============================================================================

# Unicode dice faces (⚀⚁⚂⚃⚄⚅)
DICE_FACES = {
    1: "⚀",
    2: "⚁",
    3: "⚂",
    4: "⚃",
    5: "⚄",
    6: "⚅"
}


# =============================================================================
# UI COMPONENT 1: PAPER DOLL INVENTORY
# =============================================================================

def render_gear_grid(
    equipped: Dict[GearSlot, Optional[GearItem]],
    console: Optional[Console] = None
) -> Panel:
    """
    Render the 10-slot equipment paper doll with Bioluminescent Decay theme.

    Visual layout mimics a character sheet:
           [HEAD]
        [SHOULDERS]
    [L.HAND] [CHEST] [R.HAND]
           [ARMS]
           [LEGS]
      [L.RING] [NECK] [R.RING]

    Empty slots appear hollow/dim (decay).
    Equipped items glow with tier-appropriate colors.

    Args:
        equipped: Dictionary mapping GearSlot -> GearItem (or None if empty)
        console: Optional Console for width detection

    Returns:
        Rich Panel containing the equipment grid
    """
    if console is None:
        console = Console()

    # Tier color mapping (material quality = glow intensity)
    TIER_COLORS = {
        0: f"dim {SHADOW_PURPLE}",      # Unarmed - barely visible
        1: DECAY_GREEN,                  # Scrap - mossy decay
        2: "white",                      # Iron - plain steel
        3: "bright_white",               # Steel - polished
        4: FUNGAL_CYAN,                  # Mithral - glowing
        5: WILLOW_GOLD,                  # Burnwillow - radiant
    }

    def format_slot(slot: GearSlot) -> Text:
        """Format a single equipment slot with visual flair."""
        item = equipped.get(slot)

        if item is None:
            # Empty slot - hollow appearance with rot aesthetic
            slot_text = Text()
            slot_text.append(f"┌─ {slot.value:^10} ─┐\n", style=f"dim {SHADOW_PURPLE}")
            slot_text.append("│   ", style=SHADOW)
            slot_text.append("░░░░░░", style=f"dim {DECAY_GREEN}")  # Moss growth
            slot_text.append("   │\n", style=SHADOW)
            slot_text.append("│   ", style=SHADOW)
            slot_text.append("EMPTY", style=SHADOW)
            slot_text.append("    │\n", style=SHADOW)
            slot_text.append("└─────────────┘", style=f"dim {SHADOW_PURPLE}")
            return slot_text
        else:
            # Equipped item - show tier, name, bonuses with glow effect
            tier_value = item.tier.value if hasattr(item.tier, 'value') else 0
            tier_style = TIER_COLORS.get(tier_value, BONE)

            # Get material name
            if hasattr(item.tier, 'name'):
                material = item.tier.name.replace('TIER_', 'T')
                if material == 'T0':
                    material = "Bare"
            else:
                material = f"T{tier_value}"

            slot_text = Text()

            # Top border with slot name
            slot_text.append(f"╔═ {slot.value:^10} ═╗\n", style=MOSS)

            # Material tier indicator
            slot_text.append("║ ", style=MOSS)
            slot_text.append(f"{material:^13}", style=tier_style)
            slot_text.append(" ║\n", style=MOSS)

            # Item name (truncate if too long)
            item_name = item.name[:13] if len(item.name) <= 13 else item.name[:10] + "..."
            slot_text.append("║ ", style=MOSS)
            slot_text.append(f"{item_name:^13}", style=BONE)
            slot_text.append(" ║\n", style=MOSS)

            # Dice bonus (the core mechanic)
            dice_bonus = tier_value
            slot_text.append("║ ", style=MOSS)
            slot_text.append(f"+{dice_bonus}d6", style=GLOW)
            slot_text.append(" " * (13 - len(f"+{dice_bonus}d6")))
            slot_text.append(" ║\n", style=MOSS)

            # Stat bonuses (if any)
            if hasattr(item, 'stat_bonuses') and item.stat_bonuses:
                bonus_parts = []
                for stat, value in item.stat_bonuses.items():
                    stat_abbr = stat.value[:3] if hasattr(stat, 'value') else str(stat)[:3]
                    bonus_parts.append(f"+{value}{stat_abbr}")
                bonus_str = " ".join(bonus_parts)[:13]
                slot_text.append("║ ", style=MOSS)
                slot_text.append(f"{bonus_str:<13}", style="yellow")
                slot_text.append(" ║\n", style=MOSS)

            # Special traits (magical/unique abilities)
            if hasattr(item, 'special_traits') and item.special_traits:
                trait_raw = item.special_traits[0]  # First trait only
                trait = f"{trait_raw[:12]}\u2026" if len(trait_raw) > 13 else trait_raw
                slot_text.append("║ ", style=MOSS)
                slot_text.append(f"{trait:<13}", style=WILLOW)
                slot_text.append(" ║\n", style=MOSS)

            # Bottom border
            slot_text.append("╚═════════════╝", style=MOSS)

            return slot_text

    # Build the paper doll grid layout
    # Using Table.grid for precise positioning
    grid = Table.grid(padding=(0, 1))
    grid.add_column(justify="center", width=17)
    grid.add_column(justify="center", width=17)
    grid.add_column(justify="center", width=17)

    # Row 1: HEAD (center)
    grid.add_row("", format_slot(GearSlot.HEAD), "")

    # Row 2: SHOULDERS (center)
    grid.add_row("", format_slot(GearSlot.SHOULDERS), "")

    # Row 3: L.HAND, CHEST, R.HAND (full row)
    grid.add_row(
        format_slot(GearSlot.L_HAND),
        format_slot(GearSlot.CHEST),
        format_slot(GearSlot.R_HAND)
    )

    # Row 4: ARMS (center)
    grid.add_row("", format_slot(GearSlot.ARMS), "")

    # Row 5: LEGS (center)
    grid.add_row("", format_slot(GearSlot.LEGS), "")

    # Row 6: L.RING, NECK, R.RING (full row)
    grid.add_row(
        format_slot(GearSlot.L_RING),
        format_slot(GearSlot.NECK),
        format_slot(GearSlot.R_RING)
    )

    # Wrap in themed panel
    return Panel(
        Align.center(grid),
        title=f"[{GLOW}]╞═══ Equipment Loadout ═══╡[/]",
        border_style=DECAY_GREEN,
        box=box.DOUBLE,
        padding=(1, 2)
    )


# =============================================================================
# UI COMPONENT 2: VISUAL DICE TRAY
# =============================================================================

def render_roll_result(
    rolls: List[int],
    modifier: int,
    total: int,
    dc: int,
    context: str = "Action"
) -> Panel:
    """
    Display dice roll results with unicode dice faces and color coding.

    Format: [⚅][⚂][⚀] + 2 = 12 vs DC 10 ✓

    Success = Cyan glow (fungal bioluminescence)
    Failure = Rust orange (dying embers)

    Args:
        rolls: Individual die results (1-6)
        modifier: Flat bonus added to roll
        total: Sum of rolls + modifier
        dc: Difficulty Class to beat
        context: What this roll represents (e.g., "Lockpicking", "Attack")

    Returns:
        Rich Panel showing the roll breakdown with thematic styling
    """
    success = total >= dc

    # Build the visual dice display with unicode faces
    dice_text = Text()

    for i, roll in enumerate(rolls):
        face = DICE_FACES[roll]

        # Color each die by value (high = glowing cyan, low = dying ember)
        if roll >= 5:
            die_style = GLOW  # High roll - bioluminescent glow
        elif roll <= 2:
            die_style = EMBER  # Low roll - dying embers
        else:
            die_style = BONE  # Mid roll - bone white

        dice_text.append(f"[{face}]", style=die_style)

        # Add spacing between dice
        if i < len(rolls) - 1:
            dice_text.append(" ", style=SHADOW)

    # Add modifier display
    if modifier != 0:
        sign = "+" if modifier >= 0 else ""
        dice_text.append(f" {sign}{modifier}", style="yellow")

    # Add equals and total
    dice_text.append(" = ", style=MOSS)
    total_style = GLOW if success else EMBER
    dice_text.append(f"{total}", style=f"bold {total_style}")

    # Add DC comparison
    dice_text.append(f" vs DC {dc}", style=BONE)

    # Add result indicator (success/failure)
    if success:
        dice_text.append(" ✓", style=GLOW)
        result_text = "SUCCESS"
        result_style = GLOW
        border_style = FUNGAL_CYAN
        result_desc = "The fungal glow illuminates your path..."
    else:
        dice_text.append(" ✗", style=EMBER)
        result_text = "FAILURE"
        result_style = EMBER
        border_style = EMBER_RUST
        result_desc = "The embers fade to ash..."

    # Build content layout
    content = Table.grid(padding=(0, 1))
    content.add_column(justify="center")

    # Context header
    content.add_row(Text(context.upper(), style=WILLOW))
    content.add_row(Text("─" * 40, style=SHADOW))
    content.add_row("")

    # Dice visualization
    content.add_row(dice_text)
    content.add_row("")

    # Result verdict
    content.add_row(Text(result_text, style=f"bold {result_style}"))
    content.add_row("")
    content.add_row(Text(result_desc, style=f"dim italic {result_style}"))

    # Wrap in themed panel with animated border
    return Panel(
        Align.center(content),
        title=f"[bold {border_style}]⚂ Dice Tray ⚂[/]",
        border_style=border_style,
        box=box.HEAVY,
        padding=(1, 3)
    )


# =============================================================================
# UI COMPONENT 3: CHARACTER STATUS PANEL
# =============================================================================

def render_status(
    character_data: Dict,
    console: Optional[Console] = None
) -> Layout:
    """
    Display character vitals, stats, doom clock, and depth.

    Layout:
    ┌─────────────────────────────────────────────┐
    │ HP: [████████████░░░░░░░░] 12/20           │
    │ Depth: Floor 3  │  Doom: ●●●●○○○○○○        │
    ├─────────────────────────────────────────────┤
    │ MIGHT  14 (+2)  │  WITS   12 (+1)          │
    │ GRIT   16 (+3)  │  AETHER 10 (+0)          │
    └─────────────────────────────────────────────┘

    Args:
        character_data: Dict containing:
            - hp_current, hp_max
            - might, wits, grit, aether (with modifiers)
            - dungeon_depth
            - doom_clock (current progress out of max)
        console: Optional Console instance

    Returns:
        Rich Layout with status display
    """
    if console is None:
        console = Console()

    layout = Layout()

    # Extract character data
    hp_current = character_data.get('hp_current', 10)
    hp_max = character_data.get('hp_max', 10)
    depth = character_data.get('dungeon_depth', 1)
    doom_current = character_data.get('doom_clock', 0)
    doom_max = character_data.get('doom_max', 10)

    stats = character_data.get('stats', {
        'might': (10, 0),
        'wits': (10, 0),
        'grit': (10, 0),
        'aether': (10, 0)
    })

    # === TOP SECTION: HP & PROGRESSION ===
    top_grid = Table.grid(padding=(0, 0))
    top_grid.add_column(justify="left", width=45)

    # HP Bar (visual progress bar)
    hp_percent = hp_current / hp_max if hp_max > 0 else 0
    bar_width = 20
    filled = int(bar_width * hp_percent)
    empty = bar_width - filled

    hp_bar = Text()
    hp_bar.append("HP: ", style=WILLOW)
    hp_bar.append("[", style=MOSS)

    # Color HP bar based on health percentage
    if hp_percent > 0.66:
        hp_color = GLOW
    elif hp_percent > 0.33:
        hp_color = "yellow"
    else:
        hp_color = EMBER

    hp_bar.append("█" * filled, style=hp_color)
    hp_bar.append("░" * empty, style=SHADOW)
    hp_bar.append("]", style=MOSS)
    hp_bar.append(f" {hp_current}/{hp_max}", style=BONE)

    top_grid.add_row(hp_bar)
    top_grid.add_row("")

    # Depth and Doom Clock (side by side)
    progress_row = Text()

    # Depth indicator
    progress_row.append("Depth: ", style=WILLOW)
    progress_row.append(f"Floor {depth}", style=GLOW)
    progress_row.append("  │  ", style=MOSS)

    # Doom Clock visual (filled/empty circles)
    doom_filled = min(doom_current, doom_max)
    doom_empty = max(0, doom_max - doom_filled)

    progress_row.append("Doom: ", style=EMBER)
    progress_row.append("●" * doom_filled, style=EMBER)
    progress_row.append("○" * doom_empty, style=SHADOW)

    top_grid.add_row(progress_row)

    # === MIDDLE SECTION: STAT SEPARATOR ===
    separator = Text("─" * 45, style=MOSS)

    # === BOTTOM SECTION: FOUR CORE STATS ===
    stats_table = Table(box=None, show_header=False, padding=(0, 3))
    stats_table.add_column(justify="left", width=20)
    stats_table.add_column(justify="left", width=20)

    def format_stat(name: str, score: int, modifier: int) -> Text:
        """Format a stat line with score and modifier."""
        text = Text()
        text.append(f"{name:6}", style=WILLOW)
        text.append(f" {score:2}", style=BONE)

        # Color modifier based on value
        sign = "+" if modifier >= 0 else ""
        if modifier > 0:
            mod_style = GLOW
        elif modifier == 0:
            mod_style = SHADOW
        else:
            mod_style = EMBER

        text.append(f" ({sign}{modifier})", style=mod_style)
        return text

    # Parse stats (format: {stat_name: (score, modifier)})
    might_score, might_mod = stats.get('might', (10, 0))
    wits_score, wits_mod = stats.get('wits', (10, 0))
    grit_score, grit_mod = stats.get('grit', (10, 0))
    aether_score, aether_mod = stats.get('aether', (10, 0))

    # Add stat rows (2x2 grid)
    stats_table.add_row(
        format_stat("MIGHT", might_score, might_mod),
        format_stat("WITS", wits_score, wits_mod)
    )
    stats_table.add_row(
        format_stat("GRIT", grit_score, grit_mod),
        format_stat("AETHER", aether_score, aether_mod)
    )

    # === COMBINE INTO PANEL ===
    content_grid = Table.grid(padding=(0, 1))
    content_grid.add_column()
    content_grid.add_row(top_grid)
    content_grid.add_row("")
    content_grid.add_row(separator)
    content_grid.add_row("")
    content_grid.add_row(stats_table)

    status_panel = Panel(
        content_grid,
        title=f"[{GLOW}]Character Status[/]",
        border_style=DECAY_GREEN,
        box=box.ROUNDED,
        padding=(1, 2)
    )

    layout.update(status_panel)
    return layout


# =============================================================================
# UI COMPONENT 4: DEATH SCREEN
# =============================================================================

@dataclass
class RunStatistics:
    """Track player performance for death screen."""
    floors_cleared: int = 0
    enemies_slain: int = 0
    turns_taken: int = 0
    chests_opened: int = 0
    gold_collected: int = 0
    highest_depth: int = 1
    cause_of_death: str = "Unknown"


@dataclass
class MetaUnlocks:
    """Persistent progression across runs."""
    total_runs: int = 0
    deepest_depth: int = 0
    total_kills: int = 0
    unlocked_starts: List[str] = field(default_factory=lambda: ["Wanderer"])
    unlocked_blessings: List[str] = field(default_factory=list)


def render_death_screen(
    stats: RunStatistics,
    unlocks: MetaUnlocks,
    depth: int,
    console: Optional[Console] = None
) -> Panel:
    """
    Display the permadeath screen with beautiful rot aesthetic.

    Sections:
    1. Thematic death message (random epitaph)
    2. Run statistics (performance this run)
    3. "What Persists" (meta-progression unlocks)
    4. Career totals
    5. Restart prompt

    Args:
        stats: RunStatistics from the completed run
        unlocks: MetaUnlocks showing persistent progression
        depth: Final dungeon depth reached
        console: Optional Console instance

    Returns:
        Rich Panel with full death screen
    """
    if console is None:
        console = Console()

    # Thematic death messages (bioluminescent decay theme)
    death_messages = [
        "The Blight claims another soul...",
        "Your light fades into the fungal glow...",
        "The Burnwillow's roots drink deep...",
        "Moss creeps over still flesh...",
        "The dungeon remembers your bones...",
        "You become part of the beautiful rot...",
        "The embers of your life extinguish...",
        "Nature reclaims what was borrowed...",
    ]
    epitaph = random.choice(death_messages)

    # Build the death screen content
    content = Table.grid(padding=(0, 2))
    content.add_column(justify="center")

    # === HEADER: Death Message ===
    content.add_row("")
    content.add_row(Text("☠", style=f"bold {EMBER_RUST}"))
    content.add_row(Text("YOU HAVE FALLEN", style=f"bold {EMBER}"))
    content.add_row("")
    content.add_row(Text(epitaph, style=f"italic {SHADOW}"))
    content.add_row("")

    # === SEPARATOR ===
    content.add_row(Text("═" * 50, style=MOSS))
    content.add_row("")

    # === SECTION 1: Run Statistics ===
    stats_header = Text("⚔ Run Statistics ⚔", style=f"bold {WILLOW}")
    content.add_row(stats_header)
    content.add_row("")

    # Build stats table
    stats_table = Table(box=None, show_header=False, padding=(0, 2))
    stats_table.add_column(justify="left", style=BONE, width=20)
    stats_table.add_column(justify="right", style=GLOW, width=15)

    stats_table.add_row("Floors Cleared", str(stats.floors_cleared))
    stats_table.add_row("Enemies Slain", str(stats.enemies_slain))
    stats_table.add_row("Turns Survived", str(stats.turns_taken))
    stats_table.add_row("Chests Opened", str(stats.chests_opened))
    stats_table.add_row("Gold Collected", f"{stats.gold_collected}g")
    stats_table.add_row("Deepest Depth", f"Floor {depth}")
    stats_table.add_row("", "")
    stats_table.add_row("Cause of Death", Text(stats.cause_of_death, style=EMBER))

    content.add_row(stats_table)
    content.add_row("")

    # === SEPARATOR ===
    content.add_row(Text("─" * 50, style=SHADOW))
    content.add_row("")

    # === SECTION 2: What Persists ===
    persist_header = Text("✦ What Persists ✦", style=f"bold {FUNGAL_CYAN}")
    content.add_row(persist_header)
    content.add_row("")

    # Calculate new unlocks gained this run
    unlocks_gained = []

    # New depth record
    if depth > unlocks.deepest_depth:
        unlocks_gained.append(f"New Depth Record: Floor {depth}")

    # Kill milestones
    total_kills_after = unlocks.total_kills + stats.enemies_slain
    if total_kills_after >= 100 and unlocks.total_kills < 100:
        unlocks_gained.append("Unlocked: 'Slayer' Starting Blessing")
    if total_kills_after >= 50 and unlocks.total_kills < 50:
        unlocks_gained.append("Unlocked: 'Hunter' Starting Blessing")

    # Run count milestones
    total_runs_after = unlocks.total_runs + 1
    if total_runs_after % 10 == 0:
        unlocks_gained.append(f"Milestone: {total_runs_after} Runs Completed")
    elif total_runs_after % 5 == 0:
        unlocks_gained.append(f"Completed {total_runs_after} Runs")

    # Display unlocks
    if unlocks_gained:
        for unlock in unlocks_gained:
            unlock_text = Text()
            unlock_text.append("✦ ", style=WILLOW)
            unlock_text.append(unlock, style=GLOW)
            content.add_row(unlock_text)
    else:
        content.add_row(Text("The dungeon yields no secrets this time...", style=SHADOW))

    content.add_row("")

    # === SECTION 3: Career Totals ===
    content.add_row(Text("─" * 50, style=SHADOW))
    content.add_row("")

    totals_text = Text()
    totals_text.append("Career: ", style=BONE)
    totals_text.append(f"{total_runs_after} Runs", style=WILLOW)
    totals_text.append(" │ ", style=SHADOW)
    totals_text.append(f"{total_kills_after} Kills", style=EMBER)
    totals_text.append(" │ ", style=SHADOW)
    totals_text.append(f"Best: Floor {max(depth, unlocks.deepest_depth)}", style=GLOW)

    content.add_row(totals_text)
    content.add_row("")

    # === FOOTER: Restart Prompt ===
    content.add_row(Text("═" * 50, style=MOSS))
    content.add_row("")
    content.add_row(Text("Press [R] to Delve Again", style=f"bold {FUNGAL_CYAN}"))
    content.add_row(Text("Press [Q] to Abandon Hope", style=f"dim {SHADOW}"))
    content.add_row("")

    # Wrap in themed panel with decay border
    return Panel(
        Align.center(content),
        title=f"[{EMBER}]═══ The Burnwillow Remembers ═══[/]",
        border_style=EMBER_RUST,
        box=box.DOUBLE,
        padding=(2, 4)
    )


# =============================================================================
# EXAMPLE USAGE & VISUAL TESTING
# =============================================================================

def create_sample_data():
    """Create sample data for testing UI components."""
    # Sample equipped gear
    if ENGINE_AVAILABLE:
        from codex.games.burnwillow.engine import create_starter_gear
        starter_items = create_starter_gear()
        equipped = {
            GearSlot.HEAD: None,
            GearSlot.SHOULDERS: None,
            GearSlot.CHEST: starter_items[1],  # Padded Jerkin
            GearSlot.ARMS: starter_items[3],   # Burglar's Gloves
            GearSlot.LEGS: None,
            GearSlot.R_HAND: starter_items[0], # Rusted Shortsword
            GearSlot.L_HAND: starter_items[4], # Pot Lid Shield
            GearSlot.R_RING: None,
            GearSlot.L_RING: None,
            GearSlot.NECK: None,
        }
    else:
        # Stub data for standalone testing
        equipped = {slot: None for slot in GearSlot}

    # Sample character stats
    character_data = {
        'hp_current': 8,
        'hp_max': 15,
        'dungeon_depth': 3,
        'doom_clock': 4,
        'doom_max': 10,
        'stats': {
            'might': (14, 2),
            'wits': (12, 1),
            'grit': (16, 3),
            'aether': (10, 0)
        }
    }

    # Sample run statistics
    run_stats = RunStatistics(
        floors_cleared=2,
        enemies_slain=15,
        turns_taken=87,
        chests_opened=5,
        gold_collected=280,
        highest_depth=3,
        cause_of_death="Blight Warden"
    )

    # Sample meta unlocks
    meta_unlocks = MetaUnlocks(
        total_runs=7,
        deepest_depth=2,
        total_kills=89,
        unlocked_starts=["Wanderer"],
        unlocked_blessings=["Fortune"]
    )

    return equipped, character_data, run_stats, meta_unlocks


if __name__ == "__main__":
    """Visual test of all Burnwillow UI components."""
    console = Console()

    console.print("\n")
    console.print(Panel(
        Text("BURNWILLOW UI COMPONENTS", justify="center", style=WILLOW),
        border_style=FUNGAL_CYAN,
        box=box.DOUBLE
    ))
    console.print("\n")

    # Create sample data
    equipped, character_data, run_stats, meta_unlocks = create_sample_data()

    # Test 1: Paper Doll Inventory
    console.print(Text("1. PAPER DOLL INVENTORY", style=f"bold {WILLOW}"))
    console.print(render_gear_grid(equipped, console))
    console.print("\n")

    # Test 2: Dice Roll Results
    console.print(Text("2. VISUAL DICE TRAY", style=f"bold {WILLOW}"))

    # Success example (lockpicking)
    rolls_success = [5, 4, 3]
    modifier_success = 2
    total_success = sum(rolls_success) + modifier_success
    console.print(render_roll_result(
        rolls_success, modifier_success, total_success, 12, "Lockpicking"
    ))
    console.print("\n")

    # Failure example (attack)
    rolls_fail = [1, 2, 2]
    modifier_fail = 1
    total_fail = sum(rolls_fail) + modifier_fail
    console.print(render_roll_result(
        rolls_fail, modifier_fail, total_fail, 12, "Melee Attack"
    ))
    console.print("\n")

    # Test 3: Character Status Panel
    console.print(Text("3. CHARACTER STATUS", style=f"bold {WILLOW}"))
    console.print(render_status(character_data, console))
    console.print("\n")

    # Test 4: Death Screen
    console.print(Text("4. DEATH SCREEN", style=f"bold {WILLOW}"))
    console.print(render_death_screen(
        run_stats, meta_unlocks, 3, console
    ))
    console.print("\n")

    console.print(Panel(
        Text("All UI components rendered successfully!", justify="center", style=GLOW),
        border_style=FUNGAL_CYAN
    ))
    console.print("\n")

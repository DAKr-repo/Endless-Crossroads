#!/usr/bin/env python3
"""
Burnwillow Paper Doll Character Sheet TUI
==========================================
A bioluminescent decay-themed equipment and stat display
that reads directly from the engine's Character / GearGrid types.

Rewritten for WO V20.0 Task 6A — no local type stubs.
"""

from typing import Optional, Dict
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich import box

from codex.games.burnwillow.engine import (
    Character, GearSlot, GearItem, GearGrid, calculate_stat_mod,
)

# BURNWILLOW COLOR PALETTE (Bioluminescent Decay)
FUNGAL_CYAN = "#00FFCC"
DECAY_GREEN = "#2D5016"
EMBER_RUST = "#CC5500"
BONE_WHITE = "#F5F5DC"
SHADOW_PURPLE = "#4B0082"
WILLOW_GOLD = "#FFD700"


def render_dice_pips(count: int, max_pips: int = 5) -> Text:
    """Render dice contribution as 5-pip visualizer: [***oo] = 3d6."""
    text = Text("[", style=DECAY_GREEN)
    for _ in range(min(count, max_pips)):
        text.append("*", style=FUNGAL_CYAN)
    for _ in range(max_pips - count):
        text.append("o", style=SHADOW_PURPLE)
    text.append("]", style=DECAY_GREEN)
    return text


def render_hp_bar(current: int, maximum: int, width: int = 10) -> Text:
    """Render HP as a visual bar with threshold coloring."""
    maximum = max(1, maximum)
    percent = max(0, min(1, current / maximum))
    filled = int(width * percent)
    empty = width - filled

    if percent > 0.6:
        color = FUNGAL_CYAN
    elif percent > 0.3:
        color = WILLOW_GOLD
    else:
        color = EMBER_RUST

    bar = Text()
    bar.append("#" * filled, style=color)
    bar.append("-" * empty, style=SHADOW_PURPLE)
    return bar


def render_doom_pips(doom: int, max_doom: int = 10) -> Text:
    """Render doom counter as 10-pip display."""
    text = Text()
    for i in range(max_doom):
        if i < doom:
            text.append("*", style=EMBER_RUST)
        else:
            text.append("o", style=SHADOW_PURPLE + " dim")
    return text


def _slot_display(slot: GearSlot, item: Optional[GearItem], width: int = 14) -> Panel:
    """Render a single equipment slot panel."""
    content = Text()
    if item:
        item_name = item.name[:width - 2]
        content.append(item_name + "\n", style=BONE_WHITE)
        _tier = item.tier.value if hasattr(item.tier, 'value') else item.tier
        content.append(render_dice_pips(_tier))
        if item.special_traits:
            content.append(f"\n{','.join(item.special_traits)}", style=FUNGAL_CYAN + " dim")
    else:
        content.append("Empty\n", style=SHADOW_PURPLE + " dim")
        content.append(render_dice_pips(0))

    return Panel(
        content,
        title=slot.value.upper(),
        title_align="center",
        border_style=DECAY_GREEN,
        box=box.ROUNDED,
        width=width,
        padding=(0, 1),
    )


def render_paper_doll(character: Character, console_width: int = 70) -> Panel:
    """Render the complete Paper Doll character sheet from engine types.

    Args:
        character: Engine Character object with .gear, .current_hp, stats, etc.
        console_width: Available console width.

    Returns:
        Rich Panel containing the full character sheet.
    """
    slots = character.gear.slots

    # === HEADER ===
    header = Text()
    header.append(character.name.upper(), style=WILLOW_GOLD + " bold")
    header.append("\n")
    header.append("HP: ", style=WILLOW_GOLD)
    header.append(render_hp_bar(character.current_hp, character.max_hp))
    header.append(f" {character.current_hp}/{character.max_hp}", style=BONE_WHITE)
    header.append("\n")
    header.append(f"DEF: {character.get_defense()}", style=WILLOW_GOLD)
    header.append(f"  DR: {character.gear.get_total_dr()}", style=WILLOW_GOLD)

    # === EQUIPMENT GRID ===
    equipment_grid = Table.grid(padding=(0, 1))
    equipment_grid.add_column(justify="center")
    equipment_grid.add_column(justify="center")
    equipment_grid.add_column(justify="center")

    equipment_grid.add_row(
        "",
        _slot_display(GearSlot.HEAD, slots.get(GearSlot.HEAD)),
        "",
    )
    equipment_grid.add_row(
        _slot_display(GearSlot.SHOULDERS, slots.get(GearSlot.SHOULDERS)),
        _slot_display(GearSlot.NECK, slots.get(GearSlot.NECK)),
        "",
    )
    equipment_grid.add_row(
        _slot_display(GearSlot.L_HAND, slots.get(GearSlot.L_HAND)),
        _slot_display(GearSlot.CHEST, slots.get(GearSlot.CHEST)),
        _slot_display(GearSlot.R_HAND, slots.get(GearSlot.R_HAND)),
    )
    equipment_grid.add_row(
        _slot_display(GearSlot.ARMS, slots.get(GearSlot.ARMS)),
        _slot_display(GearSlot.LEGS, slots.get(GearSlot.LEGS)),
        "",
    )
    equipment_grid.add_row(
        _slot_display(GearSlot.L_RING, slots.get(GearSlot.L_RING)),
        _slot_display(GearSlot.R_RING, slots.get(GearSlot.R_RING)),
        "",
    )

    # === STATS COLUMN ===
    stat_table = Table.grid(padding=(0, 2))
    stat_table.add_column(style=WILLOW_GOLD + " bold", justify="left")
    stat_table.add_column(style=BONE_WHITE, justify="right")
    stat_table.add_column(style=FUNGAL_CYAN, justify="left")

    stat_table.add_row("MIGHT:", str(character.might), f"({calculate_stat_mod(character.might):+d})")
    stat_table.add_row("WITS:", str(character.wits), f"({calculate_stat_mod(character.wits):+d})")
    stat_table.add_row("GRIT:", str(character.grit), f"({calculate_stat_mod(character.grit):+d})")
    stat_table.add_row("AETHER:", str(character.aether), f"({calculate_stat_mod(character.aether):+d})")

    dice_pool = character.gear.get_total_dice_bonus(None)
    dice_text = Text("\nDICE POOL\n", style=WILLOW_GOLD + " bold underline")
    dice_text.append(render_dice_pips(dice_pool, max_pips=5))
    dice_text.append(f" {dice_pool}d6", style=FUNGAL_CYAN + " bold")

    stats_panel_content = Table.grid()
    stats_panel_content.add_row(stat_table)
    stats_panel_content.add_row(dice_text)

    # === LAYOUT ===
    layout = Layout()
    layout.split_row(
        Layout(name="equipment", ratio=2),
        Layout(name="stats", ratio=1),
    )
    layout["equipment"].update(Panel(equipment_grid, border_style=DECAY_GREEN, box=box.SIMPLE))
    layout["stats"].update(Panel(stats_panel_content, border_style=DECAY_GREEN, box=box.SIMPLE, padding=(1, 2)))

    return Panel(
        Group(header, "", layout),
        title=f"[bold {WILLOW_GOLD}]CHARACTER SHEET[/]",
        title_align="center",
        border_style=DECAY_GREEN,
        box=box.DOUBLE,
        padding=(1, 2),
        width=console_width,
    )


def render_dual_backpack(character: Character, width: int = 40) -> Panel:
    """Render inventory as a two-column backpack display.

    Args:
        character: Engine Character with .inventory dict.
        width: Panel width.

    Returns:
        Rich Panel with left/right column layout.
    """
    if not character.inventory:
        return Panel("[dim]Backpack is empty.[/dim]", title="Backpack", border_style=DECAY_GREEN, width=width)

    sorted_keys = sorted(character.inventory.keys())
    left = [k for i, k in enumerate(sorted_keys) if i % 2 == 0]
    right = [k for i, k in enumerate(sorted_keys) if i % 2 == 1]
    max_rows = max(len(left), len(right))

    lines = []
    for row in range(max_rows):
        if row < len(left):
            l_name = character.inventory[left[row]].name
            l_str = f"[{left[row]}] {l_name[:13]}\u2026" if len(l_name) > 14 else f"[{left[row]}] {l_name}"
        else:
            l_str = ""
        if row < len(right):
            r_name = character.inventory[right[row]].name
            r_str = f"[{right[row]}] {r_name[:13]}\u2026" if len(r_name) > 14 else f"[{right[row]}] {r_name}"
        else:
            r_str = ""
        lines.append(f" {l_str:<20}| {r_str}")

    return Panel(
        "\n".join(lines),
        title=f"Backpack ({len(character.inventory)})",
        border_style=DECAY_GREEN,
        box=box.ROUNDED,
        width=width,
    )


def render_item_detail(item: GearItem) -> Panel:
    """Render a detailed inspection of a single item.

    Args:
        item: The GearItem to inspect.

    Returns:
        Rich Panel with full item stats and description.
    """
    lines = Text()
    lines.append(f"{item.name}\n", style=WILLOW_GOLD + " bold")
    tier_val = item.tier.value if hasattr(item.tier, 'value') else item.tier
    lines.append(f"Slot: {item.slot.value}  |  Tier: {tier_val}\n", style=BONE_WHITE)
    lines.append("Dice: ", style=BONE_WHITE)
    lines.append(render_dice_pips(tier_val))
    lines.append("\n")

    if item.damage_reduction:
        lines.append(f"DR: {item.damage_reduction}\n", style=FUNGAL_CYAN)
    if item.stat_bonuses:
        bonus_strs = [f"{stat.value} {val:+d}" for stat, val in item.stat_bonuses.items()]
        lines.append(f"Bonuses: {', '.join(bonus_strs)}\n", style=FUNGAL_CYAN)
    if item.special_traits:
        lines.append(f"Traits: {', '.join(item.special_traits)}\n", style=FUNGAL_CYAN)
    if item.two_handed:
        lines.append("Two-Handed\n", style=EMBER_RUST)
    if item.description:
        lines.append(f"\n{item.description}\n", style=BONE_WHITE + " italic")

    return Panel(lines, title="Item Detail", border_style=WILLOW_GOLD, box=box.ROUNDED)

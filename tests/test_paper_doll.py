#!/usr/bin/env python3
"""
Tests for Burnwillow Paper Doll rendering system.
Verifies paper doll renders correctly from engine types.
"""
import pytest
from rich.console import Console
from rich.panel import Panel

from codex.games.burnwillow.engine import (
    Character, GearSlot, GearItem, GearGrid,
)
from codex.games.burnwillow.paper_doll import (
    render_paper_doll,
    render_dice_pips,
    render_hp_bar,
    render_doom_pips,
    render_dual_backpack,
    render_item_detail,
)


def _make_gear_item(name: str, slot: GearSlot, tier: int = 1,
                    traits: list | None = None) -> GearItem:
    """Helper to build a GearItem with sensible defaults."""
    return GearItem(
        name=name,
        slot=slot,
        tier=tier,
        stat_bonuses={},
        damage_reduction=0,
        special_traits=traits or [],
    )


def _make_character(name: str = "Moss", equipped: dict | None = None) -> Character:
    """Helper to build a Character with optional pre-equipped gear.

    Character uses init=False for max_hp/current_hp/base_defense —
    they're computed in __post_init__ from stats.
    """
    grid = GearGrid()
    if equipped:
        for slot, item in equipped.items():
            grid.equip(item)
    return Character(
        name=name,
        might=14, wits=12, grit=16, aether=10,
        gear=grid, inventory={},
    )


class TestDicePips:
    def test_zero_pips(self):
        result = render_dice_pips(0, max_pips=5)
        assert "o" * 5 in result.plain

    def test_full_pips(self):
        result = render_dice_pips(5, max_pips=5)
        assert "*" * 5 in result.plain

    def test_partial_pips(self):
        result = render_dice_pips(3, max_pips=5)
        plain = result.plain
        assert plain.count("*") == 3
        assert plain.count("o") == 2


class TestHpBar:
    def test_full_hp(self):
        result = render_hp_bar(15, 15)
        assert result is not None

    def test_zero_hp(self):
        result = render_hp_bar(0, 15)
        assert result is not None


class TestPaperDollRendering:
    def test_empty_gear_renders(self):
        char = _make_character("Fern")
        panel = render_paper_doll(char, console_width=80)
        assert isinstance(panel, Panel)

    def test_equipped_gear_renders(self):
        equipped = {
            GearSlot.R_HAND: _make_gear_item("Sap Cudgel", GearSlot.R_HAND, tier=2),
            GearSlot.CHEST: _make_gear_item("Ironbark Plate", GearSlot.CHEST, tier=2),
            GearSlot.HEAD: _make_gear_item("Bark Helm", GearSlot.HEAD, tier=2),
        }
        char = _make_character("Moss", equipped=equipped)
        panel = render_paper_doll(char, console_width=80)
        assert isinstance(panel, Panel)

    def test_paper_doll_contains_character_name(self):
        char = _make_character("Thornwalker")
        panel = render_paper_doll(char, console_width=80)
        console = Console(file=open("/dev/null", "w"), force_terminal=True)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()
        assert "THORNWALKER" in output.upper()


class TestItemDetail:
    def test_renders_basic_item(self):
        item = _make_gear_item("Rusted Shortsword", GearSlot.R_HAND, tier=1)
        panel = render_item_detail(item)
        assert isinstance(panel, Panel)

    def test_renders_item_with_traits(self):
        item = _make_gear_item("Arborist's Aegis", GearSlot.L_HAND, tier=4,
                               traits=["INTERCEPT", "REFLECT"])
        panel = render_item_detail(item)
        assert isinstance(panel, Panel)

    def test_display_name_with_affixes(self):
        item = _make_gear_item("Longsword", GearSlot.R_HAND, tier=2)
        item.prefix = "Blazing"
        item.suffix = "of the Canopy"
        panel = render_item_detail(item)
        console = Console(file=__import__("io").StringIO(), force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()
        assert "Blazing" in output
        assert "Canopy" in output

    def test_prefix_effect_shown(self):
        item = _make_gear_item("Axe", GearSlot.R_HAND, tier=2)
        item.prefix = "Vampiric"
        console = Console(file=__import__("io").StringIO(), force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(render_item_detail(item))
        output = capture.get()
        assert "Heal" in output and "kill" in output

    def test_suffix_effect_shown(self):
        item = _make_gear_item("Ring", GearSlot.R_RING, tier=2)
        item.suffix = "of Thorns"
        console = Console(file=__import__("io").StringIO(), force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(render_item_detail(item))
        output = capture.get()
        assert "Reflect" in output

    def test_gear_set_progress_shown(self):
        item1 = _make_gear_item("Warden Helm", GearSlot.HEAD, tier=3)
        item1.set_id = "wardens_watch"
        item2 = _make_gear_item("Warden Shield", GearSlot.L_HAND, tier=3)
        item2.set_id = "wardens_watch"
        grid = GearGrid()
        grid.equip(item1)
        grid.equip(item2)
        console = Console(file=__import__("io").StringIO(), force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(render_item_detail(item1, gear_grid=grid))
        output = capture.get()
        assert "Warden" in output
        assert "2/" in output  # Shows 2/X progress

    def test_named_legendary_ability_shown(self):
        item = _make_gear_item("Sun-Cleaver", GearSlot.R_HAND, tier=4)
        console = Console(file=__import__("io").StringIO(), force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(render_item_detail(item))
        output = capture.get()
        assert "Ember Momentum" in output

    def test_combo_hints_for_setup_trait(self):
        item = _make_gear_item("Net", GearSlot.R_HAND, tier=2, traits=["[Snare]"])
        console = Console(file=__import__("io").StringIO(), force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(render_item_detail(item))
        output = capture.get()
        assert "CLEAVE" in output or "RANGED" in output

    def test_combo_hints_for_payoff_trait(self):
        item = _make_gear_item("Axe", GearSlot.R_HAND, tier=2, traits=["[Cleave]"])
        console = Console(file=__import__("io").StringIO(), force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(render_item_detail(item))
        output = capture.get()
        assert "SNARE" in output or "CHARGE" in output


class TestDualBackpack:
    def test_empty_backpack(self):
        char = _make_character("Empty")
        panel = render_dual_backpack(char)
        assert isinstance(panel, Panel)

    def test_populated_backpack(self):
        char = _make_character("Loaded")
        item = _make_gear_item("Healing Potion", GearSlot.HEAD, tier=1)
        char.inventory[1] = item
        char.inventory[2] = _make_gear_item("Rope", GearSlot.HEAD, tier=1)
        panel = render_dual_backpack(char)
        assert isinstance(panel, Panel)


# Visual showcase (run with: python tests/test_paper_doll.py)
def main():
    console = Console()
    console.clear()

    console.print("\n[bold #FFD700]TEST 1: DICE PIP VISUALIZATION[/bold #FFD700]")
    for i in range(6):
        pips = render_dice_pips(i, max_pips=5)
        console.print(f"  {i}d6: {pips}")

    console.print("\n[bold #FFD700]TEST 2: MID-GAME CHARACTER[/bold #FFD700]")
    equipped = {
        GearSlot.HEAD: _make_gear_item("Bark Helm", GearSlot.HEAD, tier=2),
        GearSlot.CHEST: _make_gear_item("Ironbark Plate", GearSlot.CHEST, tier=2),
        GearSlot.LEGS: _make_gear_item("Thornwalker", GearSlot.LEGS, tier=2),
        GearSlot.R_HAND: _make_gear_item("Sap Cudgel", GearSlot.R_HAND, tier=2),
        GearSlot.L_HAND: _make_gear_item("Scrap Shield", GearSlot.L_HAND, tier=1),
    }
    char = _make_character("Moss", equipped=equipped)
    console.print(render_paper_doll(char, console_width=80))

    console.print("\n[bold #FFD700]TEST 3: STARTER CHARACTER (EMPTY SLOTS)[/bold #FFD700]")
    starter = _make_character("Fern", equipped={
        GearSlot.R_HAND: _make_gear_item("Rusty Shiv", GearSlot.R_HAND, tier=1),
    })
    console.print(render_paper_doll(starter, console_width=80))

    console.print("\n[bold #00FFCC]Tests complete![/bold #00FFCC]")
    console.print("[dim]All components rendered successfully.[/dim]\n")


if __name__ == "__main__":
    main()

"""
Journey Renderer — Rich terminal rendering for travel sequences.
================================================================

All functions return Rich renderables (Panel, Table, etc.).
No input handling — that lives in the game loops.

WO-V64.0
"""

from __future__ import annotations

from typing import List, Optional

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from codex.core.mechanics.journey import (
    CampResult, EventOutcome, JourneyEngine, JourneyState, TravelRole,
)


# ─── Color Scheme ────────────────────────────────────────────────────────

_TERRAIN_COLORS = {
    "road": "wheat1",
    "forest": "green",
    "mountain": "grey70",
    "swamp": "dark_olive_green3",
    "coast": "dodger_blue1",
    "underdark": "purple4",
    "urban": "gold1",
}


def _terrain_color(terrain_type: str) -> str:
    return _TERRAIN_COLORS.get(terrain_type, "white")


# ─── Journey Announcement ───────────────────────────────────────────────

def render_journey_announcement(journey: JourneyEngine) -> Panel:
    """Show journey overview: origin, destination, segments, supplies."""
    text = Text()
    text.append(f"{journey.origin}", style="bold cyan")
    text.append("  -->  ", style="dim")
    text.append(f"{journey.destination}\n\n", style="bold cyan")

    text.append("Route:\n", style="bold")
    for i, seg in enumerate(journey.segments):
        color = _terrain_color(seg.terrain_type)
        marker = ">" if i == journey.current_segment_idx else " "
        text.append(f"  {marker} ", style="bold" if marker == ">" else "dim")
        text.append(f"{seg.name}", style=color)
        text.append(f" ({seg.terrain_type}, {seg.days}d)\n", style="dim")

    text.append(f"\nTotal: {journey.total_days} days", style="bold")
    text.append(f"  |  Supplies: {journey.supplies}", style="bold")
    text.append(f"  |  Party: {journey.party_size}\n", style="bold")

    if journey.deadline_days is not None:
        on_time, remaining = journey.check_deadline()
        dl_style = "green" if remaining > 2 else ("yellow" if remaining > 0 else "red")
        text.append(f"Deadline: {journey.deadline_days} days", style=dl_style)

    return Panel(text, title="[bold]JOURNEY[/bold]", border_style="cyan", box=box.DOUBLE)


# ─── Role Assignment ────────────────────────────────────────────────────

def render_role_assignment(journey: JourneyEngine) -> Table:
    """Show current role assignments."""
    table = Table(title="Travel Roles", box=box.SIMPLE, border_style="dim")
    table.add_column("Role", style="bold")
    table.add_column("Character", style="cyan")
    table.add_column("Stat", justify="right")
    table.add_column("Effect", style="dim")

    effects = {
        TravelRole.SCOUT: "Detect threats, prevent ambush",
        TravelRole.GUIDE: "Stay on course, avoid delays",
        TravelRole.FORAGER: "Find food, reduce rations",
        TravelRole.GUARD: "Night watch, prevent raids",
    }

    for role in TravelRole:
        assignment = journey.roles.get(role)
        name = assignment.character_name if assignment else "[dim]Unassigned[/dim]"
        stat = str(assignment.stat_value) if assignment else "-"
        table.add_row(role.value.title(), name, stat, effects[role])

    return table


# ─── Segment Progress ───────────────────────────────────────────────────

def render_segment_header(journey: JourneyEngine) -> Panel:
    """Show current segment with progress."""
    seg = journey.current_segment
    if not seg:
        return Panel("[green]Journey complete.[/green]")

    idx = journey.current_segment_idx + 1
    total = len(journey.segments)
    color = _terrain_color(seg.terrain_type)

    # Build progress bar
    filled = journey.current_segment_idx
    bar_len = 20
    filled_chars = int((filled / total) * bar_len) if total > 0 else 0
    bar = "[green]" + "#" * filled_chars + "[/green]" + "[dim]" + "-" * (bar_len - filled_chars) + "[/dim]"

    text = Text()
    text.append(f"Segment {idx}/{total}: ", style="bold")
    text.append(f"{seg.name}\n", style=f"bold {color}")
    text.append(f"Terrain: {seg.terrain_type}  |  Days: {seg.days}  |  Day {journey.days_elapsed + 1}\n", style="dim")

    if journey.deadline_days is not None:
        on_time, remaining = journey.check_deadline()
        dl_style = "green" if remaining > 2 else ("yellow" if remaining > 0 else "bold red")
        text.append(f"Deadline: {remaining} days remaining", style=dl_style)

    return Panel(text, border_style=color)


# ─── Event Rendering ────────────────────────────────────────────────────

def render_event(outcome: EventOutcome) -> Panel:
    """Render a single journey event and its outcome."""
    event = outcome.event
    text = Text()
    text.append(f"{event.title}\n", style="bold")
    text.append(f"{event.description}\n\n", style="italic")

    role_name = event.target_role.title()
    text.append(f"{role_name} check: ", style="dim")
    text.append(f"{outcome.roll}", style="bold")
    text.append(f" vs DC {event.dc} — ", style="dim")

    if outcome.success:
        text.append("SUCCESS\n", style="bold green")
        text.append(outcome.text, style="green")
    else:
        text.append("FAILURE\n", style="bold red")
        text.append(outcome.text, style="red")

    if outcome.reward:
        for k, v in outcome.reward.items():
            text.append(f"\n  +{v} {k}", style="green")
    if outcome.cost:
        for k, v in outcome.cost.items():
            text.append(f"\n  -{v} {k}", style="red")

    border = "green" if outcome.success else "red"
    type_icon = {"combat": "X", "discovery": "?", "skill_challenge": "!"}
    icon = type_icon.get(event.event_type, ".")
    return Panel(text, title=f"[bold][{icon}] Event[/bold]", border_style=border)


# ─── Camp Phase ─────────────────────────────────────────────────────────

def render_camp(result: CampResult, supplies_after: int) -> Panel:
    """Render camp phase results."""
    text = Text()
    text.append("CAMP\n\n", style="bold")

    for role_key, data in result.role_outcomes.items():
        name = data.get("character", "No one")
        success = data.get("success", False)
        style = "green" if success else "red"
        icon = "+" if success else "-"
        text.append(f"  [{icon}] {role_key.title()} ({name}): ", style="dim")
        text.append(f"{data.get('text', '')}\n", style=style)

    text.append(f"\nRations consumed: {result.rations_consumed}", style="dim")
    if result.bonus_rations > 0:
        text.append(f" (foraged {result.bonus_rations})", style="green")
    text.append(f"\nSupplies remaining: {supplies_after}\n", style="bold")

    if result.hp_changes:
        text.append("\nStarvation!\n", style="bold red")
        for name, delta in result.hp_changes.items():
            text.append(f"  {name}: {delta} HP\n", style="red")

    if result.night_raid:
        text.append("\n[bold red]NIGHT RAID![/bold red] The camp is attacked!\n")
    if result.lost:
        text.append("\n[bold yellow]LOST![/bold yellow] An extra day wasted.\n")

    border = "yellow" if (result.night_raid or result.lost) else "dim"
    return Panel(text, border_style=border)


# ─── Arrival ────────────────────────────────────────────────────────────

def render_arrival(journey: JourneyEngine) -> Panel:
    """Render arrival summary."""
    text = Text()
    on_time, remaining = journey.check_deadline()

    text.append(f"Arrived at {journey.destination}\n\n", style="bold cyan")
    text.append(f"Days traveled: {journey.days_elapsed}\n", style="dim")
    text.append(f"Supplies remaining: {journey.supplies}\n", style="dim")

    if journey.deadline_days is not None:
        if on_time:
            if remaining > 0:
                text.append(f"\nArrived with {remaining} days to spare.", style="green")
            else:
                text.append("\nArrived just in time!", style="yellow")
        else:
            text.append(f"\nLATE by {abs(remaining)} day(s)!", style="bold red")

    # Summary stats
    total_events = sum(len(outcomes) for outcomes in journey.segment_history)
    successes = sum(
        1 for outcomes in journey.segment_history
        for o in outcomes if o.success
    )
    combats = sum(
        1 for outcomes in journey.segment_history
        for o in outcomes if o.combat_triggered
    )
    raids = sum(1 for c in journey.camp_history if c.night_raid)

    text.append(f"\n\nEvents: {total_events} ({successes} succeeded)", style="dim")
    if combats:
        text.append(f"  |  Ambushes: {combats}", style="red")
    if raids:
        text.append(f"  |  Night raids: {raids}", style="red")

    border = "green" if on_time else "red"
    return Panel(text, title="[bold]JOURNEY COMPLETE[/bold]", border_style=border, box=box.DOUBLE)

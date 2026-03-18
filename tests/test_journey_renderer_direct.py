"""
Direct unit tests for codex/core/mechanics/journey_renderer.py

Covers:
- render_journey_announcement returns a Panel
- render_role_assignment returns a Table
- render_event returns a Panel for both success and failure outcomes
- _terrain_color fallback for unknown terrain types
"""

import pytest

from rich.panel import Panel
from rich.table import Table

from codex.core.mechanics.journey import (
    CampResult,
    EventOutcome,
    JourneyEngine,
    JourneyEvent,
    RoleAssignment,
    TerrainSegment,
    TravelRole,
    clear_terrain_cache,
)
from codex.core.mechanics.journey_renderer import (
    _terrain_color,
    render_event,
    render_journey_announcement,
    render_role_assignment,
)


# ── Shared Fixtures ───────────────────────────────────────────────────────

def _make_journey(
    terrain_type: str = "road",
    deadline_days: int = None,
    supplies: int = 10,
) -> JourneyEngine:
    """Build a minimal two-segment JourneyEngine without touching the filesystem."""
    segments = [
        TerrainSegment(name="Forest Path", terrain_type="forest", days=2),
        TerrainSegment(name=f"{terrain_type.title()} Road", terrain_type=terrain_type, days=3),
    ]
    return JourneyEngine(
        origin="Greenest",
        destination="Candlekeep",
        segments=segments,
        deadline_days=deadline_days,
        party_size=3,
        supplies=supplies,
    )


def _make_event_outcome(success: bool = True) -> EventOutcome:
    event = JourneyEvent(
        event_id="test_evt",
        event_type="skill_challenge",
        title="Dense Fog",
        description="Thick fog descends, disorienting the party.",
        target_role="guide",
        dc=10,
        success_text="You find landmarks and press on.",
        failure_text="You wander off course.",
        success_reward={"rations": 1},
        failure_cost={"days": 1},
    )
    return EventOutcome(
        event=event,
        roll=12 if success else 5,
        stat_value=2,
        success=success,
        text=event.success_text if success else event.failure_text,
        reward={"rations": 1} if success else {},
        cost={} if success else {"days": 1},
    )


# ── Tests ─────────────────────────────────────────────────────────────────

class TestTerrainColor:
    """_terrain_color returns the correct color or falls back to white."""

    def test_known_terrain_returns_color(self):
        assert _terrain_color("forest") == "green"
        assert _terrain_color("swamp") == "dark_olive_green3"
        assert _terrain_color("mountain") == "grey70"
        assert _terrain_color("urban") == "gold1"

    def test_unknown_terrain_falls_back_to_white(self):
        assert _terrain_color("lava_plains") == "white"
        assert _terrain_color("") == "white"
        assert _terrain_color("FOREST") == "white"  # case-sensitive

    def test_all_canonical_terrains_have_non_white_color(self):
        canonical = ["road", "forest", "mountain", "swamp", "coast", "underdark", "urban"]
        for terrain in canonical:
            color = _terrain_color(terrain)
            assert color != "white", f"Expected non-white for known terrain '{terrain}'"


class TestRenderJourneyAnnouncement:
    """render_journey_announcement must return a Rich Panel."""

    def test_returns_panel(self):
        journey = _make_journey()
        result = render_journey_announcement(journey)
        assert isinstance(result, Panel)

    def test_panel_contains_origin_and_destination(self):
        journey = _make_journey()
        panel = render_journey_announcement(journey)
        # The renderable is a Text object — convert via repr for content check.
        rendered = str(panel.renderable)
        assert "Greenest" in rendered
        assert "Candlekeep" in rendered

    def test_panel_with_deadline(self):
        # Deadline tracking should not raise and still returns a Panel.
        journey = _make_journey(deadline_days=10)
        result = render_journey_announcement(journey)
        assert isinstance(result, Panel)

    def test_panel_with_past_deadline(self):
        # days_elapsed > deadline_days — deadline in red, still returns Panel.
        journey = _make_journey(deadline_days=1)
        journey.days_elapsed = 5
        result = render_journey_announcement(journey)
        assert isinstance(result, Panel)


class TestRenderRoleAssignment:
    """render_role_assignment must return a Rich Table with all four roles."""

    def test_returns_table(self):
        journey = _make_journey()
        result = render_role_assignment(journey)
        assert isinstance(result, Table)

    def test_table_has_four_role_rows(self):
        journey = _make_journey()
        table = render_role_assignment(journey)
        # Each TravelRole enum member maps to one row.
        assert table.row_count == len(TravelRole)

    def test_table_with_assigned_roles(self):
        journey = _make_journey()
        journey.assign_role(TravelRole.SCOUT, "Kael", 3)
        journey.assign_role(TravelRole.GUIDE, "Mira", 2)
        result = render_role_assignment(journey)
        assert isinstance(result, Table)
        assert result.row_count == 4


class TestRenderEvent:
    """render_event must return a Panel reflecting success or failure state."""

    def test_success_outcome_returns_panel(self):
        outcome = _make_event_outcome(success=True)
        result = render_event(outcome)
        assert isinstance(result, Panel)

    def test_failure_outcome_returns_panel(self):
        outcome = _make_event_outcome(success=False)
        result = render_event(outcome)
        assert isinstance(result, Panel)

    def test_success_panel_border_is_green(self):
        outcome = _make_event_outcome(success=True)
        panel = render_event(outcome)
        assert panel.border_style == "green"

    def test_failure_panel_border_is_red(self):
        outcome = _make_event_outcome(success=False)
        panel = render_event(outcome)
        assert panel.border_style == "red"

    def test_combat_event_type_uses_x_icon(self):
        outcome = _make_event_outcome(success=False)
        outcome.event.event_type = "combat"
        panel = render_event(outcome)
        assert "[X]" in str(panel.title)

    def test_discovery_event_type_uses_question_icon(self):
        outcome = _make_event_outcome(success=True)
        outcome.event.event_type = "discovery"
        panel = render_event(outcome)
        assert "[?]" in str(panel.title)

    def test_unknown_event_type_uses_dot_icon(self):
        outcome = _make_event_outcome(success=True)
        outcome.event.event_type = "weird_custom_type"
        panel = render_event(outcome)
        assert "[.]" in str(panel.title)

    def test_reward_in_success_content(self):
        outcome = _make_event_outcome(success=True)
        outcome.reward = {"rations": 2}
        panel = render_event(outcome)
        rendered = str(panel.renderable)
        assert "rations" in rendered

    def test_cost_in_failure_content(self):
        outcome = _make_event_outcome(success=False)
        outcome.cost = {"days": 1}
        panel = render_event(outcome)
        rendered = str(panel.renderable)
        assert "days" in rendered

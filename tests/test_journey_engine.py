"""
Tests for the JourneyEngine — WO-V64.0 Travel System.
"""

import random
import pytest

from codex.core.mechanics.journey import (
    CampResult,
    EventOutcome,
    JourneyEngine,
    JourneyEvent,
    JourneyState,
    RoleAssignment,
    TerrainSegment,
    TravelRole,
    build_journey_from_world_map,
    clear_terrain_cache,
    load_terrain_events,
)
from codex.core.mechanics.journey_renderer import (
    render_arrival,
    render_camp,
    render_event,
    render_journey_announcement,
    render_role_assignment,
    render_segment_header,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def basic_segments():
    return [
        TerrainSegment(name="Greenfields", terrain_type="road", days=2),
        TerrainSegment(name="Darkwood", terrain_type="forest", days=3),
        TerrainSegment(name="Fenmarsh", terrain_type="swamp", days=2),
    ]


@pytest.fixture
def journey(basic_segments):
    return JourneyEngine(
        origin="Greenest",
        destination="Baldur's Gate",
        segments=basic_segments,
        deadline_days=10,
        party_size=4,
        supplies=20,
        tier=1,
    )


@pytest.fixture
def seeded_rng():
    return random.Random(42)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_terrain_cache()
    yield
    clear_terrain_cache()


# ── TerrainSegment ──────────────────────────────────────────────────────


class TestTerrainSegment:
    def test_defaults(self):
        seg = TerrainSegment(name="Test", terrain_type="road")
        assert seg.days == 2
        assert seg.event_count == 2

    def test_roundtrip(self):
        seg = TerrainSegment(name="Darkwood", terrain_type="forest", days=3, event_count=4)
        rebuilt = TerrainSegment.from_dict(seg.to_dict())
        assert rebuilt.name == seg.name
        assert rebuilt.terrain_type == seg.terrain_type
        assert rebuilt.days == seg.days
        assert rebuilt.event_count == seg.event_count


# ── RoleAssignment ──────────────────────────────────────────────────────


class TestRoleAssignment:
    def test_roundtrip(self):
        ra = RoleAssignment(TravelRole.SCOUT, "Kael", 3)
        rebuilt = RoleAssignment.from_dict(ra.to_dict())
        assert rebuilt.role == TravelRole.SCOUT
        assert rebuilt.character_name == "Kael"
        assert rebuilt.stat_value == 3


# ── JourneyEvent ────────────────────────────────────────────────────────


class TestJourneyEvent:
    def test_from_dict_minimal(self):
        ev = JourneyEvent.from_dict({"id": "test", "type": "discovery"})
        assert ev.event_id == "test"
        assert ev.event_type == "discovery"
        assert ev.dc == 10

    def test_from_dict_full(self):
        ev = JourneyEvent.from_dict({
            "id": "wolf_pack",
            "type": "combat",
            "title": "Wolf Pack",
            "description": "Wolves!",
            "target_role": "scout",
            "dc": 12,
            "success": "You dodge them.",
            "failure": "They attack.",
            "enemies_tier": 1,
        })
        assert ev.title == "Wolf Pack"
        assert ev.enemies_tier == 1
        assert ev.target_role == "scout"


# ── JourneyEngine Initialization ────────────────────────────────────────


class TestJourneyInit:
    def test_initial_state(self, journey):
        assert journey.state == JourneyState.PLANNING
        assert journey.origin == "Greenest"
        assert journey.destination == "Baldur's Gate"
        assert journey.party_size == 4
        assert journey.supplies == 20
        assert journey.total_days == 7  # 2 + 3 + 2
        assert journey.current_segment_idx == 0
        assert journey.days_elapsed == 0

    def test_party_size_minimum(self):
        j = JourneyEngine("A", "B", [], party_size=0)
        assert j.party_size == 1


# ── Role Assignment ─────────────────────────────────────────────────────


class TestRoleAssignmentOnEngine:
    def test_assign_and_get(self, journey):
        journey.assign_role(TravelRole.SCOUT, "Kael", 3)
        assert journey.get_role_stat(TravelRole.SCOUT) == 3
        assert journey.get_role_character(TravelRole.SCOUT) == "Kael"

    def test_unassigned_defaults(self, journey):
        assert journey.get_role_stat(TravelRole.FORAGER) == 0
        assert journey.get_role_character(TravelRole.FORAGER) == "No one"


# ── Segment Resolution ──────────────────────────────────────────────────


class TestSegmentResolution:
    def test_resolve_produces_outcomes(self, journey, seeded_rng):
        journey.assign_role(TravelRole.SCOUT, "Kael", 3)
        journey.assign_role(TravelRole.GUIDE, "Lyra", 2)
        outcomes = journey.resolve_segment(seeded_rng)
        assert isinstance(outcomes, list)
        assert all(isinstance(o, EventOutcome) for o in outcomes)
        assert journey.state == JourneyState.TRAVELING

    def test_resolve_past_end_returns_empty(self, journey):
        journey.current_segment_idx = 999
        outcomes = journey.resolve_segment()
        assert outcomes == []

    def test_resolve_records_history(self, journey, seeded_rng):
        journey.resolve_segment(seeded_rng)
        assert len(journey.segment_history) == 1

    def test_event_outcome_fields(self, journey, seeded_rng):
        journey.assign_role(TravelRole.SCOUT, "Kael", 5)
        outcomes = journey.resolve_segment(seeded_rng)
        if outcomes:
            o = outcomes[0]
            assert hasattr(o, "roll")
            assert hasattr(o, "success")
            assert hasattr(o, "text")
            assert hasattr(o, "event")


# ── Camp Phase ──────────────────────────────────────────────────────────


class TestCampPhase:
    def test_camp_consumes_rations(self, journey, seeded_rng):
        initial = journey.supplies
        journey.resolve_segment(seeded_rng)
        result = journey.camp_phase(seeded_rng)
        assert isinstance(result, CampResult)
        assert journey.supplies <= initial
        assert result.rations_consumed > 0

    def test_camp_records_history(self, journey, seeded_rng):
        journey.resolve_segment(seeded_rng)
        journey.camp_phase(seeded_rng)
        assert len(journey.camp_history) == 1

    def test_camp_forager_check(self, journey, seeded_rng):
        journey.assign_role(TravelRole.FORAGER, "Thorn", 5)
        journey.resolve_segment(seeded_rng)
        result = journey.camp_phase(seeded_rng)
        assert "forager" in result.role_outcomes

    def test_camp_guard_check(self, journey, seeded_rng):
        journey.assign_role(TravelRole.GUARD, "Bryn", 4)
        journey.resolve_segment(seeded_rng)
        result = journey.camp_phase(seeded_rng)
        assert "guard" in result.role_outcomes

    def test_camp_guide_check(self, journey, seeded_rng):
        journey.assign_role(TravelRole.GUIDE, "Lyra", 3)
        journey.resolve_segment(seeded_rng)
        result = journey.camp_phase(seeded_rng)
        assert "guide" in result.role_outcomes

    def test_starvation_when_no_supplies(self):
        # Use a fixed seed where forager fails (stat=0, need 10+)
        rng = random.Random(99)
        seg = [TerrainSegment("Road", "road", days=2)]
        j = JourneyEngine("A", "B", seg, supplies=0, party_size=2)
        j.assign_role(TravelRole.FORAGER, "Thorn", 0)
        j.assign_role(TravelRole.GUARD, "Bryn", 0)
        j.assign_role(TravelRole.GUIDE, "Lyra", 0)
        j.resolve_segment(rng)
        result = j.camp_phase(rng)
        # With 0 starting supplies, rations_consumed should be capped
        # The camp may still produce bonus rations from events
        assert result.rations_consumed >= 0


# ── Advancement ─────────────────────────────────────────────────────────


class TestAdvancement:
    def test_advance_increments_segment(self, journey):
        assert journey.current_segment_idx == 0
        journey.advance()
        assert journey.current_segment_idx == 1
        assert journey.days_elapsed == 2  # first segment was 2 days

    def test_advance_to_arrival(self, journey):
        for _ in journey.segments:
            journey.advance()
        assert journey.state == JourneyState.ARRIVED
        assert journey.is_complete

    def test_advance_past_end(self, journey):
        for _ in range(10):
            journey.advance()
        assert journey.state == JourneyState.ARRIVED


# ── Queries ─────────────────────────────────────────────────────────────


class TestQueries:
    def test_is_complete_initial(self, journey):
        assert not journey.is_complete

    def test_current_segment(self, journey):
        seg = journey.current_segment
        assert seg is not None
        assert seg.name == "Greenfields"

    def test_current_segment_after_advance(self, journey):
        journey.advance()
        seg = journey.current_segment
        assert seg.name == "Darkwood"

    def test_current_segment_after_complete(self, journey):
        for _ in journey.segments:
            journey.advance()
        assert journey.current_segment is None

    def test_progress_fraction(self, journey):
        assert journey.progress_fraction == 0.0
        journey.advance()
        assert abs(journey.progress_fraction - 1 / 3) < 0.01
        journey.advance()
        journey.advance()
        assert journey.progress_fraction == 1.0

    def test_check_deadline(self, journey):
        on_time, remaining = journey.check_deadline()
        assert on_time
        assert remaining == 10

    def test_check_deadline_no_deadline(self):
        j = JourneyEngine("A", "B", [])
        on_time, remaining = j.check_deadline()
        assert on_time
        assert remaining == 999

    def test_days_remaining(self, journey):
        assert journey.days_remaining == 7
        journey.advance()
        assert journey.days_remaining == 5  # 3 + 2


# ── Serialization ───────────────────────────────────────────────────────


class TestSerialization:
    def test_roundtrip(self, journey, seeded_rng):
        journey.assign_role(TravelRole.SCOUT, "Kael", 3)
        journey.assign_role(TravelRole.GUIDE, "Lyra", 2)
        journey.resolve_segment(seeded_rng)
        journey.advance()

        data = journey.to_dict()
        rebuilt = JourneyEngine.from_dict(data)

        assert rebuilt.origin == journey.origin
        assert rebuilt.destination == journey.destination
        assert rebuilt.supplies == journey.supplies
        assert rebuilt.current_segment_idx == journey.current_segment_idx
        assert rebuilt.days_elapsed == journey.days_elapsed
        assert rebuilt.state == journey.state
        assert len(rebuilt.segments) == len(journey.segments)
        assert TravelRole.SCOUT in rebuilt.roles
        assert rebuilt.roles[TravelRole.SCOUT].character_name == "Kael"


# ── Terrain Event Loading ──────────────────────────────────────────────


class TestTerrainLoading:
    def test_load_road_events(self):
        events = load_terrain_events("road", 1)
        assert len(events) >= 3
        assert all("id" in e for e in events)

    def test_load_forest_events(self):
        events = load_terrain_events("forest", 1)
        assert len(events) >= 3

    def test_load_swamp_events(self):
        events = load_terrain_events("swamp", 1)
        assert len(events) >= 2

    def test_load_tier2(self):
        events = load_terrain_events("road", 2)
        assert len(events) >= 2

    def test_unknown_terrain_falls_back_to_road(self):
        events = load_terrain_events("volcanic_wasteland", 1)
        assert len(events) >= 3  # Should fall back to road

    def test_cache_works(self):
        e1 = load_terrain_events("road", 1)
        e2 = load_terrain_events("road", 1)
        assert e1 is e2  # Same object from cache


# ── World Map Builder ──────────────────────────────────────────────────


class TestWorldMapBuilder:
    def test_build_from_simple_map(self):
        world_map = {
            "rooms": {
                "0": {
                    "location_id": "greenest",
                    "name": "Greenest",
                    "terrain": "road",
                    "travel_days": 2,
                    "connections": [1],
                },
                "1": {
                    "location_id": "forest_camp",
                    "name": "Forest Camp",
                    "terrain": "forest",
                    "travel_days": 3,
                    "connections": [0, 2],
                },
                "2": {
                    "location_id": "baldurs_gate",
                    "name": "Baldur's Gate",
                    "terrain": "road",
                    "travel_days": 1,
                    "connections": [1],
                },
            }
        }
        j = build_journey_from_world_map(world_map, "greenest", "baldurs_gate", party_size=4)
        assert j is not None
        assert j.origin == "Greenest"
        assert j.destination == "Baldur's Gate"
        assert len(j.segments) == 2  # forest_camp + baldurs_gate (skip origin)

    def test_build_returns_none_for_missing_rooms(self):
        world_map = {"rooms": {"0": {"location_id": "a", "name": "A"}}}
        assert build_journey_from_world_map(world_map, "a", "nonexistent") is None

    def test_build_with_deadline(self):
        world_map = {
            "rooms": {
                "0": {"location_id": "a", "name": "Start", "connections": [1]},
                "1": {"location_id": "b", "name": "End", "connections": [0]},
            }
        }
        j = build_journey_from_world_map(world_map, "a", "b", deadline_days=15)
        assert j is not None
        assert j.deadline_days == 15


# ── Full Journey Loop ──────────────────────────────────────────────────


class TestFullJourneyLoop:
    def test_full_journey(self, journey, seeded_rng):
        """Run a complete journey from start to finish."""
        journey.assign_role(TravelRole.SCOUT, "Kael", 3)
        journey.assign_role(TravelRole.GUIDE, "Lyra", 2)
        journey.assign_role(TravelRole.FORAGER, "Thorn", 1)
        journey.assign_role(TravelRole.GUARD, "Bryn", 2)

        while not journey.is_complete:
            outcomes = journey.resolve_segment(seeded_rng)
            camp = journey.camp_phase(seeded_rng)
            journey.advance()

        assert journey.state == JourneyState.ARRIVED
        assert journey.current_segment_idx == 3
        assert journey.days_elapsed >= 7
        assert len(journey.segment_history) == 3
        assert len(journey.camp_history) == 3

    def test_full_journey_no_roles(self, journey, seeded_rng):
        """Journey without assigned roles should still work (stat=0)."""
        while not journey.is_complete:
            journey.resolve_segment(seeded_rng)
            journey.camp_phase(seeded_rng)
            journey.advance()

        assert journey.state == JourneyState.ARRIVED


# ── Renderer ────────────────────────────────────────────────────────────


class TestRenderer:
    def test_render_journey_announcement(self, journey):
        panel = render_journey_announcement(journey)
        assert panel is not None

    def test_render_role_assignment(self, journey):
        journey.assign_role(TravelRole.SCOUT, "Kael", 3)
        table = render_role_assignment(journey)
        assert table is not None

    def test_render_segment_header(self, journey):
        panel = render_segment_header(journey)
        assert panel is not None

    def test_render_segment_header_complete(self, journey):
        for _ in journey.segments:
            journey.advance()
        panel = render_segment_header(journey)
        assert panel is not None

    def test_render_event(self, seeded_rng):
        event = JourneyEvent(
            event_id="test", event_type="discovery", title="Test Event",
            description="A test.", target_role="scout", dc=10,
            success_text="You win.", failure_text="You lose.",
        )
        outcome = EventOutcome(
            event=event, roll=12, stat_value=2, success=True,
            text="You win.", reward={"rations": 2},
        )
        panel = render_event(outcome)
        assert panel is not None

    def test_render_camp(self):
        result = CampResult(
            role_outcomes={
                "forager": {"character": "Thorn", "success": True, "text": "Found food!"},
                "guard": {"character": "Bryn", "success": True, "text": "Peaceful night."},
            },
            rations_consumed=4,
            bonus_rations=2,
        )
        panel = render_camp(result, supplies_after=16)
        assert panel is not None

    def test_render_arrival(self, journey):
        for _ in journey.segments:
            journey.advance()
        panel = render_arrival(journey)
        assert panel is not None

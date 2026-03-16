"""
JourneyEngine — Unified travel system for multi-day overland journeys.
=====================================================================

Handles FAR travel (3+ day, multi-terrain-segment journeys) with:
- Role assignment (Scout/Guide/Forager/Guard)
- Terrain-typed event pools loaded from config/travel/*.json
- Camp phases with ration consumption and role checks
- Optional deadline tracking via UniversalClock

System-agnostic: stat values are passed in, not extracted from engines.

WO-V64.0
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from codex.core.config_loader import load_config


# ─── Enums & Data Classes ───────────────────────────────────────────────

class TravelRole(Enum):
    SCOUT = "scout"      # Detect threats — prevents ambush
    GUIDE = "guide"      # Navigate — prevents getting lost
    FORAGER = "forager"  # Find food — reduces ration cost
    GUARD = "guard"      # Night watch — prevents camp raids


class JourneyState(Enum):
    PLANNING = "planning"
    ASSIGNING_ROLES = "assigning_roles"
    TRAVELING = "traveling"
    CAMPING = "camping"
    ARRIVED = "arrived"
    FAILED = "failed"


# Stat names each role checks, in priority order (first match wins)
ROLE_STAT_KEYS: Dict[TravelRole, List[str]] = {
    TravelRole.SCOUT:   ["wits", "wisdom", "cognitive", "insight"],
    TravelRole.GUIDE:   ["wits", "wisdom", "cognitive", "survival"],
    TravelRole.FORAGER: ["grit", "constitution", "physical", "survival"],
    TravelRole.GUARD:   ["might", "strength", "physical", "fortitude"],
}


@dataclass
class TerrainSegment:
    """One leg of a journey."""
    name: str
    terrain_type: str  # maps to config/travel/{terrain_type}.json
    days: int = 2
    event_count: int = 2  # how many events to draw for this segment

    def to_dict(self) -> dict:
        return {"name": self.name, "terrain_type": self.terrain_type,
                "days": self.days, "event_count": self.event_count}

    @classmethod
    def from_dict(cls, d: dict) -> TerrainSegment:
        return cls(name=d["name"], terrain_type=d["terrain_type"],
                   days=d.get("days", 2), event_count=d.get("event_count", 2))


@dataclass
class RoleAssignment:
    """Maps a role to a character and their stat value for the check."""
    role: TravelRole
    character_name: str
    stat_value: int = 0

    def to_dict(self) -> dict:
        return {"role": self.role.value, "character_name": self.character_name,
                "stat_value": self.stat_value}

    @classmethod
    def from_dict(cls, d: dict) -> RoleAssignment:
        return cls(role=TravelRole(d["role"]), character_name=d["character_name"],
                   stat_value=d.get("stat_value", 0))


@dataclass
class JourneyEvent:
    """A single event drawn from a terrain pool."""
    event_id: str
    event_type: str  # "skill_challenge", "combat", "discovery"
    title: str
    description: str
    target_role: str  # role name or "any"
    dc: int = 10
    success_text: str = ""
    failure_text: str = ""
    success_reward: Dict[str, Any] = field(default_factory=dict)
    failure_cost: Dict[str, Any] = field(default_factory=dict)
    enemies_tier: int = 0  # for combat events

    @classmethod
    def from_dict(cls, d: dict) -> JourneyEvent:
        return cls(
            event_id=d.get("id", "unknown"),
            event_type=d.get("type", "skill_challenge"),
            title=d.get("title", "Unknown Event"),
            description=d.get("description", ""),
            target_role=d.get("target_role", "any"),
            dc=d.get("dc", 10),
            success_text=d.get("success", ""),
            failure_text=d.get("failure", ""),
            success_reward=d.get("success_reward", {}),
            failure_cost=d.get("failure_cost", {}),
            enemies_tier=d.get("enemies_tier", 0),
        )


@dataclass
class EventOutcome:
    """Result of resolving a single event."""
    event: JourneyEvent
    roll: int
    stat_value: int
    success: bool
    text: str
    reward: Dict[str, Any] = field(default_factory=dict)
    cost: Dict[str, Any] = field(default_factory=dict)
    combat_triggered: bool = False


@dataclass
class CampResult:
    """Result of a camp phase between segments."""
    role_outcomes: Dict[str, dict] = field(default_factory=dict)
    rations_consumed: int = 0
    rations_remaining: int = 0
    hp_changes: Dict[str, int] = field(default_factory=dict)
    bonus_rations: int = 0
    night_raid: bool = False
    lost: bool = False


# ─── Terrain Pool Loading ────────────────────────────────────────────────

_TERRAIN_CACHE: Dict[str, List[dict]] = {}


def load_terrain_events(terrain_type: str, tier: int = 1) -> List[dict]:
    """Load events for a terrain type and tier from config/travel/*.json."""
    key = f"{terrain_type}_{tier}"
    if key in _TERRAIN_CACHE:
        return _TERRAIN_CACHE[key]

    data = load_config("travel", terrain_type, fallback=None)
    if not data:
        # Fallback to road
        data = load_config("travel", "road", fallback={"events": {}})

    tier_key = f"tier_{tier}"
    events = data.get("events", {}).get(tier_key, [])
    if not events:
        # Try tier_1 as fallback
        events = data.get("events", {}).get("tier_1", [])

    _TERRAIN_CACHE[key] = events
    return events


def clear_terrain_cache():
    """Clear cached terrain event pools (for testing)."""
    _TERRAIN_CACHE.clear()


# ─── Journey Engine ──────────────────────────────────────────────────────

class JourneyEngine:
    """Manages a multi-segment overland journey.

    Usage:
        journey = JourneyEngine("Greenest", "Baldur's Gate", segments, ...)
        journey.assign_role(TravelRole.SCOUT, "Kael", wits_value)
        while not journey.is_complete:
            outcomes = journey.resolve_segment(rng)
            camp = journey.camp_phase(rng)
            journey.advance()
    """

    def __init__(
        self,
        origin: str,
        destination: str,
        segments: List[TerrainSegment],
        deadline_days: Optional[int] = None,
        party_size: int = 1,
        supplies: int = 10,
        tier: int = 1,
    ):
        self.origin = origin
        self.destination = destination
        self.segments = segments
        self.deadline_days = deadline_days
        self.party_size = max(1, party_size)
        self.supplies = supplies
        self.tier = tier

        self.state = JourneyState.PLANNING
        self.current_segment_idx = 0
        self.days_elapsed = 0
        self.total_days = sum(s.days for s in segments)
        self.roles: Dict[TravelRole, RoleAssignment] = {}

        # Track outcomes for recap
        self.segment_history: List[List[EventOutcome]] = []
        self.camp_history: List[CampResult] = []

    # ── Role Assignment ─────────────────────────────────────────────────

    def assign_role(self, role: TravelRole, character_name: str, stat_value: int):
        """Assign a character to a travel role."""
        self.roles[role] = RoleAssignment(role, character_name, stat_value)

    def get_role_stat(self, role: TravelRole) -> int:
        """Get the stat value for a role, or 0 if unassigned."""
        assignment = self.roles.get(role)
        return assignment.stat_value if assignment else 0

    def get_role_character(self, role: TravelRole) -> str:
        """Get the character name for a role, or 'No one' if unassigned."""
        assignment = self.roles.get(role)
        return assignment.character_name if assignment else "No one"

    # ── Segment Resolution ──────────────────────────────────────────────

    def resolve_segment(self, rng: Optional[random.Random] = None) -> List[EventOutcome]:
        """Draw and resolve events for the current terrain segment.

        Returns list of EventOutcome objects.
        """
        if self.current_segment_idx >= len(self.segments):
            return []

        rng = rng or random.Random()
        segment = self.segments[self.current_segment_idx]
        self.state = JourneyState.TRAVELING

        # Load terrain events
        pool = load_terrain_events(segment.terrain_type, self.tier)
        if not pool:
            # No events configured — uneventful segment
            self.segment_history.append([])
            return []

        # Draw events (without replacement if possible)
        count = min(segment.event_count, len(pool))
        drawn = rng.sample(pool, count) if count <= len(pool) else pool[:count]

        outcomes = []
        for event_data in drawn:
            event = JourneyEvent.from_dict(event_data)
            outcome = self._resolve_event(event, rng)
            outcomes.append(outcome)

        self.segment_history.append(outcomes)
        return outcomes

    def _resolve_event(self, event: JourneyEvent, rng: random.Random) -> EventOutcome:
        """Resolve a single journey event with a 2d6 + stat roll."""
        role_key = event.target_role.lower()
        try:
            role = TravelRole(role_key)
        except ValueError:
            role = TravelRole.GUIDE  # default

        stat = self.get_role_stat(role)
        roll = rng.randint(1, 6) + rng.randint(1, 6) + stat
        success = roll >= event.dc

        if success:
            text = event.success_text or "Success."
            reward = dict(event.success_reward)
            cost = {}
        else:
            text = event.failure_text or "Failure."
            reward = {}
            cost = dict(event.failure_cost)

        combat = event.event_type == "combat" and not success

        return EventOutcome(
            event=event, roll=roll, stat_value=stat,
            success=success, text=text, reward=reward,
            cost=cost, combat_triggered=combat,
        )

    # ── Camp Phase ──────────────────────────────────────────────────────

    def camp_phase(self, rng: Optional[random.Random] = None) -> CampResult:
        """Resolve camp between segments: rations, role checks, events."""
        rng = rng or random.Random()
        self.state = JourneyState.CAMPING

        if self.current_segment_idx >= len(self.segments):
            return CampResult()

        segment = self.segments[self.current_segment_idx]
        result = CampResult()

        # Rations consumed: party_size per day of segment
        base_rations = self.party_size * segment.days
        result.rations_consumed = base_rations

        # Forager check — success reduces ration cost
        forager_stat = self.get_role_stat(TravelRole.FORAGER)
        forager_roll = rng.randint(1, 6) + rng.randint(1, 6) + forager_stat
        forager_dc = 10
        forager_success = forager_roll >= forager_dc
        forager_name = self.get_role_character(TravelRole.FORAGER)

        if forager_success:
            bonus = max(1, self.party_size // 2)
            result.bonus_rations = bonus
            result.rations_consumed = max(0, base_rations - bonus)
            result.role_outcomes["forager"] = {
                "character": forager_name, "roll": forager_roll,
                "dc": forager_dc, "success": True,
                "text": f"Found food! Saved {bonus} rations.",
            }
        else:
            result.role_outcomes["forager"] = {
                "character": forager_name, "roll": forager_roll,
                "dc": forager_dc, "success": False,
                "text": "No game found. Full rations consumed.",
            }

        # Guard check — failure means night raid
        guard_stat = self.get_role_stat(TravelRole.GUARD)
        guard_roll = rng.randint(1, 6) + rng.randint(1, 6) + guard_stat
        guard_dc = 10
        guard_success = guard_roll >= guard_dc
        guard_name = self.get_role_character(TravelRole.GUARD)

        if guard_success:
            result.role_outcomes["guard"] = {
                "character": guard_name, "roll": guard_roll,
                "dc": guard_dc, "success": True,
                "text": "Peaceful night. No disturbances.",
            }
        else:
            result.night_raid = True
            result.role_outcomes["guard"] = {
                "character": guard_name, "roll": guard_roll,
                "dc": guard_dc, "success": False,
                "text": "Night raid! The camp is attacked.",
            }

        # Guide check — failure means lost, +1 day
        guide_stat = self.get_role_stat(TravelRole.GUIDE)
        guide_roll = rng.randint(1, 6) + rng.randint(1, 6) + guide_stat
        guide_dc = 10
        guide_success = guide_roll >= guide_dc
        guide_name = self.get_role_character(TravelRole.GUIDE)

        if guide_success:
            result.role_outcomes["guide"] = {
                "character": guide_name, "roll": guide_roll,
                "dc": guide_dc, "success": True,
                "text": "On course. Good progress.",
            }
        else:
            result.lost = True
            self.days_elapsed += 1  # Extra day from getting lost
            result.role_outcomes["guide"] = {
                "character": guide_name, "roll": guide_roll,
                "dc": guide_dc, "success": False,
                "text": "Lost! Wasted a day finding the trail. (+1 day)",
            }

        # Apply ration consumption
        self.supplies = max(0, self.supplies - result.rations_consumed)
        result.rations_remaining = self.supplies

        # Starvation penalty
        if self.supplies <= 0 and result.rations_consumed > 0:
            for name in [self.get_role_character(r) for r in TravelRole]:
                if name != "No one":
                    result.hp_changes[name] = result.hp_changes.get(name, 0) - 1

        # Apply costs from failed segment events
        for outcomes in self.segment_history[self.current_segment_idx:self.current_segment_idx + 1]:
            for outcome in outcomes:
                extra_days = outcome.cost.get("days", 0)
                if extra_days:
                    self.days_elapsed += int(extra_days)
                # Apply ration rewards from successful events
                extra_rations = outcome.reward.get("rations", 0)
                if extra_rations:
                    self.supplies += int(extra_rations)
                    result.rations_remaining = self.supplies

        self.camp_history.append(result)
        return result

    # ── Advancement ─────────────────────────────────────────────────────

    def advance(self) -> JourneyState:
        """Move to the next segment or arrive."""
        if self.current_segment_idx >= len(self.segments):
            self.state = JourneyState.ARRIVED
            return self.state

        segment = self.segments[self.current_segment_idx]
        self.days_elapsed += segment.days
        self.current_segment_idx += 1

        if self.current_segment_idx >= len(self.segments):
            self.state = JourneyState.ARRIVED
        else:
            self.state = JourneyState.TRAVELING

        return self.state

    # ── Queries ─────────────────────────────────────────────────────────

    @property
    def is_complete(self) -> bool:
        return self.state in (JourneyState.ARRIVED, JourneyState.FAILED)

    @property
    def current_segment(self) -> Optional[TerrainSegment]:
        if 0 <= self.current_segment_idx < len(self.segments):
            return self.segments[self.current_segment_idx]
        return None

    @property
    def progress_fraction(self) -> float:
        """0.0 to 1.0 journey progress."""
        if not self.segments:
            return 1.0
        return min(1.0, self.current_segment_idx / len(self.segments))

    def check_deadline(self) -> Tuple[bool, int]:
        """Check deadline status. Returns (on_time, days_remaining)."""
        if self.deadline_days is None:
            return True, 999
        remaining = self.deadline_days - self.days_elapsed
        return remaining >= 0, remaining

    @property
    def days_remaining(self) -> int:
        """Days left to travel (estimated)."""
        remaining_segments = self.segments[self.current_segment_idx:]
        return sum(s.days for s in remaining_segments)

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "segments": [s.to_dict() for s in self.segments],
            "deadline_days": self.deadline_days,
            "party_size": self.party_size,
            "supplies": self.supplies,
            "tier": self.tier,
            "state": self.state.value,
            "current_segment_idx": self.current_segment_idx,
            "days_elapsed": self.days_elapsed,
            "roles": {r.value: a.to_dict() for r, a in self.roles.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> JourneyEngine:
        segments = [TerrainSegment.from_dict(s) for s in d["segments"]]
        engine = cls(
            origin=d["origin"],
            destination=d["destination"],
            segments=segments,
            deadline_days=d.get("deadline_days"),
            party_size=d.get("party_size", 1),
            supplies=d.get("supplies", 10),
            tier=d.get("tier", 1),
        )
        engine.state = JourneyState(d.get("state", "planning"))
        engine.current_segment_idx = d.get("current_segment_idx", 0)
        engine.days_elapsed = d.get("days_elapsed", 0)
        for role_key, assign_data in d.get("roles", {}).items():
            engine.roles[TravelRole(role_key)] = RoleAssignment.from_dict(assign_data)
        return engine


# ─── Helper: Build journey from world map data ──────────────────────────

def build_journey_from_world_map(
    world_map: dict,
    origin_id: str,
    destination_id: str,
    party_size: int = 1,
    supplies: int = 10,
    deadline_days: Optional[int] = None,
    tier: int = 1,
) -> Optional[JourneyEngine]:
    """Build a JourneyEngine from a module's world_map.json data.

    The world_map should have room nodes with optional 'terrain' and
    'travel_days' fields. Rooms are connected; we trace a path from
    origin to destination and build terrain segments.
    """
    rooms = world_map.get("rooms", {})

    # Find origin and destination room data
    origin_room = None
    dest_room = None
    for room_data in rooms.values():
        loc_id = room_data.get("location_id", "")
        if loc_id == origin_id:
            origin_room = room_data
        if loc_id == destination_id:
            dest_room = room_data

    if not origin_room or not dest_room:
        return None

    origin_name = origin_room.get("name", origin_id)
    dest_name = dest_room.get("name", destination_id)

    # Simple path: collect intermediate rooms between origin and destination
    # For MVP, just build segments from the rooms in order
    segments = []
    seen = {origin_id}
    current = origin_room

    # BFS-style traversal through connected rooms toward destination
    path = _find_path(rooms, origin_id, destination_id)
    if not path:
        # Direct journey — one segment
        terrain = dest_room.get("terrain", "road")
        days = dest_room.get("travel_days", 3)
        segments.append(TerrainSegment(
            name=f"Road to {dest_name}",
            terrain_type=terrain,
            days=days,
        ))
    else:
        for room_id in path[1:]:  # skip origin
            room = rooms.get(str(room_id), rooms.get(room_id, {}))
            terrain = room.get("terrain", "road")
            days = room.get("travel_days", 2)
            name = room.get("name", f"Leg {len(segments) + 1}")
            segments.append(TerrainSegment(
                name=name, terrain_type=terrain, days=days,
            ))

    if not segments:
        return None

    return JourneyEngine(
        origin=origin_name,
        destination=dest_name,
        segments=segments,
        deadline_days=deadline_days,
        party_size=party_size,
        supplies=supplies,
        tier=tier,
    )


def _find_path(rooms: dict, origin_id: str, dest_id: str) -> Optional[List[str]]:
    """BFS through world_map rooms to find a path."""
    from collections import deque

    # Build adjacency from room connections
    adj: Dict[str, List[str]] = {}
    for key, room in rooms.items():
        loc = room.get("location_id", key)
        connections = room.get("connections", [])
        adj.setdefault(loc, []).extend(
            rooms.get(str(c), {}).get("location_id", str(c))
            for c in connections
        )

    queue = deque([[origin_id]])
    visited = {origin_id}
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == dest_id:
            return path
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return None

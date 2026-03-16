#!/usr/bin/env python3
"""
codex/spatial/world_map.py - World Map Data Model
==================================================

Provides the data layer for overworld navigation: a graph of named locations
connected by travel routes. Supports both hand-authored worlds and factory
construction from GRAPES Geography profiles.

Designed as a lightweight data model — no rendering, no game logic. Bridges
to map_engine.py via zone IDs stored on LocationNode.

Architecture:
    LocationNode  -- a named point of interest on the world grid
    TravelRoute   -- a weighted directed edge between two locations
    WorldMap      -- the full graph; exposes traversal and merge helpers

Version: 1.0
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from codex.core.world.grapes_engine import GrapesProfile


# =============================================================================
# TERRAIN -> LOCATION TYPE MAPPING
# =============================================================================

# Maps GRAPES terrain strings to location_type for LocationNode construction.
_TERRAIN_TO_LOCATION_TYPE: Dict[str, str] = {
    "coastal":   "city",
    "urban":     "city",
    "forest":    "wilderness_poi",
    "mountain":  "dungeon_entrance",
    "plains":    "town",
    "desert":    "ruins",
    "swamp":     "ruins",
    "river":     "village",
    "tundra":    "wilderness_poi",
    "volcanic":  "dungeon_entrance",
}

# Icon characters for each location type (for ASCII world-map rendering).
_LOCATION_ICONS: Dict[str, str] = {
    "city":              "#",
    "town":              "O",
    "village":           "o",
    "ruins":             "%",
    "dungeon_entrance":  "D",
    "wilderness_poi":    "*",
    "camp":              "^",
}

# Default services by location type.
_DEFAULT_SERVICES: Dict[str, List[str]] = {
    "city":             ["tavern", "forge", "market", "temple", "library"],
    "town":             ["tavern", "forge", "market"],
    "village":          ["tavern", "market"],
    "ruins":            [],
    "dungeon_entrance": [],
    "wilderness_poi":   [],
    "camp":             ["tavern"],
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class LocationNode:
    """
    A single named location on the world map.

    Attributes:
        id:                  Unique machine-readable identifier (e.g. "waterdeep").
        display_name:        Human-readable name (e.g. "Waterdeep").
        x:                   Grid column on the world map.
        y:                   Grid row on the world map.
        location_type:       Category: city/town/village/ruins/dungeon_entrance/
                             wilderness_poi/camp.
        terrain:             Biome: coastal/forest/mountain/plains/desert/swamp/urban.
        feature:             Short descriptive phrase (e.g. "A port city carved into
                             sea-cliffs").
        zones:               List of zone IDs that can be entered from this location.
        connections:         IDs of adjacent locations reachable from here.
        icon:                Single character for ASCII world-map display.
        tier:                Difficulty tier (1-4); higher = more dangerous.
        is_starting_location: True if the party begins their adventure here.
        services:            Available services: tavern/forge/market/temple etc.
        grapes_landmark_index: Optional index into GrapesProfile.geography list
                              that was used to create this node.
    """

    id: str
    display_name: str
    x: int
    y: int
    location_type: str
    terrain: str
    feature: str
    zones: List[str]
    connections: List[str]
    icon: str
    tier: int
    is_starting_location: bool = False
    services: List[str] = field(default_factory=list)
    grapes_landmark_index: Optional[int] = None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        d: dict = {
            "id": self.id,
            "display_name": self.display_name,
            "x": self.x,
            "y": self.y,
            "location_type": self.location_type,
            "terrain": self.terrain,
            "feature": self.feature,
            "zones": list(self.zones),
            "connections": list(self.connections),
            "icon": self.icon,
            "tier": self.tier,
            "is_starting_location": self.is_starting_location,
            "services": list(self.services),
        }
        if self.grapes_landmark_index is not None:
            d["grapes_landmark_index"] = self.grapes_landmark_index
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "LocationNode":
        """Deserialize from a dictionary (backward-compatible)."""
        return cls(
            id=data["id"],
            display_name=data["display_name"],
            x=data["x"],
            y=data["y"],
            location_type=data["location_type"],
            terrain=data["terrain"],
            feature=data["feature"],
            zones=list(data.get("zones", [])),
            connections=list(data.get("connections", [])),
            icon=data.get("icon", "?"),
            tier=data.get("tier", 1),
            is_starting_location=data.get("is_starting_location", False),
            services=list(data.get("services", [])),
            grapes_landmark_index=data.get("grapes_landmark_index", None),
        )


@dataclass
class TravelRoute:
    """
    A directed travel connection between two locations.

    Routes are stored undirectionally in WorldMap (both (A->B) and (B->A)
    are represented by a single TravelRoute; callers match on either end).

    Attributes:
        from_id:      Origin location ID.
        to_id:        Destination location ID.
        travel_days:  Approximate journey time in days.
        terrain:      Travel surface: road/trail/river/mountain_pass/sea.
        danger_level: Encounter risk 0 (safe) to 4 (extremely dangerous).
        description:  Flavour text describing the route.
    """

    from_id: str
    to_id: str
    travel_days: int
    terrain: str
    danger_level: int
    description: str

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "travel_days": self.travel_days,
            "terrain": self.terrain,
            "danger_level": self.danger_level,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TravelRoute":
        """Deserialize from a dictionary."""
        return cls(
            from_id=data["from_id"],
            to_id=data["to_id"],
            travel_days=data["travel_days"],
            terrain=data.get("terrain", "road"),
            danger_level=data.get("danger_level", 1),
            description=data.get("description", ""),
        )


@dataclass
class WorldMap:
    """
    The complete overworld navigation graph.

    Attributes:
        world_id:          Machine-readable world identifier.
        display_name:      Human-readable world name.
        system_id:         Game system this world belongs to (e.g. "burnwillow").
        seed:              RNG seed used during procedural generation.
        bounds:            (width, height) in grid units.
        locations:         Dict of location_id -> LocationNode.
        routes:            List of TravelRoute edges.
        start_location_id: ID of the default starting location.
    """

    world_id: str
    display_name: str
    system_id: str
    seed: int
    bounds: Tuple[int, int]
    locations: Dict[str, LocationNode]
    routes: List[TravelRoute]
    start_location_id: str

    # ------------------------------------------------------------------
    # Graph traversal
    # ------------------------------------------------------------------

    def get_connections(self, location_id: str) -> List[LocationNode]:
        """Return all LocationNodes directly reachable from *location_id*.

        Looks up the location's ``connections`` list and resolves each ID.
        Unknown IDs are silently skipped.
        """
        node = self.locations.get(location_id)
        if node is None:
            return []
        result: List[LocationNode] = []
        for conn_id in node.connections:
            neighbour = self.locations.get(conn_id)
            if neighbour is not None:
                result.append(neighbour)
        return result

    def get_route(self, from_id: str, to_id: str) -> Optional[TravelRoute]:
        """Return the TravelRoute between two locations, or None if no route exists.

        The search is undirected — ``get_route("A", "B")`` and
        ``get_route("B", "A")`` return the same object.
        """
        for route in self.routes:
            if (route.from_id == from_id and route.to_id == to_id) or \
               (route.from_id == to_id and route.to_id == from_id):
                return route
        return None

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def merge_locations(self, other: "WorldMap") -> None:
        """Overlay all locations and routes from *other* onto this map.

        Existing locations with the same ID are overwritten.
        Duplicate routes (same from/to pair) are deduplicated — the incoming
        route wins.
        """
        # Merge locations (incoming wins on collision)
        self.locations.update(other.locations)

        # Merge routes — remove existing routes that match incoming pairs,
        # then extend with the full incoming list.
        incoming_pairs = {(r.from_id, r.to_id) for r in other.routes}
        incoming_pairs |= {(r.to_id, r.from_id) for r in other.routes}

        self.routes = [
            r for r in self.routes
            if (r.from_id, r.to_id) not in incoming_pairs
            and (r.to_id, r.from_id) not in incoming_pairs
        ]
        self.routes.extend(other.routes)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize the entire WorldMap to a JSON-compatible dictionary."""
        return {
            "world_id": self.world_id,
            "display_name": self.display_name,
            "system_id": self.system_id,
            "seed": self.seed,
            "bounds": list(self.bounds),
            "locations": {loc_id: loc.to_dict() for loc_id, loc in self.locations.items()},
            "routes": [r.to_dict() for r in self.routes],
            "start_location_id": self.start_location_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldMap":
        """Deserialize a WorldMap from a dictionary."""
        bounds_raw = data.get("bounds", [80, 40])
        bounds: Tuple[int, int] = (int(bounds_raw[0]), int(bounds_raw[1]))

        locations: Dict[str, LocationNode] = {
            loc_id: LocationNode.from_dict(loc_data)
            for loc_id, loc_data in data.get("locations", {}).items()
        }
        routes: List[TravelRoute] = [
            TravelRoute.from_dict(r) for r in data.get("routes", [])
        ]

        return cls(
            world_id=data["world_id"],
            display_name=data["display_name"],
            system_id=data.get("system_id", ""),
            seed=data.get("seed", 0),
            bounds=bounds,
            locations=locations,
            routes=routes,
            start_location_id=data.get("start_location_id", ""),
        )

    # ------------------------------------------------------------------
    # Factory: GRAPES Geography
    # ------------------------------------------------------------------

    @classmethod
    def from_grapes_geography(
        cls,
        profile: "GrapesProfile",
        world_id: str,
        system_id: str,
        seed: int,
        bounds: Tuple[int, int] = (80, 40),
        display_name: str = "",
    ) -> "WorldMap":
        """Build a WorldMap from a GRAPES GrapesProfile.

        Each ``Landmark`` in ``profile.geography`` becomes a ``LocationNode``.
        Positions are assigned via seeded scatter within *bounds*.
        Connections are determined by nearest-neighbour graph (1–3 edges per node).

        Args:
            profile:      A fully populated GrapesProfile from grapes_engine.
            world_id:     Machine-readable ID for the new world.
            system_id:    Game system identifier (e.g. "burnwillow").
            seed:         RNG seed for position scatter and connection selection.
            bounds:       (width, height) of the world grid.
            display_name: Human-readable world name (defaults to world_id).

        Returns:
            A new WorldMap with one LocationNode per landmark and a nearest-
            neighbour connection graph.
        """
        rng = random.Random(seed)
        w, h = bounds
        _name = display_name or world_id

        landmarks = profile.geography if profile.geography else []
        locations: Dict[str, LocationNode] = {}

        # ---- Scatter landmarks across the grid --------------------------------
        margin = 4  # keep nodes away from the border
        occupied: List[Tuple[int, int]] = []

        for idx, lm in enumerate(landmarks):
            # Derive a stable location ID from landmark name
            loc_id = _slugify(lm.name)
            # Resolve location type from terrain
            loc_type = _TERRAIN_TO_LOCATION_TYPE.get(lm.terrain.lower(), "wilderness_poi")
            icon = _LOCATION_ICONS.get(loc_type, "?")
            default_svc = list(_DEFAULT_SERVICES.get(loc_type, []))

            # Place the node; retry up to 30 times to avoid crowding
            x, y = _scatter_point(rng, w, h, margin, occupied, min_distance=6)
            occupied.append((x, y))

            # Tier: first landmark is tier 1, last is tier 4, interpolate
            if len(landmarks) > 1:
                tier = max(1, min(4, 1 + round(3 * idx / (len(landmarks) - 1))))
            else:
                tier = 1

            node = LocationNode(
                id=loc_id,
                display_name=lm.name,
                x=x,
                y=y,
                location_type=loc_type,
                terrain=lm.terrain.lower(),
                feature=lm.feature,
                zones=[],
                connections=[],
                icon=icon,
                tier=tier,
                is_starting_location=(idx == 0),
                services=default_svc,
                grapes_landmark_index=idx,
            )
            locations[loc_id] = node

        # ---- Nearest-neighbour connection graph --------------------------------
        loc_list = list(locations.values())
        routes: List[TravelRoute] = []
        connected_pairs: set = set()

        for node in loc_list:
            nx, ny = node.x, node.y
            others = sorted(
                [n for n in loc_list if n.id != node.id],
                key=lambda n: math.hypot(n.x - nx, n.y - ny),
            )
            target_connections = rng.randint(1, min(3, len(others)))
            added = 0
            for neighbour in others:
                if added >= target_connections:
                    break
                pair = tuple(sorted([node.id, neighbour.id]))
                if pair in connected_pairs:
                    # Already connected; still count as a connection for this node
                    if neighbour.id not in node.connections:
                        node.connections.append(neighbour.id)
                        neighbour.connections.append(node.id)
                    added += 1
                    continue

                connected_pairs.add(pair)
                node.connections.append(neighbour.id)
                neighbour.connections.append(node.id)

                dist = math.hypot(neighbour.x - nx, neighbour.y - ny)
                days = max(1, round(dist / 10))

                # Infer travel terrain from the biomes of both endpoints
                route_terrain = _infer_route_terrain(node.terrain, neighbour.terrain)
                danger = min(4, max(node.tier, neighbour.tier) - 1)

                routes.append(TravelRoute(
                    from_id=node.id,
                    to_id=neighbour.id,
                    travel_days=days,
                    terrain=route_terrain,
                    danger_level=danger,
                    description=f"The path between {node.display_name} and {neighbour.display_name}.",
                ))
                added += 1

        # ---- Determine starting location --------------------------------
        start_id = loc_list[0].id if loc_list else ""

        return cls(
            world_id=world_id,
            display_name=_name,
            system_id=system_id,
            seed=seed,
            bounds=bounds,
            locations=locations,
            routes=routes,
            start_location_id=start_id,
        )


# =============================================================================
# PRIVATE HELPERS
# =============================================================================

def _slugify(name: str) -> str:
    """Convert a display name to a lowercase underscore-separated ID."""
    slug = name.lower().strip()
    # Replace non-alphanumeric sequences with underscores
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "location"


def _scatter_point(
    rng: random.Random,
    w: int,
    h: int,
    margin: int,
    occupied: List[Tuple[int, int]],
    min_distance: int = 4,
    max_attempts: int = 50,
) -> Tuple[int, int]:
    """Find a grid position that is at least *min_distance* from all occupied points.

    Falls back to the best available position after *max_attempts*.
    """
    best_pos = (rng.randint(margin, w - margin), rng.randint(margin, h - margin))
    best_dist = 0.0

    for _ in range(max_attempts):
        x = rng.randint(margin, w - margin)
        y = rng.randint(margin, h - margin)
        if not occupied:
            return (x, y)
        min_d = min(math.hypot(x - ox, y - oy) for ox, oy in occupied)
        if min_d >= min_distance:
            return (x, y)
        if min_d > best_dist:
            best_dist = min_d
            best_pos = (x, y)

    return best_pos


def _infer_route_terrain(terrain_a: str, terrain_b: str) -> str:
    """Infer a travel surface type from the terrains of two connected locations."""
    combined = {terrain_a.lower(), terrain_b.lower()}
    if "coastal" in combined or "sea" in combined:
        return "sea"
    if "mountain" in combined:
        return "mountain_pass"
    if "river" in combined:
        return "river"
    if "forest" in combined or "swamp" in combined or "tundra" in combined:
        return "trail"
    # Default for plains/urban/desert connections
    return "road"

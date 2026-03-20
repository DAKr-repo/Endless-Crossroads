#!/usr/bin/env python3
"""
codex_map_engine.py - Universal Procedural Map Engine
======================================================

A system-agnostic dungeon generation engine using Binary Space Partitioning (BSP).
Separates geometry generation (universal) from content population (ruleset-specific).

Architecture:
  - CodexMapEngine: Generates pure geometry (rooms, corridors, connections)
  - ContentInjector: Populates rooms with game-specific content
  - RulesetAdapter: Abstract interface for ruleset-specific population logic

Design Principles:
  - Geometry is universal: BSP algorithm works for any game system
  - Content is modular: Each ruleset (Burnwillow, D&D, etc.) implements an adapter
  - Deterministic: Seed-based generation for reproducibility
  - Efficient: O(n) room generation, suitable for Pi 5 constraints

Resource Profile:
  - RAM: ~15-30MB peak during generation, ~5-10MB resident
  - CPU: ~50-100ms for BSP, ~10-50ms per room for content
  - Thermal: Negligible (short CPU burst)

Version: 1.0 (Universal Geometry Layer)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import random
import json

from codex.games.burnwillow.content import ROOM_DESCRIPTIONS, SPECIAL_ROOM_DESCRIPTIONS
from codex.games.burnwillow.atmosphere import thermal_narrative_modifier, ThermalTone


# =============================================================================
# CORE ENUMS & CONSTANTS
# =============================================================================

class RoomType(Enum):
    """Room classification for generation and content population."""
    START = "start"          # Dungeon entrance
    NORMAL = "normal"        # Standard room
    TREASURE = "treasure"    # Loot room (locked or guarded)
    BOSS = "boss"            # Major encounter
    CORRIDOR = "corridor"    # Connecting passage
    SECRET = "secret"        # Hidden room (requires special detection)
    RETURN_GATE = "return_gate"  # Extraction point back to hub
    HIDDEN_PORTAL = "hidden_portal"      # D&D 5e arcane portal (deep dungeon)
    BORDER_CROSSING = "border_crossing"  # Crown & Crew forward-infra
    EXIT = "exit"                  # Zone exit / transition point
    CHAMBER = "chamber"            # Large encounter room
    HUB = "hub"                    # Multi-path junction / service hub
    # Settlement building types
    TAVERN = "tavern"              # Inn / social hub
    FORGE = "forge"                # Crafting / repair
    MARKET = "market"              # Buy / sell
    TEMPLE = "temple"              # Healing / blessings
    BARRACKS = "barracks"          # Quest board / bounties
    TOWN_GATE = "town_gate"        # Exit to dungeon / wilderness
    TOWN_SQUARE = "town_square"    # Central hub (start room)
    LIBRARY = "library"            # Lore / Mimir's Vault access
    RESIDENCE = "residence"        # NPC homes


class Direction(Enum):
    """Cardinal directions for room connections."""
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)

    @property
    def delta(self) -> Tuple[int, int]:
        """Get (dx, dy) offset for this direction."""
        return self.value


class GenerationMode(Enum):
    """Map topology variant."""
    DUNGEON = "dungeon"        # Existing BSP rooms + corridors
    WILDERNESS = "wilderness"  # Cellular automata open areas
    VERTICAL = "vertical"      # Linear ascending layout (tower/ship)
    SETTLEMENT = "settlement"  # Towns, villages, camps


# =============================================================================
# DATA STRUCTURES — GEOMETRY LAYER
# =============================================================================

@dataclass
class RoomNode:
    """
    A single room in the procedural dungeon graph.

    This is the universal geometry representation. It contains NO game-specific
    content — only spatial data and connectivity.

    Attributes:
        id: Unique room identifier (integer)
        x: X-coordinate in grid space
        y: Y-coordinate in grid space
        width: Room width in grid units
        height: Room height in grid units
        room_type: Classification of room (affects content population)
        connections: List of room IDs this room connects to
        tier: Difficulty tier (1-4, based on distance from start)
        is_locked: Whether this room requires a key or lockpicking
        is_secret: Whether this room requires special detection
    """
    id: int
    x: int
    y: int
    width: int
    height: int
    room_type: RoomType
    connections: List[int] = field(default_factory=list)
    tier: int = 1
    is_locked: bool = False
    is_secret: bool = False
    content_hints: Optional[dict] = None

    def center(self) -> Tuple[int, int]:
        """Get the center point of this room."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def contains_point(self, px: int, py: int) -> bool:
        """Check if a point is inside this room."""
        return (self.x <= px < self.x + self.width and
                self.y <= py < self.y + self.height)

    def overlaps(self, other: "RoomNode") -> bool:
        """Check if this room overlaps with another."""
        return not (self.x + self.width <= other.x or
                    other.x + other.width <= self.x or
                    self.y + self.height <= other.y or
                    other.y + other.height <= self.y)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        d = {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "room_type": self.room_type.value,
            "connections": self.connections,
            "tier": self.tier,
            "is_locked": self.is_locked,
            "is_secret": self.is_secret,
        }
        if self.content_hints is not None:
            d["content_hints"] = self.content_hints
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RoomNode":
        """Deserialize from dict."""
        return cls(
            id=data["id"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            room_type=RoomType(data["room_type"]),
            connections=data.get("connections", []),
            tier=data.get("tier", 1),
            is_locked=data.get("is_locked", False),
            is_secret=data.get("is_secret", False),
            content_hints=data.get("content_hints", None),
        )


@dataclass
class DungeonGraph:
    """
    The complete dungeon map as a graph of connected rooms.

    This is the output of the CodexMapEngine. It contains ONLY geometry —
    no enemies, loot, or game-specific content.

    Attributes:
        seed: Random seed used for generation (for reproducibility)
        width: Total dungeon width in grid units
        height: Total dungeon height in grid units
        rooms: Dictionary of room_id -> RoomNode
        start_room_id: ID of the entrance room
    """
    seed: int
    width: int
    height: int
    rooms: Dict[int, RoomNode] = field(default_factory=dict)
    start_room_id: int = 0
    metadata: Optional[dict] = None

    def get_room(self, room_id: int) -> Optional[RoomNode]:
        """Get a room by ID."""
        return self.rooms.get(room_id)

    def get_connected_rooms(self, room_id: int) -> List[RoomNode]:
        """Get all rooms connected to a given room."""
        room = self.get_room(room_id)
        if not room:
            return []
        return [self.rooms[conn_id] for conn_id in room.connections if conn_id in self.rooms]

    def to_dict(self) -> dict:
        """Serialize to JSON."""
        d = {
            "seed": self.seed,
            "width": self.width,
            "height": self.height,
            "rooms": {room_id: room.to_dict() for room_id, room in self.rooms.items()},
            "start_room_id": self.start_room_id,
        }
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "DungeonGraph":
        """Deserialize from JSON."""
        graph = cls(
            seed=data["seed"],
            width=data["width"],
            height=data["height"],
            start_room_id=data["start_room_id"],
            metadata=data.get("metadata", None),
        )
        graph.rooms = {
            int(room_id): RoomNode.from_dict(room_data)
            for room_id, room_data in data["rooms"].items()
        }
        return graph


# =============================================================================
# BSP MAP GENERATOR — GEOMETRY ENGINE
# =============================================================================

@dataclass
class BSPNode:
    """
    Internal node for Binary Space Partitioning tree.

    The BSP algorithm recursively subdivides space into smaller regions,
    then places rooms in leaf nodes. This creates organic dungeon layouts
    with natural corridors.

    Not exposed outside the generator — only RoomNodes are public.
    """
    x: int
    y: int
    width: int
    height: int
    left: Optional["BSPNode"] = None
    right: Optional["BSPNode"] = None
    room: Optional[RoomNode] = None

    def is_leaf(self) -> bool:
        """Check if this is a leaf node (has a room)."""
        return self.left is None and self.right is None


class CodexMapEngine:
    """
    The Universal Procedural Map Generator.

    Uses Binary Space Partitioning (BSP) to generate dungeon geometry.
    Output is a DungeonGraph containing only spatial data — no game content.

    Algorithm Overview:
        1. Start with a rectangular region (dungeon bounds)
        2. Recursively split the region (horizontally or vertically)
        3. Stop splitting when regions are too small or max depth reached
        4. Place rooms in leaf nodes
        5. Connect adjacent rooms with corridors
        6. Assign room types (start, normal, treasure, boss)
        7. Calculate difficulty tiers based on distance from start

    Parameters:
        - width: Dungeon width in grid units (default: 50)
        - height: Dungeon height in grid units (default: 50)
        - min_room_size: Minimum room dimension (default: 5)
        - max_depth: Maximum BSP tree depth (default: 4)
        - seed: Random seed for reproducibility (default: random)

    Example:
        engine = CodexMapEngine(seed=12345)
        graph = engine.generate(width=50, height=50, max_depth=4)
        # graph now contains ~8-16 rooms with corridors

    Resource Cost:
        - ~5-10MB RAM for 50x50 dungeon
        - ~50-100ms CPU time on Pi 5
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the map engine.

        Args:
            seed: Random seed for deterministic generation. If None, uses system time.
        """
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.rng = random.Random(self.seed)
        self._next_room_id = 0

    def generate(
        self,
        width: int = 50,
        height: int = 50,
        min_room_size: int = 5,
        max_depth: int = 4,
        system_id: str = "burnwillow",
    ) -> DungeonGraph:
        """
        Generate a procedural dungeon graph.

        Args:
            width: Dungeon width in grid units
            height: Dungeon height in grid units
            min_room_size: Minimum room dimension (prevents tiny rooms)
            max_depth: BSP recursion depth (controls room count: ~2^depth rooms)

        Returns:
            DungeonGraph with connected rooms (geometry only, no content)
        """
        # Reset state
        self._next_room_id = 0
        self.rng = random.Random(self.seed)

        # Build BSP tree
        root = BSPNode(x=0, y=0, width=width, height=height)
        self._split_node(root, max_depth, min_room_size)

        # Create rooms in leaf nodes
        leaf_nodes = self._get_leaf_nodes(root)
        rooms: Dict[int, RoomNode] = {}

        for node in leaf_nodes:
            room = self._create_room_in_node(node)
            rooms[room.id] = room
            node.room = room

        # Connect adjacent rooms
        self._connect_rooms(root, rooms)

        # Assign room types
        start_room = self._assign_room_types(rooms, system_id=system_id)

        # Calculate difficulty tiers (distance from start)
        self._assign_tiers(rooms, start_room.id)

        # Build and return graph
        graph = DungeonGraph(
            seed=self.seed,
            width=width,
            height=height,
            rooms=rooms,
            start_room_id=start_room.id
        )

        return graph

    # ─────────────────────────────────────────────────────────────────────
    # BSP TREE CONSTRUCTION
    # ─────────────────────────────────────────────────────────────────────

    def _split_node(self, node: BSPNode, depth: int, min_size: int):
        """
        Recursively split a BSP node.

        Args:
            node: Node to split
            depth: Remaining recursion depth
            min_size: Minimum dimension for a split
        """
        if depth == 0:
            return  # Max depth reached

        # Decide split direction (prefer splitting longer dimension)
        can_split_h = node.width >= min_size * 2
        can_split_v = node.height >= min_size * 2

        if not (can_split_h or can_split_v):
            return  # Node too small to split

        # Choose split direction (weighted by dimension)
        if can_split_h and can_split_v:
            split_horizontally = self.rng.random() < (node.height / (node.width + node.height))
        elif can_split_h:
            split_horizontally = False
        else:
            split_horizontally = True

        # Perform split
        if split_horizontally:
            # Split along Y-axis
            split_y = self.rng.randint(min_size, node.height - min_size)
            node.left = BSPNode(node.x, node.y, node.width, split_y)
            node.right = BSPNode(node.x, node.y + split_y, node.width, node.height - split_y)
        else:
            # Split along X-axis
            split_x = self.rng.randint(min_size, node.width - min_size)
            node.left = BSPNode(node.x, node.y, split_x, node.height)
            node.right = BSPNode(node.x + split_x, node.y, node.width - split_x, node.height)

        # Recurse
        self._split_node(node.left, depth - 1, min_size)
        self._split_node(node.right, depth - 1, min_size)

    def _get_leaf_nodes(self, node: BSPNode) -> List[BSPNode]:
        """Get all leaf nodes (nodes that will contain rooms)."""
        if node.is_leaf():
            return [node]
        leaves = []
        if node.left:
            leaves.extend(self._get_leaf_nodes(node.left))
        if node.right:
            leaves.extend(self._get_leaf_nodes(node.right))
        return leaves

    def _create_room_in_node(self, node: BSPNode) -> RoomNode:
        """
        Create a room inside a BSP node.

        Room is slightly smaller than node bounds to create natural spacing.
        """
        # Room is 60-90% of node size (random variation)
        room_w = self.rng.randint(max(3, node.width // 2), max(4, node.width - 2))
        room_h = self.rng.randint(max(3, node.height // 2), max(4, node.height - 2))

        # Center room in node (with random offset)
        room_x = node.x + self.rng.randint(1, max(1, node.width - room_w - 1))
        room_y = node.y + self.rng.randint(1, max(1, node.height - room_h - 1))

        room = RoomNode(
            id=self._next_room_id,
            x=room_x,
            y=room_y,
            width=room_w,
            height=room_h,
            room_type=RoomType.NORMAL  # Will be assigned later
        )

        self._next_room_id += 1
        return room

    # ─────────────────────────────────────────────────────────────────────
    # ROOM CONNECTION
    # ─────────────────────────────────────────────────────────────────────

    def _connect_rooms(self, node: BSPNode, rooms: Dict[int, RoomNode]):
        """
        Connect rooms by traversing BSP tree.

        Sibling leaf nodes are connected via corridors.
        """
        if node.is_leaf():
            return

        # Recurse on children first
        if node.left:
            self._connect_rooms(node.left, rooms)
        if node.right:
            self._connect_rooms(node.right, rooms)

        # Connect rooms in left and right subtrees
        if node.left and node.right:
            left_rooms = self._get_rooms_in_subtree(node.left)
            right_rooms = self._get_rooms_in_subtree(node.right)

            if left_rooms and right_rooms:
                # Connect closest pair
                room_a = self.rng.choice(left_rooms)
                room_b = self.rng.choice(right_rooms)

                room_a.connections.append(room_b.id)
                room_b.connections.append(room_a.id)

    def _get_rooms_in_subtree(self, node: BSPNode) -> List[RoomNode]:
        """Get all rooms in a subtree."""
        if node.is_leaf():
            return [node.room] if node.room else []

        rooms = []
        if node.left:
            rooms.extend(self._get_rooms_in_subtree(node.left))
        if node.right:
            rooms.extend(self._get_rooms_in_subtree(node.right))
        return rooms

    # ─────────────────────────────────────────────────────────────────────
    # ROOM TYPE ASSIGNMENT
    # ─────────────────────────────────────────────────────────────────────

    def _assign_room_types(self, rooms: Dict[int, RoomNode],
                           system_id: str = "burnwillow") -> RoomNode:
        """
        Assign special room types (start, treasure, boss, exit points).

        Exit-point assignment is system-dispatched:
          - burnwillow: RETURN_GATE (25-50% BFS distance)
          - dnd5e: HIDDEN_PORTAL (10% chance, deep rooms >= 50%)
          - crown_and_crew: BORDER_CROSSING (deep room >= 75%)
          - default (stc, etc.): no special exit point

        Returns the start room.
        """
        room_list = list(rooms.values())

        # Pick start room (random)
        start_room = self.rng.choice(room_list)
        start_room.room_type = RoomType.START

        # Pick boss room (farthest from start)
        distances = self._calculate_distances(rooms, start_room.id)
        boss_room = max(room_list, key=lambda r: distances.get(r.id, 0))
        boss_room.room_type = RoomType.BOSS

        # Pick treasure rooms (30% of non-special rooms)
        normal_rooms = [r for r in room_list if r.room_type == RoomType.NORMAL]
        treasure_count = max(1, len(normal_rooms) // 3)
        treasure_rooms = self.rng.sample(normal_rooms, min(treasure_count, len(normal_rooms)))

        for room in treasure_rooms:
            room.room_type = RoomType.TREASURE
            room.is_locked = self.rng.random() < 0.6  # 60% of treasure rooms are locked

        # Pick secret rooms (10% chance per room)
        for room in normal_rooms:
            if room not in treasure_rooms and self.rng.random() < 0.1:
                room.room_type = RoomType.SECRET
                room.is_secret = True

        # System-dispatched exit-point assignment
        remaining = [r for r in room_list if r.room_type == RoomType.NORMAL]

        if system_id == "burnwillow":
            # Return Gate: 1 per dungeon, 25-50% BFS distance
            if remaining and distances:
                max_dist = max(distances.values()) or 1
                candidates = [r for r in remaining
                              if 0.25 <= distances.get(r.id, 0) / max_dist <= 0.50]
                if not candidates:
                    candidates = remaining[:1]  # Fallback: first available
                gate = self.rng.choice(candidates)
                gate.room_type = RoomType.RETURN_GATE

        elif system_id == "dnd5e":
            # Hidden Portal: 10% chance, only deep rooms (distance >= 50%)
            if remaining and distances:
                max_dist = max(distances.values()) or 1
                for r in remaining:
                    if distances.get(r.id, 0) / max_dist >= 0.50 and self.rng.random() < 0.10:
                        r.room_type = RoomType.HIDDEN_PORTAL
                        break  # At most one

        elif system_id == "crown_and_crew":
            # Border Crossing: forward-infra, deep room (>= 75% distance)
            if remaining and distances:
                max_dist = max(distances.values()) or 1
                deep = [r for r in remaining if distances.get(r.id, 0) / max_dist >= 0.75]
                if deep:
                    self.rng.choice(deep).room_type = RoomType.BORDER_CROSSING

        # Default (stc, cosmere, unknown): no special exit point

        return start_room

    def _assign_tiers(self, rooms: Dict[int, RoomNode], start_id: int):
        """
        Assign difficulty tiers based on distance from start.

        Tiers: 1 (near start) to 4 (deep dungeon).
        """
        distances = self._calculate_distances(rooms, start_id)
        max_dist = max(distances.values()) if distances else 1

        for room in rooms.values():
            dist = distances.get(room.id, 0)
            # Map distance to tier (1-4)
            normalized = dist / max(1, max_dist)
            room.tier = min(4, int(normalized * 4) + 1)

    def _calculate_distances(self, rooms: Dict[int, RoomNode], start_id: int) -> Dict[int, int]:
        """
        Calculate shortest path distance from start to all rooms (BFS).

        Returns dict of room_id -> distance.
        """
        distances = {start_id: 0}
        queue = [start_id]
        visited = {start_id}

        while queue:
            current_id = queue.pop(0)
            current_dist = distances[current_id]

            room = rooms[current_id]
            for neighbor_id in room.connections:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    distances[neighbor_id] = current_dist + 1
                    queue.append(neighbor_id)

        return distances

    # ─────────────────────────────────────────────────────────────────────
    # ALTERNATE TOPOLOGY GENERATORS
    # ─────────────────────────────────────────────────────────────────────

    # Alias: existing generate() is the dungeon generator
    generate_dungeon = generate

    def generate_wilderness(
        self,
        width: int = 60,
        height: int = 60,
        room_count: int = 10,
        min_room_size: int = 4,
        max_room_size: int = 10,
        system_id: str = "burnwillow",
    ) -> DungeonGraph:
        """Generate a wilderness-style open map using cellular automata placement.

        Instead of BSP subdivision, rooms are scattered randomly and connected
        by proximity (nearest-neighbour graph).  This produces open, organic
        layouts suitable for overworld or forest areas.

        Args:
            width: Map width in grid units.
            height: Map height in grid units.
            room_count: Target number of rooms (clearings / camps / ruins).
            min_room_size: Minimum room dimension.
            max_room_size: Maximum room dimension.

        Returns:
            DungeonGraph with connected rooms.
        """
        self._next_room_id = 0
        self.rng = random.Random(self.seed)

        rooms: Dict[int, RoomNode] = {}
        attempts = 0
        max_attempts = room_count * 20

        while len(rooms) < room_count and attempts < max_attempts:
            attempts += 1
            rw = self.rng.randint(min_room_size, max_room_size)
            rh = self.rng.randint(min_room_size, max_room_size)
            rx = self.rng.randint(1, width - rw - 1)
            ry = self.rng.randint(1, height - rh - 1)

            candidate = RoomNode(
                id=self._next_room_id, x=rx, y=ry,
                width=rw, height=rh, room_type=RoomType.NORMAL,
            )

            # Reject overlapping rooms
            if any(candidate.overlaps(r) for r in rooms.values()):
                continue

            rooms[candidate.id] = candidate
            self._next_room_id += 1

        # Connect via nearest-neighbour: each room connects to 1-3 closest
        room_list = list(rooms.values())
        for room in room_list:
            cx, cy = room.center()
            others = sorted(
                [r for r in room_list if r.id != room.id],
                key=lambda r: abs(r.center()[0] - cx) + abs(r.center()[1] - cy),
            )
            for neighbour in others[:self.rng.randint(1, 3)]:
                if neighbour.id not in room.connections:
                    room.connections.append(neighbour.id)
                    neighbour.connections.append(room.id)

        start_room = self._assign_room_types(rooms, system_id=system_id)
        self._assign_tiers(rooms, start_room.id)

        return DungeonGraph(
            seed=self.seed, width=width, height=height,
            rooms=rooms, start_room_id=start_room.id,
        )

    def generate_vertical(
        self,
        floors: int = 6,
        rooms_per_floor: int = 2,
        floor_width: int = 30,
        floor_height: int = 8,
        system_id: str = "burnwillow",
    ) -> DungeonGraph:
        """Generate a linear ascending layout for tower/ship/vertical dungeons.

        Rooms are stacked in rows (floors).  Each floor has *rooms_per_floor*
        rooms connected horizontally.  Floors are connected by a single
        stairway link between a random room on each floor.

        Args:
            floors: Number of vertical levels.
            rooms_per_floor: Rooms per level.
            floor_width: Width allocated per floor.
            floor_height: Height allocated per floor.

        Returns:
            DungeonGraph with vertically connected rooms.
        """
        self._next_room_id = 0
        self.rng = random.Random(self.seed)

        rooms: Dict[int, RoomNode] = {}
        floor_rooms: list[list[RoomNode]] = []

        for floor_idx in range(floors):
            current_floor: list[RoomNode] = []
            y_base = floor_idx * (floor_height + 2)

            for slot in range(rooms_per_floor):
                rw = self.rng.randint(5, max(6, floor_width // rooms_per_floor - 2))
                rh = self.rng.randint(4, floor_height - 1)
                rx = slot * (floor_width // rooms_per_floor) + 1
                ry = y_base + 1

                room = RoomNode(
                    id=self._next_room_id, x=rx, y=ry,
                    width=rw, height=rh, room_type=RoomType.NORMAL,
                )
                rooms[room.id] = room
                current_floor.append(room)
                self._next_room_id += 1

            # Connect rooms on the same floor horizontally
            for i in range(len(current_floor) - 1):
                a, b = current_floor[i], current_floor[i + 1]
                a.connections.append(b.id)
                b.connections.append(a.id)

            floor_rooms.append(current_floor)

        # Connect consecutive floors via stairway
        for fi in range(len(floor_rooms) - 1):
            lower = self.rng.choice(floor_rooms[fi])
            upper = self.rng.choice(floor_rooms[fi + 1])
            lower.connections.append(upper.id)
            upper.connections.append(lower.id)

        start_room = self._assign_room_types(rooms, system_id=system_id)
        self._assign_tiers(rooms, start_room.id)

        total_w = floor_width + 4
        total_h = floors * (floor_height + 2) + 2

        return DungeonGraph(
            seed=self.seed, width=total_w, height=total_h,
            rooms=rooms, start_room_id=start_room.id,
        )

    # ─────────────────────────────────────────────────────────────────────
    # SETTLEMENT GENERATORS
    # ─────────────────────────────────────────────────────────────────────

    def load_blueprint(self, blueprint_path: str) -> DungeonGraph:
        """Load a hand-authored settlement/dungeon from a JSON blueprint.

        Blueprint format: same as DungeonGraph.to_dict() output.
        Rooms have fixed positions, connections, and types.
        No BSP — layout is exactly as authored.
        """
        with open(blueprint_path) as f:
            data = json.load(f)
        return DungeonGraph.from_dict(data)

    def generate_settlement(
        self,
        width: int = 40,
        height: int = 30,
        building_count: int = 8,
        system_id: str = "burnwillow",
    ) -> DungeonGraph:
        """Generate a procedural settlement layout.

        Uses wilderness-style scatter placement but assigns settlement
        RoomTypes instead of dungeon types. Buildings are connected
        by proximity (streets).

        For known settlements (Emberhome), prefer load_blueprint().
        """
        graph = self.generate_wilderness(
            width=width, height=height,
            room_count=building_count,
            min_room_size=4, max_room_size=8,
            system_id=system_id,
        )
        self._assign_settlement_types(graph.rooms)
        for room in graph.rooms.values():
            room.tier = 0
        return graph

    def _assign_settlement_types(self, rooms: Dict[int, RoomNode]):
        """Assign settlement building types to rooms."""
        room_list = list(rooms.values())
        if not room_list:
            return

        room_list[0].room_type = RoomType.TOWN_SQUARE

        required = [
            RoomType.TAVERN, RoomType.FORGE, RoomType.MARKET,
            RoomType.TOWN_GATE, RoomType.BARRACKS,
        ]
        for i, rtype in enumerate(required):
            if i + 1 < len(room_list):
                room_list[i + 1].room_type = rtype

        optional = [RoomType.TEMPLE, RoomType.LIBRARY, RoomType.RESIDENCE]
        for i in range(len(required) + 1, len(room_list)):
            room_list[i].room_type = self.rng.choice(optional)


# =============================================================================
# CONTENT POPULATION — ADAPTER PATTERN
# =============================================================================

@dataclass
class PopulatedRoom:
    """
    A room with game-specific content.

    This is the output of a RulesetAdapter. It wraps a RoomNode and adds
    game-specific data (enemies, loot, hazards, etc.).

    The content field is intentionally untyped (Any) — each adapter defines
    its own content structure.
    """
    geometry: RoomNode
    content: Any  # Ruleset-specific content (dict, object, etc.)

    def to_dict(self) -> dict:
        """Serialize to JSON."""
        return {
            "geometry": self.geometry.to_dict(),
            "content": self.content
        }


class RulesetAdapter(ABC):
    """
    Abstract base class for ruleset-specific content population.

    Each game system (Burnwillow, D&D, etc.) implements this interface to
    inject content into rooms.

    Responsibilities:
        - Generate enemies appropriate for room tier
        - Generate loot appropriate for room type
        - Generate hazards and environmental features
        - Respect room type constraints (start, treasure, boss)

    Implementation Strategy:
        - Adapters wrap existing game engines (e.g., burnwillow_module.py)
        - Adapters use deterministic randomness (seeded from room ID)
        - Adapters return dict-based content (serializable)
    """

    @abstractmethod
    def populate_room(self, room: RoomNode) -> PopulatedRoom:
        """
        Populate a room with game-specific content.

        Args:
            room: Geometry node to populate

        Returns:
            PopulatedRoom with content field populated
        """
        pass

    @abstractmethod
    def get_enemy_pool(self, tier: int) -> List[str]:
        """
        Get list of enemy types available for a given tier.

        Args:
            tier: Difficulty tier (1-4)

        Returns:
            List of enemy type names
        """
        pass

    @abstractmethod
    def get_loot_pool(self, tier: int) -> List[str]:
        """
        Get list of loot items available for a given tier.

        Args:
            tier: Difficulty tier (1-4)

        Returns:
            List of item names
        """
        pass


class ContentInjector:
    """
    The Content Population Engine.

    Takes a DungeonGraph (geometry only) and a RulesetAdapter,
    produces a fully populated dungeon.

    Usage:
        engine = CodexMapEngine(seed=123)
        graph = engine.generate()
        adapter = BurnwillowAdapter()
        injector = ContentInjector(adapter)
        populated_rooms = injector.populate_all(graph)
    """

    def __init__(self, adapter: RulesetAdapter):
        """
        Initialize the injector.

        Args:
            adapter: Ruleset-specific content generator
        """
        self.adapter = adapter

    def populate_room(self, room: RoomNode) -> PopulatedRoom:
        """
        Populate a single room.

        Args:
            room: Geometry node

        Returns:
            PopulatedRoom with content
        """
        return self.adapter.populate_room(room)

    def populate_all(self, graph: DungeonGraph) -> Dict[int, PopulatedRoom]:
        """
        Populate all rooms in a dungeon graph.

        Args:
            graph: Dungeon geometry

        Returns:
            Dict of room_id -> PopulatedRoom
        """
        populated = {}
        for room_id, room in graph.rooms.items():
            populated[room_id] = self.populate_room(room)
        return populated


# =============================================================================
# BURNWILLOW ADAPTER — FIRST IMPLEMENTATION
# =============================================================================

class BurnwillowAdapter(RulesetAdapter):
    """
    Burnwillow-specific content population.

    Uses the Burnwillow SRD to generate enemies, loot, and hazards.

    Content Structure:
        {
            "enemies": [{"name": str, "hp": int, "defense": int, "damage": str}, ...],
            "loot": [{"name": str, "slot": str, "tier": int}, ...],
            "hazards": [{"type": str, "dc": int, "effect": str}, ...],
            "description": str
        }

    Tier Mapping:
        - Tier 1: Rust Rats, Scrap Piles, Tier I gear
        - Tier 2: Clockwork Spiders, Iron Chests, Tier II gear
        - Tier 3: Blighted Sentinels, Steel Vaults, Tier III gear
        - Tier 4: Mithral Golems, Cursed Relics, Tier IV gear
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the adapter.

        Args:
            seed: Random seed for content generation (default: random)
        """
        self.seed = seed if seed is not None else random.randint(0, 999999)

    def populate_room(self, room: RoomNode) -> PopulatedRoom:
        """Populate a Burnwillow room."""
        rng = random.Random(self.seed + room.id)  # Deterministic per-room seed

        content = {
            "enemies": [],
            "loot": [],
            "hazards": [],
            "furniture": [],
            "description": ""
        }

        # Generate content based on room type
        if room.room_type == RoomType.START:
            content["description"] = rng.choice(SPECIAL_ROOM_DESCRIPTIONS.get("start", ["The entrance looms."]))
            content["description"] = thermal_narrative_modifier(content["description"], room.tier, rng)
            # Start room has no enemies, basic loot
            if rng.random() < 0.3:
                content["loot"].append(self._generate_loot(room.tier, rng))

        elif room.room_type == RoomType.BOSS:
            content["description"] = rng.choice(SPECIAL_ROOM_DESCRIPTIONS.get("boss", ["Something stirs."]))
            content["description"] = thermal_narrative_modifier(content["description"], room.tier, rng)
            # Boss room has single tough enemy
            boss_enemy = self._generate_boss_enemy(room.tier, rng)
            content["enemies"].append(boss_enemy)
            # Boss room always has treasure
            content["loot"].extend([self._generate_loot(room.tier + 1, rng) for _ in range(2)])

        elif room.room_type == RoomType.TREASURE:
            content["description"] = rng.choice(SPECIAL_ROOM_DESCRIPTIONS.get("treasure", ["Riches await."]))
            content["description"] = thermal_narrative_modifier(content["description"], room.tier, rng)
            # Treasure room has guarded loot
            if not room.is_locked:
                # Unlocked treasure is guarded
                enemy_count = rng.randint(1, 2)
                content["enemies"].extend([self._generate_enemy(room.tier, rng) for _ in range(enemy_count)])
            # Multiple loot items
            loot_count = rng.randint(2, 4)
            content["loot"].extend([self._generate_loot(room.tier, rng) for _ in range(loot_count)])

        elif room.room_type == RoomType.SECRET:
            content["description"] = rng.choice(SPECIAL_ROOM_DESCRIPTIONS.get("secret", ["A hidden space."]))
            content["description"] = thermal_narrative_modifier(content["description"], room.tier, rng)
            # Secret room has high-value loot, sometimes a hazard
            content["loot"].extend([self._generate_loot(room.tier + 1, rng) for _ in range(2)])
            if rng.random() < 0.5:
                content["hazards"].append(self._generate_hazard(room.tier, rng))

        elif room.room_type == RoomType.RETURN_GATE:
            content["description"] = rng.choice(SPECIAL_ROOM_DESCRIPTIONS.get(
                "return_gate", ["A familiar warmth seeps through the stone."]))
            content["description"] = thermal_narrative_modifier(content["description"], 0, rng)
            # No enemies, light loot
            if rng.random() < 0.3:
                content["loot"].append(self._generate_loot(room.tier, rng))

        elif room.room_type == RoomType.HIDDEN_PORTAL:
            content["description"] = rng.choice(SPECIAL_ROOM_DESCRIPTIONS.get(
                "hidden_portal", ["Arcane energy crackles in the air."]))
            content["description"] = thermal_narrative_modifier(
                content["description"], room.tier, rng,
                tone_override=ThermalTone.ARCANE)
            # No enemies, no loot — portal room
            content["is_portal"] = True

        elif room.room_type == RoomType.BORDER_CROSSING:
            content["description"] = rng.choice(SPECIAL_ROOM_DESCRIPTIONS.get(
                "border_crossing", ["The border stretches ahead."]))
            content["description"] = thermal_narrative_modifier(
                content["description"], room.tier, rng,
                tone_override=ThermalTone.GOTHIC)
            # No enemies, no loot — crossing point

        else:  # NORMAL or CORRIDOR
            content["description"] = self._generate_description(room.tier, rng)
            content["description"] = thermal_narrative_modifier(content["description"], room.tier, rng)
            # Normal room has standard enemy/loot distribution
            enemy_count = rng.randint(0, 2) if room.room_type == RoomType.NORMAL else 0
            content["enemies"].extend([self._generate_enemy(room.tier, rng) for _ in range(enemy_count)])

            if rng.random() < 0.4:
                content["loot"].append(self._generate_loot(room.tier, rng))

            if rng.random() < 0.2:
                content["hazards"].append(self._generate_hazard(room.tier, rng))

        # Furniture for NORMAL and TREASURE rooms (30% chance)
        if room.room_type in (RoomType.NORMAL, RoomType.TREASURE) and rng.random() < 0.3:
            content["furniture"].append(self._generate_furniture(room.tier, rng))

        # Assign (x, y) coordinates relative to room bounds
        self._assign_entity_positions(room, content)

        return PopulatedRoom(geometry=room, content=content)

    def _assign_entity_positions(self, room: RoomNode, content: dict):
        """Assign x, y coordinates to enemies, loot, and furniture within the room interior."""
        inner_x0 = room.x + 1
        inner_y0 = room.y + 1
        inner_x1 = room.x + room.width - 2
        inner_y1 = room.y + room.height - 2
        cx = room.x + room.width // 2
        cy = room.y + room.height // 2

        for i, enemy in enumerate(content.get("enemies", [])):
            ex = cx + 1 + i
            ey = cy
            enemy["x"] = max(inner_x0, min(inner_x1, ex))
            enemy["y"] = max(inner_y0, min(inner_y1, ey))

        for i, item in enumerate(content.get("loot", [])):
            lx = cx - 1 - i
            ly = cy
            item["x"] = max(inner_x0, min(inner_x1, lx))
            item["y"] = max(inner_y0, min(inner_y1, ly))

        for i, obj in enumerate(content.get("furniture", [])):
            fx = cx - 1 + i
            fy = cy + 1
            obj["x"] = max(inner_x0, min(inner_x1, fx))
            obj["y"] = max(inner_y0, min(inner_y1, fy))

    # Enemy archetype classification and damage reduction by tier
    ENEMY_ARCHETYPES = {
        "Rust Rat": "beast", "Scrap Imp": "scavenger", "Oil Slick": "aetherial",
        "Clockwork Spider": "construct", "Blighted Worker": "scavenger", "Iron Hound": "construct",
        "Blighted Sentinel": "construct", "Forge Wraith": "aetherial", "Steel Serpent": "construct",
        "Mithral Golem": "construct", "Void Sentinel": "aetherial", "Burnwillow Shade": "aetherial",
    }
    DR_BY_TIER = {1: 0, 2: 1, 3: 2, 4: 3}

    def get_enemy_pool(self, tier: int) -> List[str]:
        """Get Burnwillow enemy pool for tier."""
        pools = {
            1: ["Rust Rat", "Scrap Imp", "Oil Slick"],
            2: ["Clockwork Spider", "Blighted Worker", "Iron Hound"],
            3: ["Blighted Sentinel", "Forge Wraith", "Steel Serpent"],
            4: ["Mithral Golem", "Void Sentinel", "Burnwillow Shade"]
        }
        return pools.get(tier, pools[1])

    def get_loot_pool(self, tier: int) -> List[str]:
        """Get Burnwillow loot pool for tier."""
        pools = {
            1: ["Rusted Shortsword", "Padded Jerkin", "Old Oak Wand", "Burglar's Gloves"],
            2: ["Iron Longsword", "Leather Cuirass", "Ash Wand", "Thief's Toolkit"],
            3: ["Steel Greatsword", "Chainmail Armor", "Silver Staff", "Arcane Focus"],
            4: ["Mithral Blade", "Plate Armor", "Golden Wand", "Master Lockpicks"]
        }
        return pools.get(tier, pools[1])

    # ─────────────────────────────────────────────────────────────────────
    # INTERNAL GENERATION HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _generate_enemy(self, tier: int, rng: random.Random) -> dict:
        """Generate a standard enemy."""
        pool = self.get_enemy_pool(tier)
        name = rng.choice(pool)

        # Scale stats by tier
        base_hp = 5 + (tier * 2)
        base_defense = 10 + tier
        damage_dice = f"{tier}d6"

        return {
            "name": name,
            "hp": rng.randint(base_hp, base_hp + tier * 3),
            "defense": base_defense,
            "damage": damage_dice,
            "tier": tier,
            "dr": self.DR_BY_TIER.get(tier, 0),
            "archetype": self.ENEMY_ARCHETYPES.get(name, "beast"),
        }

    def _generate_boss_enemy(self, tier: int, rng: random.Random) -> dict:
        """Generate a boss enemy (2x normal stats)."""
        pool = self.get_enemy_pool(tier)
        name = f"{rng.choice(pool)} Alpha"

        base_hp = 15 + (tier * 5)
        base_defense = 12 + tier
        damage_dice = f"{min(5, tier + 1)}d6"

        base_name = name.replace(" Alpha", "")
        return {
            "name": name,
            "hp": base_hp + rng.randint(0, tier * 5),
            "defense": base_defense,
            "damage": damage_dice,
            "tier": tier,
            "is_boss": True,
            "dr": tier + 1,
            "archetype": self.ENEMY_ARCHETYPES.get(base_name, "beast"),
        }

    def _generate_loot(self, tier: int, rng: random.Random) -> dict:
        """Generate a loot item."""
        pool = self.get_loot_pool(min(4, tier))
        name = rng.choice(pool)

        # Map to gear slots (simplified)
        slot_map = {
            "Sword": "R.Hand",
            "Blade": "R.Hand",
            "Wand": "R.Hand",
            "Staff": "R.Hand",
            "Jerkin": "Chest",
            "Armor": "Chest",
            "Cuirass": "Chest",
            "Gloves": "Arms",
            "Toolkit": "Arms",
            "Lockpicks": "Arms",
            "Focus": "Neck"
        }

        slot = "R.Hand"
        for keyword, slot_type in slot_map.items():
            if keyword in name:
                slot = slot_type
                break

        return {
            "name": name,
            "slot": slot,
            "tier": tier
        }

    def _generate_hazard(self, tier: int, rng: random.Random) -> dict:
        """Generate a room hazard."""
        hazards = [
            ("Poison Gas Trap", "Grit", "Take {tier}d6 poison damage"),
            ("Collapsing Floor", "Wits", "Fall into pit, take {tier}d6 damage"),
            ("Rusted Spikes", "Might", "Impaled, take {tier}d6 damage and bleed"),
            ("Arcane Ward", "Aether", "Drains {tier} Aether, magic fails")
        ]

        name, stat, effect = rng.choice(hazards)
        dc = 8 + (tier * 2)

        return {
            "name": name,
            "stat": stat,
            "dc": dc,
            "effect": effect.format(tier=tier)
        }

    def _generate_description(self, tier: int, rng: random.Random) -> str:
        """Generate a room description from the content pool."""
        pool = ROOM_DESCRIPTIONS.get(min(4, tier), ROOM_DESCRIPTIONS[1])
        return rng.choice(pool)

    def _generate_furniture(self, tier: int, rng: random.Random) -> dict:
        """Generate an interactive furniture/object for a room."""
        pools = {
            1: ["Rusted Chest", "Crumbling Pedestal", "Iron Lever", "Weapon Rack"],
            2: ["Clockwork Console", "Oil Barrel", "Broken Automaton", "Supply Rack"],
            3: ["Arcane Obelisk", "Crystal Forge", "Sealed Vault Door", "Armory Rack"],
            4: ["Mithral Sarcophagus", "Void Anchor", "Eternity Engine", "Trophy Chest"],
        }
        pool = pools.get(min(4, tier), pools[1])
        name = rng.choice(pool)
        # Classify container type for map rendering (WO V20.3)
        name_lower = name.lower()
        if "chest" in name_lower or "sarcophagus" in name_lower or "vault" in name_lower:
            container_type = "chest"
        elif "rack" in name_lower:
            container_type = "rack"
        else:
            container_type = "furniture"
        return {"name": name, "tier": tier, "container_type": container_type}


# =============================================================================
# SERIALIZATION & UTILITIES
# =============================================================================

def save_dungeon(graph: DungeonGraph, filepath: str):
    """
    Save a dungeon graph to JSON file.

    Args:
        graph: Dungeon to save
        filepath: Output path
    """
    with open(filepath, 'w') as f:
        json.dump(graph.to_dict(), f, indent=2)


def load_dungeon(filepath: str) -> DungeonGraph:
    """
    Load a dungeon graph from JSON file.

    Args:
        filepath: Input path

    Returns:
        Loaded DungeonGraph
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    return DungeonGraph.from_dict(data)


# =============================================================================
# STANDALONE TEST & DEMO
# =============================================================================

def run_demo():
    """Demonstrate the Universal Procedural Map Engine."""
    print("=" * 70)
    print("CODEX MAP ENGINE v1.0 - STANDALONE TEST")
    print("=" * 70)

    # Generate geometry
    print("\n[GEOMETRY GENERATION]")
    engine = CodexMapEngine(seed=42)
    graph = engine.generate(width=50, height=50, max_depth=4, min_room_size=5, system_id="burnwillow")

    print(f"Seed: {graph.seed}")
    print(f"Dungeon Size: {graph.width}x{graph.height}")
    print(f"Total Rooms: {len(graph.rooms)}")
    print(f"Start Room: {graph.start_room_id}")

    # Display room summary
    print("\n[ROOM SUMMARY]")
    for room in sorted(graph.rooms.values(), key=lambda r: r.id):
        room_type = room.room_type.value.upper()
        locked = " [LOCKED]" if room.is_locked else ""
        print(f"  Room {room.id:02d}: {room_type:10s} | Tier {room.tier} | "
              f"({room.x:2d},{room.y:2d}) {room.width}x{room.height}{locked}")

    # Populate with Burnwillow content
    print("\n[CONTENT POPULATION - BURNWILLOW]")
    adapter = BurnwillowAdapter(seed=42)
    injector = ContentInjector(adapter)
    populated = injector.populate_all(graph)

    print(f"Populated {len(populated)} rooms")

    # Display sample room content
    print("\n[SAMPLE ROOM CONTENT]")
    for room_id in [graph.start_room_id, graph.start_room_id + 1, graph.start_room_id + 2]:
        if room_id in populated:
            pop_room = populated[room_id]
            content = pop_room.content
            room = pop_room.geometry

            print(f"\n--- Room {room.id} ({room.room_type.value.upper()}, Tier {room.tier}) ---")
            print(f"Description: {content['description']}")

            if content['enemies']:
                print("Enemies:")
                for enemy in content['enemies']:
                    boss = " (BOSS)" if enemy.get('is_boss') else ""
                    print(f"  - {enemy['name']}{boss}: {enemy['hp']} HP, DEF {enemy['defense']}, DMG {enemy['damage']}")

            if content['loot']:
                print("Loot:")
                for item in content['loot']:
                    print(f"  - {item['name']} ({item['slot']}, Tier {item['tier']})")

            if content['hazards']:
                print("Hazards:")
                for hazard in content['hazards']:
                    print(f"  - {hazard['name']}: {hazard['stat']} DC {hazard['dc']} ({hazard['effect']})")

    # Save to file
    print("\n[SERIALIZATION TEST]")
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix="_test_dungeon.json", mode='w', delete=False)
    tmp.close()
    save_path = tmp.name
    save_dungeon(graph, save_path)
    print(f"Saved dungeon to: {save_path}")

    loaded_graph = load_dungeon(save_path)
    print(f"Loaded dungeon: {len(loaded_graph.rooms)} rooms, seed {loaded_graph.seed}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()

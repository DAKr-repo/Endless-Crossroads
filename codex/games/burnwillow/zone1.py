#!/usr/bin/env python3
"""
burnwillow_zone1.py - The Tangle (Zone 1) Procedural Generator
=================================================================

Biome-specific procedural generation for Zone 1: The Tangle.

LORE:
    The Tangle is the upper root system of the Burnwillow World-Tree.
    Gnarled roots form organic corridors. Sap flows like golden blood.
    The Blight—a fungal corruption—rises from below, rotting the ancient wood.

BIOME IDENTITY:
    - Organic architecture: Twisted roots, living wood, pulsing sap
    - Arborist Tech: Amber deposits, Memory Caches, hardened sap
    - Corruption: Blight patches, Rot-infested creatures, dying roots

ARCHITECTURE (The Heart):
    - Pure deterministic logic
    - NO text generation (that's the Brain's job)
    - NO I/O operations
    - Uses RulesetAdapter pattern from codex_map_engine.py

RESOURCE PROFILE:
    - RAM: ~5-10MB resident (same as base map engine)
    - CPU: ~10-20ms per room for biome tag assignment
    - Thermal: Negligible

Version: 1.0 (Tangle Biome Adapter)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random
import json

# Import base map engine components
try:
    from codex.spatial.map_engine import (
        RoomNode,
        RoomType,
        RulesetAdapter,
        PopulatedRoom,
        CodexMapEngine,
        ContentInjector,
        DungeonGraph
    )
except ImportError:
    # Define minimal stubs for standalone testing
    class RoomType(Enum):
        START = "start"
        NORMAL = "normal"
        TREASURE = "treasure"
        BOSS = "boss"
        SECRET = "secret"
        CORRIDOR = "corridor"

    @dataclass
    class RoomNode:
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


# =============================================================================
# BIOME TAG ENUMS
# =============================================================================

class BiomeTag(Enum):
    """
    Environmental features unique to The Tangle.

    These are STRUCTURAL tags (Heart logic), not descriptions (Brain logic).
    The Brain will later generate flavor text based on these tags.
    """
    ROOT_WALL = "ROOT_WALL"              # Climbable root barriers
    SAP_RIVER = "SAP_RIVER"              # Flowing Aether (heal/harm)
    AMBER_VEIN = "AMBER_VEIN"            # Harvestable resource nodes
    HOLLOW_NEST = "HOLLOW_NEST"          # Enemy spawn points
    BLIGHT_PATCH = "BLIGHT_PATCH"        # Corruption zone (damage over time)
    MEMORY_CACHE = "MEMORY_CACHE"        # Blueprint/lore storage
    VAULT_DOOR = "VAULT_DOOR"            # Sealed Amber door (special key)
    FUNGAL_GROWTH = "FUNGAL_GROWTH"      # Slows movement, obscures vision
    SAP_POOL = "SAP_POOL"                # Healing zone (consumable)
    ROTWOOD_COLUMN = "ROTWOOD_COLUMN"    # Unstable structure (hazard)


# =============================================================================
# BIOME TAG PROBABILITY TABLES
# =============================================================================

# Probability weights for tag assignment (per room)
TANGLE_BIOME_WEIGHTS: Dict[BiomeTag, float] = {
    BiomeTag.ROOT_WALL: 0.8,          # Very common (80% of rooms)
    BiomeTag.HOLLOW_NEST: 0.4,        # Common (40% of rooms)
    BiomeTag.SAP_RIVER: 0.2,          # Uncommon (20% of rooms)
    BiomeTag.FUNGAL_GROWTH: 0.2,      # Uncommon (20% of rooms)
    BiomeTag.AMBER_VEIN: 0.15,        # Rare (15% of rooms)
    BiomeTag.SAP_POOL: 0.15,          # Rare (15% of rooms)
    BiomeTag.BLIGHT_PATCH: 0.1,       # Rare (10% of rooms, dangerous)
    BiomeTag.ROTWOOD_COLUMN: 0.1,     # Rare (10% of rooms, hazard)
    BiomeTag.MEMORY_CACHE: 0.05,      # Very rare (5% of rooms)
    BiomeTag.VAULT_DOOR: 0.02,        # Legendary (2% of rooms)
}

# Boss room guaranteed tags
BOSS_GUARANTEED_TAGS = [
    BiomeTag.ROOT_WALL,
    BiomeTag.BLIGHT_PATCH,
    BiomeTag.HOLLOW_NEST
]

# Treasure room guaranteed tags
TREASURE_GUARANTEED_TAGS = [
    BiomeTag.AMBER_VEIN
]

# Start room guaranteed tags
START_GUARANTEED_TAGS = [
    BiomeTag.ROOT_WALL,
    BiomeTag.SAP_POOL
]


# =============================================================================
# ENEMY POOLS (TIER-BASED)
# =============================================================================

# The Tangle enemy catalog
TANGLE_ENEMIES = {
    1: [
        {"name": "Rot-Beetle", "hp": 5, "defense": 10, "damage": "1d6"},
        {"name": "Sap Imp", "hp": 4, "defense": 11, "damage": "1d6"},
        {"name": "Fungal Crawler", "hp": 6, "defense": 9, "damage": "1d6"}
    ],
    2: [
        {"name": "Blighted Root", "hp": 10, "defense": 11, "damage": "2d6"},
        {"name": "Amber Guardian", "hp": 12, "defense": 12, "damage": "2d6"},
        {"name": "Sap Elemental", "hp": 8, "defense": 10, "damage": "2d6"}
    ],
    3: [
        {"name": "Rot Knight", "hp": 18, "defense": 13, "damage": "3d6"},
        {"name": "Hollowborn", "hp": 15, "defense": 12, "damage": "3d6"},
        {"name": "Tangle Wyrm", "hp": 20, "defense": 14, "damage": "3d6"}
    ],
    4: [
        {"name": "Blight Lord", "hp": 30, "defense": 15, "damage": "4d6"},
        {"name": "Ancient Root", "hp": 35, "defense": 16, "damage": "4d6"},
        {"name": "Sap Colossus", "hp": 40, "defense": 14, "damage": "5d6"}
    ]
}

# Boss variants (enhanced stats)
TANGLE_BOSSES = {
    1: {"name": "Rot-Beetle Queen", "hp": 15, "defense": 12, "damage": "2d6"},
    2: {"name": "The Blighted Sentinel", "hp": 25, "defense": 14, "damage": "3d6"},
    3: {"name": "Hollowborn Elder", "hp": 40, "defense": 16, "damage": "4d6"},
    4: {"name": "Tangle Heart Corruption", "hp": 60, "defense": 18, "damage": "5d6"}
}


# =============================================================================
# LOOT POOLS (TIER-BASED)
# =============================================================================

TANGLE_LOOT = {
    1: [
        {"name": "Rootbark Shield", "slot": "L.Hand", "tier": 1, "dr": 1},
        {"name": "Sap-Soaked Club", "slot": "R.Hand", "tier": 1, "damage": "1d6"},
        {"name": "Fungal Cap Helm", "slot": "Head", "tier": 1, "dr": 1},
        {"name": "Woven Bark Armor", "slot": "Chest", "tier": 1, "dr": 1}
    ],
    2: [
        {"name": "Amber Blade", "slot": "R.Hand", "tier": 2, "damage": "2d6"},
        {"name": "Hardwood Bow", "slot": "R.Hand", "tier": 2, "damage": "2d6"},
        {"name": "Rootweave Cloak", "slot": "Shoulders", "tier": 2, "dr": 1},
        {"name": "Sap Infusion Vial", "slot": "Neck", "tier": 2, "special": "Heal 2d6 HP"}
    ],
    3: [
        {"name": "Burnwillow Greatsword", "slot": "R.Hand", "tier": 3, "damage": "3d6"},
        {"name": "Amber-Fused Plate", "slot": "Chest", "tier": 3, "dr": 3},
        {"name": "Memory Seed", "slot": "Neck", "tier": 3, "special": "Unlock blueprint"},
        {"name": "Aether-Touched Staff", "slot": "R.Hand", "tier": 3, "damage": "3d6", "stat": "Aether +1"}
    ],
    4: [
        {"name": "Tangle's Wrath", "slot": "R.Hand", "tier": 4, "damage": "4d6", "special": "Lifesteal"},
        {"name": "Living Amber Armor", "slot": "Chest", "tier": 4, "dr": 4, "special": "Regen 1 HP/turn"},
        {"name": "Arborist's Masterwork Ring", "slot": "L.Ring", "tier": 4, "stat": "Wits +2"},
        {"name": "Sap Core", "slot": "Neck", "tier": 4, "special": "Store 1 spell"}
    ]
}


# =============================================================================
# HAZARD DEFINITIONS
# =============================================================================

TANGLE_HAZARDS = [
    {
        "name": "Brittle Roots",
        "type": "trap",
        "stat": "Wits",
        "dc_formula": lambda tier: 8 + tier * 2,
        "effect_formula": lambda tier: f"Fall {tier}d6 damage"
    },
    {
        "name": "Toxic Spores",
        "type": "environmental",
        "stat": "Grit",
        "dc_formula": lambda tier: 10 + tier * 2,
        "effect_formula": lambda tier: f"{tier}d6 poison damage over time"
    },
    {
        "name": "Sap Geyser",
        "type": "trap",
        "stat": "Might",
        "dc_formula": lambda tier: 12 + tier,
        "effect_formula": lambda tier: f"{tier}d6 scalding damage, stuck for 1 turn"
    },
    {
        "name": "Blight Miasma",
        "type": "environmental",
        "stat": "Aether",
        "dc_formula": lambda tier: 10 + tier * 2,
        "effect_formula": lambda tier: f"Lose {tier} max HP until rest"
    }
]


# =============================================================================
# THE TANGLE ADAPTER (RulesetAdapter Implementation)
# =============================================================================

class TangleAdapter(RulesetAdapter):
    """
    Zone 1: The Tangle content population adapter.

    This adapter generates biome-specific content for Tangle rooms.

    ARCHITECTURE COMPLIANCE:
        - Heart logic only: No text generation
        - Deterministic: Seeded RNG per room
        - Composable: Works with any CodexMapEngine output

    Content Structure:
        {
            "biome_tags": [BiomeTag.ROOT_WALL, BiomeTag.SAP_RIVER, ...],
            "enemies": [{"name": str, "hp": int, "defense": int, "damage": str}, ...],
            "loot": [{"name": str, "slot": str, "tier": int, "special": str}, ...],
            "hazards": [{"name": str, "type": str, "stat": str, "dc": int, "effect": str}],
            "interactive": [...]  # Climbable roots, breakable amber, etc.
        }

    NOTE: The "description" field is intentionally omitted. That's the Brain's job.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the Tangle adapter.

        Args:
            seed: Random seed for deterministic generation (default: random)
        """
        self.seed = seed if seed is not None else random.randint(0, 999999)

    def populate_room(self, room: RoomNode) -> PopulatedRoom:
        """
        Populate a room with Tangle-specific content.

        Args:
            room: Geometry node from map engine

        Returns:
            PopulatedRoom with Tangle biome content
        """
        # Create room-specific RNG (deterministic)
        rng = random.Random(self.seed + room.id)

        # Initialize content structure
        content = {
            "biome_tags": [],
            "enemies": [],
            "loot": [],
            "hazards": [],
            "interactive": []
        }

        # Assign biome tags
        content["biome_tags"] = self._assign_biome_tags(room, rng)

        # Populate based on room type
        if room.room_type == RoomType.START:
            self._populate_start_room(room, content, rng)

        elif room.room_type == RoomType.BOSS:
            self._populate_boss_room(room, content, rng)

        elif room.room_type == RoomType.TREASURE:
            self._populate_treasure_room(room, content, rng)

        elif room.room_type == RoomType.SECRET:
            self._populate_secret_room(room, content, rng)

        else:  # NORMAL or CORRIDOR
            self._populate_normal_room(room, content, rng)

        # Add interactive elements based on biome tags
        self._add_interactive_elements(room, content, rng)

        return PopulatedRoom(geometry=room, content=content)

    # ─────────────────────────────────────────────────────────────────────
    # BIOME TAG ASSIGNMENT
    # ─────────────────────────────────────────────────────────────────────

    def _assign_biome_tags(self, room: RoomNode, rng: random.Random) -> List[str]:
        """
        Assign biome-specific environmental tags to a room.

        Args:
            room: Room to tag
            rng: Seeded random generator

        Returns:
            List of BiomeTag values (as strings for serialization)
        """
        tags = []

        # Guaranteed tags by room type
        if room.room_type == RoomType.START:
            tags.extend([tag.value for tag in START_GUARANTEED_TAGS])

        elif room.room_type == RoomType.BOSS:
            tags.extend([tag.value for tag in BOSS_GUARANTEED_TAGS])

        elif room.room_type == RoomType.TREASURE:
            tags.extend([tag.value for tag in TREASURE_GUARANTEED_TAGS])

        # Probabilistic tags
        for tag, weight in TANGLE_BIOME_WEIGHTS.items():
            if tag.value not in tags and rng.random() < weight:
                tags.append(tag.value)

        # Ensure at least one tag
        if not tags:
            tags.append(BiomeTag.ROOT_WALL.value)

        return tags

    # ─────────────────────────────────────────────────────────────────────
    # ROOM TYPE POPULATION METHODS
    # ─────────────────────────────────────────────────────────────────────

    def _populate_start_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate the starting room (safe zone)."""
        # Start room has no enemies
        # Provide basic loot to get started
        if rng.random() < 0.5:
            content["loot"].append(rng.choice(TANGLE_LOOT[1]))

    def _populate_boss_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate a boss encounter room."""
        # Single boss enemy
        boss_template = TANGLE_BOSSES.get(room.tier, TANGLE_BOSSES[1])
        boss = boss_template.copy()
        boss["is_boss"] = True
        content["enemies"].append(boss)

        # Boss rooms always have high-tier loot
        loot_tier = min(4, room.tier + 1)
        loot_count = rng.randint(2, 3)
        content["loot"].extend([rng.choice(TANGLE_LOOT[loot_tier]) for _ in range(loot_count)])

    def _populate_treasure_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate a treasure room (guarded or locked)."""
        # If not locked, add guardian enemies
        if not room.is_locked:
            enemy_count = rng.randint(1, 2)
            enemy_pool = TANGLE_ENEMIES.get(room.tier, TANGLE_ENEMIES[1])
            content["enemies"].extend([rng.choice(enemy_pool).copy() for _ in range(enemy_count)])

        # Multiple loot items
        loot_count = rng.randint(2, 4)
        loot_pool = TANGLE_LOOT.get(room.tier, TANGLE_LOOT[1])
        content["loot"].extend([rng.choice(loot_pool).copy() for _ in range(loot_count)])

    def _populate_secret_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate a hidden room (high value, possible hazard)."""
        # High-tier loot
        loot_tier = min(4, room.tier + 1)
        loot_pool = TANGLE_LOOT.get(loot_tier, TANGLE_LOOT[1])
        content["loot"].extend([rng.choice(loot_pool).copy() for _ in range(2)])

        # 50% chance of hazard
        if rng.random() < 0.5:
            hazard = rng.choice(TANGLE_HAZARDS)
            content["hazards"].append({
                "name": hazard["name"],
                "type": hazard["type"],
                "stat": hazard["stat"],
                "dc": hazard["dc_formula"](room.tier),
                "effect": hazard["effect_formula"](room.tier)
            })

    def _populate_normal_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate a standard room (balanced enemies/loot/hazards)."""
        # Enemy spawns (0-2 enemies)
        if room.room_type != RoomType.CORRIDOR:
            enemy_count = rng.randint(0, 2)
            enemy_pool = TANGLE_ENEMIES.get(room.tier, TANGLE_ENEMIES[1])
            content["enemies"].extend([rng.choice(enemy_pool).copy() for _ in range(enemy_count)])

        # Loot (40% chance)
        if rng.random() < 0.4:
            loot_pool = TANGLE_LOOT.get(room.tier, TANGLE_LOOT[1])
            content["loot"].append(rng.choice(loot_pool).copy())

        # Hazards (20% chance)
        if rng.random() < 0.2:
            hazard = rng.choice(TANGLE_HAZARDS)
            content["hazards"].append({
                "name": hazard["name"],
                "type": hazard["type"],
                "stat": hazard["stat"],
                "dc": hazard["dc_formula"](room.tier),
                "effect": hazard["effect_formula"](room.tier)
            })

    # ─────────────────────────────────────────────────────────────────────
    # INTERACTIVE ELEMENT GENERATION
    # ─────────────────────────────────────────────────────────────────────

    def _add_interactive_elements(self, room: RoomNode, content: dict, rng: random.Random):
        """
        Add interactive elements based on biome tags.

        Interactive elements are structural affordances (climbable, breakable, etc.)
        NOT descriptions. The Brain will generate text for these later.
        """
        tags = content["biome_tags"]

        # ROOT_WALL → Climbable surface
        if BiomeTag.ROOT_WALL.value in tags:
            content["interactive"].append({
                "type": "climbable",
                "target": "root wall",
                "stat": "Might",
                "dc": 8 + room.tier
            })

        # AMBER_VEIN → Breakable resource node
        if BiomeTag.AMBER_VEIN.value in tags:
            content["interactive"].append({
                "type": "breakable",
                "target": "amber vein",
                "stat": "Might",
                "dc": 10 + room.tier,
                "reward": f"Amber Shard (Tier {room.tier})"
            })

        # SAP_POOL → Consumable healing
        if BiomeTag.SAP_POOL.value in tags:
            content["interactive"].append({
                "type": "consumable",
                "target": "sap pool",
                "effect": f"Heal {room.tier}d6 HP (once per room)"
            })

        # MEMORY_CACHE → Loot container
        if BiomeTag.MEMORY_CACHE.value in tags:
            content["interactive"].append({
                "type": "lootable",
                "target": "memory cache",
                "requires": "Lockpick or Key",
                "reward": "Blueprint or Lore Fragment"
            })

        # VAULT_DOOR → Special unlock mechanism
        if BiomeTag.VAULT_DOOR.value in tags:
            content["interactive"].append({
                "type": "portal",
                "target": "vault door",
                "requires": "Amber Key",
                "leads_to": "Secret treasure vault"
            })

    # ─────────────────────────────────────────────────────────────────────
    # RULESETADAPTER INTERFACE METHODS
    # ─────────────────────────────────────────────────────────────────────

    def get_enemy_pool(self, tier: int) -> List[str]:
        """
        Get list of enemy names for a given tier.

        Args:
            tier: Difficulty tier (1-4)

        Returns:
            List of enemy type names
        """
        enemies = TANGLE_ENEMIES.get(tier, TANGLE_ENEMIES[1])
        return [enemy["name"] for enemy in enemies]

    def get_loot_pool(self, tier: int) -> List[str]:
        """
        Get list of loot item names for a given tier.

        Args:
            tier: Difficulty tier (1-4)

        Returns:
            List of item names
        """
        loot = TANGLE_LOOT.get(tier, TANGLE_LOOT[1])
        return [item["name"] for item in loot]


# =============================================================================
# ZONE GENERATOR — HIGH-LEVEL INTERFACE
# =============================================================================

class TangleGenerator:
    """
    High-level interface for generating a complete Tangle zone.

    This wraps CodexMapEngine + TangleAdapter for convenience.

    Usage:
        generator = TangleGenerator()
        zone = generator.generate_zone(depth=4, seed=12345)
        print(f"Generated {len(zone['rooms'])} rooms")

        for room in zone['rooms']:
            print(f"Room {room['id']}: {room['biome_tags']}")
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize the Tangle zone generator.

        Args:
            config: Optional configuration dict for zone generation parameters.
        """
        self.config = config or {}

    def generate_zone(
        self,
        depth: int = 4,
        seed: Optional[int] = None,
        width: int = 50,
        height: int = 50,
        min_room_size: int = 5
    ) -> dict:
        """
        Generate a complete Tangle zone.

        Args:
            depth: BSP depth (controls room count: ~2^depth rooms)
            seed: Random seed for reproducibility
            width: Dungeon width in grid units
            height: Dungeon height in grid units
            min_room_size: Minimum room dimension

        Returns:
            Dict containing:
                - "seed": Generation seed
                - "graph": DungeonGraph object
                - "rooms": List of room dicts with content
                - "start_room_id": Entrance room ID
                - "total_rooms": Room count
        """
        # Generate geometry
        map_engine = CodexMapEngine(seed=seed)
        graph = map_engine.generate(
            width=width,
            height=height,
            min_room_size=min_room_size,
            max_depth=depth,
            system_id="burnwillow",
        )

        # Populate with Tangle content
        adapter = TangleAdapter(seed=seed)
        injector = ContentInjector(adapter)
        populated_rooms = injector.populate_all(graph)

        # Convert to serializable format
        rooms = []
        for room_id, pop_room in populated_rooms.items():
            room_dict = {
                "id": pop_room.geometry.id,
                "type": pop_room.geometry.room_type.value,
                "tier": pop_room.geometry.tier,
                "position": (pop_room.geometry.x, pop_room.geometry.y),
                "size": (pop_room.geometry.width, pop_room.geometry.height),
                "connections": pop_room.geometry.connections,
                "is_locked": pop_room.geometry.is_locked,
                "is_secret": pop_room.geometry.is_secret,
                "biome_tags": pop_room.content["biome_tags"],
                "enemies": pop_room.content["enemies"],
                "loot": pop_room.content["loot"],
                "hazards": pop_room.content["hazards"],
                "interactive": pop_room.content["interactive"]
            }
            rooms.append(room_dict)

        return {
            "seed": graph.seed,
            "graph": graph,
            "rooms": rooms,
            "start_room_id": graph.start_room_id,
            "total_rooms": len(rooms)
        }


# =============================================================================
# STANDALONE TEST & DEMO
# =============================================================================

def run_demo():
    """Demonstrate the Tangle zone generator."""
    print("=" * 70)
    print("ZONE 1: THE TANGLE - PROCEDURAL GENERATOR TEST")
    print("=" * 70)

    # Generate a Tangle zone
    print("\n[GENERATION]")
    generator = TangleGenerator()
    zone = generator.generate_zone(depth=3, seed=999)

    print(f"Seed: {zone['seed']}")
    print(f"Total Rooms: {zone['total_rooms']}")
    print(f"Start Room: {zone['start_room_id']}")

    # Display room summaries
    print("\n[ROOM SUMMARIES]")
    for room in sorted(zone['rooms'], key=lambda r: r['id']):
        room_type = room['type'].upper()
        locked = " [LOCKED]" if room['is_locked'] else ""

        print(f"\n--- Room {room['id']:02d}: {room_type:10s} (Tier {room['tier']}){locked} ---")
        print(f"Position: {room['position']} | Size: {room['size']}")
        print(f"Connections: {room['connections']}")
        print(f"Biome Tags: {', '.join(room['biome_tags'])}")

        if room['enemies']:
            print("Enemies:")
            for enemy in room['enemies']:
                boss = " (BOSS)" if enemy.get('is_boss') else ""
                print(f"  - {enemy['name']}{boss}: {enemy['hp']} HP, DEF {enemy['defense']}, DMG {enemy['damage']}")

        if room['loot']:
            print("Loot:")
            for item in room['loot']:
                special = f" [{item.get('special', '')}]" if 'special' in item else ""
                print(f"  - {item['name']} ({item['slot']}, Tier {item['tier']}){special}")

        if room['hazards']:
            print("Hazards:")
            for hazard in room['hazards']:
                print(f"  - {hazard['name']}: {hazard['stat']} DC {hazard['dc']} ({hazard['effect']})")

        if room['interactive']:
            print("Interactive:")
            for elem in room['interactive']:
                print(f"  - {elem['type'].upper()}: {elem['target']}")

    # Statistical summary
    print("\n[STATISTICS]")
    tag_counts = {}
    for room in zone['rooms']:
        for tag in room['biome_tags']:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print("Biome Tag Distribution:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / zone['total_rooms']) * 100
        print(f"  {tag:20s}: {count:2d} rooms ({percentage:5.1f}%)")

    total_enemies = sum(len(room['enemies']) for room in zone['rooms'])
    total_loot = sum(len(room['loot']) for room in zone['rooms'])
    total_hazards = sum(len(room['hazards']) for room in zone['rooms'])

    print(f"\nTotal Enemies: {total_enemies}")
    print(f"Total Loot: {total_loot}")
    print(f"Total Hazards: {total_hazards}")

    # Save to file
    print("\n[SERIALIZATION]")
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix="_tangle_zone_test.json", mode='w', delete=False)
    zone_data = zone.copy()
    zone_data['graph'] = zone['graph'].to_dict()
    json.dump(zone_data, tmp, indent=2)
    tmp.close()
    print(f"Saved zone to: {tmp.name}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()

#!/usr/bin/env python3
"""
zone_heartwood.py - The Heartwood (Zone 6) Procedural Generator
================================================================

Biome-specific procedural generation for Zone 6: The Heartwood.

LORE:
    The Wood Behind the Wood. Architecture IS the tree — you are not moving
    through a structure, you are moving through the body of something ancient.
    Concentric growth rings form the walls, floor, and ceiling. The Arborists
    built here ten generations before the Blight existed. What remains is not
    rot-corrupted — it is the tree's own immune system treating you as an
    infection that has gone too deep.

BIOME IDENTITY:
    - Arborist construction: Carved growth rings, amber-lit tools, singing seals
    - Deep amber: Not a resource here — a material, a medium, a tomb
    - Immune response: Constructs and echoes, not Rot. Order against intrusion.
    - Living architecture: Warm wood, grain that pulses, walls that breathe

ARCHITECTURE (The Heart):
    - Pure deterministic logic
    - NO text generation (that's the Brain's job)
    - NO I/O operations
    - Uses RulesetAdapter pattern from map_engine.py

RESOURCE PROFILE:
    - RAM: ~5-10MB resident (same as base map engine)
    - CPU: ~10-20ms per room for biome tag assignment
    - Thermal: Negligible

Version: 1.0 (Heartwood Biome Adapter)
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

class HeartBiome(Enum):
    """
    Environmental features unique to The Heartwood.

    These are STRUCTURAL tags (Heart logic), not descriptions (Brain logic).
    The Brain will later generate flavor text based on these tags.
    """
    GROWTH_RING    = "GROWTH_RING"      # Concentric ring wall formations
    SAP_CHANNEL    = "SAP_CHANNEL"      # Arborist-carved sap conduits (sealed, pressurized)
    AMBER_DEPOSIT  = "AMBER_DEPOSIT"    # Thick amber masses, some with things inside
    RESIN_POCKET   = "RESIN_POCKET"     # Hollow cavity of liquid resin, harvestable
    PAINTED_MURAL  = "PAINTED_MURAL"    # Arborist painted-song panels covering walls
    SILENT_GARDEN  = "SILENT_GARDEN"    # Living wood shaped over centuries, no decay
    IMMUNE_NODE    = "IMMUNE_NODE"      # Active construct spawn point
    ARBORIST_RELIC = "ARBORIST_RELIC"   # Sealed tools, instruments, sealed containers
    CRACKED_SEAL   = "CRACKED_SEAL"     # Compromised Arborist containment (hazard)


# =============================================================================
# BIOME TAG PROBABILITY TABLES
# =============================================================================

# Probability weights for tag assignment (per room)
HEARTWOOD_BIOME_WEIGHTS: Dict[HeartBiome, float] = {
    HeartBiome.GROWTH_RING:    0.85,   # Ubiquitous (85% of rooms) — the architecture itself
    HeartBiome.AMBER_DEPOSIT:  0.45,   # Common (45%) — this deep, amber is everywhere
    HeartBiome.SAP_CHANNEL:    0.30,   # Uncommon (30%) — Arborist infrastructure
    HeartBiome.IMMUNE_NODE:    0.25,   # Uncommon (25%) — tree defenses
    HeartBiome.PAINTED_MURAL:  0.20,   # Uncommon (20%) — Arborist cultural record
    HeartBiome.SILENT_GARDEN:  0.15,   # Rare (15%) — shaped-wood sanctuaries
    HeartBiome.RESIN_POCKET:   0.12,   # Rare (12%) — valuable, fragile
    HeartBiome.ARBORIST_RELIC:0.10,   # Rare (10%) — sealed tools and instruments
    HeartBiome.CRACKED_SEAL:   0.08,   # Rare (8%) — dangerous, triggers immune response
}

# Boss room guaranteed tags
BOSS_GUARANTEED_TAGS = [
    HeartBiome.GROWTH_RING,
    HeartBiome.AMBER_DEPOSIT,
    HeartBiome.IMMUNE_NODE
]

# Treasure room guaranteed tags
TREASURE_GUARANTEED_TAGS = [
    HeartBiome.RESIN_POCKET,
    HeartBiome.ARBORIST_RELIC
]

# Start room guaranteed tags
START_GUARANTEED_TAGS = [
    HeartBiome.GROWTH_RING,
    HeartBiome.SAP_CHANNEL
]

# Secret room guaranteed tags
SECRET_GUARANTEED_TAGS = [
    HeartBiome.PAINTED_MURAL,
    HeartBiome.SILENT_GARDEN
]


# =============================================================================
# ENEMY POOLS (TIER-BASED)
# =============================================================================

HEARTWOOD_ENEMIES: Dict[int, List[dict]] = {
    1: [
        {
            "name": "Amber Shard",
            "hp": 5,
            "defense": 11,
            "damage": "1d6",
            "note": "Minor construct. Fragments on death, scattering cutting debris."
        },
        {
            "name": "Growth Ring Sentinel",
            "hp": 6,
            "defense": 10,
            "damage": "1d6",
            "note": "Patrols concentric paths. Disorienting to fight in tight rings."
        }
    ],
    2: [
        {
            "name": "Amber Echo",
            "hp": 10,
            "defense": 15,
            "damage": "2d6",
            "note": "Phase-shifts through amber walls. Briefly incorporeal between attacks."
        },
        {
            "name": "Arborist Automaton",
            "hp": 12,
            "defense": 13,
            "damage": "2d6",
            "note": "Ancient construct. Still follows original patrol instructions to the letter."
        }
    ],
    3: [
        {
            "name": "Immune Response",
            "hp": 18,
            "defense": 14,
            "damage": "3d6",
            "note": "Tree antibody. Spawns from IMMUNE_NODE walls. Cannot be reasoned with."
        },
        {
            "name": "Elder Amber Echo",
            "hp": 15,
            "defense": 16,
            "damage": "3d6",
            "note": "Older phase-shift. Lingers half-inside walls. Emits subsonic hum."
        }
    ],
    4: [
        {
            "name": "Heartwood Guardian",
            "hp": 25,
            "defense": 17,
            "damage": "4d6",
            "note": "Ancient construct. DR 2. The tree's own fist. Moves like it has always been here."
        },
        {
            "name": "Sealed Singer",
            "hp": 20,
            "defense": 16,
            "damage": "4d6",
            "note": "Amber-trapped Arborist. Still alive inside. Still singing. The song is a weapon now."
        }
    ]
}


# =============================================================================
# BOSS POOLS (TIER-BASED)
# =============================================================================

HEARTWOOD_BOSSES: Dict[int, dict] = {
    1: {
        "name": "The First Seal",
        "hp": 15,
        "defense": 13,
        "damage": "2d6",
        "note": "A door that learned to fight. Amber panels, ring-carved, slammed shut ten generations ago."
    },
    2: {
        "name": "Amber Warden",
        "hp": 30,
        "defense": 15,
        "damage": "3d6",
        "note": "Construct-guardian of a major ring boundary. Shoulders wide as the corridor."
    },
    3: {
        "name": "The Immune Heart",
        "hp": 45,
        "defense": 17,
        "damage": "4d6",
        "note": "A concentrated knot of immune response. Drains warmth from the air. The grain pulls toward it."
    },
    4: {
        "name": "Ancient Arborist",
        "hp": 60,
        "defense": 18,
        "damage": "5d6",
        "note": "Half-Hollowed, still singing. Trapped here since the First Seal. Knows every room in this body."
    }
}


# =============================================================================
# LOOT POOLS (TIER-BASED)
# =============================================================================

HEARTWOOD_LOOT: Dict[int, List[dict]] = {
    1: [
        {"name": "Amber Chisel", "slot": "R.Hand", "tier": 1, "damage": "1d6",
         "note": "Arborist tool repurposed as a weapon. Still holds an edge."},
        {"name": "Growth Ring Brace", "slot": "L.Hand", "tier": 1, "dr": 1,
         "note": "Curved wood from a concentric wall. Shaped to the hand."},
        {"name": "Sealed Resin Vial", "slot": "Neck", "tier": 1, "special": "Heal 1d6 HP",
         "note": "Arborist preservation fluid. Still viable."},
        {"name": "Grain-Read Gloves", "slot": "Hands", "tier": 1, "special": "Wits +1 on Heartwood checks",
         "note": "Thin leather. Sensitized fingertips. The grain tells you things."}
    ],
    2: [
        {"name": "Arborist Shortsword", "slot": "R.Hand", "tier": 2, "damage": "2d6",
         "note": "Amber-core blade. Warm to the touch. Does not rust."},
        {"name": "Sap-Sealed Plate", "slot": "Chest", "tier": 2, "dr": 2,
         "note": "Arborist breastplate. The sap hardened around it like a mold."},
        {"name": "Echo Lens", "slot": "Head", "tier": 2, "special": "See Amber Echoes while phased",
         "note": "Two polished amber discs in a wire frame. The world looks sepia through them."},
        {"name": "Resin Memory Shard", "slot": "Neck", "tier": 2, "special": "Unlock 1 Arborist blueprint",
         "note": "A memory crystallized in amber. Someone's hands. A tool being made."}
    ],
    3: [
        {"name": "Singing Blade", "slot": "R.Hand", "tier": 3, "damage": "3d6",
         "special": "Resonates against immune constructs (+1d6)",
         "note": "Forged from an Arborist instrument. Still holds the note."},
        {"name": "Amber-Fused Gauntlets", "slot": "Hands", "tier": 3, "dr": 2,
         "special": "DR applies to construct damage",
         "note": "The amber grew around them. Warm and permanent."},
        {"name": "Growth Ring Mantle", "slot": "Shoulders", "tier": 3, "dr": 2,
         "special": "Resist Immune Response slow",
         "note": "Carved from a ring section. Smells like old rain on bark."},
        {"name": "Arborist's Compass", "slot": "Neck", "tier": 3,
         "special": "Reveals IMMUNE_NODEs on minimap",
         "note": "A sealed dial. Always points toward the oldest growth."}
    ],
    4: [
        {"name": "Heartwood Spear", "slot": "R.Hand", "tier": 4, "damage": "4d6",
         "special": "Ignore construct DR",
         "note": "Cut from the innermost ring. The wood is red and dense as iron."},
        {"name": "Ancient Amber Armor", "slot": "Chest", "tier": 4, "dr": 4,
         "special": "Regen 1 HP per room (tree warmth)",
         "note": "The amber did not coat this armor. The armor grew inside the amber."},
        {"name": "Sealed Singer's Throat", "slot": "Neck", "tier": 4,
         "special": "Cast 1 Arborist Song per encounter",
         "note": "A fragment of crystallized voice. Do not press it to your ear in quiet rooms."},
        {"name": "Arborist Master Key", "slot": "L.Hand", "tier": 4,
         "special": "Open any CRACKED_SEAL without triggering immune response",
         "note": "Amber rod. The grain runs the same direction as all the seals here."}
    ]
}


# =============================================================================
# HAZARD DEFINITIONS
# =============================================================================

HEARTWOOD_HAZARDS = [
    {
        "name": "Cracked Seal Burst",
        "type": "environmental",
        "stat": "Grit",
        "dc_formula": lambda tier: 10 + tier * 2,
        "effect_formula": lambda tier: f"Pressurized resin spray, {tier}d6 damage + blinded 1 turn"
    },
    {
        "name": "Immune Pulse",
        "type": "trap",
        "stat": "Wits",
        "dc_formula": lambda tier: 9 + tier * 2,
        "effect_formula": lambda tier: f"Wall-born shock, {tier}d6 damage + stunned 1 turn"
    },
    {
        "name": "Amber Slow",
        "type": "environmental",
        "stat": "Might",
        "dc_formula": lambda tier: 11 + tier,
        "effect_formula": lambda tier: f"Partial amber coating — movement halved for {tier} turns"
    },
    {
        "name": "Resonance Feedback",
        "type": "environmental",
        "stat": "Aether",
        "dc_formula": lambda tier: 10 + tier * 2,
        "effect_formula": lambda tier: f"Subsonic hum — lose {tier} Aether, spells cost double next turn"
    }
]


# =============================================================================
# ROOM DESCRIPTIONS (TIER-BASED)
# =============================================================================

HEARTWOOD_ROOM_DESCRIPTIONS: Dict[int, List[str]] = {
    1: [
        # Tier 1: Recognizable Arborist construction. Carved wood, familiar tools, amber-lit.
        "The walls are wood, but carved — ring-lines cut in parallel bands, smooth under the hand. Amber sconces glow from recessed niches. The ceiling arches in a shallow curve. You can hear your own footsteps clearly.",
        "A low-ceilinged passage. The floor is polished, the grain running lengthwise. Something has been at the walls with a fine chisel, marking intervals of three finger-widths in neat rows. The amber glow here is yellow, warm, like a candle held too close.",
        "Wide enough for two abreast. The ring markings on the walls are fresh-looking despite their age — the wood does not crack here. A sealed alcove to the left holds what might be tools behind a panel of clear amber.",
        "The ceiling is lower than the last room by a full handspan. You feel it. A groove runs along the floor's center, precisely cut, leading nowhere apparent. The amber light flickers once and holds.",
        "Arborist work. The walls have been joined without seams — each board running parallel to the next in growth-ring sequence. The air smells of old resin and sealed things. Something tapped against a far wall once, then stopped.",
        "A chamber with eight sides, each wall a different ring-width. The narrower walls have recesses carved into them, empty now. The floor has been swept recently — or was swept centuries ago and nothing has disturbed it since.",
        "Amber in the walls here, thin veins of it running between the boards like mortar. Still liquid in places, pressing against the grain. The light it gives is even and sourceless.",
        "The passage widens into a room that was clearly designed for working. A low bench runs one wall, built into the grain. The tools are gone. The bolts that held them remain, still polished."
    ],
    2: [
        # Tier 2: Denser. Amber embedded in walls like fossils in stone. Geometry curves wrong.
        "The walls are thicker here. Amber is not in veins — it is mass, filling gaps between the ring-boards in solid sections. Inside the largest amber mass, at eye level: a shape. Too regular to be a branch.",
        "The floor begins to curve upward at both walls, meeting the ceiling in a slight arc. Not structural damage — designed. The Arborists wanted this curve. You have to tilt your head to read the ring markings.",
        "Something is suspended in the amber panel beside the door. A hand. Wrist down. Fingers slightly open. The amber around it is perfect, without seam or crack, as if it was poured around the moment.",
        "The passages behind you were straight. This one bends. Not much — perhaps ten degrees — but by the third bend you have lost your cardinal direction entirely. The ring markings are still parallel, still precise.",
        "The amber here is dark amber, almost red. It thickens the light. Shapes move in it — not creatures, but motion, the way sunlight moves through water. The wall is warm.",
        "A juncture of three corridors, all the same width, all meeting at a subtle angle that makes it unclear which you came from. The floor has a drain at the center, also blocked with amber. Sealed from below.",
        "The ceiling has lowered enough that you are aware of it. Growth rings above, very close. The amber between them has developed small bubbles. They are perfectly spherical. They have not moved.",
        "Two amber slabs face each other across a gap you can barely pass through sideways. Both contain shapes — partial, the amber cut smooth at the surface. Whatever is inside continues deeper than you can see."
    ],
    3: [
        # Tier 3: Wood so dense it rings like metal. Light comes from the grain itself.
        "The wall does not sound like wood when you knock it. It rings. The density is wrong for something organic — this growth ring has compressed to something past timber and approaching stone. The light comes from inside the grain itself, a cold amber-white.",
        "No amber sconces here. No veins. The wood glows directly, a luminescence that has no source you can trace, running along the grain in pulses spaced like heartbeats. The pulses are not synchronized room to room.",
        "Every surface is carved — floor, ceiling, all four walls — in overlapping ring-script. Too dense to read in this light. Too dense to read in any light. This was not meant to be read. It was meant to be said.",
        "The doors here are not hinged. They are grown shut, the grain flowing from door to frame in continuous lines. The only opening is a crack too narrow for a shoulder but wide enough for the light to pulse through.",
        "The air has pressure. Not heat, not cold — pressure. As if the walls are squeezing inward at a rate too slow to measure. The growth rings are visible on every surface, counting backwards toward center.",
        "A circular room. The growth rings on the walls are complete circles here — this is where the tree is round. The floor is the lowest point of a bowl shape, perfectly symmetrical. Your voice sounds different. Flatter.",
        "The grain here pulls diagonally, upward and inward, toward something above. Every board, every ring. Even the amber deposits are elongated in that direction, stretched by growth over centuries. You cannot see what they are reaching toward.",
        "Two branching corridors ahead, but the wood between them has grown into the gap — not blocking it, just present, filling the space with dense grain. You could push through. It would feel like pushing through something asleep."
    ],
    4: [
        # Tier 4: The First Ring. Alien. Beautiful. The wood is warm and breathing.
        "The First Ring. The wood here predates the name Arborist. Predates naming. It is warm — not ambient warmth, warm the way living skin is warm. When you press your palm flat, you can feel the pulse.",
        "There is no light source. The wood produces light the way it produces heat — it simply does. The grain here has never been cut. These surfaces are not carved: they are grown, shaped over four centuries of patient pressure into corridors and chambers.",
        "You can hear it. Not a sound — below sound. A vibration felt in the sternum, in the back teeth. The whole mass of wood around you is resonating at a single frequency. The amber deposits vibrate at the same frequency. You vibrate at a different one. The tree notices.",
        "The growth rings on this wall tell four hundred years. You count them the way you count the rings of a felled tree, running your finger from the outside in. Here, you cannot find the outside. You are inside all of them.",
        "The amber here is not amber. It is the same material, hardened sap, but it is red at depth and white at the surface, and it moves. Slowly. Measurably. The trapped shapes inside it have moved since you entered. They have turned toward you.",
        "The architecture stops making sense in human terms. The walls are not perpendicular. The ceiling is not parallel to the floor. Everything slopes toward a center that is below you and above you simultaneously. You are inside a growth node.",
        "The Arborists built here, and then the tree grew around what they built, and then they built around what the tree grew, and then the tree grew around that. The joins between made and grown are invisible. You cannot tell where one ends.",
        "Still. The First Ring is still. No amber echoes here, no immune response. The warmth is absolute. Your wounds stop aching. This is not safety — this is the inside of something very large that has not decided what to do with you yet."
    ]
}


# =============================================================================
# SPECIAL ROOM DESCRIPTIONS
# =============================================================================

HEARTWOOD_SPECIAL_DESCRIPTIONS: Dict[str, str] = {
    "start": (
        "The seal parts. Not breaks — parts. The two halves of carved amber slide into the walls with a sound like a breath released after long holding. Beyond: older wood. Darker. The air on the other side is still and warm and smells of nothing at all. The ring markings on the floor continue without interruption from the Tangle into here, as if the Arborists considered this a single space. They were right."
    ),
    "boss": (
        "The chamber is a perfect cylinder. The walls are amber pillars, each one floor-to-ceiling, each one containing a shape at its core — unidentifiable at this distance, but present. Between the pillars, the grain flows in arcs, reaching from wall to wall overhead. The silence here is not empty. It is the silence of a held note, a sound that has been sustained for so long it no longer vibrates. You feel it in your jaw. In the center of the floor: a growth ring so compressed it has become a circle of red wood, darker than the rest. Something stands on it."
    ),
    "treasure": (
        "The resin pocket has cracked — not catastrophically, but enough. A fracture line runs from floor to ceiling, and through it, amber-warm light bleeds. Inside: density. The resin has crystallized around objects, layers upon layers, accumulating over centuries. Some are tools. Some are instruments. Some are neither, and the shape of them suggests the hands that used them were not making anything you would recognize. The crystallized surfaces are smooth, and where you touch one, it briefly warms."
    ),
    "secret": (
        "The wall here is different from the others — not in texture or material, but in intention. The grain runs parallel everywhere else in the Heartwood. Here it converges, funneling inward to a single point at eye level. Press it. The panel does not open so much as it exhales, a long slow breath of still air, and behind it: a corridor you were never meant to find, lit by murals that cover every surface from threshold to end."
    ),
    "painted_gallery": (
        "Every surface. The murals here cover every surface — floor, ceiling, all four walls — in continuous images that do not repeat. Arborist work: pigments suspended in resin, still bright. The images show people working. Not building — maintaining. Their tools are precise. Their faces are careful. Some of them are looking out of the image, into the room. Their expressions are not warning you. They are noting your presence for the record."
    ),
    "silent_garden": (
        "The living wood here has been shaped. Not by tools — by time, by hands applying steady pressure over years. The walls have grown into curves that catch and hold the amber light. Alcoves hold wooden forms: instruments, or vessel-shapes, or things that have no analogue. No dust. No decay. The tree has kept this room. Whatever was placed here four hundred years ago is still here, warm and clean and undisturbed, waiting for hands that know what to do with it."
    ),
    "amber_stasis": (
        "They are standing. Three of them, that you can see, each one sealed in amber to the chest. The amber has grown up over centuries — it was not poured around them. They grew into it, or it grew around them, at a pace that let them remain intact. Their eyes are open. The amber in front of their faces is perfectly clear. One of them blinks. Once. The amber does not crack. The expression does not change. The eyes find yours and stay."
    )
}


# =============================================================================
# THE HEARTWOOD ADAPTER (RulesetAdapter Implementation)
# =============================================================================

class HeartwoodAdapter(RulesetAdapter):
    """
    Zone 6: The Heartwood content population adapter.

    This adapter generates biome-specific content for Heartwood rooms.

    ARCHITECTURE COMPLIANCE:
        - Heart logic only: No text generation
        - Deterministic: Seeded RNG per room
        - Composable: Works with any CodexMapEngine output

    Content Structure:
        {
            "biome_tags":   [HeartBiome.GROWTH_RING.value, ...],
            "enemies":      [{"name": str, "hp": int, "defense": int, "damage": str, "note": str}, ...],
            "loot":         [{"name": str, "slot": str, "tier": int, ...}, ...],
            "hazards":      [{"name": str, "type": str, "stat": str, "dc": int, "effect": str}],
            "interactive":  [...]
        }

    NOTE: The "description" field is intentionally omitted. That is the Brain's job.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the Heartwood adapter.

        Args:
            seed: Random seed for deterministic generation (default: random)
        """
        self.seed = seed if seed is not None else random.randint(0, 999999)

    def populate_room(self, room: RoomNode) -> PopulatedRoom:
        """
        Populate a room with Heartwood-specific content.

        Args:
            room: Geometry node from map engine

        Returns:
            PopulatedRoom with Heartwood biome content
        """
        # Deterministic RNG: seeded per room so every room is repeatable
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
            rng:  Seeded random generator

        Returns:
            List of HeartBiome values (as strings for serialization)
        """
        tags = []

        # Guaranteed tags by room type
        if room.room_type == RoomType.START:
            tags.extend([tag.value for tag in START_GUARANTEED_TAGS])

        elif room.room_type == RoomType.BOSS:
            tags.extend([tag.value for tag in BOSS_GUARANTEED_TAGS])

        elif room.room_type == RoomType.TREASURE:
            tags.extend([tag.value for tag in TREASURE_GUARANTEED_TAGS])

        elif room.room_type == RoomType.SECRET:
            tags.extend([tag.value for tag in SECRET_GUARANTEED_TAGS])

        # Probabilistic tags (skip any already guaranteed)
        for tag, weight in HEARTWOOD_BIOME_WEIGHTS.items():
            if tag.value not in tags and rng.random() < weight:
                tags.append(tag.value)

        # Ensure at least one tag
        if not tags:
            tags.append(HeartBiome.GROWTH_RING.value)

        return tags

    # ─────────────────────────────────────────────────────────────────────
    # ROOM TYPE POPULATION METHODS
    # ─────────────────────────────────────────────────────────────────────

    def _populate_start_room(self, room: RoomNode, content: dict, rng: random.Random):
        """
        Populate the starting room.

        The seal has just parted. No enemies. Sparse loot — the Arborists
        did not leave a welcome cache here.
        """
        # No enemies in the start room
        # 40% chance of a single Tier 1 item — something dropped near the threshold
        if rng.random() < 0.4:
            content["loot"].append(rng.choice(HEARTWOOD_LOOT[1]).copy())

    def _populate_boss_room(self, room: RoomNode, content: dict, rng: random.Random):
        """
        Populate a boss chamber.

        Single guardian, always present. High-tier loot — the tree does not
        hoard, but what it protects is worth protecting.
        """
        # Single boss enemy, enhanced with is_boss flag
        boss_template = HEARTWOOD_BOSSES.get(room.tier, HEARTWOOD_BOSSES[1])
        boss = boss_template.copy()
        boss["is_boss"] = True
        content["enemies"].append(boss)

        # Boss rooms carry higher-tier loot (tier + 1, capped at 4)
        loot_tier = min(4, room.tier + 1)
        loot_count = rng.randint(2, 3)
        content["loot"].extend(
            [rng.choice(HEARTWOOD_LOOT[loot_tier]).copy() for _ in range(loot_count)]
        )

    def _populate_treasure_room(self, room: RoomNode, content: dict, rng: random.Random):
        """
        Populate a resin pocket vault.

        Unlocked rooms have a construct guardian. Locked rooms do not — the
        seal is the guard. Either way: good loot.
        """
        # Unlocked treasure rooms have a guardian
        if not room.is_locked:
            enemy_count = rng.randint(1, 2)
            enemy_pool = HEARTWOOD_ENEMIES.get(room.tier, HEARTWOOD_ENEMIES[1])
            content["enemies"].extend(
                [rng.choice(enemy_pool).copy() for _ in range(enemy_count)]
            )

        # Multiple loot items — the resin pocket has been accumulating
        loot_count = rng.randint(2, 4)
        loot_pool = HEARTWOOD_LOOT.get(room.tier, HEARTWOOD_LOOT[1])
        content["loot"].extend(
            [rng.choice(loot_pool).copy() for _ in range(loot_count)]
        )

    def _populate_secret_room(self, room: RoomNode, content: dict, rng: random.Random):
        """
        Populate a hidden room.

        The painted gallery or silent garden. No enemies — the tree keeps
        this room deliberately still. High-tier loot, possible resonance hazard.
        """
        # No combat here — these rooms are preserved, not defended
        # High-tier loot (tier + 1, capped at 4)
        loot_tier = min(4, room.tier + 1)
        loot_pool = HEARTWOOD_LOOT.get(loot_tier, HEARTWOOD_LOOT[1])
        content["loot"].extend([rng.choice(loot_pool).copy() for _ in range(2)])

        # 40% chance of a resonance hazard — the stillness is maintained by something
        if rng.random() < 0.4:
            hazard = rng.choice(HEARTWOOD_HAZARDS)
            content["hazards"].append({
                "name": hazard["name"],
                "type": hazard["type"],
                "stat": hazard["stat"],
                "dc": hazard["dc_formula"](room.tier),
                "effect": hazard["effect_formula"](room.tier)
            })

    def _populate_normal_room(self, room: RoomNode, content: dict, rng: random.Random):
        """
        Populate a standard room.

        May have constructs patrolling, loot embedded in the amber,
        and the occasional cracked seal to navigate.
        """
        # Constructs patrol normal rooms (0-2 enemies), corridors are empty
        if room.room_type != RoomType.CORRIDOR:
            enemy_count = rng.randint(0, 2)
            enemy_pool = HEARTWOOD_ENEMIES.get(room.tier, HEARTWOOD_ENEMIES[1])
            content["enemies"].extend(
                [rng.choice(enemy_pool).copy() for _ in range(enemy_count)]
            )

        # 35% chance of loot — Arborist items embedded in amber or left in alcoves
        if rng.random() < 0.35:
            loot_pool = HEARTWOOD_LOOT.get(room.tier, HEARTWOOD_LOOT[1])
            content["loot"].append(rng.choice(loot_pool).copy())

        # 20% chance of hazard — cracked seals or immune pulses
        if rng.random() < 0.20:
            hazard = rng.choice(HEARTWOOD_HAZARDS)
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

        Interactive elements are structural affordances (harvestable, breakable, etc.)
        NOT descriptions. The Brain will generate text for these later.
        """
        tags = content["biome_tags"]

        # GROWTH_RING → Readable surface (Arborist ring-script)
        if HeartBiome.GROWTH_RING.value in tags:
            content["interactive"].append({
                "type": "readable",
                "target": "growth ring script",
                "stat": "Wits",
                "dc": 10 + room.tier,
                "reward": "Lore fragment or construct patrol pattern"
            })

        # AMBER_DEPOSIT → Examinable (may contain items or stasis shapes)
        if HeartBiome.AMBER_DEPOSIT.value in tags:
            content["interactive"].append({
                "type": "examinable",
                "target": "amber deposit",
                "stat": "Wits",
                "dc": 9 + room.tier,
                "reward": f"Identify contents — possible Tier {room.tier} loot or stasis creature"
            })

        # SAP_CHANNEL → Operable valve (pressurized — risk/reward)
        if HeartBiome.SAP_CHANNEL.value in tags:
            content["interactive"].append({
                "type": "operable",
                "target": "sap channel valve",
                "stat": "Wits",
                "dc": 11 + room.tier,
                "reward": f"Redirect sap flow — seal hazard or reveal passage",
                "risk": f"Burst: {room.tier}d6 damage on failure"
            })

        # RESIN_POCKET → Harvestable resource
        if HeartBiome.RESIN_POCKET.value in tags:
            content["interactive"].append({
                "type": "harvestable",
                "target": "resin pocket",
                "stat": "Wits",
                "dc": 10 + room.tier,
                "reward": f"Pure Heartwood Resin (Tier {room.tier} crafting component)"
            })

        # ARBORIST_RELIC → Lootable container (sealed)
        if HeartBiome.ARBORIST_RELIC.value in tags:
            content["interactive"].append({
                "type": "lootable",
                "target": "sealed Arborist container",
                "stat": "Wits",
                "dc": 12 + room.tier,
                "reward": "Arborist tool, instrument, or blueprint fragment"
            })

        # CRACKED_SEAL → Hazard + potential bypass
        if HeartBiome.CRACKED_SEAL.value in tags:
            content["interactive"].append({
                "type": "hazard_object",
                "target": "cracked Arborist seal",
                "stat": "Might",
                "dc": 13 + room.tier,
                "reward": "Force seal — stop immune response this room",
                "risk": f"Failure triggers Cracked Seal Burst: {room.tier}d6 damage"
            })

        # SILENT_GARDEN → Rest point (rare, fragile)
        if HeartBiome.SILENT_GARDEN.value in tags:
            content["interactive"].append({
                "type": "rest_point",
                "target": "silent garden",
                "effect": f"Short rest: recover {room.tier}d6 HP (disturbs the room — one use only)"
            })

        # PAINTED_MURAL → Lore source
        if HeartBiome.PAINTED_MURAL.value in tags:
            content["interactive"].append({
                "type": "readable",
                "target": "painted mural",
                "stat": "Aether",
                "dc": 8 + room.tier,
                "reward": "Arborist lore — names, dates, or technique record"
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
        enemies = HEARTWOOD_ENEMIES.get(tier, HEARTWOOD_ENEMIES[1])
        return [enemy["name"] for enemy in enemies]

    def get_loot_pool(self, tier: int) -> List[str]:
        """
        Get list of loot item names for a given tier.

        Args:
            tier: Difficulty tier (1-4)

        Returns:
            List of item names
        """
        loot = HEARTWOOD_LOOT.get(tier, HEARTWOOD_LOOT[1])
        return [item["name"] for item in loot]


# =============================================================================
# STANDALONE TEST & DEMO
# =============================================================================

def run_demo():
    """Demonstrate the Heartwood zone generator using HeartwoodAdapter directly."""
    print("=" * 70)
    print("ZONE 6: THE HEARTWOOD - PROCEDURAL GENERATOR TEST")
    print("=" * 70)

    # Generate a Heartwood zone
    print("\n[GENERATION]")
    map_engine = CodexMapEngine(seed=42)
    graph = map_engine.generate(
        width=50, height=50, min_room_size=5, max_depth=3,
        system_id="burnwillow",
    )
    adapter = HeartwoodAdapter(seed=42)
    injector = ContentInjector(adapter)
    populated_rooms = injector.populate_all(graph)

    zone = {
        "seed": graph.seed,
        "rooms": [],
        "start_room_id": graph.start_room_id,
        "total_rooms": len(populated_rooms),
    }
    for room_id, pop_room in populated_rooms.items():
        zone["rooms"].append({
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
            "interactive": pop_room.content["interactive"],
        })

    print(f"Seed: {zone['seed']}")
    print(f"Total Rooms: {zone['total_rooms']}")
    print(f"Start Room: {zone['start_room_id']}")

    # Display room summaries
    print("\n[ROOM SUMMARIES]")
    for room in sorted(zone["rooms"], key=lambda r: r["id"]):
        room_type = room["type"].upper()
        locked = " [LOCKED]" if room["is_locked"] else ""

        print(f"\n--- Room {room['id']:02d}: {room_type:10s} (Tier {room['tier']}){locked} ---")
        print(f"Position: {room['position']} | Size: {room['size']}")
        print(f"Connections: {room['connections']}")
        print(f"Biome Tags: {', '.join(room['biome_tags'])}")

        if room["enemies"]:
            print("Enemies:")
            for enemy in room["enemies"]:
                boss = " (BOSS)" if enemy.get("is_boss") else ""
                print(f"  - {enemy['name']}{boss}: {enemy['hp']} HP, DEF {enemy['defense']}, DMG {enemy['damage']}")

        if room["loot"]:
            print("Loot:")
            for item in room["loot"]:
                special = f" [{item.get('special', '')}]" if "special" in item else ""
                print(f"  - {item['name']} ({item['slot']}, Tier {item['tier']}){special}")

        if room["hazards"]:
            print("Hazards:")
            for hazard in room["hazards"]:
                print(f"  - {hazard['name']}: {hazard['stat']} DC {hazard['dc']} ({hazard['effect']})")

        if room["interactive"]:
            print("Interactive:")
            for elem in room["interactive"]:
                print(f"  - {elem['type'].upper()}: {elem['target']}")

    # Statistical summary
    print("\n[STATISTICS]")
    tag_counts: dict = {}
    for room in zone["rooms"]:
        for tag in room["biome_tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print("Biome Tag Distribution:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / zone["total_rooms"]) * 100
        print(f"  {tag:22s}: {count:2d} rooms ({percentage:5.1f}%)")

    total_enemies  = sum(len(room["enemies"]) for room in zone["rooms"])
    total_loot     = sum(len(room["loot"])    for room in zone["rooms"])
    total_hazards  = sum(len(room["hazards"]) for room in zone["rooms"])

    print(f"\nTotal Enemies:  {total_enemies}")
    print(f"Total Loot:     {total_loot}")
    print(f"Total Hazards:  {total_hazards}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()

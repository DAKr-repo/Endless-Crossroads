#!/usr/bin/env python3
"""
zone_undergrove.py - The Undergrove (Zone 7) Procedural Generator
==================================================================

Biome-specific procedural generation for Zone 7: The Undergrove.

LORE:
    Below the four Groves, where their roots meet and become indistinguishable
    from one another, lies the Undergrove. The Rot did not invade this place.
    It was born here. Failed Grove fossils — petrified skeletons of trees that
    preceded the Four — stand enormous in the dark. The Choir's song is not
    heard in the Undergrove. It is felt. In your molars. In the fluid behind
    your eyes. The deeper you descend, the more the song becomes pressure.

BIOME IDENTITY:
    - Root convergence: All four Grove signatures woven together, inseparable
    - Decomposition ecology: The Rot as a natural process, not an invasion
    - Failed Grove fossils: Petrified relics of an older world
    - Root-Road intersections: Sealed passages from each Grove surface
    - The Choir's physical presence: Distortion waves, sympathetic vibration

ARCHITECTURE (The Heart):
    - Pure deterministic logic
    - NO text generation (that's the Brain's job)
    - NO I/O operations
    - Uses RulesetAdapter pattern from map_engine.py

RESOURCE PROFILE:
    - RAM: ~5-10MB resident (same as base map engine)
    - CPU: ~10-20ms per room for biome tag assignment
    - Thermal: Negligible

Version: 1.0 (Undergrove Biome Adapter)
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

class UndergroveBiome(Enum):
    """
    Environmental features unique to The Undergrove.

    These are STRUCTURAL tags (Heart logic), not descriptions (Brain logic).
    The Brain will later generate flavor text based on these tags.
    """
    ROOT_TANGLE = "ROOT_TANGLE"                  # Impenetrable woven root-mass, movement hazard
    DECOMPOSITION_LAYER = "DECOMPOSITION_LAYER"  # Active Rot processing zone (damage over time)
    FAILED_GROVE_FOSSIL = "FAILED_GROVE_FOSSIL"  # Ancient petrified tree skeleton (lore node)
    ROOT_ROAD_JUNCTION = "ROOT_ROAD_JUNCTION"    # Sealed passage bearing multi-Grove signatures
    CHOIR_RESONANCE = "CHOIR_RESONANCE"          # Physical song distortion (stat check zone)
    HOLLOW_DRIFT = "HOLLOW_DRIFT"                # Active Hollow migration path
    MYCELIUM_VEIN = "MYCELIUM_VEIN"              # Fungal network node (harvestable ingredient)
    NUTRIENT_POOL = "NUTRIENT_POOL"              # Decomposed organic slurry (hazard + resource)
    BREACH_POINT = "BREACH_POINT"                # Raw wound in zone boundary (unstable, dangerous)


# =============================================================================
# BIOME TAG PROBABILITY TABLES
# =============================================================================

# Probability weights for tag assignment (per room)
UNDERGROVE_BIOME_WEIGHTS: Dict[UndergroveBiome, float] = {
    UndergroveBiome.ROOT_TANGLE: 0.85,          # Ubiquitous (85% of rooms)
    UndergroveBiome.DECOMPOSITION_LAYER: 0.45,  # Common (45% of rooms)
    UndergroveBiome.HOLLOW_DRIFT: 0.35,         # Common (35% of rooms)
    UndergroveBiome.CHOIR_RESONANCE: 0.30,      # Uncommon (30% of rooms)
    UndergroveBiome.MYCELIUM_VEIN: 0.25,        # Uncommon (25% of rooms)
    UndergroveBiome.NUTRIENT_POOL: 0.20,        # Uncommon (20% of rooms)
    UndergroveBiome.ROOT_ROAD_JUNCTION: 0.10,   # Rare (10% of rooms)
    UndergroveBiome.FAILED_GROVE_FOSSIL: 0.08,  # Rare (8% of rooms)
    UndergroveBiome.BREACH_POINT: 0.04,         # Very rare (4% of rooms, dangerous)
}

# Boss room guaranteed tags
BOSS_GUARANTEED_TAGS = [
    UndergroveBiome.CHOIR_RESONANCE,
    UndergroveBiome.DECOMPOSITION_LAYER,
    UndergroveBiome.ROOT_TANGLE
]

# Treasure room guaranteed tags
TREASURE_GUARANTEED_TAGS = [
    UndergroveBiome.NUTRIENT_POOL,
    UndergroveBiome.MYCELIUM_VEIN
]

# Start room guaranteed tags
START_GUARANTEED_TAGS = [
    UndergroveBiome.ROOT_TANGLE,
    UndergroveBiome.BREACH_POINT
]


# =============================================================================
# ENEMY POOLS (TIER-BASED)
# =============================================================================

# The Undergrove enemy catalog
UNDERGROVE_ENEMIES: Dict[int, List[dict]] = {
    1: [
        {
            "name": "Chorus Walker",
            "hp": 14,
            "defense": 13,
            "damage": "1d6",
            "special": "Resonance-Touched",
            "aura": "Choir Aura — any creature starting its turn adjacent takes 1 psychic damage"
        },
        {
            "name": "Drift Hollow",
            "hp": 8,
            "defense": 10,
            "damage": "1d6",
            "special": None,
            "note": "Former denizen, now fully Hollow; may be wearing civilian gear"
        }
    ],
    2: [
        {
            "name": "Sap Leech Swarm",
            "hp": 15,
            "defense": 9,
            "damage": "2d6",
            "special": "Weakened",
            "effect": "On hit, target has -1 to all rolls until end of next turn (sap drain)"
        },
        {
            "name": "Mature Gall",
            "hp": 12,
            "defense": 10,
            "damage": "2d6",
            "special": None,
            "note": "Root-growth parasite; bursts on death (Grit DC 12 or Weakened 1 round)"
        }
    ],
    3: [
        {
            "name": "Section Leader",
            "hp": 25,
            "defense": 16,
            "damage": "3d6",
            "special": "Zone Rot Buff",
            "aura": "While alive, all Rot-type enemies in zone deal +1 damage"
        },
        {
            "name": "Choir Elite",
            "hp": 18,
            "defense": 15,
            "damage": "3d6",
            "special": "Harmonic Strike",
            "effect": "On hit, Aether DC 14 or target is Deafened for 1 round (disadvantage on Wits)"
        }
    ],
    4: [
        {
            "name": "Ancient Hollow",
            "hp": 30,
            "defense": 16,
            "damage": "4d6",
            "special": "Named Gear",
            "note": "Wearing recognizable Seeker equipment; defeating it may yield a named item"
        },
        {
            "name": "Root Colossus",
            "hp": 35,
            "defense": 18,
            "damage": "4d6",
            "special": "Petrified Carapace",
            "effect": "First hit each round deals -2 damage (fossil-root plating)"
        }
    ]
}

# Boss variants (enhanced stats, unique mechanics)
UNDERGROVE_BOSSES: Dict[int, dict] = {
    1: {
        "name": "Breach Warden",
        "hp": 20,
        "defense": 14,
        "damage": "2d6",
        "special": "Boundary Seal",
        "effect": "At start of each round, seals one exit (Might DC 13 to force open)"
    },
    2: {
        "name": "The Compost King",
        "hp": 35,
        "defense": 16,
        "damage": "3d6",
        "special": "Decomposition Aura",
        "effect": "All creatures in room lose 1 max HP at end of each round until King is defeated"
    },
    3: {
        "name": "Choir Conductor Minor",
        "hp": 50,
        "defense": 17,
        "damage": "3d6",
        "special": "Resonance Cascade",
        "effect": "On kill, triggers wave of psychic damage (1d6) to all other creatures in room"
    },
    4: {
        "name": "The Conductor",
        "hp": 80,
        "defense": 18,
        "damage": "4d6",
        "special": "Song of Ending",
        "persistent": "Persistent 1d4 psychic damage per round to all creatures in chamber",
        "summon": "Summons 1d2 Chorus Walkers at start of each round",
        "phase_2": {
            "trigger_hp": 40,
            "name": "Song of Ending",
            "dc": 22,
            "stat": "Aether",
            "effect": "On failed save: Incapacitated for 1 round. On critical fail: Charmed by the Choir for 1 minute"
        }
    }
}


# =============================================================================
# LOOT POOLS (TIER-BASED)
# =============================================================================

UNDERGROVE_LOOT: Dict[int, List[dict]] = {
    1: [
        {"name": "Decomposed Bark Strip", "slot": "Consumable", "tier": 1,
         "special": "Craft ingredient (Undergrove composite armor base)"},
        {"name": "Mycelium Paste", "slot": "Consumable", "tier": 1,
         "special": "Ingredient; applied to wounds — stop bleeding, 1d4 HP"},
        {"name": "Leech-Purged Shard", "slot": "Trinket", "tier": 1,
         "dr": 0, "special": "Resist 1 psychic damage per round while held"},
        {"name": "Woven Root Brace", "slot": "Hands", "tier": 1, "dr": 1}
    ],
    2: [
        {"name": "Rot-Processed Pauldrons", "slot": "Shoulders", "tier": 2, "dr": 2,
         "special": "Treated with Undergrove Rot; immune to Weakened condition"},
        {"name": "Gall-Burst Vial", "slot": "Consumable", "tier": 2,
         "special": "Thrown (range 10ft): 2d6 acid damage in 5ft radius, Grit DC 13 or Weakened"},
        {"name": "Resonance-Dulled Helm", "slot": "Head", "tier": 2, "dr": 1,
         "special": "Advantage on saves vs. Choir effects"},
        {"name": "Compost-Fed Shortblade", "slot": "R.Hand", "tier": 2, "damage": "2d6",
         "special": "On hit vs. Rot enemies: +1d4 bonus damage"}
    ],
    3: [
        {"name": "Fossil-Root Breastplate", "slot": "Chest", "tier": 3, "dr": 3,
         "special": "Petrified failed-Grove wood; immune to Decomposition Aura effects"},
        {"name": "Conductor's Baton Fragment", "slot": "R.Hand", "tier": 3, "damage": "3d6",
         "special": "Aether +1; wielder can hear the Choir clearly (advantage on Choir-related lore checks)"},
        {"name": "Deep-Root Salve", "slot": "Consumable", "tier": 3,
         "special": "Restore 3d6 HP; clear Weakened, Deafened, and Charmed conditions simultaneously"},
        {"name": "Memory Seed (Undergrove Strain)", "slot": "Neck", "tier": 3,
         "special": "Unlock blueprint — Undergrove composite gear set (Tier 3 recipe)"}
    ],
    4: [
        {"name": "The Conductor's Coat", "slot": "Chest", "tier": 4, "dr": 4,
         "special": "Regen 1 HP/round; psychic damage you deal +2; Choir creatures do not attack you unless you attack first"},
        {"name": "Root Colossus Shard-Axe", "slot": "R.Hand", "tier": 4, "damage": "4d6",
         "special": "On kill: deal 1d6 psychic splash to all adjacent enemies (resonance discharge)"},
        {"name": "Undergrove Sovereign Ring", "slot": "L.Ring", "tier": 4,
         "stat": "Aether +2", "special": "Once per rest: become immune to Choir effects for 1 minute"},
        {"name": "Ancient Hollow Core", "slot": "Neck", "tier": 4,
         "special": "Store 1 spell; once per rest: cast that spell without expending a slot (Undergrove resonance)"}
    ]
}


# =============================================================================
# HAZARD DEFINITIONS
# =============================================================================

UNDERGROVE_HAZARDS = [
    {
        "name": "Root Crush",
        "type": "trap",
        "stat": "Might",
        "dc_formula": lambda tier: 9 + tier * 2,
        "effect_formula": lambda tier: f"{tier}d6 bludgeoning damage, Restrained until freed (Might DC {8 + tier * 2})"
    },
    {
        "name": "Decomposition Mist",
        "type": "environmental",
        "stat": "Grit",
        "dc_formula": lambda tier: 10 + tier * 2,
        "effect_formula": lambda tier: f"Lose {tier} max HP until rest (organic decay)"
    },
    {
        "name": "Choir Pulse",
        "type": "environmental",
        "stat": "Aether",
        "dc_formula": lambda tier: 11 + tier * 2,
        "effect_formula": lambda tier: f"{tier}d4 psychic damage; Wits -1 until end of encounter"
    },
    {
        "name": "Sinkhole Nutrient Pool",
        "type": "trap",
        "stat": "Wits",
        "dc_formula": lambda tier: 10 + tier,
        "effect_formula": lambda tier: f"Submerged in nutrient slurry — {tier}d6 acid damage, gear requires cleaning (Grit DC 10 or Weakened)"
    }
]


# =============================================================================
# ROOM DESCRIPTIONS (STATIC POOLS — BRAIN SUPPLEMENTS THESE)
# =============================================================================

UNDERGROVE_ROOM_DESCRIPTIONS: Dict[int, List[str]] = {
    1: [
        # Tier 1: Roots you can identify. Burnwillow amber-veined alongside Verdhollow green strands. Damp.
        "Amber veins pulse faint and slow through the root wall to your left — Burnwillow, unmistakably. "
        "To your right, green strands the color of moss run parallel. Verdhollow. Both systems are still "
        "alive here, still distinct. The ceiling drips. Cold water collects in the grooves between roots.",

        "The roots are thick as your thigh and smell of wet soil and copper. You can still tell them apart "
        "— the amber-flecked Burnwillow strands, the darker Verdhollow weave above them. The floor is "
        "spongy with accumulated organic matter. Each step produces a soft, deliberate sound.",

        "Light does not reach here from above. What illumination exists comes from the amber veins "
        "themselves — a dim, unsteady pulse that makes shadows lean the wrong direction. The roots "
        "around you are identifiable: four systems, four colors, all running the same direction. Deeper.",

        "Water seeps from every surface. The roots here are young by Undergrove standards — thick but "
        "not fused. You can see where Burnwillow amber and Cindergrove rust-red run side by side without "
        "merging. The gap between them is a centimeter at most. The air tastes of copper and old growth.",

        "The passage is barely wide enough for two abreast. The roots that form its walls are smooth "
        "from something's repeated passage — worn down to the wood. Burnwillow amber weeps where the "
        "surface is abraded. The weeping has no smell. That is unusual.",

        "Drip-water has pooled in a natural depression. The pool is the color of black tea, layered "
        "with decomposed root matter. Around its edges you can identify the contributing root systems "
        "by the color of their runoff: amber, green, rust, grey. Four sources. One pool.",

        "The roots overhead are still distinguishable here — you can trace Verdhollow green from "
        "Cindergrove rust without much effort. But the floor is different. The floor is composite, "
        "already indistinguishable, already part of whatever the Undergrove is making of them. "
        "Walking on it feels softer than it should.",

        "You stop and listen. There is a sound beneath the ambient drip — low, rhythmic, like breathing "
        "through a wet cloth. It does not stop when you stop moving. The amber veins in the root wall "
        "nearest you pulse in time with it. Slow. Once every three seconds. You count to be sure."
    ],
    2: [
        # Tier 2: Roots indistinguishable. Woven so tight you can't tell which Grove. Water seeps everywhere.
        "The roots here have fused. You press your palm against the wall and cannot find a seam — "
        "Burnwillow amber and Verdhollow green have merged into something the color of old bronze. "
        "Water seeps from the joint. It is warm. The warmth has no natural explanation.",

        "You cannot tell which Grove these roots belong to. The color is uniform: a deep, wet umber "
        "that absorbs your light rather than reflecting it. They are woven too tightly to navigate "
        "around. Your only path is through the gap they leave, which they did not leave for you.",

        "The ceiling here is a continuous mass of interwoven root. Individual strands are no longer "
        "visible. What you see is a single surface — breathing, slightly, as water pressure shifts "
        "within it. Drops fall from its lowest points every few seconds. The floor is ankle-deep "
        "in the accumulated result.",

        "Water seeps from every junction in the root weave. This is not a leak. This is the system "
        "working. The Undergrove processes what falls through from above and what rises from below, "
        "and the water is the byproduct — nutrient-rich, dark, smelling of copper and old iron. "
        "It soaks your boots within seconds of standing still.",

        "The root mass has grown so dense that movement requires pressing through it. It yields "
        "reluctantly. There is a sound when it does — not quite tearing, not quite releasing. "
        "Something between the two. The roots close behind you as you pass.",

        "You cannot name what you are looking at. The walls were roots once. Now they are a single "
        "organism — or something close enough to one that the distinction has stopped mattering. "
        "The color shifts as you move your light: bronze to green to amber to grey. All four Groves. "
        "None of them.",

        "The air here is wet enough to breathe in mouthfuls. Your lungs feel heavier. The root mass "
        "around you is sweating — a thin film of nutrient fluid coating every surface. You can write "
        "your name in it with a finger. The surface reseals itself in under a minute.",

        "There is a low-frequency vibration in the root wall that you feel in your chest rather than "
        "hear with your ears. It has been there since you entered this corridor. You have stopped "
        "noticing it except when it pauses — brief, irregular breaks that make you look up, "
        "anticipating something that does not come."
    ],
    3: [
        # Tier 3: The Choir's song is physical. Visible as distortion waves. Your gear hums sympathetically.
        "The song is visible. Ahead of you, the air shimmers in a slow wave — like heat distortion, "
        "but moving against the thermal gradient. Your blade hums a single note in response. "
        "You did not touch it. The resonance found it on its own.",

        "Every metal surface you carry is vibrating. Not violently — a sustained, precise frequency "
        "that your body translates as nausea if you hold still long enough to feel it. The distortion "
        "waves move through the root mass and out the other side, carrying the Choir's intent with them.",

        "You can see sound. You know that is not how perception works. But the pressure pulses moving "
        "through this chamber are dense enough that they push the fungal spore-cloud into visible "
        "patterns — concentric rings expanding from somewhere below. The center is deeper. Always deeper.",

        "Your pack is heavier. Nothing has been added to it. The vibration has found the resonant "
        "frequency of the frame and is holding it there, adding a sympathetic weight that your "
        "muscles feel as real load. You stop and breathe. The weight does not leave when you exhale.",

        "The root walls here do not absorb the Choir's song. They transmit it, each strand "
        "vibrating at its natural frequency and combining with the others into something that "
        "presses on your ears from inside. You have a nosebleed. You did not notice when it started.",

        "Distortion waves roll through the chamber in sets of three. The first you hear. The second "
        "you feel. The third you do not experience — you simply find that a moment has passed "
        "that you cannot account for. Your companions are looking at you.",

        "The amber veins in the root mass are pulsing in rhythm with the Choir — faster here, "
        "urgently, as if the Grove is being instructed. The pulse matches a frequency you feel "
        "in your back teeth. Holding your jaw shut is a deliberate effort that requires attention.",

        "You count the distortion waves: three per minute, each one broader than the last. "
        "Your lantern flame bends toward the source with each pulse. Not away — toward. "
        "Every combustion in this place is being pulled in the same direction."
    ],
    4: [
        # Tier 4: Failed Grove fossils. Petrified tree skeletons older than the Four. Some enormous. Silence.
        "The tree is enormous. Petrified completely — every fiber turned to dark stone, the root "
        "system spread across the chamber floor in a calcified fan wider than a house. This tree "
        "predates the Four. It predates whatever choice was made to limit the world to four Groves. "
        "It is not connected to the root network. It stands alone. Silent.",

        "The Choir does not sing here. In every other part of the Undergrove it is present — "
        "ambient, insistent, physical. Here it stops. The silence presses inward the way sound "
        "does elsewhere. You become aware of your own breathing as a violation.",

        "Three petrified trunks dominate this space, their crowns fused in the ceiling above. "
        "They are not the same tree — different bark textures, different stone colors. They grew "
        "here together and were petrified together. The process was not instantaneous. You can "
        "see the growth rings in cross-section where the stone fractured. Decades, at minimum.",

        "The fossil here is identifiable — similar root geometry to Burnwillow, similar vascular "
        "patterning, but wrong in fundamental ways. Older. Larger. The amber in its stone veins "
        "is not amber. It is something that preceded amber, that amber evolved from or was "
        "bred to replace. You have no word for its color.",

        "The silence is structural. The petrified roots absorb the Choir's frequency and "
        "convert it — not to heat, not to motion — to nothing. You stand in a pocket of true "
        "quiet and feel the full weight of how much noise the Undergrove had been making "
        "until this moment. Your ears ring with the absence.",

        "This fossil was a canopy tree once. The root system that spread from its base "
        "occupied hundreds of meters. Most of that root network is buried in the Undergrove "
        "floor — you are standing on it, have been for the last several rooms. What rises "
        "from the stone here is just the junction point. The anchor of something older "
        "than the world you were told about.",

        "Memory Seeds grow along the base of the petrified column. Not implanted — grown. "
        "Naturally occurring, in a species you have not seen cultivated in any Grove. "
        "The Arborists above do not know these exist. Or they did, once, and chose to stop "
        "acknowledging them. The seeds are cold to the touch.",

        "The largest fossil in the chamber stands forty feet tall and twice that wide "
        "at the base. The stone is the color of charcoal, with white mineral veins "
        "running the grain. It does not look dead. It looks finished — completed, "
        "sealed, waiting in a patience that does not require any particular outcome."
    ]
}

# Special room descriptions (unique, non-repeating)
UNDERGROVE_SPECIAL_DESCRIPTIONS: Dict[str, str] = {
    "start": (
        "The descent into the Undergrove is marked by a single amber seal — a thick disk of "
        "hardened sap set into the root floor, engraved with a date in Arborist notation. "
        "The date is recent. The seal is cracked. Through the crack, grey light rises from "
        "below, cold and uniform, sourceless. The air that escapes with it carries the smell "
        "of copper, compost, and something you cannot classify — something alive in a way "
        "that has nothing to do with warmth. You descend through the crack. The amber flexes "
        "around you as you pass, like lips closing behind a swallowed thing."
    ),
    "boss": (
        "The chamber has no walls you can find. The root mass extends in every direction and "
        "the edges of your light do not reach a boundary. At the center, where the distortion "
        "is densest, the Choir's song has become visible architecture — standing waves of "
        "compressed air that refract your light into sheets. Within the interference pattern, "
        "something moves. The movement is too large to be a Hollow. Too structured to be "
        "weather. Every metal surface you carry is screaming a single sustained note in "
        "response to a frequency you cannot hear but your body is measuring anyway."
    ),
    "treasure": (
        "The nutrient pool is deeper than it looks. What you thought was a shallow depression "
        "in the root floor descends past the reach of your light, its surface utterly still "
        "despite the vibrations that make everything else in the Undergrove tremble. "
        "Objects have accumulated at the pool's edge through the same process that accumulates "
        "everything down here — gravity and time. Blades with their hilts dissolved. "
        "Packs still buckled. A sealed box that is heavier than its size suggests, its lock "
        "replaced by a solid mass of root growth. All of it draped in mycelium that glows "
        "a pale blue when your light disturbs it."
    ),
    "secret": (
        "The chamber behind the false wall is lined with Failed Grove fossils. Not one — "
        "forty. Perhaps more. Petrified root systems of different species, different scales, "
        "arranged in no pattern you can identify as deliberate. At the chamber's far end, "
        "a natural formation of Memory Seeds grows from the base of the largest fossil, "
        "the seeds unnaturally large, cold to the touch. The Choir does not reach this room. "
        "Whatever the fossils do to the sound, they do it completely. You can hear yourself think. "
        "You are not sure that is a comfort."
    ),
    "root_road_junction": (
        "Four sealed passages meet at a single point. Each bears a Grove signature in its "
        "framing root-work: Burnwillow amber, Verdhollow green, Cindergrove rust, "
        "Ashgrove grey. All four passages have been closed — deliberately, by someone who "
        "understood the architecture — with root growth that has been guided and compressed "
        "into seals. The seals are not equal. One is older than the others by decades. "
        "One is newer than the others by weeks. Standing at the junction, you can feel "
        "pressure from all four directions, each distinct, each insistent."
    ),
    "hollow_drift": (
        "They move in a column, single-file, shuffling deeper at a pace that suggests "
        "direction without urgency. Hollows. Thirty, perhaps forty. Half are wearing "
        "the remnants of civilian clothing — Undergrove workers, probably, from before "
        "the Rot established itself here. Three are wearing Seeker gear. You recognize "
        "the loadout: standard deep-run kit, amber-inlaid pauldrons, the blade configuration "
        "favored by third-tier Seekers. You do not recognize the faces. The column does not "
        "react to your presence. It continues. The Choir hums louder where they pass."
    ),
    "breach_point": (
        "The wound in the boundary is still open. Root matter curls back from its edges "
        "the way skin curls from a burn — reactive, agonized, the amber veins in the "
        "exposed wood gone dark and dry. Through the breach, the Rot is visible as a "
        "slow fog, not moving with air currents but with purpose, a directed seep. "
        "The breach is not large. A person could pass through it if they chose to. "
        "The root matter on the other side of the boundary is different: denser, darker, "
        "grown with an intention that the Undergrove root mass does not share. "
        "Something made this opening from the other side."
    )
}


# =============================================================================
# THE UNDERGROVE ADAPTER (RulesetAdapter Implementation)
# =============================================================================

class UndergroveAdapter(RulesetAdapter):
    """
    Zone 7: The Undergrove content population adapter.

    This adapter generates biome-specific content for Undergrove rooms.

    ARCHITECTURE COMPLIANCE:
        - Heart logic only: No text generation
        - Deterministic: Seeded RNG per room
        - Composable: Works with any CodexMapEngine output

    ZONE UNIQUE MECHANICS:
        - Normal rooms have 30% base ingredient drop chance (doubled vs. surface zones)
        - Hollow Drift rooms may spawn Hollows wearing named Seeker gear
        - Choir Resonance tag triggers psychic hazard generation

    Content Structure:
        {
            "biome_tags": [UndergroveBiome.ROOT_TANGLE, ...],
            "enemies": [{"name": str, "hp": int, "defense": int, "damage": str}, ...],
            "loot": [{"name": str, "slot": str, "tier": int, "special": str}, ...],
            "hazards": [{"name": str, "type": str, "stat": str, "dc": int, "effect": str}],
            "interactive": [...]
        }

    NOTE: The "description" field is intentionally omitted. That's the Brain's job.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the Undergrove adapter.

        Args:
            seed: Random seed for deterministic generation (default: random)
        """
        self.seed = seed if seed is not None else random.randint(0, 999999)

    def populate_room(self, room: RoomNode) -> "PopulatedRoom":
        """
        Populate a room with Undergrove-specific content.

        Args:
            room: Geometry node from map engine

        Returns:
            PopulatedRoom with Undergrove biome content
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
            List of UndergroveBiome values (as strings for serialization)
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
        for tag, weight in UNDERGROVE_BIOME_WEIGHTS.items():
            if tag.value not in tags and rng.random() < weight:
                tags.append(tag.value)

        # Ensure at least one tag
        if not tags:
            tags.append(UndergroveBiome.ROOT_TANGLE.value)

        return tags

    # ─────────────────────────────────────────────────────────────────────
    # ROOM TYPE POPULATION METHODS
    # ─────────────────────────────────────────────────────────────────────

    def _populate_start_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate the starting room (descent entry — safe, no enemies)."""
        # Start room has no enemies — the Seekers who went first cleared it
        # Small chance of a left-behind ingredient or consumable
        if rng.random() < 0.6:
            content["loot"].append(rng.choice(UNDERGROVE_LOOT[1]))

    def _populate_boss_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate a boss encounter room."""
        # Single boss enemy
        boss_template = UNDERGROVE_BOSSES.get(room.tier, UNDERGROVE_BOSSES[1])
        boss = boss_template.copy()
        boss["is_boss"] = True
        content["enemies"].append(boss)

        # Boss rooms always have high-tier loot
        loot_tier = min(4, room.tier + 1)
        loot_count = rng.randint(2, 3)
        content["loot"].extend(
            [rng.choice(UNDERGROVE_LOOT[loot_tier]).copy() for _ in range(loot_count)]
        )

        # Choir Resonance hazard is guaranteed in boss rooms (physical song pressure)
        content["hazards"].append({
            "name": "Choir Pulse",
            "type": "environmental",
            "stat": "Aether",
            "dc": 11 + room.tier * 2,
            "effect": f"{room.tier}d4 psychic damage per round; Wits -1 until end of encounter"
        })

    def _populate_treasure_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate a nutrient pool cache room (guarded or locked)."""
        # Unlocked caches may have a guardian — compost-fed or leech-cluster
        if not room.is_locked:
            enemy_count = rng.randint(1, 2)
            enemy_pool = UNDERGROVE_ENEMIES.get(room.tier, UNDERGROVE_ENEMIES[1])
            content["enemies"].extend(
                [rng.choice(enemy_pool).copy() for _ in range(enemy_count)]
            )

        # Multiple loot items — nutrient pool processing enriches everything
        loot_count = rng.randint(2, 4)
        loot_pool = UNDERGROVE_LOOT.get(room.tier, UNDERGROVE_LOOT[1])
        content["loot"].extend([rng.choice(loot_pool).copy() for _ in range(loot_count)])

        # Nutrient pool is always available as an interactive element
        content["interactive"].append({
            "type": "harvestable",
            "target": "nutrient pool",
            "stat": "Wits",
            "dc": 10 + room.tier,
            "reward": f"Rot-Processed Ingredient x{rng.randint(1, 3)} (crafting tier {room.tier})"
        })

    def _populate_secret_room(self, room: RoomNode, content: dict, rng: random.Random):
        """Populate a Failed Grove fossil chamber (high value, silence)."""
        # High-tier loot — Memory Seeds and fossil-derived materials
        loot_tier = min(4, room.tier + 1)
        loot_pool = UNDERGROVE_LOOT.get(loot_tier, UNDERGROVE_LOOT[1])
        content["loot"].extend([rng.choice(loot_pool).copy() for _ in range(2)])

        # Always contains Memory Seed (Undergrove strain) in higher tiers
        if room.tier >= 3:
            content["loot"].append({
                "name": "Memory Seed (Undergrove Strain)",
                "slot": "Neck",
                "tier": 3,
                "special": "Unlock blueprint — Undergrove composite gear set (Tier 3 recipe)"
            })

        # Fossil chamber is always free of Choir resonance (the fossils absorb it)
        # No hazards — the silence is the mechanic
        # Small chance of a dormant Hollow guardian that activates on loot touch
        if rng.random() < 0.35:
            ancient_hollow = UNDERGROVE_ENEMIES[4][0].copy()
            ancient_hollow["note"] = (
                "Dormant at room entry; activates when loot is touched — "
                "Wits DC 14 to notice before triggering"
            )
            content["enemies"].append(ancient_hollow)

    def _populate_normal_room(self, room: RoomNode, content: dict, rng: random.Random):
        """
        Populate a standard room (balanced enemies/loot/hazards).

        ZONE UNIQUE: Normal rooms have 30% base ingredient drop chance —
        doubled versus surface zone baseline (15%). The Undergrove is dense
        with processable organic material.

        ZONE UNIQUE: Hollow Drift rooms may generate enemies wearing named gear.
        """
        tags = content["biome_tags"]

        # Enemy spawns (0-2 enemies)
        if room.room_type != RoomType.CORRIDOR:
            # Hollow Drift rooms have higher enemy density and named gear chance
            if UndergroveBiome.HOLLOW_DRIFT.value in tags:
                enemy_count = rng.randint(1, 3)
                enemy_pool = UNDERGROVE_ENEMIES.get(room.tier, UNDERGROVE_ENEMIES[1])
                for _ in range(enemy_count):
                    enemy = rng.choice(enemy_pool).copy()
                    # 25% chance a Hollow in a Drift room wears named Seeker gear
                    if enemy["name"] == "Drift Hollow" and rng.random() < 0.25:
                        named_item = rng.choice(UNDERGROVE_LOOT.get(room.tier, UNDERGROVE_LOOT[1]))
                        enemy["wearing"] = named_item["name"]
                        enemy["loot_on_defeat"] = named_item
                    content["enemies"].append(enemy)
            else:
                enemy_count = rng.randint(0, 2)
                enemy_pool = UNDERGROVE_ENEMIES.get(room.tier, UNDERGROVE_ENEMIES[1])
                content["enemies"].extend(
                    [rng.choice(enemy_pool).copy() for _ in range(enemy_count)]
                )

        # Loot: 30% base chance (zone unique — doubled ingredient density)
        if rng.random() < 0.30:
            loot_pool = UNDERGROVE_LOOT.get(room.tier, UNDERGROVE_LOOT[1])
            content["loot"].append(rng.choice(loot_pool).copy())

        # Ingredient drop (separate from gear loot): 30% chance in any room
        if rng.random() < 0.30:
            ingredient_tier = max(1, room.tier)
            content["loot"].append({
                "name": f"Rot-Processed Ingredient (T{ingredient_tier})",
                "slot": "Consumable",
                "tier": ingredient_tier,
                "special": "Crafting material (Undergrove composite recipes)"
            })

        # Hazards: 25% chance (higher than surface zones — this place is actively hostile)
        if rng.random() < 0.25:
            # If Choir Resonance tag present, weight toward psychic hazard
            if UndergroveBiome.CHOIR_RESONANCE.value in tags:
                hazard = UNDERGROVE_HAZARDS[2]  # Choir Pulse
            else:
                hazard = rng.choice(UNDERGROVE_HAZARDS)

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

        Interactive elements are structural affordances (climbable, harvestable, etc.)
        NOT descriptions. The Brain will generate text for these later.
        """
        tags = content["biome_tags"]

        # ROOT_TANGLE → Traversal check (movement hazard)
        if UndergroveBiome.ROOT_TANGLE.value in tags:
            content["interactive"].append({
                "type": "traversal",
                "target": "root tangle",
                "stat": "Might",
                "dc": 7 + room.tier,
                "effect_on_fail": f"Restrained 1 round; {room.tier}d4 bludgeoning from root-crush"
            })

        # MYCELIUM_VEIN → Harvestable ingredient node
        if UndergroveBiome.MYCELIUM_VEIN.value in tags:
            content["interactive"].append({
                "type": "harvestable",
                "target": "mycelium vein",
                "stat": "Wits",
                "dc": 9 + room.tier,
                "reward": f"Mycelium Extract x{rng.randint(1, 2)} (healing ingredient, Tier {room.tier})"
            })

        # FAILED_GROVE_FOSSIL → Lore node (inspectable)
        if UndergroveBiome.FAILED_GROVE_FOSSIL.value in tags:
            content["interactive"].append({
                "type": "inspectable",
                "target": "failed grove fossil",
                "stat": "Wits",
                "dc": 12 + room.tier,
                "reward": "Lore Fragment — pre-Four Grove taxonomy entry"
            })

        # ROOT_ROAD_JUNCTION → Sealed passage (may be forced)
        if UndergroveBiome.ROOT_ROAD_JUNCTION.value in tags:
            grove_signatures = ["Burnwillow", "Verdhollow", "Cindergrove", "Ashgrove"]
            rng.shuffle(grove_signatures)
            content["interactive"].append({
                "type": "sealed_passage",
                "target": "root road junction",
                "grove_signatures": grove_signatures,
                "stat": "Might",
                "dc": 14 + room.tier,
                "effect_on_success": "Opens sealed passage to adjacent zone segment"
            })

        # CHOIR_RESONANCE → Resonance reading (Aether check for intel)
        if UndergroveBiome.CHOIR_RESONANCE.value in tags:
            content["interactive"].append({
                "type": "commune",
                "target": "choir resonance",
                "stat": "Aether",
                "dc": 13 + room.tier,
                "reward": "Sense direction of nearest boss room; count enemies in adjacent rooms"
            })

        # NUTRIENT_POOL → Harvestable (with risk)
        if UndergroveBiome.NUTRIENT_POOL.value in tags and room.room_type != RoomType.TREASURE:
            content["interactive"].append({
                "type": "harvestable",
                "target": "nutrient pool",
                "stat": "Wits",
                "dc": 10 + room.tier,
                "reward": f"Rot-Processed Ingredient x{rng.randint(1, 2)} (Tier {room.tier})",
                "risk": f"On fail: Sinkhole — Grit DC {10 + room.tier} or {room.tier}d6 acid + Weakened"
            })

        # BREACH_POINT → Inspectable wound (Wits for intel, high risk)
        if UndergroveBiome.BREACH_POINT.value in tags:
            content["interactive"].append({
                "type": "inspectable",
                "target": "breach point",
                "stat": "Wits",
                "dc": 15 + room.tier,
                "reward": "Identify what created the breach (enemy type or Grove event)",
                "risk": f"On fail: Decomposition Mist — Grit DC {11 + room.tier} or lose {room.tier} max HP until rest"
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
        enemies = UNDERGROVE_ENEMIES.get(tier, UNDERGROVE_ENEMIES[1])
        return [enemy["name"] for enemy in enemies]

    def get_loot_pool(self, tier: int) -> List[str]:
        """
        Get list of loot item names for a given tier.

        Args:
            tier: Difficulty tier (1-4)

        Returns:
            List of item names
        """
        loot = UNDERGROVE_LOOT.get(tier, UNDERGROVE_LOOT[1])
        return [item["name"] for item in loot]


# =============================================================================
# STANDALONE TEST & DEMO
# =============================================================================

def run_demo():
    """Demonstrate the Undergrove zone generator using UndergroveAdapter directly."""
    print("=" * 70)
    print("ZONE 7: THE UNDERGROVE - PROCEDURAL GENERATOR TEST")
    print("=" * 70)

    print("\n[GENERATION]")
    map_engine = CodexMapEngine(seed=777)
    graph = map_engine.generate(
        width=50, height=50, min_room_size=5, max_depth=3,
        system_id="burnwillow",
    )
    adapter = UndergroveAdapter(seed=777)
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
                wearing = f" [wearing: {enemy['wearing']}]" if 'wearing' in enemy else ""
                print(f"  - {enemy['name']}{boss}{wearing}: {enemy['hp']} HP, DEF {enemy['defense']}, DMG {enemy['damage']}")

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
    tag_counts: Dict[str, int] = {}
    for room in zone['rooms']:
        for tag in room['biome_tags']:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print("Biome Tag Distribution:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / zone['total_rooms']) * 100
        print(f"  {tag:30s}: {count:2d} rooms ({percentage:5.1f}%)")

    total_enemies = sum(len(room['enemies']) for room in zone['rooms'])
    total_loot = sum(len(room['loot']) for room in zone['rooms'])
    total_hazards = sum(len(room['hazards']) for room in zone['rooms'])

    print(f"\nTotal Enemies: {total_enemies}")
    print(f"Total Loot: {total_loot}")
    print(f"Total Hazards: {total_hazards}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()

"""
atmosphere.py - Thermal Narrative Layer for Burnwillow
======================================================

Layers sensory tone onto room descriptions based on tier depth.
Each tier maps to a ThermalTone that defines:
  - SENSORY_LEADS: Prepended atmospheric sentences
  - LEXICON: Word substitutions that shift vocabulary by depth

Tier Mapping:
  Tier 1 (WARM)     — Industrial decay, rust, oil, heat
  Tier 2 (WITHERED) — Cold machinery, silence, stillness
  Tier 3 (COLD)     — Arcane chill, rune-light, resonance
  Tier 4 (ROT)      — Blight corruption, reality fracture
"""

import random
import re
from enum import Enum
from typing import Dict, List, Tuple


class ThermalTone(Enum):
    HOMECOMING = 0  # Return Gate: warmth, safety, relief
    WARM = 1       # Tier 1: Industrial decay, rust, oil, heat
    WITHERED = 2   # Tier 2: Cold machinery, silence, stillness
    COLD = 3       # Tier 3: Arcane chill, rune-light, resonance
    ROT = 4        # Tier 4: Blight corruption, reality fracture
    ARCANE = 5     # D&D portals: humming, ozone, visual distortion
    GOTHIC = 6     # Ashburn borders: scratch of trees, Lunar Filter
    CANOPY_LOW = 7    # Trunk interior: sap, bark, amber light, enclosed
    CANOPY_MID = 8    # Branch network: wind, open air, dappled light, vertigo
    CANOPY_HIGH = 9   # Crown canopy: blinding gold, thin air, exposed
    CANOPY_CROWN = 10 # The Crown itself: pure sap-light, sacred/ancient


# ---------------------------------------------------------------------------
# SENSORY LEADS — prepended to base description
# ---------------------------------------------------------------------------

SENSORY_LEADS: Dict[ThermalTone, List[str]] = {
    ThermalTone.HOMECOMING: [
        "The smell of pine sap and the distant sound of village bells replace the frozen silence of the deep.",
        "Warmth seeps back into your fingers. The air tastes clean for the first time in hours.",
        "A draft carries hearth-smoke and the murmur of voices. Civilization is close.",
        "The oppressive weight lifts from your chest. You can breathe again.",
    ],
    ThermalTone.WARM: [
        "Warm sap weeps from the walls, amber and slow.",
        "The air is thick with the scent of heated resin and old wood.",
        "A furnace draft pushes through the corridor, carrying amber-tinged smoke.",
        "Heat pulses through the roots overhead. The Burnwillow breathes here.",
    ],
    ThermalTone.WITHERED: [
        "The warmth has bled from this place.",
        "Dust hangs motionless — nothing stirs.",
        "A grey stillness fills the chamber, heavy and flat.",
        "Your breath comes out thin. The cold has settled deep.",
    ],
    ThermalTone.COLD: [
        "Cold bites through your gloves.",
        "Frost traces the edges of every surface.",
        "The air hums with residual Aether — sharp, electric.",
        "Your teeth ache. The temperature dropped the moment you crossed the threshold.",
    ],
    ThermalTone.ROT: [
        "The Blight-smell hits you — sweetrot and copper.",
        "Reality sags here, heavy and rotten.",
        "Your skin crawls. The air tastes wrong — metallic and alive.",
        "Something pulses in the walls. The stone is warm and shouldn't be.",
    ],
    ThermalTone.ARCANE: [
        "The air hums at a frequency that sets your fillings buzzing. Ozone crackles.",
        "A shimmering heat-haze ripples across the stone, though the air is cold.",
        "Your shadow splits into three. The light here comes from no visible source.",
        "Static lifts the hair on your arms. The Weave is thin here — dangerously thin.",
    ],
    ThermalTone.GOTHIC: [
        "Branches claw at the shutters. The scratch is rhythmic, almost deliberate.",
        "The Lunar Filter presses down — a weight on your chest, silver and suffocating.",
        "Fog curls at ankle height, too thick, too still. It does not move with the draft.",
        "A bell tolls somewhere distant. You count the strikes. There is always one too many.",
    ],
    ThermalTone.CANOPY_LOW: [
        "Warm sap seeps through bark fissures, amber and slow. The trunk groans around you.",
        "The air is thick with resin-scent. Heartwood pillars rise into darkness above.",
        "Golden light filters through cracks in the bark. The tree breathes here — you feel it.",
        "Sap veins glow faintly in the walls. The wood is warm and alive under your palm.",
    ],
    ThermalTone.CANOPY_MID: [
        "Wind tears through gaps in the branch network. The ground is far below.",
        "Dappled light dances across the bark platform. A bird screams somewhere above.",
        "The branch sways underfoot. Don't look down. The canopy stretches in every direction.",
        "Your stomach lurches. The wind is stronger here, and the footing is narrow.",
    ],
    ThermalTone.CANOPY_HIGH: [
        "Blinding gold pours through the leaf ceiling. The air is thin and tastes of ozone.",
        "You can see the horizon through gaps in the foliage. The world is very small below.",
        "The wind is a constant roar. Leaves the size of shields snap past like thrown blades.",
        "Sunlight hits the sap-veins and they ignite with inner fire. Everything glows.",
    ],
    ThermalTone.CANOPY_CROWN: [
        "The Crown opens above you — a cathedral of golden light and ancient wood.",
        "Sap-light is everywhere. It pulses slow, rhythmic, like a heartbeat.",
        "The air hums with something old and alive. This place was not made for you.",
        "Pure amber radiance. The Burnwillow's crown is a living furnace of golden fire.",
    ],
}


# ---------------------------------------------------------------------------
# LEXICON — word substitutions per tone
# ---------------------------------------------------------------------------

LEXICON: Dict[ThermalTone, List[Tuple[str, str]]] = {
    ThermalTone.HOMECOMING: [
        ("maw", "door"),
        ("membrane", "walls"),
        ("scarred ground", "floor"),
        ("sick glow", "light"),
    ],
    ThermalTone.WARM: [
        ("door", "hatch"),
        ("walls", "hull plates"),
        ("floor", "deck plates"),
        ("ceiling", "overhead"),
    ],
    ThermalTone.WITHERED: [
        ("door", "gate"),
        ("stone walls", "stonework"),
        ("walls", "stonework"),
        ("floor", "flagstone"),
        ("light", "grey light"),
    ],
    ThermalTone.COLD: [
        ("door", "seal"),
        ("walls", "wards"),
        ("floor", "frost-cracked stone"),
        ("light", "rune-light"),
    ],
    ThermalTone.ROT: [
        ("door", "maw"),
        ("walls", "membrane"),
        ("floor", "scarred ground"),
        ("light", "sick glow"),
    ],
    ThermalTone.ARCANE: [
        ("door", "threshold"),
        ("walls", "wards"),
        ("floor", "inscribed stone"),
        ("light", "arcane radiance"),
    ],
    ThermalTone.GOTHIC: [
        ("door", "iron gate"),
        ("walls", "crumbling masonry"),
        ("floor", "flagstone"),
        ("light", "guttering candlelight"),
    ],
    ThermalTone.CANOPY_LOW: [
        ("door", "bark hatch"),
        ("walls", "trunk walls"),
        ("floor", "heartwood platform"),
        ("light", "sap-glow"),
    ],
    ThermalTone.CANOPY_MID: [
        ("door", "branch gap"),
        ("walls", "woven branches"),
        ("floor", "bark walkway"),
        ("light", "dappled sun"),
    ],
    ThermalTone.CANOPY_HIGH: [
        ("door", "leaf curtain"),
        ("walls", "wind-stripped boughs"),
        ("floor", "swaying platform"),
        ("light", "raw sunlight"),
    ],
    ThermalTone.CANOPY_CROWN: [
        ("door", "sap-sealed gate"),
        ("walls", "living wood"),
        ("floor", "crown platform"),
        ("light", "sap-fire"),
    ],
}


def thermal_narrative_modifier(
    description: str, tier: int, rng: random.Random,
    tone_override: "ThermalTone | None" = None,
) -> str:
    """
    Enrich a room description with sensory tone based on tier depth.

    1. Maps tier (1-4) to a ThermalTone (or uses tone_override)
    2. Prepends a random sensory lead-in from that tone's pool
    3. Applies lexicon word substitutions to the base description
    4. Returns the enriched description

    Args:
        description: Base room description text
        tier: Dungeon tier (1-4)
        rng: Seeded Random instance for deterministic output
        tone_override: If set, use this tone instead of tier-derived one

    Returns:
        Enriched description string
    """
    if tone_override is not None:
        tone = tone_override
    else:
        tone = ThermalTone(max(0, min(4, tier)))

    # Prepend sensory lead
    leads = SENSORY_LEADS[tone]
    lead = rng.choice(leads)

    # Apply lexicon substitutions (word-boundary aware to avoid partial matches)
    enriched = description
    for old_word, new_word in LEXICON[tone]:
        enriched = re.sub(r'\b' + re.escape(old_word) + r'\b', new_word, enriched)

    return f"{lead} {enriched}"


# ---------------------------------------------------------------------------
# Style markers -- inject world-level architecture/fashion into descriptions
# ---------------------------------------------------------------------------

STYLE_TEMPLATES = [
    "The {material} walls bear {motif}.",
    "Above, the ceiling is built in {building_style} fashion \u2014 {motif}.",
    "A figure in {textile} passes, {accessory} glinting.",
    "{clothing_style} garments hang from a hook \u2014 {textile}, fastened with {accessory}.",
]


def inject_style_markers(
    description: str,
    architecture: list,
    rng: random.Random,
) -> str:
    """Append a world-style clause to a room description.

    Args:
        description: Base room description text.
        architecture: List of AestheticProfile dicts or dataclass instances.
        rng: Seeded Random instance for deterministic output.

    Returns:
        Description with an appended style clause, or unchanged if
        *architecture* is empty/None.
    """
    if not architecture:
        return description

    profile = rng.choice(architecture)
    template = rng.choice(STYLE_TEMPLATES)

    # Accept both dict and dataclass
    if hasattr(profile, "to_dict"):
        fields = profile.to_dict()
    elif isinstance(profile, dict):
        fields = profile
    else:
        return description

    try:
        clause = template.format(**fields)
    except KeyError:
        return description

    return f"{description} {clause}"

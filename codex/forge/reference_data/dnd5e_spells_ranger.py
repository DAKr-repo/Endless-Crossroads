"""
codex.forge.reference_data.dnd5e_spells_ranger
===============================================
Ranger spell list for D&D 5e, levels 1-5.
Source: Player's Handbook (PHB), Xanathar's Guide to Everything (XGE),
        Tasha's Cauldron of Everything (TCE).

Rangers are half-casters (Wisdom-based, spells known).
They have no cantrips and access spells up to 5th level.
Ranger Conclave spells are NOT included here — this is the base class list only.
"""

SPELLS: dict = {
    0: [],  # Rangers have no cantrips
    1: [
        "Absorb Elements",
        "Alarm",
        "Animal Friendship",
        "Beast Bond",
        "Cure Wounds",
        "Detect Magic",
        "Detect Poison and Disease",
        "Ensnaring Strike",
        "Fog Cloud",
        "Goodberry",
        "Hail of Thorns",
        "Hunter's Mark",
        "Jump",
        "Longstrider",
        "Speak with Animals",
        "Zephyr Strike",
    ],
    2: [
        "Aid",
        "Animal Messenger",
        "Barkskin",
        "Beast Sense",
        "Cordon of Arrows",
        "Darkvision",
        "Find Traps",
        "Gust of Wind",
        "Lesser Restoration",
        "Locate Animals or Plants",
        "Locate Object",
        "Pass Without Trace",
        "Protection from Poison",
        "Silence",
        "Spike Growth",
        "Summon Beast",
    ],
    3: [
        "Conjure Animals",
        "Conjure Barrage",
        "Daylight",
        "Flame Arrows",
        "Lightning Arrow",
        "Nondetection",
        "Plant Growth",
        "Protection from Energy",
        "Speak with Plants",
        "Summon Fey",
        "Water Breathing",
        "Water Walk",
        "Wind Wall",
    ],
    4: [
        "Conjure Woodland Beings",
        "Freedom of Movement",
        "Grasping Vine",
        "Guardian of Nature",
        "Locate Creature",
        "Stoneskin",
        "Summon Elemental",
    ],
    5: [
        "Commune with Nature",
        "Conjure Volley",
        "Swift Quiver",
        "Tree Stride",
        "Wrath of Nature",
    ],
}

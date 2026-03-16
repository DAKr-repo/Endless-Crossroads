"""
codex.forge.reference_data.dnd5e_spells_paladin
================================================
Paladin spell list for D&D 5e, levels 1-5.
Source: Player's Handbook (PHB), Xanathar's Guide to Everything (XGE),
        Tasha's Cauldron of Everything (TCE).

Paladins are half-casters (Charisma-based, prepared).
They have no cantrips and access spells up to 5th level.
Oath spells are NOT included here — this is the base class list only.
"""

SPELLS: dict = {
    0: [],  # Paladins have no cantrips
    1: [
        "Bless",
        "Command",
        "Compelled Duel",
        "Cure Wounds",
        "Detect Evil and Good",
        "Detect Magic",
        "Detect Poison and Disease",
        "Divine Favor",
        "Heroism",
        "Protection from Evil and Good",
        "Purify Food and Drink",
        "Searing Smite",
        "Shield of Faith",
        "Thunderous Smite",
        "Wrathful Smite",
    ],
    2: [
        "Aid",
        "Branding Smite",
        "Find Steed",
        "Gentle Repose",
        "Lesser Restoration",
        "Locate Object",
        "Magic Weapon",
        "Prayer of Healing",
        "Protection from Poison",
        "Warding Bond",
        "Zone of Truth",
    ],
    3: [
        "Aura of Vitality",
        "Blinding Smite",
        "Create Food and Water",
        "Crusader's Mantle",
        "Daylight",
        "Dispel Magic",
        "Elemental Weapon",
        "Magic Circle",
        "Remove Curse",
        "Revivify",
        "Spirit Shroud",
    ],
    4: [
        "Aura of Life",
        "Aura of Purity",
        "Banishment",
        "Death Ward",
        "Find Greater Steed",
        "Locate Creature",
        "Staggering Smite",
    ],
    5: [
        "Banishing Smite",
        "Circle of Power",
        "Destructive Wave",
        "Dispel Evil and Good",
        "Geas",
        "Holy Weapon",
        "Raise Dead",
        "Summon Celestial",
    ],
}

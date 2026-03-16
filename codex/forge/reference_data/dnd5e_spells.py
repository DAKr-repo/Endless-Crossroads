"""
codex.forge.reference_data.dnd5e_spells
=========================================
Hardcoded D&D 5e PHB / Xanathar's / Tasha's / Eberron spell and equipment
reference tables used by the character creation wizard and spellcasting
validation layer.

Contains four static dictionaries:
  - SPELL_LISTS: Per-class spell lists keyed by spell level (0-9).
                 Aggregated from per-class files (dnd5e_spells_{class}.py).
  - SPELL_SLOT_TABLE: Full caster spell slots by character level.
  - HALF_CASTER_SLOT_TABLE: Half caster spell slots by character level.
  - WARLOCK_SLOT_TABLE: Warlock pact magic slots by character level.
  - SPELLCASTING: Per-class spellcasting metadata (type, ability, progression).
  - STARTING_EQUIPMENT: Per-class equipment packages and gold alternative.
  - EQUIPMENT_CATALOG: Canonical item data (weapons, armor, adventuring packs).
"""

# ---------------------------------------------------------------------------
# 1. SPELL_LISTS
# ---------------------------------------------------------------------------
# Per-class spell files provide levels 0-9 (or 1-5 for half-casters).
# Imported here and aggregated into SPELL_LISTS for backward compatibility.
# ---------------------------------------------------------------------------

from codex.forge.reference_data.dnd5e_spells_bard import SPELLS as _BARD_SPELLS
from codex.forge.reference_data.dnd5e_spells_cleric import SPELLS as _CLERIC_SPELLS
from codex.forge.reference_data.dnd5e_spells_druid import SPELLS as _DRUID_SPELLS
from codex.forge.reference_data.dnd5e_spells_paladin import SPELLS as _PALADIN_SPELLS
from codex.forge.reference_data.dnd5e_spells_ranger import SPELLS as _RANGER_SPELLS
from codex.forge.reference_data.dnd5e_spells_sorcerer import SPELLS as _SORCERER_SPELLS
from codex.forge.reference_data.dnd5e_spells_warlock import SPELLS as _WARLOCK_SPELLS
from codex.forge.reference_data.dnd5e_spells_wizard import SPELLS as _WIZARD_SPELLS
from codex.forge.reference_data.dnd5e_spells_artificer import SPELLS as _ARTIFICER_SPELLS

SPELL_LISTS: dict = {
    "bard": _BARD_SPELLS,
    "cleric": _CLERIC_SPELLS,
    "druid": _DRUID_SPELLS,
    "paladin": _PALADIN_SPELLS,
    "ranger": _RANGER_SPELLS,
    "sorcerer": _SORCERER_SPELLS,
    "warlock": _WARLOCK_SPELLS,
    "wizard": _WIZARD_SPELLS,
    "artificer": _ARTIFICER_SPELLS,
}

# ---------------------------------------------------------------------------
# 1b. SPELL SLOT TABLES
# ---------------------------------------------------------------------------

# Full caster: character level -> {spell_level: num_slots}
SPELL_SLOT_TABLE: dict = {
    1:  {1: 2},
    2:  {1: 3},
    3:  {1: 4, 2: 2},
    4:  {1: 4, 2: 3},
    5:  {1: 4, 2: 3, 3: 2},
    6:  {1: 4, 2: 3, 3: 3},
    7:  {1: 4, 2: 3, 3: 3, 4: 1},
    8:  {1: 4, 2: 3, 3: 3, 4: 2},
    9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}

# Half caster: uses caster_level = class_level // 2, max 5th level slots
HALF_CASTER_SLOT_TABLE: dict = {
    lvl: {k: v for k, v in SPELL_SLOT_TABLE.get(max(1, lvl // 2), {}).items() if k <= 5}
    for lvl in range(1, 21)
}

# Warlock Pact Magic: all slots same level, recover on short rest
WARLOCK_SLOT_TABLE: dict = {
    1: {"slots": 1, "slot_level": 1},
    2: {"slots": 2, "slot_level": 1},
    3: {"slots": 2, "slot_level": 2},
    4: {"slots": 2, "slot_level": 2},
    5: {"slots": 2, "slot_level": 3},
    6: {"slots": 2, "slot_level": 3},
    7: {"slots": 2, "slot_level": 4},
    8: {"slots": 2, "slot_level": 4},
    9: {"slots": 2, "slot_level": 5},
    10: {"slots": 2, "slot_level": 5},
    11: {"slots": 3, "slot_level": 5},
    12: {"slots": 3, "slot_level": 5},
    13: {"slots": 3, "slot_level": 5},
    14: {"slots": 3, "slot_level": 5},
    15: {"slots": 3, "slot_level": 5},
    16: {"slots": 3, "slot_level": 5},
    17: {"slots": 4, "slot_level": 5},
    18: {"slots": 4, "slot_level": 5},
    19: {"slots": 4, "slot_level": 5},
    20: {"slots": 4, "slot_level": 5},
}

# ---------------------------------------------------------------------------
# 2. SPELLCASTING
# ---------------------------------------------------------------------------
# Keyed by class name.  Fields:
#   type         -- "known" (fixed list) or "prepared" (ability + level formula)
#   ability      -- spellcasting ability (lowercase)
#   cantrips     -- {character_level: cantrips_known} — only levels where the
#                   count increases are listed; absent for half-casters that
#                   have no cantrips (paladin, ranger).
#   spells_known -- {character_level: total_spells_known} — "known" classes only.
#   half_caster  -- True for paladin / ranger / artificer (spell slots follow
#                   the half-caster progression table).
# ---------------------------------------------------------------------------

SPELLCASTING: dict = {
    "bard": {
        "type": "known",
        "ability": "charisma",
        "cantrips": {1: 2, 4: 3, 10: 4},
        "spells_known": {
            1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9,
            7: 10, 8: 11, 9: 12, 10: 14, 11: 15,
            13: 16, 14: 18, 15: 19, 17: 20, 18: 22,
        },
    },
    "cleric": {
        "type": "prepared",
        "ability": "wisdom",
        "cantrips": {1: 3, 4: 4, 10: 5},
    },
    "druid": {
        "type": "prepared",
        "ability": "wisdom",
        "cantrips": {1: 2, 4: 3, 10: 4},
    },
    "paladin": {
        "type": "prepared",
        "ability": "charisma",
        "half_caster": True,
    },
    "ranger": {
        "type": "known",
        "ability": "wisdom",
        "half_caster": True,
        "spells_known": {
            2: 2, 3: 3, 5: 4, 7: 5, 9: 6,
            11: 7, 13: 8, 15: 9, 17: 10, 19: 11,
        },
    },
    "sorcerer": {
        "type": "known",
        "ability": "charisma",
        "cantrips": {1: 4, 4: 5, 10: 6},
        "spells_known": {
            1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7,
            7: 8, 8: 9, 9: 10, 10: 11, 11: 12,
            13: 13, 15: 14, 17: 15,
        },
    },
    "warlock": {
        "type": "known",
        "ability": "charisma",
        "cantrips": {1: 2, 4: 3, 10: 4},
        "spells_known": {
            1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7,
            7: 8, 8: 9, 9: 10, 11: 11, 13: 12,
            15: 13, 17: 14, 19: 15,
        },
    },
    "wizard": {
        "type": "prepared",
        "ability": "intelligence",
        "cantrips": {1: 3, 4: 4, 10: 5},
    },
    "artificer": {
        "type": "prepared",
        "ability": "intelligence",
        "half_caster": True,
        "cantrips": {1: 2, 10: 3, 14: 4},
    },
}

# ---------------------------------------------------------------------------
# 3. STARTING_EQUIPMENT
# ---------------------------------------------------------------------------
# Keyed by class name.  Each value is a dict with:
#   packages         -- list of {"name": str, "items": [str, ...]}
#   gold_alternative -- {"dice": int, "multiplier": int}
#                       Roll <dice>d4, multiply by <multiplier> for starting gp.
#                       multiplier=1 means no multiplication (e.g., monk's 5d4).
# ---------------------------------------------------------------------------

STARTING_EQUIPMENT: dict = {
    "barbarian": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Greataxe",
                    "2 Handaxes",
                    "Explorer's Pack",
                    "4 Javelins",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Martial melee weapon",
                    "2 Handaxes",
                    "Explorer's Pack",
                    "4 Javelins",
                ],
            },
        ],
        "gold_alternative": {"dice": 2, "multiplier": 10},
    },
    "bard": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Rapier",
                    "Diplomat's Pack",
                    "Lute",
                    "Leather armor",
                    "Dagger",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Longsword",
                    "Entertainer's Pack",
                    "Musical instrument",
                    "Leather armor",
                    "Dagger",
                ],
            },
        ],
        "gold_alternative": {"dice": 5, "multiplier": 10},
    },
    "cleric": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Mace",
                    "Scale mail",
                    "Light crossbow",
                    "20 bolts",
                    "Priest's Pack",
                    "Shield",
                    "Holy symbol",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Warhammer",
                    "Chain mail",
                    "Light crossbow",
                    "20 bolts",
                    "Explorer's Pack",
                    "Shield",
                    "Holy symbol",
                ],
            },
        ],
        "gold_alternative": {"dice": 5, "multiplier": 10},
    },
    "druid": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Wooden shield",
                    "Scimitar",
                    "Leather armor",
                    "Explorer's Pack",
                    "Druidic focus",
                ],
            },
        ],
        "gold_alternative": {"dice": 2, "multiplier": 10},
    },
    "fighter": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Chain mail",
                    "Martial weapon",
                    "Shield",
                    "Light crossbow",
                    "20 bolts",
                    "Dungeoneer's Pack",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Leather armor",
                    "Longbow",
                    "20 arrows",
                    "Two martial weapons",
                    "Explorer's Pack",
                ],
            },
        ],
        "gold_alternative": {"dice": 5, "multiplier": 10},
    },
    "monk": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Shortsword",
                    "Dungeoneer's Pack",
                    "10 darts",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Simple weapon",
                    "Explorer's Pack",
                    "10 darts",
                ],
            },
        ],
        "gold_alternative": {"dice": 5, "multiplier": 1},
    },
    "paladin": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Martial weapon",
                    "Shield",
                    "5 Javelins",
                    "Priest's Pack",
                    "Chain mail",
                    "Holy symbol",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Two martial weapons",
                    "5 Javelins",
                    "Explorer's Pack",
                    "Chain mail",
                    "Holy symbol",
                ],
            },
        ],
        "gold_alternative": {"dice": 5, "multiplier": 10},
    },
    "ranger": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Scale mail",
                    "Two shortswords",
                    "Dungeoneer's Pack",
                    "Longbow",
                    "20 arrows",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Leather armor",
                    "Two simple melee weapons",
                    "Explorer's Pack",
                    "Longbow",
                    "20 arrows",
                ],
            },
        ],
        "gold_alternative": {"dice": 5, "multiplier": 10},
    },
    "rogue": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Rapier",
                    "Shortbow",
                    "20 arrows",
                    "Burglar's Pack",
                    "Leather armor",
                    "Two daggers",
                    "Thieves' tools",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Shortsword",
                    "Shortbow",
                    "20 arrows",
                    "Dungeoneer's Pack",
                    "Leather armor",
                    "Two daggers",
                    "Thieves' tools",
                ],
            },
        ],
        "gold_alternative": {"dice": 4, "multiplier": 10},
    },
    "sorcerer": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Light crossbow",
                    "20 bolts",
                    "Arcane focus",
                    "Dungeoneer's Pack",
                    "Two daggers",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Simple weapon",
                    "Arcane focus",
                    "Explorer's Pack",
                    "Two daggers",
                ],
            },
        ],
        "gold_alternative": {"dice": 3, "multiplier": 10},
    },
    "warlock": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Light crossbow",
                    "20 bolts",
                    "Arcane focus",
                    "Scholar's Pack",
                    "Leather armor",
                    "Simple weapon",
                    "Two daggers",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Simple weapon",
                    "Arcane focus",
                    "Dungeoneer's Pack",
                    "Leather armor",
                    "Simple weapon",
                    "Two daggers",
                ],
            },
        ],
        "gold_alternative": {"dice": 4, "multiplier": 10},
    },
    "wizard": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Quarterstaff",
                    "Arcane focus",
                    "Scholar's Pack",
                    "Spellbook",
                ],
            },
            {
                "name": "Package B",
                "items": [
                    "Dagger",
                    "Component pouch",
                    "Explorer's Pack",
                    "Spellbook",
                ],
            },
        ],
        "gold_alternative": {"dice": 4, "multiplier": 10},
    },
    "artificer": {
        "packages": [
            {
                "name": "Package A",
                "items": [
                    "Two simple weapons",
                    "Light crossbow",
                    "20 bolts",
                    "Studded leather armor",
                    "Thieves' tools",
                    "Dungeoneer's Pack",
                ],
            },
        ],
        "gold_alternative": {"dice": 5, "multiplier": 10},
    },
}

# ---------------------------------------------------------------------------
# 4. EQUIPMENT_CATALOG
# ---------------------------------------------------------------------------
# Categories: simple_melee, simple_ranged, martial_melee, martial_ranged,
#             armor, packs.
#
# Weapon fields: name, cost_gp (float), damage (str), weight_lb (float),
#                properties (list[str])
# Armor fields:  name, cost_gp (int/float), ac (str), strength_req (str|None),
#                stealth_disadvantage (bool), weight_lb (int), category (str)
# Pack fields:   name, cost_gp (int), contents (list[str])
# ---------------------------------------------------------------------------

EQUIPMENT_CATALOG: dict = {
    "simple_melee": [
        {
            "name": "Club",
            "cost_gp": 0.1,
            "damage": "1d4 bludgeoning",
            "weight_lb": 2,
            "properties": ["Light"],
        },
        {
            "name": "Dagger",
            "cost_gp": 2,
            "damage": "1d4 piercing",
            "weight_lb": 1,
            "properties": ["Finesse", "Light", "Thrown (20/60)"],
        },
        {
            "name": "Greatclub",
            "cost_gp": 0.2,
            "damage": "1d8 bludgeoning",
            "weight_lb": 10,
            "properties": ["Two-handed"],
        },
        {
            "name": "Handaxe",
            "cost_gp": 5,
            "damage": "1d6 slashing",
            "weight_lb": 2,
            "properties": ["Light", "Thrown (20/60)"],
        },
        {
            "name": "Javelin",
            "cost_gp": 0.5,
            "damage": "1d6 piercing",
            "weight_lb": 2,
            "properties": ["Thrown (30/120)"],
        },
        {
            "name": "Light hammer",
            "cost_gp": 2,
            "damage": "1d4 bludgeoning",
            "weight_lb": 2,
            "properties": ["Light", "Thrown (20/60)"],
        },
        {
            "name": "Mace",
            "cost_gp": 5,
            "damage": "1d6 bludgeoning",
            "weight_lb": 4,
            "properties": [],
        },
        {
            "name": "Quarterstaff",
            "cost_gp": 0.2,
            "damage": "1d6 bludgeoning",
            "weight_lb": 4,
            "properties": ["Versatile (1d8)"],
        },
        {
            "name": "Sickle",
            "cost_gp": 1,
            "damage": "1d4 slashing",
            "weight_lb": 2,
            "properties": ["Light"],
        },
        {
            "name": "Spear",
            "cost_gp": 1,
            "damage": "1d6 piercing",
            "weight_lb": 3,
            "properties": ["Thrown (20/60)", "Versatile (1d8)"],
        },
    ],
    "simple_ranged": [
        {
            "name": "Crossbow, light",
            "cost_gp": 25,
            "damage": "1d8 piercing",
            "weight_lb": 5,
            "properties": ["Ammunition (80/320)", "Loading", "Two-handed"],
        },
        {
            "name": "Dart",
            "cost_gp": 0.05,
            "damage": "1d4 piercing",
            "weight_lb": 0.25,
            "properties": ["Finesse", "Thrown (20/60)"],
        },
        {
            "name": "Shortbow",
            "cost_gp": 25,
            "damage": "1d6 piercing",
            "weight_lb": 2,
            "properties": ["Ammunition (80/320)", "Two-handed"],
        },
        {
            "name": "Sling",
            "cost_gp": 0.1,
            "damage": "1d4 bludgeoning",
            "weight_lb": 0,
            "properties": ["Ammunition (30/120)"],
        },
    ],
    "martial_melee": [
        {
            "name": "Battleaxe",
            "cost_gp": 10,
            "damage": "1d8 slashing",
            "weight_lb": 4,
            "properties": ["Versatile (1d10)"],
        },
        {
            "name": "Flail",
            "cost_gp": 10,
            "damage": "1d8 bludgeoning",
            "weight_lb": 2,
            "properties": [],
        },
        {
            "name": "Glaive",
            "cost_gp": 20,
            "damage": "1d10 slashing",
            "weight_lb": 6,
            "properties": ["Heavy", "Reach", "Two-handed"],
        },
        {
            "name": "Greataxe",
            "cost_gp": 30,
            "damage": "1d12 slashing",
            "weight_lb": 7,
            "properties": ["Heavy", "Two-handed"],
        },
        {
            "name": "Greatsword",
            "cost_gp": 50,
            "damage": "2d6 slashing",
            "weight_lb": 6,
            "properties": ["Heavy", "Two-handed"],
        },
        {
            "name": "Halberd",
            "cost_gp": 20,
            "damage": "1d10 slashing",
            "weight_lb": 6,
            "properties": ["Heavy", "Reach", "Two-handed"],
        },
        {
            "name": "Lance",
            "cost_gp": 10,
            "damage": "1d12 piercing",
            "weight_lb": 6,
            "properties": ["Reach", "Special"],
        },
        {
            "name": "Longsword",
            "cost_gp": 15,
            "damage": "1d8 slashing",
            "weight_lb": 3,
            "properties": ["Versatile (1d10)"],
        },
        {
            "name": "Maul",
            "cost_gp": 10,
            "damage": "2d6 bludgeoning",
            "weight_lb": 10,
            "properties": ["Heavy", "Two-handed"],
        },
        {
            "name": "Morningstar",
            "cost_gp": 15,
            "damage": "1d8 piercing",
            "weight_lb": 4,
            "properties": [],
        },
        {
            "name": "Pike",
            "cost_gp": 5,
            "damage": "1d10 piercing",
            "weight_lb": 18,
            "properties": ["Heavy", "Reach", "Two-handed"],
        },
        {
            "name": "Rapier",
            "cost_gp": 25,
            "damage": "1d8 piercing",
            "weight_lb": 2,
            "properties": ["Finesse"],
        },
        {
            "name": "Scimitar",
            "cost_gp": 25,
            "damage": "1d6 slashing",
            "weight_lb": 3,
            "properties": ["Finesse", "Light"],
        },
        {
            "name": "Shortsword",
            "cost_gp": 10,
            "damage": "1d6 piercing",
            "weight_lb": 2,
            "properties": ["Finesse", "Light"],
        },
        {
            "name": "Trident",
            "cost_gp": 5,
            "damage": "1d6 piercing",
            "weight_lb": 4,
            "properties": ["Thrown (20/60)", "Versatile (1d8)"],
        },
        {
            "name": "War pick",
            "cost_gp": 5,
            "damage": "1d8 piercing",
            "weight_lb": 2,
            "properties": [],
        },
        {
            "name": "Warhammer",
            "cost_gp": 15,
            "damage": "1d8 bludgeoning",
            "weight_lb": 2,
            "properties": ["Versatile (1d10)"],
        },
        {
            "name": "Whip",
            "cost_gp": 2,
            "damage": "1d4 slashing",
            "weight_lb": 3,
            "properties": ["Finesse", "Reach"],
        },
    ],
    "martial_ranged": [
        {
            "name": "Blowgun",
            "cost_gp": 10,
            "damage": "1 piercing",
            "weight_lb": 1,
            "properties": ["Ammunition (25/100)", "Loading"],
        },
        {
            "name": "Crossbow, hand",
            "cost_gp": 75,
            "damage": "1d6 piercing",
            "weight_lb": 3,
            "properties": ["Ammunition (30/120)", "Light", "Loading"],
        },
        {
            "name": "Crossbow, heavy",
            "cost_gp": 50,
            "damage": "1d10 piercing",
            "weight_lb": 18,
            "properties": ["Ammunition (100/400)", "Heavy", "Loading", "Two-handed"],
        },
        {
            "name": "Longbow",
            "cost_gp": 50,
            "damage": "1d8 piercing",
            "weight_lb": 2,
            "properties": ["Ammunition (150/600)", "Heavy", "Two-handed"],
        },
        {
            "name": "Net",
            "cost_gp": 1,
            "damage": "0",
            "weight_lb": 3,
            "properties": ["Special", "Thrown (5/15)"],
        },
    ],
    "armor": [
        {
            "name": "Padded",
            "cost_gp": 5,
            "ac": "11 + DEX",
            "strength_req": None,
            "stealth_disadvantage": True,
            "weight_lb": 8,
            "category": "light",
        },
        {
            "name": "Leather",
            "cost_gp": 10,
            "ac": "11 + DEX",
            "strength_req": None,
            "stealth_disadvantage": False,
            "weight_lb": 10,
            "category": "light",
        },
        {
            "name": "Studded leather",
            "cost_gp": 45,
            "ac": "12 + DEX",
            "strength_req": None,
            "stealth_disadvantage": False,
            "weight_lb": 13,
            "category": "light",
        },
        {
            "name": "Hide",
            "cost_gp": 10,
            "ac": "12 + DEX (max 2)",
            "strength_req": None,
            "stealth_disadvantage": False,
            "weight_lb": 12,
            "category": "medium",
        },
        {
            "name": "Chain shirt",
            "cost_gp": 50,
            "ac": "13 + DEX (max 2)",
            "strength_req": None,
            "stealth_disadvantage": False,
            "weight_lb": 20,
            "category": "medium",
        },
        {
            "name": "Scale mail",
            "cost_gp": 50,
            "ac": "14 + DEX (max 2)",
            "strength_req": None,
            "stealth_disadvantage": True,
            "weight_lb": 45,
            "category": "medium",
        },
        {
            "name": "Breastplate",
            "cost_gp": 400,
            "ac": "14 + DEX (max 2)",
            "strength_req": None,
            "stealth_disadvantage": False,
            "weight_lb": 20,
            "category": "medium",
        },
        {
            "name": "Half plate",
            "cost_gp": 750,
            "ac": "15 + DEX (max 2)",
            "strength_req": None,
            "stealth_disadvantage": True,
            "weight_lb": 40,
            "category": "medium",
        },
        {
            "name": "Ring mail",
            "cost_gp": 30,
            "ac": "14",
            "strength_req": None,
            "stealth_disadvantage": True,
            "weight_lb": 40,
            "category": "heavy",
        },
        {
            "name": "Chain mail",
            "cost_gp": 75,
            "ac": "16",
            "strength_req": "STR 13",
            "stealth_disadvantage": True,
            "weight_lb": 55,
            "category": "heavy",
        },
        {
            "name": "Splint",
            "cost_gp": 200,
            "ac": "17",
            "strength_req": "STR 15",
            "stealth_disadvantage": True,
            "weight_lb": 60,
            "category": "heavy",
        },
        {
            "name": "Plate",
            "cost_gp": 1500,
            "ac": "18",
            "strength_req": "STR 15",
            "stealth_disadvantage": True,
            "weight_lb": 65,
            "category": "heavy",
        },
        {
            "name": "Shield",
            "cost_gp": 10,
            "ac": "+2",
            "strength_req": None,
            "stealth_disadvantage": False,
            "weight_lb": 6,
            "category": "shield",
        },
    ],
    "packs": [
        {
            "name": "Burglar's Pack",
            "cost_gp": 16,
            "contents": [
                "Backpack",
                "Bag of 1000 ball bearings",
                "10 feet of string",
                "Bell",
                "5 candles",
                "Crowbar",
                "Hammer",
                "10 pitons",
                "Hooded lantern",
                "2 flasks of oil",
                "5 days rations",
                "Tinderbox",
                "Waterskin",
                "50 feet hempen rope",
            ],
        },
        {
            "name": "Diplomat's Pack",
            "cost_gp": 39,
            "contents": [
                "Chest",
                "2 cases for maps and scrolls",
                "Fine clothes",
                "Bottle of ink",
                "Ink pen",
                "Lamp",
                "2 flasks of oil",
                "5 sheets of paper",
                "Vial of perfume",
                "Sealing wax",
                "Soap",
            ],
        },
        {
            "name": "Dungeoneer's Pack",
            "cost_gp": 12,
            "contents": [
                "Backpack",
                "Crowbar",
                "Hammer",
                "10 pitons",
                "10 torches",
                "Tinderbox",
                "10 days rations",
                "Waterskin",
                "50 feet hempen rope",
            ],
        },
        {
            "name": "Entertainer's Pack",
            "cost_gp": 40,
            "contents": [
                "Backpack",
                "Bedroll",
                "2 costumes",
                "5 candles",
                "5 days rations",
                "Waterskin",
                "Disguise kit",
            ],
        },
        {
            "name": "Explorer's Pack",
            "cost_gp": 10,
            "contents": [
                "Backpack",
                "Bedroll",
                "Mess kit",
                "Tinderbox",
                "10 torches",
                "10 days rations",
                "Waterskin",
                "50 feet hempen rope",
            ],
        },
        {
            "name": "Priest's Pack",
            "cost_gp": 19,
            "contents": [
                "Backpack",
                "Blanket",
                "10 candles",
                "Tinderbox",
                "Alms box",
                "2 blocks of incense",
                "Censer",
                "Vestments",
                "2 days rations",
                "Waterskin",
            ],
        },
        {
            "name": "Scholar's Pack",
            "cost_gp": 40,
            "contents": [
                "Backpack",
                "Book of lore",
                "Bottle of ink",
                "Ink pen",
                "10 sheets of parchment",
                "Little bag of sand",
                "Small knife",
            ],
        },
    ],
}

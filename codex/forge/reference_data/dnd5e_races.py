"""
codex.forge.reference_data.dnd5e_races
========================================
Hardcoded D&D 5e SRD + PHB + Xanathar's Guide (XGE) + Tasha's Cauldron (TCE)
+ Sword Coast Adventurer's Guide (SCAG) + Volo's Guide to Monsters (VGM)
+ Eberron: Rising from the Last War (ERLW) + Van Richten's Guide (VGM source) +
Dungeon Master's Guide (DMG) reference data for races and subclasses.

SUBRACES  -- keyed by race name (lowercase).  Each value is a list of subrace
             dicts with keys: id, name, source, bonuses (dict), traits (list).
SUBCLASSES -- keyed by class name (lowercase).  Each value is a list of
             subclass dicts with keys: id, name, source, level (int).
"""

# ---------------------------------------------------------------------------
# SUBRACES
# ---------------------------------------------------------------------------

SUBRACES: dict = {
    "dwarf": [
        {
            "id": "hill_dwarf",
            "name": "Hill Dwarf",
            "source": "PHB",
            "bonuses": {"wis": 1},
            "traits": ["Dwarven Toughness"],
        },
        {
            "id": "mountain_dwarf",
            "name": "Mountain Dwarf",
            "source": "PHB",
            "bonuses": {"str": 2},
            "traits": ["Dwarven Armor Training"],
        },
        {
            "id": "duergar",
            "name": "Duergar",
            "source": "SCAG",
            "bonuses": {"str": 1},
            "traits": ["Superior Darkvision", "Duergar Magic"],
        },
    ],

    "elf": [
        {
            "id": "high_elf",
            "name": "High Elf",
            "source": "PHB",
            "bonuses": {"int": 1},
            "traits": ["Elf Weapon Training", "Cantrip"],
        },
        {
            "id": "wood_elf",
            "name": "Wood Elf",
            "source": "PHB",
            "bonuses": {"wis": 1},
            "traits": ["Fleet of Foot", "Mask of the Wild"],
        },
        {
            "id": "drow",
            "name": "Drow (Dark Elf)",
            "source": "PHB",
            "bonuses": {"cha": 1},
            "traits": ["Superior Darkvision", "Drow Magic"],
        },
        {
            "id": "eladrin",
            "name": "Eladrin",
            "source": "XGE",
            "bonuses": {"cha": 1},
            "traits": ["Fey Step"],
        },
        {
            "id": "sea_elf",
            "name": "Sea Elf",
            "source": "XGE",
            "bonuses": {"con": 1},
            "traits": ["Sea Elf Training"],
        },
        {
            "id": "shadar_kai",
            "name": "Shadar-kai",
            "source": "XGE",
            "bonuses": {"con": 1},
            "traits": ["Blessing of the Raven Queen"],
        },
    ],

    "halfling": [
        {
            "id": "lightfoot",
            "name": "Lightfoot Halfling",
            "source": "PHB",
            "bonuses": {"cha": 1},
            "traits": ["Naturally Stealthy"],
        },
        {
            "id": "stout",
            "name": "Stout Halfling",
            "source": "PHB",
            "bonuses": {"con": 1},
            "traits": ["Stout Resilience"],
        },
        {
            "id": "ghostwise",
            "name": "Ghostwise Halfling",
            "source": "SCAG",
            "bonuses": {"wis": 1},
            "traits": ["Silent Speech"],
        },
        {
            "id": "lotusden",
            "name": "Lotusden Halfling",
            "source": "XGE",
            "bonuses": {"wis": 1},
            "traits": ["Child of the Wood"],
        },
    ],

    "human": [
        {
            "id": "standard",
            "name": "Standard Human",
            "source": "PHB",
            "bonuses": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1},
            "traits": [],
        },
        {
            "id": "variant",
            "name": "Variant Human",
            "source": "PHB",
            "bonuses": {"any_two": 1},
            "grants_feat": True,
            "traits": ["Skill Versatility"],
        },
    ],

    "gnome": [
        {
            "id": "forest_gnome",
            "name": "Forest Gnome",
            "source": "PHB",
            "bonuses": {"dex": 1},
            "traits": ["Natural Illusionist", "Speak with Small Beasts"],
        },
        {
            "id": "rock_gnome",
            "name": "Rock Gnome",
            "source": "PHB",
            "bonuses": {"con": 1},
            "traits": ["Artificer's Lore", "Tinker"],
        },
        {
            "id": "deep_gnome",
            "name": "Deep Gnome (Svirfneblin)",
            "source": "SCAG",
            "bonuses": {"dex": 1},
            "traits": ["Stone Camouflage", "Superior Darkvision"],
        },
    ],

    "half_elf": [
        {
            "id": "standard",
            "name": "Half-Elf",
            "source": "PHB",
            "bonuses": {"cha": 2, "any_two_others": 1},
            "traits": ["Skill Versatility"],
        },
    ],

    "half_orc": [
        {
            "id": "standard",
            "name": "Half-Orc",
            "source": "PHB",
            "bonuses": {"con": 1},
            "traits": ["Menacing", "Relentless Endurance", "Savage Attacks"],
        },
    ],

    "tiefling": [
        {
            "id": "standard",
            "name": "Tiefling",
            "source": "PHB",
            "bonuses": {"cha": 2, "int": 1},
            "traits": ["Hellish Resistance", "Infernal Legacy"],
        },
        {
            "id": "variant_feral",
            "name": "Variant Tiefling (Feral)",
            "source": "SCAG",
            "bonuses": {"dex": 2, "int": 1},
            "traits": ["Hellish Resistance"],
        },
        {
            "id": "levistus",
            "name": "Tiefling (Levistus)",
            "source": "XGE",
            "bonuses": {"cha": 2, "con": 1},
            "traits": ["Legacy of Stygia"],
        },
        {
            "id": "zariel",
            "name": "Tiefling (Zariel)",
            "source": "XGE",
            "bonuses": {"cha": 2, "str": 1},
            "traits": ["Legacy of Avernus"],
        },
    ],

    "dragonborn": [
        {
            "id": "standard",
            "name": "Dragonborn",
            "source": "PHB",
            "bonuses": {"str": 2, "cha": 1},
            "traits": ["Draconic Ancestry", "Breath Weapon", "Damage Resistance"],
        },
        {
            "id": "draconblood",
            "name": "Draconblood Dragonborn",
            "source": "XGE",
            "bonuses": {"int": 1, "cha": 1},
            "traits": ["Darkvision", "Forceful Presence"],
        },
        {
            "id": "ravenite",
            "name": "Ravenite Dragonborn",
            "source": "XGE",
            "bonuses": {"str": 2, "con": 1},
            "traits": ["Darkvision", "Vengeful Assault"],
        },
    ],

    "aasimar": [
        {
            "id": "protector",
            "name": "Protector Aasimar",
            "source": "VGM",
            "bonuses": {"wis": 1},
            "traits": ["Radiant Soul"],
        },
        {
            "id": "scourge",
            "name": "Scourge Aasimar",
            "source": "VGM",
            "bonuses": {"con": 1},
            "traits": ["Radiant Consumption"],
        },
        {
            "id": "fallen",
            "name": "Fallen Aasimar",
            "source": "VGM",
            "bonuses": {"str": 1},
            "traits": ["Necrotic Shroud"],
        },
    ],

    "goliath": [
        {
            "id": "standard",
            "name": "Goliath",
            "source": "VGM",
            "bonuses": {"con": 1},
            "traits": ["Natural Athlete", "Stone's Endurance", "Mountain Born"],
        },
    ],

    "firbolg": [
        {
            "id": "standard",
            "name": "Firbolg",
            "source": "VGM",
            "bonuses": {"wis": 1},
            "traits": ["Firbolg Magic", "Hidden Step", "Speech of Beast and Leaf"],
        },
    ],

    "kenku": [
        {
            "id": "standard",
            "name": "Kenku",
            "source": "VGM",
            "bonuses": {"dex": 1},
            "traits": ["Expert Forgery", "Mimicry"],
        },
    ],

    "lizardfolk": [
        {
            "id": "standard",
            "name": "Lizardfolk",
            "source": "VGM",
            "bonuses": {"con": 1},
            "traits": ["Natural Armor", "Hungry Jaws", "Cunning Artisan"],
        },
    ],

    "tabaxi": [
        {
            "id": "standard",
            "name": "Tabaxi",
            "source": "VGM",
            "bonuses": {"cha": 1},
            "traits": ["Feline Agility", "Cat's Claws", "Cat's Talent"],
        },
    ],

    "triton": [
        {
            "id": "standard",
            "name": "Triton",
            "source": "VGM",
            "bonuses": {"con": 1},
            "traits": ["Control Air and Water", "Emissary of the Sea", "Guardians of the Depths"],
        },
    ],

    "bugbear": [
        {
            "id": "standard",
            "name": "Bugbear",
            "source": "VGM",
            "bonuses": {"dex": 1},
            "traits": ["Long-Limbed", "Powerful Build", "Surprise Attack"],
        },
    ],

    "goblin": [
        {
            "id": "standard",
            "name": "Goblin",
            "source": "VGM",
            "bonuses": {"dex": 1},
            "traits": ["Fury of the Small", "Nimble Escape"],
        },
    ],

    "hobgoblin": [
        {
            "id": "standard",
            "name": "Hobgoblin",
            "source": "VGM",
            "bonuses": {"con": 1},
            "traits": ["Martial Training", "Saving Face"],
        },
    ],

    "kobold": [
        {
            "id": "standard",
            "name": "Kobold",
            "source": "VGM",
            "bonuses": {"dex": 1},
            "traits": ["Grovel", "Pack Tactics", "Sunlight Sensitivity"],
        },
    ],

    "orc": [
        {
            "id": "standard",
            "name": "Orc",
            "source": "VGM",
            "bonuses": {"con": 1},
            "traits": ["Aggressive", "Powerful Build"],
        },
    ],

    "yuan_ti": [
        {
            "id": "standard",
            "name": "Yuan-ti Pureblood",
            "source": "VGM",
            "bonuses": {"cha": 1},
            "traits": ["Magic Resistance", "Poison Immunity"],
        },
    ],

    "changeling": [
        {
            "id": "standard",
            "name": "Changeling",
            "source": "ERLW",
            "bonuses": {"cha": 1, "any_one": 1},
            "traits": ["Shapechanger", "Changeling Instincts"],
        },
    ],

    "kalashtar": [
        {
            "id": "standard",
            "name": "Kalashtar",
            "source": "ERLW",
            "bonuses": {"wis": 1, "cha": 1},
            "traits": ["Dual Mind", "Mental Discipline", "Mind Link"],
        },
    ],

    "shifter": [
        {
            "id": "beasthide",
            "name": "Beasthide Shifter",
            "source": "ERLW",
            "bonuses": {"con": 2, "str": 1},
            "traits": ["Tough Hide"],
        },
        {
            "id": "longtooth",
            "name": "Longtooth Shifter",
            "source": "ERLW",
            "bonuses": {"str": 2, "dex": 1},
            "traits": ["Fierce"],
        },
        {
            "id": "swiftstride",
            "name": "Swiftstride Shifter",
            "source": "ERLW",
            "bonuses": {"dex": 2, "cha": 1},
            "traits": ["Swift"],
        },
        {
            "id": "wildhunt",
            "name": "Wildhunt Shifter",
            "source": "ERLW",
            "bonuses": {"wis": 2, "dex": 1},
            "traits": ["Mark the Scent"],
        },
    ],

    "warforged": [
        {
            "id": "standard",
            "name": "Warforged",
            "source": "ERLW",
            "bonuses": {"con": 2, "any_one": 1},
            "traits": ["Constructed Resilience", "Sentry's Rest", "Integrated Protection"],
        },
    ],

    "custom_lineage": [
        {
            "id": "custom",
            "name": "Custom Lineage",
            "source": "TCE",
            "bonuses": {"any_one": 2},
            "grants_feat": True,
            "traits": ["Variable Trait"],
        },
    ],
}

# ---------------------------------------------------------------------------
# SUBCLASSES
# ---------------------------------------------------------------------------

SUBCLASSES: dict = {
    "barbarian": [
        {"id": "berserker",           "name": "Path of the Berserker",           "source": "PHB", "level": 3},
        {"id": "totem_warrior",       "name": "Path of the Totem Warrior",       "source": "PHB", "level": 3},
        {"id": "ancestral_guardian",  "name": "Path of the Ancestral Guardian",  "source": "XGE", "level": 3},
        {"id": "storm_herald",        "name": "Path of the Storm Herald",        "source": "XGE", "level": 3},
        {"id": "zealot",              "name": "Path of the Zealot",              "source": "XGE", "level": 3},
        {"id": "beast",               "name": "Path of the Beast",               "source": "TCE", "level": 3},
        {"id": "wild_magic",          "name": "Path of Wild Magic",              "source": "TCE", "level": 3},
    ],

    "bard": [
        {"id": "lore",       "name": "College of Lore",       "source": "PHB", "level": 3},
        {"id": "valor",      "name": "College of Valor",      "source": "PHB", "level": 3},
        {"id": "glamour",    "name": "College of Glamour",    "source": "XGE", "level": 3},
        {"id": "swords",     "name": "College of Swords",     "source": "XGE", "level": 3},
        {"id": "whispers",   "name": "College of Whispers",   "source": "XGE", "level": 3},
        {"id": "creation",   "name": "College of Creation",   "source": "TCE", "level": 3},
        {"id": "eloquence",  "name": "College of Eloquence",  "source": "TCE", "level": 3},
    ],

    "cleric": [
        {"id": "knowledge",  "name": "Knowledge Domain",  "source": "PHB",  "level": 1},
        {"id": "life",       "name": "Life Domain",       "source": "PHB",  "level": 1},
        {"id": "light",      "name": "Light Domain",      "source": "PHB",  "level": 1},
        {"id": "nature",     "name": "Nature Domain",     "source": "PHB",  "level": 1},
        {"id": "tempest",    "name": "Tempest Domain",    "source": "PHB",  "level": 1},
        {"id": "trickery",   "name": "Trickery Domain",   "source": "PHB",  "level": 1},
        {"id": "war",        "name": "War Domain",        "source": "PHB",  "level": 1},
        {"id": "forge",      "name": "Forge Domain",      "source": "XGE",  "level": 1},
        {"id": "grave",      "name": "Grave Domain",      "source": "XGE",  "level": 1},
        {"id": "order",      "name": "Order Domain",      "source": "TCE",  "level": 1},
        {"id": "peace",      "name": "Peace Domain",      "source": "TCE",  "level": 1},
        {"id": "twilight",   "name": "Twilight Domain",   "source": "TCE",  "level": 1},
        {"id": "arcana",     "name": "Arcana Domain",     "source": "SCAG", "level": 1},
        {"id": "death",      "name": "Death Domain",      "source": "DMG",  "level": 1},
    ],

    "druid": [
        {"id": "land",      "name": "Circle of the Land",      "source": "PHB", "level": 2},
        {"id": "moon",      "name": "Circle of the Moon",      "source": "PHB", "level": 2},
        {"id": "dreams",    "name": "Circle of Dreams",        "source": "XGE", "level": 2},
        {"id": "shepherd",  "name": "Circle of the Shepherd",  "source": "XGE", "level": 2},
        {"id": "spores",    "name": "Circle of Spores",        "source": "XGE", "level": 2},
        {"id": "stars",     "name": "Circle of Stars",         "source": "TCE", "level": 2},
        {"id": "wildfire",  "name": "Circle of Wildfire",      "source": "TCE", "level": 2},
    ],

    "fighter": [
        {"id": "champion",       "name": "Champion",                "source": "PHB", "level": 3},
        {"id": "battle_master",  "name": "Battle Master",           "source": "PHB", "level": 3},
        {"id": "eldritch_knight","name": "Eldritch Knight",         "source": "PHB", "level": 3},
        {"id": "arcane_archer",  "name": "Arcane Archer",           "source": "XGE", "level": 3},
        {"id": "cavalier",       "name": "Cavalier",                "source": "XGE", "level": 3},
        {"id": "samurai",        "name": "Samurai",                 "source": "XGE", "level": 3},
        {"id": "psi_warrior",    "name": "Psi Warrior",             "source": "TCE", "level": 3},
        {"id": "rune_knight",    "name": "Rune Knight",             "source": "TCE", "level": 3},
        {"id": "echo_knight",    "name": "Echo Knight",             "source": "XGE", "level": 3},
    ],

    "monk": [
        {"id": "open_hand",    "name": "Way of the Open Hand",    "source": "PHB", "level": 3},
        {"id": "shadow",       "name": "Way of Shadow",           "source": "PHB", "level": 3},
        {"id": "four_elements","name": "Way of the Four Elements","source": "PHB", "level": 3},
        {"id": "drunken_master","name": "Way of the Drunken Master","source": "XGE","level": 3},
        {"id": "kensei",       "name": "Way of the Kensei",       "source": "XGE", "level": 3},
        {"id": "sun_soul",     "name": "Way of the Sun Soul",     "source": "XGE", "level": 3},
        {"id": "astral_self",  "name": "Way of the Astral Self",  "source": "TCE", "level": 3},
        {"id": "mercy",        "name": "Way of Mercy",            "source": "TCE", "level": 3},
    ],

    "paladin": [
        {"id": "devotion",    "name": "Oath of Devotion",    "source": "PHB",  "level": 3},
        {"id": "ancients",    "name": "Oath of the Ancients","source": "PHB",  "level": 3},
        {"id": "vengeance",   "name": "Oath of Vengeance",   "source": "PHB",  "level": 3},
        {"id": "conquest",    "name": "Oath of Conquest",    "source": "XGE",  "level": 3},
        {"id": "redemption",  "name": "Oath of Redemption",  "source": "XGE",  "level": 3},
        {"id": "crown",       "name": "Oath of the Crown",   "source": "SCAG", "level": 3},
        {"id": "glory",       "name": "Oath of Glory",       "source": "TCE",  "level": 3},
        {"id": "watchers",    "name": "Oath of the Watchers","source": "TCE",  "level": 3},
    ],

    "ranger": [
        {"id": "hunter",         "name": "Hunter",                "source": "PHB", "level": 3},
        {"id": "beast_master",   "name": "Beast Master",          "source": "PHB", "level": 3},
        {"id": "gloom_stalker",  "name": "Gloom Stalker",         "source": "XGE", "level": 3},
        {"id": "horizon_walker", "name": "Horizon Walker",        "source": "XGE", "level": 3},
        {"id": "monster_slayer", "name": "Monster Slayer",        "source": "XGE", "level": 3},
        {"id": "fey_wanderer",   "name": "Fey Wanderer",          "source": "TCE", "level": 3},
        {"id": "swarmkeeper",    "name": "Swarmkeeper",           "source": "TCE", "level": 3},
        {"id": "drakewarden",    "name": "Drakewarden",           "source": "TCE", "level": 3},
    ],

    "rogue": [
        {"id": "thief",           "name": "Thief",              "source": "PHB",      "level": 3},
        {"id": "assassin",        "name": "Assassin",           "source": "PHB",      "level": 3},
        {"id": "arcane_trickster","name": "Arcane Trickster",   "source": "PHB",      "level": 3},
        {"id": "inquisitive",     "name": "Inquisitive",        "source": "XGE",      "level": 3},
        {"id": "mastermind",      "name": "Mastermind",         "source": "XGE/SCAG", "level": 3},
        {"id": "scout",           "name": "Scout",              "source": "XGE",      "level": 3},
        {"id": "swashbuckler",    "name": "Swashbuckler",       "source": "XGE/SCAG", "level": 3},
        {"id": "phantom",         "name": "Phantom",            "source": "TCE",      "level": 3},
        {"id": "soulknife",       "name": "Soulknife",          "source": "TCE",      "level": 3},
    ],

    "sorcerer": [
        {"id": "draconic_bloodline","name": "Draconic Bloodline",    "source": "PHB",      "level": 1},
        {"id": "wild_magic",       "name": "Wild Magic",             "source": "PHB",      "level": 1},
        {"id": "divine_soul",      "name": "Divine Soul",            "source": "XGE",      "level": 1},
        {"id": "shadow_magic",     "name": "Shadow Magic",           "source": "XGE",      "level": 1},
        {"id": "storm_sorcery",    "name": "Storm Sorcery",          "source": "XGE/SCAG", "level": 1},
        {"id": "aberrant_mind",    "name": "Aberrant Mind",          "source": "TCE",      "level": 1},
        {"id": "clockwork_soul",   "name": "Clockwork Soul",         "source": "TCE",      "level": 1},
    ],

    "warlock": [
        {"id": "archfey",     "name": "The Archfey",      "source": "PHB", "level": 1},
        {"id": "fiend",       "name": "The Fiend",        "source": "PHB", "level": 1},
        {"id": "great_old_one","name": "The Great Old One","source": "PHB","level": 1},
        {"id": "celestial",   "name": "The Celestial",    "source": "XGE", "level": 1},
        {"id": "hexblade",    "name": "The Hexblade",     "source": "XGE", "level": 1},
        {"id": "fathomless",  "name": "The Fathomless",   "source": "TCE", "level": 1},
        {"id": "genie",       "name": "The Genie",        "source": "TCE", "level": 1},
        {"id": "undead",      "name": "The Undead",       "source": "TCE", "level": 1},
    ],

    "wizard": [
        {"id": "abjuration",      "name": "School of Abjuration",      "source": "PHB",      "level": 2},
        {"id": "conjuration",     "name": "School of Conjuration",     "source": "PHB",      "level": 2},
        {"id": "divination",      "name": "School of Divination",      "source": "PHB",      "level": 2},
        {"id": "enchantment",     "name": "School of Enchantment",     "source": "PHB",      "level": 2},
        {"id": "evocation",       "name": "School of Evocation",       "source": "PHB",      "level": 2},
        {"id": "illusion",        "name": "School of Illusion",        "source": "PHB",      "level": 2},
        {"id": "necromancy",      "name": "School of Necromancy",      "source": "PHB",      "level": 2},
        {"id": "transmutation",   "name": "School of Transmutation",   "source": "PHB",      "level": 2},
        {"id": "bladesinging",    "name": "Bladesinging",              "source": "TCE/SCAG", "level": 2},
        {"id": "war_magic",       "name": "School of War Magic",       "source": "XGE",      "level": 2},
        {"id": "chronurgy",       "name": "Chronurgy Magic",           "source": "XGE",      "level": 2},
        {"id": "graviturgy",      "name": "Graviturgy Magic",          "source": "XGE",      "level": 2},
        {"id": "order_of_scribes","name": "Order of Scribes",          "source": "TCE",      "level": 2},
    ],

    "artificer": [
        {"id": "alchemist",    "name": "Alchemist",    "source": "TCE", "level": 3},
        {"id": "armorer",      "name": "Armorer",      "source": "TCE", "level": 3},
        {"id": "artillerist",  "name": "Artillerist",  "source": "TCE", "level": 3},
        {"id": "battle_smith", "name": "Battle Smith", "source": "TCE", "level": 3},
    ],
}

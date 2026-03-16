"""
D&D 5e skill, background, and class proficiency reference data.

Contains four static dictionaries used by character creation and validation:
  - SKILLS: All 18 core skills with their governing ability and source book.
  - CLASS_SKILL_CHOICES: Per-class skill selection rules (pick N from list).
  - BACKGROUND_SKILLS: Fixed skill grants per background.
  - SAVING_THROW_PROFICIENCIES: Per-class saving throw proficiency pairs.
  - ALIGNMENTS: All nine alignments with display names.
"""

# ---------------------------------------------------------------------------
# 1. SKILLS
# ---------------------------------------------------------------------------

SKILLS = {
    "acrobatics":     {"ability": "dexterity",     "source": "PHB"},
    "animal_handling":{"ability": "wisdom",         "source": "PHB"},
    "arcana":         {"ability": "intelligence",   "source": "PHB"},
    "athletics":      {"ability": "strength",       "source": "PHB"},
    "deception":      {"ability": "charisma",       "source": "PHB"},
    "history":        {"ability": "intelligence",   "source": "PHB"},
    "insight":        {"ability": "wisdom",         "source": "PHB"},
    "intimidation":   {"ability": "charisma",       "source": "PHB"},
    "investigation":  {"ability": "intelligence",   "source": "PHB"},
    "medicine":       {"ability": "wisdom",         "source": "PHB"},
    "nature":         {"ability": "intelligence",   "source": "PHB"},
    "perception":     {"ability": "wisdom",         "source": "PHB"},
    "performance":    {"ability": "charisma",       "source": "PHB"},
    "persuasion":     {"ability": "charisma",       "source": "PHB"},
    "religion":       {"ability": "intelligence",   "source": "PHB"},
    "sleight_of_hand":{"ability": "dexterity",      "source": "PHB"},
    "stealth":        {"ability": "dexterity",      "source": "PHB"},
    "survival":       {"ability": "wisdom",         "source": "PHB"},
}

# ---------------------------------------------------------------------------
# 2. CLASS_SKILL_CHOICES
# ---------------------------------------------------------------------------

CLASS_SKILL_CHOICES = {
    "barbarian": {
        "pick": 2,
        "from": [
            "animal_handling", "athletics", "intimidation",
            "nature", "perception", "survival",
        ],
    },
    "bard": {
        "pick": 3,
        "from": "any",
    },
    "cleric": {
        "pick": 2,
        "from": ["history", "insight", "medicine", "persuasion", "religion"],
    },
    "druid": {
        "pick": 2,
        "from": [
            "arcana", "animal_handling", "insight", "medicine",
            "nature", "perception", "religion", "survival",
        ],
    },
    "fighter": {
        "pick": 2,
        "from": [
            "acrobatics", "animal_handling", "athletics", "history",
            "insight", "intimidation", "perception", "survival",
        ],
    },
    "monk": {
        "pick": 2,
        "from": [
            "acrobatics", "athletics", "history",
            "insight", "religion", "stealth",
        ],
    },
    "paladin": {
        "pick": 2,
        "from": [
            "athletics", "insight", "intimidation",
            "medicine", "persuasion", "religion",
        ],
    },
    "ranger": {
        "pick": 3,
        "from": [
            "animal_handling", "athletics", "insight", "investigation",
            "nature", "perception", "stealth", "survival",
        ],
    },
    "rogue": {
        "pick": 4,
        "from": [
            "acrobatics", "athletics", "deception", "insight",
            "intimidation", "investigation", "perception", "performance",
            "persuasion", "sleight_of_hand", "stealth",
        ],
    },
    "sorcerer": {
        "pick": 2,
        "from": [
            "arcana", "deception", "insight",
            "intimidation", "persuasion", "religion",
        ],
    },
    "warlock": {
        "pick": 2,
        "from": [
            "arcana", "deception", "history",
            "intimidation", "investigation", "nature", "religion",
        ],
    },
    "wizard": {
        "pick": 2,
        "from": [
            "arcana", "history", "insight",
            "investigation", "medicine", "religion",
        ],
    },
    "artificer": {
        "pick": 2,
        "from": [
            "arcana", "history", "investigation", "medicine",
            "nature", "perception", "sleight_of_hand",
        ],
    },
}

# ---------------------------------------------------------------------------
# 3. BACKGROUND_SKILLS
# ---------------------------------------------------------------------------

BACKGROUND_SKILLS = {
    # PHB backgrounds
    "acolyte":          ["insight", "religion"],
    "charlatan":        ["deception", "sleight_of_hand"],
    "criminal":         ["deception", "stealth"],
    "entertainer":      ["acrobatics", "performance"],
    "folk_hero":        ["animal_handling", "survival"],
    "guild_artisan":    ["insight", "persuasion"],
    "hermit":           ["medicine", "religion"],
    "noble":            ["history", "persuasion"],
    "outlander":        ["athletics", "survival"],
    "sage":             ["arcana", "history"],
    "sailor":           ["athletics", "perception"],
    "soldier":          ["athletics", "intimidation"],
    "urchin":           ["sleight_of_hand", "stealth"],
    # SCAG backgrounds
    "city_watch":           ["athletics", "insight"],          # SCAG
    "clan_crafter":         ["history", "insight"],            # SCAG
    "cloistered_scholar":   ["history", "religion"],           # SCAG; alt: arcana or nature
    "courtier":             ["insight", "persuasion"],         # SCAG
    "faction_agent":        ["insight", "investigation"],      # SCAG; alt: other based on faction
    "far_traveler":         ["insight", "perception"],         # SCAG
    "inheritor":            ["survival", "arcana"],            # SCAG; alt: history or religion
    "knight_of_the_order":  ["persuasion", "religion"],        # SCAG; alt: arcana, nature, or history
    "mercenary_veteran":    ["athletics", "persuasion"],       # SCAG
    "urban_bounty_hunter":  ["deception", "stealth"],          # SCAG; alt: insight or persuasion
    "uthgardt_tribe_member":["athletics", "survival"],         # SCAG
    "waterdhavian_noble":   ["history", "persuasion"],         # SCAG
    # Curse of Strahd backgrounds
    "haunted_one":          ["arcana", "investigation"],       # CoS; alt: religion or survival
}

# ---------------------------------------------------------------------------
# 4. SAVING_THROW_PROFICIENCIES
# ---------------------------------------------------------------------------

SAVING_THROW_PROFICIENCIES = {
    "barbarian": ["strength",      "constitution"],
    "bard":      ["dexterity",     "charisma"],
    "cleric":    ["wisdom",        "charisma"],
    "druid":     ["intelligence",  "wisdom"],
    "fighter":   ["strength",      "constitution"],
    "monk":      ["strength",      "dexterity"],
    "paladin":   ["wisdom",        "charisma"],
    "ranger":    ["strength",      "dexterity"],
    "rogue":     ["dexterity",     "intelligence"],
    "sorcerer":  ["constitution",  "charisma"],
    "warlock":   ["wisdom",        "charisma"],
    "wizard":    ["intelligence",  "wisdom"],
    "artificer": ["constitution",  "intelligence"],
}

# ---------------------------------------------------------------------------
# 5. ALIGNMENTS
# ---------------------------------------------------------------------------

ALIGNMENTS = {
    "lawful_good":    "Lawful Good",
    "neutral_good":   "Neutral Good",
    "chaotic_good":   "Chaotic Good",
    "lawful_neutral": "Lawful Neutral",
    "true_neutral":   "True Neutral",
    "chaotic_neutral":"Chaotic Neutral",
    "lawful_evil":    "Lawful Evil",
    "neutral_evil":   "Neutral Evil",
    "chaotic_evil":   "Chaotic Evil",
}

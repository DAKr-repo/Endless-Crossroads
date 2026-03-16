"""
codex.forge.reference_data.dnd5e_tashas
========================================
Tasha's Cauldron of Everything reference data for D&D 5e character creation.
Includes life path tables, dark secrets, group patrons, optional class features,
and custom lineage rules.

Source: Tasha's Cauldron of Everything (TCE), 2020
"""

# ---------------------------------------------------------------------------
# LIFE_PATH_TABLES — from "This Is Your Life" chapter
# Each list contains rollable/selectable entries for that category.
# ---------------------------------------------------------------------------
LIFE_PATH_TABLES: dict = {
    "parents": [
        "You knew both your parents.",
        "You knew only your mother.",
        "You knew only your father.",
        "You were raised by your grandparents.",
        "You were raised by an aunt or uncle.",
        "You were raised in a monastery or temple.",
        "You were raised in an orphanage.",
        "You were raised by a kindly stranger.",
    ],
    "birthplace": [
        "Home",
        "Home of a family friend",
        "On a battlefield",
        "In an alley or on a street",
        "At a temple",
        "In a castle",
        "In a cave",
        "In a tree",
        "Among a nomadic tribe",
        "In a prison or labor camp",
        "In a laboratory",
        "On a ship at sea",
        "In a carriage or wagon",
        "In a palace",
        "At a crossroads",
        "In a forest clearing",
    ],
    "siblings": [
        "No siblings",
        "1d3 siblings (you are the eldest)",
        "1d3 siblings (you are the youngest)",
        "1d3 siblings (you are in the middle)",
        "1d4+1 siblings (large family, you are somewhere in the middle)",
        "Twin sibling",
    ],
    "childhood_memories": [
        "I am still haunted by my childhood, when I was treated badly by my peers.",
        "I spent most of my childhood alone, with no close friends.",
        "Others saw me as being different or strange, and so I had few companions.",
        "I had a few close friends and lived an ordinary childhood.",
        "I had several friends, and my childhood was generally a happy one.",
        "I always found it easy to make friends, and I loved being around people.",
        "Everyone knew who I was, and I had friends everywhere I went.",
        "I was raised in isolation, far from civilization.",
    ],
    "life_events": [
        "You suffered a tragedy. A family member or close friend died.",
        "You gained an enemy. Someone swore to do you harm.",
        "You made a friend. An ally proved loyal in a time of need.",
        "You spent time working in a job related to your background.",
        "You met someone important — an adventurer, noble, or sage.",
        "You went on an adventure and barely survived.",
        "You had a supernatural experience — a vision, a haunting, or divine sign.",
        "You fought in a battle and witnessed the horrors of war.",
        "You committed a crime, whether justified or not.",
        "You encountered something magical — an item, a creature, or a place of power.",
        "You fell in love, or someone fell in love with you.",
        "You traveled to a distant land and experienced a different culture.",
        "You lost something of great value — an heirloom, a fortune, or a position.",
        "You were imprisoned for a crime you may or may not have committed.",
        "You discovered a hidden talent or received training in a new skill.",
        "You made a terrible mistake that still haunts you.",
    ],
}

# ---------------------------------------------------------------------------
# DARK_SECRETS — 12 options from TCE "This Is Your Life"
# ---------------------------------------------------------------------------
DARK_SECRETS: list = [
    {
        "id": "murder",
        "name": "Murder",
        "description": (
            "You killed someone and have never been caught. The guilt — "
            "or lack of it — defines you."
        ),
    },
    {
        "id": "forbidden_knowledge",
        "name": "Forbidden Knowledge",
        "description": (
            "You learned something no mortal should know — about the gods, "
            "the planes, or the nature of reality."
        ),
    },
    {
        "id": "false_identity",
        "name": "False Identity",
        "description": (
            "You are not who you claim to be. Your true name, heritage, "
            "or past is carefully hidden."
        ),
    },
    {
        "id": "pact",
        "name": "Otherworldly Pact",
        "description": (
            "You made a bargain with a powerful entity — a fiend, fey, or "
            "aberration — and the debt is not yet paid."
        ),
    },
    {
        "id": "stolen_inheritance",
        "name": "Stolen Inheritance",
        "description": (
            "Your wealth, title, or position was taken from someone else "
            "through deception or force."
        ),
    },
    {
        "id": "undead_connection",
        "name": "Undead Connection",
        "description": (
            "Someone close to you became undead, or you yourself have been "
            "touched by necromantic energy."
        ),
    },
    {
        "id": "cult_member",
        "name": "Former Cult Member",
        "description": (
            "You once belonged to a dangerous cult and participated in their "
            "rituals before escaping."
        ),
    },
    {
        "id": "hunted",
        "name": "Hunted",
        "description": (
            "A powerful organization or individual is actively searching for you."
        ),
    },
    {
        "id": "betrayal",
        "name": "Great Betrayal",
        "description": (
            "You betrayed someone who trusted you completely, and the "
            "consequences still ripple outward."
        ),
    },
    {
        "id": "cursed",
        "name": "Cursed",
        "description": (
            "You bear a curse — placed by a hag, a dying enemy, or an artifact "
            "you should never have touched."
        ),
    },
    {
        "id": "prophecy",
        "name": "Dark Prophecy",
        "description": (
            "A seer foretold something terrible about your future, and every "
            "day brings you closer to it."
        ),
    },
    {
        "id": "creation",
        "name": "Unnatural Origin",
        "description": (
            "You were not born naturally — you were created, cloned, or "
            "reborn through magic."
        ),
    },
]

# ---------------------------------------------------------------------------
# GROUP_PATRONS — 8 patron types from TCE
# ---------------------------------------------------------------------------
GROUP_PATRONS: list = [
    {
        "id": "academy",
        "name": "Academy",
        "description": (
            "A university, wizard's college, or bardic conservatory sponsors "
            "the group."
        ),
        "perks": [
            "Access to libraries and research facilities",
            "Free lodging on campus",
            "Discounts on spell components",
        ],
        "quest_hooks": [
            "Recover a stolen tome of ancient lore",
            "Investigate a magical anomaly",
            "Test a new spell in the field",
        ],
    },
    {
        "id": "ancient_being",
        "name": "Ancient Being",
        "description": (
            "A dragon, archfey, celestial, or other powerful entity directs "
            "the group from the shadows."
        ),
        "perks": [
            "Occasional magical gifts",
            "Prophetic visions or warnings",
            "Protection from lesser threats",
        ],
        "quest_hooks": [
            "Retrieve an artifact the being desires",
            "Eliminate a rival entity's servants",
            "Investigate a disturbance in the being's domain",
        ],
    },
    {
        "id": "aristocrat",
        "name": "Aristocrat",
        "description": (
            "A noble family or titled individual funds the group's activities "
            "in exchange for service."
        ),
        "perks": [
            "Monthly stipend (lifestyle: comfortable)",
            "Letters of introduction",
            "Access to noble courts",
        ],
        "quest_hooks": [
            "Protect the family's interests in a trade dispute",
            "Recover a kidnapped heir",
            "Investigate a rival noble house",
        ],
    },
    {
        "id": "criminal_syndicate",
        "name": "Criminal Syndicate",
        "description": (
            "A thieves' guild, smuggling ring, or organized crime family "
            "employs the group."
        ),
        "perks": [
            "Fencing stolen goods at 60% value",
            "Safe houses in major cities",
            "Underground contacts",
        ],
        "quest_hooks": [
            "Pull off a daring heist",
            "Eliminate a rival gang leader",
            "Smuggle contraband past city guards",
        ],
    },
    {
        "id": "guild",
        "name": "Guild",
        "description": (
            "A merchant guild, adventurer's guild, or artisan's collective "
            "provides backing."
        ),
        "perks": [
            "Guild membership benefits",
            "Discounts at guild-affiliated shops",
            "Job board access",
        ],
        "quest_hooks": [
            "Escort a valuable shipment",
            "Clear a trade route of bandits",
            "Negotiate a new trade agreement",
        ],
    },
    {
        "id": "military_force",
        "name": "Military Force",
        "description": (
            "An army, navy, or mercenary company assigns missions to the group."
        ),
        "perks": [
            "Military rank and authority",
            "Access to armories and training grounds",
            "Backup troops for major operations",
        ],
        "quest_hooks": [
            "Scout enemy positions",
            "Defend a strategic location",
            "Retrieve intelligence from behind enemy lines",
        ],
    },
    {
        "id": "religious_order",
        "name": "Religious Order",
        "description": (
            "A temple, monastery, or holy order guides the group on divine "
            "missions."
        ),
        "perks": [
            "Free healing at temples",
            "Holy water and blessed items",
            "Divination consultations",
        ],
        "quest_hooks": [
            "Purge an undead infestation",
            "Recover a holy relic",
            "Convert or protect a remote community",
        ],
    },
    {
        "id": "sovereign",
        "name": "Sovereign",
        "description": (
            "A king, queen, or governing body directly commissions the group."
        ),
        "perks": [
            "Royal warrant granting legal authority",
            "Access to the treasury for mission expenses",
            "Audiences with the ruler",
        ],
        "quest_hooks": [
            "Investigate a conspiracy against the crown",
            "Negotiate with a hostile nation",
            "Slay a monster threatening the realm",
        ],
    },
]

# ---------------------------------------------------------------------------
# OPTIONAL_CLASS_FEATURES — per-class optional rules from TCE
# Each entry: name, replaces (None or feature name), level, description
# ---------------------------------------------------------------------------
OPTIONAL_CLASS_FEATURES: dict = {
    "barbarian": [
        {
            "name": "Primal Knowledge",
            "replaces": None,
            "level": 3,
            "description": (
                "Gain proficiency in one skill from: Animal Handling, Athletics, "
                "Intimidation, Nature, Perception, Survival."
            ),
        },
        {
            "name": "Instinctive Pounce",
            "replaces": None,
            "level": 7,
            "description": (
                "When you enter rage, you can move up to half your speed as part "
                "of the bonus action."
            ),
        },
    ],
    "bard": [
        {
            "name": "Magical Inspiration",
            "replaces": None,
            "level": 2,
            "description": (
                "Bardic Inspiration die can also add to damage or healing rolls."
            ),
        },
        {
            "name": "Bardic Versatility",
            "replaces": None,
            "level": 4,
            "description": (
                "When you gain an ASI, you can replace one cantrip or "
                "Expertise skill."
            ),
        },
    ],
    "cleric": [
        {
            "name": "Harness Divine Power",
            "replaces": None,
            "level": 2,
            "description": (
                "Use Channel Divinity to regain a spell slot (level = prof bonus "
                "/ 2, rounded up)."
            ),
        },
        {
            "name": "Cantrip Versatility",
            "replaces": None,
            "level": 4,
            "description": (
                "When you gain an ASI, you can replace one cleric cantrip."
            ),
        },
        {
            "name": "Blessed Strikes",
            "replaces": "Divine Strike or Potent Spellcasting",
            "level": 8,
            "description": (
                "Once per turn, deal extra 1d8 radiant damage with weapon "
                "or cantrip."
            ),
        },
    ],
    "druid": [
        {
            "name": "Wild Companion",
            "replaces": None,
            "level": 2,
            "description": (
                "Expend a use of Wild Shape to cast Find Familiar without "
                "material components."
            ),
        },
        {
            "name": "Cantrip Versatility",
            "replaces": None,
            "level": 4,
            "description": (
                "When you gain an ASI, you can replace one druid cantrip."
            ),
        },
    ],
    "fighter": [
        {
            "name": "Fighting Style Options",
            "replaces": None,
            "level": 1,
            "description": (
                "Additional fighting styles: Blind Fighting, Interception, "
                "Superior Technique, Thrown Weapon Fighting, Unarmed Fighting."
            ),
        },
        {
            "name": "Martial Versatility",
            "replaces": None,
            "level": 4,
            "description": (
                "When you gain an ASI, you can replace a fighting style "
                "or maneuver."
            ),
        },
    ],
    "monk": [
        {
            "name": "Dedicated Weapon",
            "replaces": None,
            "level": 2,
            "description": (
                "You can designate a weapon you're proficient with as a monk "
                "weapon at the end of a rest."
            ),
        },
        {
            "name": "Ki-Fueled Attack",
            "replaces": None,
            "level": 3,
            "description": (
                "After spending a ki point on your turn, make one unarmed "
                "strike as a bonus action."
            ),
        },
        {
            "name": "Quickened Healing",
            "replaces": None,
            "level": 4,
            "description": (
                "Spend 2 ki points to regain HP equal to one roll of your "
                "Martial Arts die + proficiency bonus."
            ),
        },
    ],
    "paladin": [
        {
            "name": "Fighting Style Options",
            "replaces": None,
            "level": 2,
            "description": (
                "Additional fighting styles: Blind Fighting, Interception."
            ),
        },
        {
            "name": "Harness Divine Power",
            "replaces": None,
            "level": 3,
            "description": (
                "Use Channel Divinity to regain a spell slot (level = prof "
                "bonus / 2, rounded up)."
            ),
        },
        {
            "name": "Martial Versatility",
            "replaces": None,
            "level": 4,
            "description": (
                "When you gain an ASI, you can replace a fighting style."
            ),
        },
    ],
    "ranger": [
        {
            "name": "Deft Explorer",
            "replaces": "Natural Explorer",
            "level": 1,
            "description": (
                "Canny (expertise in one skill), Roving (climbing/swimming "
                "speed), Tireless (temp HP)."
            ),
        },
        {
            "name": "Favored Foe",
            "replaces": "Favored Enemy",
            "level": 1,
            "description": (
                "Mark a creature, deal extra 1d4 damage once per turn "
                "(concentration, no spell slot)."
            ),
        },
        {
            "name": "Fighting Style Options",
            "replaces": None,
            "level": 2,
            "description": (
                "Additional fighting styles: Blind Fighting, Druidic Warrior, "
                "Thrown Weapon Fighting."
            ),
        },
        {
            "name": "Primal Awareness",
            "replaces": "Primeval Awareness",
            "level": 3,
            "description": (
                "Free castings of Speak with Animals, Beast Sense, Speak with "
                "Plants, Locate Creature, Commune with Nature."
            ),
        },
    ],
    "rogue": [
        {
            "name": "Steady Aim",
            "replaces": None,
            "level": 3,
            "description": (
                "Bonus action: give yourself advantage on next attack "
                "(no movement that turn)."
            ),
        },
    ],
    "sorcerer": [
        {
            "name": "Sorcerous Versatility",
            "replaces": None,
            "level": 4,
            "description": (
                "When you gain an ASI, replace one cantrip or Metamagic option."
            ),
        },
        {
            "name": "Magical Guidance",
            "replaces": None,
            "level": 5,
            "description": (
                "Spend 1 sorcery point to reroll a failed ability check."
            ),
        },
    ],
    "warlock": [
        {
            "name": "Eldritch Versatility",
            "replaces": None,
            "level": 4,
            "description": (
                "When you gain an ASI, replace one cantrip, pact boon, "
                "or invocation."
            ),
        },
    ],
    "wizard": [
        {
            "name": "Cantrip Formulas",
            "replaces": None,
            "level": 3,
            "description": (
                "You can replace one wizard cantrip at the end of a long rest "
                "from the wizard spell list."
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# CUSTOM_LINEAGE — TCE flexible race-replacement rules
# ---------------------------------------------------------------------------
CUSTOM_LINEAGE: dict = {
    "description": (
        "Instead of choosing a standard race, you can create a custom lineage "
        "with flexible ability scores. Work with your DM to define your "
        "creature's origins."
    ),
    "ability_bonus": "+2 to one ability score of your choice",
    "size": "Small or Medium (your choice)",
    "speed": 30,
    "feat": "One feat of your choice (for which you qualify)",
    "darkvision_or_skill": (
        "Either darkvision (60 ft.) or one skill proficiency of your choice"
    ),
    "languages": ["Common", "One language of your choice"],
}

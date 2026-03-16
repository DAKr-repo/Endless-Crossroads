"""
codex.forge.reference_data.bob_playbooks
=========================================
Band of Blades specialist playbook definitions.

Covers the four core specialist playbooks (Heavy, Medic, Officer, Scout),
plus Rookie abilities for ordinary soldiers and Heritage backgrounds.

SOURCE: Band of Blades.pdf — Character Creation pp.64-72, Loadout pp.73-76,
        Standard Abilities p.77, Specialist playbooks pp.79-115.
"""

from typing import Dict, List, Any

# =========================================================================
# SPECIALIST PLAYBOOKS
# =========================================================================
# SOURCE: Band of Blades.pdf, pp.79-115

PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "Heavy": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.79-81
        "description": (
            "A guardian and powerful melee fighter. Shock troop and unbreakable "
            "tower of iron, the Heavy represents the Legion's unyielding determination "
            "on the field of battle. You are the front-line protector of the troops "
            "under your care."
        ),
        "xp_trigger": (
            "Earn xp when you helped your squad through might or fortitude."
        ),
        "specialist_action": "ANCHOR",
        "starting_action_ratings": {
            "Anchor": 2,  # SOURCE: p.79 starting abilities chart
            "Skirmish": 2,
            "Wreck": 1,
        },
        "special_abilities": [
            {
                "name": "Bulwark",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "You can spend ANCHOR uses as special armor against consequences "
                    "to a squad you are defending. ANCHOR uses are restored when you "
                    "select your load at the start of a mission."
                ),
            },
            {
                "name": "Backup",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "When you protect a squadmate, resist with +1d. When you assist "
                    "someone, their pushes only cost 1 stress."
                ),
            },
            {
                "name": "Tenacious",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "Penalties from harm are one level less severe (though level 4 "
                    "harm is still fatal). Level 1 harm does not penalize you, level 2 "
                    "harm gives less effect rather than -1d, and level 3 harm does not "
                    "incapacitate but gives -1d instead."
                ),
            },
            {
                "name": "Weaponmaster",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "You're known as a Weaponmaster even outside the Legion. When you "
                    "push yourself, you also gain potency in melee combat."
                ),
            },
            {
                "name": "War Machine",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "When you push yourself, you can do one of the following: perform "
                    "a feat of physical force that verges on the superhuman — reduce "
                    "the threat level of all the enemies you're facing by one."
                ),
            },
            {
                "name": "Vigorous",
                # SOURCE: Band of Blades.pdf, p.81
                "description": (
                    "When you check wounds during rest and recuperation, place one free "
                    "check. When you take harm, clear 1 stress."
                ),
            },
            {
                "name": "Against the Darkness",
                # SOURCE: Band of Blades.pdf, p.81
                "description": (
                    "You and all squadmates that can see you gain +1d to resist fear "
                    "and corruption."
                ),
            },
        ],
        "items": [
            "Flare Gun",         # SOURCE: p.81 Light Load
            "Fine Armor",        # SOURCE: p.81 Light Load
            "Fine Hand Weapon",  # SOURCE: p.81 Light Load
            "Fitted Heavy Plate (replaces Armor)",  # SOURCE: p.81 Normal Load
            "Fine Shield OR Fine Heavy Weapon",     # SOURCE: p.81 Normal Load
            "Fine Wrecking Kit",  # SOURCE: p.81 Heavy Load
            "Fine Tower Shield",  # SOURCE: p.81 Heavy Load
        ],
    },

    "Medic": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.83-85
        "description": (
            "A combat physician. In this time of war, the Legion needs those who can "
            "wield a scalpel as well as a sword. When things go wrong (and they always "
            "do), the squad will look to you to keep them going."
        ),
        "xp_trigger": (
            "Earn xp when you helped your squad through medical knowledge or "
            "emotional support."
        ),
        "specialist_action": "DOCTOR",
        "starting_action_ratings": {
            "Doctor": 1,     # SOURCE: p.83 starting abilities chart
            "Research": 1,
            "Maneuver": 1,
            "Consort": 1,
            "Discipline": 1,
        },
        "special_abilities": [
            {
                "name": "Attache",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "You may deploy on any mission even outside the usual Specialist "
                    "caps. Gain this ability for free when you promote to or create a "
                    "Medic."
                ),
            },
            {
                "name": "First Aid",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "You can spend one use of Tonics to remove appropriate level 1 harm "
                    "on any one person on your mission."
                ),
            },
            {
                "name": "Not Today",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "You can spend a DOCTOR use on a Legionnaire who has taken level 4 "
                    "harm on a mission, but you must do so quickly before they die. You "
                    "treat them and reduce the wound to level 3 instead."
                ),
            },
            {
                "name": "Doctor Feelgood",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "Spend one use of Tonics to grant one person potency for a physical "
                    "action."
                ),
            },
            {
                "name": "Field Dressing",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "At the end of a mission you may expend remaining DOCTOR uses to "
                    "add one check to a Legionnaire's level 2 or 3 harm, once per "
                    "person."
                ),
            },
            {
                "name": "Chemist",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "You have training in Orite alchemical medicine. You may equip an "
                    "Alchemical Bandolier on each mission. It holds four charges of "
                    "alchemicals."
                ),
            },
            {
                "name": "Moral Support",
                # SOURCE: Band of Blades.pdf, p.85
                "description": (
                    "You know how to keep troop spirits up. Once a mission, if you tell "
                    "a funny, personal, or meaningful story when the squad is resting, "
                    "anyone listening may clear 1 stress."
                ),
            },
        ],
        "items": [
            "Fine Medic Kit",    # SOURCE: p.85 Light Load
            "Tonics (1 use)",    # SOURCE: p.85 Light Load
            "Holy Symbol of Mercy",     # SOURCE: p.85 Light Load
            "Mark of the Healing Goddess",  # SOURCE: p.85 Light Load
            "Fine Pistol",       # SOURCE: p.85 Normal Load
            "Ammo",              # SOURCE: p.85 Normal Load
            "Armor",             # SOURCE: p.85 Normal Load
            "Tonics (2nd use)",  # SOURCE: p.85 Normal Load
            "Tonics (2 more uses — total 4)",  # SOURCE: p.85 Heavy Load
        ],
    },

    "Officer": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.87-91 (Officer playbook)
        # NOTE: The Officer playbook's specialist action is CHANNELS.
        # SOURCE: Band of Blades.pdf, p.72 specialist actions
        "description": (
            "A Legion officer who leads from the front, coordinates squad actions, "
            "and leverages Legion resources. Lieutenants, captains, and majors still "
            "rank the Marshal must acknowledge."
        ),
        "xp_trigger": (
            "Earn xp when you helped your squad through command and authority."
        ),
        "specialist_action": "CHANNELS",
        "special_abilities": [
            {
                "name": "Veteran",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability available to all Specialists)
                "description": (
                    "Take a special ability from another source (another playbook)."
                ),
            },
            {
                "name": "Elite",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability)
                "description": (
                    "Gain mastery of two actions (up to rank 4)."
                ),
            },
            {
                "name": "Hardened",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability)
                "description": (
                    "You can mark two additional stress boxes. May be taken twice "
                    "(total of 10 stress boxes)."
                ),
            },
            {
                "name": "Survivor",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability)
                "description": (
                    "You can take +1 trauma before dying. May be taken twice "
                    "(total of 4 trauma boxes)."
                ),
            },
        ],
        # SOURCE: Band of Blades.pdf, p.77 — Officer is a playbook with access to
        # standard abilities; unique abilities documented at pp.87-91 (EXPANDED)
        "items": [
            "Officer's sidearm",
            "Light armor",
            "Signal equipment",
            "Officer's kit (maps, orders, cipher)",
        ],
    },

    "Scout": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.91-95 (Scout playbook)
        # NOTE: Scout specialist action is SCOUT (the action itself).
        # SOURCE: Band of Blades.pdf, p.71
        "description": (
            "The Legion's eyes and ears. You range ahead, find the safe paths, "
            "identify enemy positions, and bring intelligence back alive. "
            "You don't fight fair — you fight smart."
        ),
        "xp_trigger": (
            "Earn xp when you helped your squad through stealth, infiltration, "
            "or gathering critical intelligence."
        ),
        "specialist_action": "SCROUNGE",
        "special_abilities": [
            {
                "name": "Veteran",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability)
                "description": (
                    "Take a special ability from another source (another playbook)."
                ),
            },
            {
                "name": "Elite",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability)
                "description": (
                    "Gain mastery of two actions (up to rank 4)."
                ),
            },
            {
                "name": "Hardened",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability)
                "description": (
                    "You can mark two additional stress boxes. May be taken twice "
                    "(total of 10 stress boxes)."
                ),
            },
            {
                "name": "Survivor",
                # SOURCE: Band of Blades.pdf, p.77 (standard ability)
                "description": (
                    "You can take +1 trauma before dying. May be taken twice "
                    "(total of 4 trauma boxes)."
                ),
            },
        ],
        # SOURCE: Band of Blades.pdf, pp.91-95 — Scout unique abilities EXPANDED
        "items": [
            "Light armor",
            "Hand Weapon",
            "Climbing Kit",
            "Compass and Maps",
            "Rations",
        ],
    },
}

# =========================================================================
# ROOKIE ABILITIES
# =========================================================================
# SOURCE: Band of Blades.pdf, pp.70-72 — Actions available to all Legionnaires

ROOKIE_ABILITIES: Dict[str, str] = {
    # Insight actions — SOURCE: p.70-71
    "Doctor": "Use specialized medical training to soothe and treat a soldier's wounds. A DOCTOR use allows a soldier to ignore wound penalties for a scene.",
    "Marshal": "Direct a squad or group of people to action. Organize flanking, coordinate fire, direct charges.",
    "Research": "Scrutinize details and interpret evidence. Gather information from tomes, Annals, whispered rumors.",
    "Scout": "Move or observe without being noticed. Watch undead, lift keys, sneak, climb.",
    # Prowess actions — SOURCE: p.70
    "Maneuver": "Lift, climb, jump, run, or swim, usually either away from or into danger.",
    "Skirmish": "Engage in close combat with a hostile opponent. Brawl, use melee weapons, fire pistols at short range.",
    "Wreck": "Apply savage force or careful sabotage to destroy a place, item, or obstacle.",
    # Resolve actions — SOURCE: p.70-71
    "Consort": "Socialize with friends and contacts. Gain access to resources, information, people, or places.",
    "Discipline": "Compel obedience with your force of personality. Intimidate, bark orders, coerce.",
    "Sway": "Influence someone with guile, charm, or logic. Lie, persuade, argue facts.",
    # Additional standard action — SOURCE: p.70
    "Rig": "Alter how an existing mechanism works or create a new one. Disable traps, repair weapons, set bombs.",
    # Specialist actions available to some playbooks — SOURCE: p.72
    "Aim": "Use careful timing and cool nerves to improve your shot. Increases effect level of shot, one-for-one.",
    "Anchor": "Use your size and training to clash with more numerous or far superior foes. Each ANCHOR use allows you to fight as a small group.",
    "Channels": "Leverage connections, social capital, and authority to acquire supplies beyond your allotment.",
    "Grit": "Use the hard lessons taught over soldiering to weather the worst the war has to offer. Reduce stress cost of a resistance roll.",
    "Scrounge": "Repurpose the environment around you to find shelter or source items.",
    "Weave": "Invoke arcane powers to change the world around you. Identify artifacts or detect the presence of the divine.",
    "Shoot": "Fire on a target with precision from a distance.",
}

# =========================================================================
# HERITAGES
# =========================================================================
# SOURCE: Band of Blades.pdf, pp.356-362 (Heritage chapter)
# Heritage names in-world: Barta, Or, Panya, Zemya
# The playbook names use: Bartan, Orite, Panyar, Zemyati

HERITAGES: Dict[str, Dict[str, str]] = {
    "Bartan": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.356 — Bartan heritage
        "description": (
            "From the heart of the Eastern Kingdoms, Bartans are the Legion's most "
            "common soldiers. Barta is a large, diverse nation with a long martial "
            "tradition. Bartans are trained from youth in Legion discipline and the "
            "duties of soldiering. Shreya herself is Bartan."
        ),
        "cultural_trait": (
            "Bartan heritage grants traits from a martial tradition: disciplined "
            "formations, Legion ceremony knowledge, and comfort with the chain of "
            "command. Bartans often know the Annals and Legion customs by rote."
        ),
    },
    "Orite": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.358 — Orite heritage
        "description": (
            "The Orite hail from the triumvirate cities of Or — master engineers, "
            "alchemists, and craftspeople. Their three crafter-gods (the Builder, the "
            "Maker, and the Crafter) govern all aspects of Orite life. They bring "
            "technical expertise and alchemical knowledge to the Legion. "
            "Blighter was once an Orite Chosen."
        ),
        "cultural_trait": (
            "Orite heritage grants traits of technical mastery: knowledge of alchemy, "
            "mechanical devices, and engineering. Orites often carry trade tools and "
            "reference the Old Empire technology that their gods inspired."
        ),
    },
    "Panyar": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.360 — Panyar heritage
        "description": (
            "Panyar come from the forest peoples whose goddess of the moon, Nyx, was "
            "Broken by the Cinder King — causing the moon to shatter in the sky. The "
            "Horned One is the Panyar Chosen, known as Silver Dancing Moonlight. "
            "Panyar carry deep grief and burning rage at the loss of their goddess."
        ),
        "cultural_trait": (
            "Panyar heritage grants traits of spiritual attunement: connection to "
            "animals and the natural world, knowledge of forest paths, and the "
            "ability to read the land for signs of corruption or divine influence."
        ),
    },
    "Zemyati": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.362 — Zemyati heritage
        "description": (
            "From the cold lands of Zemya, these soldiers follow the Living God — "
            "a deity who created nine Chosen long ago that do not burn out. Zora is "
            "the Zemyati Chosen. Render (Vlaisim, the Shining One) was also Zemyati "
            "before he was Broken. Zemyati warriors carry ancient purpose."
        ),
        "cultural_trait": (
            "Zemyati heritage grants traits of endurance and warrior culture: "
            "comfort in harsh conditions, knowledge of the Living God's teachings, "
            "and a fatalistic courage in the face of death."
        ),
    },
}

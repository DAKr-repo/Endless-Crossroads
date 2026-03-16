"""
codex.forge.reference_data.stc_orders
=======================================
Expanded Radiant Order reference data for the Cosmere RPG (Stormlight).

SOURCE AUTHORITY:
  Primary: STC_Stormlight_Starter_Rules_digital.pdf (Cosmere RPG v1.01, 2025)
  Lore:    Stormlight Archive novels by Brandon Sanderson
  Full rules: STC_Stormlight_Handbook_digital.pdf (ch.5-6 — Radiant paths,
              surges, ideals; too large to extract directly)

SOURCED vs EXPANDED notation:
  # SOURCE: — directly verified from a PDF page
  # EXPANDED: — not in Starter Rules; derived from novels/handbook description
               or invented for this codebase.

CONFIRMED from Starter Rules / GM Tools:
  - Radiant characters have "Surge Skills" and "Investiture" on their stat blocks
    SOURCE: Starter Rules p.12 char sheet, GM Tools p.5 (Kaiana stat block)
  - Kaiana (Starter adventure) uses Surges: Illumination + Progression
    SOURCE: GM Tools p.5 stat block
  - Ylt (Starter adventure) uses Surges: Cohesion + Illumination + Tension
    SOURCE: GM Tools p.17 stat block — confirms Willshaper/Elsecaller surge combo
  - Investiture pool confirmed as a stat SOURCE: Starter Rules p.16
  - All 10 order names and their surge pairs: SOURCE Stormlight Archive novels
    (canonical Sanderson lore; confirmed in full Handbook which we cannot extract)
  - First Ideal (the Immortal Words): "Life before death. Strength before weakness.
    Journey before destination." — SOURCE: Stormlight Archive novels

IMPORTANT: per_ideal_powers are ALL EXPANDED.
  The Starter Rules do not include Radiant path rules (those are in the Handbook).
  The specific power names, descriptions, and stormlight costs are our engine's
  game design abstraction. Verify all against the full Handbook when available.

Each order entry contains:
  - description: Narrative flavor for the order
  - surges: Two surges available to members of this order  [SOURCE: novels]
  - ideals: Five ideal texts (index 1-5)                  [SOURCE: novels + EXPANDED]
  - per_ideal_powers: Dict mapping ideal level to powers  [EXPANDED]
  - starting_equipment: List of starting gear names       [EXPANDED]
  - oath_text: First Ideal + order-specific oath          [SOURCE: novels + EXPANDED]
"""

from typing import Any, Dict, List


# =========================================================================
# SURGE TYPES
# SOURCE: Stormlight Archive novels (canonical Sanderson lore).
# Confirmed in STC RPG: Starter Rules p.16 mentions Investiture/surgebinding;
# GM Tools p.5 Kaiana stat block lists "Surge Skills: Illumination +4 (1 rank),
# Progression +5 (2 ranks)"; GM Tools p.17 Ylt stat block lists
# "Surges: Cohesion +6 (3 ranks), Illumination +6 (2 ranks), Tension +5 (3 ranks)".
# The 10 surge names and their assignments to orders are canonical from novels.
# SOURCE: Starter Rules p.57-58 — "Surge Skills" appear on adversary stat blocks.
# =========================================================================

SURGE_TYPES: Dict[str, Dict[str, Any]] = {
    "Adhesion": {
        "setting": "roshar",
        "description": "The surge of pressure and vacuum. Allows binding objects together "
                       "and controlling atmospheric pressure.",
        # SOURCE: Stormlight Archive novels — Windrunner/Bondsmith surge
    },
    "Gravitation": {
        "setting": "roshar",
        "description": "The surge of gravity and lashing. Allows manipulation of gravitational "
                       "pull on objects and people, including self-flight via Lashings.",
        # SOURCE: Stormlight Archive novels — Windrunner/Skybreaker surge
    },
    "Division": {
        "setting": "roshar",
        "description": "The surge of destruction and decay. Causes rapid decomposition, "
                       "disintegration, or combustion in targeted materials.",
        # SOURCE: Stormlight Archive novels — Skybreaker/Dustbringer surge
    },
    "Abrasion": {
        "setting": "roshar",
        "description": "The surge of friction and smoothness. Grants frictionless movement, "
                       "slick surfaces, or extreme grip as needed.",
        # SOURCE: Stormlight Archive novels — Dustbringer/Edgedancer surge
    },
    "Progression": {
        "setting": "roshar",
        "description": "The surge of growth and healing. Accelerates living tissue growth, "
                       "heals wounds rapidly, and enhances plant growth.",
        # SOURCE: confirmed in GM Tools p.5 — Kaiana uses Progression surge
    },
    "Illumination": {
        "setting": "roshar",
        "description": "The surge of light and sound. Creates complex illusions, alters "
                       "perception, and bends light around objects.",
        # SOURCE: confirmed in GM Tools p.5 and p.17 — Kaiana and Ylt use Illumination surge
    },
    "Transformation": {
        "setting": "roshar",
        "description": "The surge of soulcasting. Converts matter from one form to another "
                       "by convincing the object's spren of its new nature.",
        # SOURCE: Stormlight Archive novels — Lightweaver/Elsecaller surge
    },
    "Transportation": {
        "setting": "roshar",
        "description": "The surge of motion and spren. Allows near-instantaneous travel "
                       "through the Cognitive Realm via Oathgates.",
        # SOURCE: Stormlight Archive novels — Elsecaller/Willshaper surge
    },
    "Cohesion": {
        "setting": "roshar",
        "description": "The surge of strong axial interconnection. Temporarily softens stone "
                       "and other rigid materials for shaping.",
        # SOURCE: confirmed in GM Tools p.17 — Ylt uses Cohesion surge (Willshaper)
    },
    "Tension": {
        "setting": "roshar",
        "description": "The surge of soft axial interconnection. Hardens soft materials into "
                       "rigid forms temporarily.",
        # SOURCE: confirmed in GM Tools p.17 — Ylt uses Tension surge (Willshaper/Stoneward)
    },
}


# =========================================================================
# RADIANT ORDERS — Full expanded reference data
# =========================================================================

ORDERS: Dict[str, Dict[str, Any]] = {

    "windrunner": {
        "setting": "roshar",
        "description": (
            "Windrunners bond Honorspren and wield the surges of Gravitation and Adhesion. "
            "They are protectors above all else, drawn to shield the weak and lead in battle. "
            "Dalinar Kholin's son Kaladin Stormblessed is the most famous modern Windrunner."
        ),
        "surges": ["Gravitation", "Adhesion"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will protect those who cannot protect themselves.",
            3: "I will protect even those I hate, so long as it is right.",
            4: "I accept that there will be those I cannot protect.",
            5: "I will stand watch and let the storm break against me.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Basic Lashing",
                    "description": "Redirect gravity for yourself or a touched object. "
                                   "Fly upward, fall sideways, or pin an enemy to a wall.",
                    "stormlight_cost": 2,
                },
            ],
            2: [
                {
                    "name": "Full Lashing",
                    "description": "Bind two objects or surfaces together with incredible "
                                   "adhesive force that only stormlight can dissolve.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Reverse Lashing",
                    "description": "Create a point of attraction. Arrows, debris, and "
                                   "smaller objects are pulled toward the lashed point.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Windrunner's Shield",
                    "description": "Surround allies with a bubble of altered gravity that "
                                   "deflects incoming ranged attacks and thrown weapons.",
                    "stormlight_cost": 5,
                },
            ],
            5: [
                {
                    "name": "Honorspren Bond",
                    "description": "Your bond with your Honorspren reaches its fullest "
                                   "expression. Your Sylblade becomes permanent; you can "
                                   "lash others without touch at no additional cost.",
                    "stormlight_cost": 0,
                },
            ],
        },
        "starting_equipment": ["Spear", "Windrunner Glyph Brooch", "Leather Vest"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will protect those who cannot protect themselves."
        ),
    },

    "skybreaker": {
        "setting": "roshar",
        "description": (
            "Skybreakers bond Highspren and wield the surges of Gravitation and Division. "
            "They are arbiters of law and justice, sworn to an external code above personal "
            "loyalty. Nale, one of the Heralds, leads this order in the modern era."
        ),
        "surges": ["Gravitation", "Division"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will put the law before all else.",
            3: "I will seek justice, and where I find it, I will enforce it.",
            4: "I will be the sword of the law, merciful only when the law demands it.",
            5: "I am the law. My code is supreme and I will enforce it without exception.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Gravitation Lashing",
                    "description": "Basic self-Lashing for flight. Redirect your own "
                                   "gravity to fly at speed.",
                    "stormlight_cost": 2,
                },
            ],
            2: [
                {
                    "name": "Verdict Strike",
                    "description": "Channel Division through a weapon strike. On a hit, "
                                   "the target's armor or shield is partially disintegrated.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Erosion",
                    "description": "Project Division at range, causing rapid decay in "
                                   "stone, wood, or organic material. DC 13 Constitution "
                                   "or take ongoing damage.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Highspren Chains",
                    "description": "Your Highspren manifests as chains of law that bind "
                                   "a target in place. Target is restrained for 2 rounds.",
                    "stormlight_cost": 5,
                },
            ],
            5: [
                {
                    "name": "Living Law",
                    "description": "You become a manifest embodiment of the code you "
                                   "have sworn. Lawbreakers in your presence feel crushing "
                                   "supernatural guilt and suffer disadvantage on all rolls.",
                    "stormlight_cost": 0,
                },
            ],
        },
        "starting_equipment": ["Longsword", "Skybreaker Badge", "Chain Shirt"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will put the law before all else."
        ),
    },

    "dustbringer": {
        "setting": "roshar",
        "description": (
            "Dustbringers bond Ashspren and wield the surges of Division and Abrasion. "
            "Despite the ominous name (which they reject, preferring Releaser), they are "
            "seekers of self-mastery, controlling the destructive power within themselves."
        ),
        "surges": ["Division", "Abrasion"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will master myself before I seek to master others.",
            3: "I accept that destruction is sometimes necessary for growth.",
            4: "I will control my power so that it does not control me.",
            5: "I am the flame that refines, not the fire that consumes.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Frictionless Step",
                    "description": "Remove friction from your feet and legs. Move twice "
                                   "as far on your turn without provoking opportunity attacks.",
                    "stormlight_cost": 2,
                },
            ],
            2: [
                {
                    "name": "Ashspren Combustion",
                    "description": "Touch an object and cause it to rapidly combust. "
                                   "Deals fire damage to adjacent enemies.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Controlled Erosion",
                    "description": "Surgically apply Division to a precise area. Can "
                                   "disintegrate locks, hinges, or a specific section of wall.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Dust Storm",
                    "description": "Create a localized storm of abrasive particles. "
                                   "All enemies in the area take ongoing abrasion damage "
                                   "and have obscured vision.",
                    "stormlight_cost": 5,
                },
            ],
            5: [
                {
                    "name": "Perfect Mastery",
                    "description": "Your control over Division and Abrasion is flawless. "
                                   "You can apply either surge with surgical precision at "
                                   "no stormlight cost for minor applications.",
                    "stormlight_cost": 0,
                },
            ],
        },
        "starting_equipment": ["Axe", "Ashspren Charm", "Leather Bracers"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will master myself before I seek to master others."
        ),
    },

    "edgedancer": {
        "setting": "roshar",
        "description": (
            "Edgedancers bond Cultivationspren and wield the surges of Abrasion and "
            "Progression. They remember the forgotten and heal the broken, gliding across "
            "surfaces with supernatural grace. Lift is the most famous modern Edgedancer."
        ),
        "surges": ["Abrasion", "Progression"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will remember those who have been forgotten.",
            3: "I will listen to those who have been ignored.",
            4: "I will heal those who cannot heal themselves.",
            5: "I will not let even the least of them fall.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Edgedancer's Grace",
                    "description": "Glide across any surface with supernatural speed "
                                   "and grace. Ignore difficult terrain; vertical surfaces "
                                   "become traversable.",
                    "stormlight_cost": 2,
                },
            ],
            2: [
                {
                    "name": "Regrowth",
                    "description": "Channel Progression into a touched target, rapidly "
                                   "healing wounds. Restore significant HP to an ally.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Lifegrowth",
                    "description": "Accelerate plant growth and vegetation in an area. "
                                   "Vines and roots entangle enemies; allies gain cover.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Memory Palace",
                    "description": "Your perfect memory allows you to recall any face, "
                                   "name, or detail encountered. Gain advantage on all "
                                   "knowledge checks regarding people.",
                    "stormlight_cost": 0,
                },
            ],
            5: [
                {
                    "name": "Complete Restoration",
                    "description": "Your Regrowth reaches its fullest power. Heal a "
                                   "target completely, or slow the progression of any "
                                   "magical disease or corruption.",
                    "stormlight_cost": 5,
                },
            ],
        },
        "starting_equipment": ["Staff", "Cultivationspren Blossom Token", "Dancer's Slippers"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will remember those who have been forgotten."
        ),
    },

    "truthwatcher": {
        "setting": "roshar",
        "description": (
            "Truthwatchers bond Mistspren and wield the surges of Progression and "
            "Illumination. They are the rarest order, sensing truth and falsehood, "
            "and offering healing paired with revelation."
        ),
        "surges": ["Progression", "Illumination"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will seek the truth, even when it is uncomfortable.",
            3: "I will share what I discover with those who need it.",
            4: "I will not let falsehood stand unchallenged in my presence.",
            5: "I am the lantern in the dark. Truth flows through me.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Truthsense",
                    "description": "Sense whether a statement is believed to be true "
                                   "by the speaker. Does not detect practiced liars perfectly.",
                    "stormlight_cost": 1,
                },
            ],
            2: [
                {
                    "name": "Mistspren Healing",
                    "description": "Channel Progression to heal an ally. Equivalent to "
                                   "Regrowth but accompanied by revealing visions of the "
                                   "target's true self.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "True Sight",
                    "description": "Bend Illumination inward. See through mundane "
                                   "disguises and illusions for the duration.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Revelation Burst",
                    "description": "Flash Illumination outward, blinding enemies and "
                                   "revealing invisible or hidden creatures.",
                    "stormlight_cost": 4,
                },
            ],
            5: [
                {
                    "name": "Prophetic Vision",
                    "description": "Meditate to receive fragmented visions of likely "
                                   "futures. Gain advantage on the next three rolls of "
                                   "your choice within 24 hours.",
                    "stormlight_cost": 5,
                },
            ],
        },
        "starting_equipment": ["Staff", "Mistspren Crystal", "Scholar's Robes"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will seek the truth, even when it is uncomfortable."
        ),
    },

    "lightweaver": {
        "setting": "roshar",
        "description": (
            "Lightweavers bond Cryptics (logicspren) and wield the surges of Illumination "
            "and Transformation. They speak their truths — not oaths, but honest "
            "admissions — to advance. Shallan Davar is the most prominent modern Lightweaver."
        ),
        "surges": ["Illumination", "Transformation"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will speak my truth to my spren.",
            3: "I accept what I have done and what I am.",
            4: "I will not hide behind masks of my own making.",
            5: "I am the artist and the art. I will not fear my reflection.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Lightweaving",
                    "description": "Create visual and auditory illusions of any image "
                                   "you can clearly envision. Illusions last until dismissed "
                                   "or until you run out of stormlight.",
                    "stormlight_cost": 2,
                },
            ],
            2: [
                {
                    "name": "Soulcast (Minor)",
                    "description": "Transform a small quantity of one simple material "
                                   "into another (stone to air, water to grain). "
                                   "DC 10 Transformation check.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Memory Sketch",
                    "description": "Perfectly reproduce the appearance of anyone you "
                                   "have met as a Lightweaving. Usable as a disguise "
                                   "or for identification.",
                    "stormlight_cost": 2,
                },
            ],
            4: [
                {
                    "name": "Pattern Strike",
                    "description": "Your Cryptic manifests as a solid blade. Attack "
                                   "with advantage; the blade ignores mundane armor.",
                    "stormlight_cost": 4,
                },
            ],
            5: [
                {
                    "name": "Grand Illusion",
                    "description": "Create a sustained illusion affecting all senses "
                                   "across a large area. Enemies must make an Intellect "
                                   "check to see through it.",
                    "stormlight_cost": 5,
                },
            ],
        },
        "starting_equipment": ["Dagger", "Sketchbook", "Charcoal Sticks", "Fine Dress Uniform"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will speak my truth to my spren."
        ),
    },

    "elsecaller": {
        "setting": "roshar",
        "description": (
            "Elsecallers bond Inkspren and wield the surges of Transformation and "
            "Transportation. They are scholars and strategists who study the Cognitive "
            "Realm and seek to elevate humanity. Jasnah Kholin is the most famous Elsecaller."
        ),
        "surges": ["Transformation", "Transportation"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will reach my potential and help others reach theirs.",
            3: "I accept that knowledge requires sacrifice.",
            4: "I will act on what I know, not what I feel.",
            5: "I am humanity's edge. I will sharpen myself without limit.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Soulcasting",
                    "description": "Transform matter from one substance to another. "
                                   "You perceive the Cognitive aspect of objects and "
                                   "negotiate their transformation.",
                    "stormlight_cost": 3,
                },
            ],
            2: [
                {
                    "name": "Cognitive Step",
                    "description": "Step briefly into the Cognitive Realm and re-emerge "
                                   "up to 30 feet away. Bypass obstacles and barriers.",
                    "stormlight_cost": 4,
                },
            ],
            3: [
                {
                    "name": "Advanced Soulcasting",
                    "description": "Soulcast complex or large materials. Can transform "
                                   "flesh into stone or air. DC 15 Transformation check.",
                    "stormlight_cost": 5,
                },
            ],
            4: [
                {
                    "name": "Oathgate Key",
                    "description": "With an Inkspren's help, activate a dormant Oathgate "
                                   "to transport the party to a linked location.",
                    "stormlight_cost": 6,
                },
            ],
            5: [
                {
                    "name": "Cognitive Mastery",
                    "description": "You perceive both the Physical and Cognitive realms "
                                   "simultaneously. Immune to illusions; can interact "
                                   "with spren as naturally as physical objects.",
                    "stormlight_cost": 0,
                },
            ],
        },
        "starting_equipment": ["Stiletto", "Inkspren Companion", "Scholar's Satchel", "Research Journal"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will reach my potential and help others reach theirs."
        ),
    },

    "willshaper": {
        "setting": "roshar",
        "description": (
            "Willshapers bond Lightspren (Reachers) and wield the surges of Transportation "
            "and Cohesion. They are explorers, freedom-seekers, and individualists who "
            "reject restriction and embrace the journey itself."
        ),
        "surges": ["Transportation", "Cohesion"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will seek freedom for myself and for others.",
            3: "I will not allow chains — physical or spiritual — to bind the innocent.",
            4: "I will explore what has not been explored.",
            5: "The journey is the destination. I will embrace every step.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Stone Shaping",
                    "description": "Temporarily soften stone with Cohesion, reshaping "
                                   "it like clay. Create handholds, seal passages, or "
                                   "shape simple stone forms.",
                    "stormlight_cost": 2,
                },
            ],
            2: [
                {
                    "name": "Reacher Step",
                    "description": "Your Lightspren assists you in short-range teleportation "
                                   "through the Cognitive Realm. Similar to Cognitive Step "
                                   "but requires the spren's cooperation.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Cohesion Wave",
                    "description": "Release a wave of Cohesion energy that temporarily "
                                   "softens all stone and earth in the area. Enemies in "
                                   "the area sink into softened ground.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Freedom's Call",
                    "description": "Shatter magical bindings, mundane restraints, or "
                                   "compulsions affecting nearby allies. Acts as a group "
                                   "dispel for movement-restricting effects.",
                    "stormlight_cost": 4,
                },
            ],
            5: [
                {
                    "name": "Path Forger",
                    "description": "You can permanently reshape stone and earth, "
                                   "creating or closing tunnels, passes, and paths. "
                                   "Cohesion is maintained without stormlight expenditure "
                                   "for shaping tasks that take more than one minute.",
                    "stormlight_cost": 0,
                },
            ],
        },
        "starting_equipment": ["Shortsword", "Explorer's Pack", "Lightspren Journal"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will seek freedom for myself and for others."
        ),
    },

    "stoneward": {
        "setting": "roshar",
        "description": (
            "Stonewards bond Peakspren and wield the surges of Cohesion and Tension. "
            "They are the immovable pillars of battle, endurance specialists who hold "
            "the line when all others falter."
        ),
        "surges": ["Cohesion", "Tension"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will be there when I am needed.",
            3: "I will not retreat until I choose to.",
            4: "I will be the foundation that others build upon.",
            5: "I am the stone. Let the storms break against me.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Stone Skin",
                    "description": "Channel Tension to temporarily harden your skin "
                                   "and clothing to near-stone durability. Gain significant "
                                   "damage reduction for one round.",
                    "stormlight_cost": 2,
                },
            ],
            2: [
                {
                    "name": "Earthen Grasp",
                    "description": "Soften the earth under an enemy's feet with Cohesion, "
                                   "then harden it around their feet with Tension. "
                                   "Target is restrained.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Immovable Stance",
                    "description": "Plant yourself with surgebinding power. You cannot "
                                   "be moved, knocked prone, or forcibly repositioned "
                                   "for the duration. You also gain bonus HP.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Tension Shield",
                    "description": "Harden the air itself into a rigid barrier using "
                                   "Tension. Creates a temporary wall or shield that "
                                   "blocks attacks for one round.",
                    "stormlight_cost": 4,
                },
            ],
            5: [
                {
                    "name": "Peakspren's Endurance",
                    "description": "Your bond grants you near-invulnerability to being "
                                   "moved or destroyed. When reduced to 0 HP, make a "
                                   "Constitution check to remain at 1 HP instead. "
                                   "Once per long rest.",
                    "stormlight_cost": 0,
                },
            ],
        },
        "starting_equipment": ["Warhammer", "Tower Shield", "Peakspren Stone Amulet", "Heavy Armor"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will be there when I am needed."
        ),
    },

    "bondsmith": {
        "setting": "roshar",
        "description": (
            "Bondsmiths bond the three Godspren (the Stormfather, Nightwatcher, or "
            "Sibling) and wield the surges of Tension and Adhesion. Only three can "
            "ever exist. They unite, connect, and restore what is broken — including "
            "the Nahel bond itself."
        ),
        "surges": ["Tension", "Adhesion"],
        "ideals": {
            1: "Life before death, strength before weakness, journey before destination.",
            2: "I will unite instead of divide.",
            3: "I will mend what has been broken.",
            4: "I accept that not all bonds can be restored, but I will try.",
            5: "I am the connector. Through me, all things may be made whole.",
        },
        "per_ideal_powers": {
            1: [
                {
                    "name": "Bond Sense",
                    "description": "Sense the emotional and spiritual connections "
                                   "between people in your presence. Feel the strength "
                                   "of oaths, friendships, and enmities.",
                    "stormlight_cost": 1,
                },
            ],
            2: [
                {
                    "name": "Adhesion Aura",
                    "description": "Radiate an aura of pressure that binds hostile "
                                   "projectiles and slows enemies. Allies gain a bonus "
                                   "to defense within the aura.",
                    "stormlight_cost": 3,
                },
            ],
            3: [
                {
                    "name": "Spiritual Connection",
                    "description": "Reach across spiritual distances to strengthen "
                                   "the bond of a Radiant whose spren has retreated. "
                                   "Restore their access to stormlight.",
                    "stormlight_cost": 4,
                },
            ],
            4: [
                {
                    "name": "Unity",
                    "description": "Connect the spirits of your allies, allowing them "
                                   "to share hit points, condition immunity, and "
                                   "coordinated action for one round.",
                    "stormlight_cost": 5,
                },
            ],
            5: [
                {
                    "name": "Dawnshard Fragment",
                    "description": "Channel a fragment of a Dawnshard's power through "
                                   "your bond. For one action, you may Command reality "
                                   "at a fundamental level — healing, destroying, or "
                                   "connecting in ways normally impossible.",
                    "stormlight_cost": 8,
                },
            ],
        },
        "starting_equipment": ["Quarterstaff", "Stormfather's Brand", "Commander's Uniform"],
        "oath_text": (
            "Life before death. Strength before weakness. Journey before destination. "
            "I will unite instead of divide."
        ),
    },
}


__all__ = ["ORDERS", "SURGE_TYPES"]

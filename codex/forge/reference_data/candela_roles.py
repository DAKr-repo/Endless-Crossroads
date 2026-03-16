"""
codex.forge.reference_data.candela_roles
=========================================
Candela Obscura — Role and Specialization reference data.

5 roles x 2 specializations = 10 total.
Each specialization carries 4 abilities (first 4 from the book's 6-ability list).

Ability structure:
    name        (str)  — Ability display name
    description (str)  — What it does in play
    cost        (dict) — body/brain/bleed marks required (0 means free / narrative only)
    trigger     (str)  — When / how to activate

SOURCE: Candela Obscura Core Rulebook PDF - November 2023
  Roles & Specialties overview: p.4
  Role cards (names + primary drives): pp.20-24
  Role abilities: p.27
  Specialty abilities: pp.28-32
  Action ratings per specialization: p.25
  Drives per specialization: p.26
"""

from typing import Dict, Any, List

# =========================================================================
# ROLES
# =========================================================================
# Drive lists below use the three ACTIONS of each role's primary drive family.
# Face primary: Cunning (Sway/Read/Hide). SOURCE: p.20, p.27.
# Muscle primary: Nerve (Move/Strike/Control). SOURCE: p.21, p.27.
# Scholar primary drive split by spec: Doctor=Intuition, Professor=Cunning. SOURCE: p.22, p.26.
#   Listed here as the three Intuition actions as Scholar's signature drive family.
# Slink primary split: Criminal=Cunning, Detective=Nerve. SOURCE: p.23, p.26.
#   Listed here as the three Cunning actions as Slink's signature drive family.
# Weird primary: Intuition (Survey/Focus/Sense). SOURCE: p.24, p.26.

ROLES: Dict[str, Dict[str, Any]] = {
    "Face": {
        # SOURCE: Candela Obscura Core Rulebook, p.4, p.20
        "setting": "newfaire",
        "description": (
            "The spokesperson, heart, or charismatic member of the group. "
            "A Face character is generally a confident individual skilled in "
            "acting, persuasion, or motivation."
        ),
        # SOURCE: p.20 — Journalist primary drive: Cunning; Magician primary drive: Intuition
        # Role-level drives listed as the Cunning action triad (Face's dominant drive).
        "drives": ["sway", "read", "hide"],
        "specializations": {
            "Journalist": {
                # SOURCE: Candela Obscura Core Rulebook, p.20, p.28
                "description": (
                    "A bold investigator who knows how to get to the bottom of things. "
                    "Primary drive is Cunning, abilities focused on collecting and "
                    "assessing information."
                ),
                "abilities": [
                    {
                        # SOURCE: p.28
                        "name": "Insider Access",
                        "description": (
                            "Your line of work offers you special privileges. Once per "
                            "assignment, automatically gain access to an important person "
                            "or place by using the Press Credentials gear."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "Once per assignment when access to a person or place is needed.",
                    },
                    {
                        # SOURCE: p.28
                        "name": "Open Book",
                        "description": (
                            "You can get people to open up to you very quickly. When you "
                            "attempt to connect with others by sharing something deeply "
                            "personal, add a number of dice equal to your current Cunning "
                            "resistance to a Sway roll. On a success, they will reciprocate."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "When connecting with another person by sharing something personal.",
                    },
                    {
                        # SOURCE: p.28
                        "name": "Lie Detector",
                        "description": (
                            "When you make a Read roll in an attempt to figure out whether "
                            "a person is telling the truth, gild an additional die. The "
                            "first Cunning you spend on the roll is worth +2d instead of +1d."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "When making a Read roll to detect deception.",
                    },
                    {
                        # SOURCE: p.28
                        "name": "Press Conference",
                        "description": (
                            "You can spend 1 Cunning to gather a large group of people "
                            "together to make announcements, ask questions, or stage a "
                            "distraction. All Cunning rolls you make at this assembly take +1d."
                        ),
                        "cost": {"cunning": 1},
                        "trigger": "When you need to gather a group for announcements or a distraction.",
                    },
                ],
            },
            "Magician": {
                # SOURCE: Candela Obscura Core Rulebook, p.20, p.28
                "description": (
                    "A talented entertainer who knows how to deflect attention and create "
                    "illusions. Primary drive is Intuition, abilities focused on performing "
                    "and detecting tricks."
                ),
                "abilities": [
                    {
                        # SOURCE: p.28
                        "name": "Misdirection",
                        "description": (
                            "When you use your words or actions to distract a target from "
                            "what is actually happening here, make a Hide roll. The first "
                            "Cunning you or an ally spends on this roll is worth +2d instead of +1d."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "When distracting a target from what is actually happening.",
                    },
                    {
                        # SOURCE: p.28
                        "name": "Escape Artist",
                        "description": (
                            "Spend 1 Nerve to automatically escape ropes, cuffs, manacles, "
                            "or a creature that has grappled you."
                        ),
                        "cost": {"nerve": 1},
                        "trigger": "When physically restrained or grappled.",
                    },
                    {
                        # SOURCE: p.28
                        "name": "Practiced Patter",
                        "description": (
                            "You've long rehearsed for a moment like this. When making a "
                            "Sway or Hide roll, you may spend Intuition instead of Cunning."
                        ),
                        "cost": {"intuition": 0},
                        "trigger": "When making a Sway or Hide roll.",
                    },
                    {
                        # SOURCE: p.28
                        "name": "Uncanny Eye",
                        "description": (
                            "You may spend 1 Intuition to ask the GM a question: "
                            "How can I leverage something here to my advantage? "
                            "What here doesn't work the way it appears? What is out of place here?"
                        ),
                        "cost": {"intuition": 1},
                        "trigger": "When surveying a scene for hidden advantages or inconsistencies.",
                    },
                ],
            },
        },
    },

    "Muscle": {
        # SOURCE: Candela Obscura Core Rulebook, p.4, p.21
        "setting": "newfaire",
        "description": (
            "The protector, fighter, or daring member of the group. A Muscle character "
            "is generally an intrepid individual skilled in combat, tactics, or physical activities."
        ),
        # SOURCE: p.21 — Explorer primary drive: Nerve; Soldier primary drive: Intuition
        # Role-level drives listed as the Nerve action triad (Muscle's dominant drive).
        "drives": ["move", "strike", "control"],
        "specializations": {
            "Explorer": {
                # SOURCE: Candela Obscura Core Rulebook, p.21, p.29
                "description": (
                    "A fearless daredevil who knows how to navigate difficult and dangerous "
                    "environments. Primary drive is Nerve, abilities focused on endurance "
                    "and confronting danger."
                ),
                "abilities": [
                    {
                        # SOURCE: p.29
                        "name": "Obscure Lexicon",
                        "description": (
                            "When you encounter an ancient or esoteric language, you can "
                            "spend 1 Intuition to understand what it says."
                        ),
                        "cost": {"intuition": 1},
                        "trigger": "When encountering an unknown ancient or esoteric language.",
                    },
                    {
                        # SOURCE: p.29
                        "name": "Field Experience",
                        "description": (
                            "You've traveled the world and been in many dangerous positions "
                            "before. Once per assignment, describe to the group how a previous "
                            "adventure is similar to your current situation and refresh 1 Nerve "
                            "for everyone in your circle."
                        ),
                        "cost": {"nerve": 0},
                        "trigger": "Once per assignment when a past experience is relevant.",
                    },
                    {
                        # SOURCE: p.29
                        "name": "Mind Over Matter",
                        "description": (
                            "When you are told to use a specific action on a roll, you may "
                            "take a Brain mark to utilize an alternative action instead. "
                            "You may also spend the drive that corresponds with your chosen "
                            "action. Describe how you adapt to your situation."
                        ),
                        "cost": {"brain": 1},
                        "trigger": "When forced to use an action that doesn't suit your approach.",
                    },
                    {
                        # SOURCE: p.29
                        "name": "Tenacious",
                        "description": (
                            "When you have 1 or more Bleed marks, gild an additional die "
                            "on Move, Strike, and Control rolls while in danger."
                        ),
                        "cost": {"bleed": 0},
                        "trigger": "Passively when you have 1+ Bleed marks and are in danger.",
                    },
                ],
            },
            "Soldier": {
                # SOURCE: Candela Obscura Core Rulebook, p.21, p.29
                "description": (
                    "A trained warrior who knows how to fight and make tactical decisions. "
                    "Primary drive is Intuition, abilities focused on combat strategy and discipline."
                ),
                "abilities": [
                    {
                        # SOURCE: p.29
                        "name": "Basic Training",
                        "description": (
                            "You have tactical experience in high-pressure situations. "
                            "When you make a Survey roll in a dangerous place, also add "
                            "a number of dice equal to your current Nerve resistance."
                        ),
                        "cost": {"nerve": 0},
                        "trigger": "When making a Survey roll in a dangerous location.",
                    },
                    {
                        # SOURCE: p.29
                        "name": "Geared Up",
                        "description": (
                            "You and one ally in your circle may mark an additional gear "
                            "slot during each assignment."
                        ),
                        "cost": {"body": 0},
                        "trigger": "At the start of an assignment when selecting gear.",
                    },
                    {
                        # SOURCE: p.29
                        "name": "Sharpshooter",
                        "description": (
                            "When you want to make a ranged attack with a weapon, you may "
                            "spend 1 Nerve to steady your aim before shooting, and add "
                            "+2d to your next shot at this target."
                        ),
                        "cost": {"nerve": 1},
                        "trigger": "When making a ranged attack.",
                    },
                    {
                        # SOURCE: p.29
                        "name": "Tactician",
                        "description": (
                            "When you are in a dangerous scenario, you may spend 1 Nerve "
                            "to ask the GM a question: How do I get to safety? What poses "
                            "the largest immediate threat to my circle? Where is the target "
                            "going to move next?"
                        ),
                        "cost": {"nerve": 1},
                        "trigger": "When in a dangerous scenario needing tactical intelligence.",
                    },
                ],
            },
        },
    },

    "Scholar": {
        # SOURCE: Candela Obscura Core Rulebook, p.4, p.22
        "setting": "newfaire",
        "description": (
            "The studious, logical, or intellectual member of the group. A Scholar "
            "character is generally an educated individual skilled in academics, "
            "critical thinking, or technical activities."
        ),
        # SOURCE: p.22 — Doctor primary drive: Intuition; Professor primary drive: Cunning
        # Role-level drives listed as Intuition action triad (Scholar's dominant drive family).
        "drives": ["survey", "focus", "sense"],
        "specializations": {
            "Doctor": {
                # SOURCE: Candela Obscura Core Rulebook, p.22, p.30
                "description": (
                    "A skilled physician who knows how to conduct medical procedures. "
                    "Primary drive is Intuition, abilities focused on anatomy and healing."
                ),
                "abilities": [
                    {
                        # SOURCE: p.30
                        "name": "Patch Up",
                        "description": (
                            "When you have a few moments of calm, you can make a Focus roll "
                            "to heal 1 Body mark on an ally. On a 4-5, spend 2 Intuition to "
                            "accomplish this. On a 6, spend 1 Intuition. On a 3 or less, you "
                            "may take a Brain mark to take the 4-5 result instead."
                        ),
                        "cost": {"intuition": 1},
                        "trigger": "When you have a moment of calm to treat an ally's injury.",
                    },
                    {
                        # SOURCE: p.30
                        "name": "Non-Combatant",
                        "description": (
                            "Your pain spurs others to action. If you haven't hurt anyone "
                            "yet during this assignment, when you take a mark, each of your "
                            "allies in the scene can recover 1 drive point of their choice."
                        ),
                        "cost": {"body": 0},
                        "trigger": "When you take a mark without having hurt anyone this assignment.",
                    },
                    {
                        # SOURCE: p.30
                        "name": "Dissection",
                        "description": (
                            "When you make a Focus roll to dissect a piece of organic matter "
                            "affected by bleed, gild an additional die. You cannot take Bleed "
                            "marks from this inspection."
                        ),
                        "cost": {"focus": 0},
                        "trigger": "When using Focus to dissect bleed-affected organic matter.",
                    },
                    {
                        # SOURCE: p.30
                        "name": "Resuscitation",
                        "description": (
                            "When a nearby ally takes a scar, you can make a Focus roll in "
                            "an attempt to immediately revive them. On a 6, it works — they "
                            "still receive the scar but are back on their feet. On a 4-5, it "
                            "will cost 3 drive points of your choosing. Cannot be used when "
                            "a PC takes their fourth scar."
                        ),
                        "cost": {"intuition": 0},
                        "trigger": "Immediately when a nearby ally takes a scar.",
                    },
                ],
            },
            "Professor": {
                # SOURCE: Candela Obscura Core Rulebook, p.22, p.30
                "description": (
                    "A professional academic who knows a great deal about their chosen "
                    "field of study. Primary drive is Cunning, abilities focused on critical "
                    "thinking and leveraging expertise."
                ),
                "abilities": [
                    {
                        # SOURCE: p.30
                        "name": "Steel Mind",
                        "description": (
                            "Once per assignment, when you should take a Brain mark, you may "
                            "instead burn 1 Intuition resistance to soak it."
                        ),
                        "cost": {"intuition": 0},
                        "trigger": "Once per assignment when you would take a Brain mark.",
                    },
                    {
                        # SOURCE: p.30
                        "name": "University Resources",
                        "description": (
                            "Your university has alumni all over the world. Once per session, "
                            "describe a person you know from your tenure as a professor, and "
                            "ask the GM where they can be found locally."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "Once per session when you need a local expert contact.",
                    },
                    {
                        # SOURCE: p.30
                        "name": "Learn from My Mistakes",
                        "description": (
                            "Any time you get a result of 3 or less on a roll, describe what "
                            "lesson you learned from your failure, and refresh 1 drive point "
                            "of your choice."
                        ),
                        "cost": {"brain": 0},
                        "trigger": "When you roll a 3 or less on any action roll.",
                    },
                    {
                        # SOURCE: p.30
                        "name": "Better Part of Valor",
                        "description": (
                            "When making a Control or Move roll to flee danger, gild a die. "
                            "On this roll, the first Nerve you spend is worth +2d instead of +1d."
                        ),
                        "cost": {"nerve": 0},
                        "trigger": "When making a Control or Move roll to flee danger.",
                    },
                ],
            },
        },
    },

    "Slink": {
        # SOURCE: Candela Obscura Core Rulebook, p.4, p.23
        "setting": "newfaire",
        "description": (
            "The streetsmart, roguish, or nefarious member of the group. A Slink "
            "character is generally a subversive and clever individual skilled in crime, "
            "the underworld, or clandestine activities."
        ),
        # SOURCE: p.23 — Criminal primary drive: Cunning; Detective primary drive: Nerve
        # Role-level drives listed as Cunning action triad (Slink's dominant drive family).
        "drives": ["sway", "read", "hide"],
        "specializations": {
            "Criminal": {
                # SOURCE: Candela Obscura Core Rulebook, p.23, p.31
                "description": (
                    "An accomplished outlaw who knows how to operate successfully in the "
                    "underworld. Primary drive is Cunning, abilities focused on street "
                    "connections and nefarious activities."
                ),
                "abilities": [
                    {
                        # SOURCE: p.31
                        "name": "Street Smarts",
                        "description": (
                            "You know how to keep an eye on your surroundings. Whenever you "
                            "make a Survey roll, you may spend any drive instead of only Intuition."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "When making a Survey roll.",
                    },
                    {
                        # SOURCE: p.31
                        "name": "Leverage",
                        "description": (
                            "On a successful Read roll, you may ask the GM what your target "
                            "truly wants. On any Sway rolls you make using this information, "
                            "also add a number of dice equal to your current Cunning resistance."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "After a successful Read roll against a target.",
                    },
                    {
                        # SOURCE: p.31
                        "name": "Hardened",
                        "description": (
                            "When you take a scar, you may choose not to shift any action "
                            "points as a result."
                        ),
                        "cost": {"body": 0},
                        "trigger": "When you take a scar.",
                    },
                    {
                        # SOURCE: p.31
                        "name": "Born in the Shadows",
                        "description": (
                            "When attempting to avoid security or detection, gild an "
                            "additional Hide die."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "When attempting to avoid security or detection.",
                    },
                ],
            },
            "Detective": {
                # SOURCE: Candela Obscura Core Rulebook, p.23, p.31
                "description": (
                    "An experienced investigator who has an outside perspective on the "
                    "ins and outs of the criminal world. Primary drive is Nerve, abilities "
                    "focused on uncovering the truth and stopping malefactors."
                ),
                "abilities": [
                    {
                        # SOURCE: p.31
                        "name": "Mind Palace",
                        "description": (
                            "When you want to figure out how two clues might relate or what "
                            "path they should point you toward, burn 1 Intuition resistance. "
                            "The GM will give you the information you've deduced."
                        ),
                        "cost": {"intuition": 0},
                        "trigger": "When you need to connect two clues to find a path forward.",
                    },
                    {
                        # SOURCE: p.31
                        "name": "Interrogation",
                        "description": (
                            "When you are questioning someone about information they are "
                            "resistant to revealing, add a number of dice equal to your "
                            "current Cunning resistance to your Read roll."
                        ),
                        "cost": {"cunning": 0},
                        "trigger": "When questioning a resistant subject.",
                    },
                    {
                        # SOURCE: p.31
                        "name": "Back Against the Wall",
                        "description": (
                            "When you are making a high-stakes roll, you may take a Brain "
                            "mark to make any Nerve you spend worth +2d instead of +1d."
                        ),
                        "cost": {"brain": 1},
                        "trigger": "When making a high-stakes roll.",
                    },
                    {
                        # SOURCE: p.31
                        "name": "Inspection",
                        "description": (
                            "You have experience examining crime scenes. When you make a "
                            "Survey roll to gather evidence about what might have happened "
                            "in this location, gild an additional die on the roll."
                        ),
                        "cost": {"nerve": 0},
                        "trigger": "When making a Survey roll at a crime scene or investigation location.",
                    },
                ],
            },
        },
    },

    "Weird": {
        # SOURCE: Candela Obscura Core Rulebook, p.4, p.24
        "setting": "newfaire",
        "description": (
            "The arcane, magickal, or supernatural member of the group. A Weird "
            "character is generally connected to the occult and skilled in enigmatic "
            "lore, psychic abilities, and understanding thinnings."
        ),
        # SOURCE: p.24 — Medium primary drive: Intuition; Occultist primary drive: Intuition
        "drives": ["survey", "focus", "sense"],
        "specializations": {
            "Medium": {
                # SOURCE: Candela Obscura Core Rulebook, p.24, p.32
                "description": (
                    "An adept psychic who knows how to commune with the otherworldly. "
                    "Primary drive is Intuition, abilities focused on divination and "
                    "connecting with spirits."
                ),
                "abilities": [
                    {
                        # SOURCE: p.32
                        "name": "Miasma",
                        "description": (
                            "You can spend 1 Intuition to tell if and how a person or object "
                            "has been affected by bleed."
                        ),
                        "cost": {"intuition": 1},
                        "trigger": "When examining a person or object for bleed corruption.",
                    },
                    {
                        # SOURCE: p.32
                        "name": "Bending Spoons",
                        "description": (
                            "You can make a Sense roll to control an object in the room with "
                            "your mind: flip a switch, knock something over, move a small "
                            "object, put out a light, etc. On a mixed success, you may take "
                            "a Bleed mark to make it a full success instead."
                        ),
                        "cost": {"bleed": 0},
                        "trigger": "When you need to telekinetically manipulate a nearby object.",
                    },
                    {
                        # SOURCE: p.32
                        "name": "Cold Read",
                        "description": (
                            "On a successful Sense roll, you know what ailment, stress, or "
                            "loss a person has in their life, even if they're trying to hide it."
                        ),
                        "cost": {"intuition": 0},
                        "trigger": "On a successful Sense roll against a person.",
                    },
                    {
                        # SOURCE: p.32
                        "name": "Premonitions",
                        "description": (
                            "You have visions of the future. When an ally is about to take "
                            "1 or more marks, burn an Intuition resistance to warn them about "
                            "the coming danger. Then, soak one of these marks."
                        ),
                        "cost": {"intuition": 0},
                        "trigger": "When an ally is about to take marks.",
                    },
                ],
            },
            "Occultist": {
                # SOURCE: Candela Obscura Core Rulebook, p.24, p.32
                "description": (
                    "A highly studied practitioner of the mystic arts who has a fundamental "
                    "knowledge of the supernatural. Primary drive is Intuition, abilities "
                    "focused on ritual and knowledge of the arcane."
                ),
                "abilities": [
                    {
                        # SOURCE: p.32
                        "name": "Ghostblade",
                        "description": (
                            "You can attune a ritual knife to yourself. If you coat it in "
                            "your blood (take a Body mark), it is particularly effective "
                            "against magickal beings and can strike invisible or ethereal entities."
                        ),
                        "cost": {"body": 1},
                        "trigger": "When attuning or wielding the ritual knife against a supernatural entity.",
                    },
                    {
                        # SOURCE: p.32
                        "name": "Blood of the Covenant",
                        "description": (
                            "The first time a dangerous phenomenon inflicts a mark on anyone "
                            "in your circle, you refresh a number of points, in any drive, "
                            "equal to your current Intuition resistance."
                        ),
                        "cost": {"bleed": 0},
                        "trigger": "The first time a phenomenon marks anyone in your circle.",
                    },
                    {
                        # SOURCE: p.32
                        "name": "Speak Their Language",
                        "description": (
                            "You can speak the supernatural language of any phenomenon you "
                            "encounter. Describe what strange or terrifying way you "
                            "communicate with each other."
                        ),
                        "cost": {"bleed": 0},
                        "trigger": "When attempting to communicate with a supernatural phenomenon.",
                    },
                    {
                        # SOURCE: p.32
                        "name": "Play the Bait",
                        "description": (
                            "You know how to draw the attention of a phenomenon — you just "
                            "have to play the bait. Make a Sense roll to bring a nearby "
                            "phenomenon toward you."
                        ),
                        "cost": {"bleed": 1},
                        "trigger": "When you need to draw a nearby phenomenon toward you.",
                    },
                ],
            },
        },
    },
}


# =========================================================================
# CATALYSTS
# =========================================================================
# SOURCE: Candela Obscura Core Rulebook, p.33 (Catalyst character sheet prompt)
# The book defines Catalyst as the reason a character joined Candela Obscura.
# Specific catalyst names are not enumerated in the book — these are EXPANDED
# entries consistent with the game's tone and setting.

CATALYSTS: List[Dict[str, str]] = [
    {
        # SOURCE: Implied by book's Catalyst definition, p.33 — EXPANDED
        "name": "Curiosity",
        "description": (
            "The unknown is an open wound you cannot stop picking at. "
            "You need to know what is behind the veil, regardless of the cost."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Duty",
        "description": (
            "Someone has to stand between the darkness and the innocent. "
            "You have accepted that burden, even if no one asked you to."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Revenge",
        "description": (
            "Something supernatural destroyed something precious to you. "
            "You will hunt it, understand it, and end it."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Guilt",
        "description": (
            "You opened a door you should have left closed. "
            "What came through is your responsibility to contain."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Grief",
        "description": (
            "You lost someone to the phenomena. Investigating keeps you "
            "close to them — or close to the truth of what happened."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Ambition",
        "description": (
            "The phenomena represent power, knowledge, or opportunity "
            "no one else is positioned to claim. You intend to claim it."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Fear",
        "description": (
            "You are terrified of the supernatural — and the only way "
            "to control fear is to understand its source."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Faith",
        "description": (
            "Your beliefs demand you confront the darkness. "
            "This is a sacred charge, not a choice."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Obligation",
        "description": (
            "Someone you love or owe is already inside this world. "
            "You follow to protect them or honor their work."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Obsession",
        "description": (
            "One particular phenomenon has been the center of your life "
            "for years. You cannot stop until you understand it completely."
        ),
    },
]


__all__ = ["ROLES", "CATALYSTS"]

"""
codex.forge.reference_data.candela_circles
===========================================
Candela Obscura — Circle abilities, trust system, and NPC relationships.

Circle abilities represent shared resources that an investigative circle
can develop over time. They are chosen during circle creation and at each
advancement milestone.

SOURCE: Candela Obscura Core Rulebook PDF - November 2023
  Circle creation (Steps 1-5): pp.39-41
  Circle abilities (exact names and text): p.41
  Resources (Stitch/Refresh/Train): p.41
  Circle examples in text: pp.40, 43
  NPC relationships: EXPANDED original content consistent with setting
  Trust mechanics: EXPANDED — consistent with Sway/social mechanics (pp.9, 50)

NOTE ON CIRCLE ABILITIES:
  The book lists exactly 6 circle abilities on p.41:
    Stamina Training, Nobody Left Behind, In This Together,
    Interdisciplinary, Resource Management, One Last Run
  All 6 are sourced directly from p.41. No fabricated abilities appear here.

NOTE ON NPC RELATIONSHIPS AND TRUST:
  The book does not provide a named NPC relationship list or formal trust
  tier system with mechanical names. All NPC entries and the trust mechanics
  dict are EXPANDED original content consistent with the setting.
"""

from typing import Dict, Any, List

# =========================================================================
# CIRCLE ABILITIES
# =========================================================================
# SOURCE: Candela Obscura Core Rulebook, p.41 (Step 4: Choose Circle Abilities)
# All 6 abilities below are sourced directly from p.41.

CIRCLE_ABILITIES: Dict[str, Dict[str, Any]] = {
    "stamina_training": {
        # SOURCE: Candela Obscura Core Rulebook, p.41
        "setting": "newfaire",
        "name": "Stamina Training",
        "description": (
            "Your circle has trained together to push through adversity. "
            "Three gilded dice are available at the beginning of every assignment "
            "that anyone may add as +1d to any roll. Once a die has been rolled, "
            "it is expended."
        ),
        "mechanical_effect": (
            "Three shared gilded dice at the start of each assignment. "
            "Any circle member may take one as +1d on any roll. "
            "Each die is expended on use."
        ),
    },
    "nobody_left_behind": {
        # SOURCE: Candela Obscura Core Rulebook, p.41
        "setting": "newfaire",
        "name": "Nobody Left Behind",
        "description": (
            "Your circle does not abandon its members, no matter the cost. "
            "When a member of your circle drops incapacitated from taking "
            "too many marks, any roll a player makes in the scene to protect "
            "them, or get them out of danger, has +1d."
        ),
        "mechanical_effect": (
            "+1d on any roll made to protect or rescue an incapacitated circle member."
        ),
    },
    "in_this_together": {
        # SOURCE: Candela Obscura Core Rulebook, p.41
        "setting": "newfaire",
        "name": "In This Together",
        "description": (
            "Your circle has learned to draw strength from one another. "
            "When you spend drive to help an ally on a roll, on a result of "
            "3 or less, you both earn back 1 drive point of your choice."
        ),
        "mechanical_effect": (
            "When assisting an ally: on a result of 3 or less, both the helper "
            "and the roller each earn back 1 drive point of their choice."
        ),
    },
    "interdisciplinary": {
        # SOURCE: Candela Obscura Core Rulebook, p.41
        "setting": "newfaire",
        "name": "Interdisciplinary",
        "description": (
            "Your circle has learned from one another's expertise. "
            "When choosing a new ability during character advancement, "
            "once per campaign, each character may choose an ability from "
            "a character role or specialty outside their own."
        ),
        "mechanical_effect": (
            "Once per campaign per character: choose one ability from any role "
            "or specialty other than your own during character advancement."
        ),
    },
    "resource_management": {
        # SOURCE: Candela Obscura Core Rulebook, p.41
        "setting": "newfaire",
        "name": "Resource Management",
        "description": (
            "Your circle has become efficient at conserving and recovering "
            "its shared reserves. When your circle hits a milestone on the "
            "Illumination Track, earn back 1 Stitch, Refresh, or Train resource."
        ),
        "mechanical_effect": (
            "When the circle hits a milestone on the Illumination Track: "
            "recover 1 Stitch, Refresh, or Train resource of your choice."
        ),
    },
    "one_last_run": {
        # SOURCE: Candela Obscura Core Rulebook, p.41
        "setting": "newfaire",
        "name": "One Last Run",
        "description": (
            "Your circle has decided this next assignment is your last. "
            "When you select this ability, the next assignment is your last. "
            "Everyone gets to take all four options during character advancement "
            "instead of only two."
        ),
        "mechanical_effect": (
            "Triggers campaign endgame: the next assignment is the circle's last. "
            "All characters take all four advancement options instead of two."
        ),
    },
}


# =========================================================================
# TRUST MECHANICS
# =========================================================================
# SOURCE: EXPANDED — consistent with social action mechanics (pp.9, 50)
# The book does not define formal named trust tiers with mechanical levels.
# These four tiers are original content designed to support NPC relationship
# tracking in campaign play.

TRUST_MECHANICS: Dict[str, Dict[str, Any]] = {
    "suspicious": {
        # SOURCE: EXPANDED
        "level": 0,
        "name": "Suspicious",
        "description": (
            "The NPC actively doubts the circle's motives or capabilities. "
            "They may withhold information, provide false leads, or report "
            "the circle's activities to interested parties."
        ),
        "effects": {
            "information": "NPC provides only publicly available information",
            "assistance": "NPC refuses direct requests for help",
            "interference": "NPC may actively work against the circle on a failed Sway roll",
            "upgrade_cost": "Two successful positive interactions to reach Cautious",
        },
    },
    "cautious": {
        # SOURCE: EXPANDED
        "level": 1,
        "name": "Cautious",
        "description": (
            "The NPC is watching and evaluating. They will provide minimal "
            "assistance but need proof of the circle's competence or good faith "
            "before committing further."
        ),
        "effects": {
            "information": "NPC shares one relevant fact per interaction",
            "assistance": "NPC assists with low-risk requests only",
            "interference": "NPC stays neutral unless directly threatened",
            "upgrade_cost": "One successful meaningful interaction to reach Trusting",
        },
    },
    "trusting": {
        # SOURCE: EXPANDED
        "level": 2,
        "name": "Trusting",
        "description": (
            "The NPC believes in the circle's intentions and is willing "
            "to take risks on their behalf. They share more sensitive "
            "information and can be called upon for active support."
        ),
        "effects": {
            "information": "NPC shares sensitive information related to their expertise",
            "assistance": "NPC assists with moderate-risk requests",
            "interference": "NPC defends circle's reputation if challenged",
            "upgrade_cost": "One high-stakes successful collaboration to reach Bonded",
        },
    },
    "bonded": {
        # SOURCE: EXPANDED
        "level": 3,
        "name": "Bonded",
        "description": (
            "The NPC considers the circle family or cause-partners. "
            "They will take serious personal risks on the circle's behalf "
            "and share everything they know about their domain."
        ),
        "effects": {
            "information": "NPC shares all known information, including dangerous secrets",
            "assistance": "NPC assists with high-risk requests without hesitation",
            "interference": "NPC will actively intervene if the circle is in danger",
            "special": "Bonded NPCs can join an investigation scene as a supporting figure",
        },
    },
}


# =========================================================================
# NPC RELATIONSHIPS
# =========================================================================
# SOURCE: EXPANDED — original content set in the Fairelands / Newfaire.
# Named example NPCs in the book are example PCs (Ezra Ashford, Morgan Ansari,
# Isadora Álvarez, Lim Dae, Swift — pp.19, 29-31) rather than NPC contacts.
# The book does not provide a pre-built NPC contact list.
# All 12 NPCs below are original content consistent with Candela Obscura's
# setting: the city of Newfaire, its districts, and its organizations.

NPC_RELATIONSHIPS: List[Dict[str, Any]] = [
    {
        # SOURCE: EXPANDED
        "name": "Magistra Elara Voss",
        "role": "Senior Archivist, Imperial Records Hall",
        "initial_trust": "cautious",
        "secret": (
            "She has been suppressing records of previous phenomena for twenty years "
            "on orders from a superior who is no longer in contact. "
            "She does not know why."
        ),
        "connection_to_phenomena": (
            "Her archive contains the only surviving records of the Pale Door's "
            "earlier manifestations in this city. She has read them. She was affected."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Cpl. Benedikt Haase",
        "role": "Night Watch Commander, Harbor District",
        "initial_trust": "suspicious",
        "secret": (
            "He lost his partner to a phenomenon three months ago and filed it "
            "as a drowning. He is terrified, grieving, and angry — "
            "and he blames investigators like the circle for not preventing it."
        ),
        "connection_to_phenomena": (
            "He patrols the area where the Moth Swarm first appeared. "
            "He has seen things he cannot explain. He keeps detailed unofficial notes."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Dr. Mireille Chantry",
        "role": "Physician, Foundling Hospital",
        "initial_trust": "trusting",
        "secret": (
            "She is herself a former Candela investigator, retired after a "
            "catastrophic case fifteen years ago. She uses her hospital as "
            "a discreet recovery space for affected individuals."
        ),
        "connection_to_phenomena": (
            "She has treated victims of the Crimson Weave and keeps tissue "
            "samples in a sealed cold cabinet. She will share them if asked directly."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Sable",
        "role": "Fence and Information Broker, Undercity",
        "initial_trust": "cautious",
        "secret": (
            "Sable is a recovered victim of the Glass Garden. The crystallization "
            "never fully reversed — one hand remains partially translucent. "
            "She covers it always."
        ),
        "connection_to_phenomena": (
            "She moves alchemical materials for the city's underground and "
            "knows who is buying the components for the Crimson Weave. "
            "She will not say unless the circle earns her trust."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Professor Aldric Mourn",
        "role": "Chair of Natural Philosophy, Ashford University",
        "initial_trust": "trusting",
        "secret": (
            "His published theories on dimensional folding are based on "
            "firsthand experience he has denied in public. He entered the "
            "Pale Door and came back. He remembers everything."
        ),
        "connection_to_phenomena": (
            "He is the city's foremost theoretical expert on dimensional phenomena "
            "and will share his knowledge freely — but his firsthand account "
            "is the real prize."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Sister Ines Collard",
        "role": "Church Warden, Basilica of the First Flame",
        "initial_trust": "cautious",
        "secret": (
            "The Basilica is built over an acoustic anomaly that amplifies "
            "supernatural phenomena. Sister Ines knows this and uses it "
            "for her own spiritual practice. She is not malicious — she is devout "
            "and wrong about what she is actually contacting."
        ),
        "connection_to_phenomena": (
            "The Bone Singer manifested inside the Basilica twice. Both times "
            "she interpreted it as a divine visitation. Her records are "
            "extraordinarily detailed."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Gregor Lenz",
        "role": "Retired Alchemist, Lenz & Sons Apothecary",
        "initial_trust": "trusting",
        "secret": (
            "He formulated the original alchemical compound that became the "
            "Crimson Weave in a student experiment forty years ago. "
            "He thought it was destroyed. He was wrong."
        ),
        "connection_to_phenomena": (
            "He knows the exact counter-reagent for the Crimson Weave and the "
            "Glass Garden. He will provide it if the circle explains the "
            "situation without telling him it was his formula."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Theodora Vane",
        "role": "Society Hostess and Philanthropist",
        "initial_trust": "suspicious",
        "secret": (
            "She is the primary financial backer of a group attempting to "
            "deliberately cultivate and control phenomena for commercial ends. "
            "She does not believe they are dangerous."
        ),
        "connection_to_phenomena": (
            "Her salon is a gathering point for occult enthusiasts. Three of "
            "the Thought Plague's primary early vectors attended her parties. "
            "She has not yet been infected, but she is close."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Nils Acker",
        "role": "City Cartographer, Survey Office",
        "initial_trust": "trusting",
        "secret": (
            "He has been mapping the spread patterns of phenomena for a decade "
            "without understanding what he was mapping. His maps show something "
            "alarming: the phenomena are converging on a single point."
        ),
        "connection_to_phenomena": (
            "His archives contain the most comprehensive spatial data on "
            "phenomena locations in the city's history. He will share it "
            "enthusiastically — he has been desperate for someone to explain the patterns."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "The Caretaker",
        "role": "Unknown — appears near Pale Door scar locations",
        "initial_trust": "suspicious",
        "secret": (
            "The Caretaker is not human and has not been for some time. "
            "They entered the Pale Door before the circle was founded. "
            "They return periodically but are unwilling or unable to explain why."
        ),
        "connection_to_phenomena": (
            "The Caretaker knows more about the Pale Door than any living person. "
            "They will share nothing until they have observed the circle across "
            "at least two investigations and judged them worthy."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Constance Frey",
        "role": "Journalist, The Evening Standard",
        "initial_trust": "cautious",
        "secret": (
            "She is the author of the most widely-circulated account of the "
            "Thought Plague — and she is infected. She believes she is cured. "
            "She is not."
        ),
        "connection_to_phenomena": (
            "Her published articles have spread awareness of the Thought Plague "
            "city-wide. She is simultaneously a valuable information source and "
            "an active vector. The circle must decide how to handle this."
        ),
    },
    {
        # SOURCE: EXPANDED
        "name": "Warden Kaske",
        "role": "Head of the City Morgue",
        "initial_trust": "trusting",
        "secret": (
            "Several of the bodies in his care are not entirely dead — "
            "they register faint vital signs. He has been filing them as "
            "dead to prevent panic. He is deeply frightened."
        ),
        "connection_to_phenomena": (
            "His morgue contains victims of at least four distinct phenomena. "
            "He keeps meticulous intake records and will allow examination of "
            "remains if the circle presents any official-looking credentials."
        ),
    },
]


__all__ = ["CIRCLE_ABILITIES", "TRUST_MECHANICS", "NPC_RELATIONSHIPS"]

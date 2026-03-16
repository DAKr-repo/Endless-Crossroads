"""
codex.forge.reference_data.stc_heritages
==========================================
Rosharan heritage (ethnicity/culture) reference data for the Cosmere RPG.

SOURCE AUTHORITY:
  Primary: STC_Stormlight_Starter_Rules_digital.pdf (Cosmere RPG v1.01, 2025)
  Full rules: STC_Stormlight_Handbook_digital.pdf (character creation ch.2-3)

SOURCED vs EXPANDED notation:
  # SOURCE: — directly confirmed from a PDF page
  # EXPANDED: — not in Starter Rules; derived from novels or invented for this
               codebase. Verify against full Handbook before treating as canonical.

CONFIRMED from Starter Rules:
  - Six attributes are: Strength, Speed, Intellect, Willpower, Awareness, Presence
    SOURCE: Starter Rules p.13
  - Heritages are called "Ancestry" on the character sheet (Abena's sheet shows
    "Human" ancestry). SOURCE: Starter Rules p.12
  - The full Handbook chapter on character creation lists heritage-specific bonuses.
    Those details are NOT in the Starter Rules PDF (60 pages), which uses pregenerated
    characters only. All stat_bonuses below are EXPANDED unless noted otherwise.

HERITAGES vs ANCESTRIES:
  The game officially calls these "Ancestry" (SOURCE: Starter Rules p.12 char sheet).
  We use "heritage" as an engine-level synonym for cultural background.

NOTE on "focus" bonus:
  Focus is a derived resource (max focus = 2 + Willpower; SOURCE: Starter Rules p.16).
  Heritage bonuses to "focus" in this file represent our engine-level abstraction
  for heritages that narratively enhance mental/spiritual resilience (Iriali, Natan).
  This may not match the full Handbook's implementation — verify when available.

Each heritage provides:
  - stat_bonuses: Dict of attribute adjustments
  - cultural_traits: List of cultural ability names
  - description: Narrative flavor text
  - starting_languages: Languages commonly spoken
"""

from typing import Any, Dict, List


HERITAGES: Dict[str, Dict[str, Any]] = {

    "Alethi": {
        "setting": "roshar",
        "description": (
            "The dominant culture of eastern Roshar. Alethi society is rigidly divided "
            "by the light/dark eye caste system, with a deeply martial culture shaped "
            "by endless war on the Shattered Plains. Lighteyes command; darkeyes serve. "
            "Scholarship is the province of women; warfare of men. Both gender traditions "
            "produce exceptional practitioners."
            # SOURCE: Stormlight Archive novels; cultural details confirmed in GM Tools
            # NPC profiles (Ellar, Bordin, Taln etc. are described as Alethi).
        ),
        "stat_bonuses": {"strength": 1},
        # EXPANDED: Strength +1 for Alethi is a design choice befitting their martial culture.
        # Full Handbook heritage bonuses needed to confirm exact value.
        "cultural_traits": [
            "Warrior's Discipline: Advantage on Athletics tests to resist being disarmed or grappled.",
            # EXPANDED: mechanics invented for engine; Athletics confirmed as a physical skill
            # SOURCE: Starter Rules p.19
            "Glyph Literacy: Can read and write Alethi glyphs (warrior script) without training.",
            # SOURCE: Stormlight Archive novels confirm glyph literacy is gendered/caste-based
            "Caste Awareness: Intuitively read social rank from dress, eye color, and behavior.",
            # EXPANDED: reflects the caste system described in the novels
        ],
        "starting_languages": ["Alethi", "Trade Tongue"],
        # SOURCE: GM Tools NPC profiles — Alethi characters list "Languages: Alethi" or similar
    },

    "Veden": {
        "setting": "roshar",
        "description": (
            "Vedens are a scholarly people from Jah Keved, a nation to the west known "
            "for fine wines, philosophical debate, and a tradition of dueling. Veden "
            "society values both the sword and the mind. They tend toward lighter skin "
            "and a wide range of eye colors. Their dueling tradition produces exceptional "
            "swordsmen, and their scholars are respected across Roshar."
            # SOURCE: Stormlight Archive novels
        ),
        "stat_bonuses": {"intellect": 1},
        # EXPANDED: Intellect +1 for Veden reflects their scholarly/dueling culture.
        "cultural_traits": [
            "Dueling Stance: Once per encounter, gain advantage on an attack roll against "
            "a single opponent you have declared a duel with.",
            # EXPANDED
            "Scholar's Mind: Advantage on Lore tests related to history, philosophy, and politics.",
            # EXPANDED: Lore confirmed as a cognitive skill SOURCE: Starter Rules p.20
            "Wine Expertise: Can identify the vintage, region, and quality of any wine; "
            "provides social advantage in Veden settings.",
            # EXPANDED
        ],
        "starting_languages": ["Veden", "Alethi", "Trade Tongue"],
        # EXPANDED: language list based on lore
    },

    "Thaylen": {
        "setting": "roshar",
        "description": (
            "Thaylens are a seafaring and mercantile people, identifiable by their long "
            "white eyebrows that can be tucked behind the ears. They dominate ocean trade "
            "across Roshar and are known for their reliability in deals. Their merchants "
            "travel everywhere, and their navy is formidable. A Thaylen merchant's word "
            "is considered binding without any written contract."
            # SOURCE: Stormlight Archive novels; Ryvlk described as Thaylen in GM Tools p.12
        ),
        "stat_bonuses": {"speed": 1},
        # EXPANDED: Speed +1 for Thaylen reflects their nimble seafaring nature.
        "cultural_traits": [
            "Merchant's Eye: Accurately appraise the value of goods and detect deceptive "
            "pricing or false weights with a Deduction test (DC 10).",
            # EXPANDED: Deduction confirmed as a cognitive skill SOURCE: Starter Rules p.20
            "Sailor's Balance: Advantage on Agility tests on unstable surfaces such "
            "as ships, bridge-wagons, or moving platforms.",
            # EXPANDED: Agility confirmed as a physical skill SOURCE: Starter Rules p.19
            "Trade Network: Once per session, call in a favor from a Thaylen trade contact "
            "to acquire a mundane item or piece of information.",
            # EXPANDED
        ],
        "starting_languages": ["Thaylen", "Trade Tongue", "Alethi"],
        # EXPANDED
    },

    "Azish": {
        "setting": "roshar",
        "description": (
            "The Azish Empire is the largest political entity on Roshar by territory, "
            "governed by an elaborate bureaucracy that values written law, proper process, "
            "and documented authority above all else. Azish people tend toward darker "
            "complexions. Their culture produces exceptional administrators, lawyers, and "
            "scholars. Azish Prime Aqasix is elected from among the greatest bureaucrats."
            # SOURCE: Stormlight Archive novels
        ),
        "stat_bonuses": {"intellect": 1},
        # EXPANDED: Intellect +1 for Azish reflects their bureaucratic, scholarly culture.
        "cultural_traits": [
            "Bureaucratic Mastery: Advantage on checks to navigate legal systems, obtain "
            "official permits, or exploit loopholes in written agreements.",
            # EXPANDED: uses Lore or Deduction skills contextually
            "Linguistic Breadth: Know one additional language of your choice at character creation.",
            # EXPANDED
            "Documented Authority: When presenting a forged or genuine official document, "
            "others are more likely to comply (advantage on relevant Persuasion tests).",
            # EXPANDED: Persuasion confirmed as a spiritual skill SOURCE: Starter Rules p.21
        ],
        "starting_languages": ["Azish", "Trade Tongue", "One additional language"],
        # EXPANDED
    },

    "Herdazian": {
        "setting": "roshar",
        "description": (
            "Herdazians are a resilient and adaptable people from the western coast, "
            "neighbors and sometimes subjects of Alethkar. They are known for stone-like "
            "fingernails (a recessive Listener trait from ancient interbreeding), quick "
            "humor, practical resourcefulness, and unusual endurance. They are common in "
            "Alethi warcamps as soldiers and support personnel."
            # SOURCE: Stormlight Archive novels; stone fingernails confirmed as canonical trait
        ),
        "stat_bonuses": {"speed": 1},
        # EXPANDED: Speed +1 for Herdazian reflects their adaptability and nimbleness.
        "cultural_traits": [
            "Stone Nails: Your natural fingernails are partially mineralized. Unarmed "
            "strikes deal an additional 1 damage and can be used to climb stone surfaces "
            "without equipment.",
            # SOURCE: Stone fingernails are canonical from Stormlight Archive novels
            # EXPANDED: game mechanics for the trait
            "Resilient Constitution: Advantage on Athletics tests against poison and "
            "environmental hazards.",
            # EXPANDED: Athletics confirmed as physical skill SOURCE: Starter Rules p.19
            "Survivor's Instinct: Once per long rest, reduce damage from a single attack "
            "that would reduce you to 0 HP to 1 HP instead.",
            # EXPANDED
        ],
        "starting_languages": ["Herdazian", "Alethi"],
        # EXPANDED
    },

    "Shin": {
        "setting": "roshar",
        "description": (
            "The Shin are an isolated people from Shinovar, the one region of Roshar "
            "with true soil, vegetation, and animals similar to pre-Desolation Ashyn. "
            "They are considered strange by other Rosharans for their pacifism (until "
            "pushed), their reverence for stone, their discomfort outdoors in Highstorms, "
            "and their tradition of walking on stone being considered almost sacred. "
            "Shin soldiers are considered disgraced outcasts by their own people."
            # SOURCE: Stormlight Archive novels; Taszo-son-Clutio described as Shin in
            # GM Tools p.6 ('Roleplaying Taszo' profile)
        ),
        "stat_bonuses": {"intellect": 1},
        # EXPANDED: Intellect +1 for Shin reflects their introspective, scholarly nature.
        "cultural_traits": [
            "Pacifist's Precision: When forced to fight, gain advantage on the first "
            "attack roll of any combat (your reluctance makes your strike unexpected).",
            # EXPANDED
            "Stone Reverence: Can sense the age and origin of stone and stone structures "
            "by touch. Useful for identifying ancient Radiants' construction.",
            # SOURCE: Shin reverence for stone from Stormlight Archive novels
            # EXPANDED: game mechanics
            "Cognitive Clarity: Advantage on Discipline tests against mental manipulation, "
            "illusions, and emotional Investiture effects.",
            # EXPANDED: Discipline confirmed as cognitive skill SOURCE: Starter Rules p.20
        ],
        "starting_languages": ["Shin", "Trade Tongue"],
        # SOURCE: Taszo speaks Alethi and Shin per GM Tools p.3 stat block
    },

    "Makabaki": {
        "setting": "roshar",
        "description": (
            "The Makabaki people encompass a diverse collection of nations in central "
            "and southern Roshar, including Azir's neighbors and several independent "
            "kingdoms. While each nation has its own culture, common threads include "
            "darker skin tones, a tradition of oral history and storytelling, and a "
            "deep connection to regional spren. Makabaki scholars are renowned for "
            "their breadth of knowledge."
            # SOURCE: Stormlight Archive novels (Taln described as Makabaki in GM Tools p.6)
        ),
        "stat_bonuses": {"intellect": 1},
        # EXPANDED: Intellect +1 for Makabaki reflects their oral history/scholarship traditions.
        "cultural_traits": [
            "Cultural Memory: Advantage on Lore tests to recall historical events, oral "
            "traditions, or legends from any Rosharan culture.",
            # EXPANDED: Lore confirmed as cognitive skill SOURCE: Starter Rules p.20
            "Spren Affinity: When entering a new region, you instinctively sense the "
            "dominant regional spren within one hour of arrival.",
            # EXPANDED
            "Adaptive Learner: At each ideal advancement, gain one additional minor "
            "cultural expertise of your choice.",
            # EXPANDED: Expertises confirmed as a character system SOURCE: Starter Rules p.15
        ],
        "starting_languages": ["Trade Tongue", "One regional Makabaki dialect", "Azish"],
        # EXPANDED
    },

    "Iriali": {
        "setting": "roshar",
        "description": (
            "The Iriali are a nomadic people with golden hair and a cyclic view of "
            "existence called the Long Trail. They believe all Iriali souls are fragments "
            "of one divine being that split apart to experience the world, and will one "
            "day reunite. Their wandering culture has taken them across Roshar and "
            "reportedly to other worlds entirely. They have a mystical relationship "
            "with Investiture and are known as seekers of experience."
            # SOURCE: Stormlight Archive novels; Kaiana speaks Alethi and Reshi per GM Tools p.5
        ),
        "stat_bonuses": {"focus": 1},
        # EXPANDED: Focus +1 for Iriali represents their spiritual resilience.
        # NOTE: Focus is a derived stat (2 + Willpower) in this game.
        # SOURCE: Starter Rules p.16. The bonus here is engine-level abstraction.
        "cultural_traits": [
            "Long Trail Wanderer: You have an uncanny sense of direction and can never "
            "become truly lost. Advantage on Survival tests for navigation.",
            # EXPANDED: Survival confirmed as spiritual skill SOURCE: Starter Rules p.21
            "World Memory: Your culture's oral traditions span multiple worlds. Once per "
            "session, recall a relevant fact about Cosmere history or geography.",
            # EXPANDED: references Cosmere's multi-world nature from the novels
            "Investiture Sense: You can feel the presence of active Investiture within "
            "60 feet of you (fabrials, Radiant surgebinding, Voidlight).",
            # EXPANDED: reflects Iriali spiritual attunement from novels
        ],
        "starting_languages": ["Iriali", "Trade Tongue", "Alethi"],
        # SOURCE: Kaiana speaks Alethi and Reshi (Reshi is regional near Iriali territory)
        # per GM Tools p.5 stat block
    },

    "Unkalaki": {
        "setting": "roshar",
        "description": (
            "The Unkalaki, known to Alethi as Horneaters, are a people of the mountains "
            "between Alethkar and Shinovar. They are large, powerful, and can see spren "
            "that others cannot — a trait linked to their heritage. They eat the shells "
            "of Rosharan crustaceans that others discard. Their shamans and warriors are "
            "both formidable. Rock is the most famous modern Unkalaki, serving as "
            "Kaladin's bridgeman cook."
            # SOURCE: Stormlight Archive novels; spren-seeing ability canonical
        ),
        "stat_bonuses": {"strength": 1},
        # EXPANDED: Strength +1 for Unkalaki reflects their large, powerful physiques.
        "cultural_traits": [
            "Spren Sight: You can see all varieties of spren naturally, including those "
            "normally invisible to humans without special ability.",
            # SOURCE: Unkalaki spren-sight is canonical from Stormlight Archive novels
            "Shell Eater: You can safely consume chitin, crem, and other materials "
            "inedible to standard humans. You are immune to most common poisons "
            "derived from Rosharan shellfish.",
            # SOURCE: Horneater diet from Stormlight Archive novels
            "Mountain Heritage: Advantage on Athletics tests for climbing and Survival "
            "tests against cold and altitude sickness.",
            # EXPANDED: Athletics and Survival confirmed as skills
            # SOURCE: Starter Rules p.19, p.21
        ],
        "starting_languages": ["Unkalaki", "Alethi"],
        # EXPANDED
    },

    "Natan": {
        "setting": "roshar",
        "description": (
            "The Natans are a pale-blue-skinned people from the Reshi Isles and Natanatan "
            "region. They are among the rarest heritages on Roshar, descended from an "
            "ancient bloodline that predates the Desolations. Their unusual appearance "
            "draws attention everywhere. Scholars believe their distinctive coloration "
            "reflects a connection to Honor's original Investiture. They often possess "
            "unusual sensitivity to spiritual phenomena."
            # SOURCE: Stormlight Archive novels (blue-skinned people mentioned)
            # EXPANDED: specific lore connections to Honor's Investiture
        ),
        "stat_bonuses": {"focus": 1},
        # EXPANDED: Focus +1 for Natan represents their spiritual sensitivity.
        # Same caveat as Iriali — focus is a derived stat in this game.
        "cultural_traits": [
            "Ancient Bloodline: Your heritage carries faint echoes of pre-Desolation "
            "power. You have advantage on Discipline tests to resist Voidlight corruption "
            "and Unmade influence.",
            # EXPANDED: Discipline confirmed as cognitive skill SOURCE: Starter Rules p.20
            "Spiritual Resonance: You can sense the spiritual health of bonds — "
            "Nahel bonds, oaths, and promises feel tangible to you. Know if an "
            "oath has been broken within 1 hour of the breaking.",
            # EXPANDED
            "Distinctive Presence: Your blue skin makes you memorable everywhere. "
            "Disadvantage on Stealth in normal crowds; advantage when you want to "
            "be noticed and remembered.",
            # EXPANDED: Stealth confirmed as physical skill SOURCE: Starter Rules p.21
        ],
        "starting_languages": ["Natan", "Trade Tongue", "Alethi"],
        # EXPANDED
    },
}


__all__ = ["HERITAGES"]

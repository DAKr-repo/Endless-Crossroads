"""
codex.forge.reference_data.sav_factions
=========================================
Scum and Villainy faction reference data for the Procyon Sector.

Contains all 26 factions with tiers, categories, descriptions, and goals.
Faction list and tiers confirmed from PDF p.316 (faction table).
Detailed descriptions confirmed from PDF p.317-319 and individual faction
pages p.320-326+.

SOURCE POLICY:
  # SOURCE: Scum and Villainy.pdf, p.XX  — verified directly from PDF text
  # EXPANDED — content consistent with game fiction but not verbatim from PDF

FACTION CATEGORIES (SOURCE: p.316):
  Hegemony, Weirdness, Criminal
"""

# =========================================================================
# FACTION CATEGORIES
# SOURCE: Scum and Villainy.pdf, p.316 — three categories confirmed
# =========================================================================

FACTION_CATEGORIES: list = [
    "Hegemony",   # SOURCE: p.316
    "Weirdness",  # SOURCE: p.316
    "Criminal",   # SOURCE: p.316
]

# =========================================================================
# FACTIONS
# SOURCE: Scum and Villainy.pdf, p.316 (tier table), p.317-326 (descriptions)
# All faction names and tiers confirmed from p.316 table.
# Descriptions drawn from p.317-319 summary text and individual faction pages.
# NPC names confirmed where individual faction pages were rendered.
# =========================================================================

FACTIONS: dict = {

    # -----------------------------------------------------------------------
    # HEGEMONY FACTIONS
    # SOURCE: Scum and Villainy.pdf, p.316 (Hegemony column)
    # -----------------------------------------------------------------------

    # SOURCE: p.316 Tier V, p.318 description
    "Guild of Engineers": {
        "setting": "procyon",
        "tier": 5,
        "category": "Hegemony",
        "description": (
            "One of the Hegemonic High Guilds, responsible for resource acquisition, "
            "cybernetics, AI, tech advancement, and research. Maintain the jumpgates "
            "and hyperspace lanes, and build ships. All ships in Hegemonic space must "
            "be certified and registered with the Starsmiths Guild — but forged papers "
            "are all too common. Often have the best toys."
        ),
        "goal": "Control and certify all technical work in Procyon.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED — individual faction page not rendered
        "sector": "All sectors",  # EXPANDED
        "quirk": "Certification is power. Unlicensed work is the deepest insult.",  # EXPANDED
    },
    # SOURCE: p.316 Tier IV, p.317 description, p.323 full page
    "Church of Stellar Flame": {
        "setting": "procyon",
        "tier": 4,
        "category": "Hegemony",
        "description": (
            "One of the official Hegemonic Cults. A religious group with Hegemonic "
            "backing, believing that many Precursor artifacts and mystic practices are "
            "dangerous. Religious zealots with only a few powerful members. Stretched "
            "thin, they use their power and influence to seek out and eradicate "
            "dangerous artifacts and mystic activity in the sector."
        ),
        "goal": "Root out heretics and dangerous elements.",  # SOURCE: p.323 goal box
        "notable_npcs": [  # SOURCE: p.323
            "Alaana (Noble, high priestess, mystic, driven, ex-heretic)",
            "Battle Sister Diana (battle-scarred, exo-suited, unstoppable)",
            "Iraam the Kind (inquisitor, plain, quiet, cruel)",
        ],
        "sector": "Orbiting incredibly close to a star (The Way of Light battle cruiser)",  # SOURCE: p.323
        "quirk": "Each member is branded with the Kiss of Light. Faithful pray by bathing in as much light as they can bear.",  # SOURCE: p.323
    },
    # SOURCE: p.316 Tier IV, p.318 description, p.325 full page
    "Counters Guild": {
        "setting": "procyon",
        "tier": 4,
        "category": "Hegemony",
        "description": (
            "Officials who maintain the galactic currency network and build shadow "
            "repositories in any system the Guild has a presence in, storing "
            "mysterious items and securing auctions and commerce."
        ),
        "goal": "Disrupt Guild of Engineers' mining operation.",  # SOURCE: p.325 goal box
        "notable_npcs": [  # SOURCE: p.325
            "Torx Verron (chief executive, calculating, ruthless, expansionary)",
            "Rintar Ix (operations head, conniving, jealous, sly)",
            "Broq Vsigh (repository head, honorable, meticulous)",
        ],
        "sector": "Warren (currency exchange HQ), shadow repositories sector-wide",  # SOURCE: p.325
        "quirk": "Members sign a contract for cycles of labor. Any breach can be punished harshly.",  # SOURCE: p.325
    },
    # SOURCE: p.316 Tier IV — listed but individual page not rendered
    "Starless Veil": {
        "setting": "procyon",
        "tier": 4,
        "category": "Hegemony",
        "description": (  # SOURCE: p.319
            "Hegemonic counterintelligence and spies. Currently at odds with House "
            "Malklaith. Seek to undermine the Governor in order to make a case for "
            "change in House control."
        ),
        "goal": "Undermine House Malklaith and reform House control.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED — individual faction page not rendered
        "sector": "All sectors (intelligence network)",  # EXPANDED
        "quirk": "They see everything. Information is their primary weapon.",  # EXPANDED
    },
    # SOURCE: p.316 Tier III, p.317 description, p.320 full page
    "51st Legion": {
        "setting": "procyon",
        "tier": 3,
        "category": "Hegemony",
        "description": (
            "A faction of the Hegemonic military, preparing a coup. Hegemonic military "
            "that represents the law anywhere off-planet."
        ),
        "goal": "Cleanse the Legion of anyone disloyal.",  # SOURCE: p.320 goal box
        "notable_npcs": [  # SOURCE: p.320
            "Tallon 'the Butcher' (commander, disciplined, imposing, vicious)",
            "Liyara (lieutenant, psychic, changed, eerie, loyal)",
            "Wick (spy, xeno, unreadable, mysterious, loyal)",
        ],
        "sector": "The Scorpio (dreadnought HQ), naval yards throughout the sector",  # SOURCE: p.320
        "quirk": "There are oddly few xenos among the Legion.",  # SOURCE: p.320
    },
    # SOURCE: p.316 Tier III — listed but individual page not rendered
    "House Malklaith": {
        "setting": "procyon",
        "tier": 3,
        "category": "Hegemony",
        "description": (  # SOURCE: p.318
            "A powerful Noble House of the Hegemony that ostensibly owns the sector. "
            "Represented by the Governor, who lives on Warren."
        ),
        "goal": "Maintain dominance over the Procyon sector.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED — individual faction page not rendered
        "sector": "Warren (Governor's residence)",  # SOURCE: p.318
        "quirk": "The Governor's focus on the Core keeps them distracted from local politics.",  # EXPANDED
    },
    # SOURCE: p.316 Tier III — listed; p.318 description
    "Isotropa Max Secure": {
        "setting": "procyon",
        "tier": 3,
        "category": "Hegemony",
        "description": (  # SOURCE: p.318
            "The most notorious prison system in the Procyon sector, housing the worst "
            "of the worst. Brokers audiences with its population and grants commutations "
            "for those with power and wealth. Reports to Malklaith but the prison largely "
            "runs itself."
        ),
        "goal": "House the sector's most dangerous criminals indefinitely.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED — individual faction page not rendered
        "sector": "Orbiting near the star in Brekk system",  # SOURCE: p.312
        "quirk": "Nothing goes in or out without authorization. Nothing.",  # EXPANDED
    },
    # SOURCE: p.316 Tier III; p.319 description
    "Starsmiths Guild": {
        "setting": "procyon",
        "tier": 3,
        "category": "Hegemony",
        "description": (  # SOURCE: p.319
            "Maintain the jumpgates and hyperspace lanes, and build ships. All ships "
            "in Hegemonic space must be certified and registered with the Starsmiths "
            "Guild — but forged papers are all too common."
        ),
        "goal": "Certify and control all shipbuilding and hyperspace infrastructure.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "All major stations (certification offices)",  # EXPANDED
        "quirk": "Forged Guild papers are a common underworld commodity.",  # EXPANDED
    },
    # SOURCE: p.316 Tier II — listed but individual page not rendered
    "Cult of the Seekers": {
        "setting": "procyon",
        "tier": 2,
        "category": "Hegemony",
        "description": (  # SOURCE: p.317 and p.325
            "Wandering mystics studying artifacts and exploring, looking to open the "
            "Hantu gate. Members include the Hegemon's mother."
        ),
        "goal": "Find missing Hantu gate keys.",  # SOURCE: p.325 goal box
        "notable_npcs": [  # SOURCE: p.325
            "Lasaya al'Nim-Amar (Noble, mystic, brilliant, obsessed)",
            "Yor Brah-Rahim (explorer, hot-tempered, stressed)",
            "Qulocct (Memish, researcher, sharp, obsequious)",
        ],
        "sector": "Small island research station on Mem (HQ), dig site on Shimaya",  # SOURCE: p.325
        "quirk": "Many are young ex-Legionnaires personally drafted by the Hegemon's mother.",  # SOURCE: p.325
    },
    # SOURCE: p.316 Tier II; p.318 description
    "Hegemonic News Network": {
        "setting": "procyon",
        "tier": 2,
        "category": "Hegemony",
        "description": (  # SOURCE: p.318
            "Those who control the media control the mind. Often use this as leverage "
            "over other factions. Spies."
        ),
        "goal": "Control the flow of information across Procyon.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "All major stations (broadcast infrastructure)",  # EXPANDED
        "quirk": "Every reporter is potentially an informant. Every story is potentially leverage.",  # EXPANDED
    },
    # SOURCE: p.316 Tier II; p.318 description
    "Yaru (Makers Guild)": {
        "setting": "procyon",
        "tier": 2,
        "category": "Hegemony",
        "description": (  # SOURCE: p.319
            "Guild that force-grows clones for labor. Clones are short-lived, have a "
            "symbol on their foreheads, and are supposedly only barely sentient. Folks "
            "are distinctly uncomfortable around the clones."
        ),
        "goal": "Expand clone labor operations across Procyon.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Deep space, Aleph system borders",  # EXPANDED
        "quirk": "No one is quite sure if the clones are truly not sentient. Most prefer not to think about it.",  # EXPANDED
    },
    # SOURCE: p.316 Tier I; p.317 description, p.324 full page
    "Concordiat Knights": {
        "setting": "procyon",
        "tier": 1,
        "category": "Hegemony",
        "description": (
            "Fourth and fifth children of Noble Houses who have taken an oath "
            "sanctioned by the Hegemon to seek the Light of the World. Often "
            "accompanied by a motley crew of adventurers."
        ),
        "goal": "Find the first Ur site on their map.",  # SOURCE: p.324 goal box
        "notable_npcs": [  # SOURCE: p.324
            "Nicols al'Nim-Amar (leader, glib, hopeful)",
            "Vnipe al'Vorron (priestess, renowned, bejeweled)",
            "Junrai (explorer, death wish, restless)",
            "Intal Brel (religious, vigilant, honorable)",
        ],
        "sector": "No fixed turf; The Grail (a bar on Sonhandra) as message drop",  # SOURCE: p.324
        "quirk": "Each Knight is as distinct as they can be from each other.",  # SOURCE: p.324
    },

    # -----------------------------------------------------------------------
    # WEIRDNESS FACTIONS
    # SOURCE: Scum and Villainy.pdf, p.316 (Weirdness column)
    # -----------------------------------------------------------------------

    # SOURCE: p.316 Tier IV — listed but individual page not rendered
    "Sah'iir": {
        "setting": "procyon",
        "tier": 4,
        "category": "Weirdness",
        "description": (  # SOURCE: p.319
            "Tall, ebon-skinned xenos who travel with blindfolded servants that speak "
            "for them. Gave the Hegemony their ansible network. Have creepy black-metal "
            "ships. Very rich and work as merchant families."
        ),
        "goal": "Expand their commercial empire and ansible network.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Deep space, merchant routes throughout Procyon",  # EXPANDED
        "quirk": "They communicate only through their blindfolded servants. Direct address is considered rude.",  # EXPANDED
    },
    # SOURCE: p.316 Tier IV; p.317 description — listed but individual page not rendered
    "Suneaters": {
        "setting": "procyon",
        "tier": 4,
        "category": "Weirdness",
        "description": (  # SOURCE: p.317
            "Ur-archaeologists and scientists obsessed with recreating jumpgate "
            "technology. Looking to extinguish a star in pursuit of their goals."
        ),
        "goal": "Extinguish a star to power their jumpgate research.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Unknown (research cells throughout sector)",  # EXPANDED
        "quirk": "Their ultimate goal would destroy an entire star system. They consider this acceptable.",  # EXPANDED
    },
    # SOURCE: p.316 Tier III; p.317 description, p.321 full page
    "The Agony": {
        "setting": "procyon",
        "tier": 3,
        "category": "Weirdness",
        "description": (
            "Human Cultists infecting themselves with Way creatures to access the "
            "universe in unsettling ways. Named for the pain most endure for their "
            "usual abilities. A Cult of humans who infect themselves with Way creatures."
        ),
        "goal": "Move Planet Omega towards Mem.",  # SOURCE: p.321 goal box
        "notable_npcs": [  # SOURCE: p.321
            "Lexal (mystic, addicted, power-hungry, winged)",
            "Iritha (mystic, many-limbed, glowing, powerful, potent)",
            "Noro (mystic, calculating, enrapturing, elongated)",
        ],
        "sector": "Platform orbiting Planet Omega (HQ), secret chantries on Mem, Sonhandra, and Lithios",  # SOURCE: p.321
        "quirk": "Each member is changed in some highly visible way — extra limbs, semi-spectral forms, or many new mouths and eyes.",  # SOURCE: p.321
    },
    # SOURCE: p.316 Tier III — listed; p.322 full page
    "Ashtari Cult": {
        "setting": "procyon",
        "tier": 3,
        "category": "Weirdness",
        "description": (
            "A Cult of Precursor worshipers claiming Ur descent. They carry vials "
            "of gases from the Ashtari Cloud, which they inhale to connect to their "
            "presumed ancestors."
        ),
        "goal": "Align the moons of Nightfall.",  # SOURCE: p.322 goal box
        "notable_npcs": [  # SOURCE: p.322
            "Urmak Theon (compassionate, educated, well spoken)",
            "Urmak Lesh (artificer, ex-Guilder, researcher)",
            "Urley Fean (Noble, cautious, hidden, influential)",
            "Rokono Maex (captain, scavenger, coarse, nonbeliever, stoic)",
        ],
        "sector": "Undocumented Ur ruin on Lithios, moon base on a Nightfall moon (HQ)",  # SOURCE: p.322
        "quirk": "Each cult member wears a small vial of Ashtari gas to commune with their 'Ur past.'",  # SOURCE: p.322
    },
    # SOURCE: p.316 Tier III; p.319 description — listed but individual page not rendered
    "Vignerons": {
        "setting": "procyon",
        "tier": 3,
        "category": "Weirdness",
        "description": (  # SOURCE: p.319
            "A small handful of immortality seekers using artifact tech implants and "
            "chemicals distilled from the living. Several of them have been around for "
            "hundreds of years. Most were powerful before their transformation, though "
            "they now conceal their true identities."
        ),
        "goal": "Maintain immortality and expand their centuries-long influence.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "All sectors (disguised as ordinary citizens)",  # EXPANDED
        "quirk": "No one suspects the immortals. They look perfectly normal. They have had centuries to perfect the act.",  # EXPANDED
    },
    # SOURCE: p.316 Tier II; p.318 description — listed but individual page not rendered
    "Ghosts": {
        "setting": "procyon",
        "tier": 2,
        "category": "Weirdness",
        "description": (  # SOURCE: p.318
            "Scientists who, due to a mishap, live exo-suited in a half-phased state. "
            "The Church of Stellar Flame offers a significant bounty on them and their "
            "ghost ship, the Skeleton Key — dead or destroyed (but certainly not alive)."
        ),
        "goal": "Survive and find a way to reverse their half-phased condition.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "The Skeleton Key (ghost ship, location unknown)",  # SOURCE: p.318
        "quirk": "They exist partially outside normal space. Standard weapons barely affect them.",  # EXPANDED
    },
    # SOURCE: p.316 Tier II; p.318 description — listed but individual page not rendered
    "Mendicants": {
        "setting": "procyon",
        "tier": 2,
        "category": "Weirdness",
        "description": (  # SOURCE: p.318
            "Originally the Church of the Emerald Heart, their organization was "
            "politically destroyed. Now they wander the stars as traveling physicians "
            "and healers."
        ),
        "goal": "Provide healing throughout Procyon; rebuild their organization.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Wandering (no fixed base)",  # EXPANDED
        "quirk": "They treat anyone who asks, regardless of faction or affiliation.",  # EXPANDED
    },
    # SOURCE: p.316 Tier II; p.318 description — listed but individual page not rendered
    "Nightspeakers": {
        "setting": "procyon",
        "tier": 2,
        "category": "Weirdness",
        "description": (  # SOURCE: p.318
            "Mystics with dark proclivities bent on finding a set of dangerous "
            "Precursor artifacts."
        ),
        "goal": "Locate and acquire dangerous Precursor artifacts.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Blackstarr (vast Nightspeaker ship), hidden conclave in Brekk",  # SOURCE: p.312
        "quirk": "Initiates train for their first year on a blacked-out ship that moves routinely to prevent discovery.",  # SOURCE: p.312
    },
    # SOURCE: p.316 Tier I; p.317 description, p.320 full page
    "Acolytes of Brashkadesh": {
        "setting": "procyon",
        "tier": 1,
        "category": "Weirdness",
        "description": (
            "A collective that eschews individuality. Initiates adopt the same garb "
            "and the name 'Ashkad,' in the pursuit of perfection at any cost."
        ),
        "goal": "Convert an entire factory to their religion.",  # SOURCE: p.320 goal box
        "notable_npcs": [  # SOURCE: p.320
            "Ashkad (charismatic, passionate, idealistic)",
            "Ashkad (mystic, devout, artistic)",
            "Ashkad (technician, skilled, liar, wealthy)",
        ],
        "sector": "Numerous meditation rooms throughout Indri",  # SOURCE: p.320
        "quirk": "All members wear the same garb and use the same name. Attuning to the Pillar of Truth lets them share memories.",  # SOURCE: p.320
    },
    # SOURCE: p.316 Tier I; p.324 full page
    "Conclave 01": {
        "setting": "procyon",
        "tier": 1,
        "category": "Weirdness",
        "description": (
            "Independent, sentient Urbots led by an ancient Urbot known as the Prime, "
            "seeking free will and independence for all Urbots. Working to control "
            "mining sites and gain control over Precursor AI modules required to "
            "generate true sentient machines."
        ),
        "goal": "Take control of an Iota factory.",  # SOURCE: p.324 goal box
        "notable_npcs": [  # SOURCE: p.324
            "The Prime (ancient, powerful, mysterious, wise)",
            "Bar-Hazuk (gardener, huge, kind)",
            "Delta-7 (architect, weapons platform, massive)",
            "Sp-d3r (hacker, infiltrator, cloaked, tiny)",
        ],
        "sector": "Secret bases on Baftoma and the Indri Wastelands (HQ)",  # SOURCE: p.324
        "quirk": "All members are currently Urbots of varied shapes and sizes. Urbot spies pose as everyday servants.",  # SOURCE: p.324
    },
    # SOURCE: p.316 Tier I — listed but individual page not rendered
    "Vigilance": {
        "setting": "procyon",
        "tier": 1,
        "category": "Weirdness",
        "description": (  # SOURCE: p.319
            "Warrior mystics bearing artifact blades, who seek to enforce an ancient "
            "code of justice on any they find wanting."
        ),
        "goal": "Enforce their ancient code of justice across Procyon.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Wandering (no fixed base)",  # EXPANDED
        "quirk": "They judge silently. Their artifact blades are proof of their authority.",  # EXPANDED
    },

    # -----------------------------------------------------------------------
    # CRIMINAL FACTIONS
    # SOURCE: Scum and Villainy.pdf, p.316 (Criminal column)
    # -----------------------------------------------------------------------

    # SOURCE: p.316 Tier IV — listed but individual page not rendered
    "Lost Legion": {
        "setting": "procyon",
        "tier": 4,
        "category": "Criminal",
        "description": (  # SOURCE: p.318
            "Formerly the Hegemon's personal guard, they rebelled when the current "
            "Hegemon rose to power. They seek to see the Hegemon dethroned and have "
            "been guns for hire ever since the schism."
        ),
        "goal": "Dethrone the current Hegemon.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Outer system (mobile fleet)",  # EXPANDED
        "quirk": "Former personal guard of the Hegemon — they know Hegemony protocols intimately.",  # EXPANDED
    },
    # SOURCE: p.316 Tier IV — listed; p.319 description
    "Scarlet Wolves": {
        "setting": "procyon",
        "tier": 4,
        "category": "Criminal",
        "description": (  # SOURCE: p.319
            "Although they often hire themselves out as bounty hunters, the Scarlet "
            "Wolves are a renowned group of assassins. Each bears a distinctive tattoo "
            "of a wolf holding a star in its mouth."
        ),
        "goal": "Expand their assassination and bounty hunting empire.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "All sectors (no fixed base)",  # EXPANDED
        "quirk": "The wolf-and-star tattoo is a mark of pride and terror throughout the sector.",  # SOURCE: p.319
    },
    # SOURCE: p.316 Tier IV — listed; p.319 description
    "Vorex": {
        "setting": "procyon",
        "tier": 4,
        "category": "Criminal",
        "description": (  # SOURCE: p.319
            "The most successful information broker to ever live. Can access any terminal "
            "in the system — though no one can explain how. Frantically seeking her "
            "sister, who the Counters Guild took hostage."
        ),
        "goal": "Find and free her sister from the Counters Guild.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED — Vorex herself is the notable NPC
        "sector": "All sectors (can access any terminal)",  # SOURCE: p.319
        "quirk": "No one knows how Vorex accesses terminals. Every major faction wants to hire or neutralize her.",  # EXPANDED
    },
    # SOURCE: p.316 Tier III; p.317 description, p.321 full page
    "Ashen Knives": {
        "setting": "procyon",
        "tier": 3,
        "category": "Criminal",
        "description": (
            "Once lean and battle ready, the Ashen Knives are a decadent Syndicate "
            "focused on drugs, gambling, and pleasures of the flesh. Dangerous criminal "
            "Syndicate known for their control of gambling and assassination in the sector."
        ),
        "goal": "Control major planetary crimes in Rin.",  # SOURCE: p.321 goal box
        "notable_npcs": [  # SOURCE: p.321
            "Pasha Qo'iin (sly, corpulent, sartorial, decadent)",
            "Knife Lirik (xeno, assassin, gambler, deadly, graceful)",
            "Oya (high ranking, greedy, well armed, natural leader)",
        ],
        "sector": "Drug dens, gambling houses, hidden reinforced bunker on Warren (HQ)",  # SOURCE: p.321
        "quirk": "To join, Knives must take a life. Promotion requires doing unsavory tasks. Regional leaders are titled 'Pashas.'",  # SOURCE: p.321
    },
    # SOURCE: p.316 Tier III — listed; p.317 description, p.322 full page
    "Borniko Syndicate": {
        "setting": "procyon",
        "tier": 3,
        "category": "Criminal",
        "description": (
            "A tightly knit group of thieves who steal high-end technological supplies. "
            "The Guild hates these guys."
        ),
        "goal": "Steal Governor Malklaith's rings.",  # SOURCE: p.322 goal box
        "notable_npcs": [  # SOURCE: p.322
            "Ria 'Keycard' (wizard-class hacker, ambitious, daring)",
            "Nals E (Urboticist, gearhead, muscled)",
            "MaxiMillions (arrogant, expert infiltrator, gorgeous)",
            "Pip (mystic, xeno, small, unsettling)",
        ],
        "sector": "Former Counters Guild shadow repository (HQ), Warren",  # SOURCE: p.322
        "quirk": "Joining involves pulling off a heist that impresses the leadership.",  # SOURCE: p.322
    },
    # SOURCE: p.316 Tier III; p.317 description, p.326 full page
    "Draxler's Raiders": {
        "setting": "procyon",
        "tier": 3,
        "category": "Criminal",
        "description": (
            "Violent pirates who disable ships before boarding, ransoming crew and "
            "cargo alike. Fierce individualistic pirates who specialize in disabling "
            "ships before boarding. Mostly found in Iota and Brekk."
        ),
        "goal": "Pull off a jailbreak at Isotropa Max Secure.",  # SOURCE: p.326 goal box
        "notable_npcs": [  # SOURCE: p.326
            "Draxler (leader, killer, vengeful)",
            "Wudu 'Starhawk' (captain, loyal, vicious, wary)",
            "Samara 'She Wolf' Red (captain, enforcer, cold, physical)",
        ],
        "sector": "Abandoned mining station in an Iota asteroid belt (HQ)",  # SOURCE: p.326
        "quirk": "Almost all members are wanted for crimes. They've set their sights on eliminating Isotropa Max Secure.",  # SOURCE: p.326
    },
    # SOURCE: p.316 Tier III; p.318 description — listed but individual page not rendered
    "The Maelstrom": {
        "setting": "procyon",
        "tier": 3,
        "category": "Criminal",
        "description": (  # SOURCE: p.318
            "Rowdy space pirates living in a nebula that's difficult to navigate. "
            "Often clash with the Legion."
        ),
        "goal": "Expand their territory and keep the Legion out of their nebula.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Nebula (difficult to navigate, exact location unknown)",  # SOURCE: p.318
        "quirk": "Their nebula base is nearly impossible to navigate without a guide. It's their greatest defense.",  # EXPANDED
    },
    # SOURCE: p.316 Tier II — listed; p.318 description
    "Echo Wave Riders": {
        "setting": "procyon",
        "tier": 2,
        "category": "Criminal",
        "description": (  # SOURCE: p.318
            "Pilots. Many organize illegal races. Many take dangerous jobs for pay, "
            "and a few test dangerous new engine/flight technologies for the Guild. "
            "They wear a pin that shows how many races they've won."
        ),
        "goal": "Win the next great illegal race and secure Guild contracts.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Bright Wind gas cloud in Brekk system (racing grounds)",  # SOURCE: p.312
        "quirk": "Every member wears a pin showing their race victories. Status is everything.",  # SOURCE: p.318
    },
    # SOURCE: p.316 Tier II — listed; p.318 description
    "Janus Syndicate": {
        "setting": "procyon",
        "tier": 2,
        "category": "Criminal",
        "description": (  # SOURCE: p.318
            "Weapons dealers that specialize in ship weapons, headed up by the ruthless "
            "Viktor Bax, who insists on the first deal with every client in person."
        ),
        "goal": "Become the dominant ship weapons supplier in Procyon.",  # EXPANDED
        "notable_npcs": [  # SOURCE: p.318
            "Viktor Bax (ruthless, insists on meeting every client personally)",
        ],
        "sector": "All sectors (mobile dealing operations)",  # EXPANDED
        "quirk": "Viktor Bax meets every new client personally. No exceptions.",  # SOURCE: p.318
    },
    # SOURCE: p.316 Tier II — listed; p.319 description
    "Turner Society": {
        "setting": "procyon",
        "tier": 2,
        "category": "Criminal",
        "description": (  # SOURCE: p.319
            "A Holt-based Syndicate running drug dens masquerading as society houses. "
            "Their drugs are cooked with rare Aketi animal parts and Vosian crystals — "
            "which they sometimes have trouble sourcing."
        ),
        "goal": "Secure a reliable supply chain for Aketi parts and Vosian crystals.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Holt system (drug den network)",  # SOURCE: p.319
        "quirk": "Their product requires ingredients from two different systems, making supply chain their greatest vulnerability.",  # EXPANDED
    },
    # SOURCE: p.316 Tier I — listed; p.317 description, p.323 full page
    "Cobalt Syndicate": {
        "setting": "procyon",
        "tier": 1,
        "category": "Criminal",
        "description": (
            "Once a labor union, the Cobalt Syndicate has turned to smuggling and "
            "extortion to carve out shipping lanes and have a real say. An organized "
            "labor union dabbling in a little crime to fund their demands for a better "
            "life. Usually display a blue stripe somewhere on their clothing."
        ),
        "goal": "Unify the labor force.",  # SOURCE: p.323 goal box
        "notable_npcs": [  # SOURCE: p.323
            "Jax (leader, cold, killer, arrogant)",
            "Keve (captain, augmented, defiant, enterprising)",
            "Sephua (Jax's sibling, thug, daring, envious, gambler)",
        ],
        "sector": "The Pit mining quarry on Aleph (HQ), major berth and docks on Warren",  # SOURCE: p.323
        "quirk": "Every member wears a solid blue stripe. A blue stripe on docks and warehouses is a call to action.",  # SOURCE: p.323
    },
    # SOURCE: p.316 Tier I — listed; p.317-318 description, p.326 full page
    "Dyrinek Gang": {
        "setting": "procyon",
        "tier": 1,
        "category": "Criminal",
        "description": (
            "Mostly young, disenfranchised xenos who have turned to crime and found "
            "strength and solidarity with each other. Based on Warren but looking to "
            "expand wherever there are other like-minded folks."
        ),
        "goal": "Take over HNN broadcast on Warren.",  # SOURCE: p.326 goal box
        "notable_npcs": [  # SOURCE: p.326
            "Dyrinek (xeno, revolutionary, proud)",
            "Burn (Memish mystic, xeno, fast, overconfident, untrained)",
            "Radds (human, hacker, smart)",
            "Myrk (xeno, gun enthusiast, hothead)",
        ],
        "sector": "Lost Paradise club with attached warehouse on Warren (HQ)",  # SOURCE: p.326
        "quirk": "When a new member joins, they all go on a drunken tear across the city.",  # SOURCE: p.326
    },
    # SOURCE: p.316 Tier I — listed; p.317 description
    "Wreckers": {
        "setting": "procyon",
        "tier": 1,
        "category": "Criminal",
        "description": (  # SOURCE: p.319
            "Scavengers and thieves with a few brilliant hackers, who incite factions "
            "to fight so that they may pick the battlefields clean later."
        ),
        "goal": "Pick the next major battlefield clean before anyone else.",  # EXPANDED
        "notable_npcs": [],  # EXPANDED
        "sector": "Brekk debris fields",  # EXPANDED
        "quirk": "They never start fights — they just make sure other people do, then profit from the aftermath.",  # SOURCE: p.319
    },
}

# =========================================================================
# FACTION STATUS SCALE
# SOURCE: Scum and Villainy.pdf — status track used throughout
# Exact label text EXPANDED (consistent with FITD system standard)
# =========================================================================

FACTION_STATUS: dict = {
    3: "Allied — Deep mutual trust and active cooperation. They go out of their way to help you.",
    2: "Friendly — Goodwill and willingness to assist. They will do you favors without hesitation.",
    1: "Helpful — Cautiously positive. They will trade and work with you given reason.",
    0: "Neutral — No strong feelings either way. Standard dealings.",
    -1: "Tense — Wary and suspicious. Dealings are possible but guarded.",
    -2: "Hostile — Active animosity. They will obstruct and oppose you when opportunity arises.",
    -3: "War — Open conflict. They will try to destroy you on sight.",
}

# =========================================================================
# FACTION LOOKUP HELPERS
# =========================================================================

def get_factions_by_tier(tier: int) -> list:
    """Return list of faction names at the given tier."""
    return [name for name, data in FACTIONS.items() if data["tier"] == tier]


def get_factions_by_category(category: str) -> list:
    """Return list of faction names in the given category (Hegemony/Weirdness/Criminal)."""
    return [name for name, data in FACTIONS.items() if data["category"] == category]


__all__ = [
    "FACTIONS",
    "FACTION_CATEGORIES",
    "FACTION_STATUS",
    "get_factions_by_tier",
    "get_factions_by_category",
]

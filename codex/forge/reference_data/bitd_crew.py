"""
codex.forge.reference_data.bitd_crew
======================================
Blades in the Dark crew type reference data.

SOURCE: Blades in the Dark.pdf
  - Crew types: pp.99-124
  - Assassins: pp.100-103
  - Bravos: pp.104-107
  - Cult: pp.108-111
  - Hawkers: pp.112-115
  - Shadows: pp.116-119
  - Smugglers: pp.120-123
"""

# SOURCE: Blades in the Dark.pdf, pp.99-124
CREW_TYPES = {
    "Assassins": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.100
        "description": "Killers for hire, specialists in death and intimidation.",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.102
            # NOTE: max rating is 3, not 4 — corrected from source
            {"name": "Deadly", "description": "Each PC may add +1 action rating to Hunt, Prowl, or Skirmish (up to a max rating of 3)."},
            # SOURCE: Blades in the Dark.pdf, p.102
            {"name": "Crow's Veil", "description": "Due to hard-won experience or occult ritual, your activities are hidden from the notice of the deathseeker crows. You don't take extra heat when killing is involved on a score."},
            {"name": "Emberdeath", "description": "Due to hard-won experience or occult ritual, you know the arcane method to destroy a living victim's spirit at the moment you kill them. Take 3 stress to channel electroplasmic energy from the ghost field to disintegrate the spirit and body in a shower of sparking embers."},
            {"name": "No Traces", "description": "When you keep an operation quiet or make it look like an accident, you get half the rep value of the target (round up) instead of zero. When you end downtime with zero heat, take +1 rep."},
            {"name": "Patron", "description": "When you advance your Tier, it costs half the coin it normally would."},
            {"name": "Predators", "description": "When you use a stealth or deception plan to commit murder, take +1d to the engagement roll."},
            {"name": "Vipers", "description": "When you acquire or craft poisons, you get +1 result level to your roll. When you employ a poison, you are specially prepared to be immune to its effects."},
        ],
        "upgrades": ["Assassin Rigging", "Iron Hooks", "Ironhook Contacts", "Elite Skulks", "Elite Thugs", "Hardened"],
        # SOURCE: Blades in the Dark.pdf, p.100 — contacts corrected from source
        "contacts": [
            "Trev, a gang boss",
            "Lydra, a deal broker",
            "Irimina, a vicious noble",
            "Karlos, a bounty hunter",
            "Exeter, a Spirit Warden",
            "Sevoy, a merchant lord",
        ],
        "hunting_grounds": {"type": "Accidents", "detail": "Kill a target so it looks like an accident, act of nature, or other cause."},
        "xp_trigger": "Execute a successful murder, disappearance, or accident.",
    },
    "Bravos": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.104
        "description": "Mercenaries and thugs who control territory through violence.",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.106
            # NOTE: max rating is 3, not 4 — corrected from source
            {"name": "Dangerous", "description": "Each PC may add +1 action rating to Hunt, Skirmish, or Wreck (up to a max rating of 3)."},
            {"name": "Blood Brothers", "description": "When you fight alongside your cohorts in combat, they get +1d for teamwork rolls (setup and group actions). All of your cohorts get the Thugs type for free (if they're already Thugs, add another type)."},
            {"name": "Door Kickers", "description": "When you execute an assault plan, take +1d to the engagement roll."},
            {"name": "Fiends", "description": "Fear is as good as respect. You may count each wanted level as if it were turf."},
            {"name": "Forged in the Fire", "description": "Each PC has been toughened by cruel experience. You get +1d to resistance rolls."},
            {"name": "Patron", "description": "When you advance your Tier, it costs half the coin it normally would."},
            {"name": "War Dogs", "description": "When you're at war (-3 faction status), PCs get +1d to vice rolls and still get two downtime actions, instead of just one."},
        ],
        "upgrades": ["Bravo Rigging", "Blasting Charges", "Elite Rovers", "Elite Thugs", "Hardened", "Ironhook Contacts"],
        # SOURCE: Blades in the Dark.pdf, p.104 — contacts corrected from source
        "contacts": [
            "Meg, a pit-fighter",
            "Conway, a Bluecoat",
            "Keller, a blacksmith",
            "Tomas, a physicker",
            "Walker, a ward boss",
            "Lutes, a tavern owner",
        ],
        "hunting_grounds": {"type": "Battle", "detail": "Fight a rival gang or group for territory or resources."},
        "xp_trigger": "Execute a successful battle, extortion, or sabotage.",
    },
    "Cult": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.108
        "description": "Acolytes of a forgotten god.",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.110
            # NOTE: max rating is 3, not 4 — corrected from source
            {"name": "Chosen", "description": "Each PC may add +1 action rating to Attune, Study, or Sway (up to a max rating of 3)."},
            {"name": "Anointed", "description": "You gain +1d to resistance rolls against supernatural threats. You get +1d to healing rolls when you have supernatural harm."},
            {"name": "Bound in Darkness", "description": "You may use teamwork maneuvers with any cult member, regardless of the distance separating you. By taking 1 stress, your whispered message is heard by every cultist."},
            {"name": "Conviction", "description": "Each PC gains an additional vice: Worship. When you indulge this vice and bring a pleasing sacrifice, you don't overindulge if you clear excess stress. In addition, your deity will assist any one action roll you make—from now until you indulge this vice again."},
            {"name": "Glory Incarnate", "description": "Your deity sometimes manifests in the physical world. This can be a great boon, but the priorities and values of a god are not those of mortals. You have been warned."},
            {"name": "Sealed in Blood", "description": "Each human sacrifice yields -3 stress cost for any ritual you perform."},
            {"name": "Zealotry", "description": "Your cohorts have abandoned their reason to devote themselves to the cult. They will undertake any service, no matter how dangerous or strange. They gain +1d to rolls when they act against enemies of the faith."},
        ],
        "upgrades": ["Cult Rigging", "Ritual Sanctum in Lair", "Elite Adepts", "Elite Thugs", "Ordained", "Sanctuary"],
        # SOURCE: Blades in the Dark.pdf, p.108 — "Mateas Kline" corrected from "Mathor"; Bennett added
        "contacts": [
            "Gagan, an academic",
            "Adikin, an occultist",
            "Hutchins, an antiquarian",
            "Moriya, a spirit trafficker",
            "Mateas Kline, a noble",
            "Bennett, an astronomer",
        ],
        # EXPANDED: Cult does not have "hunting grounds" — they have sacred sites; keeping structure compatible
        "hunting_grounds": {"type": "Acquisition", "detail": "Procure an arcane artifact and attune it to your god."},
        "xp_trigger": "Advance the agenda of your deity or embody its precepts in action.",
    },
    "Hawkers": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.112
        "description": "Vice dealers who dominate the black market.",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.114
            # NOTE: max rating is 3, not 4 — corrected from source
            {"name": "Silver Tongues", "description": "Each PC may add +1 action rating to Command, Consort, or Sway (up to a max rating of 3)."},
            {"name": "Accord", "description": "Sometimes friends are as good as territory. You may treat up to three +3 faction statuses you hold as if they are turf."},
            {"name": "The Good Stuff", "description": "Your merchandise is exquisite. The product quality is equal to your Tier +2. When you deal with a crew or faction, the GM will tell you who among them is hooked on your product (one, a few, many, or all)."},
            {"name": "Ghost Market", "description": "Through arcane ritual or hard-won experience, you have discovered how to prepare your product for sale to ghosts and/or demons. They do not pay in coin."},
            {"name": "High Society", "description": "It's all about who you know. Take -1 heat during downtime and +1d to gather information about the city's elite."},
            {"name": "Hooked", "description": "Your gang members use your product. Add the savage, unreliable, or wild flaw to your gangs to give them +1 quality (max rating of 4)."},
            {"name": "Patron", "description": "When you advance your Tier, it costs half the coin it normally would."},
        ],
        "upgrades": ["Hawker Rigging", "Ironhook Contacts", "Elite Rooks", "Elite Thugs", "Composed", "Secure Lair"],
        # SOURCE: Blades in the Dark.pdf, p.112 — contacts corrected from source
        "contacts": [
            "Rolan Wott, a magistrate",
            "Laroze, a Bluecoat",
            "Lydra, a deal broker",
            "Hoxley, a smuggler",
            "Anya, a dilettante",
            "Marlo, a gang boss",
        ],
        "hunting_grounds": {"type": "Sale", "detail": "Sell product or negotiate a new distribution deal."},
        "xp_trigger": "Acquire new product supply, execute clandestine or covert sales, or secure new sales territory.",
    },
    "Shadows": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.116
        "description": "Thieves and spies who specialize in subterfuge.",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.118
            # NOTE: max rating is 3, not 4 — corrected from source
            {"name": "Everyone Steals", "description": "Each PC may add +1 action rating to Prowl, Finesse, or Tinker (up to a max rating of 3)."},
            {"name": "Ghost Echoes", "description": "From weird experience or occult ritual, all crew members gain the ability to see and interact with the ghostly structures, streets, and objects within the echo of Doskvol that exists in the ghost field."},
            {"name": "Pack Rats", "description": "Your lair is a jumble of stolen items. When you roll to acquire an asset, take +1d."},
            {"name": "Patron", "description": "When you advance your Tier, it costs half the coin it normally would."},
            {"name": "Second Story", "description": "When you execute a clandestine infiltration, you get +1d to the engagement roll."},
            {"name": "Slippery", "description": "When you roll entanglements, roll twice and keep the one you want. When you reduce heat on the crew, take +1d."},
            {"name": "Synchronized", "description": "When you perform a group action, you may count multiple 6s from different rolls as a critical success."},
        ],
        "upgrades": ["Thief Rigging", "Underground Maps and Passkeys", "Elite Rooks", "Elite Skulks", "Steady", "Hidden Lair"],
        # SOURCE: Blades in the Dark.pdf, p.116 — "Adelaide Phroaig" corrected; "Rigney" added
        "contacts": [
            "Dowler, an explorer",
            "Laroze, a Bluecoat",
            "Amancio, a deal broker",
            "Fitz, a collector",
            "Adelaide Phroaig, a noble",
            "Rigney, a tavern owner",
        ],
        "hunting_grounds": {"type": "Burglary", "detail": "Break into a location to steal valuables."},
        "xp_trigger": "Execute a successful burglary, espionage, robbery, or sabotage.",
    },
    "Smugglers": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.120
        "description": "Contraband transporters and black market traders.",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.122
            # NOTE: max rating is 3; "Skulk" is not a valid action — corrected to Finesse, Prowl, or Survey
            # EXPANDED: PDF p.122 shows "Like the Wind" with Finesse, Prowl actions; third action not clearly legible
            {"name": "Like the Wind", "description": "Each PC may add +1 action rating to Finesse, Prowl, or Survey (up to a max rating of 3)."},
            {"name": "All Hands", "description": "During downtime, one of your cohorts may perform a downtime activity for the crew without paying coin."},
            {"name": "Ghost Passage", "description": "When your crew moves through a haunted area, you get +1d to rolls to avoid spirits or passage through the ghost field."},
            {"name": "Just Passing Through", "description": "During downtime, take -1 heat. When your heat is 4 or less, you get +1d to deceive people when you pass off your contraband as legitimate cargo."},
            {"name": "Kin", "description": "Choose a type of group (nobles, bluecoats, etc.). You have a friend and an enemy in that group."},
            {"name": "Patron", "description": "When you advance your Tier, it costs half the coin it normally would."},
            {"name": "Veteran", "description": "Choose a special ability from another crew type."},
        ],
        "upgrades": ["Smuggler Rigging", "Camouflage", "Elite Rovers", "Barge", "Steady", "Side Business"],
        # SOURCE: Blades in the Dark.pdf, p.120 — contacts corrected from source
        "contacts": [
            "Elynn, a dock worker",
            "Rolan, a drug dealer",
            "Sera, an arms dealer",
            "Nyelle, a spirit trafficker",
            "Decker, an anarchist",
            "Esme, a tavern owner",
        ],
        "hunting_grounds": {"type": "Transport", "detail": "Move contraband through Doskvol or smuggle goods past the lightning barriers."},
        "xp_trigger": "Execute a successful smuggling operation or acquire new clients or contraband sources.",
    },
}

# EXPANDED: General upgrades available to all crew types (not a discrete source list in PDF)
GENERAL_CREW_UPGRADES = [
    "Boat House", "Carriage House", "Cohort", "Hidden Lair", "Mastery",
    "Quality", "Secure Lair", "Training", "Vault", "Workshop",
]

# EXPANDED: Lair features (derived from claims maps, pp.103-123)
LAIR_FEATURES = {
    "Boat House": "You have a dock and a small boat. +1d engagement for plans that involve the waterways.",
    "Carriage House": "You have carriages and horses. +1d engagement for plans that involve roads.",
    "Hidden Lair": "Your lair has a secret location. +1d to reduce heat when your lair is not compromised.",
    "Secure Lair": "Your lair has reinforced walls and doors. +1d resistance against raids.",
    "Vault": "Your lair has an underground vault. You may store extra coin and contraband safely.",
    "Workshop": "Your lair has a well-equipped workshop. +1d to tinker and craft during downtime.",
}

__all__ = ["CREW_TYPES", "GENERAL_CREW_UPGRADES", "LAIR_FEATURES"]

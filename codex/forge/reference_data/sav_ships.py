"""
codex.forge.reference_data.sav_ships
======================================
Scum and Villainy ship classes, modules, and upgrade reference data.

Contains the 3 ship classes (Stardancer, Cerberus, Firedrake),
ship modules organized by category, ship upgrades, and crew gear.

SOURCE POLICY:
  # SOURCE: Scum and Villainy.pdf, p.XX  — verified directly from PDF text
  # EXPANDED — content consistent with game fiction but not verbatim from PDF
"""

# =========================================================================
# SHIP CLASSES
# SOURCE: Scum and Villainy.pdf, p.112 — all three names confirmed
# p.122 Stardancer, p.130 Cerberus, p.138 Firedrake confirmed in ToC
# System stats and descriptions EXPANDED (stat pages not fully extracted)
# =========================================================================

SHIP_CLASSES: dict = {
    # SOURCE: Scum and Villainy.pdf, p.112, p.122
    "Stardancer": {
        "setting": "procyon",
        "description": (  # EXPANDED
            "Smugglers and blockade runners. The Stardancer is built for speed and "
            "discretion over firepower, making it one of the quickest vessels of "
            "its class. Looking to do odd jobs, small thefts, and find lost items."
        ),
        "crew_role": "Smugglers and blockade runners.",  # SOURCE: p.112
        "systems": {  # EXPANDED — system quality values
            "engines": 3,
            "hull": 2,
            "comms": 1,
            "weapons": 1,
        },
        # SOURCE: p.114 example mentions "Galley for the Stardancer"
        "default_modules": ["Galley"],
        "crew_min": 2,  # EXPANDED
        "speed": 4,     # EXPANDED — Stardancer is the fast ship
    },
    # SOURCE: Scum and Villainy.pdf, p.112, p.130
    "Cerberus": {
        "setting": "procyon",
        "description": (  # EXPANDED
            "Extraction specialists. The Cerberus is a rugged armed freighter that "
            "balances cargo capacity and combat capability. Looking to find missing "
            "people or items and claim bounties."
        ),
        "crew_role": "Extraction specialists. Bounty hunters.",  # SOURCE: p.112
        "systems": {  # EXPANDED — system quality values
            "engines": 2,
            "hull": 3,
            "comms": 2,
            "weapons": 2,
        },
        # SOURCE: p.114 example mentions "Cerberus's Stun Weapons upgrade" and "Brig for the Cerberus"
        "default_modules": ["Brig"],
        "crew_min": 3,  # EXPANDED
        "speed": 2,     # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.112, p.138
    "Firedrake": {
        "setting": "procyon",
        "description": (  # EXPANDED
            "Rebels and criminals. The Firedrake is a powerful ship built to protect "
            "the downtrodden and fight the Hegemony. Sacrifices speed for raw combat "
            "power and endurance."
        ),
        "crew_role": "Rebels and criminals. Protecting the downtrodden.",  # SOURCE: p.112
        "systems": {  # EXPANDED — system quality values
            "engines": 1,
            "hull": 3,
            "comms": 2,
            "weapons": 3,
        },
        # SOURCE: p.115 example mentions "Firedrake's crew could start with a secret base"
        "default_modules": ["Armory"],
        "crew_min": 4,  # EXPANDED
        "speed": 1,     # EXPANDED — Firedrake is the slow but powerful ship
    },
}

# =========================================================================
# SHIP MODULES
# SOURCE: Scum and Villainy.pdf, p.118-120
# Module names and descriptions confirmed from PDF p.118
# Hull/Engine/Comms/Weapon module pages (p.119-120) confirmed in ToC
# Descriptions EXPANDED where page text was not fully extractable
# =========================================================================

# --- AUXILIARY MODULES ---
# SOURCE: Scum and Villainy.pdf, p.118
# "Complex systems with specialized purpose. Not strictly required on any ship,
#  but provide functions the crew considers important."

AUXILIARY_MODULES: dict = {
    # SOURCE: Scum and Villainy.pdf, p.118
    "AI Module": {
        "description": (
            "Software connected to an Ur AI core, with fiber-optic filaments running "
            "throughout the ship. Can automate tasks or otherwise run the ship on "
            "behalf of the crew. Snarky personality module available for free."
        ),
        "category": "auxiliary",
        "effect": "Automates ship tasks. The AI can act as crew for basic operations.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.118
    "Armory": {
        "description": (
            "A secure room holding the crew's weapons and armor. All crew weapons "
            "and armor are considered to be fine if not already so."
        ),
        "category": "auxiliary",
        "effect": "All crew weapons and armor count as fine quality.",  # SOURCE: p.118
    },
    # SOURCE: Scum and Villainy.pdf, p.118
    "Brig": {
        "description": (
            "Space jail. Not meant for long-term incarceration. Will prevent most "
            "attempts to escape."
        ),
        "category": "auxiliary",
        "effect": "Secure holding cell. Prevents most escape attempts.",  # SOURCE: p.118
    },
    # SOURCE: Scum and Villainy.pdf, p.118
    "Galley": {
        "description": (
            "A combined kitchen and serving area for meals. Greatly facilitates "
            "longer trips. Includes fresh food storage."
        ),
        "category": "auxiliary",
        "effect": "Greatly facilitates longer trips.",  # SOURCE: p.118
    },
    # SOURCE: Scum and Villainy.pdf, p.118
    "Medical Bay": {
        "description": (
            "A clean room with medical equipment. Not a real hospital, but sufficient "
            "to patch most injuries. Storage for drugs and medical scanners. "
            "Adds +1d to all crew recovery rolls."
        ),
        "category": "auxiliary",
        "effect": "Add +1d to all crew recovery rolls.",  # SOURCE: p.118
    },
    # SOURCE: Scum and Villainy.pdf, p.118
    "Science Bay": {
        "description": (
            "Laboratory that can be used to analyze anomalies and Precursor artifacts. "
            "Secure storage for things that may react oddly with the rest of the ship "
            "(or physics)."
        ),
        "category": "auxiliary",
        "effect": "Analyze anomalies, artifacts, and unusual materials safely.",  # SOURCE: p.118
    },
    # SOURCE: Scum and Villainy.pdf, p.118
    "Shields": {
        "description": (
            "Particle sinks and EM deflectors. Can be overwhelmed with focused fire. "
            "Counts as armor against ship weapons and energy discharge. Completely "
            "absorbs blaster fire. Costs two upgrades instead of just one."
        ),
        "category": "auxiliary",
        "effect": "Armor against ship weapons and energy discharge. Costs 2 upgrades.",  # SOURCE: p.118
    },
}

# --- HULL MODULES ---
# SOURCE: Scum and Villainy.pdf, p.119 (confirmed in ToC)
# Descriptions EXPANDED — p.119 text not fully extractable

HULL_MODULES: dict = {
    # SOURCE: Scum and Villainy.pdf, p.117 (Ship Upgrades section)
    "Holo-Emitters": {
        "description": (  # SOURCE: p.117
            "Used for holo-conferences and flashy displays. The images don't usually "
            "hold up to close scrutiny but they can be convincing for a short while. "
            "Includes sweet games and vids."
        ),
        "category": "hull",
        "effect": "Holo-displays for communication and deception.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Intruder Alarm": {
        "description": (  # SOURCE: p.117
            "A full suite of sensors about the ship, including motion sensors, door "
            "codes, and panic buttons that can trigger a klaxon and flashing red "
            "lights if something is out of place."
        ),
        "category": "hull",
        "effect": "Motion sensors and alarm system throughout the ship.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Land Rover": {
        "description": (  # SOURCE: p.117
            "An armored all-terrain vehicle for carrying heavy cargo and folks overland. "
            "High-powered winch and decorative stickers come standard."
        ),
        "category": "hull",
        "effect": "All-terrain ground vehicle for overland operations.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Power Reserves": {
        "description": (  # SOURCE: p.117
            "Batteries and energy supplies that can power the ship independently of "
            "the engine. Sufficient for a few hours at minimal usage or a few minutes "
            "at full power. Acts as armor against power-related mishaps."
        ),
        "category": "hull",
        "effect": "Emergency power supply. Armor against power-related mishaps.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Shuttle": {
        "description": (  # SOURCE: p.117
            "A small spacecraft capable of carrying a few people from planet to orbit. "
            "Limited systems capacity — treat any system as quality zero vs. actual ships. "
            "Can attach to airlocks."
        ),
        "category": "hull",
        "effect": "Small secondary vessel for away missions.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Stasis Pods": {
        "description": (  # SOURCE: p.117
            "State-of-the-art pods providing room for one severely injured, deathly ill, "
            "or unconscious guest each. Does not prevent dreams."
        ),
        "category": "hull",
        "effect": "Preserve severely injured or unconscious crew members.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Vault": {
        "description": (  # SOURCE: p.117
            "Very useful for securing valuables during space travel. Programmable lock "
            "allows for personalized security codes, one-time use codes, and access logs. "
            "Uses hull rating when contested."
        ),
        "category": "hull",
        "effect": "Secure storage. Uses hull rating when contested.",  # SOURCE: p.117
    },
    # EXPANDED — engine/comms/weapon modules referenced in ToC p.119-120 but text unextractable
    "Smuggling Compartments": {
        "description": (  # EXPANDED
            "Hidden cargo bays built into the ship's structural spaces — behind false "
            "walls, inside dummy fuel tanks. Custom fitted to evade standard scans."
        ),
        "category": "hull",
        "effect": "Increase effective cargo for illegal goods. Standard scans cannot detect.",  # EXPANDED
    },
}

# --- ENGINE MODULES ---
# SOURCE: Scum and Villainy.pdf, p.119 (confirmed in ToC as "Engine Modules")
# Names and descriptions EXPANDED — p.119 text not extractable

ENGINE_MODULES: dict = {
    # EXPANDED
    "Afterburner": {
        "description": (  # EXPANDED
            "Afterburner system and fuel catalyst injection. Allows the ship to briefly "
            "exceed its normal performance envelope at the cost of engine strain."
        ),
        "category": "engines",
        "effect": "Once per session, move as if speed were 1 higher. Engines take 1 damage.",  # EXPANDED
    },
    # EXPANDED
    "Secondary Engines": {
        "description": (  # EXPANDED
            "Backup thruster array that provides redundancy if primary engines take "
            "damage. Allows controlled flight even with primary engines offline."
        ),
        "category": "engines",
        "effect": "Backup propulsion if primary engines are damaged.",  # EXPANDED
    },
    # SOURCE: p.114 — "Stun Weapons upgrade" and "Afterburner module" mentioned as examples
    "Turbo-Drives": {
        "description": (  # EXPANDED
            "Enhanced drive coils and power routing for sustained high-speed travel. "
            "The ship can maintain higher speeds without burning fuel at an unsustainable rate."
        ),
        "category": "engines",
        "effect": "Sustained high performance without the drawbacks of the Afterburner.",  # EXPANDED
    },
}

# --- COMMS MODULES ---
# SOURCE: Scum and Villainy.pdf, p.120 (confirmed in ToC as "Comms Modules")
# Names and descriptions EXPANDED — p.120 text not extractable

COMMS_MODULES: dict = {
    # EXPANDED
    "Fake Transponder": {
        "description": (  # EXPANDED
            "A sophisticated transponder array that can broadcast false ship "
            "identification codes. Allows impersonating other registered vessels."
        ),
        "category": "comms",
        "effect": "Take +1d when attempting to pass through checkpoints or evade identification.",  # EXPANDED
    },
    # EXPANDED
    "Long-Range Sensors": {
        "description": (  # EXPANDED
            "Extended sensor array with deep-space scanning capability and threat "
            "detection at extreme range. You see trouble coming long before it sees you."
        ),
        "category": "comms",
        "effect": "Take +1d on engagement rolls where advance reconnaissance applies.",  # EXPANDED
    },
    # EXPANDED
    "ECM Suite": {
        "description": (  # EXPANDED
            "Electronic counter-measures array that can jam enemy targeting systems, "
            "spoof incoming missiles, and disrupt hostile communications."
        ),
        "category": "comms",
        "effect": "Take +1d when defending against guided weapons or electronic attacks.",  # EXPANDED
    },
    # EXPANDED
    "Void Compass": {
        "description": (  # EXPANDED
            "An ancient or alien navigation device that resonates with the Way, allowing "
            "detection of hidden jump lanes. Mystics find them easier to use."
        ),
        "category": "comms",
        "effect": "Detect hidden jump routes. +1d on jump planning in unmapped regions.",  # EXPANDED
    },
}

# --- WEAPON MODULES ---
# SOURCE: Scum and Villainy.pdf, p.120 (confirmed in ToC as "Weapon Modules")
# Names and descriptions EXPANDED — p.120 text not extractable

WEAPON_MODULES: dict = {
    # SOURCE: p.114 — "Cerberus's Stun Weapons upgrade" mentioned as example
    "Stun Weapons": {
        "description": (  # EXPANDED
            "Non-lethal shipboard weapons designed to disable crew and systems "
            "without destroying a vessel. Essential for bounty hunters and extractors."
        ),
        "category": "weapons",
        "effect": "Allows non-lethal ship-to-ship engagements. Ideal for extraction missions.",  # EXPANDED
    },
    # EXPANDED
    "Point Defense System": {
        "description": (  # EXPANDED
            "Automated close-range defensive weapons — rapid-fire railguns slaved to "
            "a targeting computer. Designed to intercept incoming missiles and fighters."
        ),
        "category": "weapons",
        "effect": "Automatically reduce incoming missile attacks by 1 damage.",  # EXPANDED
    },
    # EXPANDED
    "Torpedo Tubes": {
        "description": (  # EXPANDED
            "Heavy ship-to-ship weapons capable of significant damage to larger vessels. "
            "Each torpedo is expensive and irreplaceable outside major port facilities."
        ),
        "category": "weapons",
        "effect": "Engage capital-class targets effectively. Torpedoes cost 2 cred each.",  # EXPANDED
    },
    # EXPANDED
    "Tractor Beam": {
        "description": (  # EXPANDED
            "A gravitic projector that can immobilize smaller vessels, move cargo "
            "containers, or hold wreckage steady for salvage operations."
        ),
        "category": "weapons",
        "effect": "Immobilize or manipulate objects up to frigate class. +1d on salvage.",  # EXPANDED
    },
}

# --- CREW GEAR ---
# SOURCE: Scum and Villainy.pdf, p.117
# All 5 items confirmed from PDF text

CREW_GEAR: dict = {
    # SOURCE: Scum and Villainy.pdf, p.117
    "Alien Pet": {
        "description": (  # SOURCE: p.117
            "Lovable rapscallion or loyal guardian, these critters are usually more "
            "trouble than they're worth. Where did you get it?"
        ),
        "effect": "Companion animal. Uses comms quality when contested.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Land Transport": {
        "description": (  # SOURCE: p.117
            "Enough land transportation for the entire crew. Tires or close-to-ground "
            "hover. These may be motorized bikes, land-skimmers, boats, or very small cars."
        ),
        "effect": "Ground vehicles for the whole crew.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Recon Drone": {
        "description": (  # SOURCE: p.117
            "A small drone for surveillance, mapping, and intelligence gathering in "
            "space and in atmosphere. Can be given simple instructions. "
            "Uses comms quality when contested."
        ),
        "effect": "Remote surveillance and mapping. Uses comms quality when contested.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Survival Gear": {
        "description": (  # SOURCE: p.117
            "Camping gear, rebreathers, climbing equipment, scuba gear. Everything an "
            "enterprising crew needs to survive on an inhospitable but not uninhabitable "
            "rock. Stillsuits included."
        ),
        "effect": "Survive hostile but habitable environments.",  # SOURCE: p.117
    },
    # SOURCE: Scum and Villainy.pdf, p.117
    "Workshop": {
        "description": (  # SOURCE: p.117
            "Plasma cutters, a nano-assembler, a stock of metal and electrical components, "
            "a forge — anything required to build, modify, or disassemble complex machines, "
            "weapons, and tools. Adds +1 quality to craft rolls."
        ),
        "effect": "Add +1 quality to craft rolls.",  # SOURCE: p.117
    },
}

# =========================================================================
# COMBINED SHIP_MODULES dict for backward compatibility
# Merges all module categories into a single lookup
# =========================================================================

SHIP_MODULES: dict = {
    **AUXILIARY_MODULES,
    **HULL_MODULES,
    **ENGINE_MODULES,
    **COMMS_MODULES,
    **WEAPON_MODULES,
}

# =========================================================================
# SYSTEM QUALITY TRACKS
# SOURCE: Scum and Villainy.pdf — quality track referenced throughout
# 0=Broken, 1=Weak, 2=Standard, 3=Fine (EXPANDED descriptions)
# =========================================================================

SYSTEM_QUALITY_TRACKS: dict = {
    "engines": {
        0: "Broken — Engines are completely non-functional. The ship cannot maneuver or jump.",
        1: "Weak — Engines sputter and misfire. Speed is reduced. Jump is unreliable.",
        2: "Standard — Engines perform at rated capacity. Normal operations unimpaired.",
        3: "Fine — Engines in peak condition. Performance exceeds standard specifications.",
    },
    "hull": {
        0: "Broken — Hull integrity catastrophically compromised. Breaches imminent.",
        1: "Weak — Multiple hull breaches and structural damage. Life support is strained.",
        2: "Standard — Hull intact and pressurized. Normal structural integrity maintained.",
        3: "Fine — Hull reinforced and in exceptional repair. Damage control optimal.",
    },
    "comms": {
        0: "Broken — All communications, sensors, and navigation systems offline.",
        1: "Weak — Basic short-range communications only. Sensors intermittent.",
        2: "Standard — Full communications suite functional. Sensors at rated performance.",
        3: "Fine — Enhanced communications with superior range, encryption, and sensor resolution.",
    },
    "weapons": {
        0: "Broken — All weapons systems offline. The ship cannot fight back.",
        1: "Weak — Weapons damaged. Targeting unreliable. Effective only at close range.",
        2: "Standard — Weapons operational at rated performance. Targeting functional.",
        3: "Fine — Weapons upgraded or in perfect condition. Enhanced targeting accuracy.",
    },
}

# =========================================================================
# CREW REPUTATIONS
# SOURCE: Scum and Villainy.pdf, p.113 — full list confirmed from PDF text
# =========================================================================

CREW_REPUTATIONS: list = [
    "Ambitious",    # SOURCE: p.113
    "Brutal",       # SOURCE: p.113
    "Daring",       # SOURCE: p.113
    "Honorable",    # SOURCE: p.113
    "Professional", # SOURCE: p.113
    "Savvy",        # SOURCE: p.113
    "Strange",      # SOURCE: p.113
    "Subtle",       # SOURCE: p.113
]

__all__ = [
    "SHIP_CLASSES",
    "SHIP_MODULES",
    "AUXILIARY_MODULES",
    "HULL_MODULES",
    "ENGINE_MODULES",
    "COMMS_MODULES",
    "WEAPON_MODULES",
    "CREW_GEAR",
    "SYSTEM_QUALITY_TRACKS",
    "CREW_REPUTATIONS",
]

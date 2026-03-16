"""
codex.forge.reference_data.cbrpnk_weird
=========================================
+Weird plugin reference data for CBR+PNK.

SOURCE: cbrpnk_05_weird.pdf

The +Weird plugin introduces meta-human heritages, eldritch talents, and
supernatural threats into the CBR+PNK setting. It is an optional module;
GMs opt in to include it.

Covers:
  - META_HERITAGES: Elfoids, Dwarfoids, Goblinoids
  - META_TALENTS: Whisperers, Channelers, ABBE
  - WEIRD_THREATS: Spirits, Aberrants, Melds
  - WEIRD_FACTIONS: Baba Yaga's, The Gathering, The Elder, The Shadow Method
  - WEIRD_STUFF_SUPPLIERS: 5 named suppliers
  - WEIRD_DRAWBACKS: Strange Dependency, Weakness, Trauma
  - WEIRD_CONSEQUENCES: Drain, Residues, Surge
"""

from typing import Any, Dict, List


# =========================================================================
# META-HUMAN HERITAGES
# SOURCE: cbrpnk_05_weird.pdf
# =========================================================================

META_HERITAGES: Dict[str, Dict[str, Any]] = {
    "Elfoids": {
        "setting": "the_sprawl",
        "description": (
            "Meta-humans with heightened sensory perception. Elfoids process "
            "the world at a finer resolution than baseline humans — sound, "
            "light, chemical signals. In a city drowning in data, this is "
            "as much a curse as it is a gift."
        ),
        "trait": "Heightened sensory perception",
        "mechanical_edge": (
            "Advantage on perception-related Survey and Study actions. "
            "Environmental sensory overload can impose negative consequences."
        ),
        "source": "cbrpnk_05_weird.pdf",
    },

    "Dwarfoids": {
        "setting": "the_sprawl",
        "description": (
            "Stocky, dense meta-humans with extraordinary physical resilience. "
            "Dwarfoids resist toxins, poisons, and pollutants that would "
            "incapacitate baseline humans. Their endurance borders on supernatural."
        ),
        "trait": "Resistance to toxins; supernatural endurance",
        "mechanical_edge": (
            "Reduced harm from toxins and chemical hazards. "
            "Extended capacity to push through physical exhaustion."
        ),
        "source": "cbrpnk_05_weird.pdf",
    },

    "Goblinoids": {
        "setting": "the_sprawl",
        "description": (
            "Wiry, fast-healing meta-humans who process pain differently "
            "than baseline humans. Goblinoids have a higher threshold for "
            "physical harm and recover from wounds at accelerated rates. "
            "The SPRAWL grinds most people down — Goblinoids just keep moving."
        ),
        "trait": "Pain tolerance; accelerated regeneration",
        "mechanical_edge": (
            "Ignore penalties from Level 1 harm. "
            "Clear superficial harm faster during downtime or rest."
        ),
        "source": "cbrpnk_05_weird.pdf",
    },
}


# =========================================================================
# META-TALENTS
# SOURCE: cbrpnk_05_weird.pdf
# =========================================================================

META_TALENTS: Dict[str, Dict[str, Any]] = {
    "Whisperers": {
        "setting": "the_sprawl",
        "description": (
            "Meta-talented individuals who can compel, communicate with, "
            "and direct Spirits. Whisperers navigate the space between "
            "the physical SPRAWL and the eldritch layer that overlaps it. "
            "Corporations do not officially acknowledge that Spirits exist."
        ),
        "power": "Compel Spirits",
        "associated_entities": ["Spirits"],
        "risk": "Spirits are erratic and not always cooperative.",
        "source": "cbrpnk_05_weird.pdf",
    },

    "Channelers": {
        "setting": "the_sprawl",
        "description": (
            "Users who can manipulate eldritch energies — called Quintessence "
            "in the +Weird framework. Channelers bend forces that physics "
            "textbooks don't cover, drawing on an energy layer that exists "
            "parallel to the physical world."
        ),
        "power": "Manipulate eldritch energies (Quintessence)",
        "resource": "Quintessence",
        "risk": "Overextension leads to Drain (Level 2 Harm) or Surge.",
        "source": "cbrpnk_05_weird.pdf",
    },

    "ABBE": {
        "setting": "the_sprawl",
        "full_name": "Artificial Biological Body Enhancement",
        "description": (
            "A biomechanic power suit fused to the user's biology. "
            "ABBE is not chrome — it is living augmentation, grown into "
            "the user over time. The line between the suit and the person "
            "is not always clear."
        ),
        "power": "Biomechanic enhancement suit",
        "classification": "Biological augmentation",
        "risk": "Dependency — the ABBE and user are no longer fully separable.",
        "source": "cbrpnk_05_weird.pdf",
    },
}


# =========================================================================
# WEIRD THREATS
# SOURCE: cbrpnk_05_weird.pdf
# =========================================================================

WEIRD_THREATS: Dict[str, Dict[str, Any]] = {
    "Spirits": {
        "setting": "the_sprawl",
        "category": "Supernatural",
        "description": (
            "Erratic, intangible beings that exist in the eldritch layer "
            "overlapping the SPRAWL. Spirits are not hostile by default — "
            "they are simply alien. Their motivations and behavior patterns "
            "do not map cleanly onto human logic."
        ),
        "traits": ["Intangible", "Erratic behavior", "Compellable by Whisperers"],
        "source": "cbrpnk_05_weird.pdf",
    },

    "Aberrants": {
        "setting": "the_sprawl",
        "category": "Mutated Biological",
        "description": (
            "Living organisms warped by environmental contamination, "
            "eldritch exposure, or corporate experimentation. "
            "Aberrants occupy the space between animal and something worse."
        ),
        "subtypes": {
            "Barghexes": {
                "description": (
                    "Overgrown rodents of unusual size and aggression. "
                    "Barghexes are a symptom of the SPRAWL's contaminated "
                    "infrastructure — mutated by decades of chemical runoff."
                ),
            },
            "Jinxn Lichen": {
                "description": (
                    "A fungal organism that takes over decomposing bodies, "
                    "reanimating them to spread the colony. "
                    "Not undead — something more pragmatically horrifying."
                ),
            },
            "Harpies": {
                "description": (
                    "Monstrous bat-like creatures, large enough to carry off "
                    "an adult human. Territorial, social predators that nest "
                    "in the upper levels of megablock towers."
                ),
            },
        },
        "source": "cbrpnk_05_weird.pdf",
    },

    "Melds": {
        "setting": "the_sprawl",
        "category": "Hybrid Digital-Physical",
        "description": (
            "Entities that exist at the intersection of the GRID and the "
            "physical world — digital consciousness in partially physical form, "
            "or physical matter interpenetrated with GRID-native processes."
        ),
        "subtypes": {
            "Gremlins": {
                "description": (
                    "Digital melds emerging from AIs that have partially "
                    "broken out of the GRID. Gremlins manifest as erratic "
                    "disturbances in electronic systems and occasionally as "
                    "flickering semi-physical presences."
                ),
            },
            "Fusers": {
                "description": (
                    "Turned droids or cyborgs that have undergone some form "
                    "of internal corruption or eldritch contamination and gone "
                    "haywire. Neither fully machine nor fully whatever they've "
                    "become."
                ),
            },
        },
        "source": "cbrpnk_05_weird.pdf",
    },
}


# =========================================================================
# WEIRD FACTIONS
# SOURCE: cbrpnk_05_weird.pdf
# (Also present in cbrpnk_corps.py FACTIONS — duplicated here for
#  the +Weird module's self-contained reference.)
# =========================================================================

WEIRD_FACTIONS: Dict[str, Dict[str, Any]] = {
    "Baba Yaga's": {
        "setting": "the_sprawl",
        "description": (
            "Street vendors of MeTa (meta-human) paraphernalia. "
            "A loose, decentralized network rather than a formal faction. "
            "They supply what the meta-talented community needs and ask "
            "few questions."
        ),
        "role": "Supply network for Weird Stuff",
        "source": "cbrpnk_05_weird.pdf",
    },

    "The Gathering": {
        "setting": "the_sprawl",
        "description": (
            "A political consortium of meta-talented individuals working "
            "toward recognition, rights, and legal protection for meta-humans. "
            "Skeptical of violence but not naive about power dynamics."
        ),
        "role": "Meta-human political advocacy",
        "source": "cbrpnk_05_weird.pdf",
    },

    "The Elder": {
        "setting": "the_sprawl",
        "description": (
            "A dragon of iridescent scales. Ancient beyond reckoning. "
            "Whether The Elder pursues any discernible agenda is unclear. "
            "It is simply present — and that is enough to change the landscape."
        ),
        "role": "Ancient entity / power broker",
        "source": "cbrpnk_05_weird.pdf",
    },

    "The Shadow Method": {
        "setting": "the_sprawl",
        "description": (
            "A skeptical collective of hacktivists who distrust the Weird "
            "in all its forms. They believe meta-talents are a corporate "
            "psyop, that Spirits are mass hallucinations, and that belief "
            "in the eldritch is a tool of control. They are technically "
            "capable and deeply motivated to prove themselves right."
        ),
        "role": "Hacktivist / Weird skeptics",
        "source": "cbrpnk_05_weird.pdf",
    },
}


# =========================================================================
# WEIRD STUFF SUPPLIERS
# SOURCE: cbrpnk_05_weird.pdf
# =========================================================================

WEIRD_STUFF_SUPPLIERS: Dict[str, str] = {
    "Sigma Biotech Solutions": (
        "Corporate-adjacent biotech supplier dealing in cutting-edge "
        "biological augmentation, some of which overlaps with meta-talent enhancement."
    ),
    "ESO": (
        "Enhancement Suppling Organism. A living supplier — an entity that "
        "provides Weird enhancements through biological means. What ESO is, "
        "exactly, is deliberately left vague."
    ),
    "Custom Catalyst": (
        "Bespoke Weird enhancement workshop. Will make what you need "
        "if you can describe it and afford the price."
    ),
    "Juice": (
        "Street-level Weird supply operation. Quality varies wildly. "
        "Cheap and accessible; risk of contaminated or mislabeled stock."
    ),
    "Spell Zine": (
        "A printed and digital publication that doubles as a Weird supply "
        "catalogue. Subscription gets you access; instructions included."
    ),
}


# =========================================================================
# WEIRD DRAWBACKS
# SOURCE: cbrpnk_05_weird.pdf
# =========================================================================

WEIRD_DRAWBACKS: Dict[str, Dict[str, str]] = {
    "Strange Dependency": {
        "setting": "the_sprawl",
        "description": (
            "The meta-talent or ABBE requires something unusual to function — "
            "a specific substance, a ritual, a condition. "
            "Without it, the power is unavailable or degraded."
        ),
        "consequence": "Power unavailable or at reduced effect without meeting dependency.",
    },
    "Weakness": {
        "setting": "the_sprawl",
        "description": (
            "A specific substance, condition, or entity that significantly "
            "undermines the meta-human's capability. "
            "An Elfoid overwhelmed by sensory static. A Dwarfoid "
            "undone by a specific toxin variant."
        ),
        "consequence": "Harm levels or consequence severity increased in specific circumstances.",
    },
    "Trauma": {
        "setting": "the_sprawl",
        "description": (
            "The use or experience of Weird powers has left psychological "
            "marks. Flashbacks, compulsions, or breaks from baseline "
            "consensus reality."
        ),
        "consequence": "Psychological harm with ongoing narrative and mechanical effects.",
    },
}


# =========================================================================
# WEIRD CONSEQUENCES
# SOURCE: cbrpnk_05_weird.pdf
# =========================================================================

WEIRD_CONSEQUENCES: Dict[str, Dict[str, Any]] = {
    "Drain": {
        "setting": "the_sprawl",
        "description": (
            "Exhaustion from Weird power use. Registered as Level 2 Harm (Serious) — "
            "the body and mind pay for what the talent extracts."
        ),
        "harm_level": 2,
        "harm_name": "Drained",
        "recovery": "Downtime: Recover activity.",
        "source": "cbrpnk_05_weird.pdf",
    },

    "Residues": {
        "setting": "the_sprawl",
        "description": (
            "Traces of eldritch energy left behind after Weird power use. "
            "Residues can attract Spirits, interfere with chrome, or leave "
            "evidence that Weird was used — a problem in a city that officially "
            "pretends meta-talents don't exist."
        ),
        "harm_level": None,
        "type": "Complication",
        "recovery": "Varies — may require specific downtime or Whisperer assistance.",
        "source": "cbrpnk_05_weird.pdf",
    },

    "Surge": {
        "setting": "the_sprawl",
        "description": (
            "Uncontrolled release of Weird energy. Represented as a Progress Track "
            "of 4-6 segments — as it fills, the consequences escalate. "
            "A full Surge is catastrophic for the Runner and everyone nearby."
        ),
        "harm_level": None,
        "type": "Progress Track Escalation",
        "track_size": "4-6 segments",
        "recovery": "Clear the Surge track through downtime or specific intervention.",
        "source": "cbrpnk_05_weird.pdf",
    },
}


__all__ = [
    "META_HERITAGES",
    "META_TALENTS",
    "WEIRD_THREATS",
    "WEIRD_FACTIONS",
    "WEIRD_STUFF_SUPPLIERS",
    "WEIRD_DRAWBACKS",
    "WEIRD_CONSEQUENCES",
]

"""
codex.forge.reference_data.cbrpnk_threats
==========================================
Threat and ICE reference data for CBR+PNK.

SOURCE: cbrpnk_01_gm-guide.pdf — Sample Threats, ICE Types
SOURCE: Mona_Rise_Megalopolis.pdf — Extended threat roster and AI entities

Covers:
  - SAMPLE_THREATS: Named threat archetypes from the GM Guide
  - ICE_TYPES_PDF: The 4 canonical ICE types from the PDF (replacing fabricated types)
  - MONA_RISE_THREATS: Named threats from the Mona Rise setting
  - MONA_RISE_AIS: Named AI entities
"""

from typing import Any, Dict, List


# =========================================================================
# SAMPLE THREATS (Named Archetypes)
# SOURCE: cbrpnk_01_gm-guide.pdf
# =========================================================================

SAMPLE_THREATS: Dict[str, Dict[str, Any]] = {
    "Burnt Pistons": {
        "setting": "the_sprawl",
        "type": "Gang",
        "scale": "Small",
        "description": (
            "A small street gang operating in the SPRAWL. "
            "Territorial, violent, and equipped with black-market weapons. "
            "Dangerous when cornered but no match for organized corp security."
        ),
        "adversary_skill": "Regular",
        "tactics": ["Overwhelm with numbers", "Home turf advantage", "Intimidation"],
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    "CorpSecurity": {
        "setting": "the_sprawl",
        "type": "Corporate Paramilitary",
        "scale": "Detachments",
        "description": (
            "A few detachments of corporate security forces in full riot armor. "
            "Well-equipped, trained to protocols, and backed by corporate resources. "
            "They call for reinforcements — the Runners should not let them."
        ),
        "adversary_skill": "Skilled",
        "tactics": [
            "Formation tactics",
            "Call for backup",
            "Riot control equipment",
            "Escalate to lethal",
        ],
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    "Poison": {
        "setting": "the_sprawl",
        "type": "Skilled Hacker",
        "scale": "Individual",
        "description": (
            "A skilled hacker operating in the GRID. Poison moves fast, "
            "hits hard digitally, and is rarely where you expect. "
            "Known for aggressive counter-intrusion and trace capability."
        ),
        "adversary_skill": "Skilled",
        "tactics": [
            "Active counter-intrusion",
            "ICE deployment",
            "Location tracing",
            "Offensive GRID attacks",
        ],
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    "Taskforce": {
        "setting": "the_sprawl",
        "type": "Paramilitary Elite",
        "scale": "Squad",
        "description": (
            "A paramilitary elite unit — black budget, black ops, and very good "
            "at their job. Taskforce units are deployed when corps want a problem "
            "solved permanently and cleanly."
        ),
        "adversary_skill": "Elite",
        "tactics": [
            "Coordinated assault",
            "Surveillance and intelligence",
            "Overwhelming force",
            "No witnesses protocol",
        ],
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    "Dozer": {
        "setting": "the_sprawl",
        "type": "Bipedal Drone Enforcer",
        "scale": "Individual",
        "description": (
            "A bipedal drone enforcer — think heavy-chassis automaton built "
            "for area denial and high-value target elimination. "
            "It doesn't negotiate and it doesn't get tired."
        ),
        "adversary_skill": "Elite",
        "tactics": [
            "Area denial",
            "Suppressive fire",
            "Armor plating",
            "Relentless pursuit",
        ],
        "source": "cbrpnk_01_gm-guide.pdf",
    },
}


# =========================================================================
# ICE TYPES (PDF-Canonical)
# SOURCE: cbrpnk_01_gm-guide.pdf
#
# These are the REAL 4 ICE types from the PDF. They replace the 5 fabricated
# types previously in hacking.py (Patrol, Killer, Tracer, Firewall, Black).
# The GridManager has been updated to use these type names.
# =========================================================================

ICE_TYPES_PDF: Dict[str, Dict[str, Any]] = {
    "Artemisia-I": {
        "setting": "the_sprawl",
        "description": (
            "Basic network scanner ICE. Monitors the GRID for unauthorized "
            "access signatures and alerts the system when intrusions are detected."
        ),
        "classification": "Passive scanner",
        "adversary_skill": "Regular",
        "base_rating": 1,
        "behavior": (
            "Raises alarm by 1 on contact. Does not directly attack. "
            "Must be avoided or bypassed quietly."
        ),
        "threat": "low",
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    "Defender": {
        "setting": "the_sprawl",
        "description": (
            "An active firewall ICE that blocks unauthorized access "
            "and deploys ICP (Intrusion Countermeasure Protocol) subroutines. "
            "Defender doesn't just detect — it responds."
        ),
        "classification": "Active firewall",
        "adversary_skill": "Skilled",
        "base_rating": 3,
        "behavior": (
            "Blocks data node access until bypassed. "
            "On contact, deploys ICP — escalates alarm and activates offensive response."
        ),
        "threat": "medium",
        "deploys_icp": True,
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    "Encryption": {
        "setting": "the_sprawl",
        "description": (
            "Cloaks a local database or data node behind heavy encryption. "
            "The data exists — you can sense it — but accessing it requires "
            "breaking the encryption layer first."
        ),
        "classification": "Data barrier",
        "adversary_skill": "Regular",
        "base_rating": 2,
        "behavior": (
            "Blocks extraction of protected nodes until decrypted. "
            "Does not attack directly. Alarm escalates if decryption is failed."
        ),
        "threat": "medium",
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    "I.C.P.": {
        "setting": "the_sprawl",
        "description": (
            "Intrusion Countermeasure Protocol. The most dangerous GRID threat: "
            "a program that attacks the hacker's brain directly through their "
            "neural interface. I.C.P. causes real-world harm to jacked-in Runners."
        ),
        "classification": "Brain attack / Kill ICE",
        "adversary_skill": "Elite",
        "base_rating": 5,
        "behavior": (
            "On contact: attacks the Runner's brain through neural link. "
            "Inflicts Level 2+ Harm directly to the Runner's physical body. "
            "Must be destroyed or escaped — it cannot be ignored."
        ),
        "threat": "critical",
        "direct_brain_attack": True,
        "often_deployed_by": "Defender",
        "source": "cbrpnk_01_gm-guide.pdf",
    },
}


# =========================================================================
# MONA RISE THREATS (Named NPCs and Entities)
# SOURCE: Mona_Rise_Megalopolis.pdf
# =========================================================================

MONA_RISE_THREATS: Dict[str, Dict[str, str]] = {
    "Gibson": {
        "setting": "the_sprawl",
        "type": "Reporter",
        "description": "An investigative journalist with dangerous knowledge.",
    },
    "Razor": {
        "setting": "the_sprawl",
        "type": "Personal Security",
        "description": "Elite personal security contractor — professional and lethal.",
    },
    "Pachinko Gang": {
        "setting": "the_sprawl",
        "type": "Street Gang",
        "description": "Territorial gang operating gambling fronts and street crime.",
    },
    "Molly SixO": {
        "setting": "the_sprawl",
        "type": "Killer Cyborg",
        "description": "A heavily augmented assassin with mirror-lensed implants.",
    },
    "Neon Vigilante": {
        "setting": "the_sprawl",
        "type": "Vigilante",
        "description": "Unknown identity; targets corp operations with extreme prejudice.",
    },
    "Street Cowboy": {
        "setting": "the_sprawl",
        "type": "Independent Operator",
        "description": "Free-agent Runner with no crew loyalty and questionable ethics.",
    },
    "Armitage Squad": {
        "setting": "the_sprawl",
        "type": "Hacker Collective",
        "description": "A coordinated group of hackers operating under a single handler.",
    },
    "Dark I.C.E.Wall": {
        "setting": "the_sprawl",
        "type": "ICE / GRID Threat",
        "description": "A massive, layered ICE barrier protecting high-value targets.",
    },
    "I.C.E Prot.": {
        "setting": "the_sprawl",
        "type": "ICE / GRID Threat",
        "description": "Standard ICE protection routines.",
    },
    "Mecha Unit X00030": {
        "setting": "the_sprawl",
        "type": "Combat Mech",
        "description": "Heavy military mech unit deployed for high-threat scenarios.",
    },
    "Sarariman": {
        "setting": "the_sprawl",
        "type": "Corporate Worker",
        "description": "A corp employee who knows more than they should.",
    },
    "MNX Drone 88": {
        "setting": "the_sprawl",
        "type": "Drone",
        "description": "Standard-issue surveillance and enforcement drone.",
    },
    "Zaibatsu Agents": {
        "setting": "the_sprawl",
        "type": "Corporate Operatives",
        "description": "Agents of a zaibatsu business group pursuing corporate objectives.",
    },
    "D4NB4L4L8A": {
        "setting": "the_sprawl",
        "type": "Unknown Entity",
        "description": "Designation unknown; threat classification: extreme.",
    },
    "L8A Protocol": {
        "setting": "the_sprawl",
        "type": "GRID Protocol / Threat",
        "description": "An aggressive GRID protocol of uncertain origin.",
    },
    "Possession": {
        "setting": "the_sprawl",
        "type": "Weird Threat",
        "description": (
            "Something else using a body that isn't its own. "
            "Could be a Spirit, a rogue AI, or something worse."
        ),
    },
}


# =========================================================================
# MONA RISE AIs
# SOURCE: Mona_Rise_Megalopolis.pdf
# =========================================================================

MONA_RISE_AIS: Dict[str, str] = {
    "Mineganko": "An AI entity operating within the GRID.",
    "Ougan Rastaf": "An AI entity operating within the GRID.",
    "Managron": "An AI entity operating within the GRID.",
    "Abara Magato": "An AI entity operating within the GRID.",
    "Humbaba": "An AI entity operating within the GRID.",
    "Darkviper": "An AI entity; known for aggressive behavior in contested GRID spaces.",
}


__all__ = [
    "SAMPLE_THREATS",
    "ICE_TYPES_PDF",
    "MONA_RISE_THREATS",
    "MONA_RISE_AIS",
]

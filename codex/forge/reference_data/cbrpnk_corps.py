"""
codex.forge.reference_data.cbrpnk_corps
=========================================
Faction and megacorporation reference data for CBR+PNK.

Renamed from CORPORATIONS to FACTIONS (broader scope — includes street gangs,
weird factions, and off-world interests alongside megacorps).
CORPORATIONS is kept as a re-export alias for backward compatibility.

Sources:
  cbrpnk_01_gm-guide.pdf    — Omni Global Solutions (sample oppressor)
  Mona_Rise_Megalopolis.pdf  — Toha Heavy Industries, TekNet Megacorp, MezoTuring Hosaka
  cbrpnk_05_weird.pdf        — Weird factions: Baba Yaga's, The Gathering, The Elder, The Shadow Method
  cbrpnk_04_prdtr.pdf        — PRDTR factions: Insurgents, Corporate Security (APX), Scavengers
"""

from typing import Any, Dict, List


# =========================================================================
# FACTIONS
# =========================================================================

FACTIONS: Dict[str, Dict[str, Any]] = {

    # ------------------------------------------------------------------
    # SOURCE: cbrpnk_01_gm-guide.pdf — Sample Oppressor for Long Shot mode
    # ------------------------------------------------------------------

    "Omni Global Solutions": {
        "setting": "the_sprawl",
        "type": "Megacorporation",
        "tier": 5,
        "sector": "Conglomerate",
        "security_level": 5,
        "description": (
            "A mega conglomerate with fingers in every major industry sector. "
            "Omni Global Solutions doesn't specialize — it owns. Infrastructure, "
            "media, biotech, military contracts, financial services. "
            "When the GM Guide needed a sample oppressor for Long Shot campaigns, "
            "OGS was the obvious choice: faceless, total, and everywhere."
        ),
        "role": "Sample oppressor for Long Shot campaign mode.",
        "long_shot_angles": ["Take Down", "Resist", "Liberate"],
        "notable_npcs": [],  # Not detailed in source
        "source": "cbrpnk_01_gm-guide.pdf",
    },

    # ------------------------------------------------------------------
    # SOURCE: Mona_Rise_Megalopolis.pdf — City-state factions
    # ------------------------------------------------------------------

    "Toha Heavy Industries": {
        "setting": "the_sprawl",
        "type": "Megacorporation",
        "tier": 4,
        "sector": "Industrial / Transport",
        "security_level": 4,
        "description": (
            "A dominant industrial and transport corporation controlling logistics "
            "and heavy manufacturing across the Mona Rise megalopolis. "
            "Led by Toha Makima."
        ),
        "notable_npcs": [
            {
                "name": "Toha Makima",
                "role": "Leader",
                "note": "Controls industrial and transport operations.",
            }
        ],
        "source": "Mona_Rise_Megalopolis.pdf",
    },

    "TekNet Megacorp": {
        "setting": "the_sprawl",
        "type": "Megacorporation",
        "tier": 4,
        "sector": "Servers / Orbital",
        "security_level": 4,
        "description": (
            "Manages server infrastructure and orbital data relay networks "
            "across the megalopolis. Led by the hacker identity Poison_Kiss."
        ),
        "notable_npcs": [
            {
                "name": "Poison_Kiss",
                "role": "Leader",
                "note": "Skilled hacker who commands TekNet's operations.",
            }
        ],
        "source": "Mona_Rise_Megalopolis.pdf",
    },

    "MezoTuring Hosaka": {
        "setting": "the_sprawl",
        "type": "Megacorporation",
        "tier": 3,
        "sector": "Digital Finance",
        "security_level": 3,
        "description": (
            "A Martian family-run megacorp specializing in digital money, "
            "financial instruments, and encrypted transactions. "
            "The Hosaka family maintains strict dynastic control. "
            "Led by Hatlee Hosaka."
        ),
        "notable_npcs": [
            {
                "name": "Hatlee Hosaka",
                "role": "Family Patriarch / CEO",
                "note": "Martian family head; controls digital money operations.",
            }
        ],
        "source": "Mona_Rise_Megalopolis.pdf",
    },

    # ------------------------------------------------------------------
    # SOURCE: cbrpnk_05_weird.pdf — Weird factions
    # ------------------------------------------------------------------

    "Baba Yaga's": {
        "setting": "the_sprawl",
        "type": "Street Vendor Network",
        "tier": 1,
        "sector": "Weird / Meta-Human Supply",
        "security_level": 1,
        "description": (
            "A loose network of street vendors dealing in MeTa (meta-human) "
            "paraphernalia — weird augmentations, ritual materials, eldritch "
            "supplies, and Weird Stuff for the meta-talented community. "
            "More folklore than formal faction, but they know what you need."
        ),
        "notable_npcs": [],  # Not detailed in source
        "source": "cbrpnk_05_weird.pdf",
    },

    "The Gathering": {
        "setting": "the_sprawl",
        "type": "Political Consortium",
        "tier": 2,
        "sector": "Meta-Talented Rights / Political",
        "security_level": 2,
        "description": (
            "A political consortium of meta-talented individuals — Whisperers, "
            "Channelers, heritage-bearers — advocating for meta-human rights "
            "through legal and political channels. Skeptical of violence, "
            "but not naive about power."
        ),
        "notable_npcs": [],  # Not detailed in source
        "source": "cbrpnk_05_weird.pdf",
    },

    "The Elder": {
        "setting": "the_sprawl",
        "type": "Singular Entity / Faction",
        "tier": 5,
        "sector": "Unknown / Weird",
        "security_level": 5,
        "description": (
            "A dragon of iridescent scales. Ancient, inscrutable, and operating "
            "on timescales the Runners barely register. Whether The Elder is a "
            "faction, a phenomenon, or something else entirely is left to the table."
        ),
        "notable_npcs": [
            {
                "name": "The Elder",
                "role": "Dragon",
                "note": "Iridescent scales; motivations unknown.",
            }
        ],
        "source": "cbrpnk_05_weird.pdf",
    },

    "The Shadow Method": {
        "setting": "the_sprawl",
        "type": "Underground Collective",
        "tier": 2,
        "sector": "Hacktivist / Skeptic",
        "security_level": 2,
        "description": (
            "A skeptical collective of hacktivists who distrust the 'Weird' — "
            "meta-talents, spirits, and eldritch powers — and work to expose "
            "what they believe is corporate exploitation or mass delusion. "
            "Methodical, skeptical, and technically competent."
        ),
        "notable_npcs": [],  # Not detailed in source
        "source": "cbrpnk_05_weird.pdf",
    },

    # ------------------------------------------------------------------
    # SOURCE: cbrpnk_04_prdtr.pdf — Ganymede / Biosphere-5 factions
    # ------------------------------------------------------------------

    "Insurgents": {
        "setting": "the_sprawl",
        "type": "Armed Resistance",
        "tier": 2,
        "sector": "Anti-Corporate / Military",
        "security_level": 2,
        "description": (
            "A resistance cell operating against Corporate Security (APX) "
            "inside Biosphere-5 on Ganymede. Led in the field by Eli. "
            "Outgunned but motivated."
        ),
        "notable_npcs": [
            {
                "name": "Eli",
                "role": "Insurgent Leader",
                "note": "Field commander; true name unknown.",
            }
        ],
        "location": "Biosphere-5, Ganymede",
        "source": "cbrpnk_04_prdtr.pdf",
    },

    "Corporate Security (APX)": {
        "setting": "the_sprawl",
        "type": "Corporate Paramilitary",
        "tier": 3,
        "sector": "Security / Military",
        "security_level": 4,
        "description": (
            "The corporate security apparatus enforcing APX's control over "
            "Biosphere-5 on Ganymede. Led by Sarge Heinlein. "
            "Well-equipped, ruthless, operating under legal cover."
        ),
        "notable_npcs": [
            {
                "name": "Sarge Heinlein",
                "role": "Corp Sec Commander",
                "note": "Enforcer of APX corporate interests on Ganymede.",
            }
        ],
        "location": "Biosphere-5, Ganymede",
        "source": "cbrpnk_04_prdtr.pdf",
    },

    "Scavengers": {
        "setting": "the_sprawl",
        "type": "Autonomous Gang / Survivalists",
        "tier": 1,
        "sector": "Salvage / Black Market",
        "security_level": 1,
        "description": (
            "Unaffiliated operators surviving in the margins of Biosphere-5 "
            "on Ganymede by scavenging corporate hardware, trading salvage, "
            "and staying out of the Corp vs. Insurgent conflict when possible. "
            "When not possible, they sell to whoever pays."
        ),
        "notable_npcs": [
            {
                "name": "Old Finn",
                "role": "Hustler / Fixer",
                "note": "Key contact for scavenged goods and local intelligence.",
            }
        ],
        "location": "Biosphere-5, Ganymede",
        "source": "cbrpnk_04_prdtr.pdf",
    },
}


# Backward-compatibility alias — existing code importing CORPORATIONS still works.
CORPORATIONS: Dict[str, Dict[str, Any]] = FACTIONS


__all__ = ["FACTIONS", "CORPORATIONS"]

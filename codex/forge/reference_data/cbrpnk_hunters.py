"""
codex.forge.reference_data.cbrpnk_hunters
==========================================
Cyberpunk Hunters plugin reference data for CBR+PNK.

SOURCE: CYBERPUNK_HUNTERS.pdf

The Hunters plugin introduces escalating pursuit mechanics where failed
runs at high Threat Level cause a specialized Hunter to be deployed
against the crew. Hunters have three Ranks — each harder to defeat.

Covers:
  - PREMADE_HUNTERS: 6 named hunters with full rank/trait/aug/ability data
  - HUNTER_ACTIVATION_RULES: How and when hunters enter play
  - HUNTER_BUILDING_RULES: GM guidance for custom hunter creation
"""

from typing import Any, Dict, List


# =========================================================================
# PREMADE HUNTERS
# SOURCE: CYBERPUNK_HUNTERS.pdf
# Each hunter has: augmentation, special ability, and 3 ranks.
# Each rank unlocks new traits. Rank 3 upgrades the core ability.
# =========================================================================

PREMADE_HUNTERS: Dict[str, Dict[str, Any]] = {
    "Stalker": {
        "setting": "the_sprawl",
        "description": (
            "A stealth assassin built for patient elimination. "
            "The Stalker approaches through darkness and silence, "
            "striking from ambush with lethal precision."
        ),
        "role": "Stealth assassin",
        "augmentation": {
            "name": "EZ-10 Prowler System",
            "description": "Full-spectrum stealth augmentation suite — thermal masking, sound dampening, EM suppression.",
        },
        "special_ability": {
            "name": "Deadly Ambush",
            "description": "Harm inflicted from ambush is increased by +1 level.",
        },
        "ranks": {
            1: {
                "description": "Initial deployment — tracking and preparation phase.",
                "traits": ["Athletics", "[Redacted]", "Decoys"],
                "notes": "One trait is deliberately withheld from Runners until used.",
            },
            2: {
                "description": "Active pursuit — the Stalker is closing in.",
                "traits": ["Stealthy", "Smart", "Killbox"],
                "notes": "Killbox means the Stalker has prepared the terrain for the kill.",
            },
            3: {
                "description": "Endgame — the Stalker is in position and ready.",
                "ability_upgrade": "Harm from ambush is increased by +2 levels.",
                "notes": "At Rank 3, the Stalker's ability becomes devastating.",
            },
        },
        "source": "CYBERPUNK_HUNTERS.pdf",
    },

    "Saboteur": {
        "setting": "the_sprawl",
        "description": (
            "A debuffer and disruptor who systematically dismantles "
            "the crew's tools, chrome, and tactical options before "
            "delivering the finishing blow."
        ),
        "role": "Debuffer / equipment disabler",
        "augmentation": {
            "name": "R.N.N. Drone Swarm",
            "description": "A swarm of micro-drones capable of targeted electronic disruption and reconnaissance.",
        },
        "special_ability": {
            "name": "System Overload",
            "description": "DISABLE 1 piece of Gear or Augmentation per use.",
        },
        "ranks": {
            1: {
                "description": "Initial deployment — intelligence gathering and first disruptions.",
                "traits": ["Coding", "Rigging", "Disruptors"],
                "notes": "Begins stripping the crew's advantages from the edges.",
            },
            2: {
                "description": "Active campaign — multiple systems being targeted.",
                "traits": ["Smart", "Aggressive", "Firewall"],
                "notes": "Firewall means the Saboteur protects its own systems while attacking.",
            },
            3: {
                "description": "Endgame — systematic demolition of crew capability.",
                "ability_upgrade": "DISABLE 2 pieces of Gear or Augmentations per use.",
                "notes": "At Rank 3, the Saboteur can cripple a Runner in a single engagement.",
            },
        },
        "source": "CYBERPUNK_HUNTERS.pdf",
    },

    "Commando": {
        "setting": "the_sprawl",
        "description": (
            "A one-person army who closes distance and never stops. "
            "The Commando doesn't care about subtlety — it cares about "
            "getting there and not going down."
        ),
        "role": "One-person army / sustained assault",
        "augmentation": {
            "name": "H.9UND Exoskeleton",
            "description": "Military-grade powered exoskeleton providing enhanced strength, armor, and carrying capacity.",
        },
        "special_ability": {
            "name": "Relentless",
            "description": "Recover 1 segment of its Counter Track when triggered.",
        },
        "ranks": {
            1: {
                "description": "Initial deployment — direct engagement begins.",
                "traits": ["Close Combat", "Ranged Combat", "Combat Surge"],
                "notes": "The Commando hits from multiple vectors simultaneously.",
            },
            2: {
                "description": "Sustained pressure — the Commando adapts.",
                "traits": ["Aggressive", "Empathic", "Bulwark"],
                "notes": (
                    "Empathic means it reads the crew's tactics. "
                    "Bulwark means it's hardening its defensive posture."
                ),
            },
            3: {
                "description": "Endgame — the Commando is at full capability.",
                "ability_upgrade": "Recover 2 segments of its Counter Track when triggered.",
                "notes": "At Rank 3, conventional attrition strategies won't work.",
            },
        },
        "source": "CYBERPUNK_HUNTERS.pdf",
    },

    "The Faceless": {
        "setting": "the_sprawl",
        "description": (
            "A social chameleon spy who infiltrates the crew's network, "
            "poisons their relationships, and strikes from inside "
            "their trusted circle. "
            "By the time they know they've been compromised, it's too late."
        ),
        "role": "Social chameleon / spy",
        "augmentation": {
            "name": "L/DZ Shadow Network",
            "description": "A covert social and information network providing real-time intelligence on targets and contacts.",
        },
        "special_ability": {
            "name": "A Million Faces",
            "description": "Unknown characters gain +1 die when acting against the crew.",
        },
        "ranks": {
            1: {
                "description": "Initial infiltration — the Faceless is learning the crew.",
                "traits": ["Influence", "Analyze", "Chameleons"],
                "notes": "Chameleons means assets are being placed near the crew.",
            },
            2: {
                "description": "Active manipulation — the Faceless is inside the crew's world.",
                "traits": ["Empathic", "Stealthy", "Whispers"],
                "notes": "Whispers means disinformation is spreading through crew contacts.",
            },
            3: {
                "description": "Endgame — the Faceless has complete situational awareness.",
                "ability_upgrade": "Unknown characters gain +2 dice when acting against the crew.",
                "notes": "At Rank 3, nearly everyone around the crew could be the Faceless.",
            },
        },
        "source": "CYBERPUNK_HUNTERS.pdf",
    },

    "Warbot": {
        "setting": "the_sprawl",
        "description": (
            "A murder machine. The Warbot does not have tactics — "
            "it has munitions and the will to expend them. "
            "Every engagement with a Warbot is a battle of attrition "
            "the crew cannot afford."
        ),
        "role": "Heavy weapons platform / area denial",
        "augmentation": {
            "name": "MUR/H. Weapons Rigging",
            "description": "Full-body integrated weapons mount supporting multiple simultaneous weapon systems.",
        },
        "special_ability": {
            "name": "Suppressive Fire",
            "description": (
                "Each Consequence the Warbot triggers fires twice. "
                "One of those Consequences is automatically Level 1 Harm."
            ),
        },
        "ranks": {
            1: {
                "description": "Initial deployment — the Warbot establishes a kill zone.",
                "traits": ["Piloting", "Sciences", "Multicore AI"],
                "notes": "Multicore AI means the Warbot processes multiple threats simultaneously.",
            },
            2: {
                "description": "Active assault — the kill zone is moving.",
                "traits": ["Aggressive", "Stealthy", "Forbidden Tech"],
                "notes": "Forbidden Tech means the Warbot carries illegal weapons.",
            },
            3: {
                "description": "Endgame — the Warbot is at full operational capacity.",
                "ability_upgrade": "Each Consequence triggers three times instead of twice.",
                "notes": "At Rank 3, a single failed roll can cascade catastrophically.",
            },
        },
        "source": "CYBERPUNK_HUNTERS.pdf",
    },

    "The Boss": {
        "setting": "the_sprawl",
        "description": (
            "A criminal leader who brings overwhelming social and logistical "
            "force to bear. The Boss doesn't fight — it directs. "
            "And everything it directs is aimed at making the crew's "
            "existence unsustainable."
        ),
        "role": "Criminal leader / resource coordinator",
        "augmentation": {
            "name": "N4U-1 Comms Relay",
            "description": "Encrypted command-and-control relay system for real-time coordination of assets and personnel.",
        },
        "special_ability": {
            "name": "Overwhelming Presence",
            "description": "SET UP, ASSIST, and LEAD GROUP actions taken against the crew gain +1 die.",
        },
        "ranks": {
            1: {
                "description": "Initial deployment — the Boss is organizing its response.",
                "traits": ["Streetwise", "Influence", "Hired Muscle"],
                "notes": "Hired Muscle means the Boss has contracted additional operatives.",
            },
            2: {
                "description": "Active campaign — the Boss is tightening the net.",
                "traits": ["Smart", "Empathic", "Elite Squad"],
                "notes": "Elite Squad means the contracted operatives are high-quality.",
            },
            3: {
                "description": "Endgame — the Boss has fully committed its network.",
                "ability_upgrade": (
                    "SET UP, ASSIST, and LEAD GROUP actions gain +1 die AND "
                    "the crew's opposing actions lose 1 die."
                ),
                "notes": "At Rank 3, the Boss's coordination actively degrades crew performance.",
            },
        },
        "source": "CYBERPUNK_HUNTERS.pdf",
    },
}


# =========================================================================
# HUNTER ACTIVATION RULES
# SOURCE: CYBERPUNK_HUNTERS.pdf
# =========================================================================

HUNTER_ACTIVATION_RULES: Dict[str, Any] = {
    "trigger": (
        "When the crew fails a roll at Threat Level 3, they become HUNTED. "
        "A Hunter is then deployed against them."
    ),
    "threat_level_required": 3,
    "hunted_status": "HUNTED",
    "rank_determination": {
        "method": "Roll 1d6",
        "table": {
            "1-3": "Rank 1 Hunter — initial deployment",
            "4-5": "Rank 2 Hunter — experienced threat",
            "6": "Rank 3 Hunter — elite assassin deployed immediately",
        },
    },
    "counter_track": (
        "Each Hunter has a Counter Track. When the track is filled, "
        "the Hunter is defeated. The track size scales with Rank."
    ),
    "escalation": (
        "If the crew fails to defeat a Hunter within a set number of runs, "
        "the Hunter may escalate to the next Rank."
    ),
    "multiple_hunters": (
        "A crew can theoretically be targeted by multiple Hunters simultaneously "
        "if they have triggered multiple factions. Each Hunter tracks independently."
    ),
}


# =========================================================================
# HUNTER BUILDING RULES (GM Guidance)
# SOURCE: CYBERPUNK_HUNTERS.pdf
# =========================================================================

HUNTER_BUILDING_RULES: Dict[str, Any] = {
    "description": (
        "GMs can create custom Hunters for specific campaign needs. "
        "Each Hunter requires the following elements."
    ),
    "required_elements": [
        "A name and role (what kind of threat is this?)",
        "An Augmentation (the Hunter's key piece of chrome)",
        "A Special Ability (unique mechanical effect, usable at Rank 1+)",
        "Rank 1 Traits (3 traits — one can be [Redacted])",
        "Rank 2 Traits (3 traits — more powerful or specialized)",
        "Rank 3 Ability Upgrade (enhanced version of the Special Ability)",
        "A Counter Track size (how hard is the Hunter to defeat?)",
    ],
    "trait_guidance": (
        "Traits describe what the Hunter can do beyond its base capability. "
        "Good traits are evocative nouns or adjectives: 'Aggressive', 'Networked', "
        "'Firewall', 'Elite Squad'. They describe capability, not mechanics."
    ),
    "ability_guidance": (
        "Special Abilities should have concrete mechanical effects. "
        "Use clear action language: DISABLE, RECOVER, TRIGGER, ADD DICE. "
        "Rank 3 upgrades scale the existing ability rather than replacing it."
    ),
    "counter_track_guidance": {
        "Rank 1": "4-6 segment Counter Track",
        "Rank 2": "6-8 segment Counter Track",
        "Rank 3": "8-10 segment Counter Track",
    },
}


__all__ = [
    "PREMADE_HUNTERS",
    "HUNTER_ACTIVATION_RULES",
    "HUNTER_BUILDING_RULES",
]

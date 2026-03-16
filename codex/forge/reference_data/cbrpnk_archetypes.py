"""
codex.forge.reference_data.cbrpnk_archetypes
=============================================
CBR+PNK archetype and background reference data.

SOURCE: creation_rules.json (vault/FITD/CBR_PNK/creation_rules.json)
SOURCE: cbrpnk_03_framework.pdf (Core Rules)

4 Archetypes: Hacker, Punk, Fixer, Ghost
4 Backgrounds: Corporate Exile, Street Born, Colony Transplant, Synthetic
4 Vices: Stimulants, Virtu, Rebellion, Connection
3 Attributes: Insight, Prowess, Resolve
8 Actions (not 12 — the CBRPNKCharacter class has extra dots that don't
correspond to real system actions; that is a separate task to reconcile)
"""

from typing import Dict, Any, List


# =========================================================================
# ARCHETYPES
# SOURCE: creation_rules.json
# =========================================================================

ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "Hacker": {
        "setting": "the_sprawl",
        "description": (
            "A digital infiltrator who navigates the GRID like a ghost. "
            "Hackers jack into corporate networks, crack ICE, extract data, "
            "and wreak havoc on infrastructure — all from the shadows of a "
            "safe house or the chaos of a live firefight."
        ),
        # NOTE: Full special abilities are in cbrpnk_02 (Runner File, not yet available).
        # Abilities below are derived from archetype role. Marked EXPANDED.
        "special_abilities": [
            {
                "name": "Ghost Signal",
                # EXPANDED: not in source PDF — derived from archetype role
                "description": (
                    "Your intrusion signature is scrambled. When you jack in "
                    "cleanly, reduce alarm escalation by 1 on your first move."
                ),
            },
            {
                "name": "Neural Override",
                # EXPANDED: not in source PDF — derived from archetype role
                "description": (
                    "Push your GRID connection to the limit. Take 1 stress to "
                    "roll an extra die on any Hack action this scene."
                ),
            },
        ],
        "starting_chrome": ["Neural Jack"],  # EXPANDED
        "starting_items": [
            "Deck (hacking rig)",
            "Encrypted data chip x3",
            "Subvocal mic",
        ],
        "attribute_emphasis": "Insight",
        "xp_trigger": (
            "You successfully extracted data or disrupted a corporate system."
        ),
    },

    "Punk": {
        "setting": "the_sprawl",
        "description": (
            "Angry, loud, and deliberate about it. Punks are survivors who "
            "turned survival into a philosophy. They push back against corporate "
            "control through action, art, and organized defiance — and they're "
            "harder to put down than anyone expects."
        ),
        # EXPANDED: not in source PDF — derived from archetype role
        "special_abilities": [
            {
                "name": "Street Cred",
                # EXPANDED: not in source PDF
                "description": (
                    "Your reputation precedes you in the right circles. "
                    "When you need help from street-level contacts, they "
                    "answer — no negotiation required."
                ),
            },
            {
                "name": "Bloody-Minded",
                # EXPANDED: not in source PDF
                "description": (
                    "You keep going when others quit. Once per session, clear "
                    "1 harm through sheer refusal to stop."
                ),
            },
        ],
        "starting_chrome": [],  # EXPANDED — Punks often resist augmentation
        "starting_items": [
            "Makeshift weapon",
            "Spray cans (tagging kit)",
            "Burner comm",
        ],
        "attribute_emphasis": "Resolve",
        "xp_trigger": (
            "You acted against corporate or authoritarian interests in a meaningful way."
        ),
    },

    "Fixer": {
        "setting": "the_sprawl",
        "description": (
            "The miracle worker who knows everyone and owes everyone. "
            "Fixers are the glue of the SPRAWL's grey economy — brokers, "
            "connectors, and operators who turn impossible jobs into "
            "profitable outcomes through cunning and social capital."
        ),
        # EXPANDED: not in source PDF — derived from archetype role
        "special_abilities": [
            {
                "name": "The Right Contact",
                # EXPANDED: not in source PDF
                "description": (
                    "You always know a person. Once per session, establish "
                    "a contact in a relevant field without a prior roll — "
                    "they exist because you say they do."
                ),
            },
            {
                "name": "Cut a Deal",
                # EXPANDED: not in source PDF
                "description": (
                    "After a run, negotiate a better payout. Roll Consort; "
                    "on a success, increase the crew's take by one tier."
                ),
            },
        ],
        "starting_chrome": ["Voice Modulator"],  # EXPANDED
        "starting_items": [
            "Burner comm x2",
            "Fake SIN",
            "Credchip (loaded)",
        ],
        "attribute_emphasis": "Resolve",
        "xp_trigger": (
            "You negotiated a deal, brokered information, or avoided violence through cunning."
        ),
    },

    "Ghost": {
        "setting": "the_sprawl",
        "description": (
            "You were never here. Ghosts are specialists in absence — "
            "moving through spaces without leaving traces, eliminating "
            "targets without announcements, and vanishing before the "
            "corps even know a run happened."
        ),
        # EXPANDED: not in source PDF — derived from archetype role
        "special_abilities": [
            {
                "name": "No Trace",
                # EXPANDED: not in source PDF
                "description": (
                    "When you exit a location cleanly, you leave no evidence "
                    "of your presence. Reduce heat generated from the run by 1."
                ),
            },
            {
                "name": "Deadly Patience",
                # EXPANDED: not in source PDF
                "description": (
                    "You can hold position indefinitely. When you strike from "
                    "an established hidden position, treat effect as one level higher."
                ),
            },
        ],
        "starting_chrome": ["Ghost Module"],  # EXPANDED
        "starting_items": [
            "Suppressed sidearm",
            "Infiltration kit",
            "Trauma kit",
        ],
        "attribute_emphasis": "Prowess",
        "xp_trigger": (
            "You completed an objective without being detected or identified."
        ),
    },
}


# =========================================================================
# BACKGROUNDS
# SOURCE: creation_rules.json
# =========================================================================

BACKGROUNDS: Dict[str, Dict[str, Any]] = {
    "Corporate Exile": {
        "setting": "the_sprawl",
        "description": (
            "You used to wear a badge. Whether you burned out, got pushed out, "
            "or walked away with company secrets, you know how the corps operate "
            "from the inside. That knowledge is worth more than any street rep."
        ),
        "starting_contacts": [
            "Former colleague (corporate insider)",
            "HR fixer (covers paper trails)",
        ],
        "bonus_action": "Consort",
        "starting_heat": 1,
        "narrative_hook": (
            "A corp you used to work for wants something from you — "
            "or wants you silenced."
        ),
    },

    "Street Born": {
        "setting": "the_sprawl",
        "description": (
            "You grew up in the cracks between the megablock towers, where "
            "survival meant reading people fast and moving faster. The street "
            "made you hard, but it also made you connected in ways corp kids never are."
        ),
        "starting_contacts": [
            "Neighborhood fixer",
            "Gang lieutenant (neutral terms)",
        ],
        "bonus_action": "Prowl",
        "starting_heat": 0,
        "narrative_hook": (
            "Someone from your past needs help — or needs to disappear."
        ),
    },

    "Colony Transplant": {
        "setting": "the_sprawl",
        "description": (
            "You came from off-world or an outer colony — Ganymede, Mars, "
            "an orbital platform. The SPRAWL is overwhelming and alien, but "
            "you carry skills and perspectives that Earth-born runners don't have."
        ),
        "starting_contacts": [
            "Colony liaison (handles off-world logistics)",
            "Black market importer (colony-grade tech)",
        ],
        "bonus_action": "Tinker",
        "starting_heat": 0,
        "narrative_hook": (
            "Something that happened in the colony followed you here — "
            "a debt, a vendetta, or a secret."
        ),
    },

    "Synthetic": {
        "setting": "the_sprawl",
        "description": (
            "You are artificial — whether fully synthetic, heavily augmented "
            "beyond human baseline, or something in between. Corps regard you "
            "as property. The street regards you with unease. You regard "
            "both with clear eyes."
        ),
        "starting_contacts": [
            "Underground synthetics rights advocate",
            "Back-alley technician (repairs, no questions)",
        ],
        "bonus_action": "Hack",
        "starting_heat": 0,
        "narrative_hook": (
            "Your origin — who made you, why, and for what purpose — "
            "is the question that shapes everything."
        ),
    },
}


# =========================================================================
# VICES
# SOURCE: creation_rules.json
# =========================================================================

VICES: Dict[str, str] = {
    "Stimulants": (
        "Chemical performance enhancers, uppers, nootropics, combat drugs. "
        "You indulge to sharpen the edge — and because the alternative is "
        "feeling everything."
    ),
    "Virtu": (
        "Full-immersion GRID entertainment — games, fantasies, simulated worlds. "
        "Virtu addicts spend more time in the digital than the physical. "
        "The colors are better there."
    ),
    "Rebellion": (
        "Sabotage, direct action, protest, causing problems for the powerful. "
        "You indulge your vice by fighting the system — but sometimes the "
        "fight becomes an end in itself."
    ),
    "Connection": (
        "Intimacy, belonging, loyalty to a person or community. "
        "In a world that commodifies everything, genuine connection is both "
        "rare and dangerous."
    ),
}


# =========================================================================
# ATTRIBUTES & ACTIONS
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

ATTRIBUTES: Dict[str, Dict[str, Any]] = {
    "Insight": {
        "description": (
            "Mental acuity, technical knowledge, and perception. "
            "Used for understanding systems, gathering information, and "
            "interfacing with technology."
        ),
        "actions": ["Hack", "Study", "Survey"],
    },
    "Prowess": {
        "description": (
            "Physical capability, dexterity, and hands-on skill. "
            "Used for athletic feats, combat, and technical manipulation."
        ),
        "actions": ["Prowl", "Skirmish", "Tinker"],
    },
    "Resolve": {
        "description": (
            "Social force, willpower, and interpersonal influence. "
            "Used for persuasion, manipulation, and commanding presence."
        ),
        "actions": ["Consort", "Sway"],
    },
}

ACTIONS: Dict[str, Dict[str, str]] = {
    # Insight actions
    "Hack": {
        "attribute": "Insight",
        "description": (
            "Interface with systems, crack ICE, extract or corrupt data, "
            "and move through the GRID. The core action for GRID operations."
        ),
    },
    "Study": {
        "attribute": "Insight",
        "description": (
            "Gather information through research, observation, and analysis. "
            "Understand people, situations, and technical problems."
        ),
    },
    "Survey": {
        "attribute": "Insight",
        "description": (
            "Assess a location, situation, or group at a distance. "
            "Read the room, spot threats, map escape routes."
        ),
    },
    # Prowess actions
    "Prowl": {
        "attribute": "Prowess",
        "description": (
            "Move without being detected, infiltrate locations, "
            "shadow targets, and operate in stealth."
        ),
    },
    "Skirmish": {
        "attribute": "Prowess",
        "description": (
            "Engage in direct physical conflict — fighting, subduing, "
            "defending. The primary combat action."
        ),
    },
    "Tinker": {
        "attribute": "Prowess",
        "description": (
            "Create, repair, modify, or sabotage physical equipment. "
            "Applies to weapons, chrome, vehicles, and hardware."
        ),
    },
    # Resolve actions
    "Consort": {
        "attribute": "Resolve",
        "description": (
            "Cultivate relationships, gather intelligence through social "
            "networks, and leverage existing connections."
        ),
    },
    "Sway": {
        "attribute": "Resolve",
        "description": (
            "Influence, persuade, intimidate, or deceive. "
            "Change what someone believes, feels, or will do."
        ),
    },
}


# =========================================================================
# ENGAGEMENT PLANS
# SOURCE: cbrpnk_01_gm-guide.pdf
# =========================================================================

ENGAGEMENT_PLANS: Dict[str, str] = {
    "Assault": (
        "Go in hard and fast. Direct, forceful entry. "
        "High heat potential; low subtlety. Best when time is short "
        "and the crew has firepower."
    ),
    "Deception": (
        "Infiltrate through false identity, misdirection, or planted "
        "information. Requires preparation and good intelligence. "
        "Failure means blown cover with no easy exit."
    ),
    "Stealth": (
        "Move through the objective unseen and unheard. "
        "The quietest option — no engagement, no witnesses. "
        "Success depends on preparation and patience."
    ),
    "Social": (
        "Gain access or extract the objective through legitimate-looking "
        "social means: invitations, bribes, seduction, negotiation. "
        "Works best with a Face or Fixer."
    ),
    "Transport": (
        "The objective is mobile — extract a person, intercept a convoy, "
        "or smuggle something through checkpoints. "
        "Logistics and timing are everything."
    ),
}


__all__ = [
    "ARCHETYPES",
    "BACKGROUNDS",
    "VICES",
    "ATTRIBUTES",
    "ACTIONS",
    "ENGAGEMENT_PLANS",
]

"""
codex.forge.reference_data.crown_factions
==========================================
Political faction definitions for Crown & Crew.

Each faction has influence (0-10), territory, resources, ideology,
political goals, and event triggers. Relationships between factions
are encoded in FACTION_RELATIONSHIPS.

Influence scale:
    0-2  : Marginal (whisper campaigns, minor disruption)
    3-5  : Competitive (can swing votes, holds visible territory)
    6-8  : Dominant (controls institutions, sets agendas)
    9-10 : Hegemonic (effectively the only voice in a domain)
"""

from typing import Dict, Any, List

# =============================================================================
# FACTIONS
# =============================================================================

FACTIONS: Dict[str, Dict[str, Any]] = {
    "Crown Loyalists": {
        "description": (
            "The traditional power structure — nobles, senior military officers, "
            "and senior clergy who have prospered under the current regime and "
            "have every reason to preserve it."
        ),
        "ideology": "Order through hierarchy; the Crown's authority is divinely sanctioned and historically proven",
        "influence": 8,
        "territory": ["Palace Quarter", "Military Garrison", "High Court District"],
        "leader_name": "The High Inquisitor",
        "resources": {
            "gold": 9,
            "soldiers": 8,
            "spies": 6,
            "influence": 8,
        },
        "agenda": [
            "Maintain the King's absolute authority over provincial governors",
            "Suppress the Crew's network and make public example of captured members",
            "Pass the Sedition Act to criminalize association with any rebel organization",
        ],
        "allies": ["Temple Authority"],
        "enemies": ["People's Assembly", "Free Companies", "Reformists"],
        "events": [
            {
                "text": "Crown Loyalists have posted new warrants. The bounty on Crew leadership has doubled.",
                "bias": "crown", "tag": "GUILE",
            },
            {
                "text": "Loyalist nobles have voted to fund a second garrison. Construction begins at the eastern gate.",
                "bias": "crown", "tag": "BLOOD",
            },
        ],
    },
    "People's Assembly": {
        "description": (
            "A loose coalition of dockworkers, guild artisans, minor clergy, "
            "and displaced smallholders who want representation in the decisions "
            "that govern their lives. Organizationally chaotic, politically passionate."
        ),
        "ideology": "Governance by and for the governed; taxation without representation is theft",
        "influence": 4,
        "territory": ["Docklands", "Grain District", "Outer Wards"],
        "leader_name": "The Faceless",
        "resources": {
            "gold": 2,
            "soldiers": 3,
            "spies": 2,
            "influence": 5,
        },
        "agenda": [
            "Establish an elected council with binding authority over tax rates",
            "Repeal the Sedition Act (or prevent its passage)",
            "Secure legal recognition of the dock workers' guild",
        ],
        "allies": ["Free Companies", "Reformists"],
        "enemies": ["Crown Loyalists", "Old Blood"],
        "events": [
            {
                "text": "The Assembly has called a general strike. Three major supply routes are disrupted.",
                "bias": "crew", "tag": "DEFIANCE",
            },
            {
                "text": "Assembly leaders have been arrested. Their trial is scheduled for the Breach day.",
                "bias": "neutral", "tag": "BLOOD",
            },
        ],
    },
    "Merchant Guild": {
        "description": (
            "The city's commercial class, united by profit motive and divided by "
            "everything else. They will back whoever makes trade predictable. "
            "Currently Crown-adjacent, but the relationship is transactional."
        ),
        "ideology": "Stable markets above all; political order is a means to commercial ends",
        "influence": 6,
        "territory": ["Market Quarter", "Harbor Exchange", "Counting Houses"],
        "leader_name": "The Merchant Prince",
        "resources": {
            "gold": 8,
            "soldiers": 1,
            "spies": 4,
            "influence": 6,
        },
        "agenda": [
            "Secure favorable trade terms and low tariff rates from whoever wins",
            "Maintain control of the harbor exchange regardless of political outcome",
            "Acquire or neutralize the Crew's smuggling operations (preferably acquire)",
        ],
        "allies": ["Crown Loyalists", "Shadow Court"],
        "enemies": ["People's Assembly"],
        "events": [
            {
                "text": "The Guild has frozen credit to the Crown garrison. The soldiers haven't been paid in six weeks.",
                "bias": "crew", "tag": "GUILE",
            },
            {
                "text": "A Merchant Guild convoy has hired Crew escorts. Someone is testing the waters.",
                "bias": "neutral", "tag": "HEARTH",
            },
        ],
    },
    "Shadow Court": {
        "description": (
            "The criminal underworld organized into something approaching "
            "an institution. They run the city's gambling, protection, "
            "and information brokerage operations. Officially, they don't exist."
        ),
        "ideology": "Power is real; law is opinion; everyone has a price",
        "influence": 5,
        "territory": ["Undercroft", "Night Market", "Sewer Passages"],
        "leader_name": "The Spymaster",
        "resources": {
            "gold": 6,
            "soldiers": 4,
            "spies": 9,
            "influence": 5,
        },
        "agenda": [
            "Maintain operational independence from both Crown and Crew",
            "Expand the information brokerage to include military intelligence",
            "Ensure whoever wins owes the Shadow Court a favor",
        ],
        "allies": ["Merchant Guild"],
        "enemies": ["Temple Authority"],
        "events": [
            {
                "text": "The Shadow Court is selling information to both sides. A third party is now in the bidding.",
                "bias": "neutral", "tag": "GUILE",
            },
            {
                "text": "A Shadow Court safe house has been raided — by the Crew, not the Crown. Tensions are rising.",
                "bias": "crown", "tag": "BLOOD",
            },
        ],
    },
    "Temple Authority": {
        "description": (
            "The established religious hierarchy that runs the city's hospitals, "
            "schools, and granaries. They hold genuine popular legitimacy and "
            "are prepared to use it as political leverage."
        ),
        "ideology": "The sacred compact between rulers and ruled is mediated by the Temple; both sides answer to the divine",
        "influence": 7,
        "territory": ["Temple Precinct", "Almshouses", "Hospital Wards"],
        "leader_name": "The High Priestess",
        "resources": {
            "gold": 5,
            "soldiers": 2,
            "spies": 3,
            "influence": 8,
        },
        "agenda": [
            "Negotiate the Concordat — Temple legal immunity from Crown prosecution",
            "Maintain Temple control of hospitals and food distribution regardless of political outcome",
            "Prevent either side from committing atrocities that would require the Temple to publicly condemn them",
        ],
        "allies": ["Crown Loyalists", "Reformists"],
        "enemies": ["Shadow Court"],
        "events": [
            {
                "text": "The Temple has opened its granaries to the Outer Wards. The Crew gets the credit in the streets.",
                "bias": "crew", "tag": "HEARTH",
            },
            {
                "text": "The High Priestess has issued a conditional condemnation of the Crew. She left the door open.",
                "bias": "crown", "tag": "SILENCE",
            },
        ],
    },
    "Free Companies": {
        "description": (
            "Mercenary soldiers, disbanded veterans, and private military "
            "contractors who sell organized violence to the highest bidder. "
            "Currently the Crew's most reliable martial resource."
        ),
        "ideology": "Professional competence is the only virtue; politics are someone else's problem",
        "influence": 3,
        "territory": ["Barracks District", "Road Inns", "Border Outposts"],
        "leader_name": "The Mercenary",
        "resources": {
            "gold": 3,
            "soldiers": 7,
            "spies": 2,
            "influence": 3,
        },
        "agenda": [
            "Secure long-term contracts with whoever wins — the war must keep going long enough to be profitable",
            "Maintain legal amnesty for Free Company soldiers regardless of which flags they've previously served",
            "Block Crown monopolization of military force (personal interest)",
        ],
        "allies": ["People's Assembly"],
        "enemies": ["Crown Loyalists"],
        "events": [
            {
                "text": "Three Free Companies have been offered Crown commissions. They're asking the Crew to match the terms.",
                "bias": "neutral", "tag": "BLOOD",
            },
            {
                "text": "Free Company veterans have occupied a Crown checkpoint and are charging 'toll road fees.' They say it's legal.",
                "bias": "crew", "tag": "DEFIANCE",
            },
        ],
    },
    "Old Blood": {
        "description": (
            "Ancient noble families whose power predates the current Crown. "
            "They view the King as an upstart and the Crew as a useful tool "
            "for weakening him — after which they expect to reclaim ancestral authority."
        ),
        "ideology": "Legitimacy flows from bloodline and tradition; the current regime is an interruption of proper order",
        "influence": 4,
        "territory": ["Old City Walls", "Estate Districts", "Ancestral Seats"],
        "leader_name": "Lady Miren",
        "resources": {
            "gold": 7,
            "soldiers": 3,
            "spies": 4,
            "influence": 4,
        },
        "agenda": [
            "Restore ancestral titles and lands stripped during the Succession War",
            "Weaken the Crown's centralized authority to restore traditional noble autonomy",
            "Ensure the Crew does not replace one centralized authority with another",
        ],
        "allies": [],
        "enemies": ["Crown Loyalists", "People's Assembly"],
        "events": [
            {
                "text": "Old Blood lawyers have filed a writ challenging the Crown's seizure of three noble estates. The court date is set.",
                "bias": "neutral", "tag": "GUILE",
            },
            {
                "text": "An Old Blood lord has quietly offered the Crew use of his estate for a staging point. The price is unspecified.",
                "bias": "crew", "tag": "HEARTH",
            },
        ],
    },
    "Reformists": {
        "description": (
            "An ideologically committed movement that wants neither Crown absolutism "
            "nor revolutionary chaos — they believe the existing institutions can be "
            "reformed from within if the right people are in the right positions."
        ),
        "ideology": "Systemic change through legal process; revolution eats its own children",
        "influence": 3,
        "territory": ["University Quarter", "Press District", "Reform Clubs"],
        "leader_name": "The Justiciar",
        "resources": {
            "gold": 2,
            "soldiers": 0,
            "spies": 3,
            "influence": 4,
        },
        "agenda": [
            "Pass constitutional limits on Crown executive authority through legal challenge",
            "Establish an independent judiciary protected from political interference",
            "Achieve Crew amnesty through legal mechanism rather than military victory",
        ],
        "allies": ["People's Assembly", "Temple Authority"],
        "enemies": ["Crown Loyalists"],
        "events": [
            {
                "text": "Reformist pamphlets are circulating openly. The Crown has not moved to suppress them — yet.",
                "bias": "neutral", "tag": "DEFIANCE",
            },
            {
                "text": "The Justiciar has ruled that three Crown arrests were unlawful. The released prisoners are looking for work.",
                "bias": "crew", "tag": "GUILE",
            },
        ],
    },
}

# =============================================================================
# FACTION RELATIONSHIPS — Pre-Built Relationship Matrix
# =============================================================================
# Values: "alliance" / "rivalry" / "neutral" / "tension"

FACTION_RELATIONSHIPS: Dict[str, Dict[str, str]] = {
    "Crown Loyalists": {
        "People's Assembly": "rivalry",
        "Merchant Guild": "tension",
        "Shadow Court": "tension",
        "Temple Authority": "alliance",
        "Free Companies": "rivalry",
        "Old Blood": "tension",
        "Reformists": "rivalry",
    },
    "People's Assembly": {
        "Crown Loyalists": "rivalry",
        "Merchant Guild": "rivalry",
        "Shadow Court": "tension",
        "Temple Authority": "neutral",
        "Free Companies": "alliance",
        "Old Blood": "rivalry",
        "Reformists": "alliance",
    },
    "Merchant Guild": {
        "Crown Loyalists": "tension",
        "People's Assembly": "rivalry",
        "Shadow Court": "alliance",
        "Temple Authority": "neutral",
        "Free Companies": "neutral",
        "Old Blood": "tension",
        "Reformists": "neutral",
    },
    "Shadow Court": {
        "Crown Loyalists": "tension",
        "People's Assembly": "tension",
        "Merchant Guild": "alliance",
        "Temple Authority": "rivalry",
        "Free Companies": "neutral",
        "Old Blood": "neutral",
        "Reformists": "tension",
    },
    "Temple Authority": {
        "Crown Loyalists": "alliance",
        "People's Assembly": "neutral",
        "Merchant Guild": "neutral",
        "Shadow Court": "rivalry",
        "Free Companies": "neutral",
        "Old Blood": "neutral",
        "Reformists": "alliance",
    },
    "Free Companies": {
        "Crown Loyalists": "rivalry",
        "People's Assembly": "alliance",
        "Merchant Guild": "neutral",
        "Shadow Court": "neutral",
        "Temple Authority": "neutral",
        "Old Blood": "tension",
        "Reformists": "tension",
    },
    "Old Blood": {
        "Crown Loyalists": "tension",
        "People's Assembly": "rivalry",
        "Merchant Guild": "tension",
        "Shadow Court": "neutral",
        "Temple Authority": "neutral",
        "Free Companies": "tension",
        "Reformists": "neutral",
    },
    "Reformists": {
        "Crown Loyalists": "rivalry",
        "People's Assembly": "alliance",
        "Merchant Guild": "neutral",
        "Shadow Court": "tension",
        "Temple Authority": "alliance",
        "Free Companies": "tension",
        "Old Blood": "neutral",
    },
}

# Ordered list of all faction names for consistent iteration
FACTION_NAMES: List[str] = list(FACTIONS.keys())

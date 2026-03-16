"""
codex.forge.reference_data.crown_leaders
=========================================
Deep lore data for Crown & Crew leaders and patrons.

Each entry includes personality, backstory, secret agenda, betrayal trigger,
political alignment, and inter-leader relationship mappings.

Political alignment: crown_lean float from -1.0 (pure crew) to +1.0 (pure crown).
Relationship attitudes: rival / ally / neutral / suspicious.
"""

from typing import Dict, Any

# =============================================================================
# LEADERS — The Crew's Known Champions
# =============================================================================

LEADERS: Dict[str, Dict[str, Any]] = {
    "Captain Vane": {
        "title": "Captain of the Free Crews",
        "personality": "Charismatic, reckless, fiercely loyal to anyone who earns it",
        "backstory": (
            "Once a Crown naval officer who watched his crew executed for a crime "
            "they didn't commit. Defected the night of their hanging, taking three "
            "warships and their crews with him. Lives by the code: 'No one gets left "
            "on the gibbet.'"
        ),
        "secret_agenda": "Seeking the logbook that proves Crown corruption — intends to use it as leverage, not justice",
        "betrayal_trigger": "If the Crown offers him his old commission back and exonerates his dead crew posthumously",
        "loyalty_bonus": "+1 sway when rescuing a crewmate from certain death",
        "crown_lean": -0.7,
        "relationships": {
            "The Defector": "suspicious",
            "The Mercenary": "neutral",
            "The Mystic": "ally",
            "Brother Ash": "rival",
            "Lady Miren": "neutral",
            "The Faceless": "suspicious",
            "Old Sergeant Kell": "ally",
        },
    },
    "The Defector": {
        "title": "Former Crown Intelligence Analyst",
        "personality": "Calculating, paranoid, never explains his reasoning until after the fact",
        "backstory": (
            "Spent fifteen years mapping informant networks for the Crown Spymaster. "
            "Vanished the day he discovered his own name on a termination list. "
            "Everything he knows about the Crew was learned by hunting them first."
        ),
        "secret_agenda": "Building a second set of records — blackmail insurance against both the Crown and the Crew's leadership",
        "betrayal_trigger": "If his family (whom he believes dead) are revealed to be alive and held by the Crown",
        "loyalty_bonus": "+1 sway when successfully gathering intelligence without violence",
        "crown_lean": -0.2,
        "relationships": {
            "Captain Vane": "suspicious",
            "The Mercenary": "ally",
            "The Mystic": "neutral",
            "Brother Ash": "rival",
            "Lady Miren": "ally",
            "The Faceless": "suspicious",
            "Old Sergeant Kell": "neutral",
        },
    },
    "The Mercenary": {
        "title": "Blademaster of the Ironhand Company",
        "personality": "Pragmatic, professionally cheerful, deeply transactional",
        "backstory": (
            "Has fought under six different banners in three wars and made peace "
            "with the fact that loyalty is a luxury. The Crew pays on time and "
            "doesn't ask questions about old scars. That's enough."
        ),
        "secret_agenda": "Skimming a percentage of every operation to fund retirement on a distant island",
        "betrayal_trigger": "If the Crown offers double his current contract rate with a signed amnesty",
        "loyalty_bonus": "No sway bonus — reliable but mercenary",
        "crown_lean": 0.0,
        "relationships": {
            "Captain Vane": "neutral",
            "The Defector": "ally",
            "The Mystic": "suspicious",
            "Brother Ash": "neutral",
            "Lady Miren": "neutral",
            "The Faceless": "rival",
            "Old Sergeant Kell": "ally",
        },
    },
    "The Mystic": {
        "title": "Keeper of the Unmarked Path",
        "personality": "Serene, oblique, occasionally terrifying when direct",
        "backstory": (
            "Was a Crown court astrologer before she predicted an assassination "
            "attempt on the king — correctly, two days early. The King's suspicion "
            "that she had foreknowledge became a charge of conspiracy. She walked "
            "out of her own execution, and no one has explained how."
        ),
        "secret_agenda": "Searching for a specific artifact the Crown confiscated from her predecessor — its nature she will not discuss",
        "betrayal_trigger": "If the artifact is recovered and its power threatens people she cares about",
        "loyalty_bonus": "+1 sway when following her cryptic guidance on breach day",
        "crown_lean": -0.5,
        "relationships": {
            "Captain Vane": "ally",
            "The Defector": "neutral",
            "The Mercenary": "suspicious",
            "Brother Ash": "rival",
            "Lady Miren": "suspicious",
            "The Faceless": "neutral",
            "Old Sergeant Kell": "neutral",
        },
    },
    "Brother Ash": {
        "title": "Former Inquisitor, Third Seat",
        "personality": "Zealous, self-flagellating, genuinely believes the Crew's cause is divine mandate",
        "backstory": (
            "Was an Inquisitor who burned three villages looking for heretics, found "
            "none, and walked into the wilderness to do penance. The Crew found him "
            "half-starved, still wearing his Inquisition brand. He joined because "
            "'God sends me where I am needed, not where I am comfortable.'"
        ),
        "secret_agenda": "Seeks to destroy the Inquisition from within — and believes the player is the instrument of that destruction",
        "betrayal_trigger": "If the Crew's actions cause civilian casualties that rival the Inquisition's own crimes",
        "loyalty_bonus": "+1 sway when protecting the innocent at personal cost",
        "crown_lean": -0.3,
        "relationships": {
            "Captain Vane": "rival",
            "The Defector": "rival",
            "The Mercenary": "neutral",
            "The Mystic": "rival",
            "Lady Miren": "neutral",
            "The Faceless": "suspicious",
            "Old Sergeant Kell": "ally",
        },
    },
    "Lady Miren": {
        "title": "The Fallen Countess of Ashenvale",
        "personality": "Elegant, ruthlessly polite, carries old money's absolute certainty that she is right",
        "backstory": (
            "Her family backed the wrong succession claimant three generations ago. "
            "The title was stripped, the lands burned, and she grew up in a debtor's "
            "house knowing exactly what was stolen. The Crew offered resources. "
            "She offered connections and a very long memory."
        ),
        "secret_agenda": "Intends to reclaim Ashenvale through legal channels once the Crew destabilizes the current regime — the Crew is a means, not an end",
        "betrayal_trigger": "If offered official restitution of her family's lands and title",
        "loyalty_bonus": "+1 sway when successfully manipulating Crown officials through social means",
        "crown_lean": 0.3,
        "relationships": {
            "Captain Vane": "neutral",
            "The Defector": "ally",
            "The Mercenary": "neutral",
            "The Mystic": "suspicious",
            "Brother Ash": "neutral",
            "The Faceless": "rival",
            "Old Sergeant Kell": "suspicious",
        },
    },
    "The Faceless": {
        "title": "Voice of the Unaligned",
        "personality": "Ideologically pure, charismatically abrasive, allergic to hierarchy",
        "backstory": (
            "No one knows where they came from, and they have made that a point "
            "of principle. Wears a blank mask to deny the Crown's ability to make "
            "their face into a symbol. Has organized three dockworker uprisings and "
            "a miller's strike that nearly collapsed the capital's grain supply."
        ),
        "secret_agenda": "The Faceless wants the Crew to dissolve itself after victory — they believe all leadership structures self-corrupt",
        "betrayal_trigger": "If the Crew starts behaving like the Crown — issuing mandates, punishing defection, demanding oaths",
        "loyalty_bonus": "+1 sway when the player defies the Crew's hierarchy for principle",
        "crown_lean": -0.9,
        "relationships": {
            "Captain Vane": "suspicious",
            "The Defector": "suspicious",
            "The Mercenary": "rival",
            "The Mystic": "neutral",
            "Brother Ash": "suspicious",
            "Lady Miren": "rival",
            "Old Sergeant Kell": "rival",
        },
    },
    "Old Sergeant Kell": {
        "title": "Sergeant-Major (Retired), Seventh Infantry",
        "personality": "Blunt, warm, has seen enough death to find gallows humor appropriate",
        "backstory": (
            "Thirty-two years under the Crown's colors, four wars, and a pension "
            "that didn't cover his veterans' medical costs. When the Crown dissolved "
            "the Seventh Infantry to cut expenses, he organized the survivors. Most "
            "of them are in the Crew now. 'Same job,' he says. 'Different employer.'"
        ),
        "secret_agenda": "Wants to negotiate a veterans' amnesty for all former Crown soldiers in the Crew before the end — a final act of care for his people",
        "betrayal_trigger": "If the Crew orders actions that would cause veterans' amnesty to become politically impossible",
        "loyalty_bonus": "+1 sway when following a tactically sound plan even at personal risk",
        "crown_lean": 0.1,
        "relationships": {
            "Captain Vane": "ally",
            "The Defector": "neutral",
            "The Mercenary": "ally",
            "The Mystic": "neutral",
            "Brother Ash": "ally",
            "Lady Miren": "suspicious",
            "The Faceless": "rival",
        },
    },
}

# =============================================================================
# PATRONS — The Crown's Representatives
# =============================================================================

PATRONS: Dict[str, Dict[str, Any]] = {
    "The High Inquisitor": {
        "title": "First Voice of the Crown's Law",
        "personality": "Coldly methodical, believes the law is divine and his interpretation of it is final",
        "backstory": (
            "Rose from a merchant family by passing every exam the Crown offered and "
            "then writing new ones. Has never lost a case, because he doesn't bring "
            "cases he hasn't already won. The Crew's existence is a personal affront."
        ),
        "secret_agenda": "Constructing an updated legal framework that would make all dissent a capital offense — needs the Crew's network maps to close the loopholes",
        "betrayal_trigger": "Would never betray the Crown — but could be discredited if his personal financial irregularities were exposed",
        "leverage_bonus": "+1 pressure when invoking law and precedent",
        "crown_lean": 1.0,
        "relationships": {
            "The Governor": "rival",
            "The Spymaster": "suspicious",
            "The Justiciar": "ally",
            "The High Priestess": "neutral",
            "The Merchant Prince": "suspicious",
            "The Iron Marshal": "ally",
            "The Court Astrologer": "rival",
        },
    },
    "The Governor": {
        "title": "Provincial Governor, Northern Reach",
        "personality": "Pragmatic administrator, despises inefficiency, can be reasoned with if you bring numbers",
        "backstory": (
            "Appointed three governors ago, survived by being useful rather than "
            "loyal. Has rebuilt two provinces after wars and has genuine pride in "
            "stable roads and functioning granaries. Views the Crew as expensive "
            "disorder, not a moral threat."
        ),
        "secret_agenda": "Skimming reconstruction funds into private accounts — would deal with the Crew quietly if it means keeping the audit away",
        "betrayal_trigger": "Can be flipped to neutrality if given evidence of the High Inquisitor's overreach threatening the province",
        "leverage_bonus": "+1 pressure when threatening economic disruption",
        "crown_lean": 0.6,
        "relationships": {
            "The High Inquisitor": "rival",
            "The Spymaster": "neutral",
            "The Justiciar": "neutral",
            "The High Priestess": "ally",
            "The Merchant Prince": "ally",
            "The Iron Marshal": "suspicious",
            "The Court Astrologer": "neutral",
        },
    },
    "The Spymaster": {
        "title": "Director of the Crown's Intelligence Bureau",
        "personality": "Urbane, never surprised, always three steps ahead — or pretending to be",
        "backstory": (
            "The Spymaster doesn't have a real name in any record. The current "
            "holder of the position may be the third or fourth person to hold it "
            "under that title. Whoever they are, they've run the Defector's old "
            "network for fifteen years and know where every body is buried."
        ),
        "secret_agenda": "Maintaining the Crew as a controlled opposition — they are more useful as a threat than as a solved problem",
        "betrayal_trigger": "Will expose Crown corruption if the High Inquisitor moves to dissolve the Intelligence Bureau",
        "leverage_bonus": "+1 pressure when using information as leverage",
        "crown_lean": 0.4,
        "relationships": {
            "The High Inquisitor": "suspicious",
            "The Governor": "neutral",
            "The Justiciar": "neutral",
            "The High Priestess": "suspicious",
            "The Merchant Prince": "ally",
            "The Iron Marshal": "neutral",
            "The Court Astrologer": "ally",
        },
    },
    "The Justiciar": {
        "title": "Lord Justiciar of the High Courts",
        "personality": "Incorruptible, procedurally obsessed, genuinely believes in due process",
        "backstory": (
            "The one Patron who actually reads the warrants before signing them. "
            "Has dismissed three Crown cases on procedural grounds, to the King's "
            "fury, because the evidence was improperly obtained. Hates the Crew "
            "and hates the Inquisitor's methods with equal conviction."
        ),
        "secret_agenda": "Writing a legal precedent that would limit Crown executive power — needs a test case, even a Crew case, to set the precedent",
        "betrayal_trigger": "Would stay his hand if the Crew submitted to lawful trial — sees legal process as more important than outcome",
        "leverage_bonus": "+1 pressure when operating within legal frameworks (even technically)",
        "crown_lean": 0.7,
        "relationships": {
            "The High Inquisitor": "ally",
            "The Governor": "neutral",
            "The Spymaster": "neutral",
            "The High Priestess": "ally",
            "The Merchant Prince": "suspicious",
            "The Iron Marshal": "rival",
            "The Court Astrologer": "neutral",
        },
    },
    "The High Priestess": {
        "title": "Archpriestess of the Sacred Compact",
        "personality": "Serene, politically astute, operates entirely through moral framing",
        "backstory": (
            "Commands more genuine loyalty than the King in three provinces because "
            "her temples feed the poor. Opposes the Crew not from loyalty to the "
            "Crown but from fear that their revolution would burn the temples along "
            "with the palaces."
        ),
        "secret_agenda": "Negotiating a Concordat with the Crown that would give the Temple legal immunity in exchange for supporting the suppression of the Crew",
        "betrayal_trigger": "Would withhold support from the Crown if the Inquisitor moved against Temple lands",
        "leverage_bonus": "+1 pressure when invoking public morality or mercy",
        "crown_lean": 0.5,
        "relationships": {
            "The High Inquisitor": "neutral",
            "The Governor": "ally",
            "The Spymaster": "suspicious",
            "The Justiciar": "ally",
            "The Merchant Prince": "neutral",
            "The Iron Marshal": "neutral",
            "The Court Astrologer": "suspicious",
        },
    },
    "The Merchant Prince": {
        "title": "Chair of the Crown's Trade Commission",
        "personality": "Convivially greedy, views everything as a transaction, is genuinely difficult to offend",
        "backstory": (
            "Made his fortune supplying both sides of the last border war and "
            "considers that a business success, not a moral failure. Supports the "
            "Crown because stability is good for trade. Would support the Crew if "
            "they offered better terms."
        ),
        "secret_agenda": "Wants the Crew's smuggling network — not destroyed, acquired",
        "betrayal_trigger": "Will broker a quiet deal with the Crew if they offer him control of the docklands and a cut of their operations",
        "leverage_bonus": "+1 pressure when appealing to financial incentives",
        "crown_lean": 0.2,
        "relationships": {
            "The High Inquisitor": "suspicious",
            "The Governor": "ally",
            "The Spymaster": "ally",
            "The Justiciar": "suspicious",
            "The High Priestess": "neutral",
            "The Iron Marshal": "neutral",
            "The Court Astrologer": "neutral",
        },
    },
    "The Iron Marshal": {
        "title": "Marshal-General of the Crown's Standing Armies",
        "personality": "Blunt, contemptuous of political maneuvering, respects only direct action",
        "backstory": (
            "Won the Succession War in six weeks by doing things the previous "
            "Marshal refused to do. The King rewards results and ignores methods. "
            "Views the Crew as an insurgency problem — which means a logistics "
            "problem, which means a solvable problem, given enough soldiers."
        ),
        "secret_agenda": "Wants the war to continue — peace is bad for military budgets and his personal power",
        "betrayal_trigger": "Will oppose the Crown if ordered to stand down for political reasons — he does not accept political limits on military solutions",
        "leverage_bonus": "+1 pressure when demonstrating tactical capability",
        "crown_lean": 0.9,
        "relationships": {
            "The High Inquisitor": "ally",
            "The Governor": "suspicious",
            "The Spymaster": "neutral",
            "The Justiciar": "rival",
            "The High Priestess": "neutral",
            "The Merchant Prince": "neutral",
            "The Court Astrologer": "suspicious",
        },
    },
    "The Court Astrologer": {
        "title": "Royal Reader of the Celestial Record",
        "personality": "Distantly amused, speaks in layers, may be genuinely prescient or an expert manipulator",
        "backstory": (
            "Has served four kings and outlived three. The Crew's former Mystic "
            "was one of her students. She cast the horoscope at the Crew's founding "
            "and keeps a copy in a locked box. She will tell no one what it says."
        ),
        "secret_agenda": "Ensuring a specific succession outcome she predicted decades ago — all her political moves serve a calendar no one else can read",
        "betrayal_trigger": "Will aid the Crew if a specific celestial event occurs — she has been waiting for it",
        "leverage_bonus": "+1 pressure when invoking prophecy, fate, or long-term consequence",
        "crown_lean": 0.1,
        "relationships": {
            "The High Inquisitor": "rival",
            "The Governor": "neutral",
            "The Spymaster": "ally",
            "The Justiciar": "neutral",
            "The High Priestess": "suspicious",
            "The Merchant Prince": "neutral",
            "The Iron Marshal": "suspicious",
        },
    },
}

# =============================================================================
# LEADER EVENTS — Unique Events Tied to Specific Leaders
# =============================================================================

LEADER_EVENTS: Dict[str, list] = {
    "Captain Vane": [
        {
            "text": "Vane receives word that a former crewmate is being held at Crown Station Seven. He's asking for volunteers — not orders.",
            "bias": "crew", "tag": "HEARTH",
            "sway_shift": 1,
        },
        {
            "text": "A Crown naval vessel flies a white flag in the harbor. Vane recognizes the captain's signal — an old Navy code for 'meet me alone.'",
            "bias": "crown", "tag": "GUILE",
            "sway_shift": -1,
        },
    ],
    "The Defector": [
        {
            "text": "The Defector hands you a sealed folder before dawn. 'Don't open it unless I don't come back by sunset,' he says, and walks into the city alone.",
            "bias": "neutral", "tag": "SILENCE",
            "sway_shift": 0,
        },
        {
            "text": "A Crown analyst has been asking questions about the Defector's old cover identities. He wants them silenced. He won't say how.",
            "bias": "crown", "tag": "BLOOD",
            "sway_shift": -1,
        },
    ],
    "The Mystic": [
        {
            "text": "The Mystic has been awake for three days. She says the artifact is close. She says this every six months, but this time her hands are shaking.",
            "bias": "crew", "tag": "SILENCE",
            "sway_shift": 1,
        },
        {
            "text": "A Temple priest approaches your camp under escort. He carries a letter with the Court Astrologer's seal. He delivers it to the Mystic and leaves without a word.",
            "bias": "neutral", "tag": "GUILE",
            "sway_shift": 0,
        },
    ],
    "Brother Ash": [
        {
            "text": "Ash has found a survivor from one of the villages his old unit burned. He's asking you to witness his apology. The survivor has a knife.",
            "bias": "crew", "tag": "HEARTH",
            "sway_shift": 1,
        },
        {
            "text": "An Inquisitor arrives demanding Ash's surrender, citing a warrant sealed before he joined the Crew. The Crew is watching to see what you do.",
            "bias": "crown", "tag": "DEFIANCE",
            "sway_shift": -1,
        },
    ],
    "Lady Miren": [
        {
            "text": "Miren has received a legal brief from a Crown solicitor — the beginning of her land restoration claim. She needs you to secure a specific document as evidence.",
            "bias": "neutral", "tag": "GUILE",
            "sway_shift": 0,
        },
        {
            "text": "A Crown noble has offered to restore one-third of Miren's lands immediately in exchange for her resignation from the Crew. She hasn't said no yet.",
            "bias": "crown", "tag": "HEARTH",
            "sway_shift": -1,
        },
    ],
    "The Faceless": [
        {
            "text": "The Faceless has organized a work stoppage at the Crown's main granary. Three hundred workers are refusing to unload. The city has food for two weeks.",
            "bias": "crew", "tag": "DEFIANCE",
            "sway_shift": 1,
        },
        {
            "text": "Someone has unmasked The Faceless — or claims to. A pamphlet is circulating with a name and a face. The Crew is buzzing. The Faceless says nothing.",
            "bias": "neutral", "tag": "SILENCE",
            "sway_shift": 0,
        },
    ],
    "Old Sergeant Kell": [
        {
            "text": "Three Crown veterans have deserted and come to Kell for protection. They're good soldiers. They're also wanted for a mutiny that left two officers dead.",
            "bias": "crew", "tag": "BLOOD",
            "sway_shift": 1,
        },
        {
            "text": "The Crown has announced a veterans' amnesty — conditional on surrender. Kell reads it three times. 'It's real,' he says. 'But it's only for the rank and file.'",
            "bias": "crown", "tag": "HEARTH",
            "sway_shift": -1,
        },
    ],
    "The Mercenary": [
        {
            "text": "The Mercenary has received a competing offer. He's shown it to you before telling the Crew. The number is significant.",
            "bias": "neutral", "tag": "BLOOD",
            "sway_shift": 0,
        },
        {
            "text": "The Ironhand Company's old contracts have surfaced — including one where they worked for the Crown to suppress a dock strike. Three crewmates recognize the date.",
            "bias": "crew", "tag": "DEFIANCE",
            "sway_shift": 1,
        },
    ],
}

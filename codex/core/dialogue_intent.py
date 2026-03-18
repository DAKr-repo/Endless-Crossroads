"""
Dialogue Intent Classifier — Sentiment-to-Trait (S2T) Pipeline.
================================================================

Zero-LLM keyword classifier that maps player dialogue to personality
nudges and bond changes. Used by the companion dialogue bridge in
play_burnwillow._companion_dialogue() to wire player speech to
trait evolution.

WO-V62.0: Dialogue-to-Trait Evolution Bridge.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class DialogueIntent:
    """Classified intent from a player's dialogue line."""
    category: str                           # "counsel_caution", "praise", etc.
    confidence: float                       # 0.0-1.0
    trait_nudges: List[Tuple[str, float]]   # [(trait, delta), ...]
    bond_delta: float                       # How much this affects bond
    acknowledgment: str                     # Short phrase for Mimir prompt


# =========================================================================
# INTENT DEFINITIONS — keyword patterns + effects
# =========================================================================

_INTENT_DEFS: List[dict] = [
    # --- Hostile intents (checked first, override positive) ---
    {
        "category": "insult",
        "phrases": ["useless", "pathetic", "worthless", "idiot", "fool", "weak", "coward"],
        "nudges": [("aggression", 0.02)],
        "bond": -0.04,
        "ack": "insulted you",
    },
    {
        "category": "threaten",
        "phrases": ["or else", "do as i say", "obey", "shut up", "i'll leave you", "don't test me"],
        "nudges": [("caution", 0.02), ("aggression", 0.01)],
        "bond": -0.03,
        "ack": "threatened you",
    },
    {
        "category": "criticize",
        "phrases": ["you should have", "why didn't you", "that was bad", "what were you thinking"],
        "nudges": [],
        "bond": -0.02,
        "ack": "criticized your actions",
    },
    {
        "category": "dismiss",
        "phrases": ["whatever", "don't care", "not interested", "go away", "leave me alone"],
        "nudges": [],
        "bond": -0.02,
        "ack": "dismissed you",
    },
    # --- Positive intents ---
    {
        "category": "counsel_caution",
        "phrases": ["be careful", "stay back", "watch out", "don't rush", "play safe", "slow down"],
        "nudges": [("caution", 0.03), ("aggression", -0.02)],
        "bond": 0.01,
        "ack": "counseled caution",
    },
    {
        "category": "encourage_aggression",
        "phrases": ["charge in", "fight harder", "be brave", "hit them", "don't hold back", "go all out"],
        "nudges": [("aggression", 0.03), ("caution", -0.02)],
        "bond": 0.01,
        "ack": "encouraged aggression",
    },
    {
        "category": "encourage_curiosity",
        "phrases": ["look around", "investigate", "what do you think", "check that", "explore"],
        "nudges": [("curiosity", 0.03)],
        "bond": 0.01,
        "ack": "encouraged exploration",
    },
    {
        "category": "praise",
        "phrases": ["good job", "well done", "nice work", "great fight", "thank you", "amazing"],
        "nudges": [],
        "bond": 0.03,
        "ack": "praised you",
    },
    {
        "category": "comfort",
        "phrases": ["are you ok", "hang in there", "we'll make it", "don't worry", "it's alright"],
        "nudges": [("caution", 0.01)],
        "bond": 0.02,
        "ack": "offered comfort",
    },
]

# Pre-sort: multi-word phrases first (longest match), then single words
_SORTED_INTENTS: List[Tuple[str, str, dict]] = []
for _def in _INTENT_DEFS:
    for _phrase in _def["phrases"]:
        _SORTED_INTENTS.append((_phrase, _def["category"], _def))
_SORTED_INTENTS.sort(key=lambda x: len(x[0]), reverse=True)


def classify_intent(player_message: str) -> DialogueIntent:
    """Classify player dialogue into an intent category.

    Uses keyword matching with priority ordering:
    hostile intents override positive when both could match.
    Multi-word phrases checked before single keywords.
    """
    text = player_message.lower().strip()
    if not text:
        return DialogueIntent(
            category="bond", confidence=0.1,
            trait_nudges=[], bond_delta=0.005,
            acknowledgment="spoke to you",
        )

    for phrase, category, intent_def in _SORTED_INTENTS:
        if phrase in text:
            return DialogueIntent(
                category=category,
                confidence=0.8 if len(phrase) > 4 else 0.6,
                trait_nudges=list(intent_def["nudges"]),
                bond_delta=intent_def["bond"],
                acknowledgment=intent_def["ack"],
            )

    # Fallback: any conversation builds a tiny bond
    return DialogueIntent(
        category="bond", confidence=0.1,
        trait_nudges=[], bond_delta=0.005,
        acknowledgment="spoke to you",
    )

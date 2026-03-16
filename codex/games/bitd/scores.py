"""
codex.games.bitd.scores
=========================
Score cycle subsystem for Blades in the Dark.

Handles engagement rolls, flashbacks, Devil's Bargains, and score state.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random


@dataclass
class ScoreState:
    """Tracks the state of an active score (heist/job)."""

    target: str = ""
    plan_type: str = ""       # assault, deception, infiltration, occult, social, transport
    detail: str = ""          # specific detail for the plan
    engagement_result: int = 0
    active: bool = False
    flashbacks_used: int = 0
    devils_bargains: List[str] = field(default_factory=list)
    complications: List[str] = field(default_factory=list)
    heat_generated: int = 0
    rep_earned: int = 0
    coin_earned: int = 0

    def to_dict(self) -> dict:
        """Serialize to a plain dict for persistence."""
        return {
            "target": self.target,
            "plan_type": self.plan_type,
            "detail": self.detail,
            "engagement_result": self.engagement_result,
            "active": self.active,
            "flashbacks_used": self.flashbacks_used,
            "devils_bargains": list(self.devils_bargains),
            "complications": list(self.complications),
            "heat_generated": self.heat_generated,
            "rep_earned": self.rep_earned,
            "coin_earned": self.coin_earned,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScoreState":
        """Deserialize from a plain dict."""
        return cls(
            target=data.get("target", ""),
            plan_type=data.get("plan_type", ""),
            detail=data.get("detail", ""),
            engagement_result=data.get("engagement_result", 0),
            active=data.get("active", False),
            flashbacks_used=data.get("flashbacks_used", 0),
            devils_bargains=data.get("devils_bargains", []),
            complications=data.get("complications", []),
            heat_generated=data.get("heat_generated", 0),
            rep_earned=data.get("rep_earned", 0),
            coin_earned=data.get("coin_earned", 0),
        )


# Plan types and engagement roll modifiers
PLAN_TYPES = {
    "assault": {"description": "Do violence to a target.", "detail_ask": "Point of attack"},
    "deception": {"description": "Lure, trick, or manipulate.", "detail_ask": "Method of deception"},
    "infiltration": {"description": "Trespass unseen.", "detail_ask": "Entry point"},
    "occult": {"description": "Engage a supernatural power.", "detail_ask": "Arcane method"},
    "social": {"description": "Negotiate, bargain, persuade.", "detail_ask": "Social connection"},
    "transport": {"description": "Carry cargo or people through danger.", "detail_ask": "Route or means"},
}

# Engagement result interpretation
ENGAGEMENT_OUTCOMES = {
    1: {"position": "desperate", "description": "Things have already gone very badly. The opposition has the advantage."},
    2: {"position": "desperate", "description": "Things have already gone very badly. The opposition has the advantage."},
    3: {"position": "desperate", "description": "Things have already gone very badly. The opposition has the advantage."},
    4: {"position": "risky", "description": "The situation is steep, but not hopeless. You have a chance."},
    5: {"position": "risky", "description": "The situation is steep, but not hopeless. You have a chance."},
    6: {"position": "controlled", "description": "Good setup. The opposition is unprepared or vulnerable."},
    # Critical (multiple 6s)
    7: {"position": "controlled", "description": "Exceptional start! You have total surprise or an overwhelming advantage."},
}


def engagement_roll(
    crew_tier: int = 0,
    plan_type: str = "infiltration",
    detail_bonus: int = 0,
    misc_bonus: int = 0,
    misc_penalty: int = 0,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Roll for engagement at the start of a score.

    Base pool is built from crew_tier + detail_bonus + misc_bonus, minus
    misc_penalty. If pool <= 0, roll 2d6 and take the lowest (disadvantage).

    Args:
        crew_tier: The crew's current tier rating.
        plan_type: One of the six plan types (assault, deception, etc.).
        detail_bonus: Bonus dice from a well-chosen plan detail.
        misc_bonus: Additional bonus dice from abilities or help.
        misc_penalty: Penalty dice from complications or opposition.
        rng: Optional seeded Random for deterministic testing.

    Returns:
        Dict with keys: dice, highest, critical, position, description, result_key.
    """
    _rng = rng or random.Random()
    total_bonus = crew_tier + detail_bonus + misc_bonus
    total_penalty = misc_penalty
    pool = max(0, total_bonus - total_penalty)

    if pool == 0:
        # Roll 2d6 take lowest (disadvantage)
        dice = sorted([_rng.randint(1, 6), _rng.randint(1, 6)])
        highest = dice[0]
        critical = False
    else:
        dice = [_rng.randint(1, 6) for _ in range(pool)]
        highest = max(dice)
        sixes = dice.count(6)
        critical = sixes >= 2

    if critical:
        result_key = 7
    else:
        result_key = min(6, highest)

    outcome = ENGAGEMENT_OUTCOMES.get(result_key, ENGAGEMENT_OUTCOMES[4])
    return {
        "dice": dice,
        "highest": highest,
        "critical": critical,
        "position": outcome["position"],
        "description": outcome["description"],
        "result_key": result_key,
    }


class FlashbackManager:
    """Manages flashback scenes during a score.

    Flashbacks cost stress (0-2 based on complexity).
    """

    COST_TABLE = {
        "simple": 0,     # A thing you could easily have done before
        "complex": 1,    # A thing that requires setup or resources
        "elaborate": 2,  # A thing that is very unlikely or requires luck
    }

    def __init__(self):
        self.flashbacks: List[Dict[str, Any]] = []

    def use_flashback(self, description: str, complexity: str = "simple") -> Dict[str, Any]:
        """Use a flashback during a score.

        Args:
            description: What the flashback depicts.
            complexity: One of 'simple', 'complex', or 'elaborate'.

        Returns:
            Dict with description, complexity, stress_cost, and index.
        """
        cost = self.COST_TABLE.get(complexity, 1)
        fb = {
            "description": description,
            "complexity": complexity,
            "stress_cost": cost,
            "index": len(self.flashbacks),
        }
        self.flashbacks.append(fb)
        return fb

    def to_dict(self) -> dict:
        """Serialize to a plain dict for persistence."""
        return {"flashbacks": list(self.flashbacks)}

    @classmethod
    def from_dict(cls, data: dict) -> "FlashbackManager":
        """Deserialize from a plain dict."""
        mgr = cls()
        mgr.flashbacks = data.get("flashbacks", [])
        return mgr


class DevilsBargainTracker:
    """Tracks Devil's Bargains offered and accepted during a score.

    A Devil's Bargain gives +1d to a roll in exchange for a complication.
    """

    # Sample bargains by category
    SAMPLE_BARGAINS = {
        "collateral_damage": [
            "An innocent bystander gets hurt.",
            "Property is destroyed beyond repair.",
            "A neutral faction takes offense.",
        ],
        "evidence": [
            "You leave behind clear evidence of your identity.",
            "A witness escapes and will talk.",
            "Your tools or gear are left at the scene.",
        ],
        "supernatural": [
            "A ghost takes notice of your activity.",
            "You attract the attention of a demon.",
            "The ghost field ripples and something stirs.",
        ],
        "betrayal": [
            "A friend or contact is compromised.",
            "Your vice catches up with you at the worst time.",
            "An old enemy learns your whereabouts.",
        ],
        "debt": [
            "You owe a favor to a dangerous person.",
            "You must sacrifice something valuable later.",
            "A clock starts ticking against you.",
        ],
    }

    def __init__(self):
        self.bargains_offered: List[Dict[str, str]] = []
        self.bargains_accepted: List[Dict[str, str]] = []

    def offer_bargain(self, category: str = "", rng: Optional[random.Random] = None) -> Dict[str, str]:
        """Generate and offer a Devil's Bargain.

        Args:
            category: Optional category key; random if empty or invalid.
            rng: Optional seeded Random for deterministic testing.

        Returns:
            Dict with category and description.
        """
        _rng = rng or random.Random()
        if not category or category not in self.SAMPLE_BARGAINS:
            category = _rng.choice(list(self.SAMPLE_BARGAINS.keys()))
        pool = self.SAMPLE_BARGAINS[category]
        desc = _rng.choice(pool)
        bargain = {"category": category, "description": desc}
        self.bargains_offered.append(bargain)
        return bargain

    def accept_bargain(self, index: int = -1) -> Optional[Dict[str, str]]:
        """Accept the most recent (or indexed) offered bargain.

        Args:
            index: Index into bargains_offered; -1 means most recent.

        Returns:
            The accepted bargain dict, or None if none were offered.
        """
        if not self.bargains_offered:
            return None
        idx = index if 0 <= index < len(self.bargains_offered) else len(self.bargains_offered) - 1
        bargain = self.bargains_offered[idx]
        self.bargains_accepted.append(bargain)
        return bargain

    def to_dict(self) -> dict:
        """Serialize to a plain dict for persistence."""
        return {
            "bargains_offered": list(self.bargains_offered),
            "bargains_accepted": list(self.bargains_accepted),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DevilsBargainTracker":
        """Deserialize from a plain dict."""
        tracker = cls()
        tracker.bargains_offered = data.get("bargains_offered", [])
        tracker.bargains_accepted = data.get("bargains_accepted", [])
        return tracker


def resolve_score(score: ScoreState, crew_tier: int = 0, target_tier: int = 0) -> Dict[str, Any]:
    """Resolve a completed score and determine outcomes.

    Calculates rep earned, heat generated, and coin based on the target's
    tier relative to the crew's tier.

    Args:
        score: The active ScoreState to resolve.
        crew_tier: The crew's current tier.
        target_tier: The target faction's tier.

    Returns:
        Dict with rep_earned, heat_generated, coin_earned, complications,
        flashbacks_used, and a summary string.
    """
    tier_diff = max(0, target_tier - crew_tier)
    base_rep = max(1, target_tier) + 1
    base_heat = max(0, 1 + tier_diff)

    # Complications add heat
    heat = base_heat + len(score.complications)
    rep = base_rep
    coin = max(1, target_tier)

    return {
        "rep_earned": rep,
        "heat_generated": heat,
        "coin_earned": coin,
        "complications": len(score.complications),
        "flashbacks_used": score.flashbacks_used,
        "summary": (
            f"Score complete! Target: {score.target or 'unknown'}. "
            f"Rep: +{rep}, Heat: +{heat}, Coin: +{coin}. "
            f"Complications: {len(score.complications)}, "
            f"Flashbacks: {score.flashbacks_used}."
        ),
    }

"""
Trait Evolution — Personality drift for AI companions.
=====================================================

WO-V61.0 Track D: Companions' personality floats evolve based on
in-game experiences. A vanguard who nearly dies learns caution.
A scholar who kills a boss gains aggression. Drift is capped to
prevent complete personality inversion.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TraitDelta:
    """A recorded event that nudges personality floats."""
    trait: str       # "aggression", "curiosity", "caution"
    delta: float     # +/- change (small: 0.02-0.05)
    reason: str      # "nearly_died", "saved_ally", "explored_secret"
    turn: int = 0


class TraitEvolution:
    """Tracks cumulative nudges to personality floats over time.

    MAX_DRIFT caps how far any trait can drift from its original value,
    preventing complete personality inversion.
    """

    MAX_DRIFT = 0.4

    def __init__(self, original_traits: dict):
        """
        Args:
            original_traits: Dict of trait_name -> float original value.
                             e.g. {"aggression": 0.9, "curiosity": 0.3, "caution": 0.1}
        """
        self.original: dict = dict(original_traits)
        self.deltas: List[TraitDelta] = []
        self.bond: float = 0.0  # -1.0 (enmity) to +1.0 (deep bond)

    def nudge(self, trait: str, delta: float, reason: str, turn: int = 0) -> None:
        """Apply a small personality nudge. Clamps to MAX_DRIFT from original."""
        if trait not in self.original:
            return
        self.deltas.append(TraitDelta(trait=trait, delta=delta, reason=reason, turn=turn))

    def get_current_value(self, trait: str) -> float:
        """Return the effective value for a single trait after all deltas."""
        if trait not in self.original:
            return 0.0
        base = self.original[trait]
        total_delta = sum(d.delta for d in self.deltas if d.trait == trait)
        # Clamp drift
        clamped_delta = max(-self.MAX_DRIFT, min(self.MAX_DRIFT, total_delta))
        return max(0.0, min(1.0, base + clamped_delta))

    def get_current_traits(self) -> dict:
        """Return all traits with accumulated nudges applied."""
        result = {}
        for trait in self.original:
            result[trait] = self.get_current_value(trait)
        return result

    def get_drift(self, trait: str) -> float:
        """Return the net drift for a trait (positive = increased)."""
        if trait not in self.original:
            return 0.0
        total = sum(d.delta for d in self.deltas if d.trait == trait)
        return max(-self.MAX_DRIFT, min(self.MAX_DRIFT, total))

    def get_evolution_summary(self) -> str:
        """Return a narrative summary of how the companion has changed."""
        if not self.deltas:
            return "No personality evolution yet."

        changes = []
        for trait in self.original:
            drift = self.get_drift(trait)
            if abs(drift) >= 0.05:
                direction = "more" if drift > 0 else "less"
                changes.append(f"{direction} {trait} ({drift:+.2f})")

        if not changes:
            return "Personality has barely shifted."

        reasons = set(d.reason for d in self.deltas[-5:])  # Recent reasons
        reason_str = ", ".join(reasons) if reasons else "experience"
        return f"Through {reason_str}: {'; '.join(changes)}."

    def adjust_bond(self, delta: float) -> None:
        """Adjust bond score. Clamps to -1.0 to +1.0."""
        self.bond = max(-1.0, min(1.0, self.bond + delta))

    def get_bond_tier(self) -> str:
        """Qualitative bond tier for prompt injection."""
        if self.bond >= 0.8:
            return "deeply bonded"
        if self.bond >= 0.5:
            return "trusted ally"
        if self.bond >= 0.2:
            return "growing closer"
        if self.bond >= -0.1:
            return "new acquaintance"
        if self.bond >= -0.5:
            return "distrustful"
        return "hostile"

    def get_bond_multiplier(self) -> float:
        """Scale dialogue nudge effectiveness by bond depth.

        Positive bond scales mentorship (0.3 baseline to 1.0 at deep bond).
        Negative bond INVERTS nudge direction — counsel is resisted.
        """
        if self.bond >= 0:
            return 0.3 + 0.7 * self.bond
        else:
            return 0.7 * self.bond

    def to_dict(self) -> dict:
        return {
            "original": dict(self.original),
            "deltas": [
                {"trait": d.trait, "delta": d.delta, "reason": d.reason, "turn": d.turn}
                for d in self.deltas
            ],
            "bond": self.bond,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TraitEvolution":
        evo = cls(data.get("original", {}))
        for d in data.get("deltas", []):
            evo.deltas.append(TraitDelta(
                trait=d["trait"], delta=d["delta"],
                reason=d.get("reason", ""), turn=d.get("turn", 0),
            ))
        evo.bond = data.get("bond", 0.0)
        return evo


# =========================================================================
# NUDGE TRIGGERS — Event-to-trait mapping
# =========================================================================

NUDGE_TRIGGERS = {
    "nearly_died":      [("caution", +0.03)],
    "killed_boss":      [("aggression", +0.02)],
    "saved_ally":       [("caution", -0.02), ("aggression", -0.01)],
    "found_secret":     [("curiosity", +0.02)],
    "learned_caution":  [("caution", +0.04)],
    "survivor_growth":  [("aggression", -0.02), ("caution", +0.03)],
    "player_feedback":  [],  # Context-dependent, handled by caller
}


def apply_nudge_trigger(evolution: TraitEvolution, trigger: str, turn: int = 0) -> List[str]:
    """Apply a predefined nudge trigger. Returns list of change descriptions."""
    nudges = NUDGE_TRIGGERS.get(trigger, [])
    descriptions = []
    for trait, delta in nudges:
        if trait in evolution.original:
            evolution.nudge(trait, delta, trigger, turn)
            direction = "gained" if delta > 0 else "lost"
            descriptions.append(f"{direction} {abs(delta):.2f} {trait} ({trigger})")
    return descriptions

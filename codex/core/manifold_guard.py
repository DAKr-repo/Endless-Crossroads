"""
manifold_guard.py - The Manifold Guard (Stability Layer)

Enforces "Conservation of Identity" through Manifold Constrained
Hyper-Connections (mHC). Acts as a Sinkhorn-Knopp normalizer between
the Narrative lane (generated text) and the State lane (ground truth JSON).

Core Principle: You cannot add new "Truth" without authorized State validation.
The State JSON is the single source of truth. Narrative must conform to it.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import numpy as np


class GuardVerdict(Enum):
    """Result of manifold validation."""
    PASS = "PASS"          # Narrative aligns with State
    FAIL = "FAIL"          # Irreconcilable contradiction
    CORRECT = "CORRECT"    # Minor drift, correction provided


@dataclass
class ValidationResult:
    """Result of verify_conservation_of_identity check."""
    verdict: GuardVerdict
    semantic_density: float          # 0.0 - 1.0, how much state is reflected
    drift_score: float               # 0.0 - 1.0, how far narrative drifted
    contradictions: list[str]        # List of detected contradictions
    correction_instruction: Optional[str] = None  # How to fix, if CORRECT
    normalized_narrative: Optional[str] = None    # Suggested fix


@dataclass
class StateClaim:
    """A claim extracted from narrative that can be validated."""
    claim_type: str      # "has", "lacks", "is", "can", "did", "quantity"
    subject: str         # What the claim is about
    predicate: str       # The assertion
    raw_text: str        # Original text span
    confidence: float    # Extraction confidence


@dataclass
class StateConstraint:
    """A constraint derived from the State JSON."""
    path: str            # JSON path (e.g., "character.spell_slots")
    value: Any           # The authoritative value
    constraint_type: str # "exists", "equals", "min", "max", "contains"


class ManifoldGuard:
    """
    The Guard - Sinkhorn-Knopp Normalizer for Narrative/State Alignment.

    Ensures that generated narrative does not contradict the ground truth
    state. Calculates semantic density and drift, provides corrections
    when possible, and hard-fails when contradictions are irreconcilable.
    """

    # Patterns for extracting claims from narrative
    CLAIM_PATTERNS = {
        "has": [
            r"(?:I |you |they |he |she |it |we )?(?:have|has|got|possess(?:es)?)\s+(?:a |an |the |my |your )?([\w\s]+)",
            r"(?:with|carrying|holding|wielding)\s+(?:a |an |the |my )?([\w\s]+)",
        ],
        "lacks": [
            r"(?:I |you |they )?(?:don't|doesn't|do not|does not)\s+have\s+([\w\s]+)",
            r"(?:no |without |lacking )([\w\s]+)",
            r"(?:ran out of|exhausted|depleted)\s+(?:my |the )?([\w\s]+)",
        ],
        "quantity": [
            r"(\d+)\s+([\w\s]+?)(?:\s+(?:left|remaining|available))?",
            r"([\w\s]+?):\s*(\d+)",
        ],
        "is": [
            r"(?:I am|you are|is|are)\s+(?:a |an |the )?([\w\s]+)",
            r"(?:currently|now)\s+([\w\s]+)",
        ],
        "can": [
            r"(?:I |you )?can(?:not|'t)?\s+([\w\s]+)",
            r"(?:able|unable)\s+to\s+([\w\s]+)",
        ],
        "did": [
            r"(?:I |you |they )?(?:cast|used|spent|consumed)\s+(?:a |an |the |my )?([\w\s]+)",
            r"(?:just |already )?(?:attacked|healed|moved|rolled)\s*([\w\s]*)",
        ],
    }

    # Keywords that map to common state paths
    STATE_KEYWORDS = {
        "spell_slots": ["spell", "slots", "spells", "casting", "cast"],
        "hit_points": ["hp", "health", "hit points", "hitpoints", "life"],
        "inventory": ["item", "items", "carrying", "has", "have", "gold", "coins"],
        "abilities": ["ability", "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
        "status": ["condition", "status", "poisoned", "paralyzed", "stunned", "prone"],
        "position": ["location", "position", "room", "area", "zone"],
        "resources": ["ki", "rage", "sorcery points", "channel divinity", "bardic inspiration"],
    }

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the Manifold Guard.

        Args:
            strict_mode: If True, any contradiction results in FAIL.
                        If False, attempts correction when possible.
        """
        self.strict_mode = strict_mode
        self._state_cache: dict = {}

    def extract_claims(self, narrative: str) -> list[StateClaim]:
        """
        Extract validatable claims from narrative text.

        Parses the narrative for assertions about state that can be
        checked against the ground truth JSON.
        """
        claims = []
        narrative_lower = narrative.lower()

        for claim_type, patterns in self.CLAIM_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, narrative_lower, re.IGNORECASE)
                for match in matches:
                    # Extract the subject/predicate from the match
                    groups = match.groups()
                    if groups:
                        subject = groups[0].strip() if groups[0] else ""
                        predicate = groups[1].strip() if len(groups) > 1 and groups[1] else ""

                        claims.append(StateClaim(
                            claim_type=claim_type,
                            subject=subject,
                            predicate=predicate,
                            raw_text=match.group(0),
                            confidence=0.7  # Base confidence for regex extraction
                        ))

        return claims

    def extract_constraints(self, state_json: dict, prefix: str = "") -> list[StateConstraint]:
        """
        Recursively extract constraints from state JSON.

        Flattens the JSON into a list of path-value constraints
        that can be checked against narrative claims.
        """
        constraints = []

        for key, value in state_json.items():
            path = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recurse into nested objects
                constraints.extend(self.extract_constraints(value, path))
            elif isinstance(value, list):
                # List: check for membership
                constraints.append(StateConstraint(
                    path=path,
                    value=value,
                    constraint_type="contains"
                ))
                # Also add count constraint
                constraints.append(StateConstraint(
                    path=f"{path}._count",
                    value=len(value),
                    constraint_type="equals"
                ))
            elif isinstance(value, bool):
                constraints.append(StateConstraint(
                    path=path,
                    value=value,
                    constraint_type="equals"
                ))
            elif isinstance(value, (int, float)):
                constraints.append(StateConstraint(
                    path=path,
                    value=value,
                    constraint_type="equals"
                ))
                # Numeric values also imply min/max of 0
                if value == 0:
                    constraints.append(StateConstraint(
                        path=path,
                        value=0,
                        constraint_type="max"
                    ))
            elif isinstance(value, str):
                constraints.append(StateConstraint(
                    path=path,
                    value=value.lower(),
                    constraint_type="equals"
                ))

        return constraints

    def _match_claim_to_constraint(
        self,
        claim: StateClaim,
        constraints: list[StateConstraint]
    ) -> Optional[tuple[StateConstraint, bool]]:
        """
        Find the constraint that matches a claim and check validity.

        Returns:
            (constraint, is_valid) tuple, or None if no matching constraint.
        """
        claim_text = f"{claim.subject} {claim.predicate}".lower()

        for constraint in constraints:
            path_parts = constraint.path.lower().split(".")

            # Check if any path component matches the claim
            for part in path_parts:
                if part in claim_text or any(
                    kw in claim_text
                    for kw in self.STATE_KEYWORDS.get(part, [])
                ):
                    # Found a potential match - validate
                    is_valid = self._validate_claim_against_constraint(claim, constraint)
                    return (constraint, is_valid)

        return None

    def _validate_claim_against_constraint(
        self,
        claim: StateClaim,
        constraint: StateConstraint
    ) -> bool:
        """
        Check if a specific claim is valid against a constraint.
        """
        # Handle "lacks" claims - asserting something is not present
        if claim.claim_type == "lacks":
            if constraint.constraint_type == "equals":
                if isinstance(constraint.value, (int, float)):
                    return constraint.value == 0
                if isinstance(constraint.value, bool):
                    return not constraint.value
            if constraint.constraint_type == "contains":
                return len(constraint.value) == 0
            return True  # Can't disprove, assume valid

        # Handle "has" claims - asserting possession
        if claim.claim_type == "has":
            if constraint.constraint_type == "equals":
                if isinstance(constraint.value, (int, float)):
                    return constraint.value > 0
                if isinstance(constraint.value, bool):
                    return constraint.value
            if constraint.constraint_type == "contains":
                # Check if claimed item is in the list
                claim_item = claim.subject.lower()
                return any(
                    claim_item in str(item).lower()
                    for item in constraint.value
                )
            return True

        # Handle "quantity" claims - asserting specific numbers
        if claim.claim_type == "quantity":
            try:
                claimed_value = int(claim.subject) if claim.subject.isdigit() else int(claim.predicate)
                if constraint.constraint_type == "equals":
                    return claimed_value == constraint.value
                if constraint.constraint_type == "max":
                    return claimed_value <= constraint.value
                if constraint.constraint_type == "min":
                    return claimed_value >= constraint.value
            except (ValueError, TypeError):
                pass
            return True

        # Handle "did" claims - asserting actions taken
        if claim.claim_type == "did":
            # Check if action is possible given state
            # e.g., "cast fireball" requires spell_slots > 0
            if "cast" in claim.raw_text or "spell" in claim.subject:
                if "spell" in constraint.path.lower():
                    if isinstance(constraint.value, (int, float)):
                        return constraint.value > 0
            return True

        # Default: can't validate, assume valid
        return True

    def calculate_semantic_density(
        self,
        claims: list[StateClaim],
        constraints: list[StateConstraint],
        narrative: str
    ) -> float:
        """
        Calculate how much of the state is reflected in the narrative.

        Semantic Density = (matched_constraints / total_constraints)

        Higher density means the narrative is well-grounded in state.
        """
        if not constraints:
            return 1.0  # No constraints = fully dense by default

        matched = 0
        narrative_lower = narrative.lower()

        for constraint in constraints:
            path_parts = constraint.path.lower().split(".")
            for part in path_parts:
                if part.startswith("_"):
                    continue
                if part in narrative_lower:
                    matched += 1
                    break
                # Check keyword synonyms
                for kw in self.STATE_KEYWORDS.get(part, []):
                    if kw in narrative_lower:
                        matched += 1
                        break

        return min(1.0, matched / len(constraints))

    def calculate_drift_score(
        self,
        claims: list[StateClaim],
        constraints: list[StateConstraint]
    ) -> tuple[float, list[str]]:
        """
        Calculate how far the narrative has drifted from state truth.

        Drift Score = (invalid_claims / total_claims)

        Returns:
            (drift_score, list_of_contradictions)
        """
        if not claims:
            return 0.0, []

        invalid_claims = 0
        contradictions = []

        for claim in claims:
            match_result = self._match_claim_to_constraint(claim, constraints)
            if match_result:
                constraint, is_valid = match_result
                if not is_valid:
                    invalid_claims += 1
                    contradictions.append(
                        f"CONTRADICTION: '{claim.raw_text}' violates {constraint.path}={constraint.value}"
                    )

        drift = invalid_claims / len(claims) if claims else 0.0
        return drift, contradictions

    def _sinkhorn_normalize(
        self,
        narrative_weight: float,
        state_weight: float,
        iterations: int = 5
    ) -> tuple[float, float]:
        """
        Apply Sinkhorn-Knopp normalization to balance narrative/state weights.

        This ensures the "information budget" is conserved - narrative
        cannot assert more than the state authorizes.
        """
        # Create 2x2 matrix: [narrative_self, narrative_to_state]
        #                    [state_to_narrative, state_self]
        matrix = np.array([
            [narrative_weight, 1 - narrative_weight],
            [1 - state_weight, state_weight]
        ], dtype=np.float64)

        # Sinkhorn iterations
        for _ in range(iterations):
            # Row normalization
            row_sums = matrix.sum(axis=1, keepdims=True)
            row_sums = np.where(row_sums == 0, 1, row_sums)
            matrix = matrix / row_sums

            # Column normalization
            col_sums = matrix.sum(axis=0, keepdims=True)
            col_sums = np.where(col_sums == 0, 1, col_sums)
            matrix = matrix / col_sums

        # Return normalized weights
        return float(matrix[0, 0]), float(matrix[1, 1])

    def generate_correction(
        self,
        contradictions: list[str],
        narrative: str,
        state_json: dict
    ) -> str:
        """
        Generate correction instruction for the Voice module.

        Provides specific guidance on how to fix the narrative
        to align with state truth.
        """
        if not contradictions:
            return ""

        corrections = ["[MANIFOLD GUARD CORRECTION REQUIRED]", ""]
        corrections.append("The following statements contradict authorized state:")

        for contradiction in contradictions:
            corrections.append(f"  - {contradiction}")

        corrections.append("")
        corrections.append("INSTRUCTION: Regenerate response with these constraints:")

        # Extract specific fixes from state
        for contradiction in contradictions:
            if "spell" in contradiction.lower():
                slots = self._find_in_state(state_json, "spell_slots", "slots")
                if slots is not None:
                    corrections.append(f"  - Spell slots available: {slots}")
            if "hp" in contradiction.lower() or "health" in contradiction.lower():
                hp = self._find_in_state(state_json, "hit_points", "hp", "health")
                if hp is not None:
                    corrections.append(f"  - Current HP: {hp}")
            if "item" in contradiction.lower() or "inventory" in contradiction.lower():
                inv = self._find_in_state(state_json, "inventory", "items")
                if inv is not None:
                    corrections.append(f"  - Inventory contains: {inv}")

        return "\n".join(corrections)

    def _find_in_state(self, state: dict, *keys) -> Any:
        """Helper to find a value in state by trying multiple keys."""
        for key in keys:
            if key in state:
                return state[key]
            # Check nested
            for v in state.values():
                if isinstance(v, dict):
                    result = self._find_in_state(v, key)
                    if result is not None:
                        return result
        return None

    def verify_conservation_of_identity(
        self,
        narrative_text: str,
        state_json: dict
    ) -> ValidationResult:
        """
        Primary validation function.

        Checks if the narrative conserves identity with the state.
        If narrative contradicts state, returns correction instructions.

        Args:
            narrative_text: Generated text from the model
            state_json: Ground truth state dictionary

        Returns:
            ValidationResult with verdict, scores, and corrections
        """
        # Extract claims from narrative
        claims = self.extract_claims(narrative_text)

        # Extract constraints from state
        constraints = self.extract_constraints(state_json)

        # Calculate semantic density
        density = self.calculate_semantic_density(claims, constraints, narrative_text)

        # Calculate drift and find contradictions
        drift, contradictions = self.calculate_drift_score(claims, constraints)

        # Apply Sinkhorn normalization to get balanced view
        norm_narrative, norm_state = self._sinkhorn_normalize(
            1 - drift,  # Narrative validity
            density     # State coverage
        )

        # Determine verdict
        if not contradictions:
            verdict = GuardVerdict.PASS
            correction = None
        elif self.strict_mode or drift > 0.5:
            verdict = GuardVerdict.FAIL
            correction = self.generate_correction(contradictions, narrative_text, state_json)
        else:
            verdict = GuardVerdict.CORRECT
            correction = self.generate_correction(contradictions, narrative_text, state_json)

        return ValidationResult(
            verdict=verdict,
            semantic_density=density,
            drift_score=drift,
            contradictions=contradictions,
            correction_instruction=correction,
            normalized_narrative=None  # Could be populated by Voice module
        )


# Module-level convenience function
def verify_conservation_of_identity(
    narrative_text: str,
    state_json: dict,
    strict: bool = False
) -> ValidationResult:
    """
    Validate narrative against state truth.

    Args:
        narrative_text: The generated narrative to validate
        state_json: The authoritative state dictionary
        strict: If True, any contradiction is FAIL. If False, allows CORRECT.

    Returns:
        ValidationResult with verdict and correction instructions if needed.
    """
    guard = ManifoldGuard(strict_mode=strict)
    return guard.verify_conservation_of_identity(narrative_text, state_json)


if __name__ == "__main__":
    # Self-test with example scenario
    print("C.O.D.E.X. Manifold Guard - Conservation Test")
    print("=" * 50)

    # Example state: A wizard with no spell slots
    test_state = {
        "character": {
            "name": "Aldric",
            "class": "wizard",
            "level": 5
        },
        "spell_slots": {
            "level_1": 0,
            "level_2": 0,
            "level_3": 1
        },
        "hit_points": {
            "current": 15,
            "max": 32
        },
        "inventory": ["staff", "spellbook", "potion of healing"],
        "conditions": ["exhausted"]
    }

    # Test 1: Valid narrative
    valid_narrative = "Aldric grips his staff tightly, feeling exhausted from the battle. He has one spell left."
    print("\nTest 1: Valid Narrative")
    print(f"  Input: {valid_narrative}")
    result = verify_conservation_of_identity(valid_narrative, test_state)
    print(f"  Verdict: {result.verdict.value}")
    print(f"  Density: {result.semantic_density:.2f}, Drift: {result.drift_score:.2f}")

    # Test 2: Contradicting narrative (casting with no slots)
    invalid_narrative = "I cast Fireball using my level 1 spell slot, dealing massive damage!"
    print("\nTest 2: Contradicting Narrative")
    print(f"  Input: {invalid_narrative}")
    result = verify_conservation_of_identity(invalid_narrative, test_state, strict=False)
    print(f"  Verdict: {result.verdict.value}")
    print(f"  Density: {result.semantic_density:.2f}, Drift: {result.drift_score:.2f}")
    if result.contradictions:
        print("  Contradictions:")
        for c in result.contradictions:
            print(f"    - {c}")
    if result.correction_instruction:
        print(f"\n  Correction:\n{result.correction_instruction}")

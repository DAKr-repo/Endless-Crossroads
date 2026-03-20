"""
codex.games.candela.investigations
====================================
Candela Obscura — Investigation Framework.

Provides the clue-tracking, case-management, and investigation-roll
mechanics for running a Candela Obscura investigation.

Classes:
    Clue               — A single piece of discovered evidence
    ClueTracker        — Collection manager for all clues in a case
    CaseState          — Snapshot of an active investigation's status
    InvestigationManager — Orchestrates case lifecycle and resolution

Constants:
    INVESTIGATION_METHODS  — Available investigation approaches
    ILLUMINATION_OUTCOMES  — Roll-to-outcome mapping for case resolution
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================================
# INVESTIGATION METHODS
# =========================================================================

INVESTIGATION_METHODS: Dict[str, Dict[str, str]] = {
    "survey": {
        "description": "Systematically observe an area or person for evidence.",
        "primary_action": "survey",
        "notes": "Best for scene entry and establishing clue presence.",
    },
    "focus": {
        "description": "Concentrate deeply on a specific object, text, or sensation.",
        "primary_action": "focus",
        "notes": "Best for verifying clues and interpreting occult phenomena.",
    },
    "sense": {
        "description": "Use supernatural sensitivity to detect hidden impressions.",
        "primary_action": "sense",
        "notes": "Best for Weird characters; reveals clues invisible to others.",
    },
    "sway": {
        "description": "Persuade, charm, or pressure an NPC into sharing information.",
        "primary_action": "sway",
        "notes": "Best for social investigation; may improve NPC trust.",
    },
    "read": {
        "description": "Read a person's body language, intentions, or emotional state.",
        "primary_action": "read",
        "notes": "Best for gauging NPC honesty or detecting deception.",
    },
    "hide": {
        "description": "Investigate covertly — tailing, eavesdropping, or searching unseen.",
        "primary_action": "hide",
        "notes": "Best for gathering evidence without alerting the subject.",
    },
    "strike": {
        "description": "Confront a supernatural entity or phenomenon directly.",
        "primary_action": "strike",
        "notes": "Best for danger escalation encounters; physical confrontation.",
    },
    "control": {
        "description": "Manage a volatile situation — containing, restraining, or sealing.",
        "primary_action": "control",
        "notes": "Best for ritual sealing and containing active phenomena.",
    },
    "move": {
        "description": "Navigate hazardous terrain or pursue/escape a target.",
        "primary_action": "move",
        "notes": "Best for physical investigation locations with environmental danger.",
    },
}


# =========================================================================
# ILLUMINATION OUTCOMES
# =========================================================================

ILLUMINATION_OUTCOMES: Dict[str, Dict[str, str]] = {
    "critical": {
        "label": "Complete Illumination",
        "description": (
            "The phenomenon is fully understood and neutralized. "
            "All clues are verified. The circle gains a major story benefit."
        ),
        "case_outcome": "illuminated",
        "danger_cleared": True,
    },
    "success": {
        "label": "Illumination",
        "description": (
            "The phenomenon is neutralized. The circle understands what happened "
            "and has prevented future recurrence."
        ),
        "case_outcome": "illuminated",
        "danger_cleared": True,
    },
    "mixed": {
        "label": "Partial Illumination",
        "description": (
            "The phenomenon is contained but not fully understood. "
            "It may return or leave a scar. The circle takes one consequence."
        ),
        "case_outcome": "contained",
        "danger_cleared": False,
    },
    "failure": {
        "label": "Failure to Illuminate",
        "description": (
            "The phenomenon escapes or escalates. The circle takes consequences "
            "and must retreat. Danger increases by 2."
        ),
        "case_outcome": "failed",
        "danger_cleared": False,
    },
}


# =========================================================================
# CLUE
# =========================================================================

@dataclass
class Clue:
    """A single piece of discovered evidence in a Candela investigation.

    Args:
        description:         What was found or observed.
        source:              Where or from whom the clue came.
        verified:            Whether the clue has been confirmed as accurate.
        connected_phenomena: The phenomenon key this clue links to (if known).
    """

    description: str
    source: str
    verified: bool = False
    connected_phenomena: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for save/load."""
        return {
            "description": self.description,
            "source": self.source,
            "verified": self.verified,
            "connected_phenomena": self.connected_phenomena,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Clue":
        """Deserialize from a plain dict."""
        return cls(
            description=data.get("description", ""),
            source=data.get("source", ""),
            verified=data.get("verified", False),
            connected_phenomena=data.get("connected_phenomena", ""),
        )


# =========================================================================
# CLUE TRACKER
# =========================================================================

class ClueTracker:
    """Manages the collection of clues for the current investigation.

    Provides add, verify, connect, and filter operations on the clue list.
    """

    def __init__(self) -> None:
        self.clues: List[Clue] = []

    # ── Mutation ──────────────────────────────────────────────────────────

    def add_clue(self, description: str, source: str) -> Clue:
        """Add a new unverified clue to the tracker.

        Args:
            description: What was found or observed.
            source:      Where or from whom the clue came.

        Returns:
            The newly created Clue instance.
        """
        clue = Clue(description=description, source=source)
        self.clues.append(clue)
        return clue

    def verify_clue(self, index: int) -> Dict[str, Any]:
        """Mark the clue at *index* as verified.

        Args:
            index: Zero-based index into self.clues.

        Returns:
            Dict with 'success', 'clue', and optional 'error' keys.
        """
        if index < 0 or index >= len(self.clues):
            return {"success": False, "error": f"No clue at index {index}"}
        clue = self.clues[index]
        if clue.verified:
            return {"success": False, "error": "Clue already verified", "clue": clue.to_dict()}
        clue.verified = True
        return {"success": True, "clue": clue.to_dict()}

    def connect_clue(self, index: int, phenomena: str) -> Dict[str, Any]:
        """Connect the clue at *index* to a named phenomenon.

        Args:
            index:    Zero-based index into self.clues.
            phenomena: Phenomenon key (e.g. 'crimson_weave').

        Returns:
            Dict with 'success', 'clue', and optional 'error' keys.
        """
        if index < 0 or index >= len(self.clues):
            return {"success": False, "error": f"No clue at index {index}"}
        clue = self.clues[index]
        clue.connected_phenomena = phenomena
        return {"success": True, "clue": clue.to_dict()}

    # ── Query ─────────────────────────────────────────────────────────────

    def get_unverified(self) -> List[Clue]:
        """Return all clues that have not yet been verified."""
        return [c for c in self.clues if not c.verified]

    def get_by_phenomena(self, phenomena: str) -> List[Clue]:
        """Return all clues connected to a specific phenomenon.

        Args:
            phenomena: Phenomenon key to filter by.

        Returns:
            List of matching Clue instances.
        """
        return [c for c in self.clues if c.connected_phenomena == phenomena]

    def verified_count(self) -> int:
        """Return the number of verified clues."""
        return sum(1 for c in self.clues if c.verified)

    def total_count(self) -> int:
        """Return the total number of clues."""
        return len(self.clues)

    # ── Persistence ───────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for save/load."""
        return {"clues": [c.to_dict() for c in self.clues]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClueTracker":
        """Deserialize from a plain dict."""
        tracker = cls()
        tracker.clues = [Clue.from_dict(d) for d in data.get("clues", [])]
        return tracker


# =========================================================================
# CASE STATE
# =========================================================================

@dataclass
class CaseState:
    """Snapshot of an active investigation's current status.

    Args:
        case_name:     Human-readable name for the investigation.
        phenomena:     Key of the primary phenomenon being investigated.
        clues_found:   Number of clues discovered so far.
        clues_needed:  Number of clues required to attempt illumination.
        danger_level:  Current danger level (0 = safe, 5 = catastrophic).
        active:        Whether the case is currently open.
        outcome:       Final outcome string (set when case is closed).
    """

    case_name: str
    phenomena: str = ""
    clues_found: int = 0
    clues_needed: int = 5
    danger_level: int = 0
    active: bool = True
    outcome: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for save/load."""
        return {
            "case_name": self.case_name,
            "phenomena": self.phenomena,
            "clues_found": self.clues_found,
            "clues_needed": self.clues_needed,
            "danger_level": self.danger_level,
            "active": self.active,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseState":
        """Deserialize from a plain dict."""
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


# =========================================================================
# INVESTIGATION MANAGER
# =========================================================================

class InvestigationManager:
    """Orchestrates the lifecycle of a Candela Obscura investigation.

    Manages cases, clues, trust relationships with NPCs, and the
    mechanics for investigation rolls, gilded moves, and illumination.
    """

    def __init__(self) -> None:
        self.active_case: Optional[CaseState] = None
        self.clue_tracker: ClueTracker = ClueTracker()
        self.circle_trust: Dict[str, int] = {}  # NPC name -> trust level (0-3)
        self._closed_cases: List[Dict[str, Any]] = []

    # ── Case Lifecycle ────────────────────────────────────────────────────

    def open_case(
        self,
        case_name: str,
        phenomena: str = "",
        clues_needed: int = 5,
    ) -> CaseState:
        """Open a new investigation case.

        If a case is already active it is archived before the new one opens.

        Args:
            case_name:    Human-readable name for the investigation.
            phenomena:    Key of the primary phenomenon being investigated.
            clues_needed: Number of clues required to attempt illumination.

        Returns:
            The newly created CaseState.
        """
        if self.active_case and self.active_case.active:
            self._closed_cases.append(self.active_case.to_dict())

        self.active_case = CaseState(
            case_name=case_name,
            phenomena=phenomena,
            clues_needed=max(1, clues_needed),
        )
        self.clue_tracker = ClueTracker()
        return self.active_case

    def close_case(self, outcome: str = "resolved") -> Dict[str, Any]:
        """Close the active case with the given outcome.

        Args:
            outcome: One of 'resolved', 'illuminated', 'contained', 'failed', etc.

        Returns:
            Dict summarizing the closed case.
        """
        if not self.active_case:
            return {"success": False, "error": "No active case"}

        self.active_case.active = False
        self.active_case.outcome = outcome
        summary = {
            "success": True,
            "case": self.active_case.to_dict(),
            "clues_found": self.clue_tracker.total_count(),
            "verified_clues": self.clue_tracker.verified_count(),
        }
        self._closed_cases.append(self.active_case.to_dict())
        return summary

    # ── Investigation Actions ─────────────────────────────────────────────

    def investigate(
        self,
        action_dots: int,
        method: str = "survey",
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Perform an investigation roll using the FITD d6-pool system.

        Success reveals a full clue; partial (mixed) success reveals a hint;
        failure increases the danger level.

        Args:
            action_dots: Number of d6 dice to roll (character's action rating).
            method:      Investigation method key (see INVESTIGATION_METHODS).
            rng:         Optional seeded Random for deterministic testing.

        Returns:
            Dict with outcome, clue data, and updated case status.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect

        if not self.active_case:
            return {"success": False, "error": "No active case"}

        _rng = rng or random.Random()
        roll = FITDActionRoll(
            dice_count=action_dots,
            position=Position.RISKY,
            effect=Effect.STANDARD,
        )
        result = roll.roll(_rng)

        method_info = INVESTIGATION_METHODS.get(method, INVESTIGATION_METHODS["survey"])
        response: Dict[str, Any] = {
            "method": method,
            "method_description": method_info["description"],
            "outcome": result.outcome,
            "dice": result.all_dice,
            "highest": result.highest,
        }

        if result.outcome in ("success", "critical"):
            # Full clue revealed
            clue_desc = _generate_clue_description(
                self.active_case.phenomena, method, _rng
            )
            clue = self.clue_tracker.add_clue(
                description=clue_desc,
                source=method_info["description"],
            )
            if result.outcome == "critical":
                # Critical: clue is immediately verified
                clue.verified = True
            self.active_case.clues_found += 1
            response["clue_found"] = True
            response["clue"] = clue.to_dict()
            response["message"] = (
                f"You discover: {clue_desc}"
                + (" (Verified)" if clue.verified else "")
            )

        elif result.outcome == "mixed":
            # Partial: hint only
            hint = _generate_hint(self.active_case.phenomena, method, _rng)
            response["clue_found"] = False
            response["hint"] = hint
            response["message"] = f"You glimpse something: {hint}"

        else:
            # Failure: danger escalates
            self.active_case.danger_level = min(
                5, self.active_case.danger_level + 1
            )
            response["clue_found"] = False
            response["danger_level"] = self.active_case.danger_level
            response["message"] = (
                f"Your investigation goes wrong. Danger rises to "
                f"{self.active_case.danger_level}."
            )

        response["case_status"] = self.active_case.to_dict()
        return response

    def gilded_move(
        self,
        character: Any,
        ability_name: str,
    ) -> Dict[str, Any]:
        """Use a role ability (gilded move) that costs Body/Brain/Bleed marks.

        Looks up the ability in ROLES data, applies mark costs to the character,
        and returns a result dict.

        Args:
            character:    A CandelaCharacter instance.
            ability_name: The ability name to use (case-insensitive search).

        Returns:
            Dict with success, ability info, and mark changes applied.
        """
        from codex.forge.reference_data.candela_roles import ROLES

        # Find the ability across all roles
        found_ability: Optional[Dict[str, Any]] = None
        for role_data in ROLES.values():
            for spec_data in role_data["specializations"].values():
                for ability in spec_data["abilities"]:
                    if ability["name"].lower() == ability_name.lower():
                        found_ability = ability
                        break
                if found_ability:
                    break
            if found_ability:
                break

        if not found_ability:
            return {
                "success": False,
                "error": f"Unknown ability: '{ability_name}'",
            }

        # Apply costs
        cost = found_ability.get("cost", {})
        marks_applied: Dict[str, Dict[str, Any]] = {}
        for track, amount in cost.items():
            if track in ("body", "brain", "bleed") and hasattr(character, "take_mark"):
                mark_result = character.take_mark(track, amount)
                marks_applied[track] = mark_result

        return {
            "success": True,
            "ability": found_ability,
            "marks_applied": marks_applied,
            "message": (
                f"[{found_ability['name']}] {found_ability['description']} "
                f"| Cost: {cost or 'Free'}"
            ),
        }

    def illuminate(self, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        """Attempt to illuminate (resolve) the active phenomenon.

        Requires that at least clues_needed clues have been found.
        The dice pool equals the number of verified clues.

        Args:
            rng: Optional seeded Random for deterministic testing.

        Returns:
            Dict with outcome and case resolution details.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect

        if not self.active_case:
            return {"success": False, "error": "No active case"}

        if self.active_case.clues_found < self.active_case.clues_needed:
            shortage = self.active_case.clues_needed - self.active_case.clues_found
            return {
                "success": False,
                "error": (
                    f"Insufficient clues. Need {shortage} more before illumination."
                ),
                "clues_found": self.active_case.clues_found,
                "clues_needed": self.active_case.clues_needed,
            }

        _rng = rng or random.Random()
        dice_pool = max(1, self.clue_tracker.verified_count())
        roll = FITDActionRoll(
            dice_count=dice_pool,
            position=Position.RISKY,
            effect=Effect.GREAT,
        )
        result = roll.roll(_rng)
        outcome_data = ILLUMINATION_OUTCOMES.get(
            result.outcome, ILLUMINATION_OUTCOMES["mixed"]
        )

        # Close the case with the resolved outcome
        self.active_case.active = False
        self.active_case.outcome = outcome_data["case_outcome"]
        if outcome_data.get("danger_cleared"):
            self.active_case.danger_level = 0

        return {
            "success": True,
            "roll_outcome": result.outcome,
            "dice": result.all_dice,
            "highest": result.highest,
            "illumination": outcome_data,
            "case": self.active_case.to_dict(),
        }

    def danger_escalation(self, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        """Roll when danger is high — the phenomenon may manifest.

        At Danger 3+, manifestation becomes possible.
        At Danger 5, manifestation is automatic.

        Args:
            rng: Optional seeded Random for deterministic testing.

        Returns:
            Dict with manifestation result and updated danger level.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect

        if not self.active_case:
            return {"success": False, "error": "No active case"}

        danger = self.active_case.danger_level
        _rng = rng or random.Random()

        if danger >= 5:
            # Automatic manifestation
            self.active_case.danger_level = 5
            return {
                "success": True,
                "manifested": True,
                "danger_level": danger,
                "message": (
                    "The phenomenon fully manifests! The circle must act immediately."
                ),
            }

        if danger < 3:
            return {
                "success": True,
                "manifested": False,
                "danger_level": danger,
                "message": f"Danger is {danger} — no escalation check needed yet.",
            }

        # Danger 3 or 4: roll to see if it escalates
        roll = FITDActionRoll(
            dice_count=danger,  # more danger = more dice against you
            position=Position.DESPERATE,
            effect=Effect.EXTREME,
        )
        result = roll.roll(_rng)

        if result.outcome in ("success", "critical"):
            # The phenomenon asserts itself
            self.active_case.danger_level = min(5, danger + 1)
            return {
                "success": True,
                "manifested": True,
                "danger_level": self.active_case.danger_level,
                "dice": result.all_dice,
                "message": (
                    f"The phenomenon stirs! Danger escalates to "
                    f"{self.active_case.danger_level}."
                ),
            }
        else:
            return {
                "success": True,
                "manifested": False,
                "danger_level": danger,
                "dice": result.all_dice,
                "message": f"The phenomenon holds back. Danger remains at {danger}.",
            }

    def build_trust(self, npc_name: str, action_result: str) -> Dict[str, Any]:
        """Adjust an NPC's trust level based on an investigation action result.

        Args:
            npc_name:      NPC identifier (case-insensitive).
            action_result: FITD outcome string: 'failure', 'mixed', 'success', 'critical'.

        Returns:
            Dict with NPC name, old trust, new trust, and trust level name.
        """
        from codex.forge.reference_data.candela_circles import TRUST_MECHANICS

        key = npc_name.lower()
        old_trust = self.circle_trust.get(key, 1)  # default: Cautious

        if action_result in ("success", "critical"):
            new_trust = min(3, old_trust + 1)
        elif action_result == "mixed":
            new_trust = old_trust  # no change
        else:  # failure
            new_trust = max(0, old_trust - 1)

        self.circle_trust[key] = new_trust

        # Map trust int to name
        trust_names = {0: "Suspicious", 1: "Cautious", 2: "Trusting", 3: "Bonded"}
        old_name = trust_names.get(old_trust, "Unknown")
        new_name = trust_names.get(new_trust, "Unknown")

        return {
            "npc": npc_name,
            "old_trust": old_trust,
            "old_trust_name": old_name,
            "new_trust": new_trust,
            "new_trust_name": new_name,
            "changed": old_trust != new_trust,
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full investigation state for save/load."""
        return {
            "active_case": self.active_case.to_dict() if self.active_case else None,
            "clue_tracker": self.clue_tracker.to_dict(),
            "circle_trust": self.circle_trust,
            "closed_cases": self._closed_cases,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationManager":
        """Deserialize investigation state from a plain dict."""
        mgr = cls()
        raw_case = data.get("active_case")
        if raw_case:
            mgr.active_case = CaseState.from_dict(raw_case)
        mgr.clue_tracker = ClueTracker.from_dict(data.get("clue_tracker", {}))
        mgr.circle_trust = data.get("circle_trust", {})
        mgr._closed_cases = data.get("closed_cases", [])
        return mgr


# =========================================================================
# INTERNAL HELPERS
# =========================================================================

_CLUE_TEMPLATES: Dict[str, List[str]] = {
    "crimson_weave": [
        "Crimson discoloration found in the water cistern",
        "A victim's eyes show the characteristic milky red tint",
        "Alchemical burn residue with a sulfur-copper signature detected",
        "A witness describes seeing the contamination spread upstream",
        "A still-lucid victim confirms they were compelled to seek water sources",
    ],
    "hollow_choir": [
        "Historical records show a mass casualty event at this exact location",
        "A clock in the building is running backward",
        "A witness reports experiencing vivid hallucinations of past violence",
        "Glass surfaces in the affected room show ghostly reflections",
        "Written documents contain dates that are impossible anachronisms",
    ],
    "flickering_man": [
        "A photograph shows a blurred humanoid form no one recalls being present",
        "A witness describes reliving their worst memory in vivid detail",
        "Electromagnetic interference caused all lights to strobe in rhythm",
        "A journal entry contains words the author does not remember writing",
        "A peripheral sighting that vanished on direct observation",
    ],
    "thought_plague": [
        "A witness cannot stop returning to the same conversational topic",
        "Written materials about the phenomenon have appeared in new locations",
        "An infected individual's Bleed marks have no identifiable physical cause",
        "Two early vectors attended the same social gathering three weeks ago",
        "The phenomenon grows more coherent as awareness of it spreads",
    ],
    "pale_door": [
        "A pale white door has appeared in an architecturally impossible location",
        "A returned individual refuses to describe what they saw inside",
        "A photograph of the door came out entirely white",
        "A previous Pale Door scar is located 200 yards from the current manifestation",
        "A witness reports an overpowering sense of compulsion to open the door",
    ],
    "_default": [
        "Physical evidence found at the primary scene",
        "A witness account corroborating earlier observations",
        "Documentary evidence in a relevant archive",
        "Trace evidence with supernatural properties",
        "A direct encounter that confirms the phenomenon's nature",
    ],
}

_HINT_TEMPLATES: List[str] = [
    "Something is wrong here, but you cannot pin it down yet",
    "A detail catches your eye but its significance eludes you",
    "You sense a pattern but lack the evidence to confirm it",
    "A witness says something that may be relevant — or may not be",
    "The scene suggests prior activity, but the trail is cold",
]


def _generate_clue_description(
    phenomena: str,
    method: str,
    rng: random.Random,
) -> str:
    """Select a clue description for the given phenomenon and method.

    Args:
        phenomena: Phenomenon key (may be empty).
        method:    Investigation method used.
        rng:       Seeded Random for reproducibility.

    Returns:
        A string clue description.
    """
    pool = _CLUE_TEMPLATES.get(phenomena, _CLUE_TEMPLATES["_default"])
    return rng.choice(pool)


def _generate_hint(
    phenomena: str,
    method: str,
    rng: random.Random,
) -> str:
    """Select a vague hint for a mixed investigation result.

    Args:
        phenomena: Phenomenon key (currently unused but reserved for extension).
        method:    Investigation method used (reserved for extension).
        rng:       Seeded Random for reproducibility.

    Returns:
        A string hint.
    """
    return rng.choice(_HINT_TEMPLATES)


# =========================================================================
# PHENOMENA TRACKER
# =========================================================================

@dataclass
class PhenomenaTracker:
    """4-stage phenomena escalation clock: dormant -> stirring -> active -> consuming.

    Tracks how close a supernatural phenomenon is to fully manifesting.
    Each tick advances the clock; enough ticks in a stage push it to the next.
    Successful containment actions can reduce the tick count.
    """

    STAGES = ["dormant", "stirring", "active", "consuming"]

    stage: str = "dormant"
    escalation_ticks: int = 0
    escalation_threshold: int = 4  # Ticks needed to advance stage
    phenomena_name: str = ""

    def tick(self, amount: int = 1) -> dict:
        """Add escalation ticks. Advances stage when threshold is reached.

        Args:
            amount: Number of ticks to add. Default 1.

        Returns:
            Dict with old_stage, new_stage, advanced bool, current ticks,
            and threshold.
        """
        old_stage = self.stage
        self.escalation_ticks += amount
        advanced = False
        while self.escalation_ticks >= self.escalation_threshold:
            idx = self.STAGES.index(self.stage)
            if idx < len(self.STAGES) - 1:
                self.stage = self.STAGES[idx + 1]
                self.escalation_ticks -= self.escalation_threshold
                advanced = True
            else:
                # Already at consuming — cap ticks
                self.escalation_ticks = self.escalation_threshold
                break
        return {
            "old_stage": old_stage,
            "new_stage": self.stage,
            "advanced": advanced,
            "ticks": self.escalation_ticks,
            "threshold": self.escalation_threshold,
        }

    def reduce(self, amount: int = 1) -> dict:
        """Reduce escalation ticks (from successful containment).

        Args:
            amount: Number of ticks to remove. Default 1. Floors at 0.

        Returns:
            Dict with old_ticks, new_ticks, and current stage.
        """
        old_ticks = self.escalation_ticks
        self.escalation_ticks = max(0, self.escalation_ticks - amount)
        return {
            "old_ticks": old_ticks,
            "new_ticks": self.escalation_ticks,
            "stage": self.stage,
        }

    def get_status(self) -> str:
        """Human-readable status line for the phenomena tracker.

        Returns:
            Multi-line string showing name, stage, ticks, and stage ladder.
        """
        return (
            f"Phenomena: {self.phenomena_name or 'Unknown'}\n"
            f"Stage: {self.stage.upper()} ({self.escalation_ticks}/{self.escalation_threshold})\n"
            f"Stages: {' -> '.join(s.upper() if s == self.stage else s for s in self.STAGES)}"
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict for save/load."""
        return {
            "stage": self.stage,
            "escalation_ticks": self.escalation_ticks,
            "escalation_threshold": self.escalation_threshold,
            "phenomena_name": self.phenomena_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PhenomenaTracker":
        """Deserialize from a plain dict.

        Args:
            data: Dict previously produced by to_dict().

        Returns:
            Reconstructed PhenomenaTracker instance.
        """
        return cls(
            stage=data.get("stage", "dormant"),
            escalation_ticks=data.get("escalation_ticks", 0),
            escalation_threshold=data.get("escalation_threshold", 4),
            phenomena_name=data.get("phenomena_name", ""),
        )


__all__ = [
    "INVESTIGATION_METHODS",
    "ILLUMINATION_OUTCOMES",
    "Clue",
    "ClueTracker",
    "CaseState",
    "InvestigationManager",
    "PhenomenaTracker",
]

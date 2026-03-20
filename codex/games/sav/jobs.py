"""
codex.games.sav.jobs — Job phase management for Scum & Villainy.

Manages the full job lifecycle (SaV's equivalent of BitD's scores):
  - Engagement rolls
  - Job state tracking
  - Complication management
  - Job resolution (cred, rep, heat)
  - Hyperspace jump planning
  - Pre-engagement planning phase
"""

import random
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional


# =========================================================================
# CONSTANTS
# =========================================================================

PLAN_TYPES: Dict[str, str] = {
    "assault":      "Direct attack. Go in loud and take what you need by force.",
    "deception":    "Misdirection and false pretenses. Make them think you're someone else.",
    "infiltration": "Stealth insertion. Get in, get out, don't be seen.",
    "mystic":       "Void-touched approach. Use attunement to bypass normal obstacles.",
    "social":       "Negotiation and schmoozing. Talk your way to your goal.",
    "transport":    "Move something or someone from A to B. Simple logistics, complex execution.",
}

ENGAGEMENT_OUTCOMES: Dict[str, str] = {
    "critical":  "Ideal engagement — you start in a controlled position with elevated effect.",
    "success":   "Clean engagement — you start in a controlled position.",
    "mixed":     "Messy engagement — you start in a risky position or with a complication.",
    "failure":   "Desperate engagement — you start in a desperate position with a complication.",
}

HEAT_BY_TARGET_TIER: Dict[int, int] = {
    1: 1,
    2: 2,
    3: 2,
    4: 3,
    5: 3,
}

REP_BY_TARGET_TIER: Dict[int, int] = {
    1: 1,
    2: 1,
    3: 2,
    4: 2,
    5: 3,
}

CRED_BY_TARGET_TIER: Dict[int, int] = {
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
}

# Jump planning outcomes
JUMP_OUTCOMES: Dict[str, str] = {
    "mishap":    "Jump mishap — you arrive off-target, damaged, or with a complication.",
    "clean":     "Clean jump — you arrive at the destination without incident.",
    "excellent": "Excellent jump — you arrive early with bonus time or favorable positioning.",
}


# =========================================================================
# PLANNING PHASE
# =========================================================================

@dataclass
class PlanningPhase:
    """Pre-engagement planning phase for SaV jobs.

    Allows the crew to choose an approach and specific detail before
    the engagement roll, potentially earning a bonus die.

    Attributes:
        plan_type: The approach type (assault/deception/infiltration/mystic/social/transport).
        detail: A specific actionable detail that grants the engagement bonus.
        loadout: Equipment load chosen for the job (light/normal/heavy).
        completed: Whether a plan has been set.
    """

    plan_type: str = ""
    detail: str = ""
    loadout: str = "normal"
    completed: bool = False

    VALID_PLANS: ClassVar[List[str]] = [
        "assault", "deception", "infiltration", "mystic", "social", "transport"
    ]

    def set_plan(self, plan_type: str, detail: str = "") -> dict:
        """Set the plan type and optional detail.

        Args:
            plan_type: Must be one of VALID_PLANS.
            detail: Specific actionable context for the engagement bonus.

        Returns:
            Dict with success bool and plan_type/detail on success, or error on failure.
        """
        if plan_type.lower() not in self.VALID_PLANS:
            return {
                "success": False,
                "error": f"Invalid plan type. Valid: {', '.join(self.VALID_PLANS)}",
            }
        self.plan_type = plan_type.lower()
        self.detail = detail
        self.completed = True
        return {"success": True, "plan_type": self.plan_type, "detail": self.detail}

    def to_dict(self) -> dict:
        """Serialize to plain dict for save/load."""
        return {
            "plan_type": self.plan_type,
            "detail": self.detail,
            "loadout": self.loadout,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlanningPhase":
        """Deserialize from a plain dict.

        Args:
            data: Dict from a previous to_dict() call.

        Returns:
            Restored PlanningPhase instance.
        """
        return cls(
            plan_type=data.get("plan_type", ""),
            detail=data.get("detail", ""),
            loadout=data.get("loadout", "normal"),
            completed=data.get("completed", False),
        )


# =========================================================================
# JOB STATE
# =========================================================================

@dataclass
class JobState:
    """Tracks the state of an active or completed job.

    Attributes:
        target: Who or what the job targets.
        plan_type: The approach the crew selected.
        detail: Additional context for the plan (location, timing, etc.).
        engagement_result: Outcome of the engagement roll.
        active: Whether the job is currently in progress.
        complications: List of complication descriptions that arose.
        gambits_used: Number of gambits spent during the job.
        heat_generated: Heat generated by this job.
        rep_earned: Rep earned from this job.
        cred_earned: Cred earned from this job.
    """

    target: str = ""
    plan_type: str = "assault"
    detail: str = ""
    engagement_result: str = ""
    active: bool = False
    complications: List[str] = field(default_factory=list)
    gambits_used: int = 0
    heat_generated: int = 0
    rep_earned: int = 0
    cred_earned: int = 0

    def to_dict(self) -> dict:
        """Serialize to plain dict for save/load."""
        return {
            "target": self.target,
            "plan_type": self.plan_type,
            "detail": self.detail,
            "engagement_result": self.engagement_result,
            "active": self.active,
            "complications": list(self.complications),
            "gambits_used": self.gambits_used,
            "heat_generated": self.heat_generated,
            "rep_earned": self.rep_earned,
            "cred_earned": self.cred_earned,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobState":
        """Deserialize from a plain dict.

        Args:
            data: Dict from a previous to_dict() call.

        Returns:
            Restored JobState instance.
        """
        return cls(
            target=data.get("target", ""),
            plan_type=data.get("plan_type", "assault"),
            detail=data.get("detail", ""),
            engagement_result=data.get("engagement_result", ""),
            active=data.get("active", False),
            complications=list(data.get("complications", [])),
            gambits_used=data.get("gambits_used", 0),
            heat_generated=data.get("heat_generated", 0),
            rep_earned=data.get("rep_earned", 0),
            cred_earned=data.get("cred_earned", 0),
        )


# =========================================================================
# JOB PHASE MANAGER
# =========================================================================

class JobPhaseManager:
    """Manages the full job lifecycle for a Scum & Villainy crew.

    Handles engagement rolls, complication tracking, and job resolution.
    """

    def __init__(self) -> None:
        """Initialize with no active job."""
        self._current_job: Optional[JobState] = None

    @property
    def current_job(self) -> Optional[JobState]:
        """The currently active job state, or None."""
        return self._current_job

    def job_engagement_roll(
        self,
        crew_tier: int = 1,
        plan_type: str = "assault",
        detail_bonus: int = 0,
        misc_bonus: int = 0,
        misc_penalty: int = 0,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """Roll the engagement roll to determine starting position for a job.

        Args:
            crew_tier: The crew's current tier (1-4), used as base dice.
            plan_type: The selected plan type key from PLAN_TYPES.
            detail_bonus: Bonus dice from specific, actionable detail (+1d).
            misc_bonus: Other bonus dice (from allies, prep, etc.).
            misc_penalty: Penalty dice to subtract.
            rng: Optional seeded Random for deterministic tests.

        Returns:
            Dict with outcome, description, dice, highest, and starting_position.
        """
        _rng = rng or random.Random()
        base_dice = max(0, crew_tier + detail_bonus + misc_bonus - misc_penalty)

        if base_dice <= 0:
            rolled = sorted([_rng.randint(1, 6) for _ in range(2)])
            highest = rolled[0]
        else:
            rolled = [_rng.randint(1, 6) for _ in range(base_dice)]
            highest = max(rolled)

        sixes = rolled.count(6)

        if sixes >= 2:
            outcome = "critical"
            starting_position = "controlled"
        elif highest == 6:
            outcome = "success"
            starting_position = "controlled"
        elif highest >= 4:
            outcome = "mixed"
            starting_position = "risky"
        else:
            outcome = "failure"
            starting_position = "desperate"

        plan_desc = PLAN_TYPES.get(plan_type, "Unknown plan type.")
        outcome_desc = ENGAGEMENT_OUTCOMES.get(outcome, "Unknown outcome.")

        return {
            "outcome": outcome,
            "dice": rolled,
            "highest": highest,
            "critical": sixes >= 2,
            "starting_position": starting_position,
            "plan_type": plan_type,
            "plan_description": plan_desc,
            "description": outcome_desc,
        }

    def start_job(self, target: str, plan_type: str = "assault") -> JobState:
        """Initialize a new job and set it as the active job.

        Args:
            target: The job's target (faction, person, location).
            plan_type: The approach the crew will use.

        Returns:
            Newly created JobState.
        """
        job = JobState(
            target=target,
            plan_type=plan_type,
            active=True,
        )
        self._current_job = job
        return job

    def add_complication(self, description: str) -> None:
        """Record a complication arising during the active job.

        Args:
            description: Human-readable description of the complication.
        """
        if self._current_job is not None:
            self._current_job.complications.append(description)

    def resolve_job(
        self,
        job: Optional[JobState] = None,
        crew_tier: int = 1,
        target_tier: int = 2,
    ) -> dict:
        """Resolve the active job and calculate rewards.

        Cred, rep, and heat are determined by target tier.
        Complications reduce rep earned.

        Args:
            job: The JobState to resolve (defaults to current_job).
            crew_tier: The crew's tier (affects heat calculation).
            target_tier: The target's power tier (1-5).

        Returns:
            Dict with cred, rep, heat, complications, summary string.
        """
        target_job = job or self._current_job
        if target_job is None:
            return {"error": "No active job to resolve.", "cred": 0, "rep": 0, "heat": 0}

        t = max(1, min(5, target_tier))
        base_cred = CRED_BY_TARGET_TIER.get(t, 2)
        base_rep = REP_BY_TARGET_TIER.get(t, 1)
        base_heat = HEAT_BY_TARGET_TIER.get(t, 1)

        # Complications reduce rep
        complication_penalty = min(base_rep, len(target_job.complications))
        final_rep = max(0, base_rep - complication_penalty)

        # Heat increases with number of complications (messier = more exposure)
        final_heat = base_heat + len(target_job.complications)

        target_job.cred_earned = base_cred
        target_job.rep_earned = final_rep
        target_job.heat_generated = final_heat
        target_job.active = False

        complication_summary = ""
        if target_job.complications:
            complication_summary = f" Complications: {'; '.join(target_job.complications)}."

        summary = (
            f"Job against {target_job.target} resolved. "
            f"+{base_cred} cred, +{final_rep} rep, +{final_heat} heat."
            + complication_summary
        )

        self._current_job = None

        return {
            "cred": base_cred,
            "rep": final_rep,
            "heat": final_heat,
            "complications": list(target_job.complications),
            "summary": summary,
        }

    def to_dict(self) -> dict:
        """Serialize manager state for save/load."""
        return {
            "current_job": self._current_job.to_dict() if self._current_job else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobPhaseManager":
        """Deserialize manager state from a saved dict.

        Args:
            data: Dict from a previous to_dict() call.

        Returns:
            Restored JobPhaseManager instance.
        """
        manager = cls()
        job_data = data.get("current_job")
        if job_data:
            manager._current_job = JobState.from_dict(job_data)
        return manager


# =========================================================================
# JUMP PLANNING
# =========================================================================

def jump_planning(
    destination: str,
    nav_dots: int = 0,
    rng: Optional[random.Random] = None,
) -> dict:
    """Roll for a hyperspace jump to the destination.

    Mishap on 1-3, clean on 4-5, excellent on 6+.
    Uses nav_dots (helm action) as dice pool.

    Args:
        destination: Target system or sector name.
        nav_dots: Pilot's helm action dots (0-4).
        rng: Optional seeded Random for deterministic tests.

    Returns:
        Dict with outcome, dice, highest, critical, destination, description.
    """
    _rng = rng or random.Random()
    total_dice = max(0, nav_dots)

    if total_dice <= 0:
        rolled = sorted([_rng.randint(1, 6) for _ in range(2)])
        highest = rolled[0]
    else:
        rolled = [_rng.randint(1, 6) for _ in range(total_dice)]
        highest = max(rolled)

    sixes = rolled.count(6)

    if sixes >= 2:
        outcome = "excellent"
        description = JUMP_OUTCOMES["excellent"]
    elif highest >= 6:
        outcome = "excellent"
        description = JUMP_OUTCOMES["excellent"]
    elif highest >= 4:
        outcome = "clean"
        description = JUMP_OUTCOMES["clean"]
    else:
        outcome = "mishap"
        description = JUMP_OUTCOMES["mishap"]

    return {
        "outcome": outcome,
        "dice": rolled,
        "highest": highest,
        "critical": sixes >= 2,
        "destination": destination,
        "description": description,
        "mishap": outcome == "mishap",
    }

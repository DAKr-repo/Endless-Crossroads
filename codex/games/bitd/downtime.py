"""
codex.games.bitd.downtime
===========================
Downtime subsystem for Blades in the Dark.

Handles the downtime phase: vice indulgence, long-term projects,
asset acquisition, heat reduction, recovery, and training.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random


@dataclass
class LongTermProject:
    """A long-term project tracked via a progress clock."""

    name: str
    description: str = ""
    clock_size: int = 8       # 4, 6, or 8 segments
    ticks: int = 0
    complete: bool = False

    def tick(self, amount: int = 1) -> int:
        """Add ticks to the project clock, capped at clock_size.

        Args:
            amount: Number of ticks to add.

        Returns:
            The actual number of ticks added (may be less if near completion).
        """
        added = min(amount, self.clock_size - self.ticks)
        self.ticks += added
        if self.ticks >= self.clock_size:
            self.complete = True
        return added

    def to_dict(self) -> dict:
        """Serialize to a plain dict for persistence."""
        return {
            "name": self.name,
            "description": self.description,
            "clock_size": self.clock_size,
            "ticks": self.ticks,
            "complete": self.complete,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LongTermProject":
        """Deserialize from a plain dict."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            clock_size=data.get("clock_size", 8),
            ticks=data.get("ticks", 0),
            complete=data.get("complete", False),
        )


# Roll result -> ticks earned on a clock
DOWNTIME_RESULT_TICKS = {
    1: 1,   # 1-3: 1 tick
    2: 1,
    3: 1,
    4: 2,   # 4-5: 2 ticks
    5: 2,
    6: 3,   # 6: 3 ticks
    7: 5,   # Critical: 5 ticks
}


class DowntimeManager:
    """Manages the downtime phase between scores.

    Each PC gets 2 downtime activities (+ bonus from abilities).
    Available activities: vice, project, acquire_asset, reduce_heat,
    recover, train, craft.
    """

    ACTIVITIES = [
        "vice", "project", "acquire_asset", "reduce_heat",
        "recover", "train", "craft",
    ]

    def __init__(self):
        self.projects: Dict[str, LongTermProject] = {}
        self.downtime_log: List[Dict[str, Any]] = []
        self.activities_remaining: int = 2

    def reset_activities(self, bonus: int = 0) -> None:
        """Reset available downtime activities for a new downtime phase.

        Args:
            bonus: Extra activities granted by special abilities.
        """
        self.activities_remaining = 2 + bonus
        self.downtime_log = []

    def _spend_activity(self) -> bool:
        """Spend one activity. Returns False if none remaining."""
        if self.activities_remaining <= 0:
            return False
        self.activities_remaining -= 1
        return True

    def vice_roll(
        self,
        character_name: str,
        vice_name: str = "",
        lowest_attribute: int = 1,
        stress_clock: Optional[Any] = None,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Roll for vice indulgence during downtime.

        Recovery = roll result. If recovery > stress, overindulgence occurs.
        Overindulgence: Brag, Lost, Tapped, Attracted Trouble.

        Args:
            character_name: Who is indulging.
            vice_name: Name of the vice.
            lowest_attribute: Lowest attribute rating (sets dice pool).
            stress_clock: Optional StressClock to modify.
            rng: Random number generator for deterministic tests.

        Returns:
            Dict with recovery amount, overindulgence status, and description.
        """
        if not self._spend_activity():
            return {"error": "No downtime activities remaining."}

        _rng = rng or random.Random()
        pool = max(1, lowest_attribute)
        dice = [_rng.randint(1, 6) for _ in range(pool)]
        highest = max(dice)

        current_stress = 0
        if stress_clock:
            current_stress = stress_clock.current_stress

        recovery = highest
        overindulged = recovery > current_stress and current_stress > 0

        if stress_clock:
            info = stress_clock.recover(recovery)
        else:
            info = {"recovered": recovery}

        overindulgence_type = ""
        if overindulged:
            types = ["Brag", "Lost", "Tapped", "Attracted Trouble"]
            overindulgence_type = _rng.choice(types)

        result = {
            "character": character_name,
            "vice": vice_name,
            "dice": dice,
            "highest": highest,
            "recovery": recovery,
            "overindulged": overindulged,
            "overindulgence_type": overindulgence_type,
            "description": (
                f"{character_name} indulges in {vice_name or 'vice'}. "
                f"Roll: {highest} (from {dice}). Recovered {info.get('recovered', recovery)} stress."
                + (f" OVERINDULGENCE: {overindulgence_type}!" if overindulged else "")
            ),
        }
        self.downtime_log.append({"activity": "vice", "result": result})
        return result

    def work_on_project(
        self,
        project_name: str,
        action_dots: int = 1,
        bonus: int = 0,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Work on a long-term project during downtime.

        Roll action dots. Result determines ticks on the project clock.

        Args:
            project_name: Name of an existing project.
            action_dots: The character's relevant action rating.
            bonus: Extra bonus dice from abilities or help.
            rng: Random number generator for deterministic tests.

        Returns:
            Dict with ticks_added, project state, and completion status.
        """
        if not self._spend_activity():
            return {"error": "No downtime activities remaining."}

        _rng = rng or random.Random()
        project = self.projects.get(project_name)
        if not project:
            return {"error": f"No project named '{project_name}'. Create one first."}

        pool = max(0, action_dots + bonus)
        if pool == 0:
            dice = sorted([_rng.randint(1, 6), _rng.randint(1, 6)])
            highest = dice[0]  # Take lowest of 2 (disadvantage)
            critical = False
        else:
            dice = [_rng.randint(1, 6) for _ in range(pool)]
            highest = max(dice)
            critical = dice.count(6) >= 2

        result_key = 7 if critical else min(6, highest)
        ticks = DOWNTIME_RESULT_TICKS.get(result_key, 1)
        added = project.tick(ticks)

        result = {
            "project": project_name,
            "dice": dice,
            "highest": highest,
            "critical": critical,
            "ticks_added": added,
            "progress": f"{project.ticks}/{project.clock_size}",
            "complete": project.complete,
            "description": (
                f"Work on '{project_name}': Roll {highest} -> +{added} ticks "
                f"({project.ticks}/{project.clock_size})"
                + (" -- PROJECT COMPLETE!" if project.complete else "")
            ),
        }
        self.downtime_log.append({"activity": "project", "result": result})
        return result

    def create_project(self, name: str, description: str = "", clock_size: int = 8) -> LongTermProject:
        """Create a new long-term project.

        Args:
            name: Unique name for this project.
            description: What the project accomplishes.
            clock_size: Number of segments (clamped to 4-12).

        Returns:
            The newly created LongTermProject.
        """
        project = LongTermProject(
            name=name,
            description=description,
            clock_size=max(4, min(12, clock_size)),
        )
        self.projects[name] = project
        return project

    def acquire_asset(
        self,
        crew_tier: int = 0,
        quality_desired: int = 1,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Acquire a temporary asset during downtime.

        Roll crew's Tier. Result determines the quality of the asset obtained.

        Args:
            crew_tier: The crew's current tier rating.
            quality_desired: The quality level the crew wants to acquire.
            rng: Random number generator for deterministic tests.

        Returns:
            Dict with asset quality and description.
        """
        if not self._spend_activity():
            return {"error": "No downtime activities remaining."}

        _rng = rng or random.Random()
        pool = max(1, crew_tier)
        dice = [_rng.randint(1, 6) for _ in range(pool)]
        highest = max(dice)
        critical = dice.count(6) >= 2

        if critical:
            quality = quality_desired + 1
        elif highest >= 6:
            quality = quality_desired
        elif highest >= 4:
            quality = max(0, quality_desired - 1)
        else:
            quality = max(0, quality_desired - 2)

        result = {
            "dice": dice,
            "highest": highest,
            "critical": critical,
            "quality_desired": quality_desired,
            "quality_obtained": quality,
            "description": (
                f"Acquire asset: Roll {highest} -> Quality {quality} asset obtained"
                + (" (Critical!)" if critical else "")
                + ("" if quality >= quality_desired else f" (wanted quality {quality_desired})")
            ),
        }
        self.downtime_log.append({"activity": "acquire_asset", "result": result})
        return result

    def reduce_heat(
        self,
        crew_tier: int = 0,
        bonus: int = 0,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Spend a downtime activity to reduce heat.

        Roll with crew's tier. Reduce heat by 1 on 1-3, by 2 on 4-5,
        by 3 on 6, by 5 on crit.

        Args:
            crew_tier: The crew's current tier rating.
            bonus: Additional bonus dice.
            rng: Random number generator for deterministic tests.

        Returns:
            Dict with heat reduction amount and description.
        """
        if not self._spend_activity():
            return {"error": "No downtime activities remaining."}

        _rng = rng or random.Random()
        pool = max(1, crew_tier + bonus)
        dice = [_rng.randint(1, 6) for _ in range(pool)]
        highest = max(dice)
        critical = dice.count(6) >= 2

        result_key = 7 if critical else min(6, highest)
        reduction = DOWNTIME_RESULT_TICKS.get(result_key, 1)

        result = {
            "dice": dice,
            "highest": highest,
            "critical": critical,
            "heat_reduced": reduction,
            "description": (
                f"Reduce heat: Roll {highest} -> -{reduction} heat"
                + (" (Critical!)" if critical else "")
            ),
        }
        self.downtime_log.append({"activity": "reduce_heat", "result": result})
        return result

    def recover(
        self,
        healer_dots: int = 0,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Recover from harm during downtime.

        Roll healer's Tinker/Physicker dots. Result fills healing clock segments.

        Args:
            healer_dots: The healer's relevant action rating.
            rng: Random number generator for deterministic tests.

        Returns:
            Dict with healing segments filled and description.
        """
        if not self._spend_activity():
            return {"error": "No downtime activities remaining."}

        _rng = rng or random.Random()
        pool = max(1, healer_dots)
        dice = [_rng.randint(1, 6) for _ in range(pool)]
        highest = max(dice)
        critical = dice.count(6) >= 2

        result_key = 7 if critical else min(6, highest)
        segments = DOWNTIME_RESULT_TICKS.get(result_key, 1)

        result = {
            "dice": dice,
            "highest": highest,
            "critical": critical,
            "segments_healed": segments,
            "description": (
                f"Recovery: Roll {highest} -> {segments} healing clock segment(s) filled"
                + (" (Critical!)" if critical else "")
            ),
        }
        self.downtime_log.append({"activity": "recover", "result": result})
        return result

    def train(self, attribute: str = "") -> Dict[str, Any]:
        """Train during downtime — mark XP in a single attribute.

        Args:
            attribute: Which attribute to train
                       (insight, prowess, resolve, playbook).

        Returns:
            Dict with attribute trained and xp_gained.
        """
        if not self._spend_activity():
            return {"error": "No downtime activities remaining."}

        valid = ["insight", "prowess", "resolve", "playbook"]
        attr = attribute.lower() if attribute else "playbook"
        if attr not in valid:
            attr = "playbook"

        result = {
            "attribute": attr,
            "xp_gained": 1,
            "description": f"Training: +1 XP in {attr}.",
        }
        self.downtime_log.append({"activity": "train", "result": result})
        return result

    def get_log_summary(self) -> str:
        """Return a text summary of all downtime activities performed."""
        if not self.downtime_log:
            return "No downtime activities performed yet."
        lines = [f"Downtime Summary ({len(self.downtime_log)} activities):"]
        for entry in self.downtime_log:
            desc = entry.get("result", {}).get("description", str(entry))
            lines.append(f"  - {desc}")
        lines.append(f"Activities remaining: {self.activities_remaining}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for persistence."""
        return {
            "projects": {k: v.to_dict() for k, v in self.projects.items()},
            "downtime_log": list(self.downtime_log),
            "activities_remaining": self.activities_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DowntimeManager":
        """Deserialize from a plain dict."""
        mgr = cls()
        mgr.projects = {
            k: LongTermProject.from_dict(v)
            for k, v in data.get("projects", {}).items()
        }
        mgr.downtime_log = data.get("downtime_log", [])
        mgr.activities_remaining = data.get("activities_remaining", 2)
        return mgr

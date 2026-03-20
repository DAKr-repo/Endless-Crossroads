"""
codex/games/sav/downtime.py — SaV Downtime Activities
======================================================
Mirrors BitD's downtime.py pattern for Scum & Villainy.

Each activity returns a plain dict so callers can format output themselves.
No Rich or terminal output here — pure game logic.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SaVDowntimeManager:
    """Manages downtime activities for Scum & Villainy.

    Tracks long-term project clocks between sessions.
    All roll methods accept an optional seeded rng for deterministic tests.

    Attributes:
        projects: Dict of project name -> progress dict for long-term clocks.
    """

    projects: Dict[str, dict] = field(default_factory=dict)

    def acquire_asset(self, crew_tier: int = 0, quality_desired: int = 1, rng: Optional[random.Random] = None) -> dict:
        """Roll to acquire a temporary asset.

        Args:
            crew_tier: The crew's current tier (used as dice pool).
            quality_desired: The asset quality the crew wants (1-4).
            rng: Optional seeded Random for deterministic tests.

        Returns:
            Dict with success, quality, dice, description.
        """
        _rng = rng or random.Random()
        dice = max(1, crew_tier)
        rolls = [_rng.randint(1, 6) for _ in range(dice)]
        highest = max(rolls)
        quality = min(quality_desired, highest // 2 + 1)
        return {
            "success": highest >= 4,
            "quality": quality,
            "dice": rolls,
            "description": (
                f"Asset acquired (quality {quality})" if highest >= 4 else "Failed to acquire asset"
            ),
        }

    def recover(self, healer_dots: int = 0, rng: Optional[random.Random] = None) -> dict:
        """Recover from harm during downtime.

        Args:
            healer_dots: The healer's stitch/doctor action dots (0-4).
            rng: Optional seeded Random for deterministic tests.

        Returns:
            Dict with levels_healed, dice, description.
        """
        _rng = rng or random.Random()
        dice = max(1, healer_dots)
        rolls = [_rng.randint(1, 6) for _ in range(dice)]
        highest = max(rolls)
        if highest == 6:
            levels_healed = 2
        elif highest >= 4:
            levels_healed = 1
        else:
            levels_healed = 0
        return {
            "levels_healed": levels_healed,
            "dice": rolls,
            "description": (
                f"Healed {levels_healed} harm level(s)" if levels_healed else "Recovery unsuccessful"
            ),
        }

    def vice_indulgence(self, rng: Optional[random.Random] = None) -> dict:
        """Indulge vice for stress relief.

        A single d6 roll determines stress recovered.
        Rolling 6 triggers overindulgence.

        Args:
            rng: Optional seeded Random for deterministic tests.

        Returns:
            Dict with stress_recovered, overindulged, dice, description.
        """
        _rng = rng or random.Random()
        roll = _rng.randint(1, 6)
        overindulged = roll == 6
        return {
            "stress_recovered": roll,
            "overindulged": overindulged,
            "dice": [roll],
            "description": (
                f"Vice indulgence: recovered {roll} stress"
                + (" — OVERINDULGENCE!" if overindulged else "")
            ),
        }

    def long_term_project(
        self,
        project_name: str,
        action_dots: int = 1,
        clock_size: int = 8,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """Work on a long-term project clock.

        Creates the project if it doesn't exist yet. Ticks are awarded based
        on the highest die: 1-3 = 1 tick, 4-5 = 2 ticks, 6 = 3 ticks.

        Args:
            project_name: Unique name identifying this project.
            action_dots: Relevant action dots used for the roll.
            clock_size: Total clock segments (4, 6, or 8 — default 8).
            rng: Optional seeded Random for deterministic tests.

        Returns:
            Dict with project, ticks, progress, size, completed, dice, description.
        """
        _rng = rng or random.Random()
        if project_name not in self.projects:
            self.projects[project_name] = {
                "progress": 0,
                "size": clock_size,
                "description": "",
            }
        project = self.projects[project_name]
        dice = max(1, action_dots)
        rolls = [_rng.randint(1, 6) for _ in range(dice)]
        highest = max(rolls)
        if highest == 6:
            ticks = 3
        elif highest >= 4:
            ticks = 2
        else:
            ticks = 1
        project["progress"] = min(project["size"], project["progress"] + ticks)
        completed = project["progress"] >= project["size"]
        return {
            "project": project_name,
            "ticks": ticks,
            "progress": project["progress"],
            "size": project["size"],
            "completed": completed,
            "dice": rolls,
            "description": (
                f"Project '{project_name}': +{ticks} ticks ({project['progress']}/{project['size']})"
                + (" — COMPLETED!" if completed else "")
            ),
        }

    def train(self, attribute: str = "playbook", rng: Optional[random.Random] = None) -> dict:
        """Train for XP in an attribute during downtime.

        Training always grants 1 XP mark (no roll required in SaV).

        Args:
            attribute: The attribute to mark XP in (playbook/insight/prowess/resolve).
            rng: Accepted for interface consistency; not used.

        Returns:
            Dict with attribute, xp_gained, description.
        """
        return {
            "attribute": attribute,
            "xp_gained": 1,
            "description": f"Training: gained 1 XP mark in {attribute}",
        }

    def to_dict(self) -> dict:
        """Serialize to plain dict for save/load."""
        return {"projects": dict(self.projects)}

    @classmethod
    def from_dict(cls, data: dict) -> "SaVDowntimeManager":
        """Deserialize from a plain dict.

        Args:
            data: Dict from a previous to_dict() call.

        Returns:
            Restored SaVDowntimeManager instance.
        """
        return cls(projects=dict(data.get("projects", {})))

"""
codex.games.bob.missions
==========================
Mission resolution subsystem for Band of Blades.

Handles mission planning, FITD engagement rolls adapted for military
operations, casualty rolls, and outcome resolution.

Classes:
    MissionReward   — Structured results of a successful mission.
    MissionResolver — Plans and resolves missions end-to-end.

Constants:
    MISSION_DIFFICULTY_TABLE — Maps (mission_type, pressure_level) to difficulty.
    CASUALTY_TABLE           — Maps roll result to casualty outcomes.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================================
# DIFFICULTY TABLE
# =========================================================================

# Maps (mission_type, pressure_level) -> difficulty modifier added to base
# Base difficulty comes from MISSION_TYPES in bob_legion.py
# Pressure (0-5) adds extra challenge
MISSION_DIFFICULTY_TABLE: Dict[str, Dict[int, int]] = {
    "Assault":   {0: 0, 1: 0, 2: 1, 3: 1, 4: 2, 5: 3},
    "Recon":     {0: 0, 1: 0, 2: 1, 3: 1, 4: 2, 5: 2},
    "Religious": {0: 0, 1: 0, 2: 0, 3: 1, 4: 2, 5: 3},
    "Supply":    {0: 0, 1: 0, 2: 1, 3: 1, 4: 2, 5: 2},
    "Rescue":    {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3},
    "Skirmish":  {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 2},
}

# =========================================================================
# CASUALTY TABLE
# =========================================================================

# Maps engagement roll result -> casualty outcome
# Keys: "critical", "success", "mixed", "failure"
CASUALTY_TABLE: Dict[str, Dict[str, Any]] = {
    "critical": {
        "label": "Minimal Casualties",
        "description": "The mission succeeds brilliantly. No significant losses.",
        "casualty_level": 0,
        "morale_impact": +1,
        "supply_cost": 0,
    },
    "success": {
        "label": "Light Casualties",
        "description": "Casualties are within acceptable parameters. A few wounded.",
        "casualty_level": 1,
        "morale_impact": 0,
        "supply_cost": 0,
    },
    "mixed": {
        "label": "Moderate Casualties",
        "description": "Significant losses. Some specialists may be permanently lost.",
        "casualty_level": 2,
        "morale_impact": -1,
        "supply_cost": 1,
    },
    "failure": {
        "label": "Heavy Casualties",
        "description": "Disaster. Many soldiers lost. Morale takes a serious hit.",
        "casualty_level": 3,
        "morale_impact": -2,
        "supply_cost": 2,
    },
}

# Squad quality modifies the casualty roll outcome
# Higher quality = better resistance to casualties
SQUAD_QUALITY_CASUALTY_BONUS: Dict[int, int] = {
    0: -1,  # Rookies: one tier worse
    1: 0,   # Soldiers: no modifier
    2: +1,  # Elite: one tier better
}

# Casualty level to soldier count lost (approximate)
CASUALTIES_BY_LEVEL: Dict[int, Dict[str, int]] = {
    0: {"min": 0, "max": 0},
    1: {"min": 1, "max": 2},
    2: {"min": 3, "max": 5},
    3: {"min": 6, "max": 10},
}


# =========================================================================
# MISSION REWARD
# =========================================================================

@dataclass
class MissionReward:
    """Structured results of a successful mission.

    Attributes:
        supply_gained: Additional supply earned.
        morale_gained: Morale increase for the Legion.
        intel_gained: Intel points earned.
        relic_found: Whether a holy relic was recovered.
        relic_name: Name of the relic (if relic_found is True).
        notes: Any additional narrative notes.
    """

    supply_gained: int = 0
    morale_gained: int = 0
    intel_gained: int = 0
    relic_found: bool = False
    relic_name: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "supply_gained": self.supply_gained,
            "morale_gained": self.morale_gained,
            "intel_gained": self.intel_gained,
            "relic_found": self.relic_found,
            "relic_name": self.relic_name,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionReward":
        """Deserialize from a plain dict."""
        return cls(**{k: data.get(k, v) for k, v in cls.__dataclass_fields__.items()
                      if k != "notes"},
                   notes=data.get("notes", ""))

    def describe(self) -> str:
        """Return a human-readable description of the mission rewards."""
        parts = []
        if self.supply_gained:
            parts.append(f"+{self.supply_gained} Supply")
        if self.morale_gained:
            sign = "+" if self.morale_gained >= 0 else ""
            parts.append(f"{sign}{self.morale_gained} Morale")
        if self.intel_gained:
            parts.append(f"+{self.intel_gained} Intel")
        if self.relic_found:
            parts.append(f"Relic: {self.relic_name or 'Unknown'}")
        if not parts:
            return "No significant rewards."
        return " | ".join(parts)


# =========================================================================
# MISSION RESOLVER
# =========================================================================

# Reward profiles by reward_type (from MISSION_TYPES)
_REWARD_PROFILES: Dict[str, Dict[str, int]] = {
    "supply":  {"supply_gained": 3, "morale_gained": 0, "intel_gained": 1},
    "morale":  {"supply_gained": 0, "morale_gained": 1, "intel_gained": 0},
    "intel":   {"supply_gained": 0, "morale_gained": 0, "intel_gained": 3},
}

# Outcome multipliers for reward amounts
_OUTCOME_REWARD_MULT: Dict[str, float] = {
    "critical": 1.5,
    "success":  1.0,
    "mixed":    0.5,
    "failure":  0.0,
}


class MissionResolver:
    """Handles mission planning, engagement rolls, and outcome resolution.

    Maintains a record of planned and completed missions for session
    reporting and save/load purposes.

    Args:
        rng_seed: Optional seed for deterministic testing.
    """

    def __init__(self, rng_seed: Optional[int] = None):
        self._rng: random.Random = random.Random(rng_seed)
        self._planned_mission: Optional[Dict[str, Any]] = None
        self._completed_missions: List[Dict[str, Any]] = []

    @property
    def planned_mission(self) -> Optional[Dict[str, Any]]:
        """The currently planned (but not yet resolved) mission."""
        return self._planned_mission

    @property
    def completed_missions(self) -> List[Dict[str, Any]]:
        """History of all resolved missions."""
        return list(self._completed_missions)

    def plan_mission(
        self,
        mission_type: str,
        squad: str,
        specialist: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set up a mission plan before the engagement roll.

        Validates the mission type and records the plan for later resolution.

        Args:
            mission_type: One of the MISSION_TYPES keys.
            squad: Squad type assigned (Rookies, Soldiers, or Elite).
            specialist: Optional specialist attached to this mission.

        Returns:
            Dict describing the planned mission, including base difficulty.
        """
        from codex.forge.reference_data.bob_legion import (
            MISSION_TYPES,
            SQUAD_TYPES,
        )

        # Normalise mission_type capitalisation
        normalised = mission_type.title()
        if normalised not in MISSION_TYPES:
            return {"error": f"Unknown mission type: '{mission_type}'. "
                             f"Valid types: {list(MISSION_TYPES.keys())}"}

        squad_config = SQUAD_TYPES.get(squad, SQUAD_TYPES["Soldiers"])

        plan = {
            "mission_type": normalised,
            "squad": squad,
            "squad_quality": squad_config["quality"],
            "specialist": specialist,
            "base_difficulty": MISSION_TYPES[normalised]["difficulty"],
            "reward_type": MISSION_TYPES[normalised]["reward_type"],
            "description": MISSION_TYPES[normalised]["description"],
            "status": "planned",
        }
        self._planned_mission = plan
        return plan

    def engagement_roll(
        self,
        mission_type: str,
        squad_quality: int,
        specialist_bonus: int = 0,
        pressure_level: int = 0,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Roll the FITD engagement roll adapted for military operations.

        The engagement roll determines the starting position for the mission.
        It uses FITD d6-pool mechanics: pool = squad_quality + specialist_bonus
        - difficulty_modifier.

        Args:
            mission_type: Mission type (sets difficulty modifier).
            squad_quality: Quality of the assigned squad (0=Rookies, 1=Soldiers, 2=Elite).
            specialist_bonus: Bonus dice from attached specialist (default 0).
            pressure_level: Current campaign pressure level (0-5, default 0).
            rng: Optional seeded Random for deterministic results.

        Returns:
            Dict with keys: outcome, dice, highest, dice_pool, position,
            position_description, mission_type, pressure_level.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect

        _rng = rng or self._rng

        # Base pool: squad quality (0-2) + specialist bonus
        base_pool = squad_quality + specialist_bonus

        # Difficulty modifier from pressure
        difficulty_row = MISSION_DIFFICULTY_TABLE.get(mission_type.title(), {})
        difficulty_mod = difficulty_row.get(min(5, pressure_level), 0)

        # Net dice pool (clamped to >= 0; 0 = zero-dice roll in FITD)
        net_pool = max(0, base_pool - difficulty_mod)

        roll = FITDActionRoll(
            dice_count=net_pool,
            position=Position.RISKY,
            effect=Effect.STANDARD,
        )
        result = roll.roll(_rng)

        # Map outcome to starting position
        position_map = {
            "critical": ("Controlled", "The mission goes better than planned from the start."),
            "success":  ("Risky",      "Standard engagement. Objectives are achievable."),
            "mixed":    ("Risky",      "Complications arise. The mission is still viable."),
            "failure":  ("Desperate",  "Things go wrong immediately. Every action is under pressure."),
        }
        position, position_description = position_map.get(
            result.outcome, ("Risky", "Standard engagement.")
        )

        return {
            "outcome": result.outcome,
            "dice": result.all_dice,
            "highest": result.highest,
            "dice_pool": net_pool,
            "base_pool": base_pool,
            "difficulty_mod": difficulty_mod,
            "position": position,
            "position_description": position_description,
            "mission_type": mission_type,
            "pressure_level": pressure_level,
        }

    def resolve_mission(
        self,
        mission: Dict[str, Any],
        casualties_roll: str,
        success_level: str,
    ) -> Dict[str, Any]:
        """Determine mission outcomes: rewards, casualties, morale impact.

        Args:
            mission: A mission plan dict (from ``plan_mission()``).
            casualties_roll: Casualty roll outcome ("critical", "success",
                             "mixed", or "failure").
            success_level: Overall mission success level (same keys).

        Returns:
            Dict with keys: mission_type, success_level, reward (MissionReward),
            casualty_outcome, morale_delta, supply_cost, notes,
            relic_found (bool).
        """
        mission_type = mission.get("mission_type", "Assault")
        reward_type = mission.get("reward_type", "supply")

        # Build reward based on success level
        profile = _REWARD_PROFILES.get(reward_type, _REWARD_PROFILES["supply"]).copy()
        mult = _OUTCOME_REWARD_MULT.get(success_level, 0.0)
        reward = MissionReward(
            supply_gained=int(profile["supply_gained"] * mult),
            morale_gained=int(profile["morale_gained"] * mult),
            intel_gained=int(profile["intel_gained"] * mult),
        )

        # Relic chance: 15% on success, 25% on critical (Religious missions get +10%)
        relic_base = 0.15 if success_level == "success" else (0.25 if success_level == "critical" else 0.0)
        if mission_type == "Religious":
            relic_base += 0.10
        if self._rng.random() < relic_base:
            reward.relic_found = True
            relic_names = [
                "Nyx's Lantern", "Holy Standard of the First Legion",
                "Bone Reliquary", "Shattered Idol of Coros",
                "Panyar Spirit Stone", "Aldermani War Seal",
            ]
            reward.relic_name = self._rng.choice(relic_names)

        # Casualty outcome
        casualty_data = CASUALTY_TABLE.get(casualties_roll, CASUALTY_TABLE["mixed"])

        # Build result
        resolution = {
            "mission_type": mission_type,
            "success_level": success_level,
            "reward": reward.to_dict(),
            "reward_description": reward.describe(),
            "casualty_outcome": casualty_data,
            "morale_delta": casualty_data["morale_impact"] + reward.morale_gained,
            "supply_cost": casualty_data["supply_cost"],
            "relic_found": reward.relic_found,
            "relic_name": reward.relic_name,
            "notes": casualty_data["description"],
            "status": "resolved",
        }

        # Record in history
        self._completed_missions.append({**mission, **resolution})
        self._planned_mission = None

        return resolution

    def casualty_roll(
        self,
        squad_type: str,
        mission_difficulty: int,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Roll for soldier losses after a mission.

        Uses FITD d6-pool: pool = 3 - mission_difficulty + quality_bonus.
        The outcome determines the casualty severity.

        Args:
            squad_type: Squad type ("Rookies", "Soldiers", or "Elite").
            mission_difficulty: Base difficulty of the mission (1-5).
            rng: Optional seeded Random for deterministic results.

        Returns:
            Dict with keys: squad_type, outcome, casualty_level,
            soldiers_lost (range), label, description, quality_bonus.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect
        from codex.forge.reference_data.bob_legion import SQUAD_TYPES

        _rng = rng or self._rng

        squad_config = SQUAD_TYPES.get(squad_type, SQUAD_TYPES["Soldiers"])
        quality = squad_config["quality"]
        quality_bonus = SQUAD_QUALITY_CASUALTY_BONUS.get(quality, 0)

        # Dice pool: base 2 + quality bonus - difficulty modifier
        # Higher difficulty = fewer dice = worse outcomes
        difficulty_mod = max(0, mission_difficulty - 2)
        pool = max(0, 2 + quality_bonus - difficulty_mod)

        roll = FITDActionRoll(dice_count=pool, position=Position.RISKY, effect=Effect.STANDARD)
        result = roll.roll(_rng)

        casualty_data = CASUALTY_TABLE.get(result.outcome, CASUALTY_TABLE["mixed"])
        c_level = casualty_data["casualty_level"]
        c_range = CASUALTIES_BY_LEVEL.get(c_level, {"min": 0, "max": 0})

        return {
            "squad_type": squad_type,
            "outcome": result.outcome,
            "dice": result.all_dice,
            "dice_pool": pool,
            "quality_bonus": quality_bonus,
            "casualty_level": c_level,
            "soldiers_lost_min": c_range["min"],
            "soldiers_lost_max": c_range["max"],
            "label": casualty_data["label"],
            "description": casualty_data["description"],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for save/load."""
        return {
            "planned_mission": self._planned_mission,
            "completed_missions": list(self._completed_missions),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionResolver":
        """Deserialize from a plain dict."""
        resolver = cls()
        resolver._planned_mission = data.get("planned_mission")
        resolver._completed_missions = data.get("completed_missions", [])
        return resolver

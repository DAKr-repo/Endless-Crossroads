"""
codex.games.stc.surgebinding
==============================
Stormlight and Surgebinding subsystem for the Cosmere RPG.

Classes:
  - StormTracker: Tracks highstorm cycle and stormlight sphere recharge
  - SurgeManager: Per-character stormlight tracking and surge ability activation
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================================
# STORM TRACKER
# =========================================================================

class StormTracker:
    """
    Tracks the highstorm cycle for Rosharan campaigns.

    Highstorms recharge all infused gemstone spheres and have significant
    environmental effects. They occur on a roughly 5-10 day cycle.

    Attributes:
        days_since_storm: Days elapsed since last highstorm.
        storm_cycle: Days between highstorms (default 7, rolls 5-10).
        _rng: Random instance for deterministic testing.
    """

    def __init__(self, storm_cycle: int = 7, rng: Optional[random.Random] = None) -> None:
        """
        Initialise the storm tracker.

        Args:
            storm_cycle: Days between highstorms. Default 7.
            rng: Optional seeded Random for deterministic tests.
        """
        self.days_since_storm: int = 0
        self.storm_cycle: int = storm_cycle
        self._rng = rng or random.Random()

    def advance_day(self) -> dict:
        """
        Advance the in-game calendar by one day.

        Returns:
            Dict with keys: day_advanced (True), highstorm_occurred (bool),
            days_since_storm (int), storm_data (dict or None).
        """
        self.days_since_storm += 1
        if self.days_since_storm >= self.storm_cycle:
            storm_data = self.trigger_highstorm()
            return {
                "day_advanced": True,
                "highstorm_occurred": True,
                "days_since_storm": self.days_since_storm,
                "storm_data": storm_data,
            }
        return {
            "day_advanced": True,
            "highstorm_occurred": False,
            "days_since_storm": self.days_since_storm,
            "storm_data": None,
        }

    def trigger_highstorm(self) -> dict:
        """
        Trigger a highstorm, resetting the cycle and generating effects.

        Resets days_since_storm to 0 and rolls the next storm cycle length
        (5-10 days).

        Returns:
            Dict with keys: intensity (str), sphere_recharge (str),
            environmental_effect (str), next_cycle (int).
        """
        self.days_since_storm = 0
        next_cycle = self._rng.randint(5, 10)
        self.storm_cycle = next_cycle

        intensity = self._rng.choice(["Weak", "Moderate", "Strong", "Furious"])
        _effects = {
            "Weak":     "Light rainfall and wind. Travel is difficult but possible.",
            "Moderate": "Heavy rain and fierce winds. Shelter required for most creatures.",
            "Strong":   "Torrential rain and gale-force winds. Exposed creatures take 1d6 damage.",
            "Furious":  "Catastrophic rain and hurricane winds. Exposed creatures take 2d6 damage "
                        "and must make Strength DC 15 or be swept away.",
        }

        return {
            "intensity": intensity,
            "sphere_recharge": "All infused gemstone spheres are fully recharged with Stormlight.",
            "environmental_effect": _effects[intensity],
            "next_cycle": next_cycle,
        }

    def to_dict(self) -> dict:
        """Serialise to a plain dict for save/load."""
        return {
            "days_since_storm": self.days_since_storm,
            "storm_cycle": self.storm_cycle,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StormTracker":
        """Deserialise from a saved dict."""
        tracker = cls(storm_cycle=data.get("storm_cycle", 7))
        tracker.days_since_storm = data.get("days_since_storm", 0)
        return tracker


# =========================================================================
# SURGE MANAGER
# =========================================================================

class SurgeManager:
    """
    Per-character stormlight tracking and surge ability activation.

    Manages a single character's stormlight pool, available powers based on
    their Radiant Order and ideal level, and active maintained surges.

    Attributes:
        character_name: Name of the character.
        order: Radiant Order (e.g. 'windrunner').
        stormlight: Current stormlight points.
        max_stormlight: Maximum stormlight (ideal_level × 10).
        ideal_level: Current Radiant Ideal level (1-5).
        available_powers: Powers unlocked at current ideal level.
        active_surges: Currently active surge effects with maintenance costs.
    """

    def __init__(
        self,
        character_name: str,
        order: str = "",
        ideal_level: int = 1,
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        Initialise the surge manager for a character.

        Args:
            character_name: Name of the character.
            order: Radiant Order name (lowercase, e.g. 'windrunner').
            ideal_level: Starting ideal level (1-5).
            rng: Optional seeded Random for deterministic tests.
        """
        self.character_name = character_name
        self.order = order.lower()
        self.ideal_level = max(1, min(5, ideal_level))
        self.max_stormlight: int = self.ideal_level * 10
        self.stormlight: int = 0  # Starts empty; must be infused
        self.active_surges: List[dict] = []
        self._rng = rng or random.Random()
        self._powers_cache: Optional[List[dict]] = None

    def _get_powers_for_level(self) -> List[dict]:
        """Return all powers unlocked at or below current ideal level."""
        if self._powers_cache is not None:
            return self._powers_cache
        try:
            from codex.forge.reference_data.stc_orders import ORDERS
            order_data = ORDERS.get(self.order, {})
            per_level = order_data.get("per_ideal_powers", {})
            powers: List[dict] = []
            for lvl in range(1, self.ideal_level + 1):
                for power in per_level.get(lvl, []):
                    powers.append(dict(power, ideal_level_required=lvl))
            self._powers_cache = powers
            return powers
        except ImportError:
            return []

    def _invalidate_cache(self) -> None:
        """Invalidate cached powers when ideal level changes."""
        self._powers_cache = None

    def infuse(self, amount: int) -> dict:
        """
        Absorb stormlight from spheres.

        Args:
            amount: Stormlight units to absorb.

        Returns:
            Dict with keys: absorbed (int), stormlight (int), max_stormlight (int),
            overflow (int).
        """
        amount = max(0, amount)
        before = self.stormlight
        self.stormlight = min(self.max_stormlight, self.stormlight + amount)
        absorbed = self.stormlight - before
        overflow = amount - absorbed
        return {
            "absorbed": absorbed,
            "stormlight": self.stormlight,
            "max_stormlight": self.max_stormlight,
            "overflow": overflow,
        }

    def drain(self, amount: int) -> dict:
        """
        Spend stormlight on a surge or power.

        Args:
            amount: Stormlight units to spend.

        Returns:
            Dict with keys: success (bool), spent (int), stormlight (int),
            message (str).
        """
        if amount <= 0:
            return {"success": True, "spent": 0, "stormlight": self.stormlight,
                    "message": "No cost."}
        if self.stormlight < amount:
            return {
                "success": False,
                "spent": 0,
                "stormlight": self.stormlight,
                "message": f"Insufficient stormlight. Need {amount}, have {self.stormlight}.",
            }
        self.stormlight -= amount
        return {
            "success": True,
            "spent": amount,
            "stormlight": self.stormlight,
            "message": f"Spent {amount} stormlight. Remaining: {self.stormlight}.",
        }

    def use_power(self, power_name: str) -> dict:
        """
        Activate a named surge power.

        Checks that the power is unlocked at the current ideal level and that
        sufficient stormlight is available.

        Args:
            power_name: Name of the power to activate.

        Returns:
            Dict with keys: success (bool), power (dict or None), stormlight (int),
            message (str).
        """
        powers = self._get_powers_for_level()
        target: Optional[dict] = None
        for p in powers:
            if p["name"].lower() == power_name.lower():
                target = p
                break
        if target is None:
            return {
                "success": False,
                "power": None,
                "stormlight": self.stormlight,
                "message": f"Power '{power_name}' is not available to "
                           f"{self.order.title()} at Ideal {self.ideal_level}.",
            }
        cost = target.get("stormlight_cost", 0)
        drain_result = self.drain(cost)
        if not drain_result["success"]:
            return {
                "success": False,
                "power": target,
                "stormlight": self.stormlight,
                "message": drain_result["message"],
            }
        return {
            "success": True,
            "power": target,
            "stormlight": self.stormlight,
            "message": (
                f"{self.character_name} activates {target['name']}! "
                f"Cost: {cost} stormlight. Remaining: {self.stormlight}.\n"
                f"{target['description']}"
            ),
        }

    def maintain_surges(self) -> dict:
        """
        Tick active surge maintenance costs (called each round for sustained surges).

        Returns:
            Dict with keys: total_drained (int), stormlight (int),
            expired_surges (list of names), active_count (int).
        """
        total = 0
        expired: List[str] = []
        still_active: List[dict] = []
        for surge in self.active_surges:
            cost = surge.get("maintenance_cost", 1)
            if self.stormlight >= cost:
                self.stormlight -= cost
                total += cost
                still_active.append(surge)
            else:
                expired.append(surge.get("name", "Unknown Surge"))
        self.active_surges = still_active
        return {
            "total_drained": total,
            "stormlight": self.stormlight,
            "expired_surges": expired,
            "active_count": len(self.active_surges),
        }

    def healing(self, character: Any) -> dict:
        """
        Auto-spend stormlight to heal a character.

        One stormlight heals one HP. Continues until character is at max HP
        or stormlight runs out.

        Args:
            character: CosmereCharacter (must have current_hp, max_hp, heal()).

        Returns:
            Dict with keys: healed (int), stormlight_spent (int), stormlight (int),
            new_hp (int), message (str).
        """
        need = character.max_hp - character.current_hp
        can_spend = min(need, self.stormlight)
        if can_spend <= 0:
            return {
                "healed": 0,
                "stormlight_spent": 0,
                "stormlight": self.stormlight,
                "new_hp": character.current_hp,
                "message": "No healing needed or no stormlight available.",
            }
        healed = character.heal(can_spend)
        self.stormlight -= healed
        return {
            "healed": healed,
            "stormlight_spent": healed,
            "stormlight": self.stormlight,
            "new_hp": character.current_hp,
            "message": f"Stormlight healing: {healed} HP restored. Remaining: {self.stormlight}.",
        }

    def lashing(self, target: str, direction: str = "up") -> dict:
        """
        Resolve a Gravitation surge Lashing.

        Args:
            target: Name of the target (object or creature).
            direction: Lashing direction ('up', 'down', 'sideways', 'toward'). Default 'up'.

        Returns:
            Dict with keys: success (bool), stormlight (int), message (str),
            direction (str), target (str).
        """
        # Windrunners / Skybreakers use Gravitation; cost 2 for Basic Lashing
        cost = 2
        drain_result = self.drain(cost)
        if not drain_result["success"]:
            return {
                "success": False,
                "stormlight": self.stormlight,
                "message": drain_result["message"],
                "direction": direction,
                "target": target,
            }
        _desc = {
            "up":       f"{target} is lashed upward — gravity reverses for them.",
            "down":     f"{target} is lashed downward with double gravity.",
            "sideways": f"{target} is lashed sideways — they fall in that direction.",
            "toward":   f"{target} is drawn toward the lash point rapidly.",
        }
        desc = _desc.get(direction.lower(), f"{target} is lashed in direction: {direction}.")
        return {
            "success": True,
            "stormlight": self.stormlight,
            "message": f"Lashing applied! {desc} Cost: {cost} stormlight.",
            "direction": direction,
            "target": target,
        }

    def soulcast(
        self,
        target_material: str,
        difficulty: int = 10,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        Resolve a Transformation surge Soulcasting attempt.

        Args:
            target_material: The substance to transform into (e.g. 'air', 'stone').
            difficulty: DC for the Transformation check. Default 10.
            rng: Optional Random override for the dice roll.

        Returns:
            Dict with keys: success (bool), roll (int), total (int), dc (int),
            stormlight (int), message (str).
        """
        cost = 3
        drain_result = self.drain(cost)
        if not drain_result["success"]:
            return {
                "success": False,
                "roll": 0,
                "total": 0,
                "dc": difficulty,
                "stormlight": self.stormlight,
                "message": drain_result["message"],
            }
        r = rng or self._rng
        roll = r.randint(1, 20)
        # No modifier here — pure persuasion of the material's spren
        total = roll
        success = total >= difficulty or roll == 20
        if success:
            msg = (
                f"Soulcasting succeeds! The material transforms into {target_material}. "
                f"(Roll: {roll} vs DC {difficulty})"
            )
        else:
            msg = (
                f"Soulcasting fails. The material resists transformation. "
                f"(Roll: {roll} vs DC {difficulty})"
            )
        return {
            "success": success,
            "roll": roll,
            "total": total,
            "dc": difficulty,
            "stormlight": self.stormlight,
            "message": msg,
        }

    def illuminate(self, description: str = "") -> dict:
        """
        Create a Lightweaving (Illumination surge illusion).

        Args:
            description: Description of the illusion to create.

        Returns:
            Dict with keys: success (bool), stormlight (int), message (str),
            description (str).
        """
        cost = 2
        drain_result = self.drain(cost)
        if not drain_result["success"]:
            return {
                "success": False,
                "stormlight": self.stormlight,
                "message": drain_result["message"],
                "description": description,
            }
        illusion_desc = description or "a shifting, indistinct image of light and shadow"
        return {
            "success": True,
            "stormlight": self.stormlight,
            "message": (
                f"Lightweaving created: {illusion_desc}. "
                f"Cost: {cost} stormlight. Remaining: {self.stormlight}."
            ),
            "description": illusion_desc,
        }

    def get_available_powers(self) -> List[dict]:
        """
        Return all powers unlocked at current ideal level.

        Returns:
            List of power dicts from the order's per_ideal_powers.
        """
        return self._get_powers_for_level()

    def get_status(self) -> str:
        """
        Return a human-readable status string.

        Returns:
            Formatted string showing stormlight, max, ideal level, active surges.
        """
        surge_names = [s.get("name", "Unknown") for s in self.active_surges]
        surges_str = ", ".join(surge_names) if surge_names else "None"
        return (
            f"{self.character_name} ({self.order.title() or 'Unsworn'}) — "
            f"Stormlight: {self.stormlight}/{self.max_stormlight} | "
            f"Ideal: {self.ideal_level} | Active surges: {surges_str}"
        )

    def set_ideal_level(self, level: int) -> None:
        """Update ideal level and recalculate max stormlight."""
        self.ideal_level = max(1, min(5, level))
        self.max_stormlight = self.ideal_level * 10
        self._invalidate_cache()

    def to_dict(self) -> dict:
        """Serialise to a plain dict for save/load."""
        return {
            "character_name": self.character_name,
            "order": self.order,
            "ideal_level": self.ideal_level,
            "stormlight": self.stormlight,
            "max_stormlight": self.max_stormlight,
            "active_surges": list(self.active_surges),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SurgeManager":
        """Deserialise from a saved dict."""
        mgr = cls(
            character_name=data["character_name"],
            order=data.get("order", ""),
            ideal_level=data.get("ideal_level", 1),
        )
        mgr.stormlight = data.get("stormlight", 0)
        mgr.max_stormlight = data.get("max_stormlight", mgr.max_stormlight)
        mgr.active_surges = data.get("active_surges", [])
        return mgr


__all__ = ["StormTracker", "SurgeManager"]

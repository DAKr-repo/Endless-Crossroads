"""
codex.games.sav.ships — Ship management subsystem for Scum & Villainy.

Provides ShipState dataclass and all ship-related mechanics:
  - Ship damage and repair
  - Ship combat rolls (FITD-style using system quality as dice pool)
  - Module installation
  - Gambit spending
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from codex.forge.reference_data.sav_ships import (
    SHIP_CLASSES,
    SHIP_MODULES,
    SYSTEM_QUALITY_TRACKS,
)


# =========================================================================
# SHIP STATE
# =========================================================================

@dataclass
class ShipState:
    """Full state of a crew's ship in Scum & Villainy.

    Attributes:
        name: Ship's registered (or fake) name.
        ship_class: Ship class key from SHIP_CLASSES reference data.
        hull_integrity: Overall hull damage boxes (0 = destroyed, 6 = pristine).
        systems: Dict mapping system names to quality ratings (0-3).
        installed_modules: List of module names currently installed.
        crew_quality: Crew tier for ship operations (1-4).
        gambits: Current gambit tokens (0-4), spent for bonuses, refresh each job.
    """

    name: str = "Unnamed"
    ship_class: str = ""
    hull_integrity: int = 6
    systems: Dict[str, int] = field(default_factory=lambda: {
        "engines": 2,
        "hull": 2,
        "comms": 2,
        "weapons": 2,
    })
    installed_modules: List[str] = field(default_factory=list)
    crew_quality: int = 1
    gambits: int = 2

    def __post_init__(self) -> None:
        """Initialize systems from ship class if provided."""
        if self.ship_class and self.ship_class in SHIP_CLASSES:
            class_data = SHIP_CLASSES[self.ship_class]
            # Only use class defaults if systems are still at default values
            if self.systems == {"engines": 2, "hull": 2, "comms": 2, "weapons": 2}:
                self.systems = dict(class_data["systems"])

    def is_operational(self) -> bool:
        """Return True if the ship can operate (not all systems at 0)."""
        if self.hull_integrity <= 0:
            return False
        return any(v > 0 for v in self.systems.values())

    def take_damage(self, system: str, amount: int) -> None:
        """Apply damage to a specific ship system.

        Args:
            system: System name (engines/hull/comms/weapons).
            amount: Damage amount (1+).
        """
        if system not in self.systems:
            return
        self.systems[system] = max(0, self.systems[system] - amount)
        # Hull damage also reduces hull_integrity
        if system == "hull":
            self.hull_integrity = max(0, self.hull_integrity - amount)

    def repair_system(self, system: str, amount: int) -> None:
        """Repair a ship system, clamped to max quality 3.

        Args:
            system: System name to repair.
            amount: Quality rating points to restore.
        """
        if system not in self.systems:
            return
        max_quality = 3
        self.systems[system] = min(max_quality, self.systems[system] + amount)
        if system == "hull":
            self.hull_integrity = min(6, self.hull_integrity + amount)

    def to_dict(self) -> dict:
        """Serialize to plain dict for save/load."""
        return {
            "name": self.name,
            "ship_class": self.ship_class,
            "hull_integrity": self.hull_integrity,
            "systems": dict(self.systems),
            "installed_modules": list(self.installed_modules),
            "crew_quality": self.crew_quality,
            "gambits": self.gambits,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipState":
        """Deserialize from a plain dict.

        Args:
            data: Dict from a previous to_dict() call.

        Returns:
            Restored ShipState instance.
        """
        ship = cls(
            name=data.get("name", "Unnamed"),
            ship_class=data.get("ship_class", ""),
            hull_integrity=data.get("hull_integrity", 6),
            crew_quality=data.get("crew_quality", 1),
            gambits=data.get("gambits", 2),
        )
        # Override systems directly to avoid __post_init__ overwriting saved state
        if "systems" in data:
            ship.systems = dict(data["systems"])
        ship.installed_modules = list(data.get("installed_modules", []))
        return ship


# =========================================================================
# SHIP COMBAT ROLL
# =========================================================================

def ship_combat_roll(
    ship: ShipState,
    system: str,
    bonus_dice: int = 0,
    rng: Optional[random.Random] = None,
) -> dict:
    """Execute a FITD-style ship combat roll using system quality as dice pool.

    The system quality rating (0-3) determines the base dice count.
    Bonus dice from gambits or crew quality can be added.

    If total dice is 0, roll 2d6 and take the lowest (zero-dice disadvantage rule).

    Args:
        ship: The ShipState performing the action.
        system: Ship system being used (engines/hull/comms/weapons).
        bonus_dice: Additional dice from gambits, crew, etc.
        rng: Optional seeded Random instance for deterministic tests.

    Returns:
        Dict with keys: dice (list), highest (int), critical (bool),
        position (str), description (str), outcome (str).
    """
    _rng = rng or random.Random()
    system_quality = ship.systems.get(system, 0)
    total_dice = max(0, system_quality + bonus_dice)

    if total_dice <= 0:
        # Zero-dice: roll 2, take lowest
        rolled = sorted([_rng.randint(1, 6) for _ in range(2)])
        highest = rolled[0]
    else:
        rolled = [_rng.randint(1, 6) for _ in range(total_dice)]
        highest = max(rolled)

    sixes = rolled.count(6)

    if sixes >= 2:
        outcome = "critical"
        description = f"CRITICAL! System pushes beyond rated limits. Dice: [{', '.join(str(d) for d in rolled)}]"
    elif highest == 6:
        outcome = "success"
        description = f"Full success. Clean execution. Dice: [{', '.join(str(d) for d in rolled)}]"
    elif highest >= 4:
        outcome = "mixed"
        description = f"Mixed result. Goal achieved with complication. Dice: [{', '.join(str(d) for d in rolled)}]"
    else:
        outcome = "failure"
        description = f"Failure. Systems perform poorly under pressure. Dice: [{', '.join(str(d) for d in rolled)}]"

    return {
        "dice": rolled,
        "highest": highest,
        "critical": sixes >= 2,
        "position": "risky",
        "description": description,
        "outcome": outcome,
        "system": system,
        "system_quality": system_quality,
    }


# =========================================================================
# DAMAGE SYSTEM
# =========================================================================

def damage_system(ship: ShipState, system: str, amount: int) -> dict:
    """Reduce a ship system's quality rating.

    If any system drops to 0, the ship is crippled (but not necessarily destroyed).
    Hull damage at 0 triggers a ship destruction warning.

    Args:
        ship: The ShipState to damage.
        system: System name to damage.
        amount: Quality points to reduce.

    Returns:
        Dict with damage_dealt (int), system_before (int), system_after (int),
        crippled (bool), destroyed (bool), status_description (str).
    """
    if system not in ship.systems:
        return {
            "damage_dealt": 0,
            "error": f"Unknown system: {system}",
            "crippled": False,
            "destroyed": False,
        }

    before = ship.systems[system]
    ship.take_damage(system, amount)
    after = ship.systems[system]
    actual_damage = before - after

    crippled = after == 0
    destroyed = ship.hull_integrity <= 0

    quality_track = SYSTEM_QUALITY_TRACKS.get(system, {})
    status_description = quality_track.get(after, f"{system.title()} quality: {after}/3")

    return {
        "damage_dealt": actual_damage,
        "system": system,
        "system_before": before,
        "system_after": after,
        "crippled": crippled,
        "destroyed": destroyed,
        "status_description": status_description,
    }


# =========================================================================
# REPAIR SYSTEM
# =========================================================================

def repair_system(
    ship: ShipState,
    system: str,
    mechanic_dots: int = 0,
    rng: Optional[random.Random] = None,
) -> dict:
    """Perform a downtime repair roll to restore system quality.

    Uses FITD-style resolution: mechanic dots = dice pool.
    Result determines quality restored.

    Args:
        ship: The ShipState to repair.
        system: System name to repair.
        mechanic_dots: Mechanic's rig action dots (0-4).
        rng: Optional seeded Random for deterministic tests.

    Returns:
        Dict with restored (int), system_before (int), system_after (int),
        outcome (str), description (str).
    """
    _rng = rng or random.Random()
    before = ship.systems.get(system, 0)

    if system not in ship.systems:
        return {"error": f"Unknown system: {system}", "restored": 0}

    # Repair roll: mechanic dots as dice pool
    total_dice = max(0, mechanic_dots)
    if total_dice <= 0:
        rolled = sorted([_rng.randint(1, 6) for _ in range(2)])
        highest = rolled[0]
    else:
        rolled = [_rng.randint(1, 6) for _ in range(total_dice)]
        highest = max(rolled)

    sixes = rolled.count(6)

    if sixes >= 2:
        outcome = "critical"
        restored = 2
        description = f"Critical repair! System restored by 2 quality."
    elif highest == 6:
        outcome = "success"
        restored = 1
        description = f"Repair successful. System restored by 1 quality."
    elif highest >= 4:
        outcome = "mixed"
        restored = 1
        description = f"Partial repair. System restored by 1 but took time (lose 1 downtime activity)."
    else:
        outcome = "failure"
        restored = 0
        description = f"Repair failed. System remains at quality {before}."

    if restored > 0:
        ship.repair_system(system, restored)

    after = ship.systems.get(system, 0)
    return {
        "restored": restored,
        "system": system,
        "system_before": before,
        "system_after": after,
        "outcome": outcome,
        "description": description,
        "dice": rolled,
    }


# =========================================================================
# MODULE INSTALLATION
# =========================================================================

def install_module(ship: ShipState, module_name: str) -> dict:
    """Install a module from SHIP_MODULES reference data.

    Validates that the module exists and is not already installed.

    Args:
        ship: The ShipState to install onto.
        module_name: Module name from SHIP_MODULES.

    Returns:
        Dict with success (bool), message (str), and module data if successful.
    """
    if module_name not in SHIP_MODULES:
        return {
            "success": False,
            "message": f"Unknown module: {module_name}. Check SHIP_MODULES for valid names.",
        }

    if module_name in ship.installed_modules:
        return {
            "success": False,
            "message": f"{module_name} is already installed on this ship.",
        }

    module_data = SHIP_MODULES[module_name]
    ship.installed_modules.append(module_name)

    return {
        "success": True,
        "message": f"{module_name} installed successfully.",
        "module": module_name,
        "category": module_data.get("category", module_data.get("system", "auxiliary")),
        "effect": module_data["effect"],
    }


# =========================================================================
# GAMBIT SPENDING
# =========================================================================

def use_gambit(ship: ShipState) -> dict:
    """Spend 1 gambit for a bonus die on the next ship roll.

    Gambits refresh at the start of each new job.

    Args:
        ship: The ShipState spending the gambit.

    Returns:
        Dict with success (bool), gambits_remaining (int), message (str).
    """
    if ship.gambits <= 0:
        return {
            "success": False,
            "gambits_remaining": 0,
            "message": "No gambits remaining. Gambits refresh at the start of each job.",
        }

    ship.gambits -= 1
    return {
        "success": True,
        "gambits_remaining": ship.gambits,
        "message": (
            f"Gambit spent. You have {ship.gambits} gambit(s) remaining. "
            f"Add +1d to your next ship action roll."
        ),
    }

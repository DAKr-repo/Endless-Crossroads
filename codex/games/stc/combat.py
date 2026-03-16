"""
codex.games.stc.combat
========================
Cosmere RPG combat resolution: attack rolls, Shardblade mechanics,
Shardplate defense, duels, and surge combat.

Provides:
  - AttackResult: Dataclass for attack outcomes with describe()
  - CosmereCombatResolver: Cosmere-specific combat mechanics
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =========================================================================
# DICE HELPERS
# =========================================================================

def _parse_dice(dice_str: str) -> Tuple[int, int]:
    """
    Parse a dice expression like '2d10' into (count, sides).

    Args:
        dice_str: Dice expression string (e.g. '1d8', '2d10').

    Returns:
        Tuple of (count, sides). Falls back to (1, 4) on invalid input.
    """
    try:
        parts = dice_str.lower().split("d")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 1, 4


def _roll_damage(
    dice_str: str,
    rng: random.Random,
    modifier: int = 0,
    critical: bool = False,
) -> int:
    """
    Roll damage using a dice expression.

    On a critical hit, the dice count is doubled.

    Args:
        dice_str: Dice expression (e.g. '2d10').
        rng: Random instance to use.
        modifier: Flat bonus added to the total.
        critical: If True, double the number of dice.

    Returns:
        Damage total (minimum 0).
    """
    count, sides = _parse_dice(dice_str)
    if critical:
        count *= 2
    total = sum(rng.randint(1, sides) for _ in range(count)) + modifier
    return max(0, total)


# =========================================================================
# ATTACK RESULT
# =========================================================================

@dataclass
class AttackResult:
    """
    Encapsulates the outcome of a single Cosmere attack.

    Attributes:
        attacker: Name of the attacker.
        target: Name of the target.
        roll: Raw d20 result.
        modifier: Total modifier applied.
        total: roll + modifier.
        defense: Target's defense value.
        hit: Whether the attack connected.
        critical: Whether a natural 20 was rolled.
        fumble: Whether a natural 1 was rolled.
        damage: Damage dealt (0 if missed).
        weapon: Weapon name used.
        description: Extended description of special effects.
    """

    attacker: str
    target: str = "enemy"
    roll: int = 0
    modifier: int = 0
    total: int = 0
    defense: int = 10
    hit: bool = False
    critical: bool = False
    fumble: bool = False
    damage: int = 0
    weapon: str = "unarmed"
    description: str = ""

    def describe(self) -> str:
        """Return a human-readable description of the attack result."""
        if self.fumble:
            return f"{self.attacker} fumbles! (rolled 1)"
        if self.critical:
            return (
                f"{self.attacker} CRITICAL HIT on {self.target}! "
                f"{self.damage} damage with {self.weapon}."
                + (f" {self.description}" if self.description else "")
            )
        if self.hit:
            return (
                f"{self.attacker} hits {self.target} "
                f"({self.total} vs Defense {self.defense}) "
                f"for {self.damage} damage with {self.weapon}."
                + (f" {self.description}" if self.description else "")
            )
        return (
            f"{self.attacker} misses {self.target} "
            f"({self.total} vs Defense {self.defense})."
        )


# =========================================================================
# COSMERE COMBAT RESOLVER
# =========================================================================

class CosmereCombatResolver:
    """
    Resolves Cosmere RPG combat actions with Rosharan mechanics.

    Handles standard attacks, Shardblade mechanics (limb deadening,
    armor bypassing), Shardplate defense, Alethi duels, and surge combat.

    Accepts an optional ``random.Random`` instance for deterministic testing.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        """
        Initialise the combat resolver.

        Args:
            rng: Optional seeded Random instance for deterministic tests.
        """
        self._rng = rng or random.Random()

    # ─── Standard attack ─────────────────────────────────────────────

    def attack_roll(
        self,
        attacker: Any,
        target_defense: int,
        weapon_name: str = "unarmed",
        ability_mod: int = 0,
        stormlight_bonus: int = 0,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> AttackResult:
        """
        Resolve a standard melee or ranged weapon attack roll.

        Advantage and disadvantage cancel each other out. Stormlight can be
        spent to add a bonus to the attack roll.

        Args:
            attacker: Character object with .name, or string name.
            target_defense: The target's defense value.
            weapon_name: Weapon name from stc_equipment.WEAPON_PROPERTIES.
            ability_mod: Relevant ability modifier (Strength or Speed).
            stormlight_bonus: Bonus added from spending stormlight (optional).
            advantage: Roll two d20s, take higher.
            disadvantage: Roll two d20s, take lower.

        Returns:
            AttackResult with full resolution data.
        """
        from codex.forge.reference_data.stc_equipment import WEAPON_PROPERTIES
        wpn = WEAPON_PROPERTIES.get(
            weapon_name.lower(),
            {"damage_dice": "1d4", "damage_type": "bludgeoning", "properties": []},
        )

        r1 = self._rng.randint(1, 20)
        r2 = self._rng.randint(1, 20)
        if advantage and not disadvantage:
            roll = max(r1, r2)
        elif disadvantage and not advantage:
            roll = min(r1, r2)
        else:
            roll = r1

        modifier = ability_mod + stormlight_bonus
        total = roll + modifier
        critical = roll == 20
        fumble = roll == 1
        hit = critical or (not fumble and total >= target_defense)

        damage = 0
        if hit:
            damage = _roll_damage(wpn.get("damage_dice", "1d4"), self._rng,
                                  modifier=ability_mod, critical=critical)
            damage = max(1, damage)

        attacker_name = attacker.name if hasattr(attacker, "name") else str(attacker)
        return AttackResult(
            attacker=attacker_name,
            target="target",
            roll=roll,
            modifier=modifier,
            total=total,
            defense=target_defense,
            hit=hit,
            critical=critical,
            fumble=fumble,
            damage=damage,
            weapon=weapon_name,
        )

    # ─── Shardblade attack ────────────────────────────────────────────

    def shardblade_attack(
        self,
        attacker: Any,
        target: Any,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        Resolve a Shardblade attack with full Rosharan mechanics.

        Shardblades bypass non-Shardplate armor entirely. Against living
        creatures, they kill on a hit to the torso or head. Limb hits
        deaden the struck limb (immediate functional loss; limb can be
        healed with Regrowth). Against spren, dead Shardblades kill on touch.

        Args:
            attacker: Character object with name and attributes, or string name.
            target: Target dict or object with name, hp, defense, armor.
            rng: Optional Random override.

        Returns:
            Dict with keys: hit (bool), critical (bool), roll (int),
            total (int), damage (int), location (str), effect (str),
            message (str), target_alive (bool).
        """
        r = rng or self._rng
        attacker_name = attacker.name if hasattr(attacker, "name") else str(attacker)

        # Shardblade attacks at a fixed +8 (strength of the bond)
        blade_mod = 8
        roll = r.randint(1, 20)
        total = roll + blade_mod
        critical = roll == 20
        fumble = roll == 1

        # Get target defense — Shardplate is the only defense that matters
        if hasattr(target, "defense"):
            defense = target.defense
        elif isinstance(target, dict):
            defense = target.get("defense", 10)
        else:
            defense = 10

        hit = critical or (not fumble and total >= defense)

        if not hit:
            return {
                "hit": False, "critical": False,
                "roll": roll, "total": total,
                "damage": 0, "location": "",
                "effect": "miss",
                "message": f"{attacker_name}'s Shardblade slices through empty air.",
                "target_alive": True,
            }

        # Determine hit location
        location_roll = r.randint(1, 6)
        if location_roll <= 2:
            location = "torso"
        elif location_roll == 3:
            location = "head"
        elif location_roll == 4:
            location = "right arm"
        elif location_roll == 5:
            location = "left arm"
        else:
            location = "leg"

        # Shardblade damage — always lethal to unarmored; massive to Shardplate
        base_damage = r.randint(10, 20)
        if critical:
            base_damage = r.randint(20, 40)

        # Determine effect based on location and armor
        target_name = target.name if hasattr(target, "name") else (
            target.get("name", "enemy") if isinstance(target, dict) else "enemy"
        )
        has_shardplate = (
            "shardplate" in (target.get("armor", "").lower() if isinstance(target, dict) else "")
        )

        if has_shardplate:
            effect = "plate_crack"
            damage = base_damage // 2  # Plate absorbs, but still cracks
            msg = (
                f"{attacker_name}'s Shardblade strikes {target_name}'s Shardplate at the "
                f"{location}! The plate cracks. Damage: {damage}."
            )
        elif location in ("torso", "head"):
            effect = "kill"
            damage = base_damage
            # Apply damage to target if it supports it
            if hasattr(target, "take_damage"):
                target.take_damage(damage)
            elif isinstance(target, dict):
                target["hp"] = max(0, target.get("hp", 0) - damage)
            msg = (
                f"{attacker_name}'s Shardblade strikes {target_name} in the {location}! "
                f"The spren of the soul is severed. Massive damage: {damage}. "
                f"Target may be slain."
            )
        else:
            effect = "deaden_limb"
            damage = 0  # Shardblade doesn't cause bleeding — it deadens
            msg = (
                f"{attacker_name}'s Shardblade strikes {target_name}'s {location}. "
                f"The limb goes completely dead — numb and unresponsive. "
                f"Requires Regrowth to restore."
            )

        target_hp = 0
        if hasattr(target, "current_hp"):
            target_hp = target.current_hp
        elif isinstance(target, dict):
            target_hp = target.get("hp", 0)

        return {
            "hit": True,
            "critical": critical,
            "roll": roll,
            "total": total,
            "damage": damage,
            "location": location,
            "effect": effect,
            "message": msg,
            "target_alive": target_hp > 0,
        }

    # ─── Shardplate defense ───────────────────────────────────────────

    def shardplate_defense(
        self,
        defender: Any,
        damage: int,
        plate_state: Optional[dict] = None,
    ) -> dict:
        """
        Apply Shardplate damage absorption mechanics.

        Shardplate absorbs a significant portion of incoming damage. Large hits
        crack the plate; repeated cracks eventually shatter it. The plate
        regenerates if the wearer has stormlight.

        Args:
            defender: Defender object with name attribute.
            damage: Incoming raw damage.
            plate_state: Optional dict tracking plate integrity
                         {'integrity': int, 'cracks': int}. Created if None.

        Returns:
            Dict with keys: absorbed (int), actual_damage (int),
            plate_cracked (bool), plate_shattered (bool),
            integrity (int), cracks (int), message (str).
        """
        if plate_state is None:
            plate_state = {"integrity": 100, "cracks": 0}

        defender_name = defender.name if hasattr(defender, "name") else str(defender)
        absorbed = min(damage, damage * 3 // 4)  # Plate absorbs 75% of damage
        actual_damage = damage - absorbed

        plate_cracked = False
        plate_shattered = False

        # Large hits crack the plate
        if damage >= 15:
            plate_state["cracks"] += 1
            plate_state["integrity"] -= 20
            plate_cracked = True

        # Massive hits shatter individual segments
        if damage >= 30:
            plate_state["cracks"] += 1
            plate_state["integrity"] -= 20

        # Check for shattering
        if plate_state["integrity"] <= 0:
            plate_shattered = True
            plate_state["integrity"] = 0

        msg_parts = [
            f"{defender_name}'s Shardplate absorbs {absorbed} damage "
            f"(actual: {actual_damage})."
        ]
        if plate_cracked:
            msg_parts.append(
                f"Plate cracks! Integrity: {plate_state['integrity']}%."
            )
        if plate_shattered:
            msg_parts.append("Shardplate shatters! No longer providing protection.")

        return {
            "absorbed": absorbed,
            "actual_damage": actual_damage,
            "plate_cracked": plate_cracked,
            "plate_shattered": plate_shattered,
            "integrity": plate_state["integrity"],
            "cracks": plate_state["cracks"],
            "plate_state": plate_state,
            "message": " ".join(msg_parts),
        }

    # ─── Duel of Champions ────────────────────────────────────────────

    def duel_of_champions(
        self,
        attacker: Any,
        defender: Any,
        rounds: int = 5,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        Resolve an Alethi formal duel of champions.

        Duels proceed round by round. Each round, both combatants attack.
        The first to be reduced to 0 HP loses. Standard Alethi duels are
        to first blood (half HP), Shards duels to submission or death.

        Args:
            attacker: Character dict or object with name, defense, max_hp, current_hp.
            defender: Character dict or object with name, defense, max_hp, current_hp.
            rounds: Maximum rounds before the duel is called a draw.
            rng: Optional Random override.

        Returns:
            Dict with keys: winner (str or None), rounds_fought (int),
            log (list of str), attacker_hp (int), defender_hp (int).
        """
        r = rng or self._rng
        log: List[str] = []

        # Normalise to dicts for easy manipulation
        def _to_combat_dict(c: Any) -> dict:
            if isinstance(c, dict):
                return {
                    "name": c.get("name", "Combatant"),
                    "hp": c.get("hp", c.get("current_hp", 20)),
                    "defense": c.get("defense", 10),
                    "atk_mod": c.get("atk_mod", 3),
                }
            return {
                "name": getattr(c, "name", "Combatant"),
                "hp": getattr(c, "current_hp", 20),
                "defense": getattr(c, "defense", 10),
                "atk_mod": getattr(c, "modifier", lambda a: 2)("strength"),
            }

        atk = _to_combat_dict(attacker)
        dfn = _to_combat_dict(defender)
        winner = None

        for round_num in range(1, rounds + 1):
            log.append(f"--- Round {round_num} ---")

            # Attacker's strike
            roll_a = r.randint(1, 20)
            total_a = roll_a + atk["atk_mod"]
            if roll_a == 20 or (roll_a != 1 and total_a >= dfn["defense"]):
                dmg_a = r.randint(3, 10)
                if roll_a == 20:
                    dmg_a *= 2
                dfn["hp"] -= dmg_a
                log.append(
                    f"  {atk['name']} hits {dfn['name']} for {dmg_a} "
                    f"(roll {roll_a}+{atk['atk_mod']}={total_a} vs {dfn['defense']})."
                )
            else:
                log.append(
                    f"  {atk['name']} misses "
                    f"(roll {roll_a}+{atk['atk_mod']}={total_a} vs {dfn['defense']})."
                )

            if dfn["hp"] <= 0:
                winner = atk["name"]
                log.append(f"  {dfn['name']} falls! {atk['name']} wins the duel!")
                break

            # Defender's counter-strike
            roll_d = r.randint(1, 20)
            total_d = roll_d + dfn["atk_mod"]
            if roll_d == 20 or (roll_d != 1 and total_d >= atk["defense"]):
                dmg_d = r.randint(3, 10)
                if roll_d == 20:
                    dmg_d *= 2
                atk["hp"] -= dmg_d
                log.append(
                    f"  {dfn['name']} counter-strikes {atk['name']} for {dmg_d} "
                    f"(roll {roll_d}+{dfn['atk_mod']}={total_d} vs {atk['defense']})."
                )
            else:
                log.append(
                    f"  {dfn['name']} misses "
                    f"(roll {roll_d}+{dfn['atk_mod']}={total_d} vs {atk['defense']})."
                )

            if atk["hp"] <= 0:
                winner = dfn["name"]
                log.append(f"  {atk['name']} falls! {dfn['name']} wins the duel!")
                break

        if winner is None:
            log.append(f"Duel concludes after {rounds} rounds — a draw is called.")

        return {
            "winner": winner,
            "rounds_fought": min(round_num, rounds),
            "log": log,
            "attacker_hp": max(0, atk["hp"]),
            "defender_hp": max(0, dfn["hp"]),
        }

    # ─── Surge combat ────────────────────────────────────────────────

    def resolve_surge_combat(
        self,
        character: Any,
        surge_manager: Any,
        targets: List[Any],
        power_name: str,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        Resolve a surge-based combat action through the SurgeManager.

        Args:
            character: The using character (CosmereCharacter).
            surge_manager: SurgeManager for the character.
            targets: List of target dicts or objects.
            power_name: Name of the power to activate.
            rng: Optional Random override.

        Returns:
            Dict with keys: success (bool), power_activated (str or None),
            targets_affected (list), stormlight (int), message (str).
        """
        r = rng or self._rng
        result = surge_manager.use_power(power_name)
        if not result["success"]:
            return {
                "success": False,
                "power_activated": None,
                "targets_affected": [],
                "stormlight": surge_manager.stormlight,
                "message": result["message"],
            }

        affected: List[str] = []
        power = result.get("power", {})
        power_desc = power.get("description", "")

        # Apply generic surge damage/effect to targets based on power type
        _surge_damage_powers = {
            "basic lashing", "full lashing", "reverse lashing",
            "verdict strike", "erosion", "ashspren combustion",
        }
        if power_name.lower() in _surge_damage_powers:
            for target in targets:
                t_name = getattr(target, "name", None) or (
                    target.get("name", "Enemy") if isinstance(target, dict) else "Enemy"
                )
                dmg = r.randint(4, 12)
                if hasattr(target, "take_damage"):
                    target.take_damage(dmg)
                elif isinstance(target, dict):
                    target["hp"] = max(0, target.get("hp", 0) - dmg)
                affected.append(f"{t_name} ({dmg} damage)")

        char_name = character.name if hasattr(character, "name") else str(character)
        affected_str = ", ".join(affected) if affected else "no targets directly damaged"

        return {
            "success": True,
            "power_activated": power_name,
            "targets_affected": affected,
            "stormlight": surge_manager.stormlight,
            "message": (
                f"{char_name} activates {power_name}! {power_desc}\n"
                f"Affected: {affected_str}. "
                f"Stormlight remaining: {surge_manager.stormlight}."
            ),
        }


__all__ = ["AttackResult", "CosmereCombatResolver"]

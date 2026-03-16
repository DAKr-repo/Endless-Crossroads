"""
codex.games.dnd5e.combat
==========================
D&D 5e combat resolution: attack rolls, damage, saving throws, enemy AI.

Provides:
  - WEAPON_PROPERTIES: SRD weapon data (damage dice, type, properties)
  - AttackResult / SavingThrowResult dataclasses with human-readable describe()
  - DnD5eCombatResolver: attack_roll, spell_attack, saving_throw, enemy_turn
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =========================================================================
# PROFICIENCY BY LEVEL
# =========================================================================

PROFICIENCY_BY_LEVEL: Dict[int, int] = {
    1: 2, 2: 2, 3: 2, 4: 2,
    5: 3, 6: 3, 7: 3, 8: 3,
    9: 4, 10: 4, 11: 4, 12: 4,
    13: 5, 14: 5, 15: 5, 16: 5,
    17: 6, 18: 6, 19: 6, 20: 6,
}


# =========================================================================
# WEAPON PROPERTIES TABLE (SRD 5.1)
# =========================================================================

WEAPON_PROPERTIES: Dict[str, Dict[str, Any]] = {
    # ── Simple melee ──────────────────────────────────────────────────
    "club": {
        "damage": "1d4", "type": "bludgeoning",
        "properties": ["Light"],
    },
    "dagger": {
        "damage": "1d4", "type": "piercing",
        "properties": ["Finesse", "Light", "Thrown"],
    },
    "greatclub": {
        "damage": "1d8", "type": "bludgeoning",
        "properties": ["Two-Handed"],
    },
    "handaxe": {
        "damage": "1d6", "type": "slashing",
        "properties": ["Light", "Thrown"],
    },
    "javelin": {
        "damage": "1d6", "type": "piercing",
        "properties": ["Thrown"],
    },
    "light hammer": {
        "damage": "1d4", "type": "bludgeoning",
        "properties": ["Light", "Thrown"],
    },
    "mace": {
        "damage": "1d6", "type": "bludgeoning",
        "properties": [],
    },
    "quarterstaff": {
        "damage": "1d6", "type": "bludgeoning",
        "properties": ["Versatile"],
    },
    "sickle": {
        "damage": "1d4", "type": "slashing",
        "properties": ["Light"],
    },
    "spear": {
        "damage": "1d6", "type": "piercing",
        "properties": ["Thrown", "Versatile"],
    },
    # ── Simple ranged ─────────────────────────────────────────────────
    "light crossbow": {
        "damage": "1d8", "type": "piercing",
        "properties": ["Ammunition", "Loading", "Two-Handed"],
    },
    "shortbow": {
        "damage": "1d6", "type": "piercing",
        "properties": ["Ammunition", "Two-Handed"],
    },
    # ── Martial melee ─────────────────────────────────────────────────
    "battleaxe": {
        "damage": "1d8", "type": "slashing",
        "properties": ["Versatile"],
    },
    "flail": {
        "damage": "1d8", "type": "bludgeoning",
        "properties": [],
    },
    "glaive": {
        "damage": "1d10", "type": "slashing",
        "properties": ["Heavy", "Reach", "Two-Handed"],
    },
    "greataxe": {
        "damage": "1d12", "type": "slashing",
        "properties": ["Heavy", "Two-Handed"],
    },
    "greatsword": {
        "damage": "2d6", "type": "slashing",
        "properties": ["Heavy", "Two-Handed"],
    },
    "halberd": {
        "damage": "1d10", "type": "slashing",
        "properties": ["Heavy", "Reach", "Two-Handed"],
    },
    "lance": {
        "damage": "1d12", "type": "piercing",
        "properties": ["Reach", "Special"],
    },
    "longsword": {
        "damage": "1d8", "type": "slashing",
        "properties": ["Versatile"],
    },
    "maul": {
        "damage": "2d6", "type": "bludgeoning",
        "properties": ["Heavy", "Two-Handed"],
    },
    "morningstar": {
        "damage": "1d8", "type": "piercing",
        "properties": [],
    },
    "pike": {
        "damage": "1d10", "type": "piercing",
        "properties": ["Heavy", "Reach", "Two-Handed"],
    },
    "rapier": {
        "damage": "1d8", "type": "piercing",
        "properties": ["Finesse"],
    },
    "scimitar": {
        "damage": "1d6", "type": "slashing",
        "properties": ["Finesse", "Light"],
    },
    "shortsword": {
        "damage": "1d6", "type": "piercing",
        "properties": ["Finesse", "Light"],
    },
    "trident": {
        "damage": "1d6", "type": "piercing",
        "properties": ["Thrown", "Versatile"],
    },
    "war pick": {
        "damage": "1d8", "type": "piercing",
        "properties": [],
    },
    "warhammer": {
        "damage": "1d8", "type": "bludgeoning",
        "properties": ["Versatile"],
    },
    "whip": {
        "damage": "1d4", "type": "slashing",
        "properties": ["Finesse", "Reach"],
    },
    # ── Martial ranged ────────────────────────────────────────────────
    "hand crossbow": {
        "damage": "1d6", "type": "piercing",
        "properties": ["Ammunition", "Light", "Loading"],
    },
    "heavy crossbow": {
        "damage": "1d10", "type": "piercing",
        "properties": ["Ammunition", "Heavy", "Loading", "Two-Handed"],
    },
    "longbow": {
        "damage": "1d8", "type": "piercing",
        "properties": ["Ammunition", "Heavy", "Two-Handed"],
    },
    # ── Default (unarmed) ─────────────────────────────────────────────
    "unarmed": {
        "damage": "1d1", "type": "bludgeoning",
        "properties": [],
    },
}


# =========================================================================
# DICE HELPERS
# =========================================================================

def parse_damage_dice(dice_str: str) -> Tuple[int, int]:
    """
    Parse a dice expression like '2d6' into (count, sides).

    Args:
        dice_str: Dice expression string (e.g. '1d8', '2d6').

    Returns:
        Tuple of (count, sides). Falls back to (1, 4) for invalid input.
    """
    try:
        parts = dice_str.lower().split("d")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 1, 4


def roll_damage(
    dice_str: str, modifier: int = 0, critical: bool = False
) -> int:
    """
    Roll damage dice and apply modifier.

    On a critical hit the dice count is doubled (before rolling) per 5e rules.

    Args:
        dice_str: Dice expression string (e.g. '1d8', '2d6').
        modifier: Flat bonus added to the total.
        critical: If True, double the number of dice rolled.

    Returns:
        Damage total (minimum 0 before the caller applies minimums).
    """
    count, sides = parse_damage_dice(dice_str)
    if critical:
        count *= 2
    total = sum(random.randint(1, sides) for _ in range(count)) + modifier
    return max(0, total)


# =========================================================================
# RESULT DATACLASSES
# =========================================================================

@dataclass
class AttackResult:
    """
    Encapsulates the outcome of a single attack roll.

    Attributes:
        attacker: Name of the attacking character/creature.
        target: Name of the target.
        roll: Raw d20 result.
        modifier: Total modifier applied to the roll.
        total: roll + modifier.
        ac: Target's armor class.
        hit: Whether the attack connected.
        critical: Whether a natural 20 was rolled.
        fumble: Whether a natural 1 was rolled.
        damage: Damage dealt (0 if missed).
        damage_type: Type of damage (slashing, piercing, etc.).
    """

    attacker: str
    target: str
    roll: int
    modifier: int
    total: int
    ac: int
    hit: bool
    critical: bool
    fumble: bool
    damage: int = 0
    damage_type: str = ""

    def describe(self) -> str:
        """Return a human-readable one-line description of the attack result."""
        if self.fumble:
            return f"{self.attacker} fumbles! (rolled 1)"
        if self.critical:
            return (
                f"{self.attacker} CRITICAL HIT on {self.target}! "
                f"{self.damage} {self.damage_type} damage."
            )
        if self.hit:
            return (
                f"{self.attacker} hits {self.target} "
                f"({self.total} vs AC {self.ac}) "
                f"for {self.damage} {self.damage_type} damage."
            )
        return (
            f"{self.attacker} misses {self.target} "
            f"({self.total} vs AC {self.ac})."
        )


@dataclass
class SavingThrowResult:
    """
    Encapsulates the outcome of a saving throw.

    Attributes:
        target: Name of the creature making the save.
        ability: Ability score used (e.g. 'dexterity').
        roll: Raw d20 result.
        modifier: Total modifier applied.
        total: roll + modifier.
        dc: Difficulty class to beat.
        success: True if total >= dc or natural 20.
        half_damage: If True, a successful save halves damage.
        damage: Base damage before halving.
    """

    target: str
    ability: str
    roll: int
    modifier: int
    total: int
    dc: int
    success: bool
    half_damage: bool = False
    damage: int = 0

    def describe(self) -> str:
        """Return a human-readable one-line description of the saving throw."""
        status = "succeeds" if self.success else "fails"
        line = (
            f"{self.target} {status} {self.ability} save "
            f"({self.total} vs DC {self.dc})."
        )
        if self.damage > 0:
            if self.success and self.half_damage:
                line += f" Takes {self.damage // 2} damage (halved)."
            elif not self.success:
                line += f" Takes {self.damage} damage."
        return line


# =========================================================================
# COMBAT RESOLVER
# =========================================================================

class DnD5eCombatResolver:
    """
    Resolves D&D 5e combat actions.

    Accepts an optional `random.Random` instance for deterministic testing.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        """
        Initialise the combat resolver.

        Args:
            rng: Optional seeded Random instance for deterministic tests.
        """
        self._rng = rng or random.Random()

    # ─── Attack rolls ──────────────────────────────────────────────────

    def attack_roll(
        self,
        attacker: Any,
        target_ac: int,
        weapon_name: str = "unarmed",
        ability_mod: int = 0,
        prof_bonus: int = 2,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> AttackResult:
        """
        Resolve a melee or ranged weapon attack roll.

        Advantage and disadvantage cancel each other out (both active = straight
        roll). On a hit, damage is rolled using the weapon's damage dice with
        the ability modifier. Critical hits double the dice count.

        Args:
            attacker: Character object (must have .name) or string name.
            target_ac: The target's armor class.
            weapon_name: Weapon name from WEAPON_PROPERTIES (default 'unarmed').
            ability_mod: Relevant ability modifier (STR or DEX).
            prof_bonus: Character's proficiency bonus.
            advantage: Roll two d20s and take the higher.
            disadvantage: Roll two d20s and take the lower.

        Returns:
            AttackResult with full resolution data.
        """
        weapon = WEAPON_PROPERTIES.get(
            weapon_name.lower(),
            {"damage": "1d4", "type": "bludgeoning", "properties": []},
        )

        # Roll d20 with advantage/disadvantage
        r1 = self._rng.randint(1, 20)
        r2 = self._rng.randint(1, 20)
        if advantage and not disadvantage:
            roll = max(r1, r2)
        elif disadvantage and not advantage:
            roll = min(r1, r2)
        else:
            roll = r1

        modifier = ability_mod + prof_bonus
        total = roll + modifier

        critical = roll == 20
        fumble = roll == 1
        hit = critical or (not fumble and total >= target_ac)

        damage = 0
        if hit:
            damage = roll_damage(weapon["damage"], ability_mod, critical=critical)
            damage = max(1, damage)

        attacker_name = attacker.name if hasattr(attacker, "name") else str(attacker)
        return AttackResult(
            attacker=attacker_name,
            target="target",
            roll=roll,
            modifier=modifier,
            total=total,
            ac=target_ac,
            hit=hit,
            critical=critical,
            fumble=fumble,
            damage=damage,
            damage_type=weapon.get("type", "bludgeoning"),
        )

    def spell_attack(
        self,
        attacker: Any,
        target_ac: int,
        spell_name: str,
        spell_level: int,
        ability_mod: int = 0,
        prof_bonus: int = 2,
        damage_dice: str = "1d10",
        damage_type: str = "force",
    ) -> AttackResult:
        """
        Resolve a spell attack roll (e.g. Eldritch Blast, Guiding Bolt).

        Spell attacks do not use ability modifier on damage (only on the hit
        roll). Critical hits double the damage dice.

        Args:
            attacker: Character object (must have .name) or string name.
            target_ac: The target's armor class.
            spell_name: Name of the spell being cast.
            spell_level: Slot level at which the spell is cast.
            ability_mod: Spellcasting ability modifier (added to attack roll).
            prof_bonus: Character's proficiency bonus (added to attack roll).
            damage_dice: Damage dice expression (default '1d10').
            damage_type: Damage type (default 'force').

        Returns:
            AttackResult with full resolution data.
        """
        roll = self._rng.randint(1, 20)
        modifier = ability_mod + prof_bonus
        total = roll + modifier
        critical = roll == 20
        fumble = roll == 1
        hit = critical or (not fumble and total >= target_ac)

        damage = 0
        if hit:
            # Spell damage does not add ability modifier
            damage = roll_damage(damage_dice, modifier=0, critical=critical)
            damage = max(1, damage)

        attacker_name = attacker.name if hasattr(attacker, "name") else str(attacker)
        return AttackResult(
            attacker=attacker_name,
            target="target",
            roll=roll,
            modifier=modifier,
            total=total,
            ac=target_ac,
            hit=hit,
            critical=critical,
            fumble=fumble,
            damage=damage,
            damage_type=damage_type,
        )

    # ─── Saving throws ─────────────────────────────────────────────────

    def saving_throw(
        self,
        target: Any,
        ability: str,
        dc: int,
        damage_dice: str = "0d0",
        half_on_save: bool = True,
    ) -> SavingThrowResult:
        """
        Resolve a saving throw against a spell or effect.

        The target's modifier for the ability is derived from the raw score
        on the target object (attribute lookup). A natural 20 always succeeds.

        Args:
            target: Character/creature object with ability score attributes.
            ability: Ability name as string (e.g. 'dexterity').
            dc: Difficulty class.
            damage_dice: Damage dice expression ('0d0' for no damage effects).
            half_on_save: If True, a successful save deals half damage.

        Returns:
            SavingThrowResult with full resolution data.
        """
        score = getattr(target, ability, 10) if hasattr(target, ability) else 10
        mod = (score - 10) // 2
        roll = self._rng.randint(1, 20)
        total = roll + mod
        success = (roll == 20) or (total >= dc)

        damage = roll_damage(damage_dice) if damage_dice != "0d0" else 0

        target_name = target.name if hasattr(target, "name") else str(target)
        return SavingThrowResult(
            target=target_name,
            ability=ability,
            roll=roll,
            modifier=mod,
            total=total,
            dc=dc,
            success=success,
            half_damage=half_on_save,
            damage=damage,
        )

    # ─── Enemy AI ─────────────────────────────────────────────────────

    def enemy_turn(self, enemy: dict, party: list) -> List[AttackResult]:
        """
        Simple enemy AI: attack a random living party member.

        Enemies use a flat attack bonus derived from `enemy["attack"]`.
        Critical hits double base damage. All damage is applied directly
        via `target.take_damage(damage)`.

        Args:
            enemy: Enemy dict with keys: name, hp, attack.
            party: List of character objects with is_alive(), armor_class,
                   take_damage(), and name attributes.

        Returns:
            List of AttackResult (empty if no valid targets or enemy is dead).
        """
        alive = [c for c in party if hasattr(c, "is_alive") and c.is_alive()]
        if not alive or enemy.get("hp", 0) <= 0:
            return []

        target = self._rng.choice(alive)
        atk_bonus = enemy.get("attack", 3)

        roll = self._rng.randint(1, 20)
        total = roll + atk_bonus
        critical = roll == 20
        fumble = roll == 1
        hit = critical or (not fumble and total >= target.armor_class)

        damage = 0
        if hit:
            base = self._rng.randint(1, 6) + max(0, atk_bonus // 2)
            damage = base * 2 if critical else base
            damage = max(1, damage)
            target.take_damage(damage)

        return [
            AttackResult(
                attacker=enemy.get("name", "Enemy"),
                target=target.name,
                roll=roll,
                modifier=atk_bonus,
                total=total,
                ac=target.armor_class,
                hit=hit,
                critical=critical,
                fumble=fumble,
                damage=damage,
                damage_type="slashing",
            )
        ]

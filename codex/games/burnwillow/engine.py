#!/usr/bin/env python3
"""
Burnwillow Game Engine v0.1
A roguelike dungeon crawler where "You are what you wear."

This module implements the core mechanics from the Burnwillow SRD:
- 5d6 dice pool system with stat modifiers
- Gear-based progression (no leveling)
- 10-slot equipment system (GearGrid)
- Four core stats: Might, Wits, Grit, Aether
- DoomClock for dungeon turns

Architecture: Pure deterministic game logic (The Heart).
No I/O, no AI inference, no UI rendering.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import random
import json


# =============================================================================
# CORE ENUMS & CONSTANTS
# =============================================================================

class StatType(Enum):
    """The Four Pillars of character attributes."""
    MIGHT = "MIGHT"      # Physical: Strength, melee, athletics
    WITS = "WITS"        # Mental: Perception, ranged, mechanisms
    GRIT = "GRIT"        # Fortitude: Health, stamina, resistance
    AETHER = "AETHER"    # Magical: Willpower, spellcasting, attunement


class GearSlot(Enum):
    """The 10 equipment slots (The GearGrid)."""
    HEAD = "Head"
    SHOULDERS = "Shoulders"
    CHEST = "Chest"
    ARMS = "Arms"
    LEGS = "Legs"
    R_HAND = "R.Hand"
    L_HAND = "L.Hand"
    R_RING = "R.Ring"
    L_RING = "L.Ring"
    NECK = "Neck"


class GearTier(Enum):
    """Material quality determines dice pool bonus."""
    TIER_0 = 0  # Unarmed/Naked (no bonus dice)
    TIER_I = 1  # Scrap/Wood (+1d6)
    TIER_II = 2  # Iron/Leather (+2d6)
    TIER_III = 3  # Steel/Silver (+3d6)
    TIER_IV = 4  # Mithral/Gold (+4d6)


# Difficulty Classes (from SRD)
class DC(Enum):
    """Standard Difficulty Classes for checks."""
    ROUTINE = 8   # Breaking crates, climbing rope
    HARD = 12     # Picking locks, jumping chasms
    HEROIC = 16   # Bending iron bars, deciphering runes
    LEGENDARY = 20  # Resisting dragon fear, swimming up waterfalls


# =============================================================================
# STAT SYSTEM
# =============================================================================

def calculate_stat_mod(score: int) -> int:
    """Calculate the modifier for a stat score using standard D&D floor formula.

    (score - 10) // 2  — e.g. 8→-1, 10→0, 12→+1, 14→+2, 18→+4.
    """
    return (score - 10) // 2


def roll_4d6_drop_lowest() -> int:
    """
    Roll 4d6 and drop the lowest die (character creation).

    Returns:
        Stat score (3-18)
    """
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort()
    return sum(rolls[1:])  # Drop lowest (index 0)


# =============================================================================
# DICE ENGINE
# =============================================================================

@dataclass
class CheckResult:
    """Result of a dice pool check."""
    success: bool
    total: int
    rolls: List[int]
    modifier: int
    dc: int
    dice_count: int

    def __str__(self) -> str:
        """Human-readable result."""
        outcome = "SUCCESS" if self.success else "FAILURE"
        return (f"{outcome}: {self.dice_count}d6{self.modifier:+d} = "
                f"{self.rolls} + {self.modifier} = {self.total} vs DC {self.dc}")


def roll_check(dice_count: int, modifier: int, dc: int) -> CheckResult:
    """
    Roll the core Burnwillow check: [Dice Pool]d6 + Modifier vs DC.

    Args:
        dice_count: Number of d6 to roll (1-5, capped at 5)
        modifier: Stat modifier to add
        dc: Difficulty Class to beat

    Returns:
        CheckResult with success status and details
    """
    # Cap at 5d6 (SRD rule)
    dice_count = max(1, min(5, dice_count))

    # Roll the pool
    rolls = [random.randint(1, 6) for _ in range(dice_count)]
    total = sum(rolls) + modifier

    return CheckResult(
        success=total >= dc,
        total=total,
        rolls=rolls,
        modifier=modifier,
        dc=dc,
        dice_count=dice_count
    )


def roll_dice_pool(dice_count: int, modifier: int, dc: int) -> dict:
    """
    Roll a Burnwillow dice pool check (dict-based interface).

    Args:
        dice_count: Number of d6s to roll (will be capped at 5)
        modifier: Stat modifier to add
        dc: Difficulty Class to beat

    Returns:
        {
            'rolls': [int, ...],      # Individual die results
            'total': int,             # sum(rolls) + modifier
            'modifier': int,          # The modifier used
            'dc': int,                # The DC checked against
            'success': bool,          # total >= dc
            'crit': bool,             # All dice show 6 (optional critical)
            'fumble': bool            # All dice show 1 (optional fumble)
        }
    """
    # ENFORCE MAX 5d6 (hard cap per GDD)
    dice_count = min(dice_count, 5)

    # Roll the pool
    rolls = [random.randint(1, 6) for _ in range(dice_count)]
    total = sum(rolls) + modifier
    success = total >= dc

    # Check for critical (all 6s) or fumble (all 1s)
    crit = all(r == 6 for r in rolls) if rolls else False
    fumble = all(r == 1 for r in rolls) if rolls else False

    return {
        'rolls': rolls,
        'total': total,
        'modifier': modifier,
        'dc': dc,
        'success': success,
        'crit': crit,
        'fumble': fumble
    }


def roll_ambush(wits_modifier: int, enemy_passive_dc: int) -> dict:
    """
    Roll for ambush (surprise round).

    Args:
        wits_modifier: Leader's Wits modifier
        enemy_passive_dc: Enemy's Passive Perception DC

    Returns:
        {
            'rolls': [...],
            'total': int,
            'modifier': int,
            'dc': int,
            'success': bool,
            'ambush_round': bool  # True = party acts first, enemies skip
        }
    """
    # Ambush uses base 1d6 + Wits modifier vs Enemy Passive DC
    result = roll_dice_pool(1, wits_modifier, enemy_passive_dc)
    result['ambush_round'] = result['success']

    return result


# =============================================================================
# GEAR SYSTEM
# =============================================================================


# Slot-to-stat pool mapping for dice pool segmentation (WO V20.3)
# Fixed slots have a default pool; wildcard slots (SHOULDERS, NECK, rings)
# require GearItem.primary_stat to contribute dice.
SLOT_STAT_MAP: Dict[GearSlot, StatType] = {
    GearSlot.R_HAND:  StatType.MIGHT,
    GearSlot.L_HAND:  StatType.MIGHT,
    GearSlot.HEAD:    StatType.WITS,
    GearSlot.ARMS:    StatType.WITS,
    GearSlot.CHEST:   StatType.GRIT,
    GearSlot.LEGS:    StatType.GRIT,
    # SHOULDERS, NECK, R_RING, L_RING are wildcard — not listed here
}

# Wildcard slots: must use GearItem.primary_stat to contribute to a pool
WILDCARD_SLOTS = frozenset({
    GearSlot.SHOULDERS, GearSlot.NECK, GearSlot.R_RING, GearSlot.L_RING,
})


@dataclass
class GearItem:
    """A single piece of equipment."""
    name: str
    slot: GearSlot
    tier: GearTier
    stat_bonuses: Dict[StatType, int] = field(default_factory=dict)
    damage_reduction: int = 0  # Armor DR
    defense_bonus: int = 0     # Armor defense bonus (contributes to get_defense())
    special_traits: List[str] = field(default_factory=list)  # e.g., "[Lockpick]", "[Intercept]"
    description: str = ""
    two_handed: bool = False  # If True, blocks both R.Hand and L.Hand
    weight: float = 1.0  # Default weight in abstract units
    primary_stat: Optional[StatType] = None  # Overrides SLOT_STAT_MAP for dice pool

    def get_dice_bonus(self) -> int:
        """Get the dice pool bonus from this item's tier."""
        return self.tier.value

    def get_pool_stat(self) -> Optional[StatType]:
        """Which stat pool does this item contribute dice to?
        Returns primary_stat if set, else SLOT_STAT_MAP default, else None."""
        if self.primary_stat is not None:
            return self.primary_stat
        return SLOT_STAT_MAP.get(self.slot)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        d = {
            "name": self.name,
            "slot": self.slot.value,
            "tier": self.tier.value,
            "stat_bonuses": {stat.value: bonus for stat, bonus in self.stat_bonuses.items()},
            "damage_reduction": self.damage_reduction,
            "defense_bonus": self.defense_bonus,
            "special_traits": self.special_traits,
            "description": self.description,
            "weight": self.weight,
        }
        if self.two_handed:
            d["two_handed"] = True
        if self.primary_stat is not None:
            d["primary_stat"] = self.primary_stat.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GearItem":
        """Deserialize from dict."""
        ps = data.get("primary_stat")
        return cls(
            name=data["name"],
            slot=GearSlot(data["slot"]),
            tier=GearTier(data["tier"]),
            stat_bonuses={StatType(k): v for k, v in data.get("stat_bonuses", {}).items()},
            damage_reduction=data.get("damage_reduction", 0),
            defense_bonus=data.get("defense_bonus", 0),
            special_traits=data.get("special_traits", []),
            description=data.get("description", ""),
            two_handed=data.get("two_handed", False),
            primary_stat=StatType(ps) if ps else None,
        )


@dataclass
class GearGrid:
    """The 10-slot equipment system."""
    slots: Dict[GearSlot, Optional[GearItem]] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize empty slots."""
        if not self.slots:
            self.slots = {slot: None for slot in GearSlot}

    def equip(self, item: GearItem) -> List[GearItem]:
        """
        Equip an item in its slot. Handles 1H/2H logic.

        1H weapons can go in R.Hand or L.Hand.
        2H weapons go in R.Hand and clear L.Hand.
        Equipping a 1H item clears any 2H weapon in R.Hand.

        Returns:
            List of displaced items (0-2 items).
        """
        displaced: List[GearItem] = []

        if item.two_handed:
            # 2H: occupy R.Hand, force-clear L.Hand
            item_copy = GearItem(
                name=item.name, slot=GearSlot.R_HAND, tier=item.tier,
                stat_bonuses=item.stat_bonuses, damage_reduction=item.damage_reduction,
                defense_bonus=item.defense_bonus,
                special_traits=item.special_traits, description=item.description,
                two_handed=True,
            )
            old_r = self.slots.get(GearSlot.R_HAND)
            if old_r:
                displaced.append(old_r)
            old_l = self.slots.get(GearSlot.L_HAND)
            if old_l:
                displaced.append(old_l)
            self.slots[GearSlot.R_HAND] = item_copy
            self.slots[GearSlot.L_HAND] = None
            return displaced

        # Non-2H: check if equipping in a hand slot while a 2H is active
        if item.slot in (GearSlot.R_HAND, GearSlot.L_HAND):
            r_hand = self.slots.get(GearSlot.R_HAND)
            if r_hand and r_hand.two_handed:
                # Unequip the 2H weapon
                displaced.append(r_hand)
                self.slots[GearSlot.R_HAND] = None

        old_item = self.slots.get(item.slot)
        if old_item:
            displaced.append(old_item)
        self.slots[item.slot] = item
        return displaced

    def unequip(self, slot: GearSlot) -> Optional[GearItem]:
        """Remove item from slot."""
        item = self.slots.get(slot)
        self.slots[slot] = None
        return item

    def get_total_dice_bonus(self, stat_type: StatType) -> int:
        """
        Calculate dice pool for a specific stat (WO V20.3 pool segmentation).

        Each gear piece contributes its tier dice to ONE pool:
          - Fixed slots use SLOT_STAT_MAP (hands->MIGHT, head/arms->WITS, chest/legs->GRIT)
          - Wildcard slots (shoulders/neck/rings) use item.primary_stat
          - Items with primary_stat override SLOT_STAT_MAP on any slot

        Returns base 1d6 + matching gear tier bonuses, capped at 5d6.
        """
        total_dice = 1  # Base "naked" die

        for item in self.slots.values():
            if item and item.get_pool_stat() == stat_type:
                total_dice += item.get_dice_bonus()

        return min(5, total_dice)

    def get_pool_breakdown(self, stat_type: StatType) -> Dict[str, int]:
        """Get per-slot dice contribution for a stat pool (UI display)."""
        breakdown = {}
        for slot, item in self.slots.items():
            if item and item.get_pool_stat() == stat_type:
                breakdown[slot.value] = item.get_dice_bonus()
        return breakdown

    def get_stat_bonus(self, stat_type: StatType) -> int:
        """Get total flat stat bonus from equipped gear."""
        total = 0
        for item in self.slots.values():
            if item and stat_type in item.stat_bonuses:
                total += item.stat_bonuses[stat_type]
        return total

    def get_total_dr(self) -> int:
        """Get total Damage Reduction from armor."""
        return sum(item.damage_reduction for item in self.slots.values() if item)

    def has_trait(self, trait: str) -> bool:
        """Check if any equipped gear has a special trait."""
        for item in self.slots.values():
            if item and trait in item.special_traits:
                return True
        return False

    def get_total_weight(self) -> float:
        """Sum weight of all equipped items."""
        return sum(item.weight for item in self.slots.values() if item)

    def to_dict(self) -> dict:
        """Serialize to JSON."""
        return {
            slot.value: (item.to_dict() if item else None)
            for slot, item in self.slots.items()
        }

    # Slot name migration for corrupted/variant save data
    _SLOT_MIGRATION = {
        "hands": "R.Hand", "right_hand": "R.Hand", "left_hand": "L.Hand",
        "right hand": "R.Hand", "left hand": "L.Hand",
        "r_hand": "R.Hand", "l_hand": "L.Hand",
    }

    @classmethod
    def from_dict(cls, data: dict) -> "GearGrid":
        """Deserialize from JSON."""
        grid = cls()
        for slot_name, item_data in data.items():
            if item_data:
                migrated = cls._SLOT_MIGRATION.get(slot_name, slot_name)
                try:
                    slot = GearSlot(migrated)
                except ValueError:
                    continue  # Silently skip unrecognized slot names
                grid.slots[slot] = GearItem.from_dict(item_data)
        return grid


# =============================================================================
# CHARACTER SYSTEM
# =============================================================================

@dataclass
class Character:
    """A Burnwillow adventurer."""
    name: str

    # Core Stats (4d6 drop lowest)
    might: int
    wits: int
    grit: int
    aether: int

    # Derived Stats
    max_hp: int = field(init=False)
    current_hp: int = field(init=False)
    base_defense: int = field(init=False)  # 10 + Wits modifier

    # Equipment
    gear: GearGrid = field(default_factory=GearGrid)

    # Inventory (not worn) — stable indices via dict
    inventory: Dict[int, GearItem] = field(default_factory=dict)
    _next_inv_id: int = field(default=0, repr=False)
    keys: int = 0    # Consumable lock openers
    scrap: int = 0   # Crafting resource for forge upgrades
    memory_seeds: List[dict] = field(default_factory=list)  # Each: {name, tier, deciphered}

    def __post_init__(self):
        """Calculate derived stats."""
        self.max_hp = 10 + calculate_stat_mod(self.grit)
        self.current_hp = self.max_hp
        self.base_defense = 10 + calculate_stat_mod(self.wits)

    def recalculate_hp(self):
        """Recalculate max HP from current Grit. Preserves damage taken."""
        damage_taken = self.max_hp - self.current_hp
        self.max_hp = 10 + calculate_stat_mod(self.grit)
        self.current_hp = max(1, self.max_hp - damage_taken)

    # Stat Accessors
    def get_stat_mod(self, stat_type: StatType) -> int:
        """Get total modifier for a stat (base + gear bonuses)."""
        base_score = getattr(self, stat_type.value.lower())
        base_mod = calculate_stat_mod(base_score)
        gear_bonus = self.gear.get_stat_bonus(stat_type)
        return base_mod + gear_bonus

    def get_defense(self) -> int:
        """Get total Defense (AC).

        Base defense (10 + Wits mod) plus defense_bonus from armor pieces
        equipped in body slots (Chest, Arms, Legs, Feet).
        """
        armor_slots = ("Chest", "Arms", "Legs", "Feet")
        armor_bonus = sum(
            item.defense_bonus
            for slot, item in self.gear.slots.items()
            if slot.value in armor_slots and item
        )
        return self.base_defense + armor_bonus

    # Action Methods
    def make_check(self, stat_type: StatType, dc: int) -> CheckResult:
        """
        Make a skill check with a stat.

        Args:
            stat_type: Which stat to use
            dc: Difficulty Class

        Returns:
            CheckResult
        """
        dice_count = self.gear.get_total_dice_bonus(stat_type)
        modifier = self.get_stat_mod(stat_type)
        return roll_check(dice_count, modifier, dc)

    def take_damage(self, amount: int) -> int:
        """
        Apply damage after DR reduction.

        Args:
            amount: Raw damage

        Returns:
            Actual HP lost
        """
        dr = self.gear.get_total_dr()
        actual_damage = max(1, amount - dr) if amount > 0 else 0
        self.current_hp = max(0, self.current_hp - actual_damage)
        return actual_damage

    def heal(self, amount: int) -> int:
        """
        Restore HP (cannot exceed max).

        Returns:
            Actual HP healed
        """
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp

    def is_alive(self) -> bool:
        """Check if character is still standing."""
        return self.current_hp > 0

    def can_pick_locks(self) -> bool:
        """Check if equipped with lockpicking gear."""
        return self.gear.has_trait("[Lockpick]")

    def add_to_inventory(self, item: GearItem) -> int:
        """Add item to backpack with a stable index. Returns the assigned index."""
        idx = self._next_inv_id
        self.inventory[idx] = item
        self._next_inv_id = idx + 1
        return idx

    def remove_from_inventory(self, idx: int) -> Optional[GearItem]:
        """Remove item by stable index. Returns the item or None."""
        return self.inventory.pop(idx, None)

    def check_encumbrance(self) -> dict:
        """Check slot-based encumbrance via the universal capacity manager.

        Uses SLOTS mode with a limit of 10 (the gear grid + backpack cap).
        """
        from codex.core.services.capacity_manager import check_capacity, CapacityMode
        current_slots = len(self.inventory)
        return check_capacity(CapacityMode.SLOTS, 10, current_slots)

    # Serialization
    def to_dict(self) -> dict:
        """Save character to JSON-compatible dict."""
        return {
            "name": self.name,
            "might": self.might,
            "wits": self.wits,
            "grit": self.grit,
            "aether": self.aether,
            "current_hp": self.current_hp,
            "gear": self.gear.to_dict(),
            "inventory": {str(k): v.to_dict() for k, v in self.inventory.items()},
            "keys": self.keys,
            "scrap": self.scrap,
            "memory_seeds": list(self.memory_seeds),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        """Load character from dict."""
        char = cls(
            name=data["name"],
            might=data["might"],
            wits=data["wits"],
            grit=data["grit"],
            aether=data["aether"]
        )
        char.gear = GearGrid.from_dict(data.get("gear", {}))

        # Support both legacy list and new dict inventory formats
        raw_inv = data.get("inventory", {})
        if isinstance(raw_inv, list):
            # Legacy: convert list to dict with sequential indices
            for item_data in raw_inv:
                item = GearItem.from_dict(item_data)
                char.add_to_inventory(item)
        else:
            for k, item_data in raw_inv.items():
                idx = int(k)
                char.inventory[idx] = GearItem.from_dict(item_data)
                if idx >= char._next_inv_id:
                    char._next_inv_id = idx + 1

        # Defensive HP recalculation: ensures max_hp reflects gear-buffed grit
        char.recalculate_hp()
        saved_hp = data.get("current_hp")
        if saved_hp is not None:
            char.current_hp = min(saved_hp, char.max_hp)

        char.keys = data.get("keys", 0)
        char.scrap = data.get("scrap", 0)
        char.memory_seeds = list(data.get("memory_seeds", []))
        return char

    @classmethod
    def create_random(cls, name: str) -> "Character":
        """Generate a new character with 4d6-drop-lowest stats."""
        return cls(
            name=name,
            might=roll_4d6_drop_lowest(),
            wits=roll_4d6_drop_lowest(),
            grit=roll_4d6_drop_lowest(),
            aether=roll_4d6_drop_lowest()
        )


# =============================================================================
# DOOM CLOCK (re-exported from codex.core.mechanics.clock)
# =============================================================================

from codex.core.mechanics.clock import UniversalClock, DoomClock  # noqa: F401


# =============================================================================
# CONFIG-DRIVEN CONTENT LOADERS
# Augment hardcoded CANOPY tables with entries from config/bestiary|loot|hazards/burnwillow.json
# =============================================================================

_BW_BESTIARY_CACHE: Optional[Dict[int, List[dict]]] = None
_BW_LOOT_CACHE: Optional[Dict[int, List[dict]]] = None
_BW_HAZARD_CACHE: Optional[Dict[int, List[dict]]] = None


def _load_bw_bestiary() -> Dict[int, List[dict]]:
    """Load burnwillow bestiary from config, empty dict if unavailable."""
    global _BW_BESTIARY_CACHE
    if _BW_BESTIARY_CACHE is not None:
        return _BW_BESTIARY_CACHE
    try:
        from codex.core.config_loader import load_config
        data = load_config("bestiary", "burnwillow")
        if data and "tiers" in data:
            result: Dict[int, List[dict]] = {}
            for tier_key, entries in data["tiers"].items():
                result[int(tier_key)] = entries
            _BW_BESTIARY_CACHE = result
            return result
    except Exception:
        pass
    _BW_BESTIARY_CACHE = {}
    return _BW_BESTIARY_CACHE


def _load_bw_loot() -> Dict[int, List[dict]]:
    """Load burnwillow loot from config, empty dict if unavailable."""
    global _BW_LOOT_CACHE
    if _BW_LOOT_CACHE is not None:
        return _BW_LOOT_CACHE
    try:
        from codex.core.config_loader import load_config
        data = load_config("loot", "burnwillow")
        if data and "tiers" in data:
            result: Dict[int, List[dict]] = {}
            for tier_key, items in data["tiers"].items():
                result[int(tier_key)] = items
            _BW_LOOT_CACHE = result
            return result
    except Exception:
        pass
    _BW_LOOT_CACHE = {}
    return _BW_LOOT_CACHE


def _load_bw_hazards() -> Dict[int, List[dict]]:
    """Load burnwillow hazards from config, empty dict if unavailable."""
    global _BW_HAZARD_CACHE
    if _BW_HAZARD_CACHE is not None:
        return _BW_HAZARD_CACHE
    try:
        from codex.core.config_loader import load_config
        data = load_config("hazards", "burnwillow")
        if data and "tiers" in data:
            result: Dict[int, List[dict]] = {}
            for tier_key, hazards in data["tiers"].items():
                result[int(tier_key)] = hazards
            _BW_HAZARD_CACHE = result
            return result
    except Exception:
        pass
    _BW_HAZARD_CACHE = {}
    return _BW_HAZARD_CACHE


# =============================================================================
# BURNWILLOW ENGINE
# =============================================================================

class BurnwillowEngine:
    """
    Roguelike dungeon crawler - You are what you wear.

    This is the main engine class that orchestrates:
    - Character creation and management
    - Dice rolling and checks
    - Gear system
    - DoomClock progression
    - Dungeon generation and navigation (NEW)

    Usage:
        engine = BurnwillowEngine()
        char = engine.create_character("Kael")
        engine.generate_dungeon(depth=3, seed=42)
        room = engine.get_current_room()
        result = char.make_check(StatType.MIGHT, DC.HARD.value)
        print(result)
    """

    system_id = "burnwillow"
    system_family = "BURNWILLOW"
    display_name = "Burnwillow"

    def __init__(self):
        """Initialize the engine."""
        self.character: Optional[Character] = None
        self.party: List[Character] = []
        self.doom_clock = DoomClock()

        # Set up default doom thresholds (customizable)
        self.doom_clock.thresholds = {
            5:  "The torches flicker. Distant growls echo.",
            10: "Wings beat in the dark. New creatures stir in the corridors.",
            13: "Patrol routes shift. Enemies are alert.",
            15: "Heavy footsteps from the entrance. Something is hunting.",
            17: "The Blight spreads. HP cannot be restored naturally.",
            20: "THE ROT HUNTER AWAKENS. It smells your blood.",
            22: "The dungeon seals. No escape.",
        }

        # Loot Pity Timer (WO-V17.0)
        self._turns_since_unique_loot: int = 0
        self._found_item_names: set = set()

        # Dungeon state (NEW)
        self.map_engine = None  # CodexMapEngine instance (lazy-initialized in generate_dungeon)
        self.dungeon_graph: Optional[Any] = None  # DungeonGraph from codex_map_engine
        self.populated_rooms: Dict[int, Any] = {}  # PopulatedRoom dict
        self.current_room_id: Optional[int] = None
        self.player_pos: Optional[Tuple[int, int]] = None  # Grid (x, y) position
        self.visited_rooms: set = set()  # Track exploration

        # Delta tracker for narrative storytelling (WO-V48.0)
        try:
            from codex.core.services.narrative_frame import DeltaTracker
            self.delta_tracker = DeltaTracker()
        except ImportError:
            self.delta_tracker = None

        # Civic Pulse — tick-driven civic event tracker
        try:
            from codex.core.services.town_crier import CivicPulse, WorldHistory, BURNWILLOW_CIVIC_EVENTS
            self.civic_pulse = CivicPulse(events=list(BURNWILLOW_CIVIC_EVENTS))
            self._world_history = WorldHistory()
            self.civic_pulse.attach_history(self._world_history)
        except ImportError:
            self.civic_pulse = None
            self._world_history = None

        # WO-V56.0: TraitHandler — gear trait resolution
        try:
            from codex.core.services.trait_handler import TraitHandler
            self._trait_handler = TraitHandler()
            self._trait_handler.register_resolver("burnwillow", BurnwillowTraitResolver())
        except ImportError:
            self._trait_handler = None

    # Loadout → gear indices into create_starter_gear() list
    LOADOUT_MAP = {
        "sellsword": [0, 1, 3],   # Sword + Jerkin + Gloves [Lockpick]
        "occultist": [2, 5, 1],   # Wand + Bell [Summon] + Jerkin
        "sentinel":  [0, 4, 1],   # Sword + Shield [Intercept] + Jerkin
        "archer":    [7, 1],       # Shortbow [Ranged] + Jerkin
        "vanguard":  [8, 1],       # Greatsword [Cleave] + Jerkin
        "scholar":   [9, 10, 3],   # Grimoire + Robes + Gloves [Lockpick]
    }

    def create_character(self, name: str) -> Character:
        """
        Create a new random character.

        Args:
            name: Character name

        Returns:
            New Character with rolled stats
        """
        self.character = Character.create_random(name)
        return self.character

    def create_character_with_stats(self, name: str, might: int, wits: int,
                                    grit: int, aether: int) -> Character:
        """Create a character with pre-rolled stats (from Discord wizard)."""
        self.character = Character(
            name=name, might=might, wits=wits, grit=grit, aether=aether
        )
        return self.character

    def equip_loadout(self, loadout_id: str = "sellsword"):
        """Equip starter gear based on loadout choice from creation_rules.json."""
        starter = create_starter_gear()
        indices = self.LOADOUT_MAP.get(loadout_id.lower(), self.LOADOUT_MAP["sellsword"])
        for idx in indices:
            item = starter[idx]
            self.character.gear.equip(item)
            # Seed pity timer with starter item names (WO-V17.0)
            self._found_item_names.add(item.name)

    def create_party(self, names: List[str]) -> List[Character]:
        """Create a party of characters. First is the leader (self.character)."""
        self.party = []
        for name in names:
            char = Character.create_random(name)
            self.party.append(char)
        if self.party:
            self.character = self.party[0]
        return self.party

    def get_active_party(self) -> List[Character]:
        """Return alive party members."""
        return [c for c in self.party if c.is_alive()]

    def add_to_party(self, char: Character):
        """Add a character (or summoned minion) to the party."""
        self.party.append(char)

    def remove_from_party(self, char: Character):
        """Remove a character from the party (death, unsummon)."""
        if char in self.party:
            self.party.remove(char)
        if not self.party:
            self.character = None
        elif self.character is char:
            alive = self.get_active_party()
            self.character = alive[0] if alive else None

    def get_mood_context(self) -> dict:
        """Return current mechanical state as narrative mood modifiers (WO-V61.0)."""
        party_hp_pct = (
            sum(c.current_hp for c in self.party) / max(1, sum(c.max_hp for c in self.party))
            if self.party else 1.0
        )
        doom_pct = self.doom_clock.filled / 20 if self.doom_clock else 0.0
        tension = max(doom_pct, 1.0 - party_hp_pct)

        if party_hp_pct < 0.25:
            condition = "critical"
            words = ["desperate", "ragged", "blood-slicked"]
        elif party_hp_pct < 0.5:
            condition = "battered"
            words = ["weary", "strained", "bruised"]
        elif doom_pct > 0.75:
            condition = "desperate"
            words = ["oppressive", "suffocating", "relentless"]
        else:
            condition = "healthy"
            words = []

        return {
            "tension": round(tension, 2),
            "tone_words": words,
            "party_condition": condition,
            "system_specific": {
                "doom": self.doom_clock.filled if self.doom_clock else 0,
                "doom_pct": round(doom_pct, 2),
            },
        }

    # ----- Protocol: GameEngine -----

    def get_status(self) -> Dict[str, Any]:
        """Return current game state summary."""
        lead = self.party[0] if self.party else None
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "lead_hp": f"{lead.current_hp}/{lead.max_hp}" if lead else None,
            "doom": self.doom_clock.current,
            "room": self.current_room_id,
        }

    def save_state(self) -> Dict[str, Any]:
        """Serialize engine state (protocol-compatible wrapper for save_game)."""
        data = self.save_game()
        data["system_id"] = self.system_id
        return data

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state (protocol-compatible wrapper for load_game)."""
        self.load_game(data)

    # ----- Protocol: DiceEngine -----

    def roll_check(self, character=None, stat="might", dc=None, **kwargs):
        """Execute Burnwillow dice pool check: [gear dice]d6 + stat_mod vs DC.

        Args:
            character: Character to roll for (default: lead).
            stat: One of might/wits/grit/aether.
            dc: Difficulty class (default: DC.ROUTINE = 8).

        Returns:
            Dict with roll details.
        """
        char = character or self.character
        if not char:
            return {"success": False, "error": "No character"}
        stat_type = StatType(stat.upper())
        target_dc = dc if dc is not None else DC.ROUTINE.value
        result = char.make_check(stat_type, target_dc)
        return {
            "roll": sum(result.rolls), "rolls": result.rolls,
            "modifier": result.modifier, "total": result.total,
            "dc": result.dc, "success": result.success,
            "dice_count": result.dice_count,
            "critical": all(r == 6 for r in result.rolls),
            "fumble": all(r == 1 for r in result.rolls),
        }

    def log_character_death(self, char, cause="Fell in the dungeon", seed=None):
        """Record a character death to the graveyard."""
        from codex.core.services.graveyard import log_death
        return log_death({
            "name": char.name, "hp_max": char.max_hp,
            "might": char.might, "wits": char.wits,
            "grit": char.grit, "aether": char.aether,
            "cause": cause, "doom": self.doom_clock.current,
            "room_id": self.current_room_id,
        }, system_id="burnwillow", seed=seed)

    # ----- Legacy save/load -----

    def load_character(self, data: dict) -> Character:
        """Load character from save data."""
        self.character = Character.from_dict(data)
        return self.character

    def save_game(self) -> dict:
        """
        Save current game state.

        Returns:
            JSON-serializable game state
        """
        dungeon_data = None
        if self.dungeon_graph:
            dungeon_data = {
                "graph": self.dungeon_graph.to_dict(),
                "current_room_id": self.current_room_id,
                "player_pos": list(self.player_pos) if self.player_pos else None,
                "visited_rooms": list(self.visited_rooms),
                "zone": getattr(self, '_zone', 1)
            }

        return {
            "character": self.character.to_dict() if self.character else None,
            "party": [c.to_dict() for c in self.party if not isinstance(c, Minion)],
            "doom_clock": self.doom_clock.to_dict(),
            "dungeon": dungeon_data,
            "civic_pulse": self.civic_pulse.to_dict() if self.civic_pulse else None,
            # WO-V17.0: Pity timer persistence
            "pity_counter": self._turns_since_unique_loot,
            "found_items": list(self._found_item_names),
            # WO-V48.0: Delta tracker persistence
            "delta_tracker": self.delta_tracker.to_dict() if self.delta_tracker else None,
        }

    def load_game(self, data: dict):
        """Restore game state from save."""
        if data.get("party"):
            self.party = [Character.from_dict(c) for c in data["party"]]
            self.character = self.party[0] if self.party else None
        elif data.get("character"):
            self.character = Character.from_dict(data["character"])
            self.party = [self.character]
        if data.get("doom_clock"):
            self.doom_clock = UniversalClock.from_dict(data["doom_clock"])
        if data.get("dungeon"):
            try:
                from codex.spatial.map_engine import DungeonGraph, BurnwillowAdapter, ContentInjector
                dungeon_data = data["dungeon"]
                self.dungeon_graph = DungeonGraph.from_dict(dungeon_data["graph"])
                self.current_room_id = dungeon_data.get("current_room_id")
                saved_pos = dungeon_data.get("player_pos")
                self.player_pos = tuple(saved_pos) if saved_pos else None
                self.visited_rooms = set(dungeon_data.get("visited_rooms", []))

                # Re-populate rooms (content is deterministic from seed)
                zone = dungeon_data.get("zone", 1)
                self._zone = zone
                if zone == 1:
                    try:
                        from codex.games.burnwillow.zone1 import TangleAdapter
                        adapter = TangleAdapter(seed=self.dungeon_graph.seed)
                    except ImportError:
                        adapter = BurnwillowAdapter(seed=self.dungeon_graph.seed)
                else:
                    adapter = BurnwillowAdapter(seed=self.dungeon_graph.seed)
                injector = ContentInjector(adapter)
                self.populated_rooms = injector.populate_all(self.dungeon_graph)
            except ImportError:
                pass  # Dungeon features not available

        if data.get("civic_pulse"):
            try:
                from codex.core.services.town_crier import CivicPulse
                self.civic_pulse = CivicPulse.from_dict(data["civic_pulse"])
            except ImportError:
                pass

        # WO-V17.0: Restore pity timer state
        self._turns_since_unique_loot = data.get("pity_counter", 0)
        self._found_item_names = set(data.get("found_items", []))

        # WO-V48.0: Restore delta tracker
        if data.get("delta_tracker"):
            try:
                from codex.core.services.narrative_frame import DeltaTracker
                self.delta_tracker = DeltaTracker.from_dict(data["delta_tracker"])
            except ImportError:
                pass

    def loot_item(self, room_id: Optional[int] = None) -> Optional[GearItem]:
        """Pop the first loot item from a room (no roll required).

        Args:
            room_id: Room to loot from (default: current room).

        Returns:
            GearItem if loot was available, None otherwise.
        """
        rid = room_id if room_id is not None else self.current_room_id
        if rid is None:
            return None
        pop_room = self.populated_rooms.get(rid)
        if not pop_room:
            return None
        loot_list = pop_room.content.get("loot", [])
        if not loot_list:
            return None
        raw = loot_list.pop(0)
        pop_room.content["loot"] = loot_list
        # Convert raw dict to GearItem if possible
        if isinstance(raw, dict) and "slot" in raw:
            try:
                return GearItem.from_dict(raw)
            except (KeyError, ValueError):
                pass
        # Return as a minimal GearItem with the name
        name = raw.get("name", str(raw)) if isinstance(raw, dict) else str(raw)
        return GearItem(name=name, slot=GearSlot.R_HAND, tier=GearTier.TIER_0)

    def drop_item(self, slot_or_name: str) -> Optional[GearItem]:
        """Remove an item from inventory or gear grid, optionally adding to room loot.

        Searches inventory by name first, then gear slots.

        Args:
            slot_or_name: Item name or gear slot name to drop.

        Returns:
            The dropped GearItem, or None if not found.
        """
        if not self.character:
            return None
        # Search inventory by name (case-insensitive)
        target = slot_or_name.strip().lower()
        for idx, item in list(self.character.inventory.items()):
            if item.name.lower() == target:
                dropped = self.character.remove_from_inventory(idx)
                if dropped:
                    self._add_to_room_loot(dropped)
                return dropped
        # Search gear slots
        for slot in GearSlot:
            equipped = self.character.gear.slots.get(slot)
            if equipped and equipped.name.lower() == target:
                dropped = self.character.gear.unequip(slot)
                if dropped:
                    self._add_to_room_loot(dropped)
                return dropped
        return None

    def _add_to_room_loot(self, item: GearItem):
        """Add a gear item back to the current room's loot pool."""
        if self.current_room_id is None:
            return
        pop_room = self.populated_rooms.get(self.current_room_id)
        if pop_room:
            pop_room.content.setdefault("loot", []).append(item.to_dict())

    def advance_doom(self, turns: int = 1) -> List[str]:
        """Advance the doom clock and get triggered events."""
        return self.doom_clock.advance(turns)

    # ─────────────────────────────────────────────────────────────────────
    # LOOT PITY TIMER (WO-V17.0)
    # ─────────────────────────────────────────────────────────────────────

    def _get_player_tier(self) -> int:
        """Estimate player tier from highest equipped gear tier."""
        if not self.character:
            return 1
        max_tier = 1
        for item in self.character.gear.slots.values():
            if item and item.tier.value > max_tier:
                max_tier = item.tier.value
        return max_tier

    def check_pity_loot(self) -> Optional[dict]:
        """If 12+ turns without unique loot, force a tier 2+ drop.

        Returns raw loot dict or None.
        """
        self._turns_since_unique_loot += 1
        if self._turns_since_unique_loot < 12:
            return None
        # Force a unique drop
        from codex.games.burnwillow.content import get_random_loot
        rng = random.Random()
        tier = min(4, max(2, self._get_player_tier() + 1))
        for _ in range(20):
            loot = get_random_loot(tier, rng)
            if loot["name"] not in self._found_item_names:
                self._turns_since_unique_loot = 0
                self._found_item_names.add(loot["name"])
                return loot
        # Fallback: just give something
        loot = get_random_loot(tier, rng)
        self._turns_since_unique_loot = 0
        return loot

    def register_loot_find(self, item_name: str):
        """Call when player finds any loot. Resets pity timer if unique."""
        if item_name not in self._found_item_names:
            self._found_item_names.add(item_name)
            self._turns_since_unique_loot = 0

    def reset(self):
        """Start a new run (hardcore reset)."""
        self.character = None
        self.party = []
        self.doom_clock.reset()
        self.dungeon_graph = None
        self.populated_rooms = {}
        self.current_room_id = None
        self.player_pos = None
        self.visited_rooms = set()

    # ─────────────────────────────────────────────────────────────────────
    # DUNGEON GENERATION & NAVIGATION (NEW)
    # ─────────────────────────────────────────────────────────────────────

    def generate_dungeon(self, depth: int = 4, seed: Optional[int] = None, zone: int = 1) -> dict:
        """
        Generate a procedural dungeon using the Universal Map Engine.

        Args:
            depth: BSP recursion depth (controls room count: ~2^depth rooms)
            seed: Random seed for reproducibility (default: random)
            zone: Zone number controlling which content adapter is used (1=The Tangle)

        Returns:
            Summary dict with dungeon stats

        Usage:
            engine.generate_dungeon(depth=4, seed=12345, zone=1)
        """
        try:
            from codex.spatial.map_engine import CodexMapEngine, BurnwillowAdapter, ContentInjector
        except ImportError:
            raise ImportError("codex_map_engine not found. Ensure it exists in the same directory.")

        # Generate geometry
        map_engine = CodexMapEngine(seed=seed)
        self.map_engine = map_engine
        self.dungeon_graph = map_engine.generate(
            width=50,
            height=50,
            min_room_size=5,
            max_depth=depth,
            system_id="burnwillow",
        )

        # Populate with zone-specific content
        self._zone = zone
        if zone == 1:
            try:
                from codex.games.burnwillow.zone1 import TangleAdapter
                adapter = TangleAdapter(seed=seed)
            except ImportError:
                adapter = BurnwillowAdapter(seed=seed)
            injector = ContentInjector(adapter)
            self.populated_rooms = injector.populate_all(self.dungeon_graph)
        elif zone > 1:
            # Higher zones use TangleAdapter for richer content
            try:
                from codex.games.burnwillow.zone1 import TangleAdapter
                adapter = TangleAdapter(seed=seed)
            except ImportError:
                adapter = BurnwillowAdapter(seed=seed)
            injector = ContentInjector(adapter)
            self.populated_rooms = injector.populate_all(self.dungeon_graph)
        else:
            adapter = BurnwillowAdapter(seed=seed)
            injector = ContentInjector(adapter)
            self.populated_rooms = injector.populate_all(self.dungeon_graph)

        # Set starting position
        self.current_room_id = self.dungeon_graph.start_room_id
        self.visited_rooms.add(self.current_room_id)

        # Set player grid position (center of starting room)
        start_room = self.dungeon_graph.rooms.get(self.current_room_id)
        if start_room:
            self.player_pos = (
                start_room.x + start_room.width // 2,
                start_room.y + start_room.height // 2,
            )

        return {
            "seed": self.dungeon_graph.seed,
            "total_rooms": len(self.dungeon_graph.rooms),
            "start_room": self.current_room_id,
            "dungeon_size": f"{self.dungeon_graph.width}x{self.dungeon_graph.height}"
        }

    def get_current_room(self) -> Optional[dict]:
        """
        Get the currently occupied room with all content.

        Returns:
            Dict with room geometry and content, or None if no dungeon
        """
        if not self.dungeon_graph or self.current_room_id is None:
            return None

        pop_room = self.populated_rooms.get(self.current_room_id)
        if not pop_room:
            return None

        return {
            "id": pop_room.geometry.id,
            "type": pop_room.geometry.room_type.value,
            "tier": pop_room.geometry.tier,
            "is_locked": pop_room.geometry.is_locked,
            "is_secret": pop_room.geometry.is_secret,
            "connections": pop_room.geometry.connections,
            "description": pop_room.content.get("description", "An empty room."),
            "enemies": [e for e in pop_room.content.get("enemies", [])
                        if not (isinstance(e, dict) and e.get("is_npc"))],
            "npcs": [e for e in pop_room.content.get("enemies", [])
                     if isinstance(e, dict) and e.get("is_npc")],
            "loot": pop_room.content.get("loot", []),
            "hazards": pop_room.content.get("hazards", []),
            "furniture": pop_room.content.get("furniture", []),
            "visited": self.current_room_id in self.visited_rooms
        }

    def get_connected_rooms(self) -> List[dict]:
        """
        Get all rooms connected to the current room.

        Returns:
            List of room summary dicts (id, type, tier, locked, visited)
        """
        if not self.dungeon_graph or self.current_room_id is None:
            return []

        current_room = self.dungeon_graph.get_room(self.current_room_id)
        if not current_room:
            return []

        connected = []
        for room_id in current_room.connections:
            room = self.dungeon_graph.get_room(room_id)
            if room:
                connected.append({
                    "id": room.id,
                    "type": room.room_type.value,
                    "tier": room.tier,
                    "is_locked": room.is_locked,
                    "is_secret": room.is_secret,
                    "visited": room_id in self.visited_rooms
                })

        return connected

    @staticmethod
    def _octant_direction(dx: int, dy: int) -> str:
        """Compute 8-way direction label from a delta vector.

        Uses a 2:1 ratio threshold: if one axis dominates by 2x, use pure
        cardinal; otherwise use diagonal.
        """
        if dx == 0 and dy == 0:
            return "N"  # fallback
        adx, ady = abs(dx), abs(dy)
        if adx >= 2 * ady:
            return "E" if dx > 0 else "W"
        elif ady >= 2 * adx:
            return "S" if dy > 0 else "N"
        else:
            ns = "S" if dy > 0 else "N"
            ew = "E" if dx > 0 else "W"
            return ns + ew

    def get_cardinal_exits(self) -> List[dict]:
        """Get connected rooms labelled with 8-way directions.

        Computes direction from current room center to each neighbour's center.
        Returns list of dicts with 'direction', 'id', 'type', 'tier', 'is_locked', 'visited'.
        """
        if not self.dungeon_graph or self.current_room_id is None:
            return []

        current = self.dungeon_graph.get_room(self.current_room_id)
        if not current:
            return []

        cx = current.x + current.width // 2
        cy = current.y + current.height // 2

        exits = []
        for room_id in current.connections:
            target = self.dungeon_graph.get_room(room_id)
            if not target:
                continue
            tx = target.x + target.width // 2
            ty = target.y + target.height // 2
            dx, dy = tx - cx, ty - cy
            direction = self._octant_direction(dx, dy)
            exits.append({
                "direction": direction,
                "id": target.id,
                "type": target.room_type.value,
                "tier": target.tier,
                "is_locked": target.is_locked,
                "visited": room_id in self.visited_rooms,
            })
        return exits

    def push_furniture(self, name_fragment: str, direction: str) -> dict:
        """Push a furniture object in any direction within the current room.

        Args:
            name_fragment: Partial or full name of the furniture to push.
            direction: Direction — 'n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'.

        Returns:
            Result dict with success, message, and updated position.
        """
        if not self.dungeon_graph or self.current_room_id is None:
            return {"success": False, "message": "No dungeon loaded."}

        pop_room = self.populated_rooms.get(self.current_room_id)
        if not pop_room:
            return {"success": False, "message": "No room data."}

        furniture = pop_room.content.get("furniture", [])
        target = None
        for obj in furniture:
            if name_fragment.lower() in obj.get("name", "").lower():
                target = obj
                break

        if target is None:
            return {"success": False, "message": f"No furniture matching '{name_fragment}' here."}

        # Direction deltas (1 tile per push) — 8-way
        delta = self._DIR_DELTAS.get(direction.lower())
        if delta is None:
            return {"success": False, "message": f"Invalid direction '{direction}'. Use n/s/e/w/ne/nw/se/sw."}

        # Room bounds
        room = pop_room.geometry
        inner_x0 = room.x + 1
        inner_y0 = room.y + 1
        inner_x1 = room.x + room.width - 2
        inner_y1 = room.y + room.height - 2

        old_x = target.get("x", inner_x0)
        old_y = target.get("y", inner_y0)
        new_x = old_x + delta[0]
        new_y = old_y + delta[1]

        # Wall collision
        if new_x < inner_x0 or new_x > inner_x1 or new_y < inner_y0 or new_y > inner_y1:
            return {"success": False, "message": f"{target['name']} can't be pushed further {direction.upper()}."}

        target["x"] = new_x
        target["y"] = new_y

        return {
            "success": True,
            "message": f"You push {target['name']} {direction.upper()}.",
            "furniture": target["name"],
            "position": (new_x, new_y),
        }

    def move_to_room(self, room_id: int) -> dict:
        """
        Move the character to a connected room.

        Args:
            room_id: Target room ID

        Returns:
            Result dict with success status and message

        Raises:
            ValueError if room is not connected or locked
        """
        if not self.dungeon_graph or self.current_room_id is None:
            return {"success": False, "message": "No active dungeon."}

        current_room = self.dungeon_graph.get_room(self.current_room_id)
        if not current_room:
            return {"success": False, "message": "Current room not found (corrupted state)."}

        # Check if target is connected
        if room_id not in current_room.connections:
            return {"success": False, "message": f"Room {room_id} is not connected to current room."}

        target_room = self.dungeon_graph.get_room(room_id)
        if not target_room:
            return {"success": False, "message": f"Room {room_id} does not exist."}

        # Check if locked
        if target_room.is_locked:
            # Can unlock with key or lockpicking
            if self.character and self.character.keys > 0:
                self.character.keys -= 1
                target_room.is_locked = False
                message = f"Used a key to unlock room {room_id}."
            elif self.character and self.character.can_pick_locks():
                # Lockpicking check (DC based on tier)
                dc = 8 + (target_room.tier * 2)
                result = self.character.make_check(StatType.WITS, dc)
                if result.success:
                    target_room.is_locked = False
                    message = f"Successfully picked the lock on room {room_id}."
                else:
                    return {
                        "success": False,
                        "message": f"Failed to pick lock (rolled {result.total} vs DC {dc})."
                    }
            else:
                return {
                    "success": False,
                    "message": f"Room {room_id} is locked. Need a key or lockpicking gear."
                }
        else:
            message = f"Moved to room {room_id}."

        # Move successful
        self.current_room_id = room_id
        self.visited_rooms.add(room_id)

        # Record room state for delta-based narration (WO-V48.0)
        if self.delta_tracker is not None:
            room_data = self.get_current_room()
            if room_data:
                self.delta_tracker.record_visit(room_id, room_data)

        # Re-center player in the new room
        self.player_pos = (
            target_room.x + target_room.width // 2,
            target_room.y + target_room.height // 2,
        )

        # Advance doom clock
        doom_events = self.advance_doom(1)
        if doom_events:
            message += f" {' '.join(doom_events)}"

        return {
            "success": True,
            "message": message,
            "room": self.get_current_room()
        }

    # Long-form direction name lookup
    _DIR_LONG = {
        "n": "north", "s": "south", "e": "east", "w": "west",
        "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
        "north": "north", "south": "south", "east": "east", "west": "west",
        "northeast": "northeast", "northwest": "northwest",
        "southeast": "southeast", "southwest": "southwest",
    }

    def _check_door_proximity(self, x: int, y: int, direction: str) -> Optional[int]:
        """Check if position (x,y) is near a door to a connected room in the given direction.

        Supports 8-way directions. For diagonal bumps, checks if the neighbor
        is in the matching octant direction.

        Returns the connected room_id if a door is nearby, or None.
        """
        if not self.dungeon_graph or self.current_room_id is None:
            return None
        room = self.dungeon_graph.rooms.get(self.current_room_id)
        if not room:
            return None

        # Normalize direction to long form
        dir_long = self._DIR_LONG.get(direction.lower(), direction.lower())

        for conn_id in room.connections:
            neighbor = self.dungeon_graph.rooms.get(conn_id)
            if not neighbor:
                continue

            # Determine 8-way direction to neighbor
            ndx = (neighbor.x + neighbor.width // 2) - (room.x + room.width // 2)
            ndy = (neighbor.y + neighbor.height // 2) - (room.y + room.height // 2)
            conn_dir = self._octant_direction(ndx, ndy).lower()
            # Map short octant labels to long names
            _short_to_long = {
                "n": "north", "s": "south", "e": "east", "w": "west",
                "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
            }
            conn_dir_long = _short_to_long.get(conn_dir, conn_dir)

            if conn_dir_long != dir_long:
                continue

            # Check overlap: for any direction, verify bump pos is near shared boundary
            y_overlap_min = max(room.y, neighbor.y)
            y_overlap_max = min(room.y + room.height, neighbor.y + neighbor.height)
            x_overlap_min = max(room.x, neighbor.x)
            x_overlap_max = min(room.x + room.width, neighbor.x + neighbor.width)

            if dir_long in ("east", "west"):
                if y_overlap_min <= y <= y_overlap_max:
                    return conn_id
            elif dir_long in ("north", "south"):
                if x_overlap_min <= x <= x_overlap_max:
                    return conn_id
            else:
                # Diagonal: check if bump is near both shared edges
                if (x_overlap_min <= x <= x_overlap_max or
                        y_overlap_min <= y <= y_overlap_max):
                    return conn_id

        return None

    # 8-way direction deltas: (dx, dy)
    _DIR_DELTAS = {
        "n": (0, -1), "north": (0, -1),
        "s": (0, 1),  "south": (0, 1),
        "e": (1, 0),  "east": (1, 0),
        "w": (-1, 0), "west": (-1, 0),
        "ne": (1, -1), "northeast": (1, -1),
        "nw": (-1, -1), "northwest": (-1, -1),
        "se": (1, 1),  "southeast": (1, 1),
        "sw": (-1, 1), "southwest": (-1, 1),
    }

    def move_player_grid(self, direction: str) -> dict:
        """Move the player by one tile on the spatial grid.

        Args:
            direction: One of n/s/e/w/ne/nw/se/sw (or full names).

        Returns:
            Result dict with success status and message.
        """
        if not self.player_pos:
            return {"success": False, "message": "Player has no physical form."}

        x, y = self.player_pos
        direction = direction.lower().strip()
        delta = self._DIR_DELTAS.get(direction)
        if delta is None:
            return {"success": False, "message": f"Invalid direction '{direction}'. Use n/s/e/w/ne/nw/se/sw."}
        dx, dy = delta

        new_x, new_y = x + dx, y + dy

        # Wall collision: stay inside the current room boundaries
        if self.dungeon_graph and self.current_room_id is not None:
            room = self.dungeon_graph.rooms.get(self.current_room_id)
            if room:
                # Interior bounds (inside the walls)
                min_x = room.x + 1
                min_y = room.y + 1
                max_x = room.x + room.width - 2
                max_y = room.y + room.height - 2
                if not (min_x <= new_x <= max_x and min_y <= new_y <= max_y):
                    # Check if bumping near a door — snap to exit
                    door_room = self._check_door_proximity(new_x, new_y, direction)
                    if door_room is not None:
                        return {"success": True, "message": f"Moved {direction} through doorway.",
                                "door_exit": door_room, "bump_pos": (new_x, new_y)}
                    return {"success": False, "message": "You bump into the wall.",
                            "bump_pos": (new_x, new_y)}

        self.player_pos = (new_x, new_y)
        return {"success": True, "message": f"Moved {direction}."}

    def populate_dungeon_canopy(self):
        """Populate the vertical dungeon with canopy-themed content.

        Uses CANOPY_ENEMY_TABLES, CANOPY_LOOT_TABLES, CANOPY_ROOM_DESCRIPTIONS
        instead of the root-themed equivalents.  Tiers map to floors:
        Floor 1 = Tier 1 (trunk base), top floor = Tier 4 (Crown).
        """
        from codex.games.burnwillow.content import (
            CANOPY_ENEMY_TABLES, CANOPY_LOOT_TABLES,
            CANOPY_ROOM_DESCRIPTIONS, CANOPY_ARCHETYPES,
            CONTENT_DR_BY_TIER,
        )
        from codex.games.burnwillow.atmosphere import (
            thermal_narrative_modifier, ThermalTone,
        )
        from codex.spatial.map_engine import PopulatedRoom, RoomType

        if not self.dungeon_graph:
            return

        self.populated_rooms = {}
        canopy_tones = {
            1: ThermalTone.CANOPY_LOW,
            2: ThermalTone.CANOPY_MID,
            3: ThermalTone.CANOPY_HIGH,
            4: ThermalTone.CANOPY_CROWN,
        }

        for room_id, room in self.dungeon_graph.rooms.items():
            rng = random.Random(self.dungeon_graph.seed + room_id)
            tier = max(1, min(4, room.tier))
            tone = canopy_tones.get(tier, ThermalTone.CANOPY_LOW)

            content = {
                "enemies": [], "loot": [], "hazards": [],
                "furniture": [], "description": "",
            }

            # Description
            desc_pool = CANOPY_ROOM_DESCRIPTIONS.get(tier, CANOPY_ROOM_DESCRIPTIONS[1])
            base_desc = rng.choice(desc_pool)
            content["description"] = thermal_narrative_modifier(
                base_desc, tier, rng, tone_override=tone)

            if room.room_type == RoomType.START:
                if rng.random() < 0.3:
                    content["loot"].append(
                        self._canopy_loot(tier, rng, CANOPY_LOOT_TABLES))
            elif room.room_type == RoomType.BOSS:
                boss = self._canopy_enemy(tier, rng, CANOPY_ENEMY_TABLES,
                                          CANOPY_ARCHETYPES, CONTENT_DR_BY_TIER,
                                          is_boss=True)
                content["enemies"].append(boss)
                content["loot"].extend([
                    self._canopy_loot(min(4, tier + 1), rng, CANOPY_LOOT_TABLES)
                    for _ in range(2)])
            elif room.room_type == RoomType.TREASURE:
                if not room.is_locked:
                    for _ in range(rng.randint(1, 2)):
                        content["enemies"].append(
                            self._canopy_enemy(tier, rng, CANOPY_ENEMY_TABLES,
                                               CANOPY_ARCHETYPES, CONTENT_DR_BY_TIER))
                for _ in range(rng.randint(2, 4)):
                    content["loot"].append(
                        self._canopy_loot(tier, rng, CANOPY_LOOT_TABLES))
            elif room.room_type in (RoomType.NORMAL, RoomType.CORRIDOR):
                for _ in range(rng.randint(0, 2)):
                    content["enemies"].append(
                        self._canopy_enemy(tier, rng, CANOPY_ENEMY_TABLES,
                                           CANOPY_ARCHETYPES, CONTENT_DR_BY_TIER))
                if rng.random() < 0.4:
                    content["loot"].append(
                        self._canopy_loot(tier, rng, CANOPY_LOOT_TABLES))
                # Config-driven hazards (20 % chance per room)
                cfg_hazards = _load_bw_hazards().get(tier, [])
                if cfg_hazards and rng.random() < 0.2:
                    content["hazards"].append(rng.choice(cfg_hazards))

            self.populated_rooms[room_id] = PopulatedRoom(
                geometry=room, content=content)

        # Set starting position
        self.current_room_id = self.dungeon_graph.start_room_id
        self.visited_rooms.add(self.current_room_id)
        start_room = self.dungeon_graph.rooms.get(self.current_room_id)
        if start_room:
            self.player_pos = start_room.center()

    @staticmethod
    def _canopy_enemy(tier, rng, tables, archetypes, dr_table,
                      is_boss=False):
        """Generate a single canopy enemy dict."""
        pool = tables.get(tier, tables[1])
        name, hp_base, hp_var, defense, damage, special = rng.choice(pool)
        hp = hp_base + rng.randint(0, hp_var)
        if is_boss:
            hp = int(hp * 1.5)
            name = f"{name} (Alpha)"
        return {
            "name": name, "hp": hp, "defense": defense,
            "damage": damage, "special": special, "tier": tier,
            "dr": dr_table.get(tier, 0) + (1 if is_boss else 0),
            "archetype": archetypes.get(
                name.replace(" (Alpha)", ""), "beast"),
            "is_boss": is_boss,
        }

    @staticmethod
    def _canopy_loot(tier, rng, tables):
        """Generate a single canopy loot dict."""
        tier = max(1, min(4, tier))
        pool = tables.get(tier, tables[1])
        name, slot, item_tier, traits, desc = rng.choice(pool)
        return {
            "name": name, "slot": slot, "tier": item_tier,
            "special_traits": traits, "description": desc,
        }

    def get_dungeon_map_summary(self) -> dict:
        """
        Get a summary of the entire dungeon (for debugging or map display).

        Returns:
            Dict with all rooms and their states
        """
        if not self.dungeon_graph:
            return {"error": "No dungeon generated."}

        rooms = []
        for room_id, room in self.dungeon_graph.rooms.items():
            rooms.append({
                "id": room.id,
                "type": room.room_type.value,
                "tier": room.tier,
                "position": (room.x, room.y),
                "size": (room.width, room.height),
                "connections": room.connections,
                "is_locked": room.is_locked,
                "is_secret": room.is_secret,
                "visited": room_id in self.visited_rooms,
                "is_current": room_id == self.current_room_id
            })

        return {
            "seed": self.dungeon_graph.seed,
            "total_rooms": len(rooms),
            "start_room": self.dungeon_graph.start_room_id,
            "current_room": self.current_room_id,
            "visited_count": len(self.visited_rooms),
            "rooms": rooms
        }


# =============================================================================
# TRAIT RESOLUTION (System-Specific)
# =============================================================================

class BurnwillowTraitResolver:
    """Resolves special traits using Burnwillow dice/DC mechanics.

    Implements the TraitResolver interface from
    :mod:`codex.core.services.trait_handler`.
    """

    def resolve_trait(self, trait_id: str, context: dict) -> dict:
        """Resolve *trait_id* using Burnwillow mechanics.

        Expected context keys:
            character: Character object using the trait
            room: Optional current room data dict
        """
        character = context.get("character")
        if character is None:
            return {"success": False, "message": "No character in context."}

        handler = self._TRAIT_MAP.get(trait_id)
        if handler is None:
            return {"success": False, "message": f"Unknown trait: {trait_id}"}
        return handler(self, character, context)

    def _resolve_set_trap(self, character, context: dict) -> dict:
        check = character.make_check(StatType.WITS, DC.ROUTINE.value)
        return {
            "success": check.success,
            "message": f"SET_TRAP: Wits {check.total} vs DC {DC.ROUTINE.value}",
            "creates": "HAZARD" if check.success else None,
        }

    def _resolve_charge(self, character, context: dict) -> dict:
        check = character.make_check(StatType.MIGHT, DC.ROUTINE.value)
        bonus_damage = random.randint(1, 6) if check.success else 0
        return {
            "success": check.success,
            "message": f"CHARGE: Might {check.total} vs DC {DC.ROUTINE.value}",
            "bonus_damage": bonus_damage,
        }

    def _resolve_sanctify(self, character, context: dict) -> dict:
        check = character.make_check(StatType.AETHER, DC.HEROIC.value)
        return {
            "success": check.success,
            "message": f"SANCTIFY: Aether {check.total} vs DC {DC.HEROIC.value}",
            "aoe_damage": random.randint(1, 6) if check.success else 0,
        }

    def _resolve_resist_blight(self, character, context: dict) -> dict:
        return {
            "success": True,
            "message": "RESIST_BLIGHT: Passive DR +2 vs Blight hazards.",
            "dr_bonus": 2,
        }

    def _resolve_far_sight(self, character, context: dict) -> dict:
        return {
            "success": True,
            "message": "FAR_SIGHT: Scout DC reduced by 2.",
            "scout_dc_reduction": 2,
        }

    # WO-V17.0: Active Gear Ability Resolvers
    def _resolve_intercept(self, character, context: dict) -> dict:
        """Intercept: DR bonus until next hit. Tier scales the bonus."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        dr_bonus = min(5, tier + 1)  # T1:+2, T2:+3, T3:+4, T4:+5
        reflect = random.randint(1, 6) if tier >= 4 else 0
        return {
            "success": True,
            "message": f"INTERCEPT: +{dr_bonus} DR until next incoming hit.",
            "dr_bonus": dr_bonus,
            "reflect_damage": reflect,
            "action": "intercept",
        }

    def _resolve_command(self, character, context: dict) -> dict:
        """Command: Wits DC 12 check. Grant free attack."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        bonus_dmg = max(0, tier - 1)  # T1:0, T2:+1, T3:+2, T4:+3
        check = character.make_check(StatType.WITS, 12)
        return {
            "success": check.success,
            "message": f"COMMAND: Wits {check.total} vs DC 12 — {'SUCCESS' if check.success else 'FAIL'}",
            "bonus_damage": bonus_dmg if check.success else 0,
            "free_attack": check.success,
            "action": "command",
        }

    def _resolve_bolster(self, character, context: dict) -> dict:
        """Bolster: Aether DC 10 check. Bonus dice on next roll."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        bonus_dice = min(3, tier)  # T1:+1d6, T2:+2d6, T3:+3d6, T4:+3d6
        check = character.make_check(StatType.AETHER, 10)
        return {
            "success": check.success,
            "message": f"BOLSTER: Aether {check.total} vs DC 10 — {'SUCCESS' if check.success else 'FAIL'}",
            "bonus_dice": bonus_dice if check.success else 0,
            "action": "bolster",
        }

    def _resolve_triage(self, character, context: dict) -> dict:
        """Triage: Wits DC 12 check. Heal based on tier."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        heal_dice = min(4, tier)  # T1:1d6, T2:2d6, T3:3d6, T4:4d6
        heal_amount = sum(random.randint(1, 6) for _ in range(heal_dice))
        check = character.make_check(StatType.WITS, 12)
        return {
            "success": check.success,
            "message": f"TRIAGE: Wits {check.total} vs DC 12 — {'SUCCESS' if check.success else 'FAIL'}",
            "heal_amount": heal_amount,
            "free_heal": check.success,  # Success = no charge consumed
            "action": "triage",
        }

    # WO-V32.0: AoE Combat Mechanics
    def _resolve_cleave(self, character, context: dict) -> dict:
        """Cleave: On successful attack, splash damage to adjacent enemies."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        cleave_targets = min(3, tier)  # T1:1, T2:2, T3:3, T4:3
        return {
            "success": True,
            "message": f"CLEAVE: Strikes up to {cleave_targets} additional targets at 50% damage.",
            "cleave_targets": cleave_targets,
            "cleave_damage_pct": 0.5,
            "action": "cleave",
        }

    # WO-V36.0: Expanded AoE Trait Resolvers
    def _resolve_shockwave(self, character, context: dict) -> dict:
        """Shockwave: Might DC 12. Damage + Stun 1 round, 1-3 targets."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        targets = min(3, tier)
        check = character.make_check(StatType.MIGHT, 12)
        dmg = sum(random.randint(1, 6) for _ in range(tier)) if check.success else 0
        return {
            "success": check.success,
            "message": f"SHOCKWAVE: Might {check.total} vs DC 12 — {'SUCCESS' if check.success else 'FAIL'}",
            "damage": dmg,
            "targets": targets if check.success else 0,
            "stun_rounds": 1 if check.success else 0,
            "action": "shockwave",
        }

    def _resolve_whirlwind(self, character, context: dict) -> dict:
        """Whirlwind: Might DC 14. 75% damage to ALL enemies in room."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        check = character.make_check(StatType.MIGHT, 14)
        dmg = sum(random.randint(1, 6) for _ in range(tier)) if check.success else 0
        return {
            "success": check.success,
            "message": f"WHIRLWIND: Might {check.total} vs DC 14 — {'SUCCESS' if check.success else 'FAIL'}",
            "damage": dmg,
            "damage_pct": 0.75 if check.success else 0,
            "hits_all": check.success,
            "action": "whirlwind",
        }

    def _resolve_flash(self, character, context: dict) -> dict:
        """Flash: Wits DC 12. Blind 1-2 enemies for 2 rounds."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        targets = min(2, tier)
        check = character.make_check(StatType.WITS, 12)
        return {
            "success": check.success,
            "message": f"FLASH: Wits {check.total} vs DC 12 — {'SUCCESS' if check.success else 'FAIL'}",
            "targets": targets if check.success else 0,
            "blind_rounds": 2 if check.success else 0,
            "accuracy_penalty": -2 if check.success else 0,
            "action": "flash",
        }

    def _resolve_snare(self, character, context: dict) -> dict:
        """Snare: Wits DC 12. Reduce defense of 1-3 enemies by tier."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        targets = min(3, tier)
        check = character.make_check(StatType.WITS, 12)
        return {
            "success": check.success,
            "message": f"SNARE: Wits {check.total} vs DC 12 — {'SUCCESS' if check.success else 'FAIL'}",
            "targets": targets if check.success else 0,
            "defense_reduction": tier if check.success else 0,
            "action": "snare",
        }

    def _resolve_rally(self, character, context: dict) -> dict:
        """Rally: Wits DC 10. Grant +1 bonus die to ALL allies' next attack."""
        check = character.make_check(StatType.WITS, 10)
        return {
            "success": check.success,
            "message": f"RALLY: Wits {check.total} vs DC 10 — {'SUCCESS' if check.success else 'FAIL'}",
            "bonus_dice": 1 if check.success else 0,
            "hits_all_allies": check.success,
            "action": "rally",
        }

    def _resolve_inferno(self, character, context: dict) -> dict:
        """Inferno: Aether DC 14. Fire damage + Burning 2 rounds to 1-3 targets."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        targets = min(3, tier)
        check = character.make_check(StatType.AETHER, 14)
        dmg = sum(random.randint(1, 6) for _ in range(tier)) if check.success else 0
        return {
            "success": check.success,
            "message": f"INFERNO: Aether {check.total} vs DC 14 — {'SUCCESS' if check.success else 'FAIL'}",
            "damage": dmg,
            "targets": targets if check.success else 0,
            "burning_rounds": 2 if check.success else 0,
            "action": "inferno",
        }

    def _resolve_tempest(self, character, context: dict) -> dict:
        """Tempest: Aether DC 12. Lightning damage to 1-3 targets."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        targets = min(3, tier)
        check = character.make_check(StatType.AETHER, 12)
        dmg = sum(random.randint(1, 6) for _ in range(tier)) if check.success else 0
        return {
            "success": check.success,
            "message": f"TEMPEST: Aether {check.total} vs DC 12 — {'SUCCESS' if check.success else 'FAIL'}",
            "damage": dmg,
            "targets": targets if check.success else 0,
            "action": "tempest",
        }

    def _resolve_voidgrip(self, character, context: dict) -> dict:
        """Voidgrip: Aether DC 14. Necrotic damage + Blighted 2 rounds to 1-2 targets."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        targets = min(2, tier)
        check = character.make_check(StatType.AETHER, 14)
        dmg = sum(random.randint(1, 6) for _ in range(tier)) if check.success else 0
        return {
            "success": check.success,
            "message": f"VOIDGRIP: Aether {check.total} vs DC 14 — {'SUCCESS' if check.success else 'FAIL'}",
            "damage": dmg,
            "targets": targets if check.success else 0,
            "blighted_rounds": 2 if check.success else 0,
            "action": "voidgrip",
        }

    def _resolve_mending(self, character, context: dict) -> dict:
        """Mending: Wits DC 10. Heal 1d6*tier HP to ALL party members."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        check = character.make_check(StatType.WITS, 10)
        heal = sum(random.randint(1, 6) for _ in range(tier)) if check.success else 0
        return {
            "success": check.success,
            "message": f"MENDING: Wits {check.total} vs DC 10 — {'SUCCESS' if check.success else 'FAIL'}",
            "heal_amount": heal,
            "hits_all_allies": check.success,
            "action": "mending",
        }

    def _resolve_renewal(self, character, context: dict) -> dict:
        """Renewal: Aether DC 12. HoT: 1d4 HP/round for 3 rounds to all allies."""
        check = character.make_check(StatType.AETHER, 12)
        return {
            "success": check.success,
            "message": f"RENEWAL: Aether {check.total} vs DC 12 — {'SUCCESS' if check.success else 'FAIL'}",
            "hot_rounds": 3 if check.success else 0,
            "hot_dice": "1d4" if check.success else "",
            "hits_all_allies": check.success,
            "action": "renewal",
        }

    def _resolve_aegis(self, character, context: dict) -> dict:
        """Aegis: Grit DC 10. Grant +tier DR to ALL allies for 2 rounds."""
        item = context.get("item")
        tier = item.tier.value if item else 1
        check = character.make_check(StatType.GRIT, 10)
        return {
            "success": check.success,
            "message": f"AEGIS: Grit {check.total} vs DC 10 — {'SUCCESS' if check.success else 'FAIL'}",
            "dr_bonus": tier if check.success else 0,
            "duration_rounds": 2 if check.success else 0,
            "hits_all_allies": check.success,
            "action": "aegis",
        }

    _TRAIT_MAP = {
        "SET_TRAP": _resolve_set_trap,
        "CHARGE": _resolve_charge,
        "SANCTIFY": _resolve_sanctify,
        "RESIST_BLIGHT": _resolve_resist_blight,
        "FAR_SIGHT": _resolve_far_sight,
        # WO-V17.0: Active Gear Abilities
        "INTERCEPT": _resolve_intercept,
        "COMMAND": _resolve_command,
        "BOLSTER": _resolve_bolster,
        "TRIAGE": _resolve_triage,
        # WO-V32.0: AoE Combat
        "CLEAVE": _resolve_cleave,
        # WO-V36.0: Expanded AoE Traits
        "SHOCKWAVE": _resolve_shockwave,
        "WHIRLWIND": _resolve_whirlwind,
        "FLASH": _resolve_flash,
        "SNARE": _resolve_snare,
        "RALLY": _resolve_rally,
        "INFERNO": _resolve_inferno,
        "TEMPEST": _resolve_tempest,
        "VOIDGRIP": _resolve_voidgrip,
        "MENDING": _resolve_mending,
        "RENEWAL": _resolve_renewal,
        "AEGIS": _resolve_aegis,
    }


# =============================================================================
# SUMMONED MINIONS
# =============================================================================

@dataclass
class Minion(Character):
    """A summoned creature that fights alongside the party.

    Minions are temporary Characters with reduced stats. They act as
    regular party members for targeting (Intercept, Command, etc.) but
    vanish when killed or after combat ends.
    """
    is_minion: bool = True
    summon_duration: int = 3  # Rounds remaining before unsummon

    def tick_duration(self) -> bool:
        """Reduce summon duration. Returns True if still active."""
        self.summon_duration -= 1
        return self.summon_duration > 0


def create_minion(summoner_name: str, summoner_aether_mod: int) -> Minion:
    """Create a summoned minion based on the summoner's Aether modifier.

    Minion stats scale with summoner's Aether:
      - HP: 3 + Aether mod
      - Might: 8 + Aether mod (weak melee)
      - All other stats: 8
      - Duration: 3 rounds
    """
    hp_bonus = max(0, summoner_aether_mod)
    might_val = 8 + max(0, summoner_aether_mod)
    minion = Minion(
        name="Spirit",
        might=might_val,
        wits=8,
        grit=8,
        aether=8,
    )
    # Override HP for minions (weaker than full characters)
    minion.max_hp = 3 + hp_bonus
    minion.current_hp = minion.max_hp
    minion.base_defense = 10
    minion.summon_duration = 3
    return minion


# =============================================================================
# TARGETING INTELLIGENCE
# =============================================================================

def select_target_weighted(party: list) -> Optional["Character"]:
    """Select target weighted by inverse HP ratio (wounded chars targeted more)."""
    alive = [c for c in party if c.current_hp > 0]
    if not alive:
        return None
    if len(alive) == 1:
        return alive[0]

    # Weight: lower HP% = higher weight
    weights = []
    for c in alive:
        hp_ratio = c.current_hp / max(1, c.max_hp)
        weight = max(0.1, 1.0 - hp_ratio + 0.3)  # Base 0.3 + inverse HP%
        weights.append(weight)

    total = sum(weights)
    roll = random.random() * total
    cumulative = 0
    for i, w in enumerate(weights):
        cumulative += w
        if roll <= cumulative:
            return alive[i]
    return alive[-1]


# =============================================================================
# EXAMPLE GEAR (TIER I STARTER LOOT)
# =============================================================================

def create_starter_gear() -> List[GearItem]:
    """Create example Tier I gear from the SRD."""
    return [
        GearItem(
            name="Rusted Shortsword",
            slot=GearSlot.R_HAND,
            tier=GearTier.TIER_I,
            weight=2.0,
            description="A corroded blade. Better than your fists."
        ),
        GearItem(
            name="Padded Jerkin",
            slot=GearSlot.CHEST,
            tier=GearTier.TIER_I,
            damage_reduction=1,
            defense_bonus=1,
            weight=3.0,
            description="Quilted cloth armor. Provides minimal protection."
        ),
        GearItem(
            name="Old Oak Wand",
            slot=GearSlot.R_HAND,
            tier=GearTier.TIER_I,
            stat_bonuses={StatType.AETHER: 1},
            weight=0.5,
            description="A gnarled wooden wand. Channels magic poorly."
        ),
        GearItem(
            name="Burglar's Gloves",
            slot=GearSlot.ARMS,
            tier=GearTier.TIER_I,
            stat_bonuses={StatType.WITS: 1},
            special_traits=["[Lockpick]"],
            weight=0.5,
            description="Leather gloves with lockpicks sewn into the fingers."
        ),
        GearItem(
            name="Pot Lid Shield",
            slot=GearSlot.L_HAND,
            tier=GearTier.TIER_I,
            damage_reduction=1,
            special_traits=["[Intercept]"],
            weight=3.0,
            description="A makeshift shield. Allows you to protect allies."
        ),
        GearItem(
            name="Beckoning Bell",
            slot=GearSlot.L_HAND,
            tier=GearTier.TIER_I,
            stat_bonuses={StatType.AETHER: 1},
            special_traits=["[Summon]"],
            weight=0.5,
            description="A rusted iron bell that rings in the spirit realm."
        ),
        GearItem(
            name="Lantern of the Lost",
            slot=GearSlot.L_HAND,
            tier=GearTier.TIER_II,
            stat_bonuses={StatType.AETHER: 2},
            special_traits=["[Summon]", "[Light]"],
            weight=1.5,
            description="Its pale flame draws spirits from the other side."
        ),
        GearItem(
            name="Shortbow",
            slot=GearSlot.R_HAND,
            tier=GearTier.TIER_I,
            stat_bonuses={StatType.WITS: 1},
            special_traits=["[Ranged]"],
            weight=2.0,
            description="A crude hunting bow. Strikes from a distance."
        ),
        GearItem(
            name="Greatsword",
            slot=GearSlot.R_HAND,
            tier=GearTier.TIER_I,
            stat_bonuses={StatType.MIGHT: 2},
            special_traits=["[Cleave]"],
            two_handed=True,
            weight=5.0,
            description="A heavy two-handed blade. Cleaves through armor."
        ),
        GearItem(
            name="Grimoire",
            slot=GearSlot.R_HAND,
            tier=GearTier.TIER_I,
            stat_bonuses={StatType.WITS: 1},
            special_traits=["[Spellslot]"],
            weight=1.5,
            description="A battered tome of formulae. Knowledge is power."
        ),
        GearItem(
            name="Threadbare Robes",
            slot=GearSlot.CHEST,
            tier=GearTier.TIER_I,
            stat_bonuses={StatType.AETHER: 1},
            weight=1.0,
            description="Faded mystic robes. Channels ambient Aether."
        )
    ]


# =============================================================================
# STANDALONE TEST & DEMO
# =============================================================================

def test_dice_pool():
    """
    Standalone test for roll_dice_pool and roll_ambush.

    Verifies:
    - 5d6 hard cap enforcement
    - Dice math correctness
    - Ambush mechanics
    """
    print("=" * 60)
    print("DICE POOL TEST - WORK ORDER 051B")
    print("=" * 60)

    # Test 1: 5d6 cap enforcement
    print("\n[TEST 1: 5d6 CAP ENFORCEMENT]")
    for dice in [1, 3, 5, 7, 10]:
        result = roll_dice_pool(dice, modifier=2, dc=15)
        actual_dice = len(result['rolls'])
        expected = min(dice, 5)
        status = "PASS" if actual_dice == expected else "FAIL"
        print(f"Requested {dice}d6 -> Got {actual_dice}d6 [{status}]")

    # Test 2: Dice math verification
    print("\n[TEST 2: DICE MATH VERIFICATION]")
    for i in range(5):
        result = roll_dice_pool(3, modifier=2, dc=12)
        manual_total = sum(result['rolls']) + result['modifier']
        math_check = "PASS" if manual_total == result['total'] else "FAIL"
        print(f"Roll {i+1}: {result['rolls']} + {result['modifier']} = {result['total']} vs DC {result['dc']} -> {'SUCCESS' if result['success'] else 'FAIL'} [{math_check}]")

    # Test 3: Critical and Fumble detection
    print("\n[TEST 3: CRITICAL/FUMBLE DETECTION]")
    # Force a critical (all 6s) - using RNG, so we just show the detection logic
    test_crits = [
        ([6, 6, 6], "Expected: CRIT"),
        ([1, 1, 1], "Expected: FUMBLE"),
        ([3, 4, 5], "Expected: Neither")
    ]
    for rolls, expected in test_crits:
        crit = all(r == 6 for r in rolls)
        fumble = all(r == 1 for r in rolls)
        result_str = "CRIT" if crit else ("FUMBLE" if fumble else "Neither")
        print(f"  {rolls} -> {result_str} ({expected})")

    # Test 4: Ambush rolls
    print("\n[TEST 4: AMBUSH MECHANICS]")
    wits_mod = 2
    enemy_dc = 12

    print(f"Leader (Wits +{wits_mod}) attempts ambush vs Enemy Passive DC {enemy_dc}")
    for i in range(5):
        result = roll_ambush(wits_mod, enemy_dc)
        ambush_status = "SURPRISE ROUND GRANTED" if result['ambush_round'] else "NO SURPRISE"
        print(f"  Attempt {i+1}: {result['rolls']} + {result['modifier']} = {result['total']} -> {ambush_status}")

    # Test 5: Edge cases
    print("\n[TEST 5: EDGE CASES]")

    # Zero dice (should clamp to minimum)
    result = roll_dice_pool(0, modifier=5, dc=10)
    print(f"0d6 clamping: Got {len(result['rolls'])}d6 (Expected: 0d6 since no min enforced)")

    # Negative modifier
    result = roll_dice_pool(2, modifier=-2, dc=8)
    print(f"Negative modifier: {result['rolls']} + {result['modifier']} = {result['total']}")

    # DC 0 (auto-success)
    result = roll_dice_pool(1, modifier=0, dc=0)
    success_str = "SUCCESS" if result['success'] else "FAIL"
    print(f"DC 0 (auto-success): {result['rolls']} + {result['modifier']} = {result['total']} -> {success_str}")

    print("\n" + "=" * 60)
    print("DICE POOL TEST COMPLETE")
    print("=" * 60)


def run_demo():
    """Run a demonstration of the Burnwillow engine."""
    print("=" * 60)
    print("BURNWILLOW ENGINE v0.1 - STANDALONE TEST")
    print("=" * 60)

    # Initialize engine
    engine = BurnwillowEngine()

    # Create character
    print("\n[CHARACTER CREATION]")
    hero = engine.create_character("Kael the Wanderer")
    print(f"Name: {hero.name}")
    print(f"Might: {hero.might} (mod: {calculate_stat_mod(hero.might):+d})")
    print(f"Wits: {hero.wits} (mod: {calculate_stat_mod(hero.wits):+d})")
    print(f"Grit: {hero.grit} (mod: {calculate_stat_mod(hero.grit):+d})")
    print(f"Aether: {hero.aether} (mod: {calculate_stat_mod(hero.aether):+d})")
    print(f"HP: {hero.current_hp}/{hero.max_hp}")
    print(f"Defense: {hero.get_defense()}")

    # Equip starter gear
    print("\n[EQUIPPING GEAR]")
    starter_loot = create_starter_gear()
    sword = starter_loot[0]
    jerkin = starter_loot[1]
    gloves = starter_loot[3]

    hero.gear.equip(sword)
    hero.gear.equip(jerkin)
    hero.gear.equip(gloves)

    print(f"Equipped: {sword.name} ({sword.slot.value})")
    print(f"Equipped: {jerkin.name} ({jerkin.slot.value})")
    print(f"Equipped: {gloves.name} ({gloves.slot.value})")
    print(f"Total DR: {hero.gear.get_total_dr()}")
    print(f"Can pick locks: {hero.can_pick_locks()}")

    # Test skill checks
    print("\n[SKILL CHECKS]")

    # Attack a goblin (DC 12)
    print("\n1. Attack a Goblin (Might vs DC 12)")
    result = hero.make_check(StatType.MIGHT, DC.HARD.value)
    print(result)

    # Pick a lock (DC 12)
    print("\n2. Pick a Lock (Wits vs DC 12)")
    result = hero.make_check(StatType.WITS, DC.HARD.value)
    print(result)

    # Resist poison (DC 16)
    print("\n3. Resist Poison (Grit vs DC 16)")
    result = hero.make_check(StatType.GRIT, DC.HEROIC.value)
    print(result)

    # Cast a spell (DC 8)
    print("\n4. Cast Magic Missile (Aether vs DC 8)")
    result = hero.make_check(StatType.AETHER, DC.ROUTINE.value)
    print(result)

    # Test combat damage
    print("\n[COMBAT]")
    print(f"HP Before: {hero.current_hp}/{hero.max_hp}")

    damage_taken = hero.take_damage(5)
    print(f"Goblin attacks for 5 damage!")
    print(f"DR absorbs {5 - damage_taken} damage")
    print(f"Actual damage: {damage_taken}")
    print(f"HP After: {hero.current_hp}/{hero.max_hp}")

    healed = hero.heal(3)
    print(f"\nUsing bandages, heal {healed} HP")
    print(f"HP Now: {hero.current_hp}/{hero.max_hp}")

    # Test doom clock
    print("\n[DOOM CLOCK]")
    print("Resting in the dungeon...")
    events = engine.advance_doom(3)
    for event in events:
        print(event)

    print(f"Doom Clock: {engine.doom_clock.current}")

    # Test serialization
    print("\n[SAVE/LOAD]")
    save_data = engine.save_game()
    print(f"Game saved: {len(json.dumps(save_data))} bytes")

    # Simulate death and reload
    engine.reset()
    print("Character died! Engine reset.")

    engine.load_game(save_data)
    print("Game loaded!")
    print(f"Hero: {engine.character.name} ({engine.character.current_hp}/{engine.character.max_hp} HP)")

    # Test dungeon generation (NEW)
    print("\n[DUNGEON GENERATION]")
    dungeon_summary = engine.generate_dungeon(depth=3, seed=999)
    print(f"Generated dungeon with seed {dungeon_summary['seed']}")
    print(f"Total rooms: {dungeon_summary['total_rooms']}")
    print(f"Starting room: {dungeon_summary['start_room']}")

    current_room = engine.get_current_room()
    print(f"\n[CURRENT ROOM {current_room['id']}]")
    print(f"Type: {current_room['type']} | Tier: {current_room['tier']}")
    print(f"Description: {current_room['description']}")
    print(f"Enemies: {len(current_room['enemies'])}")
    print(f"Loot: {len(current_room['loot'])}")
    print(f"Hazards: {len(current_room['hazards'])}")

    connected = engine.get_connected_rooms()
    print(f"\n[CONNECTED ROOMS]")
    for room in connected:
        locked = " [LOCKED]" if room['is_locked'] else ""
        visited = " [VISITED]" if room['visited'] else ""
        print(f"  Room {room['id']}: {room['type']} (Tier {room['tier']}){locked}{visited}")

    # Try moving to a connected room
    if connected:
        target_id = connected[0]['id']
        print(f"\n[MOVEMENT TEST]")
        result = engine.move_to_room(target_id)
        print(f"Result: {result['message']}")
        if result['success']:
            new_room = result['room']
            print(f"Now in room {new_room['id']}: {new_room['description'][:50]}...")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


# Engine registration
try:
    from codex.core.engine_protocol import register_engine
    register_engine("burnwillow", BurnwillowEngine)
except ImportError:
    pass


if __name__ == "__main__":
    run_demo()

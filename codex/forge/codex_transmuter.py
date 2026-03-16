"""
codex_transmuter.py - The System Translation Layer
====================================================
WO-103/Batch-003: Cross-system character conversion for Burnwillow.

Handles:
- Burnwillow native: stat normalization, loadout -> gear expansion, HP calculation
- D&D 5e cross-system: 6->4 stat mapping (best-of), class -> loadout, HD-based HP

HP Formula: MaxHP = 10 + Grit_Mod (Burnwillow native formula)

Policy: If a system engine is missing, raise MissingEngineError.
        Never silently fallback to Burnwillow.

Author: Codex Team (WO 103 / Batch 003)
"""

from typing import Dict, List, Optional, Tuple
from codex.games.burnwillow.engine import (
    Character, GearItem, GearGrid, GearSlot, GearTier, StatType,
    calculate_stat_mod, create_starter_gear,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class MissingEngineError(RuntimeError):
    """Raised when a campaign requires a system engine that is not available."""
    pass


# =============================================================================
# MAPPING TABLES
# =============================================================================

# Loadout ID -> starter gear indices (from create_starter_gear() return list)
LOADOUT_GEAR_MAP: Dict[str, List[int]] = {
    "sellsword": [0, 1, 3],   # Sword + Jerkin + Gloves [Lockpick]
    "occultist": [2, 5, 1],   # Wand + Bell [Summon] + Jerkin
    "sentinel":  [0, 4, 1],   # Sword + Shield [Intercept] + Jerkin
    "archer":    [7, 1],       # Shortbow [Ranged] + Jerkin
    "vanguard":  [8, 1],       # Greatsword [Cleave] + Jerkin
    "scholar":   [9, 10, 3],   # Grimoire [Spellslot] + Robes + Gloves
}

# Loadout -> hit die (for HP formula)
LOADOUT_HIT_DIE: Dict[str, int] = {
    "vanguard": 12, "sellsword": 10, "sentinel": 10, "archer": 10,
    "occultist": 8, "scholar": 6,
}

# D&D 5e class ID -> best-fit Burnwillow loadout
DND5E_CLASS_TO_LOADOUT: Dict[str, str] = {
    "barbarian": "vanguard",  "fighter": "sellsword",  "paladin": "sentinel",
    "ranger": "archer",       "rogue": "sellsword",    "monk": "sellsword",
    "bard": "occultist",      "cleric": "sentinel",    "druid": "occultist",
    "sorcerer": "occultist",  "warlock": "occultist",  "wizard": "scholar",
    "artificer": "scholar",   "blood_hunter": "sellsword",
}

# D&D 5e class -> hit die
DND5E_CLASS_HIT_DIE: Dict[str, int] = {
    "barbarian": 12,
    "fighter": 10, "paladin": 10, "ranger": 10,
    "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8, "warlock": 8,
    "sorcerer": 6, "wizard": 6, "artificer": 8, "blood_hunter": 10,
}

# Supported system engines (add new engines here as they come online)
SUPPORTED_ENGINES = {"burnwillow", "dnd5e", "bitd", "sav", "bob", "cbrpnk", "stc", "candela", "crown"}

# Keyword -> GearSlot for inventory item mapping
ITEM_SLOT_KEYWORDS: Dict[GearSlot, List[str]] = {
    GearSlot.CHEST: [
        "armor", "mail", "plate", "leather", "robe", "jerkin",
        "breastplate", "hide", "padded", "studded", "chain",
    ],
    GearSlot.R_HAND: [
        "sword", "axe", "mace", "dagger", "bow", "staff", "wand", "spear",
        "crossbow", "hammer", "flail", "halberd", "rapier", "scimitar",
        "morningstar", "maul", "pike", "lance", "trident", "javelin",
        "glaive", "whip", "greataxe", "greatsword", "quarterstaff",
        "handaxe", "club", "sickle", "sling", "blowgun", "grimoire",
    ],
    GearSlot.L_HAND: ["shield"],
    GearSlot.HEAD: ["helm", "hat", "circlet", "crown", "hood"],
    GearSlot.ARMS: ["gloves", "gauntlet", "bracer"],
}


# =============================================================================
# CHARACTER TRANSMUTER
# =============================================================================

class CharacterAdapter:
    """Cross-system character translation layer.

    Policy: Only converts characters whose system_id is in SUPPORTED_ENGINES.
    Raises MissingEngineError for unknown systems.
    """

    @staticmethod
    def convert(wizard_data: dict) -> Character:
        """Convert wizard CharacterSheet dict -> live Burnwillow Character.

        Args:
            wizard_data: Dict from saved wizard JSON or campaign.json character entry.

        Returns:
            Character object ready for BurnwillowEngine.party injection.

        Raises:
            MissingEngineError: If system_id is not in SUPPORTED_ENGINES.
        """
        system_id = wizard_data.get("system_id", "burnwillow").lower()
        if system_id not in SUPPORTED_ENGINES:
            raise MissingEngineError(
                f"No engine available for system '{system_id}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_ENGINES))}"
            )

        engine_dict = CharacterAdapter.convert_wizard_to_engine(wizard_data)
        char = Character.from_dict(engine_dict)

        # Override max_hp with adapter's HD-based formula
        adapter_hp = engine_dict.get("_adapter_max_hp")
        if adapter_hp is not None:
            char.max_hp = adapter_hp
            char.current_hp = adapter_hp

        return char

    @staticmethod
    def convert_wizard_to_engine(wizard_data: dict) -> dict:
        """Convert wizard dict -> dict compatible with Character.from_dict()."""
        system = wizard_data.get("system_id", "burnwillow")
        name = wizard_data.get("name", "Unknown")
        choices = wizard_data.get("choices", {})
        raw_stats = wizard_data.get("stats", {})
        level = wizard_data.get("level", 1)

        # --- Stat mapping ---
        if system == "dnd5e":
            stats = CharacterAdapter._map_dnd5e_stats(raw_stats)
        elif system == "stc":
            stats = CharacterAdapter._map_stc_stats(raw_stats)
        elif system == "candela":
            stats = CharacterAdapter._map_candela_stats(raw_stats)
        else:
            stats = {k.lower(): v for k, v in raw_stats.items()}

        might = stats.get("might", 10)
        wits = stats.get("wits", 10)
        grit = stats.get("grit", 10)
        aether = stats.get("aether", 10)

        # --- Resolve loadout + hit die ---
        if system == "dnd5e":
            class_choice = choices.get("class", {})
            class_id = class_choice.get("id", "") if isinstance(class_choice, dict) else str(class_choice)
            loadout_id = DND5E_CLASS_TO_LOADOUT.get(class_id.lower(), "sellsword")
            hit_die = DND5E_CLASS_HIT_DIE.get(class_id.lower(), 10)
        else:
            loadout_choice = choices.get("loadout", {})
            loadout_id = loadout_choice.get("id", "sellsword") if isinstance(loadout_choice, dict) else str(loadout_choice)
            hit_die = LOADOUT_HIT_DIE.get(loadout_id, 10)

        # --- HP: (HitDie / 2) + CON_Mod + (Level * 2) ---
        grit_mod = calculate_stat_mod(grit)
        max_hp = 10 + grit_mod

        # --- Gear mapping ---
        raw_inventory = wizard_data.get("inventory", [])
        if raw_inventory:
            gear_dict, backpack = CharacterAdapter._map_inventory_to_gear(raw_inventory)
        else:
            gear_dict = CharacterAdapter._build_gear_grid(loadout_id)
            backpack = []

        return {
            "name": name,
            "might": might,
            "wits": wits,
            "grit": grit,
            "aether": aether,
            "current_hp": max_hp,
            "gear": gear_dict,
            "inventory": backpack,
            "keys": 1,
            "_adapter_max_hp": max_hp,
        }

    @staticmethod
    def convert_campaign_characters(campaign_data: dict) -> List[Character]:
        """Convert all characters from a campaign.json manifest.

        Args:
            campaign_data: Full campaign manifest dict (has 'characters' list).

        Returns:
            List of Character objects (capped at 4 for Burnwillow party limit).

        Raises:
            MissingEngineError: If any character uses an unsupported system.
        """
        characters = []
        for char_data in campaign_data.get("characters", [])[:4]:
            characters.append(CharacterAdapter.convert(char_data))
        return characters

    # --- Internal helpers ---

    @staticmethod
    def _map_dnd5e_stats(stats: dict) -> dict:
        """Map 6 D&D 5e stats to 4 Burnwillow stats (best-of pairing)."""
        return {
            "might":  stats.get("Strength", 10),
            "wits":   max(stats.get("Dexterity", 10), stats.get("Intelligence", 10)),
            "grit":   stats.get("Constitution", 10),
            "aether": max(stats.get("Wisdom", 10), stats.get("Charisma", 10)),
        }

    @staticmethod
    def _map_stc_stats(stats: dict) -> dict:
        """Map 3 Cosmere attributes to 4 Burnwillow stats."""
        s = stats.get("strength", stats.get("Strength", 10))
        sp = stats.get("speed", stats.get("Speed", 10))
        i = stats.get("intellect", stats.get("Intellect", 10))
        return {"might": s, "wits": sp, "grit": max(s, sp), "aether": i}

    @staticmethod
    def _map_candela_stats(stats: dict) -> dict:
        """Map 3 Candela attributes (0-3 scale) to Burnwillow (10-16 scale)."""
        def scale(v): return 10 + (v * 2)
        n = stats.get("Nerve", stats.get("nerve", 1))
        c = stats.get("Cunning", stats.get("cunning", 1))
        i = stats.get("Intuition", stats.get("intuition", 1))
        return {"might": scale(n), "wits": scale(c), "grit": scale(n), "aether": scale(i)}

    @staticmethod
    def _build_gear_grid(loadout_id: str) -> dict:
        """Build serialized GearGrid dict from loadout ID."""
        starter = create_starter_gear()
        indices = LOADOUT_GEAR_MAP.get(loadout_id, LOADOUT_GEAR_MAP["sellsword"])

        grid = GearGrid()
        for idx in indices:
            if 0 <= idx < len(starter):
                grid.equip(starter[idx])

        return grid.to_dict()

    @staticmethod
    def _map_inventory_to_gear(items: list) -> Tuple[dict, list]:
        """Map a list of item name strings to gear slots by keyword."""
        grid = GearGrid()
        backpack = []

        for item_name in items:
            if not isinstance(item_name, str):
                continue
            name_lower = item_name.lower()

            matched_slot = None
            for slot, keywords in ITEM_SLOT_KEYWORDS.items():
                if any(kw in name_lower for kw in keywords):
                    matched_slot = slot
                    break

            if matched_slot and grid.slots.get(matched_slot) is None:
                gear_item = GearItem(
                    name=item_name,
                    slot=matched_slot,
                    tier=GearTier.TIER_I,
                    description="Converted from wizard inventory.",
                )
                grid.equip(gear_item)
            else:
                backpack.append(GearItem(
                    name=item_name,
                    slot=GearSlot.R_HAND,
                    tier=GearTier.TIER_I,
                    description="Carried in backpack.",
                ).to_dict())

        return grid.to_dict(), backpack

"""
codex/forge/content_pool.py — Normalized Content Pool Adapter
==============================================================
Reads from heterogeneous content sources (bestiary JSONs, loot JSONs,
ENCOUNTER_TABLE/LOCATION_DESCRIPTIONS module constants, dm_tools NPC tables)
and presents a uniform interface for the module generator.

Handles two bestiary formats:
  - D&D 5e: base_hp / base_ac / base_atk / base_dmg fields
  - FITD:   threat_level field (synthetic stats via _FITD_STAT_SCALE)

Handles two loot value fields:
  - D&D 5e: value_gp
  - FITD:   value_coin
"""

from __future__ import annotations

import importlib
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Normalised dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PoolLocation:
    """A named location with a description and topology hint."""
    name: str
    description: str
    topology: str = "settlement"


@dataclass
class PoolNPC:
    """A generated NPC ready for scene wiring."""
    name: str
    role: str = ""
    dialogue: str = ""
    notes: str = ""

    def to_scene_dict(self) -> dict:
        """Convert to content_hints NPC format expected by SceneData."""
        return {
            "name": self.name,
            "role": self.role,
            "dialogue": self.dialogue,
            "notes": self.notes,
        }


@dataclass
class PoolEnemy:
    """A combat-ready adversary with normalised stat block."""
    name: str
    tier: int = 1
    hp: int = 10
    ac: int = 10
    attack: int = 3
    damage: str = "1d6"
    is_boss: bool = False
    description: str = ""

    def to_scene_dict(self) -> dict:
        """Convert to content_hints enemy format expected by SceneData."""
        d: dict = {
            "name": self.name,
            "hp": self.hp,
            "ac": self.ac,
            "attack": self.attack,
            "damage": self.damage,
        }
        if self.is_boss:
            d["is_boss"] = True
        return d


@dataclass
class PoolLoot:
    """A loot entry with normalised value in abstract 'credits'."""
    name: str
    tier: int = 1
    value: int = 0
    description: str = ""

    def to_scene_dict(self) -> dict:
        """Convert to content_hints loot format expected by SceneData."""
        return {
            "name": self.name,
            "value": self.value,
            "type": "common" if self.tier <= 2 else "rare",
        }


@dataclass
class PoolMagicItem:
    """A magic/special item with rarity information."""
    name: str
    rarity: str = "common"
    item_type: str = "wondrous"
    description: str = ""
    attunement: bool = False

    def to_scene_dict(self) -> dict:
        return {
            "name": self.name,
            "rarity": self.rarity,
            "type": self.item_type,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# System-level constants
# ---------------------------------------------------------------------------

# Visual theme used by the spatial renderer for each system.
_SYSTEM_THEMES: Dict[str, str] = {
    "bitd": "GOTHIC",
    "sav": "STONE",
    "bob": "STONE",
    "cbrpnk": "RUST",
    "candela": "GOTHIC",
    "dnd5e": "STONE",
    "stc": "STONE",
    "crown": "STONE",
    "burnwillow": "RUST",
}

# Synthetic combat stats for FITD adversaries (which have no AC/HP in the source).
# Keyed by threat_level (1-4).
_FITD_STAT_SCALE: Dict[int, Dict[str, Any]] = {
    1: {"hp": 8,  "ac": 10, "attack": 2, "damage": "1d4"},
    2: {"hp": 15, "ac": 12, "attack": 4, "damage": "1d6"},
    3: {"hp": 25, "ac": 14, "attack": 6, "damage": "1d8+2"},
    4: {"hp": 40, "ac": 16, "attack": 8, "damage": "2d6+3"},
}

# Fallback locations used when a system module has no LOCATION_DESCRIPTIONS.
_GENERIC_LOCATIONS: List[PoolLocation] = [
    PoolLocation(name="chamber", description="A dimly lit chamber."),
    PoolLocation(name="corridor", description="A narrow passage stretches ahead."),
    PoolLocation(name="vault", description="Thick stone walls surround a secured room."),
]


# ---------------------------------------------------------------------------
# ContentPool
# ---------------------------------------------------------------------------

class ContentPool:
    """Normalised content pool for a specific game system.

    Loads content lazily from:
      1. config/bestiary/{system_id}.json   — enemy stat blocks
      2. config/loot/{system_id}.json       — loot tables
      3. codex.games.{system_id}.LOCATION_DESCRIPTIONS — room flavour
      4. codex.games.{system_id}.ENCOUNTER_TABLE       — encounter strings
      5. codex.core.dm_tools._NPC_NAMES / _NPC_TRAITS / _NPC_QUIRKS — NPCs

    Args:
        system_id: Registered system name (e.g. "bitd", "dnd5e", "stc").
        seed:      Optional RNG seed for reproducible generation.
    """

    def __init__(self, system_id: str, seed: Optional[int] = None) -> None:
        self.system_id = system_id
        self._rng = random.Random(seed)
        self._bestiary: Dict[str, List[dict]] = self._load_bestiary()
        self._loot: Dict[str, List[dict]] = self._load_loot()
        self._locations: List[PoolLocation] = self._load_locations()
        self._encounters: List[Any] = self._load_encounters()
        self._config_npcs: List[dict] = self._load_npcs_from_config()
        self._traps: Dict[str, List[dict]] = self._load_traps()
        self._tables: Dict[str, Any] = self._load_tables()
        self._magic_items: List[dict] = self._load_magic_items()

    # ------------------------------------------------------------------
    # Private loaders
    # ------------------------------------------------------------------

    def _load_bestiary(self) -> Dict[str, List[dict]]:
        """Load tiered bestiary from config/bestiary/{system_id}.json.

        Returns:
            Dict mapping tier string ("1"-"4") to list of enemy entries.
        """
        try:
            from codex.core.config_loader import load_config
            data = load_config("bestiary", self.system_id)
            if data and "tiers" in data:
                return data["tiers"]
        except Exception:
            pass
        return {}

    def _load_loot(self) -> Dict[str, List[dict]]:
        """Load tiered loot from config/loot/{system_id}.json.

        Returns:
            Dict mapping tier string ("1"-"4") to list of loot entries.
        """
        try:
            from codex.core.config_loader import load_config
            data = load_config("loot", self.system_id)
            if data and "tiers" in data:
                return data["tiers"]
        except Exception:
            pass
        return {}

    def _load_locations(self) -> List[PoolLocation]:
        """Load locations from config JSON first, falling back to engine module.

        Prefers config/locations/{system_id}.json if it exists.  Falls back to
        LOCATION_DESCRIPTIONS constant from the system's engine module.
        """
        # Try config-sourced locations first.
        config_locs = self._load_locations_from_config()
        if config_locs:
            return config_locs

        # Fall back to engine module constant.
        locations: List[PoolLocation] = []
        try:
            mod = importlib.import_module(f"codex.games.{self.system_id}")
            loc_descs = getattr(mod, "LOCATION_DESCRIPTIONS", {})
            if isinstance(loc_descs, dict):
                for loc_name, desc_list in loc_descs.items():
                    if isinstance(desc_list, (list, tuple)):
                        for desc in desc_list:
                            locations.append(
                                PoolLocation(name=str(loc_name), description=str(desc))
                            )
                    else:
                        # desc_list is a bare string
                        locations.append(
                            PoolLocation(name=str(loc_name), description=str(desc_list))
                        )
        except (ImportError, Exception):
            pass
        return locations

    def _load_locations_from_config(self) -> List[PoolLocation]:
        """Load locations from config/locations/{system_id}.json.

        Handles two list shapes:
          - chapter_houses / newfaire_locations (Candela format)
          - flat list of location dicts

        Returns:
            List of PoolLocation objects, empty if config not found.
        """
        try:
            from codex.core.config_loader import load_config
            data = load_config("locations", self.system_id)
            if not data:
                return []
        except Exception:
            return []

        locations: List[PoolLocation] = []
        # Check every top-level key that holds a list of location dicts.
        # Handles: chapter_houses, newfaire_locations, locations, dungeons,
        # settlements, waterdeep_wards, and any future category keys.
        for key, val in data.items():
            if not isinstance(val, list):
                continue
            for entry in val:
                if isinstance(entry, dict) and entry.get("name"):
                    locations.append(
                        PoolLocation(
                            name=entry.get("name", "Unknown"),
                            description=entry.get("description", ""),
                            topology=entry.get("topology", "settlement"),
                        )
                    )
        return locations

    def _load_npcs_from_config(self) -> List[dict]:
        """Load NPCs from config/npcs/{system_id}.json.

        Handles three shapes:
          - named_npcs: flat list of NPC dicts
          - generic_templates: flat list of NPC archetype dicts
          - assignment_npcs: dict of assignment_id -> list of NPC dicts

        Returns:
            Flat list of NPC dicts, empty if config not found.
        """
        try:
            from codex.core.config_loader import load_config
            data = load_config("npcs", self.system_id)
            if not data:
                return []
        except Exception:
            return []

        npcs: List[dict] = []
        # Collect from named_npcs list.
        for entry in data.get("named_npcs", []):
            if isinstance(entry, dict):
                npcs.append(entry)
        # Collect from generic_templates list.
        for entry in data.get("generic_templates", []):
            if isinstance(entry, dict):
                npcs.append(entry)
        # Collect from assignment_npcs dict-of-lists.
        assignment_npcs = data.get("assignment_npcs", {})
        if isinstance(assignment_npcs, dict):
            for entries in assignment_npcs.values():
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict):
                            npcs.append(entry)
        return npcs

    def _load_traps(self) -> Dict[str, List[dict]]:
        """Load tiered traps from config/traps/{system_id}.json.

        Returns:
            Dict mapping tier string ("1"-"4") to list of trap entries.
        """
        try:
            from codex.core.config_loader import load_config
            data = load_config("traps", self.system_id)
            if data and "traps" in data:
                # Flat list with tier field — bucket by tier
                by_tier: Dict[str, List[dict]] = {"1": [], "2": [], "3": [], "4": []}
                for trap in data["traps"]:
                    tier = str(max(1, min(4, trap.get("tier", 1))))
                    by_tier[tier].append(trap)
                return by_tier
            if data and "tiers" in data:
                return data["tiers"]
        except Exception:
            pass
        return {}

    def _load_tables(self) -> Dict[str, Any]:
        """Load procedural generation tables from config/tables/{system_id}_*.json.

        Scans for all table files matching the system prefix and merges them.

        Returns:
            Dict mapping table category to table data.
        """
        import json
        from pathlib import Path

        tables: Dict[str, Any] = {}
        try:
            # Resolve tables directory relative to project root
            project_root = Path(__file__).resolve().parent.parent.parent
            tables_dir = project_root / "config" / "tables"
            if not tables_dir.exists():
                return tables
            prefix = f"{self.system_id}_"
            for fp in sorted(tables_dir.iterdir()):
                if fp.suffix == ".json" and fp.stem.startswith(prefix):
                    try:
                        data = json.loads(fp.read_text(encoding="utf-8"))
                        category = fp.stem[len(prefix):]
                        tables[category] = data
                    except Exception:
                        continue
        except Exception:
            pass
        return tables

    def _load_magic_items(self) -> List[dict]:
        """Load magic items from config/magic_items/{system_id}.json."""
        try:
            from codex.core.config_loader import load_config
            data = load_config("magic_items", self.system_id)
            if data and "items" in data:
                return data["items"]
        except Exception:
            pass
        return []

    def _load_encounters(self) -> List[Any]:
        """Load ENCOUNTER_TABLE from the system's engine module.

        Returns an empty list if the constant doesn't exist yet.
        """
        try:
            mod = importlib.import_module(f"codex.games.{self.system_id}")
            table = getattr(mod, "ENCOUNTER_TABLE", [])
            if isinstance(table, (list, tuple)):
                return list(table)
        except (ImportError, Exception):
            pass
        return []

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_locations(self, topology: str = "") -> List[PoolLocation]:
        """Return all available locations, filtered by topology if given.

        Falls back to generic chambers if no system-specific locations exist.

        Args:
            topology: Optional filter string (e.g. "settlement", "dungeon").

        Returns:
            List of PoolLocation objects.
        """
        if not self._locations:
            return list(_GENERIC_LOCATIONS)
        if topology:
            filtered = [l for l in self._locations if l.topology == topology]
            return filtered if filtered else list(self._locations)
        return list(self._locations)

    def get_npcs(
        self,
        tier: int = 1,
        role: str = "",
        count: int = 1,
    ) -> List[PoolNPC]:
        """Return NPCs, preferring config-sourced data when available.

        If config/npcs/{system_id}.json exists, draws from that pool first.
        Falls back to procedural generation via dm_tools name tables.

        Args:
            tier:  Unused in NPC generation (kept for API consistency).
            role:  Filter by role if config NPCs available; overrides default
                   "merchant" role label for procedural NPCs.
            count: Number of NPCs to return.

        Returns:
            List of PoolNPC objects with name, role, and dialogue.
        """
        # Prefer config-sourced NPCs when available.
        if self._config_npcs:
            pool = self._config_npcs
            if role:
                filtered = [n for n in pool if n.get("role", "") == role]
                pool = filtered if filtered else pool
            selected = [self._rng.choice(pool) for _ in range(count)]
            return [
                PoolNPC(
                    name=n.get("name", "Unknown"),
                    role=n.get("role", role or "npc"),
                    dialogue=n.get("dialogue", n.get("description", "")),
                    notes=n.get("notes", ""),
                )
                for n in selected
            ]

        # Fall back to procedural generation.
        from codex.core.dm_tools import _NPC_NAMES, _NPC_TRAITS, _NPC_QUIRKS

        npcs: List[PoolNPC] = []
        for _ in range(count):
            name = self._rng.choice(_NPC_NAMES)
            trait = self._rng.choice(_NPC_TRAITS)
            quirk = self._rng.choice(_NPC_QUIRKS)
            dialogue = f"A {trait.lower()} individual. {quirk}."
            npcs.append(
                PoolNPC(
                    name=name,
                    role=role or "merchant",
                    dialogue=dialogue,
                )
            )
        return npcs

    def get_enemies(self, tier: int = 1, count: int = 1) -> List[PoolEnemy]:
        """Return random enemies from the bestiary at the given tier.

        Args:
            tier:  Difficulty tier (1-4).
            count: Number of enemies to draw.

        Returns:
            List of PoolEnemy objects with normalised stats.
            Falls back to a generic placeholder if the bestiary is empty.
        """
        tier_key = str(max(1, min(4, tier)))
        pool = self._bestiary.get(tier_key, [])
        if not pool:
            return [
                PoolEnemy(name=f"Tier {tier} Adversary", tier=tier)
                for _ in range(count)
            ]
        enemies: List[PoolEnemy] = []
        for _ in range(count):
            entry = self._rng.choice(pool)
            enemies.append(self._entry_to_enemy(entry, tier))
        return enemies

    def get_boss(self, tier: int = 1) -> PoolEnemy:
        """Return the most dangerous entry from the tier as a boss.

        Selects the entry with the highest threat_level or base_hp and
        applies a 1.5× HP multiplier.

        Args:
            tier: Difficulty tier (1-4).

        Returns:
            A single PoolEnemy flagged as is_boss=True.
        """
        tier_key = str(max(1, min(4, tier)))
        pool = self._bestiary.get(tier_key, [])
        if pool:
            # Prefer explicit threat_level; fall back to base_hp for D&D format.
            entry = max(
                pool,
                key=lambda e: e.get("threat_level", e.get("base_hp", 0)),
            )
            boss = self._entry_to_enemy(entry, tier)
            boss.is_boss = True
            boss.hp = int(boss.hp * 1.5)
            return boss
        return PoolEnemy(
            name=f"Tier {tier} Boss",
            tier=tier,
            hp=30 * tier,
            is_boss=True,
        )

    def get_loot(self, tier: int = 1, count: int = 1) -> List[PoolLoot]:
        """Return random loot items from the tier pool.

        Normalises value from either value_gp (D&D 5e) or value_coin (FITD)
        to a single `value` integer.

        Args:
            tier:  Loot tier (1-4).
            count: Number of items to draw.

        Returns:
            List of PoolLoot objects.
        """
        tier_key = str(max(1, min(4, tier)))
        pool = self._loot.get(tier_key, [])
        if not pool:
            return [
                PoolLoot(name=f"Tier {tier} Trinket", tier=tier, value=tier * 10)
                for _ in range(count)
            ]
        items: List[PoolLoot] = []
        for _ in range(count):
            entry = self._rng.choice(pool)
            if isinstance(entry, dict):
                name = entry.get("name", "Loot")
                # D&D 5e uses value_gp; FITD uses value_coin; generic uses value.
                value = entry.get(
                    "value",
                    entry.get("value_gp", entry.get("value_coin", tier * 10)),
                )
            else:
                name = str(entry)
                value = tier * 10
            items.append(PoolLoot(name=name, tier=tier, value=int(value)))
        return items

    def get_encounters(self) -> List[Any]:
        """Return the raw ENCOUNTER_TABLE entries for this system.

        Returns:
            List of encounter strings/dicts (empty if constant not defined).
        """
        return list(self._encounters)

    def get_traps(self, tier: int = 1, count: int = 1) -> List[dict]:
        """Return random traps from the tier pool.

        Args:
            tier:  Difficulty tier (1-4).
            count: Number of traps to draw.

        Returns:
            List of trap dicts with name, trigger, dc_detect, dc_disarm,
            damage, damage_type, description.
        """
        tier_key = str(max(1, min(4, tier)))
        pool = self._traps.get(tier_key, [])
        if not pool:
            return []
        return [self._rng.choice(pool) for _ in range(count)]

    def get_magic_items(
        self, rarity: str = "", count: int = 1,
    ) -> List[PoolMagicItem]:
        """Return magic items, optionally filtered by rarity.

        Args:
            rarity: Filter by rarity (common/uncommon/rare/very_rare/legendary).
            count:  Number of items to return.

        Returns:
            List of PoolMagicItem objects.
        """
        if not self._magic_items:
            return []
        pool = self._magic_items
        if rarity:
            filtered = [i for i in pool if i.get("rarity", "") == rarity]
            pool = filtered if filtered else pool
        selected = [self._rng.choice(pool) for _ in range(min(count, len(pool)))]
        return [
            PoolMagicItem(
                name=item.get("name", "Unknown"),
                rarity=item.get("rarity", "common"),
                item_type=item.get("type", "wondrous"),
                description=item.get("description", ""),
                attunement=item.get("attunement", False),
            )
            for item in selected
        ]

    def get_table(self, category: str) -> Optional[dict]:
        """Return a procedural generation table by category name.

        Categories correspond to the file suffix after the system prefix,
        e.g. ``dnd5e_dungeon_generation.json`` -> category ``dungeon_generation``.

        Args:
            category: Table category name.

        Returns:
            Parsed table data dict, or None if not found.
        """
        return self._tables.get(category)

    def get_all_tables(self) -> Dict[str, Any]:
        """Return all loaded procedural generation tables.

        Returns:
            Dict mapping category name to table data.
        """
        return dict(self._tables)

    def get_system_theme(self) -> str:
        """Return the spatial renderer theme name for this system.

        Returns:
            One of "GOTHIC", "STONE", or "RUST".
        """
        return _SYSTEM_THEMES.get(self.system_id, "STONE")

    def get_display_name(self) -> str:
        """Return a human-readable display name for the system.

        Attempts to read `display_name` from the system's engine class;
        falls back to the uppercased system_id.

        Returns:
            Display name string.
        """
        try:
            mod = importlib.import_module(f"codex.games.{self.system_id}")
            for attr_name in dir(mod):
                cls = getattr(mod, attr_name)
                if (
                    isinstance(cls, type)
                    and hasattr(cls, "display_name")
                    and hasattr(cls, "system_id")
                ):
                    return cls.display_name
        except Exception:
            pass
        return self.system_id.upper()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _entry_to_enemy(self, entry: dict, tier: int) -> PoolEnemy:
        """Convert a raw bestiary entry to a PoolEnemy.

        Handles both D&D 5e format (base_hp/base_ac/base_atk/base_dmg) and
        FITD format (threat_level — synthetic stats via _FITD_STAT_SCALE).

        Args:
            entry: Raw dict from the bestiary JSON tier pool.
            tier:  Fallback tier used when threat_level is absent.

        Returns:
            Populated PoolEnemy instance.
        """
        name = entry.get("name", "Unknown")
        desc = entry.get("description", "")

        # D&D 5e format: explicit stat block fields.
        if "base_hp" in entry:
            return PoolEnemy(
                name=name,
                tier=tier,
                hp=int(entry.get("base_hp", 10)),
                ac=int(entry.get("base_ac", 10)),
                attack=int(entry.get("base_atk", 3)),
                damage=str(entry.get("base_dmg", "1d6")),
                description=desc,
            )

        # FITD format: use threat_level to look up synthetic stats.
        threat = int(entry.get("threat_level", entry.get("tier", tier)))
        stats = _FITD_STAT_SCALE.get(min(4, max(1, threat)), _FITD_STAT_SCALE[1])
        return PoolEnemy(
            name=name,
            tier=tier,
            hp=stats["hp"],
            ac=stats["ac"],
            attack=stats["attack"],
            damage=stats["damage"],
            description=desc,
        )

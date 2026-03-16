"""
Cartography Service -- Bridge to the Map Generator.
====================================================

Bridges location descriptions (from FAISS-indexed PDFs or live game
sessions) to the spatial map generator for visual reproduction.

WO-V10.0: Fully implemented BSP generation path with adapter routing.

Usage:
    from codex.core.services.cartography import generate_map_from_context

    result = generate_map_from_context({
        "location_name": "The Sunken Reliquary",
        "system_id": "burnwillow",
        "seed": 42,
    })
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional

from codex.paths import VAULT_MAPS_DIR

# Use canonical re-export path for map engine (gives spatial/__init__.py a consumer)
try:
    from codex.core.services.spatial import CodexMapEngine  # noqa: F401
except ImportError:
    CodexMapEngine = None

try:
    from codex.spatial.map_engine import (
        RoomNode, RoomType, RulesetAdapter, PopulatedRoom, ContentInjector,
        DungeonGraph,
    )
    MAP_ENGINE_AVAILABLE = True
except ImportError:
    MAP_ENGINE_AVAILABLE = False


# =========================================================================
# GENERIC ADAPTER (WO-V10.0)
# =========================================================================

_GENERIC_ENEMIES: Dict[int, List[str]] = {
    1: ["Bandit", "Giant Rat", "Skeleton"],
    2: ["Orc Warrior", "Shadow Beast", "Dire Wolf"],
    3: ["Troll", "Wraith", "Chimera"],
    4: ["Dragon Wyrmling", "Death Knight", "Beholder Zombie"],
}

_GENERIC_LOOT: Dict[int, List[str]] = {
    1: ["Healing Potion", "Rusty Shortsword", "Leather Shield"],
    2: ["Steel Longsword", "Chain Shirt", "Scroll of Protection"],
    3: ["Enchanted Blade", "Mithral Armor", "Ring of Resistance"],
    4: ["Legendary Weapon", "Artifact Fragment", "Crown of Command"],
}


class GenericAdapter(RulesetAdapter):
    """Minimal RulesetAdapter for non-Burnwillow systems.

    Provides basic enemy/loot pools so any system can generate maps.
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed is not None else random.randint(0, 999999)

    def populate_room(self, room: RoomNode) -> PopulatedRoom:
        rng = random.Random(self.seed + room.id)
        tier = max(1, min(4, room.tier))
        content = {"enemies": [], "loot": [], "hazards": [], "interactive": []}

        if room.room_type == RoomType.START:
            pass  # Safe zone
        elif room.room_type == RoomType.BOSS:
            enemy_name = rng.choice(_GENERIC_ENEMIES.get(tier, _GENERIC_ENEMIES[1]))
            hp = rng.randint(15 * tier, 25 * tier)
            content["enemies"].append({
                "name": enemy_name, "hp": hp, "max_hp": hp,
                "is_boss": True, "tier": tier,
            })
            loot_pool = _GENERIC_LOOT.get(min(4, tier + 1), _GENERIC_LOOT[1])
            content["loot"].extend([{"name": rng.choice(loot_pool)} for _ in range(rng.randint(2, 3))])
        elif room.room_type == RoomType.TREASURE:
            loot_pool = _GENERIC_LOOT.get(tier, _GENERIC_LOOT[1])
            content["loot"].extend([{"name": rng.choice(loot_pool)} for _ in range(rng.randint(2, 4))])
        else:
            enemy_pool = _GENERIC_ENEMIES.get(tier, _GENERIC_ENEMIES[1])
            count = rng.randint(0, 2)
            for _ in range(count):
                name = rng.choice(enemy_pool)
                hp = rng.randint(4 * tier, 10 * tier)
                content["enemies"].append({
                    "name": name, "hp": hp, "max_hp": hp, "tier": tier,
                })
            if rng.random() < 0.4:
                loot_pool = _GENERIC_LOOT.get(tier, _GENERIC_LOOT[1])
                content["loot"].append({"name": rng.choice(loot_pool)})

        return PopulatedRoom(geometry=room, content=content)

    def get_enemy_pool(self, tier: int) -> List[str]:
        return list(_GENERIC_ENEMIES.get(max(1, min(4, tier)), _GENERIC_ENEMIES[1]))

    def get_loot_pool(self, tier: int) -> List[str]:
        return list(_GENERIC_LOOT.get(max(1, min(4, tier)), _GENERIC_LOOT[1]))


# =========================================================================
# ADAPTER ROUTER (WO-V10.0)
# =========================================================================

def _get_adapter(system_id: str, seed: Optional[int] = None):
    """Route system_id to the appropriate RulesetAdapter."""
    sid = system_id.lower()

    if sid == "burnwillow":
        try:
            from codex.spatial.map_engine import BurnwillowAdapter
            return BurnwillowAdapter(seed=seed)
        except ImportError:
            pass

    if sid == "burnwillow_zone1":
        try:
            from codex.games.burnwillow.zone1 import TangleAdapter
            return TangleAdapter(seed=seed)
        except ImportError:
            pass

    # All other systems use GenericAdapter
    if MAP_ENGINE_AVAILABLE:
        return GenericAdapter(seed=seed)
    return None


# =========================================================================
# MAP GENERATION (WO-V10.0 — Path A: BSP)
# =========================================================================

def generate_map_from_context(context: dict) -> dict:
    """Generate a map from a location description context using BSP.

    Args:
        context: Dict with keys:
            - ``location_name``: Name of the location
            - ``system_id``: Game system ("burnwillow", "dnd5e", etc.)
            - ``seed``: Optional RNG seed
            - ``depth``: Optional BSP depth (default 4)
            - ``width``, ``height``: Optional grid dimensions

    Returns:
        Dict with ``status``, ``total_rooms``, ``output_path``, ``graph``, ``rooms``.
    """
    system_id = context.get("system_id", "unknown")
    location = context.get("location_name", "unnamed")
    seed = context.get("seed")
    depth = context.get("depth", 4)
    width = context.get("width", 50)
    height = context.get("height", 50)

    # Ensure output directory exists
    output_dir = VAULT_MAPS_DIR / system_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if not MAP_ENGINE_AVAILABLE or CodexMapEngine is None:
        return {
            "status": "error",
            "message": "Map engine not available.",
            "output_dir": str(output_dir),
        }

    adapter = _get_adapter(system_id, seed=seed)
    if adapter is None:
        return {
            "status": "error",
            "message": f"No adapter available for system '{system_id}'.",
            "output_dir": str(output_dir),
        }

    # Generate geometry
    map_engine = CodexMapEngine(seed=seed)
    graph = map_engine.generate(
        width=width, height=height,
        min_room_size=5, max_depth=depth,
        system_id=system_id,
    )

    # Populate with content
    injector = ContentInjector(adapter)
    populated_rooms = injector.populate_all(graph)

    # Serialize rooms
    rooms = []
    for room_id, pop_room in populated_rooms.items():
        room_dict = {
            "id": pop_room.geometry.id,
            "type": pop_room.geometry.room_type.value,
            "tier": pop_room.geometry.tier,
            "position": (pop_room.geometry.x, pop_room.geometry.y),
            "size": (pop_room.geometry.width, pop_room.geometry.height),
            "connections": pop_room.geometry.connections,
        }
        if isinstance(pop_room.content, dict):
            room_dict.update(pop_room.content)
        rooms.append(room_dict)

    # Save to disk
    output_path = output_dir / f"{location.replace(' ', '_')}_{graph.seed}.json"
    save_data = {
        "location": location,
        "system_id": system_id,
        "seed": graph.seed,
        "total_rooms": len(rooms),
        "rooms": rooms,
    }
    try:
        with open(output_path, "w") as f:
            json.dump(save_data, f, indent=2)
    except Exception:
        output_path = None

    return {
        "status": "complete",
        "total_rooms": len(rooms),
        "output_path": str(output_path) if output_path else None,
        "graph": graph,
        "rooms": rooms,
    }


def list_maps(system_id: Optional[str] = None) -> Dict[str, list]:
    """List available map files grouped by system.

    Scans ``vault_maps/`` for image files (png, jpg, svg) and text
    map descriptions.
    """
    _IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".txt", ".json"}
    result: Dict[str, list] = {}

    if not VAULT_MAPS_DIR.exists():
        return result

    def _scan_dir(path: Path, sid: str):
        files = []
        for f in sorted(path.rglob("*")):
            if f.is_file() and f.suffix.lower() in _IMAGE_SUFFIXES:
                files.append(str(f.relative_to(VAULT_MAPS_DIR)))
        if files:
            result[sid] = files

    if system_id:
        target = VAULT_MAPS_DIR / system_id
        if target.is_dir():
            _scan_dir(target, system_id)
        return result

    for child in sorted(VAULT_MAPS_DIR.iterdir()):
        if child.is_dir() and child.name != "seeds":
            _scan_dir(child, child.name)

    return result

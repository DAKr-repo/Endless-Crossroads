#!/usr/bin/env python3
"""
codex/spatial/settlement_adapter.py - Settlement Content Adapter
================================================================

Implements RulesetAdapter for settlement maps (towns, villages, camps).

Settlements are safe zones — no enemies, no loot drops. Each room contains
NPCs with dialogue and a list of available services (mechanical interaction
hooks for the game layer).

Content priority:
    1. Blueprint ``content_hints`` on the RoomNode (hand-authored overrides)
    2. DEFAULT_NPCS / DEFAULT_SERVICES lookup by room type
    3. Generic fallback for unknown room types

Designed for use with ZoneLoader + ContentInjector:
    loader  = ZoneLoader(base_path)
    graph   = loader.load_zone(entry)            # DungeonGraph
    adapter = SettlementAdapter(content_hints)   # from blueprint or {}
    injector = ContentInjector(adapter)
    rooms   = injector.populate_all(graph)

Version: 1.0
"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

from codex.spatial.map_engine import PopulatedRoom, RoomNode, RoomType, RulesetAdapter

logger = logging.getLogger(__name__)


# =============================================================================
# DEFAULT CONTENT TABLES
# =============================================================================

DEFAULT_NPCS: Dict[str, List[Dict[str, str]]] = {
    "tavern": [
        {
            "name": "Barkeep",
            "role": "innkeeper",
            "dialogue": "Welcome, traveler. Ale or mead?",
        }
    ],
    "forge": [
        {
            "name": "Smith",
            "role": "blacksmith",
            "dialogue": "Need something repaired?",
        }
    ],
    "market": [
        {
            "name": "Merchant",
            "role": "trader",
            "dialogue": "Fine wares for fine folk.",
        }
    ],
    "temple": [
        {
            "name": "Priest",
            "role": "healer",
            "dialogue": "The light watches over you.",
        }
    ],
    "barracks": [
        {
            "name": "Captain",
            "role": "guard_captain",
            "dialogue": "Any trouble to report?",
        }
    ],
    "library": [
        {
            "name": "Sage",
            "role": "scholar",
            "dialogue": "Knowledge is the true treasure.",
        }
    ],
    "town_gate": [
        {
            "name": "Guard",
            "role": "gate_guard",
            "dialogue": "Papers, please. The wilds are dangerous.",
        }
    ],
    "town_square": [
        {
            "name": "Town Crier",
            "role": "announcer",
            "dialogue": "Hear ye, hear ye!",
        }
    ],
    "residence": [
        {
            "name": "Villager",
            "role": "commoner",
            "dialogue": "Good day to you.",
        }
    ],
}

DEFAULT_SERVICES: Dict[str, List[str]] = {
    "tavern":      ["drink", "rest", "rumor"],
    "forge":       ["repair", "buy_weapon", "buy_armor"],
    "market":      ["buy", "sell", "appraise"],
    "temple":      ["heal", "cure", "bless"],
    "barracks":    ["quest_board", "bounty", "train"],
    "library":     ["research", "identify", "lore"],
    "town_gate":   ["exit_settlement"],
    "town_square": ["map", "directions"],
    "residence":   [],
}

_DEFAULT_DESCRIPTIONS: Dict[str, str] = {
    "tavern":      "Warmth radiates from a crackling hearth. The smell of roasted meat fills the air.",
    "forge":       "The rhythmic clang of hammer on anvil echoes from the back room. Sparks drift like fireflies.",
    "market":      "Colorful stalls crowd the lane, vendors calling out prices over the din of commerce.",
    "temple":      "Candles flicker in neat rows before a modest altar. The air carries the scent of incense.",
    "barracks":    "Rows of bunks, polished armor on hooks, and a cork board dense with bounty notices.",
    "library":     "Shelves groan under the weight of leather-bound tomes. Dust motes drift in shafts of light.",
    "town_gate":   "Heavy oak gates stand open. A guard post flanks each side, watching the road beyond.",
    "town_square": "The beating heart of the settlement. A well stands at the center; locals pass by with purpose.",
    "residence":   "A modest home, well-kept but unremarkable. Curtains twitch as you approach.",
    # Dungeon room types that might appear in a settlement context
    "start":       "The entrance to the settlement, worn smooth by countless feet.",
    "normal":      "A quiet corner of the settlement. Little of note, but a place to rest.",
    "treasure":    "A locked storeroom — someone values what is kept here.",
    "boss":        "The seat of local power. The air is heavy with authority.",
    "secret":      "A hidden alcove, known only to a few.",
    "return_gate": "A side passage back the way you came.",
}


# =============================================================================
# SETTLEMENT ADAPTER
# =============================================================================

class SettlementAdapter(RulesetAdapter):
    """Populates settlement rooms with NPCs, services, and flavour text.

    Safe zones only: ``enemies`` and ``loot`` are always empty lists.

    Content resolution order:
        1. ``self.content_hints[str(room.id)]``   (blueprint overrides)
        2. DEFAULT_NPCS / DEFAULT_SERVICES keyed by room type value
        3. Generic empty / placeholder fallback

    Attributes:
        content_hints: Per-room override dicts keyed by string room ID.
                       Usually populated from ZoneLoader.load_blueprint().
    """

    def __init__(self, content_hints: Optional[Dict[str, Any]] = None) -> None:
        """Initialise the adapter.

        Args:
            content_hints: Per-room override dicts keyed by string room ID.
                           Keys within each room dict:
                               npcs        -- list of NPC dicts
                               services    -- list of service name strings
                               description -- room description string
                               inventory   -- list of available item dicts
        """
        self.content_hints: Dict[str, Any] = content_hints or {}

    # ------------------------------------------------------------------
    # RulesetAdapter interface
    # ------------------------------------------------------------------

    def populate_room(self, room: RoomNode, graph: Any = None, rng: Any = None) -> PopulatedRoom:  # type: ignore[override]
        """Populate a settlement room.

        Args:
            room:  Geometry node to populate.
            graph: DungeonGraph (unused; kept for adapter compatibility).
            rng:   Random source (unused; settlements are deterministic).

        Returns:
            PopulatedRoom with ``content`` dict containing:
                description  -- flavour text string
                npcs         -- list of NPC dicts
                services     -- list of service name strings
                inventory    -- list of item dicts (may be empty)
                enemies      -- always []
                loot         -- always []
        """
        # Resolve room type string
        if hasattr(room.room_type, "value"):
            room_type_str = room.room_type.value
        else:
            room_type_str = str(room.room_type)

        # Gather blueprint hints: ZoneEntry.content_hints from room or adapter
        hints: dict = {}

        # Priority 1: hints attached directly to the RoomNode (from blueprint JSON)
        if room.content_hints:
            hints = dict(room.content_hints)

        # Priority 2: adapter-level hints keyed by str(room.id)
        adapter_hints = self.content_hints.get(str(room.id), {})
        for key, value in adapter_hints.items():
            if key not in hints:
                hints[key] = value

        # Resolve final values
        npcs: List[dict] = hints.get(
            "npcs", list(DEFAULT_NPCS.get(room_type_str, []))
        )
        services: List[str] = hints.get(
            "services", list(DEFAULT_SERVICES.get(room_type_str, []))
        )
        description: str = hints.get(
            "description", self._default_description(room_type_str)
        )
        inventory: List[dict] = hints.get("inventory", [])

        content: dict = {
            "description": description,
            "npcs":        npcs,
            "services":    services,
            "inventory":   inventory,
            "enemies":     [],   # Settlements are safe zones
            "loot":        [],
        }

        return PopulatedRoom(geometry=room, content=content)

    def get_enemy_pool(self, tier: int) -> List[str]:
        """Settlements have no enemy pool.

        Returns:
            Always an empty list.
        """
        return []

    def get_loot_pool(self, tier: int) -> List[str]:
        """Settlements have no procedural loot pool.

        Returns:
            Always an empty list.
        """
        return []

    # ------------------------------------------------------------------
    # Description helpers
    # ------------------------------------------------------------------

    def _default_description(self, room_type: str) -> str:
        """Generate a default flavour description for a settlement room type.

        Args:
            room_type: RoomType value string (e.g. "tavern", "forge").

        Returns:
            Human-readable description string. Falls back to a generic phrase
            for unrecognised room types.
        """
        return _DEFAULT_DESCRIPTIONS.get(
            room_type,
            "A quiet space within the settlement. Nothing unusual stands out.",
        )

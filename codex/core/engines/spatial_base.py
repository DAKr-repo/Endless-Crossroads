"""
codex/core/engines/spatial_base.py — Spatial Dungeon Engine Base Class
=======================================================================
Extracts the common BSP dungeon navigation patterns shared by DnD5eEngine
and CosmereEngine (STC).  Subclasses provide system-specific hooks:

    _create_character(name, **kwargs)  — factory for character dataclass
    _get_adapter(**kwargs)             — RulesetAdapter for ContentInjector
    _roll_attack(char, target, **kw)   — system combat roll
    _get_loot_table()                  — list[dict] for treasure generation

Usage:
    class MyEngine(SpatialEngineBase):
        system_id = "myid"
        system_family = "MYID"
        display_name = "My System"

        def _create_character(self, name, **kwargs):
            return MyCharacter(name=name, **kwargs)

        def _get_adapter(self, **kwargs):
            return MyAdapter(**kwargs)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from codex.core.services.narrative_loom import NarrativeLoomMixin


class SpatialEngineBase(NarrativeLoomMixin):
    """Base class for spatial dungeon-crawl engines.

    Provides: generate_dungeon(), load_dungeon_graph(), move_to_room(),
    move_player_grid(), get_current_room(), get_current_room_dict(),
    get_cardinal_exits(), get_connected_rooms(), load_module(),
    advance_zone(), save_state(), load_state().

    Subclasses must override: _create_character(), _get_adapter().
    Subclasses may override: _roll_attack(), _get_loot_table(),
    get_mood_context(), get_status().
    """

    # --- Subclasses must set these class attributes -----------------------
    system_id: str = "base_spatial"
    system_family: str = "BASE"
    display_name: str = "Spatial Engine"

    def __init__(self) -> None:
        self.character: Optional[Any] = None
        self.party: List[Any] = []
        self.setting_id: str = ""
        self.dungeon_graph: Optional[Any] = None
        self.populated_rooms: Dict[int, Any] = {}
        self.current_room_id: Optional[int] = None
        self.player_pos: Optional[tuple] = None
        self.visited_rooms: set = set()
        self.zone_manager: Optional[Any] = None
        self._module_manifest_path: Optional[str] = None
        self._init_loom()
        # Optional DeltaTracker for narrative storytelling (WO-V56.0)
        try:
            from codex.core.services.narrative_frame import DeltaTracker
            self.delta_tracker: Optional[Any] = DeltaTracker()
        except ImportError:
            self.delta_tracker = None

    # =====================================================================
    # Abstract hooks — subclasses must implement
    # =====================================================================

    def _create_character(self, name: str, **kwargs) -> Any:
        """Factory for the system's character dataclass.

        Args:
            name: Character's name.
            **kwargs: System-specific keyword arguments.

        Returns:
            A new character instance.

        Raises:
            NotImplementedError: Subclasses must implement this.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _create_character()"
        )

    def _get_adapter(self, **kwargs) -> Any:
        """Return a RulesetAdapter for ContentInjector.

        Args:
            **kwargs: Adapter-specific keyword arguments (e.g. seed, party_size).

        Returns:
            A RulesetAdapter instance.

        Raises:
            NotImplementedError: Subclasses must implement this.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _get_adapter()"
        )

    # =====================================================================
    # Optional hooks — subclasses may override
    # =====================================================================

    def _roll_attack(self, attacker: Any, target: Any, **kwargs) -> Dict[str, Any]:
        """Execute a system-specific attack roll.

        Default implementation returns a placeholder result.

        Args:
            attacker: The attacking character/entity.
            target: The defending character/entity.
            **kwargs: Additional roll modifiers.

        Returns:
            Dict with at minimum 'hit' (bool) and 'damage' (int) keys.
        """
        return {"hit": True, "damage": 0, "note": "Override _roll_attack()"}

    def _get_loot_table(self) -> List[dict]:
        """Return the system's loot table as a list of item dicts.

        Default returns an empty list — no random loot.

        Returns:
            List of item dicts with at least 'name' key.
        """
        return []

    # =====================================================================
    # Character management (common pattern)
    # =====================================================================

    def create_character(self, name: str, **kwargs) -> Any:
        """Create a character and set as party lead.

        Delegates to _create_character() for system-specific construction.
        Pops 'setting_id' before forwarding kwargs.

        Args:
            name: Character's name.
            **kwargs: System-specific keyword arguments.

        Returns:
            Newly created character instance.
        """
        setting_id = kwargs.pop("setting_id", self.setting_id)
        if setting_id:
            self.setting_id = setting_id
        char = self._create_character(name, setting_id=setting_id, **kwargs)
        self.character = char
        if not self.party:
            self.party = [char]
        else:
            self.party.append(char)
        return char

    def add_to_party(self, char: Any) -> None:
        """Add an existing character to the active party.

        Args:
            char: The character instance to add.
        """
        self.party.append(char)

    def remove_from_party(self, char: Any) -> None:
        """Remove a character from the active party.

        Args:
            char: The character instance to remove.
        """
        if char in self.party:
            self.party.remove(char)
        if self.character is char:
            alive = self.get_active_party()
            self.character = alive[0] if alive else None

    def get_active_party(self) -> List[Any]:
        """Return all living party members.

        Returns:
            List of characters where is_alive() is True.
        """
        return [c for c in self.party if getattr(c, "is_alive", lambda: True)()]

    # =====================================================================
    # Status
    # =====================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return current game state summary for Butler/UI.

        Returns:
            Dict with system, party_size, lead, room.
        """
        lead = self.party[0] if self.party else None
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "room": self.current_room_id,
        }

    def get_mood_context(self) -> Dict[str, Any]:
        """Return current mechanical state as narrative mood modifiers.

        Default implementation returns a neutral context.  Subclasses
        should override to incorporate system-specific stats (HP%, stress).

        Returns:
            Dict with tension, tone_words, party_condition, system_specific.
        """
        return {
            "tension": 0.0,
            "tone_words": [],
            "party_condition": "healthy",
            "system_specific": {},
        }

    # =====================================================================
    # Dungeon generation
    # =====================================================================

    def generate_dungeon(
        self,
        depth: int = 4,
        seed: Optional[int] = None,
        zone: str = "",
    ) -> dict:
        """Generate a BSP dungeon using CodexMapEngine + adapter.

        Args:
            depth: Dungeon depth (controls room count via BSP splits).
            seed: RNG seed for reproducible generation.
            zone: Optional zone identifier passed to the adapter.

        Returns:
            Dict with 'seed', 'total_rooms', 'start_room'.
        """
        from codex.spatial.map_engine import CodexMapEngine, ContentInjector, PopulatedRoom
        map_engine = CodexMapEngine(seed=seed)
        self.dungeon_graph = map_engine.generate(
            width=50, height=50, min_room_size=5, max_depth=depth,
            system_id=self.system_id,
        )
        adapter = self._get_adapter(seed=seed, party_size=len(self.party))
        injector = ContentInjector(adapter)
        self.populated_rooms = injector.populate_all(self.dungeon_graph)
        self._apply_content_hints(PopulatedRoom)

        self.current_room_id = self.dungeon_graph.start_room_id
        self.visited_rooms.add(self.current_room_id)
        start_room = self.dungeon_graph.rooms.get(self.current_room_id)
        if start_room:
            self.player_pos = (
                start_room.x + start_room.width // 2,
                start_room.y + start_room.height // 2,
            )
        self._add_shard(
            f"{self.display_name} dungeon generated: "
            f"{len(self.dungeon_graph.rooms)} rooms, "
            f"depth {depth}, seed {self.dungeon_graph.seed}",
            "MASTER",
        )
        return {
            "seed": self.dungeon_graph.seed,
            "total_rooms": len(self.dungeon_graph.rooms),
            "start_room": self.current_room_id,
        }

    def load_dungeon_graph(self, graph: Any) -> None:
        """Load a pre-built DungeonGraph from ZoneManager.

        Populates rooms via _get_adapter() + ContentInjector, applies
        content_hints, and resets navigation state.

        Args:
            graph: A DungeonGraph instance from ZoneManager.
        """
        from codex.spatial.map_engine import ContentInjector, PopulatedRoom
        self.dungeon_graph = graph
        adapter = self._get_adapter(party_size=len(self.party))
        injector = ContentInjector(adapter)
        self.populated_rooms = injector.populate_all(graph)
        self._apply_content_hints(PopulatedRoom)
        self.current_room_id = graph.start_room_id
        self.visited_rooms = {self.current_room_id}
        start_room = graph.rooms.get(self.current_room_id)
        if start_room:
            self.player_pos = (
                start_room.x + start_room.width // 2,
                start_room.y + start_room.height // 2,
            )

    def _apply_content_hints(self, PopulatedRoom: Any) -> None:
        """Override populated rooms with hand-authored content_hints.

        Iterates dungeon graph rooms with non-empty content_hints,
        parses them via SceneData, and replaces the random PopulatedRoom.

        Args:
            PopulatedRoom: The PopulatedRoom class (passed to avoid re-import).
        """
        if not self.dungeon_graph:
            return
        try:
            from codex.spatial.scene_data import SceneData
        except ImportError:
            return

        for room_id, room_node in self.dungeon_graph.rooms.items():
            hints = getattr(room_node, "content_hints", None)
            if not hints:
                continue
            scene = SceneData.from_content_hints(hints)
            content: Dict[str, Any] = {}
            if scene.description:
                content["description"] = scene.description
            if scene.read_aloud:
                content["read_aloud"] = scene.read_aloud
            content["enemies"] = [
                {"name": e.name, "hp": e.hp, "max_hp": e.hp,
                 "attack": e.attack, "defense": e.ac, "tier": room_node.tier,
                 "notes": e.notes}
                for e in scene.enemies for _ in range(e.count)
            ]
            content["loot"] = [
                {"name": l.name, "tier": room_node.tier,
                 "value": l.value, "description": l.description}
                for l in scene.loot
            ]
            if scene.npcs:
                content["npcs"] = [n.to_dict() for n in scene.npcs]
            if scene.investigation_dc:
                content["investigation_dc"] = scene.investigation_dc
                content["investigation_success"] = scene.investigation_success
            if scene.perception_dc:
                content["perception_dc"] = scene.perception_dc
                content["perception_success"] = scene.perception_success
            if scene.services:
                content["services"] = scene.services
            if scene.event_triggers:
                content["event_triggers"] = scene.event_triggers
            content["hazards"] = []
            self.populated_rooms[room_id] = PopulatedRoom(
                geometry=room_node, content=content
            )

    # =====================================================================
    # Navigation API
    # =====================================================================

    def get_current_room(self) -> Optional[Any]:
        """Return the current RoomNode or None.

        Returns:
            The RoomNode for current_room_id, or None.
        """
        if self.dungeon_graph and self.current_room_id is not None:
            return self.dungeon_graph.rooms.get(self.current_room_id)
        return None

    def get_connected_rooms(self) -> List[int]:
        """Return list of room IDs connected to current room.

        Returns:
            List of connected room IDs.
        """
        room = self.get_current_room()
        return room.connections if room else []

    def get_cardinal_exits(self) -> List[Dict[str, Any]]:
        """Return list of {direction, id, type, tier} dicts for current room.

        Returns:
            List of exit dicts with 'direction', 'id', 'type', 'tier'.
        """
        room = self.get_current_room()
        if not room:
            return []
        exits = []
        for cid in room.connections:
            target = self.dungeon_graph.rooms.get(cid)
            if not target:
                continue
            dx = target.x - room.x
            dy = target.y - room.y
            if abs(dx) > abs(dy):
                direction = "east" if dx > 0 else "west"
            else:
                direction = "south" if dy > 0 else "north"
            exits.append({
                "direction": direction,
                "id": cid,
                "type": target.room_type.name if hasattr(target, "room_type") else "NORMAL",
                "tier": getattr(target, "tier", 1),
            })
        return exits

    def get_current_room_dict(self) -> Optional[Dict[str, Any]]:
        """Get current room as a dict for callers expecting dict interface.

        Returns:
            Dict with id, type, tier, description, enemies, loot, hazards,
            visited — or None if no dungeon is loaded.
        """
        if not self.dungeon_graph or self.current_room_id is None:
            return None
        pop_room = self.populated_rooms.get(self.current_room_id)
        if not pop_room:
            return None
        return {
            "id": pop_room.geometry.id,
            "type": (
                pop_room.geometry.room_type.value
                if hasattr(pop_room.geometry.room_type, "value")
                else str(pop_room.geometry.room_type)
            ),
            "tier": pop_room.geometry.tier,
            "description": pop_room.content.get("description", ""),
            "enemies": pop_room.content.get("enemies", []),
            "loot": pop_room.content.get("loot", []),
            "hazards": pop_room.content.get("hazards", []),
            "visited": self.current_room_id in self.visited_rooms,
        }

    def move_to_room(self, room_id: int) -> bool:
        """Move to a connected room by ID.

        Args:
            room_id: The target room's integer ID.

        Returns:
            True on success, False if room is not connected.
        """
        if room_id not in self.get_connected_rooms():
            return False
        self.current_room_id = room_id
        self.visited_rooms.add(room_id)
        self._add_shard(f"Party moved to room {room_id}", "CHRONICLE")
        target = self.dungeon_graph.rooms.get(room_id)
        if target:
            self.player_pos = (
                target.x + target.width // 2,
                target.y + target.height // 2,
            )
        if self.delta_tracker is not None:
            room_data = self.get_current_room_dict()
            if room_data:
                self.delta_tracker.record_visit(room_id, room_data)
        return True

    def move_player_grid(self, direction: str) -> bool:
        """Move one step in a cardinal direction.

        Args:
            direction: One of 'north', 'south', 'east', 'west'.

        Returns:
            True on success, False if no exit in that direction.
        """
        for ex in self.get_cardinal_exits():
            if ex["direction"] == direction:
                return self.move_to_room(ex["id"])
        return False

    # =====================================================================
    # Module / zone progression
    # =====================================================================

    def load_module(self, manifest_path: str) -> str:
        """Load a ModuleManifest and initialise the ZoneManager.

        Args:
            manifest_path: Path to the module JSON file.

        Returns:
            Human-readable status string.
        """
        import os
        from codex.spatial.module_manifest import ModuleManifest
        from codex.spatial.zone_manager import ZoneManager

        manifest = ModuleManifest.load(manifest_path)
        base_path = os.path.dirname(os.path.abspath(manifest_path))
        self._module_manifest_path = os.path.abspath(manifest_path)
        self.zone_manager = ZoneManager(manifest=manifest, base_path=base_path)

        pending = getattr(self, "_pending_zone_state", None)
        if pending:
            self.zone_manager.chapter_idx = pending.get("chapter_idx", 0)
            self.zone_manager.zone_idx = pending.get("zone_idx", 0)
            self.zone_manager.module_complete = pending.get("module_complete", False)
            if pending.get("villain_path"):
                self.zone_manager.set_villain_path(pending["villain_path"])
            self._pending_zone_state = None

        graph = self.zone_manager.load_current_zone()
        if graph:
            self.load_dungeon_graph(graph)
        entry = self.zone_manager.current_zone_entry
        zone_id = entry.zone_id if entry else "none"
        rooms = len(graph.rooms) if graph and hasattr(graph, "rooms") else 0
        self._add_shard(
            f"{self.display_name} module '{manifest.display_name}' loaded; "
            f"zone '{zone_id}' ({rooms} rooms)",
            "MASTER",
        )
        return (
            f"Module '{manifest.display_name}' loaded. "
            f"Current zone: '{zone_id}' | {self.zone_manager.zone_progress}"
        )

    def advance_zone(self) -> str:
        """Advance the ZoneManager to the next zone.

        Returns:
            Human-readable status string.
        """
        if self.zone_manager is None:
            return "No module loaded. Call load_module() first."
        entry = self.zone_manager.advance()
        if entry is None:
            return f"Module '{self.zone_manager.module_name}' is complete!"
        graph = self.zone_manager.load_current_zone()
        if graph:
            self.load_dungeon_graph(graph)
        rooms = len(graph.rooms) if graph and hasattr(graph, "rooms") else 0
        zone_id = entry.zone_id if entry else "none"
        self._add_shard(
            f"{self.display_name} advanced to zone '{zone_id}' ({rooms} rooms)",
            "CHRONICLE",
        )
        return (
            f"Advanced to zone '{zone_id}' | {self.zone_manager.zone_progress}"
        )

    # =====================================================================
    # Save / Load
    # =====================================================================

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state to JSON-safe dict.

        Returns:
            Dict containing all common spatial engine state.
        """
        return {
            "system_id": self.system_id,
            "setting_id": self.setting_id,
            "party": [c.to_dict() for c in self.party],
            "current_room_id": self.current_room_id,
            "player_pos": list(self.player_pos) if self.player_pos else None,
            "visited_rooms": list(self.visited_rooms),
            "zone_manager": self.zone_manager.to_dict() if self.zone_manager else None,
            "module_manifest_path": self._module_manifest_path,
            "delta_tracker": (
                self.delta_tracker.to_dict() if self.delta_tracker else None
            ),
        }

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict.

        Subclasses that add extra state should call super().load_state(data)
        then restore their own fields.

        Args:
            data: Dict from a previous save_state() call.
        """
        self.setting_id = data.get("setting_id", "")
        char_list = data.get("party", [])
        self.party = [self._create_character(**d) for d in char_list]
        self.character = self.party[0] if self.party else None
        self.current_room_id = data.get("current_room_id")
        pos = data.get("player_pos")
        self.player_pos = tuple(pos) if pos else None
        self.visited_rooms = set(data.get("visited_rooms", []))
        self._module_manifest_path = data.get("module_manifest_path")

        zm_data = data.get("zone_manager")
        if zm_data:
            if self.zone_manager is not None:
                self.zone_manager.chapter_idx = zm_data.get("chapter_idx", 0)
                self.zone_manager.zone_idx = zm_data.get("zone_idx", 0)
                self.zone_manager.module_complete = zm_data.get("module_complete", False)
            else:
                self._pending_zone_state: Dict[str, Any] = zm_data

        dt_data = data.get("delta_tracker")
        if dt_data:
            try:
                from codex.core.services.narrative_frame import DeltaTracker
                self.delta_tracker = DeltaTracker.from_dict(dt_data)
            except (ImportError, Exception):
                pass

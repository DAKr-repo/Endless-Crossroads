"""
Cosmere Roleplaying Game (STC) — Game Engine
==============================================

Provides the core engine for Cosmere RPG (Stormlight) campaigns.
Uses three core attributes (Strength, Speed, Intellect) and
the Radiant Order / Surge system from Roshar.

Integrates with:
  - codex/spatial/map_engine.py via CosmereAdapter (RulesetAdapter)
  - codex/forge/char_wizard.py via vault/stc/creation_rules.json
  - codex/core/services/capacity_manager.py for encumbrance
  - codex/core/dice.py for shared dice utilities

Activated when a Cosmere RPG campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random

from codex.core.services.narrative_loom import NarrativeLoomMixin

# WO-Phase3: Depth Parity — exported subsystem classes for bridge/bot usage
# (imported lazily inside methods; referenced at module level for convenience)



# =========================================================================
# RADIANT ORDERS — Surge mapping
# =========================================================================

RADIANT_ORDERS: Dict[str, Dict[str, Any]] = {
    "windrunner":   {"surges": ["Adhesion", "Gravitation"], "ideal": "I will protect"},
    "skybreaker":   {"surges": ["Gravitation", "Division"], "ideal": "I will seek justice"},
    "dustbringer":  {"surges": ["Division", "Abrasion"], "ideal": "I will seek self-mastery"},
    "edgedancer":   {"surges": ["Abrasion", "Progression"], "ideal": "I will remember"},
    "truthwatcher": {"surges": ["Progression", "Illumination"], "ideal": "I will seek truth"},
    "lightweaver":  {"surges": ["Illumination", "Transformation"], "ideal": "I will speak my truth"},
    "elsecaller":   {"surges": ["Transformation", "Transportation"], "ideal": "I will reach my potential"},
    "willshaper":   {"surges": ["Transportation", "Cohesion"], "ideal": "I will seek freedom"},
    "stoneward":    {"surges": ["Cohesion", "Tension"], "ideal": "I will be there when needed"},
    "bondsmith":    {"surges": ["Tension", "Adhesion"], "ideal": "I will unite"},
}


# =========================================================================
# CHARACTER
# =========================================================================

@dataclass
class CosmereCharacter:
    """A Cosmere RPG player character."""
    name: str
    heritage: str = ""        # Alethi, Veden, Shin, etc.
    order: str = ""           # Radiant Order (path)
    setting_id: str = ""      # Sub-setting: "roshar", etc.

    # Three core attributes
    strength: int = 10
    speed: int = 10
    intellect: int = 10

    # Derived
    max_hp: int = 0
    current_hp: int = 0
    defense: int = 10
    focus: int = 0            # Stormlight / Focus Points
    max_focus: int = 0        # Focus cap (increases with Ideals)
    inventory: List[dict] = field(default_factory=list)
    ideal_level: int = 1      # WO-V34.0: Radiant Ideal progression (1-5)

    def __post_init__(self):
        if self.max_hp == 0:
            self.max_hp = 10 + (self.strength - 10) // 2
            self.current_hp = self.max_hp
        self.defense = 10 + (self.speed - 10) // 2
        self.focus = max(0, (self.intellect - 10) // 2 + 2)
        if self.max_focus == 0:
            self.max_focus = self.focus

    def modifier(self, attr: str) -> int:
        score = getattr(self, attr, 10)
        return (score - 10) // 2

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def take_damage(self, amount: int) -> int:
        actual = max(0, amount)
        self.current_hp = max(0, self.current_hp - actual)
        return actual

    def heal(self, amount: int) -> int:
        old = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old

    def check_encumbrance(self):
        from codex.core.services.capacity_manager import check_capacity, CapacityMode
        limit = 8 + (self.strength - 10) // 2  # Cosmere slot system
        current = sum(item.get("slots", 1) for item in self.inventory)
        return check_capacity(CapacityMode.SLOTS, limit, current)

    def get_surges(self) -> List[str]:
        order_data = RADIANT_ORDERS.get(self.order.lower(), {})
        return order_data.get("surges", [])

    def get_ideal(self) -> str:
        order_data = RADIANT_ORDERS.get(self.order.lower(), {})
        return order_data.get("ideal", "")

    def to_dict(self) -> dict:
        return {
            "name": self.name, "heritage": self.heritage, "order": self.order,
            "setting_id": self.setting_id,
            "strength": self.strength, "speed": self.speed,
            "intellect": self.intellect,
            "max_hp": self.max_hp, "current_hp": self.current_hp,
            "defense": self.defense, "focus": self.focus,
            "max_focus": self.max_focus,
            "ideal_level": self.ideal_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CosmereCharacter":
        c = cls(
            name=data["name"], heritage=data.get("heritage", ""),
            order=data.get("order", ""),
            strength=data.get("strength", 10),
            speed=data.get("speed", 10),
            intellect=data.get("intellect", 10),
        )
        c.setting_id = data.get("setting_id", "")
        c.max_hp = data.get("max_hp", c.max_hp)
        c.current_hp = data.get("current_hp", c.current_hp)
        c.defense = data.get("defense", c.defense)
        c.focus = data.get("focus", c.focus)
        c.max_focus = data.get("max_focus", c.focus)
        c.ideal_level = data.get("ideal_level", 1)
        return c


# =========================================================================
# ENGINE
# =========================================================================

class CosmereEngine(NarrativeLoomMixin):
    """
    Core engine for Cosmere RPG (Stormlight) campaigns.

    Manages party, Radiant Orders, and dungeon state.
    Compatible with the Universal Map Engine via CosmereAdapter.
    """

    system_id = "stc"
    system_family = "STC"
    display_name = "Cosmere Roleplaying Game"

    def __init__(self):
        self.character: Optional[CosmereCharacter] = None
        self.party: List[CosmereCharacter] = []
        self.setting_id: str = ""
        self.dungeon_graph: Optional[Any] = None
        self.populated_rooms: Dict[int, Any] = {}
        self.current_room_id: Optional[int] = None
        self.player_pos: Optional[tuple] = None
        self.visited_rooms: set = set()
        self._init_loom()
        # Zone progression (module-based campaigns)
        self.zone_manager: Optional[Any] = None
        self._module_manifest_path: Optional[str] = None
        # WO-Phase3: Depth Parity — lazy-initialised subsystems
        self._surge_managers: Dict[str, Any] = {}     # char_name -> SurgeManager
        self._combat_resolver: Optional[Any] = None   # CosmereCombatResolver
        self._ideal_trackers: Dict[str, Any] = {}     # char_name -> IdealProgression
        self._storm_tracker: Optional[Any] = None     # StormTracker
        # WO-V56.0: DeltaTracker for narrative storytelling
        try:
            from codex.core.services.narrative_frame import DeltaTracker
            self.delta_tracker = DeltaTracker()
        except ImportError:
            self.delta_tracker = None

    # ─── WO-Phase3: Subsystem accessors ───────────────────────────────

    def _get_surge_manager(self, char: CosmereCharacter) -> Any:
        """Return (or create) the SurgeManager for a character."""
        if char.name not in self._surge_managers:
            from codex.games.stc.surgebinding import SurgeManager
            self._surge_managers[char.name] = SurgeManager(
                character_name=char.name,
                order=char.order,
                ideal_level=char.ideal_level,
            )
        return self._surge_managers[char.name]

    def _get_combat_resolver(self) -> Any:
        """Lazily initialise and return the CosmereCombatResolver."""
        if self._combat_resolver is None:
            from codex.games.stc.combat import CosmereCombatResolver
            self._combat_resolver = CosmereCombatResolver()
        return self._combat_resolver

    def _get_ideal_tracker(self, char: CosmereCharacter) -> Any:
        """Return (or create) the IdealProgression tracker for a character."""
        if char.name not in self._ideal_trackers:
            from codex.games.stc.ideals import IdealProgression
            self._ideal_trackers[char.name] = IdealProgression(
                character_name=char.name,
                order=char.order,
                current_ideal=char.ideal_level,
            )
        return self._ideal_trackers[char.name]

    def _get_storm_tracker(self) -> Any:
        """Lazily initialise and return the StormTracker."""
        if self._storm_tracker is None:
            from codex.games.stc.surgebinding import StormTracker
            self._storm_tracker = StormTracker()
        return self._storm_tracker

    def create_character(self, name: str, **kwargs) -> CosmereCharacter:
        setting_id = kwargs.pop("setting_id", self.setting_id)
        char = CosmereCharacter(name=name, setting_id=setting_id, **kwargs)
        self.character = char
        self.party = [char]
        if not self.setting_id and setting_id:
            self.setting_id = setting_id
        return char

    def add_to_party(self, char: CosmereCharacter) -> None:
        self.party.append(char)

    def remove_from_party(self, char: CosmereCharacter) -> None:
        if char in self.party:
            self.party.remove(char)
        if self.character is char:
            alive = self.get_active_party()
            self.character = alive[0] if alive else None

    def get_active_party(self) -> List[CosmereCharacter]:
        return [c for c in self.party if c.is_alive()]

    def get_mood_context(self) -> dict:
        """Return current mechanical state as narrative mood modifiers (WO-V61.0)."""
        char = self.character
        hp_pct = char.current_hp / max(1, char.max_hp) if char else 1.0
        stormlight = getattr(char, 'stormlight', 0) if char else 0
        max_stormlight = getattr(char, 'max_stormlight', 1) if char else 1
        sl_pct = stormlight / max(1, max_stormlight)
        tension = max(1.0 - hp_pct, 1.0 - sl_pct)
        words = []
        if sl_pct < 0.2:
            words.extend(["dimming", "fading", "drained"])
        if hp_pct < 0.25:
            condition = "critical"
        elif hp_pct < 0.5:
            condition = "battered"
        else:
            condition = "healthy"
        return {
            "tension": round(tension, 2),
            "tone_words": words,
            "party_condition": condition,
            "system_specific": {"stormlight_pct": round(sl_pct, 2)},
        }

    def get_status(self) -> Dict[str, Any]:
        lead = self.party[0] if self.party else None
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "lead_hp": f"{lead.current_hp}/{lead.max_hp}" if lead else None,
            "order": lead.order if lead else None,
            "room": self.current_room_id,
        }

    # ─── Setting-filtered reference data accessors ────────────────────

    def get_heritages(self) -> Dict[str, Dict[str, Any]]:
        from codex.forge.reference_data.stc_heritages import HERITAGES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(HERITAGES, self.setting_id)

    def get_orders(self) -> Dict[str, Dict[str, Any]]:
        from codex.forge.reference_data.stc_orders import ORDERS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(ORDERS, self.setting_id)

    def get_equipment(self, category: str = "weapons") -> Dict[str, Dict[str, Any]]:
        from codex.forge.reference_data import stc_equipment as eq
        from codex.forge.reference_data.setting_filter import filter_by_setting
        pools = {
            "weapons": eq.WEAPON_PROPERTIES, "shardblades": eq.SHARDBLADES,
            "shardplate": eq.SHARDPLATE, "fabrials": eq.FABRIALS,
            "spheres": eq.SPHERE_TYPES,
        }
        return filter_by_setting(pools.get(category, {}), self.setting_id)

    def roll_check(self, character=None, attribute="strength",
                   dc=None, focus_spend=0, **kwargs):
        from codex.core.dice import roll_dice
        char = character or self.character
        _, rolls, _ = roll_dice("1d20")
        raw = rolls[0]
        mod = char.modifier(attribute)
        actual_focus = min(focus_spend, char.focus)
        if actual_focus > 0:
            char.focus -= actual_focus
        total = raw + mod + actual_focus
        result = {"roll": raw, "modifier": mod, "focus_spent": actual_focus,
                  "total": total, "critical": raw == 20, "fumble": raw == 1}
        if dc is not None:
            result["dc"] = dc
            result["success"] = total >= dc or raw == 20
        return result

    def log_character_death(self, char, cause="Fell in the Shattered Plains", seed=None):
        from codex.core.services.graveyard import log_death
        return log_death({"name": char.name, "hp_max": char.max_hp,
            "heritage": char.heritage, "order": char.order,
            "cause": cause, "room_id": self.current_room_id},
            system_id="stc", seed=seed)

    def save_state(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "setting_id": self.setting_id,
            "party": [c.to_dict() for c in self.party],
            "current_room_id": self.current_room_id,
            "player_pos": list(self.player_pos) if self.player_pos else None,
            "visited_rooms": list(self.visited_rooms),
            # Zone progression state
            "zone_manager": self.zone_manager.to_dict() if self.zone_manager else None,
            "module_manifest_path": self._module_manifest_path,
            # WO-Phase3: Subsystem state
            "surge_managers": {
                name: m.to_dict() for name, m in self._surge_managers.items()
            },
            "ideal_trackers": {
                name: t.to_dict() for name, t in self._ideal_trackers.items()
            },
            "storm_tracker": self._storm_tracker.to_dict() if self._storm_tracker else None,
            # WO-V56.0: Delta tracker persistence
            "delta_tracker": self.delta_tracker.to_dict() if self.delta_tracker else None,
        }

    def load_state(self, data: Dict[str, Any]) -> None:
        self.setting_id = data.get("setting_id", "")
        self.party = [CosmereCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.current_room_id = data.get("current_room_id")
        pos = data.get("player_pos")
        self.player_pos = tuple(pos) if pos else None
        self.visited_rooms = set(data.get("visited_rooms", []))
        # WO-V57.0: Restore module manifest path
        self._module_manifest_path = data.get("module_manifest_path")
        # Zone progression: restore indices; manifest must be re-loaded separately
        zm_data = data.get("zone_manager")
        if zm_data:
            try:
                if self.zone_manager is not None:
                    self.zone_manager.chapter_idx = zm_data.get("chapter_idx", 0)
                    self.zone_manager.zone_idx = zm_data.get("zone_idx", 0)
                    self.zone_manager.module_complete = zm_data.get(
                        "module_complete", False
                    )
                else:
                    # Stash raw data for post-load manifest wiring
                    self._pending_zone_state: Dict[str, Any] = zm_data
            except (ImportError, Exception):
                pass
        # WO-Phase3: Restore subsystem state
        from codex.games.stc.surgebinding import SurgeManager, StormTracker
        from codex.games.stc.ideals import IdealProgression
        self._surge_managers = {
            n: SurgeManager.from_dict(d)
            for n, d in data.get("surge_managers", {}).items()
        }
        self._ideal_trackers = {
            n: IdealProgression.from_dict(d)
            for n, d in data.get("ideal_trackers", {}).items()
        }
        st_data = data.get("storm_tracker")
        if st_data:
            self._storm_tracker = StormTracker.from_dict(st_data)
        else:
            self._storm_tracker = None
        # WO-V56.0: Restore delta tracker
        dt_data = data.get("delta_tracker")
        if dt_data:
            try:
                from codex.core.services.narrative_frame import DeltaTracker
                self.delta_tracker = DeltaTracker.from_dict(dt_data)
            except ImportError:
                pass

    def generate_dungeon(self, depth: int = 4, seed: Optional[int] = None) -> dict:
        """Generate a dungeon using the Universal Map Engine with Cosmere content."""
        from codex.spatial.map_engine import CodexMapEngine, ContentInjector
        map_engine = CodexMapEngine(seed=seed)
        self.dungeon_graph = map_engine.generate(
            width=50, height=50, min_room_size=5, max_depth=depth,
            system_id="stc",
        )
        adapter = CosmereAdapter(seed=seed, setting_id=self.setting_id)
        injector = ContentInjector(adapter)
        self.populated_rooms = injector.populate_all(self.dungeon_graph)
        # WO-V53.0: Content-hints bridge — override random content with
        # hand-authored content_hints from module blueprints
        from codex.spatial.map_engine import PopulatedRoom
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
            f"Cosmere dungeon generated: {len(self.dungeon_graph.rooms)} rooms, "
            f"depth {depth}, seed {self.dungeon_graph.seed}",
            "MASTER",
        )
        return {
            "seed": self.dungeon_graph.seed,
            "total_rooms": len(self.dungeon_graph.rooms),
            "start_room": self.current_room_id,
        }

    def _apply_content_hints(self, PopulatedRoom) -> None:
        """Override populated rooms with hand-authored content_hints.

        For each room in the dungeon graph that has non-empty content_hints,
        parse them via SceneData and build a content dict that replaces the
        randomly-generated PopulatedRoom content.

        WO-V53.0: Ported from D&D 5e engine
        """
        if not self.dungeon_graph:
            return

        try:
            from codex.spatial.scene_data import SceneData
        except ImportError:
            return

        for room_id, room_node in self.dungeon_graph.rooms.items():
            hints = getattr(room_node, 'content_hints', None)
            if not hints:
                continue

            scene = SceneData.from_content_hints(hints)
            content: Dict[str, Any] = {}

            # Description
            if scene.description:
                content["description"] = scene.description
            if scene.read_aloud:
                content["read_aloud"] = scene.read_aloud

            # Enemies: convert SceneEnemy to engine-compatible dicts
            content["enemies"] = []
            for enemy in scene.enemies:
                for _ in range(enemy.count):
                    content["enemies"].append({
                        "name": enemy.name,
                        "hp": enemy.hp,
                        "max_hp": enemy.hp,
                        "attack": enemy.attack,
                        "defense": enemy.ac,
                        "tier": room_node.tier,
                        "notes": enemy.notes,
                    })

            # Loot: convert SceneLoot to engine-compatible dicts
            content["loot"] = [
                {"name": l.name, "tier": room_node.tier,
                 "value": l.value, "description": l.description}
                for l in scene.loot
            ]

            # NPCs: pass through as dicts
            if scene.npcs:
                content["npcs"] = [n.to_dict() for n in scene.npcs]

            # Skill check DCs
            if scene.investigation_dc:
                content["investigation_dc"] = scene.investigation_dc
                content["investigation_success"] = scene.investigation_success
            if scene.perception_dc:
                content["perception_dc"] = scene.perception_dc
                content["perception_success"] = scene.perception_success

            # Services and events
            if scene.services:
                content["services"] = scene.services
            if scene.event_triggers:
                content["event_triggers"] = scene.event_triggers
            if scene.renovation_options:
                content["renovation_options"] = scene.renovation_options

            content["hazards"] = []  # Module rooms don't use random hazards

            # Replace the populated room with content_hints data
            self.populated_rooms[room_id] = PopulatedRoom(
                geometry=room_node, content=content)

    def load_dungeon_graph(self, graph) -> None:
        """Load a pre-built DungeonGraph (from ZoneManager) into the engine.

        Populates rooms via CosmereAdapter + ContentInjector, applies any
        content_hints from module blueprints, and resets navigation state.

        WO-V53.0: Module Zone Pipeline Fix
        """
        from codex.spatial.map_engine import ContentInjector, PopulatedRoom
        self.dungeon_graph = graph
        adapter = CosmereAdapter(setting_id=self.setting_id)
        injector = ContentInjector(adapter)
        self.populated_rooms = injector.populate_all(graph)
        self._apply_content_hints(PopulatedRoom)
        self.current_room_id = graph.start_room_id
        self.visited_rooms = {self.current_room_id}
        start_room = graph.rooms.get(self.current_room_id)
        if start_room:
            self.player_pos = (start_room.x + start_room.width // 2,
                               start_room.y + start_room.height // 2)

    # ─── Navigation API ───────────────────────────────────────────────

    def get_current_room(self):
        """Return the current RoomNode or None."""
        if self.dungeon_graph and self.current_room_id is not None:
            return self.dungeon_graph.rooms.get(self.current_room_id)
        return None

    def get_connected_rooms(self):
        """Return list of room IDs connected to current room."""
        room = self.get_current_room()
        return room.connections if room else []

    def get_cardinal_exits(self):
        """Return list of {direction, id, type, tier} dicts for current room."""
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
                "direction": direction, "id": cid,
                "type": target.room_type.name if hasattr(target, 'room_type') else "NORMAL",
                "tier": getattr(target, 'tier', 1),
            })
        return exits

    def get_current_room_dict(self) -> Optional[Dict[str, Any]]:
        """Get current room as dict for callers expecting dict interface."""
        if not self.dungeon_graph or self.current_room_id is None:
            return None
        pop_room = self.populated_rooms.get(self.current_room_id)
        if not pop_room:
            return None
        return {
            "id": pop_room.geometry.id,
            "type": pop_room.geometry.room_type.value if hasattr(pop_room.geometry.room_type, 'value') else str(pop_room.geometry.room_type),
            "tier": pop_room.geometry.tier,
            "description": pop_room.content.get("description", ""),
            "enemies": pop_room.content.get("enemies", []),
            "loot": pop_room.content.get("loot", []),
            "hazards": pop_room.content.get("hazards", []),
            "visited": self.current_room_id in self.visited_rooms,
        }

    def move_to_room(self, room_id):
        """Move to a connected room. Returns True on success."""
        if room_id not in self.get_connected_rooms():
            return False
        self.current_room_id = room_id
        self.visited_rooms.add(room_id)
        self._add_shard(f"Party moved to room {room_id}", "CHRONICLE")
        target = self.dungeon_graph.rooms.get(room_id)
        if target:
            self.player_pos = (target.x + target.width // 2,
                               target.y + target.height // 2)
        # WO-V56.0: Record visit for delta-based narration
        if self.delta_tracker is not None:
            room_data = self.get_current_room_dict()
            if room_data:
                self.delta_tracker.record_visit(room_id, room_data)
        return True

    def move_player_grid(self, direction):
        """Move one tile in a cardinal direction. Returns True on success."""
        exits = self.get_cardinal_exits()
        for ex in exits:
            if ex["direction"] == direction:
                return self.move_to_room(ex["id"])
        return False

    # ─── Zone progression (module-based campaigns) ────────────────────

    def load_module(self, manifest_path: str) -> str:
        """Load a ModuleManifest from *manifest_path* and initialise the ZoneManager.

        The ZoneManager is created with the manifest's directory as ``base_path``
        so that relative blueprint paths resolve correctly.  After creation,
        the first zone is loaded immediately.

        Args:
            manifest_path: Absolute or relative path to the module JSON file.

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
        # WO-V57.0: Consume pending zone state from load_state() if present
        pending = getattr(self, '_pending_zone_state', None)
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
            f"Cosmere module '{manifest.display_name}' loaded; "
            f"zone '{zone_id}' ({rooms} rooms)",
            "MASTER",
        )
        return (
            f"Module '{manifest.display_name}' loaded. "
            f"Current zone: '{zone_id}' | {self.zone_manager.zone_progress}"
        )

    def advance_zone(self) -> str:
        """Advance the ZoneManager to the next zone and load it.

        Must call ``load_module()`` first.

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
        self._add_shard(
            f"Cosmere advanced to zone '{entry.zone_id}' ({rooms} rooms); "
            f"{self.zone_manager.zone_progress}",
            "CHRONICLE",
        )
        return (
            f"Advanced to zone '{entry.zone_id}' | "
            f"{self.zone_manager.zone_progress}"
        )

    def check_zone_exit(self, game_state: dict) -> bool:
        """Check whether the current zone's exit condition is satisfied.

        Delegates to ZoneManager.check_exit_condition().

        Args:
            game_state: Dict of current game-state flags (e.g. boss_defeated).

        Returns:
            True if the exit condition is met, False otherwise (or if no
            module is loaded).
        """
        if self.zone_manager is None:
            return False
        return self.zone_manager.check_exit_condition(game_state)

    # ─── WO-V34.0: Ideal Progression & Command Dispatch ───────────────

    def swear_ideal(self, char_name: str = "") -> str:
        """
        Swear the next Radiant Ideal — guaranteed milestone advancement.

        This is a DM/engine-controlled milestone. No dice roll. The ideal is
        always granted. For the player-facing narrative dice-check path, use
        handle_command('oath', ...) which calls _cmd_oath().

        Integrates with the IdealProgression subsystem to update tracker state
        and syncs the SurgeManager's ideal_level on success.
        """
        target = None
        for c in self.party:
            if c.name.lower() == char_name.lower() or not char_name:
                target = c
                break
        if not target:
            return f"Character '{char_name}' not found"
        if target.ideal_level >= 5:
            return f"{target.name} has sworn all 5 Ideals"

        target.ideal_level += 1

        # Sync IdealProgression tracker state (no dice check — guaranteed advance)
        tracker = self._get_ideal_tracker(target)
        tracker.current_ideal = target.ideal_level
        tracker.ideal_progress[target.ideal_level] = 1.0
        # Collect powers unlocked at this ideal level
        powers_unlocked: List[str] = []
        try:
            from codex.forge.reference_data.stc_orders import ORDERS as _ORDERS
            order_data_ref = _ORDERS.get(target.order.lower(), {})
            for power in order_data_ref.get("per_ideal_powers", {}).get(target.ideal_level, []):
                powers_unlocked.append(power["name"])
                tracker.unlock_ability(power["name"])
        except ImportError:
            pass

        # Stat boost on ideal advancement
        target.max_hp += 5
        target.current_hp = min(target.current_hp + 5, target.max_hp)
        target.max_focus += 1
        target.focus = min(target.focus + 1, target.max_focus)

        # Sync SurgeManager if it exists for this character
        if target.name in self._surge_managers:
            self._surge_managers[target.name].set_ideal_level(target.ideal_level)

        order_data = RADIANT_ORDERS.get(target.order.lower(), {})
        ideal_text = order_data.get("ideal", "I will protect")
        surges = order_data.get("surges", [])

        msg = (
            f"{target.name} swears the {_ordinal(target.ideal_level)} Ideal: "
            f'"{ideal_text}"\n'
            f"  Surges: {', '.join(surges)}\n"
            f"  Max HP +5 (now {target.max_hp})\n"
            f"  Focus cap +1 (now {target.max_focus})"
        )
        if powers_unlocked:
            msg += f"\n  Powers unlocked: {', '.join(powers_unlocked)}"

        self._add_shard(
            f"{target.name} swore the {_ordinal(target.ideal_level)} Ideal "
            f"({target.order}). Max HP: {target.max_hp}, Focus cap: {target.max_focus}",
            "ANCHOR",
        )
        return msg

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Command dispatcher for dashboard integration."""
        # ── Existing commands ──────────────────────────────────────────
        if cmd == "swear_ideal":
            return self.swear_ideal(kwargs.get("name", ""))
        elif cmd == "party_status":
            lines = ["Party:"]
            for c in self.party:
                surges = ", ".join(c.get_surges()) if c.order else "none"
                lines.append(
                    f"  {c.name}: {c.order or 'Unsworn'} (Ideal {c.ideal_level}) "
                    f"HP {c.current_hp}/{c.max_hp} Focus {c.focus} Surges: {surges}"
                )
            return "\n".join(lines)
        elif cmd == "roll_check":
            result = self.roll_check(**kwargs)
            return (
                f"Roll: {result['roll']} + {result['modifier']} "
                f"(focus: {result['focus_spent']}) = {result['total']}"
                + (f" vs DC {result['dc']}: {'SUCCESS' if result.get('success') else 'FAIL'}"
                   if 'dc' in result else "")
            )
        elif cmd == "trace_fact":
            return self.trace_fact(kwargs.get("fact", ""))
        elif cmd == "load_module":
            path = kwargs.get("path", "")
            if not path:
                return "load_module requires 'path' kwarg"
            return self.load_module(path)
        elif cmd == "advance_zone":
            return self.advance_zone()
        elif cmd == "zone_status":
            if self.zone_manager is None:
                return "No module loaded."
            zm = self.zone_manager
            status_lines = [
                f"Module: {zm.module_name}",
                f"Progress: {zm.zone_progress}",
                f"Chapter: {zm.chapter_name}",
                f"Zone: {zm.zone_name}",
                f"Complete: {zm.module_complete}",
            ]
            return "\n".join(status_lines)
        # ── WO-Phase3: New surgebinding commands ───────────────────────
        elif cmd == "surge":
            return self._cmd_surge(**kwargs)
        elif cmd == "infuse":
            return self._cmd_infuse(**kwargs)
        elif cmd == "stormlight_status":
            return self._cmd_stormlight_status(**kwargs)
        # ── WO-Phase3: New combat commands ─────────────────────────────
        elif cmd == "attack":
            return self._cmd_attack(**kwargs)
        elif cmd == "shardblade":
            return self._cmd_shardblade(**kwargs)
        elif cmd == "duel":
            return self._cmd_duel(**kwargs)
        # ── WO-Phase3: Ideal progression commands ─────────────────────
        elif cmd == "oath":
            return self._cmd_oath(**kwargs)
        elif cmd == "ideal_status":
            return self._cmd_ideal_status(**kwargs)
        # ── WO-Phase3: Storm commands ──────────────────────────────────
        elif cmd == "highstorm":
            return self._cmd_highstorm(**kwargs)
        return f"Unknown command: {cmd}"

    # ─── WO-Phase3: Command implementations ───────────────────────────

    def _cmd_surge(self, **kwargs) -> str:
        """Use a surge power: requires 'power' kwarg, optional 'char_name'."""
        char_name = kwargs.get("char_name", "")
        power_name = kwargs.get("power", "")
        if not power_name:
            return "surge requires 'power' kwarg (e.g. power='Basic Lashing')"
        char = self._resolve_character(char_name)
        if char is None:
            return f"Character '{char_name}' not found"
        mgr = self._get_surge_manager(char)
        result = mgr.use_power(power_name)
        return result["message"]

    def _cmd_infuse(self, **kwargs) -> str:
        """Infuse stormlight: requires 'amount' kwarg, optional 'char_name'."""
        char_name = kwargs.get("char_name", "")
        amount = int(kwargs.get("amount", 0))
        char = self._resolve_character(char_name)
        if char is None:
            return f"Character '{char_name}' not found"
        mgr = self._get_surge_manager(char)
        result = mgr.infuse(amount)
        return (
            f"{char.name} absorbs {result['absorbed']} stormlight. "
            f"Pool: {result['stormlight']}/{result['max_stormlight']}."
        )

    def _cmd_stormlight_status(self, **kwargs) -> str:
        """Show stormlight status for all party members."""
        if not self.party:
            return "No party members."
        lines: List[str] = []
        for c in self.party:
            if c.name in self._surge_managers:
                lines.append(self._surge_managers[c.name].get_status())
            else:
                lines.append(
                    f"{c.name} ({c.order or 'Unsworn'}) — no stormlight subsystem active"
                )
        return "\n".join(lines)

    def _cmd_attack(self, **kwargs) -> str:
        """Weapon attack: optional 'char_name', 'weapon', 'target_defense'."""
        char_name = kwargs.get("char_name", "")
        weapon = kwargs.get("weapon", "spear")
        target_enemy = kwargs.get("target_enemy", None)
        char = self._resolve_character(char_name)
        if char is None:
            return f"Character '{char_name}' not found"
        resolver = self._get_combat_resolver()
        target_def = int(kwargs.get("target_defense", 12))
        if target_enemy and isinstance(target_enemy, dict):
            target_def = target_enemy.get("defense", target_def)
        result = resolver.attack_roll(
            char,
            target_defense=target_def,
            weapon_name=weapon,
            ability_mod=char.modifier("strength"),
            advantage=kwargs.get("advantage", False),
            disadvantage=kwargs.get("disadvantage", False),
        )
        result.target = (
            target_enemy.get("name", "enemy")
            if isinstance(target_enemy, dict) else "enemy"
        )
        if result.hit and target_enemy and isinstance(target_enemy, dict):
            target_enemy["hp"] = max(0, target_enemy.get("hp", 0) - result.damage)
        return result.describe()

    def _cmd_shardblade(self, **kwargs) -> str:
        """Shardblade attack: optional 'char_name', requires 'target_enemy' dict."""
        char_name = kwargs.get("char_name", "")
        target_enemy = kwargs.get("target_enemy", None)
        char = self._resolve_character(char_name)
        if char is None:
            return f"Character '{char_name}' not found"
        if not target_enemy:
            return "shardblade requires 'target_enemy' dict"
        resolver = self._get_combat_resolver()
        result = resolver.shardblade_attack(char, target_enemy)
        return result["message"]

    def _cmd_duel(self, **kwargs) -> str:
        """Duel of champions: requires 'challenger' and 'defender' dicts."""
        challenger = kwargs.get("challenger")
        defender = kwargs.get("defender")
        if not challenger or not defender:
            return "duel requires 'challenger' and 'defender' kwargs"
        resolver = self._get_combat_resolver()
        rounds = int(kwargs.get("rounds", 5))
        result = resolver.duel_of_champions(challenger, defender, rounds=rounds)
        lines = result["log"] + [
            f"Winner: {result['winner'] or 'Draw'} | "
            f"Attacker HP: {result['attacker_hp']} | "
            f"Defender HP: {result['defender_hp']}"
        ]
        return "\n".join(lines)

    def _cmd_oath(self, **kwargs) -> str:
        """Attempt to swear the next ideal: optional 'char_name', 'context'."""
        char_name = kwargs.get("char_name", "")
        context = kwargs.get("context", "")
        char = self._resolve_character(char_name)
        if char is None:
            return f"Character '{char_name}' not found"
        tracker = self._get_ideal_tracker(char)
        next_ideal = char.ideal_level + 1
        if next_ideal > 5:
            return f"{char.name} has sworn all 5 Ideals."
        # Mark sufficient progress for the oath attempt
        tracker.add_progress(0.6, reason="oath attempt")
        result = tracker.oath_check(next_ideal, context=context)
        if result["success"]:
            # Sync character and engine state
            char.ideal_level = next_ideal
            char.max_hp += 5
            char.current_hp = min(char.current_hp + 5, char.max_hp)
            char.max_focus += 1
            char.focus = min(char.focus + 1, char.max_focus)
            if char.name in self._surge_managers:
                self._surge_managers[char.name].set_ideal_level(char.ideal_level)
            self._add_shard(
                f"{char.name} swore Ideal {next_ideal} ({char.order}). "
                f"Max HP: {char.max_hp}",
                "ANCHOR",
            )
        return result["message"]

    def _cmd_ideal_status(self, **kwargs) -> str:
        """Show ideal progression status: optional 'char_name'."""
        char_name = kwargs.get("char_name", "")
        char = self._resolve_character(char_name)
        if char is None:
            return f"Character '{char_name}' not found"
        tracker = self._get_ideal_tracker(char)
        ideals = tracker.get_available_ideals()
        lines = [f"Ideal Progression — {char.name} ({char.order.title() or 'Unsworn'}):"]
        for ideal in ideals:
            status = "SWORN" if ideal["sworn"] else (
                "READY" if ideal["ready_to_attempt"] else f"{ideal['progress']:.0%}"
            )
            lines.append(
                f"  [{status}] Ideal {ideal['ideal_number']}: "
                f"{ideal['text'][:60]}..." if len(ideal['text']) > 60 else
                f"  [{status}] Ideal {ideal['ideal_number']}: {ideal['text']}"
            )
        return "\n".join(lines)

    def _cmd_highstorm(self, **kwargs) -> str:
        """Check storm status or trigger a highstorm: optional 'trigger' bool."""
        tracker = self._get_storm_tracker()
        if kwargs.get("trigger", False):
            result = tracker.trigger_highstorm()
            return (
                f"Highstorm triggered! Intensity: {result['intensity']}. "
                f"{result['sphere_recharge']} "
                f"{result['environmental_effect']} "
                f"Next storm in {result['next_cycle']} days."
            )
        advance = kwargs.get("advance_day", False)
        if advance:
            result = tracker.advance_day()
            if result["highstorm_occurred"]:
                storm = result["storm_data"]
                return (
                    f"Day advanced. HIGHSTORM! Intensity: {storm['intensity']}. "
                    f"{storm['sphere_recharge']}"
                )
            return (
                f"Day advanced. No storm. Days since last storm: "
                f"{result['days_since_storm']}/{tracker.storm_cycle}."
            )
        # Status
        days_until = max(0, tracker.storm_cycle - tracker.days_since_storm)
        return (
            f"Storm tracker: {tracker.days_since_storm} days since last highstorm. "
            f"Next expected in ~{days_until} days."
        )

    def _resolve_character(self, char_name: str) -> Optional[CosmereCharacter]:
        """Find a party member by name (empty name returns first member)."""
        for c in self.party:
            if c.name.lower() == char_name.lower() or not char_name:
                return c
        return None


def _ordinal(n: int) -> str:
    """Return ordinal string for a number."""
    suffix = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}
    return suffix.get(n, f"{n}th")


# =========================================================================
# MAP ADAPTER — Universal Map Engine compatibility
# =========================================================================

_ENEMY_POOL_FALLBACK: Dict[int, List[str]] = {
    1: ["Cremling Swarm", "Chasmfiend Hatchling", "Parshendi Scout", "Skyeel"],
    2: ["Parshendi Warrior", "Thunderclast Shard", "Midnight Essence", "Fused Scout"],
    3: ["Fused Soldier", "Chasmfiend", "Unmade Fragment", "Regal Stormform"],
    4: ["Thunderclast", "Unmade", "Fused Magnate", "Voidbringer Herald"],
}

_LOOT_POOL_FALLBACK: Dict[int, List[str]] = {
    1: ["Stormlight Sphere (Chip)", "Shardblade Fragment", "Healing Fabrial", "Parshendi Carapace"],
    2: ["Stormlight Sphere (Mark)", "Half-Shard Shield", "Alerter Fabrial", "Windrunner Glyph"],
    3: ["Stormlight Sphere (Broam)", "Shardblade", "Soulcaster (cracked)", "Radiant Plate Shard"],
    4: ["Honorblade", "Shardplate (full)", "Soulcaster (functional)", "Herald's Relic"],
}

_HAZARD_POOL_FALLBACK: Dict[int, List[str]] = {
    1: ["Highstorm Winds", "Cracked Chasm Floor", "Crem Buildup"],
    2: ["Chasm Collapse", "Stormlight Surge", "Parshendi Trap"],
    3: ["Everstorm Fragment", "Unmade Corruption", "Void Rift"],
    4: ["Full Everstorm", "Odium's Influence", "Spiritual Realm Breach"],
}

_STC_BESTIARY_CACHE: Optional[Dict[int, List[dict]]] = None
_STC_LOOT_CACHE: Optional[Dict[int, List[str]]] = None
_STC_HAZARD_CACHE: Optional[Dict[int, List[str]]] = None


def _load_bestiary() -> Dict[int, List[dict]]:
    """Load STC bestiary from config/bestiary/stc.json, fallback to name-only."""
    global _STC_BESTIARY_CACHE
    if _STC_BESTIARY_CACHE is not None:
        return _STC_BESTIARY_CACHE
    from codex.core.config_loader import load_config
    data = load_config("bestiary", "stc")
    if data and "tiers" in data:
        result: Dict[int, List[dict]] = {}
        for tier_key, monsters in data["tiers"].items():
            result[int(tier_key)] = monsters
        _STC_BESTIARY_CACHE = result
        return result
    # Fallback: name-only entries
    result = {}
    for tier, names in _ENEMY_POOL_FALLBACK.items():
        result[tier] = [{"name": n} for n in names]
    _STC_BESTIARY_CACHE = result
    return result


def _load_loot_pool() -> Dict[int, List[str]]:
    """Load STC loot pool from config/loot/stc.json, fallback to hardcoded."""
    global _STC_LOOT_CACHE
    if _STC_LOOT_CACHE is not None:
        return _STC_LOOT_CACHE
    from codex.core.config_loader import load_config
    data = load_config("loot", "stc")
    if data and "tiers" in data:
        result: Dict[int, List[str]] = {}
        for tier_key, items in data["tiers"].items():
            result[int(tier_key)] = [item["name"] for item in items]
        _STC_LOOT_CACHE = result
        return result
    _STC_LOOT_CACHE = _LOOT_POOL_FALLBACK
    return _STC_LOOT_CACHE


def _load_hazard_pool() -> Dict[int, List[str]]:
    """Load STC hazard pool from config/hazards/stc.json, fallback to hardcoded."""
    global _STC_HAZARD_CACHE
    if _STC_HAZARD_CACHE is not None:
        return _STC_HAZARD_CACHE
    from codex.core.config_loader import load_config
    data = load_config("hazards", "stc")
    if data and "tiers" in data:
        result: Dict[int, List[str]] = {}
        for tier_key, hazards in data["tiers"].items():
            result[int(tier_key)] = [h["name"] for h in hazards]
        _STC_HAZARD_CACHE = result
        return result
    _STC_HAZARD_CACHE = _HAZARD_POOL_FALLBACK
    return _STC_HAZARD_CACHE


# Tier-scaled pools — populated from config with fallback
_ENEMY_POOL: Dict[int, List[str]] = {
    tier: [m["name"] for m in monsters]
    for tier, monsters in _load_bestiary().items()
}
_LOOT_POOL = _load_loot_pool()
_HAZARD_POOL = _load_hazard_pool()

_ENEMY_POOL_REGISTRY: Dict[str, Dict[int, List[str]]] = {"roshar": _ENEMY_POOL}
_LOOT_POOL_REGISTRY: Dict[str, Dict[int, List[str]]] = {"roshar": _LOOT_POOL}
_HAZARD_POOL_REGISTRY: Dict[str, Dict[int, List[str]]] = {"roshar": _HAZARD_POOL}


class CosmereAdapter:
    """RulesetAdapter for Cosmere RPG content injection into the Universal Map Engine."""

    def __init__(self, seed: Optional[int] = None, setting_id: str = ""):
        self._rng = random.Random(seed)
        self._setting_id = setting_id
        from codex.forge.reference_data.setting_filter import filter_pool_by_setting
        self._enemies = filter_pool_by_setting(_ENEMY_POOL, setting_id, _ENEMY_POOL_REGISTRY)
        self._loot = filter_pool_by_setting(_LOOT_POOL, setting_id, _LOOT_POOL_REGISTRY)
        self._hazards = filter_pool_by_setting(_HAZARD_POOL, setting_id, _HAZARD_POOL_REGISTRY)

    def _make_enemy(self, tier: int) -> dict:
        """Create an enemy dict from bestiary data if available."""
        bestiary = _load_bestiary()
        monsters = bestiary.get(tier, bestiary.get(1, []))
        entry = self._rng.choice(monsters) if monsters else {}
        name = entry.get("name", self._rng.choice(
            self._enemies.get(tier, self._enemies.get(1, ["Unknown"]))
        ))
        if "base_hp" in entry:
            hp = entry["base_hp"]
            deflect = entry.get("deflect", 0)
            phys = entry.get("physical", {})
            atk = phys.get("str", 2) + self._rng.randint(0, 1)
            defense = 10 + tier + deflect
        else:
            hp = self._rng.randint(4 * tier, 10 * tier)
            atk = tier + self._rng.randint(1, 4)
            defense = 10 + tier
        return {
            "name": name, "hp": hp, "max_hp": hp,
            "attack": atk, "defense": defense, "tier": tier,
        }

    def populate_room(self, room) -> "PopulatedRoom":
        from codex.spatial.map_engine import PopulatedRoom, RoomType
        content: Dict[str, Any] = {}
        tier = max(1, min(4, room.tier))
        rtype = room.room_type

        descs = {
            RoomType.NORMAL: [
                "A hewn stone chamber. Crem coats the walls in thin layers.",
                "Stormlight leaks from cracked gemstones embedded in the ceiling.",
                "The ruins of a Rosharan watchtower, half-buried in rock.",
            ],
            RoomType.TREASURE: [
                "A vault of cut gemstones, still glowing faintly with Stormlight.",
                "An armoury of ancient Rosharan make. Glyphs glow on the walls.",
            ],
            RoomType.BOSS: [
                "A vast chasm hall. The air hums with Voidlight.",
                "Thunderclast carvings line the walls. The ground trembles.",
            ],
            RoomType.START: [
                "The warcamp entrance. The Shattered Plains stretch before you.",
            ],
        }
        pool = descs.get(rtype, descs[RoomType.NORMAL])
        content["description"] = self._rng.choice(pool)

        content["enemies"] = []
        if rtype not in (RoomType.START,):
            count = self._rng.randint(0, 2) if rtype != RoomType.BOSS else self._rng.randint(1, 2)
            for _ in range(count):
                content["enemies"].append(self._make_enemy(tier))

        content["loot"] = []
        if rtype in (RoomType.TREASURE, RoomType.BOSS) or self._rng.random() < 0.3:
            loot_pool = self._loot.get(tier, self._loot[1])
            content["loot"].append({"name": self._rng.choice(loot_pool), "tier": tier})

        content["hazards"] = []
        if self._rng.random() < 0.2:
            hazard_pool = self._hazards.get(tier, self._hazards[1])
            content["hazards"].append({"name": self._rng.choice(hazard_pool)})

        return PopulatedRoom(geometry=room, content=content)

    def get_enemy_pool(self, tier: int) -> List[str]:
        return self._enemies.get(max(1, min(4, tier)), self._enemies[1])

    def get_loot_pool(self, tier: int) -> List[str]:
        return self._loot.get(max(1, min(4, tier)), self._loot[1])


# =========================================================================
# TRAIT RESOLVER
# =========================================================================

from codex.core.services.trait_handler import TraitResolver

_SURGE_ATTRIBUTES = {
    "adhesion": "strength", "gravitation": "strength",
    "division": "intellect", "abrasion": "speed",
    "progression": "intellect", "illumination": "intellect",
    "transformation": "intellect", "transportation": "speed",
    "cohesion": "strength", "tension": "strength",
}


class CosmereTraitResolver(TraitResolver):
    def resolve_trait(self, trait_id, context):
        from codex.core.dice import roll_dice
        surge = trait_id.lower()
        attribute = _SURGE_ATTRIBUTES.get(surge)
        if not attribute:
            return {"success": False, "error": f"Unknown surge: {trait_id}"}
        char = context.get("character")
        if not char:
            return {"success": False, "error": "No character in context"}
        char_surges = [s.lower() for s in char.get_surges()]
        if surge not in char_surges:
            return {"success": False, "error": f"{char.order} lacks surge: {trait_id}"}
        dc = context.get("dc", 10)
        focus_spend = context.get("focus_spend", 0)
        _, rolls, _ = roll_dice("1d20")
        raw = rolls[0]
        mod = char.modifier(attribute)
        actual_focus = min(focus_spend, char.focus)
        if actual_focus > 0:
            char.focus -= actual_focus
        total = raw + mod + actual_focus
        return {"trait_id": trait_id, "surge": surge, "attribute": attribute,
                "roll": raw, "modifier": mod, "focus_spent": actual_focus,
                "total": total, "dc": dc, "success": total >= dc or raw == 20,
                "critical": raw == 20, "fumble": raw == 1}


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("stc", CosmereEngine)
except ImportError:
    pass

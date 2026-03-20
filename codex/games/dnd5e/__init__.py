"""
D&D 5th Edition — Game Engine
===============================

Provides the core engine for D&D 5e campaigns within Codex.
Uses the standard six-ability-score system, d20 resolution,
and class/race/background character model.

Integrates with:
  - codex/spatial/map_engine.py via DnD5eAdapter (RulesetAdapter)
  - codex/forge/char_wizard.py via vault/dnd5e/creation_rules.json
  - codex/forge/codex_transmuter.py for cross-system conversion

Activated when a D&D 5e campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random

from codex.core.services.narrative_loom import NarrativeLoomMixin


# =========================================================================
# CHARACTER
# =========================================================================

@dataclass
class DnD5eCharacter:
    """A D&D 5e player character."""
    name: str
    race: str = ""
    character_class: str = ""
    level: int = 1
    background: str = ""

    # Six ability scores
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Derived
    max_hp: int = 0
    current_hp: int = 0
    armor_class: int = 10
    proficiency_bonus: int = 2
    inventory: List[dict] = field(default_factory=list)

    # WO-V34.0: Rest & Progression
    xp: int = 0
    hit_dice_remaining: int = 0
    hit_die_type: int = 0

    # WO-V40.0: Spellcasting, combat, feats
    proficiencies: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)

    # WO-V55.0: Campaign setting (e.g. "forgotten_realms")
    setting_id: str = ""

    def __post_init__(self):
        if self.max_hp == 0:
            hit_die = CLASS_HIT_DIE.get(self.character_class.lower(), 8)
            con_mod = (self.constitution - 10) // 2
            self.max_hp = hit_die + con_mod
            self.current_hp = self.max_hp
        self.armor_class = 10 + (self.dexterity - 10) // 2
        # WO-V34.0: Set hit die type and remaining from class
        if self.hit_die_type == 0:
            self.hit_die_type = CLASS_HIT_DIE.get(self.character_class.lower(), 8)
        if self.hit_dice_remaining == 0:
            self.hit_dice_remaining = max(1, self.level)

    def modifier(self, score: int) -> int:
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
        limit = self.strength * 15  # D&D 5e standard
        current = sum(item.get("weight", 0) for item in self.inventory)
        return check_capacity(CapacityMode.WEIGHT, limit, current)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "race": self.race,
            "character_class": self.character_class, "level": self.level,
            "background": self.background,
            "strength": self.strength, "dexterity": self.dexterity,
            "constitution": self.constitution, "intelligence": self.intelligence,
            "wisdom": self.wisdom, "charisma": self.charisma,
            "max_hp": self.max_hp, "current_hp": self.current_hp,
            "armor_class": self.armor_class,
            "proficiency_bonus": self.proficiency_bonus,
            "xp": self.xp,
            "hit_dice_remaining": self.hit_dice_remaining,
            "hit_die_type": self.hit_die_type,
            "proficiencies": self.proficiencies,
            "features": self.features,
            "setting_id": self.setting_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DnD5eCharacter":
        c = cls(
            name=data["name"], race=data.get("race", ""),
            character_class=data.get("character_class", ""),
            level=data.get("level", 1), background=data.get("background", ""),
            strength=data.get("strength", 10), dexterity=data.get("dexterity", 10),
            constitution=data.get("constitution", 10),
            intelligence=data.get("intelligence", 10),
            wisdom=data.get("wisdom", 10), charisma=data.get("charisma", 10),
        )
        c.max_hp = data.get("max_hp", c.max_hp)
        c.current_hp = data.get("current_hp", c.current_hp)
        c.armor_class = data.get("armor_class", c.armor_class)
        c.proficiency_bonus = data.get("proficiency_bonus", 2)
        c.xp = data.get("xp", 0)
        c.hit_dice_remaining = data.get("hit_dice_remaining", c.hit_dice_remaining)
        c.hit_die_type = data.get("hit_die_type", c.hit_die_type)
        c.proficiencies = data.get("proficiencies", [])
        c.features = data.get("features", [])
        c.setting_id = data.get("setting_id", "")
        return c


CLASS_HIT_DIE: Dict[str, int] = {
    "barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10,
    "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8,
    "warlock": 8, "artificer": 8, "sorcerer": 6, "wizard": 6,
}

# WO-V39.0: Party scaling — enemies scale with party size
DND5E_PARTY_SCALING: Dict[int, Dict[str, float]] = {
    1: {"hp": 1.0, "atk": 1.0},
    2: {"hp": 1.3, "atk": 1.1},
    3: {"hp": 1.6, "atk": 1.2},
    4: {"hp": 2.0, "atk": 1.3},
    5: {"hp": 2.3, "atk": 1.4},
    6: {"hp": 2.6, "atk": 1.5},
}


# =========================================================================
# ENGINE
# =========================================================================

class DnD5eEngine(NarrativeLoomMixin):
    """
    Core engine for D&D 5e campaigns.

    Manages party, initiative, and dungeon state.
    Compatible with the Universal Map Engine via DnD5eAdapter.
    """

    system_id = "dnd5e"
    system_family = "DND5E"
    display_name = "D&D 5th Edition"

    def __init__(self):
        self.character: Optional[DnD5eCharacter] = None
        self.party: List[DnD5eCharacter] = []
        self.dungeon_graph: Optional[Any] = None
        self.populated_rooms: Dict[int, Any] = {}
        self.current_room_id: Optional[int] = None
        self.player_pos: Optional[tuple] = None
        self.visited_rooms: set = set()
        self._init_loom()
        # WO-V40.0: Spell/combat/feat subsystems (lazy-initialised per character)
        self._spell_slots: Dict[str, Any] = {}    # char_name -> SpellSlotTracker
        self._concentration: Dict[str, Any] = {}  # char_name -> ConcentrationTracker
        self._spell_managers: Dict[str, Any] = {} # char_name -> SpellManager
        self._feat_managers: Dict[str, Any] = {}  # char_name -> FeatManager
        self._combat_resolver: Optional[Any] = None  # Lazy init
        # Zone progression (module-based campaigns)
        self.zone_manager: Optional[Any] = None
        self._module_manifest_path: Optional[str] = None
        # WO-V55.0: Campaign setting (e.g. "forgotten_realms")
        self.setting_id: str = ""
        # WO-V56.0: DeltaTracker for narrative storytelling
        try:
            from codex.core.services.narrative_frame import DeltaTracker
            self.delta_tracker = DeltaTracker()
        except ImportError:
            self.delta_tracker = None

    def create_character(self, name: str, **kwargs) -> DnD5eCharacter:
        # WO-V55.0: Pop setting_id before passing to DnD5eCharacter
        setting_id = kwargs.pop("setting_id", "")
        if setting_id:
            self.setting_id = setting_id
        char = DnD5eCharacter(name=name, setting_id=self.setting_id, **kwargs)
        self.character = char
        self.party = [char]
        return char

    def add_to_party(self, char: DnD5eCharacter) -> None:
        self.party.append(char)

    def remove_from_party(self, char: DnD5eCharacter) -> None:
        if char in self.party:
            self.party.remove(char)
        if self.character is char:
            alive = self.get_active_party()
            self.character = alive[0] if alive else None

    def get_active_party(self) -> List[DnD5eCharacter]:
        return [c for c in self.party if c.is_alive()]

    def get_mood_context(self) -> dict:
        """Return current mechanical state as narrative mood modifiers (WO-V61.0)."""
        char = self.character
        hp_pct = char.current_hp / max(1, char.max_hp) if char else 1.0
        tension = 1.0 - hp_pct
        if hp_pct < 0.25:
            condition, words = "critical", ["bleeding", "frantic", "dim"]
        elif hp_pct < 0.5:
            condition, words = "battered", ["worn", "cautious", "tense"]
        else:
            condition, words = "healthy", []
        return {
            "tension": round(tension, 2),
            "tone_words": words,
            "party_condition": condition,
            "system_specific": {},
        }

    def get_status(self) -> Dict[str, Any]:
        lead = self.party[0] if self.party else None
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "lead_hp": f"{lead.current_hp}/{lead.max_hp}" if lead else None,
            "room": self.current_room_id,
        }

    def roll_check(self, character=None, ability="strength",
                   proficiency=False, dc=None, **kwargs):
        from codex.core.dice import roll_dice
        char = character or self.character
        _, rolls, _ = roll_dice("1d20")
        raw = rolls[0]
        score = getattr(char, ability, 10)
        mod = char.modifier(score)
        prof = char.proficiency_bonus if proficiency else 0
        total = raw + mod + prof
        result = {"roll": raw, "modifier": mod, "proficiency_bonus": prof,
                  "total": total, "critical": raw == 20, "fumble": raw == 1}
        if dc is not None:
            result["dc"] = dc
            result["success"] = total >= dc or raw == 20
        return result

    def log_character_death(self, char, cause="Fell in the dungeon", seed=None):
        from codex.core.services.graveyard import log_death
        return log_death({"name": char.name, "hp_max": char.max_hp,
            "race": char.race, "character_class": char.character_class,
            "level": char.level, "cause": cause,
            "room_id": self.current_room_id}, system_id="dnd5e", seed=seed)

    def save_state(self) -> Dict[str, Any]:
        state: Dict[str, Any] = {
            "system_id": self.system_id,
            "party": [c.to_dict() for c in self.party],
            "current_room_id": self.current_room_id,
            "player_pos": list(self.player_pos) if self.player_pos else None,
            "visited_rooms": list(self.visited_rooms),
            # WO-V40.0: Spell/combat/feat subsystem state
            "spell_slots": {
                name: t.to_dict() for name, t in self._spell_slots.items()
            },
            "concentration": {
                name: t.to_dict() for name, t in self._concentration.items()
            },
            "spell_managers": {
                name: m.to_dict() for name, m in self._spell_managers.items()
            },
            "feat_managers": {
                name: m.to_dict() for name, m in self._feat_managers.items()
            },
            # Zone progression state
            "zone_manager": self.zone_manager.to_dict() if self.zone_manager else None,
            "module_manifest_path": self._module_manifest_path,
            # WO-V55.0: Campaign setting
            "setting_id": self.setting_id,
            # WO-V56.0: Delta tracker persistence
            "delta_tracker": self.delta_tracker.to_dict() if self.delta_tracker else None,
        }
        return state

    def load_state(self, data: Dict[str, Any]) -> None:
        self.party = [DnD5eCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.current_room_id = data.get("current_room_id")
        pos = data.get("player_pos")
        self.player_pos = tuple(pos) if pos else None
        self.visited_rooms = set(data.get("visited_rooms", []))
        # WO-V40.0: Restore spell/combat/feat subsystems
        from codex.games.dnd5e.spellcasting import (
            SpellSlotTracker, ConcentrationTracker, SpellManager,
        )
        from codex.games.dnd5e.feats import FeatManager
        self._spell_slots = {
            n: SpellSlotTracker.from_dict(d)
            for n, d in data.get("spell_slots", {}).items()
        }
        self._concentration = {
            n: ConcentrationTracker.from_dict(d)
            for n, d in data.get("concentration", {}).items()
        }
        self._spell_managers = {
            n: SpellManager.from_dict(d)
            for n, d in data.get("spell_managers", {}).items()
        }
        self._feat_managers = {
            n: FeatManager.from_dict(d)
            for n, d in data.get("feat_managers", {}).items()
        }
        # WO-V57.0: Restore module manifest path
        self._module_manifest_path = data.get("module_manifest_path")
        # Zone progression: restore indices; manifest must be re-loaded separately
        zm_data = data.get("zone_manager")
        if zm_data:
            try:
                from codex.spatial.zone_manager import ZoneManager
                from codex.spatial.module_manifest import ModuleManifest
                # Manifest is not stored inline — restore indices only if
                # zone_manager is already set (e.g. load_module was called first).
                # If not set we store the raw dict so callers can restore later.
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
        # WO-V55.0: Restore campaign setting
        self.setting_id = data.get("setting_id", "")
        # WO-V56.0: Restore delta tracker
        dt_data = data.get("delta_tracker")
        if dt_data:
            try:
                from codex.core.services.narrative_frame import DeltaTracker
                self.delta_tracker = DeltaTracker.from_dict(dt_data)
            except ImportError:
                pass

    def generate_dungeon(self, depth: int = 4, seed: Optional[int] = None) -> dict:
        """Generate a dungeon using the Universal Map Engine with D&D 5e content."""
        from codex.spatial.map_engine import CodexMapEngine, ContentInjector, PopulatedRoom
        map_engine = CodexMapEngine(seed=seed)
        self.dungeon_graph = map_engine.generate(
            width=50, height=50, min_room_size=5, max_depth=depth,
            system_id="dnd5e",
        )
        adapter = DnD5eAdapter(seed=seed, party_size=len(self.party))
        injector = ContentInjector(adapter)
        self.populated_rooms = injector.populate_all(self.dungeon_graph)

        # WO-V51.0: Content-hints bridge — override random content with
        # hand-authored content_hints from module blueprints
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
            f"D&D 5e dungeon generated: {len(self.dungeon_graph.rooms)} rooms, "
            f"depth {depth}, seed {self.dungeon_graph.seed}",
            "MASTER",
        )
        return {
            "seed": self.dungeon_graph.seed,
            "total_rooms": len(self.dungeon_graph.rooms),
            "start_room": self.current_room_id,
        }

    def load_dungeon_graph(self, graph) -> None:
        """Load a pre-built DungeonGraph (from ZoneManager) into the engine.

        Populates rooms via DnD5eAdapter + ContentInjector, applies any
        content_hints from module blueprints, and resets navigation state.

        WO-V53.0: Module Zone Pipeline Fix
        """
        from codex.spatial.map_engine import ContentInjector, PopulatedRoom
        self.dungeon_graph = graph
        adapter = DnD5eAdapter(party_size=len(self.party))
        injector = ContentInjector(adapter)
        self.populated_rooms = injector.populate_all(graph)
        self._apply_content_hints(PopulatedRoom)
        self.current_room_id = graph.start_room_id
        self.visited_rooms = {self.current_room_id}
        start_room = graph.rooms.get(self.current_room_id)
        if start_room:
            self.player_pos = (start_room.x + start_room.width // 2,
                               start_room.y + start_room.height // 2)

    def _apply_content_hints(self, PopulatedRoom) -> None:
        """Override populated rooms with hand-authored content_hints.

        For each room in the dungeon graph that has non-empty content_hints,
        parse them via SceneData and build a content dict that replaces the
        randomly-generated PopulatedRoom content.

        WO-V51.0: Content-hints bridge
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
        self._add_shard(
            f"Party moved to room {room_id}",
            "CHRONICLE",
        )
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

    # ─── WO-V34.0: Rest / Progression / Command Dispatch ──────────────

    def short_rest(self) -> str:
        """Short rest: spend 1 hit die per character."""
        from codex.core.mechanics.rest import RestManager
        result = RestManager().short_rest_dnd5e(self)
        return result.summary()

    def long_rest(self) -> str:
        """Long rest: full HP, recover half hit dice."""
        from codex.core.mechanics.rest import RestManager
        result = RestManager().long_rest_dnd5e(self)
        return result.summary()

    def gain_xp(self, amount: int, source: str = "") -> str:
        """Award XP to all party members."""
        msgs = []
        for char in self.party:
            char.xp += amount
            msgs.append(f"{char.name}: +{amount} XP (total: {char.xp})")
        self._add_shard(
            f"Party gained {amount} XP" + (f" from {source}" if source else ""),
            "CHRONICLE",
        )
        return "\n".join(msgs) if msgs else "No party members"

    def level_up(self, char_name: str = "") -> str:
        """Level up a character if they have enough XP."""
        from codex.core.mechanics.progression import DND5E_XP_TABLE
        target = None
        for c in self.party:
            if c.name.lower() == char_name.lower() or not char_name:
                target = c
                break
        if not target:
            return f"Character '{char_name}' not found"

        next_level = target.level + 1
        threshold = DND5E_XP_TABLE.get(next_level)
        if threshold is None:
            return f"{target.name} is at max level ({target.level})"
        if target.xp < threshold:
            return f"{target.name} needs {threshold - target.xp} more XP for level {next_level}"

        target.level = next_level
        con_mod = (target.constitution - 10) // 2
        hp_roll = random.randint(1, target.hit_die_type) + con_mod
        target.max_hp += max(1, hp_roll)
        target.current_hp = target.max_hp
        target.hit_dice_remaining = target.level
        self._add_shard(
            f"{target.name} advanced to level {next_level} "
            f"({target.character_class}). Max HP: {target.max_hp}",
            "ANCHOR",
        )
        # Proficiency bump at levels 5, 9, 13, 17
        if next_level in (5, 9, 13, 17):
            target.proficiency_bonus += 1
        return f"{target.name} advanced to level {next_level}! Max HP: {target.max_hp}"

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
            f"D&D 5e module '{manifest.display_name}' loaded; "
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
            f"D&D 5e advanced to zone '{entry.zone_id}' ({rooms} rooms); "
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

    # ─── WO-V40.0: Subsystem accessors ────────────────────────────────

    def _get_combat_resolver(self):
        """Lazily initialise and return the DnD5eCombatResolver."""
        if self._combat_resolver is None:
            from codex.games.dnd5e.combat import DnD5eCombatResolver
            self._combat_resolver = DnD5eCombatResolver()
        return self._combat_resolver

    def _get_spell_tracker(self, char):
        """Return (or create) the SpellSlotTracker for a character."""
        if char.name not in self._spell_slots:
            from codex.games.dnd5e.spellcasting import SpellSlotTracker
            self._spell_slots[char.name] = SpellSlotTracker(
                char.character_class, char.level
            )
        return self._spell_slots[char.name]

    def _get_concentration(self, char):
        """Return (or create) the ConcentrationTracker for a character."""
        if char.name not in self._concentration:
            from codex.games.dnd5e.spellcasting import ConcentrationTracker
            self._concentration[char.name] = ConcentrationTracker()
        return self._concentration[char.name]

    def _get_spell_manager(self, char):
        """Return (or create) the SpellManager for a character."""
        if char.name not in self._spell_managers:
            from codex.games.dnd5e.spellcasting import SpellManager
            _ABILITY_MAP = {
                "bard": "charisma", "cleric": "wisdom", "druid": "wisdom",
                "paladin": "charisma", "ranger": "wisdom",
                "sorcerer": "charisma", "warlock": "charisma",
                "wizard": "intelligence", "artificer": "intelligence",
            }
            ability = _ABILITY_MAP.get(char.character_class.lower(), "intelligence")
            mod = char.modifier(getattr(char, ability, 10))
            self._spell_managers[char.name] = SpellManager(
                char.character_class, char.level, mod
            )
        return self._spell_managers[char.name]

    def _get_feat_manager(self, char):
        """Return (or create) the FeatManager for a character."""
        if char.name not in self._feat_managers:
            from codex.games.dnd5e.feats import FeatManager
            self._feat_managers[char.name] = FeatManager()
        return self._feat_managers[char.name]

    # ─── WO-V40.0: Combat & spellcasting actions ───────────────────────

    def attack(
        self,
        attacker_name: str = "",
        target_enemy: Optional[dict] = None,
        weapon: str = "unarmed",
        **kwargs,
    ) -> str:
        """
        Resolve a weapon attack by a party member against an enemy dict.

        Finesse weapons use the higher of STR/DEX modifier; ranged weapons
        use DEX; everything else uses STR.

        Args:
            attacker_name: Name of the attacking character (empty = first in party).
            target_enemy: Enemy dict with keys: name, hp, defense.
            weapon: Weapon name from WEAPON_PROPERTIES (default 'unarmed').
            **kwargs: advantage (bool), disadvantage (bool).

        Returns:
            Human-readable attack description.
        """
        char = None
        for c in self.party:
            if c.name.lower() == attacker_name.lower() or not attacker_name:
                char = c
                break
        if not char:
            return f"Character '{attacker_name}' not found"
        if not target_enemy:
            return "No target specified"

        resolver = self._get_combat_resolver()
        from codex.games.dnd5e.combat import WEAPON_PROPERTIES
        wpn = WEAPON_PROPERTIES.get(weapon.lower(), {})
        props = wpn.get("properties", [])

        if "Finesse" in props:
            mod = max(char.modifier(char.strength), char.modifier(char.dexterity))
        elif "Ammunition" in props:
            mod = char.modifier(char.dexterity)
        else:
            mod = char.modifier(char.strength)

        result = resolver.attack_roll(
            char,
            target_enemy.get("defense", 10),
            weapon_name=weapon,
            ability_mod=mod,
            prof_bonus=char.proficiency_bonus,
            advantage=kwargs.get("advantage", False),
            disadvantage=kwargs.get("disadvantage", False),
        )
        result.target = target_enemy.get("name", "enemy")
        if result.hit and result.damage > 0:
            target_enemy["hp"] = max(0, target_enemy.get("hp", 0) - result.damage)
        return result.describe()

    def cast(
        self,
        caster_name: str = "",
        spell_name: str = "",
        spell_level: int = 1,
        **kwargs,
    ) -> str:
        """
        Attempt to cast a spell by a party member.

        The spell must be prepared/known by the caster and a slot at the
        requested level must be available.

        Args:
            caster_name: Name of the casting character (empty = first in party).
            spell_name: Name of the spell to cast.
            spell_level: Slot level to use (0 = cantrip, no slot expended).
            **kwargs: Unused; present for forward compatibility.

        Returns:
            Human-readable cast result.
        """
        char = None
        for c in self.party:
            if c.name.lower() == caster_name.lower() or not caster_name:
                char = c
                break
        if not char:
            return f"Character '{caster_name}' not found"

        tracker = self._get_spell_tracker(char)
        manager = self._get_spell_manager(char)
        return manager.cast_spell(spell_name, tracker, spell_level)

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Command dispatcher for dashboard integration."""
        cmd = cmd.lower().replace("-", "_")
        if cmd == "short_rest":
            return self.short_rest()
        elif cmd == "long_rest":
            return self.long_rest()
        elif cmd == "gain_xp":
            return self.gain_xp(kwargs.get("amount", 0), kwargs.get("source", ""))
        elif cmd == "level_up":
            return self.level_up(kwargs.get("name", ""))
        elif cmd == "party_status":
            lines = ["Party:"]
            for c in self.party:
                lines.append(f"  {c.name}: L{c.level} {c.character_class} "
                             f"HP {c.current_hp}/{c.max_hp} XP {c.xp}")
            return "\n".join(lines)
        elif cmd == "trace_fact":
            return self.trace_fact(kwargs.get("fact", ""))
        elif cmd == "attack":
            return self.attack(**kwargs)
        elif cmd == "cast":
            return self.cast(**kwargs)
        elif cmd == "prepare":
            char = self.character
            if char:
                mgr = self._get_spell_manager(char)
                return mgr.prepare(kwargs.get("spell", ""))
            return "No character"
        elif cmd == "spells":
            char = self.character
            if char:
                tracker = self._get_spell_tracker(char)
                mgr = self._get_spell_manager(char)
                lines = [f"Cantrips: {', '.join(mgr.cantrips) or 'None'}"]
                if mgr.casting_type == "known":
                    lines.append(f"Known: {', '.join(mgr.known_spells) or 'None'}")
                else:
                    lines.append(
                        f"Prepared ({len(mgr.prepared_spells)}/{mgr.get_max_prepared()}): "
                        f"{', '.join(mgr.prepared_spells) or 'None'}"
                    )
                for lvl in range(1, 10):
                    cur = tracker.current_slots.get(lvl, 0)
                    mx = tracker.max_slots.get(lvl, 0)
                    if mx > 0:
                        lines.append(f"  Level {lvl}: {cur}/{mx} slots")
                conc = self._get_concentration(char)
                if conc.active_spell:
                    lines.append(f"Concentrating on: {conc.active_spell}")
                return "\n".join(lines)
            return "No character"
        elif cmd == "feat_check":
            char = self.character
            if char:
                fm = self._get_feat_manager(char)
                eligible = fm.get_eligible_feats(char)
                base = f"Eligible feats: {', '.join(eligible[:10])}"
                suffix = f" (+{len(eligible) - 10} more)" if len(eligible) > 10 else ""
                return base + suffix
            return "No character"
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
        return f"Unknown command: {cmd}"


# =========================================================================
# MAP ADAPTER — Universal Map Engine compatibility
# =========================================================================

# WO-V57.0: Config-driven bestiary loader
_BESTIARY_FALLBACK: Dict[int, List[str]] = {
    1: ["Goblin", "Kobold", "Giant Rat", "Skeleton", "Zombie"],
    2: ["Orc", "Bugbear", "Ghoul", "Ogre", "Shadow"],
    3: ["Troll", "Wraith", "Wight", "Manticore", "Owlbear"],
    4: ["Young Dragon", "Beholder Zombie", "Mind Flayer", "Lich Servant", "Death Knight"],
}

_BESTIARY_CACHE: Optional[Dict[int, List[dict]]] = None


def _load_bestiary() -> Dict[int, List[dict]]:
    """Load bestiary from config/bestiary/dnd5e.json.

    Returns dict keyed by tier (1-4). Each entry is a list of dicts with
    keys: name, cr, base_hp, base_ac, base_atk, base_dmg.

    Falls back to _BESTIARY_FALLBACK (name-only) if file missing.
    """
    global _BESTIARY_CACHE
    if _BESTIARY_CACHE is not None:
        return _BESTIARY_CACHE

    import json
    import os
    bestiary_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..", "config", "bestiary", "dnd5e.json",
    )
    bestiary_path = os.path.normpath(bestiary_path)
    try:
        with open(bestiary_path) as f:
            data = json.load(f)
        tiers = data.get("tiers", {})
        result: Dict[int, List[dict]] = {}
        for tier_key, monsters in tiers.items():
            result[int(tier_key)] = monsters
        _BESTIARY_CACHE = result
        return result
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        # Fall back to name-only pool
        result = {}
        for tier, names in _BESTIARY_FALLBACK.items():
            result[tier] = [{"name": n} for n in names]
        _BESTIARY_CACHE = result
        return result


# Tier-scaled enemy pools — populated from bestiary
_ENEMY_POOL: Dict[int, List[str]] = {
    tier: [m["name"] for m in monsters]
    for tier, monsters in (_load_bestiary()).items()
}

_LOOT_POOL_FALLBACK: Dict[int, List[str]] = {
    1: ["Potion of Healing", "Shortsword +1", "50 gp", "Scroll of Shield", "Rope of Climbing"],
    2: ["Potion of Greater Healing", "Longsword +1", "200 gp", "Wand of Magic Missiles", "Cloak of Protection"],
    3: ["Potion of Superior Healing", "Greatsword +2", "750 gp", "Ring of Protection", "Staff of the Python"],
    4: ["Potion of Supreme Healing", "Holy Avenger", "2500 gp", "Rod of the Pact Keeper +3", "Vorpal Sword"],
}

_HAZARD_POOL_FALLBACK: Dict[int, List[str]] = {
    1: ["Pit Trap (DC 10)", "Poison Dart Trap (DC 12)", "Alarm Glyph"],
    2: ["Swinging Blade (DC 14)", "Poison Gas (DC 13)", "Collapsing Floor (DC 12)"],
    3: ["Flame Jet (DC 15)", "Teleport Trap (DC 16)", "Anti-Magic Zone"],
    4: ["Sphere of Annihilation", "Symbol of Death (DC 18)", "Prismatic Wall"],
}

_LOOT_CACHE: Optional[Dict[int, List[str]]] = None
_HAZARD_CACHE: Optional[Dict[int, List[str]]] = None
_MAGIC_ITEMS_CACHE: Optional[List[dict]] = None
_TRAP_CACHE: Optional[Dict[int, List[dict]]] = None


def _load_loot_pool() -> Dict[int, List[str]]:
    """Load loot pool from config/loot/dnd5e.json, fallback to hardcoded."""
    global _LOOT_CACHE
    if _LOOT_CACHE is not None:
        return _LOOT_CACHE
    from codex.core.config_loader import load_config
    data = load_config("loot", "dnd5e")
    if data and "tiers" in data:
        result: Dict[int, List[str]] = {}
        for tier_key, items in data["tiers"].items():
            result[int(tier_key)] = [item["name"] for item in items]
        _LOOT_CACHE = result
        return result
    _LOOT_CACHE = _LOOT_POOL_FALLBACK
    return _LOOT_CACHE


def _load_hazard_pool() -> Dict[int, List[str]]:
    """Load hazard pool from config/hazards/dnd5e.json, fallback to hardcoded."""
    global _HAZARD_CACHE
    if _HAZARD_CACHE is not None:
        return _HAZARD_CACHE
    from codex.core.config_loader import load_config
    data = load_config("hazards", "dnd5e")
    if data and "tiers" in data:
        result: Dict[int, List[str]] = {}
        for tier_key, hazards in data["tiers"].items():
            names = []
            for h in hazards:
                dc = h.get("dc")
                name = h["name"]
                if dc and dc > 0:
                    names.append(f"{name} (DC {dc})")
                else:
                    names.append(name)
            result[int(tier_key)] = names
        _HAZARD_CACHE = result
        return result
    _HAZARD_CACHE = _HAZARD_POOL_FALLBACK
    return _HAZARD_CACHE


def _load_magic_items() -> List[dict]:
    """Load magic items from config/magic_items/dnd5e.json."""
    global _MAGIC_ITEMS_CACHE
    if _MAGIC_ITEMS_CACHE is not None:
        return _MAGIC_ITEMS_CACHE
    from codex.core.config_loader import load_config
    data = load_config("magic_items", "dnd5e")
    if data and "items" in data:
        _MAGIC_ITEMS_CACHE = data["items"]
        return _MAGIC_ITEMS_CACHE
    _MAGIC_ITEMS_CACHE = []
    return _MAGIC_ITEMS_CACHE


def _load_trap_pool() -> Dict[int, List[dict]]:
    """Load trap pool from config/traps/dnd5e.json, empty dict if unavailable."""
    global _TRAP_CACHE
    if _TRAP_CACHE is not None:
        return _TRAP_CACHE
    from codex.core.config_loader import load_config
    data = load_config("traps", "dnd5e")
    if data and "traps" in data:
        by_tier: Dict[int, List[dict]] = {1: [], 2: [], 3: [], 4: []}
        for trap in data["traps"]:
            tier = max(1, min(4, trap.get("tier", 1)))
            by_tier[tier].append(trap)
        _TRAP_CACHE = by_tier
        return _TRAP_CACHE
    if data and "tiers" in data:
        result: Dict[int, List[dict]] = {}
        for tier_key, traps in data["tiers"].items():
            result[int(tier_key)] = traps
        _TRAP_CACHE = result
        return _TRAP_CACHE
    _TRAP_CACHE = {}
    return _TRAP_CACHE


_LOOT_POOL = _load_loot_pool()
_HAZARD_POOL = _load_hazard_pool()
_TRAP_POOL = _load_trap_pool()


class DnD5eAdapter:
    """RulesetAdapter for D&D 5e content injection into the Universal Map Engine."""

    def __init__(self, seed: Optional[int] = None, party_size: int = 1):
        self._rng = random.Random(seed)
        self._party_size = max(1, min(6, party_size))
        scale = DND5E_PARTY_SCALING.get(self._party_size, DND5E_PARTY_SCALING[1])
        self._hp_mult = scale["hp"]
        self._atk_mult = scale["atk"]

    def _make_enemy(self, tier: int) -> dict:
        """Create an enemy dict from bestiary data with party scaling."""
        bestiary = _load_bestiary()
        monsters = bestiary.get(tier, bestiary.get(1, []))
        entry = self._rng.choice(monsters) if monsters else {}
        name = entry.get("name", "Unknown")
        # Use bestiary base stats if available, otherwise random generation
        if "base_hp" in entry:
            hp = int(entry["base_hp"] * self._hp_mult)
            atk = int(entry["base_atk"] * self._atk_mult)
            ac = entry.get("base_ac", 10 + tier)
        else:
            base_hp = self._rng.randint(4 * tier, 10 * tier)
            hp = int(base_hp * self._hp_mult)
            atk = int((tier + self._rng.randint(1, 4)) * self._atk_mult)
            ac = 10 + tier
        return {
            "name": name, "hp": hp, "max_hp": hp,
            "attack": atk, "defense": ac, "tier": tier,
        }

    def populate_room(self, room) -> "PopulatedRoom":
        from codex.spatial.map_engine import PopulatedRoom, RoomType
        content: Dict[str, Any] = {}
        tier = max(1, min(4, room.tier))
        rtype = room.room_type

        # Description
        descs = {
            RoomType.NORMAL: [
                "A stone chamber with crumbling pillars.",
                "Torchlight flickers across damp walls.",
                "A musty room with a collapsed bookshelf.",
            ],
            RoomType.TREASURE: [
                "Glittering coins spill from a broken chest.",
                "A locked vault with arcane wards.",
            ],
            RoomType.BOSS: [
                "A vast hall echoing with an ancient presence.",
                "Bones crunch underfoot. Something waits here.",
            ],
            RoomType.START: [
                "The dungeon entrance. Daylight fades behind you.",
            ],
            RoomType.HIDDEN_PORTAL: [
                "The air hums with arcane resonance. A shimmering tear in reality hangs at eye level, edges crackling with pale fire.",
                "Ozone tang hits your tongue. A portal of swirling violet light hovers above a circle of runes.",
                "Visual distortion warps the far wall. Where stone should be, flickering images of somewhere else.",
                "A low thrum vibrates through your teeth. An archway of crystallized magic, surface rippling like water.",
            ],
        }
        pool = descs.get(rtype, descs[RoomType.NORMAL])
        content["description"] = self._rng.choice(pool)

        # Hidden Portal: no standard enemies/loot, optional single guardian
        if rtype == RoomType.HIDDEN_PORTAL:
            content["enemies"] = []
            content["loot"] = []
            content["hazards"] = []
            content["is_portal"] = True
            # 50% chance of a single guardian
            if self._rng.random() < 0.50:
                content["enemies"].append(self._make_enemy(tier))
            return PopulatedRoom(geometry=room, content=content)

        # Enemies (skip start rooms)
        content["enemies"] = []
        if rtype not in (RoomType.START,):
            count = self._rng.randint(0, 2) if rtype != RoomType.BOSS else self._rng.randint(1, 2)
            for _ in range(count):
                content["enemies"].append(self._make_enemy(tier))

        # Loot
        content["loot"] = []
        if rtype in (RoomType.TREASURE, RoomType.BOSS) or self._rng.random() < 0.3:
            loot_pool = _LOOT_POOL.get(tier, _LOOT_POOL[1])
            content["loot"].append({"name": self._rng.choice(loot_pool), "tier": tier})

        # Hazards
        content["hazards"] = []
        if self._rng.random() < 0.2:
            hazard_pool = _HAZARD_POOL.get(tier, _HAZARD_POOL[1])
            content["hazards"].append({"name": self._rng.choice(hazard_pool)})

        # Traps (not start rooms; higher chance in defended rooms with enemies)
        content["traps"] = []
        if rtype not in (RoomType.START,):
            trap_pool = _TRAP_POOL.get(tier, _TRAP_POOL.get(1, []))
            trap_chance = 0.30 if content["enemies"] else 0.15
            if trap_pool and self._rng.random() < trap_chance:
                content["traps"].append(self._rng.choice(trap_pool))

        return PopulatedRoom(geometry=room, content=content)

    def get_enemy_pool(self, tier: int) -> List[str]:
        return _ENEMY_POOL.get(max(1, min(4, tier)), _ENEMY_POOL[1])

    def get_loot_pool(self, tier: int) -> List[str]:
        return _LOOT_POOL.get(max(1, min(4, tier)), _LOOT_POOL[1])


# =========================================================================
# TRAIT RESOLVER
# =========================================================================

from codex.core.services.trait_handler import TraitResolver

_SKILL_ABILITIES = {
    "athletics": "strength",
    "acrobatics": "dexterity", "sleight_of_hand": "dexterity", "stealth": "dexterity",
    "arcana": "intelligence", "history": "intelligence", "investigation": "intelligence",
    "nature": "intelligence", "religion": "intelligence",
    "animal_handling": "wisdom", "insight": "wisdom", "medicine": "wisdom",
    "perception": "wisdom", "survival": "wisdom",
    "deception": "charisma", "intimidation": "charisma",
    "performance": "charisma", "persuasion": "charisma",
}


class DnD5eTraitResolver(TraitResolver):
    def resolve_trait(self, trait_id, context):
        from codex.core.dice import roll_dice
        skill = trait_id.lower()
        ability = _SKILL_ABILITIES.get(skill)
        if not ability:
            return {"success": False, "error": f"Unknown skill: {trait_id}"}
        char = context.get("character")
        if not char:
            return {"success": False, "error": "No character in context"}
        dc = context.get("dc", 10)
        prof = context.get("proficiency", False)
        _, rolls, _ = roll_dice("1d20")
        raw = rolls[0]
        mod = char.modifier(getattr(char, ability, 10))
        prof_bonus = char.proficiency_bonus if prof else 0
        total = raw + mod + prof_bonus
        return {"trait_id": trait_id, "skill": skill, "ability": ability,
                "roll": raw, "modifier": mod, "proficiency_bonus": prof_bonus,
                "total": total, "dc": dc, "success": total >= dc or raw == 20,
                "critical": raw == 20, "fumble": raw == 1}


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("dnd5e", DnD5eEngine)
except ImportError:
    pass

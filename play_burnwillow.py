#!/usr/bin/env python3
"""
play_burnwillow.py - The Interactive Burnwillow Game Loop
==========================================================

A terminal-based roguelike dungeon crawler powered by:
  - burnwillow_module.py (The Heart: dice, stats, gear, doom clock)
  - codex_map_engine.py (The Body: BSP dungeon generation)
  - codex_map_renderer.py (The Eyes: Rich spatial map rendering)

Game Loop: Init -> Render -> Input -> Logic -> (repeat)

Actions:
  Movement:   move <room_id>    - Move to a connected room (+1 Doom)
  Scout:      scout <room_id>   - Peek a room without entering (Wits vs DC 12, +1 Doom)
  Search:     search            - Thorough loot search (Wits vs DC 12, +1 Doom)
  Bind:       bind              - Heal ~50% max HP (+1 Doom)
  Attack:     attack <target>   - Fight an enemy (Might vs Defense)
  Loot:       loot              - Pick up items from the room
  Look:       look              - Re-examine the current room
  Inventory:  inv / inventory   - Show equipped gear and stats
  Map:        map               - Show the full dungeon map (debug)
  Help:       help              - Show available commands
  Quit:       quit              - End the game

Version: 1.2 (Omni-Channel Restoration)
"""

import copy
import os
import random
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich import box

# Local imports
from codex.paths import SAVES_DIR, STATE_DIR, safe_save_json
from codex.core.state_frame import build_state_frame, frame_to_json
from codex.games.burnwillow.engine import (
    BurnwillowEngine, Character, Minion, StatType, GearSlot, GearTier, GearItem,
    DoomClock, DC, CheckResult, calculate_stat_mod, roll_dice_pool, roll_ambush,
    create_starter_gear, create_minion, select_target_weighted,
)
from codex.spatial.map_engine import (
    CodexMapEngine, DungeonGraph, RoomNode, RoomType,
    BurnwillowAdapter, ContentInjector, PopulatedRoom,
)
from codex.spatial.map_renderer import (
    SpatialGridRenderer, SpatialRoom, RoomVisibility,
    MapTheme, THEMES, render_spatial_map, build_stats_sidebar,
    render_mini_map, rooms_to_minimap_dict,
)
from codex.core.registry import CommandRegistry, build_burnwillow_registry
from codex.core.encounters import EncounterEngine, EncounterContext, get_party_scaling
from codex.core.narrative_engine import NarrativeEngine, CampaignPhase
from codex.games.burnwillow.paper_doll import render_paper_doll, render_dual_backpack, render_item_detail
from codex.core.services.tutorial import PlatformTutorial
from codex.games.burnwillow.ui import RunStatistics, MetaUnlocks
from codex.games.burnwillow.ui import render_death_screen as render_death_screen_ui
from codex.forge.char_wizard import CharacterBuilderEngine, SystemBuilder
from codex.integrations.mimir import MimirAdapter
from codex.core.services.broadcast import GlobalBroadcastManager
from codex.games.burnwillow.autopilot import (
    AutopilotAgent, CompanionPersonality, create_ai_character,
    create_backfill_companions, select_ai_target, register_companion_as_npc,
    build_exploration_snapshot, build_combat_snapshot, build_hub_snapshot,
)


# =============================================================================
# CONSTANTS
# =============================================================================

VERSION = "1.2"
GAME_TITLE = "BURNWILLOW"
GAME_SUBTITLE = "You Are What You Wear"

# Theme
THEME = MapTheme.RUST
THEME_CFG = THEMES[THEME]

# Equip slot aliases (natural language -> GearSlot)
SLOT_ALIASES = {
    "left hand": GearSlot.L_HAND, "left": GearSlot.L_HAND, "off hand": GearSlot.L_HAND,
    "l hand": GearSlot.L_HAND, "lh": GearSlot.L_HAND, "l.hand": GearSlot.L_HAND,
    "right hand": GearSlot.R_HAND, "right": GearSlot.R_HAND, "main hand": GearSlot.R_HAND,
    "r hand": GearSlot.R_HAND, "rh": GearSlot.R_HAND, "r.hand": GearSlot.R_HAND,
    "head": GearSlot.HEAD, "chest": GearSlot.CHEST,
    "arms": GearSlot.ARMS, "legs": GearSlot.LEGS,
    "shoulders": GearSlot.SHOULDERS, "neck": GearSlot.NECK,
    "l.ring": GearSlot.L_RING, "r.ring": GearSlot.R_RING,
    "left ring": GearSlot.L_RING, "right ring": GearSlot.R_RING,
}

# WO-V61.0: Perception-time mood overlays
_MOOD_OVERLAYS = {
    "critical": [
        "Every shadow feels like a threat. Your hands won't stop shaking.",
        "The silence between heartbeats stretches. You taste iron.",
        "Your vision swims. One more hit and it's over.",
    ],
    "battered": [
        "You're running on borrowed time. The wounds are adding up.",
        "Sweat stings your eyes. Everything aches.",
        "Your grip on the weapon is slippery with blood.",
    ],
    "desperate": [
        "The Burnwillow groans around you. The rot is close.",
        "The air is thick and wrong. Something vast is stirring.",
        "Time is running out. You can feel it in your bones.",
    ],
}

# Defaults
DEFAULT_DUNGEON_DEPTH = 3
DEFAULT_DUNGEON_SEED = None  # Random each run

# Heal amount for Bind Wounds (percentage of max HP)
BIND_WOUNDS_HEAL_PERCENT = 0.50

# Search DC
SEARCH_DC = 12
SCOUT_DC = 12

# Adventure Log rolling buffer size
LOG_BUFFER_SIZE = 5

# Movement budget (WO: Movement Budget System)
TILE_SIZE_FT = 5        # Each grid tile = 5 feet
MOVE_BUDGET_FT = 30     # 30 feet of movement per exploration turn

# Turn-consuming commands: only explicit turn-enders (WO: Movement Budget)
TURN_CONSUMING_CMDS = frozenset({"end", "wait", "pass"})

# Doom rate multiplier by party size (WO-V32.0: 5+ players tick doom faster)
DOOM_RATE_MULT = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.1, 6: 1.2}


# =============================================================================
# GAME STATE
# =============================================================================

class GameState:
    """Holds all mutable game state for a single run."""

    def __init__(self):
        self.engine: Optional[BurnwillowEngine] = None
        self.console: Console = Console()
        self.running: bool = True
        self.turn_number: int = 0
        self.system_id: str = "burnwillow"
        self.dungeon_seed: Optional[int] = None

        # First-Strike Proficiency: +1d6 on very first attack of a run
        self.first_strike_used: bool = False

        # Run statistics (fed into death screen)
        self.enemies_slain: int = 0
        self.chests_opened: int = 0
        self.gold_collected: int = 0

        # Unified command registry (alias resolution for all interfaces)
        self.command_registry: CommandRegistry = build_burnwillow_registry()

        # Message Log (Persistent Buffer)
        self.message_log: List[str] = [
            f"Welcome to {GAME_TITLE}.",
            "Type 'help' for a list of commands."
        ]

        # Room content tracking
        self.room_enemies: Dict[int, List[dict]] = {}
        self.room_loot: Dict[int, List[dict]] = {}
        self.searched_rooms: set = set()
        self.scouted_rooms: set = set()
        self.cleared_rooms: set = set()

        # Room furniture / interactable objects (persisted)
        self.room_furniture: Dict[int, List[dict]] = {}

        # Spatial rooms cache for renderer
        self.spatial_rooms: Dict[int, SpatialRoom] = {}

        # Sidebar buffer (WO V20.3: persists until room transition or 'clear' command)
        self.sidebar_buffer: List[str] = []
        # Backward-compat alias
        self.sidebar_detail: Optional[str] = None
        # Sidebar scroll offset (0 = newest at bottom, >0 = scrolled back)
        self.sidebar_view_offset: int = 0

        # Pinned last action result (persists across frames until overwritten)
        self.last_action_result: Optional[str] = None

        # Cached exit labels for direction-based movement (e.g. "e1" -> room_id)
        self.cached_exit_labels: Dict[str, int] = {}

        # Multiplayer: active leader override for exploration
        self.active_leader_override: Optional[int] = None

        # Rot Hunter — roaming pursuer (spawns at Doom 20, WO-V17.0: was 10)
        self.rot_hunter: Optional[dict] = None

        # Wave spawn system (WO-V17.0)
        self.wave_spawns: Dict[int, List[dict]] = {}  # wave_id -> spawned entities
        self.wave_dormancy: Dict[int, int] = {}       # wave_id -> ticks until active
        self._wave_roam_counter: int = 0              # Counts doom ticks for slow roamers

        # Party & combat state
        self.active_character_index: int = 0
        self.combat_mode: bool = False
        self.combat_round: int = 0
        self.ambush_round: bool = False  # Party gets free round

        # Movement budget (WO: Movement Budget)
        self.remaining_movement: int = MOVE_BUDGET_FT
        self.action_taken: bool = False

        # Combat effect tracking (cleared each round)
        self.guarding: set = set()           # Character names currently guarding (+2 DEF)
        self.intercepting: Optional[str] = None  # Character name bracing to intercept
        self.bolster_targets: Dict[str, int] = {}  # char_name -> bonus dice count
        self.sanctified: bool = False        # Enemies take 1d6 at start of enemy phase

        # WO-V36.0: Expanded AoE state tracking
        self.stunned_enemies: Dict[str, int] = {}   # enemy_name -> rounds remaining (skip turn)
        self.blinded_enemies: Dict[str, int] = {}   # enemy_name -> rounds remaining (-2 attack)
        self.defense_debuffs: Dict[str, int] = {}   # enemy_name -> defense reduction from Snare
        self.party_dr_buff: Tuple[int, int] = (0, 0)  # (DR bonus, rounds remaining) from Aegis
        self.party_hot: Dict[str, int] = {}          # char_name -> rounds remaining for Renewal
        self.party_bonus_dice: Dict[str, int] = {}   # char_name -> bonus dice from Rally

        # Haven event bonuses (WO-V44.0)
        self.forge_bonus: int = 0        # Next forge upgrade discount
        self.shop_discount: int = 0      # Next shop purchase discount %

        # --- Broadcast Manager (WO-V45.0: NPC Memory wiring) ---
        self.broadcast_manager: GlobalBroadcastManager = GlobalBroadcastManager(system_theme="burnwillow")

        # --- Narrative Engine (Universal Adventure Module) ---
        self.narrative: Optional[NarrativeEngine] = None
        self.settlement_graph: Optional[DungeonGraph] = None
        self.settlement_rooms: Dict[int, SpatialRoom] = {}
        self.in_settlement: bool = False
        self.settlement_pos: Optional[Tuple[int, int]] = None
        self.dungeon_path: str = "descend"  # "descend" or "ascend"

        # Tutorial hint system (contextual tips for new players)
        self.tutorial: PlatformTutorial = PlatformTutorial()

        # Autopilot & Companion mode (WO-V31.0)
        self.autopilot_mode: bool = False
        self.companion_mode: bool = False
        self.autopilot_delay: float = 1.5
        self.autopilot_agents: Dict[str, AutopilotAgent] = {}

        # Doom rate scaling for larger parties (WO-V32.0)
        self.doom_rate_mult: float = 1.0
        self._doom_remainder: float = 0.0

        # Session chronicle (WO-V37.0: structured event log for recap)
        self.session_log: List[Dict[str, Any]] = []

        # WO-V61.0: Momentum ledger for trend tracking
        from codex.core.services.momentum import MomentumLedger
        self.momentum_ledger = MomentumLedger(universe_id="burnwillow")
        self.momentum_handler: Optional[Any] = None  # Initialized in game_loop

        # WO-V61.0: Anchor event tracking
        self._near_death_emitted: set = set()  # Character names already emitted near_death this combat
        self._max_tier_reached: int = 1  # Highest tier zone entered

        # World map & module manifest (Phase 3/6 spatial integration)
        self.world_map: Optional[Any] = None            # WorldMap instance
        self.current_location_id: Optional[str] = None  # Current world-map location
        self.visited_locations: Optional[set] = None    # Set of visited location IDs
        self.module_manifest: Optional[Any] = None      # ModuleManifest instance
        self.current_chapter_idx: int = 0               # Current chapter in module
        self.current_zone_idx: int = 0                  # Current zone in chapter

        # WO-V62.0: Session frame and expedition controls
        self.session_frame: Optional[Any] = None
        self.expedition_timer: Optional[Any] = None
        self._session_type: str = "campaign"
        self._willow_wood_save: Optional[dict] = None

    @property
    def character(self) -> Optional[Character]:
        """Returns the leader (first party member) for backward compat."""
        if self.engine and self.engine.party:
            return self.engine.party[0]
        if self.engine:
            return self.engine.character
        return None

    @property
    def active_leader(self) -> Optional[Character]:
        """Returns the current exploration leader (overridable via 'switch')."""
        if self.engine and self.engine.party:
            if self.active_leader_override is not None:
                party = self.engine.get_active_party()
                if 0 <= self.active_leader_override < len(party):
                    return party[self.active_leader_override]
            return self.engine.party[0]
        return self.character

    @property
    def active_character(self) -> Optional[Character]:
        """Returns the party member whose turn it currently is."""
        if self.engine and self.engine.party:
            alive = self.engine.get_active_party()
            if alive and self.active_character_index < len(alive):
                return alive[self.active_character_index]
            if alive:
                return alive[0]
        return self.character

    @property
    def current_room_id(self) -> Optional[int]:
        if self.engine:
            return self.engine.current_room_id
        return None

    @property
    def doom(self) -> int:
        if self.engine:
            return self.engine.doom_clock.current
        return 0

    def add_log(self, message: str):
        """Add a message to the persistent log."""
        self.message_log.append(message)

    def clear_combat_effects(self):
        """Reset per-round combat effects."""
        self.guarding.clear()
        self.intercepting = None
        self.bolster_targets.clear()
        self.sanctified = False
        # WO-V36.0: Decrement/expire AoE effects
        for name in list(self.stunned_enemies):
            self.stunned_enemies[name] -= 1
            if self.stunned_enemies[name] <= 0:
                del self.stunned_enemies[name]
        for name in list(self.blinded_enemies):
            self.blinded_enemies[name] -= 1
            if self.blinded_enemies[name] <= 0:
                del self.blinded_enemies[name]
        for name in list(self.defense_debuffs):
            # Snare lasts 1 round then clears
            self.defense_debuffs[name] -= 1
            if self.defense_debuffs[name] <= 0:
                del self.defense_debuffs[name]
        dr_val, dr_rounds = self.party_dr_buff
        if dr_rounds > 0:
            dr_rounds -= 1
            self.party_dr_buff = (dr_val, dr_rounds) if dr_rounds > 0 else (0, 0)
        for name in list(self.party_hot):
            self.party_hot[name] -= 1
            if self.party_hot[name] <= 0:
                del self.party_hot[name]
        self.party_bonus_dice.clear()

    def clear_volatile_state(self):
        """Reset all volatile/combat state — call on session start and load."""
        self.combat_mode = False
        self.combat_round = 0
        self.active_character_index = 0
        self.guarding = set()
        self.intercepting = None
        self.bolster_targets = {}
        self.sanctified = False
        self.ambush_round = False
        self.remaining_movement = MOVE_BUDGET_FT
        self.action_taken = False
        self.active_leader_override = None
        self.sidebar_buffer = []
        self.sidebar_detail = None
        self.sidebar_view_offset = 0
        self.last_action_result = None
        # WO-V36.0: Reset expanded AoE state
        self.stunned_enemies = {}
        self.blinded_enemies = {}
        self.defense_debuffs = {}
        self.party_dr_buff = (0, 0)
        self.party_hot = {}
        self.party_bonus_dice = {}
        self._near_death_emitted = set()

    def log_event(self, event_type: str, **kwargs):
        """Append a structured event to the session chronicle (WO-V37.0)."""
        self.session_log.append({"type": event_type, "turn": self.turn_number, **kwargs})
        # WO-V61.0: Record in momentum ledger + route to handler
        if self.momentum_ledger:
            location = getattr(self, 'current_location_id', None) or "burnwillow_depths"
            tier = kwargs.get("tier", 1)
            threshold_events = self.momentum_ledger.record_from_event(
                event_type, location, turn=self.turn_number, tier=tier,
            )
            if threshold_events and self.momentum_handler:
                messages = self.momentum_handler.handle(threshold_events)
                for msg in messages:
                    self.add_log(msg)

    def start_combat(self):
        """Enter combat mode."""
        self.combat_mode = True
        self.combat_round = 0
        self.active_character_index = 0
        self.first_strike_used = False  # Reset per-combat
        self.remaining_movement = MOVE_BUDGET_FT  # Fresh 30ft per combat
        self.clear_combat_effects()

    def end_combat(self):
        """Exit combat mode and clean up minions."""
        self.combat_mode = False
        self.combat_round = 0
        self.active_character_index = 0
        self.clear_combat_effects()
        self.reset_turn()
        # Remove expired minions
        if self.engine:
            for char in list(self.engine.party):
                if isinstance(char, Minion):
                    self.engine.remove_from_party(char)

    def push_sidebar(self, text: str):
        """Append content to the persistent sidebar buffer (WO V20.3)."""
        self.sidebar_buffer.append(text)
        # Cap at 25 entries to prevent unbounded growth
        if len(self.sidebar_buffer) > 25:
            self.sidebar_buffer = self.sidebar_buffer[-25:]
        # Auto-scroll to newest on new content
        self.sidebar_view_offset = 0

    def clear_sidebar(self):
        """Clear the sidebar buffer (called on room transition or 'clear' command)."""
        self.sidebar_buffer.clear()

    # --- Turn-based exploration system (WO V20.3) ---

    def is_party_turn_mode(self) -> bool:
        """True when turn-based exploration is active (party > 1, not in combat)."""
        if not self.engine or not self.engine.party:
            return False
        return len(self.engine.get_active_party()) > 1 and not self.combat_mode

    def get_turn_character(self) -> Optional[Character]:
        """Get the character whose turn it is (exploration or combat)."""
        if not self.engine:
            return None
        party = self.engine.get_active_party()
        if not party:
            return None
        idx = self.active_character_index % len(party)
        return party[idx]

    def advance_exploration_turn(self) -> Optional[str]:
        """Advance to the next party member's turn. Returns announcement or None."""
        if not self.is_party_turn_mode():
            return None
        party = self.engine.get_active_party()
        if len(party) <= 1:
            return None
        self.active_character_index = (self.active_character_index + 1) % len(party)
        next_char = party[self.active_character_index]
        return f"{next_char.name}'s turn."

    def reset_turn(self):
        """Reset movement budget and action flag for a new exploration turn."""
        self.remaining_movement = MOVE_BUDGET_FT
        self.action_taken = False

    def build_turn_tracker(self) -> str:
        """Build the turn tracker display for the sidebar."""
        if not self.engine or not self.engine.party:
            return ""
        party = self.engine.get_active_party()
        if len(party) <= 1:
            return ""
        lines = ["=== TURN ORDER ==="]
        for i, char in enumerate(party):
            marker = "> " if i == (self.active_character_index % len(party)) else "  "
            tag = "  [ACTIVE]" if i == (self.active_character_index % len(party)) else ""
            lines.append(f"{marker}{char.name} (HP {char.current_hp}/{char.max_hp}){tag}")
        # Show enemies in combat
        if self.combat_mode:
            enemies = self.room_enemies.get(self.current_room_id, [])
            if enemies:
                lines.append("---")
                for e in enemies:
                    lines.append(f"  {e['name']} ({e.get('hp', '?')} HP)")
        return "\n".join(lines)


# =============================================================================
# QUEST HELPERS (WO-V44.0)
# =============================================================================

def _get_room_tier(state: GameState, room_id: int = None) -> int:
    """Get the tier of the current or specified room."""
    if room_id is None:
        room_id = state.current_room_id
    if state.engine and state.engine.dungeon_graph:
        room_node = state.engine.dungeon_graph.rooms.get(room_id)
        if room_node:
            return room_node.tier
    return 1


def _check_quest_kill(state: GameState, room_id: int = None) -> List[str]:
    """Fire kill objective trigger and return quest messages."""
    if not state.narrative:
        return []
    tier = _get_room_tier(state, room_id)
    return state.narrative.check_objective(f"kill_tier_{tier}")


def _check_quest_loot(state: GameState, room_id: int = None) -> List[str]:
    """Fire loot objective trigger and return quest messages."""
    if not state.narrative:
        return []
    tier = _get_room_tier(state, room_id)
    return state.narrative.check_objective(f"loot_tier_{tier}")


def _check_quest_search(state: GameState, room_id: int = None) -> List[str]:
    """Fire search objective trigger and return quest messages."""
    if not state.narrative:
        return []
    tier = _get_room_tier(state, room_id)
    return state.narrative.check_objective(f"search_tier_{tier}")


def _apply_haven_event(state: GameState, event: dict) -> str:
    """Apply a haven event's mechanical effect. Returns description or empty string."""
    effect = event.get("effect")
    if not effect:
        return ""
    etype = effect.get("type", "")
    value = effect.get("value", 0)
    desc = effect.get("desc", "")

    if etype == "heal":
        if state.engine and state.engine.party:
            for char in state.engine.party:
                if hasattr(char, 'current_hp') and hasattr(char, 'max_hp'):
                    char.current_hp = min(char.current_hp + value, char.max_hp)
                elif hasattr(char, 'hp') and hasattr(char, 'max_hp'):
                    char.hp = min(char.hp + value, char.max_hp)
    elif etype == "doom":
        if state.engine and state.engine.doom_clock:
            state.engine.doom_clock.advance(value)
    elif etype == "forge_bonus":
        state.forge_bonus = value
    elif etype == "shop_discount":
        state.shop_discount = value

    return desc


def _grant_quest_item(state: GameState, reward: dict):
    """Add a quest reward item to the leader's inventory."""
    if not state.active_leader or not reward.get("item_name"):
        return
    item = GearItem(
        name=reward["item_name"],
        slot=GearSlot.R_HAND,
        tier=GearTier.TIER_I,
        description=reward.get("item_desc", "A quest reward."),
    )
    state.active_leader.add_to_inventory(item)


# =============================================================================
# EMBERHOME HUB
# =============================================================================

def _init_npc_memory(state: GameState):
    """Initialize NPC memory system and attach to narrative engine."""
    try:
        from codex.core.services.npc_memory import NPCMemoryManager
        cultural_values = []
        # Extract cultural values from world state if available
        try:
            from codex.core.world.grapes_engine import GrapesProfile
            world_file = STATE_DIR / "world_state.json"
            if world_file.exists():
                with open(world_file, "r") as f:
                    ws = json.load(f)
                grapes = ws.get("grapes", {})
                if isinstance(grapes, dict) and "culture" in grapes:
                    from codex.core.world.grapes_engine import CulturalValue
                    cultural_values = [
                        CulturalValue.from_dict(cv)
                        for cv in grapes["culture"]
                    ]
        except Exception:
            pass

        state._npc_memory = NPCMemoryManager(
            broadcast_manager=state.broadcast_manager,
            cultural_values=cultural_values,
        )
        state._npc_memory.load()
        if state.narrative:
            state.narrative.attach_npc_memory(state._npc_memory)
    except ImportError:
        pass

    # Wire Mimir adapter so NPC dialogue uses Ollama when available
    if state.narrative and state.narrative.mimir is None:
        state.narrative.mimir = MimirAdapter()


def _load_emberhome_settlement(state: GameState):
    """Load Emberhome settlement blueprint and build spatial rooms."""
    blueprint_path = Path(__file__).resolve().parent / "codex" / "spatial" / "blueprints" / "emberhome.json"
    if not blueprint_path.exists():
        return
    settlement_engine = CodexMapEngine(seed=0)
    state.settlement_graph = settlement_engine.load_blueprint(str(blueprint_path))
    # Build spatial rooms for rendering
    state.settlement_rooms = {}
    for room_id, room_node in state.settlement_graph.rooms.items():
        sr = SpatialRoom.from_map_engine_room(room_node)
        sr.visibility = RoomVisibility.VISITED
        state.settlement_rooms[room_id] = sr
    start_room = state.settlement_graph.rooms.get(state.settlement_graph.start_room_id)
    if start_room:
        state.settlement_pos = (start_room.x + start_room.width // 2,
                                start_room.y + start_room.height // 2)


def _get_settlement_room_at_pos(state: GameState) -> Optional[RoomNode]:
    """Return the settlement room the player is standing in."""
    if not state.settlement_graph or not state.settlement_pos:
        return None
    px, py = state.settlement_pos
    for room_node in state.settlement_graph.rooms.values():
        if (room_node.x <= px < room_node.x + room_node.width and
                room_node.y <= py < room_node.y + room_node.height):
            return room_node
    return None


def _handle_character_export(state: GameState):
    """Export current party leader to saves/characters/."""
    from codex.core.character_export import export_character, save_exported_character
    con = state.console
    char = state.character
    if not char:
        con.print("[dim]No character to export.[/dim]")
        return
    char_data = state.engine.save_game().get("party", [{}])[0] if state.engine else {}
    if not char_data:
        char_data = {"name": char.name, "max_hp": char.max_hp, "current_hp": char.current_hp}
    campaign_id = state.session_frame.campaign_id if state.session_frame else None
    exported = export_character(char_data, "burnwillow", campaign_id)
    path = save_exported_character(exported)
    con.print(f"[green]Character exported to {path.name}[/green]")


def _handle_character_import(state: GameState):
    """List available characters for import."""
    from codex.core.character_export import list_exported_characters
    con = state.console
    chars = list_exported_characters()
    if not chars:
        con.print("[dim]No exported characters found.[/dim]")
        return
    for i, c in enumerate(chars, 1):
        sys_id = c.get("system_id", "?")
        con.print(f"  [{i}] {c['name']} ({sys_id})")
    con.print("[dim]Character import into active sessions coming soon.[/dim]")


def _run_willow_wood(state: GameState, destination: str) -> str:
    """Navigate through Willow Wood between Emberhome and a destination gate."""
    from codex.spatial.willow_wood import WillowWoodZone
    import random as _random
    con = state.console

    session_num = state.session_frame.session_number if state.session_frame else 1

    # Build GRAPES health from momentum ledger
    grapes_health = {}
    if state.momentum_ledger:
        for cat in ("security", "economics", "politics", "religion", "geography", "social"):
            trend = state.momentum_ledger.get_dominant_trend("burnwillow_depths")
            if trend and trend[0] == cat:
                grapes_health[cat] = min(1.0, max(-1.0, trend[1] / 10.0))

    wood = WillowWoodZone(session_seed=session_num, grapes_health=grapes_health)
    wood.generate()

    # Load save state if any
    if state._willow_wood_save:
        wood.load_save_dict(state._willow_wood_save)

    # Get path rooms for this gate
    gate_id = destination  # "descent", "ascent", or "explore"
    path = wood.path_rooms(gate_id)
    if not path:
        con.print("[dim]The wood parts before you. The path is clear.[/dim]")
        state._willow_wood_save = wood.to_save_dict()
        return "continue"

    # Traverse landmark rooms then path rooms
    all_rooms = wood.landmark_rooms() + path
    for room in all_rooms:
        con.print(Panel(room.description, title=room.name, border_style="green"))

        # Roll encounter
        encounter = wood.roll_encounter(room.id, _random.Random(session_num + hash(str(room.id))))
        if encounter:
            approach_lines = []
            for i, (pillar, data) in enumerate(encounter.approaches.items(), 1):
                desc = data.get("description", pillar.title())
                approach_lines.append(f"  [{i}] [bold]{pillar.title()}[/]: {desc}")
            con.print(Panel(
                f"[bold]{encounter.name}[/bold]\n{encounter.description}\n\n"
                + "\n".join(approach_lines),
                title="Encounter", border_style="yellow",
            ))
            choice = Prompt.ask("Choose approach", console=con, default="1")
            try:
                idx = int(choice) - 1
                pillars = list(encounter.approaches.keys())
                pillar_key = pillars[idx] if 0 <= idx < len(pillars) else pillars[0]
                approach = encounter.approaches[pillar_key]
                outcome = approach.get("reward", "You proceed.")
                con.print(f"[green]{outcome}[/green]")
                state.log_event("wood_encounter", encounter=encounter.name, approach=pillar_key)
            except (ValueError, IndexError):
                con.print("[dim]You press on.[/dim]")

        # Check secrets — gated by skill checks
        secrets = wood.check_secrets(room.id, session_num)
        for secret in secrets:
            # Gate by drop_chance
            if secret.drop_chance > 0 and random.random() > secret.drop_chance:
                continue
            # Gate by DC — roll Wits check
            if secret.dc > 0:
                char = state.character
                if char:
                    stat = getattr(char, 'wits', 0)
                    roll = random.randint(1, 6) + random.randint(1, 6) + stat
                    if roll < secret.dc:
                        continue  # Failed the check — don't reveal
                    con.print(f"[dim]Wits check: {roll} vs DC {secret.dc} — Success![/dim]")
                else:
                    continue  # No character, skip DC-gated secrets
            con.print(f"[bold magenta]Secret: {secret.secret_type.replace('_', ' ').title()}[/bold magenta]")
            if secret.reward:
                con.print(f"  Reward: {secret.reward}")
            wood.discover_secret(secret.secret_type)
            state.log_event("wood_secret", secret_type=secret.secret_type)

        try:
            Prompt.ask("[dim]Press Enter to continue[/]", console=con, default="")
        except (EOFError, KeyboardInterrupt):
            state._willow_wood_save = wood.to_save_dict()
            return "abort"

    state._willow_wood_save = wood.to_save_dict()
    return "continue"


def _run_emberhome_hub(state: GameState):
    """Haven phase: navigate Emberhome as a spatial settlement map."""
    con = state.console
    state.in_settlement = True

    if not state.settlement_graph:
        _load_emberhome_settlement(state)
    if not state.settlement_graph:
        _run_emberhome_menu_fallback(state)
        return

    # Haven event on arrival (if returning from dungeon)
    if state.narrative and state.narrative.phase == CampaignPhase.AFTERMATH:
        event = state.narrative.roll_haven_event()
        if event:
            event_text = event.get("text", "") if isinstance(event, dict) else str(event)
            if event_text:
                con.print(Panel(event_text, title="Emberhome", border_style="dark_goldenrod"))
                # WO-V44.0: Apply mechanical effect
                effect_msg = _apply_haven_event(state, event)
                if effect_msg:
                    con.print(f"  [bold]{effect_msg}[/]")
                Prompt.ask("[dim]Press Enter[/]", console=con, default="")
        state.narrative.phase = CampaignPhase.HAVEN

    # Import SETTLEMENT_DESCRIPTIONS for room text
    try:
        from codex.core.narrative_content import SETTLEMENT_DESCRIPTIONS
    except ImportError:
        SETTLEMENT_DESCRIPTIONS = {}

    while True:
        con.clear()
        # Render settlement map using VILLAGE theme
        if state.settlement_rooms and state.settlement_pos:
            # Determine which settlement room the player is in
            _cur = _get_settlement_room_at_pos(state)
            _cur_id = _cur.id if _cur else state.settlement_graph.start_room_id
            layout = render_spatial_map(
                state.settlement_rooms,
                player_room_id=_cur_id,
                player_pos=state.settlement_pos,
                theme=MapTheme.VILLAGE,
            )
            con.print(layout)

        # Show current building info
        current_room = _get_settlement_room_at_pos(state)
        if current_room:
            rtype = current_room.room_type if isinstance(current_room.room_type, str) else current_room.room_type.value
            descs = SETTLEMENT_DESCRIPTIONS.get(rtype, [])
            desc = random.choice(descs) if descs else f"You stand in the {rtype.replace('_', ' ').title()}."
            con.print(f"\n  [bold dark_goldenrod]{rtype.replace('_', ' ').title()}[/]")
            con.print(f"  [dim]{desc}[/]")
            # Show NPCs at this location
            if state.narrative:
                npcs = state.narrative.get_npcs_at(rtype)
                for npc in npcs:
                    con.print(f"  [cyan]{npc.name}[/] ({npc.role}) — \"{npc.dialogue_greeting}\"")

        # Show active quests summary
        if state.narrative:
            active = state.narrative.get_active_quests()
            if active:
                con.print(f"\n  [bold]Active Quests:[/] {len(active)}")

        con.print(f"\n  [dim]Commands: n/s/e/w/ne/nw/se/sw (move), talk <name>, quest, rumor, companion, recap, save, descend/ascend (at Gate), quit[/]")

        # WO-V31.0: Autopilot hub interception
        if _should_autopilot(state):
            import time as _time
            snapshot = build_hub_snapshot(state)
            agent = next(iter(state.autopilot_agents.values()), None)
            if agent:
                raw = agent.decide_hub(snapshot)
                con.print(f"  [dim][AI: autopilot] {raw}[/dim]")
                _time.sleep(state.autopilot_delay * 0.5)
            else:
                raw = "descend"
        else:
            try:
                raw = Prompt.ask("[bold dark_goldenrod]>[/]", console=con, default="")
            except (EOFError, KeyboardInterrupt):
                state.running = False
                break

        cmd, args = parse_command(raw)
        if not cmd:
            continue

        _settlement_dir_map = {
            "n": "n", "s": "s", "e": "e", "w": "w",
            "north": "n", "south": "s", "east": "e", "west": "w",
            "ne": "ne", "nw": "nw", "se": "se", "sw": "sw",
            "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
        }
        if cmd in _settlement_dir_map:
            _move_settlement(state, _settlement_dir_map[cmd])

        elif cmd == "talk" and args:
            _settlement_talk(state, " ".join(args))
        elif cmd in ("quest", "journal", "quests"):
            _settlement_quest_log(state)
        elif cmd in ("status", "party"):
            _emberhome_party_status(state)
        elif cmd == "forge":
            _emberhome_forge(state)
        elif cmd == "companion":
            msgs = action_companion(state)
            for m in msgs:
                con.print(f"  {m}")
        elif cmd in ("rumor", "board", "rumors"):
            _settlement_rumor_board(state)
        elif cmd in ("descend", "ascend", "enter", "delve"):
            current_room = _get_settlement_room_at_pos(state)
            rtype = ""
            if current_room:
                rtype = current_room.room_type if isinstance(current_room.room_type, str) else current_room.room_type.value
            if rtype == "town_gate":
                # Offer path choice
                con.print("\n  [bold]THE GATE[/]")
                con.print("  Two paths diverge from Emberhome:\n")
                con.print("  [1] [red]DESCEND[/] -- Into the roots. Corruption festers below.")
                con.print("      [dim]Purge the Rot Heart. End the Blight.[/]")
                con.print("  [2] [yellow]ASCEND[/] -- Into the canopy. The fire grows dim.")
                con.print("      [dim]Harvest the Burnwillow Sap. Fuel the flame.[/]")
                con.print("")
                path = Prompt.ask("  Choose your path", console=con,
                                  choices=["1", "2", "back"], default="back")
                if path in ("1", "2"):
                    state.dungeon_path = "descend" if path == "1" else "ascend"
                    # WO-V62.0: Willow Wood overworld traversal
                    destination = "descent" if path == "1" else "ascent"
                    wood_result = _run_willow_wood(state, destination)
                    if wood_result == "abort":
                        continue  # Player returned to Emberhome
                    state.in_settlement = False
                    if state.narrative:
                        state.narrative.phase = CampaignPhase.DELVE
                    break
            else:
                con.print("[dim]You must be at the Town Gate to depart.[/]")
        elif cmd == "tutorial":
            try:
                from codex.core.services.tutorial import TutorialBrowser
                import codex.core.services.tutorial_content  # noqa: F401
                browser = TutorialBrowser(tutorial=state.tutorial, system_filter="burnwillow")
                browser.run_loop(con)
            except Exception:
                con.print("  [dim]Tutorial unavailable.[/]")
        elif cmd == "recap":
            msgs = action_recap(state)
            for m in msgs:
                con.print(f"  {m}")
            Prompt.ask("[dim]Press Enter[/]", console=con, default="")
        elif cmd == "save":
            msgs = action_save(state)
            for m in msgs:
                con.print(f"  {m}")
            Prompt.ask("[dim]Press Enter[/]", console=con, default="")
        elif cmd in ("quit", "q"):
            state.running = False
            break
        elif cmd == "export":
            _handle_character_export(state)
            Prompt.ask("[dim]Press Enter[/]", console=con, default="")
        elif cmd == "import":
            _handle_character_import(state)
            Prompt.ask("[dim]Press Enter[/]", console=con, default="")
        elif cmd == "wood":
            _run_willow_wood(state, "explore")


def _move_settlement(state: GameState, direction: str):
    """Move to the nearest connected room in the given direction.

    Settlement navigation is room-to-room, not pixel-by-pixel.
    From the current room, find the best neighbor in the desired direction.
    Uses dot-product scoring so diagonal rooms are reachable.
    """
    if not state.settlement_pos or not state.settlement_graph:
        return
    current_room = _get_settlement_room_at_pos(state)
    if not current_room:
        # Player is in a corridor — snap to nearest room
        best_dist = float("inf")
        best_room = None
        px, py = state.settlement_pos
        for room in state.settlement_graph.rooms.values():
            cx = room.x + room.width // 2
            cy = room.y + room.height // 2
            d = abs(cx - px) + abs(cy - py)
            if d < best_dist:
                best_dist = d
                best_room = room
        if best_room:
            state.settlement_pos = (best_room.x + best_room.width // 2,
                                    best_room.y + best_room.height // 2)
        return

    # Direction vectors (8-way)
    dir_map = {
        "n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0),
        "ne": (1, -1), "nw": (-1, -1), "se": (1, 1), "sw": (-1, 1),
    }
    dvec = dir_map.get(direction)
    if dvec is None:
        return
    dx, dy = dvec

    cur_cx = current_room.x + current_room.width // 2
    cur_cy = current_room.y + current_room.height // 2

    # Search connected rooms for best match using dot-product alignment
    best_room = None
    best_score = -1.0
    for conn_id in current_room.connections:
        neighbor = state.settlement_graph.rooms.get(conn_id)
        if not neighbor:
            continue
        ncx = neighbor.x + neighbor.width // 2
        ncy = neighbor.y + neighbor.height // 2
        rel_x = ncx - cur_cx
        rel_y = ncy - cur_cy
        dist = (rel_x ** 2 + rel_y ** 2) ** 0.5
        if dist == 0:
            continue
        # Dot product of direction vector and relative vector (normalized)
        dot = (dx * rel_x + dy * rel_y) / dist
        if dot <= 0:
            continue  # Room is behind us
        # Score: higher dot = more aligned, penalize distance
        score = dot / (dist + 1)
        if score > best_score:
            best_score = score
            best_room = neighbor

    if best_room:
        state.settlement_pos = (best_room.x + best_room.width // 2,
                                best_room.y + best_room.height // 2)
        # TTS: narrate settlement room entry
        if hasattr(state, 'butler') and state.butler and hasattr(state.butler, 'narrate'):
            try:
                rtype = best_room.room_type if isinstance(best_room.room_type, str) else best_room.room_type.value
                room_label = best_room.label if hasattr(best_room, 'label') and best_room.label else rtype.replace("_", " ").title()
                state.butler.narrate(room_label)
            except Exception:
                pass
    else:
        state.console.print("[dim]Nothing that way.[/]")


def _settlement_talk(state: GameState, raw_input: str):
    """Talk to a named NPC in the current settlement building.

    Supports both ``talk <name>`` (greeting) and ``talk <name> <message>``
    (conversational dialogue via Mimir).  Name resolution uses longest-prefix
    matching against known NPCs at the current location.
    """
    con = state.console
    if not state.narrative:
        con.print("[dim]No one to talk to.[/]")
        return
    current_room = _get_settlement_room_at_pos(state)
    if not current_room:
        return
    rtype = current_room.room_type if isinstance(current_room.room_type, str) else current_room.room_type.value
    npcs = state.narrative.get_npcs_at(rtype)
    # Also include party companions (they follow you everywhere)
    party_npcs = [n for n in state.narrative.npcs if n.location == "party"]
    npcs = npcs + party_npcs

    # Longest-prefix match: try to split raw_input into (npc_name, message)
    target = None
    player_message = ""
    input_lower = raw_input.lower()

    # Sort NPC names longest-first so multi-word names match before shorter ones
    for npc in sorted(npcs, key=lambda n: len(n.name), reverse=True):
        npc_lower = npc.name.lower()
        if input_lower.startswith(npc_lower):
            target = npc
            remainder = raw_input[len(npc.name):].strip()
            player_message = remainder
            break

    # Fallback: original fuzzy substring match (single-word names, partial match)
    if not target:
        for npc in npcs:
            if input_lower in npc.name.lower() or npc.name.lower() in input_lower:
                target = npc
                # Try to extract message after the matched name
                idx = input_lower.find(npc.name.lower())
                if idx >= 0:
                    after = raw_input[idx + len(npc.name):].strip()
                    player_message = after
                break

    if not target:
        con.print(f"[dim]No one named '{raw_input}' is here.[/]")
        return

    dialogue = state.narrative.talk_to_npc(target.name, player_message=player_message)
    con.print(f"\n  [bold cyan]{target.name}[/] ({target.role})")
    con.print(f'  {dialogue}')

    # WO-V44.0: Check if this NPC has completable quests to turn in
    from codex.core.quest_rewards import materialize_reward, format_reward_panel
    completable = [q for q in state.narrative.quests
                   if q.status == "complete" and q.turn_in_npc == target.role]
    if completable:
        con.print(f"\n  [cyan]{target.name} notices you've completed their request.[/]")
        for q in completable:
            con.print(f"    [bold]{q.title}[/]")
            accept = Prompt.ask("  Turn in? [y/n]", console=con, default="y")
            if accept.lower() == "y":
                msg, reward = state.narrative.turn_in_quest(q.quest_id)
                concrete = materialize_reward(
                    reward,
                    setting_id=getattr(state, 'system_id', 'burnwillow'),
                    tier=q.tier_hint,
                )
                state.gold_collected += concrete.get("gold", 0)
                if concrete.get("item_name"):
                    _grant_quest_item(state, concrete)
                con.print(f"  [green]{msg}[/]")
                con.print(f"  {format_reward_panel(concrete)}")
                # WO-V50.0: Narrate quest turn-in
                if hasattr(state, 'butler') and state.butler and hasattr(state.butler, 'narrate'):
                    try:
                        state.butler.narrate(f"Quest complete. {q.title}.")
                    except Exception:
                        pass
                # WO-V45.0: Broadcast quest turn-in for NPC memory
                state.broadcast_manager.broadcast("HIGH_IMPACT_DECISION", {
                    "_event_type": "HIGH_IMPACT_DECISION",
                    "event_tag": "quest_turned_in",
                    "category": "security",
                    "summary": f"Completed '{q.title}'.",
                })
                # WO-V61.0: faction_shift anchor on quest completion
                state.log_event("faction_shift", npc_name=target.name,
                                old_tier="neutral", new_tier="friendly")
                _broadcast_anchor(state, "faction_shift", npc_name=target.name,
                                  old_tier="neutral", new_tier="friendly")
                # WO-V56.0: Memory shard for quest completion
                mem = getattr(state.engine, 'memory_engine', None)
                if mem:
                    mem.create_shard(
                        f"Completed quest: {q.title}",
                        shard_type="ANCHOR",
                        tags=["quest", q.quest_id],
                    )

    # WO-V44.0: Disposition-gated bonus dialogue
    if target.disposition >= 2 and not player_message:
        if target.dialogue_rumor:
            con.print(f"\n  [dim italic]{target.name} leans closer...[/]")
            con.print(f'  [dim]"{target.dialogue_rumor}"[/]')

    # TTS hook: narrate NPC dialogue
    if hasattr(state, 'butler') and state.butler:
        try:
            if hasattr(state.butler, 'narrate'):
                state.butler.narrate(dialogue)
        except Exception:
            pass

    Prompt.ask("[dim]Press Enter[/]", console=con, default="")


def _settlement_rumor_board(state: GameState):
    """WO-V45.0: Rumor board — generates a Mimir quest when online, or shows nothing."""
    con = state.console
    if not state.narrative:
        con.print("  [dim]The rumor board is empty.[/]")
        Prompt.ask("[dim]Press Enter[/]", console=con, default="")
        return

    con.print("\n  [bold]RUMOR BOARD[/]")
    con.print("  [dim]Whispers pinned to weathered cork...[/]\n")

    # Try Mimir-generated quest
    quest = state.narrative.generate_mimir_quest(tier=state.narrative.chapter)
    if quest:
        con.print(f"  [yellow]{quest.title}[/]")
        con.print(f"  {quest.description}")
        accept = Prompt.ask("  Accept this quest? [y/n]", console=con, default="y")
        if accept.lower() == "y":
            msg = state.narrative.accept_quest(quest.quest_id)
            con.print(f"  [green]{msg}[/]")
            state.broadcast_manager.broadcast("CIVIC_EVENT", {
                "_event_type": "CIVIC_EVENT",
                "event_tag": "quest_accepted",
                "category": "security",
                "summary": f"Accepted '{quest.title}' from the rumor board.",
            })
        else:
            con.print("  [dim]You leave the notice.[/]")
    else:
        con.print("  [dim]Nothing of interest today.[/]")

    Prompt.ask("[dim]Press Enter[/]", console=con, default="")


def _settlement_quest_log(state: GameState):
    """Display active, completable, and available quests with turn-in."""
    from codex.core.quest_rewards import materialize_reward, format_reward_panel

    con = state.console
    if not state.narrative:
        con.print("[dim]No quest log available.[/]")
        return

    active = [q for q in state.narrative.get_active_quests() if q.status == "active"]
    completed = [q for q in state.narrative.quests if q.status == "complete"]
    available = state.narrative.get_available_quests()

    con.print("\n  [bold]QUEST LOG[/]")

    # Active quests with progress
    if active:
        con.print("  [bold yellow]Active:[/]")
        for q in active:
            tag = "[red]MAIN[/]" if q.quest_type == "main" else "[dim]SIDE[/]"
            progress_str = ""
            if q.progress_target > 1:
                progress_str = f" [{q.progress}/{q.progress_target}]"
            con.print(f"    {tag} [yellow]{q.title}[/]{progress_str} -- {q.objective}")

    # Completed quests ready for turn-in
    if completed:
        con.print("  [bold cyan]Ready to Turn In:[/]")
        for i, q in enumerate(completed, 1):
            tag = "[red]MAIN[/]" if q.quest_type == "main" else "[dim]SIDE[/]"
            con.print(f"    [{i}] {tag} [cyan]{q.title}[/]")
        choice = Prompt.ask("  Turn in # (or Enter to skip)", console=con, default="")
        if choice.isdigit() and 1 <= int(choice) <= len(completed):
            quest = completed[int(choice) - 1]
            msg, reward = state.narrative.turn_in_quest(quest.quest_id)
            concrete = materialize_reward(
                reward,
                setting_id=getattr(state, 'system_id', 'burnwillow'),
                tier=quest.tier_hint,
            )
            state.gold_collected += concrete.get("gold", 0)
            if concrete.get("item_name"):
                _grant_quest_item(state, concrete)
            con.print(f"  [green]{msg}[/]")
            con.print(f"  {format_reward_panel(concrete)}")
            # WO-V50.0: Narrate quest turn-in
            if hasattr(state, 'butler') and state.butler and hasattr(state.butler, 'narrate'):
                try:
                    state.butler.narrate(f"Quest complete. {quest.title}.")
                except Exception:
                    pass
            # WO-V45.0: Broadcast quest turn-in for NPC memory
            state.broadcast_manager.broadcast("HIGH_IMPACT_DECISION", {
                "_event_type": "HIGH_IMPACT_DECISION",
                "event_tag": "quest_turned_in",
                "category": "security",
                "summary": f"Completed '{quest.title}'.",
            })

    # Available quests to accept
    if available:
        con.print("  [bold green]Available:[/]")
        for i, q in enumerate(available, 1):
            tag = "[red]MAIN[/]" if q.quest_type == "main" else "[dim]SIDE[/]"
            con.print(f"    [{i}] {tag} {q.title} -- {q.description}")
        choice = Prompt.ask("  Accept quest # (or Enter to skip)", console=con, default="")
        if choice.isdigit() and 1 <= int(choice) <= len(available):
            accepted_quest = available[int(choice) - 1]
            msg = state.narrative.accept_quest(accepted_quest.quest_id)
            con.print(f"  [green]{msg}[/]")
            # WO-V45.0: Broadcast quest acceptance for NPC memory
            state.broadcast_manager.broadcast("CIVIC_EVENT", {
                "_event_type": "CIVIC_EVENT",
                "event_tag": "quest_accepted",
                "category": "security",
                "summary": f"Accepted '{accepted_quest.title}'.",
            })

    if not active and not available and not completed:
        con.print("  [dim]No quests at this time.[/]")
    Prompt.ask("[dim]Press Enter[/]", console=con, default="")


def _run_emberhome_menu_fallback(state: GameState):
    """Fallback: old menu-based Emberhome if no blueprint loaded."""
    con = state.console
    party = state.engine.party

    while True:
        con.clear()
        hub_text = Text()
        hub_text.append("\n  EMBERHOME\n", style=f"bold {THEME_CFG.color_current}")
        hub_text.append("  The last warm light before the deep.\n\n", style="dim white")
        hub_text.append(f"  {party[0].name} stands at the mouth of the Burnwillow.\n", style="white")
        hub_text.append("  A lantern flickers at the threshold.\n", style="dim white")
        con.print(Panel(hub_text, border_style=THEME_CFG.color_current, box=box.DOUBLE))

        con.print(f"\n  [yellow]1[/] Descend into the Burnwillow")
        con.print(f"  [yellow]2[/] Party Status")
        con.print(f"  [yellow]3[/] The Forge  [dim](Repair Gear)[/]")
        con.print(f"  [yellow]4[/] Decipher Blueprints  [dim](Memory Seeds)[/]")

        choice = Prompt.ask("\n  [bold]Choose[/]", console=con, default="1")

        if choice == "1":
            break
        elif choice == "2":
            _emberhome_party_status(state)
        elif choice == "3":
            _emberhome_forge(state)
        elif choice == "4":
            _emberhome_decipher(state)


def _emberhome_party_status(state: GameState):
    """Show party stats and equipped gear at Emberhome."""
    con = state.console
    for char in state.engine.party:
        lines = Text()
        lines.append(f"{char.name}\n", style="bold yellow")
        lines.append(f"  HP: {char.current_hp}/{char.max_hp}  ", style="white")
        lines.append(f"MIG:{char.might} WIT:{char.wits} GRT:{char.grit} AET:{char.aether}\n", style="dim cyan")
        for slot, item in char.gear.slots.items():
            if item:
                lines.append(f"  [{slot.value}] {item.name} (T{item.tier.value})\n", style="dim cyan")
        con.print(Panel(lines, border_style="yellow"))
    Prompt.ask("[dim]Press Enter to return[/]", console=con, default="")


def _emberhome_forge(state: GameState):
    """Forge stub — awaiting Scrap resource system."""
    state.console.print(Panel(
        "[dim]The Forge smolders quietly. No Scrap available.\n"
        "Find Scrap in the dungeon to repair damaged gear.[/]",
        title="The Forge", border_style="red"))
    Prompt.ask("[dim]Press Enter to return[/]", console=state.console, default="")


def _emberhome_decipher(state: GameState):
    """Decipher stub — awaiting Memory Seed system."""
    state.console.print(Panel(
        "[dim]The deciphering table sits empty. No Memory Seeds found.\n"
        "Rare and Epic seeds must be deciphered here before use.[/]",
        title="Decipher Blueprints", border_style="magenta"))
    Prompt.ask("[dim]Press Enter to return[/]", console=state.console, default="")


# =============================================================================
# CHARACTER WIZARD
# =============================================================================

def _run_character_wizard(console: Console, party_size: int) -> Optional[List[tuple]]:
    """Run the CharacterWizard for each party member.

    Returns a list of (name, stats_dict, loadout_id) tuples, or None if the
    vault/burnwillow/creation_rules.json is missing.
    """
    try:
        cbe = CharacterBuilderEngine()
        schema = cbe.get_system("burnwillow")
        if not schema:
            return None
    except Exception:
        return None

    results = []
    for i in range(party_size):
        if party_size > 1:
            console.print(f"\n[bold]Character {i + 1} of {party_size}[/]")
        builder = SystemBuilder(schema, console)
        sheet = builder.run()
        name = sheet.name or f"Wanderer_{i + 1}"
        stats = dict(sheet.stats) if sheet.stats else {}
        loadout_choice = sheet.choices.get("loadout", {})
        loadout_id = loadout_choice.get("id", "sellsword") if isinstance(loadout_choice, dict) else "sellsword"
        results.append((name, stats, loadout_id))
    return results


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_game(state: GameState, names: List[str], seed: Optional[int] = None,
              char_specs: Optional[List[tuple]] = None):
    """Set up a new game run: engine, party, dungeon, starter gear.

    Args:
        names: List of character names (1-6). Solo = 1 name.
        seed: Optional dungeon seed.
        char_specs: Optional list of (name, stats_dict, loadout_id) from wizard.
                    When provided, uses precise stats + loadout instead of random.
    """
    state.engine = BurnwillowEngine()

    if char_specs:
        # Wizard path: create characters with explicit stats + loadouts
        for i, (name, stats, loadout_id) in enumerate(char_specs):
            if stats:
                state.engine.create_character_with_stats(
                    name,
                    might=stats.get("Might", 10),
                    wits=stats.get("Wits", 10),
                    grit=stats.get("Grit", 10),
                    aether=stats.get("Aether", 10),
                )
            else:
                state.engine.create_character(name)
            if i == 0:
                state.engine.party = [state.engine.character]
            else:
                state.engine.party.append(state.engine.character)
            state.engine.equip_loadout(loadout_id)
        state.engine.character = state.engine.party[0]
        state.engine.party[0].keys = 1
    else:
        # Quick Start path: random stats + inline loadout picker
        state.engine.create_party(names)
        starter = create_starter_gear()
        # starter: [0] Rusted Shortsword, [1] Padded Jerkin, [2] Old Oak Wand,
        #          [3] Burglar's Gloves, [4] Pot Lid Shield

        party = state.engine.party
        party_size = len(party)

        if party_size == 1:
            # Solo class picker - "You Are What You Wear"
            state.console.print("\n[bold]Choose your loadout:[/]")
            state.console.print("  [yellow]1[/] The Sellsword  - Sword + Jerkin + Gloves [Lockpick]")
            state.console.print("  [yellow]2[/] The Occultist  - Wand + Bell [Summon] + Jerkin")
            state.console.print("  [yellow]3[/] The Sentinel   - Sword + Shield [Intercept] + Jerkin")
            choice = Prompt.ask("  Loadout", choices=["1", "2", "3"], default="1", console=state.console)
            if choice == "2":
                party[0].gear.equip(starter[2])  # Old Oak Wand (R.Hand)
                party[0].gear.equip(starter[5])  # Beckoning Bell (L.Hand) [Summon]
                party[0].gear.equip(starter[1])  # Padded Jerkin (Chest)
            elif choice == "3":
                party[0].gear.equip(starter[0])  # Rusted Shortsword (R.Hand)
                party[0].gear.equip(starter[4])  # Pot Lid Shield (L.Hand) [Intercept]
                party[0].gear.equip(starter[1])  # Padded Jerkin (Chest)
            else:
                party[0].gear.equip(starter[0])  # Rusted Shortsword (R.Hand)
                party[0].gear.equip(starter[1])  # Padded Jerkin (Chest)
                party[0].gear.equip(starter[3])  # Burglar's Gloves (Arms) [Lockpick]
            party[0].keys = 1
        else:
            # Char 1 (Fighter): Sword + Jerkin
            party[0].gear.equip(starter[0])  # Rusted Shortsword
            party[0].gear.equip(starter[1])  # Padded Jerkin
            party[0].keys = 1
            # Char 2 (Support): Gloves + Shield
            if party_size >= 2:
                party[1].gear.equip(starter[3])  # Burglar's Gloves [Lockpick]
                party[1].gear.equip(starter[4])  # Pot Lid Shield [Intercept]
            # Char 3+ (Caster/Extra): Wand + Bell
            if party_size >= 3:
                party[2].gear.equip(starter[2])  # Old Oak Wand (R.Hand)
                party[2].gear.equip(starter[5])  # Beckoning Bell (L.Hand) [Summon]
            if party_size >= 4:
                # 4th member gets jerkin copy for survivability
                party[3].gear.equip(GearItem(
                    name="Tattered Robe",
                    slot=GearSlot.CHEST,
                    tier=GearTier.TIER_I,
                    damage_reduction=1,
                    description="A threadbare robe. Better than nothing."
                ))
            if party_size >= 5:
                # 5th member (Commander): Warhorn [Command] + Tattered Robe
                party[4].gear.equip(GearItem(
                    name="Warhorn",
                    slot=GearSlot.L_HAND,
                    tier=GearTier.TIER_I,
                    special_traits=["[Command]"],
                    description="Battered brass horn. Shout orders to rally allies."
                ))
                party[4].gear.equip(GearItem(
                    name="Tattered Robe",
                    slot=GearSlot.CHEST,
                    tier=GearTier.TIER_I,
                    damage_reduction=1,
                    description="A threadbare robe. Better than nothing."
                ))
            if party_size >= 6:
                # 6th member (Medic): Healer's Satchel [Triage] + Tattered Robe
                party[5].gear.equip(GearItem(
                    name="Healer's Satchel",
                    slot=GearSlot.ARMS,
                    tier=GearTier.TIER_I,
                    special_traits=["[Triage]"],
                    description="Bandages and salves. Wits-based healing."
                ))
                party[5].gear.equip(GearItem(
                    name="Tattered Robe",
                    slot=GearSlot.CHEST,
                    tier=GearTier.TIER_I,
                    damage_reduction=1,
                    description="A threadbare robe. Better than nothing."
                ))

    # WO-V61.0: Momentum ledger for trend tracking
    from codex.core.services.momentum import MomentumLedger
    state.momentum_ledger = MomentumLedger(universe_id="burnwillow")

    # --- Narrative Engine (Universal Adventure Module) ---
    state.narrative = NarrativeEngine(system_id=state.system_id or "burnwillow")
    # WO-V56.0: Wire _engine_ref — unlocks DeltaTracker + memory shard injection
    state.narrative._engine_ref = state.engine
    # WO-V56.0: Wire memory engine for ANCHOR shard injection into Mimir prompts
    try:
        from codex.core.memory import CodexMemoryEngine
        state.engine.memory_engine = CodexMemoryEngine()
    except ImportError:
        state.engine.memory_engine = None
    _load_emberhome_settlement(state)
    _init_npc_memory(state)

    # --- Emberhome Hub (pre-dungeon staging) ---
    _run_emberhome_hub(state)

    if not state.running:
        return {"seed": 0, "total_rooms": 0, "start_room": 0}

    # Generate dungeon based on path choice
    dungeon_seed = seed if seed is not None else random.randint(0, 999999)
    state.dungeon_seed = dungeon_seed

    if state.dungeon_path == "ascend":
        # Vertical canopy dungeon
        if not state.engine.map_engine:
            state.engine.map_engine = CodexMapEngine(seed=state.dungeon_seed or 0)
        state.engine.dungeon_graph = state.engine.map_engine.generate_vertical(
            floors=6, rooms_per_floor=2,
            floor_width=30, floor_height=8,
            system_id=state.system_id or "burnwillow",
        )
        state.engine.dungeon_graph.seed = dungeon_seed
        state.engine.seed = dungeon_seed
        state.engine.current_room_id = state.engine.dungeon_graph.start_room_id
        if state.engine.dungeon_graph.start_room_id in state.engine.dungeon_graph.rooms:
            start_room = state.engine.dungeon_graph.rooms[state.engine.dungeon_graph.start_room_id]
            state.engine.player_pos = (
                start_room.x + start_room.width // 2,
                start_room.y + start_room.height // 2,
            )
        state.engine.populate_dungeon_canopy()
        summary = {
            "seed": dungeon_seed,
            "total_rooms": len(state.engine.dungeon_graph.rooms),
            "start_room": state.engine.dungeon_graph.start_room_id,
        }
    else:
        # Default BSP descending dungeon
        summary = state.engine.generate_dungeon(depth=DEFAULT_DUNGEON_DEPTH, seed=dungeon_seed)

    # Archive seed for the Librarian's Seed Vault
    _archive_dungeon_seed(state, dungeon_seed, summary)

    # Initialize room content tracking from populated rooms
    for room_id, pop_room in state.engine.populated_rooms.items():
        content = pop_room.content
        state.room_enemies[room_id] = list(content.get("enemies", []))
        state.room_loot[room_id] = list(content.get("loot", []))
        state.room_furniture[room_id] = list(content.get("furniture", []))

    # WO-V32.0: Scale pre-populated enemies by party size
    _scaling = get_party_scaling(len(state.engine.party))
    for enemies in state.room_enemies.values():
        for e in enemies:
            e["hp"] = max(1, int(e.get("hp", 1) * _scaling["hp_mult"]))
            if "max_hp" in e:
                e["max_hp"] = max(1, int(e["max_hp"] * _scaling["hp_mult"]))
            e["_dmg_mult"] = _scaling["dmg_mult"]

    # Set doom rate multiplier for this party size
    state.doom_rate_mult = DOOM_RATE_MULT.get(len(state.engine.party), 1.0)

    # Build spatial rooms for renderer
    _rebuild_spatial_rooms(state)

    return summary


def init_game_with_characters(state: GameState, characters, seed=None):
    """Init game with pre-built Character objects from the adapter.

    Skips stat rolling, name prompts, and loadout selection. Characters
    arrive fully formed with stats, HP, and gear already set.

    Args:
        state: GameState to populate.
        characters: List of Character objects (1-6).
        seed: Optional dungeon seed.
    """
    state.engine = BurnwillowEngine()
    state.engine.party = list(characters)
    state.engine.character = state.engine.party[0]

    # Ensure lead has at least 1 key
    if state.engine.party[0].keys < 1:
        state.engine.party[0].keys = 1

    # WO-V61.0: Momentum ledger for trend tracking
    from codex.core.services.momentum import MomentumLedger
    state.momentum_ledger = MomentumLedger(universe_id="burnwillow")

    # --- Narrative Engine + Emberhome Hub ---
    state.narrative = NarrativeEngine(system_id=state.system_id or "burnwillow")
    _load_emberhome_settlement(state)
    _init_npc_memory(state)
    _run_emberhome_hub(state)

    if not state.running:
        return {"seed": 0, "total_rooms": 0, "start_room": 0}

    # Generate dungeon based on path choice
    dungeon_seed = seed if seed is not None else random.randint(0, 999999)
    state.dungeon_seed = dungeon_seed

    if state.dungeon_path == "ascend":
        # Vertical canopy dungeon
        if not state.engine.map_engine:
            state.engine.map_engine = CodexMapEngine(seed=state.dungeon_seed or 0)
        state.engine.dungeon_graph = state.engine.map_engine.generate_vertical(
            floors=6, rooms_per_floor=2,
            floor_width=30, floor_height=8,
            system_id=state.system_id or "burnwillow",
        )
        state.engine.dungeon_graph.seed = dungeon_seed
        state.engine.seed = dungeon_seed
        state.engine.current_room_id = state.engine.dungeon_graph.start_room_id
        if state.engine.dungeon_graph.start_room_id in state.engine.dungeon_graph.rooms:
            start_room = state.engine.dungeon_graph.rooms[state.engine.dungeon_graph.start_room_id]
            state.engine.player_pos = (
                start_room.x + start_room.width // 2,
                start_room.y + start_room.height // 2,
            )
        state.engine.populate_dungeon_canopy()
        summary = {
            "seed": dungeon_seed,
            "total_rooms": len(state.engine.dungeon_graph.rooms),
            "start_room": state.engine.dungeon_graph.start_room_id,
        }
    else:
        # Default BSP descending dungeon
        summary = state.engine.generate_dungeon(depth=DEFAULT_DUNGEON_DEPTH, seed=dungeon_seed)

    # Archive seed for the Librarian's Seed Vault
    _archive_dungeon_seed(state, dungeon_seed, summary)

    # Initialize room content tracking from populated rooms
    for room_id, pop_room in state.engine.populated_rooms.items():
        content = pop_room.content
        state.room_enemies[room_id] = list(content.get("enemies", []))
        state.room_loot[room_id] = list(content.get("loot", []))
        state.room_furniture[room_id] = list(content.get("furniture", []))

    # WO-V32.0: Scale pre-populated enemies by party size
    _scaling = get_party_scaling(len(state.engine.party))
    for enemies in state.room_enemies.values():
        for e in enemies:
            e["hp"] = max(1, int(e.get("hp", 1) * _scaling["hp_mult"]))
            if "max_hp" in e:
                e["max_hp"] = max(1, int(e["max_hp"] * _scaling["hp_mult"]))
            e["_dmg_mult"] = _scaling["dmg_mult"]

    # Set doom rate multiplier for this party size
    state.doom_rate_mult = DOOM_RATE_MULT.get(len(state.engine.party), 1.0)

    # Build spatial rooms for renderer
    _rebuild_spatial_rooms(state)

    return summary


def _archive_dungeon_seed(state: GameState, seed: int, summary: dict):
    """Archive the dungeon seed to the Librarian's Seed Vault."""
    try:
        from codex.core.services.librarian import LibrarianTUI
        LibrarianTUI.archive_seed({
            "seed_value": seed,
            "dungeon_type": "burnwillow",
            "level_number": summary.get("depth", DEFAULT_DUNGEON_DEPTH),
            "total_rooms": summary.get("total_rooms", 0),
            "start_room": summary.get("start_room_id"),
            "system_id": state.system_id,
            "party": [c.name for c in state.engine.party] if state.engine else [],
        })
    except Exception:
        pass  # Seed archiving is non-critical


def _broadcast_death(state: GameState):
    """Record fallen party members in the Graveyard service."""
    try:
        from codex.core.services.graveyard import log_death
        for char in state.engine.party:
            if isinstance(char, Minion):
                continue
            log_death(
                {
                    "name": char.name,
                    "hp_max": char.max_hp,
                    "might": char.might,
                    "wits": char.wits,
                    "grit": char.grit,
                    "aether": char.aether,
                    "cause": "Total party kill in the Burnwillow",
                    "doom": state.doom,
                    "turns": state.turn_number,
                    "room_id": state.current_room_id,
                },
                system_id=state.system_id,
                seed=state.dungeon_seed,
            )
    except Exception:
        pass  # Death logging is non-critical


def _broadcast_victory(state: GameState, butler=None):
    """Archive the winning seed and log fallen party members."""
    try:
        from codex.core.services.librarian import LibrarianTUI
        LibrarianTUI.archive_seed({
            "seed_value": state.dungeon_seed,
            "dungeon_type": "burnwillow",
            "level_number": DEFAULT_DUNGEON_DEPTH,
            "total_rooms": len(state.engine.dungeon_graph.rooms) if state.engine and state.engine.dungeon_graph else 0,
            "system_id": state.system_id,
            "party": [c.name for c in state.engine.party] if state.engine else [],
            "victory": True,
        })
    except Exception:
        pass  # Seed archiving is non-critical

    try:
        from codex.core.services.graveyard import log_death
        for char in state.engine.party:
            if not char.is_alive() and not isinstance(char, Minion):
                log_death(
                    {
                        "name": char.name,
                        "hp_max": char.max_hp,
                        "might": char.might,
                        "wits": char.wits,
                        "grit": char.grit,
                        "aether": char.aether,
                        "cause": "Fell in victory at the Burnwillow",
                        "doom": state.doom,
                        "turns": state.turn_number,
                        "room_id": state.current_room_id,
                    },
                    system_id=state.system_id,
                    seed=state.dungeon_seed,
                )
    except Exception:
        pass  # Death logging is non-critical

    if butler:
        try:
            butler.sync_session_to_file()
        except Exception:
            pass


def _format_cardinal_exits(state: GameState) -> List[str]:
    """Format connected rooms as '[N] Room 4' style exit strings.

    When multiple exits share the same cardinal direction, they are
    disambiguated with numeric suffixes: [E1], [E2], etc.
    Also rebuilds state.cached_exit_labels for the move parser.
    """
    if not state.engine:
        return []
    exits = state.engine.get_cardinal_exits()

    # Count exits per direction to detect ambiguity
    dir_counts: Dict[str, int] = {}
    for e in exits:
        d = e["direction"]
        dir_counts[d] = dir_counts.get(d, 0) + 1

    # Assign indexed labels for ambiguous directions
    dir_indices: Dict[str, int] = {}
    state.cached_exit_labels.clear()
    result = []
    for e in exits:
        d = e["direction"]
        tags = ""
        if e["is_locked"]:
            tags += " LOCKED"
        if e["visited"]:
            tags += " *"
        if dir_counts[d] > 1:
            idx = dir_indices.get(d, 1)
            dir_indices[d] = idx + 1
            label = f"{d}{idx}"
        else:
            label = d
        state.cached_exit_labels[label.lower()] = e["id"]
        result.append(f"[{label}] Room {e['id']}{tags}")
    return result


def _rebuild_spatial_rooms(state: GameState):
    """Rebuild the spatial room cache from engine state."""
    if not state.engine or not state.engine.dungeon_graph:
        return

    state.spatial_rooms.clear()
    graph = state.engine.dungeon_graph

    for room_id, room_node in graph.rooms.items():
        # Determine visibility
        if room_id == state.engine.current_room_id:
            vis = RoomVisibility.CURRENT
        elif room_id in state.engine.visited_rooms:
            vis = RoomVisibility.VISITED
        elif room_id in state.scouted_rooms:
            vis = RoomVisibility.VISITED  # Scouted rooms show as visited (dimmed)
        else:
            vis = RoomVisibility.UNEXPLORED

        sr = SpatialRoom.from_map_engine_room(room_node, visibility=vis)

        # Inject live enemy/loot/furniture data for current room
        # list() copies isolate renderer from live state (WO V3.0.1)
        if room_id == state.engine.current_room_id:
            sr.enemies = list(state.room_enemies.get(room_id, []))
            sr.loot = list(state.room_loot.get(room_id, []))
            sr.furniture = list(state.room_furniture.get(room_id, []))
        elif room_id in state.scouted_rooms:
            # Scouted rooms show entity positions dimmed on map
            sr.enemies = list(state.room_enemies.get(room_id, []))
            sr.loot = list(state.room_loot.get(room_id, []))

        # Inject Rot Hunter marker into visited rooms (not player's room — already in room_enemies there)
        if (state.rot_hunter and state.rot_hunter.get("active")
                and state.rot_hunter.get("room_id") == room_id
                and room_id != state.engine.current_room_id
                and room_id in state.engine.visited_rooms):
            hunter_marker = {"name": "The Rot Hunter", "is_rot_hunter": True, "is_boss": True}
            sr.enemies = list(sr.enemies) + [hunter_marker]

        # WO-V45.0: Inject quest markers for rooms matching active quest tiers
        if state.narrative:
            room_tier = getattr(room_node, "tier", 1)
            for q in state.narrative.get_active_quests():
                if q.status == "active" and q.tier_hint == room_tier:
                    # Derive marker type from objective trigger
                    obj = q.objective_trigger
                    if "kill" in obj:
                        sr.quest_markers.append("kill")
                    elif "search" in obj:
                        sr.quest_markers.append("search")
                    elif "loot" in obj:
                        sr.quest_markers.append("loot")
                    elif "reach" in obj:
                        sr.quest_markers.append("reach")

        state.spatial_rooms[room_id] = sr


# =============================================================================
# RENDERING
# =============================================================================

SIDEBAR_WINDOW_SIZE = 25


def _build_sidebar_detail(state: GameState) -> Optional[str]:
    """Build windowed sidebar detail with scroll indicators and pinned turn tracker."""
    if not state.sidebar_buffer:
        # Even with no buffer, pin turn tracker if applicable
        tracker = state.build_turn_tracker() if state.is_party_turn_mode() else ""
        return tracker if tracker else None

    total = len(state.sidebar_buffer)

    # Clamp offset to valid range
    max_offset = max(0, total - SIDEBAR_WINDOW_SIZE)
    state.sidebar_view_offset = max(0, min(state.sidebar_view_offset, max_offset))
    offset = state.sidebar_view_offset

    # Window slice: newest at bottom, offset scrolls back toward older
    end = total - offset
    start = max(0, end - SIDEBAR_WINDOW_SIZE)

    window = state.sidebar_buffer[start:end]
    parts = []

    # Scroll-up indicator
    if start > 0:
        parts.append(f"  [{start} older -- press '[' to scroll up]")

    parts.append("\n---\n".join(window))

    # Scroll-down indicator
    if end < total:
        parts.append(f"  [{total - end} newer -- press ']' to scroll down]")

    # Pin turn tracker at bottom (always visible regardless of scroll)
    if state.is_party_turn_mode():
        tracker = state.build_turn_tracker()
        if tracker:
            parts.append("---")
            parts.append(tracker)

    return "\n".join(parts)


def render_frame(state: GameState):
    """Render the full game frame: map + HUD + room description + message log."""
    _rebuild_spatial_rooms(state)
    con = state.console
    con.clear()

    # Title bar
    title_text = Text()
    title_text.append(f" {GAME_TITLE} ", style=f"bold {THEME_CFG.color_current} on #1a1a2e")
    title_text.append(f" :: {GAME_SUBTITLE} ", style=f"dim {THEME_CFG.color_visited}")
    title_text.append(f"  Doom: {state.doom}", style=f"bold {THEME_CFG.color_enemy}")
    title_text.append(f"  Turn: {state.turn_number}", style=f"dim white")
    title_text.append(f"  Move: {state.remaining_movement}ft", style="dim cyan")
    action_status = "Ready" if not state.action_taken else "Used"
    action_style = "dim green" if not state.action_taken else "dim red"
    title_text.append(f"  Action: {action_status}", style=action_style)
    # WO-V44.0: Quest tracker in HUD
    if state.narrative:
        active_quests = state.narrative.get_active_quests()
        if active_quests:
            nearest = active_quests[0]
            q_label = f"  Quest: {nearest.title}"
            if nearest.progress_target > 1:
                q_label += f" [{nearest.progress}/{nearest.progress_target}]"
            title_text.append(q_label, style="dim cyan")
    con.print(Panel(title_text, box=box.HEAVY, border_style=THEME_CFG.color_current))

    # Pinned last action result
    if state.last_action_result:
        con.print(Panel(state.last_action_result, title="Last Action",
                        border_style="bold yellow", box=box.SIMPLE))

    # Get current room data
    room_data = state.engine.get_current_room()
    if not room_data:
        con.print("[red]ERROR: No current room data.[/red]")
        return

    enemies = state.room_enemies.get(state.current_room_id, [])
    loot = state.room_loot.get(state.current_room_id, [])

    # Build stats dict for sidebar
    furniture = state.room_furniture.get(state.current_room_id, [])
    stats = {
        "room_name": f"Room {room_data['id']} ({room_data['type'].upper()})",
        "room_description": room_data["description"],
        "hp_current": (state.active_leader or state.character).current_hp,
        "hp_max": (state.active_leader or state.character).max_hp,
        "depth": room_data.get("tier", 1),
        "enemies": enemies,
        "loot": loot,
        "furniture": furniture,
        "exits": _format_cardinal_exits(state),
        "detail": _build_sidebar_detail(state),
    }

    # Inject mini-map into sidebar
    if state.engine and state.engine.dungeon_graph:
        mm_rooms = rooms_to_minimap_dict(state.engine.dungeon_graph)
        # WO-V45.0: Inject quest_markers into mini-map room dicts
        for rid, sr in state.spatial_rooms.items():
            if rid in mm_rooms and sr.quest_markers:
                mm_rooms[rid]["quest_markers"] = list(sr.quest_markers)
        stats["mini_map"] = render_mini_map(
            mm_rooms, state.current_room_id, state.engine.visited_rooms,
            rich_mode=True, theme=THEME,
            doom=state.engine.doom_clock.current if hasattr(state.engine, 'doom_clock') else None,
        )

    # Render map with sidebar
    map_panel = render_spatial_map(
        rooms=state.spatial_rooms,
        player_room_id=state.current_room_id,
        theme=THEME,
        stats=stats,
        viewport_width=50,
        viewport_height=20,
        console=con,
        player_pos=state.engine.player_pos if state.engine else None,
    )
    con.print(map_panel)

    # Party quick-stats bar (shows all members)
    party = state.engine.party if state.engine else []
    if not party and state.character:
        party = [state.character]

    party_lines = Text()
    for i, char in enumerate(party):
        if i > 0:
            party_lines.append("  |  ", style="dim")
        is_active = (state.combat_mode and char is state.active_character)
        tag = "[ACTIVE] " if is_active else ""
        minion_tag = "[S] " if isinstance(char, Minion) else ""
        dead_style = "dim strike" if not char.is_alive() else ""

        name_style = f"bold {THEME_CFG.color_player}" if not dead_style else dead_style
        party_lines.append(f" {tag}{minion_tag}{char.name} ", style=name_style)

        hp_style = "bold red" if char.current_hp <= char.max_hp // 3 else "bold white"
        if dead_style:
            hp_style = dead_style
        party_lines.append(f"HP:{char.current_hp}/{char.max_hp}", style=hp_style)

        if not isinstance(char, Minion):
            party_lines.append(f" M{calculate_stat_mod(char.might):+d}", style=dead_style or "white")
            party_lines.append(f" W{calculate_stat_mod(char.wits):+d}", style=dead_style or "white")
            party_lines.append(f" G{calculate_stat_mod(char.grit):+d}", style=dead_style or "white")
            party_lines.append(f" A{calculate_stat_mod(char.aether):+d}", style=dead_style or "white")
            party_lines.append(f" DR:{char.gear.get_total_dr()}", style=dead_style or "white")

    # Leader's keys
    leader = state.active_leader or state.character
    if leader:
        party_lines.append(f"  Keys:{leader.keys}", style=f"{THEME_CFG.color_loot}")

    con.print(Panel(party_lines, box=box.SIMPLE, border_style="dim"))

    # Render Adventure Log (rolling buffer)
    if state.message_log:
        recent = state.message_log[-LOG_BUFFER_SIZE:]
        log_text = "\n".join(msg.strip() for msg in recent if msg.strip())
        if log_text:
            con.print(Panel(log_text, title="Adventure Log", border_style="grey50", box=box.SIMPLE))

    # Contextual alerts
    if state.combat_mode:
        con.print(f"  [bold {THEME_CFG.color_enemy}]** COMBAT **[/]  Round {state.combat_round}")
    if enemies:
        enemy_names = ", ".join(e["name"] for e in enemies)
        con.print(f"  [bold {THEME_CFG.color_enemy}]HOSTILE:[/] {enemy_names}")
    if loot:
        loot_names = ", ".join(item["name"] for item in loot)
        con.print(f"  [bold {THEME_CFG.color_loot}]LOOT:[/] {loot_names}")
    if state.current_room_id in state.cleared_rooms and not enemies:
        con.print(f"  [{THEME_CFG.color_visited}]This room has been cleared.[/]")
    if state.current_room_id in state.searched_rooms:
        con.print(f"  [{THEME_CFG.color_visited}]You have already searched this room.[/]")

    con.print()

    # Emit StateFrame for Player View viewer (external monitor)
    if state.engine:
        tmp = None
        try:
            frame = build_state_frame(
                engine=state.engine, game_state=state,
                system_id="burnwillow", turn_number=state.turn_number,
            )
            frame_path = STATE_DIR / "player_frame.json"
            frame_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(frame_path.parent), suffix=".tmp")
            with os.fdopen(fd, 'w') as f:
                f.write(frame_to_json(frame))
            os.replace(tmp, str(frame_path))
            tmp = None  # Replaced successfully, no cleanup needed
        except Exception:
            pass  # Non-critical — don't crash game loop
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass


def screen_refresh(state: GameState):
    """Clear and fully redraw the game frame (WO V20.3 2D)."""
    render_frame(state)


def render_title_screen(con: Console):
    """Show the game title screen."""
    con.clear()
    title_art = """
    ╔══════════════════════════════════════════════╗
    ║                                              ║
    ║          ╔╗ ╦ ╦╦═╗╔╗╔╦ ╦╦╦  ╦  ╔═╗╦ ╦      ║
    ║          ╠╩╗║ ║╠╦╝║║║║║║║║  ║  ║ ║║║║      ║
    ║          ╚═╝╚═╝╩╚═╝╚╝╚╩╝╩╩═╝╩═╝╚═╝╚╩╝      ║
    ║                                              ║
    ║           "You Are What You Wear"            ║
    ║                                              ║
    ║   A Roguelike Dungeon Crawler (Terminal)     ║
    ║                                              ║
    ╚══════════════════════════════════════════════╝
    """
    con.print(Text(title_art, style=f"bold {THEME_CFG.color_current}"))
    con.print()


def render_death_screen(state: GameState):
    """Show the death screen (total party kill)."""
    con = state.console
    con.print()
    death_text = Text()
    death_text.append("\n  YOUR FLAME IS EXTINGUISHED\n", style=f"bold {THEME_CFG.color_enemy}")
    # List all fallen
    for char in state.engine.party:
        if not isinstance(char, Minion):
            death_text.append(f"  {char.name} has fallen.\n", style="dim white")
    death_text.append(f"\n  Doom Clock: {state.doom}\n", style=f"dim {THEME_CFG.color_enemy}")
    death_text.append(f"  Rooms explored: {len(state.engine.visited_rooms)}\n", style="dim white")
    death_text.append(f"  Turns survived: {state.turn_number}\n", style="dim white")
    con.print(Panel(death_text, border_style=THEME_CFG.color_enemy, box=box.DOUBLE))

    # TTS: narrate death
    if hasattr(state, 'butler') and state.butler and hasattr(state.butler, 'narrate'):
        try:
            state.butler.narrate("Your flame is extinguished.")
        except Exception:
            pass


def render_victory_screen(state: GameState):
    """Show the victory screen (reached boss room and cleared it)."""
    con = state.console
    con.print()
    victory_text = Text()
    victory_text.append("\n  THE BURNWILLOW BLOOMS AGAIN\n", style=f"bold {THEME_CFG.color_current}")
    survivors = [c for c in state.engine.party if c.is_alive() and not isinstance(c, Minion)]
    if len(survivors) == 1:
        victory_text.append(f"\n  {survivors[0].name} has vanquished the threat.\n", style=f"bold {THEME_CFG.color_loot}")
    else:
        names = ", ".join(c.name for c in survivors)
        victory_text.append(f"\n  The party has vanquished the threat!\n", style=f"bold {THEME_CFG.color_loot}")
        victory_text.append(f"  Survivors: {names}\n", style=f"{THEME_CFG.color_loot}")
    # Fallen
    fallen = [c for c in state.engine.party if not c.is_alive() and not isinstance(c, Minion)]
    if fallen:
        fallen_names = ", ".join(c.name for c in fallen)
        victory_text.append(f"  Fallen: {fallen_names}\n", style=f"dim {THEME_CFG.color_enemy}")
    victory_text.append(f"\n  Doom Clock: {state.doom}\n", style="dim white")
    victory_text.append(f"  Rooms explored: {len(state.engine.visited_rooms)}\n", style="dim white")
    victory_text.append(f"  Turns survived: {state.turn_number}\n", style="dim white")
    con.print(Panel(victory_text, border_style=THEME_CFG.color_loot, box=box.DOUBLE))

    # WO-V50.0: Narrate victory
    if hasattr(state, 'butler') and state.butler and hasattr(state.butler, 'narrate'):
        try:
            state.butler.narrate("The Burnwillow blooms again. You are victorious.")
        except Exception:
            pass


# =============================================================================
# MODULE / ZONE HELPERS  (Phase 3/6 spatial integration)
# =============================================================================

def check_zone_completion(state) -> bool:
    """Check if the current zone is complete and ready for transition.

    Conditions:
    - Dungeon: Boss room cleared (if boss room exists)
    - Settlement: Player at TOWN_GATE room
    - Manual: DM uses !advance command

    Args:
        state: Active GameState instance.

    Returns:
        True if the current zone exit condition has been met, False otherwise.
    """
    if not state.module_manifest:
        return False

    # Check if current room is a boss room and it's cleared
    if hasattr(state, 'current_room_id') and state.current_room_id is not None:
        room_id = state.current_room_id
        if hasattr(state, 'populated_rooms') and room_id in getattr(state, 'populated_rooms', {}):
            room = state.populated_rooms[room_id]
            if hasattr(room, 'room_type') and room.room_type == 'boss':
                if hasattr(room, 'enemies') and not room.enemies:
                    return True
        # Settlement exit: player reached town_gate
        if room_id == 'town_gate':
            return True
        # Generic exit room check via dungeon graph
        if (state.engine and state.engine.dungeon_graph and
                hasattr(state.engine.dungeon_graph, 'rooms') and
                room_id in state.engine.dungeon_graph.rooms):
            room_node = state.engine.dungeon_graph.rooms[room_id]
            if (hasattr(room_node, 'room_type') and
                    str(room_node.room_type).lower() in ('exit', 'return_gate')):
                return True

    return False


def advance_to_next_zone(state) -> bool:
    """Advance to the next zone in the module manifest.

    Increments ``state.current_chapter_idx`` and ``state.current_zone_idx``
    to point at the next ZoneEntry in the module's chapter progression.

    Args:
        state: Active GameState instance.

    Returns:
        True if there is a next zone and the indices were updated.
        False if the module is complete (no further zones exist).
    """
    if not state.module_manifest:
        return False

    result = state.module_manifest.get_next_zone(
        state.current_chapter_idx,
        state.current_zone_idx,
    )

    if result is None:
        return False

    state.current_chapter_idx, state.current_zone_idx, _zone_entry = result
    return True


# =============================================================================
# GAME ACTIONS
# =============================================================================

def action_move(state: GameState, target_id: int) -> List[str]:
    """Move to a connected room. Advances Doom Clock by 1. Triggers ambush check."""
    messages = []

    # End any active combat before moving
    if state.combat_mode:
        state.end_combat()

    # Clear sidebar on room transition (WO V20.3)
    state.clear_sidebar()

    result = state.engine.move_to_room(target_id)
    if not result["success"]:
        messages.append(f"[Cannot move] {result['message']}")
        return messages

    messages.append(result["message"])
    state.turn_number += 1
    # WO-V37.0: Log room entered
    state.log_event("room_entered", room_id=target_id)

    # WO-V61.0: zone_breakthrough anchor
    room_node = state.engine.dungeon_graph.rooms.get(target_id) if state.engine and state.engine.dungeon_graph else None
    if room_node and hasattr(room_node, 'tier') and room_node.tier > state._max_tier_reached:
        state._max_tier_reached = room_node.tier
        state.log_event("zone_breakthrough", zone_id=target_id, tier=room_node.tier)
        _broadcast_anchor(state, "zone_breakthrough", zone_id=target_id, tier=room_node.tier)

    # WO-V32.0: move_to_room() internally advances doom by 1.
    # Apply fractional extra for larger parties via the accumulator.
    if state.doom_rate_mult > 1.0:
        extra = (1 * state.doom_rate_mult - 1) + state._doom_remainder
        extra_ticks = int(extra)
        state._doom_remainder = extra - extra_ticks
        if extra_ticks > 0:
            extra_events = state.engine.advance_doom(extra_ticks)
            for ev in extra_events:
                messages.append(ev)

    # Acoustic Bridge: narrate room entry via TTS (WO V20.3 4C)
    if hasattr(state, 'butler') and state.butler:
        try:
            room = state.engine.get_current_room()
            if room and hasattr(state.butler, 'narrate'):
                raw_desc = room.get("description", "")
                desc = f"{raw_desc[:80]}..." if len(raw_desc) > 80 else raw_desc
                state.butler.narrate(f"{room.get('name', 'Unknown Room')}. {desc}")
        except Exception:
            pass  # TTS failure must not block gameplay

    # Quest objective tracking: room entry
    if state.narrative:
        room_node = state.engine.dungeon_graph.rooms.get(target_id)
        tier = room_node.tier if room_node else 1
        triggers = state.narrative.check_objective(f"reach_tier_{tier}")
        for msg in triggers:
            messages.append(f"[QUEST] {msg}")

    # NPC encounter check (empty rooms only)
    npc_msgs = _handle_dungeon_npc_encounter(state, target_id)
    messages.extend(npc_msgs)

    # Check for enemies in new room -> ambush check + enter combat
    new_enemies = state.room_enemies.get(target_id, [])

    # Encounter engine: augment room with party-size/doom scaling
    if new_enemies:
        room_node = state.engine.dungeon_graph.rooms.get(target_id)
        _scaling = get_party_scaling(len(state.engine.get_active_party()))
        enc_ctx = EncounterContext(
            system_tag="BURNWILLOW",
            party_size=len(state.engine.get_active_party()),
            threat_level=state.doom,
            floor_tier=room_node.tier if room_node else 1,
            room_type=room_node.room_type.value if room_node else "normal",
            trigger="move_entry",
            seed=(state.engine.dungeon_graph.seed + target_id + state.turn_number),
            hp_mult=_scaling["hp_mult"],
            dmg_mult=_scaling["dmg_mult"],
        )
        enc_result = EncounterEngine().generate(enc_ctx)
        if enc_result.entities:
            # Position extra enemies within room interior
            if room_node:
                cx = room_node.x + room_node.width // 2
                cy = room_node.y + room_node.height // 2
                inner_x1 = room_node.x + room_node.width - 2
                offset = len(new_enemies)
                for i, extra in enumerate(enc_result.entities):
                    extra["x"] = min(cx + 1 + offset + i, inner_x1)
                    extra["y"] = cy
            new_enemies.extend(enc_result.entities)
            if enc_result.description:
                messages.append(enc_result.description)

    if new_enemies:
        enemy_names = ", ".join(e["name"] for e in new_enemies)
        messages.append(f"Enemies spotted: {enemy_names}")

        # Ambush check: leader's Wits vs enemy passive DC 10
        leader = state.active_leader or state.character
        if leader:
            wits_mod = leader.get_stat_mod(StatType.WITS)
            ambush_result = roll_ambush(wits_mod, enemy_passive_dc=10)
            if ambush_result["ambush_round"]:
                messages.append(
                    f"AMBUSH! {leader.name} spots them first "
                    f"({ambush_result['total']} vs DC 10). "
                    f"Party gets a free action round!"
                )
                state.ambush_round = True
            else:
                messages.append(
                    f"The enemies are alert ({ambush_result['total']} vs DC 10). "
                    f"Combat begins!"
                )
                state.ambush_round = False

        # Enter combat mode
        state.start_combat()
        # Combat intro quip — Butler first, static pool fallback
        from codex.games.burnwillow.content import COMBAT_INTRO_QUIPS
        quip = None
        if hasattr(state, 'butler') and state.butler:
            quip = state.butler.get_quip("combat_start")
        if not quip:
            quip = random.choice(COMBAT_INTRO_QUIPS)
        messages.append(quip)
        if hasattr(state, 'butler') and state.butler:
            try:
                if hasattr(state.butler, 'narrate'):
                    names = " and ".join(e["name"] for e in new_enemies[:2])
                    verb = "attacks" if len(new_enemies) == 1 else "engage"
                    state.butler.narrate(f"Combat! {names} {verb}!")
            except Exception:
                pass
        if state.ambush_round:
            messages.append("[AMBUSH ROUND] Each party member may take one action before enemies react.")

    # Rot Hunter advancement (doom was advanced inside move_to_room)
    rot_msgs = _process_doom_advancement(state, [])
    messages.extend(rot_msgs)

    # WO-V61.0: Perception-time mood overlay
    if state.engine:
        mood = state.engine.get_mood_context() if hasattr(state.engine, 'get_mood_context') else {}
        condition = mood.get("party_condition", "healthy")
        overlays = _MOOD_OVERLAYS.get(condition)
        if overlays:
            messages.insert(1, f"[dim italic]{random.choice(overlays)}[/]")

    return messages


def action_scout(state: GameState, target_id: int) -> List[str]:
    """Peek at a connected room without entering. Wits vs DC 12. +1 Doom."""
    messages = []
    char = state.active_character or state.character

    # Validate target is connected
    connected = state.engine.get_connected_rooms()
    connected_ids = [r["id"] for r in connected]

    if target_id not in connected_ids:
        messages.append(f"Room {target_id} is not connected to your current room.")
        return messages

    if target_id in state.scouted_rooms or target_id in state.engine.visited_rooms:
        messages.append(f"You already know what's in room {target_id}.")
        return messages

    # Wits check
    check = char.make_check(StatType.WITS, SCOUT_DC)
    doom_events = _advance_doom_scaled(state, 1)
    for _evt in doom_events:
        state.log_event("doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
        _broadcast_anchor(state, "doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
    state.turn_number += 1

    if check.success:
        state.scouted_rooms.add(target_id)
        # Reveal room content
        pop_room = state.engine.populated_rooms.get(target_id)
        if pop_room:
            content = pop_room.content
            room_node = pop_room.geometry
            messages.append(
                f"Scout SUCCESS ({check.total} vs DC {SCOUT_DC}): "
                f"Room {target_id} ({room_node.room_type.value.upper()}, Tier {room_node.tier})"
            )
            desc = content.get("description", "An unremarkable chamber.")
            messages.append(f"  \"{desc}\"")
            enemies = content.get("enemies", [])
            if enemies:
                enemy_str = ", ".join(f"{e['name']} ({e['hp']} HP)" for e in enemies)
                messages.append(f"  Enemies: {enemy_str}")
            else:
                messages.append("  No enemies detected.")
            loot_items = content.get("loot", [])
            if loot_items:
                messages.append(f"  Loot: {len(loot_items)} item(s) visible.")
        else:
            messages.append(f"Scout SUCCESS: Room {target_id} appears empty.")
    else:
        messages.append(
            f"Scout FAILED ({check.total} vs DC {SCOUT_DC}): "
            f"You can't make out what's in room {target_id}."
        )
        # Fumble check: if any die rolled a 1, noise alerts an enemy
        if 1 in check.rolls:
            messages.append("FUMBLE! Your noise alerts the enemy!")
            pop_room = state.engine.populated_rooms.get(target_id)
            source_enemies = pop_room.content.get("enemies", []) if pop_room else []
            room_node = state.engine.dungeon_graph.rooms.get(target_id)

            _scaling = get_party_scaling(len(state.engine.get_active_party()))
            enc_ctx = EncounterContext(
                system_tag="BURNWILLOW",
                party_size=len(state.engine.get_active_party()),
                threat_level=state.doom,
                floor_tier=room_node.tier if room_node else 1,
                room_type=room_node.room_type.value if room_node else "normal",
                trigger="scout_fumble",
                seed=(state.engine.dungeon_graph.seed + target_id + state.turn_number),
                source_room_enemies=source_enemies,
                hp_mult=_scaling["hp_mult"],
                dmg_mult=_scaling["dmg_mult"],
            )
            enc_result = EncounterEngine().generate(enc_ctx)

            # Place pulled enemies in current room
            current_room = state.engine.dungeon_graph.rooms.get(state.current_room_id)
            existing = state.room_enemies.get(state.current_room_id, [])
            for i, entity in enumerate(enc_result.entities):
                if current_room:
                    cx = current_room.x + current_room.width // 2
                    cy = current_room.y + current_room.height // 2
                    inner_x1 = current_room.x + current_room.width - 2
                    entity["x"] = min(cx + 1 + len(existing) + i, inner_x1)
                    entity["y"] = cy
                state.room_enemies.setdefault(state.current_room_id, []).append(entity)
                messages.append(f"  A {entity['name']} charges into your room!")

            # Handle traps from fumble (30% chance)
            for trap in enc_result.traps:
                messages.append(f"  TRAP! {trap['name']} — {trap['description']}")
                messages.append(f"  [{trap['stat']} DC {trap['dc']}] {trap['effect']}")

            if enc_result.entities and not state.combat_mode:
                state.start_combat()
                messages.append("Combat begins!")

    for event in doom_events:
        messages.append(event)

    rot_msgs = _process_doom_advancement(state, doom_events)
    messages.extend(rot_msgs)

    return messages


def action_search(state: GameState) -> List[str]:
    """Thoroughly search the current room for hidden loot. Wits vs DC 12. +1 Doom."""
    messages = []
    char = state.active_character or state.character
    room_id = state.current_room_id

    if room_id in state.searched_rooms:
        messages.append("You have already searched this room thoroughly.")
        return messages

    # Wits check
    check = char.make_check(StatType.WITS, SEARCH_DC)
    doom_events = _advance_doom_scaled(state, 1)
    for _evt in doom_events:
        state.log_event("doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
        _broadcast_anchor(state, "doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
    state.turn_number += 1
    state.searched_rooms.add(room_id)

    if check.success:
        # Generate bonus loot
        room_node = state.engine.dungeon_graph.get_room(room_id)
        tier = room_node.tier if room_node else 1
        adapter = BurnwillowAdapter(seed=(state.engine.dungeon_graph.seed + room_id + 1000))
        rng = random.Random(state.engine.dungeon_graph.seed + room_id + 1000)
        bonus_item = adapter._generate_loot(tier, rng)

        state.room_loot.setdefault(room_id, []).append(bonus_item)
        messages.append(
            f"Search SUCCESS ({check.total} vs DC {SEARCH_DC}): "
            f"You found a hidden {bonus_item['name']}!"
        )
        # WO-V44.0: Quest search trigger
        for qm in _check_quest_search(state, room_id):
            messages.append(f"[QUEST] {qm}")
    else:
        messages.append(
            f"Search FAILED ({check.total} vs DC {SEARCH_DC}): "
            f"You find nothing beyond what's already visible."
        )

    for event in doom_events:
        messages.append(event)

    rot_msgs = _process_doom_advancement(state, doom_events)
    messages.extend(rot_msgs)

    return messages


def action_bind_wounds(state: GameState) -> List[str]:
    """Heal approximately 50% of max HP. Costs 1 Dungeon Turn (+1 Doom)."""
    messages = []
    char = state.active_leader

    if char.current_hp >= char.max_hp:
        messages.append("You are already at full health.")
        return messages

    # Heal
    heal_amount = max(1, int(char.max_hp * BIND_WOUNDS_HEAL_PERCENT))
    actual = char.heal(heal_amount)

    doom_events = _advance_doom_scaled(state, 1)
    for _evt in doom_events:
        state.log_event("doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
        _broadcast_anchor(state, "doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
    state.turn_number += 1

    messages.append(
        f"Bind Wounds: Healed {actual} HP "
        f"(now {char.current_hp}/{char.max_hp})."
    )

    for event in doom_events:
        messages.append(event)

    rot_msgs = _process_doom_advancement(state, doom_events)
    messages.extend(rot_msgs)

    return messages


ARCHETYPE_LOOT = {
    "beast": [
        ("Chitin Plate", "Chest", [], "Hardened carapace shell. Organic armor."),
        ("Venomous Spike", "R.Hand", [], "A barbed fang, dripping with venom."),
        ("Sinew Bindings", "Arms", [], "Braided tendons. Flexible and tough."),
        ("Feral Pelt", "Shoulders", [], "Thick hide torn from a beast."),
    ],
    "scavenger": [
        ("Scrap Shiv", "R.Hand", [], "A jagged blade cobbled from refuse."),
        ("Dented Buckler", "L.Hand", ["[Intercept]"], "Battered but functional shield."),
        ("Pilfered Ring", "Neck", [], "A stolen trinket with faint enchantment."),
        ("Ragged Coif", "Head", [], "A threadbare hood offering meager protection."),
    ],
    "aetherial": [
        ("Focus Shard", "R.Hand", [], "A splinter of crystallized aether."),
        ("Essence Veil", "Shoulders", [], "Shimmering fabric woven from residual energy."),
        ("Spectral Band", "Neck", [], "A ghostly ring that hums with power."),
        ("Void Thread Mantle", "Chest", [], "Cloak of woven shadow."),
    ],
    "construct": [
        ("Iron Plate", "Chest", [], "Salvaged plating from a mechanical foe."),
        ("Gear Assembly", "Arms", [], "Interlocking cogs repurposed as gauntlets."),
        ("Piston Gauntlet", "Arms", [], "A hydraulic glove of surprising force."),
        ("Spring Greaves", "Legs", [], "Coiled leg armor that aids movement."),
    ],
}

# Primary stat pool for archetype loot wildcard-slot items (WO V20.3)
ARCHETYPE_LOOT_STATS: Dict[str, str] = {
    "Feral Pelt": "GRIT",        # Beast shoulders -> survivability
    "Pilfered Ring": "AETHER",    # Scavenger neck -> enchantment
    "Essence Veil": "AETHER",     # Aetherial shoulders -> magic
    "Spectral Band": "AETHER",    # Aetherial neck -> magic
    "Void Thread Mantle": "AETHER",  # Aetherial chest -> Aether override
}

TIER_PREFIX = {1: "Scrap", 2: "Ironbark", 3: "Heartwood", 4: "Ambercore"}


def generate_enemy_loot(enemy: dict, state: GameState) -> Optional[dict]:
    """Roll for a loot drop from a slain enemy.

    Bosses always drop loot (floor_tier+1); normal enemies have a 50% chance.
    Loot matches the enemy's archetype.
    """
    is_boss = enemy.get("is_boss", False)
    drop_chance = 1.0 if is_boss else 0.5
    if random.random() > drop_chance:
        return None

    tier = enemy.get("tier", 1)
    if is_boss:
        tier = min(4, tier + 1)

    archetype = enemy.get("archetype", "beast")
    pool = ARCHETYPE_LOOT.get(archetype, ARCHETYPE_LOOT["beast"])
    name, slot, traits, desc = random.choice(pool)

    prefix = TIER_PREFIX.get(tier, "Scrap")
    full_name = f"{prefix} {name}"

    result = {
        "name": full_name,
        "slot": slot,
        "tier": tier,
        "special_traits": list(traits),
        "description": desc,
    }
    ps = ARCHETYPE_LOOT_STATS.get(name)
    if ps:
        result["primary_stat"] = ps
    return result


ROT_HUNTER_LOOT_POOL = [
    ("Rotclaw Fang", "R.Hand", [], "A blade hewn from the Hunter's own claw. Pulses with blight."),
    ("Hunter's Heartstone", "Neck", [], "A crystallized organ that throbs with stolen vitality."),
    ("Blighthide Mantle", "Shoulders", [], "The Hunter's own skin, tanned by rot into supple armor."),
    ("Rot-Tendril Gauntlets", "Arms", [], "Writhing tendrils that tighten on command."),
]


def _generate_rot_hunter_loot(state: GameState) -> dict:
    """Always tier 4 artifact-class loot from the Rot Hunter."""
    from codex.games.burnwillow.content import LOOT_PRIMARY_STATS
    name, slot, traits, desc = random.choice(ROT_HUNTER_LOOT_POOL)
    result = {
        "name": f"Ambercore {name}",
        "slot": slot,
        "tier": 4,
        "special_traits": list(traits),
        "description": desc,
    }
    ps = LOOT_PRIMARY_STATS.get(name)
    if ps:
        result["primary_stat"] = ps
    return result


def _bfs_path(graph, start_id: int, target_id: int) -> List[int]:
    """BFS shortest path from start_id to target_id through dungeon graph.

    Returns list of room IDs [start, ..., target] or empty list if unreachable.
    """
    if start_id == target_id:
        return [start_id]
    from collections import deque
    visited = {start_id}
    queue = deque([(start_id, [start_id])])
    while queue:
        current, path = queue.popleft()
        room = graph.get_room(current)
        if room is None:
            continue
        for neighbor_id in room.connections:
            if neighbor_id == target_id:
                return path + [neighbor_id]
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append((neighbor_id, path + [neighbor_id]))
    return []


def _check_rot_hunter_spawn(state: GameState, doom_events: list) -> List[str]:
    """Spawn the Rot Hunter when doom reaches 20+. Returns spawn messages."""
    if state.rot_hunter is not None:
        return []
    if not state.engine or state.engine.doom_clock.current < 20:
        return []

    # Determine tier from max visited room tier + 2 (capped at 4)
    max_tier = 1
    if state.engine.dungeon_graph:
        for rid in state.engine.visited_rooms:
            room = state.engine.dungeon_graph.get_room(rid)
            if room and room.tier > max_tier:
                max_tier = room.tier
    hunter_tier = min(4, max_tier + 2)

    # Find start room (lowest ID = dungeon entrance)
    start_room = min(state.engine.dungeon_graph.rooms.keys()) if state.engine.dungeon_graph else 0

    state.rot_hunter = {
        "name": "The Rot Hunter",
        "room_id": start_room,
        "hp": 30 + hunter_tier * 8,
        "max_hp": 30 + hunter_tier * 8,
        "defense": 14 + hunter_tier,
        "damage": f"{min(5, hunter_tier + 1)}d6",
        "dr": hunter_tier + 1,
        "tier": hunter_tier,
        "archetype": "aetherial",
        "is_boss": True,
        "is_rot_hunter": True,
        "active": True,
        "special": "Relentless Pursuit: Moves one room toward the player each Doom tick.",
        "description": "A skeletal amalgam of rust and sinew, drawn by the scent of the living.",
    }

    return ["[bold magenta]THE ROT HUNTER HAS AWAKENED.[/] It stalks from the dungeon entrance..."]


def _advance_rot_hunter(state: GameState) -> List[str]:
    """Move the Rot Hunter one room closer to the player. Returns messages."""
    hunter = state.rot_hunter
    if hunter is None or not hunter.get("active"):
        return []
    if not state.engine or not state.engine.dungeon_graph:
        return []

    player_room = state.engine.current_room_id
    hunter_room = hunter["room_id"]

    if hunter_room == player_room:
        return []  # Already in player's room (combat should be active)

    path = _bfs_path(state.engine.dungeon_graph, hunter_room, player_room)
    if len(path) < 2:
        return []  # No path found or already there

    # Move one step
    hunter["room_id"] = path[1]
    messages = []

    if hunter["room_id"] == player_room:
        # Hunter has arrived — inject into room enemies, trigger combat
        room_enemies = state.room_enemies.setdefault(player_room, [])
        room_enemies.append(dict(hunter))
        messages.append("[bold magenta]The Rot Hunter crashes into the room![/] Its hollow eyes lock onto you.")
        if not state.combat_mode:
            state.start_combat()
            messages.append("Combat begins!")
    elif len(path) == 3:
        # One room away — proximity warning
        messages.append("[dim magenta]You hear scraping claws in the adjacent corridor...[/]")

    return messages


# =============================================================================
# WAVE SPAWN SYSTEM (WO-V17.0)
# =============================================================================

def _spawn_wave_1(state: GameState) -> List[str]:
    """Wave 1 (Doom 10): Spawn 2-3 ambush enemies in random unvisited rooms."""
    from codex.games.burnwillow.content import WAVE_ENEMIES, CONTENT_DR_BY_TIER, CONTENT_ARCHETYPES, get_party_scaling
    messages = []
    if not state.engine or not state.engine.dungeon_graph:
        return messages

    # Find unvisited rooms
    all_rooms = set(state.engine.dungeon_graph.rooms.keys())
    unvisited = list(all_rooms - state.engine.visited_rooms)
    if not unvisited:
        return messages

    count = min(random.randint(2, 3), len(unvisited))
    target_rooms = random.sample(unvisited, count)
    spawned = []
    scaling = get_party_scaling(len(state.engine.party))

    for rid in target_rooms:
        pool = WAVE_ENEMIES[1]
        name, hp_base, hp_var, defense, damage, special = random.choice(pool)
        enemy = {
            "name": name,
            "hp": max(1, int((hp_base + random.randint(0, hp_var)) * scaling["hp_mult"])),
            "defense": defense,
            "damage": damage,
            "special": special,
            "tier": 2,
            "dr": CONTENT_DR_BY_TIER.get(2, 1),
            "archetype": CONTENT_ARCHETYPES.get(name, "beast"),
            "wave": 1,
            "room_id": rid,
            "_dmg_mult": scaling["dmg_mult"],
        }
        # Inject into room's enemy list
        room_enemies = state.room_enemies.setdefault(rid, [])
        room_enemies.append(enemy)
        # Also inject into populated_rooms if available
        pop_room = state.engine.populated_rooms.get(rid)
        if pop_room:
            pop_room.content.setdefault("enemies", []).append(enemy)
        spawned.append(enemy)

    state.wave_spawns[1] = spawned
    messages.append("[bold yellow]Wings beat in the dark. New creatures stir in the corridors...[/]")
    messages.append(f"  ({count} ambush creatures placed in unexplored rooms)")
    return messages


def _spawn_wave_2(state: GameState) -> List[str]:
    """Wave 2 (Doom 15): Spawn 1-2 slow roamers at dungeon entrance."""
    from codex.games.burnwillow.content import WAVE_ENEMIES, CONTENT_DR_BY_TIER, CONTENT_ARCHETYPES, get_party_scaling
    messages = []
    if not state.engine or not state.engine.dungeon_graph:
        return messages

    start_room = min(state.engine.dungeon_graph.rooms.keys())
    count = random.randint(1, 2)
    spawned = []
    scaling = get_party_scaling(len(state.engine.party))

    for _ in range(count):
        pool = WAVE_ENEMIES[2]
        name, hp_base, hp_var, defense, damage, special = random.choice(pool)
        enemy = {
            "name": name,
            "hp": max(1, int((hp_base + random.randint(0, hp_var)) * scaling["hp_mult"])),
            "defense": defense,
            "damage": damage,
            "special": special,
            "tier": 3,
            "dr": CONTENT_DR_BY_TIER.get(3, 2),
            "archetype": CONTENT_ARCHETYPES.get(name, "beast"),
            "wave": 2,
            "room_id": start_room,
            "active": True,
            "_dmg_mult": scaling["dmg_mult"],
        }
        spawned.append(enemy)

    state.wave_spawns[2] = spawned
    state._wave_roam_counter = 0
    messages.append("[bold red]Heavy footsteps echo from the dungeon entrance. Something is hunting...[/]")
    messages.append(f"  ({count} roaming hunters enter from the entrance)")
    return messages


def _advance_wave_roamers(state: GameState) -> List[str]:
    """Move Wave 2 roamers one room closer every 2 doom ticks."""
    messages = []
    roamers = state.wave_spawns.get(2, [])
    if not roamers or not state.engine or not state.engine.dungeon_graph:
        return messages

    state._wave_roam_counter += 1
    if state._wave_roam_counter % 2 != 0:
        return messages  # Only advance every other doom tick

    player_room = state.engine.current_room_id
    for roamer in roamers:
        if not roamer.get("active"):
            continue
        if roamer.get("hp", 0) <= 0:
            continue

        roamer_room = roamer.get("room_id")
        if roamer_room == player_room:
            continue  # Already in player's room

        path = _bfs_path(state.engine.dungeon_graph, roamer_room, player_room)
        if len(path) < 2:
            continue

        # Move one step
        old_room = roamer["room_id"]
        roamer["room_id"] = path[1]

        # Remove from old room
        old_enemies = state.room_enemies.get(old_room, [])
        state.room_enemies[old_room] = [e for e in old_enemies if e is not roamer]

        if roamer["room_id"] == player_room:
            # Arrived — inject into current room and trigger combat
            state.room_enemies.setdefault(player_room, []).append(roamer)
            pop_room = state.engine.populated_rooms.get(player_room)
            if pop_room:
                pop_room.content.setdefault("enemies", []).append(roamer)
            messages.append(f"[bold red]{roamer['name']} crashes into the room![/]")
            if not state.combat_mode:
                state.start_combat()
                messages.append("Combat begins!")
        elif len(path) == 3:
            messages.append(f"[dim red]You hear {roamer['name'].lower()} footsteps nearby...[/]")

    return messages


def _process_wave_spawns(state: GameState, doom_events: list) -> List[str]:
    """Spawn and manage wave enemies based on Doom thresholds."""
    messages = []
    if not state.engine:
        return messages
    doom = state.engine.doom_clock.current

    # Wave 1: Doom 10 — stationary ambush spawns
    if doom >= 10 and 1 not in state.wave_spawns:
        messages.extend(_spawn_wave_1(state))

    # Wave 2: Doom 15 — slow roamers
    if doom >= 15 and 2 not in state.wave_spawns:
        messages.extend(_spawn_wave_2(state))

    # Wave 3: Doom 20 — Rot Hunter (existing logic, threshold raised)
    messages.extend(_check_rot_hunter_spawn(state, doom_events))

    # Advance roaming entities
    messages.extend(_advance_wave_roamers(state))
    messages.extend(_advance_rot_hunter(state))

    return messages


def _process_doom_advancement(state: GameState, doom_events: list) -> List[str]:
    """Process wave spawns and Rot Hunter after Doom advances."""
    return _process_wave_spawns(state, doom_events)


# --- Movement Budget helpers (WO: Movement Budget System) ---

def _end_exploration_turn(state: GameState, doom_cost: int = 0) -> List[str]:
    """End the current exploration turn: advance doom, rotate party, reset budget."""
    messages = []

    if doom_cost > 0:
        doom_events = _advance_doom_scaled(state, doom_cost)
        for _evt in doom_events:
            state.log_event("doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
            _broadcast_anchor(state, "doom_threshold", doom_value=state.engine.doom_clock.filled, event_text=_evt)
        state.turn_number += 1
        messages.extend(doom_events)
        rot_msgs = _process_doom_advancement(state, doom_events)
        messages.extend(rot_msgs)
    else:
        state.turn_number += 1

    # Party rotation
    if state.is_party_turn_mode():
        turn_msg = state.advance_exploration_turn()
        if turn_msg:
            messages.append(turn_msg)

    state.reset_turn()
    return messages


def _advance_doom_scaled(state: GameState, base_cost: int) -> list:
    """Advance doom with party-size multiplier using fractional accumulator (WO-V32.0).

    For 5-6 player groups, doom ticks slightly faster (1.1x / 1.2x).
    Fractional remainder carries over between calls so no ticks are lost.

    Returns:
        List of doom event strings (same as engine.advance_doom).
    """
    if base_cost <= 0:
        return []
    scaled = base_cost * state.doom_rate_mult + state._doom_remainder
    whole_ticks = int(scaled)
    state._doom_remainder = scaled - whole_ticks
    if whole_ticks <= 0:
        return []
    return state.engine.advance_doom(whole_ticks)


# WO-V61.0: Anchor event types for broadcast
_ANCHOR_EVENT_TYPES = frozenset({
    "near_death", "ally_saved", "rare_item_used", "critical_roll",
    "companion_fell", "faction_shift", "doom_threshold", "zone_breakthrough",
    "party_death",
})


def _format_anchor_summary(event_type: str, kwargs: dict) -> str:
    """Produce a 1-sentence summary of an anchor event for NPC memory broadcast."""
    if event_type == "near_death":
        return f"{kwargs.get('name', '?')} nearly fell in battle ({kwargs.get('hp', '?')}/{kwargs.get('max_hp', '?')} HP)"
    elif event_type == "ally_saved":
        return f"{kwargs.get('savior', '?')} saved {kwargs.get('saved', '?')} via {kwargs.get('method', '?')}"
    elif event_type == "companion_fell":
        return f"Companion {kwargs.get('name', '?')} fell to {kwargs.get('cause', 'unknown')}"
    elif event_type == "doom_threshold":
        return f"Doom reached {kwargs.get('doom_value', '?')}: {kwargs.get('event_text', '')}"
    elif event_type == "zone_breakthrough":
        return f"Party broke through to Tier {kwargs.get('tier', '?')}"
    elif event_type == "faction_shift":
        return f"{kwargs.get('npc_name', '?')} shifted from {kwargs.get('old_tier', '?')} to {kwargs.get('new_tier', '?')}"
    elif event_type == "critical_roll":
        return f"{kwargs.get('roller', '?')} scored a {kwargs.get('result', '?')} {kwargs.get('context', '')}"
    elif event_type == "rare_item_used":
        return f"{kwargs.get('user', '?')} used {kwargs.get('item_name', '?')}"
    elif event_type == "party_death":
        return f"{kwargs.get('name', '?')} has fallen in battle"
    return f"{event_type} occurred"


def _broadcast_anchor(state: "GameState", event_type: str, **kwargs):
    """Broadcast an anchor event for NPC memory consumption (WO-V61.0)."""
    if state.broadcast_manager and event_type in _ANCHOR_EVENT_TYPES:
        state.broadcast_manager.broadcast("HIGH_IMPACT_DECISION", {
            "_event_type": "HIGH_IMPACT_DECISION",
            "event_tag": f"anchor_{event_type}",
            "category": "security",
            "summary": _format_anchor_summary(event_type, kwargs),
        })


def _find_exit_in_direction(state: GameState, direction: str) -> Optional[dict]:
    """Check if there's a room exit in the given direction (8-way)."""
    # Map input direction to the short uppercase label from get_cardinal_exits()
    dir_map = {
        "n": "N", "s": "S", "e": "E", "w": "W",
        "ne": "NE", "nw": "NW", "se": "SE", "sw": "SW",
        "north": "N", "south": "S", "east": "E", "west": "W",
        "northeast": "NE", "northwest": "NW", "southeast": "SE", "southwest": "SW",
    }
    target_dir = dir_map.get(direction.lower())
    if not target_dir:
        return None
    for ex in state.engine.get_cardinal_exits():
        if ex["direction"] == target_dir:
            return ex
    return None


def _check_action_available(state: GameState) -> Optional[str]:
    """Return a denial message if the turn action has been used, else None."""
    if state.action_taken:
        return "You've already used your action this turn. Type 'end' to end your turn."
    return None


def _check_cleave_trait(char: Character) -> Optional[dict]:
    """Check if character has [Cleave] on an equipped weapon. Returns resolver data or None."""
    if not char or not char.gear:
        return None
    for slot in (GearSlot.R_HAND, GearSlot.L_HAND):
        item = char.gear.slots.get(slot)
        if item and item.special_traits and "[Cleave]" in item.special_traits:
            tier = item.tier.value if item.tier else 1
            return {
                "cleave_targets": min(3, tier),
                "cleave_damage_pct": 0.5,
            }
    return None


# WO-V36.0: Auto-trigger damage AoE check functions
def _check_damage_aoe_trait(char: Character) -> Optional[Tuple[str, int]]:
    """Check if character has a damage AoE trait on an equipped weapon.

    Returns (trait_name, tier) for the highest-tier damage AoE, or None.
    Only one fires per hit. Cleave is handled separately.
    """
    if not char or not char.gear:
        return None
    _DAMAGE_AOE_TRAITS = ["[Shockwave]", "[Whirlwind]", "[Inferno]", "[Tempest]", "[Voidgrip]"]
    best: Optional[Tuple[str, int]] = None
    for slot in (GearSlot.R_HAND, GearSlot.L_HAND):
        item = char.gear.slots.get(slot)
        if item and item.special_traits:
            for trait in _DAMAGE_AOE_TRAITS:
                if trait in item.special_traits:
                    tier = item.tier.value if item.tier else 1
                    if best is None or tier > best[1]:
                        best = (trait, tier)
    return best


def _apply_damage_aoe(state: GameState, char: Character, trait_name: str, tier: int,
                       damage_dealt: int, enemies: list, room_id: int) -> List[str]:
    """Apply auto-trigger damage AoE effect after a successful hit."""
    messages = []
    if trait_name == "[Shockwave]":
        targets = min(3, tier)
        dmg = sum(random.randint(1, 6) for _ in range(tier))
        hit_count = 0
        for enemy in list(enemies):
            if hit_count >= targets:
                break
            dr = enemy.get("dr", 0)
            actual = max(1, dmg - dr)
            enemy["hp"] = enemy.get("hp", 1) - actual
            messages.append(f"  [bold yellow]SHOCKWAVE![/] {enemy['name']} takes {actual} damage and is stunned!")
            state.stunned_enemies[enemy["name"]] = 1
            if enemy["hp"] <= 0:
                enemies.remove(enemy)
                messages.append(f"  {enemy['name']} is slain by shockwave!")
                state.enemies_slain += 1
                for qm in _check_quest_kill(state, room_id):
                    messages.append(f"  [QUEST] {qm}")
                loot_drop = generate_enemy_loot(enemy, state)
                if loot_drop:
                    state.room_loot.setdefault(room_id, []).append(loot_drop)
                    messages.append(f"  {enemy['name']} drops: {loot_drop['name']}!")
            hit_count += 1

    elif trait_name == "[Whirlwind]":
        dmg_base = sum(random.randint(1, 6) for _ in range(tier))
        dmg = max(1, int(dmg_base * 0.75))
        for enemy in list(enemies):
            dr = enemy.get("dr", 0)
            actual = max(1, dmg - dr)
            enemy["hp"] = enemy.get("hp", 1) - actual
            messages.append(f"  [bold yellow]WHIRLWIND![/] {enemy['name']} takes {actual} damage!")
            if enemy["hp"] <= 0:
                enemies.remove(enemy)
                messages.append(f"  {enemy['name']} is slain by whirlwind!")
                state.enemies_slain += 1
                for qm in _check_quest_kill(state, room_id):
                    messages.append(f"  [QUEST] {qm}")
                loot_drop = generate_enemy_loot(enemy, state)
                if loot_drop:
                    state.room_loot.setdefault(room_id, []).append(loot_drop)
                    messages.append(f"  {enemy['name']} drops: {loot_drop['name']}!")

    elif trait_name == "[Inferno]":
        targets = min(3, tier)
        dmg = sum(random.randint(1, 6) for _ in range(tier))
        hit_count = 0
        for enemy in list(enemies):
            if hit_count >= targets:
                break
            dr = enemy.get("dr", 0)
            actual = max(1, dmg - dr)
            enemy["hp"] = enemy.get("hp", 1) - actual
            messages.append(f"  [bold red]INFERNO![/] {enemy['name']} takes {actual} fire damage and is burning!")
            # Mark burning (tracked outside dict for simplicity — use blinded_enemies as burning proxy)
            state.blinded_enemies[enemy["name"]] = max(state.blinded_enemies.get(enemy["name"], 0), 2)
            if enemy["hp"] <= 0:
                enemies.remove(enemy)
                messages.append(f"  {enemy['name']} is consumed by flame!")
                state.enemies_slain += 1
                for qm in _check_quest_kill(state, room_id):
                    messages.append(f"  [QUEST] {qm}")
                loot_drop = generate_enemy_loot(enemy, state)
                if loot_drop:
                    state.room_loot.setdefault(room_id, []).append(loot_drop)
                    messages.append(f"  {enemy['name']} drops: {loot_drop['name']}!")
            hit_count += 1

    elif trait_name == "[Tempest]":
        targets = min(3, tier)
        dmg = sum(random.randint(1, 6) for _ in range(tier))
        hit_count = 0
        for enemy in list(enemies):
            if hit_count >= targets:
                break
            dr = enemy.get("dr", 0)
            actual = max(1, dmg - dr)
            enemy["hp"] = enemy.get("hp", 1) - actual
            messages.append(f"  [bold cyan]TEMPEST![/] Lightning strikes {enemy['name']} for {actual} damage!")
            if enemy["hp"] <= 0:
                enemies.remove(enemy)
                messages.append(f"  {enemy['name']} is slain by lightning!")
                state.enemies_slain += 1
                for qm in _check_quest_kill(state, room_id):
                    messages.append(f"  [QUEST] {qm}")
                loot_drop = generate_enemy_loot(enemy, state)
                if loot_drop:
                    state.room_loot.setdefault(room_id, []).append(loot_drop)
                    messages.append(f"  {enemy['name']} drops: {loot_drop['name']}!")
            hit_count += 1

    elif trait_name == "[Voidgrip]":
        targets = min(2, tier)
        dmg = sum(random.randint(1, 6) for _ in range(tier))
        hit_count = 0
        for enemy in list(enemies):
            if hit_count >= targets:
                break
            dr = enemy.get("dr", 0)
            actual = max(1, dmg - dr)
            enemy["hp"] = enemy.get("hp", 1) - actual
            messages.append(f"  [bold magenta]VOIDGRIP![/] {enemy['name']} takes {actual} necrotic damage and is blighted!")
            state.blinded_enemies[enemy["name"]] = max(state.blinded_enemies.get(enemy["name"], 0), 2)
            if enemy["hp"] <= 0:
                enemies.remove(enemy)
                messages.append(f"  {enemy['name']} withers away!")
                state.enemies_slain += 1
                for qm in _check_quest_kill(state, room_id):
                    messages.append(f"  [QUEST] {qm}")
                loot_drop = generate_enemy_loot(enemy, state)
                if loot_drop:
                    state.room_loot.setdefault(room_id, []).append(loot_drop)
                    messages.append(f"  {enemy['name']} drops: {loot_drop['name']}!")
            hit_count += 1

    if not enemies:
        state.cleared_rooms.add(room_id)
        messages.append("Room cleared!")
    return messages


def _perform_attack(state: GameState, char: Character, target_index: int) -> List[str]:
    """Core attack logic used by attack action, command bonus attack, etc."""
    messages = []
    room_id = state.current_room_id
    enemies = state.room_enemies.get(room_id, [])

    if not enemies:
        messages.append("There are no enemies here to fight.")
        return messages

    if target_index < 0 or target_index >= len(enemies):
        messages.append(f"Invalid target. Choose 0-{len(enemies)-1}.")
        return messages

    enemy = enemies[target_index]
    enemy_name = enemy["name"]
    enemy_defense = enemy.get("defense", 10)
    enemy_hp = enemy.get("hp", 5)

    # Check for bolster bonus
    bonus_dice = state.bolster_targets.pop(char.name, 0)

    check = char.make_check(StatType.MIGHT, enemy_defense)
    # Add bolster bonus dice if present
    if bonus_dice > 0:
        bolster_rolls = [random.randint(1, 6) for _ in range(bonus_dice)]
        bolster_total = sum(bolster_rolls)
        check = CheckResult(
            success=(check.total + bolster_total) >= enemy_defense,
            total=check.total + bolster_total,
            rolls=check.rolls + bolster_rolls,
            modifier=check.modifier,
            dc=check.dc,
            dice_count=check.dice_count + bonus_dice,
        )
        messages.append(f"  (Bolstered! +{bonus_dice}d6 = {bolster_rolls})")

    # First-Strike Proficiency: +1d6 on the very first attack of the run
    if not state.first_strike_used:
        state.first_strike_used = True
        fs_roll = random.randint(1, 6)
        check = CheckResult(
            success=(check.total + fs_roll) >= enemy_defense,
            total=check.total + fs_roll,
            rolls=check.rolls + [fs_roll],
            modifier=check.modifier,
            dc=check.dc,
            dice_count=check.dice_count + 1,
        )
        messages.append(f"  [bold cyan]FIRST STRIKE![/] +1d6 = [{fs_roll}]")

    # WO-V61.0: critical_roll anchor
    if check.rolls:
        if all(r == 6 for r in check.rolls):
            state.log_event("critical_roll", roller=char.name,
                            roll_type="attack", result="critical",
                            context=f"vs {enemy_name}")
            _broadcast_anchor(state, "critical_roll", roller=char.name,
                               roll_type="attack", result="critical",
                               context=f"vs {enemy_name}")
        elif all(r == 1 for r in check.rolls):
            state.log_event("critical_roll", roller=char.name,
                            roll_type="attack", result="fumble",
                            context=f"vs {enemy_name}")
            _broadcast_anchor(state, "critical_roll", roller=char.name,
                               roll_type="attack", result="fumble",
                               context=f"vs {enemy_name}")

    if check.success:
        raw_damage = max(1, check.total - enemy_defense + 2)
        enemy_dr = enemy.get("dr", 0)
        damage_dealt = max(1, raw_damage - enemy_dr)
        dr_note = f" (DR absorbs {raw_damage - damage_dealt})" if enemy_dr > 0 and raw_damage > damage_dealt else ""
        enemy["hp"] = enemy_hp - damage_dealt
        messages.append(
            f"{char.name} ATTACKS ({check.total} vs DEF {enemy_defense}): HIT! "
            f"Deals {damage_dealt} damage to {enemy_name}.{dr_note} "
            f"({max(0, enemy['hp'])} HP remaining)"
        )

        if enemy["hp"] <= 0:
            enemies.pop(target_index)
            messages.append(f"{enemy_name} is slain!")
            state.enemies_slain += 1
            for qm in _check_quest_kill(state, room_id):
                messages.append(f"[QUEST] {qm}")
            # WO-V37.0: Log kill event
            state.log_event("kill", target=enemy_name,
                            tier=enemy.get("tier", 1), room_id=room_id)
            # WO-V56.0: Memory shard for kill event
            mem = getattr(state.engine, 'memory_engine', None)
            if mem:
                mem.create_shard(
                    f"Killed {enemy_name} in room {room_id}",
                    shard_type="ANCHOR",
                    tags=["combat", "kill", f"tier_{enemy.get('tier', 1)}"],
                )
            # Rot Hunter death handling
            if enemy.get("is_rot_hunter") and state.rot_hunter:
                state.rot_hunter["active"] = False
                messages.append("[bold magenta]The Rot Hunter collapses! The pursuit ends.[/]")
                rot_loot = _generate_rot_hunter_loot(state)
                state.room_loot.setdefault(room_id, []).append(rot_loot)
                messages.append(f"  The Rot Hunter drops: {rot_loot['name']}!")
            else:
                # Normal loot drop check
                loot_drop = generate_enemy_loot(enemy, state)
                if loot_drop:
                    state.room_loot.setdefault(room_id, []).append(loot_drop)
                    messages.append(f"  {enemy_name} drops: {loot_drop['name']}!")
            if not enemies:
                state.cleared_rooms.add(room_id)
                messages.append("Room cleared!")
                # WO-V37.0: Log room cleared
                room_node = state.engine.dungeon_graph.get_room(room_id) if state.engine and state.engine.dungeon_graph else None
                state.log_event("room_cleared", room_id=room_id,
                                room_type=room_node.room_type.value if room_node and hasattr(room_node.room_type, 'value') else "unknown")

        # WO-V32.0: [Cleave] AoE splash to additional enemies
        if check.success and enemies:
            cleave_data = _check_cleave_trait(char)
            if cleave_data:
                cleave_count = cleave_data["cleave_targets"]
                cleave_pct = cleave_data["cleave_damage_pct"]
                splash_dmg = max(1, int(damage_dealt * cleave_pct))
                cleaved = 0
                for ci, cleave_enemy in enumerate(list(enemies)):
                    if cleaved >= cleave_count:
                        break
                    if cleave_enemy is enemy:
                        continue  # Skip primary target (may already be dead/removed)
                    cleave_dr = cleave_enemy.get("dr", 0)
                    cleave_actual = max(1, splash_dmg - cleave_dr)
                    cleave_enemy["hp"] = cleave_enemy.get("hp", 1) - cleave_actual
                    messages.append(
                        f"  [bold yellow]CLEAVE![/] {char.name} strikes {cleave_enemy['name']} "
                        f"for {cleave_actual} splash damage! ({max(0, cleave_enemy['hp'])} HP)"
                    )
                    if cleave_enemy["hp"] <= 0:
                        enemies.remove(cleave_enemy)
                        messages.append(f"  {cleave_enemy['name']} is slain by cleave!")
                        state.enemies_slain += 1
                        for qm in _check_quest_kill(state, room_id):
                            messages.append(f"  [QUEST] {qm}")
                        # WO-V37.0: Log cleave kill
                        state.log_event("kill", target=cleave_enemy['name'],
                                        tier=cleave_enemy.get("tier", 1), room_id=room_id)
                        loot_drop = generate_enemy_loot(cleave_enemy, state)
                        if loot_drop:
                            state.room_loot.setdefault(room_id, []).append(loot_drop)
                            messages.append(f"  {cleave_enemy['name']} drops: {loot_drop['name']}!")
                    cleaved += 1
                if not enemies:
                    state.cleared_rooms.add(room_id)
                    messages.append("Room cleared!")
                    room_node = state.engine.dungeon_graph.get_room(room_id) if state.engine and state.engine.dungeon_graph else None
                    state.log_event("room_cleared", room_id=room_id,
                                    room_type=room_node.room_type.value if room_node and hasattr(room_node.room_type, 'value') else "unknown")

        # WO-V36.0: Auto-trigger damage AoE (highest tier wins if no Cleave)
        if check.success and enemies and not _check_cleave_trait(char):
            aoe_data = _check_damage_aoe_trait(char)
            if aoe_data:
                pre_count = len(enemies)
                aoe_msgs = _apply_damage_aoe(state, char, aoe_data[0], aoe_data[1],
                                              damage_dealt, enemies, room_id)
                messages.extend(aoe_msgs)
                # WO-V37.0: Log AoE activation
                state.log_event("aoe_used", trait=aoe_data[0], by=char.name,
                                targets_hit=pre_count - len(enemies))

        # WO-V36.0: Apply Rally bonus dice if present
        rally_bonus = state.party_bonus_dice.pop(char.name, 0)
        if rally_bonus > 0 and not check.success:
            # Rally was consumed but missed — no effect
            pass

    else:
        messages.append(
            f"{char.name} ATTACKS ({check.total} vs DEF {enemy_defense}): MISS! "
            f"{enemy_name} dodges the strike."
        )

    return messages


def action_attack(state: GameState, target_index: int, char: Optional[Character] = None) -> List[str]:
    """Attack an enemy. Uses active character if char not specified."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    messages = _perform_attack(state, char, target_index)
    return messages


def action_guard(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Guard: +2 Defense until this character's next turn."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    state.guarding.add(char.name)
    return [f"{char.name} takes a defensive stance. (+2 DEF until next turn)"]


def action_intercept(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Brace to intercept the next attack on any ally. Requires [Intercept] gear."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    if not char.gear.has_trait("[Intercept]"):
        return [f"{char.name} has no gear with [Intercept] (e.g., a shield)."]

    state.intercepting = char.name
    return [f"{char.name} braces their shield to intercept! (Next ally hit redirected here, +2 DR)"]


def _find_party_member(state: GameState, target_name: str) -> Optional[Character]:
    """Find a party member by name (case-insensitive partial match)."""
    target_lower = target_name.lower()
    for c in state.engine.get_active_party():
        if c.name.lower() == target_lower or c.name.lower().startswith(target_lower):
            return c
    return None


def action_command(state: GameState, target_name: str, char: Optional[Character] = None) -> List[str]:
    """Command: Wits vs DC 12. Target ally immediately makes a bonus attack."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    target = _find_party_member(state, target_name)
    if not target:
        return [f"No alive party member named '{target_name}'."]
    if target is char:
        return ["You can't command yourself."]

    check = char.make_check(StatType.WITS, 12)
    if check.success:
        messages = [f"{char.name} COMMANDS {target.name}! (Wits {check.total} vs DC 12: SUCCESS)"]
        enemies = state.room_enemies.get(state.current_room_id, [])
        if enemies:
            messages.append(f"  {target.name} makes a bonus attack!")
            messages.extend(_perform_attack(state, target, 0))
        else:
            messages.append("  But there are no enemies to attack.")
        return messages
    else:
        return [f"{char.name} tries to coordinate {target.name} but fumbles the order. (Wits {check.total} vs DC 12: FAIL)"]


def action_bolster(state: GameState, target_name: str, char: Optional[Character] = None) -> List[str]:
    """Bolster: Aether vs DC 12. Grant target +2d6 on their next roll."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    target = _find_party_member(state, target_name)
    if not target:
        return [f"No alive party member named '{target_name}'."]

    check = char.make_check(StatType.AETHER, 12)
    if check.success:
        state.bolster_targets[target.name] = 2
        return [f"{char.name} BOLSTERS {target.name}! (Aether {check.total} vs DC 12: SUCCESS) +2d6 on next roll."]
    else:
        return [f"{char.name} tries to bolster {target.name} but the magic fizzles. (Aether {check.total} vs DC 12: FAIL)"]


def action_triage(state: GameState, target_name: str, char: Optional[Character] = None) -> List[str]:
    """Triage: Wits vs DC 12. Heal target 1d6 + Wits mod (half on fail)."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    target = _find_party_member(state, target_name)
    if not target:
        return [f"No alive party member named '{target_name}'."]

    if target.current_hp >= target.max_hp:
        return [f"{target.name} is already at full health."]

    wits_mod = char.get_stat_mod(StatType.WITS)
    heal_roll = random.randint(1, 6)
    full_heal = heal_roll + max(0, wits_mod)

    check = char.make_check(StatType.WITS, 12)
    if check.success:
        old_hp = target.current_hp
        actual = target.heal(full_heal)
        msg = f"{char.name} performs TRIAGE on {target.name}! (Wits {check.total} vs DC 12: SUCCESS) Healed {actual} HP ({target.current_hp}/{target.max_hp})."
        # WO-V61.0: ally_saved anchor
        was_critical = (old_hp / max(1, target.max_hp)) < 0.2
        now_safe = (target.current_hp / max(1, target.max_hp)) >= 0.2
        if was_critical and now_safe:
            state.log_event("ally_saved", savior=char.name, saved=target.name, method="triage")
            _broadcast_anchor(state, "ally_saved", savior=char.name, saved=target.name, method="triage")
        return [msg]
    else:
        half_heal = max(1, full_heal // 2)
        old_hp = target.current_hp
        actual = target.heal(half_heal)
        msg = f"{char.name} tries triage on {target.name}. (Wits {check.total} vs DC 12: FAIL) Partial heal: {actual} HP ({target.current_hp}/{target.max_hp})."
        # WO-V61.0: ally_saved anchor
        was_critical = (old_hp / max(1, target.max_hp)) < 0.2
        now_safe = (target.current_hp / max(1, target.max_hp)) >= 0.2
        if was_critical and now_safe:
            state.log_event("ally_saved", savior=char.name, saved=target.name, method="triage")
            _broadcast_anchor(state, "ally_saved", savior=char.name, saved=target.name, method="triage")
        return [msg]


def action_sanctify(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Sanctify Area: Aether vs DC 14. Enemies take 1d6 at start of enemy phase."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    check = char.make_check(StatType.AETHER, 14)
    if check.success:
        state.sanctified = True
        return [f"{char.name} SANCTIFIES the area! (Aether {check.total} vs DC 14: SUCCESS) Enemies take 1d6 holy damage this round."]
    else:
        return [f"{char.name} tries to sanctify but the ritual fails. (Aether {check.total} vs DC 14: FAIL)"]


def action_summon(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Summon: Aether vs DC 12. Conjure a spirit minion that joins the party for 3 rounds."""
    char = char or state.active_character
    if not char:
        return ["No active character."]

    if not char.gear.has_trait("[Summon]"):
        return [f"{char.name} has no summoning focus equipped. (Requires gear with [Summon])"]

    # Limit: max 1 active minion per summoner
    for c in state.engine.party:
        if isinstance(c, Minion) and c.is_alive():
            return [f"{char.name} already has an active spirit. Dismiss it first or wait for it to fade."]

    check = char.make_check(StatType.AETHER, 12)
    if check.success:
        aether_mod = char.get_stat_mod(StatType.AETHER)
        minion = create_minion(char.name, aether_mod)
        state.engine.add_to_party(minion)
        # WO-V61.0: rare_item_used anchor (Summon trait)
        gear_item = None
        for slot_name, item in char.gear.slots.items():
            if item and item.special_traits and "[Summon]" in item.special_traits:
                gear_item = item
                break
        if gear_item and hasattr(gear_item, 'tier') and gear_item.tier and gear_item.tier.value >= 3:
            state.log_event("rare_item_used", item_name=gear_item.name,
                            tier=gear_item.tier.value, user=char.name, trait="Summon")
            _broadcast_anchor(state, "rare_item_used", item_name=gear_item.name,
                               tier=gear_item.tier.value, user=char.name, trait="Summon")
        return [
            f"{char.name} SUMMONS a spirit! (Aether {check.total} vs DC 12: SUCCESS)",
            f"  {minion.name} joins the party ({minion.current_hp} HP, {minion.summon_duration} rounds)."
        ]
    else:
        return [f"{char.name} tries to summon but the Aether slips away. (Aether {check.total} vs DC 12: FAIL)"]


# WO-V36.0: Manual AoE Combat Commands
def _has_trait_any_slot(char: Character, trait: str) -> Optional[int]:
    """Return the tier of the first item with the given trait, or None."""
    if not char or not char.gear:
        return None
    for slot_name, item in char.gear.slots.items():
        if item and item.special_traits and trait in item.special_traits:
            return item.tier.value if item.tier else 1
    return None


def action_flash(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Flash: Wits DC 12. Blind 1-2 enemies for 2 rounds (-2 attack accuracy)."""
    char = char or state.active_character
    if not char:
        return ["No active character."]
    tier = _has_trait_any_slot(char, "[Flash]")
    if tier is None:
        return [f"{char.name} has no Flash gear equipped. (Requires [Flash] trait)"]
    room_id = state.current_room_id
    enemies = state.room_enemies.get(room_id, [])
    if not enemies:
        return ["No enemies to blind."]
    check = char.make_check(StatType.WITS, 12)
    if not check.success:
        return [f"{char.name} tries to flash but the light fizzles. (Wits {check.total} vs DC 12: FAIL)"]
    targets = min(2, tier, len(enemies))
    msgs = [f"{char.name} unleashes a blinding FLASH! (Wits {check.total} vs DC 12: SUCCESS)"]
    for enemy in enemies[:targets]:
        state.blinded_enemies[enemy["name"]] = 2
        msgs.append(f"  {enemy['name']} is blinded for 2 rounds! (-2 attack accuracy)")
    return msgs


def action_snare(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Snare: Wits DC 12. Reduce defense of 1-3 enemies by tier value."""
    char = char or state.active_character
    if not char:
        return ["No active character."]
    tier = _has_trait_any_slot(char, "[Snare]")
    if tier is None:
        return [f"{char.name} has no Snare gear equipped. (Requires [Snare] trait)"]
    room_id = state.current_room_id
    enemies = state.room_enemies.get(room_id, [])
    if not enemies:
        return ["No enemies to snare."]
    check = char.make_check(StatType.WITS, 12)
    if not check.success:
        return [f"{char.name} tries to snare but misses. (Wits {check.total} vs DC 12: FAIL)"]
    targets = min(3, tier, len(enemies))
    msgs = [f"{char.name} throws a SNARE! (Wits {check.total} vs DC 12: SUCCESS)"]
    for enemy in enemies[:targets]:
        state.defense_debuffs[enemy["name"]] = tier
        enemy["defense"] = enemy.get("defense", 10) - tier
        msgs.append(f"  {enemy['name']}'s defense reduced by {tier}!")
    return msgs


def action_rally(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Rally: Wits DC 10. Grant +1 bonus die to ALL allies' next attack."""
    char = char or state.active_character
    if not char:
        return ["No active character."]
    tier = _has_trait_any_slot(char, "[Rally]")
    if tier is None:
        return [f"{char.name} has no Rally gear equipped. (Requires [Rally] trait)"]
    check = char.make_check(StatType.WITS, 10)
    if not check.success:
        return [f"{char.name} tries to rally but falters. (Wits {check.total} vs DC 10: FAIL)"]
    alive = state.engine.get_active_party()
    msgs = [f"{char.name} sounds the RALLY! (Wits {check.total} vs DC 10: SUCCESS)"]
    for ally in alive:
        if ally is not char:
            state.party_bonus_dice[ally.name] = state.party_bonus_dice.get(ally.name, 0) + 1
            msgs.append(f"  {ally.name} gains +1 bonus die on next attack!")
    return msgs


def action_mending(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Mending: Wits DC 10. Heal 1d6*tier HP to ALL party members."""
    char = char or state.active_character
    if not char:
        return ["No active character."]
    tier = _has_trait_any_slot(char, "[Mending]")
    if tier is None:
        return [f"{char.name} has no Mending gear equipped. (Requires [Mending] trait)"]
    check = char.make_check(StatType.WITS, 10)
    if not check.success:
        return [f"{char.name} tries to mend but the herbs scatter. (Wits {check.total} vs DC 10: FAIL)"]
    heal = sum(random.randint(1, 6) for _ in range(tier))
    alive = state.engine.get_active_party()
    msgs = [f"{char.name} invokes MENDING! (Wits {check.total} vs DC 10: SUCCESS) — {heal} HP to all!"]
    for ally in alive:
        old_hp = ally.current_hp
        ally.current_hp = min(ally.max_hp, ally.current_hp + heal)
        healed = ally.current_hp - old_hp
        if healed > 0:
            msgs.append(f"  {ally.name} healed for {healed} HP ({ally.current_hp}/{ally.max_hp})")
            # WO-V61.0: ally_saved anchor
            was_critical = (old_hp / max(1, ally.max_hp)) < 0.2
            now_safe = (ally.current_hp / max(1, ally.max_hp)) >= 0.2
            if was_critical and now_safe:
                state.log_event("ally_saved", savior=char.name, saved=ally.name, method="mending")
                _broadcast_anchor(state, "ally_saved", savior=char.name, saved=ally.name, method="mending")
    return msgs


def action_renewal(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Renewal: Aether DC 12. HoT: 1d4 HP/round for 3 rounds to all allies."""
    char = char or state.active_character
    if not char:
        return ["No active character."]
    tier = _has_trait_any_slot(char, "[Renewal]")
    if tier is None:
        return [f"{char.name} has no Renewal gear equipped. (Requires [Renewal] trait)"]
    check = char.make_check(StatType.AETHER, 12)
    if not check.success:
        return [f"{char.name} tries renewal but the Aether dissipates. (Aether {check.total} vs DC 12: FAIL)"]
    alive = state.engine.get_active_party()
    msgs = [f"{char.name} channels RENEWAL! (Aether {check.total} vs DC 12: SUCCESS) — HoT for 3 rounds!"]
    for ally in alive:
        state.party_hot[ally.name] = 3
        msgs.append(f"  {ally.name} gains regeneration (1d4 HP/round for 3 rounds)")
    return msgs


def action_aegis(state: GameState, char: Optional[Character] = None) -> List[str]:
    """Aegis: Grit DC 10. Grant +tier DR to ALL allies for 2 rounds."""
    char = char or state.active_character
    if not char:
        return ["No active character."]
    tier = _has_trait_any_slot(char, "[Aegis]")
    if tier is None:
        return [f"{char.name} has no Aegis gear equipped. (Requires [Aegis] trait)"]
    check = char.make_check(StatType.GRIT, 10)
    if not check.success:
        return [f"{char.name} tries to raise an aegis but fails. (Grit {check.total} vs DC 10: FAIL)"]
    state.party_dr_buff = (tier, 2)
    msgs = [f"{char.name} raises an AEGIS! (Grit {check.total} vs DC 10: SUCCESS) — +{tier} DR for 2 rounds!"]
    return msgs


# WO-V36.0: In-Game Companion Command
def action_companion(state: GameState) -> List[str]:
    """Summon or check AI companion status. Hub-only."""
    if not state.in_settlement:
        return ["Companions can only be summoned at Emberhome hub."]

    # Check if we already have a companion
    existing_companion = None
    for name, agent in state.autopilot_agents.items():
        existing_companion = name
        break

    if existing_companion:
        # Show companion status
        companion_char = None
        for c in state.engine.party:
            if c.name == existing_companion:
                companion_char = c
                break
        if companion_char:
            return [
                f"[bold cyan]Companion: {companion_char.name}[/]",
                f"  HP: {companion_char.current_hp}/{companion_char.max_hp}",
                f"  Archetype: {state.autopilot_agents[existing_companion].personality.archetype if hasattr(state.autopilot_agents[existing_companion], 'personality') else 'standard'}",
                f"  Status: Active (AI-controlled)",
            ]
        return [f"Companion {existing_companion} is registered but not in party."]

    # Summon a new companion
    if len(state.engine.party) >= 6:
        return ["Party is full (6/6). Cannot summon a companion."]

    try:
        from codex.games.burnwillow.autopilot import create_ai_character
        from codex.games.burnwillow.engine import create_starter_gear as _csg
        personality, companion_name, stats, bio, quirk = create_ai_character()
        companion = Character(companion_name, **stats)
        _csg(companion)
        state.engine.add_to_party(companion)
        agent = AutopilotAgent(personality, biography=bio)
        state.autopilot_agents[companion_name] = agent
        state.companion_mode = True
    except Exception:
        # Fallback: create basic companion with default stats
        companion_name = "Ashara"
        companion = Character(companion_name, might=2, wits=2, grit=2, aether=2)
        state.engine.add_to_party(companion)
        state.companion_mode = True

    # Register NPC personality if narrative engine available
    if state.narrative and hasattr(state.narrative, 'register_npc'):
        try:
            state.narrative.register_npc(companion_name, {
                "role": "companion",
                "archetype": "guardian",
                "personality": "Loyal AI companion summoned at Emberhome.",
            })
        except Exception:
            pass

    # WO-V37.0: Log companion summoned
    state.log_event("companion_summoned", name=companion_name)

    return [
        f"[bold cyan]{companion_name} joins your party as an AI companion![/]",
        f"  HP: {companion.current_hp}/{companion.max_hp}",
        f"  {companion_name} will act automatically in combat and exploration.",
        f"  Type 'companion' again to check status.",
    ]


RETREAT_DC = 12


def _find_nearest_cleared_room(state: GameState) -> Optional[int]:
    """BFS from current room to find the nearest cleared room to retreat to."""
    if not state.engine or not state.engine.dungeon_graph:
        return None
    graph = state.engine.dungeon_graph
    start = state.engine.current_room_id
    if not state.cleared_rooms:
        return None

    visited = {start}
    queue = list(graph.get_room(start).connections) if graph.get_room(start) else []
    visited.update(queue)

    while queue:
        current = queue.pop(0)
        if current in state.cleared_rooms:
            return current
        room = graph.get_room(current)
        if room:
            for neighbor_id in room.connections:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)
    return None


def _rot_hunter_retreat_pursuit(state: GameState, retreat_room: int) -> List[str]:
    """After a successful retreat, 25% chance the Rot Hunter follows immediately."""
    messages: List[str] = []
    if not state.rot_hunter or not state.rot_hunter.get("active"):
        return messages

    if random.random() < 0.25:
        state.rot_hunter["room_id"] = retreat_room
        messages.append(
            "[bold magenta]The Rot Hunter pursues! It follows you![/]"
        )
        state.room_enemies.setdefault(retreat_room, []).append(dict(state.rot_hunter))
        state.start_combat()
        messages.append("Combat begins!")
    else:
        messages.append("[dim magenta]The Rot Hunter does not pursue... for now.[/]")
    return messages


def action_retreat(state: GameState) -> List[str]:
    """Attempt to flee combat. Grit DC 12 for the lead character.

    Success: end combat, retreat to nearest cleared room, +1 Doom.
    Failure: lose turn, enemies get free attack, +1 Doom.
    Rot Hunter: retreat allowed; 25% chance it pursues to the new room.
    """
    messages: List[str] = []
    char = state.active_character or (state.engine.party[0] if state.engine.party else None)
    if not char:
        return ["No active character."]

    room_id = state.current_room_id
    enemies = state.room_enemies.get(room_id, [])
    if not enemies:
        return ["No enemies to retreat from."]

    # Always costs +1 Doom
    doom_events = _advance_doom_scaled(state, 1)

    # Grit check
    check = char.make_check(StatType.GRIT, RETREAT_DC)

    if check.success:
        retreat_room = _find_nearest_cleared_room(state)
        if retreat_room is None:
            messages.append(
                f"Retreat CHECK PASSED (Grit {check.total} vs DC {RETREAT_DC}), "
                f"but there is nowhere to fall back to!"
            )
            # Fall through to failure path
        else:
            messages.append(
                f"[bold green]RETREAT![/] (Grit {check.total} vs DC {RETREAT_DC}): "
                f"The party disengages and falls back!"
            )
            state.engine.current_room_id = retreat_room
            room_node = state.engine.dungeon_graph.get_room(retreat_room)
            if room_node:
                state.engine.player_pos = (
                    room_node.x + room_node.width // 2,
                    room_node.y + room_node.height // 2,
                )
            state.end_combat()

            # Rot Hunter pursuit check
            rot_msgs = _rot_hunter_retreat_pursuit(state, retreat_room)
            messages.extend(rot_msgs)

            for event in doom_events:
                messages.append(event)
            messages.extend(_process_doom_advancement(state, doom_events))
            return messages

    # Failure path (or no retreat room)
    messages.append(
        f"[bold red]Retreat FAILED[/] (Grit {check.total} vs DC {RETREAT_DC}): "
        f"You stumble! The enemy capitalizes!"
    )

    # Enemies get a free attack
    for e in enemies:
        if e.get("hp", 0) > 0:
            alive = state.engine.get_active_party()
            if not alive:
                break
            target = random.choice(alive)
            dmg_str = e.get("damage", "1d6")
            try:
                if "d" in str(dmg_str):
                    parts = str(dmg_str).split("d")
                    n = int(parts[0]) if parts[0] else 1
                    d = int(parts[1].split("+")[0].split("-")[0])
                    raw_dmg = sum(random.randint(1, d) for _ in range(n))
                else:
                    raw_dmg = int(dmg_str)
            except (ValueError, IndexError):
                raw_dmg = random.randint(1, 6)
            actual = target.take_damage(raw_dmg)
            messages.append(f"  {e['name']} strikes {target.name} for {actual} damage!")

    for event in doom_events:
        messages.append(event)
    messages.extend(_process_doom_advancement(state, doom_events))
    return messages


def _enemy_phase(state: GameState) -> List[str]:
    """Run the enemy counter-attack phase. Enemies attack random alive party members."""
    messages = []
    room_id = state.current_room_id
    enemies = state.room_enemies.get(room_id, [])

    if not enemies:
        return messages

    alive_party = state.engine.get_active_party()
    if not alive_party:
        return messages

    # Sanctify damage
    if state.sanctified:
        sanctify_dmg = random.randint(1, 6)
        messages.append(f"Holy energy sears the enemies for {sanctify_dmg} damage!")
        for enemy in list(enemies):
            enemy["hp"] = enemy.get("hp", 5) - sanctify_dmg
            if enemy["hp"] <= 0:
                messages.append(f"  {enemy['name']} is destroyed by sanctified ground!")
                loot_drop = generate_enemy_loot(enemy, state)
                if loot_drop:
                    state.room_loot.setdefault(room_id, []).append(loot_drop)
                    messages.append(f"  {enemy['name']} drops: {loot_drop['name']}!")
                enemies.remove(enemy)
        if not enemies:
            state.cleared_rooms.add(room_id)
            messages.append("Room cleared!")
            return messages

    # WO-V36.0: Apply Renewal HoT at start of enemy phase (before enemies act)
    for ally in list(alive_party):
        if ally.name in state.party_hot and ally.is_alive():
            hot_heal = random.randint(1, 4)
            old_hp = ally.current_hp
            ally.current_hp = min(ally.max_hp, ally.current_hp + hot_heal)
            healed = ally.current_hp - old_hp
            if healed > 0:
                messages.append(f"  [green]Renewal heals {ally.name} for {healed} HP ({ally.current_hp}/{ally.max_hp})[/]")

    # Each surviving enemy attacks a random party member
    for enemy in enemies:
        if not alive_party:
            break

        # WO-V36.0: Skip stunned enemies
        if enemy["name"] in state.stunned_enemies:
            messages.append(f"  {enemy['name']} is [bold yellow]STUNNED[/] and cannot act!")
            continue

        # WO-V32.0: Check for AoE enemy attacks (e.g. "AOE 10ft", "AOE slam 15ft")
        enemy_special = enemy.get("special", "")
        is_aoe = "AOE" in enemy_special.upper() if enemy_special else False

        enemy_damage_str = enemy.get("damage", "1d6")
        try:
            num_dice = int(enemy_damage_str.split("d")[0])
        except (ValueError, IndexError):
            num_dice = 1

        # WO-V36.0: Blinded enemies have -2 accuracy (reduce dice pool, min 1)
        if enemy["name"] in state.blinded_enemies:
            num_dice = max(1, num_dice - 1)
            messages.append(f"  {enemy['name']} is [dim]blinded[/] (-1 attack die)")

        # AoE enemies attack ALL alive party members
        targets_for_attack = list(alive_party) if is_aoe else [select_target_weighted(alive_party)]
        if is_aoe and len(targets_for_attack) > 1:
            messages.append(f"  [bold red]{enemy['name']} unleashes an area attack![/]")

        for target in targets_for_attack:
            if not target.is_alive():
                continue

            # Check for intercept redirect (only for single-target)
            intercepted = False
            if not is_aoe and state.intercepting:
                interceptor = _find_party_member(state, state.intercepting)
                if interceptor and interceptor is not target and interceptor.is_alive():
                    messages.append(f"  {interceptor.name} INTERCEPTS the attack on {target.name}!")
                    target = interceptor
                    intercepted = True
                    state.intercepting = None  # Consumed

            # Calculate defense (guard bonus)
            target_defense = target.get_defense()
            if target.name in state.guarding:
                target_defense += 2

            enemy_roll = roll_dice_pool(num_dice, 0, target_defense)
            if enemy_roll["success"]:
                raw_damage = max(1, enemy_roll["total"] - target_defense + 1)
                # WO-V32.0: Apply party-size damage multiplier
                dmg_mult = enemy.get("_dmg_mult", 1.0)
                if dmg_mult != 1.0:
                    raw_damage = max(1, int(raw_damage * dmg_mult))
                # Intercept gives +2 DR bonus on top of gear DR
                if intercepted:
                    raw_damage = max(0, raw_damage - 2)
                # WO-V36.0: Aegis DR buff
                aegis_dr, aegis_rounds = state.party_dr_buff
                if aegis_dr > 0 and aegis_rounds > 0:
                    raw_damage = max(0, raw_damage - aegis_dr)
                actual_damage = target.take_damage(raw_damage)
                messages.append(
                    f"  {enemy['name']} attacks {target.name} for {raw_damage} raw damage! "
                    f"(DR absorbs {raw_damage - actual_damage}, takes {actual_damage})"
                )
                # WO-V61.0: near_death anchor
                if target.is_alive() and target.current_hp / max(1, target.max_hp) < 0.2:
                    if target.name not in state._near_death_emitted:
                        state._near_death_emitted.add(target.name)
                        state.log_event("near_death", name=target.name,
                                        hp=target.current_hp, max_hp=target.max_hp,
                                        attacker=enemy['name'])
                        _broadcast_anchor(state, "near_death", name=target.name,
                                          hp=target.current_hp, max_hp=target.max_hp,
                                          attacker=enemy['name'])
                if not target.is_alive():
                    if isinstance(target, Minion):
                        messages.append(f"  {target.name} dissipates!")
                        state.engine.remove_from_party(target)
                    else:
                        messages.append(f"  {target.name} has FALLEN!")
                        # WO-V37.0: Log party death
                        state.log_event("party_death", name=target.name)
                        _broadcast_anchor(state, "party_death", name=target.name)
                        # WO-V61.0: companion_fell anchor
                        if target.name in state.autopilot_agents:
                            agent = state.autopilot_agents[target.name]
                            state.log_event("companion_fell", name=target.name,
                                            archetype=getattr(agent.personality, 'archetype', 'unknown'),
                                            cause=enemy['name'])
                            _broadcast_anchor(state, "companion_fell", name=target.name,
                                              archetype=getattr(agent.personality, 'archetype', 'unknown'),
                                              cause=enemy['name'])
                    alive_party = state.engine.get_active_party()
            else:
                messages.append(f"  {enemy['name']} swings at {target.name} and misses!")

    # Tick minion durations
    for char in list(state.engine.party):
        if isinstance(char, Minion):
            if not char.tick_duration():
                messages.append(f"  {char.name} fades back to the Aether.")
                state.engine.remove_from_party(char)

    return messages


def run_combat_round(state: GameState) -> List[str]:
    """Run one full combat round: each party member acts, then enemies retaliate."""
    messages = []
    con = state.console
    room_id = state.current_room_id
    enemies = state.room_enemies.get(room_id, [])

    if not enemies:
        state.end_combat()
        return ["No enemies remain. Combat over."]

    state.combat_round += 1
    state.clear_combat_effects()
    messages.append(f"--- Combat Round {state.combat_round} ---")

    alive = state.engine.get_active_party()
    if not alive:
        return messages

    # Party phase: each alive member takes an action
    for i, char in enumerate(alive):
        if not enemies:
            break

        state.active_character_index = i
        minion_tag = " [SUMMON]" if isinstance(char, Minion) else ""
        messages.append(f"\n[{char.name}{minion_tag}] HP:{char.current_hp}/{char.max_hp} - Your action?")
        actions_line1 = "  attack <#> | guard | intercept | bolster <name> | triage <name>"
        actions_line2 = "  command <name> | sanctify"
        if char.gear.has_trait("[Summon]"):
            actions_line2 += " | summon"
        # WO-V36.0: Show AoE commands if gear equipped
        aoe_cmds = []
        for _trait, _cmd in [("[Flash]", "flash"), ("[Snare]", "snare"), ("[Rally]", "rally"),
                              ("[Mending]", "mending"), ("[Renewal]", "renewal"), ("[Aegis]", "aegis")]:
            if char.gear.has_trait(_trait):
                aoe_cmds.append(_cmd)
        if aoe_cmds:
            actions_line2 += " | " + " | ".join(aoe_cmds)
        actions_line2 += " | look | retreat"
        move_hint = f"  [dim]Move: n/s/e/w (free, {state.remaining_movement}ft left)[/dim]"
        messages.append(actions_line1)
        messages.append(actions_line2)
        messages.append(move_hint)

        # Print current messages so far, then get input
        con.print()
        for msg in messages:
            con.print(f"  {msg}")
        messages.clear()

        # Show enemies
        for ei, e in enumerate(enemies):
            boss_tag = " [BOSS]" if e.get("is_boss") else ""
            con.print(f"    [{ei}] {e['name']}{boss_tag}: {e.get('hp', '?')} HP")

        # Get combat action input (loop allows free movement before action)
        while True:
            # WO-V31.0: Autopilot combat interception
            if _should_autopilot(state, char):
                import time as _time
                snapshot = build_combat_snapshot(state, char)
                agent = state.autopilot_agents.get(
                    char.name,
                    next(iter(state.autopilot_agents.values()), None)
                )
                if agent:
                    raw = agent.decide_combat(snapshot)
                    con.print(f"  [dim][AI: {char.name}] {raw}[/dim]")
                    _time.sleep(state.autopilot_delay * 0.3)
                else:
                    raw = "attack 0"
            else:
                try:
                    raw = Prompt.ask(
                        f"  [bold {THEME_CFG.color_current}]{char.name}>[/]",
                        console=con,
                        default=""
                    )
                except (EOFError, KeyboardInterrupt):
                    state.running = False
                    return ["Combat interrupted."]

            cmd, args = parse_command(raw)
            turn_messages = []

            # --- Free action: in-combat movement (doesn't consume turn) ---
            _COMBAT_DIRS = (
                "n", "s", "e", "w", "ne", "nw", "se", "sw",
                "north", "south", "east", "west",
                "northeast", "northwest", "southeast", "southwest",
            )
            if cmd in _COMBAT_DIRS:
                if state.remaining_movement < TILE_SIZE_FT:
                    con.print(f"  No movement remaining ({state.remaining_movement}ft).")
                else:
                    result = state.engine.move_player_grid(cmd)
                    if result.get("bump_pos"):
                        con.print(f"  [dim]Wall. Can't move that way during combat.[/dim]")
                    else:
                        state.remaining_movement -= TILE_SIZE_FT
                        con.print(f"  [cyan]Repositioned.[/cyan] ({state.remaining_movement}ft remaining)")
                continue  # Re-prompt for actual combat action

            if cmd in ("attack", "atk", "fight"):
                idx = 0
                if args:
                    try:
                        idx = int(args[0])
                    except ValueError:
                        idx = 0
                turn_messages = action_attack(state, idx, char)

            elif cmd == "guard":
                turn_messages = action_guard(state, char)

            elif cmd == "intercept":
                turn_messages = action_intercept(state, char)

            elif cmd == "bolster":
                if not args:
                    turn_messages = ["Usage: bolster <name>"]
                else:
                    turn_messages = action_bolster(state, " ".join(args), char)

            elif cmd == "triage":
                if not args:
                    turn_messages = ["Usage: triage <name>"]
                else:
                    turn_messages = action_triage(state, " ".join(args), char)

            elif cmd == "command":
                if not args:
                    turn_messages = ["Usage: command <name>"]
                else:
                    turn_messages = action_command(state, " ".join(args), char)

            elif cmd == "sanctify":
                turn_messages = action_sanctify(state, char)

            elif cmd == "summon":
                turn_messages = action_summon(state, char)

            # WO-V36.0: Manual AoE combat commands
            elif cmd == "flash":
                turn_messages = action_flash(state, char)
            elif cmd == "snare":
                turn_messages = action_snare(state, char)
            elif cmd == "rally":
                turn_messages = action_rally(state, char)
            elif cmd == "mending":
                turn_messages = action_mending(state, char)
            elif cmd == "renewal":
                turn_messages = action_renewal(state, char)
            elif cmd == "aegis":
                turn_messages = action_aegis(state, char)

            elif cmd == "look" or cmd == "l":
                turn_messages = action_look(state)

            elif cmd == "roll" or cmd == "r":
                turn_messages = _handle_roll(state, args)

            elif cmd in ("retreat", "flee", "run"):
                turn_messages = action_retreat(state)
                for msg in turn_messages:
                    con.print(f"  {msg}")
                messages.extend(turn_messages)
                # If retreat succeeded, combat is over — return immediately
                if not state.combat_mode:
                    return messages
                # Failed retreat — enemies already attacked in action_retreat,
                # skip normal enemy phase this round and return.
                return messages

            else:
                turn_messages = [f"Unknown combat action: '{cmd}'. Defaulting to Guard."]
                turn_messages.extend(action_guard(state, char))

            for msg in turn_messages:
                con.print(f"  {msg}")
            break  # Action taken, exit movement loop

        # Refresh enemies reference (may have been modified)
        enemies = state.room_enemies.get(room_id, [])

    # Enemy phase (skip if ambush round)
    if state.ambush_round:
        messages.append("\n[AMBUSH] Enemies are caught off guard - no counter-attack this round!")
        state.ambush_round = False
    elif enemies:
        messages.append("\n--- Enemy Phase ---")
        messages.extend(_enemy_phase(state))

    # Check if combat is over
    enemies = state.room_enemies.get(room_id, [])
    if not enemies:
        state.end_combat()
        state.cleared_rooms.add(room_id)
        messages.append("\nAll enemies defeated! Combat over.")
        if hasattr(state, 'butler') and state.butler:
            quip = state.butler.get_quip("combat_win")
            if quip:
                messages.append(quip)
    elif not state.engine.get_active_party():
        messages.append("\nThe party has been wiped out...")
        stats = RunStatistics(
            floors_cleared=len(state.cleared_rooms),
            enemies_slain=getattr(state, 'enemies_slain', 0),
            turns_taken=state.turn_number,
            chests_opened=getattr(state, 'chests_opened', 0),
            gold_collected=getattr(state, 'gold_collected', 0),
            highest_depth=1,
            cause_of_death="The Blight",
        )
        unlocks = MetaUnlocks()
        try:
            death_panel = render_death_screen_ui(stats, unlocks, 1, state.console)
            state.console.print(death_panel)
        except Exception:
            pass  # Graceful degradation if ui module has issues

    state.turn_number += 1
    return messages


def action_loot(state: GameState) -> List[str]:
    """Pick up loot items from the current room and add to inventory."""
    messages = []
    room_id = state.current_room_id
    loot = state.room_loot.get(room_id, [])

    if not loot:
        messages.append("There is nothing to pick up here.")
        return messages

    # Check if enemies are still present (can't loot during combat)
    enemies = state.room_enemies.get(room_id, [])
    if enemies:
        messages.append("You can't loot while enemies are present!")
        return messages

    for item_data in loot:
        # Convert loot dict to GearItem and add to inventory
        try:
            slot = GearSlot(item_data.get("slot", "R.Hand"))
        except ValueError:
            slot = GearSlot.R_HAND
        tier_val = item_data.get("tier", 1)
        try:
            tier = GearTier(min(4, tier_val))
        except ValueError:
            tier = GearTier.TIER_I

        # Resolve primary_stat for dice pool assignment
        ps_raw = item_data.get("primary_stat")
        primary_stat = StatType(ps_raw) if ps_raw else None

        gear_item = GearItem(
            name=item_data["name"],
            slot=slot,
            tier=tier,
            special_traits=list(item_data.get("special_traits", [])),
            description=item_data.get("description", f"Tier {tier_val} item found in the dungeon."),
            primary_stat=primary_stat,
        )
        state.active_leader.add_to_inventory(gear_item)
        messages.append(f"Picked up: {gear_item.name} ({slot.value}, Tier {tier_val})")
        # WO-V37.0: Log loot event
        state.log_event("loot", item_name=gear_item.name, tier=tier_val, room_id=room_id)
        # WO-V44.0: Quest loot trigger
        for qm in _check_quest_loot(state, room_id):
            messages.append(f"[QUEST] {qm}")

    state.room_loot[room_id] = []

    # Capacity warning after looting
    if state.active_leader:
        cap = state.active_leader.check_encumbrance()
        if cap.get("message"):
            messages.append(f"[Backpack] {cap['message']}")

    return messages


def action_look(state: GameState) -> List[str]:
    """Re-examine the current room. Pushes detail to sidebar."""
    room_data = state.engine.get_current_room()
    if not room_data:
        return ["You see nothing (no room data)."]

    lines = []
    lines.append(f"Room {room_data['id']} ({room_data['type'].upper()}, Tier {room_data['tier']})")
    lines.append(room_data["description"])
    lines.append("")

    enemies = state.room_enemies.get(state.current_room_id, [])
    if enemies:
        for i, e in enumerate(enemies):
            boss_tag = " [BOSS]" if e.get("is_boss") else ""
            lines.append(f"[{i}] {e['name']}{boss_tag}: {e['hp']} HP, DEF {e.get('defense', '?')}")
    else:
        lines.append("No enemies.")

    loot = state.room_loot.get(state.current_room_id, [])
    if loot:
        for item in loot:
            lines.append(f"* {item['name']} (Tier {item.get('tier', '?')})")

    connected = state.engine.get_connected_rooms()
    if connected:
        exit_strs = []
        for r in connected:
            tags = ""
            if r["is_locked"]:
                tags += " [LOCKED]"
            if r["visited"]:
                tags += " [VISITED]"
            elif r["id"] in state.scouted_rooms:
                tags += " [SCOUTED]"
            exit_strs.append(f"Room {r['id']} ({r['type']}, T{r['tier']}){tags}")
        lines.append(f"Exits: {', '.join(exit_strs)}")

    state.push_sidebar("\n".join(lines))
    return ["Surveying the room..."]


_THREAT_LABELS = {1: "Trivial", 2: "Moderate", 3: "Dangerous", 4: "Deadly"}


def _build_enemy_inspect(e: dict) -> List[str]:
    """Build detailed inspection lines for an enemy."""
    boss_tag = " [BOSS]" if e.get("is_boss") else ""
    threat = "BOSS" if e.get("is_boss") else _THREAT_LABELS.get(e.get("tier", 1), "Unknown")
    lines = [
        f"{e['name']}{boss_tag}",
        f"HP: {e['hp']}  DEF: {e.get('defense', '?')}  DR: {e.get('dr', 0)}",
        f"DMG: {e.get('damage', '?')}  Tier: {e.get('tier', '?')}",
        f"Type: {e.get('archetype', 'unknown').capitalize()}  Threat: {threat}",
    ]
    if e.get("special"):
        lines.append(f"Ability: {e['special']}")
    if e.get("description"):
        lines.append(e["description"])
    return lines


def _enrich_inspect_lore(state: GameState, entity_name: str):
    """Append cached lore to sidebar. Query Mimir on cache miss with delay.

    WO V20.5.4: Lore enrichment for inspect command.
    """
    try:
        from codex.core.cache import LoreCache, grit_scrub
    except ImportError:
        return
    cache = LoreCache()
    system = state.system_id or "burnwillow"

    cached = cache.get(system, entity_name.lower())
    if cached:
        state.push_sidebar(f"[Lore] {cached}")
        return

    # Cache miss: query Mimir in real-time (5-30s on Pi 5)
    try:
        from codex.integrations.mimir import query_mimir
        state.console.print("[dim]Consulting Mimir...[/dim]")
        result = query_mimir(
            f"Describe the '{entity_name}' in 2 sentences. "
            f"Focus on appearance and combat behavior.",
            namespace=system,
        )
        if result and not result.startswith("Error"):
            result = grit_scrub(result)
            cache.put(system, entity_name.lower(), result)
            state.push_sidebar(f"[Lore] {result}")
        else:
            state.push_sidebar("[Lore unavailable]")
    except ImportError:
        pass  # No Mimir available, skip lore enrichment


def action_inspect(state: GameState, target: str) -> List[str]:
    """Inspect an enemy or item by index/name. Pushes detail to sidebar."""
    target = target.strip().lower()

    # Try enemy by index
    enemies = state.room_enemies.get(state.current_room_id, [])
    try:
        idx = int(target)
        if 0 <= idx < len(enemies):
            state.push_sidebar("\n".join(_build_enemy_inspect(enemies[idx])))
            _enrich_inspect_lore(state, enemies[idx]["name"])
            return [f"Inspecting {enemies[idx]['name']}."]
    except ValueError:
        pass

    # Try enemy by name
    for e in enemies:
        if target in e.get("name", "").lower():
            state.push_sidebar("\n".join(_build_enemy_inspect(e)))
            _enrich_inspect_lore(state, e["name"])
            return [f"Inspecting {e['name']}."]

    # Try loot by name
    loot = state.room_loot.get(state.current_room_id, [])
    for item in loot:
        if target in item.get("name", "").lower():
            lines = [
                f"{item['name']}",
                f"Tier: {item.get('tier', '?')}  Slot: {item.get('slot', '?')}",
            ]
            if item.get("description"):
                lines.append(item["description"])
            state.push_sidebar("\n".join(lines))
            return [f"Inspecting {item['name']}."]

    return [f"Nothing matching '{target}' found."]


def action_inventory(state: GameState, use_paper_doll: bool = False) -> List[str]:
    """Show character stats, equipped gear, and inventory.

    If use_paper_doll is True, prints the full paper doll directly.
    Otherwise routes text summary to sidebar.
    """
    char = state.active_leader or state.character
    if not char:
        return ["No active character."]

    if use_paper_doll:
        # Full graphical paper doll — printed directly to console
        state.console.print(render_paper_doll(char))
        if char.inventory:
            state.console.print(render_dual_backpack(char))
        return ["Character sheet displayed."]

    # Text fallback for sidebar
    lines = []

    lines.append(f"{char.name}")
    lines.append(
        f"HP:{char.current_hp}/{char.max_hp} DEF:{char.get_defense()} "
        f"DR:{char.gear.get_total_dr()} Keys:{char.keys}"
    )
    lines.append(
        f"M{calculate_stat_mod(char.might):+d} [Might]  "
        f"W{calculate_stat_mod(char.wits):+d} [Wits]  "
        f"G{calculate_stat_mod(char.grit):+d} [Grit]  "
        f"A{calculate_stat_mod(char.aether):+d} [Aether]"
    )
    lines.append("")
    lines.append("[Gear]")
    for slot in GearSlot:
        item = char.gear.slots.get(slot)
        if item:
            # Build stat annotation: dice bonus + which stat pool
            pool_stat = item.get_pool_stat()
            stat_abbr = pool_stat.value[0] if pool_stat else None
            dice = item.tier.value if hasattr(item.tier, 'value') else item.tier
            parts = []
            if dice > 0 and stat_abbr:
                parts.append(f"+{dice}d6 {stat_abbr}")
            if item.damage_reduction > 0:
                parts.append(f"DR {item.damage_reduction}")
            stat_note = f" ({', '.join(parts)})" if parts else ""
            traits = f" [{','.join(item.special_traits)}]" if item.special_traits else ""
            lines.append(f" {slot.value}: {item.name}{stat_note}{traits}")
        else:
            lines.append(f" {slot.value}: ---")

    if char.inventory:
        lines.append("")
        lines.append(f"[Backpack] ({len(char.inventory)})")
        sorted_keys = sorted(char.inventory.keys())
        left = [k for k in sorted_keys if k < 5]
        right = [k for k in sorted_keys if k >= 5]
        max_rows = max(len(left), len(right))
        for row in range(max_rows):
            if row < len(left):
                l_name = char.inventory[left[row]].name
                l_str = f"[{left[row]}] {l_name[:15]}\u2026" if len(l_name) > 16 else f"[{left[row]}] {l_name}"
            else:
                l_str = ""
            if row < len(right):
                r_name = char.inventory[right[row]].name
                r_str = f"[{right[row]}] {r_name[:15]}\u2026" if len(r_name) > 16 else f"[{right[row]}] {r_name}"
            else:
                r_str = ""
            lines.append(f" {l_str:<22}| {r_str}")

    state.push_sidebar("\n".join(lines))
    return ["Checking inventory..."]


def action_inspect_item(state: GameState, inv_index: int) -> List[str]:
    """Inspect a specific item in inventory by index — full detail to sidebar."""
    char = state.active_leader or state.character
    if not char:
        return ["No active character."]

    item = char.inventory.get(inv_index)
    if item is None:
        # Also check equipped gear by slot name isn't practical via index;
        # just validate inventory
        valid = ", ".join(str(k) for k in sorted(char.inventory.keys()))
        return [f"No item at index {inv_index}. Valid: [{valid}]"]

    # Build detailed text for sidebar
    _SYNERGY_HINTS = {
        "[Lockpick]": "Enables lock-picking",
        "[Intercept]": "Shield allies in combat",
        "[Summon]": "Call minion in combat",
        "[Guard]": "Guard adjacent allies",
        "[Heal]": "Restore HP",
        "[Reflect]": "Reflect ranged attacks",
    }
    lines = []
    lines.append(f"{item.name}")
    lines.append(f"Slot: {item.slot.value}  |  Tier: {item.tier.value}")
    lines.append(f"Dice: {item.tier.value}d6")
    if item.damage_reduction:
        lines.append(f"DR: {item.damage_reduction}")
    if item.stat_bonuses:
        bonus_strs = [f"{stat.value} {val:+d}" for stat, val in item.stat_bonuses.items()]
        lines.append(f"Bonuses: {', '.join(bonus_strs)}")
    if item.special_traits:
        lines.append(f"Traits: {', '.join(item.special_traits)}")
        for trait in item.special_traits:
            hint = _SYNERGY_HINTS.get(trait)
            if hint:
                lines.append(f"  -> {hint}")
    if item.two_handed:
        lines.append("Two-Handed")
    if hasattr(item, 'weight') and item.weight:
        lines.append(f"Weight: {item.weight}")
    if item.description:
        lines.append(f"\n{item.description}")

    state.push_sidebar("\n".join(lines))
    return [f"Inspecting {item.name}."]


def action_equip(state: GameState, inv_index: int, target_slot: Optional[GearSlot] = None) -> List[str]:
    """Equip an item from inventory by stable index.

    Args:
        state: Current game state.
        inv_index: Inventory slot index.
        target_slot: Optional override slot (from SLOT_ALIASES).
    """
    messages = []
    char = state.active_leader

    item = char.remove_from_inventory(inv_index)
    if item is None:
        valid = ", ".join(str(k) for k in sorted(char.inventory.keys()))
        messages.append(f"No item at index {inv_index}. Valid: [{valid}]")
        return messages

    # Apply slot override for hand-compatible items
    if target_slot and target_slot in (GearSlot.R_HAND, GearSlot.L_HAND):
        if item.slot in (GearSlot.R_HAND, GearSlot.L_HAND) and not item.two_handed:
            item.slot = target_slot

    displaced = char.gear.equip(item)
    messages.append(f"Equipped: {item.name} -> {item.slot.value}")

    for old_item in displaced:
        char.add_to_inventory(old_item)
        messages.append(f"Unequipped: {old_item.name} -> Backpack")

    return messages


def action_save(state: GameState) -> List[str]:
    """Save the current game to a JSON file in saves/."""
    if not state.engine:
        return ["No active game to save."]

    save_data = state.engine.save_game()
    # Augment with play_burnwillow state
    save_data["turn_number"] = state.turn_number
    save_data["cleared_rooms"] = list(state.cleared_rooms)
    save_data["searched_rooms"] = list(state.searched_rooms)
    save_data["scouted_rooms"] = list(state.scouted_rooms)
    # Seed-lock: always write from authoritative source (WO V20.3)
    graph_seed = state.engine.dungeon_graph.seed if state.engine.dungeon_graph else state.dungeon_seed
    save_data["dungeon_seed"] = graph_seed
    save_data["floor_seed"] = graph_seed  # Forward-compat alias
    save_data["room_enemies"] = copy.deepcopy({str(k): v for k, v in state.room_enemies.items()})
    save_data["room_loot"] = copy.deepcopy({str(k): v for k, v in state.room_loot.items()})
    save_data["room_furniture"] = copy.deepcopy({str(k): v for k, v in state.room_furniture.items()})
    save_data["doom_clock_state"] = {
        "current_turn": state.turn_number,
        "doom_level": state.engine.doom_clock.current if state.engine else 0,
    }
    save_data["rot_hunter"] = copy.deepcopy(state.rot_hunter)
    save_data["first_strike_used"] = state.first_strike_used
    save_data["dungeon_path"] = state.dungeon_path
    # WO-V32.0: Doom rate scaling persistence
    save_data["doom_rate_mult"] = state.doom_rate_mult
    save_data["_doom_remainder"] = state._doom_remainder
    if state.narrative:
        save_data["narrative"] = state.narrative.to_dict()
    # WO-V56.0: Persist memory engine shards
    mem = getattr(state.engine, 'memory_engine', None)
    if mem and hasattr(mem, 'shards'):
        save_data["memory_shards"] = [s.to_dict() for s in mem.shards]

    # Persist NPC memory banks (WO-V12.1)
    if hasattr(state, '_npc_memory') and state._npc_memory:
        state._npc_memory.save()

    # Persist autopilot agent metadata (WO-V31.0)
    if state.autopilot_agents:
        save_data["autopilot_agents"] = {
            name: {
                "archetype": agent.personality.archetype,
                "biography": agent.biography,
                "quirk": agent.personality.quirk,
            }
            for name, agent in state.autopilot_agents.items()
        }
    save_data["autopilot_mode"] = state.autopilot_mode
    save_data["companion_mode"] = state.companion_mode
    # WO-V37.0: Persist session chronicle
    save_data["session_log"] = state.session_log
    # WO-V62.0: Persist new session modules
    if state.momentum_ledger:
        save_data["momentum_ledger"] = state.momentum_ledger.to_dict()
    if state.session_frame:
        save_data["session_frame"] = state.session_frame.to_dict()
    if state.expedition_timer:
        save_data["expedition_timer"] = state.expedition_timer.to_dict()
    if state._willow_wood_save:
        save_data["willow_wood_save"] = state._willow_wood_save
    # Phase 3/6: Persist world map & module manifest navigation state
    save_data["current_location_id"] = state.current_location_id
    save_data["visited_locations"] = list(state.visited_locations) if state.visited_locations else []
    save_data["current_chapter_idx"] = state.current_chapter_idx
    save_data["current_zone_idx"] = state.current_zone_idx
    # WorldMap and ModuleManifest objects are not JSON-serialized inline;
    # they are reloaded from their source files on load.

    filename = SAVES_DIR / "burnwillow_save.json"
    safe_save_json(filename, save_data)

    return [f"Game saved to {filename.name}."]


def action_load(state: GameState) -> List[str]:
    """Load a saved game from saves/burnwillow_save.json."""
    save_file = SAVES_DIR / "burnwillow_save.json"
    if not save_file.exists():
        return ["No save file found."]

    try:
        with open(save_file, "r") as f:
            save_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return [f"Failed to load save: {e}"]

    # Rebuild engine from save
    state.engine = BurnwillowEngine()
    state.engine.load_game(save_data)

    # Restore GameState fields
    state.turn_number = save_data.get("turn_number", 0)
    state.cleared_rooms = set(save_data.get("cleared_rooms", []))
    state.searched_rooms = set(save_data.get("searched_rooms", []))
    state.scouted_rooms = set(save_data.get("scouted_rooms", []))
    state.dungeon_seed = save_data.get("dungeon_seed") or save_data.get("floor_seed")

    # Seed-lock sanity check (WO V20.3)
    if state.engine.dungeon_graph and not state.engine.dungeon_graph.rooms:
        return ["Save load failed: dungeon graph has no rooms. Save may be corrupted."]

    # Restore room content from save if present, else rebuild from populated_rooms
    saved_enemies = save_data.get("room_enemies")
    saved_loot = save_data.get("room_loot")

    if saved_enemies is not None:
        state.room_enemies = {int(k): copy.deepcopy(v) for k, v in saved_enemies.items()}
    else:
        state.room_enemies = {}
        for room_id, pop_room in state.engine.populated_rooms.items():
            content = pop_room.content
            state.room_enemies[room_id] = list(content.get("enemies", []))
        # WO-V32.0: Scale rebuilt enemies by party size
        _scaling = get_party_scaling(len(state.engine.party))
        for enemies in state.room_enemies.values():
            for e in enemies:
                e["hp"] = max(1, int(e.get("hp", 1) * _scaling["hp_mult"]))
                if "max_hp" in e:
                    e["max_hp"] = max(1, int(e["max_hp"] * _scaling["hp_mult"]))
                e["_dmg_mult"] = _scaling["dmg_mult"]

    if saved_loot is not None:
        state.room_loot = {int(k): copy.deepcopy(v) for k, v in saved_loot.items()}
    else:
        state.room_loot = {}
        for room_id, pop_room in state.engine.populated_rooms.items():
            content = pop_room.content
            state.room_loot[room_id] = list(content.get("loot", []))

    # Restore room furniture (backward-compatible)
    state.room_furniture = {int(k): copy.deepcopy(v) for k, v in save_data.get("room_furniture", {}).items()}

    # Restore Rot Hunter state (backward-compatible)
    state.rot_hunter = copy.deepcopy(save_data.get("rot_hunter"))
    # First-Strike: per-combat, default False (ready for next fight)
    state.first_strike_used = save_data.get("first_strike_used", False)

    # WO-V32.0: Restore doom rate scaling
    state.doom_rate_mult = save_data.get("doom_rate_mult", DOOM_RATE_MULT.get(len(state.engine.party), 1.0))
    state._doom_remainder = save_data.get("_doom_remainder", 0.0)

    # Restore narrative engine state (backward-compatible)
    state.dungeon_path = save_data.get("dungeon_path", "descend")
    if "narrative" in save_data:
        state.narrative = NarrativeEngine.from_dict(save_data["narrative"])
    else:
        state.narrative = NarrativeEngine(system_id=state.system_id or "burnwillow")
    # WO-V56.0: Wire _engine_ref on load too
    state.narrative._engine_ref = state.engine
    # WO-V56.0: Restore memory engine
    try:
        from codex.core.memory import CodexMemoryEngine, MemoryShard
        state.engine.memory_engine = CodexMemoryEngine()
        if "memory_shards" in save_data:
            for sd in save_data["memory_shards"]:
                state.engine.memory_engine.shards.append(MemoryShard.from_dict(sd))
    except ImportError:
        state.engine.memory_engine = None

    # Reload settlement graph from blueprint (deterministic)
    _load_emberhome_settlement(state)

    # Restore NPC memory system (WO-V12.1)
    _init_npc_memory(state)

    # Restore autopilot agent metadata (WO-V31.0)
    state.autopilot_mode = save_data.get("autopilot_mode", False)
    state.companion_mode = save_data.get("companion_mode", False)
    saved_agents = save_data.get("autopilot_agents", {})
    if saved_agents:
        from codex.games.burnwillow.autopilot import (
            AutopilotAgent, CompanionPersonality, PERSONALITY_POOL,
        )
        for name, meta in saved_agents.items():
            archetype = meta.get("archetype", "vanguard")
            # Find matching personality from pool
            personality = None
            for p in PERSONALITY_POOL:
                if p.archetype == archetype:
                    personality = p
                    break
            if personality is None:
                personality = CompanionPersonality(
                    archetype=archetype,
                    description=f"A {archetype}",
                    quirk=meta.get("quirk", "..."),
                    aggression=0.5, curiosity=0.5, caution=0.5,
                )
            state.autopilot_agents[name] = AutopilotAgent(
                personality=personality,
                biography=meta.get("biography", ""),
            )

    # WO-V37.0: Restore session chronicle
    state.session_log = save_data.get("session_log", [])
    # WO-V62.0: Restore session modules
    if "momentum_ledger" in save_data:
        from codex.core.services.momentum import MomentumLedger
        state.momentum_ledger = MomentumLedger.from_dict(save_data["momentum_ledger"])
    if "session_frame" in save_data:
        from codex.core.session_frame import SessionFrame
        state.session_frame = SessionFrame.from_dict(save_data["session_frame"])
    if "expedition_timer" in save_data:
        from codex.core.session_frame import ExpeditionTimer
        state.expedition_timer = ExpeditionTimer.from_dict(save_data["expedition_timer"])
    state._willow_wood_save = save_data.get("willow_wood_save")
    # Phase 3/6: Restore world map & module manifest navigation state
    state.current_location_id = save_data.get("current_location_id")
    _visited_raw = save_data.get("visited_locations", [])
    state.visited_locations = set(_visited_raw) if _visited_raw else None
    state.current_chapter_idx = save_data.get("current_chapter_idx", 0)
    state.current_zone_idx = save_data.get("current_zone_idx", 0)
    # WorldMap / ModuleManifest are not saved inline; callers that set them
    # must re-attach them after loading (e.g. play_burnwillow main loop).

    # Clear zombie combat flags from save
    state.clear_volatile_state()

    # Rebuild spatial rooms
    _rebuild_spatial_rooms(state)

    messages = [
        f"Game loaded! Turn {state.turn_number}, Doom {state.doom}.",
        f"Party: {', '.join(c.name for c in state.engine.party)}",
    ]
    return messages


def action_party(state: GameState) -> List[str]:
    """Show detailed party status."""
    messages = ["=== PARTY STATUS ==="]
    for i, char in enumerate(state.engine.party):
        leader_tag = " (Leader)" if i == 0 else ""
        minion_tag = " [SUMMON]" if isinstance(char, Minion) else ""
        alive_tag = "" if char.is_alive() else " [DEAD]"
        messages.append(f"\n  {char.name}{leader_tag}{minion_tag}{alive_tag}")
        messages.append(f"    HP: {char.current_hp}/{char.max_hp}  DEF: {char.get_defense()}  DR: {char.gear.get_total_dr()}")
        if not isinstance(char, Minion):
            messages.append(
                f"    MIG {char.might}({calculate_stat_mod(char.might):+d})  "
                f"WIT {char.wits}({calculate_stat_mod(char.wits):+d})  "
                f"GRT {char.grit}({calculate_stat_mod(char.grit):+d})  "
                f"AET {char.aether}({calculate_stat_mod(char.aether):+d})"
            )
            gear_names = [f"{item.name}" for item in char.gear.slots.values() if item]
            if gear_names:
                messages.append(f"    Gear: {', '.join(gear_names)}")
        else:
            messages.append(f"    Rounds remaining: {char.summon_duration}")
    return messages


def _handle_roll(state: GameState, args: List[str]) -> List[str]:
    """Ad-hoc dice roll. Supports 'roll 2d6+3' or bare 'roll' (rolls 1d6)."""
    if not args:
        formula = "1d6"
    else:
        formula = args[0]
    try:
        if '+' in formula:
            base, mod_str = formula.split('+')
            mod = int(mod_str)
        elif '-' in formula:
            base, mod_str = formula.split('-')
            mod = -int(mod_str)
        else:
            base = formula
            mod = 0
        count_str, die_str = base.lower().split('d')
        count = int(count_str) if count_str else 1
        die = int(die_str)
        rolls = [random.randint(1, die) for _ in range(count)]
        total = sum(rolls) + mod
        mod_fmt = f"{mod:+d}" if mod else ""
        return [f"Rolled {count}d{die}{mod_fmt}: [{', '.join(map(str, rolls))}] = {total}"]
    except Exception:
        return [f"Bad dice format: '{formula}'. Use XdY or XdY+Z (e.g. 2d6+3)"]


def action_give(state: GameState, inv_index: int, target_party_index: int) -> List[str]:
    """Transfer an item from the active leader's inventory to another party member.

    Costs 1 Doom Clock tick (hand-off takes dungeon time).
    """
    messages = []
    giver = state.active_leader
    if not giver:
        return ["No active character."]

    party = state.engine.get_active_party()
    if target_party_index < 0 or target_party_index >= len(party):
        return [f"Invalid target. Party has {len(party)} members (0-{len(party)-1})."]

    receiver = party[target_party_index]
    if receiver is giver:
        return ["You can't give items to yourself. Use 'equip' instead."]

    item = giver.remove_from_inventory(inv_index)
    if item is None:
        valid = ", ".join(str(k) for k in sorted(giver.inventory.keys()))
        return [f"No item at index {inv_index}. Valid: [{valid}]"]

    receiver.add_to_inventory(item)
    doom_events = state.engine.advance_doom(1)
    state.turn_number += 1

    messages.append(f"{giver.name} gives {item.name} to {receiver.name}.")
    for event in doom_events:
        messages.append(event)

    rot_msgs = _process_doom_advancement(state, doom_events)
    messages.extend(rot_msgs)

    return messages


def action_library(state: GameState) -> List[str]:
    """Open Mimir's Vault restricted to the current system."""
    try:
        from codex.core.services.librarian import LibrarianTUI
    except ImportError:
        return ["[Mimir's Vault unavailable -- librarian module not found.]"]

    mimir_fn = None
    try:
        from codex.integrations.mimir import query_mimir
        mimir_fn = query_mimir
    except ImportError:
        pass

    # WO V20.5.4: Persistent lore cache (lazy, reads on first access)
    cache = None
    try:
        from codex.core.cache import LoreCache
        cache = LoreCache()
    except ImportError:
        pass

    lib = LibrarianTUI(mimir_fn=mimir_fn, system_id=state.system_id, cache=cache)
    lib.run_loop(state.console)
    return ["Returned from Mimir's Vault."]


# =============================================================================
# INTERACT COMMAND
# =============================================================================

_FURNITURE_FLAVOR = {
    "altar": [
        "Cold stone, etched with symbols you cannot read. It hums faintly.",
        "The altar radiates a dull warmth. Offerings of bone litter its surface.",
    ],
    "barrel": [
        "You pry the lid. Inside: stale water and a dead rat.",
        "The barrel sloshes. Something fermented and best left undisturbed.",
    ],
    "bookshelf": [
        "Most volumes crumble at your touch. One spine reads: 'On the Nature of Blight.'",
        "Dust and cobwebs. A single readable page describes warding rituals.",
    ],
    "chest": [
        "The chest is empty, its lock already forced by someone before you.",
        "Rusted hinges groan. Inside: moth-eaten cloth and a broken compass.",
    ],
    "brazier": [
        "Cold coals. Whatever burned here did so long ago.",
        "You stir the ashes. A faint ember glows and dies.",
    ],
    "statue": [
        "A weathered figure of a knight, sword raised. The face has been chiseled away.",
        "Stone eyes watch nothing. The statue's hand is outstretched, palm empty.",
    ],
    "table": [
        "Scratched wood. Someone carved tally marks into the surface. Many, many tallies.",
        "A rotting table. Maps and documents have long since moldered to pulp.",
    ],
    "well": [
        "You drop a pebble. The splash takes far too long to arrive.",
        "Dark water, still as glass. Your reflection stares back, then blinks.",
    ],
}


def _get_furniture_flavor(name: str, tier: int = 1) -> str:
    """Return tier-appropriate examination text for a furniture object."""
    key = name.lower().strip()
    for furniture_key, flavors in _FURNITURE_FLAVOR.items():
        if furniture_key in key:
            idx = min(tier - 1, len(flavors) - 1)
            return flavors[max(0, idx)]
    # Generic fallback
    generic = [
        f"You examine the {name}. It is unremarkable, but sturdy.",
        f"The {name} shows signs of age. Nothing of immediate use.",
        f"You poke at the {name}. It does not respond. Probably for the best.",
    ]
    return random.choice(generic)


def action_recruit(state: GameState) -> List[str]:
    """Launch Character Wizard mid-game to recruit a new party member."""
    if len(state.engine.party) >= 6:
        return ["Party is full (6 members). Someone must fall before another can join."]

    if state.combat_mode:
        return ["Cannot recruit during combat."]

    try:
        from codex.forge.char_wizard import (
            CharacterBuilderEngine, SystemBuilder, render_character,
        )
        from codex.forge.codex_transmuter import CharacterAdapter, MissingEngineError
    except ImportError:
        return ["Character Forge not available."]

    con = state.console
    con.print()
    con.print(Panel(
        "[bold]The Recruit Forge[/]\n\n"
        "A wanderer emerges from the shadows, seeking to join your expedition.\n"
        "Guide their creation through the Forge.",
        border_style="yellow",
    ))

    engine = CharacterBuilderEngine()
    all_systems = engine.list_systems()
    if not all_systems:
        return ["No character systems found in vault."]

    # Filter out sub-settings (setting_id set) — they appear via secondary prompt
    systems = [s for s in all_systems if not s.setting_id]
    sub_settings = [s for s in all_systems if s.parent_engine and s.setting_id]

    # System selection
    con.print("\n[bold yellow]Available Systems:[/]")
    for i, schema in enumerate(systems, 1):
        con.print(f"  [{i}] {schema.display_name} ({schema.genre})")
    con.print(f"  [0] Cancel")

    try:
        choice = Prompt.ask("Select system", console=con)
        idx = int(choice)
        if idx == 0:
            return ["Recruitment cancelled."]
        if idx < 1 or idx > len(systems):
            return ["Invalid selection. Recruitment cancelled."]
    except (ValueError, EOFError):
        return ["Recruitment cancelled."]

    selected = systems[idx - 1]

    # Sub-setting prompt if applicable
    child_settings = [s for s in sub_settings if s.parent_engine == selected.system_id]
    if child_settings:
        con.print(f"\n[bold yellow]{selected.display_name} — Choose Setting:[/]")
        con.print(f"  [1] All {selected.display_name} content")
        for j, cs in enumerate(child_settings, 2):
            con.print(f"  [{j}] {cs.display_name} ({cs.genre})")
        try:
            sub_choice = Prompt.ask("Select setting", console=con)
            sub_idx = int(sub_choice)
            if 2 <= sub_idx <= len(child_settings) + 1:
                selected = child_settings[sub_idx - 2]
        except (ValueError, EOFError):
            pass

    # Build character
    builder = SystemBuilder(selected, con)
    sheet = builder.run()

    if not sheet.name:
        return ["No character created. Recruitment cancelled."]

    # Show the finished character
    con.print()
    con.print(render_character(sheet, selected))

    # Convert to Burnwillow Character
    try:
        wizard_data = {
            "system_id": sheet.system_id,
            "name": sheet.name,
            "choices": sheet.choices,
            "stats": sheet.stats,
        }
        new_char = CharacterAdapter.convert(wizard_data)
    except MissingEngineError as e:
        return [f"Cannot convert: {e}"]

    # Add to party
    state.engine.add_to_party(new_char)
    return [
        f"{new_char.name} joins the expedition!",
        f"HP: {new_char.current_hp}/{new_char.max_hp} | "
        f"Might: {new_char.might} Wits: {new_char.wits} "
        f"Grit: {new_char.grit} Aether: {new_char.aether}",
        f"Party size: {len(state.engine.party)}/6",
    ]


def action_interact(state, args: List[str]) -> List[str]:
    """Interact with a furniture object in the current room."""
    messages = []
    furniture = state.room_furniture.get(state.current_room_id, [])
    if not furniture:
        return ["Nothing to interact with here."]

    if not args:
        messages.append("Objects in this room:")
        for i, obj in enumerate(furniture, 1):
            messages.append(f"  {i}. {obj.get('name', '???')}")
        messages.append("Use 'interact <number>' to examine.")
        return messages

    try:
        idx = int(args[0]) - 1
        obj = furniture[idx]
    except (ValueError, IndexError):
        return ["Invalid object number."]

    name = obj.get("name", "???")
    messages.append(f"You examine the {name}...")
    messages.append(_get_furniture_flavor(name, obj.get("tier", 1)))
    return messages


# =============================================================================
# BUMP PHYSICS (WO V20.3)
# =============================================================================

LOCKPICK_DC = 14


def _resolve_bump(state: GameState, pos: Tuple[int, int]) -> Optional[List[str]]:
    """Resolve a wall-bump at the given grid position.

    Checks for enemies, then furniture at the bump target.
    Returns messages if something was hit, or None for a plain wall bump.
    """
    room_id = state.current_room_id
    if room_id is None:
        return None

    bx, by = pos

    # 1. Check for enemy at bump position
    enemies = state.room_enemies.get(room_id, [])
    for i, e in enumerate(enemies):
        ex, ey = e.get("x"), e.get("y")
        if ex == bx and ey == by:
            # Bump into enemy -> start combat + auto-attack
            if not state.combat_mode:
                state.start_combat()
            msgs = [f"You slam into {e['name']}! Combat begins!"]
            atk_msgs = _perform_attack(state, state.active_character, i)
            msgs.extend(atk_msgs)
            return msgs

    # 2. Check for furniture at bump position
    furniture = state.room_furniture.get(room_id, [])
    for obj in furniture:
        fx, fy = obj.get("x"), obj.get("y")
        if fx == bx and fy == by:
            ctype = obj.get("container_type", "furniture")
            name = obj.get("name", "object")

            # Locked chest with lockpick tag
            if ctype == "chest" and obj.get("locked", False):
                # Check for Lockpick gear tag
                char = state.active_character
                has_lockpick = False
                if char and char.gear_grid:
                    for item in char.gear_grid.slots.values():
                        if item and "Lockpick" in (item.tags or []):
                            has_lockpick = True
                            break
                if has_lockpick:
                    result = roll_dice_pool(
                        char.get_stat_value(StatType.WITS),
                        char.gear_grid.get_total_dice_bonus(StatType.WITS),
                        DC(LOCKPICK_DC),
                    )
                    if result.success:
                        obj["locked"] = False
                        return [f"You pick the lock on {name}! (Wits {result.total} vs DC {LOCKPICK_DC})"]
                    else:
                        return [f"The lock resists your attempt. (Wits {result.total} vs DC {LOCKPICK_DC})"]
                else:
                    return [f"The {name} is locked. You need a Lockpick."]

            # Unlocked furniture -> flavor text in sidebar
            flavor = _get_furniture_flavor(name, obj.get("tier", 1))
            state.push_sidebar(f"[{name}] {flavor}")
            return [f"You examine the {name}."]

    # No entity at bump position -> plain wall
    return None


_HELP_PAGES = [
    # Page 1: Movement & Exploration
    [
        "=== BURNWILLOW COMMANDS (Page 1/3) ===",
        "",
        "--- Movement ---",
        "  n / s / e / w         Walk one tile on the grid",
        "  move <id|dir>         Move to a room by ID or direction (+1 Doom)",
        "                        e.g. move 5, move n, move e1",
        "",
        "--- Exploration ---",
        "  look / l              Survey room (detail -> sidebar)",
        "  inspect <#>           Inspect enemy by index or name",
        "  inspect item <#>      Inspect inventory item (full stats)",
        "  scout <id>            Peek at a room (Wits vs DC 12, +1 Doom)",
        "  search                Search for hidden loot (Wits vs DC 12, +1 Doom)",
        "  loot                  Pick up all loot in the room",
        "  interact              Interact with furniture/objects in room",
        "  interact <#>          Examine a specific object by number",
        "  leave / return        Leave dungeon (from entrance or Return Gate)",
        "",
        "Page 1/3 -- type 'help 2' for next page",
    ],
    # Page 2: Character & Party
    [
        "=== BURNWILLOW COMMANDS (Page 2/3) ===",
        "",
        "--- Character ---",
        "  inv / gear / backpack Show stats and gear (-> sidebar)",
        "  doll / sheet          Full paper doll character sheet",
        "  equip <#> [slot]      Equip item from backpack by index",
        "                        Slots: left hand, right hand, head, chest,",
        "                        arms, legs, shoulders, neck",
        "  bind / heal / rest    Bind Wounds: heal ~50% max HP (+1 Doom)",
        "",
        "--- Party ---",
        "  party                 Show full party status",
        "  recruit               Recruit a new party member via the Forge",
        "  switch <#>            Switch active leader (e.g. switch 1)",
        "  give <#> to <#>       Give item to party member (+1 Doom)",
        "                        e.g. give 0 to 1",
        "",
        "--- Utility ---",
        "  roll <XdY>            Roll dice freely (e.g. roll 2d6+3)",
        "  library               Browse Mimir's Vault (system lore)",
        "  save / load           Save or load the current game",
        "  recap                 Session recap (kills, loot, rooms)",
        "  map                   Show full dungeon map (debug)",
        "  help                  Show this help text",
        "  quit                  End the game",
        "",
        "Page 2/3 -- type 'help 3' for next page",
    ],
    # Page 3: Combat
    [
        "=== BURNWILLOW COMMANDS (Page 3/3) ===",
        "",
        "--- Combat (when enemies are present) ---",
        "  attack <#>            Attack enemy by index (Might vs Defense)",
        "  guard                 Defensive stance (+2 DEF until next turn)",
        "  intercept             Redirect next ally hit to you (+2 DR, needs shield)",
        "  command <name>        Order ally to make a bonus attack (Wits vs DC 12)",
        "  bolster <name>        Grant ally +2d6 on next roll (Aether vs DC 12)",
        "  triage <name>         Heal ally 1d6+Wits mod (Wits vs DC 12)",
        "  sanctify              Enemies take 1d6 damage this round (Aether vs DC 14)",
        "  summon                Conjure an Aether spirit (Aether vs DC 12, needs [Summon])",
        "",
        "  Doom advances on Move, Scout, Search, Bind, and Give.",
        "  Party of 1? Pick 'The Occultist' loadout to summon allies.",
        "",
        "Page 3/3 -- type 'help 1' to return to page 1",
    ],
]


# =============================================================================
# EXTRACTION — RETURN GATE (WO-V4.4)
# =============================================================================

VILLAGE_PROGRESS_FILE = SAVES_DIR / "village_progression.json"


def _extract_memory_seeds(state: GameState) -> List[dict]:
    """Scan all party inventories for Memory Seed items, remove and return them."""
    seeds: List[dict] = []
    if not state.engine or not state.engine.party:
        return seeds
    for char in state.engine.party:
        to_remove: List[int] = []
        for idx, item in char.inventory.items():
            traits = item.special_traits if hasattr(item, "special_traits") else []
            if "[Unlock blueprint]" in traits or "Unlock blueprint" in traits:
                seeds.append({"name": item.name, "source": char.name})
                to_remove.append(idx)
        for idx in to_remove:
            char.remove_from_inventory(idx)
    return seeds


def _save_village_progress(state: GameState, seeds: List[dict]) -> None:
    """Persist extracted Memory Seeds to the village progression file."""
    from datetime import datetime

    universe_id = "burnwillow_default"

    # Load existing
    data: dict = {"universes": {}}
    if VILLAGE_PROGRESS_FILE.exists():
        try:
            with open(VILLAGE_PROGRESS_FILE, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    universes = data.setdefault("universes", {})
    uni = universes.setdefault(universe_id, {
        "memory_seeds": [],
        "total_extractions": 0,
        "last_extraction": None,
    })
    for seed in seeds:
        uni["memory_seeds"].append(seed["name"])
    uni["total_extractions"] = uni.get("total_extractions", 0) + 1
    uni["last_extraction"] = datetime.now().isoformat()

    safe_save_json(VILLAGE_PROGRESS_FILE, data)


def _reinitialize_room_state(state: GameState) -> None:
    """Rebuild room content tracking after dungeon regeneration."""
    state.room_enemies.clear()
    state.room_loot.clear()
    state.room_furniture.clear()
    state.cleared_rooms.clear()
    state.searched_rooms.clear()
    state.scouted_rooms.clear()
    state.rot_hunter = None

    for room_id, pop_room in state.engine.populated_rooms.items():
        content = pop_room.content
        state.room_enemies[room_id] = list(content.get("enemies", []))
        state.room_loot[room_id] = list(content.get("loot", []))
        state.room_furniture[room_id] = list(content.get("furniture", []))

    _rebuild_spatial_rooms(state)


def action_return(state: GameState) -> List[str]:
    """Extract through a Return Gate or dungeon entrance back to Emberhome."""
    if not state.engine or state.current_room_id is None:
        return ["No active dungeon."]

    room_node = state.engine.dungeon_graph.get_room(state.current_room_id)
    if not room_node or room_node.room_type not in (RoomType.RETURN_GATE, RoomType.START):
        return ["You can only leave from the dungeon entrance or a Return Gate."]

    via_entrance = room_node.room_type == RoomType.START

    # Collect Memory Seeds
    seeds = _extract_memory_seeds(state)
    if seeds:
        _save_village_progress(state, seeds)

    # Reset doom
    state.engine.doom_clock.current = 0

    if via_entrance:
        msgs = [f"You retrace your steps to the surface. {len(seeds)} Memory Seed(s) secured."]
    else:
        msgs = [f"You step through the extraction circle. {len(seeds)} Memory Seed(s) secured."]
    msgs.append("The warmth of Emberhome welcomes you back.")

    # Set narrative phase to AFTERMATH for haven event display
    if state.narrative:
        state.narrative.phase = CampaignPhase.AFTERMATH

    # Return to Emberhome hub
    _run_emberhome_hub(state)

    if not state.running:
        return msgs

    # Regenerate dungeon based on chosen path
    new_seed = random.randint(0, 999999)
    state.dungeon_seed = new_seed

    if state.dungeon_path == "ascend":
        if not state.engine.map_engine:
            state.engine.map_engine = CodexMapEngine(seed=state.dungeon_seed or 0)
        state.engine.dungeon_graph = state.engine.map_engine.generate_vertical(
            floors=6, rooms_per_floor=2,
            floor_width=30, floor_height=8,
            system_id=state.system_id or "burnwillow",
        )
        state.engine.dungeon_graph.seed = new_seed
        state.engine.seed = new_seed
        state.engine.current_room_id = state.engine.dungeon_graph.start_room_id
        if state.engine.dungeon_graph.start_room_id in state.engine.dungeon_graph.rooms:
            start_room = state.engine.dungeon_graph.rooms[state.engine.dungeon_graph.start_room_id]
            state.engine.player_pos = (
                start_room.x + start_room.width // 2,
                start_room.y + start_room.height // 2,
            )
        state.engine.populate_dungeon_canopy()
    else:
        state.engine.generate_dungeon(depth=DEFAULT_DUNGEON_DEPTH, seed=new_seed)

    _reinitialize_room_state(state)
    state.turn_number = 0

    # Advance civic pulse (1 tick per dungeon run)
    if state.engine and state.engine.civic_pulse:
        events = state.engine.civic_pulse.advance(1)
        if events:
            from codex.core.services.town_crier import CrierVoice, BURNWILLOW_CRIER_TEMPLATES
            crier = CrierVoice(system_theme="burnwillow")
            crier.register_templates("burnwillow", BURNWILLOW_CRIER_TEMPLATES)
            for ev in events:
                rumor = crier.narrate(ev, {})
                msgs.append(f"[dim italic]{rumor}[/dim italic]")

    msgs.append("The dungeon shifts. A new path awaits.")
    return msgs


def action_recap(state: GameState) -> List[str]:
    """Generate a session recap from the chronicle log (WO-V37.0)."""
    from codex.core.services.narrative_loom import summarize_session
    snapshot = {
        "party": [
            {"name": c.name, "hp": c.current_hp, "max_hp": c.max_hp}
            for c in (state.engine.party if state.engine else [])
        ],
        "doom": state.engine.doom_clock.current if state.engine else 0,
        "turns": state.turn_number,
        "chapter": state.narrative.chapter if state.narrative and hasattr(state.narrative, 'chapter') else 1,
        "completed_quests": (
            [q.title for q in state.narrative.completed_quests]
            if state.narrative and hasattr(state.narrative, 'completed_quests')
            else []
        ),
    }
    mimir_fn = getattr(state, '_mimir_fn', None)
    return [summarize_session(state.session_log, snapshot, mimir_fn)]


def action_help(page: int = 1) -> List[str]:
    """Return paged help text. Pages are 1-indexed."""
    idx = max(0, min(page - 1, len(_HELP_PAGES) - 1))
    return list(_HELP_PAGES[idx])


# =============================================================================
# DUNGEON NPC ENCOUNTERS
# =============================================================================

def _handle_dungeon_npc_encounter(state: GameState, room_id: int) -> List[str]:
    """Check for and handle a random NPC encounter in a dungeon room.

    Only triggers in rooms without enemies. Uses deterministic seed
    based on engine seed + room_id for repeatable encounters.

    Returns list of messages (empty if no encounter).
    """
    if not state.narrative:
        return []
    # Only in empty rooms (no enemies)
    if state.room_enemies.get(room_id):
        return []

    room_node = state.engine.dungeon_graph.get_room(room_id) if state.engine else None
    tier = room_node.tier if room_node else 1
    _seed = state.engine.dungeon_graph.seed if state.engine and state.engine.dungeon_graph else 0
    encounter_rng = random.Random(_seed + room_id + 9999)
    dungeon_npc = state.narrative.roll_dungeon_npc_encounter(tier, encounter_rng)
    if not dungeon_npc:
        return []

    con = state.console
    msgs = []

    # Display NPC
    con.print(f"\n  [bold cyan]You encounter someone.[/]")
    con.print(f"  [bold]{dungeon_npc.name}[/] ({dungeon_npc.role}) -- {dungeon_npc.description}")

    # Greeting (Mimir-enhanced if available)
    greeting = state.narrative.synthesize_npc_dialogue(dungeon_npc, "greeting")
    con.print(f'  "{greeting}"')
    msgs.append(f"Met {dungeon_npc.name} ({dungeon_npc.role}).")

    # Interaction menu
    while True:
        options = ["[1] Talk (Lore)"]
        if dungeon_npc.dialogue_trade or dungeon_npc.dialogue_trade_seed:
            options.append("[2] Trade")
        if dungeon_npc.dialogue_quest or dungeon_npc.dialogue_quest_seed:
            options.append("[3] Quest")
        options.append("[0] Leave")
        con.print("  " + "  ".join(options))

        try:
            choice = Prompt.ask("  >", console=con, default="0")
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            lore = state.narrative.synthesize_npc_dialogue(dungeon_npc, "lore")
            if lore:
                con.print(f'  "{lore}"')
            else:
                con.print("  [dim]They have nothing more to say.[/]")
        elif choice == "2":
            trade = state.narrative.synthesize_npc_dialogue(dungeon_npc, "trade")
            if trade:
                con.print(f'  "{trade}"')
            else:
                con.print("  [dim]They have nothing to trade.[/]")
        elif choice == "3":
            # WO-V44.0: Offer a real quest from this dungeon NPC
            offered_quest = None
            if state.narrative:
                offered_quest = state.narrative.offer_dungeon_quest(dungeon_npc)
            if offered_quest:
                # Show flavor dialogue first
                quest_dialogue = state.narrative.synthesize_npc_dialogue(dungeon_npc, "quest")
                if quest_dialogue:
                    con.print(f'  "{quest_dialogue}"')
                con.print(f'  [yellow]New Quest: {offered_quest.title}[/]')
                con.print(f'  {offered_quest.description}')
                accept = Prompt.ask("  Accept? [y/n]", console=con, default="y")
                if accept.lower() == "y":
                    accept_msg = state.narrative.accept_quest(offered_quest.quest_id)
                    con.print(f"  [green]{accept_msg}[/]")
                    # WO-V45.0: Record dungeon NPC quest anchor in memory
                    if hasattr(state, '_npc_memory') and state._npc_memory:
                        bank = state._npc_memory.register_npc(
                            name=dungeon_npc.name,
                            role=dungeon_npc.role,
                        )
                        bank.record_anchor(
                            f"Gave quest '{offered_quest.title}' to a delver.",
                            tags=["quest_given"],
                        )
                else:
                    con.print("  [dim]Perhaps another time.[/]")
            else:
                quest_dialogue = state.narrative.synthesize_npc_dialogue(dungeon_npc, "quest") if state.narrative else ""
                if quest_dialogue:
                    con.print(f'  "{quest_dialogue}"')
                else:
                    con.print("  [dim]They have no requests.[/]")
        else:
            con.print("  [dim]You move on.[/]")
            break

    dungeon_npc.encountered = True
    # WO-V56.0: Memory shard for NPC encounter
    mem = getattr(state.engine, 'memory_engine', None)
    if mem:
        mem.create_shard(
            f"Met {dungeon_npc.name}, a {dungeon_npc.role}",
            shard_type="ANCHOR",
            tags=["npc", dungeon_npc.name.lower()],
        )
    return msgs


# =============================================================================
# DM SCREEN (WO-V31.0 Phase 1A)
# =============================================================================

def _dm_screen_menu(state: GameState):
    """DM Screen sub-menu with 10 tools. Does NOT advance Doom or consume an action."""
    con = state.console
    from codex.core import dm_tools
    from codex.games.burnwillow.content import lookup_creature

    while True:
        con.print(Panel(
            "[1] Roll Dice    [2] Generate NPC   [3] Generate Trap\n"
            "[4] Roll Loot    [5] Gen Encounter   [6] Bestiary\n"
            "[7] DC Table     [8] Conditions      [9] Names\n"
            "[0] Session Notes\n"
            "[b] Back",
            title="DM Screen",
            border_style="dark_goldenrod",
        ))

        try:
            choice = Prompt.ask("[dark_goldenrod]DM>[/]", console=con, default="b")
        except (EOFError, KeyboardInterrupt):
            break

        choice = choice.strip().lower()

        if choice in ("b", "back", "q"):
            break

        elif choice == "1":
            expr = Prompt.ask("  Dice expression (e.g. 2d6+3)", console=con, default="1d20")
            total, msg = dm_tools.roll_dice(expr)
            con.print(f"  {msg}")

        elif choice == "2":
            arch = Prompt.ask("  Archetype (blank=random)", console=con, default="")
            result = dm_tools.generate_npc(arch)
            con.print(Panel(result, title="NPC", border_style="cyan"))

        elif choice == "3":
            diff = Prompt.ask("  Difficulty (easy/medium/hard)", console=con, default="medium")
            result = dm_tools.generate_trap(diff)
            con.print(Panel(result, title="Trap", border_style="red"))

        elif choice == "4":
            diff = Prompt.ask("  Difficulty (easy/medium/hard)", console=con, default="medium")
            ps = Prompt.ask("  Party size", console=con, default="4")
            try:
                ps_int = int(ps)
            except ValueError:
                ps_int = 4
            result = dm_tools.calculate_loot(diff, ps_int)
            con.print(Panel(result, title="Loot", border_style="yellow"))

        elif choice == "5":
            tier = Prompt.ask("  Tier (1-4)", console=con, default="1")
            ps = Prompt.ask("  Party size", console=con, default="4")
            try:
                tier_int = int(tier)
                ps_int = int(ps)
            except ValueError:
                tier_int, ps_int = 1, 4
            result = dm_tools.generate_encounter("BURNWILLOW", tier_int, ps_int)
            con.print(Panel(result, title="Encounter", border_style="magenta"))

        elif choice == "6":
            query = Prompt.ask("  Creature name/search", console=con, default="")
            if query:
                result = lookup_creature(query)
                if result:
                    con.print(Panel(result, title="Bestiary", border_style="green"))
                else:
                    con.print("  [dim]No creature found.[/]")

        elif choice == "7":
            dc_text = (
                "DC  8 — Routine (breaking crates, climbing rope)\n"
                "DC 12 — Hard (picking locks, jumping chasms)\n"
                "DC 16 — Heroic (bending iron bars, deciphering runes)\n"
                "DC 20 — Legendary (resisting dragon fear)"
            )
            con.print(Panel(dc_text, title="DC Table", border_style="blue"))

        elif choice == "8":
            cond_text = (
                "Poisoned — 1d6 damage/turn, DC 12 Grit to end\n"
                "Restrained — Cannot move, attacks at -1d6\n"
                "Blinded — Attacks at -2d6, auto-fail Wits checks\n"
                "Prone — Stand costs half movement, melee +1d6 vs you\n"
                "Frightened — Cannot approach source, -1d6 to all checks\n"
                "Burning — 1d6 fire/turn, DC 10 action to extinguish"
            )
            con.print(Panel(cond_text, title="Conditions", border_style="bright_red"))

        elif choice == "9":
            try:
                from codex.core.world.grapes_engine import generate_name
                names = [generate_name() for _ in range(5)]
                con.print(f"  Generated names: {', '.join(names)}")
            except ImportError:
                import random as _rng
                fallback = ["Theron", "Bryn", "Isolde", "Corwin", "Neve",
                           "Aldric", "Petra", "Caelum", "Selene", "Hadrik"]
                names = _rng.sample(fallback, min(5, len(fallback)))
                con.print(f"  Names: {', '.join(names)}")

        elif choice == "0":
            log_text = "\n".join(state.message_log[-20:]) if state.message_log else "(empty)"
            result = dm_tools.summarize_context(log_text)
            con.print(Panel(result, title="Session Notes", border_style="dim"))

        try:
            Prompt.ask("[dim]Press Enter[/]", console=con, default="")
        except (EOFError, KeyboardInterrupt):
            break


# =============================================================================
# AUTOPILOT HELPERS (WO-V31.0 Phase 1C)
# =============================================================================

def _should_autopilot(state: GameState, char: Optional[Character] = None) -> bool:
    """Returns True if the given character should be AI-controlled.

    In autopilot mode: all characters are AI-controlled.
    In companion mode: only non-first characters are AI-controlled.
    """
    if state.autopilot_mode:
        return True
    if state.companion_mode and char:
        # First party member is human-controlled
        if state.engine and state.engine.party:
            return char is not state.engine.party[0]
    return False


# =============================================================================
# INPUT PARSER
# =============================================================================

def parse_command(raw: str) -> Tuple[str, List[str]]:
    """Parse raw input into (command, args)."""
    parts = raw.strip().split()
    if not parts:
        return ("", [])
    return (parts[0].lower(), parts[1:])


# =============================================================================
# MAIN GAME LOOP
# =============================================================================

def game_loop(state: GameState, butler=None):
    """The core Init -> Render -> Input -> Logic loop."""
    con = state.console

    # Carry butler reference on state for action_move narration
    state.butler = butler

    # WO 100: Register engine with Butler for session-aware reflexes
    if butler and state.engine:
        butler.register_session(state.engine)

    # WO-V62.0: Initialize momentum threshold handler
    from codex.core.services.momentum_handler import MomentumThresholdHandler
    state.momentum_handler = MomentumThresholdHandler(
        world_ledger=getattr(state.engine, 'world_ledger', None),
        crier=None,
        broadcast_manager=state.broadcast_manager,
        engine=state.engine,
    )

    # WO-V62.0: Create SessionFrame
    from codex.core.session_frame import (
        SessionFrame, ExpeditionTimer, generate_opening_hook,
        generate_epilogue, get_next_session_number, save_session_counter,
    )
    campaign_id = f"burnwillow_{state.dungeon_seed}" if hasattr(state, 'dungeon_seed') else "burnwillow"
    session_number = get_next_session_number(campaign_id)
    state.session_frame = SessionFrame(
        session_id=f"{campaign_id}_s{session_number}",
        session_number=session_number,
        session_type=state._session_type,
        campaign_id=campaign_id,
    )

    # Generate and display opening hook
    hook = generate_opening_hook(
        session_type=state._session_type,
        momentum_ledger=state.momentum_ledger,
        location=getattr(state, 'current_location_id', 'burnwillow'),
    )
    if hook:
        state.session_frame.opening_hook = hook
        state.add_log(f"[italic]{hook}[/italic]")

    # Clear any zombie combat flags from prior session
    state.clear_volatile_state()

    try:
        _game_loop_inner(state, butler=butler)
    finally:
        # WO-V62.0: Close session frame on exit
        if state.session_frame and not state.session_frame.ended_at:
            state.session_frame.turn_count = state.turn_number
            state.session_frame.close(state.session_log)
            save_session_counter(state.session_frame.campaign_id or "", state.session_frame.session_number)
            epilogue = generate_epilogue(
                state.session_log, state._session_type, state.momentum_ledger,
            )
            if epilogue:
                con.print(Panel(f"[italic]Meanwhile...[/italic]\n\n{epilogue}",
                                title="Epilogue", border_style="dim"))

        # WO 100: Always clear session on exit
        if butler:
            butler.clear_session()


def _game_loop_inner(state: GameState, butler=None):
    """Inner game loop (separated for try/finally session cleanup)."""
    con = state.console

    while state.running:
        # WO-V62.0: Expedition timer tick
        if state.expedition_timer:
            supply_msg = state.expedition_timer.tick()
            if supply_msg:
                state.add_log(supply_msg)
            if state.expedition_timer.exhausted:
                state.add_log("[bold red]Your supplies are gone. You must return to Emberhome.[/bold red]")
                state.in_settlement = True
                state.running = False
                break

        # Check total party kill
        if state.engine and state.engine.party:
            alive = state.engine.get_active_party()
            if not alive:
                screen_refresh(state)
                render_death_screen(state)
                _broadcast_death(state)
                # Advance civic pulse (1 tick per dungeon run)
                if state.engine and state.engine.civic_pulse:
                    events = state.engine.civic_pulse.advance(1)
                    if events:
                        from codex.core.services.town_crier import CrierVoice, BURNWILLOW_CRIER_TEMPLATES
                        crier = CrierVoice(system_theme="burnwillow")
                        crier.register_templates("burnwillow", BURNWILLOW_CRIER_TEMPLATES)
                        for ev in events:
                            rumor = crier.narrate(ev, {})
                            state.add_log(f"[dim italic]{rumor}[/dim italic]")
                state.running = False
                break
        elif state.character and not state.character.is_alive():
            screen_refresh(state)
            render_death_screen(state)
            _broadcast_death(state)
            # Advance civic pulse (1 tick per dungeon run)
            if state.engine and state.engine.civic_pulse:
                events = state.engine.civic_pulse.advance(1)
                if events:
                    from codex.core.services.town_crier import CrierVoice, BURNWILLOW_CRIER_TEMPLATES
                    crier = CrierVoice(system_theme="burnwillow")
                    crier.register_templates("burnwillow", BURNWILLOW_CRIER_TEMPLATES)
                    for ev in events:
                        rumor = crier.narrate(ev, {})
                        state.add_log(f"[dim italic]{rumor}[/dim italic]")
            state.running = False
            break

        # Check victory: boss room cleared
        if state.engine and state.current_room_id is not None:
            current_room_node = state.engine.dungeon_graph.get_room(state.current_room_id)
            if (current_room_node and
                    current_room_node.room_type == RoomType.BOSS and
                    state.current_room_id in state.cleared_rooms):
                screen_refresh(state)
                render_victory_screen(state)
                _broadcast_victory(state, butler=butler)

                # Module-based play: advance to next zone instead of ending
                if state.module_manifest and advance_to_next_zone(state):
                    con.print(Panel(
                        f"[bold green]Zone cleared! Advancing to next zone...[/bold green]\n"
                        f"[dim]Chapter {state.current_chapter_idx + 1}, "
                        f"Zone {state.current_zone_idx + 1}[/dim]",
                        border_style="green",
                    ))
                    try:
                        Prompt.ask("\n[dim]Press Enter to continue[/]",
                                   console=con, default="")
                    except (EOFError, KeyboardInterrupt):
                        state.running = False
                        break
                    # Regenerate dungeon for new zone, preserving party
                    state.cleared_rooms.clear()
                    state.room_enemies.clear()
                    state.room_loot.clear()
                    state.searched_rooms.clear()
                    state.scouted_rooms.clear()
                    state.spatial_rooms.clear()
                    state.room_furniture.clear()
                    state.clear_combat_effects()
                    state.first_strike_used = False
                    con.print("[dim]Generating next dungeon...[/dim]")
                    summary = state.engine.generate_dungeon()
                    con.print(f"  Rooms: {summary['total_rooms']}  |  Start: Room {summary['start_room']}")
                    _rebuild_spatial_rooms(state)
                    continue

                state.running = False
                break

        # Render
        screen_refresh(state)

        # Combat mode: run structured combat rounds
        if state.combat_mode:
            enemies = state.room_enemies.get(state.current_room_id, [])
            if enemies:
                messages = run_combat_round(state)
                if messages:
                    # Append combat summary to persistent log
                    state.add_log("\n[COMBAT SUMMARY]")
                    for msg in messages:
                        state.add_log(f"  {msg}")
                    
                    # Force a render update to show combat results
                    screen_refresh(state)

                    # WO 102: Sync game state to bridge file for voice
                    if butler:
                        butler.sync_session_to_file()

                    # WO-V31.0: Bypass press-enter in autopilot mode
                    if _should_autopilot(state):
                        import time as _time
                        _time.sleep(state.autopilot_delay * 0.5)
                    else:
                        try:
                            Prompt.ask("[dim]Press Enter to continue[/]", console=con, default="")
                        except (EOFError, KeyboardInterrupt):
                            state.running = False
                continue
            else:
                state.end_combat()

        # Exploration mode: Input
        # Show active character name in party turn mode (WO V20.3)
        if state.is_party_turn_mode():
            turn_char = state.get_turn_character()
            prompt_label = f"[bold {THEME_CFG.color_current}][{turn_char.name}]>[/]"
        else:
            turn_char = state.active_leader
            prompt_label = f"[bold {THEME_CFG.color_current}]>[/]"

        # WO-V31.0: Autopilot exploration interception
        if _should_autopilot(state, turn_char):
            import time as _time
            snapshot = build_exploration_snapshot(state)
            agent = state.autopilot_agents.get(
                turn_char.name if turn_char else "",
                next(iter(state.autopilot_agents.values()), None)
            )
            if agent:
                raw_input = agent.decide_exploration(snapshot)
                con.print(f"  [dim][AI: {turn_char.name if turn_char else 'autopilot'}] {raw_input}[/dim]")
                _time.sleep(state.autopilot_delay * 0.5)
            else:
                raw_input = "end"
        else:
            try:
                raw_input = Prompt.ask(
                    prompt_label,
                    console=con,
                    default=""
                )
            except (EOFError, KeyboardInterrupt):
                con.print("\nFarewell, adventurer.")
                state.running = False
                break

        cmd, args = parse_command(raw_input)

        if not cmd:
            continue

        # Resolve aliases via unified command registry
        resolved = state.command_registry.resolve(cmd)
        if resolved:
            cmd = resolved.canonical

        # Logic
        new_messages = []

        if cmd in ("quit", "exit", "q"):
            save_choice = Prompt.ask(
                "[dim]Save before quitting?[/]",
                choices=["y", "n"],
                default="y",
                console=con,
            )
            if save_choice.lower() == "y":
                save_msgs = action_save(state)
                for msg in save_msgs:
                    con.print(f"[green]{msg}[/green]")
            # WO-V37.0: Auto-show recap on quit if session has events
            if state.session_log:
                con.print("")
                recap_msgs = action_recap(state)
                for msg in recap_msgs:
                    con.print(msg)
                con.print("")
            con.print("\nThe dungeon swallows your retreat. Farewell.")
            state.running = False
            break

        elif cmd == "help":
            page = 1
            if args:
                try:
                    page = int(args[0])
                except ValueError:
                    pass
            help_lines = action_help(page)
            state.push_sidebar("\n".join(help_lines))
            new_messages = [f"Help page {page}/3 -- see sidebar."]

        elif cmd == "recap":
            recap_lines = action_recap(state)
            state.push_sidebar("\n".join(recap_lines))
            new_messages = ["Session recap -- see sidebar."]

        elif cmd == "look" or cmd == "l":
            new_messages = action_look(state)

        elif cmd in ("inv", "inventory", "i", "gear", "backpack", "doll", "sheet"):
            new_messages = action_inventory(state, use_paper_doll=True)

        elif cmd == "party":
            new_messages = action_party(state)

        elif cmd in ("n", "s", "e", "w", "ne", "nw", "se", "sw",
                     "north", "south", "east", "west",
                     "northeast", "northwest", "southeast", "southwest"):
            if state.remaining_movement < TILE_SIZE_FT:
                new_messages = [f"No movement remaining ({state.remaining_movement}ft). Type 'end' to end your turn."]
            else:
                result = state.engine.move_player_grid(cmd)
                if result.get("bump_pos"):
                    # Door-snap: engine detected a nearby door
                    if result.get("door_exit") is not None:
                        state.remaining_movement -= TILE_SIZE_FT
                        new_messages = action_move(state, result["door_exit"])
                    else:
                        # Existing wall bump: check for room exit in this direction
                        exit_info = _find_exit_in_direction(state, cmd)
                        if exit_info and not exit_info.get("is_locked"):
                            state.remaining_movement -= TILE_SIZE_FT
                            new_messages = action_move(state, exit_info["id"])
                        elif exit_info and exit_info.get("is_locked"):
                            new_messages = [f"The way {exit_info['direction']} is locked."]
                        else:
                            bump_msgs = _resolve_bump(state, result["bump_pos"])
                            new_messages = bump_msgs or [result["message"]]
                else:
                    state.remaining_movement -= TILE_SIZE_FT
                    new_messages = [result["message"]]

        elif cmd in ("move", "go"):
            if not args:
                new_messages = ["Usage: move <room_id or direction>  (e.g. move 5, move n, move e1)"]
            elif state.remaining_movement < TILE_SIZE_FT:
                new_messages = [f"No movement remaining ({state.remaining_movement}ft). Type 'end' to end your turn."]
            else:
                target_str = args[0].lower()
                if target_str in state.cached_exit_labels:
                    target_id = state.cached_exit_labels[target_str]
                    state.remaining_movement -= TILE_SIZE_FT
                    new_messages = action_move(state, target_id)
                else:
                    try:
                        target = int(target_str)
                        state.remaining_movement -= TILE_SIZE_FT
                        new_messages = action_move(state, target)
                    except ValueError:
                        new_messages = [f"Unknown direction or room: '{target_str}'. Check exits in sidebar."]

        elif cmd == "scout":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            elif not args:
                new_messages = ["Usage: scout <room_id>"]
            else:
                try:
                    target = int(args[0])
                    new_messages = action_scout(state, target)
                    state.action_taken = True
                except ValueError:
                    new_messages = ["Room ID must be a number."]

        elif cmd == "search":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            else:
                new_messages = action_search(state)
                state.action_taken = True

        elif cmd in ("bind", "heal", "rest"):
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            else:
                new_messages = action_bind_wounds(state)
                state.action_taken = True

        elif cmd in ("attack", "atk", "fight"):
            # Out-of-combat attack triggers combat mode first
            enemies = state.room_enemies.get(state.current_room_id, [])
            if enemies and not state.combat_mode:
                state.start_combat()
                new_messages = ["Combat begins!"]
            elif not enemies:
                new_messages = ["There are no enemies here to fight."]
            # Combat round will be handled on next loop iteration

        elif cmd == "inspect":
            if not args:
                new_messages = ["Usage: inspect <target> | inspect item <idx/name> | inspect equipped <name>"]
            elif args[0].lower() == "equipped" and len(args) > 1:
                # WO V20.3 4B: Inspect equipped gear by slot/name
                search = " ".join(args[1:]).lower()
                char = state.active_character
                found = False
                if char and char.gear_grid:
                    for slot, item in char.gear_grid.slots.items():
                        if item and (search in item.name.lower() or search in slot.name.lower()):
                            detail = render_item_detail(item)
                            state.push_sidebar(detail)
                            new_messages = [f"Inspecting {item.name} -- see sidebar."]
                            found = True
                            break
                if not found:
                    new_messages = [f"No equipped item matching '{search}'."]
            elif args[0].lower() == "item" and len(args) > 1:
                try:
                    idx = int(args[1])
                    new_messages = action_inspect_item(state, idx)
                except ValueError:
                    # WO V20.3 4B: Try name-based search in inventory
                    search = " ".join(args[1:]).lower()
                    char = state.active_character
                    found = False
                    if char:
                        for idx, item in char.inventory.items():
                            if search in item.name.lower():
                                new_messages = action_inspect_item(state, idx)
                                found = True
                                break
                    if not found:
                        new_messages = [f"No inventory item matching '{search}'."]
            else:
                new_messages = action_inspect(state, " ".join(args))

        elif cmd == "interact":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            else:
                new_messages = action_interact(state, args)
                state.action_taken = True

        elif cmd == "loot":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            else:
                new_messages = action_loot(state)
                state.action_taken = True

        elif cmd == "equip":
            if not args:
                new_messages = ["Usage: equip <index> [slot]  (e.g. equip 0 left hand)"]
            else:
                slot_override_str = " ".join(args[1:]).lower() if len(args) > 1 else None
                target_slot = SLOT_ALIASES.get(slot_override_str) if slot_override_str else None
                try:
                    idx = int(args[0])
                    new_messages = action_equip(state, idx, target_slot=target_slot)
                except ValueError:
                    new_messages = ["Usage: equip <index> [slot]  (e.g. equip 0 left hand)"]

        elif cmd == "map":
            # Debug: show all rooms
            _rebuild_spatial_rooms(state)
            debug_panel = render_spatial_map(
                rooms=state.spatial_rooms,
                player_room_id=state.current_room_id,
                theme=THEME,
                viewport_width=60,
                viewport_height=30,
                console=con,
                player_pos=state.engine.player_pos if state.engine else None,
            )
            con.print(debug_panel)
            new_messages = ["(Debug map rendered above)"]

        # Support actions available out of combat too (triage/bind)
        elif cmd == "triage":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            elif not args:
                new_messages = ["Usage: triage <name>"]
            else:
                new_messages = action_triage(state, " ".join(args))
                state.action_taken = True

        elif cmd == "summon":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            else:
                new_messages = action_summon(state)
                state.action_taken = True

        elif cmd == "recruit":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            else:
                new_messages = action_recruit(state)
                state.action_taken = True

        elif cmd in ("return", "extract", "retreat", "leave"):
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            else:
                new_messages = action_return(state)
                state.action_taken = True

        elif cmd == "end":
            turn_char = state.get_turn_character()
            if turn_char:
                new_messages = [f"{turn_char.name} ends their turn."]
            else:
                new_messages = ["Turn ends."]
            new_messages.extend(_end_exploration_turn(state, doom_cost=0))

        elif cmd in ("wait", "pass"):
            turn_char = state.get_turn_character()
            if turn_char:
                new_messages = [f"{turn_char.name} waits."]
            else:
                new_messages = ["You wait."]
            new_messages.extend(_end_exploration_turn(state, doom_cost=1))

        elif cmd in ("clear", "cls"):
            state.clear_sidebar()
            new_messages = ["Sidebar cleared."]

        elif cmd == "[":
            # Scroll sidebar back toward older content
            state.sidebar_view_offset = min(
                state.sidebar_view_offset + 10,
                max(0, len(state.sidebar_buffer) - SIDEBAR_WINDOW_SIZE),
            )
            new_messages = []  # Pure UI action, no log entry

        elif cmd == "]":
            # Scroll sidebar toward newer content
            state.sidebar_view_offset = max(0, state.sidebar_view_offset - 10)
            new_messages = []  # Pure UI action, no log entry

        elif cmd == "save":
            new_messages = action_save(state)

        elif cmd == "load":
            new_messages = action_load(state)

        elif cmd == "roll" or cmd == "r":
            new_messages = _handle_roll(state, args)

        elif cmd == "library":
            new_messages = action_library(state)

        elif cmd == "refresh_lore":
            try:
                from codex.core.cache import LoreCache
                cache = LoreCache()
                removed = cache.clear(system_tag=state.system_id)
                new_messages = [f"Lore cache cleared for '{state.system_id}' ({removed} entries). Next queries will re-fetch."]
            except ImportError:
                new_messages = ["Lore cache module not available."]

        elif cmd == "switch":
            if not args:
                new_messages = ["Usage: switch <party_index>  (e.g. switch 1)"]
            else:
                try:
                    idx = int(args[0])
                    party = state.engine.get_active_party()
                    if 0 <= idx < len(party):
                        state.active_leader_override = idx
                        new_messages = [f"Now controlling: {party[idx].name}"]
                    else:
                        new_messages = [f"Invalid. Party has {len(party)} members (0-{len(party)-1})."]
                except ValueError:
                    new_messages = ["Usage: switch <party_index>"]

        elif cmd == "give":
            deny = _check_action_available(state)
            if deny:
                new_messages = [deny]
            elif len(args) < 3 or args[1].lower() != "to":
                new_messages = ["Usage: give <inv_index> to <party_index>  (e.g. give 0 to 1)"]
            else:
                try:
                    inv_idx = int(args[0])
                    target_idx = int(args[2])
                    new_messages = action_give(state, inv_idx, target_idx)
                    state.action_taken = True
                except ValueError:
                    new_messages = ["Usage: give <inv_index> to <party_index>"]

        elif cmd in ("quest", "journal", "quests"):
            _settlement_quest_log(state)
            new_messages = []

        elif cmd == "talk" and args:
            target_name = " ".join(args)
            # WO-V31.0: Companion talk in dungeon
            if state.companion_mode and state.autopilot_agents:
                agent = state.autopilot_agents.get(target_name)
                if agent:
                    # Use narrative engine talk_to_npc if available
                    if state.narrative and hasattr(state.narrative, 'talk_to_npc'):
                        dialogue = state.narrative.talk_to_npc(target_name)
                        if dialogue:
                            new_messages = [f'[cyan]{target_name}[/]: "{dialogue}"']
                        else:
                            # Fallback: personality-based quip
                            new_messages = [f'[cyan]{target_name}[/]: "{agent.personality.quirk}"']
                    else:
                        new_messages = [f'[cyan]{target_name}[/]: "{agent.personality.quirk}"']
                else:
                    # Check partial match
                    matches = [n for n in state.autopilot_agents if target_name.lower() in n.lower()]
                    if matches:
                        matched = matches[0]
                        a = state.autopilot_agents[matched]
                        new_messages = [f'[cyan]{matched}[/]: "{a.personality.quirk}"']
                    else:
                        new_messages = ["No companion by that name. NPCs appear in empty rooms."]
            else:
                new_messages = ["There's no one to talk to here. NPCs appear in empty rooms."]

        elif cmd == "dm":
            _dm_screen_menu(state)
            new_messages = []  # DM screen is a sub-menu, no log entry

        elif cmd == "tutorial":
            try:
                from codex.core.services.tutorial import TutorialBrowser
                import codex.core.services.tutorial_content  # noqa: F401
                browser = TutorialBrowser(tutorial=state.tutorial, system_filter="burnwillow")
                browser.run_loop(state.console)
            except Exception:
                pass
            new_messages = []

        else:
            new_messages = [f"Unknown command: '{cmd}'. Type 'help' for a list of commands."]

        # Tutorial hint
        if hasattr(state, 'tutorial') and state.tutorial:
            state.tutorial.record_command(cmd)
            hint = state.tutorial.get_hint(cmd)
            if hint:
                new_messages.append(hint)

        # Update persistent log (rolling buffer display)
        if new_messages:
            for msg in new_messages:
                state.add_log(msg)
            # Pin latest action result for next frame
            state.last_action_result = "\n".join(new_messages[-3:])

        # WO 102: Sync game state to bridge file for voice
        if butler:
            butler.sync_session_to_file()


# =============================================================================
# ENTRY POINT
# =============================================================================

def main(butler=None, characters=None, autopilot=False, companion=False,
         autopilot_delay=1.5, companion_name=None, cli_seed=None,
         module_manifest_path=None, session_type=None):
    """Launch the Burnwillow interactive game loop.

    Args:
        butler: Optional CodexButler for session-aware reflexes.
        characters: Optional list of pre-built Character objects (from adapter).
                    If provided, skips party size/name/loadout prompts.
        autopilot: If True, all characters are AI-controlled.
        companion: If True, an AI companion joins the player.
        autopilot_delay: Seconds between autopilot actions.
        companion_name: Optional name for AI companion.
        cli_seed: Optional dungeon seed from CLI.
        module_manifest_path: Optional path to module_manifest.json for zone
                              progression. When set, the game advances through
                              module zones instead of ending after boss defeat.
    """
    con = Console()

    # Title screen
    render_title_screen(con)

    # WO-V62.0: Session type selection
    # WO-V63.0: Skip when loading a saved campaign with known session type
    from codex.core.session_behaviors import get_session_labels, get_expedition_budget
    _session_type = session_type  # May be pre-set from saved campaign
    if _session_type:
        con.print(f"[dim]Session type: {_session_type}[/dim]")

    if _session_type is None:
        labels = get_session_labels("burnwillow")
        con.print("\n[bold]Choose session type:[/bold]")
        for i, (stype, (label, desc)) in enumerate(labels.items(), 1):
            con.print(f"  [{i}] [bold]{label}[/] — {desc}")
        try:
            stype_choice = Prompt.ask("Select", console=con,
                                      choices=[str(i) for i in range(1, len(labels)+1)], default="3")
            session_types_list = list(labels.keys())
            _session_type = session_types_list[int(stype_choice) - 1]
        except (EOFError, KeyboardInterrupt):
            return

    # Load module manifest if provided
    _loaded_manifest = None
    if module_manifest_path:
        try:
            from codex.spatial.module_manifest import ModuleManifest
            _loaded_manifest = ModuleManifest.load(module_manifest_path)
        except Exception:
            pass

    # --- WO 103: Pre-built characters from adapter bypass interactive setup ---
    if characters:
        state = GameState()
        state.console = con
        state._session_type = _session_type
        if _session_type == "expedition":
            from codex.core.session_frame import ExpeditionTimer
            state.expedition_timer = ExpeditionTimer(turn_budget=get_expedition_budget("burnwillow"))
        if _loaded_manifest:
            state.module_manifest = _loaded_manifest
        party_size = len(characters)

        con.print(f"\n[bold {THEME_CFG.color_current}]Generating dungeon...[/]")
        summary = init_game_with_characters(state, characters)
        con.print(f"  Seed: {summary['seed']}  |  Rooms: {summary['total_rooms']}  |  Start: Room {summary['start_room']}")

        # Show party summary
        for char in state.engine.party:
            gear_names = [item.name for item in char.gear.slots.values() if item]
            gear_str = ", ".join(gear_names) if gear_names else "bare hands"
            con.print(f"  {char.name}: {char.current_hp} HP | MIG {char.might} WIT {char.wits} GRT {char.grit} AET {char.aether} | {gear_str}")

        if state.dungeon_path == "ascend":
            entry_verb = "ascends into the burning canopy"
            entry_party = "The party ascends into the burning canopy of Burnwillow."
        else:
            entry_verb = "descends into the Burnwillow roots"
            entry_party = "The party descends into the roots of Burnwillow."

        if party_size == 1:
            entry_text = f"{state.character.name} {entry_verb}."
            con.print(f"\n  {entry_text}")
        else:
            entry_text = entry_party
            con.print(f"\n  {entry_text}")

        # TTS: narrate dungeon entry
        if butler and hasattr(butler, 'narrate'):
            try:
                butler.narrate(entry_text)
            except Exception:
                pass

        try:
            Prompt.ask("\n[dim]Press Enter to begin[/]", console=con, default="")
        except (EOFError, KeyboardInterrupt):
            return

        game_loop(state, butler=butler)
        con.print(f"\n[dim]Game over. Final Doom: {state.doom}, Turns: {state.turn_number}[/]\n")
        return

    # --- WO-V31.0: Autopilot / Companion party creation bypass ---
    if autopilot or companion:
        import time as _time
        state = GameState()
        state.console = con
        state._session_type = _session_type
        if _session_type == "expedition":
            from codex.core.session_frame import ExpeditionTimer
            state.expedition_timer = ExpeditionTimer(turn_budget=get_expedition_budget("burnwillow"))
        if _loaded_manifest:
            state.module_manifest = _loaded_manifest
        state.autopilot_mode = autopilot
        state.companion_mode = companion
        state.autopilot_delay = autopilot_delay

        if autopilot:
            # Full autopilot: create 2 AI characters
            con.print(f"\n  [bold cyan]AUTOPILOT MODE[/bold cyan] — All characters AI-controlled")
            con.print(f"  [dim]Delay: {autopilot_delay}s between actions[/dim]\n")
            p1, n1, s1, l1, b1 = create_ai_character(seed=42)
            p2, n2, s2, l2, b2 = create_ai_character(seed=99)
            ai_names = [n1, n2]
            ai_specs = [(n1, s1, l1), (n2, s2, l2)]

            con.print(f"  [bold {THEME_CFG.color_current}]Generating dungeon...[/]")
            seed = cli_seed
            summary = init_game(state, ai_names, seed, char_specs=ai_specs)
            con.print(f"  Seed: {summary['seed']}  |  Rooms: {summary['total_rooms']}  |  Start: Room {summary['start_room']}")

            state.autopilot_agents[n1] = AutopilotAgent(personality=p1, biography=b1)
            state.autopilot_agents[n2] = AutopilotAgent(personality=p2, biography=b2)

            # Register companions as NPCs for dialogue
            for name, agent in state.autopilot_agents.items():
                register_companion_as_npc(
                    state.engine, name, agent.personality, agent.biography,
                    narrative_engine=state.narrative,
                )

        else:
            # Companion mode: human char 1, AI char 2
            con.print(f"\n  [bold green]COMPANION MODE[/bold green] — AI partner joins your party")
            con.print(f"  [dim]Delay: {autopilot_delay}s for companion actions[/dim]\n")

            # Human character creation
            try:
                name = Prompt.ask(
                    f"[bold {THEME_CFG.color_current}]Enter your name[/]",
                    console=con, default="Kael"
                )
            except (EOFError, KeyboardInterrupt):
                return

            # AI companion
            comp_p, comp_n, comp_s, comp_l, comp_b = create_ai_character(
                name=companion_name
            )
            con.print(f"  [cyan]{comp_n}[/] ({comp_p.archetype}) joins your party.")
            con.print(f"  [dim]{comp_p.quirk}[/]\n")

            names = [name, comp_n]
            char_specs = [(name, None, None), (comp_n, comp_s, comp_l)]

            # For human char: use quick-start (None stats/loadout)
            con.print(f"  [bold {THEME_CFG.color_current}]Generating dungeon...[/]")
            seed = cli_seed
            summary = init_game(state, names, seed)
            con.print(f"  Seed: {summary['seed']}  |  Rooms: {summary['total_rooms']}  |  Start: Room {summary['start_room']}")

            state.autopilot_agents[comp_n] = AutopilotAgent(
                personality=comp_p, biography=comp_b
            )

            # Register companion as NPC
            register_companion_as_npc(
                state.engine, comp_n, comp_p, comp_b,
                narrative_engine=state.narrative,
            )

        # Show party summary
        for char in state.engine.party:
            gear_names = [item.name for item in char.gear.slots.values() if item]
            gear_str = ", ".join(gear_names) if gear_names else "bare hands"
            tag = " [AI]" if char.name in state.autopilot_agents else ""
            con.print(f"  {char.name}{tag}: {char.current_hp} HP | MIG {char.might} WIT {char.wits} GRT {char.grit} AET {char.aether} | {gear_str}")

        entry_text = "The party descends into the roots of Burnwillow."
        con.print(f"\n  {entry_text}")

        if autopilot:
            _time.sleep(autopilot_delay)
        else:
            try:
                Prompt.ask("\n[dim]Press Enter to begin[/]", console=con, default="")
            except (EOFError, KeyboardInterrupt):
                return

        game_loop(state, butler=butler)
        con.print(f"\n[dim]Game over. Final Doom: {state.doom}, Turns: {state.turn_number}[/]\n")
        return

    # --- Tutorial option on title screen ---
    con.print(f"  [dim][T] Tutorial   [Enter] Play[/]")
    try:
        title_choice = con.input("  > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if title_choice == "t":
        try:
            from codex.core.services.tutorial import TutorialBrowser, PlatformTutorial
            import codex.core.services.tutorial_content  # noqa: F401
            browser = TutorialBrowser(tutorial=PlatformTutorial(), system_filter="burnwillow")
            browser.run_loop(con)
        except Exception as e:
            con.print(f"  [yellow]Tutorial unavailable: {e}[/]")
        render_title_screen(con)

    # --- Standard interactive flow ---

    # Check for existing save -> offer Continue
    save_file = SAVES_DIR / "burnwillow_save.json"
    if save_file.exists():
        try:
            start_choice = Prompt.ask(
                f"[bold {THEME_CFG.color_current}]Save file found. [C]ontinue / [N]ew game?[/]",
                choices=["c", "n"],
                default="c",
                console=con,
            )
        except (EOFError, KeyboardInterrupt):
            con.print("\nFarewell.")
            return

        if start_choice.lower() == "c":
            state = GameState()
            state.console = con
            state._session_type = _session_type
            if _session_type == "expedition":
                from codex.core.session_frame import ExpeditionTimer
                state.expedition_timer = ExpeditionTimer(turn_budget=get_expedition_budget("burnwillow"))
            load_msgs = action_load(state)
            for msg in load_msgs:
                con.print(f"  {msg}")
            try:
                Prompt.ask("\n[dim]Press Enter to resume[/]", console=con, default="")
            except (EOFError, KeyboardInterrupt):
                return
            game_loop(state, butler=butler)
            con.print(f"\n[dim]Game over. Final Doom: {state.doom}, Turns: {state.turn_number}[/]\n")
            return

    # Party size
    try:
        size_input = Prompt.ask(
            f"[bold {THEME_CFG.color_current}]How many adventurers? (1-6)[/]",
            console=con,
            default="1"
        )
    except (EOFError, KeyboardInterrupt):
        con.print("\nFarewell.")
        return

    try:
        party_size = max(1, min(6, int(size_input)))
    except ValueError:
        party_size = 1

    # Creation mode: Wizard (stat allocation + 6 loadouts) or Quick Start (random)
    char_specs = None
    try:
        mode = Prompt.ask(
            f"[bold {THEME_CFG.color_current}][W]izard (full creation) / [Q]uick start (random stats)?[/]",
            console=con,
            choices=["w", "q"],
            default="w",
        )
    except (EOFError, KeyboardInterrupt):
        con.print("\nFarewell.")
        return

    if mode.lower() == "w":
        char_specs = _run_character_wizard(con, party_size)
        if char_specs:
            names = [spec[0] for spec in char_specs]
        else:
            con.print("[dim]Wizard unavailable (missing creation_rules.json). Falling back to Quick Start.[/]")

    if not char_specs:
        # Quick Start: gather names with defaults
        names = []
        default_names = ["Kael", "Sera", "Grim", "Lyra", "Rowan", "Thorne"]
        for i in range(party_size):
            label = "Enter your name" if party_size == 1 else f"Name for adventurer {i+1}"
            try:
                name = Prompt.ask(
                    f"[bold {THEME_CFG.color_current}]{label}[/]",
                    console=con,
                    default=default_names[i]
                )
            except (EOFError, KeyboardInterrupt):
                con.print("\nFarewell.")
                return
            names.append(name)

    # Optional seed
    try:
        seed_input = Prompt.ask(
            f"[{THEME_CFG.color_visited}]Dungeon seed (blank = random)[/]",
            console=con,
            default=""
        )
    except (EOFError, KeyboardInterrupt):
        con.print("\nFarewell.")
        return

    seed = int(seed_input) if seed_input.strip().isdigit() else None

    # Initialize
    state = GameState()
    state.console = con
    state._session_type = _session_type
    if _session_type == "expedition":
        from codex.core.session_frame import ExpeditionTimer
        state.expedition_timer = ExpeditionTimer(turn_budget=get_expedition_budget("burnwillow"))
    if _loaded_manifest:
        state.module_manifest = _loaded_manifest

    con.print(f"\n[bold {THEME_CFG.color_current}]Generating dungeon...[/]")
    summary = init_game(state, names, seed, char_specs=char_specs)
    con.print(f"  Seed: {summary['seed']}  |  Rooms: {summary['total_rooms']}  |  Start: Room {summary['start_room']}")

    # WO-V32.0: Companion backfill — offer to fill empty slots with AI companions
    if len(state.engine.party) < 6 and not state.autopilot_mode and not state.companion_mode:
        open_slots = 6 - len(state.engine.party)
        try:
            fill_choice = Prompt.ask(
                f"[bold {THEME_CFG.color_current}]Fill {open_slots} slot(s) with AI companions? [Y/n][/]",
                console=con, default="y"
            )
        except (EOFError, KeyboardInterrupt):
            fill_choice = "n"
        if fill_choice.lower() in ("y", "yes", ""):
            existing_names = [c.name for c in state.engine.party]
            backfills = create_backfill_companions(
                open_slots, existing_names=existing_names, seed=state.dungeon_seed
            )
            for personality, comp_name, stats, loadout_id, bio in backfills:
                state.engine.create_character_with_stats(
                    comp_name,
                    might=stats.get("Might", 10),
                    wits=stats.get("Wits", 10),
                    grit=stats.get("Grit", 10),
                    aether=stats.get("Aether", 10),
                )
                state.engine.party.append(state.engine.character)
                state.engine.equip_loadout(loadout_id)
                agent = AutopilotAgent(personality=personality, biography=bio)
                state.autopilot_agents[comp_name] = agent
                if state.narrative:
                    register_companion_as_npc(
                        state.engine, comp_name, personality, bio,
                        narrative_engine=state.narrative,
                    )
                con.print(f"  [cyan]{comp_name}[/] ({personality.archetype}) joins the party. [AI]")
            state.engine.character = state.engine.party[0]
            # Recalculate doom rate for new party size
            state.doom_rate_mult = DOOM_RATE_MULT.get(len(state.engine.party), 1.0)
            # Re-scale enemies for new party size
            _scaling = get_party_scaling(len(state.engine.party))
            for room_enemies in state.room_enemies.values():
                for e in room_enemies:
                    # Undo previous 1.0 scaling, apply new
                    old_scaling = get_party_scaling(len(state.engine.party) - open_slots)
                    if old_scaling["hp_mult"] != 0:
                        base_hp = e.get("hp", 1) / old_scaling["hp_mult"]
                        e["hp"] = max(1, int(base_hp * _scaling["hp_mult"]))
                        if "max_hp" in e:
                            base_max = e["max_hp"] / old_scaling["hp_mult"]
                            e["max_hp"] = max(1, int(base_max * _scaling["hp_mult"]))
                    e["_dmg_mult"] = _scaling["dmg_mult"]

    # Show party summary
    for char in state.engine.party:
        gear_names = [item.name for item in char.gear.slots.values() if item]
        gear_str = ", ".join(gear_names) if gear_names else "bare hands"
        con.print(f"  {char.name}: {char.current_hp} HP | MIG {char.might} WIT {char.wits} GRT {char.grit} AET {char.aether} | {gear_str}")

    if state.dungeon_path == "ascend":
        entry_verb = "ascends into the burning canopy"
        entry_party = "The party ascends into the burning canopy of Burnwillow."
    else:
        entry_verb = "descends into the Burnwillow roots"
        entry_party = "The party descends into the roots of Burnwillow."

    if party_size == 1:
        entry_text = f"{state.character.name} {entry_verb}."
        con.print(f"\n  {entry_text}")
        con.print(f"  [dim](Tip: Equip gear with [Summon] to conjure Aether spirits)[/]")
    else:
        entry_text = entry_party
        con.print(f"\n  {entry_text}")

    # TTS: narrate dungeon entry
    if butler and hasattr(butler, 'narrate'):
        try:
            butler.narrate(entry_text)
        except Exception:
            pass

    try:
        Prompt.ask("\n[dim]Press Enter to begin[/]", console=con, default="")
    except (EOFError, KeyboardInterrupt):
        return

    # Run the loop
    game_loop(state, butler=butler)

    con.print(f"\n[dim]Game over. Final Doom: {state.doom}, Turns: {state.turn_number}[/]\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Burnwillow - Terminal Roguelike")
    parser.add_argument("--autopilot", action="store_true",
                        help="Full AI autopilot mode (all characters AI-controlled)")
    parser.add_argument("--companion", action="store_true",
                        help="Companion mode (AI partner joins your party)")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Autopilot action delay in seconds (default: 1.5)")
    parser.add_argument("--companion-name", type=str, default=None,
                        help="Name for the AI companion")
    parser.add_argument("--seed", type=int, default=None,
                        help="Dungeon seed for deterministic generation")
    cli_args = parser.parse_args()
    main(
        autopilot=cli_args.autopilot,
        companion=cli_args.companion,
        autopilot_delay=cli_args.delay,
        companion_name=cli_args.companion_name,
        cli_seed=cli_args.seed,
    )

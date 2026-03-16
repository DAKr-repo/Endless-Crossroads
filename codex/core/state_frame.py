"""
codex/core/state_frame.py - StateFrame Data Contract
=====================================================

Frozen dataclass capturing a complete game snapshot after every command.
Both the DM View (terminal) and Player View (external monitor / Discord / Telegram)
consume this same structure.

Builder function extracts data from any engine via duck-typing.
JSON serialization supports the file-watching Player View viewer.

Also houses the universal GameState enum, state-specific button maps,
help text, lore snippets, and color constants scavenged from the
orphaned codex_ui_manager.py.

Version: 2.0 (WO V27.0)
"""

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, Optional, Tuple, Union, Set


# =============================================================================
# UNIVERSAL GAME STATES (scavenged from codex_ui_manager.py)
# =============================================================================

class GameState(Enum):
    """Universal game states shared across all UI channels."""
    BOOT = auto()
    MAIN_MENU = auto()
    GAMEPLAY = auto()
    INVENTORY = auto()
    COMBAT = auto()
    DIALOGUE = auto()
    MAP = auto()
    CHARACTER = auto()
    SETTINGS = auto()
    HELP = auto()
    LOADING = auto()
    JOURNAL = auto()


# Color scheme — Fantasy RPG (Terminal)
GOLD = "bold yellow"
CRIMSON = "bold red"
EMERALD = "bold green"
SILVER = "dim white"
ROYAL_BLUE = "bold blue"
PARCHMENT = "wheat1"
MYSTIC = "bold magenta"

# State-specific button mappings
STATE_BUTTONS = {
    GameState.BOOT: [("[C] Continue", "continue"), ("[Q] Quit", "quit")],
    GameState.MAIN_MENU: [
        ("[N] New Campaign", "new"),
        ("[L] Load Game", "load"),
        ("[S] Settings", "settings"),
        ("[Q] Quit", "quit"),
    ],
    GameState.GAMEPLAY: [
        ("[I] Inventory", "inventory"),
        ("[M] Map", "map"),
        ("[J] Journal", "journal"),
        ("[ESC] Menu", "menu"),
    ],
    GameState.INVENTORY: [
        ("[U] Use", "use"),
        ("[D] Drop", "drop"),
        ("[E] Equip", "equip"),
        ("[B] Back", "back"),
    ],
    GameState.COMBAT: [
        ("[A] Attack", "attack"),
        ("[S] Spell", "spell"),
        ("[I] Item", "item"),
        ("[F] Flee", "flee"),
    ],
    GameState.DIALOGUE: [
        ("[1-4] Response", "respond"),
        ("[ESC] End", "end"),
    ],
    GameState.MAP: [
        ("[WASD] Navigate", "navigate"),
        ("[E] Examine", "examine"),
        ("[B] Back", "back"),
    ],
    GameState.CHARACTER: [
        ("[L] Level Up", "levelup"),
        ("[S] Skills", "skills"),
        ("[B] Back", "back"),
    ],
    GameState.SETTINGS: [
        ("[V] Volume", "volume"),
        ("[D] Display", "display"),
        ("[B] Back", "back"),
    ],
    GameState.HELP: [("[B] Back", "back"), ("[?] Index", "index")],
    GameState.LOADING: [],
    GameState.JOURNAL: [
        ("[Q] Quests", "quests"),
        ("[N] Notes", "notes"),
        ("[B] Back", "back"),
    ],
}

# Context-specific help text
HELP_TEXT = {
    GameState.BOOT: (
        "**Welcome, Adventurer!**\n\n"
        "C.O.D.E.X. is initializing its arcane systems.\n"
        "The Cortex monitors thermal homeostasis to ensure\n"
        "stable operation of your Digital Ectotherm."
    ),
    GameState.MAIN_MENU: (
        "**The Crossroads**\n\n"
        "From here, you may embark on a new journey,\n"
        "continue a saved tale, or adjust the ancient\n"
        "runes that govern this realm's behavior."
    ),
    GameState.GAMEPLAY: (
        "**Adventure Awaits**\n\n"
        "You are in active play. The Dungeon Master\n"
        "awaits your commands. Speak naturally, or\n"
        "use slash commands for specific actions."
    ),
    GameState.INVENTORY: (
        "**The Adventurer's Pack**\n\n"
        "Review your possessions here. Items marked\n"
        "with a star are equipped. Weight limits\n"
        "are enforced by the Manifold Guard."
    ),
    GameState.COMBAT: (
        "**Steel and Sorcery**\n\n"
        "Initiative has been rolled. Choose your\n"
        "action wisely. The Architect routes complex\n"
        "moves through the Academy for tactical analysis."
    ),
    GameState.DIALOGUE: (
        "**Words Have Power**\n\n"
        "Choose your responses carefully. NPCs\n"
        "remember your choices. The Manifold Guard\n"
        "ensures narrative consistency."
    ),
    GameState.MAP: (
        "**Cartographer's View**\n\n"
        "Explored areas are revealed. Fog of war\n"
        "conceals the unknown. Points of interest\n"
        "are marked with distinctive sigils."
    ),
    GameState.CHARACTER: (
        "**The Mirror of Self**\n\n"
        "Your abilities, skills, and destiny are\n"
        "recorded here. Level advancement unlocks\n"
        "new capabilities and narrative branches."
    ),
    GameState.SETTINGS: (
        "**The Artificer's Workshop**\n\n"
        "Configure the behavior of C.O.D.E.X.\n"
        "Thermal thresholds, voice settings, and\n"
        "display preferences can be adjusted here."
    ),
    GameState.HELP: (
        "**The Sage's Library**\n\n"
        "You have found the help system. Browse\n"
        "topics using the index, or press Back\n"
        "to return to your previous location."
    ),
    GameState.LOADING: (
        "**Between Worlds**\n\n"
        "The veil between states thins...\n"
        "Reality reassembles itself around you."
    ),
    GameState.JOURNAL: (
        "**The Chronicle**\n\n"
        "Active quests, completed tales, and your\n"
        "personal notes are preserved here. The\n"
        "journal persists across sessions."
    ),
}

# Lore snippets for loading screens
LORE_SNIPPETS = [
    "The Manifold Guard ensures that narrative and state remain in harmony...",
    "Deep in the Cortex, thermal spirits regulate the flow of computation...",
    "The Architect weighs each query, routing thoughts through optimal pathways...",
    "The Reflex whispers quick answers; the Academy ponders the profound...",
    "In the space between commands, the Digital Ectotherm rests and recovers...",
    "The Voice speaks through Piper's throat, giving form to the formless...",
    "Conservation of Identity: what is spoken must not contradict what is known...",
    "The FAISS index remembers all that has been indexed in the Vault...",
    "Homeostasis is the art of balance between power and heat...",
    "Every Discord message passes through the Soul before reaching mortal ears...",
]

# Gameplay tips for loading screens
GAMEPLAY_TIPS = [
    "TIP: Use '!status' to check the Cortex thermal state at any time.",
    "TIP: Complex queries are routed to the Academy if thermal clearance allows.",
    "TIP: The '!think' command forces deep reasoning mode.",
    "TIP: Your game state is validated by the Manifold Guard automatically.",
    "TIP: Use '!dmscreen' in Discord to summon the interactive dashboard.",
    "TIP: Voice channels require the bot to have 'Connect' permissions.",
    "TIP: The Vault stores your indexed PDFs for RAG retrieval.",
    "TIP: Check 'codex_builder.log' if indexing fails silently.",
]


@dataclass(frozen=True)
class StateFrame:
    """Immutable snapshot of game state consumed by all renderers."""

    system_id: str = "unknown"
    turn_number: int = 0

    # Spatial
    current_room_id: int = -1
    player_pos: Optional[Tuple[int, int]] = None
    visited_rooms: FrozenSet[int] = frozenset()
    dungeon_rooms: Tuple = ()  # Tuple of (room_id, room_dict) pairs

    # Current room content
    room_name: str = ""
    room_description: str = ""
    room_tier: int = 1
    enemies: Tuple[dict, ...] = ()
    loot: Tuple[dict, ...] = ()
    furniture: Tuple[dict, ...] = ()
    hazards: Tuple[dict, ...] = ()
    exits: Tuple[dict, ...] = ()

    # DM-only (stripped by PlayerRenderer)
    trap_details: Tuple[dict, ...] = ()
    invisible_enemies: Tuple[dict, ...] = ()

    # Party
    party: Tuple[dict, ...] = ()
    active_character: Optional[str] = None

    # System-specific
    doom: Optional[int] = None
    combat_mode: bool = False
    combat_round: int = 0

    # UI
    sidebar_detail: Optional[str] = None
    last_action: Optional[str] = None
    message_log: Tuple[str, ...] = ()

    # Exploration
    scouted_rooms: FrozenSet[int] = frozenset()
    cleared_rooms: FrozenSet[int] = frozenset()
    searched_rooms: FrozenSet[int] = frozenset()
    rot_hunter: Optional[dict] = None

    # Crossover (WO-V9.0)
    battlefield: Optional[dict] = None  # SaV+BoB crossover status

    # UI State (WO-V27.0)
    game_state: str = "GAMEPLAY"  # String for JSON compat; matches GameState.name


def _rooms_to_tuples(graph) -> Tuple:
    """Convert a DungeonGraph's rooms dict to serializable tuple of (id, dict) pairs."""
    if not graph or not hasattr(graph, 'rooms'):
        return ()
    pairs = []
    for rid, room in graph.rooms.items():
        pairs.append((rid, {
            "x": room.x,
            "y": room.y,
            "width": room.width,
            "height": room.height,
            "connections": list(room.connections),
            "room_type": room.room_type.name if hasattr(room, 'room_type') else "NORMAL",
            "tier": getattr(room, 'tier', 1),
            "is_locked": getattr(room, 'is_locked', False),
        }))
    return tuple(pairs)


def _party_to_dicts(party_list) -> Tuple[dict, ...]:
    """Convert a list of Character objects to serializable dicts."""
    result = []
    for char in party_list:
        result.append({
            "name": getattr(char, 'name', 'Unknown'),
            "hp": getattr(char, 'current_hp', 0),
            "max_hp": getattr(char, 'max_hp', 0),
            "alive": char.is_alive() if hasattr(char, 'is_alive') else True,
            "is_minion": hasattr(char, 'rounds_remaining'),
        })
    return tuple(result)


def build_state_frame(engine, game_state=None, system_id="unknown",
                      turn_number=0) -> StateFrame:
    """Build a StateFrame from an engine and optional game_state.

    Args:
        engine: Any game engine (BurnwillowEngine, DnD5eEngine, etc.)
        game_state: Terminal GameState object (play_burnwillow.py). None for bridge mode.
        system_id: System identifier string.
        turn_number: Current turn number.

    Returns:
        Frozen StateFrame snapshot.
    """
    # Current room info — WO-V57.0: prefer dict getter for dict callers
    room_data = {}
    if hasattr(engine, 'get_current_room'):
        _room_getter = getattr(engine, 'get_current_room_dict', engine.get_current_room)
        room_data = _room_getter() or {}

    current_room_id = getattr(engine, 'current_room_id', -1) or -1

    # Room content from populated_rooms
    pop = None
    if hasattr(engine, 'populated_rooms'):
        pop = engine.populated_rooms.get(current_room_id)
    content = pop.content if pop else {}

    # Enemies / loot from game_state (terminal) or engine content
    if game_state:
        enemies = tuple(game_state.room_enemies.get(current_room_id, []))
        loot = tuple(game_state.room_loot.get(current_room_id, []))
        furniture = tuple(game_state.room_furniture.get(current_room_id, []))
    else:
        enemies = tuple(content.get("enemies", []))
        loot = tuple(content.get("loot", []))
        furniture = ()

    hazards = tuple(content.get("hazards", []))

    # Exits
    exits_raw = []
    if hasattr(engine, 'get_cardinal_exits'):
        for ex in engine.get_cardinal_exits():
            exits_raw.append({
                "direction": ex.get("direction", "?"),
                "id": ex.get("id", -1),
                "type": ex.get("type", "normal"),
                "tier": ex.get("tier", 1),
                "is_locked": ex.get("is_locked", False),
                "visited": ex.get("id", -1) in getattr(engine, 'visited_rooms', set()),
            })
    elif hasattr(engine, 'get_connected_rooms'):
        for c in engine.get_connected_rooms():
            exits_raw.append({
                "direction": str(c.get("id", "?")),
                "id": c.get("id", -1),
                "type": c.get("type", "normal"),
                "tier": c.get("tier", 1),
                "is_locked": c.get("is_locked", False),
                "visited": c.get("visited", False),
            })
    exits = tuple(exits_raw)

    # Party
    party_list = getattr(engine, 'party', [])
    if not party_list:
        char = getattr(engine, 'character', None)
        if char:
            party_list = [char]
    party = _party_to_dicts(party_list)

    # Active character
    active_char_name = None
    if game_state and hasattr(game_state, 'active_character') and game_state.active_character:
        active_char_name = game_state.active_character.name
    elif hasattr(engine, 'character') and engine.character:
        active_char_name = engine.character.name

    # Doom
    doom = None
    if hasattr(engine, 'doom_clock'):
        doom = engine.doom_clock.current

    # Room name/desc
    room_name = ""
    room_description = ""
    room_tier = 1
    if isinstance(room_data, dict):
        room_name = room_data.get("type", "Unknown").capitalize()
        room_description = room_data.get("description", "")
        room_tier = room_data.get("tier", 1)
    elif hasattr(room_data, 'room_type'):
        room_name = room_data.room_type.name if hasattr(room_data.room_type, 'name') else str(room_data.room_type)
        room_description = getattr(room_data, 'description', "")
        room_tier = getattr(room_data, 'tier', 1)

    # Game state fields
    combat_mode = False
    combat_round = 0
    sidebar_detail = None
    last_action = None
    message_log = ()
    scouted_rooms = frozenset()
    cleared_rooms = frozenset()
    searched_rooms = frozenset()
    rot_hunter = None

    if game_state:
        combat_mode = getattr(game_state, 'combat_mode', False)
        combat_round = getattr(game_state, 'combat_round', 0)
        sidebar_detail = getattr(game_state, 'sidebar_detail', None)
        last_action = getattr(game_state, 'last_action_result', None)
        message_log = tuple(getattr(game_state, 'message_log', []))
        scouted_rooms = frozenset(getattr(game_state, 'scouted_rooms', set()))
        cleared_rooms = frozenset(getattr(game_state, 'cleared_rooms', set()))
        searched_rooms = frozenset(getattr(game_state, 'searched_rooms', set()))
        rot_hunter = getattr(game_state, 'rot_hunter', None)

    return StateFrame(
        system_id=system_id,
        turn_number=turn_number,
        current_room_id=current_room_id,
        player_pos=getattr(engine, 'player_pos', None),
        visited_rooms=frozenset(getattr(engine, 'visited_rooms', set())),
        dungeon_rooms=_rooms_to_tuples(getattr(engine, 'dungeon_graph', None)),
        room_name=room_name,
        room_description=room_description,
        room_tier=room_tier,
        enemies=enemies,
        loot=loot,
        furniture=furniture,
        hazards=hazards,
        exits=exits,
        trap_details=tuple(content.get("traps", [])),
        invisible_enemies=(),
        party=party,
        active_character=active_char_name,
        doom=doom,
        combat_mode=combat_mode,
        combat_round=combat_round,
        sidebar_detail=sidebar_detail,
        last_action=last_action,
        message_log=message_log,
        scouted_rooms=scouted_rooms,
        cleared_rooms=cleared_rooms,
        searched_rooms=searched_rooms,
        rot_hunter=rot_hunter,
    )


# ─── JSON Serialization ───────────────────────────────────────────────────────

def frame_to_json(frame: StateFrame) -> str:
    """Serialize a StateFrame to JSON string."""
    d = {}
    d["system_id"] = frame.system_id
    d["turn_number"] = frame.turn_number
    d["current_room_id"] = frame.current_room_id
    d["player_pos"] = list(frame.player_pos) if frame.player_pos else None
    d["visited_rooms"] = sorted(frame.visited_rooms)
    d["dungeon_rooms"] = [[rid, rdata] for rid, rdata in frame.dungeon_rooms]
    d["room_name"] = frame.room_name
    d["room_description"] = frame.room_description
    d["room_tier"] = frame.room_tier
    d["enemies"] = list(frame.enemies)
    d["loot"] = list(frame.loot)
    d["furniture"] = list(frame.furniture)
    d["hazards"] = list(frame.hazards)
    d["exits"] = list(frame.exits)
    d["trap_details"] = list(frame.trap_details)
    d["invisible_enemies"] = list(frame.invisible_enemies)
    d["party"] = list(frame.party)
    d["active_character"] = frame.active_character
    d["doom"] = frame.doom
    d["combat_mode"] = frame.combat_mode
    d["combat_round"] = frame.combat_round
    d["sidebar_detail"] = frame.sidebar_detail
    d["last_action"] = frame.last_action
    d["message_log"] = list(frame.message_log)
    d["scouted_rooms"] = sorted(frame.scouted_rooms)
    d["cleared_rooms"] = sorted(frame.cleared_rooms)
    d["searched_rooms"] = sorted(frame.searched_rooms)
    d["rot_hunter"] = frame.rot_hunter
    d["battlefield"] = frame.battlefield
    d["game_state"] = frame.game_state
    return json.dumps(d, separators=(",", ":"))


def frame_from_json(data: str) -> StateFrame:
    """Deserialize a StateFrame from JSON string."""
    d = json.loads(data)
    return StateFrame(
        system_id=d.get("system_id", "unknown"),
        turn_number=d.get("turn_number", 0),
        current_room_id=d.get("current_room_id", -1),
        player_pos=tuple(d["player_pos"]) if d.get("player_pos") else None,
        visited_rooms=frozenset(d.get("visited_rooms", [])),
        dungeon_rooms=tuple(
            (pair[0], pair[1]) for pair in d.get("dungeon_rooms", [])
        ),
        room_name=d.get("room_name", ""),
        room_description=d.get("room_description", ""),
        room_tier=d.get("room_tier", 1),
        enemies=tuple(d.get("enemies", [])),
        loot=tuple(d.get("loot", [])),
        furniture=tuple(d.get("furniture", [])),
        hazards=tuple(d.get("hazards", [])),
        exits=tuple(d.get("exits", [])),
        trap_details=tuple(d.get("trap_details", [])),
        invisible_enemies=tuple(d.get("invisible_enemies", [])),
        party=tuple(d.get("party", [])),
        active_character=d.get("active_character"),
        doom=d.get("doom"),
        combat_mode=d.get("combat_mode", False),
        combat_round=d.get("combat_round", 0),
        sidebar_detail=d.get("sidebar_detail"),
        last_action=d.get("last_action"),
        message_log=tuple(d.get("message_log", [])),
        scouted_rooms=frozenset(d.get("scouted_rooms", [])),
        cleared_rooms=frozenset(d.get("cleared_rooms", [])),
        searched_rooms=frozenset(d.get("searched_rooms", [])),
        rot_hunter=d.get("rot_hunter"),
        battlefield=d.get("battlefield"),
        game_state=d.get("game_state", "GAMEPLAY"),
    )

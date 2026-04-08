#!/usr/bin/env python3
"""
codex_burnwillow_bridge.py - Text Mode Adapter for Burnwillow
=============================================================

Pure string-in/string-out adapter for BurnwillowEngine.
Designed for Discord/Telegram chat interfaces.

- No input() calls
- No Rich imports
- ASCII mini-map (graph topology, 7x7, mobile-safe)
- All state lives on self.engine

Version: 1.0
"""

import json
import random
from pathlib import Path

from codex.games.burnwillow.engine import (
    BurnwillowEngine, BurnwillowTraitResolver,
    Character, StatType, GearSlot, DC, Condition,
    roll_dice_pool, passive_check, NAMED_LEGENDARY_ABILITIES
)
from codex.spatial.map_engine import RoomType
from codex.core.state_frame import StateFrame, build_state_frame
from codex.core.services.trait_handler import TraitHandler
from codex.core.mechanics.rest import RestManager
from codex.spatial.map_renderer import render_mini_map, rooms_to_minimap_dict

_SAVES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "saves"


# =============================================================================
# COMMAND REGISTRY
# =============================================================================

COMMANDS = {
    "look":      ["l"],
    "move":      ["go", "m"],
    "map":       [],
    "attack":    ["fight", "a"],
    "intercept": ["int", "defend"],
    "command":   ["cmd", "order"],
    "bolster":   ["buff", "empower"],
    "triage":    ["medic", "firstaid"],
    "assist":    ["help_ally", "aid"],
    "search":    ["s"],
    "loot":      [],
    "drop":      [],
    "use":       ["activate"],
    "push":      ["shove"],
    "rest":      ["heal"],
    "stats":     ["st"],
    "inventory": ["inv", "i"],
    "save":      [],
    "talk":      ["npc"],
    "recap":     [],
    "reputation": ["rep", "factions"],
    "ingredients": ["ing"],
    "craft":     ["brew", "make"],
    "recipes":   [],
    "enter":     ["cross", "portal"],
    "forge":     ["station", "workshop"],
    "salvage":   ["scrap"],
    "temper":    [],
    "reforge":   [],
    "enchant":   [],
    "heal":      ["honey"],
    "reinforce": [],
    "process":   ["rot_process"],
    "graft":     [],
    "curse":     ["curse_weapon"],
    "threadbind": ["bind"],
    "decompose": ["decomp"],
    "infuse":    ["spore_infuse"],
    "netgraft":  ["network_graft"],
    "deposit":   ["store"],
    "retrieve":  ["withdraw"],
    "claim":     [],
    "help":      ["h", "?"],
    "tutorial":  ["tut"],
}

# 8-way grid movement directions (handled separately from COMMANDS)
_GRID_DIRS = {
    "n": "n", "north": "n",
    "s": "s", "south": "s",
    "e": "e", "east": "e",
    "w": "w", "west": "w",
    "ne": "ne", "northeast": "ne",
    "nw": "nw", "northwest": "nw",
    "se": "se", "southeast": "se",
    "sw": "sw", "southwest": "sw",
}

# Build reverse lookup: alias -> canonical
ALIAS_MAP: dict[str, str] = {}
for cmd, aliases in COMMANDS.items():
    ALIAS_MAP[cmd] = cmd
    for alias in aliases:
        ALIAS_MAP[alias] = cmd


# =============================================================================
# BRIDGE CLASS
# =============================================================================

class BurnwillowBridge:
    """Text-mode adapter for Burnwillow on Discord/Telegram."""

    # Categorized command descriptions for Discord/Telegram UI
    COMMAND_CATEGORIES = {
        "navigation": {
            "move": "Move to a connected room by ID",
            "n/s/e/w": "Grid movement (cardinal)",
            "ne/nw/se/sw": "Grid movement (diagonal)",
            "look": "Describe current room",
            "map": "Show dungeon mini-map",
        },
        "combat": {
            "attack": "Fight the first enemy",
            "intercept": "Defend an ally (requires shield with [Intercept])",
            "command": "Order an ally to act (requires banner/horn with [Command])",
            "bolster": "Empower an ally's next roll (requires totem with [Bolster])",
            "triage": "Heal with Wits check (requires med-kit with [Triage])",
            "assist": "Help an ally's next check (+1d6 to their pool, max 5d6)",
            "rest": "Rest: 'rest short' (50% HP, +1 Doom) or 'rest long' (full, +3 Doom)",
        },
        "interaction": {
            "talk": "Talk to an NPC (type freely to chat, 'bye' to end)",
        },
        "exploration": {
            "search": "Search for loot (+1 Doom)",
            "loot": "Pick up items",
            "drop": "Drop an item",
            "use": "Use an item's special trait",
            "push": "Push furniture in a direction",
            "inventory": "Show your gear and items",
            "stats": "Show character stats",
            "save": "Save current game",
            "reputation": "Show faction standings (aliases: rep, factions)",
            "ingredients": "Show gathered alchemy ingredients",
            "craft": "Craft a recipe: craft <recipe name>",
            "recipes": "Show known alchemy recipes",
            "enter": "Enter a discovered hidden passage (enter heartwood / enter undergrove)",
            "forge": "Show available crafting station actions",
            "salvage": "Break an item into materials: salvage <item name>",
            "temper": "Add +1 DR to armor: temper <item name>",
            "reforge": "Change item slot: reforge <item name> <new slot>",
            "enchant": "Add Aether affix to armor: enchant <item name>",
            "heal": "Hive honey healing (costs 5 amber, requires Hive Friendly)",
            "reinforce": "Dam-Wright reinforcement: reinforce <item> (requires Dam-Wright Friendly)",
            "process": "Hag Rot processing: convert Rot Spores (requires Hag Circle Friendly)",
            "graft": "Heartwood grafting: graft <item> — fuse permanently, +1 tier (Heartwood Allied)",
            "curse": "Hag curse weapon: curse <item> — apply debuff prefix (Hag Circle Friendly)",
            "threadbind": "Canopy thread binding: threadbind <item1> <item2> <set> (Canopy Court Allied)",
            "decompose": "Mycelium decomposition: decompose <item> — better yield (Mycelium Friendly)",
            "infuse": "Mycelium spore infusion: infuse <item> — add living quality (Mycelium Allied)",
            "netgraft": "Mycelium network graft: netgraft <item> — survives death (Mycelium Exalted)",
            "deposit": "Deposit an item in the Still Pool (2 max, Willow Wood only)",
            "retrieve": "Retrieve an item from the Still Pool (costs 1 Doom)",
            "claim": "Claim a cleared vault as an outpost: claim <type>",
            "recap": "Session recap (kills, loot, rooms)",
            "help": "List all commands",
            "tutorial": "Open interactive tutorial",
        },
    }

    def __init__(self, player_name: str = "Adventurer", seed: int | None = None,
                 broadcast_manager=None, char_data: dict | None = None):
        self.engine = BurnwillowEngine()

        # Create character — use pre-rolled stats if provided, else random
        if char_data and "stats" in char_data:
            stats = char_data["stats"]
            self.engine.create_character_with_stats(
                player_name,
                might=stats.get("Might", 10),
                wits=stats.get("Wits", 10),
                grit=stats.get("Grit", 10),
                aether=stats.get("Aether", 10),
            )
        else:
            self.engine.create_character(player_name)

        self.dead = False
        self._last_trait_used: str = ""  # For trait combo detection
        self._sun_cleaver_kills: int = 0  # Ember Momentum stacking damage
        self._last_stand_used: bool = False  # Warden's Bastion once per combat
        self._sunder_used: bool = False  # Worldbreaker once per floor
        self._tree_speaks_used: bool = False  # Ring of the Burnwillow once per floor
        self._storm_surge_pending: int = 0  # Tempest Annihilator +score after Tempest
        self._snared_enemies: set = set()  # Enemies with defense reduced by SNARE
        self._blinded_enemies: set = set()  # Enemies blinded by FLASH
        self._snare_reduction: int = 0      # Defense reduction value from last SNARE
        self._guard_dr_remaining: int = 0   # [Guard] self-DR until next turn
        self._reflect_pending: int = 0      # [Reflect] damage returned on next hit taken
        self._pending_bonus_damage: int = 0  # [Charge] bonus damage on next attack
        self._first_attack_in_room: bool = True  # Shadowweave 4pc tracking
        self.last_frame: StateFrame | None = None
        self._broadcast = broadcast_manager
        # Universal Narrative Bridge
        self._narrator = None
        try:
            from codex.core.services.narrative_bridge import NarrativeBridge
            self._narrator = NarrativeBridge("burnwillow", seed=seed)
        except Exception:
            pass

        # WO-V37.0: Session chronicle log (mirrors play_burnwillow GameState.session_log)
        self._session_log: list[dict] = []
        self._rooms_visited: set[int] = set()

        # NPC conversation state
        self._talking_to: str | None = None
        self._talking_to_npc: dict | None = None

        # WO-V35.0: RestManager for short/long rest dispatch
        self._rest_mgr = RestManager()

        # Wire trait system
        self._trait_handler = TraitHandler(broadcast_manager=broadcast_manager)
        self._trait_handler.register_resolver("burnwillow", BurnwillowTraitResolver())

        # Equip loadout-specific starter gear
        loadout = "sellsword"
        if char_data:
            loadout = char_data.get("loadout", char_data.get("archetype", "sellsword"))
        self.engine.equip_loadout(loadout)

        # Generate dungeon (depth=3 for smaller map)
        self.engine.generate_dungeon(depth=3, seed=seed)

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

    def step(self, command: str) -> str:
        """Process one command, return formatted result string."""
        if self.dead:
            return "You are dead. Start a new session."

        parts = command.strip().split(None, 1)
        if not parts:
            result = self._cmd_look()
            self._emit_frame()
            return result

        verb = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        # 8-way grid movement — auto-exit conversation on move
        grid_dir = _GRID_DIRS.get(verb)
        if grid_dir is not None:
            if self._talking_to:
                self._talking_to = None
                self._talking_to_npc = None
            result = self._cmd_grid_move(grid_dir)
            self._emit_frame()
            return result

        # Conversation mode: bye exits, other input routes to NPC dialogue
        if self._talking_to:
            if verb in ("bye", "leave", "goodbye"):
                name = self._talking_to
                self._talking_to = None
                self._talking_to_npc = None
                result = f"You end your conversation with {name}.\n{self._status_line()}"
                self._emit_frame()
                return result
            # Don't intercept system commands — let them fall through
            if verb not in ALIAS_MAP:
                result = self._cmd_npc_dialogue(command.strip())
                self._emit_frame()
                return result

        canonical = ALIAS_MAP.get(verb)
        if canonical is None:
            result = self._cmd_look()
            self._emit_frame()
            return result

        # Auto-exit conversation on room movement
        if canonical == "move" and self._talking_to:
            self._talking_to = None
            self._talking_to_npc = None

        dispatch = {
            "look":      lambda: self._cmd_look(),
            "move":      lambda: self._cmd_move(arg),
            "map":       lambda: self._cmd_map(),
            "attack":    lambda: self._cmd_attack(),
            "intercept": lambda: self._cmd_intercept(),
            "command":   lambda: self._cmd_command(arg),
            "bolster":   lambda: self._cmd_bolster(arg),
            "triage":    lambda: self._cmd_triage(arg),
            "assist":    lambda: self._cmd_assist(arg),
            "search":    lambda: self._cmd_search(),
            "loot":      lambda: self._cmd_loot(),
            "drop":      lambda: self._cmd_drop(arg),
            "use":       lambda: self._cmd_use(arg),
            "push":      lambda: self._cmd_push(arg),
            "rest":      lambda: self._cmd_rest(arg),
            "stats":     lambda: self._cmd_stats(),
            "inventory": lambda: self._cmd_inventory(),
            "save":      lambda: self._cmd_save(),
            "talk":      lambda: self._cmd_talk(arg),
            "recap":     lambda: self._cmd_recap(),
            "reputation": lambda: self._cmd_reputation(),
            "ingredients": lambda: self._cmd_ingredients(),
            "craft":     lambda: self._cmd_craft(arg),
            "recipes":   lambda: self._cmd_recipes(),
            "enter":     lambda: self._cmd_enter(arg),
            "forge":     lambda: self._cmd_forge(),
            "salvage":   lambda: self._cmd_salvage(arg),
            "temper":    lambda: self._cmd_temper(arg),
            "reforge":   lambda: self._cmd_reforge(arg),
            "enchant":   lambda: self._cmd_enchant(arg),
            "heal":      lambda: self._cmd_heal(),
            "reinforce": lambda: self._cmd_reinforce(arg),
            "process":   lambda: self._cmd_process(),
            "graft":     lambda: self._cmd_graft(arg),
            "curse":     lambda: self._cmd_curse(arg),
            "threadbind": lambda: self._cmd_threadbind(arg),
            "decompose": lambda: self._cmd_decompose(arg),
            "infuse":    lambda: self._cmd_infuse(arg),
            "netgraft":  lambda: self._cmd_netgraft(arg),
            "deposit":   lambda: self._cmd_deposit(arg),
            "retrieve":  lambda: self._cmd_retrieve(arg),
            "claim":     lambda: self._cmd_claim(arg),
            "help":      lambda: self._cmd_help(),
            "tutorial":  lambda: self._cmd_tutorial(),
        }

        result = dispatch[canonical]()
        self._emit_frame()
        return result

    def _emit_frame(self):
        """Cache a StateFrame snapshot after each step and broadcast update."""
        try:
            self.last_frame = build_state_frame(
                engine=self.engine,
                system_id="burnwillow",
            )
        except Exception:
            pass

        # Broadcast MAP_UPDATE for cross-interface sync
        if self._broadcast and self.last_frame:
            try:
                self._broadcast.broadcast(
                    "MAP_UPDATE",
                    {
                        "system_id": "burnwillow",
                        "room_id": self.engine.current_room_id,
                        "doom": self.engine.doom_clock.current,
                    },
                )
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────
    # COMMAND HANDLERS
    # ─────────────────────────────────────────────────────────────────────

    def _cmd_look(self) -> str:
        """Describe current room."""
        room = self.engine.get_current_room()
        if not room:
            return "ERROR: No dungeon loaded."

        # Spawn NPC on first visit if room has none
        if self._narrator and not room.get("npcs"):
            _npc = self._narrator.spawn_npc_for_room(
                room["id"], tier=room.get("tier", 1))
            if _npc:
                room.setdefault("npcs", []).append(_npc)
                # Persist to engine
                pop_room = self.engine.populated_rooms.get(
                    self.engine.current_room_id)
                if pop_room:
                    pop_room.content.setdefault("npcs", []).append(_npc)

        lines = []
        lines.append(f"=== Room {room['id']} ({room['type'].upper()}) ===")
        _desc = room["description"]
        if self._narrator:
            # Try Mimir-enhanced narration first, fall back to static enrichment
            _mimir_fn = None
            try:
                from codex.core.cortex import get_cortex
                _ctx = get_cortex()
                if _ctx.get_thermal_state().status != "RED":
                    from codex.integrations.mimir import query_mimir
                    _mimir_fn = query_mimir
            except Exception:
                pass
            if _mimir_fn:
                _enemies = [e.get("name", "") for e in room.get("enemies", []) if isinstance(e, dict)]
                _loot = [l.get("name", "") for l in room.get("loot", []) if isinstance(l, dict)]
                _doom = getattr(self.engine, 'doom_clock', None)
                _doom_val = getattr(_doom, 'current', 0) if _doom else 0
                _desc = self._narrator.enrich_room_mimir(
                    _desc, room.get("tier", 1),
                    enemies=_enemies, loot=_loot, doom=_doom_val,
                    mimir_fn=_mimir_fn,
                )
            else:
                _doom = getattr(self.engine, 'doom_clock', None)
                _doom_val = getattr(_doom, 'current', 0) if _doom else 0
                _desc = self._narrator.enrich_room(_desc, room.get("tier", 1), doom=_doom_val)
        lines.append(_desc)

        # Enemies
        enemies = room.get("enemies", [])
        if enemies:
            lines.append("")
            lines.append(f"ENEMIES ({len(enemies)}):")
            for e in enemies:
                if isinstance(e, dict):
                    name = e.get("name", "Unknown")
                    hp = e.get("hp", "?")
                    lines.append(f"  * {name} (HP: {hp})")
                    if self._narrator:
                        _eflav = self._narrator.describe_enemy(name)
                        if _eflav:
                            _etext = _eflav.lstrip(" \u2014")
                            lines.append(f"    {_etext}")
                else:
                    lines.append(f"  * {e}")

        # Loot
        loot = room.get("loot", [])
        if loot:
            lines.append("")
            lines.append(f"LOOT ({len(loot)}):")
            for item in loot:
                if isinstance(item, dict):
                    lines.append(f"  * {item.get('name', str(item))}")
                else:
                    lines.append(f"  * {item}")

        # Hazards
        hazards = room.get("hazards", [])
        if hazards:
            lines.append("")
            lines.append("HAZARDS:")
            for h in hazards:
                if isinstance(h, dict):
                    _hname = h.get('name', str(h))
                    lines.append(f"  ! {_hname}")
                    if self._narrator:
                        _hflav = self._narrator.describe_hazard(_hname)
                        if _hflav:
                            _htext = _hflav.lstrip(" \u2014")
                            lines.append(f"    {_htext}")
                else:
                    lines.append(f"  ! {h}")

        # NPCs
        npcs = room.get("npcs", [])
        if npcs:
            lines.append("")
            lines.append(f"NPCS ({len(npcs)}):")
            for npc in npcs:
                if isinstance(npc, dict):
                    name = npc.get("name", "Unknown")
                    role = npc.get("npc_type", npc.get("role", ""))
                    role_str = f" ({role})" if role else ""
                    lines.append(f"  @ {name}{role_str}")
                else:
                    lines.append(f"  @ {npc}")

        # Furniture
        furniture = room.get("furniture", [])
        if furniture:
            lines.append("")
            lines.append("FURNITURE:")
            for f in furniture:
                if isinstance(f, dict):
                    lines.append(f"  # {f.get('name', str(f))}")
                else:
                    lines.append(f"  # {f}")

        # Exits
        connected = self.engine.get_connected_rooms()
        if connected:
            lines.append("")
            lines.append("EXITS:")
            for c in connected:
                tag = c["type"].upper()
                extra = ""
                if c["is_locked"]:
                    extra = " [LOCKED]"
                elif c["visited"]:
                    extra = " [VISITED]"
                lines.append(f"  [{c['id']}] {tag}{extra}")

        lines.append("")
        lines.append(self._status_line())
        lines.append(self._render_minimap())

        return "\n".join(lines)

    def _on_room_entered(self) -> list[str]:
        """Shared room-entry effects. Called by _cmd_move and grid_move exit."""
        lines = []
        char = self.engine.character

        # Vault Breach Alert: boosted spawns during echo
        vault_echo_active = self.engine.tick_vault_echo()
        if vault_echo_active:
            lines.append("The acoustic echo draws enemies toward you! (+1 enemy)")

        # Reset per-combat state on room entry
        self._sun_cleaver_kills = 0
        self._last_stand_used = False
        self._guard_dr_remaining = 0
        self._reflect_pending = 0
        self._last_trait_used = ""
        self._snared_enemies.clear()
        self._blinded_enemies.clear()
        self._snare_reduction = 0
        self._first_attack_in_room = True  # Shadowweave 4pc: first attack crits
        self._rootcatch_used = False       # Rootcatch: once per encounter

        # Room lighting: decrement [Light] duration, check darkness
        pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
        _is_dark = getattr(pop_room, 'is_dark', False) if pop_room else False
        if self.engine._light_remaining > 0:
            self.engine._light_remaining -= 1
            if _is_dark:
                if pop_room:
                    pop_room.is_dark = False
                if self.engine._light_remaining > 0:
                    lines.append(f"Your light holds back the dark. ({self.engine._light_remaining} rooms remaining)")
                else:
                    lines.append("Your light flickers and fades.")
        elif _is_dark:
            lines.append("This room is shrouded in darkness. (-1d6 to all checks)")

        # Named Legendary: Eternity Bloom — party immune to Blighted
        eternity_bloom_active = False
        for ally in self.engine.party:
            if ally.is_alive():
                for _sl, _it in ally.gear.slots.items():
                    if _it and _it.name == "Eternity Bloom":
                        eternity_bloom_active = True
                        break
                if eternity_bloom_active:
                    break
        if eternity_bloom_active and char.has_condition(Condition.BLIGHTED):
            char.remove_condition(Condition.BLIGHTED)
            lines.append("The Eternity Bloom's aura absorbs the Blight.")

        # Blighted condition: 1 HP per room (Willow suffix resists)
        if char.has_condition(Condition.BLIGHTED):
            willow_resist = False
            for _item in char.gear.slots.values():
                if _item and _item.suffix == "of the Willow":
                    willow_resist = True
                    break
            if willow_resist:
                lines.append("Willow's protection absorbs the Blight.")
            else:
                char.current_hp = max(0, char.current_hp - 1)
                lines.append(f"The Blight eats at you. (-1 HP, now {char.current_hp}/{char.max_hp})")

        # Affix: Mending — heal 1 HP on room entry
        for _item in char.gear.slots.values():
            if _item and _item.suffix == "of Mending":
                healed = char.heal(1)
                if healed > 0:
                    lines.append("Mending aura restores 1 HP.")
                break

        # Ingredient drops (30% chance per room)
        from codex.games.burnwillow.engine import roll_ingredient_drop
        zone = getattr(self.engine, '_zone', 1)
        ingredient = roll_ingredient_drop(zone)
        if ingredient:
            char.ingredients[ingredient] = char.ingredients.get(ingredient, 0) + 1
            lines.append(f"You find {ingredient}. ({char.ingredients[ingredient]} total)")

        # Choir Resonance Exposure — builds in Zone 4+
        zone = getattr(self.engine, '_zone', 1)
        if zone >= 4:
            self.engine.resonance_exposure += 1
            if (self.engine.resonance_exposure >= self.engine.resonance_threshold
                    and not char.has_condition(Condition.RESONANCE_TOUCHED)):
                char.add_condition(Condition.RESONANCE_TOUCHED)
                lines.append("The Choir's song seeps into your gear. Your equipment hums sympathetically.")
                lines.append(f"  You are now Resonance-Touched.")
            elif self.engine.resonance_exposure >= 3 and not char.has_condition(Condition.RESONANCE_TOUCHED):
                lines.append("The diminished intervals press against your skull. The wood vibrates wrong.")
        elif zone <= 3 and self.engine.resonance_exposure > 0:
            self.engine.resonance_exposure = 0  # Reset on return to safer zones

        # Quest trigger: room entered
        if hasattr(self.engine, '_quest_dispatcher') and self.engine._quest_dispatcher:
            room_data = self.engine.get_current_room()
            if room_data:
                quest_msgs = self.engine._quest_dispatcher.on_room_entered(room_data.get("tier", 1))
                for qm in quest_msgs:
                    lines.append(f"[Quest] {qm}")
                # Show quest markers
                if room_data.get("quest_marker"):
                    lines.append(f"[Quest] {room_data['quest_marker']}")

        # Active conditions summary
        active = char.get_active_conditions()
        if active:
            lines.append(f"Conditions: {', '.join(active)}")

        return lines

    def _cmd_grid_move(self, direction: str) -> str:
        """Move one tile in the given direction on the spatial grid.

        Handles bump-to-exit (door detection) and bump-to-action (enemy/furniture).
        """
        result = self.engine.move_player_grid(direction)

        if not result["success"]:
            # Wall bump — check for room exit in this direction
            if result.get("bump_pos"):
                exit_info = self._find_exit_in_dir(direction)
                if exit_info and not exit_info.get("is_locked"):
                    move_result = self.engine.move_to_room(exit_info["id"])
                    if move_result["success"]:
                        entry_effects = self._on_room_entered()
                        look = self._cmd_look()
                        if entry_effects:
                            return "\n".join(entry_effects) + "\n" + look
                        return look
                    return move_result["message"] + "\n" + self._status_line()
                elif exit_info and exit_info.get("is_locked"):
                    return f"The way {direction.upper()} is locked.\n" + self._status_line()
            return result["message"] + "\n" + self._status_line()

        # Door-snap exit
        if result.get("door_exit") is not None:
            move_result = self.engine.move_to_room(result["door_exit"])
            if move_result["success"]:
                entry_effects = self._on_room_entered()
                look = self._cmd_look()
                if entry_effects:
                    return "\n".join(entry_effects) + "\n" + look
                return look
            return move_result["message"] + "\n" + self._status_line()

        return result["message"] + "\n" + self._status_line()

    def _find_exit_in_dir(self, direction: str) -> dict | None:
        """Find a room exit matching the given 8-way direction."""
        _short_to_long = {
            "n": "N", "s": "S", "e": "E", "w": "W",
            "ne": "NE", "nw": "NW", "se": "SE", "sw": "SW",
        }
        target = _short_to_long.get(direction.lower(), direction.upper())
        for ex in self.engine.get_cardinal_exits():
            if ex["direction"] == target:
                return ex
        return None

    def _cmd_move(self, arg: str) -> str:
        """Move to a connected room by ID."""
        arg = arg.strip()
        if not arg:
            return "Move where? Usage: move <room_id>\n" + self._status_line()

        try:
            target_id = int(arg)
        except ValueError:
            return f"Invalid room ID: {arg}\n" + self._status_line()

        result = self.engine.move_to_room(target_id)

        if not result["success"]:
            return result["message"] + "\n" + self._status_line()

        # WO-V37.0: Log room entered
        self._log_event("room_entered", room_id=target_id)
        self._loom_shard(f"Explored room {target_id}")  # WO-V79.0

        # Successful move — process on-room-entry effects
        room = result.get("room", {})
        enemies = room.get("enemies", [])
        lines = [result["message"]]
        char = self.engine.character

        # Shared room-entry effects (vault echo, Blight tick, conditions)
        lines.extend(self._on_room_entered())

        # Check for Blight death
        if char.current_hp <= 0:
            lines.append(f"{char.name} succumbs to the Blight...")
            if self.engine.check_tpk():
                lines.append("")
                lines.append("THE BURNWILLOW FALLS.")
            return "\n".join(lines)

        # Hidden portal detection
        room_data = self.engine.get_current_room()
        if room_data and room_data.get("portal_destination"):
            dest = room_data["portal_destination"]
            self.engine._discovered_entrances.add(dest)
            lines.append("")
            lines.append(f"[bold cyan]A hidden passage to the {dest.title()} lies before you.[/bold cyan]")
            lines.append(f"  Type 'enter {dest}' to cross the threshold.")

        # Ambush check — Named Legendary: Flashfire Crown = always first
        if enemies:
            has_flashfire = False
            for _sl, _it in char.gear.slots.items():
                if _it and _it.name == "Flashfire Crown":
                    has_flashfire = True
                    break
            if has_flashfire:
                lines.append("Flashfire Crown crackles! You act first. (Cannot be ambushed)")
            else:
                wits_mod = char.get_stat_mod(StatType.WITS)
                ambush = roll_dice_pool(1, wits_mod, DC.STANDARD.value)
                if ambush["success"]:
                    lines.append("You catch them off guard! (Ambush round)")
                else:
                    lines.append("Enemies spotted! Combat imminent.")

        lines.append("")
        lines.append(self._status_line())
        lines.append(self._render_minimap())

        # Show room description
        lines.append("")
        room_data = self.engine.get_current_room()
        if room_data:
            lines.append(f"=== Room {room_data['id']} ({room_data['type'].upper()}) ===")
            lines.append(room_data["description"])

        return "\n".join(lines)

    def _cmd_map(self) -> str:
        """Render 7x7 mini-map."""
        return self._render_minimap() + "\n" + self._status_line()

    def _cmd_attack(self) -> str:
        """Attack the first enemy in the room."""
        room = self.engine.get_current_room()
        if not room:
            return "ERROR: No dungeon loaded."

        enemies = room.get("enemies", [])
        if not enemies:
            return "No enemies here.\n" + self._status_line()

        char = self.engine.character
        enemy = enemies[0]

        # Resolve enemy stats
        if isinstance(enemy, dict):
            enemy_name = enemy.get("name", "Enemy")
            enemy_hp = enemy.get("hp", 5)
            enemy_defense = enemy.get("defense", 10)
            enemy_damage = enemy.get("damage", 3)
        else:
            enemy_name = str(enemy)
            enemy_hp = 5
            enemy_defense = 10
            enemy_damage = 3

        lines = []

        # WO-V80.0: Acquire Mimir function for combat narration (thermal-gated)
        _combat_mimir_fn = None
        if self._narrator:
            try:
                from codex.core.cortex import get_cortex
                _ctx = get_cortex()
                if _ctx.get_thermal_state().status != "RED":
                    from codex.integrations.mimir import query_mimir
                    _combat_mimir_fn = query_mimir
            except Exception:
                pass

        # Player attacks
        might_mod = char.get_stat_mod(StatType.MIGHT)
        dice_count = char.gear.get_total_dice_bonus(StatType.MIGHT)

        # Darkness penalty: -1d6 in dark rooms with no light
        pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
        _is_dark = getattr(pop_room, 'is_dark', False) if pop_room else False
        if _is_dark and self.engine._light_remaining <= 0:
            dice_count = max(1, dice_count - 1)
            lines.append("(Darkness: -1d6)")

        # Check for assist from ally
        _assisted = getattr(self, '_assist_pending', False)
        if _assisted:
            self._assist_pending = False

        # Gear set bonuses that affect attack rolls
        _set_bonuses = char.gear.get_active_set_bonuses()

        # Shadowweave 4pc: First attack each combat auto-crits
        _shadow_first_crit = self._first_attack_in_room and any(
            b.get("first_attack_crit") for b in _set_bonuses.values()
        )

        # Passive threshold: auto-hit weak enemies
        if passive_check(might_mod, enemy_defense):
            result = {"success": True, "total": might_mod + 1, "rolls": [], "modifier": might_mod, "dc": enemy_defense, "crit": _shadow_first_crit, "fumble": False}
            lines.append(f"Your gear outclasses {enemy_name}. (Auto-hit)")
        else:
            result = roll_dice_pool(dice_count, might_mod, enemy_defense, assist=_assisted)

        # Shadowweave 4pc: force crit on first attack
        if _shadow_first_crit and result["success"] and not result.get("crit"):
            result["crit"] = True
            lines.append("  Shadowweave: First strike is lethal!")

        self._first_attack_in_room = False

        if result["success"]:
            # Deal damage based on weapon tier
            weapon = char.gear.slots.get(GearSlot.R_HAND)
            damage = weapon.tier.value + 1 if weapon else 1

            # Apply CHARGE bonus damage if pending
            bonus = getattr(self, '_pending_bonus_damage', 0)
            if bonus:
                damage += bonus
                self._pending_bonus_damage = 0

            # Named Legendary: Sun-Cleaver stacking damage
            if self._sun_cleaver_kills > 0 and weapon and weapon.name == "Sun-Cleaver":
                damage += self._sun_cleaver_kills

            # Rot Hunter 3pc: +2 damage vs Blighted enemies
            _enemy_blighted = isinstance(enemy, dict) and "Blighted" in enemy.get("special", "")
            if _enemy_blighted and any(b.get("bonus_vs_blighted") for b in _set_bonuses.values()):
                rot_bonus = sum(b.get("bonus_vs_blighted", 0) for b in _set_bonuses.values())
                damage += rot_bonus
                lines.append(f"  Rot Hunter: +{rot_bonus} vs Blighted!")

            enemy_hp -= damage

            # Active Oil — weapon coating bonus damage
            if char.active_oil:
                oil = char.active_oil
                oil_effect = oil.get("effect", "")
                import re as _re
                oil_dmg_match = _re.search(r'\+(\d+)d(\d+)', oil_effect)
                if oil_dmg_match:
                    od = int(oil_dmg_match.group(1))
                    os = int(oil_dmg_match.group(2))
                    oil_dmg = sum(random.randint(1, os) for _ in range(od))
                    enemy_hp -= oil_dmg
                    lines.append(f"  {oil['name']}! +{oil_dmg} damage.")
                if "lifesteal" in oil_effect.lower():
                    char.heal(1)
                    lines.append(f"  Void lifesteal! (+1 HP)")

            # Affix: Blazing — +1d4 fire damage on hit
            if weapon and weapon.prefix == "Blazing":
                fire_dmg = random.randint(1, 4)
                enemy_hp -= fire_dmg
                lines.append(f"  Blazing! +{fire_dmg} fire damage.")

            # Affix: Frozen — 10% chance to slow (inflict Frozen condition)
            if weapon and weapon.prefix == "Frozen":
                if random.random() < 0.1:
                    if isinstance(enemy, dict):
                        enemy["frozen"] = True
                        lines.append(f"  Frozen! {enemy_name} is slowed — defense reduced!")

            _wname = weapon.name if weapon else "fists"
            # Affix: Keen — crit range expanded to 5-6
            is_crit = result.get("crit")
            if weapon and weapon.prefix == "Keen" and not is_crit:
                rolls = result.get("rolls", [])
                if rolls and all(r >= 5 for r in rolls):
                    is_crit = True

            if is_crit:
                lines.append(f"CRITICAL HIT! You strike {enemy_name} for {damage} damage!")
            else:
                lines.append(f"You hit {enemy_name} for {damage} damage! ({result['total']} vs DC {enemy_defense})")
            if self._narrator:
                _etype = "crit" if is_crit else "hit"
                _cnarr = self._narrator.narrate_combat_mimir(
                    _etype, enemy_name, damage, _wname, mimir_fn=_combat_mimir_fn)
                if _cnarr:
                    lines.append(f"  {_cnarr}")

            if enemy_hp <= 0:
                lines.append(f"{enemy_name} is slain!")
                if self._narrator:
                    _knarr = self._narrator.narrate_combat_mimir(
                        "kill", enemy_name, mimir_fn=_combat_mimir_fn)
                    if _knarr:
                        lines.append(f"  {_knarr}")
                enemies.pop(0)
                # Affix: Vampiric — heal 1 HP on kill
                if weapon and weapon.prefix == "Vampiric":
                    healed = char.heal(1)
                    if healed > 0:
                        lines.append(f"  Vampiric drain! (+{healed} HP)")
                # Rot Hunter 4pc: heal 1d6 on Blighted kill
                if _enemy_blighted and any(b.get("heal_on_blighted_kill") for b in _set_bonuses.values()):
                    rot_heal = random.randint(1, 6)
                    actual_heal = char.heal(rot_heal)
                    if actual_heal > 0:
                        lines.append(f"  Rot Hunter: Blight energy heals {actual_heal} HP!")
                # Named Legendary: on_kill effects
                if weapon and weapon.name in NAMED_LEGENDARY_ABILITIES:
                    leg = NAMED_LEGENDARY_ABILITIES[weapon.name]
                    if leg["trigger"] == "on_kill":
                        if leg["effect"] == "stacking_damage":
                            self._sun_cleaver_kills += 1
                            lines.append(f"  Ember Momentum! (+{self._sun_cleaver_kills} damage on next attack)")
                        elif leg["effect"] == "memory_drain":
                            lines.append(f"  Memory Drain! The {enemy_name}'s memories flow into you.")
                            lines.append(f"  (Ask the GM one fact about this floor.)")
                # Faction reputation: killing faction-aligned enemies
                _enemy_faction = enemy.get("faction_id", "") if isinstance(enemy, dict) else ""
                if _enemy_faction and hasattr(self.engine, 'faction_rep'):
                    # Killing faction enemies reduces rep with that faction
                    rep_msgs = self.engine.faction_rep.change_rep(_enemy_faction, -1)
                    for rm in rep_msgs:
                        lines.append(f"  [Faction] {rm}")

                # Quest trigger: enemy defeated
                if hasattr(self.engine, '_quest_dispatcher') and self.engine._quest_dispatcher:
                    faction_id = _enemy_faction
                    tier = enemy.get("tier", 1) if isinstance(enemy, dict) else 1
                    quest_msgs = self.engine._quest_dispatcher.on_enemy_defeated(enemy_name, tier, faction_id)
                    for qm in quest_msgs:
                        lines.append(f"  [Quest] {qm}")
                # WO-V37.0: Log kill event
                self._log_event("kill", target=enemy_name,
                                tier=enemy.get("tier", 1) if isinstance(enemy, dict) else 1,
                                room_id=self.engine.current_room_id)
                self._loom_shard(f"Slew {enemy_name} in room {self.engine.current_room_id}")  # WO-V79.0
                # Update the engine's populated room content
                pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
                if pop_room:
                    pop_room.content["enemies"] = enemies
            else:
                if isinstance(enemy, dict):
                    enemy["hp"] = enemy_hp
                lines.append(f"{enemy_name} has {enemy_hp} HP remaining.")
        else:
            if result.get("fumble"):
                lines.append(f"FUMBLE! You swing wildly and miss {enemy_name}. ({result['total']} vs DC {enemy_defense})")
                # Affix: Volatile — self-damage on fumble
                weapon = char.gear.slots.get(GearSlot.R_HAND)
                if weapon and weapon.prefix == "Volatile":
                    char.current_hp = max(0, char.current_hp - 1)
                    lines.append(f"  Volatile backlash! (-1 HP)")
            else:
                lines.append(f"You miss {enemy_name}. ({result['total']} vs DC {enemy_defense})")
            if self._narrator:
                _miss_type = "fumble" if result.get("fumble") else "miss"
                _mnarr = self._narrator.narrate_combat_mimir(
                    _miss_type, enemy_name, mimir_fn=_combat_mimir_fn)
                if _mnarr:
                    lines.append(f"  {_mnarr}")

        # Enemy retaliates (if alive)
        if enemy_hp > 0:
            lines.append("")
            retaliation = roll_dice_pool(2, 0, char.get_defense())
            if retaliation["success"]:
                # Check for Intercept DR bonus (WO-V17.0) + Guard self-DR
                intercept_dr = getattr(char, '_intercept_dr_bonus', 0) if getattr(char, '_intercept_active', False) else 0
                guard_dr = self._guard_dr_remaining
                self._guard_dr_remaining = 0  # Guard expires after one hit
                raw_damage = enemy_damage if isinstance(enemy_damage, int) else 3
                # Affix: Rooted — +1 DR when stationary (attacking = not moving)
                rooted_dr = sum(
                    1 for _it in char.gear.slots.values()
                    if _it and _it.prefix == "Rooted"
                )
                # Archetype: Rootwarden — +1 DR
                _arch_bonuses = self._get_archetype_bonuses()
                arch_dr = _arch_bonuses.get("dr_bonus", 0)
                effective_damage = max(1, raw_damage - char.gear.get_total_dr() - intercept_dr - guard_dr - rooted_dr - arch_dr)
                char.current_hp = max(0, char.current_hp - effective_damage)
                if guard_dr:
                    lines.append(f"{enemy_name} strikes! Guard absorbs {guard_dr} damage! {effective_damage} damage taken.")
                    # Warden's Watch 4pc: on block, allies get +1d6 next attack
                    if any(b.get("on_block_ally_bonus") for b in _set_bonuses.values()):
                        self._pending_bonus_damage += 1
                        lines.append(f"  Warden's Watch: Allies rallied! +1d6 next attack.")
                elif intercept_dr:
                    char._intercept_active = False
                    char._intercept_dr_bonus = 0
                    lines.append(f"{enemy_name} strikes! Your shield absorbs the blow! (-{intercept_dr} DR bonus) {effective_damage} damage taken.")
                else:
                    lines.append(f"{enemy_name} strikes you for {effective_damage} damage!")
                    # Reaction: Hearthflare / Solflare — fire on being hit
                    lines.extend(self._check_hearthflare(enemy_name, enemy))
                    # Affix: Thorns — reflect 1 damage on hit
                    # Named Legendary: Aegis Shield — full reflect
                    reflect_dmg = 0
                    for _slot_item in char.gear.slots.values():
                        if _slot_item and _slot_item.name == "Aegis Shield":
                            reflect_dmg = raw_damage  # Full attack reflected
                            enemy_hp -= reflect_dmg
                            lines.append(f"  Aegis Shield UNYIELDING! {reflect_dmg} damage reflected!")
                            break
                        elif _slot_item and _slot_item.suffix == "of Thorns":
                            reflect_dmg = 1
                            enemy_hp -= 1
                            lines.append(f"  Thorns reflect 1 damage back!")
                            break
                    # [Reflect] trait: pending reflect from `use` command
                    if self._reflect_pending > 0:
                        enemy_hp -= self._reflect_pending
                        lines.append(f"  Reflect! {self._reflect_pending} damage returned!")
                        self._reflect_pending = 0
                    if self._narrator:
                        _ehnarr = self._narrator.narrate_combat_mimir(
                            "enemy_hit", enemy_name, effective_damage, mimir_fn=_combat_mimir_fn)
                        if _ehnarr:
                            lines.append(f"  {_ehnarr}")

                # Enemy special: condition infliction on hit
                enemy_special = enemy.get("special", "") if isinstance(enemy, dict) else ""
                _CONDITION_KEYWORDS = {
                    "Sap-Drained": Condition.SAP_DRAINED,
                    "Spore-Sick": Condition.SPORE_SICK,
                    "Resonance-Touched": Condition.RESONANCE_TOUCHED,
                    "Blighted": Condition.BLIGHTED,
                    "Gall-Marked": Condition.GALL_MARKED,
                    "Shaken": Condition.SHAKEN,
                    "Entangled": Condition.ENTANGLED,
                    "Poisoned": Condition.POISONED,
                    "Weakened": Condition.WEAKENED,
                }
                for keyword, cond in _CONDITION_KEYWORDS.items():
                    if keyword in enemy_special and not char.has_condition(cond):
                        # Rot Hunter 2pc: resist Blight passively
                        if cond == Condition.BLIGHTED and any(
                            b.get("resist_blight") for b in _set_bonuses.values()
                        ):
                            lines.append("  Rot Hunter: Blight resisted!")
                            break
                        # Archetype: Blightwalker — immune to Blighted
                        if cond == Condition.BLIGHTED and self._get_archetype_bonuses().get("blight_immune"):
                            lines.append("  Blightwalker: The Blight cannot touch you.")
                            break
                        # Check for a DC save if mentioned (e.g., "DC 11 Grit")
                        import re
                        dc_match = re.search(r'DC\s*(\d+)\s*(Might|Wits|Grit|Aether)', enemy_special)
                        if dc_match:
                            save_dc = int(dc_match.group(1))
                            save_stat = StatType(dc_match.group(2).upper())
                            save_mod = char.get_stat_mod(save_stat)
                            save_roll = roll_dice_pool(char.gear.get_total_dice_bonus(save_stat), save_mod, save_dc)
                            if not save_roll["success"]:
                                # Reaction: Spore Adaptation / Choir Resonance
                                spore_lines = self._check_spore_adaptation(char, cond, save_stat, save_dc)
                                lines.extend(spore_lines)
                                if not char.has_condition(cond):  # Reaction may have prevented it
                                    if not any("succeeded" in l.lower() or "shields you" in l.lower() for l in spore_lines):
                                        msg = char.add_condition(cond)
                                        lines.append(f"  {msg} (failed {save_stat.value} save vs DC {save_dc})")
                        else:
                            msg = char.add_condition(cond)
                            lines.append(f"  {msg}")
                        break  # Only one condition per hit

            else:
                lines.append(f"{enemy_name} attacks but misses!")
                if self._narrator:
                    _emnarr = self._narrator.narrate_combat_mimir(
                        "enemy_miss", enemy_name, mimir_fn=_combat_mimir_fn)
                    if _emnarr:
                        lines.append(f"  {_emnarr}")

        # Check death — Reactions first, then Named Legendary intercepts
        if not char.is_alive():
            # Reaction: Rootcatch / Blightgrasp — stabilize at 1
            rootcatch_lines = self._check_rootcatch(char)
            if rootcatch_lines:
                lines.extend(rootcatch_lines)
            # Soulstone Amulet: revive once per campaign (if still dead)
            amulet_slot = None
            for slot, item in char.gear.slots.items():
                if item and item.name == "Soulstone Amulet":
                    amulet_slot = slot
                    break
            if amulet_slot:
                char.current_hp = 1
                char.gear.unequip(amulet_slot)
                lines.append("")
                lines.append("The Soulstone Amulet SHATTERS. A trapped soul screams free.")
                lines.append(f"{char.name} gasps back to life at 1 HP.")
                lines.append("The amulet is gone. The soul is released.")
                # NOT dead — skip death handling
            # Warden's Bastion: save an ally (check if another party member has it)
            elif not self._last_stand_used:
                bastion_holder = None
                for ally in self.engine.party:
                    if ally is not char and ally.is_alive():
                        for slot, item in ally.gear.slots.items():
                            if item and item.name == "Warden's Bastion":
                                bastion_holder = ally
                                break
                        if bastion_holder:
                            break
                if bastion_holder:
                    char.current_hp = 1
                    self._last_stand_used = True
                    lines.append("")
                    lines.append(f"{bastion_holder.name}'s Warden's Bastion flares!")
                    lines.append(f"LAST STAND! {char.name} is saved at 1 HP.")
                    lines.append("(Once per combat.)")
                    # NOT dead — skip death handling

        if not char.is_alive():
            self.dead = True
            lines.append("")
            if self.engine.check_tpk():
                lines.append("=== THE BURNWILLOW FALLS ===")
                lines.append("")
                lines.append("Every light has gone out. No one returns to Emberhome.")
                lines.append("No Memory Seeds carry forward. No names for the Chapel wall.")
                lines.append("The fire-leaves darken. The Root-Song ends.")
                lines.append("")
                lines.append("Campaign over. Full reset.")
            else:
                lines.append("=== YOU HAVE FALLEN ===")
                lines.append(f"Doom Clock: {self.engine.doom_clock.current}")
                lines.append("The dungeon claims another soul.")
            return "\n".join(lines)

        # End of combat round — tick conditions
        expired = char.tick_conditions()
        for msg in expired:
            lines.append(msg)

        # Burning damage
        if char.has_condition(Condition.BURNING):
            burn_dmg = random.randint(1, 4)
            char.current_hp = max(0, char.current_hp - burn_dmg)
            lines.append(f"Burning! (-{burn_dmg} HP)")

        # Poisoned damage
        if char.has_condition(Condition.POISONED):
            poison_dmg = random.randint(1, 4)
            char.current_hp = max(0, char.current_hp - poison_dmg)
            lines.append(f"Poison courses through you. (-{poison_dmg} HP)")

        # Moonstone 4pc: party regen 1 HP/round in combat
        regen_amount = sum(b.get("party_regen", 0) for b in _set_bonuses.values())
        if regen_amount > 0 and char.is_alive():
            for ally in self.engine.party:
                if ally.is_alive() and ally.current_hp < ally.max_hp:
                    actual = ally.heal(regen_amount)
                    if actual > 0:
                        lines.append(f"  Moonstone Circle: {ally.name} regenerates {actual} HP.")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_search(self) -> str:
        """Search the room for loot. +1 Doom."""
        room = self.engine.get_current_room()
        if not room:
            return "ERROR: No dungeon loaded."

        char = self.engine.character
        wits_mod = char.get_stat_mod(StatType.WITS)
        dice_count = char.gear.get_total_dice_bonus(StatType.WITS)

        # Shadowweave 2pc: +2 Scout bonus
        _set_bonuses = char.gear.get_active_set_bonuses()
        scout_bonus = sum(b.get("scout_bonus", 0) for b in _set_bonuses.values())
        wits_mod += scout_bonus

        # Darkness penalty: -1d6 in dark rooms with no light
        pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
        _is_dark = getattr(pop_room, 'is_dark', False) if pop_room else False
        if _is_dark and self.engine._light_remaining <= 0:
            dice_count = max(1, dice_count - 1)

        # Passive threshold: auto-succeed if gear makes failure impossible
        if passive_check(wits_mod, 11):
            result = {"success": True, "total": wits_mod + 1, "rolls": [], "modifier": wits_mod, "dc": 11, "crit": False, "fumble": False}
            auto_pass = True
        else:
            result = roll_dice_pool(dice_count, wits_mod, 11)
            auto_pass = False

        doom_events = self.engine.advance_doom(1)

        lines = []
        if auto_pass:
            lines.append("Your trained eye finds it instantly. (Auto-success)")

        found_loot = False
        if result["success"]:
            loot = room.get("loot", [])
            if loot:
                found = loot.pop(0)
                if isinstance(found, dict):
                    name = found.get("name", str(found))
                else:
                    name = str(found)
                _lflav = self._narrator.describe_loot(name) if self._narrator else ""
                lines.append(f"You found: {name}!{_lflav}")
                self.engine.register_loot_find(name)
                found_loot = True
                # Quest trigger: loot acquired
                if hasattr(self.engine, '_quest_dispatcher') and self.engine._quest_dispatcher:
                    room = self.engine.get_current_room()
                    tier = room.get("tier", 1) if room else 1
                    quest_msgs = self.engine._quest_dispatcher.on_loot_acquired(tier)
                    for qm in quest_msgs:
                        lines.append(f"  [Quest] {qm}")
                # Update engine state
                pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
                if pop_room:
                    pop_room.content["loot"] = loot
            else:
                lines.append("Search successful, but nothing of value remains.")
        else:
            lines.append(f"You find nothing useful. ({result['total']} vs DC 12)")

        # WO-V17.0: Pity timer — guarantee loot after drought
        if not found_loot:
            pity = self.engine.check_pity_loot()
            if pity:
                lines.append(f"As you dig deeper... you uncover: {pity['name']}!")
                pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
                if pop_room:
                    pop_room.content.setdefault("loot", []).append(pity)

        for event in doom_events:
            lines.append(event)

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_loot(self) -> str:
        """Pick up the first item from the room (no roll)."""
        item = self.engine.loot_item()
        if item is None:
            return "Nothing to pick up.\n" + self._status_line()
        self.engine.character.add_to_inventory(item)
        # WO-V37.0: Log loot event
        self._log_event("loot", item_name=item.name,
                        tier=item.tier.value if item.tier else 1,
                        room_id=self.engine.current_room_id)
        self._loom_shard(f"Found {item.name}")  # WO-V79.0
        return f"Picked up: {item.name}\n\n" + self._status_line()

    def _cmd_drop(self, arg: str) -> str:
        """Drop an item by name."""
        arg = arg.strip()
        if not arg:
            return "Drop what? Usage: drop <item name>\n" + self._status_line()
        dropped = self.engine.drop_item(arg)
        if dropped is None:
            return f"You don't have '{arg}'.\n" + self._status_line()
        return f"Dropped: {dropped.name}\n\n" + self._status_line()

    def _cmd_rest(self, arg: str = "") -> str:
        """Rest using RestManager: 'rest short' (default) or 'rest long'."""
        rest_type = arg.strip().lower() if arg else "short"
        if rest_type not in ("short", "long"):
            rest_type = "short"

        # Ensure party includes character for RestManager
        if not self.engine.party and self.engine.character:
            self.engine.party = [self.engine.character]

        result = self._rest_mgr.rest(self.engine, "BURNWILLOW", rest_type)

        # Restore Aether pool: short rest = half, long rest = full
        char = self.engine.character
        if rest_type == "long":
            restored = char.restore_aether(char.max_aether_pool)
        else:
            restored = char.restore_aether((char.max_aether_pool + 1) // 2)

        lines = [result.summary()]
        if restored > 0:
            lines.append(f"Aether restored: +{restored} ({char.current_aether_pool}/{char.max_aether_pool})")

        # WO-V35.0: Broadcast rest complete
        if self._broadcast:
            self._broadcast.broadcast("REST_COMPLETE", {
                "rest_type": rest_type,
                "system_tag": "BURNWILLOW",
                "hp_recovered": result.hp_recovered,
                "summary": result.summary(),
            })

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_stats(self) -> str:
        """Show character stats and active archetypes."""
        from codex.games.burnwillow.engine import detect_archetypes
        char = self.engine.character
        lines = [
            f"=== {char.name} ===",
            f"HP: {char.current_hp}/{char.max_hp}  |  Aether: {char.current_aether_pool}/{char.max_aether_pool}",
            f"Defense: {char.get_defense()} | DR: {char.gear.get_total_dr()}",
            "",
            f"MIGHT:  {char.might:>2} ({char.get_stat_mod(StatType.MIGHT):+d})",
            f"WITS:   {char.wits:>2} ({char.get_stat_mod(StatType.WITS):+d})",
            f"GRIT:   {char.grit:>2} ({char.get_stat_mod(StatType.GRIT):+d})",
            f"AETHER: {char.aether:>2} ({char.get_stat_mod(StatType.AETHER):+d})",
        ]
        # Active archetypes from gear source alignment
        archetypes = detect_archetypes(char.gear)
        if archetypes:
            lines.append("")
            lines.append("ARCHETYPES:")
            for arch_id, arch_def in archetypes.items():
                lines.append(f"  {arch_def['name']}: {arch_def['description']}")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_inventory(self) -> str:
        """Show equipped gear grid."""
        char = self.engine.character
        lines = ["=== GEAR GRID ==="]

        for slot in GearSlot:
            item = char.gear.slots.get(slot)
            if item:
                traits = " ".join(item.special_traits) if item.special_traits else ""
                extra = f" {traits}" if traits else ""
                lines.append(f"  {slot.value:<12} {item.name} (T{item.tier.value}){extra}")
            else:
                lines.append(f"  {slot.value:<12} --empty--")

        if char.inventory:
            lines.append("")
            lines.append("BACKPACK:")
            for item in char.inventory:
                lines.append(f"  * {item.name}")

        if char.keys > 0:
            lines.append(f"\nKeys: {char.keys}")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_push(self, arg: str) -> str:
        """Push a piece of furniture in a cardinal direction."""
        parts = arg.strip().split()
        if len(parts) < 2:
            return "Usage: push <name> <n/s/e/w>\n" + self._status_line()

        direction = parts[-1].lower()
        name_fragment = " ".join(parts[:-1])

        result = self.engine.push_furniture(name_fragment, direction)
        lines = [result["message"]]
        if result["success"]:
            pos = result.get("position", ("?", "?"))
            lines.append(f"  -> Now at ({pos[0]}, {pos[1]})")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _try_use_consumable(self, char, arg: str) -> str:
        """Try to use a consumable (potion/bomb/oil/elixir). Returns result string or empty."""
        # Search all consumable lists
        for consumable_list, list_name in [
            (char.potions, "potions"),
            (char.bombs, "bombs"),
            (char.oils, "oils"),
            (char.elixirs, "elixirs"),
        ]:
            for i, item in enumerate(consumable_list):
                if arg in item["name"].lower():
                    # Found a match — consume it
                    consumed = consumable_list.pop(i)
                    return self._apply_consumable(char, consumed)
        return ""  # No consumable matched

    def _apply_consumable(self, char, item: dict) -> str:
        """Apply a consumable's effect and return the result message."""
        lines = [f"Used {item['name']}!"]
        name = item["name"]
        item_type = item["type"]
        effect = item["effect"]

        if item_type == "potion":
            # Parse and apply potion effects
            if "Heal" in effect or "heal" in effect:
                import re
                heal_match = re.search(r'(\d+)d(\d+)', effect)
                if heal_match:
                    dice = int(heal_match.group(1))
                    sides = int(heal_match.group(2))
                    heal_amount = sum(random.randint(1, sides) for _ in range(dice))
                    actual = char.heal(heal_amount)
                    lines.append(f"  Healed {actual} HP.")
                if "cure Poisoned" in effect:
                    char.remove_condition(Condition.POISONED)
                    lines.append("  Poison cured.")
            if "+2 Might" in effect:
                # Temporary stat buff — store as condition-like effect
                char.might += 2
                lines.append(f"  Might increased by 2 for 3 rounds. (Score: {char.might})")
            if "+2 DR" in effect:
                lines.append(f"  +2 DR for 3 rounds.")
            if "Reveal hidden" in effect:
                lines.append(f"  Hidden rooms and traps revealed for this floor.")
            if "Sense all enemies" in effect:
                lines.append(f"  All enemies on this floor are now visible.")
            if "Summon" in effect:
                lines.append(f"  A wolf spirit materializes!")

        elif item_type == "bomb":
            # Apply AoE damage to all enemies in room
            room = self.engine.get_current_room()
            enemies = room.get("enemies", []) if room else []
            import re
            dmg_match = re.search(r'(\d+)d(\d+)', effect)
            total_dmg = 0
            if dmg_match:
                dice = int(dmg_match.group(1))
                sides = int(dmg_match.group(2))
                total_dmg = sum(random.randint(1, sides) for _ in range(dice))

            if enemies:
                killed = []
                for enemy in enemies:
                    if isinstance(enemy, dict):
                        enemy["hp"] = enemy.get("hp", 5) - total_dmg
                        if enemy["hp"] <= 0:
                            killed.append(enemy.get("name", "Enemy"))
                lines.append(f"  BOOM! {total_dmg} damage to all enemies!")
                if "Burning" in effect:
                    lines.append(f"  Enemies are Burning!")
                if "Blind" in effect or "blind" in effect:
                    lines.append(f"  Enemies are Blinded!")
                if "Entangled" in effect:
                    lines.append(f"  Enemies are Entangled!")
                if "Frozen" in effect:
                    lines.append(f"  Enemies are Frozen!")
                if killed:
                    # Clean up dead enemies
                    pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
                    if pop_room:
                        pop_room.content["enemies"] = [
                            e for e in pop_room.content.get("enemies", [])
                            if not (isinstance(e, dict) and e.get("hp", 1) <= 0)
                        ]
                    lines.append(f"  Slain: {', '.join(killed)}")
            else:
                lines.append(f"  The bomb explodes... but there's nothing to hit.")

        elif item_type == "oil":
            # Apply weapon coating
            char.active_oil = item
            lines.append(f"  Weapon coated. Effect: {effect}")
            lines.append(f"  (Lasts 1 combat encounter.)")

        elif item_type == "elixir":
            # Apply floor-duration buff (replaces active elixir)
            if char.active_elixir:
                lines.append(f"  (Replacing active elixir: {char.active_elixir['name']})")
            char.active_elixir = item
            lines.append(f"  Effect: {effect}")
            lines.append(f"  (Lasts entire floor. One elixir at a time.)")
            # Hag's Bargain self-damage
            if "Costs 1d6 HP" in effect or "costs 1d6" in effect.lower():
                self_dmg = random.randint(1, 6)
                char.current_hp = max(1, char.current_hp - self_dmg)
                lines.append(f"  The bargain demands blood. (-{self_dmg} HP)")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_use(self, arg: str) -> str:
        """Activate a special trait on an equipped item, or use a consumable."""
        arg = arg.strip().lower()
        if not arg:
            return "Use what? Usage: use <item name>\n" + self._status_line()

        char = self.engine.character

        # Check consumables first (potions, bombs, oils, elixirs)
        consumable_result = self._try_use_consumable(char, arg)
        if consumable_result:
            return consumable_result

        # Search equipped gear for matching item
        target_item = None
        for slot, item in char.gear.slots.items():
            if item and arg in item.name.lower():
                target_item = item
                break

        # Search backpack
        if target_item is None:
            for idx, item in char.inventory.items():
                if arg in item.name.lower():
                    target_item = item
                    break

        if target_item is None:
            return f"You don't have '{arg}'.\n" + self._status_line()

        if not target_item.special_traits:
            return f"{target_item.name} has no special traits.\n" + self._status_line()

        # Activate the first trait on the item
        trait_id = target_item.special_traits[0]
        # Strip bracket formatting if present (e.g., "[Lockpick]" -> "Lockpick")
        clean_id = trait_id.strip("[]").upper().replace(" ", "_")

        # Aether cost gating for magical traits
        _AETHER_COSTS = {
            "LIGHT": 1, "REVEAL": 1, "SPELLSLOT": 2, "SUMMON": 3, "HEAL": 1,
            # Void traits
            "NULLIFY": 2, "VOIDGRIP": 2, "COLLAPSE": 3, "WITHER": 3,
            # Choir traits
            "HELLFIRE": 2, "BLIGHTWEB": 2, "ICEWALL": 1, "OVERGROWTH_LASH": 2, "CHOIR_CALL": 3,
        }
        aether_cost = _AETHER_COSTS.get(clean_id, 0)
        # Arborist 3pc: Sanctify costs no action (free cast)
        _use_set_bonuses = char.gear.get_active_set_bonuses()
        if clean_id == "SANCTIFY" and any(b.get("trait_free") == "SANCTIFY" for b in _use_set_bonuses.values()):
            aether_cost = 0
        # Archetype: Voidtouched — Nullify costs 1 less Aether
        if clean_id == "NULLIFY" and self._get_archetype_bonuses().get("nullify_cost_reduction"):
            aether_cost = max(0, aether_cost - 1)
        if aether_cost > 0:
            if not char.spend_aether(aether_cost):
                return (f"Not enough Aether! ({clean_id} costs {aether_cost}, "
                        f"you have {char.current_aether_pool}/{char.max_aether_pool})\n"
                        + self._status_line())

        # Build context with combat state for damage-dealing traits
        pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
        enemies = pop_room.content.get("enemies", []) if pop_room and isinstance(pop_room.content, dict) else []
        enemy_defense = enemies[0].get("defense", 10) if enemies else 11
        # Archetype bonuses for trait context
        _arch_bonuses = self._get_archetype_bonuses()
        context = {
            "character": char,
            "room": self.engine.get_current_room(),
            "item": target_item,
            "enemy_defense": enemy_defense,
            "enemy_count": len(enemies),
            "is_boss": enemies[0].get("boss", False) if enemies and isinstance(enemies[0], dict) else False,
            "ambush_round": getattr(self, '_ambush_round', False) or (
                clean_id == "BACKSTAB" and any(
                    b.get("backstab_double_surprise") for b in _use_set_bonuses.values()
                )
            ),
            "enemy_blinded": bool(getattr(self, '_blinded_enemies', set())),
            # Archetype: Sporecaster — Snare +1 target
            "snare_extra_target": _arch_bonuses.get("snare_extra_target", 0),
        }

        try:
            result = self._trait_handler.activate_trait(clean_id, "burnwillow", context)
        except Exception as e:
            return f"Trait activation failed: {e}\n" + self._status_line()

        lines = [f"** {target_item.name} — {clean_id} **"]
        lines.append(result.get("message", "Trait activated."))

        # ── Apply effects to game state ──
        if result.get("success"):
            # SET_TRAP: add a HAZARD to the current room
            if result.get("creates") == "HAZARD":
                pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
                if pop_room:
                    hazard = {"name": f"Trap ({target_item.name})", "damage": 4, "source": "player"}
                    pop_room.content.setdefault("hazards", []).append(hazard)
                    lines.append("  -> Trap set! Enemies entering will take damage.")

            # CHARGE: store bonus damage for the next attack
            if result.get("bonus_damage"):
                self._pending_bonus_damage = result["bonus_damage"]
                lines.append(f"  -> Next attack deals +{result['bonus_damage']} bonus damage!")

            # SANCTIFY: deal AoE damage to all enemies in the room
            if result.get("aoe_damage"):
                aoe = result["aoe_damage"]
                pop_room = self.engine.populated_rooms.get(self.engine.current_room_id)
                if pop_room:
                    enemies = pop_room.content.get("enemies", [])
                    killed = []
                    for enemy in enemies:
                        if isinstance(enemy, dict):
                            enemy["hp"] = enemy.get("hp", 5) - aoe
                            if enemy["hp"] <= 0:
                                killed.append(enemy.get("name", "Enemy"))
                    for name in killed:
                        pop_room.content["enemies"] = [
                            e for e in pop_room.content["enemies"]
                            if not (isinstance(e, dict) and e.get("hp", 1) <= 0)
                        ]
                    lines.append(f"  -> Holy fire deals {aoe} damage to all enemies!")
                    if killed:
                        lines.append(f"  -> Slain: {', '.join(killed)}")

            # RESIST_BLIGHT: apply temporary DR bonus to character
            if result.get("dr_bonus"):
                char._blight_dr_bonus = result["dr_bonus"]
                lines.append(f"  -> Blight DR +{result['dr_bonus']} active.")

            # FAR_SIGHT: reduce scout DC for next search
            if result.get("scout_dc_reduction"):
                self._scout_dc_reduction = result["scout_dc_reduction"]
                lines.append(f"  -> Scout DC reduced by {result['scout_dc_reduction']} for next search.")

            # ── Track setup traits for combo detection ──
            if result.get("defense_reduction"):
                self._snared_enemies.add("room_enemies")
                self._snare_reduction = result["defense_reduction"]
                self._last_trait_used = "SNARE"
            elif result.get("blind_rounds"):
                self._blinded_enemies.add("room_enemies")
                self._last_trait_used = "FLASH"
            elif result.get("self_dr_bonus") and result.get("action") == "guard":
                self._last_trait_used = "GUARD"
            elif result.get("bonus_damage") and result.get("action") != "command":
                self._last_trait_used = "CHARGE"
            elif result.get("dispels_darkness"):
                self._last_trait_used = "LIGHT"
            else:
                self._last_trait_used = clean_id

            # ── Combo registry: (setup → payoff) → bonus ──
            _combo_lines = self._resolve_combo(clean_id, result, enemies, pop_room)
            lines.extend(_combo_lines)

            # Named Legendary: Tempest Annihilator Storm Surge
            if clean_id == "TEMPEST":
                for _sl, _it in char.gear.slots.items():
                    if _it and _it.name == "Tempest Annihilator":
                        self._storm_surge_pending = 4
                        lines.append("  -> Storm Surge! +4 Aether score on next check.")
                        break

            # DAMAGE: apply to current enemy (Ranged, Spellslot, Backstab)
            if result.get("damage") and result["damage"] > 0:
                dmg = result["damage"]
                # Arborist 4pc: Aether abilities auto-crit on Blighted enemies
                if result.get("uses_aether") or result.get("action") in ("spellslot", "sanctify", "inferno", "tempest", "voidgrip"):
                    if enemies and isinstance(enemies[0], dict) and "Blighted" in enemies[0].get("special", ""):
                        if any(b.get("crit_vs_blighted") for b in _use_set_bonuses.values()):
                            dmg *= 2
                            lines.append("  -> Arborist's Legacy: Auto-crit vs Blighted!")
                if enemies:
                    target = enemies[0]
                    target["hp"] = target.get("hp", 5) - dmg
                    ename = target.get("name", "Enemy")
                    lines.append(f"  -> {ename} takes {dmg} damage!")
                    if target["hp"] <= 0:
                        pop_room.content["enemies"] = [e for e in enemies if e.get("hp", 1) > 0]
                        lines.append(f"  -> {ename} slain!")

            # HEAL: restore HP (resolver already calls char.heal, just display)
            if result.get("heal_amount") and result["heal_amount"] > 0:
                heal_total = result["heal_amount"]
                # Moonstone 2pc: Mending heals +1d6
                if result.get("action") == "mending":
                    bonus_dice = sum(b.get("heal_bonus_die", 0) for b in _use_set_bonuses.values())
                    if bonus_dice > 0:
                        bonus_heal = sum(random.randint(1, 6) for _ in range(bonus_dice))
                        extra = char.heal(bonus_heal)
                        heal_total += extra
                        lines.append(f"  -> Moonstone Circle: +{extra} bonus healing!")
                lines.append(f"  -> Healed {heal_total} HP! ({char.current_hp}/{char.max_hp})")
                # Moonstone 3pc: Renewal duration +2 rounds
                if result.get("action") == "renewal" and result.get("hot_rounds"):
                    duration_bonus = sum(b.get("renewal_duration_bonus", 0) for b in _use_set_bonuses.values())
                    if duration_bonus > 0:
                        total_rounds = result["hot_rounds"] + duration_bonus
                        lines.append(f"  -> Moonstone Circle: Renewal extended to {total_rounds} rounds!")

            # GUARD: self DR buff until next turn
            if result.get("self_dr_bonus"):
                self._guard_dr_remaining = result["self_dr_bonus"]
                # Archetype: Amberwright — Guard lasts 1 extra round
                _arch = self._get_archetype_bonuses()
                if _arch.get("guard_reflect_extra_round"):
                    self._guard_dr_remaining_extra = result["self_dr_bonus"]
                    lines.append(f"  -> DR +{result['self_dr_bonus']} for 2 turns! (Amberwright)")
                else:
                    lines.append(f"  -> DR +{result['self_dr_bonus']} until your next turn.")

            # REFLECT: store pending reflect for next incoming hit
            if result.get("reflect_damage"):
                self._reflect_pending = result["reflect_damage"]
                lines.append(f"  -> Next attack against you reflects {result['reflect_damage']} damage!")

            # LIGHT: dispel darkness in current room + duration
            if result.get("dispels_darkness"):
                self.engine._light_remaining = result.get("light_duration", 3)
                if pop_room:
                    pop_room.is_dark = False
                lines.append(f"  -> Light! Darkness dispelled for {result['light_duration']} rooms.")

            # REVEAL: show hidden exits and secret rooms
            if result.get("reveals_secrets"):
                revealed = []
                room_data = self.engine.get_current_room()
                if room_data and self.engine.dungeon_graph:
                    geom = room_data.get("geometry")
                    if geom and hasattr(geom, 'connections'):
                        for conn_id in geom.connections:
                            conn_room = self.engine.dungeon_graph.rooms.get(conn_id)
                            if conn_room and getattr(conn_room, 'is_secret', False):
                                conn_room.is_secret = False
                                revealed.append(conn_room.name if hasattr(conn_room, 'name') else f"Room {conn_id}")
                if revealed:
                    lines.append(f"  -> Revealed: {', '.join(revealed)}")
                else:
                    lines.append("  -> No hidden features nearby.")

            # LOCKPICK: unlock adjacent locked room
            if result.get("action") == "lockpick" and result.get("success"):
                unlocked = False
                room_data = self.engine.get_current_room()
                if room_data and self.engine.dungeon_graph:
                    geom = room_data.get("geometry")
                    if geom and hasattr(geom, 'connections'):
                        for conn_id in geom.connections:
                            conn_room = self.engine.dungeon_graph.rooms.get(conn_id)
                            if conn_room and getattr(conn_room, 'is_locked', False):
                                conn_room.is_locked = False
                                rname = conn_room.name if hasattr(conn_room, 'name') else f"Room {conn_id}"
                                lines.append(f"  -> Unlocked: {rname}")
                                unlocked = True
                                break
                if not unlocked:
                    lines.append("  -> No locked doors nearby.")

            # SUMMON: spawn a spirit minion
            if result.get("summon"):
                from codex.games.burnwillow.engine import create_minion
                minion = create_minion(char.name, char.get_stat_mod(StatType.AETHER))
                self.engine.party.append(minion)
                lines.append(f"  -> Spirit summoned! (HP: {minion.current_hp}, {minion.summon_duration} rounds)")

        else:
            if result.get("creates"):
                lines.append("  -> Failed to create effect.")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────
    # TRAIT COMBO SYSTEM (#172)
    # ─────────────────────────────────────────────────────────────────────

    # Combo registry: (setup_trait, payoff_trait) → themed name
    # Combos fire when payoff_trait is used while setup_trait's effect is active.
    _COMBO_REGISTRY: dict[tuple[str, str], str] = {
        # Natural combos (source-themed)
        ("SNARE", "CLEAVE"):    "ROOT CRUSH",      # Rot + Wood: mycelium holds, branch strikes
        ("SNARE", "RANGED"):    "PINNED PREY",     # Rot + Physical: tendrils hold, arrow finds
        ("FLASH", "BACKSTAB"):  "EMBER SHADOW",    # Fire + Stealth: hearth-flash blinds, blade follows
        ("FLASH", "SPELLSLOT"): "SUNBURST",        # Fire + Song: fire amplifies the song
        ("GUARD", "REFLECT"):   "AMBER MIRROR",    # Amber + Amber: hardened sap rebounds
        ("CHARGE", "CLEAVE"):   "TIMBER FALL",     # Wood + Wood: the whole tree comes down
        ("LIGHT", "REVEAL"):    "SONG ECHO",       # Fire + Song: light carries the song
        # Corrupted Choir combos (Zone 3+, Undergrove)
        ("BLIGHTWEB", "CLEAVE"):  "BLIGHT CRUSH",  # Choir Rot + Wood: +1d6 AND Blighted
        ("FLASH", "HELLFIRE"):    "SOLAR FLARE",   # Fire + Solheart: 2x AoE, hits allies
        ("ICEWALL", "REFLECT"):   "ICE MIRROR",    # Ashenmere + Amber: 3x reflect, -1 DR
        ("LIGHT", "CHOIR_CALL"):  "CHOIR PULSE",   # Fire + Choir: reveals floor, +1 Resonance
        # Void combos (endgame)
        ("NULLIFY", "WITHER"):  "UNRAVELING",      # Strip defenses then diminish: 2x wither
        ("COLLAPSE", "INFERNO"): "EVENT HORIZON",   # Gravity + AoE: +50% to pinned targets
        ("COLLAPSE", "TEMPEST"): "EVENT HORIZON",
        ("COLLAPSE", "WHIRLWIND"): "EVENT HORIZON",
        ("COLLAPSE", "SHOCKWAVE"): "EVENT HORIZON",
        ("COLLAPSE", "HELLFIRE"): "EVENT HORIZON",
    }

    def _resolve_combo(self, current_trait: str, result: dict,
                       enemies: list, pop_room) -> list[str]:
        """Check if current_trait forms a combo with _last_trait_used.

        Returns lines describing combo effects. Mutates game state as needed.
        """
        lines: list[str] = []
        setup = self._last_trait_used
        combo_key = (setup, current_trait)
        combo_name = self._COMBO_REGISTRY.get(combo_key)

        if not combo_name:
            # Show combo hints for setup traits
            if current_trait == "SNARE" and result.get("success"):
                lines.append("  -> Combo ready: CLEAVE (Root Crush) or RANGED (Pinned Prey)!")
            elif current_trait == "FLASH" and result.get("success"):
                lines.append("  -> Combo ready: BACKSTAB (Ember Shadow) or SPELLSLOT (Sunburst)!")
            elif current_trait == "GUARD":
                lines.append("  -> Combo ready: REFLECT (Amber Mirror)!")
            elif current_trait == "CHARGE" and result.get("success"):
                lines.append("  -> Combo ready: CLEAVE (Timber Fall)!")
            elif current_trait == "LIGHT":
                lines.append("  -> Combo ready: REVEAL (Song Echo)!")
            elif current_trait == "BLIGHTWEB" and result.get("success"):
                lines.append("  -> Choir combo ready: CLEAVE (Blight Crush)!")
            elif current_trait == "ICEWALL":
                lines.append("  -> Choir combo ready: REFLECT (Ice Mirror)!")
            elif current_trait == "NULLIFY" and result.get("success"):
                lines.append("  -> Void combo ready: WITHER (Unraveling)!")
            elif current_trait == "COLLAPSE" and result.get("success"):
                lines.append("  -> Void combo ready: any AoE (Event Horizon)!")
            return lines

        lines.append(f"  >> COMBO: {combo_name}! ({setup} + {current_trait}) <<")

        if combo_key == ("SNARE", "CLEAVE"):
            # +1d6 bonus damage per snared target applied to all cleave hits
            bonus = random.randint(1, 6)
            lines.append(f"  -> Snared enemies reel! +{bonus} bonus cleave damage!")
            if enemies:
                for e in enemies[:result.get("cleave_targets", 1)]:
                    e["hp"] = e.get("hp", 5) - bonus
                    ename = e.get("name", "Enemy")
                    lines.append(f"  -> {ename} takes {bonus} combo damage!")
                    if e["hp"] <= 0:
                        lines.append(f"  -> {ename} slain!")
                if pop_room and isinstance(pop_room.content, dict):
                    pop_room.content["enemies"] = [
                        e for e in pop_room.content.get("enemies", [])
                        if e.get("hp", 1) > 0
                    ]
            self._snared_enemies.clear()

        elif combo_key == ("SNARE", "RANGED"):
            # Snare lowers the effective DC for ranged attacks
            reduction = self._snare_reduction
            lines.append(f"  -> Pinned target! DC reduced by {reduction} for this shot.")
            # Re-resolve ranged with lower DC if original missed
            if not result.get("success") and reduction > 0:
                char = self.engine.character
                item = None
                for _it in char.gear.slots.values():
                    if _it and any("Ranged" in t for t in _it.special_traits):
                        item = _it
                        break
                if item:
                    stat = item.get_pool_stat() if item else StatType.MIGHT
                    enemy_def = enemies[0].get("defense", 10) if enemies else 11
                    new_dc = max(1, enemy_def - reduction)
                    recheck = char.make_check(stat, new_dc)
                    if recheck.success:
                        tier = item.tier.value if item else 1
                        damage = tier + 1
                        lines.append(f"  -> Re-aimed! {stat.value} {recheck.total} vs DC {new_dc} — HIT for {damage}!")
                        if enemies:
                            enemies[0]["hp"] = enemies[0].get("hp", 5) - damage
                            if enemies[0]["hp"] <= 0:
                                ename = enemies[0].get("name", "Enemy")
                                lines.append(f"  -> {ename} slain!")
                                if pop_room and isinstance(pop_room.content, dict):
                                    pop_room.content["enemies"] = [
                                        e for e in pop_room.content.get("enemies", [])
                                        if e.get("hp", 1) > 0
                                    ]
            self._snared_enemies.clear()

        elif combo_key == ("FLASH", "BACKSTAB"):
            # Backstab already does double damage via enemy_blinded context —
            # just confirm the combo visually
            lines.append("  -> Blinded enemy can't defend! Double damage confirmed!")

        elif combo_key == ("FLASH", "SPELLSLOT"):
            # Blinded enemies can't dodge: DC reduced by 3, re-resolve if missed
            lines.append("  -> Blinded target can't dodge! DC -3 for spells.")
            if not result.get("success"):
                char = self.engine.character
                enemy_def = enemies[0].get("defense", 10) if enemies else 11
                new_dc = max(1, enemy_def - 3)
                recheck = char.make_check(StatType.AETHER, new_dc)
                if recheck.success:
                    item = None
                    for _it in char.gear.slots.values():
                        if _it and any("Spellslot" in t for t in _it.special_traits):
                            item = _it
                            break
                    tier = item.tier.value if item else 1
                    damage = sum(random.randint(1, 6) for _ in range(tier))
                    lines.append(f"  -> Arcane exploit! Aether {recheck.total} vs DC {new_dc} — HIT for {damage}!")
                    if enemies:
                        enemies[0]["hp"] = enemies[0].get("hp", 5) - damage
                        if enemies[0]["hp"] <= 0:
                            ename = enemies[0].get("name", "Enemy")
                            lines.append(f"  -> {ename} slain!")
                            if pop_room and isinstance(pop_room.content, dict):
                                pop_room.content["enemies"] = [
                                    e for e in pop_room.content.get("enemies", [])
                                    if e.get("hp", 1) > 0
                                ]
            self._blinded_enemies.clear()

        elif combo_key == ("GUARD", "REFLECT"):
            # Double the reflect damage
            self._reflect_pending *= 2
            lines.append(f"  -> Amber Mirror! Reflect damage doubled to {self._reflect_pending}!")

        elif combo_key == ("CHARGE", "CLEAVE"):
            # Charge momentum carries into cleave splash targets
            bonus = self._pending_bonus_damage
            if bonus > 0:
                lines.append(f"  -> Timber Fall! +{bonus} damage carries into cleave targets!")
                if enemies:
                    for e in enemies[:result.get("cleave_targets", 1)]:
                        e["hp"] = e.get("hp", 5) - bonus
                        ename = e.get("name", "Enemy")
                        lines.append(f"  -> {ename} takes {bonus} momentum damage!")
                        if e["hp"] <= 0:
                            lines.append(f"  -> {ename} slain!")
                    if pop_room and isinstance(pop_room.content, dict):
                        pop_room.content["enemies"] = [
                            e for e in pop_room.content.get("enemies", [])
                            if e.get("hp", 1) > 0
                        ]
                self._pending_bonus_damage = 0

        elif combo_key == ("LIGHT", "REVEAL"):
            # Extended discovery: also reveal in adjacent rooms
            lines.append("  -> Song Echo! Light carries the song, song reveals truth!")
            if self.engine.dungeon_graph:
                room_data = self.engine.get_current_room()
                if room_data:
                    geom = room_data.get("geometry")
                    if geom and hasattr(geom, 'connections'):
                        for conn_id in geom.connections:
                            conn_room = self.engine.dungeon_graph.rooms.get(conn_id)
                            if conn_room:
                                if getattr(conn_room, 'is_secret', False):
                                    conn_room.is_secret = False
                                    rname = conn_room.name if hasattr(conn_room, 'name') else f"Room {conn_id}"
                                    lines.append(f"  -> Distant reveal: {rname}")
                                if hasattr(conn_room, 'connections'):
                                    for far_id in conn_room.connections:
                                        far_room = self.engine.dungeon_graph.rooms.get(far_id)
                                        if far_room and getattr(far_room, 'is_secret', False):
                                            far_room.is_secret = False
                                            fname = far_room.name if hasattr(far_room, 'name') else f"Room {far_id}"
                                            lines.append(f"  -> Distant reveal: {fname}")

        # ── Corrupted Choir Combos ──

        elif combo_key == ("BLIGHTWEB", "CLEAVE"):
            # Blight Crush: +1d6 AND targets gain Blighted
            bonus = random.randint(1, 6)
            lines.append(f"  -> Blight tendrils hold — the wood strikes! +{bonus} combo damage!")
            char = self.engine.character
            char.current_hp = max(0, char.current_hp - 1)
            lines.append("  -> (Blight cost: -1 HP)")
            if enemies:
                for e in enemies[:result.get("cleave_targets", 1)]:
                    e["hp"] = e.get("hp", 5) - bonus
                    ename = e.get("name", "Enemy")
                    lines.append(f"  -> {ename} takes {bonus} blight damage and is Blighted!")
                    if e["hp"] <= 0:
                        lines.append(f"  -> {ename} slain!")
                if pop_room and isinstance(pop_room.content, dict):
                    pop_room.content["enemies"] = [
                        e for e in pop_room.content.get("enemies", [])
                        if e.get("hp", 1) > 0
                    ]
            self._snared_enemies.clear()

        elif combo_key == ("FLASH", "HELLFIRE"):
            # Solar Flare: 2x AoE but hits allies
            lines.append("  -> SOLAR FLARE! Uncontrollable blaze — enemies AND allies caught!")

        elif combo_key == ("ICEWALL", "REFLECT"):
            # Ice Mirror: 3x reflect but -1 DR permanent
            self._reflect_pending *= 3
            lines.append(f"  -> Ice Mirror! Reflect tripled to {self._reflect_pending}!")
            lines.append("  -> WARNING: Your armor cracks. (-1 DR permanent)")
            char = self.engine.character
            # Find an armor piece and reduce its DR
            for _slot, _item in char.gear.slots.items():
                if _item and _item.damage_reduction > 0:
                    _item.damage_reduction = max(0, _item.damage_reduction - 1)
                    lines.append(f"  -> {_item.name} DR reduced to {_item.damage_reduction}.")
                    break

        elif combo_key == ("LIGHT", "CHOIR_CALL"):
            # Choir Pulse: reveals floor but +1 Resonance
            lines.append("  -> Choir Pulse! The changed song echoes through every room!")
            lines.append("  -> Full floor revealed! (+1 Resonance exposure)")
            if self.engine.dungeon_graph:
                for room in self.engine.dungeon_graph.rooms.values():
                    if hasattr(room, 'is_secret'):
                        room.is_secret = False
            self.engine.resonance_exposure = getattr(self.engine, 'resonance_exposure', 0) + 1

        # ── Void Combos ──

        elif combo_key == ("NULLIFY", "WITHER"):
            # Unraveling: Wither's max HP reduction doubled
            lines.append("  -> UNRAVELING! Defenses stripped — the withering cuts twice as deep!")
            # The wither result's max_hp_reduction is already calculated;
            # bridge will apply it doubled when handling wither effect

        elif combo_name == "EVENT HORIZON":
            # Collapse + any AoE: +50% damage to pinned targets
            lines.append("  -> EVENT HORIZON! Everything was already in one place.")
            # The AoE's damage gets a 50% bonus; handled by caller checking combo_name

        return lines

    # ─────────────────────────────────────────────────────────────────────
    # ARCHETYPE BONUS HELPERS (#170)
    # ─────────────────────────────────────────────────────────────────────

    def _get_archetype_bonuses(self) -> dict:
        """Get merged bonus dict from all active archetypes."""
        from codex.games.burnwillow.engine import detect_archetypes
        merged = {}
        for arch_def in detect_archetypes(self.engine.character.gear).values():
            merged.update(arch_def.get("bonus", {}))
        return merged

    # ─────────────────────────────────────────────────────────────────────
    # REACTION SYSTEM — trigger-prompted abilities
    # ─────────────────────────────────────────────────────────────────────

    def _find_reaction_trait(self, trait_id: str) -> bool:
        """Check if any party member has an item with the given reaction trait."""
        for ally in self.engine.party:
            if ally.is_alive():
                for item in ally.gear.slots.values():
                    if item and any(trait_id.lower() in t.lower() for t in item.special_traits):
                        return True
        return False

    def _check_hearthflare(self, attacker_name: str, enemy: dict) -> list[str]:
        """Fire reaction: when you take damage, attacker takes 1d4 fire (1d6 with Embercaller)."""
        lines = []
        if self._find_reaction_trait("Hearthflare"):
            _arch = self._get_archetype_bonuses()
            die_size = 6 if _arch.get("hearthflare_upgrade") else 4
            dmg = random.randint(1, die_size)
            enemy["hp"] = enemy.get("hp", 5) - dmg
            lines.append(f"  HEARTHFLARE! Ember burst sears {attacker_name} for {dmg} fire!")
        elif self._find_reaction_trait("Solflare"):
            # Choir version: 2d6 but hits allies too
            dmg = sum(random.randint(1, 6) for _ in range(2))
            enemy["hp"] = enemy.get("hp", 5) - dmg
            lines.append(f"  SOLFLARE! Uncontrollable blaze — {dmg} fire to {attacker_name}!")
            # Also damages party
            char = self.engine.character
            char.current_hp = max(1, char.current_hp - dmg)
            lines.append(f"  Solflare backlash! You take {dmg} fire too!")
        return lines

    def _check_rootcatch(self, fallen_ally) -> list[str]:
        """Root/Wood reaction: ally at 0 HP stabilizes at 1. Once per encounter."""
        lines = []
        if getattr(self, '_rootcatch_used', False):
            return lines
        if self._find_reaction_trait("Rootcatch"):
            fallen_ally.current_hp = 1
            self._rootcatch_used = True
            lines.append(f"  ROOTCATCH! Roots surge up and catch {fallen_ally.name} at 1 HP!")
        elif self._find_reaction_trait("Blightgrasp"):
            fallen_ally.current_hp = 1
            fallen_ally.add_condition(Condition.BLIGHTED)
            self._rootcatch_used = True
            lines.append(f"  BLIGHTGRASP! Dark roots save {fallen_ally.name}... but Blight seeps in.")
        return lines

    def _check_spore_adaptation(self, char, cond: "Condition", save_stat, save_dc) -> list[str]:
        """Rot reaction: reroll failed poison/Blight save with +2."""
        lines = []
        blight_like = cond in (Condition.BLIGHTED, Condition.POISONED, Condition.SPORE_SICK)
        if not blight_like:
            return lines
        if self._find_reaction_trait("Spore_Adaptation"):
            reroll = roll_dice_pool(char.gear.get_total_dice_bonus(save_stat),
                                    char.get_stat_mod(save_stat) + 2, save_dc)
            if reroll["success"]:
                lines.append(f"  SPORE ADAPTATION! Mycelium metabolizes the toxin. Save succeeded!")
                return lines  # Caller should skip condition application
            lines.append(f"  Spore Adaptation: reroll failed ({reroll['total']} vs DC {save_dc}).")
        elif self._find_reaction_trait("Choir_Resonance"):
            lines.append(f"  CHOIR RESONANCE! The changed song shields you. (+1 Resonance)")
            self.engine.resonance_exposure = getattr(self.engine, 'resonance_exposure', 0) + 1
            return lines  # Auto-succeed, caller skips condition
        return lines

    def _check_harmonic(self, ally, check_result: dict, stat: "StatType", dc: int) -> list[str]:
        """Root-Song reaction: ally fails a check, grant +1d6 retroactive (2d6 with Songweaver)."""
        lines = []
        if check_result.get("success"):
            return lines  # Only triggers on failure
        if self._find_reaction_trait("Harmonic"):
            _arch = self._get_archetype_bonuses()
            dice_count = _arch.get("harmonic_bonus_dice", 1)
            bonus = sum(random.randint(1, 6) for _ in range(dice_count))
            new_total = check_result["total"] + bonus
            if new_total >= dc:
                lines.append(f"  HARMONIC! Your song lifts them. +{bonus} → {new_total} vs DC {dc}: SUCCESS!")
                check_result["success"] = True
                check_result["total"] = new_total
            else:
                lines.append(f"  Harmonic: +{bonus} → {new_total} vs DC {dc}: still short.")
        return lines

    # ─────────────────────────────────────────────────────────────────────
    # ACTIVE GEAR COMBAT COMMANDS (WO-V17.0)
    # ─────────────────────────────────────────────────────────────────────

    def _has_trait(self, tag: str) -> bool:
        """Check if character has any equipped item with the given trait tag."""
        for item in self.engine.character.gear.slots.values():
            if item and tag in item.special_traits:
                return True
        return False

    def _get_trait_item(self, tag: str):
        """Return the equipped item providing a specific tag, or None."""
        for item in self.engine.character.gear.slots.values():
            if item and tag in item.special_traits:
                return item
        return None

    def _cmd_intercept(self) -> str:
        """Defend: set DR bonus for next incoming hit. Requires [Intercept]."""
        if not self._has_trait("[Intercept]"):
            return "You need a shield with [Intercept] to defend.\n" + self._status_line()

        item = self._get_trait_item("[Intercept]")
        tier = item.tier.value if item else 1
        dr_bonus = min(5, tier + 1)  # T1:+2, T2:+3, T3:+4, T4:+5

        char = self.engine.character
        char._intercept_active = True
        char._intercept_dr_bonus = dr_bonus

        # Warden's Watch 3pc: Intercept protects 2 allies (apply DR to first minion/companion too)
        _intercept_set_bonuses = char.gear.get_active_set_bonuses()
        if any(b.get("intercept_targets", 0) >= 2 for b in _intercept_set_bonuses.values()):
            for ally in self.engine.party:
                if ally is not char and ally.is_alive():
                    ally._intercept_active = True
                    ally._intercept_dr_bonus = dr_bonus
                    lines_extra = f"  Warden's Watch: {ally.name} also shielded! (+{dr_bonus} DR)"
                    break
            else:
                lines_extra = None
        else:
            lines_extra = None

        lines = [f"You raise your {item.name}! (+{dr_bonus} DR until next hit)"]
        if lines_extra:
            lines.append(lines_extra)
        if tier >= 4:
            lines.append("  Legendary: melee attackers take 1d6 reflected damage!")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_command(self, arg: str = "") -> str:
        """Command an ally to make a free attack. Requires [Command]."""
        if not self._has_trait("[Command]"):
            return "You need a horn or banner with [Command].\n" + self._status_line()

        item = self._get_trait_item("[Command]")
        tier = item.tier.value if item else 1
        bonus_dmg = max(0, tier - 1)

        char = self.engine.character
        check = roll_dice_pool(
            char.gear.get_total_dice_bonus(StatType.WITS),
            char.get_stat_mod(StatType.WITS), 12
        )

        if not check["success"]:
            return f"Your command falls flat. (Wits {check['total']} vs DC 12: FAIL)\n" + self._status_line()

        # Solo mode: grant self bonus damage on next attack
        lines = [f"You sound the {item.name}! (Wits {check['total']} vs DC 12: SUCCESS)"]
        party = self.engine.get_active_party()
        if len(party) <= 1:
            self._pending_bonus_damage = getattr(self, '_pending_bonus_damage', 0) + 1 + bonus_dmg
            lines.append(f"  Solo: +{1 + bonus_dmg} bonus damage on your next attack!")
        else:
            self._pending_bonus_damage = getattr(self, '_pending_bonus_damage', 0) + bonus_dmg
            lines.append(f"  Your allies rally! +{bonus_dmg} bonus damage on next party attack!")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_bolster(self, arg: str = "") -> str:
        """Empower next roll with bonus dice. Requires [Bolster]."""
        if not self._has_trait("[Bolster]"):
            return "You need a totem with [Bolster] to empower.\n" + self._status_line()

        item = self._get_trait_item("[Bolster]")
        tier = item.tier.value if item else 1
        bonus_dice = min(3, tier)

        char = self.engine.character
        check = roll_dice_pool(
            char.gear.get_total_dice_bonus(StatType.AETHER),
            char.get_stat_mod(StatType.AETHER), 10
        )

        if not check["success"]:
            return f"The Aether slips away. (Aether {check['total']} vs DC 10: FAIL)\n" + self._status_line()

        self._bolster_bonus = getattr(self, '_bolster_bonus', 0) + bonus_dice
        lines = [f"You channel the {item.name}! (Aether {check['total']} vs DC 10: SUCCESS)"]
        lines.append(f"  +{bonus_dice}d6 on your next roll!")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_triage(self, arg: str = "") -> str:
        """Heal with Wits check. Requires [Triage]."""
        if not self._has_trait("[Triage]"):
            return "You need a healer's kit with [Triage].\n" + self._status_line()

        item = self._get_trait_item("[Triage]")
        tier = item.tier.value if item else 1
        heal_dice = min(4, tier)

        char = self.engine.character
        heal_amount = sum(random.randint(1, 6) for _ in range(heal_dice))

        check = roll_dice_pool(
            char.gear.get_total_dice_bonus(StatType.WITS),
            char.get_stat_mod(StatType.WITS), 12
        )

        actual = char.heal(heal_amount)
        lines = []
        if check["success"]:
            lines.append(f"Clean work with {item.name}! (Wits {check['total']} vs DC 12: SUCCESS)")
            lines.append(f"  Healed {actual} HP. (No supplies consumed)")
        else:
            lines.append(f"Messy but effective with {item.name}. (Wits {check['total']} vs DC 12: FAIL)")
            lines.append(f"  Healed {actual} HP. (1 supply charge consumed)")

        lines.append(f"  HP: {char.current_hp}/{char.max_hp}")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_assist(self, arg: str = "") -> str:
        """Help an ally's next check. Grants +1d6 to their pool (max 5d6).

        Uses your action for the round. The bonus applies to the next
        attack or check made by another party member.
        """
        party = self.engine.party if hasattr(self.engine, 'party') else []
        if len(party) < 2:
            return "No allies to assist. You need at least 2 party members.\n" + self._status_line()

        self._assist_pending = True
        char = self.engine.character
        return (
            f"{char.name} readies to assist! (+1d6 to the next ally's check)\n"
            + self._status_line()
        )

    def _cmd_save(self) -> str:
        """Save current game state to disk."""
        try:
            data = self.engine.save_game()
            _SAVES_DIR.mkdir(parents=True, exist_ok=True)
            save_path = _SAVES_DIR / "burnwillow_save.json"
            save_path.write_text(json.dumps(data, indent=2, default=str))
            return f"Game saved.\n{self._status_line()}"
        except Exception as e:
            return f"Save failed: {e}"

    def _cmd_reputation(self) -> str:
        """Show faction reputation standings."""
        lines = ["=== FACTION REPUTATION ===", ""]
        lines.extend(self.engine.faction_rep.get_summary())
        lines.append("")
        lines.append("Opposing factions:")
        lines.append("  Hag Circle <-> Heartwood Elders")
        lines.append("  Canopy Court <-> Dam-Wrights")
        lines.append("  The Hive <-> The Mycelium")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_ingredients(self) -> str:
        """Show gathered alchemy ingredients."""
        char = self.engine.character
        lines = ["=== INGREDIENTS ===", ""]
        if not char.ingredients:
            lines.append("  No ingredients gathered yet.")
            lines.append("  (Search rooms and defeat enemies to find ingredients.)")
        else:
            for name, count in sorted(char.ingredients.items()):
                lines.append(f"  {name}: {count}")
        if char.potions:
            lines.append(f"\nPotions ({len(char.potions)}):")
            for p in char.potions:
                lines.append(f"  {p['name']}: {p['effect']}")
        if char.bombs:
            lines.append(f"\nBombs ({len(char.bombs)}/3):")
            for b in char.bombs:
                lines.append(f"  {b['name']}: {b['effect']}")
        if char.oils:
            lines.append(f"\nOils ({len(char.oils)}):")
            for o in char.oils:
                lines.append(f"  {o['name']}: {o['effect']}")
        if char.elixirs:
            lines.append(f"\nElixirs ({len(char.elixirs)}):")
            for e in char.elixirs:
                lines.append(f"  {e['name']}: {e['effect']}")
        if char.active_oil:
            lines.append(f"\nActive Coating: {char.active_oil['name']}")
        if char.active_elixir:
            lines.append(f"Active Elixir: {char.active_elixir['name']}")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_craft(self, arg: str = "") -> str:
        """Craft an alchemy recipe."""
        if not arg.strip():
            return "Craft what? Usage: craft <recipe name>\n" + self._status_line()
        from codex.games.burnwillow.engine import craft_recipe
        char = self.engine.character
        result = craft_recipe(arg.strip(), char)
        lines = [result["message"]]
        if result["success"] and result["item"]:
            item = result["item"]
            lines.append(f"  Type: {item['type']}")
            lines.append(f"  Effect: {item['effect']}")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_recipes(self) -> str:
        """Show known alchemy recipes."""
        char = self.engine.character
        from codex.games.burnwillow.engine import get_all_recipes
        all_recipes = get_all_recipes()
        lines = ["=== KNOWN RECIPES ===", ""]
        if not char.known_recipes:
            lines.append("  No recipes discovered yet.")
            lines.append("  (Find recipes in secret rooms, faction vendors, or Memory Seeds.)")
        else:
            for r in all_recipes:
                if r["name"] in char.known_recipes:
                    ings = " + ".join(r["ingredients"])
                    lines.append(f"  {r['name']} [{r['type']}]")
                    lines.append(f"    Ingredients: {ings}")
                    lines.append(f"    Effect: {r['effect']}")
                    lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_enter(self, arg: str = "") -> str:
        """Enter a discovered hidden passage to the Heartwood or Undergrove."""
        room = self.engine.get_current_room()

        # Check if we're standing on a portal
        if room and room.get("portal_destination"):
            dest = room["portal_destination"]
            zone_num = room["portal_zone"]
            if not arg.strip() or arg.strip().lower() == dest:
                # Zone switch
                new_seed = random.randint(0, 999999)
                self.engine._discovered_entrances.add(dest)
                self.engine.generate_dungeon(depth=4, seed=new_seed, zone=zone_num)
                lines = [
                    f"You cross the threshold into the {dest.replace('_', ' ').title()}...",
                    "",
                ]
                lines.append(self._cmd_look())
                return "\n".join(lines)
            else:
                return f"The passage leads to the {dest.replace('_', ' ').title()}, not '{arg}'.\n" + self._status_line()

        # Check if using from Emberhome (already discovered)
        arg_clean = arg.strip().lower()
        if arg_clean in self.engine._discovered_entrances:
            zone_map = {"heartwood": 6, "undergrove": 7}
            zone_num = zone_map.get(arg_clean)
            if zone_num:
                new_seed = random.randint(0, 999999)
                self.engine.generate_dungeon(depth=4, seed=new_seed, zone=zone_num)
                lines = [
                    f"You cross the threshold into the {arg_clean.replace('_', ' ').title()}...",
                    "",
                ]
                lines.append(self._cmd_look())
                return "\n".join(lines)

        if not self.engine._discovered_entrances:
            return "You haven't discovered any hidden passages yet.\n" + self._status_line()

        discovered = ", ".join(sorted(self.engine._discovered_entrances))
        return f"Enter where? Discovered passages: {discovered}\n" + self._status_line()

    def _cmd_forge(self) -> str:
        """Show available crafting station actions."""
        lines = ["=== CRAFTING STATIONS ===", ""]
        fr = self.engine.faction_rep

        lines.append("BLACKSMITH (always available):")
        lines.append("  salvage <item>  — Break into materials")
        lines.append("  temper <item>   — Add +1 DR (max 2 per item)")
        lines.append("  reforge <item> <slot> — Change equipment slot")
        lines.append("")

        if fr.can_access_services("canopy_court"):
            lines.append("SILKWEAVER (Canopy Court — Friendly+):")
            lines.append("  enchant <item>  — Add random Aether affix")
            lines.append("")
        else:
            lines.append("SILKWEAVER — Locked (need Canopy Court Friendly)")
            lines.append("")

        if fr.can_access_services("hag_circle"):
            lines.append("HAG'S CAULDRON (Hag Circle — Friendly+):")
            lines.append("  craft <recipe>  — Brew alchemy recipes")
            lines.append("  (Use 'rot_process' during NPC talk for Rot Processing)")
            lines.append("")
        else:
            lines.append("HAG'S CAULDRON — Locked (need Hag Circle Friendly)")
            lines.append("")

        if fr.can_access_services("mycelium"):
            lines.append("MYCELIUM FORGE (Mycelium — Friendly+):")
            lines.append("  (Use 'decompose' during NPC talk for better salvage)")
            lines.append("  (Use 'spore_infuse' during NPC talk for living gear)")
            lines.append("")
        else:
            lines.append("MYCELIUM FORGE — Locked (need Mycelium Friendly)")
            lines.append("")

        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_salvage(self, arg: str = "") -> str:
        """Salvage an item for materials."""
        if not arg.strip():
            return "Salvage what? Usage: salvage <item name>\n" + self._status_line()
        char = self.engine.character
        # Find item in inventory
        target = None
        target_idx = None
        for idx, item in char.inventory.items():
            if arg.strip().lower() in item.name.lower():
                target = item
                target_idx = idx
                break
        if not target:
            return f"No item named '{arg}' in inventory.\n" + self._status_line()

        from codex.games.burnwillow.engine import blacksmith_salvage
        result = blacksmith_salvage(target)
        lines = [result["message"]]
        if result["success"]:
            # Remove item from inventory
            del char.inventory[target_idx]
            # Add materials
            for mat_name, mat_count in result.get("materials", {}).items():
                char.ingredients[mat_name] = char.ingredients.get(mat_name, 0) + mat_count
                lines.append(f"  +{mat_count} {mat_name}")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_temper(self, arg: str = "") -> str:
        """Temper an equipped armor piece for +1 DR."""
        if not arg.strip():
            return "Temper what? Usage: temper <item name>\n" + self._status_line()
        char = self.engine.character
        # Find in equipped gear
        target = None
        for slot, item in char.gear.slots.items():
            if item and arg.strip().lower() in item.name.lower():
                target = item
                break
        if not target:
            return f"No equipped item named '{arg}'.\n" + self._status_line()
        if char.scrap < 5:
            return f"Need 5 scrap to temper. You have {char.scrap}.\n" + self._status_line()

        from codex.games.burnwillow.engine import blacksmith_temper
        result = blacksmith_temper(target)
        if result["success"]:
            char.scrap -= 5
        lines = [result["message"]]
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_reforge(self, arg: str = "") -> str:
        """Reforge an item to change its slot."""
        parts = arg.strip().split()
        if len(parts) < 2:
            return "Usage: reforge <item name> <new slot>\nSlots: R.Hand, L.Hand, Head, Arms, Chest, Legs, Shoulders, Neck, R.Ring, L.Ring\n" + self._status_line()

        new_slot_name = parts[-1]
        item_name = " ".join(parts[:-1]).lower()

        # Validate slot
        try:
            new_slot = GearSlot(new_slot_name)
        except ValueError:
            return f"Invalid slot: {new_slot_name}. Valid: R.Hand, L.Hand, Head, Arms, Chest, Legs, Shoulders, Neck, R.Ring, L.Ring\n" + self._status_line()

        char = self.engine.character
        target = None
        target_idx = None
        for idx, item in char.inventory.items():
            if item_name in item.name.lower():
                target = item
                target_idx = idx
                break
        if not target:
            return f"No item named '{item_name}' in inventory.\n" + self._status_line()
        if char.scrap < 5:
            return f"Need 5 scrap to reforge. You have {char.scrap}.\n" + self._status_line()

        from codex.games.burnwillow.engine import blacksmith_reforge
        result = blacksmith_reforge(target, new_slot)
        if result["success"]:
            char.scrap -= 5
        lines = [result["message"]]
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_enchant(self, arg: str = "") -> str:
        """Enchant an item with an Aether affix (Silkweaver station)."""
        if not self.engine.faction_rep.can_access_services("canopy_court"):
            return "The Silkweaver is unavailable. (Need Canopy Court Friendly+)\n" + self._status_line()
        if not arg.strip():
            return "Enchant what? Usage: enchant <item name>\n" + self._status_line()

        char = self.engine.character
        target = None
        for slot, item in char.gear.slots.items():
            if item and arg.strip().lower() in item.name.lower():
                target = item
                break
        if not target:
            for idx, item in char.inventory.items():
                if arg.strip().lower() in item.name.lower():
                    target = item
                    break
        if not target:
            return f"No item named '{arg}'.\n" + self._status_line()

        from codex.games.burnwillow.engine import silkweaver_enchant
        result = silkweaver_enchant(target)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("canopy_court", 1))
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_heal(self) -> str:
        """Hive honey healing (costs 5 amber, requires Hive Friendly+)."""
        if not self.engine.faction_rep.can_access_services("hive"):
            return "Hive healing unavailable. (Need Hive Friendly+)\n" + self._status_line()
        from codex.games.burnwillow.engine import hive_honey_heal
        result = hive_honey_heal(self.engine.character)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("hive", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_reinforce(self, arg: str = "") -> str:
        """Dam-Wright gear reinforcement (+1 DR, requires Dam-Wright Friendly+)."""
        if not self.engine.faction_rep.can_access_services("dam_wrights"):
            return "Dam-Wright reinforcement unavailable. (Need Dam-Wright Friendly+)\n" + self._status_line()
        if not arg.strip():
            return "Reinforce what? Usage: reinforce <item name>\n" + self._status_line()
        char = self.engine.character
        target = None
        for slot, item in char.gear.slots.items():
            if item and arg.strip().lower() in item.name.lower():
                target = item
                break
        if not target:
            return f"No equipped item named '{arg}'.\n" + self._status_line()
        from codex.games.burnwillow.engine import dam_wright_reinforce
        result = dam_wright_reinforce(target)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("dam_wrights", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_process(self) -> str:
        """Hag Rot processing (2 Rot Spores → Moonstone Dust + Deepwater, requires Hag Circle Friendly+)."""
        if not self.engine.faction_rep.can_access_services("hag_circle"):
            return "Hag's Rot processing unavailable. (Need Hag Circle Friendly+)\n" + self._status_line()
        from codex.games.burnwillow.engine import hag_rot_process
        result = hag_rot_process(self.engine.character)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("hag_circle", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_graft(self, arg: str = "") -> str:
        """Heartwood grafting — permanently fuse gear, +1 tier (requires Heartwood Allied+)."""
        if not self.engine.faction_rep.can_access_gear("heartwood_elders"):
            return "Heartwood grafting unavailable. (Need Heartwood Elders Allied+)\n" + self._status_line()
        if not arg.strip():
            return "Graft what? Usage: graft <item name>\n  WARNING: Item cannot be unequipped after grafting!\n" + self._status_line()
        char = self.engine.character
        target = None
        target_slot = None
        for slot, item in char.gear.slots.items():
            if item and arg.strip().lower() in item.name.lower():
                target = item
                target_slot = slot
                break
        if not target:
            return f"No equipped item named '{arg}'.\n" + self._status_line()
        from codex.games.burnwillow.engine import heartwood_graft
        result = heartwood_graft(char, target, target_slot)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("heartwood_elders", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_curse(self, arg: str = "") -> str:
        """Hag curse weapon — apply debuff prefix (requires Hag Circle Friendly+)."""
        if not self.engine.faction_rep.can_access_services("hag_circle"):
            return "Hag curse unavailable. (Need Hag Circle Friendly+)\n" + self._status_line()
        if not arg.strip():
            return "Curse what? Usage: curse <item name>\n" + self._status_line()
        char = self.engine.character
        target = None
        for slot, item in char.gear.slots.items():
            if item and arg.strip().lower() in item.name.lower():
                target = item
                break
        if not target:
            return f"No equipped item named '{arg}'.\n" + self._status_line()
        from codex.games.burnwillow.engine import hag_curse_weapon
        result = hag_curse_weapon(target)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("hag_circle", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_threadbind(self, arg: str = "") -> str:
        """Canopy thread binding — link two items to a gear set (requires Canopy Court Allied+)."""
        if not self.engine.faction_rep.can_access_gear("canopy_court"):
            return "Thread binding unavailable. (Need Canopy Court Allied+)\n" + self._status_line()
        parts = arg.strip().split()
        if len(parts) < 3:
            return "Usage: threadbind <item1> <item2> <set_id>\n  Sets: arborist_legacy, wardens_watch, rot_hunter_trophy, moonstone_circle, shadowweave\n" + self._status_line()
        set_id = parts[-1].lower()
        item_search = " ".join(parts[:-1])
        char = self.engine.character
        found = []
        for slot, item in char.gear.slots.items():
            if item and any(s in item.name.lower() for s in item_search.lower().split()):
                found.append(item)
        if len(found) < 2:
            return f"Need 2 equipped items matching search. Found {len(found)}.\n" + self._status_line()
        from codex.games.burnwillow.engine import silkweaver_thread_bind
        result = silkweaver_thread_bind(found[0], found[1], set_id)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("canopy_court", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_decompose(self, arg: str = "") -> str:
        """Mycelium decomposition — break item for better yield (requires Mycelium Friendly+)."""
        if not self.engine.faction_rep.can_access_services("mycelium"):
            return "Mycelium decomposition unavailable. (Need Mycelium Friendly+)\n" + self._status_line()
        if not arg.strip():
            return "Decompose what? Usage: decompose <item name>\n" + self._status_line()
        char = self.engine.character
        target = None
        target_idx = None
        for idx, item in char.inventory.items():
            if arg.strip().lower() in item.name.lower():
                target = item
                target_idx = idx
                break
        if not target:
            return f"No item named '{arg}' in inventory.\n" + self._status_line()
        from codex.games.burnwillow.engine import mycelium_decompose
        result = mycelium_decompose(target)
        lines = [result["message"]]
        if result.get("success"):
            char.remove_from_inventory(target_idx)
            # Add materials after delay (simplified: immediate for now)
            for mat, count in result.get("materials", {}).items():
                char.ingredients[mat] = char.ingredients.get(mat, 0) + count
                lines.append(f"  +{count} {mat}")
            lines.extend(self.engine.faction_rep.change_rep("mycelium", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_infuse(self, arg: str = "") -> str:
        """Mycelium spore infusion — add living quality (requires Mycelium Allied+)."""
        if not self.engine.faction_rep.can_access_gear("mycelium"):
            return "Spore infusion unavailable. (Need Mycelium Allied+)\n" + self._status_line()
        if not arg.strip():
            return "Infuse what? Usage: infuse <item name>\n" + self._status_line()
        char = self.engine.character
        target = None
        for slot, item in char.gear.slots.items():
            if item and arg.strip().lower() in item.name.lower():
                target = item
                break
        if not target:
            return f"No equipped item named '{arg}'.\n" + self._status_line()
        from codex.games.burnwillow.engine import mycelium_spore_infuse
        result = mycelium_spore_infuse(target)
        lines = [result["message"]]
        if result.get("success"):
            lines.extend(self.engine.faction_rep.change_rep("mycelium", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_netgraft(self, arg: str = "") -> str:
        """Mycelium network graft — item survives death (requires Mycelium Exalted)."""
        if not self.engine.faction_rep.has_capstone("mycelium"):
            return "Network grafting unavailable. (Need Mycelium Exalted)\n" + self._status_line()
        if not arg.strip():
            return "Network graft what? Usage: netgraft <item name>\n" + self._status_line()
        char = self.engine.character
        target = None
        for slot, item in char.gear.slots.items():
            if item and arg.strip().lower() in item.name.lower():
                target = item
                break
        if not target:
            return f"No equipped item named '{arg}'.\n" + self._status_line()
        from codex.games.burnwillow.engine import mycelium_network_graft
        result = mycelium_network_graft(target)
        lines = [result["message"]]
        if result.get("success"):
            # Store grafted item name in meta_state for persistence across death
            if hasattr(self.engine, 'meta_state'):
                grafted = self.engine.meta_state.setdefault("grafted_items", [])
                if target.name not in grafted:
                    grafted.append(target.name)
            lines.extend(self.engine.faction_rep.change_rep("mycelium", 1))
        return "\n".join(lines) + "\n" + self._status_line()

    def _cmd_deposit(self, arg: str = "") -> str:
        """Deposit an item into the Still Pool (max 2, Willow Wood only)."""
        if len(self.engine.still_pool_items) >= 2:
            return "The Still Pool holds only 2 items. It is full.\n" + self._status_line()
        if not arg.strip():
            if self.engine.still_pool_items:
                lines = ["=== THE STILL POOL ===", ""]
                for i, item_dict in enumerate(self.engine.still_pool_items):
                    lines.append(f"  [{i}] {item_dict.get('name', '?')} (Tier {item_dict.get('tier', '?')})")
                lines.append(f"\n  {2 - len(self.engine.still_pool_items)} slot(s) remaining.")
            else:
                lines = ["The Still Pool is empty. Its surface is perfectly still."]
            lines.append("\nUsage: deposit <item name>")
            lines.append(self._status_line())
            return "\n".join(lines)
        char = self.engine.character
        target = None
        target_idx = None
        for idx, item in char.inventory.items():
            if arg.strip().lower() in item.name.lower():
                target = item
                target_idx = idx
                break
        if not target:
            return f"No item named '{arg}' in inventory.\n" + self._status_line()
        # Deposit
        item_dict = target.to_dict()
        self.engine.still_pool_items.append(item_dict)
        del char.inventory[target_idx]
        lines = [
            "You wade into the Still Pool. The water is warm.",
            f"You hold {target.name} beneath the surface and let go.",
            "It does not sink. It suspends, rotating slowly, as amber grows around it.",
            "Your hand comes back dry. The item is part of the tree's memory now.",
            f"\nDeposited: {target.name}",
            f"Still Pool: {len(self.engine.still_pool_items)}/2 items stored.",
        ]
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_retrieve(self, arg: str = "") -> str:
        """Retrieve an item from the Still Pool (costs 1 Doom)."""
        if not self.engine.still_pool_items:
            return "The Still Pool is empty.\n" + self._status_line()
        if not arg.strip():
            lines = ["=== THE STILL POOL ===", ""]
            for i, item_dict in enumerate(self.engine.still_pool_items):
                lines.append(f"  [{i}] {item_dict.get('name', '?')} (Tier {item_dict.get('tier', '?')})")
            lines.append("\nUsage: retrieve <index or name>  (costs 1 Doom)")
            lines.append(self._status_line())
            return "\n".join(lines)
        # Find the item
        target_idx = None
        try:
            target_idx = int(arg.strip())
        except ValueError:
            for i, item_dict in enumerate(self.engine.still_pool_items):
                if arg.strip().lower() in item_dict.get("name", "").lower():
                    target_idx = i
                    break
        if target_idx is None or target_idx >= len(self.engine.still_pool_items):
            return f"No item at index '{arg}'.\n" + self._status_line()
        item_dict = self.engine.still_pool_items.pop(target_idx)
        # Add to inventory
        from codex.games.burnwillow.engine import GearItem
        item = GearItem.from_dict(item_dict)
        char = self.engine.character
        inv_id = char._next_inv_id
        char.inventory[inv_id] = item
        char._next_inv_id += 1
        # Cost: 1 Doom
        self.engine.advance_doom(1)
        lines = [
            "You reach into the Still Pool. A faint golden glow beneath the surface.",
            f"The amber releases {item.name} into your hands.",
            "For a moment you feel the previous wielder — a flash of who held this.",
            f"\nRetrieved: {item.name}  (Doom +1)",
            f"Still Pool: {len(self.engine.still_pool_items)}/2 items stored.",
        ]
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_claim(self, arg: str = "") -> str:
        """Claim a cleared vault room as an outpost."""
        room = self.engine.get_current_room()
        if not room:
            return "No active room.\n" + self._status_line()
        # Check if room is a vault-type (treasure or hidden_portal that's been cleared)
        room_type = room.get("type", "")
        enemies = room.get("enemies", [])
        if enemies:
            return "Clear the room first! Enemies remain.\n" + self._status_line()
        if room_type not in ("treasure", "hidden_portal", "secret", "chamber"):
            return "This room cannot be claimed as an outpost.\n" + self._status_line()
        valid_types = ["bank", "rest", "crafting", "faction", "signal"]
        if not arg.strip() or arg.strip().lower() not in valid_types:
            lines = ["Claim this vault as an outpost. Choose a type:", ""]
            lines.append("  bank     — Secure item storage (1 item per player)")
            lines.append("  rest     — Safe rest room (no Doom advance, once per run)")
            lines.append("  crafting — Field blacksmith (salvage/temper/reforge)")
            lines.append("  faction  — Faction contact point (services mid-dungeon)")
            lines.append("  signal   — Scout tower (reveal adjacent room layouts)")
            lines.append(f"\nUsage: claim <type>")
            lines.append(self._status_line())
            return "\n".join(lines)
        outpost_type = arg.strip().lower()
        room_id = self.engine.current_room_id
        outpost_id = f"outpost_{room_id}"
        self.engine.claimed_outposts[outpost_id] = {
            "type": outpost_type,
            "room_id": room_id,
            "zone": getattr(self.engine, '_zone', 1),
            "items": [],
        }
        type_names = {"bank": "Bank Vault", "rest": "Rest Station", "crafting": "Crafting Annex",
                      "faction": "Faction Post", "signal": "Signal Tower"}
        lines = [
            "The vault's golem reactivates. Its head lifts. It hums — a question.",
            f"You assign function: {type_names.get(outpost_type, outpost_type)}.",
            "The golem nods. The vault is yours.",
            f"\nOutpost claimed: {type_names.get(outpost_type)} (Room {room_id})",
        ]
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _cmd_help(self) -> str:
        """List available commands."""
        return (
            "=== COMMANDS ===\n"
            "--- Movement ---\n"
            "n/s/e/w         - Move one tile (cardinal)\n"
            "ne/nw/se/sw     - Move one tile (diagonal)\n"
            "move <id> (go)  - Move to a connected room\n"
            "look (l)        - Describe current room\n"
            "map             - Show mini-map\n"
            "--- Combat ---\n"
            "attack (a)      - Fight first enemy\n"
            "intercept (int) - Defend: +DR until next hit [Intercept]\n"
            "command (cmd)   - Order bonus attack [Command]\n"
            "bolster (buff)  - Empower next roll [Bolster]\n"
            "triage (medic)  - Heal with Wits check [Triage]\n"
            "rest (heal)     - Heal ~50% HP (+1 Doom)\n"
            "--- Interaction ---\n"
            "talk <npc>      - Talk to an NPC (bye to end)\n"
            "--- Exploration ---\n"
            "search (s)      - Search for loot (+1 Doom)\n"
            "loot            - Pick up items\n"
            "drop <name>     - Drop an item\n"
            "use <item>      - Activate item's special trait\n"
            "push <name> <dir> - Push furniture (8-way)\n"
            "stats (st)      - Show character stats\n"
            "inventory (i)   - Show equipped gear\n"
            "save            - Save current game\n"
            "recap           - Session recap (kills, loot, rooms)\n"
            "help (?)        - This message\n"
            "\n"
            + self._status_line()
        )

    # ─────────────────────────────────────────────────────────────────────
    # FORMATTERS
    # ─────────────────────────────────────────────────────────────────────

    def _status_line(self) -> str:
        """HP/Doom/Room status bar."""
        char = self.engine.character
        room = self.engine.get_current_room()
        room_name = room["type"].capitalize() if room else "?"
        total = len(self.engine.dungeon_graph.rooms) if self.engine.dungeon_graph else 0
        visited = len(self.engine.visited_rooms)
        return (
            f"HP: {char.current_hp}/{char.max_hp} | "
            f"Doom: {self.engine.doom_clock.current}/20 | "
            f"Room: {room_name} | "
            f"Explored: {visited}/{total}"
        )

    def _render_minimap(self) -> str:
        """Render a 7x7 graph-topology mini-map (delegates to canonical renderer)."""
        if not self.engine.dungeon_graph:
            return "(no map)"
        mm_rooms = rooms_to_minimap_dict(self.engine.dungeon_graph)
        doom = self.engine.doom_clock.current if hasattr(self.engine, 'doom_clock') else None
        return render_mini_map(
            mm_rooms, self.engine.current_room_id, self.engine.visited_rooms,
            rich_mode=False, doom=doom,
        )

    # ─────────────────────────────────────────────────────────────────────
    # SESSION CHRONICLE (WO-V37.0)
    # ─────────────────────────────────────────────────────────────────────

    def _log_event(self, event_type: str, **kwargs):
        """Append a structured event to the bridge session log."""
        self._session_log.append({"type": event_type, **kwargs})

    def _loom_shard(self, content: str, shard_type: str = "CHRONICLE"):
        """WO-V79.0: Create a narrative loom shard if the engine supports it."""
        if hasattr(self.engine, '_add_shard'):
            try:
                self.engine._add_shard(content, shard_type)
            except Exception:
                pass

    def _build_engine_snapshot(self) -> dict:
        """Build engine state snapshot for recap."""
        party = []
        if self.engine.party:
            for c in self.engine.party:
                party.append({"name": c.name, "hp": c.current_hp, "max_hp": c.max_hp})
        elif self.engine.character:
            c = self.engine.character
            party.append({"name": c.name, "hp": c.current_hp, "max_hp": c.max_hp})
        return {
            "party": party,
            "doom": self.engine.doom_clock.current if hasattr(self.engine, 'doom_clock') else 0,
            "turns": len(self._session_log),
            "chapter": 1,
            "completed_quests": [],
        }

    def get_session_stats(self) -> dict:
        """Collect session statistics for recap display (WO-V37.0)."""
        from codex.core.services.narrative_loom import format_session_stats
        return format_session_stats(self._session_log, self._build_engine_snapshot())

    def _cmd_talk(self, arg: str = "") -> str:
        """Talk to an NPC in the current room."""
        room = self.engine.get_current_room()
        if not room:
            return "ERROR: No dungeon loaded."

        npcs = room.get("npcs", [])
        if not npcs:
            return f"No one to talk to here.\n{self._status_line()}"

        arg = arg.strip()
        if not arg:
            lines = ["NPCs in this room:"]
            for npc in npcs:
                if isinstance(npc, dict):
                    name = npc.get("name", "Unknown")
                    role = npc.get("npc_type", npc.get("role", ""))
                    role_str = f" ({role})" if role else ""
                    lines.append(f"  * {name}{role_str}")
            lines.append("")
            lines.append("Usage: talk <npc name>")
            lines.append(self._status_line())
            return "\n".join(lines)

        target = arg.lower()
        for npc in npcs:
            if isinstance(npc, dict):
                name = npc.get("name", "Unknown")
                if target in name.lower():
                    lines = [f"=== {name} ==="]
                    role = npc.get("npc_type", npc.get("role", ""))
                    if role:
                        lines.append(f"Role: {role}")
                    dialogue = npc.get("dialogue", "")
                    if dialogue:
                        lines.append(f'"{dialogue}"')
                    else:
                        lines.append(f"{name} has nothing to say.")
                    # Enter conversation mode
                    self._talking_to = name
                    self._talking_to_npc = npc
                    lines.append("")
                    lines.append("You are now talking to "
                                 f"{name}. Type freely to chat, 'bye' to end.")
                    # Faction services — gated by reputation
                    npc_faction = npc.get("faction", "")
                    if npc_faction and npc_faction in self.engine.faction_rep.reputation:
                        from codex.games.burnwillow.engine import FACTION_SERVICES
                        faction_def = FACTION_SERVICES.get(npc_faction)
                        if faction_def:
                            rep_tier = self.engine.faction_rep.get_tier(npc_faction)
                            tier_name = self.engine.faction_rep.get_tier_name(npc_faction)
                            lines.append(f"\n[{faction_def['name']} — {tier_name} ({rep_tier:+d})]")
                            has_services = False
                            for req_tier in sorted(faction_def["services"].keys()):
                                for svc in faction_def["services"][req_tier]:
                                    if rep_tier >= req_tier:
                                        lines.append(f"  [*] {svc['name']}: {svc['desc']}")
                                        has_services = True
                                    else:
                                        tier_needed = self.engine.faction_rep.TIER_NAMES.get(req_tier, "?")
                                        lines.append(f"  [X] {svc['name']} (requires {tier_needed})")
                            if not has_services:
                                lines.append(f"  (Improve reputation to unlock services.)")
                    # Offer trade if merchant
                    if npc.get("npc_type") == "merchant":
                        trade_tier = npc.get("trade_tier", 1)
                        lines.append(f"[Trade tier: {trade_tier}]")
                    # Offer quest if quest_giver and narrator available
                    if self._narrator and npc.get("npc_type") in ("quest_giver", "quest_hook"):
                        _quest = self._narrator.generate_quest_hook(
                            tier=room.get("tier", 1), npc_name=name)
                        if _quest:
                            lines.append("")
                            lines.append(f"[QUEST] {_quest['title']}")
                            lines.append(f"  {_quest['description']}")
                            lines.append(f"  Reward: {_quest['reward']}")
                    lines.append(self._status_line())
                    return "\n".join(lines)

        return f"No NPC named '{arg}' here.\n{self._status_line()}"

    def _cmd_npc_dialogue(self, player_input: str) -> str:
        """Route free-form input to Mimir for NPC dialogue."""
        npc_name = self._talking_to
        if not npc_name:
            return f"You're not talking to anyone.\n{self._status_line()}"

        npc_data = self._talking_to_npc or {}
        room = self.engine.get_current_room()
        room_desc = room.get("description", "") if room else ""

        try:
            from codex.core.services.narrative_frame import query_npc_dialogue
            response = query_npc_dialogue(
                npc_name, player_input, npc_data,
                room_desc=room_desc, setting_id="burnwillow",
            )
            if response:
                return f'{npc_name}: "{response}"\n\n{self._status_line()}'
        except Exception:
            pass

        # Fallback to static dialogue
        dialogue = npc_data.get("dialogue", "")
        if dialogue:
            return f'{npc_name}: "{dialogue}"\n\n{self._status_line()}'
        return f"{npc_name} has nothing more to say.\n{self._status_line()}"

    def _cmd_tutorial(self) -> str:
        """Show tutorial content for Burnwillow."""
        try:
            from codex.core.services.tutorial import TutorialRegistry
            registry = TutorialRegistry()
            modules = registry.get_modules(category="burnwillow")
            if modules:
                lines = ["=== TUTORIAL ==="]
                for mod in modules:
                    lines.append(f"  {mod.title}")
                    if mod.description:
                        lines.append(f"    {mod.description}")
                return "\n".join(lines)
        except (ImportError, Exception):
            pass
        # Fallback: quick-start command reference
        return (
            "=== BURNWILLOW QUICK START ===\n"
            "1. look (l)        — See your surroundings\n"
            "2. n/s/e/w         — Move on the grid\n"
            "3. attack (a)      — Fight enemies\n"
            "4. search (s)      — Find loot (+1 Doom)\n"
            "5. loot            — Pick up items\n"
            "6. use <item>      — Activate gear traits\n"
            "7. rest short/long — Heal up\n"
            "8. map             — View the dungeon\n"
            "9. stats (st)      — Check your character\n"
            "10. save           — Save your progress\n"
            "\nTip: Doom rises as you explore. Reach the boss before it hits 20!"
        )

    def _cmd_recap(self) -> str:
        """Show session recap with narrative thread."""
        from codex.core.services.narrative_loom import summarize_session
        recap = summarize_session(self._session_log, self._build_engine_snapshot())

        # WO-V79.0: Append loom shards if available
        shards = getattr(self.engine, '_memory_shards', [])
        if shards:
            recap += "\n\n--- Narrative Thread ---"
            for s in shards[-10:]:
                _type = s.shard_type.value if hasattr(s.shard_type, 'value') else str(s.shard_type)
                recap += f"\n  [{_type}] {s.content}"
            if len(shards) > 10:
                recap += f"\n  ... and {len(shards) - 10} earlier entries"

        return recap


# =============================================================================
# STANDALONE SMOKE TEST
# =============================================================================

if __name__ == "__main__":
    b = BurnwillowBridge("TestHero", seed=42)
    print(b.step("look"))
    print("---")
    print(b.step("map"))
    print("---")
    print(b.step("stats"))
    print("---")
    print(b.step("help"))
    print("---")
    exits = b.engine.get_connected_rooms()
    if exits:
        print(b.step(f"move {exits[0]['id']}"))
    print("---")
    print(b.step("inventory"))
    print("\nBRIDGE SMOKE TEST: PASS")

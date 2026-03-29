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
    roll_dice_pool, passive_check
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

        # Ambush check
        if enemies:
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

        # Check for assist from ally
        _assisted = getattr(self, '_assist_pending', False)
        if _assisted:
            self._assist_pending = False

        # Passive threshold: auto-hit weak enemies
        if passive_check(might_mod, enemy_defense):
            result = {"success": True, "total": might_mod + 1, "rolls": [], "modifier": might_mod, "dc": enemy_defense, "crit": False, "fumble": False}
            lines.append(f"Your gear outclasses {enemy_name}. (Auto-hit)")
        else:
            result = roll_dice_pool(dice_count, might_mod, enemy_defense, assist=_assisted)

        if result["success"]:
            # Deal damage based on weapon tier
            weapon = char.gear.slots.get(GearSlot.R_HAND)
            damage = weapon.tier.value + 1 if weapon else 1

            # Apply CHARGE bonus damage if pending
            bonus = getattr(self, '_pending_bonus_damage', 0)
            if bonus:
                damage += bonus
                self._pending_bonus_damage = 0

            enemy_hp -= damage

            # Affix: Blazing — +1d4 fire damage on hit
            if weapon and weapon.prefix == "Blazing":
                fire_dmg = random.randint(1, 4)
                enemy_hp -= fire_dmg
                lines.append(f"  Blazing! +{fire_dmg} fire damage.")

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
                # Check for Intercept DR bonus (WO-V17.0)
                intercept_dr = getattr(char, '_intercept_dr_bonus', 0) if getattr(char, '_intercept_active', False) else 0
                raw_damage = enemy_damage if isinstance(enemy_damage, int) else 3
                effective_damage = max(1, raw_damage - char.gear.get_total_dr() - intercept_dr)
                char.current_hp = max(0, char.current_hp - effective_damage)
                if intercept_dr:
                    char._intercept_active = False
                    char._intercept_dr_bonus = 0
                    lines.append(f"{enemy_name} strikes! Your shield absorbs the blow! (-{intercept_dr} DR bonus) {effective_damage} damage taken.")
                else:
                    lines.append(f"{enemy_name} strikes you for {effective_damage} damage!")
                    # Affix: Thorns — reflect 1 damage on hit
                    for _slot_item in char.gear.slots.values():
                        if _slot_item and _slot_item.suffix == "of Thorns":
                            enemy_hp -= 1
                            lines.append(f"  Thorns reflect 1 damage back!")
                            break
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
                        # Check for a DC save if mentioned (e.g., "DC 11 Grit")
                        import re
                        dc_match = re.search(r'DC\s*(\d+)\s*(Might|Wits|Grit|Aether)', enemy_special)
                        if dc_match:
                            save_dc = int(dc_match.group(1))
                            save_stat = StatType(dc_match.group(2).upper())
                            save_mod = char.get_stat_mod(save_stat)
                            save_roll = roll_dice_pool(char.gear.get_total_dice_bonus(save_stat), save_mod, save_dc)
                            if not save_roll["success"]:
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

        # Check death
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

        lines = [result.summary()]

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
        """Show character stats."""
        char = self.engine.character
        lines = [
            f"=== {char.name} ===",
            f"HP: {char.current_hp}/{char.max_hp}",
            f"Defense: {char.get_defense()} | DR: {char.gear.get_total_dr()}",
            "",
            f"MIGHT:  {char.might:>2} ({char.get_stat_mod(StatType.MIGHT):+d})",
            f"WITS:   {char.wits:>2} ({char.get_stat_mod(StatType.WITS):+d})",
            f"GRIT:   {char.grit:>2} ({char.get_stat_mod(StatType.GRIT):+d})",
            f"AETHER: {char.aether:>2} ({char.get_stat_mod(StatType.AETHER):+d})",
            "",
            self._status_line(),
        ]
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

    def _cmd_use(self, arg: str) -> str:
        """Activate a special trait on an equipped or carried item."""
        arg = arg.strip().lower()
        if not arg:
            return "Use what? Usage: use <item name>\n" + self._status_line()

        char = self.engine.character

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

        context = {
            "character": char,
            "room": self.engine.get_current_room(),
            "item": target_item,
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
        else:
            if result.get("creates"):
                lines.append("  -> Failed to create effect.")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

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

        lines = [f"You raise your {item.name}! (+{dr_bonus} DR until next hit)"]
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

"""
codex/games/bridge.py - Universal Game Bridge
==============================================

Protocol-aware text adapter for any engine satisfying the GameEngine
navigation protocol (get_current_room, get_cardinal_exits, move_to_room,
populated_rooms, roll_check). Designed for Discord/Telegram chat interfaces.

Replaces the need for per-engine bridge classes for DnD5e, Cosmere, etc.
BurnwillowBridge remains separate due to its unique mechanics (Doom Clock,
GearGrid, dice pools).

Version: 1.0 (WO V4.0)
"""

import json
import random
from pathlib import Path
from typing import Optional

from codex.core.state_frame import StateFrame, build_state_frame
from codex.core.mechanics.rest import RestManager
from codex.spatial.map_renderer import render_mini_map, rooms_to_minimap_dict

_SAVES_DIR = Path(__file__).resolve().parent.parent.parent / "saves"


class UniversalGameBridge:
    """Text-mode adapter for any engine satisfying the GameEngine protocol.

    Translates plain-text commands (from Discord, Telegram, or terminal) into
    engine method calls and formats the results as human-readable strings.
    Handles movement, combat, inventory, NPC dialogue, map rendering, save/load,
    and audio narration without any engine-specific branching — all engines that
    implement the navigation protocol work transparently.

    Key attributes:
        engine: The underlying GameEngine instance.
        COMMAND_CATEGORIES: Structured command reference used by help/UI builders.
        dead: True once the player character has died; blocks further commands.
        last_frame: Cached StateFrame from the most recent step() call.
    """

    # Categorized command descriptions for Discord/Telegram UI
    COMMAND_CATEGORIES = {
        "movement": {
            "north": "Move north",
            "south": "Move south",
            "east": "Move east",
            "west": "Move west",
            "ne/nw/se/sw": "Diagonal movement",
        },
        "combat": {
            "attack": "Fight the first enemy",
            "rest": "Rest: 'rest short' or 'rest long'",
            "hitdice": "Spend hit dice to heal (DnD5e only)",
        },
        "interaction": {
            "talk": "Talk to an NPC",
            "investigate": "Investigation skill check",
            "perceive": "Perception skill check",
            "unlock": "Pick a lock",
            "services": "List room services",
            "event": "Show room events",
        },
        "exploration": {
            "look": "Describe current room",
            "search": "Search for loot",
            "loot": "Pick up items",
            "drop": "Drop an item",
            "use": "Use an item's special trait",
            "push": "Push furniture in a direction",
            "map": "Show mini-map",
            "inventory": "Show inventory",
            "stats": "Show character stats",
            "travel": "Use a transit point",
            "voice": "Toggle voice narration on/off",
            "sheet": "Full character sheet",
            "save": "Save current game",
            "help": "List all commands",
        },
        "narrative": {
            "trace": "Trace a fact through narrative shards",
            "reputation": "Show faction standing",
            "recap": "Session recap with narrative thread",
        },
    }

    def __init__(self, engine_class, character_data=None, seed=None,
                 broadcast_manager=None):
        """Instantiate the bridge, create or restore a character, and generate the dungeon."""
        self.engine = engine_class()
        self._init_shared_attrs(broadcast_manager)

        if character_data:
            self.engine.load_state(character_data)
        else:
            self.engine.create_character("Adventurer")
            self.engine.generate_dungeon(seed=seed)

    @classmethod
    def create_lightweight(cls, engine, broadcast=None):
        """Create a bridge wrapping a pre-initialized engine (bypass __init__).

        Single source of truth for lightweight bridge construction — replaces
        the scattered ``object.__new__()`` + manual attribute assignment pattern.
        """
        bridge = object.__new__(cls)
        bridge.engine = engine
        bridge._init_shared_attrs(broadcast)
        return bridge

    def _init_shared_attrs(self, broadcast=None):
        """Set all non-engine attributes to safe defaults."""
        self.dead = False
        self.last_frame: Optional[StateFrame] = None
        self._broadcast = broadcast
        self._system_tag = getattr(self.engine, 'system_id', 'unknown').upper()
        self._rest_mgr = RestManager()  # WO-V35.0
        self._butler = None  # WO-V50.0: Audio narration bridge
        self.show_dm_notes: bool = False  # WO-V54.0: Hide DM notes by default
        self._talking_to: Optional[str] = None  # WO-V54.0: NPC conversation state
        self._npc_trust: dict = {}  # WO-V81.0: NPC name -> conversation count
        self._session_log: list = []  # WO-V61.0: Session event chronicle
        self._visited_rooms: set = set()  # WO-V79.0: Track first-visit for loom shards
        self._momentum_handler = None  # WO-V62.0: Threshold handler
        self._pending_momentum_msgs: list = []  # WO-V62.0: Pending messages
        # WO-V68.0: Faction reputation tracker
        try:
            from codex.core.mechanics.reputation import ReputationTracker
            self._reputation: "Optional[ReputationTracker]" = ReputationTracker()
        except ImportError:
            self._reputation = None
        # Universal Narrative Bridge — config content → gameplay narration
        self._narrator = None
        try:
            from codex.core.services.narrative_bridge import NarrativeBridge
            _sys = getattr(self.engine, 'system_id', 'unknown')
            self._narrator = NarrativeBridge(_sys)
        except Exception:
            pass
        # WO-V129: Character Loom for personalized narration
        self._character_loom = None
        try:
            from codex.core.services.character_loom import CharacterLoom
            char = getattr(self.engine, 'character', None)
            if char:
                self._character_loom = CharacterLoom.from_sheet(char)
                # Share with narrator for personalized descriptions
                if self._narrator and self._character_loom:
                    self._narrator.set_character_loom(self._character_loom)
        except Exception:
            pass

    def _loom_shard(self, content: str, shard_type: str = "CHRONICLE"):
        """WO-V79.0: Create a narrative loom shard if the engine supports it."""
        if hasattr(self.engine, '_add_shard'):
            try:
                self.engine._add_shard(content, shard_type)
            except Exception:
                pass

    def set_butler(self, butler):
        """WO-V50.0: Attach a CodexButler for audio narration."""
        self._butler = butler

    def set_character_loom(self, char_data):
        """WO-V129: Attach a Character Loom from character data or sheet."""
        try:
            from codex.core.services.character_loom import CharacterLoom
            if hasattr(char_data, 'name'):  # CharacterSheet-like
                self._character_loom = CharacterLoom.from_sheet(char_data)
            elif isinstance(char_data, dict):
                self._character_loom = CharacterLoom.from_dict(char_data)
        except Exception:
            pass

    def _loom_resolve(self, text: str) -> str:
        """WO-V129: Resolve {loom.*} variables in any text if Loom is available."""
        if self._character_loom and hasattr(self._character_loom, 'resolve'):
            return self._character_loom.resolve(text)
        return text

    def _try_narrate(self, text):
        """WO-V50.0: Best-effort narration via butler (fire-and-forget)."""
        if self._butler and hasattr(self._butler, 'narrate'):
            try:
                self._butler.narrate(text)
            except Exception:
                pass

    def _log_event(self, event_type: str, **kwargs):
        """Append a structured event to the session chronicle."""
        self._session_log.append({"type": event_type, **kwargs})
        # WO-V61.0: Record in momentum ledger if available
        if hasattr(self, '_momentum_ledger') and self._momentum_ledger:
            location = getattr(self.engine, 'current_room_id', 0)
            threshold_events = self._momentum_ledger.record_from_event(
                event_type, str(location), tier=kwargs.get("tier", 1),
            )
            # WO-V62.0: Route threshold events to handler
            if threshold_events and self._momentum_handler:
                messages = self._momentum_handler.handle(threshold_events)
                self._pending_momentum_msgs.extend(messages)

    def get_session_log(self) -> list:
        """Return the session event log for recap use."""
        return list(self._session_log)

    def pop_momentum_messages(self) -> list:
        """Return and clear pending momentum threshold messages."""
        msgs = list(self._pending_momentum_msgs)
        self._pending_momentum_msgs.clear()
        return msgs

    @property
    def current_exits(self):
        """Return list of cardinal direction strings for current room."""
        return [e["direction"] for e in self.engine.get_cardinal_exits()]

    def step(self, command: str) -> str:
        """Process one command, return formatted text response."""
        if self.dead:
            return "You are dead. Start a new session."

        cmd = command.strip().lower()
        parts = cmd.split()
        verb = parts[0] if parts else ""

        # 8-way directions
        _DIR_ALIASES = {
            "n": "north", "s": "south", "e": "east", "w": "west",
            "north": "north", "south": "south", "east": "east", "west": "west",
            "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
            "northeast": "northeast", "northwest": "northwest",
            "southeast": "southeast", "southwest": "southwest",
        }
        if verb in _DIR_ALIASES:
            result = self._handle_move(_DIR_ALIASES[verb])
            self._emit_frame()
            return result

        dispatch = {
            "look": self._handle_look,
            "l": self._handle_look,
            "attack": self._handle_attack,
            "fight": self._handle_attack,
            "a": self._handle_attack,
            "search": self._handle_search,
            "loot": self._handle_loot,
            "drop": self._handle_drop,
            "inventory": self._handle_inventory,
            "inv": self._handle_inventory,
            "i": self._handle_inventory,
            "status": self._handle_status,
            "stats": self._handle_status,
            "map": self._handle_map,
            "help": self._help_text,
            "h": self._help_text,
            "?": self._help_text,
            "rest": self._handle_rest,
            "heal": self._handle_rest,
            "hitdice": self._handle_hitdice,
            "travel": self._handle_travel,
            "portal": self._handle_travel,
            "return": self._handle_travel,
            "extract": self._handle_travel,
            "retreat": self._handle_travel,
            "leave": self._handle_travel,
            "save": self._handle_save,
            "use": self._handle_use,
            "push": self._handle_push,
            "voice": self._handle_voice,
            "talk": self._handle_talk,
            "npc": self._handle_talk,
            "investigate": self._handle_investigate,
            "perceive": self._handle_perceive,
            "perception": self._handle_perceive,
            "unlock": self._handle_unlock,
            "lockpick": self._handle_unlock,
            "services": self._handle_services,
            "event": self._handle_event,
            "lore": self._handle_lore,
            "sheet": self._handle_sheet,
            "doll": self._handle_sheet,
            "character": self._handle_sheet,
            "trace": self._handle_trace,
            "reputation": self._handle_reputation,
            "rep": self._handle_reputation,
            "recap": self._handle_recap,
            "summarize": self._handle_recap,
            "summary": self._handle_recap,
        }

        # WO-V54.0: Service alias routing — route service names to _handle_services
        _SERVICE_ALIASES = {
            "drink", "drinks", "rumor", "rumors", "quest", "quest_board",
            "buy", "sell", "buy_weapons", "buy_chrome", "chrome_installation",
            "heal", "cure", "bless", "repair", "research",
            "job_briefing", "intel_purchase", "biometric_services",
            "exit_settlement",
        }
        if verb in _SERVICE_ALIASES:
            result = self._handle_services(verb)
            self._emit_frame()
            return result

        # WO-V54.0: Conversation exit commands
        if verb in ("bye", "leave", "goodbye") and self._talking_to:
            npc_name = self._talking_to
            self._talking_to = None
            return f"You end your conversation with {npc_name}.\n{self._status_line()}"

        handler = dispatch.get(verb)
        if handler:
            # Pass remaining args for handlers that accept them
            if verb in ("drop", "use", "push", "rest", "heal", "hitdice",
                        "voice", "talk", "npc", "services", "lore", "trace"):
                arg = " ".join(parts[1:]) if len(parts) > 1 else ""
                result = handler(arg)
            else:
                result = handler()
            self._emit_frame()
            return result

        # WO-V54.0: Route unrecognized input to NPC dialogue if in conversation
        if self._talking_to:
            return self._handle_npc_dialogue(cmd)

        return f"Unknown command: {verb}. Type 'help' for commands."

    def _emit_frame(self):
        """Cache a StateFrame snapshot after each step and broadcast update."""
        try:
            self.last_frame = build_state_frame(
                engine=self.engine,
                system_id=getattr(self.engine, 'system_id', 'unknown'),
            )
        except Exception:
            pass

        # Broadcast MAP_UPDATE for cross-interface sync
        if getattr(self, '_broadcast', None) and self.last_frame:
            try:
                self._broadcast.broadcast(
                    "MAP_UPDATE",
                    {
                        "system_id": getattr(self.engine, 'system_id', 'unknown'),
                        "room_id": self.engine.current_room_id,
                    },
                )
            except Exception:
                pass

    # ─── Command Handlers ─────────────────────────────────────────────

    def _handle_look(self) -> str:
        """Describe the current room."""
        room_node = self.engine.get_current_room()
        if not room_node:
            return "ERROR: No dungeon loaded."

        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        content = pop.content if pop else {}

        # Spawn NPC on first visit if room has none
        if self._narrator and pop and not content.get("npcs"):
            _tier = getattr(room_node, 'tier', 1) if room_node else 1
            _npc = self._narrator.spawn_npc_for_room(room_id, tier=_tier)
            if _npc:
                content.setdefault("npcs", []).append(_npc)

        room_type = room_node.room_type.name if hasattr(room_node, 'room_type') else "NORMAL"
        lines = [f"=== Room {room_id} ({room_type}) ==="]

        desc = content.get("description", "An unremarkable chamber.")
        if self._narrator:
            _tier = getattr(room_node, 'tier', 1) if room_node else 1
            _doom_clock = getattr(self.engine, 'doom_clock', None)
            _doom_val = getattr(_doom_clock, 'current', 0) if _doom_clock else 0
            desc = self._narrator.enrich_room(desc, _tier, doom=_doom_val)
        lines.append(desc)

        # Enemies
        enemies = content.get("enemies", [])
        if enemies:
            lines.append("")
            lines.append(f"ENEMIES ({len(enemies)}):")
            for e in enemies:
                if isinstance(e, dict):
                    _ename = e.get('name', 'Unknown')
                    lines.append(f"  * {_ename} (HP: {e.get('hp', '?')}/{e.get('max_hp', '?')})")
                    if self._narrator:
                        _eflav = self._narrator.describe_enemy(_ename)
                        if _eflav:
                            _etext = _eflav.lstrip(" \u2014")
                            lines.append(f"    {_etext}")
                else:
                    lines.append(f"  * {e}")

        # Loot
        loot = content.get("loot", [])
        if loot:
            lines.append("")
            lines.append(f"LOOT ({len(loot)}):")
            for item in loot:
                name = item.get("name", str(item)) if isinstance(item, dict) else str(item)
                lines.append(f"  * {name}")

        # Hazards
        hazards = content.get("hazards", [])
        if hazards:
            lines.append("")
            lines.append("HAZARDS:")
            for h in hazards:
                name = h.get("name", str(h)) if isinstance(h, dict) else str(h)
                lines.append(f"  ! {name}")
                if self._narrator and isinstance(h, dict):
                    _hflav = self._narrator.describe_hazard(name)
                    if _hflav:
                        _htext = _hflav.lstrip(" \u2014")
                        lines.append(f"    {_htext}")

        # Furniture
        furniture = content.get("furniture", [])
        if furniture:
            lines.append("")
            lines.append("FURNITURE:")
            for f in furniture:
                name = f.get("name", str(f)) if isinstance(f, dict) else str(f)
                lines.append(f"  # {name}")

        # NPCs (WO-V52.0, V81.0: show quirk on look)
        npcs = content.get("npcs", [])
        if npcs:
            lines.append("")
            lines.append(f"NPCS ({len(npcs)}):")
            for npc in npcs:
                if isinstance(npc, dict):
                    name = npc.get("name", "Unknown")
                    role = npc.get("role", "")
                    role_str = f" ({role})" if role else ""
                    quirk = npc.get("quirk", "")
                    if quirk:
                        lines.append(f"  @ {name}{role_str} — {quirk}")
                    else:
                        lines.append(f"  @ {name}{role_str}")
                else:
                    lines.append(f"  @ {npc}")

        # Services (WO-V52.0)
        services = content.get("services", [])
        if services:
            lines.append("")
            lines.append("SERVICES:")
            for svc in services:
                if isinstance(svc, dict):
                    lines.append(f"  * {svc.get('name', str(svc))}")
                else:
                    lines.append(f"  * {svc}")

        # Skill check hints (WO-V52.0)
        if content.get("investigation_dc", 0):
            lines.append("")
            lines.append("  Something here can be investigated...")
        if content.get("perception_dc", 0):
            lines.append("  You sense something hidden...")
        if content.get("lock_dc", 0):
            lines.append("  There is a lock here...")

        # Exits
        exits = self.engine.get_cardinal_exits()
        if exits:
            lines.append("")
            lines.append("EXITS:")
            for ex in exits:
                visited = " [VISITED]" if ex["id"] in self.engine.visited_rooms else ""
                lines.append(f"  {ex['direction'].upper()} -> Room {ex['id']} ({ex['type']}){visited}")

        lines.append("")
        lines.append(self._status_line())
        lines.append(self._render_minimap())

        return "\n".join(lines)

    # Map long direction names to short labels used by get_cardinal_exits()
    _DIR_SHORT = {
        "north": "N", "south": "S", "east": "E", "west": "W",
        "northeast": "NE", "northwest": "NW", "southeast": "SE", "southwest": "SW",
    }

    def _handle_move(self, direction: str) -> str:
        """Move in a direction (8-way)."""
        self._talking_to = None  # WO-V54.0: Auto-exit conversation on movement
        exits = self.engine.get_cardinal_exits()
        short_dir = self._DIR_SHORT.get(direction, direction.upper())
        target = None
        for ex in exits:
            # Normalize engine direction to short form for comparison
            # Handles both Burnwillow ("N") and D&D 5e/STC ("north") formats
            ex_dir = self._DIR_SHORT.get(ex["direction"].lower(), ex["direction"].upper())
            if ex_dir == short_dir:
                target = ex
                break

        if not target:
            return f"You can't go {direction}.\n{self._status_line()}"

        self.engine.move_to_room(target["id"])
        self._log_event("room_entered", room_id=target["id"])  # WO-V61.0

        # WO-V79.0: Loom shard on first visit to a room
        _rid = target["id"]
        if _rid not in self._visited_rooms:
            self._visited_rooms.add(_rid)
            _rnode = self.engine.get_current_room()
            _rtype = ""
            if _rnode:
                _rtype = _rnode.room_type.name if hasattr(_rnode, 'room_type') else "room"
                _rtype = _rtype.replace("_", " ")
            self._loom_shard(f"Explored {_rtype} (room {_rid})")

        # WO-V50.0 / V51.0: Narrate room entry — prefer read_aloud if present
        room_node = self.engine.get_current_room()
        if room_node:
            pop = self.engine.populated_rooms.get(target["id"])
            if pop and pop.content.get("read_aloud"):
                self._try_narrate(pop.content["read_aloud"][:200])
            else:
                desc = pop.content.get("description", "") if pop else ""
                rtype = room_node.room_type.name if hasattr(room_node, 'room_type') else "Room"
                self._try_narrate(f"{rtype.replace('_', ' ').title()}. {desc[:100]}")

        # WO-V52.0: Show first event trigger on room entry
        look_result = self._handle_look()
        pop = self.engine.populated_rooms.get(target["id"])
        if pop:
            events = pop.content.get("event_triggers", [])
            if events:
                look_result += f"\n\n[Event] {events[0]}"
        return look_result

    def _handle_attack(self) -> str:
        """Attack the first enemy in the room."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return "ERROR: No room data."

        enemies = pop.content.get("enemies", [])
        if not enemies:
            return f"No enemies here.\n{self._status_line()}"

        char = self.engine.character
        if not char:
            return "No active character."

        enemy = enemies[0]
        enemy_name = enemy.get("name", "Enemy") if isinstance(enemy, dict) else str(enemy)
        enemy_hp = enemy.get("hp", 5) if isinstance(enemy, dict) else 5
        enemy_defense = enemy.get("defense", 12) if isinstance(enemy, dict) else 12
        enemy_attack = enemy.get("attack", 3) if isinstance(enemy, dict) else 3

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

        # Player attack roll
        result = self.engine.roll_check(dc=enemy_defense)
        if result.get("success") or result.get("critical"):
            # Damage scales with proficiency/level
            base_damage = random.randint(1, 8) + (result.get("modifier", 0))
            damage = max(1, base_damage)
            if result.get("critical"):
                damage *= 2
                lines.append(f"CRITICAL HIT! You strike {enemy_name} for {damage} damage!")
            else:
                lines.append(f"You hit {enemy_name} for {damage} damage! ({result['total']} vs DC {enemy_defense})")
            if self._narrator:
                _etype = "crit" if result.get("critical") else "hit"
                _cnarr = self._narrator.narrate_combat_mimir(
                    _etype, enemy_name, damage, mimir_fn=_combat_mimir_fn)
                if _cnarr:
                    lines.append(f"  {_cnarr}")

            enemy_hp -= damage
            if isinstance(enemy, dict):
                enemy["hp"] = enemy_hp

            if enemy_hp <= 0:
                lines.append(f"{enemy_name} is slain!")
                if self._narrator:
                    _knarr = self._narrator.narrate_combat_mimir(
                        "kill", enemy_name, mimir_fn=_combat_mimir_fn)
                    if _knarr:
                        lines.append(f"  {_knarr}")
                enemies.pop(0)
                pop.content["enemies"] = enemies
                self._try_narrate(f"{enemy_name} is slain!")  # WO-V50.0
                self._log_event("kill", target=enemy_name)  # WO-V61.0
                self._loom_shard(f"Slew {enemy_name} in room {room_id}")  # WO-V79.0
            else:
                lines.append(f"{enemy_name} has {enemy_hp} HP remaining.")
        else:
            _miss_type = "fumble" if result.get("fumble") else "miss"
            if result.get("fumble"):
                lines.append(f"FUMBLE! You swing wildly and miss {enemy_name}.")
            else:
                lines.append(f"You miss {enemy_name}. ({result['total']} vs DC {enemy_defense})")
            if self._narrator:
                _mnarr = self._narrator.narrate_combat_mimir(
                    _miss_type, enemy_name, mimir_fn=_combat_mimir_fn)
                if _mnarr:
                    lines.append(f"  {_mnarr}")

        # Enemy retaliation (if alive)
        if enemy_hp > 0:
            lines.append("")
            char_defense = getattr(char, 'armor_class', getattr(char, 'defense', 10))
            enemy_roll = random.randint(1, 20) + enemy_attack
            if enemy_roll >= char_defense:
                dmg = random.randint(1, 6) + enemy_attack // 2
                actual = char.take_damage(dmg)
                lines.append(f"{enemy_name} strikes you for {actual} damage!")
                if self._narrator:
                    _ehnarr = self._narrator.narrate_combat_mimir(
                        "enemy_hit", enemy_name, actual, mimir_fn=_combat_mimir_fn)
                    if _ehnarr:
                        lines.append(f"  {_ehnarr}")
                if char.is_alive() and char.current_hp / max(1, getattr(char, 'max_hp', 1)) < 0.2:
                    self._log_event("near_death", name=getattr(char, 'name', 'Unknown'),
                                    hp=char.current_hp, max_hp=getattr(char, 'max_hp', 1),
                                    attacker=enemy_name)  # WO-V61.0
                    _cname = getattr(char, 'name', 'The adventurer')
                    self._loom_shard(
                        f"{_cname} nearly fell to {enemy_name} ({char.current_hp} HP remaining)",
                        "ANCHOR")  # WO-V79.0
            else:
                lines.append(f"{enemy_name} attacks but misses!")
                if self._narrator:
                    _emnarr = self._narrator.narrate_combat_mimir(
                        "enemy_miss", enemy_name, mimir_fn=_combat_mimir_fn)
                    if _emnarr:
                        lines.append(f"  {_emnarr}")

        # Death check
        if not char.is_alive():
            self.dead = True
            self._log_event("party_death", name=getattr(char, 'name', 'Unknown'))  # WO-V61.0
            self._loom_shard(
                f"{getattr(char, 'name', 'The adventurer')} fell in room {room_id}",
                "ANCHOR")  # WO-V79.0
            self._try_narrate("You have fallen.")  # WO-V50.0
            lines.append("")
            lines.append("=== YOU HAVE FALLEN ===")
            lines.append("The dungeon claims another soul.")
            return "\n".join(lines)

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _handle_search(self) -> str:
        """Search the current room for loot."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return "Nothing to search."

        result = self.engine.roll_check(dc=12)
        lines = []

        if result.get("success") or result.get("critical"):
            loot = pop.content.get("loot", [])
            if loot:
                found = loot.pop(0)
                name = found.get("name", str(found)) if isinstance(found, dict) else str(found)
                _lflav = self._narrator.describe_loot(name) if self._narrator else ""
                lines.append(f"You found: {name}!{_lflav}")
                pop.content["loot"] = loot
                self._loom_shard(f"Discovered {name}")  # WO-V79.0
            else:
                lines.append("Search successful, but nothing of value remains.")
        else:
            lines.append(f"You find nothing useful. ({result['total']} vs DC 12)")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _handle_loot(self) -> str:
        """Pick up the first item from the room (no roll)."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return "Nothing to search."

        loot = pop.content.get("loot", [])
        if not loot:
            return f"Nothing to pick up.\n{self._status_line()}"

        found = loot.pop(0)
        name = found.get("name", str(found)) if isinstance(found, dict) else str(found)
        pop.content["loot"] = loot

        # Add to character inventory if available
        char = self.engine.character
        if char and hasattr(char, 'inventory'):
            if isinstance(char.inventory, list):
                char.inventory.append(found)
            elif isinstance(char.inventory, dict) and hasattr(char, 'add_to_inventory'):
                # Burnwillow-style dict inventory with GearItem
                try:
                    from codex.games.burnwillow.engine import GearItem, GearSlot, GearTier
                    if isinstance(found, dict) and "slot" in found:
                        item = GearItem.from_dict(found)
                    else:
                        item = GearItem(name=name, slot=GearSlot.R_HAND, tier=GearTier.TIER_0)
                    char.add_to_inventory(item)
                except (ImportError, KeyError, ValueError):
                    pass

        self._log_event("loot", item=name)  # WO-V61.0
        self._loom_shard(f"Found {name}")  # WO-V79.0
        _lflav = self._narrator.describe_loot(name) if self._narrator else ""
        return f"Picked up: {name}!{_lflav}\n\n{self._status_line()}"

    def _handle_drop(self, arg: str = "") -> str:
        """Drop a named item from inventory."""
        arg = arg.strip()
        if not arg:
            return f"Drop what? Usage: drop <item name>\n{self._status_line()}"

        char = self.engine.character
        if not char:
            return "No active character."

        inv = getattr(char, 'inventory', [])
        target = arg.lower()

        # Search inventory
        if isinstance(inv, list):
            for i, item in enumerate(inv):
                name = item.get("name", str(item)) if isinstance(item, dict) else str(item)
                if name.lower() == target:
                    removed = inv.pop(i)
                    # Add back to room loot
                    room_id = self.engine.current_room_id
                    pop = self.engine.populated_rooms.get(room_id)
                    if pop:
                        pop.content.setdefault("loot", []).append(removed)
                    return f"Dropped: {name}\n\n{self._status_line()}"
        elif isinstance(inv, dict):
            for idx, item in list(inv.items()):
                item_name = getattr(item, 'name', str(item))
                if item_name.lower() == target:
                    removed = inv.pop(idx)
                    room_id = self.engine.current_room_id
                    pop = self.engine.populated_rooms.get(room_id)
                    if pop:
                        item_dict = removed.to_dict() if hasattr(removed, 'to_dict') else {"name": item_name}
                        pop.content.setdefault("loot", []).append(item_dict)
                    return f"Dropped: {item_name}\n\n{self._status_line()}"

        return f"You don't have '{arg}'.\n{self._status_line()}"

    def _handle_inventory(self) -> str:
        """List character inventory."""
        char = self.engine.character
        if not char:
            return "No active character."

        lines = [f"=== {char.name} — Inventory ==="]
        inv = getattr(char, 'inventory', [])
        if inv:
            for item in inv[:15]:
                name = item.get("name", str(item)) if isinstance(item, dict) else str(item)
                lines.append(f"  * {name}")
            if len(inv) > 15:
                lines.append(f"  ...and {len(inv) - 15} more")
        else:
            lines.append("  (empty)")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _handle_status(self) -> str:
        """Show character status."""
        char = self.engine.character
        if not char:
            return "No active character."

        system = getattr(self.engine, 'system_id', 'unknown')
        lines = [f"=== {char.name} ({self.engine.display_name}) ==="]
        lines.append(f"HP: {char.current_hp}/{char.max_hp}")

        if system == "dnd5e":
            lines.append(f"AC: {char.armor_class} | Level: {char.level}")
            lines.append(f"Class: {char.character_class or 'None'} | Race: {char.race or 'None'}")
            lines.append(f"STR: {char.strength} DEX: {char.dexterity} CON: {char.constitution}")
            lines.append(f"INT: {char.intelligence} WIS: {char.wisdom} CHA: {char.charisma}")
        elif system == "stc":
            lines.append(f"Defense: {char.defense} | Focus: {char.focus}")
            lines.append(f"Order: {char.order or 'None'} | Heritage: {char.heritage or 'None'}")
            lines.append(f"STR: {char.strength} SPD: {char.speed} INT: {char.intellect}")

        total = len(self.engine.dungeon_graph.rooms) if self.engine.dungeon_graph else 0
        visited = len(self.engine.visited_rooms)
        lines.append(f"Explored: {visited}/{total} rooms")

        return "\n".join(lines)

    def _handle_sheet(self) -> str:
        """Show full character sheet.

        Terminal callers intercept 'sheet' before reaching bridge and render
        Rich panels directly. Chat interfaces (Discord/Telegram) fall through
        here and get the text-only status instead.
        """
        return self._handle_status()

    def _handle_map(self) -> str:
        """Render mini-map."""
        return self._render_minimap() + "\n" + self._status_line()

    def _handle_rest(self, arg: str = "") -> str:
        """Rest using RestManager: 'rest short' (default) or 'rest long'."""
        char = self.engine.character
        if not char:
            return "No active character."

        rest_type = arg.strip().lower() if arg else "short"
        if rest_type not in ("short", "long"):
            rest_type = "short"

        result = self._rest_mgr.rest(self.engine, self._system_tag, rest_type)

        # WO-V35.0: Broadcast rest complete
        if getattr(self, '_broadcast', None):
            self._broadcast.broadcast("REST_COMPLETE", {
                "rest_type": rest_type,
                "system_tag": self._system_tag,
                "hp_recovered": result.hp_recovered,
                "summary": result.summary(),
            })

        return f"{result.summary()}\n\n{self._status_line()}"

    def _handle_hitdice(self, arg: str = "") -> str:
        """Spend hit dice to heal (DnD5e only). WO-V35.0."""
        if self._system_tag != "DND5E":
            return f"Hit dice are only available in D&D 5e.\n{self._status_line()}"

        char = self.engine.character
        if not char:
            return "No active character."

        hd_remaining = getattr(char, 'hit_dice_remaining', 0)
        if hd_remaining <= 0:
            return f"No hit dice remaining.\n{self._status_line()}"

        result = self._rest_mgr.short_rest_dnd5e(self.engine)
        return f"{result.summary()}\n\n{self._status_line()}"

    def _handle_travel(self) -> str:
        """Attempt to use a transit point in the current room."""
        room_node = self.engine.get_current_room()
        if not room_node:
            return "ERROR: No dungeon loaded."

        rtype = room_node.room_type.name if hasattr(room_node, 'room_type') else "NORMAL"

        if rtype == "START":
            return (
                "You retrace your steps back to the dungeon entrance. "
                "Daylight spills in from the surface above.\n\n"
                + self._status_line()
            )
        elif rtype == "RETURN_GATE":
            return (
                "The extraction circle flares to life beneath your feet. "
                "Warmth floods your limbs as the dungeon's grip loosens. "
                "You are pulled back to Emberhome.\n\n"
                + self._status_line()
            )
        elif rtype == "HIDDEN_PORTAL":
            return (
                "You step through the shimmering tear. Reality bends, "
                "stretches, and snaps back. The arcane portal deposits "
                "you somewhere... else.\n\n"
                + self._status_line()
            )
        elif rtype == "BORDER_CROSSING":
            return (
                "You cross the border marker. The Patron's influence "
                "fades like smoke. The road ahead belongs to no one.\n\n"
                + self._status_line()
            )

        return f"There is no transit point in this room.\n{self._status_line()}"

    def _handle_use(self, arg: str = "") -> str:
        """Activate a special trait on a carried item."""
        arg = arg.strip()
        if not arg:
            return f"Use what? Usage: use <item name>\n{self._status_line()}"

        char = self.engine.character
        if not char:
            return "No active character."

        # Search inventory for matching item with special_traits
        inv = getattr(char, 'inventory', {})
        matched_name = None
        matched_trait = None
        if isinstance(inv, dict):
            for idx, item in inv.items():
                name = getattr(item, 'name', str(item))
                traits = getattr(item, 'special_traits', [])
                if arg.lower() in name.lower() and traits:
                    matched_name = name
                    matched_trait = traits[0]
                    break
        elif isinstance(inv, list):
            for item in inv:
                name = item.get("name", str(item)) if isinstance(item, dict) else str(item)
                traits = item.get("special_traits", []) if isinstance(item, dict) else []
                if arg.lower() in name.lower() and traits:
                    matched_name = name
                    matched_trait = traits[0]
                    break

        if not matched_name:
            return f"No usable item matching '{arg}'.\n{self._status_line()}"

        # WO-V56.0: Route through TraitHandler if available
        handler = getattr(self.engine, '_trait_handler', None)
        if handler:
            system_id = getattr(self.engine, 'system_id', 'unknown')
            try:
                result = handler.activate_trait(
                    matched_trait, system_id,
                    {"character": char, "item": matched_name})
                desc = result.get("description", "")
                return f"You activate {matched_name}'s {matched_trait} trait. {desc}\n{self._status_line()}"
            except Exception:
                pass

        return f"You activate {matched_name}'s {matched_trait} trait.\n{self._status_line()}"

    def _handle_push(self, arg: str = "") -> str:
        """Push a piece of furniture in a cardinal direction."""
        parts = arg.strip().split()
        if len(parts) < 2:
            return f"Usage: push <name> <n/s/e/w>\n{self._status_line()}"

        direction = parts[-1].lower()
        name_fragment = " ".join(parts[:-1])

        if hasattr(self.engine, 'push_furniture'):
            result = self.engine.push_furniture(name_fragment, direction)
            lines = [result["message"]]
            if result.get("success") and result.get("position"):
                pos = result["position"]
                lines.append(f"  -> Now at ({pos[0]}, {pos[1]})")
            lines.append("")
            lines.append(self._status_line())
            return "\n".join(lines)

        return f"Push not supported for this engine.\n{self._status_line()}"

    def _handle_voice(self, arg: str = "") -> str:
        """WO-V50.0: Toggle voice narration on/off."""
        if not self._butler:
            return f"No voice system available.\n{self._status_line()}"

        arg = arg.strip().lower()
        if arg == "on":
            self._butler._voice_enabled = True
        elif arg == "off":
            self._butler._voice_enabled = False
        elif hasattr(self._butler, 'toggle_voice'):
            self._butler.toggle_voice()
        else:
            self._butler._voice_enabled = not self._butler._voice_enabled

        state = "ON" if self._butler._voice_enabled else "OFF"
        return f"Voice narration: {state}\n{self._status_line()}"

    def _handle_save(self) -> str:
        """Save current game state to disk."""
        if not hasattr(self.engine, 'save_state'):
            return "Save not supported for this engine."
        try:
            data = self.engine.save_state() if callable(getattr(self.engine, 'save_state', None)) else {}
            system_id = getattr(self.engine, 'system_id', 'unknown')
            _SAVES_DIR.mkdir(parents=True, exist_ok=True)
            save_path = _SAVES_DIR / f"{system_id}_save.json"
            save_path.write_text(json.dumps(data, indent=2, default=str))
            return f"Game saved to {save_path.name}.\n{self._status_line()}"
        except Exception as e:
            return f"Save failed: {e}"

    # ─── Scene Interaction Handlers (WO-V52.0) ─────────────────────

    def _handle_talk(self, arg: str = "") -> str:
        """Talk to an NPC in the current room."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return f"No one to talk to here.\n{self._status_line()}"

        npcs = pop.content.get("npcs", [])
        if not npcs:
            return f"There are no NPCs in this room.\n{self._status_line()}"

        arg = arg.strip()
        if not arg:
            # List all NPCs
            lines = ["NPCs in this room:"]
            for npc in npcs:
                if isinstance(npc, dict):
                    name = npc.get("name", "Unknown")
                    role = npc.get("role", "")
                    role_str = f" ({role})" if role else ""
                    lines.append(f"  * {name}{role_str}")
                else:
                    lines.append(f"  * {npc}")
            lines.append("")
            lines.append("Usage: talk <npc name>")
            lines.append(self._status_line())
            return "\n".join(lines)

        # Match NPC by case-insensitive substring
        target = arg.lower()
        for npc in npcs:
            if isinstance(npc, dict):
                name = npc.get("name", "Unknown")
                if target in name.lower():
                    lines = [f"=== {name} ==="]
                    role = npc.get("role", "")
                    if role:
                        lines.append(f"Role: {role}")
                    # WO-V81.0: Voice style tag
                    voice = npc.get("voice", "")
                    if voice:
                        lines.append(f"Voice: {voice}")
                    dialogue = npc.get("dialogue", "")
                    # WO-V131: Personalize dialogue with character background
                    if dialogue and self._character_loom:
                        dialogue = self._character_loom.resolve(dialogue)
                    if dialogue:
                        lines.append(f'"{dialogue}"')
                    else:
                        lines.append(f"{name} has nothing to say.")
                    # WO-V131: NPC recognizes character background
                    if self._character_loom and hasattr(self._character_loom, 'background'):
                        _bg = self._character_loom.background
                        _char_name = self._character_loom.name
                        if _bg and _bg != "unknown origins" and _trust_level == 1:
                            _role_bg_match = {
                                "guard": ["soldier", "fighter", "knight"],
                                "merchant": ["guild artisan", "merchant", "noble"],
                                "criminal": ["criminal", "charlatan", "urchin"],
                                "innkeeper": ["folk hero", "entertainer"],
                                "priest": ["acolyte", "hermit"],
                                "scholar": ["sage", "cloistered scholar"],
                            }
                            _matches = _role_bg_match.get(role.lower(), [])
                            if any(m in _bg.lower() for m in _matches):
                                lines.append(f'[{name} recognizes a fellow {_bg}.]')
                    # WO-V81.0: Track trust and reveal depth
                    _trust_key = name.lower()
                    self._npc_trust[_trust_key] = self._npc_trust.get(_trust_key, 0) + 1
                    _trust_level = self._npc_trust[_trust_key]
                    # Show want on 2nd+ conversation (quest hook)
                    want = npc.get("want", "")
                    if want and _trust_level >= 2:
                        lines.append(f'[{name} seems to want something: {want}]')
                    # Reveal secret on 3rd+ conversation (trust earned)
                    secret = npc.get("secret", "")
                    if secret and _trust_level >= 3:
                        lines.append(f'[{name} confides: {secret}]')
                    notes = npc.get("notes", "")
                    if notes and self.show_dm_notes:
                        lines.append(f"[{notes}]")
                    # WO-V54.0: Enter conversation mode
                    self._talking_to = name
                    # WO-V79.0: Loom shard for NPC encounter
                    self._loom_shard(f"Spoke with {name} ({role})" if role else f"Spoke with {name}")
                    lines.append("")
                    lines.append("[dim]You are now talking to "
                                 f"{name}. Type freely to chat, 'bye' to end.[/dim]")
                    lines.append(self._status_line())
                    return "\n".join(lines)

        return f"No NPC named '{arg}' here.\n{self._status_line()}"

    def _handle_investigate(self) -> str:
        """Investigate the room (skill check vs investigation_dc)."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return f"Nothing to investigate.\n{self._status_line()}"

        dc = pop.content.get("investigation_dc", 0)
        if not dc:
            return f"Nothing to investigate here.\n{self._status_line()}"

        result = self.engine.roll_check(dc=dc)
        lines = []

        if result.get("success") or result.get("critical"):
            success_text = pop.content.get("investigation_success", "You discover something interesting!")
            lines.append(f"Investigation successful! ({result['total']} vs DC {dc})")
            lines.append(success_text)
            # Clear DC so it can't be repeated
            pop.content["investigation_dc"] = 0
            self._try_narrate(success_text[:200])
            self._loom_shard(f"Investigation: {success_text[:80]}")  # WO-V79.0
        else:
            lines.append(f"Your investigation reveals nothing. ({result['total']} vs DC {dc})")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _handle_perceive(self) -> str:
        """Perceive hidden details (skill check vs perception_dc)."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return f"Nothing to perceive.\n{self._status_line()}"

        dc = pop.content.get("perception_dc", 0)
        if not dc:
            return f"You don't notice anything hidden.\n{self._status_line()}"

        result = self.engine.roll_check(dc=dc)
        lines = []

        if result.get("success") or result.get("critical"):
            success_text = pop.content.get("perception_success", "You notice something hidden!")
            lines.append(f"Perception check passed! ({result['total']} vs DC {dc})")
            lines.append(success_text)
            pop.content["perception_dc"] = 0
            self._try_narrate(success_text[:200])
        else:
            lines.append(f"You don't notice anything unusual. ({result['total']} vs DC {dc})")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _handle_unlock(self) -> str:
        """Attempt to pick a lock (skill check vs lock_dc)."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return f"Nothing to unlock.\n{self._status_line()}"

        dc = pop.content.get("lock_dc", 0)
        if not dc:
            return f"There is nothing locked here.\n{self._status_line()}"

        result = self.engine.roll_check(dc=dc)
        lines = []

        if result.get("success") or result.get("critical"):
            lines.append(f"Lock opened! ({result['total']} vs DC {dc})")
            pop.content["lock_dc"] = 0
        else:
            lines.append(f"The lock holds firm. ({result['total']} vs DC {dc})")

        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _handle_services(self, arg: str = "") -> str:
        """List or use services in the current room. WO-V54.0: dispatches service names."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return f"No services available.\n{self._status_line()}"

        services = pop.content.get("services", [])
        if not services:
            return f"No services available in this room.\n{self._status_line()}"

        arg = arg.strip().lower()
        if not arg:
            # List services
            lines = ["SERVICES:"]
            for svc in services:
                if isinstance(svc, dict):
                    lines.append(f"  * {svc.get('name', str(svc))}")
                else:
                    lines.append(f"  * {svc}")
            lines.append("")
            lines.append("Type a service name to use it.")
            lines.append(self._status_line())
            return "\n".join(lines)

        # Check if service is available in this room
        svc_names = []
        for svc in services:
            if isinstance(svc, dict):
                svc_names.append(svc.get("name", str(svc)).lower())
            else:
                svc_names.append(str(svc).lower())

        matched = next((s for s in svc_names if arg in s or s in arg), None)
        if matched:
            return self._dispatch_service(matched)

        return f"Service '{arg}' is not available here.\n{self._status_line()}"

    def _dispatch_service(self, service_name: str) -> str:
        """WO-V54.0: Generic service dispatcher for all game systems."""
        svc = service_name.lower()

        # Mechanical services — these have real game effects
        if svc in ("rest",):
            return self._handle_rest("short")

        if svc in ("rumor", "rumors", "lore", "research", "intel_purchase"):
            return self._generate_rumor()

        if svc in ("quest", "quest_board", "job_briefing"):
            return self._service_quest()

        if svc in ("heal", "cure", "bless", "biometric_services"):
            return self._service_heal()

        if svc in ("exit_settlement",):
            return (
                "Use movement commands (n/s/e/w) to leave the settlement.\n\n"
                + self._status_line()
            )

        # System-aware flavor text lookup
        system_id = getattr(self.engine, 'system_id', 'unknown')
        from codex.core.services.narrative_frame import get_service_flavor
        flavor = get_service_flavor(svc, system_id)
        if flavor:
            return f"{flavor}\n\n{self._status_line()}"

        # Generic fallback for any service in the room's list
        return (
            f"You use the {service_name} service.\n\n"
            + self._status_line()
        )

    def _generate_rumor(self) -> str:
        """WO-V54.0: Generate a rumor from room events or NPC context."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if pop:
            events = pop.content.get("event_triggers", [])
            if events:
                return f'Rumor: "{events[0]}"\n\n{self._status_line()}'
            npcs = pop.content.get("npcs", [])
            if npcs:
                npc = npcs[0]
                name = npc.get("name", "Someone") if isinstance(npc, dict) else str(npc)
                return (
                    f'{name} leans in and whispers something interesting, '
                    f'but you can\'t quite make it out over the noise.\n\n'
                    + self._status_line()
                )
        return f"No rumors to be heard here.\n{self._status_line()}"

    def _service_quest(self) -> str:
        """WO-V54.0: Find quest NPCs and show hints."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return f"No quests available here.\n{self._status_line()}"

        npcs = pop.content.get("npcs", [])
        quest_npcs = [
            n for n in npcs
            if isinstance(n, dict) and "quest" in n.get("role", "").lower()
        ]

        if quest_npcs:
            lines = ["Available quest contacts:"]
            for npc in quest_npcs:
                name = npc.get("name", "Unknown")
                lines.append(f"  * Talk to {name} (use: talk {name.lower().split()[0]})")
            lines.append("")
            lines.append(self._status_line())
            return "\n".join(lines)

        return f"No quest givers in this room. Try talking to NPCs.\n{self._status_line()}"

    def _service_heal(self) -> str:
        """WO-V54.0: Restore HP for all party members."""
        party = getattr(self.engine, 'party', [])
        char = self.engine.character
        healed = []

        if party:
            for member in party:
                if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
                    if member.current_hp < member.max_hp:
                        member.current_hp = member.max_hp
                        healed.append(member.name)
        elif char and hasattr(char, 'current_hp'):
            if char.current_hp < char.max_hp:
                char.current_hp = char.max_hp
                healed.append(char.name)

        if healed:
            return (
                f"Healing complete. Restored: {', '.join(healed)}\n\n"
                + self._status_line()
            )
        return f"Everyone is already at full health.\n{self._status_line()}"

    def _handle_npc_dialogue(self, player_input: str) -> str:
        """WO-V54.0: Route free-form input to Mimir for NPC dialogue."""
        npc_name = self._talking_to
        if not npc_name:
            return f"You're not talking to anyone.\n{self._status_line()}"

        # Find NPC data in current room
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        npc_data = {}
        if pop:
            for npc in pop.content.get("npcs", []):
                if isinstance(npc, dict) and npc.get("name", "").lower() == npc_name.lower():
                    npc_data = npc
                    break

        room_desc = pop.content.get("description", "") if pop else ""
        events = pop.content.get("event_triggers", []) if pop else []
        setting_id = getattr(self.engine, 'setting_id', '')

        # WO-V61.0: Inject mood into NPC dialogue context
        mood = self.engine.get_mood_context() if hasattr(self.engine, 'get_mood_context') else {}
        if mood.get("party_condition") in ("critical", "battered"):
            room_desc += f" The visitor looks {mood['party_condition']}."

        from codex.core.services.narrative_frame import query_npc_dialogue
        response = query_npc_dialogue(
            npc_name, player_input, npc_data,
            room_desc=room_desc, events=events, setting_id=setting_id,
        )
        if response:
            return f'{npc_name}: "{response}"\n\n{self._status_line()}'

        # Fallback to static dialogue
        dialogue = npc_data.get("dialogue", "")
        if dialogue:
            return f'{npc_name}: "{dialogue}"\n\n{self._status_line()}'
        return f'{npc_name} has nothing more to say.\n{self._status_line()}'

    def _handle_lore(self, arg: str = "") -> str:
        """WO-V55.0: Look up world lore from local wiki."""
        if not arg:
            return f"Usage: lore <topic>  (e.g., 'lore waterdeep')\n{self._status_line()}"

        setting_id = getattr(self.engine, 'setting_id', '')
        try:
            from codex.integrations.fr_wiki import is_fr_context, get_fr_wiki
        except ImportError:
            return f"Lore system not available.\n{self._status_line()}"

        if not is_fr_context(setting_id):
            return (f"No lore archive for this setting "
                    f"({setting_id or 'unknown'}).\n{self._status_line()}")

        wiki = get_fr_wiki()
        summary = wiki.get_lore_summary(arg, max_chars=600)
        if not summary:
            return f"No lore found for '{arg}'.\n{self._status_line()}"
        return f"--- Lore: {arg.title()} ---\n{summary}\n\n{self._status_line()}"

    def _handle_trace(self, arg: str = "") -> str:
        """WO-V68.0: Trace a keyword through narrative memory shards.

        Requires the engine to have a ``_memory_shards`` attribute (engines
        using NarrativeLoomMixin).  Returns a formatted list of shard layers
        that contain the keyword, ordered by authority.
        """
        keyword = arg.strip()
        if not keyword:
            return "Usage: trace <keyword>\n" + self._status_line()

        if not hasattr(self.engine, '_memory_shards'):
            return "Narrative trace requires an engine with memory shards loaded.\n" + self._status_line()

        shards = getattr(self.engine, '_memory_shards', [])
        if not shards:
            return f"No memory shards loaded — trace for '{keyword}' unavailable.\n" + self._status_line()

        try:
            from codex.core.services.narrative_loom import diagnostic_trace
        except ImportError:
            return "Narrative Loom not available.\n" + self._status_line()

        results = diagnostic_trace(keyword, shards)
        if not results:
            return f"No shards mention '{keyword}'.\n" + self._status_line()

        lines = [f"=== Trace: \"{keyword}\" ({len(results)} match{'es' if len(results) != 1 else ''}) ==="]
        for r in results:
            lines.append(
                f"  [{r['type']}] source={r['source']} relevance={r['relevance']}"
            )
            if r.get("excerpt"):
                lines.append(f"    {r['excerpt']}")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _build_engine_snapshot(self) -> dict:
        """WO-V79.0: Build an engine state snapshot for session recap."""
        char = self.engine.character
        party = []
        if char:
            party.append({
                "name": getattr(char, 'name', 'Adventurer'),
                "hp": getattr(char, 'current_hp', 0),
                "max_hp": getattr(char, 'max_hp', 1),
            })
        doom = 0
        _dc = getattr(self.engine, 'doom_clock', None)
        if _dc:
            doom = getattr(_dc, 'current', 0)
        return {
            "party": party,
            "doom": doom,
            "turns": len(self._session_log),
            "chapter": 1,
            "completed_quests": [],
        }

    def _handle_recap(self) -> str:
        """WO-V79.0: Show session recap with narrative loom shards."""
        try:
            from codex.core.services.narrative_loom import summarize_session
        except ImportError:
            return "Narrative Loom not available.\n" + self._status_line()

        snapshot = self._build_engine_snapshot()
        recap = summarize_session(self._session_log, snapshot)

        # Append loom shards summary if available
        shards = getattr(self.engine, '_memory_shards', [])
        if shards:
            recap += "\n\n--- Narrative Thread ---"
            for s in shards[-10:]:  # Show last 10 shards
                _type = s.shard_type.value if hasattr(s.shard_type, 'value') else str(s.shard_type)
                recap += f"\n  [{_type}] {s.content}"
            if len(shards) > 10:
                recap += f"\n  ... and {len(shards) - 10} earlier entries"

        return recap

    def _handle_reputation(self) -> str:
        """WO-V68.0: Show all tracked faction standings."""
        if self._reputation is None:
            return "Reputation system not available.\n" + self._status_line()

        standings = self._reputation.all_standings()
        if not standings:
            return "No faction relationships tracked yet.\n" + self._status_line()

        lines = ["=== Faction Reputation ==="]
        for fid, fs in standings:
            disp = self._reputation.get_disposition_modifier(fid)
            disp_str = f"{disp:+d}" if disp != 0 else " 0"
            lines.append(
                f"  {fid:<28} {fs.title:<10} ({fs.standing:+d})  NPC mod {disp_str}"
            )
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _handle_event(self) -> str:
        """Show event triggers for the current room."""
        room_id = self.engine.current_room_id
        pop = self.engine.populated_rooms.get(room_id)
        if not pop:
            return f"No events here.\n{self._status_line()}"

        events = pop.content.get("event_triggers", [])
        if not events:
            return f"No events in this room.\n{self._status_line()}"

        lines = ["EVENTS:"]
        for ev in events:
            lines.append(f"  * {ev}")
        lines.append("")
        lines.append(self._status_line())
        return "\n".join(lines)

    def _help_text(self) -> str:
        """List available commands (system-aware)."""
        lines = [
            "=== COMMANDS ===",
            "--- Movement ---",
            "n/s/e/w         - Move (cardinal)",
            "ne/nw/se/sw     - Move (diagonal)",
            "look (l)        - Describe current room",
            "map             - Show mini-map",
            "--- Combat ---",
            "attack (a)      - Fight first enemy",
            "rest (heal)     - Rest: 'rest short' or 'rest long'",
        ]

        # System-specific commands
        tag = self._system_tag.upper()
        if tag == "DND5E":
            lines.append("hitdice (hd)    - Spend hit dice to heal")
        if tag == "BURNWILLOW":
            lines.append("push <n> <dir>  - Push furniture (8-way)")
            lines.append("use <item>      - Activate item's special trait")
            lines.append("search          - Search for loot")

        lines.extend([
            "--- Interaction ---",
            "talk <npc>      - Start conversation (type freely, 'bye' to end)",
            "investigate     - Investigation check",
            "perceive        - Perception check",
            "unlock          - Pick a lock",
            "services        - List room services",
            "drink/rumor/quest - Use room services",
            "lore <topic>    - Look up world lore",
            "event           - Show room events",
            "--- Exploration ---",
            "loot            - Pick up items",
            "drop <name>     - Drop an item",
            "stats/status    - Show character stats",
            "inventory (i)   - Show inventory",
            "travel          - Use a transit point",
            "voice [on/off]  - Toggle voice narration",
            "save            - Save current game",
            "help (?)        - This message",
            "",
        ])
        lines.append(self._status_line())
        return "\n".join(lines)

    # ─── Formatters ───────────────────────────────────────────────────

    def _status_line(self) -> str:
        """HP/Room status bar."""
        char = self.engine.character
        if not char:
            return "No character."
        room_node = self.engine.get_current_room()
        room_type = room_node.room_type.name if room_node and hasattr(room_node, 'room_type') else "?"
        total = len(self.engine.dungeon_graph.rooms) if self.engine.dungeon_graph else 0
        visited = len(self.engine.visited_rooms)
        return (
            f"HP: {char.current_hp}/{char.max_hp} | "
            f"Room: {room_type} | "
            f"Explored: {visited}/{total}"
        )

    def _render_minimap(self) -> str:
        """Render a 7x7 graph-topology mini-map (delegates to canonical renderer)."""
        if not self.engine.dungeon_graph:
            return "(no map)"
        mm_rooms = rooms_to_minimap_dict(self.engine.dungeon_graph)
        return render_mini_map(
            mm_rooms, self.engine.current_room_id, self.engine.visited_rooms,
            rich_mode=False,
        )

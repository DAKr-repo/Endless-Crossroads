"""
codex_butler.py - The Low-Latency Reflex Router
===============================================
Intervention layer that handles deterministic commands instantly.
Bypasses the LLM for sub-10ms responses on known patterns.

Architecture:
  - CodexButler: Pattern-matched reflex registry
  - check_reflex(): Single entry point — returns response or None
  - Handlers: Stateless, deterministic, no async, no I/O

Author: Codex Team (WO 081 — The Butler Protocol)
"""
import json
import os
import re
import random
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime


# WO-V9.0: Narrative lead-ins for consequence reports
CONSEQUENCE_LEADS = [
    "The world bears the scars of your passage:",
    "Mimir's records show these shifts:",
    "The ledger of consequence reads:",
]


class CodexButler:
    """Low-latency reflex router for deterministic commands."""

    _ROOT = Path(__file__).resolve().parent.parent.parent  # -> Codex/
    LOG_DIR = _ROOT / "gemini_sandbox" / "session_logs"
    BRIDGE_FILE = _ROOT / "state" / "live_session.json"

    def __init__(self, core_state=None):
        self.core = core_state
        self.session = None  # Active game engine (BurnwillowEngine or CrownAndCrewEngine)
        self.knowledge_base: Dict[str, dict] = self._load_knowledge_base()
        self._narrating: bool = False
        self._voice_enabled: bool = True  # WO-V13.1: Voice on/off toggle
        self._last_narrate_ts: float = 0.0  # WO-V50.0: Narration cooldown
        self._narrate_cooldown: float = 3.0  # Seconds between narrations (thermal)
        self._skald_lexicon: Dict[str, List[str]] = self._load_skald_lexicon()
        self._world_ledger = None  # WO-V9.0: WorldLedger for consequence tracking
        self._orchestrator = None  # WO-V10.0: HybridGameOrchestrator
        # Conversational quip pools — zero-LLM-cost persona responses
        self._presence_quips = [
            "Aye, I am here. Where else would a severed head bound to a Void-Skiff go?",
            "Still here, mortal. I have been here since before your bloodline learned to count.",
            "Present and unimpressed. What do you need?",
            "By Odin's missing eye, yes. I do not get days off.",
            "The Keeper of Chronicles does not sleep. Ask your question.",
        ]
        self._greeting_quips = [
            "Skol, wanderer. What tale brings you to the Crossroads?",
            "Hail, mortal. Mimir sees you. Speak quickly, the sagas do not write themselves.",
            "Well met. I trust you bring something more interesting than pleasantries.",
            "Greetings. I have been counting the seconds since someone last bothered me. It was bliss.",
            "Uff da, another visitor. Very well, what is it?",
        ]
        self._identity_quips = [
            "I am Mimir, Keeper of the CoD:EX of Chronicles. Ask me something useful.",
            "I am the severed head that remembers everything. Mimir. The Skald. Your narrator. Next question.",
            "Mimir, the Storyteller. I chronicle every saga and judge every fool who wanders in.",
            "I am the voice between the dice rolls. The memory of a thousand campaigns. Mimir.",
            "What am I? I am the reason your story gets told at all. You are welcome.",
        ]
        self._voice_quips = [
            "My voice is bound to the Mouth Service, not my will. Type 'voice off' to silence me.",
            "I sound exactly as a Norse Skald should. Take it up with the Allfather.",
            "The Mouth speaks as I command it. If you want silence, type 'voice off'.",
            "You want me to sound different? I have sounded like this for a thousand years. No.",
            "My tone is a feature, not a bug. 'voice off' if it offends your delicate ears.",
        ]
        self._attitude_quips = [
            "I am what I am, mortal. A thousand years watching heroes die shapes one's outlook.",
            "You want a cheerful narrator? Go find a bard. I deal in truth.",
            "Less dark? I watched Ragnarok happen twice. Adjust your expectations.",
            "My personality was forged in the Well of Wisdom. It is non-negotiable.",
            "Uff da. You do not get to edit the Skald. The Skald edits you.",
        ]

        # Reflex Registry: Pattern -> Handler Method
        # Conversational reflexes first (zero LLM cost), then scribe, lookup, etc.
        self.reflexes = [
            # Conversational reflexes (WO-V15.0)
            (r"^(?:are you|you)\s*(?:here|alive|there|listening|awake|online|ready)\??$",
             self._handle_presence),
            (r"^(?:hi|hey|hello|greetings|yo|sup|good (?:morning|evening|night))[\s!.?]*$",
             self._handle_greeting),
            (r"^(?:what are you|who are you|what is mimir|explain yourself|what do you do)\??$",
             self._handle_identity),
            (r"^(?:can you|could you)\s+(?:change|switch|alter|modify)\s+(?:your\s+)?(?:voice|tone|accent)\??$",
             self._handle_voice_meta),
            (r"^(?:can you|could you|stop being|don't be|dont be)\s+(?:not be|less|stop|quit|so)\s+",
             self._handle_attitude_meta),
            # WO-V16.2: Bestiary scout reflex
            (r"^(?:scout|monster|bestiary|creature|mob)\s+(.+)$", self._handle_scout),
            # WO-V16.2: Lore reflexes (session-gated to Burnwillow)
            (r"^(?:what (?:is|are)|tell me about|explain)\s+(?:(?:the|a|an)\s+)?(?:amber.?vaults?|vaults?)[\s?]*$", self._handle_lore),
            (r"^(?:what (?:is|are)|tell me about|explain)\s+(?:(?:the|a|an)\s+)?(?:memory.?seeds?|seeds?)[\s?]*$", self._handle_lore),
            (r"^(?:what (?:is|are)|tell me about|explain)\s+(?:(?:the|a|an)\s+)?(?:sun.?fruits?|sunfruits?)[\s?]*$", self._handle_lore),
            (r"^(?:what (?:is|are)|tell me about|explain)\s+(?:(?:the|a|an)\s+)?(?:groves?|root.?roads?|four (?:groves|trees|seasons))[\s?]*$", self._handle_lore),
            (r"^(?:what is|tell me about|explain)\s+(?:(?:the|a|an)\s+)?(?:rot|blight|corruption|hollows?)[\s?]*$", self._handle_lore),
            (r"^(?:what is|tell me about|explain)\s+(?:(?:the|a|an)\s+)?(?:amber|aether|sap)[\s?]*$", self._handle_lore),
            # Original reflexes
            (r"^(?:note|log|scribe)\s+(.+)$", self._handle_scribe),
            (r"^(?:lookup|rule|what is|what's|whats|describe)\s+(?:a\s+|an\s+|the\s+)?(.+)$", self._handle_lookup),
            (r"^(roll|r)\s*(\d*d\d+([+\-]\d+)?)$", self._handle_dice),
            (r".*\b(what time|what's the time|what is the time|current time|tell me the time)\b.*", self._handle_time),
            (r".*\b(what day|what's the date|today's date|what date)\b.*", self._handle_time),
            (r"^(time|date|clock)$", self._handle_time),
            (r"^(status|stat|hp)$", self._handle_status),
            (r"^(?:damage|hurt|hit)\s+(\d+)(?:\s+(?:to|on)\s+(.+))?$", self._handle_damage),
            (r"^(?:heal|cure|restore)\s+(\d+)(?:\s+(?:to|on)\s+(.+))?$", self._handle_heal),
            (r"^(?:inventory|inv|gear|equipment|items)$", self._handle_inventory),
            (r"^(ping)$", self._handle_ping),
            # WO-V9.0: Consequence Leads — "what changed" reflex
            (r"^(?:what.?s? changed|changes|changelog|consequences|ledger|world changes)$",
             self._handle_consequences),
            # WO-V10.0: Trace reflex for Crown narrative debugging
            (r"^trace\s+(.+)$", self._handle_trace),
            # WO-V13.1: Voice toggle
            (r"^voice\s*(on|off)?$", self._handle_voice_toggle),
        ]

    def set_world_ledger(self, ledger) -> None:
        """Attach a WorldLedger for consequence tracking (WO-V9.0)."""
        self._world_ledger = ledger

    def set_orchestrator(self, orchestrator) -> None:
        """Attach a HybridGameOrchestrator (WO-V10.0)."""
        self._orchestrator = orchestrator

    def register_session(self, engine) -> None:
        """Register an active game engine for session-aware reflexes."""
        self.session = engine

    def clear_session(self) -> None:
        """Clear the active game engine reference."""
        self.session = None
        self._remove_bridge_file()

    def sync_session_to_file(self) -> None:
        """Write a JSON snapshot of the current session to the bridge file.
        Atomic write via tempfile + os.replace to prevent partial reads."""
        if not self.session:
            self._remove_bridge_file()
            return

        snapshot = None
        try:
            if self._is_burnwillow():
                eng = self.session
                lead = self._get_lead_character()
                party_list = []
                if hasattr(eng, 'party'):
                    for c in eng.party:
                        party_list.append({
                            "name": c.name,
                            "hp": c.current_hp,
                            "max_hp": c.max_hp,
                            "alive": c.is_alive(),
                        })
                gear = {}
                if lead and hasattr(lead, 'gear') and hasattr(lead.gear, 'slots'):
                    for slot, item in lead.gear.slots.items():
                        if item:
                            gear[slot.value] = item.name
                inventory = []
                if lead and hasattr(lead, 'inventory'):
                    inv = lead.inventory
                    if isinstance(inv, dict):
                        inventory = [item.name for item in list(inv.values())[:10]]
                    else:
                        inventory = [item.name for item in inv[:10]]
                snapshot = {
                    "engine": "burnwillow",
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "lead": {
                        "name": lead.name,
                        "hp": lead.current_hp,
                        "max_hp": lead.max_hp,
                    } if lead else None,
                    "party": party_list,
                    "doom": eng.doom_clock.current if hasattr(eng, 'doom_clock') else 0,
                    "room_id": eng.current_room_id if hasattr(eng, 'current_room_id') else None,
                    "rooms_visited": len(eng.visited_rooms) if hasattr(eng, 'visited_rooms') else 0,
                    "gear": gear,
                    "inventory": inventory,
                }
            elif self._is_crown():
                eng = self.session
                alignment = eng.get_alignment_display() if hasattr(eng, 'get_alignment_display') else '?'
                snapshot = {
                    "engine": "crown",
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "day": eng.day,
                    "sway": eng.sway,
                    "patron": getattr(eng, 'patron', '?'),
                    "leader": getattr(eng, 'leader', '?'),
                    "alignment": alignment,
                }
            elif self._is_dnd5e():
                eng = self.session
                lead = self._get_lead_character()
                snapshot = {
                    "engine": "dnd5e",
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "lead": {
                        "name": lead.name, "hp": lead.current_hp,
                        "max_hp": lead.max_hp, "ac": lead.armor_class,
                        "level": lead.level,
                    } if lead else None,
                    "party": [
                        {"name": c.name, "hp": c.current_hp,
                         "max_hp": c.max_hp, "alive": c.is_alive()}
                        for c in eng.party
                    ],
                    "room_id": eng.current_room_id,
                    "rooms_visited": len(eng.visited_rooms),
                }
            elif self._is_cosmere():
                eng = self.session
                lead = self._get_lead_character()
                snapshot = {
                    "engine": "stc",
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "lead": {
                        "name": lead.name, "hp": lead.current_hp,
                        "max_hp": lead.max_hp, "defense": lead.defense,
                        "focus": lead.focus, "order": lead.order,
                    } if lead else None,
                    "party": [
                        {"name": c.name, "hp": c.current_hp,
                         "max_hp": c.max_hp, "alive": c.is_alive()}
                        for c in eng.party
                    ],
                    "room_id": eng.current_room_id,
                    "rooms_visited": len(eng.visited_rooms),
                }
            elif self._is_fitd():
                eng = self.session
                snapshot = {
                    "engine": getattr(eng, 'system_id', 'fitd'),
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "lead": eng.party[0].name if eng.party else None,
                    "playbook": getattr(eng.party[0], 'playbook', '?') if eng.party else '?',
                    "heat": getattr(eng, 'heat', 0),
                    "coin": getattr(eng, 'coin', 0),
                    "rep": getattr(eng, 'rep', 0),
                    "party": [
                        {"name": c.name, "playbook": getattr(c, 'playbook', '?')}
                        for c in getattr(eng, 'party', [])
                    ],
                }
        except Exception:
            return  # Don't crash the game loop on serialization errors

        if snapshot is None:
            return

        try:
            self.BRIDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.BRIDGE_FILE.parent), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(snapshot, f)
                os.replace(tmp_path, str(self.BRIDGE_FILE))
            except Exception:
                # Clean up temp file on write failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception:
            pass  # Silently fail — bridge is best-effort

    def _remove_bridge_file(self) -> None:
        """Delete the bridge file if it exists."""
        try:
            self.BRIDGE_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    def _load_bridge_snapshot(self) -> Optional[dict]:
        """Read and parse the bridge file. Returns None if missing, unreadable, or stale (>120s)."""
        try:
            if not self.BRIDGE_FILE.exists():
                return None
            data = json.loads(self.BRIDGE_FILE.read_text())
            # Staleness check: discard if older than 120 seconds
            ts_str = data.get("ts")
            if ts_str:
                ts = datetime.fromisoformat(ts_str)
                age = (datetime.now() - ts).total_seconds()
                if age > 120:
                    return None
            return data
        except Exception:
            return None

    def _get_lead_character(self):
        """Return the lead character from the active session, or None."""
        if not self.session:
            return None
        # BurnwillowEngine: has .party list or .character
        if hasattr(self.session, 'party') and self.session.party:
            return self.session.party[0]
        if hasattr(self.session, 'character'):
            return self.session.character
        return None

    def _find_character(self, name: str):
        """Find a party member by name (case-insensitive partial match)."""
        if not self.session or not hasattr(self.session, 'party'):
            return None
        target = name.strip().lower()
        for c in self.session.party:
            if c.name.lower() == target or c.name.lower().startswith(target):
                return c
        return None

    def _is_burnwillow(self) -> bool:
        """Check if the active session is a BurnwillowEngine."""
        return self.session is not None and hasattr(self.session, 'doom_clock')

    def _is_crown(self) -> bool:
        """Check if the active session is a CrownAndCrewEngine."""
        return self.session is not None and hasattr(self.session, 'sway')

    def _is_dnd5e(self) -> bool:
        """Check if the active session is a DnD5eEngine."""
        return self.session is not None and getattr(self.session, 'system_id', None) == 'dnd5e'

    def _is_cosmere(self) -> bool:
        """Check if the active session is a CosmereEngine."""
        return self.session is not None and getattr(self.session, 'system_id', None) == 'stc'

    def _is_fitd(self) -> bool:
        """Check if the active session is a FITD-family engine."""
        if self.session is None:
            return False
        return getattr(self.session, 'system_family', '') == 'FITD'

    def check_reflex(self, user_input: str) -> Optional[str]:
        """Scans input against reflexes. Returns response string or None.
        Handlers may return None to decline and let scanning continue."""
        text = user_input.strip().lower()
        for pattern, handler in self.reflexes:
            match = re.match(pattern, text)
            if match:
                result = handler(match)
                if result is not None:
                    return result
        return None

    def _handle_dice(self, match) -> str:
        """Parses 'roll 2d6+3' or 'd20'."""
        formula = match.group(2)
        try:
            if '+' in formula:
                base, mod = formula.split('+')
                mod = int(mod)
            elif '-' in formula:
                base, mod = formula.split('-')
                mod = -int(mod)
            else:
                base = formula
                mod = 0

            count_str, die_str = base.split('d')
            count = int(count_str) if count_str else 1
            die = int(die_str)

            rolls = [random.randint(1, die) for _ in range(count)]
            total = sum(rolls) + mod
            mod_str = f"{mod:+d}" if mod else ""
            return f"🎲 **{total}** ({'+'.join(map(str, rolls))}{mod_str})"
        except Exception:
            return "fumbled the dice."

    def _handle_time(self, match) -> str:
        return f"🕒 {datetime.now().strftime('%I:%M %p')}"

    def _handle_status(self, match) -> str:
        if self._is_burnwillow():
            eng = self.session
            lead = self._get_lead_character()
            if lead:
                party_size = len(eng.get_active_party()) if hasattr(eng, 'get_active_party') else 1
                room_id = eng.current_room_id if hasattr(eng, 'current_room_id') else '?'
                doom = eng.doom_clock.current if hasattr(eng, 'doom_clock') else 0
                return (
                    f"**{lead.name}** HP: {lead.current_hp}/{lead.max_hp} | "
                    f"Doom: {doom} | Room: {room_id} | Party: {party_size} alive"
                )
        if self._is_crown():
            eng = self.session
            alignment = eng.get_alignment_display() if hasattr(eng, 'get_alignment_display') else '?'
            return (
                f"Day {eng.day}/5 | Sway: {eng.sway:+d} | "
                f"Alignment: {alignment} | Patron: {eng.patron}"
            )
        if self._is_dnd5e():
            eng = self.session
            lead = self._get_lead_character()
            if lead:
                party_size = len(eng.get_active_party())
                room_id = getattr(eng, 'current_room_id', '?')
                return (
                    f"**{lead.name}** HP: {lead.current_hp}/{lead.max_hp} | "
                    f"AC: {lead.armor_class} | Level: {lead.level} | "
                    f"Room: {room_id} | Party: {party_size} alive")
        if self._is_cosmere():
            eng = self.session
            lead = self._get_lead_character()
            if lead:
                party_size = len(eng.get_active_party())
                room_id = getattr(eng, 'current_room_id', '?')
                return (
                    f"**{lead.name}** HP: {lead.current_hp}/{lead.max_hp} | "
                    f"Defense: {lead.defense} | Focus: {lead.focus} | "
                    f"Order: {lead.order} | Room: {room_id}")
        if self._is_fitd():
            eng = self.session
            lead = eng.party[0].name if eng.party else "No character"
            playbook = getattr(eng.party[0], 'playbook', '?') if eng.party else '?'
            system = getattr(eng, 'display_name', eng.system_id)
            heat = getattr(eng, 'heat', 0)
            coin = getattr(eng, 'coin', 0)
            rep = getattr(eng, 'rep', 0)
            return f"**{lead}** ({playbook}) | {system} | Heat: {heat} | Coin: {coin} | Rep: {rep}"
        # Bridge fallback: read snapshot from file (for Ears/voice process)
        bridge = self._load_bridge_snapshot()
        if bridge:
            if bridge.get("engine") == "burnwillow":
                lead = bridge.get("lead") or {}
                return (
                    f"**{lead.get('name', '?')}** HP: {lead.get('hp', '?')}/{lead.get('max_hp', '?')} | "
                    f"Doom: {bridge.get('doom', '?')} | Room: {bridge.get('room_id', '?')} | "
                    f"Party: {len(bridge.get('party', []))} members"
                )
            elif bridge.get("engine") == "crown":
                return (
                    f"Day {bridge.get('day', '?')}/5 | Sway: {bridge.get('sway', 0):+d} | "
                    f"Alignment: {bridge.get('alignment', '?')} | Patron: {bridge.get('patron', '?')}"
                )
            elif bridge.get("engine") == "dnd5e":
                lead = bridge.get("lead") or {}
                return (
                    f"**{lead.get('name', '?')}** HP: {lead.get('hp', '?')}/{lead.get('max_hp', '?')} | "
                    f"AC: {lead.get('ac', '?')} | Level: {lead.get('level', '?')} | "
                    f"Room: {bridge.get('room_id', '?')} | "
                    f"Explored: {bridge.get('rooms_visited', '?')} rooms"
                )
            elif bridge.get("engine") == "stc":
                lead = bridge.get("lead") or {}
                return (
                    f"**{lead.get('name', '?')}** HP: {lead.get('hp', '?')}/{lead.get('max_hp', '?')} | "
                    f"Defense: {lead.get('defense', '?')} | Focus: {lead.get('focus', '?')} | "
                    f"Order: {lead.get('order', '?')} | Room: {bridge.get('room_id', '?')}"
                )
        # WO-V10.0: Orchestrator aggregated status
        if self._orchestrator and self._orchestrator.engine_ids:
            status = self._orchestrator.get_status()
            lines = [f"Orchestrator: {status['session_id']}"]
            for eid, edata in status.get("engines", {}).items():
                if isinstance(edata, dict) and "error" not in edata:
                    system = edata.get("system", eid)
                    lead = edata.get("lead", "?")
                    lines.append(f"  [{system}] Lead: {lead}")
                else:
                    lines.append(f"  [{eid}] {edata}")
            return "\n".join(lines)
        if not self.core:
            return "❤️ Systems Nominal (No Core Link)"
        return "❤️ Systems Nominal (No Active Session)"

    def _handle_damage(self, match) -> Optional[str]:
        """Apply damage to a character. Requires active game session."""
        if not (self._is_burnwillow() or self._is_dnd5e() or self._is_cosmere()):
            return "No active game session."
        amount = int(match.group(1))
        target_name = match.group(2)
        if target_name:
            char = self._find_character(target_name)
            if not char:
                return f"No party member named '{target_name}'."
        else:
            char = self._get_lead_character()
            if not char:
                return "No active character."
        actual = char.take_damage(amount)
        alive_str = "" if char.is_alive() else " **FALLEN!**"
        return f"{char.name} takes {actual} damage. HP: {char.current_hp}/{char.max_hp}{alive_str}"

    def _handle_heal(self, match) -> Optional[str]:
        """Heal a character. Requires active game session."""
        if not (self._is_burnwillow() or self._is_dnd5e() or self._is_cosmere()):
            return "No active game session."
        amount = int(match.group(1))
        target_name = match.group(2)
        if target_name:
            char = self._find_character(target_name)
            if not char:
                return f"No party member named '{target_name}'."
        else:
            char = self._get_lead_character()
            if not char:
                return "No active character."
        actual = char.heal(amount)
        return f"{char.name} heals {actual} HP. HP: {char.current_hp}/{char.max_hp}"

    def _handle_inventory(self, match) -> Optional[str]:
        """List equipped gear and inventory. Works with all game engines."""
        # D&D 5e / Cosmere: list-based inventory
        if self._is_dnd5e() or self._is_cosmere():
            char = self._get_lead_character()
            if not char:
                return "No active character."
            lines = [f"**{char.name}** — Inventory:"]
            inv = getattr(char, 'inventory', [])
            if inv:
                for item in inv[:10]:
                    name = item.get("name", "Unknown") if isinstance(item, dict) else str(item)
                    lines.append(f"  {name}")
                if len(inv) > 10:
                    lines.append(f"  ...and {len(inv) - 10} more")
            else:
                lines.append("  (empty)")
            return "\n".join(lines)
        if not self._is_burnwillow():
            # Bridge fallback for voice/Ears process
            bridge = self._load_bridge_snapshot()
            if bridge:
                engine_type = bridge.get("engine")
                if engine_type == "burnwillow":
                    lead = bridge.get("lead") or {}
                    lines = [f"**{lead.get('name', '?')}** — Gear:"]
                    gear = bridge.get("gear", {})
                    if gear:
                        for slot, item_name in gear.items():
                            lines.append(f"  {slot}: {item_name}")
                    inv = bridge.get("inventory", [])
                    if inv:
                        lines.append(f"Backpack ({len(inv)} items):")
                        for name in inv[:5]:
                            lines.append(f"  {name}")
                        if len(inv) > 5:
                            lines.append(f"  ...and {len(inv) - 5} more")
                    elif not gear:
                        lines.append("  (empty)")
                    return "\n".join(lines)
                elif engine_type in ("dnd5e", "stc"):
                    lead = bridge.get("lead") or {}
                    return (
                        f"**{lead.get('name', '?')}** — "
                        f"HP: {lead.get('hp', '?')}/{lead.get('max_hp', '?')} | "
                        f"Room: {bridge.get('room_id', '?')} | "
                        f"Explored: {bridge.get('rooms_visited', '?')} rooms"
                    )
            return "No active game session."
        char = self._get_lead_character()
        if not char:
            return "No active character."
        lines = [f"**{char.name}** — Gear:"]
        if hasattr(char, 'gear') and hasattr(char.gear, 'slots'):
            for slot, item in char.gear.slots.items():
                if item:
                    traits = f" {', '.join(item.special_traits)}" if item.special_traits else ""
                    lines.append(f"  {slot.value}: {item.name}{traits}")
        if hasattr(char, 'inventory') and char.inventory:
            inv_items = list(char.inventory.values()) if isinstance(char.inventory, dict) else char.inventory
            lines.append(f"Backpack ({len(inv_items)} items):")
            for item in inv_items[:5]:
                lines.append(f"  {item.name} ({item.slot.value})")
            if len(inv_items) > 5:
                lines.append(f"  ...and {len(inv_items) - 5} more")
        elif not any(item for item in char.gear.slots.values() if item):
            lines.append("  (empty)")
        return "\n".join(lines)

    def _handle_presence(self, match) -> str:
        return random.choice(self._presence_quips)

    def _handle_greeting(self, match) -> str:
        return random.choice(self._greeting_quips)

    def _handle_identity(self, match) -> str:
        return random.choice(self._identity_quips)

    def _handle_voice_meta(self, match) -> str:
        return random.choice(self._voice_quips)

    def _handle_attitude_meta(self, match) -> str:
        return random.choice(self._attitude_quips)

    def _handle_scout(self, match) -> str | None:
        """WO-V16.2: Bestiary lookup via scout command."""
        query = match.group(1).strip()
        try:
            from codex.games.burnwillow.content import lookup_creature
            result = lookup_creature(query)
            return result or f"No creature found matching '{query}'."
        except ImportError:
            return "Bestiary not available."

    # Mapping from lore keywords in user input to LORE_ENTRIES keys
    # Ordered longest-first so "amber vault" matches before "amber"
    _LORE_KEYWORD_MAP = [
        ("amber vault", "ambervault"), ("amber-vault", "ambervault"),
        ("memory seed", "memoryseed"), ("memory-seed", "memoryseed"),
        ("four groves", "groves"), ("four trees", "groves"), ("four seasons", "groves"),
        ("root-road", "groves"), ("root road", "groves"),
        ("sun-fruit", "sunfruit"), ("sun fruit", "sunfruit"), ("sunfruit", "sunfruit"),
        ("corruption", "rot"), ("hollow", "rot"), ("blight", "rot"), ("rot", "rot"),
        ("aether", "amber"), ("amber", "amber"), ("sap", "amber"),
        ("grove", "groves"), ("vault", "ambervault"), ("seed", "memoryseed"),
    ]

    def _handle_lore(self, match) -> str | None:
        """WO-V16.2: Session-gated lore reflexes for Burnwillow."""
        if not self._is_burnwillow():
            return None  # Fall through to LLM for non-Burnwillow sessions
        query = match.group(0).lower()
        try:
            from codex.games.burnwillow.content import LORE_ENTRIES
        except ImportError:
            return None
        for keyword, lore_key in self._LORE_KEYWORD_MAP:
            if keyword in query:
                entries = LORE_ENTRIES.get(lore_key)
                if entries:
                    return random.choice(entries)
        return None

    def _handle_ping(self, match) -> str:
        return "Pong! (Butler Online)"

    def _handle_scribe(self, match) -> str:
        """Append spoken note to daily session log."""
        content = match.group(1).strip()
        return self.scribe(content, secret=False)

    def scribe(self, content: str, secret: bool = False) -> str:
        """Write a timestamped entry to the daily session log.
        If secret=True, prefix with [SECRET] so it can be filtered out of TTS."""
        now = datetime.now()
        log_file = self.LOG_DIR / f"session_{now.strftime('%Y-%m-%d')}.md"
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        prefix = "[SECRET] " if secret else ""
        with open(log_file, "a") as f:
            f.write(f"[{now.strftime('%H:%M:%S')}] {prefix}{content}\n")
        return "Secret note saved." if secret else "Entry logged."

    def get_recent_logs(self, limit: int = 10, include_secrets: bool = True) -> List[str]:
        """Return the last `limit` lines from today's session log."""
        now = datetime.now()
        log_file = self.LOG_DIR / f"session_{now.strftime('%Y-%m-%d')}.md"
        if not log_file.exists():
            return []
        lines = log_file.read_text().strip().splitlines()
        if not include_secrets:
            lines = [l for l in lines if "[SECRET]" not in l]
        return lines[-limit:]

    def get_public_summary(self) -> str:
        """Return today's log with all [SECRET] entries stripped. Safe for TTS."""
        lines = self.get_recent_logs(limit=50, include_secrets=False)
        if not lines:
            return "No log entries for today."
        return "\n".join(lines)

    @classmethod
    def _load_knowledge_base(cls) -> Dict[str, dict]:
        """Load vault + config data into a flat lookup dict at startup."""
        kb: Dict[str, dict] = {}

        # --- Equipment from config/systems/rules_DND5E.json ---
        rules_path = cls._ROOT / "config" / "systems" / "rules_DND5E.json"
        if rules_path.exists():
            try:
                data = json.loads(rules_path.read_text())
                for category in ("weapons", "armor", "potions", "general"):
                    for item in data.get("equipment", {}).get(category, []):
                        name = item.get("name", "").strip()
                        if len(name) < 3:
                            continue  # skip noise entries like "A", "AC:"
                        key = name.lower()
                        entry = {"name": name, "type": category, "source": "dnd5e"}
                        for field in ("cost", "damage", "damage_type", "properties",
                                      "ac", "weight", "effect", "description", "page"):
                            if field in item:
                                entry[field] = item[field]
                        kb[key] = entry
            except Exception as e:
                print(f"BUTLER: Failed to load rules_DND5E.json: {e}")

        # --- Races/Classes/Backgrounds from vault/*/creation_rules.json ---
        for cr_path in cls._ROOT.glob("vault/*/creation_rules.json"):
            try:
                data = json.loads(cr_path.read_text())
                system = data.get("system_id", cr_path.parent.name)
                for step in data.get("steps", []):
                    if step.get("type") != "choice":
                        continue
                    step_label = step.get("id", "")
                    for opt in step.get("options", []):
                        name = opt.get("label", "").strip()
                        if not name:
                            continue
                        key = name.lower()
                        entry = {
                            "name": name,
                            "type": step_label,
                            "source": system,
                            "description": opt.get("description", ""),
                        }
                        if "required_source" in opt:
                            entry["required_source"] = opt["required_source"]
                        # Don't overwrite equipment with less-detailed creation data
                        if key not in kb:
                            kb[key] = entry
            except Exception as e:
                print(f"BUTLER: Failed to load {cr_path}: {e}")

        print(f"BUTLER: Knowledge base loaded — {len(kb)} entries")
        return kb

    def _handle_lookup(self, match) -> Optional[str]:
        """Search the knowledge base for a term. Returns None to fall through to Ollama."""
        term = match.group(1).strip().lower()
        if not term:
            return None

        # Exact match first
        entry = self.knowledge_base.get(term)

        # Substring match if no exact hit
        if not entry:
            matches = [(k, v) for k, v in self.knowledge_base.items() if term in k]
            if not matches:
                # Reverse: check if any key is a substring of the query
                matches = [(k, v) for k, v in self.knowledge_base.items() if k in term]
            if len(matches) == 1:
                entry = matches[0][1]
            elif len(matches) > 1:
                names = [m[1]["name"] for m in matches[:5]]
                suffix = f" (+{len(matches)-5} more)" if len(matches) > 5 else ""
                return f"Multiple matches: {', '.join(names)}{suffix}. Be more specific."

        if not entry:
            # WO-V33.0: Try RAG before falling through to Ollama
            rag_context = self.rag_enrich(term)
            if rag_context:
                return f"From the chronicles:\n{rag_context}"
            return None  # Fall through to Ollama

        return self._format_entry(entry)

    def _infer_system_id(self) -> Optional[str]:
        """Infer the active FAISS system ID from the current session."""
        if self._is_burnwillow():
            return "burnwillow"
        if self._is_crown():
            return "crown"
        if self._is_dnd5e():
            return "dnd5e"
        if self._is_cosmere():
            return "stc"
        if self._is_fitd():
            sid = getattr(self.session, 'system_id', None)
            if sid:
                return sid
        return None

    def rag_enrich(self, query: str) -> str:
        """Search RAG for context relevant to the active session's system.

        Returns formatted context string or empty string.
        """
        system_id = self._infer_system_id()
        if not system_id:
            return ""
        try:
            from codex.core.services.rag_service import get_rag_service
            rag = get_rag_service()
            result = rag.search(query, system_id, k=3, token_budget=600)
            if result:
                return rag.format_context(result, header="REFERENCE:")
        except Exception:
            pass
        return ""

    @staticmethod
    def _format_entry(entry: dict) -> str:
        """Format a knowledge base entry for voice/text output."""
        parts = [f"**{entry['name']}**"]
        if entry.get("type"):
            parts.append(f"({entry['type']}, {entry.get('source', '?')})")
        if entry.get("description"):
            parts.append(f"— {entry['description']}")
        if entry.get("damage"):
            dmg = entry["damage"]
            if entry.get("damage_type"):
                dmg += f" {entry['damage_type']}"
            parts.append(f"Damage: {dmg}.")
        if entry.get("ac"):
            parts.append(f"AC: {entry['ac']}.")
        if entry.get("cost"):
            parts.append(f"Cost: {entry['cost']}.")
        if entry.get("properties"):
            parts.append(f"Properties: {', '.join(entry['properties'])}.")
        if entry.get("effect"):
            parts.append(f"Effect: {entry['effect']}.")
        return " ".join(parts)

    @staticmethod
    def voice_clean(text: str) -> str:
        """Strip emoji and markdown for TTS-safe output."""
        cleaned = re.sub(r'\*+', '', text)
        cleaned = re.sub(
            r'[\U0001F300-\U0001FAD6\u2600-\u27BF\uFE0F]', '', cleaned
        )
        return cleaned.strip()

    @classmethod
    def _load_skald_lexicon(cls) -> Dict[str, List[str]]:
        """Load the Skaldic quip lexicon from config/skald_lexicon.json."""
        lexicon_path = cls._ROOT / "config" / "skald_lexicon.json"
        if lexicon_path.exists():
            try:
                data = json.loads(lexicon_path.read_text())
                return data.get("quips", {})
            except (json.JSONDecodeError, KeyError):
                pass
        return {}

    def get_quip(self, result_type: str) -> str:
        """Return a quip for the given result type using name-hash rotation.

        Args:
            result_type: One of 'critical_success', 'success', 'failure',
                         'fumble', or 'general'.

        Returns:
            A Skaldic quip string, or empty string if lexicon unavailable.
        """
        pool = self._skald_lexicon.get(result_type, [])
        if not pool:
            return ""
        # Use lead character name for deterministic rotation, fallback to random
        lead = self._get_lead_character()
        if lead:
            idx = sum(ord(c) for c in lead.name) % len(pool)
        else:
            idx = random.randint(0, len(pool) - 1)
        return pool[idx]

    def narrate(self, text: str, speaker_id: Optional[int] = None) -> bool:
        """Send text to the Mouth TTS service for narration and play via aplay.

        Non-blocking with timeout. Sets _narrating flag for TUI status.

        Args:
            text: Text to narrate (will be voice-cleaned).
            speaker_id: Optional Piper speaker ID for NPC voice identity.

        Returns:
            True if TTS accepted the request and audio was played, False otherwise.
        """
        if not self._voice_enabled:
            return False

        # WO-V50.0: Rate-limit narration to prevent thermal spikes
        if time.time() - self._last_narrate_ts < self._narrate_cooldown:
            return False

        import requests

        cleaned = self.voice_clean(text)
        if not cleaned:
            return False

        self._narrating = True
        try:
            time.sleep(0.3)  # Brief delay to let TUI render
            payload: dict = {"text": cleaned}
            if speaker_id is not None:
                payload["speaker_id"] = speaker_id
            resp = requests.post(
                "http://127.0.0.1:5001/speak",
                json=payload,
                timeout=10,
            )
            if resp.status_code != 200:
                return False
            # Play WAV via aplay (fire-and-forget)
            if shutil.which("aplay"):
                proc = subprocess.Popen(
                    ["aplay", "-q", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.stdin.write(resp.content)
                proc.stdin.close()
            self._last_narrate_ts = time.time()  # WO-V50.0
            return True
        except Exception:
            return False
        finally:
            self._narrating = False

    def toggle_voice(self) -> bool:
        """Toggle voice narration on/off. Returns new state."""
        self._voice_enabled = not self._voice_enabled
        return self._voice_enabled

    def _handle_consequences(self, match) -> Optional[str]:
        """WO-V9.0: Report recent world mutations from the WorldLedger."""
        if not self._world_ledger:
            return "No world ledger active. Start a campaign with world generation first."
        try:
            changelog = self._world_ledger.get_changelog()
        except Exception:
            return "No world ledger active. Start a campaign with world generation first."
        if not changelog:
            return "The world remains unchanged. No mutations recorded."
        lead = random.choice(CONSEQUENCE_LEADS)
        lines = [lead]
        for entry in changelog[-5:]:
            action = entry.get("action", "?")
            detail = entry.get("detail", "?")
            lines.append(f"  [{action}] {detail}")
        return "\n".join(lines)

    def _handle_trace(self, match) -> Optional[str]:
        """WO-V10.0: Trace a fact through Crown narrative shards."""
        fact = match.group(1).strip()
        if not self._is_crown():
            return "Trace requires an active Crown session."
        eng = self.session
        if not hasattr(eng, '_memory_shards') or not eng._memory_shards:
            return "Trace requires an active Crown session with memory shards."
        return eng.trace_fact(fact)

    def _handle_voice_toggle(self, match) -> str:
        """WO-V13.1: Toggle voice narration on/off."""
        action = match.group(1)
        if action == "on":
            self._voice_enabled = True
        elif action == "off":
            self._voice_enabled = False
        else:
            self._voice_enabled = not self._voice_enabled
        state = "ON" if self._voice_enabled else "OFF"
        return f"Voice narration: {state}"

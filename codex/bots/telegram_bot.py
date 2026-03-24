#!/usr/bin/env python3
"""
CODEX TELEGRAM BOT — MIRROR PROTOCOL
-------------------------------------
Telegram interface for C.O.D.E.X. mirroring Discord functionality.
Implements the Crown & Crew game loop with ASCII terminal aesthetics.

Uses python-telegram-bot v20+ (async API).
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

from codex.games.crown.engine import CrownAndCrewEngine
from codex.games.burnwillow.bridge import BurnwillowBridge
from codex.games.bridge import UniversalGameBridge
from codex.core.services.broadcast import GlobalBroadcastManager
from codex.core.menu import CodexMenu

try:
    from codex.forge.omni_forge import OmniForge
    OMNI_FORGE_AVAILABLE = True
except ImportError:
    OMNI_FORGE_AVAILABLE = False

try:
    from codex.integrations.tarot import get_card_for_context, format_tarot_text
    TAROT_AVAILABLE = True
except ImportError:
    TAROT_AVAILABLE = False

_MENU = CodexMenu()

# Load environment
load_dotenv()

_ROOT = Path(__file__).resolve().parent.parent.parent  # -> Codex/

logger = logging.getLogger("CODEX.Telegram")


# =============================================================================
# MIRROR PROTOCOL TEMPLATES — ASCII Terminal Aesthetic
# =============================================================================

def generate_sway_bar(sway: int) -> str:
    """Generate visual sway bar (-3 to +3)."""
    positions = ['═'] * 7
    index = sway + 3  # Convert -3..+3 to 0..6
    positions[index] = '■'
    bar = ''.join(positions)
    return f"👑{bar}🏴"


def wrap_lines(text: str, max_len: int = 52) -> list[str]:
    """Wrap text into lines of max_len characters."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_len:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def format_morning(day: int, world_prompt: str) -> str:
    """Phase 1: World Card template."""
    lines = wrap_lines(world_prompt, 52)
    # Pad to 4 lines
    while len(lines) < 4:
        lines.append("")

    return f"""🌲
```
╔════════════════════════════════════════════════════════╗
║                                                        ║
║   D A Y  {day}  —  T H E   R O A D   A W A I T S      ║
║                                                        ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║   {lines[0]:<52} ║
║   {lines[1]:<52} ║
║   {lines[2]:<52} ║
║   {lines[3]:<52} ║
║                                                        ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║   the party may speak freely.                          ║
║   type /travel when ready to move on.                  ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```"""


def format_campfire(campfire_prompt: str) -> str:
    """Phase 2: Allegiance Choice template."""
    lines = wrap_lines(campfire_prompt, 48)
    while len(lines) < 2:
        lines.append("")

    return f"""🔥
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│    the fire burns low. shadows press close.          │
│                                                      │
│ ──────────────────────────────────────────────────── │
│                                                      │
│    "{lines[0]}"
│    "{lines[1]}"
│                                                      │
│ ──────────────────────────────────────────────────── │
│                                                      │
│    in the dark, you must choose.                     │
│                                                      │
│        👑  CROWN  —  serve the throne                │
│        🏴  CREW   —  serve the people                │
│                                                      │
│    type your allegiance: crown or crew               │
│                                                      │
└──────────────────────────────────────────────────────┘
```"""


def format_council(day: int, dilemma: dict) -> str:
    """Phase 3: Council Vote template."""
    lines = wrap_lines(dilemma["prompt"], 50)
    while len(lines) < 2:
        lines.append("")

    return f"""⚖️
```
╔════════════════════════════════════════════════════════╗
║                                                        ║
║   M I D N I G H T   C O U N C I L  —  D A Y  {day}     ║
║                                                        ║
║ ══════════════════════════════════════════════════════ ║
║                                                        ║
║   THE DILEMMA:                                         ║
║                                                        ║
║   {lines[0]:<52} ║
║   {lines[1]:<52} ║
║                                                        ║
║ ══════════════════════════════════════════════════════ ║
║                                                        ║
║   [ 1 ]  {dilemma['option_1']:<46} ║
║                                                        ║
║   [ 2 ]  {dilemma['option_2']:<46} ║
║                                                        ║
║ ══════════════════════════════════════════════════════ ║
║                                                        ║
║   cast your vote:  1  or  2                            ║
║   the majority will bind you all.                      ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```"""


def format_legacy(engine: CrownAndCrewEngine) -> str:
    """Finale: Legacy Receipt template."""
    alignment = engine.get_alignment()
    dominant = engine.get_dominant_tag()

    from codex.games.crown.engine import LEGACY_TITLES
    title_data = LEGACY_TITLES.get(
        (alignment, dominant),
        {"title": "The Unknown", "desc": "Your path defies naming."}
    )

    sway_bar = generate_sway_bar(engine.sway)

    return f"""⚔️
```
╔════════════════════════════════════════════════════════╗
║                                                        ║
║     T H E   C A M P A I G N   I S   O V E R           ║
║                                                        ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║   PATRON:    {engine.patron:<42} ║
║   LEADER:    {engine.leader:<42} ║
║                                                        ║
║ ────────────────────────────────────────────────────── ║
║                                                        ║
║   FINAL SWAY:   [{sway_bar}]   ({engine.sway:+d})             ║
║                                                        ║
║   ALIGNMENT:    {alignment:<40} ║
║   DOMINANT:     {dominant:<40} ║
║                                                        ║
║ ────────────────────────────────────────────────────── ║
║                                                        ║
║   LEGACY TITLE:                                        ║
║                                                        ║
║       ★  {title_data['title']:<44} ★ ║
║                                                        ║
║   "{title_data['desc']}"
║                                                        ║
╚════════════════════════════════════════════════════════╝
```
_this record has been sealed._"""


# =============================================================================
# SESSION STATE MACHINE
# =============================================================================

class Phase(Enum):
    """Game phases for state machine."""
    IDLE = auto()
    MENU = auto()              # Main menu shown, awaiting selection
    DUNGEON = auto()           # Free-text Burnwillow input
    MORNING = auto()           # World card shown, awaiting /travel
    CAMPFIRE = auto()          # Allegiance choice, awaiting crown/crew
    COUNCIL = auto()           # Group dilemma, awaiting 1/2
    FINALE = auto()            # Game complete
    DND5E = auto()             # WO V4.0 — D&D 5e dungeon session
    COSMERE = auto()           # WO V4.0 — Cosmere dungeon session
    REST = auto()              # WO-V23.0 — Rest choice after council
    ASHBURN_HEIR = auto()      # WO-V23.0 — Ashburn heir selection
    ASHBURN_LEGACY = auto()    # WO-V23.0 — Ashburn legacy choice
    QUEST_SELECT = auto()      # WO-V23.0 — Quest archetype selection
    OMNI = auto()              # WO-V25.0 — Omni-Forge sub-menu
    BITD = auto()              # Blades in the Dark session
    SAV = auto()               # Scum and Villainy session
    BOB = auto()               # Band of Blades session
    CBRPNK = auto()            # CBR+PNK session
    CANDELA = auto()           # Candela Obscura session
    CREATING = auto()          # Character creation in progress


def _scan_pending_prologues() -> list[dict]:
    """Scan saves/ for campaigns with prologue_pending."""
    saves_dir = _ROOT / "saves"
    if not saves_dir.exists():
        return []
    pending = []
    for item in saves_dir.iterdir():
        if item.is_dir():
            manifest_path = item / "campaign.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        data = json.load(f)
                    if data.get('prologue_pending'):
                        pending.append(data)
                except (json.JSONDecodeError, OSError):
                    pass
    return pending


@dataclass
class TelegramSession:
    """Stateful session manager for a single Telegram chat."""
    chat_id: int
    phase: Phase = Phase.IDLE
    engine: Optional[CrownAndCrewEngine] = None
    current_dilemma: Optional[dict] = None
    game_type: str = ""
    bridge: Optional[object] = None  # BurnwillowBridge or UniversalGameBridge
    mimir: object = None  # WO 088 — AI narrative bridge
    voice_enabled: bool = False      # WO-V50.0: Voice narration flag
    # WO-V35.0: Parity gap fields
    conditions: object = None       # ConditionTracker (optional)
    initiative_order: list = field(default_factory=list)
    active_turn: str = ""
    scene_state: object = None      # _FITDSceneState (optional)
    stacked_char: object = None     # StackedCharacter (for engine stacking)
    wizard_state: object = None     # HeadlessWizard (for multi-step creation)
    dm_dashboard: object = None     # DMDashboard instance

    def start_game(self) -> str:
        """Initialize a new Crown & Crew session."""
        if self.phase != Phase.IDLE:
            return "⚠️ A game is already in progress. Use /end to stop it first."

        self.engine = CrownAndCrewEngine(mimir=self.mimir)
        self.phase = Phase.MORNING

        world_prompt = self.engine.get_world_prompt()
        # WO-V25.0: Tarot card
        if TAROT_AVAILABLE:
            card = format_tarot_text(get_card_for_context("world"), world_prompt[:200])
            world_prompt = f"```\n{card}\n```\n\n{world_prompt}"
        return format_morning(self.engine.day, world_prompt)

    def handle_travel(self) -> str:
        """Transition from MORNING to CAMPFIRE."""
        if self.phase != Phase.MORNING:
            return "⚠️ You can only travel during the morning phase."

        self.phase = Phase.CAMPFIRE

        # Day 3 Breach - skip campfire
        if self.engine.is_breach_day():
            breach_msg = "👁️ *THE BREACH*\n\n" + self.engine.get_secret_witness()
            self.phase = Phase.COUNCIL
            self._generate_dilemma()
            return breach_msg + "\n\n" + format_council(self.engine.day, self.current_dilemma)

        campfire_prompt = self.engine.get_campfire_prompt()
        # WO-V25.0: Tarot card
        if TAROT_AVAILABLE:
            card = format_tarot_text(get_card_for_context("campfire"), campfire_prompt[:200])
            campfire_prompt = f"```\n{card}\n```\n\n{campfire_prompt}"
        return format_campfire(campfire_prompt)

    def handle_allegiance(self, side: str) -> str:
        """Process allegiance choice."""
        if self.phase != Phase.CAMPFIRE:
            return None  # Ignore if not in campfire phase

        side = side.lower().strip()
        if side not in ("crown", "crew"):
            return None  # Not a valid allegiance

        # Declare allegiance
        result = self.engine.declare_allegiance(side)

        # Get narrative prompt for chosen side
        narrative = self.engine.get_prompt(side)
        # WO-V25.0: Tarot card
        if TAROT_AVAILABLE:
            card = format_tarot_text(get_card_for_context(side), narrative[:200])
            narrative = f"```\n{card}\n```\n\n{narrative}"

        # Check Drifter's Tax
        tax_msg = ""
        if self.engine.check_drifter_tax():
            tax_msg = "\n\n⚠️ *DRIFTER'S TAX:* Neutrality has consequences..."

        # WO-V24.1: Ashburn legacy check (if engine supports it)
        if hasattr(self.engine, 'generate_legacy_check'):
            check = self.engine.generate_legacy_check()
            if check.get("triggered"):
                self.phase = Phase.ASHBURN_LEGACY
                response = f"✓ *{side.upper()}* chosen.\n\n"
                response += f"_{narrative}_\n"
                response += tax_msg
                response += f"\n\n⚠️ *LEGACY CALL*\n_{check['prompt']}_\n\n"
                response += "Type `1` (Obey) or `2` (Lie)."
                return response

        # Transition to Council
        self.phase = Phase.COUNCIL
        self._generate_dilemma()

        response = f"✓ *{side.upper()}* chosen.\n\n"
        response += f"_{narrative}_\n"
        response += tax_msg
        response += "\n\n" + format_council(self.engine.day, self.current_dilemma)

        return response

    def handle_vote(self, choice: str) -> str:
        """Process council vote (WO-V23.0: REST phase + arc_length)."""
        if self.phase != Phase.COUNCIL:
            return None

        choice = choice.strip()
        if choice not in ("1", "2"):
            return None

        # Record choice outcome
        if choice == "1":
            outcome = self.current_dilemma["option_1"]
        else:
            outcome = self.current_dilemma["option_2"]

        result = f"📜 The council chose: *{outcome}*\n\n"

        # Check if final day — skip rest
        if self.engine.day >= self.engine.arc_length:
            day_result = self.engine.end_day()
            result += day_result + "\n\n"
            self.phase = Phase.FINALE
            # WO-V25.0: Tarot card for legacy
            if TAROT_AVAILABLE:
                card = format_tarot_text(get_card_for_context("legacy"), "Your journey ends. The border awaits.")
                result += f"```\n{card}\n```\n\n"
            result += format_legacy(self.engine)
            self.phase = Phase.IDLE
            self.engine = None
            return result

        # Offer rest choice (WO-V23.0)
        self.phase = Phase.REST
        result += "🛏️ *THE CAMP*\n\n"
        result += "How do you rest?\n\n"
        result += "`long` — Full rest, advance to next day.\n"
        result += "`short` — Brief respite, stay on current day.\n"
        result += "`skip` — Press on. Sway decays toward neutral."
        return result

    def handle_rest(self, choice: str) -> str:
        """Process rest choice (WO-V23.0)."""
        if self.phase != Phase.REST:
            return None

        choice = choice.lower().strip()
        if choice not in ("long", "short", "skip"):
            return None

        if choice == "long":
            day_result = self.engine.trigger_long_rest()
        elif choice == "short":
            short_msg = self.engine.trigger_short_rest()
            self.phase = Phase.MORNING
            world_prompt = self.engine.get_world_prompt()
            return f"☕ Short Rest\n_{short_msg}_\n\n" + format_morning(self.engine.day, world_prompt)
        else:
            skip_msg = self.engine.skip_rest()
            day_result = self.engine.end_day()

        # Check if game over after rest
        if self.engine.day > self.engine.arc_length:
            result = f"🛏️ {day_result if choice == 'long' else skip_msg}\n\n"
            self.phase = Phase.FINALE
            result += format_legacy(self.engine)
            self.phase = Phase.IDLE
            self.engine = None
            return result

        # Next day - return to morning
        self.phase = Phase.MORNING
        world_prompt = self.engine.get_world_prompt()
        return f"🛏️ {day_result}\n\n" + format_morning(self.engine.day, world_prompt)

    def end_game(self) -> str:
        """Force end the current session."""
        if self.phase == Phase.IDLE:
            return "No active game to end."

        self.phase = Phase.IDLE
        self.engine = None
        self.current_dilemma = None
        self.bridge = None
        self.game_type = ""
        self.conditions = None
        self.initiative_order = []
        self.active_turn = ""
        return "\U0001f6d1 Campaign abandoned. The road claims another soul."

    def get_status(self) -> str:
        """Get current session status."""
        if self.phase == Phase.IDLE or not self.engine:
            return "No active campaign. Use /play to begin."

        tier = self.engine.get_tier()
        sway_bar = generate_sway_bar(self.engine.sway)

        arc = self.engine.arc_length
        return f"""```
╔════════════════════════════════════╗
║       SESSION STATUS               ║
╠════════════════════════════════════╣
║  Day:      {self.engine.day}/{arc:<19} ║
║  Phase:    {self.phase.name:<22} ║
║  Sway:     [{sway_bar}]      ║
║  Status:   {tier['name']:<22} ║
║  Patron:   {self.engine.patron:<22} ║
║  Leader:   {self.engine.leader:<22} ║
╚════════════════════════════════════╝
```"""

    def _generate_dilemma(self):
        """Generate a council dilemma from engine (WO-V23.0)."""
        dilemma = self.engine.get_council_dilemma()
        # Normalize keys to option_1/option_2 for Telegram format_council()
        self.current_dilemma = {
            "prompt": dilemma["prompt"],
            "option_1": dilemma.get("crown", dilemma.get("option_1", "Side with authority.")),
            "option_2": dilemma.get("crew", dilemma.get("option_2", "Side with the people.")),
        }


# =============================================================================
# SESSION REGISTRY
# =============================================================================

sessions: dict[int, TelegramSession] = {}
_mimir_ref: object = None  # WO 088 — set by run_telegram_bot()


def get_session(chat_id: int) -> TelegramSession:
    """Get or create a session for a chat."""
    if chat_id not in sessions:
        sessions[chat_id] = TelegramSession(chat_id=chat_id, mimir=_mimir_ref)
    return sessions[chat_id]


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome = """<b>🌲 Welcome to C.O.D.E.X.</b>
<i>Chronicles of Destiny: Endless Crossroads</i>

Your journey begins. Every choice shapes your soul.

<b>Quick Commands:</b>
• /play — Begin Crown &amp; Crew campaign
• /status — View game state &amp; vitals
• /help — Show all commands

<i>Type /play to begin your journey.</i>"""

    await update.message.reply_text(welcome, parse_mode='HTML')


async def cmd_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /play command — alias for /menu."""
    await cmd_menu(update, context)


async def cmd_travel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /travel command - advance from morning."""
    session = get_session(update.effective_chat.id)
    response = session.handle_travel()
    await update.message.reply_text(response, parse_mode='Markdown')


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command with HTML formatting."""
    session = get_session(update.effective_chat.id)

    if session.phase != Phase.IDLE and session.engine:
        engine = session.engine
        tier = engine.get_tier()
        sway_visual = engine.get_sway_visual()

        # Determine allegiance color indicator
        if engine.sway < 0:
            allegiance_icon = "👑"  # Crown
        elif engine.sway > 0:
            allegiance_icon = "🏴"  # Crew
        else:
            allegiance_icon = "⚖️"  # Neutral

        response = (
            f"<b>⚔️ DAY {engine.day}/{engine.arc_length} — {session.phase.name}</b>\n\n"
            f"<code>{sway_visual}</code>\n\n"
            f"{allegiance_icon} <b>Allegiance:</b> {tier['name']}\n"
            f"<i>{tier['desc']}</i>\n\n"
            f"◈ <b>Dominant Trait:</b> {engine.get_dominant_tag()}\n"
            f"📊 <b>Sway:</b> <code>{engine.sway:+d}</code>\n\n"
            f"<i>Patron: {engine.patron}</i>\n"
            f"<i>Leader: {engine.leader}</i>"
        )
    elif session.bridge:
        # WO-V35.0: Dungeon session status (Burnwillow, DnD5e, Cosmere)
        bw_engine = getattr(session.bridge, 'engine', None)
        if bw_engine:
            char = getattr(bw_engine, 'character', None)
            lines = [f"<b>\u2694\ufe0f {session.game_type.upper()} SESSION</b>\n"]

            if char:
                hp = char.current_hp
                max_hp = char.max_hp
                bar_len = 20
                filled = int((hp / max_hp) * bar_len) if max_hp > 0 else 0
                bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
                lines.append(f"<b>{char.name}</b>")
                lines.append(f"<code>[{bar}] {hp}/{max_hp} HP</code>")

                # System-specific extras
                if session.game_type == "burnwillow" and hasattr(bw_engine, 'doom_clock'):
                    doom = bw_engine.doom_clock.current
                    lines.append(f"\U0001f480 Doom: <code>{doom}/20</code>")
                    lines.append(f"\U0001f3e0 Room: <code>{bw_engine.current_room_id}</code>")
                elif session.game_type == "dnd5e":
                    ac = getattr(char, 'armor_class', 10)
                    level = getattr(char, 'level', 1)
                    lines.append(f"\U0001f6e1 AC: <code>{ac}</code> | Level: <code>{level}</code>")
                elif session.game_type == "cosmere":
                    focus = getattr(char, 'focus', 0)
                    lines.append(f"\u2728 Focus: <code>{focus}</code>")

            # Condition icons
            if session.conditions:
                all_entities = session.conditions.get_all_entities()
                if all_entities:
                    from codex.core.mechanics.conditions import format_condition_icons
                    lines.append("\n<b>Status Effects:</b>")
                    for entity in all_entities:
                        conds = session.conditions.get_conditions(entity)
                        icons = format_condition_icons(conds)
                        lines.append(f"  {entity}: {icons}")

            # Active turn
            if session.active_turn:
                lines.append(f"\n\u2694\ufe0f <b>Active Turn:</b> {session.active_turn}")

            response = "\n".join(lines)
        else:
            response = (
                "<b>\U0001f4e1 SESSION STATUS</b>\n\n"
                "Active session (no engine data)."
            )
    else:
        response = (
            "<b>\U0001f4e1 SESSION STATUS</b>\n\n"
            "No active campaign.\n"
            "Use /play to begin Crown & Crew."
        )

    await update.message.reply_text(response, parse_mode='HTML')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """<b>📡 MIMIR UPLINK — Commands</b>

<b>System Commands:</b>
• /menu — Main Menu / Module Select
• /play — Alias for /menu
• /prologue — Launch Session Zero
• /travel — Advance from morning phase
• /burnwillow — Start dungeon run
• /dnd5e — D&amp;D 5e dungeon crawl
• /cosmere — Cosmere dungeon crawl
• /stop — End Session / Abort
• /status — View game state &amp; vitals
• /ping — Instant health check
• /help — Display this transmission
• /clear — Purge session memory
• /summon — Acknowledge presence

<b>Tools:</b>
• /voice — Toggle voice narration
• /sheet — Character stats
• /atlas — World atlas
• /rumors — Town crier rumors

<b>Gameplay:</b>
• Type <code>crown</code> or <code>crew</code> — Declare allegiance
• Type <code>1</code> or <code>2</code> — Council vote

<b>Game Phases:</b>
1. 🌲 Morning — World card, party discussion
2. 🔥 Campfire — Individual allegiance choice
3. ⚖️ Council — Group dilemma vote

<i>Latency is an opportunity for lore.</i>"""

    await update.message.reply_text(help_text, parse_mode='HTML')


async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /end command — alias for /stop."""
    await cmd_stop(update, context)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command — display main navigation menu."""
    session = get_session(update.effective_chat.id)
    session.phase = Phase.MENU

    # WO 109 — data-driven menu from CodexMenu
    menu_def = _MENU.get_menu("telegram")
    lines = [f"<b>\U0001f4e1 {menu_def.title}</b>", "", "Select a module to begin.", ""]
    for opt in menu_def.options:
        lines.append(f"<b>[{opt.key}]</b> {opt.label}")
        lines.append(f"     {opt.description}")
        lines.append("")
    lines.append(f"<i>{menu_def.footer}</i>")
    menu_text = "\n".join(lines)

    await update.message.reply_text(menu_text, parse_mode='HTML')


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command — end session and return to idle."""
    session = get_session(update.effective_chat.id)
    response = session.end_game()
    await update.message.reply_text(response, parse_mode='Markdown')


async def cmd_rest_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rest command -- player-initiated rest via bridge (WO-V35.0)."""
    session = get_session(update.effective_chat.id)
    if not session.bridge:
        await update.message.reply_text("No active session. Start a game first.")
        return
    rest_type = context.args[0] if context.args else "short"
    result = session.bridge.step(f"rest {rest_type}")
    await update.message.reply_text(f"```\n{result}\n```", parse_mode='Markdown')


async def cmd_recap_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recap command -- show session recap (WO-V37.0)."""
    session = get_session(update.effective_chat.id)
    if not session.bridge:
        await update.message.reply_text("No active session. Start a game first.")
        return
    if hasattr(session.bridge, 'get_session_stats'):
        stats = session.bridge.get_session_stats()
        kill_info = stats.get("kills", {})
        tier_parts = ", ".join(
            f"T{t}: {c}" for t, c in sorted(kill_info.get("by_tier", {}).items())
        )
        lines = [
            "<b>Session Recap</b>",
            f"Enemies slain: {kill_info.get('total', 0)} ({tier_parts})" if tier_parts else f"Enemies slain: {kill_info.get('total', 0)}",
            f"Rooms explored: {stats.get('rooms_explored', 0)} | Cleared: {stats.get('rooms_cleared', 0)}",
            f"Doom: {stats.get('doom', 0)}/20",
        ]
        loot_list = stats.get("loot", [])
        if loot_list:
            lines.append(f"Loot: {', '.join(loot_list[:10])}")
        party = stats.get("party", [])
        if party:
            lines.append("\n<b>Party Status</b>")
            for m in party:
                lines.append(f"  {m['name']}: {m['hp']}/{m['max_hp']} HP")
        await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    else:
        result = session.bridge.step("recap")
        await update.message.reply_text(f"```\n{result}\n```", parse_mode='Markdown')


async def cmd_init_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /init command -- show initiative order (WO-V35.0)."""
    session = get_session(update.effective_chat.id)
    if not session.initiative_order:
        await update.message.reply_text(
            "No initiative order active. The DM must run `init roll` on the dashboard.")
        return
    lines = [f"<b>Initiative Order</b> (Active: {session.active_turn or 'none'})\n"]
    for name in session.initiative_order:
        marker = "\u25b6\ufe0f" if name == session.active_turn else "\u25ab\ufe0f"
        lines.append(f"{marker} {name}")
    await update.message.reply_text("\n".join(lines), parse_mode='HTML')


async def cmd_voice_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /voice command — toggle voice narration flag (WO-V50.0)."""
    session = get_session(update.effective_chat.id)
    session.voice_enabled = not session.voice_enabled
    state = "ON" if session.voice_enabled else "OFF"
    await update.message.reply_text(f"Voice narration: <b>{state}</b>", parse_mode='HTML')


async def cmd_sheet_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sheet command — show character stats (WO-V50.0)."""
    session = get_session(update.effective_chat.id)
    if not session.bridge:
        await update.message.reply_text("No active session. Start a game first.")
        return

    engine = getattr(session.bridge, 'engine', None)
    if not engine:
        await update.message.reply_text("No engine available.")
        return

    char = getattr(engine, 'character', None)
    if not char:
        await update.message.reply_text("No active character.")
        return

    lines = [f"{char.name}"]
    lines.append(f"HP: {char.current_hp}/{char.max_hp}")

    game_type = session.game_type
    if game_type == "dnd5e":
        ac = getattr(char, 'armor_class', 10)
        level = getattr(char, 'level', 1)
        cls = getattr(char, 'character_class', 'None')
        race = getattr(char, 'race', 'None')
        lines.append(f"AC: {ac} | Level: {level}")
        lines.append(f"Class: {cls} | Race: {race}")
        lines.append(f"STR:{getattr(char,'strength',10)} DEX:{getattr(char,'dexterity',10)} CON:{getattr(char,'constitution',10)}")
        lines.append(f"INT:{getattr(char,'intelligence',10)} WIS:{getattr(char,'wisdom',10)} CHA:{getattr(char,'charisma',10)}")
    elif game_type == "cosmere":
        defense = getattr(char, 'defense', 10)
        focus = getattr(char, 'focus', 0)
        order = getattr(char, 'order', 'None')
        heritage = getattr(char, 'heritage', 'None')
        lines.append(f"DEF: {defense} | FOC: {focus}")
        lines.append(f"Order: {order} | Heritage: {heritage}")
    elif game_type == "burnwillow":
        mig = getattr(char, 'might', 0)
        wit = getattr(char, 'wit', 0)
        grt = getattr(char, 'grit', 0)
        aet = getattr(char, 'aether', 0)
        lines.append(f"MIG:{mig} WIT:{wit} GRT:{grt} AET:{aet}")
    else:
        lines.append(f"System: {game_type}")

    # Party info
    party = getattr(engine, 'party', [])
    if len(party) > 1:
        lines.append("")
        lines.append("Party:")
        for m in party:
            alive = "OK" if m.is_alive() else "DEAD"
            lines.append(f"  {m.name}: {m.current_hp}/{m.max_hp} [{alive}]")

    await update.message.reply_text(f"<pre>{chr(10).join(lines)}</pre>", parse_mode='HTML')


async def cmd_atlas_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /atlas command — show world atlas G.R.A.P.E.S. (WO-V50.0)."""
    worlds_dir = _ROOT / "worlds"
    if not worlds_dir.is_dir():
        await update.message.reply_text("No worlds found.")
        return

    # Load most recent world JSON
    world_files = sorted(worlds_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    # Filter out memory files
    world_files = [f for f in world_files if "_memory" not in f.name]
    if not world_files:
        await update.message.reply_text("No worlds found.")
        return

    try:
        data = json.loads(world_files[0].read_text())
    except (json.JSONDecodeError, OSError):
        await update.message.reply_text("Failed to load world data.")
        return

    name = data.get("name", "Unknown World")
    grapes = data.get("grapes", {})

    if not grapes:
        await update.message.reply_text(f"<b>{name}</b>\nNo G.R.A.P.E.S. data available.", parse_mode='HTML')
        return

    lines = [f"<b>World Atlas: {name}</b>", ""]
    labels = {
        "geography": "Geography",
        "religion": "Religion",
        "achievements": "Achievements",
        "politics": "Politics",
        "economics": "Economics",
        "social": "Social",
    }
    for key, label in labels.items():
        val = grapes.get(key, "Unknown")
        if isinstance(val, list):
            # Rich format: list of dicts
            parts = []
            for item in val:
                if isinstance(item, dict):
                    parts.append(item.get("name", item.get("text", str(item))))
                else:
                    parts.append(str(item))
            val = ", ".join(parts)
        lines.append(f"<b>{label}:</b> {val}")

    await update.message.reply_text("\n".join(lines), parse_mode='HTML')


async def cmd_rumors_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rumors command — town crier rumors (WO-V50.0)."""
    worlds_dir = _ROOT / "worlds"
    if not worlds_dir.is_dir():
        await update.message.reply_text("No worlds found. Generate one first.")
        return

    world_files = sorted(worlds_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    world_files = [f for f in world_files if "_memory" not in f.name]
    if not world_files:
        await update.message.reply_text("No worlds found.")
        return

    try:
        data = json.loads(world_files[0].read_text())
    except (json.JSONDecodeError, OSError):
        await update.message.reply_text("Failed to load world data.")
        return

    name = data.get("name", "Unknown World")
    grapes = data.get("grapes", {})
    primer = data.get("primer", "")

    # Generate simple rumors from GRAPES and primer
    import random as _rng
    rumor_seeds = []
    if grapes.get("politics"):
        rumor_seeds.append(f"Word from the capital: {grapes['politics']}.")
    if grapes.get("economics"):
        rumor_seeds.append(f"Merchants whisper of {grapes['economics']}.")
    if grapes.get("religion"):
        rumor_seeds.append(f"The faithful speak of {grapes['religion']}.")
    if grapes.get("social"):
        rumor_seeds.append(f"Common folk discuss {grapes['social']}.")
    if grapes.get("geography"):
        rumor_seeds.append(f"Travelers describe {grapes['geography']}.")
    if primer:
        # Extract a sentence from the primer
        sentences = [s.strip() for s in primer.split(".") if len(s.strip()) > 10]
        if sentences:
            rumor_seeds.append(f"An old sage recalls: \"{_rng.choice(sentences)}.\"")

    if not rumor_seeds:
        await update.message.reply_text("The town crier has nothing to report today.")
        return

    _rng.shuffle(rumor_seeds)
    selected = rumor_seeds[:5]

    lines = [f"<b>Town Crier — {name}</b>", ""]
    for i, rumor in enumerate(selected, 1):
        lines.append(f"{i}. <i>{rumor}</i>")

    await update.message.reply_text("\n".join(lines), parse_mode='HTML')


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - purge session memory."""
    session = get_session(update.effective_chat.id)
    if session.phase != Phase.IDLE:
        session.end_game()

    # Clear the session entirely
    chat_id = update.effective_chat.id
    if chat_id in sessions:
        del sessions[chat_id]

    await update.message.reply_text("🧹 Session memory purged.", parse_mode='Markdown')


async def cmd_summon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /summon command - acknowledge presence."""
    await update.message.reply_text(
        "<b>Mimir has been summoned.</b>\n"
        "<i>I am focusing on this conversation.</i>",
        parse_mode='HTML'
    )


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command — instant health check."""
    await update.message.reply_text("<b>Pong!</b> Online", parse_mode='HTML')


async def cmd_prologue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /prologue command — launch Crown & Crew from campaign context."""
    pending = _scan_pending_prologues()

    if not pending:
        await update.message.reply_text(
            "No campaigns with a pending prologue.\n"
            "Create one via the Campaign Wizard (terminal).",
            parse_mode='HTML'
        )
        return

    manifest = pending[0]
    campaign_ctx = manifest.get('prologue_context', {})

    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()

    session.engine = CrownAndCrewEngine(campaign_context=campaign_ctx, mimir=session.mimir)
    session.phase = Phase.MORNING

    world_prompt = session.engine.get_world_prompt()
    camp_name = manifest.get('campaign_name', 'Unknown')

    header = f"""📜 <b>PROLOGUE: {camp_name}</b>

<i>Patron:</i> {session.engine.patron}
<i>Leader:</i> {session.engine.leader}
<i>Goal:</i> {session.engine.goal}
"""
    await update.message.reply_text(header, parse_mode='HTML')

    morning = format_morning(session.engine.day, world_prompt)
    await update.message.reply_text(morning, parse_mode='Markdown')


async def cmd_burnwillow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /burnwillow command — start a dungeon run."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    session.bridge = BurnwillowBridge()
    session.game_type = "burnwillow"
    session.phase = Phase.DUNGEON
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


async def cmd_dnd5e(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dnd5e command — start a D&D 5e dungeon run."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    from codex.games.dnd5e import DnD5eEngine
    session.bridge = UniversalGameBridge(DnD5eEngine)
    session.game_type = "dnd5e"
    session.phase = Phase.DND5E
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


async def cmd_cosmere(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cosmere command — start a Cosmere dungeon run."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    from codex.games.stc import CosmereEngine
    session.bridge = UniversalGameBridge(CosmereEngine)
    session.game_type = "cosmere"
    session.phase = Phase.COSMERE
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


async def cmd_bitd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bitd command — start a Blades in the Dark session."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    try:
        from codex.games.bitd import BitDEngine
    except ImportError:
        await update.message.reply_text("BitD engine not available.")
        return
    session.bridge = UniversalGameBridge(BitDEngine)
    session.game_type = "bitd"
    session.phase = Phase.BITD
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


async def cmd_sav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sav command — start a Scum and Villainy session."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    try:
        from codex.games.sav import SaVEngine
    except ImportError:
        await update.message.reply_text("SaV engine not available.")
        return
    session.bridge = UniversalGameBridge(SaVEngine)
    session.game_type = "sav"
    session.phase = Phase.SAV
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


async def cmd_bob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bob command — start a Band of Blades session."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    try:
        from codex.games.bob import BoBEngine
    except ImportError:
        await update.message.reply_text("BoB engine not available.")
        return
    session.bridge = UniversalGameBridge(BoBEngine)
    session.game_type = "bob"
    session.phase = Phase.BOB
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


async def cmd_cbrpnk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cbrpnk command — start a CBR+PNK session."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    try:
        from codex.games.cbrpnk import CBRPNKEngine
    except ImportError:
        await update.message.reply_text("CBR+PNK engine not available.")
        return
    session.bridge = UniversalGameBridge(CBRPNKEngine)
    session.game_type = "cbrpnk"
    session.phase = Phase.CBRPNK
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


async def cmd_candela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /candela command — start a Candela Obscura session."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    try:
        from codex.games.candela import CandelaEngine
    except ImportError:
        await update.message.reply_text("Candela Obscura engine not available.")
        return
    session.bridge = UniversalGameBridge(CandelaEngine)
    session.game_type = "candela"
    session.phase = Phase.CANDELA
    await update.message.reply_text(f"```\n{session.bridge.step('look')}\n```", parse_mode='Markdown')


# ── FITD Scene Navigation Commands ────────────────────────────────────

async def cmd_scene(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scene command — show current FITD scene."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Not in a FITD session.")
        return
    from codex.bots.fitd_dispatch import dispatch_fitd_command
    result = dispatch_fitd_command(
        "scene", "", getattr(session.bridge, '_engine', None),
        session.bridge, session.scene_state)
    await update.message.reply_text(
        f"```\n{(result or 'No module loaded. Use /module to load one.')[:4000]}\n```",
        parse_mode='Markdown')


async def cmd_next_scene(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /next command — advance to next FITD scene."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Not in a FITD session.")
        return
    from codex.bots.fitd_dispatch import dispatch_fitd_command
    result = dispatch_fitd_command(
        "next", "", getattr(session.bridge, '_engine', None),
        session.bridge, session.scene_state)
    await update.message.reply_text(
        f"```\n{(result or 'No module loaded.')[:4000]}\n```",
        parse_mode='Markdown')


async def cmd_scenes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scenes command — list all FITD scenes."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Not in a FITD session.")
        return
    from codex.bots.fitd_dispatch import dispatch_fitd_command
    result = dispatch_fitd_command(
        "scenes", "", getattr(session.bridge, '_engine', None),
        session.bridge, session.scene_state)
    await update.message.reply_text(
        f"```\n{(result or 'No module loaded.')[:4000]}\n```",
        parse_mode='Markdown')


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /jobs command — list accepted FITD jobs."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Not in a FITD session.")
        return
    from codex.bots.fitd_dispatch import dispatch_fitd_command
    result = dispatch_fitd_command(
        "jobs", "", getattr(session.bridge, '_engine', None),
        session.bridge, session.scene_state)
    await update.message.reply_text(
        f"```\n{(result or 'No jobs yet.')[:4000]}\n```",
        parse_mode='Markdown')


async def cmd_resist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resist command — FITD resistance roll."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Not in a FITD session.")
        return
    args = " ".join(context.args) if context.args else ""
    from codex.bots.fitd_dispatch import dispatch_fitd_command
    result = dispatch_fitd_command(
        "resist", args, getattr(session.bridge, '_engine', None),
        session.bridge, session.scene_state)
    await update.message.reply_text(
        f"```\n{(result or 'Resist failed.')[:4000]}\n```",
        parse_mode='Markdown')


async def cmd_fitd_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /fitd_roll command — FITD action roll."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Not in a FITD session.")
        return
    args = " ".join(context.args) if context.args else ""
    from codex.bots.fitd_dispatch import dispatch_fitd_command
    result = dispatch_fitd_command(
        "roll", args, getattr(session.bridge, '_engine', None),
        session.bridge, session.scene_state)
    await update.message.reply_text(
        f"```\n{(result or 'Usage: /fitd_roll <action>')[:4000]}\n```",
        parse_mode='Markdown')


async def cmd_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /module command — load a playable module into FITD session."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Not in a FITD session. Start one with /bitd, /sav, etc.")
        return
    try:
        from play_universal import _FITDSceneState
        from codex.spatial.zone_manager import ZoneManager
    except ImportError:
        await update.message.reply_text("Scene system not available.")
        return
    from pathlib import Path
    modules_dir = Path(__file__).resolve().parent.parent.parent / "vault_maps" / "modules"
    if not modules_dir.exists():
        await update.message.reply_text("No modules directory found.")
        return
    module_dirs = sorted([
        d.name for d in modules_dir.iterdir()
        if d.is_dir() and (d / "module_manifest.json").exists()
    ])
    if not module_dirs:
        await update.message.reply_text("No modules available.")
        return
    args = " ".join(context.args) if context.args else ""
    if not args:
        listing = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(module_dirs))
        await update.message.reply_text(
            f"```\nAvailable modules:\n{listing}\n\nUsage: /module <name>\n```",
            parse_mode='Markdown')
        return
    target = args.strip().lower()
    match = next((m for m in module_dirs if target in m.lower()), None)
    if not match:
        await update.message.reply_text(f"Module '{args}' not found.")
        return
    module_path = modules_dir / match
    try:
        zm = ZoneManager(module_path)
        ss = _FITDSceneState(zm, module_path)
        session.scene_state = ss
        scene = ss.current_scene()
        if scene:
            text = ss.format_scene(scene)
            await update.message.reply_text(
                f"```\nModule loaded: {match}\n\n--- Scene 1/{ss.scene_count()} ---\n{text[:3800]}\n```",
                parse_mode='Markdown')
        else:
            await update.message.reply_text(f"Module '{match}' loaded but no scenes found.")
    except Exception as e:
        await update.message.reply_text(f"Failed to load module: {e}")


def _format_wizard_prompt(prompt: dict) -> str:
    """Format a HeadlessWizard step prompt as plain text."""
    lines = [f"--- {prompt.get('label', 'Step')} ({prompt['step_index']+1}/{prompt['total_steps']}) ---"]
    if prompt.get("prompt"):
        lines.append(prompt["prompt"])
    ptype = prompt["type"]
    if ptype == "text_input":
        lines.append("Type your answer:")
    elif ptype in ("choice", "dependent_choice"):
        for i, opt in enumerate(prompt.get("options", []), 1):
            desc = f" - {opt['description']}" if opt.get("description") else ""
            lines.append(f"  {i}. {opt['label']}{desc}")
        lines.append("Type a number to choose:")
    elif ptype == "stat_roll":
        for name, val in zip(prompt.get("assign_to", []), prompt.get("rolled_values", [])):
            lines.append(f"  {name}: {val}")
        lines.append("(Auto-assigned)")
    elif ptype == "stat_pool_allocate":
        lines.append(f"Pool: {prompt.get('pool', [])}")
        lines.append(f"Assign to: {', '.join(prompt.get('assign_to', []))}")
        lines.append("Reply: stat_name=value (e.g. STR=14 DEX=12 CON=10)")
    elif ptype == "point_allocate":
        lines.append(f"Points: {prompt.get('points', 0)} (max {prompt.get('max_per_category', 2)} per)")
        for cat in prompt.get("categories", []):
            lines.append(f"  {cat}: {prompt.get('current', {}).get(cat, 0)}")
        lines.append("Reply: category=dots (e.g. Hunt=2 Study=1)")
    elif ptype == "ability_select":
        lines.append(f"Choose {prompt.get('count', 1)} from:")
        for ab in prompt.get("abilities", []):
            lines.append(f"  - {ab}")
        lines.append("Reply with comma-separated names:")
    elif ptype == "auto_derive":
        lines.append("(Auto-calculated)")
    return "\n".join(lines)


def _parse_wizard_answer(wizard: object, text: str) -> object:
    """Parse text input into the right answer type for the current wizard step."""
    from codex.forge.char_wizard_headless import HeadlessWizard
    if not isinstance(wizard, HeadlessWizard):
        return text
    prompt = wizard.current_step_prompt()
    if not prompt:
        return text
    ptype = prompt["type"]
    if ptype == "text_input":
        return text
    elif ptype in ("choice", "dependent_choice"):
        try:
            return int(text)
        except ValueError:
            return text
    elif ptype in ("stat_pool_allocate", "point_allocate"):
        # Parse key=value pairs
        result: dict = {}
        for pair in text.replace(",", " ").split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                try:
                    result[k.strip()] = int(v.strip())
                except ValueError:
                    pass
        return result
    elif ptype == "ability_select":
        return [a.strip() for a in text.split(",")]
    return text


async def _handle_wizard_input(update: Update, session: "TelegramSession", text: str) -> None:
    """Process wizard step answers from Telegram messages."""
    ws = session.wizard_state

    # System selection phase
    if isinstance(ws, dict) and "pending_system_select" in ws:
        systems = ws["pending_system_select"]
        try:
            idx = int(text) - 1
            if 0 <= idx < len(systems):
                from codex.forge.char_wizard_headless import HeadlessWizard
                wizard = HeadlessWizard(systems[idx])
                session.wizard_state = wizard
                prompt = wizard.current_step_prompt()
                if prompt:
                    await update.message.reply_text(
                        f"```\n{_format_wizard_prompt(prompt)}\n```", parse_mode='Markdown')
                return
        except (ValueError, IndexError):
            pass
        await update.message.reply_text("Invalid selection. Type a number.")
        return

    # Transition system selection
    if isinstance(ws, dict) and "pending_transition" in ws:
        targets = ws["pending_transition"]
        try:
            idx = int(text) - 1
            if 0 <= idx < len(targets):
                target_id = targets[idx]
                from codex.forge.char_wizard_headless import HeadlessWizard
                from codex.forge.char_wizard import CharacterBuilderEngine
                engine = CharacterBuilderEngine()
                schema = engine.get_system(target_id)
                if not schema:
                    await update.message.reply_text(f"No schema for {target_id}.")
                    session.wizard_state = None
                    return
                wizard = HeadlessWizard(schema)
                session.wizard_state = {"transition_wizard": wizard, "target_system": target_id, "from_system": ws["from_system"]}
                prompt = wizard.current_step_prompt()
                if prompt:
                    await update.message.reply_text(
                        f"```\nCreating character for {target_id}...\n\n{_format_wizard_prompt(prompt)}\n```",
                        parse_mode='Markdown')
                return
        except (ValueError, IndexError):
            pass
        await update.message.reply_text("Invalid selection.")
        return

    # Transition wizard step processing
    if isinstance(ws, dict) and "transition_wizard" in ws:
        wizard = ws["transition_wizard"]
        answer = _parse_wizard_answer(wizard, text)
        result = wizard.submit_answer(answer)
        if result["ok"]:
            next_prompt = wizard.current_step_prompt()
            if next_prompt is None or wizard.complete:
                await update.message.reply_text(
                    f"```\nCharacter created for {ws['target_system']}! Transition complete.\n```",
                    parse_mode='Markdown')
                session.wizard_state = None
            else:
                await update.message.reply_text(
                    f"```\n{_format_wizard_prompt(next_prompt)}\n```", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"Error: {result.get('error', 'Invalid input')}")
        return

    # Normal wizard (character creation)
    from codex.forge.char_wizard_headless import HeadlessWizard
    if not isinstance(ws, HeadlessWizard):
        session.wizard_state = None
        return
    wizard = ws
    answer = _parse_wizard_answer(wizard, text)
    result = wizard.submit_answer(answer)
    if result["ok"]:
        next_prompt = wizard.current_step_prompt()
        if next_prompt is None or wizard.complete:
            sheet = wizard.sheet
            await update.message.reply_text(
                f"```\nCharacter '{sheet.name}' created for {sheet.system_id}!\nStats: {sheet.stats}\n```",
                parse_mode='Markdown')
            session.wizard_state = None
        else:
            await update.message.reply_text(
                f"```\n{_format_wizard_prompt(next_prompt)}\n```", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"Error: {result.get('error', 'Invalid input')}")


async def cmd_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create command — schema-driven character creation."""
    try:
        from codex.forge.char_wizard_headless import HeadlessWizard  # noqa: F401
        from codex.forge.char_wizard import CharacterBuilderEngine
    except ImportError:
        await update.message.reply_text("Character creation not available.")
        return
    engine = CharacterBuilderEngine()
    systems = engine.list_systems()
    if not systems:
        await update.message.reply_text("No character creation schemas found.")
        return
    session = get_session(update.effective_chat.id)
    lines = ["--- Character Creation ---", "Choose a game system:"]
    for i, schema in enumerate(systems, 1):
        lines.append(f"  {i}. {schema.display_name} ({schema.system_id})")
    lines.append(f"\nType a number (1-{len(systems)}):")
    session.wizard_state = {"pending_system_select": systems}
    await update.message.reply_text(f"```\n" + "\n".join(lines) + "\n```", parse_mode='Markdown')


async def cmd_scribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scribe command — add public session log entry."""
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Usage: `/scribe <log entry>`", parse_mode='Markdown')
        return
    try:
        from codex.core.butler import CodexButler
        butler = CodexButler()
        result = butler.scribe(text)
        await update.message.reply_text(f"```\n{result}\n```", parse_mode='Markdown')
    except ImportError:
        await update.message.reply_text("Butler Scribe not available.")


async def cmd_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /secret command — add secret DM note."""
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Usage: `/secret <note>`", parse_mode='Markdown')
        return
    try:
        from codex.core.butler import CodexButler
        butler = CodexButler()
        result = butler.scribe(text, secret=True)
        await update.message.reply_text(f"```\n{result}\n```", parse_mode='Markdown')
    except ImportError:
        await update.message.reply_text("Butler Scribe not available.")


async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /journal command — show recent session log entries."""
    try:
        from codex.core.butler import CodexButler
        butler = CodexButler()
        entries = butler.get_recent_logs(limit=10)
        if entries:
            text = "\n".join(entries)
            await update.message.reply_text(f"```\n{text[:4000]}\n```", parse_mode='Markdown')
        else:
            await update.message.reply_text("No session log entries yet.")
    except ImportError:
        await update.message.reply_text("Butler Scribe not available.")


async def cmd_universe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /universe command — show star chart / world registry."""
    try:
        from codex.core.services.universe_manager import UniverseManager
    except ImportError:
        await update.message.reply_text("Universe Manager not available.")
        return
    um = UniverseManager()
    universes = um.list_universes()
    if not universes:
        await update.message.reply_text("No universes registered.")
        return
    lines = ["--- Star Chart ---"]
    for u in universes:
        name = getattr(u, 'name', str(u))
        modules = getattr(u, 'modules', [])
        lines.append(f"\n  {name}")
        for mod in modules:
            mod_name = getattr(mod, 'name', str(mod))
            lines.append(f"    - {mod_name}")
    await update.message.reply_text(f"```\n" + "\n".join(lines)[:4000] + "\n```", parse_mode='Markdown')


async def cmd_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tutorial command — browse tutorial modules."""
    try:
        from codex.core.services.tutorial import TutorialRegistry
        import codex.core.services.tutorial_content  # noqa: F401 — populates registry
    except ImportError:
        await update.message.reply_text("Tutorial system not available.")
        return
    args = " ".join(context.args) if context.args else ""
    modules = TutorialRegistry.list_modules()
    if not modules:
        await update.message.reply_text("No tutorial modules registered.")
        return
    if not args:
        # List categories and modules
        categories = {}
        for mod in modules:
            cat = getattr(mod, 'category', 'general')
            categories.setdefault(cat, []).append(mod)
        lines = ["--- Tutorial Modules ---"]
        for cat, mods in sorted(categories.items()):
            lines.append(f"\n  [{cat.upper()}]")
            for mod in mods:
                name = getattr(mod, 'name', str(mod))
                desc = getattr(mod, 'description', '')
                lines.append(f"    {name}" + (f" — {desc}" if desc else ""))
        lines.append("\nUsage: /tutorial <module_name>")
        await update.message.reply_text(
            f"```\n" + "\n".join(lines)[:4000] + "\n```", parse_mode='Markdown')
    else:
        # Show specific module
        target = args.lower()
        found = next((m for m in modules
                       if getattr(m, 'name', '').lower() == target
                       or target in getattr(m, 'name', '').lower()), None)
        if not found:
            await update.message.reply_text(f"Tutorial '{args}' not found.")
            return
        pages = getattr(found, 'pages', [])
        lines = [f"--- {found.name} ---"]
        if hasattr(found, 'description'):
            lines.append(found.description)
        for i, page in enumerate(pages, 1):
            title = getattr(page, 'title', f"Page {i}")
            content = getattr(page, 'content', '')
            lines.append(f"\n[{i}] {title}")
            lines.append(content)
        await update.message.reply_text(
            f"```\n" + "\n".join(lines)[:4000] + "\n```", parse_mode='Markdown')


async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command — show DM Dashboard or run sub-command."""
    session = get_session(update.effective_chat.id)
    if not session.bridge:
        await update.message.reply_text("No active game session.")
        return
    try:
        from codex.core.dm_dashboard import DMDashboard, get_vitals
        from codex.bots.dashboard_embed import format_dashboard_text
    except ImportError:
        await update.message.reply_text("Dashboard not available.")
        return
    # Lazy-init dashboard
    if session.dm_dashboard is None:
        system_tag = session.game_type or getattr(getattr(session, 'bridge', None), '_system_tag', '') or "unknown"
        session.dm_dashboard = DMDashboard(console=None, system_tag=system_tag)
    engine = getattr(session.bridge, '_engine', None)
    args = " ".join(context.args) if context.args else ""
    if args:
        result = session.dm_dashboard.dispatch_command(args, engine)
        await update.message.reply_text(
            f"```\n{result[:4000]}\n```", parse_mode='Markdown')
    else:
        try:
            vitals = get_vitals(engine, session.game_type or "burnwillow")
        except Exception:
            await update.message.reply_text("Could not read engine vitals.")
            return
        text = format_dashboard_text(vitals, session.dm_dashboard, engine)
        await update.message.reply_text(
            f"```\n{text[:4000]}\n```", parse_mode='Markdown')


async def cmd_transition(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /transition command — stack into another FITD system."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
        await update.message.reply_text("Engine stacking only works in FITD sessions.")
        return
    try:
        from codex.core.engine_stack import STACKABLE_FAMILIES
    except ImportError:
        await update.message.reply_text("Engine stacking not available.")
        return
    current = session.game_type
    fitd_systems = STACKABLE_FAMILIES.get("fitd", set())
    targets = sorted(s for s in fitd_systems if s != current)
    if not targets:
        await update.message.reply_text("No compatible systems.")
        return
    lines = ["--- Engine Transition ---", f"Current: {current}", "", "Stack into:"]
    for i, sys_id in enumerate(targets, 1):
        lines.append(f"  {i}. {sys_id}")
    lines.append(f"\nType a number (1-{len(targets)}):")
    session.wizard_state = {"pending_transition": targets, "from_system": current}
    await update.message.reply_text(f"```\n" + "\n".join(lines) + "\n```", parse_mode='Markdown')


async def cmd_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dm command — DM Tools suite."""
    try:
        from codex.core.dm_tools import (
            roll_dice, generate_npc, generate_trap,
            calculate_loot, generate_encounter, scan_vault,
        )
    except ImportError:
        await update.message.reply_text("DM Tools module not available.")
        return

    args = " ".join(context.args) if context.args else ""
    parts = args.strip().split(None, 1)
    sub = parts[0].lower() if parts else "help"
    arg = parts[1].strip() if len(parts) > 1 else ""

    if sub in ("dice", "roll"):
        if not arg:
            await update.message.reply_text("Usage: `/dm dice 2d6+3`", parse_mode='Markdown')
            return
        total, msg = roll_dice(arg)
        await update.message.reply_text(f"*Dice Roll*\n`{msg}`", parse_mode='Markdown')

    elif sub == "npc":
        result = generate_npc(arg or "")
        await update.message.reply_text(f"*NPC Generator*\n```\n{result[:4000]}\n```", parse_mode='Markdown')

    elif sub == "loot":
        difficulty = arg or "medium"
        result = calculate_loot(difficulty)
        await update.message.reply_text(f"*Loot Generator*\n```\n{result[:4000]}\n```", parse_mode='Markdown')

    elif sub == "trap":
        difficulty = arg or "medium"
        result = generate_trap(difficulty)
        await update.message.reply_text(f"*Trap Generator*\n```\n{result[:4000]}\n```", parse_mode='Markdown')

    elif sub in ("encounter", "enc"):
        enc_parts = arg.split()
        system = enc_parts[0].upper() if enc_parts else "BURNWILLOW"
        tier = 1
        if len(enc_parts) > 1:
            try:
                tier = max(1, min(4, int(enc_parts[1])))
            except ValueError:
                pass
        result = generate_encounter(system, tier)
        await update.message.reply_text(f"*Encounter Generator*\n```\n{result[:4000]}\n```", parse_mode='Markdown')

    elif sub == "scan":
        result = scan_vault()
        await update.message.reply_text(f"*Vault Scanner*\n```\n{result[:4000]}\n```", parse_mode='Markdown')

    elif sub in ("generate", "module"):
        try:
            from scripts.generate_module import list_templates, generate_module
        except ImportError:
            await update.message.reply_text("Module generator not available.")
            return
        gen_parts = arg.split()
        if len(gen_parts) < 2:
            templates = list_templates()
            tpl_list = ", ".join(templates) if templates else "none found"
            await update.message.reply_text(
                f"Usage: `/dm generate <template> <system> [tier]`\nTemplates: {tpl_list}",
                parse_mode='Markdown')
            return
        template_id, system_id = gen_parts[0], gen_parts[1]
        tier = 1
        if len(gen_parts) > 2:
            try:
                tier = max(1, min(4, int(gen_parts[2])))
            except ValueError:
                pass
        import asyncio
        loop = asyncio.get_event_loop()
        output_dir = await loop.run_in_executor(
            None, lambda: generate_module(template_id, system_id, tier=tier))
        await update.message.reply_text(f"```\nModule generated: {output_dir}\n```", parse_mode='Markdown')

    elif sub == "enrich":
        try:
            from scripts.enrich_module import enrich_module
        except ImportError:
            await update.message.reply_text("Module enrichment not available.")
            return
        if not arg:
            await update.message.reply_text("Usage: `/dm enrich <module_directory>`", parse_mode='Markdown')
            return
        result = await enrich_module(arg)
        await update.message.reply_text(f"```\n{str(result)[:4000]}\n```", parse_mode='Markdown')

    elif sub == "genesis":
        try:
            from codex.world.genesis import GenesisEngine
        except ImportError:
            await update.message.reply_text("World Genesis module not available.")
            return
        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()
        try:
            ge = GenesisEngine()
            if not ge.data:
                await update.message.reply_text("Genesis data not found. Cannot generate world.")
                return
            world = await loop.run_in_executor(None, ge.roll_unified_world)
        except Exception as _ge_err:
            await update.message.reply_text(f"World generation failed: {_ge_err}")
            return
        grapes = world.get("grapes", {})
        faction = world.get("faction", {})
        lines = [
            f"*{world.get('name', 'Unknown World')}*",
            f"Genre: {world.get('genre', '?')}  |  Tone: {world.get('tone', '?')}",
            "",
            "*G.R.A.P.E.S.*",
        ]
        for key in ("geography", "religion", "achievements", "politics", "economics", "social"):
            val = grapes.get(key, "?")
            if isinstance(val, list):
                val = ", ".join(str(v.get("name", v) if isinstance(v, dict) else v) for v in val[:2])
            lines.append(f"  {key.title()}: {val}")
        lines += [
            "",
            f"*{faction.get('crown_title', 'The Crown')}* — {faction.get('crown_desc', '')}",
            f"*{faction.get('crew_title', 'The Crew')}* — {faction.get('crew_desc', '')}",
            "",
            "*Primer:*",
            world.get("primer", "")[:800],
        ]
        await update.message.reply_text("\n".join(lines)[:4000], parse_mode='Markdown')

    else:
        await update.message.reply_text(
            "*DM Tools*\n"
            "`/dm dice 2d6+3` — Roll dice\n"
            "`/dm npc [archetype]` — Generate NPC\n"
            "`/dm loot [easy/medium/hard]` — Generate loot\n"
            "`/dm trap [easy/medium/hard]` — Generate trap\n"
            "`/dm encounter [system] [tier]` — Generate encounter\n"
            "`/dm scan` — Scan vault PDFs for tables\n"
            "`/dm generate <tpl> <sys> [tier]` — Generate module\n"
            "`/dm enrich <dir>` — Enrich module with AI\n"
            "`/dm genesis` — Generate a procedural world",
            parse_mode='Markdown',
        )


async def cmd_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /roll command — quick dice roll."""
    try:
        from codex.core.dm_tools import roll_dice
    except ImportError:
        await update.message.reply_text("Dice module not available.")
        return
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text("Usage: `/roll 2d6+3`", parse_mode='Markdown')
        return
    total, msg = roll_dice(args)
    await update.message.reply_text(f"*Dice Roll*\n`{msg}`", parse_mode='Markdown')


async def cmd_chronology(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chronology command — show recent world history events."""
    worlds_dir = Path(__file__).resolve().parent.parent.parent / "worlds"
    if not worlds_dir.exists() or not list(worlds_dir.glob("*.json")):
        await update.message.reply_text("No saved worlds found. Create one via the Genesis Wizard.")
        return
    world_files = sorted(worlds_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    try:
        data = json.loads(world_files[0].read_text())
    except (json.JSONDecodeError, IndexError):
        await update.message.reply_text("Failed to read world data.")
        return

    chronology = data.get("chronology", [])
    if not chronology:
        await update.message.reply_text("No historical events recorded yet.")
        return

    world_name = data.get("name", "Unknown World")
    auth_labels = {1: "Eyewitness", 2: "Chronicle", 3: "Legend"}
    lines = [f"<b>World Chronology — {world_name}</b>\n"]
    for entry in chronology[-10:]:
        ts = str(entry.get("timestamp", ""))[:16].replace("T", " ")
        etype = str(entry.get("event_type", "?")).upper()
        summary = entry.get("summary", "?")
        auth = auth_labels.get(entry.get("authority_level", 2), "?")
        source = entry.get("source", "")
        lines.append(f"<b>[{etype}]</b> {ts}\n{summary}\n<i>{auth} | {source}</i>\n")
    await update.message.reply_text("\n".join(lines), parse_mode='HTML')


async def cmd_crown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /crown command — start fresh Crown & Crew campaign (WO-V23.0)."""
    session = get_session(update.effective_chat.id)
    if session.phase != Phase.IDLE:
        session.end_game()
    response = session.start_game()
    await update.message.reply_text(response, parse_mode='Markdown')


async def cmd_ashburn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ashburn command — start Ashburn High campaign (WO-V24.1)."""
    session = get_session(update.effective_chat.id)
    if session.phase != Phase.IDLE:
        session.end_game()
    try:
        from codex.games.crown.ashburn import LEADERS
        session.phase = Phase.ASHBURN_HEIR
        julian = LEADERS["Julian"]
        rowan = LEADERS["Rowan"]
        await update.message.reply_text(
            "*🥀 ASHBURN HIGH — CHOOSE YOUR HEIR*\n\n"
            f"*\\[1\\] JULIAN* — _{julian['title']}_\n"
            f"  Ability: {julian['ability']}\n"
            f"  Risk: {julian['risk']}\n\n"
            f"*\\[2\\] ROWAN* — _{rowan['title']}_\n"
            f"  Ability: {rowan['ability']}\n"
            f"  Risk: {rowan['risk']}\n\n"
            "Type `1` for Julian or `2` for Rowan.",
            parse_mode='Markdown'
        )
    except ImportError:
        await update.message.reply_text("Ashburn High module not available.")


async def cmd_quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quest command — browse quest archetypes (WO-V23.0)."""
    session = get_session(update.effective_chat.id)
    if session.phase not in (Phase.IDLE, Phase.MENU):
        session.end_game()
    try:
        from codex.games.crown.quests import list_quests
        quests = list_quests()
        if not quests:
            await update.message.reply_text("No quest archetypes available.")
            return
        session.phase = Phase.QUEST_SELECT
        lines = ["<b>⚔️ QUEST ARCHETYPES</b>\n"]
        for i, q in enumerate(quests, 1):
            lines.append(f"<b>[{i}]</b> {q.name} ({q.arc_length} days)")
            lines.append(f"     <i>{q.description[:80]}...</i>\n")
        lines.append("Type a number to select.")
        await update.message.reply_text("\n".join(lines), parse_mode='HTML')
    except ImportError:
        await update.message.reply_text("Quest archetypes module not available.")


async def cmd_genesis_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /genesis command — roll a procedural world using the GenesisEngine."""
    try:
        from codex.world.genesis import GenesisEngine
    except ImportError:
        await update.message.reply_text("World Genesis module not available.")
        return

    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()
    try:
        ge = GenesisEngine()
        if not ge.data:
            await update.message.reply_text("Genesis data not found. Cannot generate world.")
            return
        world = await loop.run_in_executor(None, ge.roll_unified_world)
    except Exception as err:
        await update.message.reply_text(f"World generation failed: {err}")
        return

    grapes = world.get("grapes", {})
    faction = world.get("faction", {})
    lines = [
        f"*{world.get('name', 'Unknown World')}*",
        f"Genre: {world.get('genre', '?')}  |  Tone: {world.get('tone', '?')}",
        "",
        "*G.R.A.P.E.S.*",
    ]
    for key in ("geography", "religion", "achievements", "politics", "economics", "social"):
        val = grapes.get(key, "?")
        if isinstance(val, list):
            val = ", ".join(str(v.get("name", v) if isinstance(v, dict) else v) for v in val[:2])
        lines.append(f"  {key.title()}: {val}")
    lines += [
        "",
        f"*{faction.get('crown_title', 'The Crown')}* — {faction.get('crown_desc', '')}",
        f"*{faction.get('crew_title', 'The Crew')}* — {faction.get('crew_desc', '')}",
        "",
        "*Primer:*",
        world.get("primer", "")[:800],
    ]
    await update.message.reply_text("\n".join(lines)[:4000], parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages for game input."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower().strip()
    session = get_session(update.effective_chat.id)

    # Character creation / transition wizard intercept
    if session.wizard_state is not None:
        await _handle_wizard_input(update, session, text)
        return

    # Dungeon session (Burnwillow / DnD5e / Cosmere free-text input)
    if session.phase in (Phase.DUNGEON, Phase.DND5E, Phase.COSMERE, Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA) and session.bridge:
        # FITD command intercept — scene nav, roll, resist, etc.
        if session.phase in (Phase.BITD, Phase.SAV, Phase.BOB, Phase.CBRPNK, Phase.CANDELA):
            from codex.bots.fitd_dispatch import dispatch_fitd_command
            _parts = text.split(None, 1)
            _verb = _parts[0] if _parts else ""
            _args = _parts[1] if len(_parts) > 1 else ""
            fitd_result = dispatch_fitd_command(
                verb=_verb, args=_args,
                engine=getattr(session.bridge, '_engine', None),
                bridge=session.bridge,
                scene_state=session.scene_state,
            )
            if fitd_result is not None:
                await update.message.reply_text(
                    f"```\n{fitd_result[:4000]}\n```", parse_mode='Markdown')
                return

        result = session.bridge.step(text)
        await update.message.reply_text(f"```\n{result}\n```", parse_mode='Markdown')
        if session.bridge.dead:
            session.end_game()
        return

    # Menu selection (WO 109 — data-driven via CodexMenu)
    if session.phase == Phase.MENU:
        action = _MENU.resolve_selection("telegram", text)
        if action:
            if action == "play_prologue":
                pending = _scan_pending_prologues()
                if not pending:
                    await update.message.reply_text(
                        "No campaigns with a pending prologue.\n"
                        "Create one via the Campaign Wizard (terminal)."
                    )
                else:
                    manifest = pending[0]
                    ctx_data = manifest.get('prologue_context', {})
                    session.engine = CrownAndCrewEngine(campaign_context=ctx_data, mimir=session.mimir)
                    session.phase = Phase.MORNING
                    camp_name = manifest.get('campaign_name', 'Unknown')
                    header = f"""\U0001f4dc <b>PROLOGUE: {camp_name}</b>

<i>Patron:</i> {session.engine.patron}
<i>Leader:</i> {session.engine.leader}
<i>Goal:</i> {session.engine.goal}
"""
                    await update.message.reply_text(header, parse_mode='HTML')
                    world_prompt = session.engine.get_world_prompt()
                    morning = format_morning(session.engine.day, world_prompt)
                    await update.message.reply_text(morning, parse_mode='Markdown')
            elif action == "play_burnwillow":
                session.bridge = BurnwillowBridge()
                session.game_type = "burnwillow"
                session.phase = Phase.DUNGEON
                await update.message.reply_text(
                    f"```\n{session.bridge.step('look')}\n```",
                    parse_mode='Markdown'
                )
            elif action == "play_dnd5e":
                from codex.games.dnd5e import DnD5eEngine
                session.bridge = UniversalGameBridge(DnD5eEngine)
                session.game_type = "dnd5e"
                session.phase = Phase.DND5E
                await update.message.reply_text(
                    f"```\n{session.bridge.step('look')}\n```",
                    parse_mode='Markdown'
                )
            elif action == "play_cosmere":
                from codex.games.stc import CosmereEngine
                session.bridge = UniversalGameBridge(CosmereEngine)
                session.game_type = "cosmere"
                session.phase = Phase.COSMERE
                await update.message.reply_text(
                    f"```\n{session.bridge.step('look')}\n```",
                    parse_mode='Markdown'
                )
            elif action == "launch_omni_forge":
                if not OMNI_FORGE_AVAILABLE:
                    await update.message.reply_text(
                        "<b>The Omni-Forge</b> — Module not available.",
                        parse_mode='HTML'
                    )
                else:
                    session.phase = Phase.OMNI
                    await update.message.reply_text(
                        "<b>🎲 THE OMNI-FORGE</b>\n\n"
                        "Type one of:\n"
                        "  <code>loot</code> — Quick Loot (Treasure Hoard)\n"
                        "  <code>lifepath</code> — Random Life Path\n"
                        "  <code>roll &lt;table&gt;</code> — Roll on a table\n"
                        "  <code>tables</code> — List available tables\n"
                        "  <code>back</code> — Return to menu",
                        parse_mode='HTML'
                    )
            elif action == "play_crown":
                # Fresh Crown & Crew campaign (WO-V23.0)
                if session.phase != Phase.IDLE:
                    session.end_game()
                response = session.start_game()
                await update.message.reply_text(response, parse_mode='Markdown')
            elif action == "play_quest":
                # Quest archetype selection (WO-V23.0)
                try:
                    from codex.games.crown.quests import list_quests
                    quests = list_quests()
                    if not quests:
                        await update.message.reply_text("No quest archetypes available.")
                    else:
                        session.phase = Phase.QUEST_SELECT
                        lines = ["<b>⚔️ QUEST ARCHETYPES</b>\n"]
                        for i, q in enumerate(quests, 1):
                            lines.append(f"<b>[{i}]</b> {q.name} ({q.arc_length} days)")
                            lines.append(f"     <i>{q.description[:80]}...</i>\n")
                        lines.append("Type a number to select.")
                        await update.message.reply_text("\n".join(lines), parse_mode='HTML')
                except ImportError:
                    await update.message.reply_text("Quest archetypes module not available.")
            elif action == "play_ashburn":
                # Ashburn High — heir selection (WO-V24.1)
                try:
                    from codex.games.crown.ashburn import LEADERS
                    if session.phase != Phase.IDLE:
                        session.end_game()
                    session.phase = Phase.ASHBURN_HEIR
                    julian = LEADERS["Julian"]
                    rowan = LEADERS["Rowan"]
                    await update.message.reply_text(
                        "*🥀 ASHBURN HIGH — CHOOSE YOUR HEIR*\n\n"
                        f"*\\[1\\] JULIAN* — _{julian['title']}_\n"
                        f"  Ability: {julian['ability']}\n"
                        f"  Risk: {julian['risk']}\n\n"
                        f"*\\[2\\] ROWAN* — _{rowan['title']}_\n"
                        f"  Ability: {rowan['ability']}\n"
                        f"  Risk: {rowan['risk']}\n\n"
                        "Type `1` for Julian or `2` for Rowan.",
                        parse_mode='Markdown'
                    )
                except ImportError:
                    await update.message.reply_text("Ashburn High module not available.")
            elif action == "end_session":
                response = session.end_game()
                await update.message.reply_text(response, parse_mode='Markdown')
            return

    # WO-V25.0: Omni-Forge handler
    if session.phase == Phase.OMNI:
        if OMNI_FORGE_AVAILABLE:
            forge = OmniForge()
            if text in ("back", "exit", "quit"):
                session.phase = Phase.MENU
                await update.message.reply_text("Returning to menu. Type /menu to see options.")
            elif text == "loot":
                result = await forge.quick_loot()
                await update.message.reply_text(f"<b>🎲 LOOT</b>\n{result}", parse_mode='HTML')
            elif text.startswith("lifepath"):
                result = await forge.generate_lifepath()
                await update.message.reply_text(f"<b>📜 LIFE PATH</b>\n{result[:3900]}", parse_mode='HTML')
            elif text == "tables":
                tables = forge.list_tables()
                await update.message.reply_text(f"<b>Available Tables:</b> {', '.join(tables)}", parse_mode='HTML')
            elif text.startswith("roll"):
                table_name = text[len("roll"):].strip().strip("<>") or "general"
                result = await forge.custom_query(table_name)
                await update.message.reply_text(f"<b>🎲 TABLE ROLL</b>\n{result}", parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "Omni-Forge commands: <code>loot</code>, <code>lifepath</code>, "
                    "<code>roll &lt;table&gt;</code>, <code>tables</code>, <code>back</code>",
                    parse_mode='HTML'
                )
        else:
            if text in ("back", "exit", "quit"):
                session.phase = Phase.MENU
                await update.message.reply_text("Returning to menu.")
            else:
                await update.message.reply_text("Omni-Forge not available. Type <code>back</code> to return.", parse_mode='HTML')
        return

    # Check for allegiance keywords
    if session.phase == Phase.CAMPFIRE:
        if text in ("crown", "crew", "👑", "🏴"):
            side = "crown" if text in ("crown", "👑") else "crew"
            response = session.handle_allegiance(side)
            if response:
                await update.message.reply_text(response, parse_mode='Markdown')
                return

    # Check for vote
    if session.phase == Phase.COUNCIL:
        if text in ("1", "2"):
            response = session.handle_vote(text)
            if response:
                await update.message.reply_text(response, parse_mode='Markdown')
                return

    # WO-V23.0: Rest choice
    if session.phase == Phase.REST:
        if text in ("long", "short", "skip"):
            response = session.handle_rest(text)
            if response:
                await update.message.reply_text(response, parse_mode='Markdown')
                return

    # WO-V24.1: Ashburn heir selection
    if session.phase == Phase.ASHBURN_HEIR:
        if text in ("1", "2"):
            try:
                from codex.games.crown.ashburn import AshburnHeirEngine
                heir_name = "Julian" if text == "1" else "Rowan"
                session.engine = AshburnHeirEngine(heir_name=heir_name, mimir=session.mimir)
                session.phase = Phase.MORNING
                world_prompt = session.engine.get_world_prompt()
                response = (
                    f"*🥀 {heir_name.upper()} — {session.engine.heir_leader['title']}*\n\n"
                    + format_morning(session.engine.day, world_prompt)
                )
                await update.message.reply_text(response, parse_mode='Markdown')
            except ImportError:
                await update.message.reply_text("Ashburn High module not available.")
        else:
            await update.message.reply_text("Choose *1* for Julian or *2* for Rowan.", parse_mode='Markdown')
        return

    # WO-V24.1: Ashburn legacy choice (Obey or Lie)
    if session.phase == Phase.ASHBURN_LEGACY:
        if text in ("1", "2"):
            result = await session.engine.resolve_legacy_choice(int(text))
            betrayal = session.engine.check_betrayal()
            if betrayal and betrayal.get("game_over"):
                await update.message.reply_text(
                    f"_{result['consequence']}_\n\n"
                    f"_{result['narration']}_\n\n"
                    "*THE SOLARIUM OPENS*\n"
                    "The glass shatters inward. You were never the heir — "
                    "you were the inheritance.\n\n"
                    "*ASHBURN CLAIMS ANOTHER.*\n\n"
                    f"_Corruption: {session.engine.legacy_corruption}/5_",
                    parse_mode='Markdown'
                )
                session.end_game()
            else:
                # Continue to council
                session.phase = Phase.COUNCIL
                session._generate_dilemma()
                response = (
                    f"_{result['consequence']}_\n\n"
                    f"_{result['narration']}_\n\n"
                    + format_council(session.engine.day, session.current_dilemma)
                )
                await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("Choose *1* (Obey) or *2* (Lie).", parse_mode='Markdown')
        return

    # WO-V23.0: Quest selection
    if session.phase == Phase.QUEST_SELECT:
        try:
            from codex.games.crown.quests import list_quests
            quests = list_quests()
            q_idx = int(text) - 1
            if 0 <= q_idx < len(quests):
                quest = quests[q_idx]
                ws = quest.to_world_state()
                session.engine = CrownAndCrewEngine(world_state=ws, mimir=session.mimir)
                session.phase = Phase.MORNING
                world_prompt = session.engine.get_world_prompt()
                response = format_morning(session.engine.day, world_prompt)
                await update.message.reply_text(response, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"Select 1-{len(quests)}.")
        except (ValueError, ImportError):
            await update.message.reply_text("Enter a quest number.")
        return


# =============================================================================
# BOT RUNNER
# =============================================================================

# =============================================================================
# OMNI-CHANNEL INLINE KEYBOARDS (Batch 005)
# =============================================================================

def build_movement_keyboard(exits: list[str]) -> InlineKeyboardMarkup:
    """Build an InlineKeyboardMarkup with N/S/E/W buttons from available exits."""
    _labels = {"north": "N", "south": "S", "east": "E", "west": "W"}
    row = []
    for direction in ("north", "south", "east", "west"):
        text = _labels[direction]
        if direction in exits:
            row.append(InlineKeyboardButton(text, callback_data=f"nav:{direction}"))
        else:
            row.append(InlineKeyboardButton(f"({text})", callback_data="noop"))
    return InlineKeyboardMarkup([row])


def build_action_keyboard() -> InlineKeyboardMarkup:
    """Build a persistent action menu for look/search/loot/inventory."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Look", callback_data="act:look"),
            InlineKeyboardButton("Search", callback_data="act:search"),
        ],
        [
            InlineKeyboardButton("Loot", callback_data="act:loot"),
            InlineKeyboardButton("Inventory", callback_data="act:inventory"),
        ],
    ])


async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process inline keyboard button presses for dungeon navigation/actions."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "noop":
        return

    chat_id = query.message.chat_id
    session = sessions.get(chat_id)
    if not session or not session.bridge:
        await query.edit_message_text("No active dungeon session.")
        return

    if data.startswith("nav:"):
        cmd = data.split(":", 1)[1]
    elif data.startswith("act:"):
        cmd = data.split(":", 1)[1]
    else:
        return

    result = session.bridge.step(cmd)
    text = f"```\n{result}\n```"

    if session.bridge.dead:
        session.end_game()
        await query.message.reply_text(text, parse_mode="Markdown")
    else:
        await query.message.reply_text(text, parse_mode="Markdown",
                                       reply_markup=build_action_keyboard())


async def run_telegram_bot(core=None):
    """
    Build and run the Telegram bot.
    Designed to be called as an asyncio task from codex_agent_main.py.
    """
    # WO 088 — expose architect as mimir for narrative generation
    global _mimir_ref
    _mimir_ref = getattr(core, 'architect', None) if core else None

    token = os.getenv("TELEGRAM_TOKEN")

    if not token:
        logger.warning("TELEGRAM_TOKEN not found in environment. Telegram bot disabled.")
        return

    logger.info("Starting Telegram bot...")

    # Build application
    app = Application.builder().token(token).build()

    # Register handlers - Full command roster
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("play", cmd_play))
    app.add_handler(CommandHandler("travel", cmd_travel))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("end", cmd_end))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("summon", cmd_summon))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("prologue", cmd_prologue))
    app.add_handler(CommandHandler("burnwillow", cmd_burnwillow))
    app.add_handler(CommandHandler("dnd5e", cmd_dnd5e))
    app.add_handler(CommandHandler("cosmere", cmd_cosmere))
    app.add_handler(CommandHandler("bitd", cmd_bitd))
    app.add_handler(CommandHandler("sav", cmd_sav))
    app.add_handler(CommandHandler("bob", cmd_bob))
    app.add_handler(CommandHandler("cbrpnk", cmd_cbrpnk))
    app.add_handler(CommandHandler("candela", cmd_candela))
    app.add_handler(CommandHandler("scene", cmd_scene))
    app.add_handler(CommandHandler("next", cmd_next_scene))
    app.add_handler(CommandHandler("scenes", cmd_scenes))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("resist", cmd_resist))
    app.add_handler(CommandHandler("fitd_roll", cmd_fitd_roll))
    app.add_handler(CommandHandler("module", cmd_module))
    app.add_handler(CommandHandler("crown", cmd_crown))
    app.add_handler(CommandHandler("ashburn", cmd_ashburn))
    app.add_handler(CommandHandler("quest", cmd_quest))
    app.add_handler(CommandHandler("create", cmd_create))
    app.add_handler(CommandHandler("transition", cmd_transition))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(CommandHandler("scribe", cmd_scribe))
    app.add_handler(CommandHandler("secret", cmd_secret))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("universe", cmd_universe))
    app.add_handler(CommandHandler("starchart", cmd_universe))
    app.add_handler(CommandHandler("tutorial", cmd_tutorial))
    app.add_handler(CommandHandler("dm", cmd_dm))
    app.add_handler(CommandHandler("roll", cmd_roll))
    app.add_handler(CommandHandler("chronology", cmd_chronology))
    app.add_handler(CommandHandler("genesis", cmd_genesis_tg))
    app.add_handler(CommandHandler("world", cmd_genesis_tg))
    app.add_handler(CommandHandler("rest", cmd_rest_tg))
    app.add_handler(CommandHandler("init", cmd_init_tg))
    app.add_handler(CommandHandler("recap", cmd_recap_tg))
    app.add_handler(CommandHandler("voice", cmd_voice_tg))
    app.add_handler(CommandHandler("sheet", cmd_sheet_tg))
    app.add_handler(CommandHandler("atlas", cmd_atlas_tg))
    app.add_handler(CommandHandler("rumors", cmd_rumors_tg))
    app.add_handler(CallbackQueryHandler(handle_button_press))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run polling (non-blocking for integration with main event loop)
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot is running.")

        # Batch 005: Subscribe to MAP_UPDATE for cross-interface sync
        try:
            broadcaster = GlobalBroadcastManager()

            async def _on_map_update(payload):
                system_id = payload.get("system_id", "unknown")
                room_id = payload.get("room_id", "?")
                for chat_id, sess in sessions.items():
                    if sess.phase not in (Phase.IDLE, Phase.MENU) and sess.bridge:
                        frame = getattr(sess.bridge, 'last_frame', None)
                        if frame:
                            logger.debug(
                                "[MAP_UPDATE] %s room %s -> chat %s",
                                system_id, room_id, chat_id,
                            )

            def _map_sync_handler(payload):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_on_map_update(payload))
                except RuntimeError:
                    pass

            broadcaster.subscribe("MAP_UPDATE", _map_sync_handler)
            logger.info("[Batch 005] Telegram subscribed to MAP_UPDATE broadcasts")

            # WO-V35.0: Subscribe to INITIATIVE_ADVANCE
            async def _on_initiative_advance(payload):
                name = payload.get("name", "?")
                order = payload.get("order", [])
                for chat_id, sess in sessions.items():
                    if sess.phase not in (Phase.IDLE, Phase.MENU):
                        sess.initiative_order = order
                        sess.active_turn = name

            def _init_sync_handler(payload):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_on_initiative_advance(payload))
                except RuntimeError:
                    pass

            broadcaster.subscribe("INITIATIVE_ADVANCE", _init_sync_handler)
            logger.info("[WO-V35.0] Telegram subscribed to INITIATIVE_ADVANCE")

            # WO-V35.0: Subscribe to CONDITION_CHANGE
            async def _on_condition_change(payload):
                entity = payload.get("entity", "?")
                action = payload.get("action", "?")
                ctype = payload.get("condition_type", "?")
                for chat_id, sess in sessions.items():
                    if sess.phase not in (Phase.IDLE, Phase.MENU):
                        if sess.conditions is None:
                            from codex.core.mechanics.conditions import ConditionTracker
                            sess.conditions = ConditionTracker()
                        if action == "apply":
                            from codex.core.mechanics.conditions import (
                                ConditionType, Condition, CONDITION_DEFAULTS)
                            try:
                                ct = ConditionType(ctype)
                                cond = Condition(
                                    condition_type=ct,
                                    duration=3,
                                    modifier=CONDITION_DEFAULTS.get(ct, 0),
                                )
                                sess.conditions.apply(entity, cond)
                            except (ValueError, KeyError):
                                pass
                        elif action == "remove":
                            from codex.core.mechanics.conditions import ConditionType
                            try:
                                ct = ConditionType(ctype)
                                sess.conditions.remove(entity, ct)
                            except (ValueError, KeyError):
                                pass

            def _cond_sync_handler(payload):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_on_condition_change(payload))
                except RuntimeError:
                    pass

            broadcaster.subscribe("CONDITION_CHANGE", _cond_sync_handler)
            logger.info("[WO-V35.0] Telegram subscribed to CONDITION_CHANGE")

            # WO-V40.0: Subscribe to zone transition events
            async def _on_zone_transition(payload):
                module = payload.get("module", "")
                chapter = payload.get("chapter", "")
                zone = payload.get("zone", "")
                progress = payload.get("progress", "")
                msg = f"Zone Transition: {module}\n{chapter} — {zone}\n{progress}"
                for chat_id, sess in sessions.items():
                    if sess.phase != Phase.IDLE:
                        try:
                            await app.bot.send_message(chat_id=chat_id, text=msg)
                        except Exception:
                            pass

            def _zone_sync_handler(payload):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_on_zone_transition(payload))
                except RuntimeError:
                    pass

            broadcaster.subscribe("ZONE_TRANSITION", _zone_sync_handler)
            broadcaster.subscribe("ZONE_COMPLETE", _zone_sync_handler)
            logger.info("[WO-V40.0] Telegram subscribed to ZONE_TRANSITION/COMPLETE")
        except Exception as e:
            logger.debug(f"[Batch 005] MAP_UPDATE subscription skipped: {e}")

        # Keep running until cancelled
        while True:
            await asyncio.sleep(3600)

    except asyncio.CancelledError:
        logger.info("Telegram bot shutting down...")
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
    finally:
        # Only stop updater if it's running
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()


def main():
    """Standalone entry point for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    print("🤖 Starting C.O.D.E.X. Telegram Bot (Standalone Mode)...")

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("❌ TELEGRAM_TOKEN not found in .env")
        return

    app = Application.builder().token(token).build()

    # Register handlers - Full command roster
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("play", cmd_play))
    app.add_handler(CommandHandler("travel", cmd_travel))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("end", cmd_end))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("summon", cmd_summon))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("prologue", cmd_prologue))
    app.add_handler(CommandHandler("burnwillow", cmd_burnwillow))
    app.add_handler(CommandHandler("dnd5e", cmd_dnd5e))
    app.add_handler(CommandHandler("cosmere", cmd_cosmere))
    app.add_handler(CommandHandler("bitd", cmd_bitd))
    app.add_handler(CommandHandler("sav", cmd_sav))
    app.add_handler(CommandHandler("bob", cmd_bob))
    app.add_handler(CommandHandler("cbrpnk", cmd_cbrpnk))
    app.add_handler(CommandHandler("candela", cmd_candela))
    app.add_handler(CommandHandler("scene", cmd_scene))
    app.add_handler(CommandHandler("next", cmd_next_scene))
    app.add_handler(CommandHandler("scenes", cmd_scenes))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("resist", cmd_resist))
    app.add_handler(CommandHandler("fitd_roll", cmd_fitd_roll))
    app.add_handler(CommandHandler("module", cmd_module))
    app.add_handler(CommandHandler("chronology", cmd_chronology))
    app.add_handler(CommandHandler("crown", cmd_crown))
    app.add_handler(CommandHandler("ashburn", cmd_ashburn))
    app.add_handler(CommandHandler("quest", cmd_quest))
    app.add_handler(CommandHandler("create", cmd_create))
    app.add_handler(CommandHandler("transition", cmd_transition))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(CommandHandler("scribe", cmd_scribe))
    app.add_handler(CommandHandler("secret", cmd_secret))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("universe", cmd_universe))
    app.add_handler(CommandHandler("starchart", cmd_universe))
    app.add_handler(CommandHandler("tutorial", cmd_tutorial))
    app.add_handler(CommandHandler("dm", cmd_dm))
    app.add_handler(CommandHandler("roll", cmd_roll))
    app.add_handler(CommandHandler("voice", cmd_voice_tg))
    app.add_handler(CommandHandler("sheet", cmd_sheet_tg))
    app.add_handler(CommandHandler("atlas", cmd_atlas_tg))
    app.add_handler(CommandHandler("rumors", cmd_rumors_tg))
    app.add_handler(CallbackQueryHandler(handle_button_press))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # WO-V40.0: Subscribe to zone transition broadcasts
    try:
        from codex.core.services.broadcast import GlobalBroadcastManager

        def _on_zone_event(payload):
            module = payload.get("module", "")
            chapter = payload.get("chapter", "")
            zone = payload.get("zone", "")
            progress = payload.get("progress", "")
            msg = f"Zone Transition: {module}\n{chapter} — {zone}\n{progress}"
            for chat_id, sess in sessions.items():
                if sess.phase != Phase.IDLE:
                    try:
                        import asyncio
                        loop = asyncio.get_running_loop()
                        loop.create_task(
                            app.bot.send_message(chat_id=chat_id, text=msg)
                        )
                    except (RuntimeError, Exception):
                        pass

        GlobalBroadcastManager.subscribe("ZONE_TRANSITION", _on_zone_event)
        GlobalBroadcastManager.subscribe("ZONE_COMPLETE", _on_zone_event)
        logger.info("[WO-V40.0] Telegram: subscribed to ZONE_TRANSITION/COMPLETE")
    except (ImportError, Exception) as e:
        logger.debug(f"[WO-V40.0] Zone broadcast subscription skipped: {e}")

    print("✅ Bot configured. Starting polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

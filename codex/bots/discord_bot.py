#!/usr/bin/env python3
"""
CODEX DISCORD BOT — Command Priority System
============================================

Discord interface for C.O.D.E.X. with proper command hierarchy:
1. Guard Clauses (ignore self, bots)
2. System Commands (!help, !menu, !status, !clear, !play)
3. Game Session Logic (Crown & Crew)
4. Mimir Chat (fallback AI conversation)

Version: 3.1 (Command Priority Patch)
"""

import asyncio
import io
import json
import logging
import os
import re
import random
import tempfile
import threading
import time
import wave
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Opus path for aarch64 (Raspberry Pi 5)
_OPUS_PATH = "/usr/lib/aarch64-linux-gnu/libopus.so.0"

# WO-V9.4: Track consecutive opus decode failures for watchdog
_opus_error_count = 0
_opus_error_lock = threading.Lock()

from codex.core.butler import CodexButler
from codex.games.crown.engine import CrownAndCrewEngine
from codex.games.burnwillow.bridge import BurnwillowBridge
from codex.games.bridge import UniversalGameBridge

try:
    from codex.forge.omni_forge import OmniForge
    OMNI_FORGE_AVAILABLE = True
except ImportError:
    OMNI_FORGE_AVAILABLE = False

try:
    from codex.games.burnwillow.discord_embed import (
        character_to_discord_embed,
        character_to_discord_embed_compact,
    )
    BURNWILLOW_EMBEDS_AVAILABLE = True
except ImportError:
    BURNWILLOW_EMBEDS_AVAILABLE = False

try:
    from codex.integrations.tarot import TAROT_CARDS, get_card_for_context, format_tarot_text
    TAROT_AVAILABLE = True
except ImportError:
    TAROT_AVAILABLE = False

from codex.core.menu import CodexMenu
_MENU = CodexMenu()

_ROOT = Path(__file__).resolve().parent.parent.parent  # -> Codex/

# Lazy-init Scrying instances (WO V4.2 — Player View screenshots)
_scryer = None
_player_renderer = None


def _get_scryer():
    """Lazy-init the ScryingEngine."""
    global _scryer
    if _scryer is None:
        from codex.bots.scryer import ScryingEngine
        _scryer = ScryingEngine()
    return _scryer


def _get_player_renderer():
    """Lazy-init the PlayerRenderer."""
    global _player_renderer
    if _player_renderer is None:
        from codex.spatial.player_renderer import PlayerRenderer
        _player_renderer = PlayerRenderer()
    return _player_renderer


def _write_player_frame(frame):
    """Write a StateFrame to state/player_frame.json for play_player_view.py."""
    try:
        frame_path = _ROOT / "state" / "player_frame.json"
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(frame, 'to_dict'):
            data = frame.to_dict()
        else:
            data = {"raw": str(frame)}
        frame_path.write_text(json.dumps(data, default=str))
    except Exception:
        pass


async def _try_scry_and_send(channel, frame, fallback_text: str):
    """Attempt to scry a frame to PNG and send it; fall back to text on failure.

    Includes thermal guard: skips rendering if CPU > 75C.
    """
    if frame is None:
        await channel.send(f"```\n{fallback_text}\n```")
        return

    # Thermal guard
    try:
        from codex.core.cortex import CodexCortex
        cortex = CodexCortex()
        state = cortex.read_metabolic_state()
        if state.cpu_temp_celsius > 75:
            await channel.send(f"```\n{fallback_text}\n```")
            return
    except Exception:
        pass  # No cortex available, proceed with rendering

    try:
        from codex.bots.scryer import scry_frame
        png = await scry_frame(frame, _get_scryer(), _get_player_renderer())
        if png and png.exists():
            await channel.send(file=discord.File(str(png), filename="view.png"))
            return
    except Exception:
        pass  # Fall back to text

    await channel.send(f"```\n{fallback_text}\n```")


async def _scry_embed_update(session, channel, frame, action_text: str):
    """Update the session's live ScryingEmbed with the latest frame.

    Creates the embed on first call.  Falls back to _try_scry_and_send
    if scrying dependencies are missing or the embed update fails.
    """
    if frame is None:
        await channel.send(f"```\n{action_text}\n```")
        return

    # Lazy-create the ScryingEmbed for this session
    if session.scrying_embed is None:
        try:
            from codex.bots.scryer import ScryingEmbed
            session.scrying_embed = ScryingEmbed(channel)
        except ImportError:
            await _try_scry_and_send(channel, frame, action_text)
            return

    # Render frame to PNG
    png = None
    try:
        from codex.bots.scryer import scry_frame
        png = await scry_frame(frame, _get_scryer(), _get_player_renderer())
    except Exception:
        pass

    if png and png.exists():
        caption = action_text[:200] if action_text else ""
        try:
            await session.scrying_embed.update(png, caption=caption)
        except Exception:
            # Embed update failed (message deleted, permissions, etc.) — reset and fall back
            session.scrying_embed = None
            await _try_scry_and_send(channel, frame, action_text)
    else:
        await channel.send(f"```\n{action_text}\n```")


load_dotenv()
logger = logging.getLogger("CODEX.Discord")


# ── WO-V9.4: Suppress py-cord opus decode error spam ──────────────────────
# py-cord's VoiceClient prints "Error occurred while decoding opus frame."
# directly to stderr or via the discord.player logger.  We install a filter
# to absorb these and count them so the watchdog can act.
class _OpusErrorFilter(logging.Filter):
    """Absorb opus decode errors; increment the global counter instead."""

    def filter(self, record: logging.LogRecord) -> bool:
        global _opus_error_count
        msg = record.getMessage()
        if "decoding opus" in msg.lower() or "opus frame" in msg.lower():
            with _opus_error_lock:
                _opus_error_count += 1
                # Log once every 50 to avoid total silence
                return _opus_error_count % 50 == 1
        return True


for _vlogger_name in ("discord.player", "discord.voice_client", "discord.gateway"):
    logging.getLogger(_vlogger_name).addFilter(_OpusErrorFilter())


# =============================================================================
# SYSTEM CONSTANTS
# =============================================================================

WAKE_WORDS = ["mimir", "volo", "codex", "computer"]

HELP_TEXT = """```
╔════════════════════════════════════════╗
║        📡 MIMIR UPLINK v3.1            ║
╠════════════════════════════════════════╣
║                                        ║
║  SYSTEM COMMANDS:                      ║
║  ─────────────────                     ║
║  !menu   :: Main Menu / Module Select  ║
║  !play   :: Alias for !menu            ║
║  !prologue :: Launch Session Zero      ║
║  !travel :: Advance from Morning       ║
║  !burnwillow :: Start dungeon run      ║
║  !dnd5e  :: D&D 5e dungeon crawl      ║
║  !cosmere :: Cosmere dungeon crawl    ║
║  !stop   :: End Session / Abort        ║
║  !status :: Game State & Vitals        ║
║  !help   :: Display this transmission  ║
║  !clear  :: Purge session memory       ║
║  !ping   :: Instant health check       ║
║  !summon :: Acknowledge presence       ║
║  !voice  :: Join/leave voice channel   ║
║  !dm     :: DM Tools (dice/npc/loot)  ║
║  !monster :: Bestiary creature lookup  ║
║  !create :: Create a character         ║
║  !map    :: Show current map as PNG    ║
║                                        ║
║  GAMEPLAY:                             ║
║  ─────────────────                     ║
║  crown / crew :: Declare allegiance    ║
║  1 / 2        :: Council vote          ║
║                                        ║
║  WAKE WORDS:                           ║
║  ─────────────────                     ║
║  "mimir", "volo", "codex", "computer"  ║
║  Or just @mention me to chat!          ║
║                                        ║
╚════════════════════════════════════════╝

    Latency is an opportunity for lore.
```"""

STATUS_OFFLINE = """```
╔════════════════════════════════════════╗
║          🔴 SYSTEM OFFLINE             ║
║   Core not initialized. Try !help      ║
╚════════════════════════════════════════╝
```"""


# =============================================================================
# DISCORD SESSION — Crown & Crew State Machine
# =============================================================================

class Phase(Enum):
    """Game phases for Crown & Crew."""
    IDLE = auto()           # No active game
    MENU = auto()           # Main menu shown, awaiting selection
    DUNGEON = auto()        # Free-text Burnwillow input
    MORNING = auto()        # World card shown, awaiting !travel
    NIGHT = auto()          # Allegiance choice
    CAMPFIRE = auto()       # Reflection (skip Breach day)
    COUNCIL = auto()        # Group vote
    FINALE = auto()         # Game over
    OMNI = auto()           # WO 089 — Omni-Forge sub-menu
    DND5E = auto()          # WO V4.0 — D&D 5e dungeon session
    COSMERE = auto()        # WO V4.0 — Cosmere dungeon session
    REST = auto()           # WO-V23.0 — Rest choice after council
    ASHBURN_HEIR = auto()   # WO-V23.0 — Ashburn heir selection
    ASHBURN_LEGACY = auto() # WO-V23.0 — Ashburn legacy choice
    QUEST_SELECT = auto()   # WO-V23.0 — Quest archetype selection


# =============================================================================
# OMNI-CHANNEL BUTTONS (Batch 005)
# =============================================================================

class NavigationButtons(discord.ui.View):
    """Cardinal direction buttons derived from available exits."""

    def __init__(self, exits: list[str], session):
        super().__init__(timeout=120)
        self._session = session
        _labels = {"north": "N", "south": "S", "east": "E", "west": "W"}
        for direction in ("north", "south", "east", "west"):
            btn = discord.ui.Button(
                label=_labels[direction],
                style=discord.ButtonStyle.primary if direction in exits else discord.ButtonStyle.secondary,
                disabled=direction not in exits,
                custom_id=f"nav_{direction}",
            )
            btn.callback = self._make_callback(direction)
            self.add_item(btn)

    def _make_callback(self, direction: str):
        async def callback(interaction: discord.Interaction):
            if self._session.bridge:
                result = self._session.bridge.step(direction)
                frame = getattr(self._session.bridge, 'last_frame', None)
                await interaction.response.send_message(
                    f"```\n{result}\n```", view=self._build_next())
                # Update live embed in background
                if frame:
                    await _scry_embed_update(
                        self._session, interaction.channel, frame, result)
                if self._session.bridge.dead:
                    self._session.end_session()
        return callback

    def _build_next(self):
        """Rebuild navigation buttons from current room exits."""
        if not self._session.bridge:
            return None
        exits = getattr(self._session.bridge, "current_exits", [])
        return NavigationButtons(exits, self._session)


class ActionButtons(discord.ui.View):
    """Persistent action buttons for look/search/loot/inventory."""

    def __init__(self, session):
        super().__init__(timeout=120)
        self._session = session

    @discord.ui.button(label="Look", style=discord.ButtonStyle.secondary, custom_id="act_look")
    async def btn_look(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._step(interaction, "look")

    @discord.ui.button(label="Search", style=discord.ButtonStyle.secondary, custom_id="act_search")
    async def btn_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._step(interaction, "search")

    @discord.ui.button(label="Loot", style=discord.ButtonStyle.success, custom_id="act_loot")
    async def btn_loot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._step(interaction, "loot")

    @discord.ui.button(label="Inventory", style=discord.ButtonStyle.secondary, custom_id="act_inv")
    async def btn_inv(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._step(interaction, "inventory")

    async def _step(self, interaction: discord.Interaction, cmd: str):
        if self._session.bridge:
            result = self._session.bridge.step(cmd)
            frame = getattr(self._session.bridge, 'last_frame', None)
            await interaction.response.send_message(f"```\n{result}\n```")
            # Update live embed in background
            if frame:
                await _scry_embed_update(
                    self._session, interaction.channel, frame, result)
            if self._session.bridge.dead:
                self._session.end_session()


class GameCommandView(discord.ui.View):
    """Category dropdown command interface for game sessions.

    WO-V9.4: Pulls commands from bridge.COMMAND_CATEGORIES (single source
    of truth) instead of hardcoded defaults.  Falls back to orchestrator
    categories (FITD), then to _FALLBACK_COMMANDS as last resort.
    """

    # Last-resort fallback if bridge has no COMMAND_CATEGORIES
    _FALLBACK_COMMANDS = {
        "movement": {
            "north": "Move north", "south": "Move south",
            "east": "Move east", "west": "Move west",
        },
        "combat": {
            "attack": "Fight the first enemy", "rest": "Heal ~50% HP",
        },
        "exploration": {
            "look": "Describe current room", "search": "Search for loot",
            "map": "Show mini-map", "inventory": "Show inventory",
            "stats": "Show character stats", "help": "List all commands",
        },
    }

    def __init__(self, session, orchestrator=None):
        super().__init__(timeout=300)
        self._session = session
        self._build_selects()

    def _resolve_categories(self) -> dict[str, dict[str, str]]:
        """Resolve command categories from the best available source.

        Priority: bridge.COMMAND_CATEGORIES > orchestrator > _FALLBACK_COMMANDS
        """
        # 1. Bridge (single source of truth)
        bridge = getattr(self._session, 'bridge', None)
        if bridge:
            cats = getattr(bridge, 'COMMAND_CATEGORIES', None)
            if cats:
                return cats

        # 2. Last resort
        return self._FALLBACK_COMMANDS

    def _build_selects(self):
        """Build category Select Menus from resolved command categories."""
        categorized = self._resolve_categories()
        row = 0
        for cat_name, cmds_dict in categorized.items():
            if row >= 5:
                break
            options = [
                discord.SelectOption(
                    label=cmd.replace("_", " ").title(),
                    value=cmd,
                    description=desc[:50],
                )
                for cmd, desc in cmds_dict.items()
            ]
            if not options:
                continue
            select = discord.ui.Select(
                placeholder=f"{cat_name.title()} Commands",
                options=options[:25],
                row=row,
            )
            select.callback = self._make_callback()
            self.add_item(select)
            row += 1

    def _make_callback(self):
        async def callback(interaction):
            cmd = interaction.data["values"][0]
            if self._session.bridge:
                result = self._session.bridge.step(cmd)
                new_view = GameCommandView(self._session) if not self._session.bridge.dead else None
                frame = getattr(self._session.bridge, 'last_frame', None)
                await interaction.response.send_message(
                    f"```\n{result}\n```", view=new_view)
                # Update live embed in background
                if frame:
                    await _scry_embed_update(
                        self._session, interaction.channel, frame, result)
                if self._session.bridge.dead:
                    self._session.end_session()
        return callback


# =============================================================================
# CHARACTER CREATION VIEW (Phase E)
# =============================================================================

_SYSTEM_ARCHETYPES = {
    "dnd5e": ["Fighter", "Wizard", "Rogue", "Cleric", "Ranger", "Barbarian", "Bard", "Paladin"],
    "cosmere": ["Soldier", "Scholar", "Scout", "Mystic"],
    "cbrpnk": ["Solo", "Netrunner", "Tech", "Fixer"],
}

# Burnwillow loadouts from vault/burnwillow/creation_rules.json
_BW_LOADOUTS = [
    ("sellsword", "The Sellsword", "Sword + Jerkin + Gloves [Lockpick]"),
    ("occultist", "The Occultist", "Wand + Bell [Summon] + Jerkin"),
    ("sentinel", "The Sentinel", "Sword + Shield [Intercept] + Jerkin"),
    ("archer", "The Archer", "Shortbow [Ranged] + Jerkin"),
    ("vanguard", "The Vanguard", "Greatsword [Cleave] + Jerkin"),
    ("scholar", "The Scholar", "Grimoire [Spellslot] + Robes + Gloves [Lockpick]"),
]

# Track users awaiting name input during Burnwillow character creation
_pending_name_input: dict = {}  # user_id -> {"channel_id": int, "char_data": dict}


class CharacterCreationView(discord.ui.View):
    """Step-by-step character creation using Discord UI components."""

    def __init__(self, user_id: int, channel, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.channel = channel
        self.char_data = {"user_id": user_id}

    @discord.ui.select(
        placeholder="Choose a game system",
        options=[
            discord.SelectOption(label="Burnwillow", value="burnwillow", description="Dark fantasy dungeon crawler"),
            discord.SelectOption(label="D&D 5e", value="dnd5e", description="Classic D&D dungeon crawl"),
            discord.SelectOption(label="Cosmere", value="cosmere", description="Stormlight-inspired adventure"),
            discord.SelectOption(label="CBR+PNK", value="cbrpnk", description="Cyberpunk one-shot"),
        ],
        row=0,
    )
    async def select_system(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character creation!", ephemeral=True)
            return

        system = select.values[0]
        self.char_data["system"] = system

        if system == "burnwillow":
            # Burnwillow wizard: Name -> Stats -> Loadout (matches terminal wizard)
            _pending_name_input[self.user_id] = {
                "channel_id": interaction.channel.id,
                "char_data": self.char_data,
            }
            embed = discord.Embed(
                title="Character Creation -- Burnwillow",
                description=(
                    "**Step 1: Name Your Wanderer**\n\n"
                    "What do they call you? Type your character's name in chat."
                ),
                color=0xFFD700,
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Non-Burnwillow: archetype selection flow
        archetypes = _SYSTEM_ARCHETYPES.get(system, ["Adventurer"])
        options = [
            discord.SelectOption(label=a, value=a.lower())
            for a in archetypes
        ]

        archetype_view = CharacterArchetypeView(
            self.user_id, self.channel, self.char_data, options)
        embed = discord.Embed(
            title="Character Creation",
            description=f"System: **{system.title()}**\nNow choose your archetype.",
            color=0x3498DB,
        )
        await interaction.response.edit_message(embed=embed, view=archetype_view)


class CharacterArchetypeView(discord.ui.View):
    """Archetype selection step for non-Burnwillow systems."""

    def __init__(self, user_id, channel, char_data, options, timeout=300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.channel = channel
        self.char_data = char_data

        select = discord.ui.Select(
            placeholder="Choose your archetype",
            options=options,
            row=0,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character creation!", ephemeral=True)
            return

        archetype = interaction.data["values"][0]
        self.char_data["archetype"] = archetype

        # Generate stats (4d6 drop lowest x6) for D&D-style systems
        import random
        stats = {}
        for stat in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            rolls = sorted([random.randint(1, 6) for _ in range(4)])
            stats[stat] = sum(rolls[1:])  # drop lowest
        self.char_data["stats"] = stats

        # Default name if not set yet
        if "name" not in self.char_data:
            self.char_data["name"] = f"Hero_{self.user_id % 10000}"

        stat_line = "  ".join(f"{k}: {v}" for k, v in stats.items())
        confirm_view = CharacterConfirmView(self.user_id, self.channel, self.char_data)
        embed = discord.Embed(
            title="Character Summary",
            description=(
                f"**Name:** {self.char_data.get('name', 'Unnamed')}\n"
                f"**System:** {self.char_data['system'].title()}\n"
                f"**Archetype:** {archetype.title()}\n"
                f"**Stats:** {stat_line}"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text="Confirm to save, or Redo to start over.")
        await interaction.response.edit_message(embed=embed, view=confirm_view)


# ─────────────────────────────────────────────────────────────────────────────
# BURNWILLOW CHARACTER WIZARD (matches terminal char_wizard flow)
# ─────────────────────────────────────────────────────────────────────────────

class BurnwillowStatAllocView(discord.ui.View):
    """Interactive stat pool allocation — roll 4d6-drop-lowest x4, assign to stats."""

    def __init__(self, user_id, channel, char_data, timeout=300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.channel = channel
        self.char_data = char_data
        self.all_stats = ["Might", "Wits", "Grit", "Aether"]
        self.remaining_stats = list(self.all_stats)
        self.assigned = {}
        self._roll_pool()
        self._build_ui()

    def _roll_pool(self):
        """Roll 4d6-drop-lowest x4 and sort high-to-low."""
        import random
        self.pool = []
        for _ in range(4):
            dice = sorted([random.randint(1, 6) for _ in range(4)])
            self.pool.append(sum(dice[1:]))
        self.pool.sort(reverse=True)
        self.remaining_pool = list(self.pool)

    def _build_ui(self):
        """Rebuild the select + buttons for current allocation state."""
        self.clear_items()

        if self.remaining_pool and self.remaining_stats:
            score = self.remaining_pool[0]
            options = [
                discord.SelectOption(
                    label=stat, value=stat,
                    description=f"Assign {score} to {stat}")
                for stat in self.remaining_stats
            ]
            select = discord.ui.Select(
                placeholder=f"Assign {score} to which stat?",
                options=options, row=0)
            select.callback = self._on_assign
            self.add_item(select)

        reroll = discord.ui.Button(
            label="Reroll All", style=discord.ButtonStyle.secondary, row=1)
        reroll.callback = self._on_reroll
        self.add_item(reroll)

    async def _on_assign(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your character!", ephemeral=True)
            return

        stat = interaction.data["values"][0]
        score = self.remaining_pool.pop(0)
        self.remaining_stats.remove(stat)
        self.assigned[stat] = score

        # Auto-assign last remaining stat
        if len(self.remaining_stats) == 1 and self.remaining_pool:
            last_stat = self.remaining_stats[0]
            last_score = self.remaining_pool.pop(0)
            self.assigned[last_stat] = last_score
            self.remaining_stats.clear()

        if not self.remaining_stats:
            # All assigned — move to loadout selection
            self.char_data["stats"] = self.assigned
            loadout_view = BurnwillowLoadoutView(
                self.user_id, self.channel, self.char_data)
            stat_line = "  ".join(f"**{k}:** {v}" for k, v in self.assigned.items())
            embed = discord.Embed(
                title="Choose Your Loadout",
                description=(
                    f"**{self.char_data.get('name', 'Hero')}** — Stats: {stat_line}\n\n"
                    "Your gear defines you. Choose wisely."
                ),
                color=0xFFD700,
            )
            await interaction.response.edit_message(embed=embed, view=loadout_view)
        else:
            self._build_ui()
            embed = self._build_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    async def _on_reroll(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your character!", ephemeral=True)
            return
        self.assigned.clear()
        self.remaining_stats = list(self.all_stats)
        self._roll_pool()
        self._build_ui()
        embed = self._build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def _build_embed(self):
        pool_str = ", ".join(f"**{s}**" for s in self.remaining_pool)
        assigned_lines = [f"**{k}:** {v}" for k, v in self.assigned.items()]
        desc = f"**Rolled Pool:** [{pool_str}]\n"
        if assigned_lines:
            desc += "\n" + "\n".join(assigned_lines) + "\n"
        if self.remaining_pool:
            desc += f"\nAssign **{self.remaining_pool[0]}** to a stat:"
        return discord.Embed(
            title=f"Stat Allocation -- {self.char_data.get('name', 'Hero')}",
            description=desc,
            color=0xFFD700,
        )


class BurnwillowLoadoutView(discord.ui.View):
    """Loadout selection — matches creation_rules.json options."""

    def __init__(self, user_id, channel, char_data, timeout=300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.channel = channel
        self.char_data = char_data

        options = [
            discord.SelectOption(label=label, value=lid, description=desc)
            for lid, label, desc in _BW_LOADOUTS
        ]
        select = discord.ui.Select(
            placeholder="Choose your loadout", options=options, row=0)
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your character!", ephemeral=True)
            return

        loadout_id = interaction.data["values"][0]
        self.char_data["loadout"] = loadout_id
        # Store display label as archetype
        for lid, label, _desc in _BW_LOADOUTS:
            if lid == loadout_id:
                self.char_data["archetype"] = label
                break

        # Move to confirm
        confirm_view = CharacterConfirmView(self.user_id, self.channel, self.char_data)
        stats = self.char_data.get("stats", {})
        stat_line = "  ".join(f"{k}: {v}" for k, v in stats.items())
        embed = discord.Embed(
            title="Character Summary",
            description=(
                f"**Name:** {self.char_data.get('name', 'Hero')}\n"
                f"**System:** Burnwillow\n"
                f"**Loadout:** {self.char_data.get('archetype', 'The Sellsword')}\n"
                f"**Stats:** {stat_line}"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text="Confirm to save, or Redo to start over.")
        await interaction.response.edit_message(embed=embed, view=confirm_view)


class CharacterConfirmView(discord.ui.View):
    """Confirm or redo character creation."""

    def __init__(self, user_id, channel, char_data, timeout=300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.channel = channel
        self.char_data = char_data

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, row=0)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character!", ephemeral=True)
            return

        # Save to state/discord_characters/{user_id}.json
        save_dir = _ROOT / "state" / "discord_characters"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"{self.user_id}.json"
        save_path.write_text(json.dumps(self.char_data, indent=2))

        embed = discord.Embed(
            title="Character Saved!",
            description=(
                f"**{self.char_data.get('name', 'Hero')}** the "
                f"**{self.char_data.get('archetype', 'Adventurer').title()}** "
                f"is ready for adventure.\n\n"
                f"Start a game with `!burnwillow`, `!dnd5e`, or `!cosmere`."
            ),
            color=0x27AE60,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Redo", style=discord.ButtonStyle.danger, row=0)
    async def redo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character!", ephemeral=True)
            return

        view = CharacterCreationView(self.user_id, self.channel)
        embed = discord.Embed(
            title="Character Creation",
            description="Starting over. Choose a game system.",
            color=0x3498DB,
        )
        await interaction.response.edit_message(embed=embed, view=view)


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


# Council Dilemmas now sourced from engine.get_council_dilemma() (WO-V23.0)


@dataclass
class DiscordSession:
    """Stateful session manager for a single Discord channel."""
    channel_id: int
    phase: Phase = Phase.IDLE
    engine: Optional[CrownAndCrewEngine] = None
    current_dilemma: Optional[dict] = None
    game_type: str = ""
    bridge: Optional[object] = None  # BurnwillowBridge or UniversalGameBridge
    mimir: object = None  # WO 088 — AI narrative bridge
    scrying_embed: Optional[object] = None  # ScryingEmbed for live player view
    # WO-V35.0: Parity gap fields
    conditions: object = None       # ConditionTracker (optional)
    initiative_order: list = field(default_factory=list)
    active_turn: str = ""

    def start_game(self) -> str:
        """Initialize a new Crown & Crew session (WO-V14.0: morning events)."""
        if self.phase != Phase.IDLE:
            return "A game is already in progress. Use `!menu` to end it first."

        self.engine = CrownAndCrewEngine(mimir=self.mimir)
        self.phase = Phase.MORNING

        world = self.engine.get_world_prompt()
        # WO-V25.0: Tarot card for world prompt
        if TAROT_AVAILABLE:
            card_key = get_card_for_context("world")
            card_text = format_tarot_text(card_key, world[:200])
            world = f"```\n{card_text}\n```\n\n{world}"
        morning_event = self.engine.get_morning_event()
        event_text = morning_event["text"]

        arc_days = f"{self.engine.arc_length} days"
        return f"""```
╔════════════════════════════════════════════════════════════╗
║                    ⚔️  CROWN & CREW ⚔️                      ║
║              {arc_days} to reach the border.{' ' * (34 - len(arc_days))}║
╠════════════════════════════════════════════════════════════╣
║  Patron: {self.engine.patron:<46} ║
║  Leader: {self.engine.leader:<46} ║
╠════════════════════════════════════════════════════════════╣
║  {self.engine.get_status():<54} ║
╚════════════════════════════════════════════════════════════╝
```
**☀️ MORNING — DAY {self.engine.day}**

_{world}_

**THE ROAD AHEAD**
_{event_text}_

Type `!travel` when ready to move on."""

    def handle_travel(self) -> str:
        """Transition from MORNING to NIGHT."""
        if self.phase != Phase.MORNING:
            return "You can only `!travel` during the morning phase."

        self.phase = Phase.NIGHT

        # Day 3 Breach
        breach_text = ""
        if self.engine.is_breach_day():
            breach_text = f"\n\n**👁️ THE BREACH**\n_{self.engine.get_secret_witness()}_\n"

        return f"""```
DAY {self.engine.day} — {self.engine.get_status()}
```
**🌙 NIGHT — THE MOMENT OF CHOICE**
{breach_text}
You must declare your allegiance BEFORE you see the consequences.

Type `crown` or `crew` to choose your side."""

    def handle_allegiance(self, side: str) -> Optional[str]:
        """Process allegiance choice."""
        if self.phase != Phase.NIGHT:
            return None

        side = side.lower().strip()
        if side not in ("crown", "crew"):
            return None

        result = self.engine.declare_allegiance(side)
        prompt = self.engine.get_prompt(side)
        # WO-V25.0: Tarot card for allegiance
        if TAROT_AVAILABLE:
            card_key = get_card_for_context(side)
            card_text = format_tarot_text(card_key, prompt[:200])
            prompt = f"```\n{card_text}\n```\n\n{prompt}"

        # Check Drifter's Tax
        tax_msg = ""
        if self.engine.check_drifter_tax():
            tax_msg = "\n\n**⚠️ DRIFTER'S TAX:** Neutrality has consequences..."

        # WO-V24.1: Ashburn legacy check (if engine supports it)
        legacy_msg = ""
        if hasattr(self.engine, 'generate_legacy_check'):
            check = self.engine.generate_legacy_check()
            if check.get("triggered"):
                self.phase = Phase.ASHBURN_LEGACY
                side_icon = "👑" if side == "crown" else "🏴"
                return (
                    f"**{side_icon} {side.upper()} CHOSEN**\n"
                    f"_{result}_\n"
                    f"{tax_msg}\n\n"
                    f"**THE DILEMMA:**\n"
                    f"_{prompt}_\n\n"
                    f"---\n\n"
                    f"**⚠️ LEGACY CALL**\n"
                    f"_{check['prompt']}_\n\n"
                    f"Type `1` (Obey) or `2` (Lie)."
                )

        # Move to campfire or council (WO-V23.0: dynamic breach day)
        if self.engine.is_breach_day():
            self.phase = Phase.COUNCIL
            self._generate_dilemma()
            next_phase = self._format_council()
        else:
            self.phase = Phase.CAMPFIRE
            next_phase = self._format_campfire()

        side_icon = "👑" if side == "crown" else "🏴"
        return f"""**{side_icon} {side.upper()} CHOSEN**
_{result}_
{tax_msg}

**THE DILEMMA:**
_{prompt}_

*What do you do?*

{next_phase}"""

    def _format_campfire(self) -> str:
        """Format campfire phase."""
        campfire = self.engine.get_campfire_prompt()
        # WO-V25.0: Tarot card for campfire
        if TAROT_AVAILABLE:
            card_key = get_card_for_context("campfire")
            card_text = format_tarot_text(card_key, campfire[:200])
            campfire = f"```\n{card_text}\n```\n\n{campfire}"
        return f"""
---
**🔥 CAMPFIRE**
_{campfire}_

*Share your reflection, then type `done` to continue.*"""

    def _format_council(self) -> str:
        """Format council phase with Crown/Crew labeling (WO-V14.0)."""
        return f"""
---
**⚖️ MIDNIGHT COUNCIL**

{self.current_dilemma['prompt']}

**[1] CROWN PATH:** {self.current_dilemma['crown']}
**[2] CREW PATH:** {self.current_dilemma['crew']}

Type `1` or `2` to vote."""

    def handle_campfire_done(self) -> Optional[str]:
        """Transition from CAMPFIRE to COUNCIL."""
        if self.phase != Phase.CAMPFIRE:
            return None

        self.phase = Phase.COUNCIL
        self._generate_dilemma()

        return f"""*The fire dies down. The council gathers.*

{self._format_council()}"""

    def handle_vote(self, choice: str) -> Optional[str]:
        """Process council vote (WO-V23.0: REST phase + arc_length)."""
        if self.phase != Phase.COUNCIL:
            return None

        if choice not in ("1", "2"):
            return None

        path = "CROWN" if choice == "1" else "CREW"
        outcome = self.current_dilemma['crown'] if choice == "1" else self.current_dilemma['crew']

        # Check if this is the final day — skip rest, go straight to finale
        if self.engine.day >= self.engine.arc_length:
            day_result = self.engine.end_day()
            self.phase = Phase.FINALE
            return self._format_finale(path, outcome)

        # Offer rest choice (WO-V23.0)
        self.phase = Phase.REST
        return f"""**📜 The council chose the {path} path.**
_{outcome}_

---
**🛏️ THE CAMP**

The day's trials are behind you. How do you rest?

Type `long` — Full rest, advance to next day.
Type `short` — Brief respite, stay on current day.
Type `skip` — Press on. Sway decays toward neutral."""

    def handle_rest(self, choice: str) -> Optional[str]:
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
            # Short rest does NOT advance day — return to morning of same day
            self.phase = Phase.MORNING
            world = self.engine.get_world_prompt()
            morning_event = self.engine.get_morning_event()
            event_text = morning_event["text"]
            return f"""**☕ Short Rest**
_{short_msg}_

---
```
DAY {self.engine.day} — {self.engine.get_status()}
```
**☀️ MORNING — DAY {self.engine.day}**

_{world}_

**THE ROAD AHEAD**
_{event_text}_

Type `!travel` when ready."""
        else:
            skip_msg = self.engine.skip_rest()
            day_result = self.engine.end_day()

        # Check if game over after rest
        if self.engine.day > self.engine.arc_length:
            self.phase = Phase.FINALE
            report = self.engine.generate_legacy_report()
            # WO-V25.0: Tarot card for legacy
            tarot_block = ""
            if TAROT_AVAILABLE:
                card_key = get_card_for_context("legacy")
                card_text = format_tarot_text(card_key, "Your journey ends. The border awaits.")
                tarot_block = f"```\n{card_text}\n```\n\n"
            summary = self.engine.get_summary()
            result = f"""**🛏️ {day_result if choice == 'long' else skip_msg}**

---
```
╔════════════════════════════════════════════════════════════╗
║            ⚔️  THE BORDER — JOURNEY'S END ⚔️               ║
╚════════════════════════════════════════════════════════════╝
```

{tarot_block}**LEGACY REPORT:**
```
{report}
```

**JOURNEY LOG:**
```
{summary}
```

_The campaign is complete. Use `!play` to begin anew._"""
            self.phase = Phase.IDLE
            self.engine = None
            return result

        # Next day — morning
        self.phase = Phase.MORNING
        world = self.engine.get_world_prompt()
        morning_event = self.engine.get_morning_event()
        event_text = morning_event["text"]

        return f"""**🛏️ {day_result}**

---
```
DAY {self.engine.day} — {self.engine.get_status()}
```
**☀️ MORNING — DAY {self.engine.day}**

_{world}_

**THE ROAD AHEAD**
_{event_text}_

Type `!travel` when ready."""

    def _format_finale(self, path: str, outcome: str) -> str:
        """Format the game finale."""
        report = self.engine.generate_legacy_report()
        summary = self.engine.get_summary()

        # Reset for next game
        result = f"""**📜 The council chose the {path} path.**
_{outcome}_

---
```
╔════════════════════════════════════════════════════════════╗
║            ⚔️  THE BORDER — JOURNEY'S END ⚔️               ║
╚════════════════════════════════════════════════════════════╝
```

**LEGACY REPORT:**
```
{report}
```

**JOURNEY LOG:**
```
{summary}
```

_The campaign is complete. Use `!play` to begin anew._"""

        self.phase = Phase.IDLE
        self.engine = None
        return result

    def _generate_dilemma(self):
        """Generate a council dilemma from engine (WO-V23.0)."""
        self.current_dilemma = self.engine.get_council_dilemma()

    def end_session(self) -> str:
        """Force end the session."""
        if self.phase == Phase.IDLE:
            return "No active session."
        self.phase = Phase.IDLE
        self.engine = None
        self.bridge = None
        self.game_type = ""
        self.scrying_embed = None
        self.conditions = None
        self.initiative_order = []
        self.active_turn = ""
        return "\U0001f6d1 Session Terminated. Returning to Idle State."

    def get_status(self) -> str:
        """Get session status."""
        if self.phase == Phase.IDLE or not self.engine:
            return "No active campaign. Use `!play` to begin."
        arc = self.engine.arc_length
        return f"""```
╔════════════════════════════════════════╗
║          SESSION STATUS                ║
╠════════════════════════════════════════╣
║  Day:    {self.engine.day}/{arc:<25} ║
║  Phase:  {self.phase.name:<28} ║
║  Sway:   {self.engine.sway:+d} ({self.engine.get_tier()['name']:<20}) ║
║  Patron: {self.engine.patron:<28} ║
║  Leader: {self.engine.leader:<28} ║
╚════════════════════════════════════════╝
```"""


# =============================================================================
# SESSION REGISTRY
# =============================================================================

sessions: dict[int, DiscordSession] = {}
_mimir_ref: object = None  # WO 088 — set by CodexBot on init


def get_session(channel_id: int) -> DiscordSession:
    """Get or create a session for a channel."""
    if channel_id not in sessions:
        sessions[channel_id] = DiscordSession(channel_id=channel_id, mimir=_mimir_ref)
    return sessions[channel_id]


# =============================================================================
# VOICE RECEIVE — Ears STT Bridge (WO 115)
# =============================================================================

class _UtteranceSink(discord.sinks.Sink):
    """Custom audio sink that buffers per-user PCM with silence detection.

    Instead of waiting for stop_recording(), this sink lets VoiceListener
    poll for completed utterances via harvest() while recording continues.
    """

    def __init__(self, *, filters=None):
        super().__init__(filters=filters)
        self.encoding = "wav"
        self._buffers: dict[int, bytearray] = {}
        self._last_ts: dict[int, float] = {}
        self._busy: set[int] = set()
        self._lock = threading.Lock()
        # Audio format params (set by init() from VoiceClient.decoder)
        self._channels = 2
        self._sample_width = 2
        self._sample_rate = 48000

    def init(self, vc):
        """Called by py-cord when recording starts."""
        super().init(vc)
        if hasattr(vc, 'decoder'):
            self._channels = vc.decoder.CHANNELS
            self._sample_width = vc.decoder.SAMPLE_SIZE // vc.decoder.CHANNELS
            self._sample_rate = vc.decoder.SAMPLING_RATE

    @discord.sinks.Filters.container
    def write(self, data, user):
        """Receive PCM audio from the voice reader thread.

        WO-V9.4: Wraps with try/except to silently drop malformed frames
        instead of spamming the console with opus decoding errors.
        """
        global _opus_error_count
        try:
            with self._lock:
                if user not in self._buffers:
                    self._buffers[user] = bytearray()
                self._buffers[user].extend(data)
                self._last_ts[user] = time.time()
            # Reset error counter on successful frame
            with _opus_error_lock:
                _opus_error_count = 0
        except Exception:
            with _opus_error_lock:
                _opus_error_count += 1
                if _opus_error_count <= 3:
                    logger.warning(
                        f"Opus frame dropped ({_opus_error_count} consecutive)"
                    )

    def harvest(self, silence_s: float, min_bytes: int):
        """Return completed utterances: list of (user_id, pcm_bytes).
        An utterance is complete when the user has been silent for silence_s
        and has accumulated at least min_bytes of audio."""
        now = time.time()
        results = []
        with self._lock:
            for uid in list(self._last_ts):
                if uid in self._busy:
                    continue
                if now - self._last_ts[uid] >= silence_s:
                    buf = self._buffers.get(uid)
                    if buf and len(buf) >= min_bytes:
                        results.append((uid, bytes(buf)))
                        self._buffers[uid] = bytearray()
                        self._busy.add(uid)
        return results

    def mark_done(self, user_id: int):
        """Allow user to be harvested again after processing."""
        with self._lock:
            self._busy.discard(user_id)

    def format_audio(self, audio):
        """Required by Sink.cleanup(). No-op since we process via harvest()."""
        pass

    def cleanup(self):
        with self._lock:
            self._buffers.clear()
            self._last_ts.clear()
            self._busy.clear()


class VoiceListener:
    """Discord voice → Ears STT → Butler/AI → Mouth TTS pipeline.

    Continuously records voice channel audio using _UtteranceSink.
    Polls for completed utterances (silence-delimited), sends WAV to Ears
    for transcription, then processes through Butler/AI and responds via TTS.
    """

    EARS_URL = "http://127.0.0.1:5000/transcribe"
    SILENCE_TIMEOUT = 0.8       # seconds of silence = utterance complete (WO 120)
    MIN_AUDIO_BYTES = 96000     # ~0.5s at 48kHz stereo 16-bit
    POLL_INTERVAL = 0.2         # check 5x/sec for low-latency response (WO 120)

    def __init__(self, bot: "CodexDiscordBot"):
        self.bot = bot
        self._active = False
        self._task: Optional[asyncio.Task] = None
        self._sink: Optional[_UtteranceSink] = None
        self._text_channel = None
        self._vc: Optional[discord.VoiceClient] = None

    async def start(self, voice_client: discord.VoiceClient, text_channel):
        """Begin listening on a voice connection."""
        self._vc = voice_client
        self._text_channel = text_channel
        self._active = True
        self._sink = _UtteranceSink()
        voice_client.start_recording(self._sink, self._on_stop, text_channel)
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("[EARS] Voice listener active — recording started")

    async def stop(self):
        """Stop listening and clean up."""
        self._active = False
        if self._task:
            self._task.cancel()
        if self._vc and self._vc.recording:
            try:
                self._vc.stop_recording()
            except Exception:
                pass
        self._sink = None
        logger.info("[EARS] Voice listener stopped")

    async def _on_stop(self, sink, channel, *args):
        """Callback when recording is externally stopped."""
        pass

    async def _poll_loop(self):
        """Periodically harvest completed utterances and process them."""
        while self._active:
            try:
                await asyncio.sleep(self.POLL_INTERVAL)
                if not self._sink:
                    continue
                completed = self._sink.harvest(
                    self.SILENCE_TIMEOUT, self.MIN_AUDIO_BYTES
                )
                for user_id, pcm_bytes in completed:
                    asyncio.create_task(self._process(user_id, pcm_bytes))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Voice poll error: {e}")

    async def _process(self, user_id: int, pcm_bytes: bytes):
        """Convert PCM → WAV, send to Ears, process through Butler/AI."""
        # Build WAV from raw PCM
        wav_buf = io.BytesIO()
        ch = self._sink._channels if self._sink else 2
        sw = self._sink._sample_width if self._sink else 2
        sr = self._sink._sample_rate if self._sink else 48000
        with wave.open(wav_buf, 'wb') as wf:
            wf.setnchannels(ch)
            wf.setsampwidth(sw)
            wf.setframerate(sr)
            wf.writeframes(pcm_bytes)
        wav_buf.seek(0)

        # Send to Ears service for transcription
        text = None
        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field(
                    'file', wav_buf,
                    filename='discord_voice.wav',
                    content_type='audio/wav'
                )
                async with session.post(
                    self.EARS_URL, data=form,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result.get('text', '').strip()
                    else:
                        logger.warning(f"[EARS] Transcription returned {resp.status}")
        except Exception as e:
            logger.error(f"[EARS] Transcription request failed: {e}")

        # Release user for next utterance
        if self._sink:
            self._sink.mark_done(user_id)

        if not text or len(text) < 2:
            return

        logger.info(f"[EARS] Transcription: {text}")

        # Wake word check
        text_lower = text.lower()
        cleaned = None
        for word in WAKE_WORDS:
            if word in text_lower:
                idx = text_lower.index(word) + len(word)
                cleaned = text[idx:].strip(' ,.:!?')
                break

        if cleaned is None:
            return  # No wake word — ignore

        if not cleaned:
            cleaned = "ping"  # Just the wake word alone

        # Butler reflex → AI fallback
        response = self.bot._butler.check_reflex(cleaned)
        if not response and self.bot.core:
            try:
                response = await self.bot.core.process_input(
                    str(user_id), cleaned
                )
            except Exception as e:
                logger.error(f"[EARS] AI processing failed: {e}")
                response = None

        if not response:
            return

        # Send text response to channel
        if self._text_channel:
            try:
                await self._text_channel.send(
                    f"\U0001f399\ufe0f *\"{text}\"*\n{response}"
                )
            except Exception:
                pass

        # Send voice response via TTS (WO-V13.1: VoiceBridge + cue parsing)
        if self._vc and self._vc.is_connected():
            voice_text = CodexButler.voice_clean(response)
            clean_text, cue = parse_voice_cue(voice_text)
            # Default to Narrator (Norse Skald voice) when no cue tagged
            if cue is None:
                cue = parse_voice_cue("[Narrator] x")[1]
            await self.bot.voice.speak_discord(clean_text, self._vc, voice_cue=cue)


# =============================================================================
# VOICE BRIDGE (TTS Output) — WO-V13.1
# =============================================================================

from codex.services.voice_bridge import VoiceBridge, parse_voice_cue, get_npc_speaker_id


# =============================================================================
# DISCORD BOT — Command Priority System
# =============================================================================

class CodexDiscordBot(commands.Bot):
    """
    C.O.D.E.X. Discord Bot with Command Priority.

    Priority Order:
    1. Guard Clauses (ignore bots)
    2. System Commands (!help, !menu, !status, !play, !travel, !clear)
    3. Wake Word Detection
    4. Game Session Logic (allegiance, votes)
    5. Mimir Chat (AI fallback)
    """

    # WO-V63.0: Admin-gated commands — only the DM can launch sessions,
    # use DM tools, or run system commands that hit Ollama/CPU.
    # Player-safe commands (help, status, ping, look, map, sheet) remain open.
    _ADMIN_COMMANDS = frozenset({
        "menu", "play", "burnwillow", "dnd5e", "cosmere", "crown",
        "prologue", "create", "dm", "clear", "stop", "fitd_status",
    })

    def __init__(self, core=None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.core = core  # CodexCore for AI chat
        self.voice = VoiceBridge()
        self.listener = VoiceListener(self)  # WO 115 — voice receive pipeline
        # WO 114 — Butler reflex router (instant pattern-matched responses)
        self._butler = getattr(core, 'butler', None) if core else None
        if not self._butler:
            self._butler = CodexButler()
        # WO 088 — expose architect as mimir for narrative generation
        global _mimir_ref
        _mimir_ref = getattr(core, 'architect', None) if core else None

        # WO-V63.0: Load admin ID from .env
        self._admin_id = int(os.environ.get("ADMIN_ID", "0"))

        # ─── Hotfix 117: Commands registered directly (no Cog) ───

        @self.command(name="help")
        async def cmd_help(ctx):
            """Display help text."""
            await ctx.send(HELP_TEXT)

        @self.command(name="menu", aliases=["play"])
        async def cmd_menu(ctx):
            """Display the main navigation menu."""
            session = get_session(ctx.channel.id)
            session.phase = Phase.MENU
            menu_def = _MENU.get_menu("discord")
            embed = discord.Embed(
                title=f"\U0001f4e1 {menu_def.title}",
                description="Select a module to begin.",
                color=0xFFD700
            )
            for opt in menu_def.options:
                suffix = " \u2014 *AI Required*" if opt.action == "launch_omni_forge" and not OMNI_FORGE_AVAILABLE else ""
                embed.add_field(
                    name=f"[{opt.key}] {opt.label}",
                    value=f"{opt.description}{suffix}",
                    inline=False
                )
            embed.set_footer(text=menu_def.footer)
            await ctx.send(embed=embed)

        @self.command(name="travel")
        async def cmd_travel(ctx):
            """Advance from morning phase."""
            session = get_session(ctx.channel.id)
            response = session.handle_travel()
            await ctx.send(response)

        @self.command(name="stop", aliases=["quit", "abort", "end"])
        async def cmd_stop(ctx):
            """End current session and return to idle."""
            session = get_session(ctx.channel.id)
            response = session.end_session()
            await ctx.send(response)

        @self.command(name="status")
        async def cmd_status(ctx):
            """Show system and session status using Discord Embed."""
            session = get_session(ctx.channel.id)
            if session.phase != Phase.IDLE and session.engine:
                # Crown & Crew session
                engine = session.engine
                tier = engine.get_tier()
                embed = discord.Embed(
                    title=f"\u2694\ufe0f DAY {engine.day}/{engine.arc_length} \u2014 {session.phase.name}",
                    description=engine.get_sway_visual(),
                    color=engine.get_sway_color()
                )
                embed.add_field(
                    name="Allegiance",
                    value=f"**{tier['name']}**\n_{tier['desc']}_",
                    inline=True
                )
                embed.add_field(
                    name="Dominant Trait",
                    value=f"\u25c8 {engine.get_dominant_tag()}",
                    inline=True
                )
                embed.add_field(
                    name="Sway",
                    value=f"`{engine.sway:+d}`",
                    inline=True
                )
                embed.set_footer(text=f"Patron: {engine.patron} \u2502 Leader: {engine.leader}")
            elif session.bridge and hasattr(getattr(session.bridge, 'engine', None), 'doom_clock'):
                # Burnwillow session (engine lives on the bridge)
                bw_engine = session.bridge.engine
                lead = None
                if hasattr(bw_engine, 'party') and bw_engine.party:
                    lead = bw_engine.party[0]
                elif hasattr(bw_engine, 'character') and bw_engine.character:
                    lead = bw_engine.character
                doom = bw_engine.doom_clock.current if bw_engine.doom_clock else 0
                if lead and BURNWILLOW_EMBEDS_AVAILABLE:
                    # WO-V35.0: Pass conditions for status effect display
                    cond_list = None
                    if session.conditions:
                        cond_list = session.conditions.get_conditions(lead.name)
                    embed_data = character_to_discord_embed_compact(lead, conditions=cond_list)
                    embed = discord.Embed.from_dict(embed_data)
                    embed.add_field(name="Doom", value=f"`{doom}/20`", inline=True)
                    embed.add_field(
                        name="Room",
                        value=f"`{bw_engine.current_room_id}`",
                        inline=True
                    )
                    # WO-V35.0: Active turn field
                    if session.active_turn:
                        embed.add_field(
                            name="\u2694\ufe0f Active Turn",
                            value=f"**{session.active_turn}**",
                            inline=True
                        )
                else:
                    party_size = len(bw_engine.party) if hasattr(bw_engine, 'party') else 1
                    embed = discord.Embed(
                        title="Burnwillow Session",
                        description=f"Party: {party_size} | Doom: {doom}/20",
                        color=0x2D5016
                    )
            else:
                embed = discord.Embed(
                    title="\U0001f4e1 SESSION STATUS",
                    description="No active campaign.\nUse `!play` to begin Crown & Crew.",
                    color=0x808080
                )
            if self.core:
                try:
                    state = self.core.cortex.read_metabolic_state()
                    vitals = f"\U0001f321\ufe0f {state.cpu_temp_celsius:.1f}\u00b0C \u2502 \U0001f4be {state.ram_available_gb:.1f}GB free"
                    embed.add_field(name="System Vitals", value=vitals, inline=False)
                except Exception:
                    pass
            await ctx.send(embed=embed)

        @self.command(name="clear")
        async def cmd_clear(ctx):
            """Clear session memory."""
            session = get_session(ctx.channel.id)
            if session.phase != Phase.IDLE:
                session.end_session()
            if self.core:
                user_session = self.core.get_session(str(ctx.author.id))
                user_session.conversation_history.clear()
                await ctx.send("\U0001f9f9 Session memory purged.")
            else:
                await ctx.send("\U0001f9f9 Session cleared.")

        @self.command(name="ping")
        async def cmd_ping(ctx):
            """Instant health check — bypasses all inference."""
            vitals = ""
            if self.core:
                try:
                    state = self.core.cortex.read_metabolic_state()
                    vitals = f" | Temp: {state.cpu_temp_celsius:.1f}\u00b0C"
                except Exception:
                    vitals = " | Temp: N/A"
            await ctx.send(f"**Pong!** Online{vitals}")

        @self.command(name="prologue")
        async def cmd_prologue(ctx):
            """Launch Crown & Crew from a saved campaign's prologue context."""
            pending = _scan_pending_prologues()
            if not pending:
                await ctx.send("No campaigns with a pending prologue.\nCreate one via the Campaign Wizard (terminal).")
                return
            manifest = pending[0]
            campaign_ctx = manifest.get('prologue_context', {})
            session = get_session(ctx.channel.id)
            if session.phase not in (Phase.IDLE, Phase.MENU):
                session.end_session()
            session.engine = CrownAndCrewEngine(campaign_context=campaign_ctx, mimir=session.mimir)
            session.phase = Phase.MORNING
            session.used_dilemmas = []
            world = session.engine.get_world_prompt()
            camp_name = manifest.get('campaign_name', 'Unknown')[:46]
            await ctx.send(f"""```
\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
\u2551              \U0001f4dc  PROLOGUE: SESSION ZERO  \U0001f4dc                 \u2551
\u2551  {camp_name:<54} \u2551
\u2560\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2563
\u2551  Patron: {session.engine.patron:<46} \u2551
\u2551  Leader: {session.engine.leader:<46} \u2551
\u2551  Goal:   {session.engine.goal:<46} \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
```
**\u2600\ufe0f MORNING \u2014 DAY {session.engine.day}**

_{world}_

Type `!travel` when ready.""")

        @self.command(name="burnwillow")
        async def cmd_burnwillow(ctx):
            """Start a Burnwillow dungeon run."""
            session = get_session(ctx.channel.id)
            if session.phase not in (Phase.IDLE, Phase.MENU):
                session.end_session()
            # Load saved character if available (stats + loadout from !create)
            char_file = _ROOT / "state" / "discord_characters" / f"{ctx.author.id}.json"
            player_name = "Adventurer"
            char_data = None
            if char_file.exists():
                try:
                    char_data = json.loads(char_file.read_text())
                    player_name = char_data.get("name", "Adventurer")
                    # Only use char_data if it was built for Burnwillow
                    if char_data.get("system") != "burnwillow":
                        char_data = None
                except (json.JSONDecodeError, KeyError):
                    char_data = None
            session.bridge = BurnwillowBridge(
                player_name=player_name, char_data=char_data)
            session.game_type = "burnwillow"
            session.phase = Phase.DUNGEON
            result = session.bridge.step('look')
            frame = getattr(session.bridge, 'last_frame', None)
            view = GameCommandView(session)
            await ctx.send(f"```\n{result}\n```", view=view)
            if frame:
                await _scry_embed_update(session, ctx.channel, frame, result)

        @self.command(name="dnd5e")
        async def cmd_dnd5e(ctx):
            """Start a D&D 5e dungeon run."""
            session = get_session(ctx.channel.id)
            if session.phase not in (Phase.IDLE, Phase.MENU):
                session.end_session()
            from codex.games.dnd5e import DnD5eEngine
            session.bridge = UniversalGameBridge(DnD5eEngine)
            session.game_type = "dnd5e"
            session.phase = Phase.DND5E
            result = session.bridge.step('look')
            frame = getattr(session.bridge, 'last_frame', None)
            view = GameCommandView(session)
            await ctx.send(f"```\n{result}\n```", view=view)
            if frame:
                await _scry_embed_update(session, ctx.channel, frame, result)

        @self.command(name="cosmere")
        async def cmd_cosmere(ctx):
            """Start a Cosmere (Stormlight) dungeon run."""
            session = get_session(ctx.channel.id)
            if session.phase not in (Phase.IDLE, Phase.MENU):
                session.end_session()
            from codex.games.stc import CosmereEngine
            session.bridge = UniversalGameBridge(CosmereEngine)
            session.game_type = "cosmere"
            session.phase = Phase.COSMERE
            result = session.bridge.step('look')
            frame = getattr(session.bridge, 'last_frame', None)
            view = GameCommandView(session)
            await ctx.send(f"```\n{result}\n```", view=view)
            if frame:
                await _scry_embed_update(session, ctx.channel, frame, result)

        @self.command(name="crown")
        async def cmd_crown(ctx):
            """Start a fresh Crown & Crew campaign (WO-V23.0)."""
            session = get_session(ctx.channel.id)
            if session.phase not in (Phase.IDLE, Phase.MENU):
                session.end_session()
            response = session.start_game()
            await ctx.send(response)

        @self.command(name="ashburn")
        async def cmd_ashburn(ctx):
            """Start an Ashburn High campaign (WO-V23.0)."""
            session = get_session(ctx.channel.id)
            if session.phase != Phase.IDLE:
                session.end_session()
            try:
                from codex.games.crown.ashburn import LEADERS
                session.phase = Phase.ASHBURN_HEIR
                julian = LEADERS["Julian"]
                rowan = LEADERS["Rowan"]
                await ctx.send(
                    f"**🥀 ASHBURN HIGH — CHOOSE YOUR HEIR**\n\n"
                    f"**[1] JULIAN** — _{julian['title']}_\n"
                    f"  Ability: {julian['ability']}\n"
                    f"  Risk: {julian['risk']}\n\n"
                    f"**[2] ROWAN** — _{rowan['title']}_\n"
                    f"  Ability: {rowan['ability']}\n"
                    f"  Risk: {rowan['risk']}\n\n"
                    f"Type `1` for Julian or `2` for Rowan."
                )
            except ImportError:
                await ctx.send("Ashburn High module not available.")

        @self.command(name="quest")
        async def cmd_quest(ctx):
            """Browse and select a quest archetype (WO-V23.0)."""
            session = get_session(ctx.channel.id)
            if session.phase not in (Phase.IDLE, Phase.MENU):
                session.end_session()
            try:
                from codex.games.crown.quests import list_quests
                quests = list_quests()
                if not quests:
                    await ctx.send("No quest archetypes available.")
                    return
                session.phase = Phase.QUEST_SELECT
                embed = discord.Embed(
                    title="⚔️ Quest Archetypes",
                    description="Select a scenario template.",
                    color=0xFFD700
                )
                for i, q in enumerate(quests, 1):
                    embed.add_field(
                        name=f"[{i}] {q.name} ({q.arc_length} days)",
                        value=q.description[:100] + "...",
                        inline=False
                    )
                embed.set_footer(text="Type a number to select.")
                await ctx.send(embed=embed)
            except ImportError:
                await ctx.send("Quest archetypes module not available.")

        @self.command(name="summon")
        async def cmd_summon(ctx):
            """Acknowledge summon."""
            await ctx.send("**Mimir has been summoned.** I am focusing on this channel.")

        @self.command(name="voice")
        async def cmd_voice(ctx, action: str = "join"):
            """Join or leave voice channel. Toggle TTS on/off."""
            if action == "join" and ctx.author.voice:
                vc = await ctx.author.voice.channel.connect()
                try:
                    await self.listener.start(vc, ctx.channel)
                    await ctx.send("\U0001f50a Voice uplink established. Ears listening.")
                except Exception as e:
                    logger.error(f"Voice listener start failed: {e}")
                    await ctx.send("\U0001f50a Voice uplink established. (Ears offline)")
            elif action == "leave" and ctx.voice_client:
                await self.listener.stop()
                await ctx.voice_client.disconnect()
                await ctx.send("\U0001f507 Voice uplink terminated.")
            elif action == "toggle":
                self.voice.enabled = not self.voice.enabled
                state = "ON" if self.voice.enabled else "OFF"
                await ctx.send(f"Voice narration: **{state}**")
            elif action == "on":
                self.voice.enabled = True
                await ctx.send("Voice narration: **ON**")
            elif action == "off":
                self.voice.enabled = False
                await ctx.send("Voice narration: **OFF**")
            else:
                await ctx.send("Usage: `!voice join|leave|toggle|on|off`")

        @self.command(name="sheet")
        async def cmd_sheet(ctx):
            """Show Burnwillow character sheet as a Discord embed."""
            if not BURNWILLOW_EMBEDS_AVAILABLE:
                await ctx.send("Character embed system not available.")
                return
            session = get_session(ctx.channel.id)
            bridge = session.bridge
            engine = getattr(bridge, 'engine', None)
            if engine is None:
                await ctx.send("No active Burnwillow character. Start a game with `!burnwillow`.")
                return
            # Party session: show compact embed per member (max 4)
            if hasattr(engine, 'party') and engine.party:
                for char in engine.party[:6]:
                    embed_data = character_to_discord_embed_compact(char)
                    embed = discord.Embed.from_dict(embed_data)
                    await ctx.send(embed=embed)
            # Single-character session: show full sheet
            elif hasattr(engine, 'character') and engine.character:
                embed_data = character_to_discord_embed(engine.character)
                embed = discord.Embed.from_dict(embed_data)
                await ctx.send(embed=embed)
            else:
                await ctx.send("No active Burnwillow character. Start a game with `!burnwillow`.")

        @self.command(name="init")
        async def cmd_init(ctx):
            """Show current initiative order (WO-V35.0)."""
            session = get_session(ctx.channel.id)
            if not session.initiative_order:
                await ctx.send("No initiative order active. The DM must run `init roll` on the dashboard.")
                return
            lines = [f"**Initiative Order** (Active: {session.active_turn or 'none'})"]
            for name in session.initiative_order:
                marker = "\u25b6\ufe0f" if name == session.active_turn else "\u25ab\ufe0f"
                lines.append(f"{marker} {name}")
            await ctx.send("\n".join(lines))

        @self.command(name="rest")
        async def cmd_rest(ctx, rest_type: str = "short"):
            """Player-initiated rest via bridge (WO-V35.0)."""
            session = get_session(ctx.channel.id)
            if not session.bridge:
                await ctx.send("No active session. Start a game first.")
                return
            result = session.bridge.step(f"rest {rest_type}")
            await ctx.send(f"```\n{result}\n```")

        @self.command(name="recap")
        async def cmd_recap(ctx):
            """Show session recap — kills, loot, rooms explored (WO-V37.0)."""
            session = get_session(ctx.channel.id)
            if not session.bridge:
                await ctx.send("No active session. Start a game first.")
                return
            # Use bridge recap if available (BurnwillowBridge)
            if hasattr(session.bridge, 'get_session_stats'):
                stats = session.bridge.get_session_stats()
                embed = discord.Embed(
                    title="Session Recap",
                    color=0xDAA520,
                )
                kill_info = stats.get("kills", {})
                tier_parts = ", ".join(
                    f"T{t}: {c}" for t, c in sorted(kill_info.get("by_tier", {}).items())
                )
                embed.add_field(
                    name="Enemies Slain",
                    value=f"{kill_info.get('total', 0)} ({tier_parts})" if tier_parts else str(kill_info.get("total", 0)),
                    inline=True,
                )
                embed.add_field(
                    name="Rooms",
                    value=f"Explored: {stats.get('rooms_explored', 0)} | Cleared: {stats.get('rooms_cleared', 0)}",
                    inline=True,
                )
                embed.add_field(
                    name="Doom",
                    value=f"{stats.get('doom', 0)}/20",
                    inline=True,
                )
                loot_list = stats.get("loot", [])
                if loot_list:
                    embed.add_field(
                        name="Loot",
                        value=", ".join(loot_list[:10]) + ("..." if len(loot_list) > 10 else ""),
                        inline=False,
                    )
                party = stats.get("party", [])
                if party:
                    party_lines = [f"{m['name']}: {m['hp']}/{m['max_hp']} HP" for m in party]
                    embed.add_field(
                        name="Party Status",
                        value="\n".join(party_lines),
                        inline=False,
                    )
                await ctx.send(embed=embed)
            else:
                # Fallback: use bridge step
                result = session.bridge.step("recap")
                await ctx.send(f"```\n{result}\n```")

        @self.command(name="atlas")
        async def cmd_atlas(ctx):
            """Show the active world's G.R.A.P.E.S. profile as a Discord embed."""
            worlds_dir = _ROOT / "worlds"
            if not worlds_dir.exists() or not list(worlds_dir.glob("*.json")):
                await ctx.send("No saved worlds found. Create one via the Genesis Wizard.")
                return
            # Load the most recently modified world
            world_files = sorted(worlds_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            try:
                data = json.loads(world_files[0].read_text())
            except (json.JSONDecodeError, IndexError):
                await ctx.send("Failed to read world data.")
                return

            grapes = data.get("grapes", {})
            world_name = data.get("name", "Unknown World")
            genre = data.get("genre", "")
            tone = data.get("tone", "")

            embed = discord.Embed(
                title=f"World Atlas: {world_name}",
                description=f"{genre} | {tone}",
                color=0xDAA520,
            )

            # Detect flat vs rich format
            sample = next(iter(grapes.values()), None) if grapes else None
            if isinstance(sample, list):
                # Rich format
                section_map = {
                    "geography": "Geography",
                    "religion": "Religion",
                    "arts": "Arts",
                    "politics": "Politics",
                    "economics": "Economics",
                    "social": "Social",
                    "language": "Language",
                    "culture": "Culture",
                    "architecture": "Architecture",
                }
                for key, label in section_map.items():
                    entries = grapes.get(key, [])
                    if entries and isinstance(entries, list):
                        lines = []
                        for entry in entries[:3]:
                            if isinstance(entry, dict):
                                first_val = next(iter(entry.values()), "?")
                                lines.append(str(first_val))
                        embed.add_field(name=label, value="\n".join(lines) or "---", inline=True)
            elif isinstance(sample, str):
                # Flat format
                for key in ("geography", "religion", "achievements", "politics", "economics", "social"):
                    val = grapes.get(key, "")
                    if val:
                        embed.add_field(name=key.title(), value=val[:100], inline=True)

            await ctx.send(embed=embed)

        @self.command(name="rumors")
        async def cmd_rumors(ctx):
            """Show G.R.A.P.E.S.-based world rumors from the active universe."""
            from codex.core.services.town_crier import CrierVoice

            worlds_dir = _ROOT / "worlds"
            if not worlds_dir.exists() or not list(worlds_dir.glob("*.json")):
                await ctx.send("No saved worlds found. Create one via the Genesis Wizard.")
                return
            world_files = sorted(
                worlds_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime, reverse=True,
            )
            try:
                data = json.loads(world_files[0].read_text())
            except (json.JSONDecodeError, IndexError):
                await ctx.send("Failed to read world data.")
                return

            grapes = data.get("grapes", {})
            if not grapes:
                await ctx.send("No G.R.A.P.E.S. data in this world.")
                return

            voice = CrierVoice(grapes_profile=grapes)
            rumors = voice.generate_grapes_rumors(limit=5)
            if not rumors:
                await ctx.send("The town crier has nothing to report.")
                return

            world_name = data.get("name", "Unknown World")
            embed = discord.Embed(
                title=f"Town Crier's Rumors — {world_name}",
                description="\n\n".join(f"- {r}" for r in rumors),
                color=0xCC8800,
            )
            await ctx.send(embed=embed)

        @self.command(name="chronology")
        async def cmd_chronology(ctx):
            """Show recent world chronology events as a Discord embed."""
            worlds_dir = _ROOT / "worlds"
            if not worlds_dir.exists() or not list(worlds_dir.glob("*.json")):
                await ctx.send("No saved worlds found. Create one via the Genesis Wizard.")
                return
            world_files = sorted(worlds_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            try:
                data = json.loads(world_files[0].read_text())
            except (json.JSONDecodeError, IndexError):
                await ctx.send("Failed to read world data.")
                return

            chronology = data.get("chronology", [])
            if not chronology:
                await ctx.send("No historical events recorded yet.")
                return

            world_name = data.get("name", "Unknown World")
            embed = discord.Embed(
                title=f"World Chronology — {world_name}",
                description="Recent historical events",
                color=0xB8860B,
            )

            auth_labels = {1: "Eyewitness", 2: "Chronicle", 3: "Legend"}
            for entry in chronology[-10:]:
                ts = str(entry.get("timestamp", ""))[:16].replace("T", " ")
                etype = str(entry.get("event_type", "?")).upper()
                summary = entry.get("summary", "?")
                auth = auth_labels.get(entry.get("authority_level", 2), "?")
                source = entry.get("source", "")
                embed.add_field(
                    name=f"[{etype}] {ts}",
                    value=f"{summary}\n*{auth}* | {source}",
                    inline=False,
                )

            await ctx.send(embed=embed)

        @self.command(name="dm")
        async def cmd_dm(ctx, *, args: str = ""):
            """DM Tools — dice, NPC, loot, trap, encounter generators."""
            try:
                from codex.core.dm_tools import (
                    roll_dice, generate_npc, generate_trap,
                    calculate_loot, generate_encounter, scan_vault,
                )
            except ImportError:
                await ctx.send("DM Tools module not available.")
                return

            parts = args.strip().split(None, 1)
            sub = parts[0].lower() if parts else "help"
            arg = parts[1].strip() if len(parts) > 1 else ""

            if sub in ("dice", "roll"):
                if not arg:
                    await ctx.send("Usage: `!dm dice 2d6+3`")
                    return
                total, msg = roll_dice(arg)
                embed = discord.Embed(
                    title="DM Dice Roll",
                    description=msg,
                    color=0x3498DB,
                )
                await ctx.send(embed=embed)

            elif sub == "npc":
                result = generate_npc(arg or "")
                embed = discord.Embed(
                    title="NPC Generator",
                    description=result,
                    color=0x2ECC71,
                )
                await ctx.send(embed=embed)

            elif sub == "loot":
                difficulty = arg or "medium"
                result = calculate_loot(difficulty)
                embed = discord.Embed(
                    title="Loot Generator",
                    description=result,
                    color=0xF1C40F,
                )
                await ctx.send(embed=embed)

            elif sub == "trap":
                difficulty = arg or "medium"
                result = generate_trap(difficulty)
                embed = discord.Embed(
                    title="Trap Generator",
                    description=result,
                    color=0xE74C3C,
                )
                await ctx.send(embed=embed)

            elif sub in ("encounter", "enc"):
                # Parse: !dm encounter [system] [tier]
                enc_parts = arg.split()
                system = enc_parts[0].upper() if enc_parts else "BURNWILLOW"
                tier = 1
                if len(enc_parts) > 1:
                    try:
                        tier = max(1, min(4, int(enc_parts[1])))
                    except ValueError:
                        pass
                result = generate_encounter(system, tier)
                embed = discord.Embed(
                    title="Encounter Generator",
                    description=result[:4000],
                    color=0xE67E22,
                )
                await ctx.send(embed=embed)

            elif sub == "scan":
                async with ctx.typing():
                    result = scan_vault()
                embed = discord.Embed(
                    title="Vault Scanner",
                    description=result,
                    color=0x9B59B6,
                )
                await ctx.send(embed=embed)

            else:
                embed = discord.Embed(
                    title="DM Tools",
                    description=(
                        "`!dm dice 2d6+3` — Roll dice\n"
                        "`!dm npc [archetype]` — Generate NPC\n"
                        "`!dm loot [easy/medium/hard]` — Generate loot\n"
                        "`!dm trap [easy/medium/hard]` — Generate trap\n"
                        "`!dm encounter [system] [tier]` — Generate encounter\n"
                        "`!dm scan` — Scan vault PDFs for tables"
                    ),
                    color=0x95A5A6,
                )
                await ctx.send(embed=embed)

        @self.command(name="monster")
        async def cmd_monster(ctx, *, name: str = ""):
            """Look up a Burnwillow creature by name."""
            if not name:
                await ctx.send("Usage: `!monster <creature name>`")
                return
            try:
                from codex.games.burnwillow.content import lookup_creature
                result = lookup_creature(name)
            except ImportError:
                result = None
            if result:
                embed = discord.Embed(title="Bestiary", description=result, color=0x8B0000)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"No creature found matching '{name}'.")

        @self.command(name="create")
        async def cmd_create(ctx):
            """Start character creation for Discord."""
            view = CharacterCreationView(ctx.author.id, ctx.channel)
            embed = discord.Embed(
                title="Character Creation",
                description="Let's build your character! Enter a name to begin.",
                color=0x3498DB,
            )
            embed.add_field(
                name="Step 1: Name",
                value="Type your character's name in chat.",
            )
            await ctx.send(embed=embed, view=view)

        @self.command(name="map")
        async def cmd_map(ctx):
            """Render and send the current spatial map as PNG."""
            session = get_session(ctx.channel.id)
            bridge = getattr(session, 'bridge', None)
            if not bridge:
                await ctx.send("No active game session. Start one with `!burnwillow`, `!dnd5e`, or `!cosmere`.")
                return
            frame = getattr(bridge, 'last_frame', None)
            if frame:
                await _try_scry_and_send(ctx.channel, frame, "Map rendering failed.")
            else:
                # Try to get a minimap from bridge step
                result = bridge.step("map")
                await ctx.send(f"```\n{result}\n```")

        @self.command(name="fitd_status")
        async def cmd_fitd_status(ctx):
            """Show FITD orchestrator status for the current session."""
            session = get_session(ctx.channel.id)
            bridge = getattr(session, 'bridge', None)
            engine = getattr(bridge, 'engine', None) if bridge else None
            if engine and hasattr(engine, 'system_family') and engine.system_family == 'FITD':
                status = engine.get_status()
                lines = [f"**{engine.display_name}** — Session Status"]
                for k, v in status.items():
                    lines.append(f"  {k}: {v}")
                await ctx.send("\n".join(lines))
            else:
                await ctx.send("No active FITD session.")

    async def on_command_error(self, ctx, error):
        """WO-V9.4: Reroute unknown !commands to active session bridge.

        If a user types ``!loot`` or ``!search`` during an active dungeon
        session, the command framework raises CommandNotFound.  Instead of
        printing a stack trace, strip the ``!`` and forward to bridge.step().
        """
        if isinstance(error, commands.CommandNotFound):
            session = get_session(ctx.channel.id)
            if (
                session.phase in (Phase.DUNGEON, Phase.DND5E, Phase.COSMERE)
                and session.bridge
            ):
                # Strip the "!" prefix and forward to bridge
                raw = ctx.message.content.lstrip("!").strip().lower()
                if raw:
                    result = session.bridge.step(raw)
                    frame = getattr(session.bridge, 'last_frame', None)
                    await ctx.send(f"```\n{result}\n```")
                    if frame:
                        await _scry_embed_update(
                            session, ctx.channel, frame, result)
                    if session.bridge.dead:
                        session.end_session()
                return
            # Silently ignore unknown commands outside active sessions
            return
        # Let other errors propagate to default handler
        raise error

    async def on_ready(self):
        """Called when bot connects."""
        # WO 118 — Force-load opus for voice receive on aarch64
        if not discord.opus.is_loaded():
            try:
                discord.opus.load_opus(_OPUS_PATH)
                logger.info(f"Opus loaded from {_OPUS_PATH}")
            except Exception as e:
                logger.warning(f"Opus load failed: {e}")
        # WO-V9.4: Post-load verification
        if discord.opus.is_loaded():
            logger.info("Opus codec: VERIFIED")
        else:
            logger.warning("Opus codec: NOT LOADED — voice receive will fail")
        logger.info(f"Discord connected as {self.user}")
        print(f"[DISCORD] Connected as {self.user}")

        # WO-V8.1: Subscribe to faction clock tick bulletins
        try:
            from codex.core.services.broadcast import GlobalBroadcastManager
            from codex.core.services.town_crier import CrierVoice, EVENT_FACTION_CLOCK_TICK

            broadcaster = getattr(self.core, 'broadcaster', None) if self.core else None
            if broadcaster and isinstance(broadcaster, GlobalBroadcastManager):
                _voice = CrierVoice()

                async def _on_faction_tick(payload):
                    bulletin = _voice.narrate_bulletin(payload)
                    # Send to all active game channels
                    for ch_id, sess in sessions.items():
                        if sess.phase != Phase.IDLE:
                            ch = self.get_channel(ch_id)
                            if ch:
                                try:
                                    embed = discord.Embed(
                                        title="Faction Bulletin",
                                        description=bulletin,
                                        color=0xFF4444,
                                    )
                                    await ch.send(embed=embed)
                                except Exception:
                                    pass
                    # WO-V9.0 / V13.1: Voice broadcast with cue parsing
                    if self.voice_clients:
                        voice_text = CodexButler.voice_clean(bulletin)
                        clean_text, cue = parse_voice_cue(voice_text)
                        # Default broadcasts to Narrator (Norse Skald voice)
                        if cue is None:
                            cue = parse_voice_cue("[Narrator] x")[1]
                        for vc in self.voice_clients:
                            if vc.is_connected():
                                try:
                                    await self.voice.speak_discord(
                                        clean_text, vc, voice_cue=cue)
                                except Exception:
                                    pass

                def _sync_handler(payload):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_on_faction_tick(payload))
                    except RuntimeError:
                        pass

                broadcaster.subscribe(EVENT_FACTION_CLOCK_TICK, _sync_handler)
                logger.info("[WO-V8.1] Subscribed to FACTION_CLOCK_TICK bulletins")

                # Batch 005: Subscribe to MAP_UPDATE for cross-interface sync
                async def _on_map_update(payload):
                    system_id = payload.get("system_id", "unknown")
                    room_id = payload.get("room_id", "?")
                    for ch_id, sess in sessions.items():
                        if sess.phase != Phase.IDLE and sess.bridge:
                            frame = getattr(sess.bridge, 'last_frame', None)
                            if frame:
                                ch = self.get_channel(ch_id)
                                if ch:
                                    try:
                                        await _scry_embed_update(
                                            sess, ch, frame,
                                            f"[{system_id}] Room {room_id}")
                                    except Exception:
                                        pass

                def _map_sync_handler(payload):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_on_map_update(payload))
                    except RuntimeError:
                        pass

                broadcaster.subscribe("MAP_UPDATE", _map_sync_handler)
                logger.info("[Batch 005] Subscribed to MAP_UPDATE broadcasts")

                # WO-V35.0: Subscribe to INITIATIVE_ADVANCE
                async def _on_initiative_advance(payload):
                    name = payload.get("name", "?")
                    order = payload.get("order", [])
                    is_player = payload.get("is_player", False)
                    rnd = payload.get("round", 1)
                    for ch_id, sess in sessions.items():
                        if sess.phase != Phase.IDLE:
                            sess.initiative_order = order
                            sess.active_turn = name
                            if is_player:
                                ch = self.get_channel(ch_id)
                                if ch:
                                    try:
                                        await ch.send(
                                            f"\u2694\ufe0f **{name}'s Turn** (Round {rnd})")
                                    except Exception:
                                        pass

                def _init_sync_handler(payload):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_on_initiative_advance(payload))
                    except RuntimeError:
                        pass

                broadcaster.subscribe("INITIATIVE_ADVANCE", _init_sync_handler)
                logger.info("[WO-V35.0] Subscribed to INITIATIVE_ADVANCE broadcasts")

                # WO-V35.0: Subscribe to CONDITION_CHANGE
                async def _on_condition_change(payload):
                    entity = payload.get("entity", "?")
                    action = payload.get("action", "?")
                    ctype = payload.get("condition_type", "?")
                    for ch_id, sess in sessions.items():
                        if sess.phase != Phase.IDLE:
                            # Lazily create tracker if needed
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
                logger.info("[WO-V35.0] Subscribed to CONDITION_CHANGE broadcasts")

                # WO-V37.0: Subscribe to SESSION_RECAP
                async def _on_session_recap(payload):
                    narrative = payload.get("narrative", "")
                    system_id = payload.get("system_id", "unknown")
                    if not narrative:
                        return
                    for ch_id, sess in sessions.items():
                        if sess.phase != Phase.IDLE:
                            ch = self.get_channel(ch_id)
                            if ch:
                                try:
                                    await ch.send(f"```\n{narrative}\n```")
                                except Exception:
                                    pass

                def _recap_sync_handler(payload):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_on_session_recap(payload))
                    except RuntimeError:
                        pass

                broadcaster.subscribe("SESSION_RECAP", _recap_sync_handler)
                logger.info("[WO-V37.0] Subscribed to SESSION_RECAP broadcasts")

                # WO-V40.0: Subscribe to zone transition events
                async def _on_zone_transition(payload):
                    module = payload.get("module", "")
                    chapter = payload.get("chapter", "")
                    zone = payload.get("zone", "")
                    progress = payload.get("progress", "")
                    for ch_id, sess in sessions.items():
                        if sess.phase != Phase.IDLE:
                            ch = self.get_channel(ch_id)
                            if ch:
                                try:
                                    embed = discord.Embed(
                                        title="Zone Transition",
                                        description=(
                                            f"**{module}**\n"
                                            f"{chapter} — {zone}\n"
                                            f"_{progress}_"
                                        ),
                                        color=0x44AAFF,
                                    )
                                    await ch.send(embed=embed)
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
                logger.info("[WO-V40.0] Subscribed to ZONE_TRANSITION/COMPLETE broadcasts")

        except Exception as e:
            logger.debug(f"[WO-V8.1] Faction bulletin subscription skipped: {e}")

        if not self.thermal_monitor.is_running():
            self.thermal_monitor.start()

    @tasks.loop(seconds=30.0)
    async def thermal_monitor(self):
        """Update presence with thermal status."""
        if self.core:
            try:
                state = self.core.cortex.read_metabolic_state()
                await self.change_presence(activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"Temp: {state.cpu_temp_celsius:.0f}°C"
                ))
            except:
                pass

    async def on_message(self, message):
        """
        Message handler with Command Priority System.
        """
        # ─────────────────────────────────────────────────────────────────────
        # PRIORITY 0: Self-loop guard (WO 118 — ignore own transcriptions)
        # ─────────────────────────────────────────────────────────────────────
        if message.author == self.user:
            return

        # ─────────────────────────────────────────────────────────────────────
        # PRIORITY 1: Guard Clauses
        # ─────────────────────────────────────────────────────────────────────
        if message.author.bot:
            return

        # ─────────────────────────────────────────────────────────────────────
        # PRIORITY 1.5: Character creation name input
        # ─────────────────────────────────────────────────────────────────────
        uid = message.author.id
        if uid in _pending_name_input:
            pending = _pending_name_input[uid]
            if message.channel.id == pending["channel_id"]:
                del _pending_name_input[uid]
                name = message.content.strip()[:30]
                if not name or name.startswith("!"):
                    name = f"Hero_{uid % 10000}"
                pending["char_data"]["name"] = name
                view = BurnwillowStatAllocView(
                    uid, message.channel, pending["char_data"])
                embed = view._build_embed()
                await message.channel.send(embed=embed, view=view)
                return

        # ─────────────────────────────────────────────────────────────────────
        # PRIORITY 2: System Commands (process_commands handles these)
        # ─────────────────────────────────────────────────────────────────────
        # WO-V63.0: Block admin-only commands from non-DM users
        if message.content.startswith("!"):
            cmd_name = message.content[1:].split()[0].lower() if len(message.content) > 1 else ""
            if cmd_name in self._ADMIN_COMMANDS and message.author.id != self._admin_id:
                await message.reply("Only the DM can use that command.", mention_author=False)
                return

        await self.process_commands(message)

        # If it was a command, don't continue
        if message.content.startswith("!"):
            return

        # ─────────────────────────────────────────────────────────────────────
        # PRIORITY 3: Wake Word Detection (substring match, same as VoiceListener)
        # ─────────────────────────────────────────────────────────────────────
        cleaned_wake_word_content = None
        text_lower = message.content.lower()
        for word in WAKE_WORDS:
            if word in text_lower:
                idx = text_lower.index(word) + len(word)
                cleaned_wake_word_content = message.content[idx:].strip(' ,.:!?')
                break

        if cleaned_wake_word_content:
            async with message.channel.typing():
                try:
                    # WO 114 — Butler reflex first (instant, no AI)
                    response = self._butler.check_reflex(cleaned_wake_word_content)

                    # Fall through to AI if Butler didn't handle it
                    if not response and self.core:
                        response = await self.core.process_input(str(message.author.id), cleaned_wake_word_content)

                    if not response:
                        return

                    # Chunk long responses
                    if len(response) > 2000:
                        for chunk in [response[i:i+1990] for i in range(0, len(response), 1990)]:
                            await message.reply(chunk, mention_author=False)
                    else:
                        await message.reply(response, mention_author=False)

                    # Voice — WO-V13.1: VoiceBridge + cue parsing
                    if message.author.voice and message.author.voice.channel:
                        if not self.voice_clients:
                            await message.author.voice.channel.connect()
                        voice_text = CodexButler.voice_clean(response)
                        clean_text, cue = parse_voice_cue(voice_text)
                        # Default Mimir responses to Narrator (Norse Skald voice)
                        if cue is None:
                            cue = parse_voice_cue("[Narrator] " + clean_text)[1]
                        await self.voice.speak_discord(
                            clean_text, self.voice_clients[0], voice_cue=cue)
                except Exception as e:
                    await message.reply(f"[Error] {e}", mention_author=False)
            return


        # ─────────────────────────────────────────────────────────────────────
        # PRIORITY 4: Game Session Logic
        # ─────────────────────────────────────────────────────────────────────
        session = get_session(message.channel.id)
        text = message.content.lower().strip()

        # Dungeon session (Burnwillow / DnD5e / Cosmere free-text input)
        if session.phase in (Phase.DUNGEON, Phase.DND5E, Phase.COSMERE):
            if not session.bridge:
                await message.channel.send(
                    "Session error: bridge lost. Use `!stop` to reset.")
                session.end_session()
            else:
                result = session.bridge.step(text)
                frame = getattr(session.bridge, 'last_frame', None)
                await _scry_embed_update(session, message.channel, frame, result)
                # Phase G1: Write frame to player_frame.json for play_player_view.py
                if frame:
                    try:
                        _write_player_frame(frame)
                    except Exception:
                        pass
                if session.bridge.dead:
                    session.end_session()
            return

        # Menu selection (WO 109 — data-driven via CodexMenu)
        if session.phase == Phase.MENU:
            action = _MENU.resolve_selection("discord", text)
            if action:
                if action == "play_prologue":
                    pending = _scan_pending_prologues()
                    if not pending:
                        await message.channel.send("No campaigns with a pending prologue.\nCreate one via the Campaign Wizard (terminal).")
                    else:
                        manifest = pending[0]
                        ctx_data = manifest.get('prologue_context', {})
                        session.engine = CrownAndCrewEngine(campaign_context=ctx_data, mimir=session.mimir)
                        session.phase = Phase.MORNING
                        world = session.engine.get_world_prompt()
                        camp_name = manifest.get('campaign_name', 'Unknown')[:46]
                        await message.channel.send(f"""```
╔════════════════════════════════════════════════════════════╗
║              📜  PROLOGUE: SESSION ZERO  📜                 ║
║  {camp_name:<54} ║
╠════════════════════════════════════════════════════════════╣
║  Patron: {session.engine.patron:<46} ║
║  Leader: {session.engine.leader:<46} ║
║  Goal:   {session.engine.goal:<46} ║
╚════════════════════════════════════════════════════════════╝
```
**☀️ MORNING — DAY {session.engine.day}**

_{world}_

Type `!travel` when ready.""")
                elif action == "play_burnwillow":
                    session.bridge = BurnwillowBridge()
                    session.game_type = "burnwillow"
                    session.phase = Phase.DUNGEON
                    result = session.bridge.step('look')
                    frame = getattr(session.bridge, 'last_frame', None)
                    view = GameCommandView(session)
                    await message.channel.send(f"```\n{result}\n```", view=view)
                    if frame:
                        await _scry_embed_update(session, message.channel, frame, result)
                elif action == "play_dnd5e":
                    from codex.games.dnd5e import DnD5eEngine
                    session.bridge = UniversalGameBridge(DnD5eEngine)
                    session.game_type = "dnd5e"
                    session.phase = Phase.DND5E
                    result = session.bridge.step('look')
                    frame = getattr(session.bridge, 'last_frame', None)
                    view = GameCommandView(session)
                    await message.channel.send(f"```\n{result}\n```", view=view)
                    if frame:
                        await _scry_embed_update(session, message.channel, frame, result)
                elif action == "play_cosmere":
                    from codex.games.stc import CosmereEngine
                    session.bridge = UniversalGameBridge(CosmereEngine)
                    session.game_type = "cosmere"
                    session.phase = Phase.COSMERE
                    result = session.bridge.step('look')
                    frame = getattr(session.bridge, 'last_frame', None)
                    view = GameCommandView(session)
                    await message.channel.send(f"```\n{result}\n```", view=view)
                    if frame:
                        await _scry_embed_update(session, message.channel, frame, result)
                elif action == "launch_omni_forge":
                    if not OMNI_FORGE_AVAILABLE:
                        await message.channel.send("**Omni-Forge** module not available.")
                    else:
                        session.phase = Phase.OMNI
                        await message.channel.send(
                            "**🎲 THE OMNI-FORGE**\n\n"
                            "Type one of:\n"
                            "  `loot` — Quick Loot (Treasure Hoard)\n"
                            "  `lifepath` — Random Life Path\n"
                            "  `roll <table>` — Roll on a table\n"
                            "  `tables` — List available tables\n"
                            "  `back` — Return to menu"
                        )
                elif action == "play_crown":
                    # Fresh Crown & Crew campaign (WO-V23.0)
                    if session.phase not in (Phase.IDLE, Phase.MENU):
                        session.end_session()
                    response = session.start_game()
                    await message.channel.send(response)
                elif action == "play_quest":
                    # Quest archetype selection (WO-V23.0)
                    try:
                        from codex.games.crown.quests import list_quests
                        quests = list_quests()
                        if not quests:
                            await message.channel.send("No quest archetypes available.")
                        else:
                            session.phase = Phase.QUEST_SELECT
                            lines = ["**⚔️ QUEST ARCHETYPES**\n"]
                            for i, q in enumerate(quests, 1):
                                lines.append(f"**[{i}]** {q.name} ({q.arc_length} days)")
                                lines.append(f"  _{q.description[:80]}..._\n")
                            lines.append("Type a number to select.")
                            await message.channel.send("\n".join(lines))
                    except ImportError:
                        await message.channel.send("Quest archetypes module not available.")
                elif action == "play_ashburn":
                    # Ashburn High — heir selection (WO-V24.1)
                    try:
                        from codex.games.crown.ashburn import LEADERS
                        if session.phase != Phase.IDLE:
                            session.end_session()
                        session.phase = Phase.ASHBURN_HEIR
                        julian = LEADERS["Julian"]
                        rowan = LEADERS["Rowan"]
                        await message.channel.send(
                            f"**🥀 ASHBURN HIGH — CHOOSE YOUR HEIR**\n\n"
                            f"**[1] JULIAN** — _{julian['title']}_\n"
                            f"  Ability: {julian['ability']}\n"
                            f"  Risk: {julian['risk']}\n\n"
                            f"**[2] ROWAN** — _{rowan['title']}_\n"
                            f"  Ability: {rowan['ability']}\n"
                            f"  Risk: {rowan['risk']}\n\n"
                            f"Type `1` for Julian or `2` for Rowan."
                        )
                    except ImportError:
                        await message.channel.send("Ashburn High module not available.")
                elif action == "end_session":
                    response = session.end_session()
                    await message.channel.send(response)
                return

        # WO 089 / WO-V14.0 — Omni-Forge sub-menu handler (always handle OMNI phase)
        if session.phase == Phase.OMNI:
            if OMNI_FORGE_AVAILABLE:
                forge = OmniForge(self.core)  # core can be None for deterministic ops
                if text in ("back", "exit", "quit"):
                    session.phase = Phase.MENU
                    await message.channel.send("Returning to menu. Type `!menu` to see options.")
                elif text == "loot":
                    async with message.channel.typing():
                        result = await forge.quick_loot()
                    await message.channel.send(f"**🎲 LOOT**\n{result}")
                elif text.startswith("lifepath"):
                    async with message.channel.typing():
                        result = await forge.generate_lifepath()
                    await message.channel.send(f"**📜 LIFE PATH**\n{result[:1900]}")
                elif text == "tables":
                    tables = forge.list_tables()
                    await message.channel.send(
                        f"**Available Tables:** {', '.join(tables)}")
                elif text.startswith("roll"):
                    table_name = text[len("roll"):].strip().strip("<>") or "general"
                    async with message.channel.typing():
                        result = await forge.custom_query(table_name)
                    await message.channel.send(f"**🎲 TABLE ROLL**\n{result}")
                else:
                    await message.channel.send(
                        "Omni-Forge commands: `loot`, `lifepath`, `roll <table>`, `tables`, `back`"
                    )
            else:
                # Forge import failed — still handle the phase to avoid fallthrough
                if text in ("back", "exit", "quit"):
                    session.phase = Phase.MENU
                    await message.channel.send("Returning to menu.")
                else:
                    await message.channel.send(
                        "Omni-Forge is not available. Type `back` to return to menu.")
            return

        # Allegiance keywords
        if session.phase == Phase.NIGHT:
            if text in ("crown", "crew", "the crown", "the crew"):
                side = "crown" if "crown" in text else "crew"
                response = session.handle_allegiance(side)
                if response:
                    await message.channel.send(response)
                    return

        # Campfire done
        if session.phase == Phase.CAMPFIRE:
            if text in ("done", "continue", "next"):
                response = session.handle_campfire_done()
                if response:
                    await message.channel.send(response)
                    return

        # Council vote
        if session.phase == Phase.COUNCIL:
            if text in ("1", "2"):
                response = session.handle_vote(text)
                if response:
                    await message.channel.send(response)
                    return

        # WO-V23.0: Rest choice
        if session.phase == Phase.REST:
            if text in ("long", "short", "skip"):
                response = session.handle_rest(text)
                if response:
                    await message.channel.send(response)
                    return

        # WO-V24.1: Ashburn heir selection
        if session.phase == Phase.ASHBURN_HEIR:
            if text in ("1", "2"):
                try:
                    from codex.games.crown.ashburn import AshburnHeirEngine
                    heir_name = "Julian" if text == "1" else "Rowan"
                    session.engine = AshburnHeirEngine(heir_name=heir_name, mimir=session.mimir)
                    session.phase = Phase.MORNING
                    world = session.engine.get_world_prompt()
                    morning_event = session.engine.get_morning_event()
                    arc_days = f"{session.engine.arc_length} days"
                    await message.channel.send(
                        f"**🥀 {heir_name.upper()} — {session.engine.heir_leader['title']}**\n\n"
                        f"_{arc_days} of gothic corruption._\n\n"
                        f"**Patron:** {session.engine.patron}\n"
                        f"**Leader:** {session.engine.leader}\n\n"
                        f"**☀️ MORNING — DAY {session.engine.day}**\n\n"
                        f"_{world}_\n\n"
                        f"**THE ROAD AHEAD**\n"
                        f"_{morning_event['text']}_\n\n"
                        f"Type `!travel` when ready."
                    )
                except ImportError:
                    await message.channel.send("Ashburn High module not available.")
            else:
                await message.channel.send("Choose **1** for Julian or **2** for Rowan.")
            return

        # WO-V24.1: Ashburn legacy choice (Obey or Lie)
        if session.phase == Phase.ASHBURN_LEGACY:
            if text in ("1", "2"):
                result = await session.engine.resolve_legacy_choice(int(text))
                betrayal = session.engine.check_betrayal()
                if betrayal and betrayal.get("game_over"):
                    await message.channel.send(
                        f"_{result['consequence']}_\n\n"
                        f"_{result['narration']}_\n\n"
                        f"**💀 THE SOLARIUM OPENS**\n"
                        f"The glass shatters inward. You were never the heir — "
                        f"you were the inheritance.\n\n"
                        f"**ASHBURN CLAIMS ANOTHER.**\n\n"
                        f"_Corruption: {session.engine.legacy_corruption}/5_"
                    )
                    session.end_session()
                else:
                    # Continue to campfire or council
                    if session.engine.is_breach_day():
                        session.phase = Phase.COUNCIL
                        session._generate_dilemma()
                        next_phase = session._format_council()
                    else:
                        session.phase = Phase.CAMPFIRE
                        next_phase = session._format_campfire()
                    await message.channel.send(
                        f"_{result['consequence']}_\n\n"
                        f"_{result['narration']}_\n\n"
                        f"{next_phase}"
                    )
            else:
                await message.channel.send("Choose **1** (Obey) or **2** (Lie).")
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
                    # Bypass start_game() — it guards phase != IDLE (CB-02 fix)
                    world = session.engine.get_world_prompt()
                    morning_event = session.engine.get_morning_event()
                    event_text = morning_event["text"]
                    arc_days = f"{session.engine.arc_length} days"
                    response = f"""```
╔════════════════════════════════════════════════════════════╗
║                    ⚔️  {quest.name.upper():<33}  ║
║              {arc_days} to reach the border.{' ' * (34 - len(arc_days))}║
╠════════════════════════════════════════════════════════════╣
║  Patron: {session.engine.patron:<46} ║
║  Leader: {session.engine.leader:<46} ║
╠════════════════════════════════════════════════════════════╣
║  {session.engine.get_status():<54} ║
╚════════════════════════════════════════════════════════════╝
```
**☀️ MORNING — DAY {session.engine.day}**

_{world}_

**THE ROAD AHEAD**
_{event_text}_

Type `!travel` when ready to move on."""
                    await message.channel.send(response)
                else:
                    await message.channel.send(f"Select 1-{len(quests)}.")
            except (ValueError, ImportError):
                await message.channel.send("Enter a quest number.")
            return

        # ─────────────────────────────────────────────────────────────────────
        # PRIORITY 5: Mimir Chat (mention or DM)
        # ─────────────────────────────────────────────────────────────────────
        is_mentioned = self.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)

        if is_mentioned or is_dm:
            clean_content = re.sub(rf"<@!?{self.user.id}>", "", message.content).strip()
            if clean_content:
                async with message.channel.typing():
                    try:
                        # WO 114 — Butler reflex first (instant, no AI)
                        response = self._butler.check_reflex(clean_content)

                        # Fall through to AI if Butler didn't handle it
                        if not response and self.core:
                            response = await self.core.process_input(str(message.author.id), clean_content)

                        if not response:
                            return

                        # Chunk long responses
                        if len(response) > 2000:
                            for chunk in [response[i:i+1990] for i in range(0, len(response), 1990)]:
                                await message.reply(chunk, mention_author=False)
                        else:
                            await message.reply(response, mention_author=False)

                        # Voice — WO-V13.1: VoiceBridge + cue parsing
                        if message.author.voice and message.author.voice.channel:
                            if not self.voice_clients:
                                await message.author.voice.channel.connect()
                            voice_text = CodexButler.voice_clean(response)
                            clean_text, cue = parse_voice_cue(voice_text)
                            # Default to Narrator (Norse Skald voice)
                            if cue is None:
                                cue = parse_voice_cue("[Narrator] x")[1]
                            await self.voice.speak_discord(
                                clean_text, self.voice_clients[0], voice_cue=cue)

                    except Exception as e:
                        await message.reply(f"[Error] {e}", mention_author=False)


# =============================================================================
# STANDALONE RUNNER
# =============================================================================

async def run_discord_bot(core=None):
    """
    Standalone async entry point for the Discord bot.

    This function blocks until the bot disconnects, so it is NOT suitable
    for embedding inside codex_agent_main.py alongside other concurrent
    tasks (terminal loop, health monitor, Telegram bot, etc.).

    codex_agent_main.py constructs CodexDiscordBot directly and wraps
    bot.start() in asyncio.create_task() so it can wire the bot instance
    into the health monitor before the coroutine begins.  Use this helper
    only when running the Discord bot in isolation (e.g. for testing or a
    dedicated bot-only deployment).
    """
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.warning("DISCORD_TOKEN not found. Discord bot disabled.")
        return

    bot = CodexDiscordBot(core=core)
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Discord bot error: {e}")


def main():
    """Standalone entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    print("📡 Starting C.O.D.E.X. Discord Bot (Standalone Mode)...")

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found in .env")
        return

    bot = CodexDiscordBot()
    print("✅ Bot configured. Connecting...")
    bot.run(token)


if __name__ == "__main__":
    main()

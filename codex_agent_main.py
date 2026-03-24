#!/usr/bin/env python3
"""
codex_agent_main.py - THE UNIFIED ORCHESTRATOR
===============================================

The single entry point for C.O.D.E.X. Combines:
- Rich terminal UI (Fantasy RPG aesthetic)
- Discord Bot (Online Mode)
- Telegram Bot (Mirror Protocol)
- Crown & Crew narrative engine
- Mimir AI chat interface

C.O.D.E.X. - Chronicles of Destiny: Endless Crossroads

Version: 3.0 (Grand Unification)
"""

import asyncio
import json
import logging
import os
import re
import socket
import subprocess
import sys
import tempfile
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Rich console for visual UI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
# Note: Prompt/Confirm removed - using async ainput() instead
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich.align import Align
from rich import box
# rich.prompt.Prompt removed — using async ainput() instead

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Crown & Crew Engine
from codex.games.crown.engine import CrownAndCrewEngine

# Ashburn Heir Engine (Gothic Corruption Variant)
try:
    from codex.games.crown.ashburn import AshburnHeirEngine, LEADERS as ASHBURN_LEADERS
    ASHBURN_AVAILABLE = True
except ImportError:
    ASHBURN_AVAILABLE = False
    AshburnHeirEngine = None  # type: ignore[assignment]
    ASHBURN_LEADERS = None  # type: ignore[assignment]

# Ashburn Tarot Card System
try:
    from codex.integrations.tarot import render_tarot_card, get_card_for_context
    TAROT_AVAILABLE = True
except ImportError:
    TAROT_AVAILABLE = False
    render_tarot_card = None  # type: ignore[assignment]
    get_card_for_context = None  # type: ignore[assignment]

# World Engine (Genesis Module)
from codex.world.world_wizard import WorldEngine, WorldState, get_world_engine

# Telegram Bot (Mirror Protocol)
try:
    from codex.bots.telegram_bot import run_telegram_bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    run_telegram_bot = None  # type: ignore[assignment]

# Discord Bot (Command Priority System)
try:
    from codex.bots.discord_bot import CodexDiscordBot
    DISCORD_BOT_AVAILABLE = True
except ImportError:
    DISCORD_BOT_AVAILABLE = False
    CodexDiscordBot = None  # type: ignore[assignment]

# Try to import GenesisEngine (instant random world generator)
try:
    from codex.world.genesis import GenesisEngine
    GENESIS_AVAILABLE = True
except ImportError:
    GENESIS_AVAILABLE = False

# Character Forge (Vault-based character builder)
try:
    from codex.forge.char_wizard import (
        main as run_character_forge,
        CharacterBuilderEngine,
        SystemBuilder,
        render_character,
    )
    from codex.forge.source_scanner import scan_system_content
    FORGE_AVAILABLE = True
except ImportError:
    FORGE_AVAILABLE = False
    run_character_forge = None  # type: ignore[assignment]
    CharacterBuilderEngine = None  # type: ignore[assignment]
    SystemBuilder = None  # type: ignore[assignment]
    render_character = None  # type: ignore[assignment]
    scan_system_content = None  # type: ignore[assignment]

# Burnwillow Game (Roguelike dungeon crawler)
try:
    from play_burnwillow import main as run_burnwillow_game
    BURNWILLOW_AVAILABLE = True
except ImportError:
    BURNWILLOW_AVAILABLE = False
    run_burnwillow_game = None  # type: ignore[assignment]

# Universal Game Loop (FITD + Dungeon engines)
try:
    from play_universal import main as run_universal_game
    from play_universal import _ensure_engines_registered
    from codex.core.engine_protocol import ENGINE_REGISTRY
    _ensure_engines_registered()
    UNIVERSAL_AVAILABLE = True
except ImportError:
    UNIVERSAL_AVAILABLE = False
    run_universal_game = None  # type: ignore[assignment]
    ENGINE_REGISTRY = {}  # type: ignore[assignment]

# Librarian TUI (Mimir's Vault browser)
try:
    from codex.core.services.librarian import LibrarianTUI
    LIBRARIAN_AVAILABLE = True
except ImportError:
    LIBRARIAN_AVAILABLE = False
    LibrarianTUI = None  # type: ignore[assignment]

# Universe Manager (Star Chart & World Registry)
try:
    from codex.core.services.universe_manager import UniverseManager
    UNIVERSE_MANAGER_AVAILABLE = True
except ImportError:
    UNIVERSE_MANAGER_AVAILABLE = False
    UniverseManager = None  # type: ignore[assignment]

# Butler Protocol (Low-Latency Reflex Router)
try:
    from codex.core.butler import CodexButler
    BUTLER_AVAILABLE = True
except ImportError:
    BUTLER_AVAILABLE = False
    CodexButler = None  # type: ignore[assignment]


# Character Adapter (WO 103 — Wizard-to-Engine bridge)
try:
    from codex.forge.adapter import CharacterAdapter
    ADAPTER_AVAILABLE = True
except ImportError:
    ADAPTER_AVAILABLE = False
    CharacterAdapter = None  # type: ignore[assignment]

try:
    from codex.core.services.broadcast import GlobalBroadcastManager
    BROADCAST_AVAILABLE = True
except ImportError:
    BROADCAST_AVAILABLE = False
    GlobalBroadcastManager = None  # type: ignore[assignment]

try:
    from codex.core.memory import CodexMemoryEngine
    MEMORY_ENGINE_AVAILABLE = True
except ImportError:
    MEMORY_ENGINE_AVAILABLE = False
    CodexMemoryEngine = None  # type: ignore[assignment]

try:
    from codex.core.services.trait_handler import TraitHandler
    TRAIT_HANDLER_AVAILABLE = True
except ImportError:
    TRAIT_HANDLER_AVAILABLE = False
    TraitHandler = None  # type: ignore[assignment]

# Unified Menu Controller (WO 109)
from codex.core.menu import CodexMenu

# Define base directory for relative paths
CODEX_DIR = Path(__file__).resolve().parent

# Core system modules
from codex.core.cortex import (
    get_cortex,
    Cortex,
    ThermalStatus,
    MetabolicState,
)
from codex.core.architect import (
    get_architect,
    Architect,
    ThinkingMode,
    RoutingDecision,
    Complexity,
)
from codex.core.manifold_guard import (
    ManifoldGuard,
    GuardVerdict
)

# DM Tools (restored from archived codex_tools as codex.core.dm_tools)
try:
    from codex.core import dm_tools
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    dm_tools = None  # type: ignore[assignment]

# Animated Dice Engine
try:
    from codex.core import dice as codex_dice_engine
    DICE_ENGINE_AVAILABLE = True
except ImportError:
    DICE_ENGINE_AVAILABLE = False
    codex_dice_engine = None  # type: ignore[assignment]

# Load environment variables from Codex directory
load_dotenv(CODEX_DIR / ".env")

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
logging.basicConfig(
    filename=str(CODEX_DIR / 'codex_system.log'),
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CODEX")

# =============================================================================
# RICH CONSOLE & COLOR SCHEME
# =============================================================================
console = Console()

# Fantasy RPG Color Palette
GOLD = "bold yellow"
CRIMSON = "bold red"
EMERALD = "bold green"
SILVER = "dim white"
ROYAL_BLUE = "bold blue"
PARCHMENT = "wheat1"
MAGENTA = "bold magenta"


# =============================================================================
# VIEW LAUNCHER (WO-V63.0) — Deferred, fire-and-forget lxterminal views
# =============================================================================
_views_launched = False


def _launch_views():
    """Spawn DM View in a separate lxterminal window.

    Called once when a game actually starts (not at boot), since the view
    polls state files that don't exist until a game is running.
    The main terminal IS the player view — no separate PlayerView needed.
    Fire-and-forget — lxterminal forks, so we can't track the PID.
    """
    global _views_launched
    if _views_launched or not os.environ.get("DISPLAY"):
        return
    _views_launched = True
    for name, script, title, geom in [
        ("DMView", "play_dm_view.py", "C.O.D.E.X. — DM Dashboard", "120x35"),
    ]:
        script_path = CODEX_DIR / script
        if not script_path.exists():
            continue
        inner_cmd = (
            f"cd {CODEX_DIR} && source venv/bin/activate && "
            f"python {script_path}"
        )
        try:
            subprocess.Popen([
                "lxterminal",
                f"--title={title}",
                f"--geometry={geom}",
                "-e", f"/bin/bash -c '{inner_cmd}'",
            ])
            console.print(f"[dim]{name}: LAUNCHED[/dim]")
        except FileNotFoundError:
            pass
        except Exception:
            pass


# ASCII Banner
TITLE_ART = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║    ███╗   ███╗██╗███╗   ███╗██╗██████╗                                ║
║    ████╗ ████║██║████╗ ████║██║██╔══██╗                               ║
║    ██╔████╔██║██║██╔████╔██║██║██████╔╝                               ║
║    ██║╚██╔╝██║██║██║╚██╔╝██║██║██╔══██╗                               ║
║    ██║ ╚═╝ ██║██║██║ ╚═╝ ██║██║██║  ██║                               ║
║    ╚═╝     ╚═╝╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝                               ║
║                                                                       ║
║           AND THE CODEX OF CHRONICLES                                 ║
║                                                                       ║
║            ~ Where all fates meet at the X. ~                        ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""

# Thread pool for non-blocking input
_input_executor = ThreadPoolExecutor(1, "AsyncInput")


async def ainput(prompt: str = "") -> str:
    """
    Non-blocking async input that allows background tasks to run.
    Uses a thread executor to avoid blocking the event loop.
    """
    if prompt:
        console.print(prompt, end="")
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(_input_executor, sys.stdin.readline)).strip()


async def aconfirm(prompt: str, default: bool = True) -> bool:
    """Non-blocking async confirmation prompt."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = await ainput(f"[gold1]{prompt}[/]{suffix}")
    if not response:
        return default
    return response.lower() in ('y', 'yes', 'true', '1')


# =============================================================================
# SESSION STATE
# =============================================================================
@dataclass
class SessionState:
    """Persistent state for a user session."""
    user_id: str
    conversation_history: list[dict]
    game_state: dict
    last_interaction: datetime


# =============================================================================
# CODEX CORE - THE BRAIN
# =============================================================================
class CodexCore:
    """
    The Brain - Interface Agnostic Logic.
    Handles the Cortex, Architect, and Manifold Guard.
    Can be driven by Discord, Terminal, Telegram, or API.
    """

    _CREATIVE_SIGNALS = {
        "as a", "roleplay", "pretend", "imagine", "in character",
        "trenchcoat", "in the voice of", "play as", "write a",
        "narrate", "tell me a story", "describe the scene",
        "what would", "if i were", "speak as", "how would",
    }

    def __init__(self):
        self.cortex: Cortex = get_cortex()
        self.architect: Architect = get_architect()
        self.guard: ManifoldGuard = ManifoldGuard(strict_mode=False)
        self.sessions: dict[str, SessionState] = {}

        # State persistence
        self.state_file = CODEX_DIR / "state" / "session_state.json"
        self.state_file.parent.mkdir(exist_ok=True)
        self.load_state()

    def _classify_query_for_model(self, query: str) -> tuple:
        """Route query to mimir (fast/short) or codex (creative/complex)."""
        q = query.strip().lower()
        words = len(query.split())
        for signal in self._CREATIVE_SIGNALS:
            if signal in q:
                return "codex", f"creative: '{signal}'"
        if words > 20:
            return "codex", f"long ({words} words)"
        return "mimir", "default persona"

    def get_session(self, user_id: str) -> SessionState:
        """Get or create a session for a user."""
        if user_id not in self.sessions:
            self.sessions[user_id] = SessionState(
                user_id=user_id,
                conversation_history=[],
                game_state={},
                last_interaction=datetime.now()
            )
        return self.sessions[user_id]

    async def process_input(self, user_id: str, content: str, game_state_update: dict = None) -> str:  # type: ignore[assignment]
        """Main logic pipeline: Input -> Architect -> Guard -> Output."""
        session = self.get_session(user_id)
        session.last_interaction = datetime.now()

        if game_state_update:
            session.game_state.update(game_state_update)

        if not content.strip():
            content = "Hello"

        # Model routing: creative/complex -> codex, simple -> mimir
        metabolic = self.cortex.read_metabolic_state()
        model_name, reason = self._classify_query_for_model(content)

        # Thermal gating: fall back to mimir if codex selected but Pi is hot
        if model_name == "codex" and not metabolic.metabolic_clearance:
            model_name = "mimir"
            reason = f"thermal fallback ({reason})"

        decision = RoutingDecision(
            mode=ThinkingMode.REFLEX,
            model=model_name,
            complexity=Complexity.LOW,
            thermal_status=metabolic.thermal_status,
            clearance_granted=metabolic.metabolic_clearance,
            reasoning=reason,
        )

        thermal_context = ""
        if decision.thermal_status == ThermalStatus.CRITICAL:
            thermal_context = "\n[I'm running very hot - output limited.]"
        elif decision.thermal_status == ThermalStatus.FATIGUED:
            thermal_context = "\n[Running warm.]"

        # WO-V33.0: RAG context enrichment
        rag_context = ""
        try:
            if BUTLER_AVAILABLE:
                from codex.core.services.rag_service import get_rag_service
                rag = get_rag_service()
                if rag.is_available:
                    result = rag.search(content, "dnd5e", k=3, token_budget=600)
                    if result:
                        rag_context = rag.format_context(result)
        except Exception:
            pass

        try:
            response = await self.architect.invoke_model(
                query=content,
                system_prompt=rag_context,
                decision=decision,
                conversation_history=session.conversation_history
            )

            if session.game_state:
                validation = self.guard.verify_conservation_of_identity(
                    response.content,
                    session.game_state
                )
                if validation.verdict == GuardVerdict.FAIL:
                    logger.warning(f"Guard Intervention: {validation.contradictions}")
                    response = await self.architect.invoke_model(
                        query=content + "\n\n" + (validation.correction_instruction or ""),
                        system_prompt="",
                        decision=decision,
                        conversation_history=session.conversation_history
                    )

            session.conversation_history.append({"role": "user", "content": content})
            session.conversation_history.append({"role": "assistant", "content": response.content})

            if len(session.conversation_history) > 10:
                session.conversation_history = session.conversation_history[-10:]

            return response.content.strip() + thermal_context

        except Exception as e:
            logger.error(f"Core Processing Error: {e}")
            return f"[System Error] The Weave is disrupted: {e}"

    def get_status_report(self) -> str:
        return self.cortex.get_status_report()

    def load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                for uid, sdata in data.items():
                    self.sessions[uid] = SessionState(
                        user_id=uid,
                        conversation_history=sdata.get("conversation_history", []),
                        game_state=sdata.get("game_state", {}),
                        last_interaction=datetime.now()
                    )
            except Exception as e:
                logger.error(f"State load error: {e}")

    def save_state(self):
        try:
            data = {
                uid: {
                    "conversation_history": s.conversation_history,
                    "game_state": s.game_state
                }
                for uid, s in self.sessions.items()
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"State save error: {e}")

    async def close(self):
        self.save_state()
        await self.architect.close()


# =============================================================================
# GAME SAVE SYSTEM
# =============================================================================
class GameSave:
    """Represents a saved campaign."""

    SAVE_DIR = CODEX_DIR / "saves"

    def __init__(self, name: str, world: str, level: int, created: datetime):
        self.name = name
        self.world = world
        self.level = level
        self.created = created
        self.playtime_hours = 0
        self.state = {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "world": self.world,
            "level": self.level,
            "created": self.created.isoformat(),
            "playtime_hours": self.playtime_hours,
            "state": self.state
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameSave":
        save = cls(
            name=data["name"],
            world=data["world"],
            level=data["level"],
            created=datetime.fromisoformat(data["created"])
        )
        save.playtime_hours = data.get("playtime_hours", 0)
        save.state = data.get("state", {})
        return save

    def save(self):
        self.SAVE_DIR.mkdir(exist_ok=True)
        save_path = self.SAVE_DIR / f"{self.name}.json"
        with open(save_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def list_saves(cls) -> list["GameSave"]:
        saves = []
        seen_names = set()
        if cls.SAVE_DIR.exists():
            # WO 103: Scan campaign directories first (saves/*/campaign.json)
            for campaign_dir in cls.SAVE_DIR.iterdir():
                if not campaign_dir.is_dir():
                    continue
                manifest_path = campaign_dir / "campaign.json"
                if not manifest_path.exists():
                    continue
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    campaign_name = manifest.get("campaign_name", campaign_dir.name)
                    system_name = manifest.get("system_name", "Unknown")
                    num_players = manifest.get("num_players", 1)
                    created_str = manifest.get("created", datetime.now().isoformat())
                    save = cls(
                        name=campaign_name,
                        world=system_name,
                        level=num_players,
                        created=datetime.fromisoformat(created_str),
                    )
                    save.state = manifest  # Store full manifest for load
                    saves.append(save)
                    seen_names.add(campaign_name)
                except Exception:
                    pass

            # Flat JSON saves (legacy)
            for save_file in cls.SAVE_DIR.glob("*.json"):
                try:
                    with open(save_file) as f:
                        data = json.load(f)
                    save = cls.from_dict(data)
                    if save.name not in seen_names:
                        saves.append(save)
                        seen_names.add(save.name)
                except Exception:
                    pass
        return sorted(saves, key=lambda s: s.created, reverse=True)


# =============================================================================
# BOOT SEQUENCE - VISUAL STARTUP
# =============================================================================
async def boot_sequence(cortex: Cortex):
    """Display the visual boot sequence with progress animation."""
    console.clear()
    console.print(Text(TITLE_ART, style=GOLD))

    console.print()

    # Boot stages with progress
    stages = [
        ("Neural Core", "Initializing consciousness matrix..."),
        ("Cortex Link", "Establishing hardware bridge..."),
        ("Manifold Guard", "Calibrating state consistency..."),
        ("Architect", "Loading reasoning pathways..."),
        ("Discord Uplink", "Preparing communication channels..."),
        ("Telegram Uplink", "Initializing Mirror Protocol..."),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]SYSTEM BOOT", total=len(stages))

        for name, desc in stages:
            progress.update(task, description=f"[cyan]{name}[/cyan] — {desc}")
            await asyncio.sleep(0.3)
            progress.advance(task)

    console.print()
    console.print(Panel(
        "[bold green]████ SYSTEM READY ████[/bold green]",
        box=box.DOUBLE,
        border_style=EMERALD
    ), justify="center")

    # Show vitals preview
    state = cortex.read_metabolic_state()
    console.print()
    console.print(f"  [dim]CPU Temp:[/dim] [bold]{state.cpu_temp_celsius:.1f}°C[/bold]  "
                  f"[dim]RAM Free:[/dim] [bold]{state.ram_available_gb:.1f}GB[/bold]  "
                  f"[dim]Status:[/dim] [bold green]{state.thermal_status.name}[/bold green]")

    await asyncio.sleep(1)


# =============================================================================
# VITALS DASHBOARD
# =============================================================================
def render_vitals(cortex: Cortex):
    """Render system vitals as RPG stats."""
    state = cortex.read_metabolic_state()

    temp = state.cpu_temp_celsius
    stamina_pct = max(0, min(100, (80 - temp) / 40 * 100))
    mana_pct = 100 - state.ram_usage_percent

    status_map = {
        ThermalStatus.OPTIMAL: ("BATTLE READY", EMERALD),
        ThermalStatus.FATIGUED: ("WINDED", "yellow"),
        ThermalStatus.CRITICAL: ("EXHAUSTED", CRIMSON),
        ThermalStatus.RECOVERY: ("MEDITATING", ROYAL_BLUE),
    }
    status_text, status_color = status_map.get(state.thermal_status, ("UNKNOWN", SILVER))

    def render_bar(pct, good, bad):
        filled = int(pct / 100 * 25)
        empty = 25 - filled
        color = good if pct > 60 else ("yellow" if pct > 30 else bad)
        return f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/]"

    vitals = Table(
        box=box.DOUBLE_EDGE,
        border_style=GOLD,
        title="[bold]═══ ADVENTURER VITALS ═══[/bold]",
        title_style=GOLD,
        show_header=False,
        padding=(0, 1)
    )

    vitals.add_column("Stat", style=PARCHMENT)
    vitals.add_column("Bar", width=28)
    vitals.add_column("Value", justify="right", style=SILVER)

    vitals.add_row("Stamina", render_bar(stamina_pct, "green", "red"), f"{temp:.1f}°C")
    vitals.add_row("Mana", render_bar(mana_pct, "blue", "purple"), f"{state.ram_available_gb:.1f}GB")
    vitals.add_row("Status", f"[{status_color}]{status_text}[/]", "")

    console.print(vitals)


# =============================================================================
# CROWN & CREW CAMPAIGN MODE
# =============================================================================

# Council Dilemmas now sourced from engine.get_council_dilemma() (WO-V23.0)


async def run_crown_campaign(
    world_state: Optional[dict] = None,
    mimir: object = None,
    butler: object = None,
    campaign_data: Optional[dict] = None,
):
    """
    Run the Crown & Crew 5-Day Narrative Campaign.

    Args:
        world_state: Optional WorldState dict to inject custom world data.
                     If None, uses hardcoded defaults.
        mimir: Optional AI bridge (Architect instance) for narrative generation.
        butler: Optional Butler instance for session-aware reflexes (WO 100).
        campaign_data: Optional parsed campaign.json dict. When provided,
                       the scene progression system is activated for the
                       campaign if it contains ``scene_chapters`` or
                       ``scenes_by_day`` keys.

    Daily Cycle:
    1. MORNING   - World Card + Travel interaction
    2. NIGHT     - Allegiance Choice + Dilemma + Action interaction
    3. CAMPFIRE  - Reflection prompt (except Day 3)
    4. MIDNIGHT  - Council vote (group decision)
    5. SLEEP     - Transition to next day
    """
    console.clear()

    engine = CrownAndCrewEngine(world_state=world_state, mimir=mimir)

    # Attach scene runner if campaign_data contains scene definitions
    if campaign_data:
        try:
            from codex.games.crown.scenes import CrownSceneRunner
            _scene_runner = CrownSceneRunner.from_campaign_json(campaign_data)
            if _scene_runner.chapters:
                engine.set_scene_runner(_scene_runner)
        except Exception:
            pass

    # WO 100: Register engine with Butler for session-aware reflexes
    if butler:
        butler.register_session(engine)  # type: ignore[attr-defined]
        butler.sync_session_to_file()  # type: ignore[attr-defined]

    def _crown_narrate(text: str) -> None:
        """Narrate text via butler if available (Norse Skald voice)."""
        if butler and getattr(butler, '_voice_enabled', False):
            try:
                butler.narrate(text[:300])  # type: ignore[attr-defined]
            except Exception:
                pass

    # Title screen
    console.print(Panel(
        f"[bold gold1]CROWN & CREW[/bold gold1]\n\n"
        f"[dim]{engine.arc_length} days to reach the border.\n"
        f"One choice to make.[/dim]\n\n"
        f"[bold]Patron:[/bold] {engine.patron}\n"
        f"[bold]Leader:[/bold] {engine.leader}\n\n"
        f"[dim]Each day has four phases:[/dim]\n"
        f"  [cyan]MORNING[/cyan]   — The road ahead\n"
        f"  [magenta]NIGHT[/magenta]     — Your allegiance is tested\n"
        f"  [yellow]CAMPFIRE[/yellow]  — Reflect on the journey\n"
        f"  [gold1]MIDNIGHT[/gold1]  — The council decides",
        box=box.DOUBLE,
        border_style=CRIMSON,
        title="[bold]⚔️  The Journey Begins ⚔️[/bold]"
    ))

    await ainput("\n[dim]Press Enter to begin your journey...[/dim]")

    # Council dilemmas now tracked by engine (WO-V23.0)

    # Main game loop (WO-V23.0: dynamic arc_length)
    while engine.day <= engine.arc_length:
        day = engine.day
        engine.reset_day_state()
        # Determine region (scales with arc_length)
        breach_day = max(1, round(engine.arc_length * engine.rest_config.get("breach_day_fraction", 0.6)))
        if day < breach_day:
            region = "THE WILDS"
        elif day == breach_day:
            region = "THE BREACH"
        elif day < engine.arc_length:
            region = "THE BORDERLANDS"
        else:
            region = "THE BORDER"

        # =====================================================================
        # PHASE 1: MORNING — The World Card
        # =====================================================================
        console.clear()
        console.print(Panel(
            f"[bold]{engine.get_status()}[/bold]",
            title=f"[bold gold1]DAY {day} — {region}[/bold gold1]",
            box=box.HEAVY,
            border_style=GOLD
        ))

        console.print()
        console.print("[bold cyan]☀️  MORNING — THE ROAD AHEAD[/bold cyan]")
        console.print()

        # Use AI-enhanced prompt if mimir is wired, else static pool
        if engine.mimir:
            world = await engine.get_world_prompt_ai()
        else:
            world = engine.get_world_prompt()
        console.print(Panel(
            world,
            title="[dim]The Hostile Wilds[/dim]",
            border_style=SILVER,
            padding=(1, 2)
        ))
        _crown_narrate(world)

        # WO-V23.0: Tarot card for world prompt
        if TAROT_AVAILABLE:
            try:
                tarot_text = render_tarot_card("wolf", world)  # type: ignore[misc]
                if tarot_text:
                    console.print(Panel(tarot_text, border_style="dim", title="[dim]🃏 THE CARD[/dim]"))
            except Exception:
                pass

        # WO-V14.0: Morning Event — sway-relevant road encounter
        morning_event = engine.get_morning_event()
        bias = morning_event["bias"]
        event_border = "cyan" if bias == "crown" else "magenta" if bias == "crew" else "dim"
        bias_label = f" [{bias.upper()}]" if bias != "neutral" else ""
        console.print()
        console.print(Panel(
            f"[italic]{morning_event['text']}[/italic]",
            title=f"[bold]THE ROAD AHEAD{bias_label}[/bold]",
            border_style=event_border,
            padding=(1, 2)
        ))
        _crown_narrate(morning_event['text'])

        # Breach day special: Secret Witness appears at dawn (WO-V23.0)
        if engine.is_breach_day():
            console.print()
            console.print(Panel(
                engine.get_secret_witness(),
                title="[bold red]👁️  A FIGURE EMERGES FROM THE SHADOWS[/bold red]",
                border_style=CRIMSON,
                padding=(1, 2)
            ))

        console.print()
        await ainput("[dim]How do you traverse this terrain? > [/dim]")

        console.print()
        await ainput("\n[dim][Press Enter to continue...][/dim]")

        # =====================================================================
        # PHASE 1.5: SCENE — Optional narrative choice (from campaign_data)
        # =====================================================================
        _scene = engine.get_scene_for_today()
        if _scene:
            console.clear()
            console.print(Panel(
                f"[bold]{engine.get_status()}[/bold]",
                title=f"[bold gold1]DAY {day} — {region}[/bold gold1]",
                box=box.HEAVY,
                border_style=GOLD
            ))
            console.print()
            console.print("[bold cyan]🎭 A SCENE UNFOLDS[/bold cyan]")
            console.print()

            _scene_title = _scene.location if _scene.location else f"Day {day} — Scene"
            console.print(Panel(
                f"[italic]{_scene.description}[/italic]",
                title=f"[bold]{_scene_title}[/bold]",
                border_style="cyan",
                padding=(1, 2)
            ))
            console.print()

            for idx, text in enumerate(_scene.get_choice_texts()):
                console.print(f"  [bold][{idx + 1}][/bold] {text}")

            console.print()
            _scene_input = ""
            while True:
                _scene_raw = (await ainput("[cyan]Your choice: [/]")).strip()
                if _scene_raw.isdigit() and 1 <= int(_scene_raw) <= len(_scene.choices):
                    _scene_input = _scene_raw
                    break
                if not _scene_raw and _scene.choices:
                    _scene_input = "1"
                    break
                console.print(f"[dim]Enter a number between 1 and {len(_scene.choices)}[/dim]")

            _scene_result = engine.resolve_scene_choice(int(_scene_input) - 1)
            if _scene_result.get("narrative"):
                console.print()
                console.print(Panel(
                    f"[italic]{_scene_result['narrative']}[/italic]",
                    border_style="dim cyan",
                    padding=(1, 2)
                ))

            _sway_delta = _scene_result.get("sway_effect", 0)
            if _sway_delta != 0:
                _direction = "toward the Crown" if _sway_delta > 0 else "toward the Crew"
                console.print(f"[dim]Sway shifts {_direction}. Now: {engine.sway:+d}[/dim]")

            console.print()
            await ainput("[dim][Press Enter to continue...][/dim]")

        # =====================================================================
        # PHASE 2: NIGHT — The Choice (Blind Allegiance)
        # =====================================================================
        console.clear()
        console.print(Panel(
            f"[bold]{engine.get_status()}[/bold]",
            title=f"[bold gold1]DAY {day} — {region}[/bold gold1]",
            box=box.HEAVY,
            border_style=GOLD
        ))

        console.print()
        console.print("[bold magenta]🌙 NIGHT — THE MOMENT OF CHOICE[/bold magenta]")
        console.print()
        console.print("[dim]The shadows gather. You must decide BEFORE you see the consequences.[/dim]")
        console.print("[dim]This is the Blind Allegiance — choose your side, then face the dilemma.[/dim]")
        console.print()

        # Allegiance choice
        while True:
            choice = (await ainput("[gold1]Declare your allegiance — [C]rown or C[R]ew: [/]")).lower().strip()

            if choice in ('c', 'crown'):
                side = 'crown'
                break
            elif choice in ('r', 'crew'):
                side = 'crew'
                break
            else:
                console.print("[dim]Enter C for Crown or R for Crew[/dim]")

        # Declare allegiance
        result = engine.declare_allegiance(side)
        console.print()
        console.print(f"[bold cyan]>> {result}[/bold cyan]")

        # Reveal the dilemma for chosen side
        if engine.mimir:
            prompt = await engine.get_dilemma_ai()
        else:
            prompt = engine.get_prompt()
        dilemma_title = "👑 THE CROWN'S BURDEN" if side == 'crown' else "🏴 THE CREW'S TRIAL"
        console.print()
        console.print(Panel(
            f"[italic]{prompt}[/italic]",
            title=f"[bold]{dilemma_title}[/bold]",
            border_style=MAGENTA,
            padding=(1, 2)
        ))
        _crown_narrate(prompt)

        # Show DNA accumulation
        dom_tag = engine.get_dominant_tag()
        console.print(f"\n[dim]Your dominant trait: [bold]{dom_tag}[/bold][/dim]")

        console.print()
        await ainput("[bold green]What do you do? > [/bold green]")

        console.print()
        await ainput("\n[dim][Press Enter to continue...][/dim]")

        # =====================================================================
        # PHASE 3: CAMPFIRE — The Echo (except Breach day)
        # =====================================================================
        if not engine.is_breach_day():
            console.clear()
            console.print(Panel(
                f"[bold]{engine.get_status()}[/bold]",
                title=f"[bold gold1]DAY {day} — {region}[/bold gold1]",
                box=box.HEAVY,
                border_style=GOLD
            ))

            console.print()
            console.print("[bold yellow]🔥 CAMPFIRE — THE ECHO[/bold yellow]")
            console.print()

            campfire = engine.get_campfire_prompt()
            console.print(Panel(
                campfire,
                title="[dim]The fire burns low. Shadows press close.[/dim]",
                border_style="yellow",
                padding=(1, 2)
            ))
            _crown_narrate(campfire)

            # WO-V23.0: Tarot card for campfire
            if TAROT_AVAILABLE:
                try:
                    tarot_text = render_tarot_card("dead_tree", campfire)  # type: ignore[misc]
                    if tarot_text:
                        console.print(Panel(tarot_text, border_style="dim yellow", title="[dim]🃏 THE CARD[/dim]"))
                except Exception:
                    pass

            console.print()
            await ainput("[bold green]Your reflection? > [/bold green]")
        else:
            console.print()
            console.print(Panel(
                "[dim italic]No campfire tonight. The Breach has broken the silence.\n"
                "You travel in darkness, each lost in your own thoughts.[/dim italic]",
                border_style="dim red"
            ))
            await ainput("\n[dim]Press Enter to continue...[/dim]")

        # =====================================================================
        # PHASE 4: MIDNIGHT — The Council
        # =====================================================================
        console.clear()
        console.print(Panel(
            f"[bold]{engine.get_status()}[/bold]",
            title=f"[bold gold1]DAY {day} — {region}[/bold gold1]",
            box=box.HEAVY,
            border_style=GOLD
        ))

        console.print()
        console.print("[bold gold1]⚖️  MIDNIGHT COUNCIL[/bold gold1]")
        console.print()
        console.print("[dim]The group gathers. A final decision must be made before sleep.[/dim]")
        console.print()

        # Get dilemma from engine (WO-V23.0 — deduplicated)
        dilemma = engine.get_council_dilemma()

        console.print(Panel(
            f"[bold]{dilemma['prompt']}[/bold]\n\n"
            f"[cyan][1] CROWN PATH:[/cyan] {dilemma['crown']}\n\n"
            f"[magenta][2] CREW PATH:[/magenta] {dilemma['crew']}",
            title="[bold]THE DILEMMA[/bold]",
            border_style=GOLD,
            padding=(1, 2)
        ))
        _crown_narrate(dilemma['prompt'])

        console.print()
        while True:
            vote = (await ainput("[bold gold1]The council votes — [1] Crown or [2] Crew: [/]")).strip()
            if vote == "1":
                console.print("\n[cyan]>> The council chooses the Crown's path.[/cyan]")
                # Council vote doesn't affect individual sway, but we could track it
                break
            elif vote == "2":
                console.print("\n[magenta]>> The council chooses the Crew's path.[/magenta]")
                break
            else:
                console.print("[dim]Enter 1 for Crown or 2 for Crew[/dim]")

        console.print()
        await ainput("\n[dim][Press Enter to continue...][/dim]")

        # =====================================================================
        # PHASE 5: REST — Day Transition (WO-V23.0: rest choice)
        # =====================================================================
        console.print()

        if day < engine.arc_length:
            # Offer rest choice
            console.print("[bold yellow]🛏️  THE CAMP[/bold yellow]")
            console.print()
            console.print("[bold][1][/bold] Long Rest   — Full phase cycle. Advances to next day.")
            console.print("[bold][2][/bold] Short Rest  — Brief respite. Stay on current day.")
            console.print("[bold][3][/bold] Press On    — No rest. Sway decays toward neutral.")
            console.print()

            while True:
                rest_choice = (await ainput("[gold1]Choose [1/2/3]: [/]")).strip()
                if rest_choice in ("1", "2", "3"):
                    break
                console.print("[dim]Enter 1, 2, or 3[/dim]")

            if rest_choice == "1":
                end_msg = engine.trigger_long_rest()
            elif rest_choice == "2":
                short_msg = engine.trigger_short_rest()
                console.print(f"[cyan]{short_msg}[/cyan]")
                # Short rest does NOT advance day — continue to next iteration
                if butler:
                    butler.sync_session_to_file()  # type: ignore[attr-defined]
                console.print()
                await ainput("[dim]Press Enter to continue...[/dim]")
                continue
            else:
                skip_msg = engine.skip_rest()
                console.print(f"[cyan]{skip_msg}[/cyan]")
                end_msg = engine.end_day()
        else:
            # Final day — no rest choice, just end
            end_msg = engine.end_day()

        if engine.mimir:
            ai_narration = await engine.resolve_day_ai()
            console.print(f"[italic dim]{ai_narration}[/italic dim]")
            _crown_narrate(ai_narration)
        for line in end_msg.split('\n'):
            console.print(f"[cyan]{line}[/cyan]")

        # WO 102: Sync Crown state to bridge file for voice
        if butler:
            butler.sync_session_to_file()  # type: ignore[attr-defined]

        console.print()
        if engine.day <= engine.arc_length:
            await ainput("[dim]Press Enter to rest...[/dim]")
        else:
            await ainput("[dim]Press Enter to face your fate...[/dim]")

    # Guard: force campaign end if loop exits abnormally
    if engine.day <= engine.arc_length:
        engine.day = engine.arc_length + 1

    # =========================================================================
    # FINALE — Legacy Report
    # =========================================================================
    console.clear()
    report = engine.generate_legacy_report()
    summary = engine.get_summary()

    console.print(Panel(
        "[bold gold1]THE BORDER — JOURNEY'S END[/bold gold1]\n\n"
        "[dim]You have reached the edge of the realm.\n"
        "The choices you made have shaped your soul.[/dim]",
        box=box.DOUBLE,
        border_style=GOLD
    ))

    # WO-V23.0: Tarot card for legacy
    if TAROT_AVAILABLE:
        try:
            tarot_text = render_tarot_card("moon", report)  # type: ignore[misc]
            if tarot_text:
                console.print(Panel(tarot_text, border_style="dim gold1", title="[dim]🃏 THE FINAL CARD[/dim]"))
        except Exception:
            pass

    console.print()
    console.print(Panel(
        report,
        title="[bold]⚔️  LEGACY REPORT ⚔️[/bold]",
        border_style=EMERALD,
        padding=(1, 2)
    ))
    _crown_narrate("Your journey is complete. " + report[:250])

    console.print()
    console.print(Panel(
        summary,
        title="[bold]📜 JOURNEY LOG[/bold]",
        border_style=SILVER,
        padding=(1, 2)
    ))

    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    legacy_dir = CODEX_DIR / "saves"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    filename = legacy_dir / f"crown_legacy_{timestamp}.txt"
    with open(filename, 'w') as f:
        f.write("CROWN & CREW - LEGACY REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(report + "\n\n" + summary)

    console.print(f"\n[dim]Report saved to: {filename}[/dim]")

    # WO 100: Clear Butler session on campaign end
    if butler:
        butler.clear_session()  # type: ignore[attr-defined]

    await ainput("\n[dim]Press Enter to return to Main Menu...[/dim]")


# =============================================================================
# ASHBURN HEIR CAMPAIGN MODE
# =============================================================================
async def run_ashburn_campaign(world_state: Optional[dict] = None, core: Optional[CodexCore] = None):
    """
    Run the Ashburn Heir 5-Day Corruption Campaign.

    Uses AshburnHeirEngine instead of base CrownAndCrewEngine.
    Implements Legacy Checks, Corruption tracking, and immediate loss.

    Args:
        world_state: Optional WorldState dict (from saved game or genesis)
        core: Optional CodexCore for AI narration integration
    """
    console.clear()

    # Ashburn color palette
    ASHBURN_CRIMSON = "#8B0000"
    ASHBURN_ASH_GREY = "grey70"
    ASHBURN_EMBER = "#CD853F"
    ASHBURN_DEEP_PURPLE = "purple"

    # =========================================================================
    # SCREEN 1: The Iron Gates (Landing)
    # =========================================================================
    ashburn_header = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║         ▄▀▄   ASHBURN HIGH   ▄▀▄                        ║
    ║        ║   ║  ─────────────  ║   ║                       ║
    ║        ║   ║  The Iron Gates ║   ║                       ║
    ║        ╠═══╣                 ╠═══╣                       ║
    ║        ║   ║    Est. 1847    ║   ║                       ║
    ║        ║   ║                 ║   ║                       ║
    ║       ▄╩▄ ▄╩▄             ▄╩▄ ▄╩▄                      ║
    ╚══════════════════════════════════════════════════════════╝
    """

    console.print(Panel(
        f"[{ASHBURN_CRIMSON}]{ashburn_header}[/]\n\n"
        "[dim]Behind the iron gates, two heirs await.\n"
        "One will inherit. One will be consumed.[/dim]",
        border_style=ASHBURN_CRIMSON,
        box=box.DOUBLE,
        title="[bold #8B0000]ASHBURN HIGH[/bold #8B0000]"
    ))

    await ainput("\n[dim]Press Enter to choose your heir...[/dim]")

    # =========================================================================
    # SCREEN 2: The Choice (Heir Selection)
    # =========================================================================
    console.clear()

    # Display two heir panels side-by-side (or stacked)
    julian_data = ASHBURN_LEADERS["Julian"]  # type: ignore[index]
    rowan_data = ASHBURN_LEADERS["Rowan"]  # type: ignore[index]

    console.print(Panel(
        "[bold #DAA520]JULIAN ASHBURN[/bold #DAA520]\n"
        "[italic grey70]The Gilded Son[/italic grey70]\n\n"
        "A golden prince trapped in amber.\n"
        "The Board chose him before he could choose himself.\n\n"
        f"[cyan]Power:[/cyan] {julian_data['ability']}\n"
        f"[{ASHBURN_CRIMSON}]Risk:[/]  {julian_data['risk']}",
        border_style="#DAA520",
        title="[bold][1] JULIAN[/bold]",
        box=box.DOUBLE,
        padding=(1, 2)
    ))

    console.print()

    console.print(Panel(
        "[bold grey70]ROWAN ASHBURN[/bold grey70]\n"
        "[italic #CD853F]The Ash Walker[/italic #CD853F]\n\n"
        "They found the old records.\n"
        "They know what the school buried.\n\n"
        f"[cyan]Power:[/cyan] {rowan_data['ability']}\n"
        f"[{ASHBURN_CRIMSON}]Risk:[/]  {rowan_data['risk']}",
        border_style="grey50",
        title="[bold][2] ROWAN[/bold]",
        box=box.DOUBLE,
        padding=(1, 2)
    ))

    console.print()

    # Heir selection loop
    while True:
        choice = await ainput("[grey70]Choose your heir — [1] Julian, [2] Rowan, or [b]ack: [/]")
        choice = choice.lower().strip()

        if choice == "back" or choice == "b":
            return  # Return to main menu

        if choice == "1":
            heir_name = "Julian"
            break
        elif choice == "2":
            heir_name = "Rowan"
            break
        else:
            console.print("[dim]Enter 1 for Julian, 2 for Rowan, or 'back' to return[/dim]")

    # =========================================================================
    # SCREEN 3: The Game Loop (Dynamic Arc Campaign)
    # =========================================================================
    console.clear()

    # Instantiate engine
    engine = AshburnHeirEngine(heir_name=heir_name, world_state=world_state)  # type: ignore[misc]

    # Briefing
    console.print(Panel(
        f"[bold gold1]{engine.heir_name}[/bold gold1] — [dim]{engine.heir_leader['title']}[/dim]\n\n"
        f"[dim]Heir of the Ashburn Line[/dim]\n\n"
        f"[bold]Corruption:[/bold] [{ASHBURN_ASH_GREY}]{'░' * 5}[/] 0/5\n"
        f"[bold]Starting Sway:[/bold] {engine.sway:+d}\n\n"
        f"[cyan]Ability:[/cyan] {engine.leader_ability}\n"
        f"[{ASHBURN_CRIMSON}]Risk:[/] {engine.heir_leader['risk']}",
        border_style=ASHBURN_CRIMSON,
        title="[bold]HEIR BRIEFING[/bold]",
        box=box.HEAVY
    ))

    await ainput("\n[dim]Press Enter to begin your journey...[/dim]")

    # =========================================================================
    # PROLOGUE — Opening Scenario
    # =========================================================================
    prologue_result = await engine.run_prologue(core=core)

    console.print(f"\n[dim]Scenario: {prologue_result['scenario']}[/dim]")
    await ainput("\n[dim]Press Enter to continue to Day 1...[/dim]")

    # Dynamic Arc Loop (CB-03/04/05 fix)
    try:
        for day in range(1, engine.arc_length + 1):
            console.clear()

            # Determine region dynamically based on arc_length
            breach_day = max(1, round(engine.arc_length * engine.rest_config.get("breach_day_fraction", 0.6)))
            if day < breach_day:
                region = "THE ASHBURN GROUNDS"
            elif day == breach_day:
                region = "THE BREACH"
            elif day < engine.arc_length:
                region = "THE TRIBUNAL APPROACH"
            else:
                region = "THE INHERITANCE"

            console.print(f"\n[bold {ASHBURN_CRIMSON}]═══ DAY {day} of {engine.arc_length} — {region} ═══[/bold {ASHBURN_CRIMSON}]\n")

            # Morning: World prompt
            world = engine.get_world_prompt()
            if TAROT_AVAILABLE:
                world_card = render_tarot_card("wolf", world, custom_title="[dim]The Hostile Grounds[/dim]")  # type: ignore[misc]
                console.print(world_card)
            else:
                console.print(Panel(
                    world,
                    title="[dim]The Hostile Grounds[/dim]",
                    border_style=ASHBURN_ASH_GREY,
                    padding=(1, 2)
                ))

            # Breach day special: Secret Witness
            if day == breach_day:
                console.print()
                console.print(Panel(
                    engine.get_secret_witness(),
                    title=f"[bold {ASHBURN_CRIMSON}]👁️  A FIGURE EMERGES[/bold {ASHBURN_CRIMSON}]",
                    border_style=ASHBURN_CRIMSON,
                    padding=(1, 2)
                ))

            console.print()
            await ainput("[dim]How do you navigate this terrain? > [/dim]")

            # Night: Allegiance choice
            console.clear()
            console.print(f"\n[bold {ASHBURN_CRIMSON}]═══ DAY {day} — NIGHT ═══[/bold {ASHBURN_CRIMSON}]\n")
            console.print("[bold magenta]🌙 THE MOMENT OF CHOICE[/bold magenta]")
            console.print()
            console.print("[dim]The shadows gather. You must decide BEFORE you see the consequences.[/dim]")
            console.print()

            # Allegiance input loop
            while True:
                side_choice = await ainput("[gold1]Declare your allegiance — [C]rown or C[R]ew: [/]")
                side_choice = side_choice.lower().strip()

                if side_choice in ('c', 'crown'):
                    side = 'crown'
                    break
                elif side_choice in ('r', 'crew'):
                    side = 'crew'
                    break
                else:
                    console.print("[dim]Enter C for Crown or R for Crew[/dim]")

            # Declare allegiance
            result = engine.declare_allegiance(side)
            console.print()
            console.print(f"[bold cyan]>> {result}[/bold cyan]")
            console.print()

            # Legacy Check (if Crown allegiance)
            check = engine.generate_legacy_check()

            if isinstance(check, dict) and check.get("triggered"):
                # LEGACY INTERVENTION
                legacy_prompt_body = (
                    f"{check['prompt']}\n\n"
                    "[bold cyan][1] OBEY[/bold cyan] — Submit to authority\n"
                    "  [dim]+1 Corruption, Sway toward Crown[/dim]\n\n"
                    f"[bold {ASHBURN_EMBER}][2] LIE[/bold {ASHBURN_EMBER}] — Deflect and deceive\n"
                    "  [dim]Sway toward Crew, Risk: Detection (33%)[/dim]"
                )

                if TAROT_AVAILABLE:
                    legacy_card = render_tarot_card(  # type: ignore[misc]
                        "moon",
                        legacy_prompt_body,
                        custom_title=f"[bold {ASHBURN_CRIMSON}]⚠️  THE BOARD SUMMONS YOU  ⚠️[/bold {ASHBURN_CRIMSON}]",
                        width=50
                    )
                    console.print(legacy_card)
                else:
                    console.print(Panel(
                        f"[bold {ASHBURN_DEEP_PURPLE}]⚠️  LEGACY CALL  ⚠️[/bold {ASHBURN_DEEP_PURPLE}]\n\n"
                        f"[italic]{check['prompt']}[/italic]\n\n"
                        "[bold cyan][1] OBEY[/bold cyan] — Submit to authority\n"
                        "  [dim]+1 Corruption, Sway toward Crown[/dim]\n\n"
                        f"[bold {ASHBURN_EMBER}][2] LIE[/bold {ASHBURN_EMBER}] — Deflect and deceive\n"
                        "  [dim]Sway toward Crew, Risk: Detection (33%)[/dim]",
                        border_style=ASHBURN_DEEP_PURPLE,
                        title=f"[bold {ASHBURN_CRIMSON}]⚠️  THE BOARD SUMMONS YOU  ⚠️[/bold {ASHBURN_CRIMSON}]",
                        box=box.HEAVY,
                        padding=(1, 2)
                    ))

                console.print()

                # Intervention choice loop
                while True:
                    intervention_choice = await ainput(f"[{ASHBURN_DEEP_PURPLE}]Your choice — [1] or [2]: [/]")
                    intervention_choice = intervention_choice.strip()

                    if intervention_choice in ['1', '2']:
                        break
                    else:
                        console.print("[dim]Enter 1 to Obey or 2 to Lie[/dim]")

                # Resolve legacy choice (async with AI narration)
                lc_result = await engine.resolve_legacy_choice(int(intervention_choice), core=core)
                console.print(f"\n[grey70]{lc_result['consequence']}[/grey70]")

                # Display AI narration
                if lc_result.get('narration'):
                    console.print(Panel(
                        lc_result['narration'],
                        border_style="dim",
                        title="[italic dim]The Aftermath[/italic dim]"
                    ))

                # Check for betrayal/game over
                betrayal = engine.check_betrayal()
                if betrayal is not None and betrayal.get("game_over"):
                    # BAD END - The Solarium Opens
                    console.print("\n")
                    console.print(Panel(
                        f"[bold {ASHBURN_CRIMSON}]THE SOLARIUM OPENS[/bold {ASHBURN_CRIMSON}]\n\n"
                        "[grey70]The glass shatters inward.\n"
                        "You were never the heir — you were the inheritance.\n\n"
                        "ASHBURN CLAIMS ANOTHER.[/grey70]",
                        border_style=ASHBURN_CRIMSON,
                        title=f"[bold {ASHBURN_CRIMSON}]GAME OVER[/bold {ASHBURN_CRIMSON}]",
                        box=box.DOUBLE
                    ))
                    console.print(f"\n[dim]Corruption: {engine.legacy_corruption}/5[/dim]")
                    console.print(f"[dim]Days Survived: {day}/{engine.arc_length}[/dim]")
                    await ainput("\n[grey70]Press Enter to return...[/grey70]")
                    return
            else:
                # STANDARD TURN - display normal prompt
                prompt = engine.get_prompt()
                dilemma_title = "👑 THE CROWN'S BURDEN" if side == 'crown' else "🏴 THE CREW'S TRIAL"

                if TAROT_AVAILABLE:
                    # Use Sun Ring for Crown, Registry Key for Crew
                    card_key = "sun_ring" if side == 'crown' else "registry_key"
                    prompt_card = render_tarot_card(card_key, prompt, custom_title=f"[bold]{dilemma_title}[/bold]")  # type: ignore[misc]
                    console.print(prompt_card)
                else:
                    console.print(Panel(
                        prompt,
                        title=f"[bold]{dilemma_title}[/bold]",
                        border_style="magenta",
                        padding=(1, 2)
                    ))

            # Show DNA accumulation
            dom_tag = engine.get_dominant_tag()
            console.print(f"\n[dim]Your dominant trait: [bold]{dom_tag}[/bold][/dim]")

            console.print()
            await ainput("[bold green]What do you do? > [/bold green]")

            # Campfire (except Breach day)
            if day != breach_day:
                console.clear()
                console.print(f"\n[bold {ASHBURN_CRIMSON}]═══ DAY {day} — CAMPFIRE ═══[/bold {ASHBURN_CRIMSON}]\n")
                console.print("[bold yellow]🔥 THE ECHO[/bold yellow]")
                console.print()

                campfire = engine.get_campfire_prompt()

                if TAROT_AVAILABLE:
                    campfire_card = render_tarot_card(  # type: ignore[misc]
                        "dead_tree",
                        campfire,
                        custom_title="[dim]The fire burns low. Shadows press close.[/dim]"
                    )
                    console.print(campfire_card)
                else:
                    console.print(Panel(
                        campfire,
                        title="[dim]The fire burns low. Shadows press close.[/dim]",
                        border_style="yellow",
                        padding=(1, 2)
                    ))

                console.print()
                await ainput("[bold green]Your reflection? > [/bold green]")
            else:
                console.print()
                console.print(Panel(
                    "[dim italic]No campfire tonight. The Breach has broken the silence.\n"
                    "You travel in darkness, each lost in your own thoughts.[/dim italic]",
                    border_style="dim red"
                ))
                await ainput("\n[dim]Press Enter to continue...[/dim]")

            # Status Update
            console.print()

            # Build corruption meter
            corruption = engine.legacy_corruption
            filled = "█" * corruption
            empty = "░" * (5 - corruption)

            if corruption == 0:
                corr_color = "green"
                corr_status = "Pure"
            elif corruption <= 2:
                corr_color = "yellow"
                corr_status = "Tempted"
            elif corruption <= 4:
                corr_color = ASHBURN_EMBER
                corr_status = "Compromised"
            else:
                corr_color = ASHBURN_CRIMSON
                corr_status = "Lost"

            console.print(Panel(
                f"[bold gold1]{engine.heir_name}[/bold gold1] — [dim]{engine.heir_leader['title']}[/dim]\n\n"
                f"[bold]CORRUPTION[/bold]\n"
                f"[{corr_color}]{filled}{empty}[/] {corruption}/5 — {corr_status}\n\n"
                f"[bold]SWAY[/bold]\n"
                f"{engine.get_sway_visual()} {engine.sway:+d}",
                border_style=ASHBURN_ASH_GREY,
                title="[bold]STATUS[/bold]"
            ))

            # Check betrayal again (in case of other corruption sources)
            betrayal = engine.check_betrayal()
            if betrayal is not None and betrayal.get("game_over"):
                # BAD END
                console.print("\n")
                console.print(Panel(
                    f"[bold {ASHBURN_CRIMSON}]THE SOLARIUM OPENS[/bold {ASHBURN_CRIMSON}]\n\n"
                    "[grey70]The glass shatters inward.\n"
                    "You were never the heir — you were the inheritance.\n\n"
                    "ASHBURN CLAIMS ANOTHER.[/grey70]",
                    border_style=ASHBURN_CRIMSON,
                    title=f"[bold {ASHBURN_CRIMSON}]GAME OVER[/bold {ASHBURN_CRIMSON}]",
                    box=box.DOUBLE
                ))
                console.print(f"\n[dim]Corruption: {engine.legacy_corruption}/5[/dim]")
                console.print(f"[dim]Days Survived: {day}/{engine.arc_length}[/dim]")
                await ainput("\n[grey70]Press Enter to return...[/grey70]")
                return

            # Day transition
            console.print()
            end_msg = engine.end_day()
            for line in end_msg.split('\n'):
                console.print(f"[cyan]{line}[/cyan]")

            console.print()
            if day < engine.arc_length:
                await ainput("[dim]Press Enter to rest...[/dim]")
            else:
                await ainput("[dim]Press Enter to face your fate...[/dim]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Campaign interrupted. Returning to main menu...[/yellow]")
        return

    # =========================================================================
    # FINALE — Good Ending (Survived the full arc)
    # =========================================================================
    console.clear()

    # Final betrayal check
    betrayal = engine.check_betrayal()
    if betrayal is not None and betrayal.get("game_over"):
        # BAD END
        console.print(Panel(
            f"[bold {ASHBURN_CRIMSON}]THE SOLARIUM OPENS[/bold {ASHBURN_CRIMSON}]\n\n"
            "[grey70]The glass shatters inward.\n"
            "You were never the heir — you were the inheritance.\n\n"
            "ASHBURN CLAIMS ANOTHER.[/grey70]",
            border_style=ASHBURN_CRIMSON,
            title=f"[bold {ASHBURN_CRIMSON}]GAME OVER[/bold {ASHBURN_CRIMSON}]",
            box=box.DOUBLE
        ))
        console.print(f"\n[dim]Corruption: {engine.legacy_corruption}/5[/dim]")
        console.print(f"[dim]Days Survived: {engine.arc_length}/{engine.arc_length}[/dim]")
        await ainput("\n[grey70]Press Enter to return...[/grey70]")
        return

    # GOOD END - Survived
    corruption = engine.legacy_corruption
    filled = "█" * corruption
    empty = "░" * (5 - corruption)

    if corruption <= 2:
        corr_color = "yellow"
    else:
        corr_color = ASHBURN_EMBER

    console.print(Panel(
        "[grey70]The iron gates open outward.\n"
        "Grey morning light spills across the threshold.\n\n"
        "You survived Ashburn. But survival is not the same as escape.\n"
        "The school remembers. It always remembers.[/grey70]\n\n"
        f"[bold]Final Corruption:[/bold] [{corr_color}]{filled}{empty}[/] {corruption}/5\n"
        f"[bold]Final Sway:[/bold] {engine.sway:+d}\n"
        f"[bold]Dominant Trait:[/bold] {engine.get_dominant_tag()}",
        border_style="grey70",
        title="[bold grey70]THE GREY MORNING[/bold grey70]",
        box=box.DOUBLE
    ))

    console.print()

    # Legacy report
    report = engine.generate_legacy_report()
    summary = engine.get_summary()

    console.print(Panel(
        report,
        title="[bold]⚔️  LEGACY REPORT ⚔️[/bold]",
        border_style=EMERALD,
        padding=(1, 2)
    ))

    console.print()

    console.print(Panel(
        summary,
        title="[bold]📜 JOURNEY LOG[/bold]",
        border_style=SILVER,
        padding=(1, 2)
    ))

    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = CODEX_DIR / f"ashburn_legacy_{timestamp}.txt"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("ASHBURN CAMPAIGN - LEGACY REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Heir: {engine.heir_name}\n")
            f.write(f"Final Corruption: {engine.legacy_corruption}/5\n")
            f.write("=" * 60 + "\n\n")
            f.write(report + "\n\n" + summary)

        console.print(f"\n[dim]Report saved to: {filename}[/dim]")
    except Exception as e:
        logger.error(f"Failed to save Ashburn report: {e}")

    await ainput("\n[grey70]Press Enter to return...[/grey70]")


# =============================================================================
# MIMIR'S VAULT (Library Browser)
# =============================================================================
async def run_library(core: CodexCore, system_id=None):
    """Launch Mimir's Vault as a modal browser.

    Runs the blocking ``LibrarianTUI.run_loop()`` in an executor so the
    async event-loop stays alive.  The calling game state (if any) is
    untouched -- this is a pure overlay that returns control on exit.
    """
    if not LIBRARIAN_AVAILABLE:
        console.print(Panel(
            "[yellow]Librarian module not available.[/yellow]\n\n"
            "[dim]Ensure codex/core/services/librarian.py is present.[/dim]",
            border_style="yellow"
        ))
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # Attempt to wire up Mimir AI for live queries
    mimir_fn = None
    try:
        from codex.integrations.mimir import query_mimir
        mimir_fn = query_mimir
    except ImportError:
        pass

    lib = LibrarianTUI(mimir_fn=mimir_fn, system_id=system_id)  # type: ignore[misc]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lib.run_loop)


# =============================================================================
# CHRONICLES TTRPG TOOLS
# =============================================================================
async def run_dm_tools_menu(core: CodexCore):
    """
    DM Tools — TTRPG Utility Toolkit.

    Provides dice rolling, NPC generation, loot tables, trap generator,
    session notes, world genesis, and character forge.
    """
    while True:
        try:
            console.clear()
            console.print(Text(TITLE_ART, style=GOLD))

            console.print()
            console.print(Panel(
                "[bold cyan]DM TOOLS[/bold cyan]\n\n"
                "[dim]The Dungeon Master's Toolkit — Dice, NPCs, World Building, and more.[/dim]",
                box=box.DOUBLE,
                border_style=ROYAL_BLUE,
                title="[bold]🛠️  DM TOOLS 🛠️[/bold]"
            ))
            console.print()

            tools_menu = Table(
                box=box.HEAVY,
                border_style=ROYAL_BLUE,
                show_header=False,
                padding=(0, 2),
                title="[bold]══════ SELECT TOOL ══════[/bold]",
                title_style=ROYAL_BLUE
            )

            tools_menu.add_column("Option", style=GOLD)
            tools_menu.add_column("Description", style=PARCHMENT)

            tools_menu.add_row("[1]", "🎲 Dice Roller         — Roll any dice expression (2d6+3, 1d20, etc.)")
            tools_menu.add_row("[2]", "👤 NPC Generator       — Create a random NPC with personality")
            tools_menu.add_row("[3]", "💰 Loot Generator      — Generate treasure and equipment")
            tools_menu.add_row("[4]", "🕳️  Trap Generator      — Create deadly traps and hazards")
            tools_menu.add_row("[5]", "⚔️  Encounter Generator — Generate random encounters")
            tools_menu.add_row("[6]", "📜 Session Notes       — Summarize current session context")
            tools_menu.add_row("[7]", "🌍 World Genesis       — Create a custom world")
            tools_menu.add_row("[8]", "⚒️  Character Forge     — Build a new hero (standalone)")
            tools_menu.add_row("[0]", "🔍 Scan Vault          — Extract tables from vault PDFs")
            tools_menu.add_row("[G]", "🏗️  Module Generator    — Generate a playable adventure module")
            tools_menu.add_row("[E]", "✨ Module Enrichment   — Enrich a module with AI descriptions")
            tools_menu.add_row("[9]", "↩️  Back to Main Menu  — Return")

            console.print()
            console.print(Align.center(tools_menu))
            console.print()

            choice = await ainput("[gold1]Choose thy tool [0-9/G/E]:[/] ")
            choice = choice.lower().strip()

            if not choice:
                continue

            if choice == "1":
                # Dice Roller
                await run_dice_roller()

            elif choice == "2":
                # NPC Generator
                if TOOLS_AVAILABLE:
                    await run_npc_generator(core)
                else:
                    console.print("[yellow]dm_tools module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "3":
                # Loot Generator
                if TOOLS_AVAILABLE:
                    await run_loot_generator()
                else:
                    console.print("[yellow]dm_tools module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "4":
                # Trap Generator
                if TOOLS_AVAILABLE:
                    await run_trap_generator()
                else:
                    console.print("[yellow]dm_tools module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "5":
                # Encounter Generator (NEW)
                if TOOLS_AVAILABLE:
                    await run_encounter_generator()
                else:
                    console.print("[yellow]dm_tools module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "6":
                # Session Notes / Context Summary
                if TOOLS_AVAILABLE:
                    await run_session_notes(core)
                else:
                    console.print("[yellow]dm_tools module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "7":
                # World Genesis
                if TAROT_AVAILABLE:
                    console.print(render_tarot_card(get_card_for_context("world"), "A new world takes shape."))  # type: ignore[misc]
                await run_genesis_sub_menu(core)

            elif choice == "8":
                # Character Forge (standalone)
                if FORGE_AVAILABLE:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, run_character_forge)  # type: ignore[arg-type]
                else:
                    console.print(Panel(
                        "[yellow]Character Forge module not available.[/yellow]\n\n"
                        "[dim]Ensure codex_char_wizard.py is present in the Codex directory.[/dim]",
                        border_style="yellow"
                    ))
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "0":
                # Scan Vault
                if TOOLS_AVAILABLE:
                    await run_vault_scan()
                else:
                    console.print("[yellow]dm_tools module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice in ("g", "gen", "generate"):
                await run_module_generator()

            elif choice in ("e", "enrich"):
                await run_module_enrichment()

            elif choice == "9":
                # Back to main menu
                return

        except KeyboardInterrupt:
            console.print("\n[yellow]Returning to main menu...[/yellow]")
            return


# ── Module Generator ──────────────────────────────────────────────────────

async def run_module_generator():
    """Interactive module generator — wraps scripts/generate_module.py."""
    console.clear()
    console.print(Panel(
        "[bold cyan]MODULE GENERATOR[/bold cyan]\n\n"
        "[dim]Generate a complete playable adventure module from a template\n"
        "and system-specific content pool. Type 'back' to return.[/dim]",
        border_style="cyan", box=box.DOUBLE,
    ))

    # List templates
    try:
        from scripts.generate_module import list_templates, generate_module
    except ImportError:
        console.print("[red]generate_module.py not found in scripts/.[/red]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    templates = list_templates()
    if not templates:
        console.print("[yellow]No templates found in config/templates/.[/yellow]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # Show templates
    t_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t_table.add_column("ID", style="bold cyan")
    for t in templates:
        t_table.add_row(t.replace("_", " ").title())
    console.print(Panel(t_table, title="Available Templates", border_style="cyan"))

    template_id = (await ainput("[cyan]Template ID (e.g. heist): [/cyan]")).strip().lower().replace(" ", "_")
    if not template_id or template_id == "back":
        return
    if template_id not in templates:
        console.print(f"[red]Unknown template '{template_id}'. Available: {', '.join(templates)}[/red]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # Show systems
    _SYSTEMS = ["bitd", "sav", "bob", "candela", "cbrpnk", "dnd5e", "stc", "burnwillow", "crown"]
    console.print(f"[dim]Systems: {', '.join(_SYSTEMS)}[/dim]")
    system_id = (await ainput("[cyan]System ID (e.g. bitd): [/cyan]")).strip().lower()
    if not system_id or system_id == "back":
        return
    if system_id not in _SYSTEMS:
        console.print(f"[red]Unknown system '{system_id}'.[/red]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # Tier
    tier_raw = (await ainput("[cyan]Tier (1-4, default 1): [/cyan]")).strip()
    tier = int(tier_raw) if tier_raw.isdigit() and 1 <= int(tier_raw) <= 4 else 1

    # Seed
    seed_raw = (await ainput("[cyan]Seed (blank for random): [/cyan]")).strip()
    seed = int(seed_raw) if seed_raw.isdigit() else None

    # Generate
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Generating {system_id} {template_id} module...", total=None)
        loop = asyncio.get_event_loop()
        try:
            output_dir = await loop.run_in_executor(
                None,
                lambda: generate_module(template_id, system_id, tier=tier, seed=seed),
            )
            progress.update(task, description="[green]Done!")
        except Exception as e:
            progress.update(task, description=f"[red]Failed: {e}")
            await ainput("\n[dim]Press Enter to continue...[/dim]")
            return

    console.print(Panel(
        f"[bold green]Module generated![/bold green]\n\n"
        f"[dim]Output: {output_dir}[/dim]\n\n"
        f"[dim]You can now play this module from the Chronicles menu,\n"
        f"or enrich it with AI descriptions using the [bold]E[/bold] option.[/dim]",
        border_style="green", box=box.DOUBLE,
    ))
    await ainput("\n[dim]Press Enter to continue...[/dim]")


# ── Module Enrichment ─────────────────────────────────────────────────────

async def run_module_enrichment():
    """Interactive module enrichment — wraps scripts/enrich_module.py."""
    console.clear()
    console.print(Panel(
        "[bold cyan]MODULE ENRICHMENT[/bold cyan]\n\n"
        "[dim]Enrich a module with AI-generated NPC dialogue, room descriptions,\n"
        "event narration, and quest arc weaving. Requires Ollama.\n"
        "Type 'back' to return.[/dim]",
        border_style="cyan", box=box.DOUBLE,
    ))

    try:
        from scripts.enrich_module import enrich_module
    except ImportError:
        console.print("[red]enrich_module.py not found in scripts/.[/red]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # List modules
    modules_dir = Path(__file__).resolve().parent / "vault_maps" / "modules"
    if not modules_dir.is_dir():
        console.print("[yellow]No vault_maps/modules/ directory found.[/yellow]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    module_dirs = sorted([
        d.name for d in modules_dir.iterdir()
        if d.is_dir() and (d / "module_manifest.json").exists()
    ])
    if not module_dirs:
        console.print("[yellow]No modules found. Generate one first.[/yellow]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # Paginated list
    m_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    m_table.add_column("#", style="bold", width=4)
    m_table.add_column("Module ID", style="cyan")
    for i, m in enumerate(module_dirs, 1):
        m_table.add_row(str(i), m)
    console.print(Panel(m_table, title=f"Modules ({len(module_dirs)})", border_style="cyan"))

    selection = (await ainput("[cyan]Module # or ID (e.g. 1 or bitd_heist_99): [/cyan]")).strip()
    if not selection or selection.lower() == "back":
        return

    # Resolve selection
    if selection.isdigit() and 1 <= int(selection) <= len(module_dirs):
        module_id = module_dirs[int(selection) - 1]
    elif selection in module_dirs:
        module_id = selection
    else:
        console.print(f"[red]Module '{selection}' not found.[/red]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    module_path = modules_dir / module_id

    # RAG option
    use_rag_raw = (await ainput("[cyan]Enable RAG (PDF context)? (y/N): [/cyan]")).strip().lower()
    use_rag = use_rag_raw in ("y", "yes")

    # Dry run first
    console.print("\n[dim]Running dry-run to preview enrichment plan...[/dim]")
    try:
        stats = await enrich_module(str(module_path), use_rag=use_rag, dry_run=True)
    except Exception as e:
        console.print(f"[red]Dry-run failed: {e}[/red]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    proceed = (await ainput("[cyan]Proceed with enrichment? (y/N): [/cyan]")).strip().lower()
    if proceed not in ("y", "yes"):
        console.print("[dim]Enrichment cancelled.[/dim]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # Run real enrichment
    console.print()
    console.print(Panel(
        "[bold yellow]Enrichment in progress...[/bold yellow]\n\n"
        "[dim]This may take several minutes on Pi 5.\n"
        "Thermal gating and LLM cooldowns are automatic.[/dim]",
        border_style="yellow",
    ))

    try:
        stats = await enrich_module(str(module_path), use_rag=use_rag, dry_run=False)
        console.print(Panel(
            f"[bold green]Enrichment complete![/bold green]\n\n"
            f"NPCs enriched: {stats.get('npcs_enriched', 0)}/{stats.get('npcs', 0)}\n"
            f"Rooms enriched: {stats.get('rooms_enriched', 0)}/{stats.get('rooms', 0)}\n"
            f"Events enriched: {stats.get('events_enriched', 0)}/{stats.get('events', 0)}\n"
            f"Quest arc: {'yes' if stats.get('quest_arc_enriched') else 'no'}",
            border_style="green", box=box.DOUBLE,
        ))
    except Exception as e:
        console.print(f"[red]Enrichment failed: {e}[/red]")

    await ainput("\n[dim]Press Enter to continue...[/dim]")


async def run_dice_roller():
    """Interactive dice roller using the animated dice engine."""
    console.clear()
    console.print(Panel(
        "[bold cyan]🎲 DICE ROLLER[/bold cyan]\n\n"
        "[dim]Enter dice expressions like: 2d6, 1d20+5, 4d6kh3\n"
        "Type 'back' to return.[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    while True:
        try:
            expr = await ainput("[cyan]Enter dice (e.g., 2d20+5):[/cyan] ")
            expr = expr.strip()

            if not expr or expr.lower() == "back":
                return

            try:
                if DICE_ENGINE_AVAILABLE:
                    total, rolls, modifier = await codex_dice_engine.animate_terminal_roll(expr, console=console)  # type: ignore[union-attr]
                    rolls_display = " + ".join([str(r) for r in rolls])
                    if modifier != 0:
                        mod_str = f"{modifier:+d}"
                        console.print(f"\n[bold green]Final Result:[/bold green] {rolls_display} {mod_str} = {total}")
                    else:
                        console.print(f"\n[bold green]Final Result:[/bold green] {rolls_display} = {total}")
                else:
                    if TOOLS_AVAILABLE:
                        total, result_msg = dm_tools.roll_dice(expr)  # type: ignore[union-attr]
                        console.print(f"[bold green]{result_msg}[/bold green]")
                    else:
                        console.print("[yellow]Dice engine not available.[/yellow]")
            except Exception as e:
                console.print(f"[red]Invalid expression: {e}[/red]")
            console.print()
        except (KeyboardInterrupt, EOFError):
            return


async def run_npc_generator(core: CodexCore):
    """Generate random NPCs using codex_tools."""
    console.clear()
    console.print(Panel(
        "[bold cyan]👤 NPC GENERATOR[/bold cyan]\n\n"
        "[dim]Generate a random NPC with name, personality, and stats.\n"
        "Enter an archetype (e.g., 'Merchant', 'Guard', 'Wizard') or leave blank for random.\n"
        "Type 'back' to return.[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    while True:
        try:
            archetype = await ainput("[cyan]Archetype (or press Enter for random):[/cyan] ")
            archetype = archetype.strip()

            if archetype.lower() == "back":
                return

            if not archetype:
                archetypes = ["Merchant", "Guard", "Wizard", "Thief", "Priest", "Farmer", "Noble"]
                archetype = random.choice(archetypes)

            try:
                npc = dm_tools.generate_npc(archetype)  # type: ignore[union-attr]
                console.print(Panel(
                    npc,
                    border_style="green",
                    title="[bold green]Generated NPC[/bold green]",
                    box=box.ROUNDED
                ))
            except Exception as e:
                console.print(f"[red]Generation failed: {e}[/red]")
            console.print()
        except (KeyboardInterrupt, EOFError):
            return


async def run_loot_generator():
    """Generate random loot using codex_tools."""
    console.clear()
    console.print(Panel(
        "[bold cyan]💰 LOOT GENERATOR[/bold cyan]\n\n"
        "[dim]Generate random treasure and equipment.\n"
        "Enter difficulty (easy/medium/hard) and party size (1-8).\n"
        "Type 'back' to return.[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    while True:
        try:
            difficulty = await ainput("[cyan]Difficulty [easy/medium/hard] (default: medium):[/cyan] ")
            difficulty = difficulty.strip().lower()

            if difficulty == "back":
                return

            if not difficulty:
                difficulty = "medium"

            party_str = await ainput("[cyan]Party size [1-8] (default: 4):[/cyan] ")
            party_str = party_str.strip()

            if party_str.lower() == "back":
                return

            party_size = 4
            if party_str:
                try:
                    party_size = max(1, min(8, int(party_str)))
                except ValueError:
                    console.print("[yellow]Invalid party size, using 4[/yellow]")
                    party_size = 4

            try:
                loot = dm_tools.calculate_loot(difficulty, party_size)  # type: ignore[union-attr]
                console.print(Panel(
                    loot,
                    border_style="gold1",
                    title="[bold gold1]Treasure Found![/bold gold1]",
                    box=box.ROUNDED
                ))
            except Exception as e:
                console.print(f"[red]Generation failed: {e}[/red]")
            console.print()
        except (KeyboardInterrupt, EOFError):
            return


async def run_trap_generator():
    """Generate random traps using codex_tools."""
    console.clear()
    console.print(Panel(
        "[bold cyan]🕳️  TRAP GENERATOR[/bold cyan]\n\n"
        "[dim]Generate deadly traps and hazards.\n"
        "Enter difficulty (easy/medium/hard) or press Enter for random.\n"
        "Type 'back' to return.[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    while True:
        try:
            difficulty = await ainput("[cyan]Difficulty [easy/medium/hard] (or press Enter):[/cyan] ")
            difficulty = difficulty.strip().lower()

            if difficulty == "back":
                return

            if not difficulty:
                difficulty = random.choice(["easy", "medium", "hard"])

            try:
                trap = dm_tools.generate_trap(difficulty)  # type: ignore[union-attr]
                console.print(Panel(
                    trap,
                    border_style="red",
                    title=f"[bold red]Trap Generated (Difficulty: {difficulty.upper()})[/bold red]",
                    box=box.ROUNDED
                ))
            except Exception as e:
                console.print(f"[red]Generation failed: {e}[/red]")
            console.print()
        except (KeyboardInterrupt, EOFError):
            return


async def run_session_notes(core: CodexCore):
    """Display session context summary."""
    console.clear()
    console.print(Panel(
        "[bold cyan]📜 SESSION NOTES[/bold cyan]\n\n"
        "[dim]Paste your session notes to get an AI summary.\n"
        "Enter a blank line when finished, or type 'back' to return.[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    console.print("[green]Paste your session log:[/green]")
    console.print("[dim](Enter a blank line to finish)[/dim]")
    console.print()

    lines = []
    try:
        while True:
            line = await ainput("")
            if not line.strip():
                break
            if line.lower() == "back":
                return
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        return

    if not lines:
        console.print("[yellow]No session notes provided.[/yellow]")
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    history_text = "\n".join(lines)

    try:
        console.print()
        console.print("[cyan]Generating summary...[/cyan]")
        summary = dm_tools.summarize_context(history_text)  # type: ignore[union-attr]
        console.print()
        console.print(Panel(
            summary,
            border_style="grey50",
            title="[bold]Session Summary[/bold]",
            box=box.ROUNDED
        ))
    except Exception as e:
        console.print(f"[red]Could not generate summary: {e}[/red]")

    await ainput("\n[dim]Press Enter to continue...[/dim]")


async def run_encounter_generator():
    """Generate random encounters using dm_tools."""
    console.clear()
    console.print(Panel(
        "[bold cyan]⚔️  ENCOUNTER GENERATOR[/bold cyan]\n\n"
        "[dim]Generate random encounters for any system.\n"
        "Type 'back' to return.[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    while True:
        try:
            system = await ainput("[cyan]System [Burnwillow/DnD5e/CBR_PNK/STC] (default: Burnwillow):[/cyan] ")
            system = system.strip()

            if system.lower() == "back":
                return

            if not system:
                system = "BURNWILLOW"

            tier_str = await ainput("[cyan]Tier [1-4] (default: 1):[/cyan] ")
            if tier_str.lower() == "back":
                return
            tier = 1
            if tier_str.strip():
                try:
                    tier = max(1, min(4, int(tier_str.strip())))
                except ValueError:
                    pass

            party_str = await ainput("[cyan]Party size [1-8] (default: 4):[/cyan] ")
            if party_str.lower() == "back":
                return
            party_size = 4
            if party_str.strip():
                try:
                    party_size = max(1, min(8, int(party_str.strip())))
                except ValueError:
                    pass

            try:
                result = dm_tools.generate_encounter(system, tier, party_size)  # type: ignore[union-attr]
                console.print(Panel(
                    result,
                    border_style="red",
                    title="[bold red]Encounter Generated[/bold red]",
                    box=box.ROUNDED
                ))
            except Exception as e:
                console.print(f"[red]Generation failed: {e}[/red]")
            console.print()
        except (KeyboardInterrupt, EOFError):
            return


async def run_vault_scan():
    """Scan vault PDFs and extract equipment tables."""
    console.clear()
    console.print(Panel(
        "[bold cyan]🔍 VAULT SCANNER[/bold cyan]\n\n"
        "[dim]Extracts equipment tables from vault PDFs into the loot system.\n"
        "This may take a few minutes for large vaults.[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    console.print("[cyan]Scanning vault...[/cyan]")
    try:
        result = dm_tools.scan_vault()  # type: ignore[union-attr]
        console.print(Panel(
            result,
            border_style="green",
            title="[bold green]Scan Complete[/bold green]",
            box=box.ROUNDED
        ))
    except Exception as e:
        console.print(f"[red]Vault scan failed: {e}[/red]")

    await ainput("\n[dim]Press Enter to continue...[/dim]")


# =============================================================================
# MIMIR CHAT MODE
# =============================================================================
async def run_mimir_chat(core: CodexCore):
    """Direct chat with Mimir AI."""
    console.clear()

    console.print(Panel(
        "[bold cyan]MIMIR CHAT MODE[/bold cyan]\n\n"
        "[dim]Speak directly with the AI. Type 'back' to return.[/dim]",
        box=box.DOUBLE,
        border_style=ROYAL_BLUE
    ))
    console.print()

    user_id = "terminal_user"

    while True:
        try:
            user_input = await ainput("[bold green]You:[/bold green] ")

            if not user_input.strip():
                continue

            if user_input.lower() in ('back', 'exit', 'menu', 'quit'):
                console.print("[dim]Returning to main menu...[/dim]")
                return

            # WO 081: Butler intercept — instant response, skip LLM
            butler = getattr(core, 'butler', None)
            if butler:
                reflex = butler.check_reflex(user_input)
                if reflex:
                    console.print(f"[bold cyan]⚡[/bold cyan] {reflex}")
                    console.print()
                    continue

            # Process with Mimir (show thinking indicator)
            console.print("[cyan]Mimir is thinking...[/cyan]")
            response = await core.process_input(user_id, user_input)

            console.print(f"[bold blue]Mimir:[/bold blue] {response}")
            console.print()

        except (KeyboardInterrupt, EOFError):
            return
        except Exception as e:
            console.print(f"[red]Chat Error: {e}[/red]")


# =============================================================================
# CODEX OF CHRONICLES — PLAY TTRPG
# =============================================================================
async def run_codex_chronicles_menu(core: CodexCore):
    """
    Codex of Chronicles — Session hub for TTRPG play.

    Offers:
    [1] Start New Campaign    — Campaign Setup Wizard
    [2] Load Campaign         — Resume from saves/
    [3] Continue Campaign     — New module, same world & party
    [4] Back
    """
    while True:
        try:
            console.clear()
            console.print(Text(TITLE_ART, style=GOLD))

            console.print()
            console.print(Panel(
                "[bold cyan]CODEX OF CHRONICLES[/bold cyan]\n\n"
                "[dim]Begin a new adventure or resume a saved campaign.[/dim]",
                box=box.DOUBLE,
                border_style=EMERALD,
                title="[bold]🐉 CODEX OF CHRONICLES 🐉[/bold]"
            ))
            console.print()

            menu = Table(
                box=box.HEAVY,
                border_style=EMERALD,
                show_header=False,
                padding=(0, 2),
                title="[bold]══════ SELECT OPTION ══════[/bold]",
                title_style=EMERALD
            )

            menu.add_column("Option", style=GOLD)
            menu.add_column("Description", style=PARCHMENT)

            menu.add_row("[1]", "⚔️  Start New Campaign  — Campaign Setup Wizard")
            menu.add_row("[2]", "💾 Load Campaign        — Resume a saved campaign")
            menu.add_row("[3]", "🔄 Continue Campaign    — New module, same world & party")
            menu.add_row("[4]", "↩️  Back to Main Menu   — Return")

            console.print()
            console.print(Align.center(menu))
            console.print()

            choice = await ainput("[gold1]Choose thy path [1/2/3/4]:[/] ")
            choice = choice.lower().strip()

            if not choice:
                continue

            if choice == "1":
                await run_campaign_setup_wizard(core)

            elif choice == "2":
                # Load existing campaign
                console.clear()
                console.print(Panel(
                    "[bold cyan]LOAD CAMPAIGN[/bold cyan]\n\n"
                    "[dim]Select a saved campaign to resume.[/dim]",
                    box=box.DOUBLE,
                    border_style=EMERALD,
                    title="[bold]💾 LOAD CAMPAIGN 💾[/bold]"
                ))
                console.print()

                saves = GameSave.list_saves()
                if not saves:
                    console.print("[yellow]No saved campaigns found in saves/[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")
                    continue

                # Display numbered list
                for i, save in enumerate(saves, 1):
                    created_str = save.created.strftime("%Y-%m-%d %H:%M")
                    console.print(
                        f"[{GOLD}]{i:>2}[/] {save.name.ljust(25)} "
                        f"[dim]World: {save.world.ljust(20)} Created: {created_str}[/dim]"
                    )

                console.print()
                valid_choices = [str(n) for n in range(1, len(saves) + 1)]
                load_choice = await ainput(f"[gold1]Select campaign [1-{len(saves)}] or [B]ack:[/] ")
                load_choice = load_choice.strip()

                if load_choice.lower() == 'b' or load_choice not in valid_choices:
                    continue

                selected_save = saves[int(load_choice) - 1]
                console.print(f"\n[green]Campaign '{selected_save.name}' loaded.[/green]")
                console.print(f"[dim]World: {selected_save.world} | Level: {selected_save.level}[/dim]")
                await ainput("\n[dim]Press Enter to continue...[/dim]")

                # WO 090/103 — Relaunch into the appropriate game engine
                manifest = selected_save.state or {}
                _launch_views()  # WO-V63.0: spawn views when game starts

                # WO-V60.0: Detect stacked (multi-system) saves
                if manifest.get("stacked") and UNIVERSAL_AVAILABLE:
                    butler = getattr(core, 'butler', None)
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, lambda: run_universal_game(  # type: ignore[misc]
                            manifest.get("active_system_id", ""),
                            manifest=manifest, butler=butler)
                    )
                    continue

                system_id = manifest.get("system_id", "").lower()
                is_burnwillow = (
                    selected_save.world.lower() == "burnwillow"
                    or system_id == "burnwillow"
                )

                if is_burnwillow:
                    # Burnwillow: dedicated dungeon crawler
                    _mm_path = manifest.get("module_manifest_path")
                    _bw_stype = manifest.get("session_type")
                    if ADAPTER_AVAILABLE and BURNWILLOW_AVAILABLE and manifest.get("characters"):
                        try:
                            characters = CharacterAdapter.convert_campaign_characters(manifest)  # type: ignore[union-attr]
                            butler = getattr(core, 'butler', None)
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(
                                None,
                                lambda: run_burnwillow_game(  # type: ignore[misc]
                                    butler=butler, characters=characters,
                                    module_manifest_path=_mm_path,
                                    session_type=_bw_stype)
                            )
                        except Exception as e:
                            console.print(f"[red]Failed to load characters: {e}[/red]")
                            await ainput("\n[dim]Press Enter to continue...[/dim]")
                    elif BURNWILLOW_AVAILABLE:
                        butler = getattr(core, 'butler', None)
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None, lambda: run_burnwillow_game(  # type: ignore[misc]
                                butler=butler, module_manifest_path=_mm_path,
                                session_type=_bw_stype)
                        )
                    else:
                        console.print("[yellow]Burnwillow module not available.[/yellow]")
                        await ainput("\n[dim]Press Enter to continue...[/dim]")
                elif system_id in ("crown", "ashburn"):
                    # Crown & Crew / Ashburn
                    _crown_campaign_data: Optional[dict] = None
                    _crown_module_path = manifest.get("module_manifest_path")
                    if _crown_module_path:
                        try:
                            from pathlib import Path as _Path
                            import json as _json
                            _campaign_json = _Path(_crown_module_path).parent / "campaign.json"
                            if _campaign_json.exists():
                                with open(_campaign_json, encoding="utf-8") as _f:
                                    _crown_campaign_data = _json.load(_f)
                        except Exception:
                            pass
                    await run_crown_campaign(
                        world_state=selected_save.state or None,
                        mimir=getattr(core, 'architect', None),
                        butler=getattr(core, 'butler', None),
                        campaign_data=_crown_campaign_data,
                    )
                elif UNIVERSAL_AVAILABLE:
                    # Resolve sub-setting for registry lookup (e.g. stc_roshar -> stc)
                    _load_routing_id = system_id
                    if "_" in system_id:
                        _lp = system_id.split("_", 1)[0]
                        if _lp in ENGINE_REGISTRY:
                            _load_routing_id = _lp
                    if _load_routing_id in ENGINE_REGISTRY:
                        # Universal engine loop (FITD, DnD5e, Cosmere, etc.)
                        butler = getattr(core, 'butler', None)
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None, lambda: run_universal_game(system_id, manifest=manifest, butler=butler)  # type: ignore[misc]
                        )
                    else:
                        console.print(f"[yellow]No game loop available for '{system_id}'.[/yellow]")
                        await ainput("\n[dim]Press Enter to continue...[/dim]")
                else:
                    console.print(f"[yellow]No game loop available for '{system_id}'.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "3":
                # Continue Campaign — load save, pick new module, keep characters
                saves = GameSave.list_saves()
                if not saves:
                    console.print("[yellow]No saved campaigns found.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")
                    continue

                console.print(Panel(
                    "[bold cyan]CONTINUE CAMPAIGN[/bold cyan]\n\n"
                    "Select a completed campaign to continue with a new module.\n"
                    "Characters and history carry forward.",
                    box=box.DOUBLE, border_style="cyan",
                    title="[bold]NEW MODULE, SAME WORLD[/bold]"
                ))

                for i, save in enumerate(saves, 1):
                    created_str = save.created.strftime("%Y-%m-%d %H:%M")
                    console.print(
                        f"[{GOLD}]{i:>2}[/] {save.name.ljust(25)} "
                        f"[dim]World: {save.world.ljust(20)} Created: {created_str}[/dim]"
                    )

                console.print()
                load_choice = await ainput(f"[gold1]Select campaign [1-{len(saves)}] or [B]ack:[/] ")
                load_choice = load_choice.strip()
                if load_choice.lower() == 'b' or load_choice not in [str(n) for n in range(1, len(saves) + 1)]:
                    continue

                selected_save = saves[int(load_choice) - 1]
                manifest = selected_save.state or {}
                system_id = manifest.get("system_id", "").lower()

                if not system_id:
                    console.print("[yellow]This save has no system_id — cannot continue.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")
                    continue

                # Resolve routing id for universal engine
                _routing_id = system_id
                if "_" in system_id:
                    _p = system_id.split("_", 1)[0]
                    if _p in ENGINE_REGISTRY:
                        _routing_id = _p

                if not UNIVERSAL_AVAILABLE or _routing_id not in ENGINE_REGISTRY:
                    console.print(f"[yellow]Continue Campaign requires the universal engine for '{system_id}'.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")
                    continue

                # Clear old module path so play_universal offers the module picker
                manifest.pop("module_manifest_path", None)
                manifest["continue_campaign"] = True

                console.print(f"\n[green]Continuing '{selected_save.name}' with a new module...[/green]")
                _launch_views()
                butler = getattr(core, 'butler', None)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: run_universal_game(system_id, manifest=manifest, butler=butler)  # type: ignore[misc]
                )

            elif choice == "4":
                return

        except KeyboardInterrupt:
            console.print("\n[yellow]Returning to main menu...[/yellow]")
            return


async def run_campaign_setup_wizard(core: CodexCore):
    """
    Campaign Setup Wizard — Setting-First guided flow for starting a new TTRPG session.

    Steps:
    1. Number of players
    2. Select game system (dynamically scanned from vault/)
    3. Select base setting (sourcebook from vault/{system}/SOURCE)
    4. Select adventure module (from vault/{system}/MODULES, or custom text)
    5. Character creation loop (one per player via CharacterBuilderEngine)
    6. Save campaign manifest with world_layers to saves/{campaign_name}/

    Type 'back' at any step to return to the previous question.

    The manifest uses a world_layers list (base setting + active module) to support
    the future Dynamic History Merger — layered world state across campaigns.
    """
    console.clear()
    console.print(Text(TITLE_ART, style=GOLD))

    console.print()
    console.print(Panel(
        "[bold cyan]CAMPAIGN SETUP WIZARD[/bold cyan]\n\n"
        "[dim]Answer a few questions and Mimir will prepare your session.\n"
        "Type 'back' at any step to return to the previous question.[/dim]",
        box=box.DOUBLE,
        border_style=EMERALD,
        title="[bold]⚔️  NEW CAMPAIGN ⚔️[/bold]"
    ))
    console.print()

    # --- Check prerequisites ---
    if not FORGE_AVAILABLE:
        console.print(Panel(
            "[yellow]Character Forge module not available.[/yellow]\n\n"
            "[dim]Ensure codex_char_wizard.py is present in the Codex directory.[/dim]",
            border_style="yellow"
        ))
        await ainput("\n[dim]Press Enter to continue...[/dim]")
        return

    # State machine for back navigation
    num_players = 1
    selected_schema = None
    vault_path = None
    vault_content = {}
    setting_name = None
    setting_file = None
    module_name = None
    module_file = None
    _selected_module_id = None  # module_id from vault_maps/modules/ selection
    _is_homebrew = False   # True when user picks Homebrew in step 3
    _is_freeform = False   # True when user picks Freeform in step 4
    _genesis_world: dict = {}  # Populated by genesis prompt after step 4
    step = 1

    while step <= 4:
        # --- Step 1: Number of Players ---
        if step == 1:
            console.print("[bold]Step 1/4:[/bold] How many players at the table? [dim](or 'back' to cancel)[/dim]")
            num_players_str = await ainput("[gold1]Number of players [1-6]:[/] ")
            if num_players_str.strip().lower() in ("back", "b"):
                return  # Can't go further back — exit wizard
            try:
                num_players = int(num_players_str.strip())
                num_players = max(1, min(6, num_players))
            except (ValueError, AttributeError):
                num_players = 1
            console.print(f"[green]{num_players} player(s) confirmed.[/green]\n")
            step = 2
            continue

        # --- Step 2: Select Game System ---
        if step == 2:
            console.print("[bold]Step 2/4:[/bold] Choose a game system. [dim](or 'back')[/dim]\n")

            engine = CharacterBuilderEngine()  # type: ignore[misc]
            all_systems = engine.list_systems()

            if not all_systems:
                console.print(Panel(
                    "[yellow]No game systems found in vault/.[/yellow]\n\n"
                    "[dim]Add a folder with creation_rules.json to vault/ to register a system.[/dim]",
                    border_style="yellow"
                ))
                await ainput("\n[dim]Press Enter to continue...[/dim]")
                return

            # Filter out sub-settings — they appear via secondary prompt
            systems = [s for s in all_systems if not s.setting_id]
            sub_settings = [s for s in all_systems if s.parent_engine and s.setting_id]

            sys_table = Table(box=box.ROUNDED, border_style=ROYAL_BLUE, title="[bold]Available Systems[/bold]")
            sys_table.add_column("#", style=GOLD, width=3)
            sys_table.add_column("System", style=EMERALD)
            sys_table.add_column("Genre", style=SILVER)

            # Load branding for family annotations
            _branding = {}
            try:
                import json as _json
                _brand_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "branding_registry.json")
                with open(_brand_path) as _bf:
                    _branding = _json.load(_bf)
            except Exception:
                pass

            for i, schema in enumerate(systems, 1):
                sid = schema.system_id.upper()
                brand = _branding.get(sid, {})
                family = brand.get("system_family", "")
                if family:
                    parent_name = family.replace("_", " ").title()
                    sys_table.add_row(str(i), f"{schema.display_name} [dim]({parent_name} expansion)[/dim]", schema.genre)
                else:
                    sys_table.add_row(str(i), schema.display_name, schema.genre)

            console.print(sys_table)
            console.print()

            sys_choice = await ainput(f"[gold1]Select system [1-{len(systems)}]:[/] ")
            if sys_choice.strip().lower() in ("back", "b"):
                step = 1
                continue
            try:
                sys_idx = int(sys_choice.strip()) - 1
                if sys_idx < 0 or sys_idx >= len(systems):
                    sys_idx = 0
            except (ValueError, AttributeError):
                sys_idx = 0

            selected_schema = systems[sys_idx]

            # Sub-setting prompt if applicable
            child_settings = [s for s in sub_settings if s.parent_engine == selected_schema.system_id]
            if child_settings:
                console.print(f"\n[bold]{selected_schema.display_name} — Choose Setting[/bold]")
                console.print(f"  [dim]1.[/dim] All {selected_schema.display_name} content")
                for j, cs in enumerate(child_settings, 2):
                    console.print(f"  [dim]{j}.[/dim] {cs.display_name} — {cs.genre}")
                sub_choice = await ainput(f"[gold1]Select setting [1-{len(child_settings) + 1}]:[/] ")
                try:
                    sub_idx = int(sub_choice.strip())
                    if 2 <= sub_idx <= len(child_settings) + 1:
                        selected_schema = child_settings[sub_idx - 2]
                except (ValueError, AttributeError):
                    pass
            assert selected_schema is not None
            vault_path = selected_schema.vault_path
            console.print(f"[green]System: {selected_schema.display_name}[/green]\n")
            step = 3
            continue

        # --- Step 3: Select Setting ---
        if step == 3:
            assert selected_schema is not None
            # If sub-setting already selected in Step 2.5, skip to Step 4
            if selected_schema.setting_id:
                setting_name = selected_schema.display_name
                step = 4
                continue
            console.print("[bold]Step 3/4:[/bold] Select Setting. [dim](or 'back')[/dim]\n")

            # Gather settings from the vault (with parent merge for sub-settings)
            setting_options = []  # list of {"name": ..., "path": ...}
            if FORGE_AVAILABLE:
                _parent_vault = None
                if selected_schema.parent_engine:
                    _pv = Path(vault_path or "").parent
                    if _pv.is_dir() and _pv.name != "vault":
                        _parent_vault = str(_pv)
                vault_content = scan_system_content(vault_path or "", parent_path=_parent_vault or "")  # type: ignore[union-attr]
                setting_options = list(vault_content.get("settings", []))

            setting_name = None
            setting_file = None

            # Build numbered table: vault settings + Homebrew at the end
            set_table = Table(box=box.ROUNDED, border_style=ROYAL_BLUE, title="[bold]Available Settings[/bold]")
            set_table.add_column("#", style=GOLD, width=3)
            set_table.add_column("Setting", style=EMERALD)

            for i, opt in enumerate(setting_options, 1):
                set_table.add_row(str(i), opt["name"])
            homebrew_idx = len(setting_options) + 1
            set_table.add_row(str(homebrew_idx), "[dim]Homebrew[/dim]")

            console.print(set_table)
            console.print()

            set_choice = await ainput(f"[gold1]Select setting [1-{homebrew_idx}]:[/] ")
            if set_choice.strip().lower() in ("back", "b"):
                step = 2
                continue
            try:
                set_idx = int(set_choice.strip()) - 1
                if 0 <= set_idx < len(setting_options):
                    setting_name = setting_options[set_idx]["name"]
                    setting_file = os.path.basename(setting_options[set_idx].get("path", ""))
            except (ValueError, AttributeError):
                pass

            if setting_name is None:
                # Homebrew selected (or invalid input defaults to Homebrew)
                custom = await ainput("[gold1]Setting name[/] [Homebrew]: ")
                if custom.strip().lower() in ("back", "b"):
                    step = 2
                    continue
                setting_name = custom.strip() if custom.strip() else "Homebrew"
                _is_homebrew = True

            console.print(f"[green]Setting: {setting_name}[/green]\n")
            step = 4
            continue

        # --- Step 4: Select Module ---
        if step == 4:
            assert selected_schema is not None
            console.print(f"[bold]Step 4/4:[/bold] Select Adventure Module for {setting_name}. [dim](or 'back')[/dim]\n")

            # Gather modules from the vault (reuse scan if available, with parent merge)
            module_options = []  # list of {"name": ..., "path": ...}
            if FORGE_AVAILABLE:
                if not vault_content:
                    _parent_vault = None
                    if selected_schema.parent_engine:
                        _pv = Path(vault_path or "").parent
                        if _pv.is_dir() and _pv.name != "vault":
                            _parent_vault = str(_pv)
                    vault_content = scan_system_content(vault_path or "", parent_path=_parent_vault or "")  # type: ignore[union-attr]
                module_options = list(vault_content.get("modules", []))

            # Also scan vault_maps/modules/ for adventure modules matching this system
            _sys_id = selected_schema.system_id.lower()
            _modules_dir = CODEX_DIR / "vault_maps" / "modules"
            _seen_names = {m["name"] for m in module_options}
            if _modules_dir.is_dir():
                for _entry in sorted(_modules_dir.iterdir()):
                    if not _entry.is_dir():
                        continue
                    _mf = _entry / "module_manifest.json"
                    if not _mf.exists():
                        continue
                    try:
                        _mdata = json.loads(_mf.read_text())
                        if _mdata.get("system_id") != _sys_id:
                            continue
                        _dname = _mdata.get("display_name", _entry.name)
                        if _dname in _seen_names:
                            continue
                        _seen_names.add(_dname)
                        module_options.append({
                            "name": _dname,
                            "path": str(_mf),
                            "module_id": _mdata.get("module_id", _entry.name),
                        })
                    except (json.JSONDecodeError, KeyError):
                        continue

            module_name = None
            module_file = None

            # Build numbered table: vault modules + Freeform at the end
            mod_table = Table(box=box.ROUNDED, border_style=ROYAL_BLUE, title="[bold]Available Modules[/bold]")
            mod_table.add_column("#", style=GOLD, width=3)
            mod_table.add_column("Module", style=EMERALD)

            for i, opt in enumerate(module_options, 1):
                mod_table.add_row(str(i), opt["name"])
            freeform_idx = len(module_options) + 1
            mod_table.add_row(str(freeform_idx), "[dim]Freeform[/dim]")

            console.print(mod_table)
            console.print()

            _selected_module_id = None  # Track module_id for vault_maps modules
            mod_choice = await ainput(f"[gold1]Select module [1-{freeform_idx}]:[/] ")
            if mod_choice.strip().lower() in ("back", "b"):
                step = 3
                continue
            try:
                mod_idx = int(mod_choice.strip()) - 1
                if 0 <= mod_idx < len(module_options):
                    module_name = module_options[mod_idx]["name"]
                    module_file = os.path.basename(module_options[mod_idx].get("path", ""))
                    _selected_module_id = module_options[mod_idx].get("module_id")
            except (ValueError, AttributeError):
                pass

            if module_name is None:
                # Freeform selected (or invalid input defaults to Freeform)
                custom = await ainput("[gold1]Module name[/] [Freeform]: ")
                if custom.strip().lower() in ("back", "b"):
                    step = 3
                    continue
                module_name = custom.strip() if custom.strip() else "Freeform"
                _is_freeform = True

            console.print(f"[green]Module: {module_name}[/green]\n")
            step = 5  # Break out of the step loop

    # --- Step 4b: Procedural World Generation (Homebrew / Freeform only) ---
    if _is_homebrew or _is_freeform:
        console.print()
        _gen_choice = await ainput("[gold1]Generate a procedural world? [Y/n]:[/] ")
        if _gen_choice.strip().lower() not in ("n", "no"):
            try:
                from codex.world.genesis import GenesisEngine
                _ge = GenesisEngine()
                if not _ge.data:
                    console.print("[yellow]Genesis data unavailable — skipping world generation.[/yellow]")
                else:
                    console.print("[dim]Rolling the world...[/dim]")
                    _genesis_world = _ge.roll_unified_world()
                    _ge.display_world(_genesis_world)
                    # Show world primer in a panel
                    console.print(Panel(
                        _genesis_world.get("primer", ""),
                        title="[bold]World Primer[/bold]",
                        border_style="grey50",
                        width=70,
                    ))
                    console.print(f"[green]World '{_genesis_world['name']}' generated![/green]\n")
            except Exception as _ge_err:
                console.print(f"[yellow]World generation skipped: {_ge_err}[/yellow]")

    # --- Step 5: Character Creation Loop ---
    assert selected_schema is not None
    console.print(Panel(
        f"[bold cyan]CHARACTER CREATION[/bold cyan]\n\n"
        f"[dim]{num_players} player(s) will now create characters using the "
        f"{selected_schema.display_name} system.[/dim]",
        box=box.DOUBLE,
        border_style=EMERALD
    ))
    console.print()

    characters = []
    loop = asyncio.get_event_loop()

    for player_num in range(1, num_players + 1):
        console.print(Panel(
            f"[bold gold1]Player {player_num}, step up to the forge.[/bold gold1]",
            border_style=GOLD
        ))
        ready_input = await ainput("[dim]Press Enter when ready (or 'back' to cancel)...[/dim]")
        if ready_input.strip().lower() in ("back", "b"):
            console.print("[dim]Returning to campaign setup...[/dim]")
            return

        # SystemBuilder.run() is synchronous (uses Prompt.ask) — run in executor
        def _build_character(schema=selected_schema):
            from rich.console import Console as RichConsole
            build_console = RichConsole()
            builder = SystemBuilder(schema, build_console)  # type: ignore[misc]
            try:
                sheet = builder.run()
            except SystemBuilder._BackStep:
                return None  # User backed out at step 1
            return sheet, schema

        result = await loop.run_in_executor(None, _build_character)
        if result is None:
            console.print("[dim]Returning to campaign setup...[/dim]")
            return
        sheet, schema = result

        # Display the finished character
        console.print()
        panel = render_character(sheet, schema)  # type: ignore[misc]
        console.print(panel)
        console.print()

        characters.append({
            "player": player_num,
            "system_id": sheet.system_id,
            "name": sheet.name,
            "choices": sheet.choices,
            "stats": sheet.stats,
        })

        console.print(f"[green]Character '{sheet.name}' forged![/green]\n")

    # --- Step 5b: Group Creation (Circle/Crew/Ship/Legion) ---
    # Run once after all characters, since the group is shared
    _group_data: dict = {}
    if selected_schema.derived and any(
        k.endswith("_creation") for k in selected_schema.derived
    ):
        def _build_group(schema=selected_schema):
            from rich.console import Console as RichConsole
            build_console = RichConsole()
            builder = SystemBuilder(schema, build_console)
            return builder.run_group_creation()

        _group_data = await loop.run_in_executor(None, _build_group)
        if _group_data:
            console.print(f"[green]Group forged![/green]\n")

    # --- Step 5c: AI Companion ---
    _ai_companion = None
    console.print(Panel(
        "[bold gold1]AI COMPANION[/bold gold1]\n"
        "[dim]Would you like an AI companion to join your party?\n"
        "They act autonomously, offering advice and taking actions in play.[/dim]",
        border_style=GOLD
    ))
    companion_choice = await ainput("[gold1]Add AI companion? [y/N]:[/] ")
    if companion_choice.strip().lower() in ("y", "yes"):
        try:
            from codex.core.companion_maps import get_personality_pool
            import random as _rng
            # Get system-appropriate companion pool
            _sys_id = selected_schema.system_id
            _pool = get_personality_pool(_sys_id)
            # Let the player choose a companion archetype
            console.print("[bold]Choose a companion:[/bold]")
            for ci, cp in enumerate(_pool, 1):
                console.print(
                    f"  [{ci}] [bold]{cp['archetype'].title()}[/bold] — {cp['description']}"
                    f"\n      [dim]{cp['quirk']}[/dim]"
                )
            _cp_choice = await ainput(
                f"[gold1]Select companion [1-{len(_pool)}]:[/] "
            )
            try:
                _cp_idx = int(_cp_choice.strip()) - 1
                _picked = _pool[max(0, min(_cp_idx, len(_pool) - 1))]
            except (ValueError, IndexError):
                _picked = _rng.choice(_pool)
            _ai_companion = {
                "archetype": _picked["archetype"],
                "personality": _picked["archetype"],
                "description": _picked["description"],
                "quirk": _picked.get("quirk", ""),
                "aggression": _picked.get("aggression", 0.5),
                "curiosity": _picked.get("curiosity", 0.5),
                "caution": _picked.get("caution", 0.5),
                "enabled": True,
            }
            console.print(
                f"[green]Companion '{_picked['archetype'].title()}' will join your party![/green]\n"
                f"[dim]{_picked['description']}[/dim]\n"
            )
        except Exception as e:
            console.print(f"[yellow]Companion unavailable: {e}[/yellow]\n")

    # --- Step 5d: DM Influence (Session Dials) ---
    _dm_influence = {"tone": 0.5, "ruthlessness": 0.5, "narration_style": "balanced", "custom_directives": []}
    try:
        # Load system defaults from GM profile
        _gm_profiles_path = Path(__file__).parent / "codex" / "core" / "services" / "system_gm_profiles.json"
        if _gm_profiles_path.exists():
            import json as _json_dm
            _gm_data = _json_dm.loads(_gm_profiles_path.read_text())
            _sys_profile = _gm_data.get(selected_schema.system_id, {})
            _dm_influence["tone"] = _sys_profile.get("default_tone_value", 0.5)
            _dm_influence["ruthlessness"] = _sys_profile.get("default_ruthlessness", 0.5)
            _gm_title = _sys_profile.get("gm_title", "Game Master")
        else:
            _gm_title = "Game Master"

        console.print(Panel(
            f"[bold gold1]SESSION DIALS[/bold gold1]\n"
            f"[dim]Adjust how your {_gm_title} runs this campaign.\n"
            f"Press Enter to accept defaults.[/dim]",
            border_style=GOLD
        ))

        # Tone slider
        _tone_label = {0: "Grimdark", 0.25: "Grim", 0.5: "Balanced", 0.75: "Heroic", 1.0: "Whimsical"}
        _current_tone = _dm_influence["tone"]
        _tone_desc = min(_tone_label.items(), key=lambda x: abs(x[0] - _current_tone))[1]
        _tone_input = await ainput(
            f"[gold1]Tone[/] [dim](0=Grimdark, 0.5=Balanced, 1=Whimsical)[/dim] [{_tone_desc} ({_current_tone})]: "
        )
        if _tone_input.strip():
            try:
                _dm_influence["tone"] = max(0.0, min(1.0, float(_tone_input.strip())))
            except ValueError:
                pass

        # Ruthlessness slider
        _ruth_input = await ainput(
            f"[gold1]Ruthlessness[/] [dim](0=Lenient, 0.5=Fair, 1=Merciless)[/dim] [{_dm_influence['ruthlessness']}]: "
        )
        if _ruth_input.strip():
            try:
                _dm_influence["ruthlessness"] = max(0.0, min(1.0, float(_ruth_input.strip())))
            except ValueError:
                pass

        # Narration style
        _style_input = await ainput(
            "[gold1]Narration style[/] [dim](terse/balanced/descriptive)[/dim] [balanced]: "
        )
        if _style_input.strip().lower() in ("terse", "balanced", "descriptive"):
            _dm_influence["narration_style"] = _style_input.strip().lower()

        # Custom directives
        _dir_input = await ainput(
            "[gold1]Custom directives[/] [dim](optional, e.g. 'lean into body horror')[/dim]: "
        )
        if _dir_input.strip():
            _dm_influence["custom_directives"] = [d.strip() for d in _dir_input.split(",") if d.strip()]

    except Exception:
        pass

    # --- Step 6: Save Campaign ---
    default_campaign = f"{setting_name}_{module_name}".replace(" ", "_")
    campaign_name = await ainput(f"[gold1]Name this campaign[/] [{default_campaign}]: ")
    if not campaign_name or not campaign_name.strip():
        campaign_name = default_campaign
    campaign_name = campaign_name.strip().replace(" ", "_")

    # Create campaign directory under saves/
    campaign_dir = CODEX_DIR / "saves" / campaign_name
    campaign_dir.mkdir(parents=True, exist_ok=True)

    # Save campaign manifest
    manifest = {
        "campaign_name": campaign_name,
        "system_id": selected_schema.system_id,
        "system_name": selected_schema.display_name,
        "world_layers": [
            {"layer": 0, "type": "base", "name": setting_name, "file": setting_file},
            {"layer": 1, "type": "module", "name": module_name, "file": module_file},
        ],
        "num_players": num_players,
        "characters": characters,
        "memory_shards": [],
        "session_type": None,  # WO-V63.0: Persisted when game engine starts
        "created": datetime.now().isoformat(),
        "group_data": _group_data or {},
        "ai_companion": _ai_companion,
        "dm_influence": _dm_influence,
    }

    # Embed procedural world data when genesis was run
    if _genesis_world:
        manifest["world_primer"] = _genesis_world.get("primer", "")
        manifest["world_name"] = _genesis_world.get("name", "")
        manifest["world_genre"] = _genesis_world.get("genre", "")
        manifest["world_tone"] = _genesis_world.get("tone", "")
        manifest["world_grapes"] = _genesis_world.get("grapes", {})
        manifest["world_faction"] = _genesis_world.get("faction", {})

    # Resolve module_manifest.json for spatial zone progression
    if module_name:
        # Prefer module_id from selection (exact dir match), fall back to slug
        _mod_slug = (
            _selected_module_id
            if _selected_module_id
            else module_name.lower().replace(" ", "_").replace("'", "")
        )
        _mod_manifest = CODEX_DIR / "vault_maps" / "modules" / _mod_slug / "module_manifest.json"
        if _mod_manifest.exists():
            manifest["module_manifest_path"] = str(_mod_manifest)

    manifest_path = campaign_dir / "campaign.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Also save individual character sheets
    for char_data in characters:
        char_path = campaign_dir / f"{char_data['system_id']}_{char_data['name']}.json"
        with open(char_path, "w") as f:
            json.dump(char_data, f, indent=2)

    console.print()
    console.print(Panel(
        f"[bold green]Campaign '{campaign_name}' created![/bold green]\n\n"
        f"[dim]System:[/dim] {selected_schema.display_name}\n"
        f"[dim]Base Setting:[/dim] {setting_name}\n"
        f"[dim]Active Module:[/dim] {module_name}\n"
        f"[dim]Players:[/dim] {num_players}\n"
        f"[dim]Characters:[/dim] {', '.join(c['name'] for c in characters)}\n\n"
        f"[dim]Saved to:[/dim] {campaign_dir}/",
        box=box.DOUBLE,
        border_style=EMERALD,
        title="[bold]CAMPAIGN FORGED[/bold]"
    ))

    # --- Step 6b: Synthesize Character Introductions ---
    try:
        from codex.core.services.opening_narration import get_gm_title
        _gm_title = get_gm_title(selected_schema.system_id)
        _sys_id = selected_schema.system_id

        # Build character context for Mimir
        _char_summaries = []
        for c in characters:
            _ch = c.get("choices", c)
            _role = _ch.get("role", "")
            if isinstance(_role, dict):
                _role = _role.get("value", _role.get("label", ""))
            _spec = _ch.get("specialty", "")
            _style = _ch.get("style", "")
            _catalyst = _ch.get("catalyst", "")
            _pronouns = _ch.get("pronouns", "they/them")
            _name = _ch.get("name", c.get("name", "Unknown"))
            _summary = f"{_name} ({_role}"
            if _spec:
                _summary += f"/{_spec}"
            _summary += f", {_pronouns})"
            if _style:
                _summary += f" — {_style[:80]}"
            _char_summaries.append(_summary)

        # Add AI companion if present
        if _ai_companion and _ai_companion.get("enabled"):
            _comp_arch = _ai_companion.get("archetype", "companion").title()
            _comp_desc = _ai_companion.get("description", "")
            _char_summaries.append(f"AI Companion ({_comp_arch}) — {_comp_desc[:60]}")

        # Group context
        _group_context = ""
        if _group_data:
            _circle = _group_data.get("circle_name", "")
            _cq = _group_data.get("circle_question", "")
            if _circle:
                _group_context = f"Circle: {_circle}. "
            if _cq:
                _group_context += f"Shared history: {_cq}. "

        # Synthesize introductions via Mimir
        _intro_prompt = (
            f"You are the {_gm_title}. Introduce these characters as they appear "
            f"in the opening scene of a {selected_schema.display_name} session. "
            f"{_group_context}"
            f"Write 1-2 sentences per character placing them in the scene. "
            f"Use their style and role to color the description. Stay in character.\n\n"
            + "\n".join(_char_summaries)
        )

        console.print()
        console.print("[dim]Synthesizing character introductions...[/dim]")

        _intro_text = ""
        try:
            from codex.integrations.mimir import query_mimir
            _intro_text = query_mimir(_intro_prompt)
            # Validate — reject AI meta-commentary
            if _intro_text and isinstance(_intro_text, str):
                _reject = ["as an ai", "i cannot", "language model", "certainly!"]
                if any(r in _intro_text.lower() for r in _reject):
                    _intro_text = ""
        except Exception:
            pass

        # Fallback: template-based introduction
        if not _intro_text:
            _intro_lines = []
            for c in characters:
                _ch = c.get("choices", c)
                _name = _ch.get("name", c.get("name", "Unknown"))
                _role = _ch.get("role", "")
                if isinstance(_role, dict):
                    _role = _role.get("value", "")
                _spec = _ch.get("specialty", "")
                _style = _ch.get("style", "")
                _line = f"{_name}, {_role}"
                if _spec:
                    _line += f" ({_spec})"
                if _style:
                    _line += f" — {_style[:100]}"
                _intro_lines.append(_line)
            _intro_text = "\n".join(_intro_lines)

        if _intro_text:
            manifest["character_introductions"] = _intro_text
            # Re-save manifest with introductions
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            console.print(Panel(
                _intro_text,
                title=f"[bold]{_gm_title}[/bold] — Character Introductions",
                border_style="yellow",
            ))

    except Exception:
        pass

    # --- Step 7: Prologue Trigger (WO 080) ---
    console.print()
    console.print(Panel(
        "[bold gold1]PHASE 2: THE PROLOGUE[/bold gold1]\n"
        "Do you wish to run 'Session 0' (Crown & Crew)?",
        border_style=GOLD
    ))
    prologue_choice = await ainput("[gold1]Run Prologue? [Y/n]:[/] ")
    if prologue_choice.strip().lower() != 'n':
        console.print("[green]Initializing Prologue Engine...[/green]")
        manifest['prologue_pending'] = True
        manifest['prologue_context'] = {
            "villain": "The Cult of the Dragon" if "Tyranny" in (module_name or "") else "The Shadow",
            "threat": "Cultists" if "Tyranny" in (module_name or "") else "Bandits",
            "region": "Greenest" if "Tyranny" in (module_name or "") else "The Wilds",
            "mentor": "Governor Nighthill" if "Tyranny" in (module_name or "") else "The Old Man",
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        console.print("[dim]Prologue queued for next load.[/dim]")

    # --- Step 8: Auto-Launch Game ---
    system_id = selected_schema.system_id.lower()
    # Resolve sub-setting system_ids for routing (e.g. "stc_roshar" -> "stc")
    _routing_id = system_id
    if "_" in system_id and UNIVERSAL_AVAILABLE:
        _parent = system_id.split("_", 1)[0]
        if _parent in ENGINE_REGISTRY:
            _routing_id = _parent
    butler = getattr(core, 'butler', None)

    await ainput("\n[dim]Press Enter to launch your campaign...[/dim]")

    # WO-V63.0: Run pending prologue before main game
    if manifest.get('prologue_pending'):
        console.print(Panel("[bold gold1]Running Prologue: Crown & Crew Session 0[/bold gold1]",
                            border_style=GOLD))
        try:
            _pro_mimir = getattr(core, 'architect', None)
            _pro_world = manifest.get("prologue_context", {})
            await run_crown_campaign(
                world_state=_pro_world, mimir=_pro_mimir, butler=butler,
            )
            manifest['prologue_pending'] = False
            manifest['prologue_complete'] = True
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            console.print("[green]Prologue complete! Launching main campaign...[/green]")
            await ainput("\n[dim]Press Enter to continue to main campaign...[/dim]")
        except Exception as e:
            console.print(f"[yellow]Prologue skipped: {e}[/yellow]")
            manifest['prologue_pending'] = False

    if _routing_id in ("crown", "ashburn"):
        # Crown & Crew / Ashburn: narrative-only engine
        mimir = getattr(core, 'architect', None)
        world_state = manifest.get("prologue_context")
        # Load campaign.json from module directory if one is referenced
        _crown_cd: Optional[dict] = None
        _crown_mp = manifest.get("module_manifest_path")
        if _crown_mp:
            try:
                from pathlib import Path as _CPath
                import json as _cjson
                _cj = _CPath(_crown_mp).parent / "campaign.json"
                if _cj.exists():
                    with open(_cj, encoding="utf-8") as _cf:
                        _crown_cd = _cjson.load(_cf)
            except Exception:
                pass
        await run_crown_campaign(
            world_state=world_state, mimir=mimir, butler=butler,
            campaign_data=_crown_cd,
        )
    elif _routing_id == "burnwillow" and BURNWILLOW_AVAILABLE:
        # Burnwillow: dedicated dungeon crawler
        console.print("[green]Launching Burnwillow...[/green]")
        _mm_path = manifest.get("module_manifest_path")
        loop = asyncio.get_event_loop()
        if ADAPTER_AVAILABLE and characters:
            try:
                bw_chars = CharacterAdapter.convert_campaign_characters(manifest)  # type: ignore[union-attr]
                await loop.run_in_executor(
                    None, lambda: run_burnwillow_game(  # type: ignore[misc]
                        butler=butler, characters=bw_chars,
                        module_manifest_path=_mm_path)
                )
            except Exception as e:
                console.print(f"[red]Character conversion failed: {e}[/red]")
                await loop.run_in_executor(
                    None, lambda: run_burnwillow_game(  # type: ignore[misc]
                        butler=butler, module_manifest_path=_mm_path)
                )
        else:
            await loop.run_in_executor(
                None, lambda: run_burnwillow_game(  # type: ignore[misc]
                    butler=butler, module_manifest_path=_mm_path)
            )
    elif UNIVERSAL_AVAILABLE and (_routing_id in ENGINE_REGISTRY or system_id in ENGINE_REGISTRY):
        # Universal engine loop (FITD, DnD5e, Cosmere, etc.)
        # Pass original system_id so play_universal can resolve sub-settings
        console.print(f"[green]Launching {system_id.upper()} engine...[/green]")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: run_universal_game(system_id, manifest=manifest, butler=butler)  # type: ignore[misc]
        )
    else:
        console.print(f"[yellow]No game loop available for '{system_id}'.[/yellow]")


# =============================================================================
# CROWN & CREW SUB-MENU
# =============================================================================
async def run_crown_crew_menu(core: CodexCore):
    """
    Crown & Crew System sub-menu.

    Displays options for:
    - Standard Crown & Crew campaign
    - Ashburn High expansion
    """
    while True:
        try:
            console.clear()
            console.print(Text(TITLE_ART, style=GOLD))

            console.print()
            console.print(Panel(
                "[bold gold1]CROWN & CREW SYSTEM[/bold gold1]\n\n"
                "[dim]The Blind Allegiance. The Journey to the Border.[/dim]",
                box=box.DOUBLE,
                border_style=CRIMSON,
                title="[bold]👑 CROWN & CREW SYSTEM 🏴[/bold]"
            ))
            console.print()

            submenu = Table(
                box=box.HEAVY,
                border_style=MAGENTA,
                show_header=False,
                padding=(0, 2),
                title="[bold]══════ SELECT CAMPAIGN TYPE ══════[/bold]",
                title_style=MAGENTA
            )

            submenu.add_column("Option", style=GOLD)
            submenu.add_column("Description", style=PARCHMENT)

            submenu.add_row("[1]", "⚔️  Standard Campaign    — Classic Crown & Crew Journey")
            submenu.add_row("[2]", "⚔️  Quest Archetype      — Scenario Template (7 available)")

            if ASHBURN_AVAILABLE:
                submenu.add_row("[3]", "🥀 Ashburn High         — Gothic Boarding School Expansion")
            else:
                submenu.add_row("[3]", "[dim]🥀 Ashburn High (Not Available)[/dim]")

            submenu.add_row("[4]", "↩️  Back to Main Menu   — Return")

            console.print()
            console.print(Align.center(submenu))
            console.print()

            choice = await ainput("[gold1]Choose thy path [1/2/3/4]:[/] ")
            choice = choice.lower().strip()

            if not choice:
                continue

            if choice == "1":
                # Standard Crown & Crew campaign
                _launch_views()
                await run_crown_campaign(world_state=None, mimir=getattr(core, 'architect', None), butler=getattr(core, 'butler', None))

            elif choice == "2":
                # Quest Archetype selection (WO-V23.0)
                try:
                    from codex.games.crown.quests import list_quests
                    quests = list_quests()
                    if not quests:
                        console.print("[yellow]No quest archetypes available.[/yellow]")
                        await ainput("\n[dim]Press Enter to continue...[/dim]")
                        continue

                    console.clear()
                    quest_table = Table(
                        box=box.HEAVY, border_style=GOLD, show_header=True,
                        title="[bold]══════ QUEST ARCHETYPES ══════[/bold]",
                        title_style=GOLD
                    )
                    quest_table.add_column("#", style=GOLD, width=3)
                    quest_table.add_column("Quest", style="bold")
                    quest_table.add_column("Days", style="cyan", width=5)
                    quest_table.add_column("Description", style=PARCHMENT)

                    for i, q in enumerate(quests, 1):
                        desc = f"{q.description[:60]}..." if len(q.description) > 60 else q.description
                        quest_table.add_row(str(i), q.name, str(q.arc_length), desc)

                    console.print(quest_table)
                    console.print()

                    q_choice = (await ainput(f"[gold1]Select quest [1-{len(quests)}] or 'b' to go back:[/] ")).strip()
                    if q_choice.lower() == 'b':
                        continue
                    try:
                        q_idx = int(q_choice) - 1
                        if 0 <= q_idx < len(quests):
                            quest = quests[q_idx]
                            ws = quest.to_world_state()
                            await run_crown_campaign(
                                world_state=ws,
                                mimir=getattr(core, 'architect', None),
                                butler=getattr(core, 'butler', None)
                            )
                        else:
                            console.print("[dim]Invalid selection.[/dim]")
                    except ValueError:
                        console.print("[dim]Invalid selection.[/dim]")
                except ImportError:
                    console.print("[yellow]Quest archetypes module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "3" and ASHBURN_AVAILABLE:
                # Ashburn High expansion
                await run_ashburn_campaign(world_state=None, core=core)

            elif choice == "3" and not ASHBURN_AVAILABLE:
                console.print("[yellow]Ashburn High module not available.[/yellow]")
                await ainput("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "4":
                # Return to main menu
                return

            else:
                continue

        except KeyboardInterrupt:
            console.print("\n[yellow]Returning to main menu...[/yellow]")
            return


# =============================================================================
# GENESIS SUB-MENU (NEW)
# =============================================================================
async def run_genesis_sub_menu(core: CodexCore):
    """
    Homebrew Genesis Sub-Menu.

    Provides three world creation methods:
    [1] Instant World Roll — Random generation (GenesisEngine)
    [2] Deep Genesis (G.R.A.P.E.S.) — Structured manual interview
    [3] Import Setting Bible — Paste existing lore
    [4] Back

    After world is created, prompts user to start campaign.
    """
    while True:
        try:
            console.clear()
            console.print(Text(TITLE_ART, style=GOLD))

            console.print()
            console.print(Panel(
                "[bold cyan]HOMEBREW GENESIS[/bold cyan]\n\n"
                "[dim]Create a custom world for your Crown & Crew campaign.[/dim]",
                box=box.DOUBLE,
                border_style=ROYAL_BLUE,
                title="[bold]🌍 WORLD CREATION METHODS 🌍[/bold]"
            ))
            console.print()

            genesis_menu = Table(
                box=box.HEAVY,
                border_style=ROYAL_BLUE,
                show_header=False,
                padding=(0, 2),
                title="[bold]══════ SELECT METHOD ══════[/bold]",
                title_style=ROYAL_BLUE
            )

            genesis_menu.add_column("Option", style=GOLD)
            genesis_menu.add_column("Description", style=PARCHMENT)

            if GENESIS_AVAILABLE:
                genesis_menu.add_row("[1]", "🎲 Instant World Roll    — Random generation (fast)")
            else:
                genesis_menu.add_row("[1]", "[dim]🎲 Instant World Roll (Not Available)[/dim]")

            genesis_menu.add_row("[2]", "📝 Deep Genesis (G.R.A.P.E.S.) — Structured interview")
            genesis_menu.add_row("[3]", "📋 Import Setting Bible  — Paste existing lore")
            genesis_menu.add_row("[4]", "↩️  Back                 — Return to Crown & Crew Menu")

            console.print()
            console.print(Align.center(genesis_menu))
            console.print()

            choice = await ainput("[gold1]Choose thy method [1/2/3/4]:[/] ")
            choice = choice.lower().strip()

            if not choice:
                continue

            world_state = None
            we = get_world_engine()
            architect = core.architect

            if choice == "1" and GENESIS_AVAILABLE:
                # Instant World Roll using GenesisEngine
                world_state = await we.run_instant_genesis()

            elif choice == "1" and not GENESIS_AVAILABLE:
                console.print("[yellow]GenesisEngine module not available.[/yellow]")
                await ainput("\n[dim]Press Enter to continue...[/dim]")
                continue

            elif choice == "2":
                # Deep Genesis (G.R.A.P.E.S.)
                world_state = await we.run_deep_genesis(architect)

            elif choice == "3":
                # Import Setting Bible
                console.clear()
                console.print(Panel(
                    "[bold cyan]TEXT IMPORT WIZARD[/bold cyan]\n\n"
                    "[dim]Paste your existing setting bible, wiki text, or notes.\n"
                    "Press Enter twice when done (blank line to finish).[/]",
                    box=box.DOUBLE,
                    border_style="cyan"
                ))
                console.print()

                console.print("[green]Paste your setting text:[/green]")
                console.print("[dim](Enter a blank line to finish)[/dim]")
                console.print()

                lines = []
                try:
                    while True:
                        line = await ainput("")
                        if not line.strip():
                            break
                        lines.append(line)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Import cancelled.[/yellow]")
                    continue

                source_text = "\n".join(lines)

                if source_text.strip():
                    world_state = await we.ingest_bible(source_text, architect)

            elif choice == "4":
                # Back to Crown & Crew Menu
                return

            # If a world was created, offer to start campaign
            if world_state is not None:
                console.clear()
                console.print(Panel(
                    f"[bold gold1]World Created: {world_state.name}[/bold gold1]\n\n"
                    "[dim]Would you like to start a campaign with this world?[/dim]",
                    box=box.DOUBLE,
                    border_style=EMERALD
                ))
                console.print()

                campaign_menu = Table(
                    box=box.ROUNDED,
                    border_style=EMERALD,
                    show_header=False,
                    padding=(0, 2)
                )

                campaign_menu.add_column("Option", style=GOLD)
                campaign_menu.add_column("Description", style=PARCHMENT)

                campaign_menu.add_row("[1]", "⚔️  Standard Crown & Crew")
                if ASHBURN_AVAILABLE:
                    campaign_menu.add_row("[2]", "🥀 Ashburn High")
                else:
                    campaign_menu.add_row("[2]", "[dim]🥀 Ashburn High (Not Available)[/dim]")
                campaign_menu.add_row("[3]", "↩️  Return to Menu")

                console.print(campaign_menu)
                console.print()

                campaign_choice = await ainput("[gold1]Choose campaign type [1/2/3]:[/] ")
                campaign_choice = campaign_choice.lower().strip()

                ws_dict = world_state.to_dict()

                if campaign_choice == "1":
                    await run_crown_campaign(world_state=ws_dict, mimir=getattr(core, 'architect', None), butler=getattr(core, 'butler', None))
                    return  # After campaign, return to Crown & Crew menu

                elif campaign_choice == "2" and ASHBURN_AVAILABLE:
                    print(f"[DEBUG PROBE] Launching Ashburn (Genesis). core type: {type(core)}, core is None: {core is None}")
                    await run_ashburn_campaign(world_state=ws_dict, core=core)
                    return

                elif campaign_choice == "2" and not ASHBURN_AVAILABLE:
                    console.print("[yellow]Ashburn High module not available.[/yellow]")
                    await ainput("\n[dim]Press Enter to continue...[/dim]")
                    continue

                elif campaign_choice == "3":
                    # Return to Genesis Sub-Menu
                    continue

        except KeyboardInterrupt:
            console.print("\n[yellow]Returning to Crown & Crew menu...[/yellow]")
            return


# =============================================================================
# MAIN MENU
# =============================================================================
async def main_menu(core: CodexCore):
    """The main dashboard and menu loop."""
    while True:
        console.clear()
        console.print(Text(TITLE_ART, style=GOLD))
        render_vitals(core.cortex)

        # Main menu (WO 109 — data-driven from CodexMenu)
        codex_menu = CodexMenu()
        menu_def = codex_menu.get_menu("terminal")
        menu = Table(
            box=box.HEAVY,
            border_style=CRIMSON,
            show_header=False,
            padding=(0, 2),
            expand=False,
            title=f"[bold]══════ {menu_def.title} ══════[/bold]",
            title_style=CRIMSON
        )

        menu.add_column("Option", style=GOLD)
        menu.add_column("Description", style=PARCHMENT)

        for opt in menu_def.options:
            menu.add_row(f"[{opt.key}]", f"{opt.icon} [bold]{opt.label}[/] \u2014 {opt.description}")

        console.print()
        console.print(Align.center(menu))
        console.print()

        # Non-blocking input allows Discord/Telegram bots to run
        choice_raw = await ainput("[gold1]Choose thy path [1/2/3/4/5/6/7/8/q]:[/] ")
        choice = choice_raw.strip()
        choice_lower = choice.lower()

        # WO 081: Butler Protocol — instant reflex check
        butler = getattr(core, 'butler', None)
        if butler:
            reflex = butler.check_reflex(choice)
            if reflex:
                console.print(Panel(reflex, style="bold cyan", title="⚡ Butler"))
                await ainput("\n[dim]Press Enter to continue...[/dim]")
                continue

        if not choice:
            continue

        # WO 107: Unified Scribe commands
        if choice_lower.startswith("!log ") and butler:
            text = choice[5:].strip()
            if text:
                result = butler.scribe(text, secret=False)
                console.print(Panel(result, style="bold green", title="Scribe"))
            else:
                console.print("[yellow]Usage: !log <text>[/yellow]")
            await ainput("\n[dim]Press Enter to continue...[/dim]")
            continue

        if (choice_lower.startswith("!note ") or choice_lower.startswith("!dm ")) and butler:
            prefix_len = 6 if choice_lower.startswith("!note ") else 4
            text = choice[prefix_len:].strip()
            if text:
                result = butler.scribe(text, secret=True)
                console.print(Panel(result, style="bold red", title="Secret Scribe"))
            else:
                console.print("[yellow]Usage: !note <text>[/yellow]")
            await ainput("\n[dim]Press Enter to continue...[/dim]")
            continue

        if choice_lower == "!journal" and butler:
            entries = butler.get_recent_logs(limit=20, include_secrets=True)
            if not entries:
                console.print(Panel("No log entries for today.", style="dim"))
            else:
                journal_table = Table(
                    box=box.SIMPLE_HEAVY,
                    border_style=CRIMSON,
                    title="[bold]Session Journal[/bold]",
                    title_style=GOLD,
                    show_header=False,
                    padding=(0, 1),
                )
                journal_table.add_column("Entry", ratio=1)
                for line in entries:
                    if "[SECRET]" in line:
                        journal_table.add_row(f"[bold red]{line}[/bold red]")
                    else:
                        journal_table.add_row(f"[green]{line}[/green]")
                console.print(journal_table)
            await ainput("\n[dim]Press Enter to continue...[/dim]")
            continue

        if choice_lower == "!read" and butler:
            summary = butler.get_public_summary()
            console.print(Panel(summary, style="green", title="Public Journal (TTS-Safe)"))
            await ainput("\n[dim]Press Enter to continue...[/dim]")
            continue

        if choice_lower in ("!universe", "!starchart"):
            um = getattr(core, "universe_manager", None)
            if um:
                um.render_star_chart(console)
            else:
                console.print("[yellow]Universe Manager not available.[/yellow]")
            await ainput("\n[dim]Press Enter to continue...[/dim]")
            continue

        # WO 109: Action-based dispatch via CodexMenu
        action = codex_menu.resolve_selection("terminal", choice)
        if action is None:
            continue

        if action == "play_chronicles":
            await run_codex_chronicles_menu(core)

        elif action == "play_crown":
            await run_crown_crew_menu(core)

        elif action == "play_burnwillow":
            if BURNWILLOW_AVAILABLE:
                _launch_views()
                loop = asyncio.get_event_loop()
                butler = getattr(core, 'butler', None)
                await loop.run_in_executor(None, lambda: run_burnwillow_game(butler=butler))  # type: ignore[misc]
            else:
                console.print(Panel(
                    "[yellow]Burnwillow module not available.[/yellow]\n\n"
                    "[dim]Ensure play_burnwillow.py is present in the Codex directory.[/dim]",
                    border_style="yellow"
                ))
                await ainput("\n[dim]Press Enter to continue...[/dim]")

        elif action == "dm_tools":
            await run_dm_tools_menu(core)

        elif action == "open_vault":
            await run_library(core)

        elif action == "open_tutorial":
            try:
                from codex.core.services.tutorial import TutorialBrowser, PlatformTutorial
                import codex.core.services.tutorial_content  # noqa: F401 -- populates registry
                tutorial = PlatformTutorial()
                browser = TutorialBrowser(tutorial=tutorial)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: browser.run_loop(console))
            except Exception as e:
                console.print(f"[yellow]Tutorial unavailable: {e}[/yellow]")
                await ainput("\n[dim]Press Enter to continue...[/dim]")

        elif action == "system_status":
            console.clear()

            # Build the status table
            status_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            status_table.add_column("Label", style="dim", min_width=20)
            status_table.add_column("Value", min_width=30)

            # Base report rows from core
            base_report = core.get_status_report()
            for line in base_report.splitlines():
                line = line.strip()
                if line:
                    status_table.add_row("", line)

            # Rich metabolic section — only if cortex is available
            if hasattr(core, 'cortex') and core.cortex:
                try:
                    ms: MetabolicState = core.cortex.read_metabolic_state()

                    status_table.add_row("", "")
                    status_table.add_row("[bold cyan]-- METABOLIC VITALS --[/bold cyan]", "")

                    # CPU temperature with colour grading
                    temp = ms.cpu_temp_celsius
                    if temp < 65.0:
                        temp_style = "green"
                    elif temp < 75.0:
                        temp_style = "yellow"
                    else:
                        temp_style = "bold red"
                    temp_bar_filled = min(int(temp / 100.0 * 20), 20)
                    temp_bar = f"[{temp_style}]{'█' * temp_bar_filled}[/{temp_style}][dim]{'░' * (20 - temp_bar_filled)}[/dim]"
                    status_table.add_row(
                        "CPU Temperature",
                        f"[{temp_style}]{temp:.1f}°C[/{temp_style}]  {temp_bar}"
                    )

                    # RAM usage bar with colour grading
                    ram_pct = ms.ram_usage_percent
                    if ram_pct < 70.0:
                        ram_style = "green"
                    elif ram_pct < 85.0:
                        ram_style = "yellow"
                    else:
                        ram_style = "bold red"
                    ram_bar_filled = min(int(ram_pct / 100.0 * 20), 20)
                    ram_bar = f"[{ram_style}]{'█' * ram_bar_filled}[/{ram_style}][dim]{'░' * (20 - ram_bar_filled)}[/dim]"
                    status_table.add_row(
                        "RAM Usage",
                        f"[{ram_style}]{ram_pct:.1f}%[/{ram_style}]  {ram_bar}  "
                        f"[dim]({ms.ram_available_gb:.2f} GB free)[/dim]"
                    )

                    # Thermal status badge
                    _badge_map = {
                        ThermalStatus.OPTIMAL:  ("[bold green]  GREEN   [/bold green]",  "green"),
                        ThermalStatus.FATIGUED: ("[bold yellow] YELLOW  [/bold yellow]", "yellow"),
                        ThermalStatus.CRITICAL: ("[bold red]   RED    [/bold red]",      "bold red"),
                        ThermalStatus.RECOVERY: ("[bold blue] COOLDOWN [/bold blue]",    "blue"),
                    }
                    badge_text, _ = _badge_map.get(
                        ms.thermal_status,
                        ("[dim]UNKNOWN[/dim]", "dim")
                    )
                    status_table.add_row("Thermal Status", badge_text)

                    # Model clearance indicator
                    if ms.metabolic_clearance:
                        clearance_text = "[bold green]GRANTED[/bold green]  [dim](large LLM calls are safe)[/dim]"
                    else:
                        clearance_text = "[bold red]DENIED[/bold red]   [dim](thermal or RAM pressure too high)[/dim]"
                    status_table.add_row("Model Clearance", clearance_text)

                    # Pain signal if active
                    if ms.pain_signal_active and ms.pain_message:
                        status_table.add_row("", "")
                        status_table.add_row(
                            "[bold red]PAIN SIGNAL[/bold red]",
                            f"[red]{ms.pain_message}[/red]"
                        )

                except Exception as _e:
                    status_table.add_row("[dim]Metabolic read failed[/dim]", f"[dim]{_e}[/dim]")

            console.print(Panel(
                status_table,
                title="[bold]SYSTEM STATUS[/bold]",
                box=box.DOUBLE,
                border_style=ROYAL_BLUE
            ))
            await ainput("\n[dim]Press Enter to continue...[/dim]")

        elif action == "exit":
            console.clear()
            console.print(Panel(
                "[bold gold1]Until we meet again, brave adventurer.[/bold gold1]\n\n"
                "[dim]May your rolls be natural 20s.[/dim]",
                box=box.DOUBLE,
                border_style=GOLD
            ))
            return "SHUTDOWN"


# =============================================================================
# DISCORD BOT
# =============================================================================
class VoiceUplink:
    PIPER_VOICE = "en_US-lessac-medium"

    async def synthesize(self, text: str) -> Optional[Path]:
        text = re.sub(r"```[\s\S]*?```", " code block ", text)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = Path(f.name)
        try:
            process = await asyncio.create_subprocess_exec(
                "piper", "--model", self.PIPER_VOICE, "--output_file", str(output_path),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate(input=text.encode())
            return output_path if process.returncode == 0 else None
        except:
            return None

    async def speak(self, text: str, voice_client: discord.VoiceClient):
        if not voice_client or not voice_client.is_connected():
            return
        path = await self.synthesize(text[:300])
        if path:
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            voice_client.play(discord.FFmpegPCMAudio(str(path)), after=lambda e: path.unlink(missing_ok=True))


class CodexBot(commands.Bot):
    def __init__(self, core: CodexCore):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.core = core
        self.voice = VoiceUplink()

    async def setup_hook(self):
        self.add_cog(GeneralCommands(self))

    async def on_ready(self):
        logger.info(f"Connected to Discord as {self.user}")
        if not self.thermal_monitor.is_running():
            self.thermal_monitor.start()

    @tasks.loop(seconds=10.0)
    async def thermal_monitor(self):
        state = self.core.cortex.read_metabolic_state()
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"Temp: {state.cpu_temp_celsius:.0f}°C"
        ))

    async def on_message(self, message):
        if message.author == self.user:
            return
        await self.process_commands(message)

        if self.user in message.mentions or isinstance(message.channel, discord.DMChannel):
            clean_content = re.sub(rf"<@!?{self.user.id}>", "", message.content).strip()  # type: ignore[union-attr]
            async with message.channel.typing():
                response = await self.core.process_input(str(message.author.id), clean_content)

                if len(response) > 2000:
                    for chunk in [response[i:i+1990] for i in range(0, len(response), 1990)]:
                        await message.reply(chunk, mention_author=False)
                else:
                    await message.reply(response, mention_author=False)

                if message.author.voice and message.author.voice.channel:
                    if not self.voice_clients:
                        await message.author.voice.channel.connect()
                    await self.voice.speak(response, self.voice_clients[0])  # type: ignore[arg-type]


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="status")
    async def cmd_status(self, ctx):
        await ctx.send(f"```\n{self.bot.core.get_status_report()}\n```")

    @commands.command(name="summon")
    async def cmd_summon(self, ctx):
        await ctx.send("**Mimir has been summoned.** I am focusing on this channel.")

    @commands.command(name="voice")
    async def cmd_voice(self, ctx, action="join"):
        if action == "join" and ctx.author.voice:
            await ctx.author.voice.channel.connect()
        elif action == "leave" and ctx.voice_client:
            await ctx.voice_client.disconnect()


# =============================================================================
# SERVICE HEALTH MONITOR (WO-V9.0)
# =============================================================================

class ServiceHealthMonitor:
    """Checks spawned services and restarts them if crashed.

    WO-V9.4: Also monitors Discord voice client health via opus error count.
    """

    OPUS_ERROR_THRESHOLD = 10  # consecutive failures before reconnect

    def __init__(self, services: list, check_port_fn, discord_bot=None):
        self._services = services  # list of [name, proc, restart_args, port]
        self._check_port = check_port_fn
        self._discord_bot = discord_bot  # CodexDiscordBot ref (optional)
        self._last_restart: dict[str, float] = {}  # WO-V63.0: rate-limit restarts

    async def check_and_restart(self):
        """Check all services, restart any that have crashed.
        Returns list of restarted service names."""
        restarted = []
        for entry in self._services:
            name, proc, args, port = entry
            needs_restart = False
            if proc.poll() is not None:
                needs_restart = True
            elif port is not None and not self._check_port(port):
                needs_restart = True
            if needs_restart:
                # WO-V63.0: Rate-limit restarts to prevent infinite restart storms
                import time as _time
                last = self._last_restart.get(name, 0)
                if _time.time() - last < 60:
                    continue  # Skip — restarted too recently
                try:
                    proc.terminate()
                except Exception:
                    pass
                try:
                    new_proc = subprocess.Popen(
                        args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    entry[1] = new_proc
                    restarted.append(name)
                    self._last_restart[name] = _time.time()
                    console.print(f"[dim]{name}: RESTARTED[/dim]")
                except Exception:
                    pass

        # WO-V9.4: Voice watchdog — reconnect on opus decode failure storm
        await self._voice_watchdog()

        return restarted

    async def _voice_watchdog(self):
        """Auto-reconnect Discord voice client on sustained opus errors."""
        if not self._discord_bot:
            return
        try:
            from codex.bots.discord_bot import (
                _opus_error_count, _opus_error_lock,
            )
            with _opus_error_lock:
                error_count = _opus_error_count
            if error_count < self.OPUS_ERROR_THRESHOLD:
                return
            # Threshold exceeded — attempt voice reconnect
            console.print(
                f"[yellow]Voice watchdog: {error_count} opus errors, "
                f"reconnecting...[/yellow]"
            )
            for vc in list(self._discord_bot.voice_clients):
                try:
                    channel = vc.channel
                    await vc.disconnect(force=True)
                    await asyncio.sleep(1)
                    await channel.connect()
                    console.print("[green]Voice watchdog: reconnected[/green]")
                except Exception as e:
                    console.print(f"[red]Voice watchdog failed: {e}[/red]")
            # Reset counter after reconnect attempt
            import codex.bots.discord_bot as _dbot
            with _dbot._opus_error_lock:
                _dbot._opus_error_count = 0
        except ImportError:
            pass
        except Exception:
            pass

    async def run_loop(self, interval: float = 30.0):
        """Background loop that calls check_and_restart periodically."""
        while True:
            try:
                await asyncio.sleep(interval)
                await self.check_and_restart()
            except asyncio.CancelledError:
                break
            except Exception:
                pass


# =============================================================================
# BOOTSTRAP
# =============================================================================
async def main_async():
    """Main async entry point."""
    # Initialize core
    core = CodexCore()

    # WO 081: Butler Protocol — attach to core for instant reflex routing
    if BUTLER_AVAILABLE:
        core.butler = CodexButler(core_state=core)  # type: ignore[attr-defined, union-attr, misc]

    # WO-V10.0: HybridGameOrchestrator — replaced by StackedCommandDispatcher (WO-V60.0)

    # Universe Manager — world registry and star chart
    if UNIVERSE_MANAGER_AVAILABLE:
        core.universe_manager = UniverseManager()  # type: ignore[attr-defined, misc]

    # Broadcast Manager — observer-pattern event bus
    if BROADCAST_AVAILABLE:
        core.broadcast = GlobalBroadcastManager(system_theme="codex")  # type: ignore[attr-defined, misc]

    # Memory Engine — shard-based context management
    if MEMORY_ENGINE_AVAILABLE:
        core.memory = CodexMemoryEngine(  # type: ignore[attr-defined, misc]
            broadcast_manager=getattr(core, 'broadcast', None)
        )

    # Trait Handler — system-agnostic trait resolution
    if TRAIT_HANDLER_AVAILABLE:
        core.trait_handler = TraitHandler(  # type: ignore[attr-defined, misc]
            broadcast_manager=getattr(core, 'broadcast', None)
        )

    # Run boot sequence
    await boot_sequence(core.cortex)

    # --- Service Auto-Launch: Ears + Mouth (WO-V9.0: tracked for health monitor) ---
    _spawned_services = []  # list of [name, proc, restart_args, port]

    def _check_port(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            return sock.connect_ex(("127.0.0.1", port)) == 0
        finally:
            sock.close()

    # Ears binds 0.0.0.0 (LAN push-to-talk UI), Mouth binds localhost (internal only)
    for _svc_name, _svc_mod, _svc_port, _svc_host in [
        ("Ears", "ears", 5000, "0.0.0.0"),
        ("Mouth", "mouth", 5001, "127.0.0.1"),
    ]:
        if not _check_port(_svc_port):
            _restart_args = [
                sys.executable, "-m", "uvicorn", f"codex.services.{_svc_mod}:app",
                "--host", _svc_host, "--port", str(_svc_port),
            ]
            try:
                proc = subprocess.Popen(
                    _restart_args,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                _spawned_services.append([_svc_name, proc, _restart_args, _svc_port])
            except Exception:
                pass

    # Start background services
    tasks_to_cancel = []

    # WO-V9.0: Service Health Monitor (bot ref wired after Discord init)
    _monitor = None
    if _spawned_services:
        _monitor = ServiceHealthMonitor(_spawned_services, _check_port)

    # Telegram bot (WO-V9.5: guard on token presence)
    telegram_token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if TELEGRAM_AVAILABLE and telegram_token:
        telegram_task = asyncio.create_task(run_telegram_bot(core=core))  # type: ignore[misc]
        tasks_to_cancel.append(telegram_task)
        console.print("[dim]Telegram Uplink: [green]ACTIVE[/green][/dim]")
    elif TELEGRAM_AVAILABLE:
        logger.info("Telegram bot available but no TELEGRAM_TOKEN set — skipping")

    # Discord bot (use new module if available, fallback to embedded)
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        if DISCORD_BOT_AVAILABLE:
            bot = CodexDiscordBot(core=core)  # type: ignore[misc]
            # WO-V9.4: Wire bot ref to health monitor for voice watchdog
            if _monitor:
                _monitor._discord_bot = bot
            discord_task = asyncio.create_task(bot.start(discord_token))
        else:
            bot = CodexBot(core)
            discord_task = asyncio.create_task(bot.start(discord_token))
        tasks_to_cancel.append(discord_task)
        console.print("[dim]Discord Uplink: [green]ACTIVE[/green][/dim]")

    # Start health monitor after Discord bot is wired (for voice watchdog)
    if _monitor:
        health_task = asyncio.create_task(_monitor.run_loop(interval=30.0))
        tasks_to_cancel.append(health_task)

    console.print()
    await asyncio.sleep(0.5)

    # Run main menu
    try:
        result = await main_menu(core)
    except (KeyboardInterrupt, EOFError):
        result = "SHUTDOWN"

    # Log exit reason
    if result == "SHUTDOWN":
        logger.info("Shutdown requested by user")
    elif result:
        logger.info(f"Main menu exited: {result}")

    # Cleanup async tasks
    for task in tasks_to_cancel:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Cleanup spawned services
    for entry in _spawned_services:
        try:
            entry[1].terminate()  # entry = [name, proc, args, port]
        except Exception:
            pass

    await core.close()


def main():
    """Synchronous entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

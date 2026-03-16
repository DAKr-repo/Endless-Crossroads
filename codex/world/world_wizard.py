#!/usr/bin/env python3
"""
codex_world_engine.py - The Genesis Module
===========================================

Generates custom Homebrew worlds for the Crown & Crew engine.
Provides a terminal wizard for world creation and persistence.

The Genesis Module answers one question:
"What kind of story are we telling?"

Version: 1.0 (Genesis)
"""

import asyncio
import json
import random
import re
import select
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_ROOT = Path(__file__).resolve().parent.parent.parent  # -> Codex/
from rich.align import Align
from rich import box
from rich.prompt import Prompt

# Try to import GenesisEngine (the new instant roll system)
try:
    from codex.world.genesis import GenesisEngine
    GENESIS_AVAILABLE = True
except ImportError:
    GENESIS_AVAILABLE = False

# Try to import MemoryEngine (WO-049: Memory Shard Neural Link)
try:
    from codex.core.memory import CodexMemoryEngine, MemoryShard, ShardType
    MEMORY_ENGINE_AVAILABLE = True
except ImportError:
    MEMORY_ENGINE_AVAILABLE = False

# =============================================================================
# CONSOLE & COLOR PALETTE (mirrors codex_agent_main.py)
# =============================================================================
console = Console()

GOLD = "bold yellow"
CRIMSON = "bold red"
EMERALD = "bold green"
SILVER = "dim white"
ROYAL_BLUE = "bold blue"
PARCHMENT = "wheat1"
MAGENTA = "bold magenta"
CYAN = "bold cyan"

# Async input helper (local to avoid circular import with codex_agent_main)
_input_executor = ThreadPoolExecutor(1, "GenesisInput")


def _read_with_paste() -> str:
    """Read a line from stdin, then collect any remaining pasted lines.

    When users paste multi-paragraph text, readline() only captures the
    first line. This function drains any extra buffered lines and joins
    them so the entire paste becomes one answer instead of bleeding into
    subsequent prompts.
    """
    line = sys.stdin.readline()
    parts = [line.rstrip("\n")]
    # Drain any remaining pasted lines (50ms window per line)
    try:
        while select.select([sys.stdin], [], [], 0.05)[0]:
            more = sys.stdin.readline()
            if not more:
                break
            parts.append(more.rstrip("\n"))
    except (OSError, ValueError):
        pass  # select not available or stdin closed
    return " ".join(p for p in parts if p.strip())


async def _ainput(prompt: str = "") -> str:
    """Non-blocking async input for the genesis wizard.

    Handles multi-line paste by collecting all buffered lines into one
    response, preventing buffer bleed into subsequent prompts.
    """
    if prompt:
        console.print(prompt, end="")
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(_input_executor, _read_with_paste)).strip()


# =============================================================================
# SYSTEM PRESETS — THE SIMULATION LIBRARY
# =============================================================================

SYSTEM_PRESETS: dict[str, dict] = {
    "dnd5e": {
        "display": "D&D 5e",
        "tagline": "High Fantasy Adventure",
        "icon": "🐉",
        "terms": {
            "crown": "The Crown",
            "crew": "The Crew",
            "neutral": "The Drifter",
            "campfire": "Campfire",
            "world": "The Wilds",
        },
        "desc": "Classic swords-and-sorcery. Dungeons. Dragons. Destiny.",
    },
    "blades": {
        "display": "Blades in the Dark",
        "tagline": "Industrial Gothic Heists",
        "icon": "🗡️",
        "terms": {
            "crown": "The Inspectors",
            "crew": "The Gang",
            "neutral": "The Ghost",
            "campfire": "The Den",
            "world": "Doskvol",
        },
        "desc": "Gaslight streets. Spectral horrors. One last score.",
    },
    "scum": {
        "display": "Scum & Villainy",
        "tagline": "Space Opera Scoundrels",
        "icon": "🚀",
        "terms": {
            "crown": "The Hegemony",
            "crew": "The Ship",
            "neutral": "The Drifter",
            "campfire": "The Galley",
            "world": "The Procyon Sector",
        },
        "desc": "Smugglers. Star-gates. A galaxy that doesn't care.",
    },
    "cosmere": {
        "display": "Cosmere RPG",
        "tagline": "Investiture & Intrigue",
        "icon": "🌀",
        "terms": {
            "crown": "The Obligators",
            "crew": "The Resistance",
            "neutral": "The Worldhopper",
            "campfire": "The Hearth",
            "world": "The Final Empire",
        },
        "desc": "Magic is physics. Gods are mortal. Ash falls from the sky.",
    },
    "shadowdark": {
        "display": "Shadowdark",
        "tagline": "Torchlit Dungeon Crawl",
        "icon": "🕯️",
        "terms": {
            "crown": "The Light",
            "crew": "The Dark",
            "neutral": "The Torchbearer",
            "campfire": "The Watch",
            "world": "The Underrealm",
        },
        "desc": "Your torch is dying. So are you. Keep moving.",
    },
}

# Tone presets
TONE_PRESETS: dict[str, dict] = {
    "gritty": {
        "display": "Gritty & Moral",
        "icon": "⚔️",
        "modifier": "dark, morally ambiguous, consequences are real",
        "desc": "Hard choices. No heroes. Survival is the victory.",
    },
    "heroic": {
        "display": "Heroic & Epic",
        "icon": "🛡️",
        "modifier": "grand, dramatic, mythic in scale",
        "desc": "Grand deeds. Worthy foes. Songs will be sung.",
    },
    "comedic": {
        "display": "Comedic & Absurd",
        "icon": "🎭",
        "modifier": "humorous, absurd, self-aware, satirical",
        "desc": "The world is ridiculous. Lean into it.",
    },
    "gothic": {
        "display": "Gothic & Haunted",
        "icon": "🦇",
        "modifier": "atmospheric, dread, slow-burn horror, melancholic",
        "desc": "Something is wrong. It has always been wrong.",
    },
}

# Spinner flavor text for LLM generation
GENESIS_PHASES: list[str] = [
    "Synthesizing leylines...",
    "Forging continental plates...",
    "Seeding civilizations...",
    "Calibrating moral entropy...",
    "Inscribing creation myths...",
    "Threading prophecies...",
    "Igniting celestial bodies...",
    "Establishing trade routes...",
    "Burying ancient ruins...",
    "Awakening dormant gods...",
]

# LLM prompt template for world primer generation
GENESIS_PROMPT_TEMPLATE = """You are a world-building engine for a tabletop RPG.

SETTING: {system_name}
GENRE: {genre}
TONE: {tone_modifier}

The world has two opposing factions:
- "{crown_term}" (the authority / establishment)
- "{crew_term}" (the rebels / outcasts)

Generate EXACTLY the following, separated by the markers shown:

===PRIMER===
A 2-3 sentence world primer describing this setting. Make it evocative and specific.

===CROWN_PROMPTS===
5 moral dilemmas from the perspective of someone tempted by {crown_term}. One per line. Each should be 1-2 sentences. Focus on safety, order, betrayal of allies.

===CREW_PROMPTS===
5 moral dilemmas from the perspective of someone loyal to {crew_term}. One per line. Each should be 1-2 sentences. Focus on sacrifice, loyalty, hard choices for the group.

===WORLD_PROMPTS===
5 environmental hazard descriptions for traveling through this world. One per line. Each should be 1-2 sentences. Vivid, dangerous, atmospheric.

===CAMPFIRE_PROMPTS===
5 introspective campfire questions for quiet moments. One per line. Each should be 1-2 sentences. Personal, reflective, probing identity.

===WITNESS===
One sentence describing a mysterious figure who appears on Day 3 carrying something that belongs to the protagonist.

===PATRONS===
5 authority figure titles/names appropriate for {crown_term}. One per line. Title only.

===LEADERS===
5 rebel leader titles/names appropriate for {crew_term}. One per line. Title only.
"""


# =============================================================================
# WORLD STATE — THE DATA SCHEMA
# =============================================================================

@dataclass
class WorldState:
    """A generated or loaded world configuration."""
    name: str
    system_id: str
    system_display: str
    tone: str
    genre: str

    # Faction terminology
    terms: dict[str, str] = field(default_factory=dict)

    # World primer (LLM-generated flavor text)
    primer: str = ""

    # Prompt pools
    prompts_crown: list[str] = field(default_factory=list)
    prompts_crew: list[str] = field(default_factory=list)
    prompts_world: list[str] = field(default_factory=list)
    prompts_campfire: list[str] = field(default_factory=list)
    secret_witness: str = ""

    # Character pools
    patrons: list[str] = field(default_factory=list)
    leaders: list[str] = field(default_factory=list)

    # Metadata
    created_timestamp: float = field(default_factory=time.time)

    # G.R.A.P.E.S. structured world-building fields (flat str or nested dict)
    grapes: dict = field(default_factory=dict)

    # Text import source (for setting bible imports)
    bible_text: str = ""

    # World map integration (optional)
    world_map_path: Optional[str] = None
    regions: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        d = {
            "name": self.name,
            "system_id": self.system_id,
            "system_display": self.system_display,
            "tone": self.tone,
            "genre": self.genre,
            "terms": self.terms,
            "primer": self.primer,
            "prompts_crown": self.prompts_crown,
            "prompts_crew": self.prompts_crew,
            "prompts_world": self.prompts_world,
            "prompts_campfire": self.prompts_campfire,
            "secret_witness": self.secret_witness,
            "patrons": self.patrons,
            "leaders": self.leaders,
            "created_timestamp": self.created_timestamp,
            "grapes": self.grapes,
            "bible_text": self.bible_text,
        }
        # Only emit new fields when populated (backward-compat with older saves)
        if self.world_map_path is not None:
            d["world_map_path"] = self.world_map_path
        if self.regions:
            d["regions"] = self.regions
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "WorldState":
        """Deserialize from dict."""
        return cls(
            name=data["name"],
            system_id=data["system_id"],
            system_display=data.get("system_display", data["system_id"]),
            tone=data.get("tone", "gritty"),
            genre=data.get("genre", "Fantasy"),
            terms=data.get("terms", {}),
            primer=data.get("primer", ""),
            prompts_crown=data.get("prompts_crown", []),
            prompts_crew=data.get("prompts_crew", []),
            prompts_world=data.get("prompts_world", []),
            prompts_campfire=data.get("prompts_campfire", []),
            secret_witness=data.get("secret_witness", ""),
            patrons=data.get("patrons", []),
            leaders=data.get("leaders", []),
            created_timestamp=data.get("created_timestamp", time.time()),
            grapes=data.get("grapes", {}),
            bible_text=data.get("bible_text", ""),
            world_map_path=data.get("world_map_path", None),
            regions=data.get("regions", []),
        )


# =============================================================================
# WORLD ENGINE — GENESIS MODULE
# =============================================================================

class WorldEngine:
    """
    The Genesis Module.

    Creates, saves, and loads custom world configurations
    for the Crown & Crew narrative engine.
    """

    WORLDS_DIR = _ROOT / "worlds"

    def __init__(self):
        self.WORLDS_DIR.mkdir(exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────

    def save_world(self, world: WorldState) -> Path:
        """Save a WorldState to worlds/{name}.json."""
        safe_name = world.name.replace(" ", "_")
        path = self.WORLDS_DIR / f"{safe_name}.json"
        with open(path, "w") as f:
            json.dump(world.to_dict(), f, indent=2)
        return path

    def load_world(self, name: str) -> Optional[WorldState]:
        """Load a WorldState from worlds/{name}.json."""
        safe_name = name.replace(" ", "_")
        path = self.WORLDS_DIR / f"{safe_name}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return WorldState.from_dict(data)

    def list_worlds(self) -> list[WorldState]:
        """List all saved worlds."""
        worlds = []
        for path in sorted(self.WORLDS_DIR.glob("*.json")):
            try:
                with open(path) as f:
                    data = json.load(f)
                worlds.append(WorldState.from_dict(data))
            except Exception:
                pass
        return worlds

    def delete_world(self, name: str) -> bool:
        """Delete a saved world."""
        safe_name = name.replace(" ", "_")
        path = self.WORLDS_DIR / f"{safe_name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # ─────────────────────────────────────────────────────────────────────
    # MEMORY ENGINE INTEGRATION (WO-049)
    # ─────────────────────────────────────────────────────────────────────

    def create_memory_engine(self, world_state: WorldState) -> Optional["CodexMemoryEngine"]:
        """Create a CodexMemoryEngine pre-loaded with world context.

        This is the primary bridge between the WorldEngine and the Memory Engine.
        The returned memory engine has a pinned MASTER shard containing the
        world primer, faction data, and G.R.A.P.E.S. summary.

        Args:
            world_state: A WorldState object (from genesis or loaded from disk)

        Returns:
            CodexMemoryEngine with world context ingested, or None if unavailable
        """
        if not MEMORY_ENGINE_AVAILABLE:
            return None

        memory = CodexMemoryEngine()
        memory.ingest_world_state(world_state.to_dict())
        return memory

    # ─────────────────────────────────────────────────────────────────────
    # INSTANT GENESIS — NEW: RANDOM WORLD ROLL
    # ─────────────────────────────────────────────────────────────────────

    async def run_instant_genesis(self) -> Optional[WorldState]:
        """
        Generate a random world using the GenesisEngine and save it.

        Provides Accept / Reroll / Back options.
        If Accept, saves the world and returns the WorldState.
        If Reroll, recursively generates a new world.
        If Back, returns None.

        Returns:
            WorldState if accepted and saved, None if cancelled.
        """
        if not GENESIS_AVAILABLE:
            console.print("[red]GenesisEngine not available. Install codex_genesis_engine.py.[/red]")
            await _ainput("\n[dim]Press Enter to continue...[/dim]")
            return None

        console.clear()
        console.print(Panel(
            "[bold cyan]🎲 INSTANT WORLD ROLL[/bold cyan]\n\n"
            "[dim]Rolling random world parameters...[/dim]",
            box=box.DOUBLE,
            border_style=CYAN,
            padding=(1, 4),
        ))
        console.print()

        # Instantiate GenesisEngine and roll
        genesis = GenesisEngine()
        # WO-V8.0: pass universe_id if available
        try:
            from codex.core.services.universe_manager import UniverseManager
            _um = UniverseManager()
            _uid = getattr(_um, 'active_universe_id', None)
        except Exception:
            _uid = None
        world_data = genesis.roll_unified_world(universe_id=_uid)

        # Display the rolled world
        genesis.display_world(world_data)

        # Convert to WorldState
        state = genesis.to_world_state(world_data)

        # Prompt: Accept or reroll?
        console.print()
        choice = Prompt.ask(
            "[gold1]Accept this world?[/gold1]",
            choices=["yes", "reroll", "back"],
            default="yes"
        )

        if choice == "reroll":
            return await self.run_instant_genesis()
        elif choice == "back":
            return None

        # Save the world
        path = self.save_world(state)
        console.print(f"[green]World '{state.name}' saved to {path}[/green]")

        # WO-V8.0: Link to universe if manager available
        try:
            from codex.core.services.universe_manager import UniverseManager
            _um = UniverseManager()
            _uid = getattr(_um, 'active_universe_id', None)
            if _uid:
                _um.link_module(_uid, state.name)
        except Exception:
            pass

        # INTEGRATION POINT: Create and save Memory Engine snapshot (WO-049)
        if MEMORY_ENGINE_AVAILABLE:
            try:
                memory = CodexMemoryEngine()
                master_shard = memory.ingest_world_state(state.to_dict())
                safe_name = state.name.replace(" ", "_")
                memory_path = self.WORLDS_DIR / f"{safe_name}_memory.json"
                memory.save_to_disk(memory_path)
                console.print(f"[dim]Memory Shard created: {master_shard.id} (MASTER, pinned)[/dim]")
                console.print(f"[dim]Memory snapshot saved to {memory_path}[/dim]")
            except Exception as e:
                console.print(f"[yellow]Memory Engine snapshot failed: {e}[/yellow]")

        await _ainput("\n[dim]Press Enter to continue...[/dim]")

        return state

    # ─────────────────────────────────────────────────────────────────────
    # LLM PRIMER GENERATION
    # ─────────────────────────────────────────────────────────────────────

    async def _generate_primer(self, architect, world: WorldState) -> WorldState:
        """
        Use the Architect to generate world-specific prompt pools.

        Falls back to empty pools (which CrownAndCrewEngine will
        backfill with hardcoded defaults) if generation fails.
        """
        from codex.core.architect import RoutingDecision, ThinkingMode, Complexity, ThermalStatus

        tone_data = TONE_PRESETS.get(world.tone, TONE_PRESETS["gritty"])

        prompt = GENESIS_PROMPT_TEMPLATE.format(
            system_name=world.system_display,
            genre=world.genre,
            tone_modifier=tone_data["modifier"],
            crown_term=world.terms.get("crown", "The Crown"),
            crew_term=world.terms.get("crew", "The Crew"),
        )

        decision = RoutingDecision(
            mode=ThinkingMode.REFLEX,
            model="mimir",
            complexity=Complexity.MEDIUM,
            thermal_status=ThermalStatus.OPTIMAL,
            clearance_granted=True,
            reasoning="Genesis Module world generation"
        )

        try:
            response = await architect.invoke_model(
                query=prompt,
                system_prompt="You are a world-building engine. Output ONLY the requested content with the exact markers. No commentary.",
                decision=decision,
            )

            raw = response.content
            world = self._parse_genesis_output(raw, world)

        except Exception as e:
            # Generation failed — world will use CrownAndCrewEngine defaults
            world.primer = f"A world shaped by {world.terms.get('crown', 'order')} and {world.terms.get('crew', 'rebellion')}."

        return world

    def _parse_genesis_output(self, raw: str, world: WorldState) -> WorldState:
        """Parse the structured LLM output into WorldState fields."""

        def _extract_section(text: str, marker: str) -> str:
            """Extract content between a marker and the next ===MARKER===."""
            start = text.find(f"==={marker}===")
            if start == -1:
                return ""
            start = text.index("===", start) + len(f"==={marker}===")
            end = text.find("===", start)
            if end == -1:
                end = len(text)
            return text[start:end].strip()

        def _lines(section: str) -> list[str]:
            """Split section into non-empty lines."""
            return [ln.strip().lstrip("0123456789.-) ") for ln in section.splitlines() if ln.strip()]

        world.primer = _extract_section(raw, "PRIMER") or world.primer

        crown = _lines(_extract_section(raw, "CROWN_PROMPTS"))
        if crown:
            world.prompts_crown = crown

        crew = _lines(_extract_section(raw, "CREW_PROMPTS"))
        if crew:
            world.prompts_crew = crew

        world_p = _lines(_extract_section(raw, "WORLD_PROMPTS"))
        if world_p:
            world.prompts_world = world_p

        campfire = _lines(_extract_section(raw, "CAMPFIRE_PROMPTS"))
        if campfire:
            world.prompts_campfire = campfire

        witness = _extract_section(raw, "WITNESS")
        if witness:
            # Take first non-empty line
            for ln in witness.splitlines():
                if ln.strip():
                    world.secret_witness = ln.strip()
                    break

        patrons = _lines(_extract_section(raw, "PATRONS"))
        if patrons:
            world.patrons = patrons

        leaders = _lines(_extract_section(raw, "LEADERS"))
        if leaders:
            world.leaders = leaders

        return world

    # ─────────────────────────────────────────────────────────────────────
    # DEEP GENESIS — G.R.A.P.E.S. STRUCTURED WORLD-BUILDING
    # ─────────────────────────────────────────────────────────────────────

    async def run_deep_genesis(self, architect) -> Optional[WorldState]:
        """
        Run the G.R.A.P.E.S. Detailed Genesis wizard.

        A step-by-step Rich console interview that asks the user for each
        G.R.A.P.E.S. detail (Geography, Religion, Achievements, Politics,
        Economics, Social).

        Args:
            architect: The Architect LLM bridge (not used directly, but kept for consistency)

        Returns:
            Fully configured WorldState, or None if cancelled
        """
        console.clear()
        console.print(Panel(
            Align.center(Text.from_markup(
                "[bold cyan]G.R.A.P.E.S. DETAILED GENESIS[/]\n\n"
                "[dim]A structured interview to build your world systematically.\n"
                "Answer each category in 1-3 sentences.[/]"
            )),
            box=box.DOUBLE,
            border_style=CYAN,
            padding=(1, 4),
        ))
        console.print()

        # Define the 6 G.R.A.P.E.S. questions
        questions = [
            ("geography", "GEOGRAPHY", "Describe the terrain, climate, and major landmarks of this world."),
            ("religion", "RELIGION", "What faiths, deities, or spiritual practices exist? Who worships what?"),
            ("achievements", "ACHIEVEMENTS", "What is the technology level? Notable inventions? Cultural milestones?"),
            ("politics", "POLITICS", "What government type exists? Who holds power? What factions compete?"),
            ("economics", "ECONOMICS", "How does trade work? What is the currency? What resources are valuable?"),
            ("social", "SOCIAL", "Describe class structure, customs, and daily life for common people."),
        ]

        grapes_data = {}

        for key, title, prompt_text in questions:
            console.print(f"[bold gold1]{title}[/bold gold1]")
            console.print(f"[dim]{prompt_text}[/dim]")
            console.print()

            response = await _ainput("[green]Your answer:[/green] ")
            grapes_data[key] = response.strip() or "No details provided."
            console.print()

        # Also ask for basic world metadata
        console.print(Panel(
            "[bold]WORLD METADATA[/bold]\n\n"
            "[dim]Now provide some basic information about your world.[/]",
            border_style=SILVER,
            box=box.ROUNDED,
        ))
        console.print()

        world_name = await _ainput("[gold1]World Name:[/] ")
        if not world_name.strip():
            world_name = "Deep Genesis World"

        genre_input = await _ainput("[gold1]Genre (e.g. 'Dark Fantasy', 'Space Opera'):[/] [Fantasy] ")
        genre = genre_input.strip() or "Fantasy"

        console.print()
        console.print(Panel(
            "[bold]FACTION CONFIGURATION[/bold]\n\n"
            "[dim]Name the two opposing forces of your world.[/]",
            border_style=SILVER,
            box=box.ROUNDED,
        ))
        console.print()

        crown_name = await _ainput("[cyan]Authority faction name[/] [The Crown]: ")
        terms = {
            "crown": crown_name.strip() or "The Crown",
            "crew": "The Crew",
            "neutral": "The Drifter",
            "campfire": "Campfire",
            "world": "The Wilds",
        }

        crew_name = await _ainput("[magenta]Rebel faction name[/] [The Crew]: ")
        if crew_name.strip():
            terms["crew"] = crew_name.strip()

        neutral_name = await _ainput("[gold1]Neutral archetype[/] [The Drifter]: ")
        if neutral_name.strip():
            terms["neutral"] = neutral_name.strip()

        console.print()

        # Tone selector (reuse existing logic)
        tone_table = Table(
            box=box.ROUNDED,
            border_style=SILVER,
            show_header=True,
            padding=(0, 1),
            title="[bold]SELECT NARRATIVE TONE[/]",
            title_style=GOLD,
        )

        tone_table.add_column("#", style=GOLD, width=3, justify="center")
        tone_table.add_column("", width=3, justify="center")
        tone_table.add_column("Tone", style=EMERALD, width=20)
        tone_table.add_column("Description", style=SILVER)

        tone_keys = list(TONE_PRESETS.keys())
        for i, key in enumerate(tone_keys, 1):
            t = TONE_PRESETS[key]
            tone_table.add_row(str(i), t["icon"], t["display"], f"[dim]{t['desc']}[/]")

        console.print(tone_table)
        console.print()

        while True:
            tone_choice = await _ainput(f"[gold1]Select tone [1-{len(tone_keys)}] (or 'back'/'quit'):[/] ")
            if tone_choice.lower() in ("back", "quit", "exit", "q"):
                console.print("[dim]World creation cancelled.[/]")
                return None
            if tone_choice.isdigit() and 1 <= int(tone_choice) <= len(tone_keys):
                break
            console.print(f"[dim]Enter a number 1-{len(tone_keys)}[/]")

        tone_id = tone_keys[int(tone_choice) - 1]

        # Synthesize primer from G.R.A.P.E.S. data
        primer = (
            f"GEOGRAPHY: {grapes_data['geography']} "
            f"RELIGION: {grapes_data['religion']} "
            f"POLITICS: {grapes_data['politics']} "
            f"ECONOMICS: {grapes_data['economics']} "
            f"SOCIAL: {grapes_data['social']} "
            f"ACHIEVEMENTS: {grapes_data['achievements']}"
        )

        # Create WorldState
        world = WorldState(
            name=world_name,
            system_id="custom",
            system_display="Deep Genesis",
            tone=tone_id,
            genre=genre,
            terms=terms,
            primer=primer,
            grapes=grapes_data,
        )

        # Confirmation
        console.print()
        console.print(Panel(
            f"[bold gold1]{world.name}[/bold gold1]\n"
            f"[dim]{genre} | {TONE_PRESETS[tone_id]['display']}[/]\n\n"
            f"[bold]G.R.A.P.E.S. SUMMARY[/bold]\n"
            + "\n".join([f"[dim]{k.upper()}:[/dim] {v}" for k, v in grapes_data.items()]) +
            f"\n\n[bold]FACTION MAPPING[/bold]\n"
            f"[dim]Authority:[/dim] [cyan]{terms['crown']}[/]\n"
            f"[dim]Rebels:[/dim] [magenta]{terms['crew']}[/]",
            title="[bold]G.R.A.P.E.S. RECEIPT[/]",
            border_style=EMERALD,
            box=box.DOUBLE,
            padding=(1, 3),
        ))
        console.print()

        confirm = await _ainput("[gold1]Forge this world? [Y/n]:[/] ")
        if confirm.lower() in ("n", "no"):
            console.print("[dim]World discarded. Returning...[/]")
            return None

        # Save
        path = self.save_world(world)
        console.print(f"\n[green]> World saved to:[/] [dim]{path}[/]")
        await _ainput("\n[dim]Press Enter to continue...[/dim]")

        return world

    # ─────────────────────────────────────────────────────────────────────
    # TEXT IMPORT — SETTING BIBLE PARSER
    # ─────────────────────────────────────────────────────────────────────

    async def ingest_bible(self, text: str, architect) -> Optional[WorldState]:
        """
        Parse a raw setting bible text into a WorldState.

        Uses the Architect LLM to extract structured data from freeform text.
        Falls back to storing the raw text in bible_text if parsing fails.

        Args:
            text: The raw setting bible text (pasted by user)
            architect: The Architect LLM bridge

        Returns:
            Fully configured WorldState, or None if cancelled
        """
        if not text.strip():
            console.print("[yellow]No text provided. Cancelling import.[/yellow]")
            return None

        console.print()
        console.print(f"[cyan]Received {len(text)} characters. Parsing with LLM...[/cyan]")
        console.print()

        from codex.core.architect import RoutingDecision, ThinkingMode, Complexity, ThermalStatus

        prompt = f"""You are a world-building extraction engine.

Parse the following setting text and extract:
1. World name (if mentioned)
2. Genre (Fantasy, Sci-Fi, Horror, etc.)
3. Two opposing factions (names and brief descriptions)
4. G.R.A.P.E.S. details:
   - Geography: terrain, climate, landmarks
   - Religion: faiths, deities, spiritual practices
   - Achievements: technology, inventions, milestones
   - Politics: government, power structures, factions
   - Economics: trade, currency, resources
   - Social: class structure, customs, daily life
5. Custom terms for 'crown' and 'crew' equivalents

Setting text:
\"\"\"
{text[:3000]}
\"\"\"

Output ONLY in this exact JSON format:
{{
  "name": "World Name or Unknown",
  "genre": "Genre",
  "tone": "gritty or heroic or gothic or comedic",
  "crown_faction": "Authority Faction Name",
  "crew_faction": "Rebel Faction Name",
  "grapes": {{
    "geography": "...",
    "religion": "...",
    "achievements": "...",
    "politics": "...",
    "economics": "...",
    "social": "..."
  }},
  "primer": "2-3 sentence world summary"
}}

Return ONLY valid JSON. No commentary.
"""

        decision = RoutingDecision(
            mode=ThinkingMode.REFLEX,
            model="mimir",
            complexity=Complexity.MEDIUM,
            thermal_status=ThermalStatus.OPTIMAL,
            clearance_granted=True,
            reasoning="Setting Bible import parsing"
        )

        try:
            with console.status("[cyan]Parsing setting bible with LLM...[/cyan]", spinner="dots"):
                response = await architect.invoke_model(
                    query=prompt,
                    system_prompt="You are a data extraction tool. Output only valid JSON.",
                    decision=decision,
                )

                raw = response.content

            # Try to parse JSON
            import json
            import re

            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in LLM response")

            # Extract data
            world_name = data.get("name", "Imported World")
            genre = data.get("genre", "Fantasy")
            tone = data.get("tone", "gritty")
            crown_faction = data.get("crown_faction", "The Authority")
            crew_faction = data.get("crew_faction", "The Resistance")
            grapes_data = data.get("grapes", {})
            primer = data.get("primer", "A world of conflict.")

            # Ensure all G.R.A.P.E.S. keys exist
            for key in ["geography", "religion", "achievements", "politics", "economics", "social"]:
                if key not in grapes_data:
                    grapes_data[key] = "No details extracted."

            console.print("[green]> LLM parsing successful.[/green]")
            console.print()

        except Exception as e:
            console.print(f"[yellow]LLM parsing failed: {e}[/yellow]")
            console.print("[yellow]Storing raw text for manual configuration.[/yellow]")
            console.print()

            # Fallback: store raw text, ask user for basic metadata
            world_name = await _ainput("[gold1]World Name:[/] ")
            if not world_name.strip():
                world_name = "Imported World"

            genre = await _ainput("[gold1]Genre:[/] [Fantasy] ")
            genre = genre.strip() or "Fantasy"

            crown_faction = await _ainput("[cyan]Authority faction name:[/] [The Authority] ")
            crown_faction = crown_faction.strip() or "The Authority"

            crew_faction = await _ainput("[magenta]Rebel faction name:[/] [The Resistance] ")
            crew_faction = crew_faction.strip() or "The Resistance"

            tone = "gritty"
            grapes_data = {}
            primer = text[:300] + "..." if len(text) > 300 else text

        # Build terms
        terms = {
            "crown": crown_faction,
            "crew": crew_faction,
            "neutral": "The Drifter",
            "campfire": "Campfire",
            "world": "The Wilds",
        }

        # Create WorldState
        world = WorldState(
            name=world_name,
            system_id="custom",
            system_display="Text Import",
            tone=tone,
            genre=genre,
            terms=terms,
            primer=primer,
            grapes=grapes_data,
            bible_text=text,
        )

        # Confirmation
        console.print(Panel(
            f"[bold gold1]{world.name}[/bold gold1]\n"
            f"[dim]{genre} | {TONE_PRESETS.get(tone, TONE_PRESETS['gritty'])['display']}[/]\n\n"
            f"[bold]EXTRACTED DATA[/bold]\n"
            f"[dim]Authority:[/dim] [cyan]{crown_faction}[/]\n"
            f"[dim]Rebels:[/dim] [magenta]{crew_faction}[/]\n"
            f"[dim]Primer:[/dim] {primer[:100]}...\n"
            f"[dim]G.R.A.P.E.S. fields:[/dim] {len([v for v in grapes_data.values() if v])}/6",
            title="[bold]IMPORT RECEIPT[/]",
            border_style=EMERALD,
            box=box.DOUBLE,
            padding=(1, 3),
        ))
        console.print()

        confirm = await _ainput("[gold1]Use this imported world? [Y/n]:[/] ")
        if confirm.lower() in ("n", "no"):
            console.print("[dim]Import cancelled. Returning...[/]")
            return None

        # Save
        path = self.save_world(world)
        console.print(f"\n[green]> World saved to:[/] [dim]{path}[/]")
        await _ainput("\n[dim]Press Enter to continue...[/dim]")

        return world

    # ─────────────────────────────────────────────────────────────────────
    # GENESIS WIZARD — THE UI
    # ─────────────────────────────────────────────────────────────────────

    async def run_genesis_wizard(self, architect=None) -> Optional[WorldState]:
        """
        Interactive world creation wizard.

        Returns a fully configured WorldState, or None if cancelled.
        """
        console.clear()

        # ═══════════════════════════════════════════════════════════════
        # HEADER — SIMULATION BOOTLOADER
        # ═══════════════════════════════════════════════════════════════
        console.print(Panel(
            Align.center(Text.from_markup(
                "[bold cyan]W O R L D   G E N E S I S[/]\n\n"
                "[dim]Simulation Bootloader v1.0[/]\n"
                "[dim]Select base reality parameters[/]"
            )),
            box=box.DOUBLE,
            border_style=CYAN,
            padding=(1, 4),
        ))
        console.print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: SYSTEM SELECTOR
        # ═══════════════════════════════════════════════════════════════
        sys_table = Table(
            box=box.HEAVY_EDGE,
            border_style=SILVER,
            show_header=True,
            padding=(0, 1),
            title="[bold]SELECT BASE SIMULATION[/]",
            title_style=GOLD,
        )

        sys_table.add_column("#", style=GOLD, width=3, justify="center")
        sys_table.add_column("", width=3, justify="center")    # icon
        sys_table.add_column("System", style=EMERALD, width=22)
        sys_table.add_column("Tagline", style=SILVER)

        preset_keys = list(SYSTEM_PRESETS.keys())
        for i, key in enumerate(preset_keys, 1):
            p = SYSTEM_PRESETS[key]
            sys_table.add_row(str(i), p["icon"], p["display"], f"[dim]{p['tagline']}[/]")
        sys_table.add_row(str(len(preset_keys) + 1), "🔧", "Custom", "[dim]Define your own reality[/]")

        console.print(sys_table)
        console.print()

        max_sys = len(preset_keys) + 1
        while True:
            choice = await _ainput(f"[gold1]Select simulation [1-{max_sys}]:[/] ")
            if choice.isdigit() and 1 <= int(choice) <= max_sys:
                break
            console.print(f"[dim]Enter a number 1-{max_sys}[/]")

        choice_idx = int(choice)
        is_custom = choice_idx == max_sys

        if is_custom:
            system_id = "custom"
            system_display = "Custom Homebrew"
            genre = "Fantasy"
            terms = {
                "crown": "The Crown",
                "crew": "The Crew",
                "neutral": "The Drifter",
                "campfire": "Campfire",
                "world": "The Wilds",
            }
        else:
            system_id = preset_keys[choice_idx - 1]
            preset = SYSTEM_PRESETS[system_id]
            system_display = preset["display"]
            genre = preset["tagline"]
            terms = dict(preset["terms"])

        console.print()
        console.print(f"[cyan]> Simulation loaded:[/] [bold]{system_display}[/]")
        console.print()

        # ═══════════════════════════════════════════════════════════════
        # NEW STEP: CREATION METHOD SELECTOR
        # ═══════════════════════════════════════════════════════════════
        console.print(Panel(
            "[bold]SELECT WORLD CREATION METHOD[/bold]\n\n"
            "[1] Quick Genesis — Fast, AI-generated world\n"
            "[2] Detailed Genesis (G.R.A.P.E.S.) — Structured interview\n"
            "[3] Import Setting Bible — Paste existing lore",
            border_style=SILVER,
            box=box.ROUNDED,
        ))
        console.print()

        while True:
            method_choice = await _ainput("[gold1]Select method [1/2/3]:[/] ")
            if method_choice in ("1", "2", "3"):
                break
            console.print("[dim]Enter 1, 2, or 3[/dim]")

        # Branch to appropriate creation flow
        if method_choice == "2":
            # G.R.A.P.E.S. Detailed Genesis
            return await self.run_deep_genesis(architect)

        elif method_choice == "3":
            # Text Import
            console.clear()
            console.print(Panel(
                "[bold cyan]TEXT IMPORT WIZARD[/bold cyan]\n\n"
                "[dim]Paste your existing setting bible, wiki text, or notes.\n"
                "Press Enter twice when done (blank line to finish).[/]",
                box=box.DOUBLE,
                border_style=CYAN
            ))
            console.print()

            console.print("[green]Paste your setting text:[/green]")
            console.print("[dim](Enter a blank line to finish)[/dim]")
            console.print()

            lines = []
            try:
                while True:
                    line = await _ainput("")
                    if not line.strip():
                        break
                    lines.append(line)
            except KeyboardInterrupt:
                console.print("\n[yellow]Import cancelled.[/yellow]")
                return None

            source_text = "\n".join(lines)

            if not source_text.strip():
                console.print("[yellow]No text provided. Returning to menu...[/yellow]")
                return None

            return await self.ingest_bible(source_text, architect)

        # If method_choice == "1", continue with Quick Genesis (original flow)
        console.print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 1b: CUSTOM FACTION NAMING (custom mode only)
        # ═══════════════════════════════════════════════════════════════
        if is_custom:
            console.print(Panel(
                "[bold]FACTION CONFIGURATION[/]\n\n"
                "[dim]Name the two opposing forces of your world.[/]",
                border_style=SILVER,
                box=box.ROUNDED,
            ))
            console.print()

            crown_name = await _ainput("[cyan]Authority faction name[/] [The Crown]: ")
            if crown_name.strip():
                terms["crown"] = crown_name.strip()

            crew_name = await _ainput("[magenta]Rebel faction name[/] [The Crew]: ")
            if crew_name.strip():
                terms["crew"] = crew_name.strip()

            neutral_name = await _ainput("[gold1]Neutral archetype[/] [The Drifter]: ")
            if neutral_name.strip():
                terms["neutral"] = neutral_name.strip()

            genre_input = await _ainput("[dim]Genre tag (e.g. 'Cosmic Horror', 'Weird Western')[/] [Fantasy]: ")
            if genre_input.strip():
                genre = genre_input.strip()

            console.print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: TONE SELECTOR
        # ═══════════════════════════════════════════════════════════════
        tone_table = Table(
            box=box.ROUNDED,
            border_style=SILVER,
            show_header=True,
            padding=(0, 1),
            title="[bold]SELECT NARRATIVE TONE[/]",
            title_style=GOLD,
        )

        tone_table.add_column("#", style=GOLD, width=3, justify="center")
        tone_table.add_column("", width=3, justify="center")
        tone_table.add_column("Tone", style=EMERALD, width=20)
        tone_table.add_column("Description", style=SILVER)

        tone_keys = list(TONE_PRESETS.keys())
        for i, key in enumerate(tone_keys, 1):
            t = TONE_PRESETS[key]
            tone_table.add_row(str(i), t["icon"], t["display"], f"[dim]{t['desc']}[/]")

        console.print(tone_table)
        console.print()

        while True:
            tone_choice = await _ainput(f"[gold1]Select tone [1-{len(tone_keys)}] (or 'back'/'quit'):[/] ")
            if tone_choice.lower() in ("back", "quit", "exit", "q"):
                console.print("[dim]World creation cancelled.[/]")
                return None
            if tone_choice.isdigit() and 1 <= int(tone_choice) <= len(tone_keys):
                break
            console.print(f"[dim]Enter a number 1-{len(tone_keys)}[/]")

        tone_id = tone_keys[int(tone_choice) - 1]
        tone_data = TONE_PRESETS[tone_id]

        console.print()
        console.print(f"[cyan]> Tone locked:[/] [bold]{tone_data['display']}[/]")
        console.print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: NAME THE WORLD
        # ═══════════════════════════════════════════════════════════════
        default_name = f"{system_display} - {tone_data['display']}"
        world_name = await _ainput(f"[gold1]Name this world[/] [{default_name}]: ")
        if not world_name.strip():
            world_name = default_name

        console.print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 4: LLM PRIMER GENERATION
        # ═══════════════════════════════════════════════════════════════
        world = WorldState(
            name=world_name,
            system_id=system_id,
            system_display=system_display,
            tone=tone_id,
            genre=genre,
            terms=terms,
        )

        if architect:
            console.print()
            phases = list(GENESIS_PHASES)
            random.shuffle(phases)

            with console.status("", spinner="earth") as status:
                for i, phase in enumerate(phases[:6]):
                    status.update(f"[cyan]{phase}[/]")
                    # Start LLM call on first phase, let spinner run
                    if i == 0:
                        gen_task = asyncio.create_task(
                            self._generate_primer(architect, world)
                        )
                    await asyncio.sleep(0.6)

                status.update("[bold cyan]Compiling reality matrix...[/]")
                world = await gen_task

            console.print("[green]> Genesis complete.[/]")
        else:
            # No architect — skeleton world with no LLM content
            world.primer = (
                f"A world defined by the tension between "
                f"{terms['crown']} and {terms['crew']}."
            )
            console.print("[yellow]> No AI model connected. World created with defaults.[/]")

        console.print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 5: WORLD RECEIPT — CONFIRMATION
        # ═══════════════════════════════════════════════════════════════
        receipt = self._render_world_receipt(world)
        console.print(receipt)
        console.print()

        # Confirm
        confirm = await _ainput("[gold1]Forge this world? [Y/n]:[/] ")
        if confirm.lower() in ("n", "no"):
            console.print("[dim]World discarded. Returning...[/]")
            return None

        # Save
        path = self.save_world(world)
        console.print(f"\n[green]> World saved to:[/] [dim]{path}[/]")
        await _ainput("\n[dim]Press Enter to continue...[/dim]")

        return world

    def _render_world_receipt(self, world: WorldState) -> Panel:
        """Render the World Receipt confirmation panel."""
        tone_data = TONE_PRESETS.get(world.tone, TONE_PRESETS["gritty"])

        # Build term mapping display
        term_lines = []
        term_map = {
            "Authority": ("crown", "cyan"),
            "Rebels": ("crew", "magenta"),
            "Neutral": ("neutral", "gold1"),
            "Rest Site": ("campfire", "yellow"),
            "Overworld": ("world", "green"),
        }
        for label, (key, color) in term_map.items():
            value = world.terms.get(key, "???")
            term_lines.append(f"  [dim]{label:>12}[/]  [{color}]{value}[/]")

        terms_block = "\n".join(term_lines)

        # Build prompt pool counts
        pool_counts = (
            f"  [dim]Crown Dilemmas:[/]  {len(world.prompts_crown) or 'default'}\n"
            f"  [dim] Crew Dilemmas:[/]  {len(world.prompts_crew) or 'default'}\n"
            f"  [dim] World Hazards:[/]  {len(world.prompts_world) or 'default'}\n"
            f"  [dim]Campfire Echoes:[/]  {len(world.prompts_campfire) or 'default'}"
        )

        # Build patron/leader preview
        char_preview = ""
        if world.patrons:
            char_preview += f"  [dim]Patrons:[/] {', '.join(world.patrons[:3])}...\n"
        if world.leaders:
            char_preview += f"  [dim]Leaders:[/] {', '.join(world.leaders[:3])}..."

        # Assemble receipt
        body = (
            f"[bold gold1]{world.name}[/]\n"
            f"[dim]{world.system_display} | {tone_data['display']} | {world.genre}[/]\n"
            f"\n"
            f"[bold]WORLD PRIMER[/]\n"
            f"[italic]{world.primer}[/]\n"
            f"\n"
            f"[bold]FACTION MAPPING[/]\n"
            f"{terms_block}\n"
            f"\n"
            f"[bold]NARRATIVE POOLS[/]\n"
            f"{pool_counts}"
        )

        if char_preview:
            body += f"\n\n[bold]CHARACTERS[/]\n{char_preview}"

        return Panel(
            body,
            title="[bold]⚗️  WORLD RECEIPT  ⚗️[/]",
            box=box.DOUBLE,
            border_style=CYAN,
            padding=(1, 3),
        )

    # ─────────────────────────────────────────────────────────────────────
    # WORLD BROWSER — SELECT FROM SAVED WORLDS
    # ─────────────────────────────────────────────────────────────────────

    async def browse_worlds(self) -> Optional[WorldState]:
        """
        Display saved worlds and let the user pick one.

        Returns the selected WorldState, or None if cancelled.
        """
        worlds = self.list_worlds()

        if not worlds:
            console.print("[dim]No saved worlds found. Use the Genesis Wizard to create one.[/]")
            await _ainput("\n[dim]Press Enter to continue...[/dim]")
            return None

        console.clear()
        console.print(Panel(
            "[bold cyan]SAVED WORLDS[/]\n[dim]Select a reality to load[/]",
            box=box.ROUNDED,
            border_style=CYAN,
        ))
        console.print()

        world_table = Table(
            box=box.ROUNDED,
            border_style=SILVER,
            show_header=True,
            padding=(0, 1),
        )
        world_table.add_column("#", style=GOLD, width=3, justify="center")
        world_table.add_column("Name", style=EMERALD)
        world_table.add_column("System", style=SILVER)
        world_table.add_column("Tone", style=SILVER)

        for i, w in enumerate(worlds, 1):
            tone_data = TONE_PRESETS.get(w.tone, {"display": w.tone})
            world_table.add_row(
                str(i), w.name, w.system_display, tone_data.get("display", w.tone)
            )

        console.print(world_table)
        console.print(f"\n[dim]Enter 0 to cancel[/]")
        console.print()

        while True:
            pick = await _ainput(f"[gold1]Select world [0-{len(worlds)}]:[/] ")
            if pick == "0":
                return None
            if pick.isdigit() and 1 <= int(pick) <= len(worlds):
                selected = worlds[int(pick) - 1]
                console.print(f"\n[cyan]> Loaded:[/] [bold]{selected.name}[/]")
                return selected
            console.print(f"[dim]Enter a number 0-{len(worlds)}[/]")


# =============================================================================
# CONVENIENCE — Module-level access
# =============================================================================

_engine_instance: Optional[WorldEngine] = None


def get_world_engine() -> WorldEngine:
    """Get or create the singleton WorldEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WorldEngine()
    return _engine_instance


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    async def _test():
        engine = WorldEngine()
        world = await engine.run_genesis_wizard(architect=None)
        if world:
            print(f"\nCreated world: {world.name}")
            print(f"Terms: {world.terms}")
            print(f"Saved to: worlds/{world.name.replace(' ', '_')}.json")
        else:
            print("\nWorld creation cancelled.")

    asyncio.run(_test())

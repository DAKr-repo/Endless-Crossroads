#!/usr/bin/env python3
"""
codex_genesis_engine.py — Procedural World Generation Engine
Generates unified worlds for Crown & Crew and Mimir's C.O.D.E.X.

This module provides procedural world generation using G.R.A.P.E.S. tags
(Geography, Religion, Achievements, Politics, Economics, Social) and
faction templates to create complete, playable worlds for the Crown & Crew
narrative engine.

Version: 1.0 (Genesis Core)
"""

import json
import random
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "genesis_data.json"

# WO-V33.0: RAG Service replaces direct CodexRetriever instantiation
_RAG_SERVICE = None
try:
    from codex.core.services.rag_service import get_rag_service
    _RAG_SERVICE = get_rag_service()
except Exception:
    pass

# Optional structured G.R.A.P.E.S. generator (WO-V8.0)
_GRAPES_GENERATOR = None
try:
    from codex.core.world.grapes_engine import GrapesGenerator, GrapesProfile
    _GRAPES_GENERATOR = GrapesGenerator()
    _GRAPES_AVAILABLE = True
except Exception:
    _GRAPES_AVAILABLE = False


class GenesisEngine:
    """Procedural world generator using G.R.A.P.E.S. tags and faction templates."""

    def __init__(self):
        """Load genesis data from JSON."""
        self.data = self._load_data()
        self.grapes = self.data.get("grapes", {})
        self.faction_templates = self.data.get("faction_templates", {})
        self.name_parts = self.data.get("name_parts", {})

    def _load_data(self) -> dict:
        """Load genesis_data.json from the module directory."""
        try:
            if not DATA_PATH.exists():
                console.print(f"[red]Genesis data not found at: {DATA_PATH}[/red]")
                return {}
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            console.print(f"[red]Genesis data error: {e}[/red]")
            return {}

    def roll_unified_world(self, universe_id: Optional[str] = None) -> dict:
        """Generate a complete world by rolling random tags.

        Returns:
            dict with keys: name, genre, tone, grapes (dict of 6 tags or nested structure),
            faction (template dict), terms (crown/crew/neutral/campfire/world mappings)
        """
        # 1. Roll G.R.A.P.E.S. -- use structured generator when available
        grapes_profile = None
        if _GRAPES_AVAILABLE and _GRAPES_GENERATOR:
            seed = random.randint(0, 2**31)
            grapes_profile = _GRAPES_GENERATOR.generate(seed=seed, universe_id=universe_id)
            rolled_grapes = grapes_profile.to_dict()
        else:
            rolled_grapes = {}
            for category in ["geography", "religion", "achievements", "politics", "economics", "social"]:
                options = self.grapes.get(category, ["Unknown"])
                if options:
                    rolled_grapes[category] = random.choice(options)
                else:
                    rolled_grapes[category] = "Unknown"

        # 2. Select a faction template
        template_keys = list(self.faction_templates.keys())
        if not template_keys:
            console.print("[yellow]Warning: No faction templates found, using defaults[/yellow]")
            faction = {
                "name": "Default",
                "crown_title": "The Crown",
                "crown_desc": "Authority and order.",
                "crew_title": "The Crew",
                "crew_desc": "Rebellion and freedom.",
                "neutral_title": "The Drifter",
                "campfire_title": "Campfire",
            }
            template_key = "default"
        else:
            template_key = random.choice(template_keys)
            faction = self.faction_templates[template_key]

        # 3. Generate a world name (Adjective + Noun)
        adjectives = self.name_parts.get("adjectives", ["Lost"])
        nouns = self.name_parts.get("nouns", ["World"])
        adj = random.choice(adjectives) if adjectives else "Lost"
        noun = random.choice(nouns) if nouns else "World"
        world_name = f"The {adj} {noun}"

        # 4. Derive genre and tone from the rolled tags
        genre = self._derive_genre(rolled_grapes)
        tone = self._derive_tone(rolled_grapes)

        # 5. Build terms dict for Crown & Crew compatibility
        terms = {
            "crown": faction.get("crown_title", "The Crown"),
            "crew": faction.get("crew_title", "The Crew"),
            "neutral": faction.get("neutral_title", "The Drifter"),
            "campfire": faction.get("campfire_title", "Campfire"),
            "world": world_name,
        }

        # 6. RAG flavor: retrieve lore chunks to enrich the primer
        rag_flavor = self._retrieve_rag_flavor(genre, tone, rolled_grapes)

        # 7. Build primer text summarizing the world
        if grapes_profile:
            primer = grapes_profile.to_narrative_summary()
        else:
            primer = self._build_primer(world_name, rolled_grapes, faction, rag_flavor)

        result = {
            "name": world_name,
            "genre": genre,
            "tone": tone,
            "grapes": rolled_grapes,
            "faction_template": template_key,
            "faction": faction,
            "terms": terms,
            "primer": primer,
        }
        if rag_flavor:
            result["rag_flavor"] = rag_flavor
        return result

    @staticmethod
    def _flatten_for_derive(grapes: dict, key: str) -> str:
        """Extract a flat string from either rich or flat grapes format."""
        value = grapes.get(key, "")
        if isinstance(value, str):
            return value.lower()
        if isinstance(value, list):
            parts = []
            for entry in value:
                if isinstance(entry, dict):
                    parts.extend(str(v) for v in entry.values())
            return " ".join(parts).lower()
        return ""

    def _derive_genre(self, grapes: dict) -> str:
        """Derive a genre string from the rolled G.R.A.P.E.S. tags."""
        achievements = self._flatten_for_derive(grapes, "achievements") or self._flatten_for_derive(grapes, "arts")
        geography = self._flatten_for_derive(grapes, "geography")

        if any(word in achievements for word in ["gunpowder", "firearms", "rail"]):
            return "Industrial Fantasy"
        elif any(word in achievements for word in ["arcane", "elemental", "telepathy", "golem"]):
            return "High Fantasy"
        elif any(word in geography for word in ["sky-island", "floating"]):
            return "Skyborne Fantasy"
        elif any(word in geography for word in ["underground", "cavern"]):
            return "Underdark Fantasy"
        elif any(word in achievements for word in ["airship"]):
            return "Steampunk Fantasy"
        else:
            return "Dark Fantasy"

    def _derive_tone(self, grapes: dict) -> str:
        """Derive a tone from the rolled tags."""
        politics = self._flatten_for_derive(grapes, "politics")
        social = self._flatten_for_derive(grapes, "social")
        economics = self._flatten_for_derive(grapes, "economics")

        dark_signals = ["slave", "junta", "caste", "segregation", "criminal", "puppet"]
        if any(word in (politics + social + economics) for word in dark_signals):
            return "grim"
        elif "democratic" in politics or "egalitarian" in social or "meritocratic" in social:
            return "heroic"
        else:
            return "gritty"

    def _retrieve_rag_flavor(self, genre: str, tone: str, grapes: dict) -> List[str]:
        """Retrieve lore chunks from FAISS to enrich world generation.

        WO-V33.0: Uses RAG Service instead of direct CodexRetriever.
        Returns a list of short text excerpts, or empty list on failure.
        """
        if _RAG_SERVICE is None:
            return []

        geography = grapes.get("geography", "")
        query = f"{genre} {tone} world themes {geography}"
        try:
            result = _RAG_SERVICE.search_multi(
                query, ["cbr_pnk", "dnd5e"], k_per_system=3
            )
            return result.chunks
        except Exception:
            return []

    def _build_primer(self, name: str, grapes: dict, faction: dict,
                      rag_flavor: Optional[List[str]] = None) -> str:
        """Build a world primer paragraph from the rolled data."""
        lines = [
            f"{name} is a land of {grapes.get('geography', 'unknown terrain')}.",
            f"The people follow {grapes.get('religion', 'unknown faiths')}.",
            f"Their greatest achievement: {grapes.get('achievements', 'unknown')}.",
            f"Power rests with {faction.get('crown_title', 'the Crown')} — {faction.get('crown_desc', 'authority incarnate')}.",
            f"In the shadows, {faction.get('crew_title', 'the Crew')} — {faction.get('crew_desc', 'resistance persists')}.",
            f"The economy runs on {grapes.get('economics', 'unknown trade')}.",
            f"Society is defined by {grapes.get('social', 'unknown structure')}.",
        ]
        if rag_flavor:
            # Weave first 2 RAG chunks into the primer as "lore whispers"
            for chunk in rag_flavor[:2]:
                # Trim to first sentence to keep primer concise
                sentence = chunk.strip().split(".")[0].strip()
                if sentence:
                    lines.append(f"Ancient texts speak of: {sentence}.")
        return " ".join(lines)

    def display_world(self, world: dict) -> None:
        """Display a generated world using Rich formatting."""
        console.print(f"\n[bold gold1]═══ {world['name'].upper()} ═══[/bold gold1]\n")

        grapes_data = world.get("grapes", {})

        # Detect rich vs flat format
        is_rich = isinstance(grapes_data.get("geography"), list)

        if is_rich:
            self._display_rich_grapes(grapes_data)
        else:
            # Legacy flat format
            table = Table(title="G.R.A.P.E.S. Profile", box=box.HEAVY, border_style="gold1")
            table.add_column("Category", style="bold cyan", width=14)
            table.add_column("Detail", style="white")

            grapes_labels = {
                "geography": "Geography",
                "religion": "Religion",
                "achievements": "Achievements",
                "politics": "Politics",
                "economics": "Economics",
                "social": "Social",
            }
            for key, label in grapes_labels.items():
                value = grapes_data.get(key, "—")
                if isinstance(value, str):
                    table.add_row(label, value)
                else:
                    table.add_row(label, str(value))

            console.print(table)

        console.print()

        # Faction Panel
        faction = world["faction"]
        faction_text = (
            f"[bold #DAA520]{faction.get('crown_title', 'The Crown')}[/bold #DAA520]\n"
            f"  {faction.get('crown_desc', 'Authority incarnate')}\n\n"
            f"[bold #CD853F]{faction.get('crew_title', 'The Crew')}[/bold #CD853F]\n"
            f"  {faction.get('crew_desc', 'Resistance persists')}"
        )
        console.print(Panel(
            faction_text,
            title=f"[bold]{faction.get('name', 'Faction')}[/bold] — Faction Template",
            border_style="gold1",
            width=60,
        ))

        # Genre and Tone
        console.print(f"  [bold]Genre:[/bold] {world['genre']}  |  [bold]Tone:[/bold] {world['tone']}\n")

    def _display_rich_grapes(self, grapes_data: dict) -> None:
        """Render the rich structured G.R.A.P.E.S. profile with Rich tables."""
        # Geography -- landmarks table
        geo = grapes_data.get("geography", [])
        if geo:
            table = Table(title="Geography -- Landmarks", box=box.ROUNDED, border_style="green")
            table.add_column("Name", style="bold")
            table.add_column("Terrain", style="cyan")
            table.add_column("Feature", style="dim")
            for lm in geo:
                table.add_row(lm.get("name", "?"), lm.get("terrain", "?"), lm.get("feature", ""))
            console.print(table)

        # Religion -- tenets panel
        rel = grapes_data.get("religion", [])
        if rel:
            lines = []
            for t in rel:
                lines.append(f"[bold]{t.get('doctrine', '?')}[/bold]")
                lines.append(f"  Ritual: {t.get('ritual', '?')}")
                lines.append(f"  Heresy: [red]{t.get('heresy', '?')}[/red]")
                lines.append("")
            console.print(Panel("\n".join(lines), title="Religion -- Tenets", border_style="yellow"))

        # Arts
        arts = grapes_data.get("arts", [])
        if arts:
            table = Table(title="Arts -- Aesthetics", box=box.ROUNDED, border_style="magenta")
            table.add_column("Style", style="bold")
            table.add_column("Form", style="cyan")
            table.add_column("Cultural Mark", style="dim")
            for a in arts:
                table.add_row(a.get("style", "?"), a.get("art_form", "?"), a.get("cultural_mark", ""))
            console.print(table)

        # Politics -- factions
        pol = grapes_data.get("politics", [])
        if pol:
            table = Table(title="Politics -- Factions", box=box.ROUNDED, border_style="red")
            table.add_column("Faction", style="bold")
            table.add_column("Agenda", style="white")
            table.add_column("Clock", style="cyan", justify="center")
            for f in pol:
                table.add_row(f.get("name", "?"), f.get("agenda", "?"), str(f.get("clock_segments", "?")))
            console.print(table)

        # Economics
        econ = grapes_data.get("economics", [])
        if econ:
            table = Table(title="Economics -- Resources", box=box.ROUNDED, border_style="gold1")
            table.add_column("Resource", style="bold")
            table.add_column("Abundance", style="cyan")
            table.add_column("Trade Note", style="dim")
            for e in econ:
                table.add_row(e.get("resource", "?"), e.get("abundance", "?"), e.get("trade_note", ""))
            console.print(table)

        # Social -- taboos
        soc = grapes_data.get("social", [])
        if soc:
            lines = []
            for t in soc:
                lines.append(f"[bold]{t.get('prohibition', '?')}[/bold]")
                lines.append(f"  Punishment: {t.get('punishment', '?')}")
                lines.append(f"  Origin: [dim]{t.get('origin', '?')}[/dim]")
                lines.append("")
            console.print(Panel("\n".join(lines), title="Social -- Taboos", border_style="blue"))

        # Language -- profiles
        lang = grapes_data.get("language", [])
        if lang:
            table = Table(title="Language -- Profiles", box=box.ROUNDED, border_style="bright_cyan")
            table.add_column("Name", style="bold")
            table.add_column("Type", style="cyan")
            table.add_column("Rules", style="dim")
            for lp in lang:
                table.add_row(
                    lp.get("name", "?"),
                    lp.get("phoneme_type", "?"),
                    lp.get("naming_rules", ""),
                )
            console.print(table)

        # Culture -- values
        cul = grapes_data.get("culture", [])
        if cul:
            lines = []
            for cv in cul:
                lines.append(f"[bold]{cv.get('tenet', '?')}[/bold]")
                lines.append(f"  Expression: {cv.get('expression', '?')}")
                lines.append(f"  Consequence: [dim]{cv.get('consequence', '?')}[/dim]")
                lines.append("")
            console.print(Panel("\n".join(lines), title="Culture -- Values", border_style="bright_magenta"))

        # Architecture & Fashion
        arch = grapes_data.get("architecture", [])
        if arch:
            table = Table(title="Architecture & Fashion", box=box.ROUNDED, border_style="dark_olive_green3")
            table.add_column("Style", style="bold")
            table.add_column("Material", style="cyan")
            table.add_column("Motif", style="dim")
            table.add_column("Fashion", style="magenta")
            table.add_column("Textile", style="green")
            table.add_column("Accessory", style="yellow")
            for ap in arch:
                table.add_row(
                    ap.get("building_style", "?"),
                    ap.get("material", "?"),
                    ap.get("motif", "?"),
                    ap.get("clothing_style", "?"),
                    ap.get("textile", "?"),
                    ap.get("accessory", "?"),
                )
            console.print(table)

    def to_world_state(self, world: dict) -> "WorldState":
        """Convert a rolled world dict into a WorldState object.

        This bridges the Genesis Engine with the existing WorldEngine/CrownAndCrewEngine.

        Args:
            world: Dict from roll_unified_world()

        Returns:
            WorldState object compatible with codex_world_engine.py

        Raises:
            ImportError: If WorldState is not available
        """
        from codex.world.world_wizard import WorldState  # Deferred import to prevent circular dependency

        # Create WorldState with the rolled data
        # Match the exact field names from WorldState dataclass
        state = WorldState(
            name=world["name"],
            system_id="genesis",
            system_display="Procedural Genesis",
            tone=world["tone"],
            genre=world["genre"],
            terms=world["terms"],
            primer=world["primer"],
            grapes=world["grapes"],
            prompts_crown=[],
            prompts_crew=[],
            prompts_world=[],
            prompts_campfire=[],
            secret_witness="",
            patrons=[],
            leaders=[],
        )
        return state


# --- Main demo ---
if __name__ == "__main__":
    try:
        console.print(Panel(
            "[bold cyan]GENESIS ENGINE — PROCEDURAL WORLD GENERATOR[/bold cyan]\n\n"
            "[dim]Rolling a unified world using G.R.A.P.E.S. tags and faction templates...[/dim]",
            box=box.DOUBLE,
            border_style="cyan"
        ))
        console.print()

        engine = GenesisEngine()

        if not engine.data:
            console.print("[red]Failed to load genesis_data.json. Cannot proceed.[/red]")
            exit(1)

        world = engine.roll_unified_world()
        engine.display_world(world)

        console.print()
        console.print(Panel(
            world["primer"],
            title="[bold]World Primer[/bold]",
            border_style="grey50",
            width=70
        ))

        console.print()
        console.print("[bold green]✓ World generation successful![/bold green]")

        # Test WorldState conversion
        console.print()
        console.print("[dim]Testing WorldState conversion...[/dim]")
        try:
            ws = engine.to_world_state(world)
            console.print(f"[green]✓ WorldState created: {ws.name}[/green]")
            console.print(f"  System: {ws.system_display}")
            console.print(f"  Genre: {ws.genre} | Tone: {ws.tone}")
            console.print(f"  Terms: Crown='{ws.terms.get('crown')}', Crew='{ws.terms.get('crew')}'")
            console.print(f"  G.R.A.P.E.S. fields: {len([k for k in ws.grapes.keys()])}/6")
        except Exception as e:
            console.print(f"[red]✗ WorldState conversion failed: {e}[/red]")

        console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()

"""
codex_boot_wizard.py - The Terminal Main Menu (RPG Style)

A "Fantasy RPG" styled CLI interface for C.O.D.E.X.
Presents system vitals as character stats and operations as quests.

Library: rich (console, panel, prompt)
Aesthetic: Fantasy RPG with borders, gold/crimson colors, boxed menus

This is the UNIFIED ENTRY POINT for the Desktop Shortcut.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path so codex.* imports resolve
# (needed when launched from desktop shortcut or maintenance/ directory)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Attempt early import of main agent to catch missing deps
try:
    import codex_agent_main
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    AGENT_IMPORT_ERROR = str(e)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich import box

from codex.core.cortex import get_cortex, ThermalStatus

# Define base directory for relative paths (project root, not maintenance/)
CODEX_DIR = Path(__file__).resolve().parent.parent

# Initialize Rich console
console = Console()

# Color scheme - Fantasy RPG
GOLD = "bold yellow"
CRIMSON = "bold red"
EMERALD = "bold green"
SILVER = "dim white"
ROYAL_BLUE = "bold blue"
PARCHMENT = "wheat1"


class GameSave:
    """Represents a saved campaign."""

    SAVE_DIR = Path(__file__).resolve().parent.parent / "saves"

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
        """Save to disk."""
        self.SAVE_DIR.mkdir(exist_ok=True)
        save_path = self.SAVE_DIR / f"{self.name}.json"
        with open(save_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def list_saves(cls) -> list["GameSave"]:
        """List all saved campaigns."""
        saves = []
        if cls.SAVE_DIR.exists():
            for save_file in cls.SAVE_DIR.glob("*.json"):
                try:
                    with open(save_file) as f:
                        data = json.load(f)
                        saves.append(cls.from_dict(data))
                except Exception:
                    pass
        return sorted(saves, key=lambda s: s.created, reverse=True)

    @classmethod
    def load(cls, name: str) -> Optional["GameSave"]:
        """Load a specific save."""
        save_path = cls.SAVE_DIR / f"{name}.json"
        if save_path.exists():
            with open(save_path) as f:
                return cls.from_dict(json.load(f))
        return None


class BootWizard:
    """
    The Terminal Game Menu - RPG Style Interface.

    Presents C.O.D.E.X. system as a fantasy RPG character sheet
    with vitals displayed as health/stamina bars.
    """

    TITLE_ART = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     ██████╗ ██████╗ ██████╗ ███████╗██╗  ██╗                      ║
║    ██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝                      ║
║    ██║     ██║   ██║██║  ██║█████╗   ╚███╔╝                       ║
║    ██║     ██║   ██║██║  ██║██╔══╝   ██╔██╗                       ║
║    ╚██████╗╚██████╔╝██████╔╝███████╗██╔╝ ██╗                      ║
║     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝                      ║
║                                                                   ║
║         Chronicles of Destiny: Endless Crossroads                 ║
║                                                                   ║
║              ~ Where all fates meet at the X. ~                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""

    def __init__(self):
        self.cortex = get_cortex()
        self.current_save: Optional[GameSave] = None
        self.running = True

    def render_title(self):
        """Render the game title."""
        console.print(Text(self.TITLE_ART, style=GOLD))

    def render_vitals(self):
        """Render system vitals as RPG stats."""
        state = self.cortex.read_metabolic_state()

        # Calculate "health" percentages
        # CPU Temp: 40°C = 100% stamina, 80°C = 0% stamina
        temp = state.cpu_temp_celsius
        stamina_pct = max(0, min(100, (80 - temp) / 40 * 100))

        # RAM: Available as "Mana"
        mana_pct = 100 - state.ram_usage_percent

        # Determine status text
        status_map = {
            ThermalStatus.OPTIMAL: ("⚔️  BATTLE READY", EMERALD),
            ThermalStatus.FATIGUED: ("🛡️  WINDED", "yellow"),
            ThermalStatus.CRITICAL: ("💀 EXHAUSTED", CRIMSON),
            ThermalStatus.RECOVERY: ("🧘 MEDITATING", ROYAL_BLUE),
        }
        status_text, status_color = status_map.get(
            state.thermal_status,
            ("❓ UNKNOWN", SILVER)
        )

        # Build vitals table
        vitals = Table(
            box=box.DOUBLE_EDGE,
            border_style=GOLD,
            title="[bold]═══ ADVENTURER VITALS ═══[/bold]",
            title_style=GOLD,
            show_header=False,
            padding=(0, 1)
        )

        vitals.add_column("Stat", style=PARCHMENT)
        vitals.add_column("Bar", width=30)
        vitals.add_column("Value", justify="right", style=SILVER)

        # Stamina (CPU Temp inverted)
        stamina_bar = self._render_bar(stamina_pct, "green", "red")
        vitals.add_row(
            "🔥 Stamina",
            stamina_bar,
            f"{temp:.1f}°C"
        )

        # Mana (RAM Available)
        mana_bar = self._render_bar(mana_pct, "blue", "purple")
        vitals.add_row(
            "✨ Mana",
            mana_bar,
            f"{state.ram_available_gb:.1f}GB free"
        )

        # DeepSeek clearance as "Arcane Power"
        if state.metabolic_clearance:
            arcane = "[bold green]█████████████████████████████[/] ✓ AVAILABLE"
        else:
            arcane = "[bold red]░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[/] ✗ SEALED"
        vitals.add_row(
            "🔮 Arcane Power",
            arcane,
            ""
        )

        # Status row
        vitals.add_row(
            "📜 Status",
            f"[{status_color}]{status_text}[/]",
            ""
        )

        console.print(vitals)

    def _render_bar(self, percentage: float, good_color: str, bad_color: str) -> str:
        """Render a progress bar with color gradient."""
        filled = int(percentage / 100 * 29)
        empty = 29 - filled

        if percentage > 60:
            color = good_color
        elif percentage > 30:
            color = "yellow"
        else:
            color = bad_color

        return f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/]"

    def render_main_menu(self):
        """Render the main menu."""
        menu = Table(
            box=box.HEAVY,
            border_style=CRIMSON,
            show_header=False,
            padding=(0, 2),
            title="[bold]══════ MAIN QUEST ══════[/bold]",
            title_style=CRIMSON
        )

        menu.add_column("Option", style=GOLD)
        menu.add_column("Description", style=PARCHMENT)

        menu.add_row("[1]", "⚔️  New Campaign     — Begin a new adventure")
        menu.add_row("[2]", "📜 Load Game        — Continue your journey")
        menu.add_row("[3]", "⚙️  Settings         — Configure thy tools")
        menu.add_row("[4]", "🧙 Summon DM        — Awaken the Dungeon Master")
        menu.add_row("[5]", "🔧 Maestro          — Maintenance Wizard")
        menu.add_row("[6]", "🚪 Exit             — Return to the mundane world")

        console.print()
        console.print(Align.center(menu))
        console.print()

    def new_campaign_wizard(self):
        """Wizard to create a new campaign."""
        console.clear()

        header = Panel(
            "[bold]✨ NEW CAMPAIGN WIZARD ✨[/bold]\n\n"
            "Prepare to forge a new legend...",
            box=box.DOUBLE,
            border_style=GOLD,
            padding=(1, 4)
        )
        console.print(Align.center(header))
        console.print()

        # World selection
        worlds_table = Table(
            box=box.ROUNDED,
            border_style=ROYAL_BLUE,
            title="[bold]Choose Thy Realm[/bold]",
            show_header=True
        )
        worlds_table.add_column("#", style=GOLD, width=3)
        worlds_table.add_column("World", style=EMERALD)
        worlds_table.add_column("Description", style=SILVER)

        worlds = [
            ("Forgotten Realms", "Classic D&D high fantasy"),
            ("Eberron", "Magitech noir adventure"),
            ("Ravenloft", "Gothic horror domains"),
            ("Homebrew", "Craft your own world"),
        ]

        for i, (name, desc) in enumerate(worlds, 1):
            worlds_table.add_row(str(i), name, desc)

        console.print(worlds_table)
        console.print()

        world_choice = IntPrompt.ask(
            "[gold1]Select realm[/]",
            choices=["1", "2", "3", "4"],
            default=1
        )
        world_name = worlds[world_choice - 1][0]

        # Campaign name
        console.print()
        campaign_name = Prompt.ask(
            "[gold1]Name thy campaign[/]",
            default=f"Quest of {datetime.now().strftime('%B')}"
        )

        # Starting level
        starting_level = IntPrompt.ask(
            "[gold1]Starting level[/]",
            default=1
        )

        # Confirm
        console.print()
        summary = Panel(
            f"[bold]Campaign:[/bold] {campaign_name}\n"
            f"[bold]World:[/bold] {world_name}\n"
            f"[bold]Starting Level:[/bold] {starting_level}",
            title="[bold gold1]Campaign Summary[/bold gold1]",
            box=box.DOUBLE,
            border_style=EMERALD
        )
        console.print(summary)

        if Confirm.ask("[gold1]Forge this campaign?[/]", default=True):
            # Create and save
            save = GameSave(
                name=campaign_name.replace(" ", "_"),
                world=world_name,
                level=starting_level,
                created=datetime.now()
            )
            save.save()
            self.current_save = save

            console.print()
            console.print(Panel(
                f"[bold green]✓ Campaign '{campaign_name}' created![/bold green]\n\n"
                "May your dice roll true, adventurer.",
                border_style=EMERALD
            ))
            console.input("\n[dim]Press Enter to continue...[/dim]")
        else:
            console.print("[yellow]Campaign creation cancelled.[/yellow]")
            console.input("\n[dim]Press Enter to continue...[/dim]")

    def load_game_menu(self):
        """Display saved games for loading."""
        console.clear()

        header = Panel(
            "[bold]📜 CHRONICLE OF ADVENTURES 📜[/bold]",
            box=box.DOUBLE,
            border_style=GOLD
        )
        console.print(Align.center(header))
        console.print()

        saves = GameSave.list_saves()

        if not saves:
            console.print(Panel(
                "[yellow]No saved campaigns found.[/yellow]\n\n"
                "Begin a [bold]New Campaign[/bold] to start your journey.",
                border_style="yellow"
            ))
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        saves_table = Table(
            box=box.ROUNDED,
            border_style=ROYAL_BLUE,
            show_header=True
        )
        saves_table.add_column("#", style=GOLD, width=3)
        saves_table.add_column("Campaign", style=EMERALD)
        saves_table.add_column("World", style=PARCHMENT)
        saves_table.add_column("Level", justify="center")
        saves_table.add_column("Created", style=SILVER)

        for i, save in enumerate(saves, 1):
            saves_table.add_row(
                str(i),
                save.name.replace("_", " "),
                save.world,
                f"Lv.{save.level}",
                save.created.strftime("%Y-%m-%d")
            )

        console.print(saves_table)
        console.print()

        choice = Prompt.ask(
            "[gold1]Select save to load (or 'b' to go back)[/]",
            default="b"
        )

        if choice.lower() == "b":
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(saves):
                self.current_save = saves[idx]
                console.print(f"\n[green]✓ Loaded: {self.current_save.name}[/green]")
                console.input("\n[dim]Press Enter to continue...[/dim]")
            else:
                console.print("[red]Invalid selection.[/red]")
                console.input("\n[dim]Press Enter to continue...[/dim]")
        except ValueError:
            console.print("[red]Invalid input.[/red]")
            console.input("\n[dim]Press Enter to continue...[/dim]")

    def settings_menu(self):
        """Settings configuration menu."""
        console.clear()

        header = Panel(
            "[bold]⚙️  ARCANE CONFIGURATION ⚙️[/bold]",
            box=box.DOUBLE,
            border_style=GOLD
        )
        console.print(Align.center(header))
        console.print()

        settings_table = Table(
            box=box.ROUNDED,
            border_style=SILVER,
            show_header=True
        )
        settings_table.add_column("#", style=GOLD, width=3)
        settings_table.add_column("Setting", style=EMERALD)
        settings_table.add_column("Current Value", style=PARCHMENT)

        # Read current config
        settings = [
            ("Thermal Threshold (Fatigue)", "65°C"),
            ("Thermal Threshold (Critical)", "75°C"),
            ("Deep Thinking Model", "deepseek-r1:1.5b"),
            ("Reflex Model", "qwen2.5-coder:1.5b"),
            ("Voice Enabled", "Yes"),
        ]

        for i, (name, value) in enumerate(settings, 1):
            settings_table.add_row(str(i), name, value)

        console.print(settings_table)
        console.print()
        console.print("[dim]Settings are configured in thermal_profiles.yaml[/dim]")
        console.input("\n[dim]Press Enter to continue...[/dim]")

    @staticmethod
    def _scan_content_and_modules() -> dict:
        """Scan config/ and vault_maps/modules/ for content inventory.

        Returns dict with:
            config_categories: list of config dirs with file counts
            module_count: total adventure modules found
            modules_by_system: dict of system_id -> list of module names
            total_config_files: total JSON files across config/
        """
        result = {
            "config_categories": [],
            "module_count": 0,
            "modules_by_system": {},
            "total_config_files": 0,
        }

        # Scan config/ categories
        config_dir = CODEX_DIR / "config"
        if config_dir.is_dir():
            for cat_dir in sorted(config_dir.iterdir()):
                if not cat_dir.is_dir():
                    continue
                jsons = list(cat_dir.glob("*.json"))
                if jsons:
                    result["config_categories"].append({
                        "name": cat_dir.name,
                        "count": len(jsons),
                    })
                    result["total_config_files"] += len(jsons)

        # Scan vault_maps/modules/
        modules_dir = CODEX_DIR / "vault_maps" / "modules"
        if modules_dir.is_dir():
            for entry in sorted(modules_dir.iterdir()):
                if not entry.is_dir():
                    continue
                manifest = entry / "module_manifest.json"
                if not manifest.exists():
                    continue
                try:
                    data = json.loads(manifest.read_text())
                    sid = data.get("system_id", "unknown")
                    name = data.get("display_name", entry.name)
                    result["module_count"] += 1
                    result["modules_by_system"].setdefault(sid, []).append(name)
                except Exception:
                    continue

        return result

    def vault_scan(self):
        """Scan vault for new/changed PDFs and content inventory."""
        # Phase 1: PDF vault changes
        vault_new = 0
        vault_changed = 0
        vault_tracked = 0
        vault_files = []
        try:
            from maintenance.codex_index_builder import check_vault_changes
            changes = check_vault_changes()
            vault_new = len(changes.get("new", []))
            vault_changed = len(changes.get("changed", []))
            vault_tracked = changes.get("total_tracked", 0)
            vault_files = changes.get("new", []) + changes.get("changed", [])
        except Exception:
            pass

        # Phase 2: Content and module inventory
        content = self._scan_content_and_modules()
        module_count = content["module_count"]
        config_count = content["total_config_files"]
        systems = content["modules_by_system"]

        # Build display
        has_vault_changes = vault_new > 0 or vault_changed > 0
        has_content = module_count > 0 or config_count > 0

        if not has_vault_changes and not has_content:
            console.print(Panel(
                f"[{EMERALD}]Library up to date[/] — "
                f"{vault_tracked} tomes catalogued.",
                border_style=EMERALD,
                box=box.ROUNDED,
            ))
            return

        lines = []

        # Content inventory summary
        if has_content:
            lines.append(f"[{EMERALD}]Content Library:[/]")
            if config_count:
                cats = ", ".join(
                    f"{c['name']}({c['count']})"
                    for c in content["config_categories"]
                )
                lines.append(f"  Config: [bold]{config_count}[/bold] files across {cats}")
            if module_count:
                sys_summary = ", ".join(
                    f"{sid}({len(mods)})"
                    for sid, mods in sorted(systems.items())
                )
                lines.append(
                    f"  Modules: [bold]{module_count}[/bold] adventures across {sys_summary}"
                )
            lines.append("")

        # Vault PDF changes
        if has_vault_changes:
            summary_parts = []
            if vault_new:
                summary_parts.append(f"[bold]{vault_new}[/bold] new tome{'s' if vault_new != 1 else ''}")
            if vault_changed:
                summary_parts.append(f"[bold]{vault_changed}[/bold] changed scroll{'s' if vault_changed != 1 else ''}")
            lines.append(f"[{GOLD}]Vault changes:[/] {', '.join(summary_parts)}")
            display_files = vault_files[:8]
            for f in display_files:
                lines.append(f"  [dim]•[/dim] {f}")
            if len(vault_files) > 8:
                lines.append(f"  [dim]... and {len(vault_files) - 8} more[/dim]")

        border = GOLD if has_vault_changes else EMERALD
        console.print(Panel(
            "\n".join(lines),
            title="[bold]Library Scanner[/bold]",
            border_style=border,
            box=box.ROUNDED,
        ))

        if has_vault_changes:
            if Confirm.ask(f"[{GOLD}]Run the Maestro to index them?[/]", default=True):
                try:
                    from maintenance.codex_maestro import _run_all
                    console.print(f"\n[{GOLD}]Launching Maestro...[/]")
                    _run_all()
                    console.print(f"[{EMERALD}]Maestro complete.[/]")
                except Exception as e:
                    console.print(f"[{CRIMSON}]Maestro error: {e}[/]")
            else:
                console.print(f"[dim]Skipping — you can run Maestro later from the menu.[/dim]")

    def launch_maestro(self):
        """Launch the Maestro maintenance wizard."""
        console.clear()

        header = Panel(
            "[bold]🔧 MAESTRO — Maintenance Wizard 🔧[/bold]",
            box=box.DOUBLE,
            border_style=GOLD,
        )
        console.print(Align.center(header))
        console.print()

        try:
            from maintenance.codex_maestro import main as maestro_main
            maestro_main()
        except Exception as e:
            console.print(f"[{CRIMSON}]Maestro error: {e}[/]")
            console.input("\n[dim]Press Enter to continue...[/dim]")

    def summon_dm(self):
        """Launch the Discord bot (Dungeon Master)."""
        console.clear()

        summoning = Panel(
            "[bold gold1]🧙 SUMMONING THE DUNGEON MASTER 🧙[/bold gold1]\n\n"
            "[dim]Channeling arcane energies...[/dim]",
            box=box.DOUBLE,
            border_style=CRIMSON
        )
        console.print(Align.center(summoning))
        console.print()

        # Check if token is configured
        from dotenv import load_dotenv
        load_dotenv(CODEX_DIR / ".env")

        if not os.getenv("DISCORD_TOKEN"):
            console.print(Panel(
                "[bold red]⚠️  NO DISCORD TOKEN FOUND[/bold red]\n\n"
                "The summoning circle is incomplete!\n\n"
                "Create a [bold].env[/bold] file with:\n"
                "[dim]DISCORD_TOKEN=your_token_here[/dim]",
                border_style=CRIMSON
            ))
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Confirm launch
        if not Confirm.ask("[gold1]Awaken the Dungeon Master?[/]", default=True):
            return

        console.print()
        console.print("[bold green]✨ The Dungeon Master awakens![/bold green]")
        console.print("[dim]Starting codex_agent_main.py...[/dim]")
        console.print()

        # Launch the bot
        try:
            subprocess.run([sys.executable, "codex_agent_main.py"], cwd=str(CODEX_DIR))
        except KeyboardInterrupt:
            console.print("\n[yellow]The Dungeon Master returns to slumber.[/yellow]")
        except Exception as e:
            console.print(f"[red]Summoning failed: {e}[/red]")

        console.input("\n[dim]Press Enter to continue...[/dim]")

    def run(self):
        """Main loop."""
        first_loop = True
        while self.running:
            console.clear()
            self.render_title()
            self.render_vitals()

            if first_loop:
                self.vault_scan()
                first_loop = False

            self.render_main_menu()

            # Current campaign indicator
            if self.current_save:
                console.print(
                    f"[dim]Active Campaign: [bold]{self.current_save.name}[/bold] "
                    f"({self.current_save.world}, Lv.{self.current_save.level})[/dim]"
                )
                console.print()

            choice = Prompt.ask(
                "[gold1]Choose thy path[/]",
                choices=["1", "2", "3", "4", "5", "6"],
                default="4"
            )

            if choice == "1":
                self.new_campaign_wizard()
            elif choice == "2":
                self.load_game_menu()
            elif choice == "3":
                self.settings_menu()
            elif choice == "4":
                self.summon_dm()
            elif choice == "5":
                self.launch_maestro()
            elif choice == "6":
                self.running = False
                console.clear()
                console.print(Panel(
                    "[bold gold1]Until we meet again, brave adventurer.[/bold gold1]\n\n"
                    "[dim]May your rolls be natural 20s.[/dim]",
                    box=box.DOUBLE,
                    border_style=GOLD
                ))


def main(auto_launch: bool = False):
    """
    Entry point.

    Args:
        auto_launch: If True, skip menu and go directly to main agent.
    """
    wizard = BootWizard()
    try:
        if auto_launch:
            # Unified boot sequence - show visuals then hand off
            console.clear()
            wizard.render_title()
            wizard.render_vitals()

            # Vault scan — prompt if new PDFs detected
            wizard.vault_scan()

            console.print()
            console.print("[bold green]████ SYSTEM READY ████[/bold green]", justify="center")
            console.print()
            time.sleep(1)

            console.print("[bold magenta]🚀 Handing off to Main Agent...[/bold magenta]", justify="center")
            time.sleep(0.5)

            if AGENT_AVAILABLE:
                # Clear screen for clean transition
                console.clear()
                # Execute the main agent's entry point directly
                codex_agent_main.main()
            else:
                console.print()
                console.print(f"[bold red]⚠️  Import Error:[/bold red] {AGENT_IMPORT_ERROR}")
                console.print("[yellow]Attempting fallback launch...[/yellow]")
                time.sleep(1)
                os.system("python codex_agent_main.py")
        else:
            # Standard menu mode
            wizard.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Farewell, adventurer.[/yellow]")


if __name__ == "__main__":
    # Default to showing the full RPG menu with all features
    # Use --auto flag to skip menu and launch main agent directly
    if "--auto" in sys.argv:
        main(auto_launch=True)
    else:
        main(auto_launch=False)

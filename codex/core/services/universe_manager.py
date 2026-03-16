"""
UniverseManager — Cross-module namespace isolation & star chart TUI.
=====================================================================

Prevents Narrative Bleed between unrelated campaigns by scoping
cross-module broadcasts to a shared ``universe_id``.

Storage: ``saves/universe_registry.json`` (auto-created).
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich import box


# =========================================================================
# DATA MODEL
# =========================================================================

@dataclass
class UniverseLink:
    """A universe scope and its linked campaign modules."""
    universe_id: str
    modules: List[str] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now().isoformat())


# =========================================================================
# UNIVERSE MANAGER
# =========================================================================

class UniverseManager:
    """Registry of universe scopes and cross-module links."""

    def __init__(self, config_path: Optional[Path] = None):
        from codex.paths import SAVES_DIR
        self._config_path = config_path or (SAVES_DIR / "universe_registry.json")
        self._universes: Dict[str, UniverseLink] = {}
        self.load()

    # ── Query ────────────────────────────────────────────────────────

    def list_universes(self) -> List[UniverseLink]:
        return list(self._universes.values())

    def get_universe_for_module(self, module_id: str) -> Optional[str]:
        """Return the universe_id containing *module_id*, or None."""
        for uid, link in self._universes.items():
            if module_id in link.modules:
                return uid
        return None

    def are_linked(self, module_a: str, module_b: str) -> bool:
        """Check if two modules share a universe."""
        uid_a = self.get_universe_for_module(module_a)
        uid_b = self.get_universe_for_module(module_b)
        if uid_a is None or uid_b is None:
            return False
        return uid_a == uid_b

    # ── Mutation ─────────────────────────────────────────────────────

    def create_universe(self, universe_id: str) -> UniverseLink:
        """Create a new empty universe scope."""
        link = UniverseLink(universe_id=universe_id)
        self._universes[universe_id] = link
        self.save()
        return link

    def link_module(self, universe_id: str, module_id: str) -> None:
        """Add a module to a universe (creates universe if needed)."""
        if universe_id not in self._universes:
            self.create_universe(universe_id)
        link = self._universes[universe_id]
        if module_id not in link.modules:
            link.modules.append(module_id)
            self.save()

    def unlink_module(self, universe_id: str, module_id: str) -> None:
        """Remove a module from a universe."""
        link = self._universes.get(universe_id)
        if link and module_id in link.modules:
            link.modules.remove(module_id)
            self.save()

    # ── Persistence ──────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "universes": {
                uid: {
                    "universe_id": l.universe_id,
                    "modules": l.modules,
                    "created": l.created,
                }
                for uid, l in self._universes.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> Dict[str, UniverseLink]:
        universes = {}
        for uid, ld in data.get("universes", {}).items():
            universes[uid] = UniverseLink(
                universe_id=ld["universe_id"],
                modules=ld.get("modules", []),
                created=ld.get("created", ""),
            )
        return universes

    def save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def load(self) -> None:
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    data = json.load(f)
                self._universes = self.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                self._universes = {}
        else:
            self._universes = {}

    # ── Star Chart TUI ───────────────────────────────────────────────

    def render_star_chart(self, console: Optional[Console] = None) -> None:
        """Rich TUI visualization of universe topology."""
        con = console or Console()

        if not self._universes:
            con.print("[dim]No universes registered. Link modules to create one.[/dim]")
            return

        tree = Tree("[bold cyan]UNIVERSE STAR CHART[/bold cyan]")

        for uid, link in self._universes.items():
            branch = tree.add(f"[bold yellow]{uid}[/bold yellow]  [dim](created {link.created[:10]})[/dim]")
            if link.modules:
                for mod in link.modules:
                    branch.add(f"[green]{mod}[/green]")
            else:
                branch.add("[dim]No modules linked[/dim]")

        con.print(tree)
        con.print()

        # Summary table
        table = Table(title="Universe Summary", box=box.SIMPLE_HEAVY, show_lines=False)
        table.add_column("Universe", style="bold yellow")
        table.add_column("Modules", style="green")
        for uid, link in self._universes.items():
            table.add_row(uid, ", ".join(link.modules) if link.modules else "-")
        con.print(table)

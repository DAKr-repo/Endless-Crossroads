"""
PlatformTutorial — Contextual hint system + structured tutorial browser.
=========================================================================

Tracks command usage per interface and provides hints for commands
used fewer than 3 times.  Stats persist to ``session_stats.json``.

Extended with:
  - TutorialPage / TutorialModule dataclasses for structured content
  - TutorialRegistry — class-level singleton dict (mirrors ENGINE_REGISTRY)
  - PlatformTutorial — completion tracking on top of original hint system
  - TutorialBrowser — Rich three-panel TUI (mirrors LibrarianTUI patterns)

JSON schema for session_stats.json (backward-compatible):
  New format:
    {
      "command_usage":     { "<cmd>": { "<iface>": <count> } },
      "tutorial_completion": { "<module_id>": { "completed": bool,
                                                "pages_viewed": [...],
                                                "timestamp": "ISO" } }
    }
  Old (flat) format — entire dict treated as command_usage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TutorialPage:
    """A single page within a TutorialModule.

    Attributes:
        page_id: Unique identifier, e.g. ``"movement_basics_1"``.
        title: Short heading shown in the content panel.
        content: Rich markup string (may include ``[bold]``, ``[dim]`` etc.).
        page_type: ``"reference"`` (read-only) or ``"interactive"`` (input validated).
        prompt: Shown below content when page_type == ``"interactive"``.
        valid_inputs: Accepted answers for interactive pages (case-insensitive).
        success_message: Shown on a correct interactive answer.
    """

    page_id: str
    title: str
    content: str
    page_type: str = "reference"
    prompt: str = ""
    valid_inputs: list = field(default_factory=list)
    success_message: str = ""


@dataclass
class TutorialModule:
    """A named sequence of TutorialPages belonging to a game system.

    Attributes:
        module_id: Unique identifier, e.g. ``"burnwillow_movement"``.
        title: Human-readable name, e.g. ``"Movement & Navigation"``.
        description: One-line description shown in the browser index.
        system_id: The game system this module belongs to, e.g. ``"burnwillow"``.
        category: Display category — usually identical to *system_id*.
        pages: Ordered list of TutorialPage objects.
        prerequisite: Optional module_id that must be completed first.
    """

    module_id: str
    title: str
    description: str
    system_id: str
    category: str
    pages: List[TutorialPage] = field(default_factory=list)
    prerequisite: Optional[str] = None


# ---------------------------------------------------------------------------
# TutorialRegistry
# ---------------------------------------------------------------------------

class TutorialRegistry:
    """Class-level singleton registry for TutorialModule objects.

    Mirrors ENGINE_REGISTRY from codex.core.engine_protocol — a plain
    class dict populated at import time.
    """

    _modules: Dict[str, TutorialModule] = {}

    @classmethod
    def register(cls, module: TutorialModule) -> None:
        """Register a TutorialModule under its module_id."""
        cls._modules[module.module_id] = module

    @classmethod
    def get_module(cls, module_id: str) -> Optional[TutorialModule]:
        """Return a module by ID, or None if not registered."""
        return cls._modules.get(module_id)

    @classmethod
    def get_modules_for_category(cls, category: str) -> List[TutorialModule]:
        """Return all modules whose category matches *category*."""
        return [m for m in cls._modules.values() if m.category == category]

    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Return sorted list of distinct category strings."""
        return sorted({m.category for m in cls._modules.values()})

    @classmethod
    def get_all_modules(cls) -> List[TutorialModule]:
        """Return all registered modules in registration order."""
        return list(cls._modules.values())


# ---------------------------------------------------------------------------
# PlatformTutorial  (original hint system + completion tracking)
# ---------------------------------------------------------------------------

class PlatformTutorial:
    """Tracks command usage and provides contextual hints.

    Persists two data structures to ``session_stats.json``:
      - ``_usage``      — existing command-usage counters
      - ``_completion`` — per-module tutorial completion state
    """

    LESSONS: Dict[str, str] = {
        "look": "Tip: 'look' surveys the room and updates the sidebar with details.",
        "search": "Tip: 'search' performs a thorough sweep (Wits check). May find hidden items.",
        "scout": "Tip: 'scout' lets you peek at an adjacent room without entering.",
        "attack": "Tip: 'attack <target>' initiates combat. Use 'look' first to see enemies.",
        "loot": "Tip: 'loot' picks up items from the room floor into your backpack.",
        "equip": "Tip: 'equip <id>' moves an item from backpack to your gear grid.",
        "map": "Tip: 'map' shows the full dungeon layout with your current position.",
        "inventory": "Tip: 'inventory' shows your backpack and equipped gear.",
        "save": "Tip: 'save' writes your current run to disk.",
        "help": "Tip: 'help' lists all available commands.",
        "move": "Tip: Use compass directions (n/s/e/w) or 'move <room_id>' to navigate.",
        "bind": "Tip: 'bind' heals ~50% max HP but advances the Doom Clock.",
    }

    # Hints show until manually disabled (0 = always show)
    HINT_THRESHOLD = 0

    def __init__(self, stats_path: Optional[Path] = None):
        from codex.paths import STATE_DIR
        self._stats_path = stats_path or (STATE_DIR / "session_stats.json")
        self._usage: Dict[str, Dict[str, int]] = {}   # command -> {interface -> count}
        self._completion: Dict[str, dict] = {}          # module_id -> completion record
        self._load_stats()

    # ------------------------------------------------------------------
    # Original hint API (unchanged)
    # ------------------------------------------------------------------

    def record_command(self, command: str, interface: str = "terminal") -> None:
        """Increment usage counter for a command on a given interface."""
        cmd = command.lower()
        if cmd not in self._usage:
            self._usage[cmd] = {}
        self._usage[cmd][interface] = self._usage[cmd].get(interface, 0) + 1
        self._save_stats()

    def get_hint(self, command: str, interface: str = "terminal") -> Optional[str]:
        """Return a hint for a command.

        When HINT_THRESHOLD is 0 hints always show.  Otherwise they
        stop after HINT_THRESHOLD uses.
        """
        cmd = command.lower()
        if cmd not in self.LESSONS:
            return None
        if self.HINT_THRESHOLD == 0:
            return self.LESSONS[cmd]
        count = self._usage.get(cmd, {}).get(interface, 0)
        if count < self.HINT_THRESHOLD:
            return self.LESSONS[cmd]
        return None

    # ------------------------------------------------------------------
    # Completion tracking API
    # ------------------------------------------------------------------

    def mark_page_viewed(self, module_id: str, page_id: str) -> None:
        """Record that *page_id* within *module_id* has been viewed.

        Automatically marks the module completed when all pages have
        been viewed at least once.

        Args:
            module_id: Registered TutorialModule.module_id.
            page_id: TutorialPage.page_id within that module.
        """
        if module_id not in self._completion:
            self._completion[module_id] = {
                "completed": False,
                "pages_viewed": [],
                "timestamp": "",
            }
        record = self._completion[module_id]
        if page_id not in record["pages_viewed"]:
            record["pages_viewed"].append(page_id)

        # Auto-complete if all pages have been viewed
        module = TutorialRegistry.get_module(module_id)
        if module and not record["completed"]:
            all_ids = {p.page_id for p in module.pages}
            viewed_ids = set(record["pages_viewed"])
            if all_ids and all_ids.issubset(viewed_ids):
                record["completed"] = True
                record["timestamp"] = datetime.now().isoformat(timespec="seconds")

        self._save_stats()

    def is_completed(self, module_id: str) -> bool:
        """Return True if the module has been fully completed.

        Args:
            module_id: TutorialModule.module_id to check.

        Returns:
            True when all pages viewed and completion flag is set.
        """
        return self._completion.get(module_id, {}).get("completed", False)

    def get_progress(self, module_id: str) -> dict:
        """Return completion progress for a module.

        Args:
            module_id: TutorialModule.module_id.

        Returns:
            Dict with keys ``"viewed"`` (int), ``"total"`` (int),
            ``"completed"`` (bool).
        """
        module = TutorialRegistry.get_module(module_id)
        total = len(module.pages) if module else 0
        record = self._completion.get(module_id, {})
        viewed = len(record.get("pages_viewed", []))
        completed = record.get("completed", False)
        return {"viewed": viewed, "total": total, "completed": completed}

    # ------------------------------------------------------------------
    # Persistence (backward-compatible)
    # ------------------------------------------------------------------

    def _load_stats(self) -> None:
        """Load usage and completion data from JSON, handling old flat format."""
        if not self._stats_path.exists():
            self._usage = {}
            self._completion = {}
            return
        try:
            with open(self._stats_path) as f:
                raw = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._usage = {}
            self._completion = {}
            return

        if isinstance(raw, dict) and "command_usage" in raw:
            # New format
            self._usage = raw.get("command_usage", {})
            self._completion = raw.get("tutorial_completion", {})
        else:
            # Old flat format — entire dict is _usage
            self._usage = raw if isinstance(raw, dict) else {}
            self._completion = {}

    def _save_stats(self) -> None:
        """Write usage and completion data to JSON in new format."""
        self._stats_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "command_usage": self._usage,
            "tutorial_completion": self._completion,
        }
        try:
            with open(self._stats_path, "w") as f:
                json.dump(payload, f, indent=2)
        except IOError:
            pass


# ---------------------------------------------------------------------------
# TutorialBrowser  (Rich three-panel TUI)
# ---------------------------------------------------------------------------

class TutorialBrowser:
    """Three-panel Rich TUI for browsing TutorialRegistry content.

    Panel layout (follows LibrarianTUI conventions):
      - Left  (ratio=2): Category tree with module list and completion checkmarks.
      - Center (ratio=5): Current page content or selection prompt.
      - Right  (ratio=3): Progress bars per category.

    Navigation:
      - ``<number>``  Select category, module, or page at the current drill level.
      - ``n`` / ``p`` Advance or retreat one page within the current module.
      - ``b``         Back up one drill level.
      - ``q``         Quit the browser.

    Interactive pages:
      - Displays the page prompt and waits for typed input.
      - Validates against page.valid_inputs (case-insensitive).
      - Shows success_message on match and auto-advances; shows "Try again." on mismatch.

    Args:
        tutorial: Optional PlatformTutorial for completion tracking.
                  If None, a fresh (non-persistent) instance is created.
        system_filter: When set (e.g. ``"burnwillow"``), only the
                       ``"platform"`` and *system_filter* categories are shown.
    """

    def __init__(
        self,
        tutorial: Optional[PlatformTutorial] = None,
        system_filter: Optional[str] = None,
    ):
        self._tutorial = tutorial or PlatformTutorial()
        self._system_filter = system_filter

        # Navigation state
        self._categories: Dict[int, str] = {}            # num -> category name
        self._modules: Dict[int, TutorialModule] = {}    # num -> module (within cat)
        self._current_category: Optional[str] = None
        self._current_module: Optional[TutorialModule] = None
        self._current_page_idx: int = 0

        # Drill level: "category" | "module" | "page"
        self._level: str = "category"

        # Status message displayed beneath the content panel
        self._status: str = ""

        self._build_category_map()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _visible_categories(self) -> List[str]:
        """Return category names to display, respecting system_filter."""
        all_cats = TutorialRegistry.get_all_categories()
        if self._system_filter is None:
            return all_cats
        allowed = {"platform", self._system_filter.lower()}
        return [c for c in all_cats if c.lower() in allowed]

    def _build_category_map(self) -> None:
        """Rebuild numbered category map from visible categories."""
        self._categories = {}
        for i, cat in enumerate(self._visible_categories(), 1):
            self._categories[i] = cat

    def _build_module_map(self, category: str) -> None:
        """Rebuild numbered module map for a given category."""
        self._modules = {}
        mods = TutorialRegistry.get_modules_for_category(category)
        for i, mod in enumerate(mods, 1):
            self._modules[i] = mod

    def _current_page(self) -> Optional[TutorialPage]:
        """Return the TutorialPage at the current index, or None."""
        if self._current_module and self._current_module.pages:
            idx = self._current_page_idx
            if 0 <= idx < len(self._current_module.pages):
                return self._current_module.pages[idx]
        return None

    def _category_progress(self, category: str) -> dict:
        """Return aggregate viewed/total/completed for a category.

        Returns:
            Dict with ``"modules"`` (int total), ``"completed"`` (int),
            ``"pages_viewed"`` (int), ``"pages_total"`` (int).
        """
        mods = TutorialRegistry.get_modules_for_category(category)
        total_mods = len(mods)
        completed_mods = 0
        pages_viewed = 0
        pages_total = 0
        for mod in mods:
            prog = self._tutorial.get_progress(mod.module_id)
            pages_viewed += prog["viewed"]
            pages_total += prog["total"]
            if prog["completed"]:
                completed_mods += 1
        return {
            "modules": total_mods,
            "completed": completed_mods,
            "pages_viewed": pages_viewed,
            "pages_total": pages_total,
        }

    @staticmethod
    def _generate_command_reference(
        system_id: str,
        categories_dict: Dict[str, List[str]],
    ) -> TutorialPage:
        """Auto-generate a command-reference TutorialPage from a COMMAND_CATEGORIES dict.

        The *categories_dict* should map category names to lists of command
        strings, e.g. ``{"Movement": ["n", "s", "e", "w"], "Combat": ["attack"]}``.

        Args:
            system_id: Used to label the page title.
            categories_dict: Category -> command list mapping.

        Returns:
            A reference-type TutorialPage with Rich markup content.
        """
        lines = [f"[bold cyan]Command Reference: {system_id.title()}[/bold cyan]", ""]
        for cat_name, commands in categories_dict.items():
            lines.append(f"[bold]{cat_name}[/bold]")
            for cmd in commands:
                lines.append(f"  [dim white]{cmd}[/dim white]")
            lines.append("")
        return TutorialPage(
            page_id=f"{system_id}_cmd_reference",
            title=f"{system_id.title()} Command Reference",
            content="\n".join(lines),
            page_type="reference",
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_index(self) -> "Panel":
        """Left panel: category tree with module list and completion checkmarks."""
        from rich.tree import Tree
        from rich.panel import Panel

        tree = Tree("", guide_style="dim cyan")
        for num, cat in self._categories.items():
            prog = self._category_progress(cat)
            cat_label = cat.replace("_", " ").title()
            completed_str = f"[dim]{prog['completed']}/{prog['modules']}[/dim]"
            if cat == self._current_category:
                branch_label = (
                    f"[bold green]>[/bold green] "
                    f"[bold white]\\[{num}][/bold white] "
                    f"[bold cyan]{cat_label}[/bold cyan] {completed_str}"
                )
            else:
                branch_label = (
                    f"  [bold white]\\[{num}][/bold white] "
                    f"{cat_label} {completed_str}"
                )
            branch = tree.add(branch_label)

            # Show modules under the selected category
            if cat == self._current_category and self._modules:
                for mod_num, mod in self._modules.items():
                    is_done = self._tutorial.is_completed(mod.module_id)
                    check = "[bold green]✓[/bold green]" if is_done else "[dim]-[/dim]"
                    is_active = (
                        self._current_module is not None
                        and self._current_module.module_id == mod.module_id
                    )
                    marker = "[bold green]>[/bold green]" if is_active else " "
                    branch.add(
                        f"{marker} [bold white]\\[{mod_num}][/bold white] "
                        f"{check} {mod.title}"
                    )

        return Panel(
            tree,
            title="[bold]Tutorial Index[/bold]",
            border_style="bright_cyan",
        )

    def _render_content(self) -> "Panel":
        """Center panel: current page or selection prompt."""
        from rich.panel import Panel

        if self._current_module is None:
            # Category or module selection level
            if self._current_category is None:
                content = "[dim]Select a category from the index...[/dim]"
                title = "[bold]Tutorial Browser[/bold]"
                subtitle = "[dim]Type a number to select | q to quit[/dim]"
            else:
                # Module selection
                lines = [
                    f"[bold cyan]{self._current_category.replace('_', ' ').title()}[/bold cyan]",
                    "",
                ]
                for num, mod in self._modules.items():
                    prog = self._tutorial.get_progress(mod.module_id)
                    done = prog["completed"]
                    check = "[bold green](complete)[/bold green]" if done else f"[dim]{prog['viewed']}/{prog['total']} pages[/dim]"
                    # Check prerequisite
                    prereq_met = True
                    if mod.prerequisite:
                        prereq_met = self._tutorial.is_completed(mod.prerequisite)
                    lock = "" if prereq_met else " [red][locked][/red]"
                    lines.append(
                        f"  [bold white]\\[{num}][/bold white] "
                        f"[bold]{mod.title}[/bold]{lock} {check}"
                    )
                    lines.append(f"    [dim]{mod.description}[/dim]")
                    lines.append("")
                content = "\n".join(lines)
                title = f"[bold]{self._current_category.replace('_', ' ').title()}[/bold]"
                subtitle = "[dim]Select a module | b back | q quit[/dim]"
            return Panel(content, title=title, subtitle=subtitle, border_style="white")

        # Page view
        page = self._current_page()
        if page is None:
            return Panel(
                "[dim]No pages in this module.[/dim]",
                title="[bold]Empty Module[/bold]",
                border_style="white",
            )

        mod = self._current_module
        total_pages = len(mod.pages)
        page_indicator = f"[dim]Page {self._current_page_idx + 1} of {total_pages}[/dim]"

        lines = [
            f"[bold cyan]{page.title}[/bold cyan]",
            "",
            page.content,
        ]

        if page.page_type == "interactive" and page.prompt:
            lines += ["", f"[bold yellow]{page.prompt}[/bold yellow]"]

        if self._status:
            lines += ["", self._status]

        content = "\n".join(lines)
        title = f"[bold]{mod.title}[/bold]"
        nav_hint = "n next | p prev | b back | q quit"
        if page.page_type == "interactive":
            nav_hint = "Type your answer | b back | q quit"
        subtitle = f"{page_indicator}  [dim]{nav_hint}[/dim]"

        return Panel(content, title=title, subtitle=subtitle, border_style="white")

    def _render_progress(self) -> "Panel":
        """Right panel: completion stats per category with simple ASCII bars."""
        from rich.panel import Panel

        lines = ["[bold]Progress[/bold]", ""]
        for cat in self._visible_categories():
            prog = self._category_progress(cat)
            cat_label = cat.replace("_", " ").title()
            total_mods = prog["modules"]
            done_mods = prog["completed"]
            total_pages = prog["pages_total"]
            viewed_pages = prog["pages_viewed"]

            # Module completion bar (10 chars wide)
            if total_mods > 0:
                filled = round((done_mods / total_mods) * 10)
                bar = "[green]" + "█" * filled + "[/green]" + "[dim]" + "░" * (10 - filled) + "[/dim]"
            else:
                bar = "[dim]" + "░" * 10 + "[/dim]"

            lines.append(f"[bold]{cat_label}[/bold]")
            lines.append(f"  Modules: {done_mods}/{total_mods}")
            lines.append(f"  {bar}")
            if total_pages > 0:
                lines.append(f"  Pages: {viewed_pages}/{total_pages}")
            lines.append("")

        if not self._visible_categories():
            lines.append("[dim]No modules registered.[/dim]")

        return Panel("\n".join(lines), title="[bold]Completion[/bold]", border_style="green")

    def render(self) -> "Layout":
        """Build and return the three-panel Layout."""
        from rich.layout import Layout

        layout = Layout()
        layout.split_row(
            Layout(self._render_index(), name="index", ratio=2),
            Layout(self._render_content(), name="content", ratio=5),
            Layout(self._render_progress(), name="progress", ratio=3),
        )
        return layout

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _handle_category_level(self, raw: str) -> bool:
        """Handle input at the category selection level.

        Returns:
            False if the caller should quit.
        """
        token = raw.strip().lower()
        if token == "q":
            return False
        if token.isdigit():
            num = int(token)
            cat = self._categories.get(num)
            if cat:
                self._current_category = cat
                self._build_module_map(cat)
                self._level = "module"
                self._status = ""
            else:
                self._status = f"[red]No category {num}.[/red]"
        else:
            self._status = "[dim]Type a number to select a category, or q to quit.[/dim]"
        return True

    def _handle_module_level(self, raw: str) -> bool:
        """Handle input at the module selection level.

        Returns:
            False if the caller should quit.
        """
        token = raw.strip().lower()
        if token == "q":
            return False
        if token == "b":
            self._current_category = None
            self._modules = {}
            self._level = "category"
            self._status = ""
            return True
        if token.isdigit():
            num = int(token)
            mod = self._modules.get(num)
            if mod is None:
                self._status = f"[red]No module {num}.[/red]"
                return True
            # Check prerequisite
            if mod.prerequisite and not self._tutorial.is_completed(mod.prerequisite):
                self._status = (
                    f"[red]Locked.[/red] Complete "
                    f"[bold]{mod.prerequisite}[/bold] first."
                )
                return True
            self._current_module = mod
            self._current_page_idx = 0
            self._level = "page"
            self._status = ""
            # Mark first page viewed immediately (for reference pages)
            page = self._current_page()
            if page and page.page_type == "reference":
                self._tutorial.mark_page_viewed(mod.module_id, page.page_id)
        else:
            self._status = "[dim]Type a number to select a module, b to go back, or q to quit.[/dim]"
        return True

    def _handle_page_level(self, console: "Console", raw: str) -> bool:
        """Handle input at the page reading level.

        Interactive pages consume input for validation before accepting
        navigation commands.

        Returns:
            False if the caller should quit.
        """
        token = raw.strip().lower()
        if token == "q":
            return False
        if token == "b":
            self._current_module = None
            self._current_page_idx = 0
            self._level = "module"
            self._status = ""
            return True

        page = self._current_page()
        mod = self._current_module
        if mod is None:
            return True

        # Interactive page: validate input first
        if page and page.page_type == "interactive" and page.valid_inputs:
            valid = [v.lower() for v in page.valid_inputs]
            if token in valid:
                self._tutorial.mark_page_viewed(mod.module_id, page.page_id)
                self._status = (
                    f"[bold green]{page.success_message or 'Correct!'}[/bold green]"
                )
                # Auto-advance after a beat
                import time
                console.print(self.render())
                time.sleep(1.2)
                self._status = ""
                self._advance_page(mod)
                return True
            else:
                self._status = "[yellow]Try again.[/yellow]"
                return True

        # Navigation on reference pages
        if token == "n":
            if page:
                self._tutorial.mark_page_viewed(mod.module_id, page.page_id)
            self._advance_page(mod)
        elif token == "p":
            self._current_page_idx = max(0, self._current_page_idx - 1)
            page = self._current_page()
            if page and page.page_type == "reference":
                self._tutorial.mark_page_viewed(mod.module_id, page.page_id)
            self._status = ""
        else:
            self._status = "[dim]n=next  p=prev  b=back  q=quit[/dim]"

        return True

    def _advance_page(self, mod: TutorialModule) -> None:
        """Move forward one page, returning to module list if exhausted."""
        total = len(mod.pages)
        if self._current_page_idx < total - 1:
            self._current_page_idx += 1
            # Auto-mark reference pages on entry
            page = self._current_page()
            if page and page.page_type == "reference":
                self._tutorial.mark_page_viewed(mod.module_id, page.page_id)
            self._status = ""
        else:
            # Module finished
            self._status = "[bold green]Module complete![/bold green]"
            self._current_module = None
            self._current_page_idx = 0
            self._level = "module"

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run_loop(self, console: Optional["Console"] = None) -> None:
        """Run the interactive TUI loop.

        Args:
            console: Rich Console to use for rendering and input.
                     If None, a new Console is created.
        """
        from rich.console import Console as RichConsole

        con = console or RichConsole()
        running = True

        while running:
            try:
                con.clear()
                con.print(self.render())

                prompt_text = "> "
                raw = con.input(prompt_text)
            except (KeyboardInterrupt, EOFError):
                break

            if self._level == "category":
                running = self._handle_category_level(raw)
            elif self._level == "module":
                running = self._handle_module_level(raw)
            elif self._level == "page":
                running = self._handle_page_level(con, raw)

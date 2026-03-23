#!/usr/bin/env python3
"""
play_universal.py - Universal Engine Terminal Game Loop
========================================================

A lightweight Rich terminal game loop that plays any registered engine
from the ENGINE_REGISTRY. Supports two gameplay modes:

A. FITD Mode (bitd, sav, bob, cbrpnk, candela)
   Score/mission-based play with handle_command() dispatch.

B. Dungeon Mode (dnd5e, stc)
   Map-based crawl using engine's navigation API + spatial renderer.

Entry point: main(system_id, manifest=None, butler=None)

Version: 1.0 (WO-V40.0 — Universal Engine Routing Fix)
"""

import json
import os
import random
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from codex.core.engine_protocol import ENGINE_REGISTRY
from codex.core.engine_stack import (
    StackedCharacter, StackedCommandDispatcher, MechanicLayer,
    snapshot_engine, seed_actions, extract_action_map, _SYSTEM_ACTIONS,
)

try:
    from codex.forge.source_scanner import scan_system_content
    from codex.forge.char_wizard import render_system_content_table
    _VAULT_BROWSER_AVAILABLE = True
except ImportError:
    _VAULT_BROWSER_AVAILABLE = False

# Phase 3/6: Spatial module system — optional import so the universal loop
# works even if the spatial package is not yet fully installed.
try:
    from codex.spatial.zone_loader import ZoneLoader
    from codex.spatial.module_manifest import ModuleManifest
    from codex.spatial.zone_manager import ZoneManager, EVENT_ZONE_COMPLETE
except ImportError:
    ZoneLoader = None  # type: ignore[assignment,misc]
    ModuleManifest = None  # type: ignore[assignment,misc]
    ZoneManager = None  # type: ignore[assignment,misc]
    EVENT_ZONE_COMPLETE = "ZONE_COMPLETE"  # type: ignore[assignment]

try:
    from codex.spatial.scene_data import SceneData
except ImportError:
    SceneData = None  # type: ignore[assignment,misc]

# WO-V54.0: Spatial map rendering for dungeon loop
try:
    from codex.spatial.map_renderer import (
        SpatialRoom, RoomVisibility, MapTheme,
        render_spatial_map, render_mini_map, rooms_to_minimap_dict,
    )
    _SPATIAL_RENDERER_AVAILABLE = True
except ImportError:
    _SPATIAL_RENDERER_AVAILABLE = False

# WO-V61.0: Companion system
try:
    from codex.core.companion_maps import (
        COMPANION_CLASS_MAP, narrate_decision, get_companion_class,
        pick_weighted_class, create_companion_character,
    )
    from codex.core.trait_evolution import TraitEvolution
    _COMPANION_AVAILABLE = True
except ImportError:
    _COMPANION_AVAILABLE = False

_SAVES_DIR = Path(__file__).resolve().parent / "saves"
_VAULT_ROOT = Path(__file__).resolve().parent / "vault"
_MODULES_DIR = Path(__file__).resolve().parent / "vault_maps" / "modules"


def _resolve_vault_path(system_id: str) -> Optional[str]:
    """Find the vault directory for a given system_id by scanning creation_rules.json files."""
    import json as _json
    if not _VAULT_ROOT.is_dir():
        return None
    for entry in _VAULT_ROOT.iterdir():
        if not entry.is_dir():
            continue
        # Check top-level vault dirs
        rules = entry / "creation_rules.json"
        if rules.is_file():
            try:
                data = _json.loads(rules.read_text())
                if data.get("system_id") == system_id:
                    return str(entry)
            except (ValueError, KeyError):
                pass
        # Check subdirs (FITD/bitd/, ILLUMINATED_WORLDS/Candela_Obscura/, etc.)
        for sub in entry.iterdir():
            if not sub.is_dir():
                continue
            sub_rules = sub / "creation_rules.json"
            if sub_rules.is_file():
                try:
                    data = _json.loads(sub_rules.read_text())
                    if data.get("system_id") == system_id:
                        return str(sub)
                except (ValueError, KeyError):
                    pass
    return None


def _ensure_engines_registered():
    """Import all game modules to trigger ENGINE_REGISTRY population.

    Uses system_discovery to find manifest-declared systems, then
    falls back to hardcoded list for backward compatibility.
    """
    import importlib
    _core_modules = [
        "codex.games.bitd", "codex.games.sav", "codex.games.bob",
        "codex.games.cbrpnk", "codex.games.candela",
        "codex.games.dnd5e", "codex.games.stc",
    ]
    # Import core engines first
    for mod in _core_modules:
        try:
            importlib.import_module(mod)
        except ImportError:
            pass

    # Import any manifest-discovered engines not in core list
    try:
        from codex.core.system_discovery import get_all_manifests, get_engine_module
        for system_id in get_all_manifests():
            mod_path = get_engine_module(system_id)
            if mod_path and mod_path not in _core_modules:
                try:
                    importlib.import_module(mod_path)
                except ImportError:
                    pass
    except ImportError:
        pass


# Systems that use the dungeon crawl loop (map + navigation)
# Populated dynamically from manifests + hardcoded fallback
try:
    from codex.core.system_discovery import discover_system_types as _discover
    DUNGEON_SYSTEMS, FITD_SYSTEMS = _discover()
except ImportError:
    DUNGEON_SYSTEMS = {"dnd5e", "stc"}
    FITD_SYSTEMS = {"bitd", "sav", "bob", "cbrpnk", "candela"}

# Per-system command definition dicts (lazy-loaded)
_SYSTEM_COMMANDS: Dict[str, Dict[str, str]] = {}
_SYSTEM_CATEGORIES: Dict[str, Dict[str, List[str]]] = {}


def _load_system_commands(system_id: str):
    """Lazy-load command dicts from game modules."""
    if system_id in _SYSTEM_COMMANDS:
        return
    try:
        if system_id == "bitd":
            from codex.games.bitd import BITD_COMMANDS, BITD_CATEGORIES
            _SYSTEM_COMMANDS["bitd"] = BITD_COMMANDS
            _SYSTEM_CATEGORIES["bitd"] = BITD_CATEGORIES
        elif system_id == "sav":
            from codex.games.sav import SAV_COMMANDS, SAV_CATEGORIES
            _SYSTEM_COMMANDS["sav"] = SAV_COMMANDS
            _SYSTEM_CATEGORIES["sav"] = SAV_CATEGORIES
        elif system_id == "bob":
            from codex.games.bob import BOB_COMMANDS, BOB_CATEGORIES
            _SYSTEM_COMMANDS["bob"] = BOB_COMMANDS
            _SYSTEM_CATEGORIES["bob"] = BOB_CATEGORIES
        elif system_id == "cbrpnk":
            from codex.games.cbrpnk import CBRPNK_COMMANDS, CBRPNK_CATEGORIES
            _SYSTEM_COMMANDS["cbrpnk"] = CBRPNK_COMMANDS
            _SYSTEM_CATEGORIES["cbrpnk"] = CBRPNK_CATEGORIES
        elif system_id == "candela":
            from codex.games.candela import CANDELA_COMMANDS, CANDELA_CATEGORIES
            _SYSTEM_COMMANDS["candela"] = CANDELA_COMMANDS
            _SYSTEM_CATEGORIES["candela"] = CANDELA_CATEGORIES
    except ImportError:
        _SYSTEM_COMMANDS.setdefault(system_id, {})
        _SYSTEM_CATEGORIES.setdefault(system_id, {})


# =========================================================================
# CHARACTER CONVERSION — Wizard manifest -> engine-native kwargs
# =========================================================================

def _extract_choice(choices: dict, key: str, default: str = "") -> str:
    """Extract a choice value that may be a string or {'id': '...'} dict."""
    val = choices.get(key, default)
    if isinstance(val, dict):
        return val.get("id", val.get("name", default))
    return str(val) if val else default


def convert_wizard_character(system_id: str, name: str,
                             choices: dict, stats: dict) -> dict:
    """Convert wizard manifest data into engine-native create_character kwargs.

    Args:
        system_id: Engine system ID (bitd, sav, bob, cbrpnk, candela, dnd5e, stc).
        name: Character name from the wizard.
        choices: Dict of wizard choices (playbook, heritage, race, etc.).
        stats: Dict of stat allocations from the wizard.

    Returns:
        Dict of kwargs suitable for engine.create_character(name, **kwargs).
    """
    kwargs: Dict[str, Any] = {}

    if system_id == "bitd":
        kwargs["playbook"] = _extract_choice(choices, "playbook")
        kwargs["heritage"] = _extract_choice(choices, "heritage")
        # 12 action dots
        for action in ("hunt", "study", "survey", "tinker",
                        "finesse", "prowl", "skirmish", "wreck",
                        "attune", "command", "consort", "sway"):
            kwargs[action] = int(stats.get(action, 0))

    elif system_id == "sav":
        kwargs["playbook"] = _extract_choice(choices, "playbook")
        kwargs["heritage"] = _extract_choice(choices, "heritage")
        for action in ("doctor", "hack", "rig", "study",
                        "helm", "scramble", "scrap", "skulk",
                        "attune", "command", "consort", "sway"):
            kwargs[action] = int(stats.get(action, 0))

    elif system_id == "bob":
        kwargs["playbook"] = _extract_choice(choices, "playbook")
        kwargs["heritage"] = _extract_choice(choices, "heritage")
        for action in ("doctor", "marshal", "research", "scout_action",
                        "maneuver", "skirmish", "wreck",
                        "consort", "discipline", "sway"):
            kwargs[action] = int(stats.get(action, 0))

    elif system_id == "cbrpnk":
        kwargs["archetype"] = _extract_choice(choices, "archetype")
        kwargs["background"] = _extract_choice(choices, "background")
        for action in ("hack", "override", "scan", "study",
                        "scramble", "scrap", "skulk", "shoot",
                        "attune", "command", "consort", "sway"):
            kwargs[action] = int(stats.get(action, 0))
        chrome = choices.get("chrome", [])
        if isinstance(chrome, list):
            kwargs["chrome"] = chrome

    elif system_id == "candela":
        kwargs["role"] = _extract_choice(choices, "role")
        kwargs["specialization"] = _extract_choice(choices, "specialization")
        for action in ("move", "strike", "control",
                        "sway", "read", "hide",
                        "survey", "focus", "sense"):
            kwargs[action] = int(stats.get(action, 0))

    elif system_id == "dnd5e":
        kwargs["character_class"] = _extract_choice(choices, "character_class",
                                                     _extract_choice(choices, "class"))
        kwargs["race"] = _extract_choice(choices, "race")
        kwargs["strength"] = int(stats.get("strength", 10))
        kwargs["dexterity"] = int(stats.get("dexterity", 10))
        kwargs["constitution"] = int(stats.get("constitution", 10))
        kwargs["intelligence"] = int(stats.get("intelligence", 10))
        kwargs["wisdom"] = int(stats.get("wisdom", 10))
        kwargs["charisma"] = int(stats.get("charisma", 10))

    elif system_id == "stc":
        kwargs["order"] = _extract_choice(choices, "order")
        kwargs["heritage"] = _extract_choice(choices, "heritage")
        kwargs["strength"] = int(stats.get("strength", 10))
        kwargs["speed"] = int(stats.get("speed", 10))
        kwargs["intellect"] = int(stats.get("intellect", 10))

    return kwargs


# =========================================================================
# FITD SCENE STATE (WO-V52.0)
# =========================================================================

class _FITDSceneState:
    """Tracks narrative scene progression for FITD modules.

    Scenes are rooms from the module blueprint, traversed linearly.
    Each scene's content_hints are parsed into SceneData for display.
    """

    def __init__(self, zone_manager, base_path: str):
        self.zm = zone_manager
        self.base_path = base_path
        self.current_graph = None  # DungeonGraph from blueprint
        self.scene_list: list = []  # List of (room_id, RoomNode) tuples
        self.scene_idx: int = 0
        self.visited: set = set()
        # WO-V54.0: Audio trigger support
        self.audio_dir = self._find_audio_dir(base_path)
        self.audio_map: Dict[int, str] = self._build_audio_map()
        # FITD roleplay: conversation mode
        self.talking_to: Optional[str] = None
        self._talking_to_npc: Optional[dict] = None
        # FITD roleplay: quest/job tracking
        self.accepted_jobs: List[dict] = []
        self.pending_offer: Optional[dict] = None
        self._load_current_zone()

    def _find_audio_dir(self, base_path: str) -> Optional[str]:
        """Find AUDIO/ sibling directory for module audio files."""
        # Walk up from module base_path to find AUDIO/
        audio_path = os.path.join(os.path.dirname(base_path), "AUDIO")
        if os.path.isdir(audio_path):
            return audio_path
        # Try one more level up
        audio_path = os.path.join(os.path.dirname(os.path.dirname(base_path)), "AUDIO")
        if os.path.isdir(audio_path):
            return audio_path
        return None

    def _build_audio_map(self) -> Dict[int, str]:
        """Map scene index -> WAV file by filename number prefix."""
        if not self.audio_dir:
            return {}
        audio_map: Dict[int, str] = {}
        try:
            for f in sorted(os.listdir(self.audio_dir)):
                if not f.lower().endswith(".wav"):
                    continue
                # Extract number from filename: "CBR PNK_01_dearpass_.wav" -> 01 -> scene 0
                import re
                match = re.search(r'_(\d+)_', f)
                if match:
                    num = int(match.group(1))
                    # File numbering starts at 01, scene index starts at 0
                    audio_map[num - 1] = os.path.join(self.audio_dir, f)
        except OSError:
            pass
        return audio_map

    def play_scene_audio(self):
        """Play audio file for current scene if available."""
        if self.audio_dir and self.scene_idx in self.audio_map:
            path = self.audio_map[self.scene_idx]
            try:
                subprocess.Popen(["aplay", "-q", path],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            except (FileNotFoundError, OSError):
                pass

    def _load_current_zone(self):
        """Load scenes from the current zone's blueprint."""
        graph = self.zm.load_current_zone()
        if graph:
            self.current_graph = graph
            self.scene_list = sorted(graph.rooms.items())
            self.scene_idx = 0
            self.visited = set()

    def current_scene(self) -> Optional[Any]:
        """Return SceneData for the current scene, or None."""
        if not self.scene_list or self.scene_idx >= len(self.scene_list):
            return None
        room_id, room_node = self.scene_list[self.scene_idx]
        self.visited.add(room_id)
        hints = getattr(room_node, 'content_hints', None) or {}
        if SceneData is not None:
            return SceneData.from_content_hints(hints)
        return hints

    def current_room_node(self):
        """Return the current (room_id, RoomNode) tuple."""
        if not self.scene_list or self.scene_idx >= len(self.scene_list):
            return None, None
        return self.scene_list[self.scene_idx]

    def enter_conversation(self, name: str, npc_data: dict):
        """Enter free-form conversation with an NPC."""
        self.talking_to = name
        self._talking_to_npc = npc_data

    def exit_conversation(self):
        """Exit conversation mode."""
        name = self.talking_to
        self.talking_to = None
        self._talking_to_npc = None
        return name

    def advance_scene(self) -> Optional[Any]:
        """Advance to the next scene. Returns SceneData or None if zone end."""
        self.scene_idx += 1
        if self.scene_idx >= len(self.scene_list):
            return None
        return self.current_scene()

    def advance_zone(self) -> bool:
        """Advance to the next zone. Returns True if successful."""
        entry = self.zm.advance()
        if entry is None:
            return False
        self._load_current_zone()
        return True

    def scene_count(self) -> int:
        return len(self.scene_list)

    def visited_count(self) -> int:
        return len(self.visited)

    def to_dict(self) -> dict:
        """Serialize scene state for save persistence."""
        return {
            "scene_idx": self.scene_idx,
            "visited": sorted(self.visited),
            "accepted_jobs": list(self.accepted_jobs),
            "pending_offer": self.pending_offer,
        }

    def restore_from_dict(self, data: dict) -> None:
        """Restore scene state from saved data."""
        self.scene_idx = data.get("scene_idx", 0)
        self.visited = set(data.get("visited", []))
        self.accepted_jobs = data.get("accepted_jobs", [])
        self.pending_offer = data.get("pending_offer")

    def format_scene(self, scene_data) -> str:
        """Format a SceneData (or dict) into a display string."""
        if scene_data is None:
            return "No scene data available."

        # Handle both SceneData objects and raw dicts
        if isinstance(scene_data, dict):
            desc = scene_data.get("description", "An empty scene.")
            npcs = scene_data.get("npcs", [])
            services = scene_data.get("services", [])
            events = scene_data.get("event_triggers", [])
        else:
            desc = scene_data.description or "An empty scene."
            npcs = scene_data.npcs or []
            services = scene_data.services or []
            events = scene_data.event_triggers or []

        lines = [desc]

        if npcs:
            lines.append("")
            lines.append("NPCs:")
            for npc in npcs:
                if isinstance(npc, dict):
                    name = npc.get("name", "Unknown")
                    role = npc.get("role", "")
                else:
                    name = npc.name
                    role = npc.role
                role_str = f" ({role})" if role else ""
                lines.append(f"  {name}{role_str}")

        if services:
            lines.append("")
            svc_strs = [str(s) for s in services]
            lines.append(f"Services: {', '.join(svc_strs)}")

        if events:
            lines.append("")
            lines.append("Events:")
            for ev in events:
                lines.append(f"  {ev}")

        return "\n".join(lines)


# =========================================================================
# ENGINE STACKING (WO-V60.0)
# =========================================================================

def _show_layers(con: Console, stacked_char: StackedCharacter):
    """Display all mechanic layers and merged action sheet."""
    lines = ["[bold]=== Mechanic Layers ===[/bold]"]
    for i, layer in enumerate(stacked_char.layers):
        status = "active" if not layer.dormant else "dormant"
        style = "bold green" if not layer.dormant else "dim"
        summary_parts = [f"[{style}][{i + 1}] {layer.system_id.upper()} ({status})[/{style}]"]
        # Show a few key action dots
        top_actions = sorted(
            ((k, v) for k, v in layer.action_snapshot.items() if v > 0),
            key=lambda x: -x[1],
        )[:5]
        if top_actions:
            summary_parts.append(
                "  " + ", ".join(f"{k}:{v}" for k, v in top_actions))
        lines.append("\n".join(summary_parts))

    merged = stacked_char.merged_actions()
    if merged:
        lines.append("")
        lines.append("[bold]=== Merged Actions ===[/bold]")
        nonzero = {k: v for k, v in sorted(merged.items()) if v > 0}
        zero = sorted(k for k, v in merged.items() if v == 0)
        if nonzero:
            lines.append("  ".join(f"{k}:{v}" for k, v in nonzero.items()))
        if zero:
            lines.append(f"[dim]{', '.join(zero)}: 0[/dim]")

    con.print(Panel("\n".join(lines), title="Engine Stack",
                    border_style="magenta", box=box.ROUNDED))


def _transition_system(
    con: Console,
    current_engine,
    stacked_char: Optional[StackedCharacter],
    current_system_id: str,
) -> Optional[dict]:
    """Run the system transition flow. Returns transition info dict or None.

    The returned dict contains:
        engine: new engine instance
        system_id: new system id
        stacked_char: updated StackedCharacter
        dispatcher: new StackedCommandDispatcher
    """
    # Show available target systems
    all_systems = DUNGEON_SYSTEMS | FITD_SYSTEMS
    available = sorted(s for s in all_systems if s != current_system_id)

    if not available:
        con.print("[red]No other systems available for transition.[/red]")
        return None

    con.print()
    table = Table(title="Available Systems", box=box.ROUNDED,
                  show_header=True, header_style="bold cyan")
    table.add_column("#", width=3)
    table.add_column("System")
    table.add_column("Type")

    for i, sid in enumerate(available):
        stype = "Dungeon" if sid in DUNGEON_SYSTEMS else "FITD"
        table.add_row(str(i + 1), sid.upper(), stype)

    con.print(table)

    # Player picks target
    choice = con.input("[bold cyan]Select target system (number, or 'cancel'): [/bold cyan]").strip()
    if choice.lower() in ("cancel", "c", ""):
        return None
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(available):
            con.print("[red]Invalid selection.[/red]")
            return None
    except ValueError:
        con.print("[red]Invalid selection.[/red]")
        return None

    target_system_id = available[idx]

    # Ensure engine class exists
    _ensure_engines_registered()
    target_class = ENGINE_REGISTRY.get(target_system_id)
    if not target_class:
        con.print(f"[red]Engine not found for {target_system_id}.[/red]")
        return None

    # Snapshot current engine
    current_snapshot = snapshot_engine(current_engine)
    current_snapshot.dormant = True

    # Build or update stacked character
    char_name = ""
    lead = getattr(current_engine, 'character', None)
    if not lead:
        party = getattr(current_engine, 'party', [])
        lead = party[0] if party else None
    if lead:
        char_name = getattr(lead, 'name', 'Adventurer')

    if stacked_char is None:
        stacked_char = StackedCharacter(name=char_name)
        # Add current system as first (dormant) layer
        stacked_char.layers.append(current_snapshot)

    else:
        # Update current active layer with latest state
        active = stacked_char.get_active_layer()
        if active:
            active.engine_state = current_snapshot.engine_state
            active.action_snapshot = current_snapshot.action_snapshot
            active.dormant = True

    # Compute seed actions
    seeds = seed_actions(stacked_char.layers, target_system_id)

    # Show seed info
    nonzero_seeds = {k: v for k, v in seeds.items() if v > 0}
    if nonzero_seeds:
        con.print()
        con.print("[bold yellow]Action Seeds from Prior Systems:[/bold yellow]")
        for action, val in sorted(nonzero_seeds.items()):
            con.print(f"  {action}: {val}")
        con.print()

    # Instantiate new engine and create character with seeded actions
    new_engine = target_class()
    con.print(f"[bold green]Transitioning to {new_engine.display_name}...[/bold green]")

    # Create character — name pre-filled, prompt for system-specific choices
    new_engine.create_character(char_name)

    # Apply seed actions to the new character
    new_char = getattr(new_engine, 'character', None)
    if not new_char:
        party = getattr(new_engine, 'party', [])
        new_char = party[0] if party else None

    if new_char and nonzero_seeds:
        for action, val in nonzero_seeds.items():
            current_val = getattr(new_char, action, None)
            if current_val is not None and isinstance(current_val, int):
                setattr(new_char, action, max(current_val, val))

    # Snapshot new engine and add as active layer
    new_snapshot = snapshot_engine(new_engine)
    stacked_char.add_layer(
        target_system_id,
        new_snapshot.engine_state,
        new_snapshot.action_snapshot,
    )

    # Build dormant engine instances for command dispatch
    dormant_engines = []
    for layer in stacked_char.layers:
        if layer.dormant and layer.system_id in ENGINE_REGISTRY:
            try:
                dormant_eng = ENGINE_REGISTRY[layer.system_id]()
                dormant_eng.load_state(layer.engine_state)
                dormant_engines.append(dormant_eng)
            except Exception:
                pass

    dispatcher = StackedCommandDispatcher(new_engine, dormant_engines)

    con.print(Panel(
        f"[bold green]Now playing: {new_engine.display_name}[/bold green]\n"
        f"[dim]Dormant systems: {', '.join(l.system_id for l in stacked_char.layers if l.dormant)}[/dim]\n"
        f"[dim]Type 'layers' to see your full stack.[/dim]",
        border_style="green", box=box.DOUBLE,
    ))

    return {
        "engine": new_engine,
        "system_id": target_system_id,
        "stacked_char": stacked_char,
        "dispatcher": dispatcher,
    }


def _save_stacked(
    con: Console,
    engine,
    system_id: str,
    stacked_char: StackedCharacter,
):
    """Save a stacked (multi-system) game state."""
    # Update active layer with current engine state
    active = stacked_char.get_active_layer()
    if active:
        if hasattr(engine, 'save_state'):
            active.engine_state = engine.save_state()
        active.action_snapshot = extract_action_map(engine)

    data = {
        "format_version": 2,
        "stacked": True,
        "active_system_id": stacked_char.active_system_id,
        "character_name": stacked_char.name,
        "layers": [l.to_dict() for l in stacked_char.layers],
    }
    if stacked_char.shared_clocks:
        data["shared_clocks"] = {
            name: clock.to_dict()
            for name, clock in stacked_char.shared_clocks.items()
        }

    _SAVES_DIR.mkdir(parents=True, exist_ok=True)
    save_path = _SAVES_DIR / f"stacked_{stacked_char.name.lower().replace(' ', '_')}_save.json"
    save_path.write_text(json.dumps(data, indent=2, default=str))
    con.print(f"[green]Stacked save written to {save_path.name}.[/green]")


def _load_stacked_save(save_data: dict) -> Optional[dict]:
    """Load a stacked save file. Returns dict with engine, dispatcher, stacked_char, system_id.

    Returns None if loading fails.
    """
    if not save_data.get("stacked"):
        return None

    stacked_char = StackedCharacter.from_dict({
        "name": save_data.get("character_name", "Unknown"),
        "active_system_id": save_data.get("active_system_id", ""),
        "layers": save_data.get("layers", []),
        "shared_clocks": save_data.get("shared_clocks", {}),
    })

    active_layer = stacked_char.get_active_layer()
    if not active_layer:
        return None

    # Instantiate active engine
    active_class = ENGINE_REGISTRY.get(active_layer.system_id)
    if not active_class:
        return None

    active_engine = active_class()
    active_engine.load_state(active_layer.engine_state)

    # Instantiate dormant engines
    dormant_engines = []
    for layer in stacked_char.layers:
        if layer.dormant and layer.system_id in ENGINE_REGISTRY:
            try:
                eng = ENGINE_REGISTRY[layer.system_id]()
                eng.load_state(layer.engine_state)
                dormant_engines.append(eng)
            except Exception:
                pass

    dispatcher = StackedCommandDispatcher(active_engine, dormant_engines)

    return {
        "engine": active_engine,
        "system_id": active_layer.system_id,
        "stacked_char": stacked_char,
        "dispatcher": dispatcher,
    }


# =========================================================================
# FITD GAME LOOP
# =========================================================================

def _render_status_panel(con: Console, engine, system_id: str,
                        companion_agent=None):
    """Render a Rich Panel showing engine status."""
    status = engine.get_status()
    lines = [f"[bold]{engine.display_name}[/bold]"]
    for k, v in status.items():
        if k == "system":
            continue
        label = k.replace("_", " ").title()
        lines.append(f"  {label}: {v}")

    # Show companion info if present
    if companion_agent and companion_agent.enabled:
        comp_name = companion_agent.personality.name or "Companion"
        arch = companion_agent.personality.archetype
        sys_class = getattr(companion_agent, '_system_class', arch)
        lines.append(f"  [cyan]Companion: {comp_name} ({arch.title()} {sys_class})[/cyan]")

    con.print(Panel("\n".join(lines), title="Status", border_style="cyan",
                    box=box.ROUNDED))


def _render_command_table(con: Console, system_id: str):
    """Render a Rich Table of available commands for the system."""
    _load_system_commands(system_id)
    categories = _SYSTEM_CATEGORIES.get(system_id, {})
    commands = _SYSTEM_COMMANDS.get(system_id, {})

    table = Table(title="Commands", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan")
    table.add_column("Command", style="green")
    table.add_column("Description")

    if categories:
        for cat_name, cmd_list in categories.items():
            table.add_row(f"[bold yellow]{cat_name}[/bold yellow]", "")
            for cmd in cmd_list:
                desc = commands.get(cmd, "")
                table.add_row(f"  {cmd}", desc)
    else:
        for cmd, desc in commands.items():
            table.add_row(cmd, desc)

    # Built-in commands
    table.add_row("[bold yellow]System[/bold yellow]", "")
    table.add_row("  roll <action>", "Shorthand for roll_action")
    table.add_row("  dice <expr>", "Free-form dice roll (e.g. dice 2d20+5)")
    table.add_row("  status", "Show engine status")
    table.add_row("  sheet", "Full character sheet")
    table.add_row("  save", "Save current game")
    table.add_row("  transition", "Cross-system transition (engine stacking)")
    table.add_row("  layers", "Show stacked mechanic layers")
    table.add_row("  companion", "Recruit/view AI companion")
    table.add_row("  help", "Show this command list")
    table.add_row("  quit", "Exit to main menu")

    con.print(table)


def _handle_companion_command(con: Console, engine, bridge_or_state, args: str = "") -> None:
    """WO-V61.0/V66.0: Handle companion recruitment and status display.

    Creates a full PC companion via create_companion_character() factory,
    picking from the full range of system classes weighted by archetype.
    """
    if not _COMPANION_AVAILABLE:
        con.print("[dim]Companion system not available.[/dim]")
        return

    companion = getattr(bridge_or_state, '_companion_agent', None)

    if companion:
        # Show companion status
        p = companion.get_effective_personality()
        comp_name = companion.personality.name or "Companion"
        con.print(f"\n[bold cyan]Companion: {comp_name}[/]")
        con.print(f"  Archetype: {companion.personality.archetype}")
        # Show system class if available
        if hasattr(companion, '_system_class'):
            con.print(f"  Class: {companion._system_class}")
        con.print(f"  Aggression: {p.aggression:.2f}  Curiosity: {p.curiosity:.2f}  Caution: {p.caution:.2f}")
        if companion.evolution and companion.evolution.deltas:
            con.print(f"  Evolution: {companion.evolution.get_evolution_summary()}")
        return

    # Recruitment flow
    archetypes = ["vanguard", "scholar", "scavenger", "healer"]
    con.print("\n[bold]Recruit a Companion[/]")
    for i, arch in enumerate(archetypes, 1):
        con.print(f"  {i}. {arch.title()}")
    con.print("  5. Random")

    from rich.prompt import Prompt
    choice = Prompt.ask("Choose", console=con, default="5")
    try:
        idx = int(choice) - 1
        if idx == 4:
            import random as _random
            archetype = _random.choice(archetypes)
        elif 0 <= idx < 4:
            archetype = archetypes[idx]
        else:
            con.print("[dim]Invalid choice.[/dim]")
            return
    except ValueError:
        archetype = choice.lower().strip()
        if archetype not in archetypes:
            con.print("[dim]Invalid choice.[/dim]")
            return

    system_id = getattr(engine, 'system_id', 'unknown')

    try:
        from codex.core.autopilot import GenericAutopilotAgent
        from codex.games.burnwillow.autopilot import (
            CompanionPersonality, PERSONALITY_POOL, COMPANION_NAME_POOL,
            _roll_biography,
        )
    except ImportError:
        con.print("[dim]Companion system not available.[/dim]")
        return

    # Pick name
    rng = random.Random()
    existing_names = set()
    if hasattr(engine, 'party'):
        existing_names = {getattr(c, 'name', '') for c in engine.party}
    available_names = [n for n in COMPANION_NAME_POOL if n not in existing_names]
    comp_name = rng.choice(available_names) if available_names else rng.choice(COMPANION_NAME_POOL)

    # Find personality matching archetype, set name + biography
    personality = None
    for _p in PERSONALITY_POOL:
        if _p.archetype == archetype:
            personality = _p
            break
    if not personality:
        personality = CompanionPersonality(archetype=archetype)

    personality.name = comp_name
    personality.biography = _roll_biography(rng)

    # Pick weighted class from full system list
    chosen_class = pick_weighted_class(system_id, archetype, rng)

    # Create actual PC in engine party
    char = create_companion_character(engine, system_id, archetype, comp_name, rng)

    # Build agent
    agent = GenericAutopilotAgent(personality, system_id)
    agent._system_class = chosen_class
    agent.init_evolution()
    agent.enabled = True
    bridge_or_state._companion_agent = agent

    con.print(f"\n[green]{comp_name} ({archetype.title()} {chosen_class}) joins as companion![/]")
    if personality.biography:
        con.print(f"  [dim]{personality.biography}[/dim]")


# ─── WO-V66.0: Companion Turn Helper ──────────────────────────────────────


def _run_companion_turn(ctx) -> None:
    """Execute a companion turn after the player's command resolves.

    Runs the companion's decide → execute → narrate pipeline and
    displays the result via Rich formatting.
    """
    agent = ctx.companion_agent
    if not agent or not agent.enabled:
        return

    try:
        # Determine phase from context
        phase = "exploration"
        if ctx.scene_state:
            phase = "exploration"  # FITD scenes are narrative
        elif ctx.bridge:
            phase = "exploration"

        action = agent.decide(ctx.engine, phase)
        if not action or action == "end":
            return

        result = agent.execute(action, ctx.engine)
        narration = agent.narrate_action(action, ctx.engine)

        comp_name = agent.personality.name or "Companion"
        if narration:
            ctx.con.print(f"  [cyan]{narration}[/cyan]")
        elif result:
            ctx.con.print(f"  [dim]{comp_name}: {result}[/dim]")
    except Exception:
        pass


# ─── WO-V64.0: Far Travel Loop ────────────────────────────────────────────


def _run_far_travel(
    con: Console,
    journey_engine,
    engine=None,
    party_names: Optional[List[str]] = None,
    butler=None,
) -> dict:
    """Interactive far-travel loop. Returns a result dict with journey outcome.

    Args:
        journey_engine: A JourneyEngine instance with segments configured.
        engine: The game engine (for stat lookups and combat).
        party_names: List of character names for role assignment.
        butler: Optional CodexButler for narration.

    Returns:
        {"arrived": bool, "days_elapsed": int, "supplies": int,
         "combats": [...], "journey": journey_engine}
    """
    from codex.core.mechanics.journey import (
        JourneyEngine, JourneyState, TravelRole, ROLE_STAT_KEYS,
    )
    from codex.core.mechanics.journey_renderer import (
        render_journey_announcement, render_role_assignment,
        render_segment_header, render_event, render_camp, render_arrival,
    )

    je = journey_engine
    combats_triggered = []
    rng = random.Random()

    # ── Phase 1: Show journey overview ────────────────────────────────
    con.print(render_journey_announcement(je))

    # ── Phase 2: Role assignment ──────────────────────────────────────
    if party_names and engine:
        je.state = JourneyState.ASSIGNING_ROLES

        for role in TravelRole:
            stat_keys = ROLE_STAT_KEYS.get(role, [])
            con.print(f"\n[bold]{role.value.title()}[/bold] — checks: {', '.join(stat_keys)}")

            # Auto-assign: pick best character for this role
            best_name = None
            best_val = -1
            for pname in party_names:
                char = None
                if hasattr(engine, 'party'):
                    for c in engine.party:
                        if getattr(c, 'name', '') == pname:
                            char = c
                            break
                if not char and hasattr(engine, 'character'):
                    char = engine.character

                if char:
                    for sk in stat_keys:
                        val = getattr(char, sk, None)
                        if val is not None:
                            if val > best_val:
                                best_val = val
                                best_name = pname
                            break

            if best_name is None:
                best_name = party_names[0] if party_names else "Adventurer"
                best_val = 0

            je.assign_role(role, best_name, max(0, best_val))
            con.print(f"  -> [cyan]{best_name}[/cyan] (stat: {best_val})")

        con.print(render_role_assignment(je))

    # ── Phase 3: Travel segments ──────────────────────────────────────
    while not je.is_complete:
        # Show segment header
        con.print(render_segment_header(je))

        # Resolve events
        outcomes = je.resolve_segment(rng)
        for outcome in outcomes:
            con.print(render_event(outcome))

            # Combat triggered — collect for caller to handle
            if outcome.combat_triggered:
                combats_triggered.append({
                    "event": outcome.event.title,
                    "enemies_tier": outcome.event.enemies_tier,
                    "segment": je.current_segment_idx,
                })
                con.print(Panel(
                    "[bold red]AMBUSH![/bold red] Combat breaks out on the road!",
                    border_style="red",
                ))
                # In a full integration, we'd run combat here
                # For now, note it and continue

            # Narrate
            if butler and hasattr(butler, 'narrate'):
                try:
                    butler.narrate(outcome.text)
                except Exception:
                    pass

        # Camp phase
        camp = je.camp_phase(rng)
        con.print(render_camp(camp, je.supplies))

        if camp.night_raid:
            combats_triggered.append({
                "event": "Night Raid",
                "enemies_tier": je.tier,
                "segment": je.current_segment_idx,
            })

        # Advance to next segment
        je.advance()

        # Pause between segments (unless arrived)
        if not je.is_complete:
            try:
                con.input("\n[dim]Press Enter to continue the journey...[/dim]")
            except (EOFError, KeyboardInterrupt):
                je.state = JourneyState.FAILED
                break

    # ── Phase 4: Arrival ──────────────────────────────────────────────
    if je.state == JourneyState.ARRIVED:
        con.print(render_arrival(je))

    return {
        "arrived": je.state == JourneyState.ARRIVED,
        "days_elapsed": je.days_elapsed,
        "supplies": je.supplies,
        "combats": combats_triggered,
        "journey": je,
    }


def _run_fitd_loop(con: Console, engine, system_id: str, butler=None,
                   scene_state: Optional[_FITDSceneState] = None,
                   stacked_char: Optional[StackedCharacter] = None,
                   dispatcher: Optional[StackedCommandDispatcher] = None,
                   companion_agent=None):
    """FITD game loop — command dispatch via engine.handle_command().

    Args:
        scene_state: Optional scene state for narrative module progression.
        stacked_char: Optional StackedCharacter for cross-system stacking.
        dispatcher: Optional StackedCommandDispatcher for multi-engine dispatch.
    """
    # WO-V65+: Wire butler for audio narration in FITD loop
    _fitd_butler = butler

    def _fitd_narrate(text: str) -> None:
        """Narrate text via butler if available."""
        if _fitd_butler and getattr(_fitd_butler, '_voice_enabled', False):
            try:
                _fitd_butler.narrate(text)
            except Exception:
                pass

    con.print(Panel(
        f"[bold green]Welcome to {engine.display_name}[/bold green]\n"
        f"[dim]Type 'help' for commands, 'quit' to exit.[/dim]",
        border_style="green", box=box.DOUBLE,
    ))

    _render_status_panel(con, engine, system_id)

    # WO-V52.0: Show opening narration — first session gets cold open, resume gets recap
    if scene_state:
        scene = scene_state.current_scene()
        if scene:
            try:
                from codex.core.services.opening_narration import (
                    generate_opening_narration, generate_resume_narration,
                    format_read_aloud_panel, is_first_session,
                )
                _thermal_ok = True
                _gm_profile = ""
                _dm_inf = None
                try:
                    from codex.core.cortex import get_cortex
                    _c = get_cortex()
                    _thermal_ok = _c.get_thermal_state().status != "RED"
                    _gm_profile = _c.get_gm_profile_prompt(system_id)
                    _dm_inf = _c.active_dm_influence
                except Exception:
                    pass

                def _mimir_opening(prompt, **kw):
                    from codex.integrations.mimir import query_mimir
                    return query_mimir(prompt)

                _mimir_fn = _mimir_opening if _thermal_ok else None

                if is_first_session(engine):
                    # First session — module cold open
                    _narration = generate_opening_narration(
                        system_id=system_id,
                        scene_data=scene,
                        gm_profile=_gm_profile,
                        dm_influence=_dm_inf,
                        mimir_fn=_mimir_fn,
                        thermal_ok=_thermal_ok,
                    )
                else:
                    # Resume — contextual recap
                    _narration = generate_resume_narration(
                        system_id=system_id,
                        engine=engine,
                        scene_data=scene,
                        mimir_fn=_mimir_fn,
                        thermal_ok=_thermal_ok,
                    )

                _panel_text = format_read_aloud_panel(_narration)
                if _panel_text:
                    con.print(Panel(
                        _panel_text,
                        title=f"[bold]{_narration.gm_title}[/bold]",
                        border_style="yellow", box=box.HEAVY,
                    ))
                    _ra = getattr(scene, 'read_aloud', '') or ''
                    if _ra:
                        _fitd_narrate(_ra[:300])
            except Exception:
                # Fallback: display raw read_aloud if available
                _ra = getattr(scene, 'read_aloud', '') or ''
                if _ra:
                    con.print(Panel(_ra, title="Read Aloud",
                                    border_style="yellow", box=box.HEAVY))

            # Scene details — description, NPCs, services
            room_id, room_node = scene_state.current_room_node()
            room_name = getattr(room_node, 'room_type', None)
            title_parts = []
            if scene_state.zm.chapter_name:
                title_parts.append(scene_state.zm.chapter_name)
            title_parts.append(f"Scene {scene_state.scene_idx + 1}")
            title = " — ".join(title_parts)
            con.print(Panel(
                scene_state.format_scene(scene),
                title=title, border_style="magenta", box=box.ROUNDED,
            ))
            scene_state.play_scene_audio()  # WO-V54.0: Audio trigger
            # Narrate scene description (if read_aloud wasn't already narrated)
            if not _ra:
                desc = getattr(scene, 'description', None) or (scene.get("description", "") if isinstance(scene, dict) else "")
                if desc:
                    _fitd_narrate(desc[:300])

    # ── Command handlers ──────────────────────────────────────────
    from codex.core.command_handlers import (
        LoopContext, SharedCommandHandler, FITDCommandHandler,
    )
    ctx = LoopContext(
        con=con, engine=engine, system_id=system_id, butler=butler,
        stacked_char=stacked_char, dispatcher=dispatcher,
        scene_state=scene_state, companion_agent=companion_agent,
    )
    _shared = SharedCommandHandler()
    _fitd = FITDCommandHandler()

    while True:
        try:
            user_input = con.input("\n[bold cyan]> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        parts = user_input.split()
        verb = parts[0].lower()

        # Dispatch through handler chain: shared -> FITD -> engine fallback
        action = _shared.dispatch(ctx, verb, parts)
        if action == "break":
            break
        if action == "continue":
            # Sync mutated context back to local vars (transition may change these)
            engine = ctx.engine
            system_id = ctx.system_id
            stacked_char = ctx.stacked_char
            dispatcher = ctx.dispatcher
            # Companion turn after player command
            _run_companion_turn(ctx)
            continue

        action = _fitd.dispatch(ctx, verb, parts)
        if action == "break":
            break
        if action == "continue":
            engine = ctx.engine
            _run_companion_turn(ctx)
            continue

        # Dispatch to engine.handle_command()
        # Parse: "crew_status" or "take_mark track=body"
        cmd = verb
        kwargs: Dict[str, Any] = {}
        for part in parts[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                kwargs[k] = v
            else:
                # Positional args vary by command — pass as generic 'arg'
                kwargs.setdefault("arg", part)

        try:
            # WO-V60.0: Use dispatcher if stacked, else direct engine dispatch
            if dispatcher:
                result = dispatcher.dispatch(cmd, **kwargs)
            else:
                result = engine.handle_command(cmd, **kwargs)
            # Contextual error hints instead of bare "Unknown command"
            if isinstance(result, str) and "unknown command" in result.lower():
                # Check if input matches an NPC name in current scene
                if scene_state:
                    _hint_scene = scene_state.current_scene()
                    if _hint_scene:
                        _hint_npcs = _hint_scene.npcs if hasattr(_hint_scene, 'npcs') else _hint_scene.get("npcs", [])
                        for _hn in _hint_npcs:
                            _hn_name = _hn.name if hasattr(_hn, 'name') else _hn.get("name", "")
                            if verb in _hn_name.lower():
                                con.print(f"[dim]Try: talk {_hn_name.lower().split()[0]}[/dim]")
                                break
                        else:
                            con.print(f"[dim]Unknown command. Try 'help' for options.[/dim]")
                    else:
                        con.print(f"[dim]Unknown command. Try 'help' for options.[/dim]")
                else:
                    con.print(f"[dim]Unknown command. Try 'help' for options.[/dim]")
            else:
                # WO-V69.0: Styled dice panel for FITD roll results
                if isinstance(result, str) and result.startswith("Dice: ["):
                    _render_fitd_dice_panel(con, result, cmd)
                else:
                    con.print(Panel(result, title=cmd.replace("_", " ").title(),
                                    border_style="blue"))
                # Narrate significant command outputs (skip short status lines)
                if isinstance(result, str) and len(result) > 40:
                    _fitd_narrate(result[:250])
        except Exception as e:
            con.print(f"[red]Command error: {e}[/red]")

        # Companion turn after engine command
        _run_companion_turn(ctx)


# =========================================================================
# FITD DICE PANEL (WO-V69.0)
# =========================================================================

def _render_fitd_dice_panel(con: Console, result: str, cmd: str):
    """Render a styled Rich panel for FITD dice roll results.

    Parses the engine's ``Dice: [4, 6] -> SUCCESS`` format and renders
    a color-coded panel: green for crit, red for fail, gold for normal.
    """
    import re as _re

    # Extract dice values from "Dice: [4, 6]" prefix
    dice_match = _re.search(r"Dice:\s*\[([^\]]+)\]", result)
    dice_vals: List[int] = []
    if dice_match:
        try:
            dice_vals = [int(x.strip()) for x in dice_match.group(1).split(",")]
        except ValueError:
            pass

    # Determine outcome from result text
    upper = result.upper()
    if "CRITICAL" in upper and "SUCCESS" in upper:
        border = "bold green"
        title = "CRITICAL SUCCESS!"
        dice_style = "bold green"
    elif "CRITICAL" in upper and "FAIL" in upper:
        border = "bold red"
        title = "CRITICAL FAIL!"
        dice_style = "bold red"
    elif "FAIL" in upper:
        border = "red"
        title = cmd.replace("_", " ").title()
        dice_style = "red"
    else:
        border = "gold1"
        title = cmd.replace("_", " ").title()
        dice_style = "bold yellow"

    # Build dice face line
    if dice_vals:
        faces = "  ".join(f"[{dice_style}][{d}][/{dice_style}]" for d in dice_vals)
        # Show the full result below the dice
        con.print(Panel(
            f"{faces}\n\n{result}",
            title=f"[bold]{title}[/bold]",
            border_style=border,
            box=box.DOUBLE,
        ))
    else:
        # Fallback if parsing fails
        con.print(Panel(result, title=cmd.replace("_", " ").title(),
                        border_style="blue"))


# =========================================================================
# SPATIAL MAP HELPERS (WO-V54.0)
# =========================================================================

def _rebuild_spatial_rooms(engine) -> Dict[int, Any]:
    """Rebuild spatial room cache from engine state. Simplified from play_burnwillow.py."""
    if not _SPATIAL_RENDERER_AVAILABLE:
        return {}
    if not engine or not getattr(engine, 'dungeon_graph', None):
        return {}

    spatial_rooms: Dict[int, Any] = {}
    graph = engine.dungeon_graph

    for room_id, room_node in graph.rooms.items():
        if room_id == engine.current_room_id:
            vis = RoomVisibility.CURRENT
        elif room_id in engine.visited_rooms:
            vis = RoomVisibility.VISITED
        else:
            vis = RoomVisibility.UNEXPLORED

        sr = SpatialRoom.from_map_engine_room(room_node, visibility=vis)

        # Inject live enemies/loot/furniture for current room
        if room_id == engine.current_room_id:
            pop = engine.populated_rooms.get(room_id)
            if pop:
                sr.enemies = list(pop.content.get("enemies", []))
                sr.loot = list(pop.content.get("loot", []))
                sr.furniture = list(pop.content.get("furniture", []))

        spatial_rooms[room_id] = sr

    return spatial_rooms


def _get_lead_hp(engine, which: str = "current") -> int:
    """Return lead character's HP value."""
    party = getattr(engine, 'party', [])
    char = party[0] if party else getattr(engine, 'character', None)
    if not char:
        return 0
    if which == "max":
        return getattr(char, 'max_hp', 0)
    return getattr(char, 'current_hp', 0)


def _render_full_map(con: Console, engine, bridge) -> Optional[Any]:
    """Render the full spatial map with sidebar stats. Returns Rich Layout or None."""
    if not _SPATIAL_RENDERER_AVAILABLE:
        return None
    if not getattr(engine, 'dungeon_graph', None):
        return None

    spatial_rooms = _rebuild_spatial_rooms(engine)
    if not spatial_rooms:
        return None

    # Determine theme
    theme_name = engine.dungeon_graph.metadata.get("theme", "STONE") if engine.dungeon_graph.metadata else "STONE"
    try:
        theme = MapTheme[theme_name.upper()]
    except (KeyError, AttributeError):
        theme = MapTheme.STONE

    # Build room info
    room_node = engine.get_current_room()
    pop = engine.populated_rooms.get(engine.current_room_id)
    content = pop.content if pop else {}
    room_type = room_node.room_type.name if room_node and hasattr(room_node, 'room_type') else "ROOM"

    # Format exits (strip DM notes from NPC data)
    exits = engine.get_cardinal_exits()
    exit_strs = []
    for ex in exits:
        visited = " [VISITED]" if ex["id"] in engine.visited_rooms else ""
        exit_strs.append(f"{ex['direction'].upper()} -> Room {ex['id']}{visited}")

    # NPCs without notes
    npcs = content.get("npcs", [])
    npc_strs = []
    for npc in npcs:
        if isinstance(npc, dict):
            name = npc.get("name", "Unknown")
            role = npc.get("role", "")
            role_str = f" ({role})" if role else ""
            npc_strs.append(f"{name}{role_str}")

    stats = {
        "room_name": f"Room {engine.current_room_id} ({room_type})",
        "room_description": content.get("description", "An unremarkable chamber."),
        "hp_current": _get_lead_hp(engine, "current"),
        "hp_max": _get_lead_hp(engine, "max"),
        "depth": getattr(room_node, 'tier', 1) if room_node else 1,
        "enemies": content.get("enemies", []),
        "loot": content.get("loot", []),
        "furniture": content.get("furniture", []),
        "exits": exit_strs,
    }

    if npc_strs:
        stats["detail"] = "NPCs:\n" + "\n".join(f"  @ {n}" for n in npc_strs)

    # Mini-map for sidebar
    mm_rooms = rooms_to_minimap_dict(engine.dungeon_graph)
    stats["mini_map"] = render_mini_map(
        mm_rooms, engine.current_room_id, engine.visited_rooms,
        rich_mode=True, theme=theme,
    )

    layout = render_spatial_map(
        rooms=spatial_rooms,
        player_room_id=engine.current_room_id,
        theme=theme,
        stats=stats,
        viewport_width=50,
        viewport_height=20,
        console=con,
        player_pos=getattr(engine, 'player_pos', None),
    )
    return layout


# =========================================================================
# DUNGEON GAME LOOP
# =========================================================================

def _run_dungeon_loop(con: Console, engine, system_id: str, butler=None,
                      zone_manager=None,
                      stacked_char: Optional[StackedCharacter] = None,
                      dispatcher: Optional[StackedCommandDispatcher] = None,
                      companion_agent=None):
    """Dungeon crawl loop for map-based engines (dnd5e, stc).

    Args:
        zone_manager: Optional ZoneManager for module-based multi-zone play.
        stacked_char: Optional StackedCharacter for cross-system stacking.
        dispatcher: Optional StackedCommandDispatcher for multi-engine dispatch.
    """
    from codex.games.bridge import UniversalGameBridge
    from codex.core.services.momentum import MomentumLedger

    # Wrap engine in bridge for command dispatch
    bridge = _EngineWrappedBridge(engine)

    # WO-V61.0: Attach momentum ledger for trend tracking
    _momentum = MomentumLedger(universe_id=getattr(engine, 'system_id', 'universal'))
    bridge._bridge._momentum_ledger = _momentum

    # WO-V62.0: Wire momentum threshold handler
    from codex.core.services.momentum_handler import MomentumThresholdHandler
    bridge._bridge._momentum_handler = MomentumThresholdHandler(
        broadcast_manager=getattr(butler, 'broadcast_manager', None) if butler else None,
        engine=engine,
    )

    # WO-V50.0: Wire butler for audio narration
    if butler and hasattr(bridge._bridge, 'set_butler'):
        bridge._bridge.set_butler(butler)

    # WO-V56.0: Subscribe to zone broadcast events for UI feedback
    if zone_manager and hasattr(zone_manager, '_broadcast') and zone_manager._broadcast:
        try:
            zone_manager._broadcast.subscribe(EVENT_ZONE_COMPLETE,
                lambda payload: con.print(
                    f"[bold green]Zone complete: {payload.get('zone', '')}[/bold green]"))
        except Exception:
            pass

    zone_label = ""
    if zone_manager and not zone_manager.module_complete:
        zone_label = f"\n[dim]{zone_manager.zone_progress}[/dim]"

    con.print(Panel(
        f"[bold green]Welcome to {engine.display_name}[/bold green]{zone_label}\n"
        f"[dim]Type 'help' for commands, 'quit' to exit.[/dim]",
        border_style="green", box=box.DOUBLE,
    ))

    # Opening narration for spatial/dungeon systems with module content
    if zone_manager and zone_manager.current_graph:
        try:
            _graph = zone_manager.current_graph
            _room_0 = _graph.rooms.get(0)
            if _room_0:
                _hints = getattr(_room_0, 'content_hints', {}) or {}
                _ra_text = _hints.get('read_aloud', '')
                if _ra_text:
                    from codex.core.services.opening_narration import (
                        generate_opening_narration, format_read_aloud_panel,
                    )
                    from codex.spatial.scene_data import SceneData
                    _sd = SceneData.from_content_hints(_hints)
                    _narration = generate_opening_narration(
                        system_id=system_id, scene_data=_sd,
                    )
                    _panel_text = format_read_aloud_panel(_narration)
                    if _panel_text:
                        con.print(Panel(
                            _panel_text,
                            title=f"[bold]{_narration.gm_title}[/bold]",
                            border_style="yellow", box=box.HEAVY,
                        ))
        except Exception:
            pass

    # WO-V54.0: Spatial rendering commands
    _SPATIAL_VERBS = {
        "look", "l", "n", "s", "e", "w", "north", "south", "east", "west",
        "ne", "nw", "se", "sw", "northeast", "northwest", "southeast", "southwest",
        "map",
    }

    # Initial look — try spatial render first
    result = bridge.step("look")
    layout = _render_full_map(con, engine, bridge)
    if layout:
        con.print(layout)
    else:
        con.print(Panel(result, title="Current Room", border_style="blue"))

    # ── Command handlers ──────────────────────────────────────────
    from codex.core.command_handlers import (
        LoopContext, SharedCommandHandler, DungeonCommandHandler,
    )
    ctx = LoopContext(
        con=con, engine=engine, system_id=system_id, butler=butler,
        stacked_char=stacked_char, dispatcher=dispatcher,
        zone_manager=zone_manager, bridge=bridge,
        companion_agent=companion_agent,
    )
    _shared = SharedCommandHandler()
    _dungeon = DungeonCommandHandler()

    while True:
        try:
            user_input = con.input("\n[bold cyan]> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        verb = user_input.split()[0].lower()
        parts = user_input.split()

        # Dispatch through handler chain: shared -> dungeon -> bridge
        action = _shared.dispatch(ctx, verb, parts)
        if action == "break":
            break
        if action == "continue":
            engine = ctx.engine
            system_id = ctx.system_id
            stacked_char = ctx.stacked_char
            dispatcher = ctx.dispatcher
            bridge = ctx.bridge
            _run_companion_turn(ctx)
            continue

        action = _dungeon.dispatch(ctx, verb, parts)
        if action == "break":
            break
        if action == "continue":
            _run_companion_turn(ctx)
            continue

        result = bridge.step(user_input)

        # WO-V62.0: Display momentum threshold messages
        for msg in bridge._bridge.pop_momentum_messages():
            con.print(msg)

        if bridge.dead:
            con.print(Panel(result, title="DEFEAT", border_style="red"))
            break

        # WO-V54.0: Spatial rendering for look/movement/map commands
        if verb in _SPATIAL_VERBS:
            layout = _render_full_map(con, engine, bridge)
            if layout:
                con.print(layout)
            else:
                # Fallback to text panel
                title = "Current Room" if verb in _SPATIAL_VERBS else verb.title()
                con.print(Panel(result, title=title, border_style="blue"))
        elif verb in ("attack", "fight", "a"):
            con.print(Panel(result, title="Combat", border_style="red"))
        else:
            con.print(Panel(result, title=verb.title(), border_style="cyan"))

        # Companion turn after player action
        _run_companion_turn(ctx)

        # Zone exit check: after each action, see if engine reports zone complete
        if zone_manager and not zone_manager.module_complete:
            game_state = {}
            if hasattr(engine, 'check_zone_exit'):
                game_state = getattr(engine, '_zone_game_state', lambda: {})()
            if zone_manager.check_exit_condition(game_state):
                zone_manager.fire_zone_complete()
                con.print(Panel(
                    f"[bold green]Zone Complete![/bold green]\n"
                    f"[dim]{zone_manager.zone_name} cleared.[/dim]",
                    border_style="green",
                ))
                next_entry = zone_manager.advance()
                if next_entry is None:
                    con.print(Panel(
                        f"[bold gold1]MODULE COMPLETE![/bold gold1]\n"
                        f"{zone_manager.module_name} finished!",
                        border_style="gold1", box=box.DOUBLE,
                    ))
                    break
                # WO-V64.0: Check for travel segment between zones
                _travel_data = getattr(next_entry, 'travel', None)
                if _travel_data and isinstance(_travel_data, dict):
                    from codex.core.mechanics.journey import (
                        JourneyEngine, TerrainSegment,
                    )
                    _t_seg = [TerrainSegment(
                        name=_travel_data.get("name", f"Road to {next_entry.zone_id}"),
                        terrain_type=_travel_data.get("terrain", "road"),
                        days=_travel_data.get("days", 2),
                    )]
                    _t_party = [getattr(c, 'name', 'Adventurer')
                                for c in getattr(engine, 'party', [])] or ["Adventurer"]
                    _t_je = JourneyEngine(
                        origin=zone_manager.zone_name or "here",
                        destination=_travel_data.get("destination", next_entry.zone_id),
                        segments=_t_seg,
                        party_size=len(_t_party),
                        supplies=_travel_data.get("supplies", 10),
                        tier=getattr(engine, '_tier', 1),
                    )
                    _run_far_travel(con, _t_je, engine=engine,
                                    party_names=_t_party, butler=butler)

                # Load next zone
                con.print(f"[dim]Loading zone: {next_entry.zone_id}...[/dim]")
                graph = zone_manager.load_current_zone()
                if graph and hasattr(engine, 'load_dungeon_graph'):
                    engine.load_dungeon_graph(graph)
                    result = bridge.step("look")
                    con.print(Panel(result, title="New Zone", border_style="green"))

    # WO-V56.0: Session recap on dungeon loop exit
    loom_shards = getattr(engine, '_memory_shards', [])
    if loom_shards:
        try:
            from codex.core.services.narrative_loom import synthesize_narrative
            summary = synthesize_narrative(
                "Summarize this adventuring session.",
                loom_shards[:20],
            )
            if summary:
                con.print(Panel(summary, title="Session Recap",
                                border_style="yellow"))
        except Exception:
            pass


class _EngineWrappedBridge:
    """Thin wrapper that uses UniversalGameBridge's step() logic
    around an already-initialized engine (no re-instantiation)."""

    def __init__(self, engine):
        from codex.games.bridge import UniversalGameBridge
        # Create a bridge but swap its engine with our pre-initialized one
        # We bypass __init__ to avoid re-creating the engine
        self._bridge = UniversalGameBridge.create_lightweight(engine)

    @property
    def dead(self):
        return self._bridge.dead

    def step(self, command: str) -> str:
        return self._bridge.step(command)

    def load_module_zone(self, zone_entry) -> Optional[Any]:
        """Load a zone from a module manifest ZoneEntry.

        Delegates to ZoneLoader if available.  Returns a DungeonGraph on
        success, or None if the spatial package is not installed or an error
        occurs.

        Args:
            zone_entry: A ``ZoneEntry`` instance from a ``ModuleManifest``.

        Returns:
            DungeonGraph populated with geometry (and metadata), or None.
        """
        if ZoneLoader is None:
            return None
        try:
            loader = ZoneLoader(base_path="")
            return loader.load_zone(zone_entry)
        except Exception:
            return None


def _resolve_module_manifest(manifest: dict) -> Optional[str]:
    """Resolve a module_manifest.json path from a campaign manifest.

    Checks for an explicit ``module_manifest_path`` key first, then
    attempts to derive the path from the ``world_layers`` module entry
    by mapping the module name to ``vault_maps/modules/<slug>/module_manifest.json``.

    Returns:
        Absolute path string, or None if not found.
    """
    # Explicit path takes priority
    explicit = manifest.get("module_manifest_path")
    if explicit and Path(explicit).exists():
        return str(Path(explicit).resolve())

    # Derive from world_layers
    layers = manifest.get("world_layers", [])
    for layer in layers:
        if layer.get("type") == "module" and layer.get("name"):
            slug = layer["name"].lower().replace(" ", "_").replace("'", "")
            candidate = (
                Path(__file__).resolve().parent
                / "vault_maps" / "modules" / slug / "module_manifest.json"
            )
            if candidate.exists():
                return str(candidate)
    return None


# =========================================================================
# MODULE SELECT (WO-V51.0)
# =========================================================================

def _offer_module_select(con: Console, system_id: str) -> Optional[dict]:
    """Scan for adventure modules matching system_id, present menu.

    For spatial engines (engines with ``generate_dungeon``), option 0 is
    'Procedural Dungeon'.  For FITD engines, modules are shown for
    narrative reference only.

    Returns:
        Dict with keys ``manifest_path``, ``base_path``, ``manifest`` if
        a module is selected; None for procedural or no modules found.
    """
    if ModuleManifest is None or not _MODULES_DIR.is_dir():
        return None

    # Scan all module directories for matching system_id
    modules: list = []
    for entry in sorted(_MODULES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        manifest_path = entry / "module_manifest.json"
        if not manifest_path.exists():
            continue
        try:
            data = json.loads(manifest_path.read_text())
            if data.get("system_id") == system_id:
                modules.append({
                    "path": str(manifest_path),
                    "base_path": str(entry),
                    "display_name": data.get("display_name", entry.name),
                    "levels": data.get("recommended_levels", {}),
                })
        except (json.JSONDecodeError, KeyError):
            continue

    if not modules:
        return None

    is_spatial = system_id in DUNGEON_SYSTEMS

    # Build menu
    con.print()
    table = Table(title="Adventure Modules", box=box.ROUNDED,
                  show_header=True, header_style="bold cyan")
    table.add_column("#", style="bold", width=3)
    table.add_column("Module")
    table.add_column("Levels")

    if is_spatial:
        table.add_row("0", "[dim]Procedural Dungeon[/dim]", "-")

    for i, mod in enumerate(modules):
        lvls = mod["levels"]
        lvl_str = f"{lvls.get('min', '?')}-{lvls.get('max', '?')}" if lvls else "-"
        table.add_row(str(i + 1), mod["display_name"], lvl_str)

    con.print(table)

    while True:
        choice = con.input("[bold cyan]Select module (number): [/bold cyan]").strip()
        if not choice:
            return None
        try:
            idx = int(choice)
        except ValueError:
            continue

        if is_spatial and idx == 0:
            return None  # Procedural dungeon

        if 1 <= idx <= len(modules):
            selected = modules[idx - 1]
            mm = ModuleManifest.load(selected["path"])

            if not is_spatial:
                # FITD: scene-based navigation
                con.print(Panel(
                    f"[bold]{mm.display_name}[/bold]\n"
                    f"Chapters: {len(mm.chapters)}\n"
                    f"[dim]Module loaded. Navigate scenes with: scene, next, scenes, talk, services.[/dim]",
                    border_style="yellow", box=box.ROUNDED,
                ))
                return {"manifest": mm, "manifest_path": selected["path"],
                        "base_path": selected["base_path"],
                        "narrative_only": True}

            return {"manifest": mm, "manifest_path": selected["path"],
                    "base_path": selected["base_path"]}

        con.print("[red]Invalid selection.[/red]")


# =========================================================================
# ENTRY POINT
# =========================================================================

def _resolve_subsetting(system_id: str):
    """Resolve sub-setting system_ids to their parent engine.

    E.g. "stc_roshar" -> ("stc", "roshar"), "dnd5e" -> ("dnd5e", "").
    Only splits if the parent is a known dungeon or FITD system.
    """
    if system_id in DUNGEON_SYSTEMS or system_id in FITD_SYSTEMS:
        return system_id, ""
    if "_" in system_id:
        parts = system_id.split("_", 1)
        candidate = parts[0]
        if candidate in DUNGEON_SYSTEMS or candidate in FITD_SYSTEMS:
            return candidate, parts[1]
    return system_id, ""


def main_stacked(save_data: dict, butler=None):
    """Launch a stacked (multi-system) game from a saved state.

    Called when loading a save with ``"stacked": True``.

    Args:
        save_data: Parsed JSON save dict with format_version 2.
        butler: Optional CodexButler for session-aware reflexes.
    """
    con = Console()
    _ensure_engines_registered()

    loaded = _load_stacked_save(save_data)
    if not loaded:
        con.print("[red]Failed to load stacked save.[/red]")
        return

    engine = loaded["engine"]
    system_id = loaded["system_id"]
    stacked_char = loaded["stacked_char"]
    dispatcher = loaded["dispatcher"]

    con.print(Panel(
        f"[bold green]Stacked Campaign Loaded: {stacked_char.name}[/bold green]\n"
        f"Active: {system_id.upper()}\n"
        f"Layers: {', '.join(l.system_id for l in stacked_char.layers)}",
        border_style="green", box=box.DOUBLE,
    ))

    resolved_id, _ = _resolve_subsetting(system_id)

    if resolved_id in DUNGEON_SYSTEMS:
        if hasattr(engine, 'generate_dungeon') and not getattr(engine, 'dungeon_graph', None):
            con.print("[dim]Generating dungeon...[/dim]")
            result = engine.generate_dungeon()
            con.print(f"[green]Dungeon ready: {result['total_rooms']} rooms[/green]")
        _run_dungeon_loop(con, engine, resolved_id, butler=butler,
                          stacked_char=stacked_char, dispatcher=dispatcher)
    elif resolved_id in FITD_SYSTEMS:
        _run_fitd_loop(con, engine, resolved_id, butler=butler,
                       stacked_char=stacked_char, dispatcher=dispatcher)
    elif hasattr(engine, 'handle_command'):
        _run_fitd_loop(con, engine, resolved_id, butler=butler,
                       stacked_char=stacked_char, dispatcher=dispatcher)
    else:
        con.print(f"[yellow]No game loop available for {system_id}.[/yellow]")


def _campaign_loading_sequence(con, engine, resolved_id, manifest, zm):
    """Show a Rich progress loading screen and synthesize memory shards.

    Handles engine-init acknowledgment, MASTER/ANCHOR shard creation,
    dungeon generation for spatial systems, and visual progress feedback.

    Returns:
        Tuple of (CodexMemoryEngine, dungeon_result_or_None).
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from codex.core.memory import CodexMemoryEngine

    mem = CodexMemoryEngine()

    is_spatial = resolved_id in DUNGEON_SYSTEMS
    needs_dungeon = is_spatial and not (zm and zm.current_graph is not None)

    stages = [
        ("Engine Init", f"Initializing {resolved_id} engine..."),
        ("Memory Shards", "Synthesizing world context..."),
        ("Game State", "Anchoring current state..."),
    ]
    if needs_dungeon:
        stages.append(("Dungeon", "Generating environment..."))
    elif is_spatial and zm:
        stages.append(("Module Zone", f"Loading {zm.zone_name}..."))
    stages.append(("Ready", "Adventure awaits..."))

    dungeon_result = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=con,
    ) as progress:
        task = progress.add_task("[cyan]Preparing...", total=len(stages))

        for stage_name, stage_desc in stages:
            progress.update(task, description=f"[cyan]{stage_desc}")

            if stage_name == "Memory Shards":
                # Create MASTER shard with world context
                world_info = []
                if manifest:
                    if manifest.get("campaign_name"):
                        world_info.append(
                            f"Campaign: {manifest['campaign_name']}")
                    if manifest.get("system_theme"):
                        world_info.append(
                            f"Theme: {manifest['system_theme']}")
                world_info.append(f"System: {resolved_id}")
                if zm and hasattr(zm, 'manifest') and zm.manifest:
                    world_info.append(
                        f"Module: {zm.manifest.display_name}")
                mem.create_shard(
                    content="\n".join(world_info),
                    shard_type="MASTER",
                    tags=["world", "init"],
                    source="system",
                    pinned=True,
                )

            elif stage_name == "Game State":
                # Create ANCHOR shard with initial game state
                state_info = ["Day 1 — Session start"]
                party = getattr(engine, 'party', [])
                if party:
                    names = [getattr(c, 'name', str(c)) for c in party[:4]]
                    state_info.append(f"Party: {', '.join(names)}")
                loc = getattr(engine, 'current_location', None)
                if loc:
                    state_info.append(f"Location: {loc}")
                mem.create_shard(
                    content="\n".join(state_info),
                    shard_type="ANCHOR",
                    tags=["session_start", "game_state"],
                    source="system",
                )

            elif stage_name == "Dungeon":
                dungeon_result = engine.generate_dungeon()

            progress.advance(task)

    # Post-progress summary
    if dungeon_result:
        con.print(
            f"[green]Dungeon ready: "
            f"{dungeon_result['total_rooms']} rooms[/green]")
    elif is_spatial and zm and zm.current_graph is not None:
        con.print(
            f"[green]Module zone loaded: {zm.zone_name}[/green]")

    con.print(f"[dim]Memory shards: {len(mem.shards)} synthesized[/dim]")

    return mem, dungeon_result


def main(system_id: str, manifest: Optional[dict] = None, butler=None):
    """Launch the universal game loop for any registered engine.

    Args:
        system_id: Engine system ID (e.g. 'bitd', 'dnd5e', 'stc', 'stc_roshar').
        manifest: Optional wizard manifest with character data.
        butler: Optional CodexButler for session-aware reflexes.
    """
    con = Console()

    # Ensure all game engines are registered
    _ensure_engines_registered()

    # WO-V60.0: Detect stacked saves and route to stacked loader
    if manifest and manifest.get("stacked"):
        return main_stacked(manifest, butler=butler)

    # Resolve sub-setting system_ids to parent engine
    resolved_id, setting_id = _resolve_subsetting(system_id)

    # Look up engine class using resolved parent ID
    engine_class = ENGINE_REGISTRY.get(resolved_id)
    if not engine_class:
        # Redirect standalone systems that have their own game loops
        if resolved_id == "burnwillow":
            import play_burnwillow as _bw
            _bw_manifest_path = manifest.get("module_manifest_path") if manifest else None
            _bw.main(
                butler=butler,
                module_manifest_path=_bw_manifest_path,
                session_type=manifest.get("session_type") if manifest else None,
            )
            return
        con.print(f"[red]Unknown game system: {system_id}[/red]")
        con.print(f"[dim]Available: {', '.join(ENGINE_REGISTRY.keys())}[/dim]")
        return

    # Instantiate engine
    engine = engine_class()

    # Propagate sub-setting to engine if applicable
    if setting_id and hasattr(engine, 'setting_id'):
        engine.setting_id = setting_id

    # Show available vault content before character creation
    if _VAULT_BROWSER_AVAILABLE:
        _vp = _resolve_vault_path(resolved_id) or _resolve_vault_path(system_id)
        if _vp:
            _vc = scan_system_content(_vp)
            render_system_content_table(_vc, system_id.upper(), con)

    # Create character(s) from manifest or defaults
    if manifest and manifest.get("characters"):
        characters = manifest["characters"]
        for i, char_data in enumerate(characters):
            name = char_data.get("name", f"Hero {i + 1}")
            choices = char_data.get("choices", {})
            stats = char_data.get("stats", {})
            kwargs = convert_wizard_character(system_id, name, choices, stats)
            # WO-V54.0: Engine now correctly appends to party
            engine.create_character(name, **kwargs)
    elif manifest and manifest.get("choices"):
        # Single character from wizard
        name = manifest.get("character_name", manifest.get("name", "Adventurer"))
        choices = manifest.get("choices", {})
        stats = manifest.get("stats", {})
        kwargs = convert_wizard_character(system_id, name, choices, stats)
        engine.create_character(name, **kwargs)
    else:
        # Default character — prompt for name
        name = con.input("[bold]Enter character name:[/bold] ").strip() or "Adventurer"
        engine.create_character(name)

    # Apply group data (Circle/Crew/Ship/Legion) from wizard manifest
    if manifest and manifest.get("group_data"):
        gd = manifest["group_data"]
        if hasattr(engine, 'circle_name') and gd.get("circle_name"):
            engine.circle_name = gd["circle_name"]
        if hasattr(engine, 'circle_abilities'):
            engine.circle_abilities = gd.get("circle_abilities", [])

    # Initialize AI companion from manifest
    _companion_agent = None
    if manifest and manifest.get("ai_companion") and manifest["ai_companion"].get("enabled"):
        try:
            from codex.core.autopilot import GenericAutopilotAgent
            from codex.games.burnwillow.autopilot import (
                CompanionPersonality, COMPANION_NAME_POOL, _roll_biography,
            )
            _comp_data = manifest["ai_companion"]
            _comp_archetype = _comp_data.get("personality", "")
            # Reconstruct personality from manifest (preserves system-specific traits)
            _comp_personality = CompanionPersonality(
                archetype=_comp_archetype,
                description=_comp_data.get("description", ""),
                quirk=_comp_data.get("quirk", ""),
                aggression=_comp_data.get("aggression", 0.5),
                curiosity=_comp_data.get("curiosity", 0.5),
                caution=_comp_data.get("caution", 0.5),
            )
            if _comp_personality:
                # Set name + biography if not already present
                if not _comp_personality.name:
                    _comp_rng = random.Random()
                    _comp_personality.name = _comp_rng.choice(COMPANION_NAME_POOL)
                    _comp_personality.biography = _roll_biography(_comp_rng)

                _companion_agent = GenericAutopilotAgent(
                    personality=_comp_personality,
                    system_tag=resolved_id,
                )
                _companion_agent.enabled = True

                # Pick weighted class and create PC in party
                _comp_class = pick_weighted_class(resolved_id, _comp_archetype)
                _companion_agent._system_class = _comp_class
                create_companion_character(
                    engine, resolved_id, _comp_archetype,
                    _comp_personality.name,
                )
                con.print(
                    f"[dim]AI Companion: {_comp_personality.name} "
                    f"({_comp_archetype.title()} {_comp_class}) — "
                    f"{_comp_personality.description}[/dim]"
                )
        except Exception:
            pass

    # Resolve module manifest for zone-based progression
    zm = None

    # WO-V51.0: Module select flow — offer module menu before dungeon gen
    # WO-V63.0: Skip module selection when loading a saved campaign
    _is_loaded_save = manifest and manifest.get("characters") and not manifest.get("continue_campaign")
    if ZoneManager is not None and not _is_loaded_save and not (manifest and _resolve_module_manifest(manifest)):
        module_info = _offer_module_select(con, resolved_id)
        if module_info and not module_info.get("narrative_only"):
            mm = module_info["manifest"]
            base_path = module_info["base_path"]
            # WO-V56.0: Wire broadcast manager for zone events
            _zm_bcast = getattr(butler, 'broadcast_manager', None) if butler else None
            zm = ZoneManager(manifest=mm, base_path=base_path,
                             broadcast_manager=_zm_bcast)
            con.print(f"[dim]Module: {mm.display_name}[/dim]")

            # WO-V51.0: Villain path prompt — check if the current chapter
            # has villain_path_* zones and let the player choose
            villain_paths = zm.get_villain_paths()
            if not villain_paths:
                # Check all chapters for villain paths
                for ch in zm.sorted_chapters:
                    for z in ch.zones:
                        trigger = z.entry_trigger.lower()
                        if trigger.startswith("villain_path_"):
                            tag = trigger[len("villain_path_"):]
                            if tag not in villain_paths:
                                villain_paths.append(tag)
                villain_paths = sorted(set(villain_paths))

            if villain_paths:
                con.print()
                con.print("[bold]Choose your villain path:[/bold]")
                for i, vp in enumerate(villain_paths):
                    con.print(f"  [{i + 1}] {vp.replace('_', ' ').title()}")
                vp_choice = con.input(
                    "[bold cyan]Select path (number): [/bold cyan]").strip()
                try:
                    vp_idx = int(vp_choice) - 1
                    if 0 <= vp_idx < len(villain_paths):
                        zm.set_villain_path(villain_paths[vp_idx])
                        con.print(
                            f"[green]Villain path: "
                            f"{villain_paths[vp_idx].replace('_', ' ').title()}"
                            f"[/green]")
                except (ValueError, IndexError):
                    pass

            # WO-V55.0: Propagate campaign_setting to engine
            if hasattr(engine, 'setting_id') and mm.campaign_setting:
                engine.setting_id = mm.campaign_setting

            # Wire into engine if it supports load_module
            if hasattr(engine, 'load_module'):
                engine.load_module(module_info["manifest_path"])
            # WO-V57.0: Persist module path in campaign manifest for reload
            if manifest and isinstance(manifest, dict):
                manifest["module_manifest_path"] = module_info["manifest_path"]

            # Load first zone
            graph = zm.load_current_zone()
            if graph and hasattr(engine, 'load_dungeon_graph'):
                engine.load_dungeon_graph(graph)

            # WO-V55.0: Seed FR wiki lore context on module load
            try:
                from codex.integrations.fr_wiki import is_fr_context, get_fr_wiki
                _setting = getattr(engine, 'setting_id', '')
                if is_fr_context(_setting):
                    _wiki = get_fr_wiki()
                    _loc = mm.starting_location or mm.display_name
                    _lore = _wiki.get_lore_summary(_loc, max_chars=400)
                    if _lore:
                        con.print(Panel(
                            f"[dim italic]{_lore}[/]",
                            title="Lore Archive",
                            border_style="blue",
                        ))
            except Exception:
                pass

        elif module_info and module_info.get("narrative_only"):
            # WO-V52.0: FITD engine with module — create scene state
            mm = module_info["manifest"]
            base_path = module_info["base_path"]
            if hasattr(engine, '_module_manifest'):
                engine._module_manifest = mm
            # Create ZoneManager + scene state for narrative runner
            _fitd_zm = ZoneManager(manifest=mm, base_path=base_path)
            _fitd_scene_state = _FITDSceneState(_fitd_zm, base_path)
            # Restore persisted scene progression if available
            _saved_scene = manifest.get("fitd_scene_state") if manifest else None
            if _saved_scene:
                _fitd_scene_state.restore_from_dict(_saved_scene)

    # Legacy: resolve module from campaign manifest
    if zm is None and resolved_id in DUNGEON_SYSTEMS and manifest and ZoneManager is not None:
        manifest_path = _resolve_module_manifest(manifest)
        if manifest_path:
            try:
                mm = ModuleManifest.load(manifest_path)
                base_path = str(Path(manifest_path).parent)
                zm = ZoneManager(manifest=mm, base_path=base_path)
                con.print(f"[dim]Module: {mm.display_name}[/dim]")
                if hasattr(engine, 'load_module'):
                    engine.load_module(manifest_path)
            except Exception:
                zm = None

    # WO-V62.0: Session type selection
    from codex.core.session_behaviors import get_session_labels, is_fitd_system
    from codex.core.session_frame import (
        SessionFrame, generate_opening_hook, generate_epilogue,
        get_next_session_number, save_session_counter,
    )

    # WO-V63.0: Skip session type prompt when loading a saved campaign
    _saved_session_type = manifest.get("session_type") if manifest else None
    if _saved_session_type:
        _session_type = _saved_session_type
        con.print(f"[dim]Session type: {_session_type}[/dim]")
    else:
        _session_labels = get_session_labels(resolved_id)
        con.print("\n[bold]Choose session type:[/bold]")
        for i, (stype, (label, desc)) in enumerate(_session_labels.items(), 1):
            con.print(f"  [{i}] [bold]{label}[/] — {desc}")
        _st_choice = con.input("[bold cyan]Select: [/bold cyan]").strip() or "3"
        _session_types_list = list(_session_labels.keys())
        try:
            _session_type = _session_types_list[int(_st_choice) - 1]
        except (ValueError, IndexError):
            _session_type = "campaign"

    # WO-V63.0: Persist session_type to campaign manifest for future loads
    if manifest and not manifest.get("session_type"):
        manifest["session_type"] = _session_type
        # Write back to campaign.json if we can find it
        for _save_dir in [Path(__file__).resolve().parent / "saves"]:
            if not _save_dir.exists():
                continue
            _cname = manifest.get("campaign_name", "")
            _cpath = _save_dir / _cname / "campaign.json"
            if _cpath.exists():
                try:
                    import json as _json
                    _cdata = _json.loads(_cpath.read_text())
                    _cdata["session_type"] = _session_type
                    _cpath.write_text(_json.dumps(_cdata, indent=2))
                except Exception:
                    pass

    _campaign_id = f"{resolved_id}_{id(engine)}"
    _session_number = get_next_session_number(_campaign_id)
    _session_frame = SessionFrame(
        session_id=f"{_campaign_id}_s{_session_number}",
        session_number=_session_number,
        session_type=_session_type,
        campaign_id=_campaign_id,
    )

    # Opening hook — only show generic hook if no module is loaded
    # (module-loaded sessions get their narration from read_aloud in the game loop)
    _has_module = zm is not None and not getattr(zm, 'module_complete', True)
    if not _has_module:
        _hook = generate_opening_hook(session_type=_session_type)
        if _hook:
            _session_frame.opening_hook = _hook
            con.print(Panel(f"[italic]{_hook}[/italic]", border_style="dim"))

    # Campaign loading screen — progress bar + memory shard synthesis
    _mem_engine, _dungeon_result = _campaign_loading_sequence(
        con, engine, resolved_id, manifest, zm)

    # Auto-open investigation case and start assignment for Candela
    if resolved_id == "candela" and hasattr(engine, '_cmd_open_case'):
        _case_module = "Unknown Assignment"
        if manifest:
            # Derive case name from module layer
            for layer in manifest.get("world_layers", []):
                if layer.get("type") == "module" and layer.get("name"):
                    _case_module = layer["name"]
                    break
        try:
            engine._cmd_open_case(case_name=_case_module, clues_needed=5)
        except Exception:
            pass
        # Auto-start the assignment so the gameplay loop begins immediately
        try:
            engine._cmd_start_assignment(name=_case_module)
        except Exception:
            pass

    # Activate GM profile on cortex for system-aware narration
    try:
        from codex.core.cortex import get_cortex
        _cortex = get_cortex()
        _cortex.active_system_id = resolved_id
        if manifest:
            _cortex.active_dm_influence = manifest.get("dm_influence")
    except Exception:
        pass

    # Write dm_frame.json so the DM Dashboard service view can detect the system
    try:
        from codex.paths import STATE_DIR
        _frame_path = STATE_DIR / "dm_frame.json"
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        _frame_data = {"system_tag": resolved_id.upper(), "system_name": system_name}
        if engine:
            # Add basic party info for the dashboard
            _party_info = []
            for p in getattr(engine, 'party', []):
                _party_info.append({
                    "name": getattr(p, 'name', '?'),
                    "hp": getattr(p, 'hp', 0),
                    "max_hp": getattr(p, 'max_hp', 0),
                    "alive": getattr(p, 'alive', True),
                })
            _frame_data["party"] = _party_info
        import json as _json_frame
        _frame_path.write_text(_json_frame.dumps(_frame_data, indent=2))
    except Exception:
        pass

    # Display pre-synthesized character introductions from manifest
    if manifest and manifest.get("character_introductions"):
        try:
            from codex.core.services.opening_narration import get_gm_title
            _gm_t = get_gm_title(resolved_id)
            con.print(Panel(
                manifest["character_introductions"],
                title=f"[bold]{_gm_t}[/bold] — Your Circle",
                border_style="yellow",
            ))
        except Exception:
            con.print(Panel(
                manifest["character_introductions"],
                title="Character Introductions",
                border_style="yellow",
            ))

    # Route to the appropriate game loop
    if resolved_id in DUNGEON_SYSTEMS:
        _run_dungeon_loop(con, engine, resolved_id, butler=butler,
                          zone_manager=zm, companion_agent=_companion_agent)
    elif resolved_id in FITD_SYSTEMS:
        # WO-V52.0: Pass scene state if a module was loaded
        fitd_ss = locals().get('_fitd_scene_state')
        _run_fitd_loop(con, engine, resolved_id, butler=butler,
                       scene_state=fitd_ss, companion_agent=_companion_agent)
    else:
        # Fallback: try FITD-style if engine has handle_command
        if hasattr(engine, 'handle_command'):
            _run_fitd_loop(con, engine, resolved_id, butler=butler,
                           companion_agent=_companion_agent)
        else:
            con.print(f"[yellow]No game loop available for {system_id}.[/yellow]")

    # WO-V62.0: Close session frame
    if _session_frame:
        _session_frame.turn_count = getattr(engine, 'turn_count', 0)
        _session_frame.close(getattr(engine, '_session_log', []))
        save_session_counter(_campaign_id, _session_number)


if __name__ == "__main__":
    import sys
    sid = sys.argv[1] if len(sys.argv) > 1 else "bitd"
    main(sid)

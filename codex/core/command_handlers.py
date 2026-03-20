"""
codex/core/command_handlers.py — Extracted Command Handlers
============================================================
Refactored from play_universal.py's monolithic loop functions.

SharedCommandHandler: quit, sheet, save, transition, layers, export, companion
FITDCommandHandler:   scene nav, talk, jobs, roll, resist, investigate, services
DungeonCommandHandler: zone, journey (bridge.step() is still in the loop)

Each handler returns:
    "break"    — exit the loop
    "continue" — skip to next input
    None       — not handled, fall through to next handler
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich import box

_SAVES_DIR = Path(__file__).resolve().parent.parent.parent / "saves"


# =========================================================================
# LOOP CONTEXT — mutable shared state for game loops
# =========================================================================

@dataclass
class LoopContext:
    """Mutable state shared across a game loop iteration.

    Handlers read and modify these fields. The loop sees the updates
    because LoopContext is a mutable reference object.
    """
    con: Console
    engine: Any
    system_id: str
    butler: Any = None
    stacked_char: Any = None      # Optional[StackedCharacter]
    dispatcher: Any = None        # Optional[StackedCommandDispatcher]
    # FITD-specific
    scene_state: Any = None       # Optional[_FITDSceneState]
    # Dungeon-specific
    zone_manager: Any = None
    bridge: Any = None            # Optional[_EngineWrappedBridge]
    # Companion
    companion_agent: Any = None   # Optional[GenericAutopilotAgent]

    def narrate(self, text: str) -> None:
        """Narrate text via butler if voice is enabled."""
        if self.butler and getattr(self.butler, '_voice_enabled', False):
            try:
                self.butler.narrate(text)
            except Exception:
                pass


# =========================================================================
# SHARED COMMAND HANDLER — commands common to FITD and Dungeon loops
# =========================================================================

class SharedCommandHandler:
    """Handles commands shared between FITD and Dungeon loops."""

    def dispatch(self, ctx: LoopContext, verb: str, parts: list) -> Optional[str]:
        """Try to handle verb. Returns 'break', 'continue', or None."""
        handler = self._DISPATCH.get(verb)
        if handler:
            return handler(self, ctx, parts)
        return None

    def _quit(self, ctx: LoopContext, parts: list) -> str:
        ctx.con.print("[dim]Returning to main menu...[/dim]")
        return "break"

    def _sheet(self, ctx: LoopContext, parts: list) -> str:
        from codex.core.sheet_renderer import render_sheet
        ctx.con.print(render_sheet(ctx.engine, ctx.system_id))
        return "continue"

    def _transition(self, ctx: LoopContext, parts: list) -> str:
        from play_universal import _transition_system, _render_status_panel
        result = _transition_system(ctx.con, ctx.engine, ctx.stacked_char, ctx.system_id)
        if result:
            ctx.engine = result["engine"]
            ctx.system_id = result["system_id"]
            ctx.stacked_char = result["stacked_char"]
            ctx.dispatcher = result["dispatcher"]
            # Rebuild bridge if in dungeon loop
            if ctx.bridge is not None:
                from play_universal import _EngineWrappedBridge
                ctx.bridge = _EngineWrappedBridge(ctx.engine)
                if ctx.butler and hasattr(ctx.bridge._bridge, 'set_butler'):
                    ctx.bridge._bridge.set_butler(ctx.butler)
            _render_status_panel(ctx.con, ctx.engine, ctx.system_id)
        return "continue"

    def _layers(self, ctx: LoopContext, parts: list) -> str:
        if ctx.stacked_char:
            from play_universal import _show_layers
            _show_layers(ctx.con, ctx.stacked_char)
        else:
            ctx.con.print("[dim]No engine stack active. Use 'transition' to start one.[/dim]")
        return "continue"

    def _export(self, ctx: LoopContext, parts: list) -> str:
        from codex.core.character_export import export_character, save_exported_character
        char = ctx.engine.party[0] if hasattr(ctx.engine, 'party') and ctx.engine.party else None
        if char:
            char_data = ctx.engine.save_state() if hasattr(ctx.engine, 'save_state') else {}
            exported = export_character(char_data, ctx.system_id)
            path = save_exported_character(exported)
            ctx.con.print(f"[green]Character exported to {path.name}[/green]")
        else:
            ctx.con.print("[dim]No character to export.[/dim]")
        return "continue"

    def _companion(self, ctx: LoopContext, parts: list) -> str:
        from play_universal import _handle_companion_command
        arg = " ".join(parts[1:]) if len(parts) > 1 else ""
        # Companion handler accepts either scene_state or bridge as 3rd arg
        state_or_bridge = ctx.scene_state if ctx.scene_state is not None else ctx.bridge
        _handle_companion_command(ctx.con, ctx.engine, state_or_bridge, arg)
        return "continue"

    def _dice(self, ctx: LoopContext, parts: list) -> str:
        """Free-form dice roll using the visual dice engine."""
        if len(parts) < 2:
            ctx.con.print("[dim]Usage: dice <expression>  (e.g. dice 2d20+5)[/dim]")
            return "continue"
        expression = parts[1]
        try:
            import asyncio
            from codex.core.dice import animate_terminal_roll
            total, rolls, modifier = asyncio.run(
                animate_terminal_roll(expression, console=ctx.con)
            )
        except RuntimeError:
            # Event loop already running (Discord hybrid) — fall back to static
            from codex.core.dice import roll_dice, format_roll_text
            total, rolls, modifier = roll_dice(expression)
            ctx.con.print(Panel(format_roll_text(total, rolls, modifier),
                                title="Dice Roll", border_style="yellow"))
        except Exception as e:
            ctx.con.print(f"[red]Dice error: {e}[/red]")
        return "continue"

    def _dashboard(self, ctx: LoopContext, parts: list) -> str:
        """Open the DM Dashboard for real-time engine monitoring."""
        from codex.core.dm_dashboard import DMDashboard, get_vitals
        dashboard = DMDashboard(ctx.con, ctx.system_id)
        try:
            vitals = get_vitals(ctx.engine, ctx.system_id)
        except Exception:
            vitals = None

        if vitals is not None:
            ctx.con.print(dashboard.render(vitals, ctx.engine))
        else:
            ctx.con.print(Panel("[dim]Vitals unavailable for this engine.[/dim]",
                                title="DM Dashboard", border_style="cyan"))

        # Simple DM command sub-loop
        ctx.con.print("[dim]DM Dashboard active. Type 'help' for commands, 'quit' or 'back' to exit.[/dim]")
        while True:
            try:
                cmd = ctx.con.input("[bold cyan]DM> [/bold cyan]").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not cmd:
                continue
            if cmd.lower() in ("quit", "back", "q", "exit"):
                break
            result = dashboard.dispatch_command(cmd, ctx.engine)
            if result:
                ctx.con.print(Panel(result, border_style="cyan"))
            # Re-render updated vitals after each command
            try:
                vitals = get_vitals(ctx.engine, ctx.system_id)
                ctx.con.print(dashboard.render(vitals, ctx.engine))
            except Exception:
                pass

        return "continue"

    _DISPATCH: Dict[str, Callable] = {
        "quit": _quit,
        "exit": _quit,
        "q": _quit,
        "sheet": _sheet,
        "doll": _sheet,
        "character": _sheet,
        "transition": _transition,
        "layers": _layers,
        "export": _export,
        "companion": _companion,
        "dice": _dice,
        "dashboard": _dashboard,
        "dm": _dashboard,
    }


# =========================================================================
# FITD COMMAND HANDLER — scene navigation, roleplay, rolls
# =========================================================================

class FITDCommandHandler:
    """Handles FITD-specific commands (scene nav, talk, roll, resist, etc.)."""

    def dispatch(self, ctx: LoopContext, verb: str, parts: list) -> Optional[str]:
        """Try to handle verb. Returns 'break', 'continue', or None."""
        # Conversation mode intercept — must check before normal dispatch
        if ctx.scene_state and ctx.scene_state.talking_to:
            return self._conversation_intercept(ctx, verb, parts)

        handler = self._DISPATCH.get(verb)
        if handler:
            return handler(self, ctx, parts)

        # Scene-only commands (only dispatch if scene_state exists)
        if ctx.scene_state:
            scene_handler = self._SCENE_DISPATCH.get(verb)
            if scene_handler:
                return scene_handler(self, ctx, parts)
            # Service alias match
            result = self._try_service_match(ctx, verb)
            if result is not None:
                return result

        return None

    # ── Conversation mode ──────────────────────────────────────────────

    def _conversation_intercept(self, ctx: LoopContext, verb: str, parts: list) -> str:
        """Handle input while in NPC conversation mode."""
        ss = ctx.scene_state
        if verb in ("bye", "leave", "goodbye"):
            name = ss.exit_conversation()
            ctx.con.print(f"[dim]You end your conversation with {name}.[/dim]")
            return "continue"

        if verb == "accept" and ss.pending_offer:
            job = ss.pending_offer
            ss.accepted_jobs.append(job)
            ss.pending_offer = None
            ctx.con.print(Panel(
                f"[bold green]Job Accepted:[/bold green] {job['title']}",
                border_style="green",
            ))
            return "continue"

        # Free-form NPC dialogue via Mimir
        npc_data = ss._talking_to_npc or {}
        npc_name = ss.talking_to
        scene = ss.current_scene()
        room_desc = ""
        events = []
        if scene:
            room_desc = scene.description if hasattr(scene, 'description') else scene.get("description", "")
            events = scene.event_triggers if hasattr(scene, 'event_triggers') else scene.get("event_triggers", [])
        setting_id = getattr(ctx.engine, 'setting_id', '')
        from codex.core.services.narrative_frame import query_npc_dialogue
        user_input = " ".join(parts)
        response = query_npc_dialogue(
            npc_name, user_input, npc_data,
            room_desc=room_desc, events=events, setting_id=setting_id,
        )
        if response:
            ctx.con.print(Panel(f'{npc_name}: "{response}"', border_style="cyan"))
        else:
            dialogue = npc_data.get("dialogue", "")
            if dialogue:
                ctx.con.print(Panel(f'{npc_name}: "{dialogue}"', border_style="cyan"))
            else:
                ctx.con.print(f"[dim]{npc_name} has nothing more to say.[/dim]")
        return "continue"

    # ── Standard commands ──────────────────────────────────────────────

    def _help(self, ctx: LoopContext, parts: list) -> str:
        from play_universal import _render_command_table
        _render_command_table(ctx.con, ctx.system_id)
        if ctx.scene_state:
            ctx.con.print(Panel(
                "scene / look    - Show current scene\n"
                "next            - Advance to next scene\n"
                "scenes          - List all scenes in zone\n"
                "talk <npc>      - Talk to scene NPC\n"
                "bye             - End conversation\n"
                "services        - List scene services\n"
                "investigate     - Investigation check\n"
                "accept          - Accept a job offer\n"
                "jobs            - List accepted jobs\n"
                "sheet           - Full character sheet",
                title="Scene Commands", border_style="magenta",
            ))
        return "continue"

    def _status(self, ctx: LoopContext, parts: list) -> str:
        from play_universal import _render_status_panel
        _render_status_panel(ctx.con, ctx.engine, ctx.system_id)
        return "continue"

    def _save(self, ctx: LoopContext, parts: list) -> str:
        try:
            if ctx.stacked_char:
                from play_universal import _save_stacked
                _save_stacked(ctx.con, ctx.engine, ctx.system_id, ctx.stacked_char)
            else:
                data = ctx.engine.save_state()
                if ctx.scene_state and hasattr(ctx.scene_state, 'to_dict'):
                    data["fitd_scene_state"] = ctx.scene_state.to_dict()
                _comp = getattr(ctx.scene_state, '_companion_agent', None)
                if _comp and _comp.evolution:
                    data["companion"] = {
                        "archetype": _comp.personality.archetype,
                        "name": _comp.personality.name,
                        "evolution": _comp.evolution.to_dict(),
                    }
                _SAVES_DIR.mkdir(parents=True, exist_ok=True)
                save_path = _SAVES_DIR / f"{ctx.system_id}_save.json"
                save_path.write_text(json.dumps(data, indent=2, default=str))
                ctx.con.print(f"[green]Game saved to {save_path.name}.[/green]")
        except Exception as e:
            ctx.con.print(f"[red]Save failed: {e}[/red]")
        return "continue"

    # ── Scene navigation ───────────────────────────────────────────────

    def _scene_look(self, ctx: LoopContext, parts: list) -> str:
        scene = ctx.scene_state.current_scene()
        if scene:
            title = f"Scene {ctx.scene_state.scene_idx + 1}/{ctx.scene_state.scene_count()}"
            ctx.con.print(Panel(
                ctx.scene_state.format_scene(scene),
                title=title, border_style="magenta", box=box.ROUNDED,
            ))
        else:
            ctx.con.print("[dim]No scene loaded.[/dim]")
        return "continue"

    def _scene_next(self, ctx: LoopContext, parts: list) -> str:
        ss = ctx.scene_state
        if ss.talking_to:
            ss.exit_conversation()
        scene = ss.advance_scene()
        if scene is None:
            ctx.con.print(Panel(
                f"[bold green]Zone Complete![/bold green]\n"
                f"[dim]All {ss.scene_count()} scenes visited.[/dim]",
                border_style="green",
            ))
            if not ss.zm.module_complete:
                choice = ctx.con.input(
                    "[bold cyan]Continue to next chapter? (y/n): [/bold cyan]"
                ).strip().lower()
                if choice in ("y", "yes", ""):
                    if ss.advance_zone():
                        scene = ss.current_scene()
                        if scene:
                            ctx.con.print(Panel(
                                ss.format_scene(scene),
                                title=f"{ss.zm.chapter_name} — Scene 1",
                                border_style="magenta", box=box.ROUNDED,
                            ))
                            ss.play_scene_audio()
                            _desc = getattr(scene, 'description', None) or (
                                scene.get("description", "") if isinstance(scene, dict) else ""
                            )
                            if _desc:
                                ctx.narrate(_desc[:300])
                    else:
                        ctx.con.print(Panel(
                            f"[bold gold1]MODULE COMPLETE![/bold gold1]\n"
                            f"{ss.zm.module_name} finished!",
                            border_style="gold1", box=box.DOUBLE,
                        ))
        else:
            title = f"Scene {ss.scene_idx + 1}/{ss.scene_count()}"
            ctx.con.print(Panel(
                ss.format_scene(scene),
                title=title, border_style="magenta", box=box.ROUNDED,
            ))
            ss.play_scene_audio()
            _desc = getattr(scene, 'description', None) or (
                scene.get("description", "") if isinstance(scene, dict) else ""
            )
            if _desc:
                ctx.narrate(_desc[:300])
        return "continue"

    def _scene_list(self, ctx: LoopContext, parts: list) -> str:
        ss = ctx.scene_state
        lines_out = []
        for i, (rid, rnode) in enumerate(ss.scene_list):
            marker = ">" if i == ss.scene_idx else " "
            visited = "[VISITED]" if rid in ss.visited else ""
            rtype = getattr(rnode, 'room_type', '')
            rtype_str = f" ({rtype.name})" if hasattr(rtype, 'name') else ""
            lines_out.append(f" {marker} Scene {i + 1}{rtype_str} {visited}")
        ctx.con.print(Panel(
            "\n".join(lines_out),
            title=f"Scenes — {ss.zm.zone_name}",
            border_style="cyan",
        ))
        return "continue"

    def _talk(self, ctx: LoopContext, parts: list) -> str:
        ss = ctx.scene_state
        arg = " ".join(parts[1:]) if len(parts) > 1 else ""
        scene = ss.current_scene()
        if not scene:
            ctx.con.print("[dim]No scene loaded.[/dim]")
            return "continue"
        npcs = scene.npcs if hasattr(scene, 'npcs') else scene.get("npcs", [])
        if not npcs:
            ctx.con.print("[dim]No NPCs in this scene.[/dim]")
            return "continue"
        if not arg:
            lines_out = ["NPCs in this scene:"]
            for npc in npcs:
                name = npc.name if hasattr(npc, 'name') else npc.get("name", "Unknown")
                role = npc.role if hasattr(npc, 'role') else npc.get("role", "")
                role_str = f" ({role})" if role else ""
                lines_out.append(f"  * {name}{role_str}")
            ctx.con.print(Panel("\n".join(lines_out), border_style="cyan"))
        else:
            target = arg.lower()
            found = False
            for npc in npcs:
                name = npc.name if hasattr(npc, 'name') else npc.get("name", "Unknown")
                if target in name.lower():
                    dialogue = npc.dialogue if hasattr(npc, 'dialogue') else npc.get("dialogue", "")
                    role = npc.role if hasattr(npc, 'role') else npc.get("role", "")
                    npc_dict = npc if isinstance(npc, dict) else {
                        "name": name, "role": role,
                        "dialogue": dialogue,
                        "notes": getattr(npc, 'notes', '') or '',
                    }
                    lines_out = [f"[bold]{name}[/bold]"]
                    if role:
                        lines_out.append(f"Role: {role}")
                    if dialogue:
                        lines_out.append(f'"{dialogue}"')
                    else:
                        lines_out.append(f"{name} has nothing to say.")
                    ss.enter_conversation(name, npc_dict)
                    lines_out.append("")
                    lines_out.append("[dim]Chat freely or 'bye' to end.[/dim]")
                    if "quest" in role.lower() or "fixer" in role.lower():
                        ss.pending_offer = {
                            "title": dialogue[:60] if dialogue else f"Job from {name}",
                            "npc": name,
                            "scene_idx": ss.scene_idx,
                        }
                        lines_out.append("[dim]Type 'accept' to take this job.[/dim]")
                    ctx.con.print(Panel("\n".join(lines_out), border_style="cyan"))
                    found = True
                    break
            if not found:
                ctx.con.print(f"[dim]No NPC named '{arg}' in this scene.[/dim]")
        return "continue"

    def _accept(self, ctx: LoopContext, parts: list) -> str:
        ss = ctx.scene_state
        if ss.pending_offer:
            job = ss.pending_offer
            ss.accepted_jobs.append(job)
            ss.pending_offer = None
            ctx.con.print(Panel(
                f"[bold green]Job Accepted:[/bold green] {job['title']}",
                border_style="green",
            ))
        else:
            ctx.con.print("[dim]No pending job offer. Talk to a quest NPC first.[/dim]")
        return "continue"

    def _jobs(self, ctx: LoopContext, parts: list) -> str:
        ss = ctx.scene_state
        if not ss.accepted_jobs:
            ctx.con.print("[dim]No jobs accepted yet.[/dim]")
        else:
            lines_out = []
            for i, job in enumerate(ss.accepted_jobs, 1):
                lines_out.append(f"  {i}. {job['title']} (from {job['npc']})")
            ctx.con.print(Panel(
                "\n".join(lines_out),
                title="Accepted Jobs", border_style="yellow",
            ))
        return "continue"

    def _services(self, ctx: LoopContext, parts: list) -> str:
        scene = ctx.scene_state.current_scene()
        if not scene:
            ctx.con.print("[dim]No scene loaded.[/dim]")
            return "continue"
        services = scene.services if hasattr(scene, 'services') else scene.get("services", [])
        if not services:
            ctx.con.print("[dim]No services in this scene.[/dim]")
        else:
            svc_text = "\n".join(f"  * {s}" for s in services)
            ctx.con.print(Panel(svc_text, title="Services", border_style="cyan"))
        return "continue"

    def _investigate(self, ctx: LoopContext, parts: list) -> str:
        scene = ctx.scene_state.current_scene()
        if not scene:
            ctx.con.print("[dim]No scene loaded.[/dim]")
            return "continue"
        dc = scene.investigation_dc if hasattr(scene, 'investigation_dc') else scene.get("investigation_dc", 0)
        if not dc:
            ctx.con.print("[dim]Nothing to investigate here.[/dim]")
        else:
            try:
                result = ctx.engine.handle_command("roll_action", action="study")
                ctx.con.print(Panel(result, title=f"Investigation (DC {dc})",
                                    border_style="yellow"))
            except Exception:
                ctx.con.print(f"[dim]Investigation DC: {dc}[/dim]")
        return "continue"

    def _roll(self, ctx: LoopContext, parts: list) -> str:
        if len(parts) < 2:
            ctx.con.print("[dim]Usage: roll <action>[/dim]")
            return "continue"
        action = parts[1].lower()
        try:
            result = ctx.engine.handle_command("roll_action", action=action)
            # WO-V69.0: Styled dice panel for roll results
            from play_universal import _render_fitd_dice_panel
            if isinstance(result, str) and result.startswith("Dice: ["):
                _render_fitd_dice_panel(ctx.con, result, "roll " + action)
            else:
                ctx.con.print(Panel(result, title="Roll Result", border_style="yellow"))
            ctx.narrate(result[:200])
        except Exception as e:
            ctx.con.print(f"[red]Roll failed: {e}[/red]")
        return "continue"

    def _resist(self, ctx: LoopContext, parts: list) -> str:
        action = parts[1].lower() if len(parts) >= 2 else "resist"
        stress_clock = getattr(ctx.engine, 'stress_clock', None)
        if stress_clock is None and hasattr(ctx.engine, 'party') and ctx.engine.party:
            stress_clock = getattr(ctx.engine.party[0], 'stress_clock', None)
        if stress_clock is None:
            ctx.con.print("[dim]No stress clock available for this engine.[/dim]")
            return "continue"
        import random as _rng
        dice = [_rng.randint(1, 6) for _ in range(2)]
        sixes = dice.count(6)
        stress_cost = max(0, 6 - sixes)
        result = stress_clock.resist(stress_cost)
        dice_str = ", ".join(str(d) for d in dice)
        lines_r = [
            f"[bold]Resist:[/bold] {action}",
            f"Dice: [{dice_str}]  Sixes: {sixes}  Stress cost: {stress_cost}",
            f"Stress: {result['new_stress']}/{stress_clock.max_stress}",
        ]
        if result.get("trauma_triggered"):
            lines_r.append(
                f"[bold red]TRAUMA:[/bold red] {result['new_trauma']} — "
                "stress cleared, trauma gained."
            )
        if result.get("broken"):
            lines_r.append("[bold red]You are BROKEN (4 traumas).[/bold red]")
        ctx.con.print(Panel("\n".join(lines_r), title="Resistance Roll",
                            border_style="yellow"))
        return "continue"

    def _recap(self, ctx: LoopContext, parts: list) -> str:
        """Synthesize a narrative recap from engine memory shards."""
        shards = getattr(ctx.engine, "_memory_shards", None)
        if not shards:
            ctx.con.print("[dim]No narrative shards recorded yet.[/dim]")
            return "continue"
        try:
            from codex.core.services.narrative_loom import synthesize_narrative
            result = synthesize_narrative("Session recap", shards)
            ctx.con.print(Panel(result, title="Session Recap", border_style="magenta"))
        except Exception as e:
            ctx.con.print(f"[red]Recap failed: {e}[/red]")
        return "continue"

    def _trace(self, ctx: LoopContext, parts: list) -> str:
        """Trace a narrative fact through memory shard layers."""
        if len(parts) < 2:
            ctx.con.print("[dim]Usage: trace <fact>[/dim]")
            return "continue"
        fact = " ".join(parts[1:])
        try:
            result = ctx.engine.trace_fact(fact)
            ctx.con.print(result)
        except AttributeError:
            ctx.con.print("[dim]This engine does not support fact tracing.[/dim]")
        except Exception as e:
            ctx.con.print(f"[red]Trace failed: {e}[/red]")
        return "continue"

    # ── Service match helper ───────────────────────────────────────────

    def _try_service_match(self, ctx: LoopContext, verb: str) -> Optional[str]:
        """Check if verb matches a scene service."""
        scene = ctx.scene_state.current_scene()
        if not scene:
            return None
        scene_services = scene.services if hasattr(scene, 'services') else scene.get("services", [])
        service_match = next(
            (s for s in scene_services
             if verb in str(s).lower() or str(s).lower() in verb),
            None,
        )
        if not service_match:
            return None
        from codex.core.services.narrative_frame import get_service_flavor
        flavor = get_service_flavor(str(service_match).lower(), ctx.system_id)
        if flavor:
            svc_result = flavor
        else:
            try:
                from codex.games.bridge import UniversalGameBridge
                _tmp_bridge = UniversalGameBridge.create_lightweight(ctx.engine)
                svc_result = _tmp_bridge._dispatch_service(str(service_match).lower())
            except Exception:
                svc_result = f"You use the {service_match} service."
        ctx.con.print(Panel(svc_result, border_style="cyan"))
        return "continue"

    # ── Dispatch tables ────────────────────────────────────────────────

    _DISPATCH: Dict[str, Callable] = {
        "help": _help,
        "status": _status,
        "save": _save,
        "roll": _roll,
        "resist": _resist,
        "recap": _recap,
        "trace": _trace,
    }

    _SCENE_DISPATCH: Dict[str, Callable] = {
        "scene": _scene_look,
        "look": _scene_look,
        "l": _scene_look,
        "next": _scene_next,
        "scenes": _scene_list,
        "talk": _talk,
        "npc": _talk,
        "accept": _accept,
        "jobs": _jobs,
        "journal": _jobs,
        "services": _services,
        "investigate": _investigate,
    }


# =========================================================================
# DUNGEON COMMAND HANDLER
# =========================================================================

class DungeonCommandHandler:
    """Handles dungeon-specific commands (zone, journey)."""

    def dispatch(self, ctx: LoopContext, verb: str, parts: list) -> Optional[str]:
        """Try to handle verb. Returns 'break', 'continue', or None."""
        handler = self._DISPATCH.get(verb)
        if handler:
            return handler(self, ctx, parts)
        return None

    def _zone(self, ctx: LoopContext, parts: list) -> str:
        if ctx.zone_manager and not ctx.zone_manager.module_complete:
            ctx.con.print(Panel(
                f"[bold]{ctx.zone_manager.module_name}[/bold]\n"
                f"Chapter: {ctx.zone_manager.chapter_name}\n"
                f"Zone: {ctx.zone_manager.zone_name}\n"
                f"Progress: {ctx.zone_manager.zone_progress}",
                title="Module Progress", border_style="cyan",
            ))
        else:
            ctx.con.print("[dim]No active module.[/dim]")
        return "continue"

    def _journey(self, ctx: LoopContext, parts: list) -> str:
        ctx.con.print("[dim]No active journey. Travel is triggered between zones.[/dim]")
        return "continue"

    _DISPATCH: Dict[str, Callable] = {
        "zone": _zone,
        "progress": _zone,
        "module": _zone,
        "journey": _journey,
    }

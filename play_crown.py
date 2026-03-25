#!/usr/bin/env python3
"""
CROWN & CREW — Terminal Interface
----------------------------------
Interactive terminal loop for the Crown & Crew narrative engine.
Supports variable-length arcs, quest archetypes, rest mechanics,
tarot card rendering, and Mimir's Vault access.

Version: 2.0 (Rest + Quests + Tarot)
"""

import json
import time
import sys
import os
from pathlib import Path
from codex.games.crown.engine import CrownAndCrewEngine

# Scene progression system (optional — backward compatible)
try:
    from codex.games.crown.scenes import CrownSceneRunner
    SCENES_AVAILABLE = True
except ImportError:
    SCENES_AVAILABLE = False

# Optional Rich + Tarot imports with fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from codex.integrations.tarot import render_tarot_card, get_card_for_context
    TAROT_AVAILABLE = True
except ImportError:
    TAROT_AVAILABLE = False

# Quest archetype system
try:
    from codex.games.crown.quests import list_quests, get_quest
    QUESTS_AVAILABLE = True
except ImportError:
    QUESTS_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def type_writer(text, speed=0.01):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()


def _render_plain(title: str | None, body: str):
    """Plain-text fallback renderer for terminals without Rich."""
    lines = []
    if title:
        lines.append(f"\n--- {title} ---")
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


def display_card(context: str, text: str, title: str | None = None):
    """Render text as a tarot card if available, else plain panel or print."""
    if TAROT_AVAILABLE and RICH_AVAILABLE:
        card_key = get_card_for_context(context)
        card = render_tarot_card(card_key, text, custom_title=title, width=60)
        console.print(card)
    elif RICH_AVAILABLE:
        console.print(Panel(text, title=title, width=60, box=box.HEAVY))
    else:
        console.print(_render_plain(title, text))


def offer_vault():
    """Between-day prompt that optionally opens Mimir's Vault."""
    print("\n  [Enter] Continue    [L] Consult Mimir's Vault    [T] Tutorial")
    choice = input("\n> ").strip().lower()
    if choice == "t":
        try:
            from rich.console import Console as RichConsole
            from codex.core.services.tutorial import TutorialBrowser, PlatformTutorial
            import codex.core.services.tutorial_content  # noqa: F401
            con = RichConsole()
            browser = TutorialBrowser(tutorial=PlatformTutorial(), system_filter="crown")
            browser.run_loop(con)
        except Exception:
            print("  [Tutorial unavailable]")
        return
    if choice == "l":
        try:
            from rich.console import Console as RichConsole
            from codex.core.services.librarian import LibrarianTUI
        except ImportError:
            print("  [Mimir's Vault unavailable]")
            return

        mimir_fn = None
        try:
            from codex.integrations.mimir import query_mimir
            mimir_fn = query_mimir
        except ImportError:
            pass

        con = RichConsole()
        lib = LibrarianTUI(mimir_fn=mimir_fn, system_id=None)
        lib.run_loop(con)


def select_quest() -> dict | None:
    """Show quest selection menu. Returns world_state dict or None for default."""
    if not QUESTS_AVAILABLE:
        return None

    quests = list_quests()
    if not quests:
        return None

    print("\n  [0] Prologue March (classic 5-day campaign)")
    for i, q in enumerate(quests, 1):
        print(f"  [{i}] {q.name} ({q.arc_length} days) — {q.description[:50]}")

    choice = input("\n> Select campaign type: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(quests):
        quest = quests[int(choice) - 1]
        return quest
    return None


def rest_choice(engine: CrownAndCrewEngine) -> str:
    """Prompt for rest type between days."""
    print("\n  [L] Long Rest (advance day)  [S] Short Rest (minor event)  [N] No Rest")
    choice = input("\n> Rest choice: ").strip().lower()
    if choice in ('s', 'short'):
        return engine.trigger_short_rest()
    elif choice in ('n', 'none'):
        return engine.skip_rest()
    else:
        return engine.trigger_long_rest()


def _parse_module_arg() -> str:
    """Return the value of --module <path> from sys.argv, or empty string."""
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--module" and i < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith("--module="):
            return arg.split("=", 1)[1]
    return ""


def _load_campaign_json(module_dir: str) -> dict:
    """Load campaign.json from a module directory.

    Args:
        module_dir: Path to the module directory.

    Returns:
        Parsed campaign.json dict, or empty dict on failure.
    """
    campaign_path = Path(module_dir) / "campaign.json"
    if not campaign_path.exists():
        return {}
    try:
        with open(campaign_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [Warning: could not load campaign.json — {e}]")
        return {}


def _discover_crown_modules() -> list:
    """Scan vault_maps/modules/ for crown module directories.

    Returns list of dicts with 'path' (module dir) and 'name' (display name).
    """
    modules_dir = Path(__file__).resolve().parent / "vault_maps" / "modules"
    if not modules_dir.is_dir():
        return []
    results = []
    for entry in sorted(modules_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Check for campaign.json (crown modules) or module_manifest.json with system_id=crown
        campaign = entry / "campaign.json"
        manifest = entry / "module_manifest.json"
        if campaign.exists():
            try:
                data = json.loads(campaign.read_text())
                results.append({
                    "path": str(entry),
                    "name": data.get("campaign_title", entry.name),
                })
                continue
            except Exception:
                pass
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text())
                if data.get("system_id") == "crown":
                    results.append({
                        "path": str(entry),
                        "name": data.get("display_name", entry.name),
                    })
            except Exception:
                continue
    return results


def main():
    clear_screen()

    # --- Module argument (--module <path>) ---
    module_dir = _parse_module_arg()
    campaign_data: dict = {}
    if module_dir:
        campaign_data = _load_campaign_json(module_dir)
        if campaign_data:
            print(f"  [Module loaded: {Path(module_dir).name}]")

    # --- Module discovery (interactive) ---
    if not module_dir:
        crown_mods = _discover_crown_modules()
        if crown_mods:
            print("\n  Adventure Modules:")
            print("  [0] Original Campaign")
            for i, m in enumerate(crown_mods, 1):
                print(f"  [{i}] {m['name']}")
            try:
                choice = input("  Select module [0]: ").strip() or "0"
                idx = int(choice)
                if 0 < idx <= len(crown_mods):
                    module_dir = crown_mods[idx - 1]["path"]
                    campaign_data = _load_campaign_json(module_dir)
                    if campaign_data:
                        print(f"  [Module loaded: {Path(module_dir).name}]")
            except (ValueError, EOFError, KeyboardInterrupt):
                pass

    # --- Quest Selection ---
    print("=" * 58)
    print("        CROWN & CREW: NARRATIVE CAMPAIGN ENGINE")
    print("=" * 58)

    quest = select_quest()
    if quest is not None:
        world_state = quest.to_world_state()
        # Merge module world_state fields if present (module takes lower priority)
        if campaign_data.get("world_state"):
            merged = dict(campaign_data["world_state"])
            merged.update(world_state)
            world_state = merged
        engine = CrownAndCrewEngine(
            world_state=world_state,
            arc_length=quest.arc_length,
            rest_config=quest.rest_config,
        )
        campaign_title = quest.name
    elif campaign_data.get("world_state"):
        engine = CrownAndCrewEngine(world_state=campaign_data["world_state"])
        campaign_title = campaign_data.get("campaign_title", "The Prologue March")
    else:
        engine = CrownAndCrewEngine()
        campaign_title = campaign_data.get("campaign_title", "The Prologue March")

    # --- Attach scene runner if campaign data contains scene definitions ---
    if SCENES_AVAILABLE and campaign_data:
        runner = CrownSceneRunner.from_campaign_json(campaign_data)
        if not runner.is_complete() or runner.chapters:
            engine.set_scene_runner(runner)

    clear_screen()

    # --- Campaign Banner ---
    crown_term = engine.terms.get("crown", "The Crown")
    crew_term = engine.terms.get("crew", "The Crew")

    if RICH_AVAILABLE:
        banner = Panel(
            f"[bold]{crown_term}[/bold] vs [bold]{crew_term}[/bold]\n\n"
            f"Patron: [cyan]{engine.patron}[/cyan]\n"
            f"Leader: [magenta]{engine.leader}[/magenta]\n"
            f"Arc: {engine.arc_length} days",
            title=f"[bold gold1]{campaign_title}[/bold gold1]",
            border_style="gold1",
            box=box.DOUBLE,
            width=58,
        )
        console.print(banner)
    else:
        print(f"\n  {campaign_title}")
        print(f"  {crown_term} vs {crew_term}")
        print(f"  Patron: {engine.patron}")
        print(f"  Leader: {engine.leader}")
        print(f"  Arc: {engine.arc_length} days")

    print("\nThe journey begins now...")
    time.sleep(2)

    # --- Main Day Loop ---
    while engine.day <= engine.arc_length:
        clear_screen()

        # --- MORNING EVENT (WO-V107: Interactive) ---
        morning = engine.get_morning_event()
        if RICH_AVAILABLE:
            console.print(
                Panel(
                    f"[dim italic]{morning['text']}[/dim italic]",
                    title=f"[bold]Dawn — Day {engine.day}/{engine.arc_length}[/bold]",
                    border_style="yellow",
                    width=60,
                )
            )
        else:
            print(f"\n--- Dawn — Day {engine.day}/{engine.arc_length} ---")
            print(f"  {morning['text']}")

        # Present morning choices (WO-V104: sway-gated bonus options)
        choices = engine.get_gated_morning_choices(morning)
        if choices:
            print()
            for i, ch in enumerate(choices):
                tag_color = {"BLOOD": "red", "GUILE": "yellow", "HEARTH": "green",
                             "SILENCE": "dim", "DEFIANCE": "magenta"}.get(ch.get("tag", ""), "white")
                sway_indicator = ""
                se = ch.get("sway_effect", 0)
                if se < 0:
                    sway_indicator = f" [{crown_term}]"
                elif se > 0:
                    sway_indicator = f" [{crew_term}]"

                if RICH_AVAILABLE:
                    console.print(f"  [{tag_color}][{i + 1}] {ch['text']}[/{tag_color}]{sway_indicator}")
                else:
                    print(f"  [{i + 1}] {ch['text']}{sway_indicator}")

            morning_choice = ""
            while not morning_choice.isdigit() or not (1 <= int(morning_choice) <= len(choices)):
                morning_choice = input(f"\n> Your choice (1-{len(choices)}): ").strip()
                if not morning_choice:
                    morning_choice = "1"

            morning_result = engine.resolve_morning_choice(int(morning_choice) - 1, morning)
            if RICH_AVAILABLE:
                console.print(f"\n[bold]{morning_result}[/bold]")
            else:
                print(f"\n--> {morning_result}")

        time.sleep(1)

        # --- THE WORLD ---
        world_prompt = engine.get_world_prompt()
        display_card("world", world_prompt, f"[dim]Day {engine.day} — The Hostile Grounds[/dim]")

        # --- MIDDAY ENCOUNTER (WO-V109) ---
        midday = engine.get_midday_encounter()
        if midday:
            # Check for Safe Passage bypass
            if engine.can_bypass_midday():
                print()
                if RICH_AVAILABLE:
                    console.print(f"[dim italic]{midday['text'][:100]}...[/dim italic]")
                    console.print(f"\n[cyan][0] Use Safe Passage — bypass this encounter[/cyan]")
                else:
                    print(f"  {midday['text'][:100]}...")
                    print(f"\n  [0] Use Safe Passage — bypass this encounter")

            print()
            if RICH_AVAILABLE:
                console.print(Panel(
                    midday["text"],
                    title=f"[bold]Midday — The March[/bold]",
                    border_style="dim yellow",
                    width=60,
                ))
            else:
                print(f"\n--- Midday — The March ---")
                print(f"  {midday['text']}")

            midday_choices = engine.get_gated_midday_choices(midday)
            for i, ch in enumerate(midday_choices):
                tag_color = {"BLOOD": "red", "GUILE": "yellow", "HEARTH": "green",
                             "SILENCE": "dim", "DEFIANCE": "magenta"}.get(ch.get("tag", ""), "white")
                if RICH_AVAILABLE:
                    console.print(f"  [{tag_color}][{i + 1}] {ch['text']}[/{tag_color}]")
                else:
                    print(f"  [{i + 1}] {ch['text']}")

            # Safe Passage option
            valid_range = range(1, len(midday_choices) + 1)
            allow_zero = engine.can_bypass_midday()

            midday_input = ""
            while True:
                midday_input = input(f"\n> Your choice ({('0/' if allow_zero else '')}1-{len(midday_choices)}): ").strip()
                if not midday_input:
                    midday_input = "1"
                if midday_input == "0" and allow_zero:
                    break
                if midday_input.isdigit() and int(midday_input) in valid_range:
                    break

            if midday_input == "0":
                bypass_result = engine.use_safe_passage()
                if RICH_AVAILABLE:
                    console.print(f"\n[bold cyan]{bypass_result}[/bold cyan]")
                else:
                    print(f"\n--> {bypass_result}")
            else:
                midday_result = engine.resolve_midday_choice(int(midday_input) - 1, {"choices": midday_choices})
                if RICH_AVAILABLE:
                    console.print(f"\n[bold]{midday_result}[/bold]")
                else:
                    print(f"\n--> {midday_result}")

        time.sleep(1)

        # --- NIGHT: THE CAMPFIRE ---
        print()
        if RICH_AVAILABLE:
            console.print(f"[bold red]NIGHT FALLS.[/bold red] [dim]{engine.get_status()}[/dim]")
        else:
            print(f"NIGHT FALLS. {engine.get_status()}")

        # Breach Day Special — THE MIRROR (WO-V99)
        if engine.is_breach_day():
            mirror = engine.get_mirror_break()

            if RICH_AVAILABLE:
                console.print(Panel(
                    f"[bold red]THE MIRROR — {mirror['sin'].upper()}[/bold red]\n\n"
                    f"[italic]{mirror['witness']}[/italic]",
                    title=f"[bold red]Day {engine.day} — The Breach[/bold red]",
                    border_style="red",
                    width=60,
                ))
            else:
                print(f"\n=== THE MIRROR — {mirror['sin'].upper()} ===")
                print(f"\n{mirror['witness']}")

            print()
            for i, ch in enumerate(mirror["choices"]):
                tag_color = {"SILENCE": "dim", "DEFIANCE": "magenta"}.get(ch["tag"], "white")
                if RICH_AVAILABLE:
                    console.print(f"  [{tag_color}][{i + 1}] {ch['text']}[/{tag_color}]")
                else:
                    print(f"  [{i + 1}] {ch['text']}")

            mirror_input = ""
            while mirror_input not in ['1', '2']:
                mirror_input = input("\n> What do you do? (1/2): ").strip()

            mirror_result = engine.resolve_mirror_choice(int(mirror_input) - 1)
            if RICH_AVAILABLE:
                console.print(f"\n[bold]{mirror_result}[/bold]")
            else:
                print(f"\n{mirror_result}")

            input("\n[Press Enter to continue...]")

        # --- SCENE PHASE (optional, from campaign.json) ---
        scene = engine.get_scene_for_today()
        if scene:
            print()
            if RICH_AVAILABLE:
                scene_title = scene.location if scene.location else f"Day {engine.day} — Scene"
                console.print(Panel(
                    scene.description,
                    title=f"[bold]{scene_title}[/bold]",
                    border_style="cyan",
                    width=60,
                ))
            else:
                loc = scene.location or f"Day {engine.day}"
                print(f"\n--- {loc} ---")
                print(f"  {scene.description}")

            for i, text in enumerate(scene.get_choice_texts()):
                print(f"  [{i + 1}] {text}")

            scene_input = ""
            while not scene_input.isdigit() or not (1 <= int(scene_input) <= len(scene.choices)):
                scene_input = input("\n> Your choice: ").strip()
                if not scene_input:
                    scene_input = "1"

            result = engine.resolve_scene_choice(int(scene_input) - 1)
            if result.get("narrative"):
                print(f"\n  {result['narrative']}")
            sway_delta = result.get("sway_effect", 0)
            if sway_delta != 0:
                direction = "toward the Crown" if sway_delta > 0 else "toward the Crew"
                print(f"  [Sway shifts {direction}. Now: {engine.sway:+d}]")
            print()
            input("[Press Enter to continue...]")

        # --- Allegiance Choice ---
        print(f"\nWho do you serve tonight?")
        print(f"  [C] {crown_term} (Order, Law, Safety)")
        print(f"  [R] {crew_term} (Freedom, Bonds, Chaos)")

        choice = ""
        while choice not in ['c', 'r']:
            choice = input("\n> Your Choice (C/R): ").lower().strip()

        side = "crown" if choice == 'c' else "crew"
        result_text = engine.declare_allegiance(side)  # No tag — Echo step follows

        if RICH_AVAILABLE:
            console.print(f"\n[bold]{result_text}[/bold]")
        else:
            print(f"\n--> {result_text}")

        # --- Allegiance Prompt Reveal ---
        prompt = engine.get_prompt()
        card_context = "crown" if side == "crown" else "crew"
        display_card(card_context, prompt, f"[dim]The Dilemma[/dim]")

        # --- THE ECHO: How did you respond? (WO-V108) ---
        echo_frame = engine.get_echo_frame()
        echo_responses = engine.get_echo_responses()

        print()
        if RICH_AVAILABLE:
            console.print(f"[bold italic]{echo_frame}[/bold italic]")
        else:
            print(f"  {echo_frame}")
        print()
        for i, resp in enumerate(echo_responses):
            tag_color = {"BLOOD": "red", "GUILE": "yellow", "HEARTH": "green",
                         "SILENCE": "dim", "DEFIANCE": "magenta"}.get(resp["tag"], "white")
            if RICH_AVAILABLE:
                console.print(f"  [{tag_color}][{i + 1}] {resp['label']}[/{tag_color}] — {resp['desc']}")
            else:
                print(f"  [{i + 1}] {resp['label']} — {resp['desc']}")

        echo_choice = ""
        while not echo_choice.isdigit() or not (1 <= int(echo_choice) <= len(echo_responses)):
            echo_choice = input("\n> How did you respond? (1-5): ").strip()
            if not echo_choice:
                echo_choice = "1"

        chosen = echo_responses[int(echo_choice) - 1]
        echo_result = engine.resolve_echo(chosen["tag"])

        if RICH_AVAILABLE:
            console.print(f"\n[bold]{echo_result}[/bold]")
        else:
            print(f"\n--> {echo_result}")

        time.sleep(1)

        # --- Campfire (not on Breach day) ---
        if not engine.is_breach_day():
            campfire = engine.get_campfire_prompt()
            display_card("campfire", campfire, f"[dim]The {engine.terms.get('campfire', 'Campfire')}[/dim]")

        input("\n[PRESS ENTER TO PROCEED TO MIDNIGHT COUNCIL]")

        # --- MIDNIGHT COUNCIL ---
        clear_screen()
        dilemma = engine.get_council_dilemma()

        if RICH_AVAILABLE:
            dilemma_text = (
                f"[italic]{dilemma['prompt']}[/italic]\n\n"
                f"[cyan][1] {crown_term}: {dilemma['crown']}[/cyan]\n"
                f"[magenta][2] {crew_term}: {dilemma['crew']}[/magenta]"
            )
            console.print(Panel(
                dilemma_text,
                title=f"[bold]Day {engine.day} — Midnight Council[/bold]",
                border_style="bright_white",
                box=box.DOUBLE,
                width=60,
            ))
        else:
            print(f"\n--- Day {engine.day}: Midnight Council ---")
            print(f"  {dilemma['prompt']}")
            print(f"\n  [1] {crown_term}: {dilemma['crown']}")
            print(f"  [2] {crew_term}: {dilemma['crew']}")

        vote = ""
        while vote not in ['1', '2']:
            vote = input("\n> Your Vote (1/2): ").strip()

        vote_side = "crown" if vote == '1' else "crew"
        result = engine.resolve_vote({vote_side: 1}, dilemma=dilemma)

        if RICH_AVAILABLE:
            console.print(f"\n[bold]{result['flavor']}[/bold]")
        else:
            print(f"\n--> {result['flavor']}")

        # WO-V110: Display council consequence
        consequence = result.get("consequence")
        if consequence and consequence.get("narrative"):
            time.sleep(1)
            if RICH_AVAILABLE:
                console.print(f"\n[dim italic]{consequence['narrative']}[/dim italic]")
            else:
                print(f"\n  {consequence['narrative']}")

        # --- Rest Choice ---
        # WO-V111: Rest deprecated — C&C is a narrative overlay.
        # Day advancement happens via end_day() in the council resolution.
        # The overlaid game system handles rest mechanics.
        end_msg = engine.end_day()
        if RICH_AVAILABLE:
            console.print(f"\n[dim]{end_msg}[/dim]")
        else:
            print(f"\n{end_msg}")

        offer_vault()

    # === THE FINALE ===
    clear_screen()

    # --- ACT 1: Patron's Reckoning (WO-V116) ---
    patron_scene = engine.generate_patron_reckoning()
    if RICH_AVAILABLE:
        console.print(Panel(
            f"[italic]{patron_scene['narrative']}[/italic]",
            title=f"[bold cyan]Act I — {patron_scene['patron_name']}[/bold cyan]",
            border_style="cyan",
            width=60,
        ))
    else:
        print(f"\n=== Act I — {patron_scene['patron_name']} ===")
        print(f"\n{patron_scene['narrative']}")

    print()
    for i, ch in enumerate(patron_scene["choices"]):
        if RICH_AVAILABLE:
            console.print(f"  [cyan][{i + 1}] {ch['text']}[/cyan]")
        else:
            print(f"  [{i + 1}] {ch['text']}")

    patron_input = ""
    while patron_input not in ['1', '2', '3']:
        patron_input = input("\n> Your response (1-3): ").strip()
    patron_response = patron_scene["choices"][int(patron_input) - 1]["response"]
    patron_result = engine.resolve_patron_response(patron_response)

    if RICH_AVAILABLE:
        console.print(f"\n[bold]{patron_result}[/bold]")
    else:
        print(f"\n{patron_result}")

    input("\n[Press Enter to continue...]")
    clear_screen()

    # --- ACT 2: Leader's Reckoning (WO-V117) ---
    leader_scene = engine.generate_leader_reckoning()
    if RICH_AVAILABLE:
        console.print(Panel(
            f"[italic]{leader_scene['narrative']}[/italic]",
            title=f"[bold magenta]Act II — {leader_scene['leader_name']}[/bold magenta]",
            border_style="magenta",
            width=60,
        ))
    else:
        print(f"\n=== Act II — {leader_scene['leader_name']} ===")
        print(f"\n{leader_scene['narrative']}")

    print()
    for i, ch in enumerate(leader_scene["choices"]):
        if RICH_AVAILABLE:
            console.print(f"  [magenta][{i + 1}] {ch['text']}[/magenta]")
        else:
            print(f"  [{i + 1}] {ch['text']}")

    leader_input = ""
    while leader_input not in ['1', '2', '3']:
        leader_input = input("\n> Your response (1-3): ").strip()
    leader_response = leader_scene["choices"][int(leader_input) - 1]["response"]
    leader_result = engine.resolve_leader_response(leader_response)

    if RICH_AVAILABLE:
        console.print(f"\n[bold]{leader_result}[/bold]")
    else:
        print(f"\n{leader_result}")

    input("\n[Press Enter to continue...]")
    clear_screen()

    # --- ACT 3: The Crossing (WO-V118) ---
    ending = engine.determine_ending()
    if RICH_AVAILABLE:
        console.print(Panel(
            f"[bold]{ending['title'].upper()}[/bold]\n\n"
            f"[italic]{ending['narrative']}[/italic]\n\n"
            f"[dim]{ending['campaign_hook']}[/dim]",
            title=f"[bold gold1]Act III — The Crossing[/bold gold1]",
            border_style="gold1",
            box=box.DOUBLE,
            width=60,
        ))
    else:
        print(f"\n{'=' * 60}")
        print(f"  {ending['title'].upper()}")
        print(f"{'=' * 60}")
        print(f"\n{ending['narrative']}")
        print(f"\n{ending['campaign_hook']}")

    input("\n[Press Enter for Legacy Report...]")
    clear_screen()

    # --- LEGACY REPORT ---
    report = engine.generate_legacy_report()
    display_card("legacy", report, "[bold gold1]Legacy Report[/bold gold1]")

    # Save structured JSON + text
    import json as _json
    from pathlib import Path
    saves_dir = Path(__file__).resolve().parent / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)

    # JSON receipt (machine-readable)
    legacy_json = engine.generate_legacy_json()
    legacy_json["patron_final_response"] = patron_response
    legacy_json["leader_final_response"] = leader_response
    legacy_json["ending"] = ending["ending_id"]
    legacy_json["ending_narrative"] = ending["narrative"]
    legacy_json["campaign_hook"] = ending["campaign_hook"]

    json_filename = saves_dir / f"legacy_{int(time.time())}.json"
    with open(json_filename, "w") as f:
        _json.dump(legacy_json, f, indent=2)
    print(f"\nLegacy JSON saved to {json_filename}")

    # Text receipt (human-readable)
    txt_filename = saves_dir / f"legacy_{int(time.time())}.txt"
    with open(txt_filename, "w") as f:
        f.write(report)
    print(f"Legacy text saved to {txt_filename}")


if __name__ == "__main__":
    main()

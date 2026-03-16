#!/usr/bin/env python3
"""
DM Live Test — Multi-Engine Diagnostic with Real LLM
=====================================================
Exercises EVERY game engine through a DM→Companion loop:
  1. Burnwillow  — dungeon crawl (DM tools + Autopilot + Mimir narration)
  2. Crown & Crew — political arc (morning events + dilemmas + sway)
  3. Blades in the Dark — FITD heist (action rolls + stress + entanglement)
  4. D&D 5e      — dungeon delve (d20 checks + generated dungeon)
  5. Cosmere      — Roshar expedition (surge checks + stormlight)

After each engine, reports what DM tools exist vs. what's MISSING.
This is the diagnostic foundation for building a robust DM View.

Usage: PYTHONPATH=. python scripts/dm_live_test.py
"""

import sys
import random
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Rich output ──────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    class _FallbackConsole:
        def print(self, *a, **kw): print(*[str(x) for x in a])
        def rule(self, *a, **kw): print("=" * 70)
    console = _FallbackConsole()

OLLAMA_URL = "http://localhost:11434/api/generate"


# ═════════════════════════════════════════════════════════════════════
# LLM HELPER
# ═════════════════════════════════════════════════════════════════════

def llm_call(model: str, prompt: str, max_tokens: int = 100) -> str:
    """Call Ollama. Returns response text or error string."""
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.7},
        }, timeout=30)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.Timeout:
        return "[LLM timeout]"
    except requests.ConnectionError:
        return "[Ollama not running]"
    except Exception as e:
        return f"[LLM error: {e}]"


def section(title: str):
    """Print a major section header."""
    console.print("")
    if HAS_RICH:
        console.rule(f"[bold red]{title}[/bold red]")
    else:
        console.print(f"\n{'='*70}\n  {title}\n{'='*70}")


def subsection(title: str):
    if HAS_RICH:
        console.print(f"\n  [bold yellow]{title}[/bold yellow]")
    else:
        console.print(f"\n  --- {title} ---")


def report_card(system_name: str, has: list, missing: list):
    """Print a capability report card for a system."""
    if HAS_RICH:
        table = Table(
            title=f"{system_name} — DM Tool Report Card",
            show_header=True, border_style="dim",
            box=box.SIMPLE_HEAVY,
        )
        table.add_column("Capability", style="bold")
        table.add_column("Status")
        table.add_column("Notes")
        for name, note in has:
            table.add_row(name, "[green]HAS[/green]", note)
        for name, note in missing:
            table.add_row(name, "[red]MISSING[/red]", note)
        console.print(table)
    else:
        console.print(f"\n  {system_name} Report Card:")
        for name, note in has:
            console.print(f"    [HAS]     {name} — {note}")
        for name, note in missing:
            console.print(f"    [MISSING] {name} — {note}")


# ═════════════════════════════════════════════════════════════════════
# ENGINE 1: BURNWILLOW — Full dungeon crawl with DM + Companion
# ═════════════════════════════════════════════════════════════════════

def test_burnwillow():
    section("ENGINE 1: BURNWILLOW — Dungeon Crawl")

    from codex.games.burnwillow.engine import BurnwillowEngine
    from codex.games.burnwillow.autopilot import (
        AutopilotAgent, PERSONALITY_POOL, create_ai_character,
    )
    from codex.games.burnwillow.content import (
        get_random_enemy, get_random_loot, get_party_scaling,
    )
    from codex.core.dm_tools import (
        roll_dice, generate_npc, generate_trap, generate_encounter,
        summarize_context,
    )

    # Create AI companion
    personality, name, stats, loadout, bio = create_ai_character(
        seed=42, archetype="vanguard",
    )
    agent = AutopilotAgent(personality=personality, biography=bio)
    console.print(f"  Companion: {name} the {personality.archetype.title()}")
    console.print(f"  Stats: {stats}")
    console.print(f"  Bio: {bio}")

    # Init engine
    engine = BurnwillowEngine()
    engine.create_party([name, "Sera", "Grim"])
    engine.equip_loadout(loadout)
    engine.generate_dungeon(depth=3, seed=42, zone=1)
    console.print(f"  Dungeon: {len(engine.dungeon_graph.rooms)} rooms generated")

    rng = random.Random(42)
    session_log = []

    # 5-turn crawl
    for turn in range(1, 6):
        subsection(f"Turn {turn} | HP: {engine.character.current_hp}/{engine.character.max_hp} | Doom: {engine.doom_clock.current}/22")

        if not engine.character.is_alive():
            console.print("    CHARACTER DOWN.")
            break

        # DM: Generate encounter
        enc_text = generate_encounter(system_tag="BURNWILLOW", tier=min(3, turn), party_size=3)
        console.print(f"    DM Encounter:\n{enc_text[:200]}")

        # DM: Spawn enemy
        enemy = get_random_enemy(min(3, turn), rng)
        console.print(f"    Enemy: {enemy['name']} (HP:{enemy['hp']} DMG:{enemy.get('dmg', enemy.get('damage', '?'))})")

        # AI: Combat decision
        snap = {
            "hp_pct": engine.character.current_hp / max(1, engine.character.max_hp),
            "enemies": [{"name": enemy["name"], "hp": enemy["hp"],
                         "max_hp": enemy["hp"], "is_boss": False}],
            "allies": [{"name": "Sera", "hp": 8, "max_hp": 10, "hp_pct": 0.8}],
            "traits": [], "char_name": name,
        }
        action = agent.decide_combat(snap)
        console.print(f"    AI Decision: {action}")

        # LLM: Companion speaks
        dialogue = llm_call("llama3.2:1b",
            f"You are {name}, a {personality.archetype}. {personality.quirk} "
            f"You chose '{action}' against {enemy['name']}. "
            f"Say ONE sentence in character (under 15 words).",
            max_tokens=30)
        console.print(f'    {name} says: "{dialogue}"')

        # LLM: Mimir narrates
        narration = llm_call("mimir",
            f"Dark fantasy narrator. In 1 sentence describe combat against "
            f"{enemy['name']} in a dungeon room. Foreboding tone.",
            max_tokens=50)
        console.print(f"    Mimir: {narration}")

        # DM: Roll combat
        atk_total, atk_msg = roll_dice("1d20+3")
        dmg_total, dmg_msg = roll_dice("1d8+2")
        console.print(f"    Attack: {atk_msg} | Damage: {dmg_msg}")

        # DM: Trap (30%)
        if rng.random() < 0.3:
            trap = generate_trap(["easy", "medium", "hard"][min(2, turn - 1)])
            console.print(f"    TRAP: {trap}")

        # DM: Loot (50%)
        if rng.random() < 0.5:
            loot = get_random_loot(min(3, turn), rng)
            console.print(f"    LOOT: {loot['name']} (T{loot['tier']})")

        # DM: NPC (20%)
        if rng.random() < 0.2:
            npc = generate_npc()
            console.print(f"    NPC: {npc[:100]}")

        engine.advance_doom(1)
        session_log.append(f"Turn {turn}: {action} vs {enemy['name']}")

    # LLM: Session summary
    subsection("Session Summary (LLM)")
    summary = summarize_context("\n".join(session_log))
    console.print(f"    {summary}")

    # Report card
    report_card("Burnwillow", [
        ("Dungeon Generation", "BSP procedural, seeded"),
        ("Enemy Tables", "Tiered 1-4, archetypes, DR, AoE"),
        ("Loot Tables", "Tiered 1-4, slot-aware, special traits"),
        ("Trap Generator", "3 difficulties, DC/damage scaling"),
        ("NPC Generator", "Names, traits, quirks, archetype stats"),
        ("Encounter Generator", "Full context + entities + doom cost"),
        ("Dice Roller", "Core d6 pool + d20 DM tools"),
        ("AI Companion", "4 archetypes, heuristic decisions"),
        ("LLM Narration", "Mimir atmosphere, llama3.2 dialogue"),
        ("Party Scaling", "HP/DMG mult for 1-6 players"),
        ("Save/Load", "Full state persistence"),
        ("Session Summary", "Ollama-backed compression"),
        ("Doom Clock", "7-threshold escalation"),
        ("Wave Spawns", "3-wave threat escalation"),
    ], [
        ("DM Bestiary Lookup", "No indexed monster manual search"),
        ("DM Condition Tracker", "No persistent status effects on enemies"),
        ("DM Initiative Tracker", "No turn-order management tool"),
        ("DM Room Description Generator", "Relies on LLM, no template table"),
        ("AI Companion Hub Decisions", "Hub heuristics are minimal"),
    ])

    return True


# ═════════════════════════════════════════════════════════════════════
# ENGINE 2: CROWN & CREW — Political narrative arc
# ═════════════════════════════════════════════════════════════════════

def test_crown():
    section("ENGINE 2: CROWN & CREW — Political Arc")

    from codex.games.crown.engine import (
        CrownAndCrewEngine, MORNING_EVENTS, COUNCIL_DILEMMAS,
    )

    engine = CrownAndCrewEngine(arc_length=5)
    engine.setup()
    console.print(f"  Arc Length: {engine.arc_length} days")
    console.print(f"  Morning Events Pool: {len(MORNING_EVENTS)}")
    console.print(f"  Council Dilemmas Pool: {len(COUNCIL_DILEMMAS)}")

    # Simulate 3-day arc
    for day in range(1, 4):
        subsection(f"Day {day} | Sway: {engine.sway} | Alignment: {engine.get_alignment()}")

        # Morning event
        morning = engine.get_morning_event()
        if morning:
            console.print(f"    Morning: {morning.get('text', 'N/A')[:100]}")
            console.print(f"    Bias: {morning.get('bias', 'neutral')}")
        else:
            console.print("    Morning: No event (Day 1 neutral pool empty?)")

        # LLM: World prompt
        world_prompt = engine.get_world_prompt()
        if world_prompt:
            narration = llm_call("mimir",
                f"You are narrating a political fantasy. The road ahead: "
                f"{world_prompt[:200]}. Describe it in 1 sentence.",
                max_tokens=40)
            console.print(f"    Mimir: {narration}")

        # Council dilemma
        dilemma = engine.get_council_dilemma()
        if dilemma:
            console.print(f"    Dilemma: {dilemma.get('prompt', 'N/A')[:100]}")
            # AI "votes" — simulate choosing crown vs crew
            choice = "crown" if day % 2 == 0 else "crew"
            console.print(f"    AI Vote: {choice}")

        # Allegiance
        side = "crown" if day % 2 == 0 else "crew"
        engine.declare_allegiance(side)
        prompt = engine.get_prompt(side)
        console.print(f"    Allegiance: {side} — {str(prompt)[:80]}")

        # Rest
        engine.trigger_long_rest()

    # Final report
    subsection("Legacy Report")
    legacy = engine.generate_legacy_report()
    console.print(f"    {legacy[:200]}")

    # LLM summary
    summary = llm_call("mimir",
        f"Summarize this political journey: started as neutral, "
        f"ended at sway {engine.sway} ({engine.get_alignment()}). "
        f"One sentence, dramatic tone.",
        max_tokens=40)
    console.print(f"    Mimir: {summary}")

    report_card("Crown & Crew", [
        ("Morning Events", f"{len(MORNING_EVENTS)} sway-biased encounters"),
        ("Council Dilemmas", f"{len(COUNCIL_DILEMMAS)} with crown/crew options"),
        ("Sway System", "7-tier alignment (-3 to +3)"),
        ("Narrative DNA", "5 tags (BLOOD/GUILE/HEARTH/SILENCE/DEFIANCE)"),
        ("Political Gravity", "Vote weight scales with conviction"),
        ("Rest Mechanics", "Long/short/skip with sway effects"),
        ("Legacy Report", "Campaign summary generation"),
        ("Save/Load", "Full arc persistence"),
        ("World Prompts", "Environment description per day"),
        ("Campfire Prompts", "Reflective moments"),
    ], [
        ("AI Companion", "No autopilot agent — purely human-driven"),
        ("DM NPC Generator", "No procedural NPC system (uses static names)"),
        ("DM Dice Roller", "No dice mechanic — narrative only"),
        ("Encounter Generator", "No combat encounters — political only"),
        ("Map/Spatial System", "No map — linear day progression"),
        ("Trap/Hazard Generator", "Not applicable to political gameplay"),
        ("LLM-Powered Dilemma Gen", "Dilemmas are static, not LLM-generated"),
        ("Consequence Engine", "Votes don't affect future dilemma pool"),
    ])

    return True


# ═════════════════════════════════════════════════════════════════════
# ENGINE 3: BLADES IN THE DARK — FITD heist
# ═════════════════════════════════════════════════════════════════════

def test_bitd():
    section("ENGINE 3: BLADES IN THE DARK — Heist Simulation")

    from codex.games.bitd import BitDEngine, BitDCharacter
    from codex.core.services.fitd_engine import (
        FITDActionRoll, Position, Effect, StressClock, FactionClock,
    )
    from codex.core.dm_tools import roll_dice

    engine = BitDEngine()
    # Create crew
    engine.create_character("Croaker", playbook="Lurk", heritage="Skovlan")
    engine.add_to_party(BitDCharacter(name="Sawtooth", playbook="Cutter", heritage="Akoros"))
    engine.add_to_party(BitDCharacter(name="Whisper", playbook="Spider", heritage="Tycheros"))

    console.print(f"  Crew: {engine.crew_name or 'The Unnamed'} ({len(engine.party)} scoundrels)")
    for c in engine.party:
        console.print(f"    {c.name} ({c.playbook}) — Heritage: {c.heritage}")

    # Simulate a 3-phase score
    for phase_num, phase in enumerate(["Engagement", "Execution", "Aftermath"], 1):
        subsection(f"Phase {phase_num}: {phase}")

        if phase == "Engagement":
            # Engagement roll
            roll = FITDActionRoll(dice_count=2, position=Position.RISKY)
            result = roll.roll()
            console.print(f"    Engagement Roll: {result.all_dice} → {result.outcome}")
            console.print(f"    Position: {result.position.value} | Effect: {result.effect.value}")

            # LLM: Describe the score
            narration = llm_call("mimir",
                f"You are narrating a Blades in the Dark heist. "
                f"The engagement roll was '{result.outcome}'. "
                f"Describe how the crew enters the score in 1 sentence. Dark Victorian tone.",
                max_tokens=50)
            console.print(f"    Mimir: {narration}")

        elif phase == "Execution":
            # Each crew member makes an action
            actions = [
                ("Croaker", "prowl", Position.RISKY),
                ("Sawtooth", "skirmish", Position.DESPERATE),
                ("Whisper", "consort", Position.CONTROLLED),
            ]
            for char_name, action, position in actions:
                char = next(c for c in engine.party if c.name == char_name)
                dots = getattr(char, action, 0)
                # Give them some dots for the test
                setattr(char, action, max(dots, 2))
                result = engine.roll_action(char, action=action, position=position)
                console.print(f"    {char_name} — {action} ({position.value}): "
                              f"{result.all_dice} → {result.outcome}")

                # Stress on mixed/failure
                if result.outcome in ("failure", "mixed"):
                    clock = engine.stress_clocks.get(char_name)
                    if clock:
                        stress_cost = 2 if result.outcome == "failure" else 1
                        clock.push(stress_cost)
                        console.print(f"    → Stress: {clock.current_stress}/{clock.max_stress}")

            # LLM: Narrate the execution
            narration = llm_call("llama3.2:1b",
                f"Blades in the Dark heist: Croaker prowls the rooftops, "
                f"Sawtooth fights a guard, Whisper charms the merchant. "
                f"Narrate in 1 sentence, gritty Victorian noir.",
                max_tokens=40)
            console.print(f"    Narration: {narration}")

        elif phase == "Aftermath":
            # Entanglement
            entanglement = engine.handle_command("entanglement")
            console.print(f"    {entanglement}")

            # Heat
            engine.heat += 2
            console.print(f"    Heat raised to {engine.heat}")

            # Crew status
            status = engine.handle_command("crew_status")
            console.print(f"    {status}")

    report_card("Blades in the Dark (FITD)", [
        ("Action Rolls", "d6 pool with position/effect"),
        ("Stress/Trauma", "StressClock with 8 trauma types"),
        ("Faction Clocks", "4/6/8 segment progress tracking"),
        ("Crew Resources", "Heat, coin, rep, turf, wanted"),
        ("Entanglement Roll", "Post-score complication generator"),
        ("Character Playbooks", "7 playbooks with action dots"),
        ("Save/Load", "Full state persistence"),
        ("Command Dispatcher", "handle_command() for crew/action/party"),
    ], [
        ("AI Companion", "No autopilot — no heuristic decision engine"),
        ("DM Score Generator", "No procedural heist/score generation"),
        ("DM NPC Generator", "No FITD-specific NPC tables"),
        ("DM Complication Table", "Entanglement is 1 table, needs more"),
        ("Map/Spatial System", "No district map, no turf visualization"),
        ("LLM Score Narration", "No structured narration pipeline"),
        ("Downtime Actions", "No vice/recover/project management"),
        ("Faction Turn", "No automated faction clock advancement"),
        ("Clock Display", "No Rich terminal clock visualization"),
        ("Resistance Roll", "StressClock.resist() exists but not wired to DM"),
    ])

    return True


# ═════════════════════════════════════════════════════════════════════
# ENGINE 4: D&D 5E — Classic dungeon delve
# ═════════════════════════════════════════════════════════════════════

def test_dnd5e():
    section("ENGINE 4: D&D 5E — Dungeon Delve")

    from codex.games.dnd5e import DnD5eEngine
    from codex.core.dm_tools import roll_dice, generate_npc, generate_trap

    engine = DnD5eEngine()
    char = engine.create_character("Aldric", character_class="fighter",
                                    race="Human", strength=16, dexterity=14,
                                    constitution=14, wisdom=12)
    console.print(f"  Character: {char.name} ({char.race} {char.character_class})")
    console.print(f"  HP: {char.current_hp}/{char.max_hp} | AC: {char.armor_class}")
    console.print(f"  STR:{char.strength} DEX:{char.dexterity} CON:{char.constitution} "
                  f"INT:{char.intelligence} WIS:{char.wisdom} CHA:{char.charisma}")

    # Generate dungeon
    dungeon_info = engine.generate_dungeon(depth=3, seed=42)
    console.print(f"  Dungeon: {dungeon_info['total_rooms']} rooms (seed {dungeon_info['seed']})")

    # 3-room delve
    for turn in range(1, 4):
        room = engine.get_current_room()
        pop = engine.populated_rooms.get(engine.current_room_id)
        content = pop.content if pop else {}

        subsection(f"Room {turn} (ID:{engine.current_room_id}) | HP: {char.current_hp}/{char.max_hp}")

        if content.get("description"):
            console.print(f"    Desc: {content['description']}")

        # Enemies
        enemies = content.get("enemies", [])
        for e in enemies:
            console.print(f"    Enemy: {e['name']} (HP:{e['hp']} ATK:{e.get('attack', '?')})")

        if enemies:
            # DM: Player rolls attack
            check = engine.roll_check(ability="strength", proficiency=True, dc=enemies[0].get("defense", 12))
            console.print(f"    Attack Check: d20={check['roll']} + {check['modifier']} + {check['proficiency_bonus']} "
                          f"= {check['total']} vs DC {check.get('dc', '?')} → {'HIT' if check.get('success') else 'MISS'}")
            if check.get("critical"):
                console.print(f"    CRITICAL HIT!")

            # LLM narrate
            narration = llm_call("mimir",
                f"D&D combat narration. {char.name} the {char.character_class} "
                f"{'strikes' if check.get('success') else 'misses'} {enemies[0]['name']}. "
                f"One sentence, heroic fantasy tone.",
                max_tokens=40)
            console.print(f"    Mimir: {narration}")

        # Loot
        for item in content.get("loot", []):
            console.print(f"    Loot: {item['name']} (T{item.get('tier', '?')})")

        # Hazards
        for h in content.get("hazards", []):
            console.print(f"    Hazard: {h['name']}")
            # DEX save
            save = engine.roll_check(ability="dexterity", dc=14)
            console.print(f"    DEX Save: {save['total']} vs DC 14 → {'PASS' if save.get('success') else 'FAIL'}")

        # Move to next room
        exits = engine.get_cardinal_exits()
        if exits:
            target = exits[0]
            engine.move_to_room(target["id"])
            console.print(f"    → Moving {target['direction']} to room {target['id']}")

    report_card("D&D 5th Edition", [
        ("Dungeon Generation", "BSP via CodexMapEngine + DnD5eAdapter"),
        ("d20 Resolution", "roll_check() with ability mods + proficiency"),
        ("Enemy Content Tables", "Tiered 1-4 (Goblin→Dragon)"),
        ("Loot Content Tables", "Tiered 1-4 (Potion→Vorpal Sword)"),
        ("Hazard Content Tables", "Tiered 1-4 (Pit Trap→Sphere of Annihilation)"),
        ("Character Model", "6 ability scores, AC, HP, class hit die"),
        ("Trait Resolver", "DnD5eTraitResolver — skill checks by ability"),
        ("Save/Load", "Full state + dungeon persistence"),
        ("Navigation API", "Cardinal exits, move_to_room, grid movement"),
        ("NPC Generator", "Shared DM tools (archetype + stat weighting)"),
    ], [
        ("AI Companion", "No autopilot agent for D&D 5e"),
        ("Initiative Tracker", "No turn-order system"),
        ("Spell System", "No spell slots, spell lists, or concentration"),
        ("Condition Tracker", "No poisoned/stunned/etc. status effects"),
        ("Rest Mechanics", "No short/long rest HP recovery"),
        ("Death Saves", "No 5e death saving throw system"),
        ("XP / Leveling", "No experience or level-up progression"),
        ("Monster Manual Lookup", "Static pool, no SRD monster stat blocks"),
        ("Multiclass Support", "Single class only"),
        ("Encounter Balance (CR)", "No CR-based encounter balancing"),
    ])

    return True


# ═════════════════════════════════════════════════════════════════════
# ENGINE 5: COSMERE — Roshar expedition
# ═════════════════════════════════════════════════════════════════════

def test_cosmere():
    section("ENGINE 5: COSMERE RPG — Roshar Expedition")

    from codex.games.stc import CosmereEngine, CosmereCharacter, RADIANT_ORDERS

    engine = CosmereEngine()
    char = engine.create_character("Kaladin", heritage="Alethi",
                                    order="windrunner",
                                    strength=14, speed=16, intellect=12)
    console.print(f"  Character: {char.name} ({char.heritage} {char.order.title()})")
    console.print(f"  HP: {char.current_hp}/{char.max_hp} | Defense: {char.defense} | Focus: {char.focus}")
    console.print(f"  STR:{char.strength} SPD:{char.speed} INT:{char.intellect}")
    console.print(f"  Surges: {char.get_surges()}")
    console.print(f"  Ideal: \"{char.get_ideal()}\"")

    # Generate dungeon
    dungeon_info = engine.generate_dungeon(depth=3, seed=42)
    console.print(f"  Dungeon: {dungeon_info['total_rooms']} rooms (Shattered Plains)")

    # 3-room expedition
    for turn in range(1, 4):
        pop = engine.populated_rooms.get(engine.current_room_id)
        content = pop.content if pop else {}

        subsection(f"Room {turn} (ID:{engine.current_room_id}) | HP: {char.current_hp}/{char.max_hp} | Focus: {char.focus}")

        if content.get("description"):
            console.print(f"    {content['description']}")

        enemies = content.get("enemies", [])
        for e in enemies:
            console.print(f"    Enemy: {e['name']} (HP:{e['hp']})")

        if enemies:
            # Combat check with focus spend
            check = engine.roll_check(attribute="strength", dc=enemies[0].get("defense", 12),
                                       focus_spend=1 if char.focus > 0 else 0)
            console.print(f"    Attack: d20={check['roll']} + {check['modifier']} "
                          f"(+{check['focus_spent']} focus) = {check['total']} "
                          f"→ {'HIT' if check.get('success') else 'MISS'}")

            # Surge use
            surges = char.get_surges()
            if surges and char.focus > 0:
                console.print(f"    Surge available: {surges[0]}")
                # Use CosmereTraitResolver
                from codex.games.stc import CosmereTraitResolver
                resolver = CosmereTraitResolver()
                surge_result = resolver.resolve_trait(surges[0], {
                    "character": char, "dc": 12, "focus_spend": 1,
                })
                console.print(f"    Surge Check ({surges[0]}): {surge_result['total']} "
                              f"→ {'SUCCESS' if surge_result.get('success') else 'FAIL'}")

            # LLM narrate
            narration = llm_call("mimir",
                f"Cosmere/Stormlight narration. {char.name} the {char.order.title()} "
                f"fights {enemies[0]['name']} in the Shattered Plains. "
                f"Mention Stormlight or surgebinding. One sentence.",
                max_tokens=50)
            console.print(f"    Mimir: {narration}")

        for item in content.get("loot", []):
            console.print(f"    Loot: {item['name']}")

        # Move
        exits = engine.get_cardinal_exits()
        if exits:
            engine.move_to_room(exits[0]["id"])
            console.print(f"    → Moving {exits[0]['direction']}")

    report_card("Cosmere RPG (Stormlight)", [
        ("Dungeon Generation", "BSP via CodexMapEngine + CosmereAdapter"),
        ("d20 Resolution", "roll_check() with attribute mods + focus spend"),
        ("Radiant Orders", f"{len(RADIANT_ORDERS)} orders with surge pairs"),
        ("Surge System", "CosmereTraitResolver — surge checks by attribute"),
        ("Focus/Stormlight", "Spendable resource for check bonuses"),
        ("Enemy Content Tables", "Tiered 1-4 (Cremling→Thunderclast)"),
        ("Loot Content Tables", "Tiered 1-4 (Chip→Honorblade)"),
        ("Hazard Content Tables", "Tiered 1-4 (Highstorm→Odium's Influence)"),
        ("Character Model", "3 attributes, heritage, order, defense, focus"),
        ("Save/Load", "Full state + dungeon persistence"),
        ("Navigation API", "Cardinal exits, move_to_room, grid movement"),
    ], [
        ("AI Companion", "No autopilot agent for Cosmere"),
        ("Stormlight Recovery", "No highstorm/rest recharge mechanic"),
        ("Ideal Progression", "No narrative oath advancement system"),
        ("Spren Bond", "No spren relationship/dialogue system"),
        ("Shardplate/Shardblade", "No equip/durability system for Shards"),
        ("NPC Generator", "No Rosharan-themed NPC tables"),
        ("Encounter Balance", "No threat-level encounter scaling"),
        ("Investiture System", "Focus exists but no allomancy/feruchemy"),
    ])

    return True


# ═════════════════════════════════════════════════════════════════════
# MAIN — Run all engines + print gap analysis
# ═════════════════════════════════════════════════════════════════════

def main():
    if HAS_RICH:
        console.print(Panel(
            "[bold]DM Live Test — Multi-Engine Diagnostic[/bold]\n"
            "Exercises every game engine through DM→Companion loops\n"
            "with real LLM calls (Mimir + llama3.2:1b).\n\n"
            "Surfaces tool gaps and missing DM View capabilities.",
            title="[bold red]CODEX DM DIAGNOSTIC[/bold red]",
            border_style="red",
        ))
    else:
        console.print("CODEX DM DIAGNOSTIC — Multi-Engine with Real LLM")

    start = time.time()
    results = {}

    for name, fn in [
        ("Burnwillow", test_burnwillow),
        ("Crown & Crew", test_crown),
        ("Blades in the Dark", test_bitd),
        ("D&D 5e", test_dnd5e),
        ("Cosmere", test_cosmere),
    ]:
        try:
            fn()
            results[name] = "PASS"
        except Exception as e:
            console.print(f"\n  [bold red]ERROR in {name}: {e}[/bold red]" if HAS_RICH
                          else f"\n  ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = f"FAIL: {e}"

    # Final summary
    elapsed = time.time() - start
    section("FINAL SUMMARY")

    if HAS_RICH:
        table = Table(title="Engine Results", border_style="bold")
        table.add_column("Engine", style="bold")
        table.add_column("Result")
        for eng, result in results.items():
            color = "green" if result == "PASS" else "red"
            table.add_row(eng, f"[{color}]{result}[/{color}]")
        table.add_row("", "")
        table.add_row("Total Time", f"{elapsed:.1f}s")
        table.add_row("LLM Models Used", "mimir, llama3.2:1b")
        console.print(table)
    else:
        for eng, result in results.items():
            console.print(f"  {eng}: {result}")
        console.print(f"\n  Time: {elapsed:.1f}s")

    # Cross-engine gap summary
    section("CROSS-ENGINE GAP ANALYSIS")
    gaps = [
        ("AI Companion System", "Burnwillow only", "FITD, D&D 5e, Cosmere, Crown all lack autopilot agents"),
        ("Procedural Dungeon Gen", "Burnwillow, D&D 5e, Cosmere", "FITD and Crown lack spatial maps entirely"),
        ("LLM Narration Pipeline", "Ad-hoc per engine", "No unified narration API across systems"),
        ("DM NPC Generator", "Shared dm_tools.py", "D&D-flavored only; no FITD/Cosmere NPC tables"),
        ("DM Encounter Generator", "Burnwillow-centric", "generate_encounter() only handles BURNWILLOW well"),
        ("Initiative/Turn Tracker", "None", "No system has structured turn order management"),
        ("Condition/Status Effects", "None", "No persistent buff/debuff tracking on any engine"),
        ("Downtime/Rest System", "Crown only (rest)", "No FITD downtime, no 5e short/long rest"),
        ("Progression System", "None", "No XP, leveling, or advancement in any engine"),
        ("DM View Terminal UI", "None", "No dedicated DM panel/dashboard in Rich"),
    ]

    if HAS_RICH:
        table = Table(title="Universal DM Tool Gaps", border_style="red", box=box.DOUBLE)
        table.add_column("Tool/Feature", style="bold")
        table.add_column("Current State", style="yellow")
        table.add_column("Gap Description")
        for feature, state, desc in gaps:
            table.add_row(feature, state, desc)
        console.print(table)
    else:
        for feature, state, desc in gaps:
            console.print(f"  [{state}] {feature}: {desc}")

    console.print("\n[bold green]DM Diagnostic complete.[/bold green]" if HAS_RICH
                  else "\nDM Diagnostic complete.")


if __name__ == "__main__":
    main()

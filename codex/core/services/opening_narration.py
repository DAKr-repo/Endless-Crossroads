"""
codex.core.services.opening_narration
======================================

Assembles opening narration for game sessions using module data,
GM profiles, and optional Mimir enhancement.

The authored ``read_aloud`` text from module hook.json is the anchor.
Mimir adds 1-2 atmospheric sentences using the system's GM profile
voice. Static ``read_aloud`` is always the fallback if Mimir is
unavailable or thermally throttled.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

_GM_PROFILES_FILE = Path(__file__).resolve().parent / "system_gm_profiles.json"

# Cache loaded profiles
_gm_profiles_cache: Optional[dict] = None


def _load_gm_profiles() -> dict:
    """Load and cache GM profiles from JSON."""
    global _gm_profiles_cache
    if _gm_profiles_cache is not None:
        return _gm_profiles_cache
    try:
        if _GM_PROFILES_FILE.exists():
            _gm_profiles_cache = json.loads(_GM_PROFILES_FILE.read_text())
            return _gm_profiles_cache
    except Exception:
        pass
    _gm_profiles_cache = {}
    return _gm_profiles_cache


def get_gm_title(system_id: str) -> str:
    """Return the GM title for a system (e.g. 'Lightkeeper', 'Dungeon Master')."""
    profiles = _load_gm_profiles()
    profile = profiles.get(system_id, {})
    return profile.get("gm_title", "Game Master")


@dataclass
class OpeningNarration:
    """Container for assembled opening narration."""

    read_aloud: str = ""      # Authored narration (always present if module loaded)
    atmosphere: str = ""      # Mimir-generated atmospheric preamble (may be empty)
    gm_title: str = "Game Master"  # System-specific GM title
    scene_title: str = ""     # From hook.json metadata
    has_module: bool = False   # True if module data was available


def generate_opening_narration(
    system_id: str,
    scene_data: Any = None,
    session_type: str = "campaign",
    module_name: str = "",
    gm_profile: str = "",
    dm_influence: Optional[dict] = None,
    mimir_fn: Optional[Callable] = None,
    thermal_ok: bool = True,
) -> OpeningNarration:
    """Generate opening narration from module data with optional Mimir enhancement.

    Args:
        system_id: Engine system identifier (e.g. "candela", "dnd5e").
        scene_data: SceneData from the module's hook.json (or None for freeform).
        session_type: Session type ("campaign", "one_shot", etc.).
        module_name: Display name of the loaded module.
        gm_profile: GM profile prompt string from cortex.
        dm_influence: DM influence dials dict.
        mimir_fn: Optional callable(prompt, context) -> str for LLM narration.
        thermal_ok: Whether thermal state allows Mimir calls.

    Returns:
        OpeningNarration with read_aloud and optional atmosphere.
    """
    gm_title = get_gm_title(system_id)
    narration = OpeningNarration(gm_title=gm_title)

    # Extract read_aloud from scene data
    read_aloud = ""
    if scene_data is not None:
        read_aloud = getattr(scene_data, "read_aloud", "") or ""
        if not read_aloud:
            # Fall back to description if no read_aloud
            read_aloud = getattr(scene_data, "description", "") or ""
        narration.has_module = bool(read_aloud)
        narration.read_aloud = read_aloud

    # If no module data, use generic session hooks
    if not narration.read_aloud:
        narration.read_aloud = _generate_fallback_hook(system_id, session_type)
        narration.has_module = False

    # Mimir atmospheric enhancement (only for opening, not transitions)
    if thermal_ok and mimir_fn and narration.read_aloud:
        narration.atmosphere = _generate_atmosphere(
            system_id=system_id,
            gm_title=gm_title,
            read_aloud=narration.read_aloud,
            gm_profile=gm_profile,
            dm_influence=dm_influence,
            mimir_fn=mimir_fn,
        )

    narration.scene_title = module_name or ""
    return narration


def _generate_atmosphere(
    system_id: str,
    gm_title: str,
    read_aloud: str,
    gm_profile: str = "",
    dm_influence: Optional[dict] = None,
    mimir_fn: Optional[Callable] = None,
) -> str:
    """Generate 1-2 atmospheric sentences via Mimir to precede the read_aloud."""
    if not mimir_fn:
        return ""

    # Build a short prompt — must stay under ~400 tokens total
    tone_hint = ""
    if dm_influence:
        tone_val = dm_influence.get("tone", 0.5)
        if tone_val < 0.3:
            tone_hint = "Tone: grim and foreboding. "
        elif tone_val > 0.7:
            tone_hint = "Tone: wondrous and inviting. "

    # Use first 200 chars of read_aloud as context
    excerpt = read_aloud[:200].rstrip()
    if len(read_aloud) > 200:
        excerpt += "..."

    prompt = (
        f"You are the {gm_title}. {tone_hint}"
        f"Write 1-2 atmospheric sentences to set the scene before this briefing. "
        f"Use sensory details — sounds, smells, light. Stay in character. "
        f"Do not repeat the briefing content.\n\n"
        f"BRIEFING EXCERPT: {excerpt}"
    )

    try:
        result = mimir_fn(prompt)
        if result and isinstance(result, str) and len(result.strip()) > 15:
            # Validate — reject AI meta-commentary
            text = result.strip()
            reject_phrases = [
                "as an ai", "i cannot", "i'm an ai", "language model",
                "i don't have", "certainly!", "of course!",
            ]
            if any(p in text.lower() for p in reject_phrases):
                return ""
            # Cap at 200 chars to keep it concise
            if len(text) > 200:
                # Try to cut at sentence boundary
                last_period = text[:200].rfind(".")
                if last_period > 80:
                    text = text[: last_period + 1]
                else:
                    text = text[:200].rstrip() + "..."
            return text
    except Exception:
        pass

    return ""


def _generate_fallback_hook(system_id: str, session_type: str) -> str:
    """Generate a system-aware fallback hook when no module is loaded."""
    profiles = _load_gm_profiles()
    profile = profiles.get(system_id, {})
    tone = profile.get("tone", "")

    # System-specific freeform hooks
    _SYSTEM_HOOKS = {
        "candela": "The gaslight flickers in your chapter house. A sealed envelope waits on the table, bearing the wax seal of Candela Obscura. Your Lightkeeper has an assignment.",
        "bitd": "The fog rolls thick through the streets of Doskvol tonight. Your crew gathers in the lair, counting coin and nursing grudges. Word is, there's a score worth taking.",
        "sav": "The ship hums beneath your boots. Another sector, another job. The comms crackle with an encrypted transmission — someone needs a crew, and they're willing to pay.",
        "bob": "Dawn breaks grey over the Legion's camp. The scouts returned in the night, faces drawn. The Marshal calls a briefing. The retreat continues.",
        "cbrpnk": "Neon bleeds through the rain-streaked windows of the safe house. The burner phone buzzes once. A job. The kind that pays enough to disappear — or get disappeared.",
        "dnd5e": "The road stretches before you, winding through lands both wondrous and perilous. Adventure calls — and the brave answer.",
        "stc": "The highstorm passed in the night, leaving the air clean and sharp with the scent of ozone. Stormlight pools in the gemstones at your belt. A new day on Roshar begins.",
        "burnwillow": "The Grove darkens. Spore-light flickers in the tunnels below. Your torches won't last forever. The descent begins.",
        "crown": "Day one. The supplies are counted, the alliances are fragile, and the road ahead is long. Who leads? Who follows? Who gets left behind?",
        "ashburn": "The bell tower chimes midnight across the Ashburn High campus. The halls are empty — or they should be. Something scrapes behind the locked door of the east wing.",
    }

    hook = _SYSTEM_HOOKS.get(system_id, "")
    if not hook:
        # Generic fallback
        try:
            from codex.core.session_frame import generate_opening_hook
            hook = generate_opening_hook(session_type=session_type)
        except Exception:
            hook = "The world awaits. What do you do?"

    return hook


def generate_resume_narration(
    system_id: str,
    engine: Any = None,
    scene_data: Any = None,
    mimir_fn: Optional[Callable] = None,
    thermal_ok: bool = True,
) -> OpeningNarration:
    """Generate a contextual 'previously on...' opening for resumed sessions.

    Uses engine state (assignment phase, clues, marks, memory shards) to
    build a session-specific opening instead of repeating the hook cold open.

    Args:
        system_id: Engine system identifier.
        engine: The game engine with current state.
        scene_data: Current scene's SceneData (not the hook — the actual current scene).
        mimir_fn: Optional LLM callable for narrative generation.
        thermal_ok: Whether thermal state allows Mimir calls.

    Returns:
        OpeningNarration with contextual read_aloud.
    """
    gm_title = get_gm_title(system_id)
    narration = OpeningNarration(gm_title=gm_title, has_module=True)

    # Build state summary from engine — system-aware extraction
    state_parts = _extract_engine_state(system_id, engine)

    # Current scene read_aloud (for the scene they're actually in, not the hook)
    current_ra = ""
    if scene_data:
        current_ra = getattr(scene_data, 'read_aloud', '') or ''

    # Try Mimir for a contextual recap
    if thermal_ok and mimir_fn and state_parts:
        state_summary = ". ".join(state_parts)
        prompt = (
            f"You are the {gm_title}. The players are resuming a session. "
            f"Write 2-3 sentences reminding them where they left off and "
            f"setting the mood to continue. Stay in character. No meta-commentary.\n\n"
            f"STATE: {state_summary}"
        )
        try:
            result = mimir_fn(prompt)
            if result and isinstance(result, str) and len(result.strip()) > 20:
                text = result.strip()
                reject = ["as an ai", "i cannot", "language model", "certainly!"]
                if not any(r in text.lower() for r in reject):
                    narration.read_aloud = text
                    # If we also have scene read_aloud, append it
                    if current_ra:
                        narration.atmosphere = text
                        narration.read_aloud = current_ra
                    return narration
        except Exception:
            pass

    # Fallback: static recap from state
    if state_parts:
        fallback_parts = [f"[bold]Session Resume[/bold]"]
        for sp in state_parts[:4]:
            fallback_parts.append(f"  {sp}")
        if current_ra:
            fallback_parts.append("")
            fallback_parts.append(current_ra)
        narration.read_aloud = "\n".join(fallback_parts)
    elif current_ra:
        narration.read_aloud = current_ra
    else:
        narration.read_aloud = _generate_fallback_hook(system_id, "campaign")

    return narration


def is_first_session(engine: Any = None, manifest: Optional[dict] = None) -> bool:
    """Determine if this is the first session of a campaign.

    Checks assignment count, memory shards, and session history.
    """
    if engine:
        if getattr(engine, 'assignments_completed', 0) > 0:
            return False
        shards = getattr(engine, 'memory_shards', [])
        if len(shards) > 2:  # More than the initial synthesis shards
            return False
        # Check if assignment tracker has progressed past hook
        tracker = getattr(engine, '_assignment_tracker', None)
        if tracker:
            phase = getattr(tracker, 'current_phase', '')
            if phase and phase not in ('', 'hook'):
                return False
    if manifest:
        if manifest.get("session_count", 0) > 1:
            return False
    return True


def _extract_engine_state(system_id: str, engine: Any) -> list:
    """Extract narrative-relevant state from engine, keyed by system type.

    Returns a list of short state description strings for Mimir context.
    """
    parts = []
    if not engine:
        return parts

    # ── Shared: party names and conditions ──
    party = getattr(engine, 'party', [])
    if party:
        names = [getattr(p, 'name', '?') for p in party[:4]]
        parts.append(f"Party: {', '.join(names)}")

    # ── FITD family (Candela, BitD, SaV, BoB, CBR+PNK) ──
    # Stress / faction clocks
    stress_total = 0
    for p in party:
        stress_total += getattr(p, 'stress', 0)
    if stress_total:
        parts.append(f"Total stress: {stress_total}")

    if system_id == "candela":
        # Circle, assignment, investigation, phenomena
        circle = getattr(engine, 'circle_name', '')
        if circle:
            parts.append(f"Circle: {circle}")
        tracker = getattr(engine, '_assignment_tracker', None)
        if tracker and getattr(tracker, 'assignment_name', ''):
            phase = (getattr(tracker, 'current_phase', '') or 'unknown').upper()
            parts.append(f"Assignment: {tracker.assignment_name}, Phase: {phase}")
        inv_mgr = getattr(engine, '_investigation_mgr', None)
        if inv_mgr and getattr(inv_mgr, 'active_case', None):
            case = inv_mgr.active_case
            parts.append(f"Clues: {case.clues_found}/{case.clues_needed}, Danger: {case.danger_level}/5")
        # Body/Brain/Bleed marks
        for p in party:
            marks = getattr(p, 'body', 0) + getattr(p, 'brain', 0) + getattr(p, 'bleed', 0)
            if marks > 0:
                parts.append(f"{p.name}: {marks} marks")

    elif system_id == "bitd":
        # Crew, heat, wanted, rep, turf
        crew = getattr(engine, 'crew_name', '')
        if crew:
            parts.append(f"Crew: {crew} ({getattr(engine, 'crew_type', '')})")
        heat = getattr(engine, 'heat', 0)
        wanted = getattr(engine, 'wanted_level', 0)
        if heat or wanted:
            parts.append(f"Heat: {heat}, Wanted: {wanted}")
        rep = getattr(engine, 'rep', 0)
        coin = getattr(engine, 'coin', 0)
        if rep or coin:
            parts.append(f"Rep: {rep}, Coin: {coin}")

    elif system_id == "sav":
        # Ship, heat, gambits
        ship = getattr(engine, 'ship_name', '')
        if ship:
            parts.append(f"Ship: {ship} ({getattr(engine, 'ship_class', '')})")
        heat = getattr(engine, 'heat', 0)
        if heat:
            parts.append(f"Wanted: {heat}")

    elif system_id == "bob":
        # Legion state: supply, morale, pressure
        legion = getattr(engine, 'legion', None)
        if legion:
            parts.append(
                f"Supply: {getattr(legion, 'supply', '?')}, "
                f"Morale: {getattr(legion, 'morale', '?')}, "
                f"Pressure: {getattr(legion, 'pressure', '?')}"
            )
        chosen = getattr(engine, 'chosen', '')
        if chosen:
            parts.append(f"Chosen: {chosen}")
        phase = getattr(engine, 'campaign_phase', '')
        if phase:
            parts.append(f"Campaign phase: {phase}")
        fallen = getattr(engine, 'fallen_legionnaires', [])
        if fallen:
            parts.append(f"Fallen: {len(fallen)} legionnaires lost")

    elif system_id == "cbrpnk":
        # Heat, glitch die
        heat = getattr(engine, 'heat', 0)
        glitch = getattr(engine, 'glitch_die', 0)
        if heat or glitch:
            parts.append(f"Corp heat: {heat}, Glitch: {glitch}")

    # ── D&D 5e / STC (spatial systems) ──
    elif system_id in ("dnd5e", "stc"):
        for p in party:
            hp = getattr(p, 'current_hp', 0)
            max_hp = getattr(p, 'max_hp', 0)
            lvl = getattr(p, 'level', 1)
            if max_hp:
                parts.append(f"{p.name}: HP {hp}/{max_hp}, Level {lvl}")
        visited = getattr(engine, 'visited_rooms', set())
        if visited:
            parts.append(f"Rooms explored: {len(visited)}")
        # STC-specific: ideal level
        if system_id == "stc":
            for p in party:
                ideal = getattr(p, 'ideal_level', 0)
                order = getattr(p, 'order', '')
                if order:
                    parts.append(f"{p.name}: {order} (Ideal {ideal})")

    # ── Burnwillow (roguelike) ──
    elif system_id == "burnwillow":
        for p in party:
            hp = getattr(p, 'current_hp', 0)
            max_hp = getattr(p, 'max_hp', 0)
            if max_hp:
                parts.append(f"{p.name}: HP {hp}/{max_hp}")
        doom = getattr(engine, 'doom_clock', None)
        if doom:
            parts.append(f"Doom: {getattr(doom, 'current', 0)}/{getattr(doom, 'max_val', 20)}")

    # ── Crown & Crew ──
    elif system_id == "crown":
        sway = getattr(engine, 'sway', 0)
        day = getattr(engine, 'day_counter', 1)
        tag = getattr(engine, 'dominant_tag', '')
        parts.append(f"Day {day}, Sway: {sway}")
        if tag:
            parts.append(f"Dominant theme: {tag}")

    # ── Memory shards (all systems) ──
    shards = getattr(engine, 'memory_shards', [])
    if shards:
        for s in shards[-3:]:
            text = s.get('text', '') if isinstance(s, dict) else str(s)
            if text:
                parts.append(f"Event: {text[:80]}")

    return parts


def format_read_aloud_panel(narration: OpeningNarration) -> str:
    """Format an OpeningNarration for display in a Rich Panel.

    Returns Rich-formatted string with atmosphere (if any) followed by
    the read_aloud text.
    """
    parts = []

    if narration.atmosphere:
        parts.append(f"[italic dim]{narration.atmosphere}[/italic dim]")
        parts.append("")  # blank line separator

    if narration.read_aloud:
        parts.append(narration.read_aloud)

    return "\n".join(parts) if parts else ""


def format_scene_read_aloud(scene_data: Any) -> Optional[str]:
    """Extract and format read_aloud from SceneData for scene transitions.

    No Mimir enhancement — returns raw authored text for snappy transitions.

    Returns:
        Formatted read_aloud string, or None if empty.
    """
    read_aloud = getattr(scene_data, "read_aloud", "") or ""
    if not read_aloud:
        return None
    return read_aloud

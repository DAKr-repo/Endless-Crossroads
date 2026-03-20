"""
Companion Maps — Cross-system archetype-to-class mapping & narration.
====================================================================

WO-V61.0 Track D: Maps personality archetypes (vanguard, scholar,
scavenger, healer) to system-specific character classes/playbooks.
Also provides narrated decision templates for companion actions.

WO-V66.0: Replaced hardcoded 1:1 COMPANION_CLASS_MAP with weighted
ARCHETYPE_WEIGHTS covering ALL classes per system. Added
create_companion_character() factory for full PC companions.
"""

from typing import Any, Dict, List, Optional, Tuple
import random

# Legacy 1:1 map — kept for backwards compat with code that reads it directly
COMPANION_CLASS_MAP: Dict[str, dict] = {
    "dnd5e": {
        "vanguard": {"class": "Fighter", "background": "Soldier"},
        "scholar": {"class": "Wizard", "background": "Sage"},
        "scavenger": {"class": "Rogue", "background": "Criminal"},
        "healer": {"class": "Cleric", "background": "Acolyte"},
    },
    "stc": {
        "vanguard": {"order": "Windrunner", "role": "front-line"},
        "scholar": {"order": "Truthwatcher", "role": "support"},
        "scavenger": {"order": "Lightweaver", "role": "utility"},
        "healer": {"order": "Edgedancer", "role": "healer"},
    },
    "bitd": {
        "vanguard": "Cutter",
        "scholar": "Whisper",
        "scavenger": "Lurk",
        "healer": "Leech",
    },
    "sav": {
        "vanguard": "Muscle",
        "scholar": "Mystic",
        "scavenger": "Scoundrel",
        "healer": "Mechanic",
    },
    "bob": {
        "vanguard": "Heavy",
        "scholar": "Medic",
        "scavenger": "Scout",
        "healer": "Officer",
    },
    "cbrpnk": {
        "vanguard": "Punk",
        "scholar": "Hacker",
        "scavenger": "Runner",
        "healer": "Fixer",
    },
    "candela": {
        "vanguard": "Face",
        "scholar": "Weird",
        "scavenger": "Slink",
        "healer": "Muscle",
    },
    "burnwillow": {
        "vanguard": {"role": "front-line", "stat_focus": "might"},
        "scholar": {"role": "utility", "stat_focus": "wits"},
        "scavenger": {"role": "utility", "stat_focus": "wits"},
        "healer": {"role": "support", "stat_focus": "aether"},
    },
    "crown": {
        "vanguard": "Soldier",
        "scholar": "Scholar",
        "scavenger": "Spy",
        "healer": "Priest",
    },
}


# =========================================================================
# ARCHETYPE WEIGHT TABLES — per-system, per-class affinity scores
# =========================================================================
# Each class has {vanguard, scholar, scavenger, healer} weights (1-5).
# Higher weight = more likely to be picked when that archetype is chosen.

ARCHETYPE_WEIGHTS: Dict[str, Dict[str, Dict[str, int]]] = {
    "dnd5e": {
        "Fighter":   {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Wizard":    {"vanguard": 1, "scholar": 5, "scavenger": 1, "healer": 2},
        "Rogue":     {"vanguard": 2, "scholar": 1, "scavenger": 5, "healer": 1},
        "Cleric":    {"vanguard": 1, "scholar": 2, "scavenger": 1, "healer": 5},
        "Paladin":   {"vanguard": 4, "scholar": 1, "scavenger": 1, "healer": 3},
        "Ranger":    {"vanguard": 3, "scholar": 2, "scavenger": 4, "healer": 1},
        "Barbarian": {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Bard":      {"vanguard": 1, "scholar": 3, "scavenger": 3, "healer": 2},
        "Druid":     {"vanguard": 1, "scholar": 4, "scavenger": 2, "healer": 4},
        "Monk":      {"vanguard": 3, "scholar": 3, "scavenger": 2, "healer": 1},
        "Sorcerer":  {"vanguard": 2, "scholar": 4, "scavenger": 2, "healer": 1},
        "Warlock":   {"vanguard": 2, "scholar": 3, "scavenger": 3, "healer": 1},
        "Artificer": {"vanguard": 1, "scholar": 4, "scavenger": 3, "healer": 2},
    },
    "stc": {
        "Warrior":  {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Scholar":  {"vanguard": 1, "scholar": 5, "scavenger": 1, "healer": 3},
        "Hunter":   {"vanguard": 3, "scholar": 1, "scavenger": 5, "healer": 1},
        "Leader":   {"vanguard": 4, "scholar": 2, "scavenger": 1, "healer": 3},
        "Agent":    {"vanguard": 2, "scholar": 2, "scavenger": 4, "healer": 1},
        "Envoy":    {"vanguard": 1, "scholar": 3, "scavenger": 2, "healer": 4},
    },
    "bitd": {
        "Cutter":  {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Hound":   {"vanguard": 3, "scholar": 2, "scavenger": 4, "healer": 1},
        "Leech":   {"vanguard": 1, "scholar": 3, "scavenger": 2, "healer": 5},
        "Lurk":    {"vanguard": 1, "scholar": 1, "scavenger": 5, "healer": 1},
        "Slide":   {"vanguard": 1, "scholar": 2, "scavenger": 3, "healer": 2},
        "Spider":  {"vanguard": 1, "scholar": 4, "scavenger": 2, "healer": 2},
        "Whisper": {"vanguard": 1, "scholar": 5, "scavenger": 1, "healer": 2},
    },
    "sav": {
        "Mechanic":  {"vanguard": 1, "scholar": 3, "scavenger": 2, "healer": 5},
        "Muscle":    {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Mystic":    {"vanguard": 1, "scholar": 5, "scavenger": 1, "healer": 2},
        "Pilot":     {"vanguard": 2, "scholar": 2, "scavenger": 4, "healer": 1},
        "Scoundrel": {"vanguard": 2, "scholar": 1, "scavenger": 5, "healer": 1},
        "Speaker":   {"vanguard": 1, "scholar": 3, "scavenger": 2, "healer": 3},
        "Stitch":    {"vanguard": 1, "scholar": 3, "scavenger": 1, "healer": 5},
    },
    "bob": {
        "Heavy":   {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Medic":   {"vanguard": 1, "scholar": 3, "scavenger": 1, "healer": 5},
        "Officer": {"vanguard": 3, "scholar": 2, "scavenger": 1, "healer": 3},
        "Scout":   {"vanguard": 2, "scholar": 1, "scavenger": 5, "healer": 1},
        "Sniper":  {"vanguard": 3, "scholar": 2, "scavenger": 4, "healer": 1},
        "Soldier": {"vanguard": 4, "scholar": 1, "scavenger": 2, "healer": 1},
        "Rookie":  {"vanguard": 3, "scholar": 2, "scavenger": 3, "healer": 2},
    },
    "cbrpnk": {
        "Hacker": {"vanguard": 1, "scholar": 5, "scavenger": 2, "healer": 1},
        "Punk":   {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Fixer":  {"vanguard": 1, "scholar": 2, "scavenger": 2, "healer": 5},
        "Ghost":  {"vanguard": 2, "scholar": 2, "scavenger": 5, "healer": 1},
    },
    "candela": {
        "Face":   {"vanguard": 3, "scholar": 2, "scavenger": 2, "healer": 3},
        "Muscle": {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Scholar":{"vanguard": 1, "scholar": 5, "scavenger": 1, "healer": 3},
        "Slink":  {"vanguard": 1, "scholar": 1, "scavenger": 5, "healer": 1},
        "Weird":  {"vanguard": 1, "scholar": 4, "scavenger": 2, "healer": 3},
    },
    "burnwillow": {
        "The Sellsword": {"vanguard": 4, "scholar": 1, "scavenger": 3, "healer": 1},
        "The Occultist":  {"vanguard": 1, "scholar": 5, "scavenger": 2, "healer": 2},
        "The Sentinel":   {"vanguard": 3, "scholar": 1, "scavenger": 1, "healer": 5},
        "The Archer":     {"vanguard": 3, "scholar": 2, "scavenger": 4, "healer": 1},
        "The Vanguard":   {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "The Scholar":    {"vanguard": 1, "scholar": 5, "scavenger": 1, "healer": 3},
    },
    "crown": {
        "Soldier": {"vanguard": 5, "scholar": 1, "scavenger": 2, "healer": 1},
        "Scholar": {"vanguard": 1, "scholar": 5, "scavenger": 1, "healer": 2},
        "Spy":     {"vanguard": 1, "scholar": 2, "scavenger": 5, "healer": 1},
        "Priest":  {"vanguard": 1, "scholar": 3, "scavenger": 1, "healer": 5},
    },
}


def pick_weighted_class(system_id: str, archetype: str,
                        rng: Optional[random.Random] = None) -> str:
    """Pick a class/role from the full list, weighted by archetype affinity.

    Args:
        system_id: Engine system identifier.
        archetype: One of "vanguard", "scholar", "scavenger", "healer".
        rng: Optional seeded RNG for determinism.

    Returns:
        Class/role name string (e.g. "Paladin", "Lurk", "Muscle").
    """
    rng = rng or random.Random()
    weights_map = ARCHETYPE_WEIGHTS.get(system_id, {})
    if not weights_map:
        # Fall back to legacy map
        legacy = COMPANION_CLASS_MAP.get(system_id, {}).get(archetype, archetype)
        if isinstance(legacy, dict):
            return legacy.get("class", legacy.get("order", archetype))
        return str(legacy)

    classes = list(weights_map.keys())
    scores = [weights_map[c].get(archetype, 1) for c in classes]
    return rng.choices(classes, weights=scores, k=1)[0]


# =========================================================================
# CHARACTER FACTORY — create full PC companions
# =========================================================================

# Stat allocation strategies per engine family
_FITD_SYSTEMS = {"bitd", "sav", "bob", "cbrpnk", "candela"}
_DUNGEON_SYSTEMS = {"dnd5e", "stc"}


def create_companion_character(
    engine: Any,
    system_id: str,
    archetype: str,
    name: str,
    rng: Optional[random.Random] = None,
) -> Any:
    """Create a full PC character for the companion and add to engine party.

    Uses the engine's own character creation to produce a real character
    with proper stats, then appends to engine.party without replacing
    the player's lead character.

    Args:
        engine: The game engine instance.
        system_id: System identifier (e.g. "dnd5e", "bitd").
        archetype: Companion archetype for weighted class selection.
        name: Character name.
        rng: Optional seeded RNG.

    Returns:
        The created character object, or None on failure.
    """
    rng = rng or random.Random()
    chosen_class = pick_weighted_class(system_id, archetype, rng)

    try:
        if system_id in _FITD_SYSTEMS:
            return _create_fitd_companion(engine, system_id, name, chosen_class, rng)
        elif system_id == "dnd5e":
            return _create_dnd5e_companion(engine, name, chosen_class, rng)
        elif system_id == "stc":
            return _create_stc_companion(engine, name, chosen_class, rng)
        elif system_id == "burnwillow":
            return _create_burnwillow_companion(engine, name, chosen_class, rng)
        elif system_id == "crown":
            return _create_crown_companion(engine, name, chosen_class, rng)
    except Exception:
        pass

    # Fallback: try generic create_character
    try:
        if hasattr(engine, 'create_character'):
            engine.create_character(name)
            if hasattr(engine, 'party') and engine.party:
                return engine.party[-1]
    except Exception:
        pass
    return None


def _create_fitd_companion(engine, system_id: str, name: str,
                           playbook: str, rng: random.Random) -> Any:
    """Create a FITD companion with proper playbook and action dots."""
    # Use engine.create_character with playbook
    if hasattr(engine, 'create_character'):
        engine.create_character(name, playbook=playbook)
    elif hasattr(engine, '_create_character'):
        engine._create_character(name, playbook=playbook)

    char = None
    if hasattr(engine, 'party') and engine.party:
        char = engine.party[-1]
    elif hasattr(engine, 'character'):
        char = engine.character

    if char and hasattr(char, 'playbook'):
        char.playbook = playbook

    # Distribute 4 action dots weighted by archetype
    if char and hasattr(char, 'action_dots'):
        _FITD_ACTION_SETS = {
            "bitd": ["hunt", "study", "survey", "tinker", "finesse", "prowl",
                     "skirmish", "wreck", "attune", "command", "consort", "sway"],
            "sav": ["doctor", "hack", "rig", "study", "helm", "scramble",
                    "scrap", "skulk", "attune", "command", "consort", "sway"],
        }
        actions = _FITD_ACTION_SETS.get(system_id, list(char.action_dots.keys()))
        if actions:
            for _ in range(4):
                act = rng.choice(actions)
                char.action_dots[act] = min(char.action_dots.get(act, 0) + 1, 3)

    return char


def _create_dnd5e_companion(engine, name: str, char_class: str,
                            rng: random.Random) -> Any:
    """Create a D&D 5e companion with rolled stats and class."""
    # Roll 4d6-drop-lowest for 6 abilities
    abilities = {}
    for stat in ["strength", "dexterity", "constitution",
                 "intelligence", "wisdom", "charisma"]:
        rolls = sorted([rng.randint(1, 6) for _ in range(4)])
        abilities[stat] = sum(rolls[1:])  # drop lowest

    if hasattr(engine, 'create_character'):
        engine.create_character(name, char_class=char_class, **abilities)
    elif hasattr(engine, '_create_character'):
        engine._create_character(name, char_class=char_class, **abilities)

    char = None
    if hasattr(engine, 'party') and engine.party:
        char = engine.party[-1]
    elif hasattr(engine, 'character'):
        char = engine.character

    # Set class if engine didn't handle it
    if char:
        if hasattr(char, 'char_class') and not char.char_class:
            char.char_class = char_class
        if hasattr(char, 'character_class') and not char.character_class:
            char.character_class = char_class

    return char


def _create_stc_companion(engine, name: str, heroic_path: str,
                          rng: random.Random) -> Any:
    """Create a Cosmere RPG companion with heroic path."""
    if hasattr(engine, 'create_character'):
        engine.create_character(name, heroic_path=heroic_path)
    elif hasattr(engine, '_create_character'):
        engine._create_character(name, heroic_path=heroic_path)

    char = None
    if hasattr(engine, 'party') and engine.party:
        char = engine.party[-1]
    elif hasattr(engine, 'character'):
        char = engine.character

    if char and hasattr(char, 'heroic_path') and not char.heroic_path:
        char.heroic_path = heroic_path
    return char


def _create_burnwillow_companion(engine, name: str, loadout: str,
                                 rng: random.Random) -> Any:
    """Create a Burnwillow companion using the existing factory."""
    from codex.games.burnwillow.autopilot import create_ai_character
    _, _, stats, loadout_id, biography = create_ai_character(
        seed=rng.randint(0, 999999), name=name,
    )
    # Use engine init with stats
    if hasattr(engine, 'init_game'):
        engine.init_game(name, stats, loadout_id)

    char = None
    if hasattr(engine, 'party') and engine.party:
        char = engine.party[-1]
    elif hasattr(engine, 'character'):
        char = engine.character
    return char


def _create_crown_companion(engine, name: str, role: str,
                            rng: random.Random) -> Any:
    """Create a Crown companion with a role."""
    if hasattr(engine, 'create_character'):
        engine.create_character(name)

    char = None
    if hasattr(engine, 'party') and engine.party:
        char = engine.party[-1]
    elif hasattr(engine, 'character'):
        char = engine.character
    return char


# Narrated decision templates — keyed by (action, archetype)
DECISION_NARRATION: Dict[tuple, List[str]] = {
    ("attack", "vanguard"): [
        "{name} snarls and charges forward.",
        "{name} doesn't hesitate — blade first.",
        "{name} lunges at {target} with reckless fury.",
    ],
    ("attack", "scholar"): [
        "{name} strikes reluctantly, eyes still scanning the room.",
        "{name} lands a precise, calculated blow.",
    ],
    ("attack", "scavenger"): [
        "{name} darts in low, striking at a gap in {target}'s guard.",
        "{name} feints left, then strikes from the shadows.",
    ],
    ("attack", "healer"): [
        "{name} raises their weapon with a grimace.",
        "{name} strikes with reluctant precision.",
    ],
    ("guard", "vanguard"): [
        "{name} plants their feet and raises their shield.",
        "{name} braces, daring anything to come closer.",
    ],
    ("guard", "healer"): [
        "{name} raises a ward and braces.",
        "{name} whispers a prayer and holds position.",
    ],
    ("triage", "healer"): [
        "{name} rushes to {target}'s side, hands already working.",
        "\"Hold still,\" {name} mutters, pressing cloth to the wound.",
    ],
    ("triage", "scholar"): [
        "{name} applies field medicine with textbook precision.",
        "{name} mutters anatomical terms as they work.",
    ],
    ("search", "scavenger"): [
        "{name} runs quick fingers along the walls and under furniture.",
        "{name} knows exactly where to look.",
    ],
    ("search", "scholar"): [
        "{name} examines the room with methodical thoroughness.",
        "{name} peers at inscriptions others would miss.",
    ],
    ("attack_reckless", "vanguard"): [
        "{name} ignores the blood streaming down their arm and charges.",
        "\"Not yet,\" {name} growls, throwing themselves at {target}.",
    ],
    ("intercept", "vanguard"): [
        "{name} steps in front of the blow, shield raised.",
        "{name} roars and throws themselves between {target} and danger.",
    ],
    ("intercept", "healer"): [
        "{name} rushes forward, ward blazing, to shield {target}.",
        "\"Not them!\" {name} cries, interposing.",
    ],
    ("bolster", "healer"): [
        "{name} channels energy into {target}, steadying their aim.",
        "{name} whispers words of power over {target}.",
    ],
    ("bolster", "scholar"): [
        "{name} traces a sigil in the air. {target} feels sharper.",
        "{name} mutters an incantation and {target}'s weapon gleams.",
    ],
    ("command", "vanguard"): [
        "\"NOW!\" {name} bellows at {target}.",
        "{name} points at the enemy and barks an order to {target}.",
    ],
    ("command", "scholar"): [
        "{name} reads the battlefield and signals {target} to strike.",
        "\"There — the opening!\" {name} calls to {target}.",
    ],
    ("summon", "scholar"): [
        "{name} pulls arcane threads from the air, binding them into form.",
        "{name} opens a tome and reads aloud. Something stirs.",
    ],
    ("summon", "healer"): [
        "{name} calls upon the beyond. A spectral guardian answers.",
        "{name} prays and a luminous shape coalesces.",
    ],
}


# Grudging narration for negative bond (WO-V62.0: Mentorship & Rivalry)
_GRUDGING_NARRATION: Dict[str, List[str]] = {
    "attack": [
        "{name} attacks — but only because their own survival demands it.",
        "{name} sighs with visible irritation and swings.",
        "{name} strikes, pointedly ignoring your direction.",
    ],
    "guard": [
        "{name} raises their shield, more for themselves than for you.",
        "{name} grudgingly takes a defensive stance.",
    ],
    "triage": [
        "{name} patches the wound in cold silence.",
        "\"Don't read into this,\" {name} mutters while applying bandages.",
    ],
    "intercept": [
        "{name} steps in — not for you, but because letting an ally fall would be inconvenient.",
    ],
    "bolster": [
        "{name} provides support with a look that says 'you owe me'.",
    ],
    "command": [
        "{name} barks an order, then adds: \"I'm not doing this for you.\"",
    ],
}


def get_companion_class(system_id: str, archetype: str) -> Optional[dict]:
    """Look up the system-specific class/playbook for an archetype.

    Returns dict (for systems with structured data) or str (for FITD playbooks),
    or None if not found.
    """
    system_map = COMPANION_CLASS_MAP.get(system_id, {})
    return system_map.get(archetype)


def narrate_decision(action: str, archetype: str, name: str,
                     target: str = "the enemy", evolution_drift: Optional[dict] = None,
                     bond_tier: Optional[str] = None) -> str:
    """Generate a narrated companion decision line.

    Args:
        action: The mechanical action ("attack", "guard", "triage", "search")
        archetype: Companion archetype ("vanguard", "scholar", etc.)
        name: Companion's name
        target: Target name for attack actions
        evolution_drift: Optional dict of trait -> drift float for evolved narration
        bond_tier: Optional bond tier ("hostile", "distrustful", etc.)

    Returns:
        Formatted narration string, or empty string if no template found.
    """
    # WO-V62.0: Grudging narration for negative bond
    if bond_tier in ("distrustful", "hostile"):
        grudge_templates = _GRUDGING_NARRATION.get(action, [])
        if grudge_templates:
            return random.choice(grudge_templates).format(name=name, target=target)

    # Check for evolved narration
    if evolution_drift:
        caution_drift = evolution_drift.get("caution", 0)
        aggression_drift = evolution_drift.get("aggression", 0)
        if action == "attack" and caution_drift > 0.15:
            return f"{name} hesitates — then charges anyway, but angles for cover."
        if action == "attack" and aggression_drift < -0.1:
            return f"{name} holds the line instead of charging. They've learned."

    templates = DECISION_NARRATION.get((action, archetype), [])
    if not templates:
        # Generic fallback
        templates = DECISION_NARRATION.get((action, "vanguard"), [])
    if not templates:
        return ""

    template = random.choice(templates)
    return template.format(name=name, target=target)

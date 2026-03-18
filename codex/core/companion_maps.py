"""
Companion Maps — Cross-system archetype-to-class mapping & narration.
====================================================================

WO-V61.0 Track D: Maps personality archetypes (vanguard, scholar,
scavenger, healer) to system-specific character classes/playbooks.
Also provides narrated decision templates for companion actions.
"""

from typing import Dict, List, Optional
import random

# Maps personality archetypes to system-specific character classes/playbooks
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

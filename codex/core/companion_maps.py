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
}


def get_companion_class(system_id: str, archetype: str) -> Optional[dict]:
    """Look up the system-specific class/playbook for an archetype.

    Returns dict (for systems with structured data) or str (for FITD playbooks),
    or None if not found.
    """
    system_map = COMPANION_CLASS_MAP.get(system_id, {})
    return system_map.get(archetype)


def narrate_decision(action: str, archetype: str, name: str,
                     target: str = "the enemy", evolution_drift: Optional[dict] = None) -> str:
    """Generate a narrated companion decision line.

    Args:
        action: The mechanical action ("attack", "guard", "triage", "search")
        archetype: Companion archetype ("vanguard", "scholar", etc.)
        name: Companion's name
        target: Target name for attack actions
        evolution_drift: Optional dict of trait -> drift float for evolved narration

    Returns:
        Formatted narration string, or empty string if no template found.
    """
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

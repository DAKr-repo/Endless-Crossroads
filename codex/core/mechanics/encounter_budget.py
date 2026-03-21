"""
codex.core.mechanics.encounter_budget — Encounter Difficulty Calculator
=========================================================================
System-aware encounter budget calculator for D&D 5e (XP thresholds),
FITD (threat level), and STC (danger rating).
"""

from typing import Dict, List, Tuple

# D&D 5e XP thresholds by level (Easy, Medium, Hard, Deadly)
DND5E_THRESHOLDS: Dict[int, Tuple[int, int, int, int]] = {
    1: (25, 50, 75, 100),
    2: (50, 100, 150, 200),
    3: (75, 150, 225, 400),
    4: (125, 250, 375, 500),
    5: (250, 500, 750, 1100),
    6: (300, 600, 900, 1400),
    7: (350, 750, 1100, 1700),
    8: (450, 900, 1400, 2100),
    9: (550, 1100, 1600, 2400),
    10: (600, 1200, 1900, 2800),
    11: (800, 1600, 2400, 3600),
    12: (1000, 2000, 3000, 4500),
    13: (1100, 2200, 3400, 5100),
    14: (1250, 2500, 3800, 5700),
    15: (1400, 2800, 4300, 6400),
    16: (1600, 3200, 4800, 7200),
    17: (2000, 3900, 5900, 8800),
    18: (2100, 4200, 6300, 9500),
    19: (2400, 4900, 7300, 10900),
    20: (2800, 5700, 8500, 12700),
}

# D&D 5e CR to XP mapping
CR_TO_XP: Dict[str, int] = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100,
    "1": 200, "2": 450, "3": 700, "4": 1100,
    "5": 1800, "6": 2300, "7": 2900, "8": 3900,
    "9": 5000, "10": 5900, "11": 7200, "12": 8400,
    "13": 10000, "14": 11500, "15": 13000, "16": 15000,
    "17": 18000, "18": 20000, "19": 22000, "20": 25000,
    "21": 33000, "22": 41000, "23": 50000, "24": 62000,
    "25": 75000, "26": 90000, "27": 105000, "28": 120000,
    "29": 135000, "30": 155000,
}

# Encounter multipliers by number of monsters (D&D 5e DMG)
ENCOUNTER_MULTIPLIERS: List[Tuple[int, float]] = [
    (1, 1.0), (2, 1.5), (3, 2.0), (7, 2.5), (11, 3.0), (15, 4.0),
]


def _get_multiplier(num_monsters: int) -> float:
    mult = 1.0
    for threshold, m in ENCOUNTER_MULTIPLIERS:
        if num_monsters >= threshold:
            mult = m
    return mult


def calculate_dnd5e_budget(
    party_levels: List[int],
    monster_crs: List[str],
) -> str:
    """Calculate D&D 5e encounter difficulty.

    Args:
        party_levels: List of party member levels [5, 5, 4, 4]
        monster_crs: List of monster CRs ["3", "1", "1"]

    Returns:
        Formatted encounter budget analysis.
    """
    if not party_levels:
        return "No party members specified."

    # Party thresholds
    easy = sum(DND5E_THRESHOLDS.get(l, (25, 50, 75, 100))[0] for l in party_levels)
    medium = sum(DND5E_THRESHOLDS.get(l, (25, 50, 75, 100))[1] for l in party_levels)
    hard = sum(DND5E_THRESHOLDS.get(l, (25, 50, 75, 100))[2] for l in party_levels)
    deadly = sum(DND5E_THRESHOLDS.get(l, (25, 50, 75, 100))[3] for l in party_levels)

    # Monster XP
    raw_xp = sum(CR_TO_XP.get(cr, 0) for cr in monster_crs)
    mult = _get_multiplier(len(monster_crs))
    adjusted_xp = int(raw_xp * mult)

    # Determine difficulty
    if adjusted_xp >= deadly:
        difficulty = "DEADLY"
    elif adjusted_xp >= hard:
        difficulty = "Hard"
    elif adjusted_xp >= medium:
        difficulty = "Medium"
    elif adjusted_xp >= easy:
        difficulty = "Easy"
    else:
        difficulty = "Trivial"

    lines = [
        "--- Encounter Budget (D&D 5e) ---",
        f"Party: {len(party_levels)} members (levels {', '.join(str(l) for l in party_levels)})",
        f"Monsters: {len(monster_crs)} (CRs {', '.join(monster_crs)})",
        f"",
        f"Thresholds: Easy {easy} / Medium {medium} / Hard {hard} / Deadly {deadly}",
        f"Monster XP: {raw_xp} raw x{mult} = {adjusted_xp} adjusted",
        f"Difficulty: {difficulty}",
    ]
    return "\n".join(lines)


def calculate_fitd_threat(tier: int, num_enemies: int, scale: str = "standard") -> str:
    """FITD threat assessment based on tier and enemy count."""
    if scale == "limited":
        threat = "Low" if num_enemies <= tier else "Moderate"
    elif scale == "standard":
        if num_enemies <= tier:
            threat = "Moderate"
        elif num_enemies <= tier * 2:
            threat = "High"
        else:
            threat = "Extreme"
    else:
        threat = "Extreme"

    lines = [
        "--- Threat Assessment (FITD) ---",
        f"Crew Tier: {tier}  Enemies: {num_enemies}  Scale: {scale}",
        f"Threat Level: {threat}",
    ]
    return "\n".join(lines)


def calculate_encounter(system_tag: str, **kwargs) -> str:
    """Route to system-specific calculator."""
    tag = system_tag.upper()
    if tag == "DND5E":
        return calculate_dnd5e_budget(
            kwargs.get("party_levels", [1]),
            kwargs.get("monster_crs", ["1"]),
        )
    elif tag in ("BITD", "SAV", "BOB", "CBRPNK", "CANDELA"):
        return calculate_fitd_threat(
            kwargs.get("tier", 1),
            kwargs.get("num_enemies", 1),
            kwargs.get("scale", "standard"),
        )
    return f"Encounter budget not implemented for {tag}."

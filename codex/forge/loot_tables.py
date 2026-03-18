"""
codex/forge/loot_tables.py — Deterministic Table Engine (WO-V14.0 / WO-V15.0)
===============================================================================
Standalone SRD-based loot, lifepath, and trinket tables.
Zero AI dependency — all results are pure random table lookups.

Supports vault-sourced data via refresh_from_vault() hot-reload.

Public API:
    roll_treasure_hoard(cr_range) -> str
    roll_lifepath() -> str
    roll_trinket() -> str
    roll_on_srd_table(category) -> str
    list_tables() -> list[str]
    refresh_from_vault() -> None
"""

import json
import random
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent  # -> Codex/

# =============================================================================
# SRD LOOT — Weapons, Armor, Potions, General (Mundane), Magic Items
# =============================================================================

SRD_LOOT: dict[str, list[dict[str, str]]] = {
    "weapons": [
        {"name": "Longsword", "desc": "A versatile blade favored by knights. 1d8 slashing."},
        {"name": "Shortbow", "desc": "A compact bow for skirmishers. 1d6 piercing, range 80/320."},
        {"name": "Battleaxe", "desc": "A heavy chopping weapon. 1d8 slashing, versatile (1d10)."},
        {"name": "Dagger", "desc": "A light blade for close work. 1d4 piercing, finesse, thrown."},
        {"name": "Greatsword", "desc": "A massive two-handed blade. 2d6 slashing, heavy."},
        {"name": "Handaxe", "desc": "A small throwing axe. 1d6 slashing, light, thrown."},
        {"name": "Javelin", "desc": "A throwing spear. 1d6 piercing, thrown (30/120)."},
        {"name": "Light Crossbow", "desc": "A mechanical ranged weapon. 1d8 piercing, loading."},
        {"name": "Mace", "desc": "A heavy bludgeoning weapon. 1d6 bludgeoning."},
        {"name": "Quarterstaff", "desc": "A simple wooden staff. 1d6 bludgeoning, versatile (1d8)."},
        {"name": "Rapier", "desc": "A thrusting blade for duelists. 1d8 piercing, finesse."},
        {"name": "Scimitar", "desc": "A curved slashing blade. 1d6 slashing, finesse, light."},
        {"name": "Spear", "desc": "A versatile polearm. 1d6 piercing, thrown (20/60)."},
        {"name": "Warhammer", "desc": "A crushing martial weapon. 1d8 bludgeoning, versatile (1d10)."},
        {"name": "Longbow", "desc": "A powerful ranged weapon. 1d8 piercing, heavy, range 150/600."},
    ],
    "armor": [
        {"name": "Padded Armor", "desc": "Quilted layers. AC 11 + Dex, stealth disadvantage.", "slot": "Chest", "defense_bonus": 1},
        {"name": "Leather Armor", "desc": "Cured hide. AC 11 + Dex.", "slot": "Chest", "defense_bonus": 1},
        {"name": "Studded Leather", "desc": "Reinforced leather. AC 12 + Dex.", "slot": "Chest", "defense_bonus": 2},
        {"name": "Hide Armor", "desc": "Thick animal pelts. AC 12 + Dex (max 2).", "slot": "Chest", "defense_bonus": 2},
        {"name": "Chain Shirt", "desc": "Interlocking rings. AC 13 + Dex (max 2).", "slot": "Chest", "defense_bonus": 3},
        {"name": "Scale Mail", "desc": "Overlapping plates. AC 14 + Dex (max 2), stealth disadv.", "slot": "Chest", "defense_bonus": 4},
        {"name": "Breastplate", "desc": "Fitted metal chest piece. AC 14 + Dex (max 2).", "slot": "Chest", "defense_bonus": 4},
        {"name": "Half Plate", "desc": "Shaped plates and mail. AC 15 + Dex (max 2), stealth disadv.", "slot": "Chest", "defense_bonus": 5},
        {"name": "Ring Mail", "desc": "Leather with heavy rings. AC 14, stealth disadvantage.", "slot": "Chest", "defense_bonus": 4},
        {"name": "Chain Mail", "desc": "Full chain links. AC 16, Str 13, stealth disadvantage.", "slot": "Chest", "defense_bonus": 6},
        {"name": "Splint Armor", "desc": "Vertical metal strips. AC 17, Str 15, stealth disadv.", "slot": "Chest", "defense_bonus": 7},
        {"name": "Plate Armor", "desc": "Full plate harness. AC 18, Str 15, stealth disadvantage.", "slot": "Chest", "defense_bonus": 8},
        {"name": "Shield", "desc": "A wooden or metal shield. +2 AC.", "slot": "L.Hand", "defense_bonus": 2},
        # Tier 3+ — memory_seed eligible
        {"name": "Ironscale Greaves", "desc": "Articulated iron leg plates. Tier III.", "slot": "Legs", "defense_bonus": 3, "memory_seed_eligible": True},
        {"name": "Deepforge Vambraces", "desc": "Forearm guards from deep-forge iron. Tier III.", "slot": "Arms", "defense_bonus": 3, "memory_seed_eligible": True},
        {"name": "Ambercore Breastplate", "desc": "Crystallized amber fused with iron. Tier IV.", "slot": "Chest", "defense_bonus": 4, "memory_seed_eligible": True},
    ],
    "potions": [
        {"name": "Potion of Healing", "desc": "Restores 2d4+2 hit points. Red liquid, glimmers."},
        {"name": "Potion of Greater Healing", "desc": "Restores 4d4+4 hit points. Bright crimson."},
        {"name": "Potion of Fire Resistance", "desc": "Resistance to fire damage for 1 hour."},
        {"name": "Potion of Invisibility", "desc": "Invisible for 1 hour or until you attack/cast."},
        {"name": "Potion of Speed", "desc": "Haste effect for 1 minute. Golden liquid."},
        {"name": "Potion of Water Breathing", "desc": "Breathe underwater for 1 hour. Murky green."},
        {"name": "Antitoxin", "desc": "Advantage on saves vs poison for 1 hour."},
        {"name": "Potion of Climbing", "desc": "Climbing speed equal to walking for 1 hour."},
    ],
    "general": [
        {"name": "Hempen Rope (50 ft)", "desc": "Standard adventuring rope. 10 lbs."},
        {"name": "Torch", "desc": "Bright light 20 ft, dim 20 ft more. Burns 1 hour."},
        {"name": "Bedroll", "desc": "Insulated sleeping roll. 7 lbs."},
        {"name": "Pitons (10)", "desc": "Iron spikes for climbing. 2.5 lbs."},
        {"name": "Rations (1 day)", "desc": "Dried food sufficient for one day. 2 lbs."},
        {"name": "Waterskin", "desc": "Holds 4 pints of liquid. 5 lbs full."},
        {"name": "Tinderbox", "desc": "Flint, steel, and tinder for starting fires."},
        {"name": "Iron Pot", "desc": "A sturdy cooking pot. 10 lbs."},
        {"name": "Crowbar", "desc": "Advantage on STR checks to force open doors/crates."},
        {"name": "Grappling Hook", "desc": "Iron hook for climbing. 4 lbs."},
        {"name": "Healer's Kit", "desc": "10 uses. Stabilize a creature at 0 HP."},
        {"name": "Thieves' Tools", "desc": "Lockpicks and files for disabling traps and locks."},
        {"name": "Oil Flask", "desc": "Burns 2 rounds if ignited. 5 ft area, 5 fire damage."},
        {"name": "Ball Bearings (bag)", "desc": "10 ft area. DEX DC 10 or fall prone."},
        {"name": "Caltrops (bag)", "desc": "5 ft area. DEX DC 15 or 1 piercing, -10 speed."},
    ],
    "magic_items": [
        {"name": "Bag of Holding", "desc": "Extradimensional space. Holds 500 lbs, weighs 15 lbs."},
        {"name": "Rope of Climbing", "desc": "60 ft silk rope that moves on command."},
        {"name": "Driftglobe", "desc": "Glass orb that hovers and casts Light/Daylight."},
        {"name": "Immovable Rod", "desc": "Iron rod that stays fixed in place when activated."},
        {"name": "Decanter of Endless Water", "desc": "Produces fresh or salt water on command."},
        {"name": "Sending Stones", "desc": "Paired stones for short messages, once per day."},
        {"name": "Goggles of Night", "desc": "Darkvision 60 ft while worn."},
        {"name": "Cloak of Protection", "desc": "+1 to AC and saving throws while attuned."},
        {"name": "Lantern of Revealing", "desc": "Reveals invisible creatures within bright light."},
        {"name": "Periapt of Wound Closure", "desc": "Stabilize at 0 HP, double healing dice."},
        {"name": "Eyes of Minute Seeing", "desc": "Advantage on Investigation checks within 1 ft."},
        {"name": "Circlet of Blasting", "desc": "Cast Scorching Ray once per dawn."},
        {"name": "Pearl of Power", "desc": "Recover one expended spell slot (3rd or lower)."},
        {"name": "Dust of Disappearance", "desc": "Invisible for 2d4 minutes when thrown."},
        {"name": "Chime of Opening", "desc": "Opens locks, latches, lids. 10 charges."},
    ],
}

# =============================================================================
# TREASURE HOARD — CR-Tiered d100 Loot Tables
# =============================================================================

_COIN_TIERS = {
    "0-4": {
        "coins": [
            (30, "6d6 x 100 cp, 3d6 x 10 sp"),
            (60, "2d6 x 10 sp, 2d6 x 10 gp"),
            (80, "2d6 x 100 cp, 2d6 x 10 gp"),
            (100, "3d6 x 10 gp"),
        ],
        "item_chance": 25,
        "item_pools": ["potions", "general"],
    },
    "5-10": {
        "coins": [
            (30, "4d6 x 100 sp, 1d6 x 100 gp"),
            (60, "2d6 x 100 gp, 1d6 x 10 pp"),
            (80, "4d6 x 100 gp"),
            (100, "2d6 x 100 gp, 3d6 x 10 pp"),
        ],
        "item_chance": 40,
        "item_pools": ["weapons", "armor", "potions", "general", "magic_items"],
    },
    "11-16": {
        "coins": [
            (25, "4d6 x 1000 gp"),
            (50, "4d6 x 1000 gp, 5d6 x 100 pp"),
            (75, "1d6 x 1000 gp, 2d6 x 100 pp"),
            (100, "2d6 x 1000 gp, 8d6 x 100 pp"),
        ],
        "item_chance": 60,
        "item_pools": ["weapons", "armor", "potions", "magic_items"],
    },
    "17+": {
        "coins": [
            (15, "12d6 x 1000 gp"),
            (55, "8d6 x 1000 gp, 5d6 x 100 pp"),
            (100, "10d6 x 1000 gp, 8d6 x 100 pp"),
        ],
        "item_chance": 100,
        "item_pools": ["weapons", "armor", "potions", "magic_items"],
    },
}


def _resolve_coins(formula: str) -> str:
    """Roll a coin formula like '6d6 x 100 cp, 3d6 x 10 sp' into readable text."""
    parts = formula.split(", ")
    results = []
    for part in parts:
        tokens = part.strip().split()
        # Parse NdM
        dice = tokens[0]
        n, m = dice.split("d")
        roll = sum(random.randint(1, int(m)) for _ in range(int(n)))
        multiplier = int(tokens[2]) if len(tokens) >= 3 else 1
        denomination = tokens[3] if len(tokens) >= 4 else tokens[-1]
        total = roll * multiplier
        results.append(f"{total:,} {denomination}")
    return ", ".join(results)


# =============================================================================
# VAULT CACHE LOADER
# =============================================================================

def _load_vault_cache() -> None:
    """Load vault-extracted equipment from config/systems/rules_DND5E.json.

    Merges vault data into SRD_LOOT, with vault data taking priority.
    Falls back silently to hardcoded tables if cache doesn't exist.
    """
    cache_path = _ROOT / "config" / "systems" / "rules_DND5E.json"
    if not cache_path.exists():
        return

    try:
        with open(cache_path, "r") as f:
            data = json.load(f)

        equipment = data.get("equipment", {})
        for category in SRD_LOOT:
            vault_items = equipment.get(category, [])
            if vault_items:
                # Merge: vault items supplement hardcoded, dedup by name
                existing_names = {item["name"] for item in SRD_LOOT[category]}
                for item in vault_items:
                    name = item.get("name", "")
                    if name and name not in existing_names:
                        SRD_LOOT[category].append(item)
                        existing_names.add(name)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass  # Silently fall back to hardcoded tables


def refresh_from_vault() -> None:
    """Public API: Re-load vault cache at runtime (e.g. after a scan)."""
    _load_vault_cache()


# Load vault cache at module import time
_load_vault_cache()


# =============================================================================
# LIFEPATH TABLES — Character Biography Generator
# =============================================================================

LIFEPATH_TABLES: dict[str, list[str]] = {
    "origins": [
        "A frontier village at the edge of civilization",
        "A bustling coastal port city",
        "A mountain monastery hidden in the clouds",
        "A noble estate fallen on hard times",
        "A nomadic caravan that never stayed long",
        "The slums of a vast imperial capital",
        "A forest commune of outcasts and refugees",
        "A mining town built around a played-out vein",
        "A riverside trading post at a crossroads",
        "An island fortress battered by storms",
    ],
    "parents": [
        "Both parents alive and in good health",
        "Orphaned young — raised by a distant relative",
        "Mother alive, father died in a war",
        "Father alive, mother lost to plague",
        "Raised by a mentor with no blood relation",
        "Parents alive but estranged — left by choice",
        "Found as an infant — parentage unknown",
        "One parent imprisoned, the other struggling",
        "Raised communally — 'everyone was family'",
        "Both parents were adventurers who never returned",
    ],
    "upbringing": [
        "Military discipline — drills before dawn",
        "Scholarly tutelage — ink-stained fingers and dusty tomes",
        "Criminal apprenticeship — locks, lies, and lookouts",
        "Spiritual devotion — hymns, fasting, and prayer",
        "Artisan craft — forge, loom, or potter's wheel",
        "Street survival — begging, stealing, running",
        "Noble court — etiquette, intrigue, and masks",
        "Wilderness isolation — hunting, trapping, silence",
        "Merchant trade — caravans, haggling, and ledgers",
        "Performer's life — stage, song, and wandering",
    ],
    "life_events": [
        "Survived a plague that killed half the settlement",
        "Witnessed a betrayal that changed your worldview",
        "Found a mentor who taught you everything that matters",
        "Fell in love — it ended badly",
        "Discovered a hidden talent during a crisis",
        "Were wrongly accused and had to prove your innocence",
        "Saved a stranger's life and earned a lifelong debt",
        "Lost everything in a fire and had to start over",
        "Uncovered a dangerous secret about someone powerful",
        "Made an enemy who still hunts you",
        "Won a contest or tournament of great renown",
        "Traveled to a foreign land and returned changed",
    ],
    "bonds": [
        "A childhood friend you haven't seen in years",
        "A sworn rival who drives you to improve",
        "A secret benefactor who watches from afar",
        "A sibling you'd die to protect",
        "A teacher whose final lesson you never understood",
        "An old debt you can never fully repay",
        "A lover whose memory haunts your dreams",
        "A comrade from your first real fight",
        "A holy figure who spoke a prophecy about you",
        "An animal companion more loyal than any person",
    ],
}


# =============================================================================
# ALIAS MAP — Normalize user input to canonical table names
# =============================================================================

_TABLE_ALIASES: dict[str, str] = {
    "treasure hoard": "_treasure_hoard",
    "treasure_hoard": "_treasure_hoard",
    "hoard": "_treasure_hoard",
    "magic items": "magic_items",
    "magic": "magic_items",
    "magical": "magic_items",
    "mundane": "general",
    "gear": "general",
    "equipment": "general",
    "adventuring gear": "general",
}


# =============================================================================
# PUBLIC API
# =============================================================================

def roll_treasure_hoard(cr_range: str = "0-4") -> str:
    """Roll on a CR-tiered treasure hoard table. Returns formatted output."""
    tier = _COIN_TIERS.get(cr_range, _COIN_TIERS["0-4"])
    d100 = random.randint(1, 100)

    # Determine coin result
    coin_text = ""
    for threshold, formula in tier["coins"]:
        if d100 <= threshold:
            coin_text = _resolve_coins(formula)
            break

    lines = [
        f"Treasure Hoard (CR {cr_range}) — d100: {d100}",
        f"  Coins: {coin_text}",
    ]

    # Item roll
    if random.randint(1, 100) <= tier["item_chance"]:
        pool_name = random.choice(tier["item_pools"])
        pool = SRD_LOOT.get(pool_name, SRD_LOOT["general"])
        item = random.choice(pool)
        lines.append(f"  Item:  {item['name']} — {item['desc']}")
    else:
        lines.append("  Item:  (none)")

    return "\n".join(lines)


def roll_lifepath() -> str:
    """Roll all 5 lifepath tables and return a formatted biography."""
    origin = random.choice(LIFEPATH_TABLES["origins"])
    parents = random.choice(LIFEPATH_TABLES["parents"])
    upbringing = random.choice(LIFEPATH_TABLES["upbringing"])
    event = random.choice(LIFEPATH_TABLES["life_events"])
    bond = random.choice(LIFEPATH_TABLES["bonds"])

    lines = [
        "LIFE PATH — Character Biography",
        "=" * 40,
        f"  Origin:    {origin}",
        f"  Parents:   {parents}",
        f"  Upbringing: {upbringing}",
        f"  Life Event: {event}",
        f"  Bond:      {bond}",
        "=" * 40,
    ]
    return "\n".join(lines)


def roll_trinket() -> str:
    """Roll a random mundane item from the general SRD pool."""
    item = random.choice(SRD_LOOT["general"])
    return f"{item['name']} — {item['desc']}"


def roll_on_srd_table(category: str) -> str | None:
    """Roll on a named SRD table. Returns None if category not found.

    Handles aliases: 'treasure hoard' -> roll_treasure_hoard(),
    'magic items' -> 'magic_items', spaces -> underscores.
    """
    category = category.lower().strip().strip("<>")

    # Check alias map first
    resolved = _TABLE_ALIASES.get(category)
    if resolved == "_treasure_hoard":
        return roll_treasure_hoard()

    # Normalize spaces to underscores
    if resolved is None:
        resolved = category.replace(" ", "_")

    pool = SRD_LOOT.get(resolved)
    if pool is None:
        return None
    item = random.choice(pool)
    return f"{item['name']} — {item['desc']}"


def list_tables() -> list[str]:
    """Return available table names."""
    srd = list(SRD_LOOT.keys())
    return srd + ["treasure_hoard", "lifepath", "trinket"]

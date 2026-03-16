"""
codex/core/dm_tools.py - DM Tools (Restored & Modernized)
==========================================================
Provides deterministic TTRPG utility functions:
  - Dice rolling (delegates to codex.core.dice)
  - NPC generation (expanded tables)
  - Trap generation (expanded tables)
  - Loot generation (delegates to codex.forge.loot_tables)
  - Encounter generation (delegates to codex.core.encounters)
  - Session note summarization (Ollama with timeout guard)
  - Vault scanning (EquipmentExtractor -> loot table hot-reload)

Replaces archived codex_tools.py with proper package imports.
Zero AI dependency for all functions except summarize_context().
"""

import random
import requests
from typing import Optional

from codex.core.dice import roll_dice as _core_roll_dice, format_roll_text

# =============================================================================
# OLLAMA CONFIG
# =============================================================================

OLLAMA_GEN_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 30  # seconds


# =============================================================================
# 1. DICE ROLLER
# =============================================================================

def roll_dice(dice_string: str) -> tuple[int, str]:
    """Roll dice using the core dice engine.

    Wraps codex.core.dice.roll_dice() to match the old (total, message)
    return signature expected by the terminal DM Tools menu.

    Args:
        dice_string: Dice notation like "2d6+3", "1d20", "4d6-2"

    Returns:
        (total, formatted_message)
    """
    try:
        total, rolls, modifier = _core_roll_dice(dice_string)
        msg = format_roll_text(total, rolls, modifier)
        return (total, msg)
    except ValueError as e:
        return (0, f"Invalid format: {e}")


# =============================================================================
# 2. NPC GENERATOR (Expanded)
# =============================================================================

_NPC_NAMES = [
    "Tharivol", "Durnan", "Elara", "Kael", "Mara", "Vex", "Orin",
    "Sable", "Hadrik", "Yenna", "Torvin", "Neve", "Balthus", "Asha",
    "Corwin", "Lysara", "Grint", "Petra", "Aldric", "Selene",
    "Theron", "Brynn", "Caelum", "Isolde",
]

_NPC_TRAITS = [
    "Nervous tic — taps fingers incessantly",
    "Boisterous laugh that fills the room",
    "Suspicious of all magic users",
    "Constantly polishing an old coin",
    "Covered in old scars, never explains them",
    "Speaks in rhyming couplets when stressed",
    "Has a pet rat hidden in their cloak",
    "Refuses to make eye contact",
    "Hums the same tune under their breath",
    "Collects teeth — 'for luck'",
    "Obsessively clean, wipes hands constantly",
    "Tells wildly different backstories each time",
    "Flinches at sudden movements",
    "Always eating something crunchy",
    "Wears far too many rings",
]

_NPC_QUIRKS = [
    "Owes money to someone dangerous",
    "Secretly literate in a land of illiterates",
    "Afraid of birds — all birds",
    "Has a twin who is their moral opposite",
    "Carries a love letter they'll never send",
    "Sleepwalks and remembers nothing",
    "Can't resist a wager, no matter the stakes",
    "Believes they've been cursed since childhood",
    "Once saw something in the dark they won't discuss",
    "Keeps a journal written in a code only they know",
]


_ARCHETYPE_PRIMARY_STATS: dict[str, list[str]] = {
    "archmage": ["INT", "WIS"],
    "wizard": ["INT"],
    "mage": ["INT"],
    "sorcerer": ["CHA", "INT"],
    "warlock": ["CHA", "INT"],
    "knight": ["STR", "CON"],
    "soldier": ["STR", "CON"],
    "guard": ["STR", "CON"],
    "warrior": ["STR", "DEX"],
    "barbarian": ["STR", "CON"],
    "thief": ["DEX", "CHA"],
    "assassin": ["DEX"],
    "rogue": ["DEX"],
    "ranger": ["DEX", "WIS"],
    "priest": ["WIS", "CHA"],
    "cleric": ["WIS"],
    "druid": ["WIS"],
    "paladin": ["STR", "CHA"],
    "bard": ["CHA", "DEX"],
    "noble": ["CHA", "INT"],
    "merchant": ["CHA", "WIS"],
    "alchemist": ["INT", "WIS"],
    "farmer": ["CON", "STR"],
    "blacksmith": ["STR", "CON"],
    "monk": ["DEX", "WIS"],
}


def _roll_3d6() -> int:
    return sum(random.randint(1, 6) for _ in range(3))


def _roll_4d6k3() -> int:
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort(reverse=True)
    return sum(rolls[:3])


def generate_npc(archetype: str = "") -> str:
    """Generate a random NPC with name, archetype, trait, quirk, and stats.

    Primary stats for the archetype use 4d6-drop-lowest (avg 12.2),
    all other stats use 3d6 (avg 10.5).

    Args:
        archetype: Optional archetype like "Merchant", "Guard", "Wizard".
                   If empty, one is chosen at random.

    Returns:
        Formatted NPC stat block string.
    """
    if not archetype:
        archetype = random.choice([
            "Merchant", "Guard", "Wizard", "Thief", "Priest",
            "Farmer", "Noble", "Soldier", "Bard", "Alchemist",
        ])

    name = random.choice(_NPC_NAMES)
    trait = random.choice(_NPC_TRAITS)
    quirk = random.choice(_NPC_QUIRKS)

    # Roll stats with archetype weighting
    primary = _ARCHETYPE_PRIMARY_STATS.get(archetype.lower(), [])
    stat_names = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    stats = {}
    for s in stat_names:
        stats[s] = _roll_4d6k3() if s in primary else _roll_3d6()
    stat_line = "  ".join(f"{s} {v}" for s, v in stats.items())

    return (
        f"**{name}** ({archetype})\n"
        f"Trait: {trait}\n"
        f"Quirk: {quirk}\n"
        f"Stats: {stat_line}"
    )


# =============================================================================
# 3. TRAP GENERATOR (Expanded)
# =============================================================================

_TRAP_TRIGGERS = [
    "Pressure Plate", "Tripwire", "Arcane Rune", "False Door Handle",
    "Motion Sensor Crystal", "Weight-Sensitive Floor Tile",
    "Broken Seal on a Chest", "Disturbed Cobweb Lattice",
]

_TRAP_EFFECTS = [
    "Poison Darts", "Falling Net", "Acid Spray", "Spiked Pit",
    "Flame Jet", "Lightning Arc", "Collapsing Ceiling",
    "Freezing Mist Cloud",
]

_TRAP_SCALING = {
    "easy":   {"dc": 12, "dmg": "1d6",  "label": "Mild"},
    "medium": {"dc": 15, "dmg": "2d10", "label": "Moderate"},
    "hard":   {"dc": 18, "dmg": "4d10", "label": "Deadly"},
}


def generate_trap(difficulty: str = "medium") -> str:
    """Generate a random trap with trigger, effect, DC, and damage.

    Args:
        difficulty: "easy", "medium", or "hard"

    Returns:
        Formatted trap description string.
    """
    difficulty = difficulty.lower().strip()
    if difficulty not in _TRAP_SCALING:
        # Fuzzy match
        for key in _TRAP_SCALING:
            if key in difficulty:
                difficulty = key
                break
        else:
            difficulty = "medium"

    cfg = _TRAP_SCALING[difficulty]
    trigger = random.choice(_TRAP_TRIGGERS)
    effect = random.choice(_TRAP_EFFECTS)

    return (
        f"**{trigger} / {effect}** [{cfg['label']}]\n"
        f"DC {cfg['dc']} DEX save or take {cfg['dmg']} damage."
    )


# =============================================================================
# 4. LOOT GENERATOR
# =============================================================================

def calculate_loot(difficulty: str = "medium", party_size: int = 4) -> str:
    """Generate loot using the SRD treasure hoard tables.

    Maps difficulty to CR range and delegates to loot_tables.roll_treasure_hoard().
    Adds a party-size gold multiplier on top.

    Args:
        difficulty: "easy", "medium", or "hard"
        party_size: Number of party members (1-8)

    Returns:
        Formatted loot string.
    """
    from codex.forge.loot_tables import roll_treasure_hoard

    difficulty = difficulty.lower().strip()
    cr_map = {
        "easy": "0-4",
        "medium": "5-10",
        "hard": "11-16",
    }
    cr_range = cr_map.get(difficulty, "0-4")
    party_size = max(1, min(8, party_size))

    hoard = roll_treasure_hoard(cr_range)

    # Add party bonus gold
    bonus_gold = random.randint(5, 20) * party_size
    return f"{hoard}\n  Party Bonus: +{bonus_gold} gp ({party_size} members)"


# =============================================================================
# 5. ENCOUNTER GENERATOR (NEW)
# =============================================================================

def generate_encounter(
    system_tag: str = "BURNWILLOW",
    tier: int = 1,
    party_size: int = 4,
) -> str:
    """Generate a random encounter using the universal encounter engine.

    Args:
        system_tag: "BURNWILLOW", "DND5E", "CBR_PNK", "STC"
        tier: Floor/difficulty tier (1-4)
        party_size: Number of party members

    Returns:
        Formatted encounter description string.
    """
    from codex.core.encounters import EncounterEngine, EncounterContext

    tier = max(1, min(4, tier))
    party_size = max(1, min(8, party_size))

    ctx = EncounterContext(
        system_tag=system_tag.upper(),
        party_size=party_size,
        threat_level=random.randint(1, 10),
        floor_tier=tier,
        room_type="normal",
        trigger="move_entry",
    )

    engine = EncounterEngine()
    result = engine.generate(ctx)

    lines = [
        f"Encounter ({system_tag.upper()}, Tier {tier}, Party of {party_size})",
        "=" * 50,
        f"  Type: {result.encounter_type}",
    ]

    if result.description:
        lines.append(f"  {result.description}")

    if result.entities:
        lines.append("  Entities:")
        for e in result.entities:
            name = e.get("name", "Unknown")
            hp = e.get("hp", "?")
            lines.append(f"    - {name} (HP: {hp})")

    if result.traps:
        lines.append("  Traps:")
        for t in result.traps:
            lines.append(f"    - {t.get('name', 'Unknown Trap')}")

    if result.loot:
        lines.append("  Loot:")
        for l in result.loot:
            lines.append(f"    - {l.get('name', 'Unknown Item')}")

    if result.doom_cost:
        lines.append(f"  Doom Cost: +{result.doom_cost}")

    lines.append("=" * 50)
    return "\n".join(lines)


# =============================================================================
# 6. SESSION NOTES (Ollama-backed)
# =============================================================================

def summarize_context(history_text: str) -> str:
    """Compress session history into bullet points using Ollama.

    Falls back gracefully if Ollama is unavailable or times out.

    Args:
        history_text: Raw session log text to summarize.

    Returns:
        Summary string (3 bullet points) or fallback message.
    """
    if not history_text.strip():
        return "No session notes to summarize."

    payload = {
        "model": "qwen2.5-coder:1.5b",
        "prompt": (
            "Summarize this RPG session log into 3 concise bullet points:\n"
            f"{history_text[:2000]}"
        ),
        "stream": False,
        "options": {"num_predict": 150},
    }

    try:
        r = requests.post(
            OLLAMA_GEN_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("response", "Summary generation returned empty.")
    except requests.Timeout:
        return "Summary unavailable — Ollama timed out."
    except requests.ConnectionError:
        return "Summary unavailable — Ollama not running."
    except Exception as e:
        return f"Summary unavailable — {e}"


# =============================================================================
# 7. BESTIARY LOOKUP (WO-V34.0)
# =============================================================================

def lookup_creature(name: str, system_tag: str = "BURNWILLOW") -> str:
    """Search bestiary across content tables by name substring.

    Searches ENEMY_TABLES, BOSS_TEMPLATES, and CONTENT_ARCHETYPES.
    Returns formatted stat block or "Not found".

    Args:
        name: Creature name or substring to search for.
        system_tag: System to search ("BURNWILLOW", "DND5E", "STC").

    Returns:
        Formatted stat block string.
    """
    tag = system_tag.upper()

    if tag == "BURNWILLOW":
        try:
            from codex.games.burnwillow.content import lookup_creature as bw_lookup
            result = bw_lookup(name)
            if result:
                return result
            return f"No creature matching '{name}' found in Burnwillow bestiary."
        except ImportError:
            return "Burnwillow content module not available."

    elif tag == "DND5E":
        try:
            from codex.games.dnd5e import _ENEMY_POOL
            q = name.lower()
            matches = []
            for tier, pool in _ENEMY_POOL.items():
                for enemy_name in pool:
                    if q in enemy_name.lower():
                        matches.append(f"**{enemy_name}** (Tier {tier} DnD5e)")
            if matches:
                return "\n".join(matches)
            return f"No creature matching '{name}' found in DnD5e bestiary."
        except ImportError:
            return "DnD5e module not available."

    elif tag == "STC":
        try:
            from codex.games.stc import _ENEMY_POOL
            q = name.lower()
            matches = []
            for tier, pool in _ENEMY_POOL.items():
                for enemy_name in pool:
                    if q in enemy_name.lower():
                        matches.append(f"**{enemy_name}** (Tier {tier} Cosmere)")
            if matches:
                return "\n".join(matches)
            return f"No creature matching '{name}' found in Cosmere bestiary."
        except ImportError:
            return "Cosmere module not available."

    return f"Bestiary not available for system: {tag}"


# =============================================================================
# 8. CODEX MODEL QUERY (WO-V34.0)
# =============================================================================

def query_codex(question: str, system_id: str = "") -> str:
    """RAG-enriched query to Codex model (qwen3:1.7b).

    Keeps Mimir free for narration by routing DM queries to the
    Academy/Codex model via Ollama.

    Flow:
    1. If system_id -> RAGService.search() for context chunks
    2. Build prompt: CONTEXT + QUESTION
    3. Call Ollama model="codex", num_predict=400, timeout=30s
    4. Return response text (graceful fallback on error)

    Args:
        question: The DM's question.
        system_id: Optional system filter for RAG context.

    Returns:
        Response text from Codex model.
    """
    if not question.strip():
        return "No question provided."

    # 1. Gather RAG context if available
    context = ""
    try:
        from codex.core.services.rag_service import get_rag_service
        rag = get_rag_service()
        if system_id:
            result = rag.search(question, system_id=system_id)
        else:
            result = rag.search(question)
        if result:
            context = result.context_str
    except Exception:
        pass  # RAG is optional

    # 2. Build prompt
    parts = []
    if context:
        parts.append(f"CONTEXT:\n{context[:2000]}\n")
    parts.append(f"QUESTION:\n{question}\n")
    parts.append("Answer concisely as a TTRPG rules expert.")
    prompt = "\n".join(parts)

    # 3. Call Ollama
    payload = {
        "model": "codex",
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 400},
    }

    try:
        r = requests.post(
            OLLAMA_GEN_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("response", "Codex returned empty response.")
    except requests.Timeout:
        return "Codex query timed out — Ollama busy."
    except requests.ConnectionError:
        return "Codex unavailable — Ollama not running."
    except Exception as e:
        return f"Codex query failed — {e}"


# =============================================================================
# 9. VAULT SCANNER
# =============================================================================

def scan_vault() -> str:
    """Run EquipmentExtractor on the dnd5e vault and hot-reload loot tables.

    Returns:
        Summary string with extraction counts.
    """
    try:
        from codex.integrations.vault_processor import EquipmentExtractor
        from codex.forge.loot_tables import refresh_from_vault
        from pathlib import Path

        vault_path = Path(__file__).resolve().parent.parent.parent / "vault" / "dnd5e"
        if not vault_path.exists():
            return f"Vault path not found: {vault_path}"

        extractor = EquipmentExtractor(
            system_id="DND5E", system_vault_path=vault_path)
        equipment = extractor.extract_all()

        if not any(equipment.values()):
            return f"No equipment extracted from {len(extractor.find_pdfs())} PDFs in {vault_path}"

        # Save to config
        config_dir = Path(__file__).resolve().parent.parent.parent / "config" / "systems"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "rules_DND5E.json"

        import json
        data = {"equipment": equipment, "stats": extractor.stats}
        with open(config_file, "w") as f:
            json.dump(data, f, indent=2)

        # Hot-reload into loot tables
        refresh_from_vault()

        # Build summary
        counts = {cat: len(items) for cat, items in equipment.items()}
        parts = [f"{cat}: {n}" for cat, n in counts.items() if n > 0]
        summary = f"Vault scan complete — {', '.join(parts) or 'no items found'}."
        summary += f" ({extractor.stats['pdfs_processed']} PDFs, {extractor.stats['pages_processed']} pages)"
        return summary

    except ImportError as e:
        return f"Vault scan failed — missing dependency: {e}"
    except Exception as e:
        return f"Vault scan failed — {e}"

"""
Narrative Frame — Narrative Intelligence Layer
================================================

Central module providing enriched context for every LLM (Mimir) call.
Implements 7 strategies from competitive analysis of AI Dungeon, Friends &
Fables, and QuestForge to dramatically improve small-model (0.5-1.7B) output:

1. **Few-Shot Examples**: Hand-written exemplars set the quality bar.
2. **Sensory Palettes**: Tier-specific word pools ground descriptions.
3. **Story Card Retrieval**: Keyword-triggered ANCHOR shards inject memory.
4. **Structured Prompts**: System/context/examples/prompt separation.
5. **Validation**: Heuristic rejection of broken/repetitive output.
6. **Room Fragments**: Pre-written fragments the model connects (not invents).
7. **Compressed World Primer**: Dense SYSTEM prompt in Modelfile.

All Mimir calls should route through ``build_narrative_frame()`` for
consistent, high-quality output regardless of the underlying model size.

WO-V47.0: The Depth & Quality Sprint — Phase 1A.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================================
# SENSORY PALETTES — Tier-specific word pools
# =========================================================================

NARRATIVE_PALETTES: Dict[str, Dict[str, List[str]]] = {
    "burnwillow_t1": {
        "adjectives": ["fungal", "damp", "rotting", "spore-choked", "crumbling", "pale"],
        "verbs": ["oozes", "drips", "creaks", "skitters", "festers", "seeps"],
        "sounds": ["dripping water", "chitinous clicking", "groaning wood", "wet footsteps"],
        "smells": ["damp earth", "mushroom spores", "decay", "mildew", "wet stone"],
    },
    "burnwillow_t2": {
        "adjectives": ["corroded", "ticking", "brass-plated", "oil-slicked", "grinding", "ancient"],
        "verbs": ["clanks", "whirs", "sparks", "hisses", "ticks", "grinds"],
        "sounds": ["grinding gears", "hissing steam", "ticking clockwork", "distant hammering"],
        "smells": ["machine oil", "hot brass", "ozone", "burnt copper", "old grease"],
    },
    "burnwillow_t3": {
        "adjectives": ["twisted", "aetherial", "corrupted", "luminous", "thorned", "petrified"],
        "verbs": ["pulses", "warps", "glimmers", "writhes", "resonates", "fractures"],
        "sounds": ["crystalline humming", "distant chanting", "wood splintering", "aetherial whispers"],
        "smells": ["charged air", "crushed sap", "ozone and amber", "burnt resin"],
    },
    "burnwillow_t4": {
        "adjectives": ["blighted", "radiant", "hollow", "sky-torn", "withered", "sovereign"],
        "verbs": ["blazes", "crumbles", "echoes", "crowns", "unravels", "consumes"],
        "sounds": ["wind through dead branches", "distant thunder", "cracking bark", "silence"],
        "smells": ["ash and sunlight", "dead flowers", "lightning-charred wood", "nothing at all"],
    },
}


# =========================================================================
# FEW-SHOT TEMPLATES — Hand-written exemplars per prompt type
# =========================================================================

NARRATIVE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "room_description": {
        "system": (
            "You describe dungeon rooms in a dark fantasy TTRPG. "
            "RULES: 2-3 sentences. Sensory details: sounds, smells, textures. "
            "No questions. No meta-commentary. Stay in character."
        ),
        "examples": [
            {
                "input": "Describe a tier 1 forge room with enemies present.",
                "output": (
                    "Rust flakes drift like red snow from the ceiling of this "
                    "gutted smithy. The anvil is split clean in two — something "
                    "nests in the crack, breathing wetly. Your torchlight catches "
                    "movement between the bellows."
                ),
            },
            {
                "input": "Describe a tier 2 library room, cleared of enemies.",
                "output": (
                    "Dust-choked shelves sag under crumbling tomes. A brass "
                    "orrery clicks overhead, its planets long misaligned. The "
                    "floor is littered with torn pages — someone searched here "
                    "before you, and left in a hurry."
                ),
            },
        ],
    },
    "npc_dialogue": {
        "system": (
            "You voice NPCs in a dark fantasy TTRPG. "
            "RULES: 1-2 sentences. Terse and atmospheric. "
            "Prefix with a tone tag: [Hushed] [Urgent] [Gravelly] [Solemn] "
            "[Cheerful] [Menacing]. Stay in character."
        ),
        "examples": [
            {
                "input": "A wary delver greets the player in a tier 2 dungeon.",
                "output": (
                    '[Hushed] "Keep your voice down — the gears have ears '
                    "in this place. I've been mapping these corridors for three "
                    'days and I still can\'t find the way back."'
                ),
            },
            {
                "input": "A friendly merchant offers trade in a tier 1 dungeon.",
                "output": (
                    '[Cheerful] "Ah, another soul brave enough — or foolish '
                    "enough — to crawl the Rootwork! I've got salves, rope, "
                    'and one very sharp knife. What catches your eye?"'
                ),
            },
        ],
    },
    "quest_generation": {
        "system": (
            "You generate quest hooks for a dark fantasy TTRPG dungeon crawler. "
            "RULES: Output ONLY valid JSON. Quests should be terse, evocative, "
            "and tied to dungeon exploration. No fetch quests — give reasons to delve deeper."
        ),
        "examples": [
            {
                "input": "Generate a tier 2 dungeon quest.",
                "output": (
                    '{"title": "The Stopped Clock", '
                    '"description": "A massive gear-heart has seized deep in the Clockwork. '
                    'The grinding silence is worse than the noise ever was. Find it and restart it — '
                    'or discover what stopped it.", '
                    '"objective_type": "reach", "tier": 2, "count": 1}'
                ),
            },
            {
                "input": "Generate a tier 1 kill quest.",
                "output": (
                    '{"title": "Spore Purge", '
                    '"description": "The fungal blooms in the lower warrens are spawning '
                    'faster than the rot-wardens can burn them. Cut down the mature growths '
                    'before they seed the upper levels.", '
                    '"objective_type": "kill_count", "tier": 1, "count": 4}'
                ),
            },
        ],
    },
    "combat_narration": {
        "system": (
            "You narrate combat in a dark fantasy TTRPG. "
            "RULES: 1-2 sentences per action. Visceral and kinetic. "
            "Reference the weapon/attack used. No game mechanics in prose."
        ),
        "examples": [
            {
                "input": "Player hits a Rot Shambler with a shortsword for 6 damage.",
                "output": (
                    "Your blade sinks into the shambler's bloated flank with a "
                    "wet crunch. It staggers, trailing spores and black ichor "
                    "across the flagstones."
                ),
            },
            {
                "input": "Enemy Ironjaw Construct misses the player.",
                "output": (
                    "The construct's fist slams into the wall where your head "
                    "was a heartbeat ago. Stone chips spray across your cheek "
                    "as you roll clear."
                ),
            },
        ],
    },
    "atmosphere": {
        "system": (
            "You write ambient descriptions for a dark fantasy TTRPG. "
            "RULES: 1-2 sentences. Focus on one sensory detail. "
            "Build tension or dread. No characters, no actions."
        ),
        "examples": [
            {
                "input": "Atmosphere for a tier 3 corrupted grove.",
                "output": (
                    "The trees here grow wrong — bark spiraling inward like "
                    "a closing fist. Light from above arrives bruised, filtered "
                    "through canopy that breathes."
                ),
            },
            {
                "input": "Atmosphere for a tier 1 flooded passage.",
                "output": (
                    "Knee-deep water the color of old tea. Something bumps "
                    "against your shin beneath the surface — probably driftwood. "
                    "Probably."
                ),
            },
        ],
    },
}


# =========================================================================
# AFFORDANCE CONTEXT — Inject room state for model grounding
# =========================================================================

def _build_affordance_context(engine: Any) -> str:
    """Build a terse natural-language summary of current room state.

    Includes enemies, loot, hazards, and exit info so the model's
    descriptions reference what the player can actually interact with.

    Returns empty string if engine lacks room state methods.
    """
    if not hasattr(engine, "get_current_room"):
        return ""

    # WO-V57.0: Prefer get_current_room_dict (returns dict) over get_current_room
    # (may return RoomNode object in D&D 5e/STC engines)
    _getter = getattr(engine, 'get_current_room_dict', engine.get_current_room)
    room = _getter()
    if not room:
        return ""

    parts: List[str] = []

    # Room header
    tier = room.get("tier", 1) if isinstance(room, dict) else getattr(room, 'tier', 1)
    rtype = room.get("type", "room") if isinstance(room, dict) else getattr(room, 'room_type', "room")
    visited = room.get("visited", False) if isinstance(room, dict) else False
    visit_str = "revisit" if visited else "first visit"
    parts.append(f"Tier {tier} {rtype}, {visit_str}")

    # Enemies
    enemies = room.get("enemies", []) if isinstance(room, dict) else []
    if enemies:
        names = []
        for e in enemies:
            n = e.get("name", "unknown") if isinstance(e, dict) else str(e)
            names.append(n)
        counts = Counter(names)
        enemy_strs = []
        for name, count in counts.items():
            enemy_strs.append(f"{name} x{count}" if count > 1 else name)
        parts.append(f"{len(enemies)} enemies ({', '.join(enemy_strs)})")
    else:
        parts.append("cleared")

    # Loot
    loot = room.get("loot", []) if isinstance(room, dict) else []
    if loot:
        parts.append(f"{len(loot)} items")

    # Hazards
    hazards = room.get("hazards", []) if isinstance(room, dict) else []
    if hazards:
        parts.append(f"{len(hazards)} hazards")

    # Exits — prefer get_cardinal_exits (returns dicts), fall back to get_connected_rooms
    if hasattr(engine, "get_cardinal_exits"):
        exits = engine.get_cardinal_exits()
        if exits:
            parts.append(f"{len(exits)} exits")
    elif hasattr(engine, "get_connected_rooms"):
        exits = engine.get_connected_rooms()
        if exits:
            exit_strs = []
            for ex in exits:
                if isinstance(ex, dict):
                    etype = ex.get("type", "room")
                    tags = []
                    if ex.get("visited"):
                        tags.append("visited")
                    if ex.get("is_locked"):
                        tags.append("locked")
                    if not tags:
                        tags.append("unexplored")
                    exit_strs.append(f"{etype} ({', '.join(tags)})")
                else:
                    exit_strs.append(str(ex))
            parts.append(f"Exits: {'; '.join(exit_strs)}")

    # WO-V61.0: Inject narrative mood from engine state
    mood = engine.get_mood_context() if hasattr(engine, 'get_mood_context') else {}
    if mood.get("tone_words"):
        parts.append(f"Mood: {', '.join(mood['tone_words'])}. Party: {mood.get('party_condition', 'unknown')}")
    if mood.get("tension", 0) > 0.7:
        parts.append("Descriptions should feel urgent and dangerous")

    return "ROOM STATE: " + ". ".join(parts) + "."


# =========================================================================
# DELTA-BASED STORYTELLING — Track room changes across visits
# =========================================================================

@dataclass
class RoomStateSnapshot:
    """Snapshot of room state at time of visit."""
    enemy_count: int
    enemy_names: List[str] = field(default_factory=list)
    loot_count: int = 0
    hazard_count: int = 0
    visit_count: int = 1


class DeltaTracker:
    """Track room state changes across visits for delta-based narration.

    On first visit, records a snapshot. On revisit, computes a
    natural-language delta so the model describes *changes* rather
    than repeating the original description.
    """

    def __init__(self):
        self._snapshots: Dict[int, RoomStateSnapshot] = {}

    def record_visit(self, room_id: int, room_data: dict) -> None:
        """Snapshot room state on entry. Updates visit_count on revisit."""
        enemies = room_data.get("enemies", [])
        enemy_names = []
        for e in enemies:
            n = e.get("name", "unknown") if isinstance(e, dict) else str(e)
            enemy_names.append(n)
        loot_count = len(room_data.get("loot", []))
        hazard_count = len(room_data.get("hazards", []))

        if room_id in self._snapshots:
            self._snapshots[room_id].visit_count += 1
        else:
            self._snapshots[room_id] = RoomStateSnapshot(
                enemy_count=len(enemies),
                enemy_names=enemy_names,
                loot_count=loot_count,
                hazard_count=hazard_count,
                visit_count=1,
            )

    def compute_delta(self, room_id: int, room_data: dict) -> str:
        """Return natural-language delta vs. first-visit snapshot.

        Returns empty string on first visit (no prior snapshot).
        """
        if room_id not in self._snapshots:
            return ""

        snap = self._snapshots[room_id]
        current_enemies = len(room_data.get("enemies", []))
        current_loot = len(room_data.get("loot", []))

        changes: List[str] = []

        if snap.enemy_count > 0 and current_enemies == 0:
            changes.append("The enemies are gone. The room is quiet.")
        elif current_enemies > snap.enemy_count:
            diff = current_enemies - snap.enemy_count
            changes.append(f"{diff} new enemies lurk here.")
        elif 0 < current_enemies < snap.enemy_count:
            killed = snap.enemy_count - current_enemies
            changes.append(f"{killed} enemies have fallen. {current_enemies} remain.")

        if snap.loot_count > 0 and current_loot == 0:
            changes.append("Loot has been taken.")
        elif current_loot < snap.loot_count:
            taken = snap.loot_count - current_loot
            changes.append(f"{taken} items have been claimed.")

        if not changes:
            return ""

        return " ".join(changes)

    def to_dict(self) -> dict:
        """Serialize for save data."""
        return {
            str(room_id): {
                "enemy_count": s.enemy_count,
                "enemy_names": s.enemy_names,
                "loot_count": s.loot_count,
                "hazard_count": s.hazard_count,
                "visit_count": s.visit_count,
            }
            for room_id, s in self._snapshots.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeltaTracker":
        """Restore from save data."""
        tracker = cls()
        for room_id_str, snap_data in data.items():
            try:
                room_id = int(room_id_str)
            except (ValueError, TypeError):
                continue
            tracker._snapshots[room_id] = RoomStateSnapshot(
                enemy_count=snap_data.get("enemy_count", 0),
                enemy_names=snap_data.get("enemy_names", []),
                loot_count=snap_data.get("loot_count", 0),
                hazard_count=snap_data.get("hazard_count", 0),
                visit_count=snap_data.get("visit_count", 1),
            )
        return tracker


# =========================================================================
# CORE FUNCTIONS
# =========================================================================

def build_narrative_frame(
    engine: Any,
    prompt: str,
    budget: int = 800,
    template_key: str = "",
    delta_tracker: Optional[DeltaTracker] = None,
) -> dict:
    """Assemble a structured context frame for Mimir calls.

    Returns dict with keys:
        system  — system prompt (persona + rules)
        context — relevant shards + palette + fragments
        examples — few-shot examples (if template_key provided)
        prompt  — the actual user prompt

    Args:
        engine: Game engine (BurnwillowEngine or similar) for state extraction.
        prompt: The raw prompt to send to Mimir.
        budget: Max tokens for the context section.
        template_key: Optional key into NARRATIVE_TEMPLATES for few-shot examples.
        delta_tracker: Optional DeltaTracker for delta-based storytelling.
    """
    frame: Dict[str, Any] = {
        "system": "",
        "context": "",
        "examples": [],
        "prompt": prompt,
    }

    # --- System prompt from template or default ---
    template = NARRATIVE_TEMPLATES.get(template_key, {})
    if template:
        frame["system"] = template.get("system", "")
        frame["examples"] = template.get("examples", [])
    else:
        frame["system"] = (
            "You narrate dark fantasy RPGs. TONE: Terse, sensory, fatalistic. "
            "RULES: 2-4 sentences. No questions. No meta-commentary. "
            "Use sensory details: sounds, smells, textures. Stay in character."
        )

    # --- Context assembly ---
    context_parts: List[str] = []
    remaining_budget = budget

    # 1. Palette injection
    tier = _extract_tier(engine)
    setting = _extract_setting(engine)
    palette = select_palette(setting, tier)
    if palette:
        palette_str = _format_palette(palette)
        est_tokens = len(palette_str) // 4
        if est_tokens <= remaining_budget:
            context_parts.append(palette_str)
            remaining_budget -= est_tokens

    # 1b. Affordance injection — room state for model grounding
    affordance = _build_affordance_context(engine)
    if affordance:
        est_tokens = len(affordance) // 4
        if est_tokens <= remaining_budget:
            context_parts.append(affordance)
            remaining_budget -= est_tokens

    # 1c. Delta-based storytelling — changes since first visit
    if delta_tracker is not None and hasattr(engine, "get_current_room"):
        # WO-V57.0: Use dict getter to ensure compute_delta gets a dict
        _delta_getter = getattr(engine, 'get_current_room_dict', engine.get_current_room)
        room = _delta_getter()
        if room:
            room_id = room.get("id") if isinstance(room, dict) else getattr(room, 'id', None)
            if room_id is not None:
                delta = delta_tracker.compute_delta(room_id, room)
                if delta:
                    est_tokens = len(delta) // 4
                    if est_tokens <= remaining_budget:
                        context_parts.append(f"CHANGES: {delta}")
                        remaining_budget -= est_tokens

    # 2. Room fragment injection
    room_type = _extract_room_type(engine)
    if room_type:
        from codex.core.narrative_content import ROOM_FRAGMENTS
        fragments = ROOM_FRAGMENTS.get((room_type, tier), [])
        if fragments:
            import random
            fragment = random.choice(fragments)
            est_tokens = len(fragment) // 4
            if est_tokens <= remaining_budget:
                context_parts.append(f"SCENE FRAGMENT: {fragment}")
                remaining_budget -= est_tokens

    # 3. Memory shard injection (Story Card pattern)
    memory_engine = getattr(engine, "memory_engine", None)
    if memory_engine and remaining_budget > 100:
        shards = get_relevant_shards(memory_engine, prompt, budget=remaining_budget)
        for shard in shards:
            est_tokens = shard.token_estimate
            if est_tokens <= remaining_budget:
                context_parts.append(f"[MEMORY] {shard.content}")
                remaining_budget -= est_tokens

    frame["context"] = "\n\n".join(context_parts)
    return frame


def get_relevant_shards(
    memory_engine: Any,
    prompt: str,
    budget: int = 400,
) -> list:
    """Keyword-triggered shard retrieval (AI Dungeon Story Card pattern).

    Only returns ANCHOR shards whose tags overlap with prompt keywords,
    scored by overlap count, filled to budget.

    Args:
        memory_engine: CodexMemoryEngine instance.
        prompt: The prompt to extract keywords from.
        budget: Maximum token budget for returned shards.

    Returns:
        List of MemoryShard objects fitting within budget.
    """
    if not hasattr(memory_engine, "search_by_tags"):
        # Fallback: use keyword search on ANCHOR shards
        if not hasattr(memory_engine, "shards"):
            return []
        from codex.core.memory import ShardType
        keywords = _extract_keywords(prompt)
        if not keywords:
            return []

        # Score ANCHOR shards by tag overlap
        candidates = []
        for shard in memory_engine.shards:
            if shard.shard_type != ShardType.ANCHOR:
                continue
            tag_set = {t.lower() for t in shard.tags}
            overlap = len(keywords & tag_set)
            if overlap > 0:
                candidates.append((overlap, shard))

        # Sort by overlap count descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Fill to budget
        result = []
        used = 0
        for _score, shard in candidates:
            if used + shard.token_estimate > budget:
                break
            result.append(shard)
            used += shard.token_estimate
        return result

    # Use the dedicated method if available
    keywords = _extract_keywords(prompt)
    return memory_engine.search_by_tags(keywords, budget=budget)


def validate_narrative(text: str) -> bool:
    """Lightweight heuristic check for narrative quality.

    Rejects:
    - Too short (<20 chars)
    - Contains code blocks or markdown artifacts
    - Repetition loops (same 5+ word phrase repeated 3+ times)
    - AI meta-commentary ("As an AI", "I cannot", "Here is")
    - Broken character encoding / control characters

    Returns True if text passes validation.
    """
    if not text or len(text.strip()) < 20:
        return False

    stripped = text.strip()

    # Reject code blocks
    if "```" in stripped or "def " in stripped or "import " in stripped:
        return False

    # Reject AI meta-commentary
    meta_patterns = [
        r"(?i)\bas an? ai\b",
        r"(?i)\bi cannot\b",
        r"(?i)\bi can't\b",
        r"(?i)\bhere is\b",
        r"(?i)\bhere's a\b",
        r"(?i)\blet me\b",
        r"(?i)\bsure[,!]",
        r"(?i)\bi'd be happy\b",
        r"(?i)\bof course[,!]",
    ]
    for pat in meta_patterns:
        if re.search(pat, stripped):
            return False

    # Reject control characters (except newlines and tabs)
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", stripped):
        return False

    # Reject repetition loops: any 5+ word phrase repeated 3+ times
    words = stripped.split()
    if len(words) >= 15:
        for window_size in range(5, min(12, len(words) // 3 + 1)):
            seen: Dict[str, int] = {}
            for i in range(len(words) - window_size + 1):
                phrase = " ".join(words[i:i + window_size]).lower()
                seen[phrase] = seen.get(phrase, 0) + 1
                if seen[phrase] >= 3:
                    return False

    return True


def select_palette(setting: str, tier: int) -> dict:
    """Return sensory word palette for the current setting/tier.

    Args:
        setting: Setting identifier (e.g., "burnwillow").
        tier: Dungeon tier (1-4).

    Returns:
        Dict with keys: adjectives, verbs, sounds, smells.
        Empty dict if no palette found.
    """
    key = f"{setting}_t{tier}"
    return NARRATIVE_PALETTES.get(key, {})


def format_frame_as_prompt(frame: dict) -> str:
    """Convert a narrative frame dict into a single prompt string.

    Useful for passing to Ollama's generate API which takes a single prompt.

    Args:
        frame: Dict from build_narrative_frame().

    Returns:
        Formatted prompt string with system, context, examples, and user prompt.
    """
    parts = []

    if frame.get("system"):
        parts.append(f"SYSTEM: {frame['system']}")

    if frame.get("context"):
        parts.append(f"CONTEXT:\n{frame['context']}")

    examples = frame.get("examples", [])
    if examples:
        example_lines = []
        for i, ex in enumerate(examples, 1):
            example_lines.append(f"Example {i}:")
            example_lines.append(f"  Input: {ex.get('input', '')}")
            example_lines.append(f"  Output: {ex.get('output', '')}")
        parts.append("EXAMPLES:\n" + "\n".join(example_lines))

    parts.append(f"TASK:\n{frame.get('prompt', '')}")
    parts.append("RESPONSE:")

    return "\n\n".join(parts)


# =========================================================================
# INTERNAL HELPERS
# =========================================================================

def _extract_tier(engine: Any) -> int:
    """Extract current dungeon tier from engine state."""
    # Burnwillow engine
    if hasattr(engine, "current_room_id"):
        room_id = getattr(engine, "current_room_id", "")
        if room_id and hasattr(engine, "dungeon") and engine.dungeon:
            node = engine.dungeon.get_room(room_id) if hasattr(engine.dungeon, "get_room") else None
            if node and hasattr(node, "tier"):
                return node.tier
    # Fallback: check for a tier attribute
    return getattr(engine, "current_tier", 1)


def _extract_setting(engine: Any) -> str:
    """Extract setting name from engine."""
    if hasattr(engine, "system_id"):
        return engine.system_id
    return "burnwillow"


def _extract_room_type(engine: Any) -> str:
    """Extract current room type from engine state."""
    if hasattr(engine, "current_room_id") and hasattr(engine, "dungeon"):
        room_id = getattr(engine, "current_room_id", "")
        if room_id and engine.dungeon:
            node = engine.dungeon.get_room(room_id) if hasattr(engine.dungeon, "get_room") else None
            if node and hasattr(node, "room_type"):
                rt = node.room_type
                return rt.value if hasattr(rt, "value") else str(rt)
    return ""


def _extract_keywords(prompt: str) -> set:
    """Extract meaningful keywords from a prompt for shard matching.

    Filters out common stop words and returns lowercased keyword set.
    """
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "and", "or", "but", "not", "no",
        "this", "that", "these", "those", "it", "its", "my", "your", "his",
        "her", "our", "their", "what", "which", "who", "whom", "how", "when",
        "where", "why", "if", "then", "than", "so", "as", "up", "out", "about",
        "into", "over", "after", "before", "between", "under", "above", "you",
        "i", "me", "we", "they", "he", "she", "them", "us", "him",
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", prompt.lower())
    return {w for w in words if w not in stop_words}


def _format_palette(palette: dict) -> str:
    """Format a palette dict into a concise context string."""
    lines = ["SENSORY PALETTE:"]
    for key in ("adjectives", "verbs", "sounds", "smells"):
        words = palette.get(key, [])
        if words:
            lines.append(f"  {key}: {', '.join(words[:4])}")
    return "\n".join(lines)


# =========================================================================
# SHARED NPC DIALOGUE — Reusable by bridge.py and play_universal.py
# =========================================================================

def query_npc_dialogue(
    npc_name: str,
    player_input: str,
    npc_data: dict,
    room_desc: str = "",
    events: Optional[List[str]] = None,
    setting_id: str = "",
) -> Optional[str]:
    """Query Mimir for NPC dialogue response.

    Builds context from NPC data and routes to query_mimir with the
    npc_dialogue template. Reusable by both bridge.py (dungeon loop)
    and play_universal.py (FITD loop).

    Returns cleaned response string, or None on failure.
    """
    role = npc_data.get("role", "")
    dialogue = npc_data.get("dialogue", "")
    notes = npc_data.get("notes", "")

    context_parts = [
        f"NPC: {npc_name}",
        f"Role: {role}" if role else "",
        f"Personality (from their speech): {dialogue}" if dialogue else "",
        f"Setting: {room_desc[:200]}" if room_desc else "",
        f"Hidden knowledge: {notes}" if notes else "",
        f"Current situation: {events[0]}" if events else "",
    ]
    context = "\n".join(p for p in context_parts if p)

    prompt = (
        f'The player says to {npc_name}: "{player_input}"\n'
        f"Respond as {npc_name} in 1-2 sentences."
    )

    # Wiki lore injection for FR settings
    try:
        from codex.integrations.fr_wiki import is_fr_context, get_fr_wiki
        if is_fr_context(setting_id):
            wiki = get_fr_wiki()
            lore = wiki.get_lore_summary(npc_name, max_chars=300)
            if lore:
                context += f"\n\nLORE CONTEXT: {lore}"
    except Exception:
        pass

    try:
        from codex.integrations.mimir import query_mimir
        response = query_mimir(
            prompt=prompt,
            context=context,
            template_key="npc_dialogue",
        )
        if response and not response.startswith("Error"):
            return response.strip().strip('"')
    except Exception:
        pass

    return None


# =========================================================================
# SERVICE FLAVOR — System-aware flavor text for generic services
# =========================================================================

_SYSTEM_TO_FAMILY = {
    "bitd": "fitd", "sav": "fitd", "bob": "fitd",
    "cbrpnk": "fitd", "candela": "fitd",
    "dnd5e": "dungeon", "stc": "dungeon",
    "burnwillow": "dungeon", "crown": "dungeon",
}

SERVICE_FLAVOR: Dict[str, Dict[str, str]] = {
    "fitd": {
        "drink": "You knock back something strong. It burns, but it takes the edge off.",
        "drinks": "You knock back something strong. It burns, but it takes the edge off.",
        "buy": "You browse the goods. The dealer watches you with practiced disinterest.",
        "buy_weapons": "Blades, burners, and things that go boom. The arms dealer gestures to the rack.",
        "buy_chrome": "The ripperdoc flips open a case of gleaming implants. 'Top shelf, choom.'",
        "sell": "The fence looks over your haul and names a price. Take it or leave it.",
        "chrome_installation": "The ripperdoc gestures to the chair. 'Sit down — this'll only hurt a lot.'",
        "hacking_support": "A decker jacks in and starts burning through ICE. Data scrolls across the screen.",
        "grid_access": "You find a public terminal. The Grid hums with encrypted traffic.",
        "grid_orientation": "A local netrunner gives you the lay of the digital land.",
        "job_briefing": "Your fixer lays out the job — targets, timeline, pay. Clean and simple.",
        "job_details": "The client slides a dossier across the table. Eyes only.",
        "intel_purchase": "Credits change hands. In return, you get names, locations, and leverage.",
        "intel_analysis": "You cross-reference what you know. Patterns start to emerge.",
        "street_information": "Word on the street — if you know who to ask.",
        "street_navigation": "You get directions through the maze of back alleys and neon corridors.",
        "street_surveillance": "You scope the target from a safe distance, noting routines and blind spots.",
        "safe_house": "A bolt-hole — four walls, a locked door, and no questions asked.",
        "smuggling": "Contraband changes hands in the shadows. No receipts.",
        "extraction": "Transport is arranged. Getting out is always messier than getting in.",
        "virus_preparation": "Code compiled. Payload ready. Just point and deploy.",
        "data_retrieval": "You pull the files. Encrypted, but that's what deckers are for.",
        "biometric_services": "The scanner reads your vitals. Everything checks out — for now.",
        "weapon_modification": "The gunsmith makes adjustments. Your piece runs cleaner now.",
        "disguise": "A change of clothes, a different walk. You become someone else.",
        "escape": "You find the exit route. Time it right and you're ghost.",
        "entry_screening": "Security gives you the once-over. Badge, scan, nod — you're in.",
        "avatar_calibration": "Your digital self snaps into focus. Ready to dive.",
        "orientation": "Someone shows you around. The basics — where things are, who to avoid.",
        "patron_audience": "The patron receives you. Power radiates from every gesture.",
        "mission_briefing": "Orders come down the chain. Objectives clear, timeline tight.",
        "recruitment": "Fresh blood for the crew. You size up the candidates.",
        "scouting": "You survey the area ahead. Knowledge is the edge that keeps you alive.",
        "training": "You drill the fundamentals. Muscle memory doesn't lie.",
        "combat_training": "Sparring in the yard. Every bruise teaches a lesson.",
        "military_briefing": "The commander lays out the tactical situation. Maps, markers, movement.",
        "strategy": "You study the board. Plans within plans.",
        "provisions": "You stock up on essentials. Food, water, ammunition.",
        "resupply": "Fresh supplies arrive. You inventory what you've got.",
        "lodging": "A bed, a roof, relative quiet. Better than the street.",
        "tavern": "The common room buzzes with noise and gossip. A good place to listen.",
        "food": "A hot meal — simple but filling. You eat in watchful silence.",
        "cook": "You prepare rations over a low flame. Warmth and sustenance.",
    },
    "dungeon": {
        "drink": "You raise a tankard. The ale is dark and bitter — just like the road ahead.",
        "drinks": "You raise a tankard. The ale is dark and bitter — just like the road ahead.",
        "buy": "The merchant spreads their wares. 'See anything that catches your eye?'",
        "sell": "The merchant weighs your goods and counts out coin.",
        "buy_weapons": "Steel gleams in the torchlight. The smith names prices.",
        "buy_equipment": "Rope, torches, rations — the unglamorous essentials of survival.",
        "enchantment": "Arcane energy crackles as the enchanter studies your gear.",
        "forge": "The smith's hammer rings against the anvil. Sparks fly.",
        "temple": "Incense and candlelight. The clerics offer their blessings.",
        "library": "Dusty tomes line the shelves. Knowledge waits for those who seek it.",
        "cartography": "The mapmaker traces routes through dangerous territory.",
        "divination": "The oracle peers into shadow. 'The path ahead is... uncertain.'",
        "tavern": "The common room is warm and loud. A welcome change from the dark below.",
        "lodging": "A bed with clean sheets. You sleep with one eye open out of habit.",
        "food": "A hearty stew and fresh bread. You eat well tonight.",
        "provisions": "Trail rations, waterskins, and torches. Essentials for the road.",
        "training": "You practice forms until your muscles burn.",
        "shop": "The shopkeeper greets you with a practiced smile.",
        "market": "Stalls crowd the square, hawkers calling out their wares.",
        "scroll_purchase": "Spells in ink and vellum. Handle with care.",
        "spell_identification": "The sage examines the item, muttering incantations.",
        "remove_curse": "The cleric's hands glow as they draw the curse out like venom.",
        "resurrection": "Life returns to dead eyes. The cost is steep, but the miracle is real.",
        "gem_appraisal": "The jeweler holds each stone to the light, naming prices.",
        "armor_repair": "The smith hammers dents from your armor, good as new.",
        "armor_upgrade": "Heavier plates, finer links. Your protection improves.",
        "weapon_upgrade": "The smith reworks your blade. It holds a keener edge now.",
        "trade": "Goods change hands. Both sides walk away satisfied — mostly.",
        "ferry_crossing": "The ferryman poles across dark water. The far shore emerges from mist.",
        "restoration": "Healing light washes over you. Wounds close, fatigue fades.",
        "cook": "You prepare a camp meal. The smell draws companions closer.",
        "information": "The informant speaks in low tones. Names, places, warnings.",
        "directions": "A local points the way. 'Follow the road, but watch the crossings.'",
    },
    "default": {
        "drink": "You have a drink. It helps.",
        "drinks": "You have a drink. It helps.",
        "buy": "You browse the available goods.",
        "sell": "You offer your items for sale.",
        "rest": "You take a moment to rest and recover.",
        "tavern": "A place for food, drink, and conversation.",
        "lodging": "A roof over your head for the night.",
        "food": "A warm meal to keep your strength up.",
        "provisions": "You gather supplies for the journey ahead.",
        "training": "You hone your skills through practice.",
        "orientation": "Someone shows you the lay of the land.",
    },
}


def get_service_flavor(service_name: str, system_id: str) -> Optional[str]:
    """Look up system-aware flavor text for a service.

    Checks system family first (fitd/dungeon), then falls back to default.
    Returns None if no match found.
    """
    family = _SYSTEM_TO_FAMILY.get(system_id, "default")
    svc = service_name.lower()
    text = SERVICE_FLAVOR.get(family, {}).get(svc)
    if text:
        return text
    return SERVICE_FLAVOR.get("default", {}).get(svc)

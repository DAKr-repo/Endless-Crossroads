"""
codex/games/burnwillow/autopilot.py - AI Companion & Autopilot System
=====================================================================

Provides heuristic-driven AI decision-making for:
  - Full autopilot mode (AI plays all characters)
  - Companion mode (AI controls party member #2)

Decision architecture:
  - decide_*() methods are pure heuristics (no LLM call in hot loop)
  - Companion dialogue uses llama3.2:1b via talk_to_npc() for quality
  - Combat narration continues using mimir for speed

Voice separation:
  DECISION_MODEL = "llama3.2:1b"   — Calculates tactics (dialogue only)
  NARRATION_MODEL = "mimir"         — Narrates results (qwen2.5:0.5b)

WO-V31.0: The Sovereign Triad — Phase 1B
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from codex.games.burnwillow.engine import (
    Character, GearSlot, GearTier, GearItem, StatType,
    roll_4d6_drop_lowest, calculate_stat_mod, create_starter_gear,
    BurnwillowEngine,
)

# =============================================================================
# MODEL CONFIG — Voice Separation
# =============================================================================

DECISION_MODEL = "llama3.2:1b"    # Calculates tactics (dialogue only)
NARRATION_MODEL = "mimir"          # Narrates results (qwen2.5:0.5b)


# =============================================================================
# COMPANION PERSONALITY
# =============================================================================

@dataclass
class CompanionPersonality:
    """Personality profile for an AI-controlled companion."""
    archetype: str          # "vanguard", "scholar", "scavenger", "healer"
    description: str        # For Mimir narration prompts
    quirk: str              # Character flavor
    aggression: float       # 0.0-1.0
    curiosity: float        # 0.0-1.0
    caution: float          # 0.0-1.0

    def to_dict(self) -> dict:
        return {
            "archetype": self.archetype,
            "description": self.description,
            "quirk": self.quirk,
            "aggression": self.aggression,
            "curiosity": self.curiosity,
            "caution": self.caution,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompanionPersonality":
        return cls(**data)


PERSONALITY_POOL: List[CompanionPersonality] = [
    CompanionPersonality(
        archetype="vanguard",
        description="A battle-hardened warrior who charges headfirst into danger.",
        quirk="Hums battle hymns under their breath.",
        aggression=0.9, curiosity=0.3, caution=0.1,
    ),
    CompanionPersonality(
        archetype="scholar",
        description="A curious arcanist who examines everything and fights reluctantly.",
        quirk="Catalogues every monster encountered in a tiny journal.",
        aggression=0.2, curiosity=0.9, caution=0.6,
    ),
    CompanionPersonality(
        archetype="scavenger",
        description="A wiry opportunist who loots first and asks questions never.",
        quirk="Always pocketing small objects 'for later'.",
        aggression=0.5, curiosity=0.7, caution=0.4,
    ),
    CompanionPersonality(
        archetype="healer",
        description="A calm field medic who prioritizes keeping allies alive.",
        quirk="Whispers apologies to enemies before killing them.",
        aggression=0.2, curiosity=0.4, caution=0.8,
    ),
]

COMPANION_NAME_POOL: List[str] = [
    "Bryn", "Theron", "Isolde", "Corwin",
    "Neve", "Aldric", "Petra", "Caelum",
    "Selene", "Hadrik", "Yenna", "Torvin",
]

# Archetype -> engine loadout mapping
_ARCHETYPE_LOADOUT = {
    "vanguard": "vanguard",
    "scholar": "scholar",
    "scavenger": "sellsword",
    "healer": "sentinel",
}


# =============================================================================
# AI CHARACTER FACTORY
# =============================================================================

def create_ai_character(
    seed: Optional[int] = None,
    archetype: Optional[str] = None,
    name: Optional[str] = None,
) -> Tuple[CompanionPersonality, str, Dict[str, int], str, str]:
    """Create a fully realized AI companion character.

    Uses seeded RNG for determinism.

    Args:
        seed: Random seed for reproducibility.
        archetype: Force a specific archetype. Random if None.
        name: Force a specific name. Random if None.

    Returns:
        (personality, name, stats_dict, loadout_id, biography)
    """
    rng = random.Random(seed)

    # Select personality
    if archetype:
        pool = [p for p in PERSONALITY_POOL if p.archetype == archetype]
        personality = pool[0] if pool else rng.choice(PERSONALITY_POOL)
    else:
        personality = rng.choice(PERSONALITY_POOL)

    # Select name
    char_name = name or rng.choice(COMPANION_NAME_POOL)

    # Roll 4d6-drop-lowest stats (capitalized keys match init_game expectations)
    stats = {
        "Might": sum(sorted([rng.randint(1, 6) for _ in range(4)])[1:]),
        "Wits": sum(sorted([rng.randint(1, 6) for _ in range(4)])[1:]),
        "Grit": sum(sorted([rng.randint(1, 6) for _ in range(4)])[1:]),
        "Aether": sum(sorted([rng.randint(1, 6) for _ in range(4)])[1:]),
    }

    # Map archetype to engine loadout
    loadout_id = _ARCHETYPE_LOADOUT.get(personality.archetype, "sellsword")

    # Roll biography from LIFEPATH_TABLES
    biography = _roll_biography(rng)

    return (personality, char_name, stats, loadout_id, biography)


def create_backfill_companions(
    count: int,
    existing_names: Optional[List[str]] = None,
    seed: Optional[int] = None,
) -> List[Tuple[CompanionPersonality, str, Dict[str, int], str, str]]:
    """Create N AI companion characters for party backfill (WO-V32.0).

    Avoids duplicate names with existing party members and uses
    sequential seeds for determinism.

    Args:
        count: Number of companions to create (1-4).
        existing_names: Names already in the party (to avoid duplicates).
        seed: Base seed for RNG. Each companion gets seed+i.

    Returns:
        List of (personality, name, stats_dict, loadout_id, biography) tuples.
    """
    existing = set(existing_names or [])
    results = []
    base_seed = seed if seed is not None else random.randint(0, 999999)
    for i in range(count):
        personality, name, stats, loadout, bio = create_ai_character(seed=base_seed + i)
        # Avoid name collisions
        while name in existing:
            base_seed += 100
            personality, name, stats, loadout, bio = create_ai_character(seed=base_seed + i)
        existing.add(name)
        results.append((personality, name, stats, loadout, bio))
    return results


def _roll_biography(rng: random.Random) -> str:
    """Generate a procedural biography from lifepath tables."""
    try:
        from codex.forge.loot_tables import LIFEPATH_TABLES
        origin = rng.choice(LIFEPATH_TABLES["origins"])
        parents = rng.choice(LIFEPATH_TABLES["parents"])
        upbringing = rng.choice(LIFEPATH_TABLES["upbringing"])
        event = rng.choice(LIFEPATH_TABLES["life_events"])
        bond = rng.choice(LIFEPATH_TABLES["bonds"])
        return (
            f"From {origin}. {parents}. "
            f"Raised with {upbringing.lower()}. "
            f"{event}. "
            f"Driven by {bond.lower()}."
        )
    except (ImportError, KeyError):
        return "A wanderer with a mysterious past."


# =============================================================================
# AUTOPILOT AGENT
# =============================================================================

@dataclass
class AutopilotAgent:
    """Heuristic decision engine for AI-controlled characters."""
    personality: CompanionPersonality
    biography: str = ""

    def decide_exploration(self, snapshot: dict) -> str:
        """Decide exploration action based on current state.

        Priority chain:
        1. HP critical -> bind wounds
        2. Loot available -> loot
        3. Enemies present -> attack (triggers combat)
        4. Room has interactive -> interact
        5. Unsearched room -> search
        6. Move to unvisited connected room
        7. BFS to nearest unvisited
        8. End turn

        Args:
            snapshot: Dict from build_exploration_snapshot()

        Returns:
            Command string (e.g. "bind", "loot", "move 5", "search")
        """
        hp_pct = snapshot.get("hp_pct", 1.0)
        enemies = snapshot.get("enemies", [])
        loot = snapshot.get("loot", [])
        searched = snapshot.get("searched", False)
        exits = snapshot.get("exits", [])
        has_interactive = snapshot.get("has_interactive", False)

        # 1. Emergency heal
        if hp_pct < 0.4:
            return "bind"

        # 2. Combat if enemies present
        if enemies:
            return "attack"

        # 3. Loot if available
        if loot:
            return "loot"

        # 4. Interact with objects
        if has_interactive and self.personality.curiosity > 0.5:
            return "interact"

        # 5. Search unsearched rooms (curiosity-driven)
        if not searched and self.personality.curiosity > 0.3:
            return "search"

        # 6. Move to unvisited connected room
        unvisited = [e for e in exits if not e.get("visited")]
        if unvisited:
            # Prefer unlocked, lowest-tier rooms for cautious, highest for aggressive
            if self.personality.caution > 0.5:
                target = min(unvisited, key=lambda e: e.get("tier", 1))
            else:
                target = max(unvisited, key=lambda e: e.get("tier", 1))
            if not target.get("is_locked"):
                return f"move {target['id']}"

        # 7. Move to any connected room (BFS would be expensive, just pick visited)
        unlocked = [e for e in exits if not e.get("is_locked")]
        if unlocked:
            return f"move {unlocked[0]['id']}"

        # 8. No options
        return "end"

    def decide_combat(self, snapshot: dict, bond: float = 0.0) -> str:
        """Decide combat action based on current state.

        Priority chain (healer):
        1. Ally critically wounded -> triage
        2. Self critically wounded -> guard
        3. Has [Intercept] and ally wounded -> intercept
        4. Has [Bolster] and allies present -> bolster <ally>
        5. Has [Command] and allies present -> command <ally>
        6. Attack weakest enemy

        Priority chain (vanguard):
        1. Self critically wounded -> guard
        2. Attack weakest enemy

        Args:
            snapshot: Dict from build_combat_snapshot()
            bond: Bond score (-1.0 to +1.0) for reluctant ally behavior.

        Returns:
            Command string (e.g. "attack 0", "guard", "triage Kael")
        """
        hp_pct = snapshot.get("hp_pct", 1.0)
        enemies = snapshot.get("enemies", [])
        allies = snapshot.get("allies", [])
        traits = list(snapshot.get("traits", []))
        char_name = snapshot.get("char_name", "")

        # WO-V62.0: Reluctant ally behavior at negative bond
        if bond < -0.3:
            traits = [t for t in traits if t not in ("[Command]", "[Bolster]")]
        if bond < -0.5 and random.random() < 0.15:
            if enemies:
                return f"attack {random.randint(0, len(enemies) - 1)}"
            return "guard"
        if bond < 0 and hp_pct < 0.35:
            return "guard"

        # Find target using tactical selection
        target_idx = select_ai_target(snapshot)

        # WO-V62.0: Gear-aware decisions
        equipped = snapshot.get("equipped_traits", [])
        has_aoe = any(t in equipped for t in ["[Shockwave]", "[Whirlwind]", "[Cleave]"])
        if has_aoe and len(enemies) >= 3 and self.personality.aggression > 0.4:
            return f"attack {target_idx}"  # Prefer attack with AoE gear

        if hp_pct < 0.25 and snapshot.get("has_healing_item"):
            return "use healing"

        # Healer/cautious behavior
        if self.personality.archetype == "healer" or self.personality.caution > 0.6:
            # Check allies for critical wounds
            wounded_ally = None
            for ally in allies:
                if ally["hp_pct"] < 0.35 and ally["name"] != char_name:
                    wounded_ally = ally
                    break

            if wounded_ally and "[Triage]" in traits:
                return f"triage {wounded_ally['name']}"

            if hp_pct < 0.25:
                return "guard"

            if wounded_ally and "[Bolster]" in traits:
                return f"bolster {wounded_ally['name']}"

        # Self-preservation for all archetypes
        if hp_pct < 0.2:
            return "guard"

        # Aggressive archetypes
        if self.personality.aggression > 0.7:
            if "[Command]" in traits and allies and random.random() < 0.3:
                other = [a for a in allies if a["name"] != char_name]
                if other:
                    return f"command {other[0]['name']}"

        # Intercept for defenders
        if "[Intercept]" in traits and any(a["hp_pct"] < 0.5 for a in allies):
            return "intercept"

        # Default: attack optimal target
        return f"attack {target_idx}"

    def decide_hub(self, snapshot: dict) -> str:
        """Decide hub action based on needs and personality.

        Args:
            snapshot: Dict with current_room_type, exits info, hp_pct, has_forge.

        Returns:
            Command string.
        """
        room_type = snapshot.get("room_type", "")
        hp_pct = snapshot.get("hp_pct", 1.0)

        # WO-V62.0: Need-based hub decisions
        if hp_pct < 0.5 and room_type == "temple":
            return "heal"
        if hp_pct < 0.5:
            # Navigate to healer
            exits = snapshot.get("exits", [])
            for exit_info in exits:
                if exit_info.get("type") in ("temple", "healer"):
                    return exit_info.get("direction", "s")

        # Personality-driven service use
        if room_type == "library" and self.personality.archetype == "scholar":
            return "study"
        if room_type == "shop" and self.personality.archetype == "scavenger":
            return "browse"
        if room_type == "forge" and snapshot.get("has_upgradeable_gear"):
            return "forge"

        if room_type == "town_gate":
            return "descend"

        # Navigate toward the gate
        exits = snapshot.get("exits", [])
        for exit_info in exits:
            if exit_info.get("type") == "town_gate":
                return exit_info.get("direction", "s")

        # Just move in a direction
        if exits:
            return exits[0].get("direction", "s")

        return "descend"

    def to_dict(self) -> dict:
        return {
            "personality": self.personality.to_dict(),
            "biography": self.biography,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AutopilotAgent":
        return cls(
            personality=CompanionPersonality.from_dict(data["personality"]),
            biography=data.get("biography", ""),
        )


# =============================================================================
# ENEMY ORCHESTRATION — Tactical Target Selection
# =============================================================================

def select_ai_target(snapshot: dict) -> int:
    """Select optimal enemy target based on tactical heuristics.

    Priority:
    1. Finish off wounded enemies (< 30% HP)
    2. Thin packs (same type, >2 of them)
    3. Target enemies threatening wounded allies
    4. Weakest enemy first (by current HP)
    5. Bosses targeted last (unless low HP)

    Args:
        snapshot: Combat snapshot dict with 'enemies' list.

    Returns:
        Index of the target enemy.
    """
    enemies = snapshot.get("enemies", [])
    if not enemies:
        return 0
    if len(enemies) == 1:
        return 0

    scored: List[Tuple[int, float]] = []

    # Count enemy types for pack detection
    type_counts: Dict[str, int] = {}
    for e in enemies:
        name = e.get("name", "")
        type_counts[name] = type_counts.get(name, 0) + 1

    for i, enemy in enumerate(enemies):
        score = 0.0
        hp = enemy.get("hp", 1)
        max_hp = enemy.get("max_hp", hp)
        hp_pct = hp / max(1, max_hp)
        is_boss = enemy.get("is_boss", False)
        name = enemy.get("name", "")

        # 1. Finish off wounded (high priority)
        if hp_pct < 0.3:
            score += 50

        # 2. Low HP in general
        score += (1.0 - hp_pct) * 20

        # 3. Pack thinning bonus
        if type_counts.get(name, 0) > 2:
            score += 15

        # 4. Bosses last (unless wounded)
        if is_boss and hp_pct > 0.3:
            score -= 30
        elif is_boss and hp_pct <= 0.3:
            score += 40  # Finish the boss!

        # 5. Lower tier enemies are easier kills
        tier = enemy.get("tier", 1)
        if tier <= 2:
            score += 5

        scored.append((i, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


# =============================================================================
# COMPANION NPC REGISTRATION
# =============================================================================

def register_companion_as_npc(
    engine: BurnwillowEngine,
    name: str,
    personality: CompanionPersonality,
    biography: str,
    narrative_engine=None,
    memory_manager=None,
) -> None:
    """Register an AI companion as an NPC for dialogue purposes.

    Creates NPC instance and appends to narrative_engine.npcs.
    Enables talk_to_npc(name) with full Mimir dialogue pipeline.

    Args:
        engine: The game engine instance.
        name: Companion character name.
        personality: CompanionPersonality dataclass.
        biography: Generated biography string.
        narrative_engine: Optional NarrativeEngine instance.
        memory_manager: Optional NPCMemoryManager instance.
    """
    if narrative_engine is None:
        return

    try:
        from codex.core.narrative_engine import NPC
    except ImportError:
        return

    npc = NPC(
        name=name,
        role="companion",
        description=f"{personality.description} {personality.quirk}",
        location="party",
        dialogue_greeting=f"*{name} adjusts their gear.* What do you need?",
        dialogue_quest="I go where you go. Lead on.",
        dialogue_rumor=f"*{name} glances around.* I've heard things... in the dark.",
    )

    # Avoid duplicates
    existing_names = {n.name for n in narrative_engine.npcs}
    if name not in existing_names:
        narrative_engine.npcs.append(npc)

    # Register in memory manager if available
    if memory_manager and hasattr(memory_manager, 'register_npc'):
        try:
            memory_manager.register_npc(name, role="companion")
        except Exception:
            pass


# =============================================================================
# SNAPSHOT BUILDERS
# =============================================================================

def build_exploration_snapshot(state) -> dict:
    """Convert GameState to a plain dict for the exploration decision engine.

    Keeps engine/view boundary clean — no GameState in autopilot module.

    Args:
        state: GameState instance from play_burnwillow.

    Returns:
        Dict with keys: hp_pct, enemies, loot, searched, exits, has_interactive,
        current_room_id, visited_rooms.
    """
    engine = state.engine
    char = state.active_leader or state.character
    room_id = state.current_room_id

    hp_pct = 1.0
    if char:
        hp_pct = char.current_hp / max(1, char.max_hp)

    enemies = state.room_enemies.get(room_id, []) if room_id is not None else []
    loot = state.room_loot.get(room_id, []) if room_id is not None else []
    searched = room_id in state.searched_rooms if room_id is not None else False

    # Get exits
    exits = []
    if engine:
        exits = engine.get_cardinal_exits()

    # Check for interactive objects
    furniture = state.room_furniture.get(room_id, []) if room_id is not None else []
    has_interactive = bool(furniture)

    return {
        "hp_pct": hp_pct,
        "enemies": enemies,
        "loot": loot,
        "searched": searched,
        "exits": exits,
        "has_interactive": has_interactive,
        "current_room_id": room_id,
    }


def build_combat_snapshot(state, char: Character) -> dict:
    """Convert GameState + character to a plain dict for combat decisions.

    Args:
        state: GameState instance.
        char: The Character whose turn it is.

    Returns:
        Dict with keys: hp_pct, enemies, allies, traits, char_name.
    """
    room_id = state.current_room_id
    enemies = state.room_enemies.get(room_id, []) if room_id is not None else []

    # Build ally info
    allies = []
    if state.engine:
        for c in state.engine.get_active_party():
            allies.append({
                "name": c.name,
                "hp": c.current_hp,
                "max_hp": c.max_hp,
                "hp_pct": c.current_hp / max(1, c.max_hp),
            })

    # Collect traits from equipped gear
    traits = []
    if char and char.gear:
        for item in char.gear.slots.values():
            if item and item.special_traits:
                traits.extend(item.special_traits)

    # WO-V62.0: Gear-aware fields
    equipped_traits = list(traits)  # Already collected above
    has_healing_item = False
    if char and hasattr(char, 'inventory'):
        for inv_item in getattr(char, 'inventory', []):
            if isinstance(inv_item, dict) and 'heal' in inv_item.get('name', '').lower():
                has_healing_item = True
                break
            elif hasattr(inv_item, 'name') and 'heal' in inv_item.name.lower():
                has_healing_item = True
                break

    return {
        "hp_pct": char.current_hp / max(1, char.max_hp) if char else 1.0,
        "enemies": enemies,
        "allies": allies,
        "traits": traits,
        "char_name": char.name if char else "",
        "equipped_traits": equipped_traits,
        "has_healing_item": has_healing_item,
    }


def build_hub_snapshot(state) -> dict:
    """Convert GameState to a dict for hub navigation decisions.

    Args:
        state: GameState instance.

    Returns:
        Dict with room_type and exits.
    """
    room_type = ""
    exits = []

    if state.in_settlement and state.settlement_graph:
        try:
            from codex.spatial.map_engine import RoomNode
            # Get current room type
            room = None
            if state.settlement_pos and state.settlement_graph:
                for rid, r in state.settlement_graph.rooms.items():
                    if (r.x <= state.settlement_pos[0] < r.x + r.width and
                            r.y <= state.settlement_pos[1] < r.y + r.height):
                        room = r
                        break
            if room:
                room_type = room.room_type if isinstance(room.room_type, str) else room.room_type.value
                for conn_id in room.connections:
                    target = state.settlement_graph.rooms.get(conn_id)
                    if target:
                        t_type = target.room_type if isinstance(target.room_type, str) else target.room_type.value
                        exits.append({
                            "id": conn_id,
                            "type": t_type,
                            "direction": "s",  # simplified
                        })
        except (ImportError, AttributeError):
            pass

    # WO-V62.0: Add companion needs
    hp_pct = 1.0
    has_upgradeable_gear = False
    if state.engine and state.engine.party:
        for c in state.engine.party:
            if c.name in (state.autopilot_agents or {}):
                hp_pct = c.current_hp / max(1, c.max_hp)
                if c.gear:
                    for item in c.gear.slots.values():
                        if item and hasattr(item.tier, 'value') and item.tier.value < 3:
                            has_upgradeable_gear = True
                            break
                break

    return {
        "room_type": room_type,
        "exits": exits,
        "hp_pct": hp_pct,
        "has_upgradeable_gear": has_upgradeable_gear,
    }

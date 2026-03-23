"""
codex.core.services.narrative_bridge
=====================================

Universal adapter that wires config content (bestiary descriptions,
loot flavor text, hazard descriptions, atmospheric sensory palettes)
into gameplay output for ALL game systems.

No LLM calls — pure config lookups with lazy-loaded name→description
indexes. Each ``NarrativeBridge`` instance is per-session, tracks
first-encounter display for enemies, and delegates to system-specific
atmosphere layers when available.
"""

import json
import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "config"

# Palette key mapping for non-Burnwillow systems
# Maps system_id → palette prefix in NARRATIVE_PALETTES
_PALETTE_MAP: Dict[str, str] = {
    "burnwillow": "burnwillow",
    "dnd5e": "burnwillow",      # Generic fantasy — reuse T1-T4
    "stc": "burnwillow",        # Epic fantasy — reuse
    "bitd": "burnwillow",       # Gothic industrial — T1/T2 fit
    "sav": "burnwillow",
    "bob": "burnwillow",
    "cbrpnk": "burnwillow",
    "candela": "burnwillow",    # Gothic noir — T2/T4 fit
    "crown": "burnwillow",
    "ashburn": "burnwillow",
}


def _load_config_index(config_type: str, system_id: str) -> Dict[str, str]:
    """Load a config JSON and build a {name.lower(): description} index.

    Handles the standard tiered format: {"tiers": {"1": [...], "2": [...]}}.
    Each entry must have "name" and "description" fields.
    Falls back to flat list format if "tiers" key is absent.

    Returns empty dict on missing file or parse error.
    """
    path = _CONFIG_DIR / config_type / f"{system_id}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}

    index: Dict[str, str] = {}

    if "tiers" in data and isinstance(data["tiers"], dict):
        for tier_entries in data["tiers"].values():
            if isinstance(tier_entries, list):
                for entry in tier_entries:
                    if isinstance(entry, dict) and entry.get("name") and entry.get("description"):
                        index[entry["name"].strip().lower()] = entry["description"]
    elif isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and entry.get("name") and entry.get("description"):
                index[entry["name"].strip().lower()] = entry["description"]

    return index


# =========================================================================
# COMBAT NARRATION TEMPLATES — static prose pools (no LLM needed)
# =========================================================================

_COMBAT_HIT: List[str] = [
    "Your {weapon} connects — {enemy} staggers from the blow.",
    "A solid strike. {enemy} recoils, bloodied.",
    "You find an opening and drive {weapon} home.",
    "The blow lands true. {enemy} snarls in pain.",
    "Steel meets flesh. {enemy} stumbles back.",
]

_COMBAT_HIT_CRIT: List[str] = [
    "A devastating strike! {enemy} crumples from the force of it.",
    "You find the weak point — {weapon} bites deep and {enemy} howls.",
    "Perfect timing. The blow sends {enemy} reeling, spraying crimson.",
    "The hit echoes off the walls. {enemy} doesn't see it coming.",
]

_COMBAT_MISS: List[str] = [
    "{enemy} twists aside at the last moment.",
    "Your swing goes wide — {enemy} is faster than expected.",
    "The blow glances harmlessly off stone.",
    "{enemy} reads the attack and slips past your guard.",
]

_COMBAT_FUMBLE: List[str] = [
    "You overcommit — the swing carries you off balance.",
    "Your footing betrays you. {enemy} watches with cold patience.",
    "The weapon slips in your grip. A dangerous moment.",
]

_COMBAT_KILL: List[str] = [
    "{enemy} collapses and does not rise.",
    "The light leaves {enemy}'s eyes. Silence returns.",
    "{enemy} crumples to the ground, still at last.",
    "A final shudder, and {enemy} is gone.",
]

_COMBAT_ENEMY_HIT: List[str] = [
    "{enemy} strikes true — pain blooms through your body.",
    "You don't see the blow coming. {enemy} catches you hard.",
    "{enemy} presses the advantage, landing a vicious strike.",
    "The impact drives the air from your lungs.",
]

_COMBAT_ENEMY_MISS: List[str] = [
    "{enemy} lunges but you twist clear.",
    "A near miss — {enemy}'s attack whistles past your ear.",
    "You duck under {enemy}'s swing, heart hammering.",
    "{enemy} overextends and you slip away.",
]


class NarrativeBridge:
    """Universal adapter: config content to gameplay narration.

    Per-session instance. Loads config data lazily. No LLM calls.

    Args:
        system_id: Engine system identifier (e.g. "burnwillow", "dnd5e").
        seed: Optional RNG seed for deterministic atmosphere selection.
    """

    def __init__(self, system_id: str, seed: Optional[int] = None) -> None:
        self.system_id = system_id
        self._rng = random.Random(seed)
        self._seen_enemies: set = set()
        self._bestiary_idx: Optional[Dict[str, str]] = None
        self._loot_idx: Optional[Dict[str, str]] = None
        self._hazard_idx: Optional[Dict[str, str]] = None
        self._room_desc_cache: Dict[int, str] = {}  # hash(desc) -> enriched text

    # ── Lazy Index Builders ──────────────────────────────────────────

    def _get_bestiary(self) -> Dict[str, str]:
        if self._bestiary_idx is None:
            self._bestiary_idx = _load_config_index("bestiary", self.system_id)
        return self._bestiary_idx

    def _get_loot(self) -> Dict[str, str]:
        if self._loot_idx is None:
            self._loot_idx = _load_config_index("loot", self.system_id)
        return self._loot_idx

    def _get_hazards(self) -> Dict[str, str]:
        if self._hazard_idx is None:
            self._hazard_idx = _load_config_index("hazards", self.system_id)
        return self._hazard_idx

    # ── Public API ───────────────────────────────────────────────────

    def enrich_room(self, description: str, tier: int = 1) -> str:
        """Prepend atmospheric sensory lead to a room description.

        For Burnwillow: delegates to atmosphere.thermal_narrative_modifier().
        For other systems: picks a sensory sentence from narrative palettes.

        Args:
            description: Base room description text.
            tier: Dungeon tier (1-4). Determines tone.

        Returns:
            Enriched description. Falls back to original on any error.
        """
        if not description:
            return description

        # Burnwillow: use the full atmosphere.py modifier
        if self.system_id == "burnwillow":
            try:
                from codex.games.burnwillow.atmosphere import thermal_narrative_modifier
                return thermal_narrative_modifier(description, tier, self._rng)
            except Exception:
                pass

        # Other systems: pick a sensory lead from narrative palettes
        try:
            from codex.core.services.narrative_frame import NARRATIVE_PALETTES
            prefix = _PALETTE_MAP.get(self.system_id, "burnwillow")
            clamped = max(1, min(4, tier))
            palette = NARRATIVE_PALETTES.get(f"{prefix}_t{clamped}", {})
            if palette:
                # Build a short sensory sentence from palette components
                sounds = palette.get("sounds", [])
                smells = palette.get("smells", [])
                pool: List[str] = []
                if sounds:
                    s = self._rng.choice(sounds)
                    pool.append(f"You hear {s}.")
                if smells:
                    s = self._rng.choice(smells)
                    pool.append(f"The air smells of {s}.")
                if pool:
                    lead = self._rng.choice(pool)
                    return f"{lead} {description}"
        except Exception:
            pass

        return description

    def describe_enemy(self, enemy_name: str) -> str:
        """Return flavor text for an enemy on first encounter.

        First call for a given name: returns " — {description}".
        Subsequent calls for same name: returns "" (already seen).
        Unknown enemy: returns "".

        Args:
            enemy_name: Enemy name to look up.

        Returns:
            Dash-prefixed description string or empty string.
        """
        if not enemy_name:
            return ""
        key = enemy_name.strip().lower()
        if key in self._seen_enemies:
            return ""
        self._seen_enemies.add(key)
        desc = self._get_bestiary().get(key, "")
        if desc:
            return f" \u2014 {desc}"
        return ""

    def describe_loot(self, loot_name: str) -> str:
        """Return flavor text for a loot item.

        Args:
            loot_name: Item name to look up.

        Returns:
            Dash-prefixed description string or empty string.
        """
        if not loot_name:
            return ""
        desc = self._get_loot().get(loot_name.strip().lower(), "")
        if desc:
            return f" \u2014 {desc}"
        return ""

    def describe_hazard(self, hazard_name: str) -> str:
        """Return description for a hazard.

        Args:
            hazard_name: Hazard name to look up.

        Returns:
            Dash-prefixed description string or empty string.
        """
        if not hazard_name:
            return ""
        desc = self._get_hazards().get(hazard_name.strip().lower(), "")
        if desc:
            return f" \u2014 {desc}"
        return ""

    def reset_seen(self) -> None:
        """Clear the seen-enemies set (e.g. on new dungeon floor)."""
        self._seen_enemies.clear()

    # ── Combat Narration ─────────────────────────────────────────────

    def narrate_hit(self, enemy_name: str, damage: int,
                    weapon: str = "", crit: bool = False) -> str:
        """Generate flavor text for a successful attack.

        Returns a short prose sentence or empty string.
        """
        templates = _COMBAT_HIT_CRIT if crit else _COMBAT_HIT
        if not templates:
            return ""
        template = self._rng.choice(templates)
        return template.format(
            enemy=enemy_name, damage=damage,
            weapon=weapon or "your weapon",
        )

    def narrate_miss(self, enemy_name: str, fumble: bool = False) -> str:
        """Generate flavor text for a missed attack."""
        templates = _COMBAT_FUMBLE if fumble else _COMBAT_MISS
        if not templates:
            return ""
        template = self._rng.choice(templates)
        return template.format(enemy=enemy_name)

    def narrate_kill(self, enemy_name: str) -> str:
        """Generate flavor text for killing an enemy."""
        if not _COMBAT_KILL:
            return ""
        template = self._rng.choice(_COMBAT_KILL)
        return template.format(enemy=enemy_name)

    def narrate_enemy_hit(self, enemy_name: str, damage: int) -> str:
        """Generate flavor text for an enemy hitting the player."""
        if not _COMBAT_ENEMY_HIT:
            return ""
        template = self._rng.choice(_COMBAT_ENEMY_HIT)
        return template.format(enemy=enemy_name, damage=damage)

    def narrate_enemy_miss(self, enemy_name: str) -> str:
        """Generate flavor text for an enemy missing."""
        if not _COMBAT_ENEMY_MISS:
            return ""
        template = self._rng.choice(_COMBAT_ENEMY_MISS)
        return template.format(enemy=enemy_name)

    # ── NPC Spawning ─────────────────────────────────────────────────

    def spawn_npc_for_room(self, room_id: int, tier: int = 1) -> Optional[dict]:
        """Decide whether to spawn an NPC and return their data.

        ~20% chance per unvisited room. Returns a scene-ready NPC dict
        or None. Uses ContentPool for config-sourced NPCs with fallback
        to procedural generation.

        Args:
            room_id: Room identifier (for deterministic seeding).
            tier: Dungeon tier for role selection.

        Returns:
            NPC dict with name/role/dialogue/notes, or None.
        """
        # Deterministic per-room: use room_id as sub-seed
        room_rng = random.Random(hash((self._rng.getrandbits(32), room_id)))
        if room_rng.random() > 0.20:
            return None

        try:
            from codex.forge.content_pool import ContentPool
            pool = ContentPool(self.system_id)
            npcs = pool.get_npcs(tier=tier, count=1)
            if npcs:
                npc = npcs[0]
                return npc.to_scene_dict()
        except Exception:
            pass

        # Procedural fallback
        _names = ["A weary traveler", "A hooded stranger", "A wounded scout",
                  "A scavenging merchant", "An old hermit"]
        _dialogues = [
            "Careful ahead. I barely made it out.",
            "Got supplies if you've got coin.",
            "You're not the first to come this way. The others didn't come back.",
            "The deeper you go, the worse it gets.",
            "I've been waiting for someone. You'll do.",
        ]
        idx = room_rng.randint(0, len(_names) - 1)
        return {
            "name": _names[idx],
            "npc_type": "ambient",
            "dialogue": _dialogues[idx],
            "notes": "",
        }

    # ── Quest Generation ───────────────────────────────────────────────

    def generate_quest_hook(self, tier: int = 1,
                            npc_name: str = "") -> Optional[dict]:
        """Generate a quest hook from config tables.

        Uses quest_hook_generator tables if available for the system.
        Returns a dict with title, description, objective, or None.

        Args:
            tier: Dungeon tier for difficulty scaling.
            npc_name: NPC offering the quest (for flavor).

        Returns:
            Quest dict or None if no tables available.
        """
        try:
            from codex.forge.content_pool import ContentPool
            pool = ContentPool(self.system_id)
            tables = pool.get_all_tables()
            # Tables may be nested under "generation" key
            hook_gen = tables.get("quest_hook_generator", {})
            if not hook_gen:
                gen = tables.get("generation", {})
                if isinstance(gen, dict):
                    hook_gen = gen.get("quest_hook_generator", {})
            if not hook_gen:
                return None

            patrons = hook_gen.get("patron", [])
            objectives = hook_gen.get("objective", [])
            complications = hook_gen.get("complication", [])
            rewards = hook_gen.get("reward", [])

            if not objectives:
                return None

            patron = npc_name or (self._rng.choice(patrons) if patrons else "A stranger")
            objective = self._rng.choice(objectives)
            complication = self._rng.choice(complications) if complications else ""
            reward = self._rng.choice(rewards) if rewards else "Coin and gratitude"

            title = objective[:40].rstrip(". ")
            description = f"{patron} asks: {objective}"
            if complication:
                description += f" Complication: {complication}"

            return {
                "quest_id": f"proc_{tier}_{hash(objective) & 0xFFFF:04x}",
                "title": title,
                "description": description,
                "patron": patron,
                "objective": objective,
                "reward": reward,
                "tier": tier,
                "status": "available",
            }
        except Exception:
            return None

    # ── Mimir Room Narration ─────────────────────────────────────────

    def enrich_room_mimir(self, description: str, tier: int = 1,
                          enemies: Optional[list] = None,
                          loot: Optional[list] = None,
                          doom: int = 0,
                          mimir_fn: Optional[Callable] = None) -> str:
        """Enhanced room description via Mimir LLM.

        Builds a prompt from tier + sensory palette + room content and
        asks Mimir for 2-3 sentences. Caches result by description hash.
        Falls back to enrich_room() if Mimir unavailable.

        Args:
            description: Base room description.
            tier: Dungeon tier (1-4).
            enemies: List of enemy names present.
            loot: List of loot names present.
            doom: Current doom clock value.
            mimir_fn: Callable(prompt) -> str for LLM generation.

        Returns:
            Enriched description string.
        """
        if not mimir_fn or not description:
            return self.enrich_room(description, tier)

        # Check cache
        cache_key = hash(description)
        if cache_key in self._room_desc_cache:
            return self._room_desc_cache[cache_key]

        # Build prompt
        parts = [
            f"Describe this dungeon room in 2-3 vivid sentences. "
            f"Tier {tier} (deeper = darker). Use sensory details.",
        ]
        if enemies:
            parts.append(f"Enemies present: {', '.join(enemies[:3])}")
        if loot:
            parts.append(f"Visible items: {', '.join(loot[:3])}")
        if doom > 10:
            parts.append("The doom clock is high — the dungeon feels hostile.")
        parts.append(f"Base room: {description[:200]}")

        prompt = " ".join(parts)

        try:
            result = mimir_fn(prompt)
            if result and isinstance(result, str) and len(result.strip()) > 30:
                text = result.strip()
                # Reject AI meta-commentary
                reject = ["as an ai", "i cannot", "language model", "certainly!"]
                if not any(r in text.lower() for r in reject):
                    # Cap length
                    if len(text) > 300:
                        last_period = text[:300].rfind(".")
                        if last_period > 100:
                            text = text[:last_period + 1]
                        else:
                            text = text[:300] + "..."
                    self._room_desc_cache[cache_key] = text
                    return text
        except Exception:
            pass

        # Fallback to static enrichment
        return self.enrich_room(description, tier)

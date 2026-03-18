#!/usr/bin/env python3
"""
codex/core/encounters.py - Universal Encounter Engine
======================================================

System-agnostic encounter generation that routes by system_tag.
Scales dynamically based on party size and threat level.

Supported systems:
  - BURNWILLOW: Dungeon crawler encounters (enemies, traps, NPCs)
  - DND5E: D&D 5e encounters using DMG encounter tables
  - STC: Cosmere RPG encounters

Triggers:
  - move_entry: Standard room entry encounter
  - scout_fumble: Botched scout pulls enemies + possible trap
  - search: Thorough search yields bonus loot or triggers trap

WO V20.3 Phase 1A / WO V3.2 Phase 5
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from codex.games.burnwillow.content import (
    get_random_enemy,
    get_random_hazard,
    get_random_loot,
    CONTENT_ARCHETYPES,
    CONTENT_DR_BY_TIER,
)

_ROOT = Path(__file__).resolve().parent.parent.parent
_ENCOUNTER_TABLE_CACHE: Optional[dict] = None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EncounterContext:
    """All inputs needed to generate an encounter."""
    system_tag: str              # "BURNWILLOW", "CBR_PNK", "DND5E"
    party_size: int              # Number of active party members
    threat_level: int            # Doom clock value (Burnwillow) or equivalent
    floor_tier: int              # Room/floor tier (1-4)
    room_type: str               # "normal", "boss", "treasure", "secret", "start"
    trigger: str                 # "move_entry", "scout_fumble", "search"
    seed: Optional[int] = None   # RNG seed for determinism
    source_room_enemies: Optional[List[dict]] = None  # Enemies in scouted room (for fumble pull)
    hp_mult: float = 1.0        # HP scaling multiplier (WO-V32.0: party size scaling)
    dmg_mult: float = 1.0       # Damage scaling multiplier (WO-V32.0: party size scaling)


@dataclass
class EncounterResult:
    """Output of an encounter generation."""
    encounter_type: str          # "enemy", "trap", "npc", "mixed", "empty"
    entities: List[dict] = field(default_factory=list)   # Enemy/NPC dicts
    traps: List[dict] = field(default_factory=list)      # Trap/hazard dicts
    loot: List[dict] = field(default_factory=list)       # Bonus loot dicts
    description: str = ""
    doom_cost: int = 0           # Additional doom to charge


# =============================================================================
# PARTY SCALING — HP/DMG multipliers by party size (WO-V32.0)
# =============================================================================

PARTY_SCALING = {
    1: {"hp_mult": 0.8,  "dmg_mult": 0.8},
    2: {"hp_mult": 0.9,  "dmg_mult": 0.9},
    3: {"hp_mult": 1.0,  "dmg_mult": 1.0},
    4: {"hp_mult": 1.0,  "dmg_mult": 1.0},
    5: {"hp_mult": 1.15, "dmg_mult": 1.1},
    6: {"hp_mult": 1.3,  "dmg_mult": 1.2},
}


def get_party_scaling(party_size: int) -> dict:
    """Return HP/damage multipliers for the given party size (clamped 1-6)."""
    clamped = max(1, min(6, party_size))
    return PARTY_SCALING.get(clamped, {"hp_mult": 1.0, "dmg_mult": 1.0})


# =============================================================================
# NPC TEMPLATES
# =============================================================================

NPC_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"name": "Scrap Peddler", "type": "merchant",
         "dialogue": "Psst... got some wares. Cheap, I promise.",
         "trade_tier": 1},
        {"name": "Lost Miner", "type": "informant",
         "dialogue": "Don't go east... something big lurks there.",
         "hint": "reveals_enemies"},
    ],
    2: [
        {"name": "Clockwork Tinker", "type": "merchant",
         "dialogue": "Ironbark tools, fresh from the forge. Interested?",
         "trade_tier": 2},
        {"name": "Wounded Scout", "type": "informant",
         "dialogue": "The next room... traps everywhere. Be careful.",
         "hint": "reveals_hazards"},
    ],
    3: [
        {"name": "Heartwood Hermit", "type": "merchant",
         "dialogue": "Rare moonstone relics. Worth every coin.",
         "trade_tier": 3},
        {"name": "Ghostly Cartographer", "type": "informant",
         "dialogue": "I mapped these halls in life. Let me show you.",
         "hint": "reveals_map"},
    ],
    4: [
        {"name": "Ambercore Dealer", "type": "merchant",
         "dialogue": "Legendary arms for those brave enough to reach me.",
         "trade_tier": 4},
        {"name": "Dying Adventurer", "type": "informant",
         "dialogue": "The boss... it adapts. Use Aether, not brute force.",
         "hint": "reveals_boss_weakness"},
    ],
}


# =============================================================================
# CBR+PNK DATA TABLES (WO-V10.0)
# =============================================================================

CBRPNK_NPC_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"name": "Back-Alley Fixer", "type": "merchant",
         "dialogue": "Need chrome? Data? I got connections.", "trade_tier": 1},
        {"name": "Street Doc", "type": "informant",
         "dialogue": "Corp security swept through here an hour ago. Watch yourself.",
         "hint": "reveals_enemies"},
    ],
    2: [
        {"name": "Data Broker", "type": "merchant",
         "dialogue": "Premium intel. Corp patrol routes, access codes. Name your price.",
         "trade_tier": 2},
        {"name": "Rogue Netrunner", "type": "informant",
         "dialogue": "ICE ahead is military-grade. I barely jacked out alive.",
         "hint": "reveals_hazards"},
    ],
    3: [
        {"name": "Chrome Surgeon", "type": "merchant",
         "dialogue": "Military augments. Clean installs. No questions.",
         "trade_tier": 3},
        {"name": "AI Fragment", "type": "informant",
         "dialogue": "I have mapped this sector's digital architecture. Follow my markers.",
         "hint": "reveals_map"},
    ],
    4: [
        {"name": "Syndicate Arms Dealer", "type": "merchant",
         "dialogue": "Prototype weapons. Corp R&D never saw these leave the lab.",
         "trade_tier": 4},
        {"name": "Dying Runner", "type": "informant",
         "dialogue": "The mainframe... it adapts. Hit it with EMP first.",
         "hint": "reveals_boss_weakness"},
    ],
}

CBRPNK_ENEMIES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"name": "Street Punk", "attack": 2, "defense": 10, "tier": 1},
        {"name": "Gang Enforcer", "attack": 3, "defense": 11, "tier": 1},
    ],
    2: [
        {"name": "Corp Security", "attack": 4, "defense": 12, "tier": 2},
        {"name": "Cyber Dog", "attack": 5, "defense": 11, "tier": 2},
    ],
    3: [
        {"name": "Combat Drone", "attack": 6, "defense": 14, "tier": 3},
        {"name": "Elite Guard", "attack": 7, "defense": 13, "tier": 3},
    ],
    4: [
        {"name": "Mech Walker", "attack": 9, "defense": 16, "tier": 4},
        {"name": "Killbot", "attack": 10, "defense": 15, "tier": 4},
    ],
}

CBRPNK_HAZARDS: Dict[int, List[Dict[str, Any]]] = {
    1: [{"name": "Firewall Spike", "type": "digital", "damage": "1d6"}],
    2: [{"name": "ICE Barrier", "type": "digital", "damage": "2d6"}],
    3: [{"name": "Black ICE", "type": "digital", "damage": "3d6"}],
    4: [{"name": "Kill-Switch", "type": "digital", "damage": "4d6"}],
}


# =============================================================================
# ENCOUNTER ENGINE
# =============================================================================

class EncounterEngine:
    """
    Universal encounter generator. Routes by system_tag to produce
    system-appropriate enemies, traps, and NPCs.
    """

    def generate(self, ctx: EncounterContext) -> EncounterResult:
        """
        Generate an encounter based on context.

        Args:
            ctx: EncounterContext with all relevant parameters.

        Returns:
            EncounterResult with entities, traps, and descriptions.
        """
        tag = ctx.system_tag.upper()

        if tag == "BURNWILLOW":
            return self._route_burnwillow(ctx)
        elif tag == "CBR_PNK":
            return self._route_cbrpnk(ctx)
        elif tag == "DND5E":
            return self._route_dnd5e(ctx)
        elif tag == "STC":
            return self._route_cosmere(ctx)
        else:
            return EncounterResult(
                encounter_type="empty",
                description=f"Unknown system: {ctx.system_tag}",
            )

    # -------------------------------------------------------------------------
    # BURNWILLOW ROUTING
    # -------------------------------------------------------------------------

    def _route_burnwillow(self, ctx: EncounterContext) -> EncounterResult:
        """Route Burnwillow encounter by trigger type."""
        if ctx.trigger == "scout_fumble":
            return self._burnwillow_scout_fumble(ctx)
        elif ctx.trigger == "move_entry":
            return self._burnwillow_move_entry(ctx)
        elif ctx.trigger == "search":
            return self._burnwillow_search(ctx)
        else:
            return EncounterResult(
                encounter_type="empty",
                description=f"Unknown trigger: {ctx.trigger}",
            )

    def _burnwillow_scout_fumble(self, ctx: EncounterContext) -> EncounterResult:
        """
        Scout fumble: pull 1 enemy from the scouted room into current room.
        30% chance of also triggering a trap.
        """
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")

        # Pull one enemy from source room if available
        source = ctx.source_room_enemies or []
        if source:
            pulled = dict(source[0])  # Copy first enemy
            result.entities.append(pulled)
            result.encounter_type = "enemy"
            result.description = f"A {pulled['name']} charges toward you!"

        # 30% chance of trap on fumble
        if rng.random() < 0.30:
            trap = get_random_hazard(ctx.floor_tier, rng)
            result.traps.append(trap)
            if result.encounter_type == "enemy":
                result.encounter_type = "mixed"
                result.description += f" You also trigger a {trap['name']}!"
            else:
                result.encounter_type = "trap"
                result.description = f"Your fumbling triggers a {trap['name']}!"

        return result

    def _burnwillow_move_entry(self, ctx: EncounterContext) -> EncounterResult:
        """
        Room entry encounter. Scales enemy count by party size and threat.
        May spawn an NPC instead of enemies (10% chance in normal rooms).
        """
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        # Skip generation for start rooms
        if ctx.room_type == "start":
            return result

        # 10% NPC chance in normal rooms when not high threat
        if ctx.room_type == "normal" and ctx.threat_level < 15 and rng.random() < 0.10:
            npc = self._generate_npc(tier, rng)
            result.entities.append(npc)
            result.encounter_type = "npc"
            result.description = f"You encounter {npc['name']}."
            return result

        # Standard enemy scaling for rooms that already have enemies
        # (This engine is called to augment, not replace, pre-populated rooms)
        extra_enemies = []

        # Party size scaling: +1 enemy per 2 members above 1
        bonus_count = max(0, (ctx.party_size - 1) // 2)
        for _ in range(bonus_count):
            enemy = get_random_enemy(tier, rng)
            extra_enemies.append(enemy)

        # High threat scaling: upgrade one enemy to tier+1 when doom >= 10
        if ctx.threat_level >= 10 and extra_enemies:
            upgraded_tier = min(4, tier + 1)
            extra_enemies[0] = get_random_enemy(upgraded_tier, rng)
            extra_enemies[0]["_upgraded"] = True

        if extra_enemies:
            result.entities = extra_enemies
            result.encounter_type = "enemy"
            names = ", ".join(e["name"] for e in extra_enemies)
            result.description = f"Additional threats emerge: {names}"

        # Apply party-size HP/DMG multipliers to spawned entities (WO-V32.0)
        for entity in result.entities:
            if not entity.get("is_npc"):
                entity["hp"] = max(1, int(entity.get("hp", 1) * ctx.hp_mult))
                if "max_hp" in entity:
                    entity["max_hp"] = max(1, int(entity["max_hp"] * ctx.hp_mult))
                entity["_dmg_mult"] = ctx.dmg_mult

        return result

    def _burnwillow_search(self, ctx: EncounterContext) -> EncounterResult:
        """
        Search encounter: 20% bonus loot, 10% trap.
        """
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        roll = rng.random()
        if roll < 0.20:
            # Bonus loot find
            loot_item = get_random_loot(tier, rng)
            result.loot.append(loot_item)
            result.encounter_type = "loot"
            result.description = f"You uncover a hidden {loot_item['name']}!"
        elif roll < 0.30:
            # Trap triggered
            trap = get_random_hazard(tier, rng)
            result.traps.append(trap)
            result.encounter_type = "trap"
            result.description = f"Your searching triggers a {trap['name']}!"

        return result

    # -------------------------------------------------------------------------
    # NPC GENERATION
    # -------------------------------------------------------------------------

    def _generate_npc(self, tier: int, rng: random.Random,
                      templates: Optional[Dict[int, List[Dict[str, Any]]]] = None,
                      language_profile=None) -> dict:
        """
        Generate a tier-appropriate NPC.

        Args:
            tier: Dungeon tier (1-4).
            rng: Seeded RNG instance.
            templates: Optional NPC template dict override.
            language_profile: Optional LanguageProfile for procedural naming.
                When provided, the NPC gets a procedural given name + role
                title (e.g. "Kalven the Scrap Peddler").

        Returns:
            NPC dict with is_npc=True flag for downstream identification.
        """
        tier = max(1, min(4, tier))
        if templates is None:
            templates = NPC_TEMPLATES
        pool = templates.get(tier, templates.get(1, []))
        if not pool:
            pool = NPC_TEMPLATES.get(tier, NPC_TEMPLATES[1])
        template = rng.choice(pool)

        npc_name = template["name"]
        if language_profile:
            try:
                from codex.core.world.grapes_engine import generate_name
                proc_name = generate_name(language_profile, rng)
                if proc_name:
                    npc_name = f"{proc_name} the {template['name']}"
            except ImportError:
                pass

        return {
            "name": npc_name,
            "is_npc": True,
            "npc_type": template["type"],
            "dialogue": template["dialogue"],
            "tier": tier,
            "trade_tier": template.get("trade_tier"),
            "hint": template.get("hint"),
        }

    # -------------------------------------------------------------------------
    # D&D 5E ROUTING
    # -------------------------------------------------------------------------

    def _route_dnd5e(self, ctx: EncounterContext) -> EncounterResult:
        """Route D&D 5e encounter by trigger type."""
        if ctx.trigger == "move_entry":
            return self._dnd5e_move_entry(ctx)
        elif ctx.trigger == "search":
            return self._dnd5e_search(ctx)
        elif ctx.trigger == "scout_fumble":
            return self._dnd5e_scout_fumble(ctx)
        return EncounterResult(encounter_type="empty")

    def _dnd5e_move_entry(self, ctx: EncounterContext) -> EncounterResult:
        """D&D 5e room entry encounter using DMG encounter tables."""
        from codex.games.dnd5e import _ENEMY_POOL, _LOOT_POOL, _HAZARD_POOL
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        if ctx.room_type == "start":
            return result

        # 10% NPC chance in normal rooms
        if ctx.room_type == "normal" and ctx.threat_level < 15 and rng.random() < 0.10:
            npc = self._generate_npc(tier, rng, DND5E_NPC_TEMPLATES)
            result.entities.append(npc)
            result.encounter_type = "npc"
            result.description = f"You encounter {npc['name']}."
            return result

        # Load encounter table for CR-based monster selection
        table = _load_encounter_table()
        if table:
            enemies = self._dnd5e_build_encounter(ctx, table, rng)
        else:
            # Fallback to adapter pools
            enemy_pool = _ENEMY_POOL.get(tier, _ENEMY_POOL[1])
            difficulty = "hard" if ctx.room_type == "boss" else "easy"
            count = rng.randint(1, 2) if difficulty == "hard" else rng.randint(0, 2)
            enemies = []
            for _ in range(count):
                name = rng.choice(enemy_pool)
                hp = rng.randint(4 * tier, 10 * tier)
                enemies.append({
                    "name": name, "hp": hp, "max_hp": hp,
                    "attack": tier + rng.randint(1, 4),
                    "defense": 10 + tier, "tier": tier,
                })

        # Party size scaling: +1 enemy per 2 members above 1
        bonus_count = max(0, (ctx.party_size - 1) // 2)
        enemy_pool = _ENEMY_POOL.get(tier, _ENEMY_POOL[1])
        for _ in range(bonus_count):
            name = rng.choice(enemy_pool)
            hp = rng.randint(4 * tier, 10 * tier)
            enemies.append({
                "name": name, "hp": hp, "max_hp": hp,
                "attack": tier + rng.randint(1, 4),
                "defense": 10 + tier, "tier": tier,
            })

        # Threat escalation: upgrade one enemy tier when threat >= 10
        if ctx.threat_level >= 10 and enemies:
            upgraded_tier = min(4, tier + 1)
            up_pool = _ENEMY_POOL.get(upgraded_tier, _ENEMY_POOL[1])
            name = rng.choice(up_pool)
            hp = rng.randint(4 * upgraded_tier, 10 * upgraded_tier)
            enemies[0] = {
                "name": name, "hp": hp, "max_hp": hp,
                "attack": upgraded_tier + rng.randint(1, 4),
                "defense": 10 + upgraded_tier, "tier": upgraded_tier,
                "_upgraded": True,
            }

        if enemies:
            result.entities = enemies
            result.encounter_type = "enemy"
            names = ", ".join(e["name"] for e in enemies)
            result.description = f"Hostile creatures emerge: {names}"

        return result

    def _dnd5e_build_encounter(self, ctx, table, rng):
        """Build CR-appropriate enemies from the DMG encounter table."""
        tier = max(1, min(4, ctx.floor_tier))
        cr_ranges = table.get("tier_cr_ranges", {}).get(str(tier), ["1"])
        monsters_by_cr = table.get("monsters_by_cr", {})

        difficulty = "hard" if ctx.room_type == "boss" else "medium"
        if ctx.room_type == "boss":
            count = rng.randint(1, 3)
        elif ctx.room_type == "treasure":
            count = rng.randint(0, 1)
        else:
            count = rng.randint(0, 2)

        enemies = []
        for _ in range(count):
            cr = rng.choice(cr_ranges)
            pool = monsters_by_cr.get(cr, [])
            if not pool:
                continue
            name = rng.choice(pool)
            cr_xp = table.get("cr_xp", {})
            xp_val = cr_xp.get(cr, 100)
            # Scale HP from CR XP: rough approximation
            hp = max(4, xp_val // (20 * tier) + rng.randint(2, 6))
            hp = min(hp, 50 * tier)  # cap to avoid absurd values
            enemies.append({
                "name": name, "hp": hp, "max_hp": hp,
                "attack": tier + rng.randint(1, 4),
                "defense": 10 + tier, "tier": tier,
                "cr": cr,
            })
        return enemies

    def _dnd5e_search(self, ctx: EncounterContext) -> EncounterResult:
        """D&D 5e search encounter: bonus loot or trap."""
        from codex.games.dnd5e import _LOOT_POOL, _HAZARD_POOL
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        roll = rng.random()
        if roll < 0.20:
            loot_pool = _LOOT_POOL.get(tier, _LOOT_POOL[1])
            item_name = rng.choice(loot_pool)
            result.loot.append({"name": item_name, "tier": tier})
            result.encounter_type = "loot"
            result.description = f"You uncover a hidden {item_name}!"
        elif roll < 0.30:
            hazard_pool = _HAZARD_POOL.get(tier, _HAZARD_POOL[1])
            trap_name = rng.choice(hazard_pool)
            result.traps.append({"name": trap_name})
            result.encounter_type = "trap"
            result.description = f"Your searching triggers a {trap_name}!"
        return result

    def _dnd5e_scout_fumble(self, ctx: EncounterContext) -> EncounterResult:
        """D&D 5e scout fumble: pull enemy + possible trap."""
        from codex.games.dnd5e import _HAZARD_POOL
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")

        source = ctx.source_room_enemies or []
        if source:
            pulled = dict(source[0])
            result.entities.append(pulled)
            result.encounter_type = "enemy"
            result.description = f"A {pulled['name']} charges toward you!"

        if rng.random() < 0.30:
            tier = max(1, min(4, ctx.floor_tier))
            hazard_pool = _HAZARD_POOL.get(tier, _HAZARD_POOL[1])
            trap_name = rng.choice(hazard_pool)
            result.traps.append({"name": trap_name})
            if result.encounter_type == "enemy":
                result.encounter_type = "mixed"
                result.description += f" You also trigger a {trap_name}!"
            else:
                result.encounter_type = "trap"
                result.description = f"Your fumbling triggers a {trap_name}!"
        return result

    # -------------------------------------------------------------------------
    # COSMERE (STC) ROUTING
    # -------------------------------------------------------------------------

    def _route_cosmere(self, ctx: EncounterContext) -> EncounterResult:
        """Route Cosmere encounter by trigger type."""
        if ctx.trigger == "move_entry":
            return self._cosmere_move_entry(ctx)
        elif ctx.trigger == "search":
            return self._cosmere_search(ctx)
        elif ctx.trigger == "scout_fumble":
            return self._cosmere_scout_fumble(ctx)
        return EncounterResult(encounter_type="empty")

    def _cosmere_move_entry(self, ctx: EncounterContext) -> EncounterResult:
        """Cosmere room entry encounter."""
        from codex.games.stc import _ENEMY_POOL, _LOOT_POOL, _HAZARD_POOL
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        if ctx.room_type == "start":
            return result

        # 10% NPC chance in normal rooms
        if ctx.room_type == "normal" and ctx.threat_level < 15 and rng.random() < 0.10:
            npc = self._generate_npc(tier, rng, COSMERE_NPC_TEMPLATES)
            result.entities.append(npc)
            result.encounter_type = "npc"
            result.description = f"You encounter {npc['name']}."
            return result

        enemy_pool = _ENEMY_POOL.get(tier, _ENEMY_POOL[1])
        if ctx.room_type == "boss":
            count = rng.randint(1, 3)
        else:
            count = rng.randint(0, 2)

        enemies = []
        for _ in range(count):
            name = rng.choice(enemy_pool)
            hp = rng.randint(4 * tier, 10 * tier)
            enemies.append({
                "name": name, "hp": hp, "max_hp": hp,
                "attack": tier + rng.randint(1, 4),
                "defense": 10 + tier, "tier": tier,
            })

        # Party size scaling
        bonus_count = max(0, (ctx.party_size - 1) // 2)
        for _ in range(bonus_count):
            name = rng.choice(enemy_pool)
            hp = rng.randint(4 * tier, 10 * tier)
            enemies.append({
                "name": name, "hp": hp, "max_hp": hp,
                "attack": tier + rng.randint(1, 4),
                "defense": 10 + tier, "tier": tier,
            })

        # Threat escalation
        if ctx.threat_level >= 10 and enemies:
            upgraded_tier = min(4, tier + 1)
            up_pool = _ENEMY_POOL.get(upgraded_tier, _ENEMY_POOL[1])
            name = rng.choice(up_pool)
            hp = rng.randint(4 * upgraded_tier, 10 * upgraded_tier)
            enemies[0] = {
                "name": name, "hp": hp, "max_hp": hp,
                "attack": upgraded_tier + rng.randint(1, 4),
                "defense": 10 + upgraded_tier, "tier": upgraded_tier,
                "_upgraded": True,
            }

        if enemies:
            result.entities = enemies
            result.encounter_type = "enemy"
            names = ", ".join(e["name"] for e in enemies)
            result.description = f"Hostile creatures emerge: {names}"
        return result

    def _cosmere_search(self, ctx: EncounterContext) -> EncounterResult:
        """Cosmere search encounter: bonus loot or trap."""
        from codex.games.stc import _LOOT_POOL, _HAZARD_POOL
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        roll = rng.random()
        if roll < 0.20:
            loot_pool = _LOOT_POOL.get(tier, _LOOT_POOL[1])
            item_name = rng.choice(loot_pool)
            result.loot.append({"name": item_name, "tier": tier})
            result.encounter_type = "loot"
            result.description = f"You uncover a hidden {item_name}!"
        elif roll < 0.30:
            hazard_pool = _HAZARD_POOL.get(tier, _HAZARD_POOL[1])
            trap_name = rng.choice(hazard_pool)
            result.traps.append({"name": trap_name})
            result.encounter_type = "trap"
            result.description = f"Your searching triggers a {trap_name}!"
        return result

    def _cosmere_scout_fumble(self, ctx: EncounterContext) -> EncounterResult:
        """Cosmere scout fumble: pull enemy + possible trap."""
        from codex.games.stc import _HAZARD_POOL
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")

        source = ctx.source_room_enemies or []
        if source:
            pulled = dict(source[0])
            result.entities.append(pulled)
            result.encounter_type = "enemy"
            result.description = f"A {pulled['name']} charges toward you!"

        if rng.random() < 0.30:
            tier = max(1, min(4, ctx.floor_tier))
            hazard_pool = _HAZARD_POOL.get(tier, _HAZARD_POOL[1])
            trap_name = rng.choice(hazard_pool)
            result.traps.append({"name": trap_name})
            if result.encounter_type == "enemy":
                result.encounter_type = "mixed"
                result.description += f" You also trigger a {trap_name}!"
            else:
                result.encounter_type = "trap"
                result.description = f"Your fumbling triggers a {trap_name}!"
        return result

    # -------------------------------------------------------------------------
    # CBR+PNK ROUTING (WO-V10.0)
    # -------------------------------------------------------------------------

    def _route_cbrpnk(self, ctx: EncounterContext) -> EncounterResult:
        """Route CBR+PNK encounter by trigger type with heat scaling."""
        if ctx.trigger == "move_entry":
            return self._cbrpnk_move_entry(ctx)
        elif ctx.trigger == "search":
            return self._cbrpnk_search(ctx)
        elif ctx.trigger == "scout_fumble":
            return self._cbrpnk_scout_fumble(ctx)
        return EncounterResult(encounter_type="empty")

    def _cbrpnk_move_entry(self, ctx: EncounterContext) -> EncounterResult:
        """CBR+PNK room entry encounter with heat scaling."""
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        if ctx.room_type == "start":
            return result

        # Heat scaling: +1 effective tier at heat >= 4
        effective_tier = min(4, tier + (1 if ctx.threat_level >= 4 else 0))

        # 10% NPC chance in normal rooms when not high heat
        if ctx.room_type == "normal" and ctx.threat_level < 4 and rng.random() < 0.10:
            npc = self._generate_npc(tier, rng, CBRPNK_NPC_TEMPLATES)
            result.entities.append(npc)
            result.encounter_type = "npc"
            result.description = f"You encounter {npc['name']}."
            return result

        enemy_pool = CBRPNK_ENEMIES.get(effective_tier, CBRPNK_ENEMIES[1])
        if ctx.room_type == "boss":
            count = rng.randint(1, 3)
        else:
            count = rng.randint(0, 2)

        # Heat >= 6: +1 enemy count
        if ctx.threat_level >= 6:
            count += 1

        enemies = []
        for _ in range(count):
            template = rng.choice(enemy_pool)
            enemy = dict(template)
            hp = rng.randint(4 * effective_tier, 10 * effective_tier)
            enemy["hp"] = hp
            enemy["max_hp"] = hp
            enemies.append(enemy)

        # Party size scaling
        bonus_count = max(0, (ctx.party_size - 1) // 2)
        for _ in range(bonus_count):
            template = rng.choice(enemy_pool)
            enemy = dict(template)
            hp = rng.randint(4 * effective_tier, 10 * effective_tier)
            enemy["hp"] = hp
            enemy["max_hp"] = hp
            enemies.append(enemy)

        if enemies:
            result.entities = enemies
            result.encounter_type = "enemy"
            names = ", ".join(e["name"] for e in enemies)
            result.description = f"Hostile contacts detected: {names}"
        return result

    def _cbrpnk_search(self, ctx: EncounterContext) -> EncounterResult:
        """CBR+PNK search encounter: bonus loot or hazard."""
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")
        tier = max(1, min(4, ctx.floor_tier))

        roll = rng.random()
        if roll < 0.20:
            loot_name = rng.choice(["Data Chip", "Stim Pack", "Chrome Fragment",
                                    "Corp Access Key", "Neural Booster"])
            result.loot.append({"name": loot_name, "tier": tier})
            result.encounter_type = "loot"
            result.description = f"You scavenge a {loot_name}."
        elif roll < 0.30:
            hazard_pool = CBRPNK_HAZARDS.get(tier, CBRPNK_HAZARDS[1])
            hazard = rng.choice(hazard_pool)
            result.traps.append(hazard)
            result.encounter_type = "trap"
            result.description = f"Grid hazard detected: {hazard['name']}!"
        return result

    def _cbrpnk_scout_fumble(self, ctx: EncounterContext) -> EncounterResult:
        """CBR+PNK scout fumble: pull enemy + possible hazard."""
        rng = random.Random(ctx.seed) if ctx.seed else random.Random()
        result = EncounterResult(encounter_type="empty")

        source = ctx.source_room_enemies or []
        if source:
            pulled = dict(source[0])
            result.entities.append(pulled)
            result.encounter_type = "enemy"
            result.description = f"A {pulled['name']} locks onto your signal!"

        if rng.random() < 0.30:
            tier = max(1, min(4, ctx.floor_tier))
            hazard_pool = CBRPNK_HAZARDS.get(tier, CBRPNK_HAZARDS[1])
            hazard = rng.choice(hazard_pool)
            result.traps.append(hazard)
            if result.encounter_type == "enemy":
                result.encounter_type = "mixed"
                result.description += f" {hazard['name']} triggers!"
            else:
                result.encounter_type = "trap"
                result.description = f"Your intrusion triggers {hazard['name']}!"
        return result



# =============================================================================
# D&D 5E NPC TEMPLATES
# =============================================================================

DND5E_NPC_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"name": "Travelling Peddler", "type": "merchant",
         "dialogue": "Potions, scrolls, and sundries. What catches your eye?",
         "trade_tier": 1},
        {"name": "Frightened Villager", "type": "informant",
         "dialogue": "Goblins took my cart... they're just down the corridor.",
         "hint": "reveals_enemies"},
    ],
    2: [
        {"name": "Dwarven Smithy", "type": "merchant",
         "dialogue": "Fine steel from Mithral Hall. Won't find better this side of the Spine.",
         "trade_tier": 2},
        {"name": "Wounded Adventurer", "type": "informant",
         "dialogue": "Watch for traps ahead. The kobolds rigged the whole passage.",
         "hint": "reveals_hazards"},
    ],
    3: [
        {"name": "Arcane Quartermaster", "type": "merchant",
         "dialogue": "Enchanted arms and protective wards. Name your price.",
         "trade_tier": 3},
        {"name": "Spectral Sage", "type": "informant",
         "dialogue": "I have walked these halls for centuries. The map is yours.",
         "hint": "reveals_map"},
    ],
    4: [
        {"name": "Planar Merchant", "type": "merchant",
         "dialogue": "I trade in wonders from beyond the Material Plane.",
         "trade_tier": 4},
        {"name": "Dying Paladin", "type": "informant",
         "dialogue": "The dragon... it's vulnerable to cold. Strike fast.",
         "hint": "reveals_boss_weakness"},
    ],
}


# =============================================================================
# COSMERE NPC TEMPLATES
# =============================================================================

COSMERE_NPC_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"name": "Crem Trader", "type": "merchant",
         "dialogue": "Spheres and supplies. Even have a few broams if you've earned it.",
         "trade_tier": 1},
        {"name": "Displaced Bridgeman", "type": "informant",
         "dialogue": "Chasmfiend hatchlings nest just beyond. Stay sharp.",
         "hint": "reveals_enemies"},
    ],
    2: [
        {"name": "Ardent Artificer", "type": "merchant",
         "dialogue": "Fabrials and Stormlight-infused gear. Fair trades only.",
         "trade_tier": 2},
        {"name": "Parshendi Deserter", "type": "informant",
         "dialogue": "The Fused laid traps in these tunnels. Tread carefully.",
         "hint": "reveals_hazards"},
    ],
    3: [
        {"name": "Thaylen Gemcutter", "type": "merchant",
         "dialogue": "Soulcast gems and rare fabrials. Only the finest.",
         "trade_tier": 3},
        {"name": "Spren Guide", "type": "informant",
         "dialogue": "I can show you the lay of these chasms. Follow me.",
         "hint": "reveals_map"},
    ],
    4: [
        {"name": "Herald's Emissary", "type": "merchant",
         "dialogue": "These are relics from a past Desolation. Treat them well.",
         "trade_tier": 4},
        {"name": "Fallen Radiant", "type": "informant",
         "dialogue": "The Unmade... it feeds on fear. Hold to your Ideals.",
         "hint": "reveals_boss_weakness"},
    ],
}


# =============================================================================
# ENCOUNTER TABLE LOADER
# =============================================================================

def _load_encounter_table() -> Optional[dict]:
    """Load and cache the D&D 5e encounter table from config."""
    global _ENCOUNTER_TABLE_CACHE
    if _ENCOUNTER_TABLE_CACHE is not None:
        return _ENCOUNTER_TABLE_CACHE

    table_path = _ROOT / "config" / "systems" / "dnd5e_encounters.json"
    if not table_path.exists():
        return None
    try:
        _ENCOUNTER_TABLE_CACHE = json.loads(table_path.read_text())
        return _ENCOUNTER_TABLE_CACHE
    except (json.JSONDecodeError, OSError):
        return None

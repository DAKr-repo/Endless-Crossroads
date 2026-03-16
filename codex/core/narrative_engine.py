"""
NarrativeEngine — Universal Adventure Module Framework
========================================================

Provides quest tracking, NPC management, chapter progression, and
Mimir-enhanced dialogue for any TTRPG system. Works alongside the
dungeon crawl (Burnwillow) and future game engines.

Content strategy: Static pools provide reliable offline scaffolding.
Mimir synthesizes/enhances pool content when available (same pattern
as Crown & Crew's ``_consult_mimir(prompt, fallback)``).

Structure: Hybrid — main questline (chapter-based, escalating) +
side quests (sandbox, procedural from pools).
"""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =========================================================================
# CAMPAIGN PHASE
# =========================================================================

class CampaignPhase(Enum):
    HAVEN = "haven"         # Town hub: NPCs, quests, shops, rest
    JOURNEY = "journey"     # Travel to dungeon (future phase)
    DELVE = "delve"         # Dungeon crawl (Burnwillow loop)
    AFTERMATH = "aftermath" # Post-delve: turn in quests, story beats


# =========================================================================
# QUEST
# =========================================================================

@dataclass
class Quest:
    quest_id: str               # "main_01", "side_goblin_king"
    title: str
    description: str
    quest_type: str             # "main" or "side"
    chapter: int                # Which chapter this belongs to
    objective: str              # "Find the Crown in the dungeon"
    objective_trigger: str      # "reach_tier_2", "defeat_boss_tier_2"
    reward_text: dict = field(default_factory=dict)  # {"gold": 50, "item": "...", "description": "..."}
    status: str = "available"   # available -> active -> complete -> turned_in
    tier_hint: int = 1
    turn_in_npc: str = ""       # NPC role who accepts completion
    path: str = ""              # "descend", "ascend", or "" (both)
    prerequisite: str = ""      # quest_id that must be turned_in first

    # Progress tracking for multi-step objectives
    progress: int = 0
    progress_target: int = 1

    def to_dict(self) -> dict:
        return {
            "quest_id": self.quest_id, "title": self.title,
            "description": self.description, "quest_type": self.quest_type,
            "chapter": self.chapter, "objective": self.objective,
            "objective_trigger": self.objective_trigger,
            "reward_text": self.reward_text, "status": self.status,
            "tier_hint": self.tier_hint, "turn_in_npc": self.turn_in_npc,
            "path": self.path, "prerequisite": self.prerequisite,
            "progress": self.progress,
            "progress_target": self.progress_target,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Quest:
        # Handle legacy string reward_text from old saves
        rt = data.get("reward_text", {})
        if isinstance(rt, str):
            data = dict(data)
            data["reward_text"] = {"description": rt}
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


# =========================================================================
# NPC (Settlement)
# =========================================================================

@dataclass
class NPC:
    name: str
    role: str                   # "merchant", "quest_giver", "informant", etc.
    description: str
    location: str = ""          # RoomType value: "tavern", "forge", etc.
    dialogue_greeting: str = ""
    dialogue_quest: str = ""
    dialogue_rumor: str = ""
    dialogue_turn_in: str = ""
    disposition: int = 0        # -3 to +3
    quest_id: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "role": self.role,
            "description": self.description, "location": self.location,
            "dialogue_greeting": self.dialogue_greeting,
            "dialogue_quest": self.dialogue_quest,
            "dialogue_rumor": self.dialogue_rumor,
            "dialogue_turn_in": self.dialogue_turn_in,
            "disposition": self.disposition, "quest_id": self.quest_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NPC:
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


# =========================================================================
# DUNGEON NPC (Encountered in the dungeon)
# =========================================================================

@dataclass
class DungeonNPC:
    """An NPC encountered in the dungeon (not a settlement resident)."""
    name: str
    role: str                       # "delver", "scholar", "merchant", etc.
    description: str
    disposition: str = "neutral"    # "friendly", "neutral", "wary", "hostile"
    tier: int = 1

    # Dialogue seeds (Mimir can expand these)
    dialogue_greeting_seed: str = ""
    dialogue_trade_seed: str = ""
    dialogue_lore_seed: str = ""
    dialogue_quest_seed: str = ""

    # Pre-written fallback dialogue
    dialogue_greeting: str = ""
    dialogue_trade: str = ""
    dialogue_lore: str = ""
    dialogue_quest: str = ""

    encountered: bool = False
    quest_hook: str = ""
    inventory: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "role": self.role,
            "description": self.description,
            "disposition": self.disposition, "tier": self.tier,
            "encountered": self.encountered,
        }


# =========================================================================
# NARRATIVE ENGINE
# =========================================================================

@dataclass
class NarrativeEngine:
    """Core narrative state: quests, NPCs, chapters, events."""

    system_id: str = "burnwillow"
    chapter: int = 1
    phase: CampaignPhase = CampaignPhase.HAVEN
    quests: list = field(default_factory=list)
    npcs: list = field(default_factory=list)
    completed_quests: list = field(default_factory=list)
    event_log: list = field(default_factory=list)
    campaign_name: str = ""
    mimir: Any = None
    npc_memory: Any = None  # Optional[NPCMemoryManager]
    dungeon_path: str = "descend"  # "descend" or "ascend"

    # Tracking counters for objective triggers
    _kill_counts: Dict[str, int] = field(default_factory=dict)
    _search_counts: Dict[str, int] = field(default_factory=dict)
    _loot_counts: Dict[str, int] = field(default_factory=dict)
    _visited_tiers: Dict[int, set] = field(default_factory=dict)

    def __post_init__(self):
        if not self.quests:
            self._seed_chapter(self.chapter)
        if not self.npcs:
            self._seed_npcs()

    # -----------------------------------------------------------------
    # Mimir integration
    # -----------------------------------------------------------------

    def _consult_mimir(self, prompt: str, fallback: str,
                       template_key: str = "") -> str:
        """Ask Mimir for AI-generated text, falling back to static pool.

        WO-V47.0: Enriches prompt via build_narrative_frame() and validates
        response with validate_narrative() before returning.
        """
        if self.mimir is None:
            return fallback
        try:
            # WO-V47.0: Enrich prompt with narrative frame
            enriched_prompt = prompt
            try:
                from codex.core.services.narrative_frame import (
                    build_narrative_frame, format_frame_as_prompt,
                    validate_narrative,
                )
                # Build engine reference for context extraction
                engine_ref = getattr(self, "_engine_ref", None)
                if engine_ref:
                    dt = getattr(engine_ref, "delta_tracker", None)
                    frame = build_narrative_frame(
                        engine_ref, prompt, template_key=template_key,
                        delta_tracker=dt,
                    )
                    enriched_prompt = format_frame_as_prompt(frame)
            except Exception:
                pass  # Graceful degradation — use raw prompt

            coro = self.mimir.generate(enriched_prompt)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, coro).result(timeout=15)
            else:
                result = asyncio.run(coro)

            if not result:
                return fallback

            # WO-V47.0: Validate narrative quality
            try:
                from codex.core.services.narrative_frame import validate_narrative
                if not validate_narrative(result):
                    return fallback
            except Exception:
                pass  # Skip validation on import error

            return result
        except Exception:
            return fallback

    # -----------------------------------------------------------------
    # NPC Memory (WO-V12.1)
    # -----------------------------------------------------------------

    def attach_npc_memory(self, manager) -> None:
        """Attach an NPCMemoryManager and register all settlement NPCs."""
        self.npc_memory = manager
        for npc in self.npcs:
            manager.register_npc(
                name=npc.name,
                role=npc.role,
                location=npc.location,
            )

    # -----------------------------------------------------------------
    # Chapter seeding
    # -----------------------------------------------------------------

    def _seed_chapter(self, chapter: int):
        """Populate quests from templates for the given chapter."""
        from codex.core.narrative_content import QUEST_TEMPLATES, CANOPY_QUEST_TEMPLATES

        templates = QUEST_TEMPLATES.get(chapter, [])
        for t in templates:
            # Parse progress target from objective (e.g. kill_count_tier1_5 -> 5)
            target = self._parse_progress_target(t["objective"])
            prereq = t.get("prerequisite", "")
            self.quests.append(Quest(
                quest_id=t["id"], title=t["title"],
                description=t["description"], quest_type=t["type"],
                chapter=chapter,
                objective=t["objective"],
                # objective_trigger is what check_objective() matches against
                objective_trigger=t["objective"],
                reward_text=t["reward"],
                turn_in_npc=t.get("turn_in", ""),
                tier_hint=chapter, path="descend",
                progress_target=target,
                prerequisite=prereq,
            ))

        # Also seed canopy quests for the ascend path
        canopy = CANOPY_QUEST_TEMPLATES.get(chapter, [])
        for t in canopy:
            target = self._parse_progress_target(t["objective"])
            prereq = t.get("prerequisite", "")
            self.quests.append(Quest(
                quest_id=t["id"], title=t["title"],
                description=t["description"], quest_type=t["type"],
                chapter=chapter,
                objective=t["objective"],
                objective_trigger=t["objective"],
                reward_text=t["reward"],
                turn_in_npc=t.get("turn_in", ""),
                tier_hint=chapter, path=t.get("path", "ascend"),
                progress_target=target,
                prerequisite=prereq,
            ))

    def _parse_progress_target(self, objective: str) -> int:
        """Extract numeric target from objective strings like kill_count_tier1_5."""
        if "_count_" not in objective:
            return 1
        parts = objective.rsplit("_", 1)
        if len(parts) == 2:
            try:
                return int(parts[1])
            except ValueError:
                pass
        return 1

    def _seed_npcs(self, language_profile=None):
        """Populate settlement NPCs from templates.

        Args:
            language_profile: Optional LanguageProfile for procedural naming.
                When provided, NPC given names are generated from the profile
                with the static pool name used as fallback.
        """
        from codex.core.narrative_content import NPC_TEMPLATES

        rng = random.Random(hash(self.system_id) + self.chapter)
        for template in NPC_TEMPLATES:
            name = rng.choice(template["names"])
            if language_profile:
                try:
                    from codex.core.world.grapes_engine import generate_name
                    proc_name = generate_name(language_profile, rng)
                    if proc_name:
                        name = proc_name
                except ImportError:
                    pass
            desc = rng.choice(template["descriptions"])
            greeting = rng.choice(template["greetings"])
            rumor = rng.choice(template["rumors"])
            turn_in = rng.choice(template["turn_ins"])
            self.npcs.append(NPC(
                name=name, role=template["role"],
                description=desc, location=template["location"],
                dialogue_greeting=greeting, dialogue_rumor=rumor,
                dialogue_turn_in=turn_in,
            ))

    # -----------------------------------------------------------------
    # Quest API
    # -----------------------------------------------------------------

    def get_active_quests(self) -> list:
        """Get quests currently in progress."""
        return [q for q in self.quests if q.status in ("active", "complete")]

    def accept_quest(self, quest_id: str) -> str:
        """Accept a quest. Returns confirmation message."""
        for q in self.quests:
            if q.quest_id == quest_id and q.status == "available":
                q.status = "active"
                return f"Quest accepted: {q.title}"
        return "Quest not found or not available."

    @staticmethod
    def _extract_tier_key(objective_trigger: str, prefix: str) -> str:
        """Extract tier key from count-based objectives.

        E.g. kill_count_tier1_5 -> "tier_1", search_count_tier2_3 -> "tier_2"
        The key is used to match against triggers like kill_tier_1, search_tier_2.
        """
        # Remove "kill_count_" / "search_count_" / "loot_count_" prefix
        remainder = objective_trigger[len(prefix):]
        # remainder is like "tier1_5" or "tier2_3"
        # We need to extract "tier_N" by splitting off the trailing count
        parts = remainder.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            # "tier1" -> "tier_1" (insert underscore before digit suffix)
            tier_str = parts[0]
            # tier_str could be "tier1" or "tier12"
            # Convert "tier1" -> "tier_1" for matching against "kill_tier_1"
            for i, ch in enumerate(tier_str):
                if ch.isdigit():
                    return tier_str[:i] + "_" + tier_str[i:]
            return tier_str
        return remainder

    def check_objective(self, trigger: str) -> list:
        """Check if any active quests match a trigger. Returns messages."""
        messages = []

        # Update tracking counters
        if trigger.startswith("kill_"):
            key = trigger
            self._kill_counts[key] = self._kill_counts.get(key, 0) + 1
        elif trigger.startswith("search_"):
            key = trigger
            self._search_counts[key] = self._search_counts.get(key, 0) + 1
        elif trigger.startswith("loot_"):
            key = trigger
            self._loot_counts[key] = self._loot_counts.get(key, 0) + 1

        for q in self.quests:
            if q.status != "active":
                continue

            matched = False
            # Direct trigger match (e.g., "reach_tier_2")
            if q.objective_trigger == trigger:
                matched = True
            # Count-based kill triggers: kill_count_tier1_5 matches kill_tier_1
            elif q.objective_trigger.startswith("kill_count_"):
                tier_key = self._extract_tier_key(q.objective_trigger, "kill_count_")
                expected_trigger = f"kill_{tier_key}"
                if trigger == expected_trigger:
                    count = self._kill_counts.get(trigger, 0)
                    q.progress = min(count, q.progress_target)
                    if q.progress >= q.progress_target:
                        matched = True
            # Count-based search triggers
            elif q.objective_trigger.startswith("search_count_"):
                tier_key = self._extract_tier_key(q.objective_trigger, "search_count_")
                expected_trigger = f"search_{tier_key}"
                if trigger == expected_trigger:
                    count = self._search_counts.get(trigger, 0)
                    q.progress = min(count, q.progress_target)
                    if q.progress >= q.progress_target:
                        matched = True
            # Count-based loot triggers
            elif q.objective_trigger.startswith("loot_count_"):
                tier_key = self._extract_tier_key(q.objective_trigger, "loot_count_")
                expected_trigger = f"loot_{tier_key}"
                if trigger == expected_trigger:
                    count = self._loot_counts.get(trigger, 0)
                    q.progress = min(count, q.progress_target)
                    if q.progress >= q.progress_target:
                        matched = True

            if matched and q.status == "active":
                q.status = "complete"
                messages.append(
                    f"Objective complete: {q.title} — {q.objective}")

        return messages

    def turn_in_quest(self, quest_id: str) -> Tuple[str, dict]:
        """Turn in a completed quest. Returns (message, reward_dict)."""
        for q in self.quests:
            if q.quest_id == quest_id and q.status == "complete":
                q.status = "turned_in"
                self.completed_quests.append(q.quest_id)
                self.event_log.append({
                    "type": "quest_turned_in",
                    "quest_id": q.quest_id,
                    "chapter": q.chapter,
                })
                # Increase turn-in NPC disposition
                for npc in self.npcs:
                    if npc.role == q.turn_in_npc:
                        npc.disposition = min(3, npc.disposition + 1)
                # Unlock prerequisite-gated quests
                self._check_quest_prerequisites()
                reward = q.reward_text if isinstance(q.reward_text, dict) else {"description": q.reward_text}
                return (
                    f"Quest complete: {q.title}!",
                    reward,
                )
        return ("Quest not ready for turn-in.", {})

    def _check_quest_prerequisites(self):
        """Unlock quests whose prerequisites have been turned in."""
        for q in self.quests:
            if q.status != "available" or not q.prerequisite:
                continue
            if q.prerequisite in self.completed_quests:
                pass  # Already available, prerequisite met
            else:
                # Keep it hidden — will be revealed when prereq completes
                pass

    def get_available_quests(self) -> list:
        """Get quests that can be accepted (prerequisite met)."""
        available = []
        for q in self.quests:
            if q.status != "available":
                continue
            if q.prerequisite and q.prerequisite not in self.completed_quests:
                continue
            available.append(q)
        return available

    def generate_mimir_quest(self, tier: int) -> Optional[Quest]:
        """Use Mimir to generate a unique quest. Returns Quest or None on failure.

        WO-V47.0: Uses NARRATIVE_TEMPLATES["quest_generation"] for few-shot examples.
        """
        if self.mimir is None:
            return None

        # WO-V47.0: Build prompt with few-shot examples from narrative templates
        base_prompt = (
            f"Generate a dark fantasy dungeon quest for tier {tier}. "
            f"Respond ONLY with JSON, no other text:\n"
            f'{{"title": "short quest name", '
            f'"description": "1-2 sentence quest description", '
            f'"objective_type": "kill_count or search_count or loot_count or reach", '
            f'"tier": {tier}, '
            f'"count": 3}}\n\n'
            f"objective_type must be one of: kill_count, search_count, loot_count, reach\n"
            f"count must be 1-5 (ignored for reach). Keep title under 40 chars."
        )
        try:
            from codex.core.services.narrative_frame import NARRATIVE_TEMPLATES
            template = NARRATIVE_TEMPLATES.get("quest_generation", {})
            examples = template.get("examples", [])
            if examples:
                example_lines = []
                for ex in examples:
                    example_lines.append(f"Example input: {ex['input']}")
                    example_lines.append(f"Example output: {ex['output']}")
                prompt = "\n".join(example_lines) + "\n\n" + base_prompt
            else:
                prompt = base_prompt
        except Exception:
            prompt = base_prompt
        try:
            coro = self.mimir.generate(prompt)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, coro).result(timeout=10)
            else:
                result = asyncio.run(coro)
            if not result:
                return None
            return self._parse_mimir_quest(result, tier)
        except Exception:
            return None

    def _parse_mimir_quest(self, raw: str, tier: int) -> Optional[Quest]:
        """Parse Mimir's JSON response into a Quest. Returns None on failure."""
        import re
        import hashlib

        # Extract JSON from response (may have surrounding text)
        match = re.search(r'\{[^}]+\}', raw)
        if not match:
            return None
        try:
            data = json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            return None

        # Validate required fields
        title = data.get("title", "")
        description = data.get("description", "")
        obj_type = data.get("objective_type", "")
        if not title or not description:
            return None

        valid_types = ("kill_count", "search_count", "loot_count", "reach")
        if obj_type not in valid_types:
            return None

        count = data.get("count", 1)
        try:
            count = int(count)
        except (ValueError, TypeError):
            count = 1
        count = max(1, min(5, count))

        # Build objective trigger string
        if obj_type == "reach":
            objective = f"reach_tier_{tier}"
            target = 1
        else:
            objective = f"{obj_type}_tier{tier}_{count}"
            target = count

        # Unique quest ID
        qhash = hashlib.md5(f"{title}{tier}{objective}".encode()).hexdigest()[:8]
        quest_id = f"mimir_{tier}_{qhash}"

        # Deduplicate
        existing_ids = {q.quest_id for q in self.quests}
        if quest_id in existing_ids:
            return None

        quest = Quest(
            quest_id=quest_id,
            title=title[:40],
            description=description[:200],
            quest_type="side",
            chapter=self.chapter,
            objective=objective,
            objective_trigger=objective,
            reward_text={"description": f"Tier {tier} reward"},
            tier_hint=tier,
            progress_target=target,
        )
        self.quests.append(quest)
        return quest

    def offer_dungeon_quest(self, npc: DungeonNPC) -> Optional[Quest]:
        """Generate a quest from a dungeon NPC. Returns Quest or None.

        WO-V45.0: Tries Mimir-generated quest first, falls back to static templates.
        """
        # Try Mimir first
        mimir_quest = self.generate_mimir_quest(npc.tier)
        if mimir_quest:
            mimir_quest.turn_in_npc = npc.role
            return mimir_quest

        # Static template fallback
        from codex.core.narrative_content import DUNGEON_NPC_QUEST_TEMPLATES

        templates = DUNGEON_NPC_QUEST_TEMPLATES.get(npc.tier, [])
        if not templates:
            return None

        # Filter out already-offered quests
        existing_ids = {q.quest_id for q in self.quests}
        candidates = [t for t in templates if t["id"] not in existing_ids]
        if not candidates:
            return None

        template = random.choice(candidates)
        target = self._parse_progress_target(template["objective"])
        quest = Quest(
            quest_id=template["id"],
            title=template["title"],
            description=template.get("description", template["objective"]),
            quest_type="side",
            chapter=self.chapter,
            objective=template["objective"],
            objective_trigger=template["objective"],
            reward_text=template.get("reward", {}),
            turn_in_npc=npc.role,
            tier_hint=npc.tier,
            progress_target=target,
        )
        self.quests.append(quest)
        return quest

    # -----------------------------------------------------------------
    # NPC API
    # -----------------------------------------------------------------

    def get_npcs_at(self, location: str) -> list:
        """Get NPCs at a specific location (RoomType value)."""
        return [n for n in self.npcs if n.location == location]

    def talk_to_npc(self, npc_name: str, player_message: str = "") -> str:
        """Talk to an NPC by name. Returns dialogue string.

        Args:
            npc_name: Name (or partial name) of the NPC.
            player_message: If non-empty, the player is speaking *to* the NPC
                            and we build a conversational prompt for Mimir.
                            If empty, this is a greeting interaction.
        """
        for npc in self.npcs:
            if npc_name.lower() in npc.name.lower():
                # Inject NPC memory context if available
                memory_ctx = ""
                if self.npc_memory:
                    memory_ctx = self.npc_memory.get_dialogue_context(npc.name)

                if player_message:
                    # Conversational mode: player said something specific
                    prompt = (
                        f"You are {npc.name}, a {npc.role} in Emberhome. "
                        f"{npc.description}\n\n"
                    )
                    if memory_ctx:
                        prompt += f"{memory_ctx}\n\n"
                    prompt += (
                        f'The player says: "{player_message}"\n\n'
                        f"Respond as {npc.name} in 1-2 sentences. "
                        f"Be terse and atmospheric."
                    )
                    if memory_ctx:
                        prompt += " Reference your memories naturally if relevant."
                else:
                    # Greeting mode (original behavior)
                    prompt = (
                        f"You are {npc.name}, a {npc.role} in Emberhome. "
                        f"{npc.description}\n\n"
                    )
                    if memory_ctx:
                        prompt += f"{memory_ctx}\n\n"
                        prompt += (
                            "Reference your memories naturally if relevant. "
                            "Greet the player in 1-2 sentences. Be terse and atmospheric."
                        )
                    else:
                        prompt += "Greet the player in 1-2 sentences. Be terse and atmospheric."

                prompt += (
                    "\n\nPrefix your reply with ONE tag from: "
                    "[Hushed] [Urgent] [Gravelly] [Solemn] [Cheerful] [Menacing]. "
                    "Example: [Solemn] The road has been long."
                )

                # WO-V33.0: RAG lore injection
                try:
                    from codex.core.services.rag_service import get_rag_service
                    rag = get_rag_service()
                    lore_query = f"{npc.role} {npc.name}"
                    lore_result = rag.search(lore_query, self.system_id, k=2, token_budget=200)
                    if lore_result:
                        prompt += f"\n\nLORE: {' '.join(c[:100] for c in lore_result.chunks)}"
                except Exception:
                    pass

                # WO-V55.0: Wiki lore injection for FR settings
                try:
                    from codex.integrations.fr_wiki import is_fr_context, get_fr_wiki
                    if is_fr_context(getattr(self, 'system_id', '')):
                        wiki = get_fr_wiki()
                        lore = wiki.get_lore_summary(npc.name, max_chars=200)
                        if lore:
                            prompt += f"\n\nWIKI: {lore}"
                except Exception:
                    pass

                dialogue = self._consult_mimir(prompt, npc.dialogue_greeting)
                # Guard against Mimir echoing back its instructions
                if "tag from" in dialogue.lower() or "prefix your reply" in dialogue.lower():
                    dialogue = npc.dialogue_greeting
                return f'{npc.name}: "{dialogue}"'
        return "No one by that name is here."

    # -----------------------------------------------------------------
    # Dungeon NPC encounters
    # -----------------------------------------------------------------

    def roll_dungeon_npc_encounter(
        self, tier: int, rng: random.Random,
        language_profile=None,
    ) -> Optional[DungeonNPC]:
        """Roll for a random NPC encounter in the dungeon.

        Args:
            tier: Dungeon tier (1-4).
            rng: Seeded RNG instance.
            language_profile: Optional LanguageProfile for procedural naming.
                Tier 3+ NPCs get full names via ``generate_full_name()``.

        Returns DungeonNPC or None (30% chance of encounter).
        """
        if rng.random() > 0.30:
            return None

        from codex.core.narrative_content import DUNGEON_NPC_TEMPLATES
        templates = DUNGEON_NPC_TEMPLATES.get(
            tier, DUNGEON_NPC_TEMPLATES.get(1, []))
        if not templates:
            return None

        template = rng.choice(templates)
        name = rng.choice(template["names"])
        if language_profile:
            try:
                from codex.core.world.grapes_engine import generate_name, generate_full_name
                if tier >= 3:
                    proc_name = generate_full_name(language_profile, rng)
                else:
                    proc_name = generate_name(language_profile, rng)
                if proc_name:
                    name = proc_name
            except ImportError:
                pass
        desc = rng.choice(template["descriptions"])

        def _pick(lst):
            return rng.choice(lst) if lst else ""

        return DungeonNPC(
            name=name, role=template["role"], description=desc,
            disposition=template["disposition"], tier=tier,
            dialogue_greeting_seed=_pick(template.get("greeting_seeds", [])),
            dialogue_greeting=_pick(template.get("greeting_fallbacks", [])),
            dialogue_lore_seed=_pick(template.get("lore_seeds", [])),
            dialogue_lore=_pick(template.get("lore_fallbacks", [])),
            dialogue_trade_seed=_pick(template.get("trade_seeds", [])),
            dialogue_trade=_pick(template.get("trade_fallbacks", [])),
            dialogue_quest_seed=_pick(template.get("quest_seeds", [])),
            dialogue_quest=_pick(template.get("quest_fallbacks", [])),
        )

    def synthesize_npc_dialogue(
        self, npc: DungeonNPC, dialogue_type: str
    ) -> str:
        """Use Mimir to expand a dialogue seed into full NPC speech.

        WO-V47.0: Injects sensory palette words and relevant memory shards.
        """
        seed_attr = f"dialogue_{dialogue_type}_seed"
        fallback_attr = f"dialogue_{dialogue_type}"
        seed = getattr(npc, seed_attr, "")
        fallback = getattr(npc, fallback_attr, "")

        if not seed:
            return fallback

        # Inject NPC memory context if available
        memory_ctx = ""
        if self.npc_memory:
            memory_ctx = self.npc_memory.get_dialogue_context(npc.name)

        prompt = (
            f"You are {npc.name}, a {npc.disposition} {npc.role} encountered "
            f"in a dungeon (tier {npc.tier}). {npc.description}\n\n"
        )

        # WO-V47.0: Inject sensory palette for grounding
        try:
            from codex.core.services.narrative_frame import select_palette
            palette = select_palette("burnwillow", npc.tier)
            if palette:
                adj = ", ".join(palette.get("adjectives", [])[:3])
                smells = ", ".join(palette.get("smells", [])[:2])
                if adj or smells:
                    prompt += f"SENSORY PALETTE: {adj}. Smells: {smells}.\n\n"
        except Exception:
            pass

        # WO-V47.0: Inject relevant memory shards
        try:
            engine_ref = getattr(self, "_engine_ref", None)
            if engine_ref:
                mem_engine = getattr(engine_ref, "memory_engine", None)
                if mem_engine:
                    from codex.core.services.narrative_frame import get_relevant_shards
                    shards = get_relevant_shards(mem_engine, f"{npc.name} {npc.role}", budget=200)
                    for shard in shards[:2]:
                        prompt += f"[MEMORY] {shard.content[:100]}\n"
                    if shards:
                        prompt += "\n"
        except Exception:
            pass

        if memory_ctx:
            prompt += f"{memory_ctx}\n\n"
        prompt += (
            f"Situation: {seed}\n\n"
            f"Write 1-3 sentences of in-character dialogue. Be terse, "
            f"atmospheric, and grounded. No exposition. Speak as the "
            f"character would."
        )
        if memory_ctx:
            prompt += " Reference your memories naturally if relevant."

        prompt += (
            "\n\nPrefix your reply with ONE tag from: "
            "[Hushed] [Urgent] [Gravelly] [Solemn] [Cheerful] [Menacing]. "
            "Example: [Gravelly] Welcome to my forge."
        )

        # WO-V33.0: RAG lore injection
        try:
            from codex.core.services.rag_service import get_rag_service
            rag = get_rag_service()
            lore_query = f"{npc.role} {npc.name}"
            lore_result = rag.search(lore_query, self.system_id, k=2, token_budget=200)
            if lore_result:
                prompt += f"\n\nLORE: {' '.join(c[:100] for c in lore_result.chunks)}"
        except Exception:
            pass

        return self._consult_mimir(prompt, fallback)

    # -----------------------------------------------------------------
    # Chapter API
    # -----------------------------------------------------------------

    def advance_chapter(self) -> str:
        """Advance to the next chapter and seed new quests."""
        self.chapter += 1
        self._seed_chapter(self.chapter)
        self.event_log.append({
            "type": "chapter_advance", "chapter": self.chapter,
        })
        return f"Chapter {self.chapter} begins."

    def get_chapter_summary(self) -> str:
        """Get a summary of the current chapter state."""
        active = len(self.get_active_quests())
        done = len([q for q in self.quests if q.status == "turned_in"])
        total = len(self.quests)
        return (f"Chapter {self.chapter} | "
                f"Quests: {done}/{total} complete, {active} active")

    # -----------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------

    def roll_haven_event(self) -> dict:
        """Roll a random haven event. Returns event dict with 'text' and optional 'effect'."""
        from codex.core.narrative_content import HAVEN_EVENTS
        rng = random.Random()
        if not HAVEN_EVENTS:
            return {}
        event = rng.choice(HAVEN_EVENTS)
        # Backward compat: if somehow a plain string remains
        if isinstance(event, str):
            return {"text": event, "effect": None}
        return event

    # -----------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "chapter": self.chapter,
            "phase": self.phase.value,
            "quests": [q.to_dict() for q in self.quests],
            "npcs": [n.to_dict() for n in self.npcs],
            "completed_quests": self.completed_quests,
            "event_log": self.event_log,
            "campaign_name": self.campaign_name,
            "dungeon_path": self.dungeon_path,
            "_kill_counts": self._kill_counts,
            "_search_counts": self._search_counts,
            "_loot_counts": self._loot_counts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NarrativeEngine:
        engine = cls.__new__(cls)
        engine.system_id = data.get("system_id", "burnwillow")
        engine.chapter = data.get("chapter", 1)
        engine.phase = CampaignPhase(data.get("phase", "haven"))
        engine.quests = [Quest.from_dict(q) for q in data.get("quests", [])]
        engine.npcs = [NPC.from_dict(n) for n in data.get("npcs", [])]
        engine.completed_quests = data.get("completed_quests", [])
        engine.event_log = data.get("event_log", [])
        engine.campaign_name = data.get("campaign_name", "")
        engine.mimir = None
        engine.npc_memory = None
        engine.dungeon_path = data.get("dungeon_path", "descend")
        engine._kill_counts = data.get("_kill_counts", {})
        engine._search_counts = data.get("_search_counts", {})
        engine._loot_counts = data.get("_loot_counts", {})
        engine._visited_tiers = {}
        return engine

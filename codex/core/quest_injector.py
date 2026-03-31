"""
codex.core.quest_injector — Quest Content Post-Processor
=========================================================

Modifies populated dungeon rooms after generation to inject quest-relevant
content: NPCs that offer quests, environmental markers that hint at
active objectives, and guaranteed encounters for quest-critical rooms.

Called during generate_dungeon() after ContentInjector.populate_all().
"""

from typing import Any, Dict, Optional
import random


class QuestContentInjector:
    """Post-population room modifier for active quests."""

    def inject_all(self, populated_rooms: Dict[int, Any], narrative, zone: int = 1) -> Dict[int, Any]:
        """Run all quest injections on populated rooms.

        Args:
            populated_rooms: Dict of room_id → PopulatedRoom from ContentInjector
            narrative: NarrativeEngine with active quests
            zone: Current dungeon zone number

        Returns:
            Modified populated_rooms dict
        """
        if not narrative or not hasattr(narrative, 'quests'):
            return populated_rooms

        active_quests = [q for q in narrative.quests if q.status in ("available", "active")]
        if not active_quests:
            return populated_rooms

        room_list = list(populated_rooms.items())
        rng = random.Random(hash(str([q.quest_id for q in active_quests])))

        for quest in active_quests:
            # Inject quest-giver NPC into a suitable room
            if quest.status == "available":
                self._inject_quest_npc(room_list, quest, zone, rng, populated_rooms)

            # Add quest markers to rooms matching the objective
            if quest.status == "active":
                self._inject_quest_markers(room_list, quest, zone, populated_rooms)

        return populated_rooms

    def _inject_quest_npc(self, room_list, quest, zone, rng, populated_rooms):
        """Place a quest-giver NPC in a room if the quest is available."""
        # Only inject if quest tier matches this zone
        tier_hint = getattr(quest, 'tier_hint', 1)
        if zone > tier_hint + 1:
            return  # Quest is for a lower zone

        # Find a normal room to place the NPC (not start, not boss)
        candidates = [
            (rid, pr) for rid, pr in room_list
            if hasattr(pr, 'geometry') and pr.geometry.room_type.value in ("normal", "corridor", "chamber")
        ]
        if not candidates:
            return

        target_rid, target_room = rng.choice(candidates)
        content = target_room.content if isinstance(target_room.content, dict) else {}

        # Add quest NPC
        npc = {
            "name": f"Quest: {quest.title}",
            "npc_type": "quest_hook",
            "quest_id": quest.quest_id,
            "dialogue": quest.description,
            "is_npc": True,
        }
        content.setdefault("npcs", []).append(npc)

        # Add environmental hint to description
        desc = content.get("description", "")
        if desc:
            content["description"] = desc + " Someone is waiting here — they have a request."

    def _inject_quest_markers(self, room_list, quest, zone, populated_rooms):
        """Add environmental markers for active quest objectives."""
        objective = getattr(quest, 'objective_trigger', '')
        if not objective:
            return

        # For kill quests, ensure rooms have enemies
        if objective.startswith("kill_"):
            for rid, pr in room_list:
                content = pr.content if isinstance(pr.content, dict) else {}
                enemies = content.get("enemies", [])
                if enemies:
                    # Mark first enemy room with quest indicator
                    content["quest_marker"] = f"Quest objective: {quest.title}"
                    break

        # For reach quests, mark the destination tier rooms
        if objective.startswith("reach_tier_"):
            try:
                target_tier = int(objective.split("_")[-1])
            except ValueError:
                return
            for rid, pr in room_list:
                if hasattr(pr, 'geometry') and pr.geometry.tier >= target_tier:
                    content = pr.content if isinstance(pr.content, dict) else {}
                    content["quest_marker"] = f"You sense you're close to completing: {quest.title}"
                    break

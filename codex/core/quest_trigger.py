"""
codex.core.quest_trigger — Quest Event Dispatcher
===================================================

Routes gameplay events (enemy killed, room entered, search completed)
to the NarrativeEngine's check_objective() system. Wires the existing
quest tracking infrastructure into actual gameplay.

The NarrativeEngine already handles: Quest state, objective matching,
progress tracking, and save/load. This module provides the EVENT BRIDGE
that makes those systems fire during play.
"""

from typing import List, Optional


class QuestTriggerDispatcher:
    """Routes game events to quest objective checks.

    Wraps a NarrativeEngine and fires the appropriate trigger strings
    when gameplay events occur. Returns message lists for display.
    """

    def __init__(self, narrative):
        """Initialize with a NarrativeEngine instance."""
        self.narrative = narrative

    def on_enemy_defeated(self, enemy_name: str, tier: int, faction_id: str = "") -> List[str]:
        """Fire when an enemy is killed. Triggers kill_tier_X objectives."""
        if not self.narrative:
            return []
        trigger = f"kill_tier_{tier}"
        return self.narrative.check_objective(trigger, faction_id)

    def on_room_entered(self, tier: int) -> List[str]:
        """Fire on every room entry. Triggers reach_tier_X objectives."""
        if not self.narrative:
            return []
        trigger = f"reach_tier_{tier}"
        return self.narrative.check_objective(trigger)

    def on_search_completed(self, tier: int) -> List[str]:
        """Fire after a successful room search. Triggers search_tier_X objectives."""
        if not self.narrative:
            return []
        trigger = f"search_tier_{tier}"
        return self.narrative.check_objective(trigger)

    def on_loot_acquired(self, tier: int) -> List[str]:
        """Fire when loot is picked up. Triggers loot_tier_X objectives."""
        if not self.narrative:
            return []
        trigger = f"loot_tier_{tier}"
        return self.narrative.check_objective(trigger)

    def on_faction_rep_changed(self, faction: str, new_tier: int) -> List[str]:
        """Fire when faction reputation changes. Triggers faction_X_Y objectives."""
        if not self.narrative:
            return []
        trigger = f"faction_{faction}_{new_tier}"
        return self.narrative.check_objective(trigger)

    def on_zone_entered(self, zone: int) -> List[str]:
        """Fire when entering a new dungeon zone. Triggers zone_X objectives."""
        if not self.narrative:
            return []
        trigger = f"zone_{zone}"
        return self.narrative.check_objective(trigger)

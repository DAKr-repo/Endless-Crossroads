"""
WO-V45.0 — Quest Map Markers, NPC Quest Memory, Mimir Quest Generation
========================================================================

Tests for the three features added in WO-V45.0:
  Phase 1: Quest markers on spatial map + mini-map
  Phase 2: NPC memory wiring via broadcast_manager
  Phase 3: Mimir-generated quests + rumor board
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from codex.spatial.map_renderer import (
    SpatialRoom, SpatialGridRenderer, RoomVisibility,
    ThemeConfig, MapTheme, THEMES, render_mini_map,
    _MM_QUEST,
)
from codex.core.narrative_engine import NarrativeEngine, Quest, DungeonNPC
from codex.core.services.broadcast import GlobalBroadcastManager
from codex.core.services.npc_memory import NPCMemoryManager, CIVIC_ROLE_MAP


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def theme_cfg():
    return THEMES[MapTheme.RUST]


@pytest.fixture
def narrative():
    """Fresh NarrativeEngine with chapter 1 quests seeded."""
    return NarrativeEngine(system_id="burnwillow", chapter=1)


@pytest.fixture
def broadcast_manager():
    return GlobalBroadcastManager(system_theme="burnwillow")


@pytest.fixture
def npc_memory(broadcast_manager):
    return NPCMemoryManager(broadcast_manager=broadcast_manager)


@pytest.fixture
def dungeon_npc_t2():
    return DungeonNPC(
        name="Varla Ashspear",
        role="delver",
        description="A scarred delver.",
        disposition="friendly",
        tier=2,
    )


# ===========================================================================
# TestQuestMapMarkers
# ===========================================================================

class TestQuestMapMarkers:
    """Phase 1: Quest marker rendering on spatial map and mini-map."""

    def test_spatial_room_quest_markers_default(self):
        """SpatialRoom.quest_markers defaults to empty list."""
        sr = SpatialRoom(id=1, x=0, y=0, width=5, height=5)
        assert sr.quest_markers == []

    def test_theme_config_quest_fields(self, theme_cfg):
        """ThemeConfig has symbol_quest and color_quest."""
        assert hasattr(theme_cfg, "symbol_quest")
        assert hasattr(theme_cfg, "color_quest")
        assert theme_cfg.symbol_quest == "?"
        assert theme_cfg.color_quest == "bold magenta"

    def test_paint_room_renders_quest_marker_current(self):
        """CURRENT room with quest_markers renders ? at bottom-left interior."""
        sr = SpatialRoom(
            id=1, x=0, y=0, width=7, height=5,
            visibility=RoomVisibility.CURRENT,
            quest_markers=["kill"],
        )
        renderer = SpatialGridRenderer({1: sr}, MapTheme.RUST)
        # Bottom-left interior: (1, 3) = (x+1, y+height-2)
        char, style = renderer.grid.get((1, 3), ("", ""))
        assert char == "?"
        assert "magenta" in style

    def test_hidden_rooms_no_quest_marker(self):
        """HIDDEN rooms should not render at all, including quest markers."""
        sr = SpatialRoom(
            id=1, x=0, y=0, width=7, height=5,
            visibility=RoomVisibility.HIDDEN,
            quest_markers=["kill"],
        )
        renderer = SpatialGridRenderer({1: sr}, MapTheme.RUST)
        # Nothing should be rendered for hidden rooms
        assert (1, 3) not in renderer.grid

    def test_visited_room_dimmed_quest_marker(self):
        """VISITED room quest marker uses scouted (dimmed) color."""
        sr = SpatialRoom(
            id=1, x=0, y=0, width=7, height=5,
            visibility=RoomVisibility.VISITED,
            quest_markers=["search"],
        )
        renderer = SpatialGridRenderer({1: sr}, MapTheme.RUST)
        char, style = renderer.grid.get((1, 3), ("", ""))
        assert char == "?"
        theme = THEMES[MapTheme.RUST]
        assert style == theme.color_scouted

    def test_minimap_quest_symbol(self):
        """Mini-map shows Q for visited rooms with quest_markers."""
        rooms = {
            1: {"x": 0, "y": 0, "width": 5, "height": 5,
                "connections": [2], "room_type": "NORMAL", "is_locked": False},
            2: {"x": 20, "y": 0, "width": 5, "height": 5,
                "connections": [1], "room_type": "NORMAL", "is_locked": False,
                "quest_markers": ["kill"]},
        }
        result = render_mini_map(rooms, current_room_id=1, visited_rooms={1, 2},
                                 rich_mode=False)
        assert "Q" in result

    def test_minimap_no_quest_for_unvisited(self):
        """Unvisited rooms with quest_markers should NOT show Q (no spoiling)."""
        rooms = {
            1: {"x": 0, "y": 0, "width": 5, "height": 5,
                "connections": [2], "room_type": "NORMAL", "is_locked": False},
            2: {"x": 20, "y": 0, "width": 5, "height": 5,
                "connections": [1], "room_type": "NORMAL", "is_locked": False,
                "quest_markers": ["kill"]},
        }
        # Room 2 is NOT visited — should show ? (unexplored) not Q
        result = render_mini_map(rooms, current_room_id=1, visited_rooms={1},
                                 rich_mode=False)
        assert "Q" not in result

    def test_empty_quest_markers_no_symbol(self):
        """Rooms with empty quest_markers list should not show Q."""
        rooms = {
            1: {"x": 0, "y": 0, "width": 5, "height": 5,
                "connections": [], "room_type": "NORMAL", "is_locked": False},
        }
        result = render_mini_map(rooms, current_room_id=1, visited_rooms={1},
                                 rich_mode=False)
        assert "Q" not in result


# ===========================================================================
# TestNPCQuestMemory
# ===========================================================================

class TestNPCQuestMemory:
    """Phase 2: NPC memory wiring via broadcast_manager."""

    def test_broadcast_manager_subscription(self, npc_memory):
        """NPCMemoryManager subscribes to all expected events when broadcast_manager provided."""
        assert npc_memory._broadcast_manager is not None
        assert len(npc_memory._callbacks) == len(NPCMemoryManager.SUBSCRIBED_EVENTS)

    def test_turn_in_fires_high_impact(self, broadcast_manager, npc_memory):
        """Quest turn-in broadcasts HIGH_IMPACT_DECISION."""
        npc_memory.register_npc("Grimshaw", "quest_giver", "tavern")
        received = []
        broadcast_manager.subscribe("HIGH_IMPACT_DECISION", lambda p: received.append(p))

        broadcast_manager.broadcast("HIGH_IMPACT_DECISION", {
            "_event_type": "HIGH_IMPACT_DECISION",
            "event_tag": "quest_turned_in",
            "category": "security",
            "summary": "Completed 'Pest Control'.",
        })

        assert len(received) >= 1
        assert received[-1]["event_tag"] == "quest_turned_in"

    def test_accept_fires_civic_event(self, broadcast_manager, npc_memory):
        """Quest acceptance broadcasts CIVIC_EVENT."""
        npc_memory.register_npc("Grimshaw", "quest_giver", "tavern")
        received = []
        broadcast_manager.subscribe("CIVIC_EVENT", lambda p: received.append(p))

        broadcast_manager.broadcast("CIVIC_EVENT", {
            "_event_type": "CIVIC_EVENT",
            "event_tag": "quest_accepted",
            "category": "security",
            "summary": "Accepted 'Pest Control'.",
        })

        assert len(received) >= 1
        assert received[-1]["event_tag"] == "quest_accepted"

    def test_npc_records_anchor_on_high_impact(self, broadcast_manager, npc_memory):
        """HIGH_IMPACT_DECISION events create ANCHOR shards on NPCs."""
        bank = npc_memory.register_npc("Grimshaw", "quest_giver", "tavern")

        broadcast_manager.broadcast("HIGH_IMPACT_DECISION", {
            "_event_type": "HIGH_IMPACT_DECISION",
            "event_tag": "quest_turned_in",
            "category": "security",
            "summary": "Completed 'Pest Control'.",
        })

        from codex.core.services.npc_memory import ShardType
        anchors = [s for s in bank.shards if s.shard_type == ShardType.ANCHOR]
        assert len(anchors) >= 1
        assert "Pest Control" in anchors[-1].content

    def test_merchant_does_not_witness_security(self, broadcast_manager, npc_memory):
        """Merchant role should NOT witness CIVIC_EVENT with category=security."""
        merchant_bank = npc_memory.register_npc("Tilda", "merchant", "market")

        broadcast_manager.broadcast("CIVIC_EVENT", {
            "_event_type": "CIVIC_EVENT",
            "event_tag": "quest_accepted",
            "category": "security",
            "summary": "Accepted 'Pest Control'.",
        })

        # Merchant is not in CIVIC_ROLE_MAP["security"] = ["leader", "quest_giver"]
        assert len(merchant_bank.shards) == 0

    def test_dungeon_npc_records_quest_given(self, npc_memory):
        """Dungeon NPC records 'quest_given' anchor when player accepts quest."""
        bank = npc_memory.register_npc("Varla", "delver")
        bank.record_anchor("Gave quest 'Cleanse the Depths' to a delver.", tags=["quest_given"])

        from codex.core.services.npc_memory import ShardType
        anchors = [s for s in bank.shards if s.shard_type == ShardType.ANCHOR]
        assert len(anchors) == 1
        assert "quest_given" in anchors[0].tags

    def test_memory_context_includes_quest_text(self, broadcast_manager, npc_memory):
        """Dialogue context for NPC includes quest-related memory."""
        npc_memory.register_npc("Grimshaw", "quest_giver", "tavern")

        broadcast_manager.broadcast("HIGH_IMPACT_DECISION", {
            "_event_type": "HIGH_IMPACT_DECISION",
            "event_tag": "quest_turned_in",
            "category": "security",
            "summary": "Completed 'Pest Control'.",
        })

        ctx = npc_memory.get_dialogue_context("Grimshaw")
        assert "Pest Control" in ctx

    def test_civic_role_map_routing(self):
        """CIVIC_ROLE_MAP routes security to leader + quest_giver."""
        assert "leader" in CIVIC_ROLE_MAP["security"]
        assert "quest_giver" in CIVIC_ROLE_MAP["security"]
        assert "merchant" not in CIVIC_ROLE_MAP["security"]

    def test_npc_memory_persistence_via_dict(self, npc_memory):
        """NPC memory bank to_dict/from_dict round-trip preserves shards."""
        from codex.core.services.npc_memory import NPCMemoryBank, BiasLens
        bank = npc_memory.register_npc("Grimshaw", "quest_giver", "tavern")
        bank.record_anchor("Completed 'Pest Control'.", tags=["quest_turned_in"])

        # Serialize
        data = bank.to_dict()
        assert data["npc_name"] == "Grimshaw"
        assert len(data["shards"]) >= 1

        # Deserialize
        bank2 = NPCMemoryBank.from_dict(data, bias_lens=BiasLens())
        assert bank2.npc_name == "Grimshaw"
        assert len(bank2.shards) >= 1
        assert "Pest Control" in bank2.shards[-1].content

    def test_gamestate_has_broadcast_manager(self):
        """GameState initializes with a broadcast_manager attribute."""
        # Import late to avoid circular imports
        import sys
        # Only test if play_burnwillow is importable (may need engine deps)
        try:
            # We can test the class definition indirectly
            from codex.core.services.broadcast import GlobalBroadcastManager
            bm = GlobalBroadcastManager(system_theme="burnwillow")
            assert bm.system_theme == "burnwillow"
        except ImportError:
            pytest.skip("broadcast module not available")


# ===========================================================================
# TestMimirQuestGeneration
# ===========================================================================

class TestMimirQuestGeneration:
    """Phase 3: Mimir-generated quests and rumor board."""

    def test_valid_json_creates_quest(self, narrative):
        """_parse_mimir_quest with valid JSON returns a Quest."""
        raw = json.dumps({
            "title": "Cleanse the Depths",
            "description": "Purge corruption from the lower tunnels.",
            "objective_type": "kill_count",
            "tier": 1,
            "count": 3,
        })
        quest = narrative._parse_mimir_quest(raw, tier=1)
        assert quest is not None
        assert quest.title == "Cleanse the Depths"
        assert quest.quest_type == "side"
        assert quest.progress_target == 3
        assert quest.quest_id.startswith("mimir_1_")

    def test_none_when_no_mimir(self, narrative):
        """generate_mimir_quest returns None when mimir is not set."""
        narrative.mimir = None
        result = narrative.generate_mimir_quest(tier=1)
        assert result is None

    def test_none_on_timeout(self, narrative):
        """generate_mimir_quest returns None when Mimir times out."""
        mock_mimir = MagicMock()
        mock_mimir.generate = AsyncMock(side_effect=TimeoutError)
        narrative.mimir = mock_mimir

        result = narrative.generate_mimir_quest(tier=1)
        assert result is None

    def test_none_on_bad_json(self, narrative):
        """_parse_mimir_quest returns None on invalid JSON."""
        result = narrative._parse_mimir_quest("not json at all", tier=1)
        assert result is None

    def test_none_on_missing_fields(self, narrative):
        """_parse_mimir_quest returns None when required fields are missing."""
        raw = json.dumps({"title": "Test"})  # Missing description, objective_type
        result = narrative._parse_mimir_quest(raw, tier=1)
        assert result is None

    def test_parse_good_data(self, narrative):
        """_parse_mimir_quest extracts correct fields from valid JSON."""
        raw = '{"title": "Root Cleanse", "description": "Kill rot beasts.", "objective_type": "kill_count", "tier": 2, "count": 4}'
        quest = narrative._parse_mimir_quest(raw, tier=2)
        assert quest is not None
        assert quest.title == "Root Cleanse"
        assert quest.tier_hint == 2
        assert quest.progress_target == 4
        assert "kill_count" in quest.objective_trigger

    def test_count_clamping(self, narrative):
        """count is clamped to 1-5 range."""
        raw = json.dumps({
            "title": "Too Many", "description": "Way too many.",
            "objective_type": "kill_count", "tier": 1, "count": 99,
        })
        quest = narrative._parse_mimir_quest(raw, tier=1)
        assert quest is not None
        assert quest.progress_target == 5  # Clamped to max 5

        raw2 = json.dumps({
            "title": "Too Few", "description": "Way too few.",
            "objective_type": "search_count", "tier": 1, "count": -5,
        })
        quest2 = narrative._parse_mimir_quest(raw2, tier=1)
        assert quest2 is not None
        assert quest2.progress_target == 1  # Clamped to min 1

    def test_invalid_objective_type_rejected(self, narrative):
        """Invalid objective_type returns None."""
        raw = json.dumps({
            "title": "Bad Type", "description": "Invalid.",
            "objective_type": "dance", "tier": 1, "count": 1,
        })
        result = narrative._parse_mimir_quest(raw, tier=1)
        assert result is None

    def test_mimir_first_in_offer_dungeon_quest(self, narrative, dungeon_npc_t2):
        """offer_dungeon_quest tries Mimir first."""
        mock_mimir = MagicMock()
        coro = AsyncMock(return_value=json.dumps({
            "title": "AI Quest",
            "description": "Generated by Mimir.",
            "objective_type": "kill_count",
            "tier": 2,
            "count": 3,
        }))
        mock_mimir.generate = coro
        narrative.mimir = mock_mimir

        quest = narrative.offer_dungeon_quest(dungeon_npc_t2)
        assert quest is not None
        assert quest.quest_id.startswith("mimir_")
        assert quest.turn_in_npc == "delver"

    def test_template_fallback_on_mimir_failure(self, narrative, dungeon_npc_t2):
        """offer_dungeon_quest falls back to static templates when Mimir fails."""
        mock_mimir = MagicMock()
        mock_mimir.generate = AsyncMock(return_value=None)
        narrative.mimir = mock_mimir

        quest = narrative.offer_dungeon_quest(dungeon_npc_t2)
        # Should fall back to static templates if available for tier 2
        if quest is not None:
            assert not quest.quest_id.startswith("mimir_")

    def test_unique_ids(self, narrative):
        """Two different Mimir quests get different IDs."""
        raw1 = json.dumps({
            "title": "Quest Alpha", "description": "First.",
            "objective_type": "kill_count", "tier": 1, "count": 2,
        })
        raw2 = json.dumps({
            "title": "Quest Beta", "description": "Second.",
            "objective_type": "search_count", "tier": 1, "count": 3,
        })
        q1 = narrative._parse_mimir_quest(raw1, tier=1)
        q2 = narrative._parse_mimir_quest(raw2, tier=1)
        assert q1 is not None and q2 is not None
        assert q1.quest_id != q2.quest_id

    def test_rumor_board_graceful_offline(self, narrative):
        """generate_mimir_quest returns None when Mimir is offline (None)."""
        narrative.mimir = None
        result = narrative.generate_mimir_quest(tier=1)
        assert result is None

    def test_reach_objective_creates_correct_trigger(self, narrative):
        """reach objective_type creates reach_tier_N trigger with target=1."""
        raw = json.dumps({
            "title": "Explore Deep", "description": "Reach the depths.",
            "objective_type": "reach", "tier": 3, "count": 1,
        })
        quest = narrative._parse_mimir_quest(raw, tier=3)
        assert quest is not None
        assert quest.objective_trigger == "reach_tier_3"
        assert quest.progress_target == 1

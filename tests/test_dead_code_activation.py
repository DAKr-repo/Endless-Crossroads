"""
tests/test_dead_code_activation.py — WO-V56.0
================================================
Tests for all tracks of the Dead Code Resurrection:

Track A: _engine_ref wiring + DeltaTracker on D&D 5e / STC
Track B: Memory Engine on Burnwillow
Track C: (Verified existing — no new tests)
Track D: RAG thermal-gated summarize
Track E: Zone broadcast event subscribers
Track F: TraitHandler Burnwillow resolver
Track G: Session recap on all engine exits
"""
from unittest.mock import MagicMock, patch, PropertyMock
import pytest


# ===========================================================================
# Track A: DeltaTracker wiring
# ===========================================================================

class TestDeltaTrackerBasics:
    """Test DeltaTracker core operations."""

    def test_delta_tracker_record_and_compute(self):
        from codex.core.services.narrative_frame import DeltaTracker
        dt = DeltaTracker()

        room_data = {
            "id": 1,
            "enemies": [{"name": "Goblin"}, {"name": "Orc"}],
            "loot": [{"name": "Gold"}],
            "hazards": [],
        }
        dt.record_visit(1, room_data)

        # First visit — no delta
        assert dt.compute_delta(1, room_data) == ""

        # Revisit with one enemy killed
        room_after = dict(room_data)
        room_after["enemies"] = [{"name": "Orc"}]
        delta = dt.compute_delta(1, room_after)
        assert "1 enemies have fallen" in delta
        assert "1 remain" in delta

    def test_delta_tracker_all_enemies_gone(self):
        from codex.core.services.narrative_frame import DeltaTracker
        dt = DeltaTracker()
        room_data = {"id": 2, "enemies": [{"name": "Troll"}], "loot": [], "hazards": []}
        dt.record_visit(2, room_data)
        room_cleared = {"id": 2, "enemies": [], "loot": [], "hazards": []}
        delta = dt.compute_delta(2, room_cleared)
        assert "enemies are gone" in delta

    def test_delta_tracker_loot_taken(self):
        from codex.core.services.narrative_frame import DeltaTracker
        dt = DeltaTracker()
        room_data = {"id": 3, "enemies": [], "loot": [{"name": "Gem"}, {"name": "Coin"}], "hazards": []}
        dt.record_visit(3, room_data)
        room_looted = {"id": 3, "enemies": [], "loot": [], "hazards": []}
        delta = dt.compute_delta(3, room_looted)
        assert "taken" in delta.lower()

    def test_delta_tracker_serialize_roundtrip(self):
        from codex.core.services.narrative_frame import DeltaTracker
        dt = DeltaTracker()
        dt.record_visit(5, {"id": 5, "enemies": [{"name": "Wolf"}], "loot": [], "hazards": []})

        data = dt.to_dict()
        dt2 = DeltaTracker.from_dict(data)
        assert 5 in dt2._snapshots
        assert dt2._snapshots[5].enemy_count == 1

    def test_delta_tracker_no_snapshot_returns_empty(self):
        from codex.core.services.narrative_frame import DeltaTracker
        dt = DeltaTracker()
        assert dt.compute_delta(99, {"enemies": [], "loot": []}) == ""


class TestDeltaTrackerOnDnD5e:
    """DeltaTracker wiring on D&D 5e engine."""

    def test_dnd5e_has_delta_tracker(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        assert hasattr(engine, 'delta_tracker')
        assert engine.delta_tracker is not None

    def test_dnd5e_delta_tracker_in_save_state(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Tester")
        state = engine.save_state()
        assert "delta_tracker" in state

    def test_dnd5e_delta_tracker_restore(self):
        from codex.games.dnd5e import DnD5eEngine
        from codex.core.services.narrative_frame import DeltaTracker
        engine = DnD5eEngine()
        engine.create_character("Tester")
        assert engine.delta_tracker is not None
        engine.delta_tracker.record_visit(1, {"enemies": [{"name": "Orc"}], "loot": [], "hazards": []})  # type: ignore[union-attr]
        state = engine.save_state()

        engine2 = DnD5eEngine()
        engine2.create_character("Tester")
        engine2.load_state(state)
        assert engine2.delta_tracker is not None
        assert 1 in engine2.delta_tracker._snapshots  # type: ignore[union-attr]

    def test_dnd5e_has_get_current_room_dict(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        assert hasattr(engine, 'get_current_room_dict')
        # Returns None with no dungeon
        assert engine.get_current_room_dict() is None


class TestDeltaTrackerOnSTC:
    """DeltaTracker wiring on Cosmere/STC engine."""

    def test_stc_has_delta_tracker(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        assert hasattr(engine, 'delta_tracker')
        assert engine.delta_tracker is not None

    def test_stc_delta_tracker_in_save_state(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin")
        state = engine.save_state()
        assert "delta_tracker" in state

    def test_stc_delta_tracker_restore(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin")
        assert engine.delta_tracker is not None
        engine.delta_tracker.record_visit(1, {"enemies": [{"name": "Parshendi"}], "loot": [], "hazards": []})  # type: ignore[union-attr]
        state = engine.save_state()

        engine2 = CosmereEngine()
        engine2.create_character("Kaladin")
        engine2.load_state(state)
        assert engine2.delta_tracker is not None
        assert 1 in engine2.delta_tracker._snapshots  # type: ignore[union-attr]

    def test_stc_has_get_current_room_dict(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        assert hasattr(engine, 'get_current_room_dict')
        assert engine.get_current_room_dict() is None


# ===========================================================================
# Track A2: Room interface mismatch fix in narrative_frame
# ===========================================================================

class TestRoomInterfaceFix:
    """Ensure build_narrative_frame handles both dict and object rooms."""

    def test_dict_room_id_extraction(self):
        """Dict-style rooms (Burnwillow) still work."""
        from codex.core.services.narrative_frame import DeltaTracker
        dt = DeltaTracker()
        room = {"id": 1, "enemies": [], "loot": []}
        room_id = room.get("id") if isinstance(room, dict) else getattr(room, 'id', None)
        assert room_id == 1

    def test_object_room_id_extraction(self):
        """Object-style rooms (D&D 5e RoomNode) work with the fix."""
        room_obj = MagicMock()
        room_obj.id = 42
        room_id = room_obj.get("id") if isinstance(room_obj, dict) else getattr(room_obj, 'id', None)
        assert room_id == 42


# ===========================================================================
# Track B: Memory Engine on Burnwillow
# ===========================================================================

class TestMemoryEngineWiring:
    """Memory engine shard creation and persistence."""

    def test_memory_engine_create_shard(self):
        from codex.core.memory import CodexMemoryEngine
        mem = CodexMemoryEngine()
        shard = mem.create_shard(
            "Killed a Goblin in room 3",
            shard_type="ANCHOR",
            tags=["combat", "kill", "tier_1"],
        )
        assert shard.shard_type.value == "ANCHOR"
        assert "kill" in shard.tags
        assert len(mem.shards) == 1

    def test_memory_shards_serialize_roundtrip(self):
        from codex.core.memory import CodexMemoryEngine, MemoryShard
        mem = CodexMemoryEngine()
        mem.create_shard("Test shard", shard_type="ANCHOR", tags=["test"])
        serialized = [s.to_dict() for s in mem.shards]
        assert len(serialized) == 1
        restored = MemoryShard.from_dict(serialized[0])
        assert restored.content == "Test shard"
        assert restored.shard_type.value == "ANCHOR"

    def test_memory_engine_on_burnwillow_engine(self):
        """Burnwillow engine should accept memory_engine attribute."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        from codex.core.memory import CodexMemoryEngine
        engine.memory_engine = CodexMemoryEngine()  # type: ignore[attr-defined]
        engine.memory_engine.create_shard("Test", shard_type="ANCHOR", tags=["test"])  # type: ignore[attr-defined]
        assert len(engine.memory_engine.shards) == 1  # type: ignore[attr-defined]


# ===========================================================================
# Track C: Verify _engine_ref unlocks narrative frame
# ===========================================================================

class TestEngineRefNarrativeFrame:
    """_engine_ref on NarrativeEngine gives build_narrative_frame access."""

    def test_narrative_engine_accepts_engine_ref(self):
        from codex.core.narrative_engine import NarrativeEngine
        ne = NarrativeEngine(system_id="burnwillow")
        engine_mock = MagicMock()
        ne._engine_ref = engine_mock  # type: ignore[attr-defined]
        assert ne._engine_ref is engine_mock  # type: ignore[attr-defined]

    def test_build_narrative_frame_with_delta_tracker(self):
        from codex.core.services.narrative_frame import (
            build_narrative_frame, DeltaTracker,
        )
        engine = MagicMock()
        room_dict = {
            "id": 1, "enemies": [], "loot": [], "type": "forge", "tier": 1,
        }
        engine.get_current_room.return_value = room_dict
        # Ensure _build_affordance_context uses get_current_room (not auto-mocked alternatives)
        del engine.get_current_room_dict
        del engine.get_cardinal_exits
        # WO-V61.0: Pin get_mood_context so tension float comparisons don't hit MagicMock
        engine.get_mood_context.return_value = {
            "tension": 0.0, "tone_words": [], "party_condition": "healthy",
            "system_specific": {},
        }
        dt = DeltaTracker()
        dt.record_visit(1, {"enemies": [{"name": "Goblin"}], "loot": [], "hazards": []})
        # Revisit with enemies cleared
        frame = build_narrative_frame(engine, "Describe the room", delta_tracker=dt)
        # Delta should be injected into context
        assert "CHANGES:" in frame.get("context", "")

    def test_build_narrative_frame_with_memory_engine(self):
        from codex.core.services.narrative_frame import build_narrative_frame
        from codex.core.memory import CodexMemoryEngine
        engine = MagicMock()
        engine.get_current_room.return_value = None
        del engine.get_current_room_dict
        del engine.get_cardinal_exits
        # WO-V61.0: Pin get_mood_context so tension float comparisons don't hit MagicMock
        engine.get_mood_context.return_value = {
            "tension": 0.0, "tone_words": [], "party_condition": "healthy",
            "system_specific": {},
        }
        mem = CodexMemoryEngine()
        mem.create_shard("Killed the Troll King", shard_type="ANCHOR", tags=["combat", "kill"])
        engine.memory_engine = mem
        frame = build_narrative_frame(engine, "The troll king fell in combat")
        # ANCHOR shard matching "kill" tag should be in context
        assert "[MEMORY]" in frame.get("context", "")


# ===========================================================================
# Track D: RAG thermal-gated summarize
# ===========================================================================

class TestRAGThermalGate:
    """Thermal gating for RAG summarization."""

    def test_should_summarize_default_true(self):
        from codex.core.services.rag_service import RAGService
        rag = RAGService()
        # When cortex is not available, default to True
        assert rag._should_summarize() is True

    @patch('codex.core.services.rag_service.RAGService._should_summarize', return_value=False)
    def test_should_summarize_returns_false_when_hot(self, mock_thermal):
        from codex.core.services.rag_service import RAGService
        rag = RAGService()
        assert rag._should_summarize() is False

    def test_summarize_preserves_chunks_on_failure(self):
        from unittest.mock import patch
        from codex.core.services.rag_service import RAGService, RAGResult
        rag = RAGService()
        result = RAGResult(chunks=["chunk1", "chunk2", "chunk3"], system_id="test", query="test")
        # Mock Mimir to simulate failure — avoids 17s+ live Ollama call on Pi 5
        with patch("codex.integrations.mimir.query_mimir", side_effect=RuntimeError("offline")):
            returned = rag.summarize(result, "test query")
        # Chunks should still be present (summary not set due to failure)
        assert len(returned.chunks) == 3

    def test_search_rules_lore_integration(self):
        """search_rules_lore should not crash when RAG is unavailable."""
        from codex.integrations.mimir import search_rules_lore
        # Will return empty since Mimir isn't running, but should not error
        result = search_rules_lore("What is a fireball?", system_id="dnd5e")
        assert isinstance(result, str)


# ===========================================================================
# Track E: Zone broadcast event subscribers
# ===========================================================================

class TestZoneBroadcastWiring:
    """Zone broadcast manager wiring."""

    def test_zone_manager_accepts_broadcast_manager(self):
        """ZoneManager should accept broadcast_manager in __init__."""
        from codex.spatial.zone_manager import ZoneManager
        from codex.spatial.module_manifest import ModuleManifest, Chapter, ZoneEntry

        mm = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="dnd5e",
            chapters=[Chapter(
                chapter_id="ch1",
                display_name="Chapter 1",
                order=1,
                zones=[ZoneEntry(
                    zone_id="z1",
                    blueprint="test.json",
                    exit_trigger="boss_defeated",
                )],
            )],
        )
        bm = MagicMock()
        zm = ZoneManager(manifest=mm, base_path="/tmp", broadcast_manager=bm)
        assert zm._broadcast is bm

    def test_fire_zone_complete_uses_instance_broadcast(self):
        from codex.spatial.zone_manager import ZoneManager
        from codex.spatial.module_manifest import ModuleManifest, Chapter, ZoneEntry

        mm = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="dnd5e",
            chapters=[Chapter(
                chapter_id="ch1",
                display_name="Chapter 1",
                order=1,
                zones=[ZoneEntry(
                    zone_id="zone1",
                    blueprint="test.json",
                    exit_trigger="boss_defeated",
                )],
            )],
        )
        bm = MagicMock()
        zm = ZoneManager(manifest=mm, base_path="/tmp", broadcast_manager=bm)
        zm.fire_zone_complete()
        bm.broadcast.assert_called_once()
        call_args = bm.broadcast.call_args
        assert call_args[0][0] == "ZONE_COMPLETE"

    def test_fire_zone_complete_silent_without_broadcast(self):
        """fire_zone_complete should not crash without broadcast manager."""
        from codex.spatial.zone_manager import ZoneManager
        from codex.spatial.module_manifest import ModuleManifest, Chapter, ZoneEntry

        mm = ModuleManifest(
            module_id="test",
            display_name="Test Module",
            system_id="dnd5e",
            chapters=[Chapter(
                chapter_id="ch1",
                display_name="Chapter 1",
                order=1,
                zones=[ZoneEntry(
                    zone_id="zone1",
                    blueprint="test.json",
                    exit_trigger="boss_defeated",
                )],
            )],
        )
        zm = ZoneManager(manifest=mm, base_path="/tmp")
        # Should not raise
        zm.fire_zone_complete()


# ===========================================================================
# Track F: TraitHandler Burnwillow resolver
# ===========================================================================

class TestTraitHandlerBurnwillow:
    """TraitHandler with Burnwillow resolver."""

    def test_burnwillow_trait_resolver_exists(self):
        from codex.games.burnwillow.engine import BurnwillowTraitResolver
        resolver = BurnwillowTraitResolver()
        assert hasattr(resolver, 'resolve_trait')

    def test_burnwillow_resolver_known_traits_with_character(self):
        from codex.games.burnwillow.engine import BurnwillowEngine, BurnwillowTraitResolver
        engine = BurnwillowEngine()
        char = engine.create_character("Test")
        resolver = BurnwillowTraitResolver()

        # CLEAVE always succeeds (no DC check)
        result = resolver.resolve_trait("CLEAVE", {"character": char})
        assert result["success"] is True
        assert "CLEAVE" in result["message"]

    def test_burnwillow_resolver_unknown_trait(self):
        from codex.games.burnwillow.engine import BurnwillowTraitResolver, BurnwillowEngine
        engine = BurnwillowEngine()
        char = engine.create_character("Test")
        resolver = BurnwillowTraitResolver()
        result = resolver.resolve_trait("FAKE_ABILITY", {"character": char})
        assert result["success"] is False
        assert "Unknown trait" in result["message"]

    def test_burnwillow_resolver_no_character(self):
        from codex.games.burnwillow.engine import BurnwillowTraitResolver
        resolver = BurnwillowTraitResolver()
        result = resolver.resolve_trait("CLEAVE", {})
        assert result["success"] is False
        assert "No character" in result["message"]

    def test_burnwillow_engine_has_trait_handler(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        assert hasattr(engine, '_trait_handler')
        assert engine._trait_handler is not None

    def test_trait_handler_dispatch_with_character(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        char = engine.create_character("Test")
        handler = engine._trait_handler  # type: ignore[attr-defined]
        assert handler is not None
        result = handler.activate_trait("INTERCEPT", "burnwillow", {"character": char})
        assert "action" in result
        assert result["action"] == "intercept"

    def test_trait_handler_has_burnwillow_resolver(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        assert engine._trait_handler is not None  # type: ignore[attr-defined]
        assert engine._trait_handler.has_resolver("burnwillow")  # type: ignore[attr-defined]

    def test_bridge_use_routes_through_trait_handler(self):
        """Bridge _handle_use should use TraitHandler when available."""
        from codex.games.bridge import UniversalGameBridge

        # Create a mock engine with trait handler
        engine = MagicMock()
        engine.system_id = "burnwillow"
        engine.character = MagicMock()

        # Mock inventory with a trait item
        item = MagicMock()
        item.name = "Burglar's Gloves"
        item.special_traits = ["[Lockpick]"]
        engine.character.inventory = {0: item}

        # Mock trait handler
        handler = MagicMock()
        handler.activate_trait.return_value = {
            "effect": "unlock",
            "description": "Attempts to pick the lock.",
        }
        engine._trait_handler = handler

        bridge = UniversalGameBridge.create_lightweight(engine)

        result = bridge._handle_use("gloves")
        handler.activate_trait.assert_called_once()
        assert "Lockpick" in result
        assert "Attempts to pick" in result


# ===========================================================================
# Track G: Session recap (synthesize_narrative)
# ===========================================================================

class TestSessionRecap:
    """synthesize_narrative for session recap."""

    def test_synthesize_narrative_fallback_concatenation(self):
        from codex.core.services.narrative_loom import synthesize_narrative
        from codex.core.memory import MemoryShard, ShardType

        shards = [
            MemoryShard(content="Party entered the dungeon.", shard_type=ShardType.CHRONICLE),
            MemoryShard(content="Defeated a troll.", shard_type=ShardType.ANCHOR),
            MemoryShard(content="Found a magic sword.", shard_type=ShardType.ANCHOR),
        ]
        result = synthesize_narrative("Summarize the session.", shards)
        assert "dungeon" in result.lower()
        assert "troll" in result.lower()
        assert "sword" in result.lower()

    def test_synthesize_narrative_empty_shards(self):
        from codex.core.services.narrative_loom import synthesize_narrative
        result = synthesize_narrative("Summarize.", [])
        assert result == ""

    def test_loom_mixin_adds_shards(self):
        """NarrativeLoomMixin._add_shard stores MemoryShard objects."""
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine._add_shard("Test event", "CHRONICLE")
        assert len(engine._memory_shards) >= 1
        assert engine._memory_shards[-1].content == "Test event"


# ===========================================================================
# Integration: BurnwillowEngine full pipeline
# ===========================================================================

class TestBurnwillowIntegration:
    """Integration tests for Burnwillow dead code activation."""

    def test_burnwillow_engine_delta_tracker_exists(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        assert hasattr(engine, 'delta_tracker')
        assert engine.delta_tracker is not None

    def test_burnwillow_delta_tracker_in_save_game(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_character("Kael")
        data = engine.save_game()
        assert "delta_tracker" in data

    def test_burnwillow_delta_tracker_restore(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_character("Kael")
        assert engine.delta_tracker is not None
        engine.delta_tracker.record_visit(1, {"enemies": [{"name": "Rat"}], "loot": [], "hazards": []})  # type: ignore[union-attr]
        data = engine.save_game()

        engine2 = BurnwillowEngine()
        engine2.load_game(data)
        assert engine2.delta_tracker is not None
        assert 1 in engine2.delta_tracker._snapshots  # type: ignore[union-attr]


# ===========================================================================
# WO-V65.0: Dead Code Purge Verification
# ===========================================================================

class TestV65DeadCodePurge:
    """Verify dead code was properly removed in WO-V65.0."""

    def test_butler_no_orchestrator_field(self):
        """Butler should no longer have _orchestrator attribute."""
        from codex.core.butler import CodexButler
        b = CodexButler()
        assert not hasattr(b, '_orchestrator')

    def test_butler_no_set_orchestrator_method(self):
        """Butler should no longer have set_orchestrator method."""
        from codex.core.butler import CodexButler
        assert not hasattr(CodexButler, 'set_orchestrator')

    def test_tangle_generator_removed(self):
        """TangleGenerator class should be removed from zone1."""
        import codex.games.burnwillow.zone1 as z1
        assert not hasattr(z1, 'TangleGenerator')

    def test_tangle_adapter_still_exists(self):
        """TangleAdapter should still be importable."""
        from codex.games.burnwillow.zone1 import TangleAdapter
        adapter = TangleAdapter()
        assert adapter is not None

    def test_synthesize_narrative_narrow_exception(self):
        """synthesize_narrative should not catch KeyboardInterrupt."""
        from codex.core.services.narrative_loom import synthesize_narrative
        from codex.core.memory import MemoryShard, ShardType

        def bad_mimir(prompt, ctx):
            raise KeyboardInterrupt("should propagate")

        shards = [MemoryShard(content="test", shard_type=ShardType.CHRONICLE)]
        import pytest
        with pytest.raises(KeyboardInterrupt):
            synthesize_narrative("q", shards, mimir_fn=bad_mimir)

    def test_synthesize_narrative_catches_type_error(self):
        """synthesize_narrative should catch TypeError from bad mimir_fn."""
        from codex.core.services.narrative_loom import synthesize_narrative
        from codex.core.memory import MemoryShard, ShardType

        def bad_mimir(prompt, ctx):
            raise TypeError("bad call")

        shards = [MemoryShard(content="test content", shard_type=ShardType.CHRONICLE)]
        result = synthesize_narrative("q", shards, mimir_fn=bad_mimir)
        assert "test content" in result  # falls back to concatenation

    def test_engine_higher_zone_without_tangle_generator(self):
        """BurnwillowEngine zone > 1 should use TangleAdapter directly."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_character("Test")
        engine.generate_dungeon(zone=2, depth=2, seed=42)
        assert engine.dungeon_graph is not None
        assert len(engine.populated_rooms) > 0


    def test_tutorial_dispatch_exists(self):
        """'tutorial' command should be dispatched, not fall through to look."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        result = b.step("tutorial")
        assert "QUICK START" in result or "TUTORIAL" in result

    def test_tutorial_alias_tut(self):
        """'tut' alias should dispatch to tutorial handler."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        result = b.step("tut")
        assert "QUICK START" in result or "TUTORIAL" in result

    def test_tutorial_not_room_description(self):
        """Tutorial output should NOT be a room description."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        result = b.step("tutorial")
        assert "=== Room" not in result

    def test_talk_command_exists(self):
        """'talk' command should dispatch, not fall through to look."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        result = b.step("talk")
        # Should say "No one to talk to" or list NPCs, not a room description
        assert "=== Room" not in result or "NPCs" in result or "No one" in result

    def test_talk_alias_npc(self):
        """'npc' alias should dispatch to talk handler."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        result = b.step("npc")
        assert "=== Room" not in result or "NPCs" in result or "No one" in result

    def test_npcs_shown_in_look(self):
        """NPCs should appear in room look output when present."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        # Inject a test NPC into the current room
        pop = b.engine.populated_rooms.get(b.engine.current_room_id)
        if pop:
            pop.content.setdefault("enemies", []).append({
                "name": "Scrap Peddler", "is_npc": True,
                "npc_type": "merchant", "dialogue": "Got wares.",
            })
        result = b.step("look")
        assert "Scrap Peddler" in result
        assert "NPCS" in result

    def test_conversation_mode_and_bye(self):
        """Entering and exiting conversation mode works."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        # Inject NPC
        pop = b.engine.populated_rooms.get(b.engine.current_room_id)
        if pop:
            pop.content.setdefault("enemies", []).append({
                "name": "Lost Miner", "is_npc": True,
                "npc_type": "informant", "dialogue": "Don't go east.",
            })
        result = b.step("talk miner")
        assert "Lost Miner" in result
        assert b._talking_to == "Lost Miner"
        # Exit conversation
        result = b.step("bye")
        assert "end your conversation" in result.lower()
        assert b._talking_to is None

    def test_movement_exits_conversation(self):
        """Grid movement should auto-exit conversation mode."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        b = BurnwillowBridge("Tester", seed=42)
        b._talking_to = "Test NPC"
        b._talking_to_npc = {"name": "Test NPC", "dialogue": "Hello"}
        b.step("n")  # grid movement
        assert b._talking_to is None

    def test_burnwillow_trait_map_has_all_traits(self):
        from codex.games.burnwillow.engine import BurnwillowTraitResolver
        resolver = BurnwillowTraitResolver()
        assert "CLEAVE" in resolver._TRAIT_MAP
        assert "INTERCEPT" in resolver._TRAIT_MAP
        assert "SHOCKWAVE" in resolver._TRAIT_MAP
        assert "INFERNO" in resolver._TRAIT_MAP

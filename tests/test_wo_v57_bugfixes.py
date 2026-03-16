"""
WO-V57.0 — Bug Fixes + Infrastructure Hardening
=================================================

Regression tests for:
  Bug 1: get_current_room() returns RoomNode, get_current_room_dict() returns dict
  Bug 2: Module manifest path persists across save/load
  Item 3: RAGService.validate() removed
"""

import pytest


# =========================================================================
# Bug 1: get_current_room() vs get_current_room_dict()
# =========================================================================

class TestGetCurrentRoomDnD5e:
    """DnD5eEngine.get_current_room() must return RoomNode with .connections."""

    def test_get_current_room_returns_roomnode(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        room = engine.get_current_room()
        assert room is not None
        assert hasattr(room, "connections"), (
            "get_current_room() must return RoomNode with .connections"
        )
        assert hasattr(room, "id")
        assert hasattr(room, "tier")

    def test_get_current_room_dict_returns_dict(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        room_dict = engine.get_current_room_dict()
        assert room_dict is not None
        assert isinstance(room_dict, dict), (
            "get_current_room_dict() must return a dict"
        )
        assert "id" in room_dict
        assert "tier" in room_dict
        assert "enemies" in room_dict

    def test_get_cardinal_exits_no_crash(self):
        """get_cardinal_exits() uses get_current_room() — must not crash."""
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        exits = engine.get_cardinal_exits()
        assert isinstance(exits, list)


class TestGetCurrentRoomSTC:
    """CosmereEngine.get_current_room() must return RoomNode with .connections."""

    def test_get_current_room_returns_roomnode(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        room = engine.get_current_room()
        assert room is not None
        assert hasattr(room, "connections"), (
            "get_current_room() must return RoomNode with .connections"
        )

    def test_get_current_room_dict_returns_dict(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        room_dict = engine.get_current_room_dict()
        assert room_dict is not None
        assert isinstance(room_dict, dict)
        assert "id" in room_dict


class TestNarrativeFrameRoomSafety:
    """narrative_frame._build_affordance_context must not crash on RoomNode."""

    def test_affordance_context_dnd5e(self):
        from codex.games.dnd5e import DnD5eEngine
        from codex.core.services.narrative_frame import _build_affordance_context
        engine = DnD5eEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        # Must not raise AttributeError on .get()
        result = _build_affordance_context(engine)
        assert isinstance(result, str)

    def test_affordance_context_stc(self):
        from codex.games.stc import CosmereEngine
        from codex.core.services.narrative_frame import _build_affordance_context
        engine = CosmereEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        result = _build_affordance_context(engine)
        assert isinstance(result, str)


class TestStateFrameRoomSafety:
    """state_frame.build_state_frame must not crash on RoomNode engines."""

    def test_build_state_frame_dnd5e(self):
        from codex.games.dnd5e import DnD5eEngine
        from codex.core.state_frame import build_state_frame
        engine = DnD5eEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        frame = build_state_frame(engine, system_id="dnd5e")
        assert frame.system_id == "dnd5e"

    def test_build_state_frame_stc(self):
        from codex.games.stc import CosmereEngine
        from codex.core.state_frame import build_state_frame
        engine = CosmereEngine()
        engine.create_character("Test")
        engine.generate_dungeon()
        frame = build_state_frame(engine, system_id="stc")
        assert frame.system_id == "stc"


# =========================================================================
# Bug 2: Module manifest path persistence
# =========================================================================

class TestModuleManifestPersistence:
    """Module manifest path must survive save/load cycle."""

    def test_dnd5e_module_path_saved(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Test")
        engine._module_manifest_path = "/fake/path/module_manifest.json"
        state = engine.save_state()
        assert state["module_manifest_path"] == "/fake/path/module_manifest.json"

    def test_dnd5e_module_path_loaded(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Test")
        engine._module_manifest_path = "/fake/path/module_manifest.json"
        state = engine.save_state()

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        assert engine2._module_manifest_path == "/fake/path/module_manifest.json"

    def test_stc_module_path_saved(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Test")
        engine._module_manifest_path = "/fake/path/module_manifest.json"
        state = engine.save_state()
        assert state["module_manifest_path"] == "/fake/path/module_manifest.json"

    def test_stc_module_path_loaded(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Test")
        engine._module_manifest_path = "/fake/path/module_manifest.json"
        state = engine.save_state()

        engine2 = CosmereEngine()
        engine2.load_state(state)
        assert engine2._module_manifest_path == "/fake/path/module_manifest.json"

    def test_dnd5e_no_module_path_backward_compat(self):
        """Old save data without module_manifest_path should load fine."""
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.load_state({"party": [], "system_id": "dnd5e"})
        assert engine._module_manifest_path is None


# =========================================================================
# Item 3: RAGService.validate() removed
# =========================================================================

class TestRAGServiceValidateRemoved:
    """RAGService must no longer have a validate() method."""

    def test_no_validate_method(self):
        from codex.core.services.rag_service import RAGService
        assert not hasattr(RAGService, "validate"), (
            "RAGService.validate() should have been removed"
        )

    def test_rag_result_fields_preserved(self):
        """validated and rejected_chunks fields should still exist on RAGResult."""
        from codex.core.services.rag_service import RAGResult
        result = RAGResult()
        assert hasattr(result, "validated")
        assert hasattr(result, "rejected_chunks")

    def test_core_methods_still_exist(self):
        """search, summarize, format_context must still be present."""
        from codex.core.services.rag_service import RAGService
        svc = RAGService()
        assert hasattr(svc, "search")
        assert hasattr(svc, "summarize")
        assert hasattr(svc, "format_context")
        assert hasattr(svc, "search_multi")


# =========================================================================
# Item 5: Config-driven bestiary
# =========================================================================

class TestBestiary:
    """Config-driven bestiary loads from config/bestiary/dnd5e.json."""

    def test_load_bestiary_returns_all_tiers(self):
        from codex.games.dnd5e import _load_bestiary
        b = _load_bestiary()
        assert 1 in b
        assert 2 in b
        assert 3 in b
        assert 4 in b

    def test_bestiary_entries_have_stats(self):
        from codex.games.dnd5e import _load_bestiary
        b = _load_bestiary()
        for tier in (1, 2, 3, 4):
            for monster in b[tier]:
                assert "name" in monster
                assert "base_hp" in monster
                assert "base_ac" in monster
                assert "base_atk" in monster

    def test_enemy_pool_populated_from_bestiary(self):
        from codex.games.dnd5e import _ENEMY_POOL
        # Should have real monster names from bestiary
        assert "Goblin" in _ENEMY_POOL[1]
        assert "Skeleton" in _ENEMY_POOL[1]
        assert len(_ENEMY_POOL[1]) > 5  # More than the old hardcoded list

    def test_adapter_uses_bestiary_stats(self):
        """DnD5eAdapter should create enemies with bestiary base_hp."""
        from codex.games.dnd5e import DnD5eAdapter
        adapter = DnD5eAdapter(seed=42, party_size=1)
        enemy = adapter._make_enemy(1)
        assert "name" in enemy
        assert "hp" in enemy
        assert enemy["hp"] > 0
        assert "defense" in enemy

    def test_bestiary_tier_counts(self):
        """Each tier should have multiple monsters for variety."""
        from codex.games.dnd5e import _load_bestiary
        b = _load_bestiary()
        for tier in (1, 2, 3, 4):
            assert len(b[tier]) >= 5, f"Tier {tier} needs at least 5 monsters"

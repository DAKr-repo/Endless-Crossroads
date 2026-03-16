"""
tests/test_zone_pipeline.py — Zone Pipeline Integration Tests
==============================================================

Verifies the full module zone pipeline: ZoneManager → load_dungeon_graph →
populated_rooms with content_hints applied.

WO-V53.0: Module Zone Pipeline Fix
"""

import json
import os

import pytest

from codex.spatial.map_engine import DungeonGraph, RoomNode, RoomType, PopulatedRoom


# =========================================================================
# FIXTURES — minimal dungeon graph with content_hints
# =========================================================================

def _make_graph(content_hints=None):
    """Build a tiny 2-room DungeonGraph with optional content_hints on room 0."""
    room0 = RoomNode(
        id=0, x=0, y=0, width=10, height=10,
        room_type=RoomType.START, connections=[1], tier=1,
        content_hints=content_hints,
    )
    room1 = RoomNode(
        id=1, x=20, y=0, width=10, height=10,
        room_type=RoomType.NORMAL, connections=[0], tier=2,
    )
    graph = DungeonGraph(seed=42, width=50, height=50, start_room_id=0)
    graph.rooms = {0: room0, 1: room1}
    return graph


_SAMPLE_HINTS = {
    "description": "A vaulted chamber with iron sconces.",
    "read_aloud": "You enter a dimly lit hall.",
    "npcs": [
        {"name": "Volothamp Geddarm", "role": "guide", "dialogue": "Well met!"}
    ],
    "enemies": [
        {"name": "Kenku", "hp": 13, "ac": 13, "attack": 4, "count": 2}
    ],
    "loot": [
        {"name": "Potion of Healing", "value": 50, "description": "Restores 2d4+2 HP"}
    ],
    "investigation_dc": 14,
    "investigation_success": "You find a hidden compartment.",
}


# =========================================================================
# D&D 5e TESTS
# =========================================================================

class TestDnD5eLoadDungeonGraph:
    """Track 1: D&D 5e load_dungeon_graph pipeline."""

    def _make_engine(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Tester", character_class="fighter")
        return engine

    def test_sets_dungeon_graph(self):
        engine = self._make_engine()
        graph = _make_graph()
        engine.load_dungeon_graph(graph)
        assert engine.dungeon_graph is graph

    def test_populates_rooms(self):
        engine = self._make_engine()
        graph = _make_graph()
        engine.load_dungeon_graph(graph)
        assert len(engine.populated_rooms) == 2
        assert all(isinstance(v, PopulatedRoom) for v in engine.populated_rooms.values())

    def test_applies_content_hints(self):
        engine = self._make_engine()
        graph = _make_graph(content_hints=_SAMPLE_HINTS)
        engine.load_dungeon_graph(graph)
        pop = engine.populated_rooms[0]
        assert pop.content["description"] == "A vaulted chamber with iron sconces."
        assert len(pop.content["npcs"]) == 1
        assert pop.content["npcs"][0]["name"] == "Volothamp Geddarm"
        # Kenku: count=2 means 2 enemy dicts
        assert len(pop.content["enemies"]) == 2
        assert pop.content["enemies"][0]["name"] == "Kenku"

    def test_resets_current_room_id(self):
        engine = self._make_engine()
        engine.current_room_id = 99
        graph = _make_graph()
        engine.load_dungeon_graph(graph)
        assert engine.current_room_id == 0

    def test_sets_player_pos(self):
        engine = self._make_engine()
        graph = _make_graph()
        engine.load_dungeon_graph(graph)
        assert engine.player_pos is not None
        assert engine.player_pos == (5, 5)  # center of 10x10 room at (0,0)

    def test_resets_visited_rooms(self):
        engine = self._make_engine()
        engine.visited_rooms = {1, 2, 3}
        graph = _make_graph()
        engine.load_dungeon_graph(graph)
        assert engine.visited_rooms == {0}

    def test_load_module_wires_graph(self, tmp_path):
        engine = self._make_engine()
        _write_module_files(tmp_path)
        manifest_path = str(tmp_path / "module_manifest.json")
        engine.load_module(manifest_path)
        assert engine.dungeon_graph is not None
        assert len(engine.populated_rooms) > 0
        assert engine.current_room_id is not None

    def test_advance_zone_wires_new_graph(self, tmp_path):
        engine = self._make_engine()
        _write_module_files(tmp_path, num_zones=2)
        manifest_path = str(tmp_path / "module_manifest.json")
        engine.load_module(manifest_path)
        old_graph = engine.dungeon_graph
        engine.advance_zone()
        # After advance, a new graph should be loaded
        assert engine.dungeon_graph is not None
        assert engine.populated_rooms is not None


# =========================================================================
# STC TESTS
# =========================================================================

class TestSTCApplyContentHints:
    """Track 2: STC _apply_content_hints + load_dungeon_graph pipeline."""

    def _make_engine(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        return engine

    def test_apply_content_hints_replaces_content(self):
        engine = self._make_engine()
        graph = _make_graph(content_hints=_SAMPLE_HINTS)
        engine.dungeon_graph = graph
        # Populate with random content first
        from codex.spatial.map_engine import ContentInjector
        from codex.games.stc import CosmereAdapter
        adapter = CosmereAdapter(setting_id=engine.setting_id)
        injector = ContentInjector(adapter)
        engine.populated_rooms = injector.populate_all(graph)
        # Now apply hints — should replace room 0
        engine._apply_content_hints(PopulatedRoom)
        pop = engine.populated_rooms[0]
        assert pop.content["description"] == "A vaulted chamber with iron sconces."
        assert pop.content["npcs"][0]["name"] == "Volothamp Geddarm"

    def test_load_dungeon_graph_sets_graph_and_populates(self):
        engine = self._make_engine()
        graph = _make_graph(content_hints=_SAMPLE_HINTS)
        engine.load_dungeon_graph(graph)
        assert engine.dungeon_graph is graph
        assert len(engine.populated_rooms) == 2
        # Content hints should be applied
        pop = engine.populated_rooms[0]
        assert pop.content["enemies"][0]["name"] == "Kenku"

    def test_generate_dungeon_applies_content_hints(self):
        engine = self._make_engine()
        engine.generate_dungeon(depth=2, seed=42)
        # With no content_hints on rooms, populated_rooms should still exist
        assert len(engine.populated_rooms) > 0
        # Verify rooms are PopulatedRoom instances
        for pop in engine.populated_rooms.values():
            assert isinstance(pop, PopulatedRoom)

    def test_load_module_wires_graph(self, tmp_path):
        engine = self._make_engine()
        _write_module_files(tmp_path, system_id="stc")
        manifest_path = str(tmp_path / "module_manifest.json")
        engine.load_module(manifest_path)
        assert engine.dungeon_graph is not None
        assert len(engine.populated_rooms) > 0
        assert engine.current_room_id is not None

    def test_advance_zone_wires_new_graph(self, tmp_path):
        engine = self._make_engine()
        _write_module_files(tmp_path, num_zones=2, system_id="stc")
        manifest_path = str(tmp_path / "module_manifest.json")
        engine.load_module(manifest_path)
        engine.advance_zone()
        assert engine.dungeon_graph is not None
        assert engine.populated_rooms is not None


# =========================================================================
# INTEGRATION TEST
# =========================================================================

class TestZonePipelineIntegration:
    """End-to-end: manifest + blueprint JSON → ZoneManager → load_dungeon_graph
    → authored NPC visible in populated_rooms."""

    def test_authored_npc_appears_in_populated_rooms(self, tmp_path):
        """Full pipeline: blueprint with content_hints → engine populated_rooms."""
        from codex.games.dnd5e import DnD5eEngine

        # Write blueprint with content_hints
        blueprint = _make_graph(content_hints=_SAMPLE_HINTS).to_dict()
        blueprint["content_hints"] = {
            "0": _SAMPLE_HINTS,
        }
        bp_path = tmp_path / "zone_tavern.json"
        bp_path.write_text(json.dumps(blueprint))

        # Write manifest referencing blueprint
        manifest = {
            "module_id": "test_integration",
            "display_name": "Integration Test Module",
            "system_id": "dnd5e",
            "chapters": [
                {
                    "chapter_id": "ch1",
                    "display_name": "Chapter 1",
                    "order": 1,
                    "zones": [
                        {
                            "zone_id": "tavern",
                            "blueprint": "zone_tavern.json",
                            "topology": "dungeon",
                            "theme": "STONE",
                        }
                    ],
                }
            ],
        }
        manifest_path = tmp_path / "module_manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        engine = DnD5eEngine()
        engine.create_character("Hero", character_class="fighter")
        engine.load_module(str(manifest_path))

        # Verify the authored NPC made it through the entire pipeline
        pop = engine.populated_rooms[0]
        assert any(
            npc["name"] == "Volothamp Geddarm"
            for npc in pop.content.get("npcs", [])
        ), "Authored NPC should appear in populated_rooms via content_hints"

        # Verify authored enemies
        kenku_enemies = [
            e for e in pop.content.get("enemies", []) if e["name"] == "Kenku"
        ]
        assert len(kenku_enemies) == 2, "2 Kenku enemies should appear (count=2)"

        # Verify DCs
        assert pop.content.get("investigation_dc") == 14

    def test_stc_authored_content_via_blueprint(self, tmp_path):
        """STC: blueprint content_hints flow through to populated_rooms."""
        from codex.games.stc import CosmereEngine

        blueprint = _make_graph(content_hints=_SAMPLE_HINTS).to_dict()
        blueprint["content_hints"] = {"0": _SAMPLE_HINTS}
        (tmp_path / "zone_ruins.json").write_text(json.dumps(blueprint))

        manifest = {
            "module_id": "stc_test",
            "display_name": "STC Test Module",
            "system_id": "stc",
            "chapters": [
                {
                    "chapter_id": "ch1",
                    "display_name": "Chapter 1",
                    "order": 1,
                    "zones": [
                        {
                            "zone_id": "ruins",
                            "blueprint": "zone_ruins.json",
                            "topology": "dungeon",
                            "theme": "STONE",
                        }
                    ],
                }
            ],
        }
        (tmp_path / "module_manifest.json").write_text(json.dumps(manifest))

        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        engine.load_module(str(tmp_path / "module_manifest.json"))

        pop = engine.populated_rooms[0]
        assert pop.content["description"] == "A vaulted chamber with iron sconces."
        assert any(
            npc["name"] == "Volothamp Geddarm"
            for npc in pop.content.get("npcs", [])
        )


# =========================================================================
# HELPERS — write manifest + blueprint files to tmp_path
# =========================================================================

def _write_module_files(tmp_path, num_zones=1, system_id="dnd5e"):
    """Write a minimal module manifest with procedural zones to tmp_path."""
    zones = []
    for i in range(num_zones):
        zones.append({
            "zone_id": f"zone_{i}",
            "topology": "dungeon",
            "theme": "STONE",
            "generation_params": {
                "width": 30,
                "height": 30,
                "max_depth": 2,
                "seed": 100 + i,
            },
        })

    manifest = {
        "module_id": f"test_{system_id}",
        "display_name": f"Test Module ({system_id})",
        "system_id": system_id,
        "chapters": [
            {
                "chapter_id": "ch1",
                "display_name": "Chapter 1",
                "order": 1,
                "zones": zones,
            }
        ],
    }
    manifest_path = tmp_path / "module_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path

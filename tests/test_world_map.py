#!/usr/bin/env python3
"""
tests/test_world_map.py - Phase 1 Spatial Systems Test Suite
=============================================================

Covers all new spatial systems introduced in Phase 1:
  - WorldMap / LocationNode / TravelRoute (world_map.py)
  - ModuleManifest / Chapter / ZoneEntry (module_manifest.py)
  - ZoneLoader: blueprint loading + procedural generation (zone_loader.py)
  - SettlementAdapter: NPC / service population (settlement_adapter.py)
  - DungeonGraph / RoomNode backward-compatibility (map_engine.py)

All tests are OFFLINE (no Ollama), DETERMINISTIC (seeded RNG), and
exercise the real file paths under vault_maps/modules/sample_module/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codex.spatial.world_map import LocationNode, TravelRoute, WorldMap
from codex.spatial.module_manifest import ZoneEntry, Chapter, ModuleManifest
from codex.spatial.zone_loader import ZoneLoader
from codex.spatial.settlement_adapter import SettlementAdapter, DEFAULT_NPCS, DEFAULT_SERVICES
from codex.spatial.map_engine import (
    DungeonGraph, RoomNode, RoomType, CodexMapEngine,
)
from codex.core.world.grapes_engine import GrapesProfile, Landmark


# =============================================================================
# PATH CONSTANTS
# =============================================================================

_SAMPLE_DIR = Path(__file__).resolve().parent.parent / "vault_maps" / "modules" / "sample_module"
_MANIFEST_PATH = str(_SAMPLE_DIR / "module_manifest.json")
_HIDEOUT_PATH = str(_SAMPLE_DIR / "hideout.json")
_TAVERN_PATH = str(_SAMPLE_DIR / "tavern.json")


# =============================================================================
# SHARED FIXTURES
# =============================================================================

@pytest.fixture
def simple_location_a() -> LocationNode:
    """A minimal town LocationNode for reuse across tests."""
    return LocationNode(
        id="ashford",
        display_name="Ashford",
        x=10,
        y=10,
        location_type="town",
        terrain="plains",
        feature="A quiet market town on the river bend.",
        zones=["ashford_keep"],
        connections=["stonegate"],
        icon="O",
        tier=1,
        is_starting_location=True,
        services=["tavern", "forge", "market"],
    )


@pytest.fixture
def simple_location_b() -> LocationNode:
    """A ruins LocationNode for reuse across tests."""
    return LocationNode(
        id="stonegate",
        display_name="Stonegate Ruins",
        x=30,
        y=20,
        location_type="ruins",
        terrain="mountain",
        feature="Crumbling battlements overlooking a cold pass.",
        zones=[],
        connections=["ashford"],
        icon="%",
        tier=3,
        is_starting_location=False,
        services=[],
    )


@pytest.fixture
def simple_route(simple_location_a, simple_location_b) -> TravelRoute:
    """A TravelRoute between the two simple locations."""
    return TravelRoute(
        from_id=simple_location_a.id,
        to_id=simple_location_b.id,
        travel_days=2,
        terrain="mountain_pass",
        danger_level=2,
        description="A treacherous pass through the Ashford mountains.",
    )


@pytest.fixture
def simple_world_map(simple_location_a, simple_location_b, simple_route) -> WorldMap:
    """A minimal WorldMap with two locations and one route."""
    return WorldMap(
        world_id="test_world",
        display_name="Test World",
        system_id="burnwillow",
        seed=42,
        bounds=(80, 40),
        locations={
            simple_location_a.id: simple_location_a,
            simple_location_b.id: simple_location_b,
        },
        routes=[simple_route],
        start_location_id=simple_location_a.id,
    )


@pytest.fixture
def zone_entry_blueprint() -> ZoneEntry:
    """A ZoneEntry pointing to the sample hideout blueprint."""
    return ZoneEntry(
        zone_id="rat_cellar",
        blueprint="hideout.json",
        topology="dungeon",
        theme="STONE",
        location_id="millhaven",
        entry_trigger="quest_complete",
        exit_trigger="boss_defeated",
    )


@pytest.fixture
def zone_entry_procedural() -> ZoneEntry:
    """A procedural dungeon ZoneEntry (no blueprint)."""
    return ZoneEntry(
        zone_id="proc_dungeon",
        blueprint=None,
        topology="dungeon",
        theme="RUST",
        location_id="somewhere",
        generation_params={"seed": 12345, "width": 40, "height": 40, "max_depth": 3},
    )


@pytest.fixture
def sample_chapter(zone_entry_blueprint, zone_entry_procedural) -> Chapter:
    """A Chapter containing two zones."""
    return Chapter(
        chapter_id="act_1",
        display_name="Act I: The Descent",
        order=1,
        zones=[zone_entry_blueprint, zone_entry_procedural],
    )


@pytest.fixture
def simple_manifest(sample_chapter) -> ModuleManifest:
    """A minimal ModuleManifest with one chapter."""
    return ModuleManifest(
        module_id="test_module",
        display_name="The Test Module",
        system_id="burnwillow",
        starting_location="ashford",
        chapters=[sample_chapter],
    )


@pytest.fixture
def simple_room_node() -> RoomNode:
    """A basic tavern RoomNode for settlement adapter tests."""
    return RoomNode(
        id=0,
        x=5,
        y=5,
        width=8,
        height=6,
        room_type=RoomType.TAVERN,
        connections=[1],
        tier=1,
    )


# =============================================================================
# WORLD MAP TESTS (~10 tests)
# =============================================================================

class TestLocationNode:
    """LocationNode creation and field defaults."""

    def test_creation_all_fields(self, simple_location_a):
        """LocationNode stores all provided fields correctly."""
        node = simple_location_a
        assert node.id == "ashford"
        assert node.display_name == "Ashford"
        assert node.x == 10
        assert node.y == 10
        assert node.location_type == "town"
        assert node.terrain == "plains"
        assert node.tier == 1
        assert node.is_starting_location is True
        assert "tavern" in node.services

    def test_default_grapes_index_is_none(self, simple_location_a):
        """grapes_landmark_index defaults to None when not provided."""
        assert simple_location_a.grapes_landmark_index is None

    def test_default_is_starting_location_false(self, simple_location_b):
        """is_starting_location defaults to False."""
        assert simple_location_b.is_starting_location is False


class TestTravelRoute:
    """TravelRoute creation and serialization."""

    def test_creation(self, simple_route):
        """TravelRoute stores all fields."""
        assert simple_route.from_id == "ashford"
        assert simple_route.to_id == "stonegate"
        assert simple_route.travel_days == 2
        assert simple_route.terrain == "mountain_pass"
        assert simple_route.danger_level == 2

    def test_to_from_dict_round_trip(self, simple_route):
        """TravelRoute serializes and deserializes correctly."""
        d = simple_route.to_dict()
        restored = TravelRoute.from_dict(d)
        assert restored.from_id == simple_route.from_id
        assert restored.to_id == simple_route.to_id
        assert restored.travel_days == simple_route.travel_days
        assert restored.terrain == simple_route.terrain
        assert restored.danger_level == simple_route.danger_level
        assert restored.description == simple_route.description


class TestWorldMap:
    """WorldMap creation, traversal, mutation, and serialization."""

    def test_creation(self, simple_world_map):
        """WorldMap holds the expected locations and routes."""
        wm = simple_world_map
        assert wm.world_id == "test_world"
        assert len(wm.locations) == 2
        assert len(wm.routes) == 1
        assert wm.start_location_id == "ashford"

    def test_to_from_dict_round_trip(self, simple_world_map):
        """WorldMap round-trips through to_dict / from_dict without data loss."""
        d = simple_world_map.to_dict()
        restored = WorldMap.from_dict(d)

        assert restored.world_id == simple_world_map.world_id
        assert restored.display_name == simple_world_map.display_name
        assert restored.system_id == simple_world_map.system_id
        assert restored.seed == simple_world_map.seed
        assert restored.bounds == simple_world_map.bounds
        assert set(restored.locations.keys()) == set(simple_world_map.locations.keys())
        assert len(restored.routes) == len(simple_world_map.routes)
        assert restored.start_location_id == simple_world_map.start_location_id

    def test_get_connections_returns_correct_neighbors(self, simple_world_map):
        """get_connections() returns the LocationNodes reachable from a location."""
        neighbors = simple_world_map.get_connections("ashford")
        assert len(neighbors) == 1
        assert neighbors[0].id == "stonegate"

    def test_get_connections_unknown_id_returns_empty(self, simple_world_map):
        """get_connections() returns [] for an unrecognised location ID."""
        result = simple_world_map.get_connections("nowhere")
        assert result == []

    def test_get_route_returns_correct_route(self, simple_world_map, simple_route):
        """get_route() returns the matching TravelRoute."""
        route = simple_world_map.get_route("ashford", "stonegate")
        assert route is not None
        assert route.from_id == simple_route.from_id
        assert route.to_id == simple_route.to_id

    def test_get_route_undirected(self, simple_world_map):
        """get_route() is undirected: (B->A) finds the same route as (A->B)."""
        route_ab = simple_world_map.get_route("ashford", "stonegate")
        route_ba = simple_world_map.get_route("stonegate", "ashford")
        assert route_ab is not None
        assert route_ba is not None
        assert route_ab is route_ba

    def test_get_route_nonexistent_returns_none(self, simple_world_map):
        """get_route() returns None when no route exists between two locations."""
        result = simple_world_map.get_route("ashford", "nowhere")
        assert result is None

    def test_merge_locations_adds_new_data(self, simple_world_map):
        """merge_locations() incorporates locations and routes from another WorldMap."""
        new_loc = LocationNode(
            id="riverport",
            display_name="Riverport",
            x=50,
            y=5,
            location_type="city",
            terrain="coastal",
            feature="A bustling port.",
            zones=[],
            connections=[],
            icon="#",
            tier=2,
        )
        new_route = TravelRoute(
            from_id="stonegate",
            to_id="riverport",
            travel_days=3,
            terrain="trail",
            danger_level=2,
            description="A long mountain trail.",
        )
        other = WorldMap(
            world_id="extra",
            display_name="Extra",
            system_id="burnwillow",
            seed=99,
            bounds=(80, 40),
            locations={"riverport": new_loc},
            routes=[new_route],
            start_location_id="riverport",
        )
        simple_world_map.merge_locations(other)

        assert "riverport" in simple_world_map.locations
        assert simple_world_map.get_route("stonegate", "riverport") is not None

    def test_from_grapes_geography_factory(self):
        """from_grapes_geography() creates a WorldMap with one node per Landmark."""
        landmarks = [
            Landmark(name="Ashford Keep", terrain="plains", feature="A fort on the plains."),
            Landmark(name="The Dark Spire", terrain="mountain", feature="A forbidding peak."),
            Landmark(name="Sunken Bay", terrain="coastal", feature="A sea-cliffed harbour."),
        ]
        profile = GrapesProfile(geography=landmarks)

        wm = WorldMap.from_grapes_geography(
            profile=profile,
            world_id="grapes_world",
            system_id="burnwillow",
            seed=7,
        )

        assert wm.world_id == "grapes_world"
        assert len(wm.locations) == 3
        # Each landmark should produce a LocationNode with grapes_landmark_index set
        for idx, node in enumerate(wm.locations.values()):
            assert node.grapes_landmark_index is not None
        # First node is the starting location
        assert wm.start_location_id != ""
        start = wm.locations[wm.start_location_id]
        assert start.is_starting_location is True


# =============================================================================
# MODULE MANIFEST TESTS (~8 tests)
# =============================================================================

class TestZoneEntry:
    """ZoneEntry creation and defaults."""

    def test_creation_defaults(self):
        """ZoneEntry uses expected default values when optional fields omitted."""
        entry = ZoneEntry(zone_id="my_zone")
        assert entry.blueprint is None
        assert entry.topology == "dungeon"
        assert entry.theme == "STONE"
        assert entry.location_id == ""
        assert entry.entry_trigger == "module_start"
        assert entry.exit_trigger == "boss_defeated"
        assert entry.generation_params is None

    def test_to_from_dict_round_trip(self, zone_entry_blueprint):
        """ZoneEntry round-trips through serialization."""
        d = zone_entry_blueprint.to_dict()
        restored = ZoneEntry.from_dict(d)
        assert restored.zone_id == zone_entry_blueprint.zone_id
        assert restored.blueprint == zone_entry_blueprint.blueprint
        assert restored.topology == zone_entry_blueprint.topology
        assert restored.theme == zone_entry_blueprint.theme


class TestChapter:
    """Chapter creation and serialization."""

    def test_creation(self, sample_chapter):
        """Chapter stores ID, name, order, and zones."""
        ch = sample_chapter
        assert ch.chapter_id == "act_1"
        assert ch.order == 1
        assert len(ch.zones) == 2

    def test_to_from_dict_round_trip(self, sample_chapter):
        """Chapter round-trips through to_dict / from_dict."""
        d = sample_chapter.to_dict()
        restored = Chapter.from_dict(d)
        assert restored.chapter_id == sample_chapter.chapter_id
        assert restored.order == sample_chapter.order
        assert len(restored.zones) == len(sample_chapter.zones)


class TestModuleManifest:
    """ModuleManifest creation, traversal, serialization, and file I/O."""

    def test_creation(self, simple_manifest):
        """ModuleManifest stores module_id, system, and chapters."""
        m = simple_manifest
        assert m.module_id == "test_module"
        assert m.system_id == "burnwillow"
        assert len(m.chapters) == 1

    def test_get_zone_chain_flattened_order(self, simple_manifest):
        """get_zone_chain() returns a flat list of all chapter zones in order."""
        chain = simple_manifest.get_zone_chain()
        # Two zones in the single chapter
        assert len(chain) == 2
        assert chain[0].zone_id == "rat_cellar"
        assert chain[1].zone_id == "proc_dungeon"

    def test_get_next_zone_advances_within_chapter(self, simple_manifest):
        """get_next_zone() advances to the next zone inside the same chapter."""
        result = simple_manifest.get_next_zone(chapter_idx=0, zone_idx=0)
        assert result is not None
        new_ch_idx, new_z_idx, entry = result
        assert new_ch_idx == 0
        assert new_z_idx == 1
        assert entry.zone_id == "proc_dungeon"

    def test_get_next_zone_advances_to_next_chapter(self):
        """get_next_zone() moves to the first zone of the next chapter when current is exhausted."""
        ch1 = Chapter(
            chapter_id="c1",
            display_name="C1",
            order=1,
            zones=[ZoneEntry(zone_id="z1")],
        )
        ch2 = Chapter(
            chapter_id="c2",
            display_name="C2",
            order=2,
            zones=[ZoneEntry(zone_id="z2")],
        )
        manifest = ModuleManifest(
            module_id="m",
            display_name="M",
            system_id="x",
            chapters=[ch1, ch2],
        )
        result = manifest.get_next_zone(chapter_idx=0, zone_idx=0)
        assert result is not None
        new_ch_idx, new_z_idx, entry = result
        assert new_ch_idx == 1
        assert new_z_idx == 0
        assert entry.zone_id == "z2"

    def test_get_next_zone_returns_none_at_end(self, simple_manifest):
        """get_next_zone() returns None when at the last zone of the last chapter."""
        # Chapter has 2 zones (indices 0 and 1). Requesting next from index 1 should be None.
        result = simple_manifest.get_next_zone(chapter_idx=0, zone_idx=1)
        assert result is None

    def test_to_from_dict_round_trip(self, simple_manifest):
        """ModuleManifest round-trips through to_dict / from_dict."""
        d = simple_manifest.to_dict()
        restored = ModuleManifest.from_dict(d)
        assert restored.module_id == simple_manifest.module_id
        assert restored.system_id == simple_manifest.system_id
        assert len(restored.chapters) == len(simple_manifest.chapters)

    def test_load_from_json_file(self):
        """ModuleManifest.load() correctly deserializes the sample JSON manifest."""
        manifest = ModuleManifest.load(_MANIFEST_PATH)
        assert manifest.module_id == "sample_module"
        assert manifest.display_name == "The Rat King's Cellar"
        assert manifest.system_id == "dnd5e"
        assert manifest.starting_location == "millhaven"
        assert len(manifest.chapters) == 2
        # Ch1 has 2 zones
        ch1_zones = manifest.chapters[0].zones
        assert len(ch1_zones) == 2
        # Freeform zones exist
        assert len(manifest.freeform_zones) == 1
        assert manifest.freeform_zones[0].zone_id == "wilderness_road"

    def test_recommended_levels_field(self):
        """ModuleManifest.load() correctly reads recommended_levels."""
        manifest = ModuleManifest.load(_MANIFEST_PATH)
        assert manifest.recommended_levels["min"] == 1
        assert manifest.recommended_levels["max"] == 3


# =============================================================================
# ZONE LOADER TESTS (~5 tests)
# =============================================================================

class TestZoneLoader:
    """ZoneLoader: blueprint loading and procedural generation."""

    def test_load_blueprint_hideout(self):
        """load_blueprint() loads the hideout.json and returns a DungeonGraph."""
        loader = ZoneLoader(base_path=str(_SAMPLE_DIR))
        graph = loader.load_blueprint("hideout.json")
        assert isinstance(graph, DungeonGraph)
        assert len(graph.rooms) > 0

    def test_blueprint_room_count_and_connections(self):
        """Blueprint graph has exactly 6 rooms with the expected connectivity."""
        loader = ZoneLoader(base_path=str(_SAMPLE_DIR))
        graph = loader.load_blueprint("hideout.json")
        # hideout.json defines rooms 0-5
        assert len(graph.rooms) == 6
        # Room 0 connects to room 1
        room_0 = graph.rooms[0]
        assert 1 in room_0.connections

    def test_procedural_dungeon_topology(self, zone_entry_procedural):
        """generate_procedural() with topology='dungeon' yields a non-empty DungeonGraph."""
        loader = ZoneLoader()
        graph = loader.generate_procedural(zone_entry_procedural)
        assert isinstance(graph, DungeonGraph)
        assert len(graph.rooms) > 0
        assert graph.seed == 12345

    def test_procedural_wilderness_topology(self):
        """generate_procedural() with topology='wilderness' produces rooms without error."""
        entry = ZoneEntry(
            zone_id="wild_zone",
            topology="wilderness",
            generation_params={"seed": 77, "width": 40, "height": 40, "room_count": 6},
        )
        loader = ZoneLoader()
        graph = loader.generate_procedural(entry)
        assert isinstance(graph, DungeonGraph)
        assert len(graph.rooms) >= 1

    def test_procedural_settlement_topology(self):
        """generate_procedural() with topology='settlement' produces rooms without error."""
        entry = ZoneEntry(
            zone_id="settle_zone",
            topology="settlement",
            generation_params={"seed": 55, "width": 40, "height": 40, "building_count": 5},
        )
        loader = ZoneLoader()
        graph = loader.generate_procedural(entry)
        assert isinstance(graph, DungeonGraph)
        assert len(graph.rooms) >= 1


# =============================================================================
# SETTLEMENT ADAPTER TESTS (~5 tests)
# =============================================================================

class TestSettlementAdapter:
    """SettlementAdapter: creation, default content, and content_hints overrides."""

    def test_creation_no_hints(self):
        """SettlementAdapter can be constructed with no arguments."""
        adapter = SettlementAdapter()
        assert adapter.content_hints == {}

    def test_populate_room_returns_populated_room(self, simple_room_node):
        """populate_room() returns a PopulatedRoom with the expected content keys."""
        adapter = SettlementAdapter()
        result = adapter.populate_room(simple_room_node)
        assert result is not None
        assert result.geometry is simple_room_node
        content = result.content
        assert "npcs" in content
        assert "services" in content
        assert "description" in content
        assert "enemies" in content
        assert "loot" in content

    def test_tavern_room_default_npcs(self, simple_room_node):
        """Tavern rooms receive the Barkeep NPC by default."""
        adapter = SettlementAdapter()
        result = adapter.populate_room(simple_room_node)
        npcs = result.content["npcs"]
        assert len(npcs) > 0
        assert any(npc["role"] == "innkeeper" for npc in npcs)

    def test_temple_room_default_services(self):
        """Temple rooms receive heal/cure/bless services by default."""
        room = RoomNode(
            id=3,
            x=5,
            y=25,
            width=8,
            height=6,
            room_type=RoomType.TEMPLE,
            connections=[0],
            tier=1,
        )
        adapter = SettlementAdapter()
        result = adapter.populate_room(room)
        services = result.content["services"]
        assert "heal" in services
        assert "bless" in services

    def test_content_hints_override_defaults(self, simple_room_node):
        """content_hints on the RoomNode take priority over defaults."""
        custom_npc = [{"name": "Mira", "role": "bard", "dialogue": "Singing for silver!"}]
        simple_room_node.content_hints = {"npcs": custom_npc, "services": ["music"]}
        adapter = SettlementAdapter()
        result = adapter.populate_room(simple_room_node)
        assert result.content["npcs"] == custom_npc
        assert "music" in result.content["services"]

    def test_settlements_have_no_enemies_or_loot(self, simple_room_node):
        """Settlements are safe zones: enemies and loot are always empty."""
        adapter = SettlementAdapter()
        result = adapter.populate_room(simple_room_node)
        assert result.content["enemies"] == []
        assert result.content["loot"] == []


# =============================================================================
# DUNGEON GRAPH BACKWARD COMPATIBILITY TESTS (~4 tests)
# =============================================================================

class TestDungeonGraphBackwardCompat:
    """RoomNode.content_hints and DungeonGraph.metadata serialization."""

    def test_room_node_without_content_hints_serializes_clean(self):
        """RoomNode with content_hints=None does NOT include 'content_hints' key in dict."""
        room = RoomNode(
            id=0, x=0, y=0, width=5, height=5,
            room_type=RoomType.NORMAL,
            content_hints=None,
        )
        d = room.to_dict()
        assert "content_hints" not in d

    def test_room_node_with_content_hints_serializes_correctly(self):
        """RoomNode with content_hints includes the field in serialized dict."""
        hints = {"description": "A dark alcove.", "enemies": []}
        room = RoomNode(
            id=1, x=0, y=0, width=5, height=5,
            room_type=RoomType.SECRET,
            content_hints=hints,
        )
        d = room.to_dict()
        assert "content_hints" in d
        assert d["content_hints"]["description"] == "A dark alcove."

    def test_dungeon_graph_with_metadata_serializes_correctly(self):
        """DungeonGraph with metadata includes the field in serialized dict."""
        room = RoomNode(id=0, x=0, y=0, width=5, height=5, room_type=RoomType.START)
        graph = DungeonGraph(
            seed=1,
            width=50,
            height=50,
            rooms={0: room},
            start_room_id=0,
            metadata={"zone_id": "test_zone", "theme": "RUST"},
        )
        d = graph.to_dict()
        assert "metadata" in d
        assert d["metadata"]["zone_id"] == "test_zone"

    def test_old_format_dungeon_graph_deserializes_without_metadata(self):
        """DungeonGraph.from_dict() handles old JSON that omits 'metadata' and 'content_hints'."""
        old_format = {
            "seed": 999,
            "width": 30,
            "height": 30,
            "start_room_id": 0,
            "rooms": {
                "0": {
                    "id": 0, "x": 5, "y": 5, "width": 6, "height": 5,
                    "room_type": "start",
                    "connections": [],
                    "tier": 1,
                    "is_locked": False,
                    "is_secret": False,
                    # No "content_hints" key — old format
                }
            }
            # No "metadata" key — old format
        }
        graph = DungeonGraph.from_dict(old_format)
        assert graph.metadata is None
        assert graph.rooms[0].content_hints is None
        assert graph.seed == 999

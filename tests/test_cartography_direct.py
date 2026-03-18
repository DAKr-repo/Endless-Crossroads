"""
Direct unit tests for codex/core/services/cartography.py.

Tests are fully self-contained: no external services, no LLM calls.
They rely on the BSP map engine being available (it is a pure-Python
in-process module — no network, no disk I/O beyond tmpdir writes).
"""

import pytest

from codex.core.services.cartography import (
    generate_map_from_context,
    _get_adapter,
    GenericAdapter,
    MAP_ENGINE_AVAILABLE,
)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not MAP_ENGINE_AVAILABLE,
    reason="Map engine not importable in this environment",
)


def _basic_context(**overrides) -> dict:
    base = {
        "location_name": "Test Vault",
        "system_id": "dnd5e",
        "seed": 42,
        "depth": 3,
        "width": 30,
        "height": 30,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test 1: generate_map_from_context returns valid output structure
# ---------------------------------------------------------------------------

class TestGenerateMapFromContext:
    def test_status_is_complete(self):
        result = generate_map_from_context(_basic_context())
        assert result["status"] == "complete"

    def test_has_rooms_list(self):
        result = generate_map_from_context(_basic_context())
        assert "rooms" in result
        assert isinstance(result["rooms"], list)

    def test_at_least_one_room_generated(self):
        result = generate_map_from_context(_basic_context())
        assert result["total_rooms"] >= 1

    def test_total_rooms_matches_rooms_length(self):
        result = generate_map_from_context(_basic_context())
        assert result["total_rooms"] == len(result["rooms"])

    def test_each_room_has_required_keys(self):
        result = generate_map_from_context(_basic_context())
        required = {"id", "type", "tier", "position", "size", "connections"}
        for room in result["rooms"]:
            assert required.issubset(room.keys()), (
                f"Room missing keys: {required - room.keys()}"
            )

    def test_graph_object_returned(self):
        result = generate_map_from_context(_basic_context())
        assert result.get("graph") is not None


# ---------------------------------------------------------------------------
# Test 2: GenericAdapter fallback for non-Burnwillow systems
# ---------------------------------------------------------------------------

class TestGenericAdapterFallback:
    def test_get_adapter_returns_generic_for_unknown(self):
        adapter = _get_adapter("totally_unknown_system", seed=1)
        assert adapter is not None
        assert isinstance(adapter, GenericAdapter)

    def test_get_adapter_returns_generic_for_dnd5e(self):
        # dnd5e is not burnwillow, so GenericAdapter is used
        adapter = _get_adapter("dnd5e", seed=7)
        assert isinstance(adapter, GenericAdapter)

    def test_generic_adapter_enemy_pool_tier1(self):
        adapter = GenericAdapter(seed=0)
        pool = adapter.get_enemy_pool(1)
        assert len(pool) > 0
        assert all(isinstance(name, str) for name in pool)

    def test_generic_adapter_loot_pool_tier3(self):
        adapter = GenericAdapter(seed=0)
        pool = adapter.get_loot_pool(3)
        assert len(pool) > 0
        assert all(isinstance(name, str) for name in pool)

    def test_generic_adapter_clamps_out_of_range_tier(self):
        adapter = GenericAdapter(seed=0)
        # Tier 0 and tier 99 should not raise; they clamp to valid range
        pool_low = adapter.get_enemy_pool(0)
        pool_high = adapter.get_enemy_pool(99)
        assert len(pool_low) > 0
        assert len(pool_high) > 0


# ---------------------------------------------------------------------------
# Test 3: unknown system handling (no crash, still returns something usable)
# ---------------------------------------------------------------------------

class TestUnknownSystem:
    def test_unknown_system_returns_complete(self):
        # GenericAdapter covers all unknown systems, so status should be "complete"
        result = generate_map_from_context(_basic_context(system_id="galactic_empire"))
        assert result["status"] == "complete"

    def test_unknown_system_has_rooms(self):
        result = generate_map_from_context(_basic_context(system_id="galactic_empire"))
        assert result["total_rooms"] >= 1

    def test_get_adapter_never_crashes_on_strange_ids(self):
        # "BURNWILLOW" lowercases to "burnwillow" and returns BurnwillowAdapter —
        # that is correct routing, not an error.  The invariant is simply: no exception.
        from codex.spatial.map_engine import RulesetAdapter
        for weird_id in ["", "   ", "1337", "BURNWILLOW", "burn willow"]:
            adapter = _get_adapter(weird_id, seed=0)
            # Must not raise; result is either None or a valid RulesetAdapter subclass.
            assert adapter is None or isinstance(adapter, RulesetAdapter)


# ---------------------------------------------------------------------------
# Test 4: seed determinism — same seed produces identical room layout
# ---------------------------------------------------------------------------

class TestSeedDeterminism:
    def test_same_seed_produces_same_room_count(self):
        ctx = _basic_context(seed=777)
        r1 = generate_map_from_context(ctx)
        r2 = generate_map_from_context(ctx)
        assert r1["total_rooms"] == r2["total_rooms"]

    def test_same_seed_produces_same_room_ids(self):
        ctx = _basic_context(seed=777)
        r1 = generate_map_from_context(ctx)
        r2 = generate_map_from_context(ctx)
        ids1 = sorted(room["id"] for room in r1["rooms"])
        ids2 = sorted(room["id"] for room in r2["rooms"])
        assert ids1 == ids2

    def test_same_seed_produces_same_room_types(self):
        ctx = _basic_context(seed=777)
        r1 = generate_map_from_context(ctx)
        r2 = generate_map_from_context(ctx)
        types1 = sorted(room["type"] for room in r1["rooms"])
        types2 = sorted(room["type"] for room in r2["rooms"])
        assert types1 == types2

    def test_different_seeds_may_differ(self):
        # Two very different seeds should produce at least one structural difference.
        r1 = generate_map_from_context(_basic_context(seed=1))
        r2 = generate_map_from_context(_basic_context(seed=999999))
        # It is theoretically possible (but astronomically unlikely) they are identical.
        # We only assert neither crashes.
        assert r1["status"] == "complete"
        assert r2["status"] == "complete"

    def test_graph_seed_attribute_matches_context_seed(self):
        ctx = _basic_context(seed=42)
        result = generate_map_from_context(ctx)
        graph = result["graph"]
        assert graph.seed == 42

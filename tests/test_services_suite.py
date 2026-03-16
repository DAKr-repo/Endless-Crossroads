"""
tests/test_services_suite.py — Comprehensive services module test coverage.
============================================================================

Covers: broadcast, graveyard, narrative_loom.

WO-V51.0: The Foundation Sprint — Track A
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================
# BROADCAST TESTS (~8)
# =========================================================================

from codex.core.services.broadcast import GlobalBroadcastManager


class TestBroadcastSubscribeAndBroadcast:
    """subscribe + broadcast delivers payload to callback."""

    def test_subscribe_and_broadcast(self):
        mgr = GlobalBroadcastManager(system_theme="test")
        received = []
        mgr.subscribe("TEST_EVENT", lambda p: received.append(p))
        mgr.broadcast("TEST_EVENT", {"key": "value"})
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_broadcast_isolates_exceptions(self):
        mgr = GlobalBroadcastManager()
        results_ok = []

        def bad_listener(p):
            raise RuntimeError("boom")

        def good_listener(p):
            results_ok.append(p)
            return {"ok": True}

        mgr.subscribe("EV", bad_listener)
        mgr.subscribe("EV", good_listener)
        results = mgr.broadcast("EV", {"data": 1})
        assert len(results_ok) == 1
        assert len(results) == 1  # only good_listener returned non-None

    def test_broadcast_returns_non_none_only(self):
        mgr = GlobalBroadcastManager()
        mgr.subscribe("EV", lambda p: None)
        mgr.subscribe("EV", lambda p: {"ack": True})
        results = mgr.broadcast("EV", {})
        assert len(results) == 1

    def test_no_subscribers_returns_empty(self):
        mgr = GlobalBroadcastManager()
        results = mgr.broadcast("NOTHING", {"data": 1})
        assert results == []


class TestBroadcastUnsubscribe:
    """unsubscribe() returns False for unknown callback."""

    def test_unsubscribe_existing(self):
        mgr = GlobalBroadcastManager()
        cb = lambda p: None
        mgr.subscribe("EV", cb)
        assert mgr.unsubscribe("EV", cb) is True

    def test_unsubscribe_unknown(self):
        mgr = GlobalBroadcastManager()
        assert mgr.unsubscribe("EV", lambda p: None) is False


class TestBroadcastCrossModule:
    """broadcast_cross_module enriches payload."""

    @patch("codex.core.services.broadcast._log_crossroad_transmission")
    def test_cross_module_enriches_payload(self, mock_log):
        mgr = GlobalBroadcastManager()
        received = []
        mgr.subscribe("BOSS_SLAIN", lambda p: received.append(p))
        mgr.broadcast_cross_module("burnwillow", "BOSS_SLAIN",
                                    {"boss": "Dragon"}, universe_id="realm_1")
        assert len(received) == 1
        assert received[0]["_source_module"] == "burnwillow"
        assert received[0]["_universe_id"] == "realm_1"
        assert received[0]["boss"] == "Dragon"
        mock_log.assert_called_once()


class TestBroadcastClear:
    """clear() removes all listeners."""

    def test_clear_then_broadcast(self):
        mgr = GlobalBroadcastManager()
        mgr.subscribe("EV", lambda p: {"result": True})
        mgr.clear()
        results = mgr.broadcast("EV", {})
        assert results == []


# =========================================================================
# GRAVEYARD TESTS (~8)
# =========================================================================

from codex.core.services import graveyard as graveyard_mod


class TestGraveyardLogDeath:
    """log_death() writes file successfully."""

    def test_log_death_minimal(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        entry = graveyard_mod.log_death({"name": "Kael"}, system_id="burnwillow")
        assert entry["name"] == "Kael"
        assert entry["system_id"] == "burnwillow"
        assert entry["elegy"]  # non-empty
        # Verify file was written
        fpath = tmp_path / "burnwillow.json"
        assert fpath.exists()

    def test_log_death_deterministic_elegy(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        e1 = graveyard_mod.log_death({"name": "Kael"}, system_id="burnwillow")
        # Same name → same elegy (deterministic via sum(ord(c)) % 8)
        expected_idx = sum(ord(c) for c in "Kael") % 8
        assert e1["elegy"] == graveyard_mod._ELEGIES[expected_idx]


class TestGraveyardListFallen:
    """list_fallen() all / single / empty."""

    def test_list_fallen_all_systems(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        graveyard_mod.log_death({"name": "A"}, system_id="burnwillow")
        graveyard_mod.log_death({"name": "B"}, system_id="dnd5e")
        fallen = graveyard_mod.list_fallen()
        assert "burnwillow" in fallen
        assert "dnd5e" in fallen

    def test_list_fallen_single_system(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        graveyard_mod.log_death({"name": "A"}, system_id="burnwillow")
        graveyard_mod.log_death({"name": "B"}, system_id="dnd5e")
        fallen = graveyard_mod.list_fallen(system_id="burnwillow")
        assert "burnwillow" in fallen
        assert "dnd5e" not in fallen

    def test_list_fallen_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        fallen = graveyard_mod.list_fallen()
        assert fallen == {}


class TestGraveyardGetElegy:
    """get_elegy() case-insensitive, most recent, None for unknown."""

    def test_get_elegy_case_insensitive(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        graveyard_mod.log_death({"name": "Kael"}, system_id="burnwillow")
        entry = graveyard_mod.get_elegy("burnwillow", "kael")
        assert entry is not None
        assert entry["name"] == "Kael"

    def test_get_elegy_most_recent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        graveyard_mod.log_death({"name": "Kael", "cause": "first"}, system_id="bw")
        graveyard_mod.log_death({"name": "Kael", "cause": "second"}, system_id="bw")
        entry = graveyard_mod.get_elegy("bw", "Kael")
        assert entry["cause"] == "second"

    def test_get_elegy_unknown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        assert graveyard_mod.get_elegy("burnwillow", "Nobody") is None


class TestGraveyardSystems:
    """get_graveyard_systems() sorted list."""

    def test_sorted_systems(self, tmp_path, monkeypatch):
        monkeypatch.setattr(graveyard_mod, "_GRAVEYARD_DIR", tmp_path)
        graveyard_mod.log_death({"name": "A"}, system_id="dnd5e")
        graveyard_mod.log_death({"name": "B"}, system_id="burnwillow")
        systems = graveyard_mod.get_graveyard_systems()
        assert systems == ["burnwillow", "dnd5e"]


# =========================================================================
# NARRATIVE LOOM TESTS (~5)
# =========================================================================

from codex.core.services.narrative_loom import (
    format_session_stats,
    diagnostic_trace,
    SessionManifest,
    _hash_shards,
    _MEMORY_AVAILABLE,
)


class TestFormatSessionStats:
    """format_session_stats() extracts kills/loot/rooms."""

    def test_extracts_from_session_log(self):
        session_log = [
            {"type": "kill", "tier": 1},
            {"type": "kill", "tier": 2},
            {"type": "loot", "item_name": "Sword"},
            {"type": "room_entered"},
            {"type": "room_cleared"},
        ]
        engine_snapshot = {"party": [], "doom": 5, "turns": 10, "chapter": 1,
                           "completed_quests": ["Save the Town"]}
        stats = format_session_stats(session_log, engine_snapshot)
        assert stats["kills"]["total"] == 2
        assert stats["kills"]["by_tier"] == {1: 1, 2: 1}
        assert stats["loot"] == ["Sword"]
        assert stats["rooms_explored"] == 1
        assert stats["rooms_cleared"] == 1
        assert "Save the Town" in stats["quests_completed"]


@pytest.mark.skipif(not _MEMORY_AVAILABLE, reason="Memory module not available")
class TestDiagnosticTrace:
    """diagnostic_trace() relevance scoring (only if MemoryShard available)."""

    def test_relevance_sorted_descending(self):
        from codex.core.memory import MemoryShard, ShardType
        shards = [
            MemoryShard(shard_type=ShardType.MASTER,
                        content="The king is alive and well.", source="lore"),
            MemoryShard(shard_type=ShardType.CHRONICLE,
                        content="The king was seen at the market.", source="session"),
        ]
        results = diagnostic_trace("the king", shards)
        assert len(results) >= 1
        # Results should be sorted by relevance descending
        if len(results) > 1:
            assert results[0]["relevance"] >= results[1]["relevance"]

    def test_no_match_returns_empty(self):
        from codex.core.memory import MemoryShard, ShardType
        shards = [
            MemoryShard(shard_type=ShardType.MASTER,
                        content="Nothing about dragons here.", source="lore"),
        ]
        results = diagnostic_trace("unicorn fairy", shards)
        assert results == []


class TestSessionManifest:
    """SessionManifest serialization and staleness."""

    def test_to_dict_from_dict_roundtrip(self):
        sm = SessionManifest(
            session_id="test_001",
            anchored_shards=["shard_1", "shard_2"],
            compiled_narrative="The story so far...",
            content_hash="abc123",
        )
        d = sm.to_dict()
        sm2 = SessionManifest.from_dict(d)
        assert sm2.session_id == "test_001"
        assert sm2.anchored_shards == ["shard_1", "shard_2"]
        assert sm2.compiled_narrative == "The story so far..."
        assert sm2.content_hash == "abc123"

    @pytest.mark.skipif(not _MEMORY_AVAILABLE, reason="Memory module not available")
    def test_is_stale_on_content_change(self):
        from codex.core.memory import MemoryShard, ShardType
        shards_v1 = [
            MemoryShard(shard_type=ShardType.MASTER, content="Version 1",
                        source="test"),
        ]
        shards_v2 = [
            MemoryShard(shard_type=ShardType.MASTER, content="Version 2",
                        source="test"),
        ]
        sm = SessionManifest(session_id="s1",
                              content_hash=_hash_shards(shards_v1))
        assert sm.is_stale(shards_v1) is False
        assert sm.is_stale(shards_v2) is True

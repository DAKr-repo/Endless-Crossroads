"""
Direct unit tests for codex/core/services/universe_manager.py

Covers:
- create_universe
- link_module / unlink_module
- are_linked check
- get_universe_for_module
- persistence round-trip (to_dict / from_dict)
- empty defaults on fresh instance
"""

import json
import tempfile
from pathlib import Path

import pytest

from codex.core.services.universe_manager import UniverseLink, UniverseManager


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_manager(tmp_path: Path) -> UniverseManager:
    """Create a UniverseManager that writes to a temp file (no real saves dir)."""
    registry = tmp_path / "universe_registry.json"
    return UniverseManager(config_path=registry)


# ── Tests ─────────────────────────────────────────────────────────────────

class TestEmptyDefaults:
    """A brand-new UniverseManager has no universes."""

    def test_list_universes_empty(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.list_universes() == []

    def test_get_universe_for_unknown_module_returns_none(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_universe_for_module("mod_x") is None


class TestCreateUniverse:
    """create_universe returns and persists a UniverseLink."""

    def test_create_returns_universe_link(self, tmp_path):
        mgr = _make_manager(tmp_path)
        link = mgr.create_universe("alpha")
        assert isinstance(link, UniverseLink)
        assert link.universe_id == "alpha"
        assert link.modules == []

    def test_create_appears_in_list(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_universe("beta")
        ids = [u.universe_id for u in mgr.list_universes()]
        assert "beta" in ids

    def test_create_writes_registry_file(self, tmp_path):
        registry = tmp_path / "universe_registry.json"
        mgr = UniverseManager(config_path=registry)
        mgr.create_universe("gamma")
        assert registry.exists()
        data = json.loads(registry.read_text())
        assert "gamma" in data["universes"]


class TestLinkUnlink:
    """link_module and unlink_module mutate the universe correctly."""

    def test_link_module_creates_universe_if_absent(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("delta", "mod_a")
        assert mgr.get_universe_for_module("mod_a") == "delta"

    def test_link_module_idempotent(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("eps", "mod_b")
        mgr.link_module("eps", "mod_b")  # second call must not duplicate
        link = next(u for u in mgr.list_universes() if u.universe_id == "eps")
        assert link.modules.count("mod_b") == 1

    def test_unlink_module_removes_module(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("zeta", "mod_c")
        mgr.unlink_module("zeta", "mod_c")
        assert mgr.get_universe_for_module("mod_c") is None

    def test_unlink_nonexistent_module_is_safe(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_universe("eta")
        # Should not raise even though mod_ghost was never linked.
        mgr.unlink_module("eta", "mod_ghost")


class TestAreLinked:
    """are_linked returns True iff both modules share a universe."""

    def test_linked_modules_return_true(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("theta", "mod_x")
        mgr.link_module("theta", "mod_y")
        assert mgr.are_linked("mod_x", "mod_y") is True

    def test_unlinked_modules_return_false(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("iota", "mod_p")
        mgr.link_module("kappa", "mod_q")
        assert mgr.are_linked("mod_p", "mod_q") is False

    def test_one_unregistered_module_returns_false(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("lambda", "mod_r")
        assert mgr.are_linked("mod_r", "mod_ghost") is False


class TestPersistenceRoundTrip:
    """to_dict / from_dict preserve universe state exactly."""

    def test_to_dict_structure(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("mu", "mod_s")
        mgr.link_module("mu", "mod_t")
        d = mgr.to_dict()
        assert "universes" in d
        assert "mu" in d["universes"]
        assert set(d["universes"]["mu"]["modules"]) == {"mod_s", "mod_t"}

    def test_from_dict_restores_modules(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.link_module("nu", "mod_u")
        mgr.link_module("nu", "mod_v")
        restored = UniverseManager.from_dict(mgr.to_dict())
        assert "nu" in restored
        assert set(restored["nu"].modules) == {"mod_u", "mod_v"}

    def test_save_load_round_trip(self, tmp_path):
        """Saving and re-loading from disk gives identical state."""
        registry = tmp_path / "universe_registry.json"
        mgr = UniverseManager(config_path=registry)
        mgr.link_module("xi", "mod_w")
        mgr.link_module("xi", "mod_x")

        # Fresh manager from same file
        mgr2 = UniverseManager(config_path=registry)
        assert mgr2.are_linked("mod_w", "mod_x") is True
        assert mgr2.get_universe_for_module("mod_w") == "xi"

    def test_corrupted_registry_falls_back_to_empty(self, tmp_path):
        registry = tmp_path / "universe_registry.json"
        registry.write_text("this is not json{{{")
        mgr = UniverseManager(config_path=registry)
        assert mgr.list_universes() == []

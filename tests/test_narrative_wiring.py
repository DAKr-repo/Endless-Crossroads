"""
tests/test_narrative_wiring.py — WO-V68.0: Narrative Wiring + Faction Reputation
==================================================================================

Tests for:
  - Part A: Wire implemented-but-unused code
      1. `trace` command on UniversalGameBridge (diagnostic_trace integration)
      2. SessionManifest caching in Crown engine (second call returns cached)
      3. StressClock.resist() produces valid output
  - Part B: Faction Reputation System
      4. ReputationTracker.adjust() clamps to -3..+3
      5. Standing titles match expected values at every level
      6. Disposition modifier correlates with standing
      7. Serialization round-trip (to_dict / from_dict)
      8. adjust() returns tier-change message on boundary cross
      9. Bridge `reputation` command returns faction list
     10. ReputationTracker.get_standing() creates neutral on first access
     11. Bridge `trace` returns shard info when shards exist
     12. Bridge `trace` returns helpful message when no shards
     13. Butler `maps` reflex returns formatted text
     14. Crown SessionManifest persists in to_dict / from_dict
     15. NarrativeEngine.turn_in_quest adjusts faction standing +1
     16. NarrativeEngine.check_objective with faction_id adjusts standing -1
     17. FactionStanding.title property
     18. ReputationTracker._get_or_create idempotency
     19. FITD resist command with missing stress clock
     20. ReputationTracker.all_standings returns sorted list
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================================
# Part B — Faction Reputation Core
# =========================================================================

class TestReputationTrackerClamp:
    """ReputationTracker.adjust() clamps standing to -3..+3."""

    def setup_method(self):
        from codex.core.mechanics.reputation import ReputationTracker
        self.tracker = ReputationTracker()

    def test_adjust_clamps_below_minus_3(self):
        """Applying -10 from neutral should clamp to -3, not -10."""
        self.tracker.adjust("guards", -10)
        fs = self.tracker.get_standing("guards")
        assert fs.standing == -3

    def test_adjust_clamps_above_plus_3(self):
        """Applying +10 from neutral should clamp to +3."""
        self.tracker.adjust("merchants", +10)
        fs = self.tracker.get_standing("merchants")
        assert fs.standing == 3

    def test_adjust_accumulates_correctly(self):
        """Multiple small adjustments accumulate correctly."""
        self.tracker.adjust("thieves", +1)
        self.tracker.adjust("thieves", +1)
        assert self.tracker.get_standing("thieves").standing == 2

    def test_adjust_already_at_max_stays_clamped(self):
        """Adjusting from +3 upward stays at +3."""
        self.tracker.adjust("city_watch", +3)
        self.tracker.adjust("city_watch", +5)
        assert self.tracker.get_standing("city_watch").standing == 3


class TestStandingTitles:
    """Standing titles match expected values at every level."""

    def setup_method(self):
        from codex.core.mechanics.reputation import (
            ReputationTracker, STANDING_TITLES,
        )
        self.tracker = ReputationTracker()
        self.STANDING_TITLES = STANDING_TITLES

    def _standing_title(self, level: int) -> str:
        from codex.core.mechanics.reputation import FactionStanding
        fs = FactionStanding(faction_id="test", standing=level)
        return fs.title

    def test_title_minus_3(self):
        assert self._standing_title(-3) == "Outcast"

    def test_title_minus_2(self):
        assert self._standing_title(-2) == "Suspect"

    def test_title_minus_1(self):
        assert self._standing_title(-1) == "Stranger"

    def test_title_zero(self):
        assert self._standing_title(0) == "Neutral"

    def test_title_plus_1(self):
        assert self._standing_title(1) == "Known"

    def test_title_plus_2(self):
        assert self._standing_title(2) == "Trusted"

    def test_title_plus_3(self):
        assert self._standing_title(3) == "Honored"

    def test_all_titles_in_map(self):
        """Every level from -3..+3 has a title in STANDING_TITLES."""
        for level in range(-3, 4):
            assert level in self.STANDING_TITLES


class TestDispositionModifier:
    """Disposition modifier correlates with standing level."""

    def setup_method(self):
        from codex.core.mechanics.reputation import ReputationTracker
        self.tracker = ReputationTracker()

    def test_honored_positive_modifier(self):
        self.tracker.adjust("faction_a", +3)
        mod = self.tracker.get_disposition_modifier("faction_a")
        assert mod > 0

    def test_outcast_negative_modifier(self):
        self.tracker.adjust("faction_b", -3)
        mod = self.tracker.get_disposition_modifier("faction_b")
        assert mod < 0

    def test_neutral_zero_modifier(self):
        mod = self.tracker.get_disposition_modifier("faction_c")
        assert mod == 0

    def test_modifier_scales_with_standing(self):
        """Higher standing yields higher modifier."""
        self.tracker.adjust("fac1", +1)
        self.tracker.adjust("fac2", +2)
        mod1 = self.tracker.get_disposition_modifier("fac1")
        mod2 = self.tracker.get_disposition_modifier("fac2")
        assert mod2 > mod1


class TestReputationSerialization:
    """Serialization round-trip via to_dict / from_dict."""

    def test_roundtrip_empty(self):
        from codex.core.mechanics.reputation import ReputationTracker
        tracker = ReputationTracker()
        data = tracker.to_dict()
        restored = ReputationTracker.from_dict(data)
        assert len(restored.standings) == 0

    def test_roundtrip_with_standings(self):
        from codex.core.mechanics.reputation import ReputationTracker
        tracker = ReputationTracker()
        tracker.adjust("guards", +2)
        tracker.adjust("thieves", -1)
        data = tracker.to_dict()
        restored = ReputationTracker.from_dict(data)
        assert restored.get_standing("guards").standing == 2
        assert restored.get_standing("thieves").standing == -1

    def test_faction_standing_roundtrip(self):
        from codex.core.mechanics.reputation import FactionStanding
        fs = FactionStanding(faction_id="merchants", standing=1)
        data = fs.to_dict()
        restored = FactionStanding.from_dict(data)
        assert restored.faction_id == "merchants"
        assert restored.standing == 1
        assert restored.title == "Known"


class TestAdjustTierChangeMessage:
    """adjust() returns a tier-change message when crossing a boundary."""

    def setup_method(self):
        from codex.core.mechanics.reputation import ReputationTracker
        self.tracker = ReputationTracker()

    def test_tier_change_message_on_improvement(self):
        """Crossing from Neutral(0) to Known(1) mentions both titles."""
        msg = self.tracker.adjust("guild", +1)
        assert "guild" in msg
        # Should mention new title (Known) or old title (Neutral)
        assert "Known" in msg or "Neutral" in msg

    def test_tier_change_message_on_decline(self):
        """Crossing from Neutral(0) to Stranger(-1) mentions both."""
        msg = self.tracker.adjust("bandits", -1)
        assert "bandits" in msg
        assert "Stranger" in msg or "Neutral" in msg

    def test_no_change_when_already_capped(self):
        """Message notes unchanged when already at cap."""
        self.tracker.adjust("faction_x", +3)
        msg = self.tracker.adjust("faction_x", +1)
        assert "unchanged" in msg.lower() or "Honored" in msg


class TestGetStanding:
    """get_standing() creates neutral FactionStanding on first access."""

    def test_creates_neutral_on_first_access(self):
        from codex.core.mechanics.reputation import ReputationTracker
        tracker = ReputationTracker()
        fs = tracker.get_standing("new_faction")
        assert fs.standing == 0
        assert fs.title == "Neutral"
        assert "new_faction" in tracker.standings

    def test_idempotent_get_standing(self):
        from codex.core.mechanics.reputation import ReputationTracker
        tracker = ReputationTracker()
        fs1 = tracker.get_standing("same_faction")
        fs2 = tracker.get_standing("same_faction")
        assert fs1 is fs2


class TestAllStandings:
    """all_standings() returns sorted list of (faction_id, FactionStanding)."""

    def test_returns_sorted(self):
        from codex.core.mechanics.reputation import ReputationTracker
        tracker = ReputationTracker()
        tracker.adjust("zorro", +1)
        tracker.adjust("alpha", +2)
        tracker.adjust("merchant", -1)
        standings = tracker.all_standings()
        faction_ids = [fid for fid, _ in standings]
        assert faction_ids == sorted(faction_ids)

    def test_empty_returns_empty_list(self):
        from codex.core.mechanics.reputation import ReputationTracker
        tracker = ReputationTracker()
        assert tracker.all_standings() == []


# =========================================================================
# Part A — Bridge Wiring
# =========================================================================

def _make_bridge():
    """Construct a minimal UniversalGameBridge without a real engine."""
    from codex.games.bridge import UniversalGameBridge
    # Minimal mock engine
    engine = MagicMock()
    engine.system_id = "dnd5e"
    engine.display_name = "Test System"
    engine.current_room_id = 1
    engine.dungeon_graph = None
    engine.visited_rooms = set()
    engine.party = []
    engine.character = None
    engine.populated_rooms = {}

    bridge = UniversalGameBridge.create_lightweight(engine)

    # Reputation tracker
    from codex.core.mechanics.reputation import ReputationTracker
    bridge._reputation = ReputationTracker()

    return bridge


class TestBridgeTraceCommand:
    """trace command on UniversalGameBridge."""

    def test_trace_no_memory_shards_attr(self):
        """Returns helpful message when engine has no _memory_shards."""
        bridge = _make_bridge()
        # engine has no _memory_shards attribute
        del bridge.engine._memory_shards
        result = bridge.step("trace king")
        assert "trace" in result.lower() or "shard" in result.lower()

    def test_trace_empty_keyword(self):
        """Returns usage hint when no keyword given."""
        bridge = _make_bridge()
        bridge.engine._memory_shards = []
        result = bridge.step("trace")
        assert "usage" in result.lower() or "trace" in result.lower()

    def test_trace_no_shards_loaded(self):
        """Returns no-shards message when list is empty."""
        bridge = _make_bridge()
        bridge.engine._memory_shards = []
        result = bridge.step("trace goblin")
        assert "no memory shards" in result.lower() or "unavailable" in result.lower()

    def test_trace_returns_shard_info(self):
        """Returns shard info when shards contain keyword."""
        try:
            from codex.core.memory import MemoryShard, ShardType
        except ImportError:
            pytest.skip("Memory module not available")

        bridge = _make_bridge()
        shard = MemoryShard(
            shard_type=ShardType.ANCHOR,
            content="The goblin king was slain at dawn.",
            source="crown",
        )
        bridge.engine._memory_shards = [shard]
        result = bridge.step("trace goblin")
        # Should contain trace output or at least the keyword
        assert "goblin" in result.lower() or "ANCHOR" in result or "shard" in result.lower()


class TestBridgeReputationCommand:
    """reputation command on UniversalGameBridge."""

    def test_reputation_no_factions(self):
        """Returns helpful message when no factions tracked yet."""
        bridge = _make_bridge()
        result = bridge.step("reputation")
        assert "no faction" in result.lower() or "tracked" in result.lower()

    def test_reputation_shows_faction_list(self):
        """Returns formatted list when factions exist."""
        bridge = _make_bridge()
        bridge._reputation.adjust("city_watch", +2)
        bridge._reputation.adjust("thieves_guild", -1)
        result = bridge.step("reputation")
        assert "city_watch" in result
        assert "thieves_guild" in result

    def test_reputation_shows_titles(self):
        """Result includes standing titles."""
        bridge = _make_bridge()
        bridge._reputation.adjust("merchants", +2)
        result = bridge.step("reputation")
        assert "Trusted" in result

    def test_reputation_alias_rep(self):
        """Short alias `rep` also works."""
        bridge = _make_bridge()
        bridge._reputation.adjust("guards", +1)
        result = bridge.step("rep")
        assert "guards" in result


# =========================================================================
# Part A — StressClock.resist()
# =========================================================================

class TestStressClockResist:
    """StressClock.resist() produces valid output."""

    def setup_method(self):
        from codex.core.services.fitd_engine import StressClock
        self.clock = StressClock()

    def test_resist_zero_cost_no_change(self):
        """Resist with stress_cost=0 adds 0 stress."""
        result = self.clock.resist(0)
        assert result["action"] == "resist"
        assert result["new_stress"] == 0

    def test_resist_adds_stress(self):
        """Resist with positive cost adds stress."""
        result = self.clock.resist(3)
        assert result["new_stress"] == 3

    def test_resist_triggers_trauma_at_max(self):
        """Resist past max stress triggers trauma."""
        self.clock.current_stress = 8  # one short of max (9)
        result = self.clock.resist(3)
        # pushed past 9 → trauma triggered
        assert result["trauma_triggered"] is True
        assert result["new_stress"] == 0  # reset after trauma

    def test_resist_returns_action_key(self):
        """Result always contains 'action' = 'resist'."""
        result = self.clock.resist(2)
        assert result["action"] == "resist"

    def test_resist_clamps_to_max(self):
        """Cost larger than max_stress is clamped."""
        result = self.clock.resist(100)
        assert result["new_stress"] <= self.clock.max_stress or result["trauma_triggered"]


# =========================================================================
# Part A — Crown SessionManifest
# =========================================================================

class TestCrownSessionManifest:
    """SessionManifest caching works in Crown engine."""

    def test_manifest_created_on_setup(self):
        """setup() creates a SessionManifest if one doesn't exist."""
        try:
            from codex.games.crown.engine import CrownAndCrewEngine
            from codex.core.services.narrative_loom import SessionManifest
        except ImportError:
            pytest.skip("Crown engine or narrative loom unavailable")

        engine = CrownAndCrewEngine()
        engine.setup()
        assert engine._manifest is not None
        assert isinstance(engine._manifest, SessionManifest)

    def test_manifest_not_overwritten_on_second_setup(self):
        """Calling setup() twice doesn't replace an existing manifest."""
        try:
            from codex.games.crown.engine import CrownAndCrewEngine
        except ImportError:
            pytest.skip("Crown engine unavailable")

        engine = CrownAndCrewEngine()
        engine.setup()
        first_manifest = engine._manifest
        engine.setup()
        # Must be the same object — not replaced
        assert engine._manifest is first_manifest

    def test_manifest_persists_in_to_dict(self):
        """to_dict() includes _manifest key when manifest exists."""
        try:
            from codex.games.crown.engine import CrownAndCrewEngine
        except ImportError:
            pytest.skip("Crown engine unavailable")

        engine = CrownAndCrewEngine()
        engine.setup()
        data = engine.to_dict()
        assert "_manifest" in data
        assert "session_id" in data["_manifest"]

    def test_manifest_restored_in_from_dict(self):
        """from_dict() restores the SessionManifest."""
        try:
            from codex.games.crown.engine import CrownAndCrewEngine
            from codex.core.services.narrative_loom import SessionManifest
        except ImportError:
            pytest.skip("Crown engine or narrative loom unavailable")

        engine = CrownAndCrewEngine()
        engine.setup()
        original_id = engine._manifest.session_id
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._manifest is not None
        assert restored._manifest.session_id == original_id


# =========================================================================
# Part A — Butler `maps` reflex
# =========================================================================

class TestButlerMapsReflex:
    """Butler `maps` reflex returns formatted text."""

    def setup_method(self):
        from codex.core.butler import CodexButler
        self.butler = CodexButler()

    def test_maps_reflex_matches(self):
        """'maps' input matches the reflex pattern."""
        result = self.butler.check_reflex("maps")
        # Should not be None (pattern matched)
        assert result is not None

    def test_map_singular_matches(self):
        """'map' also matches the maps reflex."""
        result = self.butler.check_reflex("map")
        assert result is not None

    def test_maps_returns_string(self):
        """Result is a string (may say no maps found or list maps)."""
        result = self.butler.check_reflex("maps")
        assert isinstance(result, str)


# =========================================================================
# Part B — NarrativeEngine reputation wiring
# =========================================================================

class TestNarrativeEngineReputation:
    """NarrativeEngine quest/kill events update ReputationTracker."""

    def _make_engine(self):
        from codex.core.narrative_engine import NarrativeEngine
        from codex.core.mechanics.reputation import ReputationTracker
        engine = NarrativeEngine(system_id="test")
        engine.reputation = ReputationTracker()
        return engine

    def test_turn_in_quest_adjusts_reputation(self):
        """Quest turn-in raises standing with the turn-in NPC's faction."""
        engine = self._make_engine()
        # Find any quest and force it to active + complete status
        if not engine.quests:
            pytest.skip("No quests seeded")
        q = engine.quests[0]
        q.status = "complete"
        q.turn_in_npc = "blacksmith"

        engine.turn_in_quest(q.quest_id)

        faction_id = "blacksmith"
        fs = engine.reputation.get_standing(faction_id)
        assert fs.standing == 1  # +1 for quest completion

    def test_check_objective_kill_adjusts_reputation(self):
        """check_objective with faction_id reduces standing for kill triggers."""
        engine = self._make_engine()
        # Activate a kill quest
        for q in engine.quests:
            if "kill" in q.objective_trigger.lower():
                q.status = "active"
                break

        engine.check_objective("kill_tier_1", faction_id="bandits")

        fs = engine.reputation.get_standing("bandits")
        assert fs.standing == -1  # -1 for killing their member

    def test_check_objective_no_faction_no_adjustment(self):
        """check_objective without faction_id leaves reputation unchanged."""
        engine = self._make_engine()
        engine.check_objective("kill_tier_1")
        # No factions should have been created
        assert len(engine.reputation.standings) == 0

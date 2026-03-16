"""
tests/test_anchor_shards.py — WO-V61.0 Track A
===============================================
Tests for:
1. _format_anchor() — all 9 event types + unknown fallback
2. format_session_stats() — anchor_moments key presence and filtering
3. summarize_session() — Key Moments section rendering + Mimir prompt content
4. UniversalGameBridge — _session_log init, _log_event, get_session_log
5. FITD engines — push_stress trauma ANCHOR shard emission (BitD detailed,
   SaV/BoB/CBR+PNK/Candela existence checks)
6. ANCHOR_EVENT_TYPES constant shape
"""

import pytest

from codex.core.services.narrative_loom import (
    ANCHOR_EVENT_TYPES,
    _format_anchor,
    format_session_stats,
    summarize_session,
)
from codex.games.bridge import UniversalGameBridge


# ===========================================================================
# TestFormatAnchor
# ===========================================================================

class TestFormatAnchor:
    """Unit-test every branch of _format_anchor()."""

    def test_near_death(self):
        event = {"type": "near_death", "name": "Kael", "hp": 3, "max_hp": 20, "attacker": "Ghoul"}
        result = _format_anchor(event)
        assert "Kael" in result
        assert "nearly fell" in result
        assert "3/20" in result

    def test_ally_saved(self):
        event = {"type": "ally_saved", "savior": "Mira", "saved": "Kael", "method": "triage"}
        result = _format_anchor(event)
        assert "Mira" in result
        assert "saved" in result
        assert "Kael" in result

    def test_critical_roll(self):
        event = {"type": "critical_roll", "roller": "Kael", "result": "critical", "context": "vs Ghoul"}
        result = _format_anchor(event)
        assert "critical" in result
        assert "Kael" in result

    def test_companion_fell(self):
        event = {"type": "companion_fell", "name": "Bot", "archetype": "guardian", "cause": "Dragon"}
        result = _format_anchor(event)
        assert "Bot" in result
        assert "guardian" in result

    def test_doom_threshold(self):
        event = {"type": "doom_threshold", "doom_value": 10, "event_text": "The air thickens"}
        result = _format_anchor(event)
        assert "Doom" in result
        assert "10" in result

    def test_zone_breakthrough(self):
        event = {"type": "zone_breakthrough", "zone_id": 5, "tier": 3}
        result = _format_anchor(event)
        assert "Tier 3" in result

    def test_faction_shift(self):
        event = {
            "type": "faction_shift",
            "npc_name": "Garren",
            "old_tier": "neutral",
            "new_tier": "friendly",
        }
        result = _format_anchor(event)
        assert "Garren" in result
        assert "neutral" in result
        assert "friendly" in result

    def test_rare_item_used(self):
        event = {
            "type": "rare_item_used",
            "user": "Kael",
            "item_name": "Phoenix Staff",
            "trait": "Summon",
        }
        result = _format_anchor(event)
        assert "Phoenix Staff" in result
        assert "Kael" in result

    def test_party_death(self):
        event = {"type": "party_death", "name": "Kael"}
        result = _format_anchor(event)
        assert "Kael" in result
        assert "fallen" in result

    def test_unknown_type_fallback(self):
        event = {"type": "something_else", "data": "test"}
        result = _format_anchor(event)
        assert "something_else" in result


# ===========================================================================
# TestSummarizeSessionAnchors
# ===========================================================================

class TestSummarizeSessionAnchors:
    """Tests for anchor moment integration in session stats + recap."""

    def test_anchors_in_stats(self):
        """format_session_stats returns anchor_moments key."""
        log = [
            {"type": "kill", "target": "Ghoul", "tier": 1},
            {"type": "near_death", "name": "Kael", "hp": 2, "max_hp": 20, "attacker": "Ghoul"},
            {"type": "room_entered", "room_id": 1},
        ]
        snap = {"party": [], "doom": 5, "turns": 10, "chapter": 1, "completed_quests": []}
        stats = format_session_stats(log, snap)
        assert "anchor_moments" in stats
        assert len(stats["anchor_moments"]) == 1
        assert stats["anchor_moments"][0]["type"] == "near_death"

    def test_no_anchors_unchanged(self):
        """Session with no anchor events has empty anchor_moments."""
        log = [
            {"type": "kill", "target": "Ghoul", "tier": 1},
            {"type": "room_entered", "room_id": 1},
        ]
        snap = {"party": [], "doom": 0, "turns": 5, "chapter": 1, "completed_quests": []}
        stats = format_session_stats(log, snap)
        assert stats["anchor_moments"] == []

    def test_anchors_in_recap_text(self):
        """summarize_session includes Key Moments section when anchors exist."""
        log = [
            {"type": "near_death", "name": "Kael", "hp": 2, "max_hp": 20, "attacker": "Ghoul"},
            {"type": "party_death", "name": "Mira"},
        ]
        snap = {"party": [], "doom": 10, "turns": 15, "chapter": 1, "completed_quests": []}
        recap = summarize_session(log, snap)
        assert "Key Moments" in recap
        assert "Kael" in recap
        assert "Mira" in recap

    def test_no_anchors_no_key_moments(self):
        """No anchor events means no Key Moments section."""
        log = [{"type": "kill", "target": "Ghoul", "tier": 1}]
        snap = {"party": [], "doom": 0, "turns": 5, "chapter": 1, "completed_quests": []}
        recap = summarize_session(log, snap)
        assert "Key Moments" not in recap

    def test_mimir_receives_anchors(self):
        """Mimir function receives prompt containing Key Moments."""
        log = [
            {"type": "near_death", "name": "Kael", "hp": 2, "max_hp": 20, "attacker": "Ghoul"},
        ]
        snap = {"party": [], "doom": 10, "turns": 15, "chapter": 1, "completed_quests": []}
        received_prompts = []

        def mock_mimir(prompt, ctx):
            received_prompts.append(prompt)
            return "A dramatic tale of near death."

        recap = summarize_session(log, snap, mimir_fn=mock_mimir)
        assert len(received_prompts) == 1
        assert "Key Moments" in received_prompts[0]
        assert "dramatic" in received_prompts[0]

    def test_format_anchor_all_types(self):
        """Each anchor type in ANCHOR_EVENT_TYPES produces non-empty output."""
        full_event = {
            "name": "Test",
            "hp": 1,
            "max_hp": 10,
            "attacker": "Foe",
            "savior": "Hero",
            "saved": "Victim",
            "method": "triage",
            "roller": "Test",
            "result": "critical",
            "context": "vs Foe",
            "archetype": "warrior",
            "cause": "Dragon",
            "doom_value": 10,
            "event_text": "Doom rises",
            "tier": 2,
            "zone_id": 3,
            "npc_name": "Bob",
            "old_tier": "neutral",
            "new_tier": "friendly",
            "user": "Kael",
            "item_name": "Staff",
            "trait": "Summon",
        }
        for etype in ANCHOR_EVENT_TYPES:
            event = {"type": etype, **full_event}
            result = _format_anchor(event)
            assert len(result) > 0, f"_format_anchor returned empty string for type '{etype}'"

    def test_multiple_anchor_types_in_log(self):
        """Multiple different anchor types all appear in anchor_moments."""
        log = [
            {"type": "near_death", "name": "Kael", "hp": 1, "max_hp": 20, "attacker": "Lich"},
            {"type": "ally_saved", "savior": "Mira", "saved": "Kael", "method": "heal"},
            {"type": "doom_threshold", "doom_value": 15, "event_text": "Darkness falls"},
            {"type": "kill", "target": "Lich", "tier": 3},
        ]
        snap = {"party": [], "doom": 15, "turns": 20, "chapter": 2, "completed_quests": []}
        stats = format_session_stats(log, snap)
        assert len(stats["anchor_moments"]) == 3
        types = {e["type"] for e in stats["anchor_moments"]}
        assert "near_death" in types
        assert "ally_saved" in types
        assert "doom_threshold" in types


# ===========================================================================
# TestUniversalBridgeLogging
# ===========================================================================

class TestUniversalBridgeLogging:
    """Tests for WO-V61.0 session log on UniversalGameBridge."""

    def _make_bridge(self):
        """Create a minimal bridge without engine init."""
        bridge = object.__new__(UniversalGameBridge)
        bridge._session_log = []
        bridge._butler = None
        bridge.show_dm_notes = False
        bridge._talking_to = None
        bridge.dead = False
        return bridge

    def test_bridge_has_session_log(self):
        bridge = self._make_bridge()
        assert hasattr(bridge, "_session_log")
        assert isinstance(bridge._session_log, list)

    def test_bridge_log_event(self):
        bridge = self._make_bridge()
        bridge._log_event("test_event", foo="bar")
        assert len(bridge._session_log) == 1
        assert bridge._session_log[0]["type"] == "test_event"
        assert bridge._session_log[0]["foo"] == "bar"

    def test_bridge_get_session_log(self):
        bridge = self._make_bridge()
        bridge._log_event("event1")
        bridge._log_event("event2")
        log = bridge.get_session_log()
        assert len(log) == 2
        # Verify it returns a copy, not the internal list
        log.append({"type": "fake"})
        assert len(bridge._session_log) == 2

    def test_bridge_log_event_multiple(self):
        bridge = self._make_bridge()
        bridge._log_event("kill", target="Ghoul")
        bridge._log_event("near_death", name="Hero", hp=2, max_hp=20, attacker="Ghoul")
        bridge._log_event("room_entered", room_id=5)
        assert len(bridge.get_session_log()) == 3
        types = [e["type"] for e in bridge.get_session_log()]
        assert "kill" in types
        assert "near_death" in types
        assert "room_entered" in types

    def test_bridge_log_preserves_kwargs(self):
        """All keyword args passed to _log_event are stored in the event dict."""
        bridge = self._make_bridge()
        bridge._log_event("faction_shift", npc_name="Garren", old_tier="neutral", new_tier="friendly")
        event = bridge._session_log[0]
        assert event["npc_name"] == "Garren"
        assert event["old_tier"] == "neutral"
        assert event["new_tier"] == "friendly"

    def test_bridge_log_starts_empty(self):
        """A fresh bridge (via object.__new__ pattern) has an empty session log."""
        bridge = self._make_bridge()
        assert bridge.get_session_log() == []

    def test_bridge_get_session_log_is_independent(self):
        """Two calls to get_session_log() return independent lists."""
        bridge = self._make_bridge()
        bridge._log_event("kill", target="Troll")
        log_a = bridge.get_session_log()
        log_b = bridge.get_session_log()
        log_a.clear()
        assert len(log_b) == 1  # log_b unaffected
        assert len(bridge._session_log) == 1  # internal unaffected


# ===========================================================================
# TestFITDTraumaShard
# ===========================================================================

class TestFITDTraumaShard:
    """Tests for push_stress + ANCHOR shard emission across FITD engines."""

    def test_bitd_push_stress_no_trauma(self):
        """push_stress with low stress does not emit a trauma ANCHOR shard."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("TestScoundrel")
        char_name = engine.character.name

        # Only 1 point of stress — well below max_stress=9, no trauma
        result = engine.push_stress(char_name, 1)
        assert result.get("trauma_triggered") is False

        trauma_shards = [s for s in engine._memory_shards if "trauma" in s.content.lower()]
        assert len(trauma_shards) == 0

    def test_bitd_push_stress_causes_trauma(self):
        """push_stress that overflows max_stress triggers trauma and emits ANCHOR shard."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("TestScoundrel")
        char_name = engine.character.name

        # Fill stress clock to max so the next push overflows
        clock = engine.stress_clocks[char_name]
        clock.current_stress = clock.max_stress

        result = engine.push_stress(char_name, 1)
        assert result.get("trauma_triggered") is True

        trauma_shards = [s for s in engine._memory_shards if "trauma" in s.content.lower()]
        assert len(trauma_shards) >= 1
        assert "ANCHOR" in trauma_shards[0].shard_type.value

    def test_bitd_push_stress_unknown_char_returns_empty(self):
        """push_stress for an unregistered character name returns {}."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Dariusz")
        result = engine.push_stress("NoSuchChar", 3)
        assert result == {}

    def test_sav_push_stress_exists(self):
        """SaV engine has push_stress method."""
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        assert hasattr(engine, "push_stress")
        assert callable(engine.push_stress)

    def test_bob_push_stress_exists(self):
        """BoB engine has push_stress method."""
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        assert hasattr(engine, "push_stress")
        assert callable(engine.push_stress)

    def test_candela_push_stress_exists(self):
        """Candela engine has push_stress method."""
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        assert hasattr(engine, "push_stress")
        assert callable(engine.push_stress)

    def test_cbrpnk_has_anchor_shard_path(self):
        """CBR+PNK engine has ANCHOR shard emission wired (via intrusion path, not push_stress)."""
        from codex.games.cbrpnk import CBRPNKEngine
        engine = CBRPNKEngine()
        # CBR+PNK emits ANCHOR shards inline during ICE intrusion rolls (WO-V61.0).
        # It does not expose a standalone push_stress() — that is intentional.
        # Verify the engine uses NarrativeLoomMixin so _add_shard is available.
        assert hasattr(engine, "_add_shard")
        assert hasattr(engine, "_memory_shards")

    def test_sav_push_stress_trauma(self):
        """SaV push_stress emits ANCHOR shard on trauma overflow."""
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Pilot")
        char_name = engine.character.name

        clock = engine.stress_clocks[char_name]
        clock.current_stress = clock.max_stress

        result = engine.push_stress(char_name, 1)
        assert result.get("trauma_triggered") is True

        trauma_shards = [s for s in engine._memory_shards if "trauma" in s.content.lower()]
        assert len(trauma_shards) >= 1

    def test_bob_push_stress_trauma(self):
        """BoB push_stress emits ANCHOR shard on trauma overflow."""
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Soldier")
        char_name = engine.character.name

        clock = engine.stress_clocks[char_name]
        clock.current_stress = clock.max_stress

        result = engine.push_stress(char_name, 1)
        assert result.get("trauma_triggered") is True

        trauma_shards = [s for s in engine._memory_shards if "trauma" in s.content.lower()]
        assert len(trauma_shards) >= 1


# ===========================================================================
# TestAnchorEventTypes
# ===========================================================================

class TestAnchorEventTypes:
    """Sanity checks on the ANCHOR_EVENT_TYPES constant."""

    def test_all_types_present(self):
        """ANCHOR_EVENT_TYPES contains exactly the 9 expected type strings."""
        expected = {
            "near_death",
            "ally_saved",
            "rare_item_used",
            "critical_roll",
            "companion_fell",
            "faction_shift",
            "doom_threshold",
            "zone_breakthrough",
            "party_death",
        }
        assert ANCHOR_EVENT_TYPES == expected

    def test_is_frozenset(self):
        """ANCHOR_EVENT_TYPES is immutable (frozenset)."""
        assert isinstance(ANCHOR_EVENT_TYPES, frozenset)

    def test_no_extra_types(self):
        """ANCHOR_EVENT_TYPES has exactly 9 entries — no accidental extras."""
        assert len(ANCHOR_EVENT_TYPES) == 9

    def test_all_strings(self):
        """Every member of ANCHOR_EVENT_TYPES is a non-empty string."""
        for etype in ANCHOR_EVENT_TYPES:
            assert isinstance(etype, str)
            assert len(etype) > 0

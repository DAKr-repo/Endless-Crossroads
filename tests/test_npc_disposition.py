#!/usr/bin/env python3
"""
tests/test_npc_disposition.py — NPC Disposition & Faction Response Tests (WO-P7)
================================================================================

Covers:
  - DispositionEntry and NPCDisposition dataclasses
  - faction_response() lookup function and RESPONSE_TABLE
  - DispositionManager orchestrator
  - NarrativeEngineBase integration (commands, save/load, shard emission)
"""

import sys
import unittest
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codex.core.services.npc_memory import (
    DispositionEntry,
    DispositionManager,
    FACTION_RESPONSES,
    NPCDisposition,
    RESPONSE_TABLE,
    _disposition_to_range,
    faction_response,
)


# =========================================================================
# HELPERS — minimal concrete NarrativeEngineBase subclass for integration tests
# =========================================================================

def _make_engine():
    """Return a minimal NarrativeEngineBase subclass instance."""
    from codex.core.engines.narrative_base import NarrativeEngineBase

    class _TestEngine(NarrativeEngineBase):
        system_id = "test_disposition"
        system_family = "TEST"
        display_name = "Test Engine"

        def _create_character(self, name: str, **kwargs):
            from types import SimpleNamespace
            char = SimpleNamespace(name=name, hunt=2, skirmish=1)
            char.to_dict = lambda: {"name": name, "hunt": 2, "skirmish": 1}
            return char

        def _get_command_registry(self):
            return {}

        def _use_stress_clocks(self) -> bool:
            return False

    return _TestEngine()


# =========================================================================
# T1-T7: DispositionEntry + NPCDisposition
# =========================================================================

class TestNPCDisposition(unittest.TestCase):

    def test_t1_default_disposition_neutral(self):
        """T1: Default disposition is 0 / Neutral."""
        npc = NPCDisposition(name="Shallan")
        self.assertEqual(npc.disposition, 0)
        self.assertEqual(npc.label, "Neutral")

    def test_t2_adjust_positive_changes_label(self):
        """T2: Positive adjust moves toward Friendly then Allied."""
        npc = NPCDisposition(name="Shallan")
        result = npc.adjust(1, "helped with a task")
        self.assertEqual(result["old"], 0)
        self.assertEqual(result["new"], 1)
        self.assertEqual(result["old_label"], "Neutral")
        self.assertEqual(result["new_label"], "Friendly")
        self.assertTrue(result["changed"])

    def test_t3_adjust_clamps_at_max(self):
        """T3: Adjustment cannot exceed +3."""
        npc = NPCDisposition(name="Adolin")
        for _ in range(10):
            npc.adjust(1, "repeatedly helped")
        self.assertEqual(npc.disposition, 3)
        self.assertEqual(npc.label, "Devoted")

    def test_t4_adjust_clamps_at_min(self):
        """T4: Adjustment cannot go below -3."""
        npc = NPCDisposition(name="Sadeas")
        for _ in range(10):
            npc.adjust(-1, "repeatedly opposed")
        self.assertEqual(npc.disposition, -3)
        self.assertEqual(npc.label, "Hostile")

    def test_t5_adjust_records_history(self):
        """T5: Each adjust call appends a DispositionEntry."""
        npc = NPCDisposition(name="Kaladin")
        npc.adjust(1, "saved the crew", source="player_action")
        npc.adjust(-1, "broke oath", source="session")
        self.assertEqual(len(npc.history), 2)
        self.assertEqual(npc.history[0].delta, 1)
        self.assertEqual(npc.history[0].reason, "saved the crew")
        self.assertEqual(npc.history[0].source, "player_action")
        self.assertEqual(npc.history[1].delta, -1)
        self.assertEqual(npc.history[1].source, "session")

    def test_t6_no_change_marks_unchanged(self):
        """T6: Clamped adjust at boundary sets changed=False."""
        npc = NPCDisposition(name="Lirin")
        npc.disposition = 3
        result = npc.adjust(1, "another kind act")
        self.assertFalse(result["changed"])
        self.assertEqual(result["old"], 3)
        self.assertEqual(result["new"], 3)

    def test_t7_history_summary_shows_last_5(self):
        """T7: get_history_summary shows at most 5 recent entries."""
        npc = NPCDisposition(name="Szeth")
        for i in range(8):
            # clamp at -3 so we don't flip sign
            npc.adjust(0, f"event {i}")
        summary = npc.get_history_summary()
        # Should mention Szeth and show entries
        self.assertIn("Szeth", summary)
        # The last 5 events are 3,4,5,6,7 — count occurrences of "event"
        event_count = summary.count("event")
        self.assertLessEqual(event_count, 5)

    def test_t8_all_labels_covered(self):
        """T8: All seven disposition values have correct labels."""
        npc = NPCDisposition(name="Rock")
        expected = {
            -3: "Hostile", -2: "Antagonistic", -1: "Unfriendly",
            0: "Neutral", 1: "Friendly", 2: "Allied", 3: "Devoted",
        }
        for val, label in expected.items():
            npc.disposition = val
            self.assertEqual(npc.label, label, f"Failed for disposition {val}")

    def test_t9_to_dict_from_dict_roundtrip(self):
        """T9: to_dict/from_dict preserves all fields including history."""
        npc = NPCDisposition(name="Dalinar", disposition=2, faction="Kholin", tags=["leader"])
        npc.adjust(-1, "betrayed trust", source="faction_action")
        npc.adjust(2, "swore an Oath", source="session")

        data = npc.to_dict()
        restored = NPCDisposition.from_dict(data)

        self.assertEqual(restored.name, "Dalinar")
        self.assertEqual(restored.disposition, 3)  # 2 - 1 + 2 = 3
        self.assertEqual(restored.faction, "Kholin")
        self.assertIn("leader", restored.tags)
        self.assertEqual(len(restored.history), 2)
        self.assertEqual(restored.history[0].delta, -1)
        self.assertEqual(restored.history[0].reason, "betrayed trust")
        self.assertEqual(restored.history[0].source, "faction_action")
        self.assertEqual(restored.history[1].delta, 2)
        self.assertEqual(restored.history[1].source, "session")

    def test_t10_empty_history_summary(self):
        """T10: NPC with no history returns a 'No interactions' message."""
        npc = NPCDisposition(name="Moash")
        summary = npc.get_history_summary()
        self.assertIn("No interactions recorded", summary)
        self.assertIn("Moash", summary)


# =========================================================================
# T11-T22: faction_response() and RESPONSE_TABLE
# =========================================================================

class TestFactionResponse(unittest.TestCase):

    def test_t11_hostile_score_against_retaliate(self):
        """T11: Hostile + score_against -> retaliate."""
        result = faction_response(-3, "score_against")
        self.assertEqual(result["response_type"], "retaliate")
        self.assertEqual(result["disposition_range"], "hostile")

    def test_t12_hostile_score_near_escalate(self):
        """T12: Hostile + score_near -> escalate."""
        result = faction_response(-2, "score_near")
        self.assertEqual(result["response_type"], "escalate")

    def test_t13_unfriendly_score_against_retaliate(self):
        """T13: Unfriendly + score_against -> retaliate."""
        result = faction_response(-1, "score_against")
        self.assertEqual(result["response_type"], "retaliate")

    def test_t14_neutral_ignored_ignore(self):
        """T14: Neutral + ignored -> ignore."""
        result = faction_response(0, "ignored")
        self.assertEqual(result["response_type"], "ignore")
        self.assertEqual(result["disposition_range"], "neutral")

    def test_t15_neutral_aid_given_ally(self):
        """T15: Neutral + aid_given -> ally."""
        result = faction_response(0, "aid_given")
        self.assertEqual(result["response_type"], "ally")

    def test_t16_friendly_score_against_withdraw(self):
        """T16: Friendly + score_against -> withdraw."""
        result = faction_response(1, "score_against")
        self.assertEqual(result["response_type"], "withdraw")

    def test_t17_allied_aid_given_ally(self):
        """T17: Allied + aid_given -> ally."""
        result = faction_response(2, "aid_given")
        self.assertEqual(result["response_type"], "ally")
        self.assertEqual(result["disposition_range"], "allied")

    def test_t18_allied_score_against_negotiate(self):
        """T18: Allied + score_against -> negotiate."""
        result = faction_response(3, "score_against")
        self.assertEqual(result["response_type"], "negotiate")

    def test_t19_unknown_event_falls_back_to_default(self):
        """T19: Unknown event_type falls back to 'default' response."""
        result = faction_response(0, "some_unknown_event")
        # neutral default = ignore
        self.assertEqual(result["response_type"], "ignore")

    def test_t20_result_has_description(self):
        """T20: Result always contains a non-empty description string."""
        for disp in range(-3, 4):
            for event in ("score_against", "aid_given", "ignored", "default"):
                result = faction_response(disp, event)
                self.assertIn("description", result)
                self.assertIsInstance(result["description"], str)
                self.assertTrue(len(result["description"]) > 0)

    def test_t21_disposition_range_mapping(self):
        """T21: _disposition_to_range maps all values correctly."""
        expected = {
            -3: "hostile", -2: "hostile", -1: "unfriendly",
            0: "neutral", 1: "friendly", 2: "allied", 3: "allied",
        }
        for val, expected_range in expected.items():
            self.assertEqual(_disposition_to_range(val), expected_range, f"Failed at {val}")

    def test_t22_all_response_types_in_faction_responses(self):
        """T22: Every response_type in RESPONSE_TABLE exists in FACTION_RESPONSES."""
        used_types = set()
        for event_map in RESPONSE_TABLE.values():
            used_types.update(event_map.values())
        for rt in used_types:
            self.assertIn(rt, FACTION_RESPONSES, f"Response type '{rt}' missing from FACTION_RESPONSES")


# =========================================================================
# T23-T33: DispositionManager
# =========================================================================

class TestDispositionManager(unittest.TestCase):

    def test_t23_get_or_create_creates_new(self):
        """T23: get_or_create builds a new NPCDisposition."""
        mgr = DispositionManager()
        npc = mgr.get_or_create("Wit")
        self.assertIsInstance(npc, NPCDisposition)
        self.assertEqual(npc.name, "Wit")
        self.assertEqual(npc.disposition, 0)

    def test_t24_get_or_create_returns_existing(self):
        """T24: Second get_or_create call returns the same object."""
        mgr = DispositionManager()
        npc1 = mgr.get_or_create("Wit")
        npc2 = mgr.get_or_create("Wit")
        self.assertIs(npc1, npc2)

    def test_t25_get_or_create_sets_faction_and_tags(self):
        """T25: First get_or_create stores faction and tags."""
        mgr = DispositionManager()
        npc = mgr.get_or_create("Pattern", faction="Spren", tags=["cryptic"])
        self.assertEqual(npc.faction, "Spren")
        self.assertIn("cryptic", npc.tags)

    def test_t26_adjust_disposition_works(self):
        """T26: adjust_disposition changes score via manager."""
        mgr = DispositionManager()
        result = mgr.adjust_disposition("Sylphrena", 2, "bonded a Windrunner")
        self.assertEqual(result["new"], 2)
        self.assertEqual(result["new_label"], "Allied")

    def test_t27_adjust_creates_npc_on_first_call(self):
        """T27: adjust_disposition creates NPC record if not yet tracked."""
        mgr = DispositionManager()
        self.assertNotIn("Nightblood", mgr.npcs)
        mgr.adjust_disposition("Nightblood", -2, "consumed souls")
        self.assertIn("Nightblood", mgr.npcs)

    def test_t28_get_status_unknown_npc(self):
        """T28: get_status for unknown NPC returns a 'No record' message."""
        mgr = DispositionManager()
        status = mgr.get_status("Nobody")
        self.assertIn("No record", status)
        self.assertIn("Nobody", status)

    def test_t29_get_status_known_npc(self):
        """T29: get_status for known NPC returns history summary."""
        mgr = DispositionManager()
        mgr.adjust_disposition("Hoid", 1, "told a useful story")
        status = mgr.get_status("Hoid")
        self.assertIn("Hoid", status)
        self.assertIn("told a useful story", status)

    def test_t30_get_faction_response_unknown_neutral(self):
        """T30: get_faction_response for unknown NPC uses neutral (0)."""
        mgr = DispositionManager()
        result = mgr.get_faction_response("Mystery NPC", "aid_given")
        # neutral + aid_given = ally
        self.assertEqual(result["response_type"], "ally")
        self.assertEqual(result["disposition"], 0)

    def test_t31_get_faction_response_uses_actual_disposition(self):
        """T31: get_faction_response reflects actual tracked disposition."""
        mgr = DispositionManager()
        mgr.adjust_disposition("Odium", -3, "divine hatred")
        result = mgr.get_faction_response("Odium", "score_against")
        self.assertEqual(result["response_type"], "retaliate")
        self.assertEqual(result["disposition"], -3)

    def test_t32_list_npcs_empty(self):
        """T32: list_npcs returns a message when no NPCs tracked."""
        mgr = DispositionManager()
        listing = mgr.list_npcs()
        self.assertIn("No NPCs tracked", listing)

    def test_t33_list_npcs_shows_all(self):
        """T33: list_npcs shows all tracked NPCs sorted alphabetically."""
        mgr = DispositionManager()
        mgr.adjust_disposition("Zyah", 1, "minor favor")
        mgr.adjust_disposition("Adolin", 2, "sparring session")
        listing = mgr.list_npcs()
        self.assertIn("Adolin", listing)
        self.assertIn("Zyah", listing)
        # Adolin comes before Zyah alphabetically
        self.assertLess(listing.index("Adolin"), listing.index("Zyah"))

    def test_t34_to_dict_from_dict_roundtrip(self):
        """T34: DispositionManager serialization roundtrip preserves all data."""
        mgr = DispositionManager()
        mgr.adjust_disposition("Eshonai", -1, "ancient grudge", source="faction_action")
        mgr.adjust_disposition("Venli", 1, "shared humanity", source="player_action")

        data = mgr.to_dict()
        restored = DispositionManager.from_dict(data)

        self.assertIn("Eshonai", restored.npcs)
        self.assertIn("Venli", restored.npcs)
        self.assertEqual(restored.npcs["Eshonai"].disposition, -1)
        self.assertEqual(restored.npcs["Venli"].disposition, 1)
        self.assertEqual(restored.npcs["Eshonai"].history[0].source, "faction_action")

    def test_t35_empty_manager_roundtrip(self):
        """T35: Empty DispositionManager round-trips without error."""
        mgr = DispositionManager()
        data = mgr.to_dict()
        restored = DispositionManager.from_dict(data)
        self.assertEqual(len(restored.npcs), 0)


# =========================================================================
# T36-T48: NarrativeEngineBase integration
# =========================================================================

class TestNarrativeEngineBaseIntegration(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()

    def test_t36_npc_status_no_name_lists_empty(self):
        """T36: npc_status with no name returns 'No NPCs tracked' initially."""
        result = self.engine.handle_command("npc_status")
        self.assertIn("No NPCs tracked", result)

    def test_t37_npc_adjust_creates_and_returns_formatted(self):
        """T37: npc_adjust creates NPC and returns formatted change string."""
        result = self.engine.handle_command(
            "npc_adjust", name="Syl", delta=2, reason="helped Kaladin"
        )
        self.assertIn("Syl", result)
        self.assertIn("Allied", result)
        self.assertIn("helped Kaladin", result)

    def test_t38_npc_adjust_missing_name_returns_usage(self):
        """T38: npc_adjust without name returns usage hint."""
        result = self.engine.handle_command("npc_adjust")
        self.assertIn("name=", result)

    def test_t39_npc_adjust_emits_shard_on_change(self):
        """T39: npc_adjust emits a CHRONICLE shard when disposition changes."""
        self.engine.handle_command(
            "npc_adjust", name="Adolin", delta=1, reason="defended honour"
        )
        shards = self.engine._memory_shards
        chronicle_shards = [s for s in shards if s.shard_type.name == "CHRONICLE"]
        npc_shards = [s for s in chronicle_shards if "Adolin" in s.content]
        self.assertGreater(len(npc_shards), 0)
        self.assertIn("Friendly", npc_shards[0].content)

    def test_t40_npc_adjust_no_shard_when_clamped(self):
        """T40: npc_adjust does not emit shard when value is already clamped."""
        # Lock at +3
        mgr = self.engine._get_npc_disposition()
        mgr.get_or_create("Topped").disposition = 3
        before_count = len(self.engine._memory_shards)
        self.engine.handle_command(
            "npc_adjust", name="Topped", delta=1, reason="cannot go higher"
        )
        after_count = len(self.engine._memory_shards)
        self.assertEqual(before_count, after_count)

    def test_t41_npc_status_with_name_shows_history(self):
        """T41: npc_status with a known name returns that NPC's history summary."""
        self.engine.handle_command("npc_adjust", name="Hoid", delta=1, reason="told a good story")
        result = self.engine.handle_command("npc_status", name="Hoid")
        self.assertIn("Hoid", result)
        self.assertIn("told a good story", result)

    def test_t42_npc_status_no_name_shows_all_after_adds(self):
        """T42: npc_status with no name lists all NPCs after several adjustments."""
        self.engine.handle_command("npc_adjust", name="Lopen", delta=1, reason="good vibes")
        self.engine.handle_command("npc_adjust", name="Rock", delta=-1, reason="stew incident")
        result = self.engine.handle_command("npc_status")
        self.assertIn("Lopen", result)
        self.assertIn("Rock", result)

    def test_t43_faction_response_missing_name_returns_usage(self):
        """T43: faction_response without name returns usage hint."""
        result = self.engine.handle_command("faction_response")
        self.assertIn("name=", result)

    def test_t44_faction_response_unknown_npc_neutral(self):
        """T44: faction_response for untracked NPC uses neutral (0)."""
        result = self.engine.handle_command(
            "faction_response", name="Unknown", event_type="aid_given"
        )
        self.assertIn("Unknown", result)
        self.assertIn("neutral", result)
        self.assertIn("ALLY", result)

    def test_t45_faction_response_reflects_adjusted_disposition(self):
        """T45: faction_response uses current tracked disposition."""
        self.engine.handle_command("npc_adjust", name="Odium", delta=-3, reason="divine wrath")
        result = self.engine.handle_command(
            "faction_response", name="Odium", event_type="score_against"
        )
        self.assertIn("RETALIATE", result)
        self.assertIn("hostile", result)

    def test_t46_faction_response_shows_event_type(self):
        """T46: faction_response output includes the event_type string."""
        result = self.engine.handle_command(
            "faction_response", name="Shallan", event_type="territory_taken"
        )
        self.assertIn("territory_taken", result)

    def test_t47_save_load_preserves_disposition_data(self):
        """T47: save_state/load_state round-trip preserves all NPC dispositions."""
        self.engine.handle_command("npc_adjust", name="Dalinar", delta=2, reason="united Roshar")
        self.engine.handle_command("npc_adjust", name="Moash", delta=-2, reason="betrayal")

        state = self.engine.save_state()
        self.assertIn("npc_disposition", state)
        self.assertIsNotNone(state["npc_disposition"])

        engine2 = _make_engine()
        engine2.load_state(state)

        mgr = engine2._npc_disposition
        self.assertIsNotNone(mgr)
        self.assertIn("Dalinar", mgr.npcs)
        self.assertIn("Moash", mgr.npcs)
        self.assertEqual(mgr.npcs["Dalinar"].disposition, 2)
        self.assertEqual(mgr.npcs["Moash"].disposition, -2)

    def test_t48_save_without_disposition_loads_clean(self):
        """T48: Loading a state dict with no npc_disposition key is backward compatible."""
        # Build a minimal state without npc_disposition
        state = {
            "system_id": "test_disposition",
            "setting_id": "",
            "party": [],
            "stress": {},
            "faction_clocks": [],
            # No npc_disposition key
        }
        engine = _make_engine()
        engine.load_state(state)
        # _npc_disposition should remain None (lazy-init)
        self.assertIsNone(engine._npc_disposition)

    def test_t49_trace_fact_finds_npc_shards(self):
        """T49: trace_fact can find shards emitted by npc_adjust."""
        self.engine.handle_command("npc_adjust", name="Renarin", delta=1, reason="visions of truth")
        trace = self.engine.trace_fact("Renarin")
        self.assertIn("Renarin", trace)

    def test_t50_handle_command_with_dashes_normalized(self):
        """T50: handle_command normalizes hyphens to underscores."""
        # npc-status should resolve to npc_status
        result = self.engine.handle_command("npc-status")
        self.assertIn("No NPCs tracked", result)

    def test_t51_disposition_lazy_init_only_on_access(self):
        """T51: _npc_disposition is None until first command or _get_npc_disposition call."""
        engine = _make_engine()
        self.assertIsNone(engine._npc_disposition)
        engine._get_npc_disposition()
        self.assertIsNotNone(engine._npc_disposition)

    def test_t52_multiple_adjustments_accumulate(self):
        """T52: Multiple npc_adjust calls accumulate correctly."""
        self.engine.handle_command("npc_adjust", name="Lift", delta=1, reason="brought food")
        self.engine.handle_command("npc_adjust", name="Lift", delta=1, reason="saved orphan")
        self.engine.handle_command("npc_adjust", name="Lift", delta=-1, reason="stole something")
        mgr = self.engine._get_npc_disposition()
        self.assertEqual(mgr.npcs["Lift"].disposition, 1)
        self.assertEqual(len(mgr.npcs["Lift"].history), 3)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
tests/test_npc_memory.py — NPC Persistent Memory Tests (WO-V12.1)
==================================================================

20 unit tests covering BiasLens, NPCMemoryBank, and NPCMemoryManager.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codex.core.memory import MemoryShard, ShardType
from codex.core.services.npc_memory import (
    BIAS_TABLES,
    BiasLens,
    CIVIC_ROLE_MAP,
    MAX_SHARDS,
    NPCMemoryBank,
    NPCMemoryManager,
)
from codex.core.world.grapes_engine import CulturalValue


# =========================================================================
# HELPERS
# =========================================================================

def _cv_freedom():
    return CulturalValue(
        tenet="Freedom above all",
        expression="Chains are burned",
        consequence="Oppressors exiled",
    )


def _cv_honor():
    return CulturalValue(
        tenet="Honor in battle",
        expression="Steel speaks truth",
        consequence="Cowards are shunned",
    )


def _cv_nomatch():
    """CulturalValue whose tenet matches no archetype."""
    return CulturalValue(
        tenet="Knowledge is light",
        expression="The scrolls remember",
        consequence="Ignorance is punished",
    )


# =========================================================================
# T1-T4: BiasLens
# =========================================================================

class TestBiasLens(unittest.TestCase):

    def test_t1_freedom_bias_rewrites_patrol(self):
        """T1: freedom bias rewrites 'patrol reinforced'."""
        lens = BiasLens(cultural_value=_cv_freedom())
        result = lens.rewrite("patrol reinforced in the ward")
        self.assertIn("surveillance sweep", result)
        self.assertIn("tightened their grip on", result)

    def test_t2_honor_bias_rewrites_retreat(self):
        """T2: honor bias rewrites 'retreat'."""
        lens = BiasLens(cultural_value=_cv_honor())
        result = lens.rewrite("The soldiers began their retreat")
        self.assertIn("tactical withdrawal", result)

    def test_t3_no_archetype_appends_expression(self):
        """T3: no archetype match appends cultural expression."""
        lens = BiasLens(cultural_value=_cv_nomatch())
        result = lens.rewrite("Something happened in the market")
        self.assertIn("The scrolls remember", result)
        self.assertTrue(result.endswith(")"))

    def test_t4_empty_text_passthrough(self):
        """T4: empty text returns empty string."""
        lens = BiasLens(cultural_value=_cv_freedom())
        self.assertEqual(lens.rewrite(""), "")


# =========================================================================
# T5-T11: NPCMemoryBank
# =========================================================================

class TestNPCMemoryBank(unittest.TestCase):

    def _make_bank(self):
        return NPCMemoryBank(
            npc_name="Finch",
            npc_role="merchant",
            npc_location="market",
            bias_lens=BiasLens(cultural_value=_cv_freedom()),
        )

    def test_t5_record_creates_echo(self):
        """T5: record() creates an ECHO shard."""
        bank = self._make_bank()
        shard = bank.record("Goods arrived from the east", tags=["trade"])
        self.assertEqual(shard.shard_type, ShardType.ECHO)
        self.assertIn("trade", shard.tags)
        self.assertEqual(len(bank.shards), 1)

    def test_t6_record_anchor_creates_anchor(self):
        """T6: record_anchor() creates an ANCHOR shard."""
        bank = self._make_bank()
        shard = bank.record_anchor("The king has fallen!", tags=["critical"])
        self.assertEqual(shard.shard_type, ShardType.ANCHOR)
        self.assertEqual(len(bank.shards), 1)

    def test_t7_decay_purges_oldest_echoes_first(self):
        """T7: decay purges oldest ECHOs before ANCHORs."""
        bank = self._make_bank()
        # Fill with 7 echoes + 1 anchor = 8 (at cap)
        for i in range(7):
            bank.record(f"Echo event {i}")
        bank.record_anchor("Critical anchor event")
        self.assertEqual(len(bank.shards), MAX_SHARDS)

        # Add one more echo — should evict oldest echo, not anchor
        bank.record("Overflow echo")
        self.assertEqual(len(bank.shards), MAX_SHARDS)

        # Anchor should still be present
        anchors = [s for s in bank.shards if s.shard_type == ShardType.ANCHOR]
        self.assertEqual(len(anchors), 1)
        self.assertIn("Critical anchor event", anchors[0].content)

    def test_t8_max_shards_enforced(self):
        """T8: bank never exceeds MAX_SHARDS."""
        bank = self._make_bank()
        for i in range(20):
            bank.record(f"Event number {i}")
        self.assertLessEqual(len(bank.shards), MAX_SHARDS)

    def test_t9_weave_context_within_budget(self):
        """T9: weave_context stays within token budget."""
        bank = self._make_bank()
        bank.record("First event in the marketplace")
        bank.record("Second event: a stranger arrived")
        bank.record_anchor("The Rot broke through the walls")
        ctx = bank.weave_context(token_budget=150)
        # Token estimate: ~len//4
        token_est = len(ctx) // 4
        self.assertLessEqual(token_est, 160)  # Some slack for rounding
        self.assertIn("Finch remembers:", ctx)

    def test_t10_weave_context_empty_returns_blank(self):
        """T10: empty bank returns empty string."""
        bank = NPCMemoryBank(npc_name="Ghost")
        self.assertEqual(bank.weave_context(), "")

    def test_t11_to_dict_from_dict_roundtrip(self):
        """T11: NPCMemoryBank serialization roundtrip."""
        bank = self._make_bank()
        bank.record("Test event alpha")
        bank.record_anchor("Test anchor beta")

        data = bank.to_dict()
        restored = NPCMemoryBank.from_dict(data)

        self.assertEqual(restored.npc_name, "Finch")
        self.assertEqual(restored.npc_role, "merchant")
        self.assertEqual(len(restored.shards), 2)
        self.assertEqual(restored.shards[0].shard_type, ShardType.ECHO)
        self.assertEqual(restored.shards[1].shard_type, ShardType.ANCHOR)


# =========================================================================
# T12-T20: NPCMemoryManager
# =========================================================================

class TestNPCMemoryManager(unittest.TestCase):

    def test_t12_register_npc_creates_bank(self):
        """T12: register_npc creates a new bank."""
        mgr = NPCMemoryManager(cultural_values=[_cv_freedom()])
        bank = mgr.register_npc("Finch", "merchant", "market")
        self.assertIsNotNone(bank)
        self.assertEqual(bank.npc_name, "Finch")
        self.assertEqual(bank.npc_role, "merchant")

    def test_t13_register_npc_idempotent(self):
        """T13: second register_npc call returns same bank."""
        mgr = NPCMemoryManager(cultural_values=[_cv_freedom()])
        bank1 = mgr.register_npc("Finch", "merchant", "market")
        bank2 = mgr.register_npc("Finch", "merchant", "market")
        self.assertIs(bank1, bank2)

    def test_t14_high_impact_reaches_all_npcs(self):
        """T14: HIGH_IMPACT_DECISION reaches all registered NPCs."""
        mgr = NPCMemoryManager(cultural_values=[_cv_freedom()])
        mgr.register_npc("Finch", "merchant", "market")
        mgr.register_npc("Greta", "healer", "temple")
        mgr.register_npc("Wren", "informant", "tavern")

        mgr._on_broadcast({
            "_event_type": "HIGH_IMPACT_DECISION",
            "summary": "A hero emerged from the depths",
        })

        for name in ("Finch", "Greta", "Wren"):
            bank = mgr.get_bank(name)
            self.assertEqual(len(bank.shards), 1)
            self.assertEqual(bank.shards[0].shard_type, ShardType.ANCHOR)

    def test_t15_faction_event_filtered_by_role(self):
        """T15: FACTION_CLOCK_TICK only reaches informant/leader roles."""
        mgr = NPCMemoryManager(cultural_values=[_cv_honor()])
        mgr.register_npc("Finch", "merchant", "market")
        mgr.register_npc("Wren", "informant", "tavern")
        mgr.register_npc("Greta", "healer", "temple")

        mgr._on_broadcast({
            "_event_type": "FACTION_CLOCK_TICK",
            "summary": "The Iron Hand advances its agenda",
            "faction": "Iron Hand",
        })

        # Only informant should get it (merchant and healer should not)
        self.assertEqual(len(mgr.get_bank("Wren").shards), 1)
        self.assertEqual(len(mgr.get_bank("Finch").shards), 0)
        self.assertEqual(len(mgr.get_bank("Greta").shards), 0)

    def test_t16_civic_event_filtered_by_role(self):
        """T16: CIVIC_EVENT trade -> merchant, security -> leader."""
        mgr = NPCMemoryManager(cultural_values=[_cv_freedom()])
        mgr.register_npc("Finch", "merchant", "market")
        mgr.register_npc("Captain", "leader", "barracks")
        mgr.register_npc("Greta", "healer", "temple")

        # Trade event -> merchant only
        mgr._on_broadcast({
            "_event_type": "CIVIC_EVENT",
            "category": "trade",
            "summary": "A new caravan arrived",
        })
        self.assertEqual(len(mgr.get_bank("Finch").shards), 1)
        self.assertEqual(len(mgr.get_bank("Captain").shards), 0)
        self.assertEqual(len(mgr.get_bank("Greta").shards), 0)

        # Security event -> leader only
        mgr._on_broadcast({
            "_event_type": "CIVIC_EVENT",
            "category": "security",
            "summary": "Walls breached in the south",
        })
        self.assertEqual(len(mgr.get_bank("Finch").shards), 1)  # Still just 1
        self.assertEqual(len(mgr.get_bank("Captain").shards), 1)

    def test_t17_get_dialogue_context_missing_npc(self):
        """T17: get_dialogue_context for unknown NPC returns ''."""
        mgr = NPCMemoryManager()
        self.assertEqual(mgr.get_dialogue_context("Nobody"), "")

    def test_t18_save_load_roundtrip(self):
        """T18: save/load roundtrip via tempfile."""
        mgr = NPCMemoryManager(cultural_values=[_cv_freedom()])
        bank = mgr.register_npc("Finch", "merchant", "market")
        bank.record("Goods arrived today")
        bank.record_anchor("The Rot Hunter was spotted!")

        # Save to temp location
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_file = Path(tmpdir) / "npc_memory.json"
            with patch("codex.paths.NPC_MEMORY_FILE", tmp_file):
                mgr.save()

                # Load into new manager
                mgr2 = NPCMemoryManager(cultural_values=[_cv_freedom()])
                mgr2.load()

                finch = mgr2.get_bank("Finch")
                self.assertIsNotNone(finch)
                self.assertEqual(len(finch.shards), 2)
                self.assertEqual(finch.shards[0].shard_type, ShardType.ECHO)
                self.assertEqual(finch.shards[1].shard_type, ShardType.ANCHOR)

    def test_t19_load_nonexistent_file_no_error(self):
        """T19: loading from nonexistent file raises no error."""
        mgr = NPCMemoryManager()
        nonexistent = Path("/tmp/_codex_nonexistent_npc_memory_test.json")
        if nonexistent.exists():
            nonexistent.unlink()
        with patch("codex.paths.NPC_MEMORY_FILE", nonexistent):
            # Should not raise
            mgr.load()
        self.assertEqual(len(mgr._banks), 0)

    def test_t20_bias_lens_restored_on_load(self):
        """T20: deterministic hash gives same BiasLens on load."""
        cv = _cv_freedom()
        mgr1 = NPCMemoryManager(cultural_values=[cv])
        bank1 = mgr1.register_npc("Finch", "merchant", "market")

        # Verify bias lens is set
        self.assertIsNotNone(bank1.bias_lens.cultural_value)

        # Simulate save/load by creating new manager with same cultural values
        mgr2 = NPCMemoryManager(cultural_values=[cv])
        bank2 = mgr2.register_npc("Finch", "merchant", "market")

        # Same cultural value should be assigned (deterministic hash)
        self.assertEqual(
            bank1.bias_lens.cultural_value.tenet,
            bank2.bias_lens.cultural_value.tenet,
        )
        # Verify bias actually works
        result = bank2.bias_lens.rewrite("patrol reinforced")
        self.assertIn("surveillance sweep", result)
        self.assertIn("tightened their grip on", result)


if __name__ == "__main__":
    unittest.main()

"""
tests/test_dm_dashboard.py — WO-V34.0 Comprehensive Tests
============================================================

Covers:
  1. ConditionTracker: apply, tick, remove, skip-turn, persistence roundtrip
  2. InitiativeTracker: roll, sort, next_turn, remove dead, round advancement
  3. RestManager: per-engine short/long rest, HP recovery, condition clearing
  4. ProgressionTracker: XP award, level-up check, FITD mark, milestone
  5. GenericAutopilotAgent: snapshot building + command execution
  6. VitalsSchema: all 5 adapters with real engine instances
  7. DMDashboard: render() returns Layout, command dispatch routes correctly
  8. query_codex() with mocked Ollama, lookup_creature() finds known enemies
  9. Broadcast event capture
  10. Engine modifications: DnD5e rest/xp, BitD downtime, STC ideal
"""

import random
from unittest.mock import patch, MagicMock

import pytest
from rich.console import Console
from rich.layout import Layout


# =========================================================================
# 1. CONDITION TRACKER
# =========================================================================

class TestConditionTracker:
    """Tests for codex.core.mechanics.conditions."""

    def test_apply_condition(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        cond = Condition(ConditionType.POISONED, duration=3, modifier=-2)
        msg = tracker.apply("Kael", cond)
        assert "Poisoned" in msg
        assert "3 rounds" in msg
        assert tracker.has("Kael", ConditionType.POISONED)

    def test_remove_condition(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        tracker.apply("Kael", Condition(ConditionType.STUNNED, duration=1))
        msg = tracker.remove("Kael", ConditionType.STUNNED)
        assert "removed" in msg
        assert not tracker.has("Kael", ConditionType.STUNNED)

    def test_remove_nonexistent(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, ConditionType,
        )
        tracker = ConditionTracker()
        msg = tracker.remove("Ghost", ConditionType.BLINDED)
        assert "no conditions" in msg.lower() or "not" in msg.lower()

    def test_tick_round_expires(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        tracker.apply("Kael", Condition(ConditionType.BURNING, duration=1))
        msgs = tracker.tick_round("Kael")
        assert len(msgs) == 1
        assert "expired" in msgs[0]
        assert not tracker.has("Kael", ConditionType.BURNING)

    def test_tick_round_permanent(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        tracker.apply("Kael", Condition(ConditionType.BLIGHTED, duration=-2))
        msgs = tracker.tick_round("Kael")
        assert len(msgs) == 0  # Permanent doesn't expire
        assert tracker.has("Kael", ConditionType.BLIGHTED)

    def test_should_skip_turn(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        assert not tracker.should_skip_turn("Kael")
        tracker.apply("Kael", Condition(ConditionType.STUNNED, duration=2))
        assert tracker.should_skip_turn("Kael")

    def test_attack_modifier(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        tracker.apply("Kael", Condition(ConditionType.POISONED, duration=3, modifier=-2))
        tracker.apply("Kael", Condition(ConditionType.BLESSED, duration=3, modifier=2))
        mod = tracker.get_attack_mod("Kael")
        assert mod == 0  # -2 + 2 = 0

    def test_persistence_roundtrip(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        tracker.apply("Kael", Condition(ConditionType.POISONED, duration=3, modifier=-2))
        tracker.apply("Bryn", Condition(ConditionType.BLESSED, duration=5, modifier=2))

        data = tracker.to_dict()
        restored = ConditionTracker.from_dict(data)
        assert restored.has("Kael", ConditionType.POISONED)
        assert restored.has("Bryn", ConditionType.BLESSED)
        assert not restored.has("Kael", ConditionType.BLESSED)

    def test_clear_all(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        tracker.apply("Kael", Condition(ConditionType.POISONED, duration=3))
        tracker.apply("Kael", Condition(ConditionType.STUNNED, duration=1))
        tracker.clear_all("Kael")
        assert not tracker.has("Kael", ConditionType.POISONED)
        assert not tracker.has("Kael", ConditionType.STUNNED)

    def test_replace_same_condition(self):
        from codex.core.mechanics.conditions import (
            ConditionTracker, Condition, ConditionType,
        )
        tracker = ConditionTracker()
        tracker.apply("Kael", Condition(ConditionType.POISONED, duration=1))
        tracker.apply("Kael", Condition(ConditionType.POISONED, duration=5))
        # Should have only 1 POISONED, refreshed to 5
        conds = tracker.get_conditions("Kael")
        assert len(conds) == 1
        assert conds[0].duration == 5


# =========================================================================
# 2. INITIATIVE TRACKER
# =========================================================================

class TestInitiativeTracker:
    """Tests for codex.core.mechanics.initiative."""

    def test_roll_and_sort(self):
        from codex.core.mechanics.initiative import InitiativeTracker
        tracker = InitiativeTracker()
        rng = random.Random(42)
        tracker.roll_initiative("Kael", modifier=3, is_player=True, die=20, rng=rng)
        tracker.roll_initiative("Goblin", modifier=-1, is_player=False, die=20, rng=rng)
        tracker.roll_initiative("Bryn", modifier=2, is_player=True, die=20, rng=rng)
        tracker.sort()
        order = tracker.get_order()
        assert len(order) == 3
        # Sorted descending by roll
        rolls = [e.roll for e in tracker.entries]
        assert rolls == sorted(rolls, reverse=True)

    def test_next_turn_wraps(self):
        from codex.core.mechanics.initiative import InitiativeTracker
        tracker = InitiativeTracker()
        rng = random.Random(42)
        tracker.roll_initiative("A", 0, True, 6, rng)
        tracker.roll_initiative("B", 0, False, 6, rng)
        tracker.sort()

        # First turn
        assert tracker.round_number == 1
        entry1 = tracker.next_turn()
        assert entry1 is not None

        # Second turn — should wrap
        entry2 = tracker.next_turn()
        assert entry2 is not None
        assert entry2.name != entry1.name

    def test_remove_dead(self):
        from codex.core.mechanics.initiative import InitiativeTracker
        tracker = InitiativeTracker()
        rng = random.Random(42)
        tracker.roll_initiative("Alive", 0, True, 6, rng)
        tracker.roll_initiative("Dead", 0, False, 6, rng)
        tracker.sort()

        tracker.remove("Dead")
        order = tracker.get_order()
        assert "Dead" not in order
        assert "Alive" in order

    def test_reset(self):
        from codex.core.mechanics.initiative import InitiativeTracker
        tracker = InitiativeTracker()
        tracker.roll_initiative("A", 0, True, 6)
        tracker.reset()
        assert len(tracker.entries) == 0
        assert tracker.round_number == 1

    def test_persistence_roundtrip(self):
        from codex.core.mechanics.initiative import InitiativeTracker
        tracker = InitiativeTracker()
        tracker.roll_initiative("Kael", 3, True, 20)
        tracker.roll_initiative("Goblin", -1, False, 20)
        tracker.sort()
        tracker.round_number = 3

        data = tracker.to_dict()
        restored = InitiativeTracker.from_dict(data)
        assert len(restored.entries) == 2
        assert restored.round_number == 3
        assert restored.entries[0].name == tracker.entries[0].name

    def test_empty_tracker(self):
        from codex.core.mechanics.initiative import InitiativeTracker
        tracker = InitiativeTracker()
        assert tracker.current() is None
        assert tracker.next_turn() is None
        assert tracker.get_order() == []


# =========================================================================
# 3. REST MANAGER
# =========================================================================

class TestRestManager:
    """Tests for codex.core.mechanics.rest."""

    def test_short_rest_dnd5e(self):
        from codex.core.mechanics.rest import RestManager
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.current_hp = 5  # Wounded
        engine.character.hit_dice_remaining = 1

        mgr = RestManager()
        result = mgr.short_rest_dnd5e(engine)
        assert result.rest_type == "short"
        assert "Aldric" in result.hp_recovered
        assert result.hp_recovered["Aldric"] > 0

    def test_long_rest_dnd5e(self):
        from codex.core.mechanics.rest import RestManager
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.current_hp = 3

        mgr = RestManager()
        result = mgr.long_rest_dnd5e(engine)
        assert result.rest_type == "long"
        assert engine.character.current_hp == engine.character.max_hp

    def test_short_rest_cosmere(self):
        from codex.core.mechanics.rest import RestManager
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner", intellect=14)
        assert engine.character is not None
        engine.character.focus = 0

        mgr = RestManager()
        result = mgr.short_rest_cosmere(engine)
        assert result.rest_type == "short"
        assert engine.character.focus > 0

    def test_downtime_bitd(self):
        from codex.core.mechanics.rest import RestManager
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Vex", playbook="Cutter", vice="gambling")
        # Push stress first
        engine.stress_clocks["Vex"].push(5)

        mgr = RestManager()
        result = mgr.downtime_bitd(engine, "Vex", "vice")
        assert result.rest_type == "downtime"
        assert len(result.resources_reset) > 0

    def test_rest_dispatcher(self):
        from codex.core.mechanics.rest import RestManager
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.current_hp = 3

        mgr = RestManager()
        result = mgr.rest(engine, "DND5E", "long")
        assert result.rest_type == "long"
        assert engine.character.current_hp == engine.character.max_hp

    def test_rest_summary(self):
        from codex.core.mechanics.rest import RestResult
        result = RestResult(
            rest_type="short",
            hp_recovered={"Kael": 5, "Bryn": 3},
            resources_reset=["bandages"],
            side_effects=["Doom +1"],
        )
        summary = result.summary()
        assert "SHORT REST" in summary
        assert "Kael" in summary
        assert "Doom +1" in summary


# =========================================================================
# 4. PROGRESSION TRACKER
# =========================================================================

class TestProgressionTracker:
    """Tests for codex.core.mechanics.progression."""

    def test_award_xp(self):
        from codex.core.mechanics.progression import ProgressionTracker
        tracker = ProgressionTracker(system="xp")
        msg = tracker.award_xp(300, "goblin ambush")
        assert "300" in msg
        assert tracker.current_xp == 300

    def test_check_level_up(self):
        from codex.core.mechanics.progression import ProgressionTracker
        tracker = ProgressionTracker(system="xp", current_xp=300)
        assert tracker.check_level_up(1)  # 300 >= 300 for level 2
        assert not tracker.check_level_up(2)  # Need 900 for level 3

    def test_xp_to_next(self):
        from codex.core.mechanics.progression import ProgressionTracker
        tracker = ProgressionTracker(system="xp", current_xp=100)
        remaining = tracker.get_xp_to_next(1)
        assert remaining == 200  # 300 - 100

    def test_fitd_mark(self):
        from codex.core.mechanics.progression import ProgressionTracker
        tracker = ProgressionTracker(system="fitd")
        for i in range(7):
            msg = tracker.mark_xp("desperate action")
            assert "ADVANCE" not in msg
        msg = tracker.mark_xp("final mark")
        assert "ADVANCE" in msg
        assert tracker.current_xp == 0  # Reset after advance

    def test_milestone(self):
        from codex.core.mechanics.progression import ProgressionTracker
        tracker = ProgressionTracker(system="milestone")
        msg = tracker.advance_milestone("Swore 2nd Ideal")
        assert "Milestone #1" in msg
        assert tracker.milestones == 1

    def test_persistence_roundtrip(self):
        from codex.core.mechanics.progression import ProgressionTracker
        tracker = ProgressionTracker(system="xp", current_xp=450)
        tracker.award_xp(50, "test")
        data = tracker.to_dict()
        restored = ProgressionTracker.from_dict(data)
        assert restored.current_xp == 500
        assert restored.system == "xp"
        assert len(restored.xp_log) > 0


# =========================================================================
# 5. GENERIC AUTOPILOT
# =========================================================================

class TestGenericAutopilot:
    """Tests for codex.core.autopilot.GenericAutopilotAgent."""

    def test_snapshot_dnd5e(self):
        from codex.core.autopilot import GenericAutopilotAgent
        from codex.games.burnwillow.autopilot import PERSONALITY_POOL
        from codex.games.dnd5e import DnD5eEngine

        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")

        agent = GenericAutopilotAgent(PERSONALITY_POOL[0], "DND5E")
        snapshot = agent.build_snapshot(engine, "exploration")
        assert "hp_pct" in snapshot
        assert snapshot["hp_pct"] == 1.0

    def test_snapshot_bitd(self):
        from codex.core.autopilot import GenericAutopilotAgent
        from codex.games.burnwillow.autopilot import PERSONALITY_POOL
        from codex.games.bitd import BitDEngine

        engine = BitDEngine()
        engine.create_character("Vex", playbook="Cutter")

        agent = GenericAutopilotAgent(PERSONALITY_POOL[0], "BITD")
        snapshot = agent.build_snapshot(engine, "exploration")
        assert "hp_pct" in snapshot
        assert snapshot["hp_pct"] == 1.0  # No stress = full "hp"

    def test_decide_exploration(self):
        from codex.core.autopilot import GenericAutopilotAgent
        from codex.games.burnwillow.autopilot import PERSONALITY_POOL
        from codex.games.dnd5e import DnD5eEngine

        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")

        agent = GenericAutopilotAgent(PERSONALITY_POOL[0], "DND5E")
        action = agent.decide(engine, "exploration")
        assert isinstance(action, str)
        assert len(action) > 0

    def test_execute_dnd5e(self):
        from codex.core.autopilot import GenericAutopilotAgent
        from codex.games.burnwillow.autopilot import PERSONALITY_POOL
        from codex.games.dnd5e import DnD5eEngine

        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")

        agent = GenericAutopilotAgent(PERSONALITY_POOL[0], "DND5E")
        result = agent.execute("attack", engine)
        assert "Companion" in result

    def test_toggle(self):
        from codex.core.autopilot import GenericAutopilotAgent
        from codex.games.burnwillow.autopilot import PERSONALITY_POOL

        agent = GenericAutopilotAgent(PERSONALITY_POOL[0], "DND5E")
        assert not agent.enabled
        msg = agent.toggle(True)
        assert "ENABLED" in msg
        assert agent.enabled
        msg = agent.toggle(False)
        assert "DISABLED" in msg


# =========================================================================
# 6. VITALS SCHEMA — All 5 adapters
# =========================================================================

class TestVitalsAdapters:
    """Tests for VitalsSchema adapters with real engine instances."""

    def test_burnwillow_vitals(self):
        from codex.core.dm_dashboard import vitals_from_burnwillow
        from codex.games.burnwillow.engine import BurnwillowEngine

        engine = BurnwillowEngine()
        engine.create_party(["Kael", "Bryn"])
        vitals = vitals_from_burnwillow(engine)
        assert vitals.system_tag == "BURNWILLOW"
        assert vitals.primary_resource == "HP"
        assert vitals.primary_current > 0
        assert vitals.secondary_resource == "Doom"
        assert len(vitals.party) == 2

    def test_crown_vitals(self):
        from codex.core.dm_dashboard import vitals_from_crown
        from codex.games.crown.engine import CrownAndCrewEngine

        engine = CrownAndCrewEngine()
        engine.setup()
        vitals = vitals_from_crown(engine)
        assert vitals.system_tag == "CROWN"
        assert vitals.primary_resource == "Sway"
        assert vitals.secondary_resource == "Day"
        assert "patron" in vitals.extra

    def test_bitd_vitals(self):
        from codex.core.dm_dashboard import vitals_from_bitd
        from codex.games.bitd import BitDEngine

        engine = BitDEngine()
        engine.create_character("Vex", playbook="Cutter")
        vitals = vitals_from_bitd(engine)
        assert vitals.system_tag == "BITD"
        assert vitals.primary_resource == "Stress"
        assert vitals.secondary_resource == "Heat"
        assert "crew_name" in vitals.extra

    def test_dnd5e_vitals(self):
        from codex.core.dm_dashboard import vitals_from_dnd5e
        from codex.games.dnd5e import DnD5eEngine

        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter", race="human")
        vitals = vitals_from_dnd5e(engine)
        assert vitals.system_tag == "DND5E"
        assert vitals.primary_resource == "HP"
        assert vitals.primary_current > 0
        assert "ability_scores" in vitals.extra

    def test_cosmere_vitals(self):
        from codex.core.dm_dashboard import vitals_from_cosmere
        from codex.games.stc import CosmereEngine

        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        vitals = vitals_from_cosmere(engine)
        assert vitals.system_tag == "STC"
        assert vitals.primary_resource == "HP"
        assert vitals.secondary_resource == "Focus"
        assert "surges" in vitals.extra

    def test_get_vitals_dispatcher(self):
        from codex.core.dm_dashboard import get_vitals
        from codex.games.dnd5e import DnD5eEngine

        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        vitals = get_vitals(engine, "DND5E")
        assert vitals.system_tag == "DND5E"

    def test_get_vitals_unknown_system(self):
        from codex.core.dm_dashboard import get_vitals
        vitals = get_vitals(None, "UNKNOWN")
        assert vitals.system_tag == "UNKNOWN"


# =========================================================================
# 7. DM DASHBOARD
# =========================================================================

class TestDMDashboard:
    """Tests for DMDashboard rendering and command dispatch."""

    def _make_dashboard(self, system="DND5E"):
        from codex.core.dm_dashboard import DMDashboard
        console = Console(force_terminal=True, width=120)
        return DMDashboard(console, system)

    def test_render_returns_layout(self):
        from codex.core.dm_dashboard import VitalsSchema
        dashboard = self._make_dashboard()
        vitals = VitalsSchema(
            system_name="Test", system_tag="DND5E",
            primary_resource="HP", primary_current=10, primary_max=20,
        )
        layout = dashboard.render(vitals)
        assert isinstance(layout, Layout)

    def test_dispatch_roll(self):
        dashboard = self._make_dashboard()
        result = dashboard.dispatch_command("roll 2d6")
        assert result  # Non-empty string
        assert len(dashboard._notes) > 0

    def test_dispatch_note(self):
        dashboard = self._make_dashboard()
        result = dashboard.dispatch_command("note Party found a secret passage")
        assert "Note added" in result
        assert "secret passage" in dashboard._notes[-1]

    def test_dispatch_npc(self):
        dashboard = self._make_dashboard()
        result = dashboard.dispatch_command("npc Wizard")
        assert "Wizard" in result or len(result) > 10

    def test_dispatch_help(self):
        dashboard = self._make_dashboard()
        result = dashboard.dispatch_command("help")
        assert "roll" in result
        assert "quit" in result

    def test_dispatch_unknown(self):
        dashboard = self._make_dashboard()
        result = dashboard.dispatch_command("xyzzy")
        assert "Unknown" in result

    def test_dispatch_condition(self):
        dashboard = self._make_dashboard()
        result = dashboard.dispatch_command("condition Kael Poisoned 3")
        assert "Poisoned" in result
        assert dashboard.conditions.has("Kael",
            __import__("codex.core.mechanics.conditions", fromlist=["ConditionType"]).ConditionType.POISONED)

    def test_dispatch_uncondition(self):
        dashboard = self._make_dashboard()
        dashboard.dispatch_command("condition Kael Stunned 2")
        result = dashboard.dispatch_command("uncondition Kael Stunned")
        assert "removed" in result

    def test_dispatch_init_with_engine(self):
        from codex.games.dnd5e import DnD5eEngine
        dashboard = self._make_dashboard()
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        result = dashboard.dispatch_command("init roll", engine)
        assert "Initiative" in result or "Order" in result

    def test_dispatch_rest_with_engine(self):
        from codex.games.dnd5e import DnD5eEngine
        dashboard = self._make_dashboard()
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.current_hp = 3
        result = dashboard.dispatch_command("rest long", engine)
        assert "LONG REST" in result
        assert engine.character.current_hp == engine.character.max_hp

    def test_dispatch_companion_toggle(self):
        dashboard = self._make_dashboard()
        result = dashboard.dispatch_command("companion on")
        assert "ENABLED" in result
        assert dashboard.companion is not None
        assert dashboard.companion.enabled

    def test_dispatch_bestiary(self):
        dashboard = self._make_dashboard("BURNWILLOW")
        result = dashboard.dispatch_command("bestiary rot-beetle")
        assert "Rot-Beetle" in result or "not found" in result.lower()

    def test_dispatch_encounter(self):
        dashboard = self._make_dashboard("BURNWILLOW")
        result = dashboard.dispatch_command("encounter 1")
        assert "Encounter" in result or "Tier" in result


# =========================================================================
# 8. NEW DM TOOLS
# =========================================================================

class TestNewDMTools:
    """Tests for query_codex and lookup_creature."""

    def test_lookup_creature_burnwillow(self):
        from codex.core.dm_tools import lookup_creature
        result = lookup_creature("rot-beetle", "BURNWILLOW")
        assert "Rot-Beetle" in result

    def test_lookup_creature_not_found(self):
        from codex.core.dm_tools import lookup_creature
        result = lookup_creature("nonexistent-monster-xyz", "BURNWILLOW")
        assert "not found" in result.lower() or "No creature" in result

    def test_lookup_creature_dnd5e(self):
        from codex.core.dm_tools import lookup_creature
        result = lookup_creature("goblin", "DND5E")
        assert "Goblin" in result

    def test_lookup_creature_stc(self):
        from codex.core.dm_tools import lookup_creature
        result = lookup_creature("cremling", "STC")
        assert "Cremling" in result

    @patch("codex.core.services.litert_engine.get_litert_engine")
    def test_query_codex_mocked(self, mock_get_engine):
        """Test query_codex with mocked LiteRT-LM response."""
        from codex.core.dm_tools import query_codex
        mock_engine = MagicMock()
        mock_engine.generate_sync.return_value = (
            "The Doom Clock is a timer that tracks dungeon pressure.", 15
        )
        mock_get_engine.return_value = mock_engine

        result = query_codex("What is the doom clock?")
        assert "Doom Clock" in result or "timer" in result

    @patch("codex.core.services.litert_engine.get_litert_engine")
    def test_query_codex_engine_error(self, mock_get_engine):
        """Test graceful error handling when LiteRT-LM fails."""
        from codex.core.dm_tools import query_codex
        mock_get_engine.side_effect = RuntimeError("Engine failed to load")
        result = query_codex("test question")
        assert "failed" in result.lower()

    def test_query_codex_empty(self):
        from codex.core.dm_tools import query_codex
        result = query_codex("")
        assert "No question" in result


# =========================================================================
# 9. BROADCAST EVENT CAPTURE
# =========================================================================

class TestBroadcastCapture:
    """Tests for broadcast event subscription in DMDashboard."""

    def test_event_log_captures(self):
        from codex.core.dm_dashboard import DMDashboard
        console = Console(force_terminal=True, width=80)
        dashboard = DMDashboard(console, "BURNWILLOW")

        # Simulate broadcast event
        dashboard._on_broadcast({
            "_source_module": "burnwillow",
            "type": "MAP_UPDATE",
        })
        assert len(dashboard._event_log) == 1
        assert "burnwillow" in dashboard._event_log[0]

    def test_event_log_max_size(self):
        from codex.core.dm_dashboard import DMDashboard
        console = Console(force_terminal=True, width=80)
        dashboard = DMDashboard(console, "DND5E")

        for i in range(25):
            dashboard._on_broadcast({"type": f"EVENT_{i}"})
        assert len(dashboard._event_log) == 20  # Capped at 20


# =========================================================================
# 10. ENGINE MODIFICATIONS
# =========================================================================

class TestDnD5eEngineModifications:
    """Tests for DnD5e engine additions (WO-V34.0)."""

    def test_hit_dice_init(self):
        from codex.games.dnd5e import DnD5eCharacter
        char = DnD5eCharacter(name="Aldric", character_class="fighter", level=3)
        assert char.hit_die_type == 10  # Fighter = d10
        assert char.hit_dice_remaining == 3

    def test_xp_field(self):
        from codex.games.dnd5e import DnD5eCharacter
        char = DnD5eCharacter(name="Aldric", character_class="fighter")
        assert char.xp == 0
        char.xp = 300
        data = char.to_dict()
        assert data["xp"] == 300
        restored = DnD5eCharacter.from_dict(data)
        assert restored.xp == 300

    def test_short_rest(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.current_hp = 3
        result = engine.short_rest()
        assert "SHORT REST" in result

    def test_long_rest(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.current_hp = 3
        result = engine.long_rest()
        assert "LONG REST" in result
        assert engine.character.current_hp == engine.character.max_hp

    def test_gain_xp(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        result = engine.gain_xp(300, "goblin")
        assert "300" in result
        assert engine.character.xp == 300

    def test_level_up(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.xp = 300
        result = engine.level_up("Aldric")
        assert "level 2" in result.lower()
        assert engine.character.level == 2

    def test_level_up_not_enough_xp(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        assert engine.character is not None
        engine.character.xp = 100
        result = engine.level_up("Aldric")
        assert "needs" in result.lower() or "more XP" in result

    def test_handle_command(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Aldric", character_class="fighter")
        result = engine.handle_command("party_status")
        assert "Aldric" in result


class TestBitDEngineModifications:
    """Tests for BitD engine additions (WO-V34.0)."""

    def test_xp_marks_field(self):
        from codex.games.bitd import BitDCharacter
        char = BitDCharacter(name="Vex", playbook="Cutter")
        assert char.xp_marks == 0

    def test_cmd_downtime_vice(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Vex", playbook="Cutter", vice="gambling")
        engine.stress_clocks["Vex"].push(5)
        result = engine._cmd_downtime_vice()
        assert "vice" in result.lower() or "recovered" in result.lower()

    def test_cmd_advance(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Vex", playbook="Cutter")
        assert engine.character is not None
        result = engine._cmd_advance(trigger="desperate action")
        assert "marks XP" in result
        assert engine.character.xp_marks == 1

    def test_cmd_advance_triggers_playbook(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Vex", playbook="Cutter")
        assert engine.character is not None
        engine.character.xp_marks = 7
        result = engine._cmd_advance(trigger="final mark")
        assert "ADVANCE" in result

    def test_handle_command_routes(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Vex", playbook="Cutter", vice="gambling")
        result = engine.handle_command("downtime_vice")
        assert isinstance(result, str)
        result2 = engine.handle_command("advance", trigger="test")
        assert "marks XP" in result2


class TestCosmereEngineModifications:
    """Tests for Cosmere engine additions (WO-V34.0)."""

    def test_ideal_level_field(self):
        from codex.games.stc import CosmereCharacter
        char = CosmereCharacter(name="Kaladin", order="windrunner")
        assert char.ideal_level == 1

    def test_swear_ideal(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        assert engine.character is not None
        old_max_hp = engine.character.max_hp
        result = engine.swear_ideal("Kaladin")
        assert "2nd Ideal" in result
        assert engine.character.ideal_level == 2
        assert engine.character.max_hp == old_max_hp + 5

    def test_swear_ideal_max(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        assert engine.character is not None
        engine.character.ideal_level = 5
        result = engine.swear_ideal("Kaladin")
        assert "all 5 Ideals" in result

    def test_handle_command(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        result = engine.handle_command("party_status")
        assert "Kaladin" in result
        assert "windrunner" in result.lower()

    def test_handle_command_unknown(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Kaladin", order="windrunner")
        result = engine.handle_command("nonexistent")
        assert "Unknown" in result


class TestBurnwillowConditionTriggers:
    """Tests for burnwillow/content.py condition triggers (WO-V34.0)."""

    def test_enemy_condition_triggers_exist(self):
        from codex.games.burnwillow.content import ENEMY_CONDITION_TRIGGERS
        assert "Blight-Hawk" in ENEMY_CONDITION_TRIGGERS
        assert "Spore-Crawler" in ENEMY_CONDITION_TRIGGERS

    def test_blight_hawk_trigger(self):
        from codex.games.burnwillow.content import ENEMY_CONDITION_TRIGGERS
        trigger = ENEMY_CONDITION_TRIGGERS["Blight-Hawk"]
        assert trigger["condition"] == "Blighted"
        assert trigger["duration"] == 2
        assert trigger["save_dc"] == 12

    def test_spore_crawler_trigger(self):
        from codex.games.burnwillow.content import ENEMY_CONDITION_TRIGGERS
        trigger = ENEMY_CONDITION_TRIGGERS["Spore-Crawler"]
        assert trigger["condition"] == "Poisoned"
        assert trigger["duration"] == 3


# =========================================================================
# MECHANICS PACKAGE IMPORTS
# =========================================================================

class TestMechanicsPackage:
    """Verify the mechanics __init__.py exports all expected symbols."""

    def test_imports(self):
        from codex.core.mechanics import (
            ConditionType, Condition, ConditionTracker,
            InitiativeEntry, InitiativeTracker,
            RestManager, RestResult,
            ProgressionTracker, DND5E_XP_TABLE, FITD_XP_PER_ADVANCE,
            UniversalClock, FactionClock, DoomClock,
        )
        assert ConditionType.POISONED.value == "Poisoned"
        assert FITD_XP_PER_ADVANCE == 8
        assert 2 in DND5E_XP_TABLE

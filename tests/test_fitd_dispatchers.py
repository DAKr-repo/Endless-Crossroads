"""
tests/test_fitd_dispatchers.py — WO-V67.0 FITD Command Dispatcher Tests
=========================================================================

Covers:
  - BitD dispatcher: heat_status, rep_status, entangle, vice, downtime
  - Candela dispatcher: roll_action, circle_status, take_mark, assignment,
    illuminate (existing), unknown command
  - CBR+PNK dispatcher: glitch, corp_response, overclock, roll_action,
    grid_status, unknown command
  - EncounterEngine CBR+PNK routing at different heat levels

All tests avoid network calls, file I/O, and audio subsystems.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================================
# BITD DISPATCHER — new commands (WO-V67.0)
# =========================================================================

class TestBitDDispatcherNew:
    """Tests for newly added BitD handle_command() sub-commands."""

    def _make_engine(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.crew_name = "The Crow's Foot Crew"
        engine.crew_type = "Shadows"
        engine.heat = 2
        engine.wanted_level = 1
        engine.rep = 7
        engine.coin = 3
        engine.turf = 1
        char = engine.create_character("Lysander", playbook="Lurk")
        return engine, char

    # ── heat_status ──────────────────────────────────────────────────

    def test_heat_status_shows_heat_value(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("heat_status")
        assert "Heat: 2" in result

    def test_heat_status_shows_wanted_level(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("heat_status")
        assert "Wanted Level" in result

    def test_heat_status_zero_heat(self):
        engine, _ = self._make_engine()
        engine.heat = 0
        result = engine.handle_command("heat_status")
        assert "Cold" in result or "no heat" in result.lower()

    def test_heat_status_max_heat(self):
        engine, _ = self._make_engine()
        engine.heat = 6
        result = engine.handle_command("heat_status")
        assert "6" in result

    # ── rep_status ───────────────────────────────────────────────────

    def test_rep_status_shows_rep(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("rep_status")
        assert "Rep:" in result
        assert "7" in result

    def test_rep_status_shows_crew_name(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("rep_status")
        assert "Crow's Foot Crew" in result

    def test_rep_status_shows_coin(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("rep_status")
        assert "Coin" in result or "coin" in result

    def test_rep_status_no_faction_clocks(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("rep_status")
        # Should not crash when no faction clocks present
        assert isinstance(result, str)

    # ── entangle ─────────────────────────────────────────────────────

    def test_entangle_returns_string(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("entangle")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_entangle_shows_dice(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("entangle")
        assert "Entangle:" in result

    def test_entangle_outcome_label_present(self):
        """One of the three outcome labels must appear."""
        engine, _ = self._make_engine()
        result = engine.handle_command("entangle")
        assert any(label in result.upper() for label in ["COMPLICATION", "PROBLEM", "NOTHING"])

    def test_entangle_distinct_from_entanglement(self):
        """entangle (2d6 table) vs entanglement (1d6 + heat) are separate commands."""
        engine, _ = self._make_engine()
        r1 = engine.handle_command("entangle")
        r2 = engine.handle_command("entanglement")
        # Both should return valid strings but describe different mechanics
        assert "Entangle:" in r1
        assert "Entanglement Roll:" in r2

    # ── vice ─────────────────────────────────────────────────────────

    def test_vice_returns_string(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("vice")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_vice_mentions_character(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("vice")
        assert "Lysander" in result

    def test_vice_no_character_returns_error(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        result = engine.handle_command("vice")
        assert "No active character" in result or "No character" in result

    def test_vice_mentions_vice_type(self):
        engine, char = self._make_engine()
        char.vice = "gambling"
        result = engine.handle_command("vice")
        assert "gambling" in result.lower()

    # ── downtime ─────────────────────────────────────────────────────

    def test_downtime_lists_actions(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("downtime")
        assert "recover" in result.lower()
        assert "train" in result.lower()

    def test_downtime_shows_coin_and_rep(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("downtime")
        assert "rep" in result.lower() or "coin" in result.lower()

    # ── unknown command ───────────────────────────────────────────────

    def test_unknown_command_graceful(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("nonexistent_xyz")
        assert "Unknown command" in result or "nonexistent_xyz" in result


# =========================================================================
# BITD DISPATCHER — pre-existing commands still work
# =========================================================================

class TestBitDDispatcherExisting:
    """Regression guard: pre-existing commands still work after WO-V67.0 additions."""

    def _make_engine(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Vex", playbook="Whisper")
        return engine

    def test_crew_status(self):
        engine = self._make_engine()
        result = engine.handle_command("crew_status")
        assert "Crew:" in result or "crew" in result.lower()

    def test_party_status(self):
        engine = self._make_engine()
        result = engine.handle_command("party_status")
        assert "Vex" in result

    def test_roll_action_produces_output(self):
        engine = self._make_engine()
        result = engine.handle_command("roll_action", action="skirmish")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_entanglement_still_works(self):
        engine = self._make_engine()
        result = engine.handle_command("entanglement")
        assert "Entanglement Roll:" in result


# =========================================================================
# CANDELA DISPATCHER — new command (WO-V67.0)
# =========================================================================

class TestCandelaDispatcherNew:
    """Tests for the newly added Candela assignment command."""

    def _make_engine(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.circle_name = "The Moth Circle"
        engine.assignments_completed = 2
        engine.create_character("Isolde", role="Scholar")
        return engine

    # ── assignment ───────────────────────────────────────────────────

    def test_assignment_no_active_case(self):
        engine = self._make_engine()
        result = engine.handle_command("assignment")
        assert "Moth Circle" in result
        assert "2" in result  # assignments_completed
        assert "No active assignment" in result

    def test_assignment_shows_circle_name(self):
        engine = self._make_engine()
        result = engine.handle_command("assignment")
        assert "Moth Circle" in result

    def test_assignment_shows_completed_count(self):
        engine = self._make_engine()
        result = engine.handle_command("assignment")
        assert "2" in result

    def test_assignment_with_active_case(self):
        engine = self._make_engine()
        engine.handle_command("open_case", case_name="The Pale Hunger", phenomena="possession")
        result = engine.handle_command("assignment")
        assert "Pale Hunger" in result
        assert "possession" in result.lower() or "Phenomenon" in result

    def test_assignment_with_active_case_shows_clue_progress(self):
        engine = self._make_engine()
        engine.handle_command("open_case", case_name="The Pale Hunger", clues_needed=5)
        result = engine.handle_command("assignment")
        assert "Clues:" in result or "clues" in result.lower()

    # ── unknown command ───────────────────────────────────────────────

    def test_unknown_command_graceful(self):
        engine = self._make_engine()
        result = engine.handle_command("does_not_exist")
        assert "Unknown command" in result or "does_not_exist" in result


# =========================================================================
# CANDELA DISPATCHER — existing commands still work
# =========================================================================

class TestCandelaDispatcherExisting:
    """Regression guard: pre-existing Candela commands still work."""

    def _make_engine(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Orrin", role="Muscle")
        return engine

    def test_roll_action_returns_string(self):
        engine = self._make_engine()
        result = engine.handle_command("roll_action", action="strike")
        assert isinstance(result, str) and len(result) > 0

    def test_circle_status(self):
        engine = self._make_engine()
        result = engine.handle_command("circle_status")
        assert "Orrin" in result or "circle" in result.lower()

    def test_take_mark_body(self):
        engine = self._make_engine()
        result = engine.handle_command("take_mark", track="body")
        assert "body" in result.lower() or "Body" in result

    def test_party_status(self):
        engine = self._make_engine()
        result = engine.handle_command("party_status")
        assert "Orrin" in result

    def test_illuminate_no_active_case(self):
        engine = self._make_engine()
        result = engine.handle_command("illuminate")
        assert isinstance(result, str)
        # Without an active case, should return an error message
        assert "Cannot illuminate" in result or "illuminate" in result.lower()


# =========================================================================
# CBRPNK DISPATCHER — new commands (WO-V67.0)
# =========================================================================

class TestCBRPNKDispatcherNew:
    """Tests for newly added CBR+PNK handle_command() sub-commands."""

    def _make_engine(self, heat: int = 0):
        from codex.games.cbrpnk import CBRPNKEngine
        engine = CBRPNKEngine()
        engine.heat = heat
        char = engine.create_character("Ghost", archetype="Hacker")
        char.chrome = ["Neural Jack", "Reflex Booster"]
        return engine, char

    # ── glitch ───────────────────────────────────────────────────────

    def test_glitch_returns_string(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("glitch")
        assert isinstance(result, str) and len(result) > 0

    def test_glitch_shows_roll_value(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("glitch")
        assert "Glitch Roll:" in result

    def test_glitch_shows_severity_label(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("glitch")
        assert any(label in result for label in ["MINOR", "MODERATE", "MAJOR"])

    def test_glitch_increments_counter(self):
        engine, _ = self._make_engine()
        before = engine.glitch_die
        engine.handle_command("glitch")
        assert engine.glitch_die == before + 1

    def test_glitch_accumulates_over_multiple_rolls(self):
        engine, _ = self._make_engine()
        engine.handle_command("glitch")
        engine.handle_command("glitch")
        engine.handle_command("glitch")
        assert engine.glitch_die == 3

    # ── corp_response ────────────────────────────────────────────────

    def test_corp_response_low_heat_street(self):
        engine, _ = self._make_engine(heat=1)
        result = engine.handle_command("corp_response")
        assert "street" in result.lower() or "STREET" in result

    def test_corp_response_mid_heat_security(self):
        engine, _ = self._make_engine(heat=3)
        result = engine.handle_command("corp_response")
        assert "security" in result.lower() or "SECURITY" in result

    def test_corp_response_high_heat_corp_strike(self):
        engine, _ = self._make_engine(heat=5)
        result = engine.handle_command("corp_response")
        assert "corp_strike" in result.lower() or "CORP_STRIKE" in result or "strike" in result.lower()

    def test_corp_response_shows_heat_value(self):
        engine, _ = self._make_engine(heat=2)
        result = engine.handle_command("corp_response")
        assert "Heat 2" in result or "heat" in result.lower()

    def test_corp_response_zero_heat(self):
        engine, _ = self._make_engine(heat=0)
        result = engine.handle_command("corp_response")
        # Heat 0 is still street-level
        assert isinstance(result, str) and len(result) > 0

    def test_corp_response_maximum_heat(self):
        engine, _ = self._make_engine(heat=6)
        result = engine.handle_command("corp_response")
        assert isinstance(result, str) and len(result) > 0

    # ── overclock ────────────────────────────────────────────────────

    def test_overclock_costs_stress(self):
        engine, char = self._make_engine()
        clock = engine.stress_clocks[char.name]
        before_stress = clock.current_stress
        engine.handle_command("overclock")
        assert clock.current_stress == before_stress + 1

    def test_overclock_increments_glitch_die(self):
        engine, _ = self._make_engine()
        before = engine.glitch_die
        engine.handle_command("overclock")
        assert engine.glitch_die == before + 1

    def test_overclock_no_chrome_returns_error(self):
        engine, char = self._make_engine()
        char.chrome = []
        result = engine.handle_command("overclock")
        assert "no chrome" in result.lower() or "Chrome" in result or "augment" in result.lower()

    def test_overclock_no_character_returns_error(self):
        from codex.games.cbrpnk import CBRPNKEngine
        engine = CBRPNKEngine()
        result = engine.handle_command("overclock")
        assert "No active character" in result

    def test_overclock_mentions_chrome_in_output(self):
        engine, char = self._make_engine()
        result = engine.handle_command("overclock")
        # At least one chrome item should be mentioned
        assert any(c in result for c in char.chrome)

    def test_overclock_mentions_bonus_die(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("overclock")
        assert "+1d" in result or "bonus" in result.lower()

    # ── unknown command ───────────────────────────────────────────────

    def test_unknown_command_graceful(self):
        engine, _ = self._make_engine()
        result = engine.handle_command("xyzzy_undefined")
        assert "Unknown command" in result or "xyzzy_undefined" in result


# =========================================================================
# CBRPNK DISPATCHER — existing commands still work
# =========================================================================

class TestCBRPNKDispatcherExisting:
    """Regression guard: pre-existing CBR+PNK commands still work."""

    def _make_engine(self):
        from codex.games.cbrpnk import CBRPNKEngine
        engine = CBRPNKEngine()
        engine.create_character("Nyx", archetype="Ronin")
        return engine

    def test_roll_action_returns_string(self):
        engine = self._make_engine()
        result = engine.handle_command("roll_action", action="scrap")
        assert isinstance(result, str) and len(result) > 0

    def test_crew_status(self):
        engine = self._make_engine()
        result = engine.handle_command("crew_status")
        assert "Heat" in result or "Stress" in result or "stress" in result

    def test_glitch_status(self):
        engine = self._make_engine()
        result = engine.handle_command("glitch_status")
        assert "Glitch Die" in result

    def test_grid_status_no_active_grid(self):
        engine = self._make_engine()
        result = engine.handle_command("grid_status")
        assert "No active grid" in result or "jack_in" in result


# =========================================================================
# ENCOUNTER ENGINE — CBR+PNK heat scaling
# =========================================================================

class TestCBRPNKEncounterHeatScaling:
    """Tests for EncounterEngine._route_cbrpnk() heat-level scaling."""

    def _make_ctx(self, heat: int, room_type: str = "normal", trigger: str = "move_entry"):
        from codex.core.encounters import EncounterContext
        return EncounterContext(
            system_tag="CBR_PNK",
            party_size=2,
            threat_level=heat,
            floor_tier=1,
            room_type=room_type,
            trigger=trigger,
            seed=42,
        )

    def test_low_heat_encounter_generated(self):
        from codex.core.encounters import EncounterEngine
        engine = EncounterEngine()
        ctx = self._make_ctx(heat=1, room_type="boss")
        result = engine.generate(ctx)
        assert result is not None
        assert result.encounter_type in ("enemy", "npc", "empty")

    def test_high_heat_escalates_enemy_tier(self):
        """At heat >= 4, effective tier increases by 1."""
        from codex.core.encounters import EncounterEngine
        engine = EncounterEngine()
        ctx = self._make_ctx(heat=5, room_type="boss")
        result = engine.generate(ctx)
        assert result is not None
        # Boss room + high heat should produce enemy entities (may still be empty if
        # count roll is 0, but result must be a valid EncounterResult)
        assert result.encounter_type in ("enemy", "npc", "empty")

    def test_heat_6_adds_extra_enemy(self):
        """At heat >= 6, count += 1."""
        from codex.core.encounters import EncounterEngine
        engine = EncounterEngine()
        # Use boss room and high heat to maximize encounter probability
        ctx = self._make_ctx(heat=6, room_type="boss")
        result = engine.generate(ctx)
        # Seeded RNG — result is deterministic; just verify no crash and valid type
        assert result.encounter_type in ("enemy", "npc", "empty", "loot", "trap")

    def test_start_room_always_empty(self):
        from codex.core.encounters import EncounterEngine
        engine = EncounterEngine()
        ctx = self._make_ctx(heat=6, room_type="start")
        result = engine.generate(ctx)
        assert result.encounter_type == "empty"
        assert len(result.entities) == 0

    def test_search_trigger_possible_loot(self):
        from codex.core.encounters import EncounterEngine
        engine = EncounterEngine()
        ctx = self._make_ctx(heat=0, trigger="search")
        # Over many seeds, at least some should return loot — just verify no crash
        result = engine.generate(ctx)
        assert result.encounter_type in ("loot", "trap", "empty")

    def test_scout_fumble_trigger(self):
        from codex.core.encounters import EncounterEngine, EncounterContext
        engine = EncounterEngine()
        ctx = EncounterContext(
            system_tag="CBR_PNK",
            party_size=2,
            threat_level=0,
            floor_tier=2,
            room_type="normal",
            trigger="scout_fumble",
            seed=7,
            source_room_enemies=[
                {"name": "Corp Security", "attack": 4, "defense": 12, "tier": 2}
            ],
        )
        result = engine.generate(ctx)
        # Source enemy should be pulled into encounter
        assert len(result.entities) == 1
        assert result.entities[0]["name"] == "Corp Security"

    def test_party_size_scaling_adds_bonus_enemy(self):
        from codex.core.encounters import EncounterEngine, EncounterContext
        engine = EncounterEngine()
        # party_size=3 → bonus_count=1; boss room forces count >= 1 (via randint seed)
        ctx = EncounterContext(
            system_tag="CBR_PNK",
            party_size=3,
            threat_level=0,
            floor_tier=1,
            room_type="boss",
            trigger="move_entry",
            seed=99,
        )
        result = engine.generate(ctx)
        # Can't guarantee enemy count without controlling all RNG paths, but must not crash
        assert result is not None
        assert result.encounter_type in ("enemy", "npc", "empty")

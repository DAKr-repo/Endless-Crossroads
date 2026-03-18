"""
tests/test_fitd_complications.py — Gap Fix: FITD Complication Tables
=====================================================================
Tests complication command dispatch for all 4 FITD engines + _route_stub removal.
"""
import pytest


# ===========================================================================
# BitD Complications
# ===========================================================================

class TestBitDComplications:
    def test_complication_produces_valid_entry(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Cutter")
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result
        assert "Effect:" in result

    def test_complication_heat_scaling(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Lurk")
        engine.heat = 5  # high heat should push effective tier up
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result

    def test_complication_returns_effect_string(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Spider")
        result = engine.handle_command("complication", tier=2)
        assert "Effect:" in result
        # Effect should not be empty
        effect_line = [l for l in result.split("\n") if l.startswith("Effect:")]
        assert len(effect_line) == 1
        assert effect_line[0] != "Effect:"

    def test_complication_dispatches_via_handle_command(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Slide")
        # Should not return "Unknown command"
        result = engine.handle_command("complication")
        assert "Unknown command" not in result


# ===========================================================================
# SaV Complications
# ===========================================================================

class TestSaVComplications:
    def test_complication_produces_valid_entry(self):
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Pilot")
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result
        assert "Effect:" in result

    def test_complication_heat_scaling(self):
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Mechanic")
        engine.heat = 5
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result

    def test_complication_returns_effect_string(self):
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Scoundrel")
        result = engine.handle_command("complication", tier=3)
        assert "Effect:" in result

    def test_complication_dispatches_via_handle_command(self):
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Speaker")
        result = engine.handle_command("complication")
        assert "Unknown command" not in result


# ===========================================================================
# BoB Complications
# ===========================================================================

class TestBoBComplications:
    def test_complication_produces_valid_entry(self):
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Officer")
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result
        assert "Effect:" in result

    def test_complication_pressure_scaling(self):
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Scout")
        engine.legion.pressure = 5  # high pressure should push tier up
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result

    def test_complication_returns_effect_string(self):
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Heavy")
        result = engine.handle_command("complication", tier=2)
        assert "Effect:" in result

    def test_complication_dispatches_via_handle_command(self):
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Medic")
        result = engine.handle_command("complication")
        assert "Unknown command" not in result


# ===========================================================================
# Candela Complications
# ===========================================================================

class TestCandelaComplications:
    def test_complication_produces_valid_entry(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Scholar")
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result
        assert "Effect:" in result

    def test_complication_assignment_scaling(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Face")
        engine.assignments_completed = 5  # high assignments should push tier
        result = engine.handle_command("complication", tier=1)
        assert "COMPLICATION:" in result

    def test_complication_returns_effect_string(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Slink")
        result = engine.handle_command("complication", tier=3)
        assert "Effect:" in result

    def test_complication_dispatches_via_handle_command(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Weird")
        result = engine.handle_command("complication")
        assert "Unknown command" not in result


# ===========================================================================
# _route_stub removal verification
# ===========================================================================

class TestRouteStubRemoved:
    def test_encounter_engine_no_route_stub(self):
        from codex.core.encounters import EncounterEngine
        engine = EncounterEngine()
        assert not hasattr(engine, '_route_stub')

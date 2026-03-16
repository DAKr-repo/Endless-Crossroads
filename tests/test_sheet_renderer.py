"""
tests/test_sheet_renderer.py — Character Sheet Renderer
========================================================
Tests for:
1. Shared helper functions (dots, stress, marks, hp, gauge, sway)
2. Router dispatch + fallback
3. Per-system renderers (9 systems x 2: with/without character)
4. Edge cases (empty party, missing stress clock, Crown defaults)
"""
from unittest.mock import MagicMock
import pytest

from rich.panel import Panel
from rich.text import Text

from codex.core.sheet_renderer import (
    render_sheet,
    _render_action_dots,
    _render_stress_track,
    _render_mark_track,
    _render_hp_bar,
    _render_resource_gauge,
    _render_sway_gauge,
    _RENDERERS,
)


# =========================================================================
# HELPER TESTS
# =========================================================================

class TestActionDots:
    def test_zero_dots(self):
        t = _render_action_dots(0, 4)
        assert isinstance(t, Text)
        assert t.plain == "\u25cb\u25cb\u25cb\u25cb"

    def test_partial_dots(self):
        t = _render_action_dots(2, 4)
        assert t.plain == "\u25cf\u25cf\u25cb\u25cb"

    def test_full_dots(self):
        t = _render_action_dots(4, 4)
        assert t.plain == "\u25cf\u25cf\u25cf\u25cf"

    def test_over_max_clamped(self):
        t = _render_action_dots(6, 4)
        # Should show 4 filled (clamped by range)
        assert t.plain.count("\u25cf") == 4


class TestStressTrack:
    def test_stress_track(self):
        t = _render_stress_track(4, 9)
        assert isinstance(t, Text)
        assert "4/9" in t.plain
        assert t.plain.count("\u25a0") == 4
        assert t.plain.count("\u25a1") == 5


class TestMarkTrack:
    def test_mark_track_with_label(self):
        t = _render_mark_track(2, 3, "Body")
        assert "Body" in t.plain
        assert "2/3" in t.plain
        assert t.plain.count("\u25a0") == 2
        assert t.plain.count("\u25a1") == 1


class TestHpBar:
    def test_full_hp(self):
        t = _render_hp_bar(36, 36, 16)
        assert "36/36" in t.plain
        assert "\u2591" not in t.plain or t.plain.count("\u2588") == 16

    def test_critical_hp(self):
        t = _render_hp_bar(3, 36, 16)
        assert "3/36" in t.plain
        # Should have mostly empty blocks
        assert t.plain.count("\u2591") > t.plain.count("\u2588")

    def test_zero_max(self):
        t = _render_hp_bar(0, 0, 8)
        assert "0/1" in t.plain  # max clamped to 1


class TestResourceGauge:
    def test_resource_gauge(self):
        t = _render_resource_gauge(4, 8, "Focus")
        assert "Focus" in t.plain
        assert "4/8" in t.plain


class TestSwayGauge:
    def test_sway_gauge_neutral(self):
        t = _render_sway_gauge(0, {"crown_label": "CROWN", "crew_label": "CREW"})
        assert "CROWN" in t.plain
        assert "CREW" in t.plain

    def test_sway_gauge_default_terms(self):
        t = _render_sway_gauge(2, {})
        assert "CROWN" in t.plain
        assert "CREW" in t.plain


# =========================================================================
# ROUTER TESTS
# =========================================================================

class TestRouter:
    def test_all_nine_systems_registered(self):
        expected = {"dnd5e", "stc", "bitd", "sav", "bob", "cbrpnk",
                    "candela", "crown", "burnwillow"}
        assert set(_RENDERERS.keys()) == expected

    def test_unknown_system_fallback(self):
        engine = MagicMock()
        engine.get_status.return_value = "Some status text"
        result = render_sheet(engine, "unknown_system")
        assert isinstance(result, Panel)

    def test_unknown_system_no_status(self):
        engine = MagicMock(spec=[])
        result = render_sheet(engine, "totally_unknown")
        assert isinstance(result, Panel)


# =========================================================================
# PER-SYSTEM TESTS
# =========================================================================

def _make_dnd5e_engine():
    engine = MagicMock()
    engine.system_id = "dnd5e"
    char = MagicMock()
    char.name = "Aldric"
    char.race = "Dwarf"
    char.character_class = "fighter"
    char.level = 5
    char.background = "Soldier"
    char.xp = 6500
    char.strength = 16
    char.dexterity = 12
    char.constitution = 16
    char.intelligence = 10
    char.wisdom = 13
    char.charisma = 8
    char.current_hp = 38
    char.max_hp = 44
    char.armor_class = 18
    char.proficiency_bonus = 3
    char.hit_dice_remaining = 3
    char.hit_die_type = 10
    char.features = ["Second Wind", "Action Surge"]
    char.proficiencies = ["All armor", "shields", "martial weapons"]
    engine.character = char
    return engine


def _make_stc_engine():
    engine = MagicMock()
    engine.system_id = "stc"
    char = MagicMock()
    char.name = "Kaladin"
    char.heritage = "Alethi"
    char.order = "windrunner"
    char.ideal_level = 3
    char.strength = 14
    char.speed = 16
    char.intellect = 12
    char.current_hp = 12
    char.max_hp = 16
    char.defense = 12
    char.focus = 4
    char.max_focus = 8
    char.get_surges.return_value = ["Adhesion", "Gravitation"]
    engine.character = char
    return engine


def _make_fitd_engine(system_id, **extra_char_attrs):
    engine = MagicMock()
    engine.system_id = system_id
    char = MagicMock()
    char.name = "Shade"
    char.playbook = "Lurk"
    char.heritage = "Skovlan"
    char.archetype = "Hacker"
    char.background = "Street"
    char.vice = "Gambling"
    char.chrome = ["Neural Jack", "Reflex Boosters"]
    # Set all potential action dots to 0 by default
    for attr in ["hunt", "study", "survey", "tinker", "finesse", "prowl",
                 "skirmish", "wreck", "attune", "command", "consort", "sway",
                 "doctor", "hack", "rig", "helm", "scramble", "scrap", "skulk",
                 "override", "scan", "shoot"]:
        setattr(char, attr, 1)
    for k, v in extra_char_attrs.items():
        setattr(char, k, v)
    engine.character = char

    # Stress clock
    clock = MagicMock()
    clock.current_stress = 4
    clock.max_stress = 9
    clock.traumas = ["Cold"]
    engine.stress_clocks = {"Shade": clock}

    # System-specific
    engine.crew_name = "The Silver Nails"
    engine.crew_type = "Shadows"
    engine.heat = 2
    engine.wanted_level = 0
    engine.rep = 4
    engine.coin = 3
    engine.turf = 1
    engine.ship_name = "The Stardust"
    engine.ship_class = "Stinger"
    engine.glitch_die = 1
    return engine


def _make_bob_engine():
    engine = MagicMock()
    engine.system_id = "bob"
    char = MagicMock()
    char.name = "Kel"
    char.playbook = "Scout"
    char.heritage = "Panyar"
    for attr in ["doctor", "marshal", "research", "scout_action",
                 "maneuver", "skirmish", "wreck", "consort",
                 "discipline", "sway"]:
        setattr(char, attr, 1)
    engine.character = char

    clock = MagicMock()
    clock.current_stress = 3
    clock.max_stress = 9
    clock.traumas = []
    engine.stress_clocks = {"Kel": clock}

    legion = MagicMock()
    legion.supply = 8
    legion.intel = 6
    legion.morale = 4
    legion.pressure = 4
    engine.legion = legion
    engine.chosen = "The Horned One"
    engine.campaign_phase = "camp"
    return engine


def _make_candela_engine():
    engine = MagicMock()
    engine.system_id = "candela"
    char = MagicMock()
    char.name = "Iris"
    char.role = "Scholar"
    char.specialization = "Doctor"
    char.background = "Academic"
    char.catalyst = "Curiosity"
    for attr in ["move", "strike", "control", "sway", "read", "hide",
                 "survey", "focus", "sense"]:
        setattr(char, attr, 1)
    char.body = 1
    char.body_max = 3
    char.brain = 2
    char.brain_max = 3
    char.bleed = 0
    char.bleed_max = 3
    engine.character = char
    engine.circle_name = "The Crimson Eye"
    engine.assignments_completed = 3
    return engine


def _make_crown_engine():
    engine = MagicMock()
    engine.system_id = "crown"
    engine.day = 4
    engine.arc_length = 5
    engine.sway = 1
    engine.terms = {"crown_label": "CROWN", "crew_label": "CREW"}
    engine.dna = {
        "BLOOD": 3, "GUILE": 5, "HEARTH": 2,
        "SILENCE": 4, "DEFIANCE": 1,
    }
    engine.patron = "The Spymaster"
    engine.leader = "Captain Vane"
    # Crown has no character attribute
    engine.character = None
    return engine


def _make_burnwillow_engine():
    engine = MagicMock()
    engine.system_id = "burnwillow"
    char = MagicMock()
    char.name = "Ash"
    char.current_hp = 12
    char.max_hp = 15
    char.might = 14
    char.wits = 12
    char.grit = 13
    char.aether = 10
    engine.character = char
    return engine


class TestDnD5e:
    def test_with_character(self):
        result = render_sheet(_make_dnd5e_engine(), "dnd5e")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "dnd5e")
        assert isinstance(result, Panel)


class TestSTC:
    def test_with_character(self):
        result = render_sheet(_make_stc_engine(), "stc")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "stc")
        assert isinstance(result, Panel)


class TestBitD:
    def test_with_character(self):
        result = render_sheet(_make_fitd_engine("bitd"), "bitd")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "bitd")
        assert isinstance(result, Panel)


class TestSaV:
    def test_with_character(self):
        result = render_sheet(_make_fitd_engine("sav"), "sav")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "sav")
        assert isinstance(result, Panel)


class TestBoB:
    def test_with_character(self):
        result = render_sheet(_make_bob_engine(), "bob")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "bob")
        assert isinstance(result, Panel)


class TestCBRPNK:
    def test_with_character(self):
        result = render_sheet(_make_fitd_engine("cbrpnk"), "cbrpnk")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "cbrpnk")
        assert isinstance(result, Panel)


class TestCandela:
    def test_with_character(self):
        result = render_sheet(_make_candela_engine(), "candela")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "candela")
        assert isinstance(result, Panel)


class TestCrown:
    def test_with_state(self):
        result = render_sheet(_make_crown_engine(), "crown")
        assert isinstance(result, Panel)

    def test_with_default_terms(self):
        engine = MagicMock()
        engine.day = 1
        engine.arc_length = 5
        engine.sway = 0
        engine.terms = {}
        engine.dna = {}
        engine.patron = ""
        engine.leader = ""
        engine.character = None
        result = render_sheet(engine, "crown")
        assert isinstance(result, Panel)


class TestBurnwillow:
    def test_with_character(self):
        result = render_sheet(_make_burnwillow_engine(), "burnwillow")
        assert isinstance(result, Panel)

    def test_without_character(self):
        engine = MagicMock()
        engine.character = None
        result = render_sheet(engine, "burnwillow")
        assert isinstance(result, Panel)


# =========================================================================
# EDGE CASES
# =========================================================================

class TestEdgeCases:
    def test_empty_party_dnd5e(self):
        engine = MagicMock()
        engine.character = None
        engine.party = []
        result = render_sheet(engine, "dnd5e")
        assert isinstance(result, Panel)

    def test_missing_stress_clock_bitd(self):
        engine = _make_fitd_engine("bitd")
        engine.stress_clocks = {}  # No clock for this character
        result = render_sheet(engine, "bitd")
        assert isinstance(result, Panel)

    def test_crown_extreme_sway(self):
        engine = _make_crown_engine()
        engine.sway = -3
        result = render_sheet(engine, "crown")
        assert isinstance(result, Panel)

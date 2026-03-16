"""
tests/test_omni_parity.py — WO-V23.0 Cross-Platform Parity Tests
=================================================================

Verifies:
1. Serialization round-trip for quest-injected engines
2. Menu parity (BOT_OPTIONS has 9 entries with all expected actions)
3. Quest injection persistence (arc_length, rest_config, terms)
4. Cross-platform session reconstruction from serialized state
"""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codex.games.crown.engine import CrownAndCrewEngine
from codex.core.menu import CodexMenu


# =============================================================================
# SERIALIZATION ROUND-TRIP TESTS
# =============================================================================

class TestSerializationRoundTrip:
    """Verify engine state survives serialize/deserialize."""

    def test_basic_roundtrip(self):
        """Default engine round-trips cleanly."""
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew", "HEARTH")
        engine.end_day()
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored.day == engine.day
        assert restored.sway == engine.sway
        assert restored.arc_length == engine.arc_length

    def test_quest_roundtrip(self):
        """Quest-injected engine round-trips with all quest data intact."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return  # Skip if quests not available

        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        engine.declare_allegiance("crew", "HEARTH")
        engine.end_day()

        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data, world_state=ws)

        assert restored.day == engine.day
        assert restored.sway == engine.sway
        assert restored.arc_length == quest.arc_length
        assert restored.terms == engine.terms

    def test_used_dilemmas_persist(self):
        """_used_dilemmas list persists through serialization."""
        engine = CrownAndCrewEngine()
        engine.get_council_dilemma()
        engine.get_council_dilemma()
        assert len(engine._used_dilemmas) == 2

        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._used_dilemmas == engine._used_dilemmas

    def test_rest_config_persists(self):
        """rest_config dict persists through serialization."""
        engine = CrownAndCrewEngine()
        engine.rest_config["sway_decay_on_skip"] = 2
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored.rest_config["sway_decay_on_skip"] == 2

    def test_arc_length_from_world_state(self):
        """arc_length injected via world_state is respected."""
        ws = {"arc_length": 7}
        engine = CrownAndCrewEngine(world_state=ws)
        assert engine.arc_length == 7

    def test_rest_config_from_world_state(self):
        """rest_config injected via world_state merges correctly."""
        ws = {"rest_config": {"breach_day_fraction": 0.5}}
        engine = CrownAndCrewEngine(world_state=ws)
        assert engine.rest_config["breach_day_fraction"] == 0.5
        # Other defaults should still be present
        assert "sway_decay_on_skip" in engine.rest_config


# =============================================================================
# MENU PARITY TESTS
# =============================================================================

class TestMenuParity:
    """Verify BOT_OPTIONS matches the expected 9-entry layout."""

    def test_bot_options_has_9_entries(self):
        """BOT_OPTIONS should have exactly 9 entries."""
        menu = CodexMenu()
        bot_menu = menu.get_menu("discord")
        assert len(bot_menu.options) == 9

    def test_all_bot_actions_exist(self):
        """All expected action strings are present in BOT_OPTIONS."""
        menu = CodexMenu()
        bot_menu = menu.get_menu("discord")
        actions = {opt.action for opt in bot_menu.options}

        expected = {
            "play_crown", "play_prologue", "play_quest", "play_ashburn",
            "play_burnwillow", "launch_omni_forge", "play_dnd5e",
            "play_cosmere", "end_session",
        }
        assert expected == actions, f"Missing: {expected - actions}, Extra: {actions - expected}"

    def test_terminal_and_bot_share_burnwillow(self):
        """Both menus include play_burnwillow."""
        menu = CodexMenu()
        terminal = menu.get_menu("terminal")
        bot = menu.get_menu("discord")

        terminal_actions = {opt.action for opt in terminal.options}
        bot_actions = {opt.action for opt in bot.options}

        assert "play_burnwillow" in terminal_actions
        assert "play_burnwillow" in bot_actions

    def test_terminal_and_bot_share_crown(self):
        """Terminal has play_crown, bot has play_crown."""
        menu = CodexMenu()
        terminal = menu.get_menu("terminal")
        bot = menu.get_menu("discord")

        terminal_actions = {opt.action for opt in terminal.options}
        bot_actions = {opt.action for opt in bot.options}

        assert "play_crown" in terminal_actions
        assert "play_crown" in bot_actions

    def test_bot_footer_mentions_9(self):
        """Bot menu footer references 1-9."""
        menu = CodexMenu()
        bot_menu = menu.get_menu("discord")
        assert "1-9" in bot_menu.footer


# =============================================================================
# QUEST INJECTION TESTS
# =============================================================================

class TestQuestInjection:
    """Verify quest archetypes inject correctly into engine."""

    def test_quest_arc_length_persists_through_serialization(self):
        """Quest arc_length survives to_dict() -> from_dict()."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return

        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        assert engine.arc_length == quest.arc_length

        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data, world_state=ws)
        assert restored.arc_length == quest.arc_length

    def test_quest_rest_config_persists_through_serialization(self):
        """Quest rest_config survives serialization."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return

        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws)

        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data, world_state=ws)
        assert restored.rest_config == engine.rest_config

    def test_quest_terms_override_defaults(self):
        """Quest terms replace default Crown/Crew terminology."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return

        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        # Siege quest should have different terms than default
        assert engine.terms == quest.terms

    def test_quest_council_dilemmas_injected(self):
        """Quest's council_dilemmas are used instead of defaults."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return

        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        # Engine should have quest's dilemmas, not default 8
        assert len(engine._council_dilemmas) == len(quest.council_dilemmas)


# =============================================================================
# CROSS-PLATFORM SESSION VERIFICATION
# =============================================================================

class TestCrossPlatformSession:
    """Verify serialized state can reconstruct sessions for any platform."""

    def test_serialized_state_has_all_keys(self):
        """to_dict() output contains all keys needed for session reconstruction."""
        engine = CrownAndCrewEngine(arc_length=7)
        engine.declare_allegiance("crew", "HEARTH")
        engine.end_day()

        data = engine.to_dict()
        required_keys = {
            "day", "sway", "patron", "leader", "history", "dna",
            "arc_length", "rest_type", "rest_config", "terms",
            "_used_dilemmas", "_council_dilemmas",
            "quest_slug", "quest_name", "special_mechanics",
            "_morning_events", "_short_rests_today",
        }
        assert required_keys.issubset(set(data.keys())), \
            f"Missing keys: {required_keys - set(data.keys())}"

    def test_from_dict_produces_identical_state(self):
        """from_dict() produces engine with identical gameplay state."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return

        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        engine.declare_allegiance("crown", "GUILE")
        engine.end_day()
        engine.get_council_dilemma()

        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data, world_state=ws)

        assert restored.day == engine.day
        assert restored.sway == engine.sway
        assert restored.arc_length == engine.arc_length
        assert restored.rest_config == engine.rest_config
        assert restored.terms == engine.terms
        assert restored._used_dilemmas == engine._used_dilemmas
        assert restored.patron == engine.patron
        assert restored.leader == engine.leader

    def test_engine_get_council_dilemma_works(self):
        """get_council_dilemma() returns valid dict with required keys."""
        engine = CrownAndCrewEngine()
        dilemma = engine.get_council_dilemma()
        assert "prompt" in dilemma
        assert "crown" in dilemma
        assert "crew" in dilemma

    def test_rest_mechanics(self):
        """All three rest types work correctly."""
        engine = CrownAndCrewEngine()
        engine.sway = 2

        # Skip rest — sway decays
        msg = engine.skip_rest()
        assert engine.sway == 1
        assert "Sway" in msg

        # Short rest — day stays same
        engine.sway = 0
        engine.trigger_short_rest()
        assert engine.day == 1

        # Long rest — day advances
        engine.trigger_long_rest()
        assert engine.day == 2

    def test_breach_day_scales_with_arc_length(self):
        """is_breach_day() returns True on the correct day for any arc_length."""
        for arc in (5, 7, 10):
            engine = CrownAndCrewEngine(arc_length=arc)
            breach = max(1, round(arc * 0.6))
            engine.day = breach
            assert engine.is_breach_day(), f"arc={arc}, breach={breach}"
            engine.day = breach + 1
            assert not engine.is_breach_day()


# =============================================================================
# WO-V25.0: HIGH-05 — SERIALIZATION GAP TESTS
# =============================================================================

class TestHighPrioritySerializationGaps:
    """HIGH-05: Verify council_dilemmas, quest identity survive serialization."""

    def test_council_dilemmas_persist(self):
        """_council_dilemmas survive serialization (HIGH-05)."""
        engine = CrownAndCrewEngine()
        data = engine.to_dict()
        assert "_council_dilemmas" in data
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._council_dilemmas == engine._council_dilemmas

    def test_quest_metadata_persists(self):
        """quest_slug, quest_name survive serialization (HIGH-05)."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return
        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored.quest_slug == engine.quest_slug
        assert restored.quest_name == engine.quest_name

    def test_quest_slug_default_empty(self):
        """Default engine has empty quest_slug and quest_name."""
        engine = CrownAndCrewEngine()
        assert engine.quest_slug == ""
        assert engine.quest_name == ""
        data = engine.to_dict()
        assert data["quest_slug"] == ""
        assert data["quest_name"] == ""

    def test_special_mechanics_persist(self):
        """special_mechanics dict survives serialization."""
        ws = {"special_mechanics": {"siege_defense": True, "morale_bonus": 2}}
        engine = CrownAndCrewEngine(world_state=ws)
        assert engine.special_mechanics == {"siege_defense": True, "morale_bonus": 2}
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored.special_mechanics == engine.special_mechanics


# =============================================================================
# WO-V25.0: MED-01 — MORNING EVENTS TESTS
# =============================================================================

class TestMorningEventsInjection:
    """MED-01: Verify quest morning events override defaults."""

    def test_morning_events_from_quest(self):
        """Quest morning events override defaults (MED-01)."""
        try:
            from codex.games.crown.quests import get_quest
        except ImportError:
            return
        quest = get_quest("siege")
        if quest is None:
            return
        ws = quest.to_world_state()
        if not ws.get("morning_events"):
            return  # Quest doesn't define custom morning events
        engine = CrownAndCrewEngine(world_state=ws)
        from codex.games.crown.engine import MORNING_EVENTS
        assert engine._morning_events != MORNING_EVENTS

    def test_morning_events_default_fallback(self):
        """Default engine uses module-level MORNING_EVENTS."""
        from codex.games.crown.engine import MORNING_EVENTS
        engine = CrownAndCrewEngine()
        assert len(engine._morning_events) == len(MORNING_EVENTS)

    def test_morning_events_persist(self):
        """_morning_events survive serialization."""
        engine = CrownAndCrewEngine()
        data = engine.to_dict()
        assert "_morning_events" in data
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._morning_events == engine._morning_events

    def test_custom_morning_events_injected(self):
        """Custom morning events from world_state are used."""
        custom_events = [
            {"text": "Siege engines rumble in the distance.", "bias": "crown", "tag": "BLOOD"},
            {"text": "Defenders share rations at the wall.", "bias": "crew", "tag": "HEARTH"},
            {"text": "The sun rises over a battered city.", "bias": "neutral", "tag": "SILENCE"},
        ]
        ws = {"morning_events": custom_events}
        engine = CrownAndCrewEngine(world_state=ws)
        assert len(engine._morning_events) == 3
        assert engine._morning_events[0]["text"] == "Siege engines rumble in the distance."


# =============================================================================
# WO-V25.0: MED-06 — SHORT REST COUNTER TESTS
# =============================================================================

class TestShortRestCounter:
    """MED-06: Verify short rest limited to 1 per day."""

    def test_short_rest_counter(self):
        """Short rest limited to 1 per day (MED-06)."""
        engine = CrownAndCrewEngine()
        result1 = engine.trigger_short_rest()
        assert "Short rest:" in result1
        result2 = engine.trigger_short_rest()
        assert "already" in result2.lower()
        engine.end_day()  # Reset counter
        result3 = engine.trigger_short_rest()
        assert "Short rest:" in result3

    def test_short_rest_counter_resets_on_long_rest(self):
        """Long rest (end_day) resets short rest counter."""
        engine = CrownAndCrewEngine()
        engine.trigger_short_rest()
        assert engine._short_rests_today == 1
        engine.trigger_long_rest()  # calls end_day internally
        assert engine._short_rests_today == 0

    def test_short_rest_counter_persists(self):
        """_short_rests_today survives serialization."""
        engine = CrownAndCrewEngine()
        engine.trigger_short_rest()
        data = engine.to_dict()
        assert data["_short_rests_today"] == 1
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._short_rests_today == 1

    def test_configurable_max_short_rests(self):
        """max_short_rests_per_day from rest_config is respected."""
        engine = CrownAndCrewEngine()
        engine.rest_config["max_short_rests_per_day"] = 3
        engine.trigger_short_rest()
        engine.trigger_short_rest()
        result = engine.trigger_short_rest()
        assert "Short rest:" in result
        result = engine.trigger_short_rest()
        assert "already" in result.lower()


# =============================================================================
# WO-V25.0: MED-04 — TAROT TEXT RENDERER TESTS
# =============================================================================

class TestTarotTextRenderer:
    """MED-04: Verify text-only tarot renderer for bots."""

    def test_format_tarot_text_returns_string(self):
        """format_tarot_text produces a string, not a Rich Panel."""
        from codex.integrations.tarot import format_tarot_text
        result = format_tarot_text("wolf", "Test prompt")
        assert isinstance(result, str)
        assert "THE WOLF" in result

    def test_format_tarot_text_unknown_key(self):
        """Unknown card key returns plain prompt text."""
        from codex.integrations.tarot import format_tarot_text
        result = format_tarot_text("nonexistent", "Hello")
        assert result == "Hello"

    def test_format_tarot_text_all_cards(self):
        """All 5 card keys produce valid output."""
        from codex.integrations.tarot import format_tarot_text, TAROT_CARDS
        for key in TAROT_CARDS:
            result = format_tarot_text(key, "Test")
            assert isinstance(result, str)
            assert len(result) > 10
            assert "╔" in result  # Has box drawing

    def test_format_tarot_text_contains_prompt(self):
        """Output contains the prompt text."""
        from codex.integrations.tarot import format_tarot_text
        result = format_tarot_text("moon", "The border looms ahead")
        assert "border" in result.lower()

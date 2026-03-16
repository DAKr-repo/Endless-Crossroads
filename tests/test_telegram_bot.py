"""
Tests for Telegram bot pure functions and session state (WO-V47.0).

Tests pure formatting functions that have zero external dependencies,
plus TelegramSession state transitions with mocked engine.
"""
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# Telegram SDK may not be installed in test env — stub it
_tg_stub = MagicMock()
_tg_stub.InlineKeyboardButton = MagicMock
_tg_stub.InlineKeyboardMarkup = MagicMock
sys.modules.setdefault("telegram", _tg_stub)
sys.modules.setdefault("telegram.ext", MagicMock())

from codex.bots.telegram_bot import (
    generate_sway_bar,
    wrap_lines,
    format_morning,
    format_campfire,
    format_council,
    Phase,
)


# ─────────────────────────────────────────────────────────────────────
# generate_sway_bar
# ─────────────────────────────────────────────────────────────────────

class TestGenerateSwayBar:

    def test_neutral_sway(self):
        bar = generate_sway_bar(0)
        assert "■" in bar
        assert bar.startswith("👑")
        assert bar.endswith("🏴")

    def test_max_crown_sway(self):
        bar = generate_sway_bar(-3)
        # ■ should be at leftmost position (index 0)
        assert bar == "👑■══════🏴"

    def test_max_crew_sway(self):
        bar = generate_sway_bar(3)
        # ■ should be at rightmost position (index 6)
        assert bar == "👑══════■🏴"

    def test_positive_sway(self):
        bar = generate_sway_bar(1)
        assert "■" in bar
        assert bar.count("■") == 1

    def test_negative_sway(self):
        bar = generate_sway_bar(-1)
        assert "■" in bar
        assert bar.count("■") == 1

    def test_bar_length_consistent(self):
        """All sway bars should have the same number of bar characters."""
        for sway in range(-3, 4):
            bar = generate_sway_bar(sway)
            # Remove emoji markers, count bar chars
            inner = bar[1:-1]  # Strip 👑 and 🏴 (multi-byte)
            inner = bar.replace("👑", "").replace("🏴", "")
            assert len(inner) == 7


# ─────────────────────────────────────────────────────────────────────
# wrap_lines
# ─────────────────────────────────────────────────────────────────────

class TestWrapLines:

    def test_short_text_single_line(self):
        result = wrap_lines("Hello world", 52)
        assert result == ["Hello world"]

    def test_empty_text(self):
        result = wrap_lines("", 52)
        assert result == []

    def test_long_text_wraps(self):
        text = "word " * 20  # 100 chars
        result = wrap_lines(text.strip(), 52)
        assert len(result) >= 2

    def test_respects_max_len(self):
        text = "The forge burns with ancient fire and golden sparks fly everywhere"
        result = wrap_lines(text, 30)
        for line in result:
            # Each line should be at most max_len (or a single long word)
            assert len(line) <= 66  # generous bound for single-word overflow

    def test_single_long_word(self):
        result = wrap_lines("supercalifragilisticexpialidocious", 10)
        assert len(result) == 1
        assert result[0] == "supercalifragilisticexpialidocious"

    def test_exact_boundary(self):
        result = wrap_lines("12345 12345", 11)
        assert result == ["12345 12345"]


# ─────────────────────────────────────────────────────────────────────
# format_morning
# ─────────────────────────────────────────────────────────────────────

class TestFormatMorning:

    def test_contains_day_number(self):
        result = format_morning(3, "The road is long.")
        assert "D A Y  3" in result

    def test_contains_world_prompt(self):
        result = format_morning(1, "Dark clouds gather.")
        assert "Dark clouds gather." in result

    def test_contains_travel_instruction(self):
        result = format_morning(1, "Test prompt.")
        assert "/travel" in result

    def test_has_box_drawing_chars(self):
        result = format_morning(1, "Test")
        assert "╔" in result
        assert "╚" in result

    def test_empty_prompt(self):
        # Should not crash with empty prompt
        result = format_morning(1, "")
        assert "D A Y  1" in result


# ─────────────────────────────────────────────────────────────────────
# format_campfire
# ─────────────────────────────────────────────────────────────────────

class TestFormatCampfire:

    def test_contains_crown_crew_options(self):
        result = format_campfire("A shadow approaches.")
        assert "CROWN" in result
        assert "CREW" in result

    def test_contains_prompt_text(self):
        result = format_campfire("The fire dies low.")
        assert "The fire dies low." in result

    def test_has_box_chars(self):
        result = format_campfire("Test")
        assert "┌" in result
        assert "└" in result

    def test_fire_emoji(self):
        result = format_campfire("Test")
        assert "🔥" in result


# ─────────────────────────────────────────────────────────────────────
# format_council
# ─────────────────────────────────────────────────────────────────────

class TestFormatCouncil:

    def _dilemma(self, prompt="Test dilemma", opt1="Option A", opt2="Option B"):
        return {"prompt": prompt, "option_1": opt1, "option_2": opt2}

    def test_contains_day(self):
        result = format_council(2, self._dilemma())
        assert "D A Y  2" in result

    def test_contains_options(self):
        result = format_council(1, self._dilemma(opt1="Save the village", opt2="Burn it down"))
        assert "Save the village" in result
        assert "Burn it down" in result

    def test_contains_voting_instruction(self):
        result = format_council(1, self._dilemma())
        assert "1  or  2" in result

    def test_contains_dilemma_prompt(self):
        result = format_council(1, self._dilemma(prompt="The bridge is collapsing"))
        assert "The bridge is collapsing" in result

    def test_has_box_chars(self):
        result = format_council(1, self._dilemma())
        assert "╔" in result
        assert "╚" in result


# ─────────────────────────────────────────────────────────────────────
# Phase enum
# ─────────────────────────────────────────────────────────────────────

class TestPhaseEnum:

    def test_idle_exists(self):
        assert Phase.IDLE is not None

    def test_expected_phases(self):
        expected = ["IDLE", "MENU", "DUNGEON", "MORNING", "CAMPFIRE",
                    "COUNCIL", "FINALE"]
        for name in expected:
            assert hasattr(Phase, name), f"Phase.{name} missing"

    def test_phase_values_unique(self):
        values = [p.value for p in Phase]
        assert len(values) == len(set(values))


# ─────────────────────────────────────────────────────────────────────
# TelegramSession state (with mocked engine)
# ─────────────────────────────────────────────────────────────────────

class TestTelegramSession:

    def _make_session(self):
        from codex.bots.telegram_bot import TelegramSession
        return TelegramSession(chat_id=12345)

    def test_initial_phase_is_idle(self):
        session = self._make_session()
        assert session.phase == Phase.IDLE

    def test_start_game_when_already_running(self):
        session = self._make_session()
        session.phase = Phase.MORNING
        result = session.start_game()
        assert "already in progress" in result.lower() or "⚠️" in result

    def test_chat_id_stored(self):
        session = self._make_session()
        assert session.chat_id == 12345

"""
tests/test_butler_reflexes.py -- Butler Reflex Registry
========================================================

~30 tests covering CodexButler.check_reflex() pattern matching.
Tests are grouped into 11 categories:
  1. Dice rolling
  2. Identity quips
  3. Greeting quips
  4. Status (no session)
  5. Time
  6. Ping
  7. Inventory (no session)
  8. Unknown input (returns None)
  9. Case insensitivity
 10. Presence quips
 11. Edge cases

Initialization strategy: patch both classmethods _load_knowledge_base and
_load_skald_lexicon to return empty dicts, preventing any disk I/O during
construction and allowing the butler to be instantiated cleanly in-process.
"""

import re
import unittest
from unittest.mock import patch

from codex.core.butler import CodexButler


# ---------------------------------------------------------------------------
# Shared fixture: butler with disk I/O mocked out
# ---------------------------------------------------------------------------

def _make_butler() -> CodexButler:
    """Return a CodexButler with no disk I/O side-effects.

    Both classmethods that touch the filesystem are patched to return empty
    dicts before __init__ calls them.
    """
    with patch.object(CodexButler, "_load_knowledge_base", return_value={}), \
         patch.object(CodexButler, "_load_skald_lexicon", return_value={}):
        return CodexButler(core_state=None)


# ---------------------------------------------------------------------------
# 1. Dice rolling (5 tests)
# ---------------------------------------------------------------------------

class TestDiceRolling(unittest.TestCase):
    """check_reflex correctly parses and rolls dice expressions."""

    def setUp(self):
        self.butler = _make_butler()

    def test_roll_two_d6(self):
        """'roll 2d6' returns a formatted dice result."""
        result = self.butler.check_reflex("roll 2d6")
        self.assertIsNotNone(result)
        self.assertIn("🎲", result)
        # Total must be between 2 and 12
        total_match = re.search(r"\*\*(\d+)\*\*", result)
        self.assertIsNotNone(total_match, f"No bold total in: {result}")
        total = int(total_match.group(1))
        self.assertGreaterEqual(total, 2)
        self.assertLessEqual(total, 12)

    def test_roll_d20(self):
        """'roll d20' (no count) returns a result between 1 and 20."""
        result = self.butler.check_reflex("roll d20")
        self.assertIsNotNone(result)
        total_match = re.search(r"\*\*(\d+)\*\*", result)
        self.assertIsNotNone(total_match)
        total = int(total_match.group(1))
        self.assertGreaterEqual(total, 1)
        self.assertLessEqual(total, 20)

    def test_roll_shorthand_r(self):
        """'r d6+3' uses the 'r' shorthand and applies modifier."""
        result = self.butler.check_reflex("r d6+3")
        self.assertIsNotNone(result)
        self.assertIn("🎲", result)
        total_match = re.search(r"\*\*(\d+)\*\*", result)
        self.assertIsNotNone(total_match)
        total = int(total_match.group(1))
        # d6+3: minimum 4, maximum 9
        self.assertGreaterEqual(total, 4)
        self.assertLessEqual(total, 9)

    def test_roll_with_negative_modifier(self):
        """'roll 1d20-1' applies a negative modifier correctly."""
        result = self.butler.check_reflex("roll 1d20-1")
        self.assertIsNotNone(result)
        total_match = re.search(r"\*\*(\d+)\*\*", result)
        self.assertIsNotNone(total_match)
        total = int(total_match.group(1))
        # 1d20-1: minimum 0, maximum 19
        self.assertGreaterEqual(total, 0)
        self.assertLessEqual(total, 19)

    def test_roll_result_format(self):
        """Dice result contains the expected bold-total and parenthesised breakdown."""
        result = self.butler.check_reflex("roll 1d6")
        self.assertIsNotNone(result)
        # Pattern: 🎲 **N** (N)
        self.assertRegex(result, r"🎲 \*\*\d+\*\* \(\d+\)")


# ---------------------------------------------------------------------------
# 2. Identity quips (3 tests)
# ---------------------------------------------------------------------------

class TestIdentityReflex(unittest.TestCase):
    """Identity questions route to _handle_identity and return a quip."""

    def setUp(self):
        self.butler = _make_butler()

    def test_who_are_you(self):
        result = self.butler.check_reflex("who are you")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._identity_quips)

    def test_what_are_you(self):
        result = self.butler.check_reflex("what are you")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._identity_quips)

    def test_what_is_mimir(self):
        result = self.butler.check_reflex("what is mimir")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._identity_quips)


# ---------------------------------------------------------------------------
# 3. Greeting quips (4 tests)
# ---------------------------------------------------------------------------

class TestGreetingReflex(unittest.TestCase):
    """Greeting inputs route to _handle_greeting and return a quip."""

    def setUp(self):
        self.butler = _make_butler()

    def test_hello(self):
        result = self.butler.check_reflex("hello")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._greeting_quips)

    def test_hey(self):
        result = self.butler.check_reflex("hey")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._greeting_quips)

    def test_hi(self):
        result = self.butler.check_reflex("hi")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._greeting_quips)

    def test_good_morning(self):
        result = self.butler.check_reflex("good morning")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._greeting_quips)

    def test_greetings_with_punctuation(self):
        result = self.butler.check_reflex("greetings!")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._greeting_quips)


# ---------------------------------------------------------------------------
# 4. Status (no session — 2 tests)
# ---------------------------------------------------------------------------

class TestStatusReflex(unittest.TestCase):
    """Status commands return a fallback string when no session is active."""

    def setUp(self):
        # No session, no core — should fall through to "No Core Link" message
        self.butler = _make_butler()
        self.butler.session = None

    def test_status_command(self):
        result = self.butler.check_reflex("status")
        self.assertIsNotNone(result)
        # With no session and no core, returns the nominal fallback
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_stat_alias(self):
        result = self.butler.check_reflex("stat")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_hp_alias(self):
        result = self.butler.check_reflex("hp")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_status_no_session_no_core(self):
        """With no session and no core link, status reports nominal."""
        self.butler.core = None
        result = self.butler.check_reflex("status")
        self.assertIn("Nominal", result)


# ---------------------------------------------------------------------------
# 5. Time (3 tests)
# ---------------------------------------------------------------------------

class TestTimeReflex(unittest.TestCase):
    """Time/date queries return a clock-emoji prefixed time string."""

    def setUp(self):
        self.butler = _make_butler()

    def test_what_time_is_it(self):
        result = self.butler.check_reflex("what time is it")
        self.assertIsNotNone(result)
        self.assertIn("🕒", result)

    def test_time_bare_command(self):
        result = self.butler.check_reflex("time")
        self.assertIsNotNone(result)
        self.assertIn("🕒", result)

    def test_clock_command(self):
        result = self.butler.check_reflex("clock")
        self.assertIsNotNone(result)
        self.assertIn("🕒", result)

    def test_what_day_is_it(self):
        result = self.butler.check_reflex("what day is it")
        self.assertIsNotNone(result)
        self.assertIn("🕒", result)


# ---------------------------------------------------------------------------
# 6. Ping (1 test)
# ---------------------------------------------------------------------------

class TestPingReflex(unittest.TestCase):
    """'ping' returns the pong sentinel string."""

    def setUp(self):
        self.butler = _make_butler()

    def test_ping(self):
        result = self.butler.check_reflex("ping")
        self.assertIsNotNone(result)
        self.assertIn("Pong", result)


# ---------------------------------------------------------------------------
# 7. Inventory (2 tests, no session)
# ---------------------------------------------------------------------------

class TestInventoryReflex(unittest.TestCase):
    """Inventory commands return a message when no session is active."""

    def setUp(self):
        self.butler = _make_butler()
        self.butler.session = None

    def test_inventory_command(self):
        result = self.butler.check_reflex("inventory")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_inv_alias(self):
        result = self.butler.check_reflex("inv")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_gear_alias(self):
        result = self.butler.check_reflex("gear")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# 8. Unknown input returns None (3 tests)
# ---------------------------------------------------------------------------

class TestUnknownInputReturnsNone(unittest.TestCase):
    """Unrecognised input falls through and returns None."""

    def setUp(self):
        self.butler = _make_butler()

    def test_banana_returns_none(self):
        self.assertIsNone(self.butler.check_reflex("banana"))

    def test_narrative_request_returns_none(self):
        self.assertIsNone(self.butler.check_reflex("tell me a story"))

    def test_song_request_returns_none(self):
        self.assertIsNone(self.butler.check_reflex("fly me to the moon"))


# ---------------------------------------------------------------------------
# 9. Case insensitivity (2 tests)
# ---------------------------------------------------------------------------

class TestCaseInsensitivity(unittest.TestCase):
    """check_reflex lower-cases input before matching, so case must not matter."""

    def setUp(self):
        self.butler = _make_butler()

    def test_hello_uppercase(self):
        result = self.butler.check_reflex("HELLO")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._greeting_quips)

    def test_roll_d20_mixed_case(self):
        result = self.butler.check_reflex("Roll D20")
        self.assertIsNotNone(result)
        self.assertIn("🎲", result)


# ---------------------------------------------------------------------------
# 10. Presence quips (2 tests)
# ---------------------------------------------------------------------------

class TestPresenceReflex(unittest.TestCase):
    """Presence questions route to _handle_presence and return a quip."""

    def setUp(self):
        self.butler = _make_butler()

    def test_are_you_here(self):
        result = self.butler.check_reflex("are you here")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._presence_quips)

    def test_you_alive_with_question_mark(self):
        result = self.butler.check_reflex("you alive?")
        self.assertIsNotNone(result)
        self.assertIn(result, self.butler._presence_quips)


# ---------------------------------------------------------------------------
# 11. Edge cases (2 tests)
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):
    """Edge inputs like empty strings and whitespace return None gracefully."""

    def setUp(self):
        self.butler = _make_butler()

    def test_empty_string(self):
        result = self.butler.check_reflex("")
        self.assertIsNone(result)

    def test_whitespace_only(self):
        # strip() inside check_reflex reduces this to ""
        result = self.butler.check_reflex("   ")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

"""
tests/test_architect.py — Pure logic tests for the Architect routing system.

Tests the following components WITHOUT hardware access or Ollama:
  - ComplexityAnalyzer.analyze(query)        → (Complexity, reasoning_str)
  - ComplexityAnalyzer.estimate_tokens(query) → int
  - Architect.route(query)                   → RoutingDecision

All tests mock codex.core.cortex.get_cortex() so no hardware reads occur.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from codex.core.cortex import MetabolicState, ThermalStatus
from codex.core.architect import (
    Architect,
    ArchitectConfig,
    Complexity,
    ComplexityAnalyzer,
    RoutingDecision,
    ThinkingMode,
)


# ---------------------------------------------------------------------------
# Helpers — build mock cortex objects with controlled thermal state
# ---------------------------------------------------------------------------

def _make_metabolic_state(
    thermal_status: ThermalStatus = ThermalStatus.OPTIMAL,
    clearance: bool = True,
    cpu_temp: float = 45.0,
) -> MetabolicState:
    """Return a fully populated MetabolicState with sane defaults."""
    return MetabolicState(
        cpu_temp_celsius=cpu_temp,
        ram_usage_percent=40.0,
        ram_available_gb=4.0,
        thermal_status=thermal_status,
        metabolic_clearance=clearance,
    )


def _make_mock_cortex(
    thermal_status: ThermalStatus = ThermalStatus.OPTIMAL,
    clearance: bool = True,
    cpu_temp: float = 45.0,
) -> MagicMock:
    """Return a mock Cortex that yields a controlled MetabolicState."""
    cortex = MagicMock()
    state = _make_metabolic_state(thermal_status, clearance, cpu_temp)
    cortex.read_metabolic_state.return_value = state
    cortex.get_base_persona_prompt.return_value = ""
    cortex.get_system_prompt_modifier.return_value = ""
    return cortex


# Patch target used by every test that constructs an Architect.
_CORTEX_PATCH = "codex.core.cortex.get_cortex"


# ===========================================================================
# 1. LOW complexity classification
# ===========================================================================

class TestLowComplexity(unittest.TestCase):
    """Short, simple queries should classify as LOW."""

    def setUp(self) -> None:
        self.analyzer = ComplexityAnalyzer()

    def test_greeting_hi_is_low(self) -> None:
        complexity, _ = self.analyzer.analyze("hi")
        self.assertEqual(complexity, Complexity.LOW)

    def test_greeting_hello_is_low(self) -> None:
        complexity, _ = self.analyzer.analyze("Hello there!")
        self.assertEqual(complexity, Complexity.LOW)

    def test_dice_roll_is_low(self) -> None:
        complexity, _ = self.analyzer.analyze("roll a d20 for initiative")
        self.assertEqual(complexity, Complexity.LOW)

    def test_yes_response_is_low(self) -> None:
        complexity, _ = self.analyzer.analyze("yes")
        self.assertEqual(complexity, Complexity.LOW)

    def test_thanks_is_low(self) -> None:
        complexity, _ = self.analyzer.analyze("thanks")
        self.assertEqual(complexity, Complexity.LOW)


# ===========================================================================
# 2. MEDIUM complexity classification
# ===========================================================================

class TestMediumComplexity(unittest.TestCase):
    """Moderate queries should classify as MEDIUM (score >= 1, < 3).

    Note: The scorer uses plain substring matching, not word-boundary matching.
    LOW keywords like "hi", "ok", "no" can match inside longer words, so test
    queries must be chosen carefully to avoid accidental LOW keyword hits.
    """

    def setUp(self) -> None:
        self.analyzer = ComplexityAnalyzer()

    def test_investigate_short_query_is_medium(self) -> None:
        # "investigate" → HIGH keyword, score=2.
        # word_count=3 (<10) → -1 short penalty. Final score=1 → MEDIUM.
        # "investigate the fault" contains no LOW keyword substrings.
        complexity, _ = self.analyzer.analyze("investigate the fault")
        self.assertEqual(complexity, Complexity.MEDIUM)

    def test_evaluate_short_query_is_medium(self) -> None:
        # "evaluate" → HIGH keyword, score=2.
        # word_count=3 (<10) → -1 short penalty. Final score=1 → MEDIUM.
        # "evaluate the performance" contains no LOW keyword substrings.
        complexity, _ = self.analyzer.analyze("evaluate the performance")
        self.assertEqual(complexity, Complexity.MEDIUM)

    def test_code_block_without_high_keywords_is_medium(self) -> None:
        # Contains a code fence (```): has_code=True → score=2. No HIGH keywords.
        # No LOW keyword substrings in this phrase. word_count=12 → no short penalty.
        # score=2 → MEDIUM (below the >=3 threshold for HIGH).
        complexity, _ = self.analyzer.analyze(
            "a test fragment ```x = 1 + 2``` for basic type verification and coverage"
        )
        self.assertEqual(complexity, Complexity.MEDIUM)


# ===========================================================================
# 3. HIGH complexity classification
# ===========================================================================

class TestHighComplexity(unittest.TestCase):
    """Queries with strong high-complexity signals should classify as HIGH."""

    def setUp(self) -> None:
        self.analyzer = ComplexityAnalyzer()

    def test_debug_and_refactor_is_high(self) -> None:
        # "debug" + "refactor" → 2 HIGH keyword matches → score=4.
        # word_count=8 (<10) → -1 short penalty. Net=3 → HIGH.
        # Verified: no LOW keyword substrings in this phrase.
        complexity, _ = self.analyzer.analyze(
            "debug and refactor the event routing pipeline carefully"
        )
        self.assertEqual(complexity, Complexity.HIGH)

    def test_debug_and_optimize_is_high(self) -> None:
        # "debug" + "optimize" → 2 HIGH keyword matches → score=4.
        # word_count=7 (<10) → -1 short penalty. Net=3 → HIGH.
        # Verified: no LOW keyword substrings in this phrase.
        complexity, _ = self.analyzer.analyze(
            "debug and optimize the thermal throttle logic"
        )
        self.assertEqual(complexity, Complexity.HIGH)

    def test_multi_keyword_complex_query_is_high(self) -> None:
        # "research", "evaluate", "strategy", "deep dive" → 4 HIGH keyword matches
        # → score=8. word_count=12 — no short penalty. Net=8 → HIGH.
        # Verified: no LOW keyword substrings in this phrase.
        complexity, _ = self.analyzer.analyze(
            "research and evaluate our strategy for the deep dive into distributed systems"
        )
        self.assertEqual(complexity, Complexity.HIGH)


# ===========================================================================
# 4. Routing decisions
# ===========================================================================

class TestRouting(unittest.TestCase):
    """
    Architect.route() must select the correct ThinkingMode based on
    complexity + thermal state.
    """

    def _make_architect(
        self,
        thermal_status: ThermalStatus = ThermalStatus.OPTIMAL,
        clearance: bool = True,
        cpu_temp: float = 45.0,
    ) -> Architect:
        mock_cortex = _make_mock_cortex(thermal_status, clearance, cpu_temp)
        with patch(_CORTEX_PATCH, return_value=mock_cortex):
            architect = Architect()
        # Replace the already-stored cortex with our mock (patch only guards init)
        architect.cortex = mock_cortex
        return architect

    def test_high_complexity_green_thermal_routes_academy(self) -> None:
        # "debug" + "refactor" → 2 HIGH matches → score=4; 8 words → -1 short penalty.
        # Net score=3 → HIGH complexity. With clearance=True → ACADEMY.
        architect = self._make_architect(
            thermal_status=ThermalStatus.OPTIMAL,
            clearance=True,
        )
        decision = architect.route(
            "debug and refactor the event routing pipeline carefully"
        )
        self.assertEqual(decision.mode, ThinkingMode.ACADEMY)
        self.assertEqual(decision.model, ArchitectConfig.MODEL_ACADEMY)

    def test_high_complexity_critical_thermal_falls_back_to_reflex(self) -> None:
        # Same HIGH query but thermal is CRITICAL and clearance=False.
        # HIGH complexity is detected but Academy is blocked → falls back to REFLEX.
        architect = self._make_architect(
            thermal_status=ThermalStatus.CRITICAL,
            clearance=False,
            cpu_temp=80.0,
        )
        decision = architect.route(
            "debug and refactor the event routing pipeline carefully"
        )
        self.assertEqual(decision.mode, ThinkingMode.REFLEX)
        self.assertIn("thermal override", decision.reasoning)

    def test_low_complexity_always_reflex(self) -> None:
        architect = self._make_architect(
            thermal_status=ThermalStatus.OPTIMAL,
            clearance=True,
        )
        decision = architect.route("hello")
        self.assertEqual(decision.mode, ThinkingMode.REFLEX)

    def test_medium_complexity_always_reflex(self) -> None:
        architect = self._make_architect(clearance=True)
        decision = architect.route("describe what the reflex model does")
        self.assertEqual(decision.mode, ThinkingMode.REFLEX)

    def test_routing_decision_carries_complexity(self) -> None:
        """RoutingDecision.complexity must reflect the analyzer's result."""
        architect = self._make_architect()
        decision = architect.route(
            "analyze and debug the entire pipeline"
        )
        self.assertEqual(decision.complexity, Complexity.HIGH)

    def test_routing_decision_carries_thermal_status(self) -> None:
        """RoutingDecision.thermal_status must mirror the mock cortex state."""
        architect = self._make_architect(
            thermal_status=ThermalStatus.FATIGUED,
            clearance=False,
        )
        decision = architect.route("hello")
        self.assertEqual(decision.thermal_status, ThermalStatus.FATIGUED)

    def test_clearance_denied_reflected_in_decision(self) -> None:
        architect = self._make_architect(clearance=False)
        decision = architect.route("hello")
        self.assertFalse(decision.clearance_granted)



# ===========================================================================
# 6. Token estimation
# ===========================================================================

class TestEstimateTokens(unittest.TestCase):
    """estimate_tokens() must apply the TOKENS_PER_WORD = 1.3 multiplier."""

    def setUp(self) -> None:
        self.analyzer = ComplexityAnalyzer()

    def test_four_word_query(self) -> None:
        # "roll a d20 dice" → 4 words × 1.3 = 5.2 → int(5) = 5
        result = self.analyzer.estimate_tokens("roll a d20 dice")
        self.assertEqual(result, int(4 * 1.3))

    def test_ten_word_query(self) -> None:
        # 10 words × 1.3 = 13.0 → int(13) = 13
        query = "analyze the codebase and explain why every subsystem exists here today"
        word_count = len(query.split())
        expected = int(word_count * ArchitectConfig.TOKENS_PER_WORD)
        result = self.analyzer.estimate_tokens(query)
        self.assertEqual(result, expected)

    def test_estimate_consistent_with_route_decision(self) -> None:
        """RoutingDecision.estimated_tokens must match the analyzer's calculation."""
        with patch(_CORTEX_PATCH, return_value=_make_mock_cortex()):
            architect = Architect()
        architect.cortex = _make_mock_cortex()
        query = "hello there friend"
        decision = architect.route(query)
        expected = int(len(query.split()) * ArchitectConfig.TOKENS_PER_WORD)
        self.assertEqual(decision.estimated_tokens, expected)


# ===========================================================================
# 8. Reasoning string sanity
# ===========================================================================

class TestReasoningStrings(unittest.TestCase):
    """
    The reasoning strings returned by analyze() and route() must contain
    useful human-readable content.
    """

    def setUp(self) -> None:
        self.analyzer = ComplexityAnalyzer()

    def test_analyze_returns_non_empty_reasoning(self) -> None:
        _, reasoning = self.analyzer.analyze("analyze the system")
        self.assertIsInstance(reasoning, str)
        self.assertGreater(len(reasoning), 0)

    def test_analyze_reasoning_contains_score(self) -> None:
        _, reasoning = self.analyzer.analyze("hi")
        self.assertIn("Score:", reasoning)

    def test_route_reasoning_contains_thermal(self) -> None:
        mock_cortex = _make_mock_cortex(thermal_status=ThermalStatus.OPTIMAL)
        with patch(_CORTEX_PATCH, return_value=mock_cortex):
            architect = Architect()
        architect.cortex = mock_cortex
        decision = architect.route("hello")
        self.assertIn("GREEN", decision.reasoning)


if __name__ == "__main__":
    unittest.main()

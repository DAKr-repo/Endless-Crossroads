"""
codex_architect.py - The Mind (Sovereign Trinity Router)

The Architect routes queries across the Sovereign Trinity:
  - Mimir (qwen2.5:0.5b)  — The Voice / Reflex & Narrator
  - Codex (qwen3:1.7b)    — The Philosopher / Academy (thermal-gated)
  - Experimental (qwen2.5-coder:1.5b) — The Experimenter (sandboxed, explicit only)

EXPERIMENTAL model is quarantined: never auto-routed during gameplay.
Only reachable via explicit !code command or direct API call.

This implements the core intelligence routing that makes C.O.D.E.X.
adaptive to both cognitive demands and physical constraints.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, AsyncIterator
import aiohttp

from codex.core.cortex import (
    get_cortex,
    check_metabolic_clearance,
    ThermalStatus,
    MetabolicState
)

SANDBOX_DIR = Path("/tmp/codex_sandbox")


class Complexity(Enum):
    """Query complexity classification."""
    LOW = "LOW"        # Simple, reflexive response
    MEDIUM = "MEDIUM"  # Moderate reasoning required
    HIGH = "HIGH"      # Deep analysis, recursive thought


class ThinkingMode(Enum):
    """Selected thinking mode for response."""
    REFLEX = "REFLEX"            # Fast path: mimir (qwen2.5:0.5b)
    ACADEMY = "ACADEMY"          # Deep path: codex (qwen3:1.7b, thermal-gated)
    EXPERIMENTAL = "EXPERIMENTAL"  # Sandboxed: qwen2.5-coder (explicit request only)


@dataclass
class RoutingDecision:
    """Result of the routing analysis."""
    mode: ThinkingMode
    model: str
    complexity: Complexity
    thermal_status: ThermalStatus
    clearance_granted: bool
    reasoning: str
    estimated_tokens: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ModelResponse:
    """Response from a model invocation."""
    content: str
    model: str
    mode: ThinkingMode
    thinking_trace: Optional[str] = None  # Academy model's <think> content
    tokens_used: int = 0
    latency_ms: float = 0
    thermal_at_start: float = 0
    thermal_at_end: float = 0


@dataclass
class LLMSessionStats:
    """Accumulated LLM usage stats for the current session."""
    total_calls: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0
    errors: int = 0
    last_model: str = ""
    last_latency_ms: float = 0
    last_mode: str = ""

    def record(self, response: "ModelResponse") -> None:
        """Accumulate stats from a completed ModelResponse."""
        self.total_calls += 1
        self.total_tokens += response.tokens_used or 0
        self.total_latency_ms += response.latency_ms or 0
        # Treat responses that start with a bracketed error tag as errors
        if response.content.startswith("[") and "error" in response.content.lower():
            self.errors += 1
        self.last_model = response.model or ""
        self.last_latency_ms = response.latency_ms or 0
        self.last_mode = response.mode.value if response.mode else ""

    @property
    def avg_latency_ms(self) -> float:
        """Average latency across all recorded calls."""
        return self.total_latency_ms / max(1, self.total_calls)


class ArchitectConfig:
    """Configuration for the Architect router."""

    # Ollama endpoint
    OLLAMA_HOST = "http://localhost:11434"

    # Sovereign Trinity — model identifiers
    MODEL_REFLEX = "mimir"              # The Voice — fast persona (qwen2.5:0.5b, 397MB)
    MODEL_ACADEMY = "codex"             # The Philosopher — deep reasoning (qwen3:1.7b, 1.4GB)
    MODEL_NARRATIVE = "mimir"           # The Narrator — persona & voice (qwen2.5:0.5b)
    MODEL_EXPERIMENTAL = "qwen2.5-coder:1.5b"  # The Experimenter — sandboxed, explicit request only

    # Sandbox for coder output
    SANDBOX_DIR = SANDBOX_DIR

    # Complexity thresholds
    COMPLEXITY_HIGH_KEYWORDS = [
        "analyze", "explain why", "compare", "evaluate", "design",
        "architect", "debug", "refactor", "optimize", "review",
        "understand", "investigate", "research", "plan", "strategy",
        "complex", "difficult", "challenging", "deep dive", "thorough"
    ]

    COMPLEXITY_LOW_KEYWORDS = [
        "roll", "dice", "d20", "d6", "random", "flip", "coin",
        "hello", "hi", "hey", "thanks", "thank you", "bye",
        "yes", "no", "ok", "okay", "sure", "help", "status",
        "what time", "how many", "list", "show", "tell me"
    ]

    COMPLEXITY_CODE_KEYWORDS = [
        "write code", "implement", "function", "class", "script",
        "generate code", "code review", "write a", "create a function",
        "write me", "code this", "program"
    ]

    # Token estimation (rough)
    TOKENS_PER_WORD = 1.3

    # Timeout settings (ms)
    REFLEX_TIMEOUT_MS = 120000        # 120 seconds
    ACADEMY_TIMEOUT_MS = 120000       # 120 seconds
    EXPERIMENTAL_TIMEOUT_MS = 120000  # 120 seconds


class ComplexityAnalyzer:
    """
    Analyzes query complexity to determine routing.

    Uses a combination of keyword matching, query length,
    and structural analysis to classify complexity.
    """

    def __init__(self, config: Optional[ArchitectConfig] = None):
        self.config = config or ArchitectConfig()

    def analyze(self, query: str) -> tuple[Complexity, str]:
        """
        Analyze query complexity.

        Returns:
            (Complexity level, reasoning string)
        """
        query_lower = query.lower()
        word_count = len(query.split())
        reasons = []

        # Check for high complexity indicators
        high_matches = [
            kw for kw in self.config.COMPLEXITY_HIGH_KEYWORDS
            if kw in query_lower
        ]
        if high_matches:
            reasons.append(f"High-complexity keywords: {high_matches[:3]}")

        # Check for low complexity indicators
        low_matches = [
            kw for kw in self.config.COMPLEXITY_LOW_KEYWORDS
            if kw in query_lower
        ]
        if low_matches:
            reasons.append(f"Low-complexity keywords: {low_matches[:3]}")

        # Check for code blocks or technical content
        has_code = "```" in query or re.search(r'def |class |function |import ', query)
        if has_code:
            reasons.append("Contains code/technical content")

        # Check for question complexity
        question_words = re.findall(r'\b(why|how|what if|explain|describe)\b', query_lower)
        if len(question_words) > 1:
            reasons.append(f"Multiple analytical questions: {question_words}")

        # Length-based heuristic
        if word_count > 100:
            reasons.append(f"Long query ({word_count} words)")
        elif word_count < 10:
            reasons.append(f"Short query ({word_count} words)")

        # Scoring
        score = 0

        # High complexity factors
        score += len(high_matches) * 2
        if has_code:
            score += 2
        if len(question_words) > 1:
            score += 1
        if word_count > 100:
            score += 1
        if word_count > 50:
            score += 0.5

        # Low complexity factors (subtract)
        score -= len(low_matches) * 1.5
        if word_count < 10:
            score -= 1

        # Classify
        if score >= 3:
            complexity = Complexity.HIGH
        elif score >= 1:
            complexity = Complexity.MEDIUM
        else:
            complexity = Complexity.LOW

        reasoning = f"Score: {score:.1f}. " + "; ".join(reasons) if reasons else f"Score: {score:.1f}"

        return complexity, reasoning

    def estimate_tokens(self, query: str) -> int:
        """Estimate token count for a query."""
        word_count = len(query.split())
        return int(word_count * self.config.TOKENS_PER_WORD)


_NUM_PREDICT = {"mimir": -2, "codex": 400, "qwen2.5-coder:1.5b": 300}
# -2 = use Modelfile default (120 for mimir); codex caps at 400; coder at 300


class Architect:
    """
    The Mind - Dual-Mode Intelligence Router.

    Routes queries to appropriate models based on:
    1. Query complexity analysis
    2. Thermal clearance from Cortex
    3. System resource availability
    """

    def __init__(self, config: Optional[ArchitectConfig] = None):
        self.config = config or ArchitectConfig()
        self.analyzer = ComplexityAnalyzer(self.config)
        self.cortex = get_cortex()
        self._session: Optional[aiohttp.ClientSession] = None
        self.session_stats = LLMSessionStats()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # Sandbox enforcement for CODER model
    _DESTRUCTIVE_PATTERNS = re.compile(
        r'\b(delete|remove|rm|unlink|rmdir|truncate|overwrite|drop)\b.*'
        r'(\.py|\.json|\.md|\.txt|\.yaml|\.yml|\.cfg|\.ini|/)',
        re.IGNORECASE
    )

    def _validate_coder_sandbox(self, query: str) -> Optional[str]:
        """Check if coder request targets files outside sandbox.
        Returns error message if blocked, None if allowed."""
        if not self._DESTRUCTIVE_PATTERNS.search(query):
            return None
        sandbox = str(self.config.SANDBOX_DIR)
        paths = re.findall(r'[\w./\\-]+\.(?:py|json|md|txt|yaml|yml|cfg|ini)', query)
        for p in paths:
            resolved = str(Path(p).resolve())
            if not resolved.startswith(sandbox):
                return (
                    f"[SECURITY_RESTRICTION] Coder model cannot modify "
                    f"'{p}' — outside sandbox ({sandbox}). "
                    f"File operations restricted to sandbox directory."
                )
        return None

    def _detect_code_request(self, query: str) -> bool:
        """Return True if the query looks like a code generation request."""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.config.COMPLEXITY_CODE_KEYWORDS)

    def route(self, query: str) -> RoutingDecision:
        """
        Determine the routing for a query.

        This is the primary decision function that combines
        complexity analysis with thermal clearance.

        Routing priority:
        1. Code keywords detected + GREEN/YELLOW thermal → CODER
        2. HIGH complexity + GREEN thermal → ACADEMY
        3. Everything else → REFLEX
        """
        # Analyze complexity
        complexity, analysis_reasoning = self.analyzer.analyze(query)

        # Get thermal status
        metabolic_state = self.cortex.read_metabolic_state()
        thermal_status = metabolic_state.thermal_status
        clearance = metabolic_state.metabolic_clearance

        # EXPERIMENTAL mode: only via explicit request, never auto-routed
        # (code keywords no longer trigger auto-routing to prevent
        # experimental model from entering live game loops)

        if complexity == Complexity.HIGH and clearance:
            mode = ThinkingMode.ACADEMY
            model = self.config.MODEL_ACADEMY
            reasoning = (
                f"ACADEMY mode selected. {analysis_reasoning}. "
                f"Thermal: {thermal_status.value}, Clearance: GRANTED"
            )
        else:
            mode = ThinkingMode.REFLEX
            model = self.config.MODEL_REFLEX

            if complexity == Complexity.HIGH and not clearance:
                reasoning = (
                    f"REFLEX mode (thermal override). {analysis_reasoning}. "
                    f"Thermal: {thermal_status.value}, Clearance: DENIED - "
                    f"Academy blocked, falling back to Reflex"
                )
            else:
                reasoning = (
                    f"REFLEX mode selected. {analysis_reasoning}. "
                    f"Thermal: {thermal_status.value}"
                )

        return RoutingDecision(
            mode=mode,
            model=model,
            complexity=complexity,
            thermal_status=thermal_status,
            clearance_granted=clearance,
            reasoning=reasoning,
            estimated_tokens=self.analyzer.estimate_tokens(query)
        )

    async def invoke_model(
        self,
        query: str,
        system_prompt: str = "",
        decision: Optional[RoutingDecision] = None,
        conversation_history: Optional[list[dict]] = None
    ) -> ModelResponse:
        """
        Invoke the appropriate model based on routing decision.

        Args:
            query: User query
            system_prompt: System prompt to prepend
            decision: Pre-computed routing decision (or None to compute)
            conversation_history: Optional list of previous messages
                                 Each dict should have "role" and "content" keys

        Returns:
            ModelResponse with content and metadata
        """
        if decision is None:
            decision = self.route(query)

        # Sandbox enforcement for EXPERIMENTAL mode
        if decision.mode == ThinkingMode.EXPERIMENTAL:
            sandbox_error = self._validate_coder_sandbox(query)
            if sandbox_error:
                return ModelResponse(
                    content=sandbox_error,
                    model=decision.model,
                    mode=decision.mode,
                )

        # Get persona and thermal modifiers for system prompt
        base_persona_prompt = self.cortex.get_base_persona_prompt()
        thermal_modifier = self.cortex.get_system_prompt_modifier()
        full_system_prompt = base_persona_prompt + thermal_modifier + system_prompt

        # Format conversation history into the prompt
        # Take the last 10 messages to maintain context without overwhelming the model
        formatted_prompt = query
        if conversation_history:
            # Take last 10 messages (5 exchanges)
            recent_history = conversation_history[-10:]

            # Build context string from history
            context_lines = []
            for msg in recent_history:
                role = msg.get("role", "")
                content = msg.get("content", "")

                if role == "user":
                    context_lines.append(f"User: {content}")
                elif role == "assistant":
                    context_lines.append(f"Assistant: {content}")

            # Prepend history to the current query if we have any
            if context_lines:
                history_context = "\n".join(context_lines)
                formatted_prompt = f"Previous conversation:\n{history_context}\n\nCurrent query:\nUser: {query}"

        # Record start thermal
        start_state = self.cortex.read_metabolic_state()
        start_time = time.time()

        # Select timeout based on mode
        if decision.mode == ThinkingMode.ACADEMY:
            timeout = self.config.ACADEMY_TIMEOUT_MS
        elif decision.mode == ThinkingMode.EXPERIMENTAL:
            timeout = self.config.EXPERIMENTAL_TIMEOUT_MS
        else:
            timeout = self.config.REFLEX_TIMEOUT_MS

        # Call Ollama with formatted prompt including history
        content, thinking_trace, tokens = await self._call_ollama(
            model=decision.model,
            prompt=formatted_prompt,
            system=full_system_prompt,
            timeout_ms=timeout
        )

        # Record end thermal
        end_state = self.cortex.read_metabolic_state()
        latency = (time.time() - start_time) * 1000

        response = ModelResponse(
            content=content,
            model=decision.model,
            mode=decision.mode,
            thinking_trace=thinking_trace,
            tokens_used=tokens,
            latency_ms=latency,
            thermal_at_start=start_state.cpu_temp_celsius,
            thermal_at_end=end_state.cpu_temp_celsius
        )
        self.session_stats.record(response)
        return response

    async def _call_ollama(
        self,
        model: str,
        prompt: str,
        system: str = "",
        timeout_ms: int = 30000
    ) -> tuple[str, Optional[str], int]:
        """
        Call Ollama API.

        Returns:
            (response_content, thinking_trace, token_count)
        """
        session = await self._get_session()

        num_predict = _NUM_PREDICT.get(model, 300)

        # Hard thermal pain reflex — override token budget at CRITICAL
        metabolic = self.cortex.read_metabolic_state()
        if metabolic.thermal_status == ThermalStatus.CRITICAL:
            num_predict = 150  # Absolute ceiling under thermal duress

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "num_predict": num_predict,
            }
        }

        try:
            timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000)
            async with session.post(
                f"{self.config.OLLAMA_HOST}/api/generate",
                json=payload,
                timeout=timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return f"[Model error: {response.status}] {error_text}", None, 0

                data = await response.json()
                content = data.get("response", "")
                tokens = data.get("eval_count", 0)

                # Extract thinking trace (qwen3 <think> blocks) if present
                thinking_trace = None
                if "<think>" in content:
                    think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
                    if think_match:
                        thinking_trace = think_match.group(1).strip()
                        # Remove thinking from main content
                        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

                return content, thinking_trace, tokens

        except asyncio.TimeoutError:
            return "[Response timeout - model took too long]", None, 0
        except aiohttp.ClientError as e:
            return f"[Connection error: {e}]", None, 0
        except Exception as e:
            return f"[Unexpected error: {e}]", None, 0

    async def invoke_stream(
        self,
        query: str,
        system_prompt: str = "",
        decision: Optional[RoutingDecision] = None
    ) -> AsyncIterator[str]:
        """
        Stream response from the model.

        Yields content chunks as they arrive.
        """
        if decision is None:
            decision = self.route(query)

        thermal_modifier = self.cortex.get_system_prompt_modifier()
        full_system_prompt = thermal_modifier + system_prompt

        if decision.mode == ThinkingMode.ACADEMY:
            timeout = self.config.ACADEMY_TIMEOUT_MS
        elif decision.mode == ThinkingMode.EXPERIMENTAL:
            timeout = self.config.EXPERIMENTAL_TIMEOUT_MS
        else:
            timeout = self.config.REFLEX_TIMEOUT_MS

        num_predict = _NUM_PREDICT.get(decision.model, 300)

        # Hard thermal pain reflex
        metabolic = self.cortex.read_metabolic_state()
        if metabolic.thermal_status == ThermalStatus.CRITICAL:
            num_predict = 150

        session = await self._get_session()

        payload = {
            "model": decision.model,
            "prompt": query,
            "system": full_system_prompt,
            "stream": True,
            "options": {
                "num_predict": num_predict,
            }
        }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout / 1000)
            async with session.post(
                f"{self.config.OLLAMA_HOST}/api/generate",
                json=payload,
                timeout=timeout_obj
            ) as response:
                if response.status != 200:
                    yield f"[Model error: {response.status}]"
                    return

                # Stream response chunks
                in_thinking = False
                async for line in response.content:
                    if not line:
                        continue
                    try:
                        import json
                        chunk = json.loads(line)
                        text = chunk.get("response", "")

                        # Filter out thinking blocks for streaming
                        if "<think>" in text:
                            in_thinking = True
                        if "</think>" in text:
                            in_thinking = False
                            text = text.split("</think>")[-1]
                            continue
                        if in_thinking:
                            continue

                        if text:
                            yield text

                    except json.JSONDecodeError:
                        continue

        except asyncio.TimeoutError:
            yield "[Response timeout]"
        except Exception as e:
            yield f"[Error: {e}]"

    def get_routing_report(self, query: str) -> str:
        """
        Generate a human-readable routing report for a query.

        Useful for debugging and status display.
        """
        decision = self.route(query)

        mode_indicators = {
            ThinkingMode.ACADEMY: "🧠",
            ThinkingMode.EXPERIMENTAL: "💻",
            ThinkingMode.REFLEX: "⚡",
        }
        mode_indicator = mode_indicators.get(decision.mode, "⚡")
        clearance_indicator = "✅" if decision.clearance_granted else "❌"

        lines = [
            f"{mode_indicator} Routing Decision: {decision.mode.value}",
            f"   Model: {decision.model}",
            f"   Complexity: {decision.complexity.value}",
            f"   Thermal: {decision.thermal_status.value}",
            f"   Academy Clearance: {clearance_indicator}",
            f"   Reasoning: {decision.reasoning}",
            f"   Est. Tokens: {decision.estimated_tokens}"
        ]

        return "\n".join(lines)


# Singleton instance
_architect_instance: Optional[Architect] = None


def get_architect() -> Architect:
    """Get or create the singleton Architect instance."""
    global _architect_instance
    if _architect_instance is None:
        _architect_instance = Architect()
    return _architect_instance


async def route_and_invoke(
    query: str,
    system_prompt: str = ""
) -> ModelResponse:
    """
    Convenience function: Route query and invoke appropriate model.

    Args:
        query: User query
        system_prompt: Optional system prompt

    Returns:
        ModelResponse with content and metadata
    """
    architect = get_architect()
    return await architect.invoke_model(query, system_prompt)


if __name__ == "__main__":
    # Self-test: Analyze routing for sample queries
    print("C.O.D.E.X. Architect - Routing Analysis")
    print("=" * 50)

    architect = Architect()

    test_queries = [
        "Roll a D20 for initiative",
        "Hello!",
        "Analyze this codebase and explain the architecture",
        "What's 2 + 2?",
        "Debug this function and explain why it's failing:\n```python\ndef foo():\n    return bar\n```",
        "Compare the trade-offs between using Redis vs PostgreSQL for session storage",
    ]

    for query in test_queries:
        print(f"\nQuery: \"{query[:50]}{'...' if len(query) > 50 else ''}\"")
        print(architect.get_routing_report(query))
        print("-" * 40)

    # Test actual invocation (requires Ollama running)
    print("\n" + "=" * 50)
    print("Live Invocation Test (requires Ollama)")
    print("=" * 50)

    async def test_invoke():
        try:
            response = await architect.invoke_model(
                "Say 'Hello from C.O.D.E.X.' in exactly 5 words.",
                system_prompt="You are a helpful assistant."
            )
            print(f"\nResponse: {response.content}")
            print(f"Model: {response.model}")
            print(f"Mode: {response.mode.value}")
            print(f"Latency: {response.latency_ms:.0f}ms")
            print(f"Thermal: {response.thermal_at_start:.1f}°C → {response.thermal_at_end:.1f}°C")
        except Exception as e:
            print(f"Invocation test skipped: {e}")
        finally:
            await architect.close()

    asyncio.run(test_invoke())

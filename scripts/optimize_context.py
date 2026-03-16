#!/usr/bin/env python3
"""
optimize_context.py — Context Window Manager for Mimir V2

Manages the sliding window of chat history to stay within the 8192 token limit.

Architecture:
- System Prompt: ~400 tokens (always pinned)
- World State: ~500 tokens (always pinned, contains Faction/Location)
- Recent Turns: Last 4 turns (8 messages: 4 user + 4 assistant)
- Generation Headroom: Reserved for model output
- Total Budget: 8192 tokens
"""

from typing import Optional


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.

    Uses a simple heuristic: ~4 characters per token for English text.
    This is approximate but sufficient for budget management.
    For Qwen models, actual tokenization is closer to 3.5 chars/token.

    Args:
        text: The text to estimate tokens for

    Returns:
        Estimated token count (int)
    """
    if not text:
        return 0
    # Conservative estimate: 4 chars per token
    return max(1, len(text) // 4)


class ContextWindow:
    """
    Manages the sliding window of context for Mimir's LLM calls.

    Maintains three priority tiers:
    1. PINNED (never evicted): System prompt + World State
    2. RECENT (last N turns): Most recent conversation exchanges
    3. EVICTABLE (older turns): Removed when budget exceeded
    """

    def __init__(self, max_tokens: int = 8192, reserved_for_generation: int = 2048):
        """
        Initialize the context window manager.

        Args:
            max_tokens: Maximum context window size (default 8192)
            reserved_for_generation: Tokens reserved for model output (default 2048)
        """
        self.max_tokens = max_tokens
        self.reserved = reserved_for_generation
        self.budget = max_tokens - reserved_for_generation  # usable context

        self.system_prompt: str = ""
        self.world_state: str = ""  # pinned world state summary
        self.history: list[dict] = []  # {"role": "user"/"assistant", "content": "..."}
        self.max_recent_turns: int = 4  # keep last 4 exchanges

        # Statistics tracking
        self._total_turns_added = 0
        self._total_turns_evicted = 0

    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system prompt (always pinned).

        Args:
            prompt: The system prompt text
        """
        self.system_prompt = prompt

    def set_world_state(self, state: dict) -> None:
        """
        Set the pinned world state from a WorldState or game engine dict.

        Extracts and formats:
        - World name and genre
        - Current faction terms (Crown/Crew names)
        - Current location/region
        - Player sway and allegiance
        - Key NPCs or active events

        Compresses this into a concise string under ~500 tokens.

        Args:
            state: Dictionary containing world state (from WorldEngine.to_dict())
        """
        self.world_state = self.compress_world_state(state)

    def add_turn(self, role: str, content: str) -> None:
        """
        Add a conversation turn and enforce the sliding window.

        Appends the turn to history, then trims oldest turns if
        the total context exceeds the budget.

        Args:
            role: "user" or "assistant"
            content: The message content
        """
        if not content.strip():
            return  # Don't add empty turns

        self.history.append({
            "role": role,
            "content": content
        })
        self._total_turns_added += 1

        # Enforce budget
        self._trim_to_budget()

    def build_messages(self) -> list[dict]:
        """
        Build the final message list for the LLM API call.

        Returns:
            List of {"role": "system"/"user"/"assistant", "content": "..."} dicts
            ready to pass to Ollama's chat API.

        Structure:
        1. System message (system_prompt + world_state)
        2. Recent history turns (last N that fit in budget)
        """
        messages = []

        # 1. System message (pinned)
        system_content = self.system_prompt
        if self.world_state:
            system_content += f"\n\n--- CURRENT WORLD STATE ---\n{self.world_state}"

        messages.append({
            "role": "system",
            "content": system_content
        })

        # 2. History (post-eviction, guaranteed to fit budget)
        messages.extend(self.history)

        return messages

    def _trim_to_budget(self) -> None:
        """
        Remove oldest turns until total tokens fit within budget.

        Eviction order:
        1. Oldest assistant responses (least recent)
        2. Oldest user messages (least recent)
        Never evicts: system prompt, world state, last 2 turns
        """
        while True:
            # Calculate current usage
            system_tokens = estimate_tokens(self.system_prompt)
            world_tokens = estimate_tokens(self.world_state)
            history_tokens = sum(
                estimate_tokens(turn["content"]) for turn in self.history
            )
            total_used = system_tokens + world_tokens + history_tokens

            # Check if we're within budget
            if total_used <= self.budget:
                break

            # Protect last 2 turns (1 exchange minimum)
            if len(self.history) <= 2:
                # Cannot trim further without breaking conversation
                break

            # Evict oldest turn
            self.history.pop(0)
            self._total_turns_evicted += 1

    def get_usage_report(self) -> dict:
        """
        Return current token usage breakdown.

        Returns:
            {
                "system_tokens": int,
                "world_state_tokens": int,
                "history_tokens": int,
                "total_used": int,
                "budget": int,
                "headroom": int,
                "turns_kept": int,
                "turns_evicted": int,
            }
        """
        system_tokens = estimate_tokens(self.system_prompt)
        world_tokens = estimate_tokens(self.world_state)
        history_tokens = sum(
            estimate_tokens(turn["content"]) for turn in self.history
        )
        total_used = system_tokens + world_tokens + history_tokens

        return {
            "system_tokens": system_tokens,
            "world_state_tokens": world_tokens,
            "history_tokens": history_tokens,
            "total_used": total_used,
            "budget": self.budget,
            "headroom": self.budget - total_used,
            "turns_kept": len(self.history),
            "turns_evicted": self._total_turns_evicted,
        }

    def compress_world_state(self, world_state: dict) -> str:
        """
        Compress a WorldState dict into a concise context string.

        Input: Full WorldState dict (may have G.R.A.P.E.S., terms, primer, etc.)
        Output: Condensed string like:
            "World: The Iron Reach | Genre: Dark Fantasy | Tone: Grim
             Crown: The General | Crew: The Resistance
             Location: The Border | Day: 3/5 | Sway: +2 (Crew Loyal)
             Active: Legacy Intervention pending"

        Args:
            world_state: WorldState dictionary

        Returns:
            Compressed string (target: <500 tokens)
        """
        if not world_state:
            return ""

        lines = []

        # 1. World identity
        world_name = world_state.get("name", "Unknown World")
        genre = world_state.get("genre", "Fantasy")
        tone = world_state.get("tone", "Neutral")
        lines.append(f"World: {world_name} | Genre: {genre} | Tone: {tone}")

        # 2. Faction terms
        terms = world_state.get("terms", {})
        crown = terms.get("crown", "The Authority")
        crew = terms.get("crew", "The Resistance")
        lines.append(f"Crown: {crown} | Crew: {crew}")

        # 3. Current state
        location = world_state.get("current_location", "Unknown")
        day = world_state.get("current_day", 1)
        max_days = world_state.get("max_days", 5)
        lines.append(f"Location: {location} | Day: {day}/{max_days}")

        # 4. Player allegiance
        sway = world_state.get("sway", 0)
        if sway < -1:
            allegiance = "Crown Loyal"
        elif sway > 1:
            allegiance = "Crew Loyal"
        else:
            allegiance = "Neutral"
        lines.append(f"Sway: {sway:+d} ({allegiance})")

        return "\n".join(lines)


def create_mimir_context(
    system_prompt: str,
    world_state: dict,
    chat_history: list[dict],
    max_tokens: int = 8192
) -> list[dict]:
    """
    One-shot helper to build an optimized context payload.

    Usage:
        messages = create_mimir_context(
            system_prompt=MIMIR_SYSTEM_PROMPT,
            world_state=engine.to_dict(),
            chat_history=session_history,
        )
        response = ollama.chat(model="codex", messages=messages)

    Args:
        system_prompt: Mimir persona and protocol instructions
        world_state: Current world state dictionary
        chat_history: List of {"role": "user"/"assistant", "content": "..."} dicts
        max_tokens: Maximum context window (default 8192)

    Returns:
        List of messages ready for Ollama chat API
    """
    ctx = ContextWindow(max_tokens=max_tokens)
    ctx.set_system_prompt(system_prompt)
    ctx.set_world_state(world_state)

    for turn in chat_history:
        ctx.add_turn(turn["role"], turn["content"])

    return ctx.build_messages()


# ============================================================================
# STANDALONE TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    # Demo: Create a context window, add turns, show budget usage
    ctx = ContextWindow(max_tokens=8192)
    ctx.set_system_prompt("You are Mimir, the C.O.D.E.X. Dungeon Master...")
    ctx.set_world_state({
        "name": "The Iron Reach",
        "genre": "Dark Fantasy",
        "tone": "grim",
        "terms": {"crown": "The General", "crew": "The Resistance"},
        "grapes": {"geography": "Frozen tundra", "religion": "The old gods are dead"}
    })

    # Simulate 10 turns, showing eviction
    for i in range(10):
        ctx.add_turn("user", f"Turn {i}: I approach the gate and demand entry.")
        ctx.add_turn("assistant", f"Turn {i}: The guard eyes you with suspicion. 'State your business,' he growls, hand on his sword hilt. The wind carries ash from the burning fields beyond.")

    # Show usage
    report = ctx.get_usage_report()
    print("Context Usage Report:")
    print(f"  System Prompt: {report['system_tokens']} tokens")
    print(f"  World State:   {report['world_state_tokens']} tokens")
    print(f"  History:       {report['history_tokens']} tokens")
    print(f"  Total Used:    {report['total_used']} tokens")
    print(f"  Budget:        {report['budget']} tokens")
    print(f"  Headroom:      {report['headroom']} tokens")
    print(f"  Turns Kept:    {report['turns_kept']}")
    print(f"  Turns Evicted: {report['turns_evicted']}")

    # Show message count and structure
    messages = ctx.build_messages()
    print(f"\nFinal message structure: {len(messages)} messages")
    for idx, msg in enumerate(messages):
        role = msg["role"]
        content_preview = msg["content"][:60].replace("\n", " ")
        print(f"  {idx+1}. [{role}] {content_preview}...")

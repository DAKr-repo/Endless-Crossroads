"""
Tests for the Narrative Intelligence Layer (WO-V47.0).

Tests:
- build_narrative_frame() returns dict with required keys
- get_relevant_shards() tag overlap scoring + budget enforcement
- validate_narrative() rejects broken output, accepts good output
- select_palette() returns valid palettes for each tier
- NARRATIVE_TEMPLATES structure validation
- ROOM_FRAGMENTS coverage
"""
import pytest

from codex.core.services.narrative_frame import (
    build_narrative_frame,
    format_frame_as_prompt,
    get_relevant_shards,
    validate_narrative,
    select_palette,
    NARRATIVE_PALETTES,
    NARRATIVE_TEMPLATES,
    _extract_keywords,
    _format_palette,
)


# ─────────────────────────────────────────────────────────────────────
# build_narrative_frame
# ─────────────────────────────────────────────────────────────────────

class TestBuildNarrativeFrame:
    """Tests for build_narrative_frame()."""

    def _make_stub_engine(self):
        """Minimal engine-like object."""
        class StubEngine:
            system_id = "burnwillow"
            current_room_id = ""
            dungeon = None
            current_tier = 1
        return StubEngine()

    def test_returns_dict_with_required_keys(self):
        engine = self._make_stub_engine()
        frame = build_narrative_frame(engine, "Describe the room.")
        assert isinstance(frame, dict)
        for key in ("system", "context", "examples", "prompt"):
            assert key in frame

    def test_prompt_is_preserved(self):
        engine = self._make_stub_engine()
        frame = build_narrative_frame(engine, "Test prompt here")
        assert frame["prompt"] == "Test prompt here"

    def test_system_uses_template_when_provided(self):
        engine = self._make_stub_engine()
        frame = build_narrative_frame(
            engine, "Describe room.", template_key="room_description"
        )
        assert "dungeon rooms" in frame["system"].lower()

    def test_system_has_default_when_no_template(self):
        engine = self._make_stub_engine()
        frame = build_narrative_frame(engine, "Describe room.", template_key="nonexistent")
        assert "dark fantasy" in frame["system"].lower()

    def test_examples_populated_for_valid_template(self):
        engine = self._make_stub_engine()
        frame = build_narrative_frame(
            engine, "Describe room.", template_key="room_description"
        )
        assert len(frame["examples"]) >= 2

    def test_examples_empty_for_invalid_template(self):
        engine = self._make_stub_engine()
        frame = build_narrative_frame(
            engine, "Describe room.", template_key="nonexistent"
        )
        assert frame["examples"] == []


# ─────────────────────────────────────────────────────────────────────
# format_frame_as_prompt
# ─────────────────────────────────────────────────────────────────────

class TestFormatFrameAsPrompt:

    def test_includes_system_section(self):
        frame = {"system": "Test system", "context": "", "examples": [], "prompt": "Go"}
        result = format_frame_as_prompt(frame)
        assert "SYSTEM: Test system" in result

    def test_includes_task_section(self):
        frame = {"system": "", "context": "", "examples": [], "prompt": "Describe the forge"}
        result = format_frame_as_prompt(frame)
        assert "TASK:" in result
        assert "Describe the forge" in result

    def test_includes_examples_when_present(self):
        frame = {
            "system": "",
            "context": "",
            "examples": [{"input": "test in", "output": "test out"}],
            "prompt": "Go",
        }
        result = format_frame_as_prompt(frame)
        assert "Example 1:" in result
        assert "test in" in result
        assert "test out" in result

    def test_includes_context_when_present(self):
        frame = {"system": "", "context": "Some lore here", "examples": [], "prompt": "Go"}
        result = format_frame_as_prompt(frame)
        assert "CONTEXT:" in result
        assert "Some lore here" in result


# ─────────────────────────────────────────────────────────────────────
# get_relevant_shards
# ─────────────────────────────────────────────────────────────────────

class TestGetRelevantShards:

    def _make_memory_engine(self, shards=None):
        from codex.core.memory import CodexMemoryEngine, ShardType
        engine = CodexMemoryEngine()
        if shards:
            for content, tags in shards:
                engine.create_shard(
                    content=content,
                    shard_type=ShardType.ANCHOR,
                    tags=tags,
                )
        return engine

    def test_returns_empty_for_no_keywords(self):
        mem = self._make_memory_engine()
        result = get_relevant_shards(mem, "the a an is")
        assert result == []

    def test_returns_matching_shard(self):
        mem = self._make_memory_engine([
            ("The forge burns bright", ["forge", "fire"]),
        ])
        result = get_relevant_shards(mem, "Tell me about the forge")
        assert len(result) == 1
        assert "forge" in result[0].content.lower()

    def test_scores_by_overlap_count(self):
        mem = self._make_memory_engine([
            ("Forge and fire", ["forge", "fire"]),
            ("Just forge", ["forge"]),
        ])
        result = get_relevant_shards(mem, "The forge fire burns")
        # Higher overlap (forge+fire) should come first
        assert len(result) == 2
        assert "fire" in result[0].content.lower()

    def test_respects_budget(self):
        mem = self._make_memory_engine([
            ("A" * 400, ["forge"]),  # ~100 tokens
            ("B" * 400, ["forge"]),  # ~100 tokens
        ])
        result = get_relevant_shards(mem, "The forge", budget=120)
        assert len(result) == 1

    def test_ignores_non_anchor_shards(self):
        from codex.core.memory import CodexMemoryEngine, ShardType
        mem = CodexMemoryEngine()
        mem.create_shard("Echo with forge tag", shard_type=ShardType.ECHO, tags=["forge"])
        result = get_relevant_shards(mem, "The forge")
        assert result == []


# ─────────────────────────────────────────────────────────────────────
# validate_narrative
# ─────────────────────────────────────────────────────────────────────

class TestValidateNarrative:

    def test_accepts_good_narrative(self):
        text = (
            "Rust flakes drift from the ceiling like red snow. "
            "The anvil is split clean in two."
        )
        assert validate_narrative(text) is True

    def test_rejects_empty_string(self):
        assert validate_narrative("") is False

    def test_rejects_too_short(self):
        assert validate_narrative("Hi") is False

    def test_rejects_code_blocks(self):
        assert validate_narrative("Here is the code:\n```python\ndef foo(): pass\n```") is False

    def test_rejects_import_statement(self):
        assert validate_narrative("You should import os and then run the script") is False

    def test_rejects_ai_meta_as_an_ai(self):
        assert validate_narrative("As an AI language model, I can tell you about dungeons.") is False

    def test_rejects_ai_meta_i_cannot(self):
        assert validate_narrative("I cannot help you with that request because reasons.") is False

    def test_rejects_ai_meta_let_me(self):
        assert validate_narrative("Let me help you explore this dark cavern today.") is False

    def test_rejects_ai_meta_here_is(self):
        assert validate_narrative("Here is a description of the room for your adventure.") is False

    def test_rejects_repetition_loop(self):
        phrase = "the darkness grows deeper and deeper "
        text = phrase * 5  # Same 5-word chunk repeated
        assert validate_narrative(text) is False

    def test_rejects_control_characters(self):
        assert validate_narrative("The forge burns\x00 with ancient fire and heat") is False

    def test_accepts_narrative_with_newlines(self):
        text = (
            "The corridor stretches ahead, dark and cold.\n"
            "Water drips somewhere in the distance."
        )
        assert validate_narrative(text) is True


# ─────────────────────────────────────────────────────────────────────
# select_palette
# ─────────────────────────────────────────────────────────────────────

class TestSelectPalette:

    def test_returns_palette_for_burnwillow_t1(self):
        palette = select_palette("burnwillow", 1)
        assert "adjectives" in palette
        assert "verbs" in palette
        assert "sounds" in palette
        assert "smells" in palette

    def test_returns_palette_for_all_tiers(self):
        for tier in (1, 2, 3, 4):
            palette = select_palette("burnwillow", tier)
            assert palette, f"No palette for burnwillow tier {tier}"

    def test_returns_empty_for_unknown_setting(self):
        palette = select_palette("nonexistent", 1)
        assert palette == {}

    def test_palette_has_multiple_entries(self):
        palette = select_palette("burnwillow", 2)
        assert len(palette["adjectives"]) >= 3
        assert len(palette["smells"]) >= 3


# ─────────────────────────────────────────────────────────────────────
# NARRATIVE_TEMPLATES structure
# ─────────────────────────────────────────────────────────────────────

class TestNarrativeTemplates:

    EXPECTED_KEYS = ["room_description", "npc_dialogue", "quest_generation",
                     "combat_narration", "atmosphere"]

    def test_all_template_keys_exist(self):
        for key in self.EXPECTED_KEYS:
            assert key in NARRATIVE_TEMPLATES, f"Missing template: {key}"

    def test_all_templates_have_system(self):
        for key in self.EXPECTED_KEYS:
            assert "system" in NARRATIVE_TEMPLATES[key]
            assert len(NARRATIVE_TEMPLATES[key]["system"]) > 0

    def test_all_templates_have_examples(self):
        for key in self.EXPECTED_KEYS:
            examples = NARRATIVE_TEMPLATES[key].get("examples", [])
            assert len(examples) >= 2, f"Template '{key}' needs >= 2 examples"

    def test_examples_have_input_output(self):
        for key in self.EXPECTED_KEYS:
            for ex in NARRATIVE_TEMPLATES[key]["examples"]:
                assert "input" in ex, f"Example in '{key}' missing 'input'"
                assert "output" in ex, f"Example in '{key}' missing 'output'"


# ─────────────────────────────────────────────────────────────────────
# ROOM_FRAGMENTS coverage
# ─────────────────────────────────────────────────────────────────────

class TestRoomFragments:

    def test_fragments_exist(self):
        from codex.core.narrative_content import ROOM_FRAGMENTS
        assert len(ROOM_FRAGMENTS) > 0

    def test_all_tiers_have_normal_fragments(self):
        from codex.core.narrative_content import ROOM_FRAGMENTS
        for tier in (1, 2, 3, 4):
            key = ("normal", tier)
            assert key in ROOM_FRAGMENTS, f"Missing fragments for {key}"
            assert len(ROOM_FRAGMENTS[key]) >= 3

    def test_fragments_are_strings(self):
        from codex.core.narrative_content import ROOM_FRAGMENTS
        for key, fragments in ROOM_FRAGMENTS.items():
            for frag in fragments:
                assert isinstance(frag, str), f"Non-string fragment in {key}"
                assert len(frag) > 10, f"Fragment too short in {key}: {frag}"

    def test_common_room_types_covered(self):
        from codex.core.narrative_content import ROOM_FRAGMENTS
        for room_type in ("normal", "forge", "library", "boss", "treasure",
                          "corridor", "secret", "start"):
            found = any(k[0] == room_type for k in ROOM_FRAGMENTS)
            assert found, f"Room type '{room_type}' has no fragments"


# ─────────────────────────────────────────────────────────────────────
# Helper function tests
# ─────────────────────────────────────────────────────────────────────

class TestHelpers:

    def test_extract_keywords_filters_stopwords(self):
        keywords = _extract_keywords("the forge is on fire")
        assert "the" not in keywords
        assert "forge" in keywords
        assert "fire" in keywords

    def test_extract_keywords_lowercase(self):
        keywords = _extract_keywords("FORGE FIRE")
        assert "forge" in keywords

    def test_format_palette_includes_sections(self):
        palette = {"adjectives": ["dark", "cold"], "verbs": ["drips"],
                   "sounds": ["echo"], "smells": ["ash"]}
        result = _format_palette(palette)
        assert "SENSORY PALETTE" in result
        assert "dark" in result

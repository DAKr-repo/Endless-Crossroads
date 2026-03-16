#!/usr/bin/env python3
"""
Tests for Crown & Crew v4.0 expansion:
- Rest-based progression
- Variable arc length
- Council dilemma consolidation
- Quest archetypes
- Serialization (to_dict / from_dict)
- Tarot module availability
"""

import pytest
from codex.games.crown.engine import (
    CrownAndCrewEngine,
    COUNCIL_DILEMMAS,
    MORNING_EVENTS,
)


# =============================================================================
# REST MECHANICS
# =============================================================================

class TestRestMechanics:
    def test_long_rest_advances_day(self):
        engine = CrownAndCrewEngine()
        assert engine.day == 1
        engine.trigger_long_rest()
        assert engine.day == 2

    def test_short_rest_no_day_advance(self):
        engine = CrownAndCrewEngine()
        assert engine.day == 1
        engine.trigger_short_rest()
        assert engine.day == 1  # Short rest does NOT advance day

    def test_short_rest_applies_sway(self):
        """Short rest applies sway shift based on morning event bias."""
        # Day 1 only returns neutral events — use Day 2+ to get biased ones
        shifts = set()
        for _ in range(50):
            e = CrownAndCrewEngine()
            e.day = 2  # Day 2+ returns crown/crew biased events
            e.trigger_short_rest()
            shifts.add(e.sway)
        # Should have at least some non-zero shifts (crown/crew biased events)
        assert shifts != {0}, "Expected some sway shifts from short rest events"

    def test_skip_rest_sway_decay_from_positive(self):
        engine = CrownAndCrewEngine()
        engine.sway = 2
        engine.skip_rest()
        assert engine.sway == 1

    def test_skip_rest_sway_decay_from_negative(self):
        engine = CrownAndCrewEngine()
        engine.sway = -2
        engine.skip_rest()
        assert engine.sway == -1

    def test_skip_rest_sway_at_zero(self):
        engine = CrownAndCrewEngine()
        engine.sway = 0
        engine.skip_rest()
        assert engine.sway == 0

    def test_default_rest_config_backward_compat(self):
        """Default engine with 5-day arc behaves identically to old behavior."""
        engine = CrownAndCrewEngine()
        assert engine.arc_length == 5
        assert engine.rest_type == "long"
        assert engine.rest_config["breach_day_fraction"] == 0.6

    def test_rest_type_updated(self):
        engine = CrownAndCrewEngine()
        engine.trigger_short_rest()
        assert engine.rest_type == "short"
        engine.trigger_long_rest()
        assert engine.rest_type == "long"


# =============================================================================
# ARC LENGTH
# =============================================================================

class TestArcLength:
    def test_custom_arc_length(self):
        engine = CrownAndCrewEngine(arc_length=7)
        assert engine.arc_length == 7

    def test_arc_length_allows_more_days(self):
        engine = CrownAndCrewEngine(arc_length=7)
        for _ in range(6):
            engine.trigger_long_rest()
        assert engine.day == 7
        assert engine.day <= engine.arc_length

    def test_breach_day_scales_with_arc(self):
        # Default: 5 * 0.6 = 3.0 -> round = 3
        engine = CrownAndCrewEngine(arc_length=5)
        engine.day = 3
        assert engine.is_breach_day()

        # 7 * 0.6 = 4.2 -> round = 4
        engine = CrownAndCrewEngine(arc_length=7)
        engine.day = 4
        assert engine.is_breach_day()
        engine.day = 3
        assert not engine.is_breach_day()

        # 3 * 0.6 = 1.8 -> round = 2
        engine = CrownAndCrewEngine(arc_length=3)
        engine.day = 2
        assert engine.is_breach_day()

    def test_get_status_shows_arc_length(self):
        engine = CrownAndCrewEngine(arc_length=7)
        status = engine.get_status()
        assert "/7" in status
        assert "/5" not in status

    def test_end_day_clamps_to_arc(self):
        engine = CrownAndCrewEngine(arc_length=3)
        engine.day = 3
        result = engine.end_day()
        assert engine.day == 4  # arc_length + 1
        assert "journey ends" in result.lower()

    def test_legacy_report_uses_arc_length(self):
        engine = CrownAndCrewEngine(arc_length=7)
        engine.day = 7
        report = engine.generate_legacy_report()
        assert "Days Survived: 7" in report


# =============================================================================
# COUNCIL DILEMMAS CONSOLIDATION
# =============================================================================

class TestCouncilDilemmas:
    def test_module_level_dilemmas_exist(self):
        assert len(COUNCIL_DILEMMAS) == 8

    def test_dilemma_format(self):
        for d in COUNCIL_DILEMMAS:
            assert "prompt" in d
            assert "crown" in d
            assert "crew" in d

    def test_engine_has_council_dilemmas(self):
        engine = CrownAndCrewEngine()
        assert len(engine._council_dilemmas) == 8

    def test_get_council_dilemma_returns_valid(self):
        engine = CrownAndCrewEngine()
        dilemma = engine.get_council_dilemma()
        assert "prompt" in dilemma
        assert "crown" in dilemma
        assert "crew" in dilemma

    def test_get_council_dilemma_no_repeat(self):
        engine = CrownAndCrewEngine()
        seen = set()
        for _ in range(8):
            d = engine.get_council_dilemma()
            seen.add(d["prompt"])
        assert len(seen) == 8, "Expected 8 unique dilemmas before any repeats"

    def test_get_council_dilemma_resets_after_exhaustion(self):
        engine = CrownAndCrewEngine()
        # Exhaust all 8
        for _ in range(8):
            engine.get_council_dilemma()
        # Should still work (resets)
        d = engine.get_council_dilemma()
        assert "prompt" in d

    def test_world_state_injects_custom_dilemmas(self):
        custom = [
            {"prompt": "Custom dilemma", "crown": "Option A", "crew": "Option B"}
        ]
        engine = CrownAndCrewEngine(world_state={"council_dilemmas": custom})
        d = engine.get_council_dilemma()
        assert d["prompt"] == "Custom dilemma"


# =============================================================================
# QUEST ARCHETYPES
# =============================================================================

class TestQuestArchetypes:
    @pytest.fixture(autouse=True)
    def _check_quests_available(self):
        try:
            from codex.games.crown.quests import QUEST_REGISTRY
            self.registry = QUEST_REGISTRY
            self.available = True
        except ImportError:
            self.available = False
            pytest.skip("quests.py not yet available")

    def test_quest_registry_has_seven(self):
        assert len(self.registry) == 7

    def test_quest_slugs(self):
        expected = {"siege", "summit", "trial", "caravan", "heist", "succession", "outbreak"}
        assert set(self.registry.keys()) == expected

    def test_quest_to_world_state(self):
        for slug, quest in self.registry.items():
            ws = quest.to_world_state()
            assert "terms" in ws, f"{slug} missing terms"
            assert "prompts_crown" in ws, f"{slug} missing prompts_crown"
            assert "prompts_crew" in ws, f"{slug} missing prompts_crew"
            assert "prompts_world" in ws, f"{slug} missing prompts_world"
            assert "prompts_campfire" in ws, f"{slug} missing prompts_campfire"
            assert "council_dilemmas" in ws, f"{slug} missing council_dilemmas"
            assert "morning_events" in ws, f"{slug} missing morning_events"

    def test_quest_injection_replaces_terms(self):
        quest = list(self.registry.values())[0]
        ws = quest.to_world_state()
        engine = CrownAndCrewEngine(world_state=ws, arc_length=quest.arc_length)
        # Terms should be from quest, not defaults
        assert engine.terms["crown"] == quest.terms["crown"]
        assert engine.terms["crew"] == quest.terms["crew"]

    def test_each_quest_has_content(self):
        for slug, quest in self.registry.items():
            assert len(quest.prompts_crown) >= 5, f"{slug} needs 5+ crown prompts"
            assert len(quest.prompts_crew) >= 5, f"{slug} needs 5+ crew prompts"
            assert len(quest.prompts_world) >= 5, f"{slug} needs 5+ world prompts"
            assert len(quest.prompts_campfire) >= 5, f"{slug} needs 5+ campfire prompts"
            assert len(quest.morning_events) >= 5, f"{slug} needs 5+ morning events"
            assert len(quest.council_dilemmas) >= 5, f"{slug} needs 5+ dilemmas"
            assert len(quest.patrons) >= 3, f"{slug} needs 3+ patrons"
            assert len(quest.leaders) >= 3, f"{slug} needs 3+ leaders"
            assert quest.secret_witness, f"{slug} needs a secret_witness"

    def test_get_quest(self):
        from codex.games.crown.quests import get_quest
        assert get_quest("siege") is not None
        assert get_quest("nonexistent") is None

    def test_list_quests(self):
        from codex.games.crown.quests import list_quests
        quests = list_quests()
        assert len(quests) == 7


# =============================================================================
# SERIALIZATION
# =============================================================================

class TestSerialization:
    def test_to_dict_from_dict_roundtrip(self):
        engine = CrownAndCrewEngine(arc_length=7)
        engine.declare_allegiance("crew", "HEARTH")
        engine.end_day()
        engine.declare_allegiance("crown", "GUILE")
        engine.get_council_dilemma()

        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)

        assert restored.day == engine.day
        assert restored.sway == engine.sway
        assert restored.arc_length == 7
        assert restored.patron == engine.patron
        assert restored.leader == engine.leader
        assert restored.history == engine.history
        assert restored.dna == engine.dna
        assert restored._used_crown == engine._used_crown
        assert restored._used_dilemmas == engine._used_dilemmas

    def test_from_dict_backward_compat(self):
        """Minimal data (no arc_length) should use defaults."""
        data = {"day": 3, "sway": 1, "patron": "Test", "leader": "Test"}
        engine = CrownAndCrewEngine.from_dict(data)
        assert engine.day == 3
        assert engine.sway == 1
        assert engine.arc_length == 5  # default
        assert engine.rest_type == "long"  # default

    def test_to_dict_includes_all_keys(self):
        engine = CrownAndCrewEngine()
        data = engine.to_dict()
        expected_keys = {
            "day", "sway", "patron", "leader", "history", "dna",
            "vote_log", "arc_length", "rest_type", "rest_config",
            "terms", "entities", "threat", "region", "goal",
            "_used_crown", "_used_crew", "_used_world",
            "_used_campfire", "_used_morning", "_used_dilemmas",
            "_council_dilemmas", "quest_slug", "quest_name",
            "special_mechanics", "_morning_events", "_short_rests_today",
        }
        assert set(data.keys()) == expected_keys


# =============================================================================
# TAROT INTEGRATION
# =============================================================================

class TestTarotIntegration:
    def test_tarot_module_importable(self):
        from codex.integrations.tarot import render_tarot_card, get_card_for_context
        assert callable(render_tarot_card)
        assert callable(get_card_for_context)

    def test_tarot_all_contexts_mapped(self):
        from codex.integrations.tarot import get_card_for_context
        contexts = ["crown", "crew", "campfire", "world", "legacy"]
        for ctx in contexts:
            card_key = get_card_for_context(ctx)
            assert card_key, f"No card mapped for context '{ctx}'"


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

class TestBackwardCompat:
    def test_default_5_day_campaign_unchanged(self):
        """Full 5-day default campaign behaves identically to v3.0."""
        engine = CrownAndCrewEngine()
        choices = [
            ("crew", "HEARTH"),
            ("crew", "DEFIANCE"),
            ("crown", "GUILE"),
            ("crew", "BLOOD"),
            ("crew", "BLOOD"),
        ]

        for side, tag in choices:
            engine.declare_allegiance(side, tag)
            engine.get_prompt()
            engine.get_world_prompt()
            if not engine.is_breach_day():
                engine.get_campfire_prompt()
            engine.end_day()

        assert engine.day == 6  # Past arc_length
        assert engine.get_alignment() in ("CROWN", "CREW", "DRIFTER")
        report = engine.generate_legacy_report()
        assert "CHARACTER RECEIPT" in report

    def test_breach_day_3_for_default_arc(self):
        engine = CrownAndCrewEngine()  # arc_length=5
        engine.day = 3
        assert engine.is_breach_day()

    def test_morning_events_still_work(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        assert "text" in event
        assert "bias" in event
        assert event["bias"] in ("crown", "crew", "neutral")

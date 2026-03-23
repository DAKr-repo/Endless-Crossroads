"""Tests for codex.core.services.opening_narration."""

import pytest
from dataclasses import dataclass


@dataclass
class MockSceneData:
    """Minimal SceneData mock for testing."""
    read_aloud: str = ""
    description: str = ""


class TestOpeningNarration:
    """Test generate_opening_narration() and helpers."""

    def test_module_narration_uses_read_aloud(self):
        from codex.core.services.opening_narration import generate_opening_narration
        scene = MockSceneData(read_aloud="A thunderous concussion shakes the house.")
        result = generate_opening_narration(system_id="candela", scene_data=scene)
        assert result.read_aloud == "A thunderous concussion shakes the house."
        assert result.has_module is True

    def test_falls_back_to_description_when_no_read_aloud(self):
        from codex.core.services.opening_narration import generate_opening_narration
        scene = MockSceneData(description="A modest parlor, mid-evening.")
        result = generate_opening_narration(system_id="candela", scene_data=scene)
        assert result.read_aloud == "A modest parlor, mid-evening."
        assert result.has_module is True

    def test_fallback_when_no_module(self):
        from codex.core.services.opening_narration import generate_opening_narration
        result = generate_opening_narration(system_id="candela", scene_data=None)
        assert result.has_module is False
        assert len(result.read_aloud) > 0
        assert "Lightkeeper" in result.gm_title

    def test_fallback_for_all_systems(self):
        from codex.core.services.opening_narration import generate_opening_narration
        systems = ["candela", "bitd", "sav", "bob", "cbrpnk", "dnd5e", "stc",
                    "burnwillow", "crown", "ashburn"]
        for sys_id in systems:
            result = generate_opening_narration(system_id=sys_id, scene_data=None)
            assert len(result.read_aloud) > 0, f"No fallback hook for {sys_id}"

    def test_mimir_enhancement_appended(self):
        from codex.core.services.opening_narration import generate_opening_narration
        scene = MockSceneData(read_aloud="The gaslights flicker.")

        def mock_mimir(prompt, **kw):
            return "Rain hammers the cobblestones outside."

        result = generate_opening_narration(
            system_id="candela", scene_data=scene,
            mimir_fn=mock_mimir, thermal_ok=True,
        )
        assert result.atmosphere == "Rain hammers the cobblestones outside."
        assert result.read_aloud == "The gaslights flicker."

    def test_mimir_failure_still_has_read_aloud(self):
        from codex.core.services.opening_narration import generate_opening_narration
        scene = MockSceneData(read_aloud="The gaslights flicker.")

        def mock_mimir_fail(prompt, **kw):
            raise TimeoutError("Ollama timeout")

        result = generate_opening_narration(
            system_id="candela", scene_data=scene,
            mimir_fn=mock_mimir_fail, thermal_ok=True,
        )
        assert result.atmosphere == ""
        assert result.read_aloud == "The gaslights flicker."

    def test_mimir_meta_commentary_rejected(self):
        from codex.core.services.opening_narration import generate_opening_narration
        scene = MockSceneData(read_aloud="The gaslights flicker.")

        def mock_mimir_meta(prompt, **kw):
            return "As an AI language model, I cannot set scenes."

        result = generate_opening_narration(
            system_id="candela", scene_data=scene,
            mimir_fn=mock_mimir_meta, thermal_ok=True,
        )
        assert result.atmosphere == ""

    def test_thermal_critical_skips_mimir(self):
        from codex.core.services.opening_narration import generate_opening_narration
        scene = MockSceneData(read_aloud="The gaslights flicker.")
        called = []

        def mock_mimir_track(prompt, **kw):
            called.append(True)
            return "Should not be called."

        result = generate_opening_narration(
            system_id="candela", scene_data=scene,
            mimir_fn=mock_mimir_track, thermal_ok=False,
        )
        assert len(called) == 0
        assert result.atmosphere == ""

    def test_all_systems_have_gm_title(self):
        from codex.core.services.opening_narration import get_gm_title
        systems = ["candela", "bitd", "sav", "bob", "cbrpnk", "dnd5e", "stc",
                    "burnwillow", "crown", "ashburn"]
        for sys_id in systems:
            title = get_gm_title(sys_id)
            assert len(title) > 0, f"No GM title for {sys_id}"

    def test_candela_is_lightkeeper(self):
        from codex.core.services.opening_narration import get_gm_title
        assert get_gm_title("candela") == "Lightkeeper"

    def test_dnd5e_is_dungeon_master(self):
        from codex.core.services.opening_narration import get_gm_title
        assert get_gm_title("dnd5e") == "Dungeon Master"

    def test_bob_is_marshal(self):
        from codex.core.services.opening_narration import get_gm_title
        assert get_gm_title("bob") == "Marshal"


class TestFormatReadAloud:
    """Test formatting functions."""

    def test_format_panel_with_atmosphere(self):
        from codex.core.services.opening_narration import (
            OpeningNarration, format_read_aloud_panel,
        )
        narration = OpeningNarration(
            read_aloud="The door bursts open.",
            atmosphere="Rain hammers the cobblestones.",
            gm_title="Lightkeeper",
        )
        text = format_read_aloud_panel(narration)
        assert "Rain hammers" in text
        assert "The door bursts open." in text

    def test_format_panel_without_atmosphere(self):
        from codex.core.services.opening_narration import (
            OpeningNarration, format_read_aloud_panel,
        )
        narration = OpeningNarration(
            read_aloud="The door bursts open.",
            atmosphere="",
            gm_title="Lightkeeper",
        )
        text = format_read_aloud_panel(narration)
        assert text == "The door bursts open."

    def test_format_scene_read_aloud_returns_none_for_empty(self):
        from codex.core.services.opening_narration import format_scene_read_aloud
        scene = MockSceneData(read_aloud="")
        assert format_scene_read_aloud(scene) is None

    def test_format_scene_read_aloud_returns_text(self):
        from codex.core.services.opening_narration import format_scene_read_aloud
        scene = MockSceneData(read_aloud="Glass crunches underfoot.")
        assert format_scene_read_aloud(scene) == "Glass crunches underfoot."


class TestEngineStateExtraction:
    """Test _extract_engine_state for different systems."""

    def test_candela_state(self):
        from codex.core.services.opening_narration import _extract_engine_state

        class MockCandelaEngine:
            circle_name = "Ichor & Ivy"
            party = []
            memory_shards = []

        parts = _extract_engine_state("candela", MockCandelaEngine())
        assert any("Ichor & Ivy" in p for p in parts)

    def test_bitd_state(self):
        from codex.core.services.opening_narration import _extract_engine_state

        class MockBitdEngine:
            crew_name = "The Lampblacks"
            crew_type = "Shadows"
            heat = 3
            wanted_level = 1
            rep = 5
            coin = 8
            party = []
            memory_shards = []

        parts = _extract_engine_state("bitd", MockBitdEngine())
        assert any("Lampblacks" in p for p in parts)
        assert any("Heat: 3" in p for p in parts)

    def test_bob_state(self):
        from codex.core.services.opening_narration import _extract_engine_state

        class MockLegion:
            supply = 4
            morale = 6
            pressure = 2

        class MockBobEngine:
            legion = MockLegion()
            chosen = "The Horned One"
            campaign_phase = "march"
            fallen_legionnaires = ["Private Ren", "Corporal Sav"]
            party = []
            memory_shards = []

        parts = _extract_engine_state("bob", MockBobEngine())
        assert any("Supply: 4" in p for p in parts)
        assert any("Horned One" in p for p in parts)
        assert any("2 legionnaires" in p for p in parts)

    def test_burnwillow_state(self):
        from codex.core.services.opening_narration import _extract_engine_state

        class MockDoom:
            current = 7
            max_val = 20

        class MockChar:
            name = "Grit"
            current_hp = 12
            max_hp = 20
            stress = 0

        class MockBurnEngine:
            party = [MockChar()]
            doom_clock = MockDoom()
            memory_shards = []

        parts = _extract_engine_state("burnwillow", MockBurnEngine())
        assert any("HP 12/20" in p for p in parts)
        assert any("Doom: 7/20" in p for p in parts)

    def test_empty_engine_returns_empty(self):
        from codex.core.services.opening_narration import _extract_engine_state
        parts = _extract_engine_state("candela", None)
        assert parts == []

    def test_resume_narration_with_engine_state(self):
        from codex.core.services.opening_narration import generate_resume_narration

        class MockEngine:
            circle_name = "Night Watch"
            party = []
            memory_shards = []

        result = generate_resume_narration(
            system_id="candela", engine=MockEngine()
        )
        assert "Night Watch" in result.read_aloud
        assert result.gm_title == "Lightkeeper"

    def test_is_first_session_fresh(self):
        from codex.core.services.opening_narration import is_first_session

        class FreshEngine:
            assignments_completed = 0
            memory_shards = []

        assert is_first_session(FreshEngine()) is True

    def test_is_first_session_resumed(self):
        from codex.core.services.opening_narration import is_first_session

        class ResumedEngine:
            assignments_completed = 1
            memory_shards = [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}]

        assert is_first_session(ResumedEngine()) is False

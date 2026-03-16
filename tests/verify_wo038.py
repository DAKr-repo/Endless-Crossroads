#!/usr/bin/env python3
"""
WORK ORDER 038 — QA VERIFICATION SCRIPT
========================================
Full test suite for Ashburn Module & Deep World Engine

Test Protocols:
- PROTOCOL A: Ashburn Module Tests (12 tests)
- PROTOCOL B: Deep World Engine Tests (4 tests)
- PROTOCOL C: Integration Tests (2 tests)

Total: 18 tests
"""

import sys
import asyncio
import json
import random
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from codex.games.crown.ashburn import AshburnHeirEngine, LEADERS
from codex.games.crown.engine import CrownAndCrewEngine, TAGS
from codex.world.world_wizard import WorldState


# ═══════════════════════════════════════════════════════════════════════════
# PROTOCOL A: ASHBURN MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_a1_import_instantiation():
    """TEST A1 - Import & Instantiation
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.__init__, __post_init__
    """
    julian = AshburnHeirEngine(heir_name="Julian")
    assert julian.heir_name == "Julian", "Julian heir_name mismatch"
    assert isinstance(julian, AshburnHeirEngine), "Not an AshburnHeirEngine instance"
    assert isinstance(julian, CrownAndCrewEngine), "Not a CrownAndCrewEngine subclass"

    rowan = AshburnHeirEngine(heir_name="Rowan")
    assert rowan.heir_name == "Rowan", "Rowan heir_name mismatch"


def test_a2_heir_starting_bonuses():
    """TEST A2 - Heir Starting Bonuses
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.__post_init__
    """
    # Julian: Legacy Name ability gives -1 sway (Crown lean)
    julian = AshburnHeirEngine(heir_name="Julian")
    assert julian.sway == -1, f"Julian sway should be -1, got {julian.sway}"
    assert julian.leader_ability == LEADERS["Julian"]["ability"], "Julian ability mismatch"

    # Rowan: No sway bonus
    rowan = AshburnHeirEngine(heir_name="Rowan")
    assert rowan.sway == 0, f"Rowan sway should be 0, got {rowan.sway}"
    assert rowan.leader_ability == LEADERS["Rowan"]["ability"], "Rowan ability mismatch"


def test_a3_legacy_check_distribution():
    """TEST A3 - Legacy Check Distribution
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.generate_legacy_check

    Probabilistic test: expected trigger rate is ~33% (rolls 5-6 on d6).
    Uses a generous 10%-60% acceptance band over 100 trials to avoid flakiness.
    """
    engine = AshburnHeirEngine(heir_name="Julian")

    trigger_count = 0
    non_trigger_count = 0

    for _ in range(100):
        check = engine.generate_legacy_check()
        assert isinstance(check, dict), "Legacy check must return dict"
        assert "triggered" in check, "Legacy check must have 'triggered' key"
        assert "roll" in check, "Legacy check must have 'roll' key"

        if check["triggered"]:
            trigger_count += 1
            assert "prompt" in check, "Triggered check must have 'prompt' key"
            assert isinstance(check["prompt"], str), "Prompt must be string"
            assert len(check["prompt"]) > 0, "Prompt must be non-empty"
        else:
            non_trigger_count += 1

    # Expected: rolls 5-6 trigger (~33%). Allow 10%-60% range for random variance.
    trigger_rate = trigger_count / 100
    assert 0.10 <= trigger_rate <= 0.60, (
        f"Trigger rate {trigger_rate*100:.1f}% ({trigger_count}/100) is outside "
        f"the expected 10%-60% range. May indicate a broken distribution."
    )


def test_a4_legacy_choice_resolution_obey():
    """TEST A4 - Legacy Choice Resolution (Obey)
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.resolve_legacy_choice (async)
    """
    engine = AshburnHeirEngine(heir_name="Lydia")
    initial_corruption = 0
    initial_sway = 0
    engine.legacy_corruption = initial_corruption
    engine.sway = initial_sway

    result = asyncio.run(engine.resolve_legacy_choice(1))  # Obey

    assert isinstance(result, dict), f"Result must be dict, got {type(result).__name__}"
    assert engine.legacy_corruption == initial_corruption + 1, (
        f"Corruption should be {initial_corruption + 1}, got {engine.legacy_corruption}"
    )
    assert engine.sway == initial_sway - 1, (
        f"Sway should be {initial_sway - 1}, got {engine.sway}"
    )


def test_a5_legacy_choice_resolution_lie():
    """TEST A5 - Legacy Choice Resolution (Lie - Success/Detected)
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.resolve_legacy_choice

    Probabilistic test: detection roll is 1-2 on d6 (~33%). Over 20 trials,
    both outcomes (success and detection) are expected to appear. The assertion
    requires both paths to appear, which has a (2/3)^20 + (1/3)^20 < 0.004
    probability of failure (both-or-neither outcomes). Acceptable for CI.
    """
    success_count = 0
    detected_count = 0

    for _ in range(20):
        engine = AshburnHeirEngine(heir_name="Lydia")
        engine.legacy_corruption = 0
        engine.sway = 0

        result = asyncio.run(engine.resolve_legacy_choice(2))  # Lie

        # Sway should always increase
        assert engine.sway == 1, f"Sway should be 1 after lie, got {engine.sway}"

        if engine.legacy_corruption == 0:
            success_count += 1
        elif engine.legacy_corruption == 2:
            detected_count += 1
        else:
            raise AssertionError(f"Unexpected corruption value: {engine.legacy_corruption}")

    # Both outcomes must appear at least once across 20 trials.
    # Failure probability is negligible (~0.4%). If this is flaky in practice,
    # increase trials to 50.
    assert success_count > 0, (
        f"Lie success path never triggered in 20 trials "
        f"(detected={detected_count}/20). Distribution may be broken."
    )
    assert detected_count > 0, (
        f"Lie detection path never triggered in 20 trials "
        f"(success={success_count}/20). Distribution may be broken."
    )


def test_a6_corruption_boundary_game_over():
    """TEST A6 - Corruption Boundary & Game Over
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.check_betrayal, add_corruption
    """
    engine = AshburnHeirEngine(heir_name="Lydia")
    engine.legacy_corruption = 4

    # Should not trigger at 4
    result_at_4 = engine.check_betrayal()
    assert result_at_4 is None, (
        f"Game over should not trigger at corruption 4, got {result_at_4}"
    )

    # Add 1 corruption to reach 5
    result_at_5 = engine.add_corruption(1)

    assert result_at_5 is not None, "Game over should trigger at corruption 5"
    assert isinstance(result_at_5, dict), "Game over result must be dict"
    assert result_at_5.get("game_over") is True, "game_over flag must be True"
    assert "message" in result_at_5, "Game over result must have 'message' key"
    assert "SOLARIUM" in result_at_5["message"], "Game over message should mention SOLARIUM"


def test_a7_corruption_clamping():
    """TEST A7 - Corruption Clamping
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.add_corruption, resolve_legacy_choice
    """
    engine = AshburnHeirEngine(heir_name="Lydia")

    # Try to add corruption above 5
    engine.legacy_corruption = 4
    engine.add_corruption(3)  # Would be 7, should clamp to 5

    assert engine.legacy_corruption == 5, (
        f"Corruption should clamp at 5, got {engine.legacy_corruption}"
    )

    # Check that manual sub-zero assignment followed by a no-op add doesn't crash.
    # The system doesn't have explicit lower bounds; corruption starts at 0 and
    # only increases through normal gameplay.
    engine.legacy_corruption = -1  # Manually set (shouldn't happen in normal play)
    engine.add_corruption(0)  # No-op


def test_a8_betrayal_nullification():
    """TEST A8 - Betrayal Nullification
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.get_vote_power
    """
    engine = AshburnHeirEngine(heir_name="Rowan")
    engine.sway = 3  # Crew Loyal = weight 8

    # Normal vote power
    normal_power = engine.get_vote_power()
    assert normal_power == 8, f"Vote power at sway 3 should be 8, got {normal_power}"

    # Enable betrayal
    engine.betrayal_triggered = True
    nullified_power = engine.get_vote_power()

    assert nullified_power == 1, (
        f"Vote power after betrayal should be 1, got {nullified_power}"
    )


def test_a9_prompt_override():
    """TEST A9 - Prompt Override
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.get_prompt
    """
    engine = AshburnHeirEngine(heir_name="Julian")

    # Declare allegiance first (required by get_prompt)
    engine.declare_allegiance("crown")
    crown_prompt = engine.get_prompt("crown")

    assert isinstance(crown_prompt, str), "Crown prompt must be string"
    assert len(crown_prompt) > 0, "Crown prompt must be non-empty"

    # Test crew side
    engine.declare_allegiance("crew")
    crew_prompt = engine.get_prompt("crew")

    assert isinstance(crew_prompt, str), "Crew prompt must be string"
    assert len(crew_prompt) > 0, "Crew prompt must be non-empty"


def test_a10_save_load_round_trip():
    """TEST A10 - Save/Load Round-Trip
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.to_dict, from_dict
    """
    original = AshburnHeirEngine(heir_name="Rowan")
    original.legacy_corruption = 3
    original.sway = 2
    original.day = 4
    original.betrayal_triggered = True

    # Serialize
    save_data = original.to_dict()

    assert isinstance(save_data, dict), "to_dict must return dict"
    assert "legacy_corruption" in save_data, "Save data missing legacy_corruption"
    assert "heir_name" in save_data, "Save data missing heir_name"
    assert "betrayal_triggered" in save_data, "Save data missing betrayal_triggered"
    assert "engine_type" in save_data, "Save data missing engine_type flag"
    assert save_data["engine_type"] == "ashburn", (
        f"engine_type should be 'ashburn', got {save_data['engine_type']}"
    )

    # Deserialize
    restored = AshburnHeirEngine.from_dict(save_data)

    assert restored.heir_name == "Rowan", f"heir_name mismatch: {restored.heir_name}"
    assert restored.legacy_corruption == 3, f"corruption mismatch: {restored.legacy_corruption}"
    assert restored.sway == 2, f"sway mismatch: {restored.sway}"
    assert restored.day == 4, f"day mismatch: {restored.day}"
    assert restored.betrayal_triggered is True, (
        f"betrayal_triggered mismatch: {restored.betrayal_triggered}"
    )


def test_a11_parent_method_inheritance():
    """TEST A11 - Parent Method Inheritance
    FILE(S): ashburn_crew_module.py, codex_crown_module.py
    FUNCTION(S): declare_allegiance, resolve_vote, get_vote_power
    """
    engine = AshburnHeirEngine(heir_name="Julian")

    # Test declare_allegiance
    result = engine.declare_allegiance("crew", "HEARTH")
    assert isinstance(result, str), "declare_allegiance must return string"
    assert engine.sway == 0, (
        f"Sway should be 0 after crew allegiance (Julian starts at -1), got {engine.sway}"
    )

    # Test get_vote_power (inherited, but overridden for betrayal)
    power = engine.get_vote_power()
    assert isinstance(power, int), "get_vote_power must return int"

    # Test resolve_vote
    vote_result = engine.resolve_vote({"crown": 1, "crew": 0})
    assert isinstance(vote_result, dict), "resolve_vote must return dict"
    assert "winner" in vote_result, "vote result missing 'winner' key"


def test_a12_rich_status_panel():
    """TEST A12 - Rich Status Panel
    FILE(S): ashburn_crew_module.py
    FUNCTION(S): AshburnHeirEngine.get_heir_status
    """
    for corruption_level in [0, 3, 5]:
        engine = AshburnHeirEngine(heir_name="Lydia")
        engine.legacy_corruption = corruption_level

        status = engine.get_heir_status()

        # get_heir_status returns a Rich renderable; verify it doesn't crash
        # and returns something non-None at every corruption level.
        assert status is not None, (
            f"Status panel is None at corruption {corruption_level}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# PROTOCOL B: DEEP WORLD ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_b1_world_state_new_fields():
    """TEST B1 - WorldState New Fields
    FILE(S): codex_world_engine.py
    FUNCTION(S): WorldState.to_dict, from_dict
    """
    world = WorldState(
        name="Test World",
        system_id="test",
        system_display="Test System",
        tone="gritty",
        genre="Fantasy",
        grapes={
            "geography": "Mountains and valleys",
            "religion": "Polytheistic",
            "achievements": "Iron age",
            "politics": "Feudal",
            "economics": "Barter-based",
            "social": "Caste system"
        },
        bible_text="This is a test setting bible."
    )

    # Serialize
    world_dict = world.to_dict()

    assert "grapes" in world_dict, "to_dict missing 'grapes' field"
    assert "bible_text" in world_dict, "to_dict missing 'bible_text' field"
    assert isinstance(world_dict["grapes"], dict), "grapes must be dict"
    assert isinstance(world_dict["bible_text"], str), "bible_text must be str"

    # Deserialize
    restored = WorldState.from_dict(world_dict)

    assert restored.grapes == world.grapes, "grapes data mismatch"
    assert restored.bible_text == world.bible_text, "bible_text mismatch"


def test_b2_backward_compatibility():
    """TEST B2 - Backward Compatibility
    FILE(S): codex_world_engine.py
    FUNCTION(S): WorldState.from_dict
    """
    # Create old-style WorldState dict without new fields
    old_world_dict = {
        "name": "Old World",
        "system_id": "old",
        "system_display": "Old System",
        "tone": "heroic",
        "genre": "High Fantasy",
        "terms": {},
        "primer": "An old world.",
        "prompts_crown": [],
        "prompts_crew": [],
        "prompts_world": [],
        "prompts_campfire": [],
        "secret_witness": "",
        "patrons": [],
        "leaders": [],
        "created_timestamp": 0.0,
        # Note: NO 'grapes' or 'bible_text' fields
    }

    # Should not crash
    restored = WorldState.from_dict(old_world_dict)

    assert isinstance(restored.grapes, dict), "grapes should default to dict"
    assert restored.grapes == {}, "grapes should default to empty dict"
    assert isinstance(restored.bible_text, str), "bible_text should default to str"
    assert restored.bible_text == "", "bible_text should default to empty string"


def test_b3_grapes_data_integrity():
    """TEST B3 - G.R.A.P.E.S. Data Integrity
    FILE(S): codex_world_engine.py
    FUNCTION(S): WorldState.to_dict, from_dict
    """
    world = WorldState(
        name="GRAPES World",
        system_id="test",
        system_display="Test",
        tone="gritty",
        genre="Fantasy",
        grapes={
            "geography": "Rolling hills and deep forests",
            "religion": "Nature spirits and ancestor worship",
            "achievements": "Early metallurgy, written language",
            "politics": "Tribal confederacy with elected chiefs",
            "economics": "Mixed economy with trade guilds",
            "social": "Meritocratic with strong family ties"
        }
    )

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(world.to_dict(), f)
        temp_path = f.name

    try:
        with open(temp_path, 'r') as f:
            loaded_dict = json.load(f)

        restored = WorldState.from_dict(loaded_dict)

        grapes_keys = ["geography", "religion", "achievements", "politics", "economics", "social"]
        for key in grapes_keys:
            assert key in restored.grapes, f"Missing G.R.A.P.E.S. key: {key}"
            assert restored.grapes[key] == world.grapes[key], f"Mismatch in {key}"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_b4_world_save_load_with_ashburn_data():
    """TEST B4 - World Save/Load with Ashburn Data
    FILE(S): codex_world_engine.py
    FUNCTION(S): WorldState.to_dict, from_dict
    """
    ashburn_world = WorldState(
        name="Ashburn Academy",
        system_id="custom",
        system_display="Gothic Boarding School",
        tone="gothic",
        genre="Gothic Horror",
        terms={
            "crown": "The Board",
            "crew": "The Students",
            "neutral": "The Heir",
            "campfire": "The Study",
            "world": "The Grounds"
        },
        grapes={
            "geography": "A gothic academy on foggy moors",
            "religion": "Old traditions mixed with modern secularism",
            "achievements": "Victorian era technology",
            "politics": "Autocratic Board of Regents",
            "economics": "Endowment-based wealth",
            "social": "Rigid class hierarchy"
        }
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(ashburn_world.to_dict(), f)
        temp_path = f.name

    try:
        with open(temp_path, 'r') as f:
            loaded_dict = json.load(f)

        restored = WorldState.from_dict(loaded_dict)

        assert restored.terms["crown"] == "The Board", "Crown term mismatch"
        assert restored.terms["crew"] == "The Students", "Crew term mismatch"
        assert "geography" in restored.grapes, "geography missing"
        assert "Ashburn" in restored.name, "Name mismatch"
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# PROTOCOL C: INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_c1_ashburn_world_injection():
    """TEST C1 - Ashburn + World Injection
    FILE(S): ashburn_crew_module.py, codex_world_engine.py
    FUNCTION(S): AshburnHeirEngine.__init__, WorldState.to_dict
    """
    ashburn_world = WorldState(
        name="Ashburn Academy",
        system_id="custom",
        system_display="Gothic Boarding School",
        tone="gothic",
        genre="Gothic Horror",
        terms={
            "crown": "The Board",
            "crew": "The Students",
            "neutral": "The Heir",
            "campfire": "The Study",
            "world": "The Grounds"
        }
    )

    # Inject into Ashburn engine
    engine = AshburnHeirEngine(
        heir_name="Julian",
        world_state=ashburn_world.to_dict()
    )

    assert engine.terms["crown"] == "The Board", (
        f"Crown term not injected: {engine.terms['crown']}"
    )
    assert engine.terms["crew"] == "The Students", (
        f"Crew term not injected: {engine.terms['crew']}"
    )
    assert engine.legacy_corruption == 0, "Corruption should be 0"
    assert engine.sway == -1, "Julian should start at -1 sway"
    assert engine.heir_name == "Julian", "Heir name mismatch"


def test_c2_political_gravity_with_corruption():
    """TEST C2 - Political Gravity with Corruption
    FILE(S): ashburn_crew_module.py, codex_crown_module.py
    FUNCTION(S): get_vote_power, resolve_vote
    """
    engine = AshburnHeirEngine(heir_name="Rowan")
    engine.sway = 3  # Crew Loyal = weight 8

    # Simulate a vote where crew should win due to political gravity
    vote_result = engine.resolve_vote({"crown": 3, "crew": 1})

    assert vote_result["winner"] == "crew", (
        f"Crew should win with weight 8, got {vote_result['winner']}"
    )
    assert vote_result["crew_power"] == 8, (
        f"Crew power should be 8, got {vote_result['crew_power']}"
    )
    assert vote_result["crown_power"] == 3, (
        f"Crown power should be 3, got {vote_result['crown_power']}"
    )

    # Now trigger betrayal
    engine.betrayal_triggered = True
    vote_result_betrayed = engine.resolve_vote({"crown": 3, "crew": 1})

    # With betrayal, crew weight drops to 1, so crown wins
    assert vote_result_betrayed["winner"] == "crown", (
        f"Crown should win after betrayal, got {vote_result_betrayed['winner']}"
    )
    assert vote_result_betrayed["crew_power"] == 1, (
        f"Crew power should be 1 after betrayal, got {vote_result_betrayed['crew_power']}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    all_tests = [
        test_a1_import_instantiation,
        test_a2_heir_starting_bonuses,
        test_a3_legacy_check_distribution,
        test_a4_legacy_choice_resolution_obey,
        test_a5_legacy_choice_resolution_lie,
        test_a6_corruption_boundary_game_over,
        test_a7_corruption_clamping,
        test_a8_betrayal_nullification,
        test_a9_prompt_override,
        test_a10_save_load_round_trip,
        test_a11_parent_method_inheritance,
        test_a12_rich_status_panel,
        test_b1_world_state_new_fields,
        test_b2_backward_compatibility,
        test_b3_grapes_data_integrity,
        test_b4_world_save_load_with_ashburn_data,
        test_c1_ashburn_world_injection,
        test_c2_political_gravity_with_corruption,
    ]

    passed = []
    failed = []

    for test_fn in all_tests:
        try:
            test_fn()
            passed.append(test_fn.__name__)
            print(f"PASS  {test_fn.__name__}")
        except Exception as exc:
            failed.append((test_fn.__name__, exc))
            print(f"FAIL  {test_fn.__name__}: {exc}")

    print()
    print(f"Results: {len(passed)} passed, {len(failed)} failed out of {len(all_tests)} tests")

    if failed:
        print()
        print("FAILED TESTS:")
        for name, exc in failed:
            print(f"  [{name}] {exc}")
        sys.exit(1)
    else:
        print("All tests passed.")
        sys.exit(0)

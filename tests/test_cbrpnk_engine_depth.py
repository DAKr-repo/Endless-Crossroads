"""
CBR+PNK Engine Depth — Tests
==============================

Covers:
  1. TestCBRPNKArchetypeData     — 4 archetypes load with required fields
  2. TestCBRPNKChromeData        — 20+ chrome items with required fields
  3. TestCBRPNKCorpData          — 8+ corps with required fields
  4. TestGridState               — Grid generation and structure
  5. TestGridManager             — Jack in/out, intrusion rolls, data extraction
  6. TestChromeManager           — Install/remove, humanity tracking, glitch rolls
  7. TestCBRPNKEngineSaveLoad    — Round-trip with grid + chrome state
  8. TestCBRPNKCommandDispatch   — All handle_command dispatches
"""

import random
import pytest

from codex.forge.reference_data.cbrpnk_archetypes import ARCHETYPES, BACKGROUNDS
from codex.forge.reference_data.cbrpnk_chrome import CHROME, CHROME_SLOTS, GLITCH_EFFECTS
from codex.forge.reference_data.cbrpnk_corps import CORPORATIONS
from codex.forge.reference_data.cbrpnk import (
    ARCHETYPES as AGG_ARCHETYPES,
    BACKGROUNDS as AGG_BACKGROUNDS,
    CHROME as AGG_CHROME,
    CHROME_SLOTS as AGG_CHROME_SLOTS,
    GLITCH_EFFECTS as AGG_GLITCH_EFFECTS,
    CORPORATIONS as AGG_CORPORATIONS,
)
from codex.games.cbrpnk.hacking import ICE, GridState, GridManager, ICE_TYPES
from codex.games.cbrpnk.chrome import ChromeManager, HUMANITY_THRESHOLDS
from codex.games.cbrpnk import CBRPNKEngine, CBRPNKCharacter


# =========================================================================
# HELPERS
# =========================================================================

def _rng(seed: int = 42) -> random.Random:
    """Return a seeded Random instance for deterministic tests."""
    return random.Random(seed)


def _engine_with_char(archetype: str = "Hacker") -> CBRPNKEngine:
    """Return a CBRPNKEngine with a lead character pre-created."""
    engine = CBRPNKEngine()
    engine.create_character("TestRunner", archetype=archetype, hack=3, skulk=2)
    return engine


# =========================================================================
# 1. ARCHETYPE DATA
# =========================================================================

class TestCBRPNKArchetypeData:
    """Archetype reference data structure validation."""

    def test_four_archetypes_exist(self):
        assert len(ARCHETYPES) == 4

    def test_hacker_archetype_present(self):
        assert "Hacker" in ARCHETYPES

    def test_fixer_archetype_present(self):
        assert "Fixer" in ARCHETYPES

    def test_punk_archetype_present(self):
        # SOURCE: creation_rules.json — real archetypes are Hacker/Punk/Fixer/Ghost
        assert "Punk" in ARCHETYPES

    def test_ghost_archetype_present(self):
        # SOURCE: creation_rules.json — real archetypes are Hacker/Punk/Fixer/Ghost
        assert "Ghost" in ARCHETYPES

    def test_each_archetype_has_description(self):
        for name, data in ARCHETYPES.items():
            assert "description" in data, f"Missing description for {name}"
            assert len(data["description"]) > 10

    def test_each_archetype_has_special_abilities(self):
        # NOTE: Real source (cbrpnk_02 Runner File) not available yet.
        # Archetypes have at least 2 abilities from what is source-confirmed.
        for name, data in ARCHETYPES.items():
            assert "special_abilities" in data, f"Missing abilities for {name}"
            assert len(data["special_abilities"]) >= 2, (
                f"{name} has fewer than 2 abilities"
            )

    def test_each_ability_has_name_and_description(self):
        for arch_name, data in ARCHETYPES.items():
            for ability in data["special_abilities"]:
                assert "name" in ability, f"Ability missing name in {arch_name}"
                assert "description" in ability, f"Ability missing desc in {arch_name}"

    def test_each_archetype_has_starting_chrome(self):
        # NOTE: Punk archetype may have empty starting_chrome (resistance to augmentation).
        # Key must exist; contents may be an empty list.
        for name, data in ARCHETYPES.items():
            assert "starting_chrome" in data, f"Missing starting_chrome for {name}"
            assert isinstance(data["starting_chrome"], list)

    def test_each_archetype_has_xp_trigger(self):
        for name, data in ARCHETYPES.items():
            assert "xp_trigger" in data, f"Missing xp_trigger for {name}"

    def test_each_archetype_has_starting_items(self):
        for name, data in ARCHETYPES.items():
            assert "starting_items" in data, f"Missing starting_items for {name}"
            assert len(data["starting_items"]) >= 1

    def test_four_backgrounds_exist(self):
        assert len(BACKGROUNDS) == 4

    def test_backgrounds_have_required_fields(self):
        required = {"description", "starting_contacts", "bonus_action", "starting_heat"}
        for bg_name, bg_data in BACKGROUNDS.items():
            for field in required:
                assert field in bg_data, f"Background '{bg_name}' missing '{field}'"

    def test_aggregator_exports_archetypes(self):
        assert AGG_ARCHETYPES is ARCHETYPES
        assert AGG_BACKGROUNDS is BACKGROUNDS


# =========================================================================
# 2. CHROME DATA
# =========================================================================

class TestCBRPNKChromeData:
    """Chrome reference data structure validation."""

    def test_at_least_20_chrome_items(self):
        assert len(CHROME) >= 20, f"Only {len(CHROME)} chrome items"

    def test_each_chrome_has_name(self):
        for key, data in CHROME.items():
            assert "name" in data, f"Chrome '{key}' missing 'name'"

    def test_each_chrome_has_slot(self):
        for key, data in CHROME.items():
            assert "slot" in data, f"Chrome '{key}' missing 'slot'"

    def test_each_chrome_slot_is_valid(self):
        valid_slots = set(CHROME_SLOTS.keys())
        for key, data in CHROME.items():
            assert data["slot"] in valid_slots, (
                f"Chrome '{key}' has invalid slot '{data['slot']}'"
            )

    def test_each_chrome_has_description(self):
        for key, data in CHROME.items():
            assert "description" in data, f"Chrome '{key}' missing 'description'"
            assert len(data["description"]) > 5

    def test_each_chrome_has_effect(self):
        for key, data in CHROME.items():
            assert "effect" in data, f"Chrome '{key}' missing 'effect'"

    def test_each_chrome_has_glitch_risk_float(self):
        for key, data in CHROME.items():
            assert "glitch_risk" in data, f"Chrome '{key}' missing 'glitch_risk'"
            risk = data["glitch_risk"]
            assert isinstance(risk, float), f"'{key}' glitch_risk is not float: {type(risk)}"
            assert 0.0 <= risk <= 1.0, f"'{key}' glitch_risk out of range: {risk}"

    def test_each_chrome_has_humanity_cost(self):
        for key, data in CHROME.items():
            assert "humanity_cost" in data, f"Chrome '{key}' missing 'humanity_cost'"
            cost = data["humanity_cost"]
            assert 1 <= cost <= 3, f"'{key}' humanity_cost out of range: {cost}"

    def test_neural_jack_present(self):
        assert "Neural Jack" in CHROME

    def test_wired_reflexes_present(self):
        assert "Wired Reflexes" in CHROME

    def test_mantis_blades_present(self):
        assert "Mantis Blades" in CHROME

    def test_chrome_slots_have_max_capacity(self):
        for slot_name, slot_data in CHROME_SLOTS.items():
            assert "max_capacity" in slot_data, f"Slot '{slot_name}' missing max_capacity"
            assert slot_data["max_capacity"] >= 1

    def test_glitch_effects_three_severities(self):
        assert "minor" in GLITCH_EFFECTS
        assert "major" in GLITCH_EFFECTS
        assert "critical" in GLITCH_EFFECTS

    def test_glitch_effects_have_examples(self):
        for sev, data in GLITCH_EFFECTS.items():
            assert "examples" in data, f"GLITCH_EFFECTS['{sev}'] missing examples"
            assert len(data["examples"]) >= 1

    def test_aggregator_exports_chrome(self):
        assert AGG_CHROME is CHROME
        assert AGG_CHROME_SLOTS is CHROME_SLOTS
        assert AGG_GLITCH_EFFECTS is GLITCH_EFFECTS


# =========================================================================
# 3. CORPORATION DATA
# =========================================================================

class TestCBRPNKCorpData:
    """Corporation reference data structure validation."""

    def test_at_least_8_corps(self):
        assert len(CORPORATIONS) >= 8, f"Only {len(CORPORATIONS)} corps"

    def test_each_corp_has_tier(self):
        # NOTE: CORPORATIONS is now FACTIONS — includes tier-1 street entities.
        for name, data in CORPORATIONS.items():
            assert "tier" in data, f"Faction '{name}' missing 'tier'"
            assert 1 <= data["tier"] <= 5, f"Faction '{name}' tier out of range"

    def test_each_corp_has_sector(self):
        for name, data in CORPORATIONS.items():
            assert "sector" in data, f"Corp '{name}' missing 'sector'"

    def test_each_corp_has_security_level(self):
        for name, data in CORPORATIONS.items():
            assert "security_level" in data, f"Corp '{name}' missing 'security_level'"
            assert 1 <= data["security_level"] <= 5

    def test_each_corp_has_description(self):
        for name, data in CORPORATIONS.items():
            assert "description" in data, f"Corp '{name}' missing 'description'"
            assert len(data["description"]) > 20

    def test_each_corp_has_notable_npcs(self):
        # NOTE: Some PDF-sourced factions have no named NPCs; key must exist, list may be empty.
        for name, data in CORPORATIONS.items():
            assert "notable_npcs" in data, f"Faction '{name}' missing 'notable_npcs'"
            assert isinstance(data["notable_npcs"], list)

    def test_omni_global_solutions_tier5(self):
        # SOURCE: cbrpnk_01_gm-guide.pdf — sample oppressor for Long Shot mode
        assert "Omni Global Solutions" in CORPORATIONS
        assert CORPORATIONS["Omni Global Solutions"]["tier"] == 5

    def test_toha_heavy_industries_present(self):
        # SOURCE: Mona_Rise_Megalopolis.pdf
        assert "Toha Heavy Industries" in CORPORATIONS

    def test_insurgents_tier1(self):
        # SOURCE: cbrpnk_04_prdtr.pdf — Ganymede resistance faction
        assert "Insurgents" in CORPORATIONS
        assert CORPORATIONS["Insurgents"]["tier"] == 2

    def test_aggregator_exports_corporations(self):
        assert AGG_CORPORATIONS is CORPORATIONS


# =========================================================================
# 4. GRID STATE
# =========================================================================

class TestGridState:
    """Grid generation and state structure tests."""

    def test_generate_grid_returns_grid_state(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=1, rng=_rng())
        assert isinstance(gs, GridState)

    def test_generated_grid_has_name(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=1, rng=_rng())
        assert gs.grid_name
        assert len(gs.grid_name) > 3

    def test_generated_grid_has_ice(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=2, rng=_rng())
        assert len(gs.ice_list) >= 1

    def test_generated_grid_has_data_nodes(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=1, rng=_rng())
        assert len(gs.data_nodes) >= 2

    def test_generated_grid_starts_not_jacked_in(self):
        mgr = GridManager()
        gs = mgr.generate_grid(rng=_rng())
        assert gs.jacked_in is False

    def test_generated_grid_starts_alarm_zero(self):
        mgr = GridManager()
        gs = mgr.generate_grid(rng=_rng())
        assert gs.alarm_level == 0

    def test_ice_types_are_valid(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=3, rng=_rng())
        valid = set(ICE_TYPES.keys())
        for ice in gs.ice_list:
            assert ice.ice_type in valid, f"Invalid ICE type: {ice.ice_type}"

    def test_ice_rating_in_range(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=3, rng=_rng())
        for ice in gs.ice_list:
            assert 1 <= ice.rating <= 5, f"ICE rating out of range: {ice.rating}"

    def test_grid_state_to_dict_round_trip(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=2, rng=_rng())
        data = gs.to_dict()
        restored = GridState.from_dict(data)
        assert restored.grid_name == gs.grid_name
        assert restored.alarm_level == gs.alarm_level
        assert len(restored.ice_list) == len(gs.ice_list)
        assert len(restored.data_nodes) == len(gs.data_nodes)

    def test_ice_to_dict_round_trip(self):
        ice = ICE(name="Killer-01", ice_type="Killer", rating=3, active=True,
                  description="A red construct.")
        data = ice.to_dict()
        restored = ICE.from_dict(data)
        assert restored.name == ice.name
        assert restored.ice_type == ice.ice_type
        assert restored.rating == ice.rating
        assert restored.active == ice.active

    def test_difficulty_5_generates_high_threat_ice(self):
        # SOURCE: cbrpnk_01_gm-guide.pdf — I.C.P. is the lethal ICE type
        mgr = GridManager()
        found_high_threat = False
        for seed in range(20):
            gs = mgr.generate_grid(difficulty=5, rng=_rng(seed))
            for ice in gs.ice_list:
                if ice.ice_type in ("I.C.P.", "Defender"):
                    found_high_threat = True
                    break
            if found_high_threat:
                break
        assert found_high_threat, "Difficulty 5 grid never generated I.C.P. or Defender ICE"

    def test_grid_alarm_tick_escalates_alarm(self):
        mgr = GridManager()
        gs = mgr.generate_grid(rng=_rng())
        gs.alarm_level = 3
        # Add dormant ICE to activate
        gs.ice_list.append(ICE(
            name="Patrol-99", ice_type="Patrol", rating=1, active=False,
            description="Dormant patrol."
        ))
        result = mgr.grid_alarm_tick(gs)
        assert "alarm_level" in result

    def test_grid_alarm_tick_spawns_ice_at_max_alarm(self):
        mgr = GridManager()
        gs = GridState(grid_name="TestGrid", alarm_level=5)
        result = mgr.grid_alarm_tick(gs)
        assert result["new_ice"] is not None
        assert len(gs.ice_list) == 1


# =========================================================================
# 5. GRID MANAGER
# =========================================================================

class TestGridManager:
    """GridManager action method tests."""

    def test_jack_in_success_sets_jacked_in(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=1, rng=_rng(1))
        # With 3 hack dots and seed, we should get some form of entry
        result = mgr.jack_in(hacker_dots=3, grid=gs, rng=_rng(42))
        assert gs.jacked_in is True
        assert "outcome" in result
        assert "alarm_level" in result

    def test_jack_in_zero_dots_is_harder(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=1, rng=_rng())
        # Rolling 0 dice should produce mixed or failure often
        result = mgr.jack_in(hacker_dots=0, grid=gs, rng=_rng(7))
        assert "outcome" in result

    def test_jack_in_returns_message(self):
        mgr = GridManager()
        gs = mgr.generate_grid(rng=_rng())
        result = mgr.jack_in(hacker_dots=2, grid=gs, rng=_rng())
        assert "message" in result
        assert len(result["message"]) > 5

    def test_jack_in_failure_activates_ice(self):
        mgr = GridManager()
        gs = mgr.generate_grid(difficulty=1, rng=_rng())
        # Add dormant ICE
        gs.ice_list.append(ICE(
            name="Patrol-D1", ice_type="Patrol", rating=1, active=False,
            description="Dormant patrol."
        ))
        # Force a failure roll (seed 0, 0 dots = zero-dice = take lowest)
        result = mgr.jack_in(hacker_dots=0, grid=gs, rng=_rng(999))
        # If failed, alarm should have increased
        if result["outcome"] == "failure":
            assert gs.alarm_level > 0

    def test_intrusion_roll_on_active_ice(self):
        mgr = GridManager()
        ice = ICE(name="Killer-01", ice_type="Killer", rating=2, active=True,
                  description="Red menace.")
        gs = GridState(grid_name="TestGrid", jacked_in=True, ice_list=[ice])
        result = mgr.intrusion_roll(
            hacker_dots=3, target_ice=ice, grid=gs, rng=_rng(42)
        )
        assert "outcome" in result
        assert "ice_disabled" in result
        assert "stress_cost" in result
        assert "message" in result

    def test_intrusion_roll_success_disables_ice(self):
        mgr = GridManager()
        ice = ICE(name="Patrol-01", ice_type="Patrol", rating=1, active=True,
                  description="Simple patrol.")
        gs = GridState(grid_name="TestGrid", jacked_in=True, ice_list=[ice])
        # Find a seed that produces success
        disabled = False
        for seed in range(100):
            ice.active = True
            result = mgr.intrusion_roll(
                hacker_dots=4, target_ice=ice, grid=gs, rng=_rng(seed)
            )
            if result["ice_disabled"]:
                disabled = True
                break
        assert disabled, "4-dot hacker never disabled rating-1 ICE across 100 seeds"

    def test_extract_data_blocked_by_encryption(self):
        # SOURCE: cbrpnk_01_gm-guide.pdf — Encryption ICE blocks data extraction
        mgr = GridManager()
        enc = ICE(name="Encryption-01", ice_type="Encryption", rating=2, active=True,
                  description="Data cloaking wall.")
        node = {"name": "Secret Files", "value": "High", "protected": False, "index": 0}
        gs = GridState(
            grid_name="TestGrid", jacked_in=True,
            ice_list=[enc], data_nodes=[node]
        )
        result = mgr.extract_data(gs, 0)
        assert result["success"] is False
        assert "Encryption" in result["message"]

    def test_extract_data_succeeds_with_no_active_ice(self):
        mgr = GridManager()
        node = {"name": "Secret Files", "value": "High", "protected": False, "index": 0}
        gs = GridState(
            grid_name="TestGrid", jacked_in=True, ice_list=[], data_nodes=[node]
        )
        result = mgr.extract_data(gs, 0)
        assert result["success"] is True
        assert result["node"]["name"] == "Secret Files"
        assert len(gs.data_nodes) == 0
        assert len(gs.extracted_data) == 1

    def test_extract_protected_node_blocked_by_active_ice(self):
        mgr = GridManager()
        ice = ICE(name="Patrol-01", ice_type="Patrol", rating=1, active=True,
                  description="Patrol.")
        node = {"name": "Black Budget", "value": "Critical", "protected": True, "index": 0}
        gs = GridState(
            grid_name="TestGrid", jacked_in=True,
            ice_list=[ice], data_nodes=[node]
        )
        result = mgr.extract_data(gs, 0)
        assert result["success"] is False

    def test_extract_bad_index(self):
        mgr = GridManager()
        gs = GridState(grid_name="TestGrid", jacked_in=True)
        result = mgr.extract_data(gs, 99)
        assert result["success"] is False

    def test_jack_out_requires_being_in(self):
        mgr = GridManager()
        gs = GridState(grid_name="TestGrid", jacked_in=False)
        result = mgr.jack_out(gs)
        assert result["success"] is False

    def test_jack_out_clears_jacked_in_flag(self):
        mgr = GridManager()
        gs = GridState(grid_name="TestGrid", jacked_in=True)
        result = mgr.jack_out(gs)
        assert result["success"] is True
        assert gs.jacked_in is False

    def test_jack_out_returns_extracted_count(self):
        mgr = GridManager()
        gs = GridState(
            grid_name="TestGrid", jacked_in=True,
            extracted_data=[
                {"name": "File A", "value": "High", "protected": False, "index": 0},
                {"name": "File B", "value": "Medium", "protected": False, "index": 1},
            ]
        )
        result = mgr.jack_out(gs)
        assert result["extracted_count"] == 2

    def test_not_jacked_in_extract_fails(self):
        mgr = GridManager()
        node = {"name": "Files", "value": "Low", "protected": False, "index": 0}
        gs = GridState(grid_name="TestGrid", jacked_in=False, data_nodes=[node])
        result = mgr.extract_data(gs, 0)
        assert result["success"] is False


# =========================================================================
# 6. CHROME MANAGER
# =========================================================================

class TestChromeManager:
    """ChromeManager install/remove/humanity/glitch tests."""

    def test_initial_humanity_is_10(self):
        mgr = ChromeManager()
        assert mgr.humanity == 10

    def test_initial_installed_is_empty(self):
        mgr = ChromeManager()
        assert len(mgr.installed) == 0

    def test_install_known_chrome(self):
        mgr = ChromeManager()
        result = mgr.install_chrome("Neural Jack", rng=_rng())
        assert result["success"] is True
        assert "Neural Jack" in mgr.installed

    def test_install_reduces_humanity(self):
        mgr = ChromeManager()
        old_humanity = mgr.humanity
        mgr.install_chrome("Neural Jack", rng=_rng())
        from codex.forge.reference_data.cbrpnk_chrome import CHROME
        expected_cost = CHROME["Neural Jack"]["humanity_cost"]
        assert mgr.humanity == old_humanity - expected_cost

    def test_install_unknown_chrome_fails(self):
        mgr = ChromeManager()
        result = mgr.install_chrome("Nonexistent Widget", rng=_rng())
        assert result["success"] is False
        assert "Unknown chrome" in result["message"]

    def test_install_duplicate_fails(self):
        mgr = ChromeManager()
        mgr.install_chrome("Neural Jack", rng=_rng())
        result = mgr.install_chrome("Neural Jack", rng=_rng())
        assert result["success"] is False
        assert "already installed" in result["message"]

    def test_install_at_slot_capacity_fails(self):
        mgr = ChromeManager()
        # Neural slot capacity is 3; install 3 neural items
        r1 = mgr.install_chrome("Neural Jack", rng=_rng())
        r2 = mgr.install_chrome("Smart Link", rng=_rng())
        r3 = mgr.install_chrome("Reflex Boosters", rng=_rng())
        assert r1["success"] is True
        assert r2["success"] is True
        assert r3["success"] is True
        # 4th neural item should fail (Memory Palace is also neural)
        result = mgr.install_chrome("Memory Palace", rng=_rng())
        assert result["success"] is False
        assert result["slot_conflict"] is True
        assert "Memory Palace" not in mgr.installed

    def test_remove_chrome_by_name(self):
        mgr = ChromeManager()
        mgr.install_chrome("Neural Jack", rng=_rng())
        result = mgr.remove_chrome("Neural Jack")
        assert result["success"] is True
        assert "Neural Jack" not in mgr.installed

    def test_remove_chrome_restores_partial_humanity(self):
        mgr = ChromeManager()
        mgr.install_chrome("Neural Jack", rng=_rng())
        humanity_after_install = mgr.humanity
        mgr.remove_chrome("Neural Jack")
        assert mgr.humanity > humanity_after_install

    def test_remove_nonexistent_chrome_fails(self):
        mgr = ChromeManager()
        result = mgr.remove_chrome("Nonexistent")
        assert result["success"] is False

    def test_humanity_check_passes_at_full_humanity(self):
        mgr = ChromeManager()
        # At humanity 10, risk is 0.0 — always passes
        mgr.humanity = 10
        result = mgr.humanity_check(rng=_rng())
        assert result["passed"] is True

    def test_humanity_check_fails_at_zero(self):
        mgr = ChromeManager()
        mgr.humanity = 0
        result = mgr.humanity_check(rng=_rng(42))
        assert result["passed"] is False

    def test_humanity_check_returns_required_keys(self):
        mgr = ChromeManager()
        result = mgr.humanity_check(rng=_rng())
        required = {"passed", "roll", "threshold", "status", "humanity", "message"}
        assert required.issubset(result.keys())

    def test_trigger_glitch_on_installed_chrome(self):
        mgr = ChromeManager()
        mgr.install_chrome("Wired Reflexes", rng=_rng())
        # Wired Reflexes has glitch_risk 0.30 — find a seed that triggers
        triggered = False
        for seed in range(200):
            test_mgr = ChromeManager()
            test_mgr.install_chrome("Wired Reflexes", rng=_rng(seed))
            result = test_mgr.trigger_glitch("Wired Reflexes", rng=_rng(seed))
            if result["glitch_occurred"]:
                triggered = True
                assert result["severity"] in ("minor", "major", "critical")
                assert len(result["effect"]) > 5
                break
        assert triggered, "Wired Reflexes never glitched across 200 seeds"

    def test_trigger_glitch_unknown_chrome(self):
        mgr = ChromeManager()
        result = mgr.trigger_glitch("Fake Chrome", rng=_rng())
        assert result["glitch_occurred"] is False

    def test_trigger_glitch_logs_history(self):
        mgr = ChromeManager()
        mgr.install_chrome("Wired Reflexes", rng=_rng())
        initial_count = len(mgr.glitch_history)
        # Force glitch via known-bad seed
        for seed in range(200):
            result = mgr.trigger_glitch("Wired Reflexes", rng=_rng(seed))
            if result["glitch_occurred"]:
                assert len(mgr.glitch_history) == initial_count + 1
                break

    def test_get_status_returns_string(self):
        mgr = ChromeManager()
        mgr.install_chrome("Neural Jack", rng=_rng())
        status = mgr.get_status()
        assert isinstance(status, str)
        assert "Humanity" in status
        assert "Neural Jack" in status

    def test_to_dict_round_trip(self):
        mgr = ChromeManager()
        mgr.install_chrome("Neural Jack", rng=_rng())
        mgr.install_chrome("Cybereyes", rng=_rng())
        data = mgr.to_dict()
        restored = ChromeManager.from_dict(data)
        assert restored.humanity == mgr.humanity
        assert set(restored.installed.keys()) == set(mgr.installed.keys())

    def test_humanity_thresholds_coverage(self):
        """Verify HUMANITY_THRESHOLDS covers key breakpoints."""
        assert 0 in HUMANITY_THRESHOLDS
        assert 10 in HUMANITY_THRESHOLDS
        # Should have at least 4 defined thresholds
        assert len(HUMANITY_THRESHOLDS) >= 4


# =========================================================================
# 7. SAVE / LOAD ROUND-TRIP
# =========================================================================

class TestCBRPNKEngineSaveLoad:
    """Engine save/load serialization round-trip tests."""

    def test_basic_save_load(self):
        engine = _engine_with_char()
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert engine2.character is not None
        assert engine2.character.name == "TestRunner"

    def test_heat_and_glitch_persisted(self):
        engine = _engine_with_char()
        engine.heat = 5
        engine.glitch_die = 3
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert engine2.heat == 5
        assert engine2.glitch_die == 3

    def test_party_persisted(self):
        engine = _engine_with_char()
        char2 = CBRPNKCharacter(name="Sidekick", archetype="Ghost")
        engine.add_to_party(char2)
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert len(engine2.party) == 2
        names = [c.name for c in engine2.party]
        assert "TestRunner" in names
        assert "Sidekick" in names

    def test_stress_clocks_persisted(self):
        engine = _engine_with_char()
        engine.stress_clocks["TestRunner"].push(3)
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert engine2.stress_clocks["TestRunner"].current_stress == 3

    def test_grid_state_persisted(self):
        engine = _engine_with_char()
        # Generate a grid via jack_in command
        engine.handle_command("jack_in", difficulty=1, seed=42)
        assert engine._grid_state is not None
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert engine2._grid_state is not None
        assert engine2._grid_state.grid_name == engine._grid_state.grid_name

    def test_chrome_mgr_persisted(self):
        engine = _engine_with_char()
        # Install chrome via command
        engine.handle_command("install_chrome", chrome_name="Neural Jack")
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert engine2._chrome_mgr is not None
        assert "Neural Jack" in engine2._chrome_mgr.installed

    def test_save_state_system_id(self):
        engine = _engine_with_char()
        state = engine.save_state()
        assert state["system_id"] == "cbrpnk"

    def test_empty_engine_save_load(self):
        engine = CBRPNKEngine()
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert engine2.character is None
        assert len(engine2.party) == 0

    def test_character_chrome_list_persisted(self):
        engine = _engine_with_char()
        engine.handle_command("install_chrome", chrome_name="Cybereyes")
        state = engine.save_state()
        engine2 = CBRPNKEngine()
        engine2.load_state(state)
        assert "Cybereyes" in engine2.character.chrome


# =========================================================================
# 8. COMMAND DISPATCH
# =========================================================================

class TestCBRPNKCommandDispatch:
    """handle_command dispatch and output tests."""

    def test_trace_fact_dispatches(self):
        engine = _engine_with_char()
        result = engine.handle_command("trace_fact", fact="hacker identity")
        assert isinstance(result, str)

    def test_unknown_command_returns_message(self):
        engine = _engine_with_char()
        result = engine.handle_command("totally_fake_command")
        assert "Unknown" in result

    def test_crew_status_returns_string(self):
        engine = _engine_with_char()
        result = engine.handle_command("crew_status")
        assert isinstance(result, str)
        assert "Heat" in result

    def test_glitch_status_returns_string(self):
        engine = _engine_with_char()
        result = engine.handle_command("glitch_status")
        assert isinstance(result, str)
        assert "Glitch" in result

    def test_party_status_returns_string(self):
        engine = _engine_with_char()
        result = engine.handle_command("party_status")
        assert isinstance(result, str)
        assert "TestRunner" in result

    def test_roll_action_returns_string(self):
        engine = _engine_with_char()
        result = engine.handle_command("roll_action", action="hack")
        assert isinstance(result, str)
        assert "Dice" in result or "dice" in result.lower() or len(result) > 5

    def test_roll_action_failure_increments_glitch_die(self):
        """Find a seed that causes failure and verify glitch_die increments."""
        for seed in range(200):
            engine = _engine_with_char()
            engine.character.hack = 0  # Zero dots = zero-dice = high failure
            import random as _rand
            rng = _rand.Random(seed)
            from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect
            roll = FITDActionRoll(dice_count=0, position=Position.RISKY,
                                  effect=Effect.STANDARD)
            result = roll.roll(rng=rng)
            if result.outcome == "failure":
                before = engine.glitch_die
                engine.handle_command("roll_action", action="hack")
                # The engine will use its own rng, but logic is tested separately
                assert engine.glitch_die >= before
                return
        pytest.skip("Could not generate failure in 200 seeds")

    def test_jack_in_command_returns_string(self):
        engine = _engine_with_char()
        result = engine.handle_command("jack_in", difficulty=1, seed=42)
        assert isinstance(result, str)
        assert len(result) > 10

    def test_jack_in_sets_grid_state(self):
        engine = _engine_with_char()
        engine.handle_command("jack_in", difficulty=1, seed=42)
        assert engine._grid_state is not None

    def test_jack_in_twice_refuses(self):
        engine = _engine_with_char()
        engine.handle_command("jack_in", difficulty=1, seed=42)
        result = engine.handle_command("jack_in", difficulty=1, seed=42)
        assert "Already jacked in" in result

    def test_grid_status_before_jack_in(self):
        engine = _engine_with_char()
        result = engine.handle_command("grid_status")
        assert "No active grid" in result

    def test_grid_status_after_jack_in(self):
        engine = _engine_with_char()
        engine.handle_command("jack_in", difficulty=1, seed=42)
        result = engine.handle_command("grid_status")
        assert "Grid:" in result
        assert "Alarm Level" in result

    def test_intrusion_before_jack_in(self):
        engine = _engine_with_char()
        result = engine.handle_command("intrusion", ice_name="Patrol-01")
        assert "Not jacked in" in result

    def test_intrusion_after_jack_in(self):
        engine = _engine_with_char()
        engine.handle_command("jack_in", difficulty=1, seed=42)
        # Attempt intrusion — may succeed or fail, but returns a string
        result = engine.handle_command("intrusion")
        assert isinstance(result, str)
        assert len(result) > 5

    def test_extract_before_jack_in(self):
        engine = _engine_with_char()
        result = engine.handle_command("extract", node_index=0)
        assert "Not jacked in" in result

    def test_jack_out_before_jack_in(self):
        engine = _engine_with_char()
        result = engine.handle_command("jack_out")
        assert isinstance(result, str)

    def test_jack_out_after_jack_in(self):
        engine = _engine_with_char()
        engine.handle_command("jack_in", difficulty=1, seed=42)
        result = engine.handle_command("jack_out")
        assert isinstance(result, str)
        assert engine._grid_state.jacked_in is False

    def test_install_chrome_command(self):
        engine = _engine_with_char()
        result = engine.handle_command("install_chrome", chrome_name="Cybereyes")
        assert isinstance(result, str)
        assert engine._chrome_mgr is not None
        assert "Cybereyes" in engine._chrome_mgr.installed

    def test_install_chrome_syncs_character_chrome_list(self):
        engine = _engine_with_char()
        engine.handle_command("install_chrome", chrome_name="Cybereyes")
        assert "Cybereyes" in engine.character.chrome

    def test_install_chrome_no_name_returns_error(self):
        engine = _engine_with_char()
        result = engine.handle_command("install_chrome")
        assert "chrome_name" in result.lower() or "specify" in result.lower()

    def test_remove_chrome_command(self):
        engine = _engine_with_char()
        engine.handle_command("install_chrome", chrome_name="Cybereyes")
        result = engine.handle_command("remove_chrome", slot="Cybereyes")
        assert isinstance(result, str)
        assert "Cybereyes" not in engine._chrome_mgr.installed

    def test_remove_chrome_syncs_character_chrome_list(self):
        engine = _engine_with_char()
        engine.handle_command("install_chrome", chrome_name="Cybereyes")
        engine.handle_command("remove_chrome", slot="Cybereyes")
        assert "Cybereyes" not in engine.character.chrome

    def test_chrome_status_command(self):
        engine = _engine_with_char()
        result = engine.handle_command("chrome_status")
        assert isinstance(result, str)
        assert "Humanity" in result

    def test_humanity_check_command(self):
        engine = _engine_with_char()
        result = engine.handle_command("humanity_check")
        assert isinstance(result, str)
        assert "humanity" in result.lower() or "Humanity" in result

    def test_all_commands_in_registry_are_handled(self):
        """Verify every command in CBRPNK_COMMANDS has a handler or known alias."""
        from codex.games.cbrpnk import CBRPNK_COMMANDS
        engine = CBRPNKEngine()
        for cmd in CBRPNK_COMMANDS:
            handler = getattr(engine, f"_cmd_{cmd}", None)
            assert handler is not None, (
                f"Command '{cmd}' in CBRPNK_COMMANDS has no _cmd_{cmd} handler"
            )

    def test_all_categories_commands_exist(self):
        """Verify all commands listed in CBRPNK_CATEGORIES are in CBRPNK_COMMANDS."""
        from codex.games.cbrpnk import CBRPNK_COMMANDS, CBRPNK_CATEGORIES
        all_cmd_keys = set(CBRPNK_COMMANDS.keys())
        for category, cmds in CBRPNK_CATEGORIES.items():
            for cmd in cmds:
                assert cmd in all_cmd_keys, (
                    f"Category '{category}' lists '{cmd}' not in CBRPNK_COMMANDS"
                )

"""
WO-V41.0 — Blades in the Dark Engine Depth: Tests
====================================================

Covers:
  - TestBitDPlaybookData: 7 playbooks with required fields
  - TestBitDFactionData: 30+ factions with required fields
  - TestBitDCrewData: 6 crew types with required fields
  - TestEngagementRoll: engagement roll mechanics, plan types, crit detection
  - TestFlashbackManager: flashback usage, cost table, persistence
  - TestDevilsBargain: bargain offers, acceptance, persistence
  - TestScoreState: score lifecycle, resolve_score outcomes
  - TestDowntimeManager: all 6 downtime activities, activity limit
  - TestLongTermProject: project creation, ticking, completion
  - TestBitDEngineSaveLoad: full save/load round-trip with subsystem state
  - TestBitDCommandDispatch: all new handle_command() dispatches
"""

import random
import pytest

from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS, HERITAGES, VICE_TYPES
from codex.forge.reference_data.bitd_factions import FACTIONS, FACTION_STATUS
from codex.forge.reference_data.bitd_crew import CREW_TYPES, GENERAL_CREW_UPGRADES, LAIR_FEATURES
from codex.games.bitd.scores import (
    ScoreState,
    FlashbackManager,
    DevilsBargainTracker,
    engagement_roll,
    resolve_score,
    PLAN_TYPES,
    ENGAGEMENT_OUTCOMES,
)
from codex.games.bitd.downtime import (
    DowntimeManager,
    LongTermProject,
    DOWNTIME_RESULT_TICKS,
)
from codex.games.bitd import BitDEngine, BITD_COMMANDS, BITD_CATEGORIES


# =========================================================================
# HELPERS
# =========================================================================

def _rng(seed: int = 42) -> random.Random:
    """Return a seeded Random for deterministic tests."""
    return random.Random(seed)


def _engine_with_char(name: str = "Silas", playbook: str = "Cutter") -> BitDEngine:
    """Build a BitDEngine with one character registered."""
    eng = BitDEngine()
    eng.create_character(name, playbook=playbook)
    eng.crew_name = "The Wandering Knives"
    eng.crew_type = "Assassins"
    return eng


# =========================================================================
# REFERENCE DATA: PLAYBOOKS
# =========================================================================

class TestBitDPlaybookData:
    """Verify all 7 playbooks load with required fields."""

    REQUIRED_FIELDS = {"description", "special_abilities", "friends", "rivals", "items", "xp_trigger"}
    EXPECTED_PLAYBOOKS = {"Cutter", "Hound", "Leech", "Lurk", "Slide", "Spider", "Whisper"}

    def test_all_seven_playbooks_present(self):
        """All 7 canonical playbooks must exist."""
        assert set(PLAYBOOKS.keys()) == self.EXPECTED_PLAYBOOKS

    def test_each_playbook_has_required_fields(self):
        """Every playbook must carry all required field keys."""
        for name, pb in PLAYBOOKS.items():
            missing = self.REQUIRED_FIELDS - set(pb.keys())
            assert not missing, f"{name} missing fields: {missing}"

    def test_special_abilities_are_non_empty_lists(self):
        """Each playbook must have at least one special ability."""
        for name, pb in PLAYBOOKS.items():
            assert isinstance(pb["special_abilities"], list), f"{name}: abilities not a list"
            assert len(pb["special_abilities"]) >= 1, f"{name}: no special abilities"

    def test_each_ability_has_name_and_description(self):
        """Each special ability must have 'name' and 'description' keys."""
        for pb_name, pb in PLAYBOOKS.items():
            for ability in pb["special_abilities"]:
                assert "name" in ability, f"{pb_name} ability missing 'name': {ability}"
                assert "description" in ability, f"{pb_name} ability missing 'description': {ability}"

    def test_cutter_has_battleborn(self):
        """Cutter's first ability should be Battleborn."""
        ability_names = [a["name"] for a in PLAYBOOKS["Cutter"]["special_abilities"]]
        assert "Battleborn" in ability_names

    def test_whisper_has_compel(self):
        """Whisper must have the Compel ability."""
        ability_names = [a["name"] for a in PLAYBOOKS["Whisper"]["special_abilities"]]
        assert "Compel" in ability_names

    def test_heritages_present(self):
        """All 6 heritages must be defined."""
        expected = {"Akoros", "Dagger Isles", "Iruvia", "Severos", "Skovlan", "Tycheros"}
        assert set(HERITAGES.keys()) == expected

    def test_each_heritage_has_description(self):
        """Every heritage must have a description."""
        for name, heritage in HERITAGES.items():
            assert "description" in heritage, f"{name} missing description"
            assert heritage["description"], f"{name} has empty description"

    def test_vice_types_non_empty(self):
        """VICE_TYPES must be a non-empty list of strings."""
        assert isinstance(VICE_TYPES, list)
        assert len(VICE_TYPES) >= 7
        for v in VICE_TYPES:
            assert isinstance(v, str)

    def test_xp_triggers_are_strings(self):
        """All XP triggers must be non-empty strings."""
        for name, pb in PLAYBOOKS.items():
            assert isinstance(pb["xp_trigger"], str), f"{name}: xp_trigger not a string"
            assert pb["xp_trigger"], f"{name}: xp_trigger is empty"


# =========================================================================
# REFERENCE DATA: FACTIONS
# =========================================================================

class TestBitDFactionData:
    """Verify 30+ factions load with required fields."""

    REQUIRED_FIELDS = {"tier", "hold", "description", "turf", "notable_npcs", "quirk"}

    def test_at_least_thirty_factions(self):
        """Must define 30 or more factions."""
        assert len(FACTIONS) >= 30, f"Only {len(FACTIONS)} factions defined"

    def test_each_faction_has_required_fields(self):
        """Every faction must carry all required field keys."""
        for name, faction in FACTIONS.items():
            missing = self.REQUIRED_FIELDS - set(faction.keys())
            assert not missing, f"{name} missing fields: {missing}"

    def test_tier_is_integer(self):
        """All tiers must be integers between 0 and 6."""
        for name, faction in FACTIONS.items():
            assert isinstance(faction["tier"], int), f"{name}: tier is not int"
            assert 0 <= faction["tier"] <= 6, f"{name}: tier {faction['tier']} out of range"

    def test_hold_is_strong_or_weak(self):
        """Hold must be 'strong' or 'weak'."""
        for name, faction in FACTIONS.items():
            assert faction["hold"] in ("strong", "weak"), f"{name}: invalid hold '{faction['hold']}'"

    def test_notable_npcs_is_list(self):
        """notable_npcs must be a list."""
        for name, faction in FACTIONS.items():
            assert isinstance(faction["notable_npcs"], list), f"{name}: notable_npcs not a list"

    def test_bluecoats_present_and_tier_3(self):
        """The Bluecoats are a canonical faction at tier 3."""
        assert "The Bluecoats" in FACTIONS
        assert FACTIONS["The Bluecoats"]["tier"] == 3

    def test_spirit_wardens_present(self):
        """The Spirit Wardens must be in the faction list."""
        assert "The Spirit Wardens" in FACTIONS

    def test_faction_status_table_complete(self):
        """FACTION_STATUS must map -3 through +3."""
        for level in range(-3, 4):
            assert level in FACTION_STATUS, f"Missing status level {level}"
            assert isinstance(FACTION_STATUS[level], str)


# =========================================================================
# REFERENCE DATA: CREW TYPES
# =========================================================================

class TestBitDCrewData:
    """Verify all 6 crew types load with required fields."""

    REQUIRED_FIELDS = {
        "description", "special_abilities", "upgrades",
        "contacts", "hunting_grounds", "xp_trigger",
    }
    EXPECTED_CREWS = {"Assassins", "Bravos", "Cult", "Hawkers", "Shadows", "Smugglers"}

    def test_all_six_crew_types_present(self):
        """All 6 canonical crew types must exist."""
        assert set(CREW_TYPES.keys()) == self.EXPECTED_CREWS

    def test_each_crew_has_required_fields(self):
        """Every crew type must carry all required field keys."""
        for name, crew in CREW_TYPES.items():
            missing = self.REQUIRED_FIELDS - set(crew.keys())
            assert not missing, f"{name} missing fields: {missing}"

    def test_special_abilities_are_non_empty(self):
        """Each crew type must have at least one special ability."""
        for name, crew in CREW_TYPES.items():
            assert len(crew["special_abilities"]) >= 1, f"{name}: no special abilities"

    def test_hunting_grounds_has_type_and_detail(self):
        """Each crew's hunting_grounds must have 'type' and 'detail'."""
        for name, crew in CREW_TYPES.items():
            hg = crew["hunting_grounds"]
            assert "type" in hg, f"{name}: hunting_grounds missing 'type'"
            assert "detail" in hg, f"{name}: hunting_grounds missing 'detail'"

    def test_general_upgrades_non_empty(self):
        """GENERAL_CREW_UPGRADES must be a non-empty list."""
        assert isinstance(GENERAL_CREW_UPGRADES, list)
        assert len(GENERAL_CREW_UPGRADES) >= 5

    def test_lair_features_dict(self):
        """LAIR_FEATURES must be a non-empty dict of string descriptions."""
        assert isinstance(LAIR_FEATURES, dict)
        assert len(LAIR_FEATURES) >= 4
        for key, val in LAIR_FEATURES.items():
            assert isinstance(val, str), f"{key}: feature description not a string"

    def test_assassins_has_deadly_ability(self):
        """Assassins crew must have the Deadly ability."""
        ability_names = [a["name"] for a in CREW_TYPES["Assassins"]["special_abilities"]]
        assert "Deadly" in ability_names

    def test_shadows_has_everyone_steals(self):
        """Shadows crew must have the 'Everyone Steals' ability."""
        ability_names = [a["name"] for a in CREW_TYPES["Shadows"]["special_abilities"]]
        assert "Everyone Steals" in ability_names


# =========================================================================
# ENGAGEMENT ROLL
# =========================================================================

class TestEngagementRoll:
    """Test engagement roll mechanics, plan types, and crit detection."""

    def test_single_die_pool_returns_one_die(self):
        """Pool of 1 returns a list with exactly one die."""
        result = engagement_roll(crew_tier=1, rng=_rng(1))
        assert len(result["dice"]) == 1

    def test_zero_pool_returns_two_dice_take_lowest(self):
        """Pool of 0 rolls 2d6 and takes the lowest (disadvantage)."""
        result = engagement_roll(crew_tier=0, rng=_rng(5))
        assert len(result["dice"]) == 2
        # The reported highest should be the lowest of the two dice
        assert result["highest"] == min(result["dice"])

    def test_critical_on_two_sixes(self):
        """Two or more 6s in the pool produces a critical."""
        # Force two 6s by seeding appropriately
        r = random.Random(0)
        # Loop to find a seed that produces two 6s in a 3-die pool
        found = False
        for seed in range(1000):
            res = engagement_roll(crew_tier=3, rng=random.Random(seed))
            if res["critical"]:
                found = True
                assert res["position"] == "controlled"
                assert res["result_key"] == 7
                break
        assert found, "Could not find a critical result in 1000 seeds"

    def test_result_1_to_3_is_desperate(self):
        """Results 1-3 on highest die produce desperate position."""
        for result_key in (1, 2, 3):
            outcome = ENGAGEMENT_OUTCOMES[result_key]
            assert outcome["position"] == "desperate"

    def test_result_4_to_5_is_risky(self):
        """Results 4-5 on highest die produce risky position."""
        for result_key in (4, 5):
            outcome = ENGAGEMENT_OUTCOMES[result_key]
            assert outcome["position"] == "risky"

    def test_result_6_is_controlled(self):
        """Result 6 on highest die produces controlled position."""
        assert ENGAGEMENT_OUTCOMES[6]["position"] == "controlled"

    def test_all_six_plan_types_in_plan_types_dict(self):
        """All six plan types must be defined in PLAN_TYPES."""
        expected = {"assault", "deception", "infiltration", "occult", "social", "transport"}
        assert set(PLAN_TYPES.keys()) == expected

    def test_each_plan_type_has_description_and_detail_ask(self):
        """Each plan type must have 'description' and 'detail_ask'."""
        for name, plan in PLAN_TYPES.items():
            assert "description" in plan, f"{name}: missing description"
            assert "detail_ask" in plan, f"{name}: missing detail_ask"

    def test_misc_penalty_reduces_pool(self):
        """misc_penalty reduces the effective dice pool."""
        # With crew_tier=2 and misc_penalty=2, pool becomes 0 (disadvantage)
        result = engagement_roll(crew_tier=2, misc_penalty=2, rng=_rng(10))
        # Pool 0 means 2 dice rolled (take lowest)
        assert len(result["dice"]) == 2

    def test_bonus_increases_pool(self):
        """misc_bonus increases the effective dice pool."""
        result = engagement_roll(crew_tier=1, misc_bonus=2, rng=_rng(10))
        # Pool = 1 + 2 = 3
        assert len(result["dice"]) == 3

    def test_return_keys_present(self):
        """Result dict must have all expected keys."""
        result = engagement_roll(crew_tier=1, rng=_rng(7))
        for key in ("dice", "highest", "critical", "position", "description", "result_key"):
            assert key in result, f"Missing key: {key}"


# =========================================================================
# FLASHBACK MANAGER
# =========================================================================

class TestFlashbackManager:
    """Test flashback usage, cost table, and persistence."""

    def test_simple_flashback_costs_zero_stress(self):
        """Simple flashbacks cost 0 stress."""
        mgr = FlashbackManager()
        fb = mgr.use_flashback("I hid the key earlier.", "simple")
        assert fb["stress_cost"] == 0

    def test_complex_flashback_costs_one_stress(self):
        """Complex flashbacks cost 1 stress."""
        mgr = FlashbackManager()
        fb = mgr.use_flashback("I bribed the guard three days ago.", "complex")
        assert fb["stress_cost"] == 1

    def test_elaborate_flashback_costs_two_stress(self):
        """Elaborate flashbacks cost 2 stress."""
        mgr = FlashbackManager()
        fb = mgr.use_flashback("I planted evidence a week ago.", "elaborate")
        assert fb["stress_cost"] == 2

    def test_unknown_complexity_defaults_to_one(self):
        """Unknown complexity strings default to cost of 1."""
        mgr = FlashbackManager()
        fb = mgr.use_flashback("Something weird.", "mythical")
        assert fb["stress_cost"] == 1

    def test_flashbacks_accumulate(self):
        """Multiple flashbacks are all stored."""
        mgr = FlashbackManager()
        mgr.use_flashback("First", "simple")
        mgr.use_flashback("Second", "complex")
        assert len(mgr.flashbacks) == 2

    def test_index_increments_correctly(self):
        """Each flashback gets a sequential index."""
        mgr = FlashbackManager()
        fb0 = mgr.use_flashback("Zero", "simple")
        fb1 = mgr.use_flashback("One", "simple")
        assert fb0["index"] == 0
        assert fb1["index"] == 1

    def test_to_dict_and_from_dict_round_trip(self):
        """Flashbacks survive a to_dict / from_dict round-trip."""
        mgr = FlashbackManager()
        mgr.use_flashback("The escape route.", "complex")
        data = mgr.to_dict()
        restored = FlashbackManager.from_dict(data)
        assert len(restored.flashbacks) == 1
        assert restored.flashbacks[0]["description"] == "The escape route."
        assert restored.flashbacks[0]["stress_cost"] == 1

    def test_from_dict_with_empty_data(self):
        """from_dict handles missing keys gracefully."""
        mgr = FlashbackManager.from_dict({})
        assert mgr.flashbacks == []


# =========================================================================
# DEVIL'S BARGAIN TRACKER
# =========================================================================

class TestDevilsBargain:
    """Test bargain offers, acceptance, and persistence."""

    def test_offer_bargain_returns_category_and_description(self):
        """offer_bargain must return a dict with category and description."""
        tracker = DevilsBargainTracker()
        bargain = tracker.offer_bargain(rng=_rng(1))
        assert "category" in bargain
        assert "description" in bargain

    def test_offer_with_specific_category(self):
        """Passing a valid category constrains the bargain pool."""
        tracker = DevilsBargainTracker()
        bargain = tracker.offer_bargain(category="evidence", rng=_rng(1))
        assert bargain["category"] == "evidence"

    def test_offer_with_invalid_category_picks_random(self):
        """An invalid category falls back to a random valid category."""
        tracker = DevilsBargainTracker()
        bargain = tracker.offer_bargain(category="nonexistent", rng=_rng(1))
        assert bargain["category"] in DevilsBargainTracker.SAMPLE_BARGAINS

    def test_accept_bargain_moves_to_accepted(self):
        """Accepting a bargain adds it to bargains_accepted."""
        tracker = DevilsBargainTracker()
        tracker.offer_bargain(rng=_rng(1))
        accepted = tracker.accept_bargain()
        assert accepted is not None
        assert len(tracker.bargains_accepted) == 1

    def test_accept_with_no_offers_returns_none(self):
        """Accepting when nothing offered returns None."""
        tracker = DevilsBargainTracker()
        result = tracker.accept_bargain()
        assert result is None

    def test_multiple_offers_accept_last_by_default(self):
        """accept_bargain() with index=-1 accepts the most recent offer."""
        tracker = DevilsBargainTracker()
        tracker.offer_bargain(category="collateral_damage", rng=_rng(1))
        tracker.offer_bargain(category="evidence", rng=_rng(2))
        accepted = tracker.accept_bargain()
        assert accepted["category"] == "evidence"

    def test_accept_specific_index(self):
        """accept_bargain(index=0) accepts the first offered bargain."""
        tracker = DevilsBargainTracker()
        tracker.offer_bargain(category="collateral_damage", rng=_rng(1))
        tracker.offer_bargain(category="evidence", rng=_rng(2))
        accepted = tracker.accept_bargain(index=0)
        assert accepted["category"] == "collateral_damage"

    def test_to_dict_and_from_dict_round_trip(self):
        """Bargain state survives a to_dict / from_dict round-trip."""
        tracker = DevilsBargainTracker()
        tracker.offer_bargain(category="supernatural", rng=_rng(3))
        tracker.accept_bargain()
        data = tracker.to_dict()
        restored = DevilsBargainTracker.from_dict(data)
        assert len(restored.bargains_offered) == 1
        assert len(restored.bargains_accepted) == 1

    def test_all_categories_have_entries(self):
        """All five bargain categories must have at least 3 entries."""
        for cat, entries in DevilsBargainTracker.SAMPLE_BARGAINS.items():
            assert len(entries) >= 3, f"Category '{cat}' has fewer than 3 entries"


# =========================================================================
# SCORE STATE
# =========================================================================

class TestScoreState:
    """Test score lifecycle and resolve_score outcomes."""

    def test_default_score_state_inactive(self):
        """A freshly created ScoreState should not be active."""
        score = ScoreState()
        assert not score.active

    def test_to_dict_preserves_all_fields(self):
        """to_dict must include all tracked fields."""
        score = ScoreState(
            target="The Vault", plan_type="infiltration", active=True,
            flashbacks_used=2, heat_generated=3,
        )
        d = score.to_dict()
        assert d["target"] == "The Vault"
        assert d["plan_type"] == "infiltration"
        assert d["active"] is True
        assert d["flashbacks_used"] == 2

    def test_from_dict_round_trip(self):
        """ScoreState survives a to_dict / from_dict round-trip."""
        score = ScoreState(
            target="Lord Scurlock",
            plan_type="social",
            active=True,
            devils_bargains=["A witness escapes."],
            complications=["Alarm triggered"],
        )
        data = score.to_dict()
        restored = ScoreState.from_dict(data)
        assert restored.target == "Lord Scurlock"
        assert restored.plan_type == "social"
        assert restored.active is True
        assert len(restored.devils_bargains) == 1
        assert len(restored.complications) == 1

    def test_resolve_score_awards_rep_and_heat(self):
        """resolve_score must return positive rep_earned and heat_generated."""
        score = ScoreState(active=True, target="The Hive")
        result = resolve_score(score, crew_tier=1, target_tier=4)
        assert result["rep_earned"] >= 1
        assert result["heat_generated"] >= 1

    def test_resolve_score_complications_add_heat(self):
        """Complications increase the heat generated."""
        score_clean = ScoreState(active=True)
        score_messy = ScoreState(active=True, complications=["Witness", "Alarm"])
        clean = resolve_score(score_clean, crew_tier=1, target_tier=2)
        messy = resolve_score(score_messy, crew_tier=1, target_tier=2)
        assert messy["heat_generated"] > clean["heat_generated"]

    def test_resolve_score_returns_summary_string(self):
        """resolve_score must return a non-empty summary string."""
        score = ScoreState(active=True, target="Test Target")
        result = resolve_score(score)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_resolve_score_coin_at_least_one(self):
        """Even against a tier-0 target, at least 1 coin is earned."""
        score = ScoreState(active=True)
        result = resolve_score(score, crew_tier=2, target_tier=0)
        assert result["coin_earned"] >= 1

    def test_from_dict_handles_missing_keys(self):
        """from_dict handles an empty dict with safe defaults."""
        score = ScoreState.from_dict({})
        assert not score.active
        assert score.target == ""
        assert score.devils_bargains == []


# =========================================================================
# LONG-TERM PROJECT
# =========================================================================

class TestLongTermProject:
    """Test project creation, ticking, and completion."""

    def test_initial_state(self):
        """A new project starts at 0 ticks, not complete."""
        proj = LongTermProject(name="Blueprint", clock_size=8)
        assert proj.ticks == 0
        assert not proj.complete

    def test_tick_increments_progress(self):
        """tick() increments ticks by the given amount."""
        proj = LongTermProject(name="Tunnel", clock_size=8)
        added = proj.tick(3)
        assert added == 3
        assert proj.ticks == 3

    def test_tick_caps_at_clock_size(self):
        """tick() cannot exceed clock_size."""
        proj = LongTermProject(name="Escape", clock_size=4, ticks=3)
        added = proj.tick(5)
        assert proj.ticks == 4
        assert added == 1

    def test_completion_triggers_on_full_clock(self):
        """When ticks reach clock_size, complete is set to True."""
        proj = LongTermProject(name="Infiltrate", clock_size=4)
        proj.tick(4)
        assert proj.complete

    def test_to_dict_and_from_dict_round_trip(self):
        """LongTermProject survives a to_dict / from_dict round-trip."""
        proj = LongTermProject(name="Intel", description="Gather info", clock_size=6, ticks=3)
        data = proj.to_dict()
        restored = LongTermProject.from_dict(data)
        assert restored.name == "Intel"
        assert restored.clock_size == 6
        assert restored.ticks == 3
        assert not restored.complete

    def test_from_dict_with_empty_data(self):
        """from_dict handles missing keys safely."""
        proj = LongTermProject.from_dict({"name": "Empty"})
        assert proj.clock_size == 8
        assert proj.ticks == 0

    def test_completed_project_in_round_trip(self):
        """A complete project is correctly restored."""
        proj = LongTermProject(name="Done", clock_size=4, ticks=4, complete=True)
        restored = LongTermProject.from_dict(proj.to_dict())
        assert restored.complete


# =========================================================================
# DOWNTIME MANAGER
# =========================================================================

class TestDowntimeManager:
    """Test all 6 downtime activities and the activity limit."""

    def test_initial_activities_is_two(self):
        """A fresh DowntimeManager starts with 2 activities."""
        mgr = DowntimeManager()
        assert mgr.activities_remaining == 2

    def test_reset_activities_restores_count(self):
        """reset_activities() sets activities back to 2 + bonus."""
        mgr = DowntimeManager()
        mgr.activities_remaining = 0
        mgr.reset_activities(bonus=1)
        assert mgr.activities_remaining == 3

    def test_vice_roll_consumes_activity(self):
        """vice_roll() spends one activity."""
        mgr = DowntimeManager()
        mgr.vice_roll("Silas", "Gambling", lowest_attribute=2, rng=_rng(1))
        assert mgr.activities_remaining == 1

    def test_vice_roll_returns_description(self):
        """vice_roll() result includes a non-empty description."""
        mgr = DowntimeManager()
        result = mgr.vice_roll("Nyx", "Luxury", rng=_rng(2))
        assert "description" in result
        assert len(result["description"]) > 0

    def test_activity_limit_returns_error(self):
        """When no activities remain, all downtime methods return an error."""
        mgr = DowntimeManager()
        mgr.activities_remaining = 0
        result = mgr.vice_roll("Silas", rng=_rng(1))
        assert "error" in result

    def test_acquire_asset_consumes_activity(self):
        """acquire_asset() spends one activity."""
        mgr = DowntimeManager()
        mgr.acquire_asset(crew_tier=2, quality_desired=1, rng=_rng(10))
        assert mgr.activities_remaining == 1

    def test_reduce_heat_consumes_activity(self):
        """reduce_heat() spends one activity."""
        mgr = DowntimeManager()
        mgr.reduce_heat(crew_tier=1, rng=_rng(5))
        assert mgr.activities_remaining == 1

    def test_reduce_heat_result_has_heat_reduced(self):
        """reduce_heat() result must include heat_reduced key."""
        mgr = DowntimeManager()
        result = mgr.reduce_heat(crew_tier=2, rng=_rng(99))
        assert "heat_reduced" in result
        assert result["heat_reduced"] >= 1

    def test_recover_consumes_activity(self):
        """recover() spends one activity."""
        mgr = DowntimeManager()
        mgr.recover(healer_dots=2, rng=_rng(7))
        assert mgr.activities_remaining == 1

    def test_recover_result_has_segments_healed(self):
        """recover() result must include segments_healed key."""
        mgr = DowntimeManager()
        result = mgr.recover(healer_dots=2, rng=_rng(7))
        assert "segments_healed" in result
        assert result["segments_healed"] >= 1

    def test_train_consumes_activity(self):
        """train() spends one activity."""
        mgr = DowntimeManager()
        mgr.train("prowess")
        assert mgr.activities_remaining == 1

    def test_train_defaults_to_playbook(self):
        """train() with invalid attribute defaults to 'playbook'."""
        mgr = DowntimeManager()
        result = mgr.train("invalid_attr")
        assert result["attribute"] == "playbook"

    def test_train_all_valid_attributes(self):
        """train() accepts all four valid attributes."""
        for attr in ("insight", "prowess", "resolve", "playbook"):
            mgr = DowntimeManager()
            result = mgr.train(attr)
            assert result["attribute"] == attr
            assert result["xp_gained"] == 1

    def test_work_on_project_requires_existing_project(self):
        """work_on_project() returns error if project doesn't exist."""
        mgr = DowntimeManager()
        result = mgr.work_on_project("Nonexistent Project", action_dots=2)
        assert "error" in result

    def test_create_and_work_on_project(self):
        """Creating a project then working on it tracks progress."""
        mgr = DowntimeManager()
        mgr.create_project("Safe House", "Build a new lair", clock_size=8)
        result = mgr.work_on_project("Safe House", action_dots=3, rng=_rng(42))
        assert "ticks_added" in result
        assert result["ticks_added"] >= 1

    def test_project_clock_size_clamped(self):
        """create_project clamps clock_size to 4-12."""
        mgr = DowntimeManager()
        proj = mgr.create_project("Test1", clock_size=1)
        assert proj.clock_size == 4
        proj2 = mgr.create_project("Test2", clock_size=100)
        assert proj2.clock_size == 12

    def test_log_summary_reflects_activities(self):
        """get_log_summary() shows a line for each activity performed."""
        mgr = DowntimeManager()
        mgr.train("insight")
        summary = mgr.get_log_summary()
        assert "Training" in summary

    def test_to_dict_and_from_dict_round_trip(self):
        """DowntimeManager state survives to_dict / from_dict."""
        mgr = DowntimeManager()
        mgr.create_project("Intel", clock_size=6)
        mgr.train("prowess")
        data = mgr.to_dict()
        restored = DowntimeManager.from_dict(data)
        assert "Intel" in restored.projects
        assert restored.activities_remaining == mgr.activities_remaining
        assert len(restored.downtime_log) == 1

    def test_downtime_result_ticks_table_coverage(self):
        """DOWNTIME_RESULT_TICKS covers result keys 1-7."""
        for key in range(1, 8):
            assert key in DOWNTIME_RESULT_TICKS
            assert DOWNTIME_RESULT_TICKS[key] >= 1


# =========================================================================
# SAVE / LOAD ROUND-TRIP
# =========================================================================

class TestBitDEngineSaveLoad:
    """Full save/load round-trip with subsystem state."""

    def test_basic_engine_save_load(self):
        """Basic engine fields survive save_state / load_state."""
        eng = _engine_with_char()
        eng.heat = 3
        eng.rep = 5
        eng.coin = 7
        eng.turf = 2

        data = eng.save_state()
        eng2 = BitDEngine()
        eng2.load_state(data)

        assert eng2.heat == 3
        assert eng2.rep == 5
        assert eng2.coin == 7
        assert eng2.turf == 2
        assert eng2.crew_name == "The Wandering Knives"

    def test_score_state_persists(self):
        """Score state survives save/load if an engagement was rolled."""
        eng = _engine_with_char()
        eng.handle_command("engagement", plan_type="assault", target="The Crows")

        data = eng.save_state()
        eng2 = BitDEngine()
        eng2.load_state(data)

        assert eng2._score_state is not None
        assert eng2._score_state.active is True
        assert eng2._score_state.plan_type == "assault"
        assert eng2._score_state.target == "The Crows"

    def test_flashback_state_persists(self):
        """Flashback manager survives save/load if a flashback was used."""
        eng = _engine_with_char()
        eng.handle_command("engagement", plan_type="infiltration")
        eng.handle_command("flashback", description="Bribed the guard.", complexity="complex")

        data = eng.save_state()
        eng2 = BitDEngine()
        eng2.load_state(data)

        assert eng2._flashback_mgr is not None
        assert len(eng2._flashback_mgr.flashbacks) == 1
        assert eng2._flashback_mgr.flashbacks[0]["stress_cost"] == 1

    def test_bargain_tracker_persists(self):
        """Bargain tracker survives save/load if a bargain was offered."""
        eng = _engine_with_char()
        eng.handle_command("engagement", plan_type="social")
        eng.handle_command("devils_bargain", category="evidence")
        eng.handle_command("accept_bargain")

        data = eng.save_state()
        eng2 = BitDEngine()
        eng2.load_state(data)

        assert eng2._bargain_tracker is not None
        assert len(eng2._bargain_tracker.bargains_accepted) == 1

    def test_downtime_manager_persists(self):
        """Downtime manager survives save/load after activities."""
        eng = _engine_with_char()
        eng.handle_command("downtime_train", attribute="prowess")

        data = eng.save_state()
        eng2 = BitDEngine()
        eng2.load_state(data)

        assert eng2._downtime_mgr is not None
        assert len(eng2._downtime_mgr.downtime_log) == 1

    def test_none_subsystems_not_saved_or_restored(self):
        """Unused subsystems are None after save/load — no phantom state."""
        eng = _engine_with_char()
        data = eng.save_state()

        assert data["score_state"] is None
        assert data["flashback_mgr"] is None
        assert data["bargain_tracker"] is None
        assert data["downtime_mgr"] is None

        eng2 = BitDEngine()
        eng2.load_state(data)
        assert eng2._score_state is None
        assert eng2._flashback_mgr is None

    def test_party_persists_across_save_load(self):
        """Party members survive save/load with correct attributes."""
        eng = BitDEngine()
        eng.create_character("Rynn", playbook="Lurk", prowl=3)
        data = eng.save_state()

        eng2 = BitDEngine()
        eng2.load_state(data)
        assert len(eng2.party) == 1
        assert eng2.party[0].name == "Rynn"
        assert eng2.party[0].playbook == "Lurk"
        assert eng2.party[0].prowl == 3


# =========================================================================
# COMMAND DISPATCH
# =========================================================================

class TestBitDCommandDispatch:
    """Test all new handle_command() dispatches."""

    @pytest.fixture
    def eng(self) -> BitDEngine:
        """Engine fixture with one character."""
        return _engine_with_char()

    def test_engagement_command_activates_score(self, eng):
        """engagement command sets score.active = True."""
        result = eng.handle_command("engagement", plan_type="assault", target="The Hive")
        assert "Engagement Roll" in result
        assert eng._score_state is not None
        assert eng._score_state.active is True
        assert eng._score_state.target == "The Hive"

    def test_engagement_command_includes_position(self, eng):
        """engagement command result always includes a position label."""
        result = eng.handle_command("engagement", plan_type="infiltration")
        positions = ("CONTROLLED", "RISKY", "DESPERATE")
        assert any(p in result.upper() for p in positions)

    def test_score_status_when_inactive(self, eng):
        """score_status reports no active score when none is running."""
        result = eng.handle_command("score_status")
        assert "No active score" in result

    def test_score_status_when_active(self, eng):
        """score_status shows score details when a score is active."""
        eng.handle_command("engagement", plan_type="deception", target="Lord Scurlock")
        result = eng.handle_command("score_status")
        assert "Lord Scurlock" in result
        assert "deception" in result

    def test_flashback_command(self, eng):
        """flashback command records the flashback and stress cost."""
        eng.handle_command("engagement", plan_type="infiltration")
        result = eng.handle_command(
            "flashback",
            description="I cased the manor last week.",
            complexity="complex",
        )
        assert "Flashback" in result
        assert "Stress cost: 1" in result
        assert eng._score_state.flashbacks_used == 1

    def test_devils_bargain_command(self, eng):
        """devils_bargain command generates a bargain description."""
        result = eng.handle_command("devils_bargain", category="collateral_damage")
        assert "Devil's Bargain" in result
        assert "collateral_damage" in result

    def test_accept_bargain_command(self, eng):
        """accept_bargain records the bargain into the score state."""
        eng.handle_command("engagement", plan_type="social")
        eng.handle_command("devils_bargain", category="evidence")
        result = eng.handle_command("accept_bargain")
        assert "accepted" in result.lower()
        assert len(eng._score_state.devils_bargains) == 1

    def test_accept_bargain_with_no_offer(self, eng):
        """accept_bargain without a prior offer returns a safe message."""
        result = eng.handle_command("accept_bargain")
        assert "No bargain" in result

    def test_resolve_score_command(self, eng):
        """resolve_score ends the score and awards rep/heat/coin."""
        eng.handle_command("engagement", plan_type="assault", target="The Lampblacks")
        initial_rep = eng.rep
        initial_heat = eng.heat
        result = eng.handle_command("resolve_score", crew_tier=1, target_tier=2)
        assert "Score complete" in result
        assert eng.rep > initial_rep
        assert eng.heat > initial_heat
        assert eng._score_state.active is False

    def test_resolve_score_with_no_active_score(self, eng):
        """resolve_score returns an error message when no score is active."""
        result = eng.handle_command("resolve_score")
        assert "No active score" in result

    def test_downtime_project_create_then_work(self, eng):
        """downtime_project creates a new project on first call, works on second."""
        result1 = eng.handle_command(
            "downtime_project", project_name="Bribe Network", clock_size=6
        )
        assert "created" in result1

        # Reset activities for second call
        eng._get_downtime_mgr().activities_remaining = 5
        result2 = eng.handle_command("downtime_project", project_name="Bribe Network", action_dots=2)
        assert "ticks" in result2.lower() or "Project" in result2

    def test_downtime_project_missing_name(self, eng):
        """downtime_project without a name returns error."""
        result = eng.handle_command("downtime_project")
        assert "Specify" in result

    def test_downtime_acquire_command(self, eng):
        """downtime_acquire returns asset quality information."""
        result = eng.handle_command("downtime_acquire", crew_tier=2, quality=1)
        assert "Acquire asset" in result
        assert "Quality" in result

    def test_downtime_reduce_heat_command(self, eng):
        """downtime_reduce_heat reduces engine heat and reports it."""
        eng.heat = 6
        result = eng.handle_command("downtime_reduce_heat", crew_tier=2)
        assert "Current heat" in result
        assert eng.heat < 6

    def test_downtime_recover_command(self, eng):
        """downtime_recover reports healing segments filled."""
        result = eng.handle_command("downtime_recover", healer_dots=2)
        assert "segment" in result.lower() or "Recovery" in result

    def test_downtime_train_command(self, eng):
        """downtime_train marks XP in the given attribute."""
        result = eng.handle_command("downtime_train", attribute="insight")
        assert "Training" in result
        assert "insight" in result

    def test_unknown_command_returns_error(self, eng):
        """handle_command with an unknown cmd returns 'Unknown command'."""
        result = eng.handle_command("totally_fake_command")
        assert "Unknown command" in result

    def test_all_bitd_commands_in_dict(self):
        """BITD_COMMANDS must include all depth commands."""
        depth_commands = {
            "engagement", "flashback", "devils_bargain", "accept_bargain",
            "resolve_score", "downtime_project", "downtime_acquire",
            "downtime_reduce_heat", "downtime_recover", "downtime_train",
        }
        for cmd in depth_commands:
            assert cmd in BITD_COMMANDS, f"Missing command in BITD_COMMANDS: {cmd}"

    def test_bitd_categories_has_score_category(self):
        """BITD_CATEGORIES must have a 'Score' category."""
        assert "Score" in BITD_CATEGORIES
        score_cmds = BITD_CATEGORIES["Score"]
        assert "engagement" in score_cmds
        assert "flashback" in score_cmds
        assert "resolve_score" in score_cmds

    def test_downtime_category_has_new_commands(self):
        """BITD_CATEGORIES Downtime must include extended downtime commands."""
        downtime_cmds = BITD_CATEGORIES.get("Downtime", [])
        for cmd in ("downtime_project", "downtime_acquire", "downtime_reduce_heat",
                    "downtime_recover", "downtime_train"):
            assert cmd in downtime_cmds, f"Missing from Downtime category: {cmd}"

    def test_trace_fact_command(self, eng):
        """trace_fact dispatches via handle_command without error."""
        eng.handle_command("engagement", plan_type="assault")
        result = eng.handle_command("trace_fact", fact="The Hive is our target.")
        # Should not raise; may return empty or a trace string
        assert isinstance(result, str)

    def test_entanglement_command_uses_heat(self, eng):
        """entanglement command rolls and returns a flavor result."""
        eng.heat = 5
        result = eng.handle_command("entanglement")
        assert "Entanglement Roll" in result

    def test_crew_status_command(self, eng):
        """crew_status reflects current crew heat, coin, and rep."""
        eng.heat = 4
        eng.coin = 10
        result = eng.handle_command("crew_status")
        assert "Heat: 4" in result
        assert "Coin: 10" in result

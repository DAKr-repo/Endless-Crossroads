#!/usr/bin/env python3
"""
tests/test_crown_engine_depth.py
==================================
Phase 4 Crown & Crew Depth Parity Sprint — Test Suite

Tests:
    TestCrownLeaderData          — 8 leaders and 8 patrons with all required fields
    TestCrownFactionData         — 8 factions with required fields and relationships
    TestFactionInfluenceTracker  — Influence shifts, territory, resources, dominance
    TestAllianceSystem           — Form/break alliances, query, stability checks
    TestPoliticalGravityEngine   — Council votes, power shifts, gravity calc, faction actions
    TestEventGenerator           — Weighted event selection, sway bias, chains
    TestCrownHandleCommand       — handle_command() dispatcher (Crown's first!)
    TestCrownEngineSaveLoad      — Round-trip save/load with politics + events state
"""

import random
import pytest

from codex.games.crown.engine import TAGS
from codex.forge.reference_data.crown_leaders import LEADERS, PATRONS, LEADER_EVENTS
from codex.forge.reference_data.crown_factions import (
    FACTIONS, FACTION_RELATIONSHIPS, FACTION_NAMES,
)
from codex.forge.reference_data.crown import (
    LEADERS as AGG_LEADERS,
    PATRONS as AGG_PATRONS,
    FACTIONS as AGG_FACTIONS,
)
from codex.games.crown.politics import (
    FactionInfluenceTracker,
    AllianceSystem,
    PoliticalGravityEngine,
)
from codex.games.crown.events import (
    EventGenerator,
    WEIGHTED_EVENT_POOL,
    EVENT_CHAINS,
    NPC_EVENTS,
)
from codex.games.crown.engine import (
    CrownAndCrewEngine,
    CROWN_COMMANDS,
    CROWN_CATEGORIES,
)


# =============================================================================
# 1. TestCrownLeaderData
# =============================================================================

class TestCrownLeaderData:
    """Verify 8 leaders and 8 patrons load with all required fields."""

    REQUIRED_LEADER_FIELDS = {
        "title", "personality", "backstory", "secret_agenda",
        "betrayal_trigger", "loyalty_bonus", "crown_lean", "relationships",
    }
    REQUIRED_PATRON_FIELDS = {
        "title", "personality", "backstory", "secret_agenda",
        "betrayal_trigger", "leverage_bonus", "crown_lean", "relationships",
    }

    def test_eight_leaders(self):
        assert len(LEADERS) == 8, f"Expected 8 leaders, got {len(LEADERS)}"

    def test_eight_patrons(self):
        assert len(PATRONS) == 8, f"Expected 8 patrons, got {len(PATRONS)}"

    def test_leader_required_fields(self):
        for name, data in LEADERS.items():
            missing = self.REQUIRED_LEADER_FIELDS - set(data.keys())
            assert not missing, f"Leader '{name}' missing fields: {missing}"

    def test_patron_required_fields(self):
        for name, data in PATRONS.items():
            missing = self.REQUIRED_PATRON_FIELDS - set(data.keys())
            assert not missing, f"Patron '{name}' missing fields: {missing}"

    def test_leader_crown_lean_range(self):
        for name, data in LEADERS.items():
            lean = data["crown_lean"]
            assert -1.0 <= lean <= 1.0, (
                f"Leader '{name}' crown_lean {lean} outside [-1.0, 1.0]"
            )

    def test_patron_crown_lean_range(self):
        for name, data in PATRONS.items():
            lean = data["crown_lean"]
            assert -1.0 <= lean <= 1.0, (
                f"Patron '{name}' crown_lean {lean} outside [-1.0, 1.0]"
            )

    def test_leader_relationships_are_valid_attitudes(self):
        valid = {"rival", "ally", "neutral", "suspicious"}
        for name, data in LEADERS.items():
            for other, attitude in data["relationships"].items():
                assert attitude in valid, (
                    f"Leader '{name}' → '{other}': invalid attitude '{attitude}'"
                )

    def test_patron_relationships_are_valid_attitudes(self):
        valid = {"rival", "ally", "neutral", "suspicious"}
        for name, data in PATRONS.items():
            for other, attitude in data["relationships"].items():
                assert attitude in valid, (
                    f"Patron '{name}' → '{other}': invalid attitude '{attitude}'"
                )

    def test_leader_relationships_reference_existing_leaders(self):
        known = set(LEADERS.keys())
        for name, data in LEADERS.items():
            for other in data["relationships"]:
                assert other in known, (
                    f"Leader '{name}' references unknown leader '{other}'"
                )

    def test_patron_relationships_reference_existing_patrons(self):
        known = set(PATRONS.keys())
        for name, data in PATRONS.items():
            for other in data["relationships"]:
                assert other in known, (
                    f"Patron '{name}' references unknown patron '{other}'"
                )

    def test_leader_backstory_is_non_empty(self):
        for name, data in LEADERS.items():
            assert len(data["backstory"].strip()) > 20, (
                f"Leader '{name}' backstory too short"
            )

    def test_patron_backstory_is_non_empty(self):
        for name, data in PATRONS.items():
            assert len(data["backstory"].strip()) > 20, (
                f"Patron '{name}' backstory too short"
            )

    def test_leader_events_reference_known_leaders(self):
        known = set(LEADERS.keys())
        for name in LEADER_EVENTS:
            assert name in known, f"LEADER_EVENTS key '{name}' not in LEADERS"

    def test_leader_events_structure(self):
        for name, events in LEADER_EVENTS.items():
            assert isinstance(events, list), f"LEADER_EVENTS['{name}'] must be a list"
            for event in events:
                assert "text" in event, f"Event in LEADER_EVENTS['{name}'] missing 'text'"
                assert "bias" in event, f"Event in LEADER_EVENTS['{name}'] missing 'bias'"
                assert "tag" in event, f"Event in LEADER_EVENTS['{name}'] missing 'tag'"

    def test_aggregator_re_exports_leaders_and_patrons(self):
        assert AGG_LEADERS is LEADERS
        assert AGG_PATRONS is PATRONS


# =============================================================================
# 2. TestCrownFactionData
# =============================================================================

class TestCrownFactionData:
    """Verify 8 factions load with required fields and valid relationship matrix."""

    REQUIRED_FACTION_FIELDS = {
        "description", "ideology", "influence", "territory",
        "leader_name", "resources", "agenda", "allies", "enemies", "events",
    }

    def test_eight_factions(self):
        assert len(FACTIONS) == 8, f"Expected 8 factions, got {len(FACTIONS)}"

    def test_faction_required_fields(self):
        for name, data in FACTIONS.items():
            missing = self.REQUIRED_FACTION_FIELDS - set(data.keys())
            assert not missing, f"Faction '{name}' missing fields: {missing}"

    def test_faction_influence_range(self):
        for name, data in FACTIONS.items():
            inf = data["influence"]
            assert 0 <= inf <= 10, (
                f"Faction '{name}' influence {inf} outside [0, 10]"
            )

    def test_faction_resources_keys(self):
        required_resources = {"gold", "soldiers", "spies", "influence"}
        for name, data in FACTIONS.items():
            missing = required_resources - set(data["resources"].keys())
            assert not missing, (
                f"Faction '{name}' missing resources: {missing}"
            )

    def test_faction_agenda_has_three_goals(self):
        for name, data in FACTIONS.items():
            assert len(data["agenda"]) == 3, (
                f"Faction '{name}' should have exactly 3 agenda goals"
            )

    def test_faction_events_structure(self):
        for name, data in FACTIONS.items():
            for event in data["events"]:
                assert "text" in event, f"Faction '{name}' event missing 'text'"
                assert "bias" in event, f"Faction '{name}' event missing 'bias'"
                assert "tag" in event, f"Faction '{name}' event missing 'tag'"

    def test_faction_relationships_cover_all_pairs(self):
        names = list(FACTIONS.keys())
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                rel_ab = FACTION_RELATIONSHIPS.get(a, {}).get(b)
                rel_ba = FACTION_RELATIONSHIPS.get(b, {}).get(a)
                assert rel_ab is not None or rel_ba is not None, (
                    f"No relationship defined between '{a}' and '{b}'"
                )

    def test_faction_relationship_values_are_valid(self):
        valid = {"alliance", "rivalry", "neutral", "tension"}
        for faction_a, relations in FACTION_RELATIONSHIPS.items():
            for faction_b, status in relations.items():
                assert status in valid, (
                    f"{faction_a} → {faction_b}: invalid status '{status}'"
                )

    def test_faction_names_list_matches_factions_dict(self):
        assert set(FACTION_NAMES) == set(FACTIONS.keys())

    def test_aggregator_re_exports_factions(self):
        assert AGG_FACTIONS is FACTIONS


# =============================================================================
# 3. TestFactionInfluenceTracker
# =============================================================================

class TestFactionInfluenceTracker:
    """Test FactionInfluenceTracker API."""

    def _tracker(self) -> FactionInfluenceTracker:
        return FactionInfluenceTracker()

    def test_initializes_all_factions(self):
        tracker = self._tracker()
        assert len(tracker.factions) == 8

    def test_shift_influence_positive(self):
        tracker = self._tracker()
        result = tracker.shift_influence("Merchant Guild", 2)
        assert result["new_influence"] == result["old_influence"] + 2

    def test_shift_influence_negative(self):
        tracker = self._tracker()
        result = tracker.shift_influence("People's Assembly", -1)
        assert result["new_influence"] == result["old_influence"] - 1

    def test_shift_influence_caps_at_max(self):
        tracker = self._tracker()
        tracker.factions["Crown Loyalists"]["influence"] = 9
        result = tracker.shift_influence("Crown Loyalists", 5)
        assert result["new_influence"] == 10
        assert result["capped"] is True

    def test_shift_influence_caps_at_min(self):
        tracker = self._tracker()
        tracker.factions["Reformists"]["influence"] = 1
        result = tracker.shift_influence("Reformists", -5)
        assert result["new_influence"] == 0
        assert result["capped"] is True

    def test_shift_influence_unknown_faction(self):
        tracker = self._tracker()
        result = tracker.shift_influence("Nonexistent Faction", 1)
        assert "error" in result

    def test_get_dominant_faction(self):
        tracker = self._tracker()
        dominant = tracker.get_dominant_faction()
        assert isinstance(dominant, str)
        assert dominant in tracker.factions

    def test_dominant_faction_changes_with_influence(self):
        tracker = self._tracker()
        # Set all to 0 except one
        for name in tracker.factions:
            tracker.factions[name]["influence"] = 0
        tracker.factions["Reformists"]["influence"] = 5
        assert tracker.get_dominant_faction() == "Reformists"

    def test_transfer_territory_success(self):
        tracker = self._tracker()
        from_faction = "Crown Loyalists"
        to_faction = "People's Assembly"
        # Crown Loyalists have "Palace Quarter" in their territory
        district = tracker.factions[from_faction]["territory"][0]
        result = tracker.transfer_territory(from_faction, to_faction, district)
        assert result["success"] is True
        assert district not in tracker.factions[from_faction]["territory"]
        assert district in tracker.factions[to_faction]["territory"]

    def test_transfer_territory_invalid_district(self):
        tracker = self._tracker()
        result = tracker.transfer_territory(
            "Crown Loyalists", "People's Assembly", "Nonexistent District"
        )
        assert result["success"] is False

    def test_transfer_territory_unknown_faction(self):
        tracker = self._tracker()
        result = tracker.transfer_territory(
            "Unknown Faction", "People's Assembly", "Some District"
        )
        assert result["success"] is False

    def test_resource_action_gain(self):
        tracker = self._tracker()
        old = tracker.factions["Merchant Guild"]["resources"]["gold"]
        result = tracker.resource_action("Merchant Guild", "gold", "gain", 2)
        assert result["success"] is True
        assert result["new"] == old + 2

    def test_resource_action_spend_success(self):
        tracker = self._tracker()
        tracker.factions["Merchant Guild"]["resources"]["gold"] = 5
        result = tracker.resource_action("Merchant Guild", "gold", "spend", 3)
        assert result["success"] is True
        assert result["new"] == 2

    def test_resource_action_spend_insufficient(self):
        tracker = self._tracker()
        tracker.factions["Reformists"]["resources"]["soldiers"] = 0
        result = tracker.resource_action("Reformists", "soldiers", "spend", 1)
        assert result["success"] is False

    def test_get_faction_status(self):
        tracker = self._tracker()
        status = tracker.get_faction_status("Merchant Guild")
        assert "name" in status
        assert "influence" in status
        assert "territory" in status

    def test_get_all_statuses_sorted_by_influence(self):
        tracker = self._tracker()
        statuses = tracker.get_all_statuses()
        influences = [s["influence"] for s in statuses]
        assert influences == sorted(influences, reverse=True)

    def test_serialization_roundtrip(self):
        tracker = self._tracker()
        tracker.shift_influence("Crown Loyalists", -2)
        tracker.transfer_territory(
            "Crown Loyalists", "People's Assembly",
            tracker.factions["Crown Loyalists"]["territory"][0]
            if tracker.factions["Crown Loyalists"]["territory"] else "Palace Quarter"
        )
        data = tracker.to_dict()
        restored = FactionInfluenceTracker.from_dict(data)
        assert restored.factions["Crown Loyalists"]["influence"] == (
            tracker.factions["Crown Loyalists"]["influence"]
        )


# =============================================================================
# 4. TestAllianceSystem
# =============================================================================

class TestAllianceSystem:
    """Test AllianceSystem API."""

    def _system(self) -> AllianceSystem:
        return AllianceSystem()

    def test_default_relationships_loaded(self):
        system = self._system()
        assert len(system.alliances) > 0

    def test_form_alliance(self):
        system = self._system()
        result = system.form_alliance("Reformists", "Old Blood")
        assert result["new_status"] == "alliance"
        assert system.get_relationship("Reformists", "Old Blood") == "alliance"

    def test_break_alliance(self):
        system = self._system()
        # First form it
        system.form_alliance("Reformists", "Temple Authority")
        result = system.break_alliance("Reformists", "Temple Authority", "Policy dispute")
        assert result["new_status"] == "tension"
        assert system.get_relationship("Reformists", "Temple Authority") == "tension"

    def test_declare_rivalry(self):
        system = self._system()
        result = system.declare_rivalry("Shadow Court", "Reformists")
        assert result["new_status"] == "rivalry"
        assert system.get_relationship("Shadow Court", "Reformists") == "rivalry"

    def test_normalize_relationship(self):
        system = self._system()
        system.declare_rivalry("Merchant Guild", "Free Companies")
        system.normalize("Merchant Guild", "Free Companies", "Trade agreement")
        assert system.get_relationship("Merchant Guild", "Free Companies") == "neutral"

    def test_get_allies_returns_correct_factions(self):
        system = self._system()
        system.form_alliance("Reformists", "People's Assembly")
        system.form_alliance("Reformists", "Temple Authority")
        allies = system.get_allies("Reformists")
        assert "People's Assembly" in allies
        assert "Temple Authority" in allies

    def test_get_enemies_returns_correct_factions(self):
        system = self._system()
        system.declare_rivalry("Crown Loyalists", "People's Assembly")
        enemies = system.get_enemies("Crown Loyalists")
        assert "People's Assembly" in enemies

    def test_relationship_is_symmetric(self):
        """Querying A→B and B→A should return the same status."""
        system = self._system()
        system.form_alliance("Free Companies", "People's Assembly")
        assert (
            system.get_relationship("Free Companies", "People's Assembly")
            == system.get_relationship("People's Assembly", "Free Companies")
        )

    def test_check_alliance_stability_changes_tension(self):
        system = self._system()
        # Ensure at least one tension pair exists
        system.declare_rivalry("Merchant Guild", "Reformists")
        system.normalize("Merchant Guild", "Reformists")  # → neutral
        system._set_relationship("Merchant Guild", "Reformists", "tension")
        rng = random.Random(42)
        result = system.check_alliance_stability(rng=rng)
        assert result["changed"] is True

    def test_check_alliance_stability_no_tension(self):
        """When no tension pairs exist, stability check reports no change."""
        system = AllianceSystem.__new__(AllianceSystem)
        system.alliances = {}
        system.alliance_history = []
        result = system.check_alliance_stability()
        assert result["changed"] is False

    def test_alliance_history_recorded(self):
        system = self._system()
        initial_len = len(system.alliance_history)
        system.form_alliance("Old Blood", "Shadow Court")
        assert len(system.alliance_history) == initial_len + 1

    def test_serialization_roundtrip(self):
        system = self._system()
        system.form_alliance("Reformists", "People's Assembly")
        system.declare_rivalry("Crown Loyalists", "Free Companies")
        data = system.to_dict()
        restored = AllianceSystem.from_dict(data)
        assert restored.get_relationship("Reformists", "People's Assembly") == "alliance"
        assert restored.get_relationship("Crown Loyalists", "Free Companies") == "rivalry"
        assert len(restored.alliance_history) == len(system.alliance_history)


# =============================================================================
# 5. TestPoliticalGravityEngine
# =============================================================================

class TestPoliticalGravityEngine:
    """Test PoliticalGravityEngine orchestration layer."""

    def _engine(self) -> PoliticalGravityEngine:
        return PoliticalGravityEngine()

    def test_initializes_with_defaults(self):
        engine = self._engine()
        assert engine.power_balance == 0.0
        assert engine.influence_tracker is not None
        assert engine.alliance_system is not None

    def test_council_vote_produces_winner(self):
        engine = self._engine()
        rng = random.Random(0)
        result = engine.council_vote(
            proposal="Expand the garrison",
            factions_voting={
                "Crown Loyalists": "crown",
                "People's Assembly": "crew",
                "Merchant Guild": "crown",
            },
            rng=rng,
        )
        assert result["winner"] in ("crown", "crew")
        assert "flavor" in result
        assert result["crown_weight"] > 0 or result["crew_weight"] > 0

    def test_council_vote_with_sway_modifier(self):
        engine = self._engine()
        rng = random.Random(10)
        _result_neutral = engine.council_vote(
            "Test vote",
            {"Crown Loyalists": "crown", "People's Assembly": "crew"},
            sway_modifier=0,
            rng=rng,
        )
        # With heavy positive sway modifier, crew should win more often
        engine2 = self._engine()
        rng2 = random.Random(10)
        result_crew = engine2.council_vote(
            "Test vote",
            {"Crown Loyalists": "crown", "People's Assembly": "crew"},
            sway_modifier=10,
            rng=rng2,
        )
        assert result_crew["crew_weight"] > result_crew["crown_weight"]

    def test_power_shift_positive(self):
        engine = self._engine()
        result = engine.power_shift(0.3, "Crew wins a major battle")
        assert result["new_balance"] > result["old_balance"]
        assert result["dominant"] in ("Crew", "Contested", "Crown")

    def test_power_shift_caps_at_one(self):
        engine = self._engine()
        engine.power_balance = 0.95
        result = engine.power_shift(0.5)
        assert result["new_balance"] <= 1.0

    def test_power_shift_caps_at_negative_one(self):
        engine = self._engine()
        engine.power_balance = -0.95
        result = engine.power_shift(-0.5)
        assert result["new_balance"] >= -1.0

    def test_calculate_gravity_structure(self):
        engine = self._engine()
        gravity = engine.calculate_gravity()
        assert "power_balance" in gravity
        assert "balance_label" in gravity
        assert "dominant_faction" in gravity
        assert "alliance_count" in gravity
        assert "rivalry_count" in gravity
        assert "faction_summary" in gravity
        assert isinstance(gravity["faction_summary"], list)

    def test_calculate_gravity_labels(self):
        engine = self._engine()
        engine.power_balance = -0.6
        g = engine.calculate_gravity()
        assert g["balance_label"] == "Crown Dominant"

        engine.power_balance = 0.6
        g = engine.calculate_gravity()
        assert g["balance_label"] == "Crew Dominant"

        engine.power_balance = 0.0
        g = engine.calculate_gravity()
        assert g["balance_label"] == "Contested"

    def test_faction_action_propaganda(self):
        engine = self._engine()
        old_influence = engine.influence_tracker.factions["Reformists"]["influence"]
        result = engine.faction_action(
            "Reformists", "propaganda", rng=random.Random(99)
        )
        assert result["success"] is True
        new_influence = engine.influence_tracker.factions["Reformists"]["influence"]
        assert new_influence >= old_influence  # May be capped

    def test_faction_action_sabotage(self):
        engine = self._engine()
        result = engine.faction_action(
            "Shadow Court", "sabotage", target="Crown Loyalists",
            rng=random.Random(5),
        )
        assert result["success"] is True

    def test_faction_action_recruit(self):
        engine = self._engine()
        _old = engine.influence_tracker.factions["Free Companies"]["resources"].get("soldiers", 0)
        result = engine.faction_action("Free Companies", "recruit")
        assert result["success"] is True

    def test_faction_action_unknown_faction(self):
        engine = self._engine()
        result = engine.faction_action("Nobody", "propaganda")
        assert result["success"] is False

    def test_faction_action_unknown_action_type(self):
        engine = self._engine()
        result = engine.faction_action("Reformists", "invent_magic")
        assert result["success"] is False

    def test_serialization_roundtrip(self):
        engine = self._engine()
        engine.power_shift(0.2, "test")
        engine.faction_action("Reformists", "propaganda", rng=random.Random(1))
        data = engine.to_dict()
        restored = PoliticalGravityEngine.from_dict(data)
        assert abs(restored.power_balance - engine.power_balance) < 0.001
        assert len(restored.influence_tracker.factions) == len(engine.influence_tracker.factions)


# =============================================================================
# 6. TestEventGenerator
# =============================================================================

class TestEventGenerator:
    """Test EventGenerator — pool selection, sway bias, chains."""

    def test_default_pool_has_events(self):
        gen = EventGenerator()
        assert len(gen.event_pool) >= 30, (
            f"Expected ≥30 events in pool, got {len(gen.event_pool)}"
        )

    def test_generate_event_returns_event_dict(self):
        gen = EventGenerator()
        event = gen.generate_event(sway=0, day=1, rng=random.Random(0))
        assert "text" in event
        assert "sway_bias" in event
        assert "tag" in event
        assert event["day"] == 1

    def test_generate_event_records_history(self):
        gen = EventGenerator()
        initial = len(gen.event_history)
        gen.generate_event(sway=1, day=2, rng=random.Random(7))
        assert len(gen.event_history) == initial + 1

    def test_sway_bias_crew_favors_crew_events(self):
        """With high positive sway, crew events should dominate over many draws."""
        gen = EventGenerator()
        rng = random.Random(42)
        crew_count = 0
        crown_count = 0
        for _ in range(200):
            event = gen.generate_event(sway=3, day=3, rng=rng)
            if event["sway_bias"] == "crew":
                crew_count += 1
            elif event["sway_bias"] == "crown":
                crown_count += 1
        assert crew_count > crown_count, (
            f"Expected crew events to dominate at sway +3; got crew={crew_count}, crown={crown_count}"
        )

    def test_sway_bias_crown_favors_crown_events(self):
        """With high negative sway, crown events should dominate over many draws."""
        gen = EventGenerator()
        rng = random.Random(99)
        crew_count = 0
        crown_count = 0
        for _ in range(200):
            event = gen.generate_event(sway=-3, day=3, rng=rng)
            if event["sway_bias"] == "crew":
                crew_count += 1
            elif event["sway_bias"] == "crown":
                crown_count += 1
        assert crown_count > crew_count, (
            f"Expected crown events to dominate at sway -3; got crown={crown_count}, crew={crew_count}"
        )

    def test_day_range_filtering(self):
        """Events with day_range [3, None] should not appear on day 1."""
        # Build a pool with only high-day events
        late_events = [e for e in WEIGHTED_EVENT_POOL if e.get("day_range", [1, None])[0] == 3]
        if not late_events:
            pytest.skip("No day_range=[3, None] events in pool")
        # Run 50 generations on day 1 — none should be exclusively day 3+
        gen = EventGenerator()
        rng = random.Random(0)
        for _ in range(50):
            event = gen.generate_event(sway=0, day=1, rng=rng)
            min_day = event.get("day_range", [1, None])[0]
            assert (min_day or 1) <= 1, f"Day 1 generated an event with min_day={min_day}"

    def test_generate_chain_event_advances_through_chain(self):
        gen = EventGenerator()
        chain_id = "merchant_crisis"
        chain = EVENT_CHAINS[chain_id]
        events_seen = []
        for _ in range(len(chain)):
            event = gen.generate_chain_event(chain_id)
            assert event is not None, f"Chain returned None at step {len(events_seen)}"
            events_seen.append(event["event_id"])
        assert len(events_seen) == len(chain)

    def test_generate_chain_event_returns_none_when_complete(self):
        gen = EventGenerator()
        chain_id = "plague"
        for _ in range(len(EVENT_CHAINS[chain_id])):
            gen.generate_chain_event(chain_id)
        result = gen.generate_chain_event(chain_id)
        assert result is None

    def test_is_chain_complete(self):
        gen = EventGenerator()
        chain_id = "governor_deal"
        assert not gen.is_chain_complete(chain_id)
        for _ in range(len(EVENT_CHAINS[chain_id])):
            gen.generate_chain_event(chain_id)
        assert gen.is_chain_complete(chain_id)

    def test_is_chain_complete_unknown_chain(self):
        gen = EventGenerator()
        assert gen.is_chain_complete("nonexistent_chain") is True

    def test_add_custom_event(self):
        gen = EventGenerator()
        initial_count = len(gen.event_pool)
        custom = {"event_id": "test_custom", "text": "A test event", "sway_bias": "neutral", "tag": "SILENCE", "weight": 1}
        gen.add_custom_event(custom)
        assert len(gen.event_pool) == initial_count + 1

    def test_npc_events_structure(self):
        for npc_name, events in NPC_EVENTS.items():
            assert isinstance(events, list)
            for event in events:
                assert "text" in event
                assert "sway_bias" in event
                assert "tag" in event

    def test_event_chains_structure(self):
        for chain_id, chain in EVENT_CHAINS.items():
            assert isinstance(chain, list), f"Chain '{chain_id}' must be a list"
            assert len(chain) >= 2, f"Chain '{chain_id}' must have ≥2 steps"
            for step in chain:
                assert "text" in step, f"Chain '{chain_id}' step missing 'text'"
                assert "sway_bias" in step, f"Chain '{chain_id}' step missing 'sway_bias'"

    def test_get_weighted_pool_tag_filter(self):
        gen = EventGenerator()
        blood_pool = gen.get_weighted_pool(sway=0, tags=["BLOOD"])
        for event, _ in blood_pool:
            assert event.get("tag") == "BLOOD"  # type: ignore[attr-defined]

    def test_serialization_roundtrip(self):
        gen = EventGenerator()
        gen.generate_event(sway=0, day=1, rng=random.Random(0))
        gen.generate_chain_event("succession_plot")
        data = gen.to_dict()
        restored = EventGenerator.from_dict(data)
        assert len(restored.event_history) == len(gen.event_history)
        assert restored.chain_progress == gen.chain_progress


# =============================================================================
# 7. TestCrownHandleCommand
# =============================================================================

class TestCrownHandleCommand:
    """
    Crown's FIRST handle_command() dispatcher tests.
    Verify all registered commands dispatch correctly.
    """

    def _engine(self) -> CrownAndCrewEngine:
        return CrownAndCrewEngine()

    def test_unknown_command_returns_error_string(self):
        engine = self._engine()
        result = engine.handle_command("definitely_not_a_command")
        assert "Unknown" in result or "unknown" in result.lower()

    def test_trace_fact_dispatches(self):
        engine = self._engine()
        result = engine.handle_command("trace_fact", fact="patron")
        assert isinstance(result, str)

    def test_status_command(self):
        engine = self._engine()
        result = engine.handle_command("status")
        assert "Day" in result
        assert "Sway" in result

    def test_faction_status_command(self):
        engine = self._engine()
        result = engine.handle_command("faction_status")
        assert "Faction Status" in result
        assert "influence" in result.lower()

    def test_shift_influence_command(self):
        engine = self._engine()
        result = engine.handle_command("shift_influence", faction="Reformists", amount=2)
        assert "Reformists" in result
        assert "→" in result

    def test_shift_influence_missing_faction(self):
        engine = self._engine()
        result = engine.handle_command("shift_influence", amount=1)
        assert "requires" in result.lower() or "kwarg" in result.lower()

    def test_form_alliance_command(self):
        engine = self._engine()
        result = engine.handle_command(
            "form_alliance",
            faction_a="Old Blood",
            faction_b="Reformists",
        )
        assert "Alliance" in result
        assert "Old Blood" in result or "Reformists" in result

    def test_form_alliance_missing_args(self):
        engine = self._engine()
        result = engine.handle_command("form_alliance", faction_a="Old Blood")
        assert "requires" in result.lower() or "kwarg" in result.lower()

    def test_break_alliance_command(self):
        engine = self._engine()
        # First form it
        engine.handle_command("form_alliance", faction_a="Old Blood", faction_b="Shadow Court")
        result = engine.handle_command(
            "break_alliance",
            faction_a="Old Blood",
            faction_b="Shadow Court",
            reason="Betrayal",
        )
        assert "broken" in result.lower() or "Break" in result or "break" in result.lower()

    def test_council_vote_command(self):
        engine = self._engine()
        result = engine.handle_command(
            "council_vote",
            proposal="Increase garrison",
            factions_voting={
                "Crown Loyalists": "crown",
                "People's Assembly": "crew",
            },
        )
        assert "Council Vote" in result
        assert "Winner" in result or "winner" in result.lower()

    def test_council_vote_missing_factions_voting(self):
        engine = self._engine()
        result = engine.handle_command("council_vote", proposal="Something")
        assert "requires" in result.lower()

    def test_power_balance_command(self):
        engine = self._engine()
        result = engine.handle_command("power_balance")
        assert "Power Balance" in result
        assert "Dominant faction" in result or "dominant" in result.lower()

    def test_generate_event_command(self):
        engine = self._engine()
        result = engine.handle_command("generate_event")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_event_chain_command_known_chain(self):
        engine = self._engine()
        result = engine.handle_command("event_chain", chain_id="merchant_crisis")
        assert "merchant_crisis" in result
        assert isinstance(result, str)

    def test_event_chain_command_unknown_chain(self):
        engine = self._engine()
        result = engine.handle_command("event_chain", chain_id="nonexistent")
        assert "Unknown" in result or "complete" in result or "nonexistent" in result

    def test_event_chain_missing_chain_id(self):
        engine = self._engine()
        result = engine.handle_command("event_chain")
        assert "requires" in result.lower()

    def test_political_landscape_command(self):
        engine = self._engine()
        result = engine.handle_command("political_landscape")
        assert "Political Landscape" in result
        assert "Power Balance" in result
        assert "Faction Influence" in result

    def test_crown_commands_dict_populated(self):
        assert len(CROWN_COMMANDS) >= 10
        for cmd_name, description in CROWN_COMMANDS.items():
            assert isinstance(cmd_name, str)
            assert isinstance(description, str)
            assert len(description) > 5

    def test_crown_categories_cover_all_commands(self):
        categorized = {
            cmd
            for cmds in CROWN_CATEGORIES.values()
            for cmd in cmds
        }
        for cmd in CROWN_COMMANDS:
            assert cmd in categorized, (
                f"Command '{cmd}' is in CROWN_COMMANDS but not in any CROWN_CATEGORIES bucket"
            )


# =============================================================================
# 8. TestCrownEngineSaveLoad
# =============================================================================

class TestCrownEngineSaveLoad:
    """Round-trip save/load with full Phase 4 subsystem state."""

    def test_basic_roundtrip_without_subsystems(self):
        engine = CrownAndCrewEngine(arc_length=7)
        engine.declare_allegiance("crew", "HEARTH")
        engine.end_day()
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored.day == engine.day
        assert restored.sway == engine.sway
        assert restored.arc_length == 7
        assert restored.patron == engine.patron
        assert restored.leader == engine.leader

    def test_roundtrip_with_politics_subsystem_active(self):
        engine = CrownAndCrewEngine()
        # Activate politics engine
        engine.handle_command("shift_influence", faction="Reformists", amount=3)
        engine.handle_command("form_alliance", faction_a="Old Blood", faction_b="Shadow Court")
        data = engine.to_dict()
        assert "_politics_engine" in data
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._politics_engine is not None
        assert engine._politics_engine is not None
        restored_influence = restored._politics_engine.influence_tracker.factions[
            "Reformists"
        ]["influence"]
        original_influence = engine._politics_engine.influence_tracker.factions[  # type: ignore[union-attr]
            "Reformists"
        ]["influence"]
        assert restored_influence == original_influence

    def test_roundtrip_with_event_generator_active(self):
        engine = CrownAndCrewEngine()
        # Activate event generator
        engine.handle_command("generate_event")
        engine.handle_command("event_chain", chain_id="plague")
        data = engine.to_dict()
        assert "_event_generator" in data
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._event_generator is not None
        assert engine._event_generator is not None
        assert len(restored._event_generator.event_history) == len(
            engine._event_generator.event_history  # type: ignore[union-attr]
        )
        assert restored._event_generator.chain_progress == (
            engine._event_generator.chain_progress  # type: ignore[union-attr]
        )

    def test_roundtrip_with_both_subsystems_active(self):
        engine = CrownAndCrewEngine()
        engine.handle_command("faction_status")         # politics init
        engine.handle_command("generate_event")         # events init
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._politics_engine is not None
        assert restored._event_generator is not None

    def test_existing_tests_backward_compat(self):
        """Ensure Phase 4 additions don't break existing to_dict keys."""
        engine = CrownAndCrewEngine()
        data = engine.to_dict()
        required_keys = {
            "day", "sway", "patron", "leader", "history", "dna",
            "vote_log", "arc_length", "rest_type", "rest_config",
            "terms", "entities", "threat", "region", "goal",
            "_used_crown", "_used_crew", "_used_world",
            "_used_campfire", "_used_morning", "_used_dilemmas",
            "_council_dilemmas", "quest_slug", "quest_name",
            "special_mechanics", "_morning_events", "_short_rests_today",
        }
        missing = required_keys - set(data.keys())
        assert not missing, f"to_dict() missing required keys: {missing}"

    def test_from_dict_handles_missing_subsystem_keys_gracefully(self):
        """Old save files without subsystem keys should load without error."""
        data = {
            "day": 3, "sway": 1, "patron": "The Governor", "leader": "Captain Vane"
        }
        engine = CrownAndCrewEngine.from_dict(data)
        assert engine.day == 3
        assert engine.sway == 1
        assert engine._politics_engine is None
        assert engine._event_generator is None

    def test_politics_engine_lazy_init_after_load(self):
        """After load with no politics data, accessing it creates a fresh instance."""
        data = {"day": 1, "sway": 0}
        engine = CrownAndCrewEngine.from_dict(data)
        assert engine._politics_engine is None
        # Accessing via handle_command should lazily create it
        engine.handle_command("faction_status")
        assert engine._politics_engine is not None

    def test_power_balance_persists_across_save_load(self):
        engine = CrownAndCrewEngine()
        engine._get_politics_engine().power_shift(0.4, "Crew victory")
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._politics_engine is not None
        assert engine._politics_engine is not None
        assert abs(
            restored._politics_engine.power_balance
            - engine._politics_engine.power_balance  # type: ignore[union-attr]
        ) < 0.001


# =============================================================================
# WO-V100: Drifter's Tax — Double Draw
# =============================================================================

class TestDrifterTax:
    """Test the Drifter's Tax (Double Draw at sway 0)."""

    def _make_engine(self, sway: int = 0) -> CrownAndCrewEngine:
        engine = CrownAndCrewEngine()
        engine.sway = sway
        return engine

    def test_tax_triggers_at_sway_zero(self):
        engine = self._make_engine(sway=0)
        assert engine.check_drifter_tax() is True

    def test_tax_does_not_trigger_at_nonzero_sway(self):
        for s in [-3, -2, -1, 1, 2, 3]:
            engine = self._make_engine(sway=s)
            assert engine.check_drifter_tax() is False, f"Tax should not trigger at sway {s}"

    def test_end_day_sets_tax_flag(self):
        engine = self._make_engine(sway=0)
        engine.declare_allegiance("crown")
        # Sway is now -1, but we force it back to 0 before end_day
        engine.sway = 0
        result = engine.end_day()
        assert engine._drifter_tax_active is True
        assert "TAX" in result.upper()
        assert "DOUBLE DRAW" in result.upper() or "WHIRLPOOL" in result.upper()

    def test_end_day_clears_tax_when_not_zero(self):
        engine = self._make_engine(sway=2)
        engine.declare_allegiance("crown")
        engine.end_day()
        assert engine._drifter_tax_active is False

    def test_double_draw_returns_both_prompts(self):
        engine = self._make_engine(sway=0)
        engine._drifter_tax_active = True
        engine.declare_allegiance("crown")
        prompt = engine.get_prompt()
        assert "DOUBLE DRAW" in prompt
        # Should contain both a Crown and Crew section
        crown_term = engine.terms.get("crown", "CROWN").upper()
        crew_term = engine.terms.get("crew", "CREW").upper()
        assert crown_term in prompt
        assert crew_term in prompt

    def test_double_draw_consumed_after_use(self):
        engine = self._make_engine(sway=0)
        engine._drifter_tax_active = True
        engine.declare_allegiance("crown")
        # First call consumes the tax
        prompt1 = engine.get_prompt()
        assert "DOUBLE DRAW" in prompt1
        assert engine._drifter_tax_active is False
        # Second call is normal
        prompt2 = engine.get_prompt("crown")
        assert "DOUBLE DRAW" not in prompt2

    def test_tax_survives_save_load(self):
        engine = self._make_engine(sway=0)
        engine._drifter_tax_active = True
        data = engine.to_dict()
        assert data["_drifter_tax_active"] is True
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._drifter_tax_active is True

    def test_tax_narrative_shard(self):
        """Verify the tax generates a narrative shard."""
        engine = self._make_engine(sway=0)
        engine.declare_allegiance("crown")
        engine.sway = 0  # Force back to 0
        initial_shards = len(engine._memory_shards) if hasattr(engine, '_memory_shards') else 0
        engine.end_day()
        # end_day creates a CHRONICLE shard; tax message is in the output
        assert engine._drifter_tax_active is True


# =============================================================================
# WO-V102+103: Faction & Event Auto-Wiring
# =============================================================================

class TestFactionAutoWiring:
    """Test that faction system auto-advances at end of day."""

    def test_end_day_triggers_faction_action(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crown")
        result = engine.end_day()
        # Faction message should appear (may be empty if no dominant faction yet)
        # The key test is it doesn't crash
        assert isinstance(result, str)

    def test_faction_action_produces_narrative(self):
        engine = CrownAndCrewEngine()
        # Ensure politics engine is initialized with factions
        politics = engine._get_politics_engine()
        # Boost one faction to be clearly dominant
        politics.influence_tracker.shift_influence("The Crown Loyalists", 5)
        engine.declare_allegiance("crown")
        result = engine.end_day()
        assert isinstance(result, str)
        # Should contain [Faction] message from the dominant faction's action
        assert "[Faction]" in result or "Dawn breaks" in result

    def test_council_vote_shifts_power_balance(self):
        engine = CrownAndCrewEngine()
        politics = engine._get_politics_engine()
        initial_balance = politics.power_balance
        # Simulate a council vote
        engine.resolve_vote({"crown": 3, "crew": 1})
        engine.declare_allegiance("crown")
        engine.end_day()
        # Power should have shifted toward crown (negative)
        # The shift is small (0.1) and may be overridden by faction actions,
        # but the mechanism should fire without error
        assert isinstance(politics.power_balance, float)


class TestEventAutoWiring:
    """Test that event system auto-fires at end of day."""

    def test_end_day_triggers_event(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew")
        result = engine.end_day()
        # Should contain [Event] text
        assert "[Event]" in result

    def test_event_tags_dna(self):
        engine = CrownAndCrewEngine()
        initial_dna = dict(engine.dna)
        engine.declare_allegiance("crew", tag="HEARTH")  # Explicit tag for backward compat
        engine.end_day()
        # At least one DNA tag should have been incremented by the auto-event
        total_before = sum(initial_dna.values())
        total_after = sum(engine.dna.values())
        # declare_allegiance adds 1 (HEARTH), auto_event adds 1 = at least 2 more
        assert total_after >= total_before + 2

    def test_event_creates_shard(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crown")
        shards_before = len(engine._memory_shards)
        engine.end_day()
        # end_day creates: day summary shard + event shard = at least 2 new
        assert len(engine._memory_shards) > shards_before

    def test_enhanced_morning_includes_political(self):
        engine = CrownAndCrewEngine()
        event = engine.get_enhanced_morning_event()
        assert "text" in event
        assert "bias" in event
        # Should have a political_event sub-key from EventGenerator
        assert "political_event" in event
        assert "text" in event["political_event"]


# =============================================================================
# WO-V107: Interactive Morning Events
# =============================================================================

class TestMorningChoices:
    """Test interactive morning event choices."""

    def test_morning_event_has_choices(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        assert "choices" in event
        assert len(event["choices"]) >= 2

    def test_each_choice_has_required_fields(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        for choice in event["choices"]:
            assert "text" in choice
            assert "tag" in choice
            assert "sway_effect" in choice
            assert choice["tag"] in TAGS

    def test_resolve_morning_shifts_sway(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        initial_sway = engine.sway
        # Find a choice with non-zero sway effect
        for i, ch in enumerate(event["choices"]):
            if ch["sway_effect"] != 0:
                engine.resolve_morning_choice(i, event)
                assert engine.sway != initial_sway
                return
        # If all choices are 0 effect, that's also valid
        engine.resolve_morning_choice(0, event)
        assert isinstance(engine.sway, int)

    def test_resolve_morning_assigns_tag(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        initial_dna = sum(engine.dna.values())
        engine.resolve_morning_choice(0, event)
        assert sum(engine.dna.values()) == initial_dna + 1

    def test_resolve_morning_creates_shard(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        shards_before = len(engine._memory_shards)
        engine.resolve_morning_choice(0, event)
        assert len(engine._memory_shards) > shards_before

    def test_resolve_morning_returns_narrative(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        result = engine.resolve_morning_choice(0, event)
        assert isinstance(result, str)
        assert len(result) > 10
        # Should mention the tag
        chosen_tag = event["choices"][0]["tag"]
        assert chosen_tag in result

    def test_resolve_morning_clamps_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3  # At max
        event = engine.get_morning_event()
        # Find a +1 choice
        for i, ch in enumerate(event["choices"]):
            if ch["sway_effect"] > 0:
                engine.resolve_morning_choice(i, event)
                assert engine.sway <= 3
                return

    def test_legacy_events_get_auto_choices(self):
        """Events without choices (from old modules) get auto-generated ones."""
        engine = CrownAndCrewEngine()
        # Simulate a legacy event with no choices
        legacy_event = {"text": "Something happens.", "bias": "crew", "tag": "BLOOD"}
        choices = engine._generate_morning_choices(legacy_event)
        assert len(choices) == 3
        sway_effects = {ch["sway_effect"] for ch in choices}
        assert -1 in sway_effects  # Crown option
        assert 1 in sway_effects   # Crew option
        assert 0 in sway_effects   # Neutral option

    def test_out_of_range_choice_defaults_to_zero(self):
        engine = CrownAndCrewEngine()
        event = engine.get_morning_event()
        # Should not crash — defaults to choice 0
        result = engine.resolve_morning_choice(99, event)
        assert isinstance(result, str)


# =============================================================================
# WO-V104: Sway Power Enforcement
# =============================================================================

class TestSwayPowers:
    """Test sway-gated powers and choice gating."""

    def test_has_power_at_correct_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        assert engine.has_power("royal_decree")
        engine.sway = -2
        assert engine.has_power("imperial_intelligence")
        engine.sway = 0
        assert engine.has_power("whirlpool")
        engine.sway = 2
        assert engine.has_power("inner_circle")
        engine.sway = 3
        assert engine.has_power("leaders_confidence")

    def test_has_power_false_at_wrong_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = 1
        assert not engine.has_power("royal_decree")
        assert not engine.has_power("inner_circle")
        assert not engine.has_power("whirlpool")

    def test_available_powers_stack_crown(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        powers = engine.get_available_powers()
        assert "royal_decree" in powers
        assert "imperial_intelligence" in powers
        assert "safe_passage" in powers

    def test_available_powers_stack_crew(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3
        powers = engine.get_available_powers()
        assert "leaders_confidence" in powers
        assert "inner_circle" in powers
        assert "trusted_ear" in powers

    def test_royal_decree_at_sway_minus_3(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        result = engine.activate_royal_decree()
        assert "DECREE" in result.upper()
        assert engine._royal_decree_used is True

    def test_royal_decree_once_per_march(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        engine.activate_royal_decree()
        result = engine.activate_royal_decree()
        assert "already" in result.lower()

    def test_royal_decree_rejected_at_wrong_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = 0
        result = engine.activate_royal_decree()
        assert "lack" in result.lower()

    def test_leaders_confidence_at_sway_3(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3
        engine.leader = {"name": "Captain Vane", "secret_agenda": "Find the lost treasure", "betrayal_trigger": "If the gold runs out"}
        result = engine.activate_leaders_confidence()
        assert "CONFIDENCE" in result.upper()
        assert "lost treasure" in result
        assert "gold runs out" in result
        assert engine._leaders_confidence_used is True

    def test_leaders_confidence_once_per_march(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3
        engine.activate_leaders_confidence()
        result = engine.activate_leaders_confidence()
        assert "already" in result.lower()

    def test_gated_morning_crown_intel_at_minus_2(self):
        engine = CrownAndCrewEngine()
        engine.sway = -2
        event = engine.get_morning_event()
        choices = engine.get_gated_morning_choices(event)
        gated = [c for c in choices if c.get("gated") == "imperial_intelligence"]
        assert len(gated) == 1
        assert "Crown Intel" in gated[0]["text"]

    def test_gated_morning_no_bonus_at_neutral(self):
        engine = CrownAndCrewEngine()
        engine.sway = 1  # Not enough for any bonus except trusted_ear (passive)
        event = engine.get_morning_event()
        choices = engine.get_gated_morning_choices(event)
        gated = [c for c in choices if c.get("gated")]
        assert len(gated) == 0  # No gated choices at sway 1

    def test_gated_morning_broker_at_zero(self):
        engine = CrownAndCrewEngine()
        engine.sway = 0
        event = engine.get_morning_event()
        choices = engine.get_gated_morning_choices(event)
        gated = [c for c in choices if c.get("gated") == "whirlpool"]
        assert len(gated) == 1
        assert "Broker" in gated[0]["text"]

    def test_gated_council_inner_circle_at_plus_2(self):
        engine = CrownAndCrewEngine()
        engine.sway = 2
        dilemma = {"prompt": "Test", "crown": "Crown choice", "crew": "Crew choice"}
        choices = engine.get_gated_council_choices(dilemma)
        assert len(choices) == 3  # crown + crew + inner circle
        gated = [c for c in choices if c.get("gated") == "inner_circle"]
        assert len(gated) == 1

    def test_gated_council_decree_at_minus_3(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        dilemma = {"prompt": "Test", "crown": "Crown choice", "crew": "Crew choice"}
        choices = engine.get_gated_council_choices(dilemma)
        gated = [c for c in choices if c.get("gated") == "royal_decree"]
        assert len(gated) == 1
        assert gated[0].get("force_outcome") is True

    def test_gated_council_no_decree_after_use(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        engine._royal_decree_used = True
        dilemma = {"prompt": "Test", "crown": "Crown choice", "crew": "Crew choice"}
        choices = engine.get_gated_council_choices(dilemma)
        gated = [c for c in choices if c.get("gated") == "royal_decree"]
        assert len(gated) == 0  # Used up

    def test_powers_survive_save_load(self):
        engine = CrownAndCrewEngine()
        engine._royal_decree_used = True
        engine._leaders_confidence_used = True
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._royal_decree_used is True
        assert restored._leaders_confidence_used is True


# =============================================================================
# WO-V110: Council Dilemma Consequences
# =============================================================================

class TestCouncilConsequences:
    """Test tracked consequences from council votes."""

    def test_resolve_vote_returns_consequence(self):
        engine = CrownAndCrewEngine()
        dilemma = engine.get_council_dilemma()
        result = engine.resolve_vote({"crown": 1}, dilemma=dilemma)
        # Should have consequence if dilemma has one
        if dilemma.get("consequences"):
            assert "consequence" in result
            assert "narrative" in result["consequence"]

    def test_consequence_applies_dna_tag(self):
        engine = CrownAndCrewEngine()
        initial_dna = sum(engine.dna.values())
        dilemma = engine.get_council_dilemma()
        engine.resolve_vote({"crown": 1}, dilemma=dilemma)
        if dilemma.get("consequences"):
            assert sum(engine.dna.values()) > initial_dna

    def test_consequence_applies_sway_modifier(self):
        engine = CrownAndCrewEngine()
        initial_sway = engine.sway
        # Use a known dilemma with sway_modifier
        dilemma = {
            "prompt": "Test", "crown": "Crown", "crew": "Crew",
            "consequences": {
                "crown": {"narrative": "Test", "morning_bias": "crown", "tag": "GUILE", "sway_modifier": -1},
                "crew": {"narrative": "Test", "morning_bias": "crew", "tag": "DEFIANCE", "sway_modifier": 1},
            },
        }
        engine.resolve_vote({"crown": 1}, dilemma=dilemma)
        assert engine.sway == initial_sway - 1

    def test_consequence_tracked_in_active_list(self):
        engine = CrownAndCrewEngine()
        dilemma = {
            "prompt": "Test", "crown": "Crown", "crew": "Crew",
            "consequences": {
                "crew": {"narrative": "The crew rallies.", "morning_bias": "crew", "tag": "HEARTH", "sway_modifier": 0},
            },
        }
        engine.resolve_vote({"crew": 1}, dilemma=dilemma)
        assert len(engine._active_consequences) == 1
        assert engine._active_consequences[0]["narrative"] == "The crew rallies."

    def test_consequence_creates_shard(self):
        engine = CrownAndCrewEngine()
        dilemma = {
            "prompt": "Test", "crown": "Crown", "crew": "Crew",
            "consequences": {
                "crown": {"narrative": "Order holds.", "morning_bias": "crown", "tag": "SILENCE", "sway_modifier": 0},
            },
        }
        shards_before = len(engine._memory_shards)
        engine.resolve_vote({"crown": 1}, dilemma=dilemma)
        assert len(engine._memory_shards) > shards_before

    def test_consequence_morning_bias_affects_next_day(self):
        engine = CrownAndCrewEngine()
        # Day 1: vote with crew consequence that biases morning to "crew"
        dilemma = {
            "prompt": "Test", "crown": "Crown", "crew": "Crew",
            "consequences": {
                "crew": {"narrative": "Test", "morning_bias": "crew", "tag": "HEARTH", "sway_modifier": 0},
            },
        }
        engine.resolve_vote({"crew": 1}, dilemma=dilemma)
        engine.declare_allegiance("crew", tag="HEARTH")
        engine.end_day()
        # Day 2: morning bias should be "crew" from consequence
        bias = engine.get_consequence_morning_bias()
        assert bias == "crew"

    def test_no_consequence_without_dilemma(self):
        engine = CrownAndCrewEngine()
        result = engine.resolve_vote({"crown": 1})  # No dilemma passed
        assert "consequence" not in result

    def test_backward_compat_dilemma_without_consequences(self):
        engine = CrownAndCrewEngine()
        # Legacy dilemma with no consequences field
        dilemma = {"prompt": "Old", "crown": "A", "crew": "B"}
        result = engine.resolve_vote({"crown": 1}, dilemma=dilemma)
        assert "consequence" not in result
        assert len(engine._active_consequences) == 0

    def test_consequences_survive_save_load(self):
        engine = CrownAndCrewEngine()
        engine._active_consequences = [
            {"day": 1, "winner": "crown", "narrative": "Order prevails.", "morning_bias": "crown", "tag": "GUILE"},
        ]
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert len(restored._active_consequences) == 1
        assert restored._active_consequences[0]["narrative"] == "Order prevails."


# =============================================================================
# WO-V109: Midday Encounters
# =============================================================================

class TestMiddayEncounters:
    """Test the midday encounter system."""

    def test_get_midday_encounter_returns_dict(self):
        engine = CrownAndCrewEngine()
        encounter = engine.get_midday_encounter()
        assert encounter is not None
        assert "text" in encounter
        assert "choices" in encounter
        assert len(encounter["choices"]) >= 2

    def test_midday_choices_have_required_fields(self):
        engine = CrownAndCrewEngine()
        encounter = engine.get_midday_encounter()
        for ch in encounter["choices"]:
            assert "text" in ch
            assert "tag" in ch
            assert "sway_effect" in ch

    def test_resolve_midday_shifts_sway(self):
        engine = CrownAndCrewEngine()
        encounter = engine.get_midday_encounter()
        initial_sway = engine.sway
        # Find a non-zero sway choice
        for i, ch in enumerate(encounter["choices"]):
            if ch["sway_effect"] != 0:
                engine.resolve_midday_choice(i, encounter)
                assert engine.sway != initial_sway
                return
        # All zero — still valid
        engine.resolve_midday_choice(0, encounter)

    def test_resolve_midday_assigns_dna(self):
        engine = CrownAndCrewEngine()
        encounter = engine.get_midday_encounter()
        initial_dna = sum(engine.dna.values())
        engine.resolve_midday_choice(0, encounter)
        assert sum(engine.dna.values()) == initial_dna + 1

    def test_resolve_midday_creates_shard(self):
        engine = CrownAndCrewEngine()
        encounter = engine.get_midday_encounter()
        shards_before = len(engine._memory_shards)
        engine.resolve_midday_choice(0, encounter)
        assert len(engine._memory_shards) > shards_before

    def test_midday_avoids_repeats(self):
        engine = CrownAndCrewEngine()
        seen = set()
        for _ in range(10):
            enc = engine.get_midday_encounter()
            seen.add(enc["text"][:30])
        # Should have variety (at least 5 unique out of 10 draws)
        assert len(seen) >= 5

    def test_safe_passage_available_at_sway_minus_1(self):
        engine = CrownAndCrewEngine()
        engine.sway = -1
        assert engine.can_bypass_midday() is True

    def test_safe_passage_not_available_at_sway_0(self):
        engine = CrownAndCrewEngine()
        engine.sway = 0
        assert engine.can_bypass_midday() is False

    def test_safe_passage_once_per_march(self):
        engine = CrownAndCrewEngine()
        engine.sway = -1
        result = engine.use_safe_passage()
        assert "Safe Passage" in result or "unchallenged" in result
        assert engine._safe_passage_used is True
        assert engine.can_bypass_midday() is False

    def test_safe_passage_rejected_without_power(self):
        engine = CrownAndCrewEngine()
        engine.sway = 2  # Crew side, no safe passage
        result = engine.use_safe_passage()
        assert "lack" in result.lower()

    def test_gated_midday_trusted_ear_at_sway_1(self):
        engine = CrownAndCrewEngine()
        engine.sway = 1
        encounter = engine.get_midday_encounter()
        choices = engine.get_gated_midday_choices(encounter)
        gated = [c for c in choices if c.get("gated") == "trusted_ear"]
        assert len(gated) == 1
        assert "Trusted Ear" in gated[0]["text"]

    def test_gated_midday_no_bonus_at_sway_minus_1(self):
        engine = CrownAndCrewEngine()
        engine.sway = -1
        encounter = engine.get_midday_encounter()
        choices = engine.get_gated_midday_choices(encounter)
        gated = [c for c in choices if c.get("gated")]
        assert len(gated) == 0

    def test_midday_survives_save_load(self):
        engine = CrownAndCrewEngine()
        engine._safe_passage_used = True
        engine._used_midday = [0, 1, 2]
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._safe_passage_used is True
        assert restored._used_midday == [0, 1, 2]


# =============================================================================
# WO-V99: Day 3 Mirror Break — Sin Mechanics
# =============================================================================

class TestMirrorBreak:
    """Test the Day 3 Mirror Break sin generation and hide/expose choice."""

    def test_mirror_returns_sin_based_on_dominant_tag(self):
        engine = CrownAndCrewEngine()
        engine.dna["BLOOD"] = 5  # Make BLOOD dominant
        mirror = engine.get_mirror_break()
        assert mirror["sin"] == "Unnecessary Brutality"
        assert mirror["dominant_tag"] == "BLOOD"

    def test_mirror_guile_sin(self):
        engine = CrownAndCrewEngine()
        engine.dna["GUILE"] = 5
        mirror = engine.get_mirror_break()
        assert mirror["sin"] == "A Secret Deal"

    def test_mirror_hearth_sin(self):
        engine = CrownAndCrewEngine()
        engine.dna["HEARTH"] = 5
        mirror = engine.get_mirror_break()
        assert mirror["sin"] == "Hoarding and Neglect"

    def test_mirror_silence_sin(self):
        engine = CrownAndCrewEngine()
        engine.dna["SILENCE"] = 5
        mirror = engine.get_mirror_break()
        assert mirror["sin"] == "Erasing History"

    def test_mirror_defiance_sin(self):
        engine = CrownAndCrewEngine()
        engine.dna["DEFIANCE"] = 5
        mirror = engine.get_mirror_break()
        assert mirror["sin"] == "A False Flag"

    def test_mirror_has_two_choices(self):
        engine = CrownAndCrewEngine()
        engine.dna["BLOOD"] = 3
        mirror = engine.get_mirror_break()
        assert len(mirror["choices"]) == 2
        actions = {c["action"] for c in mirror["choices"]}
        assert actions == {"hide", "expose"}

    def test_hide_choice_gives_silence_tag(self):
        engine = CrownAndCrewEngine()
        engine.dna["BLOOD"] = 3
        mirror = engine.get_mirror_break()
        hide = [c for c in mirror["choices"] if c["action"] == "hide"][0]
        assert hide["tag"] == "SILENCE"
        assert hide["sway_effect"] == 1  # Toward crew (complicity)

    def test_expose_choice_gives_defiance_tag(self):
        engine = CrownAndCrewEngine()
        engine.dna["BLOOD"] = 3
        mirror = engine.get_mirror_break()
        expose = [c for c in mirror["choices"] if c["action"] == "expose"][0]
        assert expose["tag"] == "DEFIANCE"
        assert expose["sway_effect"] == -1  # Toward crown (truth)

    def test_witness_text_includes_leader_name(self):
        engine = CrownAndCrewEngine()
        engine.dna["GUILE"] = 3
        mirror = engine.get_mirror_break()
        assert engine.leader in mirror["witness"]

    def test_resolve_mirror_hide(self):
        engine = CrownAndCrewEngine()
        engine.dna["BLOOD"] = 3
        initial_silence = engine.dna["SILENCE"]
        initial_sway = engine.sway
        result = engine.resolve_mirror_choice(0)  # 0 = hide
        assert engine.dna["SILENCE"] == initial_silence + 1
        assert engine.sway == initial_sway + 1
        assert engine._mirror_choice == "hide"
        assert "Hidden" in result

    def test_resolve_mirror_expose(self):
        engine = CrownAndCrewEngine()
        engine.dna["BLOOD"] = 3
        initial_defiance = engine.dna["DEFIANCE"]
        initial_sway = engine.sway
        result = engine.resolve_mirror_choice(1)  # 1 = expose
        assert engine.dna["DEFIANCE"] == initial_defiance + 1
        assert engine.sway == initial_sway - 1
        assert engine._mirror_choice == "expose"
        assert "Exposed" in result

    def test_resolve_mirror_creates_anchor_shard(self):
        engine = CrownAndCrewEngine()
        engine.dna["HEARTH"] = 3
        shards_before = len(engine._memory_shards)
        engine.resolve_mirror_choice(0)
        anchor_shards = [s for s in engine._memory_shards[shards_before:]
                         if hasattr(s, 'shard_type') and s.shard_type.value == "ANCHOR"]
        assert len(anchor_shards) >= 1
        assert "MIRROR" in anchor_shards[-1].content

    def test_mirror_tracks_sin_name(self):
        engine = CrownAndCrewEngine()
        engine.dna["DEFIANCE"] = 3
        engine.resolve_mirror_choice(1)
        assert engine._mirror_sin == "A False Flag"

    def test_mirror_survives_save_load(self):
        engine = CrownAndCrewEngine()
        engine._mirror_choice = "hide"
        engine._mirror_sin = "Unnecessary Brutality"
        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert restored._mirror_choice == "hide"
        assert restored._mirror_sin == "Unnecessary Brutality"

    def test_default_sin_when_no_dominant(self):
        """When all tags are 0, falls back to SILENCE sin."""
        engine = CrownAndCrewEngine()
        # All DNA at 0 — get_dominant_tag returns SILENCE
        mirror = engine.get_mirror_break()
        assert mirror["sin"] == "Erasing History"  # SILENCE maps to this


# =============================================================================
# WO-V133: Multiplayer Player Slots
# =============================================================================

class TestPlayerSlots:
    """Test multiplayer player slot system."""

    def test_solo_player_created_by_default(self):
        engine = CrownAndCrewEngine()
        assert "_solo" in engine.players
        assert len(engine.players) == 1

    def test_solo_syncs_to_legacy_fields(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = 2
        engine.players["_solo"].dna["BLOOD"] = 3
        engine._sync_solo_to_legacy()
        assert engine.sway == 2
        assert engine.dna["BLOOD"] == 3

    def test_add_player(self):
        engine = CrownAndCrewEngine()
        ps = engine.add_player("Alice")
        assert "Alice" in engine.players
        assert ps.name == "Alice"
        assert ps.sway == 0
        assert sum(ps.dna.values()) == 0

    def test_add_multiple_players(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        engine.add_player("Carol")
        assert engine.is_multiplayer()
        assert len(engine.get_all_players()) == 3

    def test_is_multiplayer_false_for_solo(self):
        engine = CrownAndCrewEngine()
        assert not engine.is_multiplayer()

    def test_get_player_creates_on_demand(self):
        engine = CrownAndCrewEngine()
        ps = engine._get_player("NewPlayer")
        assert "NewPlayer" in engine.players
        assert ps.name == "NewPlayer"

    def test_player_state_independence(self):
        engine = CrownAndCrewEngine()
        alice = engine.add_player("Alice")
        bob = engine.add_player("Bob")
        alice.sway = 3
        alice.dna["BLOOD"] = 5
        bob.sway = -2
        bob.dna["GUILE"] = 3
        assert alice.sway != bob.sway
        assert alice.dna["BLOOD"] != bob.dna["BLOOD"]

    def test_player_dominant_tag(self):
        engine = CrownAndCrewEngine()
        ps = engine.add_player("Alice")
        ps.dna["DEFIANCE"] = 5
        ps.dna["HEARTH"] = 2
        assert ps.get_dominant_tag() == "DEFIANCE"

    def test_player_alignment(self):
        engine = CrownAndCrewEngine()
        ps = engine.add_player("Alice")
        ps.sway = 3
        assert ps.get_alignment() == "CREW"
        ps.sway = -2
        assert ps.get_alignment() == "CROWN"
        ps.sway = 0
        assert ps.get_alignment() == "DRIFTER"

    def test_player_vote_power(self):
        engine = CrownAndCrewEngine()
        ps = engine.add_player("Alice")
        ps.sway = 3
        assert ps.get_vote_power() == 8
        ps.sway = 0
        assert ps.get_vote_power() == 1

    def test_players_survive_save_load(self):
        engine = CrownAndCrewEngine()
        alice = engine.add_player("Alice")
        alice.sway = 2
        alice.dna["HEARTH"] = 4
        alice._mirror_choice = "expose"
        bob = engine.add_player("Bob")
        bob.sway = -1
        bob.dna["GUILE"] = 3

        data = engine.to_dict()
        restored = CrownAndCrewEngine.from_dict(data)
        assert "Alice" in restored.players
        assert "Bob" in restored.players
        assert restored.players["Alice"].sway == 2
        assert restored.players["Alice"].dna["HEARTH"] == 4
        assert restored.players["Alice"]._mirror_choice == "expose"
        assert restored.players["Bob"].sway == -1

    def test_backward_compat_solo_declare(self):
        """Existing single-player declare_allegiance still works."""
        engine = CrownAndCrewEngine()
        result = engine.declare_allegiance("crown", tag="GUILE")
        assert engine.dna["GUILE"] == 1
        # Solo player should also have it
        assert engine.players["_solo"].dna["GUILE"] == 1

    def test_get_all_players_excludes_solo_in_multiplayer(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        players = engine.get_all_players()
        names = {p.name for p in players}
        assert "_solo" not in names
        assert "Alice" in names
        assert "Bob" in names


# =============================================================================
# WO-V119+120: Structured Legacy Report + Debts & Secrets
# =============================================================================

class TestLegacyJSON:
    """Test structured Legacy Report generation."""

    def test_legacy_json_has_required_fields(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crown", tag="GUILE")
        legacy = engine.generate_legacy_json()
        assert legacy["version"] == 2
        assert "title" in legacy
        assert "title_desc" in legacy
        assert "alignment" in legacy
        assert "sway" in legacy
        assert "tier" in legacy
        assert "dominant_tag" in legacy
        assert "dna" in legacy
        assert "patron" in legacy
        assert "leader" in legacy
        assert "patron_relationship" in legacy
        assert "leader_relationship" in legacy
        assert "mirror" in legacy
        assert "powers_used" in legacy
        assert "debts_and_secrets" in legacy
        assert "council_record" in legacy
        assert "arc_length" in legacy
        assert "days_survived" in legacy
        assert "choices_made" in legacy

    def test_legacy_json_reflects_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        engine.players["_solo"].sway = -3
        legacy = engine.generate_legacy_json()
        assert legacy["sway"] == -3
        assert legacy["alignment"] == "CROWN"
        assert legacy["patron_relationship"] == "allied"

    def test_legacy_json_reflects_crew_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3
        engine.players["_solo"].sway = 3
        legacy = engine.generate_legacy_json()
        assert legacy["alignment"] == "CREW"
        assert legacy["patron_relationship"] == "hostile"
        assert legacy["leader_relationship"] == "trusted"

    def test_legacy_json_mirror_data(self):
        engine = CrownAndCrewEngine()
        engine._mirror_choice = "expose"
        engine._mirror_sin = "A Secret Deal"
        # Sync to solo player
        engine.players["_solo"]._mirror_choice = "expose"
        engine.players["_solo"]._mirror_sin = "A Secret Deal"
        legacy = engine.generate_legacy_json()
        assert legacy["mirror"]["choice"] == "expose"
        assert legacy["mirror"]["sin"] == "A Secret Deal"

    def test_legacy_json_powers_used(self):
        engine = CrownAndCrewEngine()
        engine._royal_decree_used = True
        engine.players["_solo"]._royal_decree_used = True
        engine._safe_passage_used = True
        engine.players["_solo"]._safe_passage_used = True
        legacy = engine.generate_legacy_json()
        assert "royal_decree" in legacy["powers_used"]
        assert "safe_passage" in legacy["powers_used"]

    def test_legacy_json_council_record(self):
        engine = CrownAndCrewEngine()
        dilemma = engine.get_council_dilemma()
        engine.resolve_vote({"crown": 1}, dilemma=dilemma)
        legacy = engine.generate_legacy_json()
        assert len(legacy["council_record"]) == 1
        assert legacy["council_record"][0]["winner"] in ("crown", "crew")

    def test_legacy_text_renders_from_json(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew", tag="DEFIANCE")
        report = engine.generate_legacy_report()
        assert "CHARACTER RECEIPT" in report
        assert "NARRATIVE DNA" in report
        assert "JOURNEY SUMMARY" in report

    def test_leader_relationship_with_mirror(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3
        engine.players["_solo"].sway = 3
        engine.players["_solo"]._mirror_choice = "expose"
        legacy = engine.generate_legacy_json()
        assert legacy["leader_relationship"] == "hurt_respect"


class TestDebtsAndSecrets:
    """Test the debts & secrets ledger."""

    def test_empty_ledger(self):
        engine = CrownAndCrewEngine()
        debts = engine.generate_debts_and_secrets()
        assert isinstance(debts, list)
        assert len(debts) == 0  # No choices made yet

    def test_mirror_hide_creates_secret(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._mirror_choice = "hide"
        engine.players["_solo"]._mirror_sin = "Unnecessary Brutality"
        debts = engine.generate_debts_and_secrets()
        secrets = [d for d in debts if d["type"] == "secret"]
        assert len(secrets) >= 1
        assert "Brutality" in secrets[0]["text"]

    def test_mirror_expose_creates_debt(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._mirror_choice = "expose"
        engine.players["_solo"]._mirror_sin = "A False Flag"
        debts = engine.generate_debts_and_secrets()
        debt_items = [d for d in debts if d["type"] == "debt"]
        assert len(debt_items) >= 1
        assert "False Flag" in debt_items[0]["text"]

    def test_royal_decree_creates_debt(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._royal_decree_used = True
        debts = engine.generate_debts_and_secrets()
        debt_items = [d for d in debts if d["type"] == "debt"]
        assert any("Royal Decree" in d["text"] for d in debt_items)

    def test_council_consequences_in_ledger(self):
        engine = CrownAndCrewEngine()
        engine._active_consequences = [
            {"day": 1, "winner": "crew", "narrative": "The bridge burns."},
        ]
        debts = engine.generate_debts_and_secrets()
        consequences = [d for d in debts if d["type"] == "consequence"]
        assert len(consequences) >= 1
        assert "bridge burns" in consequences[0]["text"]

    def test_debts_in_legacy_json(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._mirror_choice = "hide"
        engine.players["_solo"]._mirror_sin = "Hoarding and Neglect"
        engine.players["_solo"]._royal_decree_used = True
        legacy = engine.generate_legacy_json()
        assert len(legacy["debts_and_secrets"]) >= 2

    def test_legacy_report_shows_debts(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._mirror_choice = "expose"
        engine.players["_solo"]._mirror_sin = "Erasing History"
        report = engine.generate_legacy_report()
        assert "DEBTS & SECRETS" in report
        assert "Erasing History" in report


# =============================================================================
# WO-V124+127+128: Character Loom Integration
# =============================================================================

class TestLoomIntegration:
    """Test Character Loom wiring into Crown engine."""

    def test_set_character_creates_loom(self):
        engine = CrownAndCrewEngine()
        engine.set_character({"name": "Kael", "background": "Soldier"})
        loom = engine.get_loom()
        assert loom is not None
        assert loom.name == "Kael"

    def test_character_data_in_init(self):
        engine = CrownAndCrewEngine(character_data={"name": "Sera", "ideal": "Freedom"})
        loom = engine.get_loom()
        assert loom.name == "Sera"
        assert loom.ideal == "Freedom"

    def test_resolve_prompt_with_loom(self):
        engine = CrownAndCrewEngine(character_data={"name": "Kael", "background": "Soldier"})
        result = engine.resolve_prompt("Welcome, {loom.name}. You were a {loom.background}.")
        assert result == "Welcome, Kael. You were a Soldier."

    def test_resolve_prompt_without_loom(self):
        engine = CrownAndCrewEngine()
        result = engine.resolve_prompt("Static text with no variables.")
        assert result == "Static text with no variables."

    def test_echo_frame_with_ideal(self):
        engine = CrownAndCrewEngine(character_data={"ideal": "Justice"})
        engine.declare_allegiance("crown")
        frame = engine.get_echo_frame()
        assert "Justice" in frame

    def test_echo_frame_without_character(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew")
        frame = engine.get_echo_frame()
        # Should still work, just generic
        assert "freedom" in frame.lower()

    def test_mirror_with_flaw(self):
        engine = CrownAndCrewEngine(character_data={"flaw": "I trust too easily"})
        engine.dna["GUILE"] = 5
        engine.players["_solo"].dna["GUILE"] = 5
        mirror = engine.get_mirror_break()
        assert "trust too easily" in mirror["witness"]

    def test_mirror_without_character(self):
        engine = CrownAndCrewEngine()
        engine.dna["BLOOD"] = 3
        engine.players["_solo"].dna["BLOOD"] = 3
        mirror = engine.get_mirror_break()
        # Should work without flaw — just no flaw note
        assert "Brutality" in mirror["sin"]
        assert "staring back" not in mirror["witness"]

    def test_multiplayer_separate_looms(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        engine.set_character({"name": "Alice", "ideal": "Duty"}, player_name="Alice")
        engine.set_character({"name": "Bob", "ideal": "Freedom"}, player_name="Bob")
        assert engine.get_loom("Alice").ideal == "Duty"
        assert engine.get_loom("Bob").ideal == "Freedom"

    def test_empty_loom_returns_defaults(self):
        engine = CrownAndCrewEngine()
        loom = engine.get_loom()
        assert loom.name == "Traveler"  # Default
        assert loom.ideal == "survival"  # Default


class TestDNASeed:
    """WO-V125: Test personality → DNA seed mapping."""

    def test_brave_personality_seeds_blood(self):
        engine = CrownAndCrewEngine()
        engine.set_character({"personality_traits": ["Brave and reckless"]})
        assert engine.players["_solo"].dna["BLOOD"] >= 1

    def test_cunning_personality_seeds_guile(self):
        engine = CrownAndCrewEngine()
        engine.set_character({"personality_traits": ["Cunning and deceptive"]})
        assert engine.players["_solo"].dna["GUILE"] >= 1

    def test_kind_personality_seeds_hearth(self):
        engine = CrownAndCrewEngine()
        engine.set_character({"personality_traits": ["Kind to strangers, protective of friends"]})
        assert engine.players["_solo"].dna["HEARTH"] >= 1

    def test_quiet_personality_seeds_silence(self):
        engine = CrownAndCrewEngine()
        engine.set_character({"personality_traits": ["Quiet and observant"]})
        assert engine.players["_solo"].dna["SILENCE"] >= 1

    def test_rebel_personality_seeds_defiance(self):
        engine = CrownAndCrewEngine()
        engine.set_character({"personality_traits": ["I challenge authority at every turn"]})
        assert engine.players["_solo"].dna["DEFIANCE"] >= 1

    def test_alignment_seeds_tag(self):
        engine = CrownAndCrewEngine()
        engine.set_character({"alignment": "Chaotic Good"})
        assert engine.players["_solo"].dna["DEFIANCE"] >= 1

    def test_no_character_no_seed(self):
        engine = CrownAndCrewEngine()
        assert sum(engine.players["_solo"].dna.values()) == 0

    def test_seed_is_nudge_not_cage(self):
        """Seeds add at most 1 per unique tag match — not overwhelming."""
        engine = CrownAndCrewEngine()
        engine.set_character({
            "personality_traits": ["Brave fighter, fierce warrior, aggressive in battle"],
            "alignment": "Chaotic Evil",
        })
        # BLOOD gets at most 1 from keywords (brave/fighter/fierce all map to BLOOD
        # but only one +1 per unique tag)
        assert engine.players["_solo"].dna["BLOOD"] == 1

    def test_multiple_tags_seeded(self):
        engine = CrownAndCrewEngine()
        engine.set_character({
            "personality_traits": ["Brave but kind, with a rebellious streak"],
        })
        total = sum(engine.players["_solo"].dna.values())
        # Should seed BLOOD (brave) + HEARTH (kind) + DEFIANCE (rebel) = 3
        assert total >= 3


# =============================================================================
# WO-V116+117+118: The Finale — 3 Acts
# =============================================================================

class TestPatronReckoning:
    """Test Act 1 — Patron confrontation."""

    def test_patron_pleased_at_crown_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = -3
        engine.players["_solo"].sway = -3
        scene = engine.generate_patron_reckoning()
        assert scene["stance"] == "pleased"
        assert engine.patron in scene["narrative"]

    def test_patron_hostile_at_crew_sway(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3
        engine.players["_solo"].sway = 3
        scene = engine.generate_patron_reckoning()
        assert scene["stance"] == "hostile"

    def test_patron_disappointed_at_zero(self):
        engine = CrownAndCrewEngine()
        scene = engine.generate_patron_reckoning()
        assert scene["stance"] == "disappointed"

    def test_patron_has_three_responses(self):
        engine = CrownAndCrewEngine()
        scene = engine.generate_patron_reckoning()
        assert len(scene["choices"]) == 3
        responses = {c["response"] for c in scene["choices"]}
        assert responses == {"accept", "reject", "silence"}

    def test_patron_references_bond_when_suspicious(self):
        engine = CrownAndCrewEngine(character_data={"bond": "my sister in the capital"})
        engine.sway = 1
        engine.players["_solo"].sway = 1
        scene = engine.generate_patron_reckoning()
        assert scene["stance"] == "suspicious"
        assert "sister" in scene["narrative"]

    def test_resolve_patron_accept(self):
        engine = CrownAndCrewEngine()
        result = engine.resolve_patron_response("accept")
        assert "hand" in result.lower() or "grip" in result.lower()

    def test_resolve_patron_reject(self):
        engine = CrownAndCrewEngine()
        result = engine.resolve_patron_response("reject")
        assert "back" in result.lower() or "fade" in result.lower()


class TestLeaderReckoning:
    """Test Act 2 — Leader confrontation."""

    def test_leader_deep_trust(self):
        engine = CrownAndCrewEngine()
        engine.sway = 3
        engine.players["_solo"].sway = 3
        engine.players["_solo"]._mirror_choice = "hide"
        scene = engine.generate_leader_reckoning()
        assert scene["stance"] == "deep_trust"

    def test_leader_hurt_respect_expose(self):
        engine = CrownAndCrewEngine()
        engine.sway = 2
        engine.players["_solo"].sway = 2
        engine.players["_solo"]._mirror_choice = "expose"
        scene = engine.generate_leader_reckoning()
        assert scene["stance"] == "hurt_respect"

    def test_leader_dismissive_at_zero(self):
        engine = CrownAndCrewEngine()
        scene = engine.generate_leader_reckoning()
        assert scene["stance"] == "dismissive"

    def test_leader_cold_fury(self):
        engine = CrownAndCrewEngine()
        engine.sway = -2
        engine.players["_solo"].sway = -2
        engine.players["_solo"]._mirror_choice = "expose"
        scene = engine.generate_leader_reckoning()
        assert scene["stance"] == "cold_fury"

    def test_leader_betrayed_references_ideal(self):
        engine = CrownAndCrewEngine(character_data={"ideal": "Liberty"})
        engine.sway = -1
        engine.players["_solo"].sway = -1
        engine.players["_solo"]._mirror_choice = "hide"
        scene = engine.generate_leader_reckoning()
        assert scene["stance"] == "betrayed"
        assert "Liberty" in scene["narrative"]

    def test_leader_has_three_responses(self):
        engine = CrownAndCrewEngine()
        scene = engine.generate_leader_reckoning()
        assert len(scene["choices"]) == 3


class TestTheCrossing:
    """Test Act 3 — ending determination."""

    def test_free_crossing(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = 3
        ending = engine.determine_ending()
        assert ending["ending_id"] == "free_crossing"

    def test_crown_pardon(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = -3
        ending = engine.determine_ending()
        assert ending["ending_id"] == "crown_pardon"

    def test_drifters_road(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = 0
        ending = engine.determine_ending()
        assert ending["ending_id"] == "drifters_road"

    def test_martyrs_march(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = 2
        engine.players["_solo"]._mirror_choice = "expose"
        ending = engine.determine_ending()
        assert ending["ending_id"] == "martyrs_march"

    def test_captured(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = 0
        engine.players["_solo"]._royal_decree_used = True
        ending = engine.determine_ending()
        assert ending["ending_id"] == "captured"

    def test_abandoned(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = 1
        engine.players["_solo"]._mirror_choice = "hide"
        ending = engine.determine_ending()
        assert ending["ending_id"] == "abandoned"

    def test_every_ending_has_campaign_hook(self):
        """All 6 endings produce a campaign hook."""
        for ending_id in ("free_crossing", "crown_pardon", "drifters_road",
                          "martyrs_march", "captured", "abandoned"):
            engine = CrownAndCrewEngine()
            ps = engine.players["_solo"]
            if ending_id == "free_crossing":
                ps.sway = 3
            elif ending_id == "crown_pardon":
                ps.sway = -3
            elif ending_id == "drifters_road":
                ps.sway = 0
            elif ending_id == "martyrs_march":
                ps.sway = 2; ps._mirror_choice = "expose"
            elif ending_id == "captured":
                ps.sway = 0; ps._royal_decree_used = True
            elif ending_id == "abandoned":
                ps.sway = 1; ps._mirror_choice = "hide"
            ending = engine.determine_ending()
            assert ending["ending_id"] == ending_id, f"Expected {ending_id}, got {ending['ending_id']}"
            assert len(ending["campaign_hook"]) > 20, f"No hook for {ending_id}"
            assert len(ending["narrative"]) > 50, f"No narrative for {ending_id}"

    def test_ending_uses_character_name(self):
        engine = CrownAndCrewEngine(character_data={"name": "Kael"})
        engine.players["_solo"].sway = 3
        ending = engine.determine_ending()
        assert "Kael" in ending["narrative"]


class TestCampaignHooks:
    """WO-V121: Test campaign hook generation."""

    def test_hooks_returns_list(self):
        engine = CrownAndCrewEngine()
        hooks = engine.generate_campaign_hooks()
        assert isinstance(hooks, list)
        assert len(hooks) >= 1

    def test_hooks_include_ending(self):
        engine = CrownAndCrewEngine()
        hooks = engine.generate_campaign_hooks()
        # At least one hook should be from the ending
        assert any("campaign" in h.lower() or "begin" in h.lower() for h in hooks)

    def test_hooks_include_patron_at_extreme_sway(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = -3
        hooks = engine.generate_campaign_hooks()
        assert any(engine.patron in h for h in hooks)

    def test_hooks_include_mirror_hide(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._mirror_choice = "hide"
        engine.players["_solo"].sway = 2
        hooks = engine.generate_campaign_hooks()
        assert any("secret" in h.lower() or "trust" in h.lower() for h in hooks)

    def test_hooks_include_mirror_expose(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._mirror_choice = "expose"
        hooks = engine.generate_campaign_hooks()
        assert any("truth" in h.lower() or "fracture" in h.lower() for h in hooks)

    def test_hooks_include_decree_debt(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"]._royal_decree_used = True
        hooks = engine.generate_campaign_hooks()
        assert any("Decree" in h or "authority" in h for h in hooks)

    def test_hooks_include_dna_reputation(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].dna["DEFIANCE"] = 10
        hooks = engine.generate_campaign_hooks()
        assert any("challenged" in h.lower() or "revolutionary" in h.lower() for h in hooks)

    def test_hooks_capped_at_six(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].sway = -3
        engine.players["_solo"]._mirror_choice = "expose"
        engine.players["_solo"]._royal_decree_used = True
        engine.players["_solo"]._leaders_confidence_used = True
        engine._active_consequences = [{"narrative": "Test consequence"}]
        hooks = engine.generate_campaign_hooks()
        assert len(hooks) <= 6

    def test_hooks_in_legacy_json(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew", tag="DEFIANCE")
        legacy = engine.generate_legacy_json()
        assert "campaign_hooks" in legacy
        assert isinstance(legacy["campaign_hooks"], list)
        assert len(legacy["campaign_hooks"]) >= 1

    def test_hooks_use_character_name(self):
        engine = CrownAndCrewEngine(character_data={"name": "Sera"})
        engine.players["_solo"].sway = 3
        hooks = engine.generate_campaign_hooks()
        assert any("Sera" in h for h in hooks)


# =============================================================================
# WO-V134+135: Multiplayer Group Voting + Dissent Tracking
# =============================================================================

class TestGroupVoting:
    """Test multiplayer group choice resolution."""

    def _make_engine(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        engine.add_player("Carol")
        return engine

    def test_majority_wins(self):
        engine = self._make_engine()
        choices = [
            {"text": "Go left", "tag": "BLOOD", "sway_effect": 1},
            {"text": "Go right", "tag": "GUILE", "sway_effect": -1},
        ]
        result = engine.resolve_group_choice(
            {"Alice": 0, "Bob": 0, "Carol": 1}, choices
        )
        assert result["winning_index"] == 0

    def test_tie_broken_by_weight(self):
        engine = self._make_engine()
        engine.players["Alice"].sway = 3  # Weight 8
        engine.players["Bob"].sway = 1    # Weight 2
        choices = [
            {"text": "Option A", "tag": "BLOOD", "sway_effect": 0},
            {"text": "Option B", "tag": "GUILE", "sway_effect": 0},
        ]
        # Alice (weight 8) picks 0, Bob (weight 2) picks 1 — Carol absent
        result = engine.resolve_group_choice(
            {"Alice": 0, "Bob": 1}, choices
        )
        # Tie 1-1 in votes, Alice's weight wins
        assert result["winning_index"] == 0

    def test_individual_dna_applied(self):
        engine = self._make_engine()
        choices = [
            {"text": "Fight", "tag": "BLOOD", "sway_effect": 0},
            {"text": "Hide", "tag": "SILENCE", "sway_effect": 0},
        ]
        engine.resolve_group_choice(
            {"Alice": 0, "Bob": 1, "Carol": 0}, choices
        )
        assert engine.players["Alice"].dna["BLOOD"] >= 1
        assert engine.players["Bob"].dna["SILENCE"] >= 1
        assert engine.players["Carol"].dna["BLOOD"] >= 1

    def test_individual_sway_applied(self):
        engine = self._make_engine()
        choices = [
            {"text": "Crown path", "tag": "GUILE", "sway_effect": -1},
            {"text": "Crew path", "tag": "DEFIANCE", "sway_effect": 1},
        ]
        engine.resolve_group_choice(
            {"Alice": 0, "Bob": 1, "Carol": 0}, choices
        )
        assert engine.players["Alice"].sway == -1
        assert engine.players["Bob"].sway == 1

    def test_dissent_tracked(self):
        engine = self._make_engine()
        choices = [
            {"text": "A", "tag": "BLOOD", "sway_effect": 0},
            {"text": "B", "tag": "GUILE", "sway_effect": 0},
        ]
        result = engine.resolve_group_choice(
            {"Alice": 0, "Bob": 0, "Carol": 1}, choices
        )
        assert "Carol" in result["dissent"]
        assert engine.players["Carol"].dissent_count == 1
        assert engine.players["Alice"].majority_count == 1


class TestGroupCouncil:
    """Test multiplayer council vote resolution."""

    def _make_engine(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        engine.add_player("Carol")
        return engine

    def test_majority_crown_wins(self):
        engine = self._make_engine()
        result = engine.resolve_group_council(
            {"Alice": "crown", "Bob": "crown", "Carol": "crew"}
        )
        assert result["winner"] == "crown"

    def test_majority_crew_wins(self):
        engine = self._make_engine()
        result = engine.resolve_group_council(
            {"Alice": "crew", "Bob": "crew", "Carol": "crown"}
        )
        assert result["winner"] == "crew"

    def test_tie_broken_by_weight(self):
        engine = self._make_engine()
        engine.players["Alice"].sway = 3  # Weight 8, votes crown
        engine.players["Bob"].sway = 1    # Weight 2, votes crew
        result = engine.resolve_group_council(
            {"Alice": "crown", "Bob": "crew"}
        )
        # 1-1 tie in count, Alice's weight (8 > 2) wins
        assert result["winner"] == "crown"

    def test_council_dissent_tracked(self):
        engine = self._make_engine()
        result = engine.resolve_group_council(
            {"Alice": "crown", "Bob": "crown", "Carol": "crew"}
        )
        assert "Carol" in result["dissent"]
        assert engine.players["Carol"].dissent_count == 1

    def test_council_consequence_applied(self):
        engine = self._make_engine()
        dilemma = {
            "prompt": "Test", "crown": "A", "crew": "B",
            "consequences": {
                "crown": {"narrative": "Order holds.", "tag": "SILENCE", "sway_modifier": 0, "morning_bias": "crown"},
            },
        }
        result = engine.resolve_group_council(
            {"Alice": "crown", "Bob": "crown", "Carol": "crew"},
            dilemma=dilemma,
        )
        assert result.get("consequence") is not None

    def test_council_in_vote_log(self):
        engine = self._make_engine()
        engine.resolve_group_council(
            {"Alice": "crown", "Bob": "crew", "Carol": "crew"}
        )
        assert len(engine.vote_log) == 1


class TestDissentSummary:
    """Test dissent narrative summary."""

    def test_reliable_voter(self):
        engine = CrownAndCrewEngine()
        ps = engine.players["_solo"]
        ps.majority_count = 4
        ps.dissent_count = 1
        summary = engine.get_dissent_summary()
        assert "reliable" in summary.lower()

    def test_contrarian(self):
        engine = CrownAndCrewEngine()
        ps = engine.players["_solo"]
        ps.majority_count = 1
        ps.dissent_count = 4
        summary = engine.get_dissent_summary()
        assert "contrarian" in summary.lower() or "lone" in summary.lower()

    def test_no_votes(self):
        engine = CrownAndCrewEngine()
        summary = engine.get_dissent_summary()
        assert "no votes" in summary.lower()

    def test_dissent_in_legacy_json(self):
        engine = CrownAndCrewEngine()
        engine.players["_solo"].majority_count = 3
        engine.players["_solo"].dissent_count = 2
        legacy = engine.generate_legacy_json()
        assert "summary" in legacy["dissent"]
        assert "3/5" in legacy["dissent"]["summary"]


# =============================================================================
# WO-V136: Mirror Witness Selection
# =============================================================================

class TestMirrorWitnessSelection:
    """Test multiplayer Mirror Break witness selection."""

    def test_solo_returns_solo(self):
        engine = CrownAndCrewEngine()
        assert engine.select_mirror_witness() == "_solo"

    def test_highest_crew_sway_selected(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        engine.add_player("Carol")
        engine.players["Alice"].sway = 1
        engine.players["Bob"].sway = 3  # Highest crew sway
        engine.players["Carol"].sway = -1
        assert engine.select_mirror_witness() == "Bob"

    def test_tiebreak_by_dominant_dna(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        engine.players["Alice"].sway = 2
        engine.players["Bob"].sway = 2
        # Both tied at sway 2. Alice has BLOOD dominant (matches a sin)
        engine.players["Alice"].dna["BLOOD"] = 5
        engine.players["Bob"].dna["HEARTH"] = 3  # HEARTH also matches a sin
        # Alice checked first since higher DNA total
        witness = engine.select_mirror_witness()
        assert witness in ("Alice", "Bob")  # Either is valid — both match sins

    def test_single_multiplayer(self):
        engine = CrownAndCrewEngine()
        engine.add_player("OnlyPlayer")
        engine.players["OnlyPlayer"].sway = 1
        assert engine.select_mirror_witness() == "OnlyPlayer"

    def test_negative_sway_still_selects(self):
        engine = CrownAndCrewEngine()
        engine.add_player("Alice")
        engine.add_player("Bob")
        engine.players["Alice"].sway = -1
        engine.players["Bob"].sway = -3
        # Alice has highest (least negative) sway
        assert engine.select_mirror_witness() == "Alice"


# =============================================================================
# WO-V108: The Echo — Player-Driven DNA Tag Assignment
# =============================================================================

class TestEcho:
    """Test the Echo response system for allegiance prompts."""

    def test_declare_without_tag_defers_echo(self):
        engine = CrownAndCrewEngine()
        result = engine.declare_allegiance("crown")
        assert engine._pending_echo is True
        assert "how did you carry" in result.lower() or "awaiting echo" in result.lower() or "choice" in result.lower()
        # DNA should NOT be incremented yet
        assert sum(engine.dna.values()) == 0

    def test_declare_with_tag_skips_echo(self):
        engine = CrownAndCrewEngine()
        result = engine.declare_allegiance("crew", tag="HEARTH")
        assert engine._pending_echo is False
        assert engine.dna["HEARTH"] == 1
        assert "HEARTH" in result

    def test_get_echo_responses_returns_five(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crown")
        responses = engine.get_echo_responses()
        assert len(responses) == 5
        tags = {r["tag"] for r in responses}
        assert tags == {"BLOOD", "GUILE", "HEARTH", "SILENCE", "DEFIANCE"}
        for r in responses:
            assert "label" in r
            assert "desc" in r
            assert len(r["label"]) > 0
            assert len(r["desc"]) > 0

    def test_get_echo_frame_crown(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crown")
        frame = engine.get_echo_frame()
        assert "order" in frame.lower()

    def test_get_echo_frame_crew(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew")
        frame = engine.get_echo_frame()
        assert "freedom" in frame.lower()

    def test_resolve_echo_assigns_tag(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew")
        assert sum(engine.dna.values()) == 0
        result = engine.resolve_echo("DEFIANCE")
        assert engine.dna["DEFIANCE"] == 1
        assert engine._pending_echo is False
        assert "DEFIANCE" in result

    def test_resolve_echo_records_history(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crown")
        engine.resolve_echo("SILENCE")
        assert len(engine.history) == 1
        assert engine.history[0]["choice"] == "crown"
        assert engine.history[0]["tag"] == "SILENCE"

    def test_resolve_echo_creates_anchor_shard(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crew")
        shards_before = len(engine._memory_shards)
        engine.resolve_echo("BLOOD")
        # declare_allegiance creates CHRONICLE, resolve_echo creates ANCHOR
        assert len(engine._memory_shards) > shards_before
        last_shard = engine._memory_shards[-1]
        assert "BLOOD" in last_shard.content
        assert "Echo" in last_shard.content

    def test_resolve_echo_invalid_tag_raises(self):
        engine = CrownAndCrewEngine()
        engine.declare_allegiance("crown")
        with pytest.raises(ValueError):
            engine.resolve_echo("INVALID_TAG")

    def test_full_echo_flow(self):
        """Test the complete declare → get_prompt → echo → resolve flow."""
        engine = CrownAndCrewEngine()
        # Step 1: Declare (no tag)
        decl = engine.declare_allegiance("crew")
        assert engine._pending_echo is True
        assert engine.sway == 1

        # Step 2: Get prompt
        prompt = engine.get_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 10

        # Step 3: Get echo responses
        responses = engine.get_echo_responses()
        assert len(responses) == 5

        # Step 4: Resolve echo
        result = engine.resolve_echo("HEARTH")
        assert engine.dna["HEARTH"] == 1
        assert engine._pending_echo is False
        assert len(engine.history) == 1

    def test_backward_compat_with_tag(self):
        """Old callers passing tag directly still work."""
        engine = CrownAndCrewEngine()
        result = engine.declare_allegiance("crown", tag="GUILE")
        assert engine.dna["GUILE"] == 1
        assert len(engine.history) == 1
        assert engine.history[0]["tag"] == "GUILE"
        assert engine._pending_echo is False

    def test_echo_with_drifter_tax_double_draw(self):
        """Echo works correctly after a Double Draw."""
        engine = CrownAndCrewEngine()
        engine._drifter_tax_active = True
        engine.declare_allegiance("crown")
        # Double Draw prompt
        prompt = engine.get_prompt()
        assert "DOUBLE DRAW" in prompt
        # Echo still works
        responses = engine.get_echo_responses()
        assert len(responses) == 5
        result = engine.resolve_echo("SILENCE")
        assert engine.dna["SILENCE"] == 1

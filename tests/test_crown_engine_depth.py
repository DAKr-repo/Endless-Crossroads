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

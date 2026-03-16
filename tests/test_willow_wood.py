"""Tests for WO-V62.0 Track B — Willow Wood Overworld."""
import random
import pytest
from codex.spatial.willow_wood import WillowWoodZone, WoodRoom, WoodEncounter


class TestWillowWoodGeneration:
    def test_generate_creates_rooms(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        assert len(zone.all_rooms()) > 0

    def test_landmark_rooms_present(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        landmarks = zone.landmark_rooms()
        assert len(landmarks) >= 8

    def test_grove_heart_is_start(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        heart = zone.get_room(0)
        assert heart is not None
        assert heart.room_type == "grove_heart"

    def test_gate_rooms_present(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        gates = zone.gate_rooms()
        assert len(gates) >= 3  # descent, ascent, cave
        gate_ids = {g.gate_id for g in gates}
        assert "descent" in gate_ids
        assert "ascent" in gate_ids
        assert "cave" in gate_ids

    def test_gate_has_exit_type(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        gates = zone.gate_rooms()
        for gate in gates:
            assert gate.exit_type in ("descend", "ascend")

    def test_generate_is_idempotent(self):
        """Calling generate() twice should not duplicate rooms."""
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        count_first = len(zone.all_rooms())
        zone.generate()
        count_second = len(zone.all_rooms())
        assert count_first == count_second


class TestProceduralPaths:
    def test_path_rooms_generated(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        descent_path = zone.path_rooms("descent")
        assert 3 <= len(descent_path) <= 5

    def test_deterministic_for_same_seed(self):
        zone1 = WillowWoodZone(session_seed=42)
        zone1.generate()
        zone2 = WillowWoodZone(session_seed=42)
        zone2.generate()
        path1 = [r.name for r in zone1.path_rooms("descent")]
        path2 = [r.name for r in zone2.path_rooms("descent")]
        assert path1 == path2

    def test_different_seeds_produce_valid_paths(self):
        """Paths with different seeds are still valid (length in range)."""
        zone1 = WillowWoodZone(session_seed=42)
        zone1.generate()
        zone2 = WillowWoodZone(session_seed=99)
        zone2.generate()
        path1 = zone1.path_rooms("descent")
        path2 = zone2.path_rooms("descent")
        assert 3 <= len(path1) <= 5
        assert 3 <= len(path2) <= 5

    def test_path_rooms_connected_in_chain(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        path = zone.path_rooms("descent")
        if len(path) > 1:
            for i in range(len(path) - 1):
                a_id = path[i].id
                b_id = path[i + 1].id
                assert b_id in path[i].connections or a_id in path[i + 1].connections

    def test_cave_path_has_more_rooms(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        cave_path = zone.path_rooms("cave")
        assert len(cave_path) >= 4  # path_rooms_min is 4 for cave

    def test_path_rooms_are_not_landmarks(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        for gate_id in ("descent", "ascent", "cave"):
            for room in zone.path_rooms(gate_id):
                assert not room.is_landmark
                assert not room.is_gate

    def test_ascent_path_generated(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        ascent_path = zone.path_rooms("ascent")
        assert 3 <= len(ascent_path) <= 5


class TestGrapesBindings:
    def test_positive_economics_modifies_crossing(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"economics": 0.5})
        zone.generate()
        crossing = zone.get_room(3)
        assert crossing is not None
        assert "caravan" in crossing.description.lower() or "lanterns" in crossing.description.lower()

    def test_negative_economics_modifies_crossing(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"economics": -0.5})
        zone.generate()
        crossing = zone.get_room(3)
        assert crossing is not None
        assert "empty" in crossing.description.lower() or "rotting" in crossing.description.lower()

    def test_neutral_leaves_description_unchanged(self):
        zone_neutral = WillowWoodZone(session_seed=42, grapes_health={"economics": 0.0})
        zone_neutral.generate()
        zone_base = WillowWoodZone(session_seed=42)
        zone_base.generate()
        crossing_neutral = zone_neutral.get_room(3)
        crossing_base = zone_base.get_room(3)
        assert crossing_neutral.description == crossing_base.description

    def test_positive_security_modifies_clearing(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"security": 0.5})
        zone.generate()
        clearing = zone.get_room(5)
        assert "patrol" in clearing.description.lower() or "soldiers" in clearing.description.lower()

    def test_negative_security_modifies_clearing(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"security": -0.5})
        zone.generate()
        clearing = zone.get_room(5)
        assert "squatters" in clearing.description.lower() or "hollow" in clearing.description.lower()

    def test_negative_religion_modifies_shrine(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"religion": -0.5})
        zone.generate()
        shrine = zone.get_room(1)
        assert "defaced" in shrine.description.lower() or "symbols" in shrine.description.lower()

    def test_positive_services_override(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"religion": 0.5})
        zone.generate()
        shrine = zone.get_room(1)
        assert "blessing" in shrine.services

    def test_negative_services_override(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"religion": -0.5})
        zone.generate()
        shrine = zone.get_room(1)
        # Negative services: only ["save"]
        assert "blessing" not in shrine.services
        assert "rest" not in shrine.services

    def test_positive_geography_modifies_thicket(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"geography": 0.5})
        zone.generate()
        thicket = zone.get_room(4)
        assert "green" in thicket.description.lower() or "growth" in thicket.description.lower()

    def test_social_binding_does_not_affect_non_social_room(self):
        zone = WillowWoodZone(session_seed=42, grapes_health={"social": 0.9})
        zone.generate()
        # Social binding is room 2 (hollow). Room 0 should be untouched.
        heart = zone.get_room(0)
        assert "whispers" not in heart.description.lower()
        assert "laughter" not in heart.description.lower()


class TestEncounters:
    def test_encounters_loaded(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        assert len(zone._encounters) >= 5

    def test_encounter_has_four_pillars(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        for enc in zone._encounters.values():
            pillars = set(enc.approaches.keys())
            assert "combat" in pillars
            assert "social" in pillars
            assert "exploration" in pillars
            assert "narrative" in pillars

    def test_encounter_approaches_include_narrative(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        for enc in zone._encounters.values():
            assert "narrative" in enc.approaches

    def test_no_encounter_in_landmark_rooms(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        for room in zone.landmark_rooms():
            assert room.encounter_chance == 0.0

    def test_roll_encounter_returns_none_at_zero_chance(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        heart = zone.get_room(0)
        # 10000 rolls — should always be None
        rng = random.Random(1)
        for _ in range(100):
            result = zone.roll_encounter(0, rng=rng)
            assert result is None

    def test_roll_encounter_can_trigger_in_path_rooms(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        # At least one path room should have a non-zero encounter chance
        has_encounter_capable = any(
            r.encounter_chance > 0 for r in zone.path_rooms("descent")
        )
        assert has_encounter_capable

    def test_roll_encounter_unknown_room_returns_none(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        result = zone.roll_encounter("nonexistent_room_id")
        assert result is None

    def test_will_o_wisp_approach_rewards(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        wisp = zone._encounters.get("will_o_wisp")
        assert wisp is not None
        assert wisp.approaches["social"]["reward"] == "guided_to_secret"
        assert wisp.approaches["narrative"]["dc"] == 0


class TestSecrets:
    def test_secrets_loaded(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        assert len(zone._secrets) >= 5

    def test_check_secrets_in_shrine(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        secrets = zone.check_secrets(1)  # shrine room
        secret_types = [s.secret_type for s in secrets]
        assert "lore_inscription" in secret_types

    def test_echo_memory_requires_sessions(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        # Session 1: echo_memory should NOT be available
        secrets = zone.check_secrets(2, session_number=1)  # hollow room
        secret_types = [s.secret_type for s in secrets]
        assert "echo_memory" not in secret_types

        # Session 3: echo_memory SHOULD be available
        secrets = zone.check_secrets(2, session_number=3)
        secret_types = [s.secret_type for s in secrets]
        assert "echo_memory" in secret_types

    def test_buried_offering_requires_inscription(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        # Without inscription: not available
        secrets_before = zone.check_secrets(1, session_number=1)
        types_before = [s.secret_type for s in secrets_before]
        assert "buried_offering" not in types_before

        # After discovering inscription this session: available
        zone.discover_secret("lore_inscription")
        secrets_after = zone.check_secrets(1, session_number=1)
        types_after = [s.secret_type for s in secrets_after]
        assert "buried_offering" in types_after

    def test_one_per_session_enforcement(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        # Find any room of type ruin/den/overlook that has hidden_cache
        found_room = None
        for room in zone.all_rooms().values():
            if room.room_type in ("ruin", "den", "overlook"):
                secrets = zone.check_secrets(room.id)
                if any(s.secret_type == "hidden_cache" for s in secrets):
                    found_room = room
                    break

        if found_room:
            zone.discover_secret("hidden_cache")
            secrets_after = zone.check_secrets(found_room.id)
            assert not any(s.secret_type == "hidden_cache" for s in secrets_after)
        else:
            # No matching room in generated rooms — just verify the mechanic
            zone.discover_secret("hidden_cache")
            for room in zone.all_rooms().values():
                secrets = zone.check_secrets(room.id)
                assert not any(s.secret_type == "hidden_cache" for s in secrets)

    def test_discovered_secrets_persist_across_zones(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        zone.discover_secret("lore_inscription")
        zone.discover_secret("hidden_cache")
        save_data = zone.to_save_dict()

        zone2 = WillowWoodZone(session_seed=99)
        zone2.generate()
        zone2.load_save_dict(save_data)
        assert "lore_inscription" in zone2.get_discovered_secrets()
        assert "hidden_cache" in zone2.get_discovered_secrets()

    def test_save_dict_keys(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        zone.discover_secret("echo_memory")
        data = zone.to_save_dict()
        assert "discovered_secrets" in data
        assert "echo_memory" in data["discovered_secrets"]

    def test_set_discovered_secrets_roundtrip(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        original = {"lore_inscription", "willow_seed"}
        zone.set_discovered_secrets(original)
        assert zone.get_discovered_secrets() == original

    def test_hidden_path_loaded(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        assert "hidden_path" in zone._secrets

    def test_willow_seed_loaded(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        assert "willow_seed" in zone._secrets
        ws = zone._secrets["willow_seed"]
        assert ws.drop_chance == 0.15


class TestDangerGradient:
    def test_grove_heart_tier_0(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        heart = zone.get_room(0)
        assert heart.tier == 0

    def test_grove_heart_has_no_encounter(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        heart = zone.get_room(0)
        assert heart.encounter_chance == 0.0

    def test_gate_rooms_have_tier_gte_1(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        for gate in zone.gate_rooms():
            assert gate.tier >= 1

    def test_cave_gate_is_tier_2(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        cave_gate = next(g for g in zone.gate_rooms() if g.gate_id == "cave")
        assert cave_gate.tier == 2

    def test_path_room_tiers_do_not_exceed_gate_tier(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        # descent gate tier=1, so no path room should be tier > 1
        descent_gate = next(g for g in zone.gate_rooms() if g.gate_id == "descent")
        for room in zone.path_rooms("descent"):
            assert room.tier <= descent_gate.tier


class TestNavigation:
    def test_grove_heart_connects_to_landmarks(self):
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        heart = zone.get_room(0)
        assert len(heart.connections) >= 2

    def test_can_reach_at_least_one_gate_from_start(self):
        """BFS from grove_heart must find at least one gate."""
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        visited: set = set()
        queue = [0]
        gates_found = []
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            room = zone.get_room(current)
            if room and room.is_gate:
                gates_found.append(room)
            if room:
                for conn in room.connections:
                    if conn not in visited:
                        queue.append(conn)
        assert len(gates_found) >= 1

    def test_all_rooms_reachable_from_start(self):
        """Every generated room must be reachable from room 0 via BFS."""
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        visited: set = set()
        queue = [0]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            room = zone.get_room(current)
            if room:
                for conn in room.connections:
                    if conn not in visited:
                        queue.append(conn)
        all_ids = set(zone.all_rooms().keys())
        unreachable = all_ids - visited
        assert unreachable == set(), f"Unreachable rooms: {unreachable}"

    def test_all_connections_are_valid_room_ids(self):
        """No connection should point to a non-existent room."""
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        all_ids = set(zone.all_rooms().keys())
        for room in zone.all_rooms().values():
            for conn in room.connections:
                assert conn in all_ids, f"Room {room.id} has dangling connection -> {conn}"

    def test_connections_are_bidirectional(self):
        """If A connects to B, B should connect back to A (for path rooms)."""
        zone = WillowWoodZone(session_seed=42)
        zone.generate()
        for room in zone.all_rooms().values():
            if not room.is_landmark:  # path + gate rooms
                for conn_id in room.connections:
                    neighbor = zone.get_room(conn_id)
                    if neighbor:
                        assert room.id in neighbor.connections, (
                            f"Missing back-edge: {conn_id} does not connect to {room.id}"
                        )

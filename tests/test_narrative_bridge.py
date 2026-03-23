"""Tests for codex.core.services.narrative_bridge — Universal Narrative Bridge."""

import pytest


class TestNarrativeBridgeInit:
    """Test NarrativeBridge initialization."""

    def test_init_with_valid_system(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        assert nb.system_id == "burnwillow"
        assert len(nb._seen_enemies) == 0

    def test_init_with_unknown_system(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("nonexistent_system_xyz")
        assert nb.system_id == "nonexistent_system_xyz"
        # Should not crash — graceful empty lookups
        assert nb.describe_enemy("anything") == ""
        assert nb.describe_loot("anything") == ""
        assert nb.describe_hazard("anything") == ""

    def test_init_with_seed(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        assert nb._rng is not None


class TestEnrichRoom:
    """Test room description enrichment."""

    def test_burnwillow_prepends_sensory_lead(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        original = "A stone chamber with a heavy door."
        enriched = nb.enrich_room(original, tier=1)
        # Should be different from original (atmosphere modifier prepends)
        assert enriched != original
        assert "stone chamber" in enriched  # Original text preserved

    def test_burnwillow_tier_2_different_tone(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        desc = "A narrow passage."
        t1 = nb.enrich_room(desc, tier=1)
        nb2 = NarrativeBridge("burnwillow", seed=42)
        t2 = nb2.enrich_room(desc, tier=2)
        # Different tiers should produce different atmosphere
        assert t1 != t2

    def test_non_burnwillow_uses_palette(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("dnd5e", seed=42)
        original = "A dusty library."
        enriched = nb.enrich_room(original, tier=1)
        # Should prepend a sensory sentence
        assert len(enriched) > len(original)
        assert "dusty library" in enriched

    def test_empty_description_handled(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.enrich_room("", tier=1)
        assert result == ""

    def test_unknown_system_returns_original(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("nonexistent_xyz")
        original = "A plain room."
        result = nb.enrich_room(original, tier=1)
        # Should still enrich via palette fallback
        assert "plain room" in result


class TestDescribeEnemy:
    """Test enemy description lookup with first-encounter tracking."""

    def test_known_enemy_returns_description(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_enemy("Rot-Beetle")
        # Should return a non-empty description with dash prefix
        assert len(result) > 0
        assert "\u2014" in result  # em-dash

    def test_unknown_enemy_returns_empty(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_enemy("Completely Made Up Monster")
        assert result == ""

    def test_first_encounter_shows_desc(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        first = nb.describe_enemy("Rot-Beetle")
        assert len(first) > 0

    def test_second_encounter_returns_empty(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        nb.describe_enemy("Rot-Beetle")  # First
        second = nb.describe_enemy("Rot-Beetle")  # Second
        assert second == ""

    def test_reset_seen_allows_redisplay(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        nb.describe_enemy("Rot-Beetle")
        nb.reset_seen()
        again = nb.describe_enemy("Rot-Beetle")
        assert len(again) > 0

    def test_case_insensitive_lookup(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_enemy("rot-beetle")
        assert len(result) > 0

    def test_empty_name_returns_empty(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        assert nb.describe_enemy("") == ""


class TestDescribeLoot:
    """Test loot flavor text lookup."""

    def test_known_loot_returns_flavor(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_loot("Rusted Shortsword")
        assert len(result) > 0
        assert "\u2014" in result

    def test_unknown_loot_returns_empty(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_loot("Nonexistent Item XYZ")
        assert result == ""

    def test_case_insensitive(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_loot("rusted shortsword")
        assert len(result) > 0

    def test_empty_name(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        assert nb.describe_loot("") == ""


class TestDescribeHazard:
    """Test hazard description lookup."""

    def test_known_hazard_returns_description(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_hazard("Rot Pool")
        assert len(result) > 0
        assert "\u2014" in result

    def test_unknown_hazard_returns_empty(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_hazard("Nonexistent Hazard")
        assert result == ""

    def test_case_insensitive(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow")
        result = nb.describe_hazard("rot pool")
        assert len(result) > 0


class TestConfigLoading:
    """Test the config index loader."""

    def test_load_burnwillow_bestiary(self):
        from codex.core.services.narrative_bridge import _load_config_index
        idx = _load_config_index("bestiary", "burnwillow")
        assert len(idx) > 0
        assert "rot-beetle" in idx

    def test_load_burnwillow_hazards(self):
        from codex.core.services.narrative_bridge import _load_config_index
        idx = _load_config_index("hazards", "burnwillow")
        assert len(idx) > 0
        assert "rot pool" in idx

    def test_load_burnwillow_loot(self):
        from codex.core.services.narrative_bridge import _load_config_index
        idx = _load_config_index("loot", "burnwillow")
        assert len(idx) > 0
        assert "rusted shortsword" in idx

    def test_load_missing_config_returns_empty(self):
        from codex.core.services.narrative_bridge import _load_config_index
        idx = _load_config_index("bestiary", "nonexistent_xyz")
        assert idx == {}

    def test_load_dnd5e_bestiary(self):
        from codex.core.services.narrative_bridge import _load_config_index
        idx = _load_config_index("bestiary", "dnd5e")
        # D&D 5e bestiary exists but entries may lack description field
        assert isinstance(idx, dict)

    def test_all_systems_bestiary_loadable(self):
        """Verify bestiary config loads without error for all systems."""
        from codex.core.services.narrative_bridge import _load_config_index
        systems = ["burnwillow", "dnd5e", "bitd", "sav", "bob",
                    "cbrpnk", "candela", "stc", "crown"]
        for sys_id in systems:
            idx = _load_config_index("bestiary", sys_id)
            # May be empty for some systems, but should never crash
            assert isinstance(idx, dict), f"Failed for {sys_id}"


class TestCombatNarration:
    """Test combat narration methods."""

    def test_narrate_hit(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.narrate_hit("Rot-Beetle", 3, "Rusted Shortsword")
        assert len(result) > 0
        assert "Rot-Beetle" in result

    def test_narrate_hit_crit(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.narrate_hit("Rot-Beetle", 6, "Longsword", crit=True)
        assert len(result) > 0

    def test_narrate_miss(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.narrate_miss("Rot-Beetle")
        assert len(result) > 0

    def test_narrate_fumble(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.narrate_miss("Rot-Beetle", fumble=True)
        assert len(result) > 0

    def test_narrate_kill(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.narrate_kill("Rot-Beetle")
        assert len(result) > 0
        assert "Rot-Beetle" in result

    def test_narrate_enemy_hit(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.narrate_enemy_hit("Rot-Beetle", 2)
        assert len(result) > 0

    def test_narrate_enemy_miss(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.narrate_enemy_miss("Rot-Beetle")
        assert len(result) > 0


class TestNPCSpawning:
    """Test procedural NPC spawning."""

    def test_spawn_returns_dict_or_none(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        # Try many rooms — some should spawn, some shouldn't
        results = [nb.spawn_npc_for_room(i, tier=1) for i in range(20)]
        spawned = [r for r in results if r is not None]
        empty = [r for r in results if r is None]
        # ~20% spawn rate means 2-6 out of 20
        assert len(spawned) > 0, "At least some NPCs should spawn"
        assert len(empty) > 0, "Not every room should have an NPC"

    def test_spawned_npc_has_required_fields(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        for i in range(50):
            npc = nb.spawn_npc_for_room(i, tier=1)
            if npc is not None:
                assert "name" in npc
                assert "dialogue" in npc
                break

    def test_spawn_deterministic_with_seed(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb1 = NarrativeBridge("burnwillow", seed=42)
        nb2 = NarrativeBridge("burnwillow", seed=42)
        r1 = [nb1.spawn_npc_for_room(i) for i in range(10)]
        r2 = [nb2.spawn_npc_for_room(i) for i in range(10)]
        # Same seed = same spawn pattern
        for a, b in zip(r1, r2):
            assert (a is None) == (b is None)


class TestQuestGeneration:
    """Test quest hook generation."""

    def test_generate_quest_hook_burnwillow(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        quest = nb.generate_quest_hook(tier=1, npc_name="Elder Kaelen")
        if quest is not None:  # May be None if tables not available
            assert "title" in quest
            assert "description" in quest
            assert "reward" in quest
            assert "Elder Kaelen" in quest["description"]

    def test_generate_quest_unknown_system(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("nonexistent_xyz", seed=42)
        quest = nb.generate_quest_hook(tier=1)
        # Should return None gracefully for systems without tables
        assert quest is None


class TestMimirRoomNarration:
    """Test Mimir-enhanced room narration."""

    def test_mimir_enhancement_with_mock(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)

        def mock_mimir(prompt):
            return "Sap drips from cracked roots above. The air hums with decay."

        result = nb.enrich_room_mimir(
            "A stone chamber.", tier=2,
            enemies=["Rot-Beetle"], doom=12,
            mimir_fn=mock_mimir,
        )
        assert "Sap drips" in result

    def test_mimir_caches_result(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        call_count = []

        def mock_mimir(prompt):
            call_count.append(1)
            return "The darkness presses close against the walls of the passage, thick and suffocating."

        nb.enrich_room_mimir("A dark room.", tier=1, mimir_fn=mock_mimir)
        nb.enrich_room_mimir("A dark room.", tier=1, mimir_fn=mock_mimir)
        assert len(call_count) == 1  # Cached — only called once

    def test_mimir_fallback_on_failure(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)

        def mock_fail(prompt):
            raise TimeoutError("Ollama timeout")

        result = nb.enrich_room_mimir("A stone room.", tier=1, mimir_fn=mock_fail)
        # Should fall back to static enrichment, not crash
        assert "stone room" in result

    def test_mimir_none_fn_uses_static(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("burnwillow", seed=42)
        result = nb.enrich_room_mimir("A passage.", tier=1, mimir_fn=None)
        assert "passage" in result


class TestMultiSystem:
    """Test bridge works across multiple systems."""

    def test_dnd5e_enemy_descriptions(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("dnd5e")
        # Just verify it doesn't crash — actual content depends on config
        result = nb.describe_enemy("Goblin")
        assert isinstance(result, str)

    def test_candela_hazards(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("candela")
        result = nb.describe_hazard("Unknown Hazard")
        assert result == ""  # Graceful empty

    def test_bitd_room_enrichment(self):
        from codex.core.services.narrative_bridge import NarrativeBridge
        nb = NarrativeBridge("bitd", seed=42)
        result = nb.enrich_room("A dark alley.", tier=1)
        assert "dark alley" in result

"""Tests for WO-V62.0 Track D — Universal Session Framing."""
import pytest
from codex.core.session_behaviors import (
    get_session_labels, SESSION_TYPE_LABELS,
    FITDOneShot, generate_one_shot_briefing, FITD_BRIEFING_TEMPLATES,
    CrownSessionConfig,
    should_persist_world, should_advance_civic, get_civic_ticks,
    is_fitd_system, is_spatial_system, get_expedition_budget,
    should_offer_character_export,
    FITD_SYSTEMS, SPATIAL_SYSTEMS, PERSISTS_WORLD,
)


class TestSessionTypeLabels:
    def test_all_systems_have_labels(self):
        for system_id in ("burnwillow", "dnd5e", "stc", "bitd", "sav", "bob", "cbrpnk", "candela", "crown"):
            labels = get_session_labels(system_id)
            assert "one_shot" in labels
            assert "campaign" in labels

    def test_each_label_has_name_and_description(self):
        for system_id, labels in SESSION_TYPE_LABELS.items():
            for stype, (name, desc) in labels.items():
                assert isinstance(name, str) and len(name) > 0, f"{system_id}.{stype} missing name"
                assert isinstance(desc, str) and len(desc) > 0, f"{system_id}.{stype} missing desc"

    def test_unknown_system_gets_defaults(self):
        labels = get_session_labels("totally_unknown")
        assert "one_shot" in labels
        assert "campaign" in labels

    def test_bitd_one_shot_label(self):
        labels = get_session_labels("bitd")
        name, desc = labels["one_shot"]
        assert "Score" in name or "score" in desc.lower()

    def test_crown_freeform_label(self):
        labels = get_session_labels("crown")
        name, desc = labels["freeform"]
        assert "Court" in name or "court" in desc.lower()


class TestFITDOneShot:
    def test_for_bitd(self):
        config = FITDOneShot.for_system("bitd")
        assert config.skip_downtime is True
        assert config.skip_engagement_roll is True
        assert config.start_in_media_res is True
        assert config.score_type == "score"

    def test_for_cbrpnk(self):
        config = FITDOneShot.for_system("cbrpnk")
        assert config.score_type == "run"

    def test_for_bob(self):
        config = FITDOneShot.for_system("bob")
        assert config.score_type == "mission"

    def test_for_candela(self):
        config = FITDOneShot.for_system("candela")
        assert config.score_type == "assignment"

    def test_for_unknown_system(self):
        config = FITDOneShot.for_system("unknown")
        assert config.skip_downtime is True
        assert config.score_type == "score"

    def test_all_fitd_skip_downtime(self):
        for system_id in FITD_SYSTEMS:
            config = FITDOneShot.for_system(system_id)
            assert config.skip_downtime is True


class TestFITDBriefing:
    def test_generates_string(self):
        for system_id in FITD_SYSTEMS:
            briefing = generate_one_shot_briefing(system_id, seed=42)
            assert isinstance(briefing, str)
            assert len(briefing) > 20

    def test_deterministic_for_same_seed(self):
        b1 = generate_one_shot_briefing("bitd", seed=42)
        b2 = generate_one_shot_briefing("bitd", seed=42)
        assert b1 == b2

    def test_different_seeds_can_differ(self):
        b1 = generate_one_shot_briefing("bitd", seed=1)
        b2 = generate_one_shot_briefing("bitd", seed=999)
        # Can't guarantee they differ, but both should be valid
        assert len(b1) > 10
        assert len(b2) > 10

    def test_unknown_system_fallback(self):
        briefing = generate_one_shot_briefing("unknown_system", seed=42)
        assert "mission" in briefing.lower() or "trust" in briefing.lower()


class TestCrownSessionConfig:
    def test_one_shot_default(self):
        config = CrownSessionConfig.for_session_type("one_shot")
        assert config.max_days == 7
        assert config.day_advance_mode == "auto"
        assert config.arc_number == 1

    def test_campaign_multi_arc(self):
        config = CrownSessionConfig.for_session_type(
            "campaign", {"arc_number": 3, "persistent_npcs": {"Vane": 0.8}}
        )
        assert config.max_days == 7
        assert config.arc_number == 3
        assert config.persistent_npcs["Vane"] == 0.8

    def test_freeform_no_day_limit(self):
        config = CrownSessionConfig.for_session_type("freeform")
        assert config.max_days is None
        assert config.day_advance_mode == "manual"

    def test_expedition_extended(self):
        config = CrownSessionConfig.for_session_type("expedition")
        assert config.max_days == 10

    def test_serialization_roundtrip(self):
        config = CrownSessionConfig(
            session_type="campaign",
            max_days=7,
            arc_number=2,
            persistent_npcs={"Vane": 0.5, "Miren": -0.3},
        )
        data = config.to_dict()
        restored = CrownSessionConfig.from_dict(data)
        assert restored.arc_number == 2
        assert restored.persistent_npcs["Vane"] == 0.5
        assert restored.persistent_npcs["Miren"] == -0.3

    def test_campaign_preserves_npcs_between_arcs(self):
        """Simulate multi-arc: config from arc 1 feeds into arc 2."""
        arc1 = CrownSessionConfig.for_session_type("campaign")
        arc1.persistent_npcs["Captain Vane"] = 0.7
        arc1.arc_number = 1
        save = arc1.to_dict()
        save["arc_number"] = 2  # Increment for next arc

        arc2 = CrownSessionConfig.for_session_type("campaign", save)
        assert arc2.arc_number == 2
        assert arc2.persistent_npcs["Captain Vane"] == 0.7


class TestSessionBehaviorQueries:
    def test_one_shot_no_world_persist(self):
        assert not should_persist_world("one_shot")

    def test_campaign_persists_world(self):
        assert should_persist_world("campaign")

    def test_freeform_persists_world(self):
        assert should_persist_world("freeform")

    def test_expedition_persists_world(self):
        assert should_persist_world("expedition")

    def test_one_shot_no_civic(self):
        assert not should_advance_civic("one_shot")

    def test_expedition_civic_ticks(self):
        assert get_civic_ticks("expedition") == 2

    def test_campaign_civic_ticks(self):
        assert get_civic_ticks("campaign") == 1

    def test_one_shot_offers_export(self):
        assert should_offer_character_export("one_shot")

    def test_campaign_no_export(self):
        assert not should_offer_character_export("campaign")

    def test_fitd_system_detection(self):
        assert is_fitd_system("bitd")
        assert is_fitd_system("sav")
        assert is_fitd_system("cbrpnk")
        assert not is_fitd_system("dnd5e")
        assert not is_fitd_system("burnwillow")

    def test_spatial_system_detection(self):
        assert is_spatial_system("dnd5e")
        assert is_spatial_system("burnwillow")
        assert is_spatial_system("stc")
        assert not is_spatial_system("bitd")

    def test_expedition_budgets(self):
        assert get_expedition_budget("burnwillow") == 50
        assert get_expedition_budget("dnd5e") == 60
        assert get_expedition_budget("unknown") == 50  # Default


class TestFITDSystems:
    def test_five_fitd_systems(self):
        assert len(FITD_SYSTEMS) == 5
        assert "bitd" in FITD_SYSTEMS
        assert "sav" in FITD_SYSTEMS
        assert "bob" in FITD_SYSTEMS
        assert "cbrpnk" in FITD_SYSTEMS
        assert "candela" in FITD_SYSTEMS

    def test_three_spatial_systems(self):
        assert len(SPATIAL_SYSTEMS) == 3

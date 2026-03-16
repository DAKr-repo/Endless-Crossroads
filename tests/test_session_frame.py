"""Tests for WO-V62.0 Track A — Session Architecture + Character Export."""
import json
import pytest
from pathlib import Path
from codex.core.session_frame import (
    SessionFrame, SESSION_TYPES, generate_opening_hook, generate_epilogue,
    ExpeditionTimer, get_next_session_number, save_session_counter,
    _generate_session_summary,
)
from codex.core.character_export import (
    export_character, import_character, list_exported_characters,
    save_exported_character, _infer_combat_style, _PORTABLE_CLASS_MAP,
)


class TestSessionFrame:
    def test_create_default(self):
        sf = SessionFrame()
        assert sf.session_type == "campaign"
        assert sf.session_number == 1
        assert sf.turn_count == 0

    def test_create_with_explicit_fields(self):
        sf = SessionFrame(
            session_id="abc",
            session_type="one_shot",
            session_number=5,
            campaign_id="my_campaign",
        )
        assert sf.session_id == "abc"
        assert sf.session_type == "one_shot"
        assert sf.session_number == 5
        assert sf.campaign_id == "my_campaign"

    def test_session_types_constant(self):
        assert "one_shot" in SESSION_TYPES
        assert "expedition" in SESSION_TYPES
        assert "campaign" in SESSION_TYPES
        assert "freeform" in SESSION_TYPES

    def test_started_at_auto_populated(self):
        sf = SessionFrame()
        assert sf.started_at != ""

    def test_ended_at_none_before_close(self):
        sf = SessionFrame()
        assert sf.ended_at is None

    def test_close_sets_ended_at(self):
        sf = SessionFrame(session_type="campaign")
        assert sf.ended_at is None
        sf.close(session_log=[])
        assert sf.ended_at is not None

    def test_close_counts_anchors(self):
        sf = SessionFrame()
        log = [
            {"type": "kill", "name": "goblin"},
            {"type": "near_death", "name": "Kael", "hp": 2, "max_hp": 20},
            {"type": "party_death", "name": "Thorn"},
        ]
        sf.close(session_log=log)
        assert sf.anchor_count == 2  # near_death + party_death

    def test_close_counts_all_anchor_types(self):
        sf = SessionFrame()
        log = [
            {"type": "near_death"},
            {"type": "ally_saved"},
            {"type": "rare_item_used"},
            {"type": "critical_roll"},
            {"type": "companion_fell"},
            {"type": "faction_shift"},
            {"type": "doom_threshold"},
            {"type": "zone_breakthrough"},
            {"type": "party_death"},
        ]
        sf.close(session_log=log)
        assert sf.anchor_count == 9

    def test_close_generates_summary(self):
        sf = SessionFrame()
        log = [
            {"type": "kill"},
            {"type": "kill"},
            {"type": "room_entered"},
        ]
        sf.close(session_log=log)
        assert sf.summary != ""
        assert "2" in sf.summary  # 2 kills

    def test_close_empty_log(self):
        sf = SessionFrame()
        sf.close(session_log=[])
        assert sf.anchor_count == 0
        assert sf.summary == ""

    def test_close_no_log(self):
        sf = SessionFrame()
        sf.close()
        assert sf.ended_at is not None
        assert sf.anchor_count == 0

    def test_serialization_roundtrip(self):
        sf = SessionFrame(
            session_id="test_001",
            session_number=3,
            session_type="freeform",
            campaign_id="test_campaign",
            summary="A dramatic session.",
        )
        data = sf.to_dict()
        restored = SessionFrame.from_dict(data)
        assert restored.session_id == "test_001"
        assert restored.session_number == 3
        assert restored.session_type == "freeform"
        assert restored.campaign_id == "test_campaign"
        assert restored.summary == "A dramatic session."

    def test_to_dict_has_all_keys(self):
        sf = SessionFrame()
        data = sf.to_dict()
        expected_keys = {
            "session_id", "session_number", "session_type", "campaign_id",
            "started_at", "ended_at", "opening_hook", "turn_count",
            "anchor_count", "summary",
        }
        assert expected_keys.issubset(data.keys())

    def test_from_dict_handles_missing_fields(self):
        # Minimal dict — all optional fields should use defaults
        sf = SessionFrame.from_dict({})
        assert sf.session_type == "campaign"
        assert sf.session_number == 1
        assert sf.campaign_id is None

    def test_mimir_summary_called(self):
        calls = []
        def fake_mimir(prompt, ctx):
            calls.append(prompt)
            return "The heroes triumphed over impossible odds."

        sf = SessionFrame()
        log = [{"type": "kill"}, {"type": "room_entered"}]
        sf.close(session_log=log, mimir_fn=fake_mimir)
        assert len(calls) == 1
        assert sf.summary == "The heroes triumphed over impossible odds."

    def test_mimir_short_result_falls_back(self):
        def fake_mimir(prompt, ctx):
            return "ok"  # Too short (len <= 10)

        sf = SessionFrame()
        log = [{"type": "kill"}, {"type": "kill"}]
        sf.close(session_log=log, mimir_fn=fake_mimir)
        # Fallback deterministic summary still produced
        assert "2" in sf.summary


class TestGenerateSessionSummary:
    def test_empty_log(self):
        result = _generate_session_summary([])
        assert "uneventful" in result.lower()

    def test_kills_in_summary(self):
        log = [{"type": "kill"}] * 5
        result = _generate_session_summary(log)
        assert "5" in result

    def test_deaths_in_summary(self):
        log = [{"type": "party_death", "name": "Kael"}]
        result = _generate_session_summary(log)
        assert "Kael" in result

    def test_rooms_in_summary(self):
        log = [{"type": "room_entered"}] * 3
        result = _generate_session_summary(log)
        assert "3" in result

    def test_multiple_deaths_listed(self):
        log = [
            {"type": "party_death", "name": "Kael"},
            {"type": "party_death", "name": "Thorn"},
        ]
        result = _generate_session_summary(log)
        assert "Kael" in result
        assert "Thorn" in result

    def test_no_events_gives_uneventful(self):
        # Only non-kill/room events
        log = [{"type": "save_game"}]
        result = _generate_session_summary(log)
        assert "uneventful" in result.lower()

    def test_mimir_timeout_falls_back(self):
        import time
        def slow_mimir(prompt, ctx):
            time.sleep(15)  # Will exceed 10s timeout
            return "Never returned"

        log = [{"type": "kill"}]
        # Should not raise — should return fallback within test timeout
        result = _generate_session_summary(log, mimir_fn=slow_mimir)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mimir_exception_falls_back(self):
        def broken_mimir(prompt, ctx):
            raise RuntimeError("Mimir offline")

        log = [{"type": "kill"}, {"type": "kill"}]
        result = _generate_session_summary(log, mimir_fn=broken_mimir)
        assert "2" in result


class TestOpeningHook:
    def test_returns_string(self):
        hook = generate_opening_hook(session_type="one_shot")
        assert isinstance(hook, str)
        assert len(hook) > 10

    def test_campaign_hook(self):
        hook = generate_opening_hook(session_type="campaign")
        assert isinstance(hook, str)

    def test_freeform_hook(self):
        hook = generate_opening_hook(session_type="freeform")
        assert isinstance(hook, str)

    def test_expedition_hook(self):
        hook = generate_opening_hook(session_type="expedition")
        assert isinstance(hook, str)

    def test_unknown_type_falls_back_to_campaign(self):
        hook = generate_opening_hook(session_type="mystery_type")
        assert isinstance(hook, str)

    def test_momentum_based_hook(self):
        class MockLedger:
            def get_dominant_trend(self, location):
                return ("security", 8.0)

        hook = generate_opening_hook(
            session_type="campaign",
            momentum_ledger=MockLedger(),
            location="docks",
        )
        assert isinstance(hook, str)
        assert len(hook) > 10

    def test_momentum_below_threshold_uses_pool(self):
        class MockLedger:
            def get_dominant_trend(self, location):
                return ("security", 5.0)  # Below 7.0 threshold

        hook = generate_opening_hook(
            session_type="one_shot",
            momentum_ledger=MockLedger(),
        )
        assert isinstance(hook, str)

    def test_momentum_exception_falls_back(self):
        class BrokenLedger:
            def get_dominant_trend(self, location):
                raise RuntimeError("ledger broken")

        hook = generate_opening_hook(
            session_type="campaign",
            momentum_ledger=BrokenLedger(),
        )
        assert isinstance(hook, str)

    def test_mimir_prior_session_context(self):
        calls = []
        def fake_mimir(prompt, ctx):
            calls.append(prompt)
            return "The dungeon awaits, darker than before."

        prior = [
            {"session_number": 1, "summary": "The party slew 5 goblins."},
        ]
        hook = generate_opening_hook(
            session_type="campaign",
            prior_sessions=prior,
            mimir_fn=fake_mimir,
        )
        assert hook == "The dungeon awaits, darker than before."
        assert len(calls) == 1

    def test_mimir_no_prior_sessions_skips_mimir(self):
        calls = []
        def fake_mimir(prompt, ctx):
            calls.append(prompt)
            return "Some hook"

        # prior_sessions empty list — no summaries → skip mimir
        hook = generate_opening_hook(
            session_type="campaign",
            prior_sessions=[],
            mimir_fn=fake_mimir,
        )
        assert isinstance(hook, str)
        assert len(calls) == 0


class TestEpilogue:
    def test_one_shot_returns_none(self):
        result = generate_epilogue([], session_type="one_shot")
        assert result is None

    def test_campaign_with_party_death(self):
        log = [{"type": "party_death", "name": "Kael"}]
        result = generate_epilogue(log, session_type="campaign")
        assert result is not None
        assert "candle" in result.lower() or "fallen" in result.lower()

    def test_doom_threshold_epilogue(self):
        log = [{"type": "doom_threshold", "doom_value": 15, "event_text": "Quake"}]
        result = generate_epilogue(log, session_type="campaign")
        assert result is not None
        assert "trembles" in result.lower() or "stirs" in result.lower()

    def test_companion_fell_epilogue(self):
        log = [{"type": "companion_fell", "name": "Rex"}]
        result = generate_epilogue(log, session_type="campaign")
        assert result is not None
        assert "bedroll" in result.lower() or "fire" in result.lower()

    def test_zone_breakthrough_epilogue(self):
        log = [{"type": "zone_breakthrough", "tier": 2}]
        result = generate_epilogue(log, session_type="campaign")
        assert result is not None
        assert "threshold" in result.lower() or "ancient" in result.lower()

    def test_no_anchors_returns_none(self):
        log = [{"type": "room_entered"}, {"type": "kill"}]
        result = generate_epilogue(log, session_type="campaign")
        assert result is None

    def test_freeform_with_anchors(self):
        log = [{"type": "party_death", "name": "Hero"}]
        result = generate_epilogue(log, session_type="freeform")
        assert result is not None

    def test_expedition_with_anchors(self):
        log = [{"type": "doom_threshold"}]
        result = generate_epilogue(log, session_type="expedition")
        assert result is not None

    def test_mimir_epilogue_called(self):
        calls = []
        def fake_mimir(prompt, ctx):
            calls.append(prompt)
            return "The innkeeper bolts the door and whispers a prayer."

        log = [{"type": "party_death", "name": "Kael"}]
        result = generate_epilogue(log, session_type="campaign", mimir_fn=fake_mimir)
        assert len(calls) == 1
        assert result == "The innkeeper bolts the door and whispers a prayer."

    def test_mimir_short_result_falls_back(self):
        def fake_mimir(prompt, ctx):
            return "nope"  # len <= 20

        log = [{"type": "party_death", "name": "Kael"}]
        result = generate_epilogue(log, session_type="campaign", mimir_fn=fake_mimir)
        assert result is not None
        assert "candle" in result.lower() or "fallen" in result.lower()

    def test_momentum_context_included(self):
        calls = []
        def fake_mimir(prompt, ctx):
            calls.append(prompt)
            return "The city holds its breath."

        class MockLedger:
            def get_dominant_trend(self, location):
                return ("security", 9.5)

        log = [{"type": "doom_threshold"}]
        result = generate_epilogue(
            log, session_type="campaign",
            momentum_ledger=MockLedger(),
            mimir_fn=fake_mimir,
        )
        assert "Dominant trend" in calls[0]


class TestExpeditionTimer:
    def test_initial_state(self):
        t = ExpeditionTimer(turn_budget=50)
        assert t.elapsed == 0
        assert not t.exhausted
        assert t.ratio == 0.0

    def test_tick_advances_elapsed(self):
        t = ExpeditionTimer(turn_budget=10)
        t.tick()
        assert t.elapsed == 1

    def test_tick_no_message_early(self):
        t = ExpeditionTimer(turn_budget=100)
        msg = t.tick()  # 1/100 = 1%
        assert msg is None

    def test_tick_message_at_50_percent(self):
        t = ExpeditionTimer(turn_budget=10)
        for _ in range(4):
            t.tick()
        msg = t.tick()  # 5/10 = 50%
        assert msg is not None
        assert "lighter" in msg.lower()

    def test_tick_message_at_70_percent(self):
        t = ExpeditionTimer(turn_budget=10)
        for _ in range(6):
            t.tick()
        msg = t.tick()  # 7/10 = 70%
        assert msg is not None
        assert "water" in msg.lower() or "jerky" in msg.lower()

    def test_tick_message_at_80_percent(self):
        t = ExpeditionTimer(turn_budget=10)
        for _ in range(7):
            t.tick()
        msg = t.tick()  # 8/10 = 80%
        assert msg is not None
        assert "returning" in msg.lower() or "supplies" in msg.lower()

    def test_tick_message_at_90_percent(self):
        t = ExpeditionTimer(turn_budget=10)
        for _ in range(8):
            t.tick()
        msg = t.tick()  # 9/10 = 90%
        assert msg is not None
        assert "torch" in msg.lower() or "cramps" in msg.lower()

    def test_tick_message_at_100_percent(self):
        t = ExpeditionTimer(turn_budget=10)
        for _ in range(9):
            t.tick()
        msg = t.tick()  # 10/10 = 100%
        assert msg is not None
        assert "rations" in msg.lower() or "exhausted" in msg.lower()

    def test_no_duplicate_stage_messages(self):
        t = ExpeditionTimer(turn_budget=10)
        messages = []
        for _ in range(10):
            m = t.tick()
            if m is not None:
                messages.append(m)
        # Each stage message fires exactly once
        assert len(messages) == len(set(messages))

    def test_exhausted_at_100_percent(self):
        t = ExpeditionTimer(turn_budget=5)
        for _ in range(5):
            t.tick()
        assert t.exhausted

    def test_not_exhausted_before_budget(self):
        t = ExpeditionTimer(turn_budget=5)
        for _ in range(4):
            t.tick()
        assert not t.exhausted

    def test_ratio_calculation(self):
        t = ExpeditionTimer(turn_budget=10)
        for _ in range(5):
            t.tick()
        assert t.ratio == pytest.approx(0.5)

    def test_zero_budget_disables_timer(self):
        t = ExpeditionTimer(turn_budget=0)
        msg = t.tick()
        assert msg is None
        assert not t.exhausted
        assert t.ratio == 0.0

    def test_serialization(self):
        t = ExpeditionTimer(turn_budget=50)
        for _ in range(25):
            t.tick()
        data = t.to_dict()
        t2 = ExpeditionTimer.from_dict(data)
        assert t2.elapsed == 25
        assert t2.budget == 50

    def test_serialization_preserves_last_stage(self):
        t = ExpeditionTimer(turn_budget=10)
        for _ in range(5):
            t.tick()  # Crosses 50% stage
        data = t.to_dict()
        t2 = ExpeditionTimer.from_dict(data)
        # Restored timer should not re-fire the 50% message
        assert t2._last_stage >= 0.5


class TestSessionCounter:
    def test_next_session_number_new(self, tmp_path):
        num = get_next_session_number("new_campaign", saves_dir=tmp_path)
        assert num == 1

    def test_save_and_get(self, tmp_path):
        save_session_counter("test_camp", 3, saves_dir=tmp_path)
        num = get_next_session_number("test_camp", saves_dir=tmp_path)
        assert num == 4

    def test_empty_campaign_id(self, tmp_path):
        num = get_next_session_number("", saves_dir=tmp_path)
        assert num == 1

    def test_save_empty_campaign_id_is_noop(self, tmp_path):
        save_session_counter("", 5, saves_dir=tmp_path)
        # No file should be written for empty campaign_id
        counter_file = tmp_path / "session_counters.json"
        assert not counter_file.exists()

    def test_multiple_campaigns_independent(self, tmp_path):
        save_session_counter("campaign_a", 2, saves_dir=tmp_path)
        save_session_counter("campaign_b", 7, saves_dir=tmp_path)
        assert get_next_session_number("campaign_a", saves_dir=tmp_path) == 3
        assert get_next_session_number("campaign_b", saves_dir=tmp_path) == 8

    def test_overwrites_existing_counter(self, tmp_path):
        save_session_counter("camp", 1, saves_dir=tmp_path)
        save_session_counter("camp", 5, saves_dir=tmp_path)
        assert get_next_session_number("camp", saves_dir=tmp_path) == 6

    def test_corrupted_file_returns_1(self, tmp_path):
        counter_file = tmp_path / "session_counters.json"
        counter_file.write_text("NOT VALID JSON {{{")
        num = get_next_session_number("any_campaign", saves_dir=tmp_path)
        assert num == 1

    def test_saves_dir_created_if_missing(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        save_session_counter("camp", 1, saves_dir=nested)
        assert (nested / "session_counters.json").exists()


class TestCharacterExport:
    def test_export_basic(self):
        char = {"name": "Kael", "level": 3, "max_hp": 30, "current_hp": 25}
        result = export_character(char, "burnwillow")
        assert result["_export_meta"]["system_id"] == "burnwillow"
        assert result["_export_meta"]["level"] == 3
        assert result["_portable_stats"]["hp_ratio"] == pytest.approx(0.83, abs=0.01)
        assert result["_portable_stats"]["name"] == "Kael"

    def test_export_preserves_original_fields(self):
        char = {"name": "Kael", "level": 3, "max_hp": 30, "current_hp": 25,
                "gold": 150, "skills": ["acrobatics"]}
        result = export_character(char, "burnwillow")
        assert result["gold"] == 150
        assert result["skills"] == ["acrobatics"]

    def test_export_infers_combat_style(self):
        char = {"name": "Test", "class": "Fighter", "level": 1, "max_hp": 10}
        result = export_character(char, "dnd5e")
        assert result["_portable_stats"]["combat_style"] == "melee"

    def test_export_with_campaign_id(self):
        char = {"name": "X", "level": 1, "max_hp": 10}
        result = export_character(char, "burnwillow", campaign_id="my_run")
        assert result["_export_meta"]["source_campaign"] == "my_run"

    def test_export_gear_extracted(self):
        char = {
            "name": "Kael", "level": 1, "max_hp": 10,
            "gear": [{"name": "Sword"}, {"name": "Shield"}, "Potion"],
        }
        result = export_character(char, "burnwillow")
        items = result["_portable_stats"]["notable_items"]
        assert "Sword" in items
        assert "Shield" in items
        assert "Potion" in items

    def test_export_inventory_fallback(self):
        char = {"name": "Kael", "level": 1, "max_hp": 10,
                "inventory": ["Torch", "Rope"]}
        result = export_character(char, "burnwillow")
        assert "Torch" in result["_portable_stats"]["notable_items"]
        assert "Rope" in result["_portable_stats"]["notable_items"]

    def test_export_gear_capped_at_five(self):
        char = {"name": "Kael", "level": 1, "max_hp": 10,
                "gear": [f"Item{i}" for i in range(10)]}
        result = export_character(char, "burnwillow")
        assert len(result["_portable_stats"]["notable_items"]) == 5

    def test_export_hp_ratio_full_health(self):
        char = {"name": "X", "level": 1, "max_hp": 20, "current_hp": 20}
        result = export_character(char, "burnwillow")
        assert result["_portable_stats"]["hp_ratio"] == 1.0

    def test_export_hp_ratio_zero_max_safe(self):
        # max_hp=0 should not divide by zero
        char = {"name": "X", "level": 1, "max_hp": 0}
        result = export_character(char, "burnwillow")
        assert isinstance(result["_portable_stats"]["hp_ratio"], float)

    def test_import_same_system(self):
        char = {"name": "Kael", "level": 3, "max_hp": 30,
                "_export_meta": {"system_id": "burnwillow"},
                "_portable_stats": {"name": "Kael", "level": 3}}
        result = import_character(char, "burnwillow")
        assert result is not None
        assert result["name"] == "Kael"
        assert "_export_meta" not in result
        assert "_portable_stats" not in result

    def test_import_same_system_preserves_all_fields(self):
        char = {"name": "Kael", "level": 3, "max_hp": 30, "gold": 500,
                "_export_meta": {"system_id": "burnwillow"},
                "_portable_stats": {}}
        result = import_character(char, "burnwillow")
        assert result["gold"] == 500

    def test_import_cross_system(self):
        char = {
            "name": "Kael",
            "_export_meta": {"system_id": "burnwillow"},
            "_portable_stats": {
                "name": "Kael", "level": 3, "hp_ratio": 0.85,
                "combat_style": "melee", "notable_items": ["Sword"],
            },
        }
        result = import_character(char, "dnd5e")
        assert result is not None
        assert result["name"] == "Kael"
        assert result["class"] == "Fighter"
        assert result["_cross_system"] is True

    def test_import_cross_system_all_styles(self):
        styles = {
            "melee": "Warrior",
            "ranged": "Ranger",
            "magic": "Arcanist",
            "support": "Healer",
        }
        for style, expected_class in styles.items():
            char = {
                "_export_meta": {"system_id": "dnd5e"},
                "_portable_stats": {"name": "X", "combat_style": style},
            }
            result = import_character(char, "burnwillow")
            assert result["class"] == expected_class, f"Failed for style: {style}"

    def test_import_unknown_system_returns_none(self):
        char = {
            "_export_meta": {"system_id": "burnwillow"},
            "_portable_stats": {"name": "X", "combat_style": "melee"},
        }
        result = import_character(char, "totally_unknown_system")
        assert result is None

    def test_import_missing_portable_stats_returns_none(self):
        char = {
            "_export_meta": {"system_id": "burnwillow"},
            # No _portable_stats
        }
        result = import_character(char, "dnd5e")
        assert result is None

    def test_import_preserves_level(self):
        char = {
            "_export_meta": {"system_id": "bitd"},
            "_portable_stats": {"name": "Z", "level": 7, "combat_style": "magic"},
        }
        result = import_character(char, "stc")
        assert result["level"] == 7

    def test_import_cross_system_imported_from_tag(self):
        char = {
            "_export_meta": {"system_id": "sav"},
            "_portable_stats": {"name": "Ash", "combat_style": "support"},
        }
        result = import_character(char, "bob")
        assert result["_imported_from"] == "sav"

    def test_save_and_list(self, tmp_path, monkeypatch):
        import codex.core.character_export as ce
        monkeypatch.setattr(ce, "_CHARACTERS_DIR", tmp_path / "characters")

        char = export_character(
            {"name": "Test Hero", "level": 2, "max_hp": 20, "current_hp": 20},
            "burnwillow",
        )
        path = save_exported_character(char)
        assert path.exists()

        chars = list_exported_characters()
        assert len(chars) == 1
        assert chars[0]["name"] == "Test Hero"

    def test_list_filtered_by_system(self, tmp_path, monkeypatch):
        import codex.core.character_export as ce
        monkeypatch.setattr(ce, "_CHARACTERS_DIR", tmp_path / "characters")

        c1 = export_character({"name": "A", "level": 1, "max_hp": 10}, "burnwillow")
        c2 = export_character({"name": "B", "level": 1, "max_hp": 10}, "dnd5e")
        save_exported_character(c1)
        save_exported_character(c2)

        bw_chars = list_exported_characters(system_id="burnwillow")
        assert len(bw_chars) == 1
        assert bw_chars[0]["name"] == "A"

    def test_list_empty_dir_returns_empty(self, tmp_path, monkeypatch):
        import codex.core.character_export as ce
        monkeypatch.setattr(ce, "_CHARACTERS_DIR", tmp_path / "nonexistent")
        assert list_exported_characters() == []

    def test_save_creates_directory(self, tmp_path, monkeypatch):
        import codex.core.character_export as ce
        target = tmp_path / "new_chars"
        monkeypatch.setattr(ce, "_CHARACTERS_DIR", target)
        char = export_character({"name": "X", "level": 1, "max_hp": 5}, "stc")
        save_exported_character(char)
        assert target.exists()

    def test_save_filename_format(self, tmp_path, monkeypatch):
        import codex.core.character_export as ce
        monkeypatch.setattr(ce, "_CHARACTERS_DIR", tmp_path / "characters")
        char = export_character({"name": "Dark Knight", "level": 1, "max_hp": 10}, "dnd5e")
        path = save_exported_character(char)
        assert path.name == "dark_knight_dnd5e.json"

    def test_list_skips_corrupt_files(self, tmp_path, monkeypatch):
        import codex.core.character_export as ce
        chars_dir = tmp_path / "characters"
        chars_dir.mkdir()
        monkeypatch.setattr(ce, "_CHARACTERS_DIR", chars_dir)
        (chars_dir / "bad.json").write_text("NOT JSON {{")
        chars = list_exported_characters()
        assert chars == []


class TestInferCombatStyle:
    def test_fighter_is_melee(self):
        assert _infer_combat_style({"class": "Fighter"}) == "melee"

    def test_cutter_is_melee(self):
        assert _infer_combat_style({"playbook": "Cutter"}) == "melee"

    def test_wizard_is_magic(self):
        assert _infer_combat_style({"class": "Wizard"}) == "magic"

    def test_whisper_is_magic(self):
        assert _infer_combat_style({"playbook": "Whisper"}) == "magic"

    def test_cleric_is_support(self):
        assert _infer_combat_style({"class": "Cleric"}) == "support"

    def test_leech_is_support(self):
        assert _infer_combat_style({"playbook": "Leech"}) == "support"

    def test_ranger_is_ranged(self):
        assert _infer_combat_style({"class": "Ranger"}) == "ranged"

    def test_lurk_is_ranged(self):
        assert _infer_combat_style({"playbook": "Lurk"}) == "ranged"

    def test_playbook_takes_precedence_over_class(self):
        # playbook should win over class
        assert _infer_combat_style({"playbook": "Whisper", "class": "Fighter"}) == "magic"

    def test_stats_fallback_str_dominant(self):
        assert _infer_combat_style({"stats": {"str": 18, "dex": 10, "int": 8, "wis": 8}}) == "melee"

    def test_stats_fallback_int_dominant(self):
        assert _infer_combat_style({"stats": {"str": 8, "dex": 10, "int": 18, "wis": 10}}) == "magic"

    def test_stats_fallback_dex_dominant(self):
        assert _infer_combat_style({"stats": {"str": 8, "dex": 18, "int": 10, "wis": 10}}) == "ranged"

    def test_default_melee(self):
        assert _infer_combat_style({}) == "melee"

    def test_case_insensitive(self):
        assert _infer_combat_style({"class": "FIGHTER"}) == "melee"
        assert _infer_combat_style({"class": "wizard"}) == "magic"

    def test_stc_windrunner_is_magic(self):
        assert _infer_combat_style({"class": "Windrunner"}) == "magic"

    def test_stc_edgedancer_is_support(self):
        assert _infer_combat_style({"class": "Edgedancer"}) == "support"


class TestPortableClassMap:
    def test_all_systems_have_four_styles(self):
        for system_id, mapping in _PORTABLE_CLASS_MAP.items():
            assert "melee" in mapping, f"{system_id} missing melee"
            assert "ranged" in mapping, f"{system_id} missing ranged"
            assert "magic" in mapping, f"{system_id} missing magic"
            assert "support" in mapping, f"{system_id} missing support"

    def test_nine_systems_covered(self):
        assert len(_PORTABLE_CLASS_MAP) == 9

    def test_expected_systems_present(self):
        expected = {"burnwillow", "dnd5e", "stc", "bitd", "sav", "bob", "cbrpnk", "candela", "crown"}
        assert set(_PORTABLE_CLASS_MAP.keys()) == expected

    def test_all_values_are_non_empty_strings(self):
        for system_id, mapping in _PORTABLE_CLASS_MAP.items():
            for style, cls in mapping.items():
                assert isinstance(cls, str) and len(cls) > 0, \
                    f"{system_id}.{style} has empty class name"

    def test_dnd5e_melee_is_fighter(self):
        assert _PORTABLE_CLASS_MAP["dnd5e"]["melee"] == "Fighter"

    def test_bitd_magic_is_whisper(self):
        assert _PORTABLE_CLASS_MAP["bitd"]["magic"] == "Whisper"

    def test_stc_support_is_truthwatcher(self):
        assert _PORTABLE_CLASS_MAP["stc"]["support"] == "Truthwatcher"

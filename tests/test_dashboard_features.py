"""Tests for DM Dashboard new features: rules reference, quest tracker, enemy viewer."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock


# ── Quest Tracker Tests ───────────────────────────────────────────────


class TestQuestTracker:
    def test_add_quest(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        result = qt.add("Find the lost artifact")
        assert "Quest added" in result
        assert len(qt.quests) == 1
        quest = list(qt.quests.values())[0]
        assert quest.title == "Find the lost artifact"
        assert quest.status == "active"

    def test_complete_quest(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        qt.add("Kill the dragon")
        qid = list(qt.quests.keys())[0]
        result = qt.complete(qid)
        assert "completed" in result
        assert qt.quests[qid].status == "completed"

    def test_abandon_quest(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        qt.add("Escort the merchant")
        qid = list(qt.quests.keys())[0]
        result = qt.abandon(qid)
        assert "abandoned" in result

    def test_remove_quest(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        qt.add("Deliver the letter")
        qid = list(qt.quests.keys())[0]
        result = qt.remove(qid)
        assert "removed" in result
        assert len(qt.quests) == 0

    def test_list_quests(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        qt.add("Quest A")
        qt.add("Quest B")
        result = qt.list_quests()
        assert "Quest A" in result
        assert "Quest B" in result

    def test_list_by_status(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        qt.add("Active quest")
        qt.add("Done quest")
        qid = list(qt.quests.keys())[1]
        qt.complete(qid)
        active = qt.list_quests(status="active")
        assert "Active quest" in active
        assert "Done quest" not in active

    def test_active_summary(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        qt.add("Quest 1")
        qt.add("Quest 2")
        summary = qt.active_summary()
        assert "Quest 1" in summary
        assert "Quest 2" in summary

    def test_empty_summary(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        assert qt.active_summary() == "No active quests."

    def test_to_dict_from_dict(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        qt.add("Persistent quest", notes="Important!", source="Bazso")
        data = qt.to_dict()
        qt2 = QuestTracker.from_dict(data)
        assert len(qt2.quests) == 1
        quest = list(qt2.quests.values())[0]
        assert quest.title == "Persistent quest"
        assert quest.notes == "Important!"
        assert quest.source == "Bazso"

    def test_not_found(self):
        from codex.core.mechanics.quest import QuestTracker
        qt = QuestTracker()
        assert "not found" in qt.complete("nonexistent")
        assert "not found" in qt.remove("nonexistent")


# ── Rules Reference Tests ─────────────────────────────────────────────


class TestRulesReference:
    def test_universal_rules_file_exists(self):
        rules_path = Path(__file__).resolve().parent.parent / "config" / "rules" / "universal.json"
        assert rules_path.exists()
        data = json.loads(rules_path.read_text())
        assert "dc_table" in data
        assert "conditions" in data
        assert "action_economy" in data

    def test_fitd_rules_file_exists(self):
        rules_path = Path(__file__).resolve().parent.parent / "config" / "rules" / "fitd.json"
        assert rules_path.exists()
        data = json.loads(rules_path.read_text())
        assert "position_effect" in data
        assert "action_roll" in data
        assert "stress_and_trauma" in data

    def test_dashboard_loads_rules(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "BITD")
        assert dashboard._rules_data
        # Should have both universal and FITD rules merged
        assert "dc_table" in dashboard._rules_data
        assert "position_effect" in dashboard._rules_data

    def test_rules_lookup_dc(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        result = dashboard._format_rules_lookup("dc")
        assert "15" in result
        assert "Moderate" in result

    def test_rules_lookup_conditions(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        result = dashboard._format_rules_lookup("conditions")
        assert "Stunned" in result
        assert "Poisoned" in result

    def test_rules_lookup_empty_lists_topics(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        result = dashboard._format_rules_lookup("")
        assert "topics" in result.lower() or "Topics" in result

    def test_rules_lookup_not_found(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        result = dashboard._format_rules_lookup("xyznotreal")
        assert "No rules found" in result


# ── Enemy Stat Viewer Tests ───────────────────────────────────────────


class TestEnemyStatViewer:
    def test_format_enemy_stat_line(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "BURNWILLOW")
        enemy = {
            "name": "Spore Crawler", "hp": 12, "max_hp": 20,
            "defense": 14, "damage": "2d6", "special": "Toxic Spores",
            "alive": True,
        }
        line = dashboard._format_enemy_stat_line(enemy)
        assert "Spore Crawler" in line
        assert "HP:12/20" in line
        assert "DEF:14" in line
        assert "Toxic Spores" in line

    def test_format_dead_enemy(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "BURNWILLOW")
        enemy = {"name": "Goblin", "hp": 0, "max_hp": 8, "defense": 10,
                 "damage": "1d6", "alive": False}
        line = dashboard._format_enemy_stat_line(enemy)
        assert "[DEAD]" in line

    def test_get_room_enemies_empty(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "BURNWILLOW")
        mock_engine = MagicMock()
        mock_engine.populated_rooms = {}
        result = dashboard._get_room_enemies(mock_engine, "room_0")
        assert result == []

    def test_get_room_enemies_with_data(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "BURNWILLOW")
        mock_engine = MagicMock()
        pop = MagicMock()
        pop.content = {"enemies": [{"name": "Wolf", "hp": 10}]}
        mock_engine.populated_rooms = {"room_0": pop}
        result = dashboard._get_room_enemies(mock_engine, "room_0")
        assert len(result) == 1
        assert result[0]["name"] == "Wolf"


# ── Dashboard dispatch_command Integration ────────────────────────────


class TestDashboardDispatch:
    def test_dispatch_rules(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        result = dashboard.dispatch_command("rules dc")
        assert "15" in result

    def test_dispatch_quest_add(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        result = dashboard.dispatch_command("quest add Find the holy grail")
        assert "Quest added" in result
        assert len(dashboard.quests.quests) == 1

    def test_dispatch_quest_list(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        dashboard.dispatch_command("quest add First quest")
        dashboard.dispatch_command("quest add Second quest")
        result = dashboard.dispatch_command("quest list")
        assert "First quest" in result
        assert "Second quest" in result

    def test_dispatch_quest_complete(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "DND5E")
        dashboard.dispatch_command("quest add Slay the beast")
        qid = list(dashboard.quests.quests.keys())[0]
        result = dashboard.dispatch_command(f"quest complete {qid}")
        assert "completed" in result

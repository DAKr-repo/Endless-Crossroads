"""Tests for codex.bots.dashboard_embed — bot dashboard text formatter."""

import pytest
from unittest.mock import MagicMock
from codex.bots.dashboard_embed import format_dashboard_text, _format_resource_bar


class TestResourceBar:
    def test_full_bar(self):
        result = _format_resource_bar("HP", 20, 20)
        assert "###############" in result
        assert "20/20" in result

    def test_half_bar(self):
        result = _format_resource_bar("HP", 10, 20)
        assert "10/20" in result

    def test_zero_max(self):
        result = _format_resource_bar("Sway", 3, 0)
        assert "Sway: 3" in result


class TestFormatDashboard:
    def _make_vitals(self, **kwargs):
        from codex.core.dm_dashboard import VitalsSchema
        defaults = {
            "system_name": "Burnwillow",
            "system_tag": "BURNWILLOW",
            "primary_resource": "HP",
            "primary_current": 15,
            "primary_max": 20,
            "party": [
                {"name": "Aldo", "hp": 15, "max_hp": 20, "alive": True},
                {"name": "Bren", "hp": 0, "max_hp": 12, "alive": False},
            ],
        }
        defaults.update(kwargs)
        return VitalsSchema(**defaults)

    def test_basic_format(self):
        vitals = self._make_vitals()
        text = format_dashboard_text(vitals)
        assert "Burnwillow" in text
        assert "Aldo" in text
        assert "Bren" in text
        assert "HP" in text

    def test_with_dashboard(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        vitals = self._make_vitals()
        dashboard = DMDashboard(Console(), "BURNWILLOW")
        dashboard.quests.add("Find the artifact")
        text = format_dashboard_text(vitals, dashboard)
        assert "Find the artifact" in text

    def test_bitd_system(self):
        vitals = self._make_vitals(
            system_name="Blades in the Dark",
            system_tag="BITD",
            primary_resource="Stress",
            primary_current=3, primary_max=9,
            secondary_resource="Heat", secondary_current=2, secondary_max=6,
            extra={"crew_name": "The Crows", "wanted_level": 1, "rep": 4, "coin": 6},
            party=[{"name": "Aldo", "hp": 3, "max_hp": 9, "playbook": "Cutter",
                    "stress": 3, "alive": True}],
        )
        text = format_dashboard_text(vitals)
        assert "Blades in the Dark" in text
        assert "The Crows" in text
        assert "Cutter" in text

    def test_under_4000_chars(self):
        vitals = self._make_vitals()
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        dashboard = DMDashboard(Console(), "BURNWILLOW")
        for i in range(20):
            dashboard.quests.add(f"Quest {i}")
            dashboard._notes.append(f"Note {i}")
        text = format_dashboard_text(vitals, dashboard)
        assert len(text) < 4000

    def test_dnd5e_with_concentration(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        vitals = self._make_vitals(
            system_name="D&D 5e", system_tag="DND5E",
            party=[{"name": "Gandalf", "hp": 40, "max_hp": 50,
                    "class": "Wizard", "level": 10, "alive": True}],
        )
        dashboard = DMDashboard(Console(), "DND5E")
        dashboard.concentration.concentrate("Gandalf", "Shield")
        dashboard.death_saves.start_dying("Frodo")
        text = format_dashboard_text(vitals, dashboard)
        assert "Concentration" in text
        assert "Shield" in text
        assert "Death Saves" in text or "Frodo" in text

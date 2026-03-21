"""Tests for all new DM Dashboard mechanics modules."""

import pytest
import time
from pathlib import Path
from tempfile import TemporaryDirectory


# ── Session Timer ─────────────────────────────────────────────────────

class TestSessionTimer:
    def test_start_stop(self):
        from codex.core.mechanics.session_timer import SessionTimer
        t = SessionTimer()
        assert "started" in t.start()
        assert t.running
        assert "ended" in t.stop()
        assert not t.running

    def test_elapsed(self):
        from codex.core.mechanics.session_timer import SessionTimer
        t = SessionTimer()
        t.start()
        t.start_time = time.time() - 120  # Fake 2 minutes
        assert "2m" in t.elapsed_str()

    def test_pause_resume(self):
        from codex.core.mechanics.session_timer import SessionTimer
        t = SessionTimer()
        t.start()
        assert "paused" in t.pause().lower()
        assert "resumed" in t.resume().lower()

    def test_pacing_check(self):
        from codex.core.mechanics.session_timer import SessionTimer
        t = SessionTimer()
        t.start()
        t.start_time = time.time() - 7200  # 2 hours
        pacing = t.pacing_check()
        assert "break" in pacing.lower()


# ── Session Log ───────────────────────────────────────────────────────

class TestSessionLog:
    def test_add_note(self):
        from codex.core.mechanics.session_log import SessionLog
        log = SessionLog()
        result = log.add_note("Party entered the dungeon")
        assert "Note" in result
        assert len(log.notes) == 1

    def test_save_and_recap(self):
        from codex.core.mechanics.session_log import SessionLog
        with TemporaryDirectory() as tmpdir:
            log = SessionLog(campaign_dir=Path(tmpdir))
            log.add_note("Found the treasure")
            log.add_note("Defeated the dragon")
            result = log.save()
            assert "Saved 2 notes" in result

            # Load recap
            recap = log.load_last_recap()
            assert "treasure" in recap
            assert "dragon" in recap

    def test_no_campaign_dir(self):
        from codex.core.mechanics.session_log import SessionLog
        log = SessionLog()
        assert "not persisted" in log.save()


# ── NPC Tracker ───────────────────────────────────────────────────────

class TestNPCTracker:
    def test_log_npc(self):
        from codex.core.mechanics.npc_tracker import NPCTracker
        tracker = NPCTracker()
        result = tracker.log("Bazso", note="Met at tavern", attitude="friendly")
        assert "logged" in result.lower()
        assert len(tracker.npcs) == 1

    def test_list_npcs(self):
        from codex.core.mechanics.npc_tracker import NPCTracker
        tracker = NPCTracker()
        tracker.log("Bazso", attitude="friendly")
        tracker.log("Roric", attitude="hostile")
        result = tracker.list_npcs()
        assert "Bazso" in result
        assert "Roric" in result

    def test_filter_by_attitude(self):
        from codex.core.mechanics.npc_tracker import NPCTracker
        tracker = NPCTracker()
        tracker.log("Bazso", attitude="friendly")
        tracker.log("Roric", attitude="hostile")
        result = tracker.list_npcs(attitude="hostile")
        assert "Roric" in result
        assert "Bazso" not in result

    def test_set_attitude(self):
        from codex.core.mechanics.npc_tracker import NPCTracker
        tracker = NPCTracker()
        tracker.log("Bazso")
        result = tracker.set_attitude("Bazso", "hostile")
        assert "hostile" in result

    def test_get_info(self):
        from codex.core.mechanics.npc_tracker import NPCTracker
        tracker = NPCTracker()
        tracker.log("Bazso", note="Lampblack leader", location="Crow's Foot")
        info = tracker.get_info("Bazso")
        assert "Lampblack" in info
        assert "Crow's Foot" in info

    def test_remove(self):
        from codex.core.mechanics.npc_tracker import NPCTracker
        tracker = NPCTracker()
        tracker.log("Bazso")
        assert "removed" in tracker.remove("Bazso").lower()
        assert len(tracker.npcs) == 0

    def test_to_dict_from_dict(self):
        from codex.core.mechanics.npc_tracker import NPCTracker
        tracker = NPCTracker()
        tracker.log("Bazso", note="Leader", attitude="friendly", location="Tavern")
        data = tracker.to_dict()
        tracker2 = NPCTracker.from_dict(data)
        assert "bazso" in tracker2.npcs
        assert tracker2.npcs["bazso"].attitude == "friendly"


# ── Concentration Tracker ─────────────────────────────────────────────

class TestConcentrationTracker:
    def test_concentrate(self):
        from codex.core.mechanics.concentration import ConcentrationTracker
        ct = ConcentrationTracker()
        result = ct.concentrate("Gandalf", "Shield")
        assert "concentrating" in result.lower()

    def test_drop_existing(self):
        from codex.core.mechanics.concentration import ConcentrationTracker
        ct = ConcentrationTracker()
        ct.concentrate("Gandalf", "Shield")
        # Starting new concentration drops old
        result = ct.concentrate("Gandalf", "Fireball")
        assert "drops" in result.lower()
        assert "Shield" in result

    def test_damage_check(self):
        from codex.core.mechanics.concentration import ConcentrationTracker
        ct = ConcentrationTracker()
        ct.concentrate("Gandalf", "Shield")
        result = ct.damage_check("Gandalf", 20)
        assert "DC 10" in result
        assert "Shield" in result

    def test_damage_check_high_damage(self):
        from codex.core.mechanics.concentration import ConcentrationTracker
        ct = ConcentrationTracker()
        ct.concentrate("Gandalf", "Shield")
        result = ct.damage_check("Gandalf", 30)
        assert "DC 15" in result

    def test_fail_save(self):
        from codex.core.mechanics.concentration import ConcentrationTracker
        ct = ConcentrationTracker()
        ct.concentrate("Gandalf", "Shield")
        result = ct.fail_save("Gandalf")
        assert "loses" in result.lower()
        assert len(ct.get_concentrating()) == 0

    def test_pass_save(self):
        from codex.core.mechanics.concentration import ConcentrationTracker
        ct = ConcentrationTracker()
        ct.concentrate("Gandalf", "Shield")
        result = ct.pass_save("Gandalf")
        assert "maintains" in result.lower()

    def test_to_dict_from_dict(self):
        from codex.core.mechanics.concentration import ConcentrationTracker
        ct = ConcentrationTracker()
        ct.concentrate("Gandalf", "Shield")
        data = ct.to_dict()
        ct2 = ConcentrationTracker.from_dict(data)
        assert "Gandalf" in ct2.get_concentrating()


# ── Death Save Tracker ────────────────────────────────────────────────

class TestDeathSaveTracker:
    def test_start_dying(self):
        from codex.core.mechanics.death_saves import DeathSaveTracker
        dst = DeathSaveTracker()
        result = dst.start_dying("Frodo")
        assert "dying" in result.lower()
        assert dst.is_dying("Frodo")

    def test_three_successes_stabilize(self):
        from codex.core.mechanics.death_saves import DeathSaveTracker
        dst = DeathSaveTracker()
        dst.start_dying("Frodo")
        dst.save_success("Frodo")
        dst.save_success("Frodo")
        result = dst.save_success("Frodo")
        assert "STABILIZED" in result
        assert not dst.is_dying("Frodo")

    def test_three_failures_death(self):
        from codex.core.mechanics.death_saves import DeathSaveTracker
        dst = DeathSaveTracker()
        dst.start_dying("Frodo")
        dst.save_failure("Frodo")
        dst.save_failure("Frodo")
        result = dst.save_failure("Frodo")
        assert "DEAD" in result
        assert not dst.is_dying("Frodo")

    def test_nat20(self):
        from codex.core.mechanics.death_saves import DeathSaveTracker
        dst = DeathSaveTracker()
        dst.start_dying("Frodo")
        result = dst.nat20("Frodo")
        assert "natural 20" in result.lower()
        assert not dst.is_dying("Frodo")

    def test_crit_fail(self):
        from codex.core.mechanics.death_saves import DeathSaveTracker
        dst = DeathSaveTracker()
        dst.start_dying("Frodo")
        result = dst.crit_fail("Frodo")
        assert "2 failures" in result

    def test_list_dying(self):
        from codex.core.mechanics.death_saves import DeathSaveTracker
        dst = DeathSaveTracker()
        dst.start_dying("Frodo")
        dst.save_success("Frodo")
        dst.save_failure("Frodo")
        result = dst.list_dying()
        assert "Frodo" in result
        assert "O" in result  # success marker
        assert "X" in result  # failure marker

    def test_to_dict_from_dict(self):
        from codex.core.mechanics.death_saves import DeathSaveTracker
        dst = DeathSaveTracker()
        dst.start_dying("Frodo")
        dst.save_success("Frodo")
        data = dst.to_dict()
        dst2 = DeathSaveTracker.from_dict(data)
        assert dst2.is_dying("Frodo")


# ── Encounter Budget ──────────────────────────────────────────────────

class TestEncounterBudget:
    def test_dnd5e_budget(self):
        from codex.core.mechanics.encounter_budget import calculate_dnd5e_budget
        result = calculate_dnd5e_budget([5, 5, 5, 5], ["3", "1", "1"])
        assert "Encounter Budget" in result
        assert "Difficulty:" in result

    def test_dnd5e_deadly(self):
        from codex.core.mechanics.encounter_budget import calculate_dnd5e_budget
        result = calculate_dnd5e_budget([1, 1], ["5"])
        assert "DEADLY" in result

    def test_fitd_threat(self):
        from codex.core.mechanics.encounter_budget import calculate_fitd_threat
        result = calculate_fitd_threat(1, 5)
        assert "Threat" in result

    def test_system_router(self):
        from codex.core.mechanics.encounter_budget import calculate_encounter
        result = calculate_encounter("DND5E", party_levels=[3], monster_crs=["1"])
        assert "Budget" in result
        result2 = calculate_encounter("BITD", tier=2, num_enemies=3)
        assert "Threat" in result2


# ── Dashboard Integration ─────────────────────────────────────────────

class TestDashboardNewCommands:
    def test_dispatch_npc_log(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        d = DMDashboard(Console(), "DND5E")
        result = d.dispatch_command("npcs log Bazso Met at tavern")
        assert "logged" in result.lower()

    def test_dispatch_timer(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        d = DMDashboard(Console(), "DND5E")
        result = d.dispatch_command("timer")
        assert "Session time" in result or "0m" in result

    def test_dispatch_concentrate(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        d = DMDashboard(Console(), "DND5E")
        result = d.dispatch_command("concentrate Gandalf Shield")
        assert "concentrating" in result.lower()

    def test_dispatch_concentrate_non_5e(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        d = DMDashboard(Console(), "BITD")
        result = d.dispatch_command("concentrate Gandalf Shield")
        assert "5e only" in result.lower()

    def test_dispatch_death_save(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        d = DMDashboard(Console(), "DND5E")
        d.dispatch_command("death start Frodo")
        result = d.dispatch_command("death success Frodo")
        assert "success" in result.lower()

    def test_dispatch_budget(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        d = DMDashboard(Console(), "DND5E")
        result = d.dispatch_command("budget 5,5,5,5 vs 3,1,1")
        assert "Budget" in result

    def test_dispatch_log(self):
        from codex.core.dm_dashboard import DMDashboard
        from rich.console import Console
        d = DMDashboard(Console(), "DND5E")
        result = d.dispatch_command("log add Party found the key")
        assert "Note" in result

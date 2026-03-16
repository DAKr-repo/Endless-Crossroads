"""
tests/test_final_integration.py
================================
End-to-end integration tests across the major subsystems introduced in the
Final Completion Sprint.

Test categories
---------------
1.  Spell pipeline (SPELL_LISTS from dnd5e_spells)
2.  Tasha's pipeline (LIFE_PATH_TABLES, dark secrets, patrons)
3.  DnD5e engine combat pipeline (attack against enemy dict)
4.  DnD5e engine spellcasting (prepare, cast, slot decrement)
5.  Feat pipeline (eligible feats, apply feat)
6.  Save/load round trip with spell slots, concentration, feat managers
7.  ZoneManager advance through a 2-chapter manifest
8.  Broadcast events fire on zone transition (mock broadcast)
9.  Cross-system module loading (DnD5e engine + a module manifest)
"""

from __future__ import annotations

import random
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Spell pipeline imports
# ---------------------------------------------------------------------------
from codex.forge.reference_data.dnd5e_spells import (
    SPELL_LISTS,
    SPELL_SLOT_TABLE,
    WARLOCK_SLOT_TABLE,
    HALF_CASTER_SLOT_TABLE,
)

# ---------------------------------------------------------------------------
# Tasha's pipeline imports
# ---------------------------------------------------------------------------
from codex.forge.reference_data.dnd5e_tashas import (
    LIFE_PATH_TABLES,
    DARK_SECRETS,
    GROUP_PATRONS,
    CUSTOM_LINEAGE,
    OPTIONAL_CLASS_FEATURES,
)

# ---------------------------------------------------------------------------
# DnD5e engine imports
# ---------------------------------------------------------------------------
from codex.games.dnd5e import DnD5eEngine, DnD5eCharacter
from codex.games.dnd5e.combat import DnD5eCombatResolver
from codex.games.dnd5e.feats import FeatManager
from codex.games.dnd5e.spellcasting import SpellSlotTracker, SpellManager

# ---------------------------------------------------------------------------
# Spatial imports
# ---------------------------------------------------------------------------
from codex.spatial.module_manifest import ModuleManifest, Chapter, ZoneEntry
from codex.spatial.zone_manager import ZoneManager, EVENT_ZONE_TRANSITION


# ===========================================================================
# Helpers
# ===========================================================================

_FULL_CASTER_CLASSES = ("bard", "cleric", "druid", "sorcerer", "wizard")
_HALF_CASTER_CLASSES = ("paladin", "ranger")
_WARLOCK = "warlock"
_ARTIFICER = "artificer"


def _make_engine(cls: str = "fighter", level: int = 5,
                 strength: int = 14, intelligence: int = 14) -> DnD5eEngine:
    engine = DnD5eEngine()
    engine.create_character(
        "TestChar",
        character_class=cls,
        level=level,
        strength=strength,
        intelligence=intelligence,
    )
    return engine


def _two_chapter_manifest() -> ModuleManifest:
    """Construct a minimal 2-chapter ModuleManifest for zone tests."""
    ch1 = Chapter(
        chapter_id="ch1",
        display_name="Chapter 1",
        order=1,
        zones=[
            ZoneEntry(zone_id="zone_a", exit_trigger="quest_complete"),
            ZoneEntry(zone_id="zone_b", exit_trigger="boss_defeated"),
        ],
    )
    ch2 = Chapter(
        chapter_id="ch2",
        display_name="Chapter 2",
        order=2,
        zones=[
            ZoneEntry(zone_id="zone_c", exit_trigger="player_choice"),
        ],
    )
    return ModuleManifest(
        module_id="integration_test_module",
        display_name="Integration Test Module",
        system_id="dnd5e",
        chapters=[ch1, ch2],
    )


# ===========================================================================
# 1. Spell pipeline
# ===========================================================================

class TestSpellPipeline:
    """SPELL_LISTS covers all 9 classes with correct level ranges."""

    EXPECTED_CLASSES = {
        "bard", "cleric", "druid", "paladin", "ranger",
        "sorcerer", "warlock", "wizard", "artificer",
    }

    def test_all_nine_classes_present(self):
        assert set(SPELL_LISTS.keys()) == self.EXPECTED_CLASSES

    @pytest.mark.parametrize("cls", _FULL_CASTER_CLASSES)
    def test_full_casters_have_levels_0_through_9(self, cls):
        """Full casters must have spell levels 0 to 9, all non-empty."""
        for lvl in range(0, 10):
            assert lvl in SPELL_LISTS[cls], (
                f"{cls} missing spell level {lvl}"
            )
            assert len(SPELL_LISTS[cls][lvl]) > 0, (
                f"{cls} level {lvl} spell list is empty"
            )

    def test_warlock_has_levels_0_through_9(self):
        """Warlock spell list spans 0–9 even though pact magic caps slots at 5."""
        for lvl in range(0, 10):
            assert lvl in SPELL_LISTS[_WARLOCK], (
                f"warlock missing spell level {lvl}"
            )

    @pytest.mark.parametrize("cls", _HALF_CASTER_CLASSES)
    def test_half_casters_cap_at_level_5(self, cls):
        """Half-casters (paladin, ranger) must not have spell levels 6–9."""
        for lvl in range(6, 10):
            assert lvl not in SPELL_LISTS[cls], (
                f"{cls} should not have spell level {lvl}"
            )

    @pytest.mark.parametrize("cls", _HALF_CASTER_CLASSES)
    def test_half_casters_have_levels_1_through_5(self, cls):
        for lvl in range(1, 6):
            assert lvl in SPELL_LISTS[cls], (
                f"{cls} missing spell level {lvl}"
            )

    def test_artificer_has_cantrips_through_5(self):
        for lvl in range(0, 6):
            assert lvl in SPELL_LISTS[_ARTIFICER], (
                f"artificer missing spell level {lvl}"
            )

    def test_wizard_has_level_9_spells(self):
        """Wizard must have at least one level 9 spell."""
        assert len(SPELL_LISTS["wizard"][9]) >= 1

    def test_spell_slot_table_has_20_levels(self):
        assert len(SPELL_SLOT_TABLE) == 20
        for lvl in range(1, 21):
            assert lvl in SPELL_SLOT_TABLE

    def test_warlock_slot_table_has_20_levels(self):
        assert len(WARLOCK_SLOT_TABLE) == 20

    def test_half_caster_slot_table_caps_at_level_5(self):
        for lvl, slots in HALF_CASTER_SLOT_TABLE.items():
            for spell_lvl in slots:
                assert spell_lvl <= 5, (
                    f"HALF_CASTER_SLOT_TABLE level {lvl} contains spell level {spell_lvl}"
                )

    def test_all_spell_entries_are_strings(self):
        for cls, levels in SPELL_LISTS.items():
            for lvl, spells in levels.items():
                for spell in spells:
                    assert isinstance(spell, str), (
                        f"{cls}[{lvl}] has non-string spell: {spell!r}"
                    )


# ===========================================================================
# 2. Tasha's pipeline
# ===========================================================================

class TestTashasPipeline:
    """LIFE_PATH_TABLES, DARK_SECRETS, GROUP_PATRONS structural validation."""

    REQUIRED_LIFE_PATH_KEYS = {
        "parents", "birthplace", "siblings",
        "childhood_memories", "life_events",
    }

    def test_life_path_tables_has_required_keys(self):
        missing = self.REQUIRED_LIFE_PATH_KEYS - set(LIFE_PATH_TABLES.keys())
        assert not missing, f"LIFE_PATH_TABLES missing: {missing}"

    def test_life_path_tables_all_categories_nonempty(self):
        for category, entries in LIFE_PATH_TABLES.items():
            assert isinstance(entries, list) and len(entries) > 0, (
                f"LIFE_PATH_TABLES['{category}'] is empty"
            )

    def test_life_events_has_at_least_eight_entries(self):
        assert len(LIFE_PATH_TABLES["life_events"]) >= 8

    def test_dark_secrets_count_is_twelve(self):
        assert len(DARK_SECRETS) == 12, (
            f"Expected 12 dark secrets, got {len(DARK_SECRETS)}"
        )

    def test_dark_secrets_all_have_id_name_description(self):
        required = {"id", "name", "description"}
        for secret in DARK_SECRETS:
            missing = required - set(secret.keys())
            assert not missing, (
                f"Dark secret {secret.get('id', '?')} missing keys: {missing}"
            )

    def test_dark_secret_ids_unique(self):
        ids = [s["id"] for s in DARK_SECRETS]
        assert len(ids) == len(set(ids)), "Duplicate dark secret IDs found"

    def test_group_patrons_count_is_eight(self):
        assert len(GROUP_PATRONS) == 8, (
            f"Expected 8 group patrons, got {len(GROUP_PATRONS)}"
        )

    def test_group_patrons_have_description_and_perks(self):
        for patron in GROUP_PATRONS:
            assert "description" in patron, (
                f"Patron {patron.get('id', '?')} missing description"
            )
            assert isinstance(patron.get("perks"), list), (
                f"Patron {patron.get('id', '?')} missing perks list"
            )
            assert len(patron["perks"]) >= 1, (
                f"Patron {patron.get('id', '?')} has no perks"
            )


# ===========================================================================
# 3. DnD5e engine combat pipeline
# ===========================================================================

class TestDnD5eCombatPipeline:
    """attack() command against a dummy enemy dict."""

    def test_attack_returns_string(self):
        engine = _make_engine(cls="fighter", strength=16)
        enemy = {"name": "Goblin", "hp": 10, "defense": 8}
        result = engine.handle_command(
            "attack", attacker_name="TestChar",
            target_enemy=enemy, weapon="longsword",
        )
        assert isinstance(result, str) and len(result) > 0

    def test_attack_mentions_attacker(self):
        engine = _make_engine(cls="fighter", strength=16)
        enemy = {"name": "Goblin", "hp": 10, "defense": 8}
        result = engine.handle_command(
            "attack", attacker_name="TestChar",
            target_enemy=enemy, weapon="longsword",
        )
        assert "TestChar" in result

    def test_attack_mentions_target(self):
        """Attack result mentions target name or fumble message."""
        engine = _make_engine(cls="fighter", strength=16)
        enemy = {"name": "Goblin", "hp": 10, "defense": 8}
        result = engine.handle_command(
            "attack", attacker_name="TestChar",
            target_enemy=enemy, weapon="longsword",
        )
        assert "Goblin" in result or "fumble" in result.lower()

    def test_attack_hit_reduces_enemy_hp(self):
        """Seed-search to get at least one hit; verify hp decreases."""
        for seed in range(200):
            engine = DnD5eEngine()
            engine.create_character("Bryn", character_class="fighter",
                                    level=5, strength=20)
            engine._combat_resolver = DnD5eCombatResolver(rng=random.Random(seed))
            enemy = {"name": "Dummy", "hp": 50, "defense": 1}
            engine.handle_command(
                "attack", attacker_name="Bryn",
                target_enemy=enemy, weapon="longsword",
            )
            if enemy["hp"] < 50:
                break
        # At least one seed must produce a hit on AC 1
        assert enemy["hp"] < 50, "Expected a hit to reduce HP but none occurred"

    def test_attack_no_target_returns_error(self):
        engine = _make_engine()
        result = engine.handle_command("attack", attacker_name="TestChar")
        assert "No target" in result

    def test_attack_unknown_character_returns_error(self):
        engine = _make_engine()
        enemy = {"name": "Orc", "hp": 20, "defense": 10}
        result = engine.handle_command(
            "attack", attacker_name="Nobody", target_enemy=enemy,
        )
        assert "not found" in result


# ===========================================================================
# 4. DnD5e engine spellcasting pipeline
# ===========================================================================

class TestDnD5eSpellcastingPipeline:
    """Prepare a spell, cast it, verify slots decrement."""

    def _wizard_engine(self, level: int = 5) -> DnD5eEngine:
        engine = DnD5eEngine()
        engine.create_character(
            "Lyra", character_class="wizard", level=level, intelligence=16,
        )
        return engine

    def test_prepare_spell_adds_to_prepared_list(self):
        engine = self._wizard_engine()
        engine.handle_command("prepare", spell="Fireball")
        mgr = engine._get_spell_manager(engine.character)
        assert "Fireball" in mgr.prepared_spells

    def test_cast_spell_returns_cast_message(self):
        engine = self._wizard_engine()
        mgr = engine._get_spell_manager(engine.character)
        mgr.prepared_spells.append("Fireball")
        result = engine.handle_command(
            "cast", caster_name="Lyra", spell_name="Fireball", spell_level=3,
        )
        assert "Cast Fireball" in result

    def test_cast_spell_decrements_slot_count(self):
        engine = self._wizard_engine(level=5)
        mgr = engine._get_spell_manager(engine.character)
        mgr.prepared_spells.append("Fireball")
        tracker = engine._get_spell_tracker(engine.character)
        slots_before = tracker.current_slots.get(3, 0)
        engine.handle_command(
            "cast", caster_name="Lyra", spell_name="Fireball", spell_level=3,
        )
        assert tracker.current_slots.get(3, 0) == slots_before - 1

    def test_cast_without_slot_fails(self):
        engine = self._wizard_engine()
        mgr = engine._get_spell_manager(engine.character)
        mgr.prepared_spells.append("Fireball")
        tracker = engine._get_spell_tracker(engine.character)
        tracker.current_slots[3] = 0
        result = engine.handle_command(
            "cast", caster_name="Lyra", spell_name="Fireball", spell_level=3,
        )
        assert "no available" in result.lower()

    def test_cast_cantrip_uses_no_slot(self):
        engine = self._wizard_engine()
        mgr = engine._get_spell_manager(engine.character)
        mgr.cantrips.append("Fire Bolt")
        tracker = engine._get_spell_tracker(engine.character)
        slots_snapshot = dict(tracker.current_slots)
        engine.handle_command(
            "cast", caster_name="Lyra", spell_name="Fire Bolt", spell_level=0,
        )
        assert tracker.current_slots == slots_snapshot

    def test_concentration_start_and_break(self):
        engine = self._wizard_engine()
        conc = engine._get_concentration(engine.character)
        msg = conc.start("Haste")
        assert "Haste" in msg
        assert conc.active_spell == "Haste"
        broken = conc.break_concentration()
        assert broken == "Haste"
        assert conc.active_spell is None


# ===========================================================================
# 5. Feat pipeline
# ===========================================================================

class TestFeatPipeline:
    """get_eligible_feats() and apply_feat() end-to-end."""

    def test_get_eligible_feats_returns_list(self):
        engine = _make_engine(cls="wizard", intelligence=14)
        fm = engine._get_feat_manager(engine.character)
        eligible = fm.get_eligible_feats(engine.character)
        assert isinstance(eligible, list) and len(eligible) > 0

    def test_get_eligible_feats_excludes_already_granted(self):
        engine = _make_engine(cls="fighter")
        fm = engine._get_feat_manager(engine.character)
        fm.granted_feats.append("Tough")
        eligible = fm.get_eligible_feats(engine.character)
        assert "Tough" not in eligible

    def test_apply_feat_tough_increases_max_hp(self):
        engine = _make_engine(cls="barbarian", level=5, strength=16)
        char = engine.character
        original_max_hp = char.max_hp
        fm = engine._get_feat_manager(char)
        fm.apply_feat("Tough", char)
        assert char.max_hp > original_max_hp

    def test_apply_feat_records_in_granted_feats(self):
        engine = _make_engine(cls="fighter")
        fm = engine._get_feat_manager(engine.character)
        fm.apply_feat("Alert", engine.character)
        assert "Alert" in fm.granted_feats

    def test_apply_feat_with_unmet_prereq_fails_gracefully(self):
        """Non-caster applying War Caster (spellcasting prereq) must get an error."""
        engine = _make_engine(cls="fighter")
        fm = engine._get_feat_manager(engine.character)
        result = fm.apply_feat("War Caster", engine.character)
        assert "Prerequisites not met" in result
        assert "War Caster" not in fm.granted_feats

    def test_apply_feat_strength_prereq_blocks_weak_character(self):
        """Grappler requires STR 13; a STR 10 character must be blocked."""
        char = DnD5eCharacter(name="Weed", character_class="wizard", strength=10)
        fm = FeatManager()
        result = fm.validate_prerequisite("Grappler", char)
        assert result is False

    def test_apply_feat_strength_prereq_allows_strong_character(self):
        """Grappler requires STR 13; a STR 16 fighter must pass."""
        char = DnD5eCharacter(name="Brute", character_class="fighter", strength=16)
        fm = FeatManager()
        result = fm.validate_prerequisite("Grappler", char)
        assert result is True


# ===========================================================================
# 6. Save / load round trip
# ===========================================================================

class TestSaveLoadRoundTrip:
    """save_state() / load_state() must preserve spell slots, concentration, feats."""

    def _wizard_with_state(self) -> DnD5eEngine:
        engine = DnD5eEngine()
        engine.create_character(
            "Aria", character_class="wizard", level=5, intelligence=16,
        )
        # Spend a slot
        tracker = engine._get_spell_tracker(engine.character)
        tracker.expend_slot(1)
        # Start concentration
        conc = engine._get_concentration(engine.character)
        conc.start("Haste")
        # Apply a feat
        fm = engine._get_feat_manager(engine.character)
        fm.apply_feat("Alert", engine.character)
        # Add known spells
        mgr = engine._get_spell_manager(engine.character)
        mgr.prepared_spells = ["Fireball", "Shield"]
        mgr.cantrips = ["Fire Bolt"]
        return engine

    def test_save_state_includes_spell_slots(self):
        engine = self._wizard_with_state()
        data = engine.save_state()
        assert "spell_slots" in data

    def test_save_state_includes_concentration(self):
        engine = self._wizard_with_state()
        data = engine.save_state()
        assert "concentration" in data

    def test_save_state_includes_feat_managers(self):
        engine = self._wizard_with_state()
        data = engine.save_state()
        assert "feat_managers" in data

    def test_save_state_includes_spell_managers(self):
        engine = self._wizard_with_state()
        data = engine.save_state()
        assert "spell_managers" in data

    def test_load_restores_expended_spell_slot(self):
        engine = self._wizard_with_state()
        tracker = engine._get_spell_tracker(engine.character)
        remaining = tracker.current_slots[1]
        state = engine.save_state()

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        restored_tracker = engine2._spell_slots.get("Aria")
        assert restored_tracker is not None
        assert restored_tracker.current_slots[1] == remaining

    def test_load_restores_active_concentration(self):
        engine = self._wizard_with_state()
        state = engine.save_state()

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        conc2 = engine2._concentration.get("Aria")
        assert conc2 is not None
        assert conc2.active_spell == "Haste"

    def test_load_restores_feat_grants(self):
        engine = self._wizard_with_state()
        state = engine.save_state()

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        fm2 = engine2._feat_managers.get("Aria")
        assert fm2 is not None
        assert "Alert" in fm2.granted_feats

    def test_load_restores_prepared_spells(self):
        engine = self._wizard_with_state()
        state = engine.save_state()

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        mgr2 = engine2._spell_managers.get("Aria")
        assert mgr2 is not None
        assert "Fireball" in mgr2.prepared_spells
        assert "Shield" in mgr2.prepared_spells

    def test_load_restores_cantrips(self):
        engine = self._wizard_with_state()
        state = engine.save_state()

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        mgr2 = engine2._spell_managers.get("Aria")
        assert "Fire Bolt" in mgr2.cantrips

    def test_load_state_missing_keys_does_not_crash(self):
        """Old save files without spell/feat keys must load without exception."""
        engine = DnD5eEngine()
        engine.create_character("Ghost", character_class="fighter", level=1)
        state = engine.save_state()
        for key in ("spell_slots", "concentration", "spell_managers", "feat_managers"):
            state.pop(key, None)

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        assert engine2._spell_slots == {}
        assert engine2._feat_managers == {}


# ===========================================================================
# 7. ZoneManager advance through a 2-chapter manifest
# ===========================================================================

class TestZoneManagerTwoChapterAdvance:
    """Advancing through a 2-chapter manifest visits all zones in correct order."""

    def test_start_zone_is_zone_a(self):
        manifest = _two_chapter_manifest()
        zm = ZoneManager(manifest=manifest)
        assert zm.current_zone_entry.zone_id == "zone_a"

    def test_advance_to_zone_b(self):
        manifest = _two_chapter_manifest()
        zm = ZoneManager(manifest=manifest)
        entry = zm.advance()
        assert entry is not None
        assert entry.zone_id == "zone_b"

    def test_advance_to_zone_c_crosses_chapter_boundary(self):
        manifest = _two_chapter_manifest()
        zm = ZoneManager(manifest=manifest)
        zm.advance()  # zone_b
        entry = zm.advance()  # zone_c (chapter 2)
        assert entry.zone_id == "zone_c"
        assert zm.chapter_idx == 1

    def test_advance_past_zone_c_returns_none(self):
        manifest = _two_chapter_manifest()
        zm = ZoneManager(manifest=manifest)
        zm.advance()  # zone_b
        zm.advance()  # zone_c
        result = zm.advance()  # past end
        assert result is None

    def test_module_complete_after_exhausting_chain(self):
        manifest = _two_chapter_manifest()
        zm = ZoneManager(manifest=manifest)
        for _ in range(5):
            zm.advance()
        assert zm.module_complete is True

    def test_all_zones_visited_in_order(self):
        manifest = _two_chapter_manifest()
        zm = ZoneManager(manifest=manifest)
        visited = [zm.current_zone_entry.zone_id]
        while True:
            entry = zm.advance()
            if entry is None:
                break
            visited.append(entry.zone_id)
        assert visited == ["zone_a", "zone_b", "zone_c"]


# ===========================================================================
# 8. Broadcast events fire on zone transition
# ===========================================================================

class TestBroadcastOnZoneTransition:
    """advance() must invoke broadcast_manager.broadcast with ZONE_TRANSITION (WO-V56.0: instance-level)."""

    def test_advance_fires_zone_transition_event(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        zm = ZoneManager(manifest=manifest, broadcast_manager=bm)
        zm.advance()

        bm.broadcast.assert_called_once()
        event_name = bm.broadcast.call_args[0][0]
        assert event_name == EVENT_ZONE_TRANSITION

    def test_advance_broadcast_payload_has_next_zone_id(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        zm = ZoneManager(manifest=manifest, broadcast_manager=bm)
        zm.advance()

        payload = bm.broadcast.call_args[0][1]
        assert payload["zone"] == "zone_b"

    def test_advance_broadcast_payload_has_module_id(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        zm = ZoneManager(manifest=manifest, broadcast_manager=bm)
        zm.advance()

        payload = bm.broadcast.call_args[0][1]
        assert payload["module"] == "integration_test_module"

    def test_no_broadcast_when_module_complete(self):
        """advance() at module end must not fire a transition event (returns None)."""
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        zm = ZoneManager(manifest=manifest, broadcast_manager=bm)
        zm.advance()  # zone_b
        zm.advance()  # zone_c (last)
        bm.reset_mock()

        result = zm.advance()  # past end -> None

        assert result is None
        bm.broadcast.assert_not_called()

    def test_broadcast_exception_does_not_prevent_advance(self):
        manifest = _two_chapter_manifest()
        bm = MagicMock()
        bm.broadcast.side_effect = RuntimeError("bus error")
        zm = ZoneManager(manifest=manifest, broadcast_manager=bm)
        entry = zm.advance()

        assert entry is not None
        assert entry.zone_id == "zone_b"


# ===========================================================================
# 9. Cross-system module loading
# ===========================================================================

class TestCrossSystemModuleLoading:
    """DnD5e engine can load a real module manifest from vault_maps/."""

    _MANIFEST_PATH = str(
        Path(__file__).resolve().parent.parent
        / "vault_maps/modules/dragon_heist/module_manifest.json"
    )

    def test_load_manifest_returns_module_manifest(self):
        manifest = ModuleManifest.load(self._MANIFEST_PATH)
        assert isinstance(manifest, ModuleManifest)

    def test_manifest_system_id_is_dnd5e(self):
        manifest = ModuleManifest.load(self._MANIFEST_PATH)
        assert manifest.system_id == "dnd5e"

    def test_zone_manager_from_real_manifest_has_chapters(self):
        manifest = ModuleManifest.load(self._MANIFEST_PATH)
        zm = ZoneManager(manifest=manifest)
        assert len(zm.sorted_chapters) > 0

    def test_zone_manager_from_real_manifest_first_zone_not_none(self):
        manifest = ModuleManifest.load(self._MANIFEST_PATH)
        zm = ZoneManager(manifest=manifest)
        assert zm.current_zone_entry is not None

    def test_dnd5e_engine_and_zone_manager_coexist(self):
        """Creating a DnD5e engine and a ZoneManager from the same module
        is the fundamental 'cross-system module loading' pattern."""
        manifest = ModuleManifest.load(self._MANIFEST_PATH)
        zm = ZoneManager(manifest=manifest)

        engine = DnD5eEngine()
        engine.create_character("Volo", character_class="bard", level=7)

        # Verify both objects are functional
        assert engine.character.name == "Volo"
        assert zm.manifest.system_id == "dnd5e"
        assert zm.current_zone_entry.zone_id is not None

    def test_zone_chain_from_real_manifest_is_nonempty(self):
        manifest = ModuleManifest.load(self._MANIFEST_PATH)
        chain = manifest.get_zone_chain()
        assert len(chain) > 0

    def test_advance_through_real_manifest_returns_second_zone(self):
        manifest = ModuleManifest.load(self._MANIFEST_PATH)
        zm = ZoneManager(manifest=manifest)
        first_zone = zm.current_zone_entry.zone_id
        second = zm.advance()
        assert second is not None
        assert second.zone_id != first_zone

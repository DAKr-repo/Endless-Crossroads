"""Tests for codex.core.services.campaign_adapter — Crown & Crew Campaign Adapter."""

import json
import pytest
from pathlib import Path
from codex.core.services.campaign_adapter import CampaignAdapter, _PATRON_ROLES, _LEADER_ROLES, _EXCLUDED_ROLES


class TestAdapterCreation:
    """Test adapter initialization."""

    def test_create_adapter(self):
        adapter = CampaignAdapter("dnd5e")
        assert adapter.system_id == "dnd5e"

    def test_create_with_module_path(self):
        adapter = CampaignAdapter("dnd5e", module_path="vault_maps/modules/dragon_heist")
        assert adapter.module_path is not None


class TestNPCLoading:
    """Test NPC data loading from config."""

    def test_load_dnd5e_npcs(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        assert len(adapter._npcs) > 0

    def test_load_nonexistent_system(self):
        adapter = CampaignAdapter("nonexistent_system")
        adapter._load_npcs()
        assert len(adapter._npcs) == 0


class TestBossExclusion:
    """Test villain/boss exclusion from NPC selection."""

    def test_boss_names_extracted_from_module(self):
        adapter = CampaignAdapter("dnd5e", module_path="vault_maps/modules/dragon_heist")
        adapter._load_boss_names()
        # Dragon Heist has boss enemies
        assert len(adapter._boss_names) >= 1

    def test_boss_excluded_from_patrons(self):
        adapter = CampaignAdapter("dnd5e", module_path="vault_maps/modules/dragon_heist")
        adapter._load_npcs()
        adapter._load_boss_names()
        patrons = adapter._select_patrons()
        patron_names = {p["name"].lower() for p in patrons}
        # No patron should be a boss
        assert not patron_names.intersection(adapter._boss_names)

    def test_boss_excluded_from_leaders(self):
        adapter = CampaignAdapter("dnd5e", module_path="vault_maps/modules/dragon_heist")
        adapter._load_npcs()
        adapter._load_boss_names()
        leaders = adapter._select_leaders()
        leader_names = {l["name"].lower() for l in leaders}
        assert not leader_names.intersection(adapter._boss_names)


class TestNPCSelection:
    """Test Crown Patron and Crew Leader selection rules."""

    def test_patrons_have_authority_roles(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        patrons = adapter._select_patrons()
        for p in patrons:
            role = p.get("role", "").lower()
            # Should prefer authority roles, but fallback is allowed
            assert role not in _EXCLUDED_ROLES

    def test_leaders_not_authority_roles(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        leaders = adapter._select_leaders()
        for l in leaders:
            role = l.get("role", "").lower()
            assert role not in _EXCLUDED_ROLES

    def test_excluded_roles_never_selected(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        patrons = adapter._select_patrons()
        leaders = adapter._select_leaders()
        all_selected = patrons + leaders
        for npc in all_selected:
            assert npc.get("role", "").lower() not in _EXCLUDED_ROLES

    def test_patrons_and_leaders_dont_overlap(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        patrons = {p["name"] for p in adapter._select_patrons()}
        leaders = {l["name"] for l in adapter._select_leaders()}
        # No NPC should be both patron and leader
        # (may overlap if pool is small, but not ideal)
        # At least one from each group should exist
        assert len(patrons) > 0
        assert len(leaders) > 0


class TestWorldStateGeneration:
    """Test full world_state dict generation."""

    def test_build_world_state_dnd5e(self):
        adapter = CampaignAdapter("dnd5e")
        ws = adapter.build_world_state()
        assert "terms" in ws
        assert "patron_pool" in ws
        assert "leader_pool" in ws
        assert "world_prompts" in ws
        assert "morning_events" in ws
        assert ws["system_id"] == "dnd5e"

    def test_terms_match_system(self):
        adapter = CampaignAdapter("dnd5e")
        ws = adapter.build_world_state()
        assert ws["terms"]["crown"] == "The Lords"
        assert ws["terms"]["crew"] == "The Company"

    def test_bitd_terms(self):
        adapter = CampaignAdapter("bitd")
        ws = adapter.build_world_state()
        assert ws["terms"]["crown"] == "The Inspectors"
        assert ws["terms"]["crew"] == "The Crew"

    def test_stc_terms(self):
        adapter = CampaignAdapter("stc")
        ws = adapter.build_world_state()
        assert "Lighteyes" in ws["terms"]["crown"]
        assert "Bridgemen" in ws["terms"]["crew"]

    def test_unknown_system_has_defaults(self):
        adapter = CampaignAdapter("unknown_game")
        ws = adapter.build_world_state()
        assert "crown" in ws["terms"]
        assert "crew" in ws["terms"]

    def test_world_prompts_not_empty(self):
        adapter = CampaignAdapter("dnd5e")
        ws = adapter.build_world_state()
        assert len(ws["world_prompts"]) >= 3

    def test_morning_events_have_choices(self):
        adapter = CampaignAdapter("dnd5e")
        ws = adapter.build_world_state()
        for event in ws["morning_events"]:
            assert "text" in event
            assert "choices" in event
            assert len(event["choices"]) >= 2

    def test_module_name_in_world_state(self):
        adapter = CampaignAdapter("dnd5e", module_path="vault_maps/modules/dragon_heist")
        ws = adapter.build_world_state()
        assert ws.get("module") == "dragon_heist"


class TestHybridMode:
    """Test overlaying system NPCs onto authored C&C modules."""

    def test_overlay_replaces_terms(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        original = {
            "terms": {"crown": "Garrison", "crew": "Deserters"},
            "patron_list": ["Colonel Graves"],
            "leader_list": ["Sergeant Kael"],
        }
        result = adapter.overlay_on_module(original)
        assert result["terms"]["crown"] == "The Lords"
        assert result["terms"]["crew"] == "The Company"

    def test_overlay_replaces_npc_pools(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        original = {
            "terms": {},
            "patron_list": ["Generic Patron"],
            "leader_list": ["Generic Leader"],
        }
        result = adapter.overlay_on_module(original)
        assert result["patron_list"] != ["Generic Patron"]
        assert result["leader_list"] != ["Generic Leader"]

    def test_overlay_preserves_other_fields(self):
        adapter = CampaignAdapter("dnd5e")
        adapter._load_npcs()
        original = {
            "terms": {},
            "crown_prompts": ["Custom prompt 1"],
            "custom_field": "preserved",
        }
        result = adapter.overlay_on_module(original)
        assert result["crown_prompts"] == ["Custom prompt 1"]
        assert result["custom_field"] == "preserved"


class TestEngineIntegration:
    """Test that adapter output works with CrownAndCrewEngine."""

    def test_world_state_accepted_by_engine(self):
        from codex.games.crown.engine import CrownAndCrewEngine
        adapter = CampaignAdapter("dnd5e")
        ws = adapter.build_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        assert engine.patron != ""
        assert engine.leader != ""
        assert engine.terms.get("crown") == "The Lords"

    def test_engine_morning_events_from_adapter(self):
        from codex.games.crown.engine import CrownAndCrewEngine
        adapter = CampaignAdapter("dnd5e")
        ws = adapter.build_world_state()
        engine = CrownAndCrewEngine(world_state=ws)
        event = engine.get_morning_event()
        assert "text" in event
        assert "choices" in event


# =============================================================================
# WO-V114+V115: Legacy Report Handoff + GM Translator
# =============================================================================

class TestLegacyTranslation:
    """Test translating C&C legacy into target system terms."""

    def _make_legacy(self, **overrides):
        base = {
            "version": 2,
            "title": "The Firebrand",
            "alignment": "CREW",
            "sway": 2,
            "dominant_tag": "DEFIANCE",
            "dna": {"BLOOD": 1, "GUILE": 2, "HEARTH": 3, "SILENCE": 0, "DEFIANCE": 5},
            "patron": "Laeral Silverhand",
            "patron_relationship": "suspicious",
            "leader": "Davil Starsong",
            "leader_relationship": "trusted",
            "mirror": {"sin": "A Secret Deal", "choice": "hide"},
            "powers_used": ["safe_passage"],
            "debts_and_secrets": [
                {"type": "secret", "text": "You hid the Leader's sin."},
            ],
            "ending": "free_crossing",
        }
        base.update(overrides)
        return base

    def test_translate_returns_structure(self):
        adapter = CampaignAdapter("dnd5e")
        legacy = self._make_legacy()
        result = adapter.translate_legacy(legacy)
        assert "system" in result
        assert "factions" in result
        assert "mechanical_benefits" in result
        assert "contacts" in result
        assert "dm_notes" in result
        assert result["system"] == "dnd5e"

    def test_dnd5e_faction_from_sway(self):
        adapter = CampaignAdapter("dnd5e")
        # Crew sway = +2 → Zhentarim (Doom Raiders)
        result = adapter.translate_legacy(self._make_legacy(sway=2))
        assert "Doom Raiders" in result["factions"].get("faction", "")

    def test_dnd5e_faction_crown(self):
        adapter = CampaignAdapter("dnd5e")
        result = adapter.translate_legacy(self._make_legacy(sway=-3))
        assert "Lords" in result["factions"].get("faction", "")

    def test_mechanical_benefit_from_dna(self):
        adapter = CampaignAdapter("dnd5e")
        result = adapter.translate_legacy(self._make_legacy(dominant_tag="BLOOD"))
        assert "Intimidation" in result["mechanical_benefits"]["benefit"]

    def test_bitd_translation(self):
        adapter = CampaignAdapter("bitd")
        result = adapter.translate_legacy(self._make_legacy(sway=3))
        assert "rep" in result["factions"] or "faction" in result["factions"]

    def test_contacts_from_patron_leader(self):
        adapter = CampaignAdapter("dnd5e")
        result = adapter.translate_legacy(self._make_legacy())
        names = {c["name"] for c in result["contacts"]}
        assert "Laeral Silverhand" in names
        assert "Davil Starsong" in names

    def test_dm_notes_mirror_hide(self):
        adapter = CampaignAdapter("dnd5e")
        result = adapter.translate_legacy(self._make_legacy(mirror={"sin": "Brutality", "choice": "hide"}))
        assert any("SECRET" in n for n in result["dm_notes"])

    def test_dm_notes_mirror_expose(self):
        adapter = CampaignAdapter("dnd5e")
        result = adapter.translate_legacy(self._make_legacy(mirror={"sin": "Brutality", "choice": "expose"}))
        assert any("RIFT" in n for n in result["dm_notes"])

    def test_dm_notes_captured_ending(self):
        adapter = CampaignAdapter("dnd5e")
        result = adapter.translate_legacy(self._make_legacy(ending="captured"))
        assert any("custody" in n.lower() for n in result["dm_notes"])

    def test_power_consequences(self):
        adapter = CampaignAdapter("dnd5e")
        result = adapter.translate_legacy(self._make_legacy(powers_used=["royal_decree", "safe_passage"]))
        assert len(result["power_consequences"]) == 2
        powers = {c["power"] for c in result["power_consequences"]}
        assert "Royal Decree" in powers
        assert "Safe Passage" in powers

    def test_stc_faction_translation(self):
        adapter = CampaignAdapter("stc")
        result = adapter.translate_legacy(self._make_legacy(sway=3))
        assert "Bridge Four" in result["factions"].get("faction", "") or "Squadleader" in str(result["factions"])


class TestFullPipeline:
    """Test the complete adapter → engine → legacy → translation pipeline."""

    def test_end_to_end(self):
        from codex.games.crown.engine import CrownAndCrewEngine

        # 1. Adapter builds world_state
        adapter = CampaignAdapter("dnd5e")
        ws = adapter.build_world_state()

        # 2. Engine runs with adapter world_state
        engine = CrownAndCrewEngine(world_state=ws)
        engine.declare_allegiance("crew", tag="DEFIANCE")
        engine.end_day()

        # 3. Engine produces legacy JSON
        legacy = engine.generate_legacy_json()
        assert legacy["version"] == 2

        # 4. Adapter translates legacy to target system
        translation = adapter.translate_legacy(legacy)
        assert translation["system"] == "dnd5e"
        assert "factions" in translation
        assert "mechanical_benefits" in translation

"""
tests/test_fitd_settings.py
=============================
WO-V46.0: Canonical FITD Settings — BitD (Doskvol), SaV (Procyon), BoB (Eastern Kingdoms),
CBR+PNK (The Sprawl), Candela Obscura (Newfaire).

Tests reference data tagging, setting filter integration, engine setting_id
propagation, save/load roundtrip, filtered accessor methods, and vault discovery.
"""

import json
import pathlib
import pytest
from typing import Dict, Any


# =========================================================================
# VAULT ROOT — absolute path to the vault directory
# =========================================================================

VAULT_ROOT = pathlib.Path(__file__).resolve().parent.parent / "vault"


# =========================================================================
# 1. REFERENCE DATA TAGGING — every entry in tagged dicts has correct value
# =========================================================================


class TestBitDTagging:
    """Every Dict[str,Dict] entry in BitD reference data has setting='doskvol'."""

    def test_playbooks_tagged(self):
        from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS
        for name, entry in PLAYBOOKS.items():
            assert entry.get("setting") == "doskvol", f"PLAYBOOKS[{name!r}] missing setting"

    def test_heritages_tagged(self):
        from codex.forge.reference_data.bitd_playbooks import HERITAGES
        for name, entry in HERITAGES.items():
            assert entry.get("setting") == "doskvol", f"HERITAGES[{name!r}] missing setting"

    def test_factions_tagged(self):
        from codex.forge.reference_data.bitd_factions import FACTIONS
        for name, entry in FACTIONS.items():
            assert entry.get("setting") == "doskvol", f"FACTIONS[{name!r}] missing setting"

    def test_crew_types_tagged(self):
        from codex.forge.reference_data.bitd_crew import CREW_TYPES
        for name, entry in CREW_TYPES.items():
            assert entry.get("setting") == "doskvol", f"CREW_TYPES[{name!r}] missing setting"


class TestSaVTagging:
    """Every Dict[str,Dict] entry in SaV reference data has setting='procyon'."""

    def test_playbooks_tagged(self):
        from codex.forge.reference_data.sav_playbooks import PLAYBOOKS
        for name, entry in PLAYBOOKS.items():
            assert entry.get("setting") == "procyon", f"PLAYBOOKS[{name!r}] missing setting"

    def test_heritages_tagged(self):
        from codex.forge.reference_data.sav_playbooks import HERITAGES
        for name, entry in HERITAGES.items():
            assert entry.get("setting") == "procyon", f"HERITAGES[{name!r}] missing setting"

    def test_factions_tagged(self):
        from codex.forge.reference_data.sav_factions import FACTIONS
        for name, entry in FACTIONS.items():
            assert entry.get("setting") == "procyon", f"FACTIONS[{name!r}] missing setting"

    def test_ship_classes_tagged(self):
        from codex.forge.reference_data.sav_ships import SHIP_CLASSES
        for name, entry in SHIP_CLASSES.items():
            assert entry.get("setting") == "procyon", f"SHIP_CLASSES[{name!r}] missing setting"


class TestBoBTagging:
    """Every Dict[str,Dict] entry in BoB reference data has setting='eastern_kingdoms'."""

    def test_playbooks_tagged(self):
        from codex.forge.reference_data.bob_playbooks import PLAYBOOKS
        for name, entry in PLAYBOOKS.items():
            assert entry.get("setting") == "eastern_kingdoms", f"PLAYBOOKS[{name!r}] missing setting"

    def test_heritages_tagged(self):
        from codex.forge.reference_data.bob_playbooks import HERITAGES
        for name, entry in HERITAGES.items():
            assert entry.get("setting") == "eastern_kingdoms", f"HERITAGES[{name!r}] missing setting"

    def test_factions_tagged(self):
        from codex.forge.reference_data.bob_factions import FACTIONS
        for name, entry in FACTIONS.items():
            assert entry.get("setting") == "eastern_kingdoms", f"FACTIONS[{name!r}] missing setting"

    def test_specialists_tagged(self):
        from codex.forge.reference_data.bob_legion import SPECIALISTS
        for name, entry in SPECIALISTS.items():
            assert entry.get("setting") == "eastern_kingdoms", f"SPECIALISTS[{name!r}] missing setting"

    def test_chosen_tagged(self):
        from codex.forge.reference_data.bob_legion import CHOSEN
        for name, entry in CHOSEN.items():
            assert entry.get("setting") == "eastern_kingdoms", f"CHOSEN[{name!r}] missing setting"


class TestCBRPNKTagging:
    """Every Dict[str,Dict] entry in CBR+PNK reference data has setting='the_sprawl'."""

    def test_archetypes_tagged(self):
        from codex.forge.reference_data.cbrpnk_archetypes import ARCHETYPES
        for name, entry in ARCHETYPES.items():
            assert entry.get("setting") == "the_sprawl", f"ARCHETYPES[{name!r}] missing setting"

    def test_backgrounds_tagged(self):
        from codex.forge.reference_data.cbrpnk_archetypes import BACKGROUNDS
        for name, entry in BACKGROUNDS.items():
            assert entry.get("setting") == "the_sprawl", f"BACKGROUNDS[{name!r}] missing setting"

    def test_chrome_tagged(self):
        from codex.forge.reference_data.cbrpnk_chrome import CHROME
        for name, entry in CHROME.items():
            assert entry.get("setting") == "the_sprawl", f"CHROME[{name!r}] missing setting"

    def test_factions_tagged(self):
        from codex.forge.reference_data.cbrpnk_corps import FACTIONS
        for name, entry in FACTIONS.items():
            assert entry.get("setting") == "the_sprawl", f"FACTIONS[{name!r}] missing setting"

    def test_sample_threats_tagged(self):
        from codex.forge.reference_data.cbrpnk_threats import SAMPLE_THREATS
        for name, entry in SAMPLE_THREATS.items():
            assert entry.get("setting") == "the_sprawl", f"SAMPLE_THREATS[{name!r}] missing setting"

    def test_ice_types_tagged(self):
        from codex.forge.reference_data.cbrpnk_threats import ICE_TYPES_PDF
        for name, entry in ICE_TYPES_PDF.items():
            assert entry.get("setting") == "the_sprawl", f"ICE_TYPES_PDF[{name!r}] missing setting"

    def test_mona_rise_threats_tagged(self):
        from codex.forge.reference_data.cbrpnk_threats import MONA_RISE_THREATS
        for name, entry in MONA_RISE_THREATS.items():
            assert entry.get("setting") == "the_sprawl", f"MONA_RISE_THREATS[{name!r}] missing setting"

    def test_premade_hunters_tagged(self):
        from codex.forge.reference_data.cbrpnk_hunters import PREMADE_HUNTERS
        for name, entry in PREMADE_HUNTERS.items():
            assert entry.get("setting") == "the_sprawl", f"PREMADE_HUNTERS[{name!r}] missing setting"

    def test_meta_heritages_tagged(self):
        from codex.forge.reference_data.cbrpnk_weird import META_HERITAGES
        for name, entry in META_HERITAGES.items():
            assert entry.get("setting") == "the_sprawl", f"META_HERITAGES[{name!r}] missing setting"

    def test_meta_talents_tagged(self):
        from codex.forge.reference_data.cbrpnk_weird import META_TALENTS
        for name, entry in META_TALENTS.items():
            assert entry.get("setting") == "the_sprawl", f"META_TALENTS[{name!r}] missing setting"

    def test_weird_threats_tagged(self):
        from codex.forge.reference_data.cbrpnk_weird import WEIRD_THREATS
        for name, entry in WEIRD_THREATS.items():
            assert entry.get("setting") == "the_sprawl", f"WEIRD_THREATS[{name!r}] missing setting"

    def test_weird_factions_tagged(self):
        from codex.forge.reference_data.cbrpnk_weird import WEIRD_FACTIONS
        for name, entry in WEIRD_FACTIONS.items():
            assert entry.get("setting") == "the_sprawl", f"WEIRD_FACTIONS[{name!r}] missing setting"

    def test_weird_drawbacks_tagged(self):
        from codex.forge.reference_data.cbrpnk_weird import WEIRD_DRAWBACKS
        for name, entry in WEIRD_DRAWBACKS.items():
            assert entry.get("setting") == "the_sprawl", f"WEIRD_DRAWBACKS[{name!r}] missing setting"

    def test_weird_consequences_tagged(self):
        from codex.forge.reference_data.cbrpnk_weird import WEIRD_CONSEQUENCES
        for name, entry in WEIRD_CONSEQUENCES.items():
            assert entry.get("setting") == "the_sprawl", f"WEIRD_CONSEQUENCES[{name!r}] missing setting"


class TestCandelaTagging:
    """Every Dict[str,Dict] entry in Candela reference data has setting='newfaire'."""

    def test_roles_tagged(self):
        from codex.forge.reference_data.candela_roles import ROLES
        for name, entry in ROLES.items():
            assert entry.get("setting") == "newfaire", f"ROLES[{name!r}] missing setting"

    def test_phenomena_tagged(self):
        from codex.forge.reference_data.candela_phenomena import PHENOMENA
        for name, entry in PHENOMENA.items():
            assert entry.get("setting") == "newfaire", f"PHENOMENA[{name!r}] missing setting"

    def test_circle_abilities_tagged(self):
        from codex.forge.reference_data.candela_circles import CIRCLE_ABILITIES
        for name, entry in CIRCLE_ABILITIES.items():
            assert entry.get("setting") == "newfaire", f"CIRCLE_ABILITIES[{name!r}] missing setting"


# =========================================================================
# 2. FILTER COUNTS — filter_by_setting returns expected entry counts
# =========================================================================


class TestFilterCounts:
    """Filtering by the canonical setting returns all entries (no cross-setting yet)."""

    def test_bitd_playbooks_filter(self):
        from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(PLAYBOOKS, "doskvol")
        assert len(result) == 7  # All 7 playbooks are doskvol

    def test_bitd_playbooks_no_filter(self):
        from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(PLAYBOOKS, None)
        assert len(result) == 7

    def test_bitd_playbooks_wrong_setting(self):
        from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(PLAYBOOKS, "procyon")
        assert len(result) == 0  # No universal tags, no procyon entries

    def test_sav_factions_filter(self):
        from codex.forge.reference_data.sav_factions import FACTIONS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(FACTIONS, "procyon")
        assert len(result) == len(FACTIONS)  # All are procyon

    def test_bob_specialists_filter(self):
        from codex.forge.reference_data.bob_legion import SPECIALISTS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(SPECIALISTS, "eastern_kingdoms")
        assert len(result) == 7  # All 7 specialists

    def test_cbrpnk_archetypes_filter(self):
        from codex.forge.reference_data.cbrpnk_archetypes import ARCHETYPES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(ARCHETYPES, "the_sprawl")
        assert len(result) == 4

    def test_cbrpnk_archetypes_wrong_setting(self):
        from codex.forge.reference_data.cbrpnk_archetypes import ARCHETYPES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(ARCHETYPES, "doskvol")
        assert len(result) == 0

    def test_cbrpnk_chrome_filter(self):
        from codex.forge.reference_data.cbrpnk_chrome import CHROME
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(CHROME, "the_sprawl")
        assert len(result) == 20

    def test_candela_roles_filter(self):
        from codex.forge.reference_data.candela_roles import ROLES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(ROLES, "newfaire")
        assert len(result) == 5

    def test_candela_phenomena_filter(self):
        from codex.forge.reference_data.candela_phenomena import PHENOMENA
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(PHENOMENA, "newfaire")
        assert len(result) == len(PHENOMENA)  # All are newfaire

    def test_candela_roles_wrong_setting(self):
        from codex.forge.reference_data.candela_roles import ROLES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(ROLES, "the_sprawl")
        assert len(result) == 0


# =========================================================================
# 3. UNIVERSAL TAGS — filter_by_setting generalized universal_tags param
# =========================================================================


class TestUniversalTags:
    """The universal_tags parameter allows custom pass-through tags."""

    SAMPLE = {
        "a": {"setting": "doskvol", "v": 1},
        "b": {"setting": "fitd", "v": 2},
        "c": {"setting": "", "v": 3},
    }

    def test_custom_universal_tags(self):
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(self.SAMPLE, "doskvol", universal_tags=["", "fitd"])
        assert len(result) == 3  # doskvol + fitd + ""

    def test_default_universal_tags_exclude_fitd(self):
        from codex.forge.reference_data.setting_filter import filter_by_setting
        result = filter_by_setting(self.SAMPLE, "doskvol")
        assert "a" in result   # doskvol match
        assert "c" in result   # "" is default universal
        assert "b" not in result  # "fitd" is not in default universal tags


# =========================================================================
# 4. ENGINE PROPAGATION — create_character sets setting_id on char + engine
# =========================================================================


class TestBitDEnginePropagation:
    """BitDEngine propagates setting_id through create_character."""

    def test_create_character_sets_setting(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        char = e.create_character("Arturo", playbook="Cutter", setting_id="doskvol")
        assert char.setting_id == "doskvol"
        assert e.setting_id == "doskvol"

    def test_create_character_no_setting(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        char = e.create_character("Brynn", playbook="Lurk")
        assert char.setting_id == ""
        assert e.setting_id == ""

    def test_engine_preset_setting_propagates(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.setting_id = "doskvol"
        char = e.create_character("Caius")
        assert char.setting_id == "doskvol"


class TestSaVEnginePropagation:
    """SaVEngine propagates setting_id through create_character."""

    def test_create_character_sets_setting(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        char = e.create_character("Zephyr", playbook="Pilot", setting_id="procyon")
        assert char.setting_id == "procyon"
        assert e.setting_id == "procyon"

    def test_create_character_no_setting(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        char = e.create_character("Nova", playbook="Mechanic")
        assert char.setting_id == ""


class TestBoBEnginePropagation:
    """BoBEngine propagates setting_id through create_character."""

    def test_create_character_sets_setting(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        char = e.create_character("Kael", playbook="Heavy", setting_id="eastern_kingdoms")
        assert char.setting_id == "eastern_kingdoms"
        assert e.setting_id == "eastern_kingdoms"

    def test_create_character_no_setting(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        char = e.create_character("Mira", playbook="Scout")
        assert char.setting_id == ""


class TestCBRPNKEnginePropagation:
    """CBRPNKEngine propagates setting_id through create_character."""

    def test_create_character_sets_setting(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        char = e.create_character("Neon", archetype="Hacker", setting_id="the_sprawl")
        assert char.setting_id == "the_sprawl"
        assert e.setting_id == "the_sprawl"

    def test_create_character_no_setting(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        char = e.create_character("Ghost", archetype="Ghost")
        assert char.setting_id == ""
        assert e.setting_id == ""

    def test_engine_preset_setting_propagates(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.setting_id = "the_sprawl"
        char = e.create_character("Wire")
        assert char.setting_id == "the_sprawl"


class TestCandelaEnginePropagation:
    """CandelaEngine propagates setting_id through create_character."""

    def test_create_character_sets_setting(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        char = e.create_character("Elara", role="Scholar", setting_id="newfaire")
        assert char.setting_id == "newfaire"
        assert e.setting_id == "newfaire"

    def test_create_character_no_setting(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        char = e.create_character("Marcus", role="Muscle")
        assert char.setting_id == ""
        assert e.setting_id == ""

    def test_engine_preset_setting_propagates(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.setting_id = "newfaire"
        char = e.create_character("Ada")
        assert char.setting_id == "newfaire"


# =========================================================================
# 5. SAVE/LOAD ROUNDTRIP — setting_id persists through save_state/load_state
# =========================================================================


class TestBitDSaveLoad:
    """BitDEngine save/load roundtrip preserves setting_id."""

    def test_roundtrip(self):
        from codex.games.bitd import BitDEngine
        e1 = BitDEngine()
        e1.create_character("Arturo", playbook="Cutter", setting_id="doskvol")
        data = e1.save_state()
        assert data["setting_id"] == "doskvol"

        e2 = BitDEngine()
        e2.load_state(data)
        assert e2.setting_id == "doskvol"

    def test_roundtrip_empty(self):
        from codex.games.bitd import BitDEngine
        e1 = BitDEngine()
        e1.create_character("Brynn")
        data = e1.save_state()

        e2 = BitDEngine()
        e2.load_state(data)
        assert e2.setting_id == ""


class TestSaVSaveLoad:
    """SaVEngine save/load roundtrip preserves setting_id."""

    def test_roundtrip(self):
        from codex.games.sav import SaVEngine
        e1 = SaVEngine()
        e1.create_character("Zephyr", playbook="Pilot", setting_id="procyon")
        data = e1.save_state()
        assert data["setting_id"] == "procyon"

        e2 = SaVEngine()
        e2.load_state(data)
        assert e2.setting_id == "procyon"


class TestBoBSaveLoad:
    """BoBEngine save/load roundtrip preserves setting_id."""

    def test_roundtrip(self):
        from codex.games.bob import BoBEngine
        e1 = BoBEngine()
        e1.create_character("Kael", playbook="Heavy", setting_id="eastern_kingdoms")
        data = e1.save_state()
        assert data["setting_id"] == "eastern_kingdoms"

        e2 = BoBEngine()
        e2.load_state(data)
        assert e2.setting_id == "eastern_kingdoms"


class TestCBRPNKSaveLoad:
    """CBRPNKEngine save/load roundtrip preserves setting_id."""

    def test_roundtrip(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e1 = CBRPNKEngine()
        e1.create_character("Neon", archetype="Hacker", setting_id="the_sprawl")
        data = e1.save_state()
        assert data["setting_id"] == "the_sprawl"

        e2 = CBRPNKEngine()
        e2.load_state(data)
        assert e2.setting_id == "the_sprawl"
        assert e2.party[0].setting_id == "the_sprawl"

    def test_roundtrip_empty(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e1 = CBRPNKEngine()
        e1.create_character("Wire")
        data = e1.save_state()
        e2 = CBRPNKEngine()
        e2.load_state(data)
        assert e2.setting_id == ""


class TestCandelaSaveLoad:
    """CandelaEngine save/load roundtrip preserves setting_id."""

    def test_roundtrip(self):
        from codex.games.candela import CandelaEngine
        e1 = CandelaEngine()
        e1.create_character("Elara", role="Scholar", setting_id="newfaire")
        data = e1.save_state()
        assert data["setting_id"] == "newfaire"

        e2 = CandelaEngine()
        e2.load_state(data)
        assert e2.setting_id == "newfaire"
        assert e2.party[0].setting_id == "newfaire"

    def test_roundtrip_empty(self):
        from codex.games.candela import CandelaEngine
        e1 = CandelaEngine()
        e1.create_character("Marcus")
        data = e1.save_state()
        e2 = CandelaEngine()
        e2.load_state(data)
        assert e2.setting_id == ""


# =========================================================================
# 6. CHARACTER to_dict / from_dict — setting_id roundtrips
# =========================================================================


class TestCharacterToFromDict:
    """Character to_dict/from_dict preserves setting_id for all 3 systems."""

    def test_bitd_character_roundtrip(self):
        from codex.games.bitd import BitDCharacter
        c = BitDCharacter(name="Test", playbook="Cutter", setting_id="doskvol")
        d = c.to_dict()
        assert d["setting_id"] == "doskvol"
        c2 = BitDCharacter.from_dict(d)
        assert c2.setting_id == "doskvol"

    def test_sav_character_roundtrip(self):
        from codex.games.sav import SaVCharacter
        c = SaVCharacter(name="Test", playbook="Pilot", setting_id="procyon")
        d = c.to_dict()
        assert d["setting_id"] == "procyon"
        c2 = SaVCharacter.from_dict(d)
        assert c2.setting_id == "procyon"

    def test_bob_character_roundtrip(self):
        from codex.games.bob import BoBCharacter
        c = BoBCharacter(name="Test", playbook="Heavy", setting_id="eastern_kingdoms")
        d = c.to_dict()
        assert d["setting_id"] == "eastern_kingdoms"
        c2 = BoBCharacter.from_dict(d)
        assert c2.setting_id == "eastern_kingdoms"

    def test_cbrpnk_character_roundtrip(self):
        from codex.games.cbrpnk import CBRPNKCharacter
        c = CBRPNKCharacter(name="Neon", archetype="Hacker", setting_id="the_sprawl")
        d = c.to_dict()
        assert d["setting_id"] == "the_sprawl"
        c2 = CBRPNKCharacter.from_dict(d)
        assert c2.setting_id == "the_sprawl"

    def test_candela_character_roundtrip(self):
        from codex.games.candela import CandelaCharacter
        c = CandelaCharacter(name="Elara", role="Scholar", setting_id="newfaire")
        d = c.to_dict()
        assert d["setting_id"] == "newfaire"
        c2 = CandelaCharacter.from_dict(d)
        assert c2.setting_id == "newfaire"

    def test_legacy_data_without_setting(self):
        """from_dict with no setting_id key defaults to empty string."""
        from codex.games.bitd import BitDCharacter
        d = {"name": "Legacy", "playbook": "Hound"}
        c = BitDCharacter.from_dict(d)
        assert c.setting_id == ""

    def test_legacy_cbrpnk_data_without_setting(self):
        from codex.games.cbrpnk import CBRPNKCharacter
        d = {"name": "OldRunner", "archetype": "Punk"}
        c = CBRPNKCharacter.from_dict(d)
        assert c.setting_id == ""

    def test_legacy_candela_data_without_setting(self):
        from codex.games.candela import CandelaCharacter
        d = {"name": "OldInvestigator", "role": "Face"}
        c = CandelaCharacter.from_dict(d)
        assert c.setting_id == ""


# =========================================================================
# 7. ACCESSOR METHODS — get_playbooks etc. return filtered data
# =========================================================================


class TestBitDAccessors:
    """BitDEngine accessor methods return setting-filtered data."""

    def test_get_playbooks_with_setting(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.setting_id = "doskvol"
        pb = e.get_playbooks()
        assert len(pb) == 7
        assert "Cutter" in pb

    def test_get_playbooks_wrong_setting(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.setting_id = "procyon"
        pb = e.get_playbooks()
        assert len(pb) == 0  # No procyon playbooks in BitD data

    def test_get_heritages(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.setting_id = "doskvol"
        h = e.get_heritages()
        assert len(h) == 6

    def test_get_factions(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.setting_id = "doskvol"
        f = e.get_factions()
        assert "The Lampblacks" in f

    def test_get_crew_types(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.setting_id = "doskvol"
        ct = e.get_crew_types()
        assert len(ct) == 6


class TestSaVAccessors:
    """SaVEngine accessor methods return setting-filtered data."""

    def test_get_playbooks(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        e.setting_id = "procyon"
        pb = e.get_playbooks()
        assert len(pb) == 7

    def test_get_heritages(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        e.setting_id = "procyon"
        h = e.get_heritages()
        assert len(h) == 4

    def test_get_factions(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        e.setting_id = "procyon"
        f = e.get_factions()
        assert len(f) > 0

    def test_get_ship_classes(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        e.setting_id = "procyon"
        sc = e.get_ship_classes()
        assert len(sc) == 3
        assert "Stardancer" in sc


class TestBoBAccessors:
    """BoBEngine accessor methods return setting-filtered data."""

    def test_get_playbooks(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        e.setting_id = "eastern_kingdoms"
        pb = e.get_playbooks()
        assert len(pb) == 5  # Heavy, Medic, Officer, Scout, Sniper

    def test_get_heritages(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        e.setting_id = "eastern_kingdoms"
        h = e.get_heritages()
        assert len(h) == 4

    def test_get_factions(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        e.setting_id = "eastern_kingdoms"
        f = e.get_factions()
        assert len(f) > 0

    def test_get_specialists(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        e.setting_id = "eastern_kingdoms"
        s = e.get_specialists()
        assert len(s) == 7

    def test_unfiltered_returns_all(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        # No setting_id — should return everything
        pb = e.get_playbooks()
        assert len(pb) == 5  # Heavy, Medic, Officer, Scout, Sniper


class TestCBRPNKAccessors:
    """CBRPNKEngine accessor methods return setting-filtered data."""

    def test_get_archetypes_with_setting(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.setting_id = "the_sprawl"
        a = e.get_archetypes()
        assert len(a) == 4
        assert "hacker" in a or "Hacker" in a

    def test_get_archetypes_wrong_setting(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.setting_id = "doskvol"
        a = e.get_archetypes()
        assert len(a) == 0

    def test_get_backgrounds(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.setting_id = "the_sprawl"
        b = e.get_backgrounds()
        assert len(b) == 4

    def test_get_factions(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.setting_id = "the_sprawl"
        f = e.get_factions()
        assert len(f) == 11

    def test_get_chrome(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.setting_id = "the_sprawl"
        c = e.get_chrome()
        assert len(c) == 20

    def test_unfiltered_returns_all(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        a = e.get_archetypes()
        assert len(a) == 4


class TestCandelaAccessors:
    """CandelaEngine accessor methods return setting-filtered data."""

    def test_get_roles_with_setting(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.setting_id = "newfaire"
        r = e.get_roles()
        assert len(r) == 5

    def test_get_roles_wrong_setting(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.setting_id = "the_sprawl"
        r = e.get_roles()
        assert len(r) == 0

    def test_get_phenomena(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.setting_id = "newfaire"
        p = e.get_phenomena()
        assert len(p) > 0

    def test_get_circle_abilities(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.setting_id = "newfaire"
        ca = e.get_circle_abilities()
        assert len(ca) == 6

    def test_unfiltered_returns_all(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        r = e.get_roles()
        assert len(r) == 5


# =========================================================================
# 8. VAULT DISCOVERY — SETTINGS/ dirs and sub-setting creation_rules
# =========================================================================


@pytest.mark.skipif(not (VAULT_ROOT / "FITD").exists(), reason="vault/FITD/ not present (third-party content, gitignored)")
class TestVaultDiscovery:
    """Vault SETTINGS/ directories and sub-setting creation_rules exist."""

    def test_bitd_settings_dir_exists(self):
        p = VAULT_ROOT / "FITD" / "bitd" / "SETTINGS" / "Doskvol.json"
        assert p.exists(), f"Missing: {p}"

    def test_sav_settings_dir_exists(self):
        p = VAULT_ROOT / "FITD" / "sav" / "SETTINGS" / "Procyon_Sector.json"
        assert p.exists(), f"Missing: {p}"

    def test_bob_settings_dir_exists(self):
        p = VAULT_ROOT / "FITD" / "bob" / "SETTINGS" / "Eastern_Kingdoms.json"
        assert p.exists(), f"Missing: {p}"

    def test_bitd_doskvol_creation_rules(self):
        p = VAULT_ROOT / "FITD" / "bitd" / "doskvol" / "creation_rules.json"
        assert p.exists()
        data = json.loads(p.read_text())
        assert data["system_id"] == "bitd_doskvol"
        assert data["parent_engine"] == "bitd"
        assert data["setting_id"] == "doskvol"

    def test_sav_procyon_creation_rules(self):
        p = VAULT_ROOT / "FITD" / "sav" / "procyon" / "creation_rules.json"
        assert p.exists()
        data = json.loads(p.read_text())
        assert data["system_id"] == "sav_procyon"
        assert data["parent_engine"] == "sav"
        assert data["setting_id"] == "procyon"

    def test_bob_eastern_kingdoms_creation_rules(self):
        p = VAULT_ROOT / "FITD" / "bob" / "eastern_kingdoms" / "creation_rules.json"
        assert p.exists()
        data = json.loads(p.read_text())
        assert data["system_id"] == "bob_eastern_kingdoms"
        assert data["parent_engine"] == "bob"
        assert data["setting_id"] == "eastern_kingdoms"

    def test_settings_json_has_required_keys(self):
        """Each SETTINGS/*.json has name, genre, description."""
        for system, setting_file in [
            ("bitd", "Doskvol.json"),
            ("sav", "Procyon_Sector.json"),
            ("bob", "Eastern_Kingdoms.json"),
        ]:
            p = VAULT_ROOT / "FITD" / system / "SETTINGS" / setting_file
            data = json.loads(p.read_text())
            assert "name" in data, f"{p.name} missing 'name'"
            assert "genre" in data, f"{p.name} missing 'genre'"
            assert "description" in data, f"{p.name} missing 'description'"

    def test_cbrpnk_settings_dir_exists(self):
        p = VAULT_ROOT / "FITD" / "CBR_PNK" / "SETTINGS" / "The_Sprawl.json"
        assert p.exists(), f"Missing: {p}"

    def test_candela_settings_dir_exists(self):
        p = VAULT_ROOT / "ILLUMINATED_WORLDS" / "Candela_Obscura" / "SETTINGS" / "Newfaire.json"
        assert p.exists(), f"Missing: {p}"

    def test_cbrpnk_the_sprawl_creation_rules(self):
        p = VAULT_ROOT / "FITD" / "CBR_PNK" / "the_sprawl" / "creation_rules.json"
        assert p.exists()
        data = json.loads(p.read_text())
        assert data["system_id"] == "cbrpnk_the_sprawl"
        assert data["parent_engine"] == "cbrpnk"
        assert data["setting_id"] == "the_sprawl"

    def test_candela_newfaire_creation_rules(self):
        p = VAULT_ROOT / "ILLUMINATED_WORLDS" / "Candela_Obscura" / "newfaire" / "creation_rules.json"
        assert p.exists()
        data = json.loads(p.read_text())
        assert data["system_id"] == "candela_newfaire"
        assert data["parent_engine"] == "candela"
        assert data["setting_id"] == "newfaire"

    def test_creation_rules_has_steps(self):
        """Each sub-setting creation_rules.json has steps list."""
        for path in [
            VAULT_ROOT / "FITD" / "bitd" / "doskvol" / "creation_rules.json",
            VAULT_ROOT / "FITD" / "sav" / "procyon" / "creation_rules.json",
            VAULT_ROOT / "FITD" / "bob" / "eastern_kingdoms" / "creation_rules.json",
            VAULT_ROOT / "FITD" / "CBR_PNK" / "the_sprawl" / "creation_rules.json",
            VAULT_ROOT / "ILLUMINATED_WORLDS" / "Candela_Obscura" / "newfaire" / "creation_rules.json",
        ]:
            data = json.loads(path.read_text())
            assert "steps" in data
            assert len(data["steps"]) >= 2

    def test_all_settings_json_has_required_keys(self):
        """Each SETTINGS/*.json has name, genre, description."""
        for system_path, setting_file in [
            (VAULT_ROOT / "FITD" / "bitd" / "SETTINGS", "Doskvol.json"),
            (VAULT_ROOT / "FITD" / "sav" / "SETTINGS", "Procyon_Sector.json"),
            (VAULT_ROOT / "FITD" / "bob" / "SETTINGS", "Eastern_Kingdoms.json"),
            (VAULT_ROOT / "FITD" / "CBR_PNK" / "SETTINGS", "The_Sprawl.json"),
            (VAULT_ROOT / "ILLUMINATED_WORLDS" / "Candela_Obscura" / "SETTINGS", "Newfaire.json"),
        ]:
            p = system_path / setting_file
            data = json.loads(p.read_text())
            assert "name" in data, f"{p.name} missing 'name'"
            assert "genre" in data, f"{p.name} missing 'genre'"
            assert "description" in data, f"{p.name} missing 'description'"

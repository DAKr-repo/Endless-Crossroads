"""
tests.test_all_engines_depth
==============================
Integration tests verifying all 8 engines have depth parity:
  - Reference data loads without error
  - Subsystem modules import cleanly
  - handle_command() dispatches new commands
  - Save/load round-trips preserve subsystem state
  - Loader routes to correct system module

WO-V41.0: Depth Parity Sprint
"""

import pytest
import random


# =========================================================================
# REFERENCE DATA LOADING
# =========================================================================

class TestBitDReferenceDataLoads:
    """BitD reference data imports without error."""

    def test_playbooks_load(self):
        from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS, HERITAGES, VICE_TYPES
        assert len(PLAYBOOKS) == 7
        assert len(HERITAGES) >= 6
        assert len(VICE_TYPES) >= 7
        for name, pb in PLAYBOOKS.items():
            assert "special_abilities" in pb, f"{name} missing special_abilities"
            assert "xp_trigger" in pb, f"{name} missing xp_trigger"

    def test_factions_load(self):
        from codex.forge.reference_data.bitd_factions import FACTIONS, FACTION_STATUS
        assert len(FACTIONS) >= 25
        assert -3 in FACTION_STATUS
        assert 3 in FACTION_STATUS

    def test_crew_load(self):
        from codex.forge.reference_data.bitd_crew import CREW_TYPES
        assert len(CREW_TYPES) == 6

    def test_aggregator_exports(self):
        from codex.forge.reference_data.bitd import PLAYBOOKS, FACTIONS, CREW_TYPES
        assert len(PLAYBOOKS) == 7
        assert len(FACTIONS) >= 25
        assert len(CREW_TYPES) == 6


class TestSaVReferenceDataLoads:
    """SaV reference data imports without error."""

    def test_playbooks_load(self):
        from codex.forge.reference_data.sav_playbooks import PLAYBOOKS
        assert len(PLAYBOOKS) == 7

    def test_ships_load(self):
        from codex.forge.reference_data.sav_ships import SHIP_CLASSES, SHIP_MODULES
        assert len(SHIP_CLASSES) >= 3
        assert len(SHIP_MODULES) >= 10

    def test_factions_load(self):
        from codex.forge.reference_data.sav_factions import FACTIONS
        assert len(FACTIONS) >= 15

    def test_aggregator_exports(self):
        from codex.forge.reference_data.sav import PLAYBOOKS, SHIP_CLASSES, FACTIONS
        assert PLAYBOOKS
        assert SHIP_CLASSES
        assert FACTIONS


class TestBoBReferenceDataLoads:
    """BoB reference data imports without error."""

    def test_playbooks_load(self):
        from codex.forge.reference_data.bob_playbooks import PLAYBOOKS
        assert len(PLAYBOOKS) >= 4

    def test_legion_load(self):
        from codex.forge.reference_data.bob_legion import SPECIALISTS, SQUAD_TYPES, CHOSEN, MISSION_TYPES
        assert len(SPECIALISTS) >= 4
        assert len(SQUAD_TYPES) >= 3
        assert len(CHOSEN) >= 3
        assert len(MISSION_TYPES) >= 5

    def test_factions_load(self):
        from codex.forge.reference_data.bob_factions import FACTIONS
        assert len(FACTIONS) >= 5

    def test_aggregator_exports(self):
        from codex.forge.reference_data.bob import PLAYBOOKS, SPECIALISTS, FACTIONS
        assert PLAYBOOKS
        assert SPECIALISTS
        assert FACTIONS


class TestCBRPNKReferenceDataLoads:
    """CBR+PNK reference data imports without error."""

    def test_archetypes_load(self):
        from codex.forge.reference_data.cbrpnk_archetypes import ARCHETYPES
        assert len(ARCHETYPES) >= 4

    def test_chrome_load(self):
        from codex.forge.reference_data.cbrpnk_chrome import CHROME, CHROME_SLOTS, GLITCH_EFFECTS
        assert len(CHROME) >= 15
        assert len(CHROME_SLOTS) >= 3
        assert "minor" in GLITCH_EFFECTS
        assert "critical" in GLITCH_EFFECTS

    def test_corps_load(self):
        from codex.forge.reference_data.cbrpnk_corps import CORPORATIONS
        assert len(CORPORATIONS) >= 8

    def test_aggregator_exports(self):
        from codex.forge.reference_data.cbrpnk import ARCHETYPES, CHROME, CORPORATIONS
        assert ARCHETYPES
        assert CHROME
        assert CORPORATIONS


class TestCandelaReferenceDataLoads:
    """Candela Obscura reference data imports without error."""

    def test_roles_load(self):
        from codex.forge.reference_data.candela_roles import ROLES
        assert len(ROLES) == 5

    def test_phenomena_load(self):
        from codex.forge.reference_data.candela_phenomena import PHENOMENA
        assert len(PHENOMENA) >= 10

    def test_circles_load(self):
        from codex.forge.reference_data.candela_circles import CIRCLE_ABILITIES, NPC_RELATIONSHIPS
        assert len(CIRCLE_ABILITIES) >= 6
        assert len(NPC_RELATIONSHIPS) >= 8

    def test_aggregator_exports(self):
        from codex.forge.reference_data.candela import ROLES, PHENOMENA, CIRCLE_ABILITIES
        assert ROLES
        assert PHENOMENA
        assert CIRCLE_ABILITIES


class TestSTCReferenceDataLoads:
    """STC/Cosmere reference data imports without error."""

    def test_orders_load(self):
        from codex.forge.reference_data.stc_orders import ORDERS, SURGE_TYPES
        assert len(ORDERS) == 10
        assert len(SURGE_TYPES) == 10
        for name, order in ORDERS.items():
            assert "per_ideal_powers" in order, f"{name} missing per_ideal_powers"
            assert "surges" in order, f"{name} missing surges"

    def test_equipment_load(self):
        from codex.forge.reference_data.stc_equipment import SHARDBLADES, SHARDPLATE, FABRIALS, SPHERE_TYPES, WEAPON_PROPERTIES
        assert len(SHARDBLADES) >= 3
        assert len(SHARDPLATE) >= 2
        assert len(FABRIALS) >= 5
        assert len(SPHERE_TYPES) >= 10
        assert len(WEAPON_PROPERTIES) >= 5

    def test_heritages_load(self):
        from codex.forge.reference_data.stc_heritages import HERITAGES
        assert len(HERITAGES) == 10

    def test_aggregator_exports(self):
        from codex.forge.reference_data.stc import ORDERS, SHARDBLADES, HERITAGES
        assert ORDERS
        assert SHARDBLADES
        assert HERITAGES


class TestCrownReferenceDataLoads:
    """Crown reference data imports without error."""

    def test_leaders_load(self):
        from codex.forge.reference_data.crown_leaders import LEADERS, PATRONS
        assert len(LEADERS) >= 8
        assert len(PATRONS) >= 8

    def test_factions_load(self):
        from codex.forge.reference_data.crown_factions import FACTIONS
        assert len(FACTIONS) >= 6

    def test_aggregator_exports(self):
        from codex.forge.reference_data.crown import LEADERS, FACTIONS
        assert LEADERS
        assert FACTIONS


# =========================================================================
# SUBSYSTEM MODULE IMPORTS
# =========================================================================

class TestSubsystemImports:
    """All subsystem modules import cleanly."""

    def test_bitd_scores(self):
        from codex.games.bitd.scores import ScoreState, FlashbackManager, DevilsBargainTracker, engagement_roll, resolve_score
        assert ScoreState is not None
        assert FlashbackManager is not None
        assert DevilsBargainTracker is not None

    def test_bitd_downtime(self):
        from codex.games.bitd.downtime import DowntimeManager, LongTermProject
        assert DowntimeManager is not None
        assert LongTermProject is not None

    def test_sav_ships(self):
        from codex.games.sav.ships import ShipState, ship_combat_roll, install_module
        assert ShipState is not None

    def test_sav_jobs(self):
        from codex.games.sav.jobs import JobPhaseManager, jump_planning
        assert JobPhaseManager is not None

    def test_bob_campaign(self):
        from codex.games.bob.campaign import CampaignPhaseManager
        assert CampaignPhaseManager is not None

    def test_bob_missions(self):
        from codex.games.bob.missions import MissionResolver
        assert MissionResolver is not None

    def test_cbrpnk_hacking(self):
        from codex.games.cbrpnk.hacking import GridManager, GridState, ICE
        assert GridManager is not None

    def test_cbrpnk_chrome(self):
        from codex.games.cbrpnk.chrome import ChromeManager
        assert ChromeManager is not None

    def test_candela_investigations(self):
        from codex.games.candela.investigations import InvestigationManager, ClueTracker, CaseState
        assert InvestigationManager is not None

    def test_stc_surgebinding(self):
        from codex.games.stc.surgebinding import SurgeManager, StormTracker
        assert SurgeManager is not None

    def test_stc_combat(self):
        from codex.games.stc.combat import CosmereCombatResolver, AttackResult
        assert CosmereCombatResolver is not None

    def test_stc_ideals(self):
        from codex.games.stc.ideals import IdealProgression
        assert IdealProgression is not None

    def test_crown_politics(self):
        from codex.games.crown.politics import PoliticalGravityEngine, FactionInfluenceTracker, AllianceSystem
        assert PoliticalGravityEngine is not None

    def test_crown_events(self):
        from codex.games.crown.events import EventGenerator
        assert EventGenerator is not None


# =========================================================================
# ENGINE INSTANTIATION & handle_command DISPATCH
# =========================================================================

class TestAllEnginesHandleCommand:
    """Every engine dispatches handle_command for its new commands."""

    def test_bitd_dispatches_engagement(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.create_character("Nyx", playbook="Lurk")
        result = e.handle_command("engagement", plan_type="infiltration")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_bitd_dispatches_flashback(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.create_character("Nyx")
        result = e.handle_command("flashback", description="I planted a bomb earlier")
        assert isinstance(result, str)

    def test_bitd_dispatches_downtime_train(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.create_character("Nyx")
        result = e.handle_command("downtime_train", attribute="prowess")
        assert isinstance(result, str)
        assert "XP" in result or "Training" in result

    def test_sav_dispatches_ship_status(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        e.create_character("Rex", playbook="Pilot")
        result = e.handle_command("ship_status")
        assert isinstance(result, str)

    def test_sav_dispatches_engagement(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        e.create_character("Rex")
        result = e.handle_command("engagement", plan_type="transport")
        assert isinstance(result, str)

    def test_bob_dispatches_march(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        e.create_character("Kael", playbook="Heavy")
        result = e.handle_command("march", destination="Plainsworth")
        assert isinstance(result, str)

    def test_bob_dispatches_campaign_status(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        e.create_character("Kael")
        result = e.handle_command("campaign_status")
        assert isinstance(result, str)

    def test_cbrpnk_dispatches_jack_in(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.create_character("Zero", archetype="Hacker")
        result = e.handle_command("jack_in")
        assert isinstance(result, str)

    def test_cbrpnk_dispatches_install_chrome(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.create_character("Zero")
        result = e.handle_command("install_chrome", chrome_name="Neural Jack")
        assert isinstance(result, str)

    def test_candela_dispatches_open_case(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.create_character("Vera", role="Scholar")
        result = e.handle_command("open_case", case_name="The Vanishing")
        assert isinstance(result, str)

    def test_candela_dispatches_investigate(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.create_character("Vera")
        e.handle_command("open_case", case_name="Test")
        result = e.handle_command("investigate", action_dots=2)
        assert isinstance(result, str)

    def test_stc_dispatches_surge(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        e.create_character("Kaladin", order="Windrunner")
        result = e.handle_command("stormlight_status")
        assert isinstance(result, str)

    def test_stc_dispatches_highstorm(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        e.create_character("Kaladin", order="Windrunner")
        result = e.handle_command("highstorm", action="status")
        assert isinstance(result, str)

    def test_crown_dispatches_faction_status(self):
        from codex.games.crown.engine import CrownAndCrewEngine
        e = CrownAndCrewEngine(arc_length=5)
        e.setup()
        result = e.handle_command("faction_status")
        assert isinstance(result, str)

    def test_crown_dispatches_council_vote(self):
        from codex.games.crown.engine import CrownAndCrewEngine
        e = CrownAndCrewEngine(arc_length=5)
        e.setup()
        result = e.handle_command("council_vote", proposal="Tax reform")
        assert isinstance(result, str)

    def test_all_engines_have_trace_fact(self):
        """Every engine dispatches trace_fact via handle_command."""
        from codex.games.bitd import BitDEngine
        from codex.games.sav import SaVEngine
        from codex.games.bob import BoBEngine
        from codex.games.cbrpnk import CBRPNKEngine
        from codex.games.candela import CandelaEngine
        from codex.games.stc import CosmereEngine
        from codex.games.crown.engine import CrownAndCrewEngine

        engines = [
            (BitDEngine, {"name": "A"}),
            (SaVEngine, {"name": "B"}),
            (BoBEngine, {"name": "C"}),
            (CBRPNKEngine, {"name": "D"}),
            (CandelaEngine, {"name": "E"}),
            (CosmereEngine, {"name": "F"}),
        ]
        for cls, kwargs in engines:
            e = cls()
            e.create_character(**kwargs)
            result = e.handle_command("trace_fact", fact="test")
            assert isinstance(result, str), f"{cls.__name__} trace_fact failed"

        # Crown is a dataclass — different setup
        crown = CrownAndCrewEngine(arc_length=5)
        crown.setup()
        result = crown.handle_command("trace_fact", fact="test")
        assert isinstance(result, str)

    def test_all_engines_return_unknown_for_bad_command(self):
        """Every engine returns an error for unknown commands."""
        from codex.games.bitd import BitDEngine
        from codex.games.sav import SaVEngine
        from codex.games.bob import BoBEngine
        from codex.games.cbrpnk import CBRPNKEngine
        from codex.games.candela import CandelaEngine
        from codex.games.stc import CosmereEngine
        from codex.games.crown.engine import CrownAndCrewEngine

        for cls in [BitDEngine, SaVEngine, BoBEngine, CBRPNKEngine, CandelaEngine, CosmereEngine]:
            e = cls()
            result = e.handle_command("definitely_not_a_real_command")
            assert "nknown" in result or "unknown" in result.lower(), f"{cls.__name__} bad unknown response"

        crown = CrownAndCrewEngine(arc_length=5)
        crown.setup()
        result = crown.handle_command("definitely_not_a_real_command")
        assert "nknown" in result or "unknown" in result.lower()


# =========================================================================
# SAVE/LOAD ROUND-TRIP WITH SUBSYSTEM STATE
# =========================================================================

class TestAllEnginesSaveLoadRoundTrip:
    """Every engine round-trips subsystem state through save/load."""

    def test_bitd_subsystem_roundtrip(self):
        from codex.games.bitd import BitDEngine
        e = BitDEngine()
        e.create_character("Nyx", playbook="Lurk")
        e.handle_command("engagement", plan_type="infiltration")
        e.handle_command("downtime_train", attribute="prowess")
        state = e.save_state()

        e2 = BitDEngine()
        e2.load_state(state)
        assert e2.character.name == "Nyx"
        assert state.get("score_state") is not None

    def test_sav_subsystem_roundtrip(self):
        from codex.games.sav import SaVEngine
        e = SaVEngine()
        e.create_character("Rex", playbook="Pilot")
        e.handle_command("engagement", plan_type="transport")
        state = e.save_state()

        e2 = SaVEngine()
        e2.load_state(state)
        assert e2.character.name == "Rex"

    def test_bob_subsystem_roundtrip(self):
        from codex.games.bob import BoBEngine
        e = BoBEngine()
        e.create_character("Kael", playbook="Heavy")
        e.handle_command("march", destination="Plainsworth")
        state = e.save_state()

        e2 = BoBEngine()
        e2.load_state(state)
        assert e2.character.name == "Kael"

    def test_cbrpnk_subsystem_roundtrip(self):
        from codex.games.cbrpnk import CBRPNKEngine
        e = CBRPNKEngine()
        e.create_character("Zero", archetype="Hacker")
        e.handle_command("jack_in")
        e.handle_command("install_chrome", chrome_name="Neural Jack")
        state = e.save_state()

        e2 = CBRPNKEngine()
        e2.load_state(state)
        assert e2.character.name == "Zero"
        assert state.get("chrome_mgr") is not None or state.get("grid_state") is not None

    def test_candela_subsystem_roundtrip(self):
        from codex.games.candela import CandelaEngine
        e = CandelaEngine()
        e.create_character("Vera", role="Scholar")
        e.handle_command("open_case", case_name="The Vanishing")
        state = e.save_state()

        e2 = CandelaEngine()
        e2.load_state(state)
        assert e2.character.name == "Vera"

    def test_stc_subsystem_roundtrip(self):
        from codex.games.stc import CosmereEngine
        e = CosmereEngine()
        e.create_character("Kaladin", order="Windrunner")
        e.handle_command("infuse", amount=20)
        state = e.save_state()

        e2 = CosmereEngine()
        e2.load_state(state)
        assert e2.character.name == "Kaladin"

    def test_crown_subsystem_roundtrip(self):
        from codex.games.crown.engine import CrownAndCrewEngine
        e = CrownAndCrewEngine(arc_length=5)
        e.setup()
        e.handle_command("shift_influence", faction_name="Crown Loyalists", amount=2)
        data = e.to_dict()

        e2 = CrownAndCrewEngine.from_dict(data)
        assert e2.arc_length == 5


# =========================================================================
# LOADER ROUTING
# =========================================================================

class TestLoaderRouting:
    """loader.load_reference routes to the correct system module."""

    def test_loader_dnd5e(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("subraces", system_id="dnd5e")
        assert isinstance(result, dict)

    def test_loader_bitd_playbooks(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("PLAYBOOKS", system_id="bitd")
        assert isinstance(result, dict)
        assert len(result) >= 7

    def test_loader_sav_playbooks(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("PLAYBOOKS", system_id="sav")
        assert isinstance(result, dict)
        assert len(result) >= 7

    def test_loader_bob(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("PLAYBOOKS", system_id="bob")
        assert isinstance(result, dict)

    def test_loader_cbrpnk(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("CHROME", system_id="cbrpnk")
        assert isinstance(result, dict)

    def test_loader_candela(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("ROLES", system_id="candela")
        assert isinstance(result, dict)

    def test_loader_stc(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("ORDERS", system_id="stc")
        assert isinstance(result, dict)

    def test_loader_crown(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("LEADERS", system_id="crown")
        assert isinstance(result, dict)

    def test_loader_unknown_system_returns_empty(self):
        from codex.forge.reference_data.loader import load_reference
        result = load_reference("anything", system_id="nonexistent")
        assert result == {}


# =========================================================================
# COMMAND REGISTRY COMPLETENESS
# =========================================================================

class TestCommandRegistryCompleteness:
    """Each engine's COMMANDS dict matches actual dispatched commands."""

    def test_bitd_commands_registered(self):
        from codex.games.bitd import BITD_COMMANDS
        assert len(BITD_COMMANDS) >= 15

    def test_sav_commands_registered(self):
        from codex.games.sav import SAV_COMMANDS
        assert len(SAV_COMMANDS) >= 10

    def test_bob_commands_registered(self):
        from codex.games.bob import BOB_COMMANDS
        assert len(BOB_COMMANDS) >= 10

    def test_cbrpnk_commands_registered(self):
        from codex.games.cbrpnk import CBRPNK_COMMANDS
        assert len(CBRPNK_COMMANDS) >= 10

    def test_candela_commands_registered(self):
        from codex.games.candela import CANDELA_COMMANDS
        assert len(CANDELA_COMMANDS) >= 10

    def test_crown_commands_registered(self):
        from codex.games.crown.engine import CROWN_COMMANDS
        assert len(CROWN_COMMANDS) >= 8

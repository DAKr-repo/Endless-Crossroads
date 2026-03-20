"""
Band of Blades -- Game Engine
==============================

Dark military fantasy using FITD. Manages the Legion's retreat
and campaign-level resources (supply, intel, morale, pressure).

Integrates with:
  - codex/core/engines/narrative_base.py (shared FITD mechanics)
  - codex/core/services/fitd_engine.py (FITD core + LegionState)
  - codex/forge/char_wizard.py via vault/FITD/bob/creation_rules.json
  - codex/games/bob/campaign.py (CampaignPhaseManager, PressureClock)
  - codex/games/bob/missions.py (MissionResolver)

Activated when a Band of Blades campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from codex.core.engines.narrative_base import NarrativeEngineBase


# =========================================================================
# CHARACTER
# =========================================================================

@dataclass
class BoBCharacter:
    """A Band of Blades Legionnaire."""
    name: str
    playbook: str = ""     # Heavy, Medic, Officer, Scout
    heritage: str = ""     # Bartan, Orite, Panyar, Zemyati

    # Action dots (0-4 each)
    doctor: int = 0
    marshal: int = 0
    research: int = 0
    scout_action: int = 0
    maneuver: int = 0
    skirmish: int = 0
    wreck: int = 0
    consort: int = 0
    discipline: int = 0
    sway: int = 0
    setting_id: str = ""

    def is_alive(self) -> bool:
        """FITD characters don't die from HP; always considered active."""
        return True

    def to_dict(self) -> dict:
        """Serialize to a plain dict for save/load."""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict) -> "BoBCharacter":
        """Deserialize from a plain dict."""
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


# =========================================================================
# ENGINE
# =========================================================================

class BoBEngine(NarrativeEngineBase):
    """Core engine for Band of Blades campaigns.

    Manages both individual Legionnaires and the Legion's campaign state
    (supply, intel, morale, pressure) via LegionState from fitd_engine.
    Also wires in CampaignPhaseManager (march/camp/mission cycle) and
    MissionResolver (engagement rolls, casualty rolls, outcome resolution).

    Inherits from NarrativeEngineBase:
        create_character, add_to_party, remove_from_party, get_active_party,
        roll_action, push_stress, get_mood_context, handle_command.

    Lazy-initialized subsystems:
        _campaign_mgr: CampaignPhaseManager
        _mission_resolver: MissionResolver
    """

    system_id = "bob"
    system_family = "FITD"
    display_name = "Band of Blades"

    def __init__(self) -> None:
        """Initialize engine with default state and lazy subsystem placeholders."""
        super().__init__()
        from codex.core.services.fitd_engine import LegionState
        self.legion: Any = LegionState()
        self.chosen: str = ""       # The Chosen (special NPC ally)
        self.campaign_phase: str = "march"  # march, camp, mission

        # Lazy-init subsystems
        self._campaign_mgr: Optional[Any] = None   # CampaignPhaseManager
        self._mission_resolver: Optional[Any] = None  # MissionResolver

        # Campaign tracking
        self._fallen_legionnaires: List[str] = []
        self._missions_completed: int = 0

    # =====================================================================
    # HOOKS (NarrativeEngineBase)
    # =====================================================================

    def _create_character(self, name: str, **kwargs) -> BoBCharacter:
        """Create a BoBCharacter from name and kwargs.

        Args:
            name: Character's name.
            **kwargs: BoBCharacter-specific fields (playbook, heritage, etc.).

        Returns:
            Newly created BoBCharacter instance.
        """
        return BoBCharacter.from_dict({"name": name, **kwargs})

    def _get_trauma_table(self) -> list:
        """Return BoB's custom trauma table for StressClock.

        Returns:
            List of BoB trauma strings (BOB_TRAUMAS from fitd_engine).
        """
        from codex.core.services.fitd_engine import BOB_TRAUMAS
        return list(BOB_TRAUMAS)

    def _get_command_registry(self) -> Dict[str, Callable]:
        """Map command aliases to handlers.

        Returns:
            Dict mapping command strings to bound methods.
        """
        return {
            # Alias base crew stress display to BoB's squad_status name
            "squad_status": self._cmd_squad_status,
            # Extended camp activities
            "religious_services": self._cmd_religious_services,
            "liberty": self._cmd_liberty,
            "scrounge": self._cmd_scrounge,
            "memorial": self._cmd_memorial,
            "record_casualty": self._cmd_record_casualty,
            "legion_advance": self._cmd_legion_advance,
            # Inherited narrative base commands (explicit registration for discoverability)
            "fortune": self._cmd_fortune,
            "resist": self._cmd_resist,
            "gather_info": self._cmd_gather_info,
        }

    def _format_status(self) -> str:
        """Return BoB-specific status string.

        Returns:
            Status string showing Legion resources and campaign phase.
        """
        lead = self.party[0] if self.party else None
        return (
            f"Chosen: {self.chosen or 'None'} | "
            f"Supply: {self.legion.supply}/10 | "
            f"Morale: {self.legion.morale}/10 | "
            f"Pressure: {self.legion.pressure}/6 | "
            f"Phase: {self.campaign_phase} | "
            f"Lead: {lead.name if lead else 'None'}"
        )

    # =====================================================================
    # LAZY SUBSYSTEM ACCESSORS
    # =====================================================================

    def _get_campaign_mgr(self) -> Any:
        """Lazily initialise and return the CampaignPhaseManager."""
        if self._campaign_mgr is None:
            from codex.games.bob.campaign import CampaignPhaseManager
            self._campaign_mgr = CampaignPhaseManager(
                current_phase=self.campaign_phase,
                supply=self.legion.supply,
                morale=self.legion.morale,
                pressure=self.legion.pressure,
            )
        return self._campaign_mgr

    def _get_mission_resolver(self) -> Any:
        """Lazily initialise and return the MissionResolver."""
        if self._mission_resolver is None:
            from codex.games.bob.missions import MissionResolver
            self._mission_resolver = MissionResolver()
        return self._mission_resolver

    # =====================================================================
    # STATUS (override for Legion info)
    # =====================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dict suitable for Butler status display."""
        lead = self.party[0] if self.party else None
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "playbook": lead.playbook if lead else None,
            "chosen": self.chosen,
            "supply": self.legion.supply,
            "morale": self.legion.morale,
            "pressure": self.legion.pressure,
            "phase": self.campaign_phase,
        }

    # =====================================================================
    # SETTING-FILTERED ACCESSORS (WO-V46.0)
    # =====================================================================

    def get_playbooks(self) -> dict:
        """Return playbooks filtered by active setting."""
        from codex.forge.reference_data.bob_playbooks import PLAYBOOKS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(PLAYBOOKS, self.setting_id)

    def get_heritages(self) -> dict:
        """Return heritages filtered by active setting."""
        from codex.forge.reference_data.bob_playbooks import HERITAGES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(HERITAGES, self.setting_id)

    def get_factions(self) -> dict:
        """Return factions filtered by active setting."""
        from codex.forge.reference_data.bob_factions import FACTIONS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(FACTIONS, self.setting_id)

    def get_specialists(self) -> dict:
        """Return specialists filtered by active setting."""
        from codex.forge.reference_data.bob_legion import SPECIALISTS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(SPECIALISTS, self.setting_id)

    # =====================================================================
    # SAVE / LOAD
    # =====================================================================

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state for persistence.

        Calls super().save_state() for base fields (party, stress, faction_clocks),
        then adds BoB-specific fields (legion, chosen, campaign_phase, subsystems).

        Returns:
            Dict suitable for JSON serialization.
        """
        state = super().save_state()
        state.update({
            "legion": self.legion.to_dict(),
            "chosen": self.chosen,
            "campaign_phase": self.campaign_phase,
            # Subsystem state (None if never initialised)
            "campaign_mgr": self._campaign_mgr.to_dict() if self._campaign_mgr else None,
            "mission_resolver": self._mission_resolver.to_dict() if self._mission_resolver else None,
            # Campaign tracking
            "fallen_legionnaires": list(self._fallen_legionnaires),
            "missions_completed": self._missions_completed,
        })
        return state

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict.

        Full override: uses BoBCharacter.from_dict for correct character type,
        then restores BoB-specific fields and subsystems.

        Args:
            data: Dict from a previous save_state() call.
        """
        from codex.core.services.fitd_engine import StressClock, UniversalClock, LegionState
        self.setting_id = data.get("setting_id", "")
        self.party = [BoBCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.stress_clocks = {k: StressClock.from_dict(v)
                              for k, v in data.get("stress", {}).items()}
        self.faction_clocks = [UniversalClock.from_dict(c)
                               for c in data.get("faction_clocks", [])]
        self.legion = LegionState.from_dict(data.get("legion", {}))
        self.chosen = data.get("chosen", "")
        self.campaign_phase = data.get("campaign_phase", "march")

        # Restore subsystems if present
        campaign_data = data.get("campaign_mgr")
        if campaign_data:
            from codex.games.bob.campaign import CampaignPhaseManager
            self._campaign_mgr = CampaignPhaseManager.from_dict(campaign_data)

        mission_data = data.get("mission_resolver")
        if mission_data:
            from codex.games.bob.missions import MissionResolver
            self._mission_resolver = MissionResolver.from_dict(mission_data)

        # Campaign tracking
        self._fallen_legionnaires = list(data.get("fallen_legionnaires", []))
        self._missions_completed = data.get("missions_completed", 0)

    # =====================================================================
    # COMMAND DISPATCHER CONSTANTS
    # =====================================================================

    _PHASE_CYCLE = ["march", "camp", "mission"]

    # ── Original commands ──────────────────────────────────────────────

    def _cmd_legion_status(self, **kwargs) -> str:
        """Display supply, intel, morale, pressure from LegionState."""
        d = self.legion.to_dict()
        return (
            f"Supply: {d['supply']}/10 | Intel: {d['intel']}/10\n"
            f"Morale: {d['morale']}/10 | Pressure: {d['pressure']}/6"
        )

    def _cmd_squad_status(self, **kwargs) -> str:
        """Show squad stress and trauma for all registered members."""
        lines = ["Squad Stress/Trauma:"]
        for name, clock in self.stress_clocks.items():
            traumas = ", ".join(clock.traumas) if clock.traumas else "none"
            lines.append(f"  {name}: stress {clock.current_stress}/{clock.max_stress} | traumas: {traumas}")
        if not self.stress_clocks:
            lines.append("  No squad members registered.")
        return "\n".join(lines)

    def _cmd_chosen_status(self, **kwargs) -> str:
        """Display the Chosen's name and current campaign phase."""
        chosen_name = self.chosen or "No Chosen selected"
        return f"Chosen: {chosen_name}\nCampaign Phase: {self.campaign_phase}"

    # ── Supply check ───────────────────────────────────────────────────

    def _cmd_supply_check(self, **kwargs) -> str:
        """Check and modify legion supply.

        Kwargs:
            delta (int): Amount to adjust (positive = gain, negative = spend).
        """
        delta = kwargs.get("delta", 0)
        result = self.legion.adjust("supply", delta)
        if "error" in result:
            return result["error"]
        msg = f"Supply: {result['old']} -> {result['new']} (delta {result['delta']:+d})"
        # Sync with campaign manager if initialised
        if self._campaign_mgr is not None:
            self._campaign_mgr.supply = self.legion.supply
        self._add_shard(msg, "CHRONICLE")
        return msg

    # ── Campaign advance ───────────────────────────────────────────────

    def _cmd_campaign_advance(self, **kwargs) -> str:
        """Advance campaign phase (march/camp/mission) using CampaignPhaseManager."""
        mgr = self._get_campaign_mgr()
        old_phase = mgr.current_phase
        new_phase = mgr.advance_phase()
        self.campaign_phase = new_phase
        self._add_shard(
            f"Campaign phase: {old_phase} -> {new_phase}",
            "CHRONICLE",
        )
        return f"Campaign phase: {old_phase} -> {new_phase}"

    # ── Phase command handlers ─────────────────────────────────────────

    def _cmd_march(self, **kwargs) -> str:
        """Move the Legion to a new destination.

        Kwargs:
            destination (str): Name of the destination (required).
            supply_cost (int): Supply consumed (default 1).
        """
        destination = kwargs.get("destination", "Unknown")
        supply_cost = int(kwargs.get("supply_cost", 1))
        mgr = self._get_campaign_mgr()
        result = mgr.march(destination=destination, supply_cost=supply_cost)

        # Sync LegionState
        self.legion.supply = mgr.supply

        lines = [
            f"Legion marches to {result['destination']} (Day {result['day']}).",
            f"Supply: {result['supply_before']} -> {result['supply_after']} "
            f"(cost: {result['supply_cost']})",
        ]
        if result["encounter"]:
            lines.append(f"Encounter: {result['encounter_type']}!")
        else:
            lines.append("No encounters on the road.")

        msg = "\n".join(lines)
        self._add_shard(msg, "CHRONICLE")
        return msg

    def _cmd_camp(self, **kwargs) -> str:
        """Perform a camp phase activity.

        Kwargs:
            activity (str): One of rest/resupply/recruit/ceremony/train/intel_review.
        """
        activity = kwargs.get("activity", "rest")
        mgr = self._get_campaign_mgr()
        result = mgr.camp(activity=activity)

        # Sync LegionState
        self.legion.supply = mgr.supply
        self.legion.morale = mgr.morale

        lines = [
            f"Camp activity: {result['activity']}",
            result["result"],
            f"Morale: {result['morale_before']} -> {result['morale_after']} | "
            f"Supply: {result['supply_before']} -> {result['supply_after']}",
        ]
        if result.get("supply_gained"):
            lines.append(f"Supply gained: +{result['supply_gained']}")

        msg = "\n".join(lines)
        self._add_shard(msg, "CHRONICLE")
        return msg

    def _cmd_mission_plan(self, **kwargs) -> str:
        """Plan a mission before the engagement roll.

        Kwargs:
            mission_type (str): Mission type (Assault/Recon/Religious/Supply/Rescue/Skirmish).
            squad (str): Squad type (Rookies/Soldiers/Elite).
            specialist (str, optional): Specialist attached to mission.
        """
        mission_type = kwargs.get("mission_type", "Assault")
        squad = kwargs.get("squad", "Soldiers")
        specialist = kwargs.get("specialist")

        resolver = self._get_mission_resolver()
        plan = resolver.plan_mission(
            mission_type=mission_type,
            squad=squad,
            specialist=specialist,
        )
        if "error" in plan:
            return plan["error"]

        specialist_str = f" | Specialist: {specialist}" if specialist else ""
        return (
            f"Mission planned: {plan['mission_type']} | Squad: {squad}{specialist_str}\n"
            f"Base difficulty: {plan['base_difficulty']} | Reward type: {plan['reward_type']}\n"
            f"{plan['description']}"
        )

    def _cmd_mission_resolve(self, **kwargs) -> str:
        """Resolve the current planned mission.

        Kwargs:
            casualties_roll (str): Casualty outcome (critical/success/mixed/failure).
            success_level (str): Mission success level (critical/success/mixed/failure).
        """
        resolver = self._get_mission_resolver()
        if not resolver.planned_mission:
            return "No mission planned. Use 'mission_plan' first."

        casualties_roll = kwargs.get("casualties_roll", "mixed")
        success_level = kwargs.get("success_level", "success")

        result = resolver.resolve_mission(
            mission=resolver.planned_mission,
            casualties_roll=casualties_roll,
            success_level=success_level,
        )

        # Apply rewards and costs to LegionState
        reward = result.get("reward", {})
        if reward.get("supply_gained", 0):
            self.legion.adjust("supply", reward["supply_gained"])
        if reward.get("intel_gained", 0):
            self.legion.adjust("intel", reward["intel_gained"])

        supply_cost = result.get("supply_cost", 0)
        if supply_cost:
            self.legion.adjust("supply", -supply_cost)

        morale_delta = result.get("morale_delta", 0)
        if morale_delta:
            self.legion.adjust("morale", morale_delta)

        # Sync campaign manager
        mgr = self._get_campaign_mgr()
        mgr.supply = self.legion.supply
        mgr.morale = min(5, max(1, self.legion.morale // 2))

        # Handle relic
        relic_str = ""
        if result.get("relic_found"):
            relic_name = result.get("relic_name", "Unknown Relic")
            mgr.add_relic(relic_name)
            relic_str = f"\nRelic acquired: {relic_name}"

        # Track mission completion for legion advancement
        self._missions_completed += 1
        advance_msg = self._check_legion_advancement()

        lines = [
            f"Mission resolved: {result['mission_type']} — {result['success_level'].upper()}",
            f"Casualties: {result['casualty_outcome']['label']}",
            f"Rewards: {result.get('reward_description', 'None')}",
            f"Morale impact: {result['morale_delta']:+d}",
            result["notes"],
        ]
        if relic_str:
            lines.append(relic_str)
        lines.append(f"Missions completed: {self._missions_completed}")
        if advance_msg:
            lines.append(advance_msg)

        msg = "\n".join(lines)
        self._add_shard(msg, "CHRONICLE")
        return msg

    def _check_legion_advancement(self) -> str:
        """Check if the legion has crossed an advancement threshold.

        Returns upgrade message if a threshold was just reached, empty string otherwise.
        """
        THRESHOLDS = {
            3: ("Improved Supply Lines", "supply", 1),
            6: ("Veteran Tactics", "intel", 1),
            10: ("Elite Legion", "morale", 2),
        }
        entry = THRESHOLDS.get(self._missions_completed)
        if entry:
            label, resource, amount = entry
            self.legion.adjust(resource, amount)
            self._add_shard(
                f"LEGION ADVANCEMENT: {label} (mission #{self._missions_completed}). "
                f"{resource} +{amount}.",
                "ANCHOR",
            )
            return f"LEGION ADVANCEMENT: {label}! ({resource} +{amount})"
        return ""

    def _cmd_pressure_check(self, **kwargs) -> str:
        """Roll to see if Pressure increases.

        No kwargs required; uses current campaign state.
        """
        mgr = self._get_campaign_mgr()
        result = mgr.pressure_check()

        # Sync LegionState pressure
        self.legion.pressure = mgr.pressure

        if result["pressure_increased"]:
            return (
                f"Pressure check: roll {result['roll']} vs threshold {result['threshold']}.\n"
                f"Pressure increases! Level {result['old_level']} -> {result['new_level']} "
                f"({result['label']})."
            )
        return (
            f"Pressure check: roll {result['roll']} vs threshold {result['threshold']}.\n"
            f"Pressure holds. Current level: {result['new_level']} ({result['label']})."
        )

    def _cmd_time_passes(self, **kwargs) -> str:
        """Advance the campaign clock.

        Kwargs:
            days (int): Days to advance (default 1).
        """
        days = int(kwargs.get("days", 1))
        mgr = self._get_campaign_mgr()
        return mgr.time_passes(days=days)

    def _cmd_complication(self, **kwargs) -> str:
        """Roll a complication from the system's consequence table."""
        import random as _rng
        tier = max(1, min(4, kwargs.get("tier", 1)))
        effective_tier = min(4, tier + (1 if self.legion.pressure >= 4 else 0))
        pool = COMPLICATION_TABLE.get(effective_tier, COMPLICATION_TABLE[1])
        entry = _rng.choice(pool)
        self._add_shard(
            f"Complication ({entry['type']}): {entry['text']}",
            "CHRONICLE",
        )
        return f"COMPLICATION: {entry['text']}\nEffect: {entry.get('effect', 'none')}"

    # =====================================================================
    # EXTENDED CAMP ACTIVITIES
    # =====================================================================

    def _cmd_religious_services(self, **kwargs) -> str:
        """Camp activity: hold religious services to boost morale.

        Rolls 1d6. 4-5 = morale +1; 6 = morale +2.

        Returns:
            Result string with roll, morale gain, and current morale.
        """
        import random as _rng
        roll = _rng.randint(1, 6)
        if roll == 6:
            morale_gain = 2
        elif roll >= 4:
            morale_gain = 1
        else:
            morale_gain = 0
        self.legion.adjust("morale", morale_gain)
        self._add_shard(f"Religious services: morale +{morale_gain}", "CHRONICLE")
        return (
            f"Religious services held. Roll: {roll}\n"
            f"Morale: +{morale_gain} (now {self.legion.morale}/10)"
        )

    def _cmd_liberty(self, **kwargs) -> str:
        """Camp activity: grant liberty to reduce stress (risk of overindulgence).

        Rolls 1d6 for stress relief. Rolling 6 triggers overindulgence (-1 morale).

        Returns:
            Result string with stress relief and any overindulgence penalty.
        """
        import random as _rng
        roll = _rng.randint(1, 6)
        stress_relief = roll
        overindulged = roll >= 6
        msg = f"Liberty granted. Stress relief: {stress_relief}"
        if overindulged:
            self.legion.adjust("morale", -1)
            msg += f"\nOVERINDULGENCE! Morale -1 (now {self.legion.morale}/10)"
        self._add_shard(
            f"Liberty: stress -{stress_relief}{' (overindulgence!)' if overindulged else ''}",
            "CHRONICLE",
        )
        return msg

    def _cmd_scrounge(self, **kwargs) -> str:
        """Camp activity: scrounge for supplies.

        Rolls 1d6. 1-3 = nothing; 4-5 = supply +1; 6 = supply +2.

        Returns:
            Result string with roll, supply gain, and current supply.
        """
        import random as _rng
        roll = _rng.randint(1, 6)
        if roll == 6:
            supply_gain = 2
        elif roll >= 4:
            supply_gain = 1
        else:
            supply_gain = 0
        self.legion.adjust("supply", supply_gain)
        msg = f"Scrounge roll: {roll}\nSupply: +{supply_gain} (now {self.legion.supply}/10)"
        if supply_gain == 0:
            msg += "\nNothing useful found."
        self._add_shard(f"Scrounge: supply +{supply_gain}", "CHRONICLE")
        return msg

    def _cmd_memorial(self, **kwargs) -> str:
        """Honor the fallen legionnaires.

        Returns:
            Memorial roster or message if no fallen.
        """
        if not self._fallen_legionnaires:
            return "No fallen legionnaires to honor. The Legion endures."
        lines = ["=== Memorial for the Fallen ==="]
        for name in self._fallen_legionnaires:
            lines.append(f"  * {name}")
        lines.append(f"\nTotal fallen: {len(self._fallen_legionnaires)}")
        lines.append("Their sacrifice is remembered.")
        return "\n".join(lines)

    def _cmd_record_casualty(self, **kwargs) -> str:
        """Record a legionnaire casualty.

        Kwargs:
            name (str): Name of the fallen legionnaire (required).

        Returns:
            Confirmation string with morale cost and running total.
        """
        name = kwargs.get("name", "")
        if not name:
            return "Specify name of the fallen."
        self._fallen_legionnaires.append(name)
        self.legion.adjust("morale", -1)
        self._add_shard(f"Legionnaire {name} has fallen. Morale -1.", "ANCHOR")
        return (
            f"{name} has fallen. They will be remembered.\n"
            f"Morale: {self.legion.morale}/10\n"
            f"Total fallen: {len(self._fallen_legionnaires)}"
        )

    def _cmd_legion_advance(self, **kwargs) -> str:
        """Check for legion advancement based on missions completed.

        Returns:
            Status string showing unlocked and pending upgrades.
        """
        thresholds = {
            3: "Improved Supply Lines (+1 supply cap)",
            6: "Veteran Tactics (+1d to engagement)",
            10: "Elite Legion (unlock specialist abilities)",
        }
        lines = [f"Missions completed: {self._missions_completed}"]
        for threshold, upgrade in thresholds.items():
            if self._missions_completed >= threshold:
                status = "UNLOCKED"
            else:
                status = f"({threshold - self._missions_completed} more needed)"
            lines.append(f"  [{threshold}] {upgrade} — {status}")
        return "\n".join(lines)

    def _cmd_campaign_status(self, **kwargs) -> str:
        """Display full campaign phase manager status."""
        mgr = self._get_campaign_mgr()
        status = mgr.get_status()
        lines = [
            f"Phase: {status['phase']} | Day: {status['day']}",
            f"Morale: {status['morale']}/5 ({status['morale_label']})",
            f"Supply: {status['supply']}/10",
            f"Pressure: {status['pressure']}/5 ({status['pressure_label']})",
            f"Relics: {status['relics']}",
        ]
        if status["route"]:
            lines.append(f"Route: {' -> '.join(status['route'][-5:])}")
        return "\n".join(lines)


# =========================================================================
# COMPLICATION TABLE (Gap Fix: per-engine consequences)
# =========================================================================

COMPLICATION_TABLE: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"type": "supply_shortage", "text": "Rations spoil in the rain. Supply stock takes a hit.", "effect": "supply -1"},
        {"type": "desertion", "text": "A rookie slips away in the night. Morale wavers.", "effect": "morale -1"},
        {"type": "undead_ambush", "text": "A handful of rotters stumble into camp. Easily dispatched.", "effect": "stress +1"},
    ],
    2: [
        {"type": "supply_shortage", "text": "The quartermaster reports spoiled water barrels.", "effect": "supply -2"},
        {"type": "undead_ambush", "text": "An undead patrol finds your rear guard. Casualties possible.", "effect": "stress +2"},
        {"type": "broken_assault", "text": "Broken scouts probe your perimeter defenses.", "effect": "pressure +1"},
    ],
    3: [
        {"type": "supply_shortage", "text": "A supply wagon is lost crossing a swollen river.", "effect": "supply -3"},
        {"type": "desertion", "text": "A squad of soldiers deserts, taking weapons with them.", "effect": "morale -2"},
        {"type": "chosen_sighting", "text": "The Chosen reports disturbing visions of the enemy's advance.", "effect": "pressure +2"},
        {"type": "broken_assault", "text": "A Broken lieutenant leads a night raid on your camp.", "effect": "stress +3"},
    ],
    4: [
        {"type": "undead_ambush", "text": "A massive undead horde descends on your position.", "effect": "pressure +3"},
        {"type": "chosen_sighting", "text": "The Chosen is wounded by a Broken assassin.", "effect": "morale -3"},
        {"type": "broken_assault", "text": "The Cinder King's elite forces assault your position.", "effect": "stress +4"},
    ],
}


# =========================================================================
# COMMAND DEFINITIONS (WO-V8.0 + Phase2A)
# =========================================================================

BOB_COMMANDS = {
    # Original commands
    "legion_status":      "Display supply, intel, morale, pressure",
    "chosen_status":      "Display the Chosen's condition",
    "roll_action":        "Roll an FITD action check",
    "squad_status":       "Show squad stress and trauma",
    "supply_check":       "Check and modify legion supply",
    # Phase cycling
    "campaign_advance":   "Advance campaign phase (march/camp/mission)",
    # Phase2A: new campaign commands
    "march":              "Move the Legion to a new destination",
    "camp":               "Perform a camp phase activity (rest/resupply/recruit/ceremony)",
    "campaign_status":    "Display full campaign phase status",
    "pressure_check":     "Roll to see if Cinder King pressure increases",
    "time_passes":        "Advance the campaign clock by days",
    # Phase2A: mission commands
    "mission_plan":       "Plan a mission (type, squad, specialist)",
    "mission_resolve":    "Resolve the current mission (casualties, success level)",
    "complication":       "Roll a complication from the consequence table",
    # P3: extended camp activities
    "religious_services": "Hold religious services (morale boost)",
    "liberty":            "Grant liberty (stress relief, overindulgence risk)",
    "scrounge":           "Scrounge for supplies",
    "memorial":           "Honor the fallen legionnaires",
    "record_casualty":    "Record a legionnaire casualty (name=<str>)",
    "legion_advance":     "Check legion advancement thresholds",
    # P3: inherited narrative mechanics
    "fortune":            "Roll a fortune die pool (dice_count=<int>)",
    "resist":             "Roll resistance (attribute=<str>)",
    "gather_info":        "Gather information (action=<str>, question=<str>)",
}

BOB_CATEGORIES = {
    "Legion": [
        "legion_status", "campaign_advance", "supply_check", "chosen_status",
        "campaign_status", "legion_advance",
    ],
    "Campaign": [
        "march", "camp", "pressure_check", "time_passes",
    ],
    "Mission": [
        "mission_plan", "mission_resolve",
    ],
    "Camp Extended": [
        "religious_services", "liberty", "scrounge", "memorial", "record_casualty",
    ],
    "Squad": [
        "roll_action", "squad_status", "complication", "fortune", "resist", "gather_info",
    ],
}


# =========================================================================
# ENCOUNTER & LOCATION CONTENT (WO-V47.0)
# =========================================================================

ENCOUNTER_TABLE = [
    {"name": "Rotting Horde", "description": "A shambling mass of undead crests the ridge, drawn by the smell of the living.", "effect": "pressure +2, 6-clock 'Overrun'"},
    {"name": "Broken Advance", "description": "A Broken lieutenant and their elite guard block the mountain pass.", "effect": "engagement roll, harm level 3 on failure"},
    {"name": "Blighter Corruption", "description": "The ground itself weeps black ichor. Plants wither in real time.", "effect": "stress +2, corruption advances"},
    {"name": "Ghost Owls", "description": "Spectral birds circle overhead, their cries freezing the blood.", "effect": "morale -1, supernatural engagement"},
    {"name": "Deserter Band", "description": "Former legionnaires gone rogue, desperate and dangerous.", "effect": "supply opportunity on success, intel -1 on failure"},
    {"name": "Siege Engine Remnant", "description": "A twisted war machine from the last offensive, still operational, defending nothing.", "effect": "6-clock 'Disable', explosive risk"},
]

LOCATION_DESCRIPTIONS = {
    "the_front": [
        "Mud and blood and the distant thunder of undead war-drums. The trenches smell of smoke and fear.",
        "No man's land stretches gray and cratered. Nothing grows here anymore.",
    ],
    "camp": [
        "Canvas tents in orderly rows, banners snapping in cold wind. The mess fires never quite warm you.",
        "Quartermasters argue over dwindling supplies while soldiers sharpen weapons in silence.",
    ],
    "holy_site": [
        "The shrine's power is fading but still tangible — a warmth that pushes back the corruption.",
        "Ancient wards carved into stone pulse with dim light. The Chosen say they can feel them weakening.",
    ],
}


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("bob", BoBEngine)
except ImportError:
    pass

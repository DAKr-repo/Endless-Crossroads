"""
Band of Blades -- Game Engine
==============================

Dark military fantasy using FITD. Manages the Legion's retreat
and campaign-level resources (supply, intel, morale, pressure).

Integrates with:
  - codex/core/services/fitd_engine.py (FITD core + LegionState)
  - codex/forge/char_wizard.py via vault/FITD/bob/creation_rules.json
  - codex/games/bob/campaign.py (CampaignPhaseManager, PressureClock)
  - codex/games/bob/missions.py (MissionResolver)

Activated when a Band of Blades campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from codex.core.services.narrative_loom import NarrativeLoomMixin


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

class BoBEngine(NarrativeLoomMixin):
    """Core engine for Band of Blades campaigns.

    Manages both individual Legionnaires and the Legion's campaign state
    (supply, intel, morale, pressure) via LegionState from fitd_engine.
    Also wires in CampaignPhaseManager (march/camp/mission cycle) and
    MissionResolver (engagement rolls, casualty rolls, outcome resolution).
    """

    system_id = "bob"
    system_family = "FITD"
    display_name = "Band of Blades"

    def __init__(self):
        from codex.core.services.fitd_engine import StressClock, FactionClock, LegionState  # noqa: F401
        self.character: Optional[BoBCharacter] = None
        self.party: List[BoBCharacter] = []
        self.stress_clocks: Dict[str, Any] = {}
        self.faction_clocks: List[Any] = []
        self.legion: Any = LegionState()
        self.chosen: str = ""       # The Chosen (special NPC ally)
        self.campaign_phase: str = "march"  # march, camp, mission

        # WO-Phase2A: Lazy-init subsystems
        self._campaign_mgr: Optional[Any] = None   # CampaignPhaseManager
        self._mission_resolver: Optional[Any] = None  # MissionResolver

        self._init_loom()
        self.setting_id: str = ""

    # =====================================================================
    # LAZY SUBSYSTEM ACCESSORS
    # =====================================================================

    def _get_campaign_mgr(self):
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

    def _get_mission_resolver(self):
        """Lazily initialise and return the MissionResolver."""
        if self._mission_resolver is None:
            from codex.games.bob.missions import MissionResolver
            self._mission_resolver = MissionResolver()
        return self._mission_resolver

    # =====================================================================
    # CHARACTER MANAGEMENT
    # =====================================================================

    def create_character(self, name: str, **kwargs) -> BoBCharacter:
        """Create a new Legionnaire and make them the party lead."""
        setting_id = kwargs.pop("setting_id", self.setting_id)
        char = BoBCharacter(name=name, setting_id=setting_id, **kwargs)
        self.character = char
        if not self.party:
            self.party = [char]
        else:
            self.party.append(char)
        from codex.core.services.fitd_engine import StressClock, BOB_TRAUMAS
        self.stress_clocks[name] = StressClock(trauma_table=list(BOB_TRAUMAS))
        self._add_shard(
            f"Legion squad formed. Lead: {name} ({char.playbook or 'Unknown'}). "
            f"Chosen: {self.chosen or 'None'}",
            "MASTER",
        )
        if not self.setting_id and setting_id:
            self.setting_id = setting_id
        return char

    def add_to_party(self, char: BoBCharacter) -> None:
        """Add an existing Legionnaire to the active party."""
        self.party.append(char)
        from codex.core.services.fitd_engine import StressClock, BOB_TRAUMAS
        self.stress_clocks[char.name] = StressClock(trauma_table=list(BOB_TRAUMAS))

    def remove_from_party(self, char: BoBCharacter) -> None:
        """Remove a Legionnaire from the active party."""
        if char in self.party:
            self.party.remove(char)
            self.stress_clocks.pop(char.name, None)

    def get_active_party(self) -> List[BoBCharacter]:
        """Return all current party members."""
        return list(self.party)

    def roll_action(self, character: Optional[BoBCharacter] = None,
                    action: str = "skirmish", bonus_dice: int = 0, **kwargs) -> Any:
        """Roll an FITD action using the character's action dots.

        Args:
            character: The acting character (defaults to lead).
            action: Action attribute name (e.g. 'skirmish', 'scout_action').
            bonus_dice: Extra dice from teamwork / assist.
            **kwargs: Accepts 'position' (Position) and 'effect' (Effect).

        Returns:
            FITDResult with outcome, dice, and position/effect context.
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect
        char = character or self.character
        dots = getattr(char, action, 0) if char else 0
        position = kwargs.get("position", Position.RISKY)
        effect = kwargs.get("effect", Effect.STANDARD)
        roll = FITDActionRoll(dice_count=dots + bonus_dice,
                              position=position, effect=effect)
        return roll.roll()

    def push_stress(self, char_name: str, amount: int = 1) -> dict:
        """Push stress with trauma shard emission (WO-V61.0).

        Args:
            char_name: Name of the character whose stress clock to push.
            amount: Stress points to add.

        Returns:
            StressClock.push() result dict, or empty dict if no clock found.
        """
        clock = self.stress_clocks.get(char_name)
        if not clock:
            return {}
        result = clock.push(amount)
        if result.get("trauma_triggered"):
            self._add_shard(
                f"{char_name} suffered trauma: {result['new_trauma']}. "
                f"Total traumas: {result['total_traumas']}/4.",
                "ANCHOR", source="session",
            )
        return result

    def get_mood_context(self) -> dict:
        """Return current mechanical state as narrative mood modifiers (WO-V61.0)."""
        char = self.character
        clock = self.stress_clocks.get(char.name) if char and hasattr(self, 'stress_clocks') else None
        stress = clock.current_stress if clock else 0
        max_stress = clock.max_stress if clock else 9
        trauma_count = len(clock.traumas) if clock else 0
        stress_pct = stress / max(1, max_stress)
        tension = min(1.0, stress_pct + (trauma_count * 0.15))

        words = []
        if trauma_count >= 2:
            words.extend(["haunted", "fractured", "unreliable"])
        if stress_pct > 0.7:
            words.extend(["fraying", "manic", "reckless"])

        if stress_pct > 0.8 or trauma_count >= 3:
            condition = "critical"
        elif stress_pct > 0.5 or trauma_count >= 1:
            condition = "battered"
        else:
            condition = "healthy"

        return {
            "tension": round(tension, 2),
            "tone_words": words,
            "party_condition": condition,
            "system_specific": {"stress": stress, "trauma_count": trauma_count},
        }

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
        """Serialize full engine state for persistence."""
        state: Dict[str, Any] = {
            "system_id": self.system_id,
            "setting_id": self.setting_id,
            "party": [c.to_dict() for c in self.party],
            "stress": {k: v.to_dict() for k, v in self.stress_clocks.items()},
            "faction_clocks": [c.to_dict() for c in self.faction_clocks],
            "legion": self.legion.to_dict(),
            "chosen": self.chosen,
            "campaign_phase": self.campaign_phase,
            # WO-Phase2A: subsystem state
            "campaign_mgr": self._campaign_mgr.to_dict() if self._campaign_mgr else None,
            "mission_resolver": self._mission_resolver.to_dict() if self._mission_resolver else None,
        }
        return state

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict."""
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

        # WO-Phase2A: restore subsystems if present
        campaign_data = data.get("campaign_mgr")
        if campaign_data:
            from codex.games.bob.campaign import CampaignPhaseManager
            self._campaign_mgr = CampaignPhaseManager.from_dict(campaign_data)

        mission_data = data.get("mission_resolver")
        if mission_data:
            from codex.games.bob.missions import MissionResolver
            self._mission_resolver = MissionResolver.from_dict(mission_data)

    # =====================================================================
    # COMMAND DISPATCHER (WO-V10.0 + Phase2A expansion)
    # =====================================================================

    _PHASE_CYCLE = ["march", "camp", "mission"]

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Dispatch a command string to the appropriate handler.

        Args:
            cmd: Command name (e.g. 'march', 'camp', 'mission_plan').
            **kwargs: Command-specific keyword arguments.

        Returns:
            Human-readable result string.
        """
        if cmd == "trace_fact":
            return self.trace_fact(kwargs.get("fact", ""))
        handler = getattr(self, f"_cmd_{cmd}", None)
        if handler:
            return handler(**kwargs)
        return f"Unknown command: {cmd}"

    # ── Original commands (unchanged) ──────────────────────────────────

    def _cmd_roll_action(self, **kwargs) -> str:
        """Roll an FITD action check."""
        from codex.core.services.fitd_engine import format_roll_result
        result = self.roll_action(**kwargs)
        return format_roll_result(result)

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

    # ── Supply check (enhanced from stub) ─────────────────────────────

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

    # ── Campaign advance (enhanced from stub) ─────────────────────────

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

    # ── Phase2A new command handlers ───────────────────────────────────

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

        lines = [
            f"Mission resolved: {result['mission_type']} — {result['success_level'].upper()}",
            f"Casualties: {result['casualty_outcome']['label']}",
            f"Rewards: {result.get('reward_description', 'None')}",
            f"Morale impact: {result['morale_delta']:+d}",
            result["notes"],
        ]
        if relic_str:
            lines.append(relic_str)

        msg = "\n".join(lines)
        self._add_shard(msg, "CHRONICLE")
        return msg

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
# COMMAND DEFINITIONS (WO-V8.0 + Phase2A)
# =========================================================================

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
}

BOB_CATEGORIES = {
    "Legion":   [
        "legion_status", "campaign_advance", "supply_check", "chosen_status",
        "campaign_status",
    ],
    "Campaign": [
        "march", "camp", "pressure_check", "time_passes",
    ],
    "Mission":  [
        "mission_plan", "mission_resolve",
    ],
    "Squad":    [
        "roll_action", "squad_status", "complication",
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

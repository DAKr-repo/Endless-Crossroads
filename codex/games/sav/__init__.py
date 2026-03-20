"""
Scum and Villainy -- Game Engine
================================

Space opera heist game using the Forged in the Dark framework.
Uses three action categories (Insight, Prowess, Resolve) with d6 pools.

Integrates with:
  - codex/core/engines/narrative_base.py for shared FITD mechanics
  - codex/forge/char_wizard.py via vault/FITD/sav/creation_rules.json
  - codex/games/sav/ships.py for ship management
  - codex/games/sav/jobs.py for job phase management

Activated when a Scum & Villainy campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from codex.core.engines.narrative_base import NarrativeEngineBase


# =========================================================================
# CHARACTER
# =========================================================================

@dataclass
class SaVCharacter:
    """A Scum & Villainy player character."""
    name: str
    playbook: str = ""     # Mechanic, Muscle, Mystic, Pilot, Scoundrel, Speaker, Stitch
    heritage: str = ""     # Colonist, Imperial, Spacer, Syndicate, Wanderer

    # Action dots (0-4 each, grouped by category)
    # Insight actions
    doctor: int = 0
    hack: int = 0
    rig: int = 0
    study: int = 0
    # Prowess actions
    helm: int = 0
    scramble: int = 0
    scrap: int = 0
    skulk: int = 0
    # Resolve actions
    attune: int = 0
    command: int = 0
    consort: int = 0
    sway: int = 0

    vice: str = ""
    setting_id: str = ""

    def is_alive(self) -> bool:
        """FITD characters don't die from HP; always considered active."""
        return True

    def to_dict(self) -> dict:
        """Serialize to a plain dict for save/load."""
        return {
            "name": self.name, "playbook": self.playbook,
            "heritage": self.heritage, "vice": self.vice,
            "setting_id": self.setting_id,
            "doctor": self.doctor, "hack": self.hack,
            "rig": self.rig, "study": self.study,
            "helm": self.helm, "scramble": self.scramble,
            "scrap": self.scrap, "skulk": self.skulk,
            "attune": self.attune, "command": self.command,
            "consort": self.consort, "sway": self.sway,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SaVCharacter":
        """Deserialize from a plain dict."""
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


# =========================================================================
# ENGINE
# =========================================================================

class SaVEngine(NarrativeEngineBase):
    """Core engine for Scum & Villainy campaigns.

    Manages crew, ship state, faction relationships, and the job cycle.
    Tracks heat, rep, and coin as crew resources.

    Inherits from NarrativeEngineBase:
        create_character, add_to_party, remove_from_party, get_active_party,
        roll_action, push_stress, get_mood_context, handle_command.

    Lazy-initialized subsystems:
        _ship_state: ShipState (ship management)
        _job_manager: JobPhaseManager (job phase management)
    """

    system_id = "sav"
    system_family = "FITD"
    display_name = "Scum and Villainy"

    def __init__(self) -> None:
        """Initialize engine with default state and lazy subsystem placeholders."""
        super().__init__()
        self.ship_name: str = ""
        self.ship_class: str = ""
        self.heat: int = 0        # Wanted level (0-6)
        self.rep: int = 0         # Reputation
        self.coin: int = 2        # Starting coin
        # Lazy-init subsystem references
        self._ship_state: Optional[Any] = None    # ShipState
        self._job_manager: Optional[Any] = None   # JobPhaseManager
        self._downtime_mgr: Optional[Any] = None  # SaVDowntimeManager
        self._planning_phase: Optional[Any] = None  # PlanningPhase

    # =====================================================================
    # HOOKS (NarrativeEngineBase)
    # =====================================================================

    def _create_character(self, name: str, **kwargs) -> SaVCharacter:
        """Create a SaVCharacter from name and kwargs."""
        return SaVCharacter.from_dict({"name": name, **kwargs})

    def _get_command_registry(self) -> Dict[str, Callable]:
        """Map command names to handlers, including base aliases."""
        return {
            # Alias base crew stress display to SaV's command name
            "crew_status": self._cmd_crew_stress,
            # Planning phase
            "plan_job": self._cmd_plan_job,
            # Downtime commands
            "downtime_acquire": self._cmd_downtime_acquire,
            "downtime_recover": self._cmd_downtime_recover,
            "downtime_vice": self._cmd_downtime_vice,
            "downtime_project": self._cmd_downtime_project,
            "downtime_train": self._cmd_downtime_train,
            "downtime_repair": self._cmd_downtime_repair,
            "downtime_resupply": self._cmd_downtime_resupply,
            # Post-job faction response
            "faction_response": self._cmd_faction_response,
            # Inherited narrative base commands (explicit registration for discoverability)
            "fortune": self._cmd_fortune,
            "resist": self._cmd_resist,
            "gather_info": self._cmd_gather_info,
        }

    def _format_status(self) -> str:
        """Return SaV-specific status string."""
        lead = self.party[0] if self.party else None
        return (
            f"Ship: {self.ship_name or 'Unnamed'} ({self.ship_class or 'Unknown'}) | "
            f"Heat: {self.heat} | Coin: {self.coin} | Rep: {self.rep} | "
            f"Crew: {len(self.party)} | "
            f"Lead: {lead.name if lead else 'None'}"
        )

    # =====================================================================
    # LAZY ACCESSORS
    # =====================================================================

    def _get_ship_state(self) -> Any:
        """Lazily initialize and return the ShipState."""
        if self._ship_state is None:
            from codex.games.sav.ships import ShipState
            self._ship_state = ShipState(
                name=self.ship_name or "Unnamed",
                ship_class=self.ship_class or "",
            )
        return self._ship_state

    def _get_job_manager(self) -> Any:
        """Lazily initialize and return the JobPhaseManager."""
        if self._job_manager is None:
            from codex.games.sav.jobs import JobPhaseManager
            self._job_manager = JobPhaseManager()
        return self._job_manager

    def _get_downtime_mgr(self) -> Any:
        """Lazily initialize and return the SaVDowntimeManager."""
        if self._downtime_mgr is None:
            from codex.games.sav.downtime import SaVDowntimeManager
            self._downtime_mgr = SaVDowntimeManager()
        return self._downtime_mgr

    def _get_planning_phase(self) -> Any:
        """Lazily initialize and return the PlanningPhase."""
        if self._planning_phase is None:
            from codex.games.sav.jobs import PlanningPhase
            self._planning_phase = PlanningPhase()
        return self._planning_phase

    # =====================================================================
    # STATUS (override for ship info)
    # =====================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dict suitable for Butler status display."""
        lead = self.party[0] if self.party else None
        ship = self._ship_state
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "playbook": lead.playbook if lead else None,
            "ship": self.ship_name or "Unnamed",
            "ship_class": self.ship_class or "Unknown",
            "heat": self.heat,
            "coin": self.coin,
            "rep": self.rep,
            "ship_systems": ship.systems if ship else {},
            "gambits": ship.gambits if ship else 0,
        }

    # =====================================================================
    # SETTING-FILTERED ACCESSORS (WO-V46.0)
    # =====================================================================

    def get_playbooks(self) -> dict:
        """Return playbooks filtered by active setting."""
        from codex.forge.reference_data.sav_playbooks import PLAYBOOKS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(PLAYBOOKS, self.setting_id)

    def get_heritages(self) -> dict:
        """Return heritages filtered by active setting."""
        from codex.forge.reference_data.sav_playbooks import HERITAGES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(HERITAGES, self.setting_id)

    def get_factions(self) -> dict:
        """Return factions filtered by active setting."""
        from codex.forge.reference_data.sav_factions import FACTIONS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(FACTIONS, self.setting_id)

    def get_ship_classes(self) -> dict:
        """Return ship classes filtered by active setting."""
        from codex.forge.reference_data.sav_ships import SHIP_CLASSES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(SHIP_CLASSES, self.setting_id)

    # =====================================================================
    # SAVE / LOAD (extend base with SaV-specific fields)
    # =====================================================================

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state for persistence."""
        state = super().save_state()
        state.update({
            "ship_name": self.ship_name,
            "ship_class": self.ship_class,
            "heat": self.heat,
            "rep": self.rep,
            "coin": self.coin,
            "ship_state": self._ship_state.to_dict() if self._ship_state else None,
            "job_manager": self._job_manager.to_dict() if self._job_manager else None,
            "downtime_mgr": self._downtime_mgr.to_dict() if self._downtime_mgr else None,
            "planning_phase": self._planning_phase.to_dict() if self._planning_phase else None,
        })
        return state

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict."""
        # Use SaVCharacter.from_dict for party (base uses _create_character)
        from codex.core.services.fitd_engine import StressClock, UniversalClock
        self.setting_id = data.get("setting_id", "")
        self.party = [SaVCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.stress_clocks = {k: StressClock.from_dict(v)
                              for k, v in data.get("stress", {}).items()}
        self.faction_clocks = [UniversalClock.from_dict(c)
                               for c in data.get("faction_clocks", [])]
        # SaV-specific fields
        self.ship_name = data.get("ship_name", "")
        self.ship_class = data.get("ship_class", "")
        self.heat = data.get("heat", 0)
        self.rep = data.get("rep", 0)
        self.coin = data.get("coin", 2)
        # Restore subsystems
        ship_data = data.get("ship_state")
        if ship_data:
            from codex.games.sav.ships import ShipState
            self._ship_state = ShipState.from_dict(ship_data)
        job_data = data.get("job_manager")
        if job_data:
            from codex.games.sav.jobs import JobPhaseManager
            self._job_manager = JobPhaseManager.from_dict(job_data)
        dt_data = data.get("downtime_mgr")
        if dt_data:
            from codex.games.sav.downtime import SaVDowntimeManager
            self._downtime_mgr = SaVDowntimeManager.from_dict(dt_data)
        pp_data = data.get("planning_phase")
        if pp_data:
            from codex.games.sav.jobs import PlanningPhase
            self._planning_phase = PlanningPhase.from_dict(pp_data)

    # =====================================================================
    # SHIP COMMANDS
    # =====================================================================

    def _cmd_ship_status(self, **kwargs) -> str:
        """Display ship name, class, systems, and modules."""
        ship = self._get_ship_state()
        lines = [
            f"Ship: {ship.name} ({ship.ship_class or 'Unknown Class'})",
            f"Hull Integrity: {ship.hull_integrity}/6 | Gambits: {ship.gambits}/4",
            f"Heat: {self.heat} | Coin: {self.coin} | Rep: {self.rep}",
            "Systems:",
        ]
        from codex.forge.reference_data.sav_ships import SYSTEM_QUALITY_TRACKS
        for sys_name, quality in ship.systems.items():
            track = SYSTEM_QUALITY_TRACKS.get(sys_name, {})
            status = track.get(quality, f"Quality {quality}/3")
            lines.append(f"  {sys_name.title()}: {'*' * quality + '-' * (3 - quality)} ({status[:50]})")
        if ship.installed_modules:
            lines.append(f"Modules: {', '.join(ship.installed_modules)}")
        else:
            lines.append("Modules: None installed")
        return "\n".join(lines)

    def _cmd_ship_upgrade(self, **kwargs) -> str:
        """Install a module on the ship."""
        module_name = kwargs.get("module", "")
        if not module_name:
            return "Specify a module: ship_upgrade module=<module_name>"
        from codex.games.sav.ships import install_module
        ship = self._get_ship_state()
        result = install_module(ship, module_name)
        return result["message"]

    def _cmd_ship_combat(self, **kwargs) -> str:
        """Roll ship combat using a specified system."""
        from codex.games.sav.ships import ship_combat_roll
        ship = self._get_ship_state()
        system = kwargs.get("system", "weapons")
        bonus_dice = int(kwargs.get("bonus_dice", 0))
        result = ship_combat_roll(ship, system, bonus_dice)
        return (
            f"Ship combat roll ({system}): {result['description']}\n"
            f"Outcome: {result['outcome'].upper()}"
        )

    def _cmd_ship_repair(self, **kwargs) -> str:
        """Repair a ship system during downtime."""
        from codex.games.sav.ships import repair_system
        ship = self._get_ship_state()
        system = kwargs.get("system", "hull")
        mechanic_dots = int(kwargs.get("mechanic_dots", 0))
        result = repair_system(ship, system, mechanic_dots)
        if "error" in result:
            return result["error"]
        return (
            f"Repair roll ({system}): {result['description']}\n"
            f"Quality: {result['system_before']} -> {result['system_after']}"
        )

    def _cmd_install_module(self, **kwargs) -> str:
        """Install a named module on the ship."""
        module_name = kwargs.get("module", "")
        if not module_name:
            return "Specify a module: install_module module=<module_name>"
        from codex.games.sav.ships import install_module
        ship = self._get_ship_state()
        result = install_module(ship, module_name)
        if result["success"]:
            self._add_shard(
                f"Module installed: {module_name} on {ship.name}",
                "ANCHOR",
            )
        return result["message"]

    def _cmd_use_gambit(self, **kwargs) -> str:
        """Spend 1 gambit for a bonus die on the next ship action."""
        from codex.games.sav.ships import use_gambit
        ship = self._get_ship_state()
        result = use_gambit(ship)
        return result["message"]

    def _cmd_set_course(self, **kwargs) -> str:
        """Plot a hyperspace jump to a destination."""
        from codex.games.sav.jobs import jump_planning
        destination = kwargs.get("destination", "unknown destination")
        nav_dots = int(kwargs.get("nav_dots", 0))
        result = jump_planning(destination, nav_dots)
        self._add_shard(
            f"Jump to {destination}: {result['outcome']}",
            "CHRONICLE",
        )
        return (
            f"Plotting course to {destination}...\n"
            f"Helm roll: Dice [{', '.join(str(d) for d in result['dice'])}] -> {result['outcome'].upper()}\n"
            f"{result['description']}"
        )

    def _cmd_jump(self, **kwargs) -> str:
        """Alias for set_course — execute a hyperspace jump."""
        return self._cmd_set_course(**kwargs)

    def _cmd_complication(self, **kwargs) -> str:
        """Roll a complication from the system's consequence table."""
        import random as _rng
        tier = max(1, min(4, kwargs.get("tier", 1)))
        effective_tier = min(4, tier + (1 if self.heat >= 4 else 0))
        pool = COMPLICATION_TABLE.get(effective_tier, COMPLICATION_TABLE[1])
        entry = _rng.choice(pool)
        self._add_shard(
            f"Complication ({entry['type']}): {entry['text']}",
            "CHRONICLE",
        )
        return f"COMPLICATION: {entry['text']}\nEffect: {entry.get('effect', 'none')}"

    # =====================================================================
    # PLANNING PHASE COMMANDS
    # =====================================================================

    def _cmd_plan_job(self, **kwargs) -> str:
        """Set the plan type and detail before engagement.

        Kwargs:
            plan_type (str): One of assault/deception/infiltration/mystic/social/transport.
            detail (str): Specific actionable context for the engagement bonus.

        Returns:
            Confirmation string or error message.
        """
        plan_type = kwargs.get("plan_type", "assault")
        detail = kwargs.get("detail", "")
        phase = self._get_planning_phase()
        result = phase.set_plan(plan_type, detail)
        if not result["success"]:
            return result["error"]
        self._add_shard(f"Job planned: {plan_type} — {detail}", "CHRONICLE")
        return f"Plan set: {plan_type}\nDetail: {detail or '(none)'}"

    # =====================================================================
    # DOWNTIME COMMANDS
    # =====================================================================

    def _cmd_downtime_acquire(self, **kwargs) -> str:
        """Acquire a temporary asset during downtime.

        Kwargs:
            crew_tier (int): Crew tier as dice pool base (default: party size).
            quality (int): Desired asset quality (default 1).

        Returns:
            Result description string.
        """
        mgr = self._get_downtime_mgr()
        crew_tier = int(kwargs.get("crew_tier", max(1, len(self.party))))
        quality = int(kwargs.get("quality", 1))
        result = mgr.acquire_asset(crew_tier, quality)
        return result["description"]

    def _cmd_downtime_recover(self, **kwargs) -> str:
        """Recover from harm during downtime.

        Kwargs:
            healer_dots (int): Healer's relevant action dots (default 0).

        Returns:
            Result description string.
        """
        mgr = self._get_downtime_mgr()
        healer_dots = int(kwargs.get("healer_dots", 0))
        result = mgr.recover(healer_dots)
        return result["description"]

    def _cmd_downtime_vice(self, **kwargs) -> str:
        """Indulge vice for stress recovery.

        Automatically reduces lead character's stress clock if present.

        Returns:
            Result description string.
        """
        mgr = self._get_downtime_mgr()
        char = self.character
        result = mgr.vice_indulgence()
        if char and char.name in self.stress_clocks:
            self.stress_clocks[char.name].recover(result["stress_recovered"])
        return result["description"]

    def _cmd_downtime_project(self, **kwargs) -> str:
        """Work on a long-term project clock.

        Kwargs:
            project_name (str): Name of the project (required).
            action_dots (int): Relevant action dots for the roll (default 1).
            clock_size (int): Project clock size if new (default 8).

        Returns:
            Progress description string or error if name missing.
        """
        mgr = self._get_downtime_mgr()
        name = kwargs.get("project_name", "")
        if not name:
            return "Specify project_name."
        action_dots = int(kwargs.get("action_dots", 1))
        clock_size = int(kwargs.get("clock_size", 8))
        result = mgr.long_term_project(name, action_dots, clock_size)
        if result["completed"]:
            self._add_shard(f"Project completed: {name}", "ANCHOR")
        return result["description"]

    def _cmd_downtime_train(self, **kwargs) -> str:
        """Train for XP in an attribute.

        Kwargs:
            attribute (str): Attribute to mark XP in (default "playbook").

        Returns:
            Confirmation string with XP gained.
        """
        mgr = self._get_downtime_mgr()
        result = mgr.train(kwargs.get("attribute", "playbook"))
        return result["description"]

    def _cmd_downtime_repair(self, **kwargs) -> str:
        """Repair the ship during downtime using the rig or mechanic action.

        Kwargs:
            system (str): Ship system to repair (default "hull").
            mechanic_dots (int): Mechanic's rig/hack dots (default 0).

        Returns:
            Repair result description string.
        """
        system = kwargs.get("system", "hull")
        mechanic_dots = int(kwargs.get("mechanic_dots", 0))
        ship = self._get_ship_state()
        from codex.games.sav.ships import repair_system
        result = repair_system(ship, system, mechanic_dots)
        if "error" in result:
            return result["error"]
        self._add_shard(
            f"Ship repair ({system}): quality {result['system_before']} -> {result['system_after']}",
            "CHRONICLE",
        )
        return (
            f"Downtime repair ({system}): {result['description']}\n"
            f"Quality: {result['system_before']} -> {result['system_after']}"
        )

    def _cmd_downtime_resupply(self, **kwargs) -> str:
        """Resupply the ship — restore 1 gambit during downtime.

        Returns:
            Confirmation with current gambit count.
        """
        ship = self._get_ship_state()
        old = ship.gambits
        ship.gambits = min(4, ship.gambits + 1)
        self._add_shard(f"Ship resupply: gambits {old} -> {ship.gambits}", "CHRONICLE")
        return f"Ship resupplied. Gambits: {old} -> {ship.gambits}/4"

    def _cmd_faction_response(self, **kwargs) -> str:
        """Post-job faction reaction based on current heat level.

        Returns:
            Description of the faction response.
        """
        import random as _rng
        responses = {
            0: "The factions haven't noticed your crew yet.",
            1: "Minor faction attention — a warning message delivered.",
            2: "A faction sends enforcers to make their displeasure known.",
            3: "Faction retaliation — they strike at your operations.",
            4: "Full faction war — they're coming for your crew.",
        }
        heat_tier = min(4, self.heat)
        response = responses[heat_tier]
        roll = _rng.randint(1, 6)
        if roll >= 5:
            response += " But an opportunity presents itself..."
        self._add_shard(f"Faction response (heat {self.heat}): {response}", "CHRONICLE")
        return f"Faction Response (heat {self.heat}): {response}"

    # =====================================================================
    # JOB COMMANDS
    # =====================================================================

    def _cmd_engagement(self, **kwargs) -> str:
        """Roll the engagement roll for a job."""
        manager = self._get_job_manager()
        target = kwargs.get("target", "Unknown target")
        plan_type = kwargs.get("plan_type", "assault")
        detail_bonus = int(kwargs.get("detail_bonus", 0))
        crew_tier = max(1, len(self.party))
        manager.start_job(target, plan_type)
        result = manager.job_engagement_roll(
            crew_tier=crew_tier,
            plan_type=plan_type,
            detail_bonus=detail_bonus,
        )
        self._add_shard(
            f"Job started: {plan_type} against {target}. Engagement: {result['outcome']}",
            "CHRONICLE",
        )
        return (
            f"Engagement roll vs {target} ({plan_type} plan):\n"
            f"Dice: [{', '.join(str(d) for d in result['dice'])}] -> {result['outcome'].upper()}\n"
            f"Starting position: {result['starting_position'].upper()}\n"
            f"{result['description']}"
        )

    def _cmd_resolve_job(self, **kwargs) -> str:
        """Resolve the current job and collect rewards."""
        manager = self._get_job_manager()
        target_tier = int(kwargs.get("target_tier", 2))
        crew_tier = max(1, len(self.party))
        result = manager.resolve_job(
            crew_tier=crew_tier,
            target_tier=target_tier,
        )
        if "error" in result:
            return result["error"]
        self.coin += result["cred"]
        self.rep += result["rep"]
        self.heat += result["heat"]
        ship = self._get_ship_state()
        ship.gambits = min(4, ship.gambits + 1)
        self._add_shard(
            f"Job resolved. +{result['cred']} cred, +{result['rep']} rep, +{result['heat']} heat.",
            "CHRONICLE",
        )
        return result["summary"]


# =========================================================================
# COMPLICATION TABLE (Gap Fix: per-engine consequences)
# =========================================================================

COMPLICATION_TABLE: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"type": "system_malfunction", "text": "A minor system glitch forces a manual override.", "effect": "position worsened"},
        {"type": "customs_interdiction", "text": "A routine customs scan picks up something suspicious.", "effect": "heat +1"},
        {"type": "bounty_hunter", "text": "A two-bit bounty hunter starts asking questions at the last port.", "effect": "heat +1"},
    ],
    2: [
        {"type": "system_malfunction", "text": "Navigation array throws false readings. Recalibration needed.", "effect": "helm -1d next roll"},
        {"type": "customs_interdiction", "text": "Hegemony patrol demands to board for inspection.", "effect": "heat +2"},
        {"type": "crew_mutiny", "text": "A crewmate questions your leadership in front of the others.", "effect": "stress +2"},
    ],
    3: [
        {"type": "system_malfunction", "text": "Engine core destabilizes during a jump. Emergency shutdown.", "effect": "hull -1"},
        {"type": "bounty_hunter", "text": "A Guild-licensed hunter locks onto your transponder signal.", "effect": "heat +3"},
        {"type": "customs_interdiction", "text": "Hegemony impounds your cargo pending investigation.", "effect": "coin -2"},
        {"type": "crew_mutiny", "text": "The crew threatens to walk unless conditions improve.", "effect": "stress +3"},
    ],
    4: [
        {"type": "system_malfunction", "text": "Critical hull breach. Atmosphere venting in section four.", "effect": "hull -2"},
        {"type": "bounty_hunter", "text": "An elite Hegemony tracker has your ship flagged system-wide.", "effect": "heat +4"},
        {"type": "crew_mutiny", "text": "Mutiny erupts. Someone pulls a weapon on the bridge.", "effect": "stress +4"},
    ],
}


# =========================================================================
# COMMAND DEFINITIONS
# =========================================================================

SAV_COMMANDS = {
    # Ship commands
    "ship_status":          "Display ship name, class, systems, and modules",
    "ship_upgrade":         "Install a module on the ship (module=<name>)",
    "ship_combat":          "Roll ship combat with a system (system=<engines|hull|comms|weapons>)",
    "ship_repair":          "Repair a ship system during downtime (system=<name>, mechanic_dots=<int>)",
    "install_module":       "Install a named module (module=<name>)",
    "use_gambit":           "Spend 1 gambit for +1d on next ship action",
    "set_course":           "Plot hyperspace jump (destination=<name>, nav_dots=<int>)",
    "jump":                 "Execute a hyperspace jump (alias for set_course)",
    # Job commands
    "engagement":           "Roll job engagement (target=<name>, plan_type=<str>)",
    "resolve_job":          "Resolve active job and collect cred/rep/heat (target_tier=<int>)",
    "plan_job":             "Set plan type and detail before job engagement",
    "faction_response":     "Check faction reaction based on heat level",
    # Downtime commands
    "downtime_acquire":     "Acquire a temporary asset (crew_tier=<int>, quality=<int>)",
    "downtime_recover":     "Recover from harm during downtime (healer_dots=<int>)",
    "downtime_vice":        "Indulge vice for stress recovery",
    "downtime_project":     "Work on a long-term project clock (project_name=<str>)",
    "downtime_train":       "Train for XP in an attribute (attribute=<str>)",
    "downtime_repair":      "Repair a ship system during downtime (system=<str>, mechanic_dots=<int>)",
    "downtime_resupply":    "Resupply the ship — restore 1 gambit",
    # Crew commands
    "roll_action":          "Roll an FITD action check",
    "crew_status":          "Show crew stress and trauma",
    "complication":         "Roll a complication from the consequence table",
    "fortune":              "Roll a fortune die pool (dice_count=<int>)",
    "resist":               "Roll resistance (attribute=<str>)",
    "gather_info":          "Gather information (action=<str>, question=<str>)",
}

SAV_CATEGORIES = {
    "Ship": [
        "ship_status", "ship_upgrade", "ship_combat", "ship_repair",
        "install_module", "use_gambit", "set_course", "jump",
    ],
    "Jobs": ["engagement", "resolve_job", "plan_job", "faction_response"],
    "Downtime": [
        "downtime_acquire", "downtime_recover", "downtime_vice",
        "downtime_project", "downtime_train",
        "downtime_repair", "downtime_resupply",
    ],
    "Crew": ["roll_action", "crew_status", "complication", "fortune", "resist", "gather_info"],
}


# =========================================================================
# ENCOUNTER & LOCATION CONTENT (WO-V47.0)
# =========================================================================

ENCOUNTER_TABLE = [
    {"name": "Hegemony Patrol Cutter", "description": "An armored patrol vessel hails you, demanding cargo manifest.", "effect": "heat +1, 4-clock 'Inspection'"},
    {"name": "Pirate Ambush", "description": "Two fast ships emerge from an asteroid's shadow, weapons hot.", "effect": "engagement roll, harm level 2 on failure"},
    {"name": "System Patrol Checkpoint", "description": "A legitimate checkpoint — unless your cargo is contraband.", "effect": "heat +2 if carrying contraband, otherwise routine"},
    {"name": "Alien Fauna Migration", "description": "A school of void-jellies drifts across your flight path, tendrils crackling with static.", "effect": "pilot roll or 2-clock 'Hull Damage'"},
    {"name": "Derelict Drifter", "description": "A ship tumbles silently through the void, no running lights, hull breached.", "effect": "opportunity for salvage, risk of trap or contagion"},
    {"name": "Mystic Signal", "description": "Your comms pick up a repeating signal in an ancient language.", "effect": "Way attunement opportunity, stress +1 to resist"},
]

LOCATION_DESCRIPTIONS = {
    "iota": [
        "A backwater moon with a single spaceport carved into red rock. Dust gets into everything.",
        "Neon signs in three languages advertise fuel, repairs, and things best left unspoken.",
    ],
    "warren": [
        "A hollowed-out asteroid riddled with tunnels. Every surface is covered in condensation and rust.",
        "The market cavern echoes with a dozen species haggling. Gravity plating flickers intermittently.",
    ],
    "nightfall": [
        "The dark side of a tidally locked world. Permanent twilight, lit by bioluminescent fungi.",
        "Ice crystals form on your visor. The settlement huddles around geothermal vents like a campfire.",
    ],
    "brekk": [
        "A gas giant refinery station. The air tastes metallic, and the superstructure groans constantly.",
        "Massive pipes run in every direction, venting steam and strange-colored gases into the void.",
    ],
    "indri": [
        "A jungle planet where the canopy blocks the sky. Everything is green, wet, and watching you.",
        "Ancient ruins poke through the undergrowth. The locals say the temples still have guardians.",
    ],
}


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("sav", SaVEngine)
except ImportError:
    pass

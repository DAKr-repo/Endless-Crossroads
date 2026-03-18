"""
Scum and Villainy -- Game Engine
================================

Space opera heist game using the Forged in the Dark framework.
Uses three action categories (Insight, Prowess, Resolve) with d6 pools.

Integrates with:
  - codex/core/services/fitd_engine.py for shared FITD mechanics
  - codex/forge/char_wizard.py via vault/FITD/sav/creation_rules.json
  - codex/games/sav/ships.py for ship management
  - codex/games/sav/jobs.py for job phase management

Activated when a Scum & Villainy campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from codex.core.services.narrative_loom import NarrativeLoomMixin


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

class SaVEngine(NarrativeLoomMixin):
    """Core engine for Scum & Villainy campaigns.

    Manages crew, ship state, faction relationships, and the job cycle.
    Tracks heat, rep, and coin as crew resources.

    Lazy-initialized subsystems:
        _ship_state: ShipState (ship management)
        _job_manager: JobPhaseManager (job phase management)
    """

    system_id = "sav"
    system_family = "FITD"
    display_name = "Scum and Villainy"

    def __init__(self) -> None:
        """Initialize engine with default state and lazy subsystem placeholders."""
        from codex.core.services.fitd_engine import StressClock, FactionClock  # noqa: F401
        self.character: Optional[SaVCharacter] = None
        self.party: List[SaVCharacter] = []
        self.stress_clocks: Dict[str, Any] = {}
        self.faction_clocks: List[Any] = []
        self.ship_name: str = ""
        self.ship_class: str = ""
        self.heat: int = 0        # Wanted level (0-6)
        self.rep: int = 0         # Reputation
        self.coin: int = 2        # Starting coin
        # Lazy-init subsystem references
        self._ship_state: Optional[Any] = None    # ShipState
        self._job_manager: Optional[Any] = None   # JobPhaseManager
        self._init_loom()
        self.setting_id: str = ""

    # =====================================================================
    # LAZY ACCESSORS
    # =====================================================================

    def _get_ship_state(self) -> Any:
        """Lazily initialize and return the ShipState.

        Returns:
            Active ShipState instance (created from ship_name/ship_class if needed).
        """
        if self._ship_state is None:
            from codex.games.sav.ships import ShipState
            self._ship_state = ShipState(
                name=self.ship_name or "Unnamed",
                ship_class=self.ship_class or "",
            )
        return self._ship_state

    def _get_job_manager(self) -> Any:
        """Lazily initialize and return the JobPhaseManager.

        Returns:
            Active JobPhaseManager instance.
        """
        if self._job_manager is None:
            from codex.games.sav.jobs import JobPhaseManager
            self._job_manager = JobPhaseManager()
        return self._job_manager

    # =====================================================================
    # CHARACTER MANAGEMENT
    # =====================================================================

    def create_character(self, name: str, **kwargs) -> SaVCharacter:
        """Create a new character and make them the party lead.

        Args:
            name: Character's name.
            **kwargs: Additional SaVCharacter fields (playbook, heritage, etc.).

        Returns:
            Newly created SaVCharacter.
        """
        setting_id = kwargs.pop("setting_id", self.setting_id)
        char = SaVCharacter(name=name, setting_id=setting_id, **kwargs)
        self.character = char
        if not self.party:
            self.party = [char]
        else:
            self.party.append(char)
        if not self.setting_id and setting_id:
            self.setting_id = setting_id
        from codex.core.services.fitd_engine import StressClock
        self.stress_clocks[name] = StressClock()
        self._add_shard(
            f"Ship crew founded. Lead: {name} ({char.playbook or 'Unknown'}). "
            f"Ship: {self.ship_name or 'Unnamed'}",
            "MASTER",
        )
        return char

    def add_to_party(self, char: SaVCharacter) -> None:
        """Add an existing character to the active party.

        Args:
            char: The SaVCharacter to add.
        """
        self.party.append(char)
        from codex.core.services.fitd_engine import StressClock
        self.stress_clocks[char.name] = StressClock()

    def remove_from_party(self, char: SaVCharacter) -> None:
        """Remove a character from the active party.

        Args:
            char: The SaVCharacter to remove.
        """
        if char in self.party:
            self.party.remove(char)
            self.stress_clocks.pop(char.name, None)

    def get_active_party(self) -> List[SaVCharacter]:
        """Return all current party members.

        Returns:
            List of active SaVCharacter instances.
        """
        return list(self.party)

    # =====================================================================
    # ACTION ROLLS
    # =====================================================================

    def roll_action(self, character: Optional[SaVCharacter] = None,
                    action: str = "scrap", bonus_dice: int = 0, **kwargs) -> Any:
        """Roll an FITD action using the character's action dots.

        Args:
            character: The acting character (defaults to lead).
            action: Action attribute name (e.g. 'hack', 'helm').
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

    # =====================================================================
    # STATUS
    # =====================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dict suitable for Butler status display.

        Returns:
            Dict with system, party_size, lead, playbook, ship, heat, coin.
        """
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
    # SAVE / LOAD
    # =====================================================================

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state for persistence.

        Returns:
            Dict containing all engine state including subsystem state.
        """
        return {
            "system_id": self.system_id,
            "setting_id": self.setting_id,
            "party": [c.to_dict() for c in self.party],
            "stress": {k: v.to_dict() for k, v in self.stress_clocks.items()},
            "faction_clocks": [c.to_dict() for c in self.faction_clocks],
            "ship_name": self.ship_name, "ship_class": self.ship_class,
            "heat": self.heat, "rep": self.rep, "coin": self.coin,
            # Subsystem state
            "ship_state": self._ship_state.to_dict() if self._ship_state else None,
            "job_manager": self._job_manager.to_dict() if self._job_manager else None,
        }

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict.

        Args:
            data: Dict from a previous save_state() call.
        """
        from codex.core.services.fitd_engine import StressClock, UniversalClock
        self.party = [SaVCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.stress_clocks = {k: StressClock.from_dict(v)
                              for k, v in data.get("stress", {}).items()}
        self.faction_clocks = [UniversalClock.from_dict(c)
                               for c in data.get("faction_clocks", [])]
        self.setting_id = data.get("setting_id", "")
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

    # =====================================================================
    # COMMAND DISPATCHER
    # =====================================================================

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Dispatch a command string to the appropriate handler.

        Args:
            cmd: Command identifier string.
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

    # ─── Crew commands ────────────────────────────────────────────────

    def _cmd_roll_action(self, **kwargs) -> str:
        """Roll an FITD action check."""
        from codex.core.services.fitd_engine import format_roll_result
        result = self.roll_action(**kwargs)
        return format_roll_result(result)

    def _cmd_crew_status(self, **kwargs) -> str:
        """Show crew stress and trauma."""
        lines = ["Crew Stress/Trauma:"]
        for name, clock in self.stress_clocks.items():
            traumas = ", ".join(clock.traumas) if clock.traumas else "none"
            lines.append(f"  {name}: stress {clock.current_stress}/{clock.max_stress} | traumas: {traumas}")
        if not self.stress_clocks:
            lines.append("  No crew members registered.")
        return "\n".join(lines)

    # ─── Ship commands ────────────────────────────────────────────────

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
        """Install a module on the ship.

        Kwargs:
            module: Module name to install (str).
        """
        module_name = kwargs.get("module", "")
        if not module_name:
            return "Specify a module: ship_upgrade module=<module_name>"
        from codex.games.sav.ships import install_module
        ship = self._get_ship_state()
        result = install_module(ship, module_name)
        return result["message"]

    def _cmd_ship_combat(self, **kwargs) -> str:
        """Roll ship combat using a specified system.

        Kwargs:
            system: System to use (engines/hull/comms/weapons). Default: weapons.
            bonus_dice: Additional dice. Default: 0.
        """
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
        """Repair a ship system during downtime.

        Kwargs:
            system: System to repair (str).
            mechanic_dots: Mechanic's rig dots. Default: 0.
        """
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
        """Install a module on the ship.

        Kwargs:
            module: Module name to install (str).
        """
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
        """Plot a hyperspace jump to a destination.

        Kwargs:
            destination: Target system or sector (str).
            nav_dots: Pilot's helm dots. Default: 0.
        """
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

    # ─── Job commands ─────────────────────────────────────────────────

    def _cmd_engagement(self, **kwargs) -> str:
        """Roll the engagement roll for a job.

        Kwargs:
            target: Job target (str).
            plan_type: Plan approach key (str). Default: assault.
            detail_bonus: Bonus dice from actionable detail. Default: 0.
        """
        manager = self._get_job_manager()
        target = kwargs.get("target", "Unknown target")
        plan_type = kwargs.get("plan_type", "assault")
        detail_bonus = int(kwargs.get("detail_bonus", 0))
        crew_tier = max(1, len(self.party))

        # Start the job
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
        """Resolve the current job and collect rewards.

        Kwargs:
            target_tier: Tier of the job target (int). Default: 2.
        """
        manager = self._get_job_manager()
        target_tier = int(kwargs.get("target_tier", 2))
        crew_tier = max(1, len(self.party))

        result = manager.resolve_job(
            crew_tier=crew_tier,
            target_tier=target_tier,
        )
        if "error" in result:
            return result["error"]

        # Apply rewards to engine state
        self.coin += result["cred"]
        self.rep += result["rep"]
        self.heat += result["heat"]

        # Refresh gambits for next job
        ship = self._get_ship_state()
        ship.gambits = min(4, ship.gambits + 1)

        self._add_shard(
            f"Job resolved. +{result['cred']} cred, +{result['rep']} rep, +{result['heat']} heat.",
            "CHRONICLE",
        )
        return result["summary"]


# =========================================================================
# COMMAND DEFINITIONS
# =========================================================================

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


SAV_COMMANDS = {
    # Ship commands
    "ship_status":      "Display ship name, class, systems, and modules",
    "ship_upgrade":     "Install a module on the ship (module=<name>)",
    "ship_combat":      "Roll ship combat with a system (system=<engines|hull|comms|weapons>)",
    "ship_repair":      "Repair a ship system during downtime (system=<name>, mechanic_dots=<int>)",
    "install_module":   "Install a named module (module=<name>)",
    "use_gambit":       "Spend 1 gambit for +1d on next ship action",
    "set_course":       "Plot hyperspace jump (destination=<name>, nav_dots=<int>)",
    "jump":             "Execute a hyperspace jump (alias for set_course)",
    # Job commands
    "engagement":       "Roll job engagement (target=<name>, plan_type=<str>)",
    "resolve_job":      "Resolve active job and collect cred/rep/heat (target_tier=<int>)",
    # Crew commands
    "roll_action":      "Roll an FITD action check",
    "crew_status":      "Show crew stress and trauma",
    "complication":     "Roll a complication from the consequence table",
}

SAV_CATEGORIES = {
    "Ship": [
        "ship_status", "ship_upgrade", "ship_combat", "ship_repair",
        "install_module", "use_gambit", "set_course", "jump",
    ],
    "Jobs": ["engagement", "resolve_job"],
    "Crew": ["roll_action", "crew_status", "complication"],
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

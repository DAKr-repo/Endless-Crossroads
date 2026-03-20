"""
Candela Obscura -- Game Engine
===============================

Supernatural noir investigation using the Illuminated Worlds system.
Uses three resource tracks (Body, Brain, Bleed) instead of FITD stress.

Integrates with:
  - codex/core/engines/narrative_base.py for shared FITD mechanics
  - codex/forge/char_wizard.py via vault/ILLUMINATED_WORLDS/Candela_Obscura/creation_rules.json
  - codex/games/candela/investigations.py for clue/case management (WO-V2C)

Activated when a Candela Obscura campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from codex.core.engines.narrative_base import NarrativeEngineBase


# =========================================================================
# CHARACTER
# =========================================================================

@dataclass
class CandelaCharacter:
    """A Candela Obscura investigator."""
    name: str
    role: str = ""           # Face, Muscle, Scholar, Slink, Weird
    specialization: str = "" # Role sub-type (e.g. Face: Journalist/Magician; Muscle: Explorer/Soldier;
                             #   Scholar: Doctor/Professor; Slink: Criminal/Detective; Weird: Medium/Occultist)
    background: str = ""     # Academic, Occultist, Soldier, Socialite
    catalyst: str = ""     # What drives them: Curiosity, Duty, Revenge, Guilt

    # Action dots grouped by drive (Nerve / Cunning / Intuition)
    # Nerve
    move: int = 0
    strike: int = 0
    control: int = 0
    # Cunning
    sway: int = 0
    read: int = 0
    hide: int = 0
    # Intuition
    survey: int = 0
    focus: int = 0
    sense: int = 0

    # Resource tracks (Illuminated Worlds uses Body/Brain/Bleed instead of stress)
    body: int = 0
    body_max: int = 3
    brain: int = 0
    brain_max: int = 3
    bleed: int = 0
    bleed_max: int = 3
    setting_id: str = ""    # WO-V46.0: sub-setting filter (e.g. "newfaire")

    def is_alive(self) -> bool:
        """A character is broken only when all three tracks are maxed out."""
        return not (self.body >= self.body_max and
                    self.brain >= self.brain_max and
                    self.bleed >= self.bleed_max)

    def take_mark(self, track: str, amount: int = 1) -> dict:
        """Mark damage on a resource track.

        Args:
            track: One of 'body', 'brain', or 'bleed'.
            amount: Number of marks to add.

        Returns:
            Dict with track, old value, new value, and scarred flag.
        """
        old = getattr(self, track, 0)
        cap = getattr(self, f"{track}_max", 3)
        new = min(cap, old + amount)
        setattr(self, track, new)
        scarred = new >= cap
        return {"track": track, "old": old, "new": new, "scarred": scarred}

    def to_dict(self) -> dict:
        """Serialize to a plain dict for save/load."""
        return {
            "name": self.name, "role": self.role,
            "specialization": self.specialization,
            "background": self.background, "catalyst": self.catalyst,
            "move": self.move, "strike": self.strike, "control": self.control,
            "sway": self.sway, "read": self.read, "hide": self.hide,
            "survey": self.survey, "focus": self.focus, "sense": self.sense,
            "body": self.body, "body_max": self.body_max,
            "brain": self.brain, "brain_max": self.brain_max,
            "bleed": self.bleed, "bleed_max": self.bleed_max,
            "setting_id": self.setting_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CandelaCharacter":
        """Deserialize from a plain dict."""
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


# =========================================================================
# ENGINE
# =========================================================================

class CandelaEngine(NarrativeEngineBase):
    """Core engine for Candela Obscura campaigns.

    Uses the Illuminated Worlds system with Body/Brain/Bleed tracks
    instead of standard FITD stress. Shares the d6-pool action roll
    and FactionClock from fitd_engine.

    Inherits from NarrativeEngineBase:
        create_character, add_to_party, remove_from_party,
        roll_action, push_stress, get_mood_context, handle_command.

    WO-V2C: Adds InvestigationManager (lazy-init) for case and clue tracking.
    """

    system_id = "candela"
    system_family = "ILLUMINATED_WORLDS"
    display_name = "Candela Obscura"

    def __init__(self) -> None:
        """Initialize engine with default state and Candela-specific fields."""
        super().__init__()
        self.circle_name: str = ""   # The investigative circle
        self.assignments_completed: int = 0
        # WO-V2C: Investigation subsystem (lazy-initialised)
        self._investigation_mgr: Optional[Any] = None
        # WO-P4: Assignment + Phenomena subsystems (lazy-initialised)
        self._assignment_tracker: Optional[Any] = None
        self._phenomena_tracker: Optional[Any] = None

    # =====================================================================
    # HOOKS (NarrativeEngineBase)
    # =====================================================================

    def _create_character(self, name: str, **kwargs) -> CandelaCharacter:
        """Create a CandelaCharacter from name and kwargs."""
        return CandelaCharacter.from_dict({"name": name, **kwargs})

    def _use_stress_clocks(self) -> bool:
        """Candela uses Body/Brain/Bleed tracks, not StressClocks."""
        return False

    def _get_command_registry(self) -> Dict[str, Callable]:
        """Map command names to handlers."""
        return {
            "start_assignment":    self._cmd_start_assignment,
            "advance_phase":       self._cmd_advance_phase,
            "complete_assignment": self._cmd_complete_assignment,
            "assignment_status":   self._cmd_assignment_status,
            "bleed_escalation":    self._cmd_bleed_escalation,
            "phenomena_status":    self._cmd_phenomena_status,
            "phenomena_tick":      self._cmd_phenomena_tick,
            "phenomena_reduce":    self._cmd_phenomena_reduce,
            "fortune":             self._cmd_fortune,
        }

    def _format_status(self) -> str:
        """Return Candela-specific status string."""
        lead = self.party[0] if self.party else None
        return (
            f"Circle: {self.circle_name or 'Unnamed'} | "
            f"Assignments: {self.assignments_completed} | "
            f"Investigators: {len(self.party)} | "
            f"Lead: {lead.name if lead else 'None'}"
        )

    # ── Lazy Accessor ──────────────────────────────────────────────────

    def _get_investigation_mgr(self) -> Any:
        """Lazily initialise and return the InvestigationManager."""
        if self._investigation_mgr is None:
            from codex.games.candela.investigations import InvestigationManager
            self._investigation_mgr = InvestigationManager()
        return self._investigation_mgr

    def _get_assignment_tracker(self) -> Any:
        """Lazily initialise and return the AssignmentTracker."""
        if self._assignment_tracker is None:
            from codex.games.candela.assignments import AssignmentTracker
            self._assignment_tracker = AssignmentTracker()
        return self._assignment_tracker

    def _get_phenomena_tracker(self) -> Any:
        """Lazily initialise and return the PhenomenaTracker."""
        if self._phenomena_tracker is None:
            from codex.games.candela.investigations import PhenomenaTracker
            self._phenomena_tracker = PhenomenaTracker()
        return self._phenomena_tracker

    # ── Party Management ───────────────────────────────────────────────

    def get_active_party(self) -> List[CandelaCharacter]:
        """Return only investigators who are not fully broken."""
        return [c for c in self.party if c.is_alive()]

    # ── Status ─────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dict suitable for Butler status display."""
        lead = self.party[0] if self.party else None
        mgr = self._investigation_mgr
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "role": lead.role if lead else None,
            "circle": self.circle_name,
            "assignments": self.assignments_completed,
            "active_case": (
                mgr.active_case.case_name
                if mgr and mgr.active_case and mgr.active_case.active
                else None
            ),
        }

    # ── Save / Load ────────────────────────────────────────────────────

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state for persistence."""
        state = super().save_state()
        state.update({
            "circle_name": self.circle_name,
            "assignments_completed": self.assignments_completed,
        })
        # WO-V2C: Persist investigation state if the manager was ever initialised
        if self._investigation_mgr is not None:
            state["investigation"] = self._investigation_mgr.to_dict()
        # WO-P4: Persist assignment and phenomena state
        state["assignment_tracker"] = (
            self._assignment_tracker.to_dict()
            if self._assignment_tracker is not None
            else None
        )
        state["phenomena_tracker"] = (
            self._phenomena_tracker.to_dict()
            if self._phenomena_tracker is not None
            else None
        )
        return state

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict."""
        from codex.core.services.fitd_engine import UniversalClock
        self.setting_id = data.get("setting_id", "")
        self.party = [CandelaCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.faction_clocks = [UniversalClock.from_dict(c)
                               for c in data.get("faction_clocks", [])]
        self.circle_name = data.get("circle_name", "")
        self.assignments_completed = data.get("assignments_completed", 0)
        # WO-V2C: Restore investigation state if present
        inv_data = data.get("investigation")
        if inv_data:
            from codex.games.candela.investigations import InvestigationManager
            self._investigation_mgr = InvestigationManager.from_dict(inv_data)
        # WO-P4: Restore assignment and phenomena trackers
        at_data = data.get("assignment_tracker")
        if at_data:
            from codex.games.candela.assignments import AssignmentTracker
            self._assignment_tracker = AssignmentTracker.from_dict(at_data)
        pt_data = data.get("phenomena_tracker")
        if pt_data:
            from codex.games.candela.investigations import PhenomenaTracker
            self._phenomena_tracker = PhenomenaTracker.from_dict(pt_data)

    # ── Setting-Filtered Accessors ─────────────────────────────────────

    def get_roles(self) -> dict:
        """Return roles filtered by active setting."""
        from codex.forge.reference_data.candela_roles import ROLES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(ROLES, self.setting_id)

    def get_phenomena(self) -> dict:
        """Return phenomena filtered by active setting."""
        from codex.forge.reference_data.candela_phenomena import PHENOMENA
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(PHENOMENA, self.setting_id)

    def get_circle_abilities(self) -> dict:
        """Return circle abilities filtered by active setting."""
        from codex.forge.reference_data.candela_circles import CIRCLE_ABILITIES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(CIRCLE_ABILITIES, self.setting_id)

    # =====================================================================
    # CANDELA-SPECIFIC COMMAND HANDLERS
    # =====================================================================

    # ── WO-P4: Assignment Phase handlers ──────────────────────────────

    def _cmd_start_assignment(self, **kwargs) -> str:
        """Start a new assignment with a name.

        Kwargs:
            name (str): Assignment name. Required.
        """
        name = kwargs.get("name", "")
        if not name:
            return "Specify assignment name."
        tracker = self._get_assignment_tracker()
        tracker.assignment_name = name
        tracker.current_phase = "hook"
        tracker.completed = False
        tracker.phase_notes = {"hook": [], "exploration": [], "climax": []}
        self._add_shard(f"Assignment started: {name}", "MASTER")
        return f"Assignment begun: {name}\nPhase: HOOK"

    def _cmd_advance_phase(self, **kwargs) -> str:
        """Advance to the next assignment phase."""
        tracker = self._get_assignment_tracker()
        result = tracker.advance_phase()
        if not result["success"]:
            return result["error"]
        self._add_shard(
            f"Assignment phase: {result['old_phase']} -> {result['new_phase']}",
            "ANCHOR",
        )
        return (
            f"Phase advanced: {result['old_phase'].upper()} -> "
            f"{result['new_phase'].upper()}"
        )

    def _cmd_complete_assignment(self, **kwargs) -> str:
        """Complete the current assignment."""
        tracker = self._get_assignment_tracker()
        result = tracker.complete()
        if not result["success"]:
            return result["error"]
        self.assignments_completed += 1
        self._add_shard(
            f"Assignment completed: {tracker.assignment_name}", "ANCHOR"
        )
        return (
            f"Assignment completed: {tracker.assignment_name}\n"
            f"Total assignments: {self.assignments_completed}"
        )

    def _cmd_assignment_status(self, **kwargs) -> str:
        """Show current assignment progress."""
        tracker = self._get_assignment_tracker()
        return tracker.get_summary()

    # ── WO-P4: Bleed escalation ───────────────────────────────────────

    def _cmd_bleed_escalation(self, **kwargs) -> str:
        """Check for bleed escalation across the circle.

        Compares total circle bleed against a threshold of 2 × party size.
        """
        total_bleed = sum(c.bleed for c in self.party)
        threshold = len(self.party) * 2
        if total_bleed >= threshold:
            self._add_shard(
                f"BLEED ESCALATION: total bleed {total_bleed} >= threshold {threshold}",
                "ANCHOR",
            )
            return (
                f"BLEED ESCALATION!\n"
                f"Total circle bleed: {total_bleed} >= threshold ({threshold})\n"
                f"The phenomena surges. All investigators take 1 brain mark."
            )
        return (
            f"Bleed check: {total_bleed}/{threshold}\n"
            f"The boundary holds — for now."
        )

    # ── WO-P4: Phenomena escalation handlers ─────────────────────────

    def _cmd_phenomena_status(self, **kwargs) -> str:
        """Show the current phenomena escalation status."""
        tracker = self._get_phenomena_tracker()
        return tracker.get_status()

    def _cmd_phenomena_tick(self, **kwargs) -> str:
        """Advance the phenomena escalation clock.

        Kwargs:
            amount (int): Ticks to add. Default 1.
        """
        amount = int(kwargs.get("amount", 1))
        tracker = self._get_phenomena_tracker()
        result = tracker.tick(amount)
        if result["advanced"]:
            self._add_shard(
                f"Phenomena escalated: {result['old_stage']} -> {result['new_stage']}",
                "ANCHOR",
            )
            return (
                f"PHENOMENA ESCALATION: {result['old_stage'].upper()} -> "
                f"{result['new_stage'].upper()}\n"
                f"Ticks: {result['ticks']}/{result['threshold']}"
            )
        return (
            f"Phenomena tick: {result['ticks']}/{result['threshold']} "
            f"({result['new_stage']})"
        )

    def _cmd_phenomena_reduce(self, **kwargs) -> str:
        """Reduce phenomena escalation (from containment).

        Kwargs:
            amount (int): Ticks to remove. Default 1.
        """
        amount = int(kwargs.get("amount", 1))
        tracker = self._get_phenomena_tracker()
        result = tracker.reduce(amount)
        return (
            f"Phenomena reduced: {result['old_ticks']} -> {result['new_ticks']} "
            f"ticks ({result['stage']})"
        )

    def _cmd_circle_status(self, **kwargs) -> str:
        lines = [f"Circle: {self.circle_name or 'Unnamed'}"]
        lines.append(f"Assignments Completed: {self.assignments_completed}")
        if self.party:
            lines.append("Members:")
            for c in self.party:
                role = c.role or "Unassigned"
                lines.append(f"  {c.name} ({role})")
        else:
            lines.append("  No investigators assigned.")
        return "\n".join(lines)

    def _cmd_take_mark(self, **kwargs) -> str:
        track = kwargs.get("track", "body")
        char = kwargs.get("character") or self.character
        if not char:
            return "No active character."
        result = char.take_mark(track)
        scarred_msg = " SCARRED!" if result["scarred"] else ""
        msg = (
            f"{char.name}: {track.title()} {result['old']} -> {result['new']}"
            f"/{getattr(char, f'{track}_max', 3)}{scarred_msg}"
        )
        if result["scarred"]:
            self._add_shard(
                f"{char.name} SCARRED on {track.title()} track",
                "CHRONICLE",
            )
        return msg

    def _cmd_party_status(self, **kwargs) -> str:
        lines = ["Investigator Tracks:"]
        for c in self.party:
            lines.append(
                f"  {c.name}: Body {c.body}/{c.body_max} | "
                f"Brain {c.brain}/{c.brain_max} | "
                f"Bleed {c.bleed}/{c.bleed_max}"
                f"{' [BROKEN]' if not c.is_alive() else ''}"
            )
        if not self.party:
            lines.append("  No investigators in circle.")
        return "\n".join(lines)

    # ── WO-V2C: Investigation handlers ────────────────────────────────

    def _cmd_open_case(self, **kwargs) -> str:
        """Open a new investigation case.

        Kwargs:
            case_name (str):    Human-readable name. Required.
            phenomena (str):    Phenomenon key. Optional.
            clues_needed (int): Clues required for illumination. Default 5.
        """
        case_name = kwargs.get("case_name", "")
        if not case_name:
            return "open_case requires 'case_name' kwarg."
        phenomena = kwargs.get("phenomena", "")
        clues_needed = int(kwargs.get("clues_needed", 5))
        mgr = self._get_investigation_mgr()
        case = mgr.open_case(case_name, phenomena=phenomena, clues_needed=clues_needed)
        self._add_shard(
            f"Case opened: '{case_name}' (phenomena: {phenomena or 'Unknown'}, "
            f"clues needed: {clues_needed})",
            "MASTER",
        )
        return (
            f"Case opened: '{case.case_name}'\n"
            f"Phenomenon: {case.phenomena or 'Unknown'}\n"
            f"Clues needed: {case.clues_needed}\n"
            f"Danger: {case.danger_level}"
        )

    def _cmd_investigate(self, **kwargs) -> str:
        """Perform an investigation roll.

        Kwargs:
            action (str):      Action attribute to roll (default 'survey').
            method (str):      Investigation method key (default 'survey').
            bonus_dice (int):  Extra dice. Default 0.
        """
        mgr = self._get_investigation_mgr()
        action = kwargs.get("action", "survey")
        method = kwargs.get("method", action)
        bonus = int(kwargs.get("bonus_dice", 0))
        char = self.character
        dots = (getattr(char, action, 0) if char else 0) + bonus
        result = mgr.investigate(action_dots=dots, method=method)
        if not result.get("success", True) and "error" in result:
            return f"Error: {result['error']}"

        lines = [f"[{method.upper()}] {result.get('outcome', '?').upper()}"]
        dice_str = ", ".join(str(d) for d in result.get("dice", []))
        lines.append(f"Dice: [{dice_str}]")
        lines.append(result.get("message", ""))

        case = result.get("case_status")
        if case:
            lines.append(
                f"Case: '{case['case_name']}' | "
                f"Clues: {case['clues_found']}/{case['clues_needed']} | "
                f"Danger: {case['danger_level']}"
            )
        if result.get("clue_found") and result.get("clue"):
            self._add_shard(
                f"Clue discovered via {method}: {result['clue'].get('description', '')}",
                "CHRONICLE",
            )
        return "\n".join(lines)

    def _cmd_gilded_move(self, **kwargs) -> str:
        """Use a role ability (gilded move).

        Kwargs:
            ability (str): Ability name. Required.
        """
        ability_name = kwargs.get("ability", "")
        if not ability_name:
            return "gilded_move requires 'ability' kwarg."
        char = self.character
        if not char:
            return "No active investigator."
        mgr = self._get_investigation_mgr()
        result = mgr.gilded_move(char, ability_name)
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        lines = [result.get("message", "")]
        marks = result.get("marks_applied", {})
        if marks:
            for track, info in marks.items():
                if info.get("scarred"):
                    lines.append(f"  SCARRED on {track.title()}!")
                    self._add_shard(
                        f"{char.name} SCARRED on {track.title()} using {ability_name}",
                        "CHRONICLE",
                    )
                else:
                    lines.append(
                        f"  {track.title()}: {info['old']} -> {info['new']}"
                        f"/{getattr(char, f'{track}_max', 3)}"
                    )
        return "\n".join(lines)

    def _cmd_illuminate(self, **kwargs) -> str:
        """Attempt to illuminate (resolve) the active case."""
        mgr = self._get_investigation_mgr()
        result = mgr.illuminate()
        if not result.get("success"):
            return f"Cannot illuminate: {result.get('error', 'Unknown error')}"

        illumination = result.get("illumination", {})
        dice_str = ", ".join(str(d) for d in result.get("dice", []))
        self.assignments_completed += 1
        self._add_shard(
            f"Case illuminated: {illumination.get('label', 'Resolved')}",
            "ANCHOR",
        )
        return (
            f"[ILLUMINATE] Dice: [{dice_str}] -> {result.get('roll_outcome', '?').upper()}\n"
            f"{illumination.get('label', '')}: {illumination.get('description', '')}"
        )

    def _cmd_case_status(self, **kwargs) -> str:
        """Show the current investigation case status."""
        mgr = self._get_investigation_mgr()
        if not mgr.active_case:
            return "No active case. Use open_case to begin an investigation."
        case = mgr.active_case
        lines = [
            f"Case: '{case.case_name}'",
            f"Phenomenon: {case.phenomena or 'Unknown'}",
            f"Status: {'Active' if case.active else 'Closed'}",
            f"Clues: {case.clues_found}/{case.clues_needed}",
            f"Verified: {mgr.clue_tracker.verified_count()}",
            f"Danger: {case.danger_level}/5",
        ]
        if case.outcome:
            lines.append(f"Outcome: {case.outcome}")
        return "\n".join(lines)

    def _cmd_clues(self, **kwargs) -> str:
        """List all clues collected in the current case."""
        mgr = self._get_investigation_mgr()
        clues = mgr.clue_tracker.clues
        if not clues:
            return "No clues collected yet."
        lines = [f"Clues ({len(clues)} total):"]
        for i, clue in enumerate(clues):
            status = "V" if clue.verified else "-"
            conn = f" [{clue.connected_phenomena}]" if clue.connected_phenomena else ""
            lines.append(f"  [{status}] {i}: {clue.description} (from: {clue.source}){conn}")
        return "\n".join(lines)

    def _cmd_danger_check(self, **kwargs) -> str:
        """Trigger a danger escalation check for the active case."""
        mgr = self._get_investigation_mgr()
        result = mgr.danger_escalation()
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        if result.get("dice"):
            dice_str = ", ".join(str(d) for d in result["dice"])
            return f"[DANGER CHECK] Dice: [{dice_str}]\n{result.get('message', '')}"
        return result.get("message", "")

    def _cmd_assignment(self, **kwargs) -> str:
        """Show current assignment/mission details.

        Returns active case summary if one exists, otherwise shows circle
        context and assignments completed so far.

        Returns:
            Human-readable string with mission/assignment details.
        """
        mgr = self._investigation_mgr
        lines = [f"Circle: {self.circle_name or 'Unnamed'}"]
        lines.append(f"Assignments completed: {self.assignments_completed}")
        if mgr and mgr.active_case and mgr.active_case.active:
            case = mgr.active_case
            lines.append("")
            lines.append(f"Active assignment: '{case.case_name}'")
            lines.append(f"Phenomenon: {case.phenomena or 'Unknown'}")
            lines.append(
                f"Clues: {case.clues_found}/{case.clues_needed} | "
                f"Danger: {case.danger_level}/5"
            )
            if mgr.clue_tracker.clues:
                lines.append("Recent clues:")
                for clue in mgr.clue_tracker.clues[-3:]:
                    verified = "V" if clue.verified else "-"
                    lines.append(f"  [{verified}] {clue.description[:60]}")
        else:
            lines.append("No active assignment. Use open_case to begin an investigation.")
        return "\n".join(lines)

    def _cmd_complication(self, **kwargs) -> str:
        """Roll a complication from the system's consequence table."""
        import random as _rng
        tier = max(1, min(4, kwargs.get("tier", 1)))
        # Candela uses assignments_completed as a rough pressure proxy
        effective_tier = min(4, tier + (1 if self.assignments_completed >= 3 else 0))
        pool = COMPLICATION_TABLE.get(effective_tier, COMPLICATION_TABLE[1])
        entry = _rng.choice(pool)
        self._add_shard(
            f"Complication ({entry['type']}): {entry['text']}",
            "CHRONICLE",
        )
        return f"COMPLICATION: {entry['text']}\nEffect: {entry.get('effect', 'none')}"

    def _cmd_build_trust(self, **kwargs) -> str:
        """Adjust trust with an NPC based on an action outcome.

        Kwargs:
            npc (str):    NPC name. Required.
            result (str): FITD outcome ('failure', 'mixed', 'success', 'critical').
        """
        npc = kwargs.get("npc", "")
        action_result = kwargs.get("result", "mixed")
        if not npc:
            return "build_trust requires 'npc' kwarg."
        mgr = self._get_investigation_mgr()
        trust_result = mgr.build_trust(npc, action_result)
        if trust_result.get("changed"):
            self._add_shard(
                f"Trust with {npc}: {trust_result['old_trust_name']} -> "
                f"{trust_result['new_trust_name']}",
                "CHRONICLE",
            )
            return (
                f"{npc}: Trust {trust_result['old_trust_name']} -> "
                f"{trust_result['new_trust_name']}"
            )
        return f"{npc}: Trust unchanged ({trust_result['new_trust_name']})"


# =========================================================================
# COMMAND DEFINITIONS
# =========================================================================

# =========================================================================
# COMPLICATION TABLE (Gap Fix: per-engine consequences)
# =========================================================================

COMPLICATION_TABLE: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"type": "mark_advance", "text": "A nagging headache intensifies. Something presses at the edge of perception.", "effect": "brain +1"},
        {"type": "phenomenon_manifestation", "text": "Objects rattle on the nearest shelf. A cold draft from nowhere.", "effect": "bleed +1"},
        {"type": "circle_strain", "text": "A contact grows distant, unsettled by your questions.", "effect": "trust -1"},
    ],
    2: [
        {"type": "mark_advance", "text": "Your hands tremble. A wound from a previous assignment reopens.", "effect": "body +1"},
        {"type": "bleed_escalation", "text": "The boundary between here and the other side thins. You hear whispers.", "effect": "bleed +1"},
        {"type": "phenomenon_manifestation", "text": "A glass shatters spontaneously. The shards arrange themselves into a symbol.", "effect": "danger +1"},
    ],
    3: [
        {"type": "mark_advance", "text": "Memories that aren't yours flood your mind. You lose minutes.", "effect": "brain +2"},
        {"type": "bleed_escalation", "text": "Blood seeps from the walls of the investigation site.", "effect": "bleed +2"},
        {"type": "circle_strain", "text": "An investigator's past catches up with them. A debt is called in.", "effect": "stress +3"},
        {"type": "phenomenon_manifestation", "text": "The phenomenon manifests briefly — a face in the mirror that isn't yours.", "effect": "danger +2"},
    ],
    4: [
        {"type": "mark_advance", "text": "Your body seizes. Something passes through you.", "effect": "body +2"},
        {"type": "bleed_escalation", "text": "The bleed tears open. Something reaches through.", "effect": "bleed +3"},
        {"type": "phenomenon_manifestation", "text": "The phenomenon fully manifests. Reality fractures around it.", "effect": "danger +3"},
    ],
}


CANDELA_COMMANDS = {
    # Existing (WO-V10.0)
    "roll_action":         "Roll a d6-pool action check",
    "circle_status":       "Show circle name and assignments",
    "take_mark":           "Mark damage on Body/Brain/Bleed",
    "party_status":        "Show all investigator resource tracks",
    "assignment":          "Show current assignment/mission details",
    # WO-V2C: Investigation
    "open_case":           "Open a new investigation case",
    "investigate":         "Perform an investigation roll to find clues",
    "gilded_move":         "Use a role ability (gilded move)",
    "illuminate":          "Attempt to resolve the active case",
    "case_status":         "Show active case details and clue count",
    "clues":               "List all discovered clues",
    "danger_check":        "Roll a danger escalation check",
    "build_trust":         "Adjust NPC trust level after an interaction",
    "complication":        "Roll a complication from the consequence table",
    # WO-P4: Assignment phase tracking
    "start_assignment":    "Start a new assignment (name=<str>)",
    "advance_phase":       "Advance to next assignment phase",
    "complete_assignment":  "Complete the current assignment",
    "assignment_status":   "Show assignment progress",
    # WO-P4: Bleed and phenomena
    "bleed_escalation":    "Check for bleed escalation across circle",
    "phenomena_status":    "Show phenomena escalation stage",
    "phenomena_tick":      "Advance phenomena escalation",
    "phenomena_reduce":    "Reduce phenomena escalation ticks",
    "fortune":             "Roll a Candela fortune die pool",
}

CANDELA_CATEGORIES = {
    "Circle":        ["circle_status", "party_status", "assignment"],
    "Action":        ["roll_action", "take_mark", "fortune"],
    "Investigation": [
        "open_case", "investigate", "case_status", "clues",
        "illuminate", "danger_check",
    ],
    "Roleplay":      ["gilded_move", "build_trust", "complication"],
    "Assignment":    [
        "start_assignment", "advance_phase", "complete_assignment",
        "assignment_status",
    ],
    "Phenomena":     [
        "phenomena_status", "phenomena_tick", "phenomena_reduce",
        "bleed_escalation",
    ],
}


# =========================================================================
# ENCOUNTER & LOCATION CONTENT (WO-V47.0)
# =========================================================================

ENCOUNTER_TABLE = [
    {"name": "Flickering Phenomenon", "description": "Reality stutters — objects duplicate, sounds echo wrong, shadows move independently.", "effect": "stress +1, 2-clock 'Manifestation'"},
    {"name": "Bleed Eruption", "description": "A wound in reality tears open. Things from the other side press against the membrane.", "effect": "4-clock 'Bleed Sealed', body marks on failure"},
    {"name": "Possessed Bystander", "description": "A civilian's eyes go black. They speak in a language that predates civilization.", "effect": "brain marks +1, engagement to subdue without harm"},
    {"name": "Memory Loop", "description": "The same thirty seconds repeat. Each iteration, something changes.", "effect": "stress +2, investigation opportunity"},
    {"name": "Thinning Veil", "description": "The air tastes of static. Compass needles spin. Animals flee.", "effect": "gilded die penalties, supernatural clues revealed"},
    {"name": "Omenborn Creature", "description": "Something that should not exist stands in the street, beautiful and terrible.", "effect": "body marks +2, 6-clock 'Containment'"},
]

LOCATION_DESCRIPTIONS = {
    "groundswell": [
        "Working-class streets where the gaslamps burn uneven. The factories never stop. Neither does the coughing.",
        "Brick tenements soot-stained and weary. Children play in alleys that smell of coal and old blood.",
    ],
    "briar_green": [
        "Manicured hedges and wrought-iron gates. The wealthy sleep behind wards they do not understand.",
        "A park at the district's center, always green, even in winter. The gardeners work in silence.",
    ],
    "hallowharbor": [
        "Salt air and the creak of moored ships. The lighthouse beam sweeps fog that never fully lifts.",
        "Fishmongers hawk their catch at dawn. By night, the harbor belongs to smugglers and worse.",
    ],
}


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("candela", CandelaEngine)
except ImportError:
    pass

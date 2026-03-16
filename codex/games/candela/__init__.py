"""
Candela Obscura -- Game Engine
===============================

Supernatural noir investigation using the Illuminated Worlds system.
Uses three resource tracks (Body, Brain, Bleed) instead of FITD stress.

Integrates with:
  - codex/core/services/fitd_engine.py for shared d6-pool mechanics
  - codex/forge/char_wizard.py via vault/ILLUMINATED_WORLDS/Candela_Obscura/creation_rules.json
  - codex/games/candela/investigations.py for clue/case management (WO-V2C)

Activated when a Candela Obscura campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from codex.core.services.narrative_loom import NarrativeLoomMixin


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

class CandelaEngine(NarrativeLoomMixin):
    """Core engine for Candela Obscura campaigns.

    Uses the Illuminated Worlds system with Body/Brain/Bleed tracks
    instead of standard FITD stress. Shares the d6-pool action roll
    and FactionClock from fitd_engine.

    WO-V2C: Adds InvestigationManager (lazy-init) for case and clue tracking.
    """

    system_id = "candela"
    system_family = "ILLUMINATED_WORLDS"
    display_name = "Candela Obscura"

    def __init__(self):
        from codex.core.services.fitd_engine import FactionClock  # noqa: F401
        self.character: Optional[CandelaCharacter] = None
        self.party: List[CandelaCharacter] = []
        self.circle_name: str = ""   # The investigative circle
        self.faction_clocks: List[Any] = []
        self.assignments_completed: int = 0
        self.setting_id: str = ""   # WO-V46.0: active sub-setting filter
        self._init_loom()
        # WO-V2C: Investigation subsystem (lazy-initialised)
        self._investigation_mgr: Optional[Any] = None

    # ── Lazy Accessor ──────────────────────────────────────────────────

    def _get_investigation_mgr(self) -> Any:
        """Lazily initialise and return the InvestigationManager."""
        if self._investigation_mgr is None:
            from codex.games.candela.investigations import InvestigationManager
            self._investigation_mgr = InvestigationManager()
        return self._investigation_mgr

    # ── Party Management ───────────────────────────────────────────────

    def create_character(self, name: str, **kwargs) -> CandelaCharacter:
        """Create a new investigator and make them the party lead."""
        setting_id = kwargs.pop("setting_id", self.setting_id)
        char = CandelaCharacter(name=name, **kwargs)
        char.setting_id = setting_id
        self.setting_id = setting_id
        self.character = char
        if not self.party:
            self.party = [char]
        else:
            self.party.append(char)
        self._add_shard(
            f"Circle investigator added: {name} ({char.role or 'Unassigned'})",
            "MASTER",
        )
        return char

    def add_to_party(self, char: CandelaCharacter) -> None:
        """Add an existing investigator to the active circle."""
        self.party.append(char)

    def remove_from_party(self, char: CandelaCharacter) -> None:
        """Remove an investigator from the active circle."""
        if char in self.party:
            self.party.remove(char)

    def get_active_party(self) -> List[CandelaCharacter]:
        """Return only investigators who are not fully broken."""
        return [c for c in self.party if c.is_alive()]

    # ── Action Roll ────────────────────────────────────────────────────

    def roll_action(self, character: Optional[CandelaCharacter] = None,
                    action: str = "survey", bonus_dice: int = 0, **kwargs) -> Any:
        """Roll a d6-pool action using the character's action dots.

        Args:
            character: The acting investigator (defaults to lead).
            action: Action attribute name (e.g. 'survey', 'strike').
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

        Candela uses Body/Brain/Bleed tracks rather than a StressClock,
        so this method returns an empty dict if no stress clock exists for
        the named character. Provided for interface parity with other FITD
        engines that share a stress-clock-based trauma path.

        Args:
            char_name: Name of the character whose stress clock to push.
            amount: Stress points to add.

        Returns:
            StressClock.push() result dict, or empty dict if no clock found.
        """
        clock = getattr(self, "stress_clocks", {}).get(char_name)
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
        clock = getattr(self, 'stress_clocks', {}).get(char.name) if char else None
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
        state: Dict[str, Any] = {
            "system_id": self.system_id,
            "setting_id": self.setting_id,
            "party": [c.to_dict() for c in self.party],
            "faction_clocks": [c.to_dict() for c in self.faction_clocks],
            "circle_name": self.circle_name,
            "assignments_completed": self.assignments_completed,
        }
        # WO-V2C: Persist investigation state if the manager was ever initialised
        if self._investigation_mgr is not None:
            state["investigation"] = self._investigation_mgr.to_dict()
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
    # COMMAND DISPATCHER
    # =====================================================================

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Dispatch a command string to the appropriate handler."""
        if cmd == "trace_fact":
            return self.trace_fact(kwargs.get("fact", ""))
        handler = getattr(self, f"_cmd_{cmd}", None)
        if handler:
            return handler(**kwargs)
        return f"Unknown command: {cmd}"

    # ── Existing handlers ──────────────────────────────────────────────

    def _cmd_roll_action(self, **kwargs) -> str:
        from codex.core.services.fitd_engine import format_roll_result
        result = self.roll_action(**kwargs)
        return format_roll_result(result)

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

CANDELA_COMMANDS = {
    # Existing (WO-V10.0)
    "roll_action":    "Roll a d6-pool action check",
    "circle_status":  "Show circle name and assignments",
    "take_mark":      "Mark damage on Body/Brain/Bleed",
    "party_status":   "Show all investigator resource tracks",
    # WO-V2C: Investigation
    "open_case":      "Open a new investigation case",
    "investigate":    "Perform an investigation roll to find clues",
    "gilded_move":    "Use a role ability (gilded move)",
    "illuminate":     "Attempt to resolve the active case",
    "case_status":    "Show active case details and clue count",
    "clues":          "List all discovered clues",
    "danger_check":   "Roll a danger escalation check",
    "build_trust":    "Adjust NPC trust level after an interaction",
}

CANDELA_CATEGORIES = {
    "Circle":        ["circle_status", "party_status"],
    "Action":        ["roll_action", "take_mark"],
    "Investigation": [
        "open_case", "investigate", "case_status", "clues",
        "illuminate", "danger_check",
    ],
    "Roleplay":      ["gilded_move", "build_trust"],
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

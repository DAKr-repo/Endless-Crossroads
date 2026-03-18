"""
Blades in the Dark -- Game Engine
==================================

Industrial fantasy heist game, the original Forged in the Dark system.
Crew-based play with faction clocks, turf, and heat mechanics.

Integrates with:
  - codex/core/services/fitd_engine.py for shared FITD mechanics
  - codex/forge/char_wizard.py via vault/FITD/bitd/creation_rules.json

Activated when a Blades in the Dark campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from codex.core.services.narrative_loom import NarrativeLoomMixin


# =========================================================================
# CHARACTER
# =========================================================================

@dataclass
class BitDCharacter:
    """A Blades in the Dark scoundrel."""
    name: str
    playbook: str = ""     # Cutter, Hound, Leech, Lurk, Slide, Spider, Whisper
    heritage: str = ""     # Akoros, Dagger Isles, Iruvia, Severos, Skovlan, Tycheros

    # Action dots (0-4 each, grouped by category)
    # Insight
    hunt: int = 0
    study: int = 0
    survey: int = 0
    tinker: int = 0
    # Prowess
    finesse: int = 0
    prowl: int = 0
    skirmish: int = 0
    wreck: int = 0
    # Resolve
    attune: int = 0
    command: int = 0
    consort: int = 0
    sway: int = 0

    vice: str = ""
    xp_marks: int = 0       # WO-V34.0: FITD advancement marks
    setting_id: str = ""    # WO-V46.0: sub-setting filter (e.g. "duskvol")

    def is_alive(self) -> bool:
        """FITD characters don't die from HP; always considered active."""
        return True

    def to_dict(self) -> dict:
        """Serialize to a plain dict for save/load."""
        return {
            "name": self.name, "playbook": self.playbook,
            "heritage": self.heritage, "vice": self.vice,
            "hunt": self.hunt, "study": self.study,
            "survey": self.survey, "tinker": self.tinker,
            "finesse": self.finesse, "prowl": self.prowl,
            "skirmish": self.skirmish, "wreck": self.wreck,
            "attune": self.attune, "command": self.command,
            "consort": self.consort, "sway": self.sway,
            "xp_marks": self.xp_marks,
            "setting_id": self.setting_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BitDCharacter":
        """Deserialize from a plain dict."""
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


# =========================================================================
# ENGINE
# =========================================================================

class BitDEngine(NarrativeLoomMixin):
    """Core engine for Blades in the Dark campaigns.

    Manages crew operations, faction relationships, and the score cycle.
    Tracks heat, wanted level, rep, coin, and turf as crew resources.
    """

    system_id = "bitd"
    system_family = "FITD"
    display_name = "Blades in the Dark"

    def __init__(self):
        from codex.core.services.fitd_engine import StressClock, FactionClock  # noqa: F401
        self.character: Optional[BitDCharacter] = None
        self.party: List[BitDCharacter] = []
        self.stress_clocks: Dict[str, Any] = {}
        self.faction_clocks: List[Any] = []
        self.crew_name: str = ""
        self.crew_type: str = ""   # Assassins, Bravos, Cult, Hawkers, Shadows, Smugglers
        self.heat: int = 0
        self.wanted_level: int = 0
        self.rep: int = 0
        self.coin: int = 2
        self.turf: int = 0
        # WO-V41.0: Subsystem state (lazy-initialized)
        self._score_state: Optional[Any] = None
        self._flashback_mgr: Optional[Any] = None
        self._bargain_tracker: Optional[Any] = None
        self._downtime_mgr: Optional[Any] = None
        self._init_loom()
        self.setting_id: str = ""   # WO-V46.0: active sub-setting filter

    def create_character(self, name: str, **kwargs) -> BitDCharacter:
        """Create a new scoundrel and make them the party lead."""
        setting_id = kwargs.pop("setting_id", self.setting_id)
        char = BitDCharacter(name=name, setting_id=setting_id, **kwargs)
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
            f"Crew founded. Lead: {name} ({char.playbook or 'Unknown'}). "
            f"Crew: {self.crew_name or 'Unnamed'} ({self.crew_type or 'Unknown'})",
            "MASTER",
        )
        return char

    def add_to_party(self, char: BitDCharacter) -> None:
        """Add an existing scoundrel to the active crew."""
        self.party.append(char)
        from codex.core.services.fitd_engine import StressClock
        self.stress_clocks[char.name] = StressClock()

    def remove_from_party(self, char: BitDCharacter) -> None:
        """Remove a scoundrel from the active crew."""
        if char in self.party:
            self.party.remove(char)
            self.stress_clocks.pop(char.name, None)

    def get_active_party(self) -> List[BitDCharacter]:
        """Return all current crew members."""
        return list(self.party)

    def roll_action(self, character: Optional[BitDCharacter] = None,
                    action: str = "skirmish", bonus_dice: int = 0, **kwargs) -> Any:
        """Roll an FITD action using the character's action dots.

        Args:
            character: The acting scoundrel (defaults to lead).
            action: Action attribute name (e.g. 'skirmish', 'prowl').
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
    # LAZY SUBSYSTEM ACCESSORS (WO-V41.0)
    # =====================================================================

    def _get_score_state(self) -> Any:
        """Return the active ScoreState, creating it on first access."""
        if self._score_state is None:
            from codex.games.bitd.scores import ScoreState
            self._score_state = ScoreState()
        return self._score_state

    def _get_flashback_mgr(self) -> Any:
        """Return the FlashbackManager, creating it on first access."""
        if self._flashback_mgr is None:
            from codex.games.bitd.scores import FlashbackManager
            self._flashback_mgr = FlashbackManager()
        return self._flashback_mgr

    def _get_bargain_tracker(self) -> Any:
        """Return the DevilsBargainTracker, creating it on first access."""
        if self._bargain_tracker is None:
            from codex.games.bitd.scores import DevilsBargainTracker
            self._bargain_tracker = DevilsBargainTracker()
        return self._bargain_tracker

    def _get_downtime_mgr(self) -> Any:
        """Return the DowntimeManager, creating it on first access."""
        if self._downtime_mgr is None:
            from codex.games.bitd.downtime import DowntimeManager
            self._downtime_mgr = DowntimeManager()
        return self._downtime_mgr

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dict suitable for Butler status display."""
        lead = self.party[0] if self.party else None
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "playbook": lead.playbook if lead else None,
            "crew": self.crew_name or "No Crew",
            "heat": self.heat,
            "coin": self.coin,
            "rep": self.rep,
        }

    # =====================================================================
    # SETTING-FILTERED ACCESSORS (WO-V46.0)
    # =====================================================================

    def get_playbooks(self) -> dict:
        """Return playbooks filtered by active setting."""
        from codex.forge.reference_data.bitd_playbooks import PLAYBOOKS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(PLAYBOOKS, self.setting_id)

    def get_heritages(self) -> dict:
        """Return heritages filtered by active setting."""
        from codex.forge.reference_data.bitd_playbooks import HERITAGES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(HERITAGES, self.setting_id)

    def get_factions(self) -> dict:
        """Return factions filtered by active setting."""
        from codex.forge.reference_data.bitd_factions import FACTIONS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(FACTIONS, self.setting_id)

    def get_crew_types(self) -> dict:
        """Return crew types filtered by active setting."""
        from codex.forge.reference_data.bitd_crew import CREW_TYPES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(CREW_TYPES, self.setting_id)

    def save_state(self) -> Dict[str, Any]:
        """Serialize full engine state for persistence."""
        return {
            "system_id": self.system_id,
            "setting_id": self.setting_id,
            "party": [c.to_dict() for c in self.party],
            "stress": {k: v.to_dict() for k, v in self.stress_clocks.items()},
            "faction_clocks": [c.to_dict() for c in self.faction_clocks],
            "crew_name": self.crew_name, "crew_type": self.crew_type,
            "heat": self.heat, "wanted_level": self.wanted_level,
            "rep": self.rep, "coin": self.coin, "turf": self.turf,
            # WO-V41.0: subsystem state
            "score_state": self._score_state.to_dict() if self._score_state else None,
            "flashback_mgr": self._flashback_mgr.to_dict() if self._flashback_mgr else None,
            "bargain_tracker": self._bargain_tracker.to_dict() if self._bargain_tracker else None,
            "downtime_mgr": self._downtime_mgr.to_dict() if self._downtime_mgr else None,
        }

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict."""
        from codex.core.services.fitd_engine import StressClock, UniversalClock
        self.setting_id = data.get("setting_id", "")
        self.party = [BitDCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.stress_clocks = {k: StressClock.from_dict(v)
                              for k, v in data.get("stress", {}).items()}
        self.faction_clocks = [UniversalClock.from_dict(c)
                               for c in data.get("faction_clocks", [])]
        self.crew_name = data.get("crew_name", "")
        self.crew_type = data.get("crew_type", "")
        self.heat = data.get("heat", 0)
        self.wanted_level = data.get("wanted_level", 0)
        self.rep = data.get("rep", 0)
        self.coin = data.get("coin", 2)
        self.turf = data.get("turf", 0)
        # WO-V41.0: restore subsystem state
        from codex.games.bitd.scores import ScoreState, FlashbackManager, DevilsBargainTracker
        from codex.games.bitd.downtime import DowntimeManager
        if data.get("score_state"):
            self._score_state = ScoreState.from_dict(data["score_state"])
        if data.get("flashback_mgr"):
            self._flashback_mgr = FlashbackManager.from_dict(data["flashback_mgr"])
        if data.get("bargain_tracker"):
            self._bargain_tracker = DevilsBargainTracker.from_dict(data["bargain_tracker"])
        if data.get("downtime_mgr"):
            self._downtime_mgr = DowntimeManager.from_dict(data["downtime_mgr"])

    # =====================================================================
    # COMMAND DISPATCHER (WO-V10.0)
    # =====================================================================

    _ENTANGLEMENT_FLAVORS = {
        0: [
            "The streets are quiet. No entanglement this time.",
            "The usual informants have nothing to report. A rare reprieve.",
            "Your crew's reputation keeps the vultures at bay — for now.",
        ],
        1: [
            "A gang demands a toll. Pay 1 coin or face trouble.",
            "A urchin delivers a note: 'We know where you sleep.' Probably bluffing.",
            "A former associate appears at your door, asking for a 'small favour.'",
        ],
        2: [
            "The Bluecoats are asking questions about your crew.",
            "A tavern keeper refuses to serve your people. Word is spreading.",
            "Someone has been following your Whisper through the ghost field.",
        ],
        3: [
            "A rival faction makes a move against your turf.",
            "Your best fence has been turned. The Bluecoats have your ledger.",
            "A fire breaks out in your territory. Arson, clearly. A message.",
        ],
        4: [
            "An informant sells your name. Wanted level rises.",
            "The Spirit Wardens knock on your lair door at midnight.",
            "A crewmate's vice lands them in the Bluecoat stockade.",
        ],
        5: [
            "The Inspectors raid a safehouse. Lose 1 coin.",
            "Your coin stash is discovered and seized. Someone talked.",
            "A demon-bound artifact in your vault activates. The walls bleed.",
        ],
        6: [
            "A demon takes notice. Something dark stirs.",
            "The Dimmer Sisters send a polite invitation. Refusal is not an option.",
            "A Leviathan surfaces in the canal by your lair. The city trembles.",
        ],
    }

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Dispatch a command string to the appropriate handler."""
        if cmd == "trace_fact":
            return self.trace_fact(kwargs.get("fact", ""))
        handler = getattr(self, f"_cmd_{cmd}", None)
        if handler:
            return handler(**kwargs)
        return f"Unknown command: {cmd}"

    def _cmd_roll_action(self, **kwargs) -> str:
        from codex.core.services.fitd_engine import format_roll_result
        result = self.roll_action(**kwargs)
        return format_roll_result(result)

    def _cmd_crew_status(self, **kwargs) -> str:
        return (
            f"Crew: {self.crew_name or 'Unnamed'} ({self.crew_type or 'Unknown'})\n"
            f"Heat: {self.heat} | Wanted: {self.wanted_level}\n"
            f"Coin: {self.coin} | Rep: {self.rep} | Turf: {self.turf}"
        )

    def _cmd_score_status(self, **kwargs) -> str:
        score = self._get_score_state()
        if not score.active:
            return "No active score. Use the engagement command to start one."
        return (
            f"Active Score: {score.target or 'Unknown target'}\n"
            f"Plan: {score.plan_type}\n"
            f"Engagement: {score.engagement_result}\n"
            f"Flashbacks: {score.flashbacks_used}\n"
            f"Bargains: {len(score.devils_bargains)}\n"
            f"Complications: {len(score.complications)}"
        )

    def _cmd_entanglement(self, **kwargs) -> str:
        import random
        import random as _rng
        roll = random.randint(1, 6)
        effective = min(6, roll + (1 if self.heat >= 4 else 0))
        flavors = self._ENTANGLEMENT_FLAVORS.get(effective, ["Strange forces are at work."])
        flavor = _rng.choice(flavors)
        self._add_shard(
            f"Entanglement roll: {roll} (effective: {effective}). {flavor}",
            "CHRONICLE",
        )
        return f"Entanglement Roll: {roll} (heat modifier: +{1 if self.heat >= 4 else 0})\n{flavor}"

    def _cmd_party_status(self, **kwargs) -> str:
        lines = ["Crew Members:"]
        for name, clock in self.stress_clocks.items():
            traumas = ", ".join(clock.traumas) if clock.traumas else "none"
            lines.append(f"  {name}: stress {clock.current_stress}/{clock.max_stress} | traumas: {traumas}")
        if not self.stress_clocks:
            lines.append("  No crew members registered.")
        return "\n".join(lines)

    # ─── WO-V41.0: Score Cycle Commands ───────────────────────────────

    def _cmd_engagement(self, **kwargs) -> str:
        """Roll engagement dice to begin a score and set the opening position."""
        from codex.games.bitd.scores import engagement_roll
        plan = kwargs.get("plan_type", "infiltration")
        result = engagement_roll(
            crew_tier=kwargs.get("crew_tier", 0),
            plan_type=plan,
            detail_bonus=kwargs.get("detail_bonus", 0),
            misc_bonus=kwargs.get("misc_bonus", 0),
            misc_penalty=kwargs.get("misc_penalty", 0),
        )
        score = self._get_score_state()
        score.active = True
        score.plan_type = plan
        score.engagement_result = result["result_key"]
        score.target = kwargs.get("target", "")
        self._add_shard(f"Score engaged: {plan} plan, result: {result['position']}", "CHRONICLE")
        return (
            f"Engagement Roll: {result['highest']} ({result['dice']})\n"
            f"Position: {result['position'].upper()}\n"
            f"{result['description']}"
        )

    def _cmd_flashback(self, **kwargs) -> str:
        """Use a flashback scene during a score, costing 0-2 stress."""
        mgr = self._get_flashback_mgr()
        desc = kwargs.get("description", "A flashback scene")
        complexity = kwargs.get("complexity", "simple")
        fb = mgr.use_flashback(desc, complexity)
        score = self._get_score_state()
        score.flashbacks_used += 1
        return f"Flashback ({complexity}): {desc}\nStress cost: {fb['stress_cost']}"

    def _cmd_devils_bargain(self, **kwargs) -> str:
        """Offer a Devil's Bargain — +1d in exchange for a complication."""
        tracker = self._get_bargain_tracker()
        category = kwargs.get("category", "")
        bargain = tracker.offer_bargain(category)
        return (
            f"Devil's Bargain ({bargain['category']}): {bargain['description']}\n"
            f"Accept for +1d to your next roll."
        )

    def _cmd_accept_bargain(self, **kwargs) -> str:
        """Accept the most recently offered Devil's Bargain."""
        tracker = self._get_bargain_tracker()
        bargain = tracker.accept_bargain()
        if bargain:
            score = self._get_score_state()
            score.devils_bargains.append(bargain["description"])
            return f"Bargain accepted: {bargain['description']}"
        return "No bargain to accept."

    def _cmd_resolve_score(self, **kwargs) -> str:
        """Resolve and end the active score, awarding rep/heat/coin."""
        from codex.games.bitd.scores import resolve_score
        score = self._get_score_state()
        if not score.active:
            return "No active score to resolve."
        result = resolve_score(
            score,
            crew_tier=kwargs.get("crew_tier", 0),
            target_tier=kwargs.get("target_tier", 0),
        )
        self.rep += result["rep_earned"]
        self.heat += result["heat_generated"]
        self.coin += result["coin_earned"]
        self._add_shard(f"Score resolved: {result['summary']}", "CHRONICLE")
        score.active = False
        return result["summary"]

    # ─── WO-V41.0: Extended Downtime Commands ──────────────────────────

    def _cmd_downtime_project(self, **kwargs) -> str:
        """Work on or create a long-term project during downtime."""
        mgr = self._get_downtime_mgr()
        name = kwargs.get("project_name", "")
        if not name:
            return "Specify project_name."
        if name not in mgr.projects:
            size = kwargs.get("clock_size", 8)
            mgr.create_project(name, kwargs.get("description", ""), size)
            return f"Project '{name}' created ({size}-clock)."
        result = mgr.work_on_project(name, kwargs.get("action_dots", 1))
        return result.get("description", str(result))

    def _cmd_downtime_acquire(self, **kwargs) -> str:
        """Acquire a temporary asset during downtime."""
        mgr = self._get_downtime_mgr()
        result = mgr.acquire_asset(
            crew_tier=kwargs.get("crew_tier", 0),
            quality_desired=kwargs.get("quality", 1),
        )
        return result.get("description", str(result))

    def _cmd_downtime_reduce_heat(self, **kwargs) -> str:
        """Spend a downtime activity to reduce crew heat."""
        mgr = self._get_downtime_mgr()
        result = mgr.reduce_heat(crew_tier=kwargs.get("crew_tier", 0))
        heat_reduced = result.get("heat_reduced", 0)
        self.heat = max(0, self.heat - heat_reduced)
        return result.get("description", str(result)) + f"\nCurrent heat: {self.heat}"

    def _cmd_downtime_recover(self, **kwargs) -> str:
        """Recover from harm during downtime."""
        mgr = self._get_downtime_mgr()
        result = mgr.recover(healer_dots=kwargs.get("healer_dots", 0))
        return result.get("description", str(result))

    def _cmd_downtime_train(self, **kwargs) -> str:
        """Train for XP in a chosen attribute during downtime."""
        mgr = self._get_downtime_mgr()
        result = mgr.train(kwargs.get("attribute", "playbook"))
        return result.get("description", str(result))

    # ─── WO-V67.0: Crew heat / rep / vice / downtime commands ─────────

    def _cmd_heat_status(self, **kwargs) -> str:
        """Show current heat level and wanted status with descriptive flavour.

        Returns:
            Human-readable string describing heat and wanted level.
        """
        heat_labels = {
            0: "Cold — no heat",
            1: "Warm — the Bluecoats are curious",
            2: "Hot — patrols are watching your territory",
            3: "Scorching — informants have talked",
            4: "Blazing — wanted posters are going up",
            5: "Infernal — the Inspectors are personally involved",
            6: "Wanted — the whole city is hunting your crew",
        }
        label = heat_labels.get(min(self.heat, 6), f"Heat {self.heat}")
        wanted_msg = (
            f"Wanted Level {self.wanted_level} — "
            + (
                "no extra scrutiny" if self.wanted_level == 0
                else "extra patrols on your turf" if self.wanted_level == 1
                else "guards shoot first on sight" if self.wanted_level >= 2
                else f"level {self.wanted_level}"
            )
        )
        return f"Heat: {self.heat}/6 — {label}\n{wanted_msg}"

    def _cmd_rep_status(self, **kwargs) -> str:
        """Show reputation, faction standings, and tier summary.

        Returns:
            Human-readable string with rep and faction clock overview.
        """
        rep_labels = ["Unknown", "Noticed", "Respected", "Feared", "Legendary"]
        rep_label = rep_labels[min(self.rep // 3, len(rep_labels) - 1)]
        lines = [
            f"Rep: {self.rep} ({rep_label}) | Turf: {self.turf} | Coin: {self.coin}",
            f"Crew: {self.crew_name or 'Unnamed'} ({self.crew_type or 'Unknown Type'})",
        ]
        if self.faction_clocks:
            lines.append("Faction Clocks:")
            for clock in self.faction_clocks:
                name = getattr(clock, "name", "?")
                current = getattr(clock, "current", 0)
                size = getattr(clock, "size", 4)
                lines.append(f"  {name}: {current}/{size}")
        return "\n".join(lines)

    def _cmd_entangle(self, **kwargs) -> str:
        """Roll for an entanglement complication after a score (2d6 table).

        Rolls 2d6. Higher result = lighter consequence.
          2-5:  Complication — serious trouble
          6-9:  Problem — manageable trouble
          10+:  Nothing — crew slipped away clean

        Returns:
            Human-readable result string.
        """
        import random as _rand
        d1 = _rand.randint(1, 6)
        d2 = _rand.randint(1, 6)
        total = d1 + d2
        if total <= 5:
            tier = "complication"
            msg = "Serious complication. Something bad follows you home."
        elif total <= 9:
            tier = "problem"
            msg = "A manageable problem. Deal with it before it escalates."
        else:
            tier = "nothing"
            msg = "The crew slipped away clean. No entanglement this time."
        self._add_shard(
            f"Entangle roll: {d1}+{d2}={total} ({tier})",
            "CHRONICLE",
        )
        return f"Entangle: [{d1}, {d2}] = {total} — {tier.upper()}\n{msg}"

    def _cmd_vice(self, **kwargs) -> str:
        """Roll stress relief via vice indulgence (1d6).

        On a roll of 6, the character overindulges (complication).

        Kwargs:
            character: Optional BitDCharacter to target (defaults to lead).

        Returns:
            Human-readable result string.
        """
        import random as _rand
        char = kwargs.get("character") or self.character
        if not char:
            return "No active character."
        clock = self.stress_clocks.get(char.name)
        if not clock:
            return f"No stress clock for {char.name}."
        roll = _rand.randint(1, 6)
        if roll == 6:
            msg = (
                f"{char.name} overindulges their vice ({char.vice or 'unknown'})! "
                "Stress cleared but complications arise."
            )
            # Clear all stress on overindulgence
            clock.current_stress = 0
        else:
            recovered = clock.recover(roll).get("recovered", roll)
            msg = (
                f"{char.name} indulges vice ({char.vice or 'unknown'}): "
                f"roll {roll}, recovered {recovered} stress. "
                f"Remaining: {clock.current_stress}/{clock.max_stress}"
            )
        return msg

    def _cmd_downtime(self, **kwargs) -> str:
        """List available downtime actions for the current crew.

        Returns:
            Human-readable list of downtime options with brief descriptions.
        """
        actions = [
            "  long_term_project — Work on a multi-segment clock project",
            "  recover          — Heal from harm (healer_dots=<int>)",
            "  reduce_heat      — Spend favors to lower crew heat",
            "  train            — Gain XP in an attribute (attribute=<str>)",
            "  acquire_asset    — Obtain a temporary asset",
            "  vice             — Indulge vice to recover stress",
            "  advance          — Spend accumulated XP marks",
            "  engagement       — Plan and roll engagement for next score",
        ]
        return (
            f"Downtime — {self.crew_name or 'crew'} has {self.rep} rep and "
            f"{self.coin} coin.\nAvailable actions:\n" + "\n".join(actions)
        )

    # ─── WO-V34.0: Downtime & Advancement ─────────────────────────────

    def _cmd_downtime_vice(self, **kwargs) -> str:
        """Downtime: vice indulgence for stress recovery."""
        import random
        char = kwargs.get("character") or self.character
        if not char:
            return "No character selected."
        clock = self.stress_clocks.get(char.name)
        if not clock:
            return f"No stress clock for {char.name}"
        recovery = random.randint(1, 6)
        info = clock.recover(recovery)
        msg = f"{char.name} indulges their vice ({char.vice or 'unknown'}). Recovered {info['recovered']} stress."
        if info.get("overindulged"):
            msg += " OVERINDULGENCE! Complications arise."
        return msg

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

    def _cmd_advance(self, **kwargs) -> str:
        """Mark XP for a character. 8 marks = playbook advance."""
        char = kwargs.get("character") or self.character
        trigger = kwargs.get("trigger", "")
        if not char:
            return "No character selected."
        char.xp_marks += 1
        if char.xp_marks >= 8:
            char.xp_marks -= 8
            self._add_shard(
                f"{char.name} achieved PLAYBOOK ADVANCE ({trigger})",
                "ANCHOR",
            )
            return f"{char.name} marks XP ({trigger}). PLAYBOOK ADVANCE! Choose a new ability."
        return f"{char.name} marks XP ({trigger}). {char.xp_marks}/8"


# =========================================================================
# COMMAND DEFINITIONS (WO-V10.0)
# =========================================================================

# =========================================================================
# COMPLICATION TABLE (Gap Fix: per-engine consequences)
# =========================================================================

COMPLICATION_TABLE: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"type": "faction_response", "text": "A street gang leaves a threatening note at your lair.", "effect": "heat +1"},
        {"type": "vice_exposure", "text": "Your vice gets you noticed by the wrong people.", "effect": "stress +1"},
        {"type": "bluecoat_raid", "text": "Bluecoats harass a crew associate at their workplace.", "effect": "coin -1"},
    ],
    2: [
        {"type": "faction_response", "text": "A rival faction sabotages one of your operations.", "effect": "rep -1"},
        {"type": "bluecoat_raid", "text": "A Bluecoat patrol stakes out your usual meeting spot.", "effect": "heat +2"},
        {"type": "ghost_manifestation", "text": "Spectral disturbances plague the neighborhood near your lair.", "effect": "stress +2"},
    ],
    3: [
        {"type": "faction_response", "text": "A powerful faction demands tribute or faces consequences.", "effect": "coin -2"},
        {"type": "bluecoat_raid", "text": "The Inspectors raid a safehouse. Evidence is seized.", "effect": "heat +3"},
        {"type": "ghost_manifestation", "text": "A vengeful ghost attacks a crew member in the night.", "effect": "stress +3"},
        {"type": "vice_exposure", "text": "Your vice dealer is arrested. Finding a new one costs extra.", "effect": "coin -1"},
    ],
    4: [
        {"type": "faction_response", "text": "A major faction declares open war on your crew.", "effect": "heat +4"},
        {"type": "bluecoat_raid", "text": "The Spirit Wardens themselves investigate your activities.", "effect": "wanted +1"},
        {"type": "ghost_manifestation", "text": "A demon takes notice of your crew's activities.", "effect": "stress +4"},
    ],
}


BITD_COMMANDS = {
    "roll_action": "Roll an FITD action check",
    "crew_status": "Show crew heat, coin, and rep",
    "score_status": "Show current score details",
    "entanglement": "Roll for entanglement complications",
    "heat_status": "Show heat level and wanted status",
    "rep_status": "Show reputation, faction standings, and turf",
    "entangle": "Roll 2d6 post-score entanglement (complication/problem/nothing)",
    "vice": "Vice indulgence stress relief (1d6; 6=overindulgence)",
    "downtime": "List available downtime actions",
    "party_status": "Show all crew members and stress",
    "downtime_vice": "Indulge vice to recover stress",
    "advance": "Mark XP toward playbook advance",
    # WO-V41.0: Score cycle depth commands
    "engagement": "Roll engagement to start a score",
    "flashback": "Use a flashback during a score",
    "devils_bargain": "Offer a Devil's Bargain for +1d",
    "accept_bargain": "Accept the offered Devil's Bargain",
    "resolve_score": "Resolve and end the active score",
    "downtime_project": "Work on a long-term project",
    "downtime_acquire": "Acquire a temporary asset",
    "downtime_reduce_heat": "Reduce crew heat",
    "downtime_recover": "Recover from harm",
    "downtime_train": "Train for XP",
    "complication": "Roll a complication from the consequence table",
}

BITD_CATEGORIES = {
    "Crew": ["crew_status", "score_status", "entanglement", "heat_status", "rep_status"],
    "Action": ["roll_action", "party_status"],
    "Score": ["engagement", "entangle", "flashback", "devils_bargain", "accept_bargain", "resolve_score", "complication"],
    "Downtime": [
        "vice", "downtime_vice", "advance", "downtime_project", "downtime_acquire",
        "downtime_reduce_heat", "downtime_recover", "downtime_train", "downtime",
    ],
}


# =========================================================================
# ENCOUNTER & LOCATION CONTENT (WO-V47.0)
# =========================================================================

ENCOUNTER_TABLE = [
    {"name": "Bluecoat Patrol", "description": "A squad of city watch on high alert.", "effect": "heat +1, 4-clock 'Escape'"},
    {"name": "Spirit Warden Procession", "description": "Hooded wardens escorting a bound ghost through the streets.", "effect": "stress +1, opportunity to acquire spirit essence"},
    {"name": "Dimmer Sisters Ritual", "description": "Cloaked figures chanting around a spectral flame in an alley.", "effect": "2-clock 'Disrupted Ritual', supernatural consequence on failure"},
    {"name": "Red Sash Ambush", "description": "Blades flash from doorways. The Red Sashes want blood.", "effect": "harm level 2, engagement roll to escape"},
    {"name": "Leviathan Hunter Return", "description": "A blood-soaked hunter staggers from the docks, raving about the deep.", "effect": "coin opportunity +2, faction clock 'Leviathan Sighting' advances"},
    {"name": "Gondolier Smugglers", "description": "A narrow boat slides through canal fog, cargo covered in oilcloth.", "effect": "coin opportunity, heat +1 if pursued"},
]

LOCATION_DESCRIPTIONS = {
    "crows_foot": [
        "Narrow streets choked with coal smoke and the stench of fish oil. Laundry lines crisscross overhead like a web.",
        "Gas lamps flicker against rain-slicked cobblestones. A Bluecoat whistle echoes three blocks away.",
    ],
    "charterhall": [
        "Grand facades of pale stone, stained dark by decades of electroplasmic smog. Students hurry past with leather satchels.",
        "The university bell tower looms through fog, its clock face glowing an unearthly blue.",
    ],
    "the_docks": [
        "Tar and brine and rotting timber. Cranes groan overhead, swinging cargo from leviathan-hunter ships.",
        "Oil-slicked water laps against barnacled pilings. Something large moves beneath the surface.",
    ],
    "six_towers": [
        "Crumbling tenements lean against each other like drunks. The smell of cheap gin and cheaper candles.",
        "A street shrine to the Forgotten Gods sits defaced with gang marks. Someone left fresh flowers anyway.",
    ],
    "whitecrown": [
        "Pristine gas-lit avenues patrolled by paired Bluecoats. The wealth here is old and the walls are high.",
        "Iron gates topped with electroplasmic coils guard estates where the city's rulers sleep soundly.",
    ],
}


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("bitd", BitDEngine)
except ImportError:
    pass

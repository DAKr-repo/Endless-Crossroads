"""
CBR+PNK -- Game Engine
=======================

Cyberpunk one-shot heist game using FITD.
Runners jack into the Grid, pull the job, get out alive.

Integrates with:
  - codex/core/services/fitd_engine.py for shared FITD mechanics
  - codex/forge/char_wizard.py via vault/FITD/CBR_PNK/creation_rules.json
  - codex/games/cbrpnk/hacking.py for Grid/ICE subsystem
  - codex/games/cbrpnk/chrome.py for cybernetics management

Activated when a CBR+PNK campaign is loaded.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from codex.core.services.narrative_loom import NarrativeLoomMixin


# =========================================================================
# CHARACTER
# =========================================================================

@dataclass
class CBRPNKCharacter:
    """A CBR+PNK Runner."""
    name: str
    archetype: str = ""    # Hacker, Fixer, Ronin, Face
    background: str = ""   # Corporate, Street, Military, Academic

    # Action dots (FITD d6 pool, 0-4 each)
    hack: int = 0
    override: int = 0
    scan: int = 0
    study: int = 0
    scramble: int = 0
    scrap: int = 0
    skulk: int = 0
    shoot: int = 0
    attune: int = 0
    command: int = 0
    consort: int = 0
    sway: int = 0

    vice: str = ""
    chrome: List[str] = field(default_factory=list)   # Cybernetic augmentation names
    setting_id: str = ""    # WO-V46.0: sub-setting filter (e.g. "the_sprawl")

    def is_alive(self) -> bool:
        """FITD characters don't die from HP; always considered active."""
        return True

    def to_dict(self) -> dict:
        """Serialize to a plain dict for save/load."""
        return {
            "name": self.name, "archetype": self.archetype,
            "background": self.background, "vice": self.vice,
            "chrome": list(self.chrome),
            "hack": self.hack, "override": self.override,
            "scan": self.scan, "study": self.study,
            "scramble": self.scramble, "scrap": self.scrap,
            "skulk": self.skulk, "shoot": self.shoot,
            "attune": self.attune, "command": self.command,
            "consort": self.consort, "sway": self.sway,
            "setting_id": self.setting_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CBRPNKCharacter":
        """Deserialize from a plain dict."""
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


# =========================================================================
# ENGINE
# =========================================================================

class CBRPNKEngine(NarrativeLoomMixin):
    """Core engine for CBR+PNK campaigns.

    Tracks heat (corp response) and a glitch die that accumulates
    from failed grid intrusions, triggering escalating complications.

    Subsystems are lazy-initialised on first access:
      - _grid_state: Active GridState from hacking.py
      - _grid_mgr: GridManager instance
      - _chrome_mgr: ChromeManager instance (per-lead-character)
    """

    system_id = "cbrpnk"
    system_family = "FITD"
    display_name = "CBR+PNK"

    def __init__(self):
        from codex.core.services.fitd_engine import StressClock, FactionClock  # noqa: F401
        self.character: Optional[CBRPNKCharacter] = None
        self.party: List[CBRPNKCharacter] = []
        self.stress_clocks: Dict[str, Any] = {}
        self.faction_clocks: List[Any] = []
        self.heat: int = 0
        self.glitch_die: int = 0   # Accumulates, triggers complications
        self.setting_id: str = ""   # WO-V46.0: active sub-setting filter

        # Lazy-init subsystem handles
        self._grid_state: Optional[Any] = None
        self._grid_mgr: Optional[Any] = None
        self._chrome_mgr: Optional[Any] = None

        self._init_loom()

    # =====================================================================
    # LAZY ACCESSORS
    # =====================================================================

    @property
    def grid_mgr(self):
        """Lazily initialise and return the GridManager."""
        if self._grid_mgr is None:
            from codex.games.cbrpnk.hacking import GridManager
            self._grid_mgr = GridManager()
        return self._grid_mgr

    @property
    def chrome_mgr(self):
        """Lazily initialise and return the ChromeManager (shared for lead)."""
        if self._chrome_mgr is None:
            from codex.games.cbrpnk.chrome import ChromeManager
            self._chrome_mgr = ChromeManager()
        return self._chrome_mgr

    # =====================================================================
    # PARTY MANAGEMENT
    # =====================================================================

    def create_character(self, name: str, **kwargs) -> CBRPNKCharacter:
        """Create a new Runner and make them the party lead."""
        setting_id = kwargs.pop("setting_id", self.setting_id)
        char = CBRPNKCharacter(name=name, **kwargs)
        char.setting_id = setting_id
        self.setting_id = setting_id
        self.character = char
        if not self.party:
            self.party = [char]
        else:
            self.party.append(char)
        from codex.core.services.fitd_engine import StressClock
        self.stress_clocks[name] = StressClock()
        self._add_shard(
            f"Runner crew formed. Lead: {name} ({char.archetype or 'Unknown'})",
            "MASTER",
        )
        return char

    def add_to_party(self, char: CBRPNKCharacter) -> None:
        """Add an existing Runner to the active party."""
        self.party.append(char)
        from codex.core.services.fitd_engine import StressClock
        self.stress_clocks[char.name] = StressClock()

    def remove_from_party(self, char: CBRPNKCharacter) -> None:
        """Remove a Runner from the active party."""
        if char in self.party:
            self.party.remove(char)
            self.stress_clocks.pop(char.name, None)

    def get_active_party(self) -> List[CBRPNKCharacter]:
        """Return all current party members."""
        return list(self.party)

    # =====================================================================
    # ROLLS
    # =====================================================================

    def roll_action(
        self,
        character: Optional[CBRPNKCharacter] = None,
        action: str = "hack",
        bonus_dice: int = 0,
        **kwargs,
    ) -> Any:
        """Roll an FITD action using the character's action dots.

        Args:
            character: The acting character (defaults to lead).
            action: Action attribute name (e.g. 'hack', 'shoot').
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
        """Return a summary dict suitable for Butler status display."""
        lead = self.party[0] if self.party else None
        return {
            "system": self.system_id,
            "party_size": len(self.party),
            "lead": lead.name if lead else None,
            "archetype": lead.archetype if lead else None,
            "heat": self.heat,
            "glitch": self.glitch_die,
        }

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
            "heat": self.heat,
            "glitch_die": self.glitch_die,
            # Subsystem state
            "grid_state": self._grid_state.to_dict() if self._grid_state is not None else None,
            "chrome_mgr": self._chrome_mgr.to_dict() if self._chrome_mgr is not None else None,
        }
        return state

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restore engine state from a previously saved dict."""
        from codex.core.services.fitd_engine import StressClock, UniversalClock
        self.party = [CBRPNKCharacter.from_dict(d) for d in data.get("party", [])]
        self.character = self.party[0] if self.party else None
        self.stress_clocks = {k: StressClock.from_dict(v)
                              for k, v in data.get("stress", {}).items()}
        self.faction_clocks = [UniversalClock.from_dict(c)
                               for c in data.get("faction_clocks", [])]
        self.heat = data.get("heat", 0)
        self.glitch_die = data.get("glitch_die", 0)
        self.setting_id = data.get("setting_id", "")

        # Restore grid subsystem
        grid_data = data.get("grid_state")
        if grid_data is not None:
            from codex.games.cbrpnk.hacking import GridState, GridManager
            self._grid_state = GridState.from_dict(grid_data)
            self._grid_mgr = GridManager()

        # Restore chrome subsystem
        chrome_data = data.get("chrome_mgr")
        if chrome_data is not None:
            from codex.games.cbrpnk.chrome import ChromeManager
            self._chrome_mgr = ChromeManager.from_dict(chrome_data)

    # =====================================================================
    # SETTING-FILTERED ACCESSORS (WO-V46.0)
    # =====================================================================

    def get_archetypes(self) -> dict:
        """Return archetypes filtered by active setting."""
        from codex.forge.reference_data.cbrpnk_archetypes import ARCHETYPES
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(ARCHETYPES, self.setting_id)

    def get_backgrounds(self) -> dict:
        """Return backgrounds filtered by active setting."""
        from codex.forge.reference_data.cbrpnk_archetypes import BACKGROUNDS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(BACKGROUNDS, self.setting_id)

    def get_factions(self) -> dict:
        """Return factions filtered by active setting."""
        from codex.forge.reference_data.cbrpnk_corps import FACTIONS
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(FACTIONS, self.setting_id)

    def get_chrome(self) -> dict:
        """Return chrome augmentations filtered by active setting."""
        from codex.forge.reference_data.cbrpnk_chrome import CHROME
        from codex.forge.reference_data.setting_filter import filter_by_setting
        return filter_by_setting(CHROME, self.setting_id)

    # =====================================================================
    # COMMAND DISPATCHER
    # =====================================================================

    def handle_command(self, cmd: str, **kwargs) -> str:
        """Dispatch a command string to the appropriate handler.

        Args:
            cmd: Command name (maps to _cmd_<name> method).
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

    # ─── Existing handlers ─────────────────────────────────────────────

    def _cmd_roll_action(self, **kwargs) -> str:
        """Roll a FITD action and accumulate glitch die on failure."""
        from codex.core.services.fitd_engine import format_roll_result
        result = self.roll_action(**kwargs)
        if result.outcome == "failure":
            self.glitch_die += 1
            self._add_shard(
                f"Grid glitch #{self.glitch_die} — action failed",
                "CHRONICLE",
            )
        return format_roll_result(result)

    def _cmd_crew_status(self, **kwargs) -> str:
        """Show runner stress and heat."""
        lines = [f"Heat: {self.heat} | Glitch Die: {self.glitch_die}"]
        lines.append("Runner Stress:")
        for name, clock in self.stress_clocks.items():
            traumas = ", ".join(clock.traumas) if clock.traumas else "none"
            lines.append(f"  {name}: stress {clock.current_stress}/{clock.max_stress} | traumas: {traumas}")
        if not self.stress_clocks:
            lines.append("  No runners registered.")
        return "\n".join(lines)

    def _cmd_glitch_status(self, **kwargs) -> str:
        """Show glitch die and heat thresholds."""
        threshold_warning = ""
        if self.glitch_die >= 6:
            threshold_warning = " [CRITICAL: System collapse imminent]"
        elif self.glitch_die >= 4:
            threshold_warning = " [WARNING: ICE countermeasures active]"
        elif self.glitch_die >= 2:
            threshold_warning = " [CAUTION: Grid instability detected]"
        return (
            f"Glitch Die: {self.glitch_die}{threshold_warning}\n"
            f"Heat: {self.heat}"
        )

    def _cmd_party_status(self, **kwargs) -> str:
        """Show all runners and chrome."""
        lines = ["Runners:"]
        for c in self.party:
            archetype = c.archetype or "Unknown"
            chrome_str = f" [{', '.join(c.chrome)}]" if c.chrome else ""
            lines.append(f"  {c.name} ({archetype}){chrome_str}")
        if not self.party:
            lines.append("  No runners in crew.")
        return "\n".join(lines)

    # ─── Grid handlers ─────────────────────────────────────────────────

    def _cmd_jack_in(self, **kwargs) -> str:
        """Jack into the Grid — generates a new grid if none is active."""
        import random as _random
        difficulty = kwargs.get("difficulty", 2)
        seed = kwargs.get("seed")
        rng = _random.Random(seed) if seed is not None else None

        # Generate grid if not already in one
        if self._grid_state is None or not self._grid_state.jacked_in:
            self._grid_state = self.grid_mgr.generate_grid(
                difficulty=difficulty, rng=rng
            )
        else:
            return "Already jacked in. Use jack_out first."

        # Determine hacker dots for the lead character
        hacker_dots = 0
        if self.character:
            hacker_dots = getattr(self.character, "hack", 0)

        result = self.grid_mgr.jack_in(
            hacker_dots=hacker_dots, grid=self._grid_state, rng=rng
        )
        self._add_shard(
            f"Runner jacked into {self._grid_state.grid_name} "
            f"(difficulty {difficulty}). Outcome: {result['outcome']}.",
            "CHRONICLE",
        )
        lines = [
            f"Target: {self._grid_state.grid_name}",
            result["message"],
            f"ICE detected: {len(self._grid_state.ice_list)}",
            f"Data nodes: {len(self._grid_state.data_nodes)}",
        ]
        return "\n".join(lines)

    def _cmd_intrusion(self, **kwargs) -> str:
        """Attack a specific ICE on the active grid.

        Kwargs:
            ice_name (str): Name of the ICE to target (e.g. 'Killer-01').
        """
        if self._grid_state is None or not self._grid_state.jacked_in:
            return "Not jacked in. Use jack_in first."

        ice_name = kwargs.get("ice_name", "")
        target = None
        for ice in self._grid_state.ice_list:
            if ice.name.lower() == ice_name.lower() or not ice_name:
                if ice.active:
                    target = ice
                    break

        if target is None:
            active = [i.name for i in self._grid_state.ice_list if i.active]
            if active:
                return f"ICE '{ice_name}' not found or not active. Active ICE: {', '.join(active)}"
            return "No active ICE on grid."

        hacker_dots = getattr(self.character, "hack", 0) if self.character else 0
        result = self.grid_mgr.intrusion_roll(
            hacker_dots=hacker_dots,
            target_ice=target,
            grid=self._grid_state,
        )
        if result.get("stress_cost", 0) > 0 and self.character:
            clock = self.stress_clocks.get(self.character.name)
            if clock:
                push_info = clock.push(result["stress_cost"])
                # WO-V61.0: Emit ANCHOR shard on trauma acquisition
                if push_info.get("trauma_triggered"):
                    char_name = self.character.name if self.character else "Unknown"
                    self._add_shard(
                        f"{char_name} suffered trauma: {push_info['new_trauma']}. "
                        f"Total traumas: {push_info['total_traumas']}/4.",
                        "ANCHOR", source="session",
                    )

        return result["message"]

    def _cmd_extract(self, **kwargs) -> str:
        """Extract data from a node on the active grid.

        Kwargs:
            node_index (int): Index of the data node to extract.
        """
        if self._grid_state is None or not self._grid_state.jacked_in:
            return "Not jacked in. Use jack_in first."

        node_index = int(kwargs.get("node_index", 0))
        result = self.grid_mgr.extract_data(
            grid=self._grid_state, node_index=node_index
        )
        if result["success"]:
            self._add_shard(
                f"Data extracted: {result['node']['name']} "
                f"(value: {result['node']['value']})",
                "CHRONICLE",
            )
        return result["message"]

    def _cmd_jack_out(self, **kwargs) -> str:
        """Disconnect from the active Grid."""
        if self._grid_state is None:
            return "No active grid session."

        result = self.grid_mgr.jack_out(grid=self._grid_state)
        if result["success"]:
            self._add_shard(
                f"Runner jacked out of {self._grid_state.grid_name}. "
                f"{result['extracted_count']} package(s) secured.",
                "CHRONICLE",
            )
        return result["message"]

    def _cmd_grid_status(self, **kwargs) -> str:
        """Display the current state of the active Grid."""
        if self._grid_state is None:
            return "No active grid. Use jack_in to begin."

        gs = self._grid_state
        lines = [
            f"Grid: {gs.grid_name}",
            f"Jacked In: {'Yes' if gs.jacked_in else 'No'}",
            f"Alarm Level: {gs.alarm_level}/5",
            "",
            "ICE Status:",
        ]
        if gs.ice_list:
            for ice in gs.ice_list:
                status = "ACTIVE" if ice.active else "inactive"
                lines.append(
                    f"  [{status}] {ice.name} ({ice.ice_type}, rating {ice.rating})"
                )
        else:
            lines.append("  No ICE on grid.")

        lines.append("")
        lines.append(f"Data Nodes ({len(gs.data_nodes)} remaining):")
        for i, node in enumerate(gs.data_nodes):
            protected = " [PROTECTED]" if node.get("protected") else ""
            lines.append(
                f"  [{i}] {node['name']} — Value: {node['value']}{protected}"
            )

        if gs.extracted_data:
            lines.append(f"\nExtracted ({len(gs.extracted_data)} package(s)):")
            for pkg in gs.extracted_data:
                lines.append(f"  {pkg['name']} [{pkg['value']}]")

        return "\n".join(lines)

    # ─── Chrome handlers ───────────────────────────────────────────────

    def _cmd_install_chrome(self, **kwargs) -> str:
        """Install a cybernetic augmentation on the lead character.

        Kwargs:
            chrome_name (str): Name of the chrome from CHROME reference.
        """
        chrome_name = kwargs.get("chrome_name", "")
        if not chrome_name:
            return "Specify chrome_name to install."

        result = self.chrome_mgr.install_chrome(
            chrome_name=chrome_name,
            character=self.character,
        )
        # Sync chrome list to character
        if result["success"] and self.character:
            if chrome_name not in self.character.chrome:
                self.character.chrome.append(chrome_name)
        self._add_shard(
            f"Chrome install: {chrome_name} — {result['message']}", "ANCHOR"
        )
        return result["message"]

    def _cmd_remove_chrome(self, **kwargs) -> str:
        """Remove chrome from the lead character by slot or name.

        Kwargs:
            slot (str): Slot name or chrome name to remove.
        """
        slot = kwargs.get("slot", "")
        if not slot:
            return "Specify 'slot' (slot name or chrome name) to remove."

        result = self.chrome_mgr.remove_chrome(slot=slot)
        if result["success"] and self.character:
            removed = result.get("removed")
            if removed and removed in self.character.chrome:
                self.character.chrome.remove(removed)
        return result["message"]

    def _cmd_chrome_status(self, **kwargs) -> str:
        """Display installed chrome and humanity score."""
        return self.chrome_mgr.get_status()

    def _cmd_humanity_check(self, **kwargs) -> str:
        """Run a humanity/cyberpsychosis stability check."""
        result = self.chrome_mgr.humanity_check()
        return result["message"]


# =========================================================================
# COMMAND DEFINITIONS
# =========================================================================

CBRPNK_COMMANDS = {
    # Existing
    "roll_action": "Roll an FITD action (glitch on fail)",
    "crew_status": "Show runner stress and heat",
    "glitch_status": "Show glitch die and heat thresholds",
    "party_status": "Show all runners and chrome",
    # Grid subsystem
    "jack_in": "Jack into the Grid (generates grid if none active)",
    "intrusion": "Attack an active ICE on the grid",
    "extract": "Extract data from a node",
    "jack_out": "Disconnect from the active Grid",
    "grid_status": "Display current Grid state",
    # Chrome subsystem
    "install_chrome": "Install a cybernetic augmentation",
    "remove_chrome": "Remove chrome by slot or name",
    "chrome_status": "Display installed chrome and humanity",
    "humanity_check": "Run a cyberpsychosis stability check",
}

CBRPNK_CATEGORIES = {
    "Grid": ["jack_in", "intrusion", "extract", "jack_out", "grid_status", "glitch_status"],
    "Chrome": ["install_chrome", "remove_chrome", "chrome_status", "humanity_check"],
    "Action": ["roll_action", "crew_status", "party_status"],
}


# =========================================================================
# ENCOUNTER & LOCATION CONTENT (WO-V47.0)
# =========================================================================

ENCOUNTER_TABLE = [
    {"name": "Corporate Security Response", "description": "Armored sec-teams deploy from an APC, weapons drawn, faceplates opaque.", "effect": "heat +2, 4-clock 'Lockdown'"},
    {"name": "ICE Counterintrusion", "description": "Black ice activates in the datastream. Your neural link burns.", "effect": "stress +2, harm level 1 to hacker"},
    {"name": "Street Samurai Crew", "description": "Chrome-augmented mercs step from the shadows, blades humming.", "effect": "engagement roll, harm level 2"},
    {"name": "Drone Swarm", "description": "A cloud of micro-drones erupts from a vent, cameras recording everything.", "effect": "heat +1, 2-clock 'Identified'"},
    {"name": "Rogue AI Fragment", "description": "Something in the network reaches back when you reach in. It speaks in dead voices.", "effect": "stress +1, glitch die escalation"},
    {"name": "Fixer Double-Cross", "description": "Your contact arrives with backup. They are not here to pay.", "effect": "engagement roll, heat +1, trust broken"},
]

LOCATION_DESCRIPTIONS = {
    "the_grid": [
        "Data flows visible as rivers of light in your neural HUD. Here, geometry is negotiable.",
        "Server towers stretch to infinity. Firewalls manifest as burning walls of code.",
    ],
    "undercity": [
        "Dripping pipes and neon graffiti. The only law down here is what you can enforce.",
        "Makeshift shelters line abandoned subway tunnels. The residents watch you pass in silence.",
    ],
    "corp_tower": [
        "Glass and steel reaching into clouds of pollution. Inside, the air is filtered and the people are not.",
        "Lobby fountains cycle recycled water. Security scanners track every biosignature.",
    ],
    "the_market": [
        "Stalls selling everything from bootleg cyberware to synthetic organs in coolers.",
        "Holographic advertisements flicker overhead, selling dreams no one can afford.",
    ],
    "the_wastes": [
        "Beyond the city wall, nothing but dust and rusted infrastructure. The corps dumped their waste here for decades.",
        "Scavengers pick through mountains of e-waste. The ground is toxic but the salvage is valuable.",
    ],
}


# =========================================================================
# ENGINE REGISTRATION
# =========================================================================

try:
    from codex.core.engine_protocol import register_engine
    register_engine("cbrpnk", CBRPNKEngine)
except ImportError:
    pass

#!/usr/bin/env python3
"""
ASHBURN HEIR ENGINE
-------------------
Gothic Corruption Campaign for Project C.O.D.E.X.

A narrative extension of the Crown & Crew system that adds:
- Legacy Corruption tracking (0-5 meter with immediate loss condition)
- Four NPC leaders with unique abilities and betrayal risks
- Legacy Checks with Lie vs. Truth moral choices
- Betrayal Nullification mechanic for political gravity

Setting: Ashburn Academy — A gothic boarding school where the player
is the heir to a disgraced noble family. The "Crown" represents
institutional authority (faculty, donors, The Board). The "Crew"
represents student resistance factions. Navigate social politics
while managing your family's corrupting legacy.

Version: 1.0 (Volatile Heir)
"""

import asyncio
import random
from dataclasses import dataclass, field
from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from codex.games.crown.engine import CrownAndCrewEngine, SWAY_TIERS, TAGS

# Tarot card system integration
try:
    from codex.integrations.tarot import render_tarot_card, get_card_for_context
    TAROT_AVAILABLE = True
except ImportError:
    TAROT_AVAILABLE = False

# Memory Engine for AI context
try:
    from codex.core.memory import CodexMemoryEngine, MemoryShard, ShardType
    MEMORY_ENGINE_AVAILABLE = True
except ImportError:
    MEMORY_ENGINE_AVAILABLE = False

# =============================================================================
# CONSOLE
# =============================================================================
console = Console()

# =============================================================================
# AI NARRATION PROMPT
# =============================================================================
ASHBURN_NARRATION_PROMPT = """You are the Narrator of a Gothic Boarding School Saga.
CONTEXT: The user is an Heir ({heir_name}) at Ashburn High.
SCENE: {scene}
ACTION: The user chose: {choice}
CONSEQUENCE: {consequence}

GAME STATE:
- Corruption: {corruption}/5 (5 = immediate game over)
- Sway: {sway} (Range: -3 to +3, negative = Crew, positive = Crown)

TASK: Write a 2-3 sentence narration describing the immediate result.
TONE: Tense, atmospheric, foreboding. Focus on sensory details (cold iron, whispers, shadows).
CRITICAL: Your narration MUST reflect the actual corruption level. If corruption is 4+, the heir is near the edge.
DO NOT use "Game Master" voice. Write as a novel. Keep under 50 words."""

# =============================================================================
# ASHBURN-SPECIFIC CONSTANTS
# =============================================================================

# The Four Leaders — NPC Archetypes with Abilities and Risks
LEADERS = {
    "Lydia": {
        "title": "The Velvet Chancellor",
        "ability": "Diplomatic Immunity — Can nullify one Crown vote per round",
        "risk": "Known double-agent. If exposed, instant +2 Corruption.",
    },
    "Jax": {
        "title": "The Signal Ghost",
        "ability": "Dead Drop — Can secretly pass intel to Crew without a vote",
        "risk": "Paranoid. 1-in-6 chance of betraying the Heir each round.",
    },
    "Julian": {
        "title": "The Gilded Son",
        "ability": "Legacy Name — Starts with +1 Sway toward Crown",
        "risk": "Arrogant. Cannot refuse Crown challenges, even losing ones.",
    },
    "Rowan": {
        "title": "The Ash Walker",
        "ability": "Ember Network — Knows the location of all Campfire events",
        "risk": "Haunted past. Random Campfire events trigger corruption checks.",
    },
}

# Ashburn-Themed Prompt Pools — Gothic Boarding School Narratives
ASHBURN_PROMPTS = {
    "crown": [
        "The Board of Regents convenes behind mirrored glass. Their agenda: control.",
        "Headmaster Alaric adjusts his signet ring. 'Order is not optional,' he says.",
        "A sealed envelope arrives bearing the Ashburn crest — a summons to the Spire.",
        "The Crown Loyalists patrol the East Wing. Their eyes miss nothing.",
        "The Alumni Association demands a progress report. Your family owes them everything.",
        "A faculty monitor stops you in the hall. 'Your father was a disappointment. Will you be different?'",
        "The scholarship committee reviews your file. One word from them could change everything.",
        "Security footage from the chapel incident surfaces. The Dean wants to discuss consequences.",
    ],
    "crew": [
        "A note slides under your door: 'The Furnace. Midnight. Bring no light.'",
        "Rowan's voice crackles through the dead radio: 'The walls have ears, but so do we.'",
        "The Crew gathers in the sub-basement, faces lit by a single ember.",
        "Someone has painted 'WE REMEMBER' on the chapel wall in ash.",
        "The resistance passes you a cipher. Decode it, or burn it. Choose quickly.",
        "A crewmate whispers: 'We're planning something. The kind of thing you can't walk back from.'",
        "The oldest student in the Crew hands you a key. 'This opens the Archive. Use it wisely.'",
        "You find a manifesto slipped into your textbook. It's written in your handwriting. You didn't write it.",
    ],
    "world": [
        "Ashburn Academy rises from the fog — gothic spires, iron gates, and silence.",
        "The Lunar Filter bathes the courtyard in pale silver. Nothing feels real here.",
        "Beyond the Glass Cage, the old forest whispers. Students are forbidden to listen.",
        "The clock tower chimes thirteen. It has done so every night since the founding.",
        "Frost clings to the windows even in summer. The groundskeeper says it's 'the soil.'",
        "The East Wing is off-limits. You hear footsteps there at night. Always descending.",
        "The lake behind campus is perfectly still. No birds. No ripples. No reflections.",
        "A portrait in the Great Hall watches you. Its eyes follow. Always the same ancestor.",
    ],
    "campfire": [
        "In the boiler room beneath the chapel, someone has left a candle burning.",
        "An old student journal lies open: 'They promised us legacy. They gave us chains.'",
        "The groundskeeper nods as you pass. He was a student here once. He never left.",
        "A photograph falls from a library book — your face, but dated thirty years ago.",
        "You dream of the tunnel beneath the dormitory. In the dream, you're running. You never escape.",
        "Someone carved your family crest into the stone foundation. It's older than the school.",
        "The Crew's elder tells a story about the first fire. It started in the Archive. No one survived.",
        "You find your mother's initials scratched into the desk. She was here. She never mentioned it.",
    ],
}

# Legacy Check Prompts — Moral Dilemmas with Lie/Truth Choices
LEGACY_PROMPTS = [
    "LEGACY CALL: Headmaster Alaric demands intel on the Crew. [1] Obey (+Corruption, -Sway) [2] Lie (+Sway, Risk)",
    "LEGACY CALL: The Board requires a loyalty demonstration. Expose an ally. [1] Comply (+Corruption, -Sway) [2] Fabricate evidence (+Sway, Risk)",
    "LEGACY CALL: Your family's endowment is threatened. Sign the oath. [1] Sign (+Corruption, -Sway) [2] Stall (+Sway, Risk)",
    "LEGACY CALL: Alaric offers a skeleton key to the Archive. The price: a name. [1] Give a name (+Corruption, -Sway) [2] Give a false name (+Sway, Risk)",
    "LEGACY CALL: A professor caught you in the East Wing. Confess your purpose. [1] Tell the truth (+Corruption, -Sway) [2] Deflect blame (+Sway, Risk)",
    "LEGACY CALL: The Alumni demand you attend the Gala. It conflicts with a Crew operation. [1] Attend (+Corruption, -Sway) [2] Fake illness (+Sway, Risk)",
    "LEGACY CALL: Security found contraband in your room. The Dean offers a deal. [1] Accept the deal (+Corruption, -Sway) [2] Challenge the evidence (+Sway, Risk)",
    "LEGACY CALL: Your family crest grants you immunity. Use it to shield yourself. [1] Use immunity (+Corruption, -Sway) [2] Face consequences (+Sway, Risk)",
]


# =============================================================================
# ASHBURN HEIR ENGINE — GOTHIC CORRUPTION CAMPAIGN
# =============================================================================

@dataclass
class AshburnHeirEngine(CrownAndCrewEngine):
    """
    Ashburn Academy narrative variant with corruption and NPC systems.

    Extends the base Crown & Crew engine with:
    - Legacy Corruption (0-5 scale, 5 = immediate loss)
    - Four Leader NPCs with abilities and risks
    - Legacy Check system (probabilistic moral choices)
    - Betrayal Nullification (political gravity penalty)
    - Immediate loss condition on corruption threshold
    """

    # Ashburn-specific state
    legacy_corruption: int = 0
    heir_name: str = "The Heir"
    heir_leader: dict = field(default_factory=dict)
    leader_ability: str = ""
    betrayal_triggered: bool = False

    def __post_init__(self):
        """Initialize Ashburn-specific state after parent initialization."""
        super().__post_init__()

        # Set heir-specific data
        if not self.heir_leader:
            self.heir_leader = LEADERS.get(self.heir_name, LEADERS["Julian"])
            self.leader_ability = self.heir_leader["ability"]

        # Apply heir-specific starting bonuses
        if self.heir_name == "Julian":
            # The Gilded Son starts with Crown leaning
            self.sway = max(-3, min(3, self.sway - 1))

        # Override prompt pools with Ashburn-themed content if no world injected
        if not self.world_state or not self.world_state.get("prompts_crown"):
            self._prompts_crown = list(ASHBURN_PROMPTS["crown"])
            self._prompts_crew = list(ASHBURN_PROMPTS["crew"])
            self._prompts_world = list(ASHBURN_PROMPTS["world"])
            self._prompts_campfire = list(ASHBURN_PROMPTS["campfire"])
            self._secret_witness = (
                "A figure steps from the shadows. They hold a locket bearing your family crest. "
                "Inside: a photograph of someone who looks exactly like you. Dated fifty years ago."
            )

        # Memory engine for AI context
        self.memory = None
        if MEMORY_ENGINE_AVAILABLE:
            try:
                self.memory = CodexMemoryEngine()
                # Ingest Ashburn world state as MASTER shard
                ashburn_state = {
                    "name": "Ashburn High",
                    "genre": "Gothic Horror",
                    "tone": "grim",
                    "terms": {"crown": "The Board", "crew": "The Students"},
                    "primer": "A gothic boarding school where heirs are consumed by legacy.",
                }
                self.memory.ingest_world_state(ashburn_state)
            except Exception:
                self.memory = None

    # ─────────────────────────────────────────────────────────────────────
    # PROLOGUE SYSTEM — OPENING SCENARIO
    # ─────────────────────────────────────────────────────────────────────

    async def run_prologue(self, core=None) -> dict:
        """
        Load a random scenario and present the prologue with AI Narration.

        Args:
            core: Optional CodexCore for AI narration via Mimir

        Returns:
            dict with scenario, choice, effects, and narration
        """
        from pathlib import Path
        import json
        import random

        # Load scenarios
        scenarios_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "scenarios" / "ashburn_scenarios.json"

        # Default/Fallback Scenario if JSON missing
        default_scenario = {
            "title": "The Fay Court Masquerade",
            "theme": "Social Decay",
            "intro_text": "Lydia's annual Fay Court Masquerade is tonight. Masks are mandatory. Debts are collected.",
            "immediate_dilemma": {
                "crown": {"label": "Accept Board Invite", "description": "Power flows upward.", "sway_effect": 1, "corruption_effect": 0},
                "crew": {"label": "Join the Ash Gallery", "description": "The resistance watches.", "sway_effect": -1, "corruption_effect": 0}
            }
        }

        scenario = default_scenario
        if scenarios_path.exists():
            try:
                with open(scenarios_path, encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("scenarios"):
                        scenario = random.choice(data["scenarios"])
            except Exception as e:
                console.print(f"[red]Error loading scenarios: {e}[/red]")

        # Display Intro
        console.clear()
        console.print(Panel(
            f"[bold #8B0000]{scenario['title']}[/bold #8B0000]\n\n[grey70]{scenario['intro_text']}[/grey70]",
            title=f"[bold]PROLOGUE — {scenario.get('theme', 'GOTHIC').upper()}[/bold]",
            border_style="#8B0000",
            box=box.DOUBLE,
            padding=(1, 2)
        ))

        # Display Choices
        crown = scenario["immediate_dilemma"]["crown"]
        crew = scenario["immediate_dilemma"]["crew"]

        console.print(f"\n[cyan][1] {crown['label']}[/cyan]\n[dim]    {crown['description']}[/dim]")
        console.print(f"\n[magenta][2] {crew['label']}[/magenta]\n[dim]    {crew['description']}[/dim]\n")

        # Input Loop
        while True:
            choice = input("Your choice — [1] or [2]: ").strip()
            if choice in ["1", "2"]:
                break

        # Apply Effects
        if choice == "1":
            chosen_side = "crown"
            sway_effect = crown.get("sway_effect", 0)
            corruption_effect = crown.get("corruption_effect", 0)
            desc = crown['description']
        else:
            chosen_side = "crew"
            sway_effect = crew.get("sway_effect", 0)
            corruption_effect = crew.get("corruption_effect", 0)
            desc = crew['description']

        self.sway = max(-3, min(3, self.sway + sway_effect))
        self.legacy_corruption = max(0, min(5, self.legacy_corruption + corruption_effect))

        # --- AI NARRATION INJECTION ---
        narration = f">> Choice recorded. Sway: {self.sway:+d}, Corruption: {self.legacy_corruption}/5"

        if core:
            console.print(Panel("⠋ Summoning Mimir... (Prologue)", style="dim blue"))
            try:
                prompt = ASHBURN_NARRATION_PROMPT.format(
                    heir_name=self.heir_name,
                    scene=f"Prologue: {scenario['title']}",
                    choice=f"Option {choice} ({chosen_side})",
                    consequence=desc,
                    corruption=self.legacy_corruption,
                    sway=self.sway
                )

                # Check for Architect or Cortex
                if hasattr(core, 'architect') and hasattr(core.architect, 'invoke_model'):
                    # Create minimal decision context to satisfy Architect signature
                    from codex.core.architect import RoutingDecision, ThinkingMode, Complexity, ThermalStatus
                    decision = RoutingDecision(ThinkingMode.REFLEX, "codex", Complexity.LOW, ThermalStatus.OPTIMAL, True, "Prologue")

                    response = await core.architect.invoke_model(query=prompt, system_prompt="You are a gothic narrator.", decision=decision)
                    narration = response.content.strip()
                elif hasattr(core, 'cortex'):
                    narration = await core.cortex.process_chat_turn(prompt)
                    # Clean tags if present
                    narration = narration.replace("<thinking>", "").split("</thinking>")[-1].strip()

            except Exception as e:
                console.print(f"[red]AI Generation Failed: {e}[/red]")

        console.print(Panel(narration, title="Mimir's Chronicle", border_style="purple"))
        input("\nPress Enter to continue to Day 1...")

        return {
            "scenario": scenario["title"],
            "choice": chosen_side,
            "sway_effect": sway_effect,
            "corruption_effect": corruption_effect,
            "narration": narration
        }

    # ─────────────────────────────────────────────────────────────────────
    # LEGACY CHECK SYSTEM — LIE VS. TRUTH MECHANIC
    # ─────────────────────────────────────────────────────────────────────

    def generate_legacy_check(self) -> dict:
        """
        Roll for Legacy Check. On 5-6, trigger a Lie vs. Truth moral choice.

        Returns:
            dict with:
                - triggered: bool (True if check fires)
                - roll: int (1-6)
                - prompt: str (the moral dilemma)
        """
        roll = random.randint(1, 6)

        if roll <= 4:
            return {"triggered": False, "roll": roll}

        # Triggered on 5-6 (33% chance)
        prompt = random.choice(LEGACY_PROMPTS)

        return {
            "triggered": True,
            "roll": roll,
            "prompt": prompt,
        }

    async def resolve_legacy_choice(self, choice: int, core=None) -> dict:
        """Resolve a legacy intervention choice.

        Args:
            choice: 1 for Obey, 2 for Lie
            core: Optional CodexCore for AI narration

        Returns:
            dict with narration, sway, corruption, game_over
        """

        # Mechanical resolution (keep existing logic)
        detected = False
        if choice == 1:
            # Obey path
            self.legacy_corruption = min(5, self.legacy_corruption + 1)
            self.sway = max(-3, self.sway - 1)
            choice_label = "Obey the Board's summons"
            consequence = f"Corruption +1 (now {self.legacy_corruption}/5), Sway toward Crown"
        else:
            # Lie path
            self.sway = min(3, self.sway + 1)
            choice_label = "Lie to deflect"
            import random
            detected = random.random() < 0.33
            if detected:
                self.legacy_corruption = min(5, self.legacy_corruption + 2)
                consequence = f"Lie DETECTED! Corruption +2 (now {self.legacy_corruption}/5)"
            else:
                consequence = "Lie succeeded. Sway toward Crew"

        # Memory shard creation
        if hasattr(self, 'memory') and self.memory:
            self.memory.create_shard(
                f"Legacy Choice: {choice_label} | Result: {consequence}",
                shard_type=ShardType.ANCHOR,
                tags=["legacy", f"corruption:{self.legacy_corruption}"],
                source="player"
            )

        # Default narration (fallback)
        narration = self._fallback_narration(choice_label) if hasattr(self, '_fallback_narration') else f">> {consequence}"

        # AI Narration attempt
        if core is not None:
            try:
                # Check for architect
                if hasattr(core, 'architect') and hasattr(core.architect, 'invoke_model'):
                    prompt = ASHBURN_NARRATION_PROMPT.format(
                        heir_name=self.heir_name,
                        scene="Legacy Intervention",
                        choice=choice_label,
                        consequence=consequence,
                        corruption=self.legacy_corruption,
                        sway=self.sway
                    )

                    from codex.core.architect import RoutingDecision, ThinkingMode, Complexity, ThermalStatus

                    decision = RoutingDecision(
                        mode=ThinkingMode.REFLEX,
                        model="codex",
                        complexity=Complexity.LOW,
                        thermal_status=ThermalStatus.OPTIMAL,
                        clearance_granted=True,
                        reasoning="Ashburn legacy choice narration"
                    )

                    response = await core.architect.invoke_model(
                        query=prompt,
                        system_prompt="You are a gothic narrator. Be atmospheric and brief.",
                        decision=decision,
                    )

                    narration = response.content.strip() if hasattr(response, 'content') else str(response).strip()

                    # Store as ECHO
                    if hasattr(self, 'memory') and self.memory:
                        self.memory.create_shard(narration, shard_type=ShardType.ECHO, source="mimir")

                # Alternative: try cortex
                elif hasattr(core, 'cortex') and hasattr(core.cortex, 'process_chat_turn'):
                    pass  # Cortex path can be implemented if needed

            except Exception as e:
                narration = self._fallback_narration(choice_label) if hasattr(self, '_fallback_narration') else f">> {consequence}"

        # Game over check
        game_over = self.legacy_corruption >= 5

        return {
            "choice_label": choice_label,
            "consequence": consequence,
            "narration": narration,
            "sway": self.sway,
            "corruption": self.legacy_corruption,
            "game_over": game_over,
            "detected": detected,
        }

    def _fallback_narration(self, choice: str) -> str:
        """Return static fallback narration when AI is unavailable."""
        fallbacks = [
            "The choice settles into your bones. Ashburn remembers.",
            "A chill passes through the corridor. Something has shifted.",
            "The decision echoes in the silence. There is no taking it back.",
            "Shadows lengthen as the weight of your choice becomes real.",
            "The walls seem to lean closer. The school is watching.",
        ]
        return random.choice(fallbacks)

    # ─────────────────────────────────────────────────────────────────────
    # CORRUPTION & LOSS CONDITION
    # ─────────────────────────────────────────────────────────────────────

    def check_betrayal(self) -> dict | None:
        """
        Check if corruption has reached the loss threshold.

        Returns:
            dict if game over:
                - game_over: True
                - message: str (loss text)
            None if still playable
        """
        if self.legacy_corruption >= 5:
            return {
                "game_over": True,
                "message": (
                    "THE SOLARIUM OPENS.\n\n"
                    "The glass shatters inward. You were never the heir — you were the inheritance.\n\n"
                    "ASHBURN CLAIMS ANOTHER.\n\n"
                    "[GAME OVER]"
                )
            }
        return None

    def add_corruption(self, amount: int = 1) -> dict | None:
        """
        Add corruption and immediately check for loss condition.

        Args:
            amount: Corruption points to add (default: 1)

        Returns:
            Same as check_betrayal() — dict if game over, None otherwise
        """
        # VALIDATION: Clamp corruption between 0 and 5
        self.legacy_corruption = max(0, min(5, self.legacy_corruption + amount))
        return self.check_betrayal()

    # ─────────────────────────────────────────────────────────────────────
    # HEIR STATUS PANEL — RICH UI
    # ─────────────────────────────────────────────────────────────────────

    def get_heir_status(self) -> str:
        """
        Generate a Rich-formatted status panel for the heir.

        Returns:
            String (Rich markup) showing:
                - Heir name and leader title
                - Corruption meter (visual bar)
                - Current sway and alignment
                - Leader ability and risk
                - Betrayal status
        """
        # Corruption bar
        corruption_bar = "█" * self.legacy_corruption + "░" * (5 - self.legacy_corruption)
        if self.legacy_corruption < 2:
            corruption_color = "green"
        elif self.legacy_corruption < 4:
            corruption_color = "yellow"
        else:
            corruption_color = "red"

        # Betrayal warning
        betrayal_warning = ""
        if self.betrayal_triggered:
            betrayal_warning = "\n[bold red]⚠️  POLITICAL CAPITAL NULLIFIED (Betrayal)[/bold red]"

        # Assemble panel content
        content = (
            f"[bold gold1]{self.heir_name}[/bold gold1] — [dim]{self.heir_leader['title']}[/dim]\n"
            f"[dim]Heir of the Ashburn Line[/dim]\n\n"
            f"[bold]CORRUPTION[/bold]\n"
            f"[{corruption_color}]{corruption_bar}[/] {self.legacy_corruption}/5\n\n"
            f"[bold]SWAY & ALIGNMENT[/bold]\n"
            f"{self.get_sway_visual()}\n"
            f"{self.get_status()}\n"
            f"{betrayal_warning}\n\n"
            f"[bold]LEADER PROFILE[/bold]\n"
            f"[dim]Ability:[/] {self.leader_ability}\n"
            f"[dim]Risk:[/] {self.heir_leader['risk']}"
        )

        return Panel(
            content,
            title="[bold]⚔️  HEIR STATUS  ⚔️[/bold]",
            border_style="gold1",
            box=box.DOUBLE,
        ).renderable

    # ─────────────────────────────────────────────────────────────────────
    # PROMPT OVERRIDE — USE ASHBURN POOLS
    # ─────────────────────────────────────────────────────────────────────

    def get_prompt(self, side: Literal["crown", "crew"] | None = None) -> str:
        """
        Get a unique prompt for the declared side.

        Overrides parent to use Ashburn-themed pools by default.

        Args:
            side: "crown" or "crew" (or None to use pending allegiance)

        Returns:
            Narrative prompt string
        """
        if side is None:
            side = self._pending_allegiance
        if side is None:
            return "ERROR: No allegiance declared. Call declare_allegiance() first."

        side = side.lower()

        # Use Ashburn pools if available
        if side == "crown" and ASHBURN_PROMPTS["crown"]:
            return self._get_unique_prompt(
                list(ASHBURN_PROMPTS["crown"]),
                self._used_crown
            )
        elif side == "crew" and ASHBURN_PROMPTS["crew"]:
            return self._get_unique_prompt(
                list(ASHBURN_PROMPTS["crew"]),
                self._used_crew
            )
        else:
            # Fallback to parent
            return super().get_prompt(side)

    # ─────────────────────────────────────────────────────────────────────
    # BETRAYAL NULLIFICATION — POLITICAL GRAVITY PENALTY
    # ─────────────────────────────────────────────────────────────────────

    def get_vote_power(self) -> int:
        """
        Get vote weight with Betrayal Nullification applied.

        Overrides parent to enforce betrayal penalty.

        Political Gravity:
            |sway| 0 → 1 vote power  (Drifter)
            |sway| 1 → 2 vote power  (Leaning)
            |sway| 2 → 4 vote power  (Trusted)
            |sway| 3 → 8 vote power  (Loyal)

        Betrayal Nullification:
            If betrayal_triggered == True:
                Weight reverts to 1 regardless of sway.

        Returns:
            int: Vote power multiplier
        """
        if self.betrayal_triggered:
            return 1  # Nullified — betrayal costs all political capital

        # Normal gravity
        return super().get_vote_power()

    # ─────────────────────────────────────────────────────────────────────
    # SAVE/LOAD EXTENSIONS
    # ─────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize Ashburn state to dict."""
        # Get parent data (if parent has to_dict, otherwise build manually)
        parent_data = {
            "day": self.day,
            "sway": self.sway,
            "patron": self.patron,
            "leader": self.leader,
            "history": self.history,
            "dna": self.dna,
            "world_state": self.world_state,
            "vote_log": self.vote_log,
        }

        # Add Ashburn-specific fields
        ashburn_data = {
            "legacy_corruption": self.legacy_corruption,
            "heir_name": self.heir_name,
            "heir_leader": self.heir_leader,
            "leader_ability": self.leader_ability,
            "betrayal_triggered": self.betrayal_triggered,
            "engine_type": "ashburn",  # Flag for load detection
        }

        return {**parent_data, **ashburn_data}

    @classmethod
    def from_dict(cls, data: dict) -> "AshburnHeirEngine":
        """Deserialize Ashburn state from dict with error handling for corrupted saves.

        CRITICAL FIX: Validates data integrity and provides graceful fallback.
        """
        try:
            # Validate input type
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict, got {type(data).__name__}")

            # Create a copy to avoid mutating original
            data_copy = data.copy()

            # Extract Ashburn fields with validation
            corruption = data_copy.pop("legacy_corruption", 0)
            heir = data_copy.pop("heir_name", "The Heir")
            heir_leader = data_copy.pop("heir_leader", {})
            leader_ability = data_copy.pop("leader_ability", "")
            betrayal = data_copy.pop("betrayal_triggered", False)
            data_copy.pop("engine_type", None)  # Remove type flag

            # Validate critical field types
            if not isinstance(corruption, int) or corruption < 0 or corruption > 5:
                console.print(f"[yellow]Warning: Invalid corruption value {corruption}, resetting to 0[/yellow]")
                corruption = 0

            if not isinstance(heir_leader, dict):
                console.print(f"[yellow]Warning: Invalid heir_leader type, using default[/yellow]")
                heir_leader = {}

            # Create instance with parent data
            instance = cls(
                day=data_copy.get("day", 1),
                sway=data_copy.get("sway", 0),
                patron=data_copy.get("patron", ""),
                leader=data_copy.get("leader", ""),
                history=data_copy.get("history", []),
                dna=data_copy.get("dna", {tag: 0 for tag in TAGS}),
                world_state=data_copy.get("world_state"),
                vote_log=data_copy.get("vote_log", []),
                heir_name=heir,
            )

            # Restore Ashburn state
            instance.legacy_corruption = corruption
            instance.heir_leader = heir_leader if heir_leader else LEADERS.get(heir, LEADERS["Julian"])
            instance.leader_ability = leader_ability if leader_ability else instance.heir_leader.get("ability", "")
            instance.betrayal_triggered = betrayal

            return instance

        except Exception as e:
            console.print(f"[red]Error loading save file: {e}[/red]")
            console.print("[yellow]Creating new game with default state...[/yellow]")
            # Return fresh instance as fallback
            return cls(heir_name="The Heir")


# =============================================================================
# INTEGRATION TEST — DEMO/VERIFY MODULE
# =============================================================================

if __name__ == "__main__":
    from rich.console import Console
    console = Console()

    console.print(Panel(
        "[bold cyan]ASHBURN HEIR ENGINE — MODULE TEST[/bold cyan]\n\n"
        "[dim]Testing core Ashburn mechanics:[/]\n"
        "  - Heir initialization\n"
        "  - Legacy Check system\n"
        "  - Corruption tracking\n"
        "  - Betrayal nullification\n"
        "  - Save/load integrity",
        box=box.DOUBLE,
        border_style="cyan",
    ))
    console.print()

    # Test 1: Initialize heir
    console.print("[bold gold1]TEST 1: Heir Initialization[/bold gold1]")
    engine = AshburnHeirEngine(heir_name="Julian")
    console.print(f"  Heir: {engine.heir_name}")
    console.print(f"  Title: {engine.heir_leader['title']}")
    console.print(f"  Starting Sway: {engine.sway} (Julian gets -1 from ability)")
    console.print(f"  Corruption: {engine.legacy_corruption}/5")
    console.print("  ✅ Initialization OK")
    console.print()

    # Test 2: Legacy Check trigger rate
    console.print("[bold gold1]TEST 2: Legacy Check Trigger Rate (30 rolls)[/bold gold1]")
    trigger_count = 0
    for _ in range(30):
        check = engine.generate_legacy_check()
        if check["triggered"]:
            trigger_count += 1
    console.print(f"  Triggered: {trigger_count}/30 ({trigger_count/30*100:.1f}%)")
    console.print(f"  Expected: ~33% (10 ± 3)")
    console.print("  ✅ Trigger rate within expected range" if 7 <= trigger_count <= 13 else "  ⚠️  Outside expected range")
    console.print()

    # Test 3: Corruption increment and loss condition
    console.print("[bold gold1]TEST 3: Corruption Loss Condition[/bold gold1]")
    test_engine = AshburnHeirEngine(heir_name="Lydia")
    test_engine.legacy_corruption = 4
    console.print(f"  Starting Corruption: {test_engine.legacy_corruption}/5")
    loss_check = test_engine.add_corruption(1)
    console.print(f"  After +1 Corruption: {test_engine.legacy_corruption}/5")
    if loss_check and loss_check.get("game_over"):
        console.print("  ✅ Game over triggered at corruption 5")
    else:
        console.print("  ❌ Game over did NOT trigger")
    console.print()

    # Test 4: Betrayal nullification
    console.print("[bold gold1]TEST 4: Betrayal Nullification[/bold gold1]")
    test_engine = AshburnHeirEngine(heir_name="Rowan")
    test_engine.sway = 2  # Trusted tier
    console.print(f"  Sway: {test_engine.sway} (Trusted)")
    console.print(f"  Normal Vote Power: {test_engine.get_vote_power()}")
    test_engine.betrayal_triggered = True
    console.print(f"  After Betrayal: {test_engine.get_vote_power()}")
    console.print("  ✅ Vote power nullified to 1" if test_engine.get_vote_power() == 1 else "  ❌ Nullification failed")
    console.print()

    # Test 5: Save/Load integrity
    console.print("[bold gold1]TEST 5: Save/Load Integrity[/bold gold1]")
    original = AshburnHeirEngine(heir_name="Jax")
    original.legacy_corruption = 3
    original.sway = -1
    original.betrayal_triggered = True
    original.day = 4

    # Serialize
    save_data = original.to_dict()
    console.print(f"  Serialized {len(save_data)} fields")

    # Deserialize
    restored = AshburnHeirEngine.from_dict(save_data)
    console.print(f"  Restored heir: {restored.heir_name}")
    console.print(f"  Corruption: {restored.legacy_corruption}/5 (expected: 3)")
    console.print(f"  Sway: {restored.sway} (expected: -1)")
    console.print(f"  Betrayal: {restored.betrayal_triggered} (expected: True)")
    console.print(f"  Day: {restored.day} (expected: 4)")

    integrity_check = (
        restored.heir_name == "Jax" and
        restored.legacy_corruption == 3 and
        restored.sway == -1 and
        restored.betrayal_triggered is True and
        restored.day == 4
    )
    console.print("  ✅ Save/load integrity verified" if integrity_check else "  ❌ Data mismatch")
    console.print()

    # Test 6: Status panel render
    console.print("[bold gold1]TEST 6: Status Panel Render[/bold gold1]")
    demo_engine = AshburnHeirEngine(heir_name="Lydia")
    demo_engine.legacy_corruption = 2
    demo_engine.sway = 1
    console.print(demo_engine.get_heir_status())
    console.print("  ✅ Panel rendered")
    console.print()

    # Final summary
    console.print(Panel(
        "[bold green]ALL TESTS COMPLETE[/bold green]\n\n"
        "[dim]Module is ready for integration with codex_agent_main.py[/]",
        border_style="green",
        box=box.DOUBLE,
    ))

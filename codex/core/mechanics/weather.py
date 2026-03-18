"""
WeatherEngine — Procedural weather simulation with terrain-aware transitions.
=============================================================================

Provides a Markov-chain weather state machine keyed to terrain type.
Each tick the engine decrements a duration counter; when it reaches zero a
weighted random transition picks the next weather state.

Mechanical modifiers (get_modifier()) expose stat adjustments to the game
loop so that combat and exploration are affected by conditions.

Usage::

    from codex.core.mechanics.weather import WeatherEngine, WeatherState

    w = WeatherEngine(terrain_type="forest")
    changed = w.advance()   # returns flavor text or None
    mods = w.get_modifier() # {"ranged": -1, ...}
    print(w.flavor_text())
    save_data["weather"] = w.to_dict()
    w2 = WeatherEngine.from_dict(save_data["weather"])
"""

from __future__ import annotations

import random
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Weather states
# ---------------------------------------------------------------------------

class WeatherState(Enum):
    """Discrete weather conditions."""
    CLEAR = "clear"
    OVERCAST = "overcast"
    RAIN = "rain"
    STORM = "storm"
    FOG = "fog"
    SNOW = "snow"
    HEAT = "heat"
    WIND = "wind"


# ---------------------------------------------------------------------------
# Transition tables
# ---------------------------------------------------------------------------

# Format: {from_state: [(to_state, weight), ...]}
# Weights are relative — they do NOT need to sum to 100.
TERRAIN_TRANSITIONS: Dict[str, Dict[WeatherState, List[Tuple[WeatherState, int]]]] = {
    "forest": {
        WeatherState.CLEAR:    [(WeatherState.CLEAR, 60),    (WeatherState.OVERCAST, 40)],
        WeatherState.OVERCAST: [(WeatherState.OVERCAST, 30), (WeatherState.RAIN, 50),    (WeatherState.CLEAR, 20)],
        WeatherState.RAIN:     [(WeatherState.RAIN, 40),     (WeatherState.STORM, 20),   (WeatherState.OVERCAST, 40)],
        WeatherState.STORM:    [(WeatherState.STORM, 20),    (WeatherState.RAIN, 50),    (WeatherState.OVERCAST, 30)],
        WeatherState.FOG:      [(WeatherState.FOG, 40),      (WeatherState.CLEAR, 40),   (WeatherState.OVERCAST, 20)],
    },
    "mountain": {
        WeatherState.CLEAR:    [(WeatherState.CLEAR, 50),    (WeatherState.WIND, 30),    (WeatherState.OVERCAST, 20)],
        WeatherState.WIND:     [(WeatherState.WIND, 30),     (WeatherState.SNOW, 40),    (WeatherState.CLEAR, 30)],
        WeatherState.SNOW:     [(WeatherState.SNOW, 35),     (WeatherState.STORM, 25),   (WeatherState.WIND, 40)],
        WeatherState.STORM:    [(WeatherState.STORM, 20),    (WeatherState.SNOW, 40),    (WeatherState.WIND, 40)],
    },
    "swamp": {
        WeatherState.FOG:      [(WeatherState.FOG, 60),      (WeatherState.RAIN, 40)],
        WeatherState.RAIN:     [(WeatherState.RAIN, 40),     (WeatherState.FOG, 40),     (WeatherState.STORM, 20)],
        WeatherState.CLEAR:    [(WeatherState.FOG, 60),      (WeatherState.OVERCAST, 30), (WeatherState.CLEAR, 10)],
    },
    "coast": {
        WeatherState.CLEAR:    [(WeatherState.CLEAR, 40),    (WeatherState.WIND, 40),    (WeatherState.OVERCAST, 20)],
        WeatherState.WIND:     [(WeatherState.WIND, 30),     (WeatherState.RAIN, 40),    (WeatherState.CLEAR, 30)],
        WeatherState.RAIN:     [(WeatherState.RAIN, 30),     (WeatherState.STORM, 30),   (WeatherState.WIND, 40)],
    },
    # Dungeons have no weather — engine never transitions
    "dungeon": {},
    "urban": {
        WeatherState.CLEAR:    [(WeatherState.CLEAR, 50),    (WeatherState.OVERCAST, 30), (WeatherState.HEAT, 20)],
        WeatherState.OVERCAST: [(WeatherState.OVERCAST, 30), (WeatherState.RAIN, 40),    (WeatherState.CLEAR, 30)],
        WeatherState.RAIN:     [(WeatherState.RAIN, 40),     (WeatherState.STORM, 20),   (WeatherState.OVERCAST, 40)],
    },
}

# Fallback transition table used when terrain type is unknown or a state has
# no entry in the terrain-specific table.
_DEFAULT_TRANSITIONS: Dict[WeatherState, List[Tuple[WeatherState, int]]] = {
    WeatherState.CLEAR:    [(WeatherState.CLEAR, 60),    (WeatherState.OVERCAST, 30), (WeatherState.WIND, 10)],
    WeatherState.OVERCAST: [(WeatherState.OVERCAST, 30), (WeatherState.RAIN, 40),    (WeatherState.CLEAR, 30)],
    WeatherState.RAIN:     [(WeatherState.RAIN, 40),     (WeatherState.CLEAR, 30),   (WeatherState.STORM, 15),   (WeatherState.OVERCAST, 15)],
    WeatherState.STORM:    [(WeatherState.STORM, 20),    (WeatherState.RAIN, 50),    (WeatherState.OVERCAST, 30)],
    WeatherState.FOG:      [(WeatherState.FOG, 40),      (WeatherState.CLEAR, 40),   (WeatherState.OVERCAST, 20)],
    WeatherState.SNOW:     [(WeatherState.SNOW, 40),     (WeatherState.WIND, 40),    (WeatherState.OVERCAST, 20)],
    WeatherState.HEAT:     [(WeatherState.HEAT, 40),     (WeatherState.CLEAR, 40),   (WeatherState.OVERCAST, 20)],
    WeatherState.WIND:     [(WeatherState.WIND, 30),     (WeatherState.CLEAR, 40),   (WeatherState.OVERCAST, 30)],
}

# ---------------------------------------------------------------------------
# Flavor text
# ---------------------------------------------------------------------------

WEATHER_FLAVOR: Dict[WeatherState, str] = {
    WeatherState.CLEAR:    "The sky is clear and bright.",
    WeatherState.OVERCAST: "Grey clouds blanket the sky.",
    WeatherState.RAIN:     "Rain falls steadily.",
    WeatherState.STORM:    "Thunder rumbles as a storm rages.",
    WeatherState.FOG:      "A thick fog obscures the surroundings.",
    WeatherState.SNOW:     "Snow drifts down in white curtains.",
    WeatherState.HEAT:     "The air shimmers with oppressive heat.",
    WeatherState.WIND:     "A strong wind howls through the area.",
}


# ---------------------------------------------------------------------------
# WeatherEngine
# ---------------------------------------------------------------------------

class WeatherEngine:
    """Markov-chain weather state machine with terrain-specific transitions.

    Attributes:
        current:          Active WeatherState.
        severity:         0–3 intensity modifier for the current state.
        turns_remaining:  Ticks until a transition roll is made.
        terrain_type:     Key into TERRAIN_TRANSITIONS.
    """

    def __init__(
        self,
        terrain_type: str = "forest",
        seed: Optional[int] = None,
    ) -> None:
        self.current: WeatherState = WeatherState.CLEAR
        self.severity: int = 0          # 0 = mild, 3 = extreme
        self.turns_remaining: int = random.randint(3, 8)
        self.terrain_type: str = terrain_type
        self._rng: random.Random = random.Random(seed)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def advance(self) -> Optional[str]:
        """Advance the weather simulation by one tick.

        Decrements *turns_remaining*.  When it hits zero a new weather
        state is rolled using the terrain transition table.

        Returns:
            Flavor text string if the weather changed, otherwise ``None``.
        """
        # Dungeons have no outdoor weather — never transition
        if self.terrain_type == "dungeon":
            return None

        self.turns_remaining -= 1
        if self.turns_remaining <= 0:
            new_weather = self._roll_weather()
            if new_weather != self.current:
                self.current = new_weather
                self.severity = self._rng.randint(0, 2)
                self.turns_remaining = self._rng.randint(3, 8)
                return WEATHER_FLAVOR.get(
                    self.current,
                    f"The weather shifts to {self.current.value}.",
                )
            # Same state again — just reset the timer
            self.turns_remaining = self._rng.randint(3, 8)
        return None

    def get_modifier(self) -> Dict[str, object]:
        """Return a dict of mechanical modifiers for the current weather.

        Modifier keys (all optional, absent if not applicable):
          - ``ranged`` (int)             — bonus/penalty to ranged attack rolls
          - ``perception`` (int)         — bonus/penalty to perception checks
          - ``movement_cost`` (int)      — extra movement cost per tile
          - ``attack`` (int)             — bonus/penalty to all attack rolls
          - ``secrets`` (int)            — bonus to searching for hidden things
          - ``torches_extinguish`` (bool)— storm extinguishes light sources
          - ``enemy_ambush_blocked`` (bool)— fog prevents surprise attacks
          - ``exhaustion_risk`` (bool)   — risk of exhaustion from heat
        """
        mods: Dict[str, object] = {}
        sev = self.severity

        if self.current == WeatherState.RAIN:
            mods["ranged"] = -(1 + min(sev, 2))
            if sev >= 3:
                mods["torches_extinguish"] = True

        elif self.current == WeatherState.FOG:
            mods["perception"] = -2
            mods["enemy_ambush_blocked"] = True

        elif self.current == WeatherState.STORM:
            mods["movement_cost"] = 1
            mods["attack"] = -1

        elif self.current == WeatherState.SNOW:
            mods["movement_cost"] = 1
            mods["secrets"] = 1   # Tracks in snow reveal passage

        elif self.current == WeatherState.WIND:
            mods["ranged"] = -1

        elif self.current == WeatherState.HEAT:
            if sev >= 2:
                mods["exhaustion_risk"] = True

        return mods

    def flavor_text(self) -> str:
        """Return flavor text for the current state, with severity escalation."""
        base = WEATHER_FLAVOR.get(self.current, "")
        if self.severity >= 2:
            base = base.rstrip(".") + " \u2014 conditions are severe."
        return base

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _roll_weather(self) -> WeatherState:
        """Pick the next weather state via the terrain transition table."""
        terrain_table = TERRAIN_TRANSITIONS.get(self.terrain_type, _DEFAULT_TRANSITIONS)
        transitions = terrain_table.get(self.current)
        if not transitions:
            transitions = _DEFAULT_TRANSITIONS.get(
                self.current,
                [(WeatherState.CLEAR, 100)],
            )
        states, weights = zip(*transitions)
        return self._rng.choices(list(states), weights=list(weights), k=1)[0]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        return {
            "current": self.current.value,
            "severity": self.severity,
            "turns_remaining": self.turns_remaining,
            "terrain_type": self.terrain_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WeatherEngine":
        """Restore from a serialized dict."""
        w = cls(terrain_type=data.get("terrain_type", "forest"))
        w.current = WeatherState(data["current"])
        w.severity = data.get("severity", 0)
        w.turns_remaining = data.get("turns_remaining", 5)
        return w

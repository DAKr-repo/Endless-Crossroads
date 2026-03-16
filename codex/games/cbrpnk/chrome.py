"""
codex.games.cbrpnk.chrome
===========================
Chrome (cybernetics) management system for CBR+PNK.

Provides:
  - ChromeManager: install/remove chrome, track humanity, trigger glitches
  - HUMANITY_THRESHOLDS: status descriptions by humanity level
"""

import random
from typing import Any, Dict, List, Optional


# =========================================================================
# HUMANITY THRESHOLDS
# =========================================================================

HUMANITY_THRESHOLDS: Dict[str, Any] = {
    10: {
        "label": "Fully Human",
        "description": "No augmentations, or so few they haven't touched your soul.",
        "cyberpsychosis_risk": 0.0,
    },
    8: {
        "label": "Lightly Augmented",
        "description": "You're enhanced, but you still feel mostly like yourself.",
        "cyberpsychosis_risk": 0.0,
    },
    6: {
        "label": "Modestly Chipped",
        "description": "The chrome is part of you now. Some days you barely notice.",
        "cyberpsychosis_risk": 0.05,
    },
    4: {
        "label": "Heavily Augmented",
        "description": "People sometimes flinch when you reach for things. They shouldn't. Probably.",
        "cyberpsychosis_risk": 0.15,
    },
    2: {
        "label": "Borderline Psychosis",
        "description": (
            "You think in machine rhythms. Emotional responses feel like lag. "
            "Your crew watches you carefully."
        ),
        "cyberpsychosis_risk": 0.35,
    },
    0: {
        "label": "Cyberpsychosis",
        "description": (
            "The humanity is gone. You operate on threat-assessment and objective "
            "fulfillment. The crew is no longer safe around you."
        ),
        "cyberpsychosis_risk": 1.0,
    },
}


def _get_threshold_data(humanity: int) -> Dict[str, Any]:
    """Return the appropriate threshold data for a given humanity value."""
    for threshold in sorted(HUMANITY_THRESHOLDS.keys(), reverse=True):
        if humanity >= threshold:
            return HUMANITY_THRESHOLDS[threshold]
    return HUMANITY_THRESHOLDS[0]


# =========================================================================
# CHROME MANAGER
# =========================================================================

class ChromeManager:
    """Manages a character's cybernetic augmentations and humanity score.

    Attributes:
        installed: Mapping of slot names to installed chrome data dicts.
        humanity: Current humanity score (0-10; starts at 10).
        glitch_history: Log of glitch events.
    """

    MAX_HUMANITY: int = 10
    MIN_HUMANITY: int = 0

    def __init__(self) -> None:
        self.installed: Dict[str, Dict[str, Any]] = {}
        self.humanity: int = self.MAX_HUMANITY
        self.glitch_history: List[Dict[str, Any]] = []

    def install_chrome(
        self,
        chrome_name: str,
        character: Optional[Any] = None,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Install a cybernetic augmentation.

        Checks slot availability and reduces humanity by the chrome's cost.
        If humanity drops to 4 or below, a cyberpsychosis check is triggered.

        Args:
            chrome_name: Key from the CHROME reference dict.
            character: Optional character object (unused; reserved for future hooks).
            rng: Optional Random instance for deterministic testing.

        Returns:
            Dict with: success (bool), chrome (dict), humanity (int),
            humanity_lost (int), slot_conflict (bool), psychosis_check (dict or None),
            message (str).
        """
        from codex.forge.reference_data.cbrpnk_chrome import CHROME, CHROME_SLOTS
        _rng = rng or random.Random()

        chrome_data = CHROME.get(chrome_name)
        if not chrome_data:
            return {
                "success": False,
                "chrome": None,
                "humanity": self.humanity,
                "humanity_lost": 0,
                "slot_conflict": False,
                "psychosis_check": None,
                "message": f"Unknown chrome: '{chrome_name}'.",
            }

        slot = chrome_data["slot"]
        slot_info = CHROME_SLOTS.get(slot, {"max_capacity": 1})
        max_cap = slot_info["max_capacity"]

        # Count currently installed items in this slot
        current_in_slot = sum(
            1 for entry in self.installed.values()
            if entry.get("slot") == slot
        )

        # Check for already installed
        if chrome_name in self.installed:
            return {
                "success": False,
                "chrome": chrome_data,
                "humanity": self.humanity,
                "humanity_lost": 0,
                "slot_conflict": True,
                "psychosis_check": None,
                "message": f"'{chrome_name}' is already installed.",
            }

        # Check capacity
        if current_in_slot >= max_cap:
            return {
                "success": False,
                "chrome": chrome_data,
                "humanity": self.humanity,
                "humanity_lost": 0,
                "slot_conflict": True,
                "psychosis_check": None,
                "message": (
                    f"Slot '{slot}' is at capacity ({current_in_slot}/{max_cap}). "
                    "Remove existing chrome first."
                ),
            }

        # Install
        humanity_cost = chrome_data["humanity_cost"]
        old_humanity = self.humanity
        self.humanity = max(self.MIN_HUMANITY, self.humanity - humanity_cost)
        humanity_lost = old_humanity - self.humanity
        self.installed[chrome_name] = dict(chrome_data)

        # Psychosis check if humanity is critically low
        psychosis_check = None
        if self.humanity <= 4:
            psychosis_check = self.humanity_check(rng=_rng)

        message = (
            f"'{chrome_name}' installed in {slot} slot. "
            f"Humanity: {old_humanity} -> {self.humanity} (-{humanity_lost})."
        )
        if psychosis_check:
            message += f" Cyberpsychosis check triggered: {psychosis_check.get('message', '')}"

        return {
            "success": True,
            "chrome": chrome_data,
            "humanity": self.humanity,
            "humanity_lost": humanity_lost,
            "slot_conflict": False,
            "psychosis_check": psychosis_check,
            "message": message,
        }

    def remove_chrome(self, slot: str) -> Dict[str, Any]:
        """Remove the most recently installed chrome from a slot.

        Partial humanity recovery (half the original cost, rounded down).

        Args:
            slot: The slot name to clear, or the chrome_name itself.

        Returns:
            Dict with: success (bool), removed (str or None), humanity_recovered (int),
            humanity (int), message (str).
        """
        from codex.forge.reference_data.cbrpnk_chrome import CHROME_SLOTS

        # Accept either slot name or chrome name
        target_name: Optional[str] = None
        if slot in self.installed:
            target_name = slot
        else:
            # Find first chrome in the given slot
            for name, data in self.installed.items():
                if data.get("slot") == slot:
                    target_name = name
                    break

        if not target_name:
            return {
                "success": False,
                "removed": None,
                "humanity_recovered": 0,
                "humanity": self.humanity,
                "message": f"No chrome found in slot/by name '{slot}'.",
            }

        chrome_data = self.installed.pop(target_name)
        humanity_cost = chrome_data.get("humanity_cost", 1)
        recovery = max(1, humanity_cost // 2) if humanity_cost > 0 else 0
        old_humanity = self.humanity
        self.humanity = min(self.MAX_HUMANITY, self.humanity + recovery)
        humanity_recovered = self.humanity - old_humanity

        message = (
            f"'{target_name}' removed. "
            f"Humanity partial recovery: +{humanity_recovered} "
            f"({old_humanity} -> {self.humanity})."
        )
        return {
            "success": True,
            "removed": target_name,
            "humanity_recovered": humanity_recovered,
            "humanity": self.humanity,
            "message": message,
        }

    def humanity_check(
        self, rng: Optional[random.Random] = None
    ) -> Dict[str, Any]:
        """Roll a humanity/cyberpsychosis stability check.

        Risk scales with how far humanity has dropped. At humanity 0,
        the check always fails.

        Args:
            rng: Optional Random instance for deterministic testing.

        Returns:
            Dict with: passed (bool), roll (float), threshold (float),
            status (str), message (str).
        """
        _rng = rng or random.Random()
        threshold_data = _get_threshold_data(self.humanity)
        risk = threshold_data["cyberpsychosis_risk"]
        status_label = threshold_data["label"]

        roll = _rng.random()  # 0.0 to 1.0
        passed = roll > risk

        if passed:
            message = (
                f"Humanity check passed (rolled {roll:.2f} vs {risk:.2f} risk). "
                f"Status: {status_label}."
            )
        else:
            message = (
                f"Humanity check FAILED (rolled {roll:.2f} vs {risk:.2f} risk). "
                f"Cyberpsychosis episode imminent. Status: {status_label}."
            )

        return {
            "passed": passed,
            "roll": round(roll, 4),
            "threshold": risk,
            "status": status_label,
            "humanity": self.humanity,
            "message": message,
        }

    def trigger_glitch(
        self, chrome_name: str, rng: Optional[random.Random] = None
    ) -> Dict[str, Any]:
        """Roll for a malfunction in a specific piece of chrome.

        Severity is determined by the chrome's glitch_risk rating.
        The glitch event is logged in glitch_history.

        Args:
            chrome_name: The name of the chrome to check.
            rng: Optional Random instance for deterministic testing.

        Returns:
            Dict with: glitch_occurred (bool), severity (str or None),
            effect (str), message (str).
        """
        from codex.forge.reference_data.cbrpnk_chrome import CHROME, GLITCH_EFFECTS
        _rng = rng or random.Random()

        # Prefer installed data (may have been modified), fall back to reference
        chrome_data = self.installed.get(chrome_name) or CHROME.get(chrome_name)
        if not chrome_data:
            return {
                "glitch_occurred": False,
                "severity": None,
                "effect": "",
                "message": f"Unknown chrome '{chrome_name}'.",
            }

        glitch_risk = chrome_data.get("glitch_risk", 0.0)
        roll = _rng.random()

        if roll > glitch_risk:
            return {
                "glitch_occurred": False,
                "severity": None,
                "effect": "",
                "message": f"'{chrome_name}' functioning within parameters.",
            }

        # Determine severity based on how far below the risk threshold we rolled
        if roll < glitch_risk * 0.2:
            severity = "critical"
        elif roll < glitch_risk * 0.5:
            severity = "major"
        else:
            severity = "minor"

        severity_data = GLITCH_EFFECTS.get(severity, GLITCH_EFFECTS["minor"])
        effect = _rng.choice(severity_data["examples"])

        event = {
            "chrome_name": chrome_name,
            "severity": severity,
            "effect": effect,
            "roll": round(roll, 4),
            "glitch_risk": glitch_risk,
        }
        self.glitch_history.append(event)

        message = (
            f"GLITCH [{severity.upper()}]: '{chrome_name}' malfunctioning. "
            f"Effect: {effect}"
        )

        return {
            "glitch_occurred": True,
            "severity": severity,
            "effect": effect,
            "message": message,
        }

    def get_status(self) -> str:
        """Return a formatted summary of installed chrome and humanity score.

        Returns:
            Multi-line string suitable for display.
        """
        threshold_data = _get_threshold_data(self.humanity)
        lines = [
            f"Humanity: {self.humanity}/{self.MAX_HUMANITY} — {threshold_data['label']}",
            f"  {threshold_data['description']}",
            "",
            f"Installed Chrome ({len(self.installed)} item(s)):",
        ]
        if self.installed:
            for name, data in self.installed.items():
                lines.append(
                    f"  [{data.get('slot', '?').upper()}] {name}: {data.get('effect', 'No effect listed')}"
                )
        else:
            lines.append("  No chrome installed.")

        if self.glitch_history:
            lines.append(f"\nGlitch History ({len(self.glitch_history)} event(s)):")
            for evt in self.glitch_history[-3:]:
                lines.append(
                    f"  [{evt['severity'].upper()}] {evt['chrome_name']}: {evt['effect']}"
                )

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager state for save/load."""
        return {
            "installed": dict(self.installed),
            "humanity": self.humanity,
            "glitch_history": list(self.glitch_history),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChromeManager":
        """Deserialize manager state from a saved dict."""
        mgr = cls()
        mgr.installed = data.get("installed", {})
        mgr.humanity = data.get("humanity", cls.MAX_HUMANITY)
        mgr.glitch_history = data.get("glitch_history", [])
        return mgr


__all__ = ["ChromeManager", "HUMANITY_THRESHOLDS"]

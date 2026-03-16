"""
codex/core/menu.py - Unified Menu Controller (WO 109)
=====================================================

Single source of truth for menu options across all three interfaces
(terminal, Discord, Telegram). Each interface renders natively but
reads labels, keys, and action strings from this module.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MenuOption:
    key: str            # "1", "2", etc.
    label: str          # "Codex of Chronicles"
    description: str    # "Play TTRPG"
    icon: str           # emoji
    action: str         # "play_chronicles"


@dataclass
class MenuDefinition:
    title: str
    options: List[MenuOption]
    footer: str


class CodexMenu:
    """Provides menu definitions and input resolution for all interfaces."""

    TERMINAL_OPTIONS = [
        ("1", "Codex of Chronicles", "Play TTRPG", "\U0001f409", "play_chronicles"),
        ("2", "Crown & Crew", "5-Day Narrative Journeys", "\U0001f451", "play_crown"),
        ("3", "Enter Burnwillow", "The Roguelike Dungeon", "\U0001f56f\ufe0f", "play_burnwillow"),
        ("4", "DM Tools", "Dice, NPCs, World Building", "\U0001f6e0\ufe0f", "dm_tools"),
        ("5", "Mimir's Vault", "Chronicles Of Destiny: Endless Crossroads", "\u2720", "open_vault"),
        ("6", "System Status", "View detailed vitals", "\U0001f4ca", "system_status"),
        ("7", "Tutorial", "Learn C.O.D.E.X. systems", "\U0001f4d6", "open_tutorial"),
        ("8", "Exit", "Return to the mundane world", "\U0001f6aa", "exit"),
    ]

    BOT_OPTIONS = [
        ("1", "Crown & Crew", "Fresh narrative campaign", "\U0001f451", "play_crown"),
        ("2", "Prologue", "Crown with saved campaign", "\U0001f4dc", "play_prologue"),
        ("3", "Quest Archetype", "Crown scenario template", "\u2694\ufe0f", "play_quest"),
        ("4", "Ashburn High", "Gothic boarding school", "\U0001f940", "play_ashburn"),
        ("5", "Burnwillow", "Roguelike dungeon crawler", "\U0001f56f\ufe0f", "play_burnwillow"),
        ("6", "The Omni-Forge", "Tables & Generators", "\U0001f3b2", "launch_omni_forge"),
        ("7", "D&D 5e Dungeon", "Classic dungeon crawl", "\U0001f409", "play_dnd5e"),
        ("8", "Cosmere: Roshar", "Stormlight dungeon", "\u2694\ufe0f", "play_cosmere"),
        ("9", "End Session", "Terminate active session", "\U0001f6d1", "end_session"),
    ]

    TERMINAL_ALIASES = {"q": "exit"}

    def __init__(self):
        self._terminal = self._build("MAIN QUEST", self.TERMINAL_OPTIONS,
                                     "Choose thy path [1/2/3/4/5/6/7/8/q]")
        self._bot = self._build("MIMIR UPLINK \u2014 Main Menu", self.BOT_OPTIONS,
                                "Type 1-9 to select.")

    @staticmethod
    def _build(title: str, raw: list, footer: str) -> MenuDefinition:
        options = [MenuOption(key=k, label=l, description=d, icon=i, action=a)
                   for k, l, d, i, a in raw]
        return MenuDefinition(title=title, options=options, footer=footer)

    def get_menu(self, interface: str) -> MenuDefinition:
        """Return the MenuDefinition for the given interface.

        Args:
            interface: "terminal", "discord", or "telegram"
        """
        if interface == "terminal":
            return self._terminal
        return self._bot

    def resolve_selection(self, interface: str, raw_input: str) -> Optional[str]:
        """Resolve user input to an action string, or None if invalid.

        Args:
            interface: "terminal", "discord", or "telegram"
            raw_input: The raw string the user typed (e.g. "3", "q")
        """
        text = raw_input.strip().lower()
        menu_def = self.get_menu(interface)
        key_map = {opt.key: opt.action for opt in menu_def.options}

        # Check direct key match
        if text in key_map:
            return key_map[text]

        # Check aliases (terminal only)
        if interface == "terminal" and text in self.TERMINAL_ALIASES:
            return self.TERMINAL_ALIASES[text]

        return None

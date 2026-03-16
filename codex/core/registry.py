"""
CommandRegistry — Unified command resolution for all C.O.D.E.X. interfaces.
=============================================================================

Provides a single source-of-truth for command definitions, aliases, and
categories.  Terminal, Discord, and Telegram all resolve user input through
this registry so that button labels, slash commands, and text input share
the same canonical names.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommandDef:
    """A single registered command."""
    canonical: str          # "move", "search", "save"
    aliases: list[str] = field(default_factory=list)   # ["go", "m"]
    description: str = ""
    category: str = "general"   # "navigation", "combat", "system"
    requires_session: bool = True

    @property
    def all_names(self) -> list[str]:
        """Canonical name plus all aliases."""
        return [self.canonical] + self.aliases


class CommandRegistry:
    """Unified command store with alias resolution.

    Usage::

        reg = CommandRegistry()
        reg.register(CommandDef("move", aliases=["go", "m"],
                                category="navigation"))
        cmd = reg.resolve("go")  # -> CommandDef for "move"
    """

    def __init__(self):
        self._commands: dict[str, CommandDef] = {}
        self._alias_map: dict[str, str] = {}

    def register(self, cmd: CommandDef) -> None:
        """Register a command definition."""
        key = cmd.canonical.lower()
        self._commands[key] = cmd
        self._alias_map[key] = key
        for alias in cmd.aliases:
            self._alias_map[alias.lower()] = key

    def resolve(self, raw_input: str) -> Optional[CommandDef]:
        """Resolve *raw_input* to a CommandDef via alias lookup.

        Returns None if no match.
        """
        token = raw_input.strip().lower().split()[0] if raw_input.strip() else ""
        canonical = self._alias_map.get(token)
        if canonical:
            return self._commands.get(canonical)
        return None

    def get_for_category(self, category: str) -> list[CommandDef]:
        """Return all commands in the given category."""
        return [c for c in self._commands.values()
                if c.category == category]

    def all_commands(self) -> list[CommandDef]:
        """Return every registered CommandDef."""
        return list(self._commands.values())

    def categories(self) -> list[str]:
        """Return distinct category names."""
        return sorted({c.category for c in self._commands.values()})


# =========================================================================
# PRE-REGISTERED BURNWILLOW COMMANDS
# =========================================================================

def build_burnwillow_registry() -> CommandRegistry:
    """Return a CommandRegistry pre-populated with Burnwillow commands."""
    reg = CommandRegistry()

    # Navigation
    reg.register(CommandDef("north", ["n"], "Move north", "navigation"))
    reg.register(CommandDef("south", ["s"], "Move south", "navigation"))
    reg.register(CommandDef("east", ["e"], "Move east", "navigation"))
    reg.register(CommandDef("west", ["w"], "Move west", "navigation"))

    # Exploration
    reg.register(CommandDef("look", ["l"], "Survey the current room", "exploration"))
    reg.register(CommandDef("search", ["sr"], "Search for hidden things", "exploration"))
    reg.register(CommandDef("inspect", ["i", "examine"], "Inspect an entity or feature", "exploration"))
    reg.register(CommandDef("scout", ["sc"], "Scout an adjacent room", "exploration"))

    # Combat / interaction
    reg.register(CommandDef("attack", ["a", "fight"], "Attack an enemy", "combat"))
    reg.register(CommandDef("defend", ["d", "block"], "Take a defensive stance", "combat"))
    reg.register(CommandDef("loot", ["grab", "take"], "Pick up loot from the room", "interaction"))
    reg.register(CommandDef("use", ["u"], "Use an item from inventory", "interaction"))

    # Inventory
    reg.register(CommandDef("inventory", ["inv", "bag", "backpack", "bp"], "Open backpack", "inventory"))
    reg.register(CommandDef("equip", ["eq"], "Equip an item", "inventory"))
    reg.register(CommandDef("drop", [], "Drop an item", "inventory"))
    reg.register(CommandDef("give", [], "Give item to party member (+1 Doom)", "inventory"))
    reg.register(CommandDef("return", ["extract", "retreat"], "Extract via Return Gate or transit point", "navigation"))
    reg.register(CommandDef("end", ["done", "finish"], "End your exploration turn", "navigation"))

    # Party
    reg.register(CommandDef("switch", ["sw", "switch_player"], "Switch active leader", "party"))

    # System
    reg.register(CommandDef("save", [], "Save current run", "system", requires_session=False))
    reg.register(CommandDef("quit", ["q", "exit"], "Quit the game", "system", requires_session=False))
    reg.register(CommandDef("help", ["h", "?"], "Show help", "system", requires_session=False))
    reg.register(CommandDef("map", ["m"], "Show the dungeon map", "system"))
    reg.register(CommandDef("status", ["st", "stats"], "Show character status", "system"))

    # Mimir's Vault & Narrative
    register_library_command(reg)
    register_narrative_commands(reg)

    return reg


def register_narrative_commands(reg: CommandRegistry) -> None:
    """Register narrative/settlement commands. Call from any registry builder."""
    reg.register(CommandDef("quest", ["quests", "journal"], "View quest log", "narrative"))
    reg.register(CommandDef("talk", ["npc", "speak"], "Talk to an NPC", "narrative"))
    reg.register(CommandDef("descend", ["delve", "enter"], "Enter the dungeon from town gate", "navigation"))
    reg.register(CommandDef("ascend", ["climb"], "Ascend into the canopy from town gate", "navigation"))


def register_library_command(reg: CommandRegistry) -> None:
    """Register the library/vault browser command.

    Call this from any game's registry builder to make the ``library``
    command available in that game loop.
    """
    reg.register(CommandDef(
        "library", ["lib", "vault", "books"],
        "Browse Mimir's Vault", "system",
        requires_session=False,
    ))


# =========================================================================
# PRE-REGISTERED D&D 5E COMMANDS
# =========================================================================

def build_dnd5e_registry() -> CommandRegistry:
    """Return a CommandRegistry pre-populated with D&D 5e commands."""
    reg = CommandRegistry()

    # Navigation
    reg.register(CommandDef("north", ["n"], "Move north", "navigation"))
    reg.register(CommandDef("south", ["s"], "Move south", "navigation"))
    reg.register(CommandDef("east", ["e"], "Move east", "navigation"))
    reg.register(CommandDef("west", ["w"], "Move west", "navigation"))

    # Exploration
    reg.register(CommandDef("look", ["l"], "Survey the current room", "exploration"))
    reg.register(CommandDef("search", ["sr"], "Search for hidden things", "exploration"))
    reg.register(CommandDef("inspect", ["i", "examine"], "Inspect an entity", "exploration"))
    reg.register(CommandDef("perception", ["perc"], "Make a Perception check", "exploration"))

    # Combat
    reg.register(CommandDef("attack", ["a", "fight"], "Attack an enemy", "combat"))
    reg.register(CommandDef("defend", ["d", "block"], "Take a defensive stance", "combat"))
    reg.register(CommandDef("cast", ["c"], "Cast a spell", "combat"))
    reg.register(CommandDef("disengage", ["dis"], "Disengage from combat", "combat"))

    # Ability checks
    reg.register(CommandDef("check", ["ck"], "Make an ability check", "ability"))

    # Interaction
    reg.register(CommandDef("loot", ["grab", "take"], "Pick up loot", "interaction"))
    reg.register(CommandDef("use", ["u"], "Use an item", "interaction"))

    # Inventory
    reg.register(CommandDef("inventory", ["inv", "bag", "bp"], "Open inventory", "inventory"))
    reg.register(CommandDef("equip", ["eq"], "Equip an item", "inventory"))
    reg.register(CommandDef("drop", [], "Drop an item", "inventory"))

    # Transit
    reg.register(CommandDef("travel", ["retreat", "portal"], "Step through a Hidden Portal", "navigation"))

    # Party
    reg.register(CommandDef("party", ["p"], "View party status", "party"))
    reg.register(CommandDef("switch", ["sw"], "Switch active character", "party"))

    # System
    reg.register(CommandDef("save", [], "Save current game", "system", requires_session=False))
    reg.register(CommandDef("quit", ["q", "exit"], "Quit the game", "system", requires_session=False))
    reg.register(CommandDef("help", ["h", "?"], "Show help", "system", requires_session=False))
    reg.register(CommandDef("map", ["m"], "Show the dungeon map", "system"))
    reg.register(CommandDef("status", ["st", "stats"], "Show character status", "system"))

    register_library_command(reg)
    register_narrative_commands(reg)
    return reg


# =========================================================================
# PRE-REGISTERED COSMERE COMMANDS
# =========================================================================

def build_cosmere_registry() -> CommandRegistry:
    """Return a CommandRegistry pre-populated with Cosmere RPG commands."""
    reg = CommandRegistry()

    # Navigation
    reg.register(CommandDef("north", ["n"], "Move north", "navigation"))
    reg.register(CommandDef("south", ["s"], "Move south", "navigation"))
    reg.register(CommandDef("east", ["e"], "Move east", "navigation"))
    reg.register(CommandDef("west", ["w"], "Move west", "navigation"))

    # Exploration
    reg.register(CommandDef("look", ["l"], "Survey the current room", "exploration"))
    reg.register(CommandDef("search", ["sr"], "Search for hidden things", "exploration"))
    reg.register(CommandDef("inspect", ["i", "examine"], "Inspect an entity", "exploration"))
    reg.register(CommandDef("perception", ["perc"], "Make a Perception check", "exploration"))

    # Combat
    reg.register(CommandDef("attack", ["a", "fight"], "Attack an enemy", "combat"))
    reg.register(CommandDef("defend", ["d", "block"], "Take a defensive stance", "combat"))
    reg.register(CommandDef("cast", ["c"], "Cast a spell", "combat"))
    reg.register(CommandDef("disengage", ["dis"], "Disengage from combat", "combat"))

    # Transit
    reg.register(CommandDef("travel", ["retreat", "warp"], "Use a transit point", "navigation"))

    # Surges
    reg.register(CommandDef("adhesion", ["adh"], "Use Adhesion surge", "surge"))
    reg.register(CommandDef("gravitation", ["grav"], "Use Gravitation surge", "surge"))
    reg.register(CommandDef("division", ["div"], "Use Division surge", "surge"))
    reg.register(CommandDef("abrasion", ["abr"], "Use Abrasion surge", "surge"))
    reg.register(CommandDef("progression", ["prog"], "Use Progression surge", "surge"))
    reg.register(CommandDef("illumination", ["illum"], "Use Illumination surge", "surge"))
    reg.register(CommandDef("transformation", ["trans"], "Use Transformation surge", "surge"))
    reg.register(CommandDef("transportation", ["tp"], "Use Transportation surge", "surge"))
    reg.register(CommandDef("cohesion", ["coh"], "Use Cohesion surge", "surge"))
    reg.register(CommandDef("tension", ["ten"], "Use Tension surge", "surge"))

    # Interaction
    reg.register(CommandDef("loot", ["grab", "take"], "Pick up loot", "interaction"))
    reg.register(CommandDef("use", ["u"], "Use an item", "interaction"))
    reg.register(CommandDef("infuse", ["inf"], "Infuse with Stormlight", "interaction"))

    # Inventory
    reg.register(CommandDef("inventory", ["inv", "bag", "bp"], "Open inventory", "inventory"))
    reg.register(CommandDef("equip", ["eq"], "Equip an item", "inventory"))
    reg.register(CommandDef("drop", [], "Drop an item", "inventory"))

    # Party
    reg.register(CommandDef("party", ["p"], "View party status", "party"))
    reg.register(CommandDef("switch", ["sw"], "Switch active character", "party"))

    # System
    reg.register(CommandDef("save", [], "Save current game", "system", requires_session=False))
    reg.register(CommandDef("quit", ["q", "exit"], "Quit the game", "system", requires_session=False))
    reg.register(CommandDef("help", ["h", "?"], "Show help", "system", requires_session=False))
    reg.register(CommandDef("map", ["m"], "Show the dungeon map", "system"))
    reg.register(CommandDef("status", ["st", "stats"], "Show character status", "system"))

    register_library_command(reg)
    register_narrative_commands(reg)
    return reg

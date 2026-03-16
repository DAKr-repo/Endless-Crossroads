#!/usr/bin/env python3
"""
codex_char_wizard.py - The Codex Character Forge
==================================================
A content-agnostic character builder that dynamically discovers game systems
from the vault/ directory. No hardcoded system names — if a vault folder
contains a creation_rules.json, it becomes a buildable system.

Architecture:
  - CharacterBuilderEngine: Scans vault/, loads schemas, routes to builders
  - SystemBuilder: Generic step-walker driven by creation_rules.json
  - View routing: paper_doll (Burnwillow) vs stat_block (everything else)

Author: Codex Team (@architect + @archivist + @designer)
"""

import os
import json
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich.columns import Columns
from rich import box

from codex.forge.source_scanner import scan_content_availability, scan_system_content

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # -> Codex/

# ---------------------------------------------------------------------------
# WO 087 — RACIAL BONUSES (SRD)
# ---------------------------------------------------------------------------
RACIAL_BONUSES: Dict[str, Dict[str, int]] = {
    "human": {"all": 1},
    "elf": {"Dexterity": 2},
    "dwarf": {"Constitution": 2},
    "halfling": {"Dexterity": 2},
    "gnome": {"Intelligence": 2},
    "half_elf": {"Charisma": 2},
    "half_orc": {"Strength": 2, "Constitution": 1},
    "tiefling": {"Charisma": 2, "Intelligence": 1},
    "dragonborn": {"Strength": 2, "Charisma": 1},
    "aarakocra": {"Dexterity": 2, "Wisdom": 1},
    "aasimar": {"Charisma": 2},
    "bugbear": {"Strength": 2, "Dexterity": 1},
    "centaur": {"Strength": 2, "Wisdom": 1},
    "changeling": {"Charisma": 2},
    "deep_gnome": {"Intelligence": 2},
    "duergar": {"Constitution": 2},
    "eladrin": {"Dexterity": 2, "Charisma": 1},
    "fairy": {"Dexterity": 2},
    "firbolg": {"Wisdom": 2, "Strength": 1},
    "genasi": {"Constitution": 2},
    "githyanki": {"Strength": 2, "Intelligence": 1},
    "githzerai": {"Wisdom": 2, "Intelligence": 1},
    "goblin": {"Dexterity": 2, "Constitution": 1},
    "goliath": {"Strength": 2, "Constitution": 1},
    "harengon": {"Dexterity": 2},
    "hobgoblin": {"Constitution": 2, "Intelligence": 1},
    "kenku": {"Dexterity": 2, "Wisdom": 1},
    "kobold": {"Dexterity": 2},
    "lizardfolk": {"Constitution": 2, "Wisdom": 1},
    "minotaur": {"Strength": 2, "Constitution": 1},
    "orc": {"Strength": 2, "Constitution": 1},
    "satyr": {"Charisma": 2, "Dexterity": 1},
    "shifter": {"Dexterity": 2},
    "tabaxi": {"Dexterity": 2, "Charisma": 1},
    "tortle": {"Strength": 2, "Wisdom": 1},
    "triton": {"Strength": 1, "Constitution": 1, "Charisma": 1},
    "yuan_ti": {"Charisma": 2, "Intelligence": 1},
}


def apply_racial_bonuses(sheet: 'CharacterSheet'):
    """Apply racial stat bonuses to the character sheet."""
    bonuses = RACIAL_BONUSES.get(sheet.race.lower(), {})
    if "all" in bonuses:
        for stat in sheet.stats:
            sheet.stats[stat] += bonuses["all"]
    else:
        for stat, bonus in bonuses.items():
            if stat in sheet.stats:
                sheet.stats[stat] += bonus

# ---------------------------------------------------------------------------
# THEME CONSTANTS
# ---------------------------------------------------------------------------
FORGE_GOLD = "#FFD700"
FORGE_CYAN = "#00FFCC"
FORGE_DIM = "#555555"
FORGE_RED = "#CC5500"
FORGE_BONE = "#F5F5DC"
FORGE_BORDER = "#2D5016"


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------
@dataclass
class CreationSchema:
    """Parsed creation_rules.json for a single game system."""
    system_id: str
    display_name: str
    genre: str
    stats_method: str
    stats: List[str]
    steps: List[Dict[str, Any]]
    view_type: str
    derived: Dict[str, Any]
    vault_path: str  # absolute path to the vault folder
    parent_engine: str = ""  # parent system_id (e.g. "crown" for Ashburn)
    setting_id: str = ""    # sub-setting: "roshar", "forgotten_realms", etc.

    @classmethod
    def from_file(cls, json_path: str, vault_path: str) -> "CreationSchema":
        """Load and parse a creation_rules.json file into a CreationSchema."""
        with open(json_path, "r") as f:
            data = json.load(f)
        return cls(
            system_id=data["system_id"],
            display_name=data["display_name"],
            genre=data.get("genre", ""),
            stats_method=data.get("stats_method", "manual"),
            stats=data.get("stats", []),
            steps=data.get("steps", []),
            view_type=data.get("view_type", "stat_block"),
            derived=data.get("derived", {}),
            vault_path=vault_path,
            parent_engine=data.get("parent_engine", ""),
            setting_id=data.get("setting_id", ""),
        )


@dataclass
class CharacterSheet:
    """System-agnostic character data built by the wizard."""
    system_id: str
    setting_id: str = ""
    name: str = ""
    choices: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=dict)
    # WO 087 — Derived stats
    max_hp: int = 0
    current_hp: int = 0
    armor_class: int = 10
    initiative_bonus: int = 0
    subclass: str = ""
    background_story: str = ""
    inventory: List[str] = field(default_factory=list)
    level: int = 1
    subrace: str = ""
    feats: List[str] = field(default_factory=list)
    fighting_styles: List[str] = field(default_factory=list)
    resources: Dict[str, dict] = field(default_factory=dict)
    # WO Blueprint — Extended character fields
    skill_proficiencies: List[str] = field(default_factory=list)
    saving_throw_proficiencies: List[str] = field(default_factory=list)
    cantrips_known: List[str] = field(default_factory=list)
    spells_known: List[str] = field(default_factory=list)
    alignment: str = ""
    personality_traits: List[str] = field(default_factory=list)
    ideals: List[str] = field(default_factory=list)
    bonds: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)
    gold: int = 0
    equipment_mode: str = "package"

    @property
    def race(self) -> str:
        """Extract race ID from choices."""
        r = self.choices.get("race", {})
        return r.get("id", "") if isinstance(r, dict) else str(r)

    @property
    def character_class(self) -> str:
        """Extract class ID from choices."""
        c = self.choices.get("class", {})
        return c.get("id", "") if isinstance(c, dict) else str(c)

    @property
    def modifiers(self) -> Dict[str, int]:
        """Calculate ability modifiers: (Score - 10) // 2."""
        return {k: (v - 10) // 2 for k, v in self.stats.items()}

    def calculate_derived_stats(self):
        """Compute HP, AC, and Initiative based on stats and class."""
        mods = self.modifiers
        hit_die = self._get_class_hit_die(self.character_class)
        con_mod = mods.get("Constitution", mods.get("Grit", 0))
        self.max_hp = hit_die + con_mod
        self.current_hp = self.max_hp
        dex_mod = mods.get("Dexterity", mods.get("Wits", 0))
        self.armor_class = 10 + dex_mod
        self.initiative_bonus = dex_mod

        # Class resources
        cls = self.character_class.lower()
        if cls == "fighter":
            self.resources["action_surge"] = {"uses": 1, "recharge": "short_rest"}
            self.resources["second_wind"] = {"uses": 1, "recharge": "short_rest", "heal": "1d10+level"}
        elif cls == "barbarian":
            self.resources["rage"] = {"uses": 2, "recharge": "long_rest", "bonus_damage": 2}
        elif cls == "monk":
            self.resources["ki_points"] = {"uses": max(1, self.level), "recharge": "short_rest"}
        elif cls == "sorcerer":
            self.resources["sorcery_points"] = {"uses": max(1, self.level), "recharge": "long_rest"}
        elif cls == "warlock":
            self.resources["pact_slots"] = {"uses": 1, "recharge": "short_rest", "level": 1}
        elif cls == "paladin":
            cha_mod = self.modifiers.get("Charisma", 0)
            self.resources["lay_on_hands"] = {"pool": max(5, self.level * 5), "recharge": "long_rest"}
            self.resources["divine_sense"] = {"uses": 1 + max(0, cha_mod), "recharge": "long_rest"}
        elif cls == "bard":
            cha_mod = self.modifiers.get("Charisma", 0)
            self.resources["bardic_inspiration"] = {"uses": max(1, cha_mod), "recharge": "long_rest", "die": "d6"}

    def _get_class_hit_die(self, class_name: str) -> int:
        """Map class ID to max hit die value."""
        hit_dice = {
            "barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10,
            "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8,
            "warlock": 8, "artificer": 8,
            "sorcerer": 6, "wizard": 6,
        }
        return hit_dice.get(class_name.lower(), 8)

    def summary_lines(self) -> List[str]:
        """Return a list of human-readable strings summarising the sheet's choices and stats."""
        lines = [f"Name: {self.name}"]
        for key, val in self.choices.items():
            if key == "name":
                continue
            if isinstance(val, dict):
                lines.append(f"{key.title()}: {val.get('label', val.get('id', str(val)))}")
            else:
                lines.append(f"{key.title()}: {val}")
        if self.stats:
            stat_str = "  ".join(f"{k}: {v}" for k, v in self.stats.items())
            lines.append(f"Stats: {stat_str}")
        if self.max_hp:
            lines.append(f"HP: {self.max_hp}  AC: {self.armor_class}  Init: {self.initiative_bonus:+d}")
        if self.subclass:
            lines.append(f"Archetype: {self.subclass}")
        if self.subrace:
            lines.append(f"Subrace: {self.subrace}")
        if self.feats:
            lines.append(f"Feats: {', '.join(self.feats)}")
        if self.alignment:
            lines.append(f"Alignment: {self.alignment}")
        if self.skill_proficiencies:
            lines.append(f"Skills: {', '.join(s.replace('_', ' ').title() for s in self.skill_proficiencies)}")
        if self.cantrips_known:
            lines.append(f"Cantrips: {', '.join(self.cantrips_known)}")
        if self.spells_known:
            lines.append(f"Spells: {', '.join(self.spells_known)}")
        if self.personality_traits:
            lines.append(f"Trait: {self.personality_traits[0]}")
        return lines


# ---------------------------------------------------------------------------
# ENGINE: Dynamic Plugin Loader
# ---------------------------------------------------------------------------
class CharacterBuilderEngine:
    """
    Scans vault/ for creation_rules.json files and registers each as a
    buildable system. Zero hardcoded system names.
    """

    def __init__(self, vault_root: Optional[str] = None):
        self.vault_root = vault_root or os.path.join(_ROOT, "vault")
        self.systems: Dict[str, CreationSchema] = {}
        self._discover()

    def _discover(self):
        """Walk vault/ dirs (including family subdirs and modules) for creation_rules.json."""
        if not os.path.isdir(self.vault_root):
            return
        for entry in sorted(os.listdir(self.vault_root)):
            vault_path = os.path.join(self.vault_root, entry)
            if not os.path.isdir(vault_path):
                continue
            rules_file = os.path.join(vault_path, "creation_rules.json")
            if os.path.isfile(rules_file):
                try:
                    schema = CreationSchema.from_file(rules_file, vault_path)
                    self.systems[schema.system_id] = schema
                except (json.JSONDecodeError, KeyError):
                    pass
            # Always scan subdirs for family systems (FITD/) and modules (crown/ashburn/)
            for sub_entry in sorted(os.listdir(vault_path)):
                sub_path = os.path.join(vault_path, sub_entry)
                if not os.path.isdir(sub_path):
                    continue
                sub_rules = os.path.join(sub_path, "creation_rules.json")
                if os.path.isfile(sub_rules):
                    try:
                        schema = CreationSchema.from_file(sub_rules, sub_path)
                        self.systems[schema.system_id] = schema
                    except (json.JSONDecodeError, KeyError):
                        pass

    def list_systems(self) -> List[CreationSchema]:
        """Return all discovered CreationSchema instances, one per buildable system."""
        return list(self.systems.values())

    def get_system(self, system_id: str) -> Optional[CreationSchema]:
        """Return the CreationSchema for a given system_id, or None if not found."""
        return self.systems.get(system_id)


# ---------------------------------------------------------------------------
# BUILDER: Generic Step Walker
# ---------------------------------------------------------------------------
class SystemBuilder:
    """Walks a CreationSchema's steps to build a CharacterSheet."""

    def __init__(self, schema: CreationSchema, console: Console, core=None):
        self.schema = schema
        self.console = console
        self.sheet = CharacterSheet(system_id=schema.system_id, setting_id=schema.setting_id)
        self.forge = None
        if core:
            try:
                from codex_omni_forge import OmniForge
                self.forge = OmniForge(core)
            except ImportError:
                pass

    def _forge_query(self, prompt: str, context: str = "") -> str:
        """Synchronously call OmniForge. Returns empty string on failure."""
        if not self.forge:
            return ""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return ""
            return loop.run_until_complete(
                self.forge.roll_on_table("Core", prompt, context)
            )
        except Exception:
            return ""

    class _BackStep(Exception):
        """Raised when the user types 'back' during a wizard step."""

    def _prompt(self, label: str, choices: list, default: str = "1") -> str:
        """Prompt.ask wrapper that always accepts 'back'/'b' and raises _BackStep."""
        valid = list(choices) + ["back", "b"]
        answer = Prompt.ask(label, choices=valid, default=default, console=self.console)
        if answer.lower() in ("back", "b"):
            raise self._BackStep()
        return answer

    def run(self) -> CharacterSheet:
        """Walk all wizard steps interactively and return the completed CharacterSheet."""
        total = len(self.schema.steps)
        idx = 0
        while idx < total:
            step = self.schema.steps[idx]
            self.console.print(
                f"\n[{FORGE_DIM}]Step {idx + 1}/{total} (type 'back' to redo previous)[/]"
            )
            step_type = step.get("type", "text_input")

            try:
                if step_type == "text_input":
                    self._step_text(step)
                elif step_type == "choice":
                    self._step_choice(step)
                elif step_type == "stat_roll":
                    self._step_stat_roll(step)
                elif step_type == "stat_pool_allocate":
                    self._step_stat_pool(step)
                idx += 1
            except self._BackStep:
                if idx > 0:
                    idx -= 1
                    self.console.print(f"[dim]Returning to step {idx + 1}...[/dim]")
                else:
                    self.console.print(f"[dim]Already at first step.[/dim]")

        # WO Blueprint — Post-step processing (D&D-specific)
        if self.sheet.system_id == "dnd5e" and self.sheet.stats:
            # 1. Apply racial bonuses (or custom lineage rules) — not back-able
            if self.sheet.race:
                if self.sheet.race.lower() == "custom_lineage":
                    self._step_custom_lineage()
                else:
                    apply_racial_bonuses(self.sheet)
                    self.console.print(
                        f"\n[{FORGE_DIM}]Racial bonuses applied for "
                        f"{self.sheet.race.replace('_', ' ').title()}[/]"
                    )

            # Back-navigable post-step sequence
            post_steps = [
                self._step_subrace,
                self._step_alignment,
                self._step_skill_proficiency,
                self._step_derived_stats,
                self._step_subclass,
                self._step_feats,
                lambda: self._step_fighting_style(self.sheet, self.console),
                self._step_spell_selection,
                self._step_personality,
                self._step_biography,
                self._step_life_path,
                self._step_dark_secret,
                self._step_group_patron,
                self._step_equipment,
            ]
            pi = 0
            while pi < len(post_steps):
                try:
                    post_steps[pi]()
                    pi += 1
                except self._BackStep:
                    if pi > 0:
                        pi -= 1
                        self.console.print(f"[dim]Going back...[/dim]")
                    else:
                        self.console.print(f"[dim]Already at first step.[/dim]")

        return self.sheet

    def _step_derived_stats(self):
        """Compute derived stats (HP, AC, Initiative) — no user input."""
        self.sheet.calculate_derived_stats()
        self.console.print(
            f"[{FORGE_DIM}]Derived: HP {self.sheet.max_hp} | "
            f"AC {self.sheet.armor_class} | "
            f"Init {self.sheet.initiative_bonus:+d}[/]"
        )

    def _step_biography(self):
        """Optional text entry for character background."""
        self.console.print(f"\n[bold {FORGE_GOLD}]Biography[/]")
        self.console.print(f"  [dim]Who are you? (Enter a short bio or press Enter to skip)[/dim]")
        bio = Prompt.ask("  Biography", default="", console=self.console)
        if bio.strip().lower() in ("back", "b"):
            raise self._BackStep()
        self.sheet.background_story = bio.strip() if bio.strip() else "A traveler of few words."

    def _step_custom_lineage(self) -> None:
        """Apply TCE Custom Lineage rules instead of a standard racial template.

        Grants: +2 to one chosen ability score, Small/Medium size choice,
        30 ft. speed, one feat pick, and either darkvision or a skill
        proficiency. Records all choices in ``self.sheet.choices["custom_lineage"]``.
        """
        try:
            from codex.forge.reference_data.loader import load_reference
            lineage = load_reference("custom_lineage")
        except ImportError:
            lineage = {}

        self.console.print(f"\n[bold {FORGE_GOLD}]Custom Lineage[/]  [dim](Tasha's Cauldron of Everything)[/dim]")
        if lineage.get("description"):
            self.console.print(f"  [dim]{lineage['description']}[/dim]")

        lineage_choices: dict = {}

        # +2 to one ability score
        stat_names = list(self.sheet.stats.keys()) if self.sheet.stats else [
            "Strength", "Dexterity", "Constitution",
            "Intelligence", "Wisdom", "Charisma",
        ]
        self.console.print(f"\n  [bold]Ability Score Increase[/bold]  [dim](+2 to one score)[/dim]")
        for j, stat in enumerate(stat_names, 1):
            current = self.sheet.stats.get(stat, 10)
            self.console.print(f"    [{FORGE_CYAN}]{j}[/] {stat} (currently {current})")
        valid = [str(n) for n in range(1, len(stat_names) + 1)]
        pick = Prompt.ask("    Choose stat", choices=valid, default="1", console=self.console)
        chosen_stat = stat_names[int(pick) - 1]
        if chosen_stat in self.sheet.stats:
            self.sheet.stats[chosen_stat] += 2
        lineage_choices["ability_increase"] = chosen_stat
        self.console.print(f"    [dim]+2 {chosen_stat} applied.[/dim]")

        # Size choice
        self.console.print(f"\n  [bold]Size[/bold]")
        self.console.print(f"    [{FORGE_CYAN}]1[/] Medium")
        self.console.print(f"    [{FORGE_CYAN}]2[/] Small")
        size_pick = Prompt.ask("    Choose size", choices=["1", "2"], default="1", console=self.console)
        chosen_size = "Medium" if size_pick == "1" else "Small"
        lineage_choices["size"] = chosen_size
        self.console.print(f"    [dim]Size: {chosen_size}[/dim]")

        # Feat pick
        self.console.print(f"\n  [bold]Feat[/bold]  [dim](one feat of your choice)[/dim]")
        try:
            from codex.forge.reference_data.loader import load_reference, filter_by_source, get_available_sources
            feats_data = load_reference("feats")
            available = get_available_sources()
            feat_list = list(feats_data.values()) if isinstance(feats_data, dict) else feats_data
            feat_list = filter_by_source(feat_list, available)
        except Exception:
            feat_list = []

        if feat_list:
            grid = Table.grid(padding=(0, 3))
            grid.add_column(min_width=35)
            grid.add_column(min_width=35)
            rows = []
            for j, feat in enumerate(feat_list, 1):
                desc = feat.get("description", "")
                rows.append(f"[{FORGE_CYAN}]{j:>2}[/] {feat['name']}  [dim]{desc}[/dim]")
            for r in range(0, len(rows), 2):
                left = rows[r]
                right = rows[r + 1] if r + 1 < len(rows) else ""
                grid.add_row(left, right)
            self.console.print(grid)
            valid_f = [str(n) for n in range(1, len(feat_list) + 1)]
            feat_pick = Prompt.ask("    Choose feat", choices=valid_f, default="1", console=self.console)
            chosen_feat = feat_list[int(feat_pick) - 1]["name"]
            if chosen_feat not in self.sheet.feats:
                self.sheet.feats.append(chosen_feat)
            lineage_choices["feat"] = chosen_feat
            self.console.print(f"    [dim]Feat: {chosen_feat}[/dim]")
        else:
            feat_text = Prompt.ask("    Feat name", default="Alert", console=self.console)
            self.sheet.feats.append(feat_text.strip())
            lineage_choices["feat"] = feat_text.strip()

        # Darkvision or skill proficiency
        self.console.print(f"\n  [bold]Darkvision or Skill Proficiency[/bold]")
        self.console.print(f"    [{FORGE_CYAN}]1[/] Darkvision (60 ft.)")
        self.console.print(f"    [{FORGE_CYAN}]2[/] One skill proficiency of your choice")
        dv_pick = Prompt.ask("    Choose", choices=["1", "2"], default="1", console=self.console)
        if dv_pick == "1":
            lineage_choices["darkvision_or_skill"] = "darkvision_60"
            self.console.print(f"    [dim]Darkvision (60 ft.) granted.[/dim]")
        else:
            COMMON_SKILLS = [
                "acrobatics", "animal_handling", "arcana", "athletics",
                "deception", "history", "insight", "intimidation",
                "investigation", "medicine", "nature", "perception",
                "performance", "persuasion", "religion", "sleight_of_hand",
                "stealth", "survival",
            ]
            for j, sk in enumerate(COMMON_SKILLS, 1):
                self.console.print(f"    [{FORGE_CYAN}]{j}[/] {sk.replace('_', ' ').title()}")
            valid_sk = [str(n) for n in range(1, len(COMMON_SKILLS) + 1)]
            sk_pick = Prompt.ask("    Choose skill", choices=valid_sk, default="1", console=self.console)
            chosen_skill = COMMON_SKILLS[int(sk_pick) - 1]
            if chosen_skill not in self.sheet.skill_proficiencies:
                self.sheet.skill_proficiencies.append(chosen_skill)
            lineage_choices["darkvision_or_skill"] = chosen_skill
            self.console.print(f"    [dim]Skill: {chosen_skill.replace('_', ' ').title()}[/dim]")

        self.sheet.choices["custom_lineage"] = lineage_choices
        self.console.print(f"\n[{FORGE_DIM}]Custom Lineage configured.[/]")

    def _step_life_path(self) -> None:
        """Display TCE 'This Is Your Life' tables and record player choices.

        Iterates every category in LIFE_PATH_TABLES. For each category the
        player can roll randomly (press Enter) or pick a numbered entry.
        Results are stored under ``self.sheet.choices["life_path"]`` as a
        ``dict[category, chosen_entry]``.
        """
        try:
            from codex.forge.reference_data.loader import load_reference
            tables = load_reference("life_path")
        except ImportError:
            return
        if not tables:
            return

        self.console.print(f"\n[bold {FORGE_GOLD}]Life Path[/]  [dim](Tasha's Cauldron of Everything)[/dim]")
        self.console.print(
            f"  [dim]Explore the events that shaped your character. "
            f"Press Enter to roll randomly, or pick a number.[/dim]"
        )

        life_path_results: dict = {}
        for category, entries in tables.items():
            if not entries:
                continue
            category_label = category.replace("_", " ").title()
            self.console.print(f"\n  [bold {FORGE_CYAN}]{category_label}[/]")
            for j, entry in enumerate(entries, 1):
                self.console.print(f"    [{FORGE_CYAN}]{j}[/] [dim]{entry}[/dim]")

            valid = [str(n) for n in range(1, len(entries) + 1)]
            choice_str = Prompt.ask(
                f"    Choice [1-{len(entries)}, Enter=random, back]",
                default="",
                console=self.console,
            )
            if choice_str.strip().lower() in ("back", "b"):
                raise self._BackStep()
            if choice_str.strip() == "" or choice_str.strip() not in valid:
                chosen_idx = random.randint(0, len(entries) - 1)
                chosen = entries[chosen_idx]
                self.console.print(f"    [dim]Rolled: {chosen}[/dim]")
            else:
                chosen = entries[int(choice_str) - 1]
                self.console.print(f"    [dim]Chosen: {chosen}[/dim]")
            life_path_results[category] = chosen

        self.sheet.choices["life_path"] = life_path_results

    def _step_dark_secret(self) -> None:
        """Optional selection from 12 TCE dark secrets.

        If the player skips (choice 0), no secret is recorded.
        The chosen secret dict is stored under
        ``self.sheet.choices["dark_secret"]``.
        """
        try:
            from codex.forge.reference_data.loader import load_reference
            secrets = load_reference("dark_secrets")
        except ImportError:
            return
        if not secrets:
            return

        self.console.print(f"\n[bold {FORGE_GOLD}]Dark Secret[/]  [dim](optional, TCE)[/dim]")
        self.console.print(
            f"  [dim]Does your character carry a hidden burden? "
            f"Choose one or skip.[/dim]"
        )
        for j, secret in enumerate(secrets, 1):
            self.console.print(
                f"  [{FORGE_CYAN}]{j}[/] [bold]{secret['name']}[/bold]"
                f"  [dim]{secret['description']}[/dim]"
            )
        self.console.print(f"  [{FORGE_CYAN}]0[/] [dim]No secret (skip)[/dim]")

        valid = [str(n) for n in range(0, len(secrets) + 1)]
        pick = self._prompt("  Choice", valid, default="0")
        idx = int(pick)
        if idx > 0:
            chosen = secrets[idx - 1]
            self.sheet.choices["dark_secret"] = chosen
            self.console.print(f"  [dim]Secret recorded: {chosen['name']}[/dim]")
        else:
            self.console.print(f"  [dim]No dark secret recorded.[/dim]")

    def _step_group_patron(self) -> None:
        """Select a TCE group patron for the adventuring party.

        The chosen patron dict (with id, name, description, perks,
        quest_hooks) is stored under ``self.sheet.choices["group_patron"]``.
        Skippable via choice 0.
        """
        try:
            from codex.forge.reference_data.loader import load_reference
            patrons = load_reference("group_patrons")
        except ImportError:
            return
        if not patrons:
            return

        self.console.print(f"\n[bold {FORGE_GOLD}]Group Patron[/]  [dim](optional, TCE)[/dim]")
        self.console.print(
            f"  [dim]Who backs your party? A patron provides resources "
            f"and drives your early quests.[/dim]"
        )
        for j, patron in enumerate(patrons, 1):
            perks_preview = patron["perks"][0] if patron.get("perks") else ""
            self.console.print(
                f"  [{FORGE_CYAN}]{j}[/] [bold]{patron['name']}[/bold]"
                f"  [dim]{patron['description']}[/dim]"
            )
            if perks_preview:
                self.console.print(f"      [dim]Perk: {perks_preview}[/dim]")
        self.console.print(f"  [{FORGE_CYAN}]0[/] [dim]No patron (skip)[/dim]")

        valid = [str(n) for n in range(0, len(patrons) + 1)]
        pick = self._prompt("  Choice", valid, default="0")
        idx = int(pick)
        if idx > 0:
            chosen = patrons[idx - 1]
            self.sheet.choices["group_patron"] = chosen
            self.console.print(f"  [dim]Patron selected: {chosen['name']}[/dim]")
            # Show all perks as a confirmation summary
            if chosen.get("perks"):
                self.console.print(f"  [dim]Perks: {', '.join(chosen['perks'])}[/dim]")
        else:
            self.console.print(f"  [dim]No group patron recorded.[/dim]")

    def _step_equipment(self):
        """Select starting equipment package based on class."""
        c = self.sheet.character_class
        self.console.print(f"\n[bold {FORGE_GOLD}]Starting Equipment[/]")

        if c in ("fighter", "paladin"):
            options = [
                "Chain Mail + Shield + Martial Weapon",
                "Leather Armor + Longbow + Martial Weapon",
            ]
        elif c in ("rogue", "ranger"):
            options = [
                "Leather Armor + Shortswords",
                "Leather Armor + Shortbow + Quiver",
            ]
        elif c in ("wizard", "sorcerer", "warlock"):
            options = [
                "Scholar's Pack + Component Pouch",
                "Explorer's Pack + Arcane Focus",
            ]
        elif c in ("cleric", "druid"):
            options = [
                "Scale Mail + Shield + Holy Symbol",
                "Leather Armor + Wooden Shield",
            ]
        elif c == "barbarian":
            options = [
                "Greataxe + Explorer's Pack",
                "Two Handaxes + Explorer's Pack",
            ]
        else:
            options = ["Standard Adventurer's Kit"]

        for j, opt in enumerate(options, 1):
            self.console.print(f"  [{FORGE_CYAN}]{j}[/] {opt}")

        if len(options) > 1:
            valid = [str(n) for n in range(1, len(options) + 1)]
            pick = self._prompt("  Choose loadout", valid, default="1")
            self.sheet.inventory = [options[int(pick) - 1]]
        else:
            self.sheet.inventory = [options[0]]
            self.console.print(f"  [dim]Equipped: {options[0]}[/dim]")

    def _parse_numbered_list(self, text: str) -> List[str]:
        """Extract items from a numbered list in AI response text."""
        import re
        items = []
        for line in text.splitlines():
            m = re.match(r'^\s*\d+[\.\)]\s*\**(.+?)(?:\*\*)?(?:\s*[-–:].*)?$', line)
            if m:
                name = m.group(1).strip().rstrip('*').strip()
                if name:
                    items.append(name)
        return items

    def _step_subrace(self):
        """Subrace selection from reference data."""
        race = self.sheet.race
        if not race:
            return
        try:
            from codex.forge.reference_data.loader import load_reference, filter_by_source, get_available_sources
            subraces_data = load_reference("subraces")
            available = get_available_sources()
        except ImportError:
            return

        race_key = race.lower().replace(" ", "_")
        options = subraces_data.get(race_key, [])
        if not options:
            return
        options = filter_by_source(options, available)
        if not options:
            return

        self.console.print(f"\n[bold {FORGE_GOLD}]Subrace[/]")
        self.console.print(f"  [dim]Choose a subrace for {race.replace('_', ' ').title()}[/dim]")
        for j, opt in enumerate(options, 1):
            bonuses = opt.get("bonuses", {})
            bonus_str = ", ".join(f"+{v} {k.title()}" for k, v in bonuses.items()) if bonuses else ""
            traits = ", ".join(opt.get("traits", []))
            desc = " | ".join(p for p in [bonus_str, traits] if p)
            self.console.print(f"  [{FORGE_CYAN}]{j}[/] {opt['name']}  [dim]({desc})[/dim]")
        self.console.print(f"  [{FORGE_CYAN}]0[/] [dim]Skip[/dim]")

        valid = [str(n) for n in range(0, len(options) + 1)]
        pick = self._prompt("  Choice", valid, default="1")
        idx = int(pick)
        if idx > 0:
            chosen = options[idx - 1]
            self.sheet.subrace = chosen["name"]
            for stat, bonus in chosen.get("bonuses", {}).items():
                stat_key = stat.title()
                if stat_key in self.sheet.stats:
                    self.sheet.stats[stat_key] += bonus
            self.console.print(f"  [dim]Subrace set: {self.sheet.subrace}[/dim]")

    def _step_subclass(self):
        """Subclass selection from reference data."""
        cls = self.sheet.character_class
        if not cls:
            self.sheet.subclass = "Heroic Archetype"
            return
        try:
            from codex.forge.reference_data.loader import load_reference, filter_by_source, get_available_sources
            subclasses_data = load_reference("subclasses")
            available = get_available_sources()
        except ImportError:
            self.sheet.subclass = "Heroic Archetype"
            return

        cls_key = cls.lower().replace(" ", "_")
        options = subclasses_data.get(cls_key, [])
        if not options:
            self.sheet.subclass = "Heroic Archetype"
            return
        options = filter_by_source(options, available)
        if not options:
            self.sheet.subclass = "Heroic Archetype"
            return

        self.console.print(f"\n[bold {FORGE_GOLD}]Subclass[/]")
        self.console.print(f"  [dim]Choose an archetype for {cls.replace('_', ' ').title()}[/dim]")
        for j, opt in enumerate(options, 1):
            source_tag = f"[dim]({opt.get('source', 'PHB')})[/dim]"
            self.console.print(f"  [{FORGE_CYAN}]{j}[/] {opt['name']}  {source_tag}")

        valid = [str(n) for n in range(1, len(options) + 1)]
        pick = self._prompt("  Choice", valid, default="1")
        self.sheet.subclass = options[int(pick) - 1]["name"]
        self.console.print(f"  [dim]Archetype set: {self.sheet.subclass}[/dim]")

    def _step_feats(self):
        """Feat selection from reference data."""
        try:
            from codex.forge.reference_data.loader import load_reference, filter_by_source, get_available_sources
            feats_data = load_reference("feats")
            available = get_available_sources()
        except ImportError:
            return
        if not feats_data:
            return

        feat_list = list(feats_data.values()) if isinstance(feats_data, dict) else feats_data
        feat_list = filter_by_source(feat_list, available)
        if not feat_list:
            return

        self.console.print(f"\n[bold {FORGE_GOLD}]Feats[/]")
        self.console.print(f"  [dim]Choose a feat (or skip)[/dim]")

        # Two-column grid for full feat list
        grid = Table.grid(padding=(0, 3))
        grid.add_column(min_width=35)
        grid.add_column(min_width=35)
        rows = []
        for j, feat in enumerate(feat_list, 1):
            desc = feat.get("description", "")
            rows.append(f"[{FORGE_CYAN}]{j:>2}[/] {feat['name']}  [dim]{desc}[/dim]")
        for r in range(0, len(rows), 2):
            left = rows[r]
            right = rows[r + 1] if r + 1 < len(rows) else ""
            grid.add_row(left, right)
        self.console.print(grid)
        self.console.print(f"  [{FORGE_CYAN}] 0[/] [dim]Skip[/dim]")

        valid = [str(n) for n in range(0, len(feat_list) + 1)]
        pick = self._prompt("  Choice", valid, default="0")
        idx = int(pick)
        if idx > 0:
            self.sheet.feats = [feat_list[idx - 1]["name"]]
            self.console.print(f"  [dim]Feat selected: {self.sheet.feats[0]}[/dim]")

    def _step_fighting_style(self, sheet: "CharacterSheet", con: Console) -> None:
        """Fighting style selection for Fighter, Paladin, and Ranger."""
        cls = sheet.character_class.lower()
        if cls not in ("fighter", "paladin", "ranger"):
            return

        # PHB fighting styles + Tasha's Cauldron of Everything (TCE) additions
        FIGHTING_STYLES = {
            "fighter": [
                "Archery (+2 to ranged attack rolls)",
                "Blind Fighting (blindsight 10 ft.)",
                "Defense (+1 AC while wearing armor)",
                "Dueling (+2 damage with one-handed weapon, no off-hand)",
                "Great Weapon Fighting (reroll 1s and 2s on two-handed damage)",
                "Interception (reduce ally damage by 1d10 + prof bonus as reaction)",
                "Protection (impose disadvantage on attacks against adjacent allies)",
                "Superior Technique (learn one Battle Master maneuver, gain d6 superiority die)",
                "Thrown Weapon Fighting (draw thrown weapon as part of attack, +2 damage)",
                "Two-Weapon Fighting (add ability modifier to off-hand damage)",
                "Unarmed Fighting (1d6+STR unarmed, 1d8 with both hands free)",
            ],
            "paladin": [
                "Blessed Warrior (learn two cleric cantrips, Charisma spellcasting)",
                "Blind Fighting (blindsight 10 ft.)",
                "Defense (+1 AC while wearing armor)",
                "Dueling (+2 damage with one-handed weapon, no off-hand)",
                "Great Weapon Fighting (reroll 1s and 2s on two-handed damage)",
                "Interception (reduce ally damage by 1d10 + prof bonus as reaction)",
                "Protection (impose disadvantage on attacks against adjacent allies)",
            ],
            "ranger": [
                "Archery (+2 to ranged attack rolls)",
                "Blind Fighting (blindsight 10 ft.)",
                "Defense (+1 AC while wearing armor)",
                "Druidic Warrior (learn two druid cantrips, Wisdom spellcasting)",
                "Dueling (+2 damage with one-handed weapon, no off-hand)",
                "Thrown Weapon Fighting (draw thrown weapon as part of attack, +2 damage)",
                "Two-Weapon Fighting (add ability modifier to off-hand damage)",
            ],
        }

        styles = FIGHTING_STYLES.get(cls, [])
        if not styles:
            return

        con.print(f"\n[bold]Fighting Style[/bold] — Choose your combat specialization:")
        for i, style in enumerate(styles, 1):
            con.print(f"  [yellow]{i}[/] {style}")

        sheet.fighting_styles = []  # Clear on re-entry
        valid = [str(n) for n in range(1, len(styles) + 1)]
        choice = self._prompt(f"  Style [1-{len(styles)}]", valid, default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(styles):
                style_name = styles[idx].split(" (")[0]
                sheet.fighting_styles.append(style_name)
                con.print(f"  [green]Fighting Style: {style_name}[/]")
            else:
                sheet.fighting_styles.append(styles[0].split(" (")[0])
        except (ValueError, IndexError):
            sheet.fighting_styles.append(styles[0].split(" (")[0])

    def _step_skill_proficiency(self):
        """Skill proficiency selection based on class and background."""
        try:
            from codex.forge.reference_data.loader import load_reference
            class_skills = load_reference("class_skills")
            bg_skills = load_reference("backgrounds")
            saving_throws = load_reference("saving_throws")
        except ImportError:
            return

        cls = self.sheet.character_class.lower()

        # Apply saving throw proficiencies
        saves = saving_throws.get(cls, [])
        if isinstance(saves, list):
            self.sheet.saving_throw_proficiencies = list(saves)
            if saves:
                self.console.print(f"\n[{FORGE_DIM}]Saving Throws: {', '.join(s.title() for s in saves)}[/]")

        # Apply background skill grants
        bg = self.sheet.choices.get("background", {})
        bg_id = bg.get("id", "") if isinstance(bg, dict) else str(bg)
        bg_id = bg_id.lower().replace(" ", "_")
        granted = bg_skills.get(bg_id, [])
        if isinstance(granted, list):
            self.sheet.skill_proficiencies.extend(granted)
            if granted:
                self.console.print(f"[{FORGE_DIM}]Background skills: {', '.join(s.replace('_', ' ').title() for s in granted)}[/]")

        # Class skill choices
        skill_info = class_skills.get(cls, {"pick": 2, "from": []})
        pick_count = skill_info.get("pick", 2)
        skill_pool = skill_info.get("from", [])

        if skill_pool == "any":
            try:
                all_skills = load_reference("skills")
                skill_pool = list(all_skills.keys())
            except Exception:
                skill_pool = []

        # Remove already-granted skills
        skill_pool = [s for s in skill_pool if s not in self.sheet.skill_proficiencies]
        if not skill_pool or pick_count <= 0:
            return

        self.console.print(f"\n[bold {FORGE_GOLD}]Skill Proficiencies[/]")
        self.console.print(f"  [dim]Choose {pick_count} skills for {cls.title()}[/dim]")

        chosen = []
        pick_num = 0
        while pick_num < pick_count:
            remaining = [s for s in skill_pool if s not in chosen]
            if not remaining:
                break
            for j, skill in enumerate(remaining, 1):
                self.console.print(f"  [{FORGE_CYAN}]{j}[/] {skill.replace('_', ' ').title()}")
            valid = [str(n) for n in range(1, len(remaining) + 1)]
            try:
                choice = self._prompt(f"  Skill {pick_num+1}/{pick_count}", valid, default="1")
            except self._BackStep:
                if chosen:
                    undone = chosen.pop()
                    pick_num -= 1
                    self.console.print(f"  [dim]Undid: {undone.replace('_', ' ').title()}[/dim]")
                    continue
                else:
                    raise  # Propagate to post-step loop
            picked = remaining[int(choice) - 1]
            chosen.append(picked)
            pick_num += 1
            self.console.print(f"  [dim]Added: {picked.replace('_', ' ').title()}[/dim]")

        self.sheet.skill_proficiencies = list(granted) if isinstance(granted, list) else []
        self.sheet.skill_proficiencies.extend(chosen)

    def _step_spell_selection(self):
        """Spell selection for spellcasting classes."""
        cls = self.sheet.character_class.lower()
        try:
            from codex.forge.reference_data.loader import load_reference
            spellcasting = load_reference("spellcasting")
            spell_lists = load_reference("spells")
        except ImportError:
            return

        casting_info = spellcasting.get(cls)
        if not casting_info:
            return
        class_spells = spell_lists.get(cls, {})
        if not class_spells:
            return

        level = self.sheet.level

        # Cantrips
        cantrip_counts = casting_info.get("cantrips", {})
        num_cantrips = 0
        for lvl_threshold in sorted(cantrip_counts.keys(), key=lambda k: int(k)):
            if level >= int(lvl_threshold):
                num_cantrips = cantrip_counts[lvl_threshold]

        cantrip_list = class_spells.get(0, class_spells.get("0", []))
        if num_cantrips > 0 and cantrip_list:
            self.console.print(f"\n[bold {FORGE_GOLD}]Cantrips[/]")
            self.console.print(f"  [dim]Choose {num_cantrips} cantrips[/dim]")
            chosen_cantrips = []
            pick_num = 0
            while pick_num < min(num_cantrips, len(cantrip_list)):
                remaining = [s for s in cantrip_list if s not in chosen_cantrips]
                if not remaining:
                    break
                grid = Table.grid(padding=(0, 3))
                grid.add_column(min_width=30)
                grid.add_column(min_width=30)
                rows = []
                for j, spell in enumerate(remaining, 1):
                    rows.append(f"[{FORGE_CYAN}]{j:>2}[/] {spell}")
                for r in range(0, len(rows), 2):
                    left = rows[r]
                    right = rows[r + 1] if r + 1 < len(rows) else ""
                    grid.add_row(left, right)
                self.console.print(grid)
                valid = [str(n) for n in range(1, len(remaining) + 1)]
                try:
                    choice = self._prompt(f"  Cantrip {pick_num+1}/{num_cantrips}", valid, default="1")
                except self._BackStep:
                    if chosen_cantrips:
                        chosen_cantrips.pop()
                        pick_num -= 1
                        continue
                    else:
                        raise
                chosen_cantrips.append(remaining[int(choice) - 1])
                pick_num += 1
            self.sheet.cantrips_known = chosen_cantrips
            self.console.print(f"  [dim]Cantrips: {', '.join(chosen_cantrips)}[/dim]")

        # Level 1 spells
        casting_type = casting_info.get("type", "known")
        spell_1_list = class_spells.get(1, class_spells.get("1", []))
        if not spell_1_list:
            return

        if casting_type == "known":
            spells_known_table = casting_info.get("spells_known", {})
            num_spells = 0
            for lvl_threshold in sorted(spells_known_table.keys(), key=lambda k: int(k)):
                if level >= int(lvl_threshold):
                    num_spells = spells_known_table[lvl_threshold]
        else:
            ability = casting_info.get("ability", "wisdom")
            mod = (self.sheet.stats.get(ability.title(), 10) - 10) // 2
            num_spells = max(1, mod + level)

        if num_spells > 0 and spell_1_list:
            action = "prepare" if casting_type == "prepared" else "learn"
            self.console.print(f"\n[bold {FORGE_GOLD}]Level 1 Spells[/]")
            self.console.print(f"  [dim]Choose {num_spells} spells to {action}[/dim]")
            chosen_spells = []
            pick_num = 0
            while pick_num < min(num_spells, len(spell_1_list)):
                remaining = [s for s in spell_1_list if s not in chosen_spells]
                if not remaining:
                    break
                grid = Table.grid(padding=(0, 3))
                grid.add_column(min_width=30)
                grid.add_column(min_width=30)
                rows = []
                for j, spell in enumerate(remaining, 1):
                    rows.append(f"[{FORGE_CYAN}]{j:>2}[/] {spell}")
                for r in range(0, len(rows), 2):
                    left = rows[r]
                    right = rows[r + 1] if r + 1 < len(rows) else ""
                    grid.add_row(left, right)
                self.console.print(grid)
                valid = [str(n) for n in range(1, len(remaining) + 1)]
                try:
                    choice = self._prompt(f"  Spell {pick_num+1}/{num_spells}", valid, default="1")
                except self._BackStep:
                    if chosen_spells:
                        chosen_spells.pop()
                        pick_num -= 1
                        continue
                    else:
                        raise
                chosen_spells.append(remaining[int(choice) - 1])
                pick_num += 1
            self.sheet.spells_known = chosen_spells
            self.console.print(f"  [dim]Spells: {', '.join(chosen_spells)}[/dim]")

    def _step_alignment(self):
        """Alignment selection."""
        alignments = [
            {"id": "lg", "name": "Lawful Good"}, {"id": "ng", "name": "Neutral Good"},
            {"id": "cg", "name": "Chaotic Good"}, {"id": "ln", "name": "Lawful Neutral"},
            {"id": "tn", "name": "True Neutral"}, {"id": "cn", "name": "Chaotic Neutral"},
            {"id": "le", "name": "Lawful Evil"}, {"id": "ne", "name": "Neutral Evil"},
            {"id": "ce", "name": "Chaotic Evil"},
        ]
        try:
            from codex.forge.reference_data.loader import load_reference
            loaded = load_reference("alignments")
            if loaded:
                if isinstance(loaded, dict):
                    # Reference data is {id: display_name} — convert to list-of-dicts
                    alignments = [{"id": k, "name": v} for k, v in loaded.items()]
                else:
                    alignments = loaded
        except ImportError:
            pass

        self.console.print(f"\n[bold {FORGE_GOLD}]Alignment[/]")
        for j, a in enumerate(alignments, 1):
            self.console.print(f"  [{FORGE_CYAN}]{j}[/] {a['name']}")
        valid = [str(n) for n in range(1, len(alignments) + 1)]
        choice = self._prompt("  Alignment", valid, default="5")
        self.sheet.alignment = alignments[int(choice) - 1]["name"]
        self.console.print(f"  [dim]Alignment: {self.sheet.alignment}[/dim]")

    def _step_personality(self):
        """Personality traits selection from background tables."""
        try:
            from codex.forge.reference_data.loader import load_reference
            personality_data = load_reference("personality")
        except ImportError:
            return

        bg = self.sheet.choices.get("background", {})
        bg_id = bg.get("id", "") if isinstance(bg, dict) else str(bg)
        bg_id = bg_id.lower().replace(" ", "_")
        bg_personality = personality_data.get(bg_id, {})
        if not bg_personality:
            return

        for category, field_name, label in [
            ("traits", "personality_traits", "Personality Trait"),
            ("ideals", "ideals", "Ideal"),
            ("bonds", "bonds", "Bond"),
            ("flaws", "flaws", "Flaw"),
        ]:
            options = bg_personality.get(category, [])
            if not options:
                continue
            self.console.print(f"\n[bold {FORGE_GOLD}]{label}[/]")
            for j, opt in enumerate(options[:8], 1):
                self.console.print(f"  [{FORGE_CYAN}]{j}[/] [dim]{opt}[/dim]")
            valid = [str(n) for n in range(1, min(len(options), 8) + 1)]
            choice = self._prompt(f"  {label}", valid, default="1")
            setattr(self.sheet, field_name, [options[int(choice) - 1]])

    def _step_text(self, step: Dict):
        label = step.get("label", "Input")
        prompt_text = step.get("prompt", "Enter value:")
        self.console.print(f"[bold {FORGE_GOLD}]{label}[/]")
        value = Prompt.ask(f"  {prompt_text}", console=self.console)
        if value.strip().lower() in ("back", "b"):
            raise self._BackStep()
        step_id = step.get("id", label.lower())
        self.sheet.choices[step_id] = value
        if step_id == "name":
            self.sheet.name = value

    def _step_choice(self, step: Dict):
        label = step.get("label", "Choose")
        prompt_text = step.get("prompt", "Select one:")
        options = step.get("options", [])

        # Filter options by available vault sources
        available = scan_content_availability()
        options = [o for o in options
                   if o.get("required_source", "Core") in available]

        self.console.print(f"[bold {FORGE_GOLD}]{label}[/]")
        self.console.print(f"  [dim]{prompt_text}[/]")

        if len(options) > 10:
            # Compact 2-column grid for long lists
            grid = Table.grid(padding=(0, 3))
            grid.add_column(min_width=35)
            grid.add_column(min_width=35)
            rows = []
            for j, opt in enumerate(options, 1):
                desc = opt.get("description", "")
                cell = f"[{FORGE_CYAN}]{j:>2}[/] {opt['label']}"
                if desc:
                    cell += f"  [dim]- {desc}[/]"
                rows.append(cell)
            # Pair into 2-column rows
            for r in range(0, len(rows), 2):
                left = rows[r]
                right = rows[r + 1] if r + 1 < len(rows) else ""
                grid.add_row(left, right)
            self.console.print(grid)
        else:
            for j, opt in enumerate(options, 1):
                desc = opt.get("description", "")
                self.console.print(
                    f"  [{FORGE_CYAN}]{j}[/] {opt['label']}"
                    + (f"  [dim]- {desc}[/]" if desc else "")
                )

        valid = [str(n) for n in range(1, len(options) + 1)]
        valid.extend(["back", "b"])
        choice = Prompt.ask("  Choice", choices=valid, default="1", console=self.console)
        if choice.lower() in ("back", "b"):
            raise self._BackStep()
        picked = options[int(choice) - 1]
        self.sheet.choices[step.get("id", label.lower())] = picked

    def _step_stat_roll(self, step: Dict):
        label = step.get("label", "Roll Stats")
        method = step.get("method", "roll_4d6_drop_lowest")
        assign_to = step.get("assign_to", self.schema.stats)

        self.console.print(f"[bold {FORGE_GOLD}]{label}[/]")

        rolls = []
        for _ in assign_to:
            if method == "roll_4d6_drop_lowest":
                dice = sorted([random.randint(1, 6) for _ in range(4)])
                total = sum(dice[1:])  # drop lowest
                rolls.append(total)
            else:
                rolls.append(10)  # default fallback

        # Display rolled values
        roll_display = "  ".join(
            f"[{FORGE_CYAN}]{r}[/]" for r in rolls
        )
        self.console.print(f"  Rolled: {roll_display}")

        # Assign in order
        for stat_name, value in zip(assign_to, rolls):
            self.sheet.stats[stat_name] = value

        stat_line = "  ".join(
            f"{name}: [{FORGE_BONE}]{val}[/]" for name, val in self.sheet.stats.items()
        )
        self.console.print(f"  Assigned: {stat_line}")

    def _step_stat_pool(self, step: Dict):
        """Roll a pool of scores via 4d6-drop-lowest, let player assign each."""
        label = step.get("label", "Allocate Stats")
        method = step.get("method", "roll_4d6_drop_lowest")
        assign_to = step.get("assign_to", self.schema.stats)

        self.console.print(f"[bold {FORGE_GOLD}]{label}[/]")

        # Roll the pool
        pool = []
        for _ in assign_to:
            if method == "roll_4d6_drop_lowest":
                dice = sorted([random.randint(1, 6) for _ in range(4)])
                total = sum(dice[1:])
                pool.append(total)
            else:
                pool.append(10)
        pool.sort(reverse=True)

        pool_display = ", ".join(f"[{FORGE_CYAN}]{v}[/]" for v in pool)
        self.console.print(f"  Your pool: [{pool_display}]")

        remaining = list(pool)
        assignments = []  # track (stat_name, chosen_value) for undo

        si = 0
        while si < len(assign_to):
            stat_name = assign_to[si]
            # Show remaining scores with indices
            avail = "  ".join(
                f"[{FORGE_CYAN}]{i+1}[/]={v}" for i, v in enumerate(remaining)
            )
            self.console.print(f"\n  Available: {avail}")
            valid = [str(n) for n in range(1, len(remaining) + 1)] + ["back", "b"]
            pick_str = Prompt.ask(
                f"  Assign to [{FORGE_BONE}]{stat_name}[/]? [1-{len(remaining)}]",
                choices=valid,
                console=self.console,
            )
            if pick_str.lower() in ("back", "b"):
                if si > 0:
                    # Undo last assignment
                    prev_stat, prev_val = assignments.pop()
                    remaining.append(prev_val)
                    remaining.sort(reverse=True)
                    del self.sheet.stats[prev_stat]
                    self.console.print(f"  [dim]Undoing {prev_stat} assignment...[/dim]")
                    si -= 1
                else:
                    raise self._BackStep()
                continue

            pick = int(pick_str)
            pick = max(1, min(pick, len(remaining)))
            chosen = remaining.pop(pick - 1)
            self.sheet.stats[stat_name] = chosen
            assignments.append((stat_name, chosen))
            self.console.print(
                f"  [{FORGE_BONE}]{stat_name}[/] = [{FORGE_CYAN}]{chosen}[/]"
            )
            si += 1

        # Final summary
        self.console.print()
        stat_line = "  ".join(
            f"{name}: [{FORGE_BONE}]{val}[/]" for name, val in self.sheet.stats.items()
        )
        self.console.print(f"  Final: {stat_line}")


# ---------------------------------------------------------------------------
# VIEWS: Paper Doll vs Stat Block
# ---------------------------------------------------------------------------
def render_stat_block_view(sheet: CharacterSheet, schema: CreationSchema) -> Panel:
    """Generic stat block for any system (D&D, BitD, SaV, etc.)."""
    content = Table.grid(padding=(0, 2))
    content.add_column(style=f"{FORGE_GOLD} bold", justify="right")
    content.add_column(style=FORGE_BONE, justify="left")

    for line in sheet.summary_lines():
        if ": " in line:
            key, val = line.split(": ", 1)
            content.add_row(key + ":", val)
        else:
            content.add_row("", line)

    # Derived stats
    if schema.derived:
        content.add_row("", "")
        for key, formula in schema.derived.items():
            content.add_row(key.upper() + ":", str(formula))

    return Panel(
        content,
        title=f"[bold {FORGE_GOLD}]{schema.display_name} Character[/]",
        subtitle=f"[dim]{schema.genre}[/]",
        border_style=FORGE_BORDER,
        box=box.DOUBLE,
        padding=(1, 2),
    )


def render_paper_doll_view(sheet: CharacterSheet, schema: CreationSchema) -> Panel:
    """Burnwillow-style paper doll view with gear slots and dice pips."""
    # Try to import the dedicated paper doll renderer
    try:
        from burnwillow_paper_doll import (
            render_paper_doll, Character as PDCharacter,
            CharacterStats as PDStats, GearItem as PDGear,
        )
        stats = PDStats(
            might=sheet.stats.get("Might", 10),
            wits=sheet.stats.get("Wits", 10),
            grit=sheet.stats.get("Grit", 10),
            aether=sheet.stats.get("Aether", 10),
        )
        char = PDCharacter(
            name=sheet.name or "Unnamed",
            title="The Wanderer",
            hp_current=stats.hp_max,
            stats=stats,
            doom=0,
        )
        return render_paper_doll(char, console_width=70)
    except ImportError:
        # Fallback: render as enhanced stat block with Burnwillow flavor
        pass

    # Fallback Burnwillow view
    content = Table.grid(padding=(0, 2))
    content.add_column(style=f"{FORGE_GOLD} bold", justify="right")
    content.add_column(style=FORGE_BONE, justify="left")

    content.add_row("Name:", sheet.name)

    loadout = sheet.choices.get("loadout", {})
    if isinstance(loadout, dict):
        content.add_row("Loadout:", loadout.get("label", "Unknown"))
        content.add_row("", f"[dim]{loadout.get('description', '')}[/]")

    if sheet.stats:
        content.add_row("", "")
        for stat, val in sheet.stats.items():
            mod = (val - 10) // 2
            sign = "+" if mod >= 0 else ""
            content.add_row(f"{stat}:", f"{val} ({sign}{mod})")

        grit = sheet.stats.get("Grit", 10)
        hp = 10 + (grit - 10) // 2
        wits = sheet.stats.get("Wits", 10)
        defense = 10 + (wits - 10) // 2
        content.add_row("", "")
        content.add_row("HP:", str(hp))
        content.add_row("DEF:", str(defense))

    return Panel(
        content,
        title=f"[bold {FORGE_GOLD}]Burnwillow - Paper Doll[/]",
        subtitle="[dim]Dark Fantasy Roguelike[/]",
        border_style=FORGE_BORDER,
        box=box.DOUBLE,
        padding=(1, 2),
    )


def render_character(sheet: CharacterSheet, schema: CreationSchema) -> Panel:
    """Route to the correct view based on schema.view_type."""
    if schema.view_type == "paper_doll":
        return render_paper_doll_view(sheet, schema)
    return render_stat_block_view(sheet, schema)


# ---------------------------------------------------------------------------
# VAULT CONTENT BROWSER
# ---------------------------------------------------------------------------
def render_system_content_table(content: dict, system_name: str, console: Console):
    """Display available vault content (sourcebooks, settings, modules) as a Rich table.

    Args:
        content: Output of scan_system_content() with rules/settings/modules lists.
        system_name: Display name of the selected system.
        console: Rich Console instance.
    """
    has_any = any(content[k] for k in ("rules", "settings", "modules"))
    if not has_any:
        return

    lines = []
    if content["rules"]:
        lines.append(f"  [bold {FORGE_CYAN}]SOURCEBOOKS[/]")
        for i, item in enumerate(content["rules"], 1):
            lines.append(f"    {i}. {item['name']}")
        lines.append("")

    if content["settings"]:
        lines.append(f"  [bold {FORGE_CYAN}]SETTINGS & SUPPLEMENTS[/]")
        for item in content["settings"]:
            lines.append(f"    - {item['name']}")
        lines.append("")

    if content["modules"]:
        lines.append(f"  [bold {FORGE_CYAN}]ADVENTURE MODULES[/]")
        for item in content["modules"]:
            lines.append(f"    - {item['name']}")
        lines.append("")

    panel = Panel(
        "\n".join(lines),
        title=f"[bold {FORGE_GOLD}]Available Content: {system_name}[/]",
        border_style=FORGE_BORDER,
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# MAIN: Interactive Wizard
# ---------------------------------------------------------------------------
def main():
    console = Console()
    console.clear()

    # Banner
    console.print(Panel(
        "[bold]C.O.D.E.X. CHARACTER FORGE[/]\n"
        "[dim]Dynamic Character Builder v1.0[/]\n"
        "[dim]Systems loaded from vault/[/]",
        border_style=FORGE_BORDER,
        box=box.DOUBLE,
        title=f"[{FORGE_GOLD}]FORGE[/]",
        padding=(1, 4),
    ))

    # Discover systems
    engine = CharacterBuilderEngine()
    systems = engine.list_systems()

    if not systems:
        console.print(
            f"\n[bold {FORGE_RED}]No game systems found.[/]"
            f"\n  Place a creation_rules.json in each vault/ subfolder."
            f"\n  Scanned: {engine.vault_root}"
        )
        return

    # System selector — Rich Table with hierarchy (WO V5.3, V43.0)
    # Sort: parents first, then module-children grouped after their parent.
    # Sub-settings (setting_id != "") are hidden from the top-level menu;
    # they appear as a secondary prompt after the user selects the parent.
    parents = [s for s in systems if not s.parent_engine]
    modules = [s for s in systems if s.parent_engine and not s.setting_id]
    sub_settings = [s for s in systems if s.parent_engine and s.setting_id]
    ordered: List[CreationSchema] = []
    for p in parents:
        ordered.append(p)
        for c in modules:
            if c.parent_engine == p.system_id:
                ordered.append(c)
    # Append any orphaned modules
    for c in modules:
        if c not in ordered:
            ordered.append(c)

    tbl = Table(
        title=f"[bold {FORGE_GOLD}]Available Systems[/]",
        box=box.SIMPLE_HEAVY,
        border_style=FORGE_BORDER,
        show_lines=False,
        padding=(0, 1),
    )
    tbl.add_column("#", style=f"bold {FORGE_CYAN}", width=4, justify="right")
    tbl.add_column("System", style="bold white", min_width=22)
    tbl.add_column("Family", style="dim white", min_width=16)
    tbl.add_column("Genre", style=f"dim {FORGE_BONE}", min_width=20)

    for i, sys in enumerate(ordered, 1):
        if sys.parent_engine:
            # Indented module under parent
            name_display = f"  [dim]\u2514\u2500[/] {sys.display_name}"
            parent_schema = engine.get_system(sys.parent_engine)
            family = parent_schema.display_name if parent_schema else sys.parent_engine
        else:
            name_display = sys.display_name
            family = "\u2014"
        tbl.add_row(str(i), name_display, family, sys.genre)

    console.print()
    console.print(tbl)

    valid = [str(n) for n in range(1, len(ordered) + 1)]
    choice = Prompt.ask(
        f"\n  Select system",
        choices=valid,
        default="1",
        console=console,
    )
    selected = ordered[int(choice) - 1]

    # WO-V43.0: Sub-setting selector — if the chosen system has sub-settings,
    # offer a secondary prompt to narrow content to a specific world/region.
    child_settings = [s for s in sub_settings if s.parent_engine == selected.system_id]
    if child_settings:
        console.print(
            f"\n[bold {FORGE_GOLD}]{selected.display_name} — Choose Setting[/]"
        )
        console.print(f"  [dim]1.[/] All {selected.display_name} content")
        for j, cs in enumerate(child_settings, 2):
            console.print(f"  [dim]{j}.[/] {cs.display_name} — {cs.genre}")
        sub_valid = [str(n) for n in range(1, len(child_settings) + 2)]
        sub_choice = Prompt.ask(
            f"\n  Select setting",
            choices=sub_valid,
            default="1",
            console=console,
        )
        sub_idx = int(sub_choice)
        if sub_idx > 1:
            selected = child_settings[sub_idx - 2]

    console.print(
        f"\n[bold {FORGE_GOLD}]Building for: {selected.display_name}[/]"
        f"\n[dim]  {len(selected.steps)} creation steps | "
        f"View: {selected.view_type} | "
        f"Stats: {', '.join(selected.stats)}[/]"
    )

    # Show available vault content before character creation
    vault_content = scan_system_content(selected.vault_path)
    if selected.parent_engine:
        parent_schema = engine.get_system(selected.parent_engine)
        if parent_schema:
            parent_content = scan_system_content(parent_schema.vault_path)
            for category in ("rules", "settings", "modules"):
                seen = {item["path"] for item in vault_content.get(category, [])}
                for item in parent_content.get(category, []):
                    if item["path"] not in seen:
                        vault_content.setdefault(category, []).append(item)
    render_system_content_table(vault_content, selected.display_name, console)

    # Walk creation steps
    builder = SystemBuilder(selected, console)
    sheet = builder.run()

    # Render final character
    console.print()
    console.print(render_character(sheet, selected))

    # Save option
    save_dir = os.path.join(_ROOT, "saves")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{sheet.system_id}_{sheet.name or 'unnamed'}.json")

    do_save = Prompt.ask(
        f"\n  Save character to [dim]{save_path}[/]?",
        choices=["y", "n"],
        default="y",
        console=console,
    )
    if do_save == "y":
        save_data = {
            "system_id": sheet.system_id,
            "setting_id": sheet.setting_id,
            "name": sheet.name,
            "choices": sheet.choices,
            "stats": sheet.stats,
        }
        # Serialize choice dicts cleanly
        with open(save_path, "w") as f:
            json.dump(save_data, f, indent=2, default=str)
        console.print(f"  [{FORGE_CYAN}]Saved.[/]")

    console.print(f"\n[dim]Character Forge complete.[/]\n")


if __name__ == "__main__":
    main()

"""
codex/spatial/scene_data.py — Typed models for adventure module scene content.
================================================================================

Formalizes the untyped ``content_hints`` dicts found in Dragon Heist (and
other module) blueprints into typed dataclasses.

Architecture:
    SceneNPC       — named NPC with role, dialogue, and DM notes
    SceneEnemy     — enemy stat block for room encounters
    SceneLoot      — lootable item with value and description
    SceneData      — top-level container parsed from content_hints

The ``SceneData.from_content_hints()`` factory handles all existing Dragon
Heist JSON shapes (NPC dicts, enemy dicts, DC fields, service lists,
renovation options) without requiring any blueprint file rewrites.

WO-V51.0: The Foundation Sprint — Phase B1
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================================
# SCENE NPC
# =========================================================================

@dataclass
class SceneNPC:
    """A named NPC present in a room scene."""
    name: str
    role: str = ""
    dialogue: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "dialogue": self.dialogue,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SceneNPC":
        return cls(
            name=data.get("name", "Unknown"),
            role=data.get("role", ""),
            dialogue=data.get("dialogue", ""),
            notes=data.get("notes", ""),
        )


# =========================================================================
# SCENE ENEMY
# =========================================================================

@dataclass
class SceneEnemy:
    """An enemy stat block for a room encounter."""
    name: str
    hp: int = 10
    ac: int = 10
    attack: int = 3
    damage: str = "1d6"
    count: int = 1
    is_boss: bool = False
    notes: str = ""
    special: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "hp": self.hp,
            "ac": self.ac,
            "attack": self.attack,
            "damage": self.damage,
            "count": self.count,
        }
        if self.is_boss:
            d["is_boss"] = True
        if self.notes:
            d["notes"] = self.notes
        if self.special:
            d["special"] = list(self.special)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SceneEnemy":
        return cls(
            name=data.get("name", "Unknown"),
            hp=data.get("hp", 10),
            ac=data.get("ac", 10),
            attack=data.get("attack", 3),
            damage=data.get("damage", "1d6"),
            count=data.get("count", 1),
            is_boss=data.get("is_boss", False),
            notes=data.get("notes", ""),
            special=data.get("special", []),
        )


# =========================================================================
# SCENE LOOT
# =========================================================================

@dataclass
class SceneLoot:
    """A lootable item in a room scene."""
    name: str
    value: int = 0
    description: str = ""

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "value": self.value}
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SceneLoot":
        return cls(
            name=data.get("name", "Unknown"),
            value=data.get("value", 0),
            description=data.get("description", ""),
        )


# =========================================================================
# SCENE DATA
# =========================================================================

@dataclass
class SceneData:
    """Top-level typed container for room scene content.

    Parsed from the ``content_hints`` dict in module blueprint JSON files.
    """
    description: str = ""
    read_aloud: str = ""
    npcs: List[SceneNPC] = field(default_factory=list)
    enemies: List[SceneEnemy] = field(default_factory=list)
    loot: List[SceneLoot] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    event_triggers: List[str] = field(default_factory=list)
    investigation_dc: int = 0
    investigation_success: str = ""
    perception_dc: int = 0
    perception_success: str = ""
    lock_dc: int = 0
    renovation_options: List[dict] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Factory: parse untyped content_hints
    # ------------------------------------------------------------------

    @classmethod
    def from_content_hints(cls, hints: dict) -> "SceneData":
        """Parse a content_hints dict into a typed SceneData.

        Handles all existing Dragon Heist JSON shapes:
        - ``npcs``: list of NPC dicts → SceneNPC
        - ``enemies``: list of enemy dicts → SceneEnemy
        - ``loot``: list of loot dicts → SceneLoot
        - ``services``: list of strings
        - ``event_triggers``: list of strings
        - ``investigation_dc`` / ``investigation_success``
        - ``perception_dc`` / ``perception_success``
        - ``lock_dc``
        - ``renovation_options``: list of dicts (Trollskull format)
        - ``read_aloud``: narration text
        - ``description``: room description
        """
        npcs = [SceneNPC.from_dict(n) for n in hints.get("npcs", [])]
        enemies = [SceneEnemy.from_dict(e) for e in hints.get("enemies", [])]
        loot = [SceneLoot.from_dict(l) for l in hints.get("loot", [])]

        return cls(
            description=hints.get("description", ""),
            read_aloud=hints.get("read_aloud", ""),
            npcs=npcs,
            enemies=enemies,
            loot=loot,
            services=hints.get("services", []),
            event_triggers=hints.get("event_triggers", []),
            investigation_dc=hints.get("investigation_dc", 0),
            investigation_success=hints.get("investigation_success", ""),
            perception_dc=hints.get("perception_dc", 0),
            perception_success=hints.get("perception_success", ""),
            lock_dc=hints.get("lock_dc", 0),
            renovation_options=hints.get("renovation_options", []),
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        d: dict = {}
        if self.description:
            d["description"] = self.description
        if self.read_aloud:
            d["read_aloud"] = self.read_aloud
        if self.npcs:
            d["npcs"] = [n.to_dict() for n in self.npcs]
        if self.enemies:
            d["enemies"] = [e.to_dict() for e in self.enemies]
        if self.loot:
            d["loot"] = [l.to_dict() for l in self.loot]
        if self.services:
            d["services"] = list(self.services)
        if self.event_triggers:
            d["event_triggers"] = list(self.event_triggers)
        if self.investigation_dc:
            d["investigation_dc"] = self.investigation_dc
        if self.investigation_success:
            d["investigation_success"] = self.investigation_success
        if self.perception_dc:
            d["perception_dc"] = self.perception_dc
        if self.perception_success:
            d["perception_success"] = self.perception_success
        if self.lock_dc:
            d["lock_dc"] = self.lock_dc
        if self.renovation_options:
            d["renovation_options"] = list(self.renovation_options)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SceneData":
        """Deserialize from a dict (output of to_dict)."""
        return cls.from_content_hints(data)

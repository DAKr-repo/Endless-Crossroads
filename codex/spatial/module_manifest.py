#!/usr/bin/env python3
"""
codex/spatial/module_manifest.py - Module Manifest System
==========================================================

Describes the complete structure of an adventure module: its chapters, zone
ordering, world map reference, and freeform sandbox zones.

A ModuleManifest acts as the "table of contents" for a module — it tells the
engine which zones to load in order and how they connect, without hard-coding
any game logic into the manifest itself.

Architecture:
    ZoneEntry       -- single zone descriptor (blueprint path or procedural params)
    Chapter         -- ordered list of ZoneEntries grouped by story act
    ModuleManifest  -- top-level container; serializes to/from JSON file

Version: 1.0
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# =============================================================================
# ZONE ENTRY
# =============================================================================

@dataclass
class ZoneEntry:
    """
    Descriptor for a single zone in a module.

    A zone can be either hand-authored (blueprint JSON) or fully procedural.
    If ``blueprint`` is set, the ZoneLoader reads geometry from that file.
    If ``blueprint`` is None, the ZoneLoader generates geometry from
    ``generation_params``.

    Attributes:
        zone_id:           Unique identifier for this zone within the module.
        blueprint:         Relative path to a JSON blueprint file, or None for
                           procedural generation.
        topology:          Geometry mode: dungeon/wilderness/vertical/settlement.
        theme:             MapTheme name for rendering (RUST/STONE/GOTHIC/NEON).
        location_id:       World map location this zone is entered from.
        entry_trigger:     When does the player enter this zone?
                           module_start / boss_defeated / quest_complete /
                           player_choice.
        exit_trigger:      What condition exits this zone and advances the chapter?
                           boss_defeated / quest_complete / player_choice / timer.
        generation_params: Dict of generation kwargs for procedural zones.
                           Recognised keys: width, height, max_depth, seed,
                           room_count, floors, rooms_per_floor.
    """

    zone_id: str
    blueprint: Optional[str] = None
    topology: str = "dungeon"
    theme: str = "STONE"
    location_id: str = ""
    entry_trigger: str = "module_start"
    exit_trigger: str = "boss_defeated"
    generation_params: Optional[dict] = None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        d: dict = {
            "zone_id": self.zone_id,
            "topology": self.topology,
            "theme": self.theme,
            "location_id": self.location_id,
            "entry_trigger": self.entry_trigger,
            "exit_trigger": self.exit_trigger,
        }
        if self.blueprint is not None:
            d["blueprint"] = self.blueprint
        if self.generation_params is not None:
            d["generation_params"] = dict(self.generation_params)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ZoneEntry":
        """Deserialize from a dictionary (backward-compatible)."""
        return cls(
            zone_id=data["zone_id"],
            blueprint=data.get("blueprint", None),
            topology=data.get("topology", "dungeon"),
            theme=data.get("theme", "STONE"),
            location_id=data.get("location_id", ""),
            entry_trigger=data.get("entry_trigger", "module_start"),
            exit_trigger=data.get("exit_trigger", "boss_defeated"),
            generation_params=data.get("generation_params", None),
        )


# =============================================================================
# CHAPTER
# =============================================================================

@dataclass
class Chapter:
    """
    A named act grouping an ordered sequence of zones.

    Chapters are traversed in ascending ``order`` value. Within a chapter,
    zones are traversed in list order.

    Attributes:
        chapter_id:   Unique identifier (e.g. "act_1").
        display_name: Human-readable title (e.g. "Act I: The Descent").
        order:        Integer sort key (lower = earlier in module).
        zones:        Ordered list of ZoneEntry descriptors for this chapter.
    """

    chapter_id: str
    display_name: str
    order: int
    zones: List[ZoneEntry] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "chapter_id": self.chapter_id,
            "display_name": self.display_name,
            "order": self.order,
            "zones": [z.to_dict() for z in self.zones],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chapter":
        """Deserialize from a dictionary."""
        zones = [ZoneEntry.from_dict(z) for z in data.get("zones", [])]
        return cls(
            chapter_id=data["chapter_id"],
            display_name=data["display_name"],
            order=data.get("order", 0),
            zones=zones,
        )


# =============================================================================
# MODULE MANIFEST
# =============================================================================

@dataclass
class ModuleManifest:
    """
    Top-level descriptor for a complete adventure module.

    A module is a structured collection of chapters (linear progression) and
    optional freeform zones (sandbox/side content). It optionally references
    a WorldMap JSON file for overworld navigation.

    Attributes:
        module_id:           Machine-readable unique ID (e.g. "the_sunken_vault").
        display_name:        Human-readable title.
        system_id:           Game system (e.g. "burnwillow", "dnd5e").
        source_pdf:          Optional path to the source PDF for librarian indexing.
        world_map:           Optional path to the world_map.json for this module.
        starting_location:   Location ID where the party begins.
        recommended_levels:  Dict with "min" and "max" integer level keys.
        chapters:            Ordered list of Chapter objects.
        freeform_zones:      Sandbox zones available at any time (side content).
    """

    module_id: str
    display_name: str
    system_id: str
    source_pdf: Optional[str] = None
    world_map: Optional[str] = None
    starting_location: str = ""
    recommended_levels: dict = field(default_factory=lambda: {"min": 1, "max": 5})
    chapters: List[Chapter] = field(default_factory=list)
    freeform_zones: List[ZoneEntry] = field(default_factory=list)
    # WO-V55.0: Campaign setting for lore integration (e.g. "forgotten_realms")
    campaign_setting: str = ""
    # WO-V60.0: System transitions — optional triggers for cross-system stacking
    # Each dict: {"target_system": "sav", "trigger": "zone_complete", "zone_id": "escape_pod"}
    system_transitions: List[dict] = field(default_factory=list)
    # WO-V70.0: Source type — provenance of the module content
    # Values: "community_authored" | "publisher_licensed" | "" (unknown/unset)
    source_type: str = ""

    # ------------------------------------------------------------------
    # Zone traversal helpers
    # ------------------------------------------------------------------

    def get_zone_chain(self) -> List[ZoneEntry]:
        """Return a flat ordered list of all chapter zones.

        Chapters are sorted by ``order`` before flattening. Freeform zones are
        NOT included (they are sandbox content, not linear progression).

        Returns:
            List[ZoneEntry] in traversal order.
        """
        sorted_chapters = sorted(self.chapters, key=lambda c: c.order)
        chain: List[ZoneEntry] = []
        for chapter in sorted_chapters:
            chain.extend(chapter.zones)
        return chain

    def get_next_zone(
        self,
        chapter_idx: int,
        zone_idx: int,
    ) -> Optional[Tuple[int, int, ZoneEntry]]:
        """Advance to the next zone in the module progression.

        Attempts to move to the next zone within the current chapter first.
        If the chapter is exhausted, advances to the first zone of the next
        chapter (sorted by order).

        Args:
            chapter_idx: Current chapter index (into the *sorted* chapters list).
            zone_idx:    Current zone index within that chapter.

        Returns:
            ``(new_chapter_idx, new_zone_idx, ZoneEntry)`` for the next zone,
            or ``None`` if the module is complete.
        """
        sorted_chapters = sorted(self.chapters, key=lambda c: c.order)
        if not sorted_chapters:
            return None

        # Clamp indices to valid range
        chapter_idx = max(0, min(chapter_idx, len(sorted_chapters) - 1))
        current_chapter = sorted_chapters[chapter_idx]

        next_zone_idx = zone_idx + 1

        # Try advancing within the current chapter
        if next_zone_idx < len(current_chapter.zones):
            return (chapter_idx, next_zone_idx, current_chapter.zones[next_zone_idx])

        # Try advancing to the next chapter
        next_chapter_idx = chapter_idx + 1
        if next_chapter_idx < len(sorted_chapters):
            next_chapter = sorted_chapters[next_chapter_idx]
            if next_chapter.zones:
                return (next_chapter_idx, 0, next_chapter.zones[0])

        # Module complete
        return None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize the manifest to a JSON-compatible dictionary."""
        d: dict = {
            "module_id": self.module_id,
            "display_name": self.display_name,
            "system_id": self.system_id,
            "starting_location": self.starting_location,
            "recommended_levels": dict(self.recommended_levels),
            "chapters": [c.to_dict() for c in self.chapters],
            "freeform_zones": [z.to_dict() for z in self.freeform_zones],
        }
        if self.source_pdf is not None:
            d["source_pdf"] = self.source_pdf
        if self.world_map is not None:
            d["world_map"] = self.world_map
        if self.campaign_setting:
            d["campaign_setting"] = self.campaign_setting
        if self.system_transitions:
            d["system_transitions"] = list(self.system_transitions)
        if self.source_type:
            d["source_type"] = self.source_type
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleManifest":
        """Deserialize from a dictionary."""
        chapters = [Chapter.from_dict(c) for c in data.get("chapters", [])]
        freeform = [ZoneEntry.from_dict(z) for z in data.get("freeform_zones", [])]
        return cls(
            module_id=data["module_id"],
            display_name=data["display_name"],
            system_id=data.get("system_id", ""),
            source_pdf=data.get("source_pdf", None),
            world_map=data.get("world_map", None),
            starting_location=data.get("starting_location", ""),
            recommended_levels=data.get("recommended_levels", {"min": 1, "max": 5}),
            chapters=chapters,
            freeform_zones=freeform,
            campaign_setting=data.get("campaign_setting", ""),
            system_transitions=data.get("system_transitions", []),
            source_type=data.get("source_type", ""),
        )

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "ModuleManifest":
        """Load a ModuleManifest from a JSON file.

        Args:
            path: Absolute or relative path to the manifest JSON.

        Returns:
            Populated ModuleManifest.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is malformed JSON.
        """
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    def save(self, path: str) -> None:
        """Persist this manifest to a JSON file.

        Args:
            path: Destination file path. Parent directories must exist.
        """
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)

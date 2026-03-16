#!/usr/bin/env python3
"""
codex/spatial/zone_manager.py - Zone Progression Manager
==========================================================

Shared zone progression manager that bridges ModuleManifest + ZoneLoader
into a stateful session-level object. Used by DnD5e, STC, Burnwillow,
and any engine that supports module-based zone progression.

Architecture:
    ZoneManager wraps a ModuleManifest and ZoneLoader. It tracks the
    current chapter/zone indices and provides advance() to move to the
    next zone when an exit condition is met. Fully serializable for
    save/load round-trips.

Broadcast Events:
    EVENT_ZONE_COMPLETE   - fired when a zone's exit condition is met
    EVENT_ZONE_TRANSITION - fired when advancing to a new zone
    EVENT_ZONE_TRAVEL     - fired when the player travels on the world map

Version: 1.0
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from codex.spatial.module_manifest import Chapter, ModuleManifest, ZoneEntry
from codex.spatial.zone_loader import ZoneLoader

logger = logging.getLogger(__name__)

# Broadcast event constants
EVENT_ZONE_COMPLETE = "ZONE_COMPLETE"
EVENT_ZONE_TRANSITION = "ZONE_TRANSITION"
EVENT_ZONE_TRAVEL = "ZONE_TRAVEL"


class ZoneManager:
    """
    Stateful zone progression manager for module-based campaigns.

    Wraps a ModuleManifest and ZoneLoader, tracks the player's current
    position in the module's chapter/zone chain, and provides methods
    to load zones, advance progression, and check exit conditions.

    Attributes:
        manifest:     The loaded ModuleManifest.
        loader:       ZoneLoader instance for blueprint/procedural zone loading.
        chapter_idx:  Current chapter index (into sorted chapters list).
        zone_idx:     Current zone index within the current chapter.
        module_complete: True when all chapters/zones have been traversed.
    """

    def __init__(
        self,
        manifest: ModuleManifest,
        base_path: str = "",
        broadcast_manager: Any = None,
    ) -> None:
        self.manifest = manifest
        self.loader = ZoneLoader(base_path=base_path)
        self.chapter_idx: int = 0
        self.zone_idx: int = 0
        self.module_complete: bool = False
        self._current_graph: Any = None  # DungeonGraph or None
        self._villain_path: str = ""     # WO-V51.0: villain path tag
        # WO-V56.0: Instance-level broadcast manager
        self._broadcast = broadcast_manager

    # ------------------------------------------------------------------
    # Zone chain helpers
    # ------------------------------------------------------------------

    @property
    def sorted_chapters(self) -> List[Chapter]:
        """Return chapters sorted by order."""
        return sorted(self.manifest.chapters, key=lambda c: c.order)

    @property
    def current_chapter(self) -> Optional[Chapter]:
        """Return the current Chapter object, or None if complete."""
        chapters = self.sorted_chapters
        if self.chapter_idx < len(chapters):
            return chapters[self.chapter_idx]
        return None

    @property
    def current_zone_entry(self) -> Optional[ZoneEntry]:
        """Return the current ZoneEntry, or None if complete."""
        chapter = self.current_chapter
        if chapter and self.zone_idx < len(chapter.zones):
            return chapter.zones[self.zone_idx]
        return None

    @property
    def module_name(self) -> str:
        return self.manifest.display_name

    @property
    def chapter_name(self) -> str:
        ch = self.current_chapter
        return ch.display_name if ch else ""

    @property
    def zone_name(self) -> str:
        ze = self.current_zone_entry
        return ze.zone_id if ze else ""

    @property
    def zone_progress(self) -> str:
        """Human-readable progress string like 'Chapter 2/5, Zone 1/3'."""
        chapters = self.sorted_chapters
        total_ch = len(chapters)
        ch = self.current_chapter
        total_z = len(ch.zones) if ch else 0
        return (
            f"Chapter {self.chapter_idx + 1}/{total_ch}, "
            f"Zone {self.zone_idx + 1}/{total_z}"
        )

    # ------------------------------------------------------------------
    # Zone loading
    # ------------------------------------------------------------------

    def load_current_zone(self) -> Any:
        """Load the DungeonGraph for the current zone.

        Returns the DungeonGraph (from ZoneLoader), or None if the module
        is complete.
        """
        entry = self.current_zone_entry
        if entry is None:
            self.module_complete = True
            return None

        self._current_graph = self.loader.load_zone(entry)
        logger.info(
            "ZoneManager: loaded zone '%s' (chapter %d, zone %d)",
            entry.zone_id, self.chapter_idx, self.zone_idx,
        )
        return self._current_graph

    @property
    def current_graph(self) -> Any:
        """Return the currently loaded DungeonGraph, or None."""
        return self._current_graph

    # ------------------------------------------------------------------
    # Progression
    # ------------------------------------------------------------------

    def advance(self) -> Optional[ZoneEntry]:
        """Advance to the next zone in the module.

        Moves to the next zone in the current chapter; if the chapter
        is exhausted, advances to the next chapter.  When a villain path
        is set, zones with non-matching ``villain_path_*`` triggers are
        skipped.

        Returns:
            The new ZoneEntry, or None if the module is complete.
        """
        result = self.manifest.get_next_zone(self.chapter_idx, self.zone_idx)
        if result is None:
            self.module_complete = True
            logger.info("ZoneManager: module '%s' complete!", self.manifest.module_id)
            return None

        new_ch_idx, new_z_idx, entry = result

        # WO-V51.0: Villain path filtering — skip zones that don't match
        if self._villain_path:
            trigger = entry.entry_trigger.lower()
            if trigger.startswith("villain_path_"):
                if trigger != f"villain_path_{self._villain_path}":
                    # Skip this zone and try next
                    self.chapter_idx = new_ch_idx
                    self.zone_idx = new_z_idx
                    return self.advance()

        self.chapter_idx = new_ch_idx
        self.zone_idx = new_z_idx
        self._current_graph = None  # Invalidate cached graph

        logger.info(
            "ZoneManager: advanced to chapter %d, zone %d ('%s')",
            new_ch_idx, new_z_idx, entry.zone_id,
        )

        # Broadcast zone transition event
        try:
            payload = {
                "module": self.manifest.module_id,
                "chapter": self.chapter_name,
                "zone": entry.zone_id,
                "progress": self.zone_progress,
            }
            # WO-V56.0: Use instance broadcast manager if available
            if self._broadcast:
                self._broadcast.broadcast(EVENT_ZONE_TRANSITION, payload)
        except Exception:
            pass

        return entry

    def check_exit_condition(self, game_state: dict) -> bool:
        """Check whether the current zone's exit condition is satisfied.

        Supported exit_trigger values:
            boss_defeated  - game_state["boss_defeated"] is truthy
            quest_complete - game_state["quest_complete"] is truthy
            player_choice  - always True (player manually chooses to leave)
            timer          - game_state["timer_expired"] is truthy
            all_rooms      - game_state.get("rooms_cleared") >= total rooms

        Args:
            game_state: Dict of current game state flags.

        Returns:
            True if the exit condition is met, False otherwise.
        """
        entry = self.current_zone_entry
        if entry is None:
            return False

        trigger = entry.exit_trigger.lower()

        if trigger == "boss_defeated":
            return bool(game_state.get("boss_defeated", False))
        elif trigger == "quest_complete":
            return bool(game_state.get("quest_complete", False))
        elif trigger == "investigation_complete":
            return bool(game_state.get("investigation_complete", False))
        elif trigger == "module_complete":
            return bool(game_state.get("module_complete", False))
        elif trigger == "player_choice":
            return True
        elif trigger == "timer":
            return bool(game_state.get("timer_expired", False))
        elif trigger == "all_rooms":
            graph = self._current_graph
            if graph is None:
                return False
            total = len(graph.rooms)
            cleared = game_state.get("rooms_cleared", 0)
            return cleared >= total
        else:
            logger.warning(
                "ZoneManager: unknown exit trigger '%s', defaulting to False",
                trigger,
            )
            return False

    def fire_zone_complete(self) -> None:
        """Broadcast that the current zone is complete."""
        try:
            entry = self.current_zone_entry
            payload = {
                "module": self.manifest.module_id,
                "chapter": self.chapter_name,
                "zone": entry.zone_id if entry else "",
                "progress": self.zone_progress,
            }
            # WO-V56.0: Use instance broadcast manager if available
            if self._broadcast:
                self._broadcast.broadcast(EVENT_ZONE_COMPLETE, payload)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # World map / travel
    # ------------------------------------------------------------------

    def get_world_map_path(self) -> Optional[str]:
        """Return the resolved world map path, or None."""
        wm = self.manifest.world_map
        if not wm:
            return None
        if os.path.isabs(wm) or not self.loader.base_path:
            return wm
        return os.path.join(self.loader.base_path, wm)

    def get_freeform_zones(self) -> List[ZoneEntry]:
        """Return sandbox/side-content zones available at any time."""
        return list(self.manifest.freeform_zones)

    # ------------------------------------------------------------------
    # Villain Path Routing (WO-V51.0)
    # ------------------------------------------------------------------

    def set_villain_path(self, path_tag: str) -> None:
        """Set the villain path for chapter filtering.

        When set, zones whose ``entry_trigger`` starts with ``villain_path_``
        are filtered to keep only those matching this tag.  Zones without
        a ``villain_path_*`` trigger are always kept.

        Args:
            path_tag: Villain identifier (e.g. "manshoon", "xanathar").
        """
        self._villain_path = path_tag.lower()
        logger.info("ZoneManager: villain path set to '%s'", self._villain_path)

    def _filter_zones_by_path(self, zones: List[ZoneEntry]) -> List[ZoneEntry]:
        """Filter zones by the active villain path.

        Keeps:
          - Zones whose entry_trigger does NOT start with ``villain_path_``
          - Zones whose entry_trigger is ``villain_path_{self._villain_path}``

        If no villain path is set, returns all zones unchanged (fallback).
        """
        if not self._villain_path:
            return zones

        filtered: List[ZoneEntry] = []
        for z in zones:
            trigger = z.entry_trigger.lower()
            if trigger.startswith("villain_path_"):
                # Keep only if it matches our chosen villain
                if trigger == f"villain_path_{self._villain_path}":
                    filtered.append(z)
            else:
                filtered.append(z)
        return filtered

    def get_villain_paths(self) -> List[str]:
        """Return available villain path tags from the current chapter.

        Scans the current chapter's zones for ``villain_path_*`` triggers
        and returns the unique path tags (e.g. ["manshoon", "cassalanter"]).
        """
        chapter = self.current_chapter
        if not chapter:
            return []
        paths = set()
        for z in chapter.zones:
            trigger = z.entry_trigger.lower()
            if trigger.startswith("villain_path_"):
                tag = trigger[len("villain_path_"):]
                paths.add(tag)
        return sorted(paths)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize zone progression state for save files."""
        d: Dict[str, Any] = {
            "module_id": self.manifest.module_id,
            "chapter_idx": self.chapter_idx,
            "zone_idx": self.zone_idx,
            "module_complete": self.module_complete,
        }
        if self._villain_path:
            d["villain_path"] = self._villain_path
        return d

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        manifest: ModuleManifest,
        base_path: str = "",
    ) -> "ZoneManager":
        """Restore ZoneManager state from a save dict.

        Args:
            data: Serialized state from to_dict().
            manifest: The ModuleManifest (must be loaded separately).
            base_path: Blueprint resolution path.

        Returns:
            Restored ZoneManager with indices set.
        """
        mgr = cls(manifest=manifest, base_path=base_path)
        mgr.chapter_idx = data.get("chapter_idx", 0)
        mgr.zone_idx = data.get("zone_idx", 0)
        mgr.module_complete = data.get("module_complete", False)
        mgr._villain_path = data.get("villain_path", "")
        return mgr

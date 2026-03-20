"""
codex/games/crown/scenes.py — Scene Progression for Crown & Crew
================================================================
Adds optional narrative scenes between morning and council phases.
Each campaign day can include a "scene" that presents location-specific
narrative with choices affecting sway. Backward compatible — campaigns
without scenes work exactly as before.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CrownScene:
    """A single narrative scene with branching choices."""
    scene_id: str
    description: str  # Read-aloud text
    location: str = ""  # Where this scene takes place
    choices: List[Dict[str, Any]] = field(default_factory=list)
    # Each choice: {"text": "Choose this", "sway_effect": +1/-1, "tag": "BLOOD", "next_scene": "scene_id or None"}
    resolved: bool = False
    chosen_index: Optional[int] = None

    def get_choice_texts(self) -> List[str]:
        """Return just the choice text strings for display."""
        return [c.get("text", "???") for c in self.choices]

    def resolve(self, choice_index: int) -> Dict[str, Any]:
        """Resolve a choice, returning its effects.

        Args:
            choice_index: Zero-based index into self.choices.

        Returns:
            dict with keys: sway_effect (int), tag (str),
            next_scene (Optional[str]), narrative (str)
        """
        if choice_index < 0 or choice_index >= len(self.choices):
            choice_index = 0
        choice = self.choices[choice_index]
        self.resolved = True
        self.chosen_index = choice_index
        return {
            "sway_effect": choice.get("sway_effect", 0),
            "tag": choice.get("tag", ""),
            "next_scene": choice.get("next_scene"),
            "narrative": choice.get("narrative", ""),
        }

    def to_dict(self) -> dict:
        """Serialize scene state to dict for save/load."""
        return {
            "scene_id": self.scene_id,
            "description": self.description,
            "location": self.location,
            "choices": self.choices,
            "resolved": self.resolved,
            "chosen_index": self.chosen_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrownScene":
        """Restore scene state from dict."""
        return cls(
            scene_id=data.get("scene_id", ""),
            description=data.get("description", ""),
            location=data.get("location", ""),
            choices=data.get("choices", []),
            resolved=data.get("resolved", False),
            chosen_index=data.get("chosen_index"),
        )


@dataclass
class CrownChapter:
    """A chapter containing multiple scenes tied to campaign days."""
    chapter_id: str
    display_name: str
    scenes: List[CrownScene] = field(default_factory=list)
    entry_condition: str = ""  # e.g. "day >= 1"
    exit_condition: str = ""   # e.g. "day >= 2"

    def get_scene_for_day(self, day: int) -> Optional[CrownScene]:
        """Get the next unresolved scene regardless of day index.

        The day parameter is accepted for API compatibility with future
        day-keyed lookup, but currently returns the first unresolved scene.

        Args:
            day: Current campaign day (1-based).

        Returns:
            First unresolved CrownScene, or None if all are resolved.
        """
        unresolved = [s for s in self.scenes if not s.resolved]
        if unresolved:
            return unresolved[0]
        return None

    def is_complete(self) -> bool:
        """Return True if all scenes in this chapter are resolved."""
        return all(s.resolved for s in self.scenes)

    def to_dict(self) -> dict:
        """Serialize chapter to dict."""
        return {
            "chapter_id": self.chapter_id,
            "display_name": self.display_name,
            "scenes": [s.to_dict() for s in self.scenes],
            "entry_condition": self.entry_condition,
            "exit_condition": self.exit_condition,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrownChapter":
        """Restore chapter from dict."""
        return cls(
            chapter_id=data.get("chapter_id", ""),
            display_name=data.get("display_name", ""),
            scenes=[CrownScene.from_dict(s) for s in data.get("scenes", [])],
            entry_condition=data.get("entry_condition", ""),
            exit_condition=data.get("exit_condition", ""),
        )


class CrownSceneRunner:
    """Processes scenes within the Crown & Crew day loop.

    Integrates with existing sway/voting mechanics. Each campaign day
    can optionally contain a "scene" phase between Morning and Council.

    Usage::

        runner = CrownSceneRunner(chapters)
        scene = runner.get_current_scene(day=engine.day)
        if scene:
            # Display scene.description
            # Show scene.get_choice_texts()
            # result = scene.resolve(player_choice)
            # engine.sway += result["sway_effect"]
            # engine.dna[result["tag"]] += 1
            runner.advance()

    Backward compatible — if chapters is empty or None, all methods
    behave safely: get_current_scene() returns None, is_complete()
    returns True, get_progress() returns "No scenes".
    """

    def __init__(self, chapters: Optional[List[CrownChapter]] = None) -> None:
        self.chapters: List[CrownChapter] = chapters or []
        self._current_chapter_idx: int = 0
        self._scene_history: List[dict] = []

    @classmethod
    def from_campaign_json(cls, campaign_data: dict) -> "CrownSceneRunner":
        """Build a scene runner from campaign.json scene definitions.

        Supports two JSON formats:

        1. ``"scene_chapters"`` — full chapter structure::

            {
              "scene_chapters": [
                {
                  "chapter_id": "act1",
                  "display_name": "Act One",
                  "scenes": [
                    {
                      "scene_id": "tavern_meeting",
                      "description": "A hooded figure...",
                      "location": "The Iron Tankard",
                      "choices": [
                        {"text": "Trust them", "sway_effect": 1, "tag": "HEARTH"},
                        {"text": "Refuse",     "sway_effect": -1, "tag": "GUILE"}
                      ]
                    }
                  ]
                }
              ]
            }

        2. ``"scenes_by_day"`` — simpler day-keyed format::

            {
              "scenes_by_day": {
                "1": {"scene_id": "...", "description": "...", "choices": [...]},
                "2": {...}
              }
            }

        Args:
            campaign_data: Parsed campaign.json dict.

        Returns:
            CrownSceneRunner instance (empty chapters if no scene data present).
        """
        chapters: List[CrownChapter] = []

        # Try chapters format first
        for ch_data in campaign_data.get("scene_chapters", []):
            scenes = []
            for s_data in ch_data.get("scenes", []):
                scenes.append(CrownScene(
                    scene_id=s_data.get("scene_id", ""),
                    description=s_data.get("description", ""),
                    location=s_data.get("location", ""),
                    choices=s_data.get("choices", []),
                ))
            chapters.append(CrownChapter(
                chapter_id=ch_data.get("chapter_id", ""),
                display_name=ch_data.get("display_name", ""),
                scenes=scenes,
            ))

        # Fallback: scenes_by_day format (simpler)
        if not chapters:
            scenes_by_day = campaign_data.get("scenes_by_day", {})
            if scenes_by_day:
                all_scenes: List[CrownScene] = []
                for day_str in sorted(scenes_by_day.keys(), key=lambda x: int(x)):
                    s_data = scenes_by_day[day_str]
                    all_scenes.append(CrownScene(
                        scene_id=s_data.get("scene_id", f"day_{day_str}"),
                        description=s_data.get("description", ""),
                        location=s_data.get("location", ""),
                        choices=s_data.get("choices", []),
                    ))
                chapters.append(CrownChapter(
                    chapter_id="main",
                    display_name="Campaign",
                    scenes=all_scenes,
                ))

        return cls(chapters=chapters)

    def get_current_scene(self, day: int = 1) -> Optional[CrownScene]:
        """Get the next unresolved scene, if any.

        Walks through chapters in order, returning the first unresolved
        scene from the current chapter. Returns None if no scenes remain
        (backward compatible — campaigns without scenes skip this phase).

        Args:
            day: Current campaign day (passed to chapter for future keying).

        Returns:
            Next unresolved CrownScene, or None.
        """
        if not self.chapters:
            return None

        while self._current_chapter_idx < len(self.chapters):
            chapter = self.chapters[self._current_chapter_idx]
            scene = chapter.get_scene_for_day(day)
            if scene:
                return scene
            # Chapter complete — try next
            if chapter.is_complete():
                self._current_chapter_idx += 1
            else:
                break
        return None

    def advance(self) -> None:
        """Advance the chapter pointer after the current chapter completes.

        Call this after resolving a scene. If the current chapter is now
        fully resolved, bumps the chapter index.
        """
        if self._current_chapter_idx < len(self.chapters):
            chapter = self.chapters[self._current_chapter_idx]
            if chapter.is_complete():
                self._current_chapter_idx += 1

    def is_complete(self) -> bool:
        """Return True if all chapters and scenes are resolved."""
        return all(ch.is_complete() for ch in self.chapters)

    def get_progress(self) -> str:
        """Return a human-readable scene progress string.

        Returns:
            String like "Scene 2/5" or "No scenes" if no content loaded.
        """
        total = sum(len(ch.scenes) for ch in self.chapters)
        done = sum(1 for ch in self.chapters for s in ch.scenes if s.resolved)
        if total == 0:
            return "No scenes"
        return f"Scene {done}/{total}"

    def to_dict(self) -> dict:
        """Serialize runner state for save/load."""
        return {
            "chapters": [ch.to_dict() for ch in self.chapters],
            "current_chapter_idx": self._current_chapter_idx,
            "scene_history": self._scene_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrownSceneRunner":
        """Restore runner from saved dict."""
        runner = cls(
            chapters=[CrownChapter.from_dict(ch) for ch in data.get("chapters", [])],
        )
        runner._current_chapter_idx = data.get("current_chapter_idx", 0)
        runner._scene_history = data.get("scene_history", [])
        return runner

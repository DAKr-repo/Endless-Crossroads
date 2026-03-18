"""
codex/core/engines — Shared Base Engine Classes
================================================
Provides SpatialEngineBase and NarrativeEngineBase for scaffolded game
systems.  Both classes extract the common implementation patterns from
the hand-written DnD5e and SaV engines so that new systems only need to
override the system-specific hooks.
"""

from .spatial_base import SpatialEngineBase
from .narrative_base import NarrativeEngineBase

__all__ = ["SpatialEngineBase", "NarrativeEngineBase"]

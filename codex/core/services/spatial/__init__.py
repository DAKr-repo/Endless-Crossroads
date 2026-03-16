"""Re-export stub providing the ``codex.core.services.spatial`` import path.

The actual implementations live in :mod:`codex.spatial.map_engine` and
:mod:`codex.spatial.map_renderer`.  This module exists so that both import
paths resolve to the same objects.
"""

from codex.spatial.map_engine import (  # noqa: F401
    CodexMapEngine,
    DungeonGraph,
    RoomNode,
    RoomType,
    GenerationMode,
    ContentInjector,
    PopulatedRoom,
    BurnwillowAdapter,
)

from codex.spatial.map_renderer import (  # noqa: F401
    MapTheme,
    ThemeConfig,
    ThemeRegistry,
    THEME_REGISTRY,
    THEMES,
)

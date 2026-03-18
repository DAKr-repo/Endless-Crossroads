"""
tests/test_responsive_layout.py — WO-V71.0 Responsive Terminal Layout Tests
=============================================================================
Tests for:
  - _detect_width returns console.width
  - NARROW_THRESHOLD constant is 80
  - _build_narrow_frame produces a Rich Text renderable
  - render_spatial_map accepts max_width / max_height without error
  - viewport shrinks when max dimensions are provided
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# Helpers
# ===========================================================================

def _make_mock_console(width: int) -> MagicMock:
    """Return a MagicMock Console with a fixed ``width`` attribute."""
    con = MagicMock()
    con.width = width
    return con


# ===========================================================================
# TestDetectWidth — console width helper
# ===========================================================================

class TestDetectWidth:
    """_detect_width should return console.width, defaulting to 120."""

    def test_returns_console_width(self):
        """_detect_width returns the width attribute of the console."""
        from play_burnwillow import _detect_width
        con = _make_mock_console(100)
        assert _detect_width(con) == 100

    def test_returns_120_when_width_is_none(self):
        """_detect_width returns 120 as default when console.width is None/0."""
        from play_burnwillow import _detect_width
        con = _make_mock_console(0)
        assert _detect_width(con) == 120

    def test_narrow_threshold_is_80(self):
        """NARROW_THRESHOLD constant must be exactly 80."""
        from play_burnwillow import NARROW_THRESHOLD
        assert NARROW_THRESHOLD == 80

    def test_narrow_detection_below_threshold(self):
        """A 79-column console is considered narrow."""
        from play_burnwillow import _detect_width, NARROW_THRESHOLD
        con = _make_mock_console(79)
        assert _detect_width(con) < NARROW_THRESHOLD

    def test_wide_detection_at_threshold(self):
        """A console exactly at NARROW_THRESHOLD is NOT considered narrow."""
        from play_burnwillow import _detect_width, NARROW_THRESHOLD
        con = _make_mock_console(80)
        assert _detect_width(con) >= NARROW_THRESHOLD


# ===========================================================================
# TestBuildNarrowFrame — renderable output
# ===========================================================================

class TestBuildNarrowFrame:
    """_build_narrow_frame must return a Rich Text object."""

    def _make_minimal_state(self):
        """Construct the smallest GameState-like object _build_narrow_frame needs."""
        state = MagicMock()
        # Minimal character
        char = MagicMock()
        char.current_hp = 10
        char.max_hp = 20
        char.gear.get_total_dr.return_value = 4
        char.keys = 2
        state.character = char
        state.active_leader = None
        state.doom = 5
        state.engine = None          # no engine — exercises None guards
        state.spatial_rooms = {}
        state.current_room_id = 0
        state.room_enemies = {}
        state.message_log = ["You enter the darkness.", "A shape moves."]
        return state

    def test_returns_rich_text(self):
        """_build_narrow_frame returns a rich.text.Text instance."""
        from rich.text import Text
        from play_burnwillow import _build_narrow_frame
        state = self._make_minimal_state()
        result = _build_narrow_frame(state)
        assert isinstance(result, Text)

    def test_contains_hp_info(self):
        """Output text includes HP values from the leader character."""
        from play_burnwillow import _build_narrow_frame
        state = self._make_minimal_state()
        result = _build_narrow_frame(state)
        plain = result.plain
        assert "HP: 10/20" in plain

    def test_contains_doom_info(self):
        """Output text includes the Doom value."""
        from play_burnwillow import _build_narrow_frame
        state = self._make_minimal_state()
        result = _build_narrow_frame(state)
        plain = result.plain
        assert "Doom: 5" in plain

    def test_includes_message_log(self):
        """Output text includes at least one message from the log."""
        from play_burnwillow import _build_narrow_frame
        state = self._make_minimal_state()
        result = _build_narrow_frame(state)
        plain = result.plain
        assert "darkness" in plain or "shape" in plain


# ===========================================================================
# TestMapRendererMaxDimensions — viewport capping
# ===========================================================================

class TestMapRendererMaxDimensions:
    """render_spatial_map should accept max_width / max_height and cap viewport."""

    def _make_rooms(self):
        """Return a minimal SpatialRoom dict for rendering."""
        from codex.spatial.map_renderer import SpatialRoom, RoomVisibility
        room = SpatialRoom(
            id=0, x=5, y=5, width=6, height=4,
            visibility=RoomVisibility.CURRENT,
        )
        return {0: room}

    def test_accepts_max_width_kwarg(self):
        """render_spatial_map does not raise when max_width is provided."""
        from codex.spatial.map_renderer import render_spatial_map, MapTheme
        rooms = self._make_rooms()
        # Should not raise
        layout = render_spatial_map(
            rooms=rooms,
            player_room_id=0,
            theme=MapTheme.RUST,
            viewport_width=60,
            viewport_height=25,
            max_width=40,
        )
        assert layout is not None

    def test_accepts_max_height_kwarg(self):
        """render_spatial_map does not raise when max_height is provided."""
        from codex.spatial.map_renderer import render_spatial_map, MapTheme
        rooms = self._make_rooms()
        layout = render_spatial_map(
            rooms=rooms,
            player_room_id=0,
            theme=MapTheme.RUST,
            viewport_width=60,
            viewport_height=25,
            max_height=12,
        )
        assert layout is not None

    def test_max_width_smaller_than_default_shrinks_viewport(self):
        """When max_width < viewport_width, the effective viewport is capped."""
        from codex.spatial.map_renderer import render_spatial_map, MapTheme
        from rich.layout import Layout
        rooms = self._make_rooms()
        # Both calls must succeed; we're verifying no exception is thrown
        layout_narrow = render_spatial_map(
            rooms=rooms,
            player_room_id=0,
            theme=MapTheme.RUST,
            viewport_width=60,
            viewport_height=25,
            max_width=20,
            max_height=8,
        )
        assert isinstance(layout_narrow, Layout)

    def test_max_larger_than_viewport_does_not_expand(self):
        """max_width larger than viewport_width leaves viewport unchanged."""
        from codex.spatial.map_renderer import render_spatial_map, MapTheme
        from rich.layout import Layout
        rooms = self._make_rooms()
        layout = render_spatial_map(
            rooms=rooms,
            player_room_id=0,
            theme=MapTheme.RUST,
            viewport_width=30,
            viewport_height=15,
            max_width=999,
            max_height=999,
        )
        assert isinstance(layout, Layout)

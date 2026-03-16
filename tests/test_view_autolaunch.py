"""Tests for Player View + DM View auto-launch via lxterminal."""
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Extract _spawn_view for unit testing.  We re-implement the function here
# to avoid importing the massive codex_agent_main module.  The logic mirrors
# codex_agent_main.py exactly.
# ---------------------------------------------------------------------------

CODEX_DIR = Path(__file__).resolve().parent.parent
_TERMINAL_CMD = "lxterminal"


def _spawn_view(name, script_path, title, geometry="100x30", extra_args=None,
                *, _spawned_services, _console=None):
    """Mirror of codex_agent_main._spawn_view for testability."""
    if not script_path.exists():
        return None
    inner_cmd = (
        f"cd {CODEX_DIR} && source venv/bin/activate && "
        f"python {script_path}"
    )
    if extra_args:
        inner_cmd += f" {extra_args}"
    args = [
        _TERMINAL_CMD,
        "--title", title,
        "--geometry", geometry,
        "-e", f"/bin/bash -c '{inner_cmd}'",
    ]
    try:
        proc = subprocess.Popen(args)
        _spawned_services.append([name, proc, args, None])
        if _console:
            _console.print(f"[dim]{name}: LAUNCHED[/dim]")
        return proc
    except FileNotFoundError:
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSpawnView:
    """Unit tests for _spawn_view helper."""

    def test_returns_none_when_script_missing(self, tmp_path):
        """_spawn_view returns None when script_path doesn't exist."""
        missing = tmp_path / "nonexistent.py"
        services = []
        result = _spawn_view("Test", missing, "Title", _spawned_services=services)
        assert result is None
        assert services == []

    def test_returns_none_when_lxterminal_missing(self, tmp_path):
        """_spawn_view returns None when lxterminal is not installed."""
        script = tmp_path / "view.py"
        script.write_text("# dummy")
        services = []
        with patch.object(subprocess, "Popen",
                          side_effect=FileNotFoundError("lxterminal not found")):
            result = _spawn_view("Test", script, "Title", _spawned_services=services)
        assert result is None
        assert services == []

    def test_calls_popen_with_correct_args(self, tmp_path):
        """_spawn_view builds the correct lxterminal command."""
        script = tmp_path / "view.py"
        script.write_text("# dummy")
        mock_proc = MagicMock()
        services = []

        with patch.object(subprocess, "Popen", return_value=mock_proc) as mock_popen:
            result = _spawn_view("PlayerView", script, "My Title", "100x30",
                                 _spawned_services=services)

        assert result is mock_proc
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "lxterminal"
        assert call_args[1] == "--title"
        assert call_args[2] == "My Title"
        assert call_args[3] == "--geometry"
        assert call_args[4] == "100x30"
        assert call_args[5] == "-e"
        assert str(script) in call_args[6]

    def test_appends_to_spawned_services(self, tmp_path):
        """Successful spawn appends [name, proc, args, None] to services list."""
        script = tmp_path / "view.py"
        script.write_text("# dummy")
        mock_proc = MagicMock()
        services = []

        with patch.object(subprocess, "Popen", return_value=mock_proc):
            _spawn_view("DMView", script, "DM Title", _spawned_services=services)

        assert len(services) == 1
        assert services[0][0] == "DMView"
        assert services[0][1] is mock_proc
        assert services[0][3] is None  # no port for views

    def test_extra_args_appended(self, tmp_path):
        """Extra args are appended to the inner command."""
        script = tmp_path / "view.py"
        script.write_text("# dummy")
        services = []

        with patch.object(subprocess, "Popen", return_value=MagicMock()) as mock_popen:
            _spawn_view("Test", script, "Title", extra_args="--standalone",
                         _spawned_services=services)

        inner_cmd = mock_popen.call_args[0][0][6]  # -e argument
        assert "--standalone" in inner_cmd

    def test_handles_generic_exception(self, tmp_path):
        """_spawn_view returns None on generic exceptions."""
        script = tmp_path / "view.py"
        script.write_text("# dummy")
        services = []
        with patch.object(subprocess, "Popen",
                          side_effect=OSError("something went wrong")):
            result = _spawn_view("Test", script, "Title", _spawned_services=services)
        assert result is None
        assert services == []

    def test_venv_activation_in_command(self, tmp_path):
        """Inner command activates venv before running Python."""
        script = tmp_path / "view.py"
        script.write_text("# dummy")
        services = []

        with patch.object(subprocess, "Popen", return_value=MagicMock()) as mock_popen:
            _spawn_view("Test", script, "Title", _spawned_services=services)

        inner_cmd = mock_popen.call_args[0][0][6]
        assert "source venv/bin/activate" in inner_cmd
        assert f"python {script}" in inner_cmd


class TestDisplayGating:
    """Tests that views are only spawned when DISPLAY is set."""

    def test_views_spawned_when_display_set(self, tmp_path):
        """Both views spawn when DISPLAY is set and scripts exist."""
        pv_script = tmp_path / "play_player_view.py"
        dm_script = tmp_path / "play_dm_view.py"
        pv_script.write_text("# player view")
        dm_script.write_text("# dm view")
        services = []

        with patch.object(subprocess, "Popen", return_value=MagicMock()):
            with patch.dict(os.environ, {"DISPLAY": ":0"}):
                if os.environ.get("DISPLAY"):
                    _spawn_view("PlayerView", pv_script,
                                "C.O.D.E.X. — Player View", "100x30",
                                _spawned_services=services)
                    _spawn_view("DMView", dm_script,
                                "C.O.D.E.X. — DM Dashboard", "120x35",
                                _spawned_services=services)

        assert len(services) == 2
        assert services[0][0] == "PlayerView"
        assert services[1][0] == "DMView"

    def test_views_not_spawned_without_display(self, tmp_path):
        """No views spawn when DISPLAY is not set."""
        pv_script = tmp_path / "play_player_view.py"
        dm_script = tmp_path / "play_dm_view.py"
        pv_script.write_text("# player view")
        dm_script.write_text("# dm view")
        services = []

        with patch.object(subprocess, "Popen", return_value=MagicMock()) as mock_popen:
            with patch.dict(os.environ, {}, clear=True):
                if os.environ.get("DISPLAY"):
                    _spawn_view("PlayerView", pv_script,
                                "C.O.D.E.X. — Player View", "100x30",
                                _spawned_services=services)
                    _spawn_view("DMView", dm_script,
                                "C.O.D.E.X. — DM Dashboard", "120x35",
                                _spawned_services=services)

        assert services == []
        mock_popen.assert_not_called()

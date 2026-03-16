"""
WO-V9.4 QA Test Suite
Verifies: Opus error filter, command routing, GameCommandView defaults,
          ServiceHealthMonitor voice watchdog, _UtteranceSink.write error handling.
"""

import logging
import sys
import os
import threading
import importlib
import importlib.util
import ast
import textwrap

# ---------------------------------------------------------------------------
# Path setup — must come before any project imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# The discord_bot module loads discord at import time; we need the venv on path.
VENV_SITE = os.path.join(PROJECT_ROOT, "venv", "lib", "python3.11", "site-packages")
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# ---------------------------------------------------------------------------
# Helpers (kept at module level for standalone use)
# ---------------------------------------------------------------------------
PASS = "[PASS]"
FAIL = "[FAIL]"


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _make_opus_record(msg: str) -> logging.LogRecord:
    """Build a LogRecord for opus filter tests."""
    return logging.LogRecord(
        name="discord.player",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )


# ===========================================================================
# 1. Opus Error Filter
# ===========================================================================

def test_opus_error_filter_import():
    """Verify _OpusErrorFilter and related symbols can be imported."""
    from codex.bots.discord_bot import (  # noqa: F401
        _opus_error_count,
        _opus_error_lock,
        _OpusErrorFilter,
    )


def test_opus_error_filter_first_hit_passes():
    """First opus error must be let through (count 1, 1 % 50 == 1 → True)."""
    import codex.bots.discord_bot as _dbot
    from codex.bots.discord_bot import _OpusErrorFilter

    # Reset counter so prior imports don't pollute this test.
    with _dbot._opus_error_lock:
        _dbot._opus_error_count = 0

    filt = _OpusErrorFilter()
    rec = _make_opus_record("Error occurred while decoding opus frame.")
    result = filt.filter(rec)

    assert result is True, f"Expected True for first hit, got {result!r}"

    with _dbot._opus_error_lock:
        count = _dbot._opus_error_count
    assert count == 1, f"Expected _opus_error_count == 1 after first hit, got {count}"


def test_opus_error_filter_suppresses_hits_2_to_49():
    """Hits 2-49 must all be suppressed (returns False)."""
    import codex.bots.discord_bot as _dbot
    from codex.bots.discord_bot import _OpusErrorFilter

    with _dbot._opus_error_lock:
        _dbot._opus_error_count = 1  # simulate one hit already recorded

    filt = _OpusErrorFilter()
    for i in range(2, 50):
        r = filt.filter(_make_opus_record("Error occurred while decoding opus frame."))
        assert r is False, f"Expected False at hit {i}, got {r!r}"

    with _dbot._opus_error_lock:
        count = _dbot._opus_error_count
    assert count == 49, f"Expected _opus_error_count == 49 after 49 hits, got {count}"


def test_opus_error_filter_hit_50_suppressed():
    """Hit 50 must be suppressed (50 % 50 == 0 → False)."""
    import codex.bots.discord_bot as _dbot
    from codex.bots.discord_bot import _OpusErrorFilter

    with _dbot._opus_error_lock:
        _dbot._opus_error_count = 49  # simulate 49 hits

    filt = _OpusErrorFilter()
    r50 = filt.filter(_make_opus_record("Error occurred while decoding opus frame."))

    assert r50 is False, f"Expected False at hit 50 (50 % 50 == 0), got {r50!r}"

    with _dbot._opus_error_lock:
        count = _dbot._opus_error_count
    assert count == 50, f"Expected _opus_error_count == 50, got {count}"


def test_opus_error_filter_hit_51_passes():
    """Hit 51 must be let through (51 % 50 == 1 → True)."""
    import codex.bots.discord_bot as _dbot
    from codex.bots.discord_bot import _OpusErrorFilter

    with _dbot._opus_error_lock:
        _dbot._opus_error_count = 50  # simulate 50 hits

    filt = _OpusErrorFilter()
    r51 = filt.filter(_make_opus_record("Error occurred while decoding opus frame."))

    assert r51 is True, f"Expected True at hit 51 (51 % 50 == 1), got {r51!r}"

    with _dbot._opus_error_lock:
        count = _dbot._opus_error_count
    assert count == 51, f"Expected _opus_error_count == 51, got {count}"


def test_opus_error_filter_passes_non_opus_messages():
    """Non-opus messages must always be let through without touching the counter."""
    import codex.bots.discord_bot as _dbot
    from codex.bots.discord_bot import _OpusErrorFilter

    with _dbot._opus_error_lock:
        _dbot._opus_error_count = 51  # arbitrary non-zero baseline

    filt = _OpusErrorFilter()
    rec_other = _make_opus_record("Heartbeat acknowledged.")
    result = filt.filter(rec_other)

    assert result is True, f"Expected True for non-opus message, got {result!r}"

    with _dbot._opus_error_lock:
        count = _dbot._opus_error_count
    assert count == 51, (
        f"Expected _opus_error_count unchanged at 51 for non-opus message, got {count}"
    )


# ===========================================================================
# 2. Command Routing — on_command_error exists on CodexDiscordBot
# ===========================================================================

def test_command_routing_imports():
    """CodexDiscordBot, Phase, and GameCommandView must be importable."""
    from codex.bots.discord_bot import CodexDiscordBot, Phase, GameCommandView  # noqa: F401


def test_on_command_error_method_exists():
    """on_command_error must be a callable method on CodexDiscordBot."""
    from codex.bots.discord_bot import CodexDiscordBot
    has_method = callable(getattr(CodexDiscordBot, "on_command_error", None))
    assert has_method, "on_command_error method not found on CodexDiscordBot"


def test_game_command_view_has_search_in_exploration():
    """GameCommandView._FALLBACK_COMMANDS['exploration'] must contain 'search'."""
    from codex.bots.discord_bot import GameCommandView
    exploration_cmds = GameCommandView._FALLBACK_COMMANDS.get("exploration", {})
    assert "search" in exploration_cmds, (
        f"'search' not found in _FALLBACK_COMMANDS['exploration']; found: {list(exploration_cmds.keys())}"
    )


# ===========================================================================
# 3. GameCommandView Default Commands
# ===========================================================================

def test_game_command_view_exploration_commands():
    """Fallback exploration commands must include search, look, map, inventory, stats, help."""
    from codex.bots.discord_bot import GameCommandView
    exploration = GameCommandView._FALLBACK_COMMANDS.get("exploration", {})
    cmd_names = set(exploration.keys())

    expected = {"look", "search", "map", "inventory", "stats", "help"}
    missing = expected - cmd_names
    assert not missing, (
        f"Missing fallback exploration commands: {missing}; found: {cmd_names}"
    )


# ===========================================================================
# 4. ServiceHealthMonitor Voice Watchdog
# ===========================================================================

def _parse_agent_main_class(class_name: str) -> ast.ClassDef:
    """Parse codex_agent_main.py via AST and return the named ClassDef node."""
    src_path = os.path.join(PROJECT_ROOT, "codex_agent_main.py")
    with open(src_path, "r") as fh:
        full_src = fh.read()
    tree = ast.parse(full_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node, full_src
    return None, full_src


def test_service_health_monitor_class_found():
    """ServiceHealthMonitor class must exist in codex_agent_main.py."""
    class_node, _ = _parse_agent_main_class("ServiceHealthMonitor")
    assert class_node is not None, (
        "ServiceHealthMonitor class not found in codex_agent_main.py"
    )


def test_service_health_monitor_attributes():
    """ServiceHealthMonitor must define OPUS_ERROR_THRESHOLD=10, _voice_watchdog, and discord_bot param."""
    class_node, _ = _parse_agent_main_class("ServiceHealthMonitor")
    assert class_node is not None, "ServiceHealthMonitor class not found — cannot check attributes"

    threshold_value = None
    has_voice_watchdog = False
    has_discord_bot_param = False

    for node in ast.walk(class_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "OPUS_ERROR_THRESHOLD":
                    if isinstance(node.value, ast.Constant):
                        threshold_value = node.value.value
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_voice_watchdog":
            has_voice_watchdog = True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__init__":
            param_names = [arg.arg for arg in node.args.args]
            if "discord_bot" in param_names:
                has_discord_bot_param = True

    assert threshold_value == 10, (
        f"Expected OPUS_ERROR_THRESHOLD == 10, found: {threshold_value}"
    )
    assert has_voice_watchdog, "_voice_watchdog async method not found in ServiceHealthMonitor"
    assert has_discord_bot_param, "__init__ does not accept a discord_bot parameter"


def test_service_health_monitor_instantiation():
    """ServiceHealthMonitor must instantiate with discord_bot=None without crashing."""
    class_node, full_src = _parse_agent_main_class("ServiceHealthMonitor")
    assert class_node is not None, "ServiceHealthMonitor class not found — cannot instantiate"

    minimal_ns: dict = {}
    exec(
        textwrap.dedent("""
        import asyncio, subprocess, threading, time

        class _FakeConsole:
            def print(self, *a, **kw): pass

        console = _FakeConsole()
        """),
        minimal_ns,
    )

    lines = full_src.splitlines(keepends=True)
    class_src = "".join(lines[class_node.lineno - 1 : class_node.end_lineno])
    exec(class_src, minimal_ns)
    SHM = minimal_ns["ServiceHealthMonitor"]

    instance = SHM(services=[], check_port_fn=lambda port: True, discord_bot=None)

    assert instance.OPUS_ERROR_THRESHOLD == 10, (
        f"Instance OPUS_ERROR_THRESHOLD expected 10, got {instance.OPUS_ERROR_THRESHOLD}"
    )
    assert callable(getattr(instance, "_voice_watchdog", None)), (
        "Instance does not have a callable _voice_watchdog"
    )


# ===========================================================================
# 5. _UtteranceSink.write references _opus_error_count
# ===========================================================================

def _parse_discord_bot_sink() -> tuple:
    """Parse discord_bot.py and return (_UtteranceSink node, full source)."""
    src_path = os.path.join(PROJECT_ROOT, "codex", "bots", "discord_bot.py")
    with open(src_path, "r") as fh:
        bot_src = fh.read()
    tree = ast.parse(bot_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_UtteranceSink":
            return node, bot_src
    return None, bot_src


def test_utterance_sink_class_found():
    """_UtteranceSink class must exist in discord_bot.py."""
    sink_class, _ = _parse_discord_bot_sink()
    assert sink_class is not None, "_UtteranceSink class not found in discord_bot.py"


def test_utterance_sink_write_method_found():
    """_UtteranceSink must have a write method."""
    sink_class, _ = _parse_discord_bot_sink()
    assert sink_class is not None, "_UtteranceSink class not found — cannot check write method"

    write_method = None
    for node in ast.walk(sink_class):
        if isinstance(node, ast.FunctionDef) and node.name == "write":
            write_method = node
            break
    assert write_method is not None, "write method not found in _UtteranceSink"


def test_utterance_sink_write_references_counter():
    """_UtteranceSink.write body must reference _opus_error_count."""
    sink_class, bot_src = _parse_discord_bot_sink()
    assert sink_class is not None, "_UtteranceSink class not found"

    write_method = None
    for node in ast.walk(sink_class):
        if isinstance(node, ast.FunctionDef) and node.name == "write":
            write_method = node
            break
    assert write_method is not None, "write method not found in _UtteranceSink"

    lines = bot_src.splitlines(keepends=True)
    write_src = "".join(lines[write_method.lineno - 1 : write_method.end_lineno])
    assert "_opus_error_count" in write_src, (
        f"write method body does not reference _opus_error_count; snippet: {write_src[:120].strip()!r}"
    )


def test_utterance_sink_write_has_try_except():
    """_UtteranceSink.write must have a try/except block for error handling."""
    sink_class, _ = _parse_discord_bot_sink()
    assert sink_class is not None, "_UtteranceSink class not found"

    write_method = None
    for node in ast.walk(sink_class):
        if isinstance(node, ast.FunctionDef) and node.name == "write":
            write_method = node
            break
    assert write_method is not None, "write method not found in _UtteranceSink"

    has_try_except = any(isinstance(n, ast.ExceptHandler) for n in ast.walk(write_method))
    assert has_try_except, "write method has no try/except block for error handling"


def test_utterance_sink_write_resets_counter_on_success():
    """_UtteranceSink.write must reset _opus_error_count to 0 on success."""
    sink_class, _ = _parse_discord_bot_sink()
    assert sink_class is not None, "_UtteranceSink class not found"

    write_method = None
    for node in ast.walk(sink_class):
        if isinstance(node, ast.FunctionDef) and node.name == "write":
            write_method = node
            break
    assert write_method is not None, "write method not found in _UtteranceSink"

    reset_to_zero = False
    for node in ast.walk(write_method):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "_opus_error_count"
                    and isinstance(node.value, ast.Constant)
                    and node.value.value == 0
                ):
                    reset_to_zero = True
    assert reset_to_zero, "write method does not reset _opus_error_count to 0 on success"


# ===========================================================================
# Standalone execution — preserves original pass/fail output and sys.exit()
# ===========================================================================
if __name__ == "__main__":
    results = []

    def check(label: str, condition: bool, detail: str = ""):
        tag = PASS if condition else FAIL
        msg = f"{tag} {label}"
        if detail:
            msg += f"  ({detail})"
        print(msg)
        results.append((label, condition))
        return condition

    def _run(fn):
        try:
            fn()
            check(fn.__name__, True)
        except AssertionError as exc:
            check(fn.__name__, False, str(exc))
        except Exception as exc:
            check(fn.__name__, False, f"{type(exc).__name__}: {exc}")

    _tests = [
        test_opus_error_filter_import,
        test_opus_error_filter_first_hit_passes,
        test_opus_error_filter_suppresses_hits_2_to_49,
        test_opus_error_filter_hit_50_suppressed,
        test_opus_error_filter_hit_51_passes,
        test_opus_error_filter_passes_non_opus_messages,
        test_command_routing_imports,
        test_on_command_error_method_exists,
        test_game_command_view_has_search_in_exploration,
        test_game_command_view_exploration_commands,
        test_service_health_monitor_class_found,
        test_service_health_monitor_attributes,
        test_service_health_monitor_instantiation,
        test_utterance_sink_class_found,
        test_utterance_sink_write_method_found,
        test_utterance_sink_write_references_counter,
        test_utterance_sink_write_has_try_except,
        test_utterance_sink_write_resets_counter_on_success,
    ]

    section("WO-V9.4 QA — Standalone Run")
    for t in _tests:
        _run(t)

    section("SUMMARY")
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    for label, ok in results:
        tag = PASS if ok else FAIL
        print(f"  {tag} {label}")

    print(f"\n{'-'*60}")
    print(f"  Result: {passed}/{total} passed, {failed} failed")
    print(f"{'-'*60}")

    sys.exit(0 if failed == 0 else 1)

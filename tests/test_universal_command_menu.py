#!/usr/bin/env python3
"""
tests/test_universal_command_menu.py
=====================================
QA: Universal Command Menu wiring verification.

Tests:
  1. UniversalGameBridge.COMMAND_CATEGORIES structure
  2. BurnwillowBridge COMMAND_CATEGORIES + ALIAS_MAP
  3. UniversalGameBridge dispatch table contains "loot"
  4. GameCommandView._resolve_categories + _FALLBACK_COMMANDS
  5. GameCommandView wiring with a mock session (bridge path)

Run (standalone):
  PYTHONPATH=. python tests/test_universal_command_menu.py

Run (pytest):
  PYTHONPATH=. pytest tests/test_universal_command_menu.py
"""

import sys

# ---------------------------------------------------------------------------
# Discord stubs must be installed at module level before any bot imports
# ---------------------------------------------------------------------------
from codex.stubs import install_discord_stubs
install_discord_stubs()


# ---------------------------------------------------------------------------
# 1. UniversalGameBridge.COMMAND_CATEGORIES
# ---------------------------------------------------------------------------

def test_universal_bridge_command_categories():
    """UniversalGameBridge.COMMAND_CATEGORIES structure."""
    from codex.games.bridge import UniversalGameBridge

    cats = UniversalGameBridge.COMMAND_CATEGORIES

    assert isinstance(cats, dict), "COMMAND_CATEGORIES must be a dict"
    assert "movement" in cats, "COMMAND_CATEGORIES must have 'movement' key"
    assert "combat" in cats, "COMMAND_CATEGORIES must have 'combat' key"
    assert "exploration" in cats, "COMMAND_CATEGORIES must have 'exploration' key"

    mov = cats.get("movement", {})
    for cmd in ("north", "south", "east", "west"):
        assert cmd in mov, f"movement category must contain '{cmd}'"

    exp = cats.get("exploration", {})
    for cmd in ("look", "search", "map", "inventory", "stats", "travel", "help"):
        assert cmd in exp, f"exploration category must contain '{cmd}'"

    cbt = cats.get("combat", {})
    for cmd in ("attack", "rest"):
        assert cmd in cbt, f"combat category must contain '{cmd}'"


# ---------------------------------------------------------------------------
# 2. BurnwillowBridge COMMAND_CATEGORIES + ALIAS_MAP
# ---------------------------------------------------------------------------

def test_burnwillow_bridge_command_categories():
    """BurnwillowBridge.COMMAND_CATEGORIES and ALIAS_MAP structure."""
    from codex.games.burnwillow.bridge import BurnwillowBridge, ALIAS_MAP

    COMMAND_CATEGORIES = BurnwillowBridge.COMMAND_CATEGORIES

    assert isinstance(COMMAND_CATEGORIES, dict), "COMMAND_CATEGORIES must be a dict"
    assert "navigation" in COMMAND_CATEGORIES, "COMMAND_CATEGORIES must have 'navigation' key"
    assert "combat" in COMMAND_CATEGORIES, "COMMAND_CATEGORIES must have 'combat' key"
    assert "exploration" in COMMAND_CATEGORIES, "COMMAND_CATEGORIES must have 'exploration' key"

    nav = COMMAND_CATEGORIES.get("navigation", {})
    assert "move" in nav, "navigation must have 'move'"
    assert "look" in nav, "navigation must have 'look'"
    assert "map" in nav, "navigation must have 'map'"
    assert "north" not in nav, "'north' must not appear in navigation (use 'move <id>')"
    assert "south" not in nav, "'south' must not appear in navigation"
    assert "east" not in nav, "'east' must not appear in navigation"
    assert "west" not in nav, "'west' must not appear in navigation"

    expl = COMMAND_CATEGORIES.get("exploration", {})
    for cmd in ("search", "loot", "drop", "inventory", "stats", "help"):
        assert cmd in expl, f"exploration must contain '{cmd}'"

    assert isinstance(ALIAS_MAP, dict), "ALIAS_MAP must be a dict"
    assert ALIAS_MAP.get("loot") == "loot", (
        f"ALIAS_MAP['loot'] must be 'loot' (standalone command), got {ALIAS_MAP.get('loot')!r}"
    )


# ---------------------------------------------------------------------------
# 3. UniversalGameBridge dispatch table contains "loot"
# ---------------------------------------------------------------------------

def test_universal_bridge_loot_dispatch():
    """UniversalGameBridge.step() dispatches 'loot' and 'search' without 'Unknown command'."""
    import inspect
    from codex.games.bridge import UniversalGameBridge

    src = inspect.getsource(UniversalGameBridge.step)
    assert '"loot"' in src or "'loot'" in src, (
        "'loot' key must exist in the dispatch dict inside step()"
    )

    class _MockEngine:
        system_id       = "mock"
        display_name    = "Mock"
        current_room_id = 0
        dungeon_graph   = None
        visited_rooms   = set()
        populated_rooms = {}
        character       = None

        def get_current_room(self): return None
        def get_cardinal_exits(self): return []
        def move_to_room(self, _): pass
        def roll_check(self, dc=10): return {"success": False, "total": 0, "modifier": 0}
        def create_character(self, name): pass
        def generate_dungeon(self, seed=None): pass
        def load_state(self, data): pass

    bridge = UniversalGameBridge.create_lightweight(_MockEngine())

    response = bridge.step("loot")
    assert "Unknown command" not in response, (
        f"step('loot') must not return 'Unknown command', got: {response!r}"
    )

    response_search = bridge.step("search")
    assert "Unknown command" not in response_search, (
        f"step('search') must not return 'Unknown command', got: {response_search!r}"
    )


# ---------------------------------------------------------------------------
# 4. GameCommandView._resolve_categories + _FALLBACK_COMMANDS
# ---------------------------------------------------------------------------

def test_game_command_view_attributes():
    """GameCommandView has _resolve_categories method and _FALLBACK_COMMANDS class attribute."""
    from codex.bots.discord_bot import GameCommandView

    assert callable(getattr(GameCommandView, "_resolve_categories", None)), (
        "GameCommandView must have a callable '_resolve_categories' method"
    )
    assert hasattr(GameCommandView, "_FALLBACK_COMMANDS"), (
        "GameCommandView must have '_FALLBACK_COMMANDS' class attribute"
    )

    fb = GameCommandView._FALLBACK_COMMANDS
    assert isinstance(fb, dict), "_FALLBACK_COMMANDS must be a dict"
    assert "movement" in fb, "_FALLBACK_COMMANDS must have 'movement' key"
    assert "combat" in fb, "_FALLBACK_COMMANDS must have 'combat' key"
    assert "exploration" in fb, "_FALLBACK_COMMANDS must have 'exploration' key"
    assert "help" in fb.get("exploration", {}), (
        "'help' must be in _FALLBACK_COMMANDS['exploration']"
    )


# ---------------------------------------------------------------------------
# 5. GameCommandView wiring with mock session (bridge path)
# ---------------------------------------------------------------------------

def test_game_command_view_mock_session():
    """GameCommandView correctly resolves categories from bridge and falls back without one."""
    from codex.bots.discord_bot import GameCommandView

    class _MockBridge:
        COMMAND_CATEGORIES = {
            "navigation": {
                "move": "Move to a connected room",
                "look": "Describe current room",
                "map":  "Show dungeon mini-map",
            },
            "combat": {
                "attack": "Fight the first enemy",
                "rest":   "Rest and heal",
            },
            "exploration": {
                "search":    "Search for loot",
                "inventory": "Show your gear",
                "stats":     "Show character stats",
                "help":      "List all commands",
            },
        }
        dead = False

    class _MockSession:
        bridge = _MockBridge()

    session = _MockSession()
    view = GameCommandView(session)

    assert len(view.children) > 0, "GameCommandView must build at least one Select item"
    assert len(view.children) == 3, (
        f"Expected 3 Select items (one per category), got {len(view.children)}"
    )

    resolved = view._resolve_categories()
    assert resolved is _MockBridge.COMMAND_CATEGORIES or resolved == _MockBridge.COMMAND_CATEGORIES, (
        f"_resolve_categories must return bridge COMMAND_CATEGORIES, got keys: {list(resolved.keys())}"
    )
    assert "navigation" in resolved, (
        "resolved categories must have 'navigation' (bridge key, not fallback 'movement')"
    )
    assert "movement" not in resolved, (
        "'movement' must not appear — should be using bridge categories, not falling back"
    )

    class _NoBridgeSession:
        bridge = None

    view_fallback = GameCommandView(_NoBridgeSession())
    resolved_fb = view_fallback._resolve_categories()
    assert resolved_fb == GameCommandView._FALLBACK_COMMANDS, (
        f"No-bridge session must fall back to _FALLBACK_COMMANDS, got keys: {list(resolved_fb.keys())}"
    )
    assert "movement" in resolved_fb, (
        "Fallback categories must have 'movement' key (not 'navigation')"
    )


# ---------------------------------------------------------------------------
# Standalone execution guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    _tests = [
        test_universal_bridge_command_categories,
        test_burnwillow_bridge_command_categories,
        test_universal_bridge_loot_dispatch,
        test_game_command_view_attributes,
        test_game_command_view_mock_session,
    ]

    passed = 0
    failed = 0
    for fn in _tests:
        label = fn.__name__
        print(f"\n=== {label} ===")
        try:
            fn()
            print(f"  [PASS] {label}")
            passed += 1
        except AssertionError as exc:
            print(f"  [FAIL] {label}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  [ERROR] {label}: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    total = passed + failed
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    if failed:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
        sys.exit(0)

"""
Tests for codex.core.services.trait_handler
============================================

All tests are self-contained: no external services, no file I/O, no LLMs.
"""

import pytest

from codex.core.services.trait_handler import (
    MissingEngineError,
    TraitHandler,
    TraitResolver,
    get_entity_override,
    get_entity_traits,
    load_entity_schema,
)


# ---------------------------------------------------------------------------
# Concrete resolver stubs
# ---------------------------------------------------------------------------


class EchoResolver(TraitResolver):
    """Returns a result that echoes trait_id and context back to the caller."""

    def resolve_trait(self, trait_id: str, context: dict) -> dict:
        return {"trait_id": trait_id, "context": context, "success": True}


class AlwaysFailResolver(TraitResolver):
    """Simulates a system whose trait always results in failure."""

    def resolve_trait(self, trait_id: str, context: dict) -> dict:
        return {"trait_id": trait_id, "success": False, "reason": "not implemented"}


class BroadcastResolver(TraitResolver):
    """Returns a result flagged for broadcast."""

    def resolve_trait(self, trait_id: str, context: dict) -> dict:
        return {"trait_id": trait_id, "success": True, "broadcast": True}


class CaptureBroadcast:
    """Minimal broadcast-manager stand-in that captures calls."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def broadcast(self, event_type: str, payload: dict) -> None:
        self.calls.append((event_type, payload))


# ---------------------------------------------------------------------------
# Test 1 — Register resolver and verify it is stored
# ---------------------------------------------------------------------------


def test_register_resolver_is_stored():
    handler = TraitHandler()
    resolver = EchoResolver()

    handler.register_resolver("burnwillow", resolver)

    assert "burnwillow" in handler._resolvers
    assert handler._resolvers["burnwillow"] is resolver


# ---------------------------------------------------------------------------
# Test 2 — Activate a known trait returns the expected result
# ---------------------------------------------------------------------------


def test_activate_known_trait_returns_result():
    handler = TraitHandler()
    handler.register_resolver("burnwillow", EchoResolver())

    result = handler.activate_trait("SET_TRAP", "burnwillow", {})

    assert result["success"] is True
    assert result["trait_id"] == "SET_TRAP"


# ---------------------------------------------------------------------------
# Test 3 — Activate with no resolver registered raises MissingEngineError
# ---------------------------------------------------------------------------


def test_activate_missing_resolver_raises():
    handler = TraitHandler()

    with pytest.raises(MissingEngineError) as exc_info:
        handler.activate_trait("SET_TRAP", "unknown_system", {})

    assert "unknown_system" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 4 — Context dict is passed through to the resolver unchanged
# ---------------------------------------------------------------------------


def test_context_passthrough_to_resolver():
    handler = TraitHandler()
    handler.register_resolver("dnd5e", EchoResolver())

    ctx = {"character": "Aldric", "room_id": 7, "advantage": True}
    result = handler.activate_trait("SNEAK_ATTACK", "dnd5e", ctx)

    assert result["context"] == ctx
    # Verify it is the exact same mapping, not a copy
    assert result["context"] is ctx


# ---------------------------------------------------------------------------
# Test 5 — has_resolver() returns True only after registration
# ---------------------------------------------------------------------------


def test_has_resolver_before_and_after_registration():
    handler = TraitHandler()

    assert handler.has_resolver("bitd") is False

    handler.register_resolver("bitd", EchoResolver())

    assert handler.has_resolver("bitd") is True


# ---------------------------------------------------------------------------
# Test 6 — Multiple resolvers for different systems dispatch independently
# ---------------------------------------------------------------------------


def test_multiple_resolvers_dispatch_correctly():
    handler = TraitHandler()
    handler.register_resolver("burnwillow", EchoResolver())
    handler.register_resolver("crown", AlwaysFailResolver())

    bw_result = handler.activate_trait("SET_TRAP", "burnwillow", {})
    cr_result = handler.activate_trait("INFLUENCE", "crown", {})

    assert bw_result["success"] is True
    assert cr_result["success"] is False
    assert cr_result["reason"] == "not implemented"
    # Each system is isolated — wrong system raises
    with pytest.raises(MissingEngineError):
        handler.activate_trait("SET_TRAP", "dnd5e", {})


# ---------------------------------------------------------------------------
# Bonus Test 7 — Broadcast fires when result carries the broadcast flag
# ---------------------------------------------------------------------------


def test_broadcast_fires_on_flagged_result():
    capture = CaptureBroadcast()
    handler = TraitHandler(broadcast_manager=capture)
    handler.register_resolver("burnwillow", BroadcastResolver())

    handler.activate_trait("AMBUSH", "burnwillow", {})

    assert len(capture.calls) == 1
    event_type, payload = capture.calls[0]
    assert event_type == "TRAIT_ACTIVATED"
    assert payload["trait_id"] == "AMBUSH"
    assert payload["system_id"] == "burnwillow"


# ---------------------------------------------------------------------------
# Bonus Test 8 — No broadcast when result lacks the broadcast flag
# ---------------------------------------------------------------------------


def test_no_broadcast_without_flag():
    capture = CaptureBroadcast()
    handler = TraitHandler(broadcast_manager=capture)
    handler.register_resolver("burnwillow", EchoResolver())

    handler.activate_trait("SET_TRAP", "burnwillow", {})

    assert len(capture.calls) == 0


# ---------------------------------------------------------------------------
# Bonus Test 9 — load_entity_schema returns empty dict for missing file
# ---------------------------------------------------------------------------


def test_load_entity_schema_missing_file(tmp_path):
    import codex.core.services.trait_handler as th_module

    # Reset the module-level cache so this test starts clean
    original_cache = th_module._entity_cache
    th_module._entity_cache = None
    try:
        result = load_entity_schema(path=tmp_path / "nonexistent.json")
        assert result == {}
    finally:
        th_module._entity_cache = original_cache


# ---------------------------------------------------------------------------
# Bonus Test 10 — get_entity_traits / get_entity_override via temp schema
# ---------------------------------------------------------------------------


def test_entity_helpers_with_temp_schema(tmp_path):
    import json
    import codex.core.services.trait_handler as th_module

    schema = {
        "entities": {
            "rot_beetle": {
                "special_traits": ["AMBUSH", "POISON"],
                "system_overrides": {
                    "burnwillow": {"hp": 6, "damage": 2}
                },
            }
        }
    }
    schema_file = tmp_path / "entity_schema.json"
    schema_file.write_text(json.dumps(schema))

    original_cache = th_module._entity_cache
    th_module._entity_cache = None
    try:
        traits = get_entity_traits.__wrapped__(schema_file) if hasattr(get_entity_traits, "__wrapped__") else None
        # Call helpers directly with the path-injected loader
        loaded = load_entity_schema(path=schema_file)
        assert "rot_beetle" in loaded
        assert loaded["rot_beetle"]["special_traits"] == ["AMBUSH", "POISON"]

        # Now test helpers against the primed cache
        traits = get_entity_traits("rot_beetle")
        assert "AMBUSH" in traits
        assert "POISON" in traits

        override = get_entity_override("rot_beetle", "burnwillow")
        assert override["hp"] == 6
        assert override["damage"] == 2

        # Unknown entity / system returns graceful empty
        assert get_entity_traits("ghost") == []
        assert get_entity_override("rot_beetle", "dnd5e") == {}
    finally:
        th_module._entity_cache = original_cache

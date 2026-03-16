"""
Test conftest — global fixtures for the Codex test suite.

Patches the RAGService thermal gate to always return True during testing.
Hardware thermal checks are a runtime concern, not a test concern.
Without this, long-running test suites on Pi 5 can warm the CPU enough
that the cortex thermal gate denies RAG requests mid-suite.

WO-V47.0: Added shared fixtures for engines, Ollama mocking, cortex, broadcast.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ─────────────────────────────────────────────────────────────────────
# Vault availability helpers — third-party content is gitignored
# ─────────────────────────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).resolve().parent.parent / "vault"

def _vault_has(*subdirs: str) -> bool:
    """Check if a vault subdirectory exists (e.g., 'FITD', 'stc', 'dnd5e')."""
    for sub in subdirs:
        if not (VAULT_ROOT / sub).exists():
            return False
    return True

requires_vault_fitd = pytest.mark.skipif(
    not _vault_has("FITD"), reason="vault/FITD/ not present (third-party, gitignored)")
requires_vault_stc = pytest.mark.skipif(
    not _vault_has("stc"), reason="vault/stc/ not present (third-party, gitignored)")
requires_vault_dnd5e = pytest.mark.skipif(
    not _vault_has("dnd5e"), reason="vault/dnd5e/ not present (third-party, gitignored)")


@pytest.fixture(autouse=True, scope="session")
def _stable_thermal_gate():
    """Ensure RAGService._check_thermal always returns True during tests."""
    with patch(
        "codex.core.services.rag_service.RAGService._check_thermal",
        return_value=True,
    ):
        yield


# ─────────────────────────────────────────────────────────────────────
# WO-V47.0: Shared test fixtures
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ollama():
    """Patch all Ollama HTTP calls to return canned responses.

    Patches requests.post globally so no real Ollama calls happen.
    The mock returns a streaming-compatible response with a simple canned reply.
    """
    canned = '{"response": "The dungeon stretches before you.", "done": true}'

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_lines = MagicMock(return_value=[canned.encode()])
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("requests.post", return_value=mock_response) as mock_post:
        yield mock_post


@pytest.fixture
def burnwillow_engine():
    """Fresh BurnwillowEngine with a 4-char party, equipped, dungeon generated."""
    from codex.games.burnwillow.engine import BurnwillowEngine
    engine = BurnwillowEngine()
    engine.create_party(["Kael", "Lyra", "Thorne", "Wren"])
    engine.generate_dungeon()
    return engine


@pytest.fixture
def mock_cortex():
    """Cortex with mocked thermal readings (defaults to 55°C, OPTIMAL)."""
    from codex.core.cortex import Cortex, CortexConfig

    config = CortexConfig()
    cortex = Cortex(config)

    with patch.object(cortex, "_read_cpu_temperature", return_value=55.0), \
         patch.object(cortex, "_read_ram_stats", return_value=(50.0, 6.0)):
        yield cortex


@pytest.fixture
def mock_broadcast():
    """GlobalBroadcastManager that captures events without side effects."""
    from codex.core.services.broadcast import GlobalBroadcastManager
    manager = GlobalBroadcastManager(system_theme="burnwillow")
    return manager

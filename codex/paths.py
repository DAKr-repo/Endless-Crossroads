"""
codex.paths - Central Path Registry
====================================
Single source of truth for all directory references in Project Codex.

Usage:
    from codex.paths import SAVES_DIR, STATE_DIR
    campaign_dir = SAVES_DIR / "my_campaign"

All paths are anchored to PROJECT_ROOT (the Codex/ directory containing
this package), so they resolve correctly regardless of the caller's
working directory.
"""

from pathlib import Path

# Codex/ project root (parent of this codex/ package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data directories
STATE_DIR     = PROJECT_ROOT / "state"
SAVES_DIR     = PROJECT_ROOT / "saves"
VAULT_DIR     = PROJECT_ROOT / "vault"
VAULT_MAPS_DIR = PROJECT_ROOT / "vault_maps"
CONFIG_DIR    = PROJECT_ROOT / "config"
WORLDS_DIR    = PROJECT_ROOT / "worlds"
MODELS_DIR    = PROJECT_ROOT / "models"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
LOGS_DIR      = PROJECT_ROOT / "gemini_sandbox" / "session_logs"
FAISS_INDEX_DIR = PROJECT_ROOT / "faiss_index"

# Specific file paths
SESSION_STATE_FILE = STATE_DIR / "session_state.json"
SESSION_STATS_FILE = STATE_DIR / "session_stats.json"
BRIDGE_FILE        = STATE_DIR / "live_session.json"
LORE_CACHE_FILE    = STATE_DIR / "lore_cache.json"
WORLD_HISTORY_FILE = STATE_DIR / "world_history.json"
NPC_MEMORY_FILE    = STATE_DIR / "npc_memory.json"

# Vault sub-paths
DND5E_SOURCE_DIR = VAULT_DIR / "dnd5e" / "SOURCE"

# Model paths
PIPER_MODEL_DIR = MODELS_DIR / "piper"


# ---------------------------------------------------------------------------
# Universal I/O Utilities
# ---------------------------------------------------------------------------

def safe_save_json(filepath: Path, data: dict) -> None:
    """Write JSON with .bak rotation for crash safety.

    1. Copy existing file to .bak (if present)
    2. Write new data via json.dump
    Usable by any game system: Burnwillow, Crown, BitD, etc.
    """
    import json
    import shutil

    filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.exists():
        try:
            shutil.copy2(str(filepath), str(filepath.with_suffix(".json.bak")))
        except OSError:
            pass  # Non-fatal — proceed with save
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

"""
codex.core.cache - Persistent Lore Cache
==========================================

System-separated, lazy-loaded JSON-backed cache for Mimir query results.
Applies the Grit Narrative Protocol before storing AI-generated text.

Keys are prefixed with the system tag to prevent cross-system bleed:
    ``STC:whirlpool``, ``burnwillow:rot-beetle``, ``dnd5e:beholder``

Usage::

    from codex.core.cache import LoreCache, grit_scrub

    cache = LoreCache()
    hit = cache.get("burnwillow", "rot-beetle")
    if hit is None:
        result = query_mimir(...)
        result = grit_scrub(result)
        cache.put("burnwillow", "rot-beetle", result)

WO V20.5.4
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional

from codex.paths import STATE_DIR


# ---------------------------------------------------------------------------
# Grit Narrative Protocol — pre-cache scrubbing
# ---------------------------------------------------------------------------

BANNED_WORDS = frozenset({"untold", "vast", "mystic", "tapestry", "secrets", "grand"})


def grit_scrub(text: str) -> str:
    """Apply Grit Narrative Protocol to AI-generated text before caching.

    - Strips markdown formatting (bold/italic asterisks)
    - Strips emoji (Unicode ranges matching voice_clean in butler.py)
    - Removes banned high-fantasy filler words
    - Collapses whitespace
    """
    # Strip markdown asterisks
    cleaned = re.sub(r'\*+', '', text)
    # Strip emoji
    cleaned = re.sub(
        r'[\U0001F300-\U0001FAD6\u2600-\u27BF\uFE0F]', '', cleaned
    )
    # Remove banned words (word-boundary-aware, case-insensitive)
    for word in BANNED_WORDS:
        cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


# ---------------------------------------------------------------------------
# Persistent Lore Cache
# ---------------------------------------------------------------------------

class LoreCache:
    """Dict[str, str] backed by ``state/lore_cache.json``.

    Lazy-loaded: the JSON file is only read on the first ``get``/``put``/
    ``has``/``clear`` call.  Writes are atomic (tempfile + os.replace).

    Keys are ``{system_tag}:{query_lower}`` to prevent cross-system bleed.
    """

    def __init__(self, cache_path: Optional[Path] = None):
        self._path = cache_path or (STATE_DIR / "lore_cache.json")
        self._data: Optional[Dict[str, str]] = None  # None = not yet loaded

    # -- lazy load ----------------------------------------------------------

    def _ensure_loaded(self):
        """Read JSON from disk on first access.  Corrupt files → empty dict."""
        if self._data is not None:
            return
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    # -- public API ---------------------------------------------------------

    def get(self, system_tag: str, key: str) -> Optional[str]:
        """Return cached value or ``None``."""
        self._ensure_loaded()
        return self._data.get(f"{system_tag}:{key}")

    def put(self, system_tag: str, key: str, value: str) -> None:
        """Store a value and flush to disk."""
        self._ensure_loaded()
        self._data[f"{system_tag}:{key}"] = value
        self._save()

    def has(self, system_tag: str, key: str) -> bool:
        """Check for key existence without returning the value."""
        self._ensure_loaded()
        return f"{system_tag}:{key}" in self._data

    def clear(self, system_tag: Optional[str] = None) -> int:
        """Wipe entries.  If *system_tag* given, only wipe that prefix.

        Returns the number of entries removed.
        """
        self._ensure_loaded()
        if system_tag:
            prefix = f"{system_tag}:"
            before = len(self._data)
            self._data = {k: v for k, v in self._data.items()
                          if not k.startswith(prefix)}
            removed = before - len(self._data)
        else:
            removed = len(self._data)
            self._data = {}
        self._save()
        return removed

    @property
    def size(self) -> int:
        """Total number of cached entries."""
        self._ensure_loaded()
        return len(self._data)

    # -- persistence --------------------------------------------------------

    def _save(self) -> None:
        """Atomic write via tempfile + os.replace (Butler bridge pattern)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._path.parent), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, str(self._path))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except OSError:
            pass  # Disk full / permissions — don't crash the game

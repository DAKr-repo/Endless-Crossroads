"""
codex_utils.py -- Unified Logging for C.O.D.E.X. Maintenance Scripts
=====================================================================

Provides a single log format and append-mode file handler shared by
all four maintenance scripts (Maestro, Index Builder, Registry Builder,
Registry Autofill).  Eliminates the filemode='w' overwrite bug and
ensures every script writes to the same codex_builder.log with a
consistent timestamp + script tag format.
"""

import logging
from datetime import datetime
from pathlib import Path

# Shared log file path -- all scripts append here
LOG_FILE = Path(__file__).resolve().parent.parent / "codex_builder.log"

# Unified format: [2026-02-14 12:00:00] [SCRIPT] LEVEL: message
_LOG_FORMAT = "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(script_name: str) -> logging.Logger:
    """Return a Logger configured with file (append) + stream handlers.

    Uses a unified format across all maintenance scripts.  The file
    handler always opens in append mode ('a'), fixing the overwrite bug
    previously present in codex_index_builder.py.

    Args:
        script_name: Tag used as the logger name (e.g. "INDEX_BUILDER").

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(script_name)

    # Avoid stacking handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # File handler -- always append
    fh = logging.FileHandler(str(LOG_FILE), mode="a")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Stream handler -- console output
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger


def log_event(script: str, message: str, level: str = "INFO"):
    """Write a standardized log line to codex_builder.log.

    Format: [YYYY-MM-DD HH:MM:SS] [SCRIPT] LEVEL: message

    This is a lightweight function for scripts that don't need a full
    Logger instance (e.g. Maestro's thin _log wrapper, or one-off
    pipeline stage markers in Autofill).
    """
    timestamp = datetime.now().strftime(_DATE_FORMAT)
    line = f"[{timestamp}] [{script}] {level}: {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)

#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source venv/bin/activate 2>/dev/null || true
exec python maintenance/codex_maestro.py "$@"

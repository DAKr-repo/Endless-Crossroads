#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source venv/bin/activate 2>/dev/null || true
exec python -m uvicorn codex.services.mouth:app --host 0.0.0.0 --port 5001 "$@"

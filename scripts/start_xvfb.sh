#!/bin/bash
# Start Xvfb virtual framebuffer for headless Rich terminal capture.
# Used by the Scrying Engine (codex/bots/scryer.py) for screenshot rendering.
#
# Usage: source scripts/start_xvfb.sh
# Or run via systemd: codex_xvfb.service

DISPLAY_NUM="${CODEX_DISPLAY:-99}"
RESOLUTION="${CODEX_RESOLUTION:-1280x720x24}"

# Kill any existing Xvfb on this display
if [ -f "/tmp/.X${DISPLAY_NUM}-lock" ]; then
    echo "[XVFB] Cleaning stale lock for :${DISPLAY_NUM}"
    kill "$(cat /tmp/.X${DISPLAY_NUM}-lock 2>/dev/null)" 2>/dev/null || true
    rm -f "/tmp/.X${DISPLAY_NUM}-lock"
fi

Xvfb ":${DISPLAY_NUM}" -screen 0 "${RESOLUTION}" -ac &
XVFB_PID=$!

export DISPLAY=":${DISPLAY_NUM}"
echo "[XVFB] Started on :${DISPLAY_NUM} (PID ${XVFB_PID}, ${RESOLUTION})"

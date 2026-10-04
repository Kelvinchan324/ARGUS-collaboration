#!/usr/bin/env bash
# Copy ARGUS robot skill into the OpenClaw workspace. Does not start the gateway.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}/skills/robot-bridge"
mkdir -p "$DEST"
cp "$ROOT/agent/openclaw/robot-bridge/SKILL.md" "$DEST/SKILL.md"
cp "$ROOT/agent/openclaw/ROBOT.md" "$DEST/ROBOT.md"
cp "$ROOT/agent/openclaw/MISSION.md" "$DEST/MISSION.md"
echo "installed skill -> $DEST"
echo "OpenClaw will load it after: openclaw gateway restart   (if the gateway is running)"

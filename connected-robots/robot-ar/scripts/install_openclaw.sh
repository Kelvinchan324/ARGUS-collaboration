#!/usr/bin/env bash
# Install OpenClaw CLI if missing, seed a loopback workspace, copy the robot skill.
# Does NOT install a systemd daemon or bind the gateway to the campus LAN.
# Full chat still needs: openclaw onboard  (DeepSeek key) — optional; agent/loop.py is enough.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v openclaw >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    echo "installing openclaw via npm (user prefix)…"
    mkdir -p "$HOME/.local"
    npm install -g openclaw --prefix "$HOME/.local"
    export PATH="$HOME/.local/bin:$PATH"
  else
    echo "npm not found. Install Node.js, then rerun." >&2
    echo "Skill files can still be copied: bash $ROOT/scripts/install_openclaw_skill.sh" >&2
    bash "$ROOT/scripts/install_openclaw_skill.sh"
    exit 1
  fi
fi

if [[ ! -d "$HOME/.openclaw/workspace" ]]; then
  if openclaw setup --help 2>/dev/null | grep -q baseline; then
    openclaw setup --baseline --non-interactive --accept-risk || true
  fi
  mkdir -p "$HOME/.openclaw/workspace/skills"
fi

bash "$ROOT/scripts/install_openclaw_skill.sh"
echo "openclaw: $(command -v openclaw || echo missing)"
echo "gateway is optional. Robot language path:  $ROOT/.venv/bin/python agent/loop.py --plan-only '前進 1 秒'"

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install --upgrade pip
"$ROOT/.venv/bin/pip" install -r "$ROOT/robot_bridge/requirements.txt"
chmod +x "$ROOT/scripts/"*.sh
echo "Next: bash $ROOT/scripts/bringup.sh"

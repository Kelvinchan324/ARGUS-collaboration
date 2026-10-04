#!/usr/bin/env bash
# Separate venv so robot_bridge does not inherit LeRobot's torch stack.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv-lerobot"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install 'lerobot'
echo
echo "LeRobot venv: $VENV"
echo "Calibrate (arm must be powered, mid-pose):"
echo "  $VENV/bin/lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=left_follower"

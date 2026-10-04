#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/robot_bridge"
python3 test_commands.py
cd "$ROOT/agent"
python3 test_planner.py
echo "all tests ok"

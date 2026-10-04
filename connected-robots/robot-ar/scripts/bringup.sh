#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
CHASSIS_PORT="${CHASSIS_PORT:-/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0}"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "venv missing. Run: $ROOT/scripts/install_deps.sh" >&2
  exit 1
fi

cd "$ROOT"
echo "serial devices:"
ls -l /dev/ttyUSB* /dev/ttyACM* /dev/serial/by-id 2>/dev/null || echo "  (none — mock mode)"

if command -v tmux >/dev/null 2>&1; then
  SESSION="robot"
  tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"
  tmux new-session -d -s "$SESSION" -c "$ROOT" \
    "CHASSIS_PORT='$CHASSIS_PORT' $VENV/bin/python robot_bridge/server.py --host $HOST --port $PORT; read"
  echo "tmux session 'robot' started"
  echo "attach: tmux attach -t robot"
else
  CHASSIS_PORT="$CHASSIS_PORT" exec "$VENV/bin/python" robot_bridge/server.py --host "$HOST" --port "$PORT"
fi

echo "teleop UI: http://$(hostname -I | awk '{print $1}'):$PORT/"

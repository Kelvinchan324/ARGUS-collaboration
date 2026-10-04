#!/usr/bin/env bash
# Run ON Thor with the arm powered. Person must be next to the robot for the sweep.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv-lerobot"
SIDE="${1:-}"
if [[ ! -x "$VENV/bin/lerobot-calibrate" ]]; then
  echo "Install first:  bash $ROOT/scripts/install_lerobot.sh" >&2
  exit 1
fi
if [[ -z "$SIDE" ]]; then
  echo "usage: $0 left|right|find"
  echo "  find  — unplug/replug wizard (lerobot-find-port)"
  echo "Then edit config/ports.yaml and rerun: $0 left"
  exit 1
fi
if [[ "$SIDE" == "find" ]]; then
  exec "$VENV/bin/lerobot-find-port"
fi
python3 - <<PY
import sys
from pathlib import Path
sys.path.insert(0, "$ROOT/robot_bridge")
from arm_hw import load_ports
cfg = load_ports(Path("$ROOT/config/ports.yaml"))
side = "$SIDE"
arm = (cfg.get("arms") or {}).get(side)
if not arm:
    raise SystemExit(f"no arms.{side} in config/ports.yaml")
print(arm)
PY
PORT=$(python3 - <<PY
from pathlib import Path
import yaml
cfg = yaml.safe_load(Path("$ROOT/config/ports.yaml").read_text())
print(cfg["arms"]["$SIDE"]["port"])
PY
)
RID=$(python3 - <<PY
from pathlib import Path
import yaml
cfg = yaml.safe_load(Path("$ROOT/config/ports.yaml").read_text())
print(cfg["arms"]["$SIDE"]["id"])
PY
)
TYPE=$(python3 - <<PY
from pathlib import Path
import yaml
cfg = yaml.safe_load(Path("$ROOT/config/ports.yaml").read_text())
print(cfg.get("robot_type", "so101_follower"))
PY
)
echo "Calibrating $SIDE  type=$TYPE  port=$PORT  id=$RID"
echo "Put every joint near mid-range, then sweep limits when asked."
exec "$VENV/bin/lerobot-calibrate" --robot.type="$TYPE" --robot.port="$PORT" --robot.id="$RID"

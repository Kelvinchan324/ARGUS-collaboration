#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DEBIAN_FRONTEND=noninteractive

echo "[install] packages"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip python3-serial tmux v4l-utils

echo "[install] dialout group for serial ports"
sudo usermod -aG dialout,plugdev "$USER" || true
sudo tee /etc/udev/rules.d/99-bimanual-serial.rules >/dev/null <<'EOF'
KERNEL=="ttyUSB*", GROUP="dialout", MODE="0660"
KERNEL=="ttyACM*", GROUP="dialout", MODE="0660"
EOF
sudo udevadm control --reload-rules || true

echo "[install] python venv"
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install --upgrade pip
"$ROOT/.venv/bin/pip" install -r "$ROOT/robot_bridge/requirements.txt"

echo
echo "Done. Open a new SSH session so dialout takes effect, then:"
echo "  $ROOT/scripts/bringup.sh"

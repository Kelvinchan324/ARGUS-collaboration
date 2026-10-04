#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== USB ==="
lsusb || true
echo
echo "=== tty ==="
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "no ttyUSB/ttyACM"
echo
echo "=== by-id (prefer these in config/ports.yaml) ==="
ls -l /dev/serial/by-id 2>/dev/null || echo "no /dev/serial/by-id"
echo
echo "=== video ==="
ls -l /dev/video* 2>/dev/null || echo "no /dev/video*"
echo
echo "Chassis USB-serial -> config chassis (bridge auto-picks ttyUSB*)."
echo "SO-ARM Feetech adapters -> usually ttyACM*. Map left/right in config/ports.yaml."
echo "If lerobot is installed:  $ROOT/.venv-lerobot/bin/lerobot-find-port"

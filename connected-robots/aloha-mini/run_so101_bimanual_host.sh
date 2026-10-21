#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LEROBOT_ROOT="${LEROBOT_ROOT:-$HOME/Robot/lerobot}"
PYTHON="${LEROBOT_PYTHON:-}"

if [[ -z "$PYTHON" ]]; then
    for candidate in "$LEROBOT_ROOT/venv/bin/python" "$LEROBOT_ROOT/.venv/bin/python"; do
        if [[ -x "$candidate" ]]; then
            PYTHON="$candidate"
            break
        fi
    done
fi

if [[ ! -x "$PYTHON" ]]; then
    printf 'LeRobot Python not found. Set LEROBOT_ROOT or LEROBOT_PYTHON.\n' >&2
    exit 1
fi

if [[ -d "$LEROBOT_ROOT/src" ]]; then
    export PYTHONPATH="$LEROBOT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
fi

exec "$PYTHON" "$SCRIPT_DIR/so101_bimanual_host.py" "$@"

#!/bin/sh
set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONFIG_FILE=${SO101_CONFIG_FILE:-"$HOME/.config/argus-so101-control.env"}

if [ -f "$CONFIG_FILE" ]; then
    . "$CONFIG_FILE"
fi

if [ -z "${SO101_FOLLOWER_HOST:-}" ]; then
    printf 'Set SO101_FOLLOWER_HOST in %s before launching.\n' "$CONFIG_FILE" >&2
    exit 1
fi

LEROBOT_ROOT=${LEROBOT_ROOT:-"$HOME/lerobot"}
SO101_CAMERA_URL=${SO101_CAMERA_URL:-"http://${SO101_FOLLOWER_HOST}:8000/"}

if [ "${1-}" = "--run-control" ]; then
    PYTHON=${LEROBOT_PYTHON:-}
    if [ -z "$PYTHON" ]; then
        for candidate in "$LEROBOT_ROOT/venv/bin/python" "$LEROBOT_ROOT/.venv/bin/python"; do
            if [ -x "$candidate" ]; then
                PYTHON=$candidate
                break
            fi
        done
    fi
    if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
        printf 'LeRobot Python not found. Set LEROBOT_ROOT or LEROBOT_PYTHON.\n' >&2
        status=1
    else
        "$PYTHON" "$SCRIPT_DIR/so100_bimanual_leader.py" \
            --follower-host "$SO101_FOLLOWER_HOST"
        status=$?
    fi
    printf '\nLeader controller exited with status %s.\n' "$status"
    printf 'Press Enter to close this terminal... '
    read -r _
    exit "$status"
fi

/usr/bin/lxterminal \
    --working-directory="$SCRIPT_DIR" \
    --title="SO-101 Leader Control" \
    --command="$SCRIPT_DIR/start-so101-control.sh --run-control" &

/usr/bin/xdg-open "$SO101_CAMERA_URL"

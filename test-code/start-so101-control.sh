#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SO101_CONFIG_FILE:-$SCRIPT_DIR/so101-config.env}"

SO101_ROLE=
SO101_FOLLOWER_HOST=
SO101_LEFT_LEADER_PORT=/dev/ttyACM1
SO101_RIGHT_LEADER_PORT=/dev/ttyACM0
SO101_LEFT_FOLLOWER_PORT=/dev/ttyACM0
SO101_RIGHT_FOLLOWER_PORT=/dev/ttyACM1
SO101_LEFT_ZMQ_PORT=5555
SO101_RIGHT_ZMQ_PORT=5556
SO101_CAMERA_PORT=8000
SO101_CAMERA_INDEX=0
SO101_CAMERA_TOP=
SO101_CAMERA_LEFT=2
SO101_CAMERA_RIGHT=4
SO101_CAMERA_WIDTH=640
SO101_CAMERA_HEIGHT=480
SO101_CAMERA_FPS=15
SO101_CAMERA_QUALITY=75
SO101_FREQUENCY=30
LEROBOT_ROOT="$HOME/ARGUS-collaboration/lerobot"
LEROBOT_PYTHON=

if [[ ! -f "$CONFIG_FILE" ]]; then
    printf 'Configuration not found: %s\nRun %s/setup-so101-device.sh first.\n' \
        "$CONFIG_FILE" "$SCRIPT_DIR" >&2
    exit 1
fi

while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" != *=* ]]; then
        printf 'Invalid configuration line: %s\n' "$line" >&2
        exit 1
    fi
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
        SO101_ROLE) SO101_ROLE="$value" ;;
        SO101_FOLLOWER_HOST) SO101_FOLLOWER_HOST="$value" ;;
        SO101_LEFT_LEADER_PORT) SO101_LEFT_LEADER_PORT="$value" ;;
        SO101_RIGHT_LEADER_PORT) SO101_RIGHT_LEADER_PORT="$value" ;;
        SO101_LEFT_FOLLOWER_PORT) SO101_LEFT_FOLLOWER_PORT="$value" ;;
        SO101_RIGHT_FOLLOWER_PORT) SO101_RIGHT_FOLLOWER_PORT="$value" ;;
        SO101_LEFT_ZMQ_PORT) SO101_LEFT_ZMQ_PORT="$value" ;;
        SO101_RIGHT_ZMQ_PORT) SO101_RIGHT_ZMQ_PORT="$value" ;;
        SO101_CAMERA_PORT) SO101_CAMERA_PORT="$value" ;;
        SO101_CAMERA_INDEX) SO101_CAMERA_INDEX="$value" ;;
        SO101_CAMERA_TOP) SO101_CAMERA_TOP="$value" ;;
        SO101_CAMERA_LEFT) SO101_CAMERA_LEFT="$value" ;;
        SO101_CAMERA_RIGHT) SO101_CAMERA_RIGHT="$value" ;;
        SO101_CAMERA_WIDTH) SO101_CAMERA_WIDTH="$value" ;;
        SO101_CAMERA_HEIGHT) SO101_CAMERA_HEIGHT="$value" ;;
        SO101_CAMERA_FPS) SO101_CAMERA_FPS="$value" ;;
        SO101_CAMERA_QUALITY) SO101_CAMERA_QUALITY="$value" ;;
        SO101_FREQUENCY) SO101_FREQUENCY="$value" ;;
        LEROBOT_ROOT) LEROBOT_ROOT="${value/#\~/$HOME}" ;;
        LEROBOT_PYTHON) LEROBOT_PYTHON="${value/#\~/$HOME}" ;;
        *) printf 'Unknown configuration key: %s\n' "$key" >&2; exit 1 ;;
    esac
done < "$CONFIG_FILE"

# Old local configs keep their camera as the top view. Never rewrite the config.
SO101_CAMERA_TOP="${SO101_CAMERA_TOP:-$SO101_CAMERA_INDEX}"

if [[ "$SO101_ROLE" != leader && "$SO101_ROLE" != follower ]]; then
    printf 'Set SO101_ROLE=leader or SO101_ROLE=follower in %s.\n' "$CONFIG_FILE" >&2
    exit 1
fi

for value in "$SO101_CAMERA_WIDTH" "$SO101_CAMERA_HEIGHT" "$SO101_CAMERA_FPS" "$SO101_CAMERA_QUALITY"; do
    if [[ ! "$value" =~ ^[0-9]+$ ]] || ((10#$value < 1)); then
        printf 'Camera width, height, FPS and quality must be positive integers.\n' >&2
        exit 1
    fi
done
if ((10#$SO101_CAMERA_QUALITY > 100)); then
    printf 'Camera quality must be between 1 and 100.\n' >&2
    exit 1
fi
for source in "$SO101_CAMERA_TOP" "$SO101_CAMERA_LEFT" "$SO101_CAMERA_RIGHT"; do
    if [[ ! "$source" =~ ^[0-9]+$ && "$source" != /dev/* ]]; then
        printf 'Camera sources must be nonnegative indices or /dev/ paths; got %s.\n' "$source" >&2
        exit 1
    fi
done
if [[ "$SO101_ROLE" == follower ]] && [[ "$SO101_CAMERA_TOP" == "$SO101_CAMERA_LEFT" || "$SO101_CAMERA_TOP" == "$SO101_CAMERA_RIGHT" || "$SO101_CAMERA_LEFT" == "$SO101_CAMERA_RIGHT" ]]; then
    printf 'Top, left and right cameras must use different devices. Run discover-cameras.py.\n' >&2
    exit 1
fi
if [[ "$SO101_ROLE" == leader && -z "$SO101_FOLLOWER_HOST" ]]; then
    printf 'Set SO101_FOLLOWER_HOST to the Aloha Mini host or IP in %s.\n' "$CONFIG_FILE" >&2
    exit 1
fi
for port in "$SO101_LEFT_ZMQ_PORT" "$SO101_RIGHT_ZMQ_PORT" "$SO101_CAMERA_PORT"; do
    if [[ ! "$port" =~ ^[0-9]+$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
        printf 'Ports must be numeric values from 1 to 65535; got %s.\n' "$port" >&2
        exit 1
    fi
done
if [[ "$SO101_LEFT_ZMQ_PORT" == "$SO101_RIGHT_ZMQ_PORT" ]]; then
    printf 'SO101_LEFT_ZMQ_PORT and SO101_RIGHT_ZMQ_PORT must differ.\n' >&2
    exit 1
fi
if [[ ! "$SO101_CAMERA_INDEX" =~ ^[0-9]+$ || ! "$SO101_FREQUENCY" =~ ^[0-9]+([.][0-9]+)?$ ]] \
    || ! awk -v frequency="$SO101_FREQUENCY" 'BEGIN { exit !(frequency > 0) }'; then
    printf 'Camera index must be nonnegative and frequency must be positive.\n' >&2
    exit 1
fi

find_python() {
    if [[ -n "$LEROBOT_PYTHON" && -x "$LEROBOT_PYTHON" ]]; then
        PYTHON="$LEROBOT_PYTHON"
        return 0
    fi
    for candidate in "$LEROBOT_ROOT/.venv/bin/python" "$LEROBOT_ROOT/venv/bin/python"; do
        if [[ -x "$candidate" ]]; then
            PYTHON="$candidate"
            return 0
        fi
    done
    printf 'LeRobot Python not found under %s. Install it with uv sync --locked --extra feetech --extra pyzmq-dep.\n' \
        "$LEROBOT_ROOT" >&2
    return 1
}

camera_url() {
    if [[ "$SO101_ROLE" == follower ]]; then
        printf 'http://127.0.0.1:%s/' "$SO101_CAMERA_PORT"
    elif [[ "$SO101_FOLLOWER_HOST" == *:* && "$SO101_FOLLOWER_HOST" != \[* ]]; then
        printf 'http://[%s]:%s/' "$SO101_FOLLOWER_HOST" "$SO101_CAMERA_PORT"
    else
        printf 'http://%s:%s/' "$SO101_FOLLOWER_HOST" "$SO101_CAMERA_PORT"
    fi
}

if [[ "${1-}" == "--check-config" ]]; then
    printf 'Role: %s\n' "$SO101_ROLE"
    printf 'LeRobot checkout: %s\n' "$LEROBOT_ROOT"
    printf 'Leader serial ports: %s, %s\n' "$SO101_LEFT_LEADER_PORT" "$SO101_RIGHT_LEADER_PORT"
    printf 'Follower serial ports: %s, %s\n' "$SO101_LEFT_FOLLOWER_PORT" "$SO101_RIGHT_FOLLOWER_PORT"
    printf 'ZeroMQ ports: %s, %s\n' "$SO101_LEFT_ZMQ_PORT" "$SO101_RIGHT_ZMQ_PORT"
    printf 'Camera page: %s\n' "$(camera_url)"
    printf 'Cameras (top / left gripper / right): %s / %s / %s\n' "$SO101_CAMERA_TOP" "$SO101_CAMERA_LEFT" "$SO101_CAMERA_RIGHT"
    printf 'Camera request: %sx%s at %s FPS, JPEG quality %s\n' "$SO101_CAMERA_WIDTH" "$SO101_CAMERA_HEIGHT" "$SO101_CAMERA_FPS" "$SO101_CAMERA_QUALITY"
    exit 0
fi

if [[ "${1-}" == "--run-control" ]]; then
    if ! find_python; then
        status=1
    elif [[ "$SO101_ROLE" == leader ]]; then
        "$PYTHON" "$SCRIPT_DIR/so100_bimanual_leader.py" \
            --follower-host "$SO101_FOLLOWER_HOST" \
            --left-port "$SO101_LEFT_LEADER_PORT" \
            --right-port "$SO101_RIGHT_LEADER_PORT" \
            --left-zmq-port "$SO101_LEFT_ZMQ_PORT" \
            --right-zmq-port "$SO101_RIGHT_ZMQ_PORT" \
            --frequency "$SO101_FREQUENCY"
        status=$?
    else
        "$PYTHON" "$SCRIPT_DIR/so101_bimanual_receiver.py" \
            --left-port "$SO101_LEFT_FOLLOWER_PORT" \
            --right-port "$SO101_RIGHT_FOLLOWER_PORT" \
            --left-zmq-port "$SO101_LEFT_ZMQ_PORT" \
            --right-zmq-port "$SO101_RIGHT_ZMQ_PORT" \
            --camera-port "$SO101_CAMERA_PORT" \
            --camera-index "$SO101_CAMERA_INDEX" \
            --camera-top "$SO101_CAMERA_TOP" \
            --camera-left "$SO101_CAMERA_LEFT" \
            --camera-right "$SO101_CAMERA_RIGHT" \
            --camera-width "$SO101_CAMERA_WIDTH" \
            --camera-height "$SO101_CAMERA_HEIGHT" \
            --camera-fps "$SO101_CAMERA_FPS" \
            --camera-quality "$SO101_CAMERA_QUALITY" \
            --frequency "$SO101_FREQUENCY"
        status=$?
    fi
    printf '\nSO-101 %s service exited with status %s.\n' "$SO101_ROLE" "$status"
    printf 'Press Enter to close this terminal... '
    read -r _ || true
    exit "$status"
fi

CAMERA_URL="$(camera_url)"
/usr/bin/lxterminal \
    --working-directory="$SCRIPT_DIR" \
    --title="SO-101 ${SO101_ROLE^}" \
    --command="$SCRIPT_DIR/start-so101-control.sh --run-control" &
/usr/bin/xdg-open "$CAMERA_URL"

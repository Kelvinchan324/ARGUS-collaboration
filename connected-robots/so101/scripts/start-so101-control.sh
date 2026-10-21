#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/../../.." && pwd)

if [ "${1-}" = "--camera-url" ]; then
    if [ "$#" -lt 2 ]; then
        printf 'Usage: %s [--camera-url URL] --follower-host HOST [leader options...]\n' "$0" >&2
        exit 2
    fi
    camera_url=$2
    shift 2
    xdg-open "$camera_url" >/dev/null 2>&1 &
fi

exec python3 "$repo_root/connected-robots/so101/leader_teleop.py" "$@"

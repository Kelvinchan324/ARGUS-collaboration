#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$SCRIPT_DIR/so101-config.env"
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
DESKTOP_FILE="$DESKTOP_DIR/SO-101-Control-and-Camera.desktop"

mkdir -p "$DESKTOP_DIR"
if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$SCRIPT_DIR/so101-config.env.example" "$CONFIG_FILE"
    printf 'Created local config: %s\n' "$CONFIG_FILE"
else
    printf 'Keeping existing config: %s\n' "$CONFIG_FILE"
fi

install -m 755 "$SCRIPT_DIR/SO-101-Control-and-Camera.desktop" "$DESKTOP_FILE"
chmod +x "$SCRIPT_DIR/start-so101-control.sh"

printf 'Installed desktop shortcut: %s\n' "$DESKTOP_FILE"
printf 'Edit %s and set SO101_ROLE and the serial ports.\n' "$CONFIG_FILE"
if [[ "$DESKTOP_DIR" != "$HOME/Desktop" ]]; then
    printf 'The desktop environment uses %s as its Desktop directory.\n' "$DESKTOP_DIR"
fi
printf 'Repository: %s\n' "$REPO_ROOT"

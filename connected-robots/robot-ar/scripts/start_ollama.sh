#!/usr/bin/env bash
# NVIDIA Ollama on Jetson Thor (JetPack 7). Loopback only — do not expose 11434.
set -euo pipefail

IMAGE="${OLLAMA_IMAGE:-ghcr.io/nvidia-ai-iot/ollama:r38.2.arm64-sbsa-cu130-24.04}"
NAME="${OLLAMA_CONTAINER:-ollama}"
DATA="${HOME}/ollama-data"
BIND="${OLLAMA_BIND:-127.0.0.1:11434}"
MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
API="http://127.0.0.1:11434"

mkdir -p "$DATA"

wait_api() {
  python3 - "$API" <<'PY'
import sys, time, urllib.request, urllib.error
base = sys.argv[1]
for _ in range(60):
    try:
        urllib.request.urlopen(base + "/api/tags", timeout=2).read()
        print("ollama API ready")
        raise SystemExit(0)
    except (urllib.error.URLError, TimeoutError, OSError):
        time.sleep(1)
print("ollama API not ready", file=sys.stderr)
raise SystemExit(1)
PY
}

start_server() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker missing" >&2
    exit 1
  fi
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "pulling $IMAGE"
    docker pull "$IMAGE"
  fi
  if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
    echo "container $NAME already running"
  elif docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
    docker start "$NAME" >/dev/null
    echo "started existing container $NAME"
  else
    # Image's /start_ollama backgrounds serve then exits; keep a foreground tail.
    docker run -d --name "$NAME" --restart unless-stopped \
      --runtime nvidia --network host \
      -e OLLAMA_HOST="$BIND" \
      -v "$DATA:/data" \
      --entrypoint /bin/bash \
      "$IMAGE" -lc '/start_ollama; exec tail -F /data/logs/ollama.log'
    echo "created container $NAME"
  fi
  wait_api
}

pull_model() {
  start_server
  echo "pulling $MODEL"
  docker exec "$NAME" ollama pull "$MODEL"
  python3 - "$API" "$MODEL" <<'PY'
import json, sys, urllib.request
base, model = sys.argv[1], sys.argv[2]
tags = json.loads(urllib.request.urlopen(base + "/api/tags", timeout=10).read().decode())
names = [m.get("name") for m in tags.get("models", [])]
print("models:", ", ".join(names) or "(none)")
if not any(model == n or n.startswith(model + ":") or n.split(":")[0] == model.split(":")[0] for n in names):
    raise SystemExit(f"{model} not in ollama tags")
PY
}

cmd="${1:-start}"
case "$cmd" in
  start) start_server ;;
  pull) pull_model ;;
  stop)
    docker stop "$NAME" >/dev/null 2>&1 || true
    echo "stopped $NAME"
    ;;
  *)
    echo "usage: $0 {start|pull|stop}" >&2
    exit 2
    ;;
esac

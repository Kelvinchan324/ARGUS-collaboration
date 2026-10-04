#!/usr/bin/env python3
"""Language in → robot_bridge HTTP out. This is the Phase-2 agent boundary."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "robot_bridge"))
from planner import plan  # noqa: E402

BASE = "http://127.0.0.1:8080"


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="+")
    p.add_argument("--plan-only", action="store_true")
    args = p.parse_args()
    text = " ".join(args.text)
    planned = plan(text)
    print(json.dumps(planned, ensure_ascii=False, indent=2))
    if args.plan_only:
        return
    result = post("/task", {"text": planned.get("text", text), "steps": planned["steps"]})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    for _ in range(200):
        st = get("/task")
        if st.get("finished") or not st.get("running"):
            print(json.dumps(st, ensure_ascii=False, indent=2))
            if st.get("error"):
                sys.exit(2)
            return
        time.sleep(0.1)


if __name__ == "__main__":
    main()

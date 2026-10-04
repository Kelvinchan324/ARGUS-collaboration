#!/usr/bin/env python3
"""CLI: python cli.py '前進 1 秒 然後 關閉夾爪'"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8080"


def post(path: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode())


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python cli.py '<command>'")
        print("example: python cli.py '前進 1 秒 然後 關閉夾爪'")
        sys.exit(1)
    text = " ".join(sys.argv[1:])
    if text in {"stop", "停"}:
        print(json.dumps(post("/stop"), ensure_ascii=False, indent=2))
        return
    print(json.dumps(post("/command", {"text": text}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

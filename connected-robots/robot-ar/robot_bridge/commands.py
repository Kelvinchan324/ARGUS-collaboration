"""Tiny language → primitive parser. No LLM required."""

from __future__ import annotations

import re
from typing import Any

DURATION = re.compile(
    r"(?:(?P<sec>[\d.]+)\s*(?:s|sec|secs|second|seconds|秒))|"
    r"(?:(?P<ms>[\d.]+)\s*ms)",
    re.I,
)

MOVE = [
    (re.compile(r"(前進|向前|forward|go forward)", re.I), {"vx": 0.30, "vy": 0.0, "wz": 0.0}),
    (re.compile(r"(後退|向後|back|backward|reverse)", re.I), {"vx": -0.30, "vy": 0.0, "wz": 0.0}),
    (re.compile(r"(左移|向左平移|往左平移|strafe left|left strafe)", re.I), {"vx": 0.0, "vy": 0.30, "wz": 0.0}),
    (re.compile(r"(右移|向右平移|往右平移|strafe right|right strafe)", re.I), {"vx": 0.0, "vy": -0.30, "wz": 0.0}),
    (re.compile(r"(左轉|逆時針|turn left|rotate left)", re.I), {"vx": 0.0, "vy": 0.0, "wz": 0.70}),
    (re.compile(r"(右轉|順時針|turn right|rotate right)", re.I), {"vx": 0.0, "vy": 0.0, "wz": -0.70}),
]


def _duration(text: str, default: float = 1.0) -> float:
    m = DURATION.search(text)
    if not m:
        return default
    if m.group("sec"):
        return max(0.05, float(m.group("sec")))
    return max(0.05, float(m.group("ms")) / 1000.0)


def _side(text: str) -> str:
    if re.search(r"(左臂|left)", text, re.I):
        return "left"
    if re.search(r"(右臂|right)", text, re.I):
        return "right"
    return "both"


def parse_command(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty command")

    parts = re.split(r"\s*(?:然後|接着|接著|and then|,|;|再)\s*", raw)
    parts = [p.strip() for p in parts if p.strip()]
    steps: list[dict[str, Any]] = []

    for part in parts:
        low = part.lower()
        if re.search(r"^(停|停止|急停|stop|halt|estop)$", part, re.I):
            steps.append({"action": "stop"})
            continue
        if re.search(r"(開電機|使能|enable motor)", part, re.I):
            steps.append({"action": "motor", "enabled": True})
            continue
        if re.search(r"(關電機|disable motor)", part, re.I):
            steps.append({"action": "motor", "enabled": False})
            continue
        if re.search(r"(復位里程計|reset odom)", part, re.I):
            steps.append({"action": "reset_odom"})
            continue
        if re.search(r"(打開夾爪|張開夾爪|open gripper)", part, re.I):
            steps.append({"action": "gripper", "side": _side(part), "open": 1.0})
            continue
        if re.search(r"(關閉夾爪|合上夾爪|夾爪.*合上|合上.*夾爪|close gripper)", part, re.I):
            steps.append({"action": "gripper", "side": _side(part), "open": 0.0})
            continue
        if re.search(r"(home|回原點|回home)", part, re.I):
            steps.append({"action": "arm_preset", "side": _side(part), "preset": "home"})
            continue
        if re.search(r"(pick pose|預備抓取|到抓取位)", part, re.I):
            steps.append({"action": "arm_preset", "side": _side(part), "preset": "pick"})
            continue
        if re.search(r"(等|wait|pause)", part, re.I):
            steps.append({"action": "wait", "duration": _duration(part, 1.0)})
            continue

        matched = False
        for pat, twist in MOVE:
            if pat.search(part):
                step = {"action": "move", "duration": _duration(part, 1.0), **twist}
                steps.append(step)
                matched = True
                break
        if not matched:
            raise ValueError(f"unrecognized command: {part}")

    return {"text": raw, "steps": steps}

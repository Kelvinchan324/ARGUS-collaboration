"""Regex first, then cloud LLM (DeepSeek), then local Ollama. Never talks to serial."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "robot_bridge"))
from commands import parse_command

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_ACTIONS = {
    "move",
    "wait",
    "stop",
    "motor",
    "reset_odom",
    "gripper",
    "arm_preset",
    "arm_joints",
}

SYSTEM = """You control a bimanual wheeled robot through JSON steps only.
Each step MUST have an "action" field. Do not use the action name as a key.
Sign convention is mandatory:
- +vx forward, -vx backward. 後/往後/後退/back MUST use negative vx.
- +vy left, -vy right. 左平移 positive vy.
- +wz CCW, -wz CW.
- 一點/一下 = duration 0.2–0.3 and |vx|,|vy| <= 0.2
- 別轉/不要轉 = wz 0, do not add a turn step
Allowed actions:
- move: vx, vy, wz, duration (seconds). |vx|,|vy|<=0.5, |wz|<=1.2
- wait: duration
- stop
- motor: enabled bool
- reset_odom
- gripper: side left|right|both, open 0..1 (1=open)
- arm_preset: side left|right|both, preset home|pick|place
- arm_joints: side, joints [6 floats]
If the user wants a visual skill you cannot do (find object, open door, tidy, camera, search),
return {"error":"needs camera and vla_act; not wired"}.
Return ONLY JSON, for example:
{"steps":[{"action":"move","vx":-0.15,"vy":0,"wz":0,"duration":0.25},{"action":"stop"}]}
"""


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def _extract_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise json.JSONDecodeError("empty LLM content", text, 0)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def _normalize_step(step: Any) -> dict[str, Any]:
    if not isinstance(step, dict):
        raise ValueError(f"LLM returned invalid step: {step!r}")
    if step.get("action") in ALLOWED_ACTIONS:
        return step
    for act in ALLOWED_ACTIONS:
        if act not in step:
            continue
        val = step.pop(act)
        step["action"] = act
        if act == "move" and "vx" not in step:
            try:
                step["vx"] = float(val)
            except (TypeError, ValueError):
                pass
        return step
    raise ValueError(f"LLM returned invalid step: {step!r}")


def _apply_language_guards(steps: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    back = bool(re.search(r"(往後|向後|後退|倒車|backward|reverse|\bback\b)", text, re.I))
    fwd = bool(re.search(r"(往前|向前|前進|forward)", text, re.I))
    nudge = bool(re.search(r"(一點點|一點|一下|稍微)", text))
    no_turn = bool(re.search(r"(別轉|不要轉|但別轉|不要轉彎)", text))
    out: list[dict[str, Any]] = []
    for step in steps:
        if step.get("action") == "motor" and step.get("enabled") is True:
            continue
        if step.get("action") != "move":
            out.append(step)
            continue
        vx = float(step.get("vx", 0.0))
        vy = float(step.get("vy", 0.0))
        wz = float(step.get("wz", 0.0))
        if back and not fwd and vx > 0:
            vx = -abs(vx)
        if fwd and not back and vx < 0:
            vx = abs(vx)
        if no_turn:
            wz = 0.0
        if nudge:
            vx = max(-0.12, min(0.12, vx))
            vy = max(-0.12, min(0.12, vy))
            step["duration"] = max(0.2, min(0.3, float(step.get("duration", 0.25))))
        step["vx"], step["vy"], step["wz"] = vx, vy, wz
        out.append(step)
    return out or steps


def _validate(planned: dict[str, Any], text: str, source: str) -> dict[str, Any]:
    if planned.get("error"):
        raise ValueError(str(planned["error"]))
    if planned.get("action") == "error":
        raise ValueError(str(planned.get("message") or "needs camera and vla_act; not wired"))
    steps = planned.get("steps")
    if isinstance(planned.get("action"), str) and planned.get("action") != "error" and not steps:
        steps = [planned]
    if not isinstance(steps, list) or not steps:
        raise ValueError("LLM returned no steps")
    if steps[0].get("action") == "error":
        raise ValueError(str(steps[0].get("message") or "needs camera and vla_act; not wired"))
    planned["steps"] = [_normalize_step(step) for step in steps]
    planned["steps"] = _apply_language_guards(planned["steps"], text)
    for step in planned["steps"]:
        if step["action"] == "move":
            for k in ("vx", "vy", "wz"):
                step[k] = max(-0.5 if k != "wz" else -1.2, min(0.5 if k != "wz" else 1.2, float(step.get(k, 0))))
            step["duration"] = max(0.05, min(8.0, float(step.get("duration", 1.0))))
    planned["text"] = text
    planned["source"] = source
    return planned


def _deepseek_chat(text: str) -> dict[str, Any]:
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
    if not key:
        raise urllib.error.URLError("no DEEPSEEK_API_KEY")
    base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
    if base.endswith("/v1"):
        url = base + "/chat/completions"
    else:
        url = base + "/chat/completions"
    model = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 800,
        "thinking": {"type": "disabled"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        if exc.code == 400 and "thinking" in payload:
            payload.pop("thinking", None)
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = json.loads(resp.read().decode())
        else:
            raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail[:400]}") from exc
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    return _extract_json(content)


def _ollama_chat(text: str) -> dict[str, Any]:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    body = json.dumps(
        {
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        host + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode())
    content = payload.get("message", {}).get("content", "")
    return _extract_json(content)


def plan(text: str) -> dict[str, Any]:
    _load_dotenv()
    try:
        parsed = parse_command(text)
        parsed["source"] = "parser"
        return parsed
    except ValueError:
        pass

    last_err = "unrecognized command"
    if os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY"):
        try:
            return _validate(_deepseek_chat(text), text, "deepseek")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
            last_err = f"DeepSeek failed: {exc}"

    try:
        return _validate(_ollama_chat(text), text, "ollama")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        last_err = f"{last_err}; Ollama failed: {exc}"

    raise ValueError(
        f"{last_err}. Use phrases like '前進 1 秒 然後 關閉夾爪', "
        "start local Ollama (bash scripts/start_ollama.sh pull), "
        "or set DEEPSEEK_API_KEY in .env (cloud planner)."
    )

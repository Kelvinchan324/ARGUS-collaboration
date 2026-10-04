from __future__ import annotations

import json
import urllib.error
from unittest import mock

import planner


def test_known_phrase_skips_llm():
    out = planner.plan("前進 1 秒 然後 關閉夾爪")
    assert out["source"] == "parser"
    assert out["steps"][0]["action"] == "move"
    assert out["steps"][1]["action"] == "gripper"


def test_unknown_without_key_raises():
    with mock.patch.dict("os.environ", {"DEEPSEEK_API_KEY": "", "LLM_API_KEY": ""}, clear=False):
        with mock.patch.object(planner, "_ollama_chat", side_effect=urllib.error.URLError("down")):
            try:
                planner.plan("請用很慢的速度往前挪一點點再停下")
            except ValueError as exc:
                assert "unrecognized" in str(exc) or "Ollama" in str(exc) or "DEEPSEEK" in str(exc)
            else:
                raise AssertionError("expected ValueError")


def test_ollama_fallback():
    fake = {"steps": [{"action": "gripper", "side": "left", "open": 0.0}, {"action": "stop"}]}
    with mock.patch.dict("os.environ", {"DEEPSEEK_API_KEY": "", "LLM_API_KEY": ""}, clear=False):
        with mock.patch.object(planner, "_ollama_chat", return_value=fake):
            out = planner.plan("請用很慢的速度往前挪一點點再停下")
    assert out["source"] == "ollama"
    assert out["steps"][0]["side"] == "left"


def test_deepseek_fallback():
    fake = {"steps": [{"action": "gripper", "side": "left", "open": 0.0}, {"action": "stop"}]}
    with mock.patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test"}, clear=False):
        with mock.patch.object(planner, "_deepseek_chat", return_value=fake):
            out = planner.plan("請用很慢的速度往前挪一點點再停下")
    assert out["source"] == "deepseek"
    assert out["steps"][0]["side"] == "left"


def test_rejects_unknown_action():
    try:
        planner._validate({"steps": [{"action": "vla_act"}]}, "x", "deepseek")
    except ValueError:
        return
    raise AssertionError("expected invalid action")


def test_extract_fenced_json():
    raw = 'sure\n```json\n{"steps":[{"action":"stop"}]}\n```\n'
    assert planner._extract_json(raw)["steps"][0]["action"] == "stop"


def test_normalizes_move_key():
    out = planner._validate(
        {"steps": [{"move": 0.5, "vy": 0, "wz": 0, "duration": 2}]},
        "慢慢往前再停",
        "ollama",
    )
    assert out["steps"][0]["action"] == "move"
    assert out["steps"][0]["vx"] == 0.5
    assert out["steps"][0]["duration"] == 2.0


def test_error_action_from_llm():
    try:
        planner._validate(
            {"action": "error", "message": "needs camera and vla_act; not wired"},
            "開門",
            "ollama",
        )
    except ValueError as exc:
        assert "camera" in str(exc)
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(name, "ok")
    print("planner tests ok")

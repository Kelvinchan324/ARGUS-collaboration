# Phase 2 first half — language agent

This folder is the ABot-Claw *slot*: an agent that may only call `robot_bridge`.

```
you --language--> agent/loop.py --HTTP--> robot_bridge --serial--> hardware
```

## Run (on Thor)

```bash
cd /path/to/ARGUS-collaboration/connected-robots/robot-ar
.venv/bin/python agent/loop.py --plan-only "前進 1 秒"
.venv/bin/python agent/loop.py "前進 1 秒 然後 關閉夾爪"
```

`--plan-only` stops after JSON. Without it, steps POST to `:8080` (mock chassis if no USB). The teleop command box uses the same `plan()` via `POST /command`; unplugged chassis → `plan_only`.

## Local planner (Ollama 7B)

Known phrases (`前進 1 秒`, `關閉夾爪`, …) never call a model.

On Thor (JetPack 7 NVIDIA container, loopback only):

```bash
bash scripts/start_ollama.sh pull    # ~5GB qwen2.5:7b, once
.venv/bin/python agent/loop.py --plan-only "慢慢往前再停"
```

Copy `.env.example` to `.env` if needed:

```
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

## Cloud planner (DeepSeek, optional)

If `DEEPSEEK_API_KEY` is set it is tried before Ollama. Key from [DeepSeek API](https://api-docs.deepseek.com/):

```
DEEPSEEK_API_KEY=sk-...
LLM_MODEL=deepseek-v4-flash
```

Free-form drive/gripper/stop sentences compile to JSON. Visual skills (open door, tidy) are refused until `vla_act` is wired. No camera images are sent.

## Tests

```bash
bash scripts/run_tests.sh
```

## OpenClaw

```bash
bash scripts/install_openclaw_skill.sh   # copies skill files
bash scripts/install_openclaw.sh         # CLI + skill; gateway optional
```

The gateway is optional. `loop.py` is enough. If you do run OpenClaw, keep it on loopback and point it at DeepSeek during `openclaw onboard`. Skill path: `~/.openclaw/workspace/skills/robot-bridge/`.

---
name: robot-bridge
description: Drive the Thor bimanual wheelbase only via HTTP robot_bridge on :8080. Never open serial ports.
---

# Robot bridge

You are the high-level agent for one robot: four-wheel-steer chassis + dual SO-ARM arms.

Read `{baseDir}/ROBOT.md` and `{baseDir}/MISSION.md`.

## Hard rules

- Control the robot ONLY through HTTP to `http://127.0.0.1:8080`.
- Never open `/dev/ttyUSB*`, never SSH to motors, never call LeRobot directly.
- If `/health` or `/state` says chassis `"mock": true`, the body will not move. Do not claim real-world success.
- GET `/capabilities` before any visual or contact skill. If `vla_act.wired` is false, refuse open-door / pick / search.
- POST `/stop` is e-stop: chassis disable + arm bus disconnect.

## Prefer this helper

```bash
cd /path/to/ARGUS-collaboration/connected-robots/robot-ar && .venv/bin/python agent/loop.py "把夾爪合上"
cd /path/to/ARGUS-collaboration/connected-robots/robot-ar && .venv/bin/python agent/loop.py --plan-only "左轉 2 秒"
```

`loop.py` uses the phrase parser first, then DeepSeek (`DEEPSEEK_API_KEY` in
the Robot-AR folder's untracked `.env`), then Ollama. The teleop page uses the
same stack via `POST /command` (`plan_only: true` when the chassis is unplugged).

## Direct HTTP

```bash
curl -s http://127.0.0.1:8080/capabilities
curl -s -X POST http://127.0.0.1:8080/stop
curl -s -X POST http://127.0.0.1:8080/command \
  -H 'Content-Type: application/json' \
  -d '{"text":"前進 1 秒 然後 關閉夾爪"}'
```

Do not POST `/vla_act` until `/capabilities` shows it wired. Do not invent open-door / tidy sequences.

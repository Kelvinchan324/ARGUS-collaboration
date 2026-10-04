# Architecture

```
language / web  →  agent (loop.py / OpenClaw skill)
                 →  robot_bridge HTTP :8080
                      ├─ chassis serial (STM32)
                      ├─ /arm/left|right  → DualArmDriver → LeRobot SO-101 if port exists
                      ├─ /camera/latest   (slot)
                      └─ /vla_act         (slot, 503 until wired)
```

Agents must not open `/dev/tty*`. Hardware is only behind the bridge.

## Layout on Thor

| Path | What |
|------|------|
| `config/ports.yaml` | Left/right Feetech ports |
| `robot_bridge/` | HTTP + mock/real drivers |
| `agent/` | OpenClaw-compatible skill |
| `scripts/calibrate_arms.sh` | LeRobot calibration (person on site) |
| `.venv` | bridge |
| `.venv-lerobot` | LeRobot (optional, heavy) |

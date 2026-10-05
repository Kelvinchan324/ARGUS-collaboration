# Robot-AR

> [Open the ARGUS website](https://kelvinchan324.github.io/ARGUS-collaboration/)

<p align="center">
  <img src="robot-ar.png" alt="ARGUS Robot 2 — Robot-AR prototype" width="520">
</p>

> Robot-AR prototype photographed for ARGUS Report Back Session 1. Robot-AR is
> the team's large four-arm mobile robot; it is separate from Aloha Mini.

Robot-AR is the large ARGUS mobile-manipulation research platform. The latest
student stack targets a four-wheel-steer chassis, four configured
SO-ARM100/101 follower buses, two paired linear-lift axes, Robonine parallel
grippers, USB camera capture and a Mini PC controller. This folder contains the
student's ARGUS-specific bridge, web teleoperation UI, command planner,
configuration, tests and integration documentation.

## Ownership and import record

- Student maintainer: [Lycheee-Lychee](https://github.com/Lycheee-Lychee)
- Upstream repository: [Lycheee-Lychee/ARGUS](https://github.com/Lycheee-Lychee/ARGUS)
- Imported upstream commit: `9c3640c8a4eccf60600850a46a4ae24e62b2fc6b`
- Import date: 2026-10-05
- Current status: the bridge now includes four-arm, lift and camera support.
  Hardware-specific behavior still requires supervised on-robot validation in
  this integration repository.

The upstream `vendor/` and duplicated `ros2_ws/` source trees were deliberately
not copied. Complete firmware and external ROS2 packages should remain in the
upstream repository until ownership, licensing, provenance and the exact
required files are confirmed. Keep this folder focused on ARGUS-owned
integration code.

## Current software

| Path | Role |
| --- | --- |
| `robot_bridge/` | FastAPI bridge, web teleoperation UI, chassis, arm, lift and camera adapters |
| `agent/` | Rule-based and optional local/cloud language planner |
| `config/ports.yaml` | Four-arm and paired-lift serial-port mapping from the imported hardware stack |
| `docs/` | Architecture, emergency-stop and task-readiness notes |
| `scripts/` | Dependency setup, bring-up, calibration and test helpers |
| `sim/` | Placeholder for optional SO-ARM simulation work |

The bridge keeps hardware access behind one HTTP boundary. Agents must not
open serial devices or call the arm driver directly.

## Quick start on the robot computer

From this folder:

```bash
bash scripts/install_deps.sh
bash scripts/run_tests.sh
bash scripts/bringup.sh
```

The safe default binds the bridge to `127.0.0.1:8080`. For remote development,
use an SSH tunnel. Do not expose the unauthenticated bridge to the public
internet or a shared campus network. An explicitly isolated laboratory network
may use `HOST=0.0.0.0 bash scripts/bringup.sh` only after a physical emergency
stop, firewall rules, speed limits, command timeout and a test observer are in
place.

## Implemented and planned capabilities

- Implemented in software: mock chassis, bilingual command parser, web controls,
  `/stop`, command timeout, four-arm Feetech bus support, paired linear-lift
  nudges, USB camera frame capture and planner/command tests.
- Hardware dependent: chassis serial control, exact arm/lift port mapping,
  gripper ranges, lift directions and camera-device compatibility.
- Not yet wired: `vla_act` visual manipulation.
- Refused until wired and validated: open-door, pick-and-place and search tasks.

## Safety

`POST /stop` cancels the current task, stops and disables the chassis, and
removes torque from the connected arm and lift buses. It is not a substitute
for a reachable physical power cut. Complete the parent repository's pre-power
and pre-motion checklist before enabling hardware.

## Configuration and secrets

Copy `.env.example` to an untracked `.env` only on the robot computer. Never
commit API keys, Wi-Fi credentials, private IP addresses, calibration data tied
to a specific unsafe setup, or customer/network information.

## Licensing

No project-wide ARGUS license has been selected. The student retains rights to
their original work unless separately agreed. Every external dependency and
hardware project keeps its own license. Confirm licensing before redistributing
or importing any omitted vendor source.

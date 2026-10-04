# Cockpit

> [Open the ARGUS website](https://kelvinchan324.github.io/ARGUS-collaboration/) · [English](https://kelvinchan324.github.io/ARGUS-collaboration/en/)

This is the shared ARGUS application. Cockpit code should handle the operator
controls, user interface, robot selection, video/telemetry display, and the
common connection layer used to reach the connected robots.

Put code here when it is useful to more than one robot. Do not place a robot's
vendor SDK or hardware-specific commands here; keep those in that robot's folder
under `connected-robots/`.

## Fleet control center

The shared [web cockpit](web/) provides one dashboard for Robot-AR, Aloha Mini,
Bimanual Bunker Mini, Unitree Go2, Pupper V3 and Open Duck Mini. Launch it from the
ARGUS website's **Open control center** button. The public page starts in a fully
local demonstration mode; it does not connect to hardware automatically.

Features include per-robot telemetry, connection freshness, reference/camera-status
view, Bunker inspection playback, base controls, demo arm/gripper/lift/posture
controls, odometry, speed history, command acknowledgements, per-robot and fleet
software stops, and JSON telemetry export. Missing sensor values remain unknown.
There is no live camera stream in the current Robot-AR backend.

### Run and connect

Build and serve the website using the root README instructions, then open
`http://127.0.0.1:8000/control/`. Alternatively, run the existing Robot-AR bridge
in mock mode and visit `http://127.0.0.1:8080/cockpit/`:

```bash
cd connected-robots/robot-ar/robot_bridge
python server.py --mock
```

In **Connection settings**, choose Robot-AR and enter the bridge address. The
local `/cockpit/` page suggests its own origin. Connecting probes telemetry only;
**Enable control** is a separate deliberate action. Hold a direction to drive,
release to send zero velocity, or use Stop to stop and disable the base.

Connected Robot-AR supports chassis telemetry and existing base commands. Its
arms are currently forced mock in the server, and camera capture is unwired;
these are not exposed as live controls. The other five robots have demo controls
and an [ARGUS v1 adapter boundary](ADAPTER_PROTOCOL.md), but their vendor bridges
are not implemented in this repository.

Public HTTPS Pages can reach only appropriately configured HTTPS bridges with
allowed browser origins. Prefer a trusted same-origin gateway for operation.
Connection URLs and optional bearer tokens stay in memory, are never committed,
are not persisted, and are excluded from telemetry exports. The existing
Robot-AR bridge has no authentication and binds to loopback by default; do not
expose it directly to the public Internet.

### Control behavior and limitations

- Base requests are capped at 0.25 m/s and 0.6 rad/s in the web client. The
  existing Robot-AR driver clamps commands again and has a 500 ms watchdog.
- Direction buttons repeat commands only while held. Pointer release/cancel
  sends zero velocity. Switching robots, hiding/blurring the page, changing
  modes or losing fresh telemetry locks controls and requests a stop.
- Device telemetry older than 2.5 seconds cannot authorize motion. A connected
  bridge's simulation flag stays visible, and missing battery percentage or
  temperature is never inferred from voltage or other values.
- Stops record actual HTTP acknowledgements or failures. Acknowledgement is
  not proof of mechanical stopping. Closing a tab or losing the network can
  prevent a stop request; a robot-side watchdog and physical stop are essential.
- This prototype has no multi-operator control lease. Use one operator on a
  trusted network. Hardware stop validation and operator arbitration remain
  required before operational deployment.
- The demo map uses fabricated floor positions. Connected mode shows only the
  selected robot's local odometry, with no assumption of a shared map frame.
- Arm/lift/posture controls are demo-only; their ranges are illustrative.

### Validation

```bash
node --test cockpit/tests/core.test.mjs
```

For browser regression tests, build the website into `build/pages-control`,
install Playwright and its Chromium browser in your development environment,
then run `node cockpit/tests/browser.cjs`. Tests use an isolated mock HTTP bridge
and never connect to hardware. See the test script for environment overrides.

## Source layout

```text
cockpit/
├── web/          Static dashboard, shared state model and HTTP adaptor boundary
├── tests/        Protocol, command-ordering and browser regression tests
├── ADAPTER_PROTOCOL.md  Integration contract for future robot bridges
└── README.md     Setup and run instructions
```

## Current public files

- [`cad/`](cad/) contains the current SolidWorks frame and seat-dimension part
  references. They are research files, not certified manufacturing drawings.
- `web/` contains the shared fleet dashboard. It is copied to `/control/` by the
  Pages build and served directly at `/cockpit/` by the Robot-AR bridge.

# ARGUS cockpit adaptor boundary

Robot-AR uses its existing `/state`, `/motor`, `/cmd_vel`, and `/stop` endpoints.
No vendor-specific calls belong in the shared cockpit. Other robot connections
must supply the following interface in their own `connected-robots/` folder.
This document is a contract, not a claim that those hardware adaptors exist.

## Telemetry

`GET /argus/v1/state` returns JSON. The `robot_id` must exactly match one of the
repository folder names. `sample_time_ms` is the time of the **device sample**
as UTC Unix milliseconds, not the time an old cache is served. Synchronize the
bridge clock; the client rejects timestamps more than one second in the future.

```json
{
  "protocol": "argus.v1",
  "robot_id": "bimanual-bunker-mini",
  "mode": "simulation",
  "sample_time_ms": 1791072000000,
  "connected": true,
  "motor_enabled": false,
  "watchdog_ms": 500,
  "capabilities": {"drive": true},
  "telemetry": {
    "battery": 82,
    "voltage": 24.1,
    "vx": 0.0,
    "wz": 0.0,
    "x": 0.0,
    "y": 0.0,
    "yaw": 0.0,
    "temp": 38.0
  },
  "task": "Standby"
}
```

Use `mode: "hardware"` only for actual hardware feedback. Omit unknown sensors
or return `null`. Battery is percentage, voltage volts, speeds m/s and rad/s,
positions metres in this robot's local frame, yaw radians, temperature Celsius.
The current dashboard accepts base or leader-backed arm control only when the
reported watchdog is positive and at most 500 ms. `capabilities.arms: true`
means a validated robot-side arm path is available; for SO-101 it is true only
while both physical leader streams and both follower arms are fresh and
connected. This declaration must correspond to a real robot-side timeout; it
is not implemented by the browser.

An arm-capable adaptor may report read-only feedback using
`telemetry.arms.left` and `telemetry.arms.right`, each with a `joints` array and
optional `gripper`. Unknown values should be `null`. The browser does not send
generic joint poses. For SO-101, physical leaders provide the action stream;
`enable` gates that stream and `stop` disables it and requests a hold at the
measured pose.

## Commands

`POST /argus/v1/command` accepts one of:

```json
{"action":"enable","enabled":true}
{"action":"drive","vx":0.15,"wz":0.0}
{"action":"stop"}
```

Respond `{"ok":true}` only after accepting a command. Reject unsupported
commands with an appropriate HTTP error or `{"ok":false}`. Stop must cancel
motion and disable the base, remain available when telemetry is stale, and not
require motion to be enabled first. Zero-velocity drive halts motion without
disabling the base. The server must enforce robot-specific limits, timeout,
authentication and single-operator ownership; frontend checks are insufficient.
Responses should be prompt enough for a 150 ms command heartbeat.

The client serializes commands and invalidates queued motion before a stop.
Network timeouts and requests already processing on a server cannot be revoked
by the client. Every actuator adaptor must gate motion on explicit enable,
expire stale inputs on the robot, and implement a stop that remains available
when telemetry is stale. SO-101 is leader-backed and does not accept browser
joint commands. Lift, posture, task execution and camera commands are not part
of this protocol.

## Hosting

Host the cockpit and adaptor on one trusted origin where possible. For remote
HTTPS access, provide authentication and allow only the specific cockpit origin
in CORS. Do not enable unrestricted CORS on an unauthenticated actuator bridge.
An optional session bearer token is sent in the Authorization header.

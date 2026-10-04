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
The current dashboard accepts base motion only when the reported watchdog is
positive and at most 500 ms. This declaration must correspond to a real
robot-side timeout; it is not implemented by the browser.

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
by the client. Implement a watchdog and server-side sequence/lease handling
before deploying a hardware adaptor. Connected arm, lift, posture, task execution
and camera APIs are intentionally not enabled in this first version.

## Hosting

Host the cockpit and adaptor on one trusted origin where possible. For remote
HTTPS access, provide authentication and allow only the specific cockpit origin
in CORS. Do not enable unrestricted CORS on an unauthenticated actuator bridge.
An optional session bearer token is sent in the Authorization header.

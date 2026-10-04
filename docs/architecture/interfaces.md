# Interface Contract

The first shared contract should stay deliberately small. A robot adapter may
offer extra functions, but the cockpit should discover them through a capability
manifest rather than assume they exist.

## Common commands

| Command | Required behavior |
| --- | --- |
| `stop` | Stop new motion immediately and enter the safest available state. |
| `heartbeat` | Prove that the operator/control process is still alive. |
| `velocity` | Request bounded planar motion where supported. |
| `pose` | Request a named or bounded joint/body pose where supported. |
| `camera.select` | Select an available video stream. |

## Common telemetry

- connection state and last heartbeat
- operating mode and active command source
- battery state when available
- pose/odometry when available
- fault and warning events
- video stream descriptors, not embedded recordings

## Required command envelope

Every command should carry `schema_version`, `robot_id`, `command_id`,
`issued_at`, `expires_at`, and a typed payload. A later implementation change
should add a JSON Schema under `interfaces/schema/` before adapters depend on it.

## Failure policy

Unknown, expired, out-of-range, or unauthorized commands must be rejected. Loss
of heartbeat must transition to the robot-specific safe state documented on its
robot page.

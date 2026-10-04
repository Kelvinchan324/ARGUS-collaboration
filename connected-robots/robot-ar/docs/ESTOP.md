# E-stop and access

## What `/stop` does

1. Cancels the task runner
2. Chassis velocity = 0, motors disabled
3. Arm LeRobot buses disconnect (`disable_torque_on_disconnect`)
4. cmd_vel timeout 500 ms if the web client dies

Use Space or the red STOP button in the teleoperation UI.

Physical power cut is still required if software hangs.

## Who can call the robot

The bridge now defaults to `127.0.0.1:8080` and has **no password**. Use an SSH
tunnel for remote development so the bridge remains on loopback.

Do not port-forward 8080 to the internet or expose it to a shared campus
network. Binding to `0.0.0.0` is an explicit laboratory-only override and
requires an isolated network, firewall rules, a reachable physical power cut,
speed limits and an on-site observer.

Optional later: `ROBOT_TOKEN` header. Not enabled yet so you cannot lock yourself out remotely.

## Agent rules

- If `mock: true` or inventory `disconnected`, do not claim a real-world success.
- Refuse door / pick / SAR until `vla_act.wired`.

# Aloha Mini — shared SO-101 runtime

The owner reports the direct SO-101/Aloha test setup worked. Its runtime is now
promoted to [SO-101](../so101/README.md), with shared camera UI in
[`cockpit/camera-ui`](../../cockpit/camera-ui/). Other devices and the bridge
control route still require supervised calibration/stop checks.

## Keep the working direct setup

On the Aloha Mini, stop the running service, update the existing checkout, then:

```bash
bash connected-robots/so101/setup-so101-device.sh
bash connected-robots/so101/start-so101-control.sh --check-config
```

Keep `SO101_ROLE=follower`. Existing `test-code/so101-config.env` is reused
when no new local config exists. The installed desktop shortcut uses the new
runtime. Repeat installation on the leader station, retaining its leader role.
Camera IDs, serial ports and calibration files are not rewritten.

`so101_bimanual_host.py` now delegates to the shared direct receiver instead
of maintaining a separate single-camera implementation. Its defaults use
`follower_left` / `follower_right`, matching the working test setup.
If you previously used the older Aloha-only `follower_l` / `follower_r`
calibration, stop and verify the matching configuration before connecting;
do not rename or overwrite calibration files to bypass a prompt.
Prefer the configured desktop launcher over the old manual host wrapper,
which does not read the shared config automatically.

## Main cockpit enable/stop route

Stop the direct leader and receiver before using the ARGUS bridge:

```bash
# Loopback-only example; configure a private interface and token for a LAN.
python connected-robots/aloha-mini/follower_bridge.py
```

This reuses the SO-101 bridge with `robot_id=aloha-mini`. Use the shared
`connected-robots/so101/leader_teleop.py` with the same token and verified
ports, following [the bridge guide](../so101/README.md).
Select **Aloha Mini** in the main cockpit and connect to this bridge, then
enable explicitly. Only arm leader-following is supported; no mobile-base,
lift, autonomous task or browser-generated arm pose is added.

Run the shared camera server separately in bridge mode. In the main cockpit's
Live Control view, set **Camera dashboard address** to that service.
Camera availability is not evidence that motors are safe or enabled.

Do not mix the raw direct protocol and token-wrapped bridge protocol.
Direct mode still has no leader-disconnect watchdog. Bridge software stop holds
position, does not cut motor power, and does not replace a physical emergency stop.

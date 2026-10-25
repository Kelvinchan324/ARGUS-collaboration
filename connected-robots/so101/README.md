# SO-101 bimanual teleoperation

## Promoted working setup (SO-101 / Aloha Mini)

The owner reports the test-code setup worked on their station. Its direct
leader/receiver, camera discovery, multi-camera server and command instruments
are now maintained here; shared dashboard assets live in `cockpit/camera-ui/`.
This report is not a certification of other hardware or the ARGUS bridge mode.

### Update the working installation

Stop both existing services first. On **both computers**, from the existing repo:

```bash
git status --short
git pull --ff-only
bash connected-robots/so101/setup-so101-device.sh
bash connected-robots/so101/start-so101-control.sh --check-config
```

The installer preserves an existing `test-code/so101-config.env` if no new
local config exists. The launcher uses that same fallback. If both exist, the
new `connected-robots/so101/so101-config.env` wins; use `SO101_CONFIG_FILE`
to select explicitly. It never copies over or rewrites your settings.
The installed desktop shortcut now starts this directory's launcher.
The original test-code scripts remain unchanged for comparison/rollback.

Keep calibration IDs: left leader `lead_r`, right leader `lead_l`,
left follower `follower_left`, right follower `follower_right`.
Do not delete calibration or accept unexpected recalibration prompts.
The bridge leader now defaults to these working IDs; previous bridge users
can retain their old mapping with `--left-id lead_l --right-id lead_r`.

### Choose ONE control route

- **Direct (working setup):** use the updated desktop shortcut on each device.
  Raw leader JSON drives the receiver. The camera dashboard shows forwarded
  command targets, not measured joints. This route has no disconnect watchdog.
  The fleet cockpit's Stop does NOT control this receiver.
- **ARGUS bridge:** stop the direct receiver and leader first, then use
  `follower_bridge.py` and `leader_teleop.py` below. Packets are token-wrapped;
  the cockpit must explicitly enable, renew the lease and stop the bridge.
  Never run both routes on the same serial ports/ZeroMQ ports.

### Cameras in the main cockpit

The server uses the same Top/Front switch, left/right gripper views, fullscreen,
independent reconnect and stale-image hiding as the successful test UI.
Launch camera-only mode without connecting motors:

```bash
python connected-robots/so101/camera_stream.py --host 0.0.0.0 --port 8000 --camera 0 2 4 6
```

Replace the example camera sources with your verified IDs or stable paths;
omit the fourth source for a three-camera setup. The direct receiver already
starts this server: do not start a second process on the same cameras.
On a trusted LAN, open the main cockpit locally in Live mode, select SO-101
or Aloha Mini, and enter the camera service URL in **Camera dashboard address**.
The view is independent of bridge connectivity and cannot enable motion.
HTTPS-hosted cockpit pages require an HTTPS camera proxy; do not expose the
unauthenticated camera server to the public Internet.
Interacting with the embedded viewer may blur the cockpit and lock bridge
motion; re-enable deliberately after returning to controls.
Without a direct receiver telemetry file, camera instruments remain unavailable.

### Hardware-independent checks

```bash
python -m pip install opencv-python-headless
python -m unittest discover -s connected-robots/so101/tests -v
```


This folder contains ARGUS-owned integration scripts for the SO-101 leader /
follower setup. It does not copy LeRobot. Install a calibrated LeRobot checkout
or release separately; the scripts use LeRobot's SO-101 driver APIs.

## Layout and control flow

- `leader_teleop.py` reads the two physical leader arms and streams their joint
  actions to the follower bridge.
- `follower_bridge.py` owns both follower arms and exposes the ARGUS v1 state,
  enable and stop endpoints for the cockpit.
- `camera_stream.py` serves USB camera MJPEG streams separately from the
  actuator bridge.

The cockpit connection only enables or stops leader-following. Joint movement
comes from the physical leader arms; the browser does not generate poses. The
bridge starts locked, accepts actions only after cockpit enable, and locks and
holds the current follower positions if either leader stream or the cockpit's
450 ms enable lease expires.
Enable and stop acknowledgements are software acknowledgements, not a physical
emergency stop.

## Install

Use the same Python environment as the tested LeRobot installation. From this
repository root, install the hardware and ZeroMQ dependencies in that
environment:

```bash
python -m pip install -e '.[feetech]' pyzmq
```

If the existing LeRobot checkout is already installed in editable mode, only
install `pyzmq` there. The camera server uses the project's
`opencv-python-headless` dependency.

## Start the follower bridge

Run this on the computer connected to both follower arms. Confirm each
`--left-port` / `--right-port` mapping and complete LeRobot calibration before
operating. The default HTTP listener is loopback-only and the default ZeroMQ
listeners are also loopback-only:

```bash
python connected-robots/so101/follower_bridge.py \
  --left-port /dev/ttyACM0 \
  --right-port /dev/ttyACM1
```

For a leader computer on another host, use a trusted isolated network, set a
strong `ARGUS_SO101_TOKEN` in both processes, and explicitly bind the bridge
listeners to the follower computer's private interface. For example:

```bash
export ARGUS_SO101_TOKEN='choose-a-long-random-token'
python connected-robots/so101/follower_bridge.py \
  --host 0.0.0.0 --zmq-host 0.0.0.0 \
  --cors-origin http://127.0.0.1:8000 \
  --left-port /dev/ttyACM0 --right-port /dev/ttyACM1
```

Do not expose the unauthenticated ZeroMQ stream or HTTP bridge to the public
Internet. The ZeroMQ token is plaintext and is not encryption; only use it on a
trusted private network. The HTTP token is sent as a bearer token. The bridge
itself is HTTP-only: use it with a local HTTP cockpit, or put it behind a TLS
reverse proxy for an HTTPS-hosted cockpit. The CORS origin must exactly match
the origin serving the cockpit.

## Start the leaders and connect the cockpit

On the computer connected to the two physical leader arms:

```bash
export ARGUS_SO101_TOKEN='the-same-token'
python connected-robots/so101/leader_teleop.py \
  --follower-host <follower-host> \
  --left-port /dev/ttyACM1 \
  --right-port /dev/ttyACM0
```

The leader port mapping above matches the previous desktop controller; check
the labels and device paths on the actual hardware. Keep the leader process
running. In the cockpit, select **SO-101 Bimanual**, switch to connected mode,
connect to the follower bridge URL, and explicitly enable control. The bridge
requires fresh action packets from both leaders before accepting enable.
Selecting another robot, leaving Control, losing fresh telemetry, or pressing
Stop disables leader-following.

To view cameras, run `camera_stream.py` on the computer with the USB cameras,
then open its printed URL. It binds to loopback by default; only bind it to a
trusted private interface when remote viewing is needed. The unauthenticated
stream is a separate read-only HTTP service, not the cockpit's ARGUS telemetry
bridge, and must not be exposed to the public Internet.

The optional `scripts/start-so101-control.sh` wrapper can be used as a desktop
shortcut target. For example, set its `Exec` entry to the installed absolute
path followed by `--camera-url http://<camera-host>:8080 --follower-host
<follower-host>`. The camera stream must already be running.

## Safety and verification

- Set up and validate the physical emergency stop before any powered test.
- Start with an unloaded, clear work area and a person beside the physical
  stop. Test one arm at a time before enabling both.
- Follower targets are limited by LeRobot's `max_relative_target` setting
  (default 2 degrees per update). Verify calibration, limits, direction and
  stop behavior on the actual hardware; software limits are not a substitute
  for mechanical limits.
- The bridge holds the last measured pose when stopped. It does not cut motor
  power and does not replace a physical emergency stop.
- The HTTP bridge reports arm joint samples only. It does not claim battery,
  base, camera, or physical-stop telemetry.
- Hardware behavior has not been validated by the repository tests. Run
  `python -m unittest discover -s connected-robots/so101/tests` for the
  hardware-independent protocol tests.

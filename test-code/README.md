# SO-101 desktop shortcut test code

This folder packages the scripts used by the existing **SO-101 Control and
Camera** desktop shortcut:

1. Start the physical leader-arm teleoperation program in a terminal.
2. Open the follower robot's camera page in the browser.

The leader program sends joint actions over ZeroMQ to the follower receiver.
The receiver and USB camera stream must already be running on the follower
computer. This is the existing direct SO-101 test setup, not the ARGUS web
cockpit or the newer ARGUS v1 bridge in `connected-robots/so101/`.

## Files

- `SO-101-Control-and-Camera.desktop` — shortcut to copy to the leader
  computer's Desktop.
- `start-so101-control.sh` — starts teleoperation in `lxterminal` and opens the
  camera page, matching the current shortcut behavior.
- `so100_bimanual_leader.py` — reads both leader arms and sends their actions.
- `so101_bimanual_receiver.py` — receives actions and controls both follower
  arms. Run this on the follower computer.
- `so101_camera_stream.py` — serves USB camera streams. Run this on the
  follower computer.

LeRobot itself is not copied into this folder. Install/use a compatible
LeRobot environment separately on both computers, along with ZeroMQ and the
camera dependencies where needed.

## Install the shortcut on the leader computer

Clone the repository to `~/ARGUS-collaboration` on the computer connected to
the two physical leader arms. Copy and enable the shortcut:

```bash
cp ~/ARGUS-collaboration/test-code/SO-101-Control-and-Camera.desktop ~/Desktop/
chmod +x ~/Desktop/SO-101-Control-and-Camera.desktop
```

If you clone the repository to another location, edit the `Exec` path in the
desktop file to point to `test-code/start-so101-control.sh`. If the desktop
environment asks whether to trust the shortcut, allow launching.

Configure the follower's host name or IP address and the LeRobot checkout on
the leader computer in `~/.config/argus-so101-control.env`:

```bash
mkdir -p ~/.config
cat > ~/.config/argus-so101-control.env <<'EOF'
SO101_FOLLOWER_HOST=replace-with-follower-hostname-or-ip
LEROBOT_ROOT="$HOME/lerobot"
EOF
```

Set `LEROBOT_ROOT` to the LeRobot checkout that contains the Python
environment. The launcher looks for `venv/bin/python` and then
`.venv/bin/python`, or you can set `LEROBOT_PYTHON` to the exact interpreter.
The leader serial ports default to `/dev/ttyACM1` and `/dev/ttyACM0`, matching
the current setup.

Clicking the shortcut opens the camera URL
`http://<SO101_FOLLOWER_HOST>:8000/` and starts the leader teleoperation
terminal. You can override that URL using `SO101_CAMERA_URL` in the same
configuration file.

## Start the follower services on the robot computer

On the computer connected to both follower arms and USB cameras, clone the
repository and use its compatible LeRobot Python environment. Start the
receiver:

```bash
python ~/ARGUS-collaboration/test-code/so101_bimanual_receiver.py \
  --left-port /dev/ttyACM0 \
  --right-port /dev/ttyACM1
```

In a second terminal, start its camera stream. For one camera:

```bash
python ~/ARGUS-collaboration/test-code/so101_camera_stream.py \
  --host 0.0.0.0 --port 8000 --camera 0
```

To stream multiple cameras, pass multiple indexes or device paths after
`--camera`. Check the actual camera indexes and serial-device mappings on each
computer before use.

## Safety and limitations

The leader and receiver scripts preserve the current direct-control protocol.
They do not authenticate ZeroMQ clients and the receiver accepts commands on
all network interfaces by default. Use only on a trusted, isolated LAN; do not
expose the control or camera ports to the public Internet. The receiver has no
leader-disconnect watchdog, so loss of the leader stream may leave the last
follower target active. Keep an accessible physical emergency stop nearby and
do not rely on browser closure or network loss to stop the arms. Verify
calibration, directions, joint limits, camera indexes and stop behavior on the
actual hardware before use.

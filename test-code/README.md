# SO-101 setup for leader station and Aloha Mini

This is the direct SO-101 leader/follower test setup. The same ARGUS repository
clone, nested LeRobot checkout and desktop shortcut can be used on both
computers. Each computer has its own local config:

- **Leader/control station**: connects to the physical leader arms, sends
  actions to Aloha Mini and opens Aloha Mini's camera page.
- **Aloha Mini**: receives leader actions, controls the follower arms and hosts
  the camera stream.

This direct setup is separate from the ARGUS web cockpit and the ARGUS v1
bridge in `connected-robots/so101/`. Here, “cockpit/control station” refers to
the computer with the physical leader arms, not the web cockpit page.

## 1. Clone both repositories

On each computer, clone ARGUS into your home directory, then clone LeRobot
inside the ARGUS folder:

```bash
git clone https://github.com/Kelvinchan324/ARGUS-collaboration.git \
  "$HOME/ARGUS-collaboration"
git clone https://github.com/huggingface/lerobot.git \
  "$HOME/ARGUS-collaboration/lerobot"
```

The nested `lerobot/` checkout is ignored by ARGUS Git, so LeRobot files will
not be included when you commit ARGUS changes.

## 2. Install LeRobot dependencies on both computers

Install `uv` if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the SO-101 Feetech and ZeroMQ dependencies from the nested
LeRobot checkout:

```bash
cd "$HOME/ARGUS-collaboration/lerobot"
uv python install 3.12
uv sync --locked --python 3.12 --extra feetech --extra pyzmq-dep
```

This installs the Python environment at
`~/ARGUS-collaboration/lerobot/.venv`. Open a new terminal if `uv` is not
found immediately after installing it. A Raspberry Pi's OS, architecture and
available memory can affect whether all LeRobot dependencies, especially
PyTorch, install successfully; consult the
[LeRobot installation guide](https://huggingface.co/docs/lerobot/installation)
if `uv sync` reports an unsupported wheel.

## 3. Install the same desktop shortcut on both computers

Run this on each computer:

```bash
bash "$HOME/ARGUS-collaboration/test-code/setup-so101-device.sh"
```

It copies the **SO-101 Control and Camera** shortcut to the Desktop and creates
`~/ARGUS-collaboration/test-code/so101-config.env` from the example if that
config does not already exist. The config file is local and ignored by Git.
You can run the setup command again later without overwriting your config.

## 4. Configure each computer

Edit the same file on each computer:

```bash
nano "$HOME/ARGUS-collaboration/test-code/so101-config.env"
```

### On the leader/control station

Set:

```ini
SO101_ROLE=leader
SO101_FOLLOWER_HOST=aloha-mini.local
SO101_LEFT_LEADER_PORT=/dev/ttyACM1
SO101_RIGHT_LEADER_PORT=/dev/ttyACM0
SO101_LEFT_ZMQ_PORT=5555
SO101_RIGHT_ZMQ_PORT=5556
SO101_CAMERA_PORT=8000
LEROBOT_ROOT=~/ARGUS-collaboration/lerobot
```

Replace `aloha-mini.local` with the actual Aloha Mini hostname or IP. Change
the leader serial ports to the ports discovered on this computer.

### On the Aloha Mini

Set:

```ini
SO101_ROLE=follower
SO101_FOLLOWER_HOST=
SO101_LEFT_FOLLOWER_PORT=/dev/ttyACM0
SO101_RIGHT_FOLLOWER_PORT=/dev/ttyACM1
SO101_LEFT_ZMQ_PORT=5555
SO101_RIGHT_ZMQ_PORT=5556
SO101_CAMERA_PORT=8000
SO101_CAMERA_INDEX=0
LEROBOT_ROOT=~/ARGUS-collaboration/lerobot
```

Set the follower serial ports and camera sources for the actual hardware (see
the three-camera setup below).
The left/right ZeroMQ ports and camera port must match the leader station's
config. Leave the follower host blank on the Aloha Mini itself.

Other supported settings include `SO101_FREQUENCY`, `SO101_CAMERA_INDEX`,
`SO101_LEFT_ZMQ_PORT`, `SO101_RIGHT_ZMQ_PORT`, `SO101_CAMERA_PORT`, and
`LEROBOT_PYTHON` (an explicit Python interpreter path).

### Discover and map the three cameras

Run this on the **follower Raspberry Pi**, with other camera apps and the
SO-101 service stopped. It only opens cameras; it does not import LeRobot,
connect to motors, or run calibration:

```bash
cd "$HOME/ARGUS-collaboration"
lerobot/.venv/bin/python test-code/discover-cameras.py --snapshots
```

The report lists usable camera IDs/device paths, aliases such as `/dev/video0`,
the actual frame size, and failed/busy/metadata nodes. Each candidate must
deliver three frames. Probes run in separate processes with an eight-second
timeout so a stuck device cannot block the whole search. On Linux it examines
existing `/dev/video*` nodes and groups their stable aliases; on other systems
it tries indices 0 through 9 (`--max-index` changes that range).

Snapshots are saved locally under ignored `test-code/camera-snapshots/`.
Open them on the Pi to identify top, left gripper and right views; discovery
cannot infer their physical positions. A USB camera can expose more than one
video node; metadata nodes are not usable streams. Do not assume IDs are 0, 1, 2.

To test specific devices or print a JSON report:

```bash
lerobot/.venv/bin/python test-code/discover-cameras.py --camera 0 2 4 --snapshots
lerobot/.venv/bin/python test-code/discover-cameras.py --json
```

Add these lines to the follower's **existing** `test-code/so101-config.env`,
replacing `0`, `2`, `4` with your verified sources:

```ini
SO101_CAMERA_TOP=0
SO101_CAMERA_LEFT=2
SO101_CAMERA_RIGHT=4
SO101_CAMERA_WIDTH=640
SO101_CAMERA_HEIGHT=480
SO101_CAMERA_FPS=15
SO101_CAMERA_QUALITY=75
```

Prefer the report's `/dev/v4l/by-id/...` paths when cameras have unique serial
numbers. For identical cameras without unique serials, use `/dev/v4l/by-path/...`
and keep each plugged into the same USB socket. These can be used directly as
the config values, without quotes. Numbered `/dev/video*` nodes can change after
reboot. Each view must resolve to a different capture device.

The launcher defaults to three views. If `SO101_CAMERA_TOP` is absent or empty,
the old `SO101_CAMERA_INDEX` becomes the top view; left/right default to 2/4.
If your old index is 2 or 4, explicitly map all three to avoid duplicate sources.
The existing local config is never rewritten by an update or setup rerun.
The leader only needs the follower host and matching camera port; the source
mapping belongs on the follower.

Check settings without connecting arms:

```bash
bash test-code/start-so101-control.sh --check-config
```

To check all three streams **without any arm connection**:

```bash
lerobot/.venv/bin/python test-code/so101_camera_stream.py --camera 0 2 4
```

Open `http://<follower-host>:8000/`. The ARGUS dashboard shows the left gripper
on the left, a larger top view in the center, and the right gripper on the right.
The **Top / Front** selector changes only the center view; both gripper views
stay visible. The compact instrument panels show arm command telemetry;
hover over a view for device details. Each view and the whole station
can expand to fullscreen. Missing cameras retry independently; offline or stale
images are hidden instead of being presented as live video. The displayed
connection status refers only to cameras, not motor/teleoperation health.
The page and logo are served locally, without a CDN or Internet dependency.

#### Add the fourth (front) camera

Discover its ID/path on the follower using `discover-cameras.py --snapshots`,
then add a single line to the existing local config, using the discovered
source (6 is only an example):

```ini
SO101_CAMERA_FRONT=6
```

Restart the follower service. The Front button becomes available. With this
setting empty or absent, existing three-camera setups continue to work and
Front is disabled. All four cameras capture on the Pi; the browser receives
only the selected center stream plus the two gripper streams. Switching views
does not restart either gripper stream or the arm receiver.

To test all four cameras without connecting arms, pass sources in the order
**top, left gripper, right gripper, front**:

```bash
lerobot/.venv/bin/python test-code/so101_camera_stream.py --camera 0 2 4 6
```

Four cameras require more USB bandwidth, power and JPEG encoding time than
three, even though only three views are displayed. Start with 640x480 at 10 FPS
if the additional camera causes dropouts.

#### Robot command instruments

The two side panels show the **last successfully forwarded leader command
targets** in native LeRobot units, the rate of received actions (Hz), elapsed
time since the latest action (ms), and a receive-rate trace. Values are not
measured joint positions, degree values, motor temperature, battery readings or
a safety/stop confirmation. The browser is read-only and adds no arm controls.

The receiver publishes snapshots in a separate thread to a private temporary
directory outside the repository. The camera server reads that file; it does
not query the motors or calibration. No extra motor reads or changes to the
command payloads are introduced. A temporary-file failure leaves the receiver
running with telemetry unavailable.

Arm values clear after one second without a fresh action; telemetry becomes
unavailable after two seconds without a receiver snapshot. The camera-only
command shows camera feeds with instrument values marked unavailable, rather
than synthetic robot values. These display timeouts do not stop the arms or
add a disconnect watchdog to the existing receiver.

The camera program also accepts one camera for diagnostics, e.g. `--camera 0`,
or custom labels, e.g. `--camera 0 2 4 --labels "Top" "Left gripper" "Right gripper"`.

Three USB cameras share bandwidth and power. The server requests MJPEG USB
transport, 640x480 at 15 FPS and JPEG quality 75; cameras may negotiate other
values. If capture is unreliable, try 10 FPS or 320x240, check cables/power, and
consider a powered USB hub. Discovery tests cameras individually; confirm all
three simultaneously with the camera-only command before starting teleoperation.
The dashboard reports actual frame dimensions; the discovery FPS is the driver's
reported rate, not a measured end-to-end latency or throughput guarantee.

### Updating existing devices and preserving calibration

Stop the running SO-101 service before updating. Once this change is merged
into `main`, update each machine from its existing checkout:

```bash
cd "$HOME/ARGUS-collaboration"
git status --short
git pull --ff-only
```

If Git reports local edits to tracked scripts or a diverged branch, resolve
those edits first; do not use a hard reset or `git clean` to force an update.
Do not replace your local config with the example. Add only the camera settings
above on the follower, then use the existing desktop shortcut.

This change does **not** update LeRobot, reinstall it, run calibration, change
arm IDs, or change leader/follower serial-port mappings. The existing IDs remain
`lead_r` (left leader), `lead_l` (right leader), `follower_left` and
`follower_right`; retaining these IDs preserves the calibration lookup behavior.
Do not rename them simply to match their spelling.

LeRobot normally stores calibration under
`~/.cache/huggingface/lerobot/calibration/`, outside this ARGUS checkout. The
[LeRobot cache settings](https://github.com/huggingface/lerobot/blob/main/src/lerobot/utils/constants.py)
`HF_LEROBOT_CALIBRATION`, `HF_LEROBOT_HOME`, or `HF_HOME` can move it. The nested `lerobot/` checkout, local
`test-code/so101-config.env`, and repo-local `calibration/`, `calibrations/` and
`.cache/huggingface/lerobot/` directories are ignored. No existing calibration
files are tracked or modified by this change. A normal pull of this change
leaves those local files intact. `.gitignore` does not protect files already
tracked in a custom branch; check any custom calibration location with
`git ls-files -- <your-calibration-path>` before updating it.

For an extra backup before updating, copy the actual calibration directory
outside the repository; for the default location:

```bash
if [ -d "$HOME/.cache/huggingface/lerobot/calibration" ]; then
  cp -a "$HOME/.cache/huggingface/lerobot/calibration" \
    "$HOME/lerobot-calibration-backup-$(date +%Y%m%d-%H%M%S)"
fi
```

There is no need to recalibrate arms that already work. This preserves the
existing LeRobot `connect()` behavior: if that installation cannot find a
matching calibration or detects a mismatch, investigate the ID/cache settings
before accepting any recalibration prompt.

## 5. Start the system

On the Aloha Mini, connect follower arms and cameras, then click the desktop
shortcut. It starts the follower receiver and camera stream in a terminal and
opens the local camera page. On the leader/control station, connect the leader
arms and click the same shortcut. It opens the Aloha Mini camera page and
starts teleoperation in a terminal.

Check that the selected serial ports and camera index match the device. Keep
the operating area clear and the physical emergency stop within reach.

## Network and safety

The ZeroMQ control and camera endpoints are unauthenticated and bind on network
interfaces so the two computers can connect. Use a trusted, isolated LAN only;
do not expose these services to the Internet. The receiver does not have a
leader-disconnect watchdog, so loss of the leader or network can leave the last
follower target active. Do not rely on closing a browser or losing network
connectivity to stop the arms. Validate calibration, movement direction and
the physical stop on the actual hardware before operation.

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

Set the follower serial ports and `SO101_CAMERA_INDEX` for the actual hardware.
The left/right ZeroMQ ports and camera port must match the leader station's
config. Leave the follower host blank on the Aloha Mini itself.

Other supported settings include `SO101_FREQUENCY`, `SO101_CAMERA_INDEX`,
`SO101_LEFT_ZMQ_PORT`, `SO101_RIGHT_ZMQ_PORT`, `SO101_CAMERA_PORT`, and
`LEROBOT_PYTHON` (an explicit Python interpreter path).

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

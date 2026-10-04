# SO-ARM simulator (laptop, optional)

> [Open the ARGUS website](https://kelvinchan324.github.io/ARGUS-collaboration/) · [English](https://kelvinchan324.github.io/ARGUS-collaboration/en/)

This is **arm-only**, not the wheeled base. Keep it off the Thor agent.

Isaac Sim is not set up here (large install). Use MuJoCo.

```bash
git clone --depth 1 https://github.com/roboninecom/SO-ARM100-101-Parallel-Gripper.git
cd SO-ARM100-101-Parallel-Gripper/simulation
# follow simulation/mujoco/README.md in that repo
pip install mujoco
```

Do not point `robot_bridge` at the simulator until a dedicated `sim` driver exists.
Real `/arm/left` talks to Feetech serial via LeRobot, or stays mock.

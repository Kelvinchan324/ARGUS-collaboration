# Pupper V3

<p align="center">
  <img src="https://pupper-v3-documentation.readthedocs.io/en/latest/_images/pupper_spin.gif" alt="Pupper V3 quadruped robot" width="650">
</p>

> Official Pupper V3 image and information from the
> [Pupper V3 documentation](https://pupper-v3-documentation.readthedocs.io/en/latest/).

- Student maintainer: To be assigned
- Status: Inventory needed
- Tested upstream version/commit: To be recorded
- Upstream code: [pupperv3-monorepo](https://github.com/Nate711/pupperv3-monorepo)

Add the Pupper V3-specific ARGUS connection and control code in this folder.
Keep the upstream Pupper software in its own repository; only add the team's
cockpit connection, configuration examples, setup notes, and tests here.

Pupper V3 uses ROS 2. Its documentation identifies the ROS 2 workspace as
`~/pupperv3-monorepo/ros2_ws` and describes adding a controller by publishing
`Twist` messages to `/cmd_vel`. Confirm these details on the team's robot and
record the exact tested commit before enabling physical motion.

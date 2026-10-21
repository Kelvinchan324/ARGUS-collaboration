import time
import unittest

from connected_robots_so101_import import load_bridge


bridge_module = load_bridge()


class FakeFollower:
    action_features = {
        "shoulder_pan.pos": float,
        "shoulder_lift.pos": float,
        "elbow_flex.pos": float,
        "wrist_flex.pos": float,
        "wrist_roll.pos": float,
        "gripper.pos": float,
    }
    is_connected = True

    def __init__(self):
        self.actions = []
        self.observation = {key: 0.0 for key in self.action_features}

    def send_action(self, action):
        self.actions.append(action)

    def get_observation(self):
        return self.observation


def packet(value=1.0, token="secret"):
    return {
        "token": token,
        "action": {key: value for key in FakeFollower.action_features},
    }


class SO101BridgeTests(unittest.TestCase):
    def setUp(self):
        self.left = FakeFollower()
        self.right = FakeFollower()
        self.bridge = bridge_module.SO101Bridge(self.left, self.right, token="secret")

    def provide_fresh_actions(self):
        self.bridge.accept_leader_action("left", packet())
        self.bridge.accept_leader_action("right", packet())

    def test_starts_locked_and_requires_both_fresh_leaders_to_enable(self):
        self.assertFalse(self.bridge.snapshot()["motor_enabled"])
        with self.assertRaisesRegex(ValueError, "both leader arms"):
            self.bridge.command({"action": "enable", "enabled": True})
        self.provide_fresh_actions()
        self.bridge.command({"action": "enable", "enabled": True})
        self.assertTrue(self.bridge.snapshot()["motor_enabled"])

    def test_leader_actions_only_reach_followers_after_enable(self):
        self.provide_fresh_actions()
        self.assertFalse(self.left.actions)
        self.bridge.command({"action": "enable", "enabled": True})
        action = packet(value=7)["action"]
        self.bridge.accept_leader_action("left", {"token": "secret", "action": action})
        self.assertEqual(self.left.actions[-1], action)
        self.assertFalse(self.right.actions)

    def test_stop_disables_and_holds_measured_joint_positions(self):
        self.provide_fresh_actions()
        self.bridge.refresh_observations()
        self.bridge.command({"action": "enable", "enabled": True})
        self.bridge.command({"action": "stop"})
        self.assertFalse(self.bridge.snapshot()["motor_enabled"])
        self.assertEqual(self.left.actions[-1], self.left.observation)
        self.assertEqual(self.right.actions[-1], self.right.observation)

    def test_stale_leader_stream_disables_control(self):
        self.provide_fresh_actions()
        self.bridge.command({"action": "enable", "enabled": True})
        self.bridge._action_times["left"] = time.monotonic() - 1
        self.bridge.expire_stale_actions()
        self.assertFalse(self.bridge.snapshot()["motor_enabled"])

    def test_expired_cockpit_lease_disables_control(self):
        self.provide_fresh_actions()
        self.bridge.command({"action": "enable", "enabled": True})
        self.bridge._enable_until = time.monotonic() - 1
        self.bridge.expire_stale_actions()
        self.assertFalse(self.bridge.snapshot()["motor_enabled"])

    def test_rejects_wrong_token_or_joint_shape(self):
        with self.assertRaises(PermissionError):
            self.bridge.accept_leader_action("left", packet(token="wrong"))
        with self.assertRaises(ValueError):
            self.bridge.accept_leader_action("left", {"token": "secret", "action": {"bad": 1}})

    def test_rejects_nonfinite_and_out_of_range_joint_targets(self):
        with self.assertRaises(ValueError):
            self.bridge.accept_leader_action("left", packet(value=float("nan")))
        with self.assertRaises(ValueError):
            self.bridge.accept_leader_action("left", packet(value=181))

    def test_only_enable_and_stop_commands_are_supported(self):
        with self.assertRaisesRegex(ValueError, "only enable and stop"):
            self.bridge.command({"action": "drive"})


if __name__ == "__main__":
    unittest.main()

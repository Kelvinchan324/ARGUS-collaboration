"""Command telemetry must remain read-only, bounded and clearly stale."""

import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from so101_telemetry import CommandTelemetry, read_telemetry


class TelemetryTests(unittest.TestCase):
    def snapshot(self, **changes):
        now = time.monotonic()
        data = {"updated_at": now, "frequency": 30, "arms": {
            side: {"received_at": now, "packets": 50, "rate_hz": 29.5,
                   "targets": {"shoulder_pan": 15.2, "gripper": 62.0}}
            for side in ("left", "right")}}
        data.update(changes)
        return data

    def read(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "commands.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return read_telemetry(path)

    def test_fresh_targets_rate_and_packet_age(self):
        result = self.read(self.snapshot())
        self.assertTrue(result["available"])
        arm = result["arms"]["left"]
        self.assertTrue(arm["fresh"])
        self.assertEqual(arm["targets"]["gripper"], 62)
        self.assertEqual(arm["rate_hz"], 29.5)
        self.assertGreaterEqual(arm["packet_age_ms"], 0)

    def test_fresh_snapshot_does_not_make_old_commands_live(self):
        data = self.snapshot()
        data["arms"]["left"]["received_at"] -= 1.5
        result = self.read(data)
        self.assertTrue(result["available"])
        self.assertFalse(result["arms"]["left"]["fresh"])
        self.assertEqual(result["arms"]["left"]["targets"], {})
        self.assertEqual(result["arms"]["left"]["rate_hz"], 0)
        self.assertTrue(result["arms"]["right"]["fresh"])

    def test_missing_corrupt_and_stale_snapshots_are_unavailable(self):
        self.assertFalse(read_telemetry(None)["available"])
        self.assertFalse(self.read({})["available"])
        self.assertFalse(self.read(self.snapshot(updated_at=time.monotonic() - 3))["available"])
        self.assertFalse(self.read(self.snapshot(updated_at=time.monotonic() + 10))["available"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "commands.json"
            self.assertFalse(read_telemetry(path)["available"])
            path.write_text("{partial", encoding="utf-8")
            self.assertFalse(read_telemetry(path)["available"])

    def test_invalid_numeric_values_never_reach_json_endpoint(self):
        for value in [float("nan"), float("inf"), "30", True]:
            with self.subTest(value=value):
                data = self.snapshot()
                data["arms"]["left"]["rate_hz"] = value
                self.assertFalse(self.read(data)["available"])

    def test_waiting_for_first_action_has_no_targets(self):
        data = self.snapshot()
        data["arms"]["left"].update(received_at=None, packets=0, targets={})
        arm = self.read(data)["arms"]["left"]
        self.assertFalse(arm["fresh"])
        self.assertIsNone(arm["packet_age_ms"])
        self.assertEqual(arm["targets"], {})

    def test_publisher_copies_commands_without_mutating_payload(self):
        telemetry = CommandTelemetry(30)
        action = {"shoulder_pan.pos": 23.5, "gripper.pos": 62,
                  "wrist_roll.pos": float("inf"), "elbow_flex.pos": True, "unknown.pos": 12}
        original = dict(action)
        try:
            telemetry.record("left", action)
            deadline = time.monotonic() + 4
            result = read_telemetry(telemetry.path)
            while not result.get("arms", {}).get("left", {}).get("fresh") and time.monotonic() < deadline:
                telemetry.record("left", action)
                time.sleep(.1)
                result = read_telemetry(telemetry.path)
            self.assertTrue(result["available"])
            self.assertEqual(result["arms"]["left"]["targets"], {"shoulder_pan": 23.5, "gripper": 62})
            self.assertEqual(action, original)
        finally:
            telemetry.close()
        self.assertFalse(telemetry.path.parent.exists())

    def test_file_write_failure_does_not_escape_to_recorder(self):
        telemetry = CommandTelemetry(30)
        try:
            with patch.object(Path, "write_text", side_effect=OSError("disk unavailable")):
                telemetry.record("left", {"gripper.pos": 10})
                time.sleep(.55)
                self.assertTrue(telemetry._thread.is_alive())
                self.assertEqual(telemetry.snapshot()["arms"]["left"]["targets"], {"gripper": 10})
        finally:
            telemetry.close()


if __name__ == "__main__":
    unittest.main()

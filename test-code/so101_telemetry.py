"""Read-only command telemetry shared with the camera process via a temporary file.

No extra motor reads, calibration changes or browser-to-arm commands. File I/O
runs on a separate thread so dashboard updates do not block the control loop.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
import tempfile
import threading
import time

LOG = logging.getLogger("so101.telemetry")
JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
STALE_SECONDS = 2.0


def finite_number(value) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


class CommandTelemetry:
    def __init__(self, frequency: float):
        self.frequency = frequency
        self._directory = tempfile.TemporaryDirectory(prefix="argus-so101-")
        self.path = Path(self._directory.name) / "commands.json"
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._arms = {side: {"targets": {}, "received_at": None, "packets": 0}
                      for side in ("left", "right")}
        self._last_counts = {"left": 0, "right": 0}
        self._last_sample = time.monotonic()
        self._thread = threading.Thread(target=self._publish, daemon=True)
        self._thread.start()

    def record(self, side: str, action: dict) -> None:
        targets = {}
        for joint in JOINTS:
            value = action.get(f"{joint}.pos")
            if finite_number(value):
                targets[joint] = value
        with self._lock:
            self._arms[side] = {"targets": targets, "received_at": time.monotonic(),
                                "packets": self._arms[side]["packets"] + 1}

    def snapshot(self) -> dict:
        now = time.monotonic()
        with self._lock:
            elapsed = max(now - self._last_sample, .001)
            arms = {}
            for side, data in self._arms.items():
                arms[side] = dict(data, rate_hz=round((data["packets"] - self._last_counts[side]) / elapsed, 1))
                self._last_counts[side] = data["packets"]
            self._last_sample = now
        return {"updated_at": now, "frequency": self.frequency, "arms": arms}

    def _publish(self) -> None:
        while not self._stop.is_set():
            try:
                temporary = self.path.with_suffix(".tmp")
                temporary.write_text(json.dumps(self.snapshot(), allow_nan=False), encoding="utf-8")
                for attempt in range(4):
                    try:
                        temporary.replace(self.path)
                        break
                    except PermissionError:
                        # Windows readers/scanners can briefly hold the target;
                        # retries remain on this background thread, never motors.
                        if attempt == 3:
                            raise
                        if self._stop.wait(.05):
                            return
            except (OSError, ValueError, TypeError) as exc:
                LOG.warning("Dashboard telemetry unavailable: %s", exc)
            self._stop.wait(.5)

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        if not self._thread.is_alive():
            self._directory.cleanup()


def read_telemetry(path: Path | None) -> dict:
    """Use monotonic timestamps from the same host; stale values never look live."""
    unavailable = {"available": False, "arms": {}}
    if path is None:
        return unavailable
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not finite_number(data["updated_at"]) or not finite_number(data["frequency"]) or data["frequency"] <= 0:
            return unavailable
        now = time.monotonic()
        age = now - data["updated_at"]
        if not math.isfinite(age) or not 0 <= age < STALE_SECONDS:
            return unavailable
        arms = {}
        for side in ("left", "right"):
            arm = data["arms"][side]
            received = arm["received_at"]
            packet_age = now - received if received is not None else None
            if packet_age is not None and (not finite_number(packet_age) or packet_age < 0):
                return unavailable
            if not finite_number(arm["rate_hz"]) or arm["rate_hz"] < 0 or type(arm["packets"]) is not int or arm["packets"] < 0:
                return unavailable
            fresh = packet_age is not None and 0 <= packet_age < 1.0
            targets = {joint: value for joint, value in arm["targets"].items()
                       if joint in JOINTS and finite_number(value)}
            arms[side] = {"fresh": fresh, "targets": targets if fresh else {},
                          "rate_hz": arm["rate_hz"] if fresh else 0,
                          "packet_age_ms": round(max(0, packet_age) * 1000) if packet_age is not None else None,
                          "packets": arm["packets"]}
        return {"available": True, "frequency": data["frequency"], "arms": arms}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return unavailable

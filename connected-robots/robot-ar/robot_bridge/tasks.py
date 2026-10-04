"""Background step sequencer. Always stops chassis if a step fails."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable


class TaskRunner:
    def __init__(self, chassis, arms) -> None:
        self.chassis = chassis
        self.arms = arms
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.status: dict[str, Any] = {
            "running": False,
            "text": "",
            "index": 0,
            "steps": [],
            "error": None,
            "finished": True,
        }

    def busy(self) -> bool:
        with self._lock:
            return bool(self.status["running"])

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self.status)

    def start(self, text: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            if self.status["running"]:
                raise RuntimeError("a task is already running; POST /stop first")
            self.status = {
                "running": True,
                "text": text,
                "index": 0,
                "steps": steps,
                "error": None,
                "finished": False,
            }
        self._thread = threading.Thread(target=self._run, args=(steps,), daemon=True)
        self._thread.start()
        return self.snapshot()

    def cancel(self) -> None:
        self.chassis.stop()
        self.chassis.enable_motor(False)
        with self._lock:
            self.status["running"] = False
            self.status["error"] = "cancelled"
            self.status["finished"] = True

    def _run(self, steps: list[dict[str, Any]]) -> None:
        try:
            self.chassis.enable_motor(True)
            for i, step in enumerate(steps):
                with self._lock:
                    if not self.status["running"]:
                        return
                    self.status["index"] = i
                self._exec(step)
            self.chassis.stop()
            with self._lock:
                self.status["running"] = False
                self.status["finished"] = True
                self.status["index"] = len(steps)
        except Exception as exc:
            self.chassis.stop()
            self.chassis.enable_motor(False)
            with self._lock:
                self.status["running"] = False
                self.status["finished"] = True
                self.status["error"] = str(exc)

    def _exec(self, step: dict[str, Any]) -> None:
        action = step.get("action")
        if action == "move":
            duration = float(step.get("duration", 1.0))
            end = time.monotonic() + duration
            while time.monotonic() < end:
                with self._lock:
                    if not self.status["running"]:
                        self.chassis.stop()
                        return
                self.chassis.set_cmd(
                    float(step.get("vx", 0.0)),
                    float(step.get("vy", 0.0)),
                    float(step.get("wz", 0.0)),
                )
                time.sleep(0.05)
            self.chassis.stop()
            return
        if action == "wait":
            time.sleep(float(step.get("duration", 1.0)))
            return
        if action == "stop":
            self.chassis.stop()
            self.chassis.enable_motor(False)
            return
        if action == "motor":
            self.chassis.enable_motor(bool(step.get("enabled", True)))
            return
        if action == "reset_odom":
            self.chassis.reset_odom()
            return
        if action == "gripper":
            self.arms.set_gripper(step.get("side", "both"), float(step.get("open", 0.0)))
            return
        if action == "arm_preset":
            self.arms.set_preset(step.get("side", "both"), step.get("preset", "home"))
            return
        if action == "arm_joints":
            self.arms.set_joints(step.get("side", "left"), list(step.get("joints", [])))
            return
        raise ValueError(f"unknown action {action}")

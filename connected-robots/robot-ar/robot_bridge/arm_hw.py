"""SO-101 follower over Feetech STS. Read-only until gripper command; no presets."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import time

import yaml

from feetech_bus import FeetechBus

JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

GRIP_SPEED = 400
ARM_SPEED = 120
NUDGE_MAX = 200
ACCEL = 30
DEFAULT_GRIPPER_IDS = [6]
DEFAULT_GRIPPER_CLOSED = [3600]
DEFAULT_GRIPPER_OPEN = [0]


def load_ports(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class HardwareArm:
    """One follower. connect() pings only; torque stays off until a command."""

    def __init__(self, side: str, cfg: dict[str, Any], robot_type: str) -> None:
        self.side = side
        self.cfg = cfg
        self.robot_type = robot_type
        self.robot = None
        self.bus: FeetechBus | None = None
        self.error: str | None = None
        self.ids: list[int] = []
        self.rest: dict[int, int] = {}
        self.torque_on = False
        self.gripper_ids = [int(x) for x in (cfg.get("gripper_ids") or DEFAULT_GRIPPER_IDS)]
        self.gripper_closed = [int(x) for x in (cfg.get("gripper_closed") or DEFAULT_GRIPPER_CLOSED)]
        self.gripper_open = [int(x) for x in (cfg.get("gripper_open") or DEFAULT_GRIPPER_OPEN)]
        while len(self.gripper_closed) < len(self.gripper_ids):
            self.gripper_closed.append(DEFAULT_GRIPPER_CLOSED[0])
        while len(self.gripper_open) < len(self.gripper_ids):
            self.gripper_open.append(DEFAULT_GRIPPER_OPEN[0])

    @property
    def port(self) -> str:
        return str(self.cfg.get("port", ""))

    def port_exists(self) -> bool:
        p = Path(self.port)
        return bool(self.port) and p.exists()

    def connect(self) -> bool:
        if not self.cfg.get("enabled", True):
            self.error = "disabled in config/ports.yaml"
            return False
        if not self.port_exists():
            self.error = f"port missing: {self.port}"
            return False
        self.disconnect()
        bus = FeetechBus(self.port)
        try:
            bus.open()
            ids = bus.ping_ids(range(1, 21))
        except Exception as exc:
            try:
                bus.close()
            except Exception:
                pass
            self.error = f"feetech open failed: {exc}"
            return False
        if len(ids) < 6:
            bus.close()
            self.error = f"incomplete STS bus on {self.port} (ids {ids}, need 1-6)"
            return False
        extra = [sid for sid in ids if sid not in self.gripper_ids and sid >= 7]
        if extra:
            # Extra servos on this bus: treat as additional gripper fingers.
            for sid in extra:
                if sid not in self.gripper_ids:
                    self.gripper_ids.append(sid)
                    self.gripper_closed.append(self.gripper_closed[0])
                    self.gripper_open.append(self.gripper_open[0])
        missing = [sid for sid in self.gripper_ids if sid not in ids]
        if missing:
            bus.close()
            self.error = f"gripper ids missing on {self.port}: {missing} (seen {ids})"
            return False
        self.bus = bus
        self.ids = ids
        self.rest = bus.read_positions(ids)
        self.torque_on = False
        self.error = None
        return True

    def read_positions(self) -> dict[int, int]:
        if self.bus is None:
            return {}
        return self.bus.read_positions(self.ids)

    def _write_goal(self, sid: int, pos: int, speed: int) -> bool:
        assert self.bus is not None
        ok = True
        ok = self.bus.set_accel(sid, ACCEL) and ok
        ok = self.bus.set_speed(sid, speed) and ok
        ok = self.bus.set_goal(sid, pos) and ok
        ok = self.bus.set_torque(sid, True) and ok
        if not ok:
            # retry once; web /state polling can collide on the bus
            time.sleep(0.02)
            ok = self.bus.set_goal(sid, pos) and self.bus.set_torque(sid, True)
        return ok

    def hold_arm(self, pos: dict[int, int] | None = None) -> dict[int, int]:
        if self.bus is None:
            raise RuntimeError(f"{self.side} bus not open")
        pos = pos or self.read_positions()
        goals: dict[int, int] = {}
        ok = True
        grip = set(self.gripper_ids)
        for sid in self.ids:
            if sid in grip:
                continue
            goal = max(0, min(4095, int(pos.get(sid, 0))))
            goals[sid] = goal
            ok = self._write_goal(sid, goal, ARM_SPEED) and ok
        self.torque_on = True
        if not ok:
            raise RuntimeError("arm hold write failed")
        return goals

    def hold_and_gripper(self, open_amount: float) -> dict[int, int]:
        if self.bus is None:
            raise RuntimeError(f"{self.side} bus not open")
        open_amount = max(0.0, min(1.0, float(open_amount)))
        pos = self.read_positions()
        hold = self.hold_arm(pos)
        goals: dict[int, int] = dict(hold)
        ok = True
        for sid, closed, opened in zip(self.gripper_ids, self.gripper_closed, self.gripper_open):
            target = int(round(closed + open_amount * (opened - closed)))
            target = max(0, min(4095, target))
            goals[sid] = target
            ok = self._write_goal(sid, target, GRIP_SPEED) and ok
        self.torque_on = True
        if not ok:
            raise RuntimeError("gripper write failed (bus collision or servo not responding)")
        return {"open": open_amount, "goals": goals, "gripper_ids": list(self.gripper_ids)}

    def nudge(self, servo_id: int, delta: int) -> dict[int, int]:
        if self.bus is None:
            raise RuntimeError(f"{self.side} bus not open")
        servo_id = int(servo_id)
        if servo_id in self.gripper_ids:
            raise ValueError("use gripper open/close for the gripper servo")
        if servo_id not in self.ids:
            raise ValueError(f"servo {servo_id} not on {self.side}")
        delta = max(-NUDGE_MAX, min(NUDGE_MAX, int(delta)))
        pos = self.read_positions()
        goals: dict[int, int] = {}
        ok = True
        grip = set(self.gripper_ids)
        for sid in self.ids:
            cur = int(pos.get(sid, 0))
            if sid == servo_id:
                goal = max(0, min(4095, cur + delta))
            else:
                goal = max(0, min(4095, cur))
            goals[sid] = goal
            speed = GRIP_SPEED if sid in grip else ARM_SPEED
            ok = self._write_goal(sid, goal, speed) and ok
        self.torque_on = True
        if not ok:
            raise RuntimeError("arm nudge write failed")
        return {"servo": servo_id, "delta": delta, "goals": goals}

    def send(self, joints: list[float], gripper: float | None) -> None:
        if gripper is None:
            raise RuntimeError("uncalibrated arm: only gripper open/close is allowed")
        self.hold_and_gripper(float(gripper))

    def torque_off(self) -> None:
        if self.bus is None:
            return
        for sid in self.ids:
            try:
                self.bus.set_torque(sid, False)
            except Exception:
                pass
        self.torque_on = False

    def disconnect(self) -> None:
        self.torque_off()
        if self.bus is not None:
            self.bus.close()
            self.bus = None
        self.robot = None

"""Dual-arm + gripper. Mock unless LeRobot + serial ports are present."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import threading
import time

from arm_hw import HardwareArm, load_ports

PRESETS = {
    "home": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "pick": [0.0, -0.6, 0.9, 0.0, 0.4, 0.0],
    "place": [0.4, -0.4, 0.7, 0.0, 0.3, 0.0],
}

DEFAULT_PORTS = Path(__file__).resolve().parent.parent / "config" / "ports.yaml"


@dataclass
class ArmState:
    side: str
    joints: list[float] = field(default_factory=lambda: [0.0] * 6)
    gripper: float = 1.0
    ready: bool = False
    mock: bool = True
    last_command: str = ""
    port: str = ""
    error: str | None = None


class DualArmDriver:
    def __init__(self, mock: bool = True, config_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self.left = ArmState(side="left", mock=True)
        self.right = ArmState(side="right", mock=True)
        self._hw: dict[str, HardwareArm] = {}
        path = config_path or DEFAULT_PORTS
        cfg = load_ports(path) if path.exists() else {}
        robot_type = cfg.get("robot_type", "so101_follower")
        for side in ("left", "right"):
            acfg = (cfg.get("arms") or {}).get(side) or {}
            hw = HardwareArm(side, acfg, robot_type)
            self._hw[side] = hw
            st = self.left if side == "left" else self.right
            st.port = hw.port
            if mock:
                st.mock = True
                st.error = "forced mock"
                continue
            ok = hw.connect()
            st.mock = not ok
            st.ready = ok
            st.error = hw.error

    @property
    def mock(self) -> bool:
        return self.left.mock and self.right.mock

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "left": self.left.__dict__.copy(),
                "right": self.right.__dict__.copy(),
                "mock": self.mock,
            }

    def _arm(self, side: str) -> ArmState:
        if side == "left":
            return self.left
        if side == "right":
            return self.right
        raise ValueError("side must be left or right")

    def sides(self, side: str) -> list[ArmState]:
        if side == "both":
            return [self.left, self.right]
        return [self._arm(side)]

    def set_joints(self, side: str, joints: list[float]) -> None:
        if len(joints) != 6:
            raise ValueError("need 6 joint values [pan, lift, elbow, wrist_flex, wrist_roll, gripper]")
        with self._lock:
            for arm in self.sides(side):
                arm.joints = [float(x) for x in joints]
                arm.gripper = float(joints[5])
                arm.last_command = f"joints={arm.joints}"
                hw = self._hw.get(arm.side)
                if hw and not arm.mock:
                    hw.send(arm.joints, arm.gripper)
                    arm.ready = True
                else:
                    arm.ready = arm.mock

    def set_preset(self, side: str, preset: str) -> None:
        if preset not in PRESETS:
            raise ValueError(f"unknown preset {preset}")
        self.set_joints(side, PRESETS[preset])
        with self._lock:
            for arm in self.sides(side):
                arm.last_command = f"preset={preset}"

    def set_gripper(self, side: str, open_amount: float) -> None:
        open_amount = max(0.0, min(1.0, float(open_amount)))
        with self._lock:
            for arm in self.sides(side):
                arm.gripper = open_amount
                arm.joints[5] = open_amount
                arm.last_command = f"gripper={open_amount:.2f}"
                hw = self._hw.get(arm.side)
                if hw and not arm.mock:
                    hw.send(arm.joints, open_amount)
                    arm.ready = True
                else:
                    arm.ready = arm.mock
        if self.mock:
            time.sleep(0.05)

    def estop(self) -> None:
        for hw in self._hw.values():
            hw.disconnect()
        with self._lock:
            for arm in (self.left, self.right):
                if not arm.mock:
                    arm.ready = False
                    arm.last_command = "estop"
                    arm.error = "disconnected by estop"

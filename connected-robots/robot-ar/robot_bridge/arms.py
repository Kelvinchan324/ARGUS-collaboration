"""Multi-arm + gripper. Configured arms come from config/ports.yaml."""

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

# Preferred display order when present in config.
SIDE_ORDER = ("left", "right", "left2", "right2")


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
    ids: list[int] = field(default_factory=list)


class DualArmDriver:
    """Keeps the old name; supports any number of arms listed under ports.yaml arms:."""

    def __init__(self, mock: bool = True, config_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._hw: dict[str, HardwareArm] = {}
        self._states: dict[str, ArmState] = {}
        path = config_path or DEFAULT_PORTS
        cfg = load_ports(path) if path.exists() else {}
        robot_type = cfg.get("robot_type", "so101_follower")
        arms_cfg = cfg.get("arms") or {}
        # Always expose left/right slots for older callers even if missing in yaml.
        side_names = list(arms_cfg.keys())
        for required in ("left", "right"):
            if required not in side_names:
                side_names.append(required)
        for side in side_names:
            acfg = arms_cfg.get(side) or {"enabled": False}
            hw = HardwareArm(side, acfg, robot_type)
            self._hw[side] = hw
            st = ArmState(side=side, mock=True)
            st.port = hw.port
            self._states[side] = st
            if mock:
                st.error = "forced mock"
                continue
            if not acfg.get("enabled", True):
                st.error = hw.error or "disabled in config/ports.yaml"
                continue
            ok = hw.connect()
            st.mock = not ok
            st.ready = ok
            st.error = hw.error
            st.ids = list(hw.ids)

        # Backward-compatible attributes.
        self.left = self._states["left"]
        self.right = self._states["right"]

    @property
    def mock(self) -> bool:
        wired = [s for s in self._states.values() if s.port]
        if not wired:
            return True
        return all(s.mock for s in wired)

    def arm_names(self) -> list[str]:
        ordered = [s for s in SIDE_ORDER if s in self._states]
        extra = [s for s in self._states if s not in ordered]
        return ordered + sorted(extra)

    def snapshot(self) -> dict:
        with self._lock:
            for side, arm in self._states.items():
                hw = self._hw.get(side)
                if hw and not arm.mock and hw.ids:
                    try:
                        pos = hw.read_positions()
                        joints = list(arm.joints)
                        for i, sid in enumerate(hw.ids[:6]):
                            if sid in pos:
                                joints[i] = float(pos[sid])
                        arm.joints = joints
                        if 6 in pos:
                            arm.gripper = float(pos[6])
                    except Exception as exc:
                        arm.error = str(exc)
            out = {side: st.__dict__.copy() for side, st in self._states.items()}
            out["mock"] = self.mock
            out["sides"] = self.arm_names()
            return out

    def _arm(self, side: str) -> ArmState:
        if side not in self._states:
            raise ValueError(f"unknown arm side {side!r}; known={self.arm_names()}")
        return self._states[side]

    def sides(self, side: str) -> list[ArmState]:
        if side == "both":
            return [self._states[s] for s in self.arm_names()]
        return [self._arm(side)]

    def set_joints(self, side: str, joints: list[float]) -> None:
        raise ValueError("absolute joint poses disabled until calibration; use /arm/{side}/nudge")

    def nudge(self, side: str, servo_id: int, delta: int) -> dict:
        with self._lock:
            out = {}
            for arm in self.sides(side):
                hw = self._hw.get(arm.side)
                if hw and not arm.mock:
                    info = hw.nudge(servo_id, delta)
                    arm.last_command = f"nudge id={servo_id} d={delta} goals={info.get('goals')}"
                    arm.ready = True
                    arm.error = None
                    out[arm.side] = info
                else:
                    raise ValueError(f"{arm.side} arm not wired")
            return out

    def set_preset(self, side: str, preset: str) -> None:
        raise ValueError("presets (home/pick/place) disabled until calibration")

    def set_gripper(self, side: str, open_amount: float) -> None:
        open_amount = max(0.0, min(1.0, float(open_amount)))
        with self._lock:
            for arm in self.sides(side):
                hw = self._hw.get(arm.side)
                if hw and not arm.mock:
                    info = hw.hold_and_gripper(open_amount)
                    arm.last_command = f"gripper={open_amount:.2f} goals={info.get('goals')}"
                    arm.ready = True
                    arm.error = None
                else:
                    arm.gripper = open_amount
                    arm.joints[5] = open_amount
                    arm.last_command = f"gripper={open_amount:.2f}"
                    arm.ready = arm.mock
        if self.mock:
            time.sleep(0.05)

    def estop(self) -> None:
        for hw in self._hw.values():
            hw.torque_off()
        with self._lock:
            for arm in self._states.values():
                if not arm.mock:
                    arm.last_command = "estop"

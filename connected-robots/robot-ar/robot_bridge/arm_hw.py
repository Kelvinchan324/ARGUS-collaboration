"""LeRobot SO-101/100 backend. Stays mock if ports or package are missing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]


def load_ports(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def try_import_lerobot():
    try:
        from lerobot.robots.so101_follower import SO101Follower
        from lerobot.robots.so101_follower.so101_follower import SO101FollowerConfig

        return SO101Follower, SO101FollowerConfig
    except Exception:
        try:
            from lerobot.common.robots.so101_follower import SO101Follower
            from lerobot.common.robots.so101_follower import SO101FollowerConfig

            return SO101Follower, SO101FollowerConfig
        except Exception:
            return None, None


class HardwareArm:
    """One follower. connect() is safe to call with nothing plugged in."""

    def __init__(self, side: str, cfg: dict[str, Any], robot_type: str) -> None:
        self.side = side
        self.cfg = cfg
        self.robot_type = robot_type
        self.robot = None
        self.error: str | None = None

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
        Follower, Config = try_import_lerobot()
        if Follower is None:
            self.error = "lerobot not installed (see scripts/install_lerobot.sh)"
            return False
        try:
            self.robot = Follower(Config(port=self.port, id=self.cfg.get("id", self.side)))
            self.robot.connect()
            self.error = None
            return True
        except Exception as exc:
            self.robot = None
            self.error = str(exc)
            return False

    def send(self, joints: list[float], gripper: float | None) -> None:
        if self.robot is None:
            return
        values = list(joints)
        if gripper is not None and len(values) >= 6:
            values[5] = float(gripper)
        action = {name: float(values[i]) for i, name in enumerate(JOINTS) if i < len(values)}
        self.robot.send_action(action)

    def disconnect(self) -> None:
        if self.robot is None:
            return
        try:
            self.robot.disconnect()
        except Exception:
            pass
        self.robot = None

"""Harness-style vla_act slot. Frozen VLA is not loaded; never fake a grasp."""

from __future__ import annotations

from typing import Any


class VLARuntime:
    def __init__(self, cameras, arms, chassis) -> None:
        self.cameras = cameras
        self.arms = arms
        self.chassis = chassis

    def capabilities(self) -> dict[str, Any]:
        cam = self.cameras.status()
        return {
            "wired": False,
            "name": "vla_act",
            "policy": None,
            "missing": [
                m
                for m, ok in (
                    ("camera_frame", bool(cam.get("devices")) and cam.get("frame") is not None),
                    ("arm_serial", False),
                    ("vla_checkpoint", False),
                )
                if not ok
            ],
            "reason": "no camera frame, no arm serial, no VLA checkpoint",
        }

    def act(self, instruction: str, timeout_s: float = 4.0) -> dict[str, Any]:
        cap = self.capabilities()
        return {
            "ok": False,
            "wired": False,
            "instruction": instruction,
            "timeout_s": timeout_s,
            "actions": [],
            "missing": cap["missing"],
            "reason": cap["reason"],
        }

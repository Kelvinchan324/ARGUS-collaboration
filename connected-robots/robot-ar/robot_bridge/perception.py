"""Camera slot. Detects devices; does not invent frames."""

from __future__ import annotations

import glob
from typing import Any


def list_video_devices() -> list[str]:
    return sorted(glob.glob("/dev/video*"))


class CameraHub:
    def status(self) -> dict[str, Any]:
        devices = list_video_devices()
        return {
            "wired": bool(devices),
            "devices": devices,
            "frame": None,
            "reason": None if devices else "no /dev/video* — plug in a USB / RealSense camera",
        }

    def latest(self) -> dict[str, Any]:
        st = self.status()
        if not st["wired"]:
            return st
        # Capture backend (OpenCV / RealSense) is not wired yet.
        st["frame"] = None
        st["wired"] = False
        st["reason"] = (
            f"camera device present ({st['devices']}) but capture pipeline not implemented"
        )
        return st

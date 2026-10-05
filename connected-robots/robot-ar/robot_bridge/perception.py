"""USB camera hub. Serves real MJPEG frames from V4L2 capture nodes."""

from __future__ import annotations

import glob
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

FRAME_PATH = Path("/tmp/robot_cam0.jpg")


def list_video_devices() -> list[str]:
    return sorted(glob.glob("/dev/video*"))


def capture_nodes() -> list[str]:
    """One node per physical camera (UVC also exposes a metadata node)."""
    nodes = sorted(glob.glob("/dev/v4l/by-path/*-video-index0"))
    if nodes:
        return nodes
    return list_video_devices()


class CameraHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._device: str | None = None
        self._error: str | None = None
        self._stop = threading.Event()
        threading.Thread(target=self._loop, name="camera-grab", daemon=True).start()

    def jpeg(self) -> bytes | None:
        with self._lock:
            return self._jpeg

    def status(self) -> dict[str, Any]:
        devices = list_video_devices()
        nodes = capture_nodes()
        with self._lock:
            has_frame = self._jpeg is not None
            err = self._error
            dev = self._device
        return {
            "wired": bool(nodes),
            "devices": devices,
            "cameras": nodes,
            "active": dev,
            "frame": has_frame,
            "reason": None if has_frame else (err or ("no /dev/video*" if not nodes else "waiting for first frame")),
        }

    def latest(self) -> dict[str, Any]:
        return self.status()

    def _grab(self, device: str) -> bytes | None:
        FRAME_PATH.unlink(missing_ok=True)
        proc = subprocess.run(
            [
                "v4l2-ctl",
                "-d",
                device,
                "--set-fmt-video=width=640,height=480,pixelformat=MJPG",
                "--stream-mmap",
                "--stream-count=1",
                f"--stream-to={FRAME_PATH}",
            ],
            capture_output=True,
            timeout=3,
            check=False,
        )
        if not FRAME_PATH.exists():
            err = (proc.stderr or proc.stdout or b"").decode("utf-8", "replace").strip()
            raise RuntimeError(err[-240:] or "v4l2-ctl produced no file")
        data = FRAME_PATH.read_bytes()
        if not data.startswith(b"\xff\xd8"):
            raise RuntimeError("capture was not JPEG")
        return data

    def _loop(self) -> None:
        while not self._stop.is_set():
            nodes = capture_nodes()
            if not nodes:
                with self._lock:
                    self._jpeg = None
                    self._device = None
                    self._error = "no /dev/video*"
                time.sleep(1.0)
                continue
            device = nodes[0]
            try:
                data = self._grab(device)
                with self._lock:
                    self._jpeg = data
                    self._device = device
                    self._error = None
            except Exception as exc:
                with self._lock:
                    self._error = f"{device}: {exc}"
                time.sleep(0.5)
            time.sleep(0.12)

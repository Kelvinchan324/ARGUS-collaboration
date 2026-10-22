"""Serve the ARGUS camera dashboard without accessing any robot arms."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import cv2

from so101_camera_utils import camera_source, open_capture, positive_int, validate_sources
from so101_telemetry import read_telemetry

LOG = logging.getLogger("so101.camera")
ROOT = Path(__file__).resolve().parent
FRESH_SECONDS = 2.0
DEFAULT_LABELS = ["Top", "Left gripper", "Right gripper"]


class CameraStream:
    def __init__(self, source: int | str, width: int, height: int, fps: int, quality: int):
        self.source = source
        self.width, self.height, self.fps, self.quality = width, height, fps, quality
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._jpeg: bytes | None = None
        self._updated = 0.0
        self._error = "Waiting for camera"
        self._resolution: list[int] | None = None
        self._thread = threading.Thread(target=self._capture_frames, daemon=True)
        self._thread.start()

    def _capture_frames(self) -> None:
        while not self._stop.is_set():
            capture = None
            try:
                capture = open_capture(self.source, self.width, self.height, self.fps)
                while not self._stop.is_set():
                    started = time.monotonic()
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        raise RuntimeError("Camera stopped returning frames; check USB power/bandwidth")
                    encoded, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                    if not encoded:
                        raise RuntimeError("Could not encode camera frame")
                    with self._lock:
                        self._jpeg = jpeg.tobytes()
                        self._updated = time.monotonic()
                        self._resolution = [int(frame.shape[1]), int(frame.shape[0])]
                        self._error = ""
                    self._stop.wait(max(0, 1 / self.fps - (time.monotonic() - started)))
            except Exception as exc:
                with self._lock:
                    self._jpeg = None
                    self._error = str(exc)
                LOG.warning("Camera %r: %s; retrying", self.source, exc)
            finally:
                if capture is not None:
                    capture.release()
            self._stop.wait(2)

    def latest_frame(self) -> bytes | None:
        with self._lock:
            return self._jpeg if time.monotonic() - self._updated < FRESH_SECONDS else None

    def status(self) -> dict:
        with self._lock:
            age = time.monotonic() - self._updated if self._updated else None
            online = self._jpeg is not None and age is not None and age < FRESH_SECONDS
            return {"source": str(self.source), "online": online, "resolution": self._resolution,
                    "frame_age_seconds": round(age, 2) if age is not None else None,
                    "error": "" if online else (self._error or "No recent frames")}

    def close(self) -> None:
        self._stop.set()
        # The capture thread owns/releases its device. A stuck driver must not
        # prevent process exit or race a release against an in-progress read.
        self._thread.join(timeout=2)


def make_handler(cameras: list[CameraStream], labels: list[str], telemetry_file: Path | None = None):
    assets = {
        "/": (ROOT / "camera-ui/index.html", "text/html; charset=utf-8"),
        "/camera.css": (ROOT / "camera-ui/camera.css", "text/css; charset=utf-8"),
        "/camera.js": (ROOT / "camera-ui/camera.js", "text/javascript; charset=utf-8"),
        "/argus-logo.png": (ROOT.parent / "docs/assets/argus-logo.png", "image/png"),
    }

    class StreamHandler(BaseHTTPRequestHandler):
        def send_bytes(self, data: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            try:
                if path in assets:
                    asset, content_type = assets[path]
                    self.send_bytes(asset.read_bytes(), content_type)
                    return
                if path == "/api/cameras":
                    roles = ["top", "left", "right", "front"]
                    states = [dict(camera.status(), id=index, label=label,
                                   role=roles[index] if index < len(roles) else "camera")
                              for index, (camera, label) in enumerate(zip(cameras, labels))]
                    self.send_bytes(json.dumps({"cameras": states}).encode(), "application/json")
                    return
                if path == "/api/telemetry":
                    self.send_bytes(json.dumps(read_telemetry(telemetry_file), allow_nan=False).encode(), "application/json")
                    return
                match = re.fullmatch(r"/stream/(\d+)", path)
                if match and int(match[1]) < len(cameras):
                    camera = cameras[int(match[1])]
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    while not camera._stop.is_set():
                        jpeg = camera.latest_frame()
                        if jpeg is not None:
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                            + f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
                                            + jpeg + b"\r\n")
                            self.wfile.flush()
                        camera._stop.wait(1 / camera.fps)
                    return
                self.send_error(404, "Not found")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, format: str, *args: object) -> None:
            LOG.debug("HTTP %s - %s", self.address_string(), format % args)

    return StreamHandler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", nargs="+", default=["0", "2", "4"], metavar="INDEX_OR_PATH")
    parser.add_argument("--labels", nargs="+", help="one display label per camera")
    parser.add_argument("--telemetry-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=positive_int, default=8000)
    parser.add_argument("--width", type=positive_int, default=640)
    parser.add_argument("--height", type=positive_int, default=480)
    parser.add_argument("--fps", type=positive_int, default=15)
    parser.add_argument("--quality", type=int, choices=range(1, 101), default=75)
    args = parser.parse_args()
    try:
        validate_sources(args.camera)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        parser.error(str(exc))
    if args.port > 65535:
        parser.error("port must be between 1 and 65535")
    labels = args.labels or ((DEFAULT_LABELS + ["Front"])[:len(args.camera)] if len(args.camera) in (3, 4) else
                             [f"Camera {index + 1}" for index in range(len(args.camera))])
    if len(labels) != len(args.camera):
        parser.error("provide exactly one --labels value per camera")
    cameras = []
    try:
        for value in args.camera:
            cameras.append(CameraStream(camera_source(value), args.width, args.height, args.fps, args.quality))
        with ThreadingHTTPServer((args.host, args.port), make_handler(cameras, labels, args.telemetry_file)) as server:
            server.daemon_threads = True
            LOG.info("ARGUS camera page: http://<follower-host>:%d", args.port)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                LOG.info("Stopping camera streams")
    finally:
        for camera in cameras:
            camera.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    main()

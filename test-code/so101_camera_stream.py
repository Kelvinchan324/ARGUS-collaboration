"""Stream one or more USB cameras from the follower computer to a browser."""

from __future__ import annotations

import argparse
import html
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

LOG = logging.getLogger("so101.camera")


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def camera_source(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


class CameraStream:
    def __init__(self, source: int | str, width: int, height: int, fps: int, quality: int):
        self.source = source
        self.fps = fps
        self.quality = quality
        self.capture = cv2.VideoCapture(source)
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError(f"Could not open camera {source!r}")
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_FPS, fps)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._jpeg: bytes | None = None
        self._thread = threading.Thread(target=self._capture_frames, daemon=True)
        self._thread.start()

    def _capture_frames(self) -> None:
        while not self._stop.is_set():
            ok, frame = self.capture.read()
            if not ok:
                LOG.warning("Failed to read camera %r; retrying", self.source)
                self._stop.wait(0.2)
                continue
            encoded, jpeg = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            )
            if encoded:
                with self._lock:
                    self._jpeg = jpeg.tobytes()

    def latest_frame(self) -> bytes | None:
        with self._lock:
            return self._jpeg

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self.capture.release()


def make_handler(cameras: list[CameraStream], labels: list[str]):
    class StreamHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                cards = "".join(
                    f'<section><h2>{html.escape(label)}</h2>'
                    f'<img src="/stream/{index}" alt="{html.escape(label)}"></section>'
                    for index, label in enumerate(labels)
                )
                page = (
                    "<!doctype html><html><head><meta charset='utf-8'>"
                    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                    "<title>SO-101 camera streams</title>"
                    "<style>body{font:16px sans-serif;background:#181818;color:#eee}"
                    "main{display:flex;flex-wrap:wrap;gap:16px}section{flex:1 1 480px}"
                    "img{display:block;width:100%;height:auto;background:#000}</style>"
                    f"</head><body><h1>SO-101 camera streams</h1><main>{cards}</main></body></html>"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.end_headers()
                self.wfile.write(page)
                return

            prefix = "/stream/"
            if self.path.startswith(prefix):
                try:
                    index = int(self.path[len(prefix) :])
                    camera = cameras[index]
                except (ValueError, IndexError):
                    self.send_error(404, "Unknown camera stream")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    while not camera._stop.is_set():
                        jpeg = camera.latest_frame()
                        if jpeg is None:
                            camera._stop.wait(0.05)
                            continue
                        self.wfile.write(
                            b"--frame\r\nContent-Type: image/jpeg\r\n"
                            + f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
                            + jpeg
                            + b"\r\n"
                        )
                        self.wfile.flush()
                        camera._stop.wait(1 / camera.fps)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return

            self.send_error(404, "Not found")

        def log_message(self, format: str, *args: object) -> None:
            LOG.info("HTTP %s - %s", self.address_string(), format % args)

    return StreamHandler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--camera",
        nargs="+",
        default=["0"],
        metavar="INDEX_OR_PATH",
        help="camera index or device path; repeat values for multiple cameras",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=positive_int, default=8000)
    parser.add_argument("--width", type=positive_int, default=1280)
    parser.add_argument("--height", type=positive_int, default=960)
    parser.add_argument("--fps", type=positive_int, default=15)
    parser.add_argument("--quality", type=int, choices=range(1, 101), default=80)
    args = parser.parse_args()

    cameras = []
    try:
        for value in args.camera:
            cameras.append(
                CameraStream(camera_source(value), args.width, args.height, args.fps, args.quality)
            )
        labels = [f"Camera {index}: {source}" for index, source in enumerate(args.camera)]
        server = ThreadingHTTPServer((args.host, args.port), make_handler(cameras, labels))
        server.daemon_threads = True
        LOG.info("Camera page ready at http://<follower-host>:%d", args.port)
        LOG.info("Streaming cameras: %s", ", ".join(args.camera))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            LOG.info("Stopping camera streams")
        finally:
            server.server_close()
    finally:
        for camera in cameras:
            camera.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    main()

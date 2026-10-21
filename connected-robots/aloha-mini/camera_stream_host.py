#!/usr/bin/env python3
"""Serve Aloha Mini camera frames to a browser over HTTP/MJPEG."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time


class LatestFrame:
    def __init__(self):
        self.condition = threading.Condition()
        self.jpeg = None
        self.sequence = 0

    def publish(self, jpeg):
        with self.condition:
            self.jpeg = jpeg
            self.sequence += 1
            self.condition.notify_all()

    def wait_for_frame(self, previous_sequence):
        with self.condition:
            self.condition.wait_for(
                lambda: self.sequence != previous_sequence, timeout=2.0
            )
            return self.sequence, self.jpeg


def make_handler(latest_frame):
    class CameraHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                body = b"""<!doctype html>
<html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Aloha Mini Camera</title>
<style>html,body{margin:0;background:#101820;color:#fff;font:16px sans-serif}
header{padding:12px 16px;background:#192833}img{display:block;width:100%;height:auto}</style>
</head><body><header>Aloha Mini | Live Camera</header>
<img src=\"/stream.mjpg\" alt=\"Live camera\"></body></html>"""
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path != "/stream.mjpg":
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=frame"
            )
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()

            sequence = -1
            try:
                while True:
                    sequence, jpeg = latest_frame.wait_for_frame(sequence)
                    if jpeg is None:
                        continue
                    self.wfile.write(
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
                        + jpeg
                        + b"\r\n"
                    )
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        def log_message(self, format, *args):
            return

    return CameraHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="Interface to listen on")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    parser.add_argument("--fps", type=float, default=10, help="Stream frame rate")
    parser.add_argument(
        "--camera-index",
        type=int,
        help="Stream only this OpenCV camera index instead of the default camera grid",
    )
    args = parser.parse_args()
    if not 0 < args.port < 65536:
        parser.error("--port must be between 1 and 65535")
    if args.fps <= 0:
        parser.error("--fps must be positive")
    if args.camera_index is not None and args.camera_index < 0:
        parser.error("--camera-index must not be negative")

    import cv2

    if args.camera_index is not None:
        camera = cv2.VideoCapture(args.camera_index)
        #=====================================================================================
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT,1280)




        if not camera.isOpened():
            camera.release()
            parser.error(f"Could not open camera index {args.camera_index}")
        cameras = [camera]
        camera_devices = [f"index {args.camera_index}"]
        create_grid = None
    else:
        from camera_view import (
            CAMERA_DEVICES,
            FRAME_HEIGHT,
            FRAME_ORDER,
            FRAME_WIDTH,
            GRID_COLS,
            GRID_ROWS,
            create_grid,
            open_camera,
        )

        cameras = [open_camera(device) for device in CAMERA_DEVICES]
        camera_devices = CAMERA_DEVICES
        if not any(camera is not None for camera in cameras):
            parser.error("No cameras could be opened; check camera_view.py device discovery")

    latest_frame = LatestFrame()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(latest_frame))
    server.daemon_threads = True
    if args.camera_index is not None:
        print(f"Streaming camera index {args.camera_index}")
    else:
        print(f"Streaming {sum(camera is not None for camera in cameras)}/{len(cameras)} cameras")
    print(f"Open http://<robot-ip>:{args.port}/ from the control station")

    try:
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        while True:
            frames = []
            for camera in cameras:
                if camera is None:
                    frames.append(None)
                    continue
                ok, frame = camera.read()
                frames.append(frame if ok else None)

            if create_grid is None:
                if frames[0] is None:
                    time.sleep(1.0 / args.fps)
                    continue
                output_frame = frames[0]
            else:
                output_frame = create_grid(
                    frames,
                    GRID_ROWS,
                    GRID_COLS,
                    FRAME_WIDTH,
                    FRAME_HEIGHT,
                    camera_devices,
                    FRAME_ORDER,
                )
            ok, encoded = cv2.imencode(
                ".jpg", output_frame, [cv2.IMWRITE_JPEG_QUALITY, 80]
            )
            if ok:
                latest_frame.publish(encoded.tobytes())
            time.sleep(1.0 / args.fps)
    except KeyboardInterrupt:
        print("Stopping camera stream")
    finally:
        server.shutdown()
        server.server_close()
        for camera in cameras:
            if camera is not None:
                camera.release()


if __name__ == "__main__":
    main()
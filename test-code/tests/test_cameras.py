"""Camera/launcher checks with synthetic frames; never imports real robot drivers."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import so101_camera_stream as stream
import so101_camera_utils as utils


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


discovery = load_script("camera_discovery", "discover-cameras.py")


class CameraTests(unittest.TestCase):
    def test_duplicate_indices_and_device_aliases_rejected(self):
        with self.assertRaises(ValueError):
            utils.validate_sources(["0", "00", "4"])
        with patch.object(utils.sys, "platform", "linux"):
            with self.assertRaises(ValueError):
                utils.validate_sources(["0", "/dev/video0", "4"])
        with self.assertRaises(argparse.ArgumentTypeError):
            utils.camera_source("-1")

    def test_usb_transport_requested_before_resolution(self):
        capture = Mock()
        capture.isOpened.return_value = True
        with patch.object(cv2, "VideoCapture", return_value=capture):
            self.assertIs(utils.open_capture(0, 640, 480, 15), capture)
        self.assertEqual(capture.set.call_args_list[0].args[0], cv2.CAP_PROP_FOURCC)

    def test_failed_open_releases_device(self):
        capture = Mock()
        capture.isOpened.return_value = False
        with patch.object(cv2, "VideoCapture", return_value=capture):
            with self.assertRaises(RuntimeError):
                utils.open_capture(0, 640, 480, 15)
        capture.release.assert_called_once()

    def test_fresh_frame_encodes_and_stale_frame_is_hidden(self):
        capture = Mock()
        capture.read.return_value = (True, np.zeros((48, 64, 3), dtype=np.uint8))
        with patch.object(stream, "open_capture", return_value=capture):
            camera = stream.CameraStream(0, 64, 48, 15, 75)
            try:
                deadline = time.monotonic() + 2
                while camera.latest_frame() is None and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(camera.status()["online"])
                jpeg = camera.latest_frame()
                decoded = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                self.assertEqual(decoded.shape[:2], (48, 64))
                camera.close()
                with patch.object(stream.time, "monotonic", return_value=time.monotonic() + 10):
                    self.assertIsNone(camera.latest_frame())
                    self.assertFalse(camera.status()["online"])
            finally:
                camera.close()
        capture.release.assert_called_once()

    def test_missing_camera_reconnects_independently(self):
        capture = Mock()
        capture.read.return_value = (True, np.zeros((48, 64, 3), dtype=np.uint8))
        with patch.object(stream, "open_capture", side_effect=[RuntimeError("unplugged"), capture]) as opened:
            camera = stream.CameraStream(2, 64, 48, 15, 75)
            try:
                deadline = time.monotonic() + 4
                while not camera.status()["online"] and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(camera.status()["online"])
                self.assertGreaterEqual(opened.call_count, 2)
            finally:
                camera.close()

    def test_probe_requires_real_frames_and_saves_sample(self):
        capture = Mock()
        capture.read.return_value = (True, np.zeros((48, 64, 3), dtype=np.uint8))
        capture.get.return_value = 15
        with tempfile.TemporaryDirectory() as folder, patch.object(discovery, "open_capture", return_value=capture):
            snapshot = str(Path(folder) / "sample.jpg")
            result = discovery.probe("0", 640, 480, 15, snapshot)
            self.assertTrue(result["usable"])
            self.assertEqual(result["resolution"], [64, 48])
            self.assertTrue(Path(snapshot).is_file())
        capture.release.assert_called_once()

    def test_metadata_node_not_reported_as_usable(self):
        capture = Mock()
        capture.read.return_value = (False, None)
        with patch.object(discovery, "open_capture", return_value=capture):
            self.assertFalse(discovery.probe("1", 640, 480, 15, None)["usable"])
        capture.release.assert_called_once()

    def test_probe_timeout_is_bounded(self):
        args = SimpleNamespace(width=640, height=480, fps=15, timeout=1)
        with patch.object(discovery.subprocess, "run", side_effect=subprocess.TimeoutExpired("probe", 1)):
            result = discovery.bounded_probe("0", args, None)
        self.assertFalse(result["usable"])
        self.assertIn("within 1s", result["error"])

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux stable-device symlinks")
    def test_discovery_groups_aliases_and_keeps_metadata_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "video0").touch()
            (root / "video1").touch()
            (root / "v4l/by-id").mkdir(parents=True)
            (root / "v4l/by-path").mkdir(parents=True)
            (root / "v4l/by-id/usb-camera-index0").symlink_to(root / "video0")
            (root / "v4l/by-path/usb-port-index0").symlink_to(root / "video0")
            devices = discovery.candidates(device_root=root)
            self.assertEqual(len(devices), 2)
            self.assertIn("by-id", devices[0]["source"])
            self.assertEqual(len(devices[0]["aliases"]), 3)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cameras = []
        _, jpeg = cv2.imencode(".jpg", np.zeros((48, 64, 3), dtype=np.uint8))
        cls.jpeg = jpeg.tobytes()
        for index in range(3):
            camera = SimpleNamespace(_stop=threading.Event(), fps=15,
                                     latest_frame=lambda: cls.jpeg,
                                     status=lambda: {"source": "test", "online": True, "resolution": [64, 48]})
            cls.cameras.append(camera)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), stream.make_handler(cls.cameras, stream.DEFAULT_LABELS))
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        for camera in cls.cameras:
            camera._stop.set()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_page_assets_and_logo_are_served_locally(self):
        for path, content_type in [("/", "text/html"), ("/camera.js", "text/javascript"),
                                   ("/camera.css", "text/css"), ("/argus-logo.png", "image/png")]:
            with self.subTest(path=path), urlopen(self.url + path, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(content_type, response.headers["Content-Type"])
                self.assertTrue(response.read())

    def test_named_status_for_all_three_cameras(self):
        with urlopen(self.url + "/api/cameras", timeout=2) as response:
            cameras = json.load(response)["cameras"]
        self.assertEqual([camera["label"] for camera in cameras], stream.DEFAULT_LABELS)
        self.assertEqual([camera["id"] for camera in cameras], [0, 1, 2])

    def test_three_independent_mjpeg_streams(self):
        for index in range(3):
            with self.subTest(index=index), urlopen(self.url + f"/stream/{index}?test=1", timeout=2) as response:
                self.assertIn("multipart/x-mixed-replace", response.headers["Content-Type"])
                self.assertEqual(response.readline(), b"--frame\r\n")
                self.assertEqual(response.readline(), b"Content-Type: image/jpeg\r\n")
                size = int(response.readline().split(b":")[1])
                self.assertEqual(response.readline(), b"\r\n")
                self.assertEqual(response.read(size), self.jpeg)

    def test_unknown_negative_and_traversal_routes_rejected(self):
        for path in ["/stream/-1", "/stream/3", "/stream/no", "/../so101-config.env", "/camera-ui/../so101-config.env"]:
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                urlopen(self.url + path, timeout=2)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()


class ReceiverTests(unittest.TestCase):
    def test_receiver_passes_three_sources_without_changing_calibration_ids(self):
        configs = []

        def config(**values):
            configs.append(values)
            return SimpleNamespace(**values)

        followers = [Mock(is_connected=True), Mock(is_connected=True)]
        modules = {"zmq": Mock(),
                   "lerobot.robots.so_follower.config_so_follower": SimpleNamespace(SOFollowerRobotConfig=config),
                   "lerobot.robots.so_follower.so_follower": SimpleNamespace(SOFollower=Mock(side_effect=followers))}
        with patch.dict(sys.modules, modules):
            receiver = load_script("test_receiver", "so101_bimanual_receiver.py")
        receiver.zmq.Poller.return_value.poll.side_effect = KeyboardInterrupt
        process = Mock()
        process.poll.return_value = None
        argv = ["receiver", "--camera-top", "/dev/v4l/by-id/top", "--camera-left", "6", "--camera-right", "8"]
        with patch.object(sys, "argv", argv), patch.object(receiver.subprocess, "Popen", return_value=process) as popen:
            receiver.main()
        command = popen.call_args.args[0]
        start = command.index("--camera") + 1
        self.assertEqual(command[start:start + 3], ["/dev/v4l/by-id/top", "6", "8"])
        self.assertEqual([item["id"] for item in configs], ["follower_left", "follower_right"])
        for follower in followers:
            follower.connect.assert_called_once_with()
            follower.disconnect.assert_called_once_with()


BASH = ("C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32" and Path("C:/Program Files/Git/bin/bash.exe").exists()
        else shutil.which("bash"))


@unittest.skipUnless(BASH, "Bash needed for Raspberry Pi launcher checks")
class LauncherTests(unittest.TestCase):
    def check_config(self, contents):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "local.env"
            config.write_text(contents, encoding="utf-8")
            before = config.read_bytes()
            result = subprocess.run([BASH, str(ROOT / "start-so101-control.sh"), "--check-config"],
                                    env=dict(os.environ, SO101_CONFIG_FILE=config.as_posix()),
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(config.read_bytes(), before, "Launcher must never rewrite local configuration")
            return result

    def test_existing_config_uses_legacy_top_and_new_defaults(self):
        result = self.check_config("SO101_ROLE=follower\nSO101_CAMERA_INDEX=6\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("6 / 2 / 4", result.stdout)

    def test_stable_paths_and_capture_options(self):
        result = self.check_config("SO101_ROLE=follower\nSO101_CAMERA_TOP=/dev/v4l/by-id/top\nSO101_CAMERA_LEFT=6\nSO101_CAMERA_RIGHT=8\nSO101_CAMERA_FPS=10\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/dev/v4l/by-id/top / 6 / 8", result.stdout)
        self.assertIn("10 FPS", result.stdout)

    def test_invalid_duplicate_and_zero_settings_rejected(self):
        for settings in ["SO101_CAMERA_LEFT=0\n", "SO101_CAMERA_FPS=0\n", "SO101_CAMERA_QUALITY=101\n", "SO101_CAMERA_TOP=-1\n"]:
            with self.subTest(settings=settings):
                self.assertNotEqual(self.check_config("SO101_ROLE=follower\n" + settings).returncode, 0)

    def test_leader_does_not_require_follower_camera_mapping(self):
        result = self.check_config("SO101_ROLE=leader\nSO101_FOLLOWER_HOST=robot.local\nSO101_CAMERA_INDEX=2\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_setup_rerun_preserves_config_and_calibration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scripts = root / "test-code"
            scripts.mkdir()
            for name in ["setup-so101-device.sh", "start-so101-control.sh", "SO-101-Control-and-Camera.desktop", "so101-config.env.example"]:
                shutil.copyfile(ROOT / name, scripts / name)
            config = scripts / "so101-config.env"
            config.write_text("SO101_ROLE=follower\nSO101_CAMERA_INDEX=6\n", encoding="utf-8")
            calibration = root / "lerobot/calibration/follower_left.json"
            calibration.parent.mkdir(parents=True)
            calibration.write_text('{"existing_calibration": true}', encoding="utf-8")
            before = (config.read_bytes(), calibration.read_bytes())
            result = subprocess.run([BASH, str(scripts / "setup-so101-device.sh")], capture_output=True,
                                    text=True, env=dict(os.environ, XDG_DESKTOP_DIR=(root / "Desktop").as_posix()), timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((config.read_bytes(), calibration.read_bytes()), before)


if __name__ == "__main__":
    unittest.main()

"""Receive SO-101 leader actions and send them to two follower arms."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import signal
import subprocess
import sys
import time

import zmq
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
from lerobot.robots.so_follower.so_follower import SOFollower

LOG = logging.getLogger("so101.receiver")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="*")
    parser.add_argument("--left-port", default="/dev/ttyACM0", help="left follower serial device")
    parser.add_argument("--right-port", default="/dev/ttyACM1", help="right follower serial device")
    parser.add_argument("--left-zmq-port", type=int, default=5555)
    parser.add_argument("--right-zmq-port", type=int, default=5556)
    parser.add_argument("--frequency", type=float, default=30.0)
    parser.add_argument("--camera-host", default="0.0.0.0")
    parser.add_argument("--camera-port", type=int, default=8000)
    parser.add_argument("--camera-index", type=int, default=0)
    args = parser.parse_args()
    if (
        args.frequency <= 0
        or not 0 < args.left_zmq_port <= 65_535
        or not 0 < args.right_zmq_port <= 65_535
        or not 0 < args.camera_port <= 65_535
        or args.camera_index < 0
    ):
        parser.error("frequency, camera index, or port value is invalid")
    if args.left_zmq_port == args.right_zmq_port:
        parser.error("left and right ZeroMQ ports must be different")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    context = zmq.Context()
    sockets = {}
    followers = []
    camera_process = None
    try:
        for side, port in (("left", args.left_zmq_port), ("right", args.right_zmq_port)):
            socket = context.socket(zmq.PULL)
            socket.setsockopt(zmq.CONFLATE, 1)
            socket.setsockopt(zmq.LINGER, 0)
            socket.bind(f"tcp://{args.host}:{port}")
            sockets[side] = socket

        left = SOFollower(SOFollowerRobotConfig(id="follower_left", port=args.left_port))
        right = SOFollower(SOFollowerRobotConfig(id="follower_right", port=args.right_port))
        followers.extend((left, right))
        LOG.info("Connecting follower arms")
        left.connect()
        right.connect()
        LOG.info("Both followers connected; waiting for leader actions")

        camera_script = Path(__file__).resolve().with_name("so101_camera_stream.py")
        camera_process = subprocess.Popen(
            [
                sys.executable,
                str(camera_script),
                "--host",
                args.camera_host,
                "--port",
                str(args.camera_port),
                "--camera",
                str(args.camera_index),
            ]
        )
        LOG.info("Camera stream starting on %s:%d", args.camera_host, args.camera_port)

        poller = zmq.Poller()
        for socket in sockets.values():
            poller.register(socket, zmq.POLLIN)
        period = 1.0 / args.frequency
        count = 0
        while True:
            started = time.perf_counter()
            for socket, _ in poller.poll(timeout=max(1, int(period * 1000))):
                side = next(name for name, candidate in sockets.items() if candidate is socket)
                try:
                    action = json.loads(socket.recv_string())
                    if not isinstance(action, dict):
                        raise ValueError("action must be a JSON object")
                    followers[0 if side == "left" else 1].send_action(action)
                    if side == "left":
                        count += 1
                        if count % 30 == 0:
                            LOG.info("Received %d left-arm actions", count)
                except (ValueError, zmq.ZMQError):
                    LOG.exception("Rejected invalid %s-arm message", side)
            time.sleep(max(period - (time.perf_counter() - started), 0))
    except KeyboardInterrupt:
        LOG.info("Shutting down follower receiver")
    finally:
        if camera_process is not None and camera_process.poll() is None:
            camera_process.send_signal(signal.SIGINT)
            try:
                camera_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                camera_process.terminate()
                camera_process.wait()
        for socket in sockets.values():
            socket.close()
        context.term()
        for follower in reversed(followers):
            if follower.is_connected:
                follower.disconnect()


if __name__ == "__main__":
    main()

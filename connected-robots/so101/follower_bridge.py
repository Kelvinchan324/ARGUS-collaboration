"""SO-101 follower bridge for cockpit status, enable and stop."""

from __future__ import annotations

import argparse
import hmac
import http.server
import ipaddress
import json
import logging
import math
import os
import threading
import time
from typing import Any

LOG = logging.getLogger("argus.so101.bridge")
PROTOCOL = "argus.v1"
ROBOT_ID = "so101"
WATCHDOG_MS = 300
ACTION_TIMEOUT_SECONDS = WATCHDOG_MS / 1000
CONTROL_LEASE_SECONDS = 0.45
JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)


def validate_action(action: Any, expected_keys: set[str]) -> dict[str, float]:
    if not isinstance(action, dict) or set(action) != expected_keys:
        raise ValueError("leader action must contain exactly the follower joint keys")
    validated = {}
    for key, value in action.items():
        if not isinstance(key, str) or not key.endswith(".pos"):
            raise ValueError("leader action contains an unsupported joint")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("leader action values must be finite numbers")
        try:
            number = float(value)
        except OverflowError as exc:
            raise ValueError("leader action values are outside the supported range") from exc
        if not math.isfinite(number):
            raise ValueError("leader action values must be finite numbers")
        lower, upper = (0.0, 100.0) if key == "gripper.pos" else (-180.0, 180.0)
        if not lower <= number <= upper:
            raise ValueError(f"{key} must be between {lower:g} and {upper:g}")
        validated[key] = number
    return validated


class SO101Bridge:
    def __init__(self, left: Any, right: Any, token: str = "") -> None:
        self.robots = {"left": left, "right": right}
        self.expected_keys = {
            side: set(robot.action_features) for side, robot in self.robots.items()
        }
        self.token = token
        self._lock = threading.RLock()
        self._actions: dict[str, dict[str, float] | None] = {"left": None, "right": None}
        self._action_times: dict[str, float] = {"left": 0.0, "right": 0.0}
        self._observations: dict[str, dict[str, float]] = {"left": {}, "right": {}}
        self.enabled = False
        self._enable_until = 0.0

    def _fresh_locked(self, now: float) -> bool:
        return all(
            self._actions[side] is not None
            and now - self._action_times[side] <= ACTION_TIMEOUT_SECONDS
            for side in self.robots
        )

    def accept_leader_action(self, side: str, packet: Any) -> None:
        if side not in self.robots:
            raise ValueError(f"unknown leader side: {side}")
        if not isinstance(packet, dict):
            raise ValueError("leader packet must be an object")
        packet_token = packet.get("token", "")
        if self.token and (
            not isinstance(packet_token, str) or not hmac.compare_digest(packet_token, self.token)
        ):
            raise PermissionError("invalid leader token")
        action = validate_action(packet.get("action"), self.expected_keys[side])
        with self._lock:
            self._actions[side] = action
            self._action_times[side] = time.monotonic()
            if self.enabled and self._fresh_locked(time.monotonic()):
                try:
                    self.robots[side].send_action(action)
                except Exception as exc:
                    raise RuntimeError(f"{side} follower rejected a leader action") from exc

    def refresh_observations(self) -> None:
        with self._lock:
            for side, robot in self.robots.items():
                observation = robot.get_observation()
                self._observations[side] = {
                    key: float(value)
                    for key, value in observation.items()
                    if key in self.expected_keys[side]
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                }

    def _hold_locked(self) -> None:
        for side, robot in self.robots.items():
            observation = robot.get_observation()
            self._observations[side] = {
                key: float(value)
                for key, value in observation.items()
                if key in self.expected_keys[side]
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            }
            observation = self._observations[side]
            hold = {key: observation[key] for key in self.expected_keys[side] if key in observation}
            if set(hold) != self.expected_keys[side]:
                raise RuntimeError(f"could not read every {side} follower joint to hold position")
            robot.send_action(hold)

    def command(self, action: Any) -> None:
        if not isinstance(action, dict) or action.get("action") not in {"enable", "stop"}:
            raise ValueError("only enable and stop commands are supported")
        with self._lock:
            if action["action"] == "stop":
                self.enabled = False
                self._enable_until = 0.0
                self._hold_locked()
                return
            if action.get("enabled") is not True:
                self.enabled = False
                self._enable_until = 0.0
                self._hold_locked()
                return
            if not all(robot.is_connected for robot in self.robots.values()):
                raise ValueError("both follower arms must be connected before enabling")
            if not self._fresh_locked(time.monotonic()):
                raise ValueError("fresh actions from both leader arms are required before enabling")
            self.enabled = True
            self._enable_until = time.monotonic() + CONTROL_LEASE_SECONDS

    def expire_stale_actions(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self.enabled and (
                not self._fresh_locked(now) or now > self._enable_until
            ):
                self.enabled = False
                self._enable_until = 0.0
                self._hold_locked()
                LOG.warning("Leader stream or cockpit lease expired; control locked and poses held")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            connected = all(robot.is_connected for robot in self.robots.values())
            input_fresh = self._fresh_locked(now)
            arms = {}
            for side, joints in self._observations.items():
                ordered = [joints.get(f"{name}.pos") for name in JOINT_NAMES[:5]]
                arms[side] = {
                    "joints": ordered,
                    "gripper": joints.get("gripper.pos"),
                }
            return {
                "protocol": PROTOCOL,
                "robot_id": ROBOT_ID,
                "mode": "hardware",
                "sample_time_ms": int(time.time() * 1000),
                "connected": connected,
                "motor_enabled": self.enabled,
                "watchdog_ms": WATCHDOG_MS,
                "capabilities": {"arms": connected and input_fresh},
                "telemetry": {"arms": arms, "joint_unit": "degrees", "gripper_unit": "%"},
                "task": "Leader teleoperation enabled" if self.enabled else (
                    "Waiting for fresh leader actions" if not input_fresh else "Control locked"
                ),
            }


def make_handler(bridge: SO101Bridge, token: str, cors_origin: str):
    class Handler(http.server.BaseHTTPRequestHandler):
        def _authorized(self) -> bool:
            origin = self.headers.get("Origin")
            if origin and origin != cors_origin:
                self.send_error(403, "Origin not allowed")
                return False
            if token and not hmac.compare_digest(
                self.headers.get("Authorization", ""), f"Bearer {token}"
            ):
                self.send_error(401, "Bearer token required")
                return False
            return True

        def _json(self, status: int, body: dict[str, Any]) -> None:
            encoded = json.dumps(body, allow_nan=False).encode("utf-8")
            self.send_response(status)
            origin = self.headers.get("Origin")
            if origin == cors_origin:
                self.send_header("Access-Control-Allow-Origin", cors_origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_OPTIONS(self) -> None:
            origin = self.headers.get("Origin")
            if origin != cors_origin:
                self.send_error(403, "Origin not allowed")
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Vary", "Origin")
            self.end_headers()

        def do_GET(self) -> None:
            if self.path != "/argus/v1/state":
                self.send_error(404)
                return
            if not self._authorized():
                return
            self._json(200, bridge.snapshot())

        def do_POST(self) -> None:
            if self.path != "/argus/v1/command":
                self.send_error(404)
                return
            if not self._authorized():
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 16_384:
                    raise ValueError("invalid request body size")
                payload = json.loads(self.rfile.read(length))
                bridge.command(payload)
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})
                return
            except Exception as exc:
                LOG.exception("Failed to apply SO-101 command")
                self._json(503, {"ok": False, "error": str(exc)})
                return
            self._json(200, {"ok": True})

        def log_message(self, format: str, *args: Any) -> None:
            LOG.info("HTTP %s - %s", self.address_string(), format % args)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8081)
    parser.add_argument("--zmq-host", default="127.0.0.1")
    parser.add_argument("--left-port", default="/dev/ttyACM0")
    parser.add_argument("--right-port", default="/dev/ttyACM1")
    parser.add_argument("--left-zmq-port", type=int, default=5555)
    parser.add_argument("--right-zmq-port", type=int, default=5556)
    parser.add_argument("--cors-origin", default="http://127.0.0.1:8000")
    parser.add_argument("--max-relative-target", type=float, default=2.0)
    args = parser.parse_args()
    token = os.environ.get("ARGUS_SO101_TOKEN", "")
    for bind_host in (args.host, args.zmq_host):
        try:
            remote = not ipaddress.ip_address(bind_host).is_loopback
        except ValueError:
            remote = bind_host not in {"localhost"}
        if remote and not token:
            parser.error("ARGUS_SO101_TOKEN is required when binding to a non-loopback interface")
    if args.max_relative_target <= 0:
        parser.error("--max-relative-target must be positive")
    if not math.isfinite(args.max_relative_target):
        parser.error("--max-relative-target must be finite")
    if any(not 0 < port <= 65_535 for port in (
        args.http_port, args.left_zmq_port, args.right_zmq_port
    )):
        parser.error("all TCP ports must be between 1 and 65535")

    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    from lerobot.robots.so_follower.so_follower import SOFollower
    import zmq

    followers = {
        "left": SOFollower(
            SOFollowerRobotConfig(
                id="follower_left", port=args.left_port, max_relative_target=args.max_relative_target
            )
        ),
        "right": SOFollower(
            SOFollowerRobotConfig(
                id="follower_right", port=args.right_port, max_relative_target=args.max_relative_target
            )
        ),
    }
    context = zmq.Context()
    sockets = {}
    server = None
    try:
        for side, port in (("left", args.left_zmq_port), ("right", args.right_zmq_port)):
            socket = context.socket(zmq.PULL)
            socket.setsockopt(zmq.CONFLATE, 1)
            socket.setsockopt(zmq.LINGER, 0)
            socket.bind(f"tcp://{args.zmq_host}:{port}")
            sockets[side] = socket
        for follower in followers.values():
            follower.connect()
        bridge = SO101Bridge(followers["left"], followers["right"], token)
        server = http.server.ThreadingHTTPServer(
            (args.host, args.http_port), make_handler(bridge, token, args.cors_origin)
        )
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        LOG.info("SO-101 ARGUS bridge listening on %s:%s", args.host, args.http_port)
        poller = zmq.Poller()
        for socket in sockets.values():
            poller.register(socket, zmq.POLLIN)
        last_observation = 0.0
        while True:
            for socket, _ in poller.poll(20):
                side = next(name for name, candidate in sockets.items() if candidate is socket)
                try:
                    packet = json.loads(socket.recv_string())
                    bridge.accept_leader_action(side, packet)
                except (ValueError, PermissionError) as exc:
                    LOG.warning("Rejected %s leader packet: %s", side, exc)
                except Exception:
                    try:
                        bridge.command({"action": "stop"})
                    except Exception:
                        LOG.exception("Could not hold follower arms after an action failure")
                    LOG.exception("Failed to apply %s leader action; control locked", side)
            try:
                bridge.expire_stale_actions()
            except Exception:
                LOG.exception("Could not hold the follower arms after leader input expired")
            if time.monotonic() - last_observation >= 0.2:
                try:
                    bridge.refresh_observations()
                except Exception:
                    try:
                        bridge.command({"action": "stop"})
                    except Exception:
                        LOG.exception("Could not hold follower arms after a state-read failure")
                    LOG.exception("Failed to read follower state; control locked")
                last_observation = time.monotonic()
    except KeyboardInterrupt:
        LOG.info("Stopping SO-101 bridge")
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if "bridge" in locals():
            try:
                bridge.command({"action": "stop"})
            except Exception:
                LOG.exception("Failed to hold follower arms during shutdown")
        for socket in sockets.values():
            socket.close()
        context.term()
        for follower in reversed(list(followers.values())):
            if follower.is_connected:
                follower.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    main()

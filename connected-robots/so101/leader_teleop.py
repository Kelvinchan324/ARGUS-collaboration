"""Read SO-101 leader arms and stream their actions to an ARGUS follower bridge."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time

import zmq
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
from lerobot.teleoperators.so_leader.so_leader import SOLeader

LOG = logging.getLogger("argus.so101.leader")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--follower-host", required=True)
    parser.add_argument("--left-port", default="/dev/ttyACM1")
    parser.add_argument("--right-port", default="/dev/ttyACM0")
    parser.add_argument("--left-zmq-port", type=int, default=5555)
    parser.add_argument("--right-zmq-port", type=int, default=5556)
    parser.add_argument("--frequency", type=float, default=30.0)
    args = parser.parse_args()
    if args.frequency <= 0:
        parser.error("--frequency must be positive")

    token = os.environ.get("ARGUS_SO101_TOKEN", "")
    context = zmq.Context()
    left_socket = context.socket(zmq.PUSH)
    right_socket = context.socket(zmq.PUSH)
    for socket in (left_socket, right_socket):
        socket.setsockopt(zmq.CONFLATE, 1)
        socket.setsockopt(zmq.LINGER, 0)
    left_socket.connect(f"tcp://{args.follower_host}:{args.left_zmq_port}")
    right_socket.connect(f"tcp://{args.follower_host}:{args.right_zmq_port}")

    leaders: list[SOLeader] = []
    try:
        left = SOLeader(SOLeaderTeleopConfig(port=args.left_port, id="lead_l"))
        right = SOLeader(SOLeaderTeleopConfig(port=args.right_port, id="lead_r"))
        leaders.extend((left, right))
        for leader in leaders:
            leader.connect()
        LOG.info("Both SO-101 leader arms connected")

        period = 1.0 / args.frequency
        while True:
            started = time.perf_counter()
            left_action = left.get_action()
            right_action = right.get_action()
            left_socket.send_string(json.dumps({"token": token, "action": left_action}))
            right_socket.send_string(json.dumps({"token": token, "action": right_action}))
            time.sleep(max(0.0, period - (time.perf_counter() - started)))
    except KeyboardInterrupt:
        LOG.info("Stopping leader teleoperation")
    finally:
        for leader in reversed(leaders):
            if leader.is_connected:
                leader.disconnect()
        left_socket.close()
        right_socket.close()
        context.term()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    main()

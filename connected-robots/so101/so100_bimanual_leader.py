"""Read two SO-101 leader arms and send their joint actions to the followers."""

from __future__ import annotations

import argparse
import json
import logging
import time

import zmq
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
from lerobot.teleoperators.so_leader.so_leader import SOLeader

LOG = logging.getLogger("so101.leader")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--follower-host", required=True)
    parser.add_argument("--left-port", default="/dev/ttyACM1", help="left leader serial device")
    parser.add_argument("--right-port", default="/dev/ttyACM0", help="right leader serial device")
    parser.add_argument("--left-zmq-port", type=int, default=5555)
    parser.add_argument("--right-zmq-port", type=int, default=5556)
    parser.add_argument("--frequency", type=float, default=30.0)
    args = parser.parse_args()
    if args.frequency <= 0 or not 0 < args.left_zmq_port <= 65_535 or not 0 < args.right_zmq_port <= 65_535:
        parser.error("frequency must be positive and ZeroMQ ports must be between 1 and 65535")
    if args.left_zmq_port == args.right_zmq_port:
        parser.error("left and right ZeroMQ ports must be different")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    leaders: list[SOLeader] = []
    context = zmq.Context()
    left_socket = context.socket(zmq.PUSH)
    right_socket = context.socket(zmq.PUSH)
    for socket in (left_socket, right_socket):
        socket.setsockopt(zmq.CONFLATE, 1)
        socket.setsockopt(zmq.LINGER, 0)
    left_socket.connect(f"tcp://{args.follower_host}:{args.left_zmq_port}")
    right_socket.connect(f"tcp://{args.follower_host}:{args.right_zmq_port}")

    try:
        left = SOLeader(SOLeaderTeleopConfig(port=args.left_port, id="lead_r"))
        right = SOLeader(SOLeaderTeleopConfig(port=args.right_port, id="lead_l"))
        leaders.extend((left, right))
        LOG.info("Connecting leader arms")
        left.connect()
        right.connect()
        LOG.info("Both leaders connected to follower at %s", args.follower_host)

        period = 1.0 / args.frequency
        count = 0
        while True:
            started = time.perf_counter()
            left_socket.send_string(json.dumps(left.get_action()))
            right_socket.send_string(json.dumps(right.get_action()))
            count += 1
            if count % 30 == 0:
                LOG.info("Sent %d action pairs", count)
            time.sleep(max(period - (time.perf_counter() - started), 0))
    except KeyboardInterrupt:
        LOG.info("Shutting down leader teleoperation")
    finally:
        for leader in reversed(leaders):
            if leader.is_connected:
                leader.disconnect()
        left_socket.close()
        right_socket.close()
        context.term()


if __name__ == "__main__":
    main()

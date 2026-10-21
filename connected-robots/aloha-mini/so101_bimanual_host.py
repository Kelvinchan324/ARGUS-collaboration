import time
import json
import logging
from pathlib import Path
import signal
import subprocess
import sys
import zmq
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

logging.basicConfig(level=logging.INFO)

PORT_LEFT = 5555
PORT_RIGHT = 5556
FREQ = 30
CAMERA_INDEX = 0  # Change to 2, 4, or 6 to test another camera.

print("Setting up ZMQ...")
ctx = zmq.Context()

cmd_sock_left = ctx.socket(zmq.PULL)
cmd_sock_left.setsockopt(zmq.CONFLATE, 1)
cmd_sock_left.bind(f"tcp://*:{PORT_LEFT}")

cmd_sock_right = ctx.socket(zmq.PULL)
cmd_sock_right.setsockopt(zmq.CONFLATE, 1)
cmd_sock_right.bind(f"tcp://*:{PORT_RIGHT}")
print("ZMQ ready!")

print("Connecting follower arms...")
config_left = SOFollowerRobotConfig(id="follower_l", port="/dev/ttyACM0")
config_right = SOFollowerRobotConfig(id="follower_r", port="/dev/ttyACM1")
robot_left = SOFollower(config_left)
robot_right = SOFollower(config_right)
robot_left.connect()
robot_right.connect()
print("Both followers connected! Waiting for commands...")

msg_count = 0
camera_process = None
try:
    camera_script = Path(__file__).resolve().with_name("camera_stream_host.py")
    camera_process = subprocess.Popen(
        [sys.executable, str(camera_script), "--camera-index", str(CAMERA_INDEX)]
    )
    print(
        f"Streaming camera index {CAMERA_INDEX} at http://<robot-ip>:8000/",
        flush=True,
    )
    while True:
        start = time.perf_counter()
        try:
            msg = cmd_sock_left.recv_string(flags=zmq.NOBLOCK)
            action = json.loads(msg)
            msg_count += 1
            if msg_count % 30 == 0:
                print(f"Actions received: {msg_count}")
            robot_left.send_action(action)
        except zmq.Again:
            pass
        except Exception as e:
            print(f"Left error: {e}")
        try:
            msg = cmd_sock_right.recv_string(flags=zmq.NOBLOCK)
            action = json.loads(msg)
            robot_right.send_action(action)
        except zmq.Again:
            pass
        except Exception as e:
            print(f"Right error: {e}")
        elapsed = time.perf_counter() - start
        time.sleep(max(1.0 / FREQ - elapsed, 0))
except KeyboardInterrupt:
    print(f"Shutting down. Total: {msg_count}")
finally:
    if camera_process is not None:
        if camera_process.poll() is None:
            camera_process.send_signal(signal.SIGINT)
            try:
                camera_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                camera_process.terminate()
                camera_process.wait()
    try:
        robot_left.disconnect()
        robot_right.disconnect()
    except:
        pass
    cmd_sock_left.close()
    cmd_sock_right.close()
    ctx.term()

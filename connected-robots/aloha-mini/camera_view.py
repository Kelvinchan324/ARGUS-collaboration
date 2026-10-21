#!/usr/bin/env python3
"""
Multi-Camera Viewer for 5 USB Cameras – Full Screen + Status Panel
Bottom‑middle cell shows robot status from /tmp/robot_status.json
Press ESC to exit, F to toggle full screen.
"""

import cv2
import numpy as np
import sys
import time
import json
import os
from camera_devices import find_usb_cameras

# ---------- CONFIGURATION ----------
CAMERA_DEVICES = find_usb_cameras()

FRAME_ORDER = [0, 1, 2, 3, 5]   # skip cell 4 (mid‑center)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
GRID_COLS = 3
GRID_ROWS = 2
WARMUP_FRAMES = 5
BLACK_THRESHOLD = 10
STATUS_FILE = "/tmp/robot_status.json"
# -----------------------------------

def open_camera(device_path):
    cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"❌ Cannot open {device_path}")
        return None
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    for _ in range(WARMUP_FRAMES):
        ret, _ = cap.read()
        if not ret:
            print(f"⚠️ {device_path} failed warm‑up")
            cap.release()
            return None
        time.sleep(0.05)
    actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"✅ {device_path} opened at {actual_w}x{actual_h}")
    return cap

def is_black(frame, threshold=BLACK_THRESHOLD):
    return frame.mean() < threshold

def get_robot_status():
    """Read status from JSON file, return formatted text lines."""
    try:
        with open(STATUS_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return ["No status", "Waiting for robot..."]

    lines = []
    lines.append(f"Mode: {data.get('mode', '?')}")
    lines.append(f"Actuator: {data.get('actuator_current', 0):.0f} mA")
    lines.append(f"Estop: {'ACTIVE' if data.get('emergency_stop', False) else 'OFF'}")
    lines.append(f"Overcurrent: {'LOCKED' if data.get('overcurrent', False) else 'OK'}")
    # Optional: laser mode indicator
    if data.get('laser_mode', False):
        lines.append("Laser Mode ON")
    return lines

def draw_status_panel(canvas, x, y, w, h):
    """Draw the robot status panel in the given cell."""
    # Fill background (dark grey)
    cv2.rectangle(canvas, (x, y), (x+w, y+h), (40, 40, 40), -1)
    # Border
    cv2.rectangle(canvas, (x, y), (x+w, y+h), (200, 200, 200), 2)
    # Title
    cv2.putText(canvas, "ROBOT STATUS", (x+10, y+30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Get status lines
    lines = get_robot_status()
    y_offset = y + 70
    for line in lines:
        cv2.putText(canvas, line, (x+15, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y_offset += 30

def create_grid(frames, grid_rows, grid_cols, cell_w, cell_h, device_paths, frame_order):
    total_cells = grid_rows * grid_cols
    canvas = np.zeros((grid_rows * cell_h, grid_cols * cell_w, 3), dtype=np.uint8)
    cell_frames = [None] * total_cells
    for cam_idx, frame in enumerate(frames):
        if cam_idx < len(frame_order):
            target_pos = frame_order[cam_idx]
            if 0 <= target_pos < total_cells:
                cell_frames[target_pos] = frame
    for cell_idx in range(total_cells):
        row = cell_idx // grid_cols
        col = cell_idx % grid_cols
        y = row * cell_h
        x = col * cell_w
        frame = cell_frames[cell_idx]
        if frame is None or is_black(frame):
            # Empty cell – put status panel in cell index 4 (mid‑center)
            if cell_idx == 4:   # bottom middle
                draw_status_panel(canvas, x, y, cell_w, cell_h)
            else:
                cv2.putText(canvas, "No Signal", (x+10, y+cell_h//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            continue
        resized = cv2.resize(frame, (cell_w, cell_h))
        canvas[y:y+cell_h, x:x+cell_w] = resized
        short_name = device_paths[cam_idx].split('/')[-1] if cam_idx < len(device_paths) else f"cam{cell_idx}"
        cv2.putText(canvas, short_name, (x+10, y+30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    return canvas

def main():
    print("Opening cameras (this may take a few seconds)...")
    caps = []
    for dev in CAMERA_DEVICES:
        cap = open_camera(dev)
        caps.append(cap)

    active_count = sum(1 for c in caps if c is not None)
    if active_count == 0:
        print("No cameras could be opened. Exiting.")
        sys.exit(1)
    print(f"Successfully opened {active_count}/{len(CAMERA_DEVICES)} cameras.")

    window = "Robot Multi-Camera View"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    time.sleep(0.2)   # allow window to be created

    fullscreen = True

    while True:
        frames = []
        for cap in caps:
            if cap is None:
                frames.append(None)
                continue
            ret, frame = cap.read()
            frames.append(frame if ret else None)

        grid = create_grid(frames, GRID_ROWS, GRID_COLS,
                           FRAME_WIDTH, FRAME_HEIGHT,
                           CAMERA_DEVICES, FRAME_ORDER)
        cv2.imshow(window, grid)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:   # ESC
            break
        elif key == ord('f') or key == ord('F'):
            fullscreen = not fullscreen
            if fullscreen:
                cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            else:
                cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window, 1280, 720)

    for cap in caps:
        if cap is not None:
            cap.release()
    cv2.destroyAllWindows()
    print("Camera view exited.")

if __name__ == "__main__":
    main()

"""Shared USB camera configuration; no robot or calibration dependencies."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def camera_source(value: str) -> int | str:
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("camera source must not be empty")
    try:
        number = int(value)
    except ValueError:
        return value
    if number < 0:
        raise argparse.ArgumentTypeError("camera index must be nonnegative")
    return number


def source_identity(source: int | str) -> str:
    """Resolve Linux indices and stable links so one device is not opened twice."""
    if isinstance(source, int):
        return str(Path(f"/dev/video{source}").resolve()) if sys.platform.startswith("linux") else str(source)
    return str(Path(source).resolve())


def validate_sources(values: list[str]) -> None:
    identities = [source_identity(camera_source(value)) for value in values]
    if len(identities) != len(set(identities)):
        raise ValueError("Each camera must use a different capture device (including aliases)")


def open_capture(source: int | str, width: int, height: int, fps: int):
    import cv2

    capture = cv2.VideoCapture(source, cv2.CAP_V4L2) if sys.platform.startswith("linux") else cv2.VideoCapture(source)
    try:
        if not capture.isOpened():
            raise RuntimeError(f"Could not open camera {source!r}; check ID, permissions, or whether it is busy")
        # Request compressed USB transport before size/rate to reduce USB bandwidth.
        # These are requests: the driver may negotiate different values.
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        capture.set(cv2.CAP_PROP_FPS, fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return capture
    except Exception:
        capture.release()
        raise

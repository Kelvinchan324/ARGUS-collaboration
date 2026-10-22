"""Find camera IDs/paths that actually return frames, without connecting to arms.

Run with the follower's LeRobot Python. Stop the camera service before probing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from so101_camera_utils import camera_source, open_capture, positive_int, source_identity


def candidates(max_index: int = 9, device_root: Path = Path("/dev")) -> list[dict]:
    if not sys.platform.startswith("linux"):
        return [{"source": str(index), "aliases": []} for index in range(max_index + 1)]
    # Group stable symlinks and numbered nodes by the same underlying device.
    # Prefer by-id (serial number), then by-path (physical USB socket).
    groups: dict[str, dict] = {}
    paths = [*sorted((device_root / "v4l/by-id").glob("*")),
             *sorted((device_root / "v4l/by-path").glob("*")),
             *sorted(device_root.glob("video*"))]
    for path in paths:
        if not path.exists() or not path.resolve().name.removeprefix("video").isdigit():
            continue
        identity = str(path.resolve())
        if identity not in groups:
            groups[identity] = {"source": str(path), "aliases": []}
        groups[identity]["aliases"].append(str(path))
    return list(groups.values())


def probe(source: str, width: int, height: int, fps: int, snapshot: str | None) -> dict:
    import cv2

    capture = None
    try:
        capture = open_capture(camera_source(source), width, height, fps)
        frames = 0
        frame = None
        for _ in range(12):
            ok, image = capture.read()
            if ok and image is not None and image.size:
                frames += 1
                frame = image
                if frames >= 3:
                    break
        if frames < 3:
            raise RuntimeError("Opened but did not deliver 3 frames (metadata node, busy device, or USB issue)")
        result = {"usable": True, "resolution": [int(frame.shape[1]), int(frame.shape[0])],
                  "reported_fps": capture.get(cv2.CAP_PROP_FPS), "frames_read": frames}
        if snapshot:
            if not cv2.imwrite(snapshot, frame):
                raise RuntimeError(f"Could not save snapshot: {snapshot}")
            result["snapshot"] = snapshot
        return result
    except Exception as exc:
        return {"usable": False, "error": str(exc)}
    finally:
        if capture is not None:
            capture.release()


def bounded_probe(source: str, args, snapshot: str | None) -> dict:
    command = [sys.executable, str(Path(__file__).resolve()), "--probe", source,
               "--width", str(args.width), "--height", str(args.height), "--fps", str(args.fps)]
    if snapshot:
        command.extend(["--snapshot-file", snapshot])
    try:
        # OpenCV reads can hang in a device driver. Probe each camera in its own
        # process so one bad /dev/video node cannot hang the entire search.
        result = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout, check=False)
        if result.returncode != 0:
            return {"usable": False, "error": f"Probe exited with status {result.returncode}"}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"usable": False, "error": f"No response within {args.timeout}s"}
    except (ValueError, OSError) as exc:
        return {"usable": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", nargs="+", help="probe specific indices or /dev paths instead of searching")
    parser.add_argument("--max-index", type=int, default=9, help="highest index to scan on non-Linux systems")
    parser.add_argument("--width", type=positive_int, default=640)
    parser.add_argument("--height", type=positive_int, default=480)
    parser.add_argument("--fps", type=positive_int, default=15)
    parser.add_argument("--timeout", type=positive_int, default=8, help="maximum seconds per probe")
    parser.add_argument("--snapshots", action="store_true", help="save a JPEG for identifying each usable camera")
    parser.add_argument("--snapshot-dir", type=Path, default=Path(__file__).resolve().parent / "camera-snapshots")
    parser.add_argument("--json", action="store_true", help="print the complete report as JSON")
    parser.add_argument("--probe", help=argparse.SUPPRESS)
    parser.add_argument("--snapshot-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.max_index < 0:
        parser.error("--max-index must be nonnegative")
    if importlib.util.find_spec("cv2") is None:
        parser.error("OpenCV is missing. Run this script with lerobot/.venv/bin/python (the streaming environment).")
    if args.probe is not None:
        print(json.dumps(probe(args.probe, args.width, args.height, args.fps, args.snapshot_file)))
        return 0
    if args.camera:
        try:
            devices = []
            seen = set()
            for source in args.camera:
                identity = source_identity(camera_source(source))
                if identity not in seen:
                    devices.append({"source": source, "aliases": []})
                    seen.add(identity)
        except argparse.ArgumentTypeError as exc:
            parser.error(str(exc))
    else:
        devices = candidates(args.max_index)
    if args.snapshots:
        args.snapshot_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, device in enumerate(devices):
        if not args.json:
            print(f"Testing {device['source']} ...", flush=True)
        snapshot = str((args.snapshot_dir / f"camera-{index}.jpg").resolve()) if args.snapshots else None
        results.append(dict(device, **bounded_probe(device["source"], args, snapshot)))
    if args.json:
        print(json.dumps({"cameras": results}, indent=2))
    else:
        print("\nCamera discovery (no arms connected or calibrated):")
        for device in results:
            if device["usable"]:
                width, height = device["resolution"]
                print(f"  OK    {device['source']}  {width}x{height}, driver reports {device['reported_fps']:g} FPS")
                if device["aliases"]:
                    print(f"        aliases: {', '.join(device['aliases'])}")
                if device.get("snapshot"):
                    print(f"        image: {device['snapshot']}")
            else:
                print(f"  FAIL  {device['source']}  {device['error']}")
        print("\nMap the verified devices to SO101_CAMERA_TOP / SO101_CAMERA_LEFT / SO101_CAMERA_RIGHT.")
        print("Use the snapshots or cover each lens to identify its position; IDs cannot identify physical placement.")
        print("Stop other camera apps before testing. Individual success does not prove three-camera USB bandwidth.")
    return 0 if any(device["usable"] for device in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

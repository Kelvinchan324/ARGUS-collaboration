"""Aloha Mini identity for the shared SO-101 ARGUS arm bridge."""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    if "--robot-id" in sys.argv or any(arg.startswith("--robot-id=") for arg in sys.argv):
        raise SystemExit("Aloha entry point fixes --robot-id to aloha-mini")
    runtime = Path(__file__).resolve().parents[1] / "so101"
    sys.path.insert(0, str(runtime))
    sys.argv.extend(["--robot-id", "aloha-mini"])
    runpy.run_path(str(runtime / "follower_bridge.py"), run_name="__main__")

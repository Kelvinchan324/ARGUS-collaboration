"""Aloha Mini entry point for the shared, user-tested direct receiver."""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    runtime = Path(__file__).resolve().parents[1] / "so101"
    sys.path.insert(0, str(runtime))
    runpy.run_path(str(runtime / "so101_bimanual_receiver.py"), run_name="__main__")

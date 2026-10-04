"""Build the ARGUS Pages artifact from public, source-verified assets."""
import argparse
import shutil
from pathlib import Path


def build(output: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    video = root / "connected-robots/bimanual-bunker-mini/media/Industrial_Inspection_Demo.mp4"
    if not video.is_file():
        raise FileNotFoundError(f"Missing concept video: {video}")
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")

    shutil.copytree(root / "docs", output)
    shutil.copytree(root / "cockpit/web", output / "control")
    video_target = output / "connected-robots/bimanual-bunker-mini/media"
    video_target.mkdir(parents=True)
    shutil.copy2(video, video_target / video.name)
    print(f"Website ready: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output.resolve())

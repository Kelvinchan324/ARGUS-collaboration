"""Publish robot assets from their canonical adaptor folder without Git duplicates."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def build(output):
    root = Path(__file__).resolve().parents[1]
    robot = root / "connected-robots/bimanual-bunker-mini"
    manifest = json.loads((robot / "asset-manifest.json").read_text(encoding="utf-8-sig"))
    for asset in manifest["assets"]:
        path = robot / asset["path"]
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if path.stat().st_size != asset["bytes"] or digest != asset["sha256"]:
            raise ValueError(f"Asset mismatch: {asset['path']}. Retrieve full assets with git lfs pull.")
    # Require a fresh directory to prevent stale downloads or accidental overwrites.
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    shutil.copytree(root / "docs", output)
    shutil.copytree(robot, output / "connected-robots" / robot.name)
    downloads = output / "downloads"
    downloads.mkdir()
    with zipfile.ZipFile(downloads / f"{robot.name}.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(robot.rglob("*")):
            if path.is_file():
                archive.write(path, Path(robot.name) / path.relative_to(robot))
    print(f"Website and complete adaptor archive ready: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output.resolve())

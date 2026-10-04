"""Small dependency-free checks used locally and in GitHub Actions."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/architecture/overview.md",
    "docs/robots/README.md",
    "third_party/dependencies.json",
)
FORBIDDEN_TRACKED_NAMES = {".env", "credentials.json", "secrets.json"}


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    dependency_file = ROOT / "third_party/dependencies.json"
    try:
        data = json.loads(dependency_file.read_text(encoding="utf-8"))
        names: set[str] = set()
        for dependency in data["dependencies"]:
            name = dependency["name"]
            if name in names:
                errors.append(f"duplicate dependency: {name}")
            names.add(name)
            if not dependency["repository"].startswith("https://github.com/"):
                errors.append(f"dependency is not an HTTPS GitHub URL: {name}")
            pin = dependency.get("pinned_commit")
            if pin is not None and not re.fullmatch(r"[0-9a-f]{40}", pin):
                errors.append(f"pinned_commit must be a full SHA or null: {name}")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid dependency register: {exc}")

    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.name.lower() in FORBIDDEN_TRACKED_NAMES:
            errors.append(f"possible secret file present: {path.relative_to(ROOT)}")
        if path.stat().st_size > 100 * 1024 * 1024:
            errors.append(f"file exceeds 100 MiB: {path.relative_to(ROOT)}")

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

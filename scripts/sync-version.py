#!/usr/bin/env python3
"""Sync VERSION file to all package manifests across the monorepo.

Reads the version from the root VERSION file and updates:
  - backend/pyproject.toml
  - backend/omoi_os/api/main.py (FastAPI app version)
  - frontend/package.json
  - subsystems/spec-sandbox/pyproject.toml
  - subsystems/spec-sandbox/src/spec_sandbox/cli.py
  - tools/resmgr/Cargo.toml
  - landing-pages/package.json

Usage:
    python scripts/sync-version.py           # Sync from VERSION file
    python scripts/sync-version.py --check   # Check if all files are in sync
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "VERSION"

# Files to sync and their replacement patterns.
# Each entry: (relative_path, regex_pattern, replacement_template)
# The regex must have a capture group around the version string.
TARGETS: list[tuple[str, str, str]] = [
    # pyproject.toml files: version = "X.Y.Z"
    (
        "backend/pyproject.toml",
        r'^(version\s*=\s*")[^"]*(")',
        r"\g<1>{version}\2",
    ),
    (
        "subsystems/spec-sandbox/pyproject.toml",
        r'^(version\s*=\s*")[^"]*(")',
        r"\g<1>{version}\2",
    ),
    # Cargo.toml: version = "X.Y.Z"
    (
        "tools/resmgr/Cargo.toml",
        r'^(version\s*=\s*")[^"]*(")',
        r"\g<1>{version}\2",
    ),
    # Click version option: @click.version_option(version="X.Y.Z")
    (
        "subsystems/spec-sandbox/src/spec_sandbox/cli.py",
        r'(@click\.version_option\(version=")[^"]*(")',
        r"\g<1>{version}\2",
    ),
]

# JSON files: update the top-level "version" field
JSON_TARGETS: list[str] = [
    "frontend/package.json",
    "landing-pages/package.json",
]


def read_version() -> str:
    """Read version from the VERSION file."""
    if not VERSION_FILE.exists():
        print(f"ERROR: {VERSION_FILE} not found", file=sys.stderr)
        sys.exit(1)
    return VERSION_FILE.read_text().strip()


def sync_text_file(path: Path, pattern: str, replacement: str, version: str) -> bool:
    """Replace version in a text file using regex. Returns True if changed."""
    if not path.exists():
        print(f"  SKIP  {path.relative_to(REPO_ROOT)} (file not found)")
        return False

    content = path.read_text()
    new_content = re.sub(
        pattern,
        replacement.format(version=version),
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if content == new_content:
        print(f"  OK    {path.relative_to(REPO_ROOT)}")
        return False

    path.write_text(new_content)
    print(f"  SYNC  {path.relative_to(REPO_ROOT)}")
    return True


def sync_json_file(path: Path, version: str) -> bool:
    """Update the 'version' field in a JSON file. Returns True if changed."""
    if not path.exists():
        print(f"  SKIP  {path.relative_to(REPO_ROOT)} (file not found)")
        return False

    content = path.read_text()
    data = json.loads(content)

    if data.get("version") == version:
        print(f"  OK    {path.relative_to(REPO_ROOT)}")
        return False

    # Use regex to preserve formatting (don't rewrite the whole file)
    new_content = re.sub(
        r'("version"\s*:\s*")[^"]*(")',
        rf"\g<1>{version}\2",
        content,
        count=1,
    )
    path.write_text(new_content)
    print(f"  SYNC  {path.relative_to(REPO_ROOT)}")
    return True


def check_mode(version: str) -> bool:
    """Check if all files are in sync. Returns True if all match."""
    all_ok = True

    for rel_path, pattern, _ in TARGETS:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        content = path.read_text()
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            file_version = content[
                match.start(1)
                + len(match.group(1).rstrip('"').rstrip("'")) : match.end(1)
            ]
            # Simpler: just check if the version string appears in the match
            if version not in match.group(0):
                print(
                    f"  DRIFT {path.relative_to(REPO_ROOT)}: found {match.group(0).strip()}"
                )
                all_ok = False
            else:
                print(f"  OK    {path.relative_to(REPO_ROOT)}")

    for rel_path in JSON_TARGETS:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        file_version = data.get("version", "???")
        if file_version != version:
            print(f"  DRIFT {path.relative_to(REPO_ROOT)}: {file_version}")
            all_ok = False
        else:
            print(f"  OK    {path.relative_to(REPO_ROOT)}")

    return all_ok


def main() -> None:
    check = "--check" in sys.argv
    version = read_version()

    print(f"Version: {version}")
    print()

    if check:
        ok = check_mode(version)
        if not ok:
            print("\nVersion drift detected. Run: just sync-version")
            sys.exit(1)
        else:
            print("\nAll files in sync.")
        return

    changed = 0
    for rel_path, pattern, replacement in TARGETS:
        if sync_text_file(REPO_ROOT / rel_path, pattern, replacement, version):
            changed += 1

    for rel_path in JSON_TARGETS:
        if sync_json_file(REPO_ROOT / rel_path, version):
            changed += 1

    print()
    if changed:
        print(f"Updated {changed} file(s).")
    else:
        print("All files already in sync.")


if __name__ == "__main__":
    main()

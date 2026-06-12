#!/usr/bin/env python3
"""Post-release steps for the neo4j-viz package.

After a release has been published, this:
  1. Bumps the version in python-wrapper/pyproject.toml.
  2. Resets changelog.md to an empty template for the next cycle.

The old changelog content is the release notes for the version just shipped,
so it is cleared once released.

Usage:
    python scripts/release/postrelease.py [--part {major,minor,patch}]
    python scripts/release/postrelease.py --set X.Y.Z

Defaults to a minor bump. Edits files only; commit the result yourself.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import PACKAGE, bold, green, git_root, pyproject_path, read_version

CHANGELOG_TEMPLATE = """# Changes

## Breaking changes

## New features

## Bug fixes

## Improvements

## Other changes
"""


def parse_version(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise SystemExit(f"ERROR: cannot parse version '{version}' as MAJOR.MINOR.PATCH")
    major, minor, patch = (int(g) for g in match.groups())
    return major, minor, patch


def bump(version: str, part: str) -> str:
    major, minor, patch = parse_version(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def write_version(pyproject: Path, old: str, new: str) -> None:
    text = pyproject.read_text()
    pattern = re.compile(rf'^version = "{re.escape(old)}"$', re.MULTILINE)
    new_text, count = pattern.subn(f'version = "{new}"', text)
    if count != 1:
        raise SystemExit(
            f"ERROR: expected exactly one 'version = \"{old}\"' line in {pyproject}, found {count}."
        )
    pyproject.write_text(new_text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-release version bump and changelog reset.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--part",
        choices=["major", "minor", "patch"],
        default="minor",
        help="Which part of the version to bump (default: minor).",
    )
    group.add_argument(
        "--set",
        dest="set_version",
        metavar="X.Y.Z",
        help="Set an explicit next version instead of bumping.",
    )
    args = parser.parse_args()

    root = git_root()
    pyproject = pyproject_path(root)
    changelog = root / "changelog.md"

    current = read_version(root)
    if args.set_version:
        parse_version(args.set_version)  # validate format
        new_version = args.set_version
    else:
        new_version = bump(current, args.part)

    print(bold(f"Bumping {PACKAGE}: {current} -> {new_version}"))
    write_version(pyproject, current, new_version)
    print(green(f"OK: updated version in {pyproject.relative_to(root)}"))

    changelog.write_text(CHANGELOG_TEMPLATE)
    print(green(f"OK: reset {changelog.relative_to(root)} to an empty template"))

    print(bold("Post-release done. Review the changes and commit them."))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Shared helpers for the release scripts (prerelease.py, postrelease.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    raise SystemExit("The release scripts require Python 3.11+ (for tomllib).")

import tomllib  # Python 3.11+


PACKAGE = "neo4j-viz"
MAIN_BRANCH = "main"


def _color(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def red(text: str) -> str:
    return _color("0;31", text)


def green(text: str) -> str:
    return _color("0;32", text)


def bold(text: str) -> str:
    return _color("1", text)


def git_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(out.stdout.strip())


def pyproject_path(root: Path | None = None) -> Path:
    return (root or git_root()) / "python-wrapper" / "pyproject.toml"


def read_version(root: Path | None = None) -> str:
    with pyproject_path(root).open("rb") as f:
        data = tomllib.load(f)
    version: str = data["project"]["version"]
    return version

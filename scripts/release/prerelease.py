#!/usr/bin/env python3
"""Pre-release checks for the neo4j-viz package.

Verifies that:
  1. The version about to be released is printed.
  2. changelog.md has at least one entry.
  3. That version is not already published on PyPI.
  4. All GitHub Actions runs on the latest commit of the main branch passed.

Requires: gh (authenticated) on PATH. Run from anywhere inside the repo.

When run inside GitHub Actions (i.e. GITHUB_OUTPUT is set), it also writes
`version` and `sha` outputs so the release workflow can reuse them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

from _common import (
    MAIN_BRANCH,
    PACKAGE,
    bold,
    git_root,
    green,
    read_version,
    red,
)

# Conclusions that do not block a release.
_OK_CONCLUSIONS = {"success", "neutral", "skipped"}


def is_on_pypi(version: str) -> bool:
    """Return True if PACKAGE==version is already published on PyPI."""
    url = f"https://pypi.org/pypi/{PACKAGE}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return bool(resp.status == 200)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise SystemExit(
            red(
                f"ERROR: Unexpected response from PyPI (HTTP {exc.code}) for {PACKAGE} {version}."
            )
        )
    except urllib.error.URLError as exc:
        raise SystemExit(red(f"ERROR: Could not reach PyPI: {exc.reason}"))


def _gh(args: list[str]) -> str:
    try:
        out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(
            red("ERROR: 'gh' CLI not found. Install it and run 'gh auth login'.")
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            red(f"ERROR: gh {' '.join(args)} failed:\n{exc.stderr.strip()}")
        )
    return out.stdout


def latest_main_sha() -> str:
    out = _gh(
        ["api", f"repos/{{owner}}/{{repo}}/commits/{MAIN_BRANCH}", "--jq", ".sha"]
    )
    return out.strip()


def workflow_runs(sha: str) -> list[dict[str, Any]]:
    """Workflow runs for `sha`, excluding the current run when on GitHub Actions."""
    out = _gh(
        [
            "run",
            "list",
            "--commit",
            sha,
            "--limit",
            "100",
            "--json",
            "databaseId,workflowName,status,conclusion",
        ]
    )
    runs: list[dict[str, Any]] = json.loads(out)
    current = os.environ.get("GITHUB_RUN_ID")
    if current:
        runs = [r for r in runs if str(r.get("databaseId")) != current]
    return runs


def check_changelog() -> bool:
    changelog = git_root() / "changelog.md"
    if not changelog.exists():
        print(red("ERROR: changelog.md not found."))
        return False
    if not any(line.startswith("- ") for line in changelog.read_text().splitlines()):
        print(
            red(
                "ERROR: changelog.md has no entries; add release notes before releasing."
            )
        )
        return False
    print(green("OK: changelog.md has entries."))
    return True


def write_github_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a") as f:
        f.write(f"{name}={value}\n")


def main() -> int:
    # --- 1. Version to be released ---
    version = read_version()
    print(bold(f"Version to be released: {PACKAGE} {version}"))

    # --- 2. Changelog has entries ---
    if not check_changelog():
        return 1

    # --- 3. Not already on PyPI ---
    print(f"Checking PyPI for an existing {PACKAGE} {version} release...")
    if is_on_pypi(version):
        print(red(f"ERROR: {PACKAGE} {version} is already published on PyPI."))
        return 1
    print(green(f"OK: {PACKAGE} {version} is not yet on PyPI."))

    # --- 4. GitHub Actions runs on the latest main commit ---
    print(f"Fetching latest commit on '{MAIN_BRANCH}'...")
    sha = latest_main_sha()
    short_sha = sha[:7]
    print(f"Latest {MAIN_BRANCH} commit: {short_sha}")

    print(f"Checking GitHub Actions runs for {short_sha}...")
    runs = workflow_runs(sha)
    if not runs:
        print(red(f"ERROR: No workflow runs found for {short_sha} on {MAIN_BRANCH}."))
        return 1

    failed = False
    for run in runs:
        name = run.get("workflowName", "<unknown>")
        status = run.get("status")
        conclusion = run.get("conclusion") or ""
        if status != "completed":
            print(red(f"  ✗ {name}: still {status}"))
            failed = True
        elif conclusion not in _OK_CONCLUSIONS:
            print(red(f"  ✗ {name}: {conclusion}"))
            failed = True
        else:
            print(green(f"  ✓ {name}: {conclusion}"))

    if failed:
        print(
            red(
                f"ERROR: Not all GitHub Actions runs passed on {MAIN_BRANCH} ({short_sha})."
            )
        )
        return 1
    print(green(f"OK: All GitHub Actions runs passed on {MAIN_BRANCH} ({short_sha})."))

    write_github_output("version", version)
    write_github_output("sha", sha)

    print(bold(f"Pre-release checks passed for {PACKAGE} {version}."))
    return 0


if __name__ == "__main__":
    sys.exit(main())

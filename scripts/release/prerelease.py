#!/usr/bin/env python3
"""Pre-release checks for the neo4j-viz package.

Verifies that:
  1. The version about to be released is printed.
  2. That version is not already published on PyPI.
  3. All GitHub Actions checks passed on the latest commit of the main branch.

Requires: gh (authenticated) on PATH. Run from anywhere inside the repo.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request

from _common import MAIN_BRANCH, PACKAGE, bold, green, read_version, red

# Conclusions that do not block a release.
_OK_CONCLUSIONS = {"success", "neutral", "skipped"}


def is_on_pypi(version: str) -> bool:
    """Return True if PACKAGE==version is already published on PyPI."""
    url = f"https://pypi.org/pypi/{PACKAGE}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.status == 200
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


def _gh_api(endpoint: str, *, paginate: bool = False) -> str:
    cmd = ["gh", "api", endpoint]
    if paginate:
        cmd.append("--paginate")
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(
            red("ERROR: 'gh' CLI not found. Install it and run 'gh auth login'.")
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(red(f"ERROR: gh api {endpoint} failed:\n{exc.stderr.strip()}"))
    return out.stdout


def latest_main_sha() -> str:
    out = _gh_api(f"repos/{{owner}}/{{repo}}/commits/{MAIN_BRANCH}")
    return json.loads(out)["sha"]


def check_runs(sha: str) -> list[dict]:
    # --paginate concatenates one JSON object per page; collect every check_run.
    raw = _gh_api(f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs", paginate=True)
    runs: list[dict] = []
    decoder = json.JSONDecoder()
    idx = 0
    text = raw.strip()
    while idx < len(text):
        obj, end = decoder.raw_decode(text, idx)
        runs.extend(obj.get("check_runs", []))
        idx = end
        while idx < len(text) and text[idx].isspace():
            idx += 1
    return runs


def main() -> int:
    # --- 1. Version to be released ---
    version = read_version()
    print(bold(f"Version to be released: {PACKAGE} {version}"))

    # --- 2. Not already on PyPI ---
    print(f"Checking PyPI for an existing {PACKAGE} {version} release...")
    if is_on_pypi(version):
        print(red(f"ERROR: {PACKAGE} {version} is already published on PyPI."))
        return 1
    print(green(f"OK: {PACKAGE} {version} is not yet on PyPI."))

    # --- 3. GitHub Actions checks on main ---
    print(f"Fetching latest commit on '{MAIN_BRANCH}'...")
    sha = latest_main_sha()
    short_sha = sha[:7]
    print(f"Latest {MAIN_BRANCH} commit: {short_sha}")

    print(f"Checking GitHub Actions check runs for {short_sha}...")
    runs = check_runs(sha)
    if not runs:
        print(red(f"ERROR: No check runs found for {short_sha} on {MAIN_BRANCH}."))
        return 1

    failed = False
    for run in runs:
        name = run.get("name", "<unknown>")
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
                f"ERROR: Not all GitHub Actions checks passed on {MAIN_BRANCH} ({short_sha})."
            )
        )
        return 1
    print(
        green(f"OK: All GitHub Actions checks passed on {MAIN_BRANCH} ({short_sha}).")
    )

    print(bold(f"Pre-release checks passed for {PACKAGE} {version}."))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Post-release finalization for the neo4j-viz package.

Run after the Release workflow has published a version to PyPI. This:
  1. Verifies the just-released version is live on PyPI.
  2. Prints a paste-ready Slack announcement built from changelog.md.
  3. Fast-forwards (or merges) main into the 1.x branch and pushes it.
  4. Bumps the version and resets changelog.md on a branch.
  5. Opens a pull request back to main with those changes.

Requires: git and gh (authenticated) on PATH, run from an up-to-date local main.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from _common import (
    MAIN_BRANCH,
    PACKAGE,
    bold,
    git_root,
    green,
    pyproject_path,
    read_version,
    red,
)
from postrelease import CHANGELOG_TEMPLATE, bump, parse_version, write_version
from prerelease import is_on_pypi

STABLE_BRANCH = "1.x"


def run(
    cmd: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, check=check, capture_output=capture)


def ask(action: str, *, assume_yes: bool) -> bool:
    """Ask for confirmation unless --yes was passed."""
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        raise SystemExit(
            red(f"ERROR: refusing to {action} without confirmation. Pass --yes.")
        )
    reply = input(f"{action}? [y/N] ").strip().lower()
    return reply in {"y", "yes"}


def repo_url(root: Path) -> str:
    out = run(
        ["gh", "repo", "view", "--json", "url", "--jq", ".url"], cwd=root, capture=True
    )
    return out.stdout.strip()


def slack_message(version: str, changelog: str, url: str) -> str:
    """Turn changelog.md into a paste-ready Slack announcement."""
    sections: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for line in changelog.splitlines():
        if line.startswith("## "):
            current = (line[3:].strip(), [])
            sections.append(current)
        elif line.startswith("- ") and current is not None:
            current[1].append(line)

    parts = [f":tada: {PACKAGE} v{version} is out!"]
    for title, bullets in sections:
        if not bullets:
            continue
        parts += ["", f"*{title}*"]
        parts += bullets
    parts += [
        "",
        "`pip install --upgrade neo4j-viz`",
        "",
        f"Release notes: {url}/releases/tag/v{version}",
        f"PyPI: https://pypi.org/project/{PACKAGE}/{version}/",
    ]
    return "\n".join(parts)


def sync_stable_branch(root: Path, *, base: str, stable: str, assume_yes: bool) -> None:
    """Advance `stable` (1.x) to include `base` (main), fast-forwarding if possible."""
    run(["git", "fetch", "origin", base, stable], cwd=root)

    ff = run(
        ["git", "merge-base", "--is-ancestor", f"origin/{stable}", f"origin/{base}"],
        cwd=root,
        check=False,
    )
    if ff.returncode == 0:
        print(f"{stable} can be fast-forwarded to {base}.")
        if not ask(f"push origin/{base} -> {stable}", assume_yes=assume_yes):
            raise SystemExit("Aborted before updating the stable branch.")
        run(["git", "push", "origin", f"origin/{base}:refs/heads/{stable}"], cwd=root)
        print(green(f"OK: {stable} fast-forwarded to {base}."))
        return

    print(f"{stable} has diverged from {base}; a merge commit is required.")
    if not ask(f"merge origin/{base} into {stable} and push", assume_yes=assume_yes):
        raise SystemExit("Aborted before merging into the stable branch.")
    original = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, capture=True
    ).stdout.strip()
    tmp = f"release/merge-{base}-into-{stable}"
    run(["git", "checkout", "-B", tmp, f"origin/{stable}"], cwd=root)
    try:
        run(["git", "merge", "--no-edit", f"origin/{base}"], cwd=root)
        run(["git", "push", "origin", f"{tmp}:refs/heads/{stable}"], cwd=root)
    except subprocess.CalledProcessError:
        run(["git", "merge", "--abort"], cwd=root, check=False)
        raise SystemExit(
            red(
                f"ERROR: could not merge {base} into {stable} cleanly. Resolve manually."
            )
        )
    finally:
        run(["git", "checkout", original], cwd=root, check=False)
        run(["git", "branch", "-D", tmp], cwd=root, check=False)
    print(green(f"OK: merged {base} into {stable}."))


def create_postrelease_pr(
    root: Path, released: str, next_version: str, *, assume_yes: bool
) -> str | None:
    branch = f"postrelease/v{next_version}"
    original = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, capture=True
    ).stdout.strip()
    run(["git", "checkout", "-B", branch, f"origin/{MAIN_BRANCH}"], cwd=root)
    try:
        write_version(pyproject_path(root), released, next_version)
        (root / "changelog.md").write_text(CHANGELOG_TEMPLATE)
        run(["git", "add", "python-wrapper/pyproject.toml", "changelog.md"], cwd=root)
        run(
            [
                "git",
                "commit",
                "-m",
                f"Bump version to {next_version} and reset changelog",
            ],
            cwd=root,
        )
        print(green(f"OK: committed the {next_version} bump on {branch}."))

        if not ask(
            f"push {branch} and open a PR into {MAIN_BRANCH}", assume_yes=assume_yes
        ):
            print(f"Skipping the PR; the commit is on local branch '{branch}'.")
            return None

        run(["git", "push", "-u", "origin", branch], cwd=root)
        body = (
            f"Automated post-release changes after v{released}:\n\n"
            f"- Bump `python-wrapper/pyproject.toml` to `{next_version}`\n"
            f"- Reset `changelog.md` for the next cycle\n"
        )
        out = run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                MAIN_BRANCH,
                "--head",
                branch,
                "--title",
                f"Post-release: bump to {next_version}",
                "--body",
                body,
            ],
            cwd=root,
            capture=True,
        )
        pr_url = out.stdout.strip()
        print(green(f"OK: opened {pr_url}"))
        return pr_url
    finally:
        run(["git", "checkout", original], cwd=root, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post-release finalization: verify, sync 1.x, bump, open PR."
    )
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
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts.")
    args = parser.parse_args()

    root = git_root()
    if run(["git", "status", "--porcelain"], cwd=root, capture=True).stdout.strip():
        raise SystemExit(
            red("ERROR: working tree has uncommitted changes; commit or stash first.")
        )

    # The version and notes must come from the commit that was released, so
    # require an up-to-date local main rather than guessing from origin refs.
    branch = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, capture=True
    ).stdout.strip()
    if branch != MAIN_BRANCH:
        raise SystemExit(
            red(f"ERROR: expected to be on '{MAIN_BRANCH}', currently on '{branch}'.")
        )

    run(["git", "fetch", "origin", MAIN_BRANCH], cwd=root)
    local_sha = run(["git", "rev-parse", "HEAD"], cwd=root, capture=True).stdout.strip()
    remote_sha = run(
        ["git", "rev-parse", f"origin/{MAIN_BRANCH}"], cwd=root, capture=True
    ).stdout.strip()
    if local_sha != remote_sha:
        raise SystemExit(
            red(
                f"ERROR: local {MAIN_BRANCH} ({local_sha[:7]}) is not at "
                f"origin/{MAIN_BRANCH} ({remote_sha[:7]}). Pull first."
            )
        )

    version = read_version(root)
    changelog = (root / "changelog.md").read_text()
    print(bold(f"Finalizing {PACKAGE} {version}"))

    print(f"Checking PyPI for {PACKAGE} {version}...")
    if not is_on_pypi(version):
        raise SystemExit(
            red(
                f"ERROR: {PACKAGE} {version} is not on PyPI yet. "
                "Has the Release workflow finished?"
            )
        )
    print(green(f"OK: {PACKAGE} {version} is live on PyPI."))

    message = slack_message(version, changelog, repo_url(root))

    sync_stable_branch(
        root, base=MAIN_BRANCH, stable=STABLE_BRANCH, assume_yes=args.yes
    )

    if args.set_version:
        parse_version(args.set_version)
        next_version = args.set_version
    else:
        next_version = bump(version, args.part)

    create_postrelease_pr(root, version, next_version, assume_yes=args.yes)

    print()
    print(bold("Slack announcement (paste into #python-visualization):"))
    print("-" * 72)
    print(message)
    print("-" * 72)

    print()
    print(bold("Remaining manual steps:"))
    print("  1. Merge the post-release PR.")
    print("  2. Docs portal: press Run on the build and bump the job up in the queue.")
    print("  3. Verify the new docs are published and correct.")
    print("  4. Update the release template card with any changed steps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

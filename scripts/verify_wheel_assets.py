"""Verify the built distributions ship the widget's build assets.

The assets are not committed (they are built by ``just js-build`` / the CI
``build-js`` action). If a build forgets that step, setuptools silently omits
them and a broken wheel/sdist is published, so check the built artifacts before
publishing.

Usage: ``python scripts/verify_wheel_assets.py [dist_dir]``
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

# Package-relative paths; matched as a suffix so the same list works for the
# wheel (``neo4j_viz/...``) and the sdist (``<name>-<version>/src/neo4j_viz/...``).
REQUIRED = (
    "neo4j_viz/resources/nvl_entrypoint/widget.js",
    "neo4j_viz/resources/nvl_entrypoint/style.css",
    "neo4j_viz/resources/nvl_entrypoint/index.html",
    "neo4j_viz/resources/streamlit_v2/graph.js",
)


def _missing(names: list[str]) -> list[str]:
    return [
        asset for asset in REQUIRED if not any(name.endswith(asset) for name in names)
    ]


def _wheel_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def _sdist_names(path: Path) -> list[str]:
    with tarfile.open(path) as archive:
        return archive.getnames()


def main(argv: list[str]) -> int:
    dist = Path(argv[1]) if len(argv) > 1 else Path("dist")
    archives = sorted(dist.glob("*.whl")) + sorted(dist.glob("*.tar.gz"))
    if not archives:
        print(f"no wheel or sdist found in {dist}", file=sys.stderr)
        return 1

    failed = False
    for archive in archives:
        names = (
            _wheel_names(archive) if archive.suffix == ".whl" else _sdist_names(archive)
        )
        missing = _missing(names)
        if missing:
            failed = True
            print(f"{archive.name}: MISSING {', '.join(missing)}", file=sys.stderr)
        else:
            print(f"{archive.name}: all {len(REQUIRED)} assets present")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

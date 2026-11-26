#!/usr/bin/env python3
"""Run Sphinx with pandoc from a container.

nbsphinx renders notebook Markdown cells by shelling out to the `pandoc` binary
on PATH (`nbsphinx.pandoc`, via `nbconvert.utils.pandoc`). A matching pandoc is
awkward to install locally, so this entry point patches those hooks to run the
pinned `pandoc/core` image instead, then hands the command line to Sphinx.

Usage: `python scripts/sphinx_container_pandoc.py <sphinx-build args>`
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

# Single source of truth for the pandoc version used to render the docs.
# Newest version published as an official `pandoc/core` image; upstream may be ahead.
PANDOC_VERSION = "3.11"


def _image() -> str:
    return os.environ.get("PANDOC_IMAGE", f"pandoc/core:{PANDOC_VERSION}")


def _run(args: list[str], source: str, encoding: str = "utf-8") -> str:
    """Run pandoc in the container, feeding `source` on stdin and returning stdout.

    pandoc reads stdin and writes stdout, so no volume mounts are needed. stderr
    stays attached to surface pandoc warnings.
    """
    cmd = ["docker", "run", "-i", "--rm", _image(), *args]
    try:
        # check=False: a non-zero exit is reported below with the failing command.
        proc = subprocess.run(
            cmd, check=False, input=source.encode(encoding), stdout=subprocess.PIPE
        )
    except FileNotFoundError as err:
        raise RuntimeError(
            "Docker is required to render the docs (pandoc runs in a container), "
            "but the `docker` executable was not found on PATH."
        ) from err

    if proc.returncode != 0:
        raise RuntimeError(
            f"pandoc container failed (exit {proc.returncode}): {' '.join(cmd)}"
        )

    return proc.stdout.decode(encoding, "replace")


def container_pandoc(
    source: str,
    fmt: str,
    to: str,
    extra_args: list[str] | None = None,
    encoding: str = "utf-8",
) -> str:
    """Drop-in for nbconvert.utils.pandoc.pandoc that runs pandoc in a container."""
    args = ["-f", fmt, "-t", to]
    if extra_args:
        args.extend(extra_args)
    return _run(args, source, encoding).rstrip("\n")


def nbsphinx_pandoc(source: str, fmt: str, to: str, filter_func: Any = None) -> str:
    """Drop-in for nbsphinx.pandoc that runs pandoc in a container.

    Mirrors nbsphinx.pandoc: convert to JSON, apply the Python filter, convert
    back to `to`.
    """
    from nbconvert.utils.version import check_version

    args = ["--eol", "lf"] if check_version(PANDOC_VERSION, "2.0") else []
    json_data = _run([*args, "--from", fmt, "--to", "json"], source)
    if filter_func:
        json_data = filter_func(json_data)
    out = _run([*args, "--from", "json", "--to", to, "--columns=500"], json_data)
    return out.rstrip("\n")


def _patch() -> None:
    import nbsphinx  # type: ignore[import-untyped]
    from nbconvert.filters import markdown as filters_markdown
    from nbconvert.filters import pandoc as filters_pandoc
    from nbconvert.utils import pandoc as utils_pandoc

    # Fail loudly if a future nbsphinx/nbconvert renames or drops these hooks,
    # instead of silently falling back to a local pandoc that may not exist.
    targets: list[tuple[Any, str, Any]] = [
        (nbsphinx, "pandoc", nbsphinx_pandoc),
        (utils_pandoc, "pandoc", container_pandoc),
        (filters_pandoc, "pandoc", container_pandoc),
        # markdown2rst picks format flags from this; markdown2asciidoc compares
        # it against 3.0 for the ATX heading flag.
        (utils_pandoc, "get_pandoc_version", lambda: PANDOC_VERSION),
        (filters_markdown, "get_pandoc_version", lambda: PANDOC_VERSION),
    ]
    for module, attr, replacement in targets:
        if not hasattr(module, attr):
            raise RuntimeError(
                f"{module.__name__} has no {attr} to patch; sphinx_container_pandoc.py needs updating for this version."
            )
        setattr(module, attr, replacement)


def main(argv: list[str] | None = None) -> None:
    _patch()

    from sphinx.cmd.build import main as sphinx_main

    sys.exit(sphinx_main(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    main()

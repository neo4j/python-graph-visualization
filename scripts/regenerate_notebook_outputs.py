#!/usr/bin/env python3
"""Regenerate the stored outputs of the example notebooks.

GitHub and other static notebook viewers cannot run the interactive widget, so a
committed notebook shows an empty cell unless the cell also stores the widget's
static PNG fallback. This script executes such cells in a disposable JupyterLab
server driven by headless Chrome: the frontend renders the graph and sends the
image back through the kernel, so the saved notebook carries the preview.

Only cells tagged ``preserve-output`` keep their outputs (see
``scripts/clean_notebooks.py``), and only the cells up to the last of them are run,
so the preview reflects what that cell displayed rather than a later mutation.
Cells tagged ``skip-execution`` are not run, which is how a notebook skips setup
cells that the harness environment cannot execute, such as ``%pip install``.

The database examples need a running Neo4j (``just local-neo4j-setup``) and are
skipped unless ``NEO4J_URI`` is set; they also run their trailing cleanup cells, so a
regeneration leaves the database as it found it. Requires Chrome, or Playwright's
Chromium (``uv run playwright install chromium``). Run from anywhere inside the repo.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass

GIT_ROOT = pathlib.Path(__file__).resolve().parent.parent
# `tests/` is not installed with the package, and a script's own directory is the only
# one Python puts on sys.path — so add its parent, as regenerate_docs_images.py does.
sys.path.insert(0, str(GIT_ROOT / "python-wrapper"))

import nbformat
from clean_notebooks import OutputMode
from clean_notebooks import main as clean_notebook
from tests.browser_harness import (
    BrowserUnavailableError,
    JupyterServer,
    jupyter_server,
    put_notebook,
    run_existing_notebook_in_browser,
)

_EXAMPLES = GIT_ROOT / "examples"
_PRESERVE_TAG = "preserve-output"
_SKIP_TAG = "skip-execution"
_ATTEMPTS = 2


@dataclass(frozen=True)
class NotebookSpec:
    """What a notebook's tags cannot express about regenerating it."""

    # Skip the notebook unless this environment variable is set (its database is up).
    requires_env: str | None = None
    # Run the cells after the last preserved one as well: in the database examples those
    # are the cleanup that leaves the database ready for the next run.
    run_to_end: bool = False


_SPECS: dict[str, NotebookSpec] = {
    "neo4j-example": NotebookSpec(requires_env="NEO4J_URI", run_to_end=True),
    "gds-example": NotebookSpec(requires_env="NEO4J_URI", run_to_end=True),
}


def _tags(cell: nbformat.NotebookNode) -> list[str]:
    return list(cell.get("metadata", {}).get("tags", []))


def _run_cells(notebook: nbformat.NotebookNode, spec: NotebookSpec) -> list[int]:
    """Indices of the cells to execute: the code cells up to the last preserved one.

    Markdown cells are skipped, and so is anything tagged ``skip-execution``. With
    ``spec.run_to_end`` the trailing cells run too.
    """
    preserved = [
        index
        for index, cell in enumerate(notebook.cells)
        if _PRESERVE_TAG in _tags(cell)
    ]
    if not preserved:
        return []
    last = len(notebook.cells) - 1 if spec.run_to_end else preserved[-1]
    return [
        index
        for index in range(last + 1)
        if notebook.cells[index].cell_type == "code"
        # An empty cell has nothing to execute, and JupyterLab never runs one (the
        # harness would wait for a prompt that never changes).
        and notebook.cells[index].source.strip()
        and _SKIP_TAG not in _tags(notebook.cells[index])
    ]


def _has_preserved_cell(notebook: nbformat.NotebookNode) -> bool:
    return any(_PRESERVE_TAG in _tags(cell) for cell in notebook.cells)


def _check_outputs(notebook: nbformat.NotebookNode, path: pathlib.Path) -> None:
    """Fail when a preserved cell stored no PNG, so a silent regression is impossible."""
    for index, cell in enumerate(notebook.cells):
        if _PRESERVE_TAG not in _tags(cell):
            continue
        mimetypes = {
            mime
            for output in cell.get("outputs", [])
            for mime in output.get("data", {})
        }
        if "image/png" not in mimetypes:
            raise RuntimeError(
                f"cell {index} of {path.name} stored no PNG preview. Is a widget displayed in "
                "that cell, and did the frontend render it?"
            )


def _regenerate(path: pathlib.Path, server: JupyterServer, spec: NotebookSpec) -> None:
    notebook = nbformat.read(path, as_version=4)  # type: ignore[no-untyped-call]
    run_cells = _run_cells(notebook, spec)
    if not run_cells:
        raise RuntimeError(f"{path.name} has no preserve-output cell to regenerate")

    saved = server.root / path.name
    run_existing_notebook_in_browser(server, path.name, run_cells=run_cells)
    # `clean_notebooks` drops the widget output (it cannot render without the kernel
    # that produced it) and any cell outputs that are not tagged for preservation, so
    # the file is left exactly as `just py-style` expects it.
    clean_notebook(saved, OutputMode.INPLACE)
    cleaned = nbformat.read(saved, as_version=4)  # type: ignore[no-untyped-call]
    _check_outputs(cleaned, path)
    nbformat.write(cleaned, path)  # type: ignore[no-untyped-call]


def _notebooks(names: Sequence[str]) -> list[pathlib.Path]:
    candidates = [
        path
        for path in sorted(_EXAMPLES.glob("*.ipynb"))
        if _has_preserved_cell(nbformat.read(path, as_version=4))  # type: ignore[no-untyped-call]
    ]
    if not names:
        return candidates
    selected = [path for path in candidates if path.stem in set(names)]
    unknown = set(names) - {path.stem for path in candidates}
    if unknown:
        raise SystemExit(
            f"unknown or untagged notebooks: {sorted(unknown)}; available: {[path.stem for path in candidates]}"
        )
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "names",
        nargs="*",
        metavar="NAME",
        help="regenerate only the named notebooks, without the .ipynb suffix (default: all)",
    )
    args = parser.parse_args()

    notebooks = _notebooks(args.names)
    if not notebooks:
        print(
            "No example notebook has a preserve-output cell; nothing to do.", flush=True
        )
        return 0

    failures: list[str] = []
    with (
        tempfile.TemporaryDirectory(prefix="neo4j-viz-notebook-outputs-") as tmp,
        jupyter_server(
            # Resolved, not as `tempfile` returns it: on macOS that is `/var/...` while the
            # real path is `/private/var/...`, and JupyterLab then refuses to serve files
            # from inside its own root ("abs_path must be within abs_root").
            pathlib.Path(tmp).resolve()
        ) as server,
    ):
        # The notebook is served from a copy of the examples tree so that relative
        # references (the markdown images in the getting-started notebook) resolve.
        shutil.copytree(
            _EXAMPLES,
            server.root,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".jupyter", "jupyter-server.log"),
        )
        for path in notebooks:
            spec = _SPECS.get(path.stem, NotebookSpec())
            if spec.requires_env and not os.environ.get(spec.requires_env):
                print(
                    f"Skipping {path.name} (set {spec.requires_env} to regenerate)",
                    flush=True,
                )
                continue
            print(
                f"Regenerating outputs of {path.relative_to(GIT_ROOT)} ...", flush=True
            )
            try:
                for attempt in range(1, _ATTEMPTS + 1):
                    # The notebook is copied into the server root through the contents
                    # API on every attempt, so a failed run cannot leave half-executed
                    # outputs behind.
                    put_notebook(server, path.name, nbformat.read(path, as_version=4))  # type: ignore[no-untyped-call]
                    try:
                        _regenerate(path, server, spec)
                    except BrowserUnavailableError:
                        raise
                    except (AssertionError, RuntimeError) as exc:
                        if attempt == _ATTEMPTS:
                            raise
                        print(
                            f"  attempt {attempt} failed ({exc}); retrying with a fresh kernel",
                            flush=True,
                        )
            except BrowserUnavailableError as exc:
                print(f"ERROR: {exc}", flush=True)
                return 1
            except (AssertionError, RuntimeError) as exc:
                # AssertionError: a Playwright `expect` timeout; RuntimeError: notebook
                # or server failures (including the debug artifacts in the message).
                print(f"ERROR while regenerating {path.name}:\n{exc}", flush=True)
                failures.append(path.name)
                continue
            print(f"  -> {path.relative_to(GIT_ROOT)}", flush=True)

    if failures:
        print(f"Failed to regenerate: {', '.join(failures)}", flush=True)
        return 1
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

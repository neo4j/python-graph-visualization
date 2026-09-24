#!/usr/bin/env python3
"""Regenerate the documentation images from the example graphs.

For each image, a disposable JupyterLab server is booted, a distilled cell
sequence reproducing the corresponding example's data and styling is run in
headless Chrome, and the rendered graph is saved via ``GraphWidget.save()``.
The images are copied back to their repository locations. The output format
(PNG or SVG) is derived from each target's file ending.

All graphs are built locally without a database, via the toy graph from the
getting-started guide and the neo4j-example's CREATE query through the
``from_gql_create`` GQL integration. Run from anywhere inside the repo.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

GIT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GIT_ROOT / "python-wrapper"))

from tests.browser_harness import (
    DONE_MARKER,
    ERROR_MARKER,
    BrowserUnavailableError,
    jupyter_server,
    run_notebook_in_browser,
)

_ANTORA_IMAGES = GIT_ROOT / "docs" / "antora" / "modules" / "ROOT" / "images"

_TOY_GRAPH_CELLS = """\
from neo4j_viz import Node, Relationship, VisualizationGraph

nodes = [
    Node(id=0, size=10, caption="Person"),
    Node(id=1, size=10, caption="Product"),
    Node(id=2, size=20, caption="Product"),
    Node(id=3, size=10, caption="Person"),
    Node(id=4, size=10, caption="Product"),
]
relationships = [
    Relationship(source=0, target=1, caption="BUYS"),
    Relationship(source=0, target=2, caption="BUYS"),
    Relationship(source=3, target=2, caption="BUYS"),
]

VG = VisualizationGraph(nodes=nodes, relationships=relationships)
"""

# The example graph from examples/neo4j-example.ipynb, built without a
# database via the GQL CREATE integration.
_EXAMPLE_CREATE_CELLS = """\
from neo4j_viz.gql_create import from_gql_create

VG = from_gql_create(
    \"\"\"
    CREATE
     (dan:Person {name: 'Dan'}),
     (annie:Person {name: 'Annie'}),
     (matt:Person {name: 'Matt'}),
     (jeff:Person {name: 'Jeff'}),
     (brie:Person {name: 'Brie'}),
     (elsa:Person {name: 'Elsa'}),

     (cookies:Product {name: 'Cookies'}),
     (tomatoes:Product {name: 'Tomatoes'}),
     (cucumber:Product {name: 'Cucumber'}),
     (celery:Product {name: 'Celery'}),
     (kale:Product {name: 'Kale'}),
     (milk:Product {name: 'Milk'}),
     (chocolate:Product {name: 'Chocolate'}),

     (dan)-[:BUYS {amount: 1.2}]->(cookies),
     (dan)-[:BUYS {amount: 3.2}]->(milk),
     (dan)-[:BUYS {amount: 2.2}]->(chocolate),

     (annie)-[:BUYS {amount: 1.2}]->(cucumber),
     (annie)-[:BUYS {amount: 3.2}]->(milk),
     (annie)-[:BUYS {amount: 3.2}]->(tomatoes),

     (matt)-[:BUYS {amount: 3}]->(tomatoes),
     (matt)-[:BUYS {amount: 2}]->(kale),
     (matt)-[:BUYS {amount: 1}]->(cucumber),

     (jeff)-[:BUYS {amount: 3}]->(cookies),
     (jeff)-[:BUYS {amount: 2}]->(milk),

     (brie)-[:BUYS {amount: 1}]->(tomatoes),
     (brie)-[:BUYS {amount: 2}]->(milk),
     (brie)-[:BUYS {amount: 2}]->(kale),
     (brie)-[:BUYS {amount: 3}]->(cucumber),
     (brie)-[:BUYS {amount: 0.3}]->(celery),

     (elsa)-[:BUYS {amount: 3}]->(chocolate),
     (elsa)-[:BUYS {amount: 3}]->(milk)
    \"\"\"
)
"""


@dataclass(frozen=True)
class ImageSpec:
    """One docs image: how to build it and where it lives in the repository."""

    name: str
    target: Path
    # Widget canvas size in pixels; for PNG output this is also the expected
    # image size. SVG output covers the entire graph, so the widget size only
    # needs to be large enough to mount the widget.
    size: tuple[int, int]
    # Cells up to and including the one that displays the widget. The harness
    # waits for the widget's canvas before running the generated save cell.
    cells: tuple[str, ...] = ()

    @property
    def fmt(self) -> str:
        """The output format, derived from the target's file ending."""
        return self.target.suffix.lstrip(".")

    @property
    def filename(self) -> str:
        return self.target.name


def _render_cell(size: tuple[int, int]) -> str:
    width, height = size
    return (
        f"widget = VG.render_widget(width='{width}px', height='{height}px')\nwidget\n"
    )


def _save_cell(spec: ImageSpec) -> str:
    filename = spec.filename
    if spec.fmt == "svg":
        # SVG export covers the entire graph and defaults to a transparent
        # background, so it blends with the docs page.
        save_call = f"await widget.save({filename!r})"
        output_check = (
            f"assert Path({filename!r}).read_text().lstrip().startswith('<svg')"
        )
    else:
        save_call = f"await widget.save({filename!r}, background_color='#ffffff')"
        output_check = (
            f"assert Path({filename!r}).read_bytes()[:8] == b'\\x89PNG\\r\\n\\x1a\\n'"
        )
    return f"""\
import traceback
from pathlib import Path
try:
    {save_call}
    {output_check}
    Path('{DONE_MARKER}').write_text('ok')
except Exception:
    Path('{ERROR_MARKER}').write_text(traceback.format_exc())
"""


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"{path} is not a PNG file")
    return struct.unpack(">II", header[16:24])


def _validate_produced(spec: ImageSpec, produced: Path) -> str | None:
    """Return an error message when the produced image does not look right."""
    if spec.fmt == "svg":
        text = produced.read_text(encoding="utf-8", errors="replace").lstrip()
        if not text.startswith("<svg"):
            return "the file does not start with '<svg'"
        return None
    actual_size = _png_size(produced)
    if actual_size != spec.size:
        return f"expected a {spec.size[0]}x{spec.size[1]} image, got {actual_size[0]}x{actual_size[1]}"
    return None


def _specs() -> list[ImageSpec]:
    guide_size = (1588, 1200)
    readme_size = (1392, 1200)

    return [
        ImageSpec(
            name="getting-started-graph",
            target=_ANTORA_IMAGES / "getting-started-graph.svg",
            size=guide_size,
            cells=(_TOY_GRAPH_CELLS, _render_cell(guide_size)),
        ),
        ImageSpec(
            name="getting-started-graph-colored",
            target=_ANTORA_IMAGES / "getting-started-graph-colored.svg",
            size=guide_size,
            cells=(
                _TOY_GRAPH_CELLS,
                "VG.color_nodes(field='caption')\n",
                _render_cell(guide_size),
            ),
        ),
        ImageSpec(
            name="example_graph",
            target=GIT_ROOT / "examples" / "example_graph.svg",
            size=readme_size,
            cells=(_EXAMPLE_CREATE_CELLS, _render_cell(readme_size)),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "names",
        nargs="*",
        metavar="NAME",
        help="regenerate only the named images (default: all)",
    )
    args = parser.parse_args()

    specs = _specs()
    if args.names:
        unknown = set(args.names) - {spec.name for spec in specs}
        if unknown:
            parser.error(
                f"unknown image names: {sorted(unknown)}; available: {[s.name for s in specs]}"
            )
        specs = [spec for spec in specs if spec.name in set(args.names)]

    unsupported = [spec.name for spec in specs if spec.fmt not in ("png", "svg")]
    if unsupported:
        parser.error(
            f"unsupported image file ending for: {unsupported} (expected .png or .svg)"
        )

    failures: list[str] = []
    with (
        tempfile.TemporaryDirectory(prefix="neo4j-viz-docs-images-") as tmp,
        jupyter_server(Path(tmp)) as server,
    ):
        for spec in specs:
            print(f"Regenerating {spec.target.relative_to(GIT_ROOT)} ...", flush=True)
            try:
                run_notebook_in_browser(server, [*spec.cells, _save_cell(spec)])
            except BrowserUnavailableError as exc:
                print(f"ERROR: {exc}", flush=True)
                return 1
            except (AssertionError, RuntimeError) as exc:
                # AssertionError: a Playwright `expect` timeout; RuntimeError:
                # notebook/server failures (including the marker error text).
                print(f"ERROR while regenerating {spec.name}:\n{exc}", flush=True)
                failures.append(spec.name)
                continue

            filename = spec.filename
            produced = server.root / filename
            error = _validate_produced(spec, produced)
            if error:
                print(f"ERROR {spec.name}: {error}", flush=True)
                failures.append(spec.name)
                continue

            spec.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(produced, spec.target)
            print(f"  -> {spec.target.relative_to(GIT_ROOT)}", flush=True)

    if failures:
        print(f"Failed to regenerate: {', '.join(failures)}", flush=True)
        return 1
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

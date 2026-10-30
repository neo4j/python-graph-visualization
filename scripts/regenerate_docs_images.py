#!/usr/bin/env python3
"""Regenerate the documentation images from the example graphs.

For each image, a disposable JupyterLab server is booted, a distilled cell
sequence reproducing the corresponding example's data and styling is run in
headless Chrome, and the whole widget element (graph canvas plus its UI chrome:
toolbar, search, legend) is screenshotted. The images are copied back to their
repository locations.

Most graphs are built locally without a database, via the toy graph from the
getting-started guide and the examples' CREATE queries through the
``from_gql_create`` GQL integration. The GDS image needs a running Graph Data
Science instance: set ``NEO4J_URI`` (see ``just local-neo4j-setup``) to include
it, otherwise that spec is skipped. Run from anywhere inside the repo.
"""

from __future__ import annotations

import argparse
import functools
import os
import shutil
import struct
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page

GIT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GIT_ROOT / "python-wrapper"))

from tests.browser_harness import (
    DONE_MARKER,
    BrowserUnavailableError,
    jupyter_server,
    run_notebook_in_browser,
)

_ANTORA_IMAGES = GIT_ROOT / "docs" / "antora" / "modules" / "ROOT" / "images"
_EXAMPLES = GIT_ROOT / "examples"
_EXAMPLE_IMAGES = _EXAMPLES / "images"

# The widget wrapper element: the graph canvas plus its UI chrome (toolbar,
# search, legend). Screenshotting it captures the widget as a user sees it.
_WIDGET_SELECTOR = '[data-neo4j-viz-ndl="true"]'
# The canvas mounts before the force-directed layout settles, so give the
# widget a moment to paint before capturing it.
_WIDGET_SETTLE_MS = 3000
# JupyterLab chrome that would otherwise overlap the widget in the capture.
_CHROME_HIDE_CSS = (
    ".jp-NotebookPanel-toolbar, .jp-Notebook-toolbar, .jp-Notification, "
    ".jp-Notification-Stack, .jp-Dialog, .jp-StatusBar { display: none !important; }"
)

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

# The graph from examples/snowflake-example.ipynb, built without Snowflake via
# the GQL CREATE integration. The labels stand in for the Snowflake table names,
# so the captions and colors match what from_snowflake produces.
_SNOWFLAKE_CELLS = """\
from neo4j_viz.gql_create import from_gql_create

VG = from_gql_create(
    \"\"\"
    CREATE
      (alice:PERSONS {SNOWFLAKEID: 'Alice'}),
      (bob:PERSONS {SNOWFLAKEID: 'Bob'}),
      (carol:PERSONS {SNOWFLAKEID: 'Carol'}),
      (dave:PERSONS {SNOWFLAKEID: 'Dave'}),
      (eve:PERSONS {SNOWFLAKEID: 'Eve'}),

      (guitar:INSTRUMENTS {SNOWFLAKEID: 'Guitar'}),
      (synthesizer:INSTRUMENTS {SNOWFLAKEID: 'Synthesizer'}),
      (bongos:INSTRUMENTS {SNOWFLAKEID: 'Bongos'}),
      (trumpet:INSTRUMENTS {SNOWFLAKEID: 'Trumpet'}),

      (alice)-[:LIKES]->(guitar),
      (alice)-[:LIKES]->(synthesizer),
      (alice)-[:LIKES]->(bongos),
      (bob)-[:LIKES]->(guitar),
      (bob)-[:LIKES]->(synthesizer),
      (carol)-[:LIKES]->(bongos),
      (dave)-[:LIKES]->(guitar),
      (dave)-[:LIKES]->(trumpet),
      (dave)-[:LIKES]->(bongos)
    \"\"\"
)
"""

# The Cora graph from examples/gds-example.ipynb. Unlike the other specs this
# needs a running GDS instance (see the module docstring).
_GDS_CELLS = (
    """\
import os

from graphdatascience import GraphDataScience

gds = GraphDataScience(
    os.environ["NEO4J_URI"],
    auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password")),
)

G = gds.graph.datasets.load_cora(graph_name="cora")
gds.node_similarity.mutate(G, mutate_relationship_type="SIMILAR", mutate_property="similarity")
gds.page_rank.mutate(G, mutate_property="pagerank")
gds.louvain.mutate(G, mutate_property="componentId")
""",
    """\
import matplotlib.colors as mcolors
from palettable.colorbrewer.qualitative import Dark2_7

from neo4j_viz.gds import from_gds

VG = from_gds(gds, G, max_node_count=100)
VG.resize_nodes(property="pagerank")

number_of_components = len({n.properties["componentId"] for n in VG.nodes})
color_map = Dark2_7.mpl_colormap.resampled(number_of_components)
colors = [mcolors.rgb2hex(color_map(i)) for i in range(number_of_components)]
VG.color_nodes(property="componentId", colors=colors, override=True)
""",
)


@dataclass(frozen=True)
class ImageSpec:
    """One docs image: how to build it and where it lives in the repository."""

    name: str
    target: Path
    # Widget canvas size in pixels; the screenshot is the same size (the widget
    # element's bounding box).
    size: tuple[int, int]
    # Cells up to and including the one that displays the widget. The harness
    # waits for the widget's canvas before running the generated marker cell.
    cells: tuple[str, ...] = ()
    # Extra locations to copy the produced image to (e.g. the examples/ copy
    # that a notebook references alongside the Antora page copy).
    also_copy: tuple[Path, ...] = ()
    # When set, the spec only runs if this environment variable is present. Used
    # for images that need an external service (e.g. GDS via NEO4J_URI).
    requires_env: str | None = None

    @property
    def filename(self) -> str:
        return self.target.name


def _render_cell(size: tuple[int, int]) -> str:
    width, height = size
    return (
        f"widget = VG.render_widget(width='{width}px', height='{height}px')\nwidget\n"
    )


def _marker_cell() -> str:
    """A final cell that signals completion."""
    return f"from pathlib import Path\nPath('{DONE_MARKER}').write_text('ok')\n"


def _screenshot_widget(page: Page, target: Path, size: tuple[int, int]) -> None:
    """Capture the whole widget element, UI chrome included."""
    # Give the widget room so it is fully on screen (the notebook otherwise
    # scrolls it partly out of view), then hide JupyterLab's own chrome so it
    # does not bleed into the capture.
    page.set_viewport_size({"width": size[0] + 600, "height": size[1] + 350})
    page.add_style_tag(content=_CHROME_HIDE_CSS)
    widget = page.locator(_WIDGET_SELECTOR)
    widget.scroll_into_view_if_needed()
    page.wait_for_timeout(_WIDGET_SETTLE_MS)
    widget.screenshot(path=str(target))


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"{path} is not a PNG file")
    return struct.unpack(">II", header[16:24])


def _validate_produced(spec: ImageSpec, produced: Path) -> str | None:
    """Return an error message when the produced image does not look right."""
    actual_size = _png_size(produced)
    # A browser screenshot includes the widget chrome, so allow a couple of
    # pixels of rounding relative to the configured canvas size.
    if abs(actual_size[0] - spec.size[0]) > 4 or abs(actual_size[1] - spec.size[1]) > 4:
        return f"expected roughly a {spec.size[0]}x{spec.size[1]} image, got {actual_size[0]}x{actual_size[1]}"
    return None


def _specs() -> list[ImageSpec]:
    widget_size = (1200, 900)

    return [
        ImageSpec(
            name="example_graph",
            target=_EXAMPLE_IMAGES / "example_graph.png",
            size=widget_size,
            cells=(_EXAMPLE_CREATE_CELLS, _render_cell(widget_size)),
        ),
        ImageSpec(
            name="getting-started-widget",
            target=_ANTORA_IMAGES / "getting-started-widget.png",
            size=widget_size,
            cells=(_TOY_GRAPH_CELLS, _render_cell(widget_size)),
            also_copy=(_EXAMPLE_IMAGES / "getting-started-widget.png",),
        ),
        ImageSpec(
            name="getting-started-widget-colored",
            target=_ANTORA_IMAGES / "getting-started-widget-colored.png",
            size=widget_size,
            cells=(
                _TOY_GRAPH_CELLS,
                "VG.color_nodes(field='caption')\n",
                _render_cell(widget_size),
            ),
            also_copy=(_EXAMPLE_IMAGES / "getting-started-widget-colored.png",),
        ),
        ImageSpec(
            name="gds-example-graph",
            target=_EXAMPLE_IMAGES / "gds-example-graph.png",
            size=widget_size,
            cells=(*_GDS_CELLS, _render_cell(widget_size)),
            requires_env="NEO4J_URI",
        ),
        ImageSpec(
            name="snowflake-example-graph",
            target=_EXAMPLE_IMAGES / "example_instruments_1.png",
            size=widget_size,
            cells=(_SNOWFLAKE_CELLS, _render_cell(widget_size)),
        ),
        ImageSpec(
            name="snowflake-example-graph-colored",
            target=_EXAMPLE_IMAGES / "example_instruments_2.png",
            size=widget_size,
            cells=(
                _SNOWFLAKE_CELLS,
                _render_cell(widget_size),
                "widget.color_nodes(property='SNOWFLAKEID', override=True)\n",
            ),
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

    failures: list[str] = []
    with (
        tempfile.TemporaryDirectory(prefix="neo4j-viz-docs-images-") as tmp,
        jupyter_server(Path(tmp)) as server,
    ):
        for spec in specs:
            if spec.requires_env and not os.environ.get(spec.requires_env):
                print(
                    f"Skipping {spec.name} (set {spec.requires_env} to regenerate)",
                    flush=True,
                )
                continue

            print(f"Regenerating {spec.target.relative_to(GIT_ROOT)} ...", flush=True)
            try:
                produced = server.root / spec.filename
                run_notebook_in_browser(
                    server,
                    [*spec.cells, _marker_cell()],
                    check=functools.partial(
                        _screenshot_widget, target=produced, size=spec.size
                    ),
                )
            except BrowserUnavailableError as exc:
                print(f"ERROR: {exc}", flush=True)
                return 1
            except (AssertionError, RuntimeError) as exc:
                # AssertionError: a Playwright `expect` timeout; RuntimeError:
                # notebook/server failures (including the marker error text).
                print(f"ERROR while regenerating {spec.name}:\n{exc}", flush=True)
                failures.append(spec.name)
                continue

            error = _validate_produced(spec, produced)
            if error:
                print(f"ERROR {spec.name}: {error}", flush=True)
                failures.append(spec.name)
                continue

            for destination in (spec.target, *spec.also_copy):
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(produced, destination)
                print(f"  -> {destination.relative_to(GIT_ROOT)}", flush=True)

    if failures:
        print(f"Failed to regenerate: {', '.join(failures)}", flush=True)
        return 1
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

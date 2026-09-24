#!/usr/bin/env python3
"""Regenerate the documentation images from the example graphs.

For each image, a disposable JupyterLab server is booted, a distilled cell
sequence reproducing the corresponding example notebook's data and styling is
run in headless Chrome, and the rendered graph is saved as a PNG via
``GraphWidget.save()``. The PNGs are copied back to their repository locations:

* ``docs/antora/modules/ROOT/images/graph_2120034f.png`` - getting-started toy graph
* ``docs/antora/modules/ROOT/images/graph_00ff5513.png`` - same graph, colored by caption
* ``examples/example_graph.png``                          - README graph (neo4j-example)

The README image needs a Neo4j instance (e.g. ``just local-neo4j-setup``) and
is skipped when ``NEO4J_URI`` is not set. Run from anywhere inside the repo.
"""

from __future__ import annotations

import argparse
import os
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


@dataclass(frozen=True)
class ImageSpec:
    """One docs image: how to build it and where it lives in the repository."""

    name: str
    target: Path
    size: tuple[int, int]
    required_env: tuple[str, ...] = ()
    # Cells up to and including the one that displays the widget. The harness
    # waits for the widget's canvas before running the generated save cell.
    cells: tuple[str, ...] = ()
    # Extra code lines run inside the save cell after the image was written
    # (e.g. database cleanup); a failure also fails the spec.
    teardown: tuple[str, ...] = ()


def _neo4j_graph_cells() -> str:
    return """\
import os

from neo4j import GraphDatabase, Result, RoutingControl
from neo4j_viz.neo4j import from_neo4j

URI = os.environ['NEO4J_URI']
auth = (os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ.get('NEO4J_PASSWORD', 'password'))
db = os.environ.get('NEO4J_DB', 'neo4j')

driver = GraphDatabase.driver(URI, auth=auth)
driver.verify_connectivity()

# Start from a clean slate so repeated runs do not duplicate the example graph.
driver.execute_query('MATCH (n:Person|Product) DETACH DELETE n RETURN count(n)', database_=db)
driver.execute_query(
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
    \"\"\",
    database_=db,
)

result = driver.execute_query(
    'MATCH (n)-[r]->(m) RETURN n,r,m',
    database_=db,
    routing_=RoutingControl.READ,
    result_transformer_=Result.graph,
)
print(f'Result graph has: {len(result.nodes)} nodes, {len(result.relationships)} relationships')

VG = from_neo4j(result)
"""


def _render_cell(size: tuple[int, int], initial_zoom: int | None = None) -> str:
    width, height = size
    zoom = f", initial_zoom={initial_zoom}" if initial_zoom is not None else ""
    return f"widget = VG.render_widget(width='{width}px', height='{height}px'{zoom})\nwidget\n"


def _save_cell(spec: ImageSpec) -> str:
    teardown = "\n".join(f"    {line}" for line in spec.teardown)
    if teardown:
        teardown += "\n"
    filename = spec.name + ".png"
    return f"""\
import traceback
from pathlib import Path
try:
    await widget.save({filename!r}, background_color='#ffffff')
    assert Path({filename!r}).read_bytes()[:8] == b'\\x89PNG\\r\\n\\x1a\\n'
{teardown}    Path('{DONE_MARKER}').write_text('ok')
except Exception:
    Path('{ERROR_MARKER}').write_text(traceback.format_exc())
"""


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"{path} is not a PNG file")
    return struct.unpack(">II", header[16:24])


def _specs() -> list[ImageSpec]:
    toy_plain_size = (3176, 2400)
    toy_colored_size = (3176, 2400)
    readme_size = (1392, 1200)

    return [
        ImageSpec(
            name="graph_2120034f",
            target=_ANTORA_IMAGES / "graph_2120034f.png",
            size=toy_plain_size,
            cells=(_TOY_GRAPH_CELLS, _render_cell(toy_plain_size, initial_zoom=2)),
        ),
        ImageSpec(
            name="graph_00ff5513",
            target=_ANTORA_IMAGES / "graph_00ff5513.png",
            size=toy_colored_size,
            cells=(
                _TOY_GRAPH_CELLS,
                "VG.color_nodes(field='caption')\n",
                _render_cell(toy_colored_size, initial_zoom=2),
            ),
        ),
        ImageSpec(
            name="example_graph",
            target=GIT_ROOT / "examples" / "example_graph.png",
            size=readme_size,
            required_env=("NEO4J_URI",),
            cells=(_neo4j_graph_cells(), _render_cell(readme_size)),
            teardown=(
                "driver.execute_query('MATCH (n:Person|Product) DETACH DELETE n RETURN count(n)', database_=db)",
                "driver.close()",
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
            missing = [var for var in spec.required_env if not os.environ.get(var)]
            if missing:
                print(
                    f"SKIP {spec.name}: missing environment variables {missing}",
                    flush=True,
                )
                continue

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

            filename = spec.name + ".png"
            produced = server.root / filename
            actual_size = _png_size(produced)
            if actual_size != spec.size:
                print(
                    f"ERROR {spec.name}: expected a {spec.size[0]}x{spec.size[1]} image, "
                    f"got {actual_size[0]}x{actual_size[1]}",
                    flush=True,
                )
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

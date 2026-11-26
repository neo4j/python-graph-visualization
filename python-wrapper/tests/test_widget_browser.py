"""End-to-end test for ``GraphWidget.save()`` in a real JupyterLab browser session.

Boots a disposable JupyterLab server, creates a notebook whose cells render a
widget and call ``save()``, drives it in headless Chrome via Playwright, and
verifies that the PNG/SVG files actually appear on the kernel side.
"""

from __future__ import annotations

import base64
import struct
from collections.abc import Iterator

import nbformat
import pytest
from playwright.sync_api import Page

from tests.browser_harness import (
    DONE_MARKER,
    ERROR_MARKER,
    BrowserUnavailableError,
    JupyterServer,
    assert_no_ndl_leak,
    create_notebook,
    jupyter_server,
    run_existing_notebook_in_browser,
    run_notebook_in_browser,
)


@pytest.fixture(scope="session")
def jupyter_lab_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[JupyterServer]:
    with jupyter_server(tmp_path_factory.mktemp("lab-root")) as server:
        yield server


def test_save_png_and_svg_end_to_end(jupyter_lab_server: JupyterServer) -> None:
    setup_cell = """\
from neo4j_viz import Node, Relationship, VisualizationGraph
nodes = [Node(id='0', caption='Alice'), Node(id='1', caption='Bob')]
rels = [Relationship(source='0', target='1', caption='KNOWS')]
widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(height='400px')
widget
"""
    save_image_cell = f"""\
import traceback
from pathlib import Path
try:
    await widget.save('out.svg')
    await widget.save('out.png', background_color='#ffffff')
    assert Path('out.svg').read_text().lstrip().startswith('<svg')
    assert Path('out.png').read_bytes()[:8] == b'\\x89PNG\\r\\n\\x1a\\n'
    Path('{DONE_MARKER}').write_text('ok')
except Exception:
    Path('{ERROR_MARKER}').write_text(traceback.format_exc())
"""
    try:
        run_notebook_in_browser(jupyter_lab_server, [setup_cell, save_image_cell])
    except BrowserUnavailableError as exc:
        pytest.skip(str(exc))

    svg = (jupyter_lab_server.root / "out.svg").read_text()
    png = (jupyter_lab_server.root / "out.png").read_bytes()
    assert svg.lstrip().startswith("<svg")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_save_in_same_cell_as_display_does_not_time_out(jupyter_lab_server: JupyterServer) -> None:
    """Regression: display the widget and ``save()`` in the same cell.

    A request sent before the frontend loads is dropped, which used to surface as a
    30 s timeout. The trailing cell keeps this one off the harness's canvas wait.
    """
    setup_cell = """\
from neo4j_viz import Node, Relationship, VisualizationGraph
nodes = [Node(id='0', caption='Alice'), Node(id='1', caption='Bob')]
rels = [Relationship(source='0', target='1', caption='KNOWS')]
widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(height='400px')
"""
    display_and_save_cell = f"""\
import traceback
from pathlib import Path
from IPython.display import display
try:
    display(widget)
    await widget.save('out-immediate.png')
    assert Path('out-immediate.png').read_bytes()[:8] == b'\\x89PNG\\r\\n\\x1a\\n'
    Path('{DONE_MARKER}').write_text('ok')
except Exception:
    Path('{ERROR_MARKER}').write_text(traceback.format_exc())
"""
    marker_cell = "pass"
    try:
        run_notebook_in_browser(jupyter_lab_server, [setup_cell, display_and_save_cell, marker_cell])
    except BrowserUnavailableError as exc:
        pytest.skip(str(exc))

    png = (jupyter_lab_server.root / "out-immediate.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_fit_end_to_end(jupyter_lab_server: JupyterServer) -> None:
    """``GraphWidget.fit()`` round-trips through a real frontend and NVL instance.

    The coordinate layout is used because its initial view is the one that is *not* framed
    automatically by NVL: the nodes sit far from the canvas origin until ``fit()`` frames them.
    ``fit=False`` keeps the automatic framing out of the way, so the explicit call is the one
    under test.
    """
    setup_cell = """\
from neo4j_viz import Node, Relationship, VisualizationGraph, Layout
nodes = [Node(id='0', caption='Alice', x=10000, y=10000), Node(id='1', caption='Bob', x=10100, y=10100)]
rels = [Relationship(source='0', target='1', caption='KNOWS')]
widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(
    height='400px', layout=Layout.COORDINATE, fit=False
)
widget
"""
    fit_cell = f"""\
import traceback
from pathlib import Path
try:
    await widget.fit()
    await widget.fit(['0'])
    Path('{DONE_MARKER}').write_text('ok')
except Exception:
    Path('{ERROR_MARKER}').write_text(traceback.format_exc())
"""
    try:
        run_notebook_in_browser(jupyter_lab_server, [setup_cell, fit_cell])
    except BrowserUnavailableError as exc:
        pytest.skip(str(exc))


# The stored fallback image is the rendered canvas, so counting the pixels that differ from
# its background says whether anything is in view at all.
_DRAWN_PIXELS_SCRIPT = """\
async () => {
  const img = [...document.querySelectorAll("img")].find(
    (candidate) => candidate.src.startsWith("data:image/png;base64,") && candidate.src.length > 10000,
  );
  if (!img) return null;
  await img.decode();
  const canvas = document.createElement("canvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const context = canvas.getContext("2d");
  context.drawImage(img, 0, 0);
  const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
  const [r, g, b] = [data[0], data[1], data[2]];
  let drawn = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (data[i] !== r || data[i + 1] !== g || data[i + 2] !== b) drawn += 1;
  }
  return drawn;
}"""


def _drawn_pixels_in_stored_image(page: Page) -> int:
    """Count the non-background pixels of the stored fallback image (the rendered view)."""
    page.wait_for_function(
        "() => [...document.querySelectorAll('img')].some((img) => "
        "img.src.startsWith('data:image/png;base64,') && img.src.length > 10000)",
        timeout=30_000,
    )
    drawn = page.evaluate(_DRAWN_PIXELS_SCRIPT)
    assert isinstance(drawn, int)
    return drawn


def _coordinate_graph_drawn_pixels(server: JupyterServer, *, fit: bool) -> int:
    """Render a coordinate-layout graph far from the canvas origin and measure what is in view."""
    setup_cell = f"""\
from neo4j_viz import Node, Relationship, VisualizationGraph, Layout
nodes = [
    Node(id='0', caption='Alice', x=10000, y=10000),
    Node(id='1', caption='Bob', x=10100, y=10100),
    Node(id='2', caption='Carol', x=10050, y=10080),
]
rels = [
    Relationship(source='0', target='1', caption='KNOWS'),
    Relationship(source='1', target='2', caption='KNOWS'),
]
widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(
    height='400px', layout=Layout.COORDINATE, fit={fit}
)
widget
"""
    marker_cell = f"""\
from pathlib import Path
Path('{DONE_MARKER}').write_text('ok')
"""
    drawn: list[int] = []

    def check(page: Page) -> None:
        drawn.append(_drawn_pixels_in_stored_image(page))

    try:
        run_notebook_in_browser(server, [setup_cell, marker_cell], check=check)
    except BrowserUnavailableError as exc:
        pytest.skip(str(exc))
    return drawn[0]


def test_automatic_fit_frames_off_screen_coordinates(jupyter_lab_server: JupyterServer) -> None:
    """The initial view frames the coordinate layout instead of leaving it at the origin.

    NVL's own default fit only adjusted the zoom and kept the pan, so coordinates far from the
    canvas origin stayed off-screen until the zoom-to-fit button was clicked. Framing every
    layout means moving the pan to the graph as well.
    """
    framed = _coordinate_graph_drawn_pixels(jupyter_lab_server, fit=True)
    unframed = _coordinate_graph_drawn_pixels(jupyter_lab_server, fit=False)

    # The unframed run is the negative control: the nodes sit outside that view, so the
    # canvas holds nothing but the background.
    assert unframed < 100, f"expected an empty view without fit, drew {unframed} pixels"
    assert framed > 1000, f"expected the framed view to show the graph, drew {framed} pixels"


def test_widget_does_not_restyle_jupyter_page(jupyter_lab_server: JupyterServer) -> None:
    setup_cell = """\
from neo4j_viz import Node, Relationship, VisualizationGraph
nodes = [Node(id='0', caption='Alice'), Node(id='1', caption='Bob')]
rels = [Relationship(source='0', target='1', caption='KNOWS')]
widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(height='400px')
widget
"""
    finish_cell = f"""\
from pathlib import Path
Path('{DONE_MARKER}').write_text('ok')
"""
    try:
        run_notebook_in_browser(jupyter_lab_server, [setup_cell, finish_cell], check=assert_no_ndl_leak)
    except BrowserUnavailableError as exc:
        pytest.skip(str(exc))


# The stored fallback image is a large inline PNG. JupyterLab's own stylesheets carry
# tiny data URIs, so the length separates ours from them.
_STORED_IMAGE_SCRIPT = """\
() => {
  const stored = [...document.querySelectorAll("img")].filter(
    (img) => img.src.startsWith("data:image/png;base64,") && img.src.length > 10000,
  );
  return { count: stored.length, visible: stored.filter((img) => img.offsetParent !== null).length };
}"""


def _assert_stored_image_hidden(page: Page) -> None:
    """Fail unless the fallback image is in the page and hidden.

    Waiting for it first proves the snapshot reached the live frontend. Only then does
    "nothing visible" mean the widget hid it, rather than that it never arrived.
    """
    page.wait_for_function(
        "() => [...document.querySelectorAll('img')].some((img) => "
        "img.src.startsWith('data:image/png;base64,') && img.src.length > 10000)",
        timeout=30_000,
    )
    state = page.evaluate(_STORED_IMAGE_SCRIPT)
    assert state["count"] > 0
    assert state["visible"] == 0, "the stored fallback image is visible next to the widget"


def test_fallback_png_is_stored_and_hidden(jupyter_lab_server: JupyterServer) -> None:
    """The widget stores a PNG preview next to its output and hides it in the frontend.

    The image is what makes a committed notebook show the graph on GitHub, where the
    widget output cannot render; in a live frontend it stays out of the way.
    """
    setup_cell = """\
from neo4j_viz import Node, Relationship, VisualizationGraph
nodes = [Node(id='0', caption='Alice'), Node(id='1', caption='Bob')]
rels = [Relationship(source='0', target='1', caption='KNOWS')]
widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(height='400px')
widget
"""
    # A second cell changes the graph, which refreshes the stored snapshot in place.
    change_cell = "widget.color_nodes(field='caption')\n"
    notebook = create_notebook(jupyter_lab_server, [setup_cell, change_cell])

    try:
        run_existing_notebook_in_browser(
            jupyter_lab_server,
            notebook,
            run_cells=[0, 1],
            check=_assert_stored_image_hidden,
        )
    except BrowserUnavailableError as exc:
        pytest.skip(str(exc))

    saved = nbformat.read(jupyter_lab_server.root / notebook, as_version=4)  # type: ignore[no-untyped-call]
    outputs = saved.cells[0].outputs
    images = [output for output in outputs if "image/png" in output.get("data", {})]
    assert len(images) == 1, f"expected one stored image, got {[list(o['data']) for o in outputs]}"

    png = base64.b64decode(images[0]["data"]["image/png"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    assert width > 0 and height > 0

    # Both outputs are stored: `scripts/clean_notebooks.py` is what drops the widget
    # output when the notebook is committed, since it cannot render without its kernel.
    mimes = {mime for output in outputs for mime in output.get("data", {})}
    assert "application/vnd.jupyter.widget-view+json" in mimes

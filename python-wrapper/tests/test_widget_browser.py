"""End-to-end test for ``GraphWidget.save()`` in a real JupyterLab browser session.

Boots a disposable JupyterLab server, creates a notebook whose cells render a
widget and call ``save()``, drives it in headless Chrome via Playwright, and
verifies that the PNG/SVG files actually appear on the kernel side.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.browser_harness import (
    DONE_MARKER,
    ERROR_MARKER,
    BrowserUnavailableError,
    JupyterServer,
    jupyter_server,
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

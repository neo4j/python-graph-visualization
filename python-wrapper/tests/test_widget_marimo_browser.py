"""End-to-end test that the widget does not restyle its Marimo host page (GDS-440).

Marimo renders anywidgets in the light DOM and mounts the widget's ``_css``
(the full NDL stylesheet) at the document level. That stylesheet contains a
Tailwind-style preflight with bare-element selectors (``h1``, ``a``,
``ol,ul,menu``, ``*``, …) which, left unscoped, reset the Marimo UI. The build
scopes the stylesheet to the widget wrapper; this test boots a real Marimo
server, renders the widget in headless Chrome, and asserts that the NDL
stylesheet applied to the document contains no bare-element rules.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

from tests.browser_harness import (
    BrowserUnavailableError,
    assert_no_ndl_leak,
    marimo_server,
    run_marimo_app_in_browser,
)

MARIMO_APP = """\
import marimo

app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    mo.md(
        \"\"\"
        # Marimo Styling Probe

        A paragraph with a [link](https://example.com).

        - first item
        - second item
        \"\"\"
    )
    return (mo,)


@app.cell
def _():
    from neo4j_viz import Node, Relationship, VisualizationGraph

    nodes = [Node(id="0", caption="Alice"), Node(id="1", caption="Bob")]
    rels = [Relationship(source="0", target="1", caption="KNOWS")]
    widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(height="300px")
    widget
    return (widget,)


if __name__ == "__main__":
    app.run()
"""


@pytest.fixture(scope="session")
def marimo_available() -> None:
    # A pruned environment can leave an empty ``marimo/`` directory behind as a
    # namespace package (``origin is None``), so a bare ``find_spec`` is not enough.
    spec = importlib.util.find_spec("marimo")
    if spec is None or spec.origin is None:
        pytest.skip("marimo is not installed")


def test_widget_does_not_restyle_marimo_page(tmp_path: pathlib.Path, marimo_available: None) -> None:
    app = tmp_path / "app.py"
    app.write_text(MARIMO_APP)

    try:
        with marimo_server(tmp_path, app) as server:
            run_marimo_app_in_browser(server, assert_no_ndl_leak)
    except BrowserUnavailableError as exc:
        pytest.skip(str(exc))

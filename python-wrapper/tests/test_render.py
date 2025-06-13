import re
from pathlib import Path
from typing import Any

import pytest
from selenium import webdriver

from neo4j_viz import Node, Relationship, VisualizationGraph
from neo4j_viz.nvl import NVL
from neo4j_viz.options import Layout, Renderer

render_cases = {
    "default": {},
    "force layout": {"layout": Layout.FORCE_DIRECTED},
    "grid layout": {"layout": Layout.GRID},
    "coordinate layout": {"layout": Layout.COORDINATE},
    "hierarchical layout + options": {"layout": Layout.HIERARCHICAL, "layout_options": {"direction": "left"}},
    "with layout options": {"layout_options": {"gravity": 0.1}},
}


@pytest.mark.parametrize("render_option", render_cases.values(), ids=render_cases.keys())
def test_basic_render(render_option: dict[str, Any], tmp_path: Path) -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person", x=1, y=10),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product", x=2, y=15),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product", x=3, pinned=True),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:12", caption="Product", x=4),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:1", caption="Person", x=5),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:7", caption="Product", x=6),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:8", caption="Product", x=7),
    ]
    relationships = [
        Relationship(
            source="4:d09f48a4-5fca-421d-921d-a30a896c604d:0",
            target="4:d09f48a4-5fca-421d-921d-a30a896c604d:6",
            caption="BUYS",
        ),
        Relationship(
            source="4:d09f48a4-5fca-421d-921d-a30a896c604d:0",
            target="4:d09f48a4-5fca-421d-921d-a30a896c604d:11",
            caption="BUYS",
        ),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    html = VG.render(**render_option)

    file_path = tmp_path / "basic_render.html"

    with open(file_path, "w+") as the_file:
        the_file.write(html.data)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")  # avoid browser window popping up
    driver = webdriver.Chrome(options=chrome_options)
    # wait for page to render
    driver.implicitly_wait(3)

    driver.get(f"file://{file_path}")

    logs = driver.get_log("browser")  # type: ignore[no-untyped-call]

    severe_logs = [log for log in logs if log["level"] == "SEVERE"]

    assert not severe_logs, f"Severe logs found: {severe_logs}, all logs: {logs}"


def test_max_allowed_nodes_limit() -> None:
    nodes = [Node(id=i) for i in range(10_001)]
    VG = VisualizationGraph(nodes=nodes, relationships=[])
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Too many nodes (10001) to render. Maximum allowed nodes is set to 10000 for performance reasons. "
            "It can be increased by overriding `max_allowed_nodes`, but rendering could then take a long time"
        ),
    ):
        VG.render(max_allowed_nodes=10_000)


def test_render_warnings() -> None:
    nodes = [Node(id=i) for i in range(10_001)]
    VG = VisualizationGraph(nodes=nodes, relationships=[])
    with pytest.warns(
        UserWarning,
        match="To visualize more than 10.000 nodes, we recommend using the WebGL renderer instead of the "
        "canvas renderer for better performance. You can set the renderer using the `renderer` parameter",
    ):
        VG.render(max_allowed_nodes=20_000, renderer=Renderer.CANVAS)

    with pytest.warns(
        UserWarning,
        match="Although better for performance, the WebGL renderer cannot render text, icons and arrowheads on "
        "relationships. If you need these features, use the canvas renderer by setting the `renderer` parameter",
    ):
        VG.render(max_allowed_nodes=20_000, renderer=Renderer.WEB_GL)


def test_render_non_json_serializable() -> None:
    import datetime

    now = datetime.datetime.now()
    node = Node(
        id=0,
        properties={
            "non-json-serializable": now,
        },
    )
    assert str(now) in NVL._serialize_entity(node)

    VG = VisualizationGraph(nodes=[node], relationships=[])
    # Should not raise an error
    VG.render()


def test_render_with_wrong_layout_options() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person", x=1, y=10),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.raises(
        ValueError,
        match="Unexpected `ForceDirectedLayoutOptions` parameter 'direction' with provided input 'left'",
    ):
        VG.render(layout_options={"direction": "left"})

    with pytest.raises(
        ValueError,
        match="Unexpected `ForceDirectedLayoutOptions` parameter 'direction' with provided input 'left'",
    ):
        VG.render(layout=Layout.FORCE_DIRECTED, layout_options={"direction": "left"})

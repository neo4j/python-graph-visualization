import pytest

from neo4j_viz.options import (
    Direction,
    ForceDirectedLayoutOptions,
    HierarchicalLayoutOptions,
    Layout,
    RenderOptions,
    Renderer,
)


def test_render_options() -> None:
    options = RenderOptions(layout=Layout.HIERARCHICAL)

    assert options.to_dict() == {"layout": "hierarchical"}


def test_render_options_with_layout_options() -> None:
    options = RenderOptions(
        layout=Layout.HIERARCHICAL, layout_options=HierarchicalLayoutOptions(direction=Direction.LEFT)
    )

    assert options.to_dict() == {"layout": "hierarchical", "layoutOptions": {"direction": "left"}}


def test_layout_options_match() -> None:
    with pytest.raises(
        ValueError, match="layout_options must be of type ForceDirectedLayoutOptions for force-directed layout"
    ):
        RenderOptions(layout=Layout.FORCE_DIRECTED, layout_options=HierarchicalLayoutOptions(direction=Direction.LEFT))


# ── to_js_options tests ──────────────────────────────────────────────────


def test_js_options_empty() -> None:
    options = RenderOptions()
    assert options.to_js_options() == {}


def test_js_options_layout_force_directed() -> None:
    options = RenderOptions(layout=Layout.FORCE_DIRECTED)
    js = options.to_js_options()
    assert js["layout"] == "d3Force"


def test_js_options_layout_hierarchical() -> None:
    options = RenderOptions(layout=Layout.HIERARCHICAL)
    js = options.to_js_options()
    assert js["layout"] == "hierarchical"


def test_js_options_layout_coordinate() -> None:
    options = RenderOptions(layout=Layout.COORDINATE)
    js = options.to_js_options()
    assert js["layout"] == "free"


def test_js_options_renderer_canvas() -> None:
    options = RenderOptions(renderer=Renderer.CANVAS)
    js = options.to_js_options()
    assert js["nvlOptions"]["disableWebGL"] is True


def test_js_options_renderer_webgl() -> None:
    options = RenderOptions(renderer=Renderer.WEB_GL)
    js = options.to_js_options()
    assert js["nvlOptions"]["disableWebGL"] is False


def test_js_options_zoom_and_pan() -> None:
    options = RenderOptions(initial_zoom=2.0, pan_X=100.0, pan_Y=200.0)
    js = options.to_js_options()
    assert js["zoom"] == 2.0
    assert js["pan"] == {"x": 100.0, "y": 200.0}


def test_js_options_min_max_zoom() -> None:
    options = RenderOptions(min_zoom=0.1, max_zoom=5.0)
    js = options.to_js_options()
    assert js["nvlOptions"]["minZoom"] == 0.1
    assert js["nvlOptions"]["maxZoom"] == 5.0


def test_js_options_allow_dynamic_min_zoom() -> None:
    options = RenderOptions(allow_dynamic_min_zoom=False)
    js = options.to_js_options()
    assert js["nvlOptions"]["allowDynamicMinZoom"] is False


def test_js_options_with_layout_options() -> None:
    options = RenderOptions(
        layout=Layout.HIERARCHICAL,
        layout_options=HierarchicalLayoutOptions(direction=Direction.LEFT),
    )
    js = options.to_js_options()
    assert js["layout"] == "hierarchical"
    assert js["layoutOptions"] == {"direction": "left"}


def test_js_options_with_force_directed_layout_options() -> None:
    options = RenderOptions(
        layout=Layout.FORCE_DIRECTED,
        layout_options=ForceDirectedLayoutOptions(gravity=0.5),
    )
    js = options.to_js_options()
    assert js["layout"] == "d3Force"
    assert js["layoutOptions"] == {"gravity": 0.5}


def test_js_options_full() -> None:
    options = RenderOptions(
        layout=Layout.HIERARCHICAL,
        layout_options=HierarchicalLayoutOptions(direction=Direction.DOWN),
        renderer=Renderer.WEB_GL,
        initial_zoom=1.5,
        min_zoom=0.05,
        max_zoom=8.0,
        allow_dynamic_min_zoom=True,
        pan_X=50.0,
        pan_Y=-30.0,
    )
    js = options.to_js_options()
    assert js == {
        "layout": "hierarchical",
        "layoutOptions": {"direction": "down"},
        "nvlOptions": {
            "disableWebGL": False,
            "minZoom": 0.05,
            "maxZoom": 8.0,
            "allowDynamicMinZoom": True,
        },
        "zoom": 1.5,
        "pan": {"x": 50.0, "y": -30.0},
    }

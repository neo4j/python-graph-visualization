from neo4j_viz.options import (
    Direction,
    ForceDirectedLayoutOptions,
    HierarchicalLayoutOptions,
    Layout,
    Renderer,
    RenderOptions,
    SelectionMode,
    WidgetLayout,
    WidgetOptions,
)


def test_widget_options_empty() -> None:
    options = RenderOptions()
    assert options.to_widget_options().to_json() == {"showLayoutButton": False}


def test_widget_options_layout_force_directed() -> None:
    options = RenderOptions(layout=Layout.FORCE_DIRECTED)
    widget_options = options.to_widget_options().to_json()
    assert widget_options["layout"] == "d3Force"


def test_widget_options_layout_hierarchical() -> None:
    options = RenderOptions(layout=Layout.HIERARCHICAL)
    widget_options = options.to_widget_options().to_json()
    assert widget_options["layout"] == "hierarchical"


def test_widget_options_layout_coordinate() -> None:
    options = RenderOptions(layout=Layout.COORDINATE)
    js = options.to_widget_options().to_json()
    assert js["layout"] == "free"


def test_widget_options_renderer_canvas() -> None:
    options = RenderOptions(renderer=Renderer.CANVAS)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["disableWebGL"] is True


def test_widget_options_renderer_webgl() -> None:
    options = RenderOptions(renderer=Renderer.WEB_GL)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["disableWebGL"] is False


def test_widget_options_zoom_and_pan() -> None:
    options = RenderOptions(initial_zoom=2.0, pan_X=100.0, pan_Y=200.0)
    js = options.to_widget_options().to_json()
    assert js["zoom"] == 2.0
    assert js["pan"] == {"x": 100.0, "y": 200.0}


def test_widget_options_min_max_zoom() -> None:
    options = RenderOptions(min_zoom=0.1, max_zoom=5.0)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["minZoom"] == 0.1
    assert js["nvlOptions"]["maxZoom"] == 5.0


def test_widget_options_allow_dynamic_min_zoom() -> None:
    options = RenderOptions(allow_dynamic_min_zoom=False)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["allowDynamicMinZoom"] is False


def test_widget_options_with_layout_options() -> None:
    options = RenderOptions(
        layout=Layout.HIERARCHICAL,
        layout_options=HierarchicalLayoutOptions(direction=Direction.LEFT),
    )
    js = options.to_widget_options().to_json()
    assert js["layout"] == "hierarchical"
    assert js["layoutOptions"] == {"direction": "left"}


def test_widget_options_with_force_directed_layout_options() -> None:
    options = RenderOptions(
        layout=Layout.FORCE_DIRECTED,
        layout_options=ForceDirectedLayoutOptions(gravity=0.5),
    )
    widget_options = options.to_widget_options().to_json()
    assert widget_options["layout"] == "d3Force"
    assert widget_options["layoutOptions"] == {"gravity": 0.5}


def test_widget_options_selection_mode() -> None:
    options = RenderOptions(selection_mode=SelectionMode.BOX)
    js = options.to_widget_options().to_json()
    assert js["selectionMode"] == "box"


def test_widget_options_no_selection_mode_by_default() -> None:
    js = RenderOptions().to_widget_options().to_json()
    assert "selectionMode" not in js


def test_widget_options_layout_is_enum() -> None:
    widget_options = RenderOptions(layout=Layout.GRID).to_widget_options()
    assert widget_options.layout is WidgetLayout.GRID
    # str enum serializes to the JS wire value
    assert widget_options.to_json()["layout"] == "grid"


def test_widget_options_coerces_layout_string_to_enum() -> None:
    widget_options = WidgetOptions.model_validate({"layout": "d3Force"})
    assert widget_options.layout is WidgetLayout.D3_FORCE


def test_widget_options_full() -> None:
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
        show_layout_button=True,
        selection_mode=SelectionMode.LASSO,
    )
    js = options.to_widget_options().to_json()
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
        "showLayoutButton": True,
        "selectionMode": "lasso",
    }

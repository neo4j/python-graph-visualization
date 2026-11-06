import warnings as warnings_module

import pytest

from neo4j_viz.options import (
    ClusteringOptions,
    Direction,
    ForceDirectedLayoutOptions,
    HierarchicalLayoutOptions,
    Layout,
    Renderer,
    RenderOptions,
    SeedingMethod,
    SelectionMode,
    WidgetLayout,
    WidgetOptions,
    construct_layout_options,
)


def test_widget_options_empty() -> None:
    options = RenderOptions()
    assert options.to_widget_options().to_json() == {
        "showLayoutButton": False,
        "showSearchButton": True,
    }


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
    assert js["nvlOptions"]["renderer"] == "canvas"
    assert js["nvlOptions"]["disableWebGL"] is True


def test_widget_options_renderer_webgl() -> None:
    options = RenderOptions(renderer=Renderer.WEB_GL)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["renderer"] == "webgl"
    assert js["nvlOptions"]["disableWebGL"] is False


def test_widget_options_gpu_force_enables_webgl_context() -> None:
    # The GPU force layout needs NVL's WebGL context even on the canvas renderer (default).
    options = RenderOptions(layout=Layout.GPU_FORCE)
    js = options.to_widget_options().to_json()
    assert js["layout"] == "forceDirected"
    assert js["nvlOptions"]["disableWebGL"] is False
    assert "renderer" not in js["nvlOptions"]


def test_widget_options_gpu_force_with_canvas_renderer() -> None:
    options = RenderOptions(layout=Layout.GPU_FORCE, renderer=Renderer.CANVAS)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["renderer"] == "canvas"
    assert js["nvlOptions"]["disableWebGL"] is False


def test_widget_options_gpu_force_with_webgl_renderer() -> None:
    options = RenderOptions(layout=Layout.GPU_FORCE, renderer=Renderer.WEB_GL)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["renderer"] == "webgl"
    assert js["nvlOptions"]["disableWebGL"] is False


def test_check_renderer_warns_on_webgl_with_captions() -> None:
    with pytest.warns(UserWarning, match="WebGL renderer does not render captions"):
        Renderer.check(Renderer.WEB_GL, num_nodes=10, has_captions=True)


def test_check_renderer_no_caption_warning_without_captions() -> None:
    with warnings_module.catch_warnings():
        warnings_module.simplefilter("error")
        Renderer.check(Renderer.WEB_GL, num_nodes=10, has_captions=False)


def test_check_renderer_no_warning_on_canvas() -> None:
    with warnings_module.catch_warnings():
        warnings_module.simplefilter("error")
        Renderer.check(Renderer.CANVAS, num_nodes=10, has_captions=True)


def test_check_renderer_warns_on_many_canvas_nodes() -> None:
    with pytest.warns(UserWarning, match="we recommend using the WebGL renderer"):
        Renderer.check(Renderer.CANVAS, num_nodes=10_001)


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


def test_widget_options_show_search_button() -> None:
    js = RenderOptions(show_search_button=False).to_widget_options().to_json()
    assert js["showSearchButton"] is False


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
        show_search_button=False,
        selection_mode=SelectionMode.LASSO,
    )
    js = options.to_widget_options().to_json()
    assert js == {
        "layout": "hierarchical",
        "layoutOptions": {"direction": "down"},
        "nvlOptions": {
            "disableWebGL": False,
            "renderer": "webgl",
            "minZoom": 0.05,
            "maxZoom": 8.0,
            "allowDynamicMinZoom": True,
        },
        "zoom": 1.5,
        "pan": {"x": 50.0, "y": -30.0},
        "showLayoutButton": True,
        "showSearchButton": False,
        "selectionMode": "lasso",
    }


def test_widget_options_layout_gpu_force() -> None:
    options = RenderOptions(layout=Layout.GPU_FORCE)
    js = options.to_widget_options().to_json()
    assert js["layout"] == "forceDirected"


def test_widget_options_min_max_fps() -> None:
    options = RenderOptions(min_fps=10, max_fps=60)
    js = options.to_widget_options().to_json()
    assert js["nvlOptions"]["minFps"] == 10
    assert js["nvlOptions"]["maxFps"] == 60


def test_widget_options_force_directed_with_seeding_method() -> None:
    options = RenderOptions(
        layout=Layout.FORCE_DIRECTED,
        layout_options=ForceDirectedLayoutOptions(seedingMethod=SeedingMethod.CIRCLE),
    )
    js = options.to_widget_options().to_json()
    assert js["layoutOptions"] == {"seedingMethod": "circle"}


def test_widget_options_gpu_force_with_clustering() -> None:
    options = RenderOptions(
        layout=Layout.GPU_FORCE,
        layout_options=ForceDirectedLayoutOptions(
            clustering=ClusteringOptions(clusterBy="community", drawOutline=True, drawHalo=True),
        ),
    )
    js = options.to_widget_options().to_json()
    assert js["layout"] == "forceDirected"
    assert js["layoutOptions"] == {
        "clustering": {"clusterBy": "community", "drawOutline": True, "drawHalo": True},
    }


def test_widget_options_hierarchical_with_clustering() -> None:
    options = RenderOptions(
        layout=Layout.HIERARCHICAL,
        layout_options=HierarchicalLayoutOptions(clusterBy="community"),
    )
    js = options.to_widget_options().to_json()
    assert js["layoutOptions"] == {"clusterBy": "community"}


def test_widget_options_cross_cluster_multiplier_out_of_range() -> None:
    with pytest.raises(ValueError, match="crossClusterRelationshipMultiplier"):
        construct_layout_options(
            Layout.GPU_FORCE,
            {"clustering": {"clusterBy": "community", "crossClusterRelationshipMultiplier": 2}},
        )


def test_widget_options_clustering_requires_cluster_by() -> None:
    with pytest.raises(ValueError, match="clusterBy"):
        construct_layout_options(Layout.GPU_FORCE, {"clustering": {"drawOutline": True}})


def test_widget_options_gpu_force_layout_options_type_mismatch() -> None:
    with pytest.raises(ValueError, match="ForceDirectedLayoutOptions"):
        RenderOptions(
            layout=Layout.GPU_FORCE,
            layout_options=HierarchicalLayoutOptions(direction=Direction.LEFT),
        )

import pytest

from neo4j_viz.options import Direction, HierarchicalLayoutOptions, Layout, RenderOptions


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

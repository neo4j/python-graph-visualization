import pytest
from pydantic_extra_types.color import Color

from neo4j_viz import Node, VisualizationGraph
from neo4j_viz.colors import (
    NEO4J_COLORS_CONTINUOUS,
    NEO4J_COLORS_DISCRETE,
    ColorSpace,
    interpolate_gradient,
)


@pytest.mark.parametrize("override", [True, False])
def test_color_nodes_dict(override: bool) -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product", color="#FF0000"),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(field="caption", colors={"Person": "#000000", "Product": "#00FF00"}, override=override)

    assert VG.nodes[0].color == Color("#000000")
    assert VG.nodes[1].color == Color("#00ff00")
    if override:
        assert VG.nodes[2].color == Color("#00ff00")
    else:
        assert VG.nodes[2].color == Color("#ff0000")


@pytest.mark.parametrize("override", [True, False])
def test_color_nodes_iter_basic(override: bool) -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product", color="#FF0000"),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(field="caption", colors=["#000000", "#00FF00"], override=override)

    assert VG.nodes[0].color == Color("#000000")
    assert VG.nodes[1].color == Color("#00ff00")
    if override:
        assert VG.nodes[2].color == Color("#00ff00")
    else:
        assert VG.nodes[2].color == Color("#ff0000")


def test_color_nodes_iter_exhausted() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:12", caption="Review"),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.warns(
        UserWarning,
        match=(
            "Ran out of colors for property 'caption'. 3 colors were needed, but only 2 were given, so reused colors"
        ),
    ):
        VG.color_nodes(field="caption", colors=["#000000", "#00FF00"])

    assert VG.nodes[0].color == Color("#000000")
    assert VG.nodes[1].color == Color("#00ff00")
    assert VG.nodes[2].color == Color("#00ff00")
    assert VG.nodes[3].color == Color("#000000")


@pytest.mark.filterwarnings("ignore:pkg_resources is deprecated as an API")
def test_color_nodes_palette() -> None:
    from palettable.wesanderson import Moonrise1_5  # type: ignore[import-untyped]

    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:12", caption="Review"),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(field="caption", colors=Moonrise1_5.colors)

    assert VG.nodes[0].color == Color((114, 202, 221))
    assert VG.nodes[1].color == Color((240, 165, 176))
    assert VG.nodes[2].color == Color((240, 165, 176))
    assert VG.nodes[3].color == Color((140, 133, 54))


def test_color_nodes_default() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:12", caption="Review"),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(field="caption")

    assert VG.nodes[0].color == Color(NEO4J_COLORS_DISCRETE[0])
    assert VG.nodes[1].color == Color(NEO4J_COLORS_DISCRETE[1])
    assert VG.nodes[2].color == Color(NEO4J_COLORS_DISCRETE[1])
    assert VG.nodes[3].color == Color(NEO4J_COLORS_DISCRETE[2])


def test_color_nodes_continuous_default() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", properties={"rank": 10}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", properties={"rank": 20}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", properties={"rank": 30}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="rank", color_space=ColorSpace.CONTINUOUS)

    assert VG.nodes[0].color == Color(NEO4J_COLORS_CONTINUOUS[0])
    assert VG.nodes[1].color == interpolate_gradient(NEO4J_COLORS_CONTINUOUS, 0.5)
    assert VG.nodes[2].color == Color(NEO4J_COLORS_CONTINUOUS[255])


def test_color_nodes_continuous_custom() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", properties={"rank": 10}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", properties={"rank": 18}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", properties={"rank": 30}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    colors = [(0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255)]
    VG.color_nodes(property="rank", colors=colors, color_space=ColorSpace.CONTINUOUS)

    assert VG.nodes[0].color == Color("black")
    assert VG.nodes[1].color == Color((102, 102, 102))
    assert VG.nodes[2].color == Color("white")


def test_color_nodes_continuous_two_stops_is_a_gradient() -> None:
    # GDS-355: two colors must interpolate a real gradient, not quantize to the two stops
    nodes = [
        Node(id="0", caption="Person", properties={"labels": ["Person"], "centrality": 0.1}),
        Node(id="1", caption="Movie", properties={"labels": ["Movie"], "centrality": 0.5}),
        Node(id="2", caption="Movie", properties={"labels": ["Movie"], "centrality": 0.9}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="centrality", colors=["#E0E0E0", "#000000"], color_space=ColorSpace.CONTINUOUS)

    assert VG.nodes[0].color == Color("#e0e0e0")
    assert VG.nodes[1].color == Color("#707070")
    assert VG.nodes[2].color == Color("#000000")


def test_color_nodes_continuous_uniform_values() -> None:
    nodes = [
        Node(id="1", properties={"score": 5}),
        Node(id="2", properties={"score": 5}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="score", colors=["#E0E0E0", "#000000"], color_space=ColorSpace.CONTINUOUS)

    assert VG.nodes[0].color == Color("#707070")
    assert VG.nodes[1].color == Color("#707070")


def test_color_nodes_continuous_single_color() -> None:
    nodes = [
        Node(id="1", properties={"score": 1}),
        Node(id="2", properties={"score": 2}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="score", colors=["#01ABCD"], color_space=ColorSpace.CONTINUOUS)

    assert VG.nodes[0].color == Color("#01abcd")
    assert VG.nodes[1].color == Color("#01abcd")


def test_color_nodes_does_not_change_captions() -> None:
    # GDS-355: coloring by a property must leave node captions untouched
    nodes = [
        Node(id="0", caption="Person", properties={"labels": ["Person"], "centrality": 0.1}),
        Node(id="1", caption="Movie", properties={"labels": ["Movie"], "centrality": 0.9}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="centrality", colors=["#E0E0E0", "#000000"], color_space=ColorSpace.CONTINUOUS)

    assert VG.nodes[0].caption == "Person"
    assert VG.nodes[1].caption == "Movie"


def test_color_nodes_continuous_serialized_payload() -> None:
    # The payload handed to the frontend: colors are long hex, captions survive
    nodes = [
        Node(id="0", caption="Person", properties={"labels": ["Person"], "centrality": 0.1}),
        Node(id="1", caption="Movie", properties={"labels": ["Movie"], "centrality": 0.9}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="centrality", colors=["#E0E0E0", "#000000"], color_space=ColorSpace.CONTINUOUS)

    assert VG.nodes[0].to_dict() == {
        "id": "0",
        "caption": "Person",
        "color": "#e0e0e0",
        "properties": {"labels": ["Person"], "centrality": 0.1},
    }
    assert VG.nodes[1].to_dict() == {
        "id": "1",
        "caption": "Movie",
        "color": "#000000",
        "properties": {"labels": ["Movie"], "centrality": 0.9},
    }


def test_color_nodes_continuous_forbidden() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", properties={"rank": 10}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", properties={"rank": 30}),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.raises(
        ValueError, match="For continuous properties, `colors` must be a list of colors representing a range"
    ):
        VG.color_nodes(property="rank", colors={10: "#000000", 30: "#00FF00"}, color_space=ColorSpace.CONTINUOUS)  # type: ignore[arg-type]


def test_color_nodes_lists() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person", properties={"labels": ["Person"]}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product", properties={"labels": ["Product"]}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product", properties={"labels": ["Product"]}),
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:1", caption="Both", properties={"labels": ["Person", "Product"]}
        ),
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:2",
            caption="Both again",
            properties={"labels": ["Person", "Product"]},
        ),
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:3",
            caption="Both reorder",
            properties={"labels": ["Product", "Person"]},
        ),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="labels", colors=["#000000", "#00FF00", "#FF0000", "#0000FF"])

    assert VG.nodes[0].color == Color("#000000")
    assert VG.nodes[1].color == Color("#00ff00")
    assert VG.nodes[2].color == Color("#00ff00")
    assert VG.nodes[3].color == Color("#ff0000")
    assert VG.nodes[4].color == Color("#ff0000")
    assert VG.nodes[5].color == Color("#0000ff")


def test_color_nodes_sets() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person", properties={"labels": {"Person"}}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product", properties={"labels": {"Product"}}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product", properties={"labels": {"Product"}}),
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:1", caption="Both", properties={"labels": {"Person", "Product"}}
        ),
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:2",
            caption="Both again",
            properties={"labels": {"Person", "Product"}},
        ),
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:3",
            caption="Both reorder",
            properties={"labels": {"Product", "Person"}},
        ),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="labels", colors=["#000000", "#00FF00", "#FF0000", "#0000FF"])

    assert VG.nodes[0].color == Color("#000000")
    assert VG.nodes[1].color == Color("#00ff00")
    assert VG.nodes[2].color == Color("#00ff00")
    assert VG.nodes[3].color == Color("#ff0000")
    assert VG.nodes[4].color == Color("#ff0000")
    assert VG.nodes[4].color == Color("#ff0000")


def test_color_nodes_dicts() -> None:
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person", properties={"config": {"age": 18}}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product", properties={"config": {"price": 100}}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product", properties={"config": {"price": 100}}),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:1", caption="Product", properties={"config": {"price": 1}}),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="config", colors=["#000000", "#00FF00", "#FF0000", "#0000FF"])

    assert VG.nodes[0].color == Color("#000000")
    assert VG.nodes[1].color == Color("#00ff00")
    assert VG.nodes[2].color == Color("#00ff00")
    assert VG.nodes[3].color == Color("#ff0000")


def test_color_nodes_unhashable() -> None:
    nodes = [
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0",
            caption="Person",
            properties={"config": {"movies": ["Star Wars", "Star Trek"]}},
        ),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.raises(ValueError, match="Unable to color nodes by unhashable property type '<class 'dict'>'"):
        VG.color_nodes(property="config", colors=["#000000"])

    nodes = [
        Node(
            id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0",
            caption="Person",
            properties={"list_of_lists": [[1, 2], [3, 4]]},
        ),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])
    with pytest.raises(ValueError, match="Unable to color nodes by unhashable property type '<class 'list'>'"):
        VG.color_nodes(property="list_of_lists", colors=["#000000"])


def test_color_nodes_default_override() -> None:
    """Test that the default value of override is True (colors are overridden by default)."""
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person", color="#FF0000"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product", color="#FF0000"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product", color="#FF0000"),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    # Call without specifying override - should use default (True) and override existing colors
    VG.color_nodes(field="caption", colors={"Person": "#000000", "Product": "#00FF00"})

    assert VG.nodes[0].color == Color("#000000")
    assert VG.nodes[1].color == Color("#00ff00")
    assert VG.nodes[2].color == Color("#00ff00")  # Should be overridden to #00ff00


def test_color_nodes_override_false() -> None:
    """Test that override=False preserves existing colors."""
    nodes = [
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0", caption="Person", color="#FF0000"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:6", caption="Product", color="#FF0000"),
        Node(id="4:d09f48a4-5fca-421d-921d-a30a896c604d:11", caption="Product"),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=[])

    # Call with override=False - should preserve existing colors
    VG.color_nodes(field="caption", colors={"Person": "#000000", "Product": "#00FF00"}, override=False)

    assert VG.nodes[0].color == Color("#ff0000")  # Should keep existing color
    assert VG.nodes[1].color == Color("#ff0000")  # Should keep existing color
    assert VG.nodes[2].color == Color("#00ff00")  # Should get new color (no existing color)


def test_color_nodes_continuous_missing_property_raises() -> None:
    VG = VisualizationGraph(nodes=[Node(id="1"), Node(id="2")], relationships=[])

    with pytest.raises(ValueError, match="No node has a value for 'name'"):
        VG.color_nodes(property="name", color_space=ColorSpace.CONTINUOUS)


def test_color_nodes_continuous_non_numeric_raises() -> None:
    nodes = [
        Node(id="1", properties={"name": "Alice"}),
        Node(id="2", properties={"name": "Bob"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.raises(ValueError, match="Continuous coloring needs numeric values"):
        VG.color_nodes(property="name", color_space=ColorSpace.CONTINUOUS)

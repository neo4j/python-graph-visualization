import pytest
from pydantic_extra_types.color import Color

from neo4j_viz import Node, Relationship, VisualizationGraph
from neo4j_viz.colors import NEO4J_COLORS_CONTINUOUS, NEO4J_COLORS_DISCRETE, ColorSpace


@pytest.mark.parametrize("override", [True, False])
def test_color_relationships_dict(override: bool) -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", caption="ACTED_IN"),
        Relationship(id="r2", source="2", target="1", caption="DIRECTED"),
        Relationship(id="r3", source="1", target="2", caption="DIRECTED", color="#FF0000"),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    VG.color_relationships(field="caption", colors={"ACTED_IN": "#000000", "DIRECTED": "#00FF00"}, override=override)

    assert VG.relationships[0].color == Color("#000000")
    assert VG.relationships[1].color == Color("#00ff00")
    if override:
        assert VG.relationships[2].color == Color("#00ff00")
    else:
        assert VG.relationships[2].color == Color("#ff0000")


@pytest.mark.parametrize("override", [True, False])
def test_color_relationships_iter_basic(override: bool) -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", caption="ACTED_IN"),
        Relationship(id="r2", source="2", target="1", caption="DIRECTED"),
        Relationship(id="r3", source="1", target="2", caption="DIRECTED", color="#FF0000"),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    VG.color_relationships(field="caption", colors=["#000000", "#00FF00"], override=override)

    assert VG.relationships[0].color == Color("#000000")
    assert VG.relationships[1].color == Color("#00ff00")
    if override:
        assert VG.relationships[2].color == Color("#00ff00")
    else:
        assert VG.relationships[2].color == Color("#ff0000")


def test_color_relationships_iter_exhausted() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", caption="ACTED_IN"),
        Relationship(id="r2", source="2", target="1", caption="DIRECTED"),
        Relationship(id="r3", source="1", target="2", caption="DIRECTED"),
        Relationship(id="r4", source="2", target="1", caption="PRODUCED"),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    with pytest.warns(
        UserWarning,
        match=(
            "Ran out of colors for property 'caption'. 3 colors were needed, but only 2 were given, so reused colors"
        ),
    ):
        VG.color_relationships(field="caption", colors=["#000000", "#00FF00"])

    assert VG.relationships[0].color == Color("#000000")
    assert VG.relationships[1].color == Color("#00ff00")
    assert VG.relationships[2].color == Color("#00ff00")
    assert VG.relationships[3].color == Color("#000000")


def test_color_relationships_default() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", caption="ACTED_IN"),
        Relationship(id="r2", source="2", target="1", caption="DIRECTED"),
        Relationship(id="r3", source="1", target="2", caption="DIRECTED"),
        Relationship(id="r4", source="2", target="1", caption="PRODUCED"),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    VG.color_relationships(field="caption")

    assert VG.relationships[0].color == Color(NEO4J_COLORS_DISCRETE[0])
    assert VG.relationships[1].color == Color(NEO4J_COLORS_DISCRETE[1])
    assert VG.relationships[2].color == Color(NEO4J_COLORS_DISCRETE[1])
    assert VG.relationships[3].color == Color(NEO4J_COLORS_DISCRETE[2])


def test_color_relationships_continuous_default() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", properties={"weight": 10}),
        Relationship(id="r2", source="2", target="1", properties={"weight": 20}),
        Relationship(id="r3", source="1", target="2", properties={"weight": 30}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    VG.color_relationships(property="weight", color_space=ColorSpace.CONTINUOUS)

    assert VG.relationships[0].color == Color(NEO4J_COLORS_CONTINUOUS[0])
    assert VG.relationships[1].color == Color(NEO4J_COLORS_CONTINUOUS[128])
    assert VG.relationships[2].color == Color(NEO4J_COLORS_CONTINUOUS[255])


def test_color_relationships_continuous_custom() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", properties={"weight": 10}),
        Relationship(id="r2", source="2", target="1", properties={"weight": 18}),
        Relationship(id="r3", source="1", target="2", properties={"weight": 30}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    colors = [(0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255)]
    VG.color_relationships(property="weight", colors=colors, color_space=ColorSpace.CONTINUOUS)

    assert VG.relationships[0].color == Color("black")
    assert VG.relationships[1].color == Color((85, 85, 85))
    assert VG.relationships[2].color == Color("white")


def test_color_relationships_unhashable() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(
            id="r1",
            source="1",
            target="2",
            properties={"config": {"sub": ["a", "b"]}},
        ),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    with pytest.raises(ValueError, match="Unable to color relationships by unhashable property type '<class 'dict'>'"):
        VG.color_relationships(property="config", colors=["#000000"])


def test_color_relationships_override_false() -> None:
    """Test that override=False preserves existing colors."""
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", caption="ACTED_IN", color="#FF0000"),
        Relationship(id="r2", source="2", target="1", caption="DIRECTED", color="#FF0000"),
        Relationship(id="r3", source="1", target="2", caption="DIRECTED"),
    ]

    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    # Call with override=False - should preserve existing colors
    VG.color_relationships(field="caption", colors={"ACTED_IN": "#000000", "DIRECTED": "#00FF00"}, override=False)

    assert VG.relationships[0].color == Color("#ff0000")  # Should keep existing color
    assert VG.relationships[1].color == Color("#ff0000")  # Should keep existing color
    assert VG.relationships[2].color == Color("#00ff00")  # Should get new color (no existing color)

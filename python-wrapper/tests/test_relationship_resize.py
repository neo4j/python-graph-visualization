import pytest

from neo4j_viz import Node, Relationship, VisualizationGraph


def test_resize_relationships_dict() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", width=1.0),
        Relationship(id="r2", source="2", target="1", width=2.0),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    VG.resize_relationships(widths={"r1": 5.0, "r2": 10.0})

    assert VG.relationships[0].width == 5.0
    assert VG.relationships[1].width == 10.0


def test_resize_relationships_property() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", properties={"weight": 1.5}),
        Relationship(id="r2", source="2", target="1", properties={"weight": 3.0}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    VG.resize_relationships(property="weight")

    assert VG.relationships[0].width == 1.5
    assert VG.relationships[1].width == 3.0


def test_resize_relationships_property_missing_uses_existing() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [
        Relationship(id="r1", source="1", target="2", width=1.0, properties={"weight": 5.0}),
        Relationship(id="r2", source="2", target="1", width=2.0, properties={}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    VG.resize_relationships(property="weight")

    assert VG.relationships[0].width == 5.0
    assert VG.relationships[1].width == 2.0


def test_resize_relationships_invalid_arguments() -> None:
    VG = VisualizationGraph(nodes=[], relationships=[])

    with pytest.raises(ValueError, match="At least one of `widths` or `property` must be given"):
        VG.resize_relationships()

    with pytest.raises(ValueError, match="At most one of the arguments `widths` and `property` can be provided"):
        VG.resize_relationships(widths={"r1": 1}, property="weight")


def test_resize_relationships_validation() -> None:
    nodes = [Node(id="1"), Node(id="2")]
    relationships = [Relationship(id="r1", source="1", target="2")]
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    with pytest.raises(ValueError, match="Width for relationship 'r1' must be a real number, but was invalid"):
        VG.resize_relationships(widths={"r1": "invalid"})  # type: ignore

    with pytest.raises(ValueError, match="Width for relationship 'r1' must be positive, but was 0"):
        VG.resize_relationships(widths={"r1": 0})

    with pytest.raises(ValueError, match="Width for relationship 'r1' must be positive, but was -1"):
        VG.resize_relationships(widths={"r1": -1})

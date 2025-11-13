import pytest

from neo4j_viz import Node, VisualizationGraph


def test_set_node_captions_from_property() -> None:
    """Test setting captions from a node property."""
    nodes = [
        Node(id="1", properties={"name": "Alice", "age": 30}),
        Node(id="2", properties={"name": "Bob", "age": 25}),
        Node(id="3", properties={"name": "Charlie", "age": 35}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(property="name")

    assert VG.nodes[0].caption == "Alice"
    assert VG.nodes[1].caption == "Bob"
    assert VG.nodes[2].caption == "Charlie"


def test_set_node_captions_from_field() -> None:
    """Test setting captions from a node field."""
    nodes = [
        Node(id="node-1", properties={"name": "Alice"}),
        Node(id="node-2", properties={"name": "Bob"}),
        Node(id="node-3", properties={"name": "Charlie"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(field="id")

    assert VG.nodes[0].caption == "node-1"
    assert VG.nodes[1].caption == "node-2"
    assert VG.nodes[2].caption == "node-3"


def test_set_node_captions_override_true() -> None:
    """Test that override=True replaces existing captions."""
    nodes = [
        Node(id="1", caption="OldCaption1", properties={"name": "Alice"}),
        Node(id="2", caption="OldCaption2", properties={"name": "Bob"}),
        Node(id="3", properties={"name": "Charlie"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(property="name", override=True)

    assert VG.nodes[0].caption == "Alice"
    assert VG.nodes[1].caption == "Bob"
    assert VG.nodes[2].caption == "Charlie"


def test_set_node_captions_override_false() -> None:
    """Test that override=False preserves existing captions."""
    nodes = [
        Node(id="1", caption="ExistingCaption", properties={"name": "Alice"}),
        Node(id="2", properties={"name": "Bob"}),
        Node(id="3", caption="AnotherCaption", properties={"name": "Charlie"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(property="name", override=False)

    assert VG.nodes[0].caption == "ExistingCaption"  # Not overridden
    assert VG.nodes[1].caption == "Bob"  # Set (was None)
    assert VG.nodes[2].caption == "AnotherCaption"  # Not overridden


def test_set_node_captions_missing_property() -> None:
    """Test behavior when property is missing from some nodes."""
    nodes = [
        Node(id="1", properties={"name": "Alice"}),
        Node(id="2", properties={"age": 25}),  # No "name" property
        Node(id="3", properties={"name": "Charlie"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(property="name")

    assert VG.nodes[0].caption == "Alice"
    assert VG.nodes[1].caption == ""  # Empty string for missing property
    assert VG.nodes[2].caption == "Charlie"


def test_set_node_captions_numeric_property() -> None:
    """Test setting captions from numeric properties."""
    nodes = [
        Node(id="1", properties={"score": 100}),
        Node(id="2", properties={"score": 200}),
        Node(id="3", properties={"score": 300}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(property="score")

    assert VG.nodes[0].caption == "100"
    assert VG.nodes[1].caption == "200"
    assert VG.nodes[2].caption == "300"


def test_set_node_captions_field_and_property_both_provided() -> None:
    """Test that providing both field and property raises an error."""
    nodes = [Node(id="1", properties={"name": "Alice"})]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.raises(ValueError, match="Exactly one of the arguments"):
        VG.set_node_captions(field="id", property="name")


def test_set_node_captions_neither_field_nor_property() -> None:
    """Test that providing neither field nor property raises an error."""
    nodes = [Node(id="1", properties={"name": "Alice"})]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.raises(ValueError, match="Exactly one of the arguments"):
        VG.set_node_captions()


def test_set_node_captions_field_with_snake_case() -> None:
    """Test that field names are converted to snake_case."""
    nodes = [
        Node(id="1", caption_size=1, properties={"name": "Alice"}),
        Node(id="2", caption_size=2, properties={"name": "Bob"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(field="captionSize")

    assert VG.nodes[0].caption == "1"
    assert VG.nodes[1].caption == "2"


def test_set_node_captions_empty_graph() -> None:
    """Test setting captions on an empty graph."""
    VG = VisualizationGraph(nodes=[], relationships=[])

    # Should not raise an error
    VG.set_node_captions(property="name")

    assert len(VG.nodes) == 0


def test_set_node_captions_complex_property_values() -> None:
    """Test setting captions from properties with complex types."""
    nodes = [
        Node(id="1", properties={"tags": ["tag1", "tag2"]}),
        Node(id="2", properties={"metadata": {"key": "value"}}),
        Node(id="3", properties={"value": None}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_captions(property="tags")
    assert VG.nodes[0].caption == "['tag1', 'tag2']"
    assert VG.nodes[1].caption == ""
    assert VG.nodes[2].caption == ""

    VG.set_node_captions(property="metadata")
    assert VG.nodes[0].caption == ""
    assert VG.nodes[1].caption == "{'key': 'value'}"
    assert VG.nodes[2].caption == ""

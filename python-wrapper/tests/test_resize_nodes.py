import re

import pytest

from neo4j_viz import Node, VisualizationGraph
from neo4j_viz.node import NodeIdType
from neo4j_viz.node_size import RealNumber, verify_radii


def test_verify_radii() -> None:
    with pytest.raises(ValueError, match="`node_radius_min_max` must be a tuple of two values, but was 3"):
        verify_radii(3)  # type: ignore

    with pytest.raises(
        ValueError, match=re.escape("`node_radius_min_max` must be a tuple of two values, but was (1, 2, 3)")
    ):
        verify_radii((1, 2, 3))  # type: ignore

    with pytest.raises(ValueError, match="Minimum node size must be a real number, but was of type <class 'str'>"):
        verify_radii(("1", 2))  # type: ignore

    with pytest.raises(ValueError, match="Maximum node size must be a real number, but was of type <class 'str'>"):
        verify_radii((1, "2"))  # type: ignore

    with pytest.raises(ValueError, match="Minimum node size must be non-negative, but was -1"):
        verify_radii((-1, 2))

    with pytest.raises(ValueError, match="Maximum node size must be non-negative, but was -2"):
        verify_radii((1, -2))

    with pytest.raises(
        ValueError, match="Minimum node size must be less than or equal to maximum node size, but was 2 > 1"
    ):
        verify_radii((2, 1))

    # This should not raise an exception
    verify_radii((1, 2))


def test_resize_nodes_either_sizes_or_property() -> None:
    nodes = [
        Node(id=42),
        Node(id="1337", size=10),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    with pytest.raises(ValueError, match="At most one of the arguments `sizes` and `property` can be provided"):
        VG.resize_nodes(sizes={"1337": 20}, property="size", node_radius_min_max=(3, 60))


def test_resize_nodes_no_scaling() -> None:
    nodes = [
        Node(id=42),
        Node(id="1337", size=10),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    new_sizes: dict[NodeIdType, RealNumber] = {"1337": 20}
    VG.resize_nodes(new_sizes, None)

    assert VG.nodes[0].size is None
    assert VG.nodes[1].size == 20

    new_sizes = {42: 8.1, "1337": 3}
    VG.resize_nodes(new_sizes, None)

    assert VG.nodes[0].size == 8.1
    assert VG.nodes[1].size == 3

    new_sizes = {42: -4.2}
    with pytest.raises(ValueError, match="Size for node '42' must be non-negative, but was -4.2"):
        VG.resize_nodes(new_sizes, None)


def test_resize_nodes_by_property() -> None:
    nodes = [
        Node(id=42, properties={"age": 4}),
        Node(id="1337", properties={"age": 2}),
        Node(id=55, properties={"age": 8}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.resize_nodes(property="age", node_radius_min_max=None)

    assert VG.nodes[0].size == 4
    assert VG.nodes[1].size == 2
    assert VG.nodes[2].size == 8

    VG.resize_nodes(property="age", node_radius_min_max=(1, 4))

    assert VG.nodes[0].size == 2
    assert VG.nodes[1].size == 1
    assert VG.nodes[2].size == 4


def test_resize_nodes_with_scaling_constant() -> None:
    nodes = [
        Node(id=42),
        Node(id="1337", size=10),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    new_sizes: dict[NodeIdType, RealNumber] = {"1337": 20}
    VG.resize_nodes(new_sizes, (3, 60))

    assert VG.nodes[0].size is None
    # Should just be the default since min == max in VG (only one node)
    assert VG.nodes[1].size == 3 + (60 - 3) / 2.0


def test_resize_nodes_with_scaling_all_sizes_provided() -> None:
    nodes = [
        Node(id=42, size=10),
        Node(id=43, size=10),
        Node(id="1337", size=15),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    new_sizes: dict[NodeIdType, RealNumber] = {42: 18, 43: 19, "1337": 20}
    VG.resize_nodes(new_sizes, (3, 60))

    assert VG.nodes[0].size == 3
    assert VG.nodes[1].size == 3 + (60 - 3) / 2.0
    assert VG.nodes[2].size == 60


def test_resize_nodes_with_scaling_some_sizes_provided() -> None:
    nodes = [
        Node(id=42, size=10),
        Node(id="1337", size=15),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    new_sizes: dict[NodeIdType, RealNumber] = {"1337": 1}
    VG.resize_nodes(new_sizes, (3, 60))

    assert VG.nodes[0].size == 60
    assert VG.nodes[1].size == 3


def test_resize_nodes_with_scaling_only() -> None:
    nodes = [
        Node(id=42, size=10),
        Node(id=43, size=10),
        Node(id="1337", size=15),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.resize_nodes(node_radius_min_max=(3, 60))

    assert VG.nodes[0].size == 3
    assert VG.nodes[1].size == 3
    assert VG.nodes[2].size == 60


def test_resize_nodes_no_args_failure() -> None:
    VG = VisualizationGraph(nodes=[], relationships=[])

    with pytest.raises(ValueError, match="At least one of `sizes`, `property` or `node_radius_min_max` must be given"):
        VG.resize_nodes(node_radius_min_max=None)

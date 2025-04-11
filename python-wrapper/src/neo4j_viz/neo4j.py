from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Optional, Union

import neo4j.graph
from neo4j import Result

from neo4j_viz.node import Node
from neo4j_viz.relationship import Relationship
from neo4j_viz.visualization_graph import VisualizationGraph


def from_neo4j(
    result: Union[neo4j.graph.Graph, Result],
    size_property: Optional[str] = None,
    node_caption: Optional[str] = "labels",
    relationship_caption: Optional[str] = "type",
    node_radius_min_max: Optional[tuple[float, float]] = (3, 60),
) -> VisualizationGraph:
    """
    Create a VisualizationGraph from a Neo4j Graph or Neo4j Result object.

    All node and relationship properties will be included in the visualization graph.
    If the property names are conflicting with those of `Node` and `Relationship` objects, they will be prefixed
    with `__`.

    Parameters
    ----------
    result : Union[neo4j.graph.Graph, Result]
        Query result either in shape of a Graph or result.
    size_property : str, optional
        Property to use for node size, by default None.
    node_caption : str, optional
        Property to use as the node caption, by default the node labels will be used.
    relationship_caption : str, optional
        Property to use as the relationship caption, by default the relationship type will be used.
    node_radius_min_max : tuple[float, float], optional
        Minimum and maximum node radius, by default (3, 60).
        To avoid tiny or huge nodes in the visualization, the node sizes are scaled to fit in the given range.
    """

    if isinstance(result, Result):
        graph = result.graph()
    elif isinstance(result, neo4j.graph.Graph):
        graph = result
    else:
        raise ValueError(f"Invalid input type `{type(result)}`. Expected `neo4j.Graph` or `neo4j.Result`")

    nodes = [_map_node(node, size_property, caption_property=node_caption) for node in graph.nodes]
    relationships = []
    for rel in graph.relationships:
        mapped_rel = _map_relationship(rel, caption_property=relationship_caption)
        if mapped_rel:
            relationships.append(mapped_rel)

    VG = VisualizationGraph(nodes, relationships)

    if node_radius_min_max and size_property is not None:
        VG.resize_nodes(node_radius_min_max=node_radius_min_max)

    return VG


def _map_node(node: neo4j.graph.Node, size_property: Optional[str], caption_property: Optional[str]) -> Node:
    labels = sorted([label for label in node.labels])

    if size_property:
        size = node.get(size_property)
    else:
        size = None

    if caption_property:
        if caption_property == "labels":
            if len(labels) > 0:
                caption = ":".join([label for label in labels])
            else:
                caption = None
        else:
            caption = str(node.get(caption_property))

    properties = {k: v for k, v in node.items()}
    properties["__labels"] = labels

    return Node(id=node.element_id, caption=caption, size=size, properties=properties)


def _map_relationship(rel: neo4j.graph.Relationship, caption_property: Optional[str]) -> Optional[Relationship]:
    if rel.start_node is None or rel.end_node is None:
        return None

    if caption_property:
        if caption_property == "type":
            caption = rel.type
        else:
            caption = str(rel.get(caption_property))
    else:
        caption = None

    properties = {k: v for k, v in rel.items()}
    properties["__type"] = rel.type

    return Relationship(
        id=rel.element_id,
        source=rel.start_node.element_id,
        target=rel.end_node.element_id,
        caption=caption,
        properties=properties,
    )

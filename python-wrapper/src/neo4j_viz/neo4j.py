from __future__ import annotations

import warnings
from typing import Optional, Union

import neo4j.graph
from neo4j import Driver, Result, RoutingControl
from pydantic import BaseModel, ValidationError

from neo4j_viz.colors import NEO4J_COLORS_DISCRETE, ColorSpace
from neo4j_viz.node import Node
from neo4j_viz.relationship import Relationship
from neo4j_viz.visualization_graph import VisualizationGraph


def _parse_validation_error(e: ValidationError, entity_type: type[BaseModel]) -> None:
    for err in e.errors():
        loc = err["loc"][0]
        raise ValueError(
            f"Error for {entity_type.__name__.lower()} property '{loc}' with provided input '{err['input']}'. Reason: {err['msg']}"
        )


def from_neo4j(
    data: Union[neo4j.graph.Graph, Result, Driver],
    row_limit: int = 10_000,
) -> VisualizationGraph:
    """
    Create a VisualizationGraph from a Neo4j `Graph`, Neo4j `Result` or Neo4j `Driver`.

    By default:

    * the caption of a node will be based on its `labels`.
    * the caption of a relationship will be based on its `type`.
    * the color of nodes will be set based on their label, unless there are more than 12 unique labels.

    All node and relationship properties will be included in the visualization graph under the `properties` field.
    Additionally, a "labels" property will be added for nodes and a "type" property for relationships.

    Parameters
    ----------
    data : Union[neo4j.graph.Graph, neo4j.Result, neo4j.Driver]
        Either a query result in the shape of a `neo4j.graph.Graph` or `neo4j.Result`, or a `neo4j.Driver` in
        which case a simple default query will be executed internally to retrieve the graph data.
    row_limit : int, optional
        Maximum number of rows to return from the query, by default 10_000.
        This is only used if a `neo4j.Driver` is passed as `result` argument, otherwise the limit is ignored.
    """

    if isinstance(data, Result):
        graph = data.graph()
    elif isinstance(data, neo4j.graph.Graph):
        graph = data
    elif isinstance(data, Driver):
        rel_count = data.execute_query(
            "MATCH ()-[r]->() RETURN count(r) as count",
            routing_=RoutingControl.READ,
            result_transformer_=Result.single,
        ).get("count")  # type: ignore[union-attr]
        if rel_count > row_limit:
            warnings.warn(
                f"Database relationship count ({rel_count}) exceeds `row_limit` ({row_limit}), so limiting will be applied. Increase the `row_limit` if needed"
            )
        graph = data.execute_query(
            f"MATCH (n)-[r]->(m) RETURN n,r,m LIMIT {row_limit}",
            routing_=RoutingControl.READ,
            result_transformer_=Result.graph,
        )
    else:
        raise ValueError(f"Invalid input type `{type(data)}`. Expected `neo4j.Graph`, `neo4j.Result` or `neo4j.Driver`")

    nodes = [_map_node(node) for node in graph.nodes]

    relationships = []

    for rel in graph.relationships:
        mapped_rel = _map_relationship(rel)
        if mapped_rel:
            relationships.append(mapped_rel)

    VG = VisualizationGraph(nodes, relationships)

    for node in VG.nodes:
        node.caption = ":".join(node.properties["labels"])
    for r in VG.relationships:
        r.caption = r.properties["type"]

    number_of_colors = len({n.caption for n in VG.nodes})
    if number_of_colors <= len(NEO4J_COLORS_DISCRETE):
        VG.color_nodes(field="caption", color_space=ColorSpace.DISCRETE, colors=NEO4J_COLORS_DISCRETE)

    return VG


def _map_node(
    node: neo4j.graph.Node,
) -> Node:
    labels = sorted([label for label in node.labels])

    properties = {prop: value for prop, value in node.items()}

    if "labels" in properties:
        properties["__labels"] = properties["labels"]
    properties["labels"] = labels

    try:
        viz_node = Node(id=node.element_id, properties=properties)
    except ValidationError as e:
        _parse_validation_error(e, Node)

    return viz_node


def _map_relationship(rel: neo4j.graph.Relationship) -> Optional[Relationship]:
    if rel.start_node is None or rel.end_node is None:
        return None

    properties = {prop: value for prop, value in rel.items()}

    if "type" in properties:
        properties["__type"] = properties["type"]
    properties["type"] = rel.type

    try:
        viz_rel = Relationship(
            id=rel.element_id, source=rel.start_node.element_id, target=rel.end_node.element_id, properties=properties
        )
    except ValidationError as e:
        _parse_validation_error(e, Relationship)

    return viz_rel

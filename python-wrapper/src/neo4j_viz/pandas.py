from __future__ import annotations

from collections.abc import Iterable
from typing import Optional, Union

from pandas import DataFrame
from pydantic import BaseModel, ValidationError

from .node import Node
from .relationship import Relationship
from .visualization_graph import VisualizationGraph

DFS_TYPE = Union[DataFrame, Iterable[DataFrame]]


def _parse_validation_error(e: ValidationError, entity_type: type[BaseModel]) -> None:
    for err in e.errors():
        loc = err["loc"][0]
        if err["type"] == "missing":
            raise ValueError(
                f"Mandatory {entity_type.__name__.lower()} column '{loc}' is missing. Expected one of {entity_type.model_fields[loc].validation_alias.choices} to be present"  # type: ignore
            )
        else:
            raise ValueError(
                f"Error for {entity_type.__name__.lower()} column '{loc}' with provided input '{err['input']}'. Reason: {err['msg']}"
            )


def _from_dfs(
    node_dfs: Optional[DFS_TYPE] = None,
    rel_dfs: Optional[DFS_TYPE] = None,
    dropna: bool = False,
) -> VisualizationGraph:
    if node_dfs is None and rel_dfs is None:
        raise ValueError("At least one of `node_dfs` or `rel_dfs` must be provided")

    if rel_dfs is None:
        relationships = []
    else:
        relationships = _parse_relationships(rel_dfs, dropna=dropna)

    if node_dfs is None:
        node_ids = set()
        for rel in relationships:
            node_ids.add(rel.source)
            node_ids.add(rel.target)
        nodes = [Node(id=id) for id in node_ids]
    else:
        nodes = _parse_nodes(node_dfs, dropna=dropna)

    return VisualizationGraph(nodes=nodes, relationships=relationships)


def _parse_nodes(node_dfs: DFS_TYPE, dropna: bool = False) -> list[Node]:
    if isinstance(node_dfs, DataFrame):
        node_dfs_iter: Iterable[DataFrame] = [node_dfs]
    elif node_dfs is None:
        node_dfs_iter = []
    else:
        node_dfs_iter = node_dfs

    basic_node_fields_aliases = Node.basic_fields_validation_aliases()

    nodes = []
    for node_df in node_dfs_iter:
        for _, row in node_df.iterrows():
            if dropna:
                row = row.dropna(inplace=False)
            mandatory_fields = {}
            properties = {}
            for key, value in row.to_dict().items():
                if key in basic_node_fields_aliases:
                    mandatory_fields[key] = value
                else:
                    properties[key] = value

            try:
                nodes.append(Node(**mandatory_fields, properties=properties))
            except ValidationError as e:
                _parse_validation_error(e, Node)

    return nodes


def _parse_relationships(rel_dfs: DFS_TYPE, dropna: bool = False) -> list[Relationship]:
    basic_rel_field_aliases = Relationship.basic_fields_validation_aliases()

    if isinstance(rel_dfs, DataFrame):
        rel_dfs_iter: Iterable[DataFrame] = [rel_dfs]
    else:
        rel_dfs_iter = rel_dfs
    relationships: list[Relationship] = []

    for rel_df in rel_dfs_iter:
        for _, row in rel_df.iterrows():
            if dropna:
                row = row.dropna(inplace=False)
            mandatory_fields = {}
            properties = {}
            for key, value in row.to_dict().items():
                if key in basic_rel_field_aliases:
                    mandatory_fields[key] = value
                else:
                    properties[key] = value

            try:
                relationships.append(Relationship(**mandatory_fields, properties=properties))
            except ValidationError as e:
                _parse_validation_error(e, Relationship)

    return relationships


def from_dfs(
    node_dfs: Optional[DFS_TYPE] = None,
    rel_dfs: Optional[DFS_TYPE] = None,
) -> VisualizationGraph:
    """
    Create a VisualizationGraph from pandas DataFrames representing a graph.

    All columns will be included in the visualization graph.
    The following columns will be treated as fields:

        * `id` for the node_dfs
        * `id`, `source`, `target` for the rel_dfs

    Other columns will be included in the `properties` dictionary on the respective node or relationship objects.

    Parameters
    ----------
    node_dfs: Optional[Union[DataFrame, Iterable[DataFrame]]], optional
        DataFrame or iterable of DataFrames containing node data.
        If None, the nodes will be created from the source and target node ids in the rel_dfs.
    rel_dfs: Optional[Union[DataFrame, Iterable[DataFrame]]], optional
        DataFrame or iterable of DataFrames containing relationship data.
        If None, no relationships will be created.

    """

    return _from_dfs(node_dfs, rel_dfs, dropna=False)

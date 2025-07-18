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
    node_radius_min_max: Optional[tuple[float, float]] = (3, 60),
    rename_properties: Optional[dict[str, str]] = None,
    dropna: bool = False,
) -> VisualizationGraph:
    if node_dfs is None and rel_dfs is None:
        raise ValueError("At least one of `node_dfs` or `rel_dfs` must be provided")

    if rel_dfs is None:
        relationships = []
    else:
        relationships = _parse_relationships(rel_dfs, rename_properties=rename_properties, dropna=dropna)

    if node_dfs is None:
        has_size = False
        node_ids = set()
        for rel in relationships:
            node_ids.add(rel.source)
            node_ids.add(rel.target)
        nodes = [Node(id=id) for id in node_ids]
    else:
        nodes, has_size = _parse_nodes(node_dfs, rename_properties=rename_properties, dropna=dropna)

    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    if node_radius_min_max is not None and has_size:
        VG.resize_nodes(node_radius_min_max=node_radius_min_max)

    return VG


def _parse_nodes(
    node_dfs: DFS_TYPE, rename_properties: Optional[dict[str, str]], dropna: bool = False
) -> tuple[list[Node], bool]:
    if isinstance(node_dfs, DataFrame):
        node_dfs_iter: Iterable[DataFrame] = [node_dfs]
    elif node_dfs is None:
        node_dfs_iter = []
    else:
        node_dfs_iter = node_dfs

    all_node_field_aliases = Node.all_validation_aliases()

    has_size = True
    nodes = []
    for node_df in node_dfs_iter:
        has_size &= "size" in [c.lower() for c in node_df.columns]
        for _, row in node_df.iterrows():
            if dropna:
                row = row.dropna(inplace=False)
            top_level = {}
            properties = {}
            for key, value in row.to_dict().items():
                if key in all_node_field_aliases:
                    top_level[key] = value
                else:
                    if rename_properties and key in rename_properties:
                        key = rename_properties[key]
                    properties[key] = value

            try:
                nodes.append(Node(**top_level, properties=properties))
            except ValidationError as e:
                _parse_validation_error(e, Node)

    return nodes, has_size


def _parse_relationships(
    rel_dfs: DFS_TYPE, rename_properties: Optional[dict[str, str]], dropna: bool = False
) -> list[Relationship]:
    all_rel_field_aliases = Relationship.all_validation_aliases()

    if isinstance(rel_dfs, DataFrame):
        rel_dfs_iter: Iterable[DataFrame] = [rel_dfs]
    else:
        rel_dfs_iter = rel_dfs
    relationships: list[Relationship] = []

    for rel_df in rel_dfs_iter:
        for _, row in rel_df.iterrows():
            if dropna:
                row = row.dropna(inplace=False)
            top_level = {}
            properties = {}
            for key, value in row.to_dict().items():
                if key in all_rel_field_aliases:
                    top_level[key] = value
                else:
                    if rename_properties and key in rename_properties:
                        key = rename_properties[key]
                    properties[key] = value

            try:
                relationships.append(Relationship(**top_level, properties=properties))
            except ValidationError as e:
                _parse_validation_error(e, Relationship)

    return relationships


def from_dfs(
    node_dfs: Optional[DFS_TYPE] = None,
    rel_dfs: Optional[DFS_TYPE] = None,
    node_radius_min_max: Optional[tuple[float, float]] = (3, 60),
) -> VisualizationGraph:
    """
    Create a VisualizationGraph from pandas DataFrames representing a graph.

    All columns will be included in the visualization graph.
    If the columns are named as the fields of the `Node` or `Relationship` classes, they will be included as
    top level fields of the respective objects. Otherwise, they will be included in the `properties` dictionary.

    Parameters
    ----------
    node_dfs: Optional[Union[DataFrame, Iterable[DataFrame]]], optional
        DataFrame or iterable of DataFrames containing node data.
        If None, the nodes will be created from the source and target node ids in the rel_dfs.
    rel_dfs: Optional[Union[DataFrame, Iterable[DataFrame]]], optional
        DataFrame or iterable of DataFrames containing relationship data.
        If None, no relationships will be created.
    node_radius_min_max : tuple[float, float], optional
        Minimum and maximum node radius.
        To avoid tiny or huge nodes in the visualization, the node sizes are scaled to fit in the given range.
    """

    return _from_dfs(node_dfs, rel_dfs, node_radius_min_max, dropna=False)

from __future__ import annotations

from itertools import chain
from typing import Optional

import pandas as pd
from graphdatascience import Graph, GraphDataScience

from .pandas import _from_dfs
from .visualization_graph import VisualizationGraph


def _node_dfs(
    gds: GraphDataScience, G: Graph, node_properties: list[str], node_labels: list[str]
) -> dict[str, pd.DataFrame]:
    return {
        lbl: gds.graph.nodeProperties.stream(
            G, node_properties=node_properties, node_labels=[lbl], separate_property_columns=True
        )
        for lbl in node_labels
    }


def _rel_df(gds: GraphDataScience, G: Graph) -> pd.DataFrame:
    relationship_properties = G.relationship_properties()

    if len(relationship_properties) > 0:
        if isinstance(relationship_properties, pd.Series):
            relationship_properties_per_type = relationship_properties.tolist()
            property_set: set[str] = set()
            for props in relationship_properties_per_type:
                if props:
                    property_set.update(props)

        return gds.graph.relationshipProperties.stream(
            G, relationship_properties=list(property_set), separate_property_columns=True
        )

    return gds.graph.relationships.stream(G)


def from_gds(
    gds: GraphDataScience,
    G: Graph,
    size_property: Optional[str] = None,
    additional_node_properties: Optional[list[str]] = None,
    node_radius_min_max: Optional[tuple[float, float]] = (3, 60),
) -> VisualizationGraph:
    """
    Create a VisualizationGraph from a GraphDataScience object and a Graph object.

    All `additional_node_properties` will be included in the visualization graph.
    If the properties are named as the fields of the `Node` class, they will be included as top level fields of the
    created `Node` objects. Otherwise, they will be included in the `properties` dictionary.
    Additionally, a new "labels" node property will be added, containing the node labels of the node.

    Parameters
    ----------
    gds : GraphDataScience
        GraphDataScience object.
    G : Graph
        Graph object.
    size_property : str, optional
        Property to use for node size, by default None.
    additional_node_properties : list[str], optional
        Additional properties to include in the visualization node, by default None. They can be used later for modifying the node appearance.
    node_radius_min_max : tuple[float, float], optional
        Minimum and maximum node radius, by default (3, 60).
        To avoid tiny or huge nodes in the visualization, the node sizes are scaled to fit in the given range.
    """
    node_properties_from_gds = G.node_properties()
    assert isinstance(node_properties_from_gds, pd.Series)
    actual_node_properties = list(chain.from_iterable(node_properties_from_gds.to_dict().values()))

    if size_property is not None and size_property not in actual_node_properties:
        raise ValueError(f"There is no node property '{size_property}' in graph '{G.name()}'")

    if additional_node_properties is not None:
        for prop in additional_node_properties:
            if prop not in actual_node_properties:
                raise ValueError(f"There is no node property '{prop}' in graph '{G.name()}'")

    node_properties = set()
    if additional_node_properties is not None:
        node_properties.update(additional_node_properties)

    if size_property is not None:
        node_properties.add(size_property)

    node_properties = list(node_properties)
    node_dfs = _node_dfs(gds, G, node_properties, G.node_labels())
    for df in node_dfs.values():
        df.rename(columns={"nodeId": "id"}, inplace=True)

    node_props_df = pd.concat(node_dfs.values(), ignore_index=True, axis=0).drop_duplicates()
    if size_property is not None:
        if "size" in actual_node_properties and size_property != "size":
            node_props_df.rename(columns={"size": "__size"}, inplace=True)
        node_props_df.rename(columns={size_property: "size"}, inplace=True)

    for lbl, df in node_dfs.items():
        if "labels" in actual_node_properties:
            df.rename(columns={"labels": "__labels"}, inplace=True)
        df["labels"] = lbl

    node_labels_df = pd.concat([df[["id", "labels"]] for df in node_dfs.values()], ignore_index=True, axis=0)
    node_labels_df = node_labels_df.groupby("id").agg({"labels": list})

    node_df = node_props_df.merge(node_labels_df, on="id")

    rel_df = _rel_df(gds, G)
    rel_df.rename(columns={"sourceNodeId": "source", "targetNodeId": "target"}, inplace=True)

    try:
        return _from_dfs(node_df, rel_df, node_radius_min_max=node_radius_min_max, rename_properties={"__size": "size"})
    except ValueError as e:
        err_msg = str(e)
        if "column" in err_msg:
            err_msg = err_msg.replace("column", "property")
            if ("'size'" in err_msg) and (size_property is not None):
                err_msg = err_msg.replace("'size'", f"'{size_property}'")
            raise ValueError(err_msg)
        raise e

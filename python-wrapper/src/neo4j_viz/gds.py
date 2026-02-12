from __future__ import annotations

import warnings
from itertools import chain
from typing import Optional, cast
from uuid import uuid4

import pandas as pd
from graphdatascience import Graph, GraphDataScience

from neo4j_viz.colors import NEO4J_COLORS_DISCRETE, ColorSpace

from .pandas import _from_dfs
from .visualization_graph import VisualizationGraph


def _fetch_node_dfs(
    gds: GraphDataScience,
    G: Graph,
    node_properties_by_label: dict[str, list[str]],
    node_labels: list[str],
    additional_db_node_properties: list[str],
) -> dict[str, pd.DataFrame]:
    return {
        lbl: gds.graph.nodeProperties.stream(
            G,
            node_properties=node_properties_by_label[lbl],
            node_labels=[lbl],
            separate_property_columns=True,
            db_node_properties=additional_db_node_properties,
        )
        for lbl in node_labels
    }


def _fetch_rel_dfs(gds: GraphDataScience, G: Graph) -> list[pd.DataFrame]:
    rel_types = G.relationship_types()

    rel_props = {rel_type: G.relationship_properties(rel_type) for rel_type in rel_types}

    rel_dfs: list[pd.DataFrame] = []
    # Have to call per stream per relationship type as there was a bug in GDS < 2.21
    for rel_type, props in rel_props.items():
        assert isinstance(props, list)
        if len(props) > 0:
            rel_df = gds.graph.relationshipProperties.stream(
                G, relationship_types=rel_type, relationship_properties=list(props), separate_property_columns=True
            )
        else:
            rel_df = gds.graph.relationships.stream(G, relationship_types=[rel_type])

        rel_dfs.append(rel_df)

    return rel_dfs


def from_gds(
    gds: GraphDataScience,
    G: Graph,
    node_properties: Optional[list[str]] = None,
    db_node_properties: Optional[list[str]] = None,
    max_node_count: int = 10_000,
) -> VisualizationGraph:
    """
    Create a VisualizationGraph from a GraphDataScience object and a Graph object.

    By default:

    * the caption of a node will be based on its `labels`.
    * the caption of a relationship will be based on its `relationshipType`.
    * the color of nodes will be set based on their label, unless there are more than 12 unique labels.

    All `node_properties` and `db_node_properties` will be included in the visualization graph under the `properties` field.
    Additionally, a new "labels" node property will be added, containing the node labels of the node.
    Similarly for relationships, a new "relationshipType" property will be added.

    Parameters
    ----------
    gds : GraphDataScience
        GraphDataScience object.
    G : Graph
        Graph object.
    node_properties : list[str], optional
        Additional properties to include in the visualization node, by default None which means that all node
        properties from the Graph will be fetched.
    db_node_properties : list[str], optional
        Additional node properties to fetch from the database, by default None. Only works if the graph was projected from the database.
    max_node_count : int, optional
        The maximum number of nodes to fetch from the graph. The graph will be sampled using random walk with restarts
        if its node count exceeds this number.
    """
    if db_node_properties is None:
        db_node_properties = []

    node_properties_from_gds = G.node_properties()
    assert isinstance(node_properties_from_gds, pd.Series)
    actual_node_properties: dict[str, list[str]] = cast(dict[str, list[str]], node_properties_from_gds.to_dict())
    all_actual_node_properties = list(chain.from_iterable(actual_node_properties.values()))

    node_properties_by_label_sets: dict[str, set[str]] = dict()
    if node_properties is None:
        node_properties_by_label_sets = {k: set(v) for k, v in actual_node_properties.items()}
    else:
        for prop in node_properties:
            if prop not in all_actual_node_properties:
                raise ValueError(f"There is no node property '{prop}' in graph '{G.name()}'")

        for label, props in actual_node_properties.items():
            node_properties_by_label_sets[label] = {
                prop for prop in actual_node_properties[label] if prop in node_properties
            }

    node_properties_by_label = {k: list(v) for k, v in node_properties_by_label_sets.items()}

    node_count = G.node_count()
    if node_count > max_node_count:
        warnings.warn(
            f"The '{G.name()}' projection's node count ({G.node_count()}) exceeds `max_node_count` ({max_node_count}), so subsampling will be applied. Increase `max_node_count` if needed"
        )
        sampling_ratio = float(max_node_count) / node_count
        sample_name = f"neo4j-viz_sample_{uuid4()}"
        G_fetched, _ = gds.graph.sample.rwr(sample_name, G, samplingRatio=sampling_ratio, nodeLabelStratification=True)
    else:
        G_fetched = G

    property_name = None
    try:
        # Since GDS does not allow us to only fetch node IDs, we add the degree property
        # as a temporary property to ensure that we have at least one property for each label to fetch
        if sum([len(props) == 0 for props in node_properties_by_label.values()]) > 0:
            property_name = f"neo4j-viz_property_{uuid4()}"
            gds.degree.mutate(G_fetched, mutateProperty=property_name)
            for props in node_properties_by_label.values():
                props.append(property_name)

        node_dfs = _fetch_node_dfs(
            gds, G_fetched, node_properties_by_label, G_fetched.node_labels(), db_node_properties
        )
        if property_name is not None:
            for df in node_dfs.values():
                df.drop(columns=[property_name], inplace=True)

        rel_dfs = _fetch_rel_dfs(gds, G_fetched)
    finally:
        if G_fetched.name() != G.name():
            G_fetched.drop()
        elif property_name is not None:
            gds.graph.nodeProperties.drop(G_fetched, node_properties=[property_name])

    for df in node_dfs.values():
        if property_name is not None and property_name in df.columns:
            df.drop(columns=[property_name], inplace=True)

    node_props_df = pd.concat(node_dfs.values(), ignore_index=True, axis=0).drop_duplicates(subset=["nodeId"])

    for lbl, df in node_dfs.items():
        if "labels" in all_actual_node_properties:
            df.rename(columns={"labels": "__labels"}, inplace=True)
        df["labels"] = lbl

    node_labels_df = pd.concat([df[["nodeId", "labels"]] for df in node_dfs.values()], ignore_index=True, axis=0)
    node_labels_df = node_labels_df.groupby("nodeId").agg({"labels": list})

    node_df = node_props_df.merge(node_labels_df, on="nodeId")

    try:
        VG = _from_dfs(node_df, rel_dfs, dropna=True)

        for node in VG.nodes:
            node.caption = ":".join([label for label in node.properties["labels"]])
        for rel in VG.relationships:
            rel.caption = rel.properties.get("relationshipType")

        number_of_colors = node_df["labels"].drop_duplicates().count()
        if number_of_colors <= len(NEO4J_COLORS_DISCRETE):
            VG.color_nodes(property="labels", color_space=ColorSpace.DISCRETE)

        return VG
    except ValueError as e:
        err_msg = str(e)
        if "column" in err_msg:
            err_msg = err_msg.replace("column", "property")
            raise ValueError(err_msg)
        raise e

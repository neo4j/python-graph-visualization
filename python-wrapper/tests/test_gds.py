from typing import Any

import pandas as pd
import pytest
from pytest_mock import MockerFixture

from neo4j_viz import Node


@pytest.mark.requires_neo4j_and_gds
def test_from_gds_integration(gds: Any) -> None:
    from neo4j_viz.gds import from_gds

    nodes = pd.DataFrame(
        {
            "nodeId": [0, 1, 2],
            "labels": [["A"], ["C"], ["A", "B"]],
            "score": [1337, 42, 3.14],
            "component": [1, 4, 2],
        }
    )
    rels = pd.DataFrame(
        {
            "sourceNodeId": [0, 1, 2],
            "targetNodeId": [1, 2, 0],
            "relationshipType": ["REL", "REL2", "REL"],
        }
    )

    with gds.graph.construct("flo", nodes, rels) as G:
        VG = from_gds(
            gds, G, size_property="score", additional_node_properties=["component"], node_radius_min_max=(3.14, 1337)
        )

        assert len(VG.nodes) == 3
        assert sorted(VG.nodes, key=lambda x: x.id) == [
            Node(id=0, labels=["A"], size=float(1337), component=float(1)),
            Node(id=1, labels=["C"], size=float(42), component=float(4)),
            Node(id=2, labels=["A", "B"], size=float(3.14), component=float(2)),
        ]

        assert len(VG.relationships) == 3
        vg_rels = sorted([(e.source, e.target, e.relationshipType) for e in VG.relationships], key=lambda x: x[0])  # type: ignore[attr-defined]
        assert vg_rels == [
            (0, 1, "REL"),
            (1, 2, "REL2"),
            (2, 0, "REL"),
        ]


def test_from_gds_mocked(mocker: MockerFixture) -> None:
    from graphdatascience import Graph, GraphDataScience

    from neo4j_viz.gds import from_gds

    nodes = {
        "A": pd.DataFrame(
            {
                "nodeId": [0, 2],
                "score": [1337, 3.14],
                "component": [1, 2],
            }
        ),
        "B": pd.DataFrame(
            {
                "nodeId": [2],
                "score": [3.14],
                "component": [2],
            }
        ),
        "C": pd.DataFrame(
            {
                "nodeId": [1],
                "score": [42],
                "component": [4],
            }
        ),
    }
    rels = pd.DataFrame(
        {
            "sourceNodeId": [0, 1, 2],
            "targetNodeId": [1, 2, 0],
            "relationshipType": ["REL", "REL2", "REL"],
        }
    )

    mocker.patch(
        "graphdatascience.Graph.__init__",
        lambda x: None,
    )
    mocker.patch(
        "graphdatascience.Graph.name",
        lambda x: "DUMMY",
    )
    node_properties = ["score", "component"]
    mocker.patch(
        "graphdatascience.Graph.node_properties",
        lambda x: pd.Series({lbl: node_properties for lbl in nodes.keys()}),
    )
    mocker.patch("graphdatascience.Graph.node_labels", lambda x: list(nodes.keys()))
    mocker.patch("graphdatascience.GraphDataScience.__init__", lambda x: None)
    mocker.patch("neo4j_viz.gds._node_dfs", return_value=nodes)
    mocker.patch("neo4j_viz.gds._rel_df", return_value=rels)

    gds = GraphDataScience()  # type: ignore[call-arg]
    G = Graph()  # type: ignore[call-arg]

    VG = from_gds(
        gds, G, size_property="score", additional_node_properties=["component"], node_radius_min_max=(3.14, 1337)
    )

    assert len(VG.nodes) == 3
    assert sorted(VG.nodes, key=lambda x: x.id) == [
        Node(id=0, labels=["A"], size=float(1337), component=float(1)),
        Node(id=1, labels=["C"], size=float(42), component=float(4)),
        Node(id=2, labels=["A", "B"], size=float(3.14), component=float(2)),
    ]

    assert len(VG.relationships) == 3
    vg_rels = sorted([(e.source, e.target, e.relationship_type) for e in VG.relationships], key=lambda x: x[0])  # type: ignore[attr-defined]
    assert vg_rels == [
        (0, 1, "REL"),
        (1, 2, "REL2"),
        (2, 0, "REL"),
    ]

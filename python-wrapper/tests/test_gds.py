import re
from typing import Any

import pandas as pd
import pytest
from pytest_mock import MockerFixture

from neo4j_viz import Node


@pytest.mark.requires_neo4j_and_gds
def test_from_gds_integration_size(gds: Any) -> None:
    from neo4j_viz.gds import from_gds

    nodes = pd.DataFrame(
        {
            "nodeId": [0, 1, 2],
            "labels": [["A"], ["C"], ["A", "B"]],
            "score": [1337, 42, 3.14],
            "component": [1, 4, 2],
            "size": [0.1, 0.2, 0.3],
        }
    )
    rels = pd.DataFrame(
        {
            "sourceNodeId": [0, 1, 2],
            "targetNodeId": [1, 2, 0],
            "cost": [1.0, 2.0, 3.0],
            "weight": [0.5, 1.5, 2.5],
            "relationshipType": ["REL", "REL2", "REL"],
        }
    )

    with gds.graph.construct("flo", nodes, rels) as G:
        VG = from_gds(
            gds,
            G,
            size_property="score",
            additional_node_properties=["component", "size"],
            node_radius_min_max=(3.14, 1337),
        )

        assert len(VG.nodes) == 3
        assert sorted(VG.nodes, key=lambda x: x.id) == [
            Node(id=0, size=float(1337), caption="['A']", properties=dict(labels=["A"], component=float(1), size=0.1)),
            Node(id=1, size=float(42), caption="['C']", properties=dict(labels=["C"], component=float(4), size=0.2)),
            Node(
                id=2,
                size=float(3.14),
                caption="['A', 'B']",
                properties=dict(labels=["A", "B"], component=float(2), size=0.3),
            ),
        ]

        assert len(VG.relationships) == 3
        vg_rels = sorted(
            [
                (
                    e.source,
                    e.target,
                    e.caption,
                    e.properties["relationshipType"],
                    e.properties["cost"],
                    e.properties["weight"],
                )
                for e in VG.relationships
            ],
            key=lambda x: x[0],
        )
        assert vg_rels == [
            (0, 1, "REL", "REL", 1.0, 0.5),
            (1, 2, "REL2", "REL2", 2.0, 1.5),
            (2, 0, "REL", "REL", 3.0, 2.5),
        ]


@pytest.mark.requires_neo4j_and_gds
def test_from_gds_integration_all_properties(gds: Any) -> None:
    from neo4j_viz.gds import from_gds

    nodes = pd.DataFrame(
        {
            "nodeId": [0, 1, 2],
            "labels": [["A"], ["C"], ["A", "B"]],
            "score": [1337, 42, 3.14],
            "component": [1, 4, 2],
            "size": [0.1, 0.2, 0.3],
        }
    )
    rels = pd.DataFrame(
        {
            "sourceNodeId": [0, 1, 2],
            "targetNodeId": [1, 2, 0],
            "cost": [1.0, 2.0, 3.0],
            "weight": [0.5, 1.5, 2.5],
            "relationshipType": ["REL", "REL2", "REL"],
        }
    )

    with gds.graph.construct("flo", nodes, rels) as G:
        VG = from_gds(
            gds,
            G,
            node_radius_min_max=None,
        )

        assert len(VG.nodes) == 3
        assert sorted(VG.nodes, key=lambda x: x.id) == [
            Node(id=0, size=0.1, caption="['A']", properties=dict(labels=["A"], component=float(1), score=1337.0)),
            Node(id=1, size=0.2, caption="['C']", properties=dict(labels=["C"], component=float(4), score=42.0)),
            Node(
                id=2, size=0.3, caption="['A', 'B']", properties=dict(labels=["A", "B"], component=float(2), score=3.14)
            ),
        ]

        assert len(VG.relationships) == 3
        vg_rels = sorted(
            [
                (
                    e.source,
                    e.target,
                    e.caption,
                    e.properties["relationshipType"],
                    e.properties["cost"],
                    e.properties["weight"],
                )
                for e in VG.relationships
            ],
            key=lambda x: x[0],
        )
        assert vg_rels == [
            (0, 1, "REL", "REL", 1.0, 0.5),
            (1, 2, "REL2", "REL2", 2.0, 1.5),
            (2, 0, "REL", "REL", 3.0, 2.5),
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
    rels = [
        pd.DataFrame(
            {
                "sourceNodeId": [0, 1, 2],
                "targetNodeId": [1, 2, 0],
                "relationshipType": ["REL", "REL2", "REL"],
            }
        )
    ]

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
    mocker.patch("graphdatascience.Graph.node_count", lambda x: sum(len(df) for df in nodes.values()))
    mocker.patch("graphdatascience.GraphDataScience.__init__", lambda x: None)
    mocker.patch("neo4j_viz.gds._fetch_node_dfs", return_value=nodes)
    mocker.patch("neo4j_viz.gds._fetch_rel_dfs", return_value=rels)

    gds = GraphDataScience()  # type: ignore[call-arg]
    G = Graph()  # type: ignore[call-arg]

    VG = from_gds(
        gds,
        G,
        size_property="score",
        additional_node_properties=["component", "score"],
        node_radius_min_max=(3.14, 1337),
    )

    assert len(VG.nodes) == 3
    assert sorted(VG.nodes, key=lambda x: x.id) == [
        Node(
            id=0,
            caption="['A']",
            size=float(1337),
            properties=dict(labels=["A"], component=float(1), score=float(1337)),
        ),
        Node(id=1, caption="['C']", size=float(42), properties=dict(labels=["C"], component=float(4), score=float(42))),
        Node(
            id=2,
            caption="['A', 'B']",
            size=float(3.14),
            properties=dict(labels=["A", "B"], component=float(2), score=float(3.14)),
        ),
    ]

    assert len(VG.relationships) == 3
    vg_rels = sorted(
        [(e.source, e.target, e.caption, e.properties["relationshipType"]) for e in VG.relationships],
        key=lambda x: x[0],
    )
    assert vg_rels == [
        (0, 1, "REL", "REL"),
        (1, 2, "REL2", "REL2"),
        (2, 0, "REL", "REL"),
    ]


@pytest.mark.requires_neo4j_and_gds
def test_from_gds_node_errors(gds: Any) -> None:
    from neo4j_viz.gds import from_gds

    nodes = pd.DataFrame(
        {
            "nodeId": [0, 1, 2],
            "labels": [["A"], ["C"], ["A", "B"]],
            "component": [1, 4, 2],
            "score": [1337, -42, 3.14],
            "size": [-0.1, 0.2, 0.3],
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
        with pytest.raises(
            ValueError,
            match=r"Error for node property 'size' with provided input '-0.1'. Reason: Input should be greater than or equal to 0",
        ):
            from_gds(
                gds,
                G,
                additional_node_properties=["component", "size"],
                node_radius_min_max=None,
            )

    with gds.graph.construct("flo", nodes, rels) as G:
        with pytest.raises(
            ValueError,
            match=r"Error for node property 'score' with provided input '-42.0'. Reason: Input should be greater than or equal to 0",
        ):
            from_gds(
                gds,
                G,
                size_property="score",
                additional_node_properties=["component", "size"],
                node_radius_min_max=None,
            )


@pytest.mark.requires_neo4j_and_gds
def test_from_gds_sample(gds: Any) -> None:
    from neo4j_viz.gds import from_gds

    with gds.graph.generate("hello", node_count=11_000, average_degree=1) as G:
        with pytest.warns(
            UserWarning,
            match=re.escape(
                "The 'hello' projection's node count (11000) exceeds `max_node_count` (10000), so subsampling will be applied. Increase `max_node_count` if needed"
            ),
        ):
            VG = from_gds(gds, G)

        # Make sure internal temporary properties are not present
        assert set(VG.nodes[0].properties.keys()) == {"labels"}

        assert len(VG.nodes) >= 9_500
        assert len(VG.nodes) <= 10_500
        assert len(VG.relationships) >= 9_500
        assert len(VG.relationships) <= 10_500


@pytest.mark.requires_neo4j_and_gds
def test_from_gds_hetero(gds: Any) -> None:
    from neo4j_viz.gds import from_gds

    A_nodes = pd.DataFrame(
        {
            "nodeId": [0, 1],
            "labels": ["A", "A"],
            "component": [1, 2],
        }
    )
    B_nodes = pd.DataFrame(
        {
            "nodeId": [2, 3],
            "labels": ["B", "B"],
            # No 'component' property
        }
    )
    X_rels = pd.DataFrame(
        {
            "sourceNodeId": [1],
            "targetNodeId": [3],
            "weight": [1.5],
            "relationshipType": ["X"],
        }
    )
    Y_rels = pd.DataFrame(
        {
            "sourceNodeId": [0],
            "targetNodeId": [2],
            "score": [1],
            "relationshipType": ["Y"],
        }
    )

    with gds.graph.construct("flo", [A_nodes, B_nodes], [X_rels, Y_rels]) as G:
        VG = from_gds(
            gds,
            G,
        )

        assert len(VG.nodes) == 4
        assert sorted(VG.nodes, key=lambda x: x.id) == [
            Node(id=0, caption="['A']", properties=dict(labels=["A"], component=float(1))),
            Node(id=1, caption="['A']", properties=dict(labels=["A"], component=float(2))),
            Node(id=2, caption="['B']", properties=dict(labels=["B"])),
            Node(id=3, caption="['B']", properties=dict(labels=["B"])),
        ]

        assert len(VG.relationships) == 2
        vg_rels = sorted(
            [
                (
                    e.source,
                    e.target,
                    e.caption,
                    e.properties,
                )
                for e in VG.relationships
            ],
            key=lambda x: x[0],
        )
        assert vg_rels == [
            (0, 2, "Y", {"relationshipType": "Y", "score": 1.0}),
            (1, 3, "X", {"relationshipType": "X", "weight": 1.5}),
        ]

import re
from typing import Any, Generator

import pandas as pd
import pytest

from neo4j_viz import Node


@pytest.fixture(scope="class")
def db_setup(gds: Any) -> Generator[None, None, None]:
    gds.run_cypher(
        "CREATE "
        "  (a:_CI_A {name:'Alice', height:20, id:42, _id: 1337, caption: 'hello'})"
        " ,(b:_CI_A:_CI_B {name:'Bob', height:10, id: 84, size: 11, labels: [1,2]})"
        " ,(a)-[:KNOWS {year: 2025, id: 41, source: 1, target: 2}]->(b)"
        " ,(b)-[:RELATED {year: 2015, _type: 'A', caption:'hej'}]->(a)"
    )
    yield
    gds.run_cypher("MATCH (n:_CI_A|_CI_B) DETACH DELETE n")


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.requires_neo4j_and_gds
def test_from_gds_integration_all_db_properties(gds: Any, db_setup: None) -> None:
    from neo4j_viz.gds import from_gds

    with gds.graph.project("g2", ["_CI_A", "_CI_B"], "*") as G:
        VG = from_gds(gds, G, db_node_properties=["name"])

        assert len(VG.nodes) == 2
        assert {n.properties["name"] for n in VG.nodes} == {"Alice", "Bob"}


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
        VG = from_gds(gds, G)

        assert len(VG.nodes) == 3
        assert sorted(VG.nodes, key=lambda x: x.id) == [
            Node(
                id=0,
                caption="A",
                color="#ffdf81",
                properties=dict(size=0.1, labels=["A"], component=float(1), score=1337.0),
            ),
            Node(
                id=1,
                caption="C",
                color="#f79767",
                properties=dict(size=0.2, labels=["C"], component=float(4), score=42.0),
            ),
            Node(
                id=2,
                caption="A:B",
                color="#c990c0",
                properties=dict(size=0.3, labels=["A", "B"], component=float(2), score=3.14),
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
            Node(id=0, caption="A", color="#ffdf81", properties=dict(labels=["A"], component=float(1))),
            Node(id=1, caption="A", color="#ffdf81", properties=dict(labels=["A"], component=float(2))),
            Node(id=2, caption="B", color="#c990c0", properties=dict(labels=["B"])),
            Node(id=3, caption="B", color="#c990c0", properties=dict(labels=["B"])),
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

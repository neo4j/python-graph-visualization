from typing import Generator

import neo4j
import pytest
from neo4j import Session

from neo4j_viz.neo4j import from_neo4j
from neo4j_viz.node import Node


@pytest.fixture(scope="class", autouse=True)
def graph_setup(neo4j_session: Session) -> Generator[None, None, None]:
    neo4j_session.run(
        "CREATE (a:_CI_A {name:'Alice', height:20, id:42, _id: 1337, caption: 'hello'})-[:KNOWS {year: 2025, id: 41, source: 1, target: 2}]->"
        "(b:_CI_A:_CI_B {name:'Bob', height:10, id: 84, size: 11, labels: [1,2]}), (b)-[:RELATED {year: 2015, _type: 'A', caption:'hej'}]->(a)"
    )
    yield
    neo4j_session.run("MATCH (n:_CI_A|_CI_B) DETACH DELETE n")


@pytest.mark.requires_neo4j_and_gds
def test_from_neo4j_graph(neo4j_session: Session) -> None:
    graph = neo4j_session.run("MATCH (a:_CI_A|_CI_B)-[r]->(b) RETURN a, b, r ORDER BY a").graph()

    VG = from_neo4j(graph)

    sorted_nodes: list[neo4j.graph.Node] = sorted(graph.nodes, key=lambda x: dict(x.items())["name"])
    node_ids: list[str] = [node.element_id for node in sorted_nodes]

    expected_nodes = [
        Node(
            id=node_ids[0],
            caption="_CI_A",
            properties=dict(
                __labels=["_CI_A"],
                name="Alice",
                height=20,
                _id=1337,
                caption="hello",
            )
        ),
        Node(
            id=node_ids[1],
            caption="_CI_A:_CI_B",
            properties=dict(
                __labels=["_CI_A", "_CI_B"],
                name="Bob",
                height=10,
                size=11,
                labels=[1, 2],
            ),
        ),
    ]

    assert len(VG.nodes) == 2
    assert sorted(VG.nodes, key=lambda x: x.properties["name"]) == expected_nodes  # type: ignore[attr-defined]

    assert len(VG.relationships) == 2
    vg_rels = sorted([(e.source, e.target, e.caption) for e in VG.relationships], key=lambda x: x[2] if x[2] else "foo")
    assert vg_rels == [
        (node_ids[0], node_ids[1], "KNOWS"),
        (node_ids[1], node_ids[0], "RELATED"),
    ]


@pytest.mark.requires_neo4j_and_gds
def test_from_neo4j_result(neo4j_session: Session) -> None:
    result = neo4j_session.run("MATCH (a:_CI_A|_CI_B)-[r]->(b) RETURN a, b, r ORDER BY a")

    VG = from_neo4j(result)

    graph = result.graph()

    sorted_nodes: list[neo4j.graph.Node] = sorted(graph.nodes, key=lambda x: dict(x.items())["name"])
    node_ids: list[str] = [node.element_id for node in sorted_nodes]

    expected_nodes = [
        Node(
            id=node_ids[0],
            caption="_CI_A",
            properties=dict(
                __labels=["_CI_A"],
                name="Alice",
                height=20,
                _id=1337,
                caption="hello",
            )
        ),
        Node(
            id=node_ids[1],
            caption="_CI_A:_CI_B",
            properties=dict(
                __labels=["_CI_A", "_CI_B"],
                name="Bob",
                height=10,
                size=11,
                labels=[1, 2],
            )
        ),
    ]

    assert len(VG.nodes) == 2
    assert sorted(VG.nodes, key=lambda x: x.properties["name"]) == expected_nodes  # type: ignore[attr-defined]

    assert len(VG.relationships) == 2
    vg_rels = sorted([(e.source, e.target, e.caption) for e in VG.relationships], key=lambda x: x[2] if x[2] else "foo")
    assert vg_rels == [
        (node_ids[0], node_ids[1], "KNOWS"),
        (node_ids[1], node_ids[0], "RELATED"),
    ]


@pytest.mark.requires_neo4j_and_gds
def test_from_neo4j_graph_full(neo4j_session: Session) -> None:
    graph = neo4j_session.run("MATCH (a:_CI_A|_CI_B)-[r]->(b) RETURN a, b, r ORDER BY a").graph()

    VG = from_neo4j(graph, node_caption="name", relationship_caption="year", size_property="height")

    sorted_nodes: list[neo4j.graph.Node] = sorted(graph.nodes, key=lambda x: dict(x.items())["name"])
    node_ids: list[str] = [node.element_id for node in sorted_nodes]

    expected_nodes = [
        Node(
            id=node_ids[0],
            caption="Alice",
            size=60.0,
            properties=dict(
                __labels=["_CI_A"],
                name="Alice",
                height=20,
                _id=1337,
                caption="hello",
            )
        ),
        Node(
            id=node_ids[1],
            caption="Bob",
            size=3.0,
            properties=dict(
                __labels=["_CI_A", "_CI_B"],
                name="Bob",
                height=10,
                size=11,
                labels=[1, 2],
            ),
        ),
    ]

    assert len(VG.nodes) == 2
    assert sorted(VG.nodes, key=lambda x: x.properties["name"]) == expected_nodes  # type: ignore[attr-defined]

    assert len(VG.relationships) == 2
    vg_rels = sorted([(e.source, e.target, e.caption) for e in VG.relationships], key=lambda x: x[2] if x[2] else "foo")
    assert vg_rels == [
        (node_ids[1], node_ids[0], "2015"),
        (node_ids[0], node_ids[1], "2025"),
    ]

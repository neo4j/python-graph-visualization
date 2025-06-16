import re
from typing import Generator

import neo4j
import pytest
from neo4j import Driver, Session

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
def test_from_neo4j_graph_basic(neo4j_session: Session) -> None:
    graph = neo4j_session.run("MATCH (a:_CI_A|_CI_B)-[r]->(b) RETURN a, b, r ORDER BY a").graph()

    VG = from_neo4j(graph)

    sorted_nodes: list[neo4j.graph.Node] = sorted(graph.nodes, key=lambda x: dict(x.items())["name"])
    node_ids: list[str] = [node.element_id for node in sorted_nodes]

    expected_nodes = [
        Node(
            id=node_ids[0],
            caption="_CI_A",
            properties=dict(
                labels=["_CI_A"],
                name="Alice",
                height=20,
                id=42,
                _id=1337,
                caption="hello",
            ),
        ),
        Node(
            id=node_ids[1],
            caption="_CI_A:_CI_B",
            size=11,
            properties=dict(
                labels=["_CI_A", "_CI_B"],
                name="Bob",
                height=10,
                id=84,
                __labels=[1, 2],
            ),
        ),
    ]

    assert len(VG.nodes) == 2
    assert sorted(VG.nodes, key=lambda x: x.properties["name"]) == expected_nodes

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
                labels=["_CI_A"],
                name="Alice",
                height=20,
                id=42,
                _id=1337,
                caption="hello",
            ),
        ),
        Node(
            id=node_ids[1],
            caption="_CI_A:_CI_B",
            size=11,
            properties=dict(
                labels=["_CI_A", "_CI_B"],
                name="Bob",
                height=10,
                id=84,
                __labels=[1, 2],
            ),
        ),
    ]

    assert len(VG.nodes) == 2
    assert sorted(VG.nodes, key=lambda x: x.properties["name"]) == expected_nodes

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
                labels=["_CI_A"],
                name="Alice",
                height=20,
                id=42,
                _id=1337,
                caption="hello",
            ),
        ),
        Node(
            id=node_ids[1],
            caption="Bob",
            size=3.0,
            properties=dict(
                labels=["_CI_A", "_CI_B"],
                name="Bob",
                size=11,
                height=10,
                id=84,
                __labels=[1, 2],
            ),
        ),
    ]

    assert len(VG.nodes) == 2
    assert sorted(VG.nodes, key=lambda x: x.properties["name"]) == expected_nodes

    assert len(VG.relationships) == 2
    vg_rels = sorted([(e.source, e.target, e.caption) for e in VG.relationships], key=lambda x: x[2] if x[2] else "foo")
    assert vg_rels == [
        (node_ids[1], node_ids[0], "2015"),
        (node_ids[0], node_ids[1], "2025"),
    ]


@pytest.mark.requires_neo4j_and_gds
def test_from_neo4j_node_error(neo4j_session: Session) -> None:
    neo4j_session.run("MATCH (n:_CI_A|_CI_B) DETACH DELETE n")
    neo4j_session.run(
        "CREATE (a:_CI_A {name:'Alice', height:20, id:42, _id: 1337, caption: 'hello', caption_size: -5})"
    )
    graph = neo4j_session.run("MATCH (a:_CI_A) RETURN a").graph()

    with pytest.raises(
        ValueError,
        match="Error for node property 'caption_size' with provided input '-5'. Reason: Input should be greater than or equal to 1",
    ):
        from_neo4j(graph)

    neo4j_session.run("MATCH (n:_CI_A|_CI_B) DETACH DELETE n")
    neo4j_session.run("CREATE (a:_CI_A {name:'Alice', height:20, id:42, _id: 1337, hello: -5})")
    graph = neo4j_session.run("MATCH (a:_CI_A) RETURN a").graph()
    with pytest.raises(
        ValueError,
        match="Error for node property 'hello' with provided input '-5'. Reason: Input should be greater than or equal to 0",
    ):
        from_neo4j(graph, size_property="hello")


@pytest.mark.requires_neo4j_and_gds
def test_from_neo4j_rel_error(neo4j_session: Session) -> None:
    neo4j_session.run("MATCH (n:_CI_A|_CI_B) DETACH DELETE n")
    neo4j_session.run(
        "CREATE (a:_CI_A {name:'Alice', height:20, id:42, _id: 1337, caption: 'hello'})-[:KNOWS {year: 2025, id: 41, source: 1, target: 2, caption_align: 'banana'}]->"
        "(b:_CI_A:_CI_B {name:'Bob', height:10, id: 84, size: 11, labels: [1,2]})"
    )
    graph = neo4j_session.run("MATCH (a:_CI_A|_CI_B)-[r]->(b) RETURN a, b, r ORDER BY a").graph()

    with pytest.raises(
        ValueError,
        match="Error for relationship property 'caption_align' with provided input 'banana'. Reason: Input should be 'top', 'center' or 'bottom'",
    ):
        from_neo4j(graph)


@pytest.mark.requires_neo4j_and_gds
def test_from_neo4j_graph_driver(neo4j_session: Session, neo4j_driver: Driver) -> None:
    graph = neo4j_session.run("MATCH (a:_CI_A|_CI_B)-[r]->(b) RETURN a, b, r ORDER BY a").graph()

    # Note that this tests requires an empty Neo4j database, as it just fetches everything
    VG = from_neo4j(neo4j_driver)

    sorted_nodes: list[neo4j.graph.Node] = sorted(graph.nodes, key=lambda x: dict(x.items())["name"])
    node_ids: list[str] = [node.element_id for node in sorted_nodes]

    expected_nodes = [
        Node(
            id=node_ids[0],
            caption="_CI_A",
            properties=dict(
                labels=["_CI_A"],
                name="Alice",
                height=20,
                id=42,
                _id=1337,
                caption="hello",
            ),
        ),
        Node(
            id=node_ids[1],
            caption="_CI_A:_CI_B",
            size=11,
            properties=dict(
                labels=["_CI_A", "_CI_B"],
                name="Bob",
                height=10,
                id=84,
                __labels=[1, 2],
            ),
        ),
    ]

    assert len(VG.nodes) == 2
    assert sorted(VG.nodes, key=lambda x: x.properties["name"]) == expected_nodes

    assert len(VG.relationships) == 2
    vg_rels = sorted([(e.source, e.target, e.caption) for e in VG.relationships], key=lambda x: x[2] if x[2] else "foo")
    assert vg_rels == [
        (node_ids[0], node_ids[1], "KNOWS"),
        (node_ids[1], node_ids[0], "RELATED"),
    ]


@pytest.mark.requires_neo4j_and_gds
def test_from_neo4j_graph_row_limit_warning(neo4j_session: Session, neo4j_driver: Driver) -> None:
    neo4j_session.run("MATCH (a:_CI_A|_CI_B)-[r]->(b) RETURN a, b, r ORDER BY a").graph()

    with pytest.warns(
        UserWarning,
        match=re.escape(
            "Database relationship count (2) exceeds `row_limit` (1), so limiting will be applied. Increase the `row_limit` if needed"
        ),
    ):
        VG = from_neo4j(neo4j_driver, row_limit=1)

    assert len(VG.relationships) == 1

import neo4j.graph

from neo4j_viz.neo4j import find_graph_entity


def _make_graph() -> neo4j.graph.Graph:
    return neo4j.graph.Graph()


def _make_node(
    graph: neo4j.graph.Graph, element_id: str, labels: list[str], props: dict[str, object]
) -> neo4j.graph.Node:
    return neo4j.graph.Node(graph, element_id, hash(element_id), labels, props)


def _make_rel(
    graph: neo4j.graph.Graph,
    element_id: str,
    rel_type: str,
    start: neo4j.graph.Node,
    end: neo4j.graph.Node,
    props: dict[str, object] | None = None,
) -> neo4j.graph.Relationship:
    RelType = graph.relationship_type(rel_type)
    rel = RelType.__new__(RelType)
    rel.__dict__.update(
        {
            "_graph": graph,
            "_element_id": element_id,
            "_id": hash(element_id),
            "_properties": props or {},
            "_start_node": start,
            "_end_node": end,
        }
    )
    return rel


def test_plain_node() -> None:
    g = _make_graph()
    node = _make_node(g, "n1", ["A"], {"x": 1})
    assert find_graph_entity(node) is g


def test_plain_relationship() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    assert find_graph_entity(rel) is g


def test_path() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    path = neo4j.graph.Path(a, rel)
    assert find_graph_entity(path) is g


def test_list_of_nodes() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    value = [a, b]
    assert find_graph_entity(value) is g


def test_nested_list() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    value = [[a]]
    assert find_graph_entity(value) is g


def test_dict_of_nodes() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    value = {"key": a}
    assert find_graph_entity(value) is g


def test_deduplication() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    value = [a, a]
    assert find_graph_entity(value) is g


def test_scalar_ignored() -> None:
    assert find_graph_entity("hello") is None
    assert find_graph_entity(42) is None
    assert find_graph_entity(None) is None


def test_mixed_list_with_graph_entities_and_scalars() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    value = ["hello", rel, 42, None]
    assert find_graph_entity(value) is g


def test_mixed_dict_with_graph_entities_and_scalars() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    value = {"text": "hello", "node": a, "count": 42, "empty": None}
    assert find_graph_entity(value) is g

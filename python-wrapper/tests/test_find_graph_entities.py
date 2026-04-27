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


def _find_graph(value: object) -> neo4j.graph.Graph | None:
    return find_graph_entity(value, {}, {})


def test_plain_node() -> None:
    g = _make_graph()
    node = _make_node(g, "n1", ["A"], {"x": 1})
    assert _find_graph(node) is g


def test_plain_relationship() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    assert _find_graph(rel) is g


def test_path() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    path = neo4j.graph.Path(a, rel)
    assert _find_graph(path) is g


def test_list_of_nodes() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    assert _find_graph([a, b]) is g


def test_nested_list() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    assert _find_graph([[a]]) is g


def test_dict_of_nodes() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    assert _find_graph({"key": a}) is g


def test_deduplication() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    assert _find_graph([a, a]) is g


def test_scalar_ignored() -> None:
    assert _find_graph("hello") is None
    assert _find_graph(42) is None
    assert _find_graph(None) is None


def test_mixed_list_with_graph_entities_and_scalars() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    assert _find_graph(["hello", rel, 42, None]) is g


def test_mixed_dict_with_graph_entities_and_scalars() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    assert _find_graph({"text": "hello", "node": a, "count": 42, "empty": None}) is g

import neo4j.graph

from neo4j_viz.neo4j import _collect_graph_entities


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
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities(node, nodes, rels)
    assert "n1" in nodes
    assert rels == {}


def test_plain_relationship() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities(rel, nodes, rels)
    assert "r1" in rels
    assert nodes == {}


def test_path() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    path = neo4j.graph.Path(a, rel)
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities(path, nodes, rels)
    assert set(nodes) == {"a", "b"}
    assert set(rels) == {"r1"}


def test_list_of_nodes() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities([a, b], nodes, rels)
    assert set(nodes) == {"a", "b"}


def test_nested_list() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities([[a]], nodes, rels)
    assert "a" in nodes


def test_dict_of_nodes() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities({"key": a}, nodes, rels)
    assert "a" in nodes


def test_deduplication() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities([a, a], nodes, rels)
    assert len(nodes) == 1


def test_scalar_ignored() -> None:
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities("hello", nodes, rels)
    _collect_graph_entities(42, nodes, rels)
    _collect_graph_entities(None, nodes, rels)
    assert nodes == {} and rels == {}


def test_mixed_list_with_path_and_node() -> None:
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    c = _make_node(g, "c", ["C"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    path = neo4j.graph.Path(a, rel)
    nodes: dict[str, neo4j.graph.Node] = {}
    rels: dict[str, neo4j.graph.Relationship] = {}
    _collect_graph_entities([path, c], nodes, rels)
    assert set(nodes) == {"a", "b", "c"}
    assert set(rels) == {"r1"}

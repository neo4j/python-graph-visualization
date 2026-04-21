import neo4j.graph

from neo4j_viz.neo4j import _collect_graph_entities


def _make_graph():
    return neo4j.graph.Graph()


def _make_node(graph, element_id: str, labels: list[str], props: dict):
    return neo4j.graph.Node(graph, element_id, hash(element_id), labels, props)


def _make_rel(graph, element_id: str, rel_type: str, start, end, props: dict = {}):
    RelType = graph.relationship_type(rel_type)
    rel = RelType.__new__(RelType)
    rel.__dict__.update({
        "_graph": graph,
        "_element_id": element_id,
        "_id": hash(element_id),
        "_properties": props,
        "_start_node": start,
        "_end_node": end,
    })
    return rel


def test_plain_node():
    g = _make_graph()
    node = _make_node(g, "n1", ["A"], {"x": 1})
    nodes, rels = {}, {}
    _collect_graph_entities(node, nodes, rels)
    assert "n1" in nodes
    assert rels == {}


def test_plain_relationship():
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    nodes, rels = {}, {}
    _collect_graph_entities(rel, nodes, rels)
    assert "r1" in rels
    assert nodes == {}


def test_path():
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    path = neo4j.graph.Path(a, rel)
    nodes, rels = {}, {}
    _collect_graph_entities(path, nodes, rels)
    assert set(nodes) == {"a", "b"}
    assert set(rels) == {"r1"}


def test_list_of_nodes():
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    nodes, rels = {}, {}
    _collect_graph_entities([a, b], nodes, rels)
    assert set(nodes) == {"a", "b"}


def test_nested_list():
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    nodes, rels = {}, {}
    _collect_graph_entities([[a]], nodes, rels)
    assert "a" in nodes


def test_dict_of_nodes():
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    nodes, rels = {}, {}
    _collect_graph_entities({"key": a}, nodes, rels)
    assert "a" in nodes


def test_deduplication():
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    nodes, rels = {}, {}
    _collect_graph_entities([a, a], nodes, rels)
    assert len(nodes) == 1


def test_scalar_ignored():
    nodes, rels = {}, {}
    _collect_graph_entities("hello", nodes, rels)
    _collect_graph_entities(42, nodes, rels)
    _collect_graph_entities(None, nodes, rels)
    assert nodes == {} and rels == {}


def test_mixed_list_with_path_and_node():
    g = _make_graph()
    a = _make_node(g, "a", ["A"], {})
    b = _make_node(g, "b", ["B"], {})
    c = _make_node(g, "c", ["C"], {})
    rel = _make_rel(g, "r1", "KNOWS", a, b)
    path = neo4j.graph.Path(a, rel)
    nodes, rels = {}, {}
    _collect_graph_entities([path, c], nodes, rels)
    assert set(nodes) == {"a", "b", "c"}
    assert set(rels) == {"r1"}

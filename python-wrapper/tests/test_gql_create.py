import pytest

from neo4j_viz.gql_create import from_gql_create


def test_from_gql_create() -> None:
    query = """
            CREATE
              (a:User {name: 'Alice', age: 23}),
              (b:User:person {name: "Bridget", age: 34}),
              (wizardMan:User {name: 'Charles: The wizard, man', hello: true, height: NULL}),
              (d:User),

              (a)-[:LINK {weight: 0.5}]->(b),

              (e:User {age: 67, my_map: {key: 'value', key2: 3.14, key3: [1, 2, 3], key4: {a: 1, b: null}}}),
              (:User {age: 42, pets: ['cat', false, 'dog']}),

              (f:User&Person


                 {name: 'Fawad', age: 78}),

              (a)-[:LINK {weight: 4}]->(wizardMan),
              (e)-[:LINK]->(d),
              (e)-[:OTHER_LINK {weight: -2}]->(f);
            """
    expected_node_dicts = [
        {"properties": {"name": "Alice", "age": 23, "__labels": ["User"]}},
        {"properties": {"name": "Bridget", "age": 34, "__labels": ["User", "person"]}},
        {"properties": {"name": "Charles: The wizard, man", "hello": True, "height": None, "__labels": ["User"]}},
        {"properties": {"__labels": ["User"]}},
        {
            "properties": {
                "age": 67,
                "my_map": {"key": "value", "key2": 3.14, "key3": [1, 2, 3], "key4": {"a": 1, "b": None}},
                "__labels": ["User"],
            }
        },
        {"properties": {"age": 42, "pets": ["cat", False, "dog"], "__labels": ["User"]}},
        {"properties": {"name": "Fawad", "age": 78, "__labels": ["Person", "User"]}},
    ]

    VG = from_gql_create(query)

    assert len(VG.nodes) == len(expected_node_dicts)
    for i, exp_node in enumerate(expected_node_dicts):
        created_node = VG.nodes[i]

        assert created_node.properties == exp_node["properties"]

    expected_relationships_dicts = [
        {"source_idx": 0, "target_idx": 1, "properties": {"weight": 0.5, "__type": "LINK"}},
        {"source_idx": 0, "target_idx": 2, "properties": {"weight": 4, "__type": "LINK"}},
        {"source_idx": 4, "target_idx": 3, "properties": {"__type": "LINK"}},
        {"source_idx": 4, "target_idx": 6, "properties": {"weight": -2, "__type": "OTHER_LINK"}},
    ]

    assert len(VG.relationships) == len(expected_relationships_dicts)
    for i, exp_rel in enumerate(expected_relationships_dicts):
        created_rel = VG.relationships[i]
        assert created_rel.source == VG.nodes[exp_rel["source_idx"]].id
        assert created_rel.target == VG.nodes[exp_rel["target_idx"]].id
        assert created_rel.properties == exp_rel["properties"]


def test_unbalanced_parentheses_snippet() -> None:
    query = "CREATE (a:User, (b:User })"
    with pytest.raises(ValueError, match=r"Unbalanced parentheses near: `.*\(b:User.*"):
        from_gql_create(query)


def test_node_property_syntax_error_snippet1() -> None:
    query = "CREATE (a:User {x, y:4})"
    with pytest.raises(ValueError, match=r"Property syntax error near: `.*x, y.*"):
        from_gql_create(query)


def test_node_property_syntax_error_snippet2() -> None:
    query = "CREATE (a:User {x:5,, y:4})"
    with pytest.raises(ValueError, match=r"Property syntax error near: `.*x:5,, y.*"):
        from_gql_create(query)


def test_invalid_element_in_create_snippet() -> None:
    query = "CREATE [not_a_node]"
    with pytest.raises(ValueError, match=r"Invalid element in CREATE near: `\[not_a_node.*"):
        from_gql_create(query)


def test_rel_property_syntax_error_snippet() -> None:
    query = "CREATE (a:User), (b:User), (a)-[:LINK {weight0.5}]->(b)"
    with pytest.raises(ValueError, match=r"Property syntax error near: `\), \(a\)-\[:LINK {weight0.5}\]->\(b`."):
        from_gql_create(query)


def test_unknown_node_alias() -> None:
    query = "CREATE (a)-[:LINK {weight0.5}]->(b)"
    with pytest.raises(
        ValueError, match=r"Relationship references unknown node alias: 'a' near: `\(a\)-\[:LINK {weig`"
    ):
        from_gql_create(query)


def test_no_create_keyword() -> None:
    query = "(a:User {y:4})"
    with pytest.raises(ValueError, match=r"Query must begin with 'CREATE' \(case insensitive\)."):
        from_gql_create(query)

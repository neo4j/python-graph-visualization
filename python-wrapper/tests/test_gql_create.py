from typing import Any

import pytest

from neo4j_viz.gql_create import from_gql_create


def test_from_gql_create_syntax() -> None:
    query = """
            CREATE
              (a:User {name: 'Alice', age: 23, labels: ['Happy'], "id": 42}),
              (b:User:person {name: "Bridget", age: 34, "caption": "Bridget"}),
              (wizardMan:User {name: 'Charles: The wizard, man', hello: true, height: NULL}),
              (d:User),
              (a)-[:LINK {weight: 0.5}]->(b),
              (e:User {age: 67, my_map: {key: 'value', key2: 3.14, key3: [1, 2, 3], key4: {a: 1, b: null}}}),
              (:User {age: 42, pets: ['cat', false, 'dog']}),
              (),
              (f:User&Person
                 {name: 'Fawad', age: 78}),
              ({age: 29}),
              (a)-[:LINK {weight: 4}]->(wizardMan),
              (e)-[:LINK]->(d),
              (e)-[:OTHER_LINK {weight: -2, type: 1, source: 1337, caption: "Balloon"}]->(f),
              ()-[:LINK]->({name: 'Florentin'});
            """
    expected_node_dicts: list[dict[str, dict[str, Any]]] = [
        # node a
        {
            "top_level": {"caption": "User", "color": "#ffdf81"},
            "properties": {"name": "Alice", "age": 23, "labels": ["User"], "__labels": ["Happy"], "id": 42},
        },
        # node b
        {
            "top_level": {"caption": "User:person", "color": "#c990c0"},
            "properties": {"name": "Bridget", "caption": "Bridget", "age": 34, "labels": ["User", "person"]},
        },
        # node wizardMan
        {
            "top_level": {"caption": "User", "color": "#ffdf81"},
            "properties": {"name": "Charles: The wizard, man", "hello": True, "height": None, "labels": ["User"]},
        },
        # node d
        {"top_level": {"caption": "User", "color": "#ffdf81"}, "properties": {"labels": ["User"]}},
        # node e
        {
            "top_level": {"caption": "User", "color": "#ffdf81"},
            "properties": {
                "age": 67,
                "my_map": {"key": "value", "key2": 3.14, "key3": [1, 2, 3], "key4": {"a": 1, "b": None}},
                "labels": ["User"],
            },
        },
        # node without alias
        {
            "top_level": {"caption": "User", "color": "#ffdf81"},
            "properties": {"age": 42, "pets": ["cat", False, "dog"], "labels": ["User"]},
        },
        # empty node
        {"top_level": {"caption": "", "color": "#f79767"}, "properties": {"labels": []}},
        # node f
        {
            "top_level": {"caption": "Person:User", "color": "#56c7e4"},
            "properties": {"name": "Fawad", "age": 78, "labels": ["Person", "User"]},
        },
        # node without alias 2
        {"top_level": {"caption": "", "color": "#f79767"}, "properties": {"age": 29, "labels": []}},
        # anonymous node at source of rel to florentin
        {"top_level": {"caption": "", "color": "#f79767"}, "properties": {"labels": []}},
        # anonymous node at target rel
        {"top_level": {"caption": "", "color": "#f79767"}, "properties": {"name": "Florentin", "labels": []}},
    ]

    VG = from_gql_create(query)

    assert len(VG.nodes) == len(expected_node_dicts)
    for i, exp_node in enumerate(expected_node_dicts):
        created_node = VG.nodes[i]

        assert created_node.model_dump(exclude_none=True, exclude={"properties", "id"}) == exp_node["top_level"], (
            f"Failed at node {created_node}"
        )
        assert created_node.properties == exp_node["properties"], f"Failed at node {created_node}"

    expected_relationships_dicts: list[dict[str, Any]] = [
        {
            "source_idx": 0,
            "target_idx": 1,
            "top_level": {"caption": "LINK"},
            "properties": {"weight": 0.5, "type": "LINK"},
        },
        {
            "source_idx": 0,
            "target_idx": 2,
            "top_level": {"caption": "LINK"},
            "properties": {"weight": 4, "type": "LINK"},
        },
        {"source_idx": 4, "target_idx": 3, "top_level": {"caption": "LINK"}, "properties": {"type": "LINK"}},
        {
            "source_idx": 4,
            "target_idx": 7,
            "top_level": {"caption": "OTHER_LINK"},
            "properties": {"weight": -2, "caption": "Balloon", "type": "OTHER_LINK", "__type": 1, "source": 1337},
        },
        {"source_idx": 9, "target_idx": 10, "top_level": {"caption": "LINK"}, "properties": {"type": "LINK"}},
    ]

    assert len(VG.relationships) == len(expected_relationships_dicts)
    for i, exp_rel in enumerate(expected_relationships_dicts):
        created_rel = VG.relationships[i]
        assert created_rel.source == VG.nodes[exp_rel["source_idx"]].id
        assert created_rel.target == VG.nodes[exp_rel["target_idx"]].id
        assert (
            created_rel.model_dump(exclude_none=True, exclude={"properties", "id", "source", "target"})
            == exp_rel["top_level"]
        ), f"Failed at relationship {created_rel}"
        assert created_rel.properties == exp_rel["properties"], f"Failed at relationship {created_rel}"


def test_from_gql_create_captions() -> None:
    query = """
            CREATE
              (a:User {name: 'Alice', age: 23}),
              (b:User:person {name: "Bridget", age: 34, "caption": "Bridget"}),
              (a)-[:LINK {weight: 0.5}]->(b);
            """
    expected_node_dicts: list[dict[str, dict[str, Any]]] = [
        {
            "top_level": {"caption": "User", "color": "#ffdf81"},
            "properties": {"name": "Alice", "age": 23, "labels": ["User"]},
        },
        {
            "top_level": {"caption": "User:person", "color": "#c990c0"},
            "properties": {"name": "Bridget", "caption": "Bridget", "age": 34, "labels": ["User", "person"]},
        },
    ]

    VG = from_gql_create(query)

    assert len(VG.nodes) == len(expected_node_dicts)
    for i, exp_node in enumerate(expected_node_dicts):
        created_node = VG.nodes[i]

        assert created_node.model_dump(exclude_none=True, exclude={"properties", "id"}) == exp_node["top_level"]
        assert created_node.properties == exp_node["properties"]

    expected_relationships_dicts: list[dict[str, Any]] = [
        {
            "source_idx": 0,
            "target_idx": 1,
            "top_level": {"caption": "LINK"},
            "properties": {"weight": 0.5, "type": "LINK"},
        },
    ]

    assert len(VG.relationships) == len(expected_relationships_dicts)
    for i, exp_rel in enumerate(expected_relationships_dicts):
        created_rel = VG.relationships[i]
        assert created_rel.source == VG.nodes[exp_rel["source_idx"]].id
        assert created_rel.target == VG.nodes[exp_rel["target_idx"]].id
        assert (
            created_rel.model_dump(exclude_none=True, exclude={"properties", "id", "source", "target"})
            == exp_rel["top_level"]
        )
        assert created_rel.properties == exp_rel["properties"]


def test_unbalanced_parentheses_snippet() -> None:
    query = "CREATE (a:User, (b:User })"
    with pytest.raises(ValueError, match=r"Unbalanced parentheses near: `.*\(b:User.*"):
        from_gql_create(query)


def test_unbalanced_brackets_snippet() -> None:
    query = "CREATE (a)-[:LINK {weight: 0.5}->(b)"
    with pytest.raises(ValueError, match=r"Unbalanced square brackets near: `eight: 0.5}->\(b\)`."):
        from_gql_create(query)


def test_node_property_syntax_error_snippet1() -> None:
    query = "CREATE (a:User {x, y:4})"
    with pytest.raises(ValueError, match=r"Property syntax error near: `.*x, y.*"):
        from_gql_create(query)


def test_node_property_paren_imbalance() -> None:
    query = "CREATE (a:User {a: [1, b: 2, c: (3, 4)})"
    with pytest.raises(ValueError, match=r"Unbalanced square brackets near: `: 2, c: \(3, 4\)}"):
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

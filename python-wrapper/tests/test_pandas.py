import pytest
from pandas import DataFrame

from neo4j_viz.node import Node
from neo4j_viz.pandas import from_dfs


def test_from_df() -> None:
    nodes = DataFrame(
        {"id": [0, 1], "caption": ["A", "B"], "size": [1337, 42], "color": "#FF0000", "instrument": ["piano", "guitar"]}
    )
    relationships = DataFrame(
        {
            "source": [0, 1],
            "target": [1, 0],
            "caption": ["REL", "REL2"],
            "weight": [1.0, 2.0],
        }
    )
    VG = from_dfs(nodes, relationships)

    assert len(VG.nodes) == 2

    assert VG.nodes[0] == Node(
        id=0,
        caption=None,
        properties={"size": 1337, "color": "#FF0000", "instrument": "piano", "caption": "A"},
    )

    assert VG.nodes[1] == Node(
        id=1,
        caption=None,
        properties={"size": 42, "color": "#FF0000", "instrument": "guitar", "caption": "B"},
    )

    assert len(VG.relationships) == 2

    assert VG.relationships[0].source == 0
    assert VG.relationships[0].target == 1
    assert VG.relationships[0].caption is None
    assert VG.relationships[0].properties == {"weight": 1.0, "caption": "REL"}

    assert VG.relationships[1].source == 1
    assert VG.relationships[1].target == 0
    assert VG.relationships[1].caption is None
    assert VG.relationships[1].properties == {"weight": 2.0, "caption": "REL2"}


def test_from_rel_dfs() -> None:
    relationships = [
        DataFrame(
            {
                "source": [0, 1],
                "target": [1, 0],
                "caption": ["REL", "REL2"],
                "weight": [1.0, 2.0],
            }
        ),
        DataFrame(
            {
                "source": [2, 3],
                "target": [1, 0],
                "caption": ["REL", "REL2"],
                "weight": [1.0, 2.0],
            }
        ),
    ]
    VG = from_dfs(None, relationships)

    assert len(VG.relationships) == 4
    assert VG.nodes == [Node(id=id) for id in [0, 1, 2, 3]]


def test_from_dfs() -> None:
    nodes = [
        DataFrame(
            {
                "id": [0],
                "caption": ["A"],
                "size": [1337],
                "color": "#FF0000",
            }
        ),
        DataFrame(
            {
                "id": [1],
                "caption": ["B"],
                "size": [42],
                "color": "#FF0000",
            }
        ),
    ]

    relationships = [
        DataFrame(
            {
                "source": [0],
                "target": [1],
                "caption": ["REL"],
            }
        ),
        DataFrame(
            {
                "source": [1],
                "target": [0],
                "caption": ["REL2"],
            }
        ),
    ]
    VG = from_dfs(nodes, relationships)

    assert len(VG.nodes) == 2

    assert VG.nodes[0] == Node(id=0, caption=None, properties={"size": 1337, "color": "#FF0000", "caption": "A"})
    assert VG.nodes[1] == Node(id=1, caption=None, properties={"size": 42, "color": "#FF0000", "caption": "B"})

    assert len(VG.relationships) == 2

    assert VG.relationships[0].source == 0
    assert VG.relationships[0].target == 1
    assert VG.relationships[0].caption is None
    assert VG.relationships[0].properties == {"caption": "REL"}

    assert VG.relationships[1].source == 1
    assert VG.relationships[1].target == 0
    assert VG.relationships[1].caption is None
    assert VG.relationships[1].properties == {"caption": "REL2"}


def test_node_errors() -> None:
    nodes = DataFrame(
        {"caption": ["A", "B"], "size": [1337, 42], "color": "#FF0000", "instrument": ["piano", "guitar"]}
    )
    with pytest.raises(
        ValueError,
        match=r"Mandatory node column 'id' is missing. Expected one of \['id', 'ID', 'id', 'nodeid', 'NODEID', 'nodeid', 'node_id', 'NODE_ID', 'nodeId'\] to be present",
    ):
        from_dfs(nodes, [])

    nodes = DataFrame(
        {
            "id": [0, 1],
            "caption": ["A", "B"],
            "size": ["aaa", 42],
            "color": "#FF0000",
            "instrument": ["piano", "guitar"],
        }
    )


def test_rel_errors() -> None:
    nodes = DataFrame(
        {"id": [0, 1], "caption": ["A", "B"], "size": [1337, 42], "color": "#FF0000", "instrument": ["piano", "guitar"]}
    )
    relationships = DataFrame(
        {
            "target": [1, 0],
            "caption": ["REL", "REL2"],
            "weight": [1.0, 2.0],
        }
    )
    with pytest.raises(
        ValueError,
        match=r"Mandatory relationship column 'source' is missing. Expected one of \['source', 'SOURCE', 'source', 'sourcenodeid', 'SOURCENODEID', 'sourcenodeid', 'source_node_id', 'SOURCE_NODE_ID', 'sourceNodeId', 'from', 'FROM', 'from'\] to be present",
    ):
        from_dfs(nodes, relationships)


def test_from_dfs_no_rels() -> None:
    nodes = [
        DataFrame(
            {
                "id": [0],
                "caption": ["A"],
                "size": [1337],
                "color": "#FF0000",
            }
        ),
        DataFrame(
            {
                "id": [1],
                "caption": ["B"],
                "size": [42],
                "color": "#FF0000",
            }
        ),
    ]
    VG = from_dfs(nodes, [])

    assert len(VG.nodes) == 2
    assert VG.nodes[0] == Node(id=0, caption=None, properties={"size": 1337, "color": "#FF0000", "caption": "A"})
    assert VG.nodes[1] == Node(id=1, caption=None, properties={"size": 42, "color": "#FF0000", "caption": "B"})

    assert len(VG.relationships) == 0

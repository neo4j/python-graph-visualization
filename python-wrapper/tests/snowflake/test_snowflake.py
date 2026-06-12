from snowflake.snowpark import Session

from neo4j_viz.node import Node
from neo4j_viz.snowflake import from_snowflake


def test_from_snowflake(session_with_minimal_graph: Session) -> None:
    VG = from_snowflake(
        session_with_minimal_graph,
        {
            "nodeTables": ["NODES"],
            "relationshipTables": {
                "RELS": {
                    "sourceTable": "NODES",
                    "targetTable": "NODES",
                },
            },
        },
    )

    assert VG.nodes == [
        Node(id=0, caption="NODES", color="#ffdf81", properties={"SNOWFLAKEID": 6}),
        Node(id=1, caption="NODES", color="#ffdf81", properties={"SNOWFLAKEID": 7}),
    ]

    assert len(VG.relationships) == 1

    assert VG.relationships[0].source == 0
    assert VG.relationships[0].target == 1
    assert VG.relationships[0].caption == "RELS"
    assert VG.relationships[0].properties == {}

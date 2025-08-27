import pytest
from snowflake.snowpark import Session
from snowflake.snowpark.types import LongType, StructField, StructType

from neo4j_viz.snowflake import from_snowflake


@pytest.fixture
def session() -> Session:
    return Session.builder.configs({"local_testing": True}).create()  # type: ignore[no-any-return]


@pytest.fixture
def session_with_minimal_graph(session: Session) -> Session:
    """
    Create a minimal graph with two nodes and one relationship.
    """
    node_df = session.create_dataframe(
        data=[
            [6],
            [7],
        ],
        schema=StructType(
            [
                StructField("NODEID", LongType()),
            ]
        ),
    )
    node_df.write.save_as_table("NODES")

    rel_df = session.create_dataframe(
        data=[
            [6, 7],
        ],
        schema=StructType(
            [
                StructField("SOURCENODEID", LongType()),
                StructField("TARGETNODEID", LongType()),
            ]
        ),
    )
    rel_df.write.save_as_table("RELS")

    return session


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

    assert len(VG.nodes) == 2

    assert VG.nodes[0].id == 0
    assert VG.nodes[0].caption == "NODES"
    assert VG.nodes[0].color is not None
    assert VG.nodes[0].properties == {"SNOWFLAKEID": 6}

    assert VG.nodes[1].id == 1
    assert VG.nodes[1].caption == "NODES"
    assert VG.nodes[0].color is not None
    assert VG.nodes[1].properties == {"SNOWFLAKEID": 7}

    assert len(VG.relationships) == 1

    assert VG.relationships[0].source == 0
    assert VG.relationships[0].target == 1
    assert VG.relationships[0].caption == "RELS"

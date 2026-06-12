import pytest

pytest.importorskip("snowflake.snowpark")

from snowflake.snowpark import Session
from snowflake.snowpark.types import LongType, StructField, StructType


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

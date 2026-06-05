import os
import random
from typing import Any, Generator

import pytest


def pytest_addoption(parser: Any) -> None:
    parser.addoption(
        "--include-neo4j-and-gds",
        action="store_true",
        help="include tests requiring a Neo4j instance with GDS running",
    )
    parser.addoption(
        "--include-snowflake",
        action="store_true",
        help="include tests requiring a Snowflake connection",
    )


def pytest_collection_modifyitems(config: Any, items: Any) -> None:
    if not config.getoption("--include-neo4j-and-gds"):
        skip = pytest.mark.skip(reason="skipping since requiring Neo4j instance with GDS running")
        for item in items:
            if "requires_neo4j_and_gds" in item.keywords:
                item.add_marker(skip)
    if not config.getoption("--include-snowflake"):
        skip = pytest.mark.skip(reason="skipping since requiring a Snowflake connection")
        for item in items:
            if "requires_snowflake" in item.keywords:
                item.add_marker(skip)


@pytest.fixture(scope="package")
def aura_db_instance() -> Generator[Any, None, None]:
    if os.environ.get("NEO4J_URI", ""):
        print(f"Skipping Aura DB setup since NEO4J_URI is set to {os.environ['NEO4J_URI']}")
        yield None
        return

    if os.environ.get("AURA_API_CLIENT_ID", None) is None:
        yield None
        return

    from tests.gds_helper import aura_api, create_auradb_instance

    api = aura_api()
    dbms_connection_info = create_auradb_instance(api)

    # setting as environment variables to run notebooks with this connection
    os.environ["NEO4J_URI"] = dbms_connection_info.get_uri()
    assert isinstance(dbms_connection_info.username, str)
    os.environ["NEO4J_USERNAME"] = dbms_connection_info.username
    assert isinstance(dbms_connection_info.password, str)
    os.environ["NEO4J_PASSWORD"] = dbms_connection_info.password
    old_instance = os.environ.get("AURA_INSTANCEID", "")
    if dbms_connection_info.aura_instance_id:
        os.environ["AURA_INSTANCEID"] = dbms_connection_info.aura_instance_id

    yield dbms_connection_info

    # Clear Neo4j_URI after test (rerun should create a new instance)
    os.environ["AURA_INSTANCEID"] = old_instance
    assert dbms_connection_info.aura_instance_id is not None
    api.delete_instance(dbms_connection_info.aura_instance_id)


@pytest.fixture(scope="package")
def gds(aura_db_instance: Any) -> Generator[Any, None, None]:
    from graphdatascience.session import SessionMemory

    from tests.gds_helper import connect_to_local_gds_session, connect_to_plugin_gds, gds_sessions

    if aura_db_instance:
        sessions = gds_sessions()

        gds = sessions.get_or_create(
            f"neo4j-viz-ci-{os.environ.get('GITHUB_RUN_ID', random.randint(0, 10**6))}",
            memory=SessionMemory.m_2GB,
            db_connection=aura_db_instance,
        )

        yield gds
        gds.delete()
    else:
        neo4j_uri = os.environ["NEO4J_URI"]
        neo4j_auth = (os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password"))

        session_uri = os.environ.get("GDS_SESSION_URI")
        if session_uri:
            gds = connect_to_local_gds_session(session_uri, neo4j_uri, neo4j_auth)
        else:
            gds = connect_to_plugin_gds(neo4j_uri, neo4j_auth)  # type: ignore
        yield gds
        gds.close()


@pytest.fixture(scope="package")
def neo4j_driver(aura_db_instance: Any) -> Generator[Any, None, None]:
    import neo4j

    if aura_db_instance:
        driver = neo4j.GraphDatabase.driver(
            aura_db_instance.uri, auth=(aura_db_instance.username, aura_db_instance.password)
        )
    else:
        NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
        driver = neo4j.GraphDatabase.driver(NEO4J_URI)

    try:
        driver.verify_connectivity()
        yield driver
    finally:
        driver.close()


@pytest.fixture(scope="package")
def neo4j_session(neo4j_driver: Any) -> Generator[Any, None, None]:
    with neo4j_driver.session() as session:
        yield session

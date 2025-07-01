import os
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
def aura_ds_instance() -> Generator[Any, None, None]:
    if os.environ.get("AURA_API_CLIENT_ID", None) is None:
        yield None
        return

    from gds_helper import aura_api, create_aurads_instance

    api = aura_api()
    id, dbms_connection_info = create_aurads_instance(api)

    # setting as environment variables to run notebooks with this connection
    os.environ["NEO4J_URI"] = dbms_connection_info.uri
    assert isinstance(dbms_connection_info.username, str)
    os.environ["NEO4J_USER"] = dbms_connection_info.username
    assert isinstance(dbms_connection_info.password, str)
    os.environ["NEO4J_PASSWORD"] = dbms_connection_info.password
    yield dbms_connection_info

    # Clear Neo4j_URI after test (rerun should create a new instance)
    os.environ["NEO4J_URI"] = ""
    api.delete_instance(id)


@pytest.fixture(scope="package")
def gds(aura_ds_instance: Any) -> Generator[Any, None, None]:
    from gds_helper import connect_to_plugin_gds
    from graphdatascience import GraphDataScience

    if aura_ds_instance:
        yield GraphDataScience(
            endpoint=aura_ds_instance.uri,
            auth=(aura_ds_instance.username, aura_ds_instance.password),
            aura_ds=True,
            database="neo4j",
        )
    else:
        NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
        gds = connect_to_plugin_gds(NEO4J_URI)
        yield gds
        gds.close()


@pytest.fixture(scope="package")
def neo4j_driver(aura_ds_instance: Any) -> Generator[Any, None, None]:
    import neo4j

    if aura_ds_instance:
        driver = neo4j.GraphDatabase.driver(
            aura_ds_instance.uri, auth=(aura_ds_instance.username, aura_ds_instance.password)
        )
    else:
        NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
        driver = neo4j.GraphDatabase.driver(NEO4J_URI)

    driver.verify_connectivity()
    yield driver

    driver.close()


@pytest.fixture(scope="package")
def neo4j_session(neo4j_driver: Any) -> Generator[Any, None, None]:
    with neo4j_driver.session() as session:
        yield session

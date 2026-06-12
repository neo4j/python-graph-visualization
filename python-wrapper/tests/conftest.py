import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
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


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
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

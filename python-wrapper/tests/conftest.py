import pathlib

import pytest

# Built by `just js-build`; not committed (see .gitignore). The widget reads
# them when it is imported, so tests cannot run without them.
_BUILT_ASSETS = (
    "resources/nvl_entrypoint/widget.js",
    "resources/nvl_entrypoint/style.css",
    "resources/nvl_entrypoint/index.html",
    "resources/streamlit_v2/graph.js",
)


def pytest_configure(config: pytest.Config) -> None:
    package_dir = pathlib.Path(__file__).parent.parent / "src" / "neo4j_viz"
    missing = [asset for asset in _BUILT_ASSETS if not (package_dir / asset).exists()]
    if missing:
        pytest.exit(
            "Missing built widget assets:\n  " + "\n  ".join(missing) + "\nRun `just js-build` to build them.",
            returncode=2,
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--include-neo4j-and-gds",
        action="store_true",
        help="include tests requiring a Neo4j instance with GDS running",
    )
    parser.addoption(
        "--only-neo4j-and-gds",
        action="store_true",
        help="run only tests requiring a Neo4j instance with GDS running",
    )
    parser.addoption(
        "--include-snowflake",
        action="store_true",
        help="include tests requiring a Snowflake connection",
    )
    parser.addoption(
        "--only-snowflake",
        action="store_true",
        help="run only tests requiring a Snowflake connection",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    only_neo4j_and_gds = config.getoption("--only-neo4j-and-gds")
    only_snowflake = config.getoption("--only-snowflake")
    # `--only-X` implies `--include-X` for that integration.
    include_neo4j_and_gds = config.getoption("--include-neo4j-and-gds") or only_neo4j_and_gds
    include_snowflake = config.getoption("--include-snowflake") or only_snowflake
    only_integration = only_neo4j_and_gds or only_snowflake

    skip_neo4j_and_gds = pytest.mark.skip(reason="skipping since requiring Neo4j instance with GDS running")
    skip_snowflake = pytest.mark.skip(reason="skipping since requiring a Snowflake connection")
    skip_non_integration = pytest.mark.skip(reason="skipping since only integration tests were requested")

    for item in items:
        requires_neo4j_and_gds = "requires_neo4j_and_gds" in item.keywords
        requires_snowflake = "requires_snowflake" in item.keywords

        if requires_neo4j_and_gds and not include_neo4j_and_gds:
            item.add_marker(skip_neo4j_and_gds)
        elif requires_snowflake and not include_snowflake:
            item.add_marker(skip_snowflake)
        elif only_integration and not (requires_neo4j_and_gds or requires_snowflake):
            item.add_marker(skip_non_integration)

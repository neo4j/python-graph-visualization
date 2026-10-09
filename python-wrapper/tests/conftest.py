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

import os

import pytest
from dotenv import load_dotenv
from graphdatascience import GraphDataScience
from graphdatascience.session import AuraGraphDataScience
from graphdatascience.version import __version__

# The GDS client >= 2.0 moved `SemanticVersion` under `versions`
if int(__version__.split(".")[0]) >= 2:
    from graphdatascience.versions.semantic_version import SemanticVersion
else:
    from graphdatascience.semantic_version.semantic_version import (  # type: ignore[import-not-found,no-redef]
        SemanticVersion,
    )

from tests.neo4j_and_gds.gds_helper import GDS_VERSION, run_id
from tests.notebook_runner import run_notebooks

# Must match the literal in examples/gds-example.ipynb
DEFAULT_SESSION_NAME = "neo4j-viz-gds-example"


@pytest.mark.requires_neo4j_and_gds
@pytest.mark.skipif(
    GDS_VERSION >= SemanticVersion(2, 0, 0),
    reason="Notebooks are only supported on GDS < 2",
)
def test_neo4j(gds: GraphDataScience | AuraGraphDataScience) -> None:
    # The `gds` fixture provisions the Aura DB / GDS session and sets the NEO4J_* env vars
    # that the notebooks read to connect.
    load_dotenv(os.environ.get("ENV_FILE"))

    # Unique per-run session name (replaced into the notebook source) so the notebook does
    # not collide with sessions leaked by earlier runs.
    session_name = f"{DEFAULT_SESSION_NAME}-ci-{run_id()}-{__version__}"

    run_notebooks(
        ["neo4j-example.ipynb", "gds-example.ipynb"],
        replacements={DEFAULT_SESSION_NAME: session_name},
    )

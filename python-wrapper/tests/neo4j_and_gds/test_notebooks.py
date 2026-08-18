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

from tests.neo4j_and_gds.gds_helper import GDS_VERSION
from tests.notebook_runner import run_notebooks


@pytest.mark.requires_neo4j_and_gds
@pytest.mark.skipif(
    GDS_VERSION >= SemanticVersion(2, 0, 0),
    reason="Notebooks are only supported on GDS < 2",
)
def test_neo4j(gds: GraphDataScience | AuraGraphDataScience) -> None:
    # The `gds` fixture provisions the Aura DB / GDS session and sets the NEO4J_* env vars
    # that the notebooks read to connect.
    load_dotenv(os.environ.get("ENV_FILE"))

    run_notebooks(["neo4j-example.ipynb", "gds-example.ipynb"])

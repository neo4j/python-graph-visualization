root_dir := justfile_directory()
py_dir := root_dir / 'python-wrapper'

py-sync:
    cd python-wrapper && uv sync --group dev --group docs --group notebook --extra pandas --extra neo4j --extra gds --extra snowflake

# check the release version is unpublished and main's CI is green
# example: just prerelease
prerelease:
    python scripts/release/prerelease.py

# bump the version and reset the changelog after a release (default: minor bump)
# examples:
#   just postrelease          # 1.5.0 -> 1.6.0
#   just postrelease patch    # 1.5.0 -> 1.5.1
#   just postrelease major    # 1.5.0 -> 2.0.0
postrelease part="minor":
    python scripts/release/postrelease.py --part {{part}}

py-style:
    just py-sync
    ./scripts/makestyle.sh && ./scripts/checkstyle.sh

py-test:
    cd python-wrapper && uv sync --all-extras --group dev
    cd python-wrapper && uv run --group dev pytest

# install a specific GDS client version and run the GDS integration tests (used by CI)
# example: just py-ci-test-gds 2.0.0a1
py-ci-test-gds gds_version:
    #!/usr/bin/env bash
    set -e
    cd {{py_dir}}
    uv sync --group dev --extra pandas --extra neo4j --extra gds
    uv pip install "graphdatascience=={{gds_version}}"
    uv run pytest tests/ --include-neo4j-and-gds

py-test-gds:
    #!/usr/bin/env bash
    set -e
    ENV_DIR="test-envs/neo4j-gds"
    trap "cd $ENV_DIR && docker compose down" EXIT
    cd $ENV_DIR && docker compose up -d
    cd -
    cd python-wrapper && \
    NEO4J_URI=bolt://localhost:7687 \
    NEO4J_USERNAME=neo4j \
    NEO4J_PASSWORD=password \
    NEO4J_DB=neo4j \
    uv run --group dev --extra gds pytest tests --include-neo4j-and-gds
    cd ..


# this expects the local compose setup to be running.
py-test-gds-sessions filter="":
    #!/usr/bin/env bash
    cd python-wrapper && \
    GDS_SESSION_URI=bolt://localhost:7688 \
    NEO4J_URI=bolt://localhost:7687 \
    NEO4J_USERNAME=neo4j \
    NEO4J_PASSWORD=password \
    uv run --group dev --extra gds pytest tests --include-neo4j-and-gds {{ if filter != "" { "-k '" + filter + "'" } else { "" } }}

local-neo4j-setup:
    #!/usr/bin/env bash
    set -e
    ENV_DIR="test-envs/neo4j-gds"
    cd $ENV_DIR && docker compose up -d

local-neo4j-teardown:
    #!/usr/bin/env bash
    set -e
    ENV_DIR="test-envs/neo4j-gds"
    cd $ENV_DIR && docker compose down

js-dev:
    cd js-applet && yarn && yarn dev

js-test:
    cd js-applet && yarn && yarn test

js-rebuild:
    ./scripts/clean_js_applet.sh && ./scripts/build_js_applet.sh

js-build:
    ./scripts/build_js_applet.sh

js-style:
    cd js-applet && yarn && yarn lint:fix && yarn format
    cd js-applet && yarn && yarn lint && yarn format:check

streamlit:
    ./scripts/run_streamlit_example.sh

marimo:
    #!/usr/bin/env bash
    set -e
    cd {{py_dir}} && uv run --group notebook marimo run {{root_dir}}/examples/marimo-example.py

marimo-edit:
    #!/usr/bin/env bash
    set -e
    cd {{py_dir}} && uv run --group notebook marimo edit {{root_dir}}/examples/marimo-example.py

ref-docs:
    ./scripts/render_antora_docs.sh

api-docs:
    ./scripts/render_host_api_docs.sh

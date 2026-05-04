root_dir := justfile_directory()
py_dir := root_dir / 'python-wrapper'

py-sync:
    cd python-wrapper && uv sync --group dev --group docs --group notebook --extra pandas --extra neo4j --extra gds --extra snowflake

py-style:
    just py-sync
    ./scripts/makestyle.sh && ./scripts/checkstyle.sh

py-test:
    cd python-wrapper && uv run --group dev pytest

py-test-gds:
    #!/usr/bin/env bash
    set -e
    ENV_DIR="test-envs/neo4j-gds"
    trap "cd $ENV_DIR && docker compose down" EXIT
    cd $ENV_DIR && docker compose up -d
    cd -
    NEO4J_URI=bolt://localhost:7687 \
    NEO4J_USER=neo4j \
    NEO4J_PASSWORD=password \
    NEO4J_DB=neo4j \
    cd python-wrapper && uv run --group dev --extra gds pytest tests --include-neo4j-and-gds
    cd ..

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

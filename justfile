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

style: py-style js-style

py-style:
    just py-sync
    ./scripts/makestyle.sh && ./scripts/checkstyle.sh

# Run Python style checks (ruff + mypy) against a pinned `graphdatascience` version, so
# the v1/v2 compat surface in _gds_compat is type-checked under that version. mypy is
# scoped to `src` because the test helpers import v2-only modules (covered by the default
# v2 gate); ruff runs on the whole tree as usual.
# example: just py-style-gds 1.22
py-style-gds version="2.0":
    #!/usr/bin/env bash
    set -e
    just py-sync
    uv pip install --python python-wrapper/.venv/bin/python "graphdatascience=={{version}}"
    # UV_NO_SYNC stops `uv run` inside the style scripts from re-syncing (which would
    # revert the pin back to the latest GDS).
    UV_NO_SYNC=1 ./scripts/makestyle.sh
    UV_NO_SYNC=1 MYPY_TARGETS=python-wrapper/src ./scripts/checkstyle.sh

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

# Render the full documentation locally: the Sphinx API reference and the
# Antora manual, with the manual's links pointing at the locally served API
# docs. Manual -> http://localhost:8000 ; API reference -> http://localhost:9000
# Press Ctrl-C to stop both servers.
render-docs:
    #!/usr/bin/env bash
    set -e
    cd {{py_dir}} && uv sync --group dev --group docs --extra pandas --extra neo4j --extra gds --extra snowflake
    # Build the Sphinx API reference (the same build CI runs).
    uv run --project {{py_dir}} bash {{root_dir}}/scripts/render_api_docs.sh
    # Build the Antora manual for preview (bypassing the `postbuild` server hook).
    cd {{root_dir}}/docs/antora
    npm install
    npx antora preview.yml --stacktrace --log-format=pretty

    cleanup() {
        trap - INT TERM EXIT
        kill "${api_pid:-}" "${manual_pid:-}" 2>/dev/null || true
    }
    trap cleanup INT TERM EXIT

    (exec node server.js) &
    manual_pid=$!
    (cd {{root_dir}}/docs/build && exec python3 -m http.server 9000) &
    api_pid=$!

    echo ""
    echo "Manual:        http://localhost:8000"
    echo "API reference: http://localhost:9000"
    echo "Press Ctrl-C to stop both."
    wait

# Regenerate the documentation images (README + getting-started guide) from the
# example graphs via GraphWidget.save() in a headless browser. All images are
# built locally without a database. Optionally restrict to named images:
# `just docs-images getting-started-graph`
docs-images *names:
    #!/usr/bin/env bash
    set -e
    cd {{py_dir}} && uv sync --group dev --group notebook
    cd {{py_dir}} && uv run --group dev --group notebook python {{root_dir}}/scripts/regenerate_docs_images.py {{names}}

#!/usr/bin/env bash
# Render the full documentation locally: the Sphinx API reference and the
# Antora manual, with the manual's links pointing at the locally served API
# docs. Manual -> http://localhost:8000 ; API reference -> http://localhost:9000
# Press Ctrl-C to stop both servers.

GIT_ROOT=$(git rev-parse --show-toplevel)
PY_PROJECT="${GIT_ROOT}/python-wrapper"

set -o errexit
set -o nounset
set -o pipefail

(
    cd "${PY_PROJECT}"
    uv sync --group dev --group docs --extra pandas --extra neo4j --extra gds --extra snowflake
)

# Build the Sphinx API reference (the same build CI runs).
uv run --project "${PY_PROJECT}" bash "${GIT_ROOT}/scripts/render_api_docs.sh"

# Build the Antora manual for preview (bypassing the `postbuild` server hook).
(
    cd "${GIT_ROOT}/docs/antora"
    npm install
    npx antora preview.yml --stacktrace --log-format=pretty
)

cleanup() {
    trap - INT TERM EXIT
    kill "${api_pid:-}" "${manual_pid:-}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

(cd "${GIT_ROOT}/docs/build" && exec python3 -m http.server 9000) &
api_pid=$!
(cd "${GIT_ROOT}/docs/antora" && exec node server.js) &
manual_pid=$!

echo ""
echo "Manual:        http://localhost:8000"
echo "API reference: http://localhost:9000"
echo "Press Ctrl-C to stop both."

# Exit (and stop the other server) as soon as either server dies, instead of
# silently serving only one of the two docs. A server whose port is already
# taken by a leftover process exits immediately, which this loop catches.
while true; do
    kill -0 "${api_pid}" 2>/dev/null || {
        echo "ERROR: the API reference server exited; is port 9000 already in use (lsof -i :9000)?" >&2
        exit 1
    }
    kill -0 "${manual_pid}" 2>/dev/null || {
        echo "ERROR: the manual server exited; is port 8000 already in use (lsof -i :8000)?" >&2
        exit 1
    }
    sleep 1
done

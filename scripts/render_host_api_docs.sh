#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail
set -o xtrace


GIT_ROOT=$(git rev-parse --show-toplevel)
PY_PROJECT="${GIT_ROOT}/python-wrapper"

# Build through the project environment so the docs toolchain does not depend on
# whatever sphinx-build happens to be on PATH. Python 3.13 matches CI and is the
# floor for Sphinx 9.1+ (see the docs group in python-wrapper/pyproject.toml).
uv sync --project "${PY_PROJECT}" --python 3.13 --group dev --group docs --extra pandas --extra neo4j --extra gds --extra snowflake
uv run --project "${PY_PROJECT}" --python 3.13 bash "${GIT_ROOT}/scripts/render_api_docs.sh"

echo http://localhost:9000
python3 -m http.server 9000 -d "${GIT_ROOT}/docs/build"

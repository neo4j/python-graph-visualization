#!/usr/bin/env bash
GIT_ROOT=$(git rev-parse --show-toplevel)

set -o errexit
set -o nounset
set -o pipefail
set -o xtrace

python -m ruff format .
python -m ruff check . --fix

if [ "${SKIP_NOTEBOOKS:-false}" == "true" ]; then
  echo "Skipping notebooks"
  exit 0
fi

python "${GIT_ROOT}/scripts/clean_notebooks.py" -i "${GIT_ROOT}/examples/" -o inplace

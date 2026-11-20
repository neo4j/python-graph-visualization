#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail
set -o xtrace


GIT_ROOT=$(git rev-parse --show-toplevel)

# Run pandoc from the pinned container image rather than requiring a local
# install; the wrapper patches nbsphinx/nbconvert and forwards to sphinx-build.
SPHINXBUILD="python ${GIT_ROOT}/scripts/sphinx_container_pandoc.py"

(
    cd "${GIT_ROOT}/docs"
    make clean html SPHINXBUILD="${SPHINXBUILD}"
)

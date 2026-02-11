#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail
set -o xtrace


GIT_ROOT=$(git rev-parse --show-toplevel)

(
    cd "${GIT_ROOT}/docs"
    make clean html
)

echo http://localhost:9000
python3 -m http.server 9000 -d "${GIT_ROOT}/docs/build"

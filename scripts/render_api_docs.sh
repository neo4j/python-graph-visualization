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

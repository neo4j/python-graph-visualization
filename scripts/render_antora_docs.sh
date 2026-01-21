#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
set -o xtrace

cd docs/antora
npm install
npm run start
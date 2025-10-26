#!/usr/bin/env bash
GIT_ROOT=$(git rev-parse --show-toplevel)

set -o errexit
set -o nounset
set -o pipefail

python -m ruff check .
python -m ruff format --check .
python -m mypy --config-file "${GIT_ROOT}/python-wrapper/pyproject.toml" .


if [ "${SKIP_NOTEBOOKS:-false}" == "true" ]; then
  echo "Skipping notebooks"
  exit 0
fi

echo "Checking notebooks"

NOTEBOOKS="${GIT_ROOT}/examples/*.ipynb" # ./examples/dev/*.ipynb"
for f in $NOTEBOOKS
do
  NB=$(cat $f)
  FORMATTED_NB=$(python "${GIT_ROOT}/scripts/clean_notebooks.py" -i "$f" -o stdout)

  if [[ "$FORMATTED_NB" != "$NB" ]];
  then
    echo "Notebook $f is not correctly formatted. See diff above for more details."
    diff --color=always --suppress-common-lines --minimal --side-by-side <(echo "$NB") <(echo "$FORMATTED_NB")
    exit 1
  fi
done

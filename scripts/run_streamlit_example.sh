GIT_ROOT=$(git rev-parse --show-toplevel)
PY_PROJECT="${GIT_ROOT}/python-wrapper"

set -o errexit
set -o nounset
set -o pipefail

uv run --project "${PY_PROJECT}" streamlit run ${GIT_ROOT}/examples/streamlit-example.py

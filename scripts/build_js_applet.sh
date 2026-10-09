GIT_ROOT=$(git rev-parse --show-toplevel)

set -o errexit
set -o nounset
set -o pipefail

(
    cd "${GIT_ROOT}/js-applet"
    yarn
    yarn build
)

# The Streamlit build emits a style.css identical to the widget's
# (nvl_entrypoint/style.css); the Python side reads that copy instead, so drop
# the duplicate the build produces.
rm -f "${GIT_ROOT}/python-wrapper/src/neo4j_viz/resources/streamlit_v2/style.css"

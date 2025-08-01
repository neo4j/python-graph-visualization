GIT_ROOT=$(git rev-parse --show-toplevel)

set -o errexit
set -o nounset
set -o pipefail

(
    cd "${GIT_ROOT}/js-applet"
    rm -rf node_modules
    rm -f yarn.lock
)

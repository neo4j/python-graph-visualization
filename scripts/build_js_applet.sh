GIT_ROOT=$(git rev-parse --show-toplevel)

set -o errexit
set -o nounset
set -o pipefail

(
    cd "${GIT_ROOT}/js-applet"
    yarn
    yarn build
)

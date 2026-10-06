#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/_common.sh"
echo "${IMAGE_TAG:?}" > "$STATE_DIR/last_good_tag"; echo "Recorded $IMAGE_TAG as last good release"

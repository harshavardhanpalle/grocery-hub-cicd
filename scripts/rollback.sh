#!/usr/bin/env bash
# Redeploys the last known-good image tag. Named volumes are untouched, so data is preserved.
set -euo pipefail
. "$(dirname "$0")/_common.sh"
[ -s "$STATE_DIR/last_good_tag" ] || { echo "No previous good release recorded - nothing to roll back to."; exit 1; }
export IMAGE_TAG=$(cat "$STATE_DIR/last_good_tag")
export SIMULATE_UNHEALTHY=false        # never carry the demo failure flag into the rollback
echo "ROLLING BACK to tag $IMAGE_TAG"
docker compose up -d --no-build --remove-orphans
bash "$(dirname "$0")/healthcheck.sh"

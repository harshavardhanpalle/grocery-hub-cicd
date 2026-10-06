#!/usr/bin/env bash
# Keeps the newest KEEP image tags per service (and the last good one); removes the rest.
set -uo pipefail
. "$(dirname "$0")/_common.sh"
KEEP="${KEEP:-3}"
good=$(cat "$STATE_DIR/last_good_tag" 2>/dev/null || echo none)
for s in $SERVICES; do
  docker images "grocery-hub/$s" --format '{{.Tag}}' | grep -E '^[0-9]+$' | sort -rn | tail -n +$((KEEP+1)) | while read -r t; do
    [ "$t" = "$good" ] && continue
    echo "Removing grocery-hub/$s:$t"; docker rmi "grocery-hub/$s:$t" || true
  done
done
docker image prune -f

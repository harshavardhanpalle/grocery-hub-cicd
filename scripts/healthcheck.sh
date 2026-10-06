#!/usr/bin/env bash
# Waits until all containers report healthy, then calls the API through the gateway.
set -uo pipefail
. "$(dirname "$0")/_common.sh"
for i in $(seq 1 30); do
  ok=1
  for s in $SERVICES; do
    cid=$(docker compose ps -q "$s"); st=$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo missing)
    [ "$st" = healthy ] || ok=0
  done
  if [ $ok = 1 ] && docker compose exec -T gateway wget -qO- http://127.0.0.1:8080/api/products >/dev/null; then
    echo "HEALTHY after $((i*3))s"; exit 0
  fi
  echo "waiting for services... ($i/30)"; sleep 3
done
docker compose ps; docker compose logs --tail=40
echo "UNHEALTHY"; exit 1

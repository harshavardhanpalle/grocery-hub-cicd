#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/_common.sh"
: "${IMAGE_TAG:?IMAGE_TAG required}"
[ -f .env ] || cp .env.example .env
export IMAGE_TAG
echo "Deploying tag $IMAGE_TAG"
docker compose up -d --no-build --remove-orphans

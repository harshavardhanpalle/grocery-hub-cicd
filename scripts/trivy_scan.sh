#!/usr/bin/env bash
# Trivy evidence + gate.
#  - reports/trivy/<svc>-full.txt : ALL severities (evidence for submission)
#  - reports/trivy/<svc>.json     : machine-readable HIGH/CRITICAL
#  - reports/trivy/<svc>.txt      : HIGH/CRITICAL table; this is what gates the deploy
#  - reports/trivy/config.txt     : Dockerfile / compose misconfiguration scan
#  - reports/trivy/SUMMARY.txt    : one line per image (PASS / FAIL)
set -uo pipefail
. "$(dirname "$0")/_common.sh"
: "${IMAGE_TAG:?IMAGE_TAG required}"
# Pinned on purpose: 0.69.3 is the last known-clean release before the March 2026 Trivy
# supply-chain incident (0.69.4-0.69.6 and ":latest" were compromised). Never use :latest.
TRIVY="${TRIVY_IMAGE:-aquasec/trivy:0.69.3}"
SEV="${TRIVY_SEVERITY:-HIGH,CRITICAL}"
EXIT="${TRIVY_EXIT_CODE:-1}"          # 0 = report-only mode
mkdir -p reports/trivy; rc=0; : > reports/trivy/SUMMARY.txt
# TRIVY_DB_REPOSITORY (optional) lets you use a mirror if GHCR rate-limits you
tv() { docker run --rm -e TRIVY_DB_REPOSITORY -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ "$TRIVY" "$@"; }

for s in $SERVICES; do
  img="grocery-hub/$s:$IMAGE_TAG"
  echo "== Trivy: $img"
  tv image --format table "$img" > "reports/trivy/$s-full.txt" 2>&1 || true
  tv image --quiet --ignore-unfixed --severity "$SEV" --format json "$img" > "reports/trivy/$s.json" 2>/dev/null || true
  tv image --ignore-unfixed --severity "$SEV" --format table --exit-code "$EXIT" "$img" 2>&1 | tee "reports/trivy/$s.txt"
  if [ "${PIPESTATUS[0]}" -eq 0 ]; then echo "PASS  $img (no fixable $SEV)" >> reports/trivy/SUMMARY.txt
  else echo "FAIL  $img (fixable $SEV found)" >> reports/trivy/SUMMARY.txt; rc=1; fi
done

echo "== Trivy: Dockerfile/compose misconfiguration scan (report only)"
# When Jenkins itself runs in a container, the workspace lives in Jenkins' volume, not on the host,
# so share that volume with the scanner instead of bind-mounting a path the host does not have.
if docker inspect "$(hostname)" >/dev/null 2>&1; then
  docker run --rm --volumes-from "$(hostname)" -w "$PWD" -v trivy-cache:/root/.cache/ "$TRIVY" config --severity HIGH,CRITICAL . > reports/trivy/config.txt 2>&1 || true
else
  docker run --rm -v "$PWD":/src -v trivy-cache:/root/.cache/ "$TRIVY" config --severity HIGH,CRITICAL /src > reports/trivy/config.txt 2>&1 || true
fi
cat reports/trivy/SUMMARY.txt
exit $rc

#!/usr/bin/env bash
# Smoke test for the running Docker Compose stack (`docker compose up --build --wait`).
#
# Drives a whole crawl through the dashboard's API without touching the internet: the
# crawler API container crawls the dashboard container's own site over the stack's
# internal network. Needs only bash, curl, python3 (or python) and docker.
#
#   scripts/docker-smoke.sh [dashboard-url]      default: http://localhost:3000
set -euo pipefail

DASHBOARD="${1:-http://localhost:${DASHBOARD_PORT:-3000}}"
TARGET="http://dashboard:3000/" # as the crawler API container sees the dashboard
TIMEOUT_S=60
PYTHON="$(command -v python3 || command -v python)"

cd "$(dirname "$0")/.."

fail() {
  echo "FAIL: $*" >&2
  exit 1
}
json() { "$PYTHON" -c "import json, sys; d = json.load(sys.stdin); print($1)"; }

echo "1. The dashboard's API reaches the crawler API"
body="$(curl -sS --fail-with-body "$DASHBOARD/api/crawls")" \
  || fail "GET $DASHBOARD/api/crawls failed (is the stack running?): ${body:-no response}"
echo "   GET /api/crawls -> $body"

echo "2. Start a crawl of $TARGET"
created="$(curl -sS --fail-with-body -X POST "$DASHBOARD/api/crawls" \
  -H 'content-type: application/json' \
  -d "{\"url\": \"$TARGET\", \"max_pages\": 5}")" || fail "starting a crawl failed: $created"
id="$(echo "$created" | json 'd["id"]')"
echo "   crawl $id started"

echo "3. Wait for it to finish (up to ${TIMEOUT_S}s)"
deadline=$((SECONDS + TIMEOUT_S))
while :; do
  status="$(curl -sS --fail-with-body "$DASHBOARD/api/crawls/$id/status")" || fail "status: $status"
  state="$(echo "$status" | json 'd["status"]')"
  [ "$state" != "running" ] && break
  [ "$SECONDS" -ge "$deadline" ] && fail "crawl still running after ${TIMEOUT_S}s: $status"
  sleep 1
done
pages="$(echo "$status" | json 'd["stats"]["pages"]')"
[ "$state" = "completed" ] || fail "crawl ended as $state: $status"
[ "$pages" -ge 1 ] || fail "crawl completed with no pages: $status"
echo "   $state with $pages page(s)"

echo "4. Services run unprivileged"
for service in backend dashboard; do
  uid="$(docker compose exec -T "$service" id -u | tr -d '\r')"
  [ "$uid" != "0" ] || fail "$service runs as root"
  echo "   $service uid=$uid"
done

echo "OK: the stack works end to end"

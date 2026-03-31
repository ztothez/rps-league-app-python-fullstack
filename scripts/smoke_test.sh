#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:4000}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

check_status() {
  local path="$1"
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}${path}")"
  if [[ "$code" != "200" ]]; then
    echo "FAIL ${path} -> HTTP ${code}" >&2
    exit 1
  fi
  echo "OK   ${path} -> HTTP ${code}"
}

check_json_key() {
  local path="$1"
  local key="$2"
  local body
  body="$(curl -sS "${BASE_URL}${path}")"
  python3 - "$body" "$path" "$key" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
path = sys.argv[2]
key = sys.argv[3]

if key not in payload:
    print(f"FAIL {path} missing key '{key}'", file=sys.stderr)
    raise SystemExit(1)

print(f"OK   {path} has key '{key}'")
PY
}

require_cmd curl
require_cmd python3

echo "Running smoke tests against ${BASE_URL}"
check_status "/"
check_status "/docs"
check_status "/openapi.json"

check_json_key "/api/matches/history?take=3" "data"
check_json_key "/api/leaderboard/today" "data"
check_json_key "/api/leaderboard/history" "data"

echo "Smoke tests passed."

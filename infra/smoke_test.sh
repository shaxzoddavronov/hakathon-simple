#!/usr/bin/env bash
# Curl-based smoke test for a running QueryMind backend.
#
# Verifies the live API path: health -> register -> login -> create
# workspace -> wait for profiling -> chat (SSE). Does NOT need the
# frontend. Requires the backend on $API and (for a non-trivial chat
# answer) a reachable vLLM + a real data DB to point the workspace at.
#
# Usage:
#   API=http://localhost:8080 \
#   DATA_HOST=localhost DATA_PORT=5432 DATA_DB=sales_demo \
#   DATA_USER=querymind DATA_PASS=querymind \
#   ./infra/smoke_test.sh
set -euo pipefail

API="${API:-http://localhost:8080}"
EMAIL="${EMAIL:-smoke+$(date +%s)@test.local}"
PASSWORD="${PASSWORD:-supersecret123}"
DATA_HOST="${DATA_HOST:-localhost}"
DATA_PORT="${DATA_PORT:-5432}"
DATA_DB="${DATA_DB:-sales_demo}"
DATA_USER="${DATA_USER:-querymind}"
DATA_PASS="${DATA_PASS:-querymind}"

say() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }
fail() { printf '\033[1;31mFAIL: %s\033[0m\n' "$1" >&2; exit 1; }

say "1. Health"
curl -fsS "$API/healthz" | grep -q '"status":"ok"' || fail "healthz not ok"
echo "ok"

say "2. Register"
curl -fsS -X POST "$API/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" >/dev/null \
  || fail "register failed (email may already exist)"
echo "registered $EMAIL"

say "3. Login"
TOKEN=$(curl -fsS -X POST "$API/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$EMAIL" \
  --data-urlencode "password=$PASSWORD" \
  | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
[ -n "$TOKEN" ] || fail "no access_token returned"
echo "got token"

say "4. Create workspace -> $DATA_DB"
WS=$(curl -fsS -X POST "$API/workspaces" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
        \"name\": \"smoke_$(date +%s)\",
        \"dialect\": \"postgres\",
        \"connection_meta\": {\"host\":\"$DATA_HOST\",\"port\":$DATA_PORT,\"db_name\":\"$DATA_DB\",\"ssl\":false},
        \"auth_kind\": \"password\",
        \"credentials\": {\"user\":\"$DATA_USER\",\"password\":\"$DATA_PASS\"}
      }")
WS_ID=$(echo "$WS" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
[ -n "$WS_ID" ] || fail "no workspace id: $WS"
echo "workspace $WS_ID"

say "5. Wait for profiling (needs Celery worker running)"
for i in $(seq 1 20); do
  STATUS=$(curl -fsS "$API/workspaces/$WS_ID" -H "Authorization: Bearer $TOKEN" \
    | sed -n 's/.*"status":"\([^"]*\)".*/\1/p')
  echo "  status=$STATUS"
  [ "$STATUS" = "ready" ] && break
  [ "$STATUS" = "error" ] && fail "profiling errored"
  sleep 2
done
[ "${STATUS:-}" = "ready" ] || echo "  (still $STATUS — is the Celery worker up?)"

say "6. Chat (SSE)"
curl -fsS -N -X POST "$API/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"message\":\"total revenue by region\",\"active_workspace_id\":\"$WS_ID\"}" \
  | sed 's/^/  /' | head -40

printf '\n\033[1;32mSmoke test reached the chat stream.\033[0m\n'

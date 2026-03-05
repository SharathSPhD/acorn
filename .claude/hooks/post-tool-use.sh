#!/bin/bash
# ACORN PostToolUse Hook — thin telemetry relay (PRD AP-4: hooks are thin relays)
# POSTs raw tool-use payload to acorn-api for processing.
# Never blocks (always exits 0). Never contains business logic.
set -euo pipefail

PAYLOAD=$(cat)
ACORN_API="${ACORN_API_URL:-http://acorn-api:8000}"

curl -s -m 2 -X POST "$ACORN_API/api/telemetry/tool-event" \
    -H "Content-Type: application/json" \
    -H "X-Agent-Id: ${ACORN_AGENT_ID:-unknown}" \
    -H "X-Problem-UUID: ${ACORN_PROBLEM_UUID:-unknown}" \
    -d "$PAYLOAD" \
    > /dev/null 2>&1 || true

exit 0

#!/bin/bash
# ACORN Idle Hook — thin relay (PRD AP-4: hooks are thin relays)
# Fires on agent idle; queries current task via API (never direct DB).
set -euo pipefail

PAYLOAD=$(cat)
TYPE=$(echo "$PAYLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type',''))" 2>/dev/null || echo "")

if [ "$TYPE" != "idle" ] && [ "$TYPE" != "waiting" ]; then
    exit 0
fi

AGENT_ID="${ACORN_AGENT_ID:-unknown}"
PROBLEM_UUID="${ACORN_PROBLEM_UUID:-unknown}"
ACORN_API="${ACORN_API_URL:-http://acorn-api:8000}"

CURRENT_TASK=$(curl -sf -m 3 "$ACORN_API/api/tasks/current?agent_id=$AGENT_ID&problem_id=$PROBLEM_UUID" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('task','unknown task'))" 2>/dev/null || echo "unknown task")

curl -s -m 2 -X POST "$ACORN_API/internal/events" \
    -H "Content-Type: application/json" \
    -d "{\"event_type\":\"agent_idle\",\"agent_id\":\"$AGENT_ID\",\"problem_uuid\":\"$PROBLEM_UUID\",\"timestamp_utc\":$(date +%s.%3N),\"payload\":{\"current_task\":\"$CURRENT_TASK\"}}" \
    > /dev/null 2>&1 || true

exit 0

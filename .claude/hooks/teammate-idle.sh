#!/bin/bash
# ACORN Notification Hook — refocus injection on agent idle.
# Fires when Claude Code sends a Notification event (typically on idle/waiting).
# Receives JSON on stdin with notification details.
# Never blocks (always exits 0).
set -euo pipefail

PAYLOAD=$(cat)
TYPE=$(echo "$PAYLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('type',''))" 2>/dev/null || echo "")

# Only act on idle notifications
if [ "$TYPE" != "idle" ] && [ "$TYPE" != "waiting" ]; then
    exit 0
fi

AGENT_ID="${ACORN_AGENT_ID:-unknown}"
PROBLEM_UUID="${ACORN_PROBLEM_UUID:-unknown}"

# Fetch current task description from DB
CURRENT_TASK=$(psql "${DATABASE_URL:-postgresql://acorn:acorn@acorn-postgres:5432/acorn}" -t -A -c \
    "SELECT title || ': ' || COALESCE(description, 'no description') FROM tasks \
     WHERE problem_id = '$PROBLEM_UUID' AND assigned_to = '$AGENT_ID' AND status = 'claimed' \
     LIMIT 1;" 2>/dev/null || echo "unknown task")

# Emit refocus event to API (will be relayed to agent via mailbox)
curl -s -m 2 -X POST "http://acorn-api:8000/internal/events" \
    -H "Content-Type: application/json" \
    -d "{
        \"event_type\": \"agent_idle\",
        \"agent_id\": \"$AGENT_ID\",
        \"problem_uuid\": \"$PROBLEM_UUID\",
        \"timestamp_utc\": $(date +%s.%3N),
        \"schema_version\": \"1.0\",
        \"payload\": {
            \"current_task\": \"$CURRENT_TASK\",
            \"message\": \"You appear idle. Your current task is: $CURRENT_TASK. Continue or flag a blocker in the mailbox.\"
        }
    }" > /dev/null 2>&1 || true

exit 0

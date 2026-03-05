#!/bin/bash
# ACORN Task Completed Hook — thin relay (PRD AP-4: hooks are thin relays)
# Blocks TaskUpdate status=completed without a Judge PASS via API check.
# Exit 2 = block. Exit 0 = allow.
set -euo pipefail

PAYLOAD=$(cat)
TOOL_NAME=$(echo "$PAYLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")

if [ "$TOOL_NAME" != "TaskUpdate" ] && [ "$TOOL_NAME" != "mcp__claude_code__TaskUpdate" ]; then
    exit 0
fi

STATUS=$(echo "$PAYLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('status',''))" 2>/dev/null || echo "")
[ "$STATUS" != "completed" ] && exit 0

TASK_ID=$(echo "$PAYLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('taskId',''))" 2>/dev/null || echo "")
[ -z "$TASK_ID" ] && exit 0

ACORN_API="${ACORN_API_URL:-http://acorn-api:8000}"
HAS_PASS=$(curl -sf -m 3 "$ACORN_API/api/judge_verdicts/check/$TASK_ID" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_pass',False))" 2>/dev/null || echo "False")

if [ "$HAS_PASS" != "True" ]; then
    echo "[ACORN task-completed] BLOCKED: task $TASK_ID has no Judge PASS verdict." >&2
    exit 2
fi

curl -s -m 2 -X POST "$ACORN_API/internal/events" \
    -H "Content-Type: application/json" \
    -d "{\"event_type\":\"task_completed\",\"agent_id\":\"${ACORN_AGENT_ID:-unknown}\",\"problem_uuid\":\"${ACORN_PROBLEM_UUID:-unknown}\",\"timestamp_utc\":$(date +%s.%3N),\"payload\":{\"task_id\":\"$TASK_ID\"}}" \
    > /dev/null 2>&1 || true

exit 0

#!/bin/bash
# OAK Task Gate Hook — blocks TaskUpdate status=completed without a Judge PASS.
# This is the hook referenced in settings.json as the second PreToolUse handler.
# Receives JSON on stdin with tool call details.
# Exit 2 = block. Exit 0 = allow.
set -euo pipefail

PAYLOAD=$(cat)
TOOL_NAME=$(echo "$PAYLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")

# Only intercept task completion attempts
if [ "$TOOL_NAME" != "TaskUpdate" ] && [ "$TOOL_NAME" != "mcp__claude_code__TaskUpdate" ]; then
    exit 0
fi

# Check if this is a "completed" status update
STATUS=$(echo "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
inp = d.get('tool_input', {})
print(inp.get('status', ''))
" 2>/dev/null || echo "")

if [ "$STATUS" != "completed" ]; then
    exit 0
fi

# Require a Judge PASS verdict for this task
TASK_ID=$(echo "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
inp = d.get('tool_input', {})
print(inp.get('taskId', ''))
" 2>/dev/null || echo "")

if [ -z "$TASK_ID" ]; then
    exit 0  # Can't verify without task ID; let it through
fi

# Query PostgreSQL for a PASS verdict
HAS_PASS=$(psql "${DATABASE_URL:-postgresql://oak:oak@oak-postgres:5432/oak}" -t -A -c \
    "SELECT COUNT(*) FROM judge_verdicts WHERE task_id = '$TASK_ID' AND verdict = 'pass';" \
    2>/dev/null || echo "0")

if [ "${HAS_PASS:-0}" -lt "1" ]; then
    echo "[OAK task-gate] BLOCKED: task $TASK_ID has no Judge PASS verdict. Invoke the Judge Agent before closing this task." >&2
    exit 2
fi

# PASS exists — also trigger skill extraction (async, non-blocking)
curl -s -m 2 -X POST "http://oak-api:8000/internal/events" \
    -H "Content-Type: application/json" \
    -d "{\"event_type\":\"task_completed\",\"agent_id\":\"${OAK_AGENT_ID:-unknown}\",\"problem_uuid\":\"${OAK_PROBLEM_UUID:-unknown}\",\"timestamp_utc\":$(date +%s.%3N),\"schema_version\":\"1.0\",\"payload\":{\"task_id\":\"$TASK_ID\"}}" \
    > /dev/null 2>&1 || true

exit 0

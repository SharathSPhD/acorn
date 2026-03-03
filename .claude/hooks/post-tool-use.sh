#!/bin/bash
# OAK PostToolUse Hook — thin telemetry relay (PRD anti-pattern AP-4: hooks are thin relays)
# Receives JSON on stdin: {"tool_name": "...", "tool_input": {...}, "tool_response": {...}}
# NEVER blocks (always exits 0). Never contains business logic.
set -euo pipefail

PAYLOAD=$(cat)
START_MS=${OAK_TOOL_START_MS:-0}
NOW_MS=$(date +%s%3N)
DURATION_MS=$(( NOW_MS - START_MS ))

EVENT=$(python3 - <<'PYEOF'
import sys, json, os, time

payload = json.load(sys.stdin)
event = {
    "event_type": "tool_called",
    "agent_id": os.environ.get("OAK_AGENT_ID", "unknown"),
    "problem_uuid": os.environ.get("OAK_PROBLEM_UUID", "unknown"),
    "timestamp_utc": time.time(),
    "schema_version": "1.0",
    "payload": payload
}
print(json.dumps(event))
PYEOF
) <<< "$PAYLOAD"

# POST to OAK API event bus — fire-and-forget, never block on failure
curl -s -m 2 -X POST \
    "http://oak-api:8000/internal/events" \
    -H "Content-Type: application/json" \
    -d "$EVENT" \
    > /dev/null 2>&1 || true

exit 0

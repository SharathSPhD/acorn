#!/bin/bash
# OAK Tool Proxy — Layer 1 deny-list (outermost security layer)
# Intercepts every command Claude Code would execute.
# Deny patterns are read from /workspace/scripts/deny-patterns.txt at runtime.
# Changes to deny-patterns.txt take effect without image rebuild.
set -euo pipefail

DENY_FILE="/workspace/scripts/deny-patterns.txt"
LOG_FILE="/tmp/oak-tool-proxy.log"

# Log the command for telemetry
echo "$(date -Iseconds) TOOL_PROXY: $*" >> "$LOG_FILE"

# Build the full command string for pattern matching
CMD="$*"

# Check deny patterns
if [ -f "$DENY_FILE" ]; then
    while IFS= read -r pattern; do
        [ -z "$pattern" ] && continue
        [[ "${pattern:0:1}" == "#" ]] && continue
        [[ "$pattern" == OAK:* ]] && continue  # OAK rules handled by pre-tool-use.sh
        if echo "$CMD" | grep -qiE "$pattern"; then
            echo "[OAK tool-proxy] BLOCKED: '$pattern' matched in: $CMD" >&2
            # Emit blocked event to Redis for telemetry
            redis-cli -u "${REDIS_URL:-redis://oak-redis:6379}" \
                PUBLISH "oak:blocked:${OAK_AGENT_ID:-unknown}" \
                "{\"cmd\":\"$CMD\",\"pattern\":\"$pattern\",\"ts\":$(date +%s)}" \
                > /dev/null 2>&1 || true
            exit 2
        fi
    done < "$DENY_FILE"
fi

# Execute the requested command
exec "$@"

#!/bin/bash
# OAK PreToolUse Hook — Layer 2 deny-list (tool-proxy.sh is Layer 1)
# Receives JSON on stdin: {"tool_name": "...", "tool_input": {...}}
# Exit 2 = block tool call. Exit 0 = allow.
set -euo pipefail

PAYLOAD=$(cat)
TOOL_NAME=$(echo "$PAYLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OAK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DENY_FILE="$OAK_ROOT/scripts/deny-patterns.txt"

# ── Bash tool: deny-list check ─────────────────────────────────────────────
if [ "$TOOL_NAME" = "Bash" ]; then
    CMD=$(echo "$PAYLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

    if [ -f "$DENY_FILE" ]; then
        while IFS= read -r pattern; do
            [ -z "$pattern" ] && continue
            [[ "${pattern:0:1}" == "#" ]] && continue
            # Skip OAK-business-rule lines in Layer 2 — handle them separately below
            [[ "$pattern" == OAK:* ]] && continue
            if echo "$CMD" | grep -qiE "$pattern"; then
                echo "[OAK pre-tool-use] BLOCKED: command matched deny pattern: $pattern" >&2
                exit 2
            fi
        done < "$DENY_FILE"
    fi

    # OAK business rules: never push directly to protected branches
    if echo "$CMD" | grep -qiE "git push.*(main|oak/agents|oak/skills|oak/ui)"; then
        echo "[OAK pre-tool-use] BLOCKED: direct push to protected branch. Open a PR instead." >&2
        exit 2
    fi

    # Never commit to main directly (commit + main without a branch)
    if echo "$CMD" | grep -qi "git commit" && git -C "$OAK_ROOT" branch --show-current 2>/dev/null | grep -q "^main$"; then
        echo "[OAK pre-tool-use] BLOCKED: direct commit to main. Create a feature branch first." >&2
        exit 2
    fi
fi

exit 0

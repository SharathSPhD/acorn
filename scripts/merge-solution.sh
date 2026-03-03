#!/bin/bash
# OAK Merge Solution — merges a completed problem branch back and archives it.
# Usage: scripts/merge-solution.sh [problem-uuid]
set -euo pipefail

PROBLEM_UUID="${1:?Usage: merge-solution.sh <problem-uuid>}"
OAK_HOME="${OAK_HOME:-$HOME/oak}"
BRANCH="oak/problem-$PROBLEM_UUID"

# Verify Judge PASS exists
HAS_PASS=$(psql "${DATABASE_URL:-postgresql://oak:oak@oak-postgres:5432/oak}" -t -A \
    -c "SELECT COUNT(*) FROM judge_verdicts jv
        JOIN tasks t ON jv.task_id = t.id
        WHERE t.problem_id = '$PROBLEM_UUID' AND jv.verdict = 'pass';" \
    2>/dev/null || echo "0")

if [ "${HAS_PASS:-0}" -lt "1" ]; then
    echo "[ERROR] No Judge PASS found for problem $PROBLEM_UUID. Cannot merge." >&2
    exit 1
fi

# Archive the problem branch (do not delete — keep for audit)
cd "$OAK_HOME"
git tag "archive/problem-$PROBLEM_UUID" "$BRANCH" 2>/dev/null || true
echo "[ok] Tagged $BRANCH as archive/problem-$PROBLEM_UUID"
echo "[info] Worktree at ~/oak-workspaces/problem-$PROBLEM_UUID kept for review"
echo "Run cleanup-orphans.sh to remove when done"

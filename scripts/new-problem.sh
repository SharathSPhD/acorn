#!/bin/bash
# OAK New Problem — creates a per-problem git worktree and launches the orchestrator.
# Usage: scripts/new-problem.sh [problem-uuid]
set -euo pipefail

PROBLEM_UUID="${1:-$(python3 -c 'import uuid; print(uuid.uuid4())')}"
OAK_HOME="${OAK_HOME:-$HOME/oak}"
WORKSPACES="${WORKSPACES:-$HOME/oak-workspaces}"
WORKTREE_PATH="$WORKSPACES/problem-$PROBLEM_UUID"
BRANCH="oak/problem-$PROBLEM_UUID"

echo "=== OAK New Problem: $PROBLEM_UUID ==="

# 1. Create problem branch
cd "$OAK_HOME"
git checkout -b "$BRANCH"

# 2. Create per-problem worktree
mkdir -p "$WORKSPACES"
git worktree add "$WORKTREE_PATH" "$BRANCH"
echo "[ok] worktree: $WORKTREE_PATH -> $BRANCH"

# 3. Write initial PROBLEM.md stub
cat > "$WORKTREE_PATH/PROBLEM.md" <<PROBLEM_MD
# Problem: $PROBLEM_UUID
## Status: pending
## Created: $(date -Iseconds)
## Data location: /mnt/oak-data/$PROBLEM_UUID/

<!-- Orchestrator: fill in the sections below before creating tasks -->
## Restated Goal
TODO

## Target User and Primary Task
TODO

## Success Metrics
- TODO

## Out of Scope (v1)
- TODO

## Open Questions / Discovery Probes
- TODO
PROBLEM_MD

# 4. Register problem in PostgreSQL
psql "${DATABASE_URL:-postgresql://oak:oak@oak-postgres:5432/oak}" \
    -c "INSERT INTO problems (id, title, status) VALUES ('$PROBLEM_UUID', 'Problem $PROBLEM_UUID', 'pending');" \
    2>/dev/null || echo "[warn] Could not register in DB — stack may not be running"

# 5. Launch orchestrator in harness container
echo "=== Launching orchestrator ==="
docker run -d \
    --name "oak-orchestrator-$PROBLEM_UUID" \
    --network oak-net \
    -v "$WORKTREE_PATH:/workspace" \
    -v "$WORKSPACES/skills:/mnt/oak-skills:ro" \
    -e "OAK_AGENT_ID=orchestrator-$PROBLEM_UUID" \
    -e "OAK_PROBLEM_UUID=$PROBLEM_UUID" \
    -e "DATABASE_URL=${DATABASE_URL:-postgresql://oak:oak@oak-postgres:5432/oak}" \
    -e "REDIS_URL=${REDIS_URL:-redis://oak-redis:6379}" \
    -e "ANTHROPIC_BASE_URL=http://oak-api-proxy:9000" \
    -e "ANTHROPIC_AUTH_TOKEN=ollama" \
    -e "ANTHROPIC_API_KEY=" \
    -e "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" \
    oak/harness:latest \
    --agent orchestrator \
    --workspace /workspace
echo "=== Orchestrator launched for problem $PROBLEM_UUID ==="
echo "Monitor: docker logs -f oak-orchestrator-$PROBLEM_UUID"

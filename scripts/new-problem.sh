#!/bin/bash
# Create a new OAK problem workspace and launch orchestrator
# Usage: bash scripts/new-problem.sh [uuid]
set -euo pipefail

PROBLEM_UUID="${1:-$(python3 -c 'import uuid; print(uuid.uuid4())')}"
BRANCH="oak/problem-${PROBLEM_UUID}"
WORKTREE_PATH="${HOME}/oak-workspaces/problem-${PROBLEM_UUID}"

echo "[new-problem] UUID: $PROBLEM_UUID"

# Create branch + worktree
git worktree add -b "$BRANCH" "$WORKTREE_PATH" main

# Launch orchestrator container
docker run -d \
    --name "oak-harness-${PROBLEM_UUID}" \
    --network oak-net \
    -e ANTHROPIC_BASE_URL=http://oak-api-proxy:9000 \
    -e ANTHROPIC_AUTH_TOKEN=ollama \
    -e ANTHROPIC_API_KEY="" \
    -e OAK_PROBLEM_UUID="$PROBLEM_UUID" \
    -v "${WORKTREE_PATH}:/workspace" \
    oak/harness:latest

echo "[new-problem] Workspace: $WORKTREE_PATH  Branch: $BRANCH"

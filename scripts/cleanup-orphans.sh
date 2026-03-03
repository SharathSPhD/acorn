#!/bin/bash
# Remove stopped harness containers and pruned worktrees
set -euo pipefail

echo "[cleanup] Removing stopped harness containers..."
docker ps -a --filter "name=oak-harness-" --filter "status=exited" \
    --format "{{.Names}}" | xargs -r docker rm

echo "[cleanup] Pruning stale worktrees..."
git worktree prune

echo "[cleanup] Done."

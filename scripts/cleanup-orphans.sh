#!/bin/bash
# OAK Cleanup Orphans — removes harness containers for completed/failed problems.
# Run on a cron schedule: */5 * * * * bash /home/oak/scripts/cleanup-orphans.sh
set -euo pipefail

DB_URL="${DATABASE_URL:-postgresql://oak:oak@oak-postgres:5432/oak}"

# Find problems that are complete or failed
DONE_UUIDS=$(psql "$DB_URL" -t -A \
    -c "SELECT id FROM problems WHERE status IN ('complete','failed') AND updated_at < NOW() - INTERVAL '1 hour';" \
    2>/dev/null || echo "")

for uuid in $DONE_UUIDS; do
    # Stop and remove all harness containers for this problem
    docker ps -q --filter "name=oak-.*-$uuid" | xargs -r docker stop
    docker ps -aq --filter "name=oak-.*-$uuid" | xargs -r docker rm
    echo "[cleanup] Removed containers for problem $uuid"
done

# Also clean up worktrees for archived problems
for worktree in ~/oak-workspaces/problem-*/; do
    uuid=$(basename "$worktree" | sed 's/problem-//')
    # Check if all containers are gone
    if ! docker ps -q --filter "name=oak-.*-$uuid" | grep -q .; then
        git -C ~/oak worktree remove --force "$worktree" 2>/dev/null || true
        echo "[cleanup] Removed orphan worktree $worktree"
    fi
done

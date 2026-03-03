#!/bin/bash
# OAK Bootstrap — run once on a new node to set up the full stack.
# Requires: docker, git, SSH key for github.com
set -euo pipefail

REPO="git@github.com:SharathSPhD/oak.git"
OAK_HOME="${OAK_HOME:-$HOME/oak}"
WORKSPACES="${WORKSPACES:-$HOME/oak-workspaces}"

echo "=== OAK Bootstrap ==="
echo "OAK_HOME: $OAK_HOME"
echo "WORKSPACES: $WORKSPACES"

# 1. Clone or update
if [ ! -d "$OAK_HOME/.git" ]; then
    git clone "$REPO" "$OAK_HOME"
else
    echo "[skip] $OAK_HOME already exists"
fi
cd "$OAK_HOME"

# 2. Configure git
git config user.name "SharathSPhD"
git config user.email ""

# 3. Create worktree directories
mkdir -p "$WORKSPACES"

# 4. Create worktrees (skip if already exist)
for branch in agents skills ui; do
    worktree_path="$WORKSPACES/$branch"
    if [ ! -d "$worktree_path" ]; then
        git fetch origin "oak/$branch" 2>/dev/null || git checkout -b "oak/$branch"
        git worktree add "$worktree_path" "oak/$branch"
        echo "[ok] worktree: $worktree_path -> oak/$branch"
    else
        echo "[skip] worktree $worktree_path already exists"
    fi
done

# 5. Copy .env.template if .env doesn't exist
if [ ! -f "$OAK_HOME/.env" ]; then
    cp "$OAK_HOME/.env.template" "$OAK_HOME/.env"
    echo "[!] .env created from template — fill in required values before running stack"
fi

# 6. Build Docker images
echo "=== Building Docker images ==="
docker build -t oak/api-proxy:latest "$OAK_HOME/oak_mcp/oak-api-proxy/"
docker build -t oak/harness:latest -f "$OAK_HOME/docker/claude-harness/Dockerfile" "$OAK_HOME/docker/claude-harness/"

# 7. Pull Ollama models
echo "=== Pulling Ollama models (run after starting stack) ==="
echo "Run after docker compose up:"
echo "  docker exec oak-ollama ollama pull qwen3-coder"
echo "  docker exec oak-ollama ollama pull glm-4.7"
echo "  docker exec oak-ollama ollama pull llama3.3:70b"

# 8. Start base stack
echo "=== Starting stack ==="
OAK_MODE="${OAK_MODE:-dgx}"
docker compose -f "$OAK_HOME/docker/docker-compose.${OAK_MODE}.yml" \
    up -d oak-postgres oak-redis oak-api-proxy oak-api oak-ui
echo "=== Bootstrap complete ==="
echo "Run: docker compose -f docker/docker-compose.${OAK_MODE}.yml ps"

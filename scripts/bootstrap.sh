#!/bin/bash
# OAK Full-stack bootstrap for DGX Spark
# Usage: bash scripts/bootstrap.sh [dgx|mini|cloud]
set -euo pipefail

MODE="${1:-dgx}"
export OAK_MODE="$MODE"
COMPOSE_FILE="docker/docker-compose.${MODE}.yml"

echo "[bootstrap] Mode: $MODE"

# Build images
docker build -t oak/api-proxy:latest ./oak_mcp/oak-api-proxy/
docker build -t oak/harness:latest ./docker/claude-harness/

# Pull Ollama models
docker compose -f "$COMPOSE_FILE" run --rm oak-ollama \
    sh -c "ollama pull qwen3-coder && ollama pull glm-4.7 && ollama pull llama3.3:70b && ollama pull deepseek-v3"

# Start stack
docker compose -f "$COMPOSE_FILE" up -d \
    oak-postgres oak-redis oak-ollama oak-api-proxy oak-api oak-ui

echo "[bootstrap] Stack healthy. Run: docker compose -f $COMPOSE_FILE ps"

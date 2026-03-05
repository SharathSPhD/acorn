#!/bin/bash
# ACORN Full-stack bootstrap for DGX Spark
# Usage: bash /any/path/scripts/bootstrap.sh [dgx|mini|cloud]
# Self-contained: resolves its own location — works from any CWD.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACORN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="${1:-dgx}"
export ACORN_MODE="$MODE"
COMPOSE_FILE="${ACORN_ROOT}/docker/docker-compose.yml"

echo "[bootstrap] ACORN root : $ACORN_ROOT"
echo "[bootstrap] Mode     : $MODE"
echo "[bootstrap] Compose  : $COMPOSE_FILE (profile: $MODE)"

# --project-directory makes all relative paths in compose files resolve from ACORN_ROOT
# --profile enables mode-specific services (dgx, mini, or cloud)
DC="docker compose --project-directory ${ACORN_ROOT} -f ${COMPOSE_FILE} --profile ${MODE}"

# ── Build images ──────────────────────────────────────────────────────────────
echo "[bootstrap] Building acorn/api-relay ..."
docker build -t acorn/api-relay:latest "${ACORN_ROOT}/acorn_mcp/acorn-api-relay/"

echo "[bootstrap] Building acorn/harness ..."
docker build -t acorn/harness:latest "${ACORN_ROOT}/docker/acorn-harness/"

echo "[bootstrap] Building acorn/api ..."
docker build -t acorn/api:latest -f "${ACORN_ROOT}/docker/api/Dockerfile" "${ACORN_ROOT}"

echo "[bootstrap] Building acorn/ui ..."
docker build -t acorn/ui:latest "${ACORN_ROOT}/ui-next/"

# ── Start infrastructure (Postgres + Redis need to be healthy before API) ─────
echo "[bootstrap] Starting acorn-postgres and acorn-redis ..."
$DC up -d acorn-postgres acorn-redis

echo "[bootstrap] Waiting for Postgres and Redis to be healthy ..."
for i in $(seq 1 30); do
    PG_HEALTHY=$($DC ps acorn-postgres 2>/dev/null | grep -c "healthy" || true)
    RD_HEALTHY=$($DC ps acorn-redis   2>/dev/null | grep -c "healthy" || true)
    if [ "$PG_HEALTHY" -ge 1 ] && [ "$RD_HEALTHY" -ge 1 ]; then
        echo "[bootstrap] Infrastructure healthy."
        break
    fi
    sleep 2
done

# ── Start profile-specific services ───────────────────────────────────────────
# Service names differ per profile
case "$MODE" in
    dgx)
        API_SVC="acorn-api"
        PROXY_SVC="acorn-api-relay"
        UI_SVC="acorn-ui"
        LLM_SVC="acorn-ollama"
        LLM_CONTAINER="acorn-ollama"
        ;;
    mini)
        API_SVC="acorn-api-mini"
        PROXY_SVC="acorn-api-relay-mini"
        UI_SVC="acorn-ui-mini"
        LLM_SVC="acorn-ollama-mini"
        LLM_CONTAINER="acorn-ollama-mini"
        ;;
    cloud)
        API_SVC="acorn-api-cloud"
        PROXY_SVC="acorn-api-relay-cloud"
        UI_SVC="acorn-ui-cloud"
        LLM_SVC="acorn-vllm"
        LLM_CONTAINER="acorn-vllm"
        ;;
    *)
        echo "[error] Unknown mode: $MODE. Use: dgx, mini, or cloud"
        exit 1
        ;;
esac

echo "[bootstrap] Starting $API_SVC and $PROXY_SVC ..."
$DC up -d $PROXY_SVC $API_SVC

echo "[bootstrap] Starting $LLM_SVC (LLM backend) ..."
$DC up -d $LLM_SVC

if [ "$MODE" = "dgx" ] || [ "$MODE" = "mini" ]; then
    echo "[bootstrap] Waiting for Ollama to start ..."
    sleep 10

    echo "[bootstrap] Pulling primary models (this may take a while on first run) ..."
    docker exec $LLM_CONTAINER ollama pull qwen3-coder || echo "[warn] qwen3-coder pull failed — retry: docker exec $LLM_CONTAINER ollama pull qwen3-coder"
    docker exec $LLM_CONTAINER ollama pull glm-4.7    || echo "[warn] glm-4.7 pull failed"
fi

# ── UI ────────────────────────────────────────────────────────────────────────
echo "[bootstrap] Starting $UI_SVC ..."
$DC up -d $UI_SVC

# ── Seed kernels DB ──────────────────────────────────────────────────────────
echo "[bootstrap] Seeding kernel library ..."
sleep 5
PG_CONTAINER=$($DC ps -q acorn-postgres 2>/dev/null || echo "")
if [ -n "$PG_CONTAINER" ]; then
    docker exec -i "$PG_CONTAINER" \
        psql -U acorn -d acorn < "${ACORN_ROOT}/scripts/seed_kernels.sql" 2>/dev/null \
        || echo "[warn] Kernel seed skipped (will auto-apply on next start)"
fi

# ── Status ────────────────────────────────────────────────────────────────────
echo ""
echo "[bootstrap] Stack launched. Verify with:"
echo "  $DC ps"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:9000/health"
echo "  curl http://localhost:11434/api/tags"
echo "  curl http://localhost:8501/_stcore/health"

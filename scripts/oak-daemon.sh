#!/bin/bash
# OAK Self-Healing Daemon
# Runs as a background service: monitors system health, restarts unhealthy services,
# and triggers self-improvement when idle.
#
# Usage: bash scripts/oak-daemon.sh [--once]  (--once runs one cycle and exits)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OAK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OAK_API="${OAK_API_URL:-http://localhost:8000}"
POLL_INTERVAL="${OAK_DAEMON_POLL_INTERVAL:-60}"
COMPOSE_FILE="${OAK_ROOT}/docker/docker-compose.yml"
MODE="${OAK_MODE:-dgx}"
DC="docker compose --project-directory ${OAK_ROOT} -f ${COMPOSE_FILE} --profile ${MODE}"
RUN_ONCE="${1:-}"

log() { echo "[oak-daemon $(date +%H:%M:%S)] $*"; }

check_service_health() {
    local service="$1"
    local container
    container=$(docker ps -q --filter "name=$service" --filter "status=running" 2>/dev/null)
    if [ -z "$container" ]; then
        return 1
    fi
    return 0
}

restart_service() {
    local service="$1"
    log "HEAL: Restarting $service..."
    $DC restart "$service" 2>/dev/null || log "WARN: Could not restart $service"
}

check_models() {
    local ollama_container
    ollama_container=$(docker ps -q --filter "name=oak-.*ollama" --filter "status=running" 2>/dev/null | head -1)
    if [ -z "$ollama_container" ]; then
        log "WARN: Ollama not running, skipping model check"
        return
    fi
    local models
    models=$(docker exec "$ollama_container" ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')
    if ! echo "$models" | grep -q "qwen3-coder"; then
        log "HEAL: qwen3-coder missing, pulling..."
        docker exec "$ollama_container" ollama pull qwen3-coder 2>/dev/null &
    fi
}

check_db_connectivity() {
    local pg_container
    pg_container=$(docker ps -q --filter "name=oak-.*postgres" --filter "status=running" 2>/dev/null | head -1)
    if [ -z "$pg_container" ]; then
        log "WARN: Postgres not running"
        return 1
    fi
    docker exec "$pg_container" pg_isready -U oak -q 2>/dev/null || return 1
    return 0
}

count_active_problems() {
    curl -sf "$OAK_API/api/problems" 2>/dev/null | python3 -c "
import sys, json
try:
    problems = json.load(sys.stdin)
    active = sum(1 for p in problems if p.get('status') in ('active', 'assembling', 'pending'))
    print(active)
except:
    print(0)
" 2>/dev/null || echo "0"
}

cleanup_orphan_containers() {
    local exited
    exited=$(docker ps -a --filter "name=oak-harness-" --filter "status=exited" --format "{{.Names}}" 2>/dev/null)
    local count=0
    for c in $exited; do
        if [ $count -ge 5 ]; then
            docker rm "$c" 2>/dev/null && log "CLEAN: Removed orphan $c"
        fi
        count=$((count + 1))
    done
}

sync_stale_problems() {
    local result
    result=$(curl -sf -X POST "$OAK_API/api/problems/cleanup" 2>/dev/null)
    if [ -n "$result" ]; then
        local cleaned
        cleaned=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cleaned',0))" 2>/dev/null || echo "0")
        if [ "$cleaned" -gt 0 ]; then
            log "SYNC: Marked $cleaned stale problems as failed"
        fi
    fi
}

LAST_BUILDER_RUN=0
BUILDER_COOLDOWN="${OAK_BUILDER_COOLDOWN:-3600}"

trigger_builder() {
    local now
    now=$(date +%s)
    local elapsed=$((now - LAST_BUILDER_RUN))
    if [ "$elapsed" -lt "$BUILDER_COOLDOWN" ]; then
        log "BUILDER: Skipping — last run ${elapsed}s ago (cooldown ${BUILDER_COOLDOWN}s)"
        return
    fi

    local health_data
    health_data=$(curl -sf "$OAK_API/health" 2>/dev/null)
    if [ -z "$health_data" ]; then
        log "BUILDER: Cannot reach API, skipping"
        return
    fi

    local builder_enabled
    builder_enabled=$(echo "$health_data" | jq -r '.feature_flags.builder_enabled // false' 2>/dev/null)

    if [ "$builder_enabled" != "true" ]; then
        log "BUILDER: Disabled via feature flag"
        return
    fi

    log "BUILDER: Triggering self-build sprint..."
    local trigger_result
    trigger_result=$(curl -sf -X POST "$OAK_API/api/builder/start-sprint" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$trigger_result" ]; then
        log "BUILDER: Sprint triggered: $trigger_result"
        LAST_BUILDER_RUN=$now
    else
        log "BUILDER: Trigger failed"
    fi
}

run_health_cycle() {
    log "Health check starting..."
    local issues=0

    # Check core services
    for svc in "oak-.*postgres" "oak-.*redis" "oak-.*api-proxy" "oak-.*api-1" "oak-.*ollama"; do
        if ! check_service_health "$svc"; then
            log "ALERT: $svc is DOWN"
            issues=$((issues + 1))
        fi
    done

    # Check DB
    if ! check_db_connectivity; then
        log "ALERT: Database not reachable"
        issues=$((issues + 1))
    fi

    # Check models
    check_models

    # Clean orphans and sync stale problems
    cleanup_orphan_containers
    sync_stale_problems

    # Report
    local active
    active=$(count_active_problems)
    log "Health check done: $issues issues, $active active problems"

    if [ "$active" -eq 0 ] && [ "$issues" -eq 0 ]; then
        log "System idle and healthy — triggering builder"
        trigger_builder
    fi
}

# Main loop
log "OAK daemon started (mode=$MODE, poll=${POLL_INTERVAL}s)"
while true; do
    run_health_cycle
    if [ "$RUN_ONCE" = "--once" ]; then
        log "Single cycle complete (--once), exiting"
        exit 0
    fi
    sleep "$POLL_INTERVAL"
done

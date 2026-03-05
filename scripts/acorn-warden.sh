#!/usr/bin/env bash
set -euo pipefail

ACORN_API="${ACORN_API_URL:-http://acorn-api:8000}"
POLL_INTERVAL="${ACORN_WARDEN_POLL_INTERVAL:-60}"
META_COOLDOWN="${ACORN_META_COOLDOWN:-3600}"
ACORN_MODE="${ACORN_MODE:-dgx}"

log() { echo "[warden $(date -Iseconds)] $*"; }

log "ACORN Warden starting (mode=$ACORN_MODE, poll=${POLL_INTERVAL}s, meta_cooldown=${META_COOLDOWN}s)"

wait_for_api() {
    local retries=0
    while ! curl -sf "$ACORN_API/health" > /dev/null 2>&1; do
        retries=$((retries + 1))
        if [ $retries -gt 60 ]; then
            log "ERROR: API not reachable after 60 retries. Exiting."
            exit 1
        fi
        log "Waiting for API at $ACORN_API ($retries/60)..."
        sleep 5
    done
    log "API is healthy."
}

check_harness_health() {
    local stale_count=0
    local containers
    containers=$(docker ps --filter "name=acorn-harness-" --format "{{.Names}}" 2>/dev/null || true)

    for name in $containers; do
        local status
        status=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || echo "unknown")

        if [ "$status" = "exited" ] || [ "$status" = "dead" ]; then
            log "Cleaning up stopped harness: $name (status=$status)"
            docker rm -f "$name" > /dev/null 2>&1 || true
            stale_count=$((stale_count + 1))
        fi
    done

    if [ "$stale_count" -gt 0 ]; then
        log "Cleaned $stale_count stale harness containers."
        curl -sf -X POST "$ACORN_API/api/problems/cleanup" > /dev/null 2>&1 || true
    fi
}

check_service_health() {
    local services=("acorn-postgres" "acorn-redis" "acorn-api-relay")
    for svc in "${services[@]}"; do
        if ! docker inspect --format '{{.State.Running}}' "$svc" 2>/dev/null | grep -q "true"; then
            log "WARN: $svc is not running. Attempting restart..."
            docker start "$svc" > /dev/null 2>&1 || log "ERROR: Failed to restart $svc"
        fi
    done
}

report_telemetry() {
    local running
    running=$(docker ps --filter "name=acorn-harness-" --format "{{.Names}}" 2>/dev/null | wc -l)
    local payload
    payload=$(cat <<EOF
{"metric":"warden_cycle","value":{"running_harnesses":$running,"mode":"$ACORN_MODE","timestamp":"$(date -Iseconds)"}}
EOF
)
    curl -sf -X POST "$ACORN_API/internal/events" \
        -H "Content-Type: application/json" \
        -d "$payload" > /dev/null 2>&1 || true
}

wait_for_api

cycle=0
while true; do
    cycle=$((cycle + 1))
    log "Cycle $cycle: checking health..."

    check_harness_health
    check_service_health
    report_telemetry

    log "Cycle $cycle complete. Sleeping ${POLL_INTERVAL}s."
    sleep "$POLL_INTERVAL"
done

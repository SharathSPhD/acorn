#!/usr/bin/env bash
set -euo pipefail

ACORN_API="${ACORN_API_URL:-http://acorn-api:8000}"
POLL_INTERVAL="${ACORN_WARDEN_POLL_INTERVAL:-60}"
META_COOLDOWN="${ACORN_META_COOLDOWN:-3600}"
ACORN_MODE="${ACORN_MODE:-dgx}"
CORTEX_AUTOSTART="${CORTEX_AUTOSTART:-true}"
META_SCHEDULE_PROBLEMS="${ACORN_META_SCHEDULE_PROBLEMS:-10}"
EPISODE_CONSOLIDATION_THRESHOLD="${ACORN_EPISODE_THRESHOLD:-100}"

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
        local found=false
        for cname in $(docker ps -a --filter "name=$svc" --format "{{.Names}}" 2>/dev/null); do
            found=true
            local running
            running=$(docker inspect --format '{{.State.Running}}' "$cname" 2>/dev/null || echo "false")
            if [ "$running" != "true" ]; then
                log "WARN: $cname is not running. Attempting restart..."
                docker start "$cname" > /dev/null 2>&1 || log "ERROR: Failed to restart $cname"
            fi
        done
        if [ "$found" = "false" ]; then
            log "WARN: No container matching $svc found."
        fi
    done
}

check_cortex_health() {
    # If CORTEX_AUTOSTART is enabled, ensure the cognitive kernel is running.
    # The API lifespan starts it; if the API restarted without CORTEX+, POST to restart.
    if [ "$CORTEX_AUTOSTART" != "true" ]; then
        return
    fi
    local status_resp
    status_resp=$(curl -sf "$ACORN_API/api/cortex/status" 2>/dev/null || echo "")
    if echo "$status_resp" | grep -q '"running":false'; then
        log "CORTEX+ is stopped. Sending restart request..."
        curl -sf -X POST "$ACORN_API/api/cortex/start" \
            -H "Content-Type: application/json" \
            -d '{"source":"warden"}' > /dev/null 2>&1 || true
    fi
}

check_meta_agent_schedule() {
    # Track completed problems and trigger meta-agent after every N completions.
    local completed
    completed=$(curl -sf "$ACORN_API/api/problems" 2>/dev/null | \
        jq '[.[] | select(.status == "complete")] | length' 2>/dev/null || echo "0")
    local modulo
    modulo=$((completed % META_SCHEDULE_PROBLEMS))
    if [ "$completed" -gt 0 ] && [ "$modulo" -eq 0 ]; then
        local meta_flag="/tmp/acorn_meta_triggered_${completed}"
        if [ ! -f "$meta_flag" ]; then
            log "Triggering meta-agent: $completed problems completed."
            curl -sf -X POST "$ACORN_API/api/problems" \
                -H "Content-Type: application/json" \
                -d "{\"title\":\"WARDEN: meta-analysis at $completed problems\",\"description\":\"Analyse agent performance, reward distributions, and prompt effectiveness across the last $META_SCHEDULE_PROBLEMS completed problems. Open amendment PRs for underperforming roles.\",\"source\":\"warden\"}" \
                > /dev/null 2>&1 || true
            touch "$meta_flag"
        fi
    fi
}

check_episode_consolidation() {
    # Trigger episodic memory consolidation when episodes exceed threshold.
    # This extracts recurring patterns and writes KERNEL.md candidates to probationary grove.
    local episode_count
    episode_count=$(curl -sf "$ACORN_API/api/telemetry/episode-count" 2>/dev/null | \
        jq '.count // 0' 2>/dev/null || echo "0")
    if [ "$episode_count" -ge "$EPISODE_CONSOLIDATION_THRESHOLD" ]; then
        local flag="/tmp/acorn_consolidation_${episode_count}"
        if [ ! -f "$flag" ]; then
            log "Triggering episodic consolidation: $episode_count episodes."
            curl -sf -X POST "$ACORN_API/api/memory/consolidate" \
                -H "Content-Type: application/json" \
                -d '{"domain":"all","source":"warden"}' > /dev/null 2>&1 || true
            touch "$flag"
        fi
    fi
}

auto_start_pending_problems() {
    local max_concurrent="${ACORN_MAX_CONCURRENT:-3}"
    local problems_json
    problems_json=$(curl -sf "$ACORN_API/api/problems" 2>/dev/null || echo "[]")

    local active_count
    active_count=$(echo "$problems_json" | jq '[.[] | select(.status == "active")] | length' 2>/dev/null || echo "0")

    if [ "$active_count" -ge "$max_concurrent" ]; then
        return
    fi

    local slots=$((max_concurrent - active_count))
    local pending_uuids
    pending_uuids=$(echo "$problems_json" | jq -r "[.[] | select(.status == \"pending\")] | .[0:$slots] | .[].id" 2>/dev/null || true)

    for uuid in $pending_uuids; do
        log "Auto-starting pending problem: $uuid"
        local result
        result=$(curl -sf -X POST "$ACORN_API/api/problems/$uuid/start" \
            -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "")
        if echo "$result" | jq -e '.status == "active"' > /dev/null 2>&1; then
            log "  -> Started successfully"
        else
            log "  -> Start failed or already active"
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
    check_cortex_health
    auto_start_pending_problems
    check_meta_agent_schedule
    check_episode_consolidation
    report_telemetry

    log "Cycle $cycle complete. Sleeping ${POLL_INTERVAL}s."
    sleep "$POLL_INTERVAL"
done

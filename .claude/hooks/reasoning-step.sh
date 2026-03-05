#!/bin/bash
# ACORN Reasoning Step Hook — thin relay to EventBus (PRD anti-pattern AP-4: hooks are thin relays)
# Receives JSON on stdin. POSTs to acorn-api internal/events.
# Never blocks (always exits 0). Never contains business logic.
set -euo pipefail

PAYLOAD=$(cat)
curl -s -m 2 -X POST "http://acorn-api:8000/internal/events" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" >/dev/null 2>&1 || true

exit 0

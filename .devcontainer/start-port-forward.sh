#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="/tmp/arc-frontend-port-forward.log"
PORT_FORWARD_CMD="kubectl port-forward svc/arc-frontend 3000:80 -n arc-store"

echo "Waiting for arc-frontend deployment before starting port-forward on port 3000..."

# Stop an older port-forward if one is still around from a previous session.
pkill -f "$PORT_FORWARD_CMD" || true

# Wait for the frontend deployment to exist and be available before forwarding.
kubectl wait deployment/arc-frontend -n arc-store --for=condition=available --timeout=300s >/dev/null 2>&1 || exit 0

nohup sh -c "$PORT_FORWARD_CMD" >"$LOG_FILE" 2>&1 &
echo "Started arc-frontend port-forward on port 3000. Logs: $LOG_FILE"

#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="/tmp/arc-frontend-port-forward.log"
PORT_FORWARD_CMD="kubectl port-forward svc/arc-frontend 3000:80 -n arc-store"
MAX_ATTEMPTS=60

log() {
	echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"
}

log "Waiting for Kubernetes API and arc-frontend deployment before starting port-forward on port 3000..."

if ! command -v kubectl >/dev/null 2>&1; then
	log "kubectl not found on PATH. Skipping port-forward startup."
	exit 0
fi

# Stop an older port-forward if one is still around from a previous session.
pkill -f "$PORT_FORWARD_CMD" || true

# Wait for the frontend deployment to exist and be available before forwarding.
attempt=1
until kubectl get deployment/arc-frontend -n arc-store >/dev/null 2>&1; do
	if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
		log "arc-frontend deployment not found after ${MAX_ATTEMPTS} attempts. Skipping port-forward startup."
		exit 0
	fi

	if [ "$attempt" -eq 1 ]; then
		log "arc-frontend deployment is not available yet. Retrying..."
	fi

	attempt=$((attempt + 1))
	sleep 5
done

if ! kubectl wait deployment/arc-frontend -n arc-store --for=condition=available --timeout=300s >/dev/null 2>&1; then
	log "arc-frontend deployment did not become available in time. Skipping port-forward startup."
	exit 0
fi

nohup sh -c "$PORT_FORWARD_CMD" >"$LOG_FILE" 2>&1 &
log "Started arc-frontend port-forward on port 3000. Logs: $LOG_FILE"

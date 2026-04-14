#!/bin/bash
# Local dry-run script for testing the orchestrator with real GitHub issue #8

set -e  # Exit on error

# ============================================================================
# CONFIGURATION - values are loaded from .env.local
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.local"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: Missing $ENV_FILE"
  echo "Create it from $SCRIPT_DIR/.env.local.example"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Default if not set in .env.local
INVESTIGATION_MAX_ITERATIONS="${INVESTIGATION_MAX_ITERATIONS:-3}"

# ============================================================================
# Setup
# ============================================================================

echo "Setting up local investigation environment..."

if command -v python3 >/dev/null 2>&1; then
  BASE_PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  BASE_PYTHON="python"
else
  echo "Error: Python is not installed or not on PATH"
  exit 1
fi

# Use a local virtual environment so package installs work on externally-managed Python builds.
VENV_DIR="${VENV_DIR:-.venv-local-investigation}"
if [ ! -d "$VENV_DIR" ]; then
  "$BASE_PYTHON" -m venv "$VENV_DIR"
fi
PYTHON_BIN="$VENV_DIR/bin/python"

if ! "$PYTHON_BIN" -c "import requests, claude_agent_sdk" >/dev/null 2>&1; then
  echo "Installing Python dependencies in $VENV_DIR..."
  "$PYTHON_BIN" -m pip install requests claude-agent-sdk
fi

# Create temp directory for GitHub event
mkdir -p /tmp/github-event

# Download the real issue #8 from GitHub
echo "Fetching issue #8 from GitHub..."
curl -s https://api.github.com/repos/joshDynatrace/dtctl-ai-bug-demo/issues/8 > /tmp/github-event/issue.json

# Create GitHub Actions event wrapper format
echo "Creating GitHub event payload..."
jq '{action: "opened", issue: ., pull_request: null, repository: {name: "dtctl-ai-bug-demo", full_name: "joshDynatrace/dtctl-ai-bug-demo"}}' /tmp/github-event/issue.json > /tmp/github-event/event.json

# ============================================================================
# Set environment variables
# ============================================================================

export GITHUB_EVENT_PATH=/tmp/github-event/event.json
export GITHUB_REPOSITORY="joshDynatrace/dtctl-ai-bug-demo"
export GITHUB_TOKEN="$GITHUB_TOKEN"
export GITHUB_RUN_ID="local-dry-run-$(date +%s)"
export GITHUB_SHA="local-test"
export DT_ENVIRONMENT="$DT_ENVIRONMENT"
export DT_API_TOKEN="$DT_API_TOKEN"
export DTCTL_CONTEXT="demo"
export DTCTL_USE_AGENT_MODE="auto"
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
export INVESTIGATION_MAX_ITERATIONS="$INVESTIGATION_MAX_ITERATIONS"
export AGENT_TRACE="${AGENT_TRACE:-true}"
export AGENT_TRACE_FILE="${AGENT_TRACE_FILE:-$SCRIPT_DIR/output/agent_trace.jsonl}"
export PYTHONUNBUFFERED="1"

# ============================================================================
# Validation
# ============================================================================

echo ""
echo "Validating configuration..."

if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN not configured"
  exit 1
fi

if [ -z "$DT_ENVIRONMENT" ]; then
  echo "Error: DT_ENVIRONMENT not configured"
  exit 1
fi

if [[ "$DT_ENVIRONMENT" != *".live.dynatrace.com"* ]]; then
  echo "Error: DT_ENVIRONMENT must be a .live.dynatrace.com URL"
  exit 1
fi

if [ -z "$DT_API_TOKEN" ]; then
  echo "Error: DT_API_TOKEN not configured"
  exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Error: ANTHROPIC_API_KEY not configured"
  exit 1
fi

if [ -z "$INVESTIGATION_MAX_ITERATIONS" ]; then
  echo "Error: INVESTIGATION_MAX_ITERATIONS not configured"
  exit 1
fi

echo "✓ All credentials configured"
echo ""

# ============================================================================
# Run orchestrator
# ============================================================================

echo "Running orchestrator..."
echo ""

cd "$SCRIPT_DIR"
$PYTHON_BIN -B orchestrator.py

# ============================================================================
# Results
# ============================================================================

echo ""
echo "============================================================================"
echo "Investigation complete!"
echo ""
echo "Check the following for results:"
echo "  - output/           - All investigation artifacts"
echo "  - output/fix_plan.json - Final investigation result from agent runtime"
echo "  - output/investigation_iterations.json - Per-iteration outcomes"
echo "  - output/issue_comment_result.json - Completion comment post result"
echo "  - output/dynatrace_event_result.json - Dynatrace event post result"
echo "============================================================================"

#!/bin/bash
# Local dry-run script for testing the orchestrator with real GitHub issue #8

set -e  # Exit on error

# ============================================================================
# CONFIGURATION - Update these with your actual credentials
# ============================================================================

GITHUB_TOKEN="your-github-token-here"
DT_ENVIRONMENT="your-dt-environment-url"  # e.g., https://xxx.apps.dynatrace.com
DT_API_TOKEN="your-dt-api-token"
ANTHROPIC_API_KEY="your-anthropic-api-key"

# ============================================================================
# Setup
# ============================================================================

echo "Setting up local investigation environment..."

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
export CLAUDECODE="1"
export INVESTIGATION_AGENT="claudecode"
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
export CLAUDECODE_INVESTIGATE_CMD="python claude_runner.py {prompt_file}"
export PYTHONUNBUFFERED="1"

# ============================================================================
# Validation
# ============================================================================

echo ""
echo "Validating configuration..."

if [ "$GITHUB_TOKEN" = "your-github-token-here" ]; then
  echo "❌ Error: GITHUB_TOKEN not configured"
  exit 1
fi

if [ "$DT_ENVIRONMENT" = "your-dt-environment-url" ]; then
  echo "Error: DT_ENVIRONMENT not configured"
  exit 1
fi

if [ "$DT_API_TOKEN" = "your-dt-api-token" ]; then
  echo "Error: DT_API_TOKEN not configured"
  exit 1
fi

if [ "$ANTHROPIC_API_KEY" = "your-anthropic-api-key" ]; then
  echo "❌ Error: ANTHROPIC_API_KEY not configured"
  exit 1
fi

echo "✓ All credentials configured"
echo ""

# ============================================================================
# Run orchestrator
# ============================================================================

echo "Running orchestrator..."
echo ""

cd "$(dirname "$0")"
python orchestrator.py

# ============================================================================
# Results
# ============================================================================

echo ""
echo "============================================================================"
echo "Investigation complete!"
echo ""
echo "Check the following for results:"
echo "  - output/           - All investigation artifacts"
echo "  - output/model_output.json - Claude's raw investigation"
echo "  - output/github_comment.json - Comment that would post to GitHub"
echo "  - output/dynatrace_event.json - Event that would post to Dynatrace"
echo "============================================================================"

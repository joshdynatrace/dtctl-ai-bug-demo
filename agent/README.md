# Agent Automation README

This folder contains the issue-investigation automation for the Dynatrace -> GitHub -> AI-agent demo.

## What This Does

When a matching GitHub issue is created, the workflow:

1. Parses the issue and extracts the dynamic Dynatrace Problem ID (`Problem: P-...`).
2. Posts a "investigation started" comment to the issue.
3. Collects dtctl capability context (command catalog + Live Debugger workspace filters).
4. Renders the investigation prompt from `agent/templates/agent_prompt.md`.
5. Hands off investigation to the configured agent runtime (ClaudeCode path).
6. Posts a completion comment with evidence summary.
7. Sends a Dynatrace event update attached to the same problem ID.
8. Uploads artifacts from `agent/output/`.

## Key Files

- `agent/orchestrator.py`
  - Main pipeline coordinator.
  - Handles issue intake, prompt rendering, comments, agent handoff, and summary artifacts.
- `agent/github_issues.py`
  - GitHub issue comment helpers.
- `agent/dynatrace_events.py`
  - Dynatrace Events API payload assembly + send.
- `agent/templates/agent_prompt.md`
  - Investigation instructions for the agent.
- `agent/templates/dynatrace_event_payload.json`
  - Base Dynatrace event payload template.
- `.github/workflows/dynatrace-agent-investigation.yml`
  - GitHub Actions workflow trigger and runtime setup.

## dtctl AI Agent Mode Auto-Detection

dtctl enables AI agent mode automatically when it detects known environment variables.

For Claude Code, set:

- `CLAUDECODE=1`

This repo workflow already sets that variable so `dtctl` can auto-switch behavior in CI.

## Required GitHub Secrets

Set these repository secrets:

- `DT_ENVIRONMENT`
  - Example: `https://abc12345.apps.dynatrace.com`
- `DT_API_TOKEN`
  - Dynatrace API token with scopes required by your dtctl commands and Events API usage.

## Required/Recommended GitHub Variables

Set these repository variables (Settings -> Secrets and variables -> Actions -> Variables):

- `CLAUDECODE_INVESTIGATE_CMD` (required for real agent execution)
  - Command template that the orchestrator executes.
  - Must include `{prompt_file}` placeholder.
  - Must print a JSON object to stdout.
  - Recommended value:
    - `python agent/claude_runner.py {prompt_file}`

Also set these secrets/vars for `agent/claude_runner.py`:

- Secret: `ANTHROPIC_API_KEY`
- Variable (optional): `CLAUDE_MODEL` (default is `claude-3-7-sonnet-latest`)
- Variable (optional): `CLAUDE_MAX_TOKENS` (default is `2200`)

## Workflow Environment Variables

Configured in `.github/workflows/dynatrace-agent-investigation.yml`:

- `DT_ENVIRONMENT`
- `DT_API_TOKEN`
- `DTCTL_USE_AGENT_MODE=auto`
- `CLAUDECODE=1`
- `INVESTIGATION_AGENT=claudecode`
- `CLAUDECODE_INVESTIGATE_CMD=${{ vars.CLAUDECODE_INVESTIGATE_CMD }}`
- `AUTO_PR=true`
- `DRY_RUN=false`

Optional:

- `DEFAULT_SERVICE_NAME`
  - Used if you want a default service value in context.

## Recommended Precheck Step

Add a fail-fast precheck in GitHub Actions so runs stop early when Claude configuration is missing.

Precheck should validate:

1. `CLAUDECODE_INVESTIGATE_CMD` is set.
2. `ANTHROPIC_API_KEY` secret is set.

Example step:

```yaml
- name: Validate Claude configuration
  env:
    CLAUDECODE_INVESTIGATE_CMD: ${{ vars.CLAUDECODE_INVESTIGATE_CMD }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    if [ -z "$CLAUDECODE_INVESTIGATE_CMD" ]; then
      echo "Missing repo variable: CLAUDECODE_INVESTIGATE_CMD"
      exit 1
    fi
    if [ -z "$ANTHROPIC_API_KEY" ]; then
      echo "Missing repo secret: ANTHROPIC_API_KEY"
      exit 1
    fi
```

Without this precheck, the orchestrator still completes but may return a fallback fix plan instead of a real investigation result.

## Agent Command Contract

The command set in `CLAUDECODE_INVESTIGATE_CMD` must:

1. Accept a prompt file path via `{prompt_file}`.
2. Read prompt content from that file.
3. Execute the agent investigation.
4. Write a single JSON object to stdout.

Expected JSON shape (minimum):

```json
{
  "root_cause": "string",
  "confidence": 0.0,
  "proposed_changes": ["string"],
  "patch_style": "string"
}
```

If command execution fails or stdout is not valid JSON, the orchestrator falls back to a safe placeholder plan so the pipeline can still complete.

## Included Claude Runner

This repo now includes `agent/claude_runner.py`, which:

1. Reads the rendered prompt file path passed as `{prompt_file}`.
2. Calls Anthropic Messages API using `ANTHROPIC_API_KEY`.
3. Parses model output and extracts a JSON object.
4. Prints only JSON to stdout (compatible with orchestrator parsing).

Recommended command value for `CLAUDECODE_INVESTIGATE_CMD`:

```text
python agent/claude_runner.py {prompt_file}
```

## Runtime Artifacts

The orchestrator writes outputs into `agent/output/`:

- `issue_context.json`
- `issue_start_comment_result.json`
- `dtctl_skill_context.json`
- `dtctl_live_debugger_context.json`
- `evidence.json`
- `evidence_summary.json`
- `agent_prompt_rendered.md`
- `fix_plan.json`
- `pr_info.json`
- `issue_comment_result.json`
- `dynatrace_event_result.json`
- `summary.json`

These are uploaded by the workflow as an artifact.

## Local Dry Run (Optional)

To run locally, set required env vars and point `GITHUB_EVENT_PATH` to a sample issue event payload JSON:

```bash
export DT_ENVIRONMENT="https://abc12345.apps.dynatrace.com"
export DT_API_TOKEN="dt0s16.XXXXXXXX.YYYYYYYY"
export GITHUB_TOKEN="ghp_xxx"
export GITHUB_REPOSITORY="owner/repo"
export GITHUB_EVENT_PATH="/path/to/issue-event.json"
export INVESTIGATION_AGENT="claudecode"
export CLAUDECODE_INVESTIGATE_CMD="python agent/claude_runner.py {prompt_file}"
export CLAUDECODE=1
python agent/orchestrator.py
```

## Troubleshooting

- Problem ID not found
  - Ensure issue body includes `Problem: P-123456`.
- dtctl auth errors
  - Verify `DT_ENVIRONMENT` and `DT_API_TOKEN` values.
- Claude command not running
  - Ensure `CLAUDECODE_INVESTIGATE_CMD` is set and executable on the runner.
- Non-JSON Claude output
  - Ensure your command prints only JSON to stdout (logs should go to stderr).
- Event not attached to problem
  - Confirm extracted problem ID is present in `agent/output/issue_context.json` and in `dynatrace_event_result.json` payload properties.

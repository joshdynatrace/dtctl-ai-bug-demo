# Agent Automation README

This folder contains the issue-investigation automation for the Dynatrace -> GitHub -> AI-agent demo.

## What This Does

When a matching GitHub issue is created, the workflow:

1. Parses the issue and extracts the dynamic Dynatrace Problem ID (`Problem: P-...`).
2. Posts a "investigation started" comment to the issue.
3. Runs a single investigation pass and invokes the configured agent runtime.
4. Lets the agent decide which dtctl commands to run during a single agent session.
5. Persists prompt/results artifacts and a final fix plan.
6. Posts a completion comment with evidence summary.
7. Sends a Dynatrace event update attached to the same problem ID.
8. Uploads artifacts from `agent/output/`.

## Key Files

- `agent/orchestrator.py`
  - Main pipeline coordinator.
  - Handles issue intake, prompt rendering, comments, agent handoff, and summary artifacts.
- `agent/agent_sdk_runner.py`
  - Invokes Claude Agent SDK with Bash tool execution.
  - Claude can run `dtctl` commands interactively and collect evidence.
  - Outputs JSON result to stdout.
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

## How the Agent Runs dtctl Commands

The orchestrator uses the Claude Agent SDK (`agent/agent_sdk_runner.py`) to create an interactive debugging session:

1. The agent receives the investigation prompt with instructions to run `dtctl` commands.
2. Claude Code's agentic loop gives it real **Bash tool** access.
3. Claude can dynamically choose which `dtctl` commands to run, execute them, and iterate based on output.
4. Results (command outputs, breakpoint data) are collected as evidence and returned as JSON.
5. The orchestrator processes the JSON and builds the final fix plan.

This replaces the older single-turn API model where Claude could only *describe* dtctl commands — now it actually *executes* them.

## Required GitHub Secrets

Set these repository secrets:

- `DT_ENV_LIVE`
  - Example: `https://abc12345.live.dynatrace.com`
- `DT_API_TOKEN`
  - Dynatrace API token. Required scope: **`events.ingest`** (for posting investigation results back to the Dynatrace problem). Add any additional scopes required by your dtctl commands.
- `ANTHROPIC_API_KEY`
  - Anthropic API key for Claude Agent SDK operations.

## GitHub Token Permissions

The investigation flow uses the GitHub token to post issue comments.

The workflow uses GitHub's built-in `GITHUB_TOKEN` by default (no custom secret required).

If issue comments fail with 403 permission errors, check repository Settings -> Actions -> Workflow permissions and make sure workflow write access is allowed.

Required permissions:

- Fine-grained PAT (recommended)
  - Repository access: limit to this repository
  - **Issues**: Read and write

- Classic PAT
  - Public repository: `public_repo`
  - Private repository: `repo`

## Optional Configuration

Set these repository variables (Settings -> Secrets and variables -> Actions -> Variables) if you need to override defaults:

- None required for the baseline investigation flow.

Useful optional runtime environment variables:

- `AGENT_TRACE`
  - Enables live stderr tracing and JSONL trace file output.
- `AGENT_TRACE_FILE`
  - Output path for structured trace events.
- `AGENT_TRACE_INCLUDE_PARTIAL`
  - Includes partial streaming events from the SDK when enabled.
- `EVIDENCE_EXCERPT_MAX_LEN`
  - Maximum length of evidence excerpts included in the GitHub completion comment.

## Workflow Environment Variables

Configured in `.github/workflows/dynatrace-agent-investigation.yml`:

- `DT_ENV_LIVE` / `DT_ENV_APPS` / `DT_API_TOKEN`
  - Dynatrace environment URLs and auth. `DT_ENV_LIVE` is used by the Events API; `DT_ENV_APPS` is used by dtctl.
- `DTCTL_CONTEXT=demo`
  - Named context for dtctl operations.
- `ANTHROPIC_API_KEY`
  - Loaded from secrets; used by Agent SDK runner.
- `AUTO_PR=true`
  - Whether to create pull requests with proposed fixes (skeleton implementation).

## Agent SDK Runner Contract

The orchestrator invokes `agent/agent_sdk_runner.py`, which:

1. Takes a rendered prompt file path as argument.
2. Uses Claude Agent SDK to create an interactive session with `allowed_tools=["Bash", "Read"]`.
3. Claude can execute `dtctl` and other commands, iterate based on output.
4. Parses the final text output for a JSON object.
5. Outputs only JSON to stdout (compatible with orchestrator parsing).

Expected JSON shape (minimum):

```json
{
  "root_cause": "string",
  "confidence": 0.0,
  "evidence": [
    {
      "type": "log|snapshot|trace",
      "detail": "string"
    }
  ]
}
```

Optional completion signal:

- `"investigation_complete": true`

If omitted, the orchestrator still completes and records the returned fix plan.

If the runner fails or returns invalid JSON, the orchestrator falls back to a placeholder plan so the pipeline can still complete.

## Runtime Artifacts

The orchestrator writes outputs into `agent/output/`:

- `issue_context.json`
- `issue_start_comment_result.json`
- `agent_prompt.md`
- `investigation_result.json`
- `evidence_summary.json`
- `agent_prompt_rendered.md`
- `agent_trace.jsonl` (when tracing is enabled)
- `fix_plan.json`
- `pr_info.json`
- `issue_comment_result.json`
- `dynatrace_event_result.json`
- `summary.json`

These are uploaded by the workflow as an artifact.

## Local Dry Run

Use the included `run-local-investigation.sh` script for a complete local setup:

```bash
cd agent
./run-local-investigation.sh
```

This script:

1. Creates a Python venv and installs dependencies (`requests`, `claude-agent-sdk`).
2. Fetches GitHub issue #8 from the repo.
3. Sets up environment variables from `.env.local` (copy from `.env.local.example` and fill in your secrets).
4. Runs the orchestrator.
5. Outputs artifacts to `agent/output/`.

By default, local runs now enable agent tracing:

- `AGENT_TRACE=true`
- `AGENT_TRACE_FILE=agent/output/agent_trace.jsonl`

This gives two views of agent behavior:

1. Live trace lines in terminal stderr (`[agent-trace] ...`) showing tool uses/results and system events.
2. Structured JSONL trace in `agent/output/agent_trace.jsonl` for post-run inspection.

Manual setup (if you prefer):

```bash
export DT_ENV_LIVE="https://abc12345.live.dynatrace.com"
export DT_ENV_APPS="https://abc12345.apps.dynatrace.com"
export DT_API_TOKEN="dt0s16.XXXXXXXX.YYYYYYYY"
export GITHUB_TOKEN="ghp_xxx"
export GITHUB_REPOSITORY="owner/repo"
export GITHUB_EVENT_PATH="/path/to/issue-event.json"
export ANTHROPIC_API_KEY="sk-ant-xxx"
export AGENT_TRACE="true"
export AGENT_TRACE_FILE="agent/output/agent_trace.jsonl"
python agent/orchestrator.py
```

## Troubleshooting

- Problem ID not found
  - Ensure issue body includes `Problem: P-123456`.
- dtctl auth errors
  - Verify `DT_ENV_LIVE` uses a `.live.dynatrace.com` URL and `DT_API_TOKEN` is valid with the `events.ingest` scope.
- Agent SDK runner fails
  - Ensure `ANTHROPIC_API_KEY` is set and valid.
  - Check that `claude-agent-sdk` is installed: `pip install claude-agent-sdk`.
  - Review live `[agent-trace]` stderr output during the run.
  - Review `agent/output/agent_trace.jsonl` after the run when tracing is enabled.
- Event not attached to problem
  - Confirm extracted problem ID is present in `agent/output/issue_context.json` and in `dynatrace_event_result.json` payload properties.

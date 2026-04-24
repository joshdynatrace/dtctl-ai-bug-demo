# Phase 3 — Remediation

--8<-- "snippets/bizevent-phase-3-remediation.js"

In Phase 3, the agent creates a pull request with a proposed fix, posts a summary back to the GitHub issue, and reports the investigation results back to Dynatrace — closing the loop.

---

## Pull Request Creation

When `AUTO_PR=true` is set (the default in this demo) in the GitHub action, the orchestrator automatically creates a fix branch and opens a pull request from the agent's findings.

The PR includes:

- A **code change** based on the agent's `fix_strategy` and `code_changes` output
- A **description** that links back to the original GitHub issue
- The **evidence** gathered during investigation — log excerpts, Live Debugger snapshot details, and trace summaries

The branch is named from the Problem ID (e.g. `fix/P-123456-null-category`), making it easy to trace back to the triggering event.

!!! tip "Where to look"
    Go to the **Pull Requests** tab in your GitHub repository. The agent's PR will be open and linked to the issue that triggered it.

---

## GitHub Issue Completion Comment

The orchestrator posts a completion comment to the original GitHub issue once the investigation is done. The comment contains:

- **Root cause** — the agent's finding in plain language
- **Confidence score** — how certain the agent is (0.0–1.0)
- **Evidence summary** — the key pieces of data that supported the conclusion (log excerpts, snapshot details, trace links)
- **Pull request link** — a direct link to the fix PR

This gives any human reviewer a complete picture before they decide to merge.

!!! tip "Where to look"
    Open the GitHub issue that triggered the workflow. You'll see two agent comments: the initial "investigation started" comment posted in Step 2, and the completion report posted here.

---

## Dynatrace Annotation Event

After the PR is created, the orchestrator calls the Dynatrace Events API (`/api/v2/events/ingest`) to post a `CUSTOM_ANNOTATION` event back to the original Problem record.

The event payload links the GitHub PR directly to the Problem:

```json
{
  "eventType": "CUSTOM_ANNOTATION",
  "properties": {
    "status": "pr_opened",
    "problem.id": "P-XXXXXX",
    "github.issue": "https://github.com/owner/repo/issues/42",
    "annotation.url": "https://github.com/owner/repo/pull/43",
    "root.cause": "NullPointerException: taxResponse.getCategory() returns null...",
    "confidence": "0.95"
  }
}
```

!!! tip "Where to look"
    Navigate to the **Problem** in your Dynatrace environment. On the problem timeline, you'll see the annotation event appear with a direct link to the pull request.

---

## Investigation Artifacts

All outputs from the pipeline are saved to `agent/output/` and uploaded as a GitHub Actions artifact named `agent-evidence-<run-id>`:

| File | Contents |
|------|----------|
| `issue_context.json` | Parsed issue data and extracted Problem ID |
| `agent_prompt_rendered.md` | The exact prompt passed to Claude |
| `investigation_result.json` | Full JSON result from the agent |
| `fix_plan.json` | Structured fix plan with code changes |
| `pr_info.json` | Created PR URL and branch details |
| `dynatrace_event_result.json` | Response from the Dynatrace Events API |
| `agent_trace.jsonl` | Structured log of every tool call Claude made |

!!! tip "Where to look"
    In the GitHub Actions run, scroll to the bottom and download the `agent-evidence-<run-id>` artifact. The `agent_trace.jsonl` file is especially useful — it records every `dtctl` command, its output, and Claude's reasoning at each step.

---

## The Completed Loop

With the PR open and the Problem annotated, the full automated loop is complete:

1. A developer reviews the PR, confirms the fix looks correct, and merges it
2. The fix ships and the error rate drops
3. Dynatrace automatically resolves the Problem
4. The complete timeline — from error detection through investigation to fix — is captured in both GitHub and Dynatrace

<div class="grid cards" markdown>
- [Cleanup :octicons-arrow-right-24:](cleanup.md)
</div>

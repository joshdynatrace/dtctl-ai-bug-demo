# Phase 2 — Investigation

--8<-- "snippets/bizevent-phase-2-investigation.js"

In Phase 2, the GitHub issue created by the Dynatrace Workflow triggers an automated AI investigation. Claude Code uses `dtctl` to query logs, traces, and the Live Debugger to find the root cause.

---

## GitHub Actions Trigger

The repository includes a GitHub Actions workflow at `.github/workflows/dynatrace-agent-investigation.yml`. It triggers whenever an issue is **opened** or **labeled** with `dynatrace-problem`:

```yaml
on:
  issues:
    types: [opened, labeled]
```

The workflow checks that the issue title contains `Defect Found` before proceeding, so only Dynatrace-generated issues trigger the agent.

The job runs inside a pre-built container image (`ghcr.io/<owner>/dtctl-agent:latest`) that includes Python, `dtctl`, and the Claude Code CLI.

!!! tip "Where to look"
    Go to the **Actions** tab in your GitHub repository. Each issue matching the trigger creates a new workflow run named **Dynatrace Agent Investigation**. Click into it to follow the live logs.

---

## Python Orchestrator

The first thing the workflow runs is `agent/orchestrator.py` — the main pipeline coordinator. It follows a structured sequence of steps:

| Step | What happens |
|------|-------------|
| **1. Intake** | Parse the GitHub issue body and extract the Dynatrace Problem ID (`P-XXXXXX`) |
| **2. Notify** | Post an "investigation started" comment to the issue |
| **3. Investigate** | Invoke the Claude Code Agent SDK runner |
| **4. Create PR** | Open a fix branch and pull request (when `AUTO_PR=true`) |
| **5. Report** | Post a completion comment with evidence summary |
| **6. Update Dynatrace** | Send a `CUSTOM_ANNOTATION` event back to the Problem |
| **7. Finalize** | Persist all artifacts to `agent/investigation_output/` |

The investigation prompt is rendered from `agent/templates/agent_prompt.md` by `agent/pipeline.py`, which injects the issue details and Problem ID before passing it to Claude.

---

## Claude Code Agent

The orchestrator invokes `agent/agent_sdk_runner.py`, which creates an interactive Claude Code session using the **Anthropic Agent SDK**.

Claude receives the investigation prompt and runs in `bypassPermissions` mode, giving it access to the full Claude Code toolset — meaning it can execute `dtctl` commands, read and edit files, and iterate based on what it finds. This is an agentic loop, not a single-shot prompt.

```python
# agent_sdk_runner.py — simplified
result = await agent.run(
    prompt=rendered_prompt,
    allowed_tools=["Bash", "Read"],
    max_turns=60,
)
```

Claude decides which commands to run, examines the output, forms a hypothesis, runs more commands, and repeats until it has enough evidence to identify the root cause.

!!! tip "Where to look"
    In the GitHub Actions log, look for lines prefixed with `[agent-trace]`. These show each `dtctl` command Claude ran, the tool result, and Claude's reasoning as it narrows in on the problem.

---

## dtctl Investigation Tools

The agent uses three primary investigation capabilities via `dtctl`:

### Logs

Claude queries Grail for recent error logs from the `arc-store` namespace:

```bash
dtctl query -A 'fetch logs
  | filter k8s.namespace.name == "arc-store"
  | filter status == "ERROR"
  | limit 100'
```

This surfaces exception messages, stack traces, and the exact lines in the code where the error originated.

### Distributed Traces

Claude retrieves distributed traces linked to the Dynatrace Problem to see the full call path:

```bash
dtctl query -A 'fetch spans
  | filter dt.entity.service == "arc-backend"
  | filter status == "ERROR"
  | limit 20'
```

Traces show the flow from the frontend request through the backend to the outbound tax service call, including the response that caused the failure.

### Live Debugger

The Live Debugger is the most powerful tool in this flow. It lets Claude set a **non-breaking breakpoint** on a specific line of code. When that line is hit by live traffic, Dynatrace captures a **snapshot** of the JVM state — local variables, the call stack, and return values — without pausing or affecting the running application.

```bash
# Set a breakpoint on the suspected line
dtctl create breakpoint backend/src/main/java/com/arcstore/service/OrderService.java:40

# Retrieve captured snapshots
dtctl query fetch application.snapshots | sort timestamp desc | limit 5 --decode-snapshots=full -o json
```

The snapshot shows Claude the actual value of every variable at that point in execution — for example, confirming that `taxResponse.getCategory()` returned `null` when the tax service omitted the field.

!!! tip "Where to look"
    Navigate to **Live Debugger** in your Dynatrace environment. While the agent is running, you'll see the breakpoints it set listed here. After a snapshot is captured, you can inspect it directly in the Dynatrace UI alongside what the agent saw.

---

## Agent Output

When the investigation completes, the agent emits a structured JSON result that the orchestrator uses to build the PR and the Dynatrace annotation:

```json
{
  "root_cause": "NullPointerException: taxResponse.getCategory() returns null when tax service omits the field for unknown product categories",
  "confidence": 0.95,
  "evidence": [
    {
      "type": "log",
      "detail": "Stack trace shows NPE at OrderService.java:47 inside processOrder()"
    },
    {
      "type": "snapshot",
      "detail": "Live Debugger snapshot: taxResponse.category == null, productId == 'PROD-999'"
    },
    {
      "type": "trace",
      "detail": "Outbound span to tax-service returned HTTP 200 with body missing 'category' field"
    }
  ],
  "fix_strategy": "Add null check before calling category.getRate(); return a default tax rate of 0.0 when category is absent",
  "code_changes": [
    {
      "file": "backend/src/main/java/com/example/arcstore/service/OrderService.java",
      "description": "Guard against null category in tax response"
    }
  ]
}
```

<div class="grid cards" markdown>
- [Phase 3: Remediation :octicons-arrow-right-24:](phase-3-remediation.md)
</div>

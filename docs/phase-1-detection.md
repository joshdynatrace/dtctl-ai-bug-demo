# Phase 1 — Detection

--8<-- "snippets/bizevent-phase-1-detection.js"

In Phase 1, an error in the Arc Store is automatically detected by Dynatrace, which raises a Problem and hands off to the investigation pipeline via a GitHub issue.

---

## The Arc Store and Tax Service

The Arc Store is an e-commerce application with three main services:

| Service | Technology | Kubernetes namespace |
|---------|-----------|---------------------|
| Frontend | React (Vite) + nginx | `arc-store` |
| Backend | Spring Boot 3.2 | `arc-store` |
| Load generator | Python | `arc-store` |

When a customer places an order, the backend calls an external **tax service** to calculate the applicable tax rate for the shipping state. The backend parses the JSON response and accesses the `category` field to get the rate.

If the tax service returns a response with a missing or malformed `category` field — for example, when a product category is not found — the backend throws a `NullPointerException` while parsing the response. This propagates as an HTTP 500 error back to the frontend.

!!! tip "Where to look"
    Open the Arc Store at [http://localhost:3000](http://localhost:3000){target=_blank} and place a test order. If the tax service returns an unexpected response, you'll see a 500 error in the browser and in the `arc-backend` logs.

---

## Dynatrace OpenPipeline

Dynatrace's **OpenPipeline** continuously processes incoming telemetry from the Arc Store — logs, traces, and metrics. When it detects an error pattern from the backend service (NullPointerException), it raises a **Dynatrace Problem** (Davis Event).

The Problem record captures:

- The affected service and entity
- The start time of the degradation
- Relevant error logs

!!! tip "Where to look"
    Navigate to **Problems** in your Dynatrace tenant. When the demo is active, you'll see a problem for the Arc Store backend. Click into it to see the full problem timeline, affected entities, and root-cause hints.

---

## Dynatrace Workflow

When the Problem is opened, a pre-configured **Dynatrace Workflow** fires automatically. The workflow performs two actions:

### 1. Collects Relevant Logs

A DQL query is used to collect relevant error logs for the GitHub issue that will be created.

### 2. Create a GitHub Issue

The workflow calls the GitHub Issues API to create an issue in this repository. The issue is structured so the agent can parse it:

- **Title**: `Defect Found: <problem description>`
- **Body**: Contains the Dynatrace Problem ID and Event ID:
    ```
    Problem: P-XXXXXX
    EventID: -7029478988662415020_1776449283806V2
    ```

### 2. Post an Annotation Event

The workflow also posts a `CUSTOM_ANNOTATION` event back to the Dynatrace Problem record to log that the automated investigation has been triggered. This keeps the full timeline visible inside Dynatrace.

!!! tip "Where to look"
    Navigate to **Workflows** in your Dynatrace tenant and open the workflow. The execution history shows each run, the inputs passed (Problem ID, entity details), and whether the GitHub issue was created successfully.

---

With the GitHub issue created, Phase 2 begins automatically.

<div class="grid cards" markdown>
- [Phase 2: Investigation :octicons-arrow-right-24:](phase-2-investigation.md)
</div>

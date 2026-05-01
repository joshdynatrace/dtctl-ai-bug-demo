import json
import os
import random
from pathlib import Path

import requests

from pipeline import FixPlan, IssueContext

SCRIPT_DIR = Path(__file__).resolve().parent.parent


def _safe_text(value, max_len=1800) -> str:
    text = str(value or "")
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def post_dynatrace_event(
    issue_ctx: IssueContext,
    fix_plan: FixPlan,
    pr_info: dict,
    evidence_summary: dict,
) -> dict:
    dt_env = os.getenv("DT_ENV_LIVE")
    dt_token = os.getenv("DT_API_TOKEN")

    if not dt_env or not dt_token:
        return {"status": "skipped", "reason": "missing DT_ENV_LIVE or DT_API_TOKEN for Events API"}

    if ".live.dynatrace.com" not in dt_env:
        url = f"{dt_env.rstrip('/')}/api/v2/events/ingest"
        return {
            "status": "skipped",
            "reason": "DT_ENV_LIVE must use a .live.dynatrace.com domain for Events API",
            "endpoint": url,
        }

    template_path = SCRIPT_DIR / "templates" / "dynatrace_event_payload.json"
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    payload["title"] = f"AI investigation update for {issue_ctx.problem_id or 'unknown problem'}"

    props = payload.setdefault("properties", {})
    pr_url = str(pr_info.get("pr_url", "") or "").strip()
    pr_branch = str(pr_info.get("branch", "") or "").strip()
    pr_title = str(pr_info.get("title", "") or "").strip()

    props["status"] = "pr_opened" if pr_url else "investigation_complete"
    props["problem.id"] = issue_ctx.problem_id or ""
    props["dt.problem.id"] = issue_ctx.problem_id or ""
    props["github.issue.number"] = str(issue_ctx.issue_number or "")
    props["github.issue.title"] = _safe_text(issue_ctx.issue_title, max_len=250)
    props["github.issue"] = issue_ctx.issue_url
    props["confidence"] = str(fix_plan.confidence)
    props["root.cause"] = _safe_text(fix_plan.root_cause, max_len=4000)
    props["service"] = issue_ctx.service_name or "unknown-service"

    if pr_url:
        props["annotation.url"] = pr_url
    else:
        props.pop("annotation.url", None)
    if pr_branch:
        props["pr.branch"] = pr_branch
    else:
        props.pop("pr.branch", None)
    if pr_title:
        props["pr.title"] = _safe_text(pr_title, max_len=250)
    else:
        props.pop("pr.title", None)

    props["evidence.query.count"] = str(evidence_summary.get("query_count", 0))
    props["evidence.debugger.count"] = str(evidence_summary.get("debugger_count", 0))

    query_names = ",".join(
        item.get("name", "") for item in evidence_summary.get("queries", []) if item.get("name")
    )
    debugger_commands = _safe_text(
        "; ".join(item.get("cmd", "") for item in evidence_summary.get("debugger", []) if item.get("cmd")),
        max_len=800,
    )
    if query_names:
        props["evidence.query.names"] = query_names
    else:
        props.pop("evidence.query.names", None)
    if debugger_commands:
        props["evidence.debugger.commands"] = debugger_commands
    else:
        props.pop("evidence.debugger.commands", None)

    props["annotation.id"] = str(random.random())
    if issue_ctx.event_id:
        props["annotation.problem_ids"] = issue_ctx.event_id
    else:
        props.pop("annotation.problem_ids", None)

    props["evidence.summary"] = _safe_text(json.dumps(evidence_summary), max_len=1800)

    url = f"{dt_env.rstrip('/')}/api/v2/events/ingest"
    headers = {"Authorization": f"Api-Token {dt_token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    return {"status": response.status_code, "response": response.text[:1000], "payload": payload, "endpoint": url}

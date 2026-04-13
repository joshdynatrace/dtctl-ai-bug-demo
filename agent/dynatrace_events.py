import json
import os
from pathlib import Path

import requests


def _safe_text(value, max_len=1800):
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _resolve_dynatrace_env():
    return os.getenv("DTCTL_ENVIRONMENT") or os.getenv("DT_ENV_URL")


def _resolve_dynatrace_token():
    return os.getenv("DTCTL_TOKEN") or os.getenv("DT_API_TOKEN")


def post_dynatrace_event(issue_ctx, fix_plan, pr_info, evidence_summary):
    dt_env = _resolve_dynatrace_env()
    dt_token = _resolve_dynatrace_token()

    if not dt_env or not dt_token:
        return {"status": "skipped", "reason": "missing Dynatrace env/token"}

    template_path = Path("agent/templates/dynatrace_event_payload.json")
    template = template_path.read_text(encoding="utf-8")
    payload = json.loads(template)
    payload["title"] = f"AI investigation update for {issue_ctx.get('problem_id', 'unknown problem')}"

    props = payload.setdefault("properties", {})
    props["problem.id"] = issue_ctx.get("problem_id", "")
    props["dt.problem.id"] = issue_ctx.get("problem_id", "")
    props["github.issue.number"] = str(issue_ctx.get("issue_number", ""))
    props["github.issue.title"] = _safe_text(issue_ctx.get("issue_title", ""), max_len=250)
    props["github.issue"] = issue_ctx.get("issue_url", "")
    props["confidence"] = str(fix_plan.get("confidence", ""))
    props["root.cause"] = fix_plan.get("root_cause", "")
    props["pr.url"] = pr_info.get("pr_url", "")
    props["pr.branch"] = pr_info.get("branch", "")
    props["pr.title"] = _safe_text(pr_info.get("title", ""), max_len=250)
    props["service"] = issue_ctx.get("service_name", "")
    props["evidence.query.count"] = str(evidence_summary.get("query_count", 0))
    props["evidence.debugger.count"] = str(evidence_summary.get("debugger_count", 0))
    props["evidence.query.names"] = ",".join(
        [item.get("name", "") for item in evidence_summary.get("queries", [])]
    )
    props["evidence.debugger.commands"] = _safe_text(
        "; ".join([item.get("cmd", "") for item in evidence_summary.get("debugger", [])]),
        max_len=800,
    )
    props["evidence.summary"] = _safe_text(json.dumps(evidence_summary), max_len=1800)

    url = f"{dt_env.rstrip('/')}/api/v2/events/ingest"
    headers = {
        "Authorization": f"Api-Token {dt_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    return {"status": response.status_code, "response": response.text[:1000], "payload": payload}

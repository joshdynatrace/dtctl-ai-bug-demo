import os

import requests


def post_issue_comment(issue_ctx, body):
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    issue_number = issue_ctx.get("issue_number")

    if not repo or not token or not issue_number:
        return {"status": "skipped", "reason": "missing GitHub env or issue number"}

    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.post(url, headers=headers, json={"body": body}, timeout=30)
    return {"status": response.status_code, "response": response.text[:1000]}


def build_start_comment(issue_ctx):
    return (
        "AI investigation started.\n\n"
        f"- Problem: {issue_ctx.get('problem_id')}\n"
        f"- Issue: {issue_ctx.get('issue_url')}\n"
        "- Next steps: collect dtctl logs, capture Dynatrace Live Debugger evidence, propose fix, and update this issue.\n"
    )


def build_completion_comment(issue_ctx, fix_plan, pr_info, evidence_summary):
    lines = [
        "AI investigation completed.",
        "",
        f"- Problem: {issue_ctx.get('problem_id')}",
        f"- Root cause: {fix_plan.get('root_cause')}",
        f"- Confidence: {fix_plan.get('confidence')}",
        f"- PR: {pr_info.get('pr_url', 'not created')}",
        f"- Evidence queries collected: {evidence_summary.get('query_count')}",
        f"- Live Debugger commands run: {evidence_summary.get('debugger_count')}",
        "",
        "Evidence summary:",
    ]

    for item in evidence_summary.get("queries", []):
        lines.append(
            f"- Query `{item.get('name')}` rc={item.get('returncode')} excerpt={item.get('stdout_excerpt')}"
        )

    for item in evidence_summary.get("debugger", []):
        lines.append(
            f"- Debugger `{item.get('cmd')}` rc={item.get('returncode')} excerpt={item.get('stdout_excerpt')}"
        )

    return "\n".join(lines)

#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dynatrace_events import post_dynatrace_event
from github_issues import build_completion_comment, build_start_comment, post_issue_comment


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def now_utc():
    return datetime.now(timezone.utc)


def read_github_event():
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        raise RuntimeError("GITHUB_EVENT_PATH is missing or invalid")
    return json.loads(Path(event_path).read_text(encoding="utf-8"))


def extract_problem_id(issue_body, issue_title=""):
    source = f"{issue_title}\n{issue_body}"
    patterns = [
        r"Problem:\s*(P-\d+)",
        r"problem\.id\s*[:=]\s*(P-\d+)",
        r"\b(P-\d{3,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, source or "", re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def build_agent_prompt(issue_ctx, investigation_state):
    template_path = SCRIPT_DIR / "templates" / "agent_prompt.md"
    prompt_template = template_path.read_text(encoding="utf-8")
    skill_text = (
        "Use dtctl directly during investigation. You are expected to choose commands dynamically, "
        "execute them, and iterate until root cause confidence is high."
    )
    live_debugger_text = (
        "Use Dynatrace Live Debugger commands through dtctl when needed. "
        "Collect concrete variable-value evidence before finalizing."
    )
    
    # Determine if agent should create a PR
    auto_pr = _env_flag("AUTO_PR", False)
    if auto_pr:
        pr_instructions = (
            f"After finalizing the root cause and fix, you MUST create a pull request:\n"
            f"1. Create a new branch named: agent/fix-{issue_ctx.get('issue_number')}\n"
            f"2. Make the necessary code changes based on your analysis\n"
            f"3. Commit the changes with a descriptive message including the root cause\n"
            f"4. Push the branch to GitHub\n"
            f"5. Create a PR with the fix plan summary in the description\n"
            f"Include the PR URL, branch name, and PR number in your final response."
        )
    else:
        pr_instructions = "PR creation is disabled (AUTO_PR not set)."

    return (
        prompt_template.replace("{{ISSUE_JSON}}", json.dumps(issue_ctx, indent=2))
        .replace("{{EVIDENCE_JSON}}", json.dumps(investigation_state, indent=2))
        .replace("{{DTCTL_SKILL_CONTEXT}}", skill_text)
        .replace("{{DTCTL_LIVE_DEBUGGER_CONTEXT}}", live_debugger_text)
        .replace("{{PR_CREATION_INSTRUCTIONS}}", pr_instructions)
    )


def _default_fix_plan(reason):
    return {
        "root_cause": f"Investigation did not complete: {reason}",
        "confidence": 0.0,
        "evidence": [],
    }


def run_agent_command(prompt_file_path):
    runner = SCRIPT_DIR / "agent_sdk_runner.py"
    trace_enabled = _env_flag("AGENT_TRACE", False)
    if trace_enabled:
        # Stream stderr live so [agent-trace] events show up in GitHub Actions logs in real time.
        proc = subprocess.Popen(
            [sys.executable, str(runner), prompt_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(SCRIPT_DIR),
        )
        stderr_lines = []
        if proc.stderr is not None:
            for line in proc.stderr:
                stderr_lines.append(line)
                print(line, end="", file=sys.stderr)
        stdout_text = proc.stdout.read() if proc.stdout is not None else ""
        returncode = proc.wait()
        stderr_text = "".join(stderr_lines).strip()
    else:
        proc = subprocess.run(
            [sys.executable, str(runner), prompt_file_path],
            capture_output=True,
            text=True,
            cwd=str(SCRIPT_DIR),
        )
        stdout_text = proc.stdout
        stderr_text = proc.stderr.strip()
        returncode = proc.returncode

    if returncode != 0:
        error_text = stderr_text or f"Runner failed with exit code {returncode}."
        return {
            "ok": False,
            "error": error_text,
            "result": _default_fix_plan(error_text),
        }
    try:
        parsed = json.loads((stdout_text or "").strip())
        if isinstance(parsed, dict):
            return {"ok": True, "error": "", "result": parsed}
        return {
            "ok": False,
            "error": "Runner output was not a JSON object",
            "result": _default_fix_plan("Runner output was not a JSON object"),
        }
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "Runner output was not valid JSON",
            "result": _default_fix_plan("Runner output was not valid JSON"),
        }


def run_investigation(issue_ctx):
    investigation_state = {
        "notes": [
            "Choose and run dtctl commands dynamically based on issue details.",
            "Only finalize when root cause evidence is concrete.",
        ],
    }

    prompt = build_agent_prompt(issue_ctx, investigation_state)
    prompt_path = OUTPUT_DIR / "agent_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    cmd_result = run_agent_command(str(prompt_path))
    investigation_result = {
        "started_at": now_utc().isoformat(),
        "ok": cmd_result.get("ok", False),
        "error": cmd_result.get("error", ""),
        "result": cmd_result.get("result", {}),
        "ended_at": now_utc().isoformat(),
    }

    final_fix_plan = investigation_result.get("result", _default_fix_plan("Empty result from runner"))

    persist("investigation_result.json", investigation_result)
    (OUTPUT_DIR / "agent_prompt_rendered.md").write_text(prompt, encoding="utf-8")
    return final_fix_plan, investigation_result


def maybe_create_pr(issue_ctx, fix_plan):
    """
    Validates that the agent created a PR if AUTO_PR is enabled.
    The agent is responsible for actually creating the PR; this function
    just extracts and validates the result from the fix_plan.
    """
    auto_pr = _env_flag("AUTO_PR", False)
    if not auto_pr:
        return {"status": "skipped", "reason": "AUTO_PR=false"}

    # Check if the agent included PR information in the fix_plan
    if "pr_url" in fix_plan and fix_plan.get("pr_url"):
        return {
            "status": "created",
            "pr_url": fix_plan.get("pr_url"),
            "pr_number": fix_plan.get("pr_number"),
            "branch": fix_plan.get("branch"),
        }
    else:
        return {
            "status": "pending",
            "reason": "Agent did not include PR details in response. This may indicate PR creation succeeded silently or encountered an issue."
        }


def persist(name, data):
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def safe_text(value, max_len=1800):
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def summarize_evidence_from_fix_plan(fix_plan):
    evidence_items = fix_plan.get("evidence", [])
    excerpt_max_len = int(os.getenv("EVIDENCE_EXCERPT_MAX_LEN", "4000"))
    query_summaries = []
    debugger_summaries = []
    for item in evidence_items if isinstance(evidence_items, list) else []:
        detail = safe_text(item.get("detail", ""), max_len=excerpt_max_len)
        evidence_type = str(item.get("type", "")).lower()
        if evidence_type == "snapshot":
            debugger_summaries.append(
                {
                    "cmd": "agent_collected_snapshot",
                    "returncode": 0,
                    "stdout_excerpt": detail,
                }
            )
        else:
            query_summaries.append(
                {
                    "name": evidence_type or "evidence",
                    "returncode": 0,
                    "stdout_excerpt": detail,
                }
            )
    return {
        "query_count": len(query_summaries),
        "debugger_count": len(debugger_summaries),
        "queries": query_summaries,
        "debugger": debugger_summaries,
    }


def main():
    # ========================================================================
    # 1. INTAKE: Parse GitHub issue and extract Dynatrace Problem ID
    # ========================================================================
    event = read_github_event()
    issue = event.get("issue", {})
    issue_body = issue.get("body", "") or ""

    issue_ctx = {
        "issue_number": issue.get("number"),
        "issue_url": issue.get("html_url"),
        "issue_title": issue.get("title", ""),
        "issue_body": issue_body,
        "problem_id": extract_problem_id(issue_body, issue.get("title", "")),
        "service_name": os.getenv("DEFAULT_SERVICE_NAME", ""),
        "repo": os.getenv("GITHUB_REPOSITORY", ""),
        "run_id": os.getenv("GITHUB_RUN_ID", ""),
        "sha": os.getenv("GITHUB_SHA", ""),
    }
    persist("issue_context.json", issue_ctx)

    if not issue_ctx.get("problem_id"):
        raise RuntimeError("Could not extract Dynatrace problem ID from the issue body/title")

    # ========================================================================
    # 2. NOTIFY: Post "investigation started" comment on the GitHub issue
    # ========================================================================
    start_comment_result = post_issue_comment(issue_ctx, build_start_comment(issue_ctx))
    persist("issue_start_comment_result.json", start_comment_result)

    # ========================================================================
    # 3. INVESTIGATE: Single handoff to agent runtime (agent chooses dtctl)
    # ========================================================================
    fix_plan, investigation_result = run_investigation(issue_ctx)
    persist("fix_plan.json", fix_plan)
    evidence_summary = summarize_evidence_from_fix_plan(fix_plan)
    persist("evidence_summary.json", evidence_summary)

    # ========================================================================
    # 4. CREATE PR (optional): If AUTO_PR enabled, create branch + PR
    # ========================================================================
    pr_info = maybe_create_pr(issue_ctx, fix_plan)
    persist("pr_info.json", pr_info)

    # ========================================================================
    # 5. REPORT RESULTS: Post completion comment with evidence summary
    # ========================================================================
    comment_body = build_completion_comment(issue_ctx, fix_plan, pr_info, evidence_summary)
    comment_result = post_issue_comment(issue_ctx, comment_body)
    persist("issue_comment_result.json", comment_result)

    # ========================================================================
    # 6. UPDATE DYNATRACE: Post investigation event linked to problem ID
    # ========================================================================
    dt_event_result = post_dynatrace_event(issue_ctx, fix_plan, pr_info, evidence_summary)
    persist("dynatrace_event_result.json", dt_event_result)

    # ========================================================================
    # 7. FINALIZE: Persist summary and output to stdout for CI logging
    # ========================================================================
    summary = {
        "issue_context": issue_ctx,
        "fix_plan": fix_plan,
        "pr_info": pr_info,
        "investigation_result": investigation_result,
        "evidence_summary": evidence_summary,
        "start_comment_result": start_comment_result,
        "comment_result": comment_result,
        "dynatrace_event_result": dt_event_result,
        "finished_at": now_utc().isoformat(),
    }
    persist("summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"orchestrator failed: {err}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from dynatrace_events import post_dynatrace_event
from github_issues import build_completion_comment, build_start_comment, post_issue_comment


OUTPUT_DIR = Path("agent/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DTCTL_SKILL_URL = "https://raw.githubusercontent.com/dynatrace-oss/dtctl/main/skills/dtctl/SKILL.md"
DEFAULT_DTCTL_LIVE_DEBUGGER_DOC_URL = "https://dynatrace-oss.github.io/dtctl/docs/live-debugger/"
DTCTL_AGENT_ENV_VARS = [
    "CLAUDECODE",
    "OPENCODE",
    "GITHUB_COPILOT",
    "CURSOR_AGENT",
    "KIRO",
    "JUNIE",
    "OPENCLAW",
    "CODEIUM_AGENT",
    "TABNINE_AGENT",
    "AMAZON_Q",
]


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


def run_cmd(args, check=False):
    proc = subprocess.run(args, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}\\n{proc.stderr}")
    return {
        "cmd": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def use_dtctl_agent_mode():
    mode = os.getenv("DTCTL_USE_AGENT_MODE", "auto").lower()
    if mode in {"true", "1", "yes"}:
        return True
    if mode in {"false", "0", "no"}:
        return False
    # auto: prefer dtctl's own environment auto-detection when supported
    return len(detected_agent_env_vars()) == 0


def detected_agent_env_vars():
    return [name for name in DTCTL_AGENT_ENV_VARS if os.getenv(name)]


def with_dtctl_agent_args(args):
    if not use_dtctl_agent_mode():
        return args
    if "--agent" in args or "-A" in args:
        return args
    return args + ["--agent"]


def get_dtctl_command_catalog():
    return run_cmd(with_dtctl_agent_args(["dtctl", "commands", "--brief", "-o", "json"]))


def fetch_dtctl_skill_context():
    url = os.getenv("DTCTL_SKILL_URL", DEFAULT_DTCTL_SKILL_URL)
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200 and response.text.strip():
            return {
                "source": url,
                "content": response.text,
                "status": "ok",
            }
        return {
            "source": url,
            "content": "",
            "status": f"http_{response.status_code}",
        }
    except requests.RequestException as err:
        return {
            "source": url,
            "content": "",
            "status": f"error: {err}",
        }


def fetch_live_debugger_doc_context():
    url = os.getenv("DTCTL_LIVE_DEBUGGER_DOC_URL", DEFAULT_DTCTL_LIVE_DEBUGGER_DOC_URL)
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200 and response.text.strip():
            return {
                "source": url,
                "content": response.text,
                "status": "ok",
            }
        return {
            "source": url,
            "content": "",
            "status": f"http_{response.status_code}",
        }
    except requests.RequestException as err:
        return {
            "source": url,
            "content": "",
            "status": f"error: {err}",
        }


def collect_evidence(issue_ctx):
    evidence = {
        "started_at": now_utc().isoformat(),
        "queries": [],
        "debugger": [],
        "notes": [],
        "dtctl_commands": {},
    }

    evidence["dtctl_commands"] = get_dtctl_command_catalog()

    # Baseline capabilities only. The investigation agent decides which queries/breakpoints to run.
    bp_cmds = [
        with_dtctl_agent_args(["dtctl", "get", "live-debugger", "workspace-filters", "-o", "json"]),
    ]
    for cmd in bp_cmds:
        evidence["debugger"].append(run_cmd(cmd))

    evidence["notes"].append(
        "Issue parsing and investigation strategy are delegated to the agent prompt; orchestrator only provides context and transport."
    )

    evidence["ended_at"] = now_utc().isoformat()
    return evidence


def build_agent_prompt(issue_ctx, evidence, skill_context, live_debugger_context):
    template_path = Path("agent/templates/agent_prompt.md")
    prompt_template = template_path.read_text(encoding="utf-8")
    payload = {
        "issue": issue_ctx,
        "evidence_summary": {
            "query_count": len(evidence.get("queries", [])),
            "debugger_actions": len(evidence.get("debugger", [])),
        },
    }
    skill_text = skill_context.get("content", "")
    if not skill_text:
        skill_text = f"Skill context unavailable. Source={skill_context.get('source')} status={skill_context.get('status')}"

    live_debugger_text = live_debugger_context.get("content", "")
    if not live_debugger_text:
        live_debugger_text = (
            "Live Debugger doc context unavailable. "
            f"Source={live_debugger_context.get('source')} status={live_debugger_context.get('status')}"
        )

    return (
        prompt_template.replace("{{ISSUE_JSON}}", json.dumps(issue_ctx, indent=2))
        .replace("{{EVIDENCE_JSON}}", json.dumps(payload, indent=2))
        .replace("{{DTCTL_SKILL_CONTEXT}}", skill_text)
        .replace("{{DTCTL_LIVE_DEBUGGER_CONTEXT}}", live_debugger_text)
    )


def _default_fix_plan(reason):
    return {
        "root_cause": f"Investigation delegated to agent runtime. {reason}",
        "confidence": 0.0,
        "proposed_changes": [
            "No deterministic patch generated by orchestrator.",
            "Configure Claude Code investigator command to return structured JSON.",
        ],
        "patch_style": "agent-delegated",
    }


def run_model_for_fix_plan(prompt_text, prompt_file_path):
    del prompt_text

    agent_runtime = os.getenv("INVESTIGATION_AGENT", "stub").lower()
    if agent_runtime != "claudecode":
        return _default_fix_plan(f"INVESTIGATION_AGENT={agent_runtime}")

    cmd_template = os.getenv("CLAUDECODE_INVESTIGATE_CMD", "").strip()
    if not cmd_template:
        return _default_fix_plan("CLAUDECODE_INVESTIGATE_CMD not set")

    rendered = cmd_template.format(prompt_file=prompt_file_path)
    cmd = shlex.split(rendered)
    result = run_cmd(cmd)

    if result.get("returncode") != 0:
        return _default_fix_plan(f"ClaudeCode command failed: {result.get('stderr', '')}")

    stdout = result.get("stdout", "")
    try:
        parsed = json.loads(stdout)
        if isinstance(parsed, dict):
            return parsed
        return _default_fix_plan("ClaudeCode output was valid JSON but not an object")
    except json.JSONDecodeError:
        return _default_fix_plan("ClaudeCode output was not valid JSON")


def maybe_create_pr(issue_ctx, fix_plan):
    auto_pr = os.getenv("AUTO_PR", "false").lower() == "true"
    if not auto_pr:
        return {"status": "skipped", "reason": "AUTO_PR=false"}

    # Skeleton: implement branch/commit/pr creation in your preferred way.
    return {
        "status": "created",
        "pr_url": "https://github.com/OWNER/REPO/pull/123",
        "branch": f"agent/fix-{issue_ctx.get('issue_number')}",
        "title": f"Fix NPE for issue #{issue_ctx.get('issue_number')}",
        "summary": fix_plan.get("root_cause", ""),
    }


def persist(name, data):
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def safe_text(value, max_len=1800):
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def summarize_evidence(evidence):
    query_summaries = []
    for item in evidence.get("queries", []):
        result = item.get("result", {})
        query_summaries.append(
            {
                "name": item.get("name"),
                "returncode": result.get("returncode"),
                "stdout_excerpt": safe_text(result.get("stdout", ""), max_len=280),
            }
        )

    debugger_summaries = []
    for item in evidence.get("debugger", []):
        debugger_summaries.append(
            {
                "cmd": " ".join(item.get("cmd", [])),
                "returncode": item.get("returncode"),
                "stdout_excerpt": safe_text(item.get("stdout", ""), max_len=280),
            }
        )

    return {
        "query_count": len(evidence.get("queries", [])),
        "debugger_count": len(evidence.get("debugger", [])),
        "queries": query_summaries,
        "debugger": debugger_summaries,
    }


def main():
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
        "detected_agent_env_vars": detected_agent_env_vars(),
        "repo": os.getenv("GITHUB_REPOSITORY", ""),
        "run_id": os.getenv("GITHUB_RUN_ID", ""),
        "sha": os.getenv("GITHUB_SHA", ""),
    }
    persist("issue_context.json", issue_ctx)

    if not issue_ctx.get("problem_id"):
        raise RuntimeError("Could not extract Dynatrace problem ID from the issue body/title")

    start_comment_result = post_issue_comment(issue_ctx, build_start_comment(issue_ctx))
    persist("issue_start_comment_result.json", start_comment_result)

    skill_context = fetch_dtctl_skill_context()
    persist("dtctl_skill_context.json", skill_context)

    live_debugger_context = fetch_live_debugger_doc_context()
    persist("dtctl_live_debugger_context.json", live_debugger_context)

    evidence = collect_evidence(issue_ctx)
    persist("evidence.json", evidence)
    evidence_summary = summarize_evidence(evidence)
    persist("evidence_summary.json", evidence_summary)

    prompt = build_agent_prompt(issue_ctx, evidence, skill_context, live_debugger_context)
    prompt_path = OUTPUT_DIR / "agent_prompt_rendered.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    fix_plan = run_model_for_fix_plan(prompt, str(prompt_path))
    persist("fix_plan.json", fix_plan)

    pr_info = maybe_create_pr(issue_ctx, fix_plan)
    persist("pr_info.json", pr_info)

    comment_body = build_completion_comment(issue_ctx, fix_plan, pr_info, evidence_summary)
    comment_result = post_issue_comment(issue_ctx, comment_body)
    persist("issue_comment_result.json", comment_result)

    dt_event_result = post_dynatrace_event(issue_ctx, fix_plan, pr_info, evidence_summary)
    persist("dynatrace_event_result.json", dt_event_result)

    summary = {
        "issue_context": issue_ctx,
        "fix_plan": fix_plan,
        "pr_info": pr_info,
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

"""Trigger adapter for non-GitHub event sources.

Reads IssueContext from a JSON payload on stdin, or from environment variables
when stdin is not a pipe. This lets the investigation pipeline be invoked from
PagerDuty webhooks, Slack events, Dynatrace workflow automations, or any other
alert source without touching the investigation logic.

JSON stdin fields (all optional):
  issue_number, issue_url, issue_title, issue_body,
  problem_id, event_id, service_name, repo, run_id, sha

Environment variable fallback:
  ISSUE_NUMBER, ISSUE_URL, ISSUE_TITLE, ISSUE_BODY,
  PROBLEM_ID, EVENT_ID, DEFAULT_SERVICE_NAME,
  GITHUB_REPOSITORY, GITHUB_RUN_ID, GITHUB_SHA

Example — invoke from a shell script:
  echo '{"problem_id": "P-12345", "issue_title": "Tax service error"}' | \\
    python agent/orchestrator.py --trigger generic
"""
import json
import os
import sys

from pipeline import IssueContext


def load_issue_context() -> IssueContext:
    if not sys.stdin.isatty():
        payload = json.loads(sys.stdin.read())
        return IssueContext(
            issue_number=payload.get("issue_number"),
            issue_url=payload.get("issue_url", ""),
            issue_title=payload.get("issue_title", ""),
            issue_body=payload.get("issue_body", ""),
            problem_id=payload.get("problem_id"),
            event_id=payload.get("event_id"),
            service_name=payload.get("service_name", os.getenv("DEFAULT_SERVICE_NAME", "")),
            repo=payload.get("repo", os.getenv("GITHUB_REPOSITORY", "")),
            run_id=payload.get("run_id", os.getenv("GITHUB_RUN_ID", "")),
            sha=payload.get("sha", os.getenv("GITHUB_SHA", "")),
        )

    raw_number = os.getenv("ISSUE_NUMBER", "")
    return IssueContext(
        issue_number=int(raw_number) if raw_number.isdigit() else None,
        issue_url=os.getenv("ISSUE_URL", ""),
        issue_title=os.getenv("ISSUE_TITLE", ""),
        issue_body=os.getenv("ISSUE_BODY", ""),
        problem_id=os.getenv("PROBLEM_ID"),
        event_id=os.getenv("EVENT_ID"),
        service_name=os.getenv("DEFAULT_SERVICE_NAME", ""),
        repo=os.getenv("GITHUB_REPOSITORY", ""),
        run_id=os.getenv("GITHUB_RUN_ID", ""),
        sha=os.getenv("GITHUB_SHA", ""),
    )

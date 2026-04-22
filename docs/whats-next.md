--8<-- "snippets/bizevent-whats-next.js"

# What's Next?

You've seen the full arc — from a live production error, through automated AI investigation, to a pull request with a fix and evidence. Here are some ideas for taking the demo further.

## Extend the Agent

**Add more investigation tools**

The agent currently uses logs, traces, and the Live Debugger. You could extend it with metric queries (`dtctl query` on metrics) or service topology lookups to broaden what it can detect.

**Tune the investigation prompt**

The prompt lives in `agent/templates/agent_prompt.md`. Editing it lets you guide the agent toward specific error patterns, restrict it to certain namespaces, or ask it to consider dependencies you know about.

**Multi-agent investigation**

Split detection, investigation, and remediation into separate Claude agents that hand off to each other — for example, a triage agent that classifies the problem type before a specialist agent investigates.

## Production Considerations

**Human approval gates**

Add a workflow step that posts the agent's findings and waits for a human to approve before the PR is auto-merged. Dynatrace Workflows supports approval steps natively.

**Confidence thresholds**

Only auto-create PRs when the agent's confidence score exceeds a configurable threshold (e.g. 0.85). Lower-confidence findings can still be reported as issues for human review.

**Notifications**

Send a Slack or email alert when the agent opens a PR, so the on-call engineer knows a fix is ready for review.

## More Dynatrace Resources

- [Dynatrace Community](https://community.dynatrace.com/){target=_blank}
- [Dynatrace University](https://university.dynatrace.com/){target=_blank}
